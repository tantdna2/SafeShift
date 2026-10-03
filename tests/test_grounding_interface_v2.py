"""Handcrafted native outputs only; no historical output, model or benchmark."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from safeshift.protocol.grounding_interface_candidate import (
    NativeDetections, PALI_ABSENCE, QWEN_ABSENCE, parse_paligemma, parse_qwen3, prompt,
)
from safeshift.protocol.grounding_interface_geometry import observe, systematic_tracking
from safeshift.protocol.schema import Evidence, strict_json
from scripts.prepare_grounding_interface_v2 import MANIFEST, build, materialize

ROOT = Path(__file__).resolve().parents[1]
PLAN = "configs/pre_freeze/grounding_interface_qualification_plan.v2.json"
LOCK = "configs/pre_freeze/grounding_interface_lock.v2.json"
BASE = "5538064e6ea015f8c15475d488064cae95461cd0"


def qwen(boxes, label="red square"):
    return json.dumps([{"bbox_2d": b, "label": label} for b in boxes])


def pali(values=(128, 256, 640, 768), label="red square"):
    return "".join(f"<loc{v:04d}>" for v in values) + " " + label


class QwenCandidateTests(unittest.TestCase):
    def test_official_shape_coordinate_order_and_mapping(self):
        result = parse_qwen3(qwen([[100, 200, 600, 800]]), label="red square")
        self.assertEqual(result, NativeDetections("SUCCESS", (Evidence((.1, .2, .6, .8), "red square"),)))

    def test_multiple_preserves_order_and_all_boxes(self):
        result = parse_qwen3(qwen([[10, 20, 30, 40], [400, 500, 700, 900]]), label="red square")
        self.assertEqual(len(result.detections), 2)
        self.assertEqual(result.detections[1].bbox, (.4, .5, .7, .9))

    def test_wrong_fields_labels_and_structures(self):
        for raw in ['{"bbox_2d":[1,2,3,4],"label":"red square"}',
                    '[{"bbox":[1,2,3,4],"label":"red square"}]',
                    '[{"point_2d":[1,2],"label":"red square"}]',
                    '[{"bbox_2d":[1,2,3,4],"label":"red square","score":1}]',
                    qwen([[1, 2, 3, 4]], "Red square"), qwen([[1, 2, 3, 4]], "red block")]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_qwen3(raw, label="red square").status, "INVALID")

    def test_strict_json_no_fences_regex_rescue_or_duplicates(self):
        good = qwen([[1, 2, 3, 4]])
        for raw in ["```json\n" + good + "\n```", "prefix " + good, good + " trailing",
                    good[:-1], "[{'bbox_2d':[1,2,3,4]}]",
                    '[{"bbox_2d":[1,2,3,4],"label":"red square","label":"red square"}]']:
            with self.subTest(raw=raw):
                self.assertEqual(parse_qwen3(raw, label="red square").status, "INVALID")

    def test_out_of_range_and_invalid_geometry_never_clamped(self):
        for box in [[-1, 0, 500, 600], [0, 0, 1001, 800], [3, 2, 1, 4],
                    [1, 2, 1, 4], [0, 1, 2, 1], [True, 1, 2, 3],
                    ["1", 2, 3, 4], [0, 0, float("inf"), 1], [0, 1, 2]]:
            with self.subTest(box=box):
                result = parse_qwen3(qwen([box]), label="red square")
                self.assertEqual(result.status, "INVALID")
                self.assertIsNone(result.detections)

    def test_no_scale_guessing_on_unit_magnitude(self):
        result = parse_qwen3(qwen([[.1, .2, .6, .8]]), label="red square")
        self.assertEqual(result.detections[0].bbox, (.0001, .0002, .0006, .0008))

    def test_range_endpoints_are_not_repaired(self):
        self.assertEqual(parse_qwen3(qwen([[0, 0, 1000, 1000]]), label="red square")
                         .detections[0].bbox, (0, 0, 1, 1))

    def test_bad_extra_detection_invalidates_whole_response(self):
        result = parse_qwen3(qwen([[10, 20, 30, 40], [1, 2, 1, 4]]), label="red square")
        self.assertEqual(result.status, "INVALID")
        self.assertIsNone(result.detections)

    def test_empty_array_is_blocked_not_absence_success(self):
        self.assertEqual(parse_qwen3("[]", label="red square"), NativeDetections("BLOCKED", error=QWEN_ABSENCE))
        for raw in ["", "null", "{}", "No objects found."]:
            self.assertEqual(parse_qwen3(raw, label="red square").status, "INVALID")


class PaliCandidateTests(unittest.TestCase):
    def test_one_mapping_and_native_label(self):
        result = parse_paligemma(pali(), label="red square")
        self.assertEqual(result, NativeDetections("SUCCESS", (Evidence((.25, .125, .75, .625), "red square"),)))

    def test_multiple_and_exact_source_supported_separators(self):
        for sep in ["; ", " ; "]:
            with self.subTest(sep=sep):
                result = parse_paligemma(pali() + sep + pali((0, 10, 100, 200)), label="red square")
                self.assertEqual(len(result.detections), 2)
                self.assertEqual(result.detections[1].bbox, (10/1024, 0, 200/1024, 100/1024))

    def test_does_not_deduplicate_or_select_first(self):
        result = parse_paligemma(" ; ".join([pali()] * 3), label="red square")
        self.assertEqual(len(result.detections), 3)

    def test_wrong_label_not_aliased(self):
        for label in ["Red square", "red block", "red square ", "red square'"]:
            self.assertEqual(parse_paligemma(pali(label=label), label="red square").status, "INVALID")

    def test_malformed_token_separator_and_unmatched_text(self):
        for raw in [pali().replace("0128", "128"), pali().replace("0128", "٠١٢٨"),
                    pali().replace(">", "> ", 1), "prefix " + pali(), pali() + "<eos>",
                    "\n" + pali(), pali() + "\n", pali() + ";", pali() + " ; ",
                    pali() + ";" + pali(), pali() + "\n" + pali(),
                    pali().replace(" red", "  red"), pali() + "<seg001>"]:
            with self.subTest(raw=raw):
                self.assertEqual(parse_paligemma(raw, label="red square").status, "INVALID")

    def test_invalid_geometry_or_range(self):
        for values in [(0, 0, 1024, 1023), (500, 100, 400, 600), (0, 20, 100, 20)]:
            self.assertEqual(parse_paligemma(pali(values), label="red square").status, "INVALID")

    def test_1023_stays_below_one(self):
        result = parse_paligemma(pali((0, 0, 1023, 1023)), label="red square")
        self.assertEqual(result.detections[0].bbox, (0, 0, 1023/1024, 1023/1024))

    def test_invalid_extra_detection_never_dropped(self):
        result = parse_paligemma(pali() + " ; " + pali((0, 0, 0, 0)), label="red square")
        self.assertEqual(result.status, "INVALID")
        self.assertIsNone(result.detections)

    def test_no_match_and_eos_not_successful_zero(self):
        self.assertEqual(parse_paligemma("", label="red square"), NativeDetections("BLOCKED", error=PALI_ABSENCE))
        for text in ["<eos>", "none", "[]", " "]:
            self.assertEqual(parse_paligemma(text, label="red square").status, "INVALID")


class SuiteAndContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = strict_json((ROOT / MANIFEST).read_bytes())
        self.plan = strict_json((ROOT / PLAN).read_bytes())

    def perfect_observations(self):
        return {case["case_id"]: observe(case, NativeDetections("SUCCESS", tuple(
            Evidence(tuple(box), case["target_label"]) for box in case["target_boxes"])))
                for case in self.manifest["cases"] if case["target_boxes"]}

    def test_ten_cases_distractors_absent_and_multi(self):
        cases = self.manifest["cases"]
        self.assertEqual([c["case_id"] for c in cases], self.plan["case_ids"])
        self.assertEqual(len(cases), 10)
        self.assertTrue(all(c["distractor_boxes"] for c in cases))
        self.assertEqual([len(c["target_boxes"]) for c in cases], [1]*8 + [0, 2])
        self.assertEqual(cases[8]["target_label"], cases[9]["target_label"])

    def test_pairs_and_tracking_include_both_diagonals(self):
        observations = self.perfect_observations()
        self.assertTrue(systematic_tracking(self.manifest["cases"], observations))
        for case_id in self.plan["case_ids"][:8]:
            wrong = deepcopy(observations)
            wrong[case_id]["geometry_ok"] = False
            self.assertFalse(systematic_tracking(self.manifest["cases"], wrong))

    def test_constant_box_cannot_claim_tracking(self):
        observations = self.perfect_observations()
        # Even forged geometry_ok cannot bypass the independent motion test.
        observations["A_2"]["detections"][0]["bbox"] = observations["A_1"]["detections"][0]["bbox"]
        self.assertFalse(systematic_tracking(self.manifest["cases"], observations))

    def test_multi_cardinality_and_bijection_no_best_box(self):
        case = self.manifest["cases"][-1]
        target = Evidence(tuple(case["target_boxes"][0]), case["target_label"])
        for detections in [(target,), (target, target), (target, target, target)]:
            self.assertFalse(observe(case, NativeDetections("SUCCESS", detections))["geometry_ok"])
        self.assertTrue(self.perfect_observations()["F_multiple"]["geometry_ok"])

    def test_all_boxes_preserved_in_geometry_and_iou_diagnostic_only(self):
        case = self.manifest["cases"][-1]
        detections = []
        for box in case["target_boxes"]:
            x, y = (box[0]+box[2])/2, (box[1]+box[3])/2
            detections.append(Evidence((x-.001, y-.001, x+.001, y+.001), "red square"))
        observation = observe(case, NativeDetections("SUCCESS", tuple(detections)))
        self.assertTrue(observation["geometry_ok"])
        self.assertEqual(len(observation["detections"]), 2)
        self.assertLess(observation["detections"][0]["iou_diagnostic"][0], .001)
        # Human giant-box review remains mandatory in plan, never auto-awarded here.

    def test_distractor_center_boundary_and_full_image_fail(self):
        case = self.manifest["cases"][0]
        for box in [(0, 0, 1, 1), (0, .375, .75, .625)]:
            self.assertFalse(observe(case, NativeDetections("SUCCESS", (Evidence(box, "red square"),)))["geometry_ok"])

    def test_absence_blocker_never_becomes_geometry_success(self):
        case = self.manifest["cases"][-2]
        for parsed in [parse_qwen3("[]", label="red square"), parse_paligemma("", label="red square")]:
            row = observe(case, parsed)
            self.assertFalse(row["geometry_ok"])
            self.assertIsNone(row["detections"])

    def test_generation_reproduces_manifest_and_input_hashes(self):
        first, images = build()
        second, repeated = build()
        self.assertEqual(first, self.manifest)
        self.assertEqual(first, second)
        self.assertEqual(images, repeated)
        for case in first["cases"]:
            self.assertEqual(hashlib.sha256(images[case["image_path"]]).hexdigest(), case["image_sha256"])

    def test_materialization_refuses_manifest_or_existing_byte_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            manifest = repo / MANIFEST
            manifest.parent.mkdir(parents=True)
            manifest.write_bytes((ROOT / MANIFEST).read_bytes())
            self.assertEqual(materialize(repo), 10)
            self.assertEqual(materialize(repo), 10)
            image = repo / self.manifest["cases"][0]["image_path"]
            image.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "EXISTING_SYNTHETIC_IMAGE_MISMATCH"):
                materialize(repo)
            self.assertEqual(image.read_bytes(), b"bad")
            manifest.write_text("{}")
            with self.assertRaisesRegex(ValueError, "FROZEN_V2_MANIFEST"):
                materialize(repo)

    def test_paths_are_relative_external_synthetic_only(self):
        self.assertEqual(self.manifest["source_kind"], "synthetic")
        self.assertEqual(self.manifest["statement"], "NO_INSPECSAFE_CONTENT_USED")
        for case in self.manifest["cases"]:
            self.assertTrue(case["image_path"].startswith("data/processed/external_grounding_interface_v2/"))
            self.assertNotIn("..", Path(case["image_path"]).parts)

    def test_fixed_prompt_for_absent_single_and_multiple(self):
        for model, settings in self.plan["models"].items():
            for case in self.manifest["cases"]:
                label = case["target_label"]
                self.assertEqual(prompt(model, label), settings["prompt_template"].format(label=label))
        self.assertEqual(prompt("paligemma", "red square") + "\n", "detect red square\n")
        with self.assertRaises(ValueError):
            prompt("qwen3", 'red square"; alternate')

    def test_pass_rules_fixed_and_no_execution_or_promotion(self):
        self.assertTrue(self.plan["PASS_RULE_PREDECLARED"])
        self.assertEqual(self.plan["EXECUTION_STATUS"], "NOT_RUN")
        self.assertEqual(self.plan["MODEL_GPU_EXECUTION"], "NO")
        self.assertEqual(self.plan["INSPECSAFE"], "NOT_RUN")
        self.assertFalse(self.plan["execution_authorized"])
        self.assertFalse(self.plan["promotion"])
        self.assertIsNone(self.plan["qualification_verdict"])
        for key in ["retry", "repair", "alternate_prompt", "increase_token_budget_in_run", "change_parser_between_cases", "gt_selected_query"]:
            self.assertIs(self.plan["fixed_controls"][key], False)
        self.assertEqual(self.plan["models"]["qwen3"]["absence_semantics"], QWEN_ABSENCE)
        self.assertEqual(self.plan["models"]["paligemma"]["absence_semantics"], PALI_ABSENCE)

    def test_raw_contract_requires_persistence_before_parse(self):
        contract = self.plan["raw_audit_contract"]
        steps = contract["order"]
        self.assertLess(steps.index("reread_verify_raw_and_metadata"), steps.index("parse_verified_persisted_continuation"))
        self.assertTrue(contract["raw_immutable"])
        self.assertTrue(contract["exclusive_run_directory"])
        self.assertIsNone(contract["failure_canonical_detections"])
        self.assertTrue({"raw_sha256", "raw_size_bytes", "parser_sha256", "input_image_sha256", "geometry_observations"} <= set(contract["required_fields"]))

    def test_predeclared_lock_hashes(self):
        lock = strict_json((ROOT / LOCK).read_bytes())
        for path, digest in lock["sha256"].items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

    def test_historical_files_unchanged_and_logs_append_only(self):
        lock = strict_json((ROOT / LOCK).read_bytes())
        for path, oid in lock["historical_git_blobs"].items():
            actual = subprocess.check_output(["git", "hash-object", "--path="+path, path], cwd=ROOT, text=True).strip()
            self.assertEqual(actual, oid, path)
        for path in ["DECISIONS.md", "TASKS.md"]:
            original = subprocess.check_output(["git", "show", BASE+":"+path], cwd=ROOT)
            current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertTrue(current.startswith(original), path)


if __name__ == "__main__":
    unittest.main()
