"""Independent handwritten CPU oracles for the proposed T2 queue contract."""

import copy
from dataclasses import FrozenInstanceError, replace
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.data.schema import PredictionRecord, SampleRecord
from safeshift.evaluation.triage import (
    ClassifiedResult as Result, HNLOSignal as H, ModelResults, MODES,
    SourceIdentity, build_review_queue, compare_review_queues,
)
from scripts.demo_triage_cpu import build_report, evaluate_synthetic_queue, synthetic_inputs

IDS = tuple(f"{i:032x}" for i in range(1, 10))
KEY = b"public-test-seed-not-a-secret"
ROOT = Path(__file__).resolve().parents[1]


def source(name, rows):
    return ModelResults(SourceIdentity(name, "revision", "implementation", "configuration",
                                       "run", "series", "attempt"), rows)


def normal(sid, score=1):
    return Result(sid, "SUCCESS", "Level04", H(score, True))


def review_ids(queue):
    return [row["sample_id"] for row in queue["review"]]


class TriageTests(unittest.TestCase):
    def queue(self, ids, rows, peers=(), mode="hnlo_only", budget=99, key=KEY):
        return build_review_queue(ids, source("focal", rows), peers,
                                  mode=mode, budget=budget, tie_key=key)

    def test_agreement_one_and_two_hazard_votes(self):
        peers = (source("a", [Result(IDS[0], "SUCCESS", "Level04"),
                              Result(IDS[1], "SUCCESS", "Level03"),
                              Result(IDS[2], "SUCCESS", "Level02")]),
                 source("b", [Result(IDS[0], "SUCCESS", "Level04"),
                              Result(IDS[1], "SUCCESS", "Level04"),
                              Result(IDS[2], "SUCCESS", "Level01")]))
        q = self.queue(IDS[:3], [normal(sid) for sid in IDS[:3]], peers, "peer_only")
        self.assertEqual(review_ids(q), [IDS[2], IDS[1], IDS[0]])
        cases = {c["sample_id"]: c for c in q["cases"]}
        self.assertEqual([cases[s]["peer_hazard_fraction"] for s in IDS[:3]], [0, .5, 1])
        self.assertEqual(q["mandatory_count"], 0)

    def test_modes_have_distinct_handwritten_orders(self):
        rows = [normal(IDS[0], 9), normal(IDS[1], 2), normal(IDS[2], 5)]
        peers = (source("a", [Result(IDS[0], "SUCCESS", "Level04"),
                              Result(IDS[1], "SUCCESS", "Level01"),
                              Result(IDS[2], "SUCCESS", "Level03")]),)
        hnlo = self.queue(IDS[:3], rows, peers, "hnlo_only")
        combined = self.queue(IDS[:3], rows, peers, "combined")
        self.assertEqual(review_ids(hnlo), [IDS[0], IDS[2], IDS[1]])
        self.assertEqual(review_ids(combined), [IDS[2], IDS[1], IDS[0]])
        self.assertEqual(hnlo["eligible_count"], 3)

    def test_combined_prioritizes_disagreement_before_arbitrarily_large_hnlo(self):
        peers = (source("a", [Result(IDS[0], "SUCCESS", "Level04"),
                              Result(IDS[1], "SUCCESS", "Level03")]),)
        q = self.queue(IDS[:2], [normal(IDS[0], 1e300), normal(IDS[1], -1e300)],
                       peers, "combined", 1)
        self.assertEqual(review_ids(q), [IDS[1]])

    def test_peer_only_does_not_rank_by_hnlo(self):
        peers = (source("a", [Result(sid, "SUCCESS", "Level01") for sid in IDS[:3]]),)
        q1 = self.queue(IDS[:3], [normal(sid, i) for i, sid in enumerate(IDS[:3])], peers, "peer_only")
        q2 = self.queue(IDS[:3], [normal(sid, -i) for i, sid in enumerate(IDS[:3])], peers, "peer_only")
        self.assertEqual(review_ids(q1), review_ids(q2))

    def test_all_hazard_levels_outside_false_safe_even_with_missing_features(self):
        for level in ("Level01", "Level02", "Level03"):
            for mode in MODES:
                with self.subTest(level=level, mode=mode):
                    q = self.queue(IDS[:1], [Result(IDS[0], "SUCCESS", level)],
                                   (source("peer", []),), mode)
                    self.assertEqual((q["focal_normal_count"], q["mandatory_count"],
                                      q["eligible_count"], q["slots_used"]), (0, 0, 0, 0))
                    self.assertEqual(q["cases"][0]["category"], "OUTSIDE_FOCAL_NORMAL")

    def test_all_focal_failures_and_absence_are_distinct_mandatory(self):
        rows = [Result(IDS[0], "INVALID"), Result(IDS[1], "TECHNICAL_ERROR"),
                Result(IDS[2], "NOT_ATTEMPTED")]
        q = self.queue(IDS[:4], rows)
        self.assertEqual((q["planned_count"], q["mandatory_count"], q["slots_used"]), (4, 4, 4))
        self.assertEqual(q["focal_normal_count"], 0)
        counts = q["coverage"]["models"][0]["statuses"]
        self.assertEqual(counts, {"SUCCESS": 0, "INVALID": 1, "TECHNICAL_ERROR": 1,
                                  "NOT_ATTEMPTED": 1, "MISSING": 1})
        self.assertEqual({c["reasons"][0] for c in q["cases"]},
                         {"FOCAL_INVALID", "FOCAL_TECHNICAL_ERROR", "FOCAL_NOT_ATTEMPTED", "FOCAL_MISSING"})

    def test_peer_failure_states_required_only_in_peer_arms(self):
        peers = (source("peer", [Result(IDS[0], "INVALID"), Result(IDS[1], "TECHNICAL_ERROR"),
                                 Result(IDS[2], "NOT_ATTEMPTED")]),)
        for mode, mandatory in (("hnlo_only", 0), ("peer_only", 4), ("combined", 4)):
            with self.subTest(mode=mode):
                q = self.queue(IDS[:4], [normal(s) for s in IDS[:4]], peers, mode)
                self.assertEqual(q["mandatory_count"], mandatory)
                self.assertEqual(q["coverage"]["models"][1]["statuses"]["MISSING"], 1)
                self.assertTrue(all(c["peer_hazard_fraction"] is None for c in q["cases"]))
                self.assertEqual(q["coverage"]["complete_peers_on_focal_normal"]["count"], 0)

    def test_partial_peer_is_not_reduced_denominator_or_implicit_agreement(self):
        q = self.queue(IDS[:1], [normal(IDS[0])],
                       (source("a", [Result(IDS[0], "SUCCESS", "Level01")]), source("b", [])),
                       "peer_only")
        self.assertEqual(q["mandatory_count"], 1)
        self.assertEqual(q["cases"][0]["peer_hazard_votes"], 1)
        self.assertIsNone(q["cases"][0]["peer_hazard_fraction"])
        self.assertEqual(q["cases"][0]["reasons"], ["PEER_MISSING:b"])

    def test_multiple_missing_reasons_cost_one_slot(self):
        q = self.queue(IDS[:1], [normal(IDS[0], None)],
                       (source("a", []), source("b", [])), "combined", 1)
        self.assertEqual(q["mandatory_count"], 1)
        self.assertEqual(q["slots_used"], 1)
        self.assertEqual(len(q["review"][0]["reasons"]), 3)

    def test_hnlo_valid_missing_ineligible_and_malformed(self):
        examples = ((4, True, "VALID"), (-3.5, True, "VALID"), (0, True, "VALID"),
                    (None, True, "MISSING"), (5, False, "INELIGIBLE"),
                    (float("nan"), True, "MALFORMED"), (float("inf"), True, "MALFORMED"),
                    (-float("inf"), True, "MALFORMED"), ("1", True, "MALFORMED"),
                    (True, True, "MALFORMED"), ([], True, "MALFORMED"),
                    ({}, True, "MALFORMED"), (10 ** 400, True, "MALFORMED"))
        for value, eligible, state in examples:
            with self.subTest(value=repr(value)):
                q = self.queue(IDS[:1], [Result(IDS[0], "SUCCESS", "Level04", H(value, eligible))])
                self.assertEqual(q["cases"][0]["focal_hnlo"]["state"], state)
                self.assertEqual(q["mandatory_count"], int(state != "VALID"))
                self.assertEqual(q["coverage"]["focal_normal_hnlo"]["states"][state], 1)
                json.dumps(q, allow_nan=False)
        with self.assertRaises(ValueError):
            H(1, "yes")

    def test_peer_only_operates_without_any_hnlo(self):
        q = self.queue(IDS[:1], [normal(IDS[0], None)],
                       (source("a", [Result(IDS[0], "SUCCESS", "Level04")]),), "peer_only")
        self.assertEqual((q["eligible_count"], q["mandatory_count"]), (1, 0))
        self.assertEqual(q["coverage"]["focal_hnlo"]["states"]["MISSING"], 1)

    def test_hnlo_on_non_normal_does_not_make_it_eligible(self):
        q = self.queue(IDS[:1], [Result(IDS[0], "INVALID", hnlo=H(99, True))])
        self.assertEqual(q["mandatory_count"], 1)
        self.assertEqual(q["eligible_count"], 0)
        self.assertEqual(q["coverage"]["focal_normal_hnlo"]["denominator"], 0)

    def test_budget_zero_overload_and_unused_slots(self):
        rows = [Result(IDS[0], "INVALID"), Result(IDS[1], "TECHNICAL_ERROR"), normal(IDS[2])]
        for budget, used, mandatory_left, ranked_left, status in (
                (0, 0, 2, 1, "OVERLOAD"), (1, 1, 1, 1, "OVERLOAD"),
                (2, 2, 0, 1, "WITHIN_CAPACITY"), (3, 3, 0, 0, "WITHIN_CAPACITY"),
                (10, 3, 0, 0, "WITHIN_CAPACITY")):
            with self.subTest(budget=budget):
                q = self.queue(IDS[:3], rows, budget=budget)
                self.assertEqual(q["status"], status)
                self.assertEqual(q["slots_used"], used)
                self.assertEqual(q["slots_unused"], budget - used)
                self.assertEqual(q["backlog"]["mandatory"], mandatory_left)
                self.assertEqual(q["backlog"]["ranked"], ranked_left)
                self.assertEqual(q["backlog"]["total"], mandatory_left + ranked_left)
                self.assertEqual(len(q["backlog"]["sample_ids"]), mandatory_left + ranked_left)
                self.assertEqual([c["order"] for c in q["review"]], list(range(1, used + 1)))
                if budget < 3:
                    self.assertNotIn(IDS[2], review_ids(q))

    def test_zero_budget_without_mandatory_is_not_overload(self):
        q = self.queue(IDS[:1], [normal(IDS[0])], budget=0)
        self.assertEqual(q["status"], "WITHIN_CAPACITY")
        self.assertEqual(q["backlog"]["ranked"], 1)

    def test_empty_plan_undefined_coverage(self):
        q = self.queue([], [], budget=0)
        self.assertEqual(q["planned_count"], 0)
        self.assertIsNone(q["coverage"]["models"][0]["valid_fraction"])
        self.assertIsNone(q["coverage"]["complete_peers_on_focal_normal"]["count"])
        self.assertEqual(q["backlog"]["total"], 0)

    def test_denominators_do_not_drop_missing_or_focal_hazards(self):
        q = self.queue(IDS[:4], [normal(IDS[0]), Result(IDS[1], "INVALID"),
                                Result(IDS[2], "SUCCESS", "Level01", H(2, True))],
                       (source("a", [Result(IDS[0], "SUCCESS", "Level03")]),), "combined", 3)
        self.assertEqual((q["planned_count"], q["focal_normal_count"], q["eligible_count"],
                          q["mandatory_count"], q["slots_used"]), (4, 1, 1, 2, 3))
        self.assertEqual([m["valid_fraction"] for m in q["coverage"]["models"]], [.5, .25])
        self.assertEqual(q["coverage"]["focal_hnlo"]["states"],
                         {"VALID": 2, "MISSING": 2, "INELIGIBLE": 0, "MALFORMED": 0})

    def test_duplicate_planned_and_result_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate planned"):
            self.queue([IDS[0], IDS[0]], [])
        for rows in ([normal(IDS[0]), normal(IDS[0])],
                     [normal(IDS[0]), Result(IDS[0], "INVALID")]):
            with self.assertRaisesRegex(ValueError, "duplicate result"):
                self.queue(IDS[:1], rows)
            with self.assertRaisesRegex(ValueError, "duplicate result"):
                self.queue(IDS[:1], [], (source("peer", [replace(r, hnlo=None) for r in rows]),))

    def test_extra_ids_rejected_in_every_stream(self):
        with self.assertRaisesRegex(ValueError, "outside planned"):
            self.queue(IDS[:1], [normal(IDS[1])])
        with self.assertRaisesRegex(ValueError, "outside planned"):
            self.queue(IDS[:1], [], (source("peer", [Result(IDS[1], "INVALID")]),))

    def test_missing_id_fields_and_nonopaque_ids_rejected(self):
        with self.assertRaises(TypeError):
            Result(status="INVALID")
        for sid in (None, "", " ", 1, True, "Level04", "domain/Level01/image.jpg",
                    "A" * 32, "a" * 31, "a" * 33, [], {}):
            with self.subTest(sid=sid), self.assertRaises(ValueError):
                self.queue([sid], [])
            with self.subTest(record=sid), self.assertRaises(ValueError):
                Result(sid, "INVALID")
        with self.assertRaises(ValueError):
            self.queue(IDS[0], [])

    def test_invalid_status_label_combinations_rejected(self):
        for status, label in (("SUCCESS", None), ("SUCCESS", "INVALID"),
                              ("SUCCESS", "Level4"), ("INVALID", "Level04"),
                              ("TECHNICAL_ERROR", "Level01"), ("NOT_ATTEMPTED", "Level02"),
                              ("MISSING", None), (None, None), ([], None)):
            with self.subTest(status=status, label=label), self.assertRaises(ValueError):
                Result(IDS[0], status, label)
        with self.assertRaises(ValueError):
            Result(IDS[0], "SUCCESS", "Level04", 1.5)

    def test_prediction_projection_preserves_historical_none_semantics(self):
        for level in ("Level01", "Level02", "Level03", "Level04", None):
            p = PredictionRecord(IDS[0], level)
            r = Result.from_prediction(p)
            self.assertEqual(r.predicted_safety_level, level)
            self.assertEqual(r.status, "INVALID" if level is None else "SUCCESS")
            self.assertEqual(p, PredictionRecord(IDS[0], level))
        with self.assertRaises(ValueError):
            Result.from_prediction(SampleRecord(IDS[0], "Level04"))

    def test_invalid_budget_mode_and_key_rejected(self):
        for budget in (-1, True, 1.5, "2", None):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.queue([], [], budget=budget)
        for key in (b"", "seed", 1, None):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.queue([], [], key=key)
        with self.assertRaises(ValueError):
            self.queue([], [], mode="learned")

    def test_source_contract_cap_uniqueness_and_peer_hnlo(self):
        for mode in ("peer_only", "combined"):
            with self.assertRaises(ValueError):
                self.queue([], [], mode=mode)
        for peers in ((source("focal", []),), (source("a", []), source("a", [])),
                      tuple(source(s, []) for s in ("a", "b", "c")), (None,)):
            with self.assertRaises(ValueError):
                self.queue([], [], peers)
        with self.assertRaisesRegex(ValueError, "peer HNLO"):
            self.queue(IDS[:1], [], (source("a", [normal(IDS[0])]),))
        with self.assertRaises(ValueError):
            ModelResults("model", [])
        with self.assertRaises(ValueError):
            source("a", [PredictionRecord(IDS[0], "Level04")])
        with self.assertRaises(ValueError):
            replace(source("a", []).identity, implementation_id="")

    def test_tied_input_permutations_and_peer_order_have_identical_full_output(self):
        for mode in MODES:
            rows = [normal(IDS[0]), normal(IDS[1]), Result(IDS[2], "INVALID")]
            peer_rows = [Result(sid, "SUCCESS", "Level03") for sid in IDS[:3]]
            peers = (source("a", peer_rows), source("b", peer_rows))
            expected = self.queue(IDS[:3], rows, peers, mode, 2)
            for permutation in itertools.permutations(range(3)):
                q = self.queue([IDS[i] for i in permutation], [rows[i] for i in permutation],
                               (source("b", reversed(peer_rows)), source("a", reversed(peer_rows))), mode, 2)
                self.assertEqual(q, expected)

    def test_many_ties_and_external_key_affect_order_without_exposing_key(self):
        rows = [normal(s) for s in IDS]
        q = self.queue(IDS, rows)
        self.assertEqual(q, self.queue(reversed(IDS), reversed(rows)))
        other = self.queue(IDS, rows, key=b"another-public-test-seed")
        self.assertNotEqual(review_ids(q), review_ids(other))
        serialized = json.dumps(q, allow_nan=False)
        self.assertNotIn(KEY.decode(), serialized)
        self.assertNotIn("tie_key", serialized)

    def test_tie_digest_collision_fails_instead_of_using_read_order(self):
        with patch("safeshift.evaluation.triage._tie", return_value=(b"same", b"same")):
            with self.assertRaisesRegex(ValueError, "tie digest collision"):
                self.queue(IDS[:2], [normal(s) for s in IDS[:2]])

    def test_provenance_does_not_choose_review_cases(self):
        focal = source("focal", [normal(IDS[0]), normal(IDS[1])])
        q1 = build_review_queue(IDS[:2], focal, [], mode="hnlo_only", budget=1, tie_key=KEY)
        identity = replace(focal.identity, model_id="another-focal", run_id="another-run",
                           series_id="another-series", configuration_id="another-config")
        q2 = build_review_queue(IDS[:2], ModelResults(identity, focal.records), [],
                                mode="hnlo_only", budget=1, tie_key=KEY)
        self.assertEqual(review_ids(q1), review_ids(q2))

    def test_mandatory_order_is_keyed_and_input_order_invariant(self):
        rows = [Result(s, "INVALID") for s in IDS]
        q = self.queue(IDS, rows, budget=3)
        self.assertEqual(q, self.queue(reversed(IDS), reversed(rows), budget=3))
        self.assertEqual(q["backlog"]["mandatory"], 6)
        self.assertNotEqual(review_ids(q), review_ids(self.queue(IDS, rows, budget=3, key=b"other")))

    def test_input_immutability_and_output_detachment(self):
        ids, focal, peers = synthetic_inputs()
        before = copy.deepcopy((ids, focal, peers))
        q = build_review_queue(ids, focal, peers, mode="combined", budget=3, tie_key=KEY)
        self.assertEqual((ids, focal, peers), before)
        q["cases"][0]["outputs"][0]["predicted_safety_level"] = "changed"
        q["coverage"]["models"][0]["identity"]["run_id"] = "changed"
        q["review"][0]["reasons"].append("changed")
        self.assertEqual((ids, focal, peers), before)
        with self.assertRaises(FrozenInstanceError):
            focal.records[0].status = "INVALID"
        mutable_rows = [normal(IDS[0])]
        s = source("a", mutable_rows)
        mutable_rows.clear()
        self.assertEqual(len(s.records), 1)

    def test_identity_and_model_outputs_preserved_separately(self):
        q = self.queue(IDS[:1], [normal(IDS[0])],
                       (source("peer", [Result(IDS[0], "SUCCESS", "Level01")]),), "combined")
        self.assertEqual([o["predicted_safety_level"] for o in q["cases"][0]["outputs"]],
                         ["Level04", "Level01"])
        identity = q["coverage"]["models"][0]["identity"]
        self.assertEqual(identity, {"model_id": "focal", "model_revision": "revision",
                                    "implementation_id": "implementation", "configuration_id": "configuration",
                                    "run_id": "run", "series_id": "series", "attempt_id": "attempt"})

    def test_gt_and_answer_metadata_not_accepted_by_ranker(self):
        for field in ("true_safety_level", "ground_truth", "domain", "filename", "raw_output"):
            with self.subTest(field=field), self.assertRaises(TypeError):
                Result(IDS[0], "SUCCESS", "Level04", **{field: "Level01"})
        with self.assertRaises(ValueError):
            self.queue([SampleRecord(IDS[0], "Level01")], [])
        with self.assertRaises(TypeError):
            build_review_queue(IDS[:1], source("focal", [normal(IDS[0])]), (),
                               mode="hnlo_only", budget=1, tie_key=KEY, ground_truth={IDS[0]: "Level01"})

    def test_gt_changes_posthoc_counts_never_queue_or_detection_claim(self):
        q = self.queue(IDS[:2], [normal(IDS[0], 4), normal(IDS[1], 1)], budget=1)
        original = copy.deepcopy(q)
        a = evaluate_synthetic_queue(q, (SampleRecord(IDS[0], "Level01"), SampleRecord(IDS[1], "Level04")))
        b = evaluate_synthetic_queue(q, (SampleRecord(IDS[0], "Level04"), SampleRecord(IDS[1], "Level01")))
        self.assertEqual((a["routed_to_review_count"], b["routed_to_review_count"]), (1, 0))
        self.assertEqual(q, original)
        for result in (a, b):
            self.assertEqual(result["human_detection"], "NOT_MEASURED")
            self.assertEqual(result["human_correction"], "NOT_MEASURED")
        with self.assertRaises(ValueError):
            evaluate_synthetic_queue(q, (SampleRecord(IDS[0], "Level01"),))

    def test_synthetic_proposed_qualification_markers_and_strict_json(self):
        q = self.queue(IDS[:1], [normal(IDS[0])])
        self.assertEqual(q["data_status"], "SYNTHETIC_ONLY")
        self.assertEqual(q["policy_status"], "PROPOSED_NOT_FROZEN")
        self.assertEqual(q["qualification"], "NOT_SCIENTIFICALLY_QUALIFIED")
        self.assertEqual(json.loads(json.dumps(q, allow_nan=False)), q)

    def test_signal_comparison_union_mandatory_and_intersection_eligible(self):
        # a: no h; b: no peer; c,d: both signals; e: focal hazard.
        ids = IDS[:5]
        focal = source("focal", [normal(ids[0], None), normal(ids[1], 1),
                                  normal(ids[2], 9), normal(ids[3], -2),
                                  Result(ids[4], "SUCCESS", "Level01")])
        peer = source("peer", [Result(ids[0], "SUCCESS", "Level04"),
                               Result(ids[2], "SUCCESS", "Level04"),
                               Result(ids[3], "SUCCESS", "Level01")])
        result = compare_review_queues(iter(ids), focal, iter([peer]), budget=3, tie_key=KEY)
        self.assertEqual(result, compare_review_queues(reversed(ids), focal, [peer], budget=3, tie_key=KEY))
        self.assertEqual([result["operational"][m]["mandatory_count"] for m in MODES], [1, 1, 2])
        for mode in MODES:
            q = result["signal_control"][mode]
            self.assertEqual((q["mandatory_count"], q["eligible_count"], q["slots_used"]), (2, 2, 3))
            self.assertEqual(set(review_ids(q)[:2]), set(ids[:2]))
            self.assertEqual(review_ids(q)[2], ids[2] if mode == "hnlo_only" else ids[3])
            self.assertIn("ARTIFICIAL_WORKLOAD", q["comparison_scope"])
            self.assertEqual(q["backlog"]["ranked"], 1)
            self.assertNotIn(ids[4], review_ids(q))
        result["signal_control"]["hnlo_only"]["cases"][0]["reasons"].append("changed")
        self.assertNotIn("changed", json.dumps(result["operational"]))

    def test_signal_comparison_overload_includes_missingness_union(self):
        focal = source("focal", [normal(IDS[0], None), normal(IDS[1], 4)])
        peer = source("peer", [Result(IDS[0], "SUCCESS", "Level01")])
        q = compare_review_queues(IDS[:2], focal, [peer], budget=1, tie_key=KEY)
        self.assertEqual(q["operational"]["hnlo_only"]["status"], "WITHIN_CAPACITY")
        self.assertEqual(q["operational"]["peer_only"]["status"], "WITHIN_CAPACITY")
        for result in q["signal_control"].values():
            self.assertEqual(result["status"], "OVERLOAD")
            self.assertEqual((result["slots_used"], result["backlog"]["mandatory"]), (1, 1))
        with self.assertRaises(ValueError):
            compare_review_queues("", source("focal", []), [source("peer", [])], budget=0, tie_key=KEY)


