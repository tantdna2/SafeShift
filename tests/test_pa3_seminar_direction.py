"""Seminar-direction diagnostic CPU tests. Synthetic fixtures/API doubles only.

No GPU, model, download or InspecSafe read; the committed manifests are checked
as committed metadata only (no image is opened).
"""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from safeshift.ls1 import tokenizer as token_module
from safeshift.ls1.core import distribution
from safeshift.ls1.evaluate import anomaly_log_odds
from safeshift.pa3.artifacts import json_bytes
from safeshift.pa3.native import access, analysis, preflight, seminar, seminar_verdict, workflow
from safeshift.pa3.native.seminar_cohort import pretty
from safeshift.pa3.native.journal import Journal, run_path
from safeshift.pa3.native.native_score import pending

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data/manifests/pa3_seminar_direction_cohort_receipt.v1.json"


def candidates(levels=("Level01", "Level02", "Level03"), anomaly=12, normal=12):
    rows = []
    for domain, _ in seminar.STRATA:
        for i in range(normal):
            rows.append({"sample_id": f"{domain}-Level04-Wheeled-{i:06d}-001", "domain": domain, "level": "Level04",
                         "group": f"{domain}-n{i}"})
        for i in range(anomaly):
            level = levels[i % len(levels)]
            rows.append({"sample_id": f"{domain}-{level}-Wheeled-{100 + i:06d}-001", "domain": domain, "level": level,
                         "group": f"{domain}-a{i}"})
    return rows


class SelectionTests(unittest.TestCase):
    def test_quota_order_level03_floor_and_order_independence(self):
        rows = candidates()
        out = seminar.select(rows, [])
        self.assertEqual(out["status"], "SELECTED")
        self.assertEqual(len(out["selected_ids"]), 90)
        shuffled = rows[:]
        random.Random(7).shuffle(shuffled)
        self.assertEqual(seminar.select(shuffled, []), out)
        for domain, quota in seminar.STRATA:
            trace = out["trace"][domain + "/Anomaly"]
            self.assertEqual(trace["selected"], quota)
            # Floor is a minimum; rank-based fill may add further Level03.
            self.assertGreaterEqual(trace["selected_level_counts"]["Level03"], min(2, trace["eligible_level_counts"]["Level03"]))
            self.assertEqual(out["trace"][domain + "/Normal"]["selected"], quota)
        self.assertEqual(out["inference_order"], sorted(out["selected_ids"], key=seminar.order_key))
        self.assertNotEqual(out["inference_order"], out["selected_ids"])

    def test_level03_floor_takes_all_when_fewer_than_two(self):
        rows = [r for r in candidates(anomaly=15) if not (r["level"] == "Level03" and r["domain"] == "tunnel")]
        rows.append({"sample_id": "tunnel-Level03-Wheeled-999999-001", "domain": "tunnel", "level": "Level03", "group": "t3"})
        out = seminar.select(rows, [])
        self.assertIn("tunnel-Level03-Wheeled-999999-001", out["selected_ids"])

    def test_one_per_mandatory_group_exclusions_and_shortage_stop(self):
        rows = candidates(anomaly=10, normal=10)
        for r in rows:
            if r["domain"] == "power" and r["level"] == "Level04":
                r["group"] = "power-shared-point"
        out = seminar.select(rows, [])
        self.assertEqual(out["status"], "STOP_INSUFFICIENT_ELIGIBLE_GROUPS")
        self.assertEqual(out["shortages"], {"power/Normal": 9})
        self.assertEqual(out["selected_ids"], [])
        rows = candidates(anomaly=10, normal=10)
        excluded = [r["sample_id"] for r in rows if r["domain"] == "coal_conveyor" and r["level"] != "Level04"][:1]
        out = seminar.select(rows, excluded)
        self.assertEqual(out["shortages"], {"coal_conveyor/Anomaly": 1})
        with self.assertRaisesRegex(ValueError, "EXCLUSION_OUTSIDE"):
            seminar.select(rows, ["unknown-id"])

    def test_no_score_or_model_output_input(self):
        rows = candidates()
        rows[0]["pa3_score"] = 1.0
        with self.assertRaisesRegex(ValueError, "CANDIDATE_SCHEMA"):
            seminar.select(rows, [])


