"""Exact-release official SDK submit, separate from historical PR177 campaigns."""
import importlib.metadata
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from contextlib import contextmanager, ExitStack
from urllib.parse import urlsplit
from unittest.mock import patch

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, write_bytes, safe, sha
from safeshift.pilot.contract import digest
from safeshift import internvl3763_release as authority

SDK_PINS = {"kaggle": "2.2.5", "kagglesdk": "0.1.38", "requests": "2.34.2"}


def campaign_ledger(request):
    from safeshift.internvl3763_campaign import Ledger
    from safeshift.kaggle_handoff import private_root
    path = private_root(safe(ROOT, request["bindings"]["runtime"]["campaign_ledger"]))
    return Ledger(path)


def admit_campaign(request):
    from safeshift import internvl3763_campaign as campaign
    grant = campaign.load(request.get("execution_release"))  # before any SDK/private Input
    require(time.time()+request["plan"]["max_seconds"]+120 < grant["expires_unix"], "FULL_CAMPAIGN_JOB_WINDOW")
    execution = campaign.bind(grant, request)
    ledger = campaign_ledger(request)
    require(ledger.grant == grant, "CAMPAIGN_LEDGER_GRANT_DRIFT")
    require(ledger.registration["operator_id"] == grant["operator_id"]
        and str(ledger.root.resolve()) == ledger.registration["root"], "CROSS_MACHINE_TAKEOVER_BLOCKED")
    intent = ledger.open_intent()
    require(intent is not None and intent["request"] == request, "STAGED_CAMPAIGN_INTENT_REQUIRED")
    require(not any(x["kind"] == "PUSH_INTENT" and x["intent_sha256"] == digest(intent) for x in ledger.events()),
        "POSSIBLE_SUBMIT_NO_RETRY")
    revision = campaign.revision(grant, request)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == revision["merged_sha"] and not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT), "CLEAN_REVIEWED_CAMPAIGN_SOURCE")
    notebook = safe(ROOT, request["notebook"])
    require(sha(notebook) == revision["notebook_sha256"] and code_hash(read(notebook)) == revision["notebook_code_sha256"]
        and notebook.read_bytes() == subprocess.check_output(["git", "show", head+":"+request["notebook"]], cwd=ROOT),
        "CAMPAIGN_COMMITTED_NOTEBOOK")
    from scripts.build_internvl3763 import build
    require(read(notebook) == build(request["runtime_commit"], execute=True, campaign=True), "CAMPAIGN_NOTEBOOK_REPRODUCIBILITY")
    history, custody = ledger.histories()
    require(execution["history"] == history, "CAMPAIGN_COMPLETE_SEALED_HISTORY")
    for ancestor, item in zip(history, custody):
        require(ancestor["evidence_sha256"] == item["sha256"], "CAMPAIGN_HISTORY_CUSTODY")
    check_sdk()
    return grant, execution


def campaign_inventory(client, request, grant, ledger):
    """Reuse pinned inventory/Input/quota checks, then inspect every campaign job.

    No prior output success or account quota counter alone proves terminal state.
    """
    caps = grant["caps"]
    pushed = {x["intent_sha256"] for x in ledger.events() if x["kind"] == "PUSH_INTENT"}
    known = {x["request"]["job"] for x in ledger.intents() if digest(x) in pushed}
    observed = inventory(client, request, {"caps": {"attempt_gpu_seconds": request["plan"]["max_seconds"]*caps["physical_gpus"]},
        "predecessors": []}, campaign_prefix="nguynanhtn/safeshift-train3763-"+grant["campaign_id"]+"-", known_jobs=known)
    from scripts.submit_internvl_v2 import bounded_http, get_kernel
    for previous in ledger.intents():
        old = previous["request"]
        if old == request:
            continue
        aborted = any(x["kind"] == "ABORTED_PRE_SUBMIT" and x["intent_sha256"] == digest(previous) for x in ledger.events())
        if aborted:
            continue
        with bounded_http():
            state = str(client.kernels_status(old["job"]+"/1").status).split(".")[-1]
            remote = get_kernel(client, old["job"])
        require(state in ("COMPLETE", "ERROR", "CANCELLED") and remote.metadata.ref == old["job"]
            and remote.metadata.is_private is True and remote.metadata.current_version_number == 1
            and code_hash(json.loads(remote.blob.source)) ==
                campaign_revision_code(ledger.grant, old), "PREVIOUS_JOB_RUNNING_UNKNOWN_OR_CHANGED")
    return observed


