"""PR177 private official-SDK dispatch. Exact release first; never re-submit."""
import argparse
from contextlib import contextmanager
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import queue
import subprocess
import threading
import time
import traceback
import zipfile
from unittest.mock import patch
from safeshift import internvl_v2_campaign as control
from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, safe, verify_archive
from safeshift.pilot.contract import digest

SDK_PINS = {"kaggle": "2.2.5", "kagglesdk": "0.1.38", "requests": "2.34.2"}
# Conservative reservation, not measured usage: two physical T4s, all three slots.
# Failed/short jobs never refund their server-enforced maximum allocation.
JOB_SECONDS = 600
PHYSICAL_GPUS = 2


def gpu_budget(grant):
    slot = grant["slot"]
    control.job(slot)
    require(grant["limits"] == control.LIMITS, "GPU_LIMITS_CHANGED")
    charged = PHYSICAL_GPUS * JOB_SECONDS
    require(slot * charged <= control.LIMITS["physical_gpu_seconds"], "CAMPAIGN_GPU_BUDGET_EXHAUSTED")
    return {"schema": "internvl-v2-gpu-upper-bound-v1", "binding": digest(grant),
        "reviewed_head": grant["reviewed_head"], "slot": slot,
        "accounting": "CONSERVATIVE_SERVER_TIMEOUT_NO_REFUND", "measured_usage": None,
        "machine_shape": "NvidiaTeslaT4", "physical_gpus": PHYSICAL_GPUS,
        "server_timeout_seconds": JOB_SECONDS, "reserved_physical_gpu_seconds": charged,
        "cumulative_reserved_physical_gpu_seconds": slot * charged,
        "campaign_limit_physical_gpu_seconds": control.LIMITS["physical_gpu_seconds"]}


def check_budget(record, grant):
    # Canonical digest also rejects bool/float substitutions for integer seconds.
    require(type(record) is dict and digest(record) == digest(gpu_budget(grant)),
            "MISSING_OR_INVALID_GPU_BUDGET_EVIDENCE")
    return record


def cumulative_budget(grant, prior):
    require(len(prior) == grant["slot"] - 1, "GPU_HISTORY_INCOMPLETE")
    total = 0
    for slot, row in enumerate(prior, 1):
        require(row["slot"] == slot and row["terminal"] in ("COMPLETE", "ERROR", "CANCELLED"),
                "GPU_HISTORY_NOT_SEQUENTIAL_TERMINAL")
        budget = row["gpu_budget"]
        # Each predecessor budget was checked against its original immutable grant.
        require(type(budget["reserved_physical_gpu_seconds"]) is int
                and budget["reserved_physical_gpu_seconds"] == PHYSICAL_GPUS * JOB_SECONDS
                and type(budget["cumulative_reserved_physical_gpu_seconds"]) is int
                and budget["cumulative_reserved_physical_gpu_seconds"] == slot * PHYSICAL_GPUS * JOB_SECONDS,
                "GPU_HISTORY_USAGE_UNKNOWN")
        total += budget["reserved_physical_gpu_seconds"]
    budget = gpu_budget(grant)
    require(total + budget["reserved_physical_gpu_seconds"] == budget["cumulative_reserved_physical_gpu_seconds"]
            <= control.LIMITS["physical_gpu_seconds"], "CAMPAIGN_GPU_BUDGET_EXHAUSTED")
    return budget


