"""Subset of historical d9r24_metrics.classification_metrics at 31a04e6.

Rows are true labels; columns are canonical predictions plus INVALID.
INVALID stays in support/recall denominators. Empty-class recall is None.
This module does not implement HNLO, AUROC, RQ strata or protocol freeze.
"""

from collections.abc import Iterable

from safeshift.data.schema import PredictionRecord, SAFETY_LEVELS, SampleRecord
from safeshift.data.validation import validate_predictions, validate_samples


def classification_metrics(
    samples: Iterable[SampleRecord], predictions: Iterable[PredictionRecord],
) -> dict:
    """Join unique records by exact ID set, then count each image once.

    Reject missing/extra predictions rather than silently changing coverage.
    Predictions may be in a different order from ground truth.
    """
    samples = validate_samples(samples)
    predictions = validate_predictions(predictions)
    by_id = {row.sample_id: row.predicted_safety_level for row in predictions}
    expected = {row.sample_id for row in samples}
    if expected != set(by_id):
        raise ValueError("predictions must match the exact ground-truth sample_id set")

    counts = {true: {pred: 0 for pred in (*SAFETY_LEVELS, "INVALID")}
              for true in SAFETY_LEVELS}
    for sample in samples:
        prediction = by_id[sample.sample_id]
        counts[sample.true_safety_level][prediction if prediction is not None else "INVALID"] += 1

    support = {level: sum(counts[level].values()) for level in SAFETY_LEVELS}
    invalid_n = sum(counts[level]["INVALID"] for level in SAFETY_LEVELS)
    return {
        "n_images": len(samples),
        "valid_canonical_n": len(samples) - invalid_n,
        "invalid_n": invalid_n,
        "confusion_matrix": counts,
        "support": support,
        "per_class": {
            level: {
                "true_positive": counts[level][level],
                "recall": counts[level][level] / support[level] if support[level] else None,
            } for level in SAFETY_LEVELS
        },
    }
