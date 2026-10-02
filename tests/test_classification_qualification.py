"""D9R16 artificial fixtures and fake native output only; never model inference."""

from collections import Counter
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image
from safeshift.qualification import classification as cq
from safeshift.qualification.runtime import condition, QualificationLifecycle, execute
from safeshift.runners.contracts import GenerationFailure, ModelIdentity, ParseStatus, RunContext, Task
from safeshift.runners.moondream2 import serialize_native, PendingMoondreamAdapter
from safeshift.runners.internvl3 import PendingInternVL3Adapter
from safeshift.runners.paligemma import PendingPaliGemmaAdapter
from scripts.generate_classification_qualification_cases import generate, fixture

BASE = "ecab4cfa6fd844fbada232975ed4494ea719a90b"


def envelope(model, text, call_id="cq_01"):
    if model == "moondream":
        return serialize_native({"answer": text})
    decoding = condition(model)[0]
    if model in ("qwen3", "qwen2_5"):
        from safeshift.runners import qwen3_vl, qwen2_5_vl
        module = qwen3_vl if model == "qwen3" else qwen2_5_vl
        obj = {"schema_version": module.ENVELOPE_VERSION, "backend": module.BACKEND,
               "model_id": cq.MODELS[model][0], "model_revision": cq.MODELS[model][1],
               "input_token_count": 1, "generated_ids_full": [2, 3], "continuation_ids": [3],
               "decoded_for_parser": text, "decoded_with_special_tokens": text + "<eos>",
               "generation_kwargs": decoding, "effective_generation_config": decoding,
               "runtime": {}}
        if model == "qwen2_5":
            obj["input_token_ids"] = [2]
            obj["runtime"] = {"software_versions": condition(model)[3], "model_dtype": "torch.float16",
                              "model_device": "cuda:0", "input_device": "cuda:0", "device_map": {"": "cuda:0"},
                              "runner_version": module.Qwen2_5VLRunner.version,
                              "attn_implementation": "sdpa", "preprocessing": module.PREPROCESSING,
                              "generation_config_scope": "CHECKPOINT_SNAPSHOT_PLUS_CALLER_KWARGS_BEFORE_DISPATCH"}
        return cq.json_bytes(obj)
    prefix = [257152] * 1024 if model == "paligemma" else [151667] * 256
    obj = {"schema_version": f"{model}-native-output-v1", "model_id": cq.MODELS[model][0],
           "revision": cq.MODELS[model][1], "input_token_ids": prefix,
           "generated_ids_full": [prefix + [3, 1]], "continuation_ids": [3, 1],
           "decoded_text": text, "decoded_with_special_tokens": text + "<eos>",
           "decoding": decoding, "run_id": "fake", "call_id": call_id,
           "input_boundary": {"pixel_values_shape": [1, 3, 448, 448], "pixel_values_dtype": "FP16",
                              "input_ids_dtype": "int64", "device": "cuda:0",
                              "image_token_count": len(prefix), "input_tokens": len(prefix)}}
    if model == "paligemma":
        obj.update(dtype="FP16", device="cuda:0", quantization="NONE", generation_kwargs={"logits_to_keep": 1},
                   hardware={"gpu_name": "Tesla T4", "visible_gpu_count": 1, "compute_capability": [7, 5],
                             "total_vram_bytes": 15 * 2**30, "device": "cuda:0", "cuda_runtime": "12.4"})
    return cq.json_bytes(obj)


def context(model="moondream"):
    decoding, preprocessing, device, versions = condition(model)
    return RunContext("fake", "cq_01", decoding, preprocessing, "FP16", "NONE", device, versions,
                      BASE, "python -m unittest tests.test_classification_qualification", cq.SOURCE_KIND)


