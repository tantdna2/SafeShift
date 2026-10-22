"""CPU doubles/synthetic bytes only; no real images, model, CUDA or network."""
import ast
from contextlib import nullcontext, ExitStack
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

from safeshift.diagnostics.qwen3_recovery import (
    audit, backend, bootstrap as boot, budget, cohort, contract, engine,
    observe, observe_audit, orchestrate as flow, worker)
from safeshift.diagnostics.hnlo_train import cohort as original_cohort, inputs
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.pa3.native.journal import Journal
from safeshift.ls1.runtime import summarize_vector
from safeshift.ls1.tokenizer import probe
from tests.test_hnlo_train import fill, CONFIG, KWARGS, TOK, CANDIDATES, FakeBackend, source
from tests.test_hnlo_capture import output
from tests import test_hnlo_one_click as old

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = [{"sample_id": f"synthetic-{i}", "image_locator": f"DATA_PATH/train/Annotations/synthetic/{i}.jpg",
              "image_sha256": hashlib.sha256(f"synthetic-{i}".encode()).hexdigest()} for i in range(224)]


def approved():
    value = contract.template()
    value["grant"] = {"approved_by": "SYNTHETIC_TEST_ONLY", "role": "Research Lead", "approved_utc": "2026-10-22T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-decision",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64,
        "unit": contract.unit(), "approvals": {k: True for k in contract.FLAGS}}
    return value


def fake_torch():
    cuda = SimpleNamespace(device_count=lambda: 2, memory_allocated=lambda i: 100 + i,
        memory_reserved=lambda i: 200 + i, max_memory_allocated=lambda i: 300 + i,
        max_memory_reserved=lambda i: 400 + i, mem_get_info=lambda i: (500 + i, 1000 + i),
        memory_stats=lambda i: {"active_bytes.all.current": 75 + i, "num_ooms": i},
        get_allocator_backend=lambda: "SYNTHETIC_ALLOCATOR")
    return SimpleNamespace(cuda=cuda, inference_mode=nullcontext)


class CPUCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")))


class MappingAndAuthorityTests(CPUCase):
    def test_all_224_original_rows_and_both_pr123_hashes(self):
        rows, mapping = cohort.inference(ROOT)
        original = original_cohort.inference(ROOT)[2]
        self.assertEqual(rows, original[717:941])
        self.assertEqual([r["original_ordinal"] for r in mapping], list(range(717, 941)))
        self.assertEqual([r["recovery_ordinal"] for r in mapping], list(range(224)))
        self.assertEqual(cohort.canonical_digest(mapping), cohort.MAPPING_SHA)
        projection = cohort.opaque_rows(rows)
        self.assertEqual(cohort.canonical_digest(projection), cohort.WORKER_SHA)
        self.assertEqual(cohort.worker_rows(projection), projection)
        self.assertEqual(rows[0]["image_sha256"], "c82dd1b1c3386b67a0372c1b9ea98de68b60cdc586436dfecd3c4c061cc9e8f5")
        self.assertFalse({r["sample_id"] for r in original[:717]} & {r["sample_id"] for r in rows})
        self.assertNotIn("sample_id", json.dumps(projection))
        self.assertNotIn("Level", json.dumps(projection))

    def test_changed_order_count_hash_and_label_fields_fail_closed(self):
        rows, _ = cohort.inference(ROOT)
        for mutate in (lambda r: r.reverse(), lambda r: r.pop(),
                       lambda r: r[0].update(image_sha256="0" * 64),
                       lambda r: r[0].update(sample_id="FORBIDDEN")):
            projection = cohort.opaque_rows(rows)
            mutate(projection)
            with self.assertRaises(ValueError):
                cohort.worker_rows(projection)
        original = Path.read_bytes
        def tamper(path):
            blob = original(path)
            return blob + b" " if path.name == "pa3_full_train_shard2.v1.json" else blob
        with patch.object(Path, "read_bytes", tamper), self.assertRaisesRegex(ValueError, "ORIGINAL_SHARD_HASH"):
            cohort.inference(ROOT)

    def test_separate_null_grant_and_old_v4_authority_rejected(self):
        from safeshift.diagnostics.hnlo_train.contract import AUTHORITY as old_authority
        for value in (contract.template(), json.loads((ROOT / old_authority).read_bytes())):
            with self.assertRaises(PermissionError):
                contract.authorize(value, source())
        self.assertNotEqual(contract.unit()["run_id"], "hnlo-train-v4-qwen3-s2-a1")
        self.assertIsNone(json.loads((ROOT / contract.AUTHORITY).read_bytes())["grant"])

    def test_synthetic_grant_is_source_scoped_and_requires_every_flag(self):
        self.assertEqual(contract.authorize(approved(), source())["unit"], contract.unit())
        mutations = [lambda v: v["scope"].update(resume=True),
            lambda v: v["grant"].update(implementation_commit="d" * 40),
            lambda v: v["grant"].update(source_payload_sha256="d" * 64),
            lambda v: v["grant"]["unit"].update(run_id="hnlo-train-v4-qwen3-s2-a1"),
            lambda v: v["grant"].update(decision_url="https://github.com/tantdna2/SafeShift/pull/123#old"),
            lambda v: v["grant"].update(approved_utc="bad")]
        mutations += [lambda v, flag=flag: v["grant"]["approvals"].update({flag: False}) for flag in contract.FLAGS]
        for mutate in mutations:
            value = approved()
            mutate(value)
            with self.assertRaises(PermissionError):
                contract.authorize(value, source())

    def test_null_grant_blocks_before_any_input_provision_or_gpu(self):
        write(self.root / contract.AUTHORITY, contract.template())
        out = self.root / "out"
        out.mkdir()
        with patch.object(flow, "Operations", side_effect=AssertionError("OPERATIONS_FORBIDDEN")), \
             patch.object(flow.cohort, "inference", side_effect=AssertionError("DATA_FORBIDDEN")):
            result = flow.run(self.root, self.root / "blocked", out, source())
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["gpu_worker_started"])
        self.assertFalse(result["dataset_read"])
        self.assertEqual(result["coverage"]["status_counts"]["NOT_ATTEMPTED"], 224)
        self.assertEqual(len(list(out.glob("*.tar.gz"))), 1)
        self.assertEqual(len(list(out.glob("*.json"))), 5)
        self.assertFalse((out / "data/processed/qwen3_recovery_attempts").exists())

    def test_worker_rechecks_null_grant_before_input_or_environment(self):
        write(self.root / contract.AUTHORITY, contract.template())
        with patch.object(boot, "verify_topology", return_value=source()), \
             patch.object(worker, "verify_inputs", side_effect=AssertionError("INPUTS_FORBIDDEN")):
            result = worker.execute("inference", self.root, self.root / "worker", source(), "unused", self.root / "unused", self.root / "raw")
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["chain"][0]["type"], "PermissionError")


