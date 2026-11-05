"""Durable Codex -> agy operations, independent of Kaggle's job lifetime.

No authority is inferred from a handoff manifest. The production adapter is
closed before SDK authentication/submission in this preparation release.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, safe, relative
from safeshift.pilot.contract import digest, require_hash

SCHEMA = "safeshift-agy-handoff-v1"
TERMINAL = ("COMPLETE", "ERROR", "CANCELLED")


@contextmanager
def lock(root, name="operator.lock"):
    """OS process lock: released even on terminal/process death, never unlinked."""
    path = safe(root, name)
    with path.open("a+b") as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("ANOTHER_OPERATOR_ACTIVE") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def private_root(root):
    root = Path(root).absolute()
    relative(root.relative_to(ROOT).as_posix())
    require(root.is_relative_to(ROOT / "data/processed"), "IGNORED_PRIVATE_HANDOFF_ROOT_REQUIRED")
    safe(ROOT, root.relative_to(ROOT).as_posix())
    result = subprocess.run(["git", "check-ignore", "--quiet", str(root / "request.json")],
        cwd=ROOT, capture_output=True, timeout=10)
    require(result.returncode == 0, "PRIVATE_ROOT_MUST_BE_GIT_IGNORED")
    return root


def validate_request(request):
    require(type(request) is dict and set(request) == {"schema", "handoff_id", "scope", "job",
        "version", "commit_sha", "runtime_commit", "notebook", "notebook_sha256", "bindings",
        "limits", "coordinator_required", "execution_release", "plan", "plan_sha256"}, "HANDOFF_FIELDS")
    require(request["schema"] == SCHEMA and re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", request["handoff_id"]), "HANDOFF_ID")
    require(request["scope"] in ("SYNTHETIC_ONLY", "TRAIN3763_PREPARATION", "TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"), "NO_TEST_OR_IMPLICIT_AUTHORITY")
    require(re.fullmatch(r"[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", request["job"]), "EXACT_JOB_REFERENCE")
    require(type(request["version"]) is int and request["version"] >= 1, "EXACT_JOB_VERSION")
    for key in ("commit_sha", "runtime_commit"):
        require(re.fullmatch(r"[0-9a-f]{40}", request[key]), "EXACT_COMMIT")
    relative(request["notebook"])
    require_hash(request["notebook_sha256"])
    require_hash(request["plan_sha256"])
    require(type(request["bindings"]) is dict and set(request["bindings"]) == {
        "dataset", "checkpoint", "source", "runtime", "rights", "scientific_method"}, "EXACT_BINDINGS")
    for value in request["bindings"].values():
        require(type(value) is dict and value, "BINDING_EVIDENCE_REQUIRED")
    limits = request["limits"]
    require(set(limits) == {"monitor_seconds", "max_calls", "job_seconds"}, "EXPLICIT_LIMITS")
    require(type(limits["monitor_seconds"]) is int and 1 <= limits["monitor_seconds"] <= 900,
        "MONITOR_MAX_15_MINUTES")
    require(type(limits["max_calls"]) is int and 0 <= limits["max_calls"] <= 3763
        and type(limits["job_seconds"]) is int and 1 <= limits["job_seconds"] <= 43200, "JOB_LIMITS")
    require(request["coordinator_required"] is False, "CANNOT_DETACH_LIVE_PERMIT_COORDINATOR")
    require(digest(request["plan"]) == request["plan_sha256"], "PLAN_BINDING")
    if request["scope"] == "TRAIN3763_PREPARATION":
        require(request["execution_release"] is None, "PREPARATION_CANNOT_SELF_GRANT")
    if request["scope"] in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
        require(request["execution_release"] is None or (type(request["execution_release"]) is dict
            and set(request["execution_release"]) == {"comment_id", "body_sha256"}), "EXACT_RELEASE_LOCATOR_ONLY")
    if request["scope"] != "SYNTHETIC_ONLY":
        require(600 <= limits["monitor_seconds"] <= 900, "LIVE_MONITOR_10_TO_15_MINUTES")
    return request


def prepare(root, request):
    validate_request(request)
    root = private_root(root)
    root.mkdir(parents=True, exist_ok=False)
    write(root / "request.json", request)
    session = Session(root)
    session.event("PREPARED")
    return session


class Session:
    def __init__(self, root):
        self.root = private_root(root)
        self.request = validate_request(read(self.root / "request.json"))
        self.binding = digest(self.request)

    def events(self):
        entries, previous = [], None
        for number, path in enumerate(sorted(self.root.glob("event-*.json")), 1):
            require(path.name == f"event-{number:05d}.json", "TORN_OR_MISSING_HANDOFF_EVENT")
            row = read(path)
            require(row["binding"] == self.binding and row["previous"] == previous, "HANDOFF_CHAIN_BINDING")
            entries.append(row)
            previous = digest(row)
        return entries

    def event(self, status, **values):
        entries = self.events()
        value = {"schema": SCHEMA, "binding": self.binding, "previous": digest(entries[-1]) if entries else None,
            "utc": datetime.now(timezone.utc).isoformat(), "status": status, **values}
        write(self.root / f"event-{len(entries)+1:05d}.json", value)
        return value

    def conversation(self):
        values = [r["conversation_id"] for r in self.events() if r.get("conversation_id")]
        return values[-1] if values else None

    def report(self, status, **values):
        entries = self.events()
        report = {"schema": SCHEMA + "-report", "status": status, "binding": self.binding,
            "handoff_id": self.request["handoff_id"], "job_id": self.request["job"],
            "version": self.request["version"], "commit_sha": self.request["commit_sha"],
            "runtime_commit": self.request["runtime_commit"], "notebook_sha256": self.request["notebook_sha256"],
            "conversation_id": self.conversation(), "scope": self.request["scope"],
            "independent_audit": "NOT_PERFORMED_OPERATIONAL_REPORT_ONLY",
            "scientific_qualified": False, **values}
        path = self.root / f"report-{len(entries)+1:05d}.json"
        write(path, report)
        self.event(status, report_path=path.name, report_sha256=sha(path))
        return report

    def latest_report(self):
        for row in reversed(self.events()):
            if "report_path" in row:
                path = safe(self.root, row["report_path"])
                require(sha(path) == row["report_sha256"], "REPORT_HASH_DRIFT")
                return read(path)
        return None


def operate(session, operator, action, *, clock=time.monotonic, sleep=time.sleep):
    """The AI calls one deterministic step; no provider retry/cancel in this API."""
    require(action in ("start", "collect"), "OPERATION_ACTION")
    with lock(session.root):
        try:
            request = session.request
            if hasattr(operator, "local_root"):
                operator.local_root = session.root
            if action == "start":
                require(not any(e["status"] == "SUBMISSION_INTENT" for e in session.events()),
                        "SUBMISSION_ALREADY_RESERVED_NO_RETRY")
                operator.preflight(request)
                session.event("SUBMISSION_INTENT")  # BEFORE any possible external push
                job = operator.submit(request)
                require(job == {"job_id": request["job"], "version": request["version"]}, "SUBMITTED_JOB_BINDING")
                session.event("SUBMITTED", **job)
                deadline = clock() + request["limits"]["monitor_seconds"]
            else:
                require(any(e["status"] == "SUBMISSION_INTENT" for e in session.events()), "NO_SUBMISSION_TO_RECONCILE")
                deadline = clock()  # user message triggers a fresh real status check, never blind download
            while True:
                identity = operator.identity(request)
                require(all(identity[k] == value for k, value in {"job_id": request["job"],
                    "version": request["version"], "notebook_sha256": request["notebook_sha256"]}.items()),
                    "REMOTE_VERSION_SOURCE_DRIFT")
                state = operator.status(request)
                session.event("OBSERVED", terminal=state, identity=identity)
                if state in TERMINAL:
                    break
                require(state in ("QUEUED", "RUNNING"), "UNKNOWN_JOB_STATE_NO_RETRY")
                # Two sequential bounded SDK reads can take60s. Stop polling
                # with75s headroom (including the next10s sleep), so a new
                # pair of reads cannot extend the15-minute window.
                if clock() >= deadline - 75:
                    return session.report("RUNNING_UNVERIFIED", terminal=state, collection="NOT_ATTEMPTED",
                        kernel_id=identity.get("kernel_id"),
                        job_cancelled=False, automatic_retry=False)
                sleep(min(10, max(0, deadline - clock())))
            # Each collection has a fresh destination; prior partials/failures survive.
            destination = session.root / ("collection-" + uuid.uuid4().hex)
            destination.mkdir()
            operator.download(request, destination)
            verified = operator.verify(request, destination, state)
            require(verified["status"] in ("PASS", "FAIL", "BLOCKED"), "VERIFIER_VERDICT")
            evidence = {p.relative_to(session.root).as_posix(): sha(p)
                for p in destination.rglob("*") if p.is_file()}
            require(evidence, "NO_COLLECTED_EVIDENCE")
            status = verified["status"] if state == "COMPLETE" else "FAIL"
            return session.report(status, terminal=state, verification=verified, evidence=evidence,
                kernel_id=identity.get("kernel_id"),
                collection="FINISHED", job_cancelled=False, automatic_retry=False)
        except Exception as error:
            # Full private transport/agent logs live locally; reports omit sensitive exception text.
            return session.report("BLOCKED", reason=type(error).__name__,
                error_sha256=hashlib.sha256(str(error).encode()).hexdigest(),
                reason_code=str(error) if re.fullmatch(r"[A-Z0-9_: -]{1,150}", str(error)) else "SEE_PRIVATE_LOGS",
                automatic_retry=False, job_cancelled=False)


class Train3763Operator:
    """Only a new reviewed release can implement/activate submission authority.

    Read-only SDK collection is present for future exact-release integration;
    the current preparation cannot produce a submission intent for this adapter.
    """
    local_root = None

    def preflight(self, request):
        if request["scope"] not in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
            from safeshift.internvl3763 import authorize
            authorize()
        from safeshift.internvl3763_operator import admit
        self.grant, self.execution = admit(request)

    def submit(self, request):
        if not hasattr(self, "grant"):
            self.preflight(request)
        from safeshift.internvl3763_operator import submit
        require(self.local_root is not None, "DURABLE_HANDOFF_SESSION_REQUIRED")
        return submit(request, self.grant, self.execution, self.local_root)

    def _api(self):
        from scripts.submit_internvl_v2 import check_sdk
        check_sdk()
        from kaggle import api
        return api

    def identity(self, request):
        from scripts.submit_internvl_v2 import get_kernel, bounded_http
        from safeshift.internvl_v2_campaign import code_hash
        with bounded_http():
            value = get_kernel(self._api(), request["job"])
        require(value.metadata.ref == request["job"] and value.metadata.is_private is True,
            "KAGGLE_JOB_PRIVACY_IDENTITY")
        if request["scope"] == "TRAIN3763_CAMPAIGN":
            content = subprocess.check_output(["git", "show", request["commit_sha"]+":"+request["notebook"]], cwd=ROOT)
            require(hashlib.sha256(content).hexdigest() == request["notebook_sha256"], "PINNED_COLLECT_NOTEBOOK")
            notebook = json.loads(content)
        else:
            path = safe(ROOT, request["notebook"])
            require(sha(path) == request["notebook_sha256"], "KAGGLE_SOURCE_DRIFT")
            notebook = read(path)
        require(code_hash(json.loads(value.blob.source)) == code_hash(notebook), "KAGGLE_SOURCE_DRIFT")
        if request["scope"] in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
            from safeshift.internvl3763_operator import input_sources
            sources = input_sources(request)
            require(value.metadata.machine_shape == "NvidiaTeslaT4"
                and sorted(value.metadata.dataset_data_sources) == sorted(sources["dataset_sources"])
                and sorted(value.metadata.kernel_data_sources) == sorted(sources["kernel_sources"]),
                "REMOTE_ACCELERATOR_OR_INPUT_DRIFT")
        return {"job_id": request["job"], "version": value.metadata.current_version_number,
            "kernel_id": value.metadata.id, "notebook_sha256": request["notebook_sha256"]}

    def status(self, request):
        from scripts.submit_internvl_v2 import bounded_http
        with bounded_http():
            return str(self._api().kernels_status(request["job"] + "/" + str(request["version"])).status).split(".")[-1]

    def download(self, request, destination):
        from scripts.submit_internvl_v2 import bounded_http
        with bounded_http():
            self._api().kernels_output(request["job"] + "/" + str(request["version"]),
                str(destination), quiet=True, file_pattern=r"\.zip(?:\.sha256\.json)?$")
            # SDK also exports the version-specific provider log. All worker/raw
            # receipts live inside the one contract ZIP, avoiding a second copy.

    def verify(self, request, destination, state):
        from safeshift.internvl3763 import verify_bundle
        bundles = list(destination.glob("*.zip"))
        require(len(bundles) == 1, "EXACTLY_ONE_CONTRACT_ARCHIVE")
        archive = bundles[0]
        if request["scope"] in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
            require(list(destination.glob("*.log")), "PROVIDER_LOG_REQUIRED")
        result = verify_bundle(archive, read(str(archive) + ".sha256.json")["sha256"], request["plan"])
        require(result["scope"] == "PRIVATE_TRAIN_METADATA", "NO_SYNTHETIC_PRODUCTION_PASS")
        if request["scope"] in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
            from safeshift.internvl3763_operator import verify_remote_custody
            result["remote_custody"] = verify_remote_custody(request, archive,
                provider={"state": state, **self.identity(request)})
        return result


def invoke_agy(session, *, resume=False, recover=False, agy="agy", run=subprocess.run):
    # Separate from the operation lock: the child must be able to execute step,
    # but a second AI turn must not race or fork the active conversation.
    with lock(session.root, "agy.lock"):
        return _invoke_agy(session, resume=resume, recover=recover, agy=agy, run=run)


def _invoke_agy(session, *, resume=False, recover=False, agy="agy", run=subprocess.run):
    """A bounded foreground turn. Only the provider job survives between turns."""
    with lock(session.root):
        events = session.events()
        if not resume:
            require(not any(e["status"] == "AGY_INVOCATION_INTENT" for e in events), "NO_DUPLICATE_HANDOFF")
        conversation = session.conversation() if resume else None
        require(not resume or conversation or recover, "CONVERSATION_MISSING_USE_READ_ONLY_RECOVERY")
        version = run([agy, "--version"], capture_output=True, text=True, timeout=10)
        require(version.returncode == 0 and version.stdout.strip() == "1.5.0", "AGY_1_5_0_REQUIRED")
        turn = len([e for e in events if e["status"] == "AGY_INVOCATION_INTENT"]) + 1
        phase = "collect" if resume else "start"
        root = session.root.relative_to(ROOT).as_posix()
        require(re.fullmatch(r"[A-Za-z0-9_./-]+", root), "SHELL_SAFE_RELATIVE_HANDOFF_DIRECTORY")
        step_python = "python"
        if session.request["scope"] in ("TRAIN3763_EXECUTION_CANDIDATE", "TRAIN3763_CAMPAIGN"):
            executable = Path(sys.executable).resolve()
            require(executable.is_relative_to(ROOT.resolve()), "ISOLATED_OPERATOR_PYTHON_REQUIRED")
            step_python = "./" + executable.relative_to(ROOT.resolve()).as_posix()
            require(re.fullmatch(r"[A-Za-z0-9_./-]+", step_python), "SHELL_SAFE_OPERATOR_PYTHON_REQUIRED")
        step_command = step_python + " -B -m scripts.kaggle_handoff step --directory " + root + " --action " + phase
        if session.request["scope"] == "SYNTHETIC_ONLY":
            step_command += " --synthetic"
        # Per-turn, exact-command permission only. Preserve configured deny/ask
        # precedence; never enable a blanket toolPermission or skip-permissions.
        settings_path = Path.home() / ".gemini/antigravity-cli/settings.json"
        permissions = read(settings_path).get("permissions", {}) if settings_path.is_file() else {}
        permissions = {k: list(v) for k, v in permissions.items()}
        permissions["allow"] = [*permissions.get("allow", []),
            "command(regex:^" + re.escape(step_command) + "$)"]
        settings = session.root / f"agy-{turn:03d}.settings.json"
        write(settings, {"permissions": permissions})
        prompt = (
            "You are the SafeShift Kaggle operator, not its independent auditor. Read AGENTS.md, "
            "docs/INTERNVL3763_ANTIGRAVITY.md and " + root + "/request.json. "
            "Use only the current exact release or bounded campaign grant; never infer rights from hashes or this prompt. "
            "Do not modify science/source/privacy/credentials or run TEST; full TRAIN operations require the "
            "corresponding authenticated campaign grant or exact legacy release. "
            "Do not cancel kernels, resubmit, retry unknown calls, or start any background AI process. "
            "Run the deterministic operation exactly once, with RunCommand Cwd set to " + str(ROOT) + ": "
            + step_command + ". Do not wrap it in cd, shell expressions, or other commands. "
            "After it returns, use that JSON output as your final response and end immediately. "
            "Do not run extra checks (including python -c/import probes), do not re-open/read reports with "
            "shell commands, and do not call any further tool after the deterministic command. "
            "Initial monitoring is capped at900 seconds; RUNNING_UNVERIFIED means stop this turn, "
            "keep the remote job alive, and wait for the user. On collect, check live terminal status first. "
            "Download all contract evidence only after terminal; verify ZIP/SHA/CRC/member/source/runtime/"
            "call/raw/status bindings. Preserve failures/partials privately. Report PASS/FAIL/BLOCKED and paths. "
            "If blocked, diagnose from the existing evidence only, never launch a new experiment. "
            "TRAIN3763_PREPARATION stays BLOCKED. TRAIN3763_EXECUTION_CANDIDATE needs a new authentic "
            "Owner release, exact source/SDK/Inputs/caps and permanent remote claims; never create authority yourself. "
            "TRAIN3763_CAMPAIGN uses one authentic campaign grant, reviewed technical source and the sole operator's "
            "mirrored ledger. No per-job Owner approval or HTTPS witness is required; unknown intent means read-only STOP. "
            "For a SYNTHETIC_ONLY request the command already includes --synthetic; this is an operations rehearsal "
            "with no dataset, GPU or model calls. Do not edit the simulated provider state. "
            + ("This is read-only recovery; never submit even if the old conversation is unavailable. " if resume else "")
        )
        argv = [agy, "-p", prompt, "--output-format", "json", "--disable-slash-commands",
                "--settings", str(settings), "--add-dir", str(ROOT), "--print-timeout", "930s"]
        if conversation:
            argv += ["--conversation", conversation]
        session.event("AGY_INVOCATION_INTENT", phase=phase, turn=turn)
        intent_number = len(session.events())
        # Reserve/persist BEFORE spawning. A timeout/crash never enables an initial replay.
        stdout = session.root / f"agy-{turn:03d}.json"
        stderr = session.root / f"agy-{turn:03d}.stderr.log"
    # Do not hold the lock while agy executes a deterministic step in another process.
    try:
        with stdout.open("xb") as output, stderr.open("xb") as errors:
            result = run(argv, cwd=ROOT, stdout=output, stderr=errors, timeout=950)
        require(stdout.stat().st_size <= 4 * 2**20, "AGY_JSON_BOUND")
        envelope = read(stdout)
        cid = envelope.get("conversation_id")
        require(isinstance(cid, str) and re.fullmatch(r"[a-f0-9-]{36}", cid), "AGY_CONVERSATION_ID_REQUIRED")
        require(not conversation or cid == conversation, "AGY_CONVERSATION_DRIFT")
        with lock(session.root):
            session.event("AGY_RETURNED", conversation_id=cid, turn=turn,
                cli_status=envelope.get("status"), stdout_sha256=sha(stdout), returncode=result.returncode)
            require(result.returncode == 0 and envelope.get("status") == "SUCCESS", "AGY_TURN_FAILED_NO_RETRY")
            require(not envelope.get("denied_actions"), "AGY_PERMISSION_DENIED")
            require(any("report_path" in e for e in session.events()[intent_number:-1]),
                "AGY_SUCCESS_WITHOUT_FRESH_OPERATION_REPORT")
            report = session.latest_report()
            require(report is not None, "AGY_SUCCESS_WITHOUT_OPERATION_REPORT")
            # Add conversation binding without mutating the original operation receipt.
            return session.report(report["status"], operation_report_sha256=digest(report),
                operation_report=report)
    except Exception as error:
        with lock(session.root):
            return session.report("BLOCKED", reason="AGY_TURN_UNKNOWN_NO_AUTOMATIC_RETRY",
                reason_code=str(error) if re.fullmatch(r"[A-Z0-9_]{1,150}", str(error)) else "SEE_PRIVATE_LOGS",
                error_type=type(error).__name__, stdout_path=stdout.name, stderr_path=stderr.name)


def accept_report(session):
    """Codex admission: rehash files once, delegate semantic checks to bound verifier."""
    report = session.latest_report()
    require(report is not None and report["binding"] == session.binding, "MISSING_BOUND_REPORT")
    operation = report.get("operation_report", report)
    if "operation_report" in report:
        require(report["operation_report_sha256"] == digest(operation)
            and report["status"] == operation["status"], "OPERATION_REPORT_BINDING")
    require(all(operation[k] == report[k] == value for k, value in {
        "binding": session.binding, "commit_sha": session.request["commit_sha"],
        "runtime_commit": session.request["runtime_commit"], "notebook_sha256": session.request["notebook_sha256"],
        "job_id": session.request["job"], "version": session.request["version"]}.items()), "REPORT_IDENTITY")
    for path, expected in operation.get("evidence", {}).items():
        require(sha(safe(session.root, path)) == expected, "COLLECTED_EVIDENCE_DRIFT")
    if operation["status"] == "PASS":
        require(operation["terminal"] == "COMPLETE" and operation["collection"] == "FINISHED"
            and operation["verification"]["status"] == "PASS" and operation["evidence"], "PASS_WITHOUT_VERIFIED_COLLECTION")
    return report