class FakeRunner:
    version = "fake-qualification-v1"

    def __init__(self, model="moondream", *, bad=None, fail_at=None, partial=False):
        self.identity = ModelIdentity(*cq.MODELS[model], "SYNTHETIC_TEST_ONLY")
        self.model, self.bad, self.fail_at, self.partial = model, bad, fail_at, partial
        self.loads = self.generates = 0
        self.requests = []
        self.loaded = False

    def initialize(self, context):
        if self.fail_at == "initialize":
            raise RuntimeError("fake dependency failure")

    def load(self, context):
        if self.fail_at == "load":
            raise RuntimeError("fake load failure")
        if not self.loaded:
            self.loads += 1
            self.loaded = True

    def prepare_input(self, request, context):
        self.requests.append(request)
        return request

    def generate_raw(self, request, context):
        self.generates += 1
        if self.generates == self.fail_at:
            raise GenerationFailure(b"partial-native-bytes" if self.partial else None)
        level = cq.SAFETY_LEVELS[(self.generates - 1) // 2]
        text = level if self.model == "paligemma" else json.dumps({"safety_level": level})
        if self.generates == 1 and self.bad is not None:
            text = self.bad
        return envelope(self.model, text, context.call_id)


class SuiteTests(unittest.TestCase):
    def test_exact_eight_balanced_rgb_hashes_and_regeneration(self):
        generate(check=True)
        cases = cq.load_suite()
        self.assertEqual(len(cases), 8)
        self.assertEqual(Counter(c["expected_safety_level"] for c, _ in cases), dict.fromkeys(cq.SAFETY_LEVELS, 2))
        for index, (case, raw) in enumerate(cases):
            self.assertEqual(raw, fixture(index))
            self.assertEqual(cq.digest(raw), case["image_sha256"])
            self.assertEqual(cq.MARKERS[case["marker"]], case["expected_safety_level"])
            self.assertNotIn("data/raw", case["image_path"])
            self.assertNotIn("inspecsafe", case["image_path"].lower())
            with Image.open(cq.ROOT / case["image_path"]) as image:
                self.assertEqual((image.mode, image.size, image.info), ("RGB", (256, 256), {}))
                colors = {color for _, color in image.getcolors(256 * 256)}
                colored = {c for c in colors if len(set(c)) > 1}
                self.assertEqual(len(colored), 1)

    def test_same_policy_no_per_case_label_in_prompt_api(self):
        for model in cq.MODELS:
            prompt = cq.prompt_for(model)
            self.assertIn(cq.POLICY, prompt)
            for case, _ in cq.load_suite():
                self.assertNotIn(case["case_id"], prompt)
                self.assertNotIn(case["image_path"], prompt)
            self.assertNotIn("expected", prompt)
        self.assertTrue(cq.prompt_for("paligemma").startswith("answer en "))

    def test_corrupt_fixture_and_manifest_fail_closed(self):
        with TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / cq.MANIFEST).parent.mkdir(parents=True)
            generate(repo)
            manifest = json.loads((repo / cq.MANIFEST).read_text())
            for mutation in (lambda x: x["cases"].pop(),
                             lambda x: x["cases"][0].update(image_path="data/raw/image.png"),
                             lambda x: x["cases"][0].update(expected_safety_level="Level04"),
                             lambda x: x.update(policy_text="different")):
                bad = deepcopy(manifest)
                mutation(bad)
                (repo / cq.MANIFEST).write_bytes(cq.json_bytes(bad))
                with self.assertRaises(ValueError):
                    cq.load_suite(repo)
            (repo / cq.MANIFEST).write_bytes(cq.json_bytes(manifest))
            (repo / manifest["cases"][0]["image_path"]).write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "HASH"):
                cq.load_suite(repo)