class CommittedManifestTests(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads(RECEIPT.read_bytes())
        self.cohort = seminar.load_cohort(ROOT, self.receipt["cohort_manifest_sha256"], self.receipt["inference_manifest_sha256"])

    def test_exact_locked_cohort_counts_and_exclusions(self):
        rows = list(self.cohort.values())
        self.assertEqual(len(rows), 90)
        self.assertEqual(sum(r["binary_class"] == "Normal" for r in rows), 45)
        self.assertEqual(sum(r["primary"] for r in rows), 80)
        manifest = json.loads((ROOT / seminar.COHORT).read_bytes())
        self.assertEqual(manifest["rule"], seminar.RULE)
        self.assertFalse(manifest["execution_authority"])
        excluded = set(manifest["exclusions"]["exact_test_duplicate_train_ids"])
        self.assertIn("metallurgy-Level01-SuspendedRail-002660-001", excluded)
        self.assertFalse(excluded & set(self.cohort))
        self.assertTrue(set(self.cohort) <= set(manifest["exposure_reservation"]["observed_ids"]))
        self.assertTrue(all(r["image_locator"].startswith("DATA_PATH/train/") for r in rows))
        self.assertEqual(sum(r["level"] == "Level03" for r in rows),
                         sum(t["selected_level_counts"]["Level03"] for t in manifest["selection"]["trace"].values()))

    def test_inference_manifest_is_gt_free_projection(self):
        inference = json.loads((ROOT / seminar.INFERENCE).read_bytes())
        self.assertTrue(all(set(r) == {"sample_id", "image_locator", "image_sha256"} for r in inference["samples"]))
        text = (ROOT / seminar.INFERENCE).read_text(encoding="utf-8")
        for key in ('"level"', '"binary_class"', '"domain"', '"text_domain"'):
            self.assertNotIn(key, text)

    def test_tamper_reorder_and_test_locator_rejected(self):
        data = (ROOT / seminar.INFERENCE).read_bytes()
        with self.assertRaisesRegex(ValueError, "CHECKSUM"):
            seminar.load_cohort(ROOT, self.receipt["cohort_manifest_sha256"], "0" * 64)
        value = json.loads(data)
        swapped = json.loads(data)
        swapped["samples"][0], swapped["samples"][1] = swapped["samples"][1], swapped["samples"][0]
        with self.assertRaisesRegex(ValueError, "ORDER"):
            seminar.validate_inference(swapped)
        value["samples"][0]["image_locator"] = value["samples"][0]["image_locator"].replace("/train/", "/test/")
        with self.assertRaisesRegex(ValueError, "TRAIN_LOCATOR"):
            seminar.validate_inference(value)
        value["samples"] = value["samples"][1:]
        with self.assertRaisesRegex(ValueError, "EXACT_90"):
            seminar.validate_inference(value)

    def test_committed_not_executed_verdict_is_regenerable(self):
        diag = seminar_verdict.evaluate(None, self.cohort, {"stage": "NOT_EXECUTED_PENDING_DIAGNOSTIC_AUTHORITY",
                                                            "gpu_runs": 0, "audit_integrity": None})
        self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.KEEP)
        self.assertEqual(diag["decision"]["reason_category"], "NOT_EXECUTED")
        self.assertEqual((ROOT / seminar_verdict.VERDICT).read_bytes(), seminar_verdict.render_markdown(diag))


