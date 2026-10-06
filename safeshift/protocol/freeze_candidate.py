"""D9R26 candidate identity, never production execution authority.

Hash Git repository text bytes: normalize checkout CRLF to LF, nothing else.
All pinned artifacts are UTF-8 text. Git blob equality is tested separately.
The candidate does not hash itself; the reviewed commit binds its own bytes.
"""

from copy import deepcopy
import json
from pathlib import Path

from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA, sha
from .classification_policy import ROOT, MODELS, load_policy

PATH = "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json"
BASE = "a3a5fdcc0a17b920f2c15942247b6fd61d25aa2d"
METRIC_CONTRACT = "configs/pre_freeze/d9r24_metric_contract.v1.json"
PINNED = (
    "configs/pre_freeze/d9r22_seminar_scope.v1.json",
    "configs/pre_freeze/production_classification_policy.d9r23.v1.json",
    METRIC_CONTRACT,
    "configs/pre_freeze/d9r25_harness_contract.v1.json",
    "prompts/p2_classification_c1_v1.txt", "prompts/.gitattributes",
    "safeshift/__init__.py", "safeshift/runners/__init__.py",
    "safeshift/data/__init__.py", "safeshift/protocol/__init__.py",
    "safeshift/qualification/__init__.py",
    "safeshift/protocol/freeze_candidate.py",
    "safeshift/protocol/classification_policy.py",
    "safeshift/protocol/classification_failure_policy.py",
    "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/metrics.py",
    "safeshift/protocol/reporting.py", "safeshift/protocol/schema.py",
    "safeshift/protocol/p2_evaluation.py",
    "safeshift/data/manifest.py", "safeshift/data/p2_execution.py",
    "safeshift/runners/p2_harness.py", "safeshift/runners/p2_bridge.py",
    "safeshift/runners/p2_preflight.py", "safeshift/runners/p2_owner.py",
    "safeshift/runners/production_classification.py",
    "safeshift/runners/contracts.py", "safeshift/runners/storage.py",
    "safeshift/runners/qwen3_vl.py", "safeshift/runners/qwen2_5_vl.py",
    "safeshift/runners/internvl3.py", "safeshift/runners/internvl3_snapshot.py",
    "safeshift/runners/moondream2.py", "safeshift/runners/moondream_snapshot.py",
    "safeshift/runners/moondream_binding.py", "safeshift/runners/moondream_precision.py",
    # CandidateAdapter imports shared receipt/types here; this is NOT a fifth runner.
    "safeshift/qualification/classification.py", "safeshift/runners/paligemma.py",
    "safeshift/runners/paligemma_snapshot.py",
    "safeshift/qualification/runtime.py",
    "scripts/provision_qwen3vl_snapshot.py", "scripts/provision_qwen2_5_snapshot.py",
    "scripts/provision_internvl3_snapshot.py", "scripts/provision_moondream_snapshot.py",
    "scripts/w2_qwen_kaggle_smoke.py", "scripts/w2_qwen2_5_t4_smoke.py",
    "configs/pre_freeze/qwen_kaggle_smoke.v1.json",
    "configs/pre_freeze/qwen2_5_t4_runtime.v1.json",
    "configs/pre_freeze/internvl3_t4_runtime.v1.json",
    "configs/pre_freeze/moondream_t4_runtime.v1.json",
    "configs/pre_freeze/moondream_precision_bridge.v1.json",
    "configs/pre_freeze/moondream_prep_audit.v1.json",
    "configs/pre_freeze/local_model_provenance.d9.json",
    "notes/w2_d9r26_freeze_candidate.md",
    "notes/w2_d9r26_qwen3_p2_runbook.md", "notes/w2_d9r26_qwen2_5_p2_runbook.md",
    "notes/w2_d9r26_internvl3_p2_runbook.md", "notes/w2_d9r26_moondream_p2_runbook.md",
)


def _current_rqs(scope, metrics):
    """Keep D9R22 science; reconcile only current implementation state."""
    required = {
        "schema_version": "d9r24-metric-contract-v1",
        "status": "IMPLEMENTED_OFFLINE_SYNTHETIC_ONLY",
        "classification_models": list(MODELS),
        "primary_grounding": "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE",
        "protocol_freeze": "PENDING",
    }
    if not isinstance(metrics, dict) or any(metrics.get(k) != v for k, v in required.items()):
        raise ValueError("D9R24_CANDIDATE_CONTRACT_MISMATCH")
    rq3 = metrics.get("rq3")
    if (not isinstance(rq3, dict)
            or rq3.get("metric_families") != scope["active_rqs"]["RQ3"]["metric_families"]):
        raise ValueError("D9R24_RQ3_METRIC_FAMILIES_MISMATCH")
    current = deepcopy(scope["active_rqs"])
    current["RQ3"].update(metric_contract=METRIC_CONTRACT, metric_implementation=metrics["status"])
    return current


