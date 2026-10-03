"""Tiny handcrafted records only; no dataset/image/model access."""

from dataclasses import replace
from itertools import permutations
import json
import random
import unittest

from safeshift.protocol.d5_engine import classification, rq1, rq2, direct_grounding, weak_proxy
from safeshift.protocol.d5_geometry import assignment, containment, pointing, valid_box
from safeshift.protocol.d5_statistics import ClusterUnit, bootstrap, bootstrap_draws, classification_statistic, interval
from safeshift.protocol.metrics import ClassificationInput, SpatialInput, GroundTruthAtom, OriginalRegion
from safeshift.protocol.reporting import report, render_json
from safeshift.protocol.schema import Classification, Evidence, Grounding, Hazard, ParseResult, SAFETY_LEVELS


def cls(i, true, predicted, domain="a", cluster=None, atoms=()):
    parsed = ParseResult("INVALID") if predicted is None else ParseResult("SUCCESS", Classification(predicted), response_schema_valid=True)
    return ClassificationInput(str(i), true, domain, cluster or str(i), parsed, frozenset(atoms))


def region(box=(0., 0., 1., 1.), *, points=None, label="Object", rid="r"):
    x, y, xx, yy = box
    return OriginalRegion(rid, label, points or ((x, y), (xx, y), (xx, yy), (x, yy)), box, "normalized", 100, 100)


def atom(h="SMOKE", aid="a", *, regions=None, support="DIRECT"):
    return GroundTruthAtom(aid, h, support, regions or (region(),))


def spatial(boxes=(), atoms=None, *, weak=(), unsupported=(), correct=True):
    hazards = tuple(Hazard(h, (Evidence(b),)) for h, b in boxes)
    parsed = ParseResult("SUCCESS", Grounding(hazards), response_schema_valid=True,
                         boxes_attempted=len(boxes), boxes_valid=len(boxes))
    return SpatialInput("s", "PARTICIPATING", parsed, (atom(),) if atoms is None else atoms,
                        weak, unsupported, correct)


class ClassificationTests(unittest.TestCase):
    def test_hand_calculated_confusion_and_safety_rates(self):
        samples = tuple(cls(i, t, p) for i, (t, p) in enumerate([
            ("Level01", "Level01"), ("Level01", "Level02"), ("Level01", "Level04"),
            ("Level02", "Level02"), ("Level03", "Level03"), ("Level04", "Level01")]))
        r = classification(samples)
        self.assertAlmostEqual(r["balanced_accuracy"], 7 / 12)
        self.assertAlmostEqual(r["macro_f1"], (.4 + 2 / 3 + 1) / 4)
        self.assertEqual(r["raw_accuracy_descriptive"]["value"], .5)
        self.assertEqual(r["anomaly_recall"], {"value": .8, "numerator": 4, "denominator": 5})
        self.assertEqual(r["anomaly_fnr"]["value"], .2)
        self.assertEqual(r["anomaly_fpr"]["value"], 1.)
        self.assertEqual(r["level01_fnr"]["value"], 2 / 3)
        self.assertEqual(r["critical_miss_rate"]["value"], 1 / 3)
        self.assertEqual(r["critical_downgrade_rate"]["value"], 1 / 3)
        self.assertEqual(r["row_normalized_confusion_matrix"]["Level01"]["Level04"], 1 / 3)

    def test_missing_class_no_zero_fill(self):
        r = classification((cls(1, "Level04", "Level04"),))
        self.assertEqual(r["K"], 1)
        self.assertEqual(r["balanced_accuracy"], 1.)
        self.assertIsNone(r["per_class"]["Level01"]["recall"])
        self.assertIsNone(r["anomaly_fnr"]["value"])
        self.assertIsNone(classification((cls(1, "Level04", "Level04"),), required_classes=SAFETY_LEVELS)["macro_f1"])

    def test_zero_true_positive_supported_class_f1_zero(self):
        r = classification((cls(1, "Level01", "Level04"),))
        self.assertEqual(r["per_class"]["Level01"]["precision"], 0.)
        self.assertEqual(r["per_class"]["Level01"]["f1"], 0.)

    def test_invalid_classification_never_repaired_to_normal(self):
        r = classification((cls(1, "Level01", None),))
        self.assertIsNone(r["anomaly_fnr"]["value"])
        self.assertEqual(r["confusion_matrix"]["Level01"]["INVALID"], 1)
        self.assertEqual(r["confusion_matrix"]["Level01"]["Level04"], 0)
        self.assertEqual(r["exact_safety_level_error_rate"]["value"], 1.)

    def test_rq1_class_conditional_and_only_four_class_spread(self):
        samples = tuple(cls(f"{d}{i}", c, c if d == "a" else "Level04", d)
                        for d in ("a", "b") for i, c in enumerate(SAFETY_LEVELS))
        samples += (cls("m", "Level01", "Level04", "metallurgy"),)
        r = rq1(samples)
        self.assertEqual(r["balanced_accuracy_comparable_domains"], ["a", "b"])
        self.assertEqual(r["balanced_accuracy_spread_diagnostic"], .75)
        self.assertEqual(r["class_conditional"]["Level01"]["observed_worst_domain_minimum"], 0.)
        row = r["class_conditional"]["Level01"]["domains"][1]
        self.assertAlmostEqual(row["pooled_to_domain_gap"], 1 / 3)
        self.assertEqual(row["support"], 1)
        self.assertEqual(r["class_conditional"]["Level01"]["domains"][2]["warning"], "Sparse-Support / Descriptive-Only")

    def test_rq2_memberships_nonadditive_group_union(self):
        samples = (cls(1, "Level01", "Level04", atoms=("SMOKE", "OPEN_FLAME")),
                   cls(2, "Level02", "Level02", atoms=("SMOKE",)))
        primary, secondary = rq2(samples), rq2(samples, grouped=True)
        self.assertEqual(len(primary["strata"]), 12)
        self.assertEqual(primary["strata"]["SMOKE"]["n_images"], 2)
        self.assertEqual(primary["strata"]["OPEN_FLAME"]["n_images"], 1)
        self.assertEqual(secondary["strata"]["A_FIRE_AND_SMOKE"]["n_images"], 2)
        self.assertFalse(primary["counts_additive"])
        self.assertTrue(primary["non_independent"])
        self.assertIsNone(primary["strata"]["NO_MASK"]["level01_recall"]["value"])
        self.assertEqual(primary["strata"]["SMOKE"]["anomaly_to_normal_miss_rate"]["value"], .5)


