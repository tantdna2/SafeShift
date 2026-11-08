"""CPU synthetic cohort/controller tests. No real data/model/GPU."""
import copy
import os
from pathlib import Path
import tempfile
import time
import subprocess
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift import internvl3763 as r
from safeshift.candidates.fulltrain_run import synthetic_cohort, synthetic_bytes
from safeshift.pilot.artifacts import write, sha, read
from safeshift.pilot.contract import digest


def make_real_memory_snapshot(base_dir, *, mem_available_kb=33554432, vm_rss_kb=65536,
                              mem_current=str(4 * 2**30), mem_max=str(32 * 2**30),
                              mem_peak=str(5 * 2**30), mem_stat="anon 1073741824\nfile 3221225472\n",
                              mem_events="high 0\nlow 0\nmax 0\noom 0\noom_group_kill 0\noom_kill 0\n",
                              cgroup_v1_only=False):
    from safeshift import internvl_v2_memory as mem
    base = Path(base_dir)
    proc, cg = base / "proc", base / "cgroup"
    if proc.exists():
        import shutil
        shutil.rmtree(proc)
    if cg.exists():
        import shutil
        shutil.rmtree(cg)
    (proc / "self").mkdir(parents=True)
    cg.mkdir(parents=True)
    if mem_available_kb is not None:
        (proc / "meminfo").write_text(f"MemAvailable: {mem_available_kb} kB\n", encoding="utf8")
    if vm_rss_kb is not None:
        (proc / "self/status").write_text(f"Name: synthetic\nVmRSS: {vm_rss_kb} kB\n", encoding="utf8")
    else:
        (proc / "self/status").write_text("Name: synthetic\n", encoding="utf8")
    (proc / "self/smaps_rollup").write_text("Rss: 65536 kB\nAnonymous: 32768 kB\n", encoding="utf8")
    if cgroup_v1_only:
        (cg / "memory").mkdir()
        (cg / "memory/memory.limit_in_bytes").write_text(str(32 * 2**30), encoding="utf8")
        (cg / "memory/memory.usage_in_bytes").write_text(str(4 * 2**30), encoding="utf8")
        return mem.snapshot(proc, cg)
    for fname, content in (
        ("memory.current", mem_current),
        ("memory.max", mem_max),
        ("memory.peak", mem_peak),
        ("memory.stat", mem_stat),
        ("memory.events", mem_events),
    ):
        if content is not None:
            (cg / fname).write_text(str(content), encoding="utf8")
    return mem.snapshot(proc, cg)


class PreparedControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = synthetic_cohort()

    def plan(self, history=None, **kwargs):
        return r.plan(self.cohort, history or [], action="initial", run_id="synthetic-run",
            attempt_id="synthetic-a1", max_calls=kwargs.get("max_calls", 3), max_seconds=kwargs.get("max_seconds", 600))

    def backend(self, response='{"safety_level":"Level02"}', fail=False):
        def generate(image, sample, binding, deadline):
            write(sample / "native_call.json", {"binding": binding})
            if fail:
                raise RuntimeError("SYNTHETIC_NATIVE_ERROR")
            raw = {"binding": binding, "response": response, "hnlo": None, "hnlo_status": r.HNLO_STATUS,
                "evidence_kind": "SYNTHETIC", "notice": "SYNTHETIC CONTROLLER FIXTURE"}
            raw_hash = write(sample / "raw.json", raw)
            # Written after raw, before the controller can classify/accept completion.
            write(sample / "trace-verification.json", {"status": "SYNTHETIC_CONTROLLER_ONLY"})
            label = r.parse_label(response)
            return {"status": "SUCCESS" if label else "INVALID", "label": label,
                "raw_sha256": raw_hash, "trace_verified": True, "hnlo": None, "hnlo_status": r.HNLO_STATUS}
        return NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=generate)

    def execute(self, backend=None, p=None):
        p = p or self.plan()
        def image_path(row):
            image = self.root / f"image-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        result = r.rehearse(self.root / "attempt", self.root / "attempt.zip", self.cohort,
            p, [], lambda _: backend or self.backend(), image_path=image_path, tokenizer_sha="a" * 64)
        return result, p

    def test_exact3763_plan_new_identity_label_only_no_inheritance(self):
        p = self.plan()
        self.assertEqual(len(p["samples"]), 3763)
        self.assertEqual(p["scheduled_ordinals"], [0, 1, 2])
        self.assertEqual(p["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(p["identity"]["hnlo_policy"], "LABEL_ONLY")
        self.assertFalse(p["pooling_allowed"])
        self.assertNotEqual(p["series_id"], r.capture.SERIES)

    def test_shared_controller_archive_raw_before_parse_and_full_denominator(self):
        result, p = self.execute()
        self.assertEqual(result["model_calls"], 3)
        self.assertEqual(result["counts"], {"SUCCESS": 3, "NOT_ATTEMPTED": 3760})
        receipt = r.verify_bundle(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["scope"], "SYNTHETIC_ONLY")
        self.assertFalse(receipt["scientific_qualified"])

    def test_invalid_is_durable_no_parser_rescue(self):
        result, _ = self.execute(self.backend('```json\n{"safety_level":"Level02"}\n```'))
        self.assertEqual(result["counts"], {"INVALID": 3, "NOT_ATTEMPTED": 3760})
        self.assertIsNone(result["records"][0]["label"])

    def test_failure_is_consumed_stop_tail_export_and_no_retry(self):
        result, p = self.execute(self.backend(fail=True))
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["counts"], {"TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(r.verify_bundle(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)["status"], "FAIL")
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_load_failure_keeps_zero_calls_and_exports(self):
        p = self.plan()
        def fail(_):
            raise RuntimeError("LOAD_FAILED")
        result = r.rehearse(self.root / "attempt", self.root / "attempt.zip", self.cohort,
            p, [], fail, image_path=Mock(side_effect=AssertionError), tokenizer_sha="a"*64)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertTrue((self.root / "attempt/failure.json").is_file())

    def test_resume_excludes_consumed_success_invalid_error_and_keeps_series(self):
        result, p = self.execute(self.backend('invalid'))
        h = r.sealed_history(self.root / "attempt.zip", sha(self.root / "attempt.zip"), p)
        next_plan = r.plan(self.cohort, [h], action="resume", run_id="synthetic-run2",
            attempt_id="synthetic-a2", max_calls=4, max_seconds=600)
        self.assertEqual(next_plan["scheduled_ordinals"], [3, 4, 5, 6])
        self.assertEqual(next_plan["counts"]["INVALID"], 3)
        h["series_id"] = "candidate160"
        with self.assertRaisesRegex(ValueError, "FOREIGN"):
            r.plan(self.cohort, [h], action="resume", run_id="r", attempt_id="a", max_calls=1, max_seconds=1)

    def test_all_native_routes_closed_before_io_even_with_environment_approval(self):
        from scripts.internvl3763 import main
        with patch.object(r, "read", side_effect=AssertionError("NO_IO")):
            for call in (lambda: r.worker(), lambda: r.NativeBackend(None, None, None, None),
                    lambda: r.NativeBackend.generate(None, None, None, None, None),
                    lambda: r.generate_prepared(None, None, None, None, None),
                    lambda: main(["--mode", "execute", "--output", "missing"]),
                    lambda: main(["--mode", "worker"])):
                with self.subTest(call=call), self.assertRaises(PermissionError):
                    call()

    def test_source_original_science_frozen_and_test_or_pilot_cohort_rejected(self):
        self.assertEqual(r.check_source(r.source_spec()), digest(r.source_spec()))
        bad = copy.deepcopy(self.cohort); bad["samples"] = bad["samples"][:160]
        with self.assertRaisesRegex(ValueError, "3763"):
            r.plan(bad, [], action="initial", run_id="r", attempt_id="a", max_calls=1, max_seconds=1)
        self.cohort["split"] = "TEST"
        with self.assertRaisesRegex(ValueError, "TRAIN_ONLY"):
            self.plan()

    def test_packaged_prepare_imports_with_no_repository_or_site_packages(self):
        extracted = self.root / "extracted"
        for name in r.source_spec()["manifest"]:
            path = extracted / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((r.ROOT / name).read_bytes())
        code = "import sys; sys.path.insert(0,sys.argv[1]); from scripts.internvl3763 import preparation; assert preparation()['status']=='BLOCKED'; print('ISOLATED_PREP_PASS')"
        result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(extracted)],
            cwd=extracted, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ISOLATED_PREP_PASS", result.stdout)

    def test_export_reserve_blocks_before_first_call_and_keeps_not_attempted(self):
        backend = self.backend()
        backend.generate = Mock(side_effect=AssertionError("NO_CALL_WITHOUT_EXPORT_SPACE"))
        with patch.object(r.shutil, "disk_usage", return_value=NS(free=0)):
            result, _ = self.execute(backend)
        backend.generate.assert_not_called()
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(read(self.root / "attempt/stop.json")["reason"], "CAPTURE_AND_EXPORT_SPACE_NOT_AVAILABLE")

    def test_noop_resume_does_not_load_or_generate(self):
        p = self.plan()
        # Handwritten synthetic HISTORY contract, not a claim of archived model outputs.
        h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": r.SERIES,
            "identity": p["identity"], "cohort_sha256": digest(self.cohort), "parent_history_sha256": digest([]),
            "action": "initial", "evidence_sha256": digest("SYNTHETIC_HISTORY_ONLY"), "repair": None,
            "records": [{**row, "status": "INVALID", "label": None, "attempts": 1,
                "native_calls": 1, "raw_sha256": digest("SYNTHETIC_RAW_REFERENCE_ONLY")}
                for row in self.cohort["samples"]]}
        next_plan = r.plan(self.cohort, [h], action="resume", run_id="noop", attempt_id="noop-a",
            max_calls=1, max_seconds=600)
        self.assertEqual(next_plan["scheduled_ordinals"], [])
        factory = Mock(side_effect=AssertionError("NO_NOOP_LOAD"))
        receipt = r.rehearse(self.root / "noop", self.root / "noop.zip", self.cohort,
            next_plan, [h], factory, image_path=Mock(side_effect=AssertionError), tokenizer_sha="a"*64)
        self.assertEqual(receipt["model_calls"], 0)
        factory.assert_not_called()

    def test_capture_budget_exact_10_vs_64_steps_and_strict_int_bounds(self):
        b10 = r.capture_budget(vocab=151936, steps=10)
        self.assertEqual(b10["per_sample_bytes"], 15378176)
        self.assertEqual(b10["sample_and_export_bytes"], 30756352)
        b64 = r.capture_budget(vocab=151936, steps=64)
        self.assertEqual(b64["per_sample_bytes"], 92758016)
        self.assertEqual(r.capture_budget()["per_sample_bytes"], 120442880)
        for bad_vocab, bad_steps in ((0, 10), (200001, 10), (True, 10), (151936.0, 10), (151936, 0), (151936, 65), (151936, False)):
            with self.subTest(vocab=bad_vocab, steps=bad_steps), self.assertRaisesRegex(ValueError, "CAPTURE_DIMENSION_BOUND"):
                r.capture_budget(vocab=bad_vocab, steps=bad_steps)

    def test_adaptive_deadline_stops_cleanly_before_risking_call_timeout(self):
        # Slow first sample (200s -> adaptive reserve = max(180, 400) = 400s): with 350s left (> 180s!), stops cleanly.
        p = r.plan(self.cohort, [], action="initial", run_id="adaptive-dl",
            attempt_id="adaptive-a1", max_calls=2, max_seconds=600)
        ticks = iter([0.0, 5.0, 5.0, 5.0, 205.0, 250.0, 250.0])
        def image_path(row):
            image = self.root / f"adaptive-img-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        result = r.rehearse(self.root / "adaptive", self.root / "adaptive.zip", self.cohort,
            p, [], lambda _: self.backend(), image_path=image_path, tokenizer_sha="a"*64,
            clock=lambda: next(ticks, 250.0))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(read(self.root / "adaptive/stop.json"), {"reason": "DEADLINE_BEFORE_NEXT_CALL"})
        self.assertFalse((self.root / "adaptive/samples/000001/started.json").exists())

    def test_pre_call_180s_reserve_zero_prior_fast_exact_boundary_and_mid_shard_preservation(self):
        def image_path(row):
            image = self.root / f"pre180-img-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        # (a) Zero prior samples: <180s (179.9s), exact 180.0s, and expired all stop before touching image/model.
        for label, max_sec, now_val in (("under_180", 180, 0.1), ("exact_180", 180, 0.0), ("expired", 180, 185.0)):
            with self.subTest(case=label):
                p0 = r.plan(self.cohort, [], action="initial", run_id=f"pre0-{label}",
                    attempt_id="a1", max_calls=2, max_seconds=max_sec)
                ticks0 = iter([0.0, 0.0, now_val, now_val])
                no_call_backend = NS(environment={"scope": "SYNTHETIC_ONLY"},
                    generate=Mock(side_effect=AssertionError("NO_CALL_WHEN_UNDER_OR_AT_180S_RESERVE")))
                res0 = r.rehearse(self.root / f"pre0-{label}", self.root / f"pre0-{label}.zip", self.cohort,
                    p0, [], lambda _: no_call_backend, image_path=Mock(side_effect=AssertionError("NO_IMAGE_READ")),
                    tokenizer_sha="a"*64, clock=lambda: next(ticks0, now_val))
                self.assertEqual(res0["status"], "PASS")
                self.assertEqual(res0["model_calls"], 0)
                self.assertEqual(res0["counts"], {"NOT_ATTEMPTED": 3763})
                self.assertEqual(read(self.root / f"pre0-{label}/stop.json"), {"reason": "DEADLINE_BEFORE_NEXT_CALL"})

        # (b) Fast prior sample (13.42s -> 2x = 26.84s < 180s): 100s left or exact 180.0s left MUST stop before call 1!
        for label, second_now in (("fast_100s_left", 500.0), ("fast_exact_180s_left", 420.0)):
            with self.subTest(case=label):
                pf = r.plan(self.cohort, [], action="initial", run_id=f"pref-{label}",
                    attempt_id="a1", max_calls=3, max_seconds=600)
                # begun=0 (deadline=600), load=5, call0check=5 (585s>180s), start0=5, end0=18.42, call1check=second_now
                ticksf = iter([0.0, 5.0, 5.0, 5.0, 18.42, second_now, second_now])
                resf = r.rehearse(self.root / f"pref-{label}", self.root / f"pref-{label}.zip", self.cohort,
                    pf, [], lambda _: self.backend(), image_path=image_path, tokenizer_sha="a"*64,
                    clock=lambda: next(ticksf, second_now))
                self.assertEqual(resf["status"], "PASS")
                self.assertEqual(resf["model_calls"], 1)
                self.assertEqual(resf["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
                self.assertEqual(read(self.root / f"pref-{label}/stop.json"), {"reason": "DEADLINE_BEFORE_NEXT_CALL"})
                self.assertEqual(r.verify_bundle(self.root / f"pref-{label}.zip", sha(self.root / f"pref-{label}.zip"), pf)["status"], "PASS")

        # (c) 180.1s left allows call 1, then stops cleanly mid-shard before call 2 preserving all raw outputs for resume.
        pm = r.plan(self.cohort, [], action="initial", run_id="prem-mid", attempt_id="a1", max_calls=4, max_seconds=600)
        # call0check=5.0, start0=5.0, end0=18.42, call1check=419.9 (180.1s left -> runs!), start1=419.9, end1=433.32, call2check=433.32 (166.68s left -> stops!)
        ticksm = iter([0.0, 5.0, 5.0, 5.0, 18.42, 419.9, 419.9, 433.32, 433.32, 434.0])
        resm = r.rehearse(self.root / "prem-mid", self.root / "prem-mid.zip", self.cohort,
            pm, [], lambda _: self.backend(), image_path=image_path, tokenizer_sha="a"*64,
            clock=lambda: next(ticksm, 434.0))
        self.assertEqual(resm["status"], "PASS")
        self.assertEqual(resm["model_calls"], 2)
        self.assertEqual(resm["counts"], {"SUCCESS": 2, "NOT_ATTEMPTED": 3761})
        self.assertTrue((self.root / "prem-mid/samples/000000/raw.json").is_file())
        self.assertTrue((self.root / "prem-mid/samples/000001/raw.json").is_file())
        hm = r.sealed_history(self.root / "prem-mid.zip", sha(self.root / "prem-mid.zip"), pm)
        next_pm = r.plan(self.cohort, [hm], action="resume", run_id="prem-next", attempt_id="a2", max_calls=2, max_seconds=600)
        self.assertEqual(next_pm["scheduled_ordinals"], [2, 3])

        # (d) Lowering pre_call_reserve_seconds below 180 or passing bool is rejected fail-closed.
        for bad_res in (0, 179, True, 180.0):
            with self.assertRaisesRegex(ValueError, "PRE_CALL_RESERVE_SECONDS"):
                r._execute(self.root / f"bad-res-{bad_res}", None, self.cohort, pm, lambda _: self.backend(),
                    image_path=image_path, tokenizer_sha="a"*64, pre_call_reserve_seconds=bad_res)

    def test_full_174_call_shard_completes_under_2x_latency_with_export_reserve(self):
        # Verify that Ledger.measure's 255s margin (75s launch headroom + 180s pre-call reserve)
        # plus 5 MiB/s ZIP export reserve lets all 174 calls complete even when setup, load,
        # and every single sample take 2x Attempt 4 latency while accumulating 2.45 GB of raw data!
        from safeshift import internvl3763_campaign as c
        proj = c.project_campaign_budget()
        opt = proj["scenarios"]["optimized_safe_current_job_cap"]
        self.assertEqual((opt["safe_calls_per_job"], opt["per_call_seconds"], opt["full_shard_seconds"]), (174, 30, 7194))
        p = c.plan(self.cohort, [], action="initial", run_id="shard174", attempt_id="attempt-1",
            max_calls=174, max_seconds=7194)
        img_file = self.root / "shared-img.bin"
        def image_path(row):
            img_file.write_bytes(synthetic_bytes(row["ordinal"]))
            return img_file
        # Launch starts at t=0 -> job_deadline=7194 -> worker_deadline = 7194 - 75 = 7119.
        # 2x setup = 534.42s, 2x worker_non_sample = 1184.294s -> worker load finishes at 1718.714s.
        # Each of 174 samples takes 2x 13.42s = 26.84s and produces 14,055,278 bytes of raw capture.
        timeline = [534.42, 1718.714]
        cur = 1718.714
        for _ in range(174):
            timeline.extend([cur, cur, cur + 26.84])
            cur += 26.84
        timeline.append(cur)
        it = iter(timeline)
        backend = self.backend()
        with patch.object(r, "_backend_capture_budget", return_value=r.capture_budget(vocab=151936, steps=10)), \
                patch.object(r, "_sample_files_and_bytes", return_value=(30, 14055278)), \
                patch.object(r.shutil, "disk_usage", return_value=NS(free=20 * 2**30)):
            res = r._execute(self.root / "shard174", None, self.cohort, p, lambda _: backend,
                image_path=image_path, tokenizer_sha="a"*64, clock=lambda: next(it, cur), hard_deadline=7119.0)
        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["model_calls"], 174)
        self.assertEqual(res["counts"], {"SUCCESS": 174, "NOT_ATTEMPTED": 3589})
        self.assertFalse((self.root / "shard174/stop.json").exists())
        # Remaining time before job_deadline (7194s) after all 174 samples is > 800s for ZIP packaging!
        self.assertGreater(7194.0 - cur, 800.0)

    def test_dynamic_oversized_sample_archive_parent_disk_log_margin_and_cgroup_headroom_stops(self):
        def image_path(row):
            image = self.root / f"guard-img-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        p = self.plan(max_calls=2, max_seconds=600)

        # (a) Archive parent directory on a nearly full mount stops before call 0 even when out has 100 GiB free.
        out_dir = self.root / "disk-out"
        arc_dir = self.root / "disk-arc"
        arc_dir.mkdir()
        def disk_by_path(target):
            return NS(free=512 * 2**20 if Path(target).resolve() == arc_dir.resolve() else 100 * 2**30)
        with patch.object(r.shutil, "disk_usage", side_effect=disk_by_path):
            res_disk = r.rehearse(out_dir, arc_dir / "out.zip", self.cohort, p, [],
                lambda _: self.backend(), image_path=image_path, tokenizer_sha="a"*64)
        self.assertEqual(res_disk["model_calls"], 0)
        self.assertEqual(read(out_dir / "stop.json"), {"reason": "CAPTURE_AND_EXPORT_SPACE_NOT_AVAILABLE"})

        # (b) Supervised worker log approaching 16 MiB cap (>= 12 MiB soft limit) stops cleanly before next call.
        sup_parent = self.root / "sup-log"
        write(sup_parent / "handoff.json", {"scope": "SYNTHETIC_SUPERVISED"})
        def noisy_generate(image, sample, binding, deadline):
            val = self.backend().generate(image, sample, binding, deadline)
            (sup_parent / "worker.log").write_bytes(b"L" * (12 * 2**20))
            return val
        res_log = r.rehearse(sup_parent / "run", self.root / "sup-log.zip", self.cohort, p, [],
            lambda _: NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=noisy_generate),
            image_path=image_path, tokenizer_sha="a"*64)
        self.assertEqual(res_log["status"], "PASS")
        self.assertEqual(res_log["model_calls"], 1)
        self.assertEqual(read(sup_parent / "run/stop.json"), {"reason": "WORKER_LOG_BUDGET_MARGIN"})

        # (c) Low cgroup memory headroom (< 512 MiB) on real internvl_v2_memory.snapshot() schema stops cleanly before next call.
        mem_backend = self.backend()
        mem_backend.check_cgroup_memory = True
        snap_ok = make_real_memory_snapshot(self.root / "snap-ok", mem_max=str(8 * 2**30), mem_current=str(2 * 2**30))
        snap_low = make_real_memory_snapshot(self.root / "snap-low", mem_max=str(8 * 2**30),
            mem_current=str(8 * 2**30 - 256 * 2**20))
        self.assertEqual(snap_ok["status"], "OBSERVED")
        self.assertNotIn("status", snap_ok["cgroup"])
        self.assertEqual(snap_low["status"], "OBSERVED")
        self.assertNotIn("status", snap_low["cgroup"])
        snapshots = iter([snap_ok, snap_low])
        with patch("safeshift.internvl_v2_memory.snapshot", side_effect=lambda: next(snapshots)):
            res_mem = r.rehearse(self.root / "mem-stop", self.root / "mem-stop.zip", self.cohort, p, [],
                lambda _: mem_backend, image_path=image_path, tokenizer_sha="a"*64)
        self.assertEqual(res_mem["status"], "PASS")
        self.assertEqual(res_mem["model_calls"], 1)
        self.assertEqual(read(self.root / "mem-stop/stop.json"), {"reason": "CGROUP_MEMORY_HEADROOM_LOW"})

        # (d) Accumulated multi-GB sample bytes expand next_call_reserve beyond 180s to protect ZIP export time!
        # With 2.0 GiB written, export reserve at 5 MiB/s requires ~410s (> 60s stage reserve -> +350s extra);
        # when 300s remain (> 180s base reserve, < 530s total reserve), worker stops cleanly before call 1.
        ticks_zip = iter([0.0, 5.0, 5.0, 5.0, 15.0, 300.0, 300.0])
        with patch.object(r, "_sample_files_and_bytes", return_value=(30, 2 * 2**30)), \
                patch.object(r.shutil, "disk_usage", return_value=NS(free=100 * 2**30)):
            res_zip_res = r._execute(self.root / "zip-res", None, self.cohort, p,
                lambda _: self.backend(), image_path=image_path, tokenizer_sha="a"*64,
                clock=lambda: next(ticks_zip, 300.0))
        self.assertEqual(res_zip_res["status"], "PASS")
        self.assertEqual(res_zip_res["model_calls"], 1)
        self.assertEqual(read(self.root / "zip-res/stop.json"), {"reason": "DEADLINE_BEFORE_NEXT_CALL"})

    def test_supervised_parent_bytes_and_archive_bounds_stop_cleanly(self):
        p = r.plan(self.cohort, [], action="initial", run_id="sup-archive",
            attempt_id="sup-a1", max_calls=2, max_seconds=600)
        parent = self.root / "supervised_job"
        write(parent / "handoff.json", {"scope": "SYNTHETIC_SUPERVISED"})
        (parent / "outer-pad.bin").write_bytes(b"x" * (4 * 2**20))
        def image_path(row):
            image = self.root / f"sup-img-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image
        per_sample = r.capture_budget()["per_sample_bytes"]
        # Allow sample 0 (4 MiB outer + ~0.5 MiB plan/cohort + 120.44 MiB + 16 MiB margin < 145 MiB),
        # then block sample 1 if sample 0 writes a large synthetic payload.
        def fat_generate(image, sample, binding, deadline):
            res = self.backend().generate(image, sample, binding, deadline)
            (sample / "steps").mkdir(exist_ok=True)
            (sample / "steps/000.f32").write_bytes(b"\x00" * (10 * 2**20))
            return res
        fat_backend = NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=fat_generate)
        tight_limit = 4 * 2**20 + per_sample + 16 * 2**20 + 2 * 2**20
        result = r.rehearse(parent / "run", self.root / "sup.zip", self.cohort,
            p, [], lambda _: fat_backend, image_path=image_path, tokenizer_sha="a"*64,
            archive_limit_bytes=tight_limit)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(read(parent / "run/stop.json"), {"reason": "ARCHIVE_VERIFIER_8GIB_BOUND_EXPORT_MARGIN"})
        for bad_limit in (0, -1, True, 1.5):
            with self.assertRaisesRegex(ValueError, "ARCHIVE_LIMIT_BYTES"):
                r._execute(self.root / f"bad-{bad_limit}", None, self.cohort, p, lambda _: fat_backend,
                    image_path=image_path, tokenizer_sha="a"*64, archive_limit_bytes=bad_limit)

    def test_real_memory_snapshot_contract_healthy_low_ram_oom_incomplete_v1_invalid_and_native_scope(self):
        def image_path(row):
            image = self.root / f"memcontract-img-{row['ordinal']}"
            image.write_bytes(synthetic_bytes(row["ordinal"]))
            return image

        # 1. Healthy OBSERVED variants from real internvl_v2_memory.snapshot(proc, cg):
        healthy_default = make_real_memory_snapshot(self.root / "m-healthy")
        healthy_no_peak = make_real_memory_snapshot(self.root / "m-nopeak", mem_peak=None)
        healthy_unlimited = make_real_memory_snapshot(self.root / "m-unlim", mem_max="max", mem_available_kb=2 * 1024 * 1024)
        healthy_exact_floor = make_real_memory_snapshot(self.root / "m-exact512",
            mem_max=str(4 * 2**30), mem_current=str(4 * 2**30 - r.CGROUP_MIN_FREE_BYTES))
        for label, snap in (
            ("default", healthy_default),
            ("no_optional_peak", healthy_no_peak),
            ("max_unlimited", healthy_unlimited),
            ("exact_512mib_floor", healthy_exact_floor),
        ):
            with self.subTest(healthy=label):
                self.assertEqual(snap["status"], "OBSERVED")
                self.assertNotIn("status", snap["cgroup"])
                self.assertIsNone(r.inspect_memory_snapshot(snap))

        # 2. Low RAM headroom variants (1 byte below 512 MiB on cgroup limit, and memory.max=='max' with low host MemAvailable):
        low_1byte = make_real_memory_snapshot(self.root / "m-low1",
            mem_max=str(4 * 2**30), mem_current=str(4 * 2**30 - r.CGROUP_MIN_FREE_BYTES + 1))
        low_host_unlim = make_real_memory_snapshot(self.root / "m-lowhost",
            mem_max="max", mem_available_kb=511 * 1024)
        self.assertEqual(r.inspect_memory_snapshot(low_1byte), "CGROUP_MEMORY_HEADROOM_LOW")
        self.assertEqual(r.inspect_memory_snapshot(low_host_unlim), "CGROUP_MEMORY_HEADROOM_LOW")

        # 3. OOM observed variants (oom_kill, oom, oom_group_kill > 0 even when RAM is plentiful):
        for oom_key in ("oom_kill", "oom", "oom_group_kill"):
            snap_oom = make_real_memory_snapshot(self.root / f"m-{oom_key}",
                mem_events=f"oom {1 if oom_key == 'oom' else 0}\noom_kill {1 if oom_key == 'oom_kill' else 0}\noom_group_kill {1 if oom_key == 'oom_group_kill' else 0}\n")
            self.assertEqual(snap_oom["status"], "OBSERVED")
            self.assertEqual(r.inspect_memory_snapshot(snap_oom), "CGROUP_OOM_OBSERVED")

        # 4. Missing / INCOMPLETE / Linux cgroup-v1-only observations fail closed (never silently pass):
        incomp_v1 = make_real_memory_snapshot(self.root / "m-v1", cgroup_v1_only=True)
        incomp_no_stat = make_real_memory_snapshot(self.root / "m-nostat", mem_stat=None)
        incomp_no_events = make_real_memory_snapshot(self.root / "m-noevents", mem_events=None)
        incomp_no_rss = make_real_memory_snapshot(self.root / "m-norss", vm_rss_kb=None)
        incomp_bad_stat = make_real_memory_snapshot(self.root / "m-badstat", mem_stat="anon -1\nfile 123\n")
        for label, snap in (
            ("cgroup_v1_only", incomp_v1),
            ("missing_stat", incomp_no_stat),
            ("missing_events", incomp_no_events),
            ("missing_vmrss", incomp_no_rss),
            ("negative_anon", incomp_bad_stat),
        ):
            with self.subTest(incomplete=label):
                self.assertEqual(snap["status"], "INCOMPLETE")
                self.assertEqual(r.inspect_memory_snapshot(snap), "CGROUP_MEMORY_UNOBSERVED")

        # 5. Forged / malformed / legacy fake cgroup.status structures fail closed:
        legacy_fake = {"cgroup": {"status": "OBSERVED", "memory.max": 8 * 2**30, "memory.current": 2**30, "memory.events": {"oom_kill": 0}}}
        injected_cg_status = copy.deepcopy(healthy_default)
        injected_cg_status["cgroup"]["status"] = "OBSERVED"
        obs_with_err = copy.deepcopy(healthy_default)
        obs_with_err["errors"] = [{"file": "memory.stat", "type": "OSError"}]
        bool_cur = copy.deepcopy(healthy_default)
        bool_cur["cgroup"]["memory.current"] = True
        bool_max = copy.deepcopy(healthy_default)
        bool_max["cgroup"]["memory.max"] = True
        bool_oom = copy.deepcopy(healthy_default)
        bool_oom["cgroup"]["memory.events"]["oom_kill"] = False
        bool_avail = copy.deepcopy(healthy_default)
        bool_avail["gate_memory"]["available_bytes"] = True
        missing_oom_key = copy.deepcopy(healthy_default)
        missing_oom_key["cgroup"]["memory.events"] = {"oom": 0}
        weird_max = copy.deepcopy(healthy_default)
        weird_max["cgroup"]["memory.max"] = "unlimited"
        for label, bad_snap in (
            ("none", None),
            ("list", []),
            ("empty_dict", {}),
            ("errors_only", {"errors": []}),
            ("legacy_fake_cgroup_status", legacy_fake),
            ("injected_cgroup_status_key", injected_cg_status),
            ("observed_with_nonempty_errors", obs_with_err),
            ("bool_current", bool_cur),
            ("bool_max", bool_max),
            ("bool_oom_kill", bool_oom),
            ("bool_available_bytes", bool_avail),
            ("missing_oom_kill_counter", missing_oom_key),
            ("invalid_max_string", weird_max),
        ):
            with self.subTest(malformed=label):
                self.assertEqual(r.inspect_memory_snapshot(bad_snap), "CGROUP_MEMORY_UNOBSERVED")

        # 6. Explicit NativeBackend vs synthetic bypass scope + real controller stop preservation:
        synth_backend = self.backend()
        native_inst = object.__new__(r.NativeBackend)
        with patch("safeshift.internvl_v2_memory.snapshot", return_value=incomp_v1):
            # Default synthetic rehearsal bypasses Linux /proc cgroup check on non-Linux hosts:
            self.assertIsNone(r._cgroup_memory_issue(synth_backend))
            self.assertFalse(r._cgroup_memory_low(synth_backend))
            # Real NativeBackend instance ALWAYS enforces the gate without needing any test flag:
            self.assertEqual(r._cgroup_memory_issue(native_inst), "CGROUP_MEMORY_UNOBSERVED")
            self.assertTrue(r._cgroup_memory_low(native_inst))

        # Controller stops cleanly on OOM, INCOMPLETE, and host-unlimited low RAM while preserving sample 0 raw output:
        p2 = self.plan(max_calls=2, max_seconds=600)
        snap_oom_kill = make_real_memory_snapshot(self.root / "m-stop-oom",
            mem_events="oom 1\noom_kill 1\noom_group_kill 0\n")
        for case_name, second_snap, expected_reason in (
            ("oom", snap_oom_kill, "CGROUP_OOM_OBSERVED"),
            ("incomplete", incomp_v1, "CGROUP_MEMORY_UNOBSERVED"),
            ("host_low_unlimited", low_host_unlim, "CGROUP_MEMORY_HEADROOM_LOW"),
        ):
            with self.subTest(controller_stop=case_name):
                b_gate = self.backend()
                b_gate.check_cgroup_memory = True
                seq = iter([healthy_default, second_snap])
                out_case = self.root / f"stop-{case_name}"
                arc_case = self.root / f"stop-{case_name}.zip"
                with patch("safeshift.internvl_v2_memory.snapshot", side_effect=lambda: next(seq)):
                    res_case = r.rehearse(out_case, arc_case, self.cohort, p2, [],
                        lambda _: b_gate, image_path=image_path, tokenizer_sha="a"*64)
                self.assertEqual(res_case["status"], "PASS")
                self.assertEqual(res_case["model_calls"], 1)
                self.assertEqual(res_case["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
                self.assertTrue((out_case / "samples/000000/raw.json").is_file())
                self.assertFalse((out_case / "samples/000001/started.json").exists())
                self.assertEqual(read(out_case / "stop.json"), {"reason": expected_reason})
                self.assertEqual(r.verify_bundle(arc_case, sha(arc_case), p2)["status"], "PASS")


@unittest.skipUnless(os.environ.get("SAFESHIFT3763_NATIVE_CPU") == "1", "opt-in CPU torch/transformers")
class NativeCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_internvl_v2_runtime import NativeCaptureTests as Helper
        Helper.setUpClass()
        cls.helper = Helper("test_all_labels_actual_generate_full_raw_before_processor_and_parse")
        cls.torch = Helper.torch

    def call(self, backend, folder):
        binding = {k: digest("SYNTHETIC-" + k) for k in r.trace_binding({},
            {"series_id": r.SERIES}, {"ordinal": 0, "image_sha256": "a"*64}, "b"*64)}
        inputs = {"input_ids": self.torch.tensor([[8]]),
            "attention_mask": self.torch.ones((1, 1), dtype=self.torch.long)}
        with patch.object(r, "authorize", return_value={"scope": "SYNTHETIC_CLAIM_ONLY"}):
            return r.generate_prepared(backend, inputs, folder, binding, time.monotonic() + 30, ordinal=0)

    def test_actual_native_generate_all_labels_full_capture_and_raw_precedes_parse(self):
        for level in range(4):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                backend = self.helper.backend(level)
                parser = r.parse_label
                def checked_parse(text):
                    self.assertTrue((folder / "raw.json").is_file())
                    self.assertTrue((folder / "native_call.json").is_file())
                    return parser(text)
                with patch.object(r, "parse_label", checked_parse):
                    result = self.call(backend, folder)
                self.assertEqual(result["label"], f"Level0{level+1}")
                self.assertTrue(result["trace_verified"])
                self.assertEqual(read(folder / "raw.json")["evidence_kind"], "SYNTHETIC")
                self.assertTrue(read(folder / "trace-verification.json")["forced_steps"])
                self.assertEqual((folder / "steps/000.f32").stat().st_size, 4 * backend.logit_width)
                self.assertFalse(backend.model._forward_hooks)

    def test_native_invalid_keeps_raw_and_failure_without_rescue(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = self.helper.backend()
            decode = backend.tokenizer.decode
            def changed(ids, **kwargs):
                text = decode(ids, **kwargs)
                return "```json\n" + text + "\n```" if (folder / "native.json").exists() else text
            with patch.object(backend.tokenizer, "decode", changed):
                result = self.call(backend, folder)
            self.assertEqual(result["status"], "INVALID")
            self.assertFalse(result["trace_verified"])
            self.assertTrue(read(folder / "raw.json")["response"].startswith("```"))

    def test_native_nonfinite_keeps_consumed_marker_and_binary(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            backend = self.helper.backend(defect="nonfinite")
            with self.assertRaisesRegex(ValueError, "NONFINITE"):
                self.call(backend, folder)
            self.assertTrue((folder / "native_call.json").is_file())
            self.assertTrue((folder / "steps/000.f32").is_file())
            self.assertFalse(backend.model._forward_hooks)

    def test_backend_capture_budget_uses_verified_grammar_required_steps(self):
        backend = self.helper.backend()
        derived = r._backend_capture_budget(backend)
        grammar = r.capture.native_grammar(backend.tokenizer, backend.generation.eos_token_id, [0], backend.logit_width)
        self.assertEqual(derived, r.capture_budget(vocab=backend.logit_width, steps=grammar.required_tokens))
        self.assertLess(derived["per_sample_bytes"], r.capture_budget()["per_sample_bytes"])

    def test_locked_public_qwen2_tokenizer_proves_10_step_151936_bound_across_all_4_labels(self):
        from safeshift import internvl3763_campaign as c
        from safeshift.candidates.source import verify_snapshot
        from safeshift.internvl_grammar import LEVELS, POLICY
        from transformers import AutoTokenizer, GenerationConfig
        src = r.ROOT / "data/processed/internvl_v2_native/public-source"
        if not src.is_dir():
            self.skipTest("pinned local public-source snapshot not present")
        verify_snapshot(src, "internvl35")
        tok = AutoTokenizer.from_pretrained(str(src), local_files_only=True, trust_remote_code=False)
        self.assertEqual(len(tok), c.LOCKED_INTERNVL35_TOKENIZER_SIZE)
        gen_cfg = GenerationConfig(**{k: v for k, v in POLICY.items() if k != "batch_size"}, eos_token_id=[151645], pad_token_id=151645)
        # Prove prompt-independence and exact 10-step / 151936 geometry across distinct prompt lengths and all 4 labels.
        for prompt_ids in ([1], [151644, 8948, 198, 2610, 525, 1207, 16948]):
            grammar = r.capture.native_grammar(tok, [151645], prompt_ids, c.LOCKED_INTERNVL35_VOCAB)
            self.assertEqual(grammar.vocab, c.LOCKED_INTERNVL35_VOCAB)
            receipt = grammar.receipt()
            for key, expected in c.LOCKED_INTERNVL35_GRAMMAR_GEOMETRY.items():
                self.assertEqual(receipt[key], expected)
            cb = grammar.callback()
            for idx, label in enumerate(LEVELS):
                expected_tokens = [4913, 82, 38618, 8274, 3252, 4449, 15, 16 + idx, 9207, 151645]
                seq = list(prompt_ids)
                for step_num, tok_id in enumerate(expected_tokens):
                    allowed = cb(0, self.torch.tensor(seq, dtype=self.torch.long))
                    if step_num == 7:
                        self.assertEqual(allowed, [16, 17, 18, 19])
                    elif step_num == 9:
                        self.assertEqual(allowed, [151645])
                    else:
                        self.assertEqual(allowed, [tok_id])
                    seq.append(tok_id)
                # After EOS at step 9 (10th generated token), GenerationMixin halts on eos_token_id=151645 AND the trie
                # has zero outgoing transitions past EOS (fails closed with GRAMMAR_PREFIX_OUTSIDE_LANGUAGE)!
                with self.assertRaisesRegex(ValueError, "GRAMMAR_PREFIX_OUTSIDE_LANGUAGE"):
                    cb(0, self.torch.tensor(seq, dtype=self.torch.long))
                decoded = tok.decode(expected_tokens[:-1], skip_special_tokens=True, clean_up_tokenization_spaces=False)
                self.assertEqual(decoded, f'{{"safety_level":"{label}"}}')
                self.assertEqual(r.parse_label(decoded), label)
        derived = r._backend_capture_budget(NS(tokenizer=tok, generation=gen_cfg, logit_width=c.LOCKED_INTERNVL35_VOCAB))
        self.assertEqual(derived["per_sample_bytes"], 15378176)
        self.assertEqual(derived["sample_and_export_bytes"], 30756352)

    def test_verify_bundle_enforces_retained_f32_vectors_on_native_invalid_sample(self):
        from safeshift import internvl3763_campaign as c
        from safeshift.pilot.artifacts import export
        cohort = synthetic_cohort()
        cohort["scope"] = "PRIVATE_TRAIN_METADATA"
        p = c.plan(cohort, [], action="initial", run_id="inv-native", attempt_id="attempt-1",
            max_calls=1, max_seconds=600)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "bundle"
            sample = root / "run/samples/000000"
            backend = self.helper.backend()
            backend.evidence_kind = "NATIVE"
            decode = backend.tokenizer.decode
            def fenced(ids, **kwargs):
                text = decode(ids, **kwargs)
                return "```json\n" + text + "\n```" if (sample / "native.json").exists() else text
            binding = r.trace_binding(p["runtime_source"], p, cohort["samples"][0], "b"*64, digest(p))
            inputs = {"input_ids": self.torch.tensor([[8]]),
                "attention_mask": self.torch.ones((1, 1), dtype=self.torch.long)}
            with patch.object(r, "authorize", return_value={"scope": "SYNTHETIC_CLAIM_ONLY"}), \
                    patch.object(backend.tokenizer, "decode", fenced):
                res = r.generate_prepared(backend, inputs, sample, binding, time.monotonic() + 30, ordinal=0)
            self.assertEqual(res["status"], "INVALID")
            write(sample / "started.json", {"row": cohort["samples"][0], "plan_sha256": digest(p)})
            rec0 = {**cohort["samples"][0], **res, "attempts": 1, "native_calls": 1}
            write(sample / "result.json", rec0)
            records = [rec0] + [{**row, "status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0,
                "hnlo": None, "hnlo_status": r.HNLO_STATUS} for row in cohort["samples"][1:]]
            write(root / "run/source.json", p["runtime_source"])
            write(root / "run/plan.json", p)
            write(root / "run/configuration.json", r.configuration())
            write(root / "run/cohort.json", cohort)
            write(root / "run/summary.json", {
                "schema": r.IDENTITY + "-result", "plan_sha256": digest(p), "source_sha256": digest(p["runtime_source"]),
                "series_id": r.SERIES, "run_id": p["run_id"], "attempt_id": p["attempt_id"],
                "status": "PASS", "failure": None, "model_calls": 1, "planned": 3763,
                "counts": {"INVALID": 1, "NOT_ATTEMPTED": 3762}, "hnlo": None, "hnlo_status": r.HNLO_STATUS,
                "records": records, "scope": cohort["scope"], "scientific_selection": "PENDING", "scientific_qualified": False,
            })
            write(root / "execution-request.json", {"source": p["runtime_source"], "plan": p})
            write(root / "terminal.json", {"status": "PASS", "error": None})
            for sup in ("setup/setup-supervisor.json", "worker-supervisor.json"):
                write(root / sup, {"schema": "fresh-process-supervision-v1", "status": "EXITED",
                    "returncode": 0, "automatic_retry": False})
            write(root / "environment/preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS",
                "source_sha256": digest(p["runtime_source"])})
            for env_name in ("software.json", "hardware.json", "cuda.json", "allocation.json",
                             "checkpoint.json", "checkpoint-stream.json", "processor.json", "preload-resources.json"):
                write(root / "environment" / env_name, {"notice": "SYNTHETIC_ENV"})
            good_zip = Path(directory) / "good-invalid.zip"
            export(root, good_zip)
            self.assertEqual(r.verify_bundle(good_zip, sha(good_zip), p)["counts"], {"INVALID": 1, "NOT_ATTEMPTED": 3762})

            # Truncating a retained .f32 inside an INVALID native sample must fail closed even if checksums.json is resealed!
            (root / "checksums.json").unlink()
            (sample / "steps/000.f32").write_bytes(b"\x00" * 8)
            raw_obj = read(sample / "raw.json")
            raw_obj["raw_vector_hashes"][0] = sha(sample / "steps/000.f32")
            (sample / "raw.json").unlink()
            rec0["raw_sha256"] = write(sample / "raw.json", raw_obj)
            (sample / "result.json").unlink()
            write(sample / "result.json", rec0)
            summary_obj = read(root / "run/summary.json")
            summary_obj["records"][0] = rec0
            (root / "run/summary.json").unlink()
            write(root / "run/summary.json", summary_obj)
            bad_zip = Path(directory) / "bad-invalid.zip"
            export(root, bad_zip)
            with self.assertRaisesRegex(ValueError, "FULL_VOCAB_BINARY_SIZE"):
                r.verify_bundle(bad_zip, sha(bad_zip), p)


if __name__ == "__main__":
    unittest.main()
