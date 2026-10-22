"""Separate recovery CPU audit. No pooling API or baseline mutation."""
import json
import importlib.metadata
import platform
from pathlib import Path

from safeshift.pa3.native.journal import Journal
from safeshift.pa3.native.train_report import metrics, export
from . import cohort
from ..hnlo_train.audit import raw_rows as baseline_raw_rows, verify_custody, seal_raw
from ..hnlo_train.cohort import metadata as load_metadata
from .contract import AUTHORITY, EVIDENCE, authorize, unit


def raw_rows(root, planned, tokenizer):
    """Preserve raw replay, but a technical stop after sealing is still an error."""
    rows, completed, integrity = baseline_raw_rows(root, planned, tokenizer)
    index = Journal(Path(root) / "raw/index")
    if index.root.exists() and index.exists("failure"):
        failure = index.read("failure")
        ordinal = failure["ordinal"]
        if ordinal is not None:
            if type(ordinal) is not int or not 0 <= ordinal < len(rows):
                raise ValueError("RECOVERY_FAILURE_ORDINAL_INVALID")
            if any(r["attempted"] for r in rows[ordinal + 1:]):
                raise ValueError("ATTEMPT_AFTER_TECHNICAL_STOP")
            row = rows[ordinal]
            if row["status"] not in ("TECHNICAL_ERROR", "INTERRUPTED"):
                row.update(status="INTERRUPTED" if failure["interrupted"] else "TECHNICAL_ERROR",
                    score=None, details=None, errors=["RECOVERY_LIFECYCLE:" + failure["type"]])
        completed = False
    return rows, completed, integrity


def cpu_context(repo):
    from .bootstrap import git
    packages = {}
    for name in ("transformers", "tokenizers"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages,
            "source_commit": git(repo, "rev-parse", "HEAD"), "gpu_used": False,
            "command_module": "safeshift.diagnostics.qwen3_recovery.evaluate"}