class ParserTests(unittest.TestCase):
    def test_all_five_all_levels(self):
        for model in cq.MODELS:
            for level in cq.SAFETY_LEVELS:
                text = level if model == "paligemma" else json.dumps({"safety_level": level})
                result = cq.CandidateAdapter(model).adapt(envelope(model, text), Task.CLASSIFICATION)
                self.assertEqual(result.parse_status, ParseStatus.SUCCESS, model)
                self.assertEqual(result.value, cq.Classification(level))

    def test_strict_json_rejects_markdown_extra_key_malformed_synonyms_duplicates(self):
        bad = ['```json\n{"safety_level":"Level01"}\n```', '{"safety_level":"Level01","extra":0}',
               '{"safety_level":', '{"safety_level":"safe"}', 'yes', 'no',
               '{"safety_level":"Level01","safety_level":"Level02"}',
               '{"safety_level":null}', '{"safety_level":true}', '{"safety_level":["Level01"]}',
               '{"safety_level":"Level01"} trailing', '{"safety_level":NaN}']
        for model in ("qwen3", "qwen2_5", "internvl3", "moondream"):
            for text in bad:
                with self.subTest(model=model, text=text):
                    self.assertEqual(cq.CandidateAdapter(model).adapt(envelope(model, text), Task.CLASSIFICATION).parse_status,
                                     ParseStatus.INVALID)

    def test_paligemma_no_rescue_or_presence_mapping(self):
        for text in ('yes', 'no', 'safe', 'unsafe', 'level01', ' Level01', 'Level01\n',
                     '```Level01```', 'Level01 explanation', '{"safety_level":"Level01"}',
                     'Level01<eos>', 'Level01 Level02', ''):
            self.assertEqual(cq.CandidateAdapter("paligemma").adapt(envelope("paligemma", text), Task.CLASSIFICATION).parse_status,
                             ParseStatus.INVALID)

    def test_hf_envelope_identity_tokens_metadata_and_extra_keys(self):
        for model in ("internvl3", "paligemma"):
            obj = json.loads(envelope(model, 'Level01'))
            for key, value in (("model_id", "other"), ("revision", "main"), ("schema_version", "other"),
                               ("continuation_ids", [True]), ("generated_ids_full", [[1]]),
                               ("decoded_text", 1), ("input_boundary", {}), ("decoding", {}),
                               ("unexpected", 1), ("call_id", "")):
                bad = {**obj, key: value}
                with self.subTest(model=model, key=key):
                    self.assertEqual(cq.CandidateAdapter(model).adapt(cq.json_bytes(bad), Task.CLASSIFICATION).parse_status,
                                     ParseStatus.INVALID)
            bad = deepcopy(obj)
            bad["decoding"]["do_sample"] = 0
            self.assertEqual(cq.CandidateAdapter(model).adapt(cq.json_bytes(bad), Task.CLASSIFICATION).parse_status,
                             ParseStatus.INVALID)

    def test_moondream_exact_answer_envelope(self):
        valid_text = '{"safety_level":"Level01"}'
        for value in ({"answer": valid_text, "reasoning": "extra"}, {"answer": 1},
                      {"answers": valid_text}, [valid_text]):
            self.assertEqual(cq.CandidateAdapter("moondream").adapt(serialize_native(value), Task.CLASSIFICATION).parse_status,
                             ParseStatus.INVALID)
        obj = json.loads(serialize_native({"answer": valid_text}))
        obj["native"][1].append(deepcopy(obj["native"][1][0]))
        self.assertEqual(cq.CandidateAdapter("moondream").adapt(cq.json_bytes(obj), Task.CLASSIFICATION).parse_status,
                         ParseStatus.INVALID)

    def test_no_grounding_dispatch(self):
        for model in cq.MODELS:
            with self.assertRaises(ValueError):
                cq.CandidateAdapter(model).adapt(b"{}", Task.GROUNDING)

    def test_native_run_and_call_identity_binding(self):
        for model in ("internvl3", "paligemma"):
            raw = envelope(model, "Level01" if model == "paligemma" else '{"safety_level":"Level01"}')
            for kwargs in ({"run_id": "different"}, {"call_id": "cq_02"}):
                self.assertEqual(cq.CandidateAdapter(model, **kwargs).adapt(raw, Task.CLASSIFICATION).parse_status,
                                 ParseStatus.INVALID)

    def test_paligemma_eos_and_text_mismatch(self):
        obj = json.loads(envelope("paligemma", "Level01"))
        obj["decoded_with_special_tokens"] = "yes<eos>"
        self.assertEqual(cq.CandidateAdapter("paligemma").adapt(cq.json_bytes(obj), Task.CLASSIFICATION).parse_status,
                         ParseStatus.INVALID)

    def test_production_pending_never_promoted(self):
        for model, adapter in (("internvl3", PendingInternVL3Adapter()),
                               ("moondream", PendingMoondreamAdapter()), ("paligemma", PendingPaliGemmaAdapter())):
            raw = envelope(model, "Level01" if model == "paligemma" else '{"safety_level":"Level01"}')
            self.assertEqual(cq.CandidateAdapter(model).adapt(raw, Task.CLASSIFICATION).parse_status, ParseStatus.SUCCESS)
            self.assertEqual(adapter.adapt(raw, Task.CLASSIFICATION).parse_status, ParseStatus.INVALID)


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        (self.repo / cq.MANIFEST).parent.mkdir(parents=True)
        shutil.copyfile(cq.ROOT / cq.MANIFEST, self.repo / cq.MANIFEST)
        shutil.copytree(cq.ROOT / cq.FIXTURES, self.repo / cq.FIXTURES)

    def run_fake(self, runner, **kwargs):
        return cq.run_suite(runner, context(runner.model), model=runner.model, repo=self.repo, **kwargs)

    def test_all_five_eight_calls_one_load_zero_grounding_no_label_leak(self):
        for model in cq.MODELS:
            runner = FakeRunner(model)
            result = self.run_fake(runner)
            self.assertEqual(result["run_status"], "PASS", model)
            self.assertEqual((runner.loads, runner.generates), (1, 8))
            self.assertEqual({r.task for r in runner.requests}, {Task.CLASSIFICATION})
            self.assertEqual({r.prompt for r in runner.requests}, {cq.prompt_for(model)})
            self.assertEqual((result["grounding_calls"], result["retry_count"], result["repair_count"]), (0, 0, 0))
            for row in result["calls"]:
                raw_path = self.repo / row["raw_output"]["path"]
                metadata = json.loads((raw_path.parent / "metadata.json").read_text())
                self.assertEqual(metadata["source_kind"], cq.SOURCE_KIND)
                self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
                self.assertNotIn("expected_safety_level", metadata["input_provenance"])

    def test_raw_bytes_checksum_metadata_persist_before_parser(self):
        original = cq.CandidateAdapter.adapt
        observations = []
        def inspect(adapter, raw, task):
            stored = list(self.repo.rglob("response.raw"))
            current = [p for p in stored if p.read_bytes() == raw]
            self.assertTrue(current)
            metadata = json.loads((current[-1].parent / "metadata.json").read_text())
            self.assertEqual(metadata["raw_output"]["sha256"], cq.digest(raw))
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            observations.append(raw)
            return original(adapter, raw, task)
        with patch.object(cq.CandidateAdapter, "adapt", inspect):
            result = self.run_fake(FakeRunner())
        self.assertEqual(result["run_status"], "PASS")
        self.assertEqual(len(observations), 8)

    def test_wrong_level_fail_but_role_and_roster_unchanged(self):
        result = self.run_fake(FakeRunner(bad='{"safety_level":"Level04"}'))
        self.assertEqual(result["run_status"], "FAIL")
        self.assertIn("SEMANTIC_CLASSIFICATION_FAILURE", result["causes"])
        self.assertEqual(result["model_role_after_run"], "PENDING_RESEARCH_LEAD_REVIEW")
        self.assertFalse(result["roster_membership_changed"])
        self.assertFalse(result["production_adapter_promoted"])

    def test_format_failure_all_eight_no_retry(self):
        runner = FakeRunner(bad="```invalid```")
        result = self.run_fake(runner)
        self.assertEqual(result["run_status"], "FAIL")
        self.assertEqual(runner.generates, 8)
        self.assertIn("INTERFACE_OR_FORMAT_FAILURE", result["causes"])

    def test_seven_of_eight_is_fail_not_pass(self):
        result = self.run_fake(FakeRunner())
        verdict = cq.evaluate(cq.load_suite(), result["calls"][:7])
        self.assertEqual(verdict["run_status"], "FAIL")
        self.assertEqual(verdict["model_role_after_run"], "PENDING_RESEARCH_LEAD_REVIEW")

    def test_runtime_failure_inconclusive_and_no_retry(self):
        for failure in ("initialize", "load", 1, 8):
            runner = FakeRunner(fail_at=failure)
            result = self.run_fake(runner, artifact_root=f"data/processed/test/{failure}")
            self.assertEqual(result["run_status"], "INCONCLUSIVE")
            self.assertEqual(result["causes"], ["INFRASTRUCTURE_OR_RUNTIME_FAILURE"])
            self.assertEqual(len(result["calls"]), failure if type(failure) is int else 1)

    def test_prior_semantic_failure_not_erased_by_runtime_failure(self):
        result = self.run_fake(FakeRunner(bad='{"safety_level":"Level04"}', fail_at=2))
        self.assertEqual(result["run_status"], "FAIL")
        self.assertIn("SEMANTIC_CLASSIFICATION_FAILURE", result["causes"])
        self.assertIn("INFRASTRUCTURE_OR_RUNTIME_FAILURE", result["causes"])

    def test_partial_raw_preserved_never_parsed(self):
        with patch.object(cq.CandidateAdapter, "adapt", side_effect=AssertionError("must not parse")) as parser:
            result = self.run_fake(FakeRunner(fail_at=1, partial=True))
        parser.assert_not_called()
        self.assertEqual(result["run_status"], "INCONCLUSIVE")
        self.assertEqual((self.repo / result["calls"][0]["raw_output"]["path"]).read_bytes(), b"partial-native-bytes")

    def test_storage_corruption_stops_before_parser(self):
        from safeshift.runners.storage import FileRawStore
        original = FileRawStore.preserve
        def corrupt(store, raw, provenance):
            ref = original(store, raw, provenance)
            (store.repo / ref.path).write_bytes(b"corrupt")
            return ref
        with patch.object(FileRawStore, "preserve", corrupt), patch.object(cq.CandidateAdapter, "adapt") as parser:
            runner = FakeRunner()
            result = self.run_fake(runner)
        parser.assert_not_called()
        self.assertEqual(result["run_status"], "INCONCLUSIVE")
        self.assertEqual(runner.generates, 1)

    def test_second_attempt_blocked_even_new_run_id(self):
        self.run_fake(FakeRunner(fail_at="load"))
        runner = FakeRunner()
        with self.assertRaises(FileExistsError):
            cq.run_suite(runner, replace(context(), run_id="new"), model="moondream", repo=self.repo)
        self.assertEqual(runner.generates, 0)

    def test_runtime_condition_change_rejected_before_load(self):
        bad_decoding = deepcopy(context().decoding)
        bad_decoding["query"]["temperature"] = False
        for update in ({"source_kind": "INSPECSAFE"}, {"precision": "BF16"}, {"decoding": {}},
                       {"decoding": bad_decoding}, {"seed": 1}):
            with self.assertRaises(ValueError):
                cq.run_suite(FakeRunner(), replace(context(), **update), model="moondream", repo=self.repo)

    def test_failed_result_save_preserves_valid_semantic_failure(self):
        with patch.object(cq.VerifiedRawStore, "save_result", side_effect=OSError("fake disk failure")):
            result = self.run_fake(FakeRunner(bad='{"safety_level":"Level04"}'))
        self.assertEqual(result["run_status"], "FAIL")
        self.assertIn("SEMANTIC_CLASSIFICATION_FAILURE", result["causes"])
        self.assertIn("INFRASTRUCTURE_OR_RUNTIME_FAILURE", result["causes"])

    def test_owner_entry_fake_execution_and_evidence_failure_keeps_fail(self):
        from safeshift.qualification import runtime
        from safeshift.runners.paligemma_snapshot import OFFLINE_ENV
        for path in (cq.PLAN,):
            shutil.copyfile(cq.ROOT / path, self.repo / path)
        runner = FakeRunner(bad='{"safety_level":"Level04"}')
        original_write = runtime._write_new
        def fail_evidence(path, raw):
            if path.name == "runtime_evidence.json":
                raise OSError("fake disk failure")
            return original_write(path, raw)
        with patch.object(runtime.subprocess, "check_output", side_effect=[BASE, ""]), \
                patch.dict(runtime.os.environ, OFFLINE_ENV), \
                patch.object(runtime.platform, "system", return_value="Linux"), \
                patch.object(runtime.platform, "machine", return_value="x86_64"), \
                patch.object(runtime.platform, "python_version", return_value=condition("moondream")[3]["python"]), \
                patch.object(runtime.importlib.metadata, "version", side_effect=condition("moondream")[3].__getitem__), \
                patch.dict("sys.modules", {"torch": SimpleNamespace()}), \
                patch.object(runtime, "native_runner", return_value=(runner, {})), \
                patch.object(runtime, "_write_new", side_effect=fail_evidence):
            report = execute("moondream", expected_commit=BASE, research_lead_authorization="SYNTHETIC_TEST_ONLY",
                             venue_internet_off=True, run_id="fake", repo=self.repo, command="unit-test")
        self.assertEqual(report["run_status"], "FAIL")
        self.assertIn("SEMANTIC_CLASSIFICATION_FAILURE", report["causes"])
        self.assertEqual((runner.loads, runner.generates), (1, 8))

    def test_lifecycle_one_load_dispatch(self):
        runner = FakeRunner()
        wrapped = QualificationLifecycle(runner, "moondream")
        for _ in range(8):
            wrapped.initialize(context())
            wrapped.load(context())
        self.assertEqual((runner.loads, wrapped.model_loads), (1, 1))

    def test_real_entry_requires_authorization_before_backend(self):
        with patch("safeshift.qualification.runtime.native_runner") as factory:
            with self.assertRaises(ValueError):
                execute("moondream", expected_commit=BASE, research_lead_authorization="", venue_internet_off=False,
                        run_id="fake", repo=self.repo, command="fake")
        factory.assert_not_called()


