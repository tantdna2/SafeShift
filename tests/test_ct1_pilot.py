"""Synthetic regressions for CT1. No image, network, runtime or GT source is opened."""

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.data.saved_reports import json_bytes, sha256, strict_json
from safeshift.evaluation.ct1_contract import (
    C1, C1_END, C1_SHA256, FORMAT, INSTRUCTIONS, ROOT, SCHEMA, parse, prompt, prompt_hashes,
)
from safeshift.evaluation.ct1_pilot import (
    MODEL_ID, REVISION, blind_packet, replay, score, validate_plan,
)
from safeshift.fulltrain.qwen_semantics import parse_classification
from scripts.ct1_pilot import main


def evidence(level="Level01"):
    return {"safety_level": level, "evidence_status": "CUE_PRESENT", "evidence": [
        {"cue": "Light near the floor", "region": "center", "visibility": "clear",
         "condition": "A flame is visible", "condition_status": "met", "rule_source": "general",
         "rule": "Open flame", "rule_level": "Level01"}
    ]}


def outputA(level):
    return json.dumps({"safety_level": level})


def fixture():
    ids = [f"p-{index:012x}" for index in range(6)]
    gt_levels = ("Level01", "Level01", "Level02", "Level04", "Level04", "Level03")
    plan = {"kind": "SYNTHETIC", "arms": ["A", "E", "S"], "cases": [
        {"case_id": key, "image_sha256": sha256(key.encode())} for key in ids]}
    plan_sha = sha256(json_bytes(plan))
    truth = {"plan_sha256": plan_sha, "cases": [
        {"case_id": case, "true_level": level} for case, level in zip(ids, gt_levels, strict=True)]}
    runs = {"plan_sha256": plan_sha, "model_id": MODEL_ID, "revision": REVISION,
            "runtime_sha256": "f" * 64, "prompt_sha256": prompt_hashes(plan["arms"]), "records": []}
    outputs = {
        "A": [outputA("Level02"), outputA("Level01"), outputA("Level01"),
              outputA("Level02"), outputA("Level04"), "bad"],
        "E": [json.dumps(evidence()), "bad", json.dumps(evidence()), None,
              json.dumps(evidence("Level04")), json.dumps(evidence("Level04"))],
        "S": [json.dumps(evidence()), json.dumps(evidence()), None, None, None, None],
    }
    for arm, values in outputs.items():
        for case, value in zip(ids, values, strict=True):
            if value is not None:
                runs["records"].append(
                    {"case_id": case, "arm": arm, "attempt_status": "RETURNED", "raw_text": value})
    runs["records"].append(
        {"case_id": ids[3], "arm": "E", "attempt_status": "TECHNICAL_ERROR", "raw_text": None})
    return plan, truth, runs, plan_sha


