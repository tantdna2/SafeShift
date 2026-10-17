"""One reviewed two-model attempt, independent of all historical grants."""

from copy import deepcopy
import hashlib
import json
import re

BASE_SHA = "6143717b1647df1ed1b2d5b0a0f23e9b03f4a9e5"
REPOSITORY = "tantdna2/SafeShift"
BRANCH = "codex/hnlo-one-click-20261017"
AUTHORITY = "configs/diagnostics/hnlo_one_click_authority.v1.json"
LOCK = "configs/diagnostics/hnlo_one_click_source.v1.json"
NOTEBOOK = "notebooks/SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb"
ORDER = ("internvl3", "qwen3")
MODELS = {
    "internvl3": {"id": "OpenGVLab/InternVL3-2B-hf",
                  "revision": "cb57a075cb75a2e6d1b668b128d48bb00ae321d2",
                  "python": "3.11.11", "cuda_visible_devices": "0", "cuda": "12.4"},
    "qwen3": {"id": "Qwen/Qwen3-VL-8B-Instruct",
              "revision": "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b",
              "python": "3.12.13", "cuda_visible_devices": "0,1", "cuda": "12.8"},
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def synthetic_png():
    """Fixed 448x448 gray RGB PNG, using stored DEFLATE (independent of zlib)."""
    import binascii
    import struct
    import zlib
    pixels = (b"\0" + bytes([128]) * (448 * 3)) * 448
    chunks = []
    for start in range(0, len(pixels), 65535):
        block = pixels[start:start + 65535]
        last = start + len(block) == len(pixels)
        chunks.append(bytes([int(last)]) + struct.pack("<HH", len(block), 65535 - len(block)) + block)
    compressed = b"\x78\x01" + b"".join(chunks) + struct.pack(">I", zlib.adler32(pixels) & 0xffffffff)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", binascii.crc32(kind + data) & 0xffffffff)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 448, 448, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", compressed) + chunk(b"IEND", b""))


def scope():
    from safeshift.protocol.classification_policy import PROMPT_SHA256
    return {
        "models": deepcopy(MODELS), "order": list(ORDER), "source_kind": "SYNTHETIC",
        "sample_id": "hnlo-gray-rgb-448-v1", "input_sha256": hashlib.sha256(synthetic_png()).hexdigest(),
        "prompt_sha256": PROMPT_SHA256, "batch_size": 1, "max_new_tokens": 32,
        "load_limit_per_model": 1, "generate_limit_per_model": 1,
        "precision": "FP16", "quantization": "NONE", "decoding": "GREEDY",
        "forced_prefix": False, "calibration": False, "retry": False,
        "dataset_access": False, "test_access": False, "labels_or_gt_access": False,
        "network_boundary": "LINUX_SECCOMP_INET_DENY_PLUS_PYTHON_GUARD",
        "hnlo_formula": "safeshift.ls1.evaluate.anomaly_log_odds(log_softmax(four_raw_logits))",
        "numerical_tolerance": {"absolute": 1e-6, "relative": 1e-6},
        "research_verified": False,
    }


def template():
    return {"schema": "hnlo-one-click-authority-v1", "base_sha": BASE_SHA,
            "scope": scope(), "grant": None}


def authorize(value, source):
    expected = template()
    if {k: v for k, v in value.items() if k != "grant"} != {k: v for k, v in expected.items() if k != "grant"}:
        raise PermissionError("AUTHORITY_SCOPE_CHANGED")
    grant = value.get("grant")
    if type(grant) is not dict:
        raise PermissionError("RESEARCH_LEAD_GRANT_REQUIRED")
    required = {"approved_by", "role", "decision_url", "approved_utc", "implementation_commit",
                "source_payload_sha256", "attempt_id", "provisioning_approved", "gpu_probe_approved",
                "technical_probe_exception_approved", "raw_provenance_criteria_approved",
                "numerical_tolerance_approved", "artifact_retention_approved", "independent_audit_url"}
    if set(grant) != required or grant.get("role") != "Research Lead":
        raise PermissionError("EXACT_LEAD_GRANT_REQUIRED")
    for flag in required - {"approved_by", "role", "decision_url", "approved_utc", "implementation_commit",
                            "source_payload_sha256", "attempt_id", "independent_audit_url"}:
        if grant[flag] is not True:
            raise PermissionError("LEAD_APPROVAL_REQUIRED:" + flag)
    if (grant["implementation_commit"] != source["implementation_commit"]
            or grant["source_payload_sha256"] != source["payload_sha256"]):
        raise PermissionError("AUTHORITY_SOURCE_BINDING_MISMATCH")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,35}", grant["attempt_id"]):
        raise PermissionError("UNIQUE_APPROVED_ATTEMPT_ID_REQUIRED")
    if not grant["approved_by"] or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", grant["approved_utc"]):
        raise PermissionError("LEAD_IDENTITY_AND_DATE_REQUIRED")
    for field in ("decision_url", "independent_audit_url"):
        if not re.fullmatch(r"https://github.com/tantdna2/SafeShift/(?:pull|issues)/\d+(?:#[-a-zA-Z0-9]+)?", grant[field]):
            raise PermissionError("DURABLE_REVIEW_REFERENCE_REQUIRED:" + field)
    return deepcopy(grant)
