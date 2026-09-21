"""Handcrafted byte fixtures, not a model implementation or capability gate.

The dummy adapter is the explicit bridge to the unchanged protocol schema. The
generic executor does not know safety labels, hazard vocabulary or dataset paths.
"""

from enum import Enum
import math

from safeshift.protocol import PARSER_VERSION
from safeshift.protocol.schema import parse_text, strict_json

from .contracts import (
    AdaptedOutput, GenerationFailure, LocalRunner, ModelIdentity, ParseStatus,
    Request, RunContext, SpatialKind, Task,
)


class DummyCase(str, Enum):
    BOX = "valid_classification_and_box"
    POINT = "valid_classification_and_point"
    NONE = "valid_classification_without_grounding"
    MALFORMED = "valid_classification_and_malformed_grounding"
    INVALID_CLASSIFICATION = "invalid_classification"
    GENERATION_FAILURE = "generation_failure"
    PARSER_FAILURE = "parser_failure"


class DummyRunner(LocalRunner):
    identity = ModelIdentity("synthetic/dummy")
    version = "dummy-runner-v1"

    def __init__(self, case: DummyCase = DummyCase.BOX, *, fail_task: Task = Task.GROUNDING):
        self.case = DummyCase(case)
        self.fail_task = Task(fail_task)
        self.events = []

    def initialize(self, context: RunContext):
        self.events.append("initialize")

    def load(self, context: RunContext):
        self.events.append("load")

    def prepare_input(self, request: Request, context: RunContext) -> Request:
        self.events.append(("prepare_input", request))
        return request

    def generate_raw(self, prepared: Request, context: RunContext) -> bytes:
        self.events.append(("generate_raw", prepared.task))
        if prepared.task == self.fail_task:
            if self.case == DummyCase.GENERATION_FAILURE:
                raise GenerationFailure()
            if self.case == DummyCase.PARSER_FAILURE:
                return b"DUMMY_PARSER_EXCEPTION"
        if prepared.task == Task.CLASSIFICATION:
            return (b'{"safety_level":"unknown"}' if self.case == DummyCase.INVALID_CLASSIFICATION
                    else b'{"safety_level":"Level04"}')
        if self.case == DummyCase.POINT:
            return b'{"native_points":[[0.25,0.75]],"coordinate_system":"xy_1"}'
        if self.case == DummyCase.NONE:
            return b'{"spatial_output":null}'
        if self.case == DummyCase.MALFORMED:
            return b'{"hazards":[{"hazard_type":"SMOKE","evidence":[{"bbox":[0.8,0.2,0.1,0.9]}]}]}'
        return b'{"hazards":[{"hazard_type":"SMOKE","evidence":[{"bbox":[0.1,0.2,0.3,0.4]}]}]}'


class DummyAdapter:
    version = "dummy-adapter-v1"
    parser_version = "dummy-envelope-v1/" + PARSER_VERSION

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput:
        if raw == b"DUMMY_PARSER_EXCEPTION":
            raise RuntimeError("synthetic parser exception")
        if task == Task.GROUNDING:
            try:
                obj = strict_json(raw)
                if isinstance(obj, dict) and "native_points" in obj:
                    if set(obj) != {"native_points", "coordinate_system"} or obj["coordinate_system"] != "xy_1":
                        raise ValueError("invalid dummy point envelope")
                    points = obj["native_points"]
                    if not isinstance(points, list) or not points:
                        raise ValueError("invalid dummy points")
                    for point in points:
                        if (not isinstance(point, list) or len(point) != 2
                                or any(type(v) not in (int, float) or not math.isfinite(v)
                                       or not 0 <= v <= 1 for v in point)):
                            raise ValueError("invalid dummy point")
                    return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NATIVE_POINT,
                                         native_evidence=obj)
                if obj == {"spatial_output": None}:
                    return AdaptedOutput(ParseStatus.UNSUPPORTED, spatial_kind=SpatialKind.NONE)
            except (ValueError, UnicodeError, RecursionError):
                return AdaptedOutput(ParseStatus.INVALID, spatial_kind=SpatialKind.MALFORMED)
        parsed = parse_text(raw, task.value)
        if task == Task.CLASSIFICATION:
            return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID,
                                 parsed.value)
        return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID,
                             parsed.value, SpatialKind.NATIVE_BOX if parsed.success else SpatialKind.MALFORMED)
