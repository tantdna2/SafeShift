"""Deterministic JSON reporting of D5 outputs; no inference or role promotion."""

import json

from .d5_engine import D5MetricEngine

REPORT_VERSION = "d5-report-d9r19-v1"
EXPLORATORY_MODELS = frozenset({"qwen3", "moondream", "paligemma"})


def report(model, *, classification_samples=(), primary_spatial=(), exploratory_spatial=(),
           bootstrap_metadata=None):
    if model not in {"qwen3", "qwen2_5", "internvl3", "moondream", "paligemma"}:
        raise ValueError("unknown roster model")
    classification_samples, primary_spatial, exploratory_spatial = (
        tuple(classification_samples), tuple(primary_spatial), tuple(exploratory_spatial))
    if model == "paligemma" and classification_samples:
        raise ValueError("PALIGEMMA_CLASSIFICATION_NOT_PARTICIPATING")
    if model != "moondream" and any(s.participation == "PARTICIPATING" for s in primary_spatial):
        raise ValueError("PRIMARY_GROUNDING_NOT_PARTICIPATING")
    if exploratory_spatial and model not in EXPLORATORY_MODELS:
        raise ValueError("EXPLORATORY_GROUNDING_EXCLUDED")
    for samples in (classification_samples, primary_spatial, exploratory_spatial):
        if len({s.sample_id for s in samples}) != len(samples):
            raise ValueError("one prediction per IMAGE required in reports")
    engine = D5MetricEngine()
    not_participating = {"participation": "NOT_PARTICIPATING", "metrics": None}
    pending = {"status": "NO_INPUT", "metrics": None}
    cls = model != "paligemma"
    primary = model == "moondream"
    return {
        "report_version": REPORT_VERSION, "metric_engine_version": engine.version, "model": model,
        "classification_RQ1": engine.rq1(classification_samples) if classification_samples else pending if cls else not_participating,
        "RQ2_primary_hazard_atoms": engine.rq2(classification_samples) if classification_samples else pending if cls else not_participating,
        "RQ2_grouped_secondary_exploratory": engine.rq2(classification_samples, grouped=True) if classification_samples else pending if cls else not_participating,
        "primary_direct_RQ3_A": engine.direct_grounding(primary_spatial) if primary_spatial else pending if primary else not_participating,
        "primary_weak_proxy_RQ3_B": engine.weak_proxy(primary_spatial) if primary_spatial else pending if primary else not_participating,
        "exploratory_grounding": {"analysis_level": "SECONDARY_EXPLORATORY",
                                  "execution_contract": "BLOCKED_PENDING_AUTHORITY",
                                  "production_qualification": False, "promotes_model": False,
                                  "direct": engine.direct_grounding(exploratory_spatial) if exploratory_spatial else pending,
                                  "weak_proxy": engine.weak_proxy(exploratory_spatial) if exploratory_spatial else pending},
        "bootstrap_CI_metadata": bootstrap_metadata if bootstrap_metadata is not None else {"status": "NOT_COMPUTED"},
        "participation": {"classification": "PARTICIPATING" if cls else "NOT_PARTICIPATING",
                          "primary_grounding": "GATE_ELIGIBLE_PRODUCTION_ADAPTER_PENDING" if primary else "NOT_PARTICIPATING",
                          "exploratory_grounding": "INCLUDED" if model in EXPLORATORY_MODELS else "EXCLUDED"},
        "inspecsafe_inference_authorized": False, "protocol_freeze": "PENDING",
    }


def render_json(result):
    return json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
