"""CPU-only release dossier and conservative serial budget for MiniCPM.

This external companion never activates the frozen runtime, contacts Kaggle,
reserves production resources or issues approvals. Offline API exports have an
explicit trust boundary; replay is not authentication of their acquisition.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.fulltrain import contract, minicpm_ui as ui
from safeshift.pilot.artifacts import read, safe, sha, write
from safeshift.pilot.contract import digest, require_hash
from scripts.generate_minicpm_fulltrain_notebook import notebook

SCHEMA = "safeshift-minicpm-fulltrain-release-candidate-v1"
MARKER = "SAFESHIFT_MINICPM_FULLTRAIN_CAMPAIGN_V1"
APPROVAL = "SAFESHIFT_MINICPM_FULLTRAIN_APPROVAL_V1"
API = "https://api.github.com/repos/tantdna2/SafeShift"
ROLES = ("source_review", "independent_audit", "merge", "postmerge", "O2", "O3", "O4", "O5", "O6")
TOOLS = ("scripts/minicpm_fulltrain_release.py", "scripts/minicpm_fulltrain_ui.py",
         "scripts/generate_minicpm_fulltrain_notebook.py", "scripts/build_fresh_fulltrain_notebooks.py",
         "scripts/build_candidate160_notebooks.py", "scripts/build_three_vlm_notebooks.py",
         "scripts/reconcile_train3763_manual.py", "safeshift/internvl3763_operator.py",
         "safeshift/internvl3763_release.py", "safeshift/kaggle_handoff.py")
STOP = ["unknown_or_partial_consumption", "missing_or_conflicting_history", "source_or_science_drift",
        "provider_input_or_zip_mismatch", "technical_error_or_nonfinite", "caps_deadline_or_quota_exhausted"]
CAPS = ("total_calls", "total_jobs", "total_gpu_seconds", "job_calls", "job_seconds",
        "physical_gpus", "loads_per_job", "archive_bytes")


def bounded(path, limit=8 * 2**20):
    require(snapshot_stat(path).st_size <= limit, "RELEASE_METADATA_BOUND")
    return read(path)


def tool_manifest(repo=ROOT):
    return {name: sha(safe(repo, name)) for name in TOOLS}


def inspect_package(directory, repo=ROOT):
    """Rebuild the complete notebook; a handoff's claimed hash is insufficient."""
    directory = Path(directory)
    handoff = bounded(safe(directory, "handoff.json"))
    value = ui.verify_capsule(safe(directory, "dataset"), handoff["capsule_sha256"], repo)
    nb_path = safe(directory, "notebook.ipynb")
    nb = bounded(nb_path)
    ref = nb["metadata"]["safeshift"]["runtime_ref"]
    require(type(ref) is str and re.fullmatch(r"[0-9a-f]{40}", ref), "RELEASE_RUNTIME_COMMIT")
    expected = notebook(ref, repo, capsule_sha256=handoff["capsule_sha256"])
    require(nb_path.read_bytes() == (json.dumps(expected, indent=1, ensure_ascii=False) + "\n").encode(),
            "RELEASE_EXACT_NOTEBOOK_BYTES")
    require(handoff == {"status": "CANDIDATE_RELEASE_BLOCKED", "capsule_sha256": sha(directory / "dataset" / ui.MARKER),
        "request_sha256": digest(value["request"]), "notebook_sha256": sha(nb_path),
        "input_sources": value["input_sources"], "job": value["job"], "provider_version": 1,
        "native_calls": 0, "scientific_qualified": False, "evidence_refs": value["evidence_refs"]}, "RELEASE_HANDOFF")
    kernel = bounded(safe(directory, "kernel-metadata.json"))
    require(kernel == {"id": value["job"], "title": value["job"].split("/")[1], "code_file": "notebook.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": True,
        "enable_tpu": False, "enable_internet": True, "competition_sources": [], "model_sources": [],
        **value["input_sources"]}, "RELEASE_KERNEL_SETTINGS")
    dataset = bounded(safe(directory, "dataset-metadata.json"))
    require(dataset == {"id": value["capsule_ref"].rsplit("/", 1)[0], "title": value["capsule_ref"].split("/")[1],
        "isPrivate": True, "description": "Private MiniCPM execution metadata and immutable same-series history; no images or weights.",
        "licenses": [{"name": "other"}]}, "RELEASE_PRIVATE_CAPSULE_METADATA")
    binding = {"runtime_commit": ref, "source_sha256": value["request"]["source_sha256"],
        "tools_sha256": digest(tool_manifest(repo)), "job": value["job"], "version": 1,
        "capsule_ref": value["capsule_ref"], "files": {name: sha(safe(directory, name)) for name in
        ("handoff.json", "notebook.ipynb", "kernel-metadata.json", "dataset-metadata.json", "dataset/" + ui.MARKER)}}
    return value, binding


