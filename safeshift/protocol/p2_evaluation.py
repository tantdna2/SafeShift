"""Label-free artifact export, followed by an explicit evaluation-only GT join."""

from dataclasses import dataclass
from pathlib import Path

from safeshift.data.manifest import DOMAINS, SPLITS
from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA, json_bytes, safe_path, sha
from safeshift.runners.p2_harness import ADAPTER, identities, registry, verified_raw
from safeshift.runners.production_classification import PARSER_VERSION
from safeshift.runners.p2_bridge import call_identity
from .classification_policy import MODELS, ROOT
from .d9r24_metrics import DisagreementSample
from .schema import HAZARDS, SAFETY_LEVELS, strict_json

PREDICTION_FIELDS = {"sample_id", "model_key", "run_id", "call_id", "parse_status", "safety_level",
                     "raw_artifact", "raw_sha256", "raw_size_bytes", "adapter_version", "parser_version"}


def prediction(row):
    if set(row) != PREDICTION_FIELDS:
        raise ValueError("LABEL_FREE_PREDICTION_SCHEMA_REQUIRED")
    if row["model_key"] not in MODELS or row["adapter_version"] != ADAPTER or row["parser_version"] != PARSER_VERSION:
        raise ValueError("PREDICTION_IDENTITY_MISMATCH")
    if row["parse_status"] == "SUCCESS":
        if row["safety_level"] not in SAFETY_LEVELS:
            raise ValueError("SUCCESS_REQUIRES_CANONICAL_LEVEL")
    elif row["parse_status"] != "INVALID" or row["safety_level"] is not None:
        # FAILED/NOT_ATTEMPTED are incomplete scientific runs, not parse INVALID.
        raise ValueError("INCOMPLETE_OR_NONCANONICAL_PREDICTION")
    return row


def export_predictions(run_root, *, repo=ROOT):
    """Read only completed artifacts, never image pixels/GT or raw output to a table."""
    root = Path(run_root).absolute()
    # All artifact paths are validated against their run root before opening.
    def read(name):
        return strict_json(safe_path(root, name).read_bytes())
    status = read("run_status.json")
    if status["status"] != "COMPLETED":
        raise ValueError("COMPLETED_INFERENCE_REQUIRED")
    for name, digest in status["artifact_sha256"].items():
        if sha(safe_path(root, name).read_bytes()) != digest:
            raise ValueError("ARTIFACT_INTEGRITY_FAILURE")
    run = read("run_manifest.json")
    if run["version"] not in ("d9r25-run-v1", "d9r26-run-v1"):
        raise ValueError("RUN_VERSION_REQUIRED")
    shard = read("shard_manifest.json")
    if run["protocol_identity"]["identity_sha256"] != identities(repo):
        raise ValueError("PROTOCOL_IDENTITY_MISMATCH")
    if run["model_condition"] != registry(repo)[run["model_key"]]:
        raise ValueError("MODEL_CONDITION_MISMATCH")
    body = {k: v for k, v in shard.items() if k != "shard_manifest_sha256"}
    if sha(json_bytes(body)) != run["shard_manifest_sha256"] or shard["shard_manifest_sha256"] != run["shard_manifest_sha256"]:
        raise ValueError("SHARD_IDENTITY_MISMATCH")
    expected = shard["ordered_sample_ids"]
    if set(status["samples"]) != set(expected):
        raise ValueError("SHARD_COHORT_MISMATCH")
    rows = []
    for sid in expected:
        directory = "calls/" + sha(sid.encode())
        row = prediction(read(directory + "/parsed.json"))
        meta = read(directory + "/metadata.json")
        if (row["sample_id"] != sid or row["model_key"] != run["model_key"]
                or row["run_id"] != run["run_id"]
                or row["call_id"] != (call_identity(sid) if run["version"] == "d9r26-run-v1" else "call1")
                or row["call_id"] != meta["call_id"]
                or row["parse_status"] != status["samples"][sid]
                or row["parse_status"] != meta["parse_status"]
                or row["raw_artifact"] != directory + "/response.raw"
                or row["raw_sha256"] != meta["raw_response"]["sha256"]
                or row["raw_size_bytes"] != meta["raw_response"]["size_bytes"]):
            raise ValueError("CALL_IDENTITY_MISMATCH")
        safe_path(root, row["raw_artifact"])
        verified_raw(root / directory, meta["raw_response"])
        rows.append(row)
    return {"version": "d9r25-parsed-export-v1", "status": "COMPLETED",
            "protocol_identity": run["protocol_identity"], "model_key": run["model_key"],
            "run_id": run["run_id"], "run_manifest_sha256": sha((root / "run_manifest.json").read_bytes()),
            "shard": shard, "rows": sorted(rows, key=lambda r: r["sample_id"])}


