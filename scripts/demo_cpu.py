"""Deterministic synthetic CPU demonstration; never a research result.

Run from the repository root: python -B -m scripts.demo_cpu
"""

import json

from safeshift.data.validation import (
    prediction_from_mapping, sample_from_mapping, validate_predictions, validate_samples,
)
from safeshift.evaluation.metrics import classification_metrics

DISCLAIMER = "SYNTHETIC DEMO — NOT RESEARCH RESULT"


def build_report() -> dict:
    """Use invented IDs/labels and explicit predictions, without calling a model."""
    examples = (
        ("synthetic-001", "Level01", "Level01"),
        ("synthetic-002", "Level01", None),
        ("synthetic-003", "Level02", "Level04"),
        ("synthetic-004", "Level03", "Level03"),
        ("synthetic-005", "Level04", "Level04"),
        ("synthetic-006", "Level04", "Level02"),
    )
    samples = validate_samples(sample_from_mapping({"sample_id": sid, "true_safety_level": true})
                               for sid, true, _ in examples)
    predictions = validate_predictions(prediction_from_mapping(
        {"sample_id": sid, "predicted_safety_level": pred}) for sid, _, pred in examples)
    return {"notice": DISCLAIMER, "data_source": "handwritten synthetic records",
            "model_execution": False, "metrics": classification_metrics(samples, predictions)}


def main() -> None:
    # ASCII escaping keeps JSON portable on Windows consoles; decoding restores the notice.
    print(json.dumps(build_report(), indent=2, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