class StagingTests(CPUCase):
    def test_confirmed_kaggle_layout_and_all_224_hashes_before_gpu(self):
        mount = self.root / "input/datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train"
        for i, row in enumerate(SYNTHETIC):
            path = mount / row["image_locator"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"synthetic-{i}".encode())
        self.assertEqual(inputs.discover_train(self.root / "input"), mount)
        self.assertEqual(len(inputs.check_images(mount, SYNTHETIC)), 224)
        inputs.stage_images(mount, SYNTHETIC, self.root / "staged", self.root / "staging")
        self.assertTrue(Journal(self.root / "staging").verify())
        with patch.object(worker, "worker_rows", side_effect=lambda rows: cohort.validate_opaque(rows, 224)):
            self.assertEqual(len(worker.verify_inputs(self.root / "staged")), 224)
            (self.root / "staged/000223.image").write_bytes(b"BAD")
            with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                worker.verify_inputs(self.root / "staged")
        self.assertEqual(len(list((self.root / "staged").iterdir())), 225)

    def test_hash_mismatch_stops_staging_and_never_publishes_request(self):
        rows = deepcopy(SYNTHETIC[:3])
        for i, row in enumerate(rows):
            path = self.root / "dataset" / row["image_locator"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"synthetic-{i}".encode() if i != 1 else b"BAD")
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            inputs.stage_images(self.root / "dataset", rows, self.root / "staged", self.root / "staging")
        self.assertFalse((self.root / "staged/request.json").exists())
        self.assertFalse((self.root / "staged/000002.image").exists())
        self.assertTrue(Journal(self.root / "staging").verify())

    def test_observation_reserve_is_in_admission_and_rejects_insufficient_output(self):
        plan = budget.estimate(224, 1000)
        self.assertGreater(plan["files_per_sample_bound"], 400)
        self.assertLess(plan["output_required_bytes"], 18 * 2**30)
        with self.assertRaisesRegex(ValueError, "OUTPUT_FREE"):
            budget.admit(plan, output_free=1, scratch_free=100 * 2**30)


