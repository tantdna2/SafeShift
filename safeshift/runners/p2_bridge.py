"""D9R26 thin native lifecycle binding. No generation or semantic parser here."""

from copy import deepcopy
from dataclasses import dataclass, replace
from importlib import import_module
from pathlib import Path
from types import MappingProxyType

from safeshift.data.p2_execution import sha
from safeshift.protocol.classification_policy import ROOT, load_policy, render_prompt, same_json
from .contracts import Request, RunContext, Roles, Participation, Task

VERSION = "d9r26-production-runner-bridge-v1"
REGISTRY_VERSION = "d9r26-native-runner-registry-v1"
REGISTRY = MappingProxyType({
    "qwen3": ("safeshift.runners.qwen3_vl", "Qwen3VLRunner", "qwen3-vl-runner-v2"),
    "qwen2_5": ("safeshift.runners.qwen2_5_vl", "Qwen2_5VLRunner", "qwen2-5-vl-runner-v2"),
    "internvl3": ("safeshift.runners.internvl3", "InternVL3Runner", "internvl3-runner-v1"),
    "moondream": ("safeshift.runners.moondream2", "Moondream2Runner", "moondream2-offline-v1"),
})
MOONDREAM_CACHE = "data/processed/moondream_hf_cache"


def call_identity(sample_id):
    return "call1-" + sha(sample_id.encode("utf-8"))


@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    git_commit: str
    source_kind: str


@dataclass(frozen=True)
class CallIdentity:
    sample_id: str
    call_id: str
    image_sha256: str


def context_for(model, entry, run, call=None):
    if type(run) is not RunIdentity or run.source_kind not in ("INSPECSAFE", "SYNTHETIC"):
        raise ValueError("EXACT_OPERATIONAL_RUN_IDENTITY_REQUIRED")
    if not run.run_id or len(run.git_commit) != 40 or any(c not in "0123456789abcdef" for c in run.git_commit):
        raise ValueError("EXACT_OPERATIONAL_RUN_IDENTITY_REQUIRED")
    provenance = {}
    if call is not None:
        if type(call) is not CallIdentity or call.call_id != call_identity(call.sample_id):
            raise ValueError("EXACT_OPERATIONAL_CALL_IDENTITY_REQUIRED")
        provenance = {"sample_id": call.sample_id, "input_id": "sha256:" + call.image_sha256,
                      "image_sha256": call.image_sha256, "model_key": model}
    return RunContext(run.run_id, call.call_id if call else "lifecycle", **{
        name: deepcopy(entry[name]) for name in ("decoding", "preprocessing", "precision",
            "quantization", "device", "software_versions", "seed")},
        git_commit_sha=run.git_commit, command="python -m safeshift.runners.p2_owner run --model " + model,
        source_kind=run.source_kind, input_provenance=provenance,
        roles=Roles(Participation.PARTICIPATING, Participation.NOT_PARTICIPATING))


def require_production_context(model, context, repo=ROOT):
    """Native guard extension: actual INSPECSAFE stays INSPECSAFE, never relabelled."""
    from .p2_harness import authorize_production
    head, authority = authorize_production(repo)
    from . import internvl3_authority, p21_authority
    from .qwen3_authority import SCHEMA, authorized_run, verify_lineage
    if authority.get("schema_version") == p21_authority.SCHEMA:
        run = p21_authority.authorized_run(authority, model, context.run_id)
        p21_authority.verify_lineage(repo, authority, model, context.run_id, run["rerun_of"])
        p21_authority.verify_progression(repo, authority, model, context.run_id)
    elif authority.get("schema_version") == internvl3_authority.SCHEMA:
        internvl3_authority.authorized_run(authority, model, context.run_id)
    elif authority.get("schema_version") == SCHEMA:
        run = authorized_run(authority, model, context.run_id)
        verify_lineage(repo, authority, model, context.run_id, run["rerun_of"])
    entry = load_policy(repo, qwen3_runtime=model == "qwen3")["classification"][model]
    if (context.source_kind != "INSPECSAFE" or context.git_commit_sha != head
            or context.roles != Roles(Participation.PARTICIPATING, Participation.NOT_PARTICIPATING)):
        raise PermissionError("AUTHORIZED_CLASSIFICATION_CONTEXT_REQUIRED")
    for name in ("decoding", "preprocessing", "precision", "quantization", "device", "software_versions", "seed"):
        if not same_json(getattr(context, name), entry[name]):
            raise ValueError("EXACT_D9R23_CONTEXT_REQUIRED:" + name)


def _runner_class(model):
    module_name, name, version = REGISTRY[model]
    cls = getattr(import_module(module_name), name)
    if (cls.__module__, cls.__name__, cls.version) != (module_name, name, version):
        raise ValueError("NATIVE_RUNNER_CLASS_BINDING_MISMATCH")
    return cls


