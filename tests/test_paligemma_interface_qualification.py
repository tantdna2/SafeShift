"""CPU/fake-only D9R10 qualification contract tests; never import torch."""

from copy import deepcopy
from io import BytesIO
import hashlib
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from scripts import w2_paligemma_interface_qualification as q
from safeshift.runners import paligemma as pg
from safeshift.runners import storage
from safeshift.runners.paligemma_snapshot import ROOT, json_bytes
from tests import test_paligemma_prep as fakes


class PlanTests(unittest.TestCase):
    def test_identity_counts_prompts_and_preserved_boundaries(self):
        plan = q.qualification_plan()
        self.assertEqual(plan["base_sha"], "93a8f32ad8c7d10a28cb3e4b62232cd3697bd0e1")
        self.assertEqual(plan["model_id"], "google/paligemma-3b-mix-448")
        self.assertEqual(plan["revision"], "ead2d9a35598cb89119af004f5d023b311d1c4a1")
        self.assertEqual([c["case_id"] for c in plan["cases"]],
                         ["cls_a", "cls_b", "cls_c", "cls_d", "grd_a", "grd_b", "grd_c", "grd_d"])
        self.assertEqual([c["task_type"] for c in plan["cases"]], ["classification"] * 4 + ["grounding"] * 4)
        self.assertEqual(plan["prompts"]["classification_presence_v1"]["text"],
                         "answer en Is there a red square in the image?")
        self.assertEqual(plan["prompts"]["grounding_detection_v1"]["text"], "detect red square")
        first, repeat = plan["cases"][0], plan["cases"][3]
        self.assertEqual((first["fixture_id"], first["prompt_id"]), (repeat["fixture_id"], repeat["prompt_id"]))
        self.assertFalse(plan["runtime"]["automatic_retry"])
        self.assertFalse(plan["runtime"]["adaptive_prompt_tuning"])
        self.assertEqual(plan["preserved_status"]["classification_interface"], "PENDING_QUALIFICATION")
        self.assertEqual(plan["preserved_status"]["grounding"], "PENDING_QUALIFICATION")
        self.assertEqual(plan["preserved_status"]["real_runtime_status"], "RUNTIME_SMOKE_PASS")
        for field in ("synthetic_v1", "inspecsafe", "promotion", "protocol_freeze", "benchmark_score",
                      "fabricated_boxes", "point_to_box", "artificial_zero_iou"):
            self.assertIs(plan["interpretation"][field], False)

    def test_deterministic_geometry_and_no_embedded_answers(self):
        from PIL import Image, ImageChops
        plan = q.qualification_plan()
        a, b = list(q.fixtures(plan)), list(q.fixtures(plan))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 4)
        for _, raw, meta in a:
            image = Image.open(BytesIO(raw))
            background = Image.new("RGB", image.size, "white")
            self.assertEqual(list(ImageChops.difference(image, background).getbbox()), meta["bbox_xyxy"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), meta["png_sha256"])
            self.assertEqual(hashlib.sha256(image.tobytes()).hexdigest(), meta["pixel_sha256"])
            self.assertNotIn("expected_answer", meta)
        left, right, small, negative = [m for _, _, m in a]
        self.assertEqual(left["bbox_xyxy"][2] - left["bbox_xyxy"][0],
                         right["bbox_xyxy"][2] - right["bbox_xyxy"][0])
        self.assertLess(small["bbox_xyxy"][2] - small["bbox_xyxy"][0], 128)
        self.assertEqual(negative["fill"], [0, 0, 255])

    def test_observes_empty_eos_text_malformed_and_hallucination_without_policy(self):
        for text, ids in (("", []), ("<eos>", [1]), ("None", [100]),
                          ("<loc9999><loc0001>", [256001]),
                          ("<loc0000><loc0001><loc1023><loc1022> red square<eos>",
                           [256000, 256001, 257023, 257022, 1]), (" Yes \nNO", [42, 43])):
            with self.subTest(text=text):
                native = {"continuation_ids": ids, "decoded_text": text,
                          "decoded_with_special_tokens": text}
                observed = q.observe(json_bytes(native))
                self.assertEqual(observed["native_output"], native)
                self.assertIsNone(observed["parser_candidate"]["canonical_output"])
                self.assertFalse(observed["parser_candidate"]["executed"])
                self.assertNotIn("boxes", observed)
                self.assertIn("NO_EMPTY_LIST_COERCION", observed["no_detection_policy"])
        self.assertEqual(q.observe(json_bytes(native))["status"], "OBSERVED_ONLY")

    def test_documentary_mapping_no_clamp_rescale_or_repair(self):
        self.assertEqual(pg.loc_values_to_d4([0, 1, 1023, 1022]), [1/1024, 0, 1022/1024, 1023/1024])
        for values in ([0, 0, 1024, 1023], [100, 100, 0, 0], [0, 1, 2], [0., 1, 2, 3], [True, 1, 2, 3]):
            with self.assertRaisesRegex(ValueError, "PARSER_FAIL_NO_REPAIR"):
                pg.loc_values_to_d4(values)
        self.assertFalse(q.qualification_plan()["documentary_mapping"]["runtime_parser_enabled"])


