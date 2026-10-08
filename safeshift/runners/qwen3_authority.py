"""Qwen3-only superseding P2 authority; offline Git and metadata checks only."""

from copy import deepcopy
from pathlib import Path
import re
import subprocess

from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA, sha
from safeshift.protocol.classification_policy import (
    ROOT, QWEN3_AMENDMENT_PATH, load_policy, same_json,
)
from safeshift.protocol.schema import strict_json
from .qwen3_placement import RUNTIME_ID

BASE = "92ef9179f23ca7c58ffb425512d239b12b26f832"
AUTHORITY_PATH = "configs/frozen/p2_execution_authority.v2.json"
HISTORICAL_PATH = "configs/frozen/p2_execution_authority.v1.json"
PLAN_PATH = "configs/frozen/qwen3_p2_execution_plan.v1.json"
PLAN_SHA256 = "5e6937e34864ca460a5d2065438b68f630cb6c3a9639883aa90885945d99bdc6"
AMENDMENT_SHA256 = "1a7a6b64b14d117a6df92e37b86752035e8cc608b88c56379386899526d8c02c"
OLD_RUN_ID = "qwen3-p2-shard0-first"
OLD_MANIFEST_SHA256 = "d4dd6ee9790dcc3c99c73e9404b52f71268fc7285ead41797dcf828261cd1500"
SCHEMA = "p2-execution-authority-v2"
PRESERVED_SHA256 = {
    HISTORICAL_PATH: "7ce2ddf474b99ff60482a8aaea6826b86721e7b729eb84ec457821cb2d1322d3",
    QWEN3_AMENDMENT_PATH: AMENDMENT_SHA256,
    "configs/pre_freeze/d9r25_harness_contract.v1.json": "5de268fb70f26e2614c387ab3b200c8d1391ec8b8c522883c37da9fd472f6ff2",
    "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json": "0901bab9b0dbd648b263071d5fdbd677120880eb91a2a5d4724c064905ab2ec2",
    "configs/pre_freeze/d9r22_seminar_scope.v1.json": "5eaf32e87288c900d4021bd774a613c8147d8140976092e45a7fde23245b4aeb",
    "configs/pre_freeze/production_classification_policy.d9r23.v1.json": "a0aeba174be9ae85f0cf3264ffcbbd97039f3088319084f9cd7f7caf852796ab",
    "prompts/p2_classification_c1_v1.txt": "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3",
    "configs/pre_freeze/d9r24_metric_contract.v1.json": "a04366aba1335d2878233bc90b43ec389ececa29377af9d8a26d99b29235c8d0",
}


def execution_plan():
    return {
        "schema_version": "qwen3-p2-execution-plan-v1", "protocol_id": "P2",
        "model_key": "qwen3", "base_sha": BASE, "runtime_id": RUNTIME_ID,
        "dataset_fingerprint": FINGERPRINT, "sample_count": 5013,
        "source_manifest_sha256": MANIFEST_SHA,
        "shard_algorithm_version": "sample-id-lexical-modulo-v1", "shard_count": 4,
        "rerun_scope": "ENTIRE_SHARD_INCLUDING_PREVIOUS_SUCCESSES",
        "runs": [{
            "run_id": "qwen3-p2-shard0-rerun1" if i == 0 else f"qwen3-p2-shard{i}-first",
            "model_key": "qwen3", "shard_count": 4, "shard_index": i,
            "sample_count": 1254 if i == 0 else 1253,
            "rerun_of": {"run_id": OLD_RUN_ID, "run_manifest_sha256": OLD_MANIFEST_SHA256}
                        if i == 0 else None,
        } for i in range(4)],
    }


def expected_authority(f1, tree):
    """Deterministic declaration for F2; does not activate production."""
    plan = execution_plan()
    rerun = plan["runs"][0]
    return {
        "schema_version": SCHEMA, "status": "FROZEN", "authority": "RESEARCH_LEAD",
        "protocol_id": "P2", "model_key": "qwen3",
        "implementation_base_sha": BASE, "expected_pre_merge_main_sha": BASE,
        "implementation_freeze_commit_sha": f1, "implementation_freeze_tree_sha": tree,
        "supersedes_authority_path": HISTORICAL_PATH,
        "supersedes_authority_sha256": PRESERVED_SHA256[HISTORICAL_PATH],
        "preserved_sha256": deepcopy(PRESERVED_SHA256),
        "runtime_amendment_path": QWEN3_AMENDMENT_PATH,
        "runtime_amendment_sha256": AMENDMENT_SHA256, "runtime_id": RUNTIME_ID,
        "execution_plan_path": PLAN_PATH, "execution_plan_sha256": PLAN_SHA256,
        "authorized_runs": plan["runs"],
        "dataset_fingerprint": FINGERPRINT, "sample_count": 5013,
        "source_manifest_sha256": MANIFEST_SHA, "inspecsafe_inference_authorized": True,
        "reruns": [{"run_id": rerun["run_id"], "model_key": "qwen3",
                    "rerun_of": rerun["rerun_of"], "authority": "RESEARCH_LEAD"}],
        "activation": "REVIEWED_STANDARD_MERGE_AND_POST_MERGE_VERIFICATION_ONLY",
        "required_reviews": ["INDEPENDENT_AUDIT", "RESEARCH_LEAD_CHATGPT_REVIEW",
                             "POST_MERGE_GIT_VERIFICATION"],
    }


