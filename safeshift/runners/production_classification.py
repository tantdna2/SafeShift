"""D9R23: classification-only adapters over durable native envelopes, no model calls.

Selective PR #67 registry/native-validator reuse. No qualification promotion,
grounding path, generation, network or runner lifecycle is exposed here.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path

from safeshift.protocol.classification_policy import (
    MODELS, ROOT, PROMPT_VERSION, PROMPT_SHA256, render_prompt, same_json,
    load_policy, validate_context, OFFLINE_SOURCES,
)
from safeshift.protocol.schema import strict_json
from safeshift.qualification.classification import CandidateAdapter
from .contracts import AdaptedOutput, ParseStatus, RawReference, Task
from .storage import FileRawStore

PARSER_VERSION = "d9r23-native-strict-classification-v1"


@dataclass(frozen=True)
class StoredEnvelope:
    repo: Path
    reference: RawReference
    provenance: dict


def _read_verified(stored):
    if not isinstance(stored, StoredEnvelope):
        raise TypeError("PERSISTED_NATIVE_ENVELOPE_REQUIRED")
    reference = stored.reference
    # Validate lexical path as well as aliases; never read outside data/processed.
    raw_path = FileRawStore(stored.repo, reference.path).root
    raw = raw_path.read_bytes()
    if len(raw) != reference.size_bytes or hashlib.sha256(raw).hexdigest() != reference.sha256:
        raise ValueError("RAW_PERSISTENCE_INTEGRITY_FAILURE")
    metadata_path = raw_path.parent / "metadata.json"
    FileRawStore(stored.repo, metadata_path.relative_to(stored.repo).as_posix())
    metadata = strict_json(metadata_path.read_bytes())
    if not same_json(metadata, {**stored.provenance, "raw_output": asdict(reference)}):
        raise ValueError("RAW_PROVENANCE_INTEGRITY_FAILURE")
    return raw


def persist_response(model, raw, *, context, hardware, sample_id, input_sha256,
                     store=None, repo=ROOT):
    """Durably preserve raw + provenance, verify reread, then return a receipt.

    This accepts a previously obtained envelope, never generates or parses it.
    Any persistence error propagates and leaves no receipt available to parse.
    Partial attempts are not overwritten; no automatic retry.
    """
    repo = Path(repo).resolve()
    entry = validate_context(model, context, hardware, repo=repo)
    prompt = render_prompt(model, repo=repo)
    if type(raw) is not bytes:
        raise TypeError("RAW_BYTES_REQUIRED")
    for value in (sample_id, context.run_id, context.call_id, context.git_commit_sha, context.command):
        if type(value) is not str or not value.strip():
            raise ValueError("EXPLICIT_PROVENANCE_REQUIRED")
    if (type(input_sha256) is not str or len(input_sha256) != 64
            or any(c not in "0123456789abcdef" for c in input_sha256)):
        raise ValueError("INPUT_SHA256_REQUIRED")
    provenance = {**asdict(context), "model_key": model, "model_id": entry["model_id"],
                  "immutable_revision": entry["immutable_revision"], "sample_id": sample_id,
                  "input_sha256": input_sha256, "prompt": prompt, "prompt_version": PROMPT_VERSION,
                  "prompt_sha256": PROMPT_SHA256, "hardware_contract": deepcopy(hardware),
                  "adapter_version": entry["adapter_version"], "parser_version": PARSER_VERSION,
                  "task": "classification", "parse_status": "NOT_ATTEMPTED"}
    store = store if store is not None else FileRawStore(repo, "data/processed/production_classification_d9r23")
    if not isinstance(store, FileRawStore) or store.repo != repo:
        raise TypeError("REPOSITORY_FILE_RAW_STORE_REQUIRED")
    reference = store.preserve(raw, deepcopy(provenance))
    saved = StoredEnvelope(repo, reference, deepcopy(provenance))
    if _read_verified(saved) != raw:
        raise ValueError("RAW_PERSISTENCE_INTEGRITY_FAILURE")
    return saved


class ClassificationAdapter:
    parser_version = PARSER_VERSION

    def __init__(self, model):
        if model not in MODELS:
            raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
        self.model = model
        self.version = f"{model}-classification-adapter-d9r23-v1"

    def adapt(self, stored):
        raw = _read_verified(stored)  # persistence failure never enters native parser
        entry = load_policy(stored.repo)["classification"][self.model]
        meta = stored.provenance
        if (meta["model_key"] != self.model or meta["model_id"] != entry["model_id"]
                or meta["immutable_revision"] != entry["immutable_revision"]
                or meta["prompt_sha256"] != PROMPT_SHA256
                or meta["prompt_version"] != PROMPT_VERSION
                or meta["prompt"] != render_prompt(self.model, repo=stored.repo)
                or meta["adapter_version"] != self.version or meta["parser_version"] != PARSER_VERSION
                or meta["parse_status"] != "NOT_ATTEMPTED" or meta["task"] != "classification"):
            raise ValueError("STORED_CLASSIFICATION_IDENTITY_MISMATCH")
        if meta["source_kind"] not in OFFLINE_SOURCES:
            raise ValueError("NO_INSPECSAFE_INFERENCE")
        for key in ("decoding", "preprocessing", "precision", "quantization", "device",
                    "software_versions", "seed", "hardware_contract"):
            if not same_json(meta[key], entry[key]):
                raise ValueError("STORED_EXECUTION_CONDITION_MISMATCH:" + key)
        try:
            obj = strict_json(raw)
            if self.model in ("qwen3", "qwen2_5"):
                if not same_json(obj["generation_kwargs"], entry["decoding"]):
                    raise ValueError("NATIVE_DECODING_MISMATCH")
                if len(obj["continuation_ids"]) > entry["max_output_tokens"]:
                    raise ValueError("NATIVE_TOKEN_LIMIT")
                if not same_json(obj["runtime"]["software_versions"], entry["software_versions"]):
                    raise ValueError("NATIVE_SOFTWARE_MISMATCH")
            # Existing validators check exact envelope keys, identity, token
            # boundaries and strict single-field canonical JSON without repairs.
            output = CandidateAdapter(self.model, run_id=meta["run_id"],
                                      call_id=meta["call_id"]).adapt(raw, Task.CLASSIFICATION)
            output.validate(Task.CLASSIFICATION)
            return output
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, RecursionError):
            return AdaptedOutput(ParseStatus.INVALID)


def classification_adapter(model):
    return ClassificationAdapter(model)


def persist_and_adapt(model, raw, **kwargs):
    """Offline consumption boundary; storage must finish before adapter dispatch."""
    adapter = classification_adapter(model)
    stored = persist_response(model, raw, **kwargs)
    return stored, adapter.adapt(stored)
