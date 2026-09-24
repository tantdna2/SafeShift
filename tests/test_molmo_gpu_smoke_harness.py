"""Offline-only tests for the Molmo GPU smoke PREP harness.

Every CUDA/model observation here is synthetic.  The suite blocks real network
entry points and injects the Molmo runner's fake backend; it is not runtime evidence.
"""

import builtins
from contextlib import ExitStack, redirect_stdout
from io import BytesIO, StringIO
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

from scripts import provision_molmo2_o_snapshot as provision
from scripts import w2_molmo_gpu_smoke as smoke
from safeshift.runners.contracts import ErrorCode, ParseStatus
from safeshift.runners.molmo2_o import Molmo2ORunner, MolmoBackend
from tests.test_molmo_runner import Model, Runtime, Tensor


PINNED_SOFTWARE = {**smoke.PINNED_PACKAGES, "python": "3.11.9",
                   "torch": "2.8.0+cu128", "torch_cuda_runtime": "12.8"}
BACKEND_SOFTWARE = {key: PINNED_SOFTWARE[key] for key in
                    ("python", "torch", "transformers", "pillow", "huggingface_hub")}


def hardware(*, available=True, names=("Synthetic CUDA device",),
             memory=40 * 1024**3, capability=(8, 0), fp32=True, current=0):
    return {
        "cuda_available": available,
        "visible_gpu_count": len(names) if available else 0,
        "current_device": current if available and names else None,
        "fp32_supported": fp32,
        "gpus": [
            {
                "index": index,
                "name": name,
                "total_memory_bytes": memory,
                "compute_capability": list(capability),
                "fp32_supported": fp32,
            }
            for index, name in enumerate(names)
        ] if available else [],
        "nvidia_smi_inventory": [],
        "driver_versions": ["550.54"],
    }


