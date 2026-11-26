"""Issue167: synthetic bytes only; no real pictures, weights, GPU or private reads."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.candidates import fulltrain as f, fulltrain_run as r
from safeshift.candidates.fulltrain_preflight import inspect_receipts, CHECKS
from safeshift.candidates.train_history import lease_key, members
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import digest


def spec(key="minicpm4"):
    return {"model_key": key, "model_id": "synthetic/" + key, "hnlo_policy": "LABEL_ONLY",
            **{n: "a" * (40 if n == "model_revision" else 64) for n in f.IDENTITY_FIELDS}}


def make_plan(history=None, action="initial", series="series1", run="run1", key="minicpm4", cap=3, repair=None, identity=None):
    c = r.synthetic_cohort()
    history = [] if history is None else history
    return f.plan(c, digest(c), identity or spec(key), history, digest(history), action=action,
                  series_id=series, run_id=run, attempt_id=run + "-attempt", max_calls=cap, max_seconds=60, repair=repair)


def history_record(status, i):
    import hashlib
    row = {"sample_id": f"synthetic-{i:04d}", "image_sha256": hashlib.sha256(r.synthetic_bytes(i)).hexdigest()}
    return {"sample_id": row["sample_id"], "image_sha256": row["image_sha256"], "status": status,
            "label": "Level04" if status == "SUCCESS" else None,
            "native_calls": int(status != "NOT_ATTEMPTED"), "attempts": int(status != "NOT_ATTEMPTED"),
            **({"raw_sha256": "f" * 64} if status in ("SUCCESS", "INVALID") else {})}


def history_fixture(statuses, key="minicpm4"):
    return [{"run_id": "original", "attempt_id": "original-attempt", "series_id": "series1", "identity": spec(key),
             "cohort_sha256": digest(r.synthetic_cohort()), "parent_history_sha256": digest([]), "action": "initial",
             "repair": None, "records": [history_record(s, i) for i, s in enumerate(statuses)], "evidence_sha256": "b" * 64}]


class Scripted:
    # Test-only fake never imported by package/CLI/notebooks.
    environment = {"scope": "CPU_SYNTHETIC_ONLY"}
    stage = "generation"
    def __init__(self, outputs):
        self.outputs, self.calls = iter(outputs), 0
    def generate(self, image, sample):
        self.calls += 1
        write(sample / "native_call.json", {"call": self.calls})
        value = next(self.outputs)
        if isinstance(value, BaseException):
            raise value
        return {"response": value, "generated_ids": [1], "raw_nonfinite": False}


class FulltrainPlanTests(unittest.TestCase):
    def test_exact_3763_for_all_candidates_and_bounded_schedule(self):
        plans = {}
        for key in f.MODELS:
            p = make_plan(key=key, cap=3763)
            self.assertEqual(p["scheduled_ordinals"], list(range(3763)))
            self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
            self.assertFalse(p["pooling_allowed"])
            plans[key] = r.synthetic_cohort()
        self.assertEqual(f.same_cohort(plans), digest(r.synthetic_cohort()))
        p = make_plan(cap=160)
        self.assertEqual(len(p["deferred_ordinals"]), 3603)

    def test_manifest_negative_count_order_id_hash_split_gt(self):
        for mutate in (lambda x: x["samples"].pop(),
                       lambda x: x["samples"][1].update(sample_id=x["samples"][0]["sample_id"]),
                       lambda x: x["samples"].reverse(),
                       lambda x: x["samples"][0].update(image_sha256="bad"),
                       lambda x: x.update(split="TEST"),
                       lambda x: x["samples"][0].update(level="Level04")):
            c = r.synthetic_cohort()
            mutate(c)
            with self.assertRaises(ValueError):
                f.validate_cohort(c, digest(c))
        with self.assertRaisesRegex(ValueError, "COHORT_CHECKSUM"):
            f.validate_cohort(r.synthetic_cohort(), "b" * 64)
        with self.assertRaisesRegex(ValueError, "ORIGINAL_MASTER"):
            f.cohort(b'{"split":"TRAIN"}')

    def test_cross_model_reorder_even_with_recomputed_hash(self):
        c = {key: r.synthetic_cohort() for key in f.MODELS}
        a, b = c["internvl35"]["samples"][:2]
        a["sample_id"], b["sample_id"] = b["sample_id"], a["sample_id"]
        with self.assertRaisesRegex(ValueError, "CROSS_MODEL"):
            f.same_cohort(c)

    def test_resume_repairs_neither_invalid_nor_consumed_error(self):
        h = history_fixture(["SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED"])
        p = make_plan(h, "resume")
        self.assertEqual(p["scheduled_ordinals"], [3, 4, 5])
        self.assertEqual(p["samples"][1]["cause"], "INVALID")
        self.assertTrue(p["samples"][1]["remedy"])
        self.assertEqual(p["counts"], {"SUCCESS": 1, "INVALID": 1, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3760})

    def test_targeted_repair_requires_fix_regression_and_exact_failed_record(self):
        h = history_fixture(["SUCCESS", "INVALID", "TECHNICAL_ERROR"])
        fix = {"targets": {v["sample_id"]: digest(v) for v in h[0]["records"][1:]},
               "fix_sha256": "d" * 64, "regression_sha256": "e" * 64, "diagnosis": "synthetic transport bug"}
        p = make_plan(h, "repair", repair=fix)
        self.assertEqual(p["scheduled_ordinals"], [1, 2])
        for mutation in (lambda v: v.pop("regression_sha256"), lambda v: v.update(diagnosis=""),
                         lambda v: v["targets"].update({h[0]["records"][0]["sample_id"]: digest(h[0]["records"][0])}),
                         lambda v: v["targets"].update({h[0]["records"][1]["sample_id"]: "b" * 64})):
            bad = copy.deepcopy(fix)
            mutation(bad)
            with self.assertRaises(ValueError):
                make_plan(h, "repair", repair=bad)

    def test_rerun_and_changed_semantics_never_pool(self):
        h = history_fixture(["SUCCESS", "INVALID"])
        for field in f.IDENTITY_FIELDS:
            changed = spec()
            changed[field] = "b" * (40 if field == "model_revision" else 64)
            with self.assertRaisesRegex(ValueError, "NEW_VERSION"):
                make_plan(h, "resume", identity=changed)
            p = make_plan(h, "rerun", series="new-series", identity=changed)
            self.assertEqual(p["scheduled_ordinals"], [0, 1, 2])
            self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
            self.assertEqual(len(p["samples"][0]["lineage"]), 1)
        with self.assertRaisesRegex(ValueError, "NEW_SERIES"):
            make_plan(h, "rerun")

    def test_duplicate_history_missing_ancestor_and_input_mismatch(self):
        h = history_fixture(["SUCCESS"])
        mutations = [lambda x: x.append(copy.deepcopy(x[0])),
                     lambda x: x[0].update(parent_history_sha256="a" * 64),
                     lambda x: x[0]["records"].append(copy.deepcopy(x[0]["records"][0])),
                     lambda x: x[0]["records"][0].update(image_sha256="c" * 64),
                     lambda x: x[0]["records"][0].update(raw_sha256=None)]
        for mutation in mutations:
            bad = copy.deepcopy(h)
            mutation(bad)
            with self.assertRaises(ValueError):
                make_plan(bad, "resume")

    def test_history_duplicate_call_cannot_hide_behind_new_attempt(self):
        h = history_fixture(["INVALID"])
        again = copy.deepcopy(h[0])
        again.update(run_id="duplicate", attempt_id="duplicate", action="resume", parent_history_sha256=digest(h))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CONSUMED"):
            make_plan([*h, again], "resume")

    def test_cause_taxonomy_keeps_unknown(self):
        for error, expected in [({"category": "OOM"}, "GPU_OOM"), ({"type": "TimeoutError"}, "TIMEOUT"),
                                ({"stage": "model_load"}, "LOAD_ENVIRONMENT"), ({"stage": "preprocessing"}, "PIPELINE"), ({}, "UNKNOWN")]:
            self.assertEqual(f.cause({"status": "TECHNICAL_ERROR", "error": error}), expected)

    def test_no_authority_flags_enable_launch_or_hnlo(self):
        for key in f.MODELS:
            with self.assertRaisesRegex(PermissionError, "CPU_ONLY"):
                f.launch(key, approved=True, allow_gpu=True, grant={"O6": "APPROVED"})
        wrong = spec()
        wrong["hnlo_policy"] = "LOCKED_EXISTING_METHOD"
        with self.assertRaisesRegex(ValueError, "MINICPM_LABEL_ONLY"):
            f.identity(wrong)

    def test_invalid_caps_and_duplicate_run_are_rejected(self):
        for cap in (True, 0, 3764):
            with self.assertRaises(ValueError):
                make_plan(cap=cap)
        with self.assertRaisesRegex(ValueError, "ATTEMPT_ALREADY"):
            make_plan(history_fixture(["SUCCESS"]), "resume", run="original")

    def test_all_3763_consumed_is_noop_but_invalid_still_has_repair_work(self):
        for key in f.MODELS:
            h = history_fixture(["SUCCESS"] * 3762 + ["INVALID"], key)
            p = make_plan(h, "resume", key=key)
            self.assertEqual(p["scheduled_ordinals"], [])
            self.assertEqual(p["counts"], {"SUCCESS": 3762, "INVALID": 1})
            self.assertIsNotNone(p["samples"][-1]["remedy"])
            h[0]["records"].pop()
            tail = make_plan(h, "resume", key=key)
            self.assertEqual(tail["scheduled_ordinals"], [3762])


class FulltrainJournalTests(unittest.TestCase):
    def fixture(self, root, ordinals):
        bundle = root / "inputs"
        bundle.mkdir(exist_ok=True)
        for i in ordinals:
            path = bundle / f"{i:06d}.bin"
            if not path.exists():
                path.write_bytes(r.synthetic_bytes(i))
        return bundle

    def run_plan(self, root, p, h, outputs):
        bundle = self.fixture(root, p["scheduled_ordinals"])
        backend = Scripted(outputs)
        directory = r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, h, lambda: backend)
        return directory, backend, r.recover(directory, r.synthetic_cohort(), digest(p))

    def test_raw_before_parse_stop_resume_repair_rerun_for_three_models(self):
        for key in f.MODELS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                p = make_plan(key=key)
                out, backend, first = self.run_plan(root, p, [], ['{"safety_level":"Level04"}', 'prose Level01', RuntimeError("synthetic out of memory")])
                self.assertEqual(backend.calls, 3)
                self.assertEqual([v["status"] for v in first["records"]], ["SUCCESS", "INVALID", "TECHNICAL_ERROR"])
                self.assertEqual(f.cause(first["records"][2]), "GPU_OOM")
                original_hashes = members(out)
                h = [first]
                p2 = make_plan(h, "resume", run="run2", key=key, cap=1)
                self.assertEqual(p2["scheduled_ordinals"], [3])
                out2, _, second = self.run_plan(root, p2, h, ['{"safety_level":"Level02"}'])
                h.append(second)
                fix = {"targets": {v["sample_id"]: digest(v) for v in first["records"][1:]},
                       "fix_sha256": "d"*64, "regression_sha256": "e"*64, "diagnosis": "synthetic transport fix"}
                p3 = make_plan(h, "repair", run="run3", key=key, repair=fix)
                _, _, third = self.run_plan(root, p3, h, ['{"safety_level":"Level01"}', 'still invalid'])
                h.append(third)
                p4 = make_plan(h, "resume", run="run4", key=key)
                self.assertEqual(p4["scheduled_ordinals"], [4, 5, 6])
                self.assertEqual(p4["samples"][2]["status"], "INVALID")
                self.assertEqual(len(p4["samples"][1]["lineage"]), 2)
                self.assertEqual(members(out), original_hashes)
                rerun = make_plan(h, "rerun", series="new-series", run="run5", key=key)
                self.assertEqual(rerun["scheduled_ordinals"], [0, 1, 2])
                self.assertEqual(read(out2 / "receipt.json")["planned_ids"], 3763)

    def test_archive_import_matches_directory_and_tamper_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            out, _, h = self.run_plan(root, p, [], ['{"safety_level":"Level01"}'])
            archive = Path(str(out) + ".zip")
            imported = r.import_attempt(archive, sha(archive), root / "imported", r.synthetic_cohort(), digest(p))
            self.assertEqual(imported, h)
            with self.assertRaisesRegex(ValueError, "OUTER_ARCHIVE"):
                r.import_attempt(archive, "a"*64, root / "bad", r.synthetic_cohort(), digest(p))
            raw = out / "calls/000000/run/samples/000000/raw.json"
            raw.write_text('{}')
            with self.assertRaises((ValueError, KeyError)):
                r.recover(out, r.synthetic_cohort(), digest(p))

    def test_raw_survives_parse_crash_and_is_recovered_without_second_call(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            bundle = self.fixture(root, [0])
            backend = Scripted(['{"safety_level":"Level01"}'])
            def crash(raw):
                self.assertTrue((root / "work/run1/calls/000000/run/samples/000000/raw.json").exists())
                raise KeyboardInterrupt("synthetic parse interruption")
            with patch("safeshift.pilot.runner.parse_label", side_effect=crash):
                out = r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, [], lambda: backend)
            # Engine preserves TECHNICAL_ERROR after parser interruption; explicit repair required.
            self.assertTrue((out / "calls/000000/run/samples/000000/raw.json").exists())
            self.assertEqual(backend.calls, 1)
            h = r.recover(out, r.synthetic_cohort(), digest(p))
            self.assertEqual(h["records"][0]["status"], "TECHNICAL_ERROR")

    def test_missing_history_blocks_before_factory_and_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            h = history_fixture(["SUCCESS"])
            p = make_plan(h, "resume", cap=1)
            bundle = self.fixture(root, p["scheduled_ordinals"])
            with self.assertRaisesRegex(ValueError, "MISSING_HISTORY_EVIDENCE"):
                r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, h, lambda: self.fail("NO_LOAD"))
            self.assertFalse((root / "work/attempts/run1-attempt.json").exists())

    def test_export_failure_preserves_raw_and_cannot_reuse_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            bundle = self.fixture(root, [0])
            backend = Scripted(['{"safety_level":"Level01"}'])
            with patch("safeshift.candidates.fulltrain_run.export", side_effect=OSError("synthetic disk full")):
                with self.assertRaises(OSError):
                    r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, [], lambda: backend)
            self.assertTrue((root / "work/run1/calls/000000/run/samples/000000/raw.json").exists())
            with self.assertRaisesRegex(ValueError, "RUN_ALREADY"):
                r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, [], lambda: self.fail("NO_LOAD"))

    def test_torn_after_raw_before_result_recovers_durably(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            out, _, _ = self.run_plan(root, p, [], ['not valid JSON'])
            # Fault simulation on synthetic evidence only, never a real history edit.
            (out / "calls/000000/run/samples/000000/result.json").unlink()
            (out / "checksums.json").unlink()
            h = r.recover(out, r.synthetic_cohort(), digest(p))
            self.assertEqual(h["records"][0]["status"], "INVALID")
            self.assertEqual(make_plan([h], "resume", run="run2")["scheduled_ordinals"], [1, 2, 3])

    def test_model_load_failure_and_deadline_leave_pending(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            bundle = self.fixture(root, [0])
            def broken():
                raise ImportError("synthetic package ABI failure")
            out = r.rehearse(root / "work", bundle, r.synthetic_cohort(), p, [], broken)
            h = r.recover(out, r.synthetic_cohort(), digest(p))
            self.assertEqual(h["records"][0]["status"], "NOT_ATTEMPTED")
            self.assertTrue((out / "calls/000000/run/failure.json").exists())
            p2 = make_plan([h], "resume", run="run2", cap=1)
            ticks = iter([0, 61])
            out2 = r.rehearse(root / "work", bundle, r.synthetic_cohort(), p2, [h], lambda: self.fail("NO_LOAD"), clock=lambda: next(ticks))
            self.assertEqual(read(out2 / "receipt.json")["stop"], "TIME_CAP")

    def test_input_hash_duplicate_run_mutated_plan_and_private_cohort_block_before_load(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            p = make_plan(cap=1)
            out, _, h = self.run_plan(root, p, [], ['{}'])
            with self.assertRaisesRegex(ValueError, "RUN_ALREADY"):
                r.rehearse(root / "work", root / "inputs", r.synthetic_cohort(), p, [], lambda: self.fail("NO_LOAD"))
            p2 = make_plan([h], "resume", run="run2", cap=1)
            bundle = self.fixture(root, [1])
            (bundle / "000001.bin").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "INPUT_CHECKSUM"):
                r.rehearse(root / "work", bundle, r.synthetic_cohort(), p2, [h], lambda: self.fail("NO_LOAD"))
            self.assertFalse((root / "work/attempts/run2-attempt.json").exists())
            altered = copy.deepcopy(p2)
            altered["scheduled_ordinals"] = [0]
            with self.assertRaisesRegex(ValueError, "PLAN_CHANGED"):
                r.rehearse(root / "work", bundle, r.synthetic_cohort(), altered, [h], lambda: self.fail("NO_LOAD"))
            private = r.synthetic_cohort()
            private["scope"] = "PRIVATE_TRAIN_METADATA"
            with self.assertRaisesRegex(ValueError, "SYNTHETIC_FIXTURE_ONLY"):
                r.rehearse(root / "work", bundle, private, p2, [h], lambda: self.fail("NO_LOAD"))

    def test_shared_process_lease_blocks_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "attempts").mkdir()
            with lease_key(Path(d), "a"*64):
                with self.assertRaises(FileExistsError):
                    with lease_key(Path(d), "a"*64):
                        self.fail("SECOND_LEASE")
            with lease_key(Path(d), "a"*64):
                pass


class FulltrainPreflightTests(unittest.TestCase):
    def test_each_measured_constraint_is_required_and_never_opens_release(self):
        binding = {k: "a"*64 for k in ("cohort_sha256", "source_sha256", "runtime_sha256", "checkpoint_sha256")}
        evidence = {
            "source_binding": {"actual_source_sha256": "a"*64, "allowlist_exact": True},
            "environment": {"kernel_python": "3.13", "worker_python": "3.11.9", "os": "Linux", "architecture": "x86_64"},
            "host_abi": {"system": "Linux", "machine": "x86_64", "pointer_bits": 64},
            "manifest": {"unique_markers": 1, "marker_sha256": "b"*64, "expected_marker_sha256": "b"*64,
                         "cohort_sha256": "a"*64, "planned_ids": 3763, "split": "TRAIN", "order_and_ids_verified": True},
            "checkpoint": {"actual_sha256": "a"*64, "allowlist_exact": True},
            "scratch": {"mount_verified": True, "write_fsync_verified": True, "cleanup_verified": True,
                        "scratch_device": 1, "output_device": 1, "allocated_bytes": 4096, "requested_bytes": 4096},
            "storage": {"scratch_free": 100, "scratch_free_required": 99, "output_free": 100, "output_free_required": 99},
            "live_resources": {"ram_free": 100, "ram_free_required": 99, "quota_remaining": 100, "quota_remaining_required": 99,
                               "time_remaining": 100, "time_remaining_required": 99},
            "runtime_setup": {"actual_runtime_sha256": "a"*64, "worker_isolated": True, "python_pin_matches": True},
            "software_cpu": {"pins_match": True, "pip_check": True, "compiled_abi": True, "native_imports": True},
            "cpu_native": {"shared_production_path": True, "processor_cases_pass": True},
            "images_cpu": {"verified_images": 3763, "checksum_and_decode": True},
            "gpu_driver": {"count_matches": True, "model_matches": True, "driver_matches": True, "visibility_matches": True},
            "cuda_child": {"worker_cuda": "MEASURED_FP16_FUNCTIONAL", "same_worker_runtime_sha256": "a"*64}}
        def inspect(values):
            receipts = {n: {"binding": binding, "evidence": v} for n, v in values.items()}
            return inspect_receipts("minicpm4", binding, receipts, {n: digest(v) for n, v in receipts.items()})
        report = inspect(evidence)
        self.assertEqual(report["receipt_admission"], "PASS")
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["levels"]["LIVE_GPU_PREFLIGHT_PASS"], "NOT_RUN")
        for name, values in evidence.items():
            for field in values:
                missing = copy.deepcopy(evidence)
                missing[name].pop(field)
                with self.subTest(name=name, field=field):
                    self.assertEqual(inspect(missing)["checks"][name]["status"], "BLOCKED")
        for marker in (0, 2):
            wrong = copy.deepcopy(evidence)
            wrong["manifest"]["unique_markers"] = marker
            self.assertEqual(inspect(wrong)["checks"]["manifest"]["status"], "BLOCKED")
        for device in (1, 2):
            wrong = copy.deepcopy(evidence)
            wrong["scratch"]["output_device"] = device
            wrong["scratch"]["allocated_bytes"] = 100
            self.assertEqual(inspect(wrong)["checks"]["scratch"]["status"], "BLOCKED")

    def test_missing_receipts_stay_blocked_repeatably_without_side_effects(self):
        binding = {k: "a"*64 for k in ("cohort_sha256", "source_sha256", "runtime_sha256", "checkpoint_sha256")}
        a = inspect_receipts("minicpm4", binding, {}, {})
        self.assertEqual(a, inspect_receipts("minicpm4", binding, {}, {}))
        self.assertEqual(a["status"], "BLOCKED")
        self.assertEqual(a["levels"]["WEIGHTS_LOADED"], "NOT_RUN")
        self.assertEqual(a["owner_slots"], 0)
        self.assertEqual(a["production_calls"], 0)

    def test_pass_words_missing_marker_packages_gpu_storage_do_not_pass(self):
        binding = {k: "a"*64 for k in ("cohort_sha256", "source_sha256", "runtime_sha256", "checkpoint_sha256")}
        for name in CHECKS:
            receipt = {"binding": binding, "evidence": {"status": "PASS"}}
            report = inspect_receipts("internvl35", binding, {name: receipt}, {name: digest(receipt)})
            self.assertEqual(report["checks"][name]["status"], "BLOCKED", name)
        with self.assertRaisesRegex(ValueError, "CUSTODY_OR_BINDING"):
            inspect_receipts("qwen3", binding, {"manifest": receipt}, {"manifest": "b"*64})


if __name__ == "__main__":
    unittest.main()
