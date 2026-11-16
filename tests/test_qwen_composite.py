"""CPU synthetic fixtures only; no historical payload or model imports."""

from copy import deepcopy
from contextlib import chdir
from fractions import Fraction
from itertools import product
import io
import json
from pathlib import Path
import tarfile
import tempfile
import subprocess
import unittest

from safeshift.evaluation.qwen_composite import (
    PROVENANCE_FIELDS, PRODUCT, auc_report, compose, digest, metrics, report,
)
from scripts.build_qwen3_composite import (
    MEMBERS, bytes_sha, csv_bytes, historical_digest, json_bytes, metric_rows,
    read_product, recovery_mapping, validate_unit, verified_archive_members, verify_train_images,
)
from scripts.check_qwen3_composite_metrics import check as independent_check


def fixture():
    master = [{"sample_id": str(i), "split": "TRAIN", "level": t, "domain": "synthetic",
               "image_sha256": digest(i)}
              for i, t in enumerate(("Level01", "Level02", "Level03", "Level04"))]
    sources = {}
    for sid, kind in (("v4", "V4_ORIGINAL"), ("rec", "RECOVERY224")):
        sources[sid] = {"kind": kind, **{k: digest([sid, k]) for k in PROVENANCE_FIELDS}}
    original = []
    for i, m in enumerate(master):
        original.append({"sample_id": m["sample_id"], "split": m["split"], "image_sha256": m["image_sha256"],
                         "true_level": m["level"], "domain": m["domain"], "status": "SUCCESS",
                         "generated_label": ("Level04", "Level02", "Level03", "Level04")[i],
                         "hnlo_score": (0, 1, 2, -1)[i], "source_id": "v4", "source_ordinal": i,
                         **{k: sources["v4"][k] for k in PROVENANCE_FIELDS}})
    original[0].update(status="TECHNICAL_ERROR", generated_label="", hnlo_score="")
    recovery = [{**original[0], **{k: sources["rec"][k] for k in PROVENANCE_FIELDS},
                 "source_id": "rec", "source_ordinal": 0, "status": "SUCCESS",
                 "generated_label": "Level04", "hnlo_score": 0}]
    return master, original, recovery, sources, {"SUCCESS": 3, "TECHNICAL_ERROR": 1}


def unit_fixture():
    master = {"synthetic": {"sample_id": "synthetic", "level": "Level01", "domain": "synthetic",
                            "image_sha256": digest("image"), "image_locator": "synthetic.jpg", "split": "TRAIN"}}
    planned = [{k: master["synthetic"][k] for k in ("sample_id", "image_sha256", "image_locator")}]
    unit = {"count": 1, "run_id": "synthetic-run", "attempt_id": "synthetic-attempt"}
    authority = {"synthetic": True}
    binding = {"unit": unit, "authority": authority, "samples": planned}
    rows = [{"sample_id": "synthetic", "domain": "synthetic", "true_level": "Level01", "status": "SUCCESS",
             "attempted": "True", "persisted": "True", "parsed": "True", "generated_label": "Level02",
             "true_binary_label": "Anomaly", "generated_binary_label": "Anomaly", "pa3_score": "1"}]
    journal = [{"sample_id": "synthetic", "ordinal": 0, "status": "SUCCESS",
                "attempted": True, "persisted": True, "parsed": True}]
    result = {"unit": unit, "export": {"unit": unit}, "schema": "hnlo-train-unit-result-v1",
              "retry": False, "research_generalization_claim": False, "scope": "DESCRIPTIVE_FULL_TRAIN",
              "sample_journal": journal, "status": "COMPLETE",
              "coverage": {"planned": 1, "scored": 1, "persisted": 1, "parsed": 1, "attempted": 1,
                           "anomaly_n": 1, "normal_n": 0, "coverage": 1.0,
                           "status_counts": {"SUCCESS": 1, "INVALID": 0}, "level_counts": {"Level01": 1}}}
    return result, binding, rows, deepcopy(unit), deepcopy(authority), deepcopy(planned), master


