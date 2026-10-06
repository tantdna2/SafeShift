"""D9R23 fake envelopes and temporary artifacts only; no model/GPU/dataset calls."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.protocol import classification_policy as policy
from safeshift.protocol.classification_failure_policy import accounting
from safeshift.protocol.schema import HAZARDS, SAFETY_LEVELS, strict_json
from safeshift.qualification.runtime import condition
from safeshift.runners import production_classification as prod
from safeshift.runners.contracts import ParseStatus, RunContext
from safeshift.runners.storage import FileRawStore
from tests.test_classification_qualification import envelope

ROOT = Path(__file__).resolve().parents[1]
BASE = "b28e4665904ecd0ab5057a1bc92e263a81c3e8c7"
PR67_HEAD = "e85300ab3ec122f819a2685613332578f7e203d8"
ALLOWED = {"DECISIONS.md", "TASKS.md", policy.POLICY_PATH, policy.PROMPT_PATH,
           "prompts/.gitattributes", "safeshift/protocol/classification_policy.py",
           "safeshift/protocol/classification_failure_policy.py",
           "safeshift/runners/production_classification.py",
           "notes/w2_d9r23_classification_production_contract.md",
           "tests/test_d9r23_classification_contract.py"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def native(model, text):
    raw = envelope(model, text)
    if model == "qwen3":
        obj = strict_json(raw)
        obj["runtime"]["software_versions"] = policy.load_policy()["classification"][model]["software_versions"]
        raw = json.dumps(obj).encode()
    return raw


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        for name in (policy.POLICY_PATH, policy.PROMPT_PATH):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.p = policy.load_policy()
        self.sequence = 0

    def context(self, model):
        e = self.p["classification"][model]
        return RunContext("fake", "cq_01", e["decoding"], e["preprocessing"], e["precision"],
                          e["quantization"], e["device"], e["software_versions"], BASE,
                          "python -m unittest tests.test_d9r23_classification_contract", "SYNTHETIC_UNIT_TEST")

    def save(self, model, raw, **kwargs):
        self.sequence += 1
        args = dict(context=self.context(model), hardware=self.p["classification"][model]["hardware_contract"],
                    sample_id=f"synthetic-{self.sequence}", input_sha256="0" * 64, repo=self.repo)
        args.update(kwargs)
        return prod.persist_response(model, raw, **args)

    def parse(self, model, raw):
        return prod.classification_adapter(model).adapt(self.save(model, raw))

    def test_exact_four_and_paligemma_rejected(self):
        self.assertEqual(policy.MODELS, ("qwen3", "qwen2_5", "internvl3", "moondream"))
        d18 = strict_json((ROOT / "configs/pre_freeze/d9r18_final_participation_decision.v1.json").read_bytes())
        self.assertEqual([e["model_id"] for e in self.p["classification"].values()],
                         [m["model_id"] for m in d18["models"] if m["classification_participation"] == "PARTICIPATING"])
        for model in ("paligemma", "google/paligemma-3b-mix-448", "smolvlm2", "unknown"):
            for function in (prod.classification_adapter, policy.render_prompt):
                with self.subTest(model=model), self.assertRaisesRegex(ValueError, "CLASSIFICATION_NOT_PARTICIPATING"):
                    function(model)

    def test_prompt_exact_upstream_table_definitions_and_mapping(self):
        prompt = policy.render_prompt("qwen3")
        brief = (ROOT / "notes/w2_model_prompt_interface_decision_brief.md").read_text(encoding="utf-8")
        table = lambda text: [line for line in text.splitlines() if line.startswith("| Safety Level")
                             or line.startswith("|--------------") or line.startswith("| Level ")]
        self.assertEqual(table(prompt), table(brief))
        self.assertEqual(len(table(prompt)), 5)
        for line in prompt.splitlines():
            if line.startswith("   - "):
                self.assertIn(line, brief)
        self.assertEqual(self.p["prompt"]["industry_table_version"], "upstream-industry-rule-table-section-11.1-v1")
        for source, target in zip(("Level one", "Level two", "Level three", "no abnormalities observed"), SAFETY_LEVELS):
            self.assertIn(f"{source} -> {target}", prompt)
        self.assertIs(self.p["prompt"]["ground_truth_policy_changed"], False)

    def test_prompt_hash_same_all_models_no_gt_or_grounding_vocabulary(self):
        raw = (ROOT / policy.PROMPT_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), policy.PROMPT_SHA256)
        self.assertNotIn(b"\r", raw)
        for model in policy.MODELS:
            self.assertEqual(policy.render_prompt(model).encode(), raw)
            for forbidden in (*HAZARDS, "bbox", "grounding", "ground_truth", "sample_id", "folder_domain", "other model"):
                self.assertNotIn(forbidden, raw.decode())
            with self.assertRaises(TypeError):
                policy.render_prompt(model, ground_truth="Level01")
        (self.repo / policy.PROMPT_PATH).write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "C1_PROMPT_HASH_MISMATCH"):
            policy.render_prompt("moondream", repo=self.repo)

    def test_execution_conditions_exact_merged_evidence(self):
        d18 = strict_json((ROOT / "configs/pre_freeze/d9r18_final_participation_decision.v1.json").read_bytes())
        revisions = {m["model_id"]: m["immutable_revision"] for m in d18["models"]}
        for model, e in self.p["classification"].items():
            decoding, preprocessing, device, versions = condition(model)
            if model == "moondream":
                decoding = {"query": decoding["query"]}
                self.assertEqual(e["thinking_controls"]["reasoning"], False)
                self.assertEqual(e["thinking_controls"]["stream"], False)
                self.assertEqual(e["native_api"], "query")
                self.assertNotIn("detect", e["decoding"])
            self.assertEqual((e["decoding"], e["preprocessing"], e["device"], e["software_versions"]),
                             (decoding, preprocessing, device, versions))
            self.assertEqual(e["immutable_revision"], revisions[e["model_id"]])
            self.assertEqual((e["precision"], e["quantization"], e["max_output_tokens"], e["batch_size"]),
                             ("FP16", "NONE", 32, 1))
            self.assertEqual(e["hardware_contract"]["visible_gpu_count"], 2 if model == "qwen3" else 1)
            self.assertEqual(e["hardware_contract"]["cuda_runtime"], "12.8" if model == "qwen3" else "12.4")
            self.assertIs(e["semantic_scores_used_for_selection"], False)
            self.assertEqual(e["adapter_version"], prod.classification_adapter(model).version)
            self.assertEqual(e["parser_version"], prod.PARSER_VERSION)
            policy.validate_context(model, self.context(model), e["hardware_contract"])

    def test_context_mismatch_and_inspecsafe_blocked(self):
        for model, e in self.p["classification"].items():
            for key, value in (("decoding", {}), ("seed", 42), ("precision", "BF16"),
                               ("quantization", "INT8"), ("source_kind", "INSPECSAFE")):
                with self.subTest(model=model, key=key), self.assertRaises(ValueError):
                    policy.validate_context(model, replace(self.context(model), **{key: value}), e["hardware_contract"])
            with self.assertRaisesRegex(ValueError, "HARDWARE"):
                policy.validate_context(model, self.context(model), {})

    def test_exact_levels_all_four_native_envelopes(self):
        for model in policy.MODELS:
            for level in SAFETY_LEVELS:
                with self.subTest(model=model, level=level):
                    result = self.parse(model, native(model, json.dumps({"safety_level": level})))
                    self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
                    self.assertEqual(result.value.safety_level, level)

    def test_invalid_strict_json_no_repairs_all_models(self):
        texts = ('{', '{}', '[]', 'null', '{"safety_level":"Level05"}',
                 '{"safety_level":"level01"}', '{"safety_level":null}',
                 '{"safety_level":"Level01","extra":0}',
                 '{"safety_level":"Level01","safety_level":"Level02"}',
                 'Level04', 'no abnormalities observed', 'Level one',
                 '```json\n{"safety_level":"Level01"}\n```',
                 'Answer: {"safety_level":"Level01"}', '{"safety_level":"Level01"} trailing',
                 '{"safety_level":NaN}', '{"safety_level":" Level04 "}')
        for model in policy.MODELS:
            for text in texts:
                with self.subTest(model=model, text=text):
                    result = self.parse(model, native(model, text))
                    self.assertEqual(result.parse_status, ParseStatus.INVALID)
                    self.assertIsNone(result.value)

    def test_malformed_native_envelope_is_invalid_after_storage(self):
        for model in policy.MODELS:
            for raw in (b'{', b'{}', b'null', b'\xff'):
                with self.subTest(model=model, raw=raw):
                    self.assertEqual(self.parse(model, raw).parse_status, ParseStatus.INVALID)
        for model in ("qwen3", "qwen2_5", "internvl3"):
            obj = strict_json(native(model, '{"safety_level":"Level01"}'))
            field = "revision" if model == "internvl3" else "model_revision"
            obj[field] = "main"
            self.assertEqual(self.parse(model, json.dumps(obj).encode()).parse_status, ParseStatus.INVALID)

    def test_native_decoding_software_and_call_identity_mismatch(self):
        for model in ("qwen3", "qwen2_5"):
            for field in ("generation_kwargs", "runtime"):
                obj = strict_json(native(model, '{"safety_level":"Level01"}'))
                obj[field] = {}
                self.assertEqual(self.parse(model, json.dumps(obj).encode()).parse_status, ParseStatus.INVALID)
        obj = strict_json(native("internvl3", '{"safety_level":"Level01"}'))
        obj["call_id"] = "other"
        self.assertEqual(self.parse("internvl3", json.dumps(obj).encode()).parse_status, ParseStatus.INVALID)

    def test_raw_and_provenance_persist_before_parser(self):
        raw = native("moondream", '{"safety_level":"Level01"}')
        store = FileRawStore(self.repo)
        events = []
        preserve = store.preserve
        def observe(data, meta):
            events.append("preserve")
            self.assertEqual(meta["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(meta["prompt_sha256"], policy.PROMPT_SHA256)
            return preserve(data, meta)
        with patch.object(store, "preserve", side_effect=observe), patch.object(
                prod.CandidateAdapter, "adapt", wraps=prod.CandidateAdapter("moondream").adapt) as parser:
            stored = self.save("moondream", raw, store=store)
            parser.assert_not_called()
            self.assertEqual((self.repo / stored.reference.path).read_bytes(), raw)
            self.assertEqual(events, ["preserve"])
            result = prod.classification_adapter("moondream").adapt(stored)
            self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
            parser.assert_called_once()
            metadata = strict_json((self.repo / stored.reference.path).with_name("metadata.json").read_bytes())
            for key in ("sample_id", "run_id", "call_id", "model_id", "immutable_revision", "prompt",
                        "decoding", "software_versions", "git_commit_sha", "raw_output"):
                self.assertIn(key, metadata)

    def test_persistence_failure_blocks_parser_and_retries_do_not_overwrite(self):
        raw = native("moondream", '{"safety_level":"Level04"}')
        with patch.object(FileRawStore, "preserve", side_effect=OSError("disk full")), patch.object(
                prod.CandidateAdapter, "adapt") as parser:
            with self.assertRaises(OSError):
                self.save("moondream", raw)
            parser.assert_not_called()
        stored = self.save("moondream", raw, sample_id="fixed")
        with self.assertRaises(FileExistsError):
            self.save("moondream", raw, sample_id="fixed")
        self.assertEqual((self.repo / stored.reference.path).read_bytes(), raw)

    def test_combined_entrypoint_orders_storage_and_parse(self):
        raw = native("moondream", '{"safety_level":"Level01"}')
        kwargs = dict(context=self.context("moondream"), sample_id="fake",
                      input_sha256="0" * 64, repo=self.repo,
                      hardware=self.p["classification"]["moondream"]["hardware_contract"])
        with patch.object(FileRawStore, "preserve", side_effect=OSError("disk full")), patch.object(
                prod.ClassificationAdapter, "adapt") as parser:
            with self.assertRaises(OSError):
                prod.persist_and_adapt("moondream", raw, **kwargs)
            parser.assert_not_called()
        original = prod.ClassificationAdapter.adapt
        def observe(adapter, stored):
            self.assertEqual((self.repo / stored.reference.path).read_bytes(), raw)
            self.assertTrue((self.repo / stored.reference.path).with_name("metadata.json").exists())
            return original(adapter, stored)
        with patch.object(prod.ClassificationAdapter, "adapt", observe):
            stored, output = prod.persist_and_adapt("moondream", raw, **kwargs)
        self.assertEqual(output.value.safety_level, "Level01")
        self.assertEqual(stored.reference.sha256, hashlib.sha256(raw).hexdigest())

    def test_metadata_write_failure_and_tamper_block_parser(self):
        from safeshift.runners import storage
        original = storage._write_new
        def fail_metadata(path, data):
            if path.name == "metadata.json":
                raise OSError("metadata failure")
            return original(path, data)
        raw = native("moondream", '{"safety_level":"Level01"}')
        with patch.object(storage, "_write_new", side_effect=fail_metadata), patch.object(prod.CandidateAdapter, "adapt") as parser:
            with self.assertRaises(OSError):
                self.save("moondream", raw)
            parser.assert_not_called()
        for target in ("response.raw", "metadata.json"):
            saved = self.save("moondream", raw)
            path = (self.repo / saved.reference.path).with_name(target)
            path.write_bytes(b"corrupted")
            with patch.object(prod.CandidateAdapter, "adapt") as parser, self.assertRaises(ValueError):
                prod.classification_adapter("moondream").adapt(saved)
            parser.assert_not_called()

    def test_adapter_refuses_unpersisted_bytes_and_other_model_receipt(self):
        with self.assertRaisesRegex(TypeError, "PERSISTED"):
            prod.classification_adapter("moondream").adapt(b'{}')
        saved = self.save("moondream", native("moondream", '{"safety_level":"Level01"}'))
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            prod.classification_adapter("qwen3").adapt(saved)

    def test_invalid_is_fn_never_false_positive_or_level04(self):
        result = accounting([("Level01", None), ("Level02", "Level01"),
                             ("Level03", "Level03"), ("Level04", "Level04")])
        self.assertEqual(result["four_class_counts"]["Level01"], {"true_n": 1, "invalid_n": 1, "tp": 0, "fn": 1, "fp": 1})
        self.assertEqual(result["four_class_counts"]["Level04"]["fp"], 0)
        self.assertEqual(result["parse_success_rate"]["value"], .75)
        self.assertEqual(result["invalid_n"], 1)

    def test_parse_conditional_and_failure_aware_have_distinct_denominators(self):
        result = accounting([("Level01", None), ("Level01", "Level04"), ("Level01", "Level01"),
                             ("Level04", None), ("Level04", "Level01"), ("Level04", "Level04")])
        self.assertEqual((result["total_n"], result["valid_canonical_n"], result["invalid_n"]), (6, 4, 2))
        for key in ("anomaly_fnr", "anomaly_fpr", "level01_fnr", "level01_recall"):
            self.assertEqual(result["parse_conditional"][key], {"numerator": 1, "denominator": 2, "value": .5})
        for metric in result["failure_aware"].values():
            self.assertEqual(metric, {"numerator": 2, "denominator": 3, "value": 2/3})
        self.assertTrue(all("fnr" not in name for name in result["failure_aware"]))

    def test_empty_or_all_invalid_denominators_undefined(self):
        for rows in ([], [("Level01", None), ("Level04", None)]):
            result = accounting(rows)
            self.assertTrue(all(v["value"] is None for v in result["parse_conditional"].values()))
        with self.assertRaises(ValueError):
            accounting([("Level01", "INVALID")])

    def test_pending_freeze_no_grounding_no_selection_and_no_model_imports(self):
        self.assertIs(self.p["inspecsafe_inference_authorized"], False)
        self.assertIs(self.p["semantic_scores_used_for_selection"], False)
        self.assertIs(self.p["active_grounding_dependency"], False)
        self.assertEqual(self.p["protocol_freeze"], "PENDING")
        self.assertEqual(self.p["implementation_freeze"], "PENDING")
        code = """import builtins
