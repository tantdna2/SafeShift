"""D9R19 classification adapters; no model execution or qualification promotion.

The exact D9R16 native validators are reused without changing historical code.
Only InternVL3/Moondream are exposed here; PaliGemma is deliberately absent.
Use contracts.execute_call to persist native bytes before calling an adapter.
"""

from safeshift.protocol import PARSER_VERSION
from safeshift.qualification.classification import CandidateAdapter
from .contracts import AdaptedOutput, ParseStatus, SpatialKind, Task


class InternVL3Adapter:
    version = "internvl3-classification-d9r19-v1"
    parser_version = "internvl3-native-output-v1/" + PARSER_VERSION

    def __init__(self, *, run_id=None, call_id=None):
        self._native = CandidateAdapter("internvl3", run_id=run_id, call_id=call_id)

    def adapt(self, raw, task):
        if task == Task.GROUNDING:
            return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE)
        return self._native.adapt(raw, task)


class MoondreamClassificationAdapter:
    version = "moondream-classification-d9r19-v1"
    parser_version = "moondream-native-lossless-v1/" + PARSER_VERSION

    def adapt(self, raw, task):
        if task == Task.GROUNDING:
            return AdaptedOutput(
                ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE,
                native_evidence={"blocker": "MOONDREAM_CALL2_ORCHESTRATION_BLOCKER"})
        return CandidateAdapter("moondream").adapt(raw, task)


def classification_adapter(model, *, run_id=None, call_id=None):
    """Closed production participant registry. Does not activate runners."""
    if model == "qwen3":
        from .qwen3_vl import Qwen3VLAdapter
        return Qwen3VLAdapter()
    if model == "qwen2_5":
        from .qwen2_5_vl import Qwen2_5VLAdapter
        return Qwen2_5VLAdapter()
    if model == "internvl3":
        return InternVL3Adapter(run_id=run_id, call_id=call_id)
    if model == "moondream":
        return MoondreamClassificationAdapter()
    raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