class SelectionTests(unittest.TestCase):
    def test_exact_complement_preserves_errors_and_inputs(self):
        args = fixture()
        before = deepcopy(args)
        rows = compose(*args)
        self.assertEqual(args, before)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["original_status"], "TECHNICAL_ERROR")
        self.assertEqual(rows[0]["generated_label"], "Level04")  # wrong GT prediction is kept
        self.assertEqual(rows[0]["source_id"], "rec")
        self.assertEqual(rows[1]["source_id"], "v4")

    def test_predictions_do_not_select_sources(self):
        args = fixture()
        first = compose(*args)
        args[2][0]["generated_label"] = "Level01"
        second = compose(*args)
        self.assertEqual([r["source_id"] for r in first], [r["source_id"] for r in second])
        self.assertEqual(second[0]["generated_label"], "Level01")

    def test_no_favorable_duplicate_or_recovery_of_success(self):
        args = fixture()
        args[2].append({**args[2][0], "generated_label": "Level01"})
        with self.assertRaisesRegex(ValueError, "unique"):
            compose(*args)
        args = fixture()
        args[2].append({**args[2][0], "sample_id": "1"})
        with self.assertRaisesRegex(ValueError, "exactly"):
            compose(*args)

    def test_missing_extra_duplicate_ids_all_ledgers(self):
        for ledger in (0, 1, 2):
            for kind in ("missing", "extra", "duplicate"):
                with self.subTest(ledger=ledger, kind=kind):
                    args = fixture()
                    if kind == "missing":
                        args[ledger].pop()
                    else:
                        args[ledger].append({**args[ledger][0], **({"sample_id": "extra"} if kind == "extra" else {})})
                    with self.assertRaises(ValueError):
                        compose(*args)

    def test_bad_hash_label_domain_split_status(self):
        for ledger in (1, 2):
            for key, bad in (("image_sha256", "0" * 64), ("true_level", "Level04"), ("domain", "other"),
                             ("split", "TEST"), ("status", "INVALID")):
                with self.subTest(ledger=ledger, key=key):
                    args = fixture()
                    args[ledger][0][key] = bad
                    with self.assertRaises(ValueError):
                        compose(*args)
        for key, bad in (("level", "bad"), ("split", "TEST"), ("image_sha256", "bad")):
            args = fixture()
            args[0][0][key] = bad
            with self.assertRaises(ValueError):
                compose(*args)

    def test_bad_prediction_and_source_kind(self):
        for key, bad in (("generated_label", "Level1"), ("source_id", "diagnostic")):
            args = fixture()
            args[2][0][key] = bad
            with self.assertRaises(ValueError):
                compose(*args)
        args = fixture()
        args[3]["rec"]["kind"] = "V4_ORIGINAL"
        with self.assertRaises(ValueError):
            compose(*args)

    def test_each_provenance_field_rejected_including_original_error(self):
        for ledger in (1, 2):
            for field in PROVENANCE_FIELDS:
                with self.subTest(ledger=ledger, field=field):
                    args = fixture()
                    args[ledger][0][field] = "changed"
                    with self.assertRaisesRegex(ValueError, "identity"):
                        compose(*args)

    def test_unavailable_scores_do_not_block_labels(self):
        for bad in (None, "", "nan", "inf", float("nan"), float("inf"), True, "bad"):
            with self.subTest(bad=bad):
                args = fixture()
                args[2][0]["hnlo_score"] = bad
                rows = compose(*args)
                self.assertIsNone(rows[0]["hnlo_score"])
                self.assertIsNotNone(rows[0]["hnlo_unavailable_reason"])
                self.assertEqual(report(rows, args[3])["planned_n"], 4)


