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
from unittest.mock import call, patch
from zipfile import ZipFile

from safeshift.data.saved_reports import json_bytes, sha256
from safeshift.evaluation.ct1_contract import ARMS
from safeshift.evaluation.ct1_pilot import replay
from safeshift.fulltrain import ct1_checkpoint, ct1_run, ct1_native, environment, gpu_driver, memory, provision, qwen
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
        return {"raw_text": json.dumps(text), "at_cap": False, "eos": True, "new_tokens": 1}

    def record_memory(self):
        return {}

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
                    controller.supervise(SimpleNamespace(config=config, job=job, deadline=None))
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
                              ("setup", "PROCESS_GROUP_CLEANUP_UNVERIFIED"),
                              ("stage", "PROCESS_GROUP_CLEANUP_UNVERIFIED")):
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
                      patch.object(controller.os, "set_blocking", create=True),
                      patch.object(controller.supervision, "run", side_effect=run),
                      patch.object(controller.supervision, "parent_deadline", return_value=nullcontext()),
                      patch.object(ct1_run, "reconstruct") as reconstruct):
                    controller.supervise(SimpleNamespace(config=config, job=job, deadline=None))
                    reconstruct.assert_not_called()
                sequence = ["setup", "probe", "stage", "io-probe", "worker"]
                self.assertEqual(calls, sequence[:sequence.index(where) + 1])
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
        ui_bound, ui_seal, ui_nb = operator.prepare(request, owner_ui_slug=operator.JOB + "-scratch")
        self.assertEqual((ui_bound["job"], ui_bound["version"]), ("owner/" + operator.JOB + "-scratch", 2))
        self.assertNotEqual(ui_seal, seal)
        ui_ledger = self.root / "owner-ui-ledger"
        with self.assertRaisesRegex(ValueError, "OWNER_UI_SMOKE_REQUIRES_OWNER"):
            operator.submit(ui_bound, ui_seal, ui_nb, sha256(ui_nb), ui_ledger)
        self.assertFalse(ui_ledger.exists())
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
                         "approved_drivers": []}, "gpu_query": SimpleNamespace(stdout="0, T4, 580.178.04"),
               "notebook_started": time.monotonic() - 180}

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
            self.assertEqual(float(launch.call_args.args[0][-1]), env["notebook_started"] + 5100)
            self.assertLess(launch.call_args.kwargs["timeout"], 5100)
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

    def test_setup_uses_scoped_nvml_before_provision(self):
        job = self.root / "job"
        root = job / "evidence"
        root.mkdir(parents=True)
        cfg = self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                                operator_request_sha256="f" * 64)
        settings = self.root / "setup.json"
        write(settings, cfg)
        args = SimpleNamespace(config=settings, command="setup", job=job, scratch=self.root,
                               deadline=time.monotonic() + 60)
        driver = Path("/usr/local/nvidia/lib64")
        software = self.root / "software"
        archive_dir = self.root / "archives"
        with (patch.object(controller, "layout", return_value=(self.data, software, None, {}, self.plan)),
              patch.object(environment, "resources", return_value={"free_bytes": []}),
              patch.object(environment, "hardware") as unscoped,
              patch.object(gpu_driver, "locate", return_value=(driver, {})),
              patch.object(gpu_driver, "hardware", return_value={"physical_gpus": [0, 1]}) as probe,
              patch.object(ct1_run, "restore_software", return_value=archive_dir),
              patch.object(provision, "prepare") as prepare,
              patch.object(memory, "observe") as observe):
            probe.side_effect = ValueError("scoped probe fails")
            with self.assertRaisesRegex(ValueError, "scoped probe fails"):
                controller.worker(args)
            prepare.assert_not_called()
            self.assertEqual(observe.call_args_list, [
                call(root, "setup-entry"), call(root, "setup-exit")])
            observe.reset_mock()
            probe.reset_mock(side_effect=True)
            probe.return_value = {"physical_gpus": [0, 1]}
            prepare.return_value = (self.root / "qwen-software/venv/bin/python", {})
            controller.worker(args)
            self.assertEqual(probe.call_args.args[2:], (driver, root, "setup"))
            prepare.assert_called_once()
            self.assertEqual(observe.call_args_list, [
                call(root, "setup-entry"), call(root, "setup-archives-restored"), call(root, "setup-exit")])
            unscoped.assert_not_called()
        before = json.loads((root / "before-setup.json").read_bytes())
        self.assertEqual(before["native_calls"], 0)
        self.assertEqual(before["physical"]["physical_gpus"], [0, 1])

    def test_probe_binds_cuda_before_torch_abi_checks(self):
        from safeshift.fulltrain import preflight

        order = []
        evidence = self.root / "evidence/runtime-probe"
        driver = Path("/usr/local/nvidia/lib64")
        def bind(out):
            self.assertEqual(out, evidence)
            order.append("bind")
            return driver

        def hardware(key, policy, bound, out, label):
            self.assertEqual((bound, out, label), (driver, evidence, "probe"))
            order.append("physical")

        def software(*args):
            order.append("Torch import")
            return {"compiled_cpu_nms": "PASS"}

        def cuda(*args):
            order.append("CUDA tensor")
            raise ValueError("fixture stops after CUDA")

        with (patch.dict(os.environ, {"SAFESHIFT_RUNTIME_ROOT": str(self.root / "venv")}),
              patch.object(environment, "resources"),
              patch.object(memory, "observe"),
              patch.object(preflight, "storage_probe"),
              patch.object(gpu_driver, "bind", side_effect=bind),
              patch.object(gpu_driver, "hardware", side_effect=hardware),
              patch.object(environment, "software", side_effect=software),
              patch.object(environment, "cuda", side_effect=cuda),
              patch.object(qwen, "verify_snapshot") as checkpoint):
            with self.assertRaisesRegex(ValueError, "fixture stops after CUDA"):
                ct1_native.probe_runtime(None, nb.ROOT, {}, ["580.178.04"], self.root, self.root,
                                         self.data, self.plan)
            self.assertEqual(order, ["bind", "physical", "Torch import", "CUDA tensor"])
            checkpoint.assert_not_called()

    def test_probe_preserves_exact_ram_failure_before_driver_probe(self):
        low_memory = {"available_bytes": 16 * 2**30 - 1,
                      "cgroup_remaining_bytes": [16 * 2**30 - 1]}
        with (patch.dict(os.environ, {"SAFESHIFT_RUNTIME_ROOT": str(self.root / "venv")}),
              patch.object(memory, "observe") as observe,
              patch.object(environment, "host_memory", return_value=low_memory),
              patch.object(gpu_driver, "bind") as bind):
            with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                ct1_native.probe_runtime(None, nb.ROOT, {}, ["580.178.04"], self.root, self.root,
                                         self.data, self.plan)
            self.assertEqual(observe.call_args_list, [
                call(self.root / "evidence/runtime-probe", "before-gate"),
                call(self.root / "evidence/runtime-probe", "gate-failure")])
            bind.assert_not_called()
        receipt = json.loads((self.root / "evidence/runtime-probe/ram-gate.json").read_bytes())
        self.assertEqual(receipt, {"memory": low_memory, "floor_bytes": 16 * 2**30,
                                   "ram_gate_passed": False})

    def test_checkpoint_gate_does_not_import_or_probe_cuda(self):
        # Reproduce the former incident boundary: enough RAM before probes,
        # unavailable immediately afterward. Hashing now runs in a separate stage.
        floor = 16 * 2**30
        phases = []
        with (patch.object(memory, "observe"),
              patch.object(environment, "host_memory", return_value={"available_bytes": floor}),
              patch.object(environment, "software", side_effect=AssertionError("no ABI probe in hash")),
              patch.object(environment, "cuda", side_effect=AssertionError("no CUDA probe in hash")),
              patch.object(qwen, "verify_snapshot", side_effect=lambda *a, **kw: phases.append("hash"))):
            ct1_native.verify_checkpoint(self.root, nb.ROOT, ["580.178.04"], self.root,
                                         time.monotonic() + 10)
        self.assertEqual(phases, ["hash"])
        gate = json.loads((self.root / "before-checkpoint-ram-gate.json").read_bytes())
        self.assertEqual(gate, {"floor_bytes": floor, "memory": {"available_bytes": floor},
                                "ram_gate_passed": True})

    def test_probe_failure_prevents_worker_and_retains_diagnostics(self):
        work = self.root / "work"
        work.mkdir()
        scratch = work / "scratch"
        scratch.mkdir()
        cfg = self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                                operator_request_sha256="a" * 64)
        config = work / "args.json"
        write(config, cfg)
        job = work / cfg["run_id"]
        phases = []

        def run(command, *, receipt, **kwargs):
            phase = command[4]
            phases.append(phase)
            if phase == "probe":
                write(job / "evidence/runtime-probe/ram-gate.json", {"ram_gate_passed": False})
                write(job / "evidence/runtime-probe-failure.json", {"code": "CT1_INPUT_TOKEN_BUDGET"})
                write(receipt, self.receipt("CHILD_FAILURE", returncode=1))
                raise RuntimeError("SUPERVISED_CHILD_FAILURE")
            write(receipt, self.receipt())
            return {"status": "EXITED", "returncode": 0}

        with (patch.object(controller, "WORK", work), patch.object(controller.sys, "platform", "linux"),
              patch.object(controller, "layout", return_value=(self.data, work, work, {},
                           {**self.plan, "cases": self.plan["cases"][:1]})),
              patch.object(controller.tempfile, "mkdtemp", return_value=str(scratch)),
              patch.object(controller.supervision, "run", side_effect=run),
              patch.object(controller.supervision, "parent_deadline", return_value=nullcontext())):
            controller.supervise(SimpleNamespace(config=config, job=job, deadline=time.monotonic() + 600))
        self.assertEqual(phases, ["setup", "probe"])
        members = verify_archive(work / (cfg["run_id"] + "-diagnostic.zip"))
        self.assertIn("probe-supervisor.json", members)
        self.assertIn("runtime-probe/ram-gate.json", members)
        self.assertIn("runtime-probe-failure.json", members)
        with ZipFile(work / (cfg["run_id"] + "-diagnostic.zip")) as z:
            self.assertEqual(json.loads(z.read("runtime-probe-failure.json"))["code"], "CT1_INPUT_TOKEN_BUDGET")
        self.assertNotIn("worker-supervisor.json", members)
        self.assertNotIn("checkpoint-stability.json", members)

    def test_worker_rechecks_each_t4_after_processor_init_before_loading_weights(self):
        job = self.root / "job"
        root = job / "evidence"
        root.mkdir(parents=True)
        cfg = self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                                operator_request_sha256="a" * 64)
        config = self.root / "settings.json"
        write(config, cfg)
        write(root / "runtime-probe.json", {"model_calls": 0, "weights_loaded": False})
        write(root / ct1_run.IO_RECEIPT, self.receipt())
        write(root / "identity.json", controller.binding(cfg, {}))
        write(root / "resume-admission.json", {"status": "FRESH_ADMITTED"})
        events = []

        def backend(*args, before_load):
            events.append("processor-initialized")
            before_load()
            self.fail("must not load weights after T4 failure")

        def physical(*args):
            events.append("physical-gate")
            raise ValueError("INDIVIDUAL_GPU_HEADROOM")

        with (patch.object(controller, "layout", return_value=(self.data, None, None, {}, self.plan)),
              patch.object(controller, "require_closed_phase"),
              patch.object(controller, "reclaim_setup"),
              patch.object(memory, "observe"),
              patch.object(ct1_checkpoint, "verified_stage", return_value=(self.root, {})),
              patch.object(gpu_driver, "bind"),
              patch.object(gpu_driver, "hardware", side_effect=physical),
              patch.object(environment, "host_memory", return_value={"available_bytes": 16 * 2**30}),
              patch.object(ct1_native, "Backend", side_effect=backend),
              patch.object(ct1_run, "execute") as execute):
            with self.assertRaisesRegex(ValueError, "INDIVIDUAL_GPU_HEADROOM"):
                controller.worker(SimpleNamespace(command="worker", deadline=time.monotonic() + 30,
                                                  job=job, scratch=self.root, config=config))
        self.assertEqual(events, ["processor-initialized", "physical-gate"])
        self.assertFalse((root / "model-load-start.json").exists())
        execute.assert_not_called()

    def checkpoint_fixture(self):
        source = self.root / "mount" / ct1_run.REVISION
        source.mkdir(parents=True)
        shard = "model-00001-of-00004.safetensors"
        files = {shard: b"synthetic locked weights", "model.safetensors.index.json":
                 json_bytes({"weight_map": {"fixture.weight": shard}})}
        for name, payload in files.items():
            write_bytes(source / name, payload)
        lock = {"model": {"revision": source.name}, "snapshot_files": [
            {"path": name, "size_bytes": len(payload), "hash_algorithm": "sha256",
             "expected_hash": sha256(payload)} for name, payload in files.items()]}
        evidence = self.root / "stage-evidence"
        scratch = self.root / "scratch"
        evidence.mkdir()
        scratch.mkdir()
        stat = scratch.stat()
        write(evidence / "scratch-ownership.json", {"device": stat.st_dev, "inode": stat.st_ino})
        return source, scratch, evidence, lock

    def test_checkpoint_stage_rechecks_actual_bytes_and_rejects_changed_destination(self):
        source, scratch, evidence, lock = self.checkpoint_fixture()
        budgets = ct1_native.release_budgets(["580.178.04"])
        with (patch.object(qwen, "reference", return_value=lock),
              patch.object(memory, "ct1_ram_gate"), patch.object(ct1_checkpoint, "capacity", return_value={}),
              patch.object(memory, "stream_readonly_sha256", wraps=memory.stream_readonly_sha256) as reader):
            ct1_checkpoint.stage(source, scratch, self.root, evidence, self.root, budgets, time.monotonic() + 30)
            staged, receipt = ct1_checkpoint.verified_stage(scratch, evidence, self.root)
            self.assertEqual([c.args[0].parent for c in reader.call_args_list], [source, source, staged, staged])
            self.assertTrue(receipt["weight_bytes_verified"])
            self.assertEqual({p.name: p.read_bytes() for p in staged.iterdir()},
                             {p.name: p.read_bytes() for p in source.iterdir()})
            shard = next(staged.glob("*.safetensors"))
            shard.chmod(0o600)
            self.addCleanup(lambda: [p.chmod(0o600) for p in staged.iterdir()])
            shard.write_bytes(b"wrong")
            with self.assertRaisesRegex(ValueError, "CT1_CHECKPOINT_STAGE_CHANGED"):
                ct1_checkpoint.verified_stage(scratch, evidence, self.root)

    def test_checkpoint_stage_does_not_admit_incorrect_readback(self):
        source, scratch, evidence, lock = self.checkpoint_fixture()
        budgets = ct1_native.release_budgets(["580.178.04"])
        stream = memory.stream_readonly_sha256

        def corrupt_digest(path, **kwargs):
            actual = stream(path, **kwargs)
            return "0" * 64 if path.is_relative_to(scratch) else actual

        with (patch.object(qwen, "reference", return_value=lock),
              patch.object(memory, "ct1_ram_gate"), patch.object(ct1_checkpoint, "capacity", return_value={}),
              patch.object(memory, "stream_readonly_sha256", side_effect=corrupt_digest)):
            with self.assertRaisesRegex(ValueError, "QWEN_FILE_SHA256"):
                ct1_checkpoint.stage(source, scratch, self.root, evidence, self.root, budgets, time.monotonic() + 30)
        self.assertFalse((evidence / ct1_checkpoint.STAGE_RECORD).exists())
        self.assertTrue((evidence / "checkpoint-stage-copy.json").exists())

    def test_staging_rejects_memory_backed_or_insufficient_scratch(self):
        source, scratch, _, _ = self.checkpoint_fixture()
        budgets = ct1_native.release_budgets(["580.178.04"])
        good = {"filesystem": "ext4", "mountpoint": "/kernel"}
        with patch.object(ct1_checkpoint, "mount_details",
                          side_effect=[good, {"filesystem": "tmpfs", "mountpoint": "/tmp"}, good]):
            with self.assertRaisesRegex(ValueError, "CT1_CHECKPOINT_SCRATCH_NOT_DISK"):
                ct1_checkpoint.capacity(source, scratch, self.root, 1, budgets)
        with (patch.object(ct1_checkpoint, "mount_details",
                           side_effect=[good, {"filesystem": "ext4", "mountpoint": "/tmp"}, good]),
              patch.object(ct1_checkpoint.shutil, "disk_usage", return_value=SimpleNamespace(free=1))):
            with self.assertRaisesRegex(ValueError, "CT1_CHECKPOINT_STAGE_DISK"):
                ct1_checkpoint.capacity(source, scratch, self.root, 1, budgets)

    def test_ct1_checks_a_tighter_visible_cgroup_ancestor(self):
        proc, cgroup = self.root / "proc", self.root / "cgroup"
        write_bytes(proc / "meminfo", b"MemAvailable: 40000000 kB\n")
        write_bytes(proc / "self/cgroup", b"0::/container/section/leaf\n")
        write_bytes(proc / "self/mountinfo",
                    f"1 2 0:1 /container {cgroup.as_posix()} rw - cgroup2 cgroup rw\n".encode())
        write_bytes(cgroup / "cgroup.controllers", b"memory cpu\n")
        for group, limit, used in ((".", 30, 6), ("section", 18, 3), ("section/leaf", 24, 2)):
            write_bytes(cgroup / group / "memory.max", str(limit * 2**30).encode())
            write_bytes(cgroup / group / "memory.current", str(used * 2**30).encode())
        self.assertEqual(environment.host_memory(proc / "meminfo", cgroup)["available_bytes"], 24 * 2**30)
        measured = environment.host_memory(proc / "meminfo", cgroup, details=True, include_ancestors=True)
        self.assertEqual(measured["available_bytes"], 15 * 2**30)
        self.assertEqual(measured["cgroups"]["section/memory.max"]["remaining_bytes"], 15 * 2**30)

    def test_checkpoint_io_probe_matches_equal_bytes_and_detects_mount_drift(self):
        source, staged, evidence = (self.root / name for name in ("source", "staged", "io"))
        evidence.mkdir()
        name = "model-00001-of-00004.safetensors"
        size = 64 * 1024
        payload = b"a" * size + b"b" * size
        write_bytes(source / name, payload)
        write_bytes(staged / name, payload)
        with patch.object(ct1_checkpoint, "SAMPLE_BYTES", size):
            ct1_checkpoint.compare_reads(source, staged, evidence, time.monotonic() + 30)
            self.assertEqual(len(list(evidence.glob("*-result.json"))), 4)
            (source / name).write_bytes(b"x" + payload[1:])
            with self.assertRaisesRegex(ValueError, "CT1_CHECKPOINT_IO_BYTES_CHANGED"):
                ct1_checkpoint.compare_reads(source, staged, self.root / "changed-io", time.monotonic() + 30)

    def test_call_time_reserve_stops_without_writing_any_intent(self):
        output = self.evidence("short-reserve")
        fake = FixtureBackend()
        ct1_run.execute(output, self.plan, self.binding, self.data / "images", fake,
                        time.monotonic() + 30, reserve_seconds=120)
        self.assertEqual(fake.calls, [])
        self.assertFalse((output / "calls").exists())
        self.assertEqual(json.loads((output / "call-admission-stop.json").read_bytes())["next_slot"], 0)

    def test_staged_smoke_allows_only_a_reaped_io_timeout_and_exports_three_results(self):
        for io_closed in (True, False):
            work = self.root / f"io-closure-{io_closed}"
            scratch = work / "scratch"
            scratch.mkdir(parents=True)
            cfg = self.config_value(mode="smoke", run_id="ct1-smoke-000000000000",
                                    operator_request_sha256="a" * 64)
            config = work / "settings.json"
            write(config, cfg)
            job = work / cfg["run_id"]
            plan = {**self.plan, "cases": self.plan["cases"][:1]}
            stages = []

            def launch(command, *, receipt, deadline, **kwargs):
                phase = command[4]
                stages.append(phase)
                if phase == "io-probe":
                    if io_closed:
                        write(receipt, self.receipt("HARD_DEADLINE", returncode=-9))
                        raise RuntimeError("SUPERVISED_HARD_DEADLINE")
                    write(receipt, self.receipt("PROCESS_GROUP_SURVIVORS", returncode=-9))
                    raise RuntimeError("SUPERVISED_PROCESS_GROUP_SURVIVORS")
                if phase == "worker":
                    self.assertLessEqual(kwargs["readiness"][1], deadline)
                    self.assertIn(str(kwargs["pass_fds"][0]), command)
                    state = controller.binding(cfg, {})
                    ct1_run.execute(job / "evidence", plan, state, self.data / "images",
                                    FixtureBackend(), time.monotonic() + 30)
                write(receipt, self.receipt())
                return {"status": "EXITED", "returncode": 0}

            with (patch.object(controller, "WORK", work), patch.object(controller.sys, "platform", "linux"),
                  patch.object(controller, "layout", return_value=(self.data, work, work, {}, plan)),
                  patch.object(controller.tempfile, "mkdtemp", return_value=str(scratch)),
                  patch.object(controller.provision, "clean_env", return_value={}),
                  patch.object(controller.os, "set_blocking", create=True),
                  patch.object(controller.supervision, "run", side_effect=launch),
                  patch.object(controller.supervision, "parent_deadline", return_value=nullcontext())):
                controller.supervise(SimpleNamespace(config=config, job=job, deadline=time.monotonic() + 600))
            prefix = ["setup", "probe", "stage", "io-probe"]
            self.assertEqual(stages, prefix + (["worker"] if io_closed else []))
            if io_closed:
                with ZipFile(work / (cfg["run_id"] + ".zip")) as archive:
                    self.assertEqual(json.loads(archive.read("summary.json"))["returned"], 3)
                    stable = json.loads(archive.read("checkpoint-stability.json"))
                    self.assertEqual(set(stable["process_receipts_sha256"]), set(ct1_run.STAGED_PROCESS_RECEIPTS))
            else:
                names = verify_archive(work / (cfg["run_id"] + "-diagnostic.zip"))
                self.assertNotIn("checkpoint-stability.json", names)

    @unittest.skipUnless(os.name == "posix", "real Linux readiness pipe and process group")
    def test_loading_watchdog_reaps_child_and_preserves_its_phase(self):
        import sys
        for acknowledged in (False, True):
            root = self.root / str(acknowledged)
            root.mkdir()
            read_fd, write_fd = os.pipe()
            try:
                os.set_blocking(read_fd, False)
                body = ("import time; time.sleep(30)" if not acknowledged else
                        f"import os, time; os.write({write_fd}, b'1'); time.sleep(1.3)")
                now = time.monotonic()
                kwargs = dict(cwd=root, env=os.environ.copy(), deadline=now + 5,
                              log=root / "worker.log", receipt=root / "worker-supervisor.json",
                              max_log_bytes=65536, pass_fds=(write_fd,), readiness=(read_fd, now + 1))
                command = [sys.executable, "-B", "-c", body]
                if acknowledged:
                    controller.supervision.run(command, **kwargs)
                else:
                    with self.assertRaisesRegex(RuntimeError, "SUPERVISED_HARD_DEADLINE"):
                        controller.supervision.run(command, **kwargs)
            finally:
                os.close(read_fd)
                os.close(write_fd)
            actual = json.loads((root / "worker-supervisor.json").read_bytes())
            self.assertTrue(controller.supervision.process_group_closed(actual))
            self.assertEqual(actual["readiness_received"], acknowledged)
            self.assertEqual(actual["readiness_deadline_expired"], not acknowledged)

    def test_new_run_requires_closed_probe_receipt_for_ordinary_zip(self):
        for status in (None, "PROCESS_GROUP_SURVIVORS", "CHILD_FAILURE", "EXITED"):
            job = self.root / ("proof-" + str(status))
            job.mkdir()
            out = self.evidence(str(job / "evidence"))
            (out / "config-summary.json").write_bytes(json_bytes({
                "mode": "pilot", "runtime_probe_required": True}))
            if status is not None:
                data = self.receipt(status, returncode=0 if status == "EXITED" else 1)
                write(out / ct1_run.PROBE_RECEIPT, data)
            archive = job / "result.zip"
            result = controller.export_job(out, archive, self.plan, self.binding, "pilot")
            if status == "EXITED":
                self.assertEqual(result, "PARTIAL_OR_BLOCKED")
                with ZipFile(archive) as z:
                    hashes = json.loads(z.read("checkpoint-stability.json"))["process_receipts_sha256"]
                    self.assertEqual(set(hashes), set(ct1_run.PROBED_PROCESS_RECEIPTS))
            else:
                self.assertEqual(result, "FORENSIC_ONLY")
                self.assertFalse(archive.exists())

    def test_clean_exit_with_incomplete_smoke_is_reported_as_partial(self):
        run_id = "ct1-smoke-000000000000"
        state = ct1_run.identity(self.plan_sha, "a" * 64, "b" * 64, "c" * 64, run_id, smoke=True)
        out = self.evidence("incomplete", mode="smoke", binding=state)
        archive = self.root / "smoke.zip"
        plan = {**self.plan, "cases": self.plan["cases"][:1]}
        self.assertEqual(controller.export_job(out, archive, plan, state, "smoke"), "PARTIAL_OR_BLOCKED")
        with ZipFile(archive) as z:
            self.assertEqual(json.loads(z.read("summary.json"))["not_attempted"], 3)
            self.assertEqual(json.loads(z.read("export-status.json"))["status"], "PARTIAL_OR_BLOCKED")

    def test_raw_and_result_survive_interrupted_post_generate_telemetry(self):
        out = self.evidence("post-generate-interrupt")
        slot = out / "calls/000"

        def interrupt():
            self.assertTrue((slot / "raw.json").is_file())
            self.assertTrue((slot / "result.json").is_file())
            raise TimeoutError("interrupted after generate")

        backend = FixtureBackend()
        backend.record_memory = interrupt
        with self.assertRaisesRegex(TimeoutError, "interrupted after generate"):
            self.run_it(out, backend)
        ct1_run.reconstruct(out, self.plan, self.binding)
        summary = json.loads((out / "summary.json").read_bytes())
        self.assertEqual(summary["returned"], 1)
        self.assertEqual(summary["durable_native_intents"], 1)
        self.assertEqual(summary["durable_tokens_without_raw"], 0)
        self.assertEqual(backend.calls, ["A"])
        self.assertFalse((slot / "memory.json").exists())

    def test_export_counts_tokens_only_without_claiming_raw_return(self):
        out = self.evidence("interrupted-decode")
        backend = FixtureBackend(after=lambda: (_ for _ in ()).throw(RuntimeError("fixture")))
        with self.assertRaises(RuntimeError):
            self.run_it(out, backend)
        ct1_run.reconstruct(out, self.plan, self.binding)
        summary = json.loads((out / "summary.json").read_bytes())
        self.assertEqual(summary["returned"], 0)
        self.assertEqual(summary["durable_native_intents"], 1)
        self.assertEqual(summary["durable_tokens_without_raw"], 1)
        self.assertTrue((out / "calls/000/tokens.json").is_file())

    def test_preload_cache_advice_only_once_then_enforces_fresh_floor(self):
        budgets = ct1_native.release_budgets(["580.178.04"])
        floor = 16 * 2**30
        for final in (floor - 1, floor):
            out = self.root / str(final)
            deadline = time.monotonic() + 30
            with (patch.object(controller, "reclaim_setup") as reclaim,
                  patch.object(gpu_driver, "hardware"),
                  patch.object(memory, "observe"),
                  patch.object(environment, "host_memory", side_effect=[
                      {"available_bytes": floor - 1}, {"available_bytes": final}])):
                if final < floor:
                    with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                        controller.admit_model_load(out, self.root, deadline, budgets, "driver")
                else:
                    controller.admit_model_load(out, self.root, deadline, budgets, "driver")
            reclaim.assert_called_once_with(out, self.root, deadline, phase="probe", label="preload")
            self.assertEqual((out / "model-load-start.json").is_file(), final == floor)

    def test_smoke_deadline_preserves_export_reserve_and_rejects_extended_budget(self):
        self.assertEqual(controller.job_deadline("smoke", 5100, 180), 5100)
        for requested in (None, 180 + 120, 180 + 5101, float("nan")):
            with self.subTest(requested=requested):
                with self.assertRaisesRegex(ValueError, "CT1_SMOKE_DEADLINE_REQUIRED"):
                    controller.job_deadline("smoke", requested, 180)
        self.assertEqual(controller.job_deadline("preflight", None, 80), 5480)

    def test_post_generate_measurement_failure_is_diagnostic_only(self):
        backend = ct1_native.Backend.__new__(ct1_native.Backend)
        with patch.object(backend, "failure_memory", side_effect=RuntimeError("NVML")):
            self.assertEqual(backend.record_memory(), {"status": "UNAVAILABLE",
                                                       "error_type": "RuntimeError"})

    def test_gate_records_host_and_named_cgroup_operands_and_unreadable_gate(self):
        proc = self.root / "meminfo"
        proc.write_text("MemAvailable: 31457280 kB\n", encoding="utf-8")
        group = self.root / "cgroup"
        group.mkdir()
        (group / "memory.max").write_text(str(32 * 2**30))
        (group / "memory.current").write_text(str(17 * 2**30))
        self.assertEqual(environment.host_memory(proc, group, details=True), {
            "available_bytes": 15 * 2**30, "cgroup_remaining_bytes": [15 * 2**30],
            "host_mem_available_bytes": 30 * 2**30,
            "cgroups": {"memory.max": {"limit_bytes": 32 * 2**30,
                                      "usage_bytes": 17 * 2**30, "remaining_bytes": 15 * 2**30}}})
        floor = 16 * 2**30
        with (patch.object(environment, "host_memory", side_effect=OSError("fixture")),
              patch.object(memory, "observe") as observe):
            with self.assertRaisesRegex(OSError, "fixture"):
                memory.ct1_ram_gate(self.root, "before-model-load-ram-gate", floor)
        self.assertEqual(observe.call_args_list, [
            call(self.root, "before-model-load-ram-gate-before"),
            call(self.root, "before-model-load-ram-gate-failure")])
        receipt = json.loads((self.root / "before-model-load-ram-gate.json").read_bytes())
        self.assertEqual(receipt, {"floor_bytes": floor, "ram_gate_passed": False,
                                   "read_error": {"type": "OSError", "message": "fixture"}})

    def test_reclaim_waits_for_closed_setup_group_and_failure_is_advisory(self):
        root = self.root / "evidence"
        closed = self.receipt()
        # A valid controller report is the source of group closure, not a zero exit alone.
        with (patch.object(ct1_run, "read_controller_record") as read_record,
              patch.object(memory, "observe") as observe,
              patch.object(memory, "advise_ct1_setup", side_effect=OSError("fixture")) as advise):
            survivor = {**closed, "group_exit": {"status": "PROCESS_GROUP_SURVIVORS"}}
            read_record.return_value = json_bytes(survivor)
            with self.assertRaisesRegex(ValueError, "DEPENDENCY_GROUP_UNVERIFIED:setup"):
                controller.reclaim_setup(root, self.root, time.monotonic() + 60)
            advise.assert_not_called()
            observe.assert_not_called()

            read_record.side_effect = [json_bytes(closed), json_bytes({"device": 1, "inode": 2})]
            deadline = time.monotonic() + 60
            controller.reclaim_setup(root, self.root, deadline)
            advise.assert_called_once_with(self.root, {"device": 1, "inode": 2}, deadline=deadline)
            self.assertEqual(observe.call_args_list, [call(root, "setup-reclaim-before"), call(root, "setup-reclaim-after")])
        report = json.loads((root / "setup-cache-advice.json").read_bytes())
        self.assertEqual(report["status"], "ADVICE_FAILED")
        self.assertEqual(report["effect"], "ADVISORY_NOT_RAM_PROOF")

    @unittest.skipUnless(hasattr(os, "posix_fadvise"), "POSIX descriptor cache advice")
    def test_ct1_advises_only_owned_unaliased_files(self):
        setup = self.root / "scratch/qwen-software"
        archives = setup.parent / "ct1-build-archives"
        setup.mkdir(parents=True)
        archives.mkdir()
        original = self.root / "outside.bin"
        payload = b"x" * (2**20)
        original.write_bytes(payload)
        active = setup / "lib.bin"
        active.write_bytes(payload)
        (archives / "python.tar.xz").write_bytes(payload)
        os.link(original, setup / "hardlink.bin")
        (setup / "alias.bin").symlink_to(original)
        info = setup.parent.stat()
        owned = {"device": info.st_dev, "inode": info.st_ino}
        advised = []
        def advice(fd, *args):
            advised.append(os.fstat(fd).st_ino)

        with patch.object(os, "posix_fadvise", side_effect=advice):
            report = memory.advise_ct1_setup(setup.parent, owned, deadline=time.monotonic() + 60)
        self.assertEqual(set(advised), {active.stat().st_ino, (archives / "python.tar.xz").stat().st_ino})
        self.assertEqual(report["advised_bytes"], 2 * len(payload))
        self.assertEqual(report["skipped_aliases"], 2)
        self.assertEqual(report["deleted_files"], 0)
        self.assertEqual(original.read_bytes(), payload)
        self.assertEqual(active.read_bytes(), payload)
        with self.assertRaisesRegex(ValueError, "ADVICE_ROOT_CHANGED"):
            memory.advise_ct1_setup(setup.parent, {**owned, "inode": -1}, deadline=time.monotonic() + 60)

    def test_fadvise_error_does_not_substitute_for_actual_checkpoint_sha(self):
        fixture = self.root / "fixture.safetensors"
        fixture.write_bytes(b"actual bytes")
        advice_errors = []
        with (patch.object(os, "POSIX_FADV_DONTNEED", 4, create=True),
              patch.object(os, "POSIX_FADV_RANDOM", 1, create=True),
              patch.object(os, "sysconf", return_value=4096, create=True),
              patch.object(os, "posix_fadvise", side_effect=OSError(22, "fixture"), create=True) as advise):
            actual = memory.stream_readonly_sha256(fixture, advice_errors=advice_errors,
                                                   deadline=time.monotonic() + 60)
            self.assertEqual([entry.args[-1] for entry in advise.call_args_list], [1, 4])
        self.assertEqual(actual, sha256(b"actual bytes"))
        self.assertEqual(advice_errors, [
            {"file": fixture.name, "hint": hint, "errno": 22} for hint in (1, 4)])

    def test_optional_random_hint_failure_does_not_disable_dontneed_or_other_files(self):
        values = [self.root / name for name in ("first.safetensors", "second.safetensors")]
        hints = []
        for item in values:
            item.write_bytes(b"x" * 4096)

        def fadvise(fd, offset, length, hint):
            hints.append((offset, length, hint))
            if hint == 1:
                raise OSError(22, "fixture")

        errors = []
        with (patch.object(os, "POSIX_FADV_DONTNEED", 4, create=True),
              patch.object(os, "POSIX_FADV_RANDOM", 1, create=True),
              patch.object(os, "sysconf", return_value=4096, create=True),
              patch.object(os, "posix_fadvise", side_effect=fadvise, create=True)):
            for item in values:
                self.assertEqual(memory.stream_readonly_sha256(
                    item, advice_errors=errors, advise_whole_file=False), sha(item))
        self.assertEqual(hints, [(0, 0, 1), (0, 4096, 4)] * 2)
        self.assertEqual(errors, [{"file": item.name, "hint": 1, "errno": 22} for item in values])

    def test_interrupted_ct1_hash_advises_only_complete_consumed_pages(self):
        fixture = self.root / "fixture.checkpoint"
        payload = b"x" * 8192
        fixture.write_bytes(payload)
        with (patch.object(os, "POSIX_FADV_DONTNEED", 4, create=True),
              patch.object(os, "POSIX_FADV_RANDOM", 1, create=True),
              patch.object(os, "sysconf", return_value=4096, create=True)):
            for reads, expected in (([OSError("read failed")], []),
                                     ([payload[:4096], OSError("read failed")], [(0, 4096, 4)])):
                with (self.subTest(expected=expected),
                      patch.object(os, "read", side_effect=reads),
                      patch.object(os, "posix_fadvise", create=True) as fadvise):
                    with self.assertRaisesRegex(OSError, "read failed"):
                        memory.stream_readonly_sha256(fixture, expected_size=len(payload),
                                                      advise_whole_file=False)
                    self.assertEqual([c.args[1:] for c in fadvise.call_args_list if c.args[-1] == 4],
                                     expected)
        self.assertEqual(fixture.read_bytes(), payload)

    def test_parent_load_samples_survive_missing_worker_cleanup(self):
        root = self.root / "evidence"
        root.mkdir()
        archive = self.root / "smoke.zip"
        observed = {"load_samples": [{"monotonic": 2}], "after_worker": {"monotonic": 3}}
        with patch.object(controller.supervision, "parent_deadline", return_value=nullcontext()):
            controller.publish_worker_memory(root, observed, time.monotonic() + 30)
        write(root / "model-initialization-exit-memory.json", {})
        write(root / "worker-supervisor.json", self.receipt("PROCESS_GROUP_CLEANUP_UNVERIFIED"))
        self.assertEqual(controller.export_job(root, archive, self.plan, self.binding, "pilot"), "FORENSIC_ONLY")
        self.assertFalse(archive.exists())
        diagnostic = controller.diagnostic_path(archive)
        verified = verify_archive(diagnostic)
        self.assertIn(controller.WORKER_MEMORY, verified)
        self.assertNotIn("model-initialization-exit-memory.json", verified)
        with ZipFile(diagnostic) as bundle:
            self.assertEqual(json.loads(bundle.read(controller.WORKER_MEMORY)), observed)

    @unittest.skipUnless(os.name == "posix", "real Linux worker supervision")
    def test_supervisor_samples_load_before_sigkill(self):
        import sys

        root = self.root / "killed"
        root.mkdir()
        receipt = root / "worker-supervisor.json"
        program = (
            "import os, signal, sys, time; from pathlib import Path; "
            "Path(sys.argv[1], 'model-load-start.json').touch(); "
            "time.sleep(2); os.kill(os.getpid(), signal.SIGKILL)"
        )
        with controller.observe_worker_load(root) as observed:
            with self.assertRaisesRegex(RuntimeError, "SUPERVISED_CHILD_FAILURE"):
                controller.supervision.run([sys.executable, "-B", "-c", program, str(root)],
                    cwd=self.root, env=os.environ.copy(), deadline=time.monotonic() + 15,
                    log=root / "worker.log", receipt=receipt, max_log_bytes=65536)
        self.assertTrue(observed["load_samples"])
        self.assertEqual(observed["after_worker_status"], "OBSERVED")
        self.assertTrue(controller.supervision.process_group_closed(json.loads(receipt.read_bytes())))

    @unittest.skipUnless(os.name == "posix", "real Linux worker supervision")
    def test_stalled_load_sampler_cannot_extend_hard_worker_deadline(self):
        import sys
        from threading import Event

        root = self.root / "hung"
        root.mkdir()
        write(root / "model-load-start.json", {})
        entered, release = Event(), Event()

        def stalled_snapshot():
            entered.set()
            release.wait(timeout=15)
            return {}

        receipt = root / "worker-supervisor.json"
        try:
            with patch.object(memory, "snapshot", side_effect=stalled_snapshot):
                with controller.observe_worker_load(root) as observed:
                    with self.assertRaisesRegex(RuntimeError, "SUPERVISED_HARD_DEADLINE"):
                        controller.supervision.run([sys.executable, "-B", "-c", "import time; time.sleep(20)"],
                            cwd=self.root, env=os.environ.copy(), deadline=time.monotonic() + 2,
                            log=root / "worker.log", receipt=receipt, max_log_bytes=65536)
                    self.assertTrue(entered.is_set())
                frozen = dict(observed)
                self.assertEqual(frozen["after_worker_status"], "UNAVAILABLE")
        finally:
            release.set()
        diagnosis = json.loads(receipt.read_bytes())
        self.assertLess(diagnosis["seconds"], 3.5)
        self.assertTrue(controller.supervision.process_group_closed(diagnosis))
        self.assertEqual(observed, frozen)

    def test_observing_low_ram_does_not_drop_returned_output(self):
        class Cuda:
            mem_get_info = staticmethod(lambda device: (10, 20))
            memory_allocated = staticmethod(lambda device: 1)
            memory_reserved = staticmethod(lambda device: 2)
            max_memory_allocated = staticmethod(lambda device: 3)

        with patch.object(environment, "host_memory", return_value={"available_bytes": 2**30}):
            report = ct1_native.memory_headroom(SimpleNamespace(cuda=Cuda), before_call=False)
            self.assertEqual(report["host"]["available_bytes"], 2**30)
            self.assertEqual(len(report["devices"]), 2)
            with self.assertRaisesRegex(ValueError, "CT1_AVAILABLE_HOST_RAM"):
                ct1_native.memory_headroom(SimpleNamespace(cuda=Cuda), before_call=True)

    def test_model_ram_guard_precedes_weight_load(self):
        import sys
        events = []
        model = SimpleNamespace(from_pretrained=lambda *a, **kw: events.append("load"))
        modules = {"torch": SimpleNamespace(float16="fp16"),
                   "transformers": SimpleNamespace(Qwen3VLForConditionalGeneration=model)}
        def gate():
            events.append("ram")
            raise ValueError("HOST_OR_CGROUP_RAM")
        with (patch.dict(sys.modules, modules),
              patch.object(qwen, "native_setup", return_value=(None, None, None)),
              patch.object(ct1_native, "prompt", return_value=b"fixture")):
            with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                ct1_native.Backend(self.root, nb.ROOT, before_load=gate)
        self.assertEqual(events, ["ram"])

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