def positive_worker_evidence(get, members, grant):
    """Validate successful stages and environment, not mere receipt existence."""
    from scripts.internvl_v2 import policy
    from safeshift.candidates.train_runtime import pins
    budgets = policy()
    for stage in ("setup", "worker", "processor"):
        require(stage + "-supervisor.log" in members, "SUCCESS_STAGE_LOG_REQUIRED")
        row = get(stage + "-supervisor.json")
        require(row["schema"] == "fresh-process-supervision-v1" and row["status"] == "EXITED"
                and type(row["returncode"]) is int and row["returncode"] == 0
                and row["group_kill_sent"] is True and row["automatic_retry"] is False
                and type(row["seconds"]) in (int, float) and math.isfinite(row["seconds"])
                and 0 <= row["seconds"] <= JOB_SECONDS
                and type(row["log_bytes"]) is int and 0 <= row["log_bytes"] <= budgets["max_log_bytes"],
                "SUCCESS_STAGE_TERMINATION_REQUIRED")
    for name in ("resources-memory-before.json", "preload-resources-memory-before.json",
                 "processor-parent-memory-before.json", "processor-parent-memory-after.json",
                 "processor-memory-before.json", "processor-memory-after.json",
                 "owned-advice-memory-before.json", "owned-advice-memory-after.json",
                 "before-checkpoint-memory.json", "after-checkpoint-memory.json"):
        observed = get(name)
        require(observed["schema"] == "internvl-v2-memory-v1" and observed["status"] == "OBSERVED"
                and observed["errors"] == [] and type(observed["pid"]) is int and observed["pid"] > 0
                and observed["process"]["status"]["VmRSS"] >= 0
                and all(type(observed["cgroup"]["memory.stat"][k]) is int
                        and observed["cgroup"]["memory.stat"][k] >= 0 for k in ("anon", "file")),
                "SUCCESS_MEMORY_DIAGNOSTICS")
    child = get("processor-memory-after.json")
    parent = get("processor-parent-memory-after.json")
    require(child["pid"] != parent["pid"] and child["cuda_visible_devices"] == "", "PROCESSOR_LIFETIME_CPU_ISOLATION")
    require(get("preload-resources-memory-before.json")["gate_memory"]["available_bytes"] >= 16 * 2**30,
            "SUCCESS_MEMORY_FLOOR")
    advice = get("owned-venv-advice.json")
    require(advice["deleted_files"] == 0 and advice["scan_complete"] is True
            and advice["method"] in ("POSIX_FADV_DONTNEED_OWNED_VENV_LIB_ONLY", "SKIPPED_NO_FILE_PAGES"),
            "SUCCESS_OWNED_ADVICE_CUSTODY")
    parent = ""
    for phase in ("launch", "setup", "worker"):
        permit = get(phase + "-permit.json")
        require(permit == control.remote_record(phase, grant["slot"])
                and permit["campaign"] == control.CAMPAIGN and permit["slot"] == grant["slot"]
                and permit["binding"] == digest(grant) and permit["phase"] == phase
                and permit["parent_nonce"] == parent, "SUCCESS_WORKER_PERMIT_BINDING")
        parent = permit["nonce"]
    checkpoint = get("checkpoint.json")
    descriptor = read(ROOT / "configs/grammar/internvl35_v2_runtime.json")
    require(checkpoint["status"] == "ACTUAL_BYTES_VERIFIED" and checkpoint["weights_loaded"] is False
            and checkpoint["model"] == descriptor["checkpoint"] and checkpoint["revision"] == descriptor["revision"],
            "SUCCESS_CHECKPOINT_EVIDENCE")
    processor = get("processor.json")
    require(processor["status"] == "CPU_SOFTWARE_PASS" and processor["scope"] == "SYNTHETIC_PROCESSOR_NO_MODEL_FORWARD"
            and processor["loads"] == processor["calls"] == 0 and processor["mask_steps"] == 40
            and processor["logit_width"] == 151936 and processor["tokenizer_size"] == 151679,
            "SUCCESS_PROCESSOR_EVIDENCE")
    software = get("software.json")
    require(software["versions"] == pins("internvl35") and software["cuda_build"] == "12.4"
            and software["compiled_cpu_nms"] == "PASS", "SUCCESS_SOFTWARE_EVIDENCE")
    hardware = get("hardware.json")["physical_gpus"]
    require(len(hardware) == PHYSICAL_GPUS, "SUCCESS_PHYSICAL_GPU_COUNT")
    for i, gpu in enumerate(hardware):
        require(gpu["index"] == i and gpu["name"] in ("Tesla T4", "NVIDIA T4")
                and gpu["driver"] in budgets["driver_versions"]
                and type(gpu["free_mib"]) is int and gpu["free_mib"] >= budgets["free_mib_per_gpu"][i],
                "SUCCESS_GPU_EVIDENCE")
    cuda = get("cuda.json")
    require(cuda["fp16"] == "MEASURED" and cuda["weights_loaded"] is False and len(cuda["gpus"]) == 1
            and cuda["gpus"][0]["index"] == 0
            and type(cuda["gpus"][0]["free_bytes"]) is int
            and cuda["gpus"][0]["free_bytes"] >= budgets["free_gpu0_runtime_mib"] * 2**20,
            "SUCCESS_CUDA_EVIDENCE")
    for name in ("initial-resources.json", "resources.json", "preload-resources.json"):
        resources = get(name)
        require(type(resources["memory"]["available_bytes"]) is int
                and resources["memory"]["available_bytes"] >= budgets["free_ram_mib"] * 2**20,
                "SUCCESS_RAM_EVIDENCE")
        wanted = [budgets[k] * 2**20 for k in ("free_scratch_mib", "free_output_mib")]
        free, devices = resources["free_bytes"], resources["devices"]
        require(len(free) == len(devices) == 2 and all(type(n) is int and n >= 0 for n in free)
                and resources["requested_reserves_bytes"] == wanted
                and (min(free) >= sum(wanted) if devices[0] == devices[1] else all(f >= w for f, w in zip(free, wanted))),
                "SUCCESS_STORAGE_EVIDENCE")
    allocation = get("allocation.json")
    require(allocation["cleanup_verified"] is True and len(allocation["allocations"]) == 2,
            "SUCCESS_ALLOCATION_EVIDENCE")
    for row, size in zip(allocation["allocations"], (budgets["scratch_probe_bytes"], budgets["output_probe_bytes"])):
        require(row["fsync"] is True and row["written_bytes"] == row["requested_bytes"] == size
                and type(row["allocated_bytes"]) is int and row["allocated_bytes"] >= size, "SUCCESS_ALLOCATION_BYTES")