class MetricTests(unittest.TestCase):
    def test_exhaustive_confusion_against_fraction_oracle(self):
        levels = ("Level01", "Level02", "Level03", "Level04")
        for predictions in product((*levels, "INVALID"), repeat=4):
            rows = [{"true_level": t, "generated_label": p} for t, p in zip(levels, predictions)]
            actual = metrics(rows)
            f1 = sum((Fraction(2 * (p == t), 1 + predictions.count(t))
                      for t, p in zip(levels, predictions)), Fraction()) / 4
            correct = sum(t == p for t, p in zip(levels, predictions))
            self.assertAlmostEqual(actual["macro_f1"], float(f1))
            self.assertEqual(actual["accuracy"]["value"], correct / 4)
            self.assertEqual(actual["balanced_accuracy"], correct / 4)
            self.assertEqual(actual["binary"]["FN"], predictions[:3].count("Level04"))
            self.assertEqual(actual["binary"]["FP"], int(predictions[3] in levels[:3]))
    def test_hand_oracle_four_class_and_binary(self):
        rows = compose(*fixture())
        m = metrics(rows)
        self.assertEqual([sum(r.values()) for r in m["confusion_4x5"].values()], [1] * 4)
        self.assertTrue(all(len(r) == 5 for r in m["confusion_4x5"].values()))
        self.assertEqual(m["accuracy"], {"numerator": 3, "denominator": 4, "value": .75})
        self.assertEqual(m["balanced_accuracy"], .75)
        self.assertAlmostEqual(m["macro_f1"], (0 + 1 + 1 + 2 / 3) / 4)
        self.assertEqual([m["binary"][k] for k in ("TP", "FN", "FP", "TN")], [2, 1, 0, 1])
        self.assertEqual(m["binary"]["hazard_recall"]["value"], 2 / 3)
        self.assertEqual(m["binary"]["false_safe"]["value"], 1 / 3)
        self.assertEqual(m["binary"]["false_alarm"]["value"], 0)

    def test_invalid_stays_in_denominator(self):
        rows = compose(*fixture())
        rows[0]["generated_label"] = "INVALID"
        m = metrics(rows)
        self.assertEqual(m["confusion_4x5"]["Level01"]["INVALID"], 1)
        self.assertEqual(m["per_class"]["Level01"]["recall"]["value"], 0)
        self.assertEqual(m["per_class"]["Level01"]["f1"]["value"], 0)
        self.assertEqual(m["invalid_n"], 1)
        self.assertEqual(m["binary"]["U_A"], 1)
        self.assertEqual(m["binary"]["false_safe"]["value"], 0)
        self.assertEqual(m["binary"]["hazard_recall"]["denominator"], 3)

    def test_empty_and_absent_classes(self):
        empty = metrics([])
        for key in ("macro_f1", "balanced_accuracy"):
            self.assertIsNone(empty[key])
        self.assertIsNone(empty["accuracy"]["value"])
        single = metrics([compose(*fixture())[-1]])
        self.assertEqual(single["macro_classes"], ["Level04"])
        self.assertIsNone(single["binary"]["hazard_recall"]["value"])
        self.assertEqual(single["macro_f1"], 1)

    def test_auc_ties_one_class_empty_and_missing(self):
        tied = [{"true_level": t, "hnlo_score": 1} for t in ("Level01", "Level04")]
        self.assertEqual(auc_report(tied)["value"], .5)
        self.assertIsNone(auc_report(tied[:1])["value"])
        self.assertIsNone(auc_report([])["value"])
        tied[0]["hnlo_score"] = "nan"
        self.assertEqual(auc_report(tied)["excluded_by_reason"], {"NONFINITE_OR_INVALID_SCORE": 1})

    def test_auc_pairwise_oracle(self):
        scores = [2, 1, 1, -2, 0, 3]
        rows = [{"true_level": "Level01" if i % 2 else "Level04", "hnlo_score": s}
                for i, s in enumerate(scores)]
        pairs = [(a["hnlo_score"], b["hnlo_score"]) for a in rows for b in rows
                 if a["true_level"] != "Level04" and b["true_level"] == "Level04"]
        expected = sum(1 if a > b else .5 if a == b else 0 for a, b in pairs) / len(pairs)
        self.assertAlmostEqual(auc_report(rows)["value"], expected)

    def test_report_strata_and_no_auc_pooling(self):
        args = fixture()
        result = report(compose(*args), args[3])
        self.assertEqual(result["source_counts"], {"RECOVERY224": 1, "V4_ORIGINAL": 3})
        self.assertIsNone(result["hnlo"]["composite"]["value"])
        self.assertEqual(result["strata"]["domain:synthetic"]["accuracy"], result["strata"]["ALL"]["accuracy"])
        self.assertEqual(sum(result["strata"]["level:" + t]["planned_n"] for t in
                             ("Level01", "Level02", "Level03", "Level04")), 4)


