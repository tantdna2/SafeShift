"""C01–C10 synthetic-only acceptance. Oracles use enumeration/hand arithmetic.

No fixture borrows any research payload. Archive mutations are generated in RAM.
Subprocess tests use -S (standard library only), and an audited filesystem fence.
"""

import copy
import csv
import io
import itertools
import json
import math
from pathlib import Path
import random
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

from safeshift.data import saved_reports as reader
from safeshift.evaluation import seminar as metrics
from scripts import analyze_seminar as cli

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / reader.CONFIG_PATH).read_text(encoding="utf-8"))


def oracle_auc(labels, scores, weights):
    pairs = [(i, j) for i in range(len(labels)) for j in range(len(labels)) if labels[i] and not labels[j]]
    denominator = sum(weights[i] * weights[j] for i, j in pairs)
    if not denominator:
        return None
    return sum(weights[i] * weights[j] * (1 if scores[i] > scores[j] else 0.5 if scores[i] == scores[j] else 0)
               for i, j in pairs) / denominator


def fixture():
    return reader.read_synthetic(CONFIG)[:3]


def invalid(row, keep_score=False):
    row.update(generated_label=None, parsed=False, label_reason="INVALID")
    if keep_score:
        row["score_independent_of_parse"] = True
    else:
        row.update(hnlo_score=None, score_reason="MISSING_SCORE")


