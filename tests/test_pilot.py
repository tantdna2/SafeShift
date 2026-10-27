"""Synthetic CPU tests only. No real image, checkpoint, dataset or GPU access."""
import copy
import ast
import base64
import hashlib
import json
import math
from pathlib import Path
import random
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
import zlib
import os

from safeshift.pilot import contract as c
from safeshift.pilot.artifacts import Store, export, import_archive, read, safe, sha, write
from safeshift.pilot.bootstrap import gpu_preflight, launch, recover_accounting
from safeshift.pilot.backend import provision
from safeshift.pilot.hnlo import branch, candidate_ids, hnlo, oracle, probe, replay, tokenizer_replay
from safeshift.pilot.manifest import (load_bundle, select_main, select_supplement,
                                     validate_master, validate_plan)
from safeshift.pilot.report import auc, combined, measurements, model_report, verdict
from safeshift.pilot.runner import execute, identity
from safeshift.pilot.runner import main as worker_main
from scripts.build_three_vlm_notebooks import ROOT, notebook
from scripts.prepare_three_vlm_pilot import prepare
from scripts.export_pilot_qwen_verified import export_labels, metadata_from_master
from scripts.report_three_vlm_pilot import combine_archives


class TextTokenizer:
    """Character tokenizer for mechanistic tests; never a production backend."""
    def encode(self, text, add_special_tokens=False):
        return list(map(ord, text))
    def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        return "".join(chr(i) for i in ids if not skip_special_tokens or i != 1000)


def raw(label="Level04"):
    tokenizer = TextTokenizer()
    text = '{"safety_level":"' + label + '"}'
    ids = tokenizer.encode(text)
    p = probe(tokenizer, "SYNTHETIC assistant\n", tokenizer.encode("SYNTHETIC assistant\n"))
    candidates = candidate_ids(p)
    steps = [{"step": i, "argmax": token, "all_finite": True,
              "raw_candidate_logits": {str(t): float(t - ord("1")) for t in candidates}}
             for i, token in enumerate(ids)]
    result = {"response": text, "generated_ids": ids, "token_probe": p, "steps": steps,
              "input_ids": tokenizer.encode("SYNTHETIC assistant\n"),
              "actual_logits_processors": [], "eos_token_ids": [1000], "capture_error": None}
    result["cpu_tokenizer_replay"] = tokenizer_replay(result, tokenizer)
    return result


def candidates(full=False):
    quotas = {"Level01": 490, "Level02": 251, "Level03": 8, "Level04": 3014} if full else c.QUOTAS
    rows = []
    for level, n in quotas.items():
        for i in range(n):
            domain = c.DOMAINS[i % len(c.DOMAINS)]
            sid = f"{domain}-{level}-Synthetic-{i:06d}-001"
            folder = "Normal" if level == "Level04" else "Anomaly"
            rows.append({"sample_id": sid, "domain": domain, "level": level, "split": "TRAIN",
                         "image_locator": f"DATA_PATH/train/Annotations/{folder}_data/{sid}/{sid}.jpg",
                         "image_sha256": hashlib.sha256(sid.encode()).hexdigest(),
                         "width": 100 + i % 17 * 200, "height": 100 + i % 7 * 150,
                         "group": hashlib.sha256(("group" + sid).encode()).hexdigest()})
    return rows


def plan(rows=None):
    rows = select_main(candidates()) if rows is None else rows
    return {"schema": "safeshift-three-vlm-manifest-v1", "split": "TRAIN", "mode": "PILOT", "seed": c.SEED,
            "master_sha256": c.MASTER_SHA, "data_revision": c.DATA_REVISION,
            "main": [{**r, "image": f"images/{i:06d}.jpg"} for i, r in enumerate(rows)], "supplement": [],
            "qwen_verified": [], "qwen_export_sha256": None, "supplement_availability": "NOT_RUN/BLOCKED"}


