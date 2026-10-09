"""InternVL3-only P2.1 authority; exact local Git gate, no runtime access."""

from copy import deepcopy
from pathlib import Path
import json
import re
import subprocess

from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA, sha
from safeshift.protocol.classification_policy import ROOT, load_policy, same_json
from safeshift.protocol.schema import strict_json
from . import internvl3_authority as historical

BASE = "f0b5ea775b3c5bbe5e8618ba1372e59b8b8e150f"
SCHEMA = "p2-execution-authority-v4"
PROTOCOL_ID = "P2.1"
PARSER_VERSION = "p21-strict-classification-v1"
SOURCE_MARKER = "safeshift/runners/p21_authority.py"
AUTHORITY_PATH = "configs/frozen/p2_execution_authority.v4.json"
HISTORICAL_PATH = "configs/frozen/p2_execution_authority.v3.json"
PLAN_PATH = "configs/frozen/internvl3_p21_execution_plan.v1.json"
PLAN_SHA256 = "c1ba042a69b69f8a2908fb5b298310a0b462623e7db6e20b0e7605531150db51"
AMENDMENT_PATH = "configs/frozen/p21_protocol_amendment.v1.json"
AMENDMENT_SHA256 = "94f5378786b5ecab699023bab42e48fc1567dbdbaea97c4de267f1ec1650fd81"
MODEL_ID = historical.MODEL_ID
REVISION = historical.REVISION
RUNNER = historical.RUNNER
RUNNER_VERSION = historical.RUNNER_VERSION
RUNTIME_PATH = historical.RUNTIME_PATH
RUNTIME_SHA256 = historical.RUNTIME_SHA256
OLD_RUN_ID = "internvl3-p2-shard0-first"
OLD_MANIFEST_SHA256 = "1c245cacc4bca2230dabc7469824426deb0d5e1345ce9de9618778b6a4221d1c"
OLD_STATUS_SHA256 = "1a5a5c88af34341672b5db1c01f99bd782fb0a588a99a19acb4e7a0fe6237a1b"
# Commit encoding is pinned in F1; exact F2 is derivable without self-hashing.
# It is Git identity metadata, not proof of external review completion.
F2_IDENTITY = "Nguyen Anh Tan <tantdna2@gmail.com> 1791532800 +0000"
F2_MESSAGE = "Freeze InternVL3 P2.1 execution authority v4"
PRESERVED_SHA256 = {
    **historical.PRESERVED_SHA256,
    HISTORICAL_PATH: "9b32387d4c7a798a8949f300d356a8c6590875a78e8562e8e4a36d1379aa662b",
    historical.PLAN_PATH: historical.PLAN_SHA256,
    "safeshift/runners/internvl3_authority.py": "3739b3cebc0efa50bce0a10f4cb17bdb0edbd72b7e01888b50c256d487f0f641",
    "safeshift/runners/qwen3_authority.py": "763d57e4aa54d71a23da3cf1ad238d1cd5c3f362aeb9a2efdb57851226fcc072",
    "safeshift/runners/qwen3_placement.py": "2ef9394055793d1914f604fb40ced0f1b1e6112f4be5f9e66db71677a1607942",
    "safeshift/runners/qwen3_vl.py": "196cd0ce72267a9ff2cdf88537409114ae1f17d5658d58495c69e21ae78a13de",
    "safeshift/runners/qwen2_5_vl.py": "ed8e477e511c28b129daf2359c5f43f84ec6be20639aa884124a6f0311b3f038",
    "safeshift/runners/moondream2.py": "4864194fe866e26920ec759c0a6b8f97f86d872162a211ca88298133b0fed9cb",
    "safeshift/qualification/classification.py": "1c67e5b68cb0545970ef4887de3cc89441764c1204c6365f55e0fc57d9eb52e6",
    "safeshift/protocol/schema.py": "1209ad7cae0b48a49e6f0507e395bee1628b733001c09f82293e58312898efcf",
    "safeshift/protocol/d9r24_metrics.py": "c01b00e973d1e0d72f589d26c2442f7c632b5b8860051b453d361645daca4086",
    "safeshift/protocol/classification_failure_policy.py": "325cefb818038083b969193e2d680c499bc4b92b753cae9eb299f20eeec81fa6",
    "safeshift/protocol/classification_policy.py": "003cc62f83232f647800dbcf7544db12042386cc002e544dd6132033ed8cdca4",
    "safeshift/data/p2_execution.py": "6695750e8b2e15d64ad9f0cd6ffd0ac30439fa30b517d4fe527856a4183d2a3d",
}