def campaign_revision_code(grant, request):
    from safeshift.internvl3763_campaign import revision
    return revision(grant, request)["notebook_code_sha256"]


def pre_submit_inventory(ledger, intent):
    """Read-only provider proof; deliberately does not admit the old source at HEAD."""
    from safeshift import internvl3763_campaign as campaign
    require(campaign.load(intent["request"]["execution_release"], collection=True) == ledger.grant,
        "RECOVERY_CAMPAIGN_GRANT_DRIFT")
    observed = campaign_inventory(api(), intent["request"], ledger.grant, ledger)
    return {"job": intent["request"]["job"], "intent_sha256": digest(intent),
        "job_absent": True, "inventory": observed}


@contextmanager
def capsule_http(query):
    """One exact SDK download RPC may turn a 302 into one anonymous storage GET.

    Nested inside bounded_http; ordinary metadata/submit/legacy traffic retains
    its no-redirect policy. Never delegate to the SDK's retrying file writer.
    """
    import requests
    bounded_send = requests.Session.send
    endpoint = "https://api.kaggle.com/v1/datasets.DatasetApiService/DownloadDataset"
    used = False
    stack = ExitStack()

    def send(session, request, **kwargs):
        nonlocal used
        if request.url != endpoint:
            return bounded_send(session, request, **kwargs)
        require(not used and request.method == "POST"
            and json.loads(request.body) == query.to_dict(), "EXACT_CAPSULE_DOWNLOAD_RPC_ONLY")
        used = True
        response = bounded_send(session, request, **{**kwargs, "stream": True})
        if response.status_code != 302:
            response.headers["Content-Type"] = "application/octet-stream"
            return response
        location = response.headers.get("Location", "")
        response.close()
        # Only Kaggle's GCS object-download host, never suffix/wildcard matching.
        # Keep the signed URL opaque; only inspect its authority, not its query.
        try:
            target = urlsplit(location)
            valid = (target.scheme == "https" and target.netloc == "storage.googleapis.com"
                and target.path.startswith("/") and target.path != "/" and target.query
                and not target.fragment and not any(ord(c) <= 32 or ord(c) == 127 for c in location)
                and "\\" not in location)
            require(valid, "UNSAFE_CAPSULE_REDIRECT")
            storage = stack.enter_context(requests.Session())
            storage.trust_env = False  # no netrc, proxy credentials or environment CA bypass
            anonymous = requests.Request("GET", location, headers={"Accept-Encoding": "identity"}).prepare()
            result = bounded_send(storage, anonymous, stream=True, verify=True, cert=None, proxies={})
            if result.status_code != 200:
                result.close()
                raise ValueError("CAPSULE_STORAGE_STATUS_OR_REDIRECT_CHAIN")
            # SDK otherwise tries JSON decoding before our streaming byte cap.
            result.headers["Content-Type"] = "application/octet-stream"
            return result
        except Exception:
            # requests exceptions contain signed URLs. Never persist them in a
            # handoff traceback, chained exception, receipt or console message.
            raise ValueError("CAPSULE_STORAGE_DOWNLOAD_FAILED_NO_RETRY") from None

    with stack, patch.object(requests.Session, "send", send):
        yield
    require(used, "CAPSULE_DOWNLOAD_TRANSPORT_NOT_OBSERVED")


def download_capsule(client, owner, slug, version, name, destination):
    """Pinned official SDK serialization/auth, bounded streaming, no retry/resume."""
    import os
    from kagglesdk.datasets.types.dataset_api_service import ApiDownloadDatasetRequest
    query = ApiDownloadDatasetRequest()
    query.owner_slug, query.dataset_slug = owner, slug
    query.dataset_version_number, query.file_name = int(version), name
    started = time.monotonic()
    try:
        with client.build_kaggle_client() as remote, capsule_http(query):
            require(remote.http_client()._verbose is False, "CAPSULE_SDK_VERBOSE_FORBIDDEN")
            with remote.datasets.dataset_api_client.download_dataset(query) as response:
                require(response.status_code == 200, "CAPSULE_HTTP_STATUS")
                # Detect wrappers from bytes below, never from an untrusted URL.
                path = destination / "download.part"
                total = 0
                with path.open("xb") as stream:
                    for chunk in response.iter_content(64*1024):
                        total += len(chunk)
                        require(total <= 64*2**20 and time.monotonic()-started <= 90, "CAPSULE_DOWNLOAD_BOUND")
                        stream.write(chunk)
                    stream.flush()
                    os.fsync(stream.fileno())
                require(time.monotonic()-started <= 90, "CAPSULE_DOWNLOAD_DEADLINE")
                return path
    except Exception:
        raise ValueError("CAPSULE_DOWNLOAD_FAILED_NO_RETRY_PARTIAL_PRESERVED") from None


