"""Freeze-gated P2 orchestration; current release authorizes synthetic only.

Production bridges receive separate typed operational identities with load and
generate. Scripted rehearsal implements load(condition), observe(), and
generate(image_bytes=, prompt=).
They return the complete native serialized envelope (bytes or UTF-8 text), not
a guessed canonical class. No backend/model library is imported here.
"""

from copy import deepcopy
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import tempfile
import struct
import zlib

from safeshift.data.p2_execution import (
    execution_records, json_bytes, safe_path, sha, shard, verify_dataset,
)
from safeshift.protocol.classification_policy import (
    ROOT, MODELS, POLICY_PATH, PROMPT_PATH, PROMPT_SHA256, load_policy, render_prompt, same_json,
)
from safeshift.protocol.schema import strict_json
from safeshift.qualification.classification import CandidateAdapter
from .contracts import AdaptedOutput, GenerationFailure, ParseStatus, Task
from .production_classification import PARSER_VERSION
from .storage import FileRawStore
from .p2_bridge import (REGISTRY as _PRODUCTION_BACKENDS, REGISTRY_VERSION, VERSION as BRIDGE_VERSION,
                        ProductionRunnerBridge, RunIdentity, CallIdentity, call_identity)

CONTRACT_PATH = "configs/pre_freeze/d9r25_harness_contract.v1.json"
BLOCK = "NO_INSPECSAFE_INFERENCE_BEFORE_PROTOCOL_FREEZE"
ADAPTER = "d9r25-durable-d9r23-native-adapter-v1"
PRODUCTION_BACKEND_REGISTRY_VERSION = REGISTRY_VERSION
IMPLEMENTATION_BASE_SHA = "e7628d68f87cf53b5343ea912b7e332064c285af"


def resolve_production_backend(model_key, *, repo=ROOT):
    """Internal fixed binding, never a caller-selectable implementation.

    Construction imports lightweight native runner definitions only, no model.
    """
    if model_key not in _PRODUCTION_BACKENDS:
        raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
    return ProductionRunnerBridge(model_key, repo=repo)


def contract(repo=ROOT):
    value = strict_json((Path(repo) / CONTRACT_PATH).read_bytes())
    if value["schema_version"] != "d9r25-p2-harness-v1" or value["protocol_id"] != "P2":
        raise ValueError("P2_CONTRACT_REQUIRED")
    return value


def identities(repo=ROOT):
    expected = contract(repo)["identity_sha256"]
    for name, digest in expected.items():
        raw = (Path(repo) / name).read_bytes()
        # JSON policy identities pin repository LF bytes across Git CRLF checkouts.
        if name.endswith(".json"):
            raw = raw.replace(b"\r\n", b"\n")
        if sha(raw) != digest:
            raise ValueError("PINNED_CONTRACT_HASH_MISMATCH:" + name)
    load_policy(repo)
    return deepcopy(expected)


def registry(repo=ROOT):
    identities(repo)
    return deepcopy(load_policy(repo, qwen3_runtime=True)["classification"])


def _model(model, repo):
    models = registry(repo)
    if model not in models:
        raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
    return models[model]


def _git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL)


