"""CPU synthetic integration. Never load weights or read real images/history."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from safeshift import internvl_v2_runtime as runtime
from safeshift.pilot.artifacts import read, write, sha, export, verify_archive
from safeshift.pilot.contract import digest
from scripts import internvl_v2 as cli
from test_internvl_grammar import CharacterTokenizer

ROOT = Path(__file__).resolve().parents[1]


def request(spec, image_hash="a" * 64):
    return {"schema": runtime.IDENTITY + "-request", "identity": runtime.IDENTITY,
        "series_id": runtime.SERIES, "attempt_id": "attempt-0001", "split": "TRAIN", "ordinal": 0,
        "sample_id": "SYNTHETIC", "image": "synthetic.png", "image_sha256": image_hash,
        "source_sha256": digest(spec), "limits": dict(runtime.LIMITS)}


class ContractTests(unittest.TestCase):
    def test_all_native_entrypoints_fenced_before_io(self):
        calls = [lambda: runtime.NativeBackend("missing", "missing"),
            lambda: runtime.generate_prepared(None, None, None, None, None),
            lambda: runtime.NativeBackend.generate(None, None, None, None, None),
            lambda: runtime.execute_attempt(None, None, None, None, None, None, None),
            lambda: cli.launch(None, mode="execute"),
            lambda: cli.worker("native", None, None, None, None),
            lambda: cli.main(["--spec", "missing", "--mode", "execute"]),
            lambda: cli.main(["--spec", "missing", "--worker", "native"])]
        with patch.dict(os.environ, {"SAFESHIFT_APPROVED": "1"}), patch.object(runtime, "read", side_effect=AssertionError):
            for call in calls:
                with self.subTest(call=call), self.assertRaises(PermissionError):
                    call()

    def test_source_and_approved_bytes(self):
        spec = runtime.source_spec()
        self.assertEqual(runtime.check_source(spec), digest(spec))
        changed = copy.deepcopy(spec)
        changed["manifest"]["safeshift/internvl_v2_runtime.py"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_HASH"):
            runtime.check_source(changed)
        changed = copy.deepcopy(spec)
        changed["manifest"].pop("safeshift/internvl_grammar.py")
        with self.assertRaisesRegex(ValueError, "INVENTORY"):
            runtime.check_source(changed)

    def test_packaged_source_imports_offline_without_repository_or_site_packages(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in runtime.runtime_sources():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes((ROOT / name).read_bytes())
            code = "import sys; sys.path.insert(0,sys.argv[1]); from scripts import internvl_v2; internvl_v2.runtime.check_source(internvl_v2.runtime.source_spec()); print('ISOLATED_IMPORT_PASS')"
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("ISOLATED_IMPORT_PASS", result.stdout)

    def test_manifest_rejects_history_full_cohort_other_split_and_extra_authority(self):
        spec = runtime.source_spec()
        valid = request(spec)
        self.assertEqual(runtime.request_binding(spec, valid), digest(valid))
        for field, value in (("series_id", "candidate160"), ("split", "TEST"), ("ordinal", 1),
                             ("ordinal", False), ("image", "../secret"), ("source_sha256", "0" * 64),
                             ("attempt_id", "attempt-0002"), ("approved", True), ("history", []),
                             ("limits", {**runtime.LIMITS, "calls": 3763})):
            bad = {**valid, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                runtime.request_binding(spec, bad)

    def test_padding_does_not_change_paths_and_is_always_masked(self):
        t = CharacterTokenizer()
        native = runtime.native_grammar(t, 0, [8], len(t))
        full = runtime.native_grammar(t, 0, [8], len(t) + 4)
        self.assertEqual(native.receipt(), full.receipt())
        for p in full.paths:
            for i in range(len(p) + 1):
                self.assertTrue(all(x < len(t) for x in full.allowed(p[:i])))
        for width in (127, 200001, True):
            with self.assertRaises(ValueError):
                runtime.native_grammar(t, 0, [8], width)

    def test_native_vocabulary_length_is_not_recomputed_for_every_input_token(self):
        class Counted(CharacterTokenizer):
            count = 0
            def __len__(self):
                self.count += 1
                return super().__len__()
        tokenizer = Counted()
        runtime.native_grammar(tokenizer, 0, [8] * 3000, 132)
        # Constructors call len a fixed number of times; input length must not
        # cause thousands of expensive native vocabulary materializations.
        self.assertLess(tokenizer.count, 200)

    def test_cli_path_types_and_command_roundtrip(self):
        with patch.object(cli, "read", return_value={}), patch.object(cli, "worker") as worker:
            self.assertEqual(cli.main(["--spec", "spec", "--worker", "setup", "--inputs", "inputs",
                "--output", "out", "--scratch", "scratch"]), 0)
            self.assertTrue(all(isinstance(p, Path) for p in worker.call_args.args[2:5]))
        command = cli.worker_command("python", "native", "s", "o", "t", "i", "r", 1.0)
        self.assertIn("--deadline", command)
        self.assertEqual(command[command.index("--request") + 1], "r")

    def test_duplicate_missing_wrong_checkpoint_markers(self):
        from safeshift.candidates.train_inputs import checkpoint
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                checkpoint(root, "internvl35")
            for name in ("a", "b"):
                write(root / name / "candidate_checkpoint_internvl35.json", {})
            with self.assertRaisesRegex(ValueError, "FOUND_2"):
                checkpoint(root, "internvl35")
        with tempfile.TemporaryDirectory() as d:
            write(Path(d) / "a/candidate_checkpoint_internvl35.json", {})
            with self.assertRaisesRegex(ValueError, "OFFICIAL_CHECKPOINT_MARKER"):
                checkpoint(d, "internvl35")

    def test_load_failure_preserved_and_cannot_replay(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runtime, "authorize"), patch.object(runtime, "check_source"):
            root = Path(d); out = root / "out"; out.mkdir()
            (root / "synthetic.png").write_bytes(b"SYNTHETIC_ONLY")
            (root / "tokenizer.json").write_text("{}")
            spec = runtime.source_spec(); r = request(spec, sha(root / "synthetic.png"))
            calls = []
            def factory(*unused):
                calls.append(1)
                raise RuntimeError("SYNTHETIC_LOAD_ERROR")
            with self.assertRaises(RuntimeError):
                runtime.execute_attempt(spec, r, root, out, root, root, time.monotonic() + 30, factory=factory)
            with self.assertRaises(FileExistsError):
                runtime.execute_attempt(spec, r, root, out, root, root, time.monotonic() + 30, factory=factory)
            result = runtime.summary(out, {"type": "RuntimeError"})
            self.assertEqual((result["load_reservations"], result["native_call_markers"]), (1, 0))
            self.assertEqual(len(calls), 1)
            archive = root / "failed.zip"; export(out, archive)
            self.assertIn("load-reservation.json", verify_archive(archive))

    def test_image_hash_and_deadline_fail_before_load(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runtime, "authorize"), patch.object(runtime, "check_source"):
            root = Path(d); (root / "synthetic.png").write_bytes(b"SYNTHETIC")
            spec = runtime.source_spec()
            for deadline, expected in ((time.monotonic() - 1, "DEADLINE"), (time.monotonic() + 5, "IMAGE_HASH")):
                out = root / expected; out.mkdir()
                with self.assertRaisesRegex(ValueError, expected):
                    runtime.execute_attempt(spec, request(spec), root, out, root, root, deadline,
                                            factory=lambda *a: self.fail("no load"))

    def test_preflight_repeat_no_attempt_and_error_archive(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runtime, "check_source"), \
                patch.object(cli.environment, "resources", return_value={}), \
                patch.object(cli.supervision, "run", side_effect=OSError("SYNTHETIC_LOG_ERROR")):
            root = Path(d)
            for _ in range(2):
                result = cli.launch({}, output=root / "out", scratch_parent=root / "scratch")
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual((result["loads"], result["calls"], result["owner_slots_consumed"]), (0, 0, 0))
                self.assertEqual(result["error"]["type"], "OSError")
            archives = list((root / "out").glob("*.zip"))
            self.assertEqual(len(archives), 2)
            for archive in archives:
                self.assertFalse(any("attempt" in n or "reservation" in n for n in verify_archive(archive)))

    def test_preflight_worker_stage_gates_and_failures_before_any_load(self):
        from contextlib import ExitStack
        from scripts import smoke_kaggle173 as smoke
        from safeshift.fulltrain import preflight
        for failed in (None, "software", "resources", "cuda", "checkpoint", "processor", "allocation", "driver"):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                root = Path(d)
                stack.enter_context(patch.object(runtime, "check_source"))
                funcs = {"software": (cli.environment, "software"), "resources": (cli.environment, "resources"),
                         "cuda": (cli.environment, "cuda"), "checkpoint": (cli, "check_checkpoint"),
                         "processor": (cli, "processor_check"), "allocation": (preflight, "storage_probe"),
                         "driver": (smoke, "driver_check")}
                stack.enter_context(patch.object(smoke, "bind_cuda_driver"))
                load = stack.enter_context(patch.object(runtime, "NativeBackend", side_effect=AssertionError("NO_LOAD")))
                for key, (module, name) in funcs.items():
                    stack.enter_context(patch.object(module, name, side_effect=ValueError("SYNTHETIC_" + key)
                        if failed == key else None, return_value=(root, root) if key == "checkpoint" else {}))
                if failed:
                    with self.assertRaises(ValueError):
                        cli.worker("preflight", {}, root, root, root)
                    self.assertFalse((root / "preflight.json").exists())
                else:
                    cli.worker("preflight", {}, root, root, root)
                    self.assertEqual(read(root / "preflight.json")["calls"], 0)
                load.assert_not_called()

    def test_synthetic_controller_child_result_and_unknown_partial(self):
        # Same supervisor command construction and archive/controller logic;
        # simulate only the external child boundary, never hardware or weights.
        for terminal in (True, False):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as d, \
                    patch.object(runtime, "check_source"), patch.object(cli.environment, "resources", return_value={}):
                root = Path(d)
                def child(command, **kwargs):
                    stage = command[command.index("--worker") + 1]
                    out = Path(command[command.index("--output") + 1])
                    if stage == "setup":
                        write(out / "runtime.json", {"python": sys.executable, "env": {}})
                    elif terminal:
                        write(out / "preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS", "calls": 0})
                    write(kwargs["receipt"], {"status": "EXITED", "synthetic": True})
                with patch.object(cli.supervision, "run", child):
                    result = cli.launch({}, output=root / "out", scratch_parent=root / "scratch")
                self.assertEqual(result["status"], "LIVE_GPU_PREFLIGHT_PASS" if terminal else "BLOCKED")
                self.assertIsNone(result["execution_authority"])

    def test_archive_mutation_rejected(self):
        import zipfile
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); out = root / "out"; out.mkdir()
            write(out / "raw.json", {"synthetic": True}); archive = root / "test.zip"
            export(out, archive)
            with zipfile.ZipFile(archive, "a") as z:
                z.writestr("unexpected.json", "{}")
            with self.assertRaises(ValueError):
                verify_archive(archive)


@unittest.skipUnless(os.environ.get("SAFESHIFT_V2_NATIVE_CPU") == "1", "opt-in CPU torch/transformers only")
class NativeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch, transformers
        cls.torch, cls.tr = torch, transformers
        torch.set_num_threads(1)
        assert transformers.__version__ == "4.55.4"

    def backend(self, label=0, defect=None, tokenizer=None, width=None):
        torch, tr = self.torch, self.tr
        t = tokenizer or CharacterTokenizer()
        width = width or len(t) + 4  # Exercise padded output head, too.
        text = '{"safety_level":"Level0' + str(label + 1) + '"}'
        tokens = t.encode(text, add_special_tokens=False) + [getattr(t, "eos_token_id", 0)]
        class Scripted(tr.PreTrainedModel, tr.GenerationMixin):
            config_class = tr.PretrainedConfig
            def __init__(inner):
                super().__init__(tr.PretrainedConfig(is_decoder=True, vocab_size=width))
                inner.anchor = torch.nn.Parameter(torch.zeros(1), requires_grad=False)
                inner.steps = 0
            def prepare_inputs_for_generation(inner, input_ids, **kwargs):
                return {"input_ids": input_ids}
            def forward(inner, input_ids=None, attention_mask=None, pixel_values=None, **kwargs):
                if defect == "forward":
                    raise RuntimeError("SYNTHETIC_FORWARD_ERROR")
                if defect == "timeout":
                    time.sleep(.03)
                logits = torch.full((1, 1, width), -7.)
                logits[0, 0, tokens[inner.steps]] = 2.
                logits[0, 0, width - 1] = 9.  # Always prefers a padded/disallowed token.
                if defect == "nonfinite":
                    logits[0, 0, 0] = float("nan")
                inner.steps += 1
                return tr.modeling_outputs.CausalLMOutputWithPast(logits=logits)
        model = Scripted().eval()
        model.generation_config = tr.GenerationConfig(eos_token_id=tokens[-1], pad_token_id=tokens[-1])
        from safeshift.candidates.backend import generation_config
        generation = generation_config(model, t, "internvl35")
        return NS(key="internvl35", tokenizer=t, cpu_tokenizer=t, model=model,
                  generation=generation, logit_width=width, evidence_kind="SYNTHETIC")

    def call(self, b, root, seconds=30):
        inputs = {"input_ids": self.torch.tensor([[8]]), "attention_mask": self.torch.ones((1, 1), dtype=self.torch.long)}
        binding = {k: digest("SYNTHETIC_" + k) for k in runtime.trace_binding(
            {"a": 1}, request({"a": 1}), "1" * 64)}
        with patch.object(runtime, "authorize"):
            return runtime.generate_prepared(b, inputs, root, binding, time.monotonic() + seconds)

    def test_all_labels_actual_generate_full_raw_before_processor_and_parse(self):
        for label in range(4):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as d:
                root = Path(d); b = self.backend(label)
                parser = runtime.parse_label
                def checked_parse(text):
                    self.assertTrue((root / "raw.json").is_file())
                    self.assertTrue((root / "native.json").is_file())
                    return parser(text)
                with patch.object(runtime, "parse_label", checked_parse):
                    result = self.call(b, root)
                self.assertEqual(result["status"], "SUCCESS")
                self.assertEqual(result["label"], f"Level0{label + 1}")
                self.assertIsNone(result["hnlo"])
                raw = read(root / "raw.json")
                self.assertEqual(raw["actual_logits_processors"], [runtime.PROCESSOR])
                self.assertEqual(raw["evidence_kind"], "SYNTHETIC")
                self.assertTrue(read(root / "trace-verification.json")["forced_steps"])
                self.assertEqual((root / "steps/000.f32").stat().st_size, 4 * b.logit_width)
                self.assertFalse(b.model._forward_hooks)

    def test_invalid_json_is_durable_completion_no_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); b = self.backend(); original = b.tokenizer.decode
            def decode(ids, **kw):
                if (root / "native.json").exists():
                    return "```json\n" + original(ids, **kw) + "\n```"
                return original(ids, **kw)
            with patch.object(b.tokenizer, "decode", decode):
                result = self.call(b, root)
            self.assertEqual(result["status"], "INVALID")
            self.assertFalse(result["trace_verified"])
            self.assertTrue(read(root / "raw.json")["response"].startswith("```"))

    def test_nonfinite_forward_failure_timeout_keep_partial(self):
        for defect in ("nonfinite", "forward", "timeout"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d); b = self.backend(defect=defect)
                with self.assertRaises((ValueError, RuntimeError)):
                    self.call(b, root, .1 if defect == "timeout" else 30)
                self.assertTrue((root / "native_call.json").exists())
                self.assertFalse((root / "result.json").exists())
                self.assertFalse(b.model._forward_hooks)
                if defect == "nonfinite":
                    self.assertTrue((root / "steps/000.f32").exists())

    def test_raw_write_failure_stops_before_mask(self):
        with tempfile.TemporaryDirectory() as d:
            b = self.backend()
            with patch.object(runtime, "write_bytes", side_effect=OSError("SYNTHETIC_DISK_FULL")), \
                    self.assertRaises(OSError):
                self.call(b, Path(d))
            self.assertFalse((Path(d) / "steps/000.masked.json").exists())
            self.assertEqual(b.model.steps, 1)

    def test_extra_processor_rejected_before_forward(self):
        with tempfile.TemporaryDirectory() as d:
            b = self.backend(); b.generation.repetition_penalty = 1.1
            with self.assertRaisesRegex(ValueError, "EXACT_NATIVE_PROCESSOR"):
                self.call(b, Path(d))
            self.assertEqual(b.model.steps, 0)
            self.assertTrue((Path(d) / "processors.json").exists())

    def test_early_eos_missing_eos_prefix_and_token_corruption(self):
        for defect in ("early", "missing", "prefix", "range"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                b = self.backend(); original = b.model.generate
                def changed(**kw):
                    result = original(**kw)
                    if defect == "early": result.sequences[0, 2] = 0
                    if defect == "missing": result.sequences = result.sequences[:, :-1]
                    if defect == "prefix": result.sequences[0, 0] = 9
                    if defect == "range": result.sequences[0, 2] = b.logit_width
                    return result
                with patch.object(b.model, "generate", changed):
                    if defect == "prefix":
                        with self.assertRaisesRegex(ValueError, "PREFIX_CHANGED"):
                            self.call(b, Path(d))
                    else:
                        result = self.call(b, Path(d))
                        self.assertNotEqual(result["status"], "SUCCESS")
                self.assertTrue((Path(d) / "native.json").exists())

    def test_raw_and_masked_hash_mutation(self):
        for target in ("000.f32", "000.masked.json"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as d:
                root = Path(d); original = runtime.Capture.steps
                def corrupt(capture):
                    p = root / "steps" / target
                    p.write_bytes(p.read_bytes() + b" ")
                    return original(capture)
                with patch.object(runtime.Capture, "steps", corrupt), self.assertRaisesRegex(ValueError, "HASH"):
                    self.call(self.backend(), root)
                self.assertTrue((root / "raw.json").exists())
                self.assertFalse((root / "result.json").exists())

    def test_native_public_tokenizer_padded_head_all_labels(self):
        from transformers import Qwen2TokenizerFast
        from tokenizers import Tokenizer
        source = Path(os.environ["SAFESHIFT_V2_TOKENIZER"])
        tokenizer = Qwen2TokenizerFast.from_pretrained(str(source), local_files_only=True)
        for label in range(4):
            with tempfile.TemporaryDirectory() as d:
                b = self.backend(label, tokenizer=tokenizer, width=151936)
                b.cpu_tokenizer = Tokenizer.from_file(str(source / "tokenizer.json"))
                result = self.call(b, Path(d))
                self.assertEqual(result["status"], "SUCCESS")
                self.assertEqual(len(read(Path(d) / "raw.json")["generated_ids"]), 10)

    def test_actual_preflight_processor_all_paths_without_model(self):
        with tempfile.TemporaryDirectory() as d, patch.object(runtime, "NativeBackend", side_effect=AssertionError("NO_LOAD")):
            result = cli.processor_check(Path(os.environ["SAFESHIFT_V2_SOURCE"]), Path(d))
            self.assertEqual(result["mask_steps"], 40)
            self.assertEqual((result["calls"], result["loads"]), (0, 0))
            self.assertEqual((result["logit_width"], result["tokenizer_size"]), (151936, 151679))
            self.assertFalse((Path(d) / "native_call.json").exists())

    def test_controller_to_native_generation_synthetic_image(self):
        from PIL import Image
        from safeshift.candidates.loading import native_setup
        source = Path(os.environ["SAFESHIFT_V2_SOURCE"])
        processor, tokenizer, config, _ = native_setup(source, "internvl35", {})
        from tokenizers import Tokenizer
        with tempfile.TemporaryDirectory() as d, patch.object(runtime, "authorize"):
            root = Path(d); out = root / "out"; out.mkdir()
            with Image.new("RGB", (17, 1), (40, 80, 120)) as image:
                image.save(root / "synthetic.png")
            spec = runtime.source_spec(); r = request(spec, sha(root / "synthetic.png"))
            scripted = self.backend(3, tokenizer=tokenizer, width=config.text_config.vocab_size)
            scripted.processor, scripted.config = processor, config
            scripted.prompt = (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf8")
            scripted.dtype, scripted.device = self.torch.float16, "cpu"
            scripted.cpu_tokenizer = Tokenizer.from_file(str(source / "tokenizer.json"))
            def factory(*unused):
                result = runtime.NativeBackend.__new__(runtime.NativeBackend)
                result.backend = scripted
                result.environment = {"scope": "SCRIPTED_NO_WEIGHTS", "weights_loaded": False}
                return result
            result = runtime.execute_attempt(spec, r, root, out, source, root, time.monotonic() + 60, factory=factory)
            self.assertEqual(result["status"], "SUCCESS")
            with self.assertRaises(FileExistsError):
                runtime.execute_attempt(spec, r, root, out, source, root, time.monotonic() + 60, factory=factory)
            self.assertEqual(runtime.summary(out)["native_call_markers"], 1)
            archive = root / "synthetic.zip"; export(out, archive)
            self.assertIn("sample/steps/000.f32", verify_archive(archive))


@unittest.skipUnless(sys.platform == "linux", "Linux process-group supervisor")
class SupervisorTests(unittest.TestCase):
    def run_child(self, code, seconds, cap=4096):
        from safeshift.fulltrain.supervision import run
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            try:
                run([sys.executable, "-B", "-c", code], cwd=ROOT, env={"PATH": os.environ["PATH"]},
                    deadline=time.monotonic() + seconds, log=root / "child.log", receipt=root / "supervisor.json",
                    max_log_bytes=cap)
            except RuntimeError:
                pass
            result = read(root / "supervisor.json")
            self.assertTrue(result["group_kill_sent"])
            return result

    def test_hard_timeout_kills_hanging_load(self):
        self.assertEqual(self.run_child("import time; time.sleep(60)", .3)["status"], "HARD_DEADLINE")

    def test_log_transport_budget_failure_no_retry(self):
        result = self.run_child("import sys,time; print('SYNTHETIC'*10000,flush=True); time.sleep(60)", 5)
        self.assertEqual(result["status"], "LOG_BUDGET_EXCEEDED")
        self.assertFalse(result["automatic_retry"])

    def test_child_failure_receipt(self):
        self.assertEqual(self.run_child("raise RuntimeError('SYNTHETIC')", 5)["status"], "CHILD_FAILURE")