def authorize(repo=ROOT):
    # Governance reviews are external gates, as in D9R27. Local Git proves the
    # immutable release structure; it does not attest to review completion.
    from .p2_harness import BLOCK, _git, identities
    try:
        head = _git(repo, "rev-parse", "HEAD").decode().strip()
        parents = _git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if len(parents) != 3 or parents[0] != head:
            raise ValueError("FINAL_MERGE_REQUIRED")
        _, parent1, f2 = parents
        authority = strict_json(_git(repo, "show", f"{head}:{AUTHORITY_PATH}"))
        f1 = authority["implementation_freeze_commit_sha"]
        if type(f1) is not str or not re.fullmatch(r"[0-9a-f]{40}", f1):
            raise ValueError("EXACT_QWEN3_FREEZE_REQUIRED")
        tree = _git(repo, "rev-parse", f"{f1}^{{tree}}").decode().strip()
        if not same_json(authority, expected_authority(f1, tree)):
            raise ValueError("EXACT_QWEN3_AUTHORITY_REQUIRED")
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
        if _git(repo, "show", f"{f2}:{AUTHORITY_PATH}") != _git(repo, "show", f"{head}:{AUTHORITY_PATH}"):
            raise ValueError("FINAL_MERGE_AUTHORITY_PARENT_REQUIRED")
        if _git(repo, "rev-parse", f"{head}^{{tree}}") != _git(repo, "rev-parse", f"{f2}^{{tree}}"):
            raise ValueError("FINAL_MERGE_TREE_MISMATCH")
        if _git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("DIRTY_EXECUTION_COMMIT")
        for path, digest in {**PRESERVED_SHA256, PLAN_PATH: PLAN_SHA256}.items():
            raw = _git(repo, "show", f"{f1}:{path}")
            local = (Path(repo) / path).read_bytes()
            if path.endswith(".json") and path != HISTORICAL_PATH:
                local = local.replace(b"\r\n", b"\n")
            if sha(raw) != digest or sha(local) != digest:
                raise ValueError("QWEN3_PINNED_ARTIFACT_MISMATCH:" + path)
        if not same_json(strict_json(_git(repo, "show", f"{f1}:{PLAN_PATH}")), execution_plan()):
            raise ValueError("EXACT_FOUR_RUN_PLAN_REQUIRED")
        identities(repo)
        load_policy(repo, qwen3_runtime=True)
        return head, authority
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError(f"{BLOCK}:{exc}") from exc


def authorized_run(authority, model, run_id):
    if authority.get("schema_version") != SCHEMA or model != "qwen3":
        raise PermissionError("QWEN3_ONLY_EXECUTION_AUTHORITY")
    runs = execution_plan()["runs"]
    if (not same_json(authority.get("authorized_runs"), runs)
            or not same_json(authority.get("reruns"), expected_authority("", "")["reruns"])):
        raise PermissionError("EXACT_FOUR_RUN_PLAN_REQUIRED")
    for run in runs:
        if run["run_id"] == run_id:
            return run
    raise PermissionError("EXACT_QWEN3_RUN_ID_REQUIRED")


def bind_run(authority, model, run_id, shard_count, shard_index, rerun_of):
    run = authorized_run(authority, model, run_id)
    if (type(shard_count) is not int or type(shard_index) is not int
            or (shard_count, shard_index) != (run["shard_count"], run["shard_index"])):
        raise PermissionError("EXACT_QWEN3_SHARD_REQUIRED")
    if rerun_of is not None and not same_json(rerun_of, run["rerun_of"]):
        raise PermissionError("EXACT_QWEN3_RERUN_REFERENCE_REQUIRED")
    return deepcopy(run["rerun_of"])


def verify_lineage(repo, authority, model, run_id, reference):
    from .p2_harness import _rerun
    try:
        _rerun(repo, model, run_id, reference, authority["reruns"])
    except OSError as exc:
        raise ValueError("RERUN_PREVIOUS_MANIFEST_REQUIRED") from exc