def scope(value, binding):
    r = value["request"]
    return deepcopy({"runtime_commit": binding["runtime_commit"], "source_sha256": r["source_sha256"],
        "tools_sha256": binding["tools_sha256"], "identity": r["plan"]["identity"], "campaign": r["campaign"],
        "original_inputs": r["original_inputs"], "checkpoint_marker_sha256": r["checkpoint_marker_sha256"],
        "python_input": r["python_input"], "resource_policy_sha256": digest(r["resource_policy"]),
        "fixed_inputs": {"dataset_sources": value["input_sources"]["dataset_sources"][:-1],
                         "kernel_sources": value["input_sources"]["kernel_sources"]}})


def template(value, binding):
    """Unsigned proposal; never fill authority, rights, caps or dates by default."""
    return {"schema": SCHEMA, "authorization": None, "implementation_pr": None, "reviewed_head": None,
        "merged_sha": None, "scope": scope(value, binding), "first_package": deepcopy(binding),
        "issued_unix": None, "expires_unix": None, "caps": {k: None for k in CAPS},
        "stop_rules": STOP.copy(), "approvals": {k: None for k in ROLES}}


def grant_scope(grant):
    # Approval records pin the entire scope, budget, dates and first package.
    return digest({k: v for k, v in grant.items() if k != "approvals"})


def validate_grant(grant, value, binding):
    expected = template(value, binding)
    require(type(grant) is dict and set(grant) == set(expected) and grant["schema"] == SCHEMA,
            "MINICPM_RELEASE_FIELDS")
    require(grant["authorization"] == "OWNER_GRANTED_SERIAL_TRAIN3763_UI_ONLY", "MINICPM_NO_IMPLICIT_GRANT")
    require(digest(grant["scope"]) == digest(expected["scope"]) and digest(grant["first_package"]) == digest(binding),
            "MINICPM_RELEASE_SOURCE_INPUT_SCIENCE_BINDING")
    require(type(grant["implementation_pr"]) is int and grant["implementation_pr"] > 195,
            "NEW_MINICPM_RELEASE_PR_REQUIRED")
    for key in ("reviewed_head", "merged_sha"):
        require(type(grant[key]) is str and re.fullmatch(r"[0-9a-f]{40}", grant[key]), "MINICPM_RELEASE_COMMIT")
    require(type(grant["issued_unix"]) is int and type(grant["expires_unix"]) is int
        and 0 < grant["issued_unix"] < grant["expires_unix"], "MINICPM_FINITE_WINDOW")
    caps = grant["caps"]
    require(type(caps) is dict and set(caps) == set(CAPS)
        and all(type(v) is int and v > 0 for v in caps.values()), "MINICPM_NUMERICAL_CAPS")
    require(caps["physical_gpus"] == 2 and caps["loads_per_job"] == 1
        and 1 <= caps["job_calls"] <= 3763 and caps["job_seconds"] <= 43200
        and caps["total_calls"] >= 3763 and caps["total_jobs"] <= 3763
        and caps["archive_bytes"] <= 7 * 2**30, "MINICPM_RESOURCE_SCOPE")
    require(grant["stop_rules"] == STOP and type(grant["approvals"]) is dict
        and set(grant["approvals"]) == set(ROLES), "MINICPM_STOP_APPROVALS")
    return grant