def authorize_production(repo=ROOT):
    """Authorize only the reviewed two-parent Standard Merge Commit.

    The authority file is deliberately insufficient on a one-parent Draft PR
    branch.  Effective authority exists only when Git proves that HEAD is the
    final reviewed merge, with the audited main commit as parent one and the
    F2 authority commit as parent two.
    """
    c = contract(repo)
    if (c["protocol_freeze"] != "FROZEN" or c["implementation_freeze"] != "FROZEN"
            or c["inspecsafe_inference_authorized"] is not True
            or c.get("implementation_base_sha") != IMPLEMENTATION_BASE_SHA
            or c.get("freeze_candidate_path") != "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json"
            or c.get("protocol_freeze_commit_sha_source") != c["freeze_manifest_path"]):
        raise PermissionError(BLOCK)
    path = c["freeze_manifest_path"]
    try:
        head = _git(repo, "rev-parse", "HEAD").decode().strip()
        parents = _git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if len(parents) != 3 or parents[0] != head:
            raise ValueError("FINAL_MERGE_REQUIRED")
        parent1, parent2 = parents[1:]
        expected_main = c["implementation_base_sha"]
        freeze = strict_json(_git(repo, "show", f"{head}:{path}"))
        commit = freeze["protocol_freeze_commit_sha"]
        if (freeze.get("schema_version") != "p2-execution-authority-v1"
                or not re.fullmatch(r"[0-9a-f]{40}", commit)
                or freeze.get("status") != "FROZEN"
                or freeze.get("authority") != "RESEARCH_LEAD"
                or freeze.get("protocol_id") != "P2"
                or freeze.get("inspecsafe_inference_authorized") is not True
                or freeze.get("implementation_base_sha") != expected_main
                or freeze.get("expected_pre_merge_main_sha") != expected_main
                or freeze.get("freeze_candidate_path") != c["freeze_candidate_path"]
                or freeze.get("freeze_candidate_sha256") != c["freeze_candidate_sha256"]
                or freeze.get("reruns") != []):
            raise ValueError("FREEZE_AUTHORITY_REQUIRED")
        if parent1 != expected_main:
            raise ValueError("FINAL_MERGE_PARENT_1_REQUIRED")
        if _git(repo, "show", f"{parent2}:{path}") != _git(repo, "show", f"{head}:{path}"):
            raise ValueError("FINAL_MERGE_AUTHORITY_PARENT_REQUIRED")
        parent2_parents = _git(repo, "rev-list", "--parents", "-n", "1", parent2).decode().split()
        if parent2_parents != [parent2, commit]:
            raise ValueError("FINAL_MERGE_PARENT_2_MUST_BE_DIRECT_F2_CHILD_OF_FREEZE")
        _git(repo, "merge-base", "--is-ancestor", commit, parent2)
        _git(repo, "merge-base", "--is-ancestor", commit, head)
        if _git(repo, "rev-parse", f"{commit}^").decode().strip() != expected_main:
            raise ValueError("FREEZE_COMMIT_PARENT_REQUIRED")
        changed = _git(repo, "diff", "--name-only", commit, head).decode().splitlines()
        if changed != [path]:
            raise ValueError("EXECUTABLE_CHANGED_AFTER_FREEZE")
        if (_git(repo, "rev-parse", f"{head}^{{tree}}")
                != _git(repo, "rev-parse", f"{parent2}^{{tree}}")):
            raise ValueError("FINAL_MERGE_TREE_MISMATCH")
        # Avoid a self-referencing SHA: freeze commit pins release artifacts;
        # a later authority commit records that freeze commit's identity.
        if _git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise ValueError("DIRTY_EXECUTION_COMMIT")
        hashes = identities(repo)
        if freeze.get("identity_sha256") != hashes:
            raise ValueError("FREEZE_HASH_MISMATCH")
        for name, digest in hashes.items():
            if sha(_git(repo, "show", f"{commit}:{name}")) != digest:
                raise ValueError("FREEZE_COMMIT_ARTIFACT_MISMATCH")
        candidate_bytes = _git(repo, "show", f"{commit}:{c['freeze_candidate_path']}")
        if sha(candidate_bytes) != c["freeze_candidate_sha256"]:
            raise ValueError("FREEZE_CANDIDATE_HASH_MISMATCH")
        if (freeze["dataset_fingerprint"] != c["dataset_fingerprint"]
                or freeze["sample_count"] != c["sample_count"]
                or freeze["dataset_fingerprint"] != "7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5"
                or freeze["sample_count"] != 5013):
            raise ValueError("FREEZE_DATASET_MISMATCH")
        return head, freeze
    except (KeyError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise PermissionError(f"{BLOCK}:{exc}") from exc


def production_run(*, model, run_id, dataset_root, manifest_path, provenance_path,
                   shard_count=1, shard_index=0, repo=ROOT,
                   rerun_of=None):
    """Guard precedes dataset reads, factory construction and backend load."""
    entry = _model(model, repo)
    commit, authority = authorize_production(repo)
    rows, manifest_hash = verify_dataset(dataset_root, manifest_path, provenance_path)
    def image(row):
        raw = safe_path(dataset_root, row["image_locator"]).read_bytes()
        if sha(raw) != row["image_sha256"]:
            raise ValueError("IMAGE_CHANGED_AFTER_PREFLIGHT")
        return raw
    return _execute(repo=repo, model=model, entry=entry, run_id=run_id, rows=rows,
                    source_hash=manifest_hash, dataset_fingerprint=contract(repo)["dataset_fingerprint"],
                    source="INSPECSAFE", image_reader=image,
                    shard_count=shard_count, shard_index=shard_index, commit=commit,
                    rerun_of=rerun_of, rerun_authorizations=authority.get("reruns", []))


def atomic_new(path, content):
    """Publish complete bytes exclusively via a same-directory hard link.

    No rename-overwrite race: link fails if destination already exists. A
    filesystem without hard-link support fails closed. Local trusted directory
    ownership is required (not a defense against hostile concurrent link swaps).
    """
    path = Path(path)
    fd, temp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def verified_raw(directory, receipt):
    raw = (Path(directory) / "response.raw").read_bytes()
    if len(raw) != receipt["size_bytes"] or sha(raw) != receipt["sha256"]:
        raise ValueError("RAW_PERSISTENCE_INTEGRITY_FAILURE")
    return raw


def persist_native(directory, native):
    if type(native) is str:
        raw = native.encode("utf-8")
        encoding = "UTF8_TEXT"
    elif type(native) is bytes:
        raw, encoding = native, "NATIVE_BYTES"
    else:
        raise TypeError("LOSSLESS_NATIVE_SERIALIZATION_REQUIRED")
    receipt = {"sha256": sha(raw), "size_bytes": len(raw), "encoding": encoding}
    atomic_new(Path(directory) / "response.raw", raw)
    if verified_raw(directory, receipt) != raw:
        raise ValueError("RAW_PERSISTENCE_INTEGRITY_FAILURE")
    return receipt


def parse_stored(directory, receipt, model, entry, run_id, call_id):
    """D9R23 strict native parsing rules over a verified durable receipt.

    Unlike the historical offline adapter, authorization is owned by the run
    entrypoint. No offline source is relabelled as production or vice versa.
    """
    raw = verified_raw(directory, receipt)
    try:
        obj = strict_json(raw)
        if model in ("qwen3", "qwen2_5"):
            if (not same_json(obj["generation_kwargs"], entry["decoding"])
                    or len(obj["continuation_ids"]) > entry["max_output_tokens"]
                    or not same_json(obj["runtime"]["software_versions"], entry["software_versions"])):
                raise ValueError("NATIVE_CONDITION_MISMATCH")
        parsed = CandidateAdapter(model, run_id=run_id, call_id=call_id).adapt(raw, Task.CLASSIFICATION)
        parsed.validate(Task.CLASSIFICATION)
        return parsed
    except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, RecursionError):
        return AdaptedOutput(ParseStatus.INVALID)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _run_path(repo, model, run_id):
    if type(run_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id):
        raise ValueError("SAFE_RUN_ID_REQUIRED")
    return FileRawStore(Path(repo), f"data/processed/benchmark/p2/{model}/{run_id}").root


