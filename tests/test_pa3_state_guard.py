"""Synthetic CPU fault injection; no torch, model weights, GPU or dataset."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from safeshift.pa3.native import native_audit, state_guard, workflow
from safeshift.pa3.native.journal import Journal, run_path
from safeshift.pa3.artifacts import json_bytes, receipt
from tests import test_pa3_native as cpu
from tests.test_pa3_full_train import running_fixture


class StateTensor:
    device, dtype = "cuda:0", "fp16"  # API double, storage is exclusively numpy/CPU

    def __init__(self, data):
        self.data = np.asarray(data, dtype=np.float16)

    @property
    def shape(self): return self.data.shape
    def is_contiguous(self): return self.data.flags.c_contiguous
    def detach(self): return self
    def cpu(self): return self
    def numel(self): return self.data.size
    def __getitem__(self, key): return StateTensor(self.data[key])
    def numpy(self): return self.data
    def view(self, kind):
        out = StateTensor([])
        out.data = self.data.reshape(-1) if kind == -1 else self.data.view(kind)
        return out


class StateTorch(cpu.Torch):
    uint8 = np.uint8
    cuda = SimpleNamespace(**vars(cpu.Torch.cuda), synchronize=lambda: None)
    is_tensor = staticmethod(lambda value: isinstance(value, StateTensor))
    isfinite = staticmethod(lambda value: np.isfinite(value.data))


def state_model():
    # State API independent of generation instrumentation (calls/text).
    module = SimpleNamespace(training=False, weight=StateTensor([1., 2.]),
                             buffer=StateTensor([3.]), scalar=4)
    config = cpu.Config(_attn_implementation="sdpa", cache_implementation=None)
    model = SimpleNamespace(rope_deltas=None, _cache=None, config=config,
        generation_config=cpu.Config(do_sample=False), model=SimpleNamespace())
    model.named_parameters = lambda: [("weight", module.weight)]
    model.named_buffers = lambda: [("nonpersistent", module.buffer)]
    model.named_modules = lambda: [("", module)]
    return model, module


class GuardTests(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, module = state_model()
            scorer = SimpleNamespace(model=model, torch=StateTorch, failed=False,
                validator=lambda: None, config=cpu.Config(do_sample=False), condition={"decoding": {}})
            journal = Journal(Path(tmp)/"run", create=True)
            guard = state_guard.StateGuard(scorer, journal)
            self.assertEqual(guard.baseline["status"], "RECORDED")
            yield guard, scorer, module, journal

    def test_matching_finite_state_discards_only_transient_cache(self):
        with self.fixture() as (guard, scorer, module, journal):
            before = module.weight.data.copy()
            scorer.model.rope_deltas = StateTensor([float("nan")])
            scorer.model._cache = object()
            self.assertTrue(guard.after_nonfinite({"sample_id": "s0"}, "sample-000000"))
            self.assertFalse(scorer.failed)
            self.assertIsNone(scorer.model.rope_deltas)
            self.assertIsNone(scorer.model._cache)
            np.testing.assert_array_equal(module.weight.data, before)
            self.assertTrue(state_guard.permits(guard.baseline, journal.read("sample-000000.state"), "s0"))

    def test_parameter_buffer_unregistered_tensor_and_scalar_mutations_block(self):
        for kind in ("weight", "buffer", "attribute", "scalar", "config", "nan", "inf", "opaque", "training"):
            with self.subTest(kind=kind), self.fixture() as (guard, scorer, module, journal):
                if kind in ("weight", "buffer"):
                    getattr(module, kind).data[0] += 1
                elif kind == "attribute": module.other_tensor = StateTensor([5.])
                elif kind == "scalar": module.scalar += 1
                elif kind == "config": scorer.config.do_sample = True
                elif kind == "opaque": module.hook = object()
                elif kind == "training": module.training = True
                else: module.weight.data[0] = float(kind)
                self.assertFalse(guard.after_nonfinite({"sample_id": "s0"}, "sample-000000"))
                self.assertTrue(scorer.failed)
                self.assertEqual(journal.read("sample-000000.state")["status"], "BLOCKED")

    def test_sync_validator_terminal_missing_baseline_and_write_errors_block(self):
        for kind in ("sync", "validator", "terminal", "baseline", "write", "interrupt"):
            with self.subTest(kind=kind), self.fixture() as (guard, scorer, _, journal):
                if kind == "terminal": scorer.failed = True
                if kind == "baseline": guard.baseline["status"] = "UNAVAILABLE"
                def fail(): raise RuntimeError("SYNTHETIC_FAULT")
                if kind == "validator": scorer.validator = fail
                if kind in ("sync", "interrupt"):
                    def sync():
                        if kind == "interrupt": raise KeyboardInterrupt()
                        fail()
                    scorer.torch = SimpleNamespace(cuda=SimpleNamespace(synchronize=sync))
                if kind == "write":
                    with patch.object(journal, "write", side_effect=OSError("disk")), self.assertRaises(OSError):
                        guard.after_nonfinite({"sample_id": "s0"}, "sample-000000")
                elif kind == "interrupt":
                    with self.assertRaises(KeyboardInterrupt):
                        guard.after_nonfinite({"sample_id": "s0"}, "sample-000000")
                else:
                    self.assertFalse(guard.after_nonfinite({"sample_id": "s0"}, "sample-000000"))
                self.assertTrue(scorer.failed)

    def test_nonfinite_initial_weights_stop_before_any_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, module = state_model()
            module.weight.data[0] = float("nan")
            scorer = SimpleNamespace(model=model, torch=StateTorch, failed=False, validator=lambda: None)
            j = Journal(Path(tmp)/"run", create=True)
            with self.assertRaisesRegex(ValueError, "MODEL_STATE_BASELINE_FAILED"):
                state_guard.StateGuard(scorer, j)
            self.assertTrue(scorer.failed)
            self.assertEqual(j.read("state-baseline")["status"], "UNAVAILABLE")

    def test_partial_or_forged_proof_not_permitted(self):
        with self.fixture() as (guard, _, _, journal):
            guard.after_nonfinite({"sample_id": "s0"}, "sample-000000")
            proof = journal.read("sample-000000.state")
            for change in ({"sample_id": "other"}, {"cache_cleared": 1}, {"after": None},
                           {"status": "BLOCKED"}, {"reason": "uncertain"}, {"extra": True}):
                self.assertFalse(state_guard.permits(guard.baseline, {**proof, **change}, "s0"))

    def test_unknown_native_attribute_cannot_create_a_healthy_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            model, module = state_model()
            module.rope_init_fn = lambda: None  # real native callable needs separate review
            scorer = SimpleNamespace(model=model, torch=StateTorch, failed=False, validator=lambda: None)
            j = Journal(Path(tmp)/"run", create=True)
            guard = state_guard.StateGuard(scorer, j)
            self.assertEqual(guard.baseline["status"], "UNAVAILABLE")
            self.assertIn("UNREVIEWED_PERSISTENT_ATTRIBUTE", guard.baseline["reason"])
            self.assertFalse(guard.after_nonfinite({"sample_id": "s0"}, "sample-000000"))

    def test_tampered_baseline_cannot_authorize_next_image(self):
        with self.fixture() as (guard, scorer, _, journal):
            p = journal.path("state-baseline")
            p.write_bytes(p.read_bytes() + b" ")
            self.assertFalse(guard.after_nonfinite({"sample_id": "s0"}, "sample-000000"))
            self.assertTrue(scorer.failed)


def inject_nan(model):
    original = model.generate
    def generate(**kwargs):
        output = original(**kwargs)
        if len(model.calls) == 1:
            for vector in output.logits:
                vector.data[0] = [float("nan")] * len(vector.data[0])
        return output
    model.generate = generate


class WorkflowGuardTests(unittest.TestCase):
    def test_safe_nan_continues_once_raw_retained_audit_and_exports_partial(self):
        # Real train workflow/guard/auditor, substitute only tensor snapshot IO
        # unavailable on the dependency-free native API double.
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, settings, inputs, model, _, _):
            inject_nan(model)
            state = {"sha256": "a"*64, "tensor_count": 2, "all_finite": True}
            with patch.object(state_guard, "snapshot", return_value=state), \
                 patch.object(cpu.Torch.cuda, "synchronize", create=True):
                with self.assertRaisesRegex(ValueError, "TRAIN_EXHAUSTED_WITH_TECHNICAL_ERRORS"):
                    workflow.execute(repo, settings, "fixture", inputs)
                root = run_path(repo, settings["run_id"])
                checked = native_audit.audit(root, repo, cpu.TOK)
                self.assertEqual([r["status"] for r in checked["results"]], ["TECHNICAL_ERROR", "SUCCESS"])
                self.assertEqual(len(model.calls), 2)
                self.assertFalse(checked["completed"])
                j = Journal(root)
                self.assertTrue(j.verify())
                self.assertFalse(j.exists("finish"))
                self.assertEqual(j.read("failure")["reason"], "TRAIN_EXHAUSTED_WITH_TECHNICAL_ERRORS")
                self.assertIsNone(j.read("sample-000000.result")["score"])
                self.assertEqual(j.read("sample-000000.raw")["steps"][0]["raw"]["nonfinite"]["nan"], 1000)
                report = Journal(root.parent/(root.name + "-report"))
                self.assertTrue(report.verify())
                metrics = json.loads((root.parent/(root.name + "-exports")/"metrics.json").read_bytes())
                self.assertFalse(metrics["completed"])
                self.assertEqual(metrics["overall"]["coverage"]["scored"], 1)
                self.assertEqual(metrics["overall"]["coverage"]["attempted"], 2)
                # Locally re-sealed tampering must not authorize an attempted tail.
                proof = j.read("sample-000000.state")
                proof["after"]["sha256"] = "b"*64
                data = json_bytes(proof)
                j.path("sample-000000.state").write_bytes(data)
                j.path("sample-000000.state").with_suffix(".sha256.json").write_bytes(json_bytes(receipt(data)))
                seal = json_bytes(j.inventory())
                j.path("seal").write_bytes(seal)
                j.path("seal").with_suffix(".sha256.json").write_bytes(json_bytes(receipt(seal)))
                with self.assertRaisesRegex(ValueError, "ATTEMPT_SEQUENCE_MISMATCH"):
                    native_audit.audit(root, repo, cpu.TOK)

    def test_unknown_or_corrupted_state_stops_with_tail_unattempted(self):
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as tmp, \
                 running_fixture(tmp) as (repo, settings, inputs, model, _, _):
                inject_nan(model)
                initial = {"sha256": "a"*64, "tensor_count": 2, "all_finite": True}
                effect = [initial, {**initial, "sha256": "b"*64}] if corrupt else AttributeError("unsupported introspection")
                with patch.object(state_guard, "snapshot", side_effect=effect), \
                     patch.object(cpu.Torch.cuda, "synchronize", create=True):
                    with self.assertRaisesRegex(ValueError, "RAW_SCORING_TECHNICAL_FAILURE"):
                        workflow.execute(repo, settings, "fixture", inputs)
                    j = Journal(run_path(repo, settings["run_id"]))
                    checked = native_audit.audit(j.root, repo, cpu.TOK)
                    self.assertEqual([r["status"] for r in checked["results"]], ["TECHNICAL_ERROR", "NOT_ATTEMPTED"])
                    self.assertEqual(len(model.calls), 1)
                    self.assertEqual(j.read("sample-000000.state")["status"], "BLOCKED")

    def test_default_workflow_still_stops_even_with_clean_state(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, cpu.backend() as (model, _):
            inject_nan(model)
            j, samples = cpu.JournalAuditTests().fixture(Path(tmp)/"run")
            with self.assertRaisesRegex(ValueError, "RAW_SCORING_TECHNICAL_FAILURE"):
                workflow.infer(j, samples, cpu.make_scorer(), cpu.TOK, lambda row: Image.new("RGB", (8, 8)))
            self.assertEqual(len(model.calls), 1)
            self.assertFalse(j.exists("sample-000001.attempt"))

    def test_generation_runtime_error_interrupt_and_other_scoring_error_never_recover(self):
        from PIL import Image
        for failure in (RuntimeError("CUDA OOM fixture"), KeyboardInterrupt(), "OTHER_TRACE_ERROR"):
            with self.subTest(failure=type(failure).__name__), tempfile.TemporaryDirectory() as tmp, \
                 cpu.backend() as (model, _):
                j, samples = cpu.JournalAuditTests().fixture(Path(tmp)/"run")
                guard = SimpleNamespace(after_nonfinite=Mock(side_effect=AssertionError("unexpected recovery")))
                original = workflow.score
                def score(*args):
                    result = original(*args)
                    result.update(status="TECHNICAL_ERROR", score=None, details=None, errors=["OTHER_TRACE_ERROR"])
                    return result
                if isinstance(failure, BaseException): model.failure = failure
                expected = type(failure) if isinstance(failure, BaseException) else ValueError
                with patch.object(workflow, "score", side_effect=score), self.assertRaises(expected):
                    workflow.infer(j, samples, cpu.make_scorer(), cpu.TOK,
                                   lambda row: Image.new("RGB", (8, 8)), state_guard=guard)
                self.assertEqual(len(model.calls), 1)
                guard.after_nonfinite.assert_not_called()
                self.assertFalse(j.exists("sample-000001.attempt"))


if __name__ == "__main__":
    unittest.main()
