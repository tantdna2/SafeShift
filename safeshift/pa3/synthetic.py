"""Small, deterministic, in-memory mock objects and traces; no input loaders."""

import hashlib
import math

from .policy import require_case

EOS = 127
LABEL_IDS = (49, 50, 51, 52)  # ASCII mock only, never Qwen token IDs.


class MockTokenizer:
    def __init__(self, *, double=False):
        if type(double) is not bool:
            raise ValueError("BOOLEAN_MOCK_VARIANT_REQUIRED")
        self.double = double

    def encode(self, text, add_special_tokens=False):
        return [ord(c) for c in text for _ in range(2 if self.double else 1)]

    def decode(self, ids, **kwargs):
        return "".join(chr(i) for i in ids[::2 if self.double else 1])


def specimen(settings, name):
    require_case(settings, name)
    # This 2x2 RGB object is not an encoded image or a dataset-derived fixture.
    pixels = bytes((17, 83, 149)) * 4
    return {"sample_id": "pa3-synthetic-" + name, "case": name,
            "source": "BUILTIN_SYNTHETIC", "image_kind": "MOCK_RGB_2x2",
            "image_pixel_sha256": hashlib.sha256(pixels).hexdigest()}


def ground_truth(settings):
    """Arbitrary test labels, with no claim about safety semantics of the pixels."""
    from .policy import authorize
    settings = authorize(settings)
    return {specimen(settings, name)["sample_id"]:
            ("Level04" if name in ("normal", "constant_normal", "reversed_normal", "invalid")
             else "Level02" if name == "level02" else "Level03" if name == "level03" else "Level01")
            for name in settings["cases"]}


def summarize(vector, generated):
    """Compact LS1-compatible summary of a tiny mock full vocabulary."""
    finite = [v for v in vector if math.isfinite(v)]
    maximum = max(finite) if finite else 0.0
    counts = {"nan": sum(math.isnan(v) for v in vector),
              "positive_inf": vector.count(math.inf), "negative_inf": vector.count(-math.inf)}
    best = max(range(len(vector)), key=vector.__getitem__)
    lse = (math.nan if counts["nan"] else math.inf if counts["positive_inf"] else
           maximum + math.log(math.fsum(math.exp(v - maximum) for v in finite)))
    return {"argmax_id": best, "argmax_value": vector[best],
            "generated_value": vector[generated], "logsumexp": lse,
            "nonfinite": counts, "candidate_values": {str(i): vector[i] for i in LABEL_IDS}}


def generate(settings, name):
    """Only a catalog name can select a mock trace. No callable/backend injection."""
    require_case(settings, name)
    raw = {"specimen": specimen(settings, name), "error": None, "trace": None}
    if name in ("runtime_error", "interrupt"):
        raw["error"] = "SYNTHETIC_" + name.upper()
        return raw
    text = '{"safety_level":"Level03"}'
    if name == "invalid":
        text += " commentary"
    if name == "fenced":
        text = "```json\n" + text + "\n```"
    if name == "escaped":
        text = '{"safety_level":"Level0\\u0033"}'
    tok = MockTokenizer(double=name == "multi_token")
    ids = tok.encode(text) + [EOS]
    if name == "alignment":
        ids[0] = ord(" ")
    logits = [0.0, 1.0, 4.0, 0.0]
    if name in ("normal", "reversed_anomaly"):
        logits = [0.0, 1.0, 4.0, 8.0]
    if name in ("constant_anomaly", "constant_normal"):
        logits = [0.0] * 4
    if name == "offset_constant":
        logits = [1e300] * 4
    if name == "overflow":
        logits = [1.7e308, 1.7e308, 1.7e308, -1.7e308]
    steps = []
    # Fixture construction does not parse or score the response.
    branch = text.index("3") * (2 if tok.double else 1)
    for i, token in enumerate(ids):
        rv = [-100.0] * 128
        pv = [-100.0] * 128
        rv[token] = pv[token] = 20.0
        if i == branch:
            for label_id, z, p in zip(LABEL_IDS, logits, (0.0, 1.0, 5.0, 0.0)):
                rv[label_id], pv[label_id] = z, p
        if i == 0:
            fault = {"raw_nan": math.nan, "raw_inf": math.inf, "raw_negative_inf": -math.inf}
            if name in fault:
                rv[0] = fault[name]
            if name in ("processed_nan", "processed_inf", "processed_mask"):
                pv[0] = {"processed_nan": math.nan, "processed_inf": math.inf,
                         "processed_mask": -math.inf}[name]
        row = {"step": i, "generated_token": token,
               "raw": summarize(rv, token), "processed": summarize(pv, token),
               "mock_raw_vector": rv, "mock_processed_vector": pv}
        steps.append(row)
    if name == "wrong_generated":
        steps[0]["generated_token"] += 1
    if name == "missing_step":
        steps.pop()
    if name == "missing_candidate":
        del steps[branch]["raw"]["candidate_values"]["52"]
    raw["trace"] = {"decoded_text": text, "continuation_ids": ids, "steps": steps,
                    "eos_token_ids": [EOS], "mock_double_tokens": tok.double}
    return raw