def grant(key="gemma", count=160):
    return {"schema": "safeshift-pilot-grant-v1", "mode": "PILOT", "model_key": key,
            "source_sha256": "a" * 64, "manifest_sha256": "b" * 64, "config_sha256": c.digest(c.settings(key)),
            "thresholds": c.THRESHOLDS, "max_initial_ids": count, "split": "TRAIN", "data_revision": c.DATA_REVISION,
            "master_sha256": c.MASTER_SHA, "run_id": "synthetic-only-run", "attempt_id": "synthetic-only-attempt",
            "max_seconds": 600, "retry_sample_ids": [],
            **{k: "SYNTHETIC_TEST_NOT_REAL_APPROVAL" for k in ("owner_approval_ref", "research_lead_review_ref",
                                                            "chatgpt_code_review_ref", "external_ledger_ref")},
            **{k: True for k in ("allow_train_images", "allow_folder_gt", "allow_model_download", "allow_gpu",
                                "allow_raw_export", "approve_thresholds")}}


def result(label="Level04", status="SUCCESS", h=None):
    return {"status": status, "label": label if status == "SUCCESS" else None,
            "attempts": 0 if status == "NOT_ATTEMPTED" else 1,
            "hnlo": h or {"status": "HNLO_UNVERIFIED", "hnlo": None}}


class ParserTests(unittest.TestCase):
    def test_exact_four_levels(self):
        for level in c.LEVELS:
            self.assertEqual(c.parse_label(' {"safety_level": "' + level + '"}\n'), level)

    def test_invalid_not_rescued(self):
        for text in ("Level01", '```json\n{"safety_level":"Level01"}\n```',
                     '{"safety_level":"Level01","explanation":"x"}', '{"safety_level":"Level01"} extra',
                     '{"safety_level":"Level01","safety_level":"Level04"}', '{"safety_level":"level01"}',
                     '{"safety_level":["Level01"]}', "null", "[]", '{"safety_level":"INVALID"}'):
            with self.subTest(text=text):
                self.assertIsNone(c.parse_label(text))


class HNLOTests(unittest.TestCase):
    def test_valid_common_multi_token_branch_replay(self):
        r = raw()
        h = replay(r, "Level04")
        self.assertEqual(h["status"], "HNLO_VALIDATED")
        self.assertEqual(h["replay_status"], "PASS")
        self.assertLess(h["hnlo"], 0)
        self.assertEqual(r["generated_ids"][h["decision_step"]], h["token_ids"]["Level04"])

    def test_oracle_extremes_and_shift_invariance(self):
        randomizer = random.Random(27102026)
        for vector in ([0., 0., 0., 0.], [-1000., -1001., -999., 1000.],
                       [1000., 1001., 999., -1000.], *[[randomizer.uniform(-1000, 1000) for _ in range(4)] for _ in range(100)]):
            self.assertAlmostEqual(hnlo(vector), oracle(vector), places=10)
            self.assertAlmostEqual(hnlo(vector), hnlo([x + 1e4 for x in vector]), places=9)
        self.assertAlmostEqual(hnlo([0., 0., 0., 0.]), math.log(3))
        self.assertAlmostEqual(hnlo([1e38] * 4), math.log(3))
        self.assertAlmostEqual(hnlo([1e38] * 4), oracle([1e38] * 4))

    def test_nonfinite_or_missing_logits(self):
        for vector in ([1., 2., 3.], [1., 2., float("nan"), 4.], [1., 2., 3., float("inf")]):
            with self.assertRaises(ValueError):
                hnlo(vector)

    def test_multi_branch_is_not_hnlo(self):
        seq = {l: [i, i + 10] for i, l in enumerate(c.LEVELS)}
        self.assertIsNone(branch(seq))
        seq = {l: [i] for i, l in enumerate(c.LEVELS)}
        seq["Level04"] = [0]
        self.assertIsNone(branch(seq))

    def test_nonempty_processors_and_changed_argmax_not_validated(self):
        r = raw()
        r["actual_logits_processors"] = ["SyntheticProcessor"]
        self.assertEqual(replay(r, "Level04")["status"], "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED")
        r = raw()
        r["steps"][0]["argmax"] += 1
        self.assertEqual(replay(r, "Level04")["status"], "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED")

    def test_incompatible_capture_failure_and_unaligned_distinct(self):
        r = raw()
        for m in r["token_probe"]["mappings"]:
            m["decision"] = None
        self.assertEqual(replay(r, "Level04")["status"], "HNLO_INCOMPATIBLE")
        r["capture_error"] = "SYNTHETIC observer error"
        self.assertEqual(replay(r, "Level04")["status"], "HNLO_TECHNICAL_FAILURE")
        r = raw()
        r["generated_ids"] = [ord(" ")] + r["generated_ids"]
        r["steps"].insert(0, {"argmax": ord(" "), "all_finite": True})
        self.assertEqual(replay(r, "Level04")["status"], "RAW_LOGITS_AVAILABLE_BUT_UNALIGNED")

    def test_tampered_mapping_and_missing_step(self):
        r = raw()
        r["token_probe"]["mappings"][0]["decision"]["step"] += 1
        self.assertEqual(replay(r, "Level04")["status"], "HNLO_TECHNICAL_FAILURE")
        r = raw()
        r["steps"].pop()
        self.assertEqual(replay(r, "Level04")["status"], "HNLO_TECHNICAL_FAILURE")

    def test_independent_decoder_mismatch(self):
        r = raw()
        r["generated_ids"][0] += 1
        with self.assertRaisesRegex(ValueError, "DECODE_MISMATCH"):
            tokenizer_replay(r, TextTokenizer())
        r = raw()
        r.pop("cpu_tokenizer_replay")
        self.assertNotEqual(replay(r, "Level04")["status"], "HNLO_VALIDATED")