class ContractTest(unittest.TestCase):
    def test_a_exact_source_and_parser(self):
        self.assertEqual(prompt("A"), (ROOT / C1).read_bytes())
        self.assertEqual(sha256(prompt("A")), C1_SHA256)
        fence = chr(96) * 3
        for raw in (outputA("Level02"), fence + "json\n" + outputA("Level04") + "\n" + fence,
                    '{"safety_level":"Level01","safety_level":"Level02"}', "prefix{}", "{}"):
            a, historical = parse("A", raw), parse_classification(raw)
            self.assertEqual((a.status, a.wrapped, a.level), (historical.status, historical.format_wrapper_detected,
                             historical.value.safety_level if historical.success else None))

    def test_prompt_arms_keep_c1_criteria(self):
        rules = prompt("A").decode().split(C1_END)[0]
        self.assertEqual(prompt("E").decode(), rules + INSTRUCTIONS["E"] + "\n\n" + FORMAT)
        self.assertEqual(prompt("S").decode(), rules + INSTRUCTIONS["S"] + "\n\n" + FORMAT)
        self.assertNotEqual(sha256(prompt("E")), sha256(prompt("S")))
        self.assertEqual(SCHEMA["properties"]["evidence"]["maxItems"], 3)

    def test_schema_keeps_missing_evidence_and_validity_distinct(self):
        empty = {"safety_level": "Level04", "evidence_status": "NO_VISIBLE_HAZARD", "evidence": []}
        unknown = {"safety_level": "Level02", "evidence_status": "INSUFFICIENT", "evidence": []}
        for arm in ("E", "S"):
            for row in (evidence(), empty, unknown):
                self.assertEqual(parse(arm, json.dumps(row)).status, "SUCCESS")
            self.assertEqual(parse(arm, outputA("Level01")).status, "INVALID")
        self.assertEqual(parse("E", json.dumps(unknown)).evidence_status, "INSUFFICIENT")

    def test_parser_rejects_ambiguous_or_inconsistent_output(self):
        fence = chr(96) * 3
        rejects = [json.dumps(evidence()) + " extra", "{} {}", "NaN", "[]",
                   '{"evidence":[],"evidence":[],"evidence_status":"INSUFFICIENT","safety_level":"Level03"}',
                   fence + "json\n" + json.dumps(evidence()),
                   json.dumps({**evidence(), "evidence_status": "NO_VISIBLE_HAZARD"}),
                   json.dumps({**evidence(), "evidence": []})]
        for invalid in ({"cue": " "}, {"region": 1}, {"visibility": "unverifiable"},
                        {"rule_source": "unknown"}, {"rule_level": "Level04"}, {"condition": "x" * 121}):
            row = evidence()
            row["evidence"][0].update(invalid)
            rejects.append(json.dumps(row))
        for value in rejects:
            with self.subTest(value=value[:50]):
                self.assertEqual(parse("E", value).status, "INVALID")
        self.assertTrue(parse("S", fence + "json\r\n" + json.dumps(evidence()) + "\r\n" + fence).wrapped)