def execution_plan():
    """Only four P2.1 attempts; shard0 has explicit cross-protocol lineage."""
    runs = []
    for i in range(4):
        runs.append({
            "run_id": "internvl3-p21-shard0-rerun1" if i == 0 else f"internvl3-p21-shard{i}-first",
            "model_key": "internvl3", "protocol_id": PROTOCOL_ID,
            "attempt_kind": "CROSS_PROTOCOL_RERUN" if i == 0 else "FIRST_ATTEMPT",
            "shard_count": 4, "shard_index": i, "sample_count": 1254 if i == 0 else 1253,
            "rerun_of": {"run_id": OLD_RUN_ID, "run_manifest_sha256": OLD_MANIFEST_SHA256} if i == 0 else None,
            "lineage": {"previous_protocol_id": "P2", "previous_git_commit": BASE,
                        "previous_run_status_sha256": OLD_STATUS_SHA256} if i == 0 else None,
        })
    return {
        "schema_version": "internvl3-p21-execution-plan-v1", "protocol_id": PROTOCOL_ID,
        "parser_version": PARSER_VERSION, "model_key": "internvl3", "base_sha": BASE,
        "model_id": MODEL_ID, "immutable_revision": REVISION,
        "runner": RUNNER, "runner_version": RUNNER_VERSION,
        "runtime_plan_path": RUNTIME_PATH, "runtime_plan_sha256": RUNTIME_SHA256,
        "dataset_fingerprint": FINGERPRINT, "sample_count": 5013,
        "source_manifest_sha256": MANIFEST_SHA,
        "shard_algorithm_version": "sample-id-lexical-modulo-v1", "shard_count": 4,
        "rerun_scope": "ENTIRE_SHARD_WITH_NEW_RUN_ID_AND_UNCHANGED_GENERATION_CONDITIONS",
        "stop_before_shards_1_3_if_shard0": ["ZERO_CANONICAL_YIELD", "GENERATION_FAILURE", "FAILED", "INTERRUPTED"],
        "runs": runs,
    }


def expected_authority(f1, tree):
    """Deterministic F2 declaration; Draft F2 never authorizes production."""
    plan = execution_plan()
    rerun = plan["runs"][0]
    return {
        "schema_version": SCHEMA, "status": "FROZEN", "authority": "RESEARCH_LEAD",
        "protocol_id": PROTOCOL_ID, "parser_version": PARSER_VERSION, "model_key": "internvl3",
        "implementation_base_sha": BASE, "expected_pre_merge_main_sha": BASE,
        "implementation_freeze_commit_sha": f1, "implementation_freeze_tree_sha": tree,
        "supersedes_authority_path": HISTORICAL_PATH,
        "supersedes_authority_sha256": PRESERVED_SHA256[HISTORICAL_PATH],
        "preserved_sha256": deepcopy(PRESERVED_SHA256),
        "model_id": MODEL_ID, "immutable_revision": REVISION,
        "runner": RUNNER, "runner_version": RUNNER_VERSION,
        "runtime_plan_path": RUNTIME_PATH, "runtime_plan_sha256": RUNTIME_SHA256,
        "protocol_amendment_path": AMENDMENT_PATH, "protocol_amendment_sha256": AMENDMENT_SHA256,
        "execution_plan_path": PLAN_PATH, "execution_plan_sha256": PLAN_SHA256,
        "authorized_runs": plan["runs"], "dataset_fingerprint": FINGERPRINT,
        "sample_count": 5013, "source_manifest_sha256": MANIFEST_SHA,
        "inspecsafe_inference_authorized": True,
        "reruns": [{"run_id": rerun["run_id"], "model_key": "internvl3",
                    "rerun_of": deepcopy(rerun["rerun_of"]), "authority": "RESEARCH_LEAD"}],
        "activation": "REVIEWED_STANDARD_MERGE_AND_POST_MERGE_VERIFICATION_ONLY",
        "required_reviews": ["INDEPENDENT_AUDIT", "RESEARCH_LEAD_CHATGPT_REVIEW",
                             "POST_MERGE_GIT_VERIFICATION"],
    }