class ManifestTests(unittest.TestCase):
    def test_qwen_projection_matches_existing_saved_verifier_contract(self):
        from safeshift.evaluation.sensitivity import join_reports
        source = candidates()[:2]
        metadata = list(metadata_from_master(source).values())
        saved = [{"sample_id": r["sample_id"], "true_level": r["level"], "domain": r["domain"],
                  "status": "SUCCESS", "generated_label": "Level04", "pa3_score": 0.0} for r in source]
        indexed, _ = join_reports(metadata, {"qwen3": saved})
        self.assertEqual(len(indexed), 2)

    def test_bundle_checksums_full_membership_and_selection(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            pool = candidates(True)
            for r in pool:
                r["image_sha256"] = hashlib.sha256(b"SYNTHETIC_NOT_IMAGE").hexdigest()
            master = {"schema": "pa3-full-train-v1", "split": "TRAIN", "samples": pool}
            write(root / "master_manifest.json", master)
            master_hash = sha(root / "master_manifest.json")
            p = plan(select_main(pool))
            p["master_sha256"] = master_hash
            p["dimension_inventory_sha256"] = c.digest(pool)
            write(root / "dimension_inventory.json", pool)
            write(root / "pilot_manifest.json", p)
            write(root / "bundle.json", {"schema": "safeshift-private-input-v1", "manifest_sha256": c.digest(p)})
            for row in p["main"]:
                path = root / row["image"]
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b"SYNTHETIC_NOT_IMAGE")
            with patch("safeshift.pilot.manifest.MASTER_SHA", master_hash):
                actual, rows = load_bundle(root)
                self.assertEqual(len(rows), 160)
                self.assertEqual(actual, p)
                (root / p["main"][0]["image"]).write_bytes(b"SYNTHETIC_CORRUPTION")
                with self.assertRaisesRegex(ValueError, "IMAGE_CHECKSUM"):
                    load_bundle(root)

    def test_deterministic_exact_160_all_domains_and_largest(self):
        pool = candidates(True)
        picked = select_main(pool)
        self.assertEqual(picked, select_main(list(reversed(pool))))
        self.assertEqual(len(picked), 160)
        self.assertEqual(len({r["sample_id"] for r in picked}), 160)
        self.assertEqual({r["domain"] for r in picked}, set(c.DOMAINS))
        for level, n in c.QUOTAS.items():
            self.assertEqual(sum(r["level"] == level for r in picked), n)
            for domain in c.DOMAINS:
                subset = [r for r in picked if r["level"] == level and r["domain"] == domain]
                if subset:
                    largest_area = max(r["width"] * r["height"] for r in pool if r["level"] == level and r["domain"] == domain)
                    self.assertEqual(max(r["width"] * r["height"] for r in subset), largest_area)

    def test_no_new_model_result_affects_selection(self):
        pool = candidates()
        before = select_main(pool)
        after = select_main([{**r, "gemma": "Level04", "phi": random.random()} for r in pool])
        self.assertEqual([r["sample_id"] for r in before], [r["sample_id"] for r in after])

    def test_shortage_test_and_duplicate_block(self):
        pool = candidates()
        with self.assertRaisesRegex(ValueError, "INSUFFICIENT"):
            select_main(pool[1:])
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            select_main(pool + pool[:1])
        pool[0]["split"] = "TEST"
        with self.assertRaises(ValueError):
            select_main(pool)

    def test_master_original_count_labels_and_train_only(self):
        rows = candidates(True)
        value = {"schema": "pa3-full-train-v1", "split": "TRAIN", "samples": rows}
        self.assertEqual(len(validate_master(value)), 3763)
        value["split"] = "TEST"
        with self.assertRaises(ValueError):
            validate_master(value)
        value["split"] = "TRAIN"
        rows[0]["image_locator"] = rows[0]["image_locator"].replace("/train/", "/test/")
        with self.assertRaises(ValueError):
            validate_master(value)

    def test_exact_plan_quota_and_path_id_binding(self):
        p = plan()
        self.assertEqual(len(validate_plan(p, candidates())), 160)
        p["main"] = p["main"][:-1]
        with self.assertRaisesRegex(ValueError, "EXACT_160"):
            validate_plan(p, candidates())
        p = plan()
        p["main"][0]["image"] = "../test.jpg"
        with self.assertRaises(ValueError):
            validate_plan(p, candidates())

    def test_qwen_original_provenance_and_no_primary_overlap(self):
        pool = candidates(True)
        verified = [{"sample_id": r["sample_id"], "ground_truth": r["level"], "image_sha256": r["image_sha256"],
                     "predicted_label": "Level04", "status": "SUCCESS", "verified": True,
                     "cohort": "QWEN3_V4_ORIGINAL", "verification_ref": "SYNTHETIC",
                     "source_artifact_sha256": "c" * 64} for r in pool[:40]]
        chosen = select_supplement(verified, pool, {verified[0]["sample_id"]})
        self.assertEqual(len(chosen), 20)
        self.assertNotIn(verified[0], chosen)
        for bad in ("RECOVERY224", "V4_PLUS_RECOVERY"):
            verified[0]["cohort"] = bad
            with self.assertRaises(ValueError):
                select_supplement(verified, pool, set())
        verified[0]["cohort"] = "QWEN3_V4_ORIGINAL"
        self.assertEqual(len(select_supplement(verified[:3], pool, set())), 3)

    def test_more_than_180_and_wrong_full_membership(self):
        p = plan()
        p["supplement"] = p["main"][:21]
        with self.assertRaises(ValueError):
            validate_plan(p, candidates())
        p = plan()
        p["mode"] = "FULL_TRAIN"
        with self.assertRaises(ValueError):
            validate_plan(p, candidates(), "FULL_TRAIN")


