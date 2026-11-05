"""CPU synthetic cohort/controller tests. No real data/model/GPU."""
import copy
import os
from pathlib import Path
import tempfile
import time
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift import internvl3763 as r
from safeshift.candidates.fulltrain_run import synthetic_cohort, synthetic_bytes
from safeshift.pilot.artifacts import write, sha, read
from safeshift.pilot.contract import digest


class PreparedControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = synthetic_cohort()

    def plan(self, history=None, **kwargs):
        return r.plan(self.cohort, history or [], action="initial", run_id="synthetic-run",
            attempt_id="synthetic-a1", max_calls=kwargs.get("max_calls", 3), max_seconds=10)

    def backend(self, response='{"safety_level":"Level02"}', fail=False):
        def generate(image, sample, binding, deadline):
            write(sample / "native_call.json", {"binding": binding})
            if fail:
                raise RuntimeError("SYNTHETIC_NATIVE_ERROR")
            raw = {"binding": binding, "response": response, "hnlo": None, "hnlo_status": r.HNLO_STATUS,
                "evidence_kind": "SYNTHETIC", "notice": "SYNTHETIC CONTROLLER FIXTURE"}
            raw_hash = write(sample / "raw.json", raw)
            # Written after raw, before the controller can classify/accept completion.
            write(sample / "trace-verification.json", {"status": "SYNTHETIC_CONTROLLER_ONLY"})
            label = r.parse_label(response)
            return {"status": "SUCCESS" if label else "INVALID", "label": label,
                "raw_sha256": raw_hash, "trace_verified": True, "hnlo": None, "hnlo_status": r.HNLO_STATUS}
        return NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=generate)

    def execute(self, backend=None, p=None):
        p = p or self.plan()
        def image_path(row):
            image = self.root / f"image-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        result = r.rehearse(self.root / "attempt", self.root / "attempt.zip", self.cohort,
            p, [], lambda _: backend or self.backend(), image_path=image_path, tokenizer_sha="a" * 64)
        return result, p

    def test_exact3763_plan_new_identity_label_only_no_inheritance(self):
        p = self.plan()
        self.assertEqual(len(p["samples"]), 3763)
        self.assertEqual(p["scheduled_ordinals"], [0, 1, 2])
        self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(p["identity"]["hnlo_policy"], "LABEL_ONLY")
        self.assertFalse(p["pooling_allowed"])
        self.assertNotEqual(p["series_id"], r.capture.SERIES)

    def test_shared_controller_archive_raw_before_parse_and_full_denominator(self):
        result, p = self.execute()
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual(result["counts"], {"SUCCESS": 3, "NOT_ATTEMPTED": 3760})
        receipt = r.verify_bundle(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["scope"], "SYNTHETIC_ONLY")
        self.assertFalse(receipt["scientific_qualified"])

    def test_invalid_is_durable_no_parser_rescue(self):
        result, _ = self.execute(self.backend('```json\n{"safety_level":"Level02"}\n```'))
        self.assertEqual(result["counts"], {"INVALID": 3, "NOT_ATTEMPTED": 3760})
        self.assertIsNone(result["records"][0]["label"])

    def test_failure_is_consumed_stop_tail_export_and_no_retry(self):
        result, p = self.execute(self.backend(fail=True))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["counts"], {"TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(r.verify_bundle(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)["status"], "FAIL")
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_load_failure_keeps_zero_calls_and_exports(self):
        p = self.plan()
        def fail(_):
            raise RuntimeError("LOAD_FAILED")
        result = r.rehearse(self.root / "attempt", self.root / "attempt.zip", self.cohort,
            p, [], fail, image_path=Mock(side_effect=AssertionError), tokenizer_sha="a"*64)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertTrue((self.root / "attempt/failure.json").is_file())

    def test_resume_excludes_consumed_success_invalid_error_and_keeps_series(self):
        result, p = self.execute(self.backend('invalid'))
        h = r.sealed_history(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)
        next_plan = r.plan(self.cohort, [h], action="resume", run_id="synthetic-run2",
            attempt_id="synthetic-a2", max_calls=4, max_seconds=10)
        self.assertEqual(next_plan["scheduled_ordinals"], [3, 4, 5, 6])
        self.assertEqual(next_plan["counts"]["INVALID"], 3)
        h["series_id"] = "candidate160"
        with self.assertRaisesRegex(ValueError, "FOREIGN"):
            r.plan(self.cohort, [h], action="resume", run_id="r", attempt_id="a", max_calls=1, max_seconds=1)

    def test_all_native_routes_closed_before_io_even_with_environment_approval(self):
        from scripts.internvl3763 import main
        with patch.object(r, "read", side_effect=AssertionError("NO_IO")):
            for call in (lambda: r.worker(), lambda: r.NativeBackend(None, None, None, None),
                    lambda: r.NativeBackend.generate(None, None, None, None, None),
                    lambda: r.generate_prepared(None, None, None, None, None),
                    lambda: main(["--mode", "execute", "--output", "missing"]),
                    lambda: main(["--mode", "worker"])):
                with self.subTest(call=call), self.assertRaises(PermissionError):
                    call()

    def test_source_original_science_frozen_and_test_or_pilot_cohort_rejected(self):
        self.assertEqual(r.check_source(r.source_spec()), digest(r.source_spec()))
        bad = copy.deepcopy(self.cohort); bad["samples"] = bad["samples"][:160]
        with self.assertRaisesRegex(ValueError, "3763"):
            r.plan(bad, [], action="initial", run_id="r", attempt_id="a", max_calls=1, max_seconds=1)
        self.cohort["split"] = "TEST"
        with self.assertRaisesRegex(ValueError, "TRAIN_ONLY"):
            self.plan()

    def test_packaged_prepare_imports_with_no_repository_or_site_packages(self):
        extracted = self.root / "extracted"
        for name in r.source_spec()["manifest"]:
            path = extracted / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((r.ROOT / name).read_bytes())
        code = "import sys; sys.path.insert(0,sys.argv[1]); from scripts.internvl3763 import preparation; assert preparation()['status']=='BLOCKED'; print('ISOLATED_PREP_PASS')"
        result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(extracted)],
            cwd=extracted, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ISOLATED_PREP_PASS", result.stdout)

    def test_export_reserve_blocks_before_first_call_and_keeps_not_attempted(self):
        backend = self.backend()
        backend.generate = Mock(side_effect=AssertionError("NO_CALL_WITHOUT_EXPORT_SPACE"))
        with patch.object(r.shutil, "disk_usage", return_value=NS(free=0)):
            result, _ = self.execute(backend)
        backend.generate.assert_not_called()
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(read(self.root / "attempt/stop.json")["reason"], "CAPTURE_AND_EXPORT_SPACE_NOT_AVAILABLE")

    def test_noop_resume_does_not_load_or_generate(self):
        p = self.plan()
        # Handwritten synthetic HISTORY contract, not a claim of archived model outputs.
        h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": r.SERIES,
            "identity": p["identity"], "cohort_sha256": digest(self.cohort), "parent_history_sha256": digest([]),
            "action": "initial", "evidence_sha256": digest("SYNTHETIC_HISTORY_ONLY"), "repair": None,
            "records": [{**row, "status": "INVALID", "label": None, "attempts": 1,
                "native_calls": 1, "raw_sha256": digest("SYNTHETIC_RAW_REFERENCE_ONLY")}
                for row in self.cohort["samples"]]}
        next_plan = r.plan(self.cohort, [h], action="resume", run_id="noop", attempt_id="noop-a",
            max_calls=1, max_seconds=10)
        self.assertEqual(next_plan["scheduled_ordinals"], [])
        factory = Mock(side_effect=AssertionError("NO_NOOP_LOAD"))
        receipt = r.rehearse(self.root / "noop", self.root / "noop.zip", self.cohort,
            next_plan, [h], factory, image_path=Mock(side_effect=AssertionError), tokenizer_sha="a"*64)
        self.assertEqual(receipt["model_calls"], 0)
        factory.assert_not_called()