def _construct(model, repo, entry, observation):
    cls = _runner_class(model)
    if model in ("qwen3", "qwen2_5"):
        module = import_module(REGISTRY[model][0])
        # Native envelope records complete *observed* versions, not policy fiction.
        def native_backend():
            native = module._native_backend()
            for name, value in native.software_versions.items():
                if observation["software_versions"].get(name) != value:
                    raise ValueError("NATIVE_SOFTWARE_MISMATCH")
            return replace(native, software_versions=deepcopy(observation["software_versions"]))
        runner = cls(backend_factory=native_backend)
    elif model == "internvl3":
        runner = cls(repo=repo)
    else:
        from .moondream_snapshot import TOKENIZER_REVISION
        from .storage import FileRawStore
        cache = FileRawStore(Path(repo), MOONDREAM_CACHE).root
        runner = cls(cache / "models--vikhyatk--moondream2" / "snapshots" / entry["immutable_revision"],
                     cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION, repo=repo)
    if type(runner) is not cls:
        raise ValueError("NATIVE_RUNNER_CLASS_BINDING_MISMATCH")
    return runner


def _check_identity(runner, model, entry):
    if ((runner.identity.model_id, runner.identity.immutable_revision)
            != (entry["model_id"], entry["immutable_revision"])
            or runner.version != REGISTRY[model][2]):
        raise ValueError("NATIVE_MODEL_IDENTITY_MISMATCH")


def _verify_qwen_snapshot(model, repo):
    if model == "qwen3":
        from scripts import provision_qwen3vl_snapshot as s
        result = s.verify_weights(s.cached_snapshot(), s.weight_files(repo))
        if not result["LOCAL_WEIGHT_BYTES_VERIFIED"]:
            raise ValueError("QWEN3_SNAPSHOT_MISMATCH")
    elif model == "qwen2_5":
        from scripts import provision_qwen2_5_snapshot as s
        s.verify_snapshot(s.cached_snapshot(), repo=repo)


def _loaded_state(runner, model):
    if model == "qwen3":
        from .qwen3_placement import require_loaded_state
        native = runner._resources[1]
        require_loaded_state(native)
    elif model == "qwen2_5":
        from scripts.w2_qwen2_5_t4_smoke import placement_gate
        placement_gate(runner._resources[1], runner._resources[0], runner._backend.torch)
    elif model == "internvl3":
        runner.state_audit()
    else:
        runner._audit_state("d9r26_bridge_observe")


class ProductionRunnerBridge:
    version = VERSION

    def __init__(self, model, *, repo=ROOT):
        if model not in REGISTRY:
            raise ValueError("CLASSIFICATION_NOT_PARTICIPATING")
        self.model, self.repo = model, Path(repo)
        self.entry = deepcopy(load_policy(repo, qwen3_runtime=model == "qwen3")["classification"][model])
        # Class metadata is safe to import; heavyweight imports remain lazy.
        cls = _runner_class(model)
        _check_identity(cls, model, self.entry)
        self.runner = self.observation = self.run = None
        self.state, self.calls, self.network = "NEW", set(), None

    def load(self, condition, *, operational):
        if self.state != "NEW" or not same_json(condition, self.entry):
            raise ValueError("ONE_EXACT_BRIDGE_LIFECYCLE_REQUIRED")
        self.state = "ATTEMPTED"
        self.run = operational
        context = context_for(self.model, self.entry, operational)
        # No real native loads through a synthetic source, even if called directly.
        require_production_context(self.model, context, self.repo)
        from .p2_preflight import runtime_observation
        from .internvl3_snapshot import network_denied
        try:
            self.network = network_denied()
            self.network.__enter__()
            self.observation = runtime_observation(self.model, self.repo)
            self.runner = _construct(self.model, self.repo, self.entry, self.observation)
            _check_identity(self.runner, self.model, self.entry)
            _verify_qwen_snapshot(self.model, self.repo)
            self.runner.initialize(context)
            self.runner.load(context)
            _loaded_state(self.runner, self.model)
            self.state = "LOADED"
        except BaseException:
            self.close()
            raise

    def observe(self):
        if self.state != "LOADED":
            raise RuntimeError("LOAD_BEFORE_OBSERVE")
        return deepcopy(self.observation)

    def generate(self, *, image_bytes, prompt, operational):
        if self.state != "LOADED":
            raise RuntimeError("BRIDGE_TERMINAL_NO_RETRY")
        context = context_for(self.model, self.entry, self.run, operational)
        if (operational.call_id in self.calls or sha(image_bytes) != operational.image_sha256
                or prompt != render_prompt(self.model, repo=self.repo)):
            raise ValueError("EXACT_IMAGE_PROMPT_CALL_REQUIRED")
        self.calls.add(operational.call_id)
        request = Request(Task.CLASSIFICATION, operational.sample_id,
                          "sha256:" + operational.image_sha256, image_bytes,
                          self.entry["prompt_version"], prompt)
        try:
            _check_identity(self.runner, self.model, self.entry)
            prepared = self.runner.prepare_input(request, context)
            raw = self.runner.generate_raw(prepared, context)
            if type(raw) is not bytes:
                raise TypeError("NATIVE_RAW_BYTES_REQUIRED")
            return raw
        except BaseException:
            self.state = "FAILED"
            raise

    def close(self):
        try:
            if self.runner is not None and hasattr(self.runner, "close"):
                self.runner.close()
        finally:
            if self.network is not None:
                self.network.__exit__(None, None, None)
                self.network = None
            self.state = "CLOSED"