class HarnessTests(unittest.TestCase):
    def setUp(self):
        # Reuse the audited fake backend; no real torch/model or snapshot bytes.
        fakes.RunnerTests.setUp(self)
        for name in (q.PLAN, "scripts/w2_paligemma_interface_qualification.py"):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.stack.enter_context(patch.dict(os.environ, CUDA_VISIBLE_DEVICES="0", CUDA_DEVICE_ORDER="PCI_BUS_ID"))
        for name in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
            self.stack.enter_context(patch.dict(os.environ, {name: ""}))
        self.stack.enter_context(patch.object(q, "checkout_gate", return_value="a" * 40))
        self.stack.enter_context(patch.object(q.subprocess, "run"))
        self.stack.enter_context(patch.object(q.platform, "system", return_value="Linux"))
        self.stack.enter_context(patch.object(q.platform, "machine", return_value="x86_64"))
        self.stack.enter_context(patch.object(q, "software_versions", return_value=self.ctx.software_versions))

    def run_harness(self, **kwargs):
        return q.run_qualification(expected_commit="a" * 40, venue_internet_off=kwargs.pop("offline", True),
                                   repo=self.repo, runner_factory=lambda **_: self.runner,
                                   torch_module=self.torch, **kwargs)

    def test_one_load_exact_eight_independent_calls_raw_before_observer(self):
        events = []
        original_fsync, original_read, original_observe = os.fsync, Path.read_bytes, q.observe
        def fsync(fd):
            events.append("fsync")
            return original_fsync(fd)
        def read(path):
            value = original_read(path)
            if path.name == "response.raw":
                events.append("reread")
            return value
        def observe(raw):
            self.assertEqual(events[-1], "reread")
            self.assertGreaterEqual(events.count("fsync"), 2)
            events.append("observe")
            return original_observe(raw)
        with patch.object(storage.os, "fsync", side_effect=fsync), patch.object(Path, "read_bytes", read), \
                patch.object(q, "observe", side_effect=observe), \
                patch.object(self.runner, "load", wraps=self.runner.load) as load:
            report = self.run_harness()
        self.assertEqual(report["status"], q.COMPLETE)
        self.assertEqual(load.call_count, 1)
        self.assertEqual((report["model_load_count"], report["native_generate_calls"]), (1, 8))
        self.assertEqual(self.model.generate_count, 8)
        self.assertEqual(events.count("observe"), 8)
        self.assertEqual(self.processor.prompts, ["answer en Is there a red square in the image?"] * 4
                         + ["detect red square"] * 4)
        self.assertEqual(len({id(i) for i in self.processor.prepared}), 8)
        self.assertEqual(len({c["raw"]["path"] for c in report["calls"]}), 8)
        for call in report["calls"]:
            raw_path = self.repo / call["raw"]["path"]
            meta = json.loads((raw_path.parent / "metadata.json").read_bytes())
            self.assertEqual(meta["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(meta["call_id"], call["case_id"])
            self.assertEqual(q.sha256_file(raw_path), call["raw"]["sha256"])
        with self.assertRaises(FileExistsError):
            self.run_harness()  # Fixed attempt cannot be retried.

    def test_corrupt_reread_stops_before_observation_or_next_call(self):
        original = Path.read_bytes
        def corrupted(path):
            data = original(path)
            return data + b" " if path.name == "response.raw" else data
        with patch.object(Path, "read_bytes", corrupted), patch.object(q, "observe") as observer:
            report = self.run_harness()
        self.assertEqual(report["status"], q.STOP)
        observer.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_fsync_failure_stops_before_observer(self):
        original = storage._write_new
        def fail(path, content):
            if path.name == "response.raw":
                with patch.object(storage.os, "fsync", side_effect=OSError("fake fsync failure")):
                    return original(path, content)
            return original(path, content)
        with patch.object(storage, "_write_new", side_effect=fail), patch.object(q, "observe") as observer:
            report = self.run_harness()
        self.assertEqual(report["status"], q.STOP)
        observer.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)

    def test_partial_native_ids_persisted_on_decode_failure_no_retry(self):
        self.processor.decode_error = ValueError("fake malformed decode")
        with patch.object(q, "observe") as observer:
            report = self.run_harness()
        self.assertEqual(report["status"], q.STOP)
        observer.assert_not_called()
        self.assertEqual(self.model.generate_count, 1)
        raw_files = list((self.repo / q.ARTIFACTS).rglob("response.raw"))
        self.assertEqual(len(raw_files), 1)
        self.assertIn("generated_ids_full", json.loads(raw_files[0].read_bytes()))

    def test_offline_barrier_fail_closed(self):
        report = self.run_harness(offline=False)
        self.assertEqual(report["status"], q.STOP)
        self.assertEqual(report["model_load_count"], 0)
        self.assertEqual(report["native_generate_calls"], 0)

    def test_mask_rejected_before_load(self):
        with patch.dict(os.environ, CUDA_VISIBLE_DEVICES="0,1"):
            report = self.run_harness()
        self.assertEqual(report["status"], q.STOP)
        self.assertEqual(self.model.generate_count, 0)

    def test_plan_mutation_rejected_before_load(self):
        # Test fixtures may write only in their temporary directory.
        with (self.repo / q.PLAN).open("ab") as stream:
            stream.write(b" ")
        report = self.run_harness()
        self.assertEqual(report["status"], q.STOP)
        self.assertEqual(report["failure"]["stage"], "PLAN")
        self.assertEqual(self.model.generate_count, 0)


if __name__ == "__main__":
    unittest.main()