class SourceTests(unittest.TestCase):
    def test_protocol_is_append_only_and_frozen_config_unchanged(self):
        config = json.loads(Path("configs/analysis/qwen3_full_train_composite.v1.json").read_bytes())
        base = "044b53059e7a9615d54f07a4ce8a44308b47e56a"
        old = subprocess.check_output(["git", "show", base + ":docs/research/SEMINAR_PROTOCOL.md"])
        new = Path("docs/research/SEMINAR_PROTOCOL.md").read_bytes()
        self.assertEqual(new[:len(old)], old)
        self.assertEqual(bytes_sha(new[len(old):]), config["protocol"]["amendment_sha256"])
        path = "docs/research/seminar_analysis_config.v1.json"
        self.assertEqual(Path(path).read_bytes(), subprocess.check_output(["git", "show", base + ":" + path]))

    def test_train_byte_hash_and_path_fences(self):
        with tempfile.TemporaryDirectory() as tmp, chdir(tmp):
            root = Path("data/raw/synthetic")
            target = root / "DATA_PATH/train/Annotations/one.jpg"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"synthetic bytes, not an image")
            master = [{"sample_id": "synthetic", "image_locator": "DATA_PATH/train/Annotations/one.jpg",
                       "image_sha256": bytes_sha(target.read_bytes())}]
            self.assertEqual(verify_train_images(root, master)["verified_n"], 1)
            target.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                verify_train_images(root, master)
            for loc in ("DATA_PATH/test/Annotations/one.jpg", "../test.jpg", "DATA_PATH/train/Annotations/one.txt"):
                master[0]["image_locator"] = loc
                with self.assertRaises(ValueError):
                    verify_train_images(root, master)
            with self.assertRaises(ValueError):
                verify_train_images(Path(tmp), master)

    def test_valid_saved_unit_and_no_score_label_dependency(self):
        args = unit_fixture()
        validate_unit(*args)
        args[2][0]["pa3_score"] = "nan"
        validate_unit(*args)

    def test_unit_negatives(self):
        changes = [(0, "unit", {"count": 1, "run_id": "wrong", "attempt_id": "wrong"}),
                   (0, "scope", "TEST"), (0, "retry", True), (0, "status", "PARTIAL"),
                   (1, "authority", {"different": True})]
        for part, key, bad in changes:
            with self.subTest(key=key):
                args = unit_fixture()
                args[part][key] = bad
                with self.assertRaises(ValueError):
                    validate_unit(*args)
        for key, bad in (("sample_id", "missing"), ("domain", "other"), ("true_level", "Level04"),
                         ("generated_label", "bad"), ("status", "INVALID"), ("persisted", "False"),
                         ("true_binary_label", "Normal"), ("generated_binary_label", "Normal")):
            args = unit_fixture()
            args[2][0][key] = bad
            with self.assertRaises((ValueError, KeyError)):
                validate_unit(*args)
        for key in ("image_sha256", "image_locator"):
            args = unit_fixture()
            args[6]["synthetic"][key] = "changed"
            with self.assertRaises(ValueError):
                validate_unit(*args)
        args = unit_fixture()
        args[0]["sample_journal"][0]["persisted"] = 1  # bool identity is strict
        with self.assertRaises(ValueError):
            validate_unit(*args)

    def test_mapping_uses_historical_lf_canonicalization(self):
        planned = [{"sample_id": str(i), "image_sha256": digest(i)} for i in range(941)]
        original = [{"sample_id": str(i), "status": "SUCCESS" if i < 717 else
                     "TECHNICAL_ERROR" if i == 717 else "NOT_ATTEMPTED"} for i in range(941)]
        mapping = [{"recovery_ordinal": i - 717, "original_shard": 2, "original_ordinal": i,
                    "sample_id": str(i), "image_sha256": digest(i), "prior_status": original[i]["status"]}
                   for i in range(717, 941)]
        worker = [{"ordinal": i, "image_sha256": r["image_sha256"]} for i, r in enumerate(planned[717:])]
        unit = {"mapping_sha256": historical_digest(mapping), "inference_sha256": historical_digest(worker)}
        binding = {"recovery_mapping": mapping}
        recovery_mapping(binding, original, planned, unit)
        for key in ("sample_id", "image_sha256", "prior_status", "original_ordinal"):
            broken = deepcopy(binding)
            broken["recovery_mapping"][0][key] = "changed"
            with self.assertRaises(ValueError):
                recovery_mapping(broken, original, planned, unit)

    def test_archive_inventory_hash_duplicate_and_missing(self):
        def archive(duplicate=False, missing=False, bad_inventory=False):
            files = {name: b'{}' for name in MEMBERS}
            manifest = {"files": [{"path": name.removeprefix("evidence/"), "size_bytes": len(raw),
                                    "sha256": "0" * 64 if bad_inventory else bytes_sha(raw)}
                                   for name, raw in files.items()]}
            manifest_raw = json_bytes(manifest)
            files["manifest.json"] = manifest_raw
            out = io.BytesIO()
            with tarfile.open(fileobj=out, mode="w:gz") as t:
                for name, raw in files.items():
                    if missing and name == "evidence/binding.json":
                        continue
                    info = tarfile.TarInfo(name)
                    info.size = len(raw)
                    t.addfile(info, io.BytesIO(raw))
                    if duplicate and name == "evidence/binding.json":
                        t.addfile(info, io.BytesIO(raw))
            payload = out.getvalue()
            return payload, {"archive_sha256": bytes_sha(payload), "archive_bytes": len(payload),
                             "manifest_sha256": bytes_sha(manifest_raw)}
        payload, export = archive()
        self.assertEqual(set(verified_archive_members(payload, export, MEMBERS)), MEMBERS | {"manifest.json"})
        with self.assertRaises(ValueError):
            verified_archive_members(payload + b'bad', export, MEMBERS)
        for option in ("duplicate", "missing", "bad_inventory"):
            payload, export = archive(**{option: True})
            with self.assertRaises(ValueError):
                verified_archive_members(payload, export, MEMBERS)