class MatchingTests(unittest.TestCase):
    def test_mode_a_threshold_free_differs_from_mode_b(self):
        w = [[.9, .25], [.25, 0.]]
        self.assertAlmostEqual(sum(v for _, _, v in assignment(w)), .9)
        b = assignment(w, threshold=.25)
        self.assertEqual(len(b), 2)
        self.assertEqual(sum(v for _, _, v in b), .5)

    def test_mode_b_tie_break_iou(self):
        b = assignment([[.5, .8], [.8, .5]], threshold=.5)
        self.assertEqual(b, ((0, 1, .8), (1, 0, .8)))

    def test_assignment_against_exhaustive_small_graphs(self):
        rng = random.Random(11)
        for _ in range(70):
            n, p = rng.randrange(1, 5), rng.randrange(1, 5)
            w = [[rng.choice([None, 0., .24, .25, .5, .9, 1.]) for _ in range(p)] for _ in range(n)]
            for threshold in (None, .25, .5):
                best = (-1, -1.)
                for columns in permutations(range(p + n), n):
                    edges = [w[j][k] for j, k in enumerate(columns) if k < p]
                    if any(v is None or (threshold is not None and v < threshold) for v in edges):
                        continue
                    key = (len(edges) if threshold else 0, sum(edges))
                    best = max(best, key)
                got = assignment(w, threshold=threshold)
                self.assertEqual(len({p for _, p, _ in got}), len(got))
                self.assertEqual(len(got) if threshold else 0, best[0])
                self.assertAlmostEqual(sum(v for _, _, v in got), best[1])

    def test_invalid_geometry_and_threshold_fail_closed(self):
        for b in ((0, 0, float('nan'), 1), (0, 0, 2, 1), (True, 0, 1, 1), (1, 0, 0, 1)):
            with self.assertRaises(ValueError):
                valid_box(b)
        with self.assertRaises(ValueError):
            assignment([[1.]], threshold=.3)