class ReplayTest(unittest.TestCase):
    def test_planned_denominators_ablation_and_metric_oracle(self):
        plan, truth, runs, plan_sha = fixture()
        decoded = replay(plan, runs, plan_sha)
        result = score(plan, decoded, truth, plan_sha)
        e = result["arms"]["E"]["labels"]
        self.assertAlmostEqual(e["macro_f1"], (0.5 + 0 + 0 + 0.5) / 4)
        self.assertEqual(e["per_class"]["Level01"]["recall"]["value"], 0.5)
        self.assertEqual(e["per_class"]["Level01"]["precision"]["value"], 0.5)
        self.assertEqual(e["binary"]["fnr"]["value"], 0.25)
        self.assertEqual(e["binary"]["fpr"]["value"], 0.0)
        self.assertEqual(e["hazard_missed_or_unavailable"]["value"], 0.5)
        self.assertEqual(e["overseverity"]["value"], 0.25)
        self.assertEqual(e["valid_label_rate"]["numerator"], 4)
        self.assertEqual(e["status_counts"], {"SUCCESS": 4, "INVALID": 1, "TECHNICAL_ERROR": 1,
                                               "NOT_ATTEMPTED": 0})
        self.assertEqual(result["arms"]["S"]["labels"]["status_counts"]["NOT_ATTEMPTED"], 4)
        self.assertEqual(result["paired"]["E-A"]["delta_level01_recall"]["value"], 0)
        self.assertEqual(result["paired"]["E-A"]["right_only_level01_correct"], 1)
        self.assertEqual(result["paired"]["E-S"]["delta_level01_recall"]["value"], -0.5)
        self.assertIsNone(result["arms"]["A"]["evidence"])
        self.assertIsNone(result["arms"]["E"]["evidence"]["supported_basis_reviewed"]["value"])

    def test_gt_and_runtime_reject_incompatible_inputs(self):
        plan, truth, runs, plan_sha = fixture()
        decoded = replay(plan, runs, plan_sha)
        truth["cases"].pop()
        with self.assertRaisesRegex(ValueError, "full planned"):
            score(plan, decoded, truth, plan_sha)
        changed = deepcopy(runs)
        changed["records"].append(changed["records"][0])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            replay(plan, changed, plan_sha)
        changed = deepcopy(runs)
        changed["prompt_sha256"]["E"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "wrong arm"):
            replay(plan, changed, plan_sha)

    def test_inputs_are_opaque_and_exclude_prior_audit(self):
        plan, _, _, _ = fixture()
        for key in ("true_level", "domain", "annotation", "image_path"):
            polluted = deepcopy(plan)
            polluted["cases"][0][key] = "secret"
            with self.assertRaises(ValueError):
                validate_plan(polluted)
        with self.assertRaisesRegex(ValueError, "TRAIN development"):
            validate_plan({**plan, "kind": "TEST"})
        private = {**plan, "kind": "TRAIN_DEVELOPMENT"}
        with self.assertRaisesRegex(ValueError, "exclusion set"):
            validate_plan(private)
        fake = sorted(sha256(f"exclude-{i}".encode()) for i in range(32))
        with patch("safeshift.evaluation.ct1_pilot.EXCLUSIONS_SHA256", sha256(json_bytes(fake))):
            validate_plan(private, fake)
            private["cases"][0]["image_sha256"] = fake[0]
            with self.assertRaisesRegex(ValueError, "audit-excluded"):
                validate_plan(private, fake)

    def test_review_join_reveals_wrong_reason_without_changing_metrics(self):
        plan, truth, runs, plan_sha = fixture()
        run_sha = sha256(json_bytes(runs))
        decoded = replay(plan, runs, plan_sha)
        packet, tokens = blind_packet(decoded, b"p" * 32, plan_sha, run_sha)
        packet2, _ = blind_packet(decoded, b"q" * 32, plan_sha, run_sha)
        self.assertNotEqual(packet, packet2)
        self.assertEqual(set(packet["cases"][0]), {"review_id", "case_id", "evidence", "evidence_status"})
        case = plan["cases"][0]["case_id"]
        token = next(token for token, key in tokens.items() if key == (case, "E"))
        reviewers = {"packet_sha256": sha256(json_bytes(packet)), "cases": [
            {"review_id": token, "basis": "CONTRADICTED", "visual_level": None,
             "evidence": [{"cue": "CONTRADICTED", "condition": "UNVERIFIABLE", "rule": "SUPPORTED"}]}
        ]}
        result = score(plan, decoded, truth, plan_sha, reviews=reviewers, packet=packet, token_to_case=tokens)
        row = result["arms"]["E"]["evidence"]
        self.assertEqual(row["reviewed_per_planned"]["numerator"], 1)
        self.assertEqual(row["correct_label_with_contradicted_basis"]["value"], 1)
        self.assertEqual(row["overall_claim_verdicts"]["CONTRADICTED"], 1)
        self.assertEqual(row["prediction_vs_independent_visual_level"]["NO_VISUAL_LEVEL"], 1)
        reviewers["packet_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            score(plan, decoded, truth, plan_sha, reviews=reviewers, packet=packet, token_to_case=tokens)

    def test_cli_creates_outputs_without_overwrite(self):
        plan, truth, runs, _ = fixture()
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, data in (("plan", plan), ("truth", truth), ("runs", runs)):
                (folder / name).write_bytes(json_bytes(data))
            (folder / "key").write_bytes(b"k" * 32)
            args = ["--plan", str(folder / "plan"), "--runs", str(folder / "runs")]
            self.assertEqual(main(["prepare", "--with-control", "--output", str(folder / "prep")]), 0)
            self.assertEqual((folder / "prep/prompt-A.txt").read_bytes(), prompt("A"))
            self.assertEqual(main(["blind", *args, "--review-key", str(folder / "key"),
                                   "--output", str(folder / "blind")]), 0)
            scores = ["score", *args, "--truth", str(folder / "truth"), "--output", str(folder / "score")]
            self.assertEqual(main(scores), 0)
            self.assertEqual(strict_json((folder / "score").read_bytes())["scope"], "SYNTHETIC")
            with self.assertRaises(FileExistsError):
                main(scores)


if __name__ == "__main__":
    unittest.main()