def verify_execution_input(client, request, intent, destination):
    """Read the exact small capsule version BEFORE push, preventing stale replay.

    Existence alone is insufficient: an old, otherwise valid campaign capsule
    could run already-consumed images on a fresh VM. No images/raw/weights download.
    """
    import zipfile
    from safeshift.pilot.contract import json_bytes
    from scripts.submit_internvl_v2 import bounded_http
    from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetMetadataRequest
    capsule = request["bindings"]["runtime"]["execution_input"]
    require(capsule["kind"] == "dataset_sources", "DATASET_CAPSULE_ONLY")
    owner, slug, version = capsule["ref"].split("/")
    expected = json_bytes({"request": request, "campaign_intent": intent})
    require(len(expected) <= 64*2**20, "CAPSULE_SIZE_BOUND")
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    name = "safeshift_train3763_execution.json"
    with bounded_http():
        query = ApiGetDatasetMetadataRequest()
        query.owner_slug, query.dataset_slug = owner, slug
        with client.build_kaggle_client() as remote:
            metadata = remote.datasets.dataset_api_client.get_dataset_metadata(query)
        require(not metadata.error_message and metadata.info.is_private is True
            and metadata.info.owner_user == owner and metadata.info.dataset_slug == slug, "CAPSULE_PRIVATE_OWNER_IDENTITY")
        files = client.dataset_list_files(capsule["ref"], page_size=16)
        require(not files.error_message and not files.next_page_token and len(files.files) == 1
            and files.files[0].name == name and files.files[0].total_bytes == len(expected), "CAPSULE_EXACT_FILE_SIZE")
        download_capsule(client, owner, slug, version, name, destination)
    paths = list(destination.iterdir())
    require(len(paths) == 1, "ONE_DOWNLOADED_CAPSULE_FILE")
    path = paths[0]
    if not zipfile.is_zipfile(path):
        require(path.stat().st_size == len(expected), "CAPSULE_DOWNLOAD_BOUND")
        payload = path.read_bytes()
    else:
        require(path.stat().st_size <= 64*2**20, "CAPSULE_WRAPPER_BOUND")
        with zipfile.ZipFile(path) as bundle:
            entries = bundle.infolist()
            require(len(entries) == 1 and entries[0].filename == name and entries[0].file_size == len(expected)
                and bundle.testzip() is None, "CAPSULE_WRAPPER_INTEGRITY")
            payload = bundle.read(name)
    require(payload == expected, "STALE_OR_WRONG_CAPSULE_NO_GPU_SUBMIT")
    proof = {"ref": capsule["ref"], "version": int(version), "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload), "request_sha256": digest(request), "intent_sha256": digest(intent)}
    write(destination.parent / "input-proof.json", proof)
    return proof


def submit_campaign(request, grant, execution, root):
    from safeshift.kaggle_handoff import lock
    ledger = campaign_ledger(request)
    # Campaign lock is held across the only external POST. The durable push
    # intent survives a hard kill/ambiguous return; a second handoff cannot push.
    with lock(ledger.root):
        require(admit_campaign(request) == (grant, execution), "CAMPAIGN_SUBMIT_SOURCE_DRIFT")
        client = api()
        observed = campaign_inventory(client, request, grant, ledger)
        intent = ledger.open_intent()
        stage = Path(root) / "submission"
        require(not stage.exists(), "STALE_SUBMISSION_PRESERVED_ABORT_AND_STAGE_NEW_ATTEMPT")
        stage.mkdir(exist_ok=False)
        write(stage / "inventory.json", observed)
        write(stage / "release.json", grant)
        write(stage / "campaign-intent.json", intent)
        verify_execution_input(client, request, intent, stage / "input-proof")
        sources = input_sources(request)
        write(stage / "kernel-metadata.json", {"id": request["job"], "title": request["job"].split("/")[1],
            "code_file": "internvl.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
            "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
            "dataset_sources": sources["dataset_sources"], "kernel_sources": sources["kernel_sources"],
            "competition_sources": [], "model_sources": []})
        write_bytes(stage / "internvl.ipynb", safe(ROOT, request["notebook"]).read_bytes())
        ledger.append("PUSH_INTENT", intent_sha256=digest(intent), inventory_sha256=digest(observed))
        from scripts.submit_internvl_v2 import bounded_http
        with bounded_http():
            response = client.kernels_push(str(stage), timeout=str(request["plan"]["max_seconds"]), acc=grant["caps"]["machine_shape"])
        write(stage / "submit-return.json", response.to_dict())
        result = {"job_id": request["job"], "version": 1}
        ledger.append("SUBMITTED", intent_sha256=digest(intent), result=result)
        return result


def check_sdk():
    actual = {name: importlib.metadata.version(name) for name in SDK_PINS}
    require(actual == SDK_PINS, "REVIEWED_LOCAL_SDK_PINS_REQUIRED_USE_ISOLATED_VENV")
    return actual


def api():
    check_sdk()  # before Kaggle import/authentication
    from kaggle import api as official
    return official


def input_sources(request):
    value = request["bindings"]["dataset"]
    require(set(value) == {"dataset_sources", "kernel_sources", "execution_request_sha256"}, "EXACT_INPUT_SOURCES_REQUIRED")
    from safeshift.pilot.contract import require_hash
    require_hash(value["execution_request_sha256"])
    require(value["execution_request_sha256"] == digest(request["bindings"]["runtime"]["execution_request"]),
        "EXECUTION_INPUT_CONTENT_BINDING")
    for key in ("dataset_sources", "kernel_sources"):
        refs = value[key]
        require(type(refs) is list and len(refs) <= 16 and len(refs) == len(set(refs)), "BOUNDED_UNIQUE_INPUT_SOURCES")
        for ref in refs:
            require(type(ref) is str and re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*", ref),
                "VERSIONED_INPUT_REFERENCE_REQUIRED")
    require(value["dataset_sources"] or value["kernel_sources"], "MISSING_INPUT")
    return value


def code_hash(notebook):
    return digest([{"cell_type": c["cell_type"], "source": "".join(c["source"])}
        for c in notebook["cells"] if c["cell_type"] == "code"])


def admit(request):
    if request["scope"] == "TRAIN3763_CAMPAIGN":
        return admit_campaign(request)
    require(request["scope"] == "TRAIN3763_EXECUTION_CANDIDATE", "EXACT_EXECUTION_CANDIDATE_REQUIRED")
    grant = authority.load(request.get("execution_release"))  # BEFORE SDK/credentials/private Inputs
    execution = authority.bind(grant, request)
    require(time.time() + grant["caps"]["seconds"] + 120 < grant["expires_unix"], "FULL_JOB_WINDOW_REQUIRED")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == grant["merged_sha"] and not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT), "CLEAN_EXACT_MERGED_SOURCE_REQUIRED")
    notebook = safe(ROOT, request["notebook"])
    require(sha(notebook) == grant["notebook_sha256"] and code_hash(read(notebook)) == grant["notebook_code_sha256"]
        and notebook.read_bytes() == subprocess.check_output(["git", "show", head + ":" + request["notebook"]], cwd=ROOT),
        "EXACT_COMMITTED_EXECUTION_NOTEBOOK_REQUIRED")
    metadata = read(notebook)["metadata"]["safeshift"]
    require(metadata["runtime_commit"] == grant["runtime_commit"]
        and metadata["source_sha256"] == grant["source_sha256"]
        and metadata["status"] == "BLOCKED_PENDING_EXACT_EXECUTION_RELEASE", "EXECUTION_NOTEBOOK_IDENTITY")
    from scripts.build_internvl3763 import build
    require(read(notebook) == build(grant["runtime_commit"], execute=True), "REPRODUCIBLE_EXECUTION_NOTEBOOK_REQUIRED")
    # Local custody of every selected ancestor, checked before GPU reservation.
    from safeshift.internvl3763 import sealed_history
    custody = request["bindings"]["runtime"].get("local_history", [])
    require(type(custody) is list and len(custody) == len(execution["history"]), "LOCAL_SEALED_HISTORY_REQUIRED")
    for ancestor, item in zip(execution["history"], custody):
        require(set(item) == {"path", "sha256", "plan"} and sealed_history(safe(ROOT, item["path"]),
            item["sha256"], item["plan"]) == ancestor, "SEALED_ANCESTOR_BINDING")
    input_sources(request)
    check_sdk()
    return grant, execution