def authority_bytes(authority):
    return (json.dumps(authority, indent=2, allow_nan=False) + "\n").encode("utf-8")


def f2_commit_bytes(f1, tree):
    return (f"tree {tree}\nparent {f1}\nauthor {F2_IDENTITY}\n"
            f"committer {F2_IDENTITY}\n\n{F2_MESSAGE}\n").encode("utf-8")


def authorize(repo=ROOT):
    """Local metadata only; proves the exact BASE -> F1 -> F2 -> merge shape."""
    from .p2_harness import BLOCK, _git, identities
    try:
        head = _git(repo, "rev-parse", "HEAD").decode().strip()
        parents = _git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if len(parents) != 3 or parents[0] != head:
            raise ValueError("FINAL_MERGE_REQUIRED")
        _, parent1, f2 = parents
        raw_authority = _git(repo, "show", f"{head}:{AUTHORITY_PATH}")
        authority = strict_json(raw_authority)
        f1 = authority["implementation_freeze_commit_sha"]
        if type(f1) is not str or not re.fullmatch(r"[0-9a-f]{40}", f1):
            raise ValueError("EXACT_P21_FREEZE_REQUIRED")
        tree = _git(repo, "rev-parse", f"{f1}^{{tree}}").decode().strip()
        expected = expected_authority(f1, tree)
        if (not same_json(authority, expected) or raw_authority != authority_bytes(expected)
                or (Path(repo) / AUTHORITY_PATH).read_bytes() != raw_authority):
            raise ValueError("EXACT_P21_AUTHORITY_REQUIRED")
        if parent1 != BASE:
            raise ValueError("FINAL_MERGE_PARENT_1_REQUIRED")
        if _git(repo, "rev-list", "--parents", "-n", "1", f1).decode().split() != [f1, BASE]:
            raise ValueError("FREEZE_COMMIT_PARENT_REQUIRED")
        if _git(repo, "rev-list", "--parents", "-n", "1", f2).decode().split() != [f2, f1]:
            raise ValueError("FINAL_MERGE_PARENT_2_MUST_BE_DIRECT_F2_CHILD_OF_FREEZE")
        if _git(repo, "ls-tree", "--name-only", f1, "--", AUTHORITY_PATH):
            raise ValueError("AUTHORITY_MUST_BE_ABSENT_FROM_F1")
        if _git(repo, "diff", "--name-status", f1, f2).decode().splitlines() != ["A\t" + AUTHORITY_PATH]:
            raise ValueError("EXECUTABLE_CHANGED_AFTER_FREEZE")
        if _git(repo, "show", f"{f2}:{AUTHORITY_PATH}") != raw_authority:
            raise ValueError("FINAL_MERGE_AUTHORITY_PARENT_REQUIRED")
        f2_tree = _git(repo, "rev-parse", f"{f2}^{{tree}}").decode().strip()
        if _git(repo, "cat-file", "commit", f2) != f2_commit_bytes(f1, f2_tree):
            raise ValueError("EXACT_FINAL_MERGE_PARENT_2_REQUIRED")
        if _git(repo, "rev-parse", f"{head}^{{tree}}").decode().strip() != f2_tree:
            raise ValueError("FINAL_MERGE_TREE_MISMATCH")
        if _git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("DIRTY_EXECUTION_COMMIT")
        for path, digest in {**PRESERVED_SHA256, PLAN_PATH: PLAN_SHA256,
                             AMENDMENT_PATH: AMENDMENT_SHA256}.items():
            if (sha(_git(repo, "show", f"{f1}:{path}")) != digest
                    or sha((Path(repo) / path).read_bytes()) != digest):
                raise ValueError("P21_PINNED_ARTIFACT_MISMATCH:" + path)
        if not same_json(strict_json(_git(repo, "show", f"{f1}:{PLAN_PATH}")), execution_plan()):
            raise ValueError("EXACT_FOUR_RUN_PLAN_REQUIRED")
        identities(repo)
        entry = load_policy(repo)["classification"]["internvl3"]
        if (entry["model_id"], entry["immutable_revision"]) != (MODEL_ID, REVISION):
            raise ValueError("EXACT_INTERNVL3_MODEL_REVISION_REQUIRED")
        return head, authority
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError(f"{BLOCK}:{exc}") from exc