def archive_bytes(kind, entries):
    buffer = io.BytesIO()
    if kind == "zip":
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                for name, payload, link in entries:
                    info = zipfile.ZipInfo(name)
                    if link:
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    archive.writestr(info, payload)
    else:
        with tarfile.open(fileobj=buffer, mode="w") as archive:
            for name, payload, link in entries:
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                if link:
                    info.type = tarfile.SYMTYPE
                    info.linkname = "../../escape"
                archive.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.meta, self.reports, self.near = fixture()

    def test_c01_exact_join_duplicate_missing_extra_label_domain_split(self):
        for change in ("duplicate", "missing", "extra", "label", "domain", "split", "id", "unknown"):
            with self.subTest(change=change):
                reports = copy.deepcopy(self.reports)
                row = reports["qwen25"][0]
                if change == "duplicate":
                    reports["qwen25"].append(copy.deepcopy(row))
                elif change == "missing":
                    reports["qwen25"].pop()
                elif change == "extra":
                    extra = copy.deepcopy(row)
                    extra["sample_id"] = "extra"
                    reports["qwen25"].append(extra)
                elif change == "label":
                    row["true_level"] = "Level04"
                elif change == "domain":
                    row["folder_domain"] = "power"
                elif change == "split":
                    row["split"] = "test"
                elif change == "id":
                    row["sample_id"] = " synthetic-00"
                else:
                    row["generated_label"] = "INVALID"
                with self.assertRaises(ValueError):
                    metrics.analyze(self.meta, reports, self.near, CONFIG)
        for key, value in (("split", "test"), ("true_level", "Normal"), ("folder_domain", "new-domain")):
            metadata = copy.deepcopy(self.meta)
            metadata[0][key] = value
            with self.assertRaises(ValueError):
                metrics.analyze(metadata, self.reports, self.near, CONFIG)

    def test_c02_c03_native_identity_partial_ledger_recovery(self):
        result = metrics.analyze(self.meta, self.reports, self.near, CONFIG)
        self.assertEqual(result["memberships"]["V3539"]["ids"], [f"synthetic-{i:02d}" for i in range(10)])
        self.assertEqual(result["memberships"]["M224"]["ids"], ["synthetic-10", "synthetic-11"])
        coverage = next(r for r in result["R1"] if r["cohort_id"] == "T3763" and r["model_id"] == "qwen3" and r["stratum"] == "ALL")
        self.assertEqual([coverage[x] for x in ("planned_n", "attempted_n", "SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED")], [12, 11, 10, 1, 1])
        self.assertEqual(result["R2"]["V3539"]["ALL"]["qwen3"]["classification"]["n_images"], 10)
        self.assertFalse(result["memberships"]["REC224"]["baseline_pooling_allowed"])
        for key, value in (("revision", "wrong"), ("source_commit", "wrong"), ("run_id", "recovery"),
                           ("attempt_id", "rerun"), ("config_sha256", "wrong"), ("release", "REC224"),
                           ("native_status", "INVALID"), ("shard", True)):
            reports = copy.deepcopy(self.reports)
            reports["qwen3"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                metrics.analyze(self.meta, reports, self.near, CONFIG)
        for key in ("generated_label", "hnlo_score", "persisted", "parsed"):
            reports = copy.deepcopy(self.reports)
            reports["qwen3"][-1][key] = "Level04" if key == "generated_label" else 0 if key == "hnlo_score" else True
            with self.subTest(key=key), self.assertRaises(ValueError):
                metrics.analyze(self.meta, reports, self.near, CONFIG)

    def test_c04_c06_independent_label_score_sets_nonfinite_and_missing_model(self):
        invalid(self.reports["qwen25"][0], keep_score=True)
        self.reports["qwen25"][1].update(hnlo_score=None, score_reason="MISSING_SCORE")
        result = metrics.analyze(self.meta, self.reports, self.near, CONFIG)
        info = result["R2"]["T3763"]["ALL"]["qwen25"]["ranking"]["eligibility"]
        self.assertEqual(info["counts"], {"P": 12, "O": 12, "L": 11, "F": 11, "J": 10})
        self.assertEqual(info["excluded"]["J"]["by_level"], {"Level01": 1, "Level04": 1})
        for value in (float("nan"), float("inf"), -float("inf"), True, "1"):
            reports = copy.deepcopy(self.reports)
            reports["qwen25"][0]["hnlo_score"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                metrics.analyze(self.meta, reports, self.near, CONFIG)
        del self.reports["qwen3"]
        with self.assertRaises(ValueError):
            metrics.analyze(self.meta, self.reports, self.near, CONFIG)

    def test_c06_empty_and_all_invalid(self):
        result = metrics.analyze([], {m: [] for m in reader.MODELS}, [], CONFIG)
        self.assertIsNone(result["R2"]["T3763"]["ALL"]["qwen25"]["ranking"]["hnlo_F"]["value"])
        self.assertEqual(result["R4"]["three_model_main"]["ALL"]["joint_parse"]["reason"], "EMPTY")
        for rows in self.reports.values():
            for row in rows:
                if row["persisted"]:
                    invalid(row)
        result = metrics.analyze(self.meta, self.reports, self.near, CONFIG)
        c = result["R2"]["V3539"]["ALL"]["qwen3"]["classification"]
        self.assertEqual(c["invalid_n"], 10)
        self.assertEqual(c["rates"]["accuracy4"]["value"], 0)
        self.assertIsNone(result["R4"]["three_model_main"]["ALL"]["unanimous4"]["value"])
        self.assertEqual(result["R3"]["completion_bounds"]["ALL"]["false_safe"]["status"], "BLOCKED")

    def test_c01_membership_digest_literal_oracle(self):
        import hashlib
        self.assertEqual(reader.membership(["z", "a"]), hashlib.sha256(b"a\nz\n").hexdigest())
        self.assertEqual(reader.membership([]), hashlib.sha256(b"").hexdigest())
        with self.assertRaises(ValueError):
            reader.membership(["a", "a"])


class FormulaTests(unittest.TestCase):
    def test_c05_pair_enumeration_all_binary_labels_scores_and_ties(self):
        for labels in itertools.product((False, True), repeat=4):
            for scores in itertools.product((-1, 0, 1), repeat=4):
                for weights in ([1, 1, 1, 1], [0.5, 1, 1 / 3, 2]):
                    expected = oracle_auc(labels, scores, weights)
                    actual = metrics.auc(list(labels), list(scores), weights)
                    if expected is None:
                        self.assertIsNone(actual["value"])
                    else:
                        self.assertAlmostEqual(actual["value"], expected, delta=1e-12)
                        self.assertAlmostEqual(actual["numerator"] / actual["denominator"], expected, delta=1e-12)
        self.assertEqual(metrics.auc([True, False], [1, 1])["value"], 0.5)
        self.assertEqual(metrics.auc([True], [1])["reason"], "ONE_CLASS")
        self.assertEqual(metrics.auc([], [])["reason"], "EMPTY")

    def test_c06_hand_confusion_binary_invalid_and_paired_controls(self):
        _, reports, _ = fixture()
        rows = copy.deepcopy(reports["qwen25"][:4])
        for r, y, p, score in zip(rows, ("Level01", "Level04", "Level02", "Level04"),
                                  ("Level04", "Level01", None, "Level04"), (2, 1, 1, 0)):
            r.update(true_level=y, generated_label=p, hnlo_score=score)
        result = metrics.classification(rows)
        self.assertEqual(result["binary_counts"], {"TP": 0, "FN": 1, "FP": 1, "TN": 1, "U_A": 1, "U_N": 0})
        expected_matrix = [[0, 0, 0, 1, 0], [0, 0, 0, 0, 1], [0, 0, 0, 0, 0], [1, 0, 0, 1, 0]]
        self.assertEqual([list(result["confusion_matrix"][l].values()) for l in reader.SAFETY_LEVELS], expected_matrix)
        self.assertEqual(result["rates"]["accuracy4"]["value"], 0.25)
        self.assertEqual(result["rates"]["FNR_observed"]["value"], 0.5)
        self.assertEqual(result["rates"]["recall_A"]["value"], 0)
        self.assertEqual(result["rates"]["macro_recall"]["value"], 1 / 6)
        self.assertEqual(result["macro_classes"], ["Level01", "Level02", "Level04"])
        ranking = metrics.ranking(rows)
        self.assertEqual(ranking["hnlo_F"]["value"], 0.875)
        self.assertEqual(ranking["paired_J"]["hnlo"]["value"], 1)
        self.assertEqual(ranking["paired_J"]["hard"]["value"], 0.25)
        self.assertEqual(ranking["paired_J"]["ordinal"]["value"], 0.25)
        self.assertEqual(ranking["delta"]["hard"]["value"], 0.75)
        self.assertEqual(ranking["paired_J"]["always_anomaly"]["value"], 0.5)
        self.assertEqual(metrics.dangerous(rows)["severe_miss"]["value"], 1)

    def test_c07_completion_bounds_hand_and_invalid_block(self):
        _, reports, _ = fixture()
        rows = reports["qwen3"]
        bounds = metrics.completion_bounds(rows)
        # 2 observed false-safes + 1 missing hazard; total 6 hazards.
        self.assertEqual((bounds["false_safe"]["lower"], bounds["false_safe"]["upper"]), (2 / 6, 3 / 6))
        self.assertEqual((bounds["severe_miss"]["lower"], bounds["severe_miss"]["upper"]), (2 / 3, 1))
        invalid(rows[0])
        self.assertEqual(metrics.completion_bounds(rows)["false_safe"]["reason"], "BOUND_REQUIRES_ALL_OBSERVED_LABELS_VALID")
        self.assertIsNone(metrics.completion_bounds([])["severe_miss"]["lower"])

    def test_c07_vote_entropy_kappa_hand_oracles(self):
        signals = metrics.vote_signals(["Level04", "Level01", "Level04"])
        h2 = -(2 / 3 * math.log(2 / 3) + 1 / 3 * math.log(1 / 3)) / math.log(2)
        self.assertAlmostEqual(signals["H2"], h2)
        self.assertAlmostEqual(signals["H4"], h2 / 2)
        self.assertAlmostEqual(signals["D"], 2 / 3)
        self.assertEqual(metrics.vote_signals(["Level02"] * 3), {"H4": 0, "H2": 0, "D": 0})
        k = metrics.kappa(["Level01", "Level01", "Level04", "Level04"], ["Level01", "Level04", "Level04", "Level04"])
        self.assertEqual(k["observed_agreement"]["value"], 0.75)
        self.assertEqual(k["expected_agreement"], 0.5)
        self.assertEqual(k["value"], 0.5)
        self.assertIsNone(metrics.kappa(["Level04"] * 2, ["Level04"] * 2)["value"])
        self.assertEqual(metrics.kappa([], [])["reason"], "EMPTY")
        with self.assertRaises(ValueError):
            metrics.vote_signals(["Level04", None])

    def test_c07_error_positive_b04_same_ids_hnlo_direction(self):
        meta, reports, near = fixture()
        result = metrics.analyze(meta, reports, near, CONFIG)
        panel = result["R4"]["three_model_main"]["ALL"]
        b04 = [0, 1, 5, 6, 7, 9]
        self.assertEqual(panel["B04"]["ids"], [f"synthetic-{i:02d}" for i in b04])
        hnlo = panel["association"]["B04_matched"]["signals"]["HNLO_Q3"]
        expected = oracle_auc([True, False, False, True, False, False], [2, 1, -1, 0, 0, -2], [1] * 6)
        self.assertEqual(hnlo["false_safe_auc"]["value"], expected)
        self.assertEqual(hnlo["error4_auc"], hnlo["false_safe_auc"])
        self.assertEqual(panel["association"]["joint"]["signals"]["H4"]["error4_auc"]["positive_n"], 4)
        self.assertEqual(panel["association"]["joint"]["signals"]["H4"]["false_safe_auc"]["positive_n"], 2)
        self.assertEqual(panel["complementarity"]["qwen25->qwen3"]["value"], 3 / 5)
        self.assertEqual(panel["complementarity"]["qwen25->qwen3"]["both_wrong"], 2)
        reports["qwen3"][0].update(hnlo_score=None, score_reason="MISSING_SCORE")
        panel = metrics.analyze(meta, reports, near, CONFIG)["R4"]["three_model_main"]["ALL"]
        self.assertEqual(len(panel["B04"]["matched_signal_ids"]), 5)
        counts = [s["false_safe_auc"]["eligible_n"] for s in panel["association"]["B04_matched"]["signals"].values()]
        self.assertEqual(counts, [5, 5, 5, 5])

    def test_c07_all_agree_shared_wrong_and_zero_errors(self):
        meta, reports, near = fixture()
        for rows in reports.values():
            for row in rows:
                if row["persisted"]:
                    row["generated_label"] = "Level04"
        panel = metrics.analyze(meta, reports, near, CONFIG)["R4"]["three_model_main"]["ALL"]
        self.assertEqual(panel["unanimous4"]["value"], 1)
        self.assertEqual(panel["shared_false_safe"]["value"], 1)
        self.assertEqual(panel["unanimous_wrong4"]["value"], 0.5)
        for signal in panel["association"]["B04"]["signals"].values():
            self.assertEqual(signal["distinct_scores"], 1)
            self.assertEqual(signal["error4_auc"]["value"], 0.5)
        for rows in reports.values():
            for row in rows:
                if row["persisted"]:
                    row["generated_label"] = row["true_level"]
        panel = metrics.analyze(meta, reports, near, CONFIG)["R4"]["three_model_main"]["ALL"]
        self.assertIsNone(panel["association"]["joint"]["signals"]["H4"]["error4_auc"]["value"])
        self.assertIsNone(panel["complementarity"]["qwen25->qwen3"]["value"])

    def test_c07_risk_curve_endpoints_tie_blocks_and_undefined(self):
        result = metrics.risk_coverage([0, 0, 2, 1], [True, False, True, False],
                                       [True, False, True, False], [True, False, True, True])
        self.assertEqual([r["retained_n"] for r in result], [0, 2, 3, 4])
        self.assertEqual([r["coverage"] for r in result], [0, 0.5, 0.75, 1])
        self.assertEqual([r["risk4"]["value"] for r in result], [None, 0.5, 1 / 3, 0.5])
        self.assertEqual([r["residual_FS"]["value"] for r in result], [0, 1 / 3, 1 / 3, 2 / 3])
        self.assertEqual(len(metrics.risk_coverage([1, 1], [True, False], [True, False], [True, False])), 2)
        self.assertIsNone(metrics.risk_coverage([], [], [], [])[0]["coverage"])
        self.assertIsNone(metrics.risk_coverage([0], [False], [False], [False])[-1]["residual_FS"]["value"])


class GroupTests(unittest.TestCase):
    def test_c08_transitive_variants_weights_representatives_and_oracle(self):
        metadata, reports, near = fixture()
        meta = reader.indexed(metadata)
        variants = metrics.group_variants(meta, near, CONFIG["sensitivity"]["variants"])
        self.assertEqual(len(variants), 10)
        mapping, weights = variants["exact_point_family_near8"]
        self.assertEqual({mapping[f"synthetic-{i:02d}"] for i in range(5)}, {"synthetic-00"})
        self.assertEqual([weights[f"synthetic-{i:02d}"] for i in range(5)], [0.2] * 5)
        self.assertEqual(len(set(mapping.values())), 8)
        self.assertIn("synthetic-00", variants["exact_representative_first"][1])
        self.assertNotIn("synthetic-01", variants["exact_representative_first"][1])
        self.assertIn("synthetic-01", variants["exact_representative_last"][1])
        # Independent BFS oracle for connected components, no union-find reuse.
        edges = [("synthetic-00", "synthetic-01"), ("synthetic-01", "synthetic-02"),
                 ("synthetic-02", "synthetic-03"), ("synthetic-03", "synthetic-04")]
        for sid in meta:
            reached, pending = set(), [sid]
            while pending:
                current = pending.pop()
                if current in reached:
                    continue
                reached.add(current)
                pending += [b if a == current else a for a, b in edges if current in (a, b)]
            self.assertEqual(mapping[sid], min(reached))
        result = metrics.analyze(metadata, reports, near, CONFIG)
        variant = result["R3"]["sensitivity"]["T3763"]["variants"]["exact_point_family_near8"]
        for domain in ["ALL", *CONFIG["domains"]]:
            rows = [r for r in reports["qwen25"] if domain == "ALL" or r["folder_domain"] == domain]
            w = [weights[r["sample_id"]] for r in rows]
            expected = oracle_auc([r["true_level"] != "Level04" for r in rows], [r["hnlo_score"] for r in rows], w)
            got = variant["strata"][domain]["models"]["qwen25"]["hnlo_F"]
            if expected is None:
                self.assertIsNone(got["value"])
            else:
                self.assertAlmostEqual(got["value"], expected, delta=1e-12)
            self.assertAlmostEqual(got["positive_mass"] + got["negative_mass"], sum(w))
        self.assertEqual(variant["group_summary"]["cross_domain_groups"], 1)
        self.assertEqual(variant["group_summary"]["severity_conflict_groups"], 1)

    def test_c08_no_outside_cohort_bridge_null_groups_pixel_mismatch(self):
        metadata, _, _ = fixture()
        meta = reader.indexed(metadata)
        small = {k: meta[k] for k in ("synthetic-00", "synthetic-04")}
        result = metrics.group_variants(small, [("synthetic-00", "outside", 1), ("outside", "synthetic-04", 1)], ["exact_point_family_near8"])
        self.assertEqual(len(set(result["exact_point_family_near8"][0].values())), 2)
        meta["synthetic-01"]["pixel_sha256"] = "different"
        with self.assertRaises(ValueError):
            metrics.group_variants(meta, [], ["exact"])


class EvidenceTests(unittest.TestCase):
    def test_c02_all_four_units_and_nested_sidecar_required(self):
        metadata, units, near = reader.synthetic_fixture(CONFIG)
        for mutated in (units[:-1], units + [units[0]]):
            with mock.patch.object(reader, "synthetic_fixture", return_value=(metadata, mutated, near)):
                with self.assertRaises(ValueError):
                    reader.read_synthetic(CONFIG)

    def test_c10_missing_postmerge_grant_and_unmerged_origin_are_denied(self):
        actual = reader.strict_json
        for key, value in (("scope", "REAL_ARTIFACTS"), ("task_grant_ref", None),
                           ("merged", False), ("post_merge_verdict", "FAIL"),
                           ("m4_real_artifact_access_granted", True)):
            def altered(payload, key=key, value=value):
                result = actual(payload)
                if isinstance(result, dict) and result.get("schema_version") == "safeshift-m3-authority-v1":
                    result[key] = value
                return result
            with mock.patch.object(reader, "strict_json", altered), self.subTest(key=key):
                with self.assertRaises(reader.AuthorityError):
                    reader.verify_authority(ROOT)
        real_git = reader.git
        def unmerged(root, *args):
            if args == ("merge-base", "--is-ancestor", reader.MERGE, "origin/main"):
                raise reader.AuthorityError("unmerged origin")
            return real_git(root, *args)
        with mock.patch.object(reader, "git", unmerged), self.assertRaises(reader.AuthorityError):
            reader.verify_authority(ROOT)

    def test_c02_c10_archive_hash_size_crc_duplicates_traversal_links_and_missing(self):
        data = b"synthetic payload"
        members = reader.inventory({"report.csv": data})
        for kind in ("tar", "zip"):
            payload = archive_bytes(kind, [("report.csv", data, False)])
            self.assertEqual(reader.archive_members(payload, reader.sha256(payload), members, kind), {"report.csv": data})
            with self.assertRaises(reader.IntegrityError):
                reader.archive_members(payload, "0" * 64, members, kind)
            for changes in ([("report.csv", b"wrong", False)], [("report.csv", data, True)],
                            [("report.csv", data, False)] * 2, [("../escape", data, False)],
                            [("/absolute", data, False)], [("C:/escape", data, False)],
                            [("report.csv", data, False), ("image.png", data, False)], []):
                changed = archive_bytes(kind, changes)
                with self.subTest(kind=kind, changes=changes), self.assertRaises(ValueError):
                    reader.archive_members(changed, reader.sha256(changed), members, kind)
        payload = archive_bytes("zip", [("report.csv", data, False)])
        offset = payload.index(data)
        damaged = payload[:offset] + b"X" + payload[offset + 1:]
        with self.assertRaisesRegex(reader.IntegrityError, "CRC"):
            reader.archive_members(damaged, reader.sha256(damaged), members, "zip")

    def test_c02_native_manifest_binding_journal_order_flags_and_finite(self):
        metadata, units, _ = reader.synthetic_fixture(CONFIG)
        unit = next(u for u in units if u["contract"]["identity"]["model_id"] == "qwen3")
        outer = reader.archive_members(unit["payload"], unit["sha256"], unit["members"], "zip")
        original = reader.archive_members(outer["unit.tar"], reader.sha256(outer["unit.tar"]), unit["inner_members"], "tar")
        for target in ("binding", "result", "journal", "order", "finite", "label", "flags", "manifest"):
            files = dict(original)
            if target in ("binding", "result", "journal", "order"):
                name = "binding.json" if target == "binding" else "result.json"
                value = reader.strict_json(files[name])
                if target in ("binding", "result"):
                    value["identity"]["attempt_id"] = "rerun"
                elif target == "journal":
                    value["journal"][0]["status"] = "NOT_ATTEMPTED"
                else:
                    value["ordered_ids"].reverse()
                files[name] = reader.json_bytes(value)
            elif target in ("finite", "label", "flags"):
                rows = list(csv.DictReader(io.StringIO(files["samples.csv"].decode())))
                rows[0][{"finite": "pa3_score", "label": "generated_label", "flags": "parsed"}[target]] = {
                    "finite": "nan", "label": "INVALID", "flags": "False"}[target]
                out = io.StringIO()
                writer = csv.DictWriter(out, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
                files["samples.csv"] = out.getvalue().encode()
            files["manifest.json"] = reader.json_bytes(reader.inventory({k: v for k, v in files.items() if k != "manifest.json"}))
            if target == "manifest":
                files["manifest.json"] = b"{}"
            with self.subTest(target=target), self.assertRaises(ValueError):
                reader.read_unit(files, unit["contract"], reader.indexed(metadata))

    def test_c10_authority_real_git_and_tamper_fail_closed(self):
        config, authority = reader.verify_authority(ROOT)
        self.assertFalse(config["protocol"]["frozen"])
        self.assertEqual(authority["scope"], "CPU_SYNTHETIC_FIXTURES_ONLY")
        self.assertFalse(authority["m4_real_artifact_access_granted"])
        real_read = Path.read_bytes
        for relative in (reader.CONFIG_PATH, reader.PROTOCOL_PATH, reader.AUTHORITY_PATH):
            def tampered(path, relative=relative):
                data = real_read(path)
                return data + b" " if path == ROOT / relative else data
            with self.subTest(path=relative), mock.patch.object(Path, "read_bytes", tampered):
                with self.assertRaises(reader.IntegrityError):
                    reader.verify_authority(ROOT)
        real_git = reader.git
        def absent_decision(root, *args):
            if args == ("show", reader.MERGE + ":docs/research/DECISIONS.md"):
                return b"# No decision\n"
            return real_git(root, *args)
        with mock.patch.object(reader, "git", absent_decision), self.assertRaises(reader.AuthorityError):
            reader.verify_authority(ROOT)
        for path in ("data/raw/secret.json", "../config.json", "/tmp/config", "C:/secret.json"):
            with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("must reject before read")):
                with self.assertRaises(reader.AuthorityError):
                    reader.verify_authority(ROOT, path)

    def test_c10_symlink_reparse_path_escape_without_privileged_link_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for path in ("../escape", "/absolute", "C:/escape", "data/processed/a:stream", "data//processed/a"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    reader.confined(root, path)
            # Exercise the exact OS link/reparse branch without requiring Windows
            # Developer Mode/admin symlink creation. No test is skipped.
            real_is_symlink = Path.is_symlink
            def symlink(path):
                return path == root / "data" or real_is_symlink(path)
            with mock.patch.object(Path, "is_symlink", symlink), self.assertRaises(reader.AuthorityError):
                reader.confined(root, "data/processed/seminar/out")
            (root / "data").mkdir()
            real_lstat = Path.lstat
            def reparse(path):
                return mock.Mock(st_file_attributes=0x400) if path == root / "data" else real_lstat(path)
            with mock.patch.object(Path, "is_symlink", return_value=False), mock.patch.object(Path, "lstat", reparse):
                with self.assertRaises(reader.AuthorityError):
                    reader.confined(root, "data/processed/seminar/out")

    def test_c10_strict_json_and_metadata_no_real_artifact_reads(self):
        for payload in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(ValueError):
                reader.strict_json(payload)
        # Pure reader/metric execution cannot open ANY filesystem payload.
        with mock.patch.object(Path, "open", side_effect=AssertionError("unexpected filesystem access")):
            meta, reports, near, _ = reader.read_synthetic(CONFIG)
            result = metrics.analyze(meta, reports, near, CONFIG)
        self.assertEqual(result["notice"], reader.NOTICE)


class ReportAndCliTests(unittest.TestCase):
    def test_c10_csv_eligibility_bounds_and_pair_provenance(self):
        metadata, reports, near = fixture()
        result = metrics.analyze(metadata, reports, near, CONFIG)
        rows = cli.report_rows("R4", result, CONFIG)
        row = next(r for r in rows if r["metric_id"] == "three_model_main/ALL/complementarity/qwen25->qwen3")
        self.assertEqual(row["planned_n"], 10)
        self.assertEqual(row["eligible_n"], 10)
        self.assertTrue(row["run_refs"])
        self.assertEqual(row["value"], 3 / 5)
        rows = cli.report_rows("R3", result, CONFIG)
        row = next(r for r in rows if r["metric_id"] == "completion_bounds/ALL/false_safe/upper")
        self.assertEqual((row["numerator"], row["denominator"], row["value"]), (3, 6, 0.5))
        invalid(reports["qwen3"][0])
        rows = cli.report_rows("R3", metrics.analyze(metadata, reports, near, CONFIG), CONFIG)
        row = next(r for r in rows if r["metric_id"] == "completion_bounds/ALL/false_safe/lower")
        self.assertEqual(row["status"], "BLOCKED")
        self.assertIsNone(row["value"])

    def test_c08_c09_outputs_blocks_roster_determinism(self):
        metadata, reports, near = fixture()
        first = metrics.analyze(metadata, reports, near, CONFIG)
        for c in ("T3763", "V3539"):
            self.assertEqual(len(first["R3"]["sensitivity"][c]["variants"]), 10)
            for variant in first["R3"]["sensitivity"][c]["variants"].values():
                for stratum in variant["strata"].values():
                    self.assertEqual(stratum["models"]["moondream2"]["status"], "N/A")
            for d in ["ALL", *CONFIG["domains"]]:
                self.assertEqual(first["R2"][c][d]["moondream2"]["status"], "N/A")
                self.assertEqual(first["R3"][c][d]["moondream2"]["status"], "N/A")
        self.assertEqual(len(first["R3"]["B01"]), 19)
        self.assertTrue(all(p["status"] == "BLOCKED" for p in first["R3"]["B01"]))
        self.assertEqual(first["R2"]["B02"]["status"], "N/A")
        self.assertEqual(first["R3"]["B05"]["status"], "BLOCKED")
        random.Random(2).shuffle(metadata)
        for rows in reports.values():
            random.Random(3).shuffle(rows)
        second = metrics.analyze(metadata, reports, near, CONFIG)
        self.assertEqual(reader.json_bytes(first), reader.json_bytes(second))

    def test_c10_cli_end_to_end_stdlib_receipt_csv_trace_overwrite_and_numeric_determinism(self):
        parent = ROOT / "data/processed/seminar"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            relative = Path(temp).relative_to(ROOT).as_posix()
            receipts = []
            for suffix in ("a", "b"):
                command = [sys.executable, "-S", "-B", "scripts/analyze_seminar.py", "--config", reader.CONFIG_PATH,
                           "--output-dir", relative + "/" + suffix]
                process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(process.returncode, 0, process.stderr)
                directory = Path(temp) / suffix
                receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
                receipts.append(receipt)
                self.assertEqual(len(receipt["outputs"]), 11)  # receipt is the twelfth file, no self hash
                self.assertEqual(receipt["authority"]["protocol_sha256"], reader.PROTOCOL_SHA)
                self.assertEqual(receipt["authority"]["config_sha256"], reader.CONFIG_SHA)
                self.assertEqual(len(receipt["inputs"]["units"]), 12)
                for name, digest in receipt["outputs"].items():
                    self.assertEqual(reader.sha256((directory / name).read_bytes()), digest)
                for report_id, name in cli.NAMES.items():
                    structured = json.loads((directory / (name + ".json")).read_text(encoding="utf-8"))
                    self.assertEqual(structured["notice"], reader.NOTICE)
                    with (directory / (name + ".csv")).open(encoding="utf-8", newline="") as stream:
                        csv_reader = csv.DictReader(stream)
                        self.assertEqual(csv_reader.fieldnames, cli.LONG_FIELDS)
                        rows = list(csv_reader)
                    self.assertEqual(len({r["row_id"] for r in rows}), len(rows))
                    self.assertEqual(len(rows), len(structured["rows"]))
                    self.assertTrue(all(r["notice"] == reader.NOTICE for r in rows))
                    self.assertTrue(all(r["reason"] for r in rows if r["value"] == ""))
                summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
                self.assertEqual(summary["status"], "PENDING_ANALYST_M4")
                self.assertIsNone(summary["scientific_conclusions"])
                self.assertIn("moondream2", summary["roster"])
                for trace in summary["trace"].values():
                    self.assertTrue(trace["input_refs"])
                    self.assertTrue(all(trace["row_ids"].values()))
                again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(again.returncode, 5)
                self.assertIn("overwrite", again.stderr)
                self.assertEqual(json.loads((directory / "receipt.json").read_text(encoding="utf-8")), receipt)
            self.assertEqual(receipts[0]["outputs"], receipts[1]["outputs"])

    def test_c10_cli_exit_codes_permission_integrity_data_io(self):
        args = ["--config", reader.CONFIG_PATH, "--output-dir", "data/processed/seminar/error-case"]
        for exception, code in ((reader.AuthorityError("no grant"), 3), (reader.IntegrityError("hash"), 4),
                                (ValueError("data"), 2), (OSError("disk"), 5)):
            with mock.patch.object(cli, "run", side_effect=exception), mock.patch("sys.stderr", new=io.StringIO()):
                self.assertEqual(cli.main(args), code)

    def test_c10_cli_read_fence_no_dataset_images_network_models_or_gpu(self):
        parent = ROOT / "data/processed/seminar"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            relative = Path(temp).relative_to(ROOT).as_posix() + "/fenced"
            code = r'''
import pathlib, sys, encodings.cp437, gzip
from scripts import analyze_seminar as cli
from safeshift.data import saved_reports as r
root = pathlib.Path.cwd()
output = (root / sys.argv[1]).resolve()
allowed = {r.CONFIG_PATH, r.PROTOCOL_PATH, r.AUTHORITY_PATH, "docs/research/DECISIONS.md",
 "docs/SOURCE_FEASIBILITY_RECEIPT_20261024.json", "safeshift/data/saved_reports.py",
 "safeshift/evaluation/seminar.py", "safeshift/evaluation/metrics.py", "safeshift/evaluation/sensitivity.py",
 "safeshift/data/schema.py", "safeshift/data/validation.py", "scripts/analyze_seminar.py"}
allowed = {(root / p).resolve() for p in allowed}
def audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes)):
        p = pathlib.Path(args[0]).resolve()
        if p not in allowed and not p.is_relative_to(output):
            raise AssertionError("unauthorized read/write: " + str(p))
    if event == "import" and args[0].split(".")[0] in {"torch", "transformers", "PIL", "numpy", "tensorflow"}:
        raise AssertionError("forbidden import")
    if event.startswith("socket."):
        raise AssertionError("network forbidden")
    if event == "subprocess.Popen":
        command = args[1]
        if not ((isinstance(command, str) and command.startswith("git -C ")) or
                (isinstance(command, (list, tuple)) and command[0] == "git")):
            raise AssertionError("only read-only Git evidence permitted")
sys.addaudithook(audit)
raise SystemExit(cli.main(["--config", r.CONFIG_PATH, "--output-dir", sys.argv[1]]))
'''
            process = subprocess.run([sys.executable, "-S", "-B", "-c", code, relative], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(process.returncode, 0, process.stderr)


if __name__ == "__main__":
    unittest.main()
