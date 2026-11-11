"""Reviewed CPU-only companion for Owner UI results; never submits or runs a model.

Run this file from a reviewed tools checkout against the ORIGINAL clean approved
operator checkout. Keeping this companion outside source_spec is intentional:
neither runtime bytes nor the exact execution commit are silently migrated.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
import zipfile

# Direct-file execution can use a different, original operator checkout. Imports
# must come exclusively from that checkout, before any authority/ledger access.
if __name__ == "__main__":
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--approved-repo", type=Path, required=True)
    boot, _ = bootstrap.parse_known_args()
    sys.path.insert(0, str(boot.approved_repo.resolve()))

from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as campaign
from safeshift import internvl3763_operator as operator
from safeshift import internvl3763_release as authority
from safeshift.candidates.source import require
from safeshift.kaggle_handoff import Session, lock, private_root, SCHEMA as HANDOFF_SCHEMA
from safeshift.pilot.artifacts import read, write, write_bytes, sha, safe
from safeshift.pilot.contract import digest, require_hash

PROVENANCE = "OWNER_UI_MANUAL"
TOOL_MARKER = "SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V1"
OWNER_MARKER = "SAFESHIFT_TRAIN3763_OWNER_MANUAL_V1"
DISTINCT_SLUG = "DISTINCT_SLUG_V1"
SAME_SLUG = "SAME_SCHEDULED_SLUG_V2"
SAME_TOOL_MARKER = "SAFESHIFT_TRAIN3763_MANUAL_ADAPTER_V2"
SAME_OWNER_MARKER = "SAFESHIFT_TRAIN3763_OWNER_MANUAL_V2"


def collection_mode(mode):
    require(mode in (DISTINCT_SLUG, SAME_SLUG), "MANUAL_COLLECTION_MODE")
    return mode == SAME_SLUG


def tool_release(locator, grant, *, mode=DISTINCT_SLUG):
    """Separate audited COLLECTION authority, never a new runtime qualification."""
    same = collection_mode(mode)
    marker = SAME_TOOL_MARKER if same else TOOL_MARKER
    scope = "SAME_SCHEDULED_SLUG_COLLECTION_ONLY" if same else "MANUAL_COLLECTION_ONLY"
    value, comment = campaign.record(locator, marker, authority.get)
    fields = {"implementation_pr", "reviewed_head", "merged_sha", "script_sha256", "audit", "scope"}
    if same:
        fields.add("owner")
    require(set(value) == fields and value["scope"] == scope, "MANUAL_TOOL_RELEASE_FIELDS")
    require(type(value["implementation_pr"]) is int and value["implementation_pr"] > 189
        and comment["user"]["login"] in grant["review_logins"]
        and comment["issue_url"] == authority.API + "/issues/" + str(value["implementation_pr"]),
        "MANUAL_TOOL_REVIEW_AUTHORITY")
    pr = authority.get("/pulls/" + str(value["implementation_pr"]))
    require(pr["merged"] is True and pr["base"]["ref"] == "main"
        and pr["head"]["sha"] == value["reviewed_head"] and pr["merge_commit_sha"] == value["merged_sha"],
        "MANUAL_TOOL_NOT_REVIEWED_MERGED")
    for key in ("reviewed_head", "merged_sha"):
        require(type(value[key]) is str and re.fullmatch(r"[a-f0-9]{40}", value[key]), "MANUAL_TOOL_COMMIT")
    require_hash(value["script_sha256"])
    require(sha(__file__) == value["script_sha256"], "MANUAL_TOOL_BYTES_DRIFT")
    audit, auditor = campaign.record(value["audit"], marker + "_AUDIT", authority.get)
    require(auditor["user"]["login"] in grant["audit_logins"] and auditor["id"] != comment["id"]
        and auditor["issue_url"] == comment["issue_url"]
        and audit == {"reviewed_head": value["reviewed_head"], "script_sha256": value["script_sha256"],
            "status": "PASS", "independent": True}, "MANUAL_TOOL_INDEPENDENT_AUDIT")
    return {"locator": locator, "release": value}


def approved_source(ledger, request):
    require(campaign.load(request["execution_release"], collection=True) == ledger.grant, "MANUAL_ORIGINAL_GRANT")
    execution = campaign.bind(ledger.grant, request)  # exact technical/audit/O5 release, unchanged
    revision = campaign.revision(ledger.grant, request)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime.ROOT, text=True).strip()
    require(head == request["commit_sha"] == revision["merged_sha"] and not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=runtime.ROOT),
        "MANUAL_ORIGINAL_CLEAN_APPROVED_CHECKOUT_REQUIRED")
    require(runtime.source_spec() == execution["source"] == request["plan"]["runtime_source"],
        "MANUAL_SOURCE_CHANGED_REQUALIFICATION_REQUIRED")
    content = subprocess.check_output(["git", "show", head + ":" + request["notebook"]], cwd=runtime.ROOT)
    require(hashlib.sha256(content).hexdigest() == sha(safe(runtime.ROOT, request["notebook"]))
        == request["notebook_sha256"] == revision["notebook_sha256"], "MANUAL_APPROVED_NOTEBOOK")
    notebook = runtime._strict_json_loads(content)
    require(operator.code_hash(notebook) == revision["notebook_code_sha256"], "MANUAL_APPROVED_NOTEBOOK_CODE")
    return notebook


def handoff_snapshot(session, request, *, mode=DISTINCT_SLUG):
    same = collection_mode(mode)
    report = session.latest_report()  # verifies the persisted report hash/chain
    require(session.request == request and (same or report is not None and report["status"] == "BLOCKED"),
        "MANUAL_IMMUTABLE_BLOCKED_HANDOFF_REQUIRED")
    events = session.events()
    require(not same or not any(e["status"] == "SUBMISSION_INTENT" for e in events),
        "MANUAL_AMBIGUOUS_HANDOFF_SUBMISSION_INTENT")
    require(not same or not (session.root / "submission").exists(), "MANUAL_AMBIGUOUS_SUBMISSION_FILES")
    require(not any(e["status"] in ("SUBMITTED", "OBSERVED", "RUNNING_UNVERIFIED", "PASS", "FAIL")
        for e in events), "MANUAL_HANDOFF_POSSIBLE_SUBMIT")
    if same:
        # UI preparation is not a failed API submission. Accept the original
        # PREPARED event without manufacturing a BLOCKED report. V1 is unchanged.
        require(read(session.root / "request.json") == request and session.binding == digest(request),
            "MANUAL_ORIGINAL_HANDOFF_REQUEST_REQUIRED")
        prepared_fields = {"schema", "binding", "previous", "utc", "status"}
        require(events and set(events[0]) == prepared_fields and events[0]["schema"] == HANDOFF_SCHEMA
            and events[0]["status"] == "PREPARED" and type(events[0]["utc"]) is str and events[0]["utc"],
            "MANUAL_ORIGINAL_PREPARED_EVENT_REQUIRED")
        reports = set()
        for number, event in enumerate(events[1:], 2):
            name = f"report-{number:05d}.json"
            require(set(event) == prepared_fields | {"report_path", "report_sha256"}
                and event["schema"] == HANDOFF_SCHEMA and event["status"] == "BLOCKED"
                and event["report_path"] == name, "MANUAL_UNEXPECTED_HANDOFF_EVENT")
            path = safe(session.root, name)
            require(sha(path) == event["report_sha256"], "REPORT_HASH_DRIFT")
            blocked = read(path)
            require(all(blocked.get(k) == v for k, v in {
                "schema": HANDOFF_SCHEMA + "-report", "status": "BLOCKED", "binding": session.binding,
                "handoff_id": request["handoff_id"], "job_id": request["job"], "version": request["version"],
                "commit_sha": request["commit_sha"], "runtime_commit": request["runtime_commit"],
                "notebook_sha256": request["notebook_sha256"], "scope": request["scope"]}.items()),
                "MANUAL_BOUND_BLOCKED_REPORT_REQUIRED")
            reports.add(name)
        require({p.name for p in session.root.glob("report-*.json")} == reports,
            "MANUAL_UNREFERENCED_HANDOFF_REPORT")
    files = {}
    for path in session.root.rglob("*"):
        if path.is_file() and path.name != "operator.lock":
            relative = path.relative_to(session.root).as_posix()
            safe(session.root, relative)
            require(len(files) < 1024 and path.stat().st_size <= 64 * 2**20, "MANUAL_HANDOFF_BOUND")
            files[relative] = sha(path)
    return {"path": str(session.root.resolve()), "files": files, "head_sha256": digest(events[-1])}


def owner_attestation(locator, ledger, intent, archive, *, mode=DISTINCT_SLUG):
    same = collection_mode(mode)
    value, comment = campaign.record(locator, SAME_OWNER_MARKER if same else OWNER_MARKER, authority.get)
    fields = {"campaign_sha256", "intent_sha256", "request_sha256", "job", "version", "kernel_id",
        "archive_sha256", "archive_bytes", "operator"}
    fields |= {"mode", "ledger_events", "ledger_head_sha256", "plan_sha256", "scheduled_ordinals",
        "input_sources", "no_api_submission", "no_other_job_or_version"} if same else {"original_job_not_run"}
    require(set(value) == fields, "MANUAL_OWNER_FIELDS")
    require(comment["user"]["login"] == authority.OWNER
        and comment["issue_url"] == authority.API + "/issues/180", "MANUAL_AUTHENTIC_OWNER_ATTESTATION")
    require(value["campaign_sha256"] == digest(ledger.grant) and value["intent_sha256"] == digest(intent)
        and value["request_sha256"] == digest(intent["request"]) and value["operator"] == PROVENANCE,
        "MANUAL_OWNER_INTENT_BINDING")
    if same:
        events = ledger.events()
        require(events and events[-1] == intent and value["mode"] == SAME_SLUG
            and type(value["ledger_events"]) is int and value["ledger_events"] == len(events)
            and value["ledger_head_sha256"] == digest(events[-1])
            and value["plan_sha256"] == digest(intent["request"]["plan"])
            and type(value["scheduled_ordinals"]) is list
            and all(type(n) is int for n in value["scheduled_ordinals"])
            and value["scheduled_ordinals"] == intent["request"]["plan"]["scheduled_ordinals"]
            and value["input_sources"] == operator.input_sources(intent["request"])
            and value["no_api_submission"] is True and value["no_other_job_or_version"] is True,
            "MANUAL_SAME_SLUG_FACT_BINDING")
    else:
        require(value["original_job_not_run"] is True, "MANUAL_OWNER_INTENT_BINDING")
    require(type(value["job"]) is str and re.fullmatch(r"nguynanhtn/[a-z0-9][a-z0-9-]{0,100}", value["job"])
        and (value["job"] == intent["request"]["job"]) == same
        and type(value["version"]) is int and value["version"] == 1
        and type(value["kernel_id"]) is int and value["kernel_id"] > 0, "MANUAL_OWNER_PROVIDER_IDENTITY")
    require(value["archive_sha256"] == sha(archive) and type(value["archive_bytes"]) is int
        and value["archive_bytes"] == Path(archive).stat().st_size <= ledger.grant["caps"]["archive_bytes"],
        "MANUAL_OWNER_ARCHIVE_BINDING")
    return value


def observe_kernel(client, job, version, notebook, sources, *, kernel_id=None, expected_state="COMPLETE"):
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    from scripts.submit_internvl_v2 import bounded_http
    with bounded_http():
        query = ApiGetKernelRequest()
        query.user_name, query.kernel_slug = job.split("/")
        query.version_label = operator.kernel_version_label(version)
        with client.build_kaggle_client() as remote:
            value = remote.kernels.kernels_api_client.get_kernel(query)
        # Also observe latest: v1 must not hide a newer version or concurrent job.
        query.version_label = None
        with client.build_kaggle_client() as remote:
            latest = remote.kernels.kernels_api_client.get_kernel(query)
        status = client.kernels_status(job + "/" + str(version))
    require(str(status.status).split(".")[-1] == expected_state in campaign.TERMINAL
        and (expected_state != "COMPLETE" or not status.failure_message),
        "MANUAL_PROVIDER_NOT_COMPLETE_OR_CONFLICT")
    for candidate in (value, latest):
        meta = candidate.metadata
        require(meta is not None and candidate.blob is not None and meta.ref == job and meta.is_private is True
            and type(meta.current_version_number) is int and meta.current_version_number == version
            and type(meta.id) is int and meta.id > 0 and (kernel_id is None or meta.id == kernel_id),
            "MANUAL_PROVIDER_IDENTITY_OR_VERSION")
        remote_notebook = runtime._strict_json_loads(candidate.blob.source)
        remote_metadata = remote_notebook.get("metadata", {}).get("safeshift")
        require(operator.code_hash(remote_notebook) == operator.code_hash(notebook)
            and (remote_metadata is None or remote_metadata == notebook.get("metadata", {}).get("safeshift")),
            "MANUAL_REMOTE_NOTEBOOK_DRIFT")
        operator.verify_kernel_metadata_inputs(meta, sources)
    require(latest.metadata.id == value.metadata.id, "MANUAL_PROVIDER_KERNEL_CHANGED")
    return {"state": expected_state, "job_id": job, "version": version, "kernel_id": value.metadata.id,
        "remote_notebook_sha256": hashlib.sha256(value.blob.source.encode()).hexdigest(),
        "safeshift_metadata": "ABSENT_EXECUTABLE_CODE_BOUND" if
            runtime._strict_json_loads(value.blob.source).get("metadata", {}).get("safeshift") is None else "MATCHED",
        "notebook_code_sha256": operator.code_hash(notebook), "failure_message": None}


def inventory(client, ledger, intent, manual_job, *, mode=DISTINCT_SLUG):
    """Prove exact scheduled-slug presence/absence and terminal predecessors.

    Manual predecessors keep their actual slug. No rewriting request['job'] or
    synthetic provider proxy to make the old API-submit inventory pass.
    """
    same = collection_mode(mode)
    require((manual_job == intent["request"]["job"]) == same, "MANUAL_INVENTORY_MODE_IDENTITY")
    from scripts.submit_internvl_v2 import bounded_http
    owned, tokens, token = set(), set(), None
    with bounded_http():
        for page in range(1, 17):
            response = client.kernels_list_with_response(mine=True, page_size=100, page_token=token,
                page=None if token else page)
            refs = [row.ref for row in response.kernels]
            require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(ref.startswith("nguynanhtn/") for ref in refs), "MANUAL_ACCOUNT_INVENTORY")
            owned.update(refs)
            token = response.next_page_token
            if not token and len(refs) < 100:
                break
            if token:
                require(token not in tokens, "MANUAL_REPEATED_INVENTORY_PAGE")
                tokens.add(token)
        else:
            raise ValueError("MANUAL_INCOMPLETE_INVENTORY")
    events = ledger.events()
    pushed = {e["intent_sha256"] for e in events if e["kind"] == "PUSH_INTENT"}
    expected = {e["request"]["job"] for e in ledger.intents() if digest(e) in pushed}
    prefix = "nguynanhtn/safeshift-train3763-" + ledger.grant["campaign_id"] + "-"
    if same:
        expected.add(manual_job)
        expected.update(e["provider"]["job_id"] for e in events if e["kind"] == "COLLECTED"
            and e["provider"]["job_id"].startswith(prefix))
    require((intent["request"]["job"] in owned) == same and manual_job in owned
        and {ref for ref in owned if ref.startswith(prefix)} == expected, "MANUAL_ORIGINAL_JOB_ABSENCE_OR_HISTORY")
    predecessors = []
    for previous in ledger.intents():
        if previous == intent:
            continue
        closed = [e for e in events if e["kind"] in ("COLLECTED", "ABORTED_PRE_SUBMIT")
            and e["intent_sha256"] == digest(previous)]
        require(len(closed) == 1, "MANUAL_AMBIGUOUS_PREDECESSOR")
        if closed[0]["kind"] == "ABORTED_PRE_SUBMIT":
            require(previous["request"]["job"] not in owned, "MANUAL_ABORTED_JOB_EXISTS")
            continue
        row = closed[0]
        provider = row["provider"]
        job = provider["job_id"]
        require(job in owned and job != manual_job, "MANUAL_REPLAY_OR_MISSING_PREDECESSOR")
        old_request = previous["request"]
        content = subprocess.check_output(["git", "show", old_request["commit_sha"] + ":" + old_request["notebook"]],
            cwd=runtime.ROOT)
        require(hashlib.sha256(content).hexdigest() == old_request["notebook_sha256"], "MANUAL_PREDECESSOR_NOTEBOOK")
        proof = observe_kernel(client, job, 1, runtime._strict_json_loads(content), operator.input_sources(old_request),
            kernel_id=provider.get("kernel_id"), expected_state=provider["state"])
        predecessors.append({"intent_sha256": digest(previous), **proof})
    return {"owned_sha256": digest(sorted(owned)), "owned_count": len(owned),
        "original_job_absent": not same, "predecessors": predecessors}


def validate_output_url(url, name):
    """Two exact provider origins, canonical paths; never echo bearer URLs."""
    require(type(url) is str and 0 < len(url) <= 16384
        and all(33 <= ord(c) < 127 for c in url) and "\\" not in url and "#" not in url,
        "MANUAL_UNSAFE_OUTPUT_URL")
    try:
        target = urlsplit(url)
    except ValueError:
        raise ValueError("MANUAL_UNSAFE_OUTPUT_URL") from None
    require(target.scheme == "https" and url.startswith("https://")
        and target.netloc in ("storage.googleapis.com", "www.kaggleusercontent.com"),
        "MANUAL_UNSAFE_OUTPUT_URL")
    # No percent escapes, empty/dot path segments or path parameters. The SDK file
    # name and literal last URL component must BOTH equal the expected name.
    parts = target.path.split("/")
    require(parts[0] == "" and parts[-1] == name and all(
        re.fullmatch(r"[A-Za-z0-9_~.-]+", p) and p not in (".", "..") for p in parts[1:]),
        "MANUAL_UNSAFE_OUTPUT_URL")
    if target.netloc == "www.kaggleusercontent.com":
        # Actual v1 output URLs use a compact JWE-style token: header, empty
        # encrypted-key field, IV, ciphertext, tag. Dots are INSIDE one path
        # segment; never decode it or publish it. Preserve simple opaque tokens.
        token = parts[3] if len(parts) == 5 else ""
        token_ok = re.fullmatch(r"[A-Za-z0-9_-]+", token) or re.fullmatch(
            r"[A-Za-z0-9_-]+\.\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", token)
        require("?" not in url and len(parts) == 5 and parts[1] == "kf"
            and re.fullmatch(r"[1-9][0-9]*", parts[2])
            and token_ok, "MANUAL_UNSAFE_OUTPUT_URL")
    else:
        require(bool(target.query), "MANUAL_UNSAFE_OUTPUT_URL")


@contextmanager
def private_transport_logs():
    """Suppress SDK/requests diagnostics that can serialize signed URLs."""
    previous = logging.root.manager.disable
    logging.disable(max(previous, logging.CRITICAL))
    try:
        yield
    finally:
        logging.disable(previous)


@contextmanager
def anonymous_output_session(deadline):
    """No ambient credentials/logged bearer paths; interrupt slow headers/body.

    The pinned urllib3 HTTPS connection keeps normal certificate verification.
    Only its connect hook is extended to register the TLS socket with a deadline
    watchdog. Idle read timeouts alone cannot stop a peer sending single bytes.
    """
    import socket
    import requests
    from urllib3.connection import HTTPSConnection
    from urllib3.connectionpool import HTTPSConnectionPool

    sockets, mutex = [], threading.Lock()
    expired = threading.Event()
    def shutdown(sock):
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass  # socket may already have closed normally
    def expire():
        with mutex:
            expired.set()
            for sock in sockets:
                shutdown(sock)
    class DeadlineConnection(HTTPSConnection):
        debuglevel = 0  # http.client debug prints bypass Python logging
        def connect(self):
            super().connect()
            with mutex:
                if expired.is_set() or time.monotonic() >= deadline:
                    shutdown(self.sock)
                    raise ValueError("MANUAL_DOWNLOAD_BOUND")
                sockets.append(self.sock)
    class DeadlinePool(HTTPSConnectionPool):
        ConnectionCls = DeadlineConnection
    class DeadlineAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            super().init_poolmanager(*args, **kwargs)
            # PoolManager's default registry is shared: never mutate it globally.
            self.poolmanager.pool_classes_by_scheme = {"https": DeadlinePool}

    remaining = deadline - time.monotonic()
    require(remaining > 0, "MANUAL_DOWNLOAD_BOUND")
    timer = threading.Timer(remaining, expire)
    timer.daemon = True
    # urllib3 diagnostics can include signed paths even on a handled exception.
    # This standalone, locked collector exposes only its sanitized failure code.
    started = False
    with private_transport_logs():
        try:
            timer.start()
            started = True
            with requests.Session() as http:
                http.trust_env = False
                http.mount("https://", DeadlineAdapter(max_retries=0))
                http.resolve_redirects = lambda *args, **kwargs: iter(())
                require(all(a.max_retries.total == 0 for a in http.adapters.values()), "MANUAL_RETRIES_FORBIDDEN")
                yield http
                require(not expired.is_set() and time.monotonic() < deadline, "MANUAL_DOWNLOAD_BOUND")
        finally:
            timer.cancel()
            if started:
                timer.join()  # no watchdog/socket work remains after return


def download_outputs(client, job, version, archive, expected_sha, destination):
    """Pinned SDK listing + bounded anonymous GET, no SDK retry/resume downloader."""
    import os
    from kagglesdk.kernels.types.kernels_api_service import ApiListKernelSessionOutputRequest
    from scripts.submit_internvl_v2 import bounded_http
    require(re.fullmatch(r"[A-Za-z0-9_-]+\.zip", archive.name), "MANUAL_ARCHIVE_NAME")
    require_hash(expected_sha)
    expected = {archive.name: archive.stat().st_size, archive.name + ".sha256.json": 4096}
    require(shutil.disk_usage(destination).free > sum(expected.values()) + 2**20, "MANUAL_DOWNLOAD_DISK_BOUND")
    with private_transport_logs(), bounded_http():
        query = ApiListKernelSessionOutputRequest()
        query.user_name, query.kernel_slug = job.split("/")
        query.version_label, query.page_size = operator.kernel_version_label(version), 256
        with client.build_kaggle_client() as remote:
            remote._http_client._verbose = False  # pinned SDK can print the response body
            result = remote.kernels.kernels_api_client.list_kernel_session_output(query)
        require(not result.next_page_token and len(result.files) <= 256
            and len({f.file_name for f in result.files}) == len(result.files), "MANUAL_OUTPUT_LIST_BOUND")
        selected = {f.file_name: f for f in result.files if f.file_name.endswith((".zip", ".zip.sha256.json"))}
        require(set(selected) == set(expected) and type(result.log) is str and 0 < len(result.log.encode()) <= 16*2**20,
            "MANUAL_EXACT_PROVIDER_OUTPUTS_AND_LOG")
    # Validate the pair before ANY output GET. Keep SDK's timeout wrapper above
    # separate: it replaces caller timeouts, including a shrinking GET budget.
    for name in expected:
        validate_output_url(selected[name].url, name)
    write_bytes(destination / "provider.log", result.log.encode())
    deadline = time.monotonic() + 240
    for name, limit in expected.items():
        remaining = deadline - time.monotonic()
        require(remaining > 0, "MANUAL_DOWNLOAD_BOUND")
        with anonymous_output_session(deadline) as http:
            # Disabling resolve_redirects also prevents requests from reading a
            # redirect body just to prepare Response.next with redirects disabled.
            with http.get(selected[name].url, stream=True, allow_redirects=False,
                    timeout=(min(10, remaining / 2), min(30, remaining / 2)),
                    headers={"Accept-Encoding": "identity"}) as response:
                require(response.status_code == 200, "MANUAL_OUTPUT_HTTP_STATUS")
                require(time.monotonic() < deadline, "MANUAL_DOWNLOAD_BOUND")
                require(response.headers.get("Content-Encoding", "identity") == "identity", "MANUAL_OUTPUT_ENCODING")
                length = response.headers.get("Content-Length")
                require(length is None or (re.fullmatch(r"[0-9]+", length)
                    and int(length) <= limit), "MANUAL_DOWNLOAD_BOUND")
                with (destination / name).open("xb") as stream:
                    total = 0
                    try:
                        for chunk in response.iter_content(65536):
                            total += len(chunk)
                            require(total <= limit and time.monotonic() < deadline, "MANUAL_DOWNLOAD_BOUND")
                            stream.write(chunk)
                        require(time.monotonic() < deadline, "MANUAL_DOWNLOAD_BOUND")
                        require(length is None or total == int(length), "MANUAL_OUTPUT_LENGTH_MISMATCH")
                    finally:
                        # Even a timeout leaves durable, create-only partials.
                        stream.flush(); os.fsync(stream.fileno())
    remote_archive = destination / archive.name
    require(sha(remote_archive) == expected_sha == read(str(remote_archive) + ".sha256.json")["sha256"],
        "MANUAL_PROVIDER_ARCHIVE_MISMATCH")
    return {"sha256": expected_sha, "bytes": remote_archive.stat().st_size,
        "sidecar_sha256": sha(str(remote_archive) + ".sha256.json"), "log_sha256": sha(destination / "provider.log")}


def verify_inputs_in_archive(archive, request):
    """Worker byte receipts supplement GetKernel's UNVERSIONED attachments."""
    from safeshift import internvl3763_python as python_input
    with zipfile.ZipFile(archive) as bundle:
        get = lambda name: runtime._strict_json_loads(bundle.read(name))
        execution = request["bindings"]["runtime"]["execution_request"]
        require(get("execution-request.json") == execution, "MANUAL_SEALED_EXECUTION_INPUT")
        images = get("environment/image-bytes.json")
        require(images["status"] == "TRAIN_BYTES_PASS" and images["master_sha256"] == execution["input_marker_sha256"]
            and images["projection_sha256"] == execution["projection_sha256"] and images["verified_images"] == 3763
            and images["changed"] == images["missing"] == images["duplicate_ids"] == 0
            and images["labels_exported"] is False, "MANUAL_TRAIN_INPUT_BYTES")
        checkpoint = get("environment/checkpoint.json")
        from safeshift.candidates.source import LOCK
        source = read(LOCK)["internvl35"]
        weights = read(LOCK.with_name("checkpoint_metadata_lock.json"))["internvl35"]
        require(checkpoint["source"] == source and checkpoint["weights"] == weights, "MANUAL_CHECKPOINT_LOCK")
        stream = get("environment/checkpoint-stream.json")
        require(stream["status"] == "ACTUAL_BYTES_VERIFIED" and stream["error"] is None
            and stream["weights_modified"] is False
            and len(stream["files"]) == len(weights["weights"])
            and {f["file"]: {"sha256": f["sha256"], "size": f["bytes_hashed"]} for f in stream["files"]}
                == weights["weights"]
            and all(f["descriptor_identity_unchanged"] is True for f in stream["files"]), "MANUAL_CHECKPOINT_BYTES")
        py = get("setup/python-input.json")
        manifest = python_input.manifest()
        require(py["status"] == "PASS" and py["ref"] == python_input.REF
            and py["sha256"] == manifest["lock"]["sha256"] and py["bytes"] == manifest["lock"]["size_bytes"]
            and py["transport_sha256"] == manifest["transport"]["sha256"]
            and py["transport_bytes"] == manifest["transport"]["size_bytes"] and py["python_downloads"] == 0,
            "MANUAL_PYTHON_INPUT_BYTES")


