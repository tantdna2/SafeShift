"""Thin registry over existing pinned runners; no provisioning or fallback."""

from importlib import import_module
import importlib.metadata
import os
import platform
import subprocess

from safeshift.runners.contracts import RunContext
from safeshift.runners.storage import FileRawStore, _write_new
from safeshift.runners.paligemma_snapshot import OFFLINE_ENV, network_denied
from .classification import (ROOT, PLAN, MANIFEST, MODELS, SOURCE_KIND, CandidateAdapter,
                             digest, json_bytes, load_suite, prompt_for, run_suite, strict_json)


def condition(model, repo=ROOT):
    plan = strict_json((repo / PLAN).read_bytes())
    entry = plan["models"][model]
    if (entry["model_id"], entry["revision"]) != MODELS[model]:
        raise ValueError("PLAN_MODEL_IDENTITY_CHANGED")
    if model == "qwen3":
        from scripts.w2_qwen_kaggle_smoke import load_plan
        runtime = load_plan(repo)
        versions = strict_json((repo / "configs/pre_freeze/qwen_kaggle_smoke_result.v1.json").read_bytes())["software_versions"]
        return runtime["decoding"], runtime["preprocessing"], runtime["device"], versions
    module = import_module("safeshift.runners." + {
        "qwen2_5": "qwen2_5_vl", "internvl3": "internvl3", "moondream": "moondream2",
        "paligemma": "paligemma"}[model])
    if model == "qwen2_5":
        from scripts.provision_qwen2_5_snapshot import load_plan
        runtime = load_plan(repo)
        decoding = runtime["smoke"]["decoding"]
    else:
        runtime = module.load_plan()
        decoding = module.DECODING
    return decoding, module.PREPROCESSING, {"placement": "cuda:0"}, runtime["software"]


def native_runner(model, repo, cache_dir, torch):
    """Read-only cache verification. Never download a missing snapshot."""
    if model == "qwen3":
        if cache_dir is not None:
            raise ValueError("QWEN_CACHE_USES_PRESET_HF_HUB_CACHE_ONLY")
        from scripts import provision_qwen3vl_snapshot as snapshot
        from scripts import w2_qwen_kaggle_smoke as smoke
        from safeshift.runners.qwen3_vl import Qwen3VLRunner
        hardware = smoke.probe_hardware(torch)
        smoke.require_t4_pair(hardware)
        if torch.version.cuda != "12.8":
            raise ValueError("VALIDATED_QWEN3_CUDA_REQUIRED")
        verification = snapshot.verify_weights(snapshot.cached_snapshot(), snapshot.weight_files(repo))
        if not verification["LOCAL_WEIGHT_BYTES_VERIFIED"]:
            raise ValueError("QWEN3_SNAPSHOT_MISMATCH")
        return Qwen3VLRunner(), {"snapshot": verification, "hardware": hardware}
    if model == "qwen2_5":
        if cache_dir is not None:
            raise ValueError("QWEN_CACHE_USES_PRESET_HF_HUB_CACHE_ONLY")
        from scripts import provision_qwen2_5_snapshot as snapshot
        from scripts.w2_qwen2_5_t4_smoke import probe_hardware
        from safeshift.runners.qwen2_5_vl import Qwen2_5VLRunner
        hardware = probe_hardware(torch)
        if torch.version.cuda != "12.4":
            raise ValueError("CUDA_BUILD_MISMATCH")
        verification = snapshot.verify_snapshot(snapshot.cached_snapshot(), repo=repo)
        return Qwen2_5VLRunner(), {"snapshot": verification, "hardware": hardware}
    if model == "moondream":
        from safeshift.runners.moondream2 import Moondream2Runner
        from safeshift.runners.moondream_snapshot import TOKENIZER_REVISION
        if cache_dir is None:
            raise ValueError("EXPLICIT_MOONDREAM_CACHE_REQUIRED")
        cache = FileRawStore(repo, cache_dir).root
        return Moondream2Runner(
            cache / "models--vikhyatk--moondream2" / "snapshots" / MODELS[model][1],
            cache / "models--moondream--starmie-v1" / "snapshots" / TOKENIZER_REVISION), None
    module = import_module("safeshift.runners." + model)
    runner_type = module.InternVL3Runner if model == "internvl3" else module.PaliGemmaRunner
    kwargs = {"repo": repo}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    return runner_type(**kwargs), None


class QualificationLifecycle:
    """One initialize/load dispatch, preserving runner's per-call checks and state."""
    def __init__(self, runner, model):
        self.runner, self.model = runner, model
        self.identity, self.version = runner.identity, runner.version
        self.initialized = self.loaded = False
        self.model_loads = self.classification_calls = 0

    def initialize(self, context):
        if not self.initialized:
            self.runner.initialize(context)
            self.initialized = True

    def load(self, context):
        if not self.loaded:
            self.runner.load(context)
            self.model_loads += 1
            if self.model == "qwen3":
                from scripts.w2_qwen_kaggle_smoke import inspect_device_map
                model = self.runner._resources[1]
                inspect_device_map(model.hf_device_map)
                if getattr(model.config, "_attn_implementation", None) == "flash_attention_2":
                    raise ValueError("FLASH_ATTENTION_2_FORBIDDEN")
            elif self.model == "qwen2_5":
                from scripts.w2_qwen2_5_t4_smoke import placement_gate
                processor, model, _ = self.runner._resources
                placement_gate(model, processor, self.runner._backend.torch)
            self.loaded = True

    def prepare_input(self, request, context):
        if request.task.value != "classification":
            raise ValueError("ZERO_GROUNDING_CALLS")
        return self.runner.prepare_input(request, context)

    def generate_raw(self, prepared, context):
        self.classification_calls += 1
        return self.runner.generate_raw(prepared, context)

    def close(self):
        if hasattr(self.runner, "close"):
            self.runner.close()


