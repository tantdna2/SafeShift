"""Shared P2.1 formatting over unchanged, strictly validated native envelopes.

No runner, model, dataset, generation or storage lifecycle is exposed here.
The caller must verify its durable raw receipt before dispatching this adapter.
"""

from safeshift.protocol.classification_policy import MODELS
from safeshift.protocol.p21_schema import PARSER_VERSION, parse_classification
from safeshift.protocol.schema import fields, strict_json
from safeshift.qualification.classification import _hf_text
from .contracts import AdaptedOutput, ParseStatus, Task


def _moondream_text(obj):
    # Identical strict lossless query-envelope shape to historical CandidateAdapter.
    fields(obj, {"schema_version", "native"})
    if obj["schema_version"] != "moondream-native-lossless-v1":
        raise ValueError("NATIVE_ENVELOPE_VERSION")
    node = obj["native"]
    if (type(node) is not list or len(node) != 2 or node[0] != "dict"
            or type(node[1]) is not list or len(node[1]) != 1):
        raise ValueError("EXACT_QUERY_ANSWER_REQUIRED")
    pair = node[1][0]
    if (type(pair) is not list or len(pair) != 2 or pair[0] != ["str", "answer"]
            or type(pair[1]) is not list or len(pair[1]) != 2
            or pair[1][0] != "str" or type(pair[1][1]) is not str):
        raise ValueError("EXACT_QUERY_ANSWER_STRING_REQUIRED")
    return pair[1][1]


class P21NativeAdapter:
    """Every participating model uses the same amended canonical parser.

    This supplies a format implementation, never execution authorization.
    Native Qwen validators still enforce the original envelope, token, runtime
    and identity rules. Their historical format verdict does not determine a
    P2.1 verdict; the unchanged native bytes are parsed separately under P2.1.
    """

    version = "p21-durable-native-classification-adapter-v1"
    parser_version = PARSER_VERSION

    def __init__(self, model, *, run_id=None, call_id=None):
        if model not in MODELS:
            raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
        self.model, self.run_id, self.call_id = model, run_id, call_id

    def adapt(self, raw, task):
        if task != Task.CLASSIFICATION:
            raise ValueError("ZERO_GROUNDING_CALLS")
        evidence = {"parser_version": PARSER_VERSION, "format_wrapper_detected": False}
        try:
            if type(raw) is not bytes:
                raise ValueError("RAW_BYTES_REQUIRED")
            obj = strict_json(raw)
            if self.model in ("qwen3", "qwen2_5"):
                from .qwen3_vl import Qwen3VLAdapter
                from .qwen2_5_vl import Qwen2_5VLAdapter
                validator = Qwen3VLAdapter() if self.model == "qwen3" else Qwen2_5VLAdapter()
                validator.adapt(raw, task).validate(task)
                text = obj["decoded_for_parser"]
            elif self.model == "internvl3":
                for key, expected in (("run_id", self.run_id), ("call_id", self.call_id)):
                    if expected is not None and obj.get(key) != expected:
                        raise ValueError("NATIVE_CALL_IDENTITY_MISMATCH")
                text = _hf_text(obj, self.model)
            else:
                text = _moondream_text(obj)
            parsed = parse_classification(text)
            evidence["format_wrapper_detected"] = parsed.format_wrapper_detected
            return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID,
                                 parsed.value, native_evidence=evidence)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, RecursionError):
            return AdaptedOutput(ParseStatus.INVALID, native_evidence=evidence)
