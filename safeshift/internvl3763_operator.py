"""Exact-release official SDK submit, separate from historical PR177 campaigns."""
import importlib.metadata
from pathlib import Path
import re
import subprocess
import time

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, write_bytes, safe, sha
from safeshift.pilot.contract import digest
from safeshift import internvl3763_release as authority

SDK_PINS = {"kaggle": "2.2.5", "kagglesdk": "0.1.38", "requests": "2.34.2"}


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


def inventory(client, request, grant):
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
            query.version_label = str(previous["version"])
            with client.build_kaggle_client() as remote:
                value = remote.kernels.kernels_api_client.get_kernel(query)
            import json
            require(value.metadata.ref == previous["job"] and value.metadata.is_private is True
                and value.metadata.current_version_number == previous["version"]
                and code_hash(json.loads(value.blob.source)) == previous["notebook_code_sha256"],
                "PREVIOUS_JOB_IDENTITY_DRIFT")
        sources = input_sources(request)
        for ref in sources["kernel_sources"]:
            user, slug, version = ref.split("/")
            query = ApiGetKernelRequest()
            query.user_name, query.kernel_slug, query.version_label = user, slug, version
            with client.build_kaggle_client() as remote:
                metadata = remote.kernels.kernels_api_client.get_kernel(query).metadata
            require(metadata.ref == user + "/" + slug and str(metadata.current_version_number) == version
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


def verify_remote_custody(request, archive):
    """Read-only reconciliation is allowed after the execution window expires."""
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