def _rerun(repo, model, run_id, reference, authorizations):
    if reference is None:
        return
    if set(reference) != {"run_id", "run_manifest_sha256"} or reference["run_id"] == run_id:
        raise ValueError("RERUN_REQUIRES_NEW_ID_AND_EXACT_REFERENCE")
    previous = _run_path(repo, model, reference["run_id"]) / "run_manifest.json"
    if sha(previous.read_bytes()) != reference["run_manifest_sha256"]:
        raise ValueError("RERUN_REFERENCE_MISMATCH")
    if {"run_id": run_id, "model_key": model, "rerun_of": reference,
            "authority": "RESEARCH_LEAD"} not in authorizations:
        raise PermissionError("RERUN_RESEARCH_LEAD_AUTHORIZATION_REQUIRED")


def _execute(*, repo, model, entry, run_id, rows, source_hash, dataset_fingerprint,
             source, image_reader, shard_count, shard_index, commit, backend_factory=None,
             rerun_of=None, rerun_authorizations=(), artifact_repo=None):
    selected, shard_meta = shard(rows, shard_count, shard_index, source_hash)
    storage_repo = repo if artifact_repo is None else artifact_repo
    _rerun(storage_repo, model, run_id, rerun_of, rerun_authorizations)
    root = _run_path(storage_repo, model, run_id)
    if root.exists():
        raise FileExistsError("EXISTING_RUN_RESUME_FORBIDDEN")
    # A new name must not silently conceal a repeat scientific attempt.
    if root.parent.exists():
        for previous in sorted(root.parent.iterdir()):
            prior_manifest = safe_path(root.parent, previous.name + "/run_manifest.json")
            prior = strict_json(prior_manifest.read_bytes())
            if prior["protocol_identity"]["source_kind"] != source:
                continue
            overlapping = any(safe_path(previous, "calls/" + sha(row["sample_id"].encode()) + "/attempt.json").exists()
                              for row in selected)
            if overlapping and (rerun_of is None or rerun_of["run_id"] != prior["run_id"]):
                raise PermissionError("PREVIOUS_ATTEMPT_REQUIRES_EXPLICIT_AUTHORIZED_RERUN")
    # Resolution follows auth/dataset/shard/attempt checks and precedes all load.
    # Only this private executor retains test injection; production exposes none.
    bound_backend = resolve_production_backend(model, repo=repo) if backend_factory is None else None
    root.mkdir(parents=True, exist_ok=False)  # includes failed/interrupted runs: no resume
    hashes = identities(repo)
    identity = {"protocol_id": "P2", "identity_sha256": hashes,
                "dataset_fingerprint": dataset_fingerprint, "source_manifest_sha256": source_hash,
                "source_kind": source}
    manifest = {"version": "d9r26-run-v1", "run_id": run_id, "model_key": model,
                "call_identity_version": "call1-sample-sha256-v1",
                "bridge_version": BRIDGE_VERSION, "backend_registry_version": REGISTRY_VERSION,
                "native_runner_binding": list(_PRODUCTION_BACKENDS[model]),
                "protocol_identity": identity, "model_condition": entry,
                "git_commit": commit, "rerun_of": rerun_of, "started_at": _now(),
                "resume": "FORBIDDEN", "shard_manifest_sha256": shard_meta["shard_manifest_sha256"]}
    atomic_new(root / "run_manifest.json", json_bytes(manifest))
    atomic_new(root / "shard_manifest.json", json_bytes(shard_meta))
    atomic_new(root / "execution_manifest.json", json_bytes(list(selected)))
    (root / "calls").mkdir()
    statuses = {r["sample_id"]: "NOT_ATTEMPTED" for r in selected}
    state, failure = "COMPLETED", None
    try:
        backend = bound_backend if backend_factory is None else backend_factory()
        if isinstance(backend, ProductionRunnerBridge):
            backend.load(deepcopy(entry), operational=RunIdentity(run_id, commit, source))
        else:
            backend.load(deepcopy(entry))  # private executor/scripted tests only
        observation = backend.observe()
        # Exact allowed fields prevent accidentally persisting tokens/env dumps.
        if (set(observation) != {"software_versions", "hardware"}
                or not same_json(observation["software_versions"], entry["software_versions"])
                or not same_json(observation["hardware"], entry["hardware_contract"])):
            raise ValueError("OBSERVED_EXECUTION_CONDITION_MISMATCH")
        atomic_new(root / "environment.json", json_bytes({**observation,
                   "observation_kind": "SIMULATED" if source == "SYNTHETIC" else "BACKEND_OBSERVED"}))
        prompt = render_prompt(model, repo=repo)
        for row in selected:
            sid = row["sample_id"]
            call_id = call_identity(sid)
            directory = root / "calls" / sha(sid.encode())
            directory.mkdir(exist_ok=False)
            started = _now()
            statuses[sid] = "ATTEMPTED"
            atomic_new(directory / "attempt.json", json_bytes({"sample_id": sid, "call_id": call_id,
                       "started_at": started}))
            stage, cause, receipt, parsed = "IMAGE_READ", None, None, None
            try:
                image_bytes = image_reader(row)
                if type(image_bytes) is not bytes or sha(image_bytes) != row["image_sha256"]:
                    raise ValueError("IMAGE_HASH_MISMATCH")
                stage = "GENERATION"
                if isinstance(backend, ProductionRunnerBridge):
                    native = backend.generate(image_bytes=image_bytes, prompt=prompt,
                                              operational=CallIdentity(sid, call_id, row["image_sha256"]))
                else:
                    native = backend.generate(image_bytes=image_bytes, prompt=prompt)
                stage = "RAW_PERSISTENCE"
                receipt = persist_native(directory, native)
                stage = "PARSER"
                parsed = parse_stored(directory, receipt, model, entry, run_id, call_id)
                stage = "COMPLETED"
            except GenerationFailure as exc:
                cause = "GENERATION_FAILURE"
                if exc.partial_raw is not None:
                    stage = "RAW_PERSISTENCE"
                    receipt = persist_native(directory, exc.partial_raw)
                stage = "GENERATION"
            except (Exception, KeyboardInterrupt) as exc:
                # Never persist arbitrary exception messages (may contain secrets).
                cause = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "STAGE_FAILURE"
            status = parsed.parse_status.value if parsed else "FAILED"
            metadata = {"run_id": run_id, "sample_id": sid, "call_id": call_id,
                        "protocol_id": "P2", "model_key": model, "git_commit": commit,
                        "bridge_version": BRIDGE_VERSION, "native_runner_binding": list(_PRODUCTION_BACKENDS[model]),
                        "source_kind": source,
                        "hardware_observation_kind": "SIMULATED" if source == "SYNTHETIC" else "BACKEND_OBSERVED",
                        "model_id": entry["model_id"], "immutable_revision": entry["immutable_revision"],
                        "prompt_version": entry["prompt_version"], "prompt_sha256": PROMPT_SHA256,
                        "production_policy_identity": hashes[POLICY_PATH],
                        "image_sha256": row["image_sha256"], "adapter_version": ADAPTER,
                        "d9r23_adapter_version": entry["adapter_version"], "parser_version": PARSER_VERSION,
                        "decoding": entry["decoding"], "preprocessing_id": entry["preprocessing_id"],
                        "preprocessing": entry["preprocessing"], "precision": entry["precision"],
                        "quantization": entry["quantization"], "software_versions": observation["software_versions"],
                        "hardware_observation": observation["hardware"],
                        "shard_identity": shard_meta["shard_manifest_sha256"],
                        "started_at": started, "ended_at": _now(), "termination_stage": stage,
                        "failure_cause": cause, "raw_response": receipt, "parse_status": status}
            atomic_new(directory / "metadata.json", json_bytes(metadata))
            export = {"sample_id": sid, "model_key": model, "run_id": run_id, "call_id": call_id,
                      "parse_status": status, "safety_level": parsed.value.safety_level if parsed and parsed.value else None,
                      "raw_artifact": f"calls/{directory.name}/response.raw" if receipt else None,
                      "raw_sha256": receipt["sha256"] if receipt else None,
                      "raw_size_bytes": receipt["size_bytes"] if receipt else None,
                      "adapter_version": ADAPTER, "parser_version": PARSER_VERSION}
            atomic_new(directory / "parsed.json", json_bytes(export))
            statuses[sid] = status
            if cause:
                state = "INTERRUPTED" if cause == "INTERRUPTED" else "FAILED"
                failure = {"stage": stage, "cause": cause}
                break
    except (Exception, KeyboardInterrupt) as exc:
        state = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "FAILED"
        failure = {"stage": "RUN_OR_PERSISTENCE", "cause": "STAGE_FAILURE"}
    finally:
        if "backend" in locals() and isinstance(backend, ProductionRunnerBridge):
            try:
                backend.close()
            except Exception:
                state, failure = "FAILED", {"stage": "CLOSE", "cause": "STAGE_FAILURE"}
    # Final immutable index binds exports to this completed shard's exact bytes.
    artifacts = {p.relative_to(root).as_posix(): sha(p.read_bytes())
                 for p in sorted(root.rglob("*.json"))}
    summary = {"status": state, "ended_at": _now(), "samples": statuses, "failure": failure,
               "artifact_sha256": artifacts}
    atomic_new(root / "run_status.json", json_bytes(summary))
    return root