class AuthorityTests(unittest.TestCase):
    SETTINGS = {"mode": seminar.MODE, "run_id": seminar.RUN_ID, "source_commit": "a" * 40,
                **{k: "b" * 64 for k in access.DIAGNOSTIC_GRANT}}

    def test_committed_grant_is_null_and_prior_authority_untouched(self):
        value = json.loads((ROOT / access.DIAGNOSTIC_AUTHORITY).read_bytes())
        self.assertIsNone(value["grant"])
        self.assertEqual(value["scope"], access.DIAGNOSTIC)
        with self.assertRaisesRegex(PermissionError, "GRANT_PENDING"):
            access.require(seminar.MODE, self.SETTINGS, ROOT)
        with self.assertRaisesRegex(PermissionError, "GRANT_PENDING"):
            seminar.inference_samples(ROOT, self.SETTINGS)
        prior = json.loads((ROOT / access.AUTHORITY).read_bytes())
        self.assertIsNone(prior["pilot"])
        self.assertEqual(prior["technical"], access.TECHNICAL)
        self.assertEqual((ROOT / access.AUTHORITY).read_bytes(), preflight.git_blob(ROOT, access.DIAGNOSTIC_BASE, access.AUTHORITY))
        with self.assertRaises(PermissionError):
            access.require("pilot-train", {"mode": "pilot-train", "source_commit": "a" * 40}, ROOT)

    def test_scope_denied_before_authority_read(self):
        with patch.object(access, "diagnostic_authority", side_effect=AssertionError("SOURCE_READ")):
            for change in ({"run_id": "pa3-qwen-seminar-direction-90-retry"}, {"mode": "technical"},
                           {"revision": "main"}, {"precision": "BF16"}, {"pilot_manifest_input": "m.json"},
                           {"cohort_plan_sha256": "c" * 64}, {"technical_source_commit": "d" * 40}):
                with self.subTest(change=change), self.assertRaises(PermissionError):
                    access.require(seminar.MODE, {**self.SETTINGS, **change})

    def test_grant_binding_is_not_caller_authority(self):
        grant = {**{k: "b" * 64 for k in access.DIAGNOSTIC_GRANT}, "approval": "LEAD-FIXTURE"}
        with patch.object(access, "diagnostic_authority", return_value={"grant": grant}):
            self.assertEqual(access.require(seminar.MODE, self.SETTINGS)["grant"], grant)
            for key in access.DIAGNOSTIC_GRANT:
                with self.subTest(key=key), self.assertRaises(PermissionError):
                    access.require(seminar.MODE, {**self.SETTINGS, key: "e" * 64})

    def topology(self, tmp, *, grant=True, extra=None, prior_change=False, f1_shape=None, base_shape=None):
        repo = Path(tmp)
        def git(*args):
            return subprocess.check_output(["git", "-C", tmp, *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-b", "main"); git("config", "core.autocrlf", "false")
        git("config", "user.email", "fixture@example.invalid"); git("config", "user.name", "CPU fixture")
        prior = repo / access.AUTHORITY
        prior.parent.mkdir(parents=True)
        prior.write_bytes(b'{"pilot": null}\n'); (repo / "code.txt").write_text("base")
        git("add", "."); git("commit", "-m", "base")
        base = git("rev-parse", "HEAD")
        git("checkout", "-b", "candidate")
        if f1_shape == "indirect":  # F1's parent is an intermediate commit, not base
            (repo / "code.txt").write_text("intermediate"); git("add", "."); git("commit", "-m", "F0")
        (repo / "code.txt").write_text("implementation")
        if prior_change:
            prior.write_bytes(b'{"pilot": {"grant": "self"}}\n')
        git("add", "."); git("commit", "-m", "F1")
        if f1_shape == "merge":  # F1 is a merge commit with two parents
            git("checkout", "-b", "side", base); (repo / "side.txt").write_text("side")
            git("add", "."); git("commit", "-m", "side"); git("checkout", "candidate")
            git("merge", "--no-ff", "side", "-m", "F1 merge")
        f1 = git("rev-parse", "HEAD")
        claimed = base
        if base_shape == "advanced":  # main moved on and the authority names it; F1's parent is old base
            git("checkout", "main"); git("commit", "--allow-empty", "-m", "main advanced")
            claimed = git("rev-parse", "HEAD"); git("checkout", "candidate")
        elif base_shape == "mismatch":  # authority base is not the merge's first parent
            claimed = f1
        value = {"base": claimed, "implementation": f1, "scope": access.DIAGNOSTIC,
                 "grant": {**{k: "b" * 64 for k in access.DIAGNOSTIC_GRANT}, "approval": "LEAD-FIXTURE"} if grant else None}
        (repo / access.DIAGNOSTIC_AUTHORITY).write_bytes(json_bytes(value))
        if extra:
            (repo / extra).write_text("not authority")
        git("add", "."); git("commit", "-m", "F2")
        f2 = git("rev-parse", "HEAD")
        git("checkout", "main"); git("merge", "--no-ff", "candidate", "-m", "fixture merge")
        return repo, git, f2, git("rev-parse", "HEAD"), base

    def test_real_git_standard_merge_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, git, f2, merge, base = self.topology(tmp)
            with patch.object(access, "DIAGNOSTIC_BASE", base):
                self.assertEqual(access.diagnostic_authority(repo, merge)["grant"]["approval"], "LEAD-FIXTURE")
                with self.assertRaisesRegex(PermissionError, "DRAFT_LOCKED"):
                    access.diagnostic_authority(repo, f2)
                (repo / "code.txt").write_text("dirty")
                with self.assertRaisesRegex(PermissionError, "DIRTY"):
                    access.diagnostic_authority(repo, merge)
                git("add", "."); git("commit", "-m", "later")
                with self.assertRaises(PermissionError):
                    access.diagnostic_authority(repo, git("rev-parse", "HEAD"))

    def test_null_grant_mixed_commit_and_prior_authority_change_denied(self):
        for options, error in (({"grant": False}, "GRANT_PENDING"), ({"extra": "other.txt"}, "AUTHORITY_ONLY"),
                               ({"prior_change": True}, "CHANGED_PRIOR_AUTHORITY"),
                               ({"f1_shape": "indirect"}, "IMPLEMENTATION_PARENT"),
                               ({"f1_shape": "merge"}, "IMPLEMENTATION_PARENT"),
                               ({"base_shape": "advanced"}, "IMPLEMENTATION_PARENT"),
                               ({"base_shape": "mismatch"}, "DRAFT_LOCKED")):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                repo, git, f2, merge, base = self.topology(tmp, **options)
                with patch.object(access, "DIAGNOSTIC_BASE", base), self.assertRaisesRegex(PermissionError, error):
                    access.diagnostic_authority(repo, merge)


def success(sid, z, label="Level03"):
    dist = distribution(list(z))
    details = {**dist, "raw_label_logits": list(z), "processed_label_scores": list(z),
               "full_vocab_log_probabilities": [x - 10 for x in z], "four_label_probability_mass": 0.5,
               "four_label_log_mass": math.log(0.5), "raw_argmax_id": 1, "processed_argmax_id": 1,
               "raw_and_processed_label_scores_equal": True, "generated_label": label,
               "decision": {"step": 3, "prefix_ids": [1], "format_wrapper_detected": False}}
    return {"sample_id": sid, "status": "SUCCESS", "attempted": True, "persisted": True, "parsed": True,
            "score": anomaly_log_odds(dist["log_probabilities"]), "details": details, "generated_label": label, "errors": []}


def invalid(sid):
    return {**pending(sid, attempted=True, persisted=True), "status": "INVALID", "errors": ["SCHEMA"]}


def synthetic_cohort():
    cohort = {}
    for domain, quota in seminar.STRATA:
        for cls in ("Normal", "Anomaly"):
            for i in range(quota):
                level = "Level04" if cls == "Normal" else ("Level01", "Level02", "Level03")[i % 3]
                sid = f"{domain}-{level}-Wheeled-{i + (0 if cls == 'Normal' else 500):06d}-001"
                cohort[sid] = {"sample_id": sid, "level": level, "binary_class": cls, "domain": domain,
                               "primary": domain in seminar.PRIMARY, "text_domain": domain, "domain_conflict": False,
                               "conservative_component": f"{domain}-{cls}-{i % 2}", "exposure": {"ls1_documentary_per_sample": False}}
    return cohort


def scored(cohort, pa3, label=lambda c, i: "Level03", drop=lambda c, i: False):
    """pa3(domain, binary, index) -> anomaly score S; z4 is set so S is exact."""
    rows, counter = [], {}
    for sid, c in cohort.items():
        i = counter[(c["domain"], c["binary_class"])] = counter.get((c["domain"], c["binary_class"]), -1) + 1
        if drop(c, i):
            rows.append(invalid(sid))
            continue
        lse = math.log(math.exp(0) + math.exp(0) + math.exp(4))
        rows.append(success(sid, (0.0, 0.0, 4.0, lse - pa3(c["domain"], c["binary_class"], i)), label(c, i)))
    return rows


EVIDENCE = {"audit_integrity": "PASS", "preflight_verified": 90, "exposure_sealed": True}


def run(rows, completed=True):
    return seminar_verdict.evaluate({"results": rows, "completed": completed, "sealed": True, "integrity": "PASS"},
                                    synthetic_cohort(), EVIDENCE)


class DecisionRuleTests(unittest.TestCase):
    def test_exact_boundary_auroc_075_passes_and_metallurgy_ignored(self):
        cohort = synthetic_cohort()
        target = {"coal_conveyor": 1.0, "oil_chemical": 0.75, "power": 0.75, "tunnel": 0.5}
        def pa3(domain, cls, i):
            if domain == "metallurgy":
                return 0.0
            if cls == "Normal":
                return 0.0
            return {1.0: 1.0, 0.75: 1.0 if i < 5 else 0.0, 0.5: 0.0}[target[domain]]
        diag = seminar_verdict.evaluate({"results": scored(cohort, pa3), "completed": True, "sealed": True, "integrity": "PASS"},
                                        cohort, EVIDENCE)
        m = diag["results"]["macro_primary"]
        self.assertEqual(m["macro_pa3_auroc"]["exact"], "3/4")
        self.assertEqual(m["macro_generated_label_auroc"]["exact"], "1/2")
        self.assertEqual(m["domains_pa3_greater"], 3)
        self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.GO)
        self.assertEqual(diag["results"]["metallurgy"]["auroc_pa3"]["value"], 0.5)
        self.assertIsNone(diag["results"]["sensitivity"]["confidence_interval"])
        self.assertEqual(diag["results"]["primary"]["auroc_generated_binary_label"]["value"], 0.5)

    def test_delta_boundary_015_and_just_below(self):
        # Generated label: all Anomaly flagged, half of Normal false alarms -> AUROC 0.75.
        label = lambda c, i: "Level03" if c["binary_class"] == "Anomaly" or i < 5 else "Level04"
        def pa3(tied_coal_normals):
            # Normal i < k ties with every Anomaly: AUROC = (10*(10-k) + 10*k/2) / 100.
            return lambda d, cls, i: 1.0 if cls == "Anomaly" or i < (tied_coal_normals if d == "coal_conveyor" else 2) else 0.0
        diag = run(scored(synthetic_cohort(), pa3(2), label))
        m = diag["results"]["macro_primary"]
        self.assertEqual((m["macro_pa3_auroc"]["exact"], m["macro_generated_label_auroc"]["exact"]), ("9/10", "3/4"))
        self.assertEqual(m["macro_delta"]["exact"], "3/20")
        self.assertEqual(diag["criteria"]["C3_MACRO_DELTA"], "PASS")
        self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.GO)
        # One more tied Normal in coal_conveyor: 0.85 there, macro 0.8875, delta 0.1375.
        diag = run(scored(synthetic_cohort(), pa3(3), label))
        self.assertEqual(diag["results"]["macro_primary"]["macro_delta"]["exact"], "11/80")
        self.assertEqual(diag["criteria"]["C3_MACRO_DELTA"], "FAIL")
        self.assertEqual(diag["decision"], {"DIRECTION_RECOMMENDATION": seminar_verdict.KEEP,
                                            "reason_category": "PERFORMANCE_NOT_CONVINCING",
                                            "failed_criteria": ["C3_MACRO_DELTA"]})

    def test_domain_wins_two_of_four_fails(self):
        pa3 = lambda d, cls, i: 1.0 if cls == "Anomaly" and d in ("coal_conveyor", "power") else 0.0
        diag = run(scored(synthetic_cohort(), pa3))
        self.assertEqual(diag["results"]["macro_primary"]["domains_pa3_greater"], 2)
        self.assertIn("C4_DOMAIN_WINS", diag["decision"]["failed_criteria"])
        self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.KEEP)

    def test_coverage_and_undefined_domain_are_insufficient_data_not_performance(self):
        perfect = lambda d, cls, i: 1.0 if cls == "Anomaly" else 0.0
        diag = run(scored(synthetic_cohort(), perfect, drop=lambda c, i: c["domain"] == "power" and c["binary_class"] == "Normal" and i < 3))
        self.assertEqual(diag["results"]["primary"]["coverage"]["Normal"]["k"], 37)
        self.assertEqual(diag["decision"]["reason_category"], "INSUFFICIENT_VALID_DATA")
        diag = run(scored(synthetic_cohort(), perfect, drop=lambda c, i: c["domain"] == "tunnel" and c["binary_class"] == "Anomaly"))
        self.assertEqual(diag["results"]["macro_primary"]["undefined_domains"], ["tunnel"])
        self.assertIsNone(diag["results"]["macro_primary"]["macro_pa3_auroc"])
        self.assertEqual(diag["decision"]["reason_category"], "INSUFFICIENT_VALID_DATA")

    def test_metallurgy_cannot_rescue_and_incomplete_and_technical(self):
        pa3 = lambda d, cls, i: 1.0 if cls == "Anomaly" and d == "metallurgy" else 0.0
        diag = run(scored(synthetic_cohort(), pa3))
        self.assertEqual(diag["results"]["metallurgy"]["auroc_pa3"]["value"], 1.0)
        self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.KEEP)
        perfect = lambda d, cls, i: 1.0 if cls == "Anomaly" else 0.0
        rows = scored(synthetic_cohort(), perfect)
        rows[-1] = pending(rows[-1]["sample_id"])
        diag = run(rows, completed=False)
        self.assertEqual(diag["decision"]["reason_category"], "INCOMPLETE")
        self.assertTrue(all(v == "NOT_EVALUABLE_INCOMPLETE_RUN" for v in diag["criteria"].values()))
        diag = seminar_verdict.evaluate({"results": scored(synthetic_cohort(), perfect), "completed": True, "sealed": True,
                                         "integrity": "PASS"}, synthetic_cohort(), {**EVIDENCE, "preflight_verified": 89})
        self.assertEqual(diag["decision"]["reason_category"], "TECHNICAL_FAIL")

    def test_audit_rejection_is_technical_fail_not_not_executed(self):
        diag = seminar_verdict.evaluate(None, synthetic_cohort(), {"audit_error": "ValueError:CPU_RECOMPUTATION_MISMATCH"})
        self.assertEqual(diag["decision"]["reason_category"], "TECHNICAL_FAIL")
        self.assertEqual(diag["criteria"]["C5_TECHNICAL_INTEGRITY"], "FAIL")
        self.assertIsNone(diag["results"])

    def test_not_executed_has_no_metrics_and_renders(self):
        diag = seminar_verdict.evaluate(None, None, {"stage": "AUTHORITY"})
        self.assertIsNone(diag["results"])
        self.assertEqual(diag["decision"]["reason_category"], "NOT_EXECUTED")
        self.assertIn(b"KEEP_CURRENT_DIRECTION", seminar_verdict.render_markdown(diag))
        self.assertEqual(seminar_verdict.render_csv(diag).count(b"\n"), 1)

    def test_tie_rule_generated_label_auroc_is_balanced_accuracy(self):
        label = lambda c, i: "Level04" if (c["binary_class"] == "Normal" and i < 4) or (c["binary_class"] == "Anomaly" and i < 1) else "Level03"
        diag = run(scored(synthetic_cohort(), lambda d, cls, i: 0.0, label))
        b = diag["results"]["by_domain"]["coal_conveyor"]
        tpr, tnr = 9 / 10, 4 / 10
        self.assertAlmostEqual(b["auroc_generated_binary_label"]["value"], (tpr + tnr) / 2)
        self.assertEqual(b["auroc_pa3"]["value"], 0.5)
        self.assertEqual(diag["results"]["baselines_primary"]["constant_score_auroc"]["value"], 0.5)


