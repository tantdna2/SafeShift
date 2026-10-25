"""Synthetic only: pairwise oracle, joins, grouping assumptions and archive I/O."""

import copy
import csv
import hashlib
import io
import itertools
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile
from collections import Counter

from scripts import analyze_source_sensitivity as cli

from safeshift.evaluation.sensitivity import (
    components, evaluate, join_reports, summarize_groups, weighted_auc,
)
from scripts.analyze_source_sensitivity import (
    analyze, archive_report, checked_bytes, internvl_rows, main, relative_path,
)


def fixture():
    meta, reports = [], {"a": [], "b": []}
    for i, label in enumerate(("Level01", "Level01", "Level04", "Level04")):
        sid = f"synthetic-{i}"
        meta.append({"sample_id": sid, "safety_level": label, "split": "train",
                     "folder_domain": "synthetic-domain", "byte_sha256": str(i // 2),
                     "pixel_sha256": str(i // 2), "point_id": str(i), "source_family": str(i // 2)})
        for model, score in (("a", (4, 1, 2, 0)[i]), ("b", (2, 1, 3, 0)[i])):
            reports[model].append({"sample_id": sid, "true_level": label,
                                   "domain": "synthetic-domain", "status": "SUCCESS",
                                   "generated_label": "Level01", "pa3_score": str(score)})
    audit = {"audit_complete": True, "exit_code": 0, "max_hamming": 8,
             "samples": meta, "near_pair_evidence": []}
    return audit, reports


class AucTests(unittest.TestCase):
    def test_weighted_rank_matches_independent_pairwise_oracle(self):
        labels = [True, False, True, False]
        weights = [0.5, 1, 0.25, 0.5]
        for scores in itertools.product((0, 1, 2), repeat=4):
            numerator = denominator = 0
            for i in (0, 2):
                for j in (1, 3):
                    mass = weights[i] * weights[j]
                    denominator += mass
                    numerator += mass * ((scores[i] > scores[j]) + 0.5 * (scores[i] == scores[j]))
            self.assertAlmostEqual(weighted_auc(labels, scores, weights), numerator / denominator)

    def test_ties_direction_undefined_and_extreme_finite_scores(self):
        self.assertEqual(weighted_auc([True, False], [1, 1]), 0.5)
        self.assertEqual(weighted_auc([True, False], [-1e300, 1e300]), 0)
        self.assertEqual(weighted_auc([True, False], [1e300, -1e300]), 1)
        for labels, scores in (([], []), ([True], [1]), ([False, False], [1, 2])):
            self.assertIsNone(weighted_auc(labels, scores))

    def test_invalid_vectors_fail(self):
        cases = [([True], [], None), ([1, 0], [1, 2], None),
                 ([True, False], [float("nan"), 1], None),
                 ([True, False], [float("inf"), 1], None),
                 ([True, False], [1, 2], [1, 0]),
                 ([True, False], [1, 2], [1, -1]),
                 ([True, False], [1, 2], [1, float("inf")]),
                 ([True, False], [True, 2], None)]
        for labels, scores, weights in cases:
            with self.subTest(labels=labels, scores=scores, weights=weights), self.assertRaises(ValueError):
                weighted_auc(labels, scores, weights)


class CohortTests(unittest.TestCase):
    def test_reordered_exact_join(self):
        audit, reports = fixture()
        reports["a"].reverse()
        meta, models = join_reports(audit["samples"], reports)
        self.assertEqual(set(meta), set(models["a"]))
        self.assertEqual(len(meta), 4)

    def test_rejects_duplicate_missing_extra_labels_domains_status_and_nonfinite(self):
        audit, original = fixture()
        mutations = [lambda r: r.append(r[0]), lambda r: r.pop(),
                     lambda r: r[0].update(sample_id="wrong-id"),
                     lambda r: r[0].update(true_level="Level04"),
                     lambda r: r[0].update(domain="wrong-domain"),
                     lambda r: r[0].update(status="NOT_ATTEMPTED"),
                     lambda r: r[0].update(generated_label="INVALID"),
                     lambda r: r[0].update(pa3_score="nan"),
                     lambda r: r[0].update(pa3_score="inf"),
                     lambda r: r[0].update(true_binary_label="Normal"),
                     lambda r: r[0].update(persisted="False"),
                     lambda r: r[0].update(pa3_score=True)]
        for mutate in mutations:
            reports = copy.deepcopy(original)
            mutate(reports["a"])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                join_reports(audit["samples"], reports)
        for change in ("duplicate", "test", "bad-label", "empty"):
            samples = copy.deepcopy(audit["samples"])
            if change == "duplicate":
                samples.append(samples[0])
            elif change == "test":
                samples[0]["split"] = "test"
            elif change == "bad-label":
                samples[0]["safety_level"] = "unknown"
            else:
                samples = []
            with self.subTest(change=change), self.assertRaises(ValueError):
                join_reports(samples, original)

    def test_transitive_components_order_and_edge_validation(self):
        ids, edges = ["d", "b", "a", "c"], [("a", "b"), ("b", "c")]
        expected = {"a": "a", "b": "a", "c": "a", "d": "d"}
        self.assertEqual(components(ids, edges), expected)
        self.assertEqual(components(reversed(ids), reversed(edges)), expected)
        for invalid in ([("a", "missing")], [("a", "a")]):
            with self.assertRaises(ValueError):
                components(ids, invalid)
        with self.assertRaises(ValueError):
            components(["a", "a"], [])

    def test_single_class_groups_do_not_make_global_auc_undefined(self):
        audit, reports = fixture()
        meta, models = join_reports(audit["samples"], reports)
        mapping = components(meta, [("synthetic-0", "synthetic-1"), ("synthetic-2", "synthetic-3")])
        result = evaluate(meta, models, mapping)
        self.assertEqual(result["group_summary"]["within_group_auc_undefined_n"], 2)
        self.assertEqual(result["strata"]["ALL"]["auroc"]["a"], 0.75)
        self.assertEqual(result["strata"]["ALL"]["anomaly_mass"], 1)
        self.assertEqual(result["strata"]["ALL"]["normal_mass"], 1)
        self.assertEqual(result["strata"]["ALL"]["gaps"]["b_minus_a"], -0.25)

    def test_mixed_group_retains_labels_and_weights_change_estimand(self):
        audit, reports = fixture()
        meta, models = join_reports(audit["samples"], reports)
        mapping = components(meta, [("synthetic-0", "synthetic-2"), ("synthetic-2", "synthetic-3")])
        result = evaluate(meta, models, mapping)
        self.assertEqual(result["group_summary"]["mixed"], 1)
        self.assertAlmostEqual(result["strata"]["ALL"]["anomaly_mass"], 4 / 3)
        self.assertEqual(result["strata"]["ALL"]["anomaly_n"], 2)
        self.assertAlmostEqual(result["strata"]["ALL"]["auroc"]["a"], 0.625)
        with self.assertRaises(ValueError):
            summarize_groups(meta, {})

    def test_representatives_do_not_optimize_scores_or_labels(self):
        audit, reports = fixture()
        meta, models = join_reports(audit["samples"], reports)
        mapping = components(meta, [("synthetic-0", "synthetic-1")])
        first, last = [evaluate(meta, models, mapping, p)["strata"]["ALL"] for p in ("first", "last")]
        self.assertEqual(first["n_images"], 3)
        self.assertEqual(first["auroc"]["a"], 1)
        self.assertEqual(last["auroc"]["a"], 0.5)

    def test_domain_weights_preserved_and_single_class_domain_is_null(self):
        audit, reports = fixture()
        for r in audit["samples"]:
            r["folder_domain"] = "positive" if r["safety_level"] != "Level04" else "negative"
        for rows in reports.values():
            for r in rows:
                r["domain"] = "positive" if r["true_level"] != "Level04" else "negative"
        meta, models = join_reports(audit["samples"], reports)
        result = evaluate(meta, models, components(meta, [("synthetic-0", "synthetic-2")]))
        self.assertEqual(result["strata"]["positive"]["anomaly_mass"], 1.5)
        self.assertIsNone(result["strata"]["positive"]["auroc"]["a"])
        self.assertIsNone(result["strata"]["positive"]["gaps"]["b_minus_a"])
        json.dumps(result, allow_nan=False)


class InputTests(unittest.TestCase):
    def test_analysis_is_proposed_and_does_not_mutate_inputs(self):
        audit, reports = fixture()
        before = copy.deepcopy((audit, reports))
        result = analyze(audit, reports)
        self.assertEqual(len(result["scenarios"]), 10)
        self.assertIn("PROPOSED", result["status"])
        self.assertFalse(result["source_identity_verified"])
        self.assertEqual((audit, reports), before)
        audit["samples"][0]["pixel_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "byte/pixel"):
            analyze(audit, reports)

    def test_group_key_and_candidate_integrity(self):
        for field, value in (("source_family", None), ("point_id", "")):
            audit, reports = fixture()
            audit["samples"][0][field] = value
            with self.assertRaises(ValueError):
                analyze(audit, reports)
        for distance, sid in ((9, "synthetic-1"), (8, "unknown"), (True, "synthetic-1")):
            audit, reports = fixture()
            audit["near_pair_evidence"] = [{"sample_id_a": "synthetic-0", "sample_id_b": sid,
                                             "split_a": "train", "split_b": "train", "dhash_distance": distance}]
            with self.assertRaises(ValueError):
                analyze(audit, reports)

    def test_partial_cohort_must_be_explicit_and_exact(self):
        audit, reports = fixture()
        ids = {"synthetic-0", "synthetic-2"}
        selected = {m: [r for r in rows if r["sample_id"] in ids] for m, rows in reports.items()}
        result = analyze(audit, selected, ids)
        self.assertEqual(result["coverage"]["metadata_n"], 2)
        with self.assertRaises(ValueError):
            analyze(audit, selected)
        for invalid in (set(), {"outside-train"}):
            with self.assertRaises(ValueError):
                analyze(audit, selected, invalid)

    def test_qwen_archive_binding_membership_and_score_checks(self):
        saved = (b"sample_id,true_level,pa3_score\n"
                 b"synthetic-positive,Level01,2\nsynthetic-negative,Level04,1\n")
        manifest = json.dumps({"files": [{"path": "report/samples.csv", "size_bytes": len(saved),
                                          "sha256": hashlib.sha256(saved).hexdigest()}]}).encode()
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for name, payload in (("manifest.json", manifest), ("evidence/report/samples.csv", saved),
                                  ("evidence/raw/forbidden", b"not a report")):
                entry = tarfile.TarInfo(name)
                entry.size = len(payload)
                tar.addfile(entry, io.BytesIO(payload))
        payload = buffer.getvalue()
        result = {"export": {"archive_bytes": len(payload), "archive_sha256": hashlib.sha256(payload).hexdigest(),
                              "manifest_sha256": hashlib.sha256(manifest).hexdigest()},
                  "metrics": {"overall": {"auroc_pa3": {"value": 1, "eligible_ids":
                               ["synthetic-positive", "synthetic-negative"]}}},
                  "unit": {"run_id": "synthetic-run"}}
        original_extract = tarfile.TarFile.extractfile

        def report_only(archive, member):
            self.assertIn(member.name, ("manifest.json", "evidence/report/samples.csv"))
            return original_extract(archive, member)

        with mock.patch.object(tarfile.TarFile, "extractfile", report_only):
            rows, binding = archive_report(payload, result)
        self.assertEqual(len(rows), 2)
        self.assertEqual(binding["samples_sha256"], hashlib.sha256(saved).hexdigest())
        for change in ("archive", "manifest", "membership", "auc"):
            bad = copy.deepcopy(result)
            if change == "archive":
                bad["export"]["archive_sha256"] = "0" * 64
            elif change == "manifest":
                bad["export"]["manifest_sha256"] = "0" * 64
            elif change == "membership":
                bad["metrics"]["overall"]["auroc_pa3"]["eligible_ids"] = ["wrong"]
            else:
                bad["metrics"]["overall"]["auroc_pa3"]["value"] = 0
            with self.subTest(change=change), self.assertRaises(ValueError):
                archive_report(payload, bad)
    def test_hash_paths_and_refuse_overwrite(self):
        for path in ("../outside", "data/raw/x", "C:/private", "/tmp/x", "data\\processed\\x"):
            with self.assertRaises(ValueError):
                relative_path(path)
        self.assertEqual(relative_path("data/processed/synthetic"), Path("data/processed/synthetic"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic"
            path.write_bytes(b"synthetic")
            self.assertEqual(checked_bytes(path, hashlib.sha256(b"synthetic").hexdigest()), b"synthetic")
            with self.assertRaisesRegex(ValueError, "checksum"):
                checked_bytes(path, "0" * 64)
            with mock.patch("scripts.analyze_source_sensitivity.relative_path", return_value=path):
                with self.assertRaises(SystemExit) as exit_info:
                    main(["--input-dir", "x", "--metadata-audit", "x", "--output", "x"])
                self.assertEqual(exit_info.exception.code, 2)
            self.assertEqual(path.read_bytes(), b"synthetic")

    def test_only_exact_regular_csv_archive_member_and_hash_is_accepted(self):
        csv_bytes = b"sample_id,true_level\nsynthetic,Level04\n"

        def archive(names, link=False):
            tar_bytes = io.BytesIO()
            with tarfile.open(fileobj=tar_bytes, mode="w:gz") as tar:
                for name in names:
                    info = tarfile.TarInfo(name)
                    info.size = len(csv_bytes)
                    if link:
                        info.type, info.linkname = tarfile.SYMTYPE, "elsewhere"
                    tar.addfile(info, io.BytesIO(csv_bytes))
            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, "w") as outer:
                outer.writestr("synthetic.tar.gz", tar_bytes.getvalue())
            return zip_bytes.getvalue()

        locked = {"synthetic.tar.gz": hashlib.sha256(csv_bytes).hexdigest()}
        name = "evidence/report/samples.csv"
        self.assertEqual(internvl_rows(archive([name]), locked)[0]["sample_id"], "synthetic")
        for names, link in (([name, name], False), (["other"], False), ([name], True)):
            with self.assertRaises(ValueError):
                internvl_rows(archive(names, link), locked)
        with self.assertRaises(ValueError):
            internvl_rows(archive([name]), {"wrong.tar.gz": "0" * 64})
        with self.assertRaises(ValueError):
            internvl_rows(archive([name]), {"synthetic.tar.gz": "0" * 64})


def original_fixture(mutate=None):
    """Four synthetic planned rows; two successes, one error, one unattempted."""
    rows, metadata, inference, journal = [], {}, [], []
    statuses = ("SUCCESS", "SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED")
    for i, status in enumerate(statuses):
        sid, level = f"synthetic-original-{i}", ("Level01" if i % 2 == 0 else "Level04")
        flags = (status != "NOT_ATTEMPTED", status == "SUCCESS", status == "SUCCESS")
        rows.append({"sample_id": sid, "true_level": level, "domain": "synthetic",
                     "status": status, "pa3_score": str(2 - i) if status == "SUCCESS" else "",
                     "generated_label": "Level01" if status == "SUCCESS" else "",
                     "true_binary_label": "Anomaly" if level != "Level04" else "Normal",
                     **dict(zip(("attempted", "persisted", "parsed"), map(str, flags)))})
        metadata[sid] = {"sample_id": sid, "safety_level": level, "folder_domain": "synthetic",
                         "split": "train", "byte_sha256": str(i)}
        inference.append({"sample_id": sid, "image_sha256": str(i), "image_locator": "synthetic/unused"})
        journal.append({"sample_id": sid, "ordinal": i, "status": status,
                        **dict(zip(("attempted", "persisted", "parsed"), flags))})
    unit = {"model": "qwen3", "id": "synthetic-model", "revision": "synthetic-revision",
            "python": "3.11", "cuda": "synthetic", "cuda_visible_devices": "synthetic",
            "shard": 2, "count": 4, "run_id": "hnlo-train-v4-qwen3-s2-a1",
            "attempt_id": "hnlo-train-v4-qwen3-s2-20261019-a1"}
    scope = {"batch_size": 1, "max_new_tokens": 32}
    endpoint = {"eligible_ids": [r["sample_id"] for r in rows[:2]], "positive_n": 1,
                "negative_n": 1, "pair_denominator": 1, "tie_credit": 0.5, "value": 1}
    source = dict.fromkeys(("implementation_commit", "authority_commit", "merge_commit", "payload_sha256", "pr_number"), "synthetic")
    result = {"unit": copy.deepcopy(unit), "schema": "hnlo-train-unit-result-v1", "scope": "DESCRIPTIVE_FULL_TRAIN",
              "retry": False, "research_generalization_claim": False, "status": "PARTIAL", "sample_journal": journal,
              "coverage": {"planned": 4, "scored": 2, "attempted": 3, "parsed": 2, "persisted": 2,
                           "anomaly_n": 2, "normal_n": 2, "level_counts": {"Level01": 2, "Level04": 2},
                           "coverage": 0.5, "status_counts": dict(Counter(statuses)), "auroc": copy.deepcopy(endpoint)},
              "metrics": {"overall": {"auroc_pa3": copy.deepcopy(endpoint)}}}
    binding = {"unit": copy.deepcopy(unit), "samples": copy.deepcopy(inference), "source": source,
               "authority": {"scope": copy.deepcopy(scope)}}
    state = {"rows": rows, "result": result, "binding": binding, "metadata": metadata}
    if mutate:
        mutate(state)
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    files = {"evidence/report/samples.csv": text.getvalue().encode(),
             "evidence/binding.json": json.dumps(binding).encode(),
             "evidence/result.json": json.dumps(result).encode()}
    manifest = json.dumps({"files": [{"path": k.removeprefix("evidence/"), "size_bytes": len(v),
                                      "sha256": hashlib.sha256(v).hexdigest()} for k, v in files.items()]}).encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, payload in {**files, "manifest.json": manifest}.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    payload = buffer.getvalue()
    result["export"] = {"archive": "hnlo-train-v4-qwen3-s2-a1.tar.gz", "archive_bytes": len(payload),
                        "archive_sha256": hashlib.sha256(payload).hexdigest(), "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
                        "status": "EXPORTED", "unit": copy.deepcopy(unit)}
    return payload, result, unit, inference, scope, metadata


class OriginalV4Tests(unittest.TestCase):
    def test_all_planned_rows_preserved_and_only_success_scores_evaluated(self):
        rows, receipt = cli.verify_v4_shard(*original_fixture())
        self.assertEqual(len(rows), 4)
        self.assertEqual(receipt["status_counts"], {"SUCCESS": 2, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 1})
        self.assertEqual(receipt["auroc_recomputed"], 1)
        self.assertEqual(receipt["planned_n"], 4)

    def test_missing_extra_duplicate_and_wrong_ids_fail(self):
        for mutate in (lambda s: s["rows"].pop(), lambda s: s["rows"].append(s["rows"][0]),
                       lambda s: s["rows"][0].update(sample_id="wrong"),
                       lambda s: s["binding"]["samples"].reverse(),
                       lambda s: s["result"]["sample_journal"][1].update(ordinal=0)):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                cli.verify_v4_shard(*original_fixture(mutate))

    def test_status_coverage_and_non_success_prediction_fail(self):
        changes = [lambda s: s["rows"][0].update(status="INVALID"),
                   lambda s: s["rows"][0].update(parsed="False"),
                   lambda s: s["rows"][2].update(pa3_score="2"),
                   lambda s: s["result"]["coverage"].update(coverage=1),
                   lambda s: s["result"]["coverage"].update(planned=3),
                   lambda s: s["result"]["coverage"]["status_counts"].update(SUCCESS=3),
                   lambda s: s["result"]["coverage"].update(anomaly_n=0)]
        for mutate in changes:
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                cli.verify_v4_shard(*original_fixture(mutate))

    def test_eligible_ids_support_and_nonfinite_metric_fail(self):
        for value in (["wrong"], ["synthetic-original-0"] * 2):
            with self.assertRaises(ValueError):
                cli.verify_v4_shard(*original_fixture(lambda s: s["result"]["metrics"]["overall"]["auroc_pa3"].update(eligible_ids=value)))
        for value in (0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                cli.verify_v4_shard(*original_fixture(lambda s: s["result"]["metrics"]["overall"]["auroc_pa3"].update(value=value)))

    def test_invalid_ground_truth_score_and_config_fail(self):
        for mutate in (lambda s: s["rows"][0].update(true_level="unknown"),
                       lambda s: s["rows"][0].update(true_level="Level04"),
                       lambda s: s["rows"][0].update(pa3_score="nan"),
                       lambda s: s["rows"][0].update(pa3_score="inf"),
                       lambda s: s["binding"]["authority"]["scope"].update(max_new_tokens=16),
                       lambda s: s["result"]["unit"].update(run_id="recovery")):
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                cli.verify_v4_shard(*original_fixture(mutate))

    def test_archive_manifest_and_export_unit_mismatch_fail(self):
        for field in ("archive_sha256", "manifest_sha256"):
            args = original_fixture()
            args[1]["export"][field] = "0" * 64
            with self.assertRaises(ValueError):
                cli.verify_v4_shard(*args)
        args = original_fixture()
        args[1]["export"]["unit"]["revision"] = "wrong"
        with self.assertRaises(ValueError):
            cli.verify_v4_shard(*args)

    def test_single_class_auc_stays_undefined(self):
        def mutate(s):
            for row in s["rows"]:
                row.update(true_level="Level04", true_binary_label="Normal")
                s["metadata"][row["sample_id"]]["safety_level"] = "Level04"
            s["result"]["coverage"].update(anomaly_n=0, normal_n=4, level_counts={"Level04": 4})
            for e in (s["result"]["coverage"]["auroc"], s["result"]["metrics"]["overall"]["auroc_pa3"]):
                e.update(positive_n=0, negative_n=2, pair_denominator=0, value=None)
        _, receipt = cli.verify_v4_shard(*original_fixture(mutate))
        self.assertIsNone(receipt["auroc_recomputed"])

    def make_zip(self, change=None):
        payload, result, *_ = original_fixture()
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
            manifest = tar.extractfile("manifest.json").read()
        result_bytes = json.dumps(result).encode()
        export = json.dumps({**result["export"], "result_sha256": hashlib.sha256(result_bytes).hexdigest()}).encode()
        files = {".tar.gz": payload, "_result.json": result_bytes, "_export.json": export,
                 "_export_sha256.json": json.dumps({"sha256": hashlib.sha256(export).hexdigest()}).encode(),
                 "_manifest.json": manifest, "_sha256.json": json.dumps({
                     "archive": result["export"]["archive"], "sha256": result["export"]["archive_sha256"],
                     "size_bytes": len(payload), "manifest_sha256": result["export"]["manifest_sha256"],
                     "status": "EXPORT_VALID", "verified_evidence_members": 3}).encode()}
        if change:
            change(files)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as outer:
            for suffix, value in files.items():
                outer.writestr("Qwen3-Shard2-V4/hnlo-train-v4-qwen3-s2-a1" + suffix, value)
        return buffer.getvalue(), payload

    def test_original_zip_binding_and_wrong_original_sha(self):
        payload, tar = self.make_zip()
        with mock.patch.multiple(cli, S2_ORIGINAL_SIZE=len(tar), S2_ORIGINAL_SHA256=hashlib.sha256(tar).hexdigest()):
            _, _, receipt = cli.original_s2_zip(payload)
            self.assertEqual(receipt["zip_crc"], "PASS")
        with self.assertRaisesRegex(ValueError, "identity"):
            cli.original_s2_zip(payload)

    def test_zip_crc_structure_and_sidecar_corruption_fail(self):
        changes = [lambda f: f.pop("_manifest.json"),
                   lambda f: f.update({"_extra.json": b"{}"}),
                   lambda f: f.update({"_manifest.json": b"{}"}),
                   lambda f: f.update({"_export_sha256.json": b'{"sha256":"wrong"}'})]
        for change in changes:
            payload, tar = self.make_zip(change)
            with mock.patch.multiple(cli, S2_ORIGINAL_SIZE=len(tar), S2_ORIGINAL_SHA256=hashlib.sha256(tar).hexdigest()):
                with self.assertRaises(ValueError):
                    cli.original_s2_zip(payload)
        payload, tar = self.make_zip()
        corrupt = payload.replace(b"EXPORT_VALID", b"EXPORT_XALID")
        with mock.patch.multiple(cli, S2_ORIGINAL_SIZE=len(tar), S2_ORIGINAL_SHA256=hashlib.sha256(tar).hexdigest()):
            with self.assertRaises((ValueError, zipfile.BadZipFile)):
                cli.original_s2_zip(corrupt)

    def full_cohort(self):
        shards, metadata = {}, {}
        for shard, count in enumerate((941, 941, 941, 940)):
            rows = [{"sample_id": f"synthetic-{shard}-{i}", "true_level": "Level04",
                     "status": ("SUCCESS" if shard != 2 or i < 717 else
                                "TECHNICAL_ERROR" if i == 717 else "NOT_ATTEMPTED")} for i in range(count)]
            unit = {"model": "qwen3", "id": "synthetic", "revision": "synthetic", "python": "synthetic",
                    "cuda": "synthetic", "cuda_visible_devices": "synthetic", "shard": shard, "count": count,
                    "run_id": f"hnlo-train-v4-qwen3-s{shard}-a1",
                    "attempt_id": f"hnlo-train-v4-qwen3-s{shard}-20261019-a1"}
            shards[shard] = (rows, {"unit": unit, "source": {"synthetic": True}, "archive_sha256": cli.S2_ORIGINAL_SHA256})
            metadata.update({r["sample_id"]: {} for r in rows})
        return shards, metadata

    def test_original_full_cohort_counts_and_failure_denominator(self):
        success, receipt = cli.verify_v4_cohort(*self.full_cohort())
        self.assertEqual(len(success), 3539)
        self.assertEqual(receipt["planned_n"], 3763)
        self.assertAlmostEqual(receipt["coverage"], 3539 / 3763)
        self.assertFalse(receipt["baseline_pooling_allowed"])

    def test_recovery_diagnostic_incomplete_duplicate_and_missing_cohort_fail(self):
        for kind in ("recovery", "diagnostic", "missing-shard", "duplicate-id", "status", "source", "revision", "missing-id"):
            shards, metadata = self.full_cohort()
            if kind == "recovery": shards[2][1]["unit"]["run_id"] = "hnlo-qwen3-s2-recovery224-v1-20261022"
            elif kind == "diagnostic": shards[2][1]["archive_sha256"] = "wrong"
            elif kind == "missing-shard": del shards[2]
            elif kind == "duplicate-id": shards[2][0][0]["sample_id"] = shards[0][0][0]["sample_id"]
            elif kind == "status": shards[2][0][0]["status"] = "NOT_ATTEMPTED"
            elif kind == "source": shards[2][1]["source"] = {"other": True}
            elif kind == "revision": shards[2][1]["unit"]["revision"] = "wrong"
            else: metadata.pop(next(iter(metadata)))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                cli.verify_v4_cohort(shards, metadata)


if __name__ == "__main__":
    unittest.main()
