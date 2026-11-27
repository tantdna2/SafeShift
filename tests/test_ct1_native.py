"""CPU-only regressions for the CT1 production path. All payloads are synthetic."""

import base64
from collections import Counter
from contextlib import nullcontext
from io import BytesIO
from itertools import permutations
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from safeshift.data.saved_reports import json_bytes, sha256
from safeshift.evaluation.ct1_contract import ARMS
from safeshift.evaluation.ct1_pilot import replay
from safeshift.fulltrain import ct1_run, ct1_native, provision, qwen
from safeshift.pilot.artifacts import export, sha, verify_archive, write, write_bytes
from scripts import build_ct1_kaggle_notebooks as nb
from scripts import run_ct1_native_pilot as controller
from scripts import submit_ct1_smoke as operator


class FixtureBackend:
    """Injected by tests only. Used to exercise the normal journal and export."""
    def __init__(self, before=None, after=None):
        self.calls = []
        self.before, self.after = before, after

    def generate(self, payload, arm, begin, record_tokens):
        self.calls.append(arm)
        if self.before:
            self.before()
        begin({"prompt_tokens": 7, "max_new_tokens": 768, "memory_before": {}})
        record_tokens({"input_ids": [1], "returned_ids": [[1, 2]], "seconds": 0.0})
        if self.after:
            self.after()
        level = "Level01"
        text = {"safety_level": level}
        if arm != "A":
            text.update(evidence_status="INSUFFICIENT", evidence=[])
        return {"raw_text": json.dumps(text), "at_cap": False, "eos": True, "new_tokens": 1}, {}

    def decode(self, tokens):
        return {"raw_text": '{"safety_level":"Level02"}', "at_cap": False, "eos": True, "new_tokens": 1}

    def failure_memory(self):
        return {"fixture": True}


class NativeTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "pilot"
        self.data.mkdir()
        (self.data / "images").mkdir()
        self.exclusions = sorted(sha256(f"audit-{i}".encode()) for i in range(32))
        self.plan = {"kind": "TRAIN_DEVELOPMENT", "arms": list(ARMS), "cases": []}
        for i in range(48):
            case = f"p-{i:012x}"
            payload = f"opaque case bytes {i}".encode()
            write_bytes(self.data / "images" / (case + ".png"), payload)
            self.plan["cases"].append({"case_id": case, "image_sha256": sha256(payload)})
        self.plan_sha = write_bytes(self.data / "plan.json", json_bytes(self.plan))
        write_bytes(self.data / "exclusions.json", json_bytes(self.exclusions))
        self.binding = ct1_run.identity(self.plan_sha, "a" * 64, "b" * 64, "c" * 64, "ct1-000000000000")
        self.patch = patch("safeshift.evaluation.ct1_pilot.EXCLUSIONS_SHA256",
                           sha256(json_bytes(self.exclusions)))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    @staticmethod
    def receipt(status="EXITED", **changes):
        return {"schema": "fresh-process-supervision-v1", "status": status,
                "returncode": 0, "group_kill_sent": True,
                "group_exit": {"status": "NO_LIVE_MEMBERS", "members": []}, **changes}

    def config_value(self, **changes):
        return {"run_id": self.binding["run_id"], "mode": "pilot", "source_commit": "a" * 40,
                "source_capsule_sha256": "b" * 64, "plan_sha256": self.plan_sha,
                "software_marker_sha256": "c" * 64, "approved_drivers": ["570.26"],
                "observed_driver": "570.26", "resume": None, "pilot_input": str(self.data),
                "software_input": str(self.root / "software"),
                "checkpoint": str(self.root / ct1_run.REVISION), **changes}

    def evidence(self, name, *, mode="pilot", binding=None):
        out = self.root / name
        out.mkdir()
        write(out / "identity.json", binding or self.binding)
        write(out / "config-summary.json", {"mode": mode})
        write(out / "resume-admission.json", {"status": "FRESH_ADMITTED"})
        for name in ct1_run.PROCESS_RECEIPTS:
            write(out / name, self.receipt())
        return out

    def run_it(self, out, backend, *, seconds=60):
        return ct1_run.execute(out, self.plan, self.binding, self.data / "images", backend,
                              time.monotonic() + seconds)

    def test_exact_opaque_cohort_and_balanced_order(self):
        ct1_run.admit(self.data, self.plan_sha)
        rows = ct1_run.schedule(self.plan)
        self.assertEqual(len(rows), 144)
        by_image = Counter(tuple(r[1] for r in rows[i:i + 3]) for i in range(0, len(rows), 3))
        self.assertEqual(by_image, dict.fromkeys(permutations(ARMS), 8))
        (self.data / "truth.json").touch()
        with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
            ct1_run.admit(self.data, self.plan_sha)

    def test_input_and_exclusions_tampering(self):
        with self.assertRaises(ValueError):
            ct1_run.admit(self.data, "d" * 64)
        p = self.data / "images" / (self.plan["cases"][0]["case_id"] + ".png")
        p.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "IMAGE_SEAL"):
            ct1_run.admit(self.data, self.plan_sha)

    def test_export_replay_all_144(self):
        output = self.evidence("good")
        fake = FixtureBackend()
        self.run_it(output, fake)
        self.assertEqual(len(fake.calls), 144)
        archive = self.root / "good.zip"
        ct1_run.checkpoint_results(output, archive, self.plan, self.binding)
        members = verify_archive(archive)
        self.assertIn("runs.json", members)
        self.assertNotIn("images", members)
        runs = json.loads((output / "runs.json").read_bytes())
        decoded = replay(self.plan, runs, self.plan_sha, self.exclusions)
        self.assertEqual(Counter(r["status"] for r in decoded.values()), {"SUCCESS": 144})
        self.run_it(output, fake)
        self.assertEqual(len(fake.calls), 144)

    def test_timeout_resume_does_not_repeat_ambiguous_intent(self):
        output = self.evidence("broken")
        first = FixtureBackend(after=lambda: (_ for _ in ()).throw(RuntimeError("fixture timeout")))
        with self.assertRaises(RuntimeError):
            self.run_it(output, first)
        self.assertEqual(len(first.calls), 1)
        archive = self.root / "broken.zip"
        ct1_run.checkpoint_results(output, archive, self.plan, self.binding)
        partial = json.loads((output / "summary.json").read_bytes())
        self.assertEqual((partial["durable_native_intents"], partial["not_attempted"]), (1, 143))
        recovered = self.evidence("resume")
        with self.assertRaisesRegex(ValueError, "ZIP_SEAL"):
            ct1_run.restore(archive, "0" * 64, recovered, self.binding)
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            ct1_run.restore(archive, sha(archive), recovered, {**self.binding, "max_calls": 143})
        ct1_run.restore(archive, sha(archive), recovered, self.binding)
        backend = FixtureBackend()
        self.run_it(recovered, backend)
        self.assertEqual(len(backend.calls), 143)
        self.assertTrue((recovered / "calls/000/failure.json").is_file())
        self.assertTrue((recovered / "calls/000/tokens.json").is_file())
        self.assertEqual(json.loads((recovered / "calls/000/result.json").read_bytes())["level"], "Level02")

    def test_no_native_when_expired_or_preprocessing_failed(self):
        output = self.evidence("early")
        fake = FixtureBackend()
        self.run_it(output, fake, seconds=-1)
        self.assertFalse(fake.calls)
        fake.before = lambda: (_ for _ in ()).throw(ValueError("invalid image"))
        with self.assertRaisesRegex(ValueError, "invalid image"):
            self.run_it(output, fake)
        self.assertFalse((output / "calls/000/intent.json").exists())
        self.assertTrue((output / "calls/000/failure.json").exists())

    def test_raw_exists_before_parsing_and_checksum_is_enforced(self):
        out = self.evidence("raw")
        invokes = []
        actual = ct1_run._parsed
        def observed(arm, row):
            if not invokes:
                self.assertTrue((out / "calls/000/raw.json").exists())
            invokes.append(arm)
            return actual(arm, row)
        with patch.object(ct1_run, "_parsed", side_effect=observed):
            self.run_it(out, FixtureBackend())
        self.assertEqual(len(invokes), 144)
        (out / "calls/000/tokens.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "TOKEN_BINDING"):
            ct1_run.checkpoint_results(out, self.root / "invalid.zip", self.plan, self.binding)

    def test_old_or_missing_checkpoint_cannot_start_a_new_vm(self):
        parent = self.root / "old.zip"
        older = self.evidence("old")
        ct1_run.checkpoint_results(older, parent, self.plan, self.binding)
        digest = sha(parent)
        for i, resume in enumerate(({"path": str(parent), "sha256": digest},
                                    {"path": "missing", "sha256": "0" * 64}, {})):
            config = self.root / f"resume-{i}.json"
            write(config, self.config_value(resume=resume))
            job = self.root / f"restart-{i}"
            with patch.object(controller, "layout") as layout:
                with self.assertRaisesRegex(ValueError, "CROSS_VM_RESUME_BLOCKED"):
                    controller.supervise(SimpleNamespace(config=config, job=job))
                layout.assert_not_called()
            self.assertFalse(job.exists())
        self.assertEqual(sha(parent), digest)

    def test_missing_stability_proof_and_truncated_archive_are_rejected(self):
        older = self.evidence("legacy")
        ct1_run.reconstruct(older, self.plan, self.binding)
        old = self.root / "legacy.zip"
        export(older, old)
        rejected = self.root / "rejected"
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_STABILITY_REQUIRED"):
            ct1_run.restore(old, sha(old), rejected, self.binding)
        truncated = self.root / "truncated.zip"
        truncated.write_bytes(old.read_bytes()[:-12])
        with self.assertRaisesRegex(ValueError, "RESUME_ZIP_SEAL"):
            ct1_run.restore(truncated, sha(old), rejected, self.binding)
        self.assertFalse(rejected.exists())

    def test_missing_worker_receipt_after_vm_loss_exports_only_diagnostics(self):
        root = self.evidence("interrupted")
        (root / "worker-supervisor.json").unlink()
        archive = self.root / "interrupted.zip"
        with patch.object(ct1_run, "reconstruct") as reconstruct:
            self.assertEqual(controller.export_job(root, archive, self.plan, self.binding, "pilot"),
                             "FORENSIC_ONLY")
            reconstruct.assert_not_called()
        self.assertFalse(archive.exists())
        diagnostic = self.root / "interrupted-diagnostic.zip"
        self.assertIn("setup-supervisor.json", verify_archive(diagnostic))
        self.assertNotIn("checkpoint-stability.json", verify_archive(diagnostic))
        with self.assertRaisesRegex(ValueError, "FORENSIC_ARCHIVE_NOT_RESUMABLE"):
            ct1_run.restore(diagnostic, sha(diagnostic), self.root / "restore", self.binding)

    def test_supervisor_cleanup_blockers_never_read_or_seal_the_ledger(self):
        for where, status in (("worker", "PROCESS_GROUP_SURVIVORS"),
                              ("setup", "PROCESS_GROUP_CLEANUP_UNVERIFIED")):
            with self.subTest(stage=where, status=status):
                work = self.root / where
                work.mkdir()
                scratch = work / "scratch"
                scratch.mkdir()
                cfg = self.config_value()
                config = work / "settings.json"
                write(config, cfg)
                job = work / cfg["run_id"]
                root = job / "evidence"
                calls = []

                def run(command, *, receipt, **kwargs):
                    stage = command[4]
                    calls.append(stage)
                    failure = stage == where
                    group_exit = ({"status": "LIVE_SURVIVORS", "members": [{"pid": 123, "state": "S"}]}
                                  if stage == "worker" else {"status": "UNVERIFIED"})
                    row = self.receipt(status, group_exit=group_exit) if failure else self.receipt()
                    write(receipt, row)
                    if failure:
                        write_bytes(root / "calls/000/intent.json", b"{")
                        raise RuntimeError("SUPERVISED_" + status)
                    return {"status": "EXITED", "returncode": 0}

                with (patch.object(controller, "WORK", work), patch.object(controller.sys, "platform", "linux"),
                      patch.object(controller, "require_native_admission"),
                      patch.object(controller, "layout", return_value=(self.data, work, work, {}, self.plan)),
                      patch.object(controller.tempfile, "mkdtemp", return_value=str(scratch)),
                      patch.object(controller.provision, "clean_env", return_value={}),
                      patch.object(controller.supervision, "run", side_effect=run),
                      patch.object(controller.supervision, "parent_deadline", return_value=nullcontext()),
                      patch.object(ct1_run, "reconstruct") as reconstruct):
                    controller.supervise(SimpleNamespace(config=config, job=job))
                    reconstruct.assert_not_called()
                self.assertEqual(calls, ["setup", where] if where == "worker" else ["setup"])
                self.assertEqual((root / "calls/000/intent.json").read_bytes(), b"{")
                archive = work / (cfg["run_id"] + "-diagnostic.zip")
                members = verify_archive(archive)
                self.assertIn(where + "-supervisor.json", members)
                self.assertNotIn("checkpoint-stability.json", members)
                self.assertFalse(any(name.startswith("calls/") for name in members))
                evidence = json.loads((job / "diagnostic/diagnostic-status.json").read_bytes())
                self.assertFalse(evidence["budget_release"])
                self.assertFalse(evidence["resumable"])
                self.assertFalse((work / (cfg["run_id"] + ".zip")).exists())
                with self.assertRaisesRegex(ValueError, "FORENSIC_ARCHIVE_NOT_RESUMABLE"):
                    ct1_run.restore(archive, sha(archive), work / "restore", self.binding)

    def test_technical_smoke_shares_the_pipeline_without_a_scoring_export(self):
        cfg = self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                                operator_request_sha256="f" * 64)
        software = self.root / "software"
        software.mkdir()
        cfg["software_marker_sha256"] = write(software / "fresh_qwen_software.json", {"runtime_lock": {}})
        with patch.object(controller, "mount_path", side_effect=lambda value, **_: Path(value)):
            _, _, _, lock, plan = controller.layout(cfg)
        self.assertEqual(plan["cases"], self.plan["cases"][:1])
        binding = controller.binding(cfg, lock)
        self.assertEqual(binding["max_calls"], 3)
        root = self.evidence("smoke", mode="smoke", binding=binding)
        fake = FixtureBackend()
        deadline = time.monotonic() + 60
        with self.assertRaisesRegex(ValueError, "CALL_PLAN_MISMATCH"):
            ct1_run.execute(root, self.plan, binding, self.data / "images", fake, deadline)
        self.assertFalse(fake.calls)
        ct1_run.execute(root, plan, binding, self.data / "images", fake, deadline)
        self.assertEqual(fake.calls, ["A", "E", "S"])
        archive = self.root / "smoke.zip"
        controller.export_job(root, archive, plan, binding, "smoke")
        members = verify_archive(archive)
        self.assertIn("smoke-runs.json", members)
        self.assertIn("calls/002/raw.json", members)
        self.assertNotIn("runs.json", members)
        with self.assertRaises(ValueError):
            replay(self.plan, json.loads((root / "smoke-runs.json").read_bytes()), self.plan_sha, self.exclusions)
        with self.assertRaisesRegex(ValueError, "RESUME_PILOT_ONLY"):
            ct1_run.restore(archive, sha(archive), self.root / "restore", binding)

    def test_atomic_journal_cut_points_export_and_do_not_repeat_call(self):
        for record in ("intent", "tokens", "raw", "result"):
            with self.subTest(record=record):
                out = self.evidence(record)
                real_write = ct1_run.write_bytes

                def torn_write(path, payload):
                    if path.name.startswith(f".{record}.json."):
                        real_write(path, b"{")
                        raise RuntimeError("fixture torn write")
                    return real_write(path, payload)

                with patch.object(ct1_run, "write_bytes", side_effect=torn_write):
                    with self.assertRaisesRegex(RuntimeError, "torn write"):
                        self.run_it(out, FixtureBackend())
                self.assertFalse((out / "calls/000" / f"{record}.json").exists())
                archive = self.root / f"cut-{record}.zip"
                ct1_run.checkpoint_results(out, archive, self.plan, self.binding)
                members = verify_archive(archive)
                self.assertTrue(any(f"/.{record}.json." in m for m in members))
                recovered = self.evidence(f"recovered-{record}")
                ct1_run.restore(archive, sha(archive), recovered, self.binding)
                backend = FixtureBackend()
                self.run_it(recovered, backend)
                self.assertEqual(len(backend.calls), 143)
                if record in ("raw", "result"):
                    self.assertTrue((recovered / "calls/000/raw.json").is_file())

    def test_corrupt_published_record_exports_forensic_only(self):
        root = self.evidence("corrupt")
        write_bytes(root / "calls/000/intent.json", b"{")
        archive = self.root / "corrupt.zip"
        self.assertEqual(controller.export_job(root, archive, self.plan, self.binding, "pilot"), "FORENSIC_ONLY")
        self.assertFalse(archive.exists())
        diagnostic = controller.diagnostic_path(archive)
        members = verify_archive(diagnostic)
        self.assertIn("calls/000/intent.json", members)
        self.assertIn("journal-export-failure.json", members)
        self.assertIn("diagnostic-status.json", members)
        self.assertNotIn("runs.json", members)
        with self.assertRaisesRegex(ValueError, "FORENSIC_ARCHIVE_NOT_RESUMABLE"):
            ct1_run.restore(diagnostic, sha(diagnostic), self.root / "forbidden", self.binding)

    def test_diagnostic_omits_receipt_alias_and_oversize(self):
        root = self.evidence("unsafe-records")
        adjacent = self.root / "adjacent.json"
        write_bytes(adjacent, b"must not be copied")
        setup, worker = (root / name for name in ct1_run.PROCESS_RECEIPTS)
        setup.unlink()
        os.link(adjacent, setup)
        worker.write_bytes(b"A" * (ct1_run.CONTROLLER_RECORD_BYTES + 1))
        archive = self.root / "unsafe-records.zip"
        self.assertEqual(controller.export_job(root, archive, self.plan, self.binding, "pilot"), "FORENSIC_ONLY")
        diagnostic = controller.diagnostic_path(archive)
        members = verify_archive(diagnostic)
        self.assertTrue(set(ct1_run.PROCESS_RECEIPTS).isdisjoint(members))
        status = json.loads((root.parent / "diagnostic/diagnostic-status.json").read_bytes())
        self.assertTrue(set(ct1_run.PROCESS_RECEIPTS) <= set(status["omitted_controller_records"]))
        self.assertEqual(adjacent.read_bytes(), b"must not be copied")

    def test_partial_archive_publication_never_exposes_an_unsealed_zip(self):
        for stage in ("write", "publish"):
            with self.subTest(stage=stage):
                job = self.root / stage
                job.mkdir()
                root = job / "evidence"
                root.mkdir()
                write(root / "data.json", {})
                archive = self.root / f"job-{stage}.zip"
                real_link = os.link

                def fail_during_write(_root, staged):
                    write_bytes(staged, b"incomplete")
                    raise OSError("fixture write interrupted")

                def fail_before_zip(source, target):
                    if target == archive:
                        raise OSError("fixture publication interrupted")
                    return real_link(source, target)

                if stage == "write":
                    failure = patch.object(controller, "export", side_effect=fail_during_write)
                else:
                    failure = patch.object(controller.os, "link", side_effect=fail_before_zip)
                with failure, self.assertRaisesRegex(OSError, "interrupted"):
                    controller.publish_export(root, archive)
                self.assertFalse(archive.exists())
                self.assertTrue((job / "export-stage" / (archive.name + ".pending")).is_file())

    def test_pilot_remains_blocked_and_smoke_requires_operator_request(self):
        for settings, expected in (
            (self.config_value(), "NO_TRUSTED_SINGLE_USE_ADMISSION"),
            (self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                               operator_request_sha256="invalid"), "SMOKE_OPERATOR_REQUEST_REQUIRED"),
        ):
            run_id = settings["run_id"]
            config = self.root / (settings["mode"] + ".json")
            write(config, settings)
            job = self.root / run_id
            with patch.object(controller, "layout") as layout:
                for entry in (controller.supervise, controller.worker):
                    with self.assertRaisesRegex(ValueError, expected):
                        entry(SimpleNamespace(config=config, job=job))
                layout.assert_not_called()
            self.assertFalse(job.exists())
        controller.require_native_admission({"mode": "preflight"})
        controller.require_native_admission({"mode": "smoke", "operator_request_sha256": "a" * 64})

    def test_operator_uses_one_durable_intent_and_never_resubmits(self):
        request = {"settings": {"source": "/kaggle/input/source", "source_commit": "a" * 40,
                   "source_zip_sha256": "b" * 64, "owner": {"run_id": "ct1-smoke-000000000000",
                   "pilot_input": "/kaggle/input/images", "plan_sha256": operator.PLAN_SHA,
                   "checkpoint": "/kaggle/input/checkpoint/" + ct1_run.REVISION,
                   "software_input": "/kaggle/input/software", "software_marker_sha256": operator.SOFTWARE_SHA,
                   "approved_drivers": [], "resume": None}},
                   "inputs": dict(zip(operator.ROLES, ("owner/source/1", "owner/images/2",
                                                      "owner/checkpoint/1", "owner/software/3"))),
                   "kaggle_owner": "owner", "data_authority_ref": "synthetic fixture"}
        bound, seal, notebook = operator.prepare(request)
        self.assertEqual(bound["limits"], {"jobs": 1, "images": 1, "calls": 3,
                                           "physical_gpus": 2, "seconds": 5400})
        for outcome in ("timeout", "http-503", "malformed-response", "rejected-input", "submitted"):
            with self.subTest(provider_response=outcome):
                ledger = self.root / ("ledger-" + outcome)
                call_args = []
                digest = sha256(notebook)

                def push(path, **kwargs):
                    self.assertTrue((ledger / "push-intent.json").is_file())
                    meta = json.loads((Path(path) / "kernel-metadata.json").read_bytes())
                    self.assertTrue(meta["is_private"])
                    self.assertFalse(meta["enable_internet"])
                    self.assertEqual(meta["dataset_sources"], list(request["inputs"].values()))
                    self.assertEqual(sha(Path(path) / "smoke.ipynb"), digest)
                    call_args.append(kwargs)
                    if outcome == "timeout":
                        raise TimeoutError("response unknown")
                    if outcome == "http-503":
                        error = RuntimeError("provider error")
                        error.response = SimpleNamespace(status_code=503)
                        raise error
                    if outcome == "malformed-response":
                        raise json.JSONDecodeError("response is malformed", "", 0)
                    rejected = [request["inputs"]["checkpoint"]] if outcome == "rejected-input" else []
                    return SimpleNamespace(error="", ref=bound["job"], version_number=1,
                                           invalid_dataset_sources=rejected, invalid_competition_sources=[],
                                           invalid_kernel_sources=[], invalid_model_sources=[], invalid_tags=[])

                with (patch.object(operator, "api", return_value=SimpleNamespace(kernels_push=push)),
                      patch.object(operator, "provider_inventory", return_value={}),
                      patch.object(operator, "bounded_http", return_value=nullcontext())):
                    if outcome == "timeout":
                        with self.assertRaises(TimeoutError):
                            operator.submit(bound, seal, notebook, digest, ledger)
                    elif outcome in ("http-503", "malformed-response"):
                        expected = RuntimeError if outcome == "http-503" else json.JSONDecodeError
                        with self.assertRaises(expected):
                            operator.submit(bound, seal, notebook, digest, ledger)
                        row = json.loads((ledger / "submission-reconciliation.json").read_bytes())
                        self.assertEqual(row["exception_type"], expected.__name__)
                        self.assertEqual(row["http_status"], 503 if outcome == "http-503" else None)
                        self.assertEqual(row["intent_sha256"], sha(ledger / "push-intent.json"))
                    elif outcome == "rejected-input":
                        with self.assertRaisesRegex(ValueError, "RESULT_UNCERTAIN_NO_RETRY"):
                            operator.submit(bound, seal, notebook, digest, ledger)
                        row = json.loads((ledger / "submission-reconciliation.json").read_bytes())
                        self.assertEqual(row["rejected"], {"invalid_dataset_sources":
                                                          [request["inputs"]["checkpoint"]]})
                    else:
                        result = operator.submit(bound, seal, notebook, digest, ledger)
                        self.assertEqual(result["kind"], "SUBMITTED")
                    with self.assertRaisesRegex(ValueError, "NO_RETRY"):
                        operator.submit(bound, seal, notebook, digest, ledger)
                self.assertEqual(call_args, [{"timeout": "5400", "acc": "NvidiaTeslaT4"}])
                self.assertEqual((ledger / "submitted.json").exists(), outcome == "submitted")

    def test_operator_does_not_round_away_reserved_or_missing_gpu_quota(self):
        gpu = {"totalTimeAllowed": "10800s", "timeUsed": "0s", "timeReserved": "0s"}
        def read(gpu_quota):
            response = SimpleNamespace(content=json_bytes({"gpuQuota": gpu_quota}))
            return operator.QuotaResponse.prepare_from(response)

        self.assertEqual(read(gpu), {"total": "10800s", "used": "0s", "reserved": "0s"})
        for field in ("timeUsed", "timeReserved"):
            low = {**gpu, field: "0.000000100s"}
            with self.assertRaisesRegex(ValueError, "QUOTA_OR_EXISTING_RESERVATION"):
                read(low)
        exact = {**gpu, "totalTimeAllowed": "10800.000000100s", "timeUsed": "0.000000100s"}
        self.assertEqual(read(exact)["used"], "0.000000100s")

    def test_observed_driver_changes_checkpoint_identity(self):
        cfg = {"source_commit": "a" * 40, "approved_drivers": ["570.26", "570.27"],
               "observed_driver": "570.26", "plan_sha256": self.plan_sha,
               "software_marker_sha256": "c" * 64, "source_capsule_sha256": "b" * 64,
               "run_id": "ct1-000000000000"}
        first = controller.binding(cfg, {})
        second = controller.binding({**cfg, "observed_driver": "570.27"}, {})
        self.assertNotEqual(first, second)

    def test_render_owner_notebook_is_exact_and_requires_seals(self):
        settings = {"source": "/kaggle/input/source", "source_commit": "a" * 40,
                    "source_zip_sha256": "b" * 64, "owner": {
                        "run_id": "ct1-000000000000", "pilot_input": "/kaggle/input/images",
                        "plan_sha256": self.plan_sha, "checkpoint": "/kaggle/input/checkpoint",
                        "software_input": "/kaggle/input/software",
                        "software_marker_sha256": "c" * 64, "approved_drivers": [], "resume": None}}
        for mode in ("pilot", "preflight"):
            payload = nb.content(mode, settings)
            self.assertEqual(payload, nb.content(mode, settings))
            row = next(c for c in json.loads(payload)["cells"] if c["id"] == "owner-settings")
            env = {}
            exec("".join(row["source"]), env)
            self.assertEqual(env["OWNER"], settings["owner"])
            self.assertEqual(env["SOURCE_COMMIT"], settings["source_commit"])
        smoke = {**settings, "owner": {**settings["owner"], "run_id": "ct1-smoke-000000000000",
                                        "operator_request_sha256": "d" * 64}}
        self.assertEqual(json.loads(nb.content("smoke", smoke))["cells"][-1]["source"],
                         json.loads(nb.content("pilot", settings))["cells"][-1]["source"])
        with self.assertRaisesRegex(ValueError, "distinct run ID"):
            nb.content("smoke", settings)
        with self.assertRaisesRegex(ValueError, "CROSS_VM_RESUME_BLOCKED"):
            nb.content("pilot", {**settings, "owner": {**settings["owner"], "resume": {}}})
        with self.assertRaisesRegex(ValueError, "sealed source"):
            nb.content("pilot", {**settings, "source_zip_sha256": ""})

    def test_bootstrap_restores_exact_capsule_and_rejects_bad_transport(self):
        work = self.root / "working"
        work.mkdir()
        mounts = self.root / "input"
        source = mounts / "datasets/nguynanhtn/source"
        source.mkdir(parents=True)
        for role in ("train", "software", "checkpoint"):
            (mounts / role).mkdir()
        buffer = BytesIO()
        paths = ("scripts/run_ct1_native_pilot.py", "configs/fulltrain/qwen3.json",
                 "configs/pilot/classification_c1.txt", "configs/pilot/pip_bootstrap.json")
        with ZipFile(buffer, "w") as archive:
            for path in paths:
                archive.writestr(path, path.encode())
        raw = buffer.getvalue()
        marker = {"commit": "a" * 40, "sha256": sha256(raw)}
        write(source / "ct1-source.json", marker)
        transport = source / ct1_run.SOURCE_TRANSPORT
        program = nb.BOOTSTRAP.replace('Path("/kaggle/working")', f"Path({str(work)!r})")
        program = program.replace('Path("/kaggle/input")', f"Path({str(mounts)!r})")
        env = {"SOURCE": str(mounts / "source"), "SOURCE_COMMIT": marker["commit"],
               "SOURCE_ZIP_SHA256": marker["sha256"], "MODE": "smoke",
               "OWNER": {"run_id": "ct1-smoke-000000000000", "pilot_input": str(mounts / "train"),
                         "software_input": str(mounts / "software"), "checkpoint": str(mounts / "checkpoint"),
                         "approved_drivers": []}, "gpu_query": SimpleNamespace(stdout="0, T4, 580.178.04")}

        with (patch.object(controller.sys, "platform", "linux"),
              patch.object(controller.subprocess, "run") as launch):
            for content in (b"!bad", b"AB==", base64.b64encode(raw + b"x"),
                            b"A" * (4 * (((8 * 2**20) + 2)//3) + 1)):
                transport.write_bytes(content)
                with self.assertRaises((ValueError, AssertionError)):
                    exec(program, env.copy())
                launch.assert_not_called()
            transport.write_bytes(base64.b64encode(raw))
            exec(program, env.copy())
            launch.assert_called_once()
            capsule = work / ("ct1-source-" + env["OWNER"]["run_id"])
            self.assertEqual((capsule / paths[0]).read_bytes(), paths[0].encode())
            self.assertEqual(json.loads((capsule / "owner-run.json").read_bytes())["pilot_input"],
                             str(mounts / "train"))

    def test_software_transport_restores_pinned_archives_and_checks_all_wheels(self):
        software = self.root / "software"
        (software / "wheels").mkdir(parents=True)
        reference = qwen.reference(nb.ROOT)
        versions = {name.lower().replace("_", "-").replace(".", "-"): version
                    for name, version in reference["software"].items() if name not in ("python", "zlib")}
        versions["pip"] = "25.0.1"
        wheels = []
        for name, version in versions.items():
            file = name + ".whl"
            write_bytes(software / "wheels" / file, name.encode())
            wheels.append({"file": file, "name": name, "version": version,
                           "size": len(name), "sha256": sha256(name.encode())})
        lock = {"versions": versions, "wheels": wheels}
        marker = {"schema": "fresh-qwen-software-v1", "runtime_lock": lock}
        for component in ct1_run.SOFTWARE_ARCHIVES:
            payload = b"abcde"
            name = reference[component]["url"].rsplit("/", 1)[1]
            reference[component]["sha256"] = sha256(payload)
            marker[component] = {"file": name, "size": len(payload), "sha256": sha256(payload)}
            write_bytes(software / ct1_run.software_transport_name(name), base64.b64encode(payload))
        marker_sha = write(software / ct1_run.SOFTWARE_MARKER, marker)
        python_path = software / ct1_run.software_transport_name(marker["python_source"]["file"])
        with (patch.object(qwen, "reference", return_value=reference),
              patch.object(provision, "reference", return_value=reference)):
            for case, bad, rule in (("truncated", b"YQ==", "TRANSPORT_SIZE"),
                                    ("oversized", b"YQ==" * 3, "TRANSPORT_SIZE"),
                                    ("malformed", b"abcdefgh", "TRANSPORT_ENCODING"),
                                    ("padding", b"YWJjZGV=", "TRANSPORT_ENCODING"),
                                    ("wrong-sha", base64.b64encode(b"12345"), "ARCHIVE_SHA256")):
                scratch = self.root / case
                scratch.mkdir()
                python_path.write_bytes(bad)
                with self.assertRaisesRegex(ValueError, rule):
                    ct1_run.restore_software(software, marker_sha, lock, scratch, nb.ROOT)
            python_path.write_bytes(base64.b64encode(payload))
            archives = ct1_run.restore_software(software, marker_sha, lock, self.root, nb.ROOT)
            self.assertEqual(provision.software_input(software, marker_sha, lock, nb.ROOT,
                                                     archive_dir=archives), marker)
            for component in ct1_run.SOFTWARE_ARCHIVES:
                self.assertEqual((archives / marker[component]["file"]).read_bytes(), payload)
            wheel = software / "wheels" / wheels[0]["file"]
            original_wheel = wheel.read_bytes()
            wheel.write_bytes(b"?" * len(original_wheel))
            with self.assertRaisesRegex(ValueError, "WHEEL_HASH"):
                provision.software_input(software, marker_sha, lock, nb.ROOT, archive_dir=archives)
            wheel.write_bytes(original_wheel)
            (software / "wheels/extra.whl").touch()
            with self.assertRaisesRegex(ValueError, "NO_EXTRA_WHEELS"):
                provision.software_input(software, marker_sha, lock, nb.ROOT, archive_dir=archives)

    def test_source_and_native_share_pixel_envelope(self):
        for size in ((2560, 1440), (1440, 2560), (720, 406)):
            self.assertTrue(ct1_native.image_size_allowed(size))
        for size in ((2336, 1752), (2561, 900), (0, 500)):
            self.assertFalse(ct1_native.image_size_allowed(size))

    def test_driver_and_resource_configuration(self):
        with self.assertRaises(ValueError):
            ct1_native.release_budgets([])
        policy = ct1_native.release_budgets(["570.26"])
        self.assertEqual(policy["free_mib_per_gpu"], [13000, 13000])
        self.assertEqual(controller.WALL_SECONDS, 10800)
        self.assertEqual(ct1_native.MAX_NEW, 768)
        self.assertEqual(ct1_native.MAX_INPUT, 4800)

    def test_notebooks_are_deterministic_and_share_bootstrap(self):
        preflight, pilot = (json.loads(nb.content(mode)) for mode in ("preflight", "pilot"))
        self.assertEqual(preflight["cells"][-1]["source"], pilot["cells"][-1]["source"])
        for n, book in ((nb.PREFLIGHT, preflight), (nb.PILOT, pilot)):
            self.assertEqual(json.loads((nb.ROOT / "notebooks" / n).read_bytes()), book)
            code = [c for c in book["cells"] if c["cell_type"] == "code"]
            for cell in code:
                compile("".join(cell["source"]), cell["id"], "exec")


if __name__ == "__main__":
    unittest.main()