def verify_scheduled_completion(request, intent, result, ancestor):
    """Same-slug release admits the whole saved shard, never cherry-picked labels."""
    scheduled = request["plan"]["scheduled_ordinals"]
    records = ancestor["records"]
    require(len(scheduled) > 0 and len(scheduled) == len(set(scheduled))
        and result["model_calls"] == len(scheduled) == intent["reserved_calls"]
        and [row["ordinal"] for row in records] == scheduled
        and all(row["status"] in ("SUCCESS", "INVALID") and type(row["native_calls"]) is int
            and row["native_calls"] == 1 for row in records), "MANUAL_EXACT_SCHEDULED_COMPLETION")


def reconcile(ledger, session, archive, owner_locator, tool_locator, destination, *, mode=DISTINCT_SLUG,
        check_only=False):
    """One truthful COLLECTED; old histories/measure consume it without patching.

    Deliberately no public injection of provider observations or verification
    verdicts. Test doubles replace only the network/authority boundary.
    """
    same = collection_mode(mode)
    require(type(check_only) is bool, "MANUAL_CHECK_ONLY_BOOLEAN")
    archive = Path(archive)
    with lock(ledger.root), lock(session.root):
        events = ledger.events()
        intent = ledger.open_intent()
        require(intent is not None and intent["request"] == session.request, "MANUAL_EXACT_OPEN_INTENT")
        request = intent["request"]
        intent_sha = digest(intent)
        require(not any(e["kind"] in ("PUSH_INTENT", "SUBMITTED") and e["intent_sha256"] == intent_sha
            for e in events), "MANUAL_POSSIBLE_API_SUBMIT_STOP")
        require(not any(e["kind"] == "COLLECTED" and e["sha256"] == sha(archive) for e in events), "MANUAL_DUPLICATE_ARCHIVE")
        tool = tool_release(tool_locator, ledger.grant, mode=mode)
        notebook = approved_source(ledger, request)
        budget = ledger.budget(authenticate=True)
        require(request["bindings"]["runtime"].get("o5_extension") == budget["extension"], "MANUAL_O5_AUTHORITY_DRIFT")
        history, _ = ledger.histories()
        require(request["bindings"]["runtime"]["execution_request"]["history"] == history, "MANUAL_ORIGINAL_HISTORY")
        before = handoff_snapshot(session, request, mode=mode)
        attestation = owner_attestation(owner_locator, ledger, intent, archive, mode=mode)
        require(not same or tool["release"]["owner"] == owner_locator, "MANUAL_REVIEWER_EXACT_OWNER_RELEASE")
        require(not any(e["kind"] == "COLLECTED" and (e["provider"]["job_id"] == attestation["job"]
            or e["provider"].get("kernel_id") == attestation["kernel_id"]
            or e.get("manual", {}).get("owner_locator") == owner_locator) for e in events), "MANUAL_PROVIDER_REPLAY")
        result = runtime.verify_bundle(archive, attestation["archive_sha256"], request["plan"])
        require(result["status"] == "PASS" and result["scope"] == "PRIVATE_TRAIN_METADATA"
            and result["model_calls"] >= 1, "MANUAL_VERIFIED_NATIVE_PASS_REQUIRED")
        campaign.verify_native_custody(request, archive, intent, ledger.grant)
        verify_inputs_in_archive(archive, request)
        ancestor = runtime.sealed_history(archive, attestation["archive_sha256"], request["plan"])
        require(ancestor["parent_history_sha256"] == digest(history), "MANUAL_HISTORY_LINEAGE")
        if same:
            verify_scheduled_completion(request, intent, result, ancestor)
        destination = private_root(destination)
        for protected in (ledger.root, ledger.mirror, session.root):
            require(not destination.resolve().is_relative_to(protected.resolve())
                and not protected.resolve().is_relative_to(destination.resolve()), "MANUAL_INDEPENDENT_EVIDENCE_DIRECTORY")
        destination.mkdir(parents=True, exist_ok=False)
        try:
            client = operator.api()  # existing official pinned SDK, read-only
            sources = operator.input_sources(request)
            args = (client, attestation["job"], 1, notebook, sources)
            provider = observe_kernel(*args, kernel_id=attestation["kernel_id"])
            observed = inventory(client, ledger, intent, attestation["job"], mode=mode)
            capsule = operator.verify_execution_input(client, request, intent, destination / "capsule")
            output = download_outputs(client, attestation["job"], 1, archive, attestation["archive_sha256"], destination)
            require(observe_kernel(*args, kernel_id=attestation["kernel_id"]) == provider, "MANUAL_PROVIDER_CHANGED_DURING_COLLECTION")
            require(inventory(client, ledger, intent, attestation["job"], mode=mode) == observed, "MANUAL_INVENTORY_CHANGED")
            require(handoff_snapshot(session, request, mode=mode) == before and ledger.events() == events, "MANUAL_LOCAL_CUSTODY_CHANGED")
            require(sha(archive) == attestation["archive_sha256"], "MANUAL_ARCHIVE_CHANGED")
            require(approved_source(ledger, request) == notebook
                and tool_release(tool_locator, ledger.grant, mode=mode) == tool
                and owner_attestation(owner_locator, ledger, intent, archive, mode=mode) == attestation,
                "MANUAL_AUTHORITY_CHANGED_DURING_COLLECTION")
            # Keep the verified provider copy in independent create-only local
            # custody, instead of trusting an editable caller ZIP after checking.
            collected = destination / archive.name
            require(sha(collected) == attestation["archive_sha256"]
                == read(str(collected) + ".sha256.json")["sha256"]
                and sha(destination / "provider.log") == output["log_sha256"], "MANUAL_PROVIDER_COPY_CUSTODY_CHANGED")
            provider["notebook_sha256"] = request["notebook_sha256"]  # approved original; remote digest separate
            manual = {"provenance": PROVENANCE, "refund": False, "owner_locator": owner_locator,
                "owner_attestation": attestation, "tool": tool, "handoff": before,
                "inventory": observed, "capsule": capsule, "output": output,
                "original_job": request["job"], "source_sha256": digest(runtime.source_spec()),
                "science_sha256": digest(campaign.science()), "execution_commit": request["commit_sha"]}
            if same:
                manual["mode"] = mode
                require(sha(str(collected) + ".sha256.json") == sha(str(archive) + ".sha256.json"),
                    "MANUAL_PRESERVED_SIDECAR_BYTES")
            require(ledger.histories()[0] == history and ledger.events() == events
                and handoff_snapshot(session, request, mode=mode) == before, "MANUAL_FINAL_LOCAL_CUSTODY_CHANGED")
            write(destination / "verification.json", {"provider": provider, "manual": manual, "verification": result,
                "collection": "NOT_APPENDED_CHECK_ONLY" if check_only else "VERIFIED_BEFORE_APPEND"})
            if check_only:
                return {"status": "READ_ONLY_VERIFIED", "provider": provider, "manual": manual,
                    "sha256": attestation["archive_sha256"], "ledger_appended": False}
            # Write through the existing mirror/fsync/chain mechanism. On a torn
            # second copy, the original Ledger rejects ALL further operations.
            row = ledger.append("COLLECTED", intent_sha256=intent_sha, provider=provider,
                archive=str(collected.resolve()), sha256=attestation["archive_sha256"], plan=request["plan"],
                history=ancestor, verification=result, manual=manual)
            ledger.events()  # both copies must exist before returning success
            return row
        except Exception as error:
            # Do not serialize provider exception text (may contain signed URLs).
            message = str(error)
            code = message if isinstance(error, ValueError) and re.fullmatch(r"[A-Z0-9_:]{1,160}", message) else "PROVIDER_IO_UNVERIFIED"
            write(destination / "BLOCKED.json", {"status": "BLOCKED", "reason_code": code,
                "error_type": type(error).__name__, "automatic_retry": False,
                "action": "READ_ONLY_RECONCILIATION_PARTIALS_PRESERVED"})
            raise ValueError("MANUAL_COLLECTION_BLOCKED:" + code) from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-repo", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--handoff", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--owner-locator", type=Path, required=True)
    parser.add_argument("--tool-locator", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--mode", choices=(DISTINCT_SLUG, SAME_SLUG), default=DISTINCT_SLUG)
    parser.add_argument("--check-only", action="store_true", help="Verify into fresh evidence; do not append any ledger event")
    args = parser.parse_args(argv)
    require(args.approved_repo.resolve() == runtime.ROOT.resolve(), "MANUAL_IMPORT_ROOT_DRIFT")
    row = reconcile(campaign.Ledger(private_root(args.ledger)), Session(args.handoff), args.archive,
        read(args.owner_locator), read(args.tool_locator), args.evidence, mode=args.mode, check_only=args.check_only)
    print(json.dumps({"status": "READ_ONLY_VERIFIED" if args.check_only else "COLLECTED",
        "provenance": PROVENANCE, "mode": args.mode, "event_sha256": None if args.check_only else digest(row),
        "archive_sha256": row["sha256"], "measurement": "NOT_RUN_USE_ORIGINAL_LEDGER_MEASURE"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