class ObservationTests(CPUCase):
    def test_both_gpus_peak_scope_and_unavailable_stats_are_not_zero(self):
        torch = fake_torch()
        values = observe.scalar_memory(torch)
        self.assertEqual(values["devices"]["0"]["allocated_bytes"], 100)
        self.assertEqual(values["devices"]["1"]["allocated_bytes"], 101)
        self.assertIsNone(values["devices"]["0"]["allocator_stats"]["num_alloc_retries"])
        torch.cuda.mem_get_info = lambda i: (_ for _ in ()).throw(RuntimeError("synthetic"))
        self.assertIsNone(observe.scalar_memory(torch)["devices"]["1"]["free_bytes"])
        self.assertEqual(values["peak_scope"], "LIFETIME_SINCE_PRE_LOAD_RESET")

    def test_original_oom_message_cause_stack_and_both_devices_survive_stats_error(self):
        class OutOfMemoryError(RuntimeError):
            pass
        observer = observe.Observer(self.root / "observations", fake_torch())
        observer.start_sample(0)
        observer.event("prefill_before")
        message = "CUDA out of memory. Tried to allocate 128.00 MiB. GPU 1 has 64.00 MiB free."
        try:
            try:
                raise ValueError("synthetic cause")
            except ValueError as cause:
                raise OutOfMemoryError(message) from cause
        except OutOfMemoryError as error:
            observer.failure(error)
        observer.finish_sample()
        observer.close()
        journal = Journal(self.root / "observations/sample-000000")
        record = journal.read("failure")
        self.assertTrue(journal.verify())
        self.assertEqual(record["error"]["stage"], "prefill_before")
        self.assertEqual(record["error"]["chain"][0]["message"], message)
        self.assertEqual([r["type"] for r in record["error"]["chain"]], ["OutOfMemoryError", "ValueError"])
        self.assertEqual(set(record["memory"]["devices"]), {"0", "1"})
        self.assertEqual(record["original_ordinal"], 717)
        self.assertNotIn("locals", json.dumps(record))

    def test_sensitive_messages_are_redacted_and_exception_not_retained(self):
        text = observe.safe_message("token=hf_fake123 /tmp/private/image.jpg C:\\private\\file.py")
        self.assertNotIn("hf_fake123", text)
        self.assertNotIn("private", text)
        self.assertLessEqual(len(observe.safe_message("x" * 9000)), 4096)

    def test_bound_stops_without_truncating_existing_events(self):
        observer = observe.Observer(self.root / "obs", fake_torch())
        observer.start_sample(0)
        with patch.object(observe, "MAX_EVENTS", 1):
            with self.assertRaisesRegex(OSError, "BUDGET_STOP") as caught:
                observer.event("extra")
            observer.failure(caught.exception)
        observer.finish_sample()
        observer.close()
        journal = Journal(self.root / "obs/sample-000000")
        self.assertEqual(set(journal.inventory()), {"event-000", "failure"})
        self.assertTrue(journal.verify())

    def test_failure_persistence_error_never_masks_original(self):
        observer = observe.Observer(self.root / "obs", fake_torch())
        original = RuntimeError("original")
        with patch.object(observer.journal, "write", side_effect=OSError("DISK_FULL")):
            observer.failure(original)
        self.assertEqual(str(original), "original")

    def test_unsealed_or_tampered_observations_cannot_pass_cpu_audit(self):
        observer = observe.Observer(self.root / "observations", fake_torch())
        observer.start_sample(0)
        index = Journal(self.root / "raw/index", create=True)
        index.write("sample-000000.attempt", cohort.opaque_rows(SYNTHETIC)[0])
        self.assertEqual(observe_audit.verify_observations(self.root, SYNTHETIC), "PARTIAL")
        observer.finish_sample()
        observer.close()
        self.assertEqual(observe_audit.verify_observations(self.root, SYNTHETIC), "PASS")
        path = self.root / "observations/sample-000000/event-000.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.assertEqual(observe_audit.verify_observations(self.root, SYNTHETIC), "PARTIAL")

    def test_wrong_observation_run_identity_is_rejected_even_with_valid_new_seal(self):
        observer = observe.Observer(self.root / "observations", fake_torch())
        observer.run.write("event-000", {"run_id": "old-v4", "attempt_id": cohort.NEW_ATTEMPT,
            "recovery_ordinal": None, "original_ordinal": None, "monotonic_ns": 1})
        observer.run.seal()
        with self.assertRaisesRegex(ValueError, "IDENTITY_CHANGED"):
            observe_audit.verify_observations(self.root, SYNTHETIC)