class TriageDemoTests(unittest.TestCase):
    def test_demo_handwritten_counts_and_operational_comparison(self):
        report = build_report(budget=3, tie_key=KEY)
        self.assertEqual(report, build_report(budget=3, tie_key=KEY))
        self.assertFalse(report["model_execution"])
        for mode, expected_ranked, routed in (("hnlo_only", IDS[0], 1),
                                              ("peer_only", IDS[1], 2), ("combined", IDS[1], 2)):
            q = report["queues"][mode]
            self.assertEqual((q["planned_count"], q["focal_normal_count"], q["eligible_count"],
                              q["mandatory_count"], q["slots_used"], q["backlog"]["total"]),
                             (6, 4, 3, 2, 3, 2))
            self.assertEqual(set(review_ids(q)[:2]), {IDS[3], IDS[4]})
            self.assertEqual(review_ids(q)[2], expected_ranked)
            self.assertEqual(report["post_hoc_fixture_counts"][mode]["synthetic_false_safe_count"], 3)
            self.assertEqual(report["post_hoc_fixture_counts"][mode]["routed_to_review_count"], routed)
            self.assertEqual(report["post_hoc_fixture_counts"][mode]["routed_via_mandatory"], 1)

    def test_real_cli_stdlib_only_no_files_from_empty_directory(self):
        code = ("import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); "
                "runpy.run_module('scripts.demo_triage_cpu',run_name='__main__')")
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(ROOT),
                                     "--budget", "3", "--tie-seed", KEY.decode()],
                                    cwd=empty, capture_output=True, text=True, check=False)
            self.assertEqual(list(Path(empty).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), build_report(budget=3, tie_key=KEY))

    def test_cli_requires_explicit_budget_and_seed_and_rejects_negative(self):
        for args in ([], ["--budget", "-1", "--tie-seed", "public"],
                     ["--budget", "0"], ["--budget", "0", "--tie-seed", ""]):
            result = subprocess.run([sys.executable, "-S", "-B", "-m", "scripts.demo_triage_cpu", *args],
                                    cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