def align_four_models(exports):
    """Require all shards of all four models, exactly one call per image/model.

    No GT accepted; deterministic alignment precedes the evaluation join.
    """
    grouped = {model: {} for model in MODELS}
    identities_seen, cohort, shards = None, None, {model: set() for model in MODELS}
    for table in exports:
        if set(table) != {"version", "status", "protocol_identity", "model_key", "run_id",
                          "run_manifest_sha256", "shard", "rows"}:
            raise ValueError("LABEL_FREE_EXPORT_SCHEMA_REQUIRED")
        model = table["model_key"]
        if model not in MODELS or table["status"] != "COMPLETED" or table["version"] != "d9r25-parsed-export-v1":
            raise ValueError("FOUR_COMPLETED_MODELS_REQUIRED")
        identity = table["protocol_identity"]
        if (set(identity) != {"protocol_id", "identity_sha256", "dataset_fingerprint",
                              "source_manifest_sha256", "source_kind"}
                or identity["identity_sha256"] != identities()
                or identity["source_kind"] not in ("SYNTHETIC", "INSPECSAFE")):
            raise ValueError("PROTOCOL_IDENTITY_MISMATCH")
        if identity["source_kind"] == "INSPECSAFE":
            if identity["dataset_fingerprint"] != FINGERPRINT or identity["source_manifest_sha256"] != MANIFEST_SHA:
                raise ValueError("P2_DATASET_IDENTITY_MISMATCH")
        elif identity["dataset_fingerprint"] != "SYNTHETIC_NOT_INSPECSAFE":
            raise ValueError("SYNTHETIC_COHORT_REQUIRED")
        if identities_seen is None:
            identities_seen = identity
        if identity != identities_seen or identity["protocol_id"] != "P2":
            raise ValueError("PROTOCOL_IDENTITY_MISMATCH")
        current = table["shard"]
        shard_body = {k: v for k, v in current.items() if k != "shard_manifest_sha256"}
        if (sha(json_bytes(shard_body)) != current["shard_manifest_sha256"]
                or current["source_manifest_sha256"] != identity["source_manifest_sha256"]
                or current["shard_algorithm_version"] != "sample-id-lexical-modulo-v1"):
            raise ValueError("SHARD_IDENTITY_MISMATCH")
        ids = current["cohort_sample_ids"]
        if ids != sorted(set(ids)):
            raise ValueError("DUPLICATE_OR_UNORDERED_COHORT")
        if cohort is None:
            cohort = ids
        if ids != cohort:
            raise ValueError("COHORT_ALIGNMENT_MISMATCH")
        if identity["source_kind"] == "INSPECSAFE" and len(ids) != 5013:
            raise ValueError("P2_REQUIRES_5013")
        count, index = current["shard_count"], current["shard_index"]
        if type(count) is not int or count < 1 or type(index) is not int or not 0 <= index < count:
            raise ValueError("INVALID_SHARD")
        if shards[model] and any(c != count for c, i in shards[model]):
            raise ValueError("INCONSISTENT_SHARD_COUNT")
        if (count, index) in shards[model]:
            raise ValueError("DUPLICATE_SHARD")
        shards[model].add((count, index))
        expected = ids[index::count]
        if current["ordered_sample_ids"] != expected or [r["sample_id"] for r in table["rows"]] != expected:
            raise ValueError("SHARD_ALIGNMENT_MISMATCH")
        for row in table["rows"]:
            prediction(row)
            sid = row["sample_id"]
            if row["model_key"] != model or row["run_id"] != table["run_id"] or sid in grouped[model]:
                raise ValueError("DUPLICATE_OR_MISALIGNED_MODEL_PREDICTION")
            grouped[model][sid] = row
    if cohort is None or any(set(rows) != set(cohort) for rows in grouped.values()):
        raise ValueError("FOUR_MODEL_COHORT_INCOMPLETE")
    for model, seen in shards.items():
        if not seen or seen != {(next(iter(seen))[0], i) for i in range(next(iter(seen))[0])}:
            raise ValueError("MISSING_SHARD")
    return tuple({"sample_id": sid, "predictions": {m: grouped[m][sid]["safety_level"] for m in MODELS},
                  "parse_status": {m: grouped[m][sid]["parse_status"] for m in MODELS}}
                 for sid in cohort)


@dataclass(frozen=True)
class EvaluationJoin:
    samples: tuple
    metadata: tuple  # original split/domain/point/GT/memberships retained at evaluation only


def join_evaluation(exports, evaluation_records):
    aligned = align_four_models(exports)  # must complete before consulting any GT
    rows = tuple(dict(row) for row in evaluation_records)
    fields = {"sample_id", "true_safety_level", "folder_domain", "split", "point_id", "hazard_memberships"}
    for row in rows:
        if (set(row) != fields or row["true_safety_level"] not in SAFETY_LEVELS
                or row["folder_domain"] not in DOMAINS or row["split"] not in SPLITS
                or not set(row["hazard_memberships"]) <= set(HAZARDS)):
            raise ValueError("EVALUATION_SCHEMA_REQUIRED")
    by_id = {r["sample_id"]: r for r in rows}
    if len(by_id) != len(rows) or set(by_id) != {r["sample_id"] for r in aligned}:
        raise ValueError("GT_COHORT_ALIGNMENT_MISMATCH")
    samples = []
    for row in aligned:
        gt = by_id[row["sample_id"]]
        samples.append(DisagreementSample(row["sample_id"], gt["true_safety_level"], gt["folder_domain"],
                       row["predictions"], frozenset(gt["hazard_memberships"]), gt["point_id"], row["parse_status"]))
    return EvaluationJoin(tuple(samples), tuple(by_id[row["sample_id"]] for row in aligned))
