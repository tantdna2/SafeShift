"""InternVL3-only P2 first attempts; offline, fail-closed release verification."""

from copy import deepcopy
from pathlib import Path
import json
import re
import subprocess

from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA, sha
from safeshift.protocol.classification_policy import ROOT, load_policy, same_json
from safeshift.protocol.schema import strict_json

BASE = "e46e98ed0c53f6c189f4069cc5f2f5d7d4295e5e"
SCHEMA = "p2-execution-authority-v3"
AUTHORITY_PATH = "configs/frozen/p2_execution_authority.v3.json"
HISTORICAL_PATH = "configs/frozen/p2_execution_authority.v2.json"
PLAN_PATH = "configs/frozen/internvl3_p2_execution_plan.v1.json"
PLAN_SHA256 = "b057d4968c0d0f85e7f7a8fc1a44d408bd7149f1af4dbcbd057ea4d63b820fdb"
RUNTIME_PATH = "configs/pre_freeze/internvl3_t4_runtime.v1.json"
RUNTIME_SHA256 = "85af239819a1903a1d1d8ce229c7039119aca147ff935b1cab4e78458599f80e"
MODEL_ID = "OpenGVLab/InternVL3-2B-hf"
REVISION = "cb57a075cb75a2e6d1b668b128d48bb00ae321d2"
RUNNER = "safeshift.runners.internvl3.InternVL3Runner"
RUNNER_VERSION = "internvl3-runner-v1"
# Pin F2's commit encoding in F1, avoiding a self-referencing authority SHA.
# This is Git identity metadata, not an attestation of external review.
F2_IDENTITY = "Nguyen Anh Tan <tantdna2@gmail.com> 1791520588 +0000"
F2_MESSAGE = "Freeze InternVL3-only P2 execution authority v3"
PRESERVED_SHA256 = {
    "configs/frozen/p2_execution_authority.v1.json": "7ce2ddf474b99ff60482a8aaea6826b86721e7b729eb84ec457821cb2d1322d3",
    HISTORICAL_PATH: "4e15937c23f6466b3d18aacdcc41d0203434e65d0ba06184dfa3f9a493fbb67d",
    "configs/frozen/qwen3_p2_execution_plan.v1.json": "5e6937e34864ca460a5d2065438b68f630cb6c3a9639883aa90885945d99bdc6",
    "configs/pre_freeze/qwen3_runtime_placement_amendment.v1.json": "1a7a6b64b14d117a6df92e37b86752035e8cc608b88c56379386899526d8c02c",
    "configs/pre_freeze/d9r25_harness_contract.v1.json": "5de268fb70f26e2614c387ab3b200c8d1391ec8b8c522883c37da9fd472f6ff2",
    "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json": "0901bab9b0dbd648b263071d5fdbd677120880eb91a2a5d4724c064905ab2ec2",
    "configs/pre_freeze/d9r22_seminar_scope.v1.json": "5eaf32e87288c900d4021bd774a613c8147d8140976092e45a7fde23245b4aeb",
    "configs/pre_freeze/production_classification_policy.d9r23.v1.json": "a0aeba174be9ae85f0cf3264ffcbbd97039f3088319084f9cd7f7caf852796ab",
    "prompts/p2_classification_c1_v1.txt": "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3",
    "configs/pre_freeze/d9r24_metric_contract.v1.json": "a04366aba1335d2878233bc90b43ec389ececa29377af9d8a26d99b29235c8d0",
    RUNTIME_PATH: RUNTIME_SHA256,
    "configs/pre_freeze/internvl3_source_audit.v1.json": "93ff3ad7e789ec72c0f9845c5b4ae22efd96df46f6d3db2e3cf92d7d43a49be1",
    "configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json": "a472d00bafc010f3041f57a54c39a5dbbae4e6a9c09ecae5dcf09f6388bf8e2f",
    "safeshift/qualification/runtime.py": "84e0d15244f431fe886c9e0b43faeff86449329d1d419bd9efccefdff57b9d40",
    "safeshift/runners/internvl3.py": "702156e2b8e392e32f6e92d6ae999b4249306a484d7fab813f118a43660e4f2b",
    "safeshift/runners/internvl3_snapshot.py": "ef6e585d9e5c986e915901b1ab62f1b436269e17ca55dfb1c3e5db543b325e6d",
}