def verification_ok():
    return {
        "schema_version": "molmo-local-snapshot-contract-verification-v1",
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
    def __init__(self, device="cuda:0", dtype="torch.float32", *, numel=8, floating=True):
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


class CensusModel(Model):
    def __init__(self, runtime, snapshot, *, parameter_device="cuda:0", parameter_dtype="torch.float32",
                 include_meta=False, failure_on_call=None, network_attempt_mode=None,
                 text='{"safety_level":"Level02"}', device_map=None, oom=False):
        super().__init__(runtime, snapshot)
        self.device = "cuda:0"
        self.hf_device_map = {"": 0} if device_map is None else device_map
        runtime.processor.text = text
        self.failure_on_call = failure_on_call
        self.network_attempt_mode = network_attempt_mode
        self.oom = oom
        self._parameters = [CensusTensor(parameter_device, parameter_dtype)]
        if include_meta:
            self._parameters.append(CensusTensor("meta", parameter_dtype))
        self._buffers = [CensusTensor("cuda:0", "torch.int64", floating=False)]
        self.generate_calls = []

    def parameters(self):
        return iter(self._parameters)

    def buffers(self):
        return iter(self._buffers)

    def generate_impl(self, **kwargs):
        self.generate_calls.append(kwargs)
        call_number = len(self.generate_calls)
        if self.network_attempt_mode == "create_connection":
            socket.create_connection(("example.invalid", 443))
        elif self.network_attempt_mode == "getaddrinfo":
            socket.getaddrinfo("example.invalid", 443)
        elif self.network_attempt_mode == "sendto":
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.sendto(b"offline-test", ("127.0.0.1", 9))
        elif self.network_attempt_mode in {"connect", "connect_ex"}:
            with socket.socket() as client:
                getattr(client, self.network_attempt_mode)(("127.0.0.1", 9))
        if self.failure_on_call == call_number:
            raise OutOfMemoryError("synthetic OOM") if self.oom else RuntimeError("synthetic native failure")
        return super().generate_impl(**kwargs)


class OutOfMemoryError(RuntimeError):
    pass


class CensusFactory:
    def __init__(self, runtime, **model_options):
        self.calls = []
        self.models = []
        self.model_options = model_options
        self.runtime = runtime

    def from_pretrained(self, local_path, **kwargs):
        self.calls.append((local_path, kwargs))
        model = CensusModel(self.runtime, local_path, **self.model_options)
        self.models.append(model)
        return model


class FakeCuda:
    def __init__(self):
        self.reset_calls = []

    def device_count(self):
        return 1

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
        self.stack.enter_context(patch.dict(os.environ, {"B3B_PREP_HEAD": "a" * 40}))
        self.network_guards = []
        for target in (
            "socket.socket.connect",
            "socket.socket.connect_ex",
            "socket.socket.sendto",
            "socket.create_connection",
            "socket.getaddrinfo",
        ):
            self.network_guards.append(self.stack.enter_context(
                patch(target, side_effect=AssertionError("network forbidden in unit tests"))
            ))
        original_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub"} and name not in sys.modules:
                raise AssertionError("real ML imports forbidden")
            return original_import(name, *args, **kwargs)
        self.stack.enter_context(patch("builtins.__import__", side_effect=guarded_import))
        self.temp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.repo = Path(self.temp)
        for relative in (smoke.PLAN, provision.PROVENANCE, "scripts/w2_molmo_gpu_smoke.py"):
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
        runtime = Runtime(self.snapshot)
        factory = CensusFactory(runtime, **model_options)
        resolver = Mock(return_value=str(self.snapshot.resolve()))
        runner = Molmo2ORunner(backend_factory=lambda: MolmoBackend(
            runtime.torch, runtime.processor_factory, factory, dict(BACKEND_SOFTWARE), resolver))
        self.factory, self.resolver, self.runner = factory, resolver, runner
        self.runner_factory_calls = 0
        self.runtime = runtime

        def runner_factory():
            self.runner_factory_calls += 1
            return runner

        return runner_factory

    def fake_git(self, args, **kwargs):
        if args[1] == "rev-parse":
            return "a" * 40
        if args[1] == "status":
            return ""
        if args[1] == "show":
            return (self.repo / smoke.PLAN).read_bytes()
        raise AssertionError(args)

    def run_fake(self, run_id=None, *, runner_options=None, environment=True,
                 hardware_result=None, snapshot_verification=None, rerun=True,
                 execution_pin="a" * 40):
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
            if execution_pin is None:
                os.environ.pop("B3B_PREP_HEAD", None)
            else:
                os.environ["B3B_PREP_HEAD"] = execution_pin
            stack.enter_context(patch.object(
                smoke.subprocess, "check_output", side_effect=self.fake_git
            ))
            self.software_probe = stack.enter_context(patch.object(
                smoke, "software_versions", return_value=dict(PINNED_SOFTWARE)
            ))
            self.hardware_probe = stack.enter_context(patch.object(
                smoke, "probe_hardware", return_value=hardware_result or hardware()
            ))
            self.snapshot_resolver = stack.enter_context(patch.object(
                smoke, "cached_snapshot", return_value=self.snapshot
            ))
            self.snapshot_verifier = stack.enter_context(patch.object(
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
        self.assertEqual(plan["model_id"], "allenai/Molmo2-O-7B")
        self.assertEqual(plan["revision"], provision.REVISION)
        self.assertEqual((plan["precision"], plan["quantization"]), ("FP32", "NONE"))
        self.assertEqual(plan["device"], {"placement": "auto"})
        self.assertEqual(plan["decoding"], {"do_sample": False, "max_new_tokens": 32})
        self.assertNotIn("temperature", plan["decoding"])
        self.assertEqual(plan["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(plan["task"], "classification")
        self.assertEqual(plan["hardware"]["memory_gate"], "OBSERVATIONAL_MEMORY_GATE")
        self.assertIsNone(plan["hardware"]["min_vram_bytes"])
        self.assertEqual(plan["number_of_calls"], 2)
        self.assertEqual(plan["runner_version"], "molmo2-o-runner-v1")

    def test_prompt_hash_and_explicit_runner_decoding(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["prompt_sha256"], hashlib.sha256(plan["prompt"].encode()).hexdigest())
        self.assertEqual(smoke.generation_decoding(plan), {"do_sample": False, "max_new_tokens": 32})

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
        self.assertEqual(provision.MODEL_ID, provision.RESOLVED_REPOSITORY_ID)

    def test_exact_seven_weight_hashes_and_sizes_match_provenance(self):
        rows = provision.weight_files()
        self.assertEqual(rows, [dict(row) for row in provision.EXPECTED_WEIGHT_FILES])
        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(row["size_bytes"] for row in rows), 31_043_241_424)

    def test_local_weight_hash_success_wrong_hash_and_missing(self):
        descriptions = []
        for index in range(7):
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
        for index in range(len(provision.CRITICAL_PROVENANCE_FILES)):
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
        pinned = report["files"][:len(critical)]
        unpinned = report["files"][len(critical):]
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
    def test_hardware_capabilities_pass_independently_of_gpu_name(self):
        for name in ("Unlisted CUDA GPU", "CUDA logical device"):
            observed = hardware(names=(name,), memory=1024, capability=(7, 5))
            self.assertTrue(smoke.require_cuda_fp32(observed))
        self.assertTrue(smoke.require_cuda_fp32(hardware(names=("GPU0", "GPU1"))))

    def test_hardware_capability_failures_block_before_runner(self):
        for observed, code in ((hardware(available=False, names=()), "CUDA_NOT_AVAILABLE"),
                               (hardware(names=()), "REQUIRES_VISIBLE_CUDA_GPU"),
                               (hardware(fp32=False), "FP32_OR_MEMORY_OBSERVATION_MISSING")):
            with self.subTest(code=code):
                report = self.run_fake(hardware_result=observed)
                self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
                self.assertEqual(report["blocker"]["code"], code)
                self.assertEqual(self.runner_factory_calls, 0)
                self.snapshot_resolver.assert_not_called()

    def assert_pin_failure(self, pin, code):
        report = self.run_fake(execution_pin=pin)
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["stage"], "EXECUTION_IDENTITY")
        self.assertEqual(report["blocker"]["code"], code)
        self.assertEqual(report["git_commit"], "a" * 40)
        self.assertEqual(report["execution_pin"], pin)
        self.assertFalse(report["execution_identity_verified"])
        self.assertEqual(self.runner_factory_calls, 0)
        self.assertEqual(self.factory.calls, [])
        self.assertEqual(report["native_generate_calls"], 0)
        for probe in (self.software_probe, self.hardware_probe,
                      self.snapshot_resolver, self.snapshot_verifier):
            probe.assert_not_called()

    def test_missing_execution_pin_blocks_before_all_preflights(self):
        self.assert_pin_failure(None, "B3B_PREP_HEAD_REQUIRED")

    def test_invalid_execution_pin_blocks_before_all_preflights(self):
        for pin in ("", "abc", "A" * 40, "g" * 40, "a" * 39, "a" * 41,
                    "a" * 40 + "\n"):
            with self.subTest(pin=pin):
                self.assert_pin_failure(pin, "B3B_PREP_HEAD_INVALID")

    def test_mismatched_execution_pin_blocks_before_all_preflights(self):
        self.assert_pin_failure("b" * 40, "EXECUTION_COMMIT_MISMATCH")

    def test_exact_execution_pin_continues_and_records_identity(self):
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(report["git_commit"], "a" * 40)
        self.assertEqual(report["execution_pin"], "a" * 40)
        self.assertTrue(report["execution_identity_verified"])
        root = self.repo / smoke.ARTIFACTS / report["run_id"]
        self.assertEqual(json.loads((root / "runtime_report.json").read_text()), report)
        environment = json.loads((root / "environment.json").read_text())
        self.assertEqual(environment["environment"]["B3B_PREP_HEAD"], "a" * 40)
        self.assertEqual(self.runner_factory_calls, 1)

    def test_all_software_versions_are_pinned(self):
        self.assertTrue(smoke.validate_software_versions(PINNED_SOFTWARE))
        for key in smoke.PINNED_PACKAGES:
            changed = {**PINNED_SOFTWARE, key: "0.0.0"}
            with self.subTest(key=key), self.assertRaises(ValueError):
                smoke.validate_software_versions(changed)
        changed = {**PINNED_SOFTWARE, "huggingface_hub": ""}
        with self.assertRaises(ValueError):
            smoke.validate_software_versions(changed)

    # LIFECYCLE, PARSER and RAW evidence coverage through the real Molmo executor.
    def test_one_runner_one_load_two_generate_calls_and_raw_before_parse(self):
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(self.runner_factory_calls, 1)
        self.assertEqual(report["load_lifecycles"], 1)
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertEqual(len(self.factory.calls), 1)
        self.assertEqual(len(report["calls"]), 2)
        self.assertEqual(len(report["memory"]), 4)
        self.assertEqual(report["initialize_lifecycles"], 1)
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
        original = smoke.Molmo2OAdapter.adapt

        def broken(*args, **kwargs):
            raise RuntimeError("controlled parser failure")

        with patch.object(smoke.Molmo2OAdapter, "adapt", broken):
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
                patch.object(smoke.Molmo2OAdapter, "adapt") as adapter:
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["code"], ErrorCode.RAW_PRESERVATION_FAILURE.value)
        adapter.assert_not_called()

    # NETWORK coverage.
    def test_offline_environment_is_required_before_backend(self):
        report = self.run_fake(environment=False)
        self.assertEqual(report["blocker"]["stage"], "OFFLINE_PREFLIGHT")
        self.assertEqual(self.runner_factory_calls, 0)

    def assert_production_network_denial(self, mode):
        report = self.run_fake(runner_options={"network_attempt_mode": mode})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["network_violation_count"], 1)
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertEqual(report["native_errors"][0]["exception_type"], "RuntimeError")
        self.assertEqual(self.runner_factory_calls, 1)
        self.assertEqual(len(self.factory.calls), 1)
        self.assertEqual(len(report["calls"]), 1)
        self.assertEqual((report["precision"], report["quantization"]), ("FP32", "NONE"))
        # The outer safety guards must never handle this attempt: production's
        # firewall must override them and increment its own violation counter.
        for guard in self.network_guards:
            guard.assert_not_called()

    def test_production_firewall_create_connection_counts_and_fails(self):
        self.assert_production_network_denial("create_connection")

    def test_production_firewall_sendto_counts_and_fails(self):
        self.assert_production_network_denial("sendto")

    def test_production_firewall_getaddrinfo_counts_and_fails(self):
        self.assert_production_network_denial("getaddrinfo")

    def test_production_firewall_connect_and_connect_ex_count_and_fail(self):
        for mode in ("connect", "connect_ex"):
            with self.subTest(mode=mode):
                self.assert_production_network_denial(mode)

    # PLACEMENT and DTYPE coverage.
    def test_parameter_placement_cuda_zero_passes_cpu_and_meta_block(self):
        good = CensusModel(Runtime(self.snapshot), self.snapshot)
        self.assertTrue(smoke.inspect_model_placement(good, 1)["passed"])
        cpu = CensusModel(Runtime(self.snapshot), self.snapshot, parameter_device="cpu")
        observed = smoke.inspect_model_placement(cpu, 1)
        self.assertFalse(observed["passed"])
        self.assertIn("PARAMETERS_OUTSIDE_VISIBLE_CUDA", observed["violations"])
        meta = CensusModel(Runtime(self.snapshot), self.snapshot, include_meta=True)
        observed = smoke.inspect_model_placement(meta, 1)
        self.assertFalse(observed["passed"])
        self.assertIn("PARAMETERS_OUTSIDE_VISIBLE_CUDA", observed["violations"])

    def test_bad_parameter_placement_blocks_before_native_generate(self):
        report = self.run_fake(runner_options={"parameter_device": "cpu"})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["runtime_check_failure"], "PARAMETER_PLACEMENT_VIOLATION")
        self.assertEqual(report["native_generate_calls"], 0)

    def test_fp32_census_recorded_and_dtype_deviation_blocks(self):
        good = smoke.inspect_model_dtypes(CensusModel(Runtime(self.snapshot), self.snapshot))
        self.assertTrue(good["passed"])
        self.assertIn("torch.float32", good["floating_parameter_census"]["by_dtype"])
        bad = smoke.inspect_model_dtypes(CensusModel(Runtime(self.snapshot), self.snapshot, parameter_dtype="torch.float16"))
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
            self.assertIn(key, row["gpus"][0])

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
                                             side_effect=self.fake_git))
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
        self.assertEqual(report["precision"], "FP32")
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
        source = (smoke.ROOT / "scripts/w2_molmo_gpu_smoke.py").read_text(encoding="utf-8")
        self.assertNotIn("Task.GROUNDING", source)
        self.assertNotIn("data/raw", source)
        self.assertNotIn("InspecSafe", source)
        self.assertNotIn("external_gate_cases", source)
        plan = smoke.load_plan()
        self.assertEqual(plan["case_ids"], smoke.CASE_IDS)
        self.assertEqual(plan["protocol_freeze_commit_sha"], "PENDING")

    def test_loader_uses_auto_without_attention_override(self):
        self.run_fake()
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

    def test_config_bytes_hash_mismatch_blocks_all_runtime_probes(self):
        path = self.repo / smoke.PLAN
        path.write_bytes(path.read_bytes() + b"\n")
        report = self.run_fake()
        self.assertEqual(report["blocker"]["code"], "SMOKE_CONFIG_HASH_MISMATCH")
        self.software_probe.assert_not_called()
        self.hardware_probe.assert_not_called()
        self.snapshot_resolver.assert_not_called()

    def test_wrong_revision_rejected_even_with_matching_config_hash(self):
        plan = smoke.expected_plan()
        plan["revision"] = "b" * 40
        path = self.repo / smoke.PLAN
        path.write_bytes(json.dumps(plan).encode())
        with patch.object(smoke, "SMOKE_CONFIG_SHA256", provision.sha256_file(path)):
            with self.assertRaisesRegex(ValueError, "SMOKE_PLAN_CHANGED"):
                smoke.load_plan(self.repo)

    def test_dirty_worktree_and_wrong_committed_config_block(self):
        original = self.fake_git
        for broken_command, result, code in (("status", " M script.py", "TRACKED_WORKTREE_DIRTY"),
                                              ("show", b"wrong", "COMMITTED_CONFIG_HASH_MISMATCH")):
            def altered(args, **kwargs):
                return result if args[1] == broken_command else original(args, **kwargs)
            with patch.object(self, "fake_git", side_effect=altered):
                report = self.run_fake()
            self.assertEqual(report["blocker"]["code"], code)
            self.hardware_probe.assert_not_called()
            self.snapshot_resolver.assert_not_called()

    def test_weight_size_mismatch_with_correct_hash_fails(self):
        descriptors = []
        for index in range(7):
            name = f"tiny-{index}.safetensors"
            (self.snapshot / name).write_bytes(b"fixture")
            descriptors.append({"path": name, "size_bytes": 8,
                                "lfs_sha256": hashlib.sha256(b"fixture").hexdigest()})
        report = provision.verify_weights(self.snapshot, descriptors)
        self.assertFalse(report["LOCAL_WEIGHT_BYTES_VERIFIED"])
        self.assertTrue(all(row["sha256"] == row["expected_sha256"] for row in report["files"]))

    def test_critical_source_mismatch_fails_without_claim_promotion(self):
        (self.snapshot / "config.json").write_bytes(b"changed")
        report = provision.verify_critical_files(self.snapshot)
        row = next(r for r in report["files"] if r["path"] == "config.json")
        self.assertEqual(row["verification_status"], "HASH_MISMATCH")
        self.assertFalse(row["verified"])
        self.assertFalse(report["CRITICAL_PROVENANCE_HASHES_VERIFIED"])

    def test_documentary_manifests_have_sources_and_do_not_change_b0_claims(self):
        rows = provision.critical_files()
        self.assertEqual(len(rows), 14)
        for row in rows:
            self.assertIn(provision.REVISION, row["url"])
            self.assertEqual(len(row["sha256"]), 64)
            self.assertGreater(row["size_bytes"], 0)
        _, record = provision._provenance()
        self.assertFalse(record["weight_provenance"]["downloaded"])
        self.assertFalse(record["weight_provenance"]["local_bytes_verified"])

    def test_verify_only_firewall_covers_byte_verification(self):
        def network_in_verification(*args):
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            socket.getaddrinfo("example.invalid", 443)

        argv = ["provision", "--verify-only", "--report-dir", "data/processed/verify-only-test"]
        with patch.object(provision, "ROOT", self.repo), patch.object(sys, "argv", argv), \
                patch.object(provision, "cached_snapshot", return_value=self.snapshot) as resolver, \
                patch.object(provision, "verify_snapshot", side_effect=network_in_verification), \
                redirect_stdout(StringIO()):
            self.assertEqual(provision.main(), 1)
        resolver.assert_called_once_with(None, offline=True)
        report = json.loads((self.repo / "data/processed/verify-only-test/snapshot_verification.json").read_text())
        self.assertEqual(report["operation"]["network_violation_count"], 1)
        self.assertFalse(report["LOCAL_SNAPSHOT_VERIFIED"])
        for guard in self.network_guards:
            guard.assert_not_called()

    def test_third_native_call_is_blocked_before_model(self):
        self.run_fake()
        model = self.factory.models[0]
        with self.assertRaisesRegex(ValueError, "THIRD_CALL_FORBIDDEN"):
            model.generate()
        self.assertEqual(len(model.generate_calls), 2)

    def test_third_case_rejected_without_inference(self):
        cases = smoke.generate_cases(self.repo)
        with patch.object(smoke, "generate_cases", return_value=cases + [cases[0]]):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_generate_calls"], 0)

    def test_raw_and_metadata_exist_when_adapter_starts(self):
        original = smoke.Molmo2OAdapter.adapt

        def checked(adapter, raw, task):
            matches = [p for p in self.repo.rglob("response.raw") if p.read_bytes() == raw]
            self.assertTrue(matches)
            self.assertTrue(any(p.with_name("metadata.json").is_file() for p in matches))
            return original(adapter, raw, task)

        with patch.object(smoke.Molmo2OAdapter, "adapt", checked):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")

    def test_grounding_and_output_invariance_have_no_semantic_claim(self):
        report = self.run_fake()
        self.assertEqual(report["grounding"], {"status": "DOCUMENTED_NATIVE_POINT",
                         "qualification": "NOT_YET_QUALIFIED", "box_iou_participation": "NOT_PARTICIPATING"})
        self.assertEqual(report["output_observation"], {"status": "RUNTIME_OBSERVATION",
                         "input_hashes_distinct": True, "raw_hashes_identical": True,
                         "semantic_interpretation": "NONE"})
        self.assertFalse(report["hardware_validated"])

    def test_disk_offload_observed_and_blocks(self):
        report = self.run_fake(runner_options={"device_map": {"vision": 0, "text": "disk"}})
        self.assertTrue(report["parameter_placement"]["disk_offload_detected"])
        self.assertEqual(report["native_generate_calls"], 0)
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")

    def test_device_map_absence_and_multiple_gpus_are_observed(self):
        model = CensusModel(Runtime(self.snapshot), self.snapshot)
        model._parameters.append(CensusTensor("cuda:1", "torch.float32", numel=16))
        model.hf_device_map = {"vision": 0, "text": "cuda:1"}
        report = smoke.inspect_model_placement(model, 2)
        self.assertTrue(report["passed"])
        self.assertEqual(report["gpu_parameter_counts"], {"cuda:0": 1, "cuda:1": 1})
        self.assertEqual(report["parameters"]["total"], {"tensor_count": 2, "numel": 24, "bytes": 96})
        del model.hf_device_map
        self.assertIsNone(smoke.inspect_model_placement(model, 2)["hf_device_map"])

    def test_memory_records_each_visible_gpu(self):
        with patch.object(self.cuda, "device_count", return_value=2):
            report = smoke.memory_snapshot(self.fake_torch, "after_call_2")
        self.assertEqual([gpu["device"] for gpu in report["gpus"]], ["cuda:0", "cuda:1"])

    def test_hardware_probe_records_inventory_without_name_gate(self):
        from contextlib import nullcontext
        cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 2,
                               get_device_properties=lambda i: SimpleNamespace(name=f"Any GPU {i}",
                                   total_memory=40 * 1024**3, major=8, minor=6),
                               device=lambda i: nullcontext(), is_bf16_supported=lambda: True,
                               current_device=lambda: 0, get_arch_list=lambda: ["sm_86"])
        inventory = "0, Any GPU 0, GPU-fake0, 570.1, 40960, Disabled\n1, Any GPU 1, GPU-fake1, 570.1, 40960, Disabled\n"
        with patch.object(smoke.subprocess, "run", return_value=SimpleNamespace(stdout=inventory)):
            observed = smoke.probe_hardware(SimpleNamespace(cuda=cuda))
        self.assertEqual(observed["visible_gpu_count"], 2)
        self.assertEqual(observed["driver_versions"], ["570.1"])
        self.assertEqual(observed["gpus"][1]["compute_capability"], [8, 6])
        self.assertTrue(observed["gpus"][1]["fp32_supported"])
        self.assertTrue(smoke.require_cuda_fp32(observed))

    def test_software_probe_records_exact_package_versions_and_cuda(self):
        pins = {("torch" if key == "torch_distribution" else key): value
                for key, value in smoke.PINNED_PACKAGES.items()}
        torch = SimpleNamespace(__version__="2.8.0+cu128", version=SimpleNamespace(cuda="12.8"))
        with patch.object(smoke.importlib.metadata, "version", side_effect=pins.__getitem__):
            versions = smoke.software_versions(torch)
        self.assertTrue(smoke.validate_software_versions(versions))

    def test_swallowed_network_attempt_still_blocks_second_call(self):
        original = CensusModel.generate_impl
        def swallowed(model, **kwargs):
            try:
                socket.getaddrinfo("example.invalid", 443)
            except RuntimeError:
                pass
            return original(model, **kwargs)
        with patch.object(CensusModel, "generate_impl", swallowed):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["network_violation_count"], 1)
        self.assertEqual(report["native_generate_calls"], 1)

    def test_geometry_png_bytes_hash_and_pixel_design(self):
        from PIL import Image
        cases = smoke.generate_cases(self.repo)
        self.assertEqual([metadata["image_sha256"] for _, metadata in cases], smoke.CASE_HASHES)
        for data, metadata in cases:
            with Image.open(BytesIO(data)) as image:
                image.load()
                self.assertEqual(image.size, (224, 192))
                self.assertEqual(image.mode, "RGB")
        with Image.open(BytesIO(cases[0][0])) as image:
            self.assertEqual(image.getpixel((30, 30)), (25, 101, 204))

    def test_pass_bundle_requires_all_ten_files(self):
        report = self.run_fake()
        root = self.repo / smoke.ARTIFACTS / report["run_id"]
        (root / "case_manifest.json").unlink()
        with self.assertRaisesRegex(ValueError, "MISSING_PASS_REPORT"):
            smoke.create_evidence_bundle(root, self.repo)

    def test_bundle_rejects_tampered_raw_evidence(self):
        report = self.run_fake()
        raw = self.repo / report["calls"][0]["raw_output"]["path"]
        raw.write_bytes(b"changed")
        root = self.repo / smoke.ARTIFACTS / report["run_id"]
        with self.assertRaisesRegex(ValueError, "CALL_EVIDENCE_HASH_MISMATCH"):
            smoke.create_evidence_bundle(root, self.repo)

    def test_artifact_paths_are_ignored_by_git(self):
        result = __import__("subprocess").run(
            ["git", "check-ignore", "--stdin"],
            cwd=smoke.ROOT,
            input=(smoke.ARTIFACTS + "/run/runtime_report.json\n"
                   "data/processed/hf-cache/model.safetensors\n"
                   "data/processed/molmo_gpu_smoke_evidence.zip\n"),
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(len(result.stdout.splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
