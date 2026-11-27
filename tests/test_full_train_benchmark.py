"""Synthetic oracles for the extension. No real records or labels are loaded."""

from copy import deepcopy
import csv
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.data.saved_reports import json_bytes, sha256
from safeshift.evaluation.full_train_benchmark import PRODUCTS, SCHEMA, compare
from scripts.benchmark_full_train import CONFIG_PATH, SOURCE_FILES, confusion_html, load_inputs, main


def fixture():
    truth = ("Level01", "Level02", "Level03", "Level04", "Level04")
    rows = [{"sample_id": f"fixture-{i}", "split": "TRAIN", "image_sha256": f"{min(i, 4):064x}",
             "true_level": level, "domain": "east" if i < 4 else "west"}
            for i, level in enumerate(truth, 1)]
    predictions = {
        "qwen3": ("Level02", "Level02", "Level04", "Level01", "Level04"),
        "internvl35": ("Level01", "Level04", "Level03", "Level04", "Level02"),
        "minicpm": ("Level04", "Level02", "Level04", "Level04", "Level04"),
    }
    config = {"schema": SCHEMA, "planned_n": 5, "release": None, "products": {}}
    products = {}
    for i, key in enumerate(PRODUCTS, 1):
        seal = f"{i:064x}"
        config["products"][key] = {"id": key, "source_seal_sha256": seal, "score_limit": "FIXTURE"}
        samples = []
        for j, (row, prediction) in enumerate(zip(rows, predictions[key], strict=True)):
            sample = {**row, "source_id": "run-1", "status": "SUCCESS", "generated_label": prediction}
            if key == "minicpm":
                sample["original_status"] = "INVALID" if j == 0 else "SUCCESS"
                sample["original_label"] = None if j == 0 else prediction
            samples.append(sample)
        products[key] = {"schema": f"{SCHEMA}-product", "product_id": key, "source_seal_sha256": seal,
                         "sources": {"run-1": {"run_id": "fixture-run", "attempt_id": "fixture-attempt",
                                               "model_id": key, "revision": "fixture-revision",
                                               "config_sha256": "a" * 64, "artifact_sha256": "b" * 64}},
                         "samples": samples[::-1]}
    return {"schema": f"{SCHEMA}-cohort", "samples": rows}, products, config


