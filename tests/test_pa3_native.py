"""CPU-only native API doubles; never imports real torch/Transformers or data."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import importlib.metadata
import json
import math
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.ls1 import runtime, tokenizer as token_module
from safeshift.protocol.classification_policy import load_policy, render_prompt
from safeshift.pa3.native import access, analysis, cohort, preflight, qwen, native_audit, workflow, kaggle
from safeshift.pa3.native.journal import Journal, run_path
from safeshift.pa3.native.native_score import score, pending
from safeshift.pa3.artifacts import json_bytes, receipt
from tests.test_ls1 import TOK, TEXT, fake_raw

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {"mode": "technical", "run_id": "pa3-qwen-unit", "source_commit": preflight.BASE_SHA}


class Tensor:
    def __init__(self, data, device="cuda:0", dtype="fp16"):
        self.data, self.device, self.dtype = deepcopy(data), device, dtype

    @property
    def shape(self):
        return (len(self.data), len(self.data[0])) if self.data and isinstance(self.data[0], list) else (len(self.data),)

    def __getitem__(self, key):
        return Tensor([self.data[i] for i in key] if isinstance(key, list) else self.data[key])

    def tolist(self):
        return deepcopy(self.data)

    def double(self):
        return self

    def item(self):
        return self.data

    def argmax(self):
        return Tensor(self.data.index(max(self.data)))

    def max(self):
        return Tensor(max(self.data))

    def sum(self):
        return Tensor(sum(self.data))


class Inputs(dict):
    def to(self, device):
        return self


class Processor:
    tokenizer = TOK
    image_processor = SimpleNamespace(min_pixels=200704, max_pixels=1003520)

    def apply_chat_template(self, messages, **kwargs):
        assert messages[0]["content"][1]["text"] == render_prompt("qwen2_5", repo=ROOT)
        assert kwargs == {"tokenize": False, "add_generation_prompt": True}
        return "<official-template>"

    def __call__(self, **kwargs):
        assert kwargs["videos"] is None and kwargs["return_tensors"] == "pt"
        return Inputs(input_ids=Tensor([[11, 22]]), attention_mask=Tensor([[1, 1]]),
                      pixel_values=Tensor([[0.25]]), image_grid_thw=Tensor([[1, 32, 32]]))


class Config(SimpleNamespace):
    def to_dict(self):
        return vars(self).copy()


class Model:
    device, dtype = "cuda:0", "fp16"
    hf_device_map = {"": "cuda:0"}
    config = SimpleNamespace(_attn_implementation="sdpa", cache_implementation=None)
    model = SimpleNamespace()
    rope_deltas = None

    def __init__(self, text=TEXT):
        self.text, self.calls, self.failure = text, [], None
        self.generation_config = Config(num_beams=1, num_return_sequences=1, cache_implementation=None,
                                       eos_token_id=999, do_sample=True)

    def parameters(self):
        return [Tensor([1.0])]

    def buffers(self):
        return []

    def eval(self):
        return self

    def generate(self, **kwargs):
        assert self.rope_deltas is None and getattr(self, "_cache", None) is None
        assert kwargs["output_logits"] and kwargs["output_scores"]
        assert kwargs["max_new_tokens"] == 32 and kwargs["do_sample"] is False
        self.calls.append(kwargs)
        if self.failure:
            raise self.failure
        self.rope_deltas, self._cache = "dirty", "dirty"
        ids = TOK.encode(self.text) + [999]
        vectors = []
        for i, token in enumerate(ids):
            vector = [-100.0] * 1000
            vector[token] = 20.0
            if i == token_module.probe(TOK)["checks"][0]["step"] and self.text == TEXT:
                for tid, value in zip([49, 50, 51, 52], [0., 1., 4., 0.]):
                    vector[tid] = value
            vectors.append(Tensor([vector]))
        return SimpleNamespace(sequences=Tensor([[11, 22] + ids]), logits=vectors, scores=deepcopy(vectors))


class Torch:
    float16 = "fp16"
    version = SimpleNamespace(cuda="12.4")
    cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 1,
        get_device_properties=lambda i: SimpleNamespace(name="Tesla T4", major=7, minor=5, total_memory=15*2**30))

    @staticmethod
    @contextmanager
    def inference_mode():
        yield

    @staticmethod
    def logsumexp(v, dim):
        m = max(v.data)
        return Tensor(m + math.log(sum(math.exp(x-m) for x in v.data)))

    @staticmethod
    def isnan(v):
        return Tensor([math.isnan(x) for x in v.data])

    @staticmethod
    def isposinf(v):
        return Tensor([x == math.inf for x in v.data])

    @staticmethod
    def isneginf(v):
        return Tensor([x == -math.inf for x in v.data])


@contextmanager
def backend(model=None):
    model = model or Model()
    loads = []
    def loader(path, **kwargs):
        loads.append(kwargs)
        return model, {"missing_keys": [], "unexpected_keys": [], "mismatched_keys": [], "error_msgs": []}
    processor = Processor()
    factory = SimpleNamespace(from_pretrained=lambda *a, **kw: processor)
    native = SimpleNamespace(process_vision_info=lambda messages: ([messages[0]["content"][0]["image"]], None),
                             model_factory=SimpleNamespace(from_pretrained=loader))
    with ExitStack() as stack:
        stack.enter_context(patch.object(access, "require"))  # CPU fixture only; production has no injected grant
        stack.enter_context(patch.object(runtime, "versions", return_value=token_module.plan("qwen2_5", ROOT)["software"]))
        stack.enter_context(patch.object(runtime, "verify_snapshot", return_value={"fixture": "CPU_ONLY"}))
        stack.enter_context(patch.object(runtime.platform, "system", return_value="Linux"))
        stack.enter_context(patch.object(runtime.platform, "machine", return_value="x86_64"))
        stack.enter_context(patch.dict(sys.modules, {"torch": Torch(), "transformers": SimpleNamespace(AutoProcessor=factory)}))
        stack.enter_context(patch("safeshift.runners.qwen2_5_vl._native_backend", return_value=native))
        yield model, loads


def make_scorer():
    return qwen.QwenRawScorer("fixture-not-a-snapshot", TOK, token_module.probe(TOK)["candidate_token_ids"], repo=ROOT, settings=SETTINGS)


def header(samples):
    return {"schema": "pa3-qwen-run-v1", "prompt": render_prompt("qwen2_5", repo=ROOT),
            "model": token_module.MODELS["qwen2_5"][0], "revision": token_module.MODELS["qwen2_5"][1],
            "source": {"source_commit": preflight.BASE_SHA, "files": {}}, "samples": samples}


def raw_fixture():
    raw = fake_raw()
    raw["generation_config"] = {"eos_token_id": 999}
    return raw


def meta_rows(n=8):
    return [{"sample_id": f"s{i}", "split": "TRAIN", "image_locator": f"fixtures/s{i}.png",
             "image_sha256": hashlib.sha256(str(i).encode()).hexdigest(),
             "level": "Level04" if i % 2 else "Level01", "domain": "domain-a", "point_id": f"p{i}",
             "exposure": "unseen", "exposure_source": "synthetic-ledger", "gt_source": "synthetic-gt",
             "metadata_source": "synthetic-fixture", "test_link": "none_verified"} for i in range(n)]


class QwenTests(unittest.TestCase):
    def test_actual_native_loader_prepare_generate_and_raw_before_parse(self):
        with tempfile.TemporaryDirectory() as tmp, backend() as (model, loads):
            journal = Journal(Path(tmp)/"run", create=True)
            scorer = make_scorer()
            self.assertEqual(loads[0]["revision"], token_module.MODELS["qwen2_5"][1])
            self.assertEqual(loads[0]["torch_dtype"], "fp16")
            self.assertEqual(loads[0]["attn_implementation"], "sdpa")
            self.assertTrue(loads[0]["local_files_only"])
            calls = []
            def observed(sample_id, raw, tok):
                self.assertEqual(journal.read("sample-000000.raw"), raw)
                calls.append(True)
                return score(sample_id, raw, tok)
            from PIL import Image
            with patch.object(workflow, "score", side_effect=observed), \
                 patch("safeshift.ls1.core.calibrate", side_effect=AssertionError("CALIBRATION")), \
                 patch("safeshift.ls1.experiment.reference_scores", side_effect=AssertionError("REFERENCES")):
                workflow.infer(journal, [{"sample_id": "s0"}], scorer, TOK, lambda r: Image.new("RGB", (8, 8)))
            self.assertTrue(calls)
            self.assertEqual(journal.read("sample-000000.result")["status"], "SUCCESS")
            scorer.generate(Image.new("RGB", (8, 8)), journal, "second")
            self.assertEqual(len(model.calls), 2)  # cache reset, no extra reference calls
            journal.seal()
            self.assertTrue(journal.verify())

    def test_runtime_error_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp, backend() as (model, _):
            journal = Journal(Path(tmp)/"run", create=True)
            scorer = make_scorer()
            model.failure = RuntimeError("synthetic failure")
            with self.assertRaises(RuntimeError):
                scorer.generate(object(), journal, "sample-000000")
            model.failure = None
            with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
                scorer.generate(object(), journal, "sample-000001")
            self.assertEqual(len(model.calls), 1)

    def test_bad_generation_alignment_keeps_native(self):
        with tempfile.TemporaryDirectory() as tmp, backend() as (model, _):
            journal = Journal(Path(tmp)/"run", create=True)
            scorer = make_scorer()
            original = model.generate
            def wrong(**kw):
                value = original(**kw)
                value.sequences.data[0][0] = 999
                return value
            model.generate = wrong
            with self.assertRaisesRegex(ValueError, "PREFIX_MISMATCH"):
                scorer.generate(object(), journal, "sample-000000")
            self.assertTrue(journal.exists("sample-000000.native"))
            self.assertFalse(journal.exists("sample-000000.raw"))

    def test_raw_processed_difference_is_audited_not_used_as_score(self):
        raw = raw_fixture()
        row = raw["steps"][token_module.probe(TOK)["checks"][0]["step"]]
        row["processed"]["candidate_values"]["52"] = -5
        before = score("s", raw, TOK)
        self.assertEqual(before["status"], "SUCCESS")
        self.assertFalse(before["details"]["raw_and_processed_label_scores_equal"])
        self.assertEqual(before["score"], score("s", raw_fixture(), TOK)["score"])
        row["processed"]["argmax_id"] = 52
        self.assertEqual(score("s", raw, TOK)["status"], "TECHNICAL_ERROR")

    def test_token_text_nonfinite_missing_alignment(self):
        for fault in ("text", "token", "nan", "missing", "forced"):
            raw = raw_fixture()
            if fault == "text": raw["decoded_text"] = raw["decoded_text"] + " "
            if fault == "token": raw["continuation_ids"][0] += 1
            if fault == "nan": raw["steps"][0]["raw"]["nonfinite"]["nan"] = 1
            if fault == "missing": raw["steps"].pop()
            if fault == "forced": raw["forced_assistant_prefix_ids"] = [1]
            with self.subTest(fault=fault):
                self.assertEqual(score("s", raw, TOK)["status"], "TECHNICAL_ERROR")


class PreflightTests(unittest.TestCase):
    def test_t1_pass_28_only_with_fixture_tokenizer(self):
        class SizedTokenizer(type(TOK)):
            def __len__(self):
                return 1000
        tok_fixture = SizedTokenizer()
        fake = SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a, **kw: tok_fixture))
        with patch.object(token_module, "verify_snapshot", return_value={"synthetic": True}), \
             patch.object(token_module, "versions", side_effect=lambda expected: expected), patch.dict(sys.modules, {"transformers": fake}):
            result, tok = preflight.tokenizer_check(ROOT, "fixture")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["checks"]), 28)
        self.assertIs(tok, tok_fixture)

    def test_t1_missing_dependency_blocked_wrong_tokenization_fail(self):
        with patch.object(token_module, "verify_snapshot", return_value={}):
            with patch.object(token_module, "versions", side_effect=importlib.metadata.PackageNotFoundError("fixture")):
                self.assertEqual(preflight.tokenizer_check(ROOT, "fixture")[0]["status"], "BLOCKED")
            with patch.object(token_module, "versions", side_effect=lambda expected: expected), \
                 patch.dict(sys.modules, {"transformers": SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a, **kw: TOK))}), \
                 patch.object(token_module, "probe", side_effect=ValueError("multi-token")):
                self.assertEqual(preflight.tokenizer_check(ROOT, "fixture")[0]["status"], "FAIL")

    def test_actual_missing_wrong_revision_hash_and_dependency(self):
        self.assertEqual(preflight.tokenizer_check(ROOT, None)[0]["status"], "BLOCKED")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(token_module.t1("qwen2_5", tmp)[0]["status"], "FAIL")
            path = Path(tmp)/token_module.MODELS["qwen2_5"][1]
            path.mkdir()
            (path/"chat_template.json").write_text("synthetic wrong bytes")
            self.assertEqual(token_module.t1("qwen2_5", path)[0]["status"], "FAIL")
        with patch.object(preflight, "versions", side_effect=importlib.metadata.PackageNotFoundError("torch")):
            with self.assertRaises(importlib.metadata.PackageNotFoundError):
                preflight.runtime(ROOT, "unread")

    def test_runtime_rejects_version_platform_and_extra_snapshot(self):
        with patch.object(preflight, "versions", return_value={}):
            with self.assertRaisesRegex(ValueError, "EXACT_RUNTIME"):
                preflight.runtime(ROOT, "unread")
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(preflight, "versions", side_effect=lambda v: v), \
             patch.object(preflight.platform, "system", return_value="Linux"), \
             patch.object(preflight.platform, "machine", return_value="x86_64"), \
             patch.object(preflight, "verify_snapshot", return_value={}):
            (Path(tmp)/"extra.py").write_text("fixture")
            with self.assertRaisesRegex(ValueError, "EXTRA_FILES"):
                preflight.runtime(ROOT, tmp)


class LockTests(unittest.TestCase):
    def test_all_rights_are_denied_regardless_of_receipt_or_env(self):
        with patch.dict(os.environ, {"PA3_APPROVED": "1", "PA3_GPU": "1"}):
            for operation in ("test", "train-dev", "train-holdout", "metadata", "images", "technical", "statistics"):
                with self.subTest(operation=operation), self.assertRaises(PermissionError):
                    access.require(operation, {"approved": True, "receipt_sha256": "a"*64})

    def test_direct_loaders_and_model_refuse_before_reads(self):
        class Trap:
            def __fspath__(self):
                raise AssertionError("PATH_READ")
        for mode in ("test", "train-dev", "train-holdout", "technical"):
            settings = {**SETTINGS, "mode": mode}
            for call in (lambda: cohort.load_plan(Trap(), settings),
                         lambda: cohort.open_image(Trap(), settings, {}),
                         lambda: cohort.evaluation_metadata(Trap(), settings, []),
                         lambda: qwen.QwenRawScorer(Trap(), None, [], repo=Trap(), settings=settings)):
                with self.assertRaises(PermissionError): call()

    def test_workflow_and_launcher_package_denial_without_input_read(self):
        for mode in ("test", "train-dev", "train-holdout", "technical"):
            for function in (workflow.execute, kaggle.launch):
                with tempfile.TemporaryDirectory() as tmp, patch.object(preflight, "source", side_effect=AssertionError("SOURCE_READ")):
                    with self.assertRaises(PermissionError):
                        if function is workflow.execute: function(tmp, {**SETTINGS, "mode": mode}, "unread")
                        else: function(tmp, "unread", {**SETTINGS, "mode": mode})
                    self.assertEqual(len(list((Path(tmp)/"data/processed/pa3_qwen").glob("*.tar.gz"))), 1)


class CohortTests(unittest.TestCase):
    def test_transitive_group_quarantine_observed_unknown_and_test(self):
        rows = meta_rows()
        rows[0]["exposure"] = "observed"
        rows[2]["test_link"] = "unknown"
        links = [{"a": "s0", "b": "s1", "kind": "scene", "review": "accepted", "evidence": "synthetic"},
                 {"a": "s1", "b": "s2", "kind": "sequence", "review": "accepted", "evidence": "synthetic"}]
        groups = cohort.candidate_groups(rows, links)
        joined = next(g for g in groups if "s0" in g["sample_ids"])
        self.assertEqual(joined["sample_ids"], ["s0", "s1", "s2"])
        self.assertEqual(joined["quarantine_reasons"], ["exposure_observed", "test_link_unknown"])
        allocation = cohort.candidate_allocation(groups, salt="fixture", dev_fraction=.5)
        self.assertEqual(allocation["assignment"][joined["group_id"]], "QUARANTINE")
        cohort.validate_overlay(rows, groups, allocation)

    def test_deterministic_allocation_and_exact_duplicate_normal_point(self):
        rows = meta_rows()
        rows[0]["image_sha256"] = rows[2]["image_sha256"]
        rows[1]["point_id"] = rows[3]["point_id"]
        groups = cohort.candidate_groups(rows, [])
        self.assertEqual(len(groups), 6)
        a = cohort.candidate_allocation(groups, salt="fixture", dev_fraction=.5)
        self.assertEqual(a, cohort.candidate_allocation(list(reversed(groups)), salt="fixture", dev_fraction=.5))
        cohort.validate_overlay(rows, groups, a)

    def test_manifest_gt_and_group_overlap_fail(self):
        for key, value in (("split", "TEST"), ("level", "Normal"), ("exposure", "approved"),
                           ("image_locator", "../secret"), ("gt_source", ""), ("image_sha256", "bad")):
            rows = meta_rows(); rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): cohort.validate_inventory(rows)
        rows = meta_rows(); rows.append(deepcopy(rows[0]))
        with self.assertRaises(ValueError): cohort.validate_inventory(rows)
        rows = meta_rows(); groups = cohort.candidate_groups(rows, [])
        a = cohort.candidate_allocation(groups, salt="fixture", dev_fraction=.5)
        with self.assertRaises(ValueError): cohort.validate_overlay(rows, groups+[groups[0]], a)

    def test_unresolved_link_quarantines_and_singletons_not_holdout(self):
        rows = meta_rows(2)
        link = {"a": "s0", "b": "s1", "kind": "near_duplicate", "review": "unresolved", "evidence": "candidate-only"}
        groups = cohort.candidate_groups(rows, [link])
        self.assertIn("unresolved_relation", groups[0]["quarantine_reasons"])
        groups = cohort.candidate_groups(rows, [])
        self.assertEqual(set(cohort.candidate_allocation(groups, salt="fixture", dev_fraction=.5)["assignment"].values()), {"QUARANTINE"})


class EvaluationTests(unittest.TestCase):
    def fixture(self):
        rows = [score("a", raw_fixture(), TOK), score("b", raw_fixture(), TOK), pending("c")]
        metadata = {"a": {"level": "Level01", "domain": "a", "group": "g1"},
                    "b": {"level": "Level04", "domain": "a", "group": "g2"},
                    "c": {"level": "Level03", "domain": "b", "group": "g3"}}
        return rows, metadata

    def test_coverage_pairs_na_controls_ovr_and_partial(self):
        rows, meta = self.fixture()
        out = analysis.report(rows, meta)
        self.assertEqual(out["overall"]["coverage"], 2/3)
        self.assertEqual(out["overall"]["auroc"]["value"], .5)
        self.assertEqual(out["overall"]["auroc"]["pair_denominator"], 1)
        self.assertIsNone(out["by_domain"]["b"]["auroc"]["value"])
        self.assertIsNone(out["four_class_macro_ovr"])
        self.assertIsNone(out["completion_bounds_not_ci"])
        self.assertEqual(out["controls_same_eligible_ids"]["constant"]["value"], .5)
        with self.assertRaises(ValueError): analysis.report(rows, meta, completed=True)

    def test_exact_join_missing_score_not_imputed_and_bounds(self):
        rows, meta = self.fixture()
        with self.assertRaises(ValueError): analysis.report(rows, {**meta, "extra": meta["a"]})
        rows[2].update(status="INVALID", attempted=True, persisted=True)
        out = analysis.report(rows, meta, completed=True)
        self.assertEqual(out["completion_bounds_not_ci"], [.25, .75])
        rows[2]["score"] = 0
        with self.assertRaises(ValueError): analysis.report(rows, meta)

    def test_group_bootstrap_reproducible_missing_draws_and_authority(self):
        rows, meta = self.fixture()
        args = dict(draws=100, seed=19, confidence=.95)
        out = analysis.grouped_bootstrap(rows, meta, **args)
        self.assertEqual(out, analysis.grouped_bootstrap(rows, meta, **args))
        self.assertGreater(out["invalid_draws"], 0)
        self.assertEqual(out["percentile_interval"], [.5, .5])
        self.assertEqual(out["paired_raw_minus_generated_interval"], [0, 0])
        with self.assertRaises(PermissionError): analysis.grouped_bootstrap(rows, meta, confirmatory=True, **args)

    def test_mixed_domain_group_never_split(self):
        rows, meta = self.fixture()
        meta["b"].update(domain="other", group="g1")
        out = analysis.grouped_bootstrap(rows[:2], {k:v for k,v in meta.items() if k != "c"}, draws=10, seed=1, confidence=.9)
        self.assertEqual(out["valid_draws"], 10)
        self.assertEqual(out["group_count"], 1)


class JournalAuditTests(unittest.TestCase):
    def fixture(self, root):
        journal = Journal(root, create=True)
        samples = [{"sample_id": "s0"}, {"sample_id": "s1"}]
        journal.write("manifest", header(samples))
        journal.write("t1", {"status": "PASS", **token_module.probe(TOK)})
        scorer = make_scorer()
        journal.write("model", scorer.evidence())
        journal.write("runtime", {"software": scorer.software, "snapshot": scorer.snapshot_receipt})
        return journal, samples

    def test_roundtrip_audit_raw_reread_no_calibration(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, backend():
            j, samples = self.fixture(Path(tmp)/"run")
            workflow.infer(j, samples, make_scorer(), TOK, lambda r: Image.new("RGB", (8,8)))
            j.write("finish", {"status": "FINISHED", "planned": 2}); j.seal()
            with patch.object(preflight, "source", return_value=header(samples)["source"]):
                out = native_audit.audit(j.root, ROOT, TOK)
            self.assertTrue(out["completed"])
            self.assertEqual([r["status"] for r in out["results"]], ["SUCCESS", "SUCCESS"])
            self.assertTrue(j.package().exists())
            with self.assertRaises(ValueError): j.write("extra", {})

    def test_interrupt_after_raw_keeps_partial_and_remaining(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, backend():
            j, samples = self.fixture(Path(tmp)/"run")
            with patch.object(workflow, "score", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    workflow.infer(j, samples, make_scorer(), TOK, lambda r: Image.new("RGB", (8,8)))
            j.write("failure", {"exception_type": "KeyboardInterrupt", "retry_permitted": False}); j.seal()
            with patch.object(preflight, "source", return_value=header(samples)["source"]):
                out = native_audit.audit(j.root, ROOT, TOK)
            self.assertFalse(out["completed"])
            self.assertEqual([r["status"] for r in out["results"]], ["INTERRUPTED", "NOT_ATTEMPTED"])
            self.assertTrue(out["results"][0]["persisted"])

    def test_checksum_torn_and_inventory_corruption(self):
        for fault in ("bytes", "torn", "extra"):
            with tempfile.TemporaryDirectory() as tmp:
                j = Journal(Path(tmp)/"run", create=True); j.write("raw", {"a": 1}); j.seal()
                if fault == "bytes": j.path("raw").write_bytes(b"{}")
                if fault == "torn": j.path("raw").with_suffix(".sha256.json").unlink()
                if fault == "extra": (j.root/"unexpected").write_text("fixture")
                with self.subTest(fault=fault), self.assertRaises((ValueError, FileNotFoundError)): j.verify()

    def test_notebook_compiles_is_offline_and_no_output(self):
        nb = json.loads((ROOT/"notebooks/pa3_qwen2_5_kaggle.ipynb").read_text(encoding="utf8"))
        self.assertFalse(nb["metadata"]["kaggle"]["isInternetEnabled"])
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                compile("".join(cell["source"]), "notebook", "exec")

    def test_resealed_result_tamper_is_recomputed_and_source_drift_fails(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, backend():
            j, samples = self.fixture(Path(tmp)/"run")
            workflow.infer(j, samples, make_scorer(), TOK, lambda r: Image.new("RGB", (8,8)))
            j.write("finish", {"status": "FINISHED", "planned": 2}); j.seal()
            with patch.object(preflight, "source", return_value={"source_commit": "b"*40}):
                with self.assertRaisesRegex(ValueError, "SOURCE_PROVENANCE"):
                    native_audit.audit(j.root, ROOT, TOK)
            altered = j.read("sample-000000.result"); altered["score"] += 1
            raw = json_bytes(altered)
            j.path("sample-000000.result").write_bytes(raw)
            j.path("sample-000000.result").with_suffix(".sha256.json").write_bytes(json_bytes(receipt(raw)))
            seal = j.read("seal"); seal["sample-000000.result"] = receipt(raw)
            data = json_bytes(seal); j.path("seal").write_bytes(data)
            j.path("seal").with_suffix(".sha256.json").write_bytes(json_bytes(receipt(data)))
            self.assertTrue(j.verify())
            with patch.object(preflight, "source", return_value=header(samples)["source"]):
                with self.assertRaisesRegex(ValueError, "RECOMPUTATION"):
                    native_audit.audit(j.root, ROOT, TOK)

    def test_unsealed_journal_and_raw_without_result_remain_partial(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, backend():
            j, samples = self.fixture(Path(tmp)/"run")
            j.write("sample-000000.attempt", samples[0])
            make_scorer().generate(Image.new("RGB", (8,8)), j, "sample-000000")
            with patch.object(preflight, "source", return_value=header(samples)["source"]):
                out = native_audit.audit(j.root, ROOT, TOK)
            self.assertFalse(out["sealed"])
            self.assertEqual(out["results"][0]["status"], "UNPROCESSED")


class WorkflowTests(unittest.TestCase):
    def prepare_repo(self, tmp):
        repo = Path(tmp)
        for name in ("configs/pre_freeze/production_classification_policy.d9r23.v1.json",
                     "configs/pre_freeze/qwen2_5_t4_runtime.v1.json", "prompts/p2_classification_c1_v1.txt"):
            target = repo/name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/name, target)
        return repo

    @contextmanager
    def prerequisites(self, model=None):
        with backend(model), ExitStack() as stack:
            stack.enter_context(patch.object(preflight, "source", return_value=header([])["source"]))
            stack.enter_context(patch.object(preflight, "runtime", return_value={"snapshot": {"fixture": "CPU_ONLY"},
                                                                                  "software": token_module.plan("qwen2_5", ROOT)["software"]}))
            stack.enter_context(patch.object(preflight, "tokenizer_check", return_value=({"status": "PASS", **token_module.probe(TOK)}, TOK)))
            yield

    def test_one_shot_technical_actual_orchestration(self):
        with tempfile.TemporaryDirectory() as tmp, self.prerequisites():
            repo = self.prepare_repo(tmp)
            root = workflow.execute(repo, SETTINGS, "fixture")
            self.assertTrue(Journal(root).verify())
            self.assertTrue(Journal(root).read("qualification")["completed"])
            self.assertEqual(len(list(root.parent.glob("*.tar.gz"))), 2)
            with self.assertRaises(FileExistsError): workflow.execute(repo, SETTINGS, "fixture")

    def test_full_train_fixture_qualification_cohort_raw_seal_then_gt(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, self.prerequisites():
            repo = self.prepare_repo(tmp)
            inventory = meta_rows()
            for i, row in enumerate(inventory):
                target = repo/row["image_locator"]; target.parent.mkdir(exist_ok=True)
                Image.new("RGB", (8,8), (i,0,0)).save(target)
                row["image_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
            groups = cohort.candidate_groups(inventory, [])
            allocation = cohort.candidate_allocation(groups, salt="fixture", dev_fraction=.5)
            plan = {"inventory": inventory, "links": [], "groups": groups, "allocation": allocation}
            path = repo/"cohort.json"; path.write_bytes(json_bytes(plan))
            settings = {**SETTINGS, "mode": "train-dev", "cohort_plan": "cohort.json",
                        "cohort_plan_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "dataset_root": "images"}
            # Move only test-owned fixture images into an explicit dataset root.
            (repo/"images").mkdir(); shutil.move(str(repo/"fixtures"), str(repo/"images/fixtures"))
            original = cohort.evaluation_metadata
            def joined_after_seal(*args):
                self.assertTrue(Journal(run_path(repo, settings["run_id"])).verify())
                return original(*args)
            with patch.object(cohort, "evaluation_metadata", side_effect=joined_after_seal):
                root = workflow.execute(repo, settings, "fixture")
            reporting = Journal(root.parent/(root.name+"-report"))
            self.assertTrue(reporting.verify())
            self.assertTrue(reporting.read("audit")["completed"])
            self.assertEqual(reporting.read("evaluation")["overall"]["planned"], 4)

    def test_all_invalid_qualification_cannot_reach_dataset(self):
        with tempfile.TemporaryDirectory() as tmp, self.prerequisites(Model("not JSON")), \
             patch.object(cohort, "load_plan", side_effect=AssertionError("DATA_READ")):
            repo = self.prepare_repo(tmp)
            with self.assertRaisesRegex(ValueError, "AT_LEAST_ONE"):
                workflow.execute(repo, {**SETTINGS, "mode": "train-dev"}, "fixture")
            self.assertEqual(Journal(run_path(repo, SETTINGS["run_id"])).read("failure")["stage"], "D_QUALIFICATION")

    def test_t1_blocked_sealed_failure_without_loading_model(self):
        with tempfile.TemporaryDirectory() as tmp, self.prerequisites(), \
             patch.object(preflight, "tokenizer_check", return_value=({"status": "BLOCKED"}, None)), \
             patch.object(qwen, "QwenRawScorer", side_effect=AssertionError("GPU_LOAD")):
            repo = self.prepare_repo(tmp)
            with self.assertRaisesRegex(ValueError, "T1_BLOCKED"):
                workflow.execute(repo, SETTINGS, "fixture")
            j = Journal(run_path(repo, SETTINGS["run_id"]))
            self.assertTrue(j.verify())
            self.assertEqual(j.read("failure")["stage"], "C_T1")

    def test_qualification_interrupt_packages_both_journals(self):
        model = Model(); model.failure = KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as tmp, self.prerequisites(model):
            repo = self.prepare_repo(tmp)
            with self.assertRaises(KeyboardInterrupt): workflow.execute(repo, SETTINGS, "fixture")
            root = run_path(repo, SETTINGS["run_id"])
            self.assertTrue(Journal(root).verify())
            self.assertTrue(Journal(root.parent/(root.name+"-qualification")).verify())
            self.assertEqual(len(list(root.parent.glob("*.tar.gz"))), 2)


class SourceAndLaunchTests(unittest.TestCase):
    def test_source_bundle_roundtrip_with_real_git_and_no_working_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)/"source"; repo.mkdir(); (repo/"safeshift").mkdir()
            (repo/"safeshift/fixture.py").write_text("value = 1\n")
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()
            git("init"); git("config", "core.autocrlf", "false"); git("add", ".")
            git("-c", "user.name=CPU Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
            sha = git("rev-parse", "HEAD")
            (repo/"untracked-private-fixture.txt").write_text("not exported")
            output = Path(tmp)/"release"
            with patch.object(preflight, "BASE_SHA", sha), patch.object(preflight, "render_prompt"), patch.object(preflight, "plan"):
                release = kaggle.bundle_source(repo, output)
                restored = Path(tmp)/"restored"
                subprocess.run(["git", "-c", "core.autocrlf=false", "clone", str(output/"pa3_source.bundle"), str(restored)],
                               check=True, capture_output=True)
                check = preflight.source(restored, sha)
            self.assertEqual(release["files"], check["files"])
            self.assertFalse((restored/"untracked-private-fixture.txt").exists())

    def test_cpu_audit_import_has_no_ml_network_or_dataset_access(self):
        code = '''
import sys
def guard(event, args):
    if event == 'import' and args[0].split('.')[0] in {'torch','transformers','PIL'}:
        raise AssertionError('ML_IMPORT')
    if event.startswith('socket.'):
        raise AssertionError('NETWORK')
    if event == 'open' and isinstance(args[0], str) and '/data/raw/' in args[0].replace('\\\\','/'):
        raise AssertionError('DATASET')
sys.addaudithook(guard)
import safeshift.pa3.native.native_audit
assert 'torch' not in sys.modules
print('CPU_AUDIT_IMPORT_PASS')
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_git_source_hash_commit_dirty_and_import_shadow(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp); (repo/"safeshift").mkdir()
            path = repo/"safeshift/synthetic.py"; path.write_text("value = 1\n")
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()
            git("init"); git("config", "core.autocrlf", "false"); git("add", ".")
            git("-c", "user.name=CPU Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-m", "fixture")
            sha = git("rev-parse", "HEAD")
            with patch.object(preflight, "BASE_SHA", sha), patch.object(preflight, "render_prompt"), patch.object(preflight, "plan"):
                out = preflight.source(repo, sha)
                self.assertEqual(out["files"]["safeshift/synthetic.py"], receipt(path.read_bytes()))
                with self.assertRaisesRegex(ValueError, "COMMIT_MISMATCH"): preflight.source(repo, "b"*40)
                path.write_text("value = 2\n")
                with self.assertRaisesRegex(ValueError, "DIRTY"): preflight.source(repo, sha)
                path.write_text("value = 1\n")
                (repo/"safeshift/shadow.py").write_text("value = 3\n")
                with self.assertRaisesRegex(ValueError, "UNTRACKED"): preflight.source(repo, sha)

    def test_runtime_hash_failure_precedes_interpreter_or_model(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, "require"), \
             patch.object(preflight, "source", return_value={}), \
             patch.object(kaggle, "verify_runtime_input", side_effect=ValueError("HASH")), \
             patch.object(kaggle, "runtime_interpreter", side_effect=AssertionError("EXECUTED")), \
             patch.object(kaggle, "restore_model", side_effect=AssertionError("MODEL_READ")):
            inputs = Path(tmp)/"inputs"; inputs.mkdir(); (inputs/"runtime").mkdir(); (inputs/"inventory.json").write_text("{}")
            s = {**SETTINGS, "runtime_input": "runtime", "runtime_inventory_input": "inventory.json", "runtime_inventory_sha256": "a"*64}
            with self.assertRaisesRegex(ValueError, "HASH"): kaggle.launch(tmp, inputs, s)
            self.assertTrue(Journal(run_path(tmp, s["run_id"]).parent/(s["run_id"]+"-launch")).verify())

    def test_notebook_bootstrap_failure_package_without_model_or_data(self):
        nb = json.loads((ROOT/"notebooks/pa3_qwen2_5_kaggle.ipynb").read_text(encoding="utf8"))
        code = "".join(nb["cells"][2]["source"])
        with tempfile.TemporaryDirectory() as tmp:
            settings = {**SETTINGS, "source_commit": ""}
            with patch.object(Path, "cwd", return_value=Path(tmp)):
                with self.assertRaisesRegex(ValueError, "SOURCE_COMMIT"):
                    exec(compile(code, "notebook", "exec"), {"SETTINGS": settings})
            self.assertTrue((Path(tmp)/"data/processed/pa3_bootstrap/pa3-qwen-unit.tar.gz").exists())


if __name__ == "__main__":
    unittest.main()
