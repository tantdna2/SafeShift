"""Submit the single Owner-approved PR #216 smoke through the D-drive Operator."""
from argparse import ArgumentParser
import json
from pathlib import Path
import re
import subprocess

from safeshift.candidates.source import require
from safeshift.data.saved_reports import json_bytes, sha256, strict_json
from safeshift.fulltrain.ct1_run import REVISION
from safeshift.fulltrain.qwen_semantics import fields
from safeshift.internvl3763_operator import api
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import safe, write, write_bytes
from scripts.build_ct1_kaggle_notebooks import ROOT, content, owner_settings
from scripts.prepare_ct1_native_pilot import source_payload
from scripts.submit_internvl_v2 import bounded_http

PROJECT = Path("D:/SafeShift")
LEDGER = "data/processed/ct1-native-operator/pr216-smoke"
JOB = "safeshift-ct1-smoke-pr216"
LIMITS = {"jobs": 1, "images": 1, "calls": 3, "physical_gpus": 2, "seconds": 5400}
ROLES = ("source", "pilot_input", "checkpoint", "software_input")
PLAN_SHA = "a4e1ec60eb966133748b4ee9c145cff7e6ab1d2aaae929d796af8c0d6dbfa4a5"
SOFTWARE_SHA = "f5af28b0d7b77b30a88732d2416b9216435bd1328e7d1aa336b753d3817820cc"


def prepare(request):
    fields(request, {"settings", "inputs", "kaggle_owner", "data_authority_ref"})
    inputs = request["inputs"]
    fields(inputs, set(ROLES))
    account = request["kaggle_owner"]
    require(type(account) is str and re.fullmatch(r"[a-z0-9_-]{1,64}", account), "CT1_KAGGLE_ACCOUNT")
    authority = request["data_authority_ref"]
    require(type(authority) is str and 0 < len(authority.strip()) <= 512, "CT1_INPUT_RIGHTS_EVIDENCE")
    settings = request["settings"]
    owner_settings(settings)
    owner = settings["owner"]
    require(owner["plan_sha256"] == PLAN_SHA and owner["software_marker_sha256"] == SOFTWARE_SHA,
            "CT1_EXACT_PILOT_PLAN_AND_SOFTWARE")
    mounts = {role: owner[role] for role in ROLES if role != "source"}
    mounts["source"] = settings["source"]
    for role, ref in inputs.items():
        require(type(ref) is str and re.fullmatch(account + r"/[a-z0-9-]+/[1-9][0-9]*", ref),
                "CT1_OWNER_PRIVATE_VERSIONED_INPUT_REF")
        slug = ref.split("/")[1]
        match = re.fullmatch(r"/kaggle/input/(?:datasets/" + re.escape(account) + "/)?"
                             + re.escape(slug) + r"(?:/[a-zA-Z0-9._-]+)*", mounts[role])
        require(match and all(part not in (".", "..") and part.casefold() != "test"
                              for part in mounts[role].split("/")), "CT1_MOUNT_INPUT_BINDING")
    require(len({ref.rsplit("/", 1)[0] for ref in inputs.values()}) == len(ROLES)
            and owner["checkpoint"].endswith("/" + REVISION), "CT1_FOUR_DISTINCT_INPUTS")
    bound = {**request, "job": account + "/" + JOB, "version": 1, "limits": LIMITS,
             "authority": "PR216_OWNER_APPROVED_OPERATOR_SMOKE_ONLY"}
    seal = sha256(json_bytes(bound))
    notebook = content("smoke", {**settings, "owner": {**owner, "operator_request_sha256": seal}})
    return bound, seal, notebook