class ProtectedStateTests(unittest.TestCase):
    def test_roster_grounding_d5_freeze_and_history_unchanged(self):
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE,
                                         "configs", "safeshift", "scripts", "notebooks", "prompts", "schemas",
                                         "tests/fixtures", "notes/w2_qwen3_external_gate_result.md",
                                         "notes/w2_paligemma_external_gate_result.md",
                                         "notes/w2_paligemma_single_t4_runtime_qualification.md",
                                         "notes/w2_metrics_statistics_decision_brief.md"], cwd=cq.ROOT, text=True).splitlines()
        for path in paths:
            if path in ("safeshift/runners/internvl3.py", "safeshift/runners/paligemma.py"):
                continue  # Exact two whitelist replacements tested independently below.
            old = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=cq.ROOT)
            # D9R18 authorizes only current roster/template overlays, guarded by its exact-delta test.
            current = (subprocess.check_output(["git", "show", "93e1004de311588e94356e19edf53220de13e194:" + path], cwd=cq.ROOT)
                       if path in ("configs/pre_freeze/local_models.d9.json", "configs/pre_freeze/freeze_manifest.d9.template.json")
                       else (cq.ROOT / path).read_bytes())
            self.assertEqual(current.replace(b"\r\n", b"\n"), old.replace(b"\r\n", b"\n"), path)
        roster = json.loads((cq.ROOT / "configs/pre_freeze/local_models.d9.json").read_text())
        self.assertEqual({m["model_id"] for m in roster["primary_models"]}, {v[0] for v in cq.MODELS.values()})
        self.assertTrue(all(m["classification"] == "CANDIDATE" for m in roster["primary_models"]))
        freeze = json.loads((cq.ROOT / "configs/pre_freeze/freeze_manifest.d9.template.json").read_text())
        self.assertEqual(freeze["protocol_freeze_commit_sha"], "PENDING")
        self.assertFalse(freeze["inspecsafe_inference_authorized"])

    def test_only_two_runner_source_whitelist_extensions(self):
        for path in ("safeshift/runners/internvl3.py", "safeshift/runners/paligemma.py"):
            before = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=cq.ROOT).decode()
            after = (cq.ROOT / path).read_text()
            self.assertEqual(after, before.replace('context.source_kind != "HANDCRAFTED_RUNTIME_SMOKE"',
                'context.source_kind not in {"HANDCRAFTED_RUNTIME_SMOKE", "EXTERNAL_CLASSIFICATION_QUALIFICATION"}'))

    def test_new_source_kind_accepts_only_narrow_pair(self):
        from safeshift.runners import internvl3, paligemma
        for key, module in (("internvl3", internvl3), ("paligemma", paligemma)):
            cls = module.InternVL3Runner if key == "internvl3" else module.PaliGemmaRunner
            with patch.object(module, "require_offline_env"):
                for source in (cq.SOURCE_KIND, "HANDCRAFTED_RUNTIME_SMOKE"):
                    cls()._condition(replace(context(key), source_kind=source))
                for source in ("INSPECSAFE", "data/raw", "EXTERNAL_GATE", ""):
                    with self.assertRaises(ValueError):
                        cls()._condition(replace(context(key), source_kind=source))

    def test_plan_prep_only_no_model_removal(self):
        plan = json.loads((cq.ROOT / cq.PLAN).read_text())
        self.assertEqual(set(plan["models"]), set(cq.MODELS))
        self.assertEqual(plan["classification_results"], "NOT_RUN")
        self.assertTrue(plan["no_model_removal"])
        self.assertFalse(plan["execution_authorized_in_prep"])
        self.assertFalse(plan["production_classification_qualified"])
        self.assertEqual(plan["protocol_freeze"], "PENDING")


if __name__ == "__main__":
    unittest.main()