old = builtins.__import__
def guard(name, *a, **k):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub'}:
        raise AssertionError('model/backend import')
    return old(name, *a, **k)
builtins.__import__ = guard
from safeshift.runners.production_classification import classification_adapter
for model in ('qwen3', 'qwen2_5', 'internvl3', 'moondream'):
    classification_adapter(model)
"""
        subprocess.run([__import__("sys").executable, "-c", code], cwd=ROOT, check=True)

    def test_exact_scope_history_and_append_only(self):
        changed = set(git("diff", "--name-only", BASE).decode().splitlines())
        staged = set(git("diff", "--cached", "--name-only").decode().splitlines())
        self.assertLessEqual(changed | staged, ALLOWED)
        paths = git("ls-tree", "-r", "--name-only", BASE).decode().splitlines()
        protected = [p for p in paths if p not in ALLOWED and (p.startswith(("configs/", "tests/fixtures/"))
                     or "d9r22" in p or "result" in p or "g5" in p or "g6" in p)]
        self.assertTrue(protected)
        self.assertEqual(git("diff", "--name-only", BASE, "--", *protected), b"")
        for p in protected:
            self.assertIn((ROOT / p).read_bytes(), (git("show", f"{BASE}:{p}"), git("cat-file", "--filters", f"{BASE}:{p}")), p)
        for p in ("DECISIONS.md", "TASKS.md"):
            self.assertTrue((ROOT / p).read_bytes().startswith(git("cat-file", "--filters", f"{BASE}:{p}")))
        self.assertEqual(git("rev-parse", "origin/w2.6-d9r19-production-implementation-d5").decode().strip(), PR67_HEAD)
        self.assertEqual(self.p["source_pr67"]["head"], PR67_HEAD)
        self.assertIs(self.p["source_pr67"]["modified"], False)


if __name__ == "__main__":
    unittest.main()