def kernel_version_label(version):
    """GetKernel uses vN; Input/status references keep their numeric /N suffix."""
    require(type(version) in (int, str) and re.fullmatch(r"[1-9][0-9]*", str(version)),
        "POSITIVE_PINNED_KERNEL_VERSION_REQUIRED")
    return "v" + str(version)


def inventory(client, request, grant, *, campaign_prefix=None, known_jobs=None):
    from scripts.submit_internvl_v2 import bounded_http
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    with bounded_http():
        owned, token, tokens = set(), None, set()
        for page in range(1, 17):
            response = client.kernels_list_with_response(mine=True, page_size=100, page_token=token,
                page=None if token else page)
            refs = [row.ref for row in response.kernels]
            require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(ref.startswith("nguynanhtn/") for ref in refs), "EXACT_OWNED_ACCOUNT_INVENTORY")
            owned.update(refs)
            token = response.next_page_token
            if not token and len(refs) < 100:
                break
            if token:
                require(token not in tokens, "REPEATED_INVENTORY_PAGE")
                tokens.add(token)
        else:
            raise ValueError("INCOMPLETE_ACCOUNT_INVENTORY")
        require(request["job"] not in owned, "JOB_EXISTS_NO_NEW_VERSION_OR_RETRY")
        if campaign_prefix is not None:
            require({ref for ref in owned if ref.startswith(campaign_prefix)} == known_jobs,
                "PROVIDER_CAMPAIGN_HISTORY_MISSING_OR_LEDGER_ROLLBACK_STOP")
        for index, expected in enumerate(grant["predecessors"], 1):
            snapshot = authority.http(grant["witness"] + "/v1/" + grant["series"] + "/" + str(index) + "/snapshot", None)
            require(snapshot["witness_id"] == grant["witness_id"], "PREDECESSOR_AUTHORITY_DATABASE_DRIFT")
            previous = snapshot["claims"]["submit"]
            require(digest(previous) == expected and previous["source_sha256"] == grant["source_sha256"],
                "PREDECESSOR_SOURCE_OR_RESERVATION_DRIFT")
            ref = previous["job"] + "/" + str(previous["version"])
            require(str(client.kernels_status(ref).status).split(".")[-1] in ("COMPLETE", "ERROR", "CANCELLED"),
                "PREVIOUS_JOB_RUNNING_OR_UNKNOWN_NO_SUBMIT")
            query = ApiGetKernelRequest()
            query.user_name, query.kernel_slug = previous["job"].split("/")
            query.version_label = kernel_version_label(previous["version"])
            with client.build_kaggle_client() as remote:
                value = remote.kernels.kernels_api_client.get_kernel(query)
            import json
            require(value.metadata is not None and value.metadata.ref == previous["job"] and value.metadata.is_private is True
                and type(value.metadata.current_version_number) is int
                and value.metadata.current_version_number == previous["version"]
                and code_hash(json.loads(value.blob.source)) == previous["notebook_code_sha256"],
                "PREVIOUS_JOB_IDENTITY_DRIFT")
        sources = input_sources(request)
        for ref in sources["kernel_sources"]:
            user, slug, version = ref.split("/")
            query = ApiGetKernelRequest()
            query.user_name, query.kernel_slug, query.version_label = user, slug, kernel_version_label(version)
            with client.build_kaggle_client() as remote:
                metadata = remote.kernels.kernels_api_client.get_kernel(query).metadata
            require(metadata is not None and metadata.ref == user + "/" + slug and metadata.is_private is True
                and type(metadata.current_version_number) is int and metadata.current_version_number == int(version)
                and str(client.kernels_status(ref).status).split(".")[-1] == "COMPLETE", "MISSING_OR_INCOMPLETE_VERSIONED_INPUT")
        for ref in sources["dataset_sources"]:
            require(client.dataset_list_files(ref, page_size=1).files, "MISSING_DATASET_INPUT")
        quota = client.quota_view().gpu_quota
        q = {key: int(getattr(quota, field).total_seconds()) for key, field in (
            ("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
        require(0 <= q["used"] <= q["total"] and q["reserved"] == 0
            and q["total"] - q["used"] >= grant["caps"]["attempt_gpu_seconds"], "GPU_QUOTA_OR_ACTIVE_JOB_BLOCKED")
    return {"owned_count": len(owned), "owned_sha256": digest(sorted(owned)), "inputs": sources,
        "quota": q, "observed_unix": time.time(), "input_bytes": "CHECKED_IN_AUTHORIZED_WORKER_BEFORE_LOAD"}


def submit(request, grant, execution, root):
    if request["scope"] == "TRAIN3763_CAMPAIGN":
        return submit_campaign(request, grant, execution, root)
    # Re-admission prevents a changed release/source between preflight and POST.
    require(admit(request) == (grant, execution), "SUBMIT_RELEASE_DRIFT")
    client = api()
    observed = inventory(client, request, grant)
    stage = Path(root) / "submission"
    stage.mkdir(exist_ok=False)
    write(stage / "inventory.json", observed)
    write(stage / "release.json", grant)
    sources = input_sources(request)
    write(stage / "kernel-metadata.json", {"id": request["job"], "title": request["job"].split("/")[1],
        "code_file": "internvl.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
        "dataset_sources": sources["dataset_sources"], "kernel_sources": sources["kernel_sources"],
        "competition_sources": [], "model_sources": []})
    write_bytes(stage / "internvl.ipynb", safe(ROOT, request["notebook"]).read_bytes())
    # Atomic remote create BEFORE the only push site. A lost response cannot retry.
    receipt = authority.Witness(grant, request["execution_release"]).claim("submit", request)
    write(stage / "remote-submission-claim.json", receipt)
    from scripts.submit_internvl_v2 import bounded_http
    with bounded_http():
        response = client.kernels_push(str(stage), timeout=str(grant["caps"]["seconds"]),
            acc=grant["caps"]["machine_shape"])
    write(stage / "submit-return.json", response.to_dict())
    return {"job_id": request["job"], "version": request["version"]}


def verify_remote_custody(request, archive, *, provider=None):
    """Read-only reconciliation is allowed after the execution window expires."""
    if request["scope"] == "TRAIN3763_CAMPAIGN":
        ledger = campaign_ledger(request)
        # Idempotent read-only recollection of a closed attempt never consumes.
        existing = [x for x in ledger.events() if x["kind"] == "COLLECTED" and x["plan"] == request["plan"]]
        if existing:
            require(len(existing) == 1 and existing[0]["sha256"] == sha(archive), "COLLECTED_ARCHIVE_DRIFT")
            return {"status": "RECONCILED", "automatic_retry": False, "scientific_pooling": False}
        require(provider is not None, "LIVE_TERMINAL_IDENTITY_REQUIRED")
        ledger.collect(request, archive, provider)
        return {"status": "RECONCILED", "automatic_retry": False, "scientific_pooling": False}
    import json
    import zipfile
    grant = authority.load(request["execution_release"], for_collection=True)
    authority.bind(grant, request)
    require(Path(archive).stat().st_size <= grant["caps"]["archive_bytes"], "RELEASE_ARCHIVE_SIZE_CAP")
    witness = authority.Witness(grant, request["execution_release"])
    snapshot = witness.observe("snapshot")["claims"]
    require(snapshot.get("submit", {}).get("release_sha256") == digest(grant), "REMOTE_SUBMISSION_CUSTODY")
    with zipfile.ZipFile(archive) as bundle:
        get = lambda name: json.loads(bundle.read(name))
        require(get("handoff.json") == request and get("release.json") == grant, "SEALED_EXACT_RELEASE_CUSTODY")
        records = get("run/summary.json")["records"]
        claims = [("launch", "launch-claim.json"), ("worker", "environment/worker-claim.json"), ("load", "run/load-claim.json")]
        for kind, name in claims:
            remote = {"found": kind in snapshot, "receipt": snapshot.get(kind)}
            local = name in bundle.namelist()
            require(remote.get("found") is local, "AMBIGUOUS_REMOTE_NATIVE_CONSUMPTION")
            if local:
                require(get(name) == remote["receipt"] and remote["receipt"]["release_sha256"] == digest(grant),
                    "REMOTE_NATIVE_RECEIPT_DRIFT")
        for ordinal in request["plan"]["scheduled_ordinals"]:
            key = f"call-{ordinal:06d}"
            remote = {"found": key in snapshot, "receipt": snapshot.get(key)}
            name = f"run/samples/{ordinal:06d}/call-claim.json"
            local = name in bundle.namelist()
            require(remote.get("found") is local, "UNKNOWN_CALL_CLAIM_NO_RETRY")
            if local:
                require(get(name) == remote["receipt"] and records[ordinal]["status"] != "NOT_ATTEMPTED",
                    "REMOTE_SAMPLE_CONSUMPTION_DRIFT")
    return {"status": "RECONCILED", "automatic_retry": False, "scientific_pooling": False}