@unittest.skipUnless(os.environ.get("SAFESHIFT3763_NATIVE_CPU") == "1", "opt-in CPU torch/transformers")
class NativeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_internvl_v2_runtime import NativeCaptureTests as Helper
        Helper.setUpClass()
        cls.helper = Helper("test_all_labels_actual_generate_full_raw_before_processor_and_parse")
        cls.torch = Helper.torch

    def call(self, backend, folder):
        binding = {k: digest("SYNTHETIC-" + k) for k in r.trace_binding({},
            {"series_id": r.SERIES}, {"ordinal": 0, "image_sha256": "a"*64}, "b"*64)}
        inputs = {"input_ids": self.torch.tensor([[8]]),
            "attention_mask": self.torch.ones((1, 1), dtype=self.torch.long)}
        with patch.object(r, "authorize", return_value={"scope": "SYNTHETIC_CLAIM_ONLY"}):
            return r.generate_prepared(backend, inputs, folder, binding, time.monotonic() + 30, ordinal=0)

    def test_actual_native_generate_all_labels_full_capture_and_raw_precedes_parse(self):
        for level in range(4):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                backend = self.helper.backend(level)
                parser = r.parse_label
                def checked_parse(text):
                    self.assertTrue((folder / "raw.json").is_file())
                    self.assertTrue((folder / "native_call.json").is_file())
                    return parser(text)
                with patch.object(r, "parse_label", checked_parse):
                    result = self.call(backend, folder)
                self.assertEqual(result["label"], f"Level0{level+1}")
                self.assertTrue(result["trace_verified"])
                self.assertEqual(read(folder / "raw.json")["evidence_kind"], "SYNTHETIC")
                self.assertTrue(read(folder / "trace-verification.json")["forced_steps"])
                self.assertEqual((folder / "steps/000.f32").stat().st_size, 4 * backend.logit_width)
                self.assertFalse(backend.model._forward_hooks)

    def test_native_invalid_keeps_raw_and_failure_without_rescue(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = self.helper.backend()
            decode = backend.tokenizer.decode
            def changed(ids, **kwargs):
                text = decode(ids, **kwargs)
                return "```json\n" + text + "\n```" if (folder / "native.json").exists() else text
            with patch.object(backend.tokenizer, "decode", changed):
                result = self.call(backend, folder)
            self.assertEqual(result["status"], "INVALID")
            self.assertFalse(result["trace_verified"])
            self.assertTrue(read(folder / "raw.json")["response"].startswith("```"))

    def test_native_nonfinite_keeps_consumed_marker_and_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = self.helper.backend(defect="nonfinite")
            with self.assertRaisesRegex(ValueError, "NONFINITE"):
                self.call(backend, folder)
            self.assertTrue((folder / "native_call.json").is_file())
            self.assertTrue((folder / "steps/000.f32").is_file())
            self.assertFalse(backend.model._forward_hooks)


if __name__ == "__main__":
    unittest.main()
