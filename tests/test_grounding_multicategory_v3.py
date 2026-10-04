"""Handcrafted/synthetic offline tests only; no model or historical outputs."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from safeshift.protocol.grounding_multicategory_candidate import (
    HAZARD_LABELS, HAZARD_QUERY_MAP, NativeDetections, POSITIVE_GUARANTEE_MISS,
    hazard_id, hazard_prompt, parse_paligemma_multicategory as pali,
    parse_qwen3_multicategory as qwen, prompt,
)
from safeshift.protocol.grounding_multicategory_geometry import observe, systematic_tracking
from safeshift.protocol.schema import Evidence, HAZARDS, strict_json
from scripts.prepare_grounding_multicategory_v3 import LABELS, MANIFEST, build, materialize

ROOT = Path(__file__).resolve().parents[1]
BASE = "775e5eee4cade340e0156f97f2af50f7c98e1551"
PLAN = "configs/pre_freeze/grounding_interface_qualification_plan.v3.json"
LOCK = "configs/pre_freeze/grounding_interface_lock.v3.json"


def loc(label="red square", box=(128, 256, 640, 768)):
    return "".join(f"<loc{v:04d}>" for v in box) + " " + label


def item(label="red square", box=(100, 200, 600, 800)):
    return {"bbox_2d": list(box), "label": label}


def expected(case):
    return NativeDetections("SUCCESS", tuple(Evidence(tuple(t["bbox"]), t["label"])
                                             for t in case["targets"]))


class CandidateTests(unittest.TestCase):
    def test_qwen_prompt_exact_order(self):
        self.assertEqual(prompt("qwen3", LABELS),
                         "Locate every instance that belongs to the following categories: "
                         "'red square, green circle, yellow triangle, cyan rectangle'. "
                         "Report bbox coordinates in JSON format.")

    def test_pali_prompt_delimiter_and_processor_newline(self):
        self.assertEqual(prompt("paligemma", LABELS),
                         "detect red square ; green circle ; yellow triangle ; cyan rectangle")
        self.assertNotIn("\n", prompt("paligemma", LABELS))

    def test_map_is_exact_canonical_order(self):
        labels = ("person without gloves", "person without helmet", "person without mask",
                  "person using mobile phone", "liquid on ground", "person smoking",
                  "open flame", "foreign object", "smoke", "non-motorized vehicle",
                  "open door", "fallen person")
        self.assertEqual(tuple(h for h, _ in HAZARD_QUERY_MAP), HAZARDS)
        self.assertEqual(HAZARD_LABELS, labels)
        for hazard, label in HAZARD_QUERY_MAP:
            self.assertEqual(hazard_id(label), hazard)
        with self.assertRaises(KeyError):
            hazard_id("person without a helmet")
        for model in ("qwen3", "paligemma"):
            self.assertEqual(hazard_prompt(model), prompt(model, labels))

    def test_query_validation_no_unordered_duplicates_or_injection(self):
        for labels in [[], set(LABELS), "red square", ["red square", "red square"],
                       [""], [" x"], ["x\n"], ["x;y"], ["x,y"], ["x'y"], [1], ["x\t"]]:
            for fn in (qwen, pali):
                with self.subTest(labels=labels, fn=fn), self.assertRaises(ValueError):
                    fn("", labels)
        with self.assertRaises(ValueError):
            prompt("unknown", LABELS)

    def test_qwen_multiple_labels_boxes_and_order(self):
        rows = [item(), item("green circle", (10, 20, 30, 40)), item()]
        result = qwen(json.dumps(rows), LABELS)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual([d.label for d in result.detections],
                         ["red square", "green circle", "red square"])
        self.assertEqual(result.detections[0].bbox, (.1, .2, .6, .8))
        self.assertEqual(result.detections[1].bbox, (.01, .02, .03, .04))
        self.assertEqual(result.detections[0], result.detections[2])  # no dedup

    def test_pali_multiple_labels_boxes_and_order(self):
        result = pali(loc() + "; " + loc("green circle") + " ; " + loc(), LABELS)
        self.assertEqual(result.status, "SUCCESS")
        self.assertEqual([d.label for d in result.detections],
                         ["red square", "green circle", "red square"])
        self.assertEqual(result.detections[0].bbox, (.25, .125, .75, .625))

    def test_unknown_alias_and_case_labels_invalidate_all(self):
        for label in ["blue square", "Red square", "red block", "red square "]:
            for fn, raw in [(qwen, json.dumps([item(), item(label)])),
                            (pali, loc() + "; " + loc(label))]:
                result = fn(raw, LABELS)
                self.assertEqual(result.status, "INVALID")
                self.assertIsNone(result.detections)

    def test_one_bad_qwen_detection_invalidates_all(self):
        for bad in [item(box=(1, 2, 1, 4)), {"label": "red square"},
                    item(box=(0, 0, 1001, 1000)), item(box=(True, 2, 3, 4)),
                    item(box=(0, 0, float("inf"), 2)), item(box=(1, 2)),
                    {**item(), "confidence": 1}, item(label=["red square"])]:
            result = qwen(json.dumps([item(), bad]), LABELS)
            self.assertEqual(result.status, "INVALID")
            self.assertIsNone(result.detections)

    def test_one_bad_pali_detection_invalidates_all(self):
        for bad in [loc(box=(0, 0, 1024, 1023)), loc(box=(100, 200, 90, 300)),
                    loc().replace("<loc0128>", "<loc128>"), "unmatched text",
                    loc() + "<seg000>", loc() + "\n"]:
            result = pali(loc() + "; " + bad, LABELS)
            self.assertEqual(result.status, "INVALID")
            self.assertIsNone(result.detections)

    def test_qwen_empty_array_is_miss_not_absence(self):
        for raw in ["[]", " \n [ ] \t", ""]:
            self.assertEqual(qwen(raw, LABELS), NativeDetections(POSITIVE_GUARANTEE_MISS))

    def test_pali_empty_continuation_is_miss_not_absence(self):
        self.assertEqual(pali("", LABELS), NativeDetections(POSITIVE_GUARANTEE_MISS))

    def test_no_qwen_json_repair(self):
        good = json.dumps([item()])
        for raw in ["```json\n" + good + "\n```", good[:-1], "prefix " + good,
                    good + " trailing", "null", "{}", " ", None,
                    '[{"bbox_2d":[1,2,3,4],"label":"red square","label":"red square"}]']:
            self.assertEqual(qwen(raw, LABELS).status, "INVALID")

    def test_no_pali_salvage_or_repair(self):
        for raw in [" " + loc(), loc() + " ", "prefix " + loc(), loc() + "; ",
                    "[]", " ", "</s>", None, loc() + "</s>",
                    loc().replace(" red", "  red"), loc() + ";" + loc()]:
            self.assertEqual(pali(raw, LABELS).status, "INVALID")

    def test_fixed_scales_no_guessing_and_no_clamp(self):
        result = qwen(json.dumps([item(box=(.1, .2, .6, .8))]), LABELS)
        self.assertEqual(result.detections[0].bbox, (.0001, .0002, .0006, .0008))
        self.assertEqual(pali(loc(box=(0, 0, 1023, 1023)), LABELS).detections[0].bbox,
                         (0, 0, 1023 / 1024, 1023 / 1024))
        self.assertEqual(qwen(json.dumps([item(box=(-1, 0, 20, 30))]), LABELS).status, "INVALID")


class SuiteTests(unittest.TestCase):
    def setUp(self):
        self.manifest, self.images = build()
        self.cases = self.manifest["cases"]

    def test_manifest_reproducible_and_every_case_positive_same_query(self):
        self.assertEqual(self.manifest, strict_json((ROOT / MANIFEST).read_bytes()))
        self.assertEqual(len(self.cases), 12)
        for c in self.cases:
            self.assertGreaterEqual(len(c["targets"]), 1)
            self.assertEqual(c["query_labels"], list(LABELS))
            self.assertEqual(set(c["expected_counts"]), set(LABELS))
            self.assertEqual(c["image_sha256"], hashlib.sha256(self.images[c["image_path"]]).hexdigest())

    def test_materialization_idempotent_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / MANIFEST
            path.parent.mkdir(parents=True)
            path.write_bytes((ROOT / MANIFEST).read_bytes())
            self.assertEqual(materialize(repo), 12)
            self.assertEqual(materialize(repo), 12)
            image = repo / self.cases[0]["image_path"]
            image.write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "EXISTING_SYNTHETIC_IMAGE_MISMATCH"):
                materialize(repo)
            self.assertEqual(image.read_bytes(), b"different")

    def test_manifest_mismatch_refuses_materialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / MANIFEST
            path.parent.mkdir(parents=True)
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "FROZEN_V3_MANIFEST"):
                materialize(repo)
            self.assertFalse((repo / "data").exists())

    def test_expected_per_label_zero_and_false_positive_rejected(self):
        case = self.cases[0]
        self.assertEqual(case["expected_counts"], dict(zip(LABELS, (1, 0, 0, 0))))
        good = expected(case)
        bad = NativeDetections("SUCCESS", good.detections +
                               (Evidence((.6, .6, .8, .8), "green circle"),))
        obs = observe(case, bad)
        self.assertEqual(obs["predicted_counts"]["green circle"], 1)
        self.assertFalse(obs["geometry_ok"])

    def test_all_instances_match_both_parsers(self):
        for case in self.cases:
            rows = [item(t["label"], [v * 1000 for v in t["bbox"]]) for t in case["targets"]]
            native = " ; ".join(loc(t["label"], tuple(int(t["bbox"][i] * 1024)
                                                       for i in (1, 0, 3, 2)))
                                for t in case["targets"])
            for parsed in (qwen(json.dumps(rows), LABELS), pali(native, LABELS)):
                self.assertTrue(observe(case, parsed)["geometry_ok"])

    def test_multi_instance_bijection_not_duplicate_assignment(self):
        case = next(c for c in self.cases if c["case_id"] == "F_two_red")
        good = expected(case)
        self.assertTrue(observe(case, good)["geometry_ok"])
        self.assertTrue(observe(case, NativeDetections("SUCCESS", good.detections[::-1]))["geometry_ok"])
        for ds in [good.detections[:1], (good.detections[0], good.detections[0])]:
            self.assertFalse(observe(case, NativeDetections("SUCCESS", ds))["geometry_ok"])

    def test_positive_tracking_and_frozen_position_failure(self):
        observations = {c["case_id"]: observe(c, expected(c)) for c in self.cases}
        self.assertTrue(systematic_tracking(self.cases, observations))
        observations["A_2"] = observe(self.cases[1], expected(self.cases[0]))
        self.assertFalse(systematic_tracking(self.cases, observations))
        self.assertFalse(systematic_tracking(self.cases[1:], observations))

    def test_wrong_label_at_right_position_and_distractor_fail(self):
        case = self.cases[0]
        for label, box in [("green circle", case["targets"][0]["bbox"]),
                           ("red square", case["distractor_boxes"][0])]:
            self.assertFalse(observe(case, NativeDetections("SUCCESS", (Evidence(tuple(box), label),)))
                             ["geometry_ok"])

    def test_full_image_and_distractor_cover_fail(self):
        case = self.cases[0]
        for box in [(0, 0, 1, 1), (.05, .35, .8, .65)]:
            self.assertFalse(observe(case, NativeDetections("SUCCESS", (Evidence(box, "red square"),)))
                             ["geometry_ok"])

    def test_all_failure_statuses_cannot_be_empty_success(self):
        for status in [POSITIVE_GUARANTEE_MISS, "INVALID", "BLOCKED", "SUCCESS"]:
            self.assertFalse(observe(self.cases[0], NativeDetections(status))["geometry_ok"])
        self.assertFalse(observe(self.cases[0], NativeDetections("SUCCESS", ()))["geometry_ok"])

    def test_case_rejects_all_absent_or_wrong_counts(self):
        for mode in ("empty", "counts"):
            c = deepcopy(self.cases[0])
            if mode == "empty":
                c["targets"] = []
            else:
                c["expected_counts"]["green circle"] = 1
            with self.assertRaises(ValueError):
                observe(c, expected(c))


class ContractProtectionTests(unittest.TestCase):
    def setUp(self):
        self.plan = strict_json((ROOT / PLAN).read_bytes())
        self.lock = strict_json((ROOT / LOCK).read_bytes())

    def test_scope_and_exclusions(self):
        s = self.plan["scope"]
        self.assertEqual((s["direct"], s["weak_proxy"], s["overlap"]), (721, 608, 347))
        self.assertEqual(s["direct"] + s["weak_proxy"] - s["overlap"], s["unique_samples"])
        self.assertEqual(s["unique_samples"], 982)
        self.assertEqual(s["unsupported_only_excluded"], 18)
        self.assertEqual(s["sample_class"], "Anomaly")
        self.assertFalse(s["normal_images_included"])
        self.assertFalse(s["full_5013_included"])

    def test_absence_blockers_and_empty_failure(self):
        a = self.plan["absence"]
        for key in ("QWEN3_ABSENCE_SEMANTICS_BLOCKER", "PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER"):
            self.assertEqual(a[key], "UNRESOLVED")
        self.assertFalse(a["ALL_TARGET_ABSENT_REQUIRED_FOR_V3"])
        self.assertEqual(a["ALL_TARGET_ABSENT_SEMANTICS"],
                         "NOT_APPLICABLE_TO_POSITIVE_GUARANTEED_PRIMARY_SCOPE")
        self.assertEqual(a["empty_response_status"], POSITIVE_GUARANTEE_MISS)
        self.assertFalse(a["empty_response_success"])
        self.assertEqual(len(a["mandatory_again_if_expanded_to"]), 4)

    def test_not_run_no_authority_no_promotion_old_roles(self):
        for obj in (self.plan, self.lock):
            self.assertEqual(obj["QUALIFICATION_EXECUTION"], "NOT_RUN")
            self.assertIs(obj["execution_authorized"], False)
        self.assertIsNone(self.plan["qualification_verdict"])
        self.assertFalse(self.plan["promotion"])
        self.assertFalse(self.plan["merge"])
        self.assertEqual(self.plan["MODEL_GPU_EXECUTION"], "NO")
        self.assertEqual(self.plan["INSPECSAFE"], "NOT_RUN")
        for model in self.plan["models"].values():
            self.assertEqual(model["primary_grounding_role"], "NOT_PARTICIPATING")
        self.assertEqual(self.plan["historical_protection"]["qwen3_external_gate"], "GATE_FAIL")
        self.assertEqual(self.plan["historical_protection"]["paligemma_external_gate"], "FAIL")

    def test_controls_pass_predeclared_raw_before_parser(self):
        p = self.plan
        self.assertTrue(p["PASS_RULE_PREDECLARED"])
        self.assertEqual(p["required_calls_per_model"], 12)
        for key, value in p["fixed_controls"].items():
            if key not in ("iou_usage", "iou_threshold", "giant_area_threshold"):
                self.assertIs(value, False, key)
        self.assertEqual(p["fixed_controls"]["iou_usage"], "DIAGNOSTIC_ONLY")
        order = p["raw_audit_contract"]["order"]
        self.assertLess(order.index("reread_verify_raw_and_metadata"),
                        order.index("parse_verified_persisted_continuation"))
        rules = " ".join(p["pass_requires_all"])
        for required in ("NO_GIANT", "ZERO", "one-to-one", "POSITIVE_GUARANTEE_MISS", "reciprocal"):
            self.assertIn(required, rules)

    def test_plan_map_models_and_full_single_call(self):
        self.assertEqual([(r["hazard_id"], r["query"]) for r in self.plan["fixed_hazard_query_map"]],
                         list(HAZARD_QUERY_MAP))
        self.assertEqual(self.plan["query_labels"], list(LABELS))
        self.assertEqual(self.plan["production_compatibility"]["logical_call2_per_image"], 1)
        self.assertEqual(self.plan["production_compatibility"]["native_calls_per_image"], 1)
        self.assertEqual(self.plan["models"]["qwen3"]["immutable_revision"],
                         "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b")
        self.assertEqual(self.plan["models"]["paligemma"]["immutable_revision"],
                         "ead2d9a35598cb89119af004f5d023b311d1c4a1")

    def test_lock_hashes_all_artifacts_and_shared_helpers(self):
        for path, checksum in self.lock["sha256"].items():
            raw = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), checksum, path)

    def test_v2_g2_and_historical_bytes_unchanged(self):
        for path, blob in self.lock["historical_git_blobs"].items():
            old = subprocess.check_output(["git", "cat-file", "blob", blob], cwd=ROOT)
            now = (ROOT / path).read_bytes()
            if Path(path).suffix != ".png":
                now = now.replace(b"\r\n", b"\n")
            self.assertEqual(now, old, path)

    def test_logs_append_only_and_g2_closure(self):
        for path in self.lock["append_only_logs"]:
            old = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
            now = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertTrue(now.startswith(old), path)
            self.assertIn(b"G2 merged as PR #69", now[len(old):])
            self.assertIn(BASE.encode(), now[len(old):])

    def test_official_source_pins_and_explicit_limits(self):
        src = strict_json((ROOT / self.plan["sources"]).read_bytes())
        self.assertTrue(src["qwen3"]["source_backed"])
        self.assertTrue(src["paligemma"]["source_backed"])
        self.assertEqual(src["paligemma"]["official_task_syntax"], "detect {object} ; {object}\n")
        self.assertEqual(src["qwen3"]["input_construction"], 'obj_names = ", ".join(classes)')
        self.assertEqual(len(src["sources"]), 7)
        for row in src["sources"]:
            self.assertEqual(len(row["sha256"]), 64)
            self.assertEqual(row["accessed_date"], "2026-10-04")
            self.assertGreater(row["bytes"], 0)
        self.assertFalse(src["paligemma"]["snapshot"]["immutable_url_available"])


if __name__ == "__main__":
    unittest.main()
