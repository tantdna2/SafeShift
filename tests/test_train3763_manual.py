"""Adversarial CPU fixtures only. No Kaggle sockets, real images or inference."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from scripts import reconcile_train3763_manual as m
from safeshift import internvl3763 as r, internvl3763_campaign as c, internvl3763_operator as op
from safeshift import internvl3763_release as authority, kaggle_handoff as handoff
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import digest
from test_internvl3763_campaign import fixture
from test_internvl3763 import make_real_memory_snapshot

try:
    import requests
    from kagglesdk import KaggleClient
except ImportError:
    KaggleClient = None


class ManualCollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, self.grant, self.comments = fixture(self.root / "ledger")
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(authority, "get", side_effect=lambda p: deepcopy(self.comments[p])))
        self.stack.enter_context(patch.object(handoff, "private_root", side_effect=lambda p: Path(p)))
        self.stack.enter_context(patch.object(m, "private_root", side_effect=lambda p: Path(p)))
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        self.ledger = c.Ledger.create(self.root / "ledger", self.root / "mirror", self.grant, "synthetic-machine")
        self.intent = self.ledger.reserve(self.request)
        self.session = handoff.prepare(self.root / "handoff", self.request)
        self.session.event("SUBMISSION_INTENT")  # actual Attempt8 preflight sequence; NOT ledger PUSH_INTENT
        self.session.report("BLOCKED", reason="SYNTHETIC_GITHUB_API_RATE_LIMIT")
        self.handoff_before = m.handoff_snapshot(self.session, self.request)
        self.original_journal = (self.ledger.root / "journal-000001.json").read_bytes()
        self.notebook = {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC_ONLY')"]}],
            "metadata": {"safeshift": {"source_sha256": digest(r.source_spec())}}}
        # CPU receipt/arithmetic fixture. Native authenticity is explicitly a
        # boundary seam here, not a claim that these scripted bytes are native.
        folder = self.root / "bundle"
        write(folder / "handoff.json", self.request)
        write(folder / "release.json", self.grant)
        write(folder / "campaign-intent.json", self.intent)
        row = self.request["bindings"]["runtime"]["execution_request"]["cohort"]["samples"][0]
        record = {**row, "status": "SUCCESS", "label": "Level02", "attempts": 1, "native_calls": 1, "raw_sha256": "f"*64,
            "hnlo": None, "hnlo_status": r.HNLO_STATUS}
        write(folder / "run/summary.json", {"records": [record], "notice": "SYNTHETIC_CPU_FIXTURE"})
        for kind, name in (("launch", "launch-claim.json"), ("worker", "environment/worker-claim.json"),
                ("load", "run/load-claim.json"), ("call-000000", "run/samples/000000/call-claim.json")):
            write(folder / name, c.native_receipt(kind, self.request, self.intent, self.grant))
        write(folder / "setup/setup-supervisor.json", {"seconds": 10})
        write(folder / "environment/preload-resources.json", {"free_bytes": [20*2**30, 20*2**30]})
        write(folder / "run/telemetry.json", {"evidence_kind": "NATIVE", "samples": [{"ordinal": 0, "seconds": 2, "bytes": 1000}],
            "load_seconds": 5, "gpu_peak_allocated_bytes": 100, "gpu_peak_reserved_bytes": 200,
            "memory": make_real_memory_snapshot(self.root / "mem"), "notice": "SYNTHETIC_ARITHMETIC_ONLY"})
        (folder / "run/scripted.f32").write_bytes(b"\0"*16)
        self.archive = self.root / "synthetic.zip"; self.checksum = export(folder, self.archive)
        p = self.request["plan"]
        self.history = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
            "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"],
            "action": p["action"], "records": [record], "evidence_sha256": self.checksum, "repair": p["repair"]}
        self.owner = {"campaign_sha256": digest(self.grant), "intent_sha256": digest(self.intent),
            "request_sha256": digest(self.request), "job": "nguynanhtn/synthetic-ui-result", "version": 1,
            "kernel_id": 123, "archive_sha256": self.checksum, "archive_bytes": self.archive.stat().st_size,
            "operator": m.PROVENANCE, "original_job_not_run": True}
        self.owner_locator = self.comment(3000, m.OWNER_MARKER, self.owner, authority.OWNER, 180)
        audit = self.comment(3001, m.TOOL_MARKER + "_AUDIT", {"reviewed_head": "a"*40,
            "script_sha256": sha(m.__file__), "status": "PASS", "independent": True}, "synthetic-auditor", 190)
        self.tool = {"implementation_pr": 190, "reviewed_head": "a"*40, "merged_sha": "b"*40,
            "script_sha256": sha(m.__file__), "audit": audit, "scope": "MANUAL_COLLECTION_ONLY"}
        self.tool_locator = self.comment(3002, m.TOOL_MARKER, self.tool, "synthetic-reviewer", 190)
        self.comments["/pulls/190"] = {"merged": True, "head": {"sha": "a"*40}, "merge_commit_sha": "b"*40,
            "base": {"ref": "main"}}
        self.stack.enter_context(patch.object(m, "approved_source", return_value=self.notebook))
        self.stack.enter_context(patch.object(r, "verify_bundle", side_effect=self.verify_fixture))
        self.stack.enter_context(patch.object(r, "sealed_history", return_value=self.history))
        self.inputs = self.stack.enter_context(patch.object(m, "verify_inputs_in_archive"))
        self.client = Mock()
        self.stack.enter_context(patch.object(op, "api", return_value=self.client))
        self.provider = {"state": "COMPLETE", "job_id": self.owner["job"], "version": 1, "kernel_id": 123}
        self.observe = self.stack.enter_context(patch.object(m, "observe_kernel", side_effect=lambda *a, **kw: deepcopy(self.provider)))
        self.inventory = self.stack.enter_context(patch.object(m, "inventory", return_value={"original_job_absent": True}))
        self.stack.enter_context(patch.object(op, "verify_execution_input", return_value={"intent_sha256": digest(self.intent)}))
        self.download = self.stack.enter_context(patch.object(m, "download_outputs", side_effect=self.copy_output))

    def comment(self, number, marker, value, login, issue):
        body = marker + "\n```json\n" + json.dumps(value) + "\n```"
        self.comments["/issues/comments/"+str(number)] = {"id": number, "body": body,
            "user": {"login": login}, "issue_url": authority.API + "/issues/" + str(issue)}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}

    def verify_fixture(self, archive, checksum, plan):
        self.assertEqual(plan, self.request["plan"])
        self.assertEqual(sha(archive), checksum)
        r.verify_archive(archive)
        if read(str(archive)+".sha256.json")["sha256"] != checksum:
            raise ValueError("ZIP_SIDECAR")
        return {"status": "PASS", "scope": "PRIVATE_TRAIN_METADATA", "model_calls": 1,
            "notice": "SYNTHETIC_NATIVE_VERIFIER_BOUNDARY_ONLY"}

    def copy_output(self, client, job, version, archive, checksum, destination):
        shutil.copyfile(archive, destination / archive.name)
        shutil.copyfile(str(archive)+".sha256.json", destination / (archive.name+".sha256.json"))
        write(destination / "provider.log", {"notice": "SYNTHETIC_PROVIDER_LOG"})
        return {"sha256": checksum, "log_sha256": sha(destination / "provider.log")}

    def run_collection(self, directory="evidence"):
        return m.reconcile(self.ledger, self.session, self.archive, self.owner_locator, self.tool_locator, self.root / directory)

    def assert_unchanged(self):
        self.assertEqual(len(self.ledger.events()), 1)
        self.assertEqual((self.ledger.root / "journal-000001.json").read_bytes(), self.original_journal)
        self.assertEqual(m.handoff_snapshot(self.session, self.request), self.handoff_before)

    def test_truthful_collection_existing_measure_and_resume_without_refund(self):
        event = self.run_collection()
        self.assertEqual([e["kind"] for e in self.ledger.events()], ["INTENT", "COLLECTED"])
        self.assertEqual(event["manual"]["provenance"], "OWNER_UI_MANUAL")
        self.assertFalse(event["manual"]["refund"])
        self.assertEqual(event["provider"]["job_id"], self.owner["job"])
        self.assertEqual(event["manual"]["original_job"], self.request["job"])
        self.assertIsNone(self.ledger.open_intent())
        history, custody = self.ledger.histories()
        self.assertEqual(history, [self.history])
        self.assertEqual(self.ledger.summary()["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(self.ledger.summary()["reserved_gpu_seconds"], 3600)
        measured = self.ledger.measure(Path(custody[0]["path"]), job_seconds=1800)
        self.assertEqual(measured["source_sha256"], digest(r.source_spec()))
        self.assertEqual(measured["safe_calls"], 4)
        cohort = self.request["bindings"]["runtime"]["execution_request"]["cohort"]
        next_plan = c.plan(cohort, history, action="resume", run_id="synthetic180-2", attempt_id="attempt-2",
            max_calls=2, max_seconds=1800)
        self.assertEqual(next_plan["scheduled_ordinals"], [1, 2])
        self.assertEqual(m.handoff_snapshot(self.session, self.request), self.handoff_before)
        self.client.kernels_push.assert_not_called()

    def test_replay_and_concurrent_collector_do_not_append_or_download_twice(self):
        with lock(self.ledger.root), self.assertRaises(RuntimeError):
            self.run_collection()
        self.run_collection()
        with self.assertRaisesRegex(ValueError, "EXACT_OPEN_INTENT"):
            self.run_collection("second")
        self.assertEqual(self.download.call_count, 1)
        self.assertEqual(len(self.ledger.events()), 2)

    def test_tampered_owner_identity_intent_archive_version_and_budget_bindings(self):
        original = deepcopy(self.owner)
        for key, bad in (("intent_sha256", "0"*64), ("request_sha256", "0"*64),
                ("campaign_sha256", "0"*64), ("archive_sha256", "0"*64), ("archive_bytes", 1),
                ("job", self.request["job"]), ("job", "attacker/wrong"), ("version", True),
                ("version", 2), ("kernel_id", 0), ("operator", "API_SUBMITTED"), ("original_job_not_run", False)):
            with self.subTest(key=key, bad=bad):
                value = {**original, key: bad}
                self.owner_locator = self.comment(3000, m.OWNER_MARKER, value, authority.OWNER, 180)
                with self.assertRaises(ValueError): self.run_collection()
                self.assert_unchanged()
        self.owner_locator = self.comment(3000, m.OWNER_MARKER, original, "attacker", 180)
        with self.assertRaisesRegex(ValueError, "AUTHENTIC_OWNER"): self.run_collection()
        self.assert_unchanged()

    def test_unaudited_unmerged_or_modified_tool_cannot_collect(self):
        for path, key, bad in (("/pulls/190", "merged", False),):
            self.comments[path][key] = bad
            with self.assertRaises(ValueError): self.run_collection()
        self.comments["/pulls/190"]["merged"] = True
        for value in ({**self.tool, "script_sha256": "0"*64}, {**self.tool, "scope": "EXECUTION"}):
            self.tool_locator = self.comment(3002, m.TOOL_MARKER, value, "synthetic-reviewer", 190)
            with self.assertRaises(ValueError): self.run_collection()
        self.tool_locator = self.comment(3002, m.TOOL_MARKER, self.tool, "synthetic-reviewer", 190)
        self.comments["/issues/comments/3001"]["user"]["login"] = "attacker"
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_AUDIT"): self.run_collection()
        self.assert_unchanged(); self.observe.assert_not_called()

    def test_possible_api_submit_never_relabels_as_owner_manual(self):
        with lock(self.ledger.root): self.ledger.append("PUSH_INTENT", intent_sha256=digest(self.intent))
        with self.assertRaisesRegex(ValueError, "POSSIBLE_API_SUBMIT"): self.run_collection()
        self.observe.assert_not_called()

    def test_bad_sidecar_or_raw_hash_and_wrong_native_claim_stop(self):
        sidecar = Path(str(self.archive)+".sha256.json")
        original = sidecar.read_bytes(); sidecar.write_text('{"sha256":"wrong"}')
        with self.assertRaisesRegex(ValueError, "ZIP_SIDECAR"): self.run_collection()
        sidecar.write_bytes(original)
        with patch.object(c, "verify_native_custody", side_effect=ValueError("NATIVE_CAMPAIGN_CLAIM_DRIFT")), \
                self.assertRaisesRegex(ValueError, "NATIVE_CAMPAIGN_CLAIM_DRIFT"): self.run_collection()
        self.archive.write_bytes(self.archive.read_bytes()+b"tamper")
        with self.assertRaisesRegex(ValueError, "ARCHIVE_BINDING"): self.run_collection()
        self.assert_unchanged()

    def test_wrong_inputs_capsule_provider_bytes_and_conflicting_status_leave_open_intent(self):
        targets = ((self.inputs, ValueError("MANUAL_TRAIN_INPUT_BYTES")),
            (self.observe, ValueError("MANUAL_PROVIDER_IDENTITY_OR_VERSION")),
            (self.inventory, ValueError("MANUAL_ORIGINAL_JOB_ABSENCE_OR_HISTORY")),
            (self.download, ValueError("MANUAL_PROVIDER_ARCHIVE_MISMATCH")))
        for i, (target, error) in enumerate(targets):
            original = target.side_effect
            target.side_effect = error
            with self.subTest(error=str(error)), self.assertRaises(ValueError): self.run_collection("blocked"+str(i))
            target.side_effect = original
            self.assert_unchanged()
        with patch.object(op, "verify_execution_input", side_effect=ValueError("STALE_OR_WRONG_CAPSULE")), \
                self.assertRaises(ValueError): self.run_collection("capsule-fail")
        self.assert_unchanged()

    def test_provider_changes_during_collection_preserves_all_outputs_without_append(self):
        self.observe.side_effect = [deepcopy(self.provider), {**self.provider, "kernel_id": 456}]
        with self.assertRaises(ValueError): self.run_collection()
        self.assertTrue((self.root / "evidence/synthetic.zip").exists())
        self.assertTrue((self.root / "evidence/BLOCKED.json").exists())
        self.assertEqual(read(self.root / "evidence/BLOCKED.json")["reason_code"], "MANUAL_PROVIDER_CHANGED_DURING_COLLECTION")
        self.assert_unchanged()

    def test_ledger_reservation_drift_and_stale_handoff_cannot_be_reconciled(self):
        name = "journal-000001.json"
        event = read(self.ledger.root/name); event["reserved_gpu_seconds"] = 1
        for root in (self.ledger.root, self.ledger.mirror):
            (root/name).write_text(json.dumps(event))
        with self.assertRaisesRegex(ValueError, "RESERVATION_DRIFT"): self.run_collection()
        for root in (self.ledger.root, self.ledger.mirror): (root/name).write_bytes(self.original_journal)
        other = handoff.prepare(self.root/"wrong-handoff", {**self.request, "handoff_id": "different"})
        with self.assertRaisesRegex(ValueError, "EXACT_OPEN_INTENT"):
            m.reconcile(self.ledger, other, self.archive, self.owner_locator, self.tool_locator, self.root/"unused")
        self.assert_unchanged()

    def test_receipt_does_not_reuse_standalone_measurement_without_collected(self):
        with self.assertRaisesRegex(ValueError, "VERIFIED_FINAL_SOURCE_MEASUREMENT_REQUIRED"):
            self.ledger.measure(self.archive, job_seconds=1800)
        self.assert_unchanged()

    def test_collection_destination_cannot_write_inside_immutable_handoff_or_journals(self):
        for protected in (self.session.root, self.ledger.root, self.ledger.mirror):
            with self.subTest(protected=protected.name), self.assertRaisesRegex(ValueError, "INDEPENDENT_EVIDENCE"):
                m.reconcile(self.ledger, self.session, self.archive, self.owner_locator, self.tool_locator, protected/"outputs")
            self.assertFalse((protected/"outputs").exists())
        self.assert_unchanged(); self.observe.assert_not_called()

    def test_changed_downloaded_provider_copy_cannot_be_appended_after_reobservation(self):
        calls = 0
        def observe(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.root / "evidence/synthetic.zip").write_bytes(b"SYNTHETIC_CHANGED_LOCAL_COPY")
            return deepcopy(self.provider)
        self.observe.side_effect = observe
        with self.assertRaises(ValueError): self.run_collection()
        self.assert_unchanged()
        self.assertTrue((self.root / "evidence/BLOCKED.json").exists())

    def test_lost_or_diverged_mirror_blocks_before_provider(self):
        mirror = self.ledger.mirror / "journal-000001.json"
        original = mirror.read_bytes(); mirror.write_bytes(original+b" ")
        with self.assertRaisesRegex(ValueError, "DIVERGENCE"): self.run_collection()
        mirror.unlink()
        with self.assertRaisesRegex(ValueError, "ROLLBACK"): self.run_collection()
        self.observe.assert_not_called()

    def test_torn_collected_mirror_never_reports_success_or_allows_retry_measure_resume(self):
        real_write = c.write
        def fail_mirror(path, value):
            if Path(path).parent == self.ledger.mirror and value.get("kind") == "COLLECTED":
                raise OSError("SYNTHETIC_DISK_FULL")
            return real_write(path, value)
        with patch.object(c, "write", side_effect=fail_mirror), self.assertRaises(ValueError): self.run_collection()
        with self.assertRaisesRegex(ValueError, "ROLLBACK"): c.Ledger(self.ledger.root)
        with self.assertRaisesRegex(ValueError, "ROLLBACK"): self.ledger.measure(self.archive, job_seconds=1800)
        with self.assertRaisesRegex(ValueError, "ROLLBACK"): self.run_collection("retry")
        self.assertEqual(self.download.call_count, 1)


class ManualSourceTests(unittest.TestCase):
    def test_companion_is_outside_manifest_and_native_source_science_unchanged(self):
        self.assertNotIn("scripts/reconcile_train3763_manual.py", r.source_spec()["manifest"])
        self.assertEqual(digest(r.source_spec()), "f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d")
        self.assertEqual(digest(c.science()), "ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50")

    def test_source_hash_equality_does_not_waive_exact_merged_commit(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, comments = fixture(Path(d)/"ledger", actual_source=True)
            with patch.object(authority, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(m.subprocess, "check_output", return_value="0"*40), \
                    self.assertRaisesRegex(ValueError, "ORIGINAL_CLEAN_APPROVED_CHECKOUT"):
                m.approved_source(NS(grant=grant), req)

    def test_original_approved_notebook_and_clean_commit_pass_without_moving_head(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, comments = fixture(Path(d)/"ledger", actual_source=True)
            notebook = read(r.ROOT/req["notebook"])
            key = "/issues/comments/2002"
            original = comments[key]
            revision = json.loads(original["body"].split("```json\n", 1)[1].split("\n```", 1)[0])
            revision["notebook_code_sha256"] = op.code_hash(notebook)
            body = "SAFESHIFT_TRAIN3763_TECHNICAL_V1\n```json\n"+json.dumps(revision)+"\n```"
            comments[key] = {**original, "body": body}
            req["bindings"]["runtime"]["technical_revision"]["body_sha256"] = hashlib.sha256(body.encode()).hexdigest()
            real_git = m.subprocess.check_output
            def git(command, **kwargs):
                if command[:3] == ["git", "status", "--porcelain"]: return b""
                return real_git(command, **kwargs)
            with patch.object(authority, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(m.subprocess, "check_output", side_effect=git):
                self.assertEqual(m.approved_source(NS(grant=grant), req), notebook)

    def test_saved_input_receipts_bind_original_train_checkpoint_python_and_capsule(self):
        from safeshift.candidates.source import LOCK
        from safeshift import internvl3763_python as py
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            req, _, _ = fixture(root/"ledger")
            execution = req["bindings"]["runtime"]["execution_request"]
            weights = read(LOCK.with_name("checkpoint_metadata_lock.json"))["internvl35"]
            manifest = py.manifest()
            members = {"execution-request.json": execution,
                "environment/image-bytes.json": {"status": "TRAIN_BYTES_PASS", "master_sha256": execution["input_marker_sha256"],
                    "projection_sha256": execution["projection_sha256"], "verified_images": 3763,
                    "changed": 0, "missing": 0, "duplicate_ids": 0, "labels_exported": False},
                "environment/checkpoint.json": {"source": read(LOCK)["internvl35"], "weights": weights},
                "environment/checkpoint-stream.json": {"status": "ACTUAL_BYTES_VERIFIED", "error": None,
                    "weights_modified": False, "files": [{"file": name, "sha256": value["sha256"],
                        "bytes_hashed": value["size"], "descriptor_identity_unchanged": True}
                        for name, value in weights["weights"].items()]},
                "setup/python-input.json": {"status": "PASS", "ref": py.REF,
                    "sha256": manifest["lock"]["sha256"], "bytes": manifest["lock"]["size_bytes"],
                    "transport_sha256": manifest["transport"]["sha256"], "transport_bytes": manifest["transport"]["size_bytes"],
                    "python_downloads": 0}}
            import zipfile
            def bundle(values):
                archive = root/"inputs.zip"
                with zipfile.ZipFile(archive, "w") as z:
                    for name, value in values.items(): z.writestr(name, json.dumps(value))
                return archive
            m.verify_inputs_in_archive(bundle(members), req)
            for member, key, value in (("execution-request.json", "input_marker_sha256", "0"*64),
                    ("environment/image-bytes.json", "master_sha256", "0"*64),
                    ("environment/image-bytes.json", "projection_sha256", "0"*64),
                    ("environment/image-bytes.json", "missing", 1),
                    ("environment/checkpoint.json", "weights", {}),
                    ("environment/checkpoint-stream.json", "files", []),
                    ("environment/checkpoint-stream.json", "weights_modified", True),
                    ("setup/python-input.json", "sha256", "0"*64),
                    ("setup/python-input.json", "python_downloads", 1)):
                values = deepcopy(members); values[member][key] = value
                with self.subTest(member=member, key=key), self.assertRaises(ValueError):
                    m.verify_inputs_in_archive(bundle(values), req)

    def test_original_raw_verifier_rejects_resealed_changed_response_and_bad_crc(self):
        # Real archive/raw/trace verification, using an explicitly synthetic
        # controller backend. No production-native verdict is mocked here.
        from test_internvl3763 import PreparedControllerTests
        helper = PreparedControllerTests("test_shared_controller_archive_raw_before_parse_and_full_denominator")
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        _, plan = helper.execute()
        original = helper.root/"attempt.zip"
        self.assertEqual(r.verify_bundle(original, sha(original), plan)["status"], "PASS")
        import zipfile
        destination = helper.root/"tamper"
        with zipfile.ZipFile(original) as z: z.extractall(destination)  # our synthetic archive only
        (destination/"checksums.json").unlink()
        raw_path = destination/"samples/000000/raw.json"
        raw = read(raw_path); raw["response"] = '{"safety_level":"Level04"}'
        raw_path.write_text(json.dumps(raw))
        altered = helper.root/"resealed.zip"; checksum = export(destination, altered)
        with self.assertRaisesRegex(ValueError, "RAW_BEFORE_PARSE"):
            r.verify_bundle(altered, checksum, plan)

    def test_provider_inventory_proves_original_slug_absent_and_stops_unknown_campaign_job(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, _ = fixture(Path(d)/"ledger")
            intent = {"kind": "INTENT", "request": req}
            ledger = NS(grant=grant, events=lambda: [intent], intents=lambda: [intent])
            client = NS(kernels_list_with_response=Mock(return_value=NS(
                kernels=[NS(ref="nguynanhtn/synthetic-ui-result")], next_page_token=None)))
            result = m.inventory(client, ledger, intent, "nguynanhtn/synthetic-ui-result")
            self.assertTrue(result["original_job_absent"])
            for extra in (req["job"], "nguynanhtn/safeshift-train3763-synthetic180-99"):
                client.kernels_list_with_response.return_value.kernels.append(NS(ref=extra))
                with self.subTest(extra=extra), self.assertRaisesRegex(ValueError, "ABSENCE_OR_HISTORY"):
                    m.inventory(client, ledger, intent, "nguynanhtn/synthetic-ui-result")
                client.kernels_list_with_response.return_value.kernels.pop()

    def test_resume_keeps_original_success0_1_and_manual_success2_starts_at3(self):
        with tempfile.TemporaryDirectory() as d:
            req, _, _ = fixture(Path(d)/"ledger")
            cohort = req["bindings"]["runtime"]["execution_request"]["cohort"]
            histories = []
            for ordinal in range(3):
                p = c.plan(cohort, histories, action="initial" if ordinal == 0 else "resume",
                    run_id=f"synthetic180-{ordinal+1}", attempt_id=f"attempt-{ordinal+1}", max_calls=1, max_seconds=1800)
                row = cohort["samples"][ordinal]
                histories.append({"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
                    "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"],
                    "action": p["action"], "evidence_sha256": str(ordinal+1)*64, "repair": None,
                    "records": [{**row, "status": "SUCCESS", "label": "Level02", "attempts": 1, "native_calls": 1,
                        "raw_sha256": "f"*64, "hnlo": None, "hnlo_status": r.HNLO_STATUS}]})
            before = deepcopy(histories)
            p = c.plan(cohort, histories, action="resume", run_id="synthetic180-4", attempt_id="attempt-4",
                max_calls=200, max_seconds=7200)
            self.assertEqual(p["scheduled_ordinals"], list(range(3, 203)))
            self.assertEqual(histories, before)
            self.assertEqual(p["counts"], {"SUCCESS": 3, "NOT_ATTEMPTED": 3760})

    def test_manual_kernel_cannot_be_claimed_again_by_a_different_intent(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, _ = fixture(Path(d)/"ledger")
            prior = {"kind": "INTENT", "request": req}
            current = {"kind": "INTENT", "request": {**req, "job": req["job"][:-1]+"2"}}
            collected = {"kind": "COLLECTED", "intent_sha256": digest(prior),
                "provider": {"job_id": "nguynanhtn/synthetic-ui-result", "state": "COMPLETE"}}
            ledger = NS(grant=grant, events=lambda: [prior, collected, current], intents=lambda: [prior, current])
            client = NS(kernels_list_with_response=Mock(return_value=NS(
                kernels=[NS(ref="nguynanhtn/synthetic-ui-result")], next_page_token=None)))
            with self.assertRaisesRegex(ValueError, "REPLAY_OR_MISSING_PREDECESSOR"):
                m.inventory(client, ledger, current, "nguynanhtn/synthetic-ui-result")


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
class ManualSdkTests(unittest.TestCase):
    def setUp(self):
        op.check_sdk()
        self.notebook = {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC_ONLY')"]}],
            "metadata": {"safeshift": {"source_sha256": "f"*64}}}
        self.meta = {"ref": "nguynanhtn/synthetic-ui-result", "id": 123, "isPrivate": True,
            "currentVersionNumber": 1, "machineShape": "NvidiaTeslaT4", "datasetDataSources": ["nguynanhtn/capsule"],
            "kernelDataSources": [], "competitionDataSources": [], "modelDataSources": []}
        self.sources = {"dataset_sources": ["nguynanhtn/capsule/1"], "kernel_sources": []}
        self.calls = []
        self.client = NS(build_kaggle_client=lambda: KaggleClient(api_token="SYNTHETIC_ONLY"),
            kernels_status=lambda _: NS(status="COMPLETE", failure_message=None))

    def send(self, request, **kwargs):
        fields = json.loads(request.body); self.calls.append(fields)
        self.assertEqual(kwargs["timeout"], (10, 30))
        response = requests.Response(); response.status_code = 200
        response._content = json.dumps({"metadata": self.meta, "blob": {"source": json.dumps(self.notebook)}}).encode()
        response.headers["Content-Type"] = "application/json"
        return response

    def observe(self):
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(requests.adapters.HTTPAdapter, "send", self.send):
            return m.observe_kernel(self.client, "nguynanhtn/synthetic-ui-result", 1, self.notebook, self.sources, kernel_id=123)

    def test_real_sdk_pins_v1_then_latest_without_submission(self):
        self.assertEqual(self.observe()["kernel_id"], 123)
        self.assertEqual(self.calls[0]["versionLabel"], "v1")
        self.assertNotIn("versionLabel", self.calls[1])

    def test_ui_metadata_omission_is_explicit_but_changed_retained_binding_stops(self):
        expected = deepcopy(self.notebook)
        self.notebook.pop("metadata")
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(requests.adapters.HTTPAdapter, "send", self.send):
            receipt = m.observe_kernel(self.client, self.meta["ref"], 1, expected, self.sources, kernel_id=123)
            self.assertEqual(receipt["safeshift_metadata"], "ABSENT_EXECUTABLE_CODE_BOUND")
            self.notebook["metadata"] = {"safeshift": {"source_sha256": "0"*64}}
            with self.assertRaisesRegex(ValueError, "NOTEBOOK_DRIFT"):
                m.observe_kernel(self.client, self.meta["ref"], 1, expected, self.sources, kernel_id=123)

    def test_wrong_provider_identity_source_inputs_privacy_version_and_state_stop(self):
        original_meta, original_notebook = deepcopy(self.meta), deepcopy(self.notebook)
        for key, value in (("ref", "nguynanhtn/wrong"), ("id", 456), ("isPrivate", False),
                ("currentVersionNumber", 2), ("machineShape", "NvidiaTeslaP100"),
                ("datasetDataSources", ["nguynanhtn/forged"]), ("modelDataSources", ["attacker/model"])):
            self.meta = {**original_meta, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): self.observe()
        self.meta = original_meta
        expected = deepcopy(self.notebook)
        self.notebook["cells"][0]["source"] = ["print('TAMPER')"]
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(requests.adapters.HTTPAdapter, "send", self.send), self.assertRaisesRegex(ValueError, "NOTEBOOK_DRIFT"):
            m.observe_kernel(self.client, self.meta["ref"], 1, expected, self.sources, kernel_id=123)
        self.notebook = original_notebook
        for status, failure in (("RUNNING", None), ("COMPLETE", "conflicting failure"), ("ERROR", None)):
            self.client.kernels_status = lambda _: NS(status=status, failure_message=failure)
            with self.subTest(status=status), self.assertRaises(ValueError): self.observe()

    def test_provider_output_download_pins_version_hash_sidecar_bounds_and_no_retry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            archive = root/"synthetic.zip"; archive.write_bytes(b"SYNTHETIC_PROVIDER_BYTES")
            checksum = sha(archive)
            sidecar = json.dumps({"sha256": checksum}).encode()
            output = {"files": [{"fileName": archive.name, "url": "https://storage.googleapis.com/test/zip?synthetic=1"},
                {"fileName": archive.name+".sha256.json", "url": "https://storage.googleapis.com/test/sidecar?synthetic=1"}],
                "log": "SYNTHETIC_PROVIDER_LOG", "nextPageToken": None}
            import io
            calls = []
            def send(adapter, request, **kwargs):
                calls.append(request.url)
                response = requests.Response(); response.status_code = 200
                if request.method == "POST":
                    fields = json.loads(request.body)
                    self.assertEqual(fields["versionLabel"], "v1")
                    response._content = json.dumps(output).encode()
                    response.headers["Content-Type"] = "application/json"
                else:
                    payload = archive.read_bytes() if "/zip?" in request.url else sidecar
                    response.raw = io.BytesIO(payload)
                return response
            with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                    patch.object(requests.adapters.HTTPAdapter, "send", send):
                dest = root/"good"; dest.mkdir()
                proof = m.download_outputs(self.client, self.meta["ref"], 1, archive, checksum, dest)
                self.assertEqual(proof["sha256"], checksum)
                self.assertEqual(len(calls), 3)
                dest = root/"wrong-hash"; dest.mkdir()
                with self.assertRaisesRegex(ValueError, "ARCHIVE_MISMATCH"):
                    m.download_outputs(self.client, self.meta["ref"], 1, archive, "0"*64, dest)
                dest = root/"unsafe"; dest.mkdir()
                output["files"][0]["url"] = "https://attacker.invalid/token?secret=1"
                before = len(calls)
                with self.assertRaisesRegex(ValueError, "UNSAFE_OUTPUT_URL"):
                    m.download_outputs(self.client, self.meta["ref"], 1, archive, checksum, dest)
                self.assertEqual(len(calls)-before, 1)  # listing only, no unsafe GET


if __name__ == "__main__":
    unittest.main()
