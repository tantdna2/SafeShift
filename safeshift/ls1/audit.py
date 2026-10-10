"""Recompute LS1 scores and calibration from sealed compact raw artifacts on CPU."""

import argparse
import hashlib
from pathlib import Path

from safeshift.data.p2_execution import safe_path
from safeshift.protocol.p21_schema import parse_classification
from safeshift.protocol.schema import strict_json
from .artifacts import verify_run, read_verified, json_bytes
from .core import REFERENCE_SPEC, score_decision, calibrate, validate_trace


def audit_run(root):
    root = Path(root).absolute()
    inventory = verify_run(root)
    manifest = strict_json((root / "run_manifest.json").read_bytes())
    status = strict_json((root / "run_status.json").read_bytes())
    if manifest["protocol"] != "LS1" or status["status"] != "FINISHED":
        raise ValueError("FINISHED_LS1_RUN_REQUIRED")
    results = strict_json((root / "results.json").read_bytes())
    cohort = strict_json((root / "cohort.json").read_bytes())["rows"]
    expected = [r["sample_id"] for r in cohort]
    if len(set(expected)) != len(expected) or [r["sample_id"] for r in results] != expected:
        raise ValueError("COHORT_RESULT_ALIGNMENT_MISMATCH")
    for result in results:
        raw_path = safe_path(root, result["raw_path"])
        if inventory[result["raw_path"]] != result["raw_receipt"]:
            raise ValueError("RESULT_RAW_RECEIPT_MISMATCH")
        raw = read_verified(raw_path, result["raw_receipt"])
        if raw["sample_id"] != result["sample_id"] or raw["context"]["run_id"] != manifest["run_id"]:
            raise ValueError("RAW_SAMPLE_OR_RUN_MISMATCH")
        if any(manifest.get(k) != value for k, value in raw["context"].items()):
            raise ValueError("RAW_CONTEXT_MISMATCH")
        cohort_row = next(row for row in cohort if row["sample_id"] == result["sample_id"])
        if raw["image_sha256"] != cohort_row["image_sha256"]:
            raise ValueError("RAW_IMAGE_CHECKSUM_MISMATCH")
        parsed = parse_classification(raw["decoded_text"])
        validate_trace(raw)
        if result["status"] == "INVALID":
            if parsed.success or result["modes"] is not None:
                raise ValueError("INVALID_RESULT_INCONSISTENT")
            continue
        if result["status"] != "SUCCESS" or not parsed.success:
            raise ValueError("RESULT_PARSE_STATUS_MISMATCH")
        mapping = result["score"]["decision"]
        if parsed.value.safety_level != mapping["generated_label"]:
            raise ValueError("RESULT_GENERATED_LABEL_MISMATCH")
        if raw["continuation_ids"][:mapping["step"]] != mapping["prefix_ids"]:
            raise ValueError("RESULT_DECISION_PREFIX_MISMATCH")
        response = mapping["prefix_ids"] + [mapping["token_ids"][
            ("Level01", "Level02", "Level03", "Level04").index(mapping["generated_label"])]] + mapping["suffix_ids"]
        if response != mapping["response_ids"] or raw["continuation_ids"][:len(response)] != response:
            raise ValueError("RESULT_RESPONSE_TOKEN_MISMATCH")
        tail = raw["continuation_ids"][len(response):]
        if tail and (len(tail) != 1 or tail[0] not in mapping["eos_token_ids"]):
            raise ValueError("RESULT_TERMINAL_EOS_MISMATCH")
        score = score_decision(raw, mapping)
        if score != result["score"]:
            raise ValueError("SCORE_RECOMPUTATION_MISMATCH")
        key = hashlib.sha256(json_bytes(mapping["prefix_ids"])).hexdigest()
        if key != result["reference_key"]:
            raise ValueError("REFERENCE_KEY_MISMATCH")
        references = {}
        for name, pixel in REFERENCE_SPEC:
            locator = "references/" + key + "/" + name + ".raw.json"
            reference = read_verified(safe_path(root, locator), inventory[locator])
            if (reference["pixel_value"] != pixel or reference["prefix_ids"] != mapping["prefix_ids"]
                    or reference["image_size"] != [448, 448] or reference["image_mode"] != "RGB"):
                raise ValueError("REFERENCE_SPEC_MISMATCH")
            if reference["context"] != raw["context"] or len(reference["steps"]) != 1:
                raise ValueError("REFERENCE_CONTEXT_MISMATCH")
            validate_trace(reference)
            expected_hash = hashlib.sha256(bytes([pixel]) * (448 * 448 * 3)).hexdigest()
            if reference["image_pixel_sha256"] != expected_hash:
                raise ValueError("REFERENCE_PIXEL_CHECKSUM_MISMATCH")
            references[name] = [reference["steps"][0]["raw"]["candidate_values"][str(i)] for i in mapping["token_ids"]]
        modes = calibrate(score["raw_label_logits"], references, protect_level01=manifest["protect_level01"])
        if modes != result["modes"]:
            raise ValueError("CALIBRATION_RECOMPUTATION_MISMATCH")
    return {"status": "PASS", "protocol": "LS1", "recomputed_n": len(results),
            "limitations": "Checksum consistency and recomputation, not proof of artifact authenticity or model accuracy."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(audit_run(args.run))


if __name__ == "__main__":
    main()
