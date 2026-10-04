"""Offline handcrafted runtime tests: no weights, torch import or GPU operations."""

from copy import deepcopy
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import grounding_multicategory_v3 as r
from scripts.prepare_grounding_multicategory_v3 import build

ROOT = Path(__file__).resolve().parents[1]
PLAN = r.read_json(ROOT / r.PLAN)
MANIFEST, IMAGES = build()


def envelope(text="[]"):
    return dict(native_ok=True, input_token_ids=[900], generated_ids_full=[900, 10, 1],
                continuation_ids=[10, 1], parser_decode=text, decoded_with_special_tokens=text + "<eos>",
                eos_token_ids=[1], effective_generation_config=r.DECODING, termination_reason="EOS")


def answer(case, model):
    if model == "qwen3":
        return json.dumps([{"label": t["label"], "bbox_2d": [v * 1000 for v in t["bbox"]]} for t in case["targets"]])
    return "; ".join("".join(f"<loc{int(t['bbox'][i] * 1024):04d}>" for i in (1, 0, 3, 2)) + " " + t["label"] for t in case["targets"])


class FakeRuntime:
    def __init__(self, model, malformed_at=None):
        self.key, self.count, self.loads, self.prompts = model, 0, 0, []
        self.malformed_at = malformed_at

    def load(self):
        self.loads += 1

    def generate(self, image, text):
        self.prompts.append(text)
        case = MANIFEST["cases"][self.count]
        assert image == IMAGES[case["image_path"]]
        raw = envelope(answer(case, self.key))
        if self.count == self.malformed_at:
            raw["generated_ids_full"][0] = 777
        self.count += 1
        return r.encode(raw)