class AuthorityTests(unittest.TestCase):
    def authorize(self, g, mode="PILOT", count=160, parent=None):
        return c.authorize(g, model="gemma", mode=mode, source_hash="a" * 64,
                           manifest_hash="b" * 64, count=count, parent=parent)

    def test_null_and_old_grants_block(self):
        for g in (None, {}, {"grant": {}}, {"schema": "old-v4-authority"}):
            with self.assertRaises(PermissionError):
                self.authorize(g)

    def test_exact_scope_and_thresholds(self):
        self.authorize(grant())
        for field, value in (("model_key", "phi"), ("source_sha256", "c" * 64), ("split", "TEST"),
                             ("allow_gpu", False), ("chatgpt_code_review_ref", ""),
                             ("thresholds", {}), ("max_initial_ids", 161)):
            g = grant()
            g[field] = value
            with self.subTest(field=field), self.assertRaises(PermissionError):
                self.authorize(g)

    def test_full_cannot_activate_from_pilot(self):
        g = grant(count=3763)
        g["mode"] = "FULL_TRAIN"
        with self.assertRaises(PermissionError):
            self.authorize(g, count=3763)
        with self.assertRaises(PermissionError):
            self.authorize(g, "FULL_TRAIN", count=3763)
        g.update(full_train_explicit=True, pilot_review_ref="SYNTHETIC", pilot_recommendation="GO_FULL_TRAIN_RECOMMENDED",
                 hnlo_disposition="CLASSIFICATION_ONLY_ACCEPTED")
        self.authorize(g, "FULL_TRAIN", count=3763)

    def test_resume_and_retry_have_separate_permissions(self):
        g = grant()
        with self.assertRaises(PermissionError):
            self.authorize(g, parent="c" * 64)
        g.update(resume_parent_archive_sha256="c" * 64, resume_approval_ref="SYNTHETIC")
        self.authorize(g, parent="c" * 64)
        g["retry_sample_ids"] = ["synthetic"]
        with self.assertRaises(PermissionError):
            self.authorize(g, parent="c" * 64)

    def test_prepare_and_qwen_deny_before_data_read(self):
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "grant.json"
            write(g, {})
            with patch("subprocess.check_output", side_effect=AssertionError("DATA READ")):
                with self.assertRaises(PermissionError):
                    prepare(g, "data/raw/fake", "data/processed/never")
                with self.assertRaises(PermissionError):
                    export_labels(g, "data/processed/fake", "data/processed/fake.zip", "data/processed/never")

    def test_notebook_no_grant_never_calls_gpu_or_installer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inputs, work = root / "input", root / "work"
            (inputs / "private").mkdir(parents=True)
            work.mkdir()
            write(inputs / "private/grant_gemma.json", None)
            with patch("subprocess.run", side_effect=AssertionError("INSTALL/GPU")), patch("subprocess.check_output", side_effect=AssertionError("GPU")):
                out = launch("gemma", c.source_digest(ROOT), ROOT, inputs, work)
            self.assertEqual(read(out / "supervisor_failure.json")["stage"], "authority")
            self.assertFalse((out / "run").exists())