def checked(root, repo, tokenizer, *, source=None):
    root, repo = Path(root), Path(repo)
    verify_custody(root)  # before metadata/GT or scores
    binding = json.loads((root / "binding.json").read_bytes())
    u = unit()
    if binding["unit"] != u:
        raise ValueError("UNIT_IDENTITY_CHANGED")
    from .bootstrap import verify_topology
    proof = verify_topology(repo, binding["source"]["github_pr"], binding["source"]["payload_sha256"])
    if proof != binding["source"] or source is not None and proof != source:
        raise ValueError("RAW_SOURCE_PROOF_MISMATCH")
    if binding["authority"] != json.loads((repo / AUTHORITY).read_bytes()):
        raise PermissionError("RAW_GRANT_MUST_MATCH_RELEASED_AUTHORITY")
    authorize(binding["authority"], proof)
    planned, mapping = cohort.inference(repo)
    if binding.get("recovery_mapping") != mapping:
        raise ValueError("PR123_RECOVERY_MAPPING_CHANGED")
    from .observe_audit import verify_observations
    observation_integrity = verify_observations(root, planned)
    if binding["samples"] != planned:
        raise ValueError("ORIGINAL_ID_ORDER_OR_IMAGE_HASH_CHANGED")
    rows, completed, integrity = raw_rows(root, planned, tokenizer)
    if observation_integrity != "PASS":
        completed = False
        integrity += ";OBSERVATIONS_" + observation_integrity
    index = Journal(root / "raw/index")
    if index.root.exists():
        allowed = {"manifest", "model", "load-start", "load-return", "native-counts", "finish", "failure", "finalization-error"}
        allowed |= {f"sample-{i:06d}.{kind}" for i in range(u["count"]) for kind in ("attempt", "result", "native-call")}
        try:
            unknown = set(index.inventory()) - allowed
        except (OSError, ValueError):
            unknown = set()  # raw_rows already marks torn integrity PARTIAL
        if unknown:
            raise ValueError("UNKNOWN_OR_EXTRA_UNIT_SAMPLE_RECORD")
    if any(r["attempted"] for r in rows):
        from safeshift.protocol.classification_policy import load_policy, render_prompt
        model = index.read("model")
        policy = load_policy(repo, qwen3_runtime=True)["classification"][u["model"]]
        runtime = model["runtime"]
        from safeshift.ls1.tokenizer import probe
        if model["tokenizer_t1"] != probe(tokenizer):
            raise ValueError("MODEL_TOKENIZER_T1_MISMATCH")
        expected = policy["software_versions"]
        if u["model"] == "qwen3":
            build = json.loads((repo / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
            expected = {**expected, **build["qwen3_additional_pins"]}
        if (model["model"] != u["model"] or model["policy"] != policy or model["clamp"] is not None
                or model["snapshot"]["model_id"] != u["id"] or model["snapshot"]["revision"] != u["revision"]
                or model["prompt"] != render_prompt(u["model"], repo=repo)
                or runtime["actual"] != expected or runtime["expected"] != expected
                or runtime["cuda"] != u["cuda"] or runtime["visible_devices"] != u["cuda_visible_devices"]):
            raise ValueError("EXACT_MODEL_RUNTIME_PROMPT_REQUIRED")
        from ..hnlo_hf import CAPTURE_FLAGS, QWEN_SOURCES
        source_rows = json.loads((root / "inference/generation-sources.json").read_bytes())
        source_hashes = {r["path"]: r["sha256"] for r in source_rows}
        if u["model"] == "qwen3":
            expected_sources = {"transformers/" + k: v for k, v in QWEN_SOURCES.items()}
        else:
            extra = json.loads((repo / "configs/diagnostics/internvl3_hnlo_generation_sources.v1.json").read_bytes())
            expected_sources = {"transformers/" + r["path"]: r["sha256"] for r in extra["files"]}
        if any(source_hashes.get(k) != v for k, v in expected_sources.items()):
            raise ValueError("PINNED_GENERATION_SOURCE_RECEIPTS_REQUIRED")
        for i, row in enumerate(rows):
            cap = Journal(root / "raw" / f"sample-{i:06d}")
            if row["persisted"]:
                marker = index.read(f"sample-{i:06d}.native-call")
                if marker != {"ordinal": i, "exposure": "NATIVE_CALL_START_RECORDED_BEFORE_INVOCATION"}:
                    raise ValueError("NATIVE_CALL_EXPOSURE_MARKER_REQUIRED")
                raw = cap.read("trace")
                if (raw["generation_config"] != model["generation_config"] or
                        raw["generation_kwargs"] != {**policy["decoding"], **CAPTURE_FLAGS}):
                    raise ValueError("NATIVE_MODEL_CONFIG_OR_POLICY_CHANGED")
        counts = index.read("native-counts") if index.exists("native-counts") else None
        if counts is not None and (counts["load_calls"] != 1 or
                counts["generate_ordinals"] != list(range(len(counts["generate_ordinals"]))) or
                any(type(i) is not int or not 0 <= i < u["count"] for i in counts["generate_ordinals"])):
            raise ValueError("NATIVE_CALL_BUDGET_OR_DUPLICATE")
        if completed and (counts is None or counts["generate_ordinals"] != list(range(u["count"]))):
            raise ValueError("COMPLETE_NATIVE_COUNTS_REQUIRED")
        worker_path = root / "inference/result.json"
        worker_result = json.loads(worker_path.read_bytes()) if worker_path.exists() else {"status": "KILLED"}
        if worker_result["status"] != "RETURNED":
            completed = False
            for row in rows:
                if row["status"] == "SUCCESS":
                    row.update(status="TECHNICAL_ERROR", score=None, details=None,
                               errors=["GLOBAL_WORKER_ADMISSION_OR_FINALIZATION_FAILED"])
    return u, rows, completed, integrity


def evaluate(root, repo, tokenizer, *, source=None):
    u, rows, completed, integrity = checked(root, repo, tokenizer, source=source)
    all_metadata = load_metadata(repo)  # raw custody + explicit per-unit label approval checked
    metadata = {r["sample_id"]: all_metadata[r["sample_id"]] for r in rows}
    evaluation = metrics(rows, metadata, completed)
    evaluation.update(schema="qwen3-s2-recovery-metrics-v1", scope="SUPPLEMENTAL_RECOVERY_TRAIN_DESCRIPTIVE",
                      cohort="SUPPLEMENTAL_RECOVERY_NOT_V4_BASELINE", baseline_pooling_allowed=False)
    export(Path(root) / "report", rows, metadata, evaluation,
           {"schema": "qwen3-s2-recovery-cpu-audit-v1", "unit": u, "integrity": integrity, "results": rows,
            "cohort": "SUPPLEMENTAL_RECOVERY_NOT_V4_BASELINE", "baseline_pooling_allowed": False,
            "cpu_environment": cpu_context(repo),
            "evidence_contract": EVIDENCE, "full_vocab_replay": False,
            "claim": "RAW_SUMMARY_REPLAY_ONLY_NOT_FULL_VECTOR_RECONSTRUCTION"})
    return evaluation
