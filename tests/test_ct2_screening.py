"""Synthetic checks for CT2 acquisition, ranking, evaluation and CLI admission."""

from copy import deepcopy
from hashlib import sha256 as hashlib_sha256
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.data.saved_reports import git, json_bytes, sha256
from safeshift.evaluation import ct2_screening
from safeshift.evaluation.full_train_benchmark import PRODUCTS, SCHEMA
from scripts import screen_full_train_triage as cli


def fixture(n=8, eligible_n=6, conversion_n=1):
    truth = ("Level01", "Level02", "Level04", "Level04", "Level01", "Level03", "Level01", "Level04")
    rows = [
        {"sample_id": f"example-{i}", "split": "TRAIN", "image_sha256": f"{i:064x}",
         "true_level": truth[i % len(truth)], "domain": "example-domain"}
        for i in range(n)
    ]
    predictions = {
        "qwen3": ("Level04",) * eligible_n + ("Level02",) * (n - eligible_n),
        "internvl35": ("Level03", "Level01", "Level02") + ("Level04",) * (n - 3),
        "minicpm": ("Level04", "Level04", "Level02", "Level04", "Level01") + ("Level04",) * (n - 5),
    }
    config = {"schema": SCHEMA, "planned_n": n, "products": {}, "release": {
        "rights_ref": "fixture-rights", "custody_ref": "fixture-custody",
        "source_review_ref": "fixture-review", "result_status": "PROVISIONAL_PRE_FINAL_ADMISSION",
    }}
    products = {}
    for model_index, key in enumerate(PRODUCTS, 1):
        seal = f"{model_index:064x}"
        config["products"][key] = {"id": key, "source_seal_sha256": seal}
        samples = []
        for i, (row, label) in enumerate(zip(rows, predictions[key], strict=True)):
            sample = {**row, "source_id": "fixture-source", "status": "SUCCESS", "generated_label": label}
            if key == "minicpm":
                converted = 5 <= i < 5 + conversion_n
                sample.update(original_status="INVALID" if converted else "SUCCESS",
                              original_label=None if converted else label)
            samples.append(sample)
        products[key] = {
            "schema": f"{SCHEMA}-product", "product_id": key, "source_seal_sha256": seal,
            "sources": {"fixture-source": {"run_id": "fixture-run", "attempt_id": "fixture-attempt",
                                           "model_id": key, "revision": "fixture-revision",
                                           "config_sha256": "a" * 64, "artifact_sha256": "b" * 64}},
            "samples": samples[::-1],
        }
    return {"schema": f"{SCHEMA}-cohort", "samples": rows}, products, config


def order(seed, purpose, n=6):
    def hash_for(i):
        encoded = json.dumps([seed, purpose, f"example-{i}"], separators=(",", ":")).encode()
        return hashlib_sha256(encoded).hexdigest()

    return sorted(range(n), key=hash_for)


