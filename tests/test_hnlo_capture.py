"""Synthetic CPU objects only: no ML imports, sockets, model load or inference."""

from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
import builtins
import json
import math
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.hnlo_capture import Capture, persist_hf, review_trace
from safeshift.diagnostics.hnlo_hf import (
    InternVL3Diagnostic, Qwen3Diagnostic, QWEN_SOURCES, verify_qwen_sources,
)
from safeshift.diagnostics.hnlo_moondream import HeadObserver, MoondreamDiagnostic, reconcile, verified_binding
from safeshift.ls1 import core, runtime
from safeshift.runners import qwen3_placement as placement
from safeshift.runners.qwen3_vl import Qwen3VLRunner, MODEL_ID, REVISION
from tests.test_ls1 import CharTokenizer, TEXT
from tests.test_qwen_runner import Runtime, context, request

TOK = CharTokenizer()
CANDIDATES = core.candidates(TOK, TEXT)["token_ids"]


class Tensor:
    dtype = "fake-float32"
    device = "cpu"

    def __init__(self, data):
        self.data = deepcopy(data)
        self.shape = (len(data), len(data[0])) if data and isinstance(data[0], list) else (len(data),)

    def __getitem__(self, index):
        return Tensor(self.data[index])

    def tolist(self):
        return deepcopy(self.data)

    def detach(self):
        return self

    def clone(self):
        return Tensor(self.data)


def metadata(model="qwen3"):
    identities = {"qwen3": (MODEL_ID, REVISION), "internvl3": runtime.MODELS["internvl3"]}
    model_id, revision = identities[model]
    return {"run_id": "hnlo-fake-cpu", "sample_id": "synthetic-only", "model_id": model_id,
            "revision": revision, "tokenizer_revision": revision,
            "tokenizer_files": [{"path": "tokenizer.json", "sha256": "f" * 64}],
            "software": {"kind": "FAKE_CPU_ONLY"}, "source_commit": "a" * 40,
            "sources": [{"path": "transformers/" + n, "sha256": h} for n, h in QWEN_SOURCES.items()],
            "command": "python -m unittest tests.test_hnlo_capture -v", "prompt": "fake prompt",
            "input_sha256": "b" * 64, "configuration": {"kind": "FAKE"}, "seed": None}


def output(text=TEXT, *, eos=999, processed_delta=0.25):
    ids = TOK.encode(text) + [eos]
    raw, processed = [], []
    for token in ids:
        values = [-10.0] * 1000
        values[token] = 10.0
        raw.append(Tensor([values]))
        processed.append(Tensor([[v + processed_delta for v in values]]))
    return SimpleNamespace(sequences=Tensor([[11, 22, 33] + ids]), logits=raw, scores=processed)


class CPUFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        for name in ("socket.socket.connect", "socket.create_connection"):
            guard = patch(name, side_effect=AssertionError("NETWORK_FORBIDDEN"))
            guard.start()
            self.addCleanup(guard.stop)
        original = builtins.__import__
        def restricted(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub"}:
                raise AssertionError("REAL_ML_IMPORT_FORBIDDEN")
            return original(name, *args, **kwargs)
        guard = patch("builtins.__import__", side_effect=restricted)
        guard.start()
        self.addCleanup(guard.stop)

    def capture(self, model="qwen3"):
        return Capture(self.repo, metadata(model))

    def persist(self, cap, native=None, tokenizer=TOK):
        return persist_hf(native or output(), [11, 22, 33], CANDIDATES, tokenizer, cap,
                          {"eos_token_id": 999}, {"do_sample": False})


class CaptureTests(CPUFixture):
    def test_raw_processed_different_and_cpu_replay(self):
        cap = self.capture()
        self.persist(cap)
        result = review_trace(cap, TOK)
        self.assertEqual(result["alignment"], "PASS")
        self.assertFalse(result["raw_and_processed_label_scores_equal"])
        self.assertEqual(len(result["raw_label_logits"]), 4)
        self.assertEqual(result["hnlo"], "N/A")
        self.assertFalse(result["hnlo_verified"])
        cap.journal.seal()
        self.assertTrue(cap.journal.verify())
        reopened = Capture.open(self.repo, metadata()["run_id"])
        self.assertEqual(review_trace(reopened, TOK), result)

    def test_decode_failure_preserves_every_tensor_before_decode(self):
        cap = self.capture()
        class Bad(CharTokenizer):
            def decode(inner, ids, **kwargs):
                self.assertTrue(cap.journal.exists("raw-000"))
                self.assertTrue(cap.journal.exists(f"processed-{len(output().scores)-1:03d}"))
                raise RuntimeError("DECODE_FAILED")
        with self.assertRaisesRegex(RuntimeError, "DECODE_FAILED"):
            self.persist(cap, tokenizer=Bad())
        self.assertTrue(cap.journal.exists("native"))
        self.assertFalse(cap.journal.exists("trace"))

    def test_missing_processed_preserves_raw_and_native(self):
        cap, native = self.capture(), output()
        native.scores = None
        with self.assertRaisesRegex(ValueError, "RAW_LOGITS_AND_PROCESSED"):
            self.persist(cap, native)
        self.assertTrue(cap.journal.exists("raw-000"))
        self.assertEqual(cap.journal.read("native")["processed_steps"], 0)

    def test_wrong_prefix_and_missing_step_preserve_all_available_tensors(self):
        for case in ("prefix", "steps"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                cap, native = Capture(Path(directory), metadata()), output()
                if case == "prefix":
                    native.sequences.data[0][0] = 7
                else:
                    native.logits.pop()
                with self.assertRaises(ValueError):
                    self.persist(cap, native)
                self.assertTrue(cap.journal.exists("processed-000"))

    def test_invalid_response_and_wrong_alignment_are_na(self):
        cap = self.capture()
        self.persist(cap, output("Level03"))
        result = review_trace(cap, TOK)
        self.assertEqual(result["alignment"], "FAIL")
        self.assertEqual(result["hnlo"], "N/A")
        self.assertIn("INVALID_RESPONSE", result["reason"])

    def test_nonfinite_original_values_are_retained_and_rejected(self):
        cap, native = self.capture(), output()
        native.logits[0].data[0][1] = math.nan
        self.persist(cap, native)
        self.assertTrue(math.isnan(cap.journal.read("raw-000")["values"][0][1]))
        self.assertEqual(review_trace(cap, TOK)["alignment"], "FAIL")

    def test_checksum_tamper_and_no_overwrite(self):
        cap = self.capture()
        self.persist(cap)
        with self.assertRaises(FileExistsError):
            cap.write("native", {})
        cap.journal.path("trace").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CHECKSUM_MISMATCH"):
            review_trace(cap, TOK)

    def test_provenance_relative_paths_and_new_run_required(self):
        doc = metadata()
        doc["sources"][0]["path"] = "C:/personal/source.py"
        with self.assertRaises(ValueError):
            Capture(self.repo, doc)
        self.capture()
        with self.assertRaises(FileExistsError):
            self.capture()

    def test_qwen_source_version_and_tamper_rejected(self):
        with self.assertRaisesRegex(ValueError, "4_57_1"):
            verify_qwen_sources(SimpleNamespace(__version__="4.52.4"))
        root = self.repo / "transformers"
        (root / "generation").mkdir(parents=True)
        (root / "generation/utils.py").write_text("wrong", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "SOURCE_MISMATCH"):
            verify_qwen_sources(SimpleNamespace(__version__="4.57.1", __file__=str(root / "__init__.py")))

    def qwen(self):
        backend = Runtime()
        backend.model.device, backend.model.dtype = "cuda:1", "torch.float16"
        backend.model.hf_device_map = deepcopy(placement.DEVICE_MAP)
        backend.model.config = SimpleNamespace(quantization_config=None, _attn_implementation="sdpa")
        backend.processor.tokenizer = TOK
        backend.model.generation_config.eos_token_id = 999
        software = {**backend.backend.software_versions, "transformers": "4.57.1"}
        backend.factory.return_value = replace(backend.backend, software_versions=software)
        ctx = context(source_kind="SYNTHETIC", precision="FP16", device=placement.device_contract(),
                      decoding={"do_sample": False, "max_new_tokens": 32}, software_versions=software)
        runner = Qwen3VLRunner(backend_factory=backend.factory)
        env = patch.dict(os.environ, {placement.ALLOCATOR_NAME: placement.ALLOCATOR_VALUE})
        env.start()
        self.addCleanup(env.stop)
        runner.initialize(ctx)
        runner.load(ctx)
        prepared = runner.prepare_input(request(), ctx)
        # Convert only injected CPU inputs to the richer fake tensor surface.
        prepared = replace(prepared, inputs={k: Tensor(v.tolist()) for k, v in prepared.inputs.items()})
        def generate(**kwargs):
            backend.model.calls.append(kwargs)
            self.assertTrue(backend.inference_active)
            self.assertIsNone(backend.model.model.rope_deltas)
            kwargs["generation_config"].temperature = 123
            return output()
        backend.model.generate = generate
        verifier = patch("safeshift.diagnostics.hnlo_hf.installed_qwen_sources", return_value=[])
        verifier.start()
        self.addCleanup(verifier.stop)
        return backend, runner, ctx, prepared

    def test_qwen_reuses_load_placement_prepare_and_changes_only_capture_flags(self):
        backend, runner, ctx, prepared = self.qwen()
        original = deepcopy(backend.model.generation_config.to_dict())
        cap = self.capture()
        diagnostic = Qwen3Diagnostic(runner, TOK)
        diagnostic.generate(prepared, ctx, cap)
        kwargs = backend.model.calls[0]
        for key in ("return_dict_in_generate", "output_logits", "output_scores"):
            self.assertIs(kwargs[key], True)
        self.assertEqual(kwargs["max_new_tokens"], 32)
        self.assertFalse(kwargs["do_sample"])
        self.assertEqual(backend.model.generation_config.to_dict(), original)
        self.assertEqual(backend.model_factory.from_pretrained.call_args.kwargs["device_map"], placement.DEVICE_MAP)
        self.assertEqual(len(backend.processor.calls), 1)
        self.assertEqual(review_trace(cap, TOK)["alignment"], "PASS")
        with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
            diagnostic.generate(prepared, ctx, cap)

    def test_qwen_decode_error_durable_failure_and_cache_cleanup(self):
        backend, runner, ctx, prepared = self.qwen()
        cap = self.capture()
        class Bad(CharTokenizer):
            def decode(self, ids, **kwargs):
                # Runtime T1 must pass first; only real continuation has EOS.
                if 999 in ids:
                    raise RuntimeError("DECODE_FAILED")
                return super().decode(ids, **kwargs)
        backend.processor.tokenizer = Bad()
        with self.assertRaisesRegex(RuntimeError, "DECODE_FAILED"):
            Qwen3Diagnostic(runner, TOK).generate(prepared, ctx, cap)
        self.assertTrue(cap.journal.exists("raw-000"))
        self.assertEqual(cap.journal.read("failure")["error_type"], "RuntimeError")
        self.assertIsNone(backend.model.model.rope_deltas)

    def intern(self):
        scorer = object.__new__(runtime.NativeScorer)
        scorer.model_key, scorer.failed = "internvl3", False
        scorer.tokenizer = TOK
        scorer.processor = SimpleNamespace(tokenizer=TOK)
        scorer.torch = SimpleNamespace(inference_mode=nullcontext)
        scorer.config = SimpleNamespace(to_dict=lambda: {"eos_token_id": 999, "num_beams": 1})
        scorer.condition = {"decoding": {"do_sample": False, "max_new_tokens": 32}}
        scorer.software, scorer.snapshot_receipt = {"kind": "FAKE"}, {"kind": "FAKE"}
        scorer.validator = lambda: None
        def prepare(image, prefix):
            self.assertEqual(prefix, ())
            return {"input_ids": Tensor([[11, 22, 33]])}
        scorer.prepare = prepare
        scorer.model = SimpleNamespace(generate=lambda **kwargs: output(), _cache=None)
        return scorer

    def test_intern_bypasses_generate_and_persists_before_capture_output_decode(self):
        scorer, cap = self.intern(), self.capture("internvl3")
        scorer.generate = lambda *a, **k: self.fail("NativeScorer.generate must never be called")
        InternVL3Diagnostic(scorer).generate(object(), cap)
        self.assertEqual(review_trace(cap, TOK)["alignment"], "PASS")
        self.assertEqual(cap.journal.read("trace")["forced_assistant_prefix_ids"], [])

    def test_intern_late_state_failure_keeps_trace_and_is_terminal(self):
        scorer, cap = self.intern(), self.capture("internvl3")
        calls = []
        def validator():
            calls.append(True)
            if len(calls) == 2:
                raise ValueError("STATE_DRIFT")
        scorer.validator = validator
        diagnostic = InternVL3Diagnostic(scorer)
        with self.assertRaisesRegex(ValueError, "STATE_DRIFT"):
            diagnostic.generate(object(), cap)
        self.assertTrue(cap.journal.exists("trace"))
        self.assertTrue(scorer.failed)
        with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
            diagnostic.generate(object(), cap)

    def test_intern_processor_tokenizer_mismatch_stops_before_generate(self):
        scorer, cap = self.intern(), self.capture("internvl3")
        class Shifted(CharTokenizer):
            def encode(self, text, **kwargs):
                return [i + 10 for i in super().encode(text)]
            def decode(self, ids, **kwargs):
                return super().decode([i-10 for i in ids], **kwargs)
        scorer.processor.tokenizer = Shifted()
        with self.assertRaisesRegex(ValueError, "T1_MISMATCH"):
            InternVL3Diagnostic(scorer).generate(object(), cap)
        self.assertFalse(cap.journal.exists("native"))

    def test_intern_decode_failure_keeps_native_vectors_and_failure(self):
        scorer, cap = self.intern(), self.capture("internvl3")
        class Bad(CharTokenizer):
            def decode(self, ids, **kwargs):
                if 999 in ids:
                    raise RuntimeError("DECODE_FAILED")
                return super().decode(ids, **kwargs)
        scorer.tokenizer = scorer.processor.tokenizer = Bad()
        with self.assertRaisesRegex(RuntimeError, "DECODE_FAILED"):
            InternVL3Diagnostic(scorer).generate(object(), cap)
        self.assertTrue(cap.journal.exists("native"))
        self.assertTrue(cap.journal.exists("raw-000"))
        self.assertTrue(cap.journal.exists("failure"))

    def test_original_vector_is_used_by_cpu_reviewer(self):
        cap = self.capture()
        self.persist(cap)
        with patch("safeshift.diagnostics.hnlo_capture.summarize_vector", return_value={}):
            self.assertIn("VECTOR_TRACE_MISMATCH", review_trace(cap, TOK)["reason"])


class Head:
    def __init__(self):
        self._forward_hooks = {}
        self.returns = []

    def register_forward_hook(self, hook):
        self._forward_hooks[0] = hook
        return SimpleNamespace(remove=lambda: self._forward_hooks.pop(0))

    def __call__(self, values):
        tensor = Tensor([values])
        for hook in list(self._forward_hooks.values()):
            self.returns.append(hook(self, (), tensor))
        return tensor


class MoonTests(CPUFixture):
    def moon(self, *, wrong_order=False, wrong_position=False, extra=False, fail=False):
        cap, head = self.capture(), Head()
        events = []
        observer = HeadObserver(head, cap, lambda: deepcopy(events[-1]))
        ids = TOK.encode(TEXT) + [999]
        if extra:
            ids.append(88)
        with observer.installed():
            for i, token in enumerate(ids):
                events.append({"phase": "prefill" if i == 0 else "decode", "position": 100 + i})
                if i == 0:
                    events[-1]["input_ids"] = [11, 22, 33]
                if wrong_order and i == 1:
                    events[-1]["phase"] = "prefill"
                if wrong_position and i == 1:
                    events[-1]["position"] += 1
                values = [-10.0] * 1000
                values[token] = 10.0
                if i:
                    values[3] = 100.0  # raw argmax differs from post-mask selection
                tensor = head(values)
                self.assertTrue(cap.journal.exists(f"raw-{i:03d}"))
                if i:
                    tensor.data[0][3] = -math.inf  # native in-place mask
                if fail and i == 1:
                    raise RuntimeError("NATIVE_FAILURE")
        self.assertEqual(head._forward_hooks, {})
        self.assertTrue(all(x is None for x in head.returns))
        return cap, head, observer

    def test_moon_clone_before_inplace_mask_and_separate_postmask(self):
        cap, head, observer = self.moon()
        self.assertEqual(cap.journal.read("raw-001")["values"][0][3], 100)
        self.assertEqual(cap.journal.read("processed-001")["values"][0][3], -math.inf)
        reconcile(observer, {"answer": TEXT}, TOK, CANDIDATES, eos_id=999)
        result = review_trace(cap, TOK)
        self.assertEqual(result["alignment"], "PASS")
        self.assertEqual(result["hnlo"], "N/A")

    def test_moon_native_failure_removes_hook_and_retains_partial(self):
        with self.assertRaisesRegex(RuntimeError, "NATIVE_FAILURE"):
            self.moon(fail=True)
        from safeshift.pa3.native.journal import Journal
        journal = Journal(self.repo / "data/processed/hnlo_capture/hnlo-fake-cpu")
        self.assertTrue(journal.read("hook-summary")["removed"])
        self.assertEqual(journal.read("hook-summary")["calls"], 2)
        self.assertEqual(journal.read("raw-001")["values"][0][3], 100)

    def test_moon_wrong_order_is_not_reconciled(self):
        cap, _, observer = self.moon(wrong_order=True)
        with self.assertRaisesRegex(ValueError, "ORDER_OR_POSITION"):
            reconcile(observer, {"answer": TEXT}, TOK, CANDIDATES, eos_id=999)
        self.assertFalse(cap.journal.exists("trace"))

    def test_moon_wrong_position_is_not_reconciled(self):
        _, _, observer = self.moon(wrong_position=True)
        with self.assertRaisesRegex(ValueError, "ORDER_OR_POSITION"):
            reconcile(observer, {"answer": TEXT}, TOK, CANDIDATES, eos_id=999)

    def test_moon_extra_call_or_missing_eos_not_trimmed(self):
        cap, _, observer = self.moon(extra=True)
        with self.assertRaisesRegex(ValueError, "EOS_OR_UNCONSUMED"):
            reconcile(observer, {"answer": TEXT}, TOK, CANDIDATES, eos_id=999)
        self.assertTrue(cap.journal.exists("inferred-ids"))

    def test_moon_native_answer_mismatch_keeps_inferred_status(self):
        cap, _, observer = self.moon()
        with self.assertRaisesRegex(ValueError, "NATIVE_ANSWER_MISMATCH"):
            reconcile(observer, {"answer": "different"}, TOK, CANDIDATES, eos_id=999)
        self.assertEqual(cap.journal.read("inferred-ids")["status"], "NOT_YET_RECONCILED")
        self.assertFalse(cap.journal.exists("trace"))

    def test_moon_identity_rejects_unknown_instance_before_hook(self):
        with self.assertRaises(AttributeError):
            verified_binding(SimpleNamespace())

    def test_moon_phase_error_always_removes_hook(self):
        cap, head = self.capture(), Head()
        def fail():
            raise ValueError("BAD_CALLER")
        observer = HeadObserver(head, cap, fail)
        with self.assertRaisesRegex(ValueError, "BAD_CALLER"), observer.installed():
            head([0.0] * 1000)
        self.assertFalse(head._forward_hooks)
        self.assertTrue(cap.journal.exists("raw-000"))
        self.assertTrue(cap.journal.exists("processed-000"))

    def test_moon_persistence_error_still_removes_hook(self):
        cap, head = self.capture(), Head()
        observer = HeadObserver(head, cap, lambda: {"phase": "prefill", "position": 10})
        original = cap.write
        def write(name, value):
            if name.startswith("raw-"):
                raise OSError("DISK_FAILURE")
            return original(name, value)
        with patch.object(cap, "write", side_effect=write):
            with self.assertRaisesRegex(OSError, "DISK_FAILURE"), observer.installed():
                head([0.0] * 1000)
        self.assertFalse(head._forward_hooks)

    def native_runner(self, *, fail=False, drift=False):
        from safeshift.runners.contracts import Task
        from safeshift.runners.moondream_snapshot import MODEL_ID as MOON_ID, REVISION as MOON_REV
        doc = metadata()
        doc.update(model_id=MOON_ID, revision=MOON_REV,
                   tokenizer_revision="35192e10a54e36eabe0a7cc57a2c1aab371cafc5")
        cap, head = Capture(self.repo, doc), Head()
        events, queries = [], []
        class NativeTokenizer:
            def encode(self, text, **kwargs):
                return SimpleNamespace(ids=TOK.encode(text))
            def decode(self, ids, skip_special_tokens=True):
                return TOK.decode([i for i in ids if i != 0 or not skip_special_tokens])
        def query(image, prompt, **kwargs):
            queries.append(kwargs)
            for i, token in enumerate(TOK.encode(TEXT) + [0]):
                events.append({"phase": "prefill" if i == 0 else "decode", "position": 100 + i})
                if i == 0:
                    events[-1]["input_ids"] = [11, 22, 33]
                values = [-10.0] * 1000
                values[token] = 10.0
                tensor = head(values)
                self.assertTrue(cap.journal.exists(f"raw-{i:03d}"))
                if i:
                    tensor.data[0][3] = -math.inf
                if fail and i == 1:
                    raise RuntimeError("NATIVE_FAILURE")
            return {"answer": TEXT}
        model = SimpleNamespace(query=query, model=SimpleNamespace(
            tokenizer=NativeTokenizer(), text=SimpleNamespace(blocks=[])))
        runner = SimpleNamespace(model=model, valid=True, _condition=lambda c: None, evidence={"kind": "FAKE"},
            backend=SimpleNamespace(torch=SimpleNamespace(inference_mode=nullcontext), software={"kind": "FAKE"}),
            binding=SimpleNamespace(installed=nullcontext))
        audit_calls = []
        def audit(*args):
            audit_calls.append(True)
            return [{"stable-layout": len(audit_calls) if drift else 1}]
        for name, value in (
            ("safeshift.diagnostics.hnlo_moondream.verified_binding", lambda r: (head, lambda: events[-1])),
            ("safeshift.runners.moondream2.audit_model_state", audit),
            ("safeshift.runners.moondream_snapshot.require_offline", lambda: None),
        ):
            guard = patch(name, side_effect=value)
            guard.start()
            self.addCleanup(guard.stop)
        return runner, cap, head, queries, (Task.CLASSIFICATION, object(), "unchanged prompt")

    def test_moon_one_native_query_no_control_generation(self):
        runner, cap, head, queries, prepared = self.native_runner()
        diagnostic = MoondreamDiagnostic(runner)
        diagnostic.generate(prepared, SimpleNamespace(source_kind="SYNTHETIC"), cap)
        self.assertEqual(len(queries), 1)
        self.assertFalse(queries[0]["reasoning"])
        self.assertFalse(queries[0]["stream"])
        self.assertFalse(head._forward_hooks)
        self.assertEqual(cap.journal.read("trace")["token_id_status"],
                         "INFERRED_MATCHES_NATIVE_ANSWER_AND_ENCODING")
        self.assertEqual(cap.journal.read("state-before"), cap.journal.read("state-after"))
        with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
            diagnostic.generate(prepared, SimpleNamespace(source_kind="SYNTHETIC"), cap)

    def test_moon_query_exception_retains_raw_and_audits_state(self):
        runner, cap, head, _, prepared = self.native_runner(fail=True)
        with self.assertRaisesRegex(RuntimeError, "NATIVE_FAILURE"):
            MoondreamDiagnostic(runner).generate(prepared, SimpleNamespace(source_kind="SYNTHETIC"), cap)
        self.assertFalse(head._forward_hooks)
        self.assertFalse(runner.valid)
        self.assertTrue(cap.journal.exists("state-after"))
        self.assertTrue(cap.journal.exists("raw-001"))
        self.assertTrue(cap.journal.exists("failure"))

    def test_moon_state_drift_retains_native_answer(self):
        runner, cap, head, _, prepared = self.native_runner(drift=True)
        with self.assertRaisesRegex(ValueError, "STABLE_MODEL_STATE_DRIFT"):
            MoondreamDiagnostic(runner).generate(prepared, SimpleNamespace(source_kind="SYNTHETIC"), cap)
        self.assertFalse(head._forward_hooks)
        self.assertTrue(cap.journal.exists("native-answer"))
        self.assertFalse(cap.journal.exists("trace"))


if __name__ == "__main__":
    unittest.main()
