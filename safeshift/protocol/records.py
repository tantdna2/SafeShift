"""Preserve raw bytes and per-call provenance before any provider parsing."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from . import PARSER_VERSION, PROTOCOL_VERSION, SCHEMA_VERSION
from .adapters import ProviderAdapter
from .firewall import external_path
from .prompts import Request
from .schema import ParseResult, parse_text


@dataclass(frozen=True)
class CallMetadata:
    run_id: str
    sample_id: str
    call_id: str
    requested_model_id: str
    resolved_model_version: str
    api_endpoint_url: str
    sdk_version: str
    decoding_parameters: dict
    git_commit_sha: str
    image_sha256: str
    environment: dict
    command: str
    seed: int | None
    source_kind: str = "handcrafted_dummy"
    protocol_freeze_commit_sha: str = "PENDING"


def preserve_and_parse(repo: Path, artifact_root: str, raw: bytes, adapter: ProviderAdapter,
                       request: Request, metadata: CallMetadata) -> ParseResult:
    """Only dummy responses are admitted by this pre-freeze development entrypoint.

    A fresh call directory is mandatory, so retries never overwrite previous calls.
    Disk/metadata failures propagate; parsing never proceeds without persistence.
    """
    external_path(repo, request.image_path)
    root = external_path(repo, artifact_root)
    processed = (repo.resolve() / "data/processed").resolve()
    if not root.is_relative_to(processed):
        raise ValueError("raw artifacts must be under data/processed/")
    if type(raw) is not bytes:
        raise TypeError("raw provider response must be unmodified bytes")
    if metadata.source_kind != "handcrafted_dummy" or metadata.protocol_freeze_commit_sha != "PENDING":
        raise ValueError("pre-freeze development accepts only handcrafted dummy responses")
    for name in (metadata.run_id, metadata.sample_id, metadata.call_id):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", name):
            raise ValueError("run/sample/call identifiers must be safe path components")
    for name in (metadata.requested_model_id, metadata.resolved_model_version,
                 metadata.api_endpoint_url, metadata.sdk_version, metadata.command):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("provenance fields must be explicit; use UNRESOLVED for dummy routes")
    for digest, length in ((metadata.git_commit_sha, 40), (metadata.image_sha256, 64)):
        if not re.fullmatch(r"[a-f0-9]{" + str(length) + "}", digest):
            raise ValueError("expected hexadecimal Git/image digest")
    directory = root / metadata.run_id / metadata.sample_id / metadata.call_id
    directory = external_path(repo, directory.relative_to(repo.resolve()))
    # Validate serializability before creating artifacts; no provider content is parsed here.
    record = {
        **asdict(metadata), "protocol_id": "P2", "protocol_version": PROTOCOL_VERSION,
        "schema_version": SCHEMA_VERSION, "parser_version": PARSER_VERSION,
        "adapter_version": adapter.version, "provider": adapter.provider,
        "coordinate_convention": adapter.convention, "task": request.task,
        "image_path": request.image_path, "prompt_template_id": request.prompt_version,
        "prompt": request.prompt, "prompt_sha256": request.prompt_sha256,
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "raw_response_id": (directory / "response.raw").relative_to(repo.resolve()).as_posix(),
    }
    serialized = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "response.raw").write_bytes(raw)
    (directory / "metadata.json").write_text(serialized, encoding="utf-8")
    try:
        text = adapter.extract_text(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        result = ParseResult("ENVELOPE_ERROR", errors=(str(exc),))
    else:
        result = parse_text(text, request.task, adapter.convention)
    result = replace(result, raw_artifact=record["raw_response_id"])
    (directory / "parsed.json").write_text(json.dumps(asdict(result), indent=2, allow_nan=False), encoding="utf-8")
    return result