class LifecycleTests(CPUCase):
    def test_separate_cpu_evaluator_checks_full_binding_and_reports_supplemental_cohort(self):
        """Small synthetic universe; real authority/runtime/raw checks, no GT read."""
        from safeshift.protocol.classification_policy import load_policy, render_prompt
        from safeshift.diagnostics.hnlo_hf import CAPTURE_FLAGS, QWEN_SOURCES
        from safeshift.diagnostics.hnlo_train.capture import persist
        from safeshift.diagnostics.hnlo_train.backend import record_native_call
        planned = SYNTHETIC[:2]
        u = {**contract.unit(), "count": 2}  # test-only reduction, no real manifest mutation
        proof = {**source(), "github_pr": {}}
        policy = load_policy(ROOT, qwen3_runtime=True)["classification"]["qwen3"]
        build = json.loads((ROOT / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
        expected = {**policy["software_versions"], **build["qwen3_additional_pins"]}
        model_record = {"model": "qwen3", "policy": policy, "clamp": None, "tokenizer_t1": probe(TOK),
            "snapshot": {"model_id": u["id"], "revision": u["revision"]},
            "prompt": render_prompt("qwen3", repo=ROOT), "generation_config": CONFIG,
            "runtime": {"actual": expected, "expected": expected, "cuda": u["cuda"],
                        "visible_devices": u["cuda_visible_devices"]}}
        class Backend(FakeBackend):
            def __init__(self, index):
                super().__init__(index)
                index.write("model", model_record)
            def generate(self, row, cap):
                record_native_call(self.index, cap, set(self.calls))
                self.calls.append(row["ordinal"])
                kwargs = {**policy["decoding"], **CAPTURE_FLAGS}
                cap.write("runtime-t1", probe(TOK))
                cap.write("call", {"configuration": CONFIG, "kwargs": kwargs, "input_shapes": {"input_ids": [1, 3]}})
                cap.write("raw-provenance", {"processors": []})
                cap.write("stopping", {"max_length": 35, "eos_token_ids": [999]})
                persist(output('{"safety_level":"Level03"}', processed_delta=0), [11, 22, 33],
                    CANDIDATES, TOK, cap, CONFIG, kwargs, lambda t, c, token: summarize_vector(t.data[0], c, token))
            def close(self):
                self.index.write("native-counts", {"load_calls": 1, "generate_ordinals": self.calls})
        evidence = self.root / "evidence"
        write(evidence / "binding.json", {"unit": u, "source": proof, "authority": approved(),
            "samples": planned, "recovery_mapping": []})
        write(evidence / "inference/generation-sources.json", [{"path": "transformers/" + k, "sha256": v} for k, v in QWEN_SOURCES.items()])
        write(evidence / "inference/result.json", {"status": "RETURNED", "inference_complete": True})
        write(self.root / "authority.json", approved())
        observer = observe.Observer(evidence / "observations", fake_torch())
        engine.execute(evidence / "raw", cohort.opaque_rows(planned), 2, Backend, observer=observer)
        audit.seal_raw(evidence)
        metadata = {r["sample_id"]: {"level": "Level04", "domain": "synthetic", "group": str(i)} for i, r in enumerate(planned)}
        def gt_after_custody(repo):
            audit.verify_custody(evidence)
            return metadata
        with patch.object(audit, "unit", return_value=u), \
             patch.object(audit, "AUTHORITY", str(self.root / "authority.json")), \
             patch.object(cohort, "inference", return_value=(planned, [])), \
             patch.object(boot, "verify_topology", return_value=proof), \
             patch.object(audit, "load_metadata", side_effect=gt_after_custody):
            result = audit.evaluate(evidence, ROOT, TOK, source=proof)
        self.assertTrue(result["completed"])
        self.assertFalse(result["baseline_pooling_allowed"])
        self.assertEqual(result["cohort"], "SUPPLEMENTAL_RECOVERY_NOT_V4_BASELINE")
        self.assertEqual(result["scope"], "SUPPLEMENTAL_RECOVERY_TRAIN_DESCRIPTIVE")
        self.assertEqual(result["schema"], "qwen3-s2-recovery-metrics-v1")
        self.assertEqual(result["overall"]["coverage"]["status_counts"]["SUCCESS"], 2)

    def test_simulated_224_native_calls_raw_replay_seals_and_archive(self):
        class Backend(FakeBackend):
            def close(self):
                self.index.write("native-counts", {"load_calls": 1, "generate_ordinals": self.calls})
        raw = self.root / "evidence/raw"
        observations = observe.Observer(self.root / "evidence/observations", fake_torch())
        index = engine.execute(raw, cohort.opaque_rows(SYNTHETIC), 224, lambda j: Backend(j), observer=observations)
        self.assertTrue(index.verify())
        self.assertTrue(index.exists("finish"))
        self.assertEqual(index.read("native-counts")["generate_ordinals"], list(range(224)))
        rows, completed, integrity = audit.raw_rows(self.root / "evidence", SYNTHETIC, TOK)
        self.assertTrue(completed)
        self.assertEqual([r["status"] for r in rows], ["SUCCESS"] * 224)
        self.assertEqual(observe_audit.verify_observations(self.root / "evidence", SYNTHETIC), "PASS")
        audit.seal_raw(self.root / "evidence")
        self.assertTrue(audit.verify_custody(self.root / "evidence"))
        archive = flow.package(self.root / "evidence", self.root, "synthetic-224")
        self.assertTrue(archive.is_file())
        receipt = json.loads((self.root / "synthetic-224_sha256.json").read_bytes())
        self.assertEqual(receipt["sha256"], sha256(archive))
        self.assertEqual(receipt["status"], "EXPORT_VALID")
        with tarfile.open(archive) as stream:
            self.assertIn("evidence/observations/sample-000223/seal.json", stream.getnames())

    def test_first_image_oom_and_middle_technical_stop_preserve_exact_tail(self):
        for stop in (0, 2):
            root = self.root / str(stop)
            observations = observe.Observer(root / "observations", fake_torch())
            index = engine.execute(root / "raw", cohort.opaque_rows(SYNTHETIC), 224,
                                   lambda j: FakeBackend(j, failure=stop), observer=observations)
            self.assertTrue(index.verify())
            self.assertFalse(index.exists("finish"))
            self.assertEqual(index.read("failure")["ordinal"], stop)
            self.assertFalse(index.exists(f"sample-{stop+1:06d}.attempt"))
            rows, completed, _ = audit.raw_rows(root, SYNTHETIC, TOK)
            self.assertEqual([r["status"] for r in rows], ["SUCCESS"] * stop + ["TECHNICAL_ERROR"] + ["NOT_ATTEMPTED"] * (223 - stop))
            self.assertEqual(observe_audit.verify_observations(root, SYNTHETIC), "PASS")

    def test_load_failure_and_time_limit_never_retry_or_invent_completion(self):
        calls = []
        def fails(index):
            calls.append(1)
            raise RuntimeError("SYNTHETIC_LOAD_OOM")
        obs = observe.Observer(self.root / "obs", fake_torch())
        index = engine.execute(self.root / "raw", cohort.opaque_rows(SYNTHETIC), 224, fails, observer=obs)
        self.assertEqual(calls, [1])
        self.assertTrue(index.verify())
        self.assertIsNone(index.read("failure")["ordinal"])
        timed = engine.execute(self.root / "timed", cohort.opaque_rows(SYNTHETIC), 224,
            lambda j: FakeBackend(j), max_seconds=0)
        self.assertEqual(timed.read("failure")["type"], "TimeoutError")
        self.assertFalse(timed.exists("sample-000000.native-call"))

    def test_diagnostic_failure_after_raw_seal_remains_technical_and_stops_tail(self):
        class FailingObserver(observe.Observer):
            def event(self, stage, **details):
                if stage == "after_sealed_cpu_replay":
                    raise OSError("SYNTHETIC_DIAGNOSTIC_WRITE_FAILURE")
                return super().event(stage, **details)
        observer = FailingObserver(self.root / "observations", fake_torch())
        index = engine.execute(self.root / "raw", cohort.opaque_rows(SYNTHETIC), 224,
                               lambda j: FakeBackend(j), observer=observer)
        self.assertTrue(Journal(self.root / "raw/sample-000000").verify())
        rows, completed, _ = audit.raw_rows(self.root, SYNTHETIC, TOK)
        self.assertEqual(rows[0]["status"], "TECHNICAL_ERROR")
        self.assertIsNone(rows[0]["score"])
        self.assertEqual(rows[1]["status"], "NOT_ATTEMPTED")
        self.assertFalse(completed)
        self.assertEqual(index.read("failure")["type"], "OSError")

    def test_actual_adapter_preserves_inputs_config_capture_and_releases_output_with_hooks(self):
        from safeshift.diagnostics.hnlo_train.capture import persist
        from safeshift.diagnostics.hnlo_train.backend import record_native_call
        from safeshift.runners.qwen3_vl import Qwen3VLRunner
        class Tensor:
            shape, dtype, device = (1, 3), "SYNTHETIC_FP16", "cuda:0"
            def __getitem__(self, key):
                return self
            def tolist(self):
                return [11, 22, 33]
        class Module:
            def __init__(self, call):
                self.pre, self.post, self.call = [], [], call
            def register_forward_pre_hook(self, hook, **kwargs):
                self.pre.append(hook)
                return SimpleNamespace(remove=lambda: self.pre.remove(hook))
            def register_forward_hook(self, hook, **kwargs):
                self.post.append(hook)
                return SimpleNamespace(remove=lambda: self.post.remove(hook))
            def __call__(self, **kwargs):
                for hook in self.pre:
                    assert hook(self, (), kwargs) is None
                value = self.call()
                for hook in self.post:
                    assert hook(self, (), kwargs, value) is None
                return value
        class NativeOutput(SimpleNamespace):
            pass
        refs, seen = [], []
        inputs = {"input_ids": Tensor(), "image_grid_thw": Tensor()}
        vision = Module(lambda: None)
        def forward():
            vision()
            out = NativeOutput(**vars(output('{"safety_level":"Level03"}', processed_delta=0)))
            refs.append(weakref.ref(out))
            return out
        native = Module(forward)
        native.model = SimpleNamespace(visual=vision, rope_deltas=None)
        native.generation_config = SimpleNamespace(to_dict=lambda: deepcopy(CONFIG))
        native._cache = None
        data = b"SYNTHETIC_IMAGE_BYTES"
        staged = self.root / "staged"
        staged.mkdir()
        (staged / "000000.image").write_bytes(data)
        rows = [{"ordinal": 0, "image_sha256": hashlib.sha256(data).hexdigest()}]
        observer = observe.Observer(self.root / "observations", fake_torch())
        b = backend.Backend.__new__(backend.Backend)
        b.observer, b.inputs, b.model, b.torch = observer, staged, native, fake_torch()
        b.cap, b.calls, b.loads, b.stack = None, set(), 1, ExitStack()
        b.key, b.context, b.policy = "qwen3", object(), {"decoding": deepcopy(KWARGS)}
        b.tokenizer, b.t1, b.candidates, b.prompt = TOK, probe(TOK), CANDIDATES, "SYNTHETIC_PROMPT"
        def prepare(request, context):
            self.assertEqual(request.input_bytes, data)
            self.assertEqual(request.prompt, "SYNTHETIC_PROMPT")
            return SimpleNamespace(inputs=inputs)
        b.runner = SimpleNamespace(_clear_call_state=Qwen3VLRunner._clear_call_state, prepare_input=prepare)
        b.handles = observer.hooks(native)
        def generate(**kwargs):
            self.assertIs(kwargs["input_ids"], inputs["input_ids"])
            self.assertIs(kwargs["image_grid_thw"], inputs["image_grid_thw"])
            seen.append(kwargs["generation_config"].to_dict())
            self.assertEqual({k: v for k, v in kwargs.items() if k not in (*inputs, "generation_config")}, KWARGS)
            record_native_call(b.index, b.cap, b.calls)
            b.cap.write("raw-provenance", {"processors": []})
            b.cap.write("stopping", {"max_length": 35, "eos_token_ids": [999]})
            return native(**inputs)
        native.generate = generate
        def factory(index):
            b.index = index
            return b
        def save(out, ids, candidates, tok, cap, cfg, kwargs, torch):
            return persist(out, ids, candidates, tok, cap, cfg, kwargs,
                           lambda t, c, token: summarize_vector(t.data[0], c, token))
        with patch("safeshift.runners.qwen3_placement.require_loaded_state"), patch.object(backend, "persist_torch", save):
            index = engine.execute(self.root / "raw", rows, 1, factory, observer=observer)
        self.assertTrue(index.exists("finish"), index.read("failure") if index.exists("failure") else None)
        self.assertEqual(seen, [CONFIG])
        self.assertTrue(all(ref() is None for ref in refs))
        self.assertEqual(native.pre, [])
        self.assertEqual(vision.post, [])
        journal = Journal(self.root / "observations/sample-000000")
        stages = [journal.read(n)["stage"] for n in journal.inventory() if n.startswith("event-")]
        self.assertIn("vision_before", stages)
        self.assertIn("prefill_after", stages)
        self.assertIn("after_adapter_frame_return", stages)
        self.assertTrue(journal.verify())


class SupervisorTests(CPUCase):
    def test_authorized_synthetic_partial_export_order_and_second_click_does_not_retry(self):
        events = []
        class Ops(flow.Operations):
            def check_inputs(self, rows):
                events.append("metadata")
                return {"synthetic": True}
            def preflight(self):
                events.append("budget")
                return {"synthetic": True}
            def stage(self, rows):
                events.append("stage224")
            def software(self):
                events.append("software")
            def worker(self, mode):
                events.append(mode)
                if mode == "inference":
                    engine.execute(self.evidence / "raw", cohort.opaque_rows(SYNTHETIC), 224,
                                   lambda j: FakeBackend(j, failure=1))
                return {"status": "RETURNED"}
            def provision(self):
                events.append("checkpoint")
            def evaluate(self):
                events.append("cpu_audit")
                audit.verify_custody(self.evidence)
                rows, completed, _ = audit.raw_rows(self.evidence, SYNTHETIC, TOK)
                metadata = {r["sample_id"]: {"level": "Level04", "domain": "synthetic", "group": str(i)} for i, r in enumerate(SYNTHETIC)}
                result = audit.metrics(rows, metadata, completed)
                audit.export(self.evidence / "report", rows, metadata, result, {"results": rows})
                return result
        write(self.root / contract.AUTHORITY, approved())
        out = self.root / "out"
        out.mkdir()
        with patch.object(cohort, "inference", return_value=(SYNTHETIC, [])):
            result = flow.run(self.root, self.root / "work", out, source(), operations_factory=Ops)
            before = {p.name: p.read_bytes() for p in out.glob("*.json")}
            again = flow.run(self.root, self.root / "again", out, source(), operations_factory=Ops)
        self.assertEqual(events, ["metadata", "budget", "stage224", "software", "inspect", "checkpoint", "inference", "cpu_audit"])
        self.assertEqual(result["status"], "PARTIAL")
        self.assertEqual(again["status"], "BLOCKED")
        self.assertFalse(result["baseline_pooling_allowed"])
        counts = result["coverage"]["status_counts"]
        self.assertEqual((counts["SUCCESS"], counts["TECHNICAL_ERROR"], counts["NOT_ATTEMPTED"]), (1, 1, 222))
        for name, data in before.items():
            self.assertEqual((out / name).read_bytes(), data)
        self.assertEqual(len(list(out.glob("*.tar.gz"))), 2)
        stem = contract.unit()["run_id"]
        export = json.loads((out / (stem + "_export.json")).read_bytes())
        self.assertEqual(export["result_sha256"], sha256(out / (stem + "_result.json")))
        self.assertEqual(export["archive_sha256"], sha256(out / (stem + ".tar.gz")))

    def test_cuda_admission_failure_stops_before_checkpoint_and_inference(self):
        events = []
        class Ops(flow.Operations):
            def check_inputs(self, rows):
                return {}
            def preflight(self):
                return {}
            def stage(self, rows):
                events.append("stage224")
            def software(self):
                pass
            def worker(self, mode):
                events.append(mode)
                raise RuntimeError("SYNTHETIC_CUDA_ADMISSION_FAILURE")
            def provision(self):
                raise AssertionError("CHECKPOINT_FORBIDDEN")
        write(self.root / contract.AUTHORITY, approved())
        out = self.root / "out"
        out.mkdir()
        with patch.object(cohort, "inference", return_value=(SYNTHETIC, [])):
            result = flow.run(self.root, self.root / "work", out, source(), operations_factory=Ops)
        self.assertEqual(events, ["stage224", "inspect"])
        self.assertFalse(result["inference_started"])


class SourceTests(old.SourceTests):
    """Exercise real F1/F2/merge Git histories against this separate trust root."""
    def setUp(self):
        self.enterContext(patch.object(old, "boot", boot))
        self.enterContext(patch.object(old, "AUTHORITY", contract.AUTHORITY))
        self.enterContext(patch.object(old, "LOCK", contract.LOCK))
        original_write = old.write
        def recovery_write(path, value):
            if Path(path).as_posix().endswith(contract.LOCK):
                value = {**value, "schema": "qwen3-s2-recovery-source-v1"}
            return original_write(path, value)
        self.enterContext(patch.object(old, "write", recovery_write))
        super().setUp()
        self.payload = hashlib.sha256(boot.canonical(json.loads((self.repo / contract.LOCK).read_bytes()))).hexdigest()


class NotebookAndPreservationTests(CPUCase):
    def test_notebook_compiles_one_cell_payload_and_clean_outputs(self):
        notebook = json.loads((ROOT / contract.NOTEBOOK).read_bytes())
        code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(code), 1)
        source_code = "".join(code[0]["source"])
        compile(ast.parse(source_code), contract.NOTEBOOK, "exec")
        self.assertEqual(code[0]["outputs"], [])
        self.assertIsNone(code[0]["execution_count"])
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        payload = hashlib.sha256(boot.canonical(lock)).hexdigest()
        self.assertIn('PAYLOAD_SHA256 = "' + payload + '"', source_code)
        self.assertTrue(source_code.endswith("result = bootstrap()\n"))
        for row in lock["files"]:
            data = (ROOT / row["path"]).read_bytes()
            if row["path"] == contract.NOTEBOOK:
                data = boot.notebook_bytes(data)
            elif not b"\x00" in data:
                data = data.replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_bootstrap_unmerged_release_exports_all_receipts_without_data_gpu(self):
        with patch.object(boot, "api", return_value=[{"number": 999}]) as api:
            api.side_effect = [[{"number": 999}], {"merged_at": None}]
            result = boot.bootstrap(self.root)
        self.assertEqual(result["result"], "BLOCKED")
        self.assertEqual(result["planned"], 224)
        self.assertFalse(result["gpu_initialization_attempted"])
        self.assertEqual(len(list(self.root.glob("*.tar.gz"))), 1)
        self.assertEqual(len(list(self.root.glob("*.json"))), 5)

    def test_protected_v4_scientific_security_notebooks_authority_are_byte_identical(self):
        protected = ["safeshift/runners", "safeshift/ls1", "safeshift/pa3", "safeshift/protocol",
            "safeshift/diagnostics/hnlo_train", "safeshift/diagnostics/one_click", "prompts", "data/manifests",
            "DECISIONS.md", "configs/diagnostics/hnlo_train_authority.v4.json",
            "configs/diagnostics/hnlo_train_source.v4.json"]
        protected += [f"notebooks/SafeShift_HNLO_TRAIN_{m}_SHARD{s}_V4.ipynb" for m in ("qwen3", "internvl3") for s in range(4)]
        self.assertEqual(subprocess.check_output(["git", "-C", str(ROOT), "diff", contract.BASE_SHA, "--", *protected]), b"")

    def test_clean_import_has_no_ml_or_network(self):
        code = ("import sys\nfrom unittest.mock import patch\n"
                "with patch('socket.socket', side_effect=AssertionError('NETWORK_FORBIDDEN')):\n"
                " import safeshift.diagnostics.qwen3_recovery.worker\n"
                " import safeshift.diagnostics.qwen3_recovery.orchestrate\n"
                "assert not ({'torch','transformers','PIL'} & set(sys.modules))")
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True, capture_output=True)

    def test_worker_payload_verification_never_reads_gt_manifest_or_old_results(self):
        code = self.root / "code.py"
        code.write_bytes(b"# synthetic\n")
        gt = self.root / "data/manifests/labels.json"
        gt.parent.mkdir(parents=True)
        gt.write_bytes(b'{"synthetic":"FORBIDDEN_LABELS"}')
        lock = {"schema": "qwen3-s2-recovery-source-v1", "base_sha": contract.BASE_SHA,
            "files": [{"path": "code.py", "sha256": sha256(code)},
                      {"path": "data/manifests/labels.json", "sha256": sha256(gt)}]}
        write(self.root / contract.LOCK, lock)
        payload = hashlib.sha256(boot.canonical(lock)).hexdigest()
        names = ["code.py", "data/manifests/labels.json", contract.AUTHORITY, contract.LOCK]
        original = Path.read_bytes
        def no_gt(path):
            if path == gt:
                raise AssertionError("WORKER_GT_FILE_READ")
            return original(path)
        with patch.object(boot, "git", side_effect=lambda repo, *args: "\0".join(names) if args[0] == "ls-files" else ""), \
             patch.object(Path, "read_bytes", no_gt):
            boot.verify_payload(self.root, payload, worker=True)
            with self.assertRaisesRegex(AssertionError, "GT_FILE_READ"):
                boot.verify_payload(self.root, payload)

    def test_custody_failure_blocks_label_loading_before_recovery_evaluation(self):
        with patch.object(audit, "verify_custody", side_effect=ValueError("BAD_CUSTODY")), \
             patch.object(audit, "load_metadata", side_effect=AssertionError("GT_FORBIDDEN")):
            with self.assertRaisesRegex(ValueError, "BAD_CUSTODY"):
                audit.evaluate(self.root, ROOT, TOK)


if __name__ == "__main__":
    unittest.main()