class ScreeningTest(unittest.TestCase):
    def screen(self, inputs=None, **kwargs):
        return ct2_screening.screen(*(inputs or fixture()), mini_conversion_n=1, **kwargs)

    def test_matched_budget_counts_and_endpoints(self):
        result = self.screen(seeds=(4,), model_call_caps=(14,), review_caps=(1, 2))
        self.assertEqual((result["planned_n"], result["eligible_n"]), (8, 6))
        self.assertEqual(result["focal_only_baseline"], {"same_selection_as": "random_matched"})
        tie_order = order(4, "review-ties")
        one, two = (cell["arms"] for cell in result["cells"])
        self.assertEqual(one["random_matched"]["model_calls"], {"qwen3": 8, "peer": 0, "total": 8})
        self.assertEqual(one["internvl_binary"]["model_calls"], {"qwen3": 8, "peer": 6, "total": 14})
        self.assertEqual(one["internvl_binary"]["workload"]["flag_overflow_n"], 2)
        self.assertEqual(one["internvl_binary"]["workload"]["unresolved_eligible_n"], 5)
        self.assertEqual(one["minicpm_binary"]["acquired_peer_normal_n"], 4)
        strict = one["minicpm_strict_c1_binary"]
        self.assertEqual(strict["acquired_peer_abstention_n"], 1)
        self.assertEqual(strict["acquired_peer_normal_n"], 3)

        self.assertEqual(one["internvl_severity"]["severe_false_safe"]["captured_n"], 0)
        severity = two["internvl_severity"]["false_safe"]
        self.assertEqual((severity["total_n"], severity["captured_n"], severity["residual_n"]), (4, 1, 3))
        self.assertEqual(severity["residual_per_gt_support"]["denominator"], 5)
        self.assertEqual(severity["precision_at_k"]["value"], 1 / 2)
        self.assertEqual(severity["matched_random_expected_captures"]["value"], 8 / 6)
        random_captured = {0, 1, 4, 5} & set(tie_order[:2])
        expected_delta = {"gained_n": len({1} - random_captured),
                          "lost_n": len(random_captured - {1}), "net_n": 1 - len(random_captured)}
        self.assertEqual(severity["vs_matched_random"], expected_delta)
        self.assertEqual(two["random_matched"]["false_safe"]["captured_n"], len(random_captured))
        self.assertEqual(two["internvl_binary"]["false_safe"]["captured_n"],
                         sum(i != 2 for i in [i for i in tie_order if i < 3][:2]))
        self.assertEqual(two["minicpm_binary"]["severe_false_safe"]["captured_n"], 1)

    def test_no_unbought_signal_and_gt_permutation_keeps_selection(self):
        inputs = fixture()
        seed = 7
        purchased = order(seed, "peer-acquisition")[:2]
        options = {"seeds": (seed,), "model_call_caps": (10,), "review_caps": (4,)}
        with patch.object(ct2_screening, "prioritize", wraps=ct2_screening.prioritize) as rank:
            original = self.screen(inputs, **options)
            first_rankings = rank.call_args_list[:]
            self.assertEqual(len(first_rankings), 4)
            for call in first_rankings:
                ids, labels = call.args
                self.assertEqual(ids, [f"example-{i}" for i in order(seed, "review-ties")])
                self.assertEqual(list(labels), [f"example-{i}" for i in purchased])
            rank.reset_mock()

            cohort, products, config = deepcopy(inputs)
            internvl = products["internvl35"]["samples"]
            for row in internvl:
                if row["sample_id"] not in {f"example-{i}" for i in purchased}:
                    row["generated_label"] = "Level01" if row["generated_label"] == "Level04" else "Level04"
            self.assertEqual(original, self.screen((cohort, products, config), **options))
            self.assertEqual(first_rankings, rank.call_args_list)
            rank.reset_mock()

            # Rotate truth consistently across all projections. The admission joins
            # still pass, and each ranking receives the same ID and label arguments.
            truth = [row["true_level"] for row in cohort["samples"]]
            rotated = {row["sample_id"]: truth[i - 1] for i, row in enumerate(cohort["samples"])}
            for projection in (cohort, *products.values()):
                for row in projection["samples"]:
                    row["true_level"] = rotated[row["sample_id"]]
            permuted = self.screen((cohort, products, config), **options)
            self.assertEqual(first_rankings, rank.call_args_list)
            self.assertNotEqual(original["cohort_identity_sha256"], permuted["cohort_identity_sha256"])
            self.assertNotEqual(original["cells"][0]["arms"]["random_matched"]["false_safe"]["total_n"],
                                permuted["cells"][0]["arms"]["random_matched"]["false_safe"]["total_n"])

    def test_zero_budget_oversized_caps_and_no_eligible(self):
        result = self.screen(seeds=(0,), model_call_caps=(8, 20), review_caps=(0, 10))
        no_peer, no_peer_full, full_peer_zero, full_peer_full = (cell["arms"] for cell in result["cells"])
        for arm in no_peer.values():
            self.assertEqual((arm["model_calls"]["total"], arm["eligible_unqueried_n"]), (8, 6))
            self.assertEqual(arm["workload"]["unique_reviews_n"], 0)
            self.assertIsNone(arm["false_safe"]["precision_at_k"]["value"])
        self.assertEqual(no_peer_full["internvl_severity"]["false_safe"],
                         no_peer_full["random_matched"]["false_safe"])
        self.assertEqual(full_peer_zero["internvl_severity"]["workload"]["flag_overflow_n"], 3)
        arm = full_peer_full["internvl_severity"]
        self.assertEqual((arm["model_calls"]["total"], arm["eligible_unqueried_n"]), (14, 0))
        self.assertEqual((arm["workload"]["unique_reviews_n"], arm["workload"]["unused_review_slots_n"]), (6, 4))
        self.assertEqual(arm["false_safe"]["residual_n"], 0)
        empty = self.screen(fixture(eligible_n=0), seeds=(0,), model_call_caps=(14,), review_caps=(1,))
        arm = empty["cells"][0]["arms"]["internvl_severity"]
        self.assertEqual(arm["model_calls"]["total"], 8)
        self.assertEqual(arm["false_safe"]["matched_random_expected_captures"]["value"], 0)
        for invalid in ({"model_call_caps": (7,)}, {"review_caps": (-1,)},
                        {"seeds": (0, 0)}, {"review_caps": ()}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.screen(**invalid)

    def test_reuses_exact_roster_cohort_and_product_validation(self):
        for projection, field, value in (
            ("cohort", "split", "TEST"),
            ("qwen3", "sample_id", "missing-id"),
            ("internvl35", "image_sha256", "f" * 64),
            ("minicpm", "true_level", "Level01"),
            ("minicpm", "status", "NOT_ATTEMPTED"),
        ):
            with self.subTest(projection=projection, field=field):
                cohort, products, config = fixture()
                by_name = {"cohort": cohort, **products}
                by_name[projection]["samples"][0][field] = value
                with self.assertRaises(ValueError):
                    self.screen((cohort, products, config))
        for mutation in ("missing", "duplicate", "wrong seal"):
            with self.subTest(mutation=mutation):
                cohort, products, config = fixture()
                internvl = products["internvl35"]
                if mutation == "missing":
                    internvl["samples"].pop()
                elif mutation == "duplicate":
                    internvl["samples"].append(internvl["samples"][0])
                else:
                    internvl["source_seal_sha256"] = "f" * 64
                with self.assertRaises(ValueError):
                    self.screen((cohort, products, config))
        cohort, products, config = fixture()
        del products["minicpm"]
        with self.assertRaisesRegex(ValueError, "product roster"):
            self.screen((cohort, products, config))

    def test_cli_reproducible_aggregate_export_and_real_admission_checks(self):
        cohort, products, config = fixture(n=3763, eligible_n=2609, conversion_n=205)
        members = {name: json_bytes(obj) for name, obj in {"cohort": cohort, **products}.items()}
        config["release"]["members"] = {name: {"sha256": sha256(data), "size_bytes": len(data)}
                                        for name, data in members.items()}
        config_bytes = json_bytes(config)
        git_sha = "a" * 40

        def synthetic_git(root, *args):
            if args == ("rev-parse", "HEAD"):
                return git_sha.encode()
            if args == ("status", "--porcelain", "--untracked-files=normal"):
                return b"?? untracked-fixture"
            if args in (("show", f"HEAD:{cli.CONFIG_PATH}"), ("show", f"{git_sha}:{cli.CONFIG_PATH}")):
                return config_bytes
            return git(root, *args)

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            git(root, "init", "--quiet")
            ignore = root / ".gitignore"
            ignore.write_text("/data/\n", encoding="utf-8")
            for name in cli.SOURCE_FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((cli.ROOT / name).read_bytes())
            directory = "data/processed/private-example-input"
            source = root / directory
            source.mkdir(parents=True)
            for name, data in members.items():
                (source / f"{name}.json").write_bytes(data)

            def run(output, *settings):
                return cli.main(["--input-dir", directory, "--output-dir", output, *settings])

            with patch.object(cli, "ROOT", root), patch.object(cli, "git", synthetic_git), \
                    patch("scripts.benchmark_full_train.git", synthetic_git), \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr:
                first, second = "data/processed/example-out-a", "data/processed/example-out-b"
                self.assertEqual(run(first), 0, stderr.getvalue())
                self.assertEqual(run(second), 0, stderr.getvalue())
                for name in cli.OUTPUT_FILES:
                    left = (root / first / name).read_bytes()
                    self.assertEqual(left, (root / second / name).read_bytes())
                    for private in (b"example-420", b"example-domain", b"fixture-run",
                                    b"private-example-input", b"example-out-a", b"image_sha256", b"true_level"):
                        self.assertNotIn(private, left)
                result_path = root / first / "screening.json"
                result = json.loads(result_path.read_bytes())
                self.assertEqual(result["eligible_n"], 2609)
                self.assertEqual(result["model_call_caps"], [4139, 4891, 6372])
                self.assertEqual(result["review_caps"], [37, 188, 376])
                self.assertEqual(result["seeds"], [0, 1, 2])
                self.assertEqual(len(result["cells"]), 27)
                receipt = json.loads((root / first / "receipt.json").read_bytes())
                self.assertEqual(receipt["source_sha"], git_sha)
                self.assertTrue(receipt["source_dirty"])
                self.assertEqual(receipt["result_status"], "EXPLORATORY_EXPOSED_TRAIN")
                self.assertEqual(receipt["upstream_result_status"], "PROVISIONAL_PRE_FINAL_ADMISSION")
                self.assertEqual(receipt["inputs"], config["release"]["members"])
                self.assertEqual(receipt["outputs"], {"screening.json": sha256(result_path.read_bytes())})
                self.assertEqual(receipt["config_sha256"], sha256(config_bytes))
                self.assertEqual(receipt["source_files"], {name: sha256((root / name).read_bytes())
                                                           for name in cli.SOURCE_FILES})
                self.assertEqual(run(first), 2)
                self.assertEqual(receipt["outputs"], {"screening.json": sha256(result_path.read_bytes())})
                nested = f"{directory}/nested"
                self.assertEqual(run(nested), 2)
                self.assertFalse((root / nested).exists())
                self.assertEqual(run("data/outside"), 2)
                custom = "data/processed/example-out-custom"
                self.assertEqual(run(custom, "--model-call-cap", "3763", "--model-call-cap", "3764",
                                     "--review-cap", "0", "--seed", "4"), 0, stderr.getvalue())
                custom_result = json.loads((root / custom / "screening.json").read_bytes())
                self.assertEqual([cell["model_call_cap"] for cell in custom_result["cells"]], [3763, 3764])
                self.assertTrue(all(cell["review_cap"] == 0 and cell["seed"] == 4
                                    for cell in custom_result["cells"]))

                # Changing one byte within an admitted size must fail before export.
                member = source / "internvl35.json"
                member.write_bytes(b" " + members["internvl35"][1:])
                wrong_hash = "data/processed/example-out-bad-hash"
                self.assertEqual(run(wrong_hash), 2)
                self.assertIn("SHA-256", stderr.getvalue())
                self.assertFalse((root / wrong_hash).exists())
                member.write_bytes(members["internvl35"])
                ignore.write_text("", encoding="utf-8")
                unignored = "data/processed/example-out-unignored"
                self.assertEqual(run(unignored), 2)
                self.assertIn("Git-ignored", stderr.getvalue())
                self.assertFalse((root / unignored).exists())


if __name__ == "__main__":
    unittest.main()