def authorized_run(authority, model, run_id):
    if (authority.get("schema_version") != SCHEMA or model != "internvl3"
            or authority.get("protocol_id") != PROTOCOL_ID
            or authority.get("parser_version") != PARSER_VERSION):
        raise PermissionError("INTERNVL3_ONLY_P21_EXECUTION_AUTHORITY")
    runs = execution_plan()["runs"]
    if (not same_json(authority.get("authorized_runs"), runs)
            or not same_json(authority.get("reruns"), expected_authority("", "")["reruns"])):
        raise PermissionError("EXACT_FOUR_RUN_PLAN_REQUIRED")
    for run in runs:
        if run["run_id"] == run_id:
            return deepcopy(run)
    raise PermissionError("EXACT_P21_RUN_ID_REQUIRED")


def bind_run(authority, model, run_id, shard_count, shard_index, rerun_of):
    run = authorized_run(authority, model, run_id)
    if (type(shard_count) is not int or type(shard_index) is not int
            or (shard_count, shard_index) != (run["shard_count"], run["shard_index"])):
        raise PermissionError("EXACT_P21_SHARD_REQUIRED")
    if rerun_of is not None and not same_json(rerun_of, run["rerun_of"]):
        raise PermissionError("EXACT_P21_RERUN_REFERENCE_REQUIRED")
    return deepcopy(run["rerun_of"])


def require_new_run(repo, model, run_id):
    from .p2_harness import _run_path
    if _run_path(repo, model, run_id).exists():
        raise FileExistsError("EXISTING_RUN_RESUME_FORBIDDEN")


def verify_lineage(repo, authority, model, run_id, reference):
    """Require original bytes; never reconstruct historical benchmark evidence."""
    from .p2_harness import _run_path, _rerun
    run = authorized_run(authority, model, run_id)
    if not same_json(reference, run["rerun_of"]):
        raise PermissionError("EXACT_P21_RERUN_REFERENCE_REQUIRED")
    if reference is None:
        return
    try:
        previous = _run_path(repo, model, OLD_RUN_ID)
        # _rerun verifies original manifest bytes and the sole explicit rerun.
        _rerun(repo, model, run_id, reference, authority["reruns"])
        manifest = strict_json((previous / "run_manifest.json").read_bytes())
        identity = manifest["protocol_identity"]
        if (manifest["run_id"] != OLD_RUN_ID or manifest["model_key"] != "internvl3"
                or manifest["git_commit"] != BASE or manifest["rerun_of"] is not None
                or manifest["version"] != "d9r26-run-v1"
                or identity["protocol_id"] != "P2" or identity["source_kind"] != "INSPECSAFE"
                or identity["dataset_fingerprint"] != FINGERPRINT
                or identity["source_manifest_sha256"] != MANIFEST_SHA
                or not same_json(manifest["model_condition"], load_policy(repo)["classification"][model])):
            raise ValueError("EXACT_PREVIOUS_P2_MANIFEST_REQUIRED")
        raw_status = (previous / "run_status.json").read_bytes()
        if sha(raw_status) != OLD_STATUS_SHA256:
            raise ValueError("RERUN_PREVIOUS_STATUS_SHA_MISMATCH")
        status = strict_json(raw_status)
        if (status["status"] != "COMPLETED" or status["failure"] is not None
                or type(status["samples"]) is not dict or len(status["samples"]) != 1254
                or any(value != "INVALID" for value in status["samples"].values())):
            raise ValueError("EXACT_PREVIOUS_P2_STATUS_REQUIRED")
    except OSError as exc:
        raise ValueError("RERUN_PREVIOUS_MANIFEST_AND_STATUS_REQUIRED") from exc