def record(body, marker):
    matches = re.findall(re.escape(marker) + r"\s*```json\s*(\{.*?\})\s*```", body, re.S)
    require(len(matches) == 1, "ONE_MINICPM_AUTHORITY_RECORD")
    def pairs(items):
        obj = {}
        for k, v in items:
            require(k not in obj, "DUPLICATE_MINICPM_AUTHORITY_KEY")
            obj[k] = v
        return obj
    return json.loads(matches[0], object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_MINICPM_AUTHORITY")))


def authenticate(locator, value, binding, *, reader):
    """Read-only authority check. reader must supply authentic GitHub responses.

    The CLI uses offline exports only and always labels their origin unverified.
    Owner attestations of review/audit are evidence references, never self-audits.
    This function does not enable any runtime entrypoint, even on success.
    """
    def comment(loc):
        require(type(loc) is dict and set(loc) == {"comment_id", "body_sha256"}
            and type(loc["comment_id"]) is int and loc["comment_id"] > 0, "MINICPM_AUTHORITY_LOCATOR")
        require_hash(loc["body_sha256"])
        got = reader("/issues/comments/" + str(loc["comment_id"]))
        require(got["id"] == loc["comment_id"] and got["user"]["login"] == "tantdna2"
            and hashlib.sha256(got["body"].encode()).hexdigest() == loc["body_sha256"], "MINICPM_AUTHENTIC_OWNER")
        return got
    owner = comment(locator)
    grant = validate_grant(record(owner["body"], MARKER), value, binding)
    pr_number = grant["implementation_pr"]
    require(owner["issue_url"] == API + "/issues/" + str(pr_number), "MINICPM_AUTHORITY_ISSUE")
    pr = reader("/pulls/" + str(pr_number))
    require(pr["merged"] is True and pr["draft"] is False and pr["base"]["ref"] == "main"
        and pr["head"]["sha"] == grant["reviewed_head"] and pr["merge_commit_sha"] == grant["merged_sha"],
        "MINICPM_REVIEWED_MERGE_REQUIRED")
    # Verify the tools actually exist at BOTH authority commits. A PR metadata
    # record plus a caller's local SHA cannot prove which code was reviewed.
    for ref in (grant["reviewed_head"], grant["merged_sha"]):
        for name, expected_sha in tool_manifest().items():
            item = reader("/contents/" + name + "?ref=" + ref)
            require(item["type"] == "file" and item["path"] == name and item["encoding"] == "base64"
                and type(item["content"]) is str and len(item["content"]) <= 2**20, "MINICPM_RELEASE_TOOL_RESPONSE")
            raw = base64.b64decode(item["content"].replace("\n", ""), validate=True)
            require(type(item["size"]) is int and len(raw) == item["size"]
                and hashlib.sha256(raw).hexdigest() == expected_sha, "MINICPM_REVIEWED_TOOL_BYTES")
    seen = {owner["id"]}
    for role, loc in grant["approvals"].items():
        proof = comment(loc)
        require(proof["id"] not in seen and proof["issue_url"] == owner["issue_url"], "MINICPM_SEPARATE_APPROVAL")
        seen.add(proof["id"])
        require(record(proof["body"], APPROVAL) == {"kind": role, "status": "APPROVED",
            "reviewed_head": grant["reviewed_head"], "scope_sha256": grant_scope(grant)}, "MINICPM_APPROVAL_ROLE_SCOPE")
    return grant


def replay_sequence(packages, attempts, supervisors, repo=ROOT):
    """Full local custody replay, followed by one proposed unexecuted package.

    Every earlier package needs both original result pairs. Reserve maxima, not
    successful-call counts; errors, unused calls/time and failures get no refund.
    Provider completeness and an outstanding VM cannot be proved from local ZIPs.
    """
    require(1 <= len(packages) <= 512 and len(attempts) == len(supervisors) == len(packages) - 1,
            "MINICPM_ALL_PRIOR_PAIRS_REQUIRED")
    first = None
    previous = None
    jobs, capsules, runs, ids = set(), set(), set(), set()
    reserved = {"calls": 0, "jobs": 0, "gpu_seconds": 0}
    limits, reports, archive_sizes = [], [], []
    for i, path in enumerate(packages):
        value, binding = inspect_package(path, repo)
        r, p = value["request"], value["request"]["plan"]
        if first is None:
            require(not r["history"] and p["action"] == "initial", "MINICPM_INITIAL_PACKAGE_REQUIRED")
            first = (value, binding)
        require(scope(value, binding) == scope(*first), "MINICPM_CAMPAIGN_SOURCE_DRIFT")
        require(value["job"] not in jobs and value["capsule_ref"] not in capsules
            and p["run_id"] not in runs and p["attempt_id"] not in ids, "MINICPM_PACKAGE_REPLAY")
        jobs.add(value["job"]); capsules.add(value["capsule_ref"])
        runs.add(p["run_id"]); ids.add(p["attempt_id"])
        require(p["scheduled_ordinals"], "MINICPM_NO_PENDING_CALLS")
        if previous is not None:
            require(previous["continuation"] == "REVIEW_CAPS_AND_RELEASE"
                and r["history"] == previous["history"] and p["action"] == "resume", "MINICPM_SERIAL_HISTORY_OR_FAILURE")
        require(len(r["history"]) == i, "MINICPM_MISSING_PRIOR_PACKAGE")
        reserved["calls"] += p["max_calls"]
        reserved["jobs"] += 1
        reserved["gpu_seconds"] += 2 * p["max_seconds"]
        limits.append({"calls": p["max_calls"], "seconds": p["max_seconds"]})
        if i < len(attempts):
            archive_sizes.extend(snapshot_stat(path).st_size for path in (attempts[i], supervisors[i]))
            with tempfile.TemporaryDirectory() as tmp:
                previous = ui.verify_results(value, Path(path) / "dataset", attempts[i], supervisors[i],
                    Path(tmp) / "verified", repo=repo)
            reports.append(previous)
    return {"first": first, "current": (value, binding), "reserved": reserved, "job_limits": limits,
        "archive_sizes": archive_sizes,
        "reports": reports, "counts_before_proposed_job": p["counts"]}


def budget(sequence, grant, *, now):
    caps, used = grant["caps"], sequence["reserved"]
    require(all(j["calls"] <= caps["job_calls"] and j["seconds"] <= caps["job_seconds"]
                for j in sequence["job_limits"]), "MINICPM_PER_JOB_CAP")
    require(used["calls"] <= caps["total_calls"] and used["jobs"] <= caps["total_jobs"]
        and used["gpu_seconds"] <= caps["total_gpu_seconds"], "MINICPM_CUMULATIVE_CAP_NO_REFUND")
    require(all(size <= caps["archive_bytes"] for size in sequence["archive_sizes"]), "MINICPM_ARCHIVE_CAP")
    require(grant["issued_unix"] <= now and now + sequence["job_limits"][-1]["seconds"] < grant["expires_unix"],
            "MINICPM_DEADLINE_HEADROOM")
    pending = sequence["counts_before_proposed_job"]["NOT_ATTEMPTED"]
    best_remaining = max(0, pending - sequence["job_limits"][-1]["calls"])
    remaining_calls = caps["total_calls"] - used["calls"]
    remaining_jobs = caps["total_jobs"] - used["jobs"]
    require(best_remaining <= min(remaining_calls, remaining_jobs * caps["job_calls"]),
            "MINICPM_CAPACITY_CANNOT_COVER_PENDING_IDS")
    return {"reserved_including_proposed_job": used, "remaining_after_proposed_job": {
        "calls": caps["total_calls"] - used["calls"], "jobs": caps["total_jobs"] - used["jobs"],
        "gpu_seconds": caps["total_gpu_seconds"] - used["gpu_seconds"]},
        "best_case_pending_after_proposed_job": best_remaining,
        "measured_provider_billing": "NOT_OBSERVED", "refunds": 0, "population_latency_fit": "NOT_ESTABLISHED"}


class Exports:
    def __init__(self, values):
        paths = {"/contents/" + name for name in TOOLS}
        require(type(values) is dict and len(values) <= 64 and all(type(k) is str and (
            re.fullmatch(r"/(?:issues/comments|pulls)/[1-9][0-9]*", k) or
            k.split("?ref=")[0] in paths and re.fullmatch(r".*\?ref=[0-9a-f]{40}", k))
            for k in values), "MINICPM_GITHUB_EXPORT_PATHS")
        self.values = values

    def __call__(self, path):
        require(path in self.values, "MINICPM_MISSING_GITHUB_EXPORT:" + path)
        return deepcopy(self.values[path])


def assess(sequence, *, locator=None, exports=None, now=None):
    value, binding = sequence["first"]
    require((locator is None) == (exports is None), "MINICPM_LOCATOR_AND_EXPORTS_TOGETHER")
    blockers = ["RUNTIME_ACTIVATION_REQUIRES_SEPARATE_REVIEWED_RELEASE",
        "CURRENT_PROVIDER_INPUT_VERSIONS_PRIVATE_CODE_CAPSULE_AND_QUOTA_NOT_OBSERVED",
        "PRIOR_PROVIDER_ZIP_CUSTODY_AND_NO_OUTSTANDING_VM_NOT_OBSERVED",
        "FINAL_SOURCE_INTEGRATED_ENVIRONMENT_LOAD_INFERENCE_EXPORT_NOT_RUN"]
    result = {"schema": SCHEMA, "status": "BLOCKED", "execution_authorized": False,
        "native_calls": 0, "production_mutations": 0, "source_scope": scope(value, binding),
        "first_package": binding, "proposed_package": sequence["current"][1],
        "reserved_including_proposed_job": sequence["reserved"],
        "counts_before_proposed_job": sequence["counts_before_proposed_job"],
        "authority": "MISSING", "blockers": blockers, "scientific_qualified": False}
    if locator is None:
        blockers.append("AUTHENTIC_OWNER_CAMPAIGN_CAPS_RIGHTS_O2_O6_REVIEW_AUDIT_MERGE_POSTMERGE_REQUIRED")
    else:
        grant = authenticate(locator, value, binding, reader=Exports(exports))
        result["authority"] = "OFFLINE_REPLAY_ONLY_ORIGIN_NOT_AUTHENTICATED"
        result["grant_sha256"] = digest(grant)
        result["budget"] = budget(sequence, grant, now=time.time() if now is None else now)
        blockers.append("OFFLINE_EXPORT_ORIGIN_REQUIRES_INDEPENDENT_ORIGINAL_VERIFICATION")
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("template", "check"))
    p.add_argument("--package", type=Path, action="append", required=True,
        help="Every package oldest first; last is proposed and has no result yet")
    p.add_argument("--attempt", type=Path, action="append", default=[])
    p.add_argument("--supervisor", type=Path, action="append", default=[])
    p.add_argument("--locator", type=Path)
    p.add_argument("--github-exports", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    require(not args.output.exists(), "MINICPM_RELEASE_CREATE_ONLY")
    sequence = replay_sequence(args.package, args.attempt, args.supervisor)
    if args.action == "template":
        require(args.locator is None and args.github_exports is None, "MINICPM_TEMPLATE_NO_APPROVAL_INPUT")
        result = template(*sequence["first"])
    else:
        result = assess(sequence, locator=bounded(args.locator) if args.locator else None,
            exports=bounded(args.github_exports) if args.github_exports else None)
    write(args.output, result)
    print("UNSIGNED_PROPOSAL" if args.action == "template" else "BLOCKED; see receipt blockers; no execution")


if __name__ == "__main__":
    main()
