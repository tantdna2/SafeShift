"""One independent call, with persistence before adaptation and no role selection.

Implementations must not carry generated output/history between calls. Input and
prompt policy belong to the caller; this layer knows no dataset or model roster.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Protocol


class Task(str, Enum):
    CLASSIFICATION = "classification"
    GROUNDING = "grounding"


class Participation(str, Enum):
    PENDING = "PENDING"
    PARTICIPATING = "PARTICIPATING"
    NOT_PARTICIPATING = "NOT_PARTICIPATING"


@dataclass(frozen=True)
class Roles:
    """Caller-supplied policy, never inferred from a successful parse or failure."""

    classification: Participation = Participation.PENDING
    grounding: Participation = Participation.PENDING


class SpatialKind(str, Enum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NATIVE_BOX = "NATIVE_BOX"
    NATIVE_POINT = "NATIVE_POINT"
    NONE = "NO_SPATIAL_OUTPUT"
    MALFORMED = "MALFORMED_SPATIAL_OUTPUT"


class ParseStatus(str, Enum):
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    SUCCESS = "SUCCESS"
    INVALID = "INVALID"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class ErrorCode(str, Enum):
    MODEL_LOAD_FAILURE = "MODEL_LOAD_FAILURE"
    INITIALIZATION_FAILURE = "RUNNER_INITIALIZATION_FAILURE"
    PREPROCESSING_FAILURE = "PREPROCESSING_FAILURE"
    GENERATION_FAILURE = "GENERATION_RUNTIME_FAILURE"
    INVALID_CLASSIFICATION = "INVALID_CLASSIFICATION_OUTPUT"
    MALFORMED_GROUNDING = "MALFORMED_GROUNDING_OUTPUT"
    UNSUPPORTED_GROUNDING = "UNSUPPORTED_GROUNDING_INTERFACE"
    PARSER_FAILURE = "PARSER_FAILURE"
    RAW_PRESERVATION_FAILURE = "RAW_PRESERVATION_FAILURE"


@dataclass(frozen=True)
class Error:
    code: ErrorCode
    stage: str
    exception_type: str | None = None


@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    immutable_revision: str | None = None
    revision_evidence: str | None = None

    def __post_init__(self):
        if not self.model_id.strip():
            raise ValueError("model ID is required")
        if (self.immutable_revision is None) != (self.revision_evidence is None):
            raise ValueError("a frozen revision requires its provenance evidence")
        if self.immutable_revision is not None:
            if not self.immutable_revision.strip() or not self.revision_evidence.strip():
                raise ValueError("revision and evidence must be explicit")
            if self.immutable_revision.casefold() in {"pending", "main", "master", "latest"}:
                raise ValueError("a mutable alias is not an immutable revision")


@dataclass(frozen=True)
class Request:
    task: Task
    sample_id: str
    input_id: str
    input_bytes: bytes
    prompt_id: str
    prompt: str

    def __post_init__(self):
        if not isinstance(self.task, Task) or type(self.input_bytes) is not bytes:
            raise ValueError("request needs an explicit task and immutable input bytes")
        if any(not s.strip() for s in (self.sample_id, self.input_id, self.prompt_id, self.prompt)):
            raise ValueError("input, sample and prompt identifiers/text are required")


@dataclass(frozen=True)
class RunContext:
    run_id: str
    call_id: str
    decoding: dict
    preprocessing: dict
    precision: str
    quantization: str
    device: dict
    software_versions: dict
    git_commit_sha: str
    command: str
    source_kind: str
    seed: int | None = None
    input_provenance: dict = field(default_factory=dict)
    roles: Roles = field(default_factory=Roles)


@dataclass(frozen=True)
class AdaptedOutput:
    """Canonical value on success; native point evidence is never a box value.

    A task-specific adapter owns canonical validation. Evidence is diagnostic and
    must not be promoted to a successful canonical result or a metric input.
    """

    parse_status: ParseStatus
    value: Any = None
    spatial_kind: SpatialKind = SpatialKind.NOT_APPLICABLE
    native_evidence: Any = None

    def validate(self, task: Task):
        if not isinstance(self.parse_status, ParseStatus) or not isinstance(self.spatial_kind, SpatialKind):
            raise ValueError("adapter must return typed statuses")
        if self.parse_status not in {ParseStatus.SUCCESS, ParseStatus.INVALID, ParseStatus.UNSUPPORTED}:
            raise ValueError("adapter must return success, invalid or unsupported")
        if (self.parse_status == ParseStatus.SUCCESS) != (self.value is not None):
            raise ValueError("only success may carry a canonical value")
        if task == Task.CLASSIFICATION:
            if self.spatial_kind != SpatialKind.NOT_APPLICABLE or self.parse_status == ParseStatus.UNSUPPORTED:
                raise ValueError("classification adapter cannot report spatial status")
        else:
            allowed = {
                ParseStatus.SUCCESS: {SpatialKind.NATIVE_BOX},
                ParseStatus.INVALID: {SpatialKind.MALFORMED},
                ParseStatus.UNSUPPORTED: {SpatialKind.NATIVE_POINT, SpatialKind.NONE},
            }
            if self.spatial_kind not in allowed[self.parse_status]:
                raise ValueError("spatial kind contradicts canonical parse status")


class LocalRunner(ABC):
    identity: ModelIdentity
    version: str

    @abstractmethod
    def initialize(self, context: RunContext) -> None:
        """Initialize backend resources without loading a model."""

    @abstractmethod
    def load(self, context: RunContext) -> None:
        """Load the declared model; never select a replacement."""

    @abstractmethod
    def prepare_input(self, request: Request, context: RunContext) -> Any:
        """Prepare only this request, without any other call's output/history."""

    @abstractmethod
    def generate_raw(self, prepared: Any, context: RunContext) -> bytes:
        """Return losslessly serialized native output, before semantic parsing.

        Future runtimes must include native text/tokens/points they expose. If a
        runtime fails after emitting partial bytes, raise GenerationFailure with
        those bytes so the executor can preserve them without parsing.
        """