class ScriptedBackend:
    """No arbitrary callback, network, model or dataset access. Rehearsal only."""
    def __init__(self, responses):
        self.responses = tuple(responses)
        if any(type(x) not in (bytes, str, GenerationFailure) for x in self.responses):
            raise TypeError("SCRIPTED_BYTES_TEXT_OR_GENERATION_FAILURE_ONLY")
        self.calls = 0

    def load(self, condition):
        self.condition = condition

    def observe(self):
        return {"software_versions": deepcopy(self.condition["software_versions"]),
                "hardware": deepcopy(self.condition["hardware_contract"])}

    def generate(self, *, image_bytes, prompt):
        value = self.responses[self.calls]
        self.calls += 1
        if type(value) is GenerationFailure:
            raise value
        return value


def synthetic_image():
    """Generate one 1x1 RGB PNG; no owner input/image path accepted."""
    def chunk(kind, payload):
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff")) + chunk(b"IEND", b""))


def rehearse(*, model, run_id, sample_ids, backend, repo=ROOT, artifact_repo=None,
             shard_count=1, shard_index=0, rerun_of=None):
    """repo is the Git source/config root; artifact_repo is storage only.

    Neither argument supplies input images. A temporary output directory must
    not be passed as the Git source. No fallback to this module's ROOT or cwd.
    """
    if type(backend) is not ScriptedBackend:
        raise TypeError("BUILTIN_SCRIPTED_BACKEND_REQUIRED")
    entry = _model(model, repo)
    source_root = Path(repo).resolve()
    if Path(_git(source_root, "rev-parse", "--show-toplevel").decode().strip()).resolve() != source_root:
        raise ValueError("EXPLICIT_GIT_SOURCE_ROOT_REQUIRED")
    commit = _git(source_root, "rev-parse", "HEAD").decode().strip()
    image = synthetic_image()
    rows = execution_records({"sample_id": sid, "image_locator": "generated.png", "image_sha256": sha(image)}
                             for sid in sample_ids)
    return _execute(repo=repo, model=model, entry=entry, run_id=run_id, rows=rows,
                    source_hash=sha(json_bytes(rows)), dataset_fingerprint="SYNTHETIC_NOT_INSPECSAFE",
                    source="SYNTHETIC", image_reader=lambda row: image,
                    backend_factory=lambda: backend, shard_count=shard_count, shard_index=shard_index,
                    commit=commit, rerun_of=rerun_of, artifact_repo=artifact_repo)