class BenchmarkTest(unittest.TestCase):
    def test_hand_counts_pairing_and_invalid(self):
        cohort, products, config = fixture()
        p = compare(cohort, products, config, mini_conversion_n=1)
        self.assertEqual((p["planned_n"], p["distinct_image_sha256_n"], p["duplicate_content_groups"]), (5, 4, 1))
        qwen = p["models"]["qwen3"]["overall"]
        self.assertEqual(qwen["accuracy"]["value"], 2 / 5)
        self.assertAlmostEqual(qwen["macro_f1"], (0 + 2 / 3 + 0 + 1 / 2) / 4)
        self.assertEqual(qwen["balanced_accuracy"], (0 + 1 + 0 + 1 / 2) / 4)
        self.assertEqual(qwen["binary"]["hazard_recall"]["value"], 2 / 3)
        self.assertEqual(qwen["binary"]["precision"]["value"], 2 / 3)
        self.assertEqual(qwen["binary"]["f1"]["value"], 2 / 3)
        self.assertEqual(qwen["binary"]["fnr"]["value"], 1 / 3)
        self.assertEqual(qwen["binary"]["fpr"]["value"], 1 / 2)
        strict = p["models"]["minicpm_c1"]["overall"]
        normalized = p["models"]["minicpm"]["overall"]
        self.assertEqual((strict["binary"]["U_A"], strict["valid_label_rate"]["value"]), (1, .8))
        self.assertEqual(strict["severe_false_safe"]["value"], 0)
        self.assertEqual(normalized["severe_false_safe"]["value"], 1)
        self.assertEqual(strict["binary"]["hazard_recall"], normalized["binary"]["hazard_recall"])
        self.assertIsNone(p["models"]["qwen3"]["by_domain"]["west"]["binary"]["fnr"]["value"])
        self.assertEqual(p["models"]["qwen3"]["worst_domain"]["false_safe"]["domains"], ["east"])
        pair = p["paired"]["qwen3|internvl35"]["four_level"]
        self.assertEqual([pair[x] for x in ("both_correct", "both_wrong", "left_only_correct",
                                           "right_only_correct")], [0, 0, 2, 3])
        self.assertEqual(pair["label_disagreement"]["value"], 1)
        self.assertEqual(p["paired"]["qwen3|internvl35"]["binary"]["both_correct"], 1)
        safety = p["paired"]["qwen3|internvl35"]["hazard_false_safe"]
        self.assertEqual(safety["support_n"], 3)
        self.assertEqual([safety[key]["numerator"] for key in
                          ("both_false_safe", "left_only_false_safe",
                           "right_only_false_safe", "neither_false_safe")], [0, 1, 1, 1])
        severe = p["paired"]["qwen3|internvl35"]["level01_false_safe"]
        self.assertEqual(severe["neither_false_safe"]["value"], 1)
        west = p["paired"]["qwen3|internvl35"]["by_domain"]["west"]["hazard_false_safe"]
        self.assertIsNone(west["both_false_safe"]["value"])
        self.assertEqual(p["paired"]["minicpm_c1|minicpm"]["four_level"]["label_disagreement"]["denominator"], 4)
        self.assertNotIn("hazard_false_safe", p["paired"]["minicpm_c1|minicpm"])
        self.assertEqual(sum(r["n"] for r in p["four_level_error_patterns"]), 5)
        self.assertTrue(all(r["AUROC"] is None for r in p["scores"].values()))
        self.assertIn(b'&lt;qwen&gt;', confusion_html({"<qwen>": p["models"]["qwen3"]}, "SYNTHETIC"))

    def test_keeps_locked_gt_in_duplicate_images(self):
        cohort, products, config = fixture()
        cohort["samples"][-1]["true_level"] = "Level02"
        for product in products.values():
            product["samples"][0]["true_level"] = "Level02"
        result = compare(cohort, products, config, mini_conversion_n=1)
        self.assertEqual(result["duplicate_groups_with_conflicting_gt"], 1)
        self.assertEqual(result["models"]["qwen3"]["overall"]["support"]["Level02"], 2)

    def test_normalization_transitions_use_fixed_support(self):
        cohort, products, config = fixture()
        normal = products["minicpm"]["samples"][0]
        normal.update(original_status="INVALID", original_label=None)
        impact = compare(cohort, products, config, mini_conversion_n=2)["minicpm_normalization_impact"]
        overall = impact["overall"]
        self.assertEqual(overall["converted_by_true_level"],
                         {"Level01": 1, "Level02": 0, "Level03": 0, "Level04": 1})
        self.assertEqual((overall["strict_c1_invalid_n"], overall["normalized_invalid_n"]), (2, 0))
        self.assertEqual(overall["normal_invalid_to_true_negative_n"], 1)
        self.assertEqual(overall["hazard_invalid_to_false_safe_n"], 1)
        endpoints = overall["endpoints"]
        for metric, numerator, denominator in (("accuracy", 1, 5), ("valid_label_rate", 2, 5),
                                               ("hazard_false_safe", 1, 3), ("level01_false_safe", 1, 1),
                                               ("hazard_missed_or_invalid", 0, 3)):
            self.assertEqual(endpoints[metric]["change"],
                             {"numerator": numerator, "denominator": denominator,
                              "value": numerator / denominator})
        empty = impact["by_domain"]["west"]["endpoints"]["hazard_false_safe"]["change"]
        self.assertEqual(empty, {"numerator": 0, "denominator": 0, "value": None})

    def test_rejects_mismatched_identity_provenance_and_lineage(self):
        for field, value in (("sample_id", "unexpected"), ("split", "TEST"), ("image_sha256", "f" * 64),
                             ("true_level", "Level01"), ("domain", "other"),
                             ("source_id", "missing"), ("generated_label", "INVALID"),
                             ("status", "NOT_ATTEMPTED")):
            with self.subTest(field=field):
                c, p, config = fixture()
                p["qwen3"]["samples"][0][field] = value
                with self.assertRaises(ValueError):
                    compare(c, p, config, mini_conversion_n=1)
        for field, value in (("config_sha256", "invalid"), ("revision", ""), ("artifact_sha256", None)):
            c, p, config = fixture()
            p["internvl35"]["sources"]["run-1"][field] = value
            with self.assertRaises(ValueError):
                compare(c, p, config, mini_conversion_n=1)
        c, p, config = fixture()
        with self.assertRaisesRegex(ValueError, "conversion count"):
            compare(c, p, config)
        p["minicpm"]["samples"][0]["original_label"] = "Level02"
        with self.assertRaisesRegex(ValueError, "mapping"):
            compare(c, p, config, mini_conversion_n=1)

    def test_authorization_precedes_io_and_admitted_members_are_exact(self):
        c, p, config = fixture()
        with patch("pathlib.Path.open", side_effect=AssertionError("opened payload")):
            with self.assertRaisesRegex(ValueError, "evaluation rights"):
                load_inputs(Path("."), "data/processed/invalid", config)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "data/processed/candidate"
            input_dir.mkdir(parents=True)
            members = {}
            for name, obj in {"cohort": c, **p}.items():
                data = json_bytes(obj)
                (input_dir / f"{name}.json").write_bytes(data)
                members[name] = {"sha256": sha256(data), "size_bytes": len(data)}
            config["release"] = {"rights_ref": "synthetic-fixture", "custody_ref": "synthetic-fixture",
                                 "source_review_ref": "synthetic-fixture", "members": members,
                                 "result_status": "PROVISIONAL_PRE_FINAL_ADMISSION"}
            self.assertEqual(load_inputs(root, "data/processed/candidate", config), (c, p))
            bad = deepcopy(config)
            del bad["release"]["members"]["qwen3"]
            with self.assertRaisesRegex(ValueError, "incomplete"):
                load_inputs(root, "data/processed/candidate", bad)
            bad["release"]["members"] = list(members)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                load_inputs(root, "data/processed/candidate", bad)
            (input_dir / "internvl35.json").write_bytes(b"x" * members["internvl35"]["size_bytes"])
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_inputs(root, "data/processed/candidate", config)

    def test_cli_gate_and_export_receipt(self):
        cohort, products, config = fixture()
        argv = ["--input-dir", "data/processed/in", "--output-dir", "data/processed/out"]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            committed_config = {**config, "planned_n": 3763}

            def git_receipt(_, *args):
                if args == ("show", f"HEAD:{CONFIG_PATH}"):
                    return json_bytes(committed_config)
                if args == ("rev-parse", "HEAD"):
                    return b"0" * 40
                if args == ("status", "--porcelain", "--untracked-files=no"):
                    return b""
                self.fail(f"unexpected git call: {args}")

            with patch("scripts.benchmark_full_train.ROOT", root), \
                    patch("scripts.benchmark_full_train.git", side_effect=git_receipt), \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr:
                self.assertEqual(main(argv), 2)
                self.assertIn("evaluation rights", stderr.getvalue())
                self.assertFalse((root / "data").exists())
                for name in SOURCE_FILES:
                    path = root / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"test source")
                result = compare(cohort, products, config, mini_conversion_n=1)
                committed_config["release"] = {"result_status": "PROVISIONAL_PRE_FINAL_ADMISSION"}
                with patch("scripts.benchmark_full_train.load_inputs", return_value=(cohort, products)), \
                        patch("scripts.benchmark_full_train.compare", return_value=result):
                    self.assertEqual(main(argv), 0)
                    self.assertEqual(main(argv), 2)
            output = root / "data/processed/out"
            receipt = json.loads((output / "receipt.json").read_bytes())
            self.assertEqual(receipt["config_sha256"], sha256(json_bytes(committed_config)))
            self.assertEqual(receipt["source_files"], {name: sha256(b"test source") for name in SOURCE_FILES})
            self.assertEqual(receipt["command"][-4:], argv)
            result_json = json.loads((output / "benchmark.json").read_bytes())
            self.assertEqual(result_json["result_status"], "PROVISIONAL_PRE_FINAL_ADMISSION")
            self.assertEqual(receipt["outputs"], {name: sha256((output / name).read_bytes())
                             for name in ("benchmark.json", "metrics.csv", "confusion.html")})
            with (output / "metrics.csv").open(encoding="utf-8", newline="") as stream:
                rows = {r["metric_path"]: r["value"] for r in csv.DictReader(stream)}
            self.assertEqual(json.loads(rows["/models/qwen3/worst_domain/false_safe/domains"]), ["east"])
            self.assertEqual(len(json.loads(rows["/models/minicpm/overall/macro_classes"])), 4)
            self.assertEqual(rows["/minicpm_normalization_impact/overall/converted_n"], "1")
            self.assertEqual(rows["/result_status"], "PROVISIONAL_PRE_FINAL_ADMISSION")


if __name__ == "__main__":
    unittest.main()
