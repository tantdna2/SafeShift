"""Issue167 full-TRAIN planning. Pure metadata; no data access or run authority.

History is an explicitly selected, sealed lineage, never a latest/best-result
query. Checksums establish custody, not scientific selection or permission.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import json
import re

from safeshift.pilot.contract import digest, require_hash, MASTER_SHA, DATA_REVISION
from safeshift.pilot.manifest import validate_master
from .source import require

COUNT = 3763
MODELS = ("qwen3", "internvl35", "minicpm4")
STATUSES = ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED")
SCHEMA = "safeshift-fulltrain-plan-v1"
IDENTITY_FIELDS = ("model_revision", "implementation_sha256", "configuration_sha256",
                   "prompt_sha256", "parser_sha256", "generation_sha256",
                   "preprocessing_sha256", "checkpoint_sha256", "runtime_sha256")
REMEDIES = {
    "NOT_ATTEMPTED": "Schedule once under a new bounded run grant.",
    "INVALID": "Inspect exact raw/strict parser/tokenizer and generation boundary; no label rescue.",
    "LOAD_ENVIRONMENT": "Repair pinned Python/packages/ABI/load path; regress before repair.",
    "GPU_OOM": "Diagnose allocation and resource envelope; precision/config changes need version review.",
    "TIMEOUT": "Check bounded worker deadline and partial custody before targeted repair.",
    "PIPELINE": "Fix transport/storage/preprocessing; preserve all partial evidence.",
    "INTERRUPTED": "Reconcile sealed raw and native-call marker; unknown calls require explicit repair.",
    "UNKNOWN": "Investigate retained error/raw; do not guess cause or automatically rerun.",
}


def token(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value), "SAFE_ID_REQUIRED")
    return value


def identity(value):
    require(type(value) is dict and set(value) == {"model_key", "model_id", "hnlo_policy", *IDENTITY_FIELDS},
            "EXACT_EXECUTION_IDENTITY_REQUIRED")
    require(value["model_key"] in MODELS and type(value["model_id"]) is str and value["model_id"], "MODEL_IDENTITY")
    require(re.fullmatch(r"[0-9a-f]{40}", value["model_revision"]), "EXACT_MODEL_REVISION")
    for field in IDENTITY_FIELDS[1:]:
        require_hash(value[field])
    require(value["hnlo_policy"] in ("LABEL_ONLY", "LOCKED_EXISTING_METHOD"), "HNLO_POLICY")
    require(value["model_key"] != "minicpm4" or value["hnlo_policy"] == "LABEL_ONLY", "MINICPM_LABEL_ONLY")
    return deepcopy(value)


def cohort(master_bytes):
    """Project the already hash-checked original master without GT/path fields.

    Check original bytes before parsing; no caller-provided hash substitutes
    for the historical source lock. No filesystem I/O is performed here.
    """
    require(type(master_bytes) is bytes and hashlib.sha256(master_bytes).hexdigest() == MASTER_SHA, "ORIGINAL_MASTER_CHECKSUM")
    master = json.loads(master_bytes)
    rows = validate_master(master)
    return {"schema": "safeshift-fulltrain-cohort-v1", "split": "TRAIN", "master_sha256": MASTER_SHA,
            "data_revision": DATA_REVISION, "scope": "PRIVATE_TRAIN_METADATA",
            "samples": [{"ordinal": i, "sample_id": r["sample_id"], "image_sha256": r["image_sha256"]}
                        for i, r in enumerate(rows)]}


def validate_cohort(value, expected_sha256):
    require_hash(expected_sha256)
    require(type(value) is dict and set(value) == {"schema", "split", "master_sha256", "data_revision", "scope", "samples"},
            "COHORT_FIELDS")
    require(digest(value) == expected_sha256, "COHORT_CHECKSUM")
    require(value["schema"] == "safeshift-fulltrain-cohort-v1" and value["split"] == "TRAIN", "TRAIN_ONLY")
    require(value["scope"] in ("SYNTHETIC_ONLY", "PRIVATE_TRAIN_METADATA"), "COHORT_SCOPE")
    require(value["master_sha256"] == MASTER_SHA and value["data_revision"] == DATA_REVISION, "MASTER_SOURCE_LOCK")
    rows = value["samples"]
    require(type(rows) is list and len(rows) == COUNT, "EXACT_3763_PLAN")
    seen = set()
    for i, r in enumerate(rows):
        require(type(r) is dict and set(r) == {"ordinal", "sample_id", "image_sha256"}, "NO_GT_OR_PATH_IN_EXECUTION_PLAN")
        require(type(r["ordinal"]) is int and r["ordinal"] == i, "EXACT_ORDER")
        token(r["sample_id"])
        require(r["sample_id"] not in seen, "DUPLICATE_SAMPLE_ID")
        seen.add(r["sample_id"])
        require_hash(r["image_sha256"])
    return deepcopy(rows)


def same_cohort(cohorts):
    require(type(cohorts) is dict and set(cohorts) == set(MODELS), "THREE_CANDIDATE_PLANS_REQUIRED_NOT_ROSTER_APPROVAL")
    for value in cohorts.values():
        validate_cohort(value, digest(value))
    require(len({digest(v) for v in cohorts.values()}) == 1, "CROSS_MODEL_COHORT_ORDER_CHECKSUM_MISMATCH")
    return digest(next(iter(cohorts.values())))


def cause(record):
    if record["status"] in ("SUCCESS", "NOT_ATTEMPTED", "INVALID"):
        return record["status"]
    error = record.get("error", {})
    if record.get("reason") == "INTERRUPTED_OR_TORN_EVIDENCE":
        return "INTERRUPTED"
    if error.get("category") == "OOM":
        return "GPU_OOM"
    if error.get("type") == "TimeoutError":
        return "TIMEOUT"
    if error.get("stage") == "model_load" or error.get("category") == "LIBRARY":
        return "LOAD_ENVIRONMENT"
    if error.get("stage") in ("preprocessing", "storage", "pipeline"):
        return "PIPELINE"
    return "UNKNOWN"


def checked_history(history, rows, manifest_hash, expected_hash):
    """Validate a complete ordered chain; no branches or silently missing ancestors."""
    require(type(history) is list and digest(history) == expected_hash, "HISTORY_CHECKSUM")
    ids = {r["sample_id"]: r for r in rows}
    runs, attempts, series, previous = set(), set(), {}, []
    for h in history:
        require(set(h) == {"run_id", "attempt_id", "series_id", "identity", "cohort_sha256", "parent_history_sha256",
                           "action", "records", "evidence_sha256", "repair"}, "HISTORY_FIELDS")
        for n in ("run_id", "attempt_id", "series_id"):
            token(h[n])
        require(h["run_id"] not in runs and h["attempt_id"] not in attempts, "DUPLICATE_ATTEMPT")
        require(h["parent_history_sha256"] == digest(previous), "MISSING_OR_REORDERED_ANCESTOR")
        require(h["cohort_sha256"] == manifest_hash, "HISTORY_COHORT_MISMATCH")
        spec = identity(h["identity"])
        require(h["action"] in ("initial", "resume", "repair", "rerun"), "HISTORY_ACTION")
        require_hash(h["evidence_sha256"])
        sid = h["series_id"]
        if sid in series:
            require(series[sid] == spec and h["action"] in ("resume", "repair"), "SERIES_IDENTITY_OR_ACTION_DRIFT")
        else:
            require(h["action"] in ("initial", "rerun"), "SERIES_ORIGIN_MISSING")
            require((h["action"] == "initial") == (not previous), "HISTORY_INITIAL_VS_RERUN")
            series[sid] = spec
        require(type(h["records"]) is list, "HISTORY_RECORDS")
        prior = {}
        for ancestor in previous:
            if ancestor["series_id"] == sid:
                for old in ancestor["records"]:
                    if old["status"] != "NOT_ATTEMPTED":
                        prior[old["sample_id"]] = old
        repair = h["repair"]
        if h["action"] == "repair":
            require(type(repair) is dict and set(repair) == {"targets", "fix_sha256", "regression_sha256", "diagnosis"}, "HISTORY_REPAIR_REQUIRED")
            require_hash(repair["fix_sha256"])
            require_hash(repair["regression_sha256"])
            require(type(repair["diagnosis"]) is str and repair["diagnosis"].strip(), "HISTORY_REPAIR_DIAGNOSIS")
            require(type(repair["targets"]) is dict and repair["targets"], "HISTORY_REPAIR_TARGETS")
            for sample, checksum in repair["targets"].items():
                require(sample in prior and prior[sample]["status"] in ("INVALID", "TECHNICAL_ERROR")
                        and digest(prior[sample]) == checksum, "HISTORY_REPAIR_TARGET_CHANGED")
        else:
            require(repair is None, "HISTORY_UNEXPECTED_REPAIR")
        seen = set()
        for record in h["records"]:
            sample = record["sample_id"]
            require(sample in ids and sample not in seen, "HISTORY_DUPLICATE_OR_UNKNOWN_ID")
            seen.add(sample)
            require(record["image_sha256"] == ids[sample]["image_sha256"], "HISTORY_INPUT_CHANGED")
            require(record["status"] in STATUSES, "HISTORY_STATUS")
            require(type(record["native_calls"]) is int and record["native_calls"] in (0, 1), "HISTORY_CALL_COUNT")
            require(type(record["attempts"]) is int and record["attempts"] in (0, 1), "HISTORY_ATTEMPT_COUNT")
            if record["status"] != "NOT_ATTEMPTED":
                if h["action"] == "repair":
                    require(sample in repair["targets"], "HISTORY_UNAUTHORIZED_REPAIR")
                else:
                    require(sample not in prior, "HISTORY_DUPLICATE_CONSUMED_ID")
            if record["status"] in ("SUCCESS", "INVALID"):
                require_hash(record.get("raw_sha256"))
                require(record["native_calls"] == record["attempts"] == 1, "COMPLETION_WITHOUT_CALL")
                require((record["status"] == "SUCCESS" and record["label"] in ("Level01", "Level02", "Level03", "Level04"))
                        or (record["status"] == "INVALID" and record["label"] is None), "STATUS_LABEL_MISMATCH")
            else:
                require(record.get("label") is None, "FAILURE_HAS_LABEL")
                if record["status"] == "NOT_ATTEMPTED":
                    require(record["native_calls"] == record["attempts"] == 0, "PENDING_HAS_CALL")
        runs.add(h["run_id"])
        attempts.add(h["attempt_id"])
        previous.append(h)
    return deepcopy(history)


def plan(cohort_value, cohort_hash, spec, history, history_hash, *, action, series_id,
         run_id, attempt_id, max_calls, max_seconds, repair=None):
    """Plan all 3763 IDs; ordinary resume never silently repairs a consumed call.

    Repair requires exact target outcome hashes plus a fix and regression receipt.
    These are preparation records, NOT execution grants or comparability approval.
    """
    rows = validate_cohort(cohort_value, cohort_hash)
    spec = identity(spec)
    history = checked_history(history, rows, cohort_hash, history_hash)
    for t in (series_id, run_id, attempt_id):
        token(t)
    require(action in ("initial", "resume", "repair", "rerun"), "ACTION")
    require(type(max_calls) is int and 1 <= max_calls <= COUNT, "EXPLICIT_CALL_CAP")
    require(type(max_seconds) is int and 1 <= max_seconds <= 43200, "EXPLICIT_TIME_CAP")
    require(all(h["run_id"] != run_id and h["attempt_id"] != attempt_id for h in history), "ATTEMPT_ALREADY_EXISTS")
    require(all(h["identity"]["model_key"] == spec["model_key"] for h in history), "CROSS_MODEL_HISTORY")
    active = [h for h in history if h["series_id"] == series_id]
    if action in ("initial", "rerun"):
        require(not active, "NEW_SERIES_REQUIRED")
        require((action == "initial") == (not history), "INITIAL_VS_RERUN")
    else:
        require(active and all(h["identity"] == spec for h in active), "NEW_VERSION_REQUIRES_NEW_SERIES")
    lineage = {r["sample_id"]: [] for r in rows}
    for h in history:
        for r in h["records"]:
            lineage[r["sample_id"]].append({"run_id": h["run_id"], "series_id": h["series_id"],
                                           "record_sha256": digest(r), **r})
    current = {}
    for h in active:
        for r in h["records"]:
            if r["status"] != "NOT_ATTEMPTED":
                current[r["sample_id"]] = r
    targets = {}
    if action == "repair":
        require(type(repair) is dict and set(repair) == {"targets", "fix_sha256", "regression_sha256", "diagnosis"}, "EXPLICIT_REPAIR_CASE_REQUIRED")
        for field in ("fix_sha256", "regression_sha256"):
            require_hash(repair[field])
        require(type(repair["diagnosis"]) is str and repair["diagnosis"].strip(), "REPAIR_DIAGNOSIS_REQUIRED")
        targets = repair["targets"]
        require(type(targets) is dict and targets, "EXACT_REPAIR_TARGETS_REQUIRED")
        for sid, checksum in targets.items():
            require(sid in current and current[sid]["status"] in ("INVALID", "TECHNICAL_ERROR")
                    and digest(current[sid]) == checksum, "REPAIR_ONLY_EXACT_FAILED_OUTCOMES")
    else:
        require(repair is None, "REPAIR_RECORD_ON_WRONG_ACTION")
    accounting, pending = [], []
    for row in rows:
        sid = row["sample_id"]
        record = current.get(sid, {"status": "NOT_ATTEMPTED"})
        eligible = sid in targets if action == "repair" else record["status"] == "NOT_ATTEMPTED"
        if eligible:
            pending.append(row["ordinal"])
        why = cause(record)
        accounting.append({**row, "status": record["status"], "cause": why,
            "remedy": REMEDIES.get(why), "lineage": lineage[sid], "eligible": eligible})
    return {"schema": SCHEMA, "scope": cohort_value["scope"], "cohort_sha256": cohort_hash,
            "history_sha256": history_hash, "identity": spec, "action": action,
            "series_id": series_id, "run_id": run_id, "attempt_id": attempt_id,
            "max_calls": max_calls, "max_seconds": max_seconds, "repair": deepcopy(repair),
            "scheduled_ordinals": pending[:max_calls], "deferred_ordinals": pending[max_calls:],
            "samples": accounting, "counts": dict(Counter(r["status"] for r in accounting)),
            "scientific_selection": "PENDING", "pooling_allowed": False,
            "execution_status": "BLOCKED_O2_O3_O4_O5_O6"}


def release_report(model_key):
    """No caller-controlled approved flag; #167 grants software preparation only."""
    require(model_key in MODELS, "MODEL_KEY")
    return {"schema": "safeshift-fulltrain-release-v1", "model_key": model_key,
        "status": "BLOCKED", "authority": {n: "PENDING" for n in ("O2", "O3", "O4", "O5", "O6")},
        "gates": {"G0": "BLOCKED_AUTHORITY", "G1": "CPU_BUILD_REVIEW_REQUIRED",
                  "G2": "NOT_VERIFIED_FINAL_RUNTIME_INPUT", "G3": "CPU_TEST_RECEIPT_REQUIRED",
                  "G4": "NOT_RUN_KAGGLE", "G5": "NOT_RUN_REAL_INFERENCE", "G6": "BLOCKED_RELEASE"},
        "preflight_required": ["unique_input_marker", "exact_3763_manifest_order_sha256", "checkpoint_allowlist_sha256",
            "source_commit_sha256", "worker_python_abi", "pinned_packages_compiled_abi", "scratch_output_devices",
            "space_allocation_fsync_cleanup", "ram_cgroup_quota_deadline", "gpu_count_model_driver_visibility", "child_cuda_fp16"],
        "levels": {"ENVIRONMENT_OBSERVED": "NOT_RUN", "CPU_SOFTWARE_PASS": "NOT_RUN",
                   "LIVE_GPU_PREFLIGHT_PASS": "NOT_RUN", "WEIGHTS_LOADED": "NOT_RUN",
                   "INFERENCE_VERIFIED": "NOT_RUN", "SCIENTIFIC_QUALIFIED": "UNVERIFIED"},
        "runtime_binding": "BLOCKED_LEGACY_QWEN_MAPPING_REVIEW" if model_key == "qwen3" else "CANDIDATE_RUNTIME_REUSE_REQUIRES_FULLTRAIN_RELEASE",
        "production_calls": 0, "owner_slots": 0}


def launch(model_key, **untrusted_options):
    # Deliberately before Input/history/credentials/package/GPU access.
    release_report(model_key)
    raise PermissionError("ISSUE167_CPU_ONLY: BLOCKED_O2_O3_O4_O5_O6_AND_FINAL_RELEASE")