def execution_plan():
    return {
        "schema_version": "internvl3-p2-execution-plan-v1", "protocol_id": "P2",
        "model_key": "internvl3", "base_sha": BASE,
        "model_id": MODEL_ID, "immutable_revision": REVISION,
        "runner": RUNNER, "runner_version": RUNNER_VERSION,
        "runtime_plan_path": RUNTIME_PATH, "runtime_plan_sha256": RUNTIME_SHA256,
        "dataset_fingerprint": FINGERPRINT, "sample_count": 5013,
        "source_manifest_sha256": MANIFEST_SHA,
        "shard_algorithm_version": "sample-id-lexical-modulo-v1", "shard_count": 4,
        "attempt_kind": "FIRST_ATTEMPT", "reruns": [],
        "runs": [{
            "run_id": f"internvl3-p2-shard{i}-first", "model_key": "internvl3",
            "shard_count": 4, "shard_index": i, "sample_count": 1254 if i == 0 else 1253,
            "rerun_of": None,
        } for i in range(4)],
    }


def expected_authority(f1, tree):
    """Declaration only; F2 remains ineffective until the exact final merge."""
    return {
        "schema_version": SCHEMA, "status": "FROZEN", "authority": "RESEARCH_LEAD",
        "protocol_id": "P2", "model_key": "internvl3",
        "implementation_base_sha": BASE, "expected_pre_merge_main_sha": BASE,
        "implementation_freeze_commit_sha": f1, "implementation_freeze_tree_sha": tree,
        "supersedes_authority_path": HISTORICAL_PATH,
        "supersedes_authority_sha256": PRESERVED_SHA256[HISTORICAL_PATH],
        "preserved_sha256": deepcopy(PRESERVED_SHA256),
        "model_id": MODEL_ID, "immutable_revision": REVISION,
        "runner": RUNNER, "runner_version": RUNNER_VERSION,
        "runtime_plan_path": RUNTIME_PATH, "runtime_plan_sha256": RUNTIME_SHA256,
        "execution_plan_path": PLAN_PATH, "execution_plan_sha256": PLAN_SHA256,
        "authorized_runs": execution_plan()["runs"],
        "dataset_fingerprint": FINGERPRINT, "sample_count": 5013,
        "source_manifest_sha256": MANIFEST_SHA, "inspecsafe_inference_authorized": True,
        "reruns": [],
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
    # External review completion is a governance gate; local Git verifies the
    # exact release structure. No dataset, snapshot, GPU, backend or network I/O.
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
            raise ValueError("EXACT_INTERNVL3_FREEZE_REQUIRED")
        tree = _git(repo, "rev-parse", f"{f1}^{{tree}}").decode().strip()
        if (not same_json(authority, expected_authority(f1, tree))
                or raw_authority != authority_bytes(expected_authority(f1, tree))
                or (Path(repo) / AUTHORITY_PATH).read_bytes() != raw_authority):
            raise ValueError("EXACT_INTERNVL3_AUTHORITY_REQUIRED")
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
        for path, digest in {**PRESERVED_SHA256, PLAN_PATH: PLAN_SHA256}.items():
            if (sha(_git(repo, "show", f"{f1}:{path}")) != digest
                    or sha((Path(repo) / path).read_bytes()) != digest):
                raise ValueError("INTERNVL3_PINNED_ARTIFACT_MISMATCH:" + path)
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
    if authority.get("schema_version") != SCHEMA or model != "internvl3":
        raise PermissionError("INTERNVL3_ONLY_EXECUTION_AUTHORITY")
    runs = execution_plan()["runs"]
    if (not same_json(authority.get("authorized_runs"), runs)
            or not same_json(authority.get("reruns"), [])):
        raise PermissionError("EXACT_FOUR_RUN_PLAN_REQUIRED")
    for run in runs:
        if run["run_id"] == run_id:
            return deepcopy(run)
    raise PermissionError("EXACT_INTERNVL3_RUN_ID_REQUIRED")


def bind_run(authority, model, run_id, shard_count, shard_index, rerun_of):
    run = authorized_run(authority, model, run_id)
    if (type(shard_count) is not int or type(shard_index) is not int
            or (shard_count, shard_index) != (run["shard_count"], run["shard_index"])):
        raise PermissionError("EXACT_INTERNVL3_SHARD_REQUIRED")
    if rerun_of is not None:
        raise PermissionError("INTERNVL3_FIRST_ATTEMPT_ONLY_NO_RERUN")
    return None


def require_new_run(repo, model, run_id):
    from .p2_harness import _run_path
    if _run_path(repo, model, run_id).exists():
        raise FileExistsError("EXISTING_RUN_RESUME_FORBIDDEN")