class HandoffTests(unittest.TestCase):
    def product(self, directory):
        args = fixture()
        rows = compose(*args)
        payload = {"schema": "safeshift-qwen3-full-train-composite-v1", "product_id": PRODUCT,
                   "samples": rows, "master": args[0], "original_ledger": args[1],
                   "recovery_ledger": args[2], "sources": args[3], "original_status_counts": args[4]}
        analysis = report(rows, args[3])
        files = {"composite.json": json_bytes(payload), "samples.csv": csv_bytes(rows),
                 "metrics.json": json_bytes(analysis), "metrics.csv": csv_bytes(list(metric_rows(analysis))),
                 "audit.json": json_bytes({"synthetic": True}),
                 "image_verification.json": json_bytes({"synthetic": True})}
        for name, raw in files.items():
            (directory / name).write_bytes(raw)
        return self.reseal(directory)

    def reseal(self, directory):
        files = {p.name: {"sha256": bytes_sha(p.read_bytes()), "size_bytes": p.stat().st_size}
                 for p in directory.iterdir() if p.name != "manifest.json"}
        raw = json_bytes({"schema": "safeshift-qwen3-composite-seal-v1", "product_id": PRODUCT, "files": files})
        (directory / "manifest.json").write_bytes(raw)
        return bytes_sha(raw)

    def test_downstream_reader_recomputes_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            sha = self.product(p)
            payload, analysis = read_product(p, sha)
            self.assertEqual(independent_check(p)["rows"], 4)
            self.assertEqual(len(payload["samples"]), 4)
            self.assertEqual(analysis["strata"]["ALL"]["accuracy"]["value"], .75)
            with self.assertRaises(ValueError):
                read_product(p, "0" * 64)
            (p / "samples.csv").write_bytes(b"changed")
            with self.assertRaises(ValueError):
                read_product(p, sha)
            sha = self.reseal(p)
            with self.assertRaisesRegex(ValueError, "CSV mismatch"):
                read_product(p, sha)

    def test_resealed_metric_must_recompute(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            self.product(p)
            m = json.loads((p / "metrics.json").read_bytes())
            m["strata"]["ALL"]["accuracy"]["value"] = 1
            (p / "metrics.json").write_bytes(json_bytes(m))
            with self.assertRaisesRegex(ValueError, "metric recomputation"):
                read_product(p, self.reseal(p))


if __name__ == "__main__":
    unittest.main()