def check_sdk():
    actual = {name: importlib.metadata.version(name) for name in SDK_PINS}
    require(actual == SDK_PINS, "REVIEWED_LOCAL_SDK_PINS_REQUIRED")
    return actual

def authenticated_github_get(path, *, missing=False):
    """Local gh session only. No token retrieval, notebook secret or read retry."""
    require(path.startswith('/') and not path.startswith('//'), 'GITHUB_RELATIVE_API_PATH')
    result = subprocess.run(['gh', 'api', '--include', 'repos/' + control.REPO + path],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    header, separator, body = result.stdout.replace('\r\n', '\n').partition('\n\n')
    require(separator and header.startswith('HTTP/'), 'AUTHENTICATED_GITHUB_RESPONSE_UNKNOWN')
    status = int(header.splitlines()[0].split()[1])
    if status == 404 and missing:
        return None
    require(status == 200 and result.returncode == 0, 'AUTHENTICATED_GITHUB_READ_HTTP_' + str(status))
    require(len(body.encode()) <= 2**20, 'REMOTE_RESPONSE_BOUND')
    return json.loads(body)


def get_kernel(api, ref):
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    request = ApiGetKernelRequest()
    request.user_name, request.kernel_slug = ref.split('/')
    with api.build_kaggle_client() as client:
        return client.kernels.kernels_api_client.get_kernel(request)


@contextmanager
def bounded_http():
    """Official SDK transport, zero automatic retry, finite network waits."""
    import requests
    original = requests.Session.send
    def send(session, request, **kwargs):
        require(all(a.max_retries.total == 0 for a in session.adapters.values()), 'SDK_RETRIES_FORBIDDEN')
        # Setup can be silent for minutes. Only the background SSE reader gets
        # a finite idle read timeout; coordinator wall deadline still caps work.
        kwargs['timeout'] = (10, 90 if '/kernels/logs/stream/' in request.url else 30)
        kwargs['allow_redirects'] = False
        response = original(session, request, **kwargs)
        if '/kernels/logs/stream/' in request.url:
            response.encoding = 'utf-8'
            # requests defaults to 512B buffering. A short challenge must reach
            # the coordinator without waiting for the next permitted phase.
            lines = response.iter_lines
            def immediate_lines(*args, **options):
                options['chunk_size'] = 1
                return lines(*args, **options)
            response.iter_lines = immediate_lines
        return response
    with patch.object(requests.Session, 'send', send):
        yield


def live_identity(api, grant):
    value = get_kernel(api, grant["job"])
    require(value.metadata.ref == grant["job"] and value.metadata.current_version_number == grant['version']
            and value.metadata.is_private is True, 'LIVE_JOB_VERSION_PRIVACY')
    require(control.code_hash(json.loads(value.blob.source)) == grant['notebook_code_sha256'], 'LIVE_JOB_CODE_DRIFT')
    require(value.metadata.machine_shape == "NvidiaTeslaT4", "LIVE_GPU_SHAPE_BUDGET_UNKNOWN")
    return value.metadata.id


def sanitized_failure(failure):
    """No URL, response body, credentials or raw stdout in public error records."""
    chain, seen = [], set()
    while failure is not None and id(failure) not in seen and len(chain) < 5:
        seen.add(id(failure))
        response = getattr(failure, 'response', None)
        chain.append({'type': type(failure).__name__, 'module': type(failure).__module__,
            'message_sha256': hashlib.sha256(str(failure).encode()).hexdigest(),
            'http_status': getattr(response, 'status_code', None),
            'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                       for f in traceback.extract_tb(failure.__traceback__)[-8:]]})
        failure = failure.__cause__ or failure.__context__
    return {'exception_chain': chain, 'message_policy': 'HASH_ONLY_NO_PRIVATE_TEXT'}


def coordinate(api, grant, seconds, evidence=None):
    coordinator = control.Coordinator(grant)
    events = queue.Queue(maxsize=128)
    stop = threading.Event()
    def put(kind, value):
        while not stop.is_set():
            try:
                events.put((kind, value), timeout=.2)
                return
            except queue.Full:
                continue
    def stream():
        # Only re-open the read-only stream. Never restart the coordinator,
        # re-submit a notebook, repeat a permit write or repeat a model call.
        for connection in range(4):
            if stop.is_set():
                return
            put('connection', connection)
            try:
                for item in api.kernels_logs_stream(grant["job"] + '/1'):
                    if stop.is_set():
                        return
                    require(isinstance(item, dict), 'LIVE_EVENT_SHAPE')
                    data = item.get('data')
                    if data is None:  # SDK heartbeat/control event, no stdout.
                        continue
                    require(isinstance(data, str), 'LIVE_LOG_TYPE')
                    put('data', data)
                state = str(api.kernels_status(grant["job"] + '/1').status).split('.')[-1]
                if state in ('COMPLETE', 'ERROR', 'CANCELLED'):
                    put('end', state)
                    return
                require(state in ('RUNNING', 'QUEUED'), 'LIVE_STATUS_UNKNOWN')
                put('disconnect', {'reason': 'EOF_BEFORE_TERMINAL', 'connection': connection})
            except Exception as failure:
                detail = sanitized_failure(failure)
                detail['connection'] = connection
                put('disconnect', detail)
                # Schema/auth failures are not transient connection failures.
                from requests.exceptions import ConnectionError, Timeout, ChunkedEncodingError
                if not isinstance(failure, (ConnectionError, Timeout, ChunkedEncodingError)):
                    put('error', detail)
                    return
            if stop.wait(1):
                return
        put('error', {'reason': 'READ_ONLY_RECONNECT_BUDGET_EXHAUSTED'})
    thread = threading.Thread(target=stream, daemon=True)
    thread.start()
    deadline, pending, total = time.monotonic() + seconds, '', 0
    observations = []
    def observe(value):
        observations.append(value)
        if evidence is not None:
            write(Path(evidence) / ('transport-%03d.json' % len(observations)), value)
    try:
        while time.monotonic() < deadline:
            try:
                kind, value = events.get(timeout=min(5, max(.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if kind in ('connection', 'disconnect', 'error'):
                observe({'kind': kind, 'detail': value, 'permits': list(coordinator.accepted)})
            require(kind != 'error', 'LIVE_LOG_TRANSPORT_ERROR_NO_RETRY')
            if kind == 'connection':
                pending = ''  # Reopened SDK stream replays from beginning.
                continue
            if kind == 'disconnect':
                continue
            if kind == 'end':
                return {'permits': list(coordinator.accepted), 'log_stream': 'ENDED',
                        'terminal': value, 'transport': observations}
            require(isinstance(value, str), 'LIVE_LOG_TYPE')
            total += len(value.encode())
            require(total <= 16 * 2**20, 'LIVE_LOG_LIMIT')
            pending += value
            lines = pending.split('\n')
            pending = lines.pop()
            require(len(pending) <= 2**20, 'LIVE_LOG_LINE_LIMIT')
            # Official SDK events may be complete stdout lines without a newline;
            # do not wait until the next process phase to acknowledge this one.
            if control.PREFIX in pending:
                try:
                    json.loads(pending.split(control.PREFIX, 1)[1])
                except json.JSONDecodeError:
                    pass  # Bounded partial chunk; never guess or repair JSON.
                else:
                    lines.append(pending)
                    pending = ''
            for line in lines:
                if control.PREFIX not in line:
                    continue
                # Kaggle may prefix stdout with a timestamp; the payload has no raw.
                challenge = json.loads(line.split(control.PREFIX, 1)[1])
                live_identity(api, grant)
                coordinator.accept(challenge)
        raise TimeoutError('COORDINATOR_DEADLINE_NO_RETRY')
    except BaseException as failure:
        observe({'kind': 'coordinator-failure', **sanitized_failure(failure),
                 'permits': list(coordinator.accepted)})
        raise
    finally:
        stop.set()


def input_sources(mode):
    datasets = ["nguynanhtn/safeshift-pilot-input"]
    if mode == "native":
        datasets.append("nguynanhtn/inspecsafe-v1-kaggle")
    return datasets, ["nguynanhtn/safeshift-prepare-internvl35",
                      "nguynanhtn/safeshift-issue173-native-smoke-v5"]


def inventory(api, grant):
    owned, tokens, token = set(), set(), None
    for number in range(1, 17):
        page = api.kernels_list_with_response(mine=True, page_size=100,
            page_token=token, page=None if token else number)
        refs = [row.ref for row in page.kernels]
        require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(ref.startswith("nguynanhtn/") for ref in refs), "OWNED_ACCOUNT_OR_DUPLICATE")
        owned.update(refs)
        token = page.next_page_token
        if not token and len(refs) < 100:
            break
        if token:
            require(token not in tokens, "REPEATED_INVENTORY_PAGE")
            tokens.add(token)
    else:
        raise ValueError("INCOMPLETE_INVENTORY")
    require(all(control.job(n) not in owned for n in range(grant["slot"], 4)), "JOB_EXISTS_NO_SUBMISSION")
    inputs = []
    for ref in input_sources(grant["mode"])[1]:
        require(ref in owned, "MISSING_PRIVATE_INPUT")
        value = get_kernel(api, ref)
        require(value.metadata.ref == ref and value.metadata.current_version_number == 1
                and str(api.kernels_status(ref).status).split(".")[-1] == "COMPLETE", "INPUT_VERSION_NOT_COMPLETE")
        inputs.append({"ref": ref, "version": 1, "id": value.metadata.id})
    quota = api.quota_view().gpu_quota
    q = {name: int(getattr(quota, field).total_seconds()) for name, field in (
        ("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
    require(0 <= q["used"] <= q["total"] and q["reserved"] == 0
            and q["total"] - q["used"] >= gpu_budget(grant)["reserved_physical_gpu_seconds"],
            "GPU_QUOTA_OR_CONCURRENT_JOB")
    return {"owned_count": len(owned), "owned_sha256": digest(sorted(owned)), "inputs": inputs,
            "quota_seconds": q, "observed_unix": int(time.time())}


def verify_result(archive, grant, state):
    require(state in ("COMPLETE", "ERROR", "CANCELLED"), "JOB_NOT_TERMINAL")
    submission = control.remote_record("submission", grant["slot"])
    require(submission is not None and submission["grant"] == grant, "GPU_SUBMISSION_EVIDENCE_REQUIRED")
    budget = check_budget(submission.get("gpu_budget"), grant)
    require(sha(archive) == read(Path(str(archive) + ".sha256.json"))["sha256"], "ARCHIVE_SIDECAR")
    members = verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        def get(name):
            require(name in members, "MISSING_POSITIVE_EVIDENCE:" + name)
            return json.loads(bundle.read(name))
        require(get("release.json")["grant"] == grant, "ARCHIVE_RELEASE")
        spec = get("source.json")
        require(digest(spec["manifest"]) == grant["manifest_sha256"]
                and digest(spec) == grant["request"]["source_sha256"], "ARCHIVE_SOURCE")
        start, end, summary = get("campaign-start.json"), get("campaign-end.json"), get("summary.json")
        require(all(v["binding"] == digest(grant) for v in (start, end, summary)), "ARCHIVE_BINDING")
        require(start["native_calls_at_start"] == start["loads_at_start"] == 0
                and start["slot"] == grant["slot"] and start["mode"] == grant["mode"], "POSITIVE_START_LEDGER")
        require(summary["campaign"] == control.CAMPAIGN and summary["slot"] == grant["slot"]
                and summary["mode"] == grant["mode"], "SUMMARY_JOB_IDENTITY")
        call = control.remote_record("call")
        load = control.remote_record("load")
        markers = int("sample/native_call.json" in members)
        reservations = int("sample/reservation.json" in members)
        require(markers == end["native_call_markers"] == summary["native_call_markers"]
                and reservations == end["call_reservations"] == summary["call_reservations"]
                and end["weights_loaded"] == summary["weights_loaded"] == ("loaded.json" in members), "LOCAL_CALL_LEDGER")
        for phase, external in (("load", load), ("call", call)):
            local = phase + "-permit.json" in members
            require(end[phase + "_permit"] == local, "LOCAL_PERMIT_LEDGER")
            if local:
                require(external == get(phase + "-permit.json") == control.remote_record(phase, grant["slot"]),
                        "EXTERNAL_LOCAL_PERMIT_BINDING")
        logs = {n: h for n, h in members.items() if n.endswith(("-supervisor.log", "-supervisor.json"))}
        require(bool(logs), "MISSING_PRIVATE_LOG_CUSTODY")
        for stage in ("setup", "worker"):
            log, receipt = stage + "-supervisor.log", stage + "-supervisor.json"
            if log in members or receipt in members:
                supervised = get(receipt)
                require(log in members and supervised["schema"] == "fresh-process-supervision-v1"
                        and supervised["status"] in ("EXITED", "CHILD_FAILURE", "HARD_DEADLINE",
                            "LOG_BUDGET_EXCEEDED", "SUPERVISOR_EXCEPTION")
                        and supervised["automatic_retry"] is False, "SUPERVISION_CUSTODY")
        zero = (markers == reservations == 0 and call is None and not end["call_permit"])
        if summary["status"] in ("SUCCESS", "INVALID", "LIVE_GPU_PREFLIGHT_PASS"):
            require(summary["error"] is None, "POSITIVE_SUMMARY_WITH_ERROR")
            positive_worker_evidence(get, members, grant)
        if summary["status"] in ("SUCCESS", "INVALID"):
            require(grant["mode"] == "native", "NATIVE_STATUS_MODE")
            result = get("sample/result.json")
            raw = get("sample/raw.json")
            require(markers == reservations == 1 and call is not None and load is not None
                    and end["call_permit"] and end["load_permit"]
                    and result["status"] == summary["status"] and result["raw_sha256"] == members["sample/raw.json"]
                    and raw["hnlo"] is None and result["hnlo"] is None, "NATIVE_RESULT_CUSTODY")
            from safeshift import internvl_v2_runtime as runtime
            request = get("execution-request.json")
            runtime.request_binding(spec, request)
            require(get("original-binding.json") == grant["request"]
                    and digest(request["sample_id"]) == grant["request"]["sample_id_sha256"]
                    and request["image_sha256"] == grant["request"]["image_sha256"]
                    and raw["binding"]["input_sha256"] == request["image_sha256"]
                    and raw["hnlo_status"] == result["hnlo_status"] == runtime.HNLO_STATUS,
                    "NATIVE_ORIGINAL_REQUEST_HNLO")
            for name in ("sample/native.json", "sample/processors.json", "sample/grammar.json"):
                get(name)
        elif summary["status"] == "LIVE_GPU_PREFLIGHT_PASS":
            require(grant["mode"] == "preflight" and zero and load is None
                    and not summary["weights_loaded"] and not any(n.startswith("sample/") for n in members),
                    "PREFLIGHT_NATIVE_CONSUMPTION")
            for name in ("checkpoint.json", "processor.json", "cuda.json", "preload-resources.json", "preflight.json"):
                get(name)
            require(get("original-binding.json") == grant["request"], "PREFLIGHT_ORIGINAL_REQUEST")
            require(get("preflight.json") == {"status": "LIVE_GPU_PREFLIGHT_PASS", "weights_loaded": False,
                "inference_verified": False, "scientific_qualified": False, "loads": 0,
                "calls": 0, "owner_slots_consumed": 0, "native_execution": "BLOCKED"}, "PREFLIGHT_RESULT_CONTRADICTION")
        else:
            require(summary["status"] == "TECHNICAL_ERROR", "UNKNOWN_RESULT_STATUS")
    return {"binding": digest(grant), "slot": grant["slot"], "terminal": state,
        "status": summary["status"] if state == "COMPLETE" else "TECHNICAL_ERROR",
        "internal_status": summary["status"], "mode": grant["mode"], "archive_sha256": sha(archive),
        "logs_sha256": digest(logs), "request_sha256": grant["request_sha256"],
        "manifest_sha256": grant["manifest_sha256"], "calls": markers,
        "weights_loaded": summary["weights_loaded"], "proof": "ZERO_CALL_CONFIRMED" if zero else "CONSUMED_OR_UNKNOWN",
        "members": len(members) + 1, "gpu_budget": budget}


def predecessors(api, grant, directory):
    records = []
    require(control.remote_record("call") is None and control.remote_record("load") is None,
            "CAMPAIGN_NATIVE_ALREADY_RESERVED")
    for slot in range(1, grant["slot"]):
        submission = control.remote_record("submission", slot)
        finished = control.remote_record("finished", slot)
        require(submission is not None and finished is not None, "MISSING_TERMINAL_PREDECESSOR")
        prior = submission["grant"]
        check_budget(submission.get("gpu_budget"), prior)
        check_budget(finished.get("gpu_budget"), prior)
        require(prior["slot"] == slot and prior["job"] == control.job(slot), "PREDECESSOR_IDENTITY")
        state = str(api.kernels_status(control.job(slot) + "/1").status).split(".")[-1]
        live_identity(api, prior)
        archive = safe(directory, control.job(slot).split("/")[1] + ".zip")
        observed = verify_result(archive, prior, state)
        require(observed == finished and digest(finished) == grant["predecessors"][slot-1]
                and finished["proof"] == "ZERO_CALL_CONFIRMED" and not finished["weights_loaded"],
                "ZERO_CALL_REPAIR_NOT_PROVEN")
        records.append(finished)
    if grant["mode"] == "native":
        require(any(r["status"] == "LIVE_GPU_PREFLIGHT_PASS" and r["terminal"] == "COMPLETE"
                    and r["request_sha256"] == grant["request_sha256"]
                    and r["manifest_sha256"] == grant["manifest_sha256"] for r in records),
                "SAME_SOURCE_REQUEST_LIVE_PREFLIGHT_REQUIRED")
    cumulative_budget(grant, records)
    return records


def validate_local_release(comment_id, notebook):
    grant = control.read_grant(comment_id)  # No Kaggle import/API before this gate.
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == grant["reviewed_head"], "LOCAL_REVIEWED_HEAD")
    # Out-of-scope untracked user files may remain; tracked source must be clean.
    require(not subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT),
            "TRACKED_REVIEWED_TREE_DIRTY")
    relative = Path(notebook).resolve().relative_to(ROOT.resolve()).as_posix()
    require(subprocess.check_output(["git", "show", head + ":" + relative], cwd=ROOT) == Path(notebook).read_bytes(),
            "NOTEBOOK_NOT_COMMITTED")
    nb = read(notebook)
    from scripts.build_internvl_v2 import build
    require(sha(notebook) == grant["notebook_sha256"] and control.code_hash(nb) == grant["notebook_code_sha256"]
            and build(grant["runtime_commit"]) == nb, "EXACT_REVIEWED_NOTEBOOK")
    from safeshift.internvl_v2_runtime import source_spec, check_source
    spec = source_spec()
    check_source(spec)
    require(digest(spec["manifest"]) == grant["manifest_sha256"]
            and digest(spec) == grant["request"]["source_sha256"], "EXACT_REVIEWED_SOURCE")
    return grant


def submit(api, grant, comment_id, notebook, stage, predecessor_directory):
    require(validate_local_release(comment_id, notebook) == grant, "SUBMIT_EXACT_RELEASE")
    control.check_head(grant)
    require(all(control.remote_record(n, slot) is None for slot in range(grant["slot"], 4)
                for n in ("submission", "submitted", *control.PHASES, "finished")), "NONEMPTY_LEDGER_NO_RESUBMISSION")
    prior = predecessors(api, grant, predecessor_directory)
    budget = cumulative_budget(grant, prior)
    observed = inventory(api, grant)
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=False)
    write(stage / "inventory.json", observed)
    write(stage / "grant.json", grant)
    write(stage / "gpu-budget.json", budget)
    datasets, kernels = input_sources(grant["mode"])
    write(stage / "kernel-metadata.json", {"id": grant["job"], "title": "SafeShift " + control.CAMPAIGN + " j" + str(grant["slot"]),
        "code_file": "internvl.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_tpu": False, "enable_internet": True, "dataset_sources": datasets,
        "kernel_sources": kernels, "competition_sources": [], "model_sources": []})
    with (stage / "internvl.ipynb").open("xb") as stream:
        stream.write(Path(notebook).read_bytes())
    control.check_head(grant)
    require(time.time() < grant["expires_unix"], "RELEASE_EXPIRED")
    # Exactly one push site. Even an SDK timeout leaves a permanent reservation.
    control.create_record("submission", {"grant": grant, "approval_comment": comment_id,
        "inventory_sha256": digest(observed), "predecessors": prior, "gpu_budget": budget}, grant["reviewed_head"], grant["slot"])
    try:
        response = api.kernels_push(str(stage), timeout=str(budget["server_timeout_seconds"]), acc=budget["machine_shape"])
        write(stage / "submit-return.json", response.to_dict())
        kernel_id = live_identity(api, grant)
        control.create_record("submitted", {"binding": digest(grant), "kernel_id": kernel_id},
                              grant["reviewed_head"], grant["slot"])
        report = coordinate(api, grant, max(.01, grant["expires_unix"] - time.time()), stage)
        write(stage / "coordinator.json", report)
    except BaseException as failure:
        write(stage / "dispatch-error.json", sanitized_failure(failure))
        # Read-only reconciliation is allowed; no permit writer is restarted.
    while time.time() < grant["expires_unix"]:
        state = str(api.kernels_status(grant["job"] + "/1").status).split(".")[-1]
        if state in ("COMPLETE", "ERROR", "CANCELLED"):
            break
        require(state in ("RUNNING", "QUEUED"), "UNKNOWN_JOB_STATE_STOP")
        time.sleep(min(10, max(0, grant["expires_unix"] - time.time())))
    else:
        raise TimeoutError("TERMINAL_UNVERIFIED_NO_RETRY")
    live_identity(api, grant)
    output = stage / "output"
    output.mkdir(exist_ok=False)
    api.kernels_output(grant["job"] + "/1", str(output), file_pattern=r"\.zip(?:\.sha256\.json)?$", quiet=True)
    archive = safe(output, grant["job"].split("/")[1] + ".zip")
    result = verify_result(archive, grant, state)
    write(stage / "verified-result.json", result)
    control.create_record("finished", result, grant["reviewed_head"], grant["slot"])
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approval-comment", type=int, required=True)
    p.add_argument("--notebook", type=Path, required=True)
    p.add_argument("--stage", type=Path, required=True)
    p.add_argument("--predecessor-directory", type=Path, required=True)
    a = p.parse_args(argv)
    with patch.object(control, "public_get", authenticated_github_get):
        grant = validate_local_release(a.approval_comment, a.notebook)
        check_sdk()
        # Official authentication remains local; never logged/exported/notebook-embedded.
        from kaggle import api
        with bounded_http():
            result = submit(api, grant, a.approval_comment, a.notebook, a.stage, a.predecessor_directory)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
