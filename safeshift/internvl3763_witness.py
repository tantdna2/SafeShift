"""Single durable authority for TRAIN3763 claims; deploy behind reviewed HTTPS.

No scheduler, inference or Kaggle credentials. Never run independent databases
for one series. SQLite transactions survive process restart; never delete claims.
"""
import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import secrets
import time

from safeshift.candidates.source import require
from safeshift.pilot.contract import digest
from safeshift import internvl3763_release as authority


class Store:
    def __init__(self, database, *, reader=None, now=None):
        self.database = str(database)
        self.reader, self.now = reader, now
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO metadata VALUES ('authority_id', ?)", (secrets.token_hex(32),))
            self.identity = db.execute("SELECT value FROM metadata WHERE name='authority_id'").fetchone()[0]
            db.execute("CREATE TABLE IF NOT EXISTS claims (series TEXT, attempt INTEGER, kind TEXT, "
                "release TEXT NOT NULL, receipt TEXT NOT NULL, PRIMARY KEY(series, attempt, kind))")
            db.execute("CREATE TABLE IF NOT EXISTS consumed (series TEXT, ordinal INTEGER, attempt INTEGER, "
                "PRIMARY KEY(series, ordinal))")
            db.execute("CREATE TABLE IF NOT EXISTS releases (locator TEXT PRIMARY KEY, grant_json TEXT NOT NULL)")

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def observe(self, series, attempt, kind):
        with self.connect() as db:
            if kind == "snapshot":
                rows = db.execute("SELECT kind, receipt FROM claims WHERE series=? AND attempt=?",
                    (series, attempt)).fetchall()
                require(len(rows) <= 3767, "SNAPSHOT_BOUND")
                return {"witness_id": self.identity, "claims": {key: json.loads(value) for key, value in rows}}
            row = db.execute("SELECT receipt FROM claims WHERE series=? AND attempt=? AND kind=?",
                (series, attempt, kind)).fetchone()
        return {"witness_id": self.identity, "found": False} if row is None else {
            "witness_id": self.identity, "found": True, "receipt": json.loads(row[0])}

    def claim(self, series, attempt, kind, payload):
        require(set(payload) == {"release", "request", "kind"} and payload["kind"] == kind, "CLAIM_FIELDS")
        locator = digest(payload["release"])
        if kind == "submit":
            grant = authority.load(payload["release"], reader=self.reader, now=self.now)
        else:
            # The first authenticated submit seals this exact finite-window
            # release in the durable authority database. No GitHub read per image.
            with self.connect() as db:
                sealed = db.execute("SELECT grant_json FROM releases WHERE locator=?", (locator,)).fetchone()
            require(sealed is not None, "AUTHENTICATED_SUBMISSION_RELEASE_REQUIRED")
            grant = json.loads(sealed[0])
            require(grant["issued_unix"] <= (time.time() if self.now is None else self.now) < grant["expires_unix"],
                "SEALED_RELEASE_EXPIRED")
        execution = authority.bind(grant, payload["request"])
        require(grant["witness_id"] == self.identity, "WRONG_OR_RESET_AUTHORITY_DATABASE")
        authority.Witness(grant, payload["release"]).path(kind)
        require((grant["series"], grant["attempt"]) == (series, attempt), "CLAIM_ROUTE_BINDING")
        require(kind != "snapshot", "SNAPSHOT_READ_ONLY")
        key = (series, attempt)
        release = digest(grant)
        receipt = {"schema": "train3763-permanent-claim-v1", "created": True,
            "claim_sha256": digest(payload), "release_sha256": release,
            "witness_id": self.identity,
            "series": series, "attempt": attempt, "kind": kind,
            "utc_unix": time.time() if self.now is None else self.now}
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if kind == "submit":
                # An authentic next release attests terminal custody of all prior
                # attempts. Even an unknown submit remains charged, never refunded.
                prior = db.execute("SELECT attempt, release, receipt FROM claims WHERE series=? AND kind='submit' ORDER BY attempt",
                    (series,)).fetchall()
                require([r[0] for r in prior] == list(range(1, attempt))
                    and [digest(json.loads(r[2])) for r in prior] == grant["predecessors"],
                    "UNKNOWN_OR_MISSING_PREDECESSOR_NO_RETRY")
                total = sum(json.loads(r[2])["reserved_gpu_seconds"] for r in prior)
                require(total + grant["caps"]["attempt_gpu_seconds"] <= grant["caps"]["campaign_gpu_seconds"],
                    "CUMULATIVE_GPU_BUDGET_EXHAUSTED")
                receipt["reserved_gpu_seconds"] = grant["caps"]["attempt_gpu_seconds"]
                receipt["cumulative_gpu_seconds"] = total + receipt["reserved_gpu_seconds"]
                receipt.update(job=grant["job"], version=grant["version"],
                    notebook_code_sha256=grant["notebook_code_sha256"], source_sha256=grant["source_sha256"])
                db.execute("INSERT INTO releases VALUES (?, ?)", (locator, json.dumps(grant, sort_keys=True)))
            else:
                parent_kind = {"launch": "submit", "worker": "launch", "load": "worker"}.get(kind, "load")
                parent = db.execute("SELECT release FROM claims WHERE series=? AND attempt=? AND kind=?",
                    (*key, parent_kind)).fetchone()
                require(parent is not None and parent[0] == release, "EXACT_PARENT_CLAIM_REQUIRED")
                if kind.startswith("call-"):
                    ordinal = int(kind[5:])
                    scheduled = execution["plan"]["scheduled_ordinals"]
                    require(ordinal in scheduled, "CALL_NOT_IN_EXACT_SCHEDULE")
                    existing = db.execute("SELECT kind FROM claims WHERE series=? AND attempt=? AND kind LIKE 'call-%'",
                        key).fetchall()
                    # Prefix order is fixed; no gaps, parallel reordered calls or
                    # silently skipped consumed IDs are accepted.
                    require(len(existing) < grant["caps"]["calls"]
                        and ordinal == scheduled[len(existing)], "CALL_CAP_OR_ORDER")
                    db.execute("INSERT INTO consumed VALUES (?, ?, ?)", (series, ordinal, attempt))
            db.execute("INSERT INTO claims VALUES (?, ?, ?, ?, ?)", (*key, kind, release,
                json.dumps(receipt, sort_keys=True, allow_nan=False)))
        return receipt


