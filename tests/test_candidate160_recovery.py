"""Synthetic CPU recovery only. No GPU, real images, weights or predictions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import copy
import errno
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_history as h
from safeshift.candidates import train_owner as owner, train_run as run, train_runtime as rt
from safeshift.candidates.source import ROOT
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, write, sha, export, verify_archive
from safeshift.pilot.contract import digest
from test_candidate160 import fixture, Scripted, raw


class StopAfter(Scripted):
    def __init__(self, n, **kwargs):
        super().__init__(**kwargs)
        self.n = n

    def generate(self, image, sample):
        if self.calls == self.n:
            self.fault = RuntimeError("SYNTHETIC CUDA out of memory")
        return super().generate(image, sample)


def start(work, inputs, key="internvl35", *, action="resume"):
    output = work / (key + "-" + __import__("uuid").uuid4().hex)
    output.mkdir()
    index = h.collect(work, inputs, output, key)
    g = h.execution(key, "c"*64, "a"*40, index, owner_start=True, action=action)
    write(output / "owner_execution.json", g)
    return output, g


def calls(output, g, plan, rows, factory, **kwargs):
    write(output / "recovery_plan.json", h.recovery_plan(output, rows, g))
    return run.run_calls(output, plan, rows, factory, g, resources=lambda: {}, **kwargs)


class RecoveryTests(unittest.TestCase):
    def layout(self, root):
        work, inputs = root / "out", root / "input"
        work.mkdir()
        inputs.mkdir()
        return work, inputs

    def test_oom_then_resume_then_noop_and_explicit_full_rerun_both_models(self):
        for key in c.KEYS:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                work, inputs = self.layout(root)
                first, g1 = start(work, inputs, key)
                backend = StopAfter(2, key=key)
                results, reason = calls(first, g1, plan, rows, lambda: backend)
                self.assertEqual(backend.calls, 3)
                self.assertIsNotNone(reason)
                before = h.members(first)
                second, g2 = start(work, inputs, key)
                self.assertNotEqual(g1["attempt_id"], g2["attempt_id"])
                self.assertEqual(g2["run_kind"], "RECOVERY")
                native = Scripted(key=key)
                result, reason = calls(second, g2, plan, rows, lambda: native)
                self.assertIsNone(reason)
                self.assertEqual(native.calls, 158)
                self.assertNotIn(Path(rows[0]["image"]).name, native.ids)
                self.assertEqual(h.members(first), before)
                accounting = read(second / "lineage_accounting.json")["samples"]
                self.assertEqual(accounting[2]["attempts_all_runs"], 2)
                self.assertEqual(accounting[2]["native_calls_all_runs"], 2)
                third, g3 = start(work, inputs, key)
                pending = h.recovery_plan(third, rows, g3)
                self.assertEqual(pending["pending_ordinals"], [])
                calls(third, g3, plan, rows, lambda: self.fail("NO_LOAD_ON_COMPLETE_RESUME"))
                fourth, g4 = start(work, inputs, key, action="rerun")
                new = Scripted(key=key, value=raw("Level04"))
                calls(fourth, g4, plan, rows, lambda: new)
                self.assertEqual(new.calls, 160)
                self.assertEqual(g4["run_kind"], "FULL_RERUN")
                self.assertEqual(read(fourth / "summary.json")["scientific_selection"], "PENDING")
                self.assertFalse(read(fourth / "summary.json")["pooling_allowed"])
                # Two valid outputs are both retained, with no preferred label.
                fifth, g5 = start(work, inputs, key)
                projection = h.recovery_plan(fifth, rows, g5)
                self.assertEqual(projection["pending_ordinals"], [])
                self.assertEqual(sum(v["durable_completion"] for v in projection["lineage"][rows[0]["sample_id"]]), 2)
                self.assertNotIn("selected_result", projection)
                sixth, g6 = start(work, inputs, key, action="rerun")
                interrupted = StopAfter(1, key=key)
                calls(sixth, g6, plan, rows, lambda: interrupted)
                seventh, g7 = start(work, inputs, key)
                continuation = h.recovery_plan(seventh, rows, g7)
                self.assertEqual(g7["series_id"], g6["series_id"])
                self.assertNotEqual(g7["series_id"], g4["series_id"])
                self.assertEqual(continuation["already_durable_ordinals"], [0])
                self.assertEqual(len(continuation["pending_ordinals"]), 159)

    def test_model_load_failure_can_start_another_attempt_without_manual_grant(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            work, inputs = self.layout(root)
            first, g = start(work, inputs)
            def failed_load():
                raise RuntimeError("SYNTHETIC model load out of memory")
            result, reason = calls(first, g, plan, rows, failed_load)
            self.assertIsNotNone(reason)
            self.assertEqual(sum(v["native_calls"] for v in result.values()), 0)
            self.assertEqual(read(first / "model_load_attempt.json")["load_attempts"], 1)
            second, retry = start(work, inputs)
            self.assertEqual(len(h.recovery_plan(second, rows, retry)["pending_ordinals"]), 160)
            native = StopAfter(0)
            calls(second, retry, plan, rows, lambda: native)
            self.assertEqual(native.calls, 1)  # stop, no automatic retry loop

    def test_raw_write_failure_preserves_partial_and_retries_only_failed_or_unfinished(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            work, inputs = self.layout(root)
            first, g = start(work, inputs)
            with patch.object(run.CandidateStore, "raw", side_effect=OSError(errno.ENOSPC, "SYNTHETIC")):
                result, reason = calls(first, g, plan, rows, lambda: Scripted())
            self.assertEqual(result[rows[0]["sample_id"]]["native_calls"], 1)
            before = h.members(first)
            second, retry = start(work, inputs)
            projection = h.recovery_plan(second, rows, retry)
            self.assertEqual(len(projection["pending_ordinals"]), 160)
            self.assertEqual(projection["lineage"][rows[0]["sample_id"]][0]["native_calls"], 1)
            self.assertEqual(h.members(first), before)

    def test_hard_kill_raw_without_result_is_replayed_and_invalid_is_completed(self):
        for invalid in (False, True):
            with self.subTest(invalid=invalid), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                work, inputs = self.layout(root)
                first, g = start(work, inputs)
                value = raw("Level01")
                if invalid:
                    value["response"] = "SYNTHETIC INVALID"
                calls(first, g, plan, rows, lambda: StopAfter(1, value=value))
                # Simulate loss of a result and finalization after durable raw.
                (first / "calls/000000/run/samples/000000/result.json").unlink()
                before = h.members(first)
                second, retry = start(work, inputs)
                projection = h.recovery_plan(second, rows, retry)
                self.assertEqual(projection["already_durable_ordinals"], [0])
                self.assertNotIn(0, projection["pending_ordinals"])
                self.assertTrue(projection["lineage"][rows[0]["sample_id"]][0]["durable_completion"])
                self.assertEqual(h.members(first), before)

    def test_new_kaggle_session_directory_or_zip_import_dedup_and_two_generations(self):
        for zipped in (False, True):
            with self.subTest(zipped=zipped), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                oldwork, inputs = self.layout(root)
                first, g = start(oldwork, inputs)
                calls(first, g, plan, rows, lambda: StopAfter(1))
                archive = Path(str(first) + ".zip")
                export(first, archive)
                verify_archive(archive)
                original = h.members(first)
                mount = inputs / "notebooks/owner/prior"
                mount.mkdir(parents=True)
                if zipped:
                    shutil.copyfile(archive, mount / archive.name)
                    shutil.copyfile(Path(str(archive)+".sha256.json"), mount / (archive.name+".sha256.json"))
                else:
                    shutil.copytree(oldwork, mount / "data/processed/candidate160")
                work = root / "newwork"
                work.mkdir()
                second, g2 = start(work, inputs)
                projection = h.recovery_plan(second, rows, g2)
                self.assertEqual(projection["already_durable_ordinals"], [0])
                self.assertEqual(len(read(second / "history_index.json")["runs"]), 1)
                calls(second, g2, plan, rows, lambda: StopAfter(1))
                nextwork = root / "thirdwork"
                nextwork.mkdir()
                shutil.copytree(work, inputs / "next/data/processed/candidate160")
                third, g3 = start(nextwork, inputs)
                projection = h.recovery_plan(third, rows, g3)
                self.assertEqual(projection["already_durable_ordinals"], [0, 1])
                self.assertEqual(len(read(third / "history_index.json")["runs"]), 2)
                self.assertEqual(h.members(first), original)

    def test_legacy_blocked_consumed_and_replacement1_are_not_permanent_locks(self):
        for status, replacement in (("BLOCKED_RESERVED_NO_RETRY", False), ("CONSUMED", False), ("CONSUMED", True)):
            with self.subTest(status=status, replacement=replacement), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                work, inputs = self.layout(root)
                old = work / ("internvl35-" + "b"*32)
                old.mkdir()
                g = owner.execution("internvl35", "c"*64, "a"*40, owner_start=True)
                write(old / "owner_execution.json", g)
                terminal = {"status": status, "run_id": g["run_id"], "attempt_id": g["attempt_id"],
                    "execution_sha256": digest(g), "attempt_consumed": status == "CONSUMED"}
                write(old / "owner_consumption_log.json", terminal)
                attempts = work / "attempts"
                attempts.mkdir()
                filename = "owner_slot_" + g["slot_sha256"] + (".replacement1.json" if replacement else ".json")
                write(attempts / filename, terminal)
                before = h.members(old)
                new, retry = start(work, inputs)
                self.assertEqual(len(h.recovery_plan(new, rows, retry)["pending_ordinals"]), 160)
                self.assertEqual(h.members(old), before)
                self.assertEqual(read(attempts / filename), terminal)

    def test_missing_conflicting_tampered_history_blocks_before_any_model_load(self):
        for fault in ("orphan", "copy_conflict", "seal", "native_without_start", "plan_changed", "ancestor_missing", "consumption"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                work, inputs = self.layout(root)
                if fault == "orphan":
                    marker = work / ("attempts/owner_slot_" + owner.slot("internvl35") + ".consumed.json")
                    write(marker, {"run_id": "missing"})
                    with self.assertRaisesRegex(ValueError, "HISTORY_MISSING"):
                        start(work, inputs)
                    continue
                first, g = start(work, inputs)
                calls(first, g, plan, rows, lambda: StopAfter(1))
                if fault == "copy_conflict":
                    copydir = inputs / "prior"
                    shutil.copytree(first, copydir)
                    write(copydir / "extra.json", {"conflict": True})
                elif fault == "seal":
                    export(first, Path(str(first)+".zip"))
                    (first / "model_load_attempt.json").write_bytes(b"CORRUPTED_SYNTHETIC")
                elif fault == "native_without_start":
                    (first / "calls/000000/run/samples/000000/started.json").unlink()
                elif fault == "consumption":
                    write(first / "owner_consumption_log.json", {"run_id": g["run_id"], "attempt_id": g["attempt_id"],
                        "execution_sha256": digest(g), "attempt_consumed": False})
                    write(first / "consumption.json", {"attempt_consumed": True, "attempt_id": g["attempt_id"]})
                if fault in ("copy_conflict", "seal", "consumption"):
                    with self.assertRaisesRegex(ValueError, "HISTORY_CONFLICTING|HISTORY_SEAL|HISTORY_CONTRADICTORY"):
                        start(work, inputs)
                else:
                    second, retry = start(work, inputs)
                    if fault == "ancestor_missing":
                        (second / "history" / g["run_id"] / "owner_execution.json").unlink()
                    if fault == "plan_changed":
                        write(second / "recovery_plan.json", {"pending_ordinals": []})
                    with self.assertRaisesRegex(ValueError, "HISTORY_NATIVE|RECOVERY_HISTORY_CHANGED|RECOVERY_PLAN_CHANGED"):
                        if fault == "plan_changed":
                            run.run_calls(second, plan, rows, lambda: self.fail("NO_LOAD"), retry, resources=lambda: {})
                        else:
                            h.recovery_plan(second, rows, retry)

    def test_kernel_lock_excludes_threads_and_releases_after_abrupt_process_exit(self):
        with tempfile.TemporaryDirectory() as d:
            work = Path(d)
            with h.lease(work, "internvl35"):
                def contender():
                    with self.assertRaisesRegex(FileExistsError, "ACTIVE_PROCESS"):
                        with h.lease(work, "internvl35"):
                            self.fail("DUPLICATE")
                with ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(contender).result()
            code = ("from safeshift.candidates.train_history import lease; import os,sys; "
                    "lock=lease(sys.argv[1], 'internvl35'); lock.__enter__(); os._exit(0)")
            subprocess.run([sys.executable, "-B", "-c", code, d], cwd=ROOT, check=True, timeout=20)
            with h.lease(work, "internvl35"):
                pass

    def test_execution_scope_and_action_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            work, inputs = self.layout(Path(d))
            output, g = start(work, inputs)
            c.authorize(g, g["model_key"], g["source_sha256"], g["runtime_ref"], None)
            for field, value in (("scientific_selection", "BEST"), ("resume", False),
                    ("recovery_action", "loop"), ("max_native_calls", 161),
                    ("manifest_sha256", "0"*64), ("owner_decision_record", "fake")):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    h.validate({**g, field: value}, g["model_key"], g["source_sha256"], g["runtime_ref"])

    def test_worker_cli_accepts_new_execution_without_grant_or_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, inputs = self.layout(root)
            output, g = start(work, inputs)
            command = ["candidate160"]
            for name in ("repo", "output", "bundle", "snapshot", "weights", "source", "ref"):
                command += ["--"+name, str(ROOT if name == "repo" else output)]
            command += ["--execution", str(output / "owner_execution.json"), "--check-only"]
            with patch.object(sys, "argv", command), patch.object(rt, "worker") as worker:
                rt.main()
            self.assertEqual(worker.call_args.args[5], g)
            self.assertIsNone(worker.call_args.args[6])

    def test_pre_execution_blocked_archive_does_not_permanently_lock_next_start(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, inputs = self.layout(root)
            failed = work / ("internvl35-" + "a"*32)
            write(failed / "supervisor_status.json", {"attempt_consumed": False, "model_key": "internvl35",
                "status": "BLOCKED", "stage": "authority", "failure": {"scope": "SYNTHETIC"}})
            export(failed, Path(str(failed)+".zip"))
            previous = h.members(failed)
            output, g = start(work, inputs)
            index = read(output / "history_index.json")
            self.assertEqual(index["runs"], {})
            self.assertEqual(len(index["diagnostics"]), 1)
            self.assertEqual(g["run_kind"], "INITIAL")
            self.assertEqual(h.members(failed), previous)

    @unittest.skipIf(os.name == "nt", "Linux Kaggle inherited-descriptor contract")
    def test_worker_keeps_kernel_lock_after_supervisor_death(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            worker = ("import pathlib,sys,time; root=pathlib.Path(sys.argv[1]); "
                      "(root/'ready').touch(); "
                      "exec(\"while not (root/'release').exists(): time.sleep(.01)\")")
            supervisor = ("import os,sys,subprocess; from safeshift.candidates.train_history import lease; "
                "lock=lease(sys.argv[1],'internvl35'); options=lock.__enter__(); "
                "subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[1]], **options); os._exit(0)")
            subprocess.run([sys.executable, "-B", "-c", supervisor, d, worker], cwd=ROOT, check=True, timeout=20)
            end = time.monotonic() + 10
            while not (root / "ready").exists() and time.monotonic() < end:
                time.sleep(.01)
            self.assertTrue((root / "ready").exists())
            try:
                with self.assertRaisesRegex(FileExistsError, "ACTIVE_PROCESS"):
                    with h.lease(root, "internvl35"):
                        self.fail("WORKER_STILL_ACTIVE")
            finally:
                (root / "release").touch()
            while True:
                try:
                    with h.lease(root, "internvl35"):
                        break
                except FileExistsError:
                    self.assertLess(time.monotonic(), end)
                    time.sleep(.01)

    def test_direct_history_manifest_is_not_mistaken_for_live_image_bundle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root / "bundle/pilot_manifest.json", {"scope": "SYNTHETIC"})
            write(root / "old/pilot_manifest.json", {"scope": "SYNTHETIC HISTORY"})
            write(root / "old/owner_execution.json", {"scope": "SYNTHETIC HISTORY"})
            self.assertEqual(discover(root, "pilot_manifest.json"), root / "bundle/pilot_manifest.json")

    def test_divergent_history_heads_do_not_implicitly_choose_a_run(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            work, inputs = self.layout(root)
            first, g1 = start(work, inputs)
            # Model two independent VMs with the same visible parent.
            modern = {"schema": h.SCHEMA, "series_id": g1["series_id"], "ancestors": []}
            index = {"runs": {"left": modern, "right": modern}}
            with self.assertRaisesRegex(ValueError, "DIVERGENT_HEADS"):
                h.execution("internvl35", "c"*64, "a"*40, index, owner_start=True)
            value = h.execution("internvl35", "c"*64, "a"*40, index, owner_start=True, action="rerun")
            self.assertEqual(value["series_id"], value["run_id"])

    def test_supervisor_v2_gpu_load_interrupt_retry_noop_and_export_both_models(self):
        for key in c.KEYS:
            for fault in ("gpu", "load", "interrupt", "raw"):
                with self.subTest(key=key, fault=fault), tempfile.TemporaryDirectory() as d, ExitStack() as stack:
                    root = Path(d)
                    bundle = root / "input/bundle"
                    bundle.mkdir(parents=True)
                    plan, rows = fixture(bundle)
                    write(bundle / "pilot_manifest.json", plan)
                    stack.enter_context(patch.object(c, "MANIFEST", sha(bundle / "pilot_manifest.json")))
                    stack.enter_context(patch.object(rt, "MANIFEST", c.MANIFEST))
                    stack.enter_context(patch.object(rt, "checkpoint", return_value=(bundle / "marker", bundle, bundle)))
                    stack.enter_context(patch.object(rt, "verify_weights", return_value={"scope": "SYNTHETIC"}))
                    stack.enter_context(patch.object(rt, "stage_snapshot", return_value={"scope": "SYNTHETIC"}))
                    scratch = root / "scratch"
                    scratch.mkdir()
                    stack.enter_context(patch.object(rt.boot, "provision_scratch_root", return_value=scratch))
                    stack.enter_context(patch.object(rt.boot, "storage_admission", return_value={"admitted": True}))
                    setup = stack.enter_context(patch.object(rt, "prepare_runtime", return_value=(Path(sys.executable), {})))
                    current = [fault]
                    def hardware(_):
                        if current[0] == "gpu":
                            raise RuntimeError("SYNTHETIC GPU unavailable")
                        return {"scope": "SYNTHETIC"}
                    stack.enter_context(patch.object(rt, "hardware", side_effect=hardware))
                    generated = []
                    def child(command, **kwargs):
                        out = Path(command[command.index("--output")+1])
                        if os.name != "nt":
                            self.assertEqual(len(kwargs["pass_fds"]), 1)
                        if "--check-only" in command:
                            return
                        if "--cuda-check-only" in command:
                            write(out / "preledger_cuda.json", {"worker_cuda": "MEASURED_FP16_FUNCTIONAL"})
                            return
                        g = read(out / "owner_execution.json")
                        self.assertEqual(g["schema"], h.SCHEMA)
                        c.authorize(g, key, g["source_sha256"], g["runtime_ref"], None)
                        native = StopAfter(2, key=key) if current[0] == "interrupt" else Scripted(key=key)
                        def factory():
                            if current[0] == "load":
                                raise RuntimeError("SYNTHETIC load failure")
                            return native
                        with ExitStack() as local:
                            if current[0] == "raw":
                                local.enter_context(patch.object(run.CandidateStore, "raw", side_effect=OSError(errno.ENOSPC, "SYNTHETIC")))
                            run.run_calls(out, plan, rows, factory, g, resources=lambda: {})
                        generated.append(native.calls)
                    stack.enter_context(patch.object(rt.subprocess, "run", side_effect=child))
                    source = c.source_hash()
                    first = rt.launch_owner(key, source, ROOT, "a"*40, owner_start=True,
                        inputs=root / "input", work=root / "out", scratch_root=scratch)
                    first_hashes = h.members(first)
                    verify_archive(Path(str(first)+".zip"))
                    current[0] = None
                    second = rt.launch_owner(key, source, ROOT, "a"*40, owner_start=True,
                        inputs=root / "input", work=root / "out", scratch_root=scratch)
                    self.assertEqual(read(second / "supervisor_status.json")["status"], "CONSUMED_REVIEW_EVIDENCE")
                    self.assertEqual(generated[-1], 158 if fault == "interrupt" else 160)
                    self.assertEqual(h.members(first), first_hashes)
                    verify_archive(Path(str(second)+".zip"))
                    setup.reset_mock()
                    third = rt.launch_owner(key, source, ROOT, "a"*40, owner_start=True,
                        inputs=root / "input", work=root / "out", scratch_root=scratch)
                    self.assertEqual(read(third / "supervisor_status.json")["status"], "ALREADY_DURABLE_NO_WORK")
                    setup.assert_not_called()
                    self.assertFalse((third / "consumption.json").exists())
                    verify_archive(Path(str(third)+".zip"))


if __name__ == "__main__":
    unittest.main()