class SpatialTests(unittest.TestCase):
    def test_no_prediction_reuse_and_candidates_are_one_atom(self):
        a = atom(regions=(region((0, 0, .5, .5)), region()))
        sample = spatial((("SMOKE", (0, 0, 1, 1)),), (a, replace(a, atom_id="b")))
        r = direct_grounding((sample,))
        self.assertEqual(r["n_atoms"], 2)
        self.assertEqual(r["end_to_end_mean_iou"], .5)
        self.assertEqual(r["median_iou"], .5)
        self.assertEqual(r["thresholds"]["@0.50"]["Hit"]["value"], .5)
        self.assertEqual(r["covariates"][0]["candidate_region_count"], 2)
        self.assertEqual(r["covariates"][0]["AtomSize"], 1.)

    def test_cross_class_unmatched_box_counts_and_conditional_zero(self):
        r = direct_grounding((spatial((("OPEN_FLAME", (0, 0, 1, 1)),)),))
        self.assertEqual(r["end_to_end_mean_iou"], 0.)
        self.assertEqual(r["parse_conditional_mean_iou"], 0.)
        self.assertEqual(r["thresholds"]["@0.25"]["evidence_precision"]["denominator"], 1)

    def test_missing_prediction_zero_e2e_na_conditional(self):
        r = direct_grounding((spatial(),))
        self.assertEqual(r["end_to_end_mean_iou"], 0.)
        self.assertIsNone(r["parse_conditional_mean_iou"])

    def test_polygon_pointing_not_derived_box(self):
        triangle = region(points=((0, 0), (1, 0), (0, 1)))
        box = (.7, .7, .9, .9)
        self.assertFalse(pointing(box, (triangle,)))
        self.assertTrue(pointing((.1, .1, .3, .3), (triangle,)))
        pixels = replace(triangle, original_polygon=((0, 0), (100, 0), (0, 100)), coordinate_frame="original_pixels")
        self.assertFalse(pointing(box, (pixels,)))
        r = direct_grounding((spatial((("SMOKE", box),), (atom(regions=(triangle,)),)),))
        self.assertEqual(r["pointing_hit"]["value"], 0.)
        self.assertEqual(r["covariates"][0]["AtomSize"], .5)

    def test_concave_original_polygon_and_containment(self):
        concave = region(points=((0, 0), (1, 0), (1, .2), (.2, .2), (.2, 1), (0, 1)), label="Person")
        self.assertFalse(pointing((.5, .5, .9, .9), (concave,)))
        self.assertAlmostEqual(containment((0, 0, 1, 1), concave), .36)
        self.assertAlmostEqual(containment((0, 0, 1, 1), region(points=((0, 0), (1, 0), (0, 1)))), .5)

    def test_parse_failure_e2e_zero_diagnostic_not_promoted(self):
        s = spatial((("SMOKE", (0, 0, 1, 1)),))
        failed = ParseResult("COORDINATE_ERROR", response_schema_valid=True, boxes_attempted=2, boxes_valid=1,
                             diagnostic_evidence=(Evidence((0, 0, 1, 1)),))
        s = replace(s, prediction=failed, diagnostic_hazards=(Hazard("SMOKE", (Evidence((0, 0, 1, 1)),)),))
        r = direct_grounding((s,))
        self.assertEqual(r["end_to_end_mean_iou"], 0.)
        self.assertEqual(r["parse_conditional_mean_iou"], 1.)
        self.assertEqual(r["PSR_response"]["value"], 1.)
        self.assertEqual(r["PSR_box"]["value"], .5)
        self.assertEqual(r["thresholds"]["@0.25"]["evidence_precision"]["denominator"], 2)
        self.assertEqual(r["thresholds"]["@0.25"]["Hit"]["value"], 0.)

    def test_unlabeled_failed_diagnostics_not_guessed(self):
        s = replace(spatial(), prediction=ParseResult("INVALID", boxes_attempted=1, boxes_valid=1))
        r = direct_grounding((s,))
        self.assertIsNone(r["parse_conditional_mean_iou"])
        self.assertEqual(r["diagnostic_boxes_without_hazard_identity"], 1)

    def test_cgi_only_classification_correct_and_no_atom_hit(self):
        good = spatial((("SMOKE", (0, 0, 1, 1)),))
        missed = replace(spatial(), sample_id="miss")
        incorrect = replace(spatial(), sample_id="incorrect", classification_correct=False)
        r = direct_grounding((good, missed, incorrect))["thresholds"]["@0.50"]
        self.assertEqual(r["CGI_zero_grounding"]["value"], .5)
        self.assertEqual(r["CGI_atom"]["denominator"], 2)
        unknown = direct_grounding((replace(good, classification_correct=None),))
        self.assertIsNone(unknown["thresholds"]["@0.25"]["CGI_atom"]["value"])

    def test_unsupported_explicit_exclusion(self):
        excluded = GroundTruthAtom("u", "DOOR_OPEN", "NO_CURRENT_SPATIAL_GT", (), "no annotation")
        r = direct_grounding((spatial(atoms=(), unsupported=(excluded,)),))
        self.assertEqual(r["unsupported_atoms_excluded"], 1)
        self.assertEqual(r["n_atoms"], 0)
        self.assertIsNone(r["end_to_end_mean_iou"])

    def test_inconsistent_parse_counts_rejected(self):
        s = spatial((("SMOKE", (0, 0, 1, 1)),))
        with self.assertRaises(ValueError):
            direct_grounding((replace(s, prediction=replace(s.prediction, boxes_valid=0)),))
        with self.assertRaises(ValueError):
            weak_proxy((replace(s, prediction=ParseResult("INVALID", boxes_valid=-1)),))

    def test_not_participating_is_never_zero(self):
        s = SpatialInput("s", "NOT_PARTICIPATING", None, (), (), ())
        self.assertEqual(direct_grounding((s,)), {"participation": "NOT_PARTICIPATING", "metrics": None})
        self.assertEqual(weak_proxy((s,))["metrics"], None)
        with self.assertRaises(ValueError):
            direct_grounding((s, spatial()))

    def test_weak_proxy_any_original_person_single_person_subset(self):
        person1 = region((0, 0, .4, 1), label="Person", rid="1")
        person2 = region((.6, 0, 1, 1), label="Person", rid="2")
        weak = atom("NO_HELMET", regions=(person1, person2), support="WEAK_PROXY")
        s = spatial((("NO_HELMET", (.7, .1, .9, .3)),), atoms=(), weak=(weak,))
        r = weak_proxy((s,))
        self.assertEqual(r["center_in_proxy_PLC"]["value"], 1.)
        self.assertAlmostEqual(r["box_containment_diagnostic"], 1.)
        self.assertIsNone(r["single_person_proxy_subset"]["center_in_proxy_PLC"]["value"])
        single = replace(s, weak_proxy_atoms=(replace(weak, candidate_regions=(person2,)),))
        self.assertEqual(weak_proxy((single,))["single_person_proxy_subset"]["center_in_proxy_PLC"]["value"], 1.)
        self.assertFalse(r["true_grounding_accuracy"])


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.units = (ClusterUnit("a1", "a", "p"), ClusterUnit("a2", "a", "p"),
                      ClusterUnit("a3", "a", "q"), ClusterUnit("b1", "b", "p"))

    def test_seed_reproducibility_order_invariance_cluster_integrity(self):
        draws = bootstrap_draws(self.units)
        self.assertEqual(len(draws), 2000)
        self.assertEqual(draws, bootstrap_draws(tuple(reversed(self.units))))
        for draw in draws:
            self.assertEqual(draw.count("a1"), draw.count("a2"))
            self.assertEqual(draw.count("a1") + draw.count("a3"), 2)
            self.assertEqual(draw.count("b1"), 1)
        self.assertGreater(len(set(draws)), 1)

    def test_pair_uses_identical_draws_and_na_intersection(self):
        seen_a, seen_b = [], []
        def a(draw):
            seen_a.append(draw)
            return draw.count("a1") if "a3" in draw else None
        def b(draw):
            seen_b.append(draw)
            return draw.count("a1") - .5
        r = bootstrap(self.units, a, metric_b=b)
        self.assertEqual(seen_a, seen_b)
        self.assertEqual(r["paired_difference"]["ci95"], [.5, .5])
        self.assertEqual(r["a"]["valid_replicates"], r["paired_difference"]["valid_paired_replicates"])
        self.assertLess(r["a"]["valid_replicates"], 2000)

    def test_missing_class_replicate_na_not_support_only(self):
        samples = (cls("a", "Level01", "Level01"), cls("b", "Level04", "Level04"))
        stat = classification_statistic(samples, "balanced_accuracy")
        self.assertIsNone(stat(("a", "a")))
        self.assertEqual(stat(("a", "b")), 1.)

    def test_percentiles_and_all_na(self):
        r = interval(tuple(range(2000)))
        self.assertEqual(r["ci95"], [49.975, 1949.0249999999999])
        self.assertIsNone(interval((None,) * 2000)["ci95"])
        with self.assertRaises(ValueError):
            interval((float('nan'),) * 2000)
        with self.assertRaises(ValueError):
            bootstrap_draws(self.units, seed=5)


