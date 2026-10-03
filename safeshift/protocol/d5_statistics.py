"""D5 domain-stratified point-cluster bootstrap, shared paired draws, no p-values."""

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import random

BOOTSTRAP_VERSION = "d5-point-cluster-python-mt19937-v1"
B = 2000
SEED = 42


@dataclass(frozen=True)
class ClusterUnit:
    sample_id: str
    domain: str
    point_id: str

    def __post_init__(self):
        if any(type(v) is not str or not v for v in (self.sample_id, self.domain, self.point_id)):
            raise ValueError("explicit sample, domain and logical point IDs required")


def bootstrap_draws(units, *, replicates=B, seed=SEED):
    """Resample the original cluster count within each domain, with replacement.

    Input has one row per image. Anomaly singleton/cluster IDs must be supplied
    explicitly by the approved manifest; never infer clusters from source-family.
    Sorting IDs makes draws invariant to model/input row order.
    """
    units = tuple(units)
    if replicates not in (2000, 5000) or seed != 42:
        raise ValueError("D5 requires B=2000 (5000 convergence only), seed=42")
    if len({u.sample_id for u in units}) != len(units) or not units:
        raise ValueError("nonempty unique image units required")
    domains = defaultdict(lambda: defaultdict(list))
    for u in sorted(units, key=lambda u: (u.domain, u.point_id, u.sample_id)):
        domains[u.domain][u.point_id].append(u.sample_id)
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        draw = []
        for clusters in domains.values():
            keys = tuple(clusters)
            for _ in keys:
                draw.extend(clusters[keys[rng.randrange(len(keys))]])
        draws.append(tuple(draw))
    return tuple(draws)


def _quantile(values, p):
    # Linear interpolation between order statistics, recorded in CI metadata.
    position = (len(values) - 1) * p
    low = math.floor(position)
    high = math.ceil(position)
    return values[low] + (values[high] - values[low]) * (position - low)


def interval(values, *, paired=False):
    values = tuple(values)
    if len(values) not in (2000, 5000):
        raise ValueError("D5 replicate count required")
    if any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in values):
        raise ValueError("use None for NA; finite scalar metrics required")
    valid = sorted(v for v in values if v is not None)
    return {"ci95": [_quantile(valid, .025), _quantile(valid, .975)] if valid else None,
            "B": len(values), "seed": SEED,
            "valid_paired_replicates" if paired else "valid_replicates": len(valid),
            "valid_fraction": len(valid) / len(values), "method": "DOMAIN_STRATIFIED_POINT_CLUSTER_PERCENTILE",
            "quantile_method": "LINEAR_ORDER_STATISTIC_INTERPOLATION",
            "version": BOOTSTRAP_VERSION, "stratification": "DOMAIN_ONLY",
            "cluster": "point_id (logical folder, not verified physical site)",
            "missing_class_replicate": "NA", "p_value_matrix": False}


def bootstrap(units, metric_a, *, metric_b=None):
    """Callbacks receive identical tuples of sample IDs, retaining multiplicity.

    Each callback must return None for an absent required class/denominator.
    See classification_statistic for a support-fixed classification callback.
    """
    draws = bootstrap_draws(units)
    a = tuple(metric_a(draw) for draw in draws)
    result = {"a": interval(a), "draws_sha256": hashlib.sha256(
        json.dumps(draws, separators=(",", ":")).encode()).hexdigest()}
    if metric_b is not None:
        b = tuple(metric_b(draw) for draw in draws)
        difference = tuple(x - y if x is not None and y is not None else None for x, y in zip(a, b))
        result.update(b=interval(b), paired_difference=interval(difference, paired=True))
    return result


def classification_statistic(samples, metric):
    """Freeze original support before resampling; never shrink K per replicate."""
    from .d5_engine import classification
    samples = tuple(samples)
    indexed = {s.sample_id: s for s in samples}
    if len(indexed) != len(samples):
        raise ValueError("unique image predictions required")
    required = tuple(sorted({s.true_safety_level for s in samples}))

    def compute(ids):
        summary = classification(tuple(indexed[i] for i in ids), required_classes=required)
        value = summary[metric]
        return value["value"] if isinstance(value, dict) else value
    return compute