class GenerationFailure(RuntimeError):
    def __init__(self, partial_raw: bytes | None = None):
        super().__init__("generation failed")
        if partial_raw is not None and type(partial_raw) is not bytes:
            raise TypeError("partial raw output must be bytes")
        self.partial_raw = partial_raw


class OutputAdapter(Protocol):
    version: str
    parser_version: str

    def adapt(self, raw: bytes, task: Task) -> AdaptedOutput: ...


@dataclass(frozen=True)
class RawReference:
    path: str
    sha256: str
    size_bytes: int


class RawStore(Protocol):
    def preserve(self, raw: bytes, provenance: dict) -> RawReference:
        """Persist bytes AND provenance before returning; never overwrite."""
        ...


@dataclass(frozen=True)
class CallResult:
    task: Task
    participation: Participation
    parse_status: ParseStatus
    spatial_kind: SpatialKind
    canonical: Any
    native_evidence: Any
    raw_output: RawReference | None
    error: Error | None
    provenance: dict


def execute_call(runner: LocalRunner, adapter: OutputAdapter, store: RawStore,
                 request: Request, context: RunContext, *, clock=None) -> CallResult:
    """Execute one task. No scores, roster, fallback, gate or paired-call input.

    The returned provenance adds parse/error status to the pre-parse snapshot.
    Persistence errors fail closed. RawStore is a trusted persistence boundary.
    """
    context = deepcopy(context)
    recorded_at = (clock or (lambda: datetime.now(timezone.utc)))()
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        raise ValueError("timestamp must have a timezone")
    for value in (context.run_id, context.call_id, context.precision, context.quantization,
                  context.git_commit_sha, context.command, context.source_kind,
                  runner.version, adapter.version, adapter.parser_version):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provenance fields must be explicit")
    if not context.device or not context.software_versions:
        raise ValueError("device and software versions must be recorded")
    participation = getattr(context.roles, request.task.value)
    if not isinstance(participation, Participation):
        raise ValueError("participation must be explicit")
    provenance = {
        **asdict(context), **asdict(runner.identity),
        "revision_status": "PENDING" if runner.identity.immutable_revision is None else "RECORDED",
        "runner_version": runner.version, "adapter_version": adapter.version,
        "parser_version": adapter.parser_version, "task": request.task.value,
        "sample_id": request.sample_id, "input_id": request.input_id,
        "input_sha256": hashlib.sha256(request.input_bytes).hexdigest(),
        "prompt_id": request.prompt_id, "prompt": request.prompt,
        "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
        "timestamp": recorded_at.astimezone(timezone.utc).isoformat(),
        "parse_status": ParseStatus.NOT_ATTEMPTED, "error_status": None,
    }
    # Snapshot and validate metadata before any backend side effects.
    provenance = json.loads(json.dumps(provenance, allow_nan=False))
    raw_ref = None

    def finish(status=ParseStatus.NOT_ATTEMPTED, spatial=SpatialKind.NOT_APPLICABLE,
               value=None, evidence=None, error=None):
        record = {**provenance, "parse_status": status.value,
                  "error_status": asdict(error) if error else None,
                  "raw_output": asdict(raw_ref) if raw_ref else None}
        return CallResult(request.task, participation, status, spatial, value,
                          evidence, raw_ref, error, record)

    def preserve(raw):
        if type(raw) is not bytes:
            raise TypeError("runner must return unmodified bytes")
        return store.preserve(raw, deepcopy(provenance))

    # NOT_PARTICIPATING is an input policy, not a failed prediction.
    if participation == Participation.NOT_PARTICIPATING:
        return finish()
    stages = (
        ("initialize", ErrorCode.INITIALIZATION_FAILURE, lambda: runner.initialize(deepcopy(context))),
        ("load", ErrorCode.MODEL_LOAD_FAILURE, lambda: runner.load(deepcopy(context))),
        ("prepare_input", ErrorCode.PREPROCESSING_FAILURE,
         lambda: runner.prepare_input(request, deepcopy(context))),
    )
    prepared = None
    for stage, code, action in stages:
        try:
            prepared = action()
        except Exception as exc:
            return finish(error=Error(code, stage, type(exc).__name__))
    try:
        raw = runner.generate_raw(prepared, deepcopy(context))
        if type(raw) is not bytes:
            raise TypeError("generate_raw must return bytes")
    except Exception as exc:
        if isinstance(exc, GenerationFailure) and exc.partial_raw is not None:
            try:
                raw_ref = preserve(exc.partial_raw)
            except Exception as storage_exc:
                return finish(error=Error(ErrorCode.RAW_PRESERVATION_FAILURE, "preserve",
                                          type(storage_exc).__name__))
        return finish(error=Error(ErrorCode.GENERATION_FAILURE, "generate_raw", type(exc).__name__))
    try:
        raw_ref = preserve(raw)
    except Exception as exc:
        return finish(error=Error(ErrorCode.RAW_PRESERVATION_FAILURE, "preserve", type(exc).__name__))
    try:
        adapted = adapter.adapt(raw, request.task)
        adapted.validate(request.task)
        # Canonical records and evidence must be serializable run artifacts.
        json.dumps(asdict(adapted), allow_nan=False)
    except Exception as exc:
        return finish(ParseStatus.FAILED, error=Error(ErrorCode.PARSER_FAILURE, "adapt", type(exc).__name__))
    error = None
    if adapted.parse_status == ParseStatus.INVALID:
        code = (ErrorCode.INVALID_CLASSIFICATION if request.task == Task.CLASSIFICATION
                else ErrorCode.MALFORMED_GROUNDING)
        error = Error(code, "adapt")
    elif adapted.parse_status == ParseStatus.UNSUPPORTED:
        error = Error(ErrorCode.UNSUPPORTED_GROUNDING, "adapt")
    return finish(adapted.parse_status, adapted.spatial_kind, adapted.value,
                  adapted.native_evidence, error)