class ReportingTests(unittest.TestCase):
    def test_separate_primary_exploratory_and_no_fake_zero(self):
        r = report("qwen3", exploratory_spatial=(spatial(),))
        self.assertEqual(r["primary_direct_RQ3_A"]["participation"], "NOT_PARTICIPATING")
        self.assertIsNone(r["primary_direct_RQ3_A"]["metrics"])
        self.assertEqual(r["exploratory_grounding"]["direct"]["end_to_end_mean_iou"], 0.)
        self.assertFalse(r["exploratory_grounding"]["production_qualification"])
        self.assertEqual(render_json(r), render_json(json.loads(render_json(r))))
        self.assertEqual(report("paligemma")["classification_RQ1"]["participation"], "NOT_PARTICIPATING")

    def test_role_guards(self):
        for model in ("qwen3", "qwen2_5", "internvl3", "paligemma"):
            with self.assertRaises(ValueError):
                report(model, primary_spatial=(spatial(),))
        for model in ("qwen2_5", "internvl3"):
            with self.assertRaises(ValueError):
                report(model, exploratory_spatial=(spatial(),))
        with self.assertRaises(ValueError):
            report("paligemma", classification_samples=(cls(1, "Level04", "Level04"),))


if __name__ == "__main__":
    unittest.main()