@contextmanager
def diagnostic_fixture(tmp, images_ok=True, failure_at=None):
    """Synthetic 90-image TRAIN-shaped tree, real manifests and gated image path."""
    from PIL import Image
    from tests.test_pa3_native import WorkflowTests, Model, Processor, TOK
    fixture = WorkflowTests()
    repo = fixture.prepare_repo(tmp)
    inputs = repo / "inputs"
    root = inputs / "train"
    pool = candidates()
    selection = seminar.select(pool, [])
    by_id = {c["sample_id"]: c for c in pool}
    samples, cohort = [], []
    for sid in selection["inference_order"]:
        c = by_id[sid]
        cls = seminar.binary(c["level"])
        locator = f"DATA_PATH/train/Annotations/{cls}_data/{sid[:-4]}/{sid}.jpg"
        path = root / locator
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (16, 16), (250 if cls == "Anomaly" else 5, 0, 0)).save(path, format="JPEG")
        row = {"sample_id": sid, "image_locator": locator, "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        samples.append(row)
        cohort.append({**row, "level": c["level"], "binary_class": cls, "domain": c["domain"],
                       "primary": c["domain"] in seminar.PRIMARY, "text_domain": c["domain"], "domain_conflict": False,
                       "mandatory_group": c["group"], "conservative_component": "component-" + c["domain"],
                       "exposure": {"ls1_documentary_per_sample": False}})
    inference = pretty({"schema": "pa3-seminar-direction-inference-v1", "run_id": seminar.RUN_ID,
                        "split": "TRAIN", "seed": seminar.SEED, "locator_root": "fixture",
                        "order_rule": seminar.RULE["inference_order"], "samples": samples})
    manifest = {"schema": "pa3-seminar-direction-cohort-v1", "run_id": seminar.RUN_ID, "status": "FIXTURE",
                "scope": "FIXTURE", "split": "TRAIN", "seed": seminar.SEED, "rule": seminar.RULE, "inputs": {},
                "exclusions": {"exact_test_duplicate_train_ids": []}, "selection": {"selected_ids": selection["selected_ids"]},
                "inference_manifest": seminar.INFERENCE, "inference_manifest_sha256": hashlib.sha256(inference).hexdigest(),
                "samples": cohort, "exposure_reservation": {}, "limitations": [], "execution_authority": False}
    (repo / "data/manifests").mkdir(parents=True)
    (repo / seminar.INFERENCE).write_bytes(inference)
    (repo / seminar.COHORT).write_bytes(json_bytes(manifest))
    if not images_ok:
        (root / samples[7]["image_locator"]).write_bytes(b"changed")
    grant = {"cohort_manifest_sha256": hashlib.sha256((repo / seminar.COHORT).read_bytes()).hexdigest(),
             "inference_manifest_sha256": hashlib.sha256(inference).hexdigest(),
             "technical_seal_sha256": "c" * 64, "technical_source_bundle_sha256": "d" * 64, "approval": "LEAD-FIXTURE"}
    settings = {"mode": seminar.MODE, "run_id": seminar.RUN_ID, "source_commit": preflight.BASE_SHA,
                "dataset_input": "train", "technical_run_input": "unused", "technical_source_bundle_input": "unused",
                **{k: grant[k] for k in access.DIAGNOSTIC_GRANT}}

    def require(operation, s=None, r=None):
        if operation != seminar.MODE or {k: (s or {}).get(k) for k in access.DIAGNOSTIC_GRANT} != {k: grant[k] for k in access.DIAGNOSTIC_GRANT}:
            raise PermissionError("FIXTURE_DENY")
        return {"grant": grant}

    seen = {}
    original_call = Processor.__call__

    def call(self, **kwargs):
        seen["anomaly"] = kwargs["images"][0].getpixel((8, 8))[0] > 128
        return original_call(self, **kwargs)

    step = token_module.probe(TOK)["checks"][0]["step"]

    class Varying(Model):
        """Level04 raw logit (token 52) depends on the decoded fixture pixels only."""
        def generate(self, **kwargs):
            out = super().generate(**kwargs)
            if failure_at is not None and len(self.calls) == failure_at:
                raise RuntimeError("FIXTURE_CUDA_FAILURE")
            for tensors in (out.logits, out.scores):
                tensors[step].data[0][52] = (-1.0 if seen["anomaly"] else 3.0) + len(self.calls) * 0.001
            return out

    original_ticket = access.image_ticket
    calls = {"verify_prior": 0}

    def prior(*args):
        calls["verify_prior"] += 1
        return {"completed": True}

    with ExitStack() as stack:
        stack.enter_context(fixture.prerequisites(Varying()))
        stack.enter_context(patch.object(access, "require", side_effect=require))
        stack.enter_context(patch.object(access, "image_ticket", original_ticket))  # real diagnostic branch
        stack.enter_context(patch.object(Processor, "__call__", call))
        stack.enter_context(patch.object(seminar, "verify_prior", side_effect=prior))
        yield repo, settings, inputs, calls, TOK


class WorkflowTests(unittest.TestCase):
    def test_one_pass_exposure_first_gt_after_seal_and_reproducible_verdict(self):
        with tempfile.TemporaryDirectory() as tmp, diagnostic_fixture(tmp) as (repo, settings, inputs, calls, tok):
            original_open, original_meta = seminar.open_image, seminar.evaluation_metadata
            def opened(*args):
                exposure = Journal(run_path(repo, settings["run_id"] + "-exposure"))
                self.assertTrue(exposure.verify())
                self.assertEqual(len(exposure.read("observed")["sample_ids"]), 90)
                self.assertTrue(Journal(run_path(repo, settings["run_id"] + "-preflight")).verify())
                return original_open(*args)
            def joined(*args):
                self.assertTrue(Journal(run_path(repo, settings["run_id"])).verify())
                return original_meta(*args)
            with patch.object(seminar, "open_image", side_effect=opened), \
                 patch.object(seminar, "evaluation_metadata", side_effect=joined):
                root = workflow.execute(repo, settings, "CPU-fixture", inputs)
            self.assertGreaterEqual(calls["verify_prior"], 1)
            report = Journal(root.parent / (root.name + "-report"))
            self.assertTrue(report.verify())
            diag = report.read("diagnostic")
            self.assertEqual(diag["results"]["overall"]["status_counts"]["SUCCESS"], 90)
            self.assertEqual(diag["results"]["macro_primary"]["macro_pa3_auroc"]["value"], 1.0)
            self.assertEqual(diag["results"]["macro_primary"]["macro_generated_label_auroc"]["value"], 0.5)
            self.assertEqual(diag["decision"]["DIRECTION_RECOMMENDATION"], seminar_verdict.GO)
            self.assertEqual(len(diag["results"]["per_image"][0]), 19)
            self.assertEqual(diag["evidence"]["telemetry"]["calls"], 90)
            # Independent CPU recomputation from the sealed journals matches the sealed records.
            # The offline CLI path: CPU audit, recompute, byte-compare report + verdict files.
            recheck = seminar_verdict.recheck(root, repo, tok, Path(tmp) / "recheck")
            self.assertEqual(json_bytes(recheck), json_bytes(diag))
            self.assertEqual(diag["evidence"]["stage_reached"], "FINISHED")
            checked, _ = seminar_verdict.collect(root, repo, tok)
            metadata = report.read("metadata")
            self.assertEqual(json_bytes(analysis.report(checked["results"], metadata, completed=True)),
                             json_bytes(report.read("evaluation")))
            verdict = root.parent / (root.name + "-verdict")
            receipt = json.loads((verdict / "checksums.json").read_bytes())
            for name in (seminar_verdict.VERDICT, seminar_verdict.PER_IMAGE, seminar_verdict.METRICS):
                self.assertEqual(receipt["files"][name]["sha256"], hashlib.sha256((verdict / name).read_bytes()).hexdigest())
            self.assertEqual((verdict / seminar_verdict.VERDICT).read_bytes(), seminar_verdict.render_markdown(diag))
            self.assertEqual(seminar_verdict.render_csv(diag).count(b"\n"), 91)
            tickets = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-tickets")
            self.assertEqual(len(list(tickets.glob("sample-*.ticket"))), 90)
            with self.assertRaises(FileExistsError):
                workflow.execute(repo, settings, "CPU-fixture", inputs)

    def test_midrun_failure_seals_and_reports_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp, diagnostic_fixture(tmp, failure_at=3) as (repo, settings, inputs, calls, tok):
            with self.assertRaises(RuntimeError):
                workflow.execute(repo, settings, "CPU-fixture", inputs)
            root = run_path(repo, settings["run_id"])
            self.assertTrue(Journal(root).verify())
            self.assertEqual(Journal(root).read("failure")["stage"], "F_ONE_PASS_INFERENCE")
            diag = Journal(root.parent / (root.name + "-report")).read("diagnostic")
            self.assertEqual(diag["decision"]["reason_category"], "INCOMPLETE")
            self.assertEqual(diag["results"]["overall"]["status_counts"]["SUCCESS"], 2)
            self.assertEqual(diag["results"]["overall"]["status_counts"]["TECHNICAL_ERROR"], 1)
            self.assertTrue((root.parent / (root.name + "-verdict") / seminar_verdict.VERDICT).is_file())

    def test_checksum_preflight_stops_before_model_load(self):
        from safeshift.pa3.native import qwen
        with tempfile.TemporaryDirectory() as tmp, diagnostic_fixture(tmp, images_ok=False) as (repo, settings, inputs, calls, tok), \
             patch.object(qwen, "QwenRawScorer", side_effect=AssertionError("MODEL_LOAD")):
            with self.assertRaisesRegex(ValueError, "DIAGNOSTIC_IMAGE_CHECKSUM"):
                workflow.execute(repo, settings, "CPU-fixture", inputs)
            root = run_path(repo, settings["run_id"])
            self.assertEqual(Journal(root).read("failure")["stage"], "C_MANIFEST_AND_DATASET_CHECKSUMS")
            self.assertFalse(Journal(root).exists("manifest"))
            diag = Journal(root.parent / (root.name + "-report")).read("diagnostic")
            self.assertEqual(diag["decision"]["reason_category"], "NOT_EXECUTED")

    def test_image_outside_manifest_and_test_root_denied(self):
        with tempfile.TemporaryDirectory() as tmp, diagnostic_fixture(tmp) as (repo, settings, inputs, calls, tok):
            row = seminar.inference_samples(repo, settings)[0]
            with self.assertRaises(PermissionError):
                seminar.open_image(repo, settings, {**row, "sample_id": "tunnel-Level04-Wheeled-777777-001"}, inputs)
            with self.assertRaisesRegex(PermissionError, "TEST_ATTACHMENT"):
                seminar.open_image(repo, {**settings, "dataset_input": "InspecSafe/test"}, row, inputs)


class NotebookTests(unittest.TestCase):
    def test_single_offline_notebook_reuses_audited_bootstrap(self):
        nb = json.loads((ROOT / "notebooks/pa3_seminar_direction_kaggle.ipynb").read_bytes())
        technical = json.loads((ROOT / "notebooks/pa3_qwen2_5_kaggle.ipynb").read_bytes())
        self.assertEqual(nb["metadata"]["kaggle"], {"accelerator": "nvidiaTeslaT4", "isInternetEnabled": False})
        code = [c for c in nb["cells"] if c["cell_type"] == "code"]
        self.assertEqual(code[1]["source"], technical["cells"][2]["source"])
        namespace = {}
        exec("".join(code[0]["source"]), namespace)
        self.assertEqual((namespace["SETTINGS"]["mode"], namespace["SETTINGS"]["run_id"]), (seminar.MODE, seminar.RUN_ID))
        for cell in code:
            compile("".join(cell["source"]), "cell", "exec")
            text = "".join(cell["source"])
            for word in ("pip install", "snapshot_download", "!pip", "retry("):
                self.assertNotIn(word, text)
            self.assertEqual(cell["outputs"], [])


if __name__ == "__main__":
    unittest.main()