def execute(model, *, expected_commit, research_lead_authorization, venue_internet_off,
            run_id, cache_dir=None, repo=ROOT, command):
    """Future owner entry point. Explicit authorization is recorded, never inferred."""
    if not venue_internet_off or not research_lead_authorization.strip():
        raise ValueError("SEPARATE_RESEARCH_LEAD_AUTHORIZATION_AND_OFFLINE_ATTESTATION_REQUIRED")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    if commit != expected_commit or subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=repo, text=True).strip():
        raise ValueError("EXACT_APPROVED_COMMIT_AND_CLEAN_CHECKOUT_REQUIRED")
    load_suite(repo)
    decoding, preprocessing, device, versions = condition(model, repo)
    root = FileRawStore(repo, f"data/processed/classification_qualification_v1/{model}").root
    root.mkdir(parents=True, exist_ok=False)  # Fixed ledger, regardless of run ID.
    provenance = {"model": model, "run_id": run_id, "git_commit": commit,
                  "research_lead_authorization": research_lead_authorization,
                  "venue_internet_off": venue_internet_off, "command": command,
                  "plan_sha256": digest((repo / PLAN).read_bytes()),
                  "manifest_sha256": digest((repo / MANIFEST).read_bytes()),
                  "prompt": prompt_for(model), "prompt_sha256": digest(prompt_for(model).encode()),
                  "parser_version": CandidateAdapter.parser_version,
                  "decoding": decoding, "preprocessing": preprocessing,
                  "precision": "FP16", "quantization": "NONE", "seed": None,
                  "software_versions": versions, "device": device}
    _write_new(root / "attempt.json", json_bytes(provenance))
    runner = report = None
    try:
        if any(os.environ.get(k) != v for k, v in OFFLINE_ENV.items()):
            raise ValueError("SET_OFFLINE_ENV_BEFORE_PROCESS_START")
        if platform.system() != "Linux" or platform.machine() != "x86_64":
            raise ValueError("LINUX_X86_64_REQUIRED")
        actual = {}
        for name in versions:
            if name == "python":
                actual[name] = platform.python_version()
            elif name == "zlib":
                import zlib
                actual[name] = zlib.ZLIB_RUNTIME_VERSION
            else:
                actual[name] = importlib.metadata.version(name)
        if actual != versions:
            raise ValueError("EXACT_EXISTING_SOFTWARE_PINS_REQUIRED")
        with network_denied():
            import torch
            runner, snapshot = native_runner(model, repo, cache_dir, torch)
            lifecycle = QualificationLifecycle(runner, model)
            context = RunContext(run_id, "cq_01", decoding, preprocessing, "FP16", "NONE",
                                 device, actual, commit, command, SOURCE_KIND)
            report = run_suite(lifecycle, context, model=model, repo=repo,
                               artifact_root=root.relative_to(repo).as_posix() + "/calls")
            evidence = {"model_loads": lifecycle.model_loads,
                        "classification_calls": lifecycle.classification_calls,
                        "snapshot": snapshot or getattr(runner, "snapshot", None),
                        "hardware": ((snapshot or {}).get("hardware") or getattr(runner, "hardware", None)
                                     or getattr(runner, "evidence", {}).get("gpu")),
                        "runner_evidence": getattr(runner, "evidence", None),
                        "state_audits": getattr(runner, "audits", None)}
            _write_new(root / "runtime_evidence.json", json_bytes(evidence))
            if report["run_status"] == "PASS" and (evidence["model_loads"], evidence["classification_calls"]) != (1, 8):
                raise ValueError("ONE_LOAD_EIGHT_CALLS_REQUIRED")
    except Exception as exc:
        if report is not None:
            report["run_status"] = "FAIL" if report["run_status"] == "FAIL" else "INCONCLUSIVE"
            report["causes"] = sorted(set(report["causes"] + ["INFRASTRUCTURE_OR_RUNTIME_FAILURE"]))
            report["evidence_failure_type"] = type(exc).__name__
        else:
            report = {"run_status": "INCONCLUSIVE", "causes": ["INFRASTRUCTURE_OR_RUNTIME_FAILURE"],
                  "exception_type": type(exc).__name__, "model_role_after_run": "PENDING_RESEARCH_LEAD_REVIEW",
                  "roster_membership_changed": False, "production_adapter_promoted": False,
                  "automatic_rerun": False, "grounding_calls": 0}
    _write_new(root / "result.json", json_bytes(report))
    return report
