"""All GPU/model observations below are fakes, never runtime validation evidence."""

import builtins
import ast
from dataclasses import replace
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import provision_qwen3vl_snapshot as provision
from scripts import w2_qwen_kaggle_smoke as smoke
from safeshift.runners.qwen3_vl import Qwen3VLRunner
from safeshift.runners.contracts import ErrorCode, ParseStatus
from tests.test_qwen_runner import Runtime


def hardware(names=("Tesla T4", "Tesla T4")):
    return {"cuda_available": True, "gpu_count": len(names),
            "gpus": [{"name": n, "compute_capability": [7, 5]} for n in names],
            "nvidia_smi": [{"name": n} for n in names]}


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
            self.stack.enter_context(patch(target, side_effect=AssertionError("network forbidden")))
        real_import = builtins.__import__
        self.real_import = real_import

        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub", "accelerate"}:
                raise AssertionError("real ML imports forbidden")
            return real_import(name, *args, **kwargs)

        self.stack.enter_context(patch("builtins.__import__", side_effect=guarded))
        self.tmp = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.repo = Path(self.tmp)
        for name in (smoke.PLAN, provision.PROVENANCE,
                     "configs/pre_freeze/external_gate_cases.v1.provenance.json",
                     "scripts/w2_qwen_kaggle_smoke.py"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(smoke.ROOT / name, target)
        self.runtime = Runtime()
        self.stack.enter_context(patch.dict(self.runtime.backend.software_versions, transformers="4.57.1"))
        self.runtime.model.hf_device_map = {"visual": 0, "language": 1}
        self.runtime.model.config = SimpleNamespace(_attn_implementation="sdpa")
        self.runner = Qwen3VLRunner(backend_factory=self.runtime.factory)
        self.factory = Mock(return_value=self.runner)
        self.cuda = SimpleNamespace(reset_peak_memory_stats=Mock())
        self.versions = {**self.runtime.backend.software_versions, "accelerate": "fake",
                         "huggingface_hub": "fake", "safetensors": "fake"}

    def run_fake(self, run_id="offline-test", **overrides):
        defaults = {"software_versions": self.versions, "probe_hardware": hardware(),
                    "verify_weights": {"LOCAL_WEIGHT_BYTES_VERIFIED": True, "files": []},
                    "cached_snapshot": self.repo / "fake-snapshot",
                    "memory_snapshot": {"stage": "fake", "gpus": []}}
        defaults.update(overrides)
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"))
            stack.enter_context(patch.object(smoke.subprocess, "check_output", return_value="a" * 40))
            for name, value in defaults.items():
                stack.enter_context(patch.object(smoke, name, return_value=value))
            return smoke.run_smoke(run_id, repo=self.repo, runner_factory=self.factory,
                                   rerun_of="offline-fixture", rerun_reason="offline test only",
                                   torch_module=SimpleNamespace(cuda=self.cuda))

    def test_exact_identity(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["model_id"], "Qwen/Qwen3-VL-8B-Instruct")
        self.assertEqual(plan["revision"], "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b")
        self.assertEqual(len(provision.weight_files()), 4)
        self.assertEqual(self.runner.identity.model_id, provision.MODEL_ID)
        self.assertEqual(self.runner.identity.immutable_revision, provision.REVISION)

    def test_snapshot_uses_exact_pin_and_local_only_flag(self):
        download = Mock(return_value="fake-cache")
        with patch.dict(sys.modules, huggingface_hub=SimpleNamespace(snapshot_download=download)), \
                patch("builtins.__import__", self.real_import):
            provision.cached_snapshot("data/processed/hf-cache", offline=False)
            download.assert_called_with(repo_id=provision.MODEL_ID, revision=provision.REVISION,
                                        cache_dir="data/processed/hf-cache", local_files_only=False)
            provision.cached_snapshot("data/processed/hf-cache")
            self.assertTrue(download.call_args.kwargs["local_files_only"])

    def test_plan_not_frozen(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["status"], "PRE_RUNTIME_VALIDATION_PLAN")
        self.assertEqual(plan["protocol_freeze_commit_sha"], "PENDING")

    def test_fixed_condition(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["precision"], "FP16")
        self.assertEqual(plan["quantization"], "NONE")
        self.assertEqual(plan["device"], {"placement": "auto"})
        self.assertEqual(plan["preprocessing"], {"mode": "official_processor"})
        self.assertEqual(plan["attention"], "native_default")

    def test_fixed_smoke_decoding(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["decoding"], {"do_sample": False, "max_new_tokens": 32})
        self.assertEqual(plan["scope"], "SMOKE_ONLY_TECHNICAL_CONFIGURATION")

    def test_prompt_hash(self):
        plan = smoke.load_plan()
        self.assertEqual(plan["prompt_sha256"], hashlib.sha256(plan["prompt"].encode()).hexdigest())

    def test_reject_mutation_and_extra_input(self):
        for key, value in (("precision", "BF16"), ("quantization", "4-bit"),
                           ("prompt", "tuned"), ("input_path", "arbitrary.png"),
                           ("decoding", {"do_sample": 0, "max_new_tokens": 32})):
            plan = smoke.expected_plan()
            plan[key] = value
            (self.repo / smoke.PLAN).write_text(json.dumps(plan), encoding="utf-8")
            with self.subTest(key=key), self.assertRaises(ValueError):
                smoke.load_plan(self.repo)

    def test_exactly_two_deterministic_images(self):
        first = smoke.generate_cases(self.repo)
        self.assertEqual(first, smoke.generate_cases(self.repo))
        self.assertEqual([m["sample_id"] for _, m in first], smoke.CASE_IDS)
        self.assertEqual(len({m["sha256"] for _, m in first}), 2)
        for raw, meta in first:
            self.assertEqual(meta["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual((meta["width"], meta["height"]), (224, 192))

    def test_synthetic_hash_collision_rejected(self):
        digest = smoke.generate_cases(self.repo)[0][1]["sha256"]
        path = self.repo / "configs/pre_freeze/external_gate_cases.v1.provenance.json"
        data = json.loads(path.read_text())
        data["images"][0]["sha256"] = digest
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "COLLISION"):
            smoke.generate_cases(self.repo)

    def test_no_dataset_input_or_grounding(self):
        source = (smoke.ROOT / "scripts/w2_qwen_kaggle_smoke.py").read_text()
        for forbidden in ("InspecSafe", "Task.GROUNDING", "data/raw", "bbox", "backup"):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("input_path", smoke.load_plan())

    def test_gpu_count_rejected(self):
        for count in (0, 1, 3):
            with self.subTest(count=count), self.assertRaises(ValueError):
                smoke.require_t4_pair(hardware(("Tesla T4",) * count))

    def test_non_t4_rejected(self):
        with self.assertRaises(ValueError):
            smoke.require_t4_pair(hardware(("Tesla T4", "A100")))

    def test_cuda_unavailable_rejected(self):
        h = hardware()
        h["cuda_available"] = False
        with self.assertRaises(ValueError):
            smoke.require_t4_pair(h)

    def test_hardware_failure_prevents_load(self):
        report = self.run_fake(probe_hardware=hardware(("Tesla T4",)))
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.factory.assert_not_called()

    def test_local_shard_validation_success_mismatch_and_missing(self):
        files = []
        for i in range(4):
            raw = f"synthetic shard {i}".encode()
            name = f"fixture-{i}.safetensors"
            (self.repo / name).write_bytes(raw)
            files.append({"path": name, "size_bytes": len(raw),
                          "lfs_sha256": hashlib.sha256(raw).hexdigest()})
        self.assertTrue(provision.verify_weights(self.repo, files)["LOCAL_WEIGHT_BYTES_VERIFIED"])
        (self.repo / files[0]["path"]).write_bytes(b"corrupt")
        self.assertFalse(provision.verify_weights(self.repo, files)["LOCAL_WEIGHT_BYTES_VERIFIED"])
        (self.repo / files[0]["path"]).unlink()
        self.assertFalse(provision.verify_weights(self.repo, files)["LOCAL_WEIGHT_BYTES_VERIFIED"])

    def test_weight_mismatch_stops_execution(self):
        report = self.run_fake(verify_weights={"LOCAL_WEIGHT_BYTES_VERIFIED": False, "files": []})
        self.assertEqual(report["blocker"]["code"], "LOCAL_WEIGHT_HASH_MISMATCH")
        self.factory.assert_not_called()

    def test_offline_required_before_backend(self):
        with patch.dict(os.environ, HF_HUB_OFFLINE="0", TRANSFORMERS_OFFLINE="1"), \
                patch.object(smoke.subprocess, "check_output", return_value="a" * 40):
            report = smoke.run_smoke("offline-rejected", repo=self.repo, runner_factory=self.factory)
        self.assertEqual(report["blocker"]["stage"], "OFFLINE_PREFLIGHT")
        self.factory.assert_not_called()

    def test_network_denial(self):
        with self.assertRaisesRegex(RuntimeError, "NETWORK_FORBIDDEN"):
            smoke.block_network()

    def test_two_calls_real_runner_executor_and_preservation(self):
        original = smoke.execute_call
        with patch.object(smoke, "execute_call", wraps=original) as execute:
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(execute.call_count, 2)
        self.assertIs(execute.call_args_list[0].args[0], self.runner)
        self.assertIs(execute.call_args_list[1].args[0], self.runner)
        self.runtime.model_factory.from_pretrained.assert_called_once()
        self.runtime.processor_factory.from_pretrained.assert_called_once()
        kwargs = self.runtime.model_factory.from_pretrained.call_args.kwargs
        self.assertTrue(kwargs["local_files_only"])
        self.assertEqual(kwargs["dtype"], "fake-fp16")
        self.assertEqual(kwargs["device_map"], "auto")
        self.assertNotIn("attn_implementation", kwargs)
        self.assertEqual(report["load_lifecycles"], 1)
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertEqual(len(report["memory"]), 4)
        for row in report["calls"]:
            self.assertTrue(row["cache_state_cleared"])
            for key in ("raw_output", "metadata"):
                self.assertEqual(row[key]["sha256"], provision.sha256_file(self.repo / row[key]["path"]))
            metadata = json.loads((self.repo / row["metadata"]["path"]).read_text())
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(metadata["prompt"], smoke.PROMPT)
            self.assertEqual(metadata["task"], "classification")

    def test_invalid_parse_passes_runtime_without_prompt_mutation(self):
        self.runtime.processor.text = "not JSON"
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(report["notes"].count("CLASSIFICATION_PARSE_INVALID"), 2)
        self.assertEqual((self.repo / smoke.PLAN).read_bytes(), (smoke.ROOT / smoke.PLAN).read_bytes())
        for call in report["calls"]:
            self.assertEqual(call["parse_status"], "INVALID")

    def test_parser_failure_blocks_runtime_smoke(self):
        def fail_adapter(adapter, raw, task):
            paths = list((self.repo / smoke.ARTIFACTS).glob("*/raw/*/response.raw"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].read_bytes(), raw)
            self.assertTrue(paths[0].with_name("metadata.json").exists())
            raise RuntimeError("controlled adapter exception")

        with patch.object(smoke.Qwen3VLAdapter, "adapt", fail_adapter):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["blocker"]["code"], ErrorCode.PARSER_FAILURE)
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertEqual(report["native_errors"], [])
        self.assertEqual(len(report["calls"]), 1)
        call = report["calls"][0]
        self.assertEqual(call["parse_status"], ParseStatus.FAILED)
        self.assertEqual(call["error"]["code"], ErrorCode.PARSER_FAILURE)
        self.assertTrue(call["cache_state_cleared"])
        for key in ("raw_output", "metadata"):
            path = self.repo / call[key]["path"]
            self.assertEqual(provision.sha256_file(path), call[key]["sha256"])
        self.assertNotIn("CLASSIFICATION_PARSE_INVALID", report["notes"])
        self.assertEqual((self.repo / smoke.PLAN).read_bytes(), (smoke.ROOT / smoke.PLAN).read_bytes())

    def test_completed_invalid_statuses_fail_closed_without_error(self):
        original = smoke.execute_call
        for status in (ParseStatus.FAILED, ParseStatus.UNSUPPORTED, ParseStatus.NOT_ATTEMPTED):
            def altered_result(*args, **kwargs):
                # Preserve two actual fake-backend generations and raw artifacts,
                # but inject an inconsistent completed status with no error code.
                result = original(*args, **kwargs)
                return replace(result, parse_status=status, error=None)

            with self.subTest(status=status), patch.object(smoke, "execute_call", altered_result):
                report = self.run_fake("fail-closed-" + status.value)
            self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
            self.assertEqual(report["native_generate_calls"], 2)
            self.assertIsNone(report["blocker"])
            self.assertTrue(all(c["raw_output"] and c["cache_state_cleared"]
                                and c["parse_status"] == status for c in report["calls"]))

    def test_native_oom_stops_without_retry_or_fallback(self):
        class OutOfMemoryError(RuntimeError):
            pass
        self.runtime.model.failure = OutOfMemoryError("private diagnostic")
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_errors"][0]["exception_type"], "OutOfMemoryError")
        self.assertEqual(report["native_generate_calls"], 1)
        self.assertEqual(len(report["calls"]), 1)
        self.assertNotIn("private diagnostic", json.dumps(report))

    def test_second_call_failure_is_not_pass(self):
        original = self.runtime.model.generate

        def fail_second(**kwargs):
            if self.runtime.model.calls:
                raise RuntimeError("second call failed")
            return original(**kwargs)

        self.runtime.model.generate = fail_second
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_generate_calls"], 2)
        self.assertIsNotNone(report["calls"][0]["raw_output"])
        self.assertIsNone(report["calls"][1]["raw_output"])

    def test_preservation_failure_stops_and_blocks_adapter(self):
        with patch.object(smoke.FileRawStore, "preserve", side_effect=OSError()), \
                patch.object(smoke.Qwen3VLAdapter, "adapt") as adapter:
            report = self.run_fake()
        self.assertEqual(report["blocker"]["code"], "RAW_PRESERVATION_FAILURE")
        self.assertEqual(report["native_generate_calls"], 1)
        adapter.assert_not_called()

    def test_raw_and_metadata_exist_at_adapter_entry(self):
        original = smoke.Qwen3VLAdapter.adapt
        observations = []

        def observe(adapter, raw, task):
            paths = list((self.repo / smoke.ARTIFACTS).glob("*/raw/*/response.raw"))
            self.assertTrue(any(p.read_bytes() == raw for p in paths))
            self.assertTrue(all(p.with_name("metadata.json").exists() for p in paths))
            observations.append(len(paths))
            return original(adapter, raw, task)

        with patch.object(smoke.Qwen3VLAdapter, "adapt", observe):
            report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertEqual(observations, [1, 2])

    def test_load_failure(self):
        self.runtime.model_factory.from_pretrained.side_effect = RuntimeError("private")
        report = self.run_fake()
        self.assertEqual(report["blocker"]["code"], "MODEL_LOAD_FAILURE")
        self.assertEqual(report["native_errors"][0]["stage"], "load")
        self.assertEqual(report["native_generate_calls"], 0)

    def test_disk_offload_stops_before_generation(self):
        self.runtime.model.hf_device_map = {"visual": 0, "language": "disk"}
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertIn("disk", report["device_map"].values())
        self.assertEqual(report["native_generate_calls"], 0)

    def test_cpu_offload_is_note(self):
        self.runtime.model.hf_device_map["head"] = "cpu"
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_PASS")
        self.assertIn("RUNTIME_NOTE_CPU_OFFLOAD", report["notes"])

    def test_device_map_normalization_and_missing(self):
        self.assertEqual(smoke.inspect_device_map({"a": "0", "b": "cuda:1"})[0],
                         {"a": "cuda:0", "b": "cuda:1"})
        for mapping in ({}, {"a": "cpu"}, {"a": "cuda:2"}):
            with self.assertRaises(ValueError):
                smoke.inspect_device_map(mapping)

    def test_flash_attention_rejected(self):
        self.runtime.model.config._attn_implementation = "flash_attention_2"
        report = self.run_fake()
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.assertEqual(report["native_generate_calls"], 0)

    def test_wrong_transformers_stops_before_runner(self):
        report = self.run_fake(software_versions={**self.versions, "transformers": "4.56.0"})
        self.assertEqual(report["status"], "RUNTIME_SMOKE_FAIL")
        self.factory.assert_not_called()

    def test_report_schema_on_early_failure_and_pass(self):
        failed = self.run_fake("fail", probe_hardware=hardware(()))
        passed = self.run_fake("pass")
        for key in ("schema_version", "git_commit", "smoke_config_sha256", "images", "hardware",
                    "software_versions", "environment", "weight_verification", "calls", "memory",
                    "prompt_sha256", "device_map", "status", "notes", "blocker"):
            self.assertIn(key, failed)
            self.assertIn(key, passed)
        path = self.repo / smoke.ARTIFACTS / "pass/runtime_report.json"
        self.assertEqual(json.loads(path.read_text()), passed)

    def test_no_overwrite(self):
        self.run_fake()
        with self.assertRaises(FileExistsError):
            self.run_fake()

    def test_rerun_requires_reason(self):
        with self.assertRaises(ValueError):
            smoke.run_smoke("retry", repo=self.repo, rerun_of="previous")

    def test_existing_attempt_requires_rerun_link(self):
        self.run_fake()
        with self.assertRaisesRegex(ValueError, "EXISTING_ATTEMPT"):
            smoke.run_smoke("unlinked", repo=self.repo)

    def test_offline_flags_at_factory_entry(self):
        def factory():
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
            return self.runtime.backend
        self.runner._backend_factory = factory
        self.assertEqual(self.run_fake()["status"], "RUNTIME_SMOKE_PASS")

    def test_probe_records_smi_identity_and_torch_properties(self):
        cuda = SimpleNamespace(device_count=lambda: 2, is_available=lambda: True,
                               get_device_properties=lambda i: SimpleNamespace(
                                   name="Tesla T4", total_memory=16 * 1024**3, major=7, minor=5))
        output = "Tesla T4, GPU-1, 555.1, 15360\nTesla T4, GPU-2, 555.1, 15360\n"
        with patch.object(smoke.subprocess, "run", return_value=SimpleNamespace(stdout=output)):
            observed = smoke.probe_hardware(SimpleNamespace(cuda=cuda))
        smoke.require_t4_pair(observed)
        self.assertEqual(observed["nvidia_smi"][1]["uuid"], "GPU-2")
        self.assertEqual(observed["nvidia_smi"][0]["driver_version"], "555.1")
        self.assertEqual(observed["gpus"][0]["total_memory_bytes"], 16 * 1024**3)

    def test_memory_observations_both_gpus(self):
        cuda = SimpleNamespace(mem_get_info=lambda i: (100 + i, 200),
                               max_memory_allocated=lambda i: 30 + i,
                               max_memory_reserved=lambda i: 40 + i)
        result = smoke.memory_snapshot(SimpleNamespace(cuda=cuda), "before_load")
        self.assertEqual(result["stage"], "before_load")
        self.assertEqual(result["gpus"][1]["free_bytes"], 101)
        self.assertEqual(result["gpus"][1]["max_memory_reserved"], 41)

    def test_runbook_ten_python_cells_compile(self):
        import re
        text = (smoke.ROOT / "notes/w2_qwen_kaggle_smoke_runbook.md").read_text(encoding="utf-8")
        cells = re.findall(r"```python\n(.*?)```", text, re.DOTALL)
        self.assertEqual(len(cells), 10)
        for code in cells:
            ast.parse(code)

    def test_invalid_run_id(self):
        with self.assertRaises(ValueError):
            smoke.run_smoke("../escape", repo=self.repo)

    def test_protected_configs_pending(self):
        for name in ("local_models.d9.json", "freeze_manifest.d9.template.json"):
            data = json.loads((smoke.ROOT / "configs/pre_freeze" / name).read_text())
            self.assertEqual(data["protocol_freeze_commit_sha"], "PENDING")

    def test_artifacts_ignored(self):
        import subprocess
        result = subprocess.run(["git", "check-ignore", "--stdin"], cwd=smoke.ROOT,
                                input=smoke.ARTIFACTS + "/test/runtime_report.json\n"
                                + "data/processed/hf-cache/model.safetensors\n",
                                capture_output=True, text=True, check=True)
        self.assertEqual(len(result.stdout.splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
