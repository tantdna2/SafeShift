"""Offline-only tests for the Ovis GPU smoke PREP harness.

Every CUDA/model observation here is synthetic.  The suite blocks real network
entry points and injects the Ovis runner's fake backend; it is not runtime evidence.
"""

from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

from scripts import provision_ovis2_5_snapshot as provision
from scripts import w2_ovis_gpu_smoke as smoke
from safeshift.runners.contracts import ErrorCode, ParseStatus
from safeshift.runners.ovis2_5 import Ovis2_5Runner, OvisBackend
from tests.test_ovis_runner import FakeModel, InferenceMode, Tensor


PINNED_SOFTWARE = {
    "python": "3.11.9",
    "torch": "2.4.0",
    "torch_distribution": "2.4.0",
    "torch_cuda_runtime": "12.1",
    "transformers": "4.51.3",
    "numpy": "1.25.0",
    "pillow": "10.3.0",
    "flash_attn": "2.7.0.post2",
    "moviepy": "1.0.3",
    "huggingface_hub": "0.36.0",
}
BACKEND_SOFTWARE = {
    "torch": "2.4.0",
    "transformers": "4.51.3",
    "pillow": "10.3.0",
    "huggingface_hub": "0.36.0",
}


def hardware(*, available=True, names=("NVIDIA A100-SXM4-40GB",),
             memory=40 * 1024**3, capability=(8, 0), bf16=True, current=0):
    return {
        "cuda_available": available,
        "visible_gpu_count": len(names) if available else 0,
        "current_device": current if available and names else None,
        "bf16_supported": bf16,
        "gpus": [
            {
                "index": index,
                "name": name,
                "total_memory_bytes": memory,
                "compute_capability": list(capability),
            }
            for index, name in enumerate(names)
        ] if available else [],
        "nvidia_smi_inventory": [],
        "driver_versions": ["550.54"],
    }


def verification_ok():
    return {
        "schema_version": "ovis-local-snapshot-contract-verification-v1",
        "snapshot": {
            "SNAPSHOT_PATH_VERIFIED": True,
            "expected_cache_suffix": provision.SNAPSHOT_IDENTITY,
            "download_filter_policy": "NO_FILTERS",
            "verification_scope": "PINNED_REQUIRED_ASSETS",
        },
        "weights": {"LOCAL_WEIGHT_BYTES_VERIFIED": True, "files": []},
        "critical_files": {
            "CRITICAL_PROVENANCE_HASHES_VERIFIED": True,
            "REQUIRED_LOCAL_ASSETS_PRESENT": True,
            "files": [],
        },
        "LOCAL_SNAPSHOT_VERIFIED": True,
    }


class FakeDType:
    def __init__(self, name, floating=True):
        self.name = name
        self.is_floating_point = floating

    def __str__(self):
        return self.name


class CensusTensor:
    def __init__(self, device="cuda:0", dtype="torch.bfloat16", *, numel=8, floating=True):
        self.device = device
        self.dtype = FakeDType(dtype, floating)
        self._numel = numel
        self._floating = floating

    def numel(self):
        return self._numel

    def element_size(self):
        return 2 if "16" in str(self.dtype) else 4

    def is_floating_point(self):
        return self._floating


class CensusModel(FakeModel):
    def __init__(self, *, parameter_device="cuda:0", parameter_dtype="torch.bfloat16",
                 include_meta=False, failure_on_call=None, network_attempt=False,
                 text='{"safety_level":"Level02"}'):
        super().__init__()
        self.text = text
        self.failure_on_call = failure_on_call
        self.network_attempt = network_attempt
        self._parameters = [CensusTensor(parameter_device, parameter_dtype)]
        if include_meta:
            self._parameters.append(CensusTensor("meta", parameter_dtype))
        self._buffers = [CensusTensor("cuda:0", "torch.int64", floating=False)]
        self.config = None

    def parameters(self):
        return iter(self._parameters)

    def buffers(self):
        return iter(self._buffers)

    def generate(self, **kwargs):
        self.generate_calls.append(kwargs)
        call_number = len(self.generate_calls)
        if self.network_attempt:
            socket.create_connection(("example.invalid", 443))
        if self.failure_on_call == call_number:
            error = RuntimeError("synthetic native failure")
            if getattr(self, "oom", False):
                error = OutOfMemoryError("synthetic OOM")
            raise error
        return Tensor(self.output)


