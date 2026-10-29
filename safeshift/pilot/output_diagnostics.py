"""Descriptive raw-output diagnostics. No thresholds, stop gate or label repair."""
from collections import Counter
from pathlib import Path

from .artifacts import read, sha
from .contract import digest, parse_label


def summarize(run):
    sequences, responses, lengths = Counter(), Counter(), Counter()
    files = {}
    valid = eos = at_cap = synthetic = 0
    for path in sorted((Path(run) / "samples").glob("*/raw.json")):
        raw = read(path)
        ids = raw["generated_ids"]
        sequences[digest(ids)] += 1
        responses[digest(raw["response"])] += 1
        lengths[str(len(ids))] += 1
        valid += parse_label(raw["response"]) is not None
        eos += bool(ids and ids[-1] in raw.get("eos_token_ids", []))
        at_cap += len(ids) == 64
        synthetic += raw.get("evidence_kind") == "SYNTHETIC_SCRIPTED_LOGITS_NOT_MODEL_PREDICTIONS"
        files[path.relative_to(run).as_posix()] = sha(path)
    return {"schema": "safeshift-output-diagnostics-v1", "raw_records": sum(sequences.values()),
            "strict_json_valid": valid, "strict_json_invalid": sum(sequences.values()) - valid,
            "unique_token_sequences": len(sequences), "largest_identical_token_sequence_n": max(sequences.values(), default=0),
            "token_sequence_group_sizes": sorted(sequences.values(), reverse=True),
            "unique_responses": len(responses), "response_group_sizes": sorted(responses.values(), reverse=True),
            "generated_length_counts": dict(lengths), "ends_with_eos_n": eos, "at_max64_n": at_cap,
            "explicit_synthetic_raw_records": synthetic, "raw_inventory_sha256": digest(files),
            "interpretation": "DESCRIPTIVE_ONLY_NO_NEW_THRESHOLD_GATE_METRIC_OR_LABEL_CHANGE; repeated output is not a causal diagnosis"}