def provider_inventory(client, request):
    from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetRequest

    account = request["kaggle_owner"]
    require(client.get_config_value(client.CONFIG_NAME_USER) == account, "CT1_KAGGLE_ACCOUNT_MISMATCH")
    owned, tokens, token = set(), set(), None
    for page in range(1, 17):
        reply = client.kernels_list_with_response(mine=True, page_size=100, page_token=token,
                                                  page=None if token else page)
        refs = [row.ref for row in reply.kernels]
        require(len(set(refs)) == len(refs) and not owned.intersection(refs)
                and all(ref.startswith(account + "/") for ref in refs), "CT1_INCOMPLETE_PROVIDER_HISTORY")
        owned.update(refs)
        token = reply.next_page_token
        if not token and len(refs) < 100:
            break
        require(not token or token not in tokens, "CT1_INCOMPLETE_PROVIDER_HISTORY")
        if token:
            tokens.add(token)
    else:
        raise ValueError("CT1_INCOMPLETE_PROVIDER_HISTORY")
    require(not any("ct1-smoke-" in ref for ref in owned), "CT1_PRIOR_SMOKE_DO_NOT_SUBMIT")
    with client.build_kaggle_client() as remote:
        for ref in request["inputs"].values():
            owner, slug, version = ref.split("/")
            query = ApiGetDatasetRequest()
            query.owner_slug, query.dataset_slug = owner, slug
            data = remote.datasets.dataset_api_client.get_dataset(query)
            require(data.ref == f"{owner}/{slug}" and data.is_private is True
                    and data.current_version_number == int(version), "CT1_PRIVATE_INPUT_VERSION_UNVERIFIED")
            files = client.dataset_list_files(ref, page_size=1)
            require(files.files and not files.error_message, "CT1_PRIVATE_INPUT_FILES_UNKNOWN")
    gpu = client.quota_view().gpu_quota
    quota = {name: int(getattr(gpu, field).total_seconds()) for name, field in
             (("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
    require(quota["used"] >= 0 and quota["reserved"] == 0 and
            quota["total"] - quota["used"] >= LIMITS["physical_gpus"] * LIMITS["seconds"],
            "CT1_GPU_QUOTA_OR_EXISTING_RESERVATION")
    return {"owned_jobs_sha256": sha256(json_bytes(sorted(owned))), "inputs": request["inputs"],
            "gpu_quota_seconds": quota}


def submit(request, seal, notebook, approved_notebook_sha, ledger):
    require(sha256(notebook) == approved_notebook_sha, "CT1_EXACT_REVIEWED_SMOKE_NOTEBOOK")
    ledger.mkdir(parents=True, exist_ok=True)
    with lock(ledger):
        intent = safe(ledger, "push-intent.json")
        stage = safe(ledger, "submission")
        require(not intent.exists() and not stage.exists(), "CT1_POSSIBLE_SUBMISSION_NO_RETRY")
        client = api()
        with bounded_http():
            observed = provider_inventory(client, request)
            stage.mkdir(exist_ok=False)
            write(stage / "kernel-metadata.json", {
                "id": request["job"], "title": JOB, "code_file": "smoke.ipynb",
                "language": "python", "kernel_type": "notebook", "is_private": True,
                "enable_gpu": True, "enable_tpu": False, "enable_internet": False,
                "dataset_sources": [request["inputs"][role] for role in ROLES],
            })
            write_bytes(stage / "smoke.ipynb", notebook)
            write(intent, {"kind": "PUSH_INTENT", "request": request, "request_sha256": seal,
                           "notebook_sha256": approved_notebook_sha, "inventory": observed})
            result = client.kernels_push(str(stage), timeout=str(LIMITS["seconds"]), acc="NvidiaTeslaT4")
        require(not result.error and result.ref == request["job"] and result.version_number == 1,
                "CT1_SUBMISSION_RESULT_UNCERTAIN_NO_RETRY")
        submitted = {"kind": "SUBMITTED", "job": request["job"], "version": 1,
                     "request_sha256": seal, "intent_sha256": sha256(intent.read_bytes())}
        write(safe(ledger, "submitted.json"), submitted)
    return submitted


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "submit"))
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--notebook-output", type=Path)
    parser.add_argument("--notebook-sha256")
    args = parser.parse_args()
    private = (PROJECT / "data/processed").resolve()
    path = args.request.resolve()
    require(path.is_relative_to(private) and path.is_file() and path.stat().st_size <= 32768,
            "CT1_LOCAL_BOUNDED_OPERATOR_REQUEST")
    bound, seal, notebook = prepare(strict_json(path.read_bytes()))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == bound["settings"]["source_commit"]
            and not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT),
            "CT1_EXACT_CLEAN_OPERATOR_SOURCE")
    require(sha256(source_payload(head)) == bound["settings"]["source_zip_sha256"],
            "CT1_REPRODUCIBLE_SOURCE_CAPSULE_REQUIRED")
    if args.action == "prepare":
        output = args.notebook_output
        require(output is not None and output.resolve().is_relative_to(private), "CT1_PRIVATE_NOTEBOOK_OUTPUT")
        receipt = {"notebook_sha256": write_bytes(output, notebook), "operator_request_sha256": seal}
    else:
        receipt = submit(bound, seal, notebook, args.notebook_sha256, safe(PROJECT, LEDGER))
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