def verify_progression(repo, authority, model, run_id):
    """Shards1–3 cannot start after missing, failed or zero-yield P2.1 shard0."""
    from safeshift.data.p2_execution import safe_path
    from safeshift.protocol.p2_evaluation import export_predictions
    from .p2_harness import _git, _run_path
    run = authorized_run(authority, model, run_id)
    if run["shard_index"] == 0:
        return
    shard0 = execution_plan()["runs"][0]
    root = _run_path(repo, model, shard0["run_id"])
    try:
        manifest = strict_json(safe_path(root, "run_manifest.json").read_bytes())
        status = strict_json(safe_path(root, "run_status.json").read_bytes())
        if (manifest["version"] != "p21-run-v1" or manifest["run_id"] != shard0["run_id"]
                or manifest["model_key"] != model
                or manifest["git_commit"] != _git(repo, "rev-parse", "HEAD").decode().strip()
                or manifest["protocol_identity"]["protocol_id"] != PROTOCOL_ID
                or manifest["protocol_identity"]["parser_version"] != PARSER_VERSION
                or manifest["protocol_identity"]["source_kind"] != "INSPECSAFE"
                or manifest["protocol_identity"]["dataset_fingerprint"] != FINGERPRINT
                or manifest["protocol_identity"]["source_manifest_sha256"] != MANIFEST_SHA
                or not same_json(manifest["rerun_of"], shard0["rerun_of"])
                or manifest["attempt_kind"] != shard0["attempt_kind"]
                or not same_json(manifest["lineage"], shard0["lineage"])
                or status["status"] != "COMPLETED" or status["failure"] is not None
                or type(status["samples"]) is not dict or len(status["samples"]) != 1254
                or any(value not in ("SUCCESS", "INVALID") for value in status["samples"].values())
                or "SUCCESS" not in status["samples"].values()):
            raise ValueError("COMPLETED_P21_SHARD0_WITH_CANONICAL_YIELD_REQUIRED")
        artifacts = {p.relative_to(root).as_posix(): sha(safe_path(root, p.relative_to(root).as_posix()).read_bytes())
                     for p in sorted(root.rglob("*.json")) if p.relative_to(root).as_posix() != "run_status.json"}
        if not same_json(status["artifact_sha256"], artifacts):
            raise ValueError("P21_SHARD0_ARTIFACT_INDEX_MISMATCH")
        for name, digest in status["artifact_sha256"].items():
            if sha(safe_path(root, name).read_bytes()) != digest:
                raise ValueError("P21_SHARD0_ARTIFACT_INTEGRITY_FAILURE")
        exported = export_predictions(root, repo=repo, protocol_version=PROTOCOL_ID)
        if (len(exported["rows"]) != 1254 or exported["shard"]["shard_count"] != 4
                or exported["shard"]["shard_index"] != 0
                or not any(row["parse_status"] == "SUCCESS" for row in exported["rows"])):
            raise ValueError("P21_SHARD0_COHORT_OR_YIELD_MISMATCH")
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError(f"P21_SHARD0_SUCCESS_REQUIRED:{exc}") from exc