class ArtifactAndEngineTests(unittest.TestCase):
    def test_one_explicit_retry_preserves_attempt_count_and_old_raw(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = plan()
            rows = p["main"][:1]
            sid = rows[0]["sample_id"]
            first = Store(root / "one", {"synthetic": True})
            first.start(0, {"attempts": 1})
            first.result(0, {"status": "TECHNICAL_ERROR", "attempts": 1, "native_calls": 1})
            second = Store(root / "two", {"synthetic": True}, first.root)
            class RetryBackend:
                environment = {"SYNTHETIC": True}
                def generate(self, path, directory):
                    return raw()
            g = {**grant(), "retry_sample_ids": [sid], "retry_approval_ref": "SYNTHETIC"}
            results, _ = execute(second, rows, RetryBackend, g, "gemma", p)
            self.assertEqual(results[sid]["attempts"], 2)
            self.assertEqual(results[sid]["native_calls"], 2)
            self.assertEqual(read(first.root / "samples/000000/result.json")["status"], "TECHNICAL_ERROR")

    def test_time_limit_never_starts_next_call(self):
        with tempfile.TemporaryDirectory() as d:
            p = plan()
            store = Store(Path(d) / "run", {"synthetic": True})
            class Unused:
                environment = {"SYNTHETIC": True}
                def generate(self, *args):
                    raise AssertionError("NO_CALL_ALLOWED")
            results, blocked = execute(store, p["main"], Unused, grant(), "gemma", p, time_budget=0)
            self.assertTrue(blocked)
            self.assertTrue(all(r["attempts"] == 0 for r in results.values()))

    def test_raw_writer_error_keeps_tail_not_attempted(self):
        with tempfile.TemporaryDirectory() as d:
            p = plan()
            store = Store(Path(d) / "run", {"synthetic": True})
            class SyntheticBackend:
                environment = {"SYNTHETIC": True}
                def generate(self, *args):
                    return raw()
            with patch.object(store, "raw", side_effect=OSError("SYNTHETIC_DISK_FULL")):
                results, blocked = execute(store, p["main"], SyntheticBackend, grant(), "gemma", p)
            self.assertTrue(blocked)
            self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 159)
            self.assertFalse(list(store.root.rglob("raw.json")))

    def test_exclusive_raw_and_archive_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            store = Store(root / "run", {"synthetic": True})
            store.raw(0, raw())
            with self.assertRaises(FileExistsError):
                store.raw(0, raw("Level01"))
            archive = root / "out.zip"
            export(store.root, archive)
            recovered = import_archive(archive, root / "recovered")
            self.assertEqual(read(recovered / "samples/000000/raw.json"), raw())
            with self.assertRaises(FileExistsError):
                import_archive(archive, recovered)

    def test_archive_path_and_checksum_attack(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ("../escape", "/absolute", "C:/machine", "a\\b"):
                archive = root / (hashlib.sha256(name.encode()).hexdigest() + ".zip")
                with zipfile.ZipFile(archive, "x") as z:
                    z.writestr(name, "SYNTHETIC")
                with self.assertRaises(ValueError):
                    import_archive(archive, root / "never")

    def test_safe_path_rejects_alias(self):
        with tempfile.TemporaryDirectory() as d:
            for p in ("../test", "DATA_PATH/test/../train/a", "C:/test", "/test"):
                with self.assertRaises(ValueError):
                    safe(d, p)

    def test_raw_durable_before_parser_and_hnlo_does_not_fail_classification(self):
        with tempfile.TemporaryDirectory() as d:
            p = plan()
            rows = p["main"][:12]
            store = Store(Path(d) / "run", {"synthetic": True})
            class SyntheticBackend:
                environment = {"SYNTHETIC": True}
                def generate(self, path, directory):
                    r = raw()
                    r["capture_error"] = "SYNTHETIC HNLO failure"
                    return r
            native_parse = c.parse_label
            def observed(text):
                self.assertTrue(list(store.root.rglob("raw.json")))
                return native_parse(text)
            with patch("safeshift.pilot.runner.parse_label", observed):
                results, blocked = execute(store, rows, SyntheticBackend, grant(), "gemma", p)
            self.assertFalse(blocked)
            self.assertEqual(sum(r["status"] == "SUCCESS" for r in results.values()), 12)
            self.assertTrue(all(r["hnlo"]["status"] == "HNLO_TECHNICAL_FAILURE" for r in results.values()))
            self.assertTrue((store.root / "early12.json").exists())

    def test_failure_stops_and_tail_is_not_attempted(self):
        with tempfile.TemporaryDirectory() as d:
            p = plan()
            store = Store(Path(d) / "run", {"synthetic": True})
            class Failing:
                environment = {"SYNTHETIC": True}
                stage = "generation"
                def generate(self, path, directory):
                    raise RuntimeError("SYNTHETIC CUDA out of memory")
            results, blocked = execute(store, p["main"], Failing, grant(), "gemma", p)
            self.assertTrue(blocked)
            self.assertEqual(sum(r["status"] == "NOT_ATTEMPTED" for r in results.values()), 159)
            self.assertEqual(next(iter(results.values()))["error_category"], "OOM")
            self.assertEqual(model_report(p, results, blocked)["primary"]["planned"], 160)

    def test_resume_skip_success_and_reject_changed_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = plan()
            rows = p["main"][:1]
            ident = identity("gemma", p, rows, "a" * 64, "synthetic")
            first = Store(root / "one", ident)
            class SyntheticBackend:
                environment = {"SYNTHETIC": True}
                def generate(self, path, directory):
                    return raw()
            execute(first, rows, SyntheticBackend, grant(), "gemma", p)
            second = Store(root / "two", ident, first.root)
            with patch.object(SyntheticBackend, "generate", side_effect=AssertionError("RERUN")):
                results, _ = execute(second, rows, SyntheticBackend, grant(), "gemma", p)
            self.assertEqual(next(iter(results.values()))["attempts"], 1)
            with self.assertRaisesRegex(ValueError, "MISMATCH"):
                Store(root / "three", {**ident, "config_sha256": "c" * 64}, first.root)

    def test_interrupted_attempt_not_retried_without_grant(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = plan()
            first = Store(root / "one", {"synthetic": True})
            first.start(0, {"attempts": 1})
            second = Store(root / "two", {"synthetic": True}, first.root)
            results, _ = execute(second, p["main"][:1], lambda: (_ for _ in ()).throw(AssertionError("RERUN")), grant(), "gemma", p)
            self.assertEqual(next(iter(results.values()))["status"], "TECHNICAL_ERROR")


class ReportTests(unittest.TestCase):
    def test_model_load_failure_not_quality_pass(self):
        p = plan()
        results = {r["sample_id"]: result(status="NOT_ATTEMPTED") for r in p["main"]}
        failure = {"category": "OOM", "stage": "model_load", "message": "SYNTHETIC"}
        v = model_report(p, results, True, failure)["conclusion"]
        self.assertEqual(v["classification_status"], "TECHNICAL_FAIL")
        self.assertEqual(v["recommendation"], "NO_GO_FULL_TRAIN")
        failure["category"] = "ACCESS"
        self.assertEqual(model_report(p, results, True, failure)["conclusion"]["recommendation"], "INCONCLUSIVE/BLOCKED")

    def test_combine_blocked_archive_keeps_every_planned_id(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            evidence = root / "evidence"
            p = plan()
            write(evidence / "pilot_manifest.json", p)
            write(evidence / "supervisor_failure.json", {"category": "LIBRARY", "stage": "software", "message": "SYNTHETIC"})
            archive = root / "blocked.zip"
            export(evidence, archive)
            with patch("scripts.report_three_vlm_pilot.processed", return_value=root / "report"):
                reports = combine_archives({"gemma": archive}, "data/processed/SYNTHETIC")
            self.assertEqual(reports["gemma"]["primary"]["NOT_ATTEMPTED"], 160)
            self.assertEqual(len(read(root / "report/comparison.json")), 160)
            self.assertEqual(reports["gemma"]["conclusion"]["classification_status"], "TECHNICAL_FAIL")

    def test_all_statuses_accounted_and_invalid_in_recall(self):
        p = plan()
        results = {r["sample_id"]: result(r["level"]) for r in p["main"]}
        for row, status in zip(p["main"][:3], ("INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED")):
            results[row["sample_id"]] = result(status=status)
        m = model_report(p, results)["primary"]
        self.assertEqual((m["planned"], m["attempted"], m["SUCCESS"], m["INVALID"], m["ERROR"], m["NOT_ATTEMPTED"]), (160, 159, 157, 1, 1, 1))
        self.assertEqual(sum(sum(v.values()) for v in m["confusion_4x5"].values()), 160)
        for row in p["main"][:3]:
            self.assertLess(m["per_class"][row["level"]]["recall"], 1)

    def test_empty_and_all_normal_or_anomaly_red_flags(self):
        self.assertIsNone(measurements([], {})["accuracy_planned"])
        p = plan()
        for label in ("Level01", "Level04"):
            results = {r["sample_id"]: result(label) for r in p["main"]}
            v = model_report(p, results)["conclusion"]
            self.assertTrue(v["quality_flags"])
            self.assertEqual(v["recommendation"], "NO_GO_FULL_TRAIN")

    def test_exact_shared_ids_and_no_missing_rows(self):
        p = plan()
        results = {r["sample_id"]: result() for r in p["main"]}
        table = combined(p, {"gemma": results})
        self.assertEqual(len(table), 160)
        self.assertTrue(all(r["phi"] == "NOT_ATTEMPTED" and r["qwen3_label_if_verified"] is None for r in table))
        results.pop(next(iter(results)))
        with self.assertRaises(ValueError):
            combined(p, {"gemma": results})

    def test_auc_against_pair_oracle_and_ties(self):
        rng = random.Random(42)
        for _ in range(20):
            data = [(bool(rng.randrange(2)), rng.randrange(5)) for _ in range(30)]
            positive = [s for y, s in data if y]
            negative = [s for y, s in data if not y]
            expected = sum((p > n) + .5 * (p == n) for p in positive for n in negative) / (len(positive) * len(negative))
            self.assertAlmostEqual(auc(data), expected)
        self.assertIsNone(auc([(True, 1.)]))


class NotebookAndPreflightTests(unittest.TestCase):
    def test_supervised_worker_accepts_precreated_evidence_root(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            grant_file = root / "grant.json"
            write(grant_file, grant())
            args = ["runner", "--repo", str(ROOT), "--bundle", "SYNTHETIC", "--grant", str(grant_file),
                    "--source-hash", "a" * 64, "--output", str(root), "--mode", "PILOT"]
            with patch.dict(os.environ, {"SAFESHIFT_SUPERVISED": "1"}), patch("sys.argv", args), patch("safeshift.pilot.runner.run") as run:
                worker_main()
            run.assert_called_once()

    def test_unreviewed_remote_code_rejected_before_download_or_execution(self):
        spec = c.MODELS["phi"]
        info = SimpleNamespace(sha=spec["revision"], siblings=[SimpleNamespace(rfilename="unreviewed.py")])
        downloader = unittest.mock.Mock(side_effect=AssertionError("DOWNLOAD_NOT_ALLOWED"))
        api = SimpleNamespace(model_info=lambda *a, **k: info)
        module = SimpleNamespace(HfApi=lambda: api, snapshot_download=downloader)
        with patch.dict("sys.modules", {"huggingface_hub": module}):
            with self.assertRaisesRegex(ValueError, "UNREVIEWED_EXECUTABLE"):
                provision(ROOT, "phi", "SYNTHETIC_NEVER_USED")
        downloader.assert_not_called()

    def test_locked_phi_code_checksums_before_custom_import(self):
        spec = c.MODELS["phi"]
        lock = read(ROOT / "configs/pilot/model_source_lock.json")["phi"]
        with tempfile.TemporaryDirectory() as d:
            snapshot = Path(d) / "snapshots" / spec["revision"]
            snapshot.mkdir(parents=True)
            siblings = [SimpleNamespace(rfilename=n) for n in lock["files"]]
            for n in lock["files"]:
                (snapshot / n).write_bytes(b"SYNTHETIC_SOURCE_TAMPER")
            info = SimpleNamespace(sha=spec["revision"], siblings=siblings)
            api = SimpleNamespace(model_info=lambda *a, **k: info)
            module = SimpleNamespace(HfApi=lambda: api, snapshot_download=lambda *a, **k: str(snapshot))
            with patch.dict("sys.modules", {"huggingface_hub": module}):
                with self.assertRaisesRegex(ValueError, "REVIEWED_SOURCE_CHECKSUM"):
                    provision(ROOT, "phi", "SYNTHETIC")

    def test_notebooks_reproduce_share_payload_pilot_only_no_outputs(self):
        hashes = set()
        for key in c.MODELS:
            path = ROOT / f"notebooks/SafeShift_TRAIN_PILOT_{key}.ipynb"
            actual = json.loads(path.read_bytes())
            self.assertEqual(actual, notebook(key))
            hashes.add(actual["metadata"]["safeshift"]["source_sha256"])
            code = "".join(actual["cells"][1]["source"])
            compile(code, str(path), "exec")
            encoded = next(n.args[0].value for n in ast.walk(ast.parse(code))
                           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "b64decode")
            payload = json.loads(zlib.decompress(base64.b64decode(encoded)))
            self.assertEqual(c.digest({p: hashlib.sha256(t.encode()).hexdigest() for p, t in payload.items()}),
                             actual["metadata"]["safeshift"]["source_sha256"])
            self.assertTrue(all((ROOT / p).read_bytes() == t.encode() for p, t in payload.items()))
            self.assertIn('mode="PILOT"', code)
            self.assertEqual(actual["cells"][1]["outputs"], [])
        self.assertEqual(len(hashes), 1)

    def test_gpu_t4_not_pooled_memory(self):
        valid = "Tesla T4, 15360, 14800, 550.90.07\nTesla T4, 15360, 14800, 550.90.07\n"
        with patch("subprocess.check_output", return_value=valid):
            self.assertIn("GPU1 unused", gpu_preflight()["placement"])
        for text in ("Tesla T4, 15360, 14800, 550.90.07\n", valid.replace("T4", "P100"), valid.replace("14800", "8000")):
            with patch("subprocess.check_output", return_value=text), self.assertRaises(RuntimeError):
                gpu_preflight()


if __name__ == "__main__":
    unittest.main()