def build_candidate(repo=ROOT):
    from safeshift.runners.p2_bridge import REGISTRY, REGISTRY_VERSION, VERSION
    from safeshift.runners.p2_harness import contract
    root = Path(repo)
    scope = json.loads((root / PINNED[0]).read_bytes())
    metrics = json.loads((root / METRIC_CONTRACT).read_bytes())
    current_rqs = _current_rqs(scope, metrics)
    c = contract(root)
    return {
        "schema_version": "protocol-freeze-candidate-d9r26-v1",
        "stacked_base_sha": BASE, "status": "FREEZE_CANDIDATE_NOT_FROZEN",
        "protocol_freeze_commit_sha": "PENDING", "protocol_freeze": "PENDING",
        "implementation_freeze": "PENDING", "inspecsafe_inference_authorized": False,
        "hash_semantics": "SHA256_GIT_REPOSITORY_UTF8_BYTES_CHECKOUT_CRLF_TO_LF_ONLY",
        "identity_sha256": {name: sha((root / name).read_bytes().replace(b"\r\n", b"\n")) for name in sorted(PINNED)},
        "research": {"title": scope["title"], "active_rqs": current_rqs},
        "models": load_policy(root)["classification"],
        "execution": {
            "bridge_version": VERSION, "registry_version": REGISTRY_VERSION,
            "registry": {k: list(v) for k, v in REGISTRY.items()},
            "binding": "IMPLEMENTED_SOURCE_BACKED_FREEZE_CANDIDATE",
            "model_payload_fields": c["model_payload_fields"],
            "bridge_operational_context_fields": c["bridge_operational_context_fields"],
            "raw_before_parse": c["raw_before_parse"],
            "sharding": c["shard_algorithm_version"], "semantic_retry": False,
            "automatic_retry": False, "resume": c["resume"], "rerun": c["rerun"],
            "call_identity_version": c["call_identity_version"],
            "caller_backend_injection": "FORBIDDEN",
            "runtime_observation": "NOT_EXECUTED_IN_CODEX",
        },
        "metrics": {"contract": METRIC_CONTRACT,
                    "engine": "safeshift/protocol/d9r24_metrics.py", "reporting": "safeshift/protocol/reporting.py",
                    "bootstrap": "UNCHANGED_B2000_SEED42_DOMAIN_STRATIFIED_NORMAL_POINT_ANOMALY_SAMPLE_LIMITATION"},
        "dataset": {"name": "InspecSafe-V1", "protocol": "P2", "sample_count": 5013,
                    "prediction_unit": "IMAGE", "fingerprint": FINGERPRINT, "source_manifest_sha256": MANIFEST_SHA},
        "governance": {"grounding": "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE", "training": False,
                       "fine_tuning": False, "semantic_score_selection": False, "p1_separate": True,
                       "p1_implemented": False, "inspecsafe": "NOT_RUN", "model_gpu_execution": False},
        "readiness": {"ready_for_independent_audit_before_freeze": True, "ready_to_run_inspecsafe": False,
                      "synthetic_rehearsal": "SCRIPTED_AND_FAKE_NATIVE_ONLY",
                      "pending": ["CHATGPT_GITHUB_VERIFICATION", "INDEPENDENT_AUDIT", "MERGE_A_THROUGH_E",
                                  "FINAL_POST_MERGE_FREEZE_AUTHORIZATION_PR", "FINAL_PROTOCOL_SHA",
                                  "EXPLICIT_INSPECSAFE_AUTHORIZATION", "ACTUAL_MODEL_EXECUTION"]},
    }


def verify_candidate(repo=ROOT):
    current = json.loads((Path(repo) / PATH).read_bytes())
    if current != build_candidate(repo):
        raise ValueError("FREEZE_CANDIDATE_IDENTITY_MISMATCH")
    return current


if __name__ == "__main__":
    # Printing allows an explicit reviewable update; never rewrites authority.
    print(json.dumps(build_candidate(), indent=2, sort_keys=True, ensure_ascii=True))