class ContractTests(unittest.TestCase):
    def test_hash_mismatch_fails_before_manifest_or_runtime(self):
        with patch.object(r, "text_hash", return_value="bad"):
            with self.assertRaisesRegex(ValueError, "FROZEN_HASH"):
                r.frozen(ROOT)

    def test_main_and_head_identity_fail_closed(self):
        for wrong in ("main", "head"):
            def git(repo, *args):
                if args == ("rev-parse", "HEAD"):
                    return "a" * 40
                if args == ("rev-parse", "origin/main"):
                    return "b" * 40 if wrong == "main" else r.BASE
                return "c" * 40
            with patch.object(r, "git", side_effect=git), self.assertRaises(ValueError):
                r.preflight(ROOT, "qwen3", "identity-test", images=False)

    def test_approved_preflight_and_mismatching_authority_fields(self):
        lock = r.read_json(ROOT / r.RUNTIME_LOCK)
        env = {"schema_version": "grounding-v3-environment-observation-v1", "model_key": "qwen3",
               "model_id": r.MODELS["qwen3"][0], "revision": r.MODELS["qwen3"][1],
               "processor_revision": r.MODELS["qwen3"][1], "tokenizer_revision": r.MODELS["qwen3"][1],
               "software_versions": {k: "test" for k in ("python", "torch", "tokenizers", "Pillow", "accelerate", "huggingface-hub", "safetensors")},
               "cuda": "test", "hardware": [{"name": "Tesla T4", "compute_capability": [7, 5]}] * 2,
               "snapshot_files": {k: {"sha256": "0" * 64, "size_bytes": 1} for k in
                                  ("config.json", "generation_config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json")},
               "observed": True, "git_commit": "a" * 40, "code_and_contract_hashes": lock["sha256"],
               "generation_config": r.DECODING}
        env["software_versions"]["transformers"] = "4.57.1"
        authority = {"execution_authorized": True, "model_key": "qwen3", "run_id": "approved-test",
                     "head_sha": "a" * 40, "main_sha": r.BASE, "environment_sha256": r.sha(r.encode(env)),
                     "runtime_lock_sha256": r.text_hash(ROOT / r.RUNTIME_LOCK), "internet_off_attested": True,
                     "research_lead": "Lead", "independent_auditor": "Auditor", "review_reference": "TEST_ONLY"}
        def git(repo, *args):
            if args == ("rev-parse", "HEAD"):
                return "a" * 40
            if args[0] == "status":
                return ""
            return r.BASE
        with patch.object(r, "git", side_effect=git):
            result = r.preflight(ROOT, "qwen3", "approved-test", env, authority, images=False)
            self.assertEqual(result["status"], "PREFLIGHT_PASS")
            for key in authority:
                bad = {**authority, key: None}
                with self.subTest(field=key), self.assertRaises(ValueError):
                    r.preflight(ROOT, "qwen3", "approved-test", env, bad, images=False)
            for key in ("processor_revision", "tokenizer_revision", "cuda", "hardware", "snapshot_files"):
                bad_env = {**env, key: {} if key == "snapshot_files" else [] if key == "hardware" else None}
                with self.subTest(field=key), self.assertRaises(ValueError):
                    r.preflight(ROOT, "qwen3", "approved-test", bad_env, authority, images=False)

    def test_frozen_identities_and_hashes(self):
        plan, manifest, lock = r.frozen(ROOT)
        self.assertEqual(plan, PLAN)
        self.assertEqual(manifest, MANIFEST)
        self.assertFalse(lock["execution_authorized"])
        self.assertEqual(lock["QUALIFICATION_EXECUTION"], "NOT_RUN")
        self.assertEqual(lock["pr67_documentary_lock"]["headRefOid"], "e85300ab3ec122f819a2685613332578f7e203d8")

    def test_g3_and_historical_artifacts_unchanged_from_base(self):
        lock = r.read_json(ROOT / r.LOCK)
        names = set(lock["sha256"]) | set(lock["historical_git_blobs"]) | {r.LOCK, "notes/w2_d9r19g3_positive_multicategory_grounding_prep.md"}
        for name in names:
            base = subprocess.check_output(["git", "show", f"{r.BASE}:{name}"], cwd=ROOT)
            actual = (ROOT / name).read_bytes()
            if not name.endswith(".png"):
                actual = actual.replace(b"\r\n", b"\n")
            self.assertEqual(actual, base, name)

    def test_logs_append_only(self):
        for name in ("DECISIONS.md", "TASKS.md"):
            base = subprocess.check_output(["git", "show", f"{r.BASE}:{name}"], cwd=ROOT)
            self.assertTrue((ROOT / name).read_bytes().replace(b"\r\n", b"\n").startswith(base))

    def test_historical_roles_and_gates(self):
        lock = r.read_json(ROOT / r.RUNTIME_LOCK)
        self.assertEqual(set(lock["historical_roles"].values()), {"NOT_PARTICIPATING"})
        self.assertEqual(lock["historical_gates"], {"qwen3": "GATE_FAIL", "paligemma": "FAIL"})
        self.assertEqual(set(lock["absence_blockers"].values()), {"UNRESOLVED"})

    def test_environment_is_not_fabricated(self):
        env = r.read_json(ROOT / r.ENV_TEMPLATE)
        self.assertFalse(env["observed"])
        self.assertFalse(env["runtime_ready"])
        self.assertFalse(env["execution_authorized"])
        self.assertIsNone(env["models"]["qwen3"]["historical_software_evidence"]["tokenizers"])
        self.assertEqual(env["models"]["qwen3"]["gpu_count"], 2)
        self.assertEqual(env["models"]["paligemma"]["gpu_count"], 1)

    def test_unauthorized_execution_never_imports_or_loads_runtime(self):
        with patch.object(r, "NativeRuntime") as native, patch.object(r, "inspect_environment") as inventory:
            with patch.object(r, "preflight", return_value={"status": "BLOCKED"}):
                with self.assertRaisesRegex(ValueError, "EXECUTION_BLOCKED"):
                    r.execute(ROOT, "qwen3", "test", None, None, [])
            native.assert_not_called()
            inventory.assert_not_called()

    def test_dry_preflight_blocks_without_authority(self):
        with patch.object(r, "inspect_environment", side_effect=AssertionError("GPU forbidden")):
            value = r.preflight(ROOT, "qwen3", "static-check", images=False)
        self.assertEqual(value["status"], "BLOCKED")
        self.assertFalse(value["execution_authorized"])
        self.assertEqual(value["required_calls"], 12)
        self.assertEqual(value["decoding"]["max_new_tokens"], 512)

    def test_paths_reject_inspecsafe_traversal_absolute_alias(self):
        for name in ("../escape", "data/raw/InspecSafe-V1", "D:/outside", "foo/InspecSafe", "a/b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                r.run_path(ROOT, name)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = r.run_path(root, "once")
            path.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "NEW_EXECUTION_DIRECTORY"):
                r.run_path(root, "once")

    def test_cli_has_no_retry_repair_or_budget_overrides(self):
        for flag in ("--retry", "--repair", "--max-new-tokens", "--prompt"):
            process = subprocess.run([sys.executable, "scripts/run_grounding_multicategory_v3.py",
                                      "--model", "qwen3", "--run-id", "fake", flag], cwd=ROOT, capture_output=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn(b"unrecognized arguments", process.stderr)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "call"

    def test_raw_metadata_closed_fsynced_reread_before_parse(self):
        events = []
        original_write, original_read = r.write_bytes, r.verified_read
        def write(path, raw):
            result = original_write(path, raw)
            events.append("closed:" + path.name)
            return result
        def read(path, receipt):
            value = original_read(path, receipt)
            events.append("verified:" + path.name)
            return value
        def parser(text, labels):
            events.append("parse")
            self.assertEqual(text, "[]")
            self.assertEqual(r.read_json(self.path / "preparse.json")["parse_status"], "NOT_ATTEMPTED")
            return r.parse_qwen3_multicategory(text, labels)
        with patch.object(r, "write_bytes", side_effect=write), patch.object(r, "verified_read", side_effect=read), \
             patch.dict(r.PARSERS, {"qwen3": parser}), patch.object(r.os, "fsync", wraps=r.os.fsync) as sync:
            r.persist_then_parse(self.path, r.encode(envelope()), {}, "qwen3", PLAN["query_labels"])
        self.assertEqual(events, ["closed:raw.json", "closed:preparse.json", "verified:raw.json", "verified:preparse.json", "parse"])
        self.assertEqual(sync.call_count, 2)

    def test_parser_uses_reread_not_in_memory_text(self):
        original_read = r.verified_read
        def read(path, receipt):
            raw = original_read(path, receipt)
            if path.name == "raw.json":
                obj = json.loads(raw)
                obj["parser_decode"] = "reread sentinel"
                return r.encode(obj)
            return raw
        parser = Mock(return_value=None)
        with patch.object(r, "verified_read", side_effect=read), patch.dict(r.PARSERS, {"qwen3": parser}):
            r.persist_then_parse(self.path, r.encode(envelope()), {}, "qwen3", PLAN["query_labels"])
        parser.assert_called_once_with("reread sentinel", PLAN["query_labels"])

    def test_storage_and_hash_failure_never_parse(self):
        for target in ("write", "fsync", "hash", "metadata_hash", "size"):
            with self.subTest(target=target):
                path = self.path / target
                self.path.mkdir(exist_ok=True)
                parser = Mock()
                original = r.verified_read
                def bad_read(file, receipt):
                    if file.name == ("preparse.json" if target == "metadata_hash" else "raw.json"):
                        receipt = {**receipt, "sha256": "0" * 64} if target != "size" else {**receipt, "size_bytes": 0}
                    return original(file, receipt)
                tool = patch.object(r, "write_bytes", side_effect=OSError("storage")) if target == "write" else \
                       patch.object(r.os, "fsync", side_effect=OSError("fsync")) if target == "fsync" else \
                       patch.object(r, "verified_read", side_effect=bad_read)
                with tool, patch.dict(r.PARSERS, {"qwen3": parser}):
                    with self.assertRaises((ValueError, OSError)):
                        r.persist_then_parse(path, r.encode(envelope()), {}, "qwen3", PLAN["query_labels"])
                parser.assert_not_called()

    def test_boundary_eos_config_failures_preserve_raw_and_never_parse(self):
        for field, value in (("generated_ids_full", [999, 10, 1]), ("continuation_ids", [10]),
                             ("continuation_ids", [True, 1]), ("termination_reason", "NO_EOS_OR_TRUNCATION"),
                             ("eos_token_ids", [99]), ("native_ok", False),
                             ("effective_generation_config", {**r.DECODING, "max_new_tokens": 513})):
            raw = envelope()
            raw[field] = value
            self.path.mkdir(exist_ok=True)
            path = self.path / field
            if path.exists():
                path = self.path / (field + "-bool")
            parser = Mock()
            with patch.dict(r.PARSERS, {"qwen3": parser}), self.assertRaises(ValueError):
                r.persist_then_parse(path, r.encode(raw), {}, "qwen3", PLAN["query_labels"])
            self.assertEqual((path / "raw.json").read_bytes(), r.encode(raw))
            parser.assert_not_called()

    def test_budget_boundary_and_no_manual_eos_repair(self):
        raw = envelope()
        raw["continuation_ids"] = [10] * 511 + [1]
        raw["generated_ids_full"] = [900] + raw["continuation_ids"]
        r.validate_continuation(raw)
        raw["continuation_ids"].insert(0, 10)
        raw["generated_ids_full"] = [900] + raw["continuation_ids"]
        with self.assertRaisesRegex(ValueError, "TOKEN_BOUNDARY"):
            r.validate_continuation(raw)


class RunTests(unittest.TestCase):
    def run_fake(self, model, malformed_at=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, raw in IMAGES.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        runtime = FakeRuntime(model, malformed_at)
        env = {"git_commit": "FAKE_OFFLINE_TEST", "software_versions": {}, "hardware": []}
        with patch.object(r, "frozen", return_value=(PLAN, MANIFEST, {})), patch.object(r, "text_hash", return_value="0" * 64):
            result = r.run_calls(root, model, "fake-run", env, runtime, ["OFFLINE_FAKE"])
        return root, runtime, result

    def test_both_models_twelve_calls_fixed_prompt_and_pending_review(self):
        for model in r.MODELS:
            with self.subTest(model=model):
                root, runtime, result = self.run_fake(model)
                self.assertEqual(runtime.count, 12)
                self.assertEqual(runtime.loads, 1)
                self.assertEqual(set(runtime.prompts), {r.prompt(model, PLAN["query_labels"])})
                self.assertEqual(result["final_verdict"], "PENDING_REVIEW")
                self.assertEqual(len(result["calls"]), 12)
                self.assertTrue(result["tracking_result"])
                self.assertTrue(result["artifact_audit_complete"])
                index = r.read_json(root / r.RUN_ROOT / "fake-run/artifact_index.json")
                for name, receipt in index.items():
                    r.verified_read(root / r.RUN_ROOT / "fake-run" / name, receipt)

    def test_failure_stops_without_retry_or_fabricating_remaining_calls(self):
        _, runtime, result = self.run_fake("qwen3", malformed_at=2)
        self.assertEqual(runtime.count, 3)
        self.assertEqual(len(result["calls"]), 2)
        self.assertEqual(result["final_verdict"], "FAIL")
        self.assertFalse(result["artifact_audit_complete"])

    def test_pass_requires_all_detections_individually_reviewed(self):
        _, _, result = self.run_fake("qwen3")
        reviews = r.review_template(result["calls"])
        self.assertEqual(len(reviews), 21)
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews), "PENDING_REVIEW")
        for row in reviews:
            row.update(reviewer="Human A", rationale="Box bounds checked visually against object", decision="NO_GIANT")
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews), "PASS")
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews[:-1]), "PENDING_REVIEW")
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews + [reviews[0]]), "FAIL")
        reviews[0]["decision"] = "GIANT"
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews), "FAIL")

    def test_review_hash_mismatch_empty_rationale_and_partial_run_no_pass(self):
        _, _, result = self.run_fake("paligemma")
        reviews = r.review_template(result["calls"])
        for row in reviews:
            row.update(reviewer="Human", rationale="Checked", decision="NO_GIANT")
        bad = deepcopy(reviews)
        bad[0]["raw_sha256"] = "changed"
        self.assertEqual(r.verdict(result, MANIFEST["cases"], bad), "FAIL")
        bad = deepcopy(reviews)
        bad[0]["rationale"] = " "
        self.assertEqual(r.verdict(result, MANIFEST["cases"], bad), "PENDING_REVIEW")
        result["calls"].pop()
        self.assertEqual(r.verdict(result, MANIFEST["cases"], reviews), "FAIL")

    def test_prep_result_cannot_pass(self):
        self.assertEqual(r.verdict({"QUALIFICATION_EXECUTION": "NOT_RUN"}, MANIFEST["cases"], []), "BLOCKED")

    def test_result_schema_writer_guards(self):
        _, _, result = self.run_fake("qwen3")
        r.validate_result(result)
        schema = r.read_json(ROOT / "schemas/grounding_multicategory_result.v1.schema.json")
        self.assertEqual(set(schema["required"]), set(result))
        for field, value in (("final_verdict", "PASS"), ("final_verdict", "PARTIAL_PASS"), ("native_calls", 13)):
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                r.validate_result({**result, field: value})

    def test_finalize_append_only_and_artifact_tamper_blocks(self):
        root, _, result = self.run_fake("qwen3")
        reviews = r.review_template(result["calls"])
        with patch.object(r, "frozen", return_value=(PLAN, MANIFEST, {})):
            with self.assertRaisesRegex(ValueError, "REVIEW_RUN_MODEL_IDENTITY"):
                r.finalize(root, "paligemma", "fake-run", reviews)
            final = r.finalize(root, "qwen3", "fake-run", reviews)
            self.assertEqual(final["final_verdict"], "PENDING_REVIEW")
            with self.assertRaises(FileExistsError):
                r.finalize(root, "qwen3", "fake-run", reviews)
            (root / r.RUN_ROOT / "fake-run/A_1/raw.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "STORAGE_HASH_OR_SIZE"):
                r.finalize(root, "qwen3", "fake-run", reviews)


class NativeTests(unittest.TestCase):
    def test_loader_uses_pinned_local_model_processor_and_config(self):
        for key in r.MODELS:
            processor = type("Qwen3VLProcessor" if key == "qwen3" else "PaliGemmaProcessor", (), {})()
            if key == "paligemma":
                processor.tokenizer = type("GemmaTokenizerFast", (), {})()
                processor.image_processor = type("SiglipImageProcessor", (), {"size": {"height": 448, "width": 448}})()
            config = SimpleNamespace(eos_token_id=1)
            def update(**kwargs):
                for name, value in kwargs.items():
                    setattr(config, name, value)
            config.update = update
            config.to_dict = lambda: {k: v for k, v in vars(config).items() if not callable(v)}
            model = Mock(generation_config=config, model=SimpleNamespace(rope_deltas=None))
            model.parameters.return_value = [SimpleNamespace(device=SimpleNamespace(type="cuda"), dtype="FP16")]
            factories = {name: Mock() for name in ("AutoProcessor", "Qwen3VLForConditionalGeneration", "PaliGemmaForConditionalGeneration")}
            factories["AutoProcessor"].from_pretrained.return_value = processor
            selected = factories["Qwen3VLForConditionalGeneration" if key == "qwen3" else "PaliGemmaForConditionalGeneration"]
            selected.from_pretrained.return_value = (model, {})
            native = r.NativeRuntime(ROOT, key, {"snapshot": "data/processed/fake-snapshot"})
            with patch.dict(sys.modules, {"torch": SimpleNamespace(float16="FP16"), "transformers": SimpleNamespace(**factories)}), \
                 patch.object(r, "deepcopy", side_effect=lambda value: value):
                native.load()
            for factory in (factories["AutoProcessor"], selected):
                kwargs = factory.from_pretrained.call_args.kwargs
                self.assertEqual(kwargs["revision"], r.MODELS[key][1])
                self.assertTrue(kwargs["local_files_only"])
                self.assertFalse(kwargs["trust_remote_code"])
                factory.from_pretrained.assert_called_once()
            self.assertEqual(native.effective["max_new_tokens"], 512)
            self.assertFalse(native.effective["do_sample"])
            self.assertFalse(native.effective["use_cache"])
            self.assertEqual(native.effective["num_beams"], 1)

    def test_native_continuation_only_decode_and_one_generate_both_models(self):
        for key in r.MODELS:
            native = r.NativeRuntime(ROOT, key, {})
            prefix = [99, 100]
            text = r.prompt(key, PLAN["query_labels"])
            class Tensor:
                shape = (1, 3, 448, 448)
                def tolist(self):
                    return [prefix]
            class Inputs(dict):
                def to(self, *args, **kwargs):
                    return self
            inputs = Inputs(input_ids=Tensor(), pixel_values=Tensor())
            processor = Mock()
            if key == "qwen3":
                inputs["image_grid_thw"] = SimpleNamespace(tolist=lambda: [[1, 16, 16]])
                processor.image_processor.patch_size = 16
            processor.apply_chat_template.return_value = inputs
            processor.return_value = inputs
            def decode(ids, **kwargs):
                self.assertFalse(kwargs["clean_up_tokenization_spaces"])
                if ids == prefix:
                    return text + "\n"
                self.assertEqual(ids, [10, 1])
                return "[]" if kwargs["skip_special_tokens"] else "[]<eos>"
            processor.decode.side_effect = decode
            native.processor = processor
            native.model = Mock(device="cuda:0", model=SimpleNamespace(rope_deltas=None))
            native.model.generate.return_value.tolist.return_value = [prefix + [10, 1]]
            native.torch = SimpleNamespace(float16="FP16", inference_mode=nullcontext)
            native.config = SimpleNamespace(**r.DECODING)
            native.effective, native.eos_ids = r.DECODING, [1]
            raw = json.loads(native.generate(next(iter(IMAGES.values())), text))
            r.validate_continuation(raw)
            self.assertEqual(native.count, 1)
            native.model.generate.assert_called_once()
            config = native.model.generate.call_args.kwargs["generation_config"]
            self.assertEqual(config.max_new_tokens, 512)
            self.assertFalse(config.do_sample)
            self.assertEqual(raw["generated_ids_full"], prefix + [10, 1])
            if key == "paligemma":
                self.assertEqual(processor.call_args.kwargs["text"], text)
                self.assertNotIn("\n", processor.call_args.kwargs["text"])
            else:
                self.assertEqual(processor.apply_chat_template.call_args.args[0][0]["content"][1]["text"], text)


if __name__ == "__main__":
    unittest.main()
