"""Closed preparation interface. No receipt, environment or backend overrides."""

import re

from . import VERSION

LOCK = "PA3_SYNTHETIC_ONLY_REAL_EXECUTION_LOCKED"
TARGET = {"model_id": "Qwen/Qwen2.5-VL-3B-Instruct",
          "revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
          "executed": False, "t1": "NOT_RUN", "runtime": "NOT_RUN"}
CASES = (
    "anomaly", "normal", "level02", "level03", "constant_anomaly",
    "constant_normal", "offset_constant", "reversed_anomaly", "reversed_normal", "invalid",
    "fenced", "escaped", "alignment", "multi_token", "wrong_generated",
    "raw_nan", "raw_inf", "raw_negative_inf", "processed_nan",
    "processed_inf", "processed_mask", "missing_step", "missing_candidate",
    "overflow", "runtime_error", "interrupt",
)
DEFAULT_CASES = ("anomaly", "normal", "level02", "level03", "invalid")


def authorize(settings):
    """Validate the entire plain-data request before any I/O or mock generation."""
    if type(settings) is not dict or set(settings) != {"mode", "run_id", "source_commit", "cases"}:
        raise PermissionError(LOCK)
    if type(settings["mode"]) is not str or settings["mode"] != "synthetic":
        raise PermissionError(LOCK)
    if (type(settings["run_id"]) is not str
            or not re.fullmatch(r"pa3-synthetic-[a-z0-9][a-z0-9_-]{0,63}", settings["run_id"])):
        raise ValueError("SYNTHETIC_RUN_ID_REQUIRED")
    if (type(settings["source_commit"]) is not str
            or not re.fullmatch(r"[0-9a-f]{40}", settings["source_commit"])):
        raise ValueError("SOURCE_COMMIT_REQUIRED_NOT_EXECUTION_AUTHORITY")
    names = settings["cases"]
    if (type(names) is not list or not names
            or any(type(n) is not str or n not in CASES for n in names)
            or len(names) != len(set(names))):
        raise PermissionError("UNIQUE_BUILTIN_SYNTHETIC_CASES_ONLY")
    return {**settings, "cases": list(names)}


def require_case(settings, name):
    settings = authorize(settings)
    if type(name) is not str or name not in settings["cases"]:
        raise PermissionError(LOCK)
    return settings


def identity(settings):
    settings = authorize(settings)
    return {"schema": VERSION, "method": "PA3_RAW_ONLY", "source": "BUILTIN_SYNTHETIC",
            "settings": settings, "target_only": dict(TARGET),
            "execution": "STDLIB_CPU_MOCK_NO_MODEL", "seed": None,
            "generation": "deterministic fixture vectors; no inference",
            "tokenizer": "ASCII mock, not Qwen T1", "prompt": "NOT_EXECUTED",
            "score": "logsumexp(z1,z2,z3)-z4", "direction": "HIGHER_IS_ANOMALY"}