class OutOfMemoryError(RuntimeError):
    pass


class CensusFactory:
    def __init__(self, **model_options):
        self.calls = []
        self.models = []
        self.model_options = model_options

    def from_pretrained(self, local_path, **kwargs):
        self.calls.append((local_path, kwargs))
        model = CensusModel(**self.model_options)
        model.config = SimpleNamespace(
            name_or_path=local_path,
            _attn_implementation="flash_attention_2",
        )
        model.llm.config = SimpleNamespace(_attn_implementation="flash_attention_2")
        self.models.append(model)
        return model


class FakeCuda:
    def __init__(self):
        self.reset_calls = []

    def reset_peak_memory_stats(self, index):
        self.reset_calls.append(index)

    def mem_get_info(self, index):
        return (30 * 1024**3, 40 * 1024**3)

    def memory_allocated(self, index):
        return 100

    def memory_reserved(self, index):
        return 200

    def max_memory_allocated(self, index):
        return 300

    def max_memory_reserved(self, index):
        return 400


class SmokeHarnessTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for target in (
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.socket.sendto",
            "socket.create_connection",
            "socket.getaddrinfo",
        ):
            self.stack.enter_context(
                patch(target, side_effect=AssertionError("network forbidden in unit tests"))
            )
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.repo = Path(self.temp)
        for relative in (smoke.PLAN, provision.PROVENANCE, "scripts/w2_ovis_gpu_smoke.py"):
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(smoke.ROOT / relative, target)
        self.snapshot = (
            self.repo / "cache" / provision.SNAPSHOT_REPOSITORY_DIR
            / "snapshots" / provision.REVISION
        )
        self.snapshot.mkdir(parents=True)
        self.cuda = FakeCuda()
        self.fake_torch = SimpleNamespace(
            __version__="2.4.0",
            version=SimpleNamespace(cuda="12.1"),
            cuda=self.cuda,
        )
        self.run_counter = 0

    def make_runner(self, **model_options):
        factory = CensusFactory(**model_options)
        resolver = Mock(return_value=str(self.snapshot.resolve()))
        backend_torch = SimpleNamespace(
            bfloat16="torch.bfloat16", inference_mode=InferenceMode,
        )
        runner = Ovis2_5Runner(
            backend_factory=lambda: OvisBackend(
                backend_torch, factory, dict(BACKEND_SOFTWARE), resolver,
            )
        )
        self.factory = factory
        self.resolver = resolver
        self.runner = runner
        self.runner_factory_calls = 0

        def runner_factory():
            self.runner_factory_calls += 1
            return runner

        return runner_factory

    def run_fake(self, run_id=None, *, runner_options=None, environment=True,
                 hardware_result=None, snapshot_verification=None, rerun=True):
        self.run_counter += 1
        run_id = run_id or f"offline-{self.run_counter}"
        runner_factory = self.make_runner(**(runner_options or {}))
        env = {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        } if environment else {
            "HF_HUB_OFFLINE": "0",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        }
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, env, clear=False))
            stack.enter_context(patch.object(
                smoke.subprocess, "check_output", return_value="a" * 40
            ))
            stack.enter_context(patch.object(
                smoke, "software_versions", return_value=dict(PINNED_SOFTWARE)
            ))
            stack.enter_context(patch.object(
                smoke, "probe_hardware", return_value=hardware_result or hardware()
            ))
            stack.enter_context(patch.object(
                smoke, "cached_snapshot", return_value=self.snapshot
            ))
            stack.enter_context(patch.object(
                smoke, "verify_snapshot",
                return_value=snapshot_verification or verification_ok(),
            ))
            kwargs = {}
            if rerun:
                kwargs = {"rerun_of": "approved-previous", "rerun_reason": "unit test"}
            return smoke.run_smoke(
                run_id,
                repo=self.repo,
                runner_factory=runner_factory,
                torch_module=self.fake_torch,
                **kwargs,
            )

    # PLAN coverage: exact identity, condition, thinking, decoding, prompt and freeze.
    def test_plan_exact_identity_and_smoke_only_condition(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["model_id"], "AIDC-AI/Ovis2.5-9B")
        self.assertEqual(plan["resolved_repository_id"], "ATH-MaaS/Ovis2.5-9B")
        self.assertEqual(plan["revision"], provision.REVISION)
        self.assertEqual((plan["precision"], plan["quantization"]), ("BF16", "NONE"))
        self.assertEqual(plan["device"], {"placement": "cuda:0"})
        self.assertEqual(plan["thinking"], {
            "enable_thinking": False, "enable_thinking_budget": False,
        })
        self.assertEqual(plan["decoding"], {"do_sample": False, "max_new_tokens": 32})
        self.assertNotIn("temperature", plan["decoding"])
        self.assertEqual(plan["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(plan["task"], "classification")

    def test_prompt_hash_and_explicit_runner_decoding(self):
        plan = smoke.load_plan()
        self.assertEqual(
            plan["prompt_sha256"], hashlib.sha256(plan["prompt"].encode()).hexdigest()
        )
        self.assertEqual(smoke.generation_decoding(plan), {
            "do_sample": False,
            "max_new_tokens": 32,
            "enable_thinking": False,
            "enable_thinking_budget": False,
        })

    def test_plan_mutation_or_extra_input_is_rejected(self):
        for key, value in (
            ("model_id", "other"),
            ("precision", "FP16"),
            ("prompt", "tuned"),
            ("input_path", "arbitrary.png"),
            ("protocol_freeze_commit_sha", "a" * 40),
        ):
            changed = smoke.expected_plan()
            changed[key] = value
            (self.repo / smoke.PLAN).write_text(json.dumps(changed), encoding="utf-8")
            with self.subTest(key=key), self.assertRaises(ValueError):
                smoke.load_plan(self.repo)

    def test_two_cases_are_deterministic_distinct_and_memory_only(self):
        first = smoke.generate_cases(self.repo)
        second = smoke.generate_cases(self.repo)
        self.assertEqual(first, second)
        self.assertEqual([row[1]["case_id"] for row in first], smoke.CASE_IDS)
        self.assertEqual(len({row[1]["image_sha256"] for row in first}), 2)
        self.assertFalse(any(self.repo.glob("RUNTIME_SMOKE_*.png")))

    # PROVISION coverage: exact resolved repo/revision, offline switch and byte rules.
    def test_snapshot_download_uses_resolved_repo_exact_revision_and_mode(self):
        download = Mock(return_value=str(self.snapshot.resolve()))
        module = SimpleNamespace(snapshot_download=download)
        with patch.dict(sys.modules, huggingface_hub=module):
            provision.cached_snapshot(self.repo / "cache", offline=False)
            self.assertEqual(download.call_args.kwargs["repo_id"], provision.RESOLVED_REPOSITORY_ID)
            self.assertEqual(download.call_args.kwargs["revision"], provision.REVISION)
            self.assertFalse(download.call_args.kwargs["local_files_only"])
            provision.cached_snapshot(self.repo / "cache", offline=True)
            self.assertTrue(download.call_args.kwargs["local_files_only"])
        self.assertNotEqual(provision.MODEL_ID, provision.RESOLVED_REPOSITORY_ID)

    def test_exact_four_weight_hashes_and_sizes_match_provenance(self):
        rows = provision.weight_files()
        self.assertEqual(rows, [dict(row) for row in provision.EXPECTED_WEIGHT_FILES])
        self.assertEqual(len(rows), 4)
        self.assertEqual(sum(row["size_bytes"] for row in rows), 18_349_727_512)

    def test_local_weight_hash_success_wrong_hash_and_missing(self):
        descriptions = []
        for index in range(4):
            raw = f"tiny synthetic shard {index}".encode()
            name = f"fixture-{index}.safetensors"
            (self.snapshot / name).write_bytes(raw)
            descriptions.append({
                "path": name,
                "size_bytes": len(raw),
                "lfs_sha256": hashlib.sha256(raw).hexdigest(),
            })
        self.assertTrue(
            provision.verify_weights(self.snapshot, descriptions)["LOCAL_WEIGHT_BYTES_VERIFIED"]
        )
        (self.snapshot / descriptions[0]["path"]).write_bytes(b"wrong")
        self.assertFalse(
            provision.verify_weights(self.snapshot, descriptions)["LOCAL_WEIGHT_BYTES_VERIFIED"]
        )
        (self.snapshot / descriptions[0]["path"]).unlink()
        self.assertFalse(
            provision.verify_weights(self.snapshot, descriptions)["LOCAL_WEIGHT_BYTES_VERIFIED"]
        )

    def test_critical_hashes_and_unpinned_assets_have_distinct_semantics(self):
        critical = []
        for index in range(5):
            raw = f"critical {index}".encode()
            name = f"critical-{index}.json"
            (self.snapshot / name).write_bytes(raw)
            critical.append({"path": name, "evidence": f"e{index}",
                             "sha256": hashlib.sha256(raw).hexdigest()})
        for name in provision.REQUIRED_LOCAL_ASSETS:
            (self.snapshot / name).write_bytes(("asset " + name).encode())
        report = provision.verify_critical_files(
            self.snapshot, critical, provision.REQUIRED_LOCAL_ASSETS
        )
        self.assertTrue(report["CRITICAL_PROVENANCE_HASHES_VERIFIED"])
        self.assertTrue(report["REQUIRED_LOCAL_ASSETS_PRESENT"])
        pinned = report["files"][:5]
        unpinned = report["files"][5:]
        self.assertTrue(all(row["verification_status"] == "VERIFIED_AGAINST_PROVENANCE"
                            and row["verified"] for row in pinned))
        self.assertTrue(all(row["verification_status"] == "RECORDED_LOCAL_HASH_ONLY"
                            and not row["verified"] and row["expected_sha256"] is None
                            for row in unpinned))
        (self.snapshot / provision.REQUIRED_LOCAL_ASSETS[0]).unlink()
        self.assertFalse(provision.verify_critical_files(
            self.snapshot, critical, provision.REQUIRED_LOCAL_ASSETS
        )["REQUIRED_LOCAL_ASSETS_PRESENT"])

    def test_wrong_snapshot_identity_fails_and_reports_are_aggregate(self):
        wrong = self.repo / "arbitrary" / provision.REVISION
        wrong.mkdir(parents=True)
        with self.assertRaises(ValueError):
            provision.validate_snapshot_path(wrong.resolve())
        verification = verification_ok()
        report_dir = self.repo / "reports"
        operation = {"mode": "VERIFY_ONLY_LOCAL", "local_files_only": True,
                     "network_firewall_enabled": True, "network_violation_count": 0}
        provision.write_verification_reports(report_dir, verification, operation)
        saved = json.loads((report_dir / "snapshot_verification.json").read_text())
        self.assertTrue(saved["LOCAL_SNAPSHOT_VERIFIED"])
        self.assertEqual(saved["operation"], operation)
        self.assertEqual(saved["component_verdicts"], {
            "snapshot_path": True,
            "weight_bytes": True,
            "critical_provenance_hashes": True,
            "required_local_assets": True,
        })

    def test_cache_report_paths_must_be_disjoint_and_verify_firewall_counts(self):
        cache = self.repo / "cache-root"
        self.assertTrue(provision._paths_overlap(cache, cache / "reports"))
        self.assertTrue(provision._paths_overlap(cache / "reports", cache))
        self.assertFalse(provision._paths_overlap(cache, self.repo / "reports"))
        firewall = provision.VerifyOnlyFirewall()
        with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
            firewall.deny()
        self.assertEqual(firewall.violation_count, 1)

    # PREFLIGHT coverage.
    def test_no_cuda_multiple_gpu_non_a100_low_vram_and_no_bf16_fail(self):
        invalid = [
            hardware(available=False, names=()),
            hardware(names=("NVIDIA A100", "NVIDIA A100")),
            hardware(names=("Tesla T4",)),
            hardware(memory=39_000_000_000),
            hardware(bf16=False),
            hardware(capability=(7, 5)),
        ]
        for item in invalid:
            with self.subTest(item=item), self.assertRaises(ValueError):
                smoke.require_single_a100(item)
        self.assertTrue(smoke.require_single_a100(hardware()))

    def test_software_pins_and_resolver_selected_hub_version(self):
        self.assertTrue(smoke.validate_software_versions(PINNED_SOFTWARE))
        for key in ("torch_distribution", "transformers", "numpy", "pillow",
                    "flash_attn", "moviepy"):
            changed = {**PINNED_SOFTWARE, key: "0.0.0"}
            with self.subTest(key=key), self.assertRaises(ValueError):
                smoke.validate_software_versions(changed)
        changed = {**PINNED_SOFTWARE, "huggingface_hub": ""}
        with self.assertRaises(ValueError):
            smoke.validate_software_versions(changed)

    # LIFECYCLE, PARSER and RAW evidence coverage through the real Ovis executor.
    def test_one_runner_one_load_two_generate_calls_and_raw_before_parse(self):
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(self.runner_factory_calls, 1)
        self.assertEqual(report["load_lifecycles"], 1)
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertEqual(len(self.factory.calls), 1)
        self.assertEqual(len(report["calls"]), 2)
        self.assertEqual(len(report["memory"]), 4)
        for call in report["calls"]:
            self.assertEqual(call["task"], "classification")
            raw = self.repo / call["raw_output"]["path"]
            metadata = self.repo / call["metadata"]["path"]
            self.assertEqual(call["raw_output"]["sha256"], provision.sha256_file(raw))
            self.assertEqual(call["metadata"]["sha256"], provision.sha256_file(metadata))
            self.assertEqual(json.loads(metadata.read_text())["parse_status"], "NOT_ATTEMPTED")

    def test_success_and_invalid_classification_are_allowed(self):
        self.assertTrue(smoke.parser_outcome_allowed(SimpleNamespace(
            parse_status=ParseStatus.SUCCESS, error=None,
        )))
        invalid_error = SimpleNamespace(code=ErrorCode.INVALID_CLASSIFICATION)
        self.assertTrue(smoke.parser_outcome_allowed(SimpleNamespace(
            parse_status=ParseStatus.INVALID, error=invalid_error,
        )))
        report = self.run_fake(runner_options={"text": "not JSON"})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual([row["parse_status"] for row in report["calls"]],
                         ["INVALID", "INVALID"])
        self.assertEqual(report["notes"].count(
            "CLASSIFICATION_PARSE_INVALID_NONBLOCKING"
        ), 2)

    def test_parser_failure_blocks_after_raw_preservation(self):
        original = smoke.Ovis2_5Adapter.adapt

        def broken(*args, **kwargs):
            raise RuntimeError("controlled parser failure")

        with patch.object(smoke.Ovis2_5Adapter, "adapt", broken):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["code"], ErrorCode.PARSER_FAILURE.value)
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertTrue(report["calls"][0]["raw_output"])
        self.assertNotIn("controlled parser failure", json.dumps(report))
        self.assertTrue(callable(original))

    def test_any_other_error_and_incomplete_second_call_block(self):
        report = self.run_fake(runner_options={"failure_on_call": 2})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertEqual(len(report["calls"]), 2)
        self.assertEqual(report["calls"][1]["error"]["code"],
                         ErrorCode.GENERATION_FAILURE.value)
        self.assertIsNone(report["calls"][1]["raw_output"])

    def test_preservation_failure_blocks_adapter(self):
        with patch.object(smoke.FileRawStore, "preserve", side_effect=OSError()), \
                patch.object(smoke.Ovis2_5Adapter, "adapt") as adapter:
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["code"], ErrorCode.RAW_PRESERVATION_FAILURE.value)
        adapter.assert_not_called()

    # NETWORK coverage.
    def test_offline_environment_is_required_before_backend(self):
        report = self.run_fake(environment=False)
        self.assertEqual(report["blocker"]["stage"], "OFFLINE_PREFLIGHT")
        self.assertEqual(self.runner_factory_calls, 0)

    def test_socket_attempt_is_counted_and_fails(self):
        report = self.run_fake(runner_options={"network_attempt": True})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["network_violation_count"], 1)
        self.assertEqual(report["native_generate_calls"], 1)

    # PLACEMENT and DTYPE coverage.
    def test_parameter_placement_cuda_zero_passes_cpu_and_meta_block(self):
        good = CensusModel()
        self.assertTrue(smoke.inspect_model_placement(good)["passed"])
        cpu = CensusModel(parameter_device="cpu")
        observed = smoke.inspect_model_placement(cpu)
        self.assertFalse(observed["passed"])
        self.assertIn("FLOATING_PARAMETER_OUTSIDE_CUDA_0", observed["violations"])
        meta = CensusModel(include_meta=True)
        observed = smoke.inspect_model_placement(meta)
        self.assertFalse(observed["passed"])
        self.assertIn("META_PARAMETER", observed["violations"])

    def test_bad_parameter_placement_blocks_before_native_generate(self):
        report = self.run_fake(runner_options={"parameter_device": "cpu"})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["runtime_check_failure"], "PARAMETER_PLACEMENT_VIOLATION")
        self.assertEqual(report["native_generate_calls"], 0)

    def test_bf16_census_recorded_and_dtype_deviation_blocks(self):
        good = smoke.inspect_model_dtypes(CensusModel())
        self.assertTrue(good["passed"])
        self.assertIn("torch.bfloat16", good["floating_parameter_census"]["by_dtype"])
        bad = smoke.inspect_model_dtypes(CensusModel(parameter_dtype="torch.float16"))
        self.assertFalse(bad["passed"])
        self.assertEqual(bad["status"], "DTYPE_DEVIATION_REVIEW_REQUIRED")
        report = self.run_fake(runner_options={"parameter_dtype": "torch.float16"})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["runtime_check_failure"], "DTYPE_DEVIATION_REVIEW_REQUIRED")
        self.assertEqual(report["native_generate_calls"], 0)

    # MEMORY/OOM and no-fallback coverage.
    def test_memory_snapshot_records_required_allocator_fields(self):
        row = smoke.memory_snapshot(self.fake_torch, "before_load")
        for key in ("memory_allocated", "memory_reserved", "max_memory_allocated",
                    "max_memory_reserved", "free_bytes", "total_bytes"):
            self.assertIn(key, row)

    def test_oom_fails_once_without_fallback_or_second_runner(self):
        runner_factory = self.make_runner(failure_on_call=1)
        # Set the synthetic exception type before the model is loaded.
        original = self.factory.from_pretrained

        def create(*args, **kwargs):
            model = original(*args, **kwargs)
            model.oom = True
            return model

        self.factory.from_pretrained = create
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, {
                "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                "HF_HUB_DISABLE_TELEMETRY": "1",
            }))
            stack.enter_context(patch.object(smoke.subprocess, "check_output",
                                             return_value="a" * 40))
            stack.enter_context(patch.object(smoke, "software_versions",
                                             return_value=dict(PINNED_SOFTWARE)))
            stack.enter_context(patch.object(smoke, "probe_hardware", return_value=hardware()))
            stack.enter_context(patch.object(smoke, "cached_snapshot", return_value=self.snapshot))
            stack.enter_context(patch.object(smoke, "verify_snapshot",
                                             return_value=verification_ok()))
            report = smoke.run_smoke(
                "oom-test", repo=self.repo, runner_factory=runner_factory,
                torch_module=self.fake_torch, rerun_of="old", rerun_reason="approved test",
            )
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertTrue(report["native_errors"][0]["oom"])
        self.assertEqual(self.runner_factory_calls, 1)
        self.assertEqual(report["precision"], "BF16")
        self.assertEqual(report["quantization"], "NONE")

    # EVIDENCE/POLICY coverage.
    def test_bundle_is_allowlisted_hashed_and_excludes_weights_secrets_images(self):
        report = self.run_fake()
        run_root = self.repo / smoke.ARTIFACTS / report["run_id"]
        (run_root / "secret-token.txt").write_text("secret")
        (run_root / "model.safetensors").write_bytes(b"weight")
        (run_root / "RUNTIME_SMOKE_01.png").write_bytes(b"image")
        bundle = smoke.create_evidence_bundle(run_root, self.repo)
        self.assertEqual(bundle["sha256"], provision.sha256_file(
            self.repo / bundle["path"]
        ))
        with zipfile.ZipFile(self.repo / bundle["path"]) as archive:
            names = set(archive.namelist())
        self.assertIn("runtime_report.json", names)
        self.assertIn("calls/RUNTIME_SMOKE_01/response.raw", names)
        self.assertFalse(any("safetensors" in name or "secret" in name
                             or name.endswith(".png") for name in names))
        sidecar = (self.repo / bundle["sidecar"]).read_text()
        self.assertIn(bundle["sha256"], sidecar)

    def test_report_structure_claims_and_early_failure_are_deterministic(self):
        failed = self.run_fake("early-fail", environment=False)
        passed = self.run_fake("later-pass", rerun=True)
        self.assertEqual(set(failed), set(passed))
        self.assertTrue(all(value is False for value in passed["claims"].values()))
        self.assertEqual(passed["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(passed["custom_remote_code"]["trust_remote_code"], True)
        self.assertEqual(passed["custom_remote_code"]["local_files_only"], True)

    def test_rerun_requires_link_reason_and_new_id(self):
        with self.assertRaises(ValueError):
            smoke.run_smoke("retry", repo=self.repo, rerun_of="old")
        first = self.run_fake("first-attempt", rerun=False)
        self.assertIn(first["status"], {"RUNTIME_SMOKE_PASS", "RUNTIME_SMOKE_FAIL"})
        with self.assertRaisesRegex(ValueError, "EXISTING_ATTEMPT"):
            smoke.run_smoke("unlinked", repo=self.repo)
        linked = self.run_fake("linked", rerun=True)
        self.assertEqual(linked["rerun_of"], "approved-previous")
        self.assertEqual(linked["rerun_reason"], "unit test")

    def test_no_grounding_synthetic_v1_inspecsafe_or_protocol_freeze_execution(self):
        source = (smoke.ROOT / "scripts/w2_ovis_gpu_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn("Task.GROUNDING", source)
        self.assertNotIn("data/raw", source)
        self.assertNotIn("InspecSafe", source)
        self.assertNotIn("external_gate_cases", source)
        plan = smoke.load_plan()
        self.assertEqual(plan["case_ids"], smoke.CASE_IDS)
        self.assertEqual(plan["protocol_freeze_commit_sha"], "PENDING")

    def test_attention_is_observed_without_runner_override(self):
        report = self.run_fake()
        self.assertEqual(report["attention"]["effective"], "flash_attention_2")
        self.assertFalse(report["attention"]["runner_override"])
        kwargs = self.factory.calls[0][1]
        self.assertNotIn("attn_implementation", kwargs)
        self.assertTrue(kwargs["trust_remote_code"])
        self.assertTrue(kwargs["local_files_only"])

    def test_snapshot_failure_prevents_runner_creation(self):
        failed = verification_ok()
        failed["LOCAL_SNAPSHOT_VERIFIED"] = False
        failed["weights"]["LOCAL_WEIGHT_BYTES_VERIFIED"] = False
        report = self.run_fake(snapshot_verification=failed)
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["code"], "LOCAL_SNAPSHOT_VERIFICATION_FAILED")
        self.assertEqual(self.runner_factory_calls, 0)

    def test_artifact_paths_are_ignored_by_git(self):
        result = __import__("subprocess").run(
            ["git", "check-ignore", "--stdin"],
            cwd=smoke.ROOT,
            input=(smoke.ARTIFACTS + "/run/runtime_report.json\n"
                   "data/processed/hf-cache/model.safetensors\n"
                   "data/processed/ovis_gpu_smoke_evidence.zip\n"),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(len(result.stdout.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