def handler(store):
    """Loopback HTTP only; a separately reviewed TLS proxy must protect hosting.

    POST bodies contain private TRAIN metadata under the release's O4 scope.
    GET returns hashes/claims only, never the request, IDs, raw or credentials.
    """
    from http.server import BaseHTTPRequestHandler
    import re
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # no URL/body/credential logging

        def reply(self, code, value):
            data = json.dumps(value, allow_nan=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def handle_claim(self, post):
            self.connection.settimeout(15)
            try:
                route = re.fullmatch(r"/v1/([A-Za-z0-9_-]{1,100})/([1-9][0-9]{0,3})/(submit|launch|worker|load|snapshot|call-[0-9]{6})", self.path)
                require(route is not None, "WITNESS_ROUTE")
                series, attempt, kind = route[1], int(route[2]), route[3]
                if post:
                    require("Transfer-Encoding" not in self.headers, "NO_CHUNKED_CLAIM_BODY")
                    size = int(self.headers.get("Content-Length", "0"))
                    require(0 < size <= 64 * 2**20, "WITNESS_BODY_BOUND")
                    body = self.rfile.read(size)
                    require(len(body) == size, "PARTIAL_WITNESS_BODY")
                    value = store.claim(series, attempt, kind, json.loads(body))
                else:
                    value = store.observe(series, attempt, kind)
                self.reply(201 if post else 200, value)
            except Exception as error:
                # A client sees BLOCKED, never an invitation to retry a POST.
                self.reply(409, {"status": "BLOCKED", "reason": type(error).__name__, "automatic_retry": False})

        def do_GET(self):
            self.handle_claim(False)

        def do_POST(self):
            self.handle_claim(True)
    return Handler
