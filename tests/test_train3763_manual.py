"""Adversarial CPU fixtures only. No Kaggle sockets, real images or inference."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import io
import json
import logging
from pathlib import Path
import shutil
import tempfile
import threading
import time
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

DOWNLOAD_OUTPUTS = m.download_outputs


def output_fixture(archive, *, gcs=False):
    """Sanitized real /kf/run/token/name shape; no actual bearer token."""
    names = (archive.name, archive.name + ".sha256.json")
    base = ("https://storage.googleapis.com/kaggle-output/synthetic/" if gcs else
        "https://www.kaggleusercontent.com/kf/367225876/SYNTHETIC_header..SYNTHETIC_iv.SYNTHETIC_ciphertext.SYNTHETIC_tag/")
    return {"files": [{"fileName": name, "url": base + name + ("?synthetic=1" if gcs else "")}
        for name in names], "log": "SYNTHETIC_PROVIDER_LOG", "nextPageToken": None}


class OutputTransport:
    """Real requests + SDK serialization, replaced only at HTTPAdapter.send."""
    def __init__(self, case, archive, *, gcs=False):
        self.case, self.archive = case, archive
        self.output = output_fixture(archive, gcs=gcs)
        self.payloads = {archive.name: archive.read_bytes(), archive.name + ".sha256.json":
            Path(str(archive)+".sha256.json").read_bytes() if Path(str(archive)+".sha256.json").exists()
            else json.dumps({"sha256": sha(archive)}).encode()}
        self.gets, self.listings = [], []
        self.status, self.error, self.headers, self.clock = 200, None, {}, None
        self.expected_timeout = None
        self.stream_error = False
        self.diagnostics = False
        self.on_get = None

    def send(self, request, **kwargs):
        response = requests.Response(); response.status_code = 200
        response.request, response.url = request, request.url
        if request.method == "POST":
            if self.diagnostics:
                logging.getLogger("kagglesdk").warning("SYNTHETIC_SECRET_URL %s", json.dumps(self.output))
            self.case.assertTrue(request.url.endswith("/ListKernelSessionOutput"))
            fields = json.loads(request.body); self.listings.append(fields)
            self.case.assertEqual(fields["versionLabel"], "v1")
            self.case.assertEqual(kwargs["timeout"], (10, 30))
            response._content = json.dumps(self.output).encode()
            response.headers["Content-Type"] = "application/json"
        else:
            self.case.assertEqual(request.method, "GET")
            self.case.assertNotIn("Authorization", request.headers)
            self.case.assertNotIn("Cookie", request.headers)
            self.case.assertEqual(kwargs["proxies"], {})
            self.case.assertTrue(kwargs["stream"])
            self.case.assertIs(kwargs["verify"], True)
            self.case.assertEqual(request.headers["Accept-Encoding"], "identity")
            self.case.assertTrue(all(0 < v <= cap for v, cap in zip(kwargs["timeout"], (10, 30))))
            if self.expected_timeout is not None:
                self.case.assertEqual(kwargs["timeout"], self.expected_timeout)
            self.gets.append(request.url)
            if self.diagnostics:
                logging.getLogger("urllib3.connectionpool").warning("SYNTHETIC_SECRET_URL %s", request.url)
            if self.on_get is not None:
                self.on_get()
            if self.error:
                raise self.error
            response.status_code = self.status
            response.headers.update(self.headers)
            name = request.url.split("?", 1)[0].rsplit("/", 1)[-1]
            response.raw = io.BytesIO(self.payloads[name])
            if self.status != 200:
                response.iter_content = Mock(side_effect=AssertionError("NO_ERROR_BODY_READ"))
            if self.clock is not None:
                self.clock[0] = 241
            if self.stream_error:
                def chunks(*args):
                    yield b"partial"
                    raise requests.ReadTimeout("SYNTHETIC_SECRET_URL")
                response.iter_content = chunks
        return response

    def install(self, stack):
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        # Environment credentials/proxies must not reach the anonymous GET.
        stack.enter_context(patch.dict("os.environ", {"HTTPS_PROXY": "http://127.0.0.1:9"}))
        stack.enter_context(patch("requests.sessions.get_netrc_auth", side_effect=AssertionError("NO_NETRC")))
        stack.enter_context(patch.object(requests.adapters.HTTPAdapter, "send", side_effect=self.send))

try:
    import requests
    from kagglesdk import KaggleClient
except ImportError:
    KaggleClient = None


class ManualFixture(unittest.TestCase):
    handoff_submission_intent = True
    handoff_blocked_report = True
    handoff_mode = m.DISTINCT_SLUG

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
        if self.handoff_submission_intent:
            self.session.event("SUBMISSION_INTENT")  # Attempt8 only: not ledger PUSH_INTENT
        if self.handoff_blocked_report:
            self.session.report("BLOCKED", reason="SYNTHETIC_GITHUB_API_RATE_LIMIT")
        self.handoff_before = self.snapshot()
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

    def snapshot(self):
        return m.handoff_snapshot(self.session, self.request, mode=self.handoff_mode)

    def assert_unchanged(self):
        self.assertEqual(len(self.ledger.events()), 1)
        self.assertEqual((self.ledger.root / "journal-000001.json").read_bytes(), self.original_journal)
        self.assertEqual(self.snapshot(), self.handoff_before)


class ManualCollectionTests(ManualFixture):
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
        self.assertEqual(self.snapshot(), self.handoff_before)
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

    @unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
    def test_cdn_zip_sidecar_download_flows_through_original_collection(self):
        self.client.build_kaggle_client.side_effect = lambda: KaggleClient(api_token="SYNTHETIC_ONLY")
        self.download.side_effect = DOWNLOAD_OUTPUTS
        transport = OutputTransport(self, self.archive)
        transport.install(self.stack)
        event = self.run_collection()
        self.assertEqual(event["manual"]["output"]["sha256"], self.checksum)
        self.assertEqual((self.root / "evidence" / self.archive.name).read_bytes(), self.archive.read_bytes())
        self.assertEqual(event["manual"]["science_sha256"], digest(c.science()))
        self.assertEqual(event["manual"]["source_sha256"], digest(r.source_spec()))
        self.assertEqual(len(transport.gets), 2)
        self.assertEqual(len(transport.listings), 1)
        self.assertEqual([e["kind"] for e in self.ledger.events()], ["INTENT", "COLLECTED"])
        self.client.kernels_push.assert_not_called()

    @unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
    def test_download_failures_preserve_both_journals_handoff_partials_and_redact_urls(self):
        self.client.build_kaggle_client.side_effect = lambda: KaggleClient(api_token="SYNTHETIC_ONLY")
        self.download.side_effect = DOWNLOAD_OUTPUTS
        transport = OutputTransport(self, self.archive)
        transport.install(self.stack)
        clock = [0]
        self.stack.enter_context(patch.object(m.time, "monotonic", side_effect=lambda: clock[0]))
        for mode in ("redirect", "connect-timeout", "read-timeout", "deadline", "changed-bytes", "unsafe"):
            transport.status, transport.error, transport.clock, transport.stream_error = 200, None, None, False
            transport.output = output_fixture(self.archive)
            transport.payloads[self.archive.name] = self.archive.read_bytes()
            clock[0] = 0
            if mode == "redirect":
                transport.status = 302
                transport.headers = {"Location": "http://127.0.0.1/SYNTHETIC_SECRET_URL"}
            elif mode == "connect-timeout":
                transport.error = requests.ConnectTimeout("https://www.kaggleusercontent.com/SYNTHETIC_SECRET_URL")
            elif mode == "read-timeout": transport.stream_error = True
            elif mode == "deadline": transport.clock = clock
            elif mode == "changed-bytes":
                transport.payloads[self.archive.name] = b"X" * self.archive.stat().st_size
            else: transport.output["files"][1]["url"] = "https://attacker.invalid/SYNTHETIC_SECRET_URL"
            directory = "failure-" + mode
            with self.subTest(mode=mode), self.assertRaises(ValueError) as error:
                self.run_collection(directory)
            self.assertNotIn("SYNTHETIC_SECRET_URL", str(error.exception))
            self.assertIn({"redirect": "MANUAL_OUTPUT_HTTP_STATUS", "deadline": "MANUAL_DOWNLOAD_BOUND",
                "unsafe": "MANUAL_UNSAFE_OUTPUT_URL", "changed-bytes": "MANUAL_PROVIDER_ARCHIVE_MISMATCH"}.get(
                    mode, "PROVIDER_IO_UNVERIFIED"), str(error.exception))
            blocked = (self.root / directory / "BLOCKED.json").read_text()
            self.assertNotIn("SYNTHETIC_SECRET_URL", blocked)
            self.assertNotIn("https://", blocked)
            self.assert_unchanged()
            self.assertEqual((self.ledger.mirror / "journal-000001.json").read_bytes(), self.original_journal)
            if mode == "read-timeout":
                self.assertEqual((self.root / directory / self.archive.name).read_bytes(), b"partial")
        # No overwrite/retry of an evidence directory or its BLOCKED receipt.
        before = (self.root / "failure-read-timeout/BLOCKED.json").read_bytes()
        with self.assertRaises(FileExistsError): self.run_collection("failure-read-timeout")
        self.assertEqual((self.root / "failure-read-timeout/BLOCKED.json").read_bytes(), before)
        self.client.kernels_push.assert_not_called()


class SameSlugCollectionTests(ManualFixture):
    handoff_submission_intent = False
    handoff_mode = m.SAME_SLUG

    def setUp(self):
        super().setUp()
        self.owner.pop("original_job_not_run")
        self.owner.update(job=self.request["job"], mode=m.SAME_SLUG, ledger_events=1,
            ledger_head_sha256=digest(self.intent), plan_sha256=digest(self.request["plan"]),
            scheduled_ordinals=self.request["plan"]["scheduled_ordinals"], input_sources=op.input_sources(self.request),
            no_api_submission=True, no_other_job_or_version=True)
        self.owner_locator = self.comment(3100, m.SAME_OWNER_MARKER, self.owner, authority.OWNER, 180)
        audit = self.comment(3101, m.SAME_TOOL_MARKER + "_AUDIT", {"reviewed_head": "c"*40,
            "script_sha256": sha(m.__file__), "status": "PASS", "independent": True}, "synthetic-auditor", 192)
        self.tool = {"implementation_pr": 192, "reviewed_head": "c"*40, "merged_sha": "d"*40,
            "script_sha256": sha(m.__file__), "audit": audit, "scope": "SAME_SCHEDULED_SLUG_COLLECTION_ONLY",
            "owner": self.owner_locator}
        self.tool_locator = self.comment(3102, m.SAME_TOOL_MARKER, self.tool, "synthetic-reviewer", 192)
        self.comments["/pulls/192"] = {"merged": True, "head": {"sha": "c"*40}, "merge_commit_sha": "d"*40,
            "base": {"ref": "main"}}
        self.provider["job_id"] = self.request["job"]
        self.inventory.return_value = {"original_job_absent": False}

    def run_collection(self, directory="evidence", *, check_only=False):
        return m.reconcile(self.ledger, self.session, self.archive, self.owner_locator, self.tool_locator,
            self.root / directory, mode=m.SAME_SLUG, check_only=check_only)

    def test_same_slug_truthful_collection_original_histories_measure_and_no_fake_submit(self):
        ManualCollectionTests.test_truthful_collection_existing_measure_and_resume_without_refund(self)
        event = [e for e in self.ledger.events() if e["kind"] == "COLLECTED"][0]
        self.assertEqual(event["manual"]["mode"], m.SAME_SLUG)
        self.assertFalse(event["manual"]["inventory"]["original_job_absent"])
        self.assertEqual(event["manual"]["owner_attestation"], self.owner)

    def test_read_only_preflight_never_appends_and_append_repeats_every_gate(self):
        result = self.run_collection("check", check_only=True)
        self.assertEqual(result["status"], "READ_ONLY_VERIFIED")
        self.assertFalse(result["ledger_appended"])
        self.assertEqual(read(self.root/"check/verification.json")["collection"], "NOT_APPENDED_CHECK_ONLY")
        self.assert_unchanged()
        self.run_collection("collect")
        self.assertEqual(self.download.call_count, 2)
        self.assertEqual(self.observe.call_count, 4)
        self.assertEqual([e["kind"] for e in self.ledger.events()], ["INTENT", "COLLECTED"])

    def test_v1_owner_or_tool_record_cannot_authorize_same_slug(self):
        for owner, tool in ((self.owner_locator, {"comment_id": 3002,
                "body_sha256": hashlib.sha256(self.comments["/issues/comments/3002"]["body"].encode()).hexdigest()}),
                ({"comment_id": 3000, "body_sha256": hashlib.sha256(
                    self.comments["/issues/comments/3000"]["body"].encode()).hexdigest()}, self.tool_locator)):
            with self.assertRaises(ValueError):
                m.reconcile(self.ledger, self.session, self.archive, owner, tool, self.root/"unused", mode=m.SAME_SLUG)
            self.assert_unchanged()
        self.observe.assert_not_called()

    def test_reviewer_release_must_pin_this_exact_owner_locator(self):
        self.owner_locator = self.comment(3199, m.SAME_OWNER_MARKER, self.owner, authority.OWNER, 180)
        with self.assertRaisesRegex(ValueError, "REVIEWER_EXACT_OWNER_RELEASE"): self.run_collection()
        self.assert_unchanged(); self.observe.assert_not_called()

    def test_wrong_parent_history_blocks_before_provider(self):
        self.history["parent_history_sha256"] = "0"*64
        with self.assertRaisesRegex(ValueError, "HISTORY_LINEAGE"): self.run_collection()
        self.assert_unchanged(); self.observe.assert_not_called()

    def test_forged_owner_facts_wrong_mode_slug_version_kernel_plan_inputs_and_ledger_stop(self):
        original = deepcopy(self.owner)
        for key, bad in (("campaign_sha256", "0"*64), ("intent_sha256", "0"*64), ("request_sha256", "0"*64),
                ("job", "nguynanhtn/different"), ("version", 2), ("version", True), ("kernel_id", 0),
                ("mode", m.DISTINCT_SLUG), ("ledger_events", 29), ("ledger_events", True),
                ("ledger_head_sha256", "0"*64), ("plan_sha256", "0"*64), ("scheduled_ordinals", [1]),
                ("scheduled_ordinals", [False]), ("input_sources", {}), ("no_api_submission", False),
                ("no_other_job_or_version", False), ("archive_sha256", "0"*64), ("archive_bytes", 1)):
            with self.subTest(key=key, bad=bad):
                self.owner_locator = self.comment(3100, m.SAME_OWNER_MARKER, {**original, key: bad}, authority.OWNER, 180)
                with self.assertRaises(ValueError): self.run_collection()
                self.assert_unchanged()
        for login, issue in (("attacker", 180), (authority.OWNER, 192)):
            self.owner_locator = self.comment(3100, m.SAME_OWNER_MARKER, original, login, issue)
            with self.assertRaisesRegex(ValueError, "AUTHENTIC_OWNER"): self.run_collection()
        self.assert_unchanged(); self.observe.assert_not_called()

    def test_edited_owner_comment_and_duplicate_json_key_fail_authentication(self):
        comment = self.comments["/issues/comments/3100"]
        comment["body"] += "edited"
        with self.assertRaisesRegex(ValueError, "COMMENT_HASH_ID_DRIFT"): self.run_collection()
        duplicate = m.SAME_OWNER_MARKER + '\n```json\n{"mode":"x","mode":"y"}\n```'
        comment["body"] = duplicate
        self.owner_locator = {"comment_id": 3100, "body_sha256": hashlib.sha256(duplicate.encode()).hexdigest()}
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CAMPAIGN_KEY"): self.run_collection()
        self.assert_unchanged()

    def test_unmerged_stale_head_wrong_script_or_nonindependent_audit_stop(self):
        pr = self.comments["/pulls/192"]
        for key, bad in (("merged", False), ("head", {"sha": "e"*40}), ("merge_commit_sha", "e"*40)):
            original = deepcopy(pr[key]); pr[key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError): self.run_collection()
            pr[key] = original
        for value in ({**self.tool, "scope": "MANUAL_COLLECTION_ONLY"}, {**self.tool, "script_sha256": "0"*64}):
            self.tool_locator = self.comment(3102, m.SAME_TOOL_MARKER, value, "synthetic-reviewer", 192)
            with self.assertRaises(ValueError): self.run_collection()
        self.tool_locator = self.comment(3102, m.SAME_TOOL_MARKER, self.tool, "synthetic-reviewer", 192)
        self.comments["/issues/comments/3101"]["user"]["login"] = "attacker"
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_AUDIT"): self.run_collection()
        self.assert_unchanged()

    def test_handoff_submission_intent_and_submission_directory_are_ambiguous(self):
        (self.session.root/"submission").mkdir()
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_SUBMISSION_FILES"): self.run_collection()
        self.session.event("SUBMISSION_INTENT")
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_HANDOFF"): self.run_collection()
        self.assertEqual(len(self.ledger.events()), 1)
        self.observe.assert_not_called()

    def test_submitted_event_without_push_intent_also_blocks(self):
        with lock(self.ledger.root):
            self.ledger.append("SUBMITTED", intent_sha256=digest(self.intent), result={"job_id": self.request["job"], "version": 1})
        with self.assertRaisesRegex(ValueError, "POSSIBLE_API_SUBMIT"): self.run_collection()
        self.observe.assert_not_called()

    def test_preserved_sidecar_bytes_cannot_be_replaced_by_semantically_similar_provider_bytes(self):
        copy = self.download.side_effect
        def altered(*args):
            result = copy(*args)
            sidecar = args[-1]/(self.archive.name+".sha256.json")
            sidecar.write_bytes(sidecar.read_bytes()+b"\n")
            return result
        self.download.side_effect = altered
        with self.assertRaisesRegex(ValueError, "PRESERVED_SIDECAR_BYTES"): self.run_collection()
        self.assert_unchanged()
        self.assertTrue((self.root/"evidence/BLOCKED.json").exists())

    def test_authority_history_inventory_or_handoff_changed_before_append_stops(self):
        for boundary, error in ((self.inventory, "MANUAL_INVENTORY_CHANGED"),):
            boundary.side_effect = [{"original_job_absent": False}, {"original_job_absent": True}]
            with self.assertRaisesRegex(ValueError, error): self.run_collection("inventory-changed")
        self.assert_unchanged()
        self.inventory.side_effect = None
        copy = self.download.side_effect
        def edited(*args):
            result = copy(*args)
            self.comments["/issues/comments/3100"]["body"] += "edited"
            return result
        self.download.side_effect = edited
        with self.assertRaisesRegex(ValueError, "COMMENT_HASH_ID_DRIFT"): self.run_collection("owner-changed")
        self.assert_unchanged()

    # Exercise the existing failure/rollback/timeout paths in BOTH modes.
    test_possible_api_submit = ManualCollectionTests.test_possible_api_submit_never_relabels_as_owner_manual
    test_replay_and_concurrency = ManualCollectionTests.test_replay_and_concurrent_collector_do_not_append_or_download_twice
    test_archive_and_native_custody = ManualCollectionTests.test_bad_sidecar_or_raw_hash_and_wrong_native_claim_stop
    test_inputs_capsule_provider = ManualCollectionTests.test_wrong_inputs_capsule_provider_bytes_and_conflicting_status_leave_open_intent
    test_future_provider_observation = ManualCollectionTests.test_provider_changes_during_collection_preserves_all_outputs_without_append
    test_mirror_loss = ManualCollectionTests.test_lost_or_diverged_mirror_blocks_before_provider
    test_torn_append = ManualCollectionTests.test_torn_collected_mirror_never_reports_success_or_allows_retry_measure_resume
    test_real_sdk_same_slug_output = ManualCollectionTests.test_cdn_zip_sidecar_download_flows_through_original_collection
    test_real_sdk_timeout_partial = ManualCollectionTests.test_download_failures_preserve_both_journals_handoff_partials_and_redact_urls


class PreparedSameSlugCollectionTests(SameSlugCollectionTests):
    """Repeat the V2 orchestration/adversarial suite with a genuine no-report handoff."""
    handoff_blocked_report = False

    def test_prepared_check_only_preserves_request_events_package_and_both_journals(self):
        package = self.session.root/"package/safeshift_train3763_execution.json"
        write(package, {"request": self.request, "campaign_intent": self.intent})
        def fingerprint(root):
            return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
                if p.is_file() and p.name != "operator.lock"}
        roots = (self.session.root, self.ledger.root, self.ledger.mirror)
        before = [fingerprint(root) for root in roots]
        with patch.object(self.session, "report", side_effect=AssertionError("NO_FAKE_BLOCKED_REPORT")), \
                patch.object(self.session, "event", side_effect=AssertionError("NO_SYNTHETIC_EVENT")), \
                patch.object(self.ledger, "append", side_effect=AssertionError("NO_CHECK_ONLY_APPEND")):
            receipt = self.run_collection("prepared-check", check_only=True)
        self.assertEqual(receipt["status"], "READ_ONLY_VERIFIED")
        self.assertFalse(receipt["ledger_appended"])
        self.assertEqual([fingerprint(root) for root in roots], before)
        self.assertIsNone(self.session.latest_report())
        self.assertEqual([e["status"] for e in self.session.events()], ["PREPARED"])
        self.assertEqual(receipt["manual"]["handoff"]["head_sha256"], digest(self.session.events()[0]))
        self.assertEqual(receipt["manual"]["handoff"]["files"][package.relative_to(self.session.root).as_posix()], sha(package))
        with self.assertRaises(FileExistsError): self.run_collection("prepared-check", check_only=True)
        self.assertEqual([fingerprint(root) for root in roots], before)

    def test_genuine_blocked_event_appended_during_collection_is_preserved_and_stops_append(self):
        copy = self.download.side_effect
        def changed(*args):
            result = copy(*args)
            self.session.report("BLOCKED", reason="SYNTHETIC_CONCURRENT_OPERATOR_STOP")
            return result
        self.download.side_effect = changed
        with self.assertRaisesRegex(ValueError, "LOCAL_CUSTODY_CHANGED"): self.run_collection()
        self.assertEqual(len(self.ledger.events()), 1)
        self.assertEqual((self.ledger.root/"journal-000001.json").read_bytes(), self.original_journal)
        self.assertEqual(self.session.latest_report()["reason"], "SYNTHETIC_CONCURRENT_OPERATOR_STOP")
        self.assertEqual([e["status"] for e in self.session.events()], ["PREPARED", "BLOCKED"])
        self.assertTrue((self.root/"evidence/BLOCKED.json").exists())


class HandoffSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, _, _ = fixture(self.root/"ledger")
        self.patch = patch.object(handoff, "private_root", side_effect=lambda p: Path(p))
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.number = 0

    def prepare(self):
        self.number += 1
        return handoff.prepare(self.root/f"handoff-{self.number}", self.request)

    def test_original_prepared_is_v2_only_and_v1_keeps_historical_blocked_behavior(self):
        session = self.prepare()
        before = m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        self.assertEqual(set(before["files"]), {"request.json", "event-00001.json"})
        with self.assertRaisesRegex(ValueError, "IMMUTABLE_BLOCKED_HANDOFF_REQUIRED"):
            m.handoff_snapshot(session, self.request)
        session.event("SUBMISSION_INTENT")
        session.report("BLOCKED", reason="SYNTHETIC_HISTORICAL_PREFLIGHT_FAILURE")
        v1 = m.handoff_snapshot(session, self.request)
        self.assertEqual(v1["head_sha256"], digest(session.events()[-1]))
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_HANDOFF_SUBMISSION_INTENT"):
            m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)

    def test_truthful_blocked_reports_are_verified_and_preserved_without_replacement(self):
        session = self.prepare()
        session.report("BLOCKED", reason="SYNTHETIC_EXISTING_STOP")
        first = m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        session.report("BLOCKED", reason="SYNTHETIC_SECOND_READ_ONLY_STOP")
        second = m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        self.assertTrue(first["files"].items() <= second["files"].items())
        self.assertEqual(session.latest_report()["reason"], "SYNTHETIC_SECOND_READ_ONLY_STOP")
        old = session.root/"report-00002.json"
        old.write_bytes(old.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "REPORT_HASH_DRIFT"):
            m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)

    def test_extra_events_and_fake_statuses_never_become_prepared_or_blocked(self):
        for status in ("PREPARED", "BLOCKED", "UNKNOWN", "AGY_INVOCATION_INTENT", "SUBMISSION_INTENT",
                "SUBMITTED", "OBSERVED", "RUNNING_UNVERIFIED", "PASS", "FAIL"):
            for with_report in (False, True):
                with self.subTest(status=status, with_report=with_report):
                    session = self.prepare()
                    session.event(status)
                    if with_report: session.report("BLOCKED", reason="SYNTHETIC_FAKE_STATUS_COVER")
                    with self.assertRaises(ValueError):
                        m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        for status in ("PREPARED", "PASS", "UNKNOWN"):
            session = self.prepare(); session.report(status)
            with self.subTest(report_status=status), self.assertRaises(ValueError):
                m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)

    def test_missing_gapped_tampered_or_misbound_prepared_event_and_request_stop(self):
        changes = ({"binding": "0"*64}, {"previous": "0"*64}, {"schema": "wrong"}, {"status": "BLOCKED"},
            {"status": "UNKNOWN"}, {"utc": None}, {"report_sha256": "0"*64}, {"extra": True})
        for change in changes:
            session = self.prepare(); event = session.root/"event-00001.json"
            event.write_text(json.dumps({**read(event), **change}), encoding="utf-8")
            with self.subTest(change=change), self.assertRaises(ValueError):
                m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        for action in (lambda p: p.unlink(), lambda p: p.rename(p.with_name("event-00002.json"))):
            session = self.prepare(); action(session.root/"event-00001.json")
            with self.assertRaises(ValueError): m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        session = self.prepare()
        (session.root/"request.json").write_text(json.dumps({**self.request, "job": "nguynanhtn/wrong"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ORIGINAL_HANDOFF_REQUEST_REQUIRED"):
            m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        session = self.prepare()
        with self.assertRaisesRegex(ValueError, "IMMUTABLE_BLOCKED_HANDOFF_REQUIRED"):
            m.handoff_snapshot(session, {**self.request, "handoff_id": "wrong"}, mode=m.SAME_SLUG)

    def test_submission_directory_and_orphan_reports_block_even_without_report_event(self):
        for name in ("submission", "report-00002.json"):
            session = self.prepare(); (session.root/name).mkdir()
            with self.subTest(name=name), self.assertRaises(ValueError):
                m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)
        session = self.prepare()
        write(session.root/"report-00002.json", {"status": "BLOCKED"})
        with self.assertRaisesRegex(ValueError, "UNREFERENCED_HANDOFF_REPORT"):
            m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)

    def test_resealed_blocked_report_with_false_binding_status_or_event_stops(self):
        for key, bad in (("binding", "0"*64), ("status", "PREPARED"), ("schema", "wrong"),
                ("job_id", "nguynanhtn/wrong"), ("notebook_sha256", "0"*64)):
            session = self.prepare(); session.report("BLOCKED")
            path = session.root/"report-00002.json"
            path.write_text(json.dumps({**read(path), key: bad}), encoding="utf-8")
            event = session.root/"event-00002.json"
            event.write_text(json.dumps({**read(event), "report_sha256": sha(path)}), encoding="utf-8")
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "BOUND_BLOCKED_REPORT_REQUIRED"):
                m.handoff_snapshot(session, self.request, mode=m.SAME_SLUG)


class ManualSourceTests(unittest.TestCase):
    def test_200_ordinals_3_to_202_replay_exact_completion_and_preserve_invalid(self):
        from test_internvl3763 import PreparedControllerTests
        helper = PreparedControllerTests("test_shared_controller_archive_raw_before_parse_and_full_denominator")
        helper.setUp(); self.addCleanup(helper.doCleanups)
        cohort, histories = helper.cohort, []
        for ordinal in range(3):
            p = c.plan(cohort, histories, action="initial" if ordinal == 0 else "resume",
                run_id=f"synthetic200-{ordinal}", attempt_id=f"synthetic-{ordinal}", max_calls=1, max_seconds=1800)
            histories.append({"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
                "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"],
                "action": p["action"], "evidence_sha256": str(ordinal+1)*64, "repair": None,
                "records": [{**cohort["samples"][ordinal], "status": "SUCCESS", "label": "Level02", "attempts": 1,
                    "native_calls": 1, "raw_sha256": "f"*64, "hnlo": None, "hnlo_status": r.HNLO_STATUS}]})
        p = c.plan(cohort, histories, action="resume", run_id="synthetic200-9", attempt_id="attempt-9",
            max_calls=200, max_seconds=7200)
        self.assertEqual(p["scheduled_ordinals"], list(range(3, 203)))
        def image_path(row):
            from safeshift.candidates.fulltrain_run import synthetic_bytes
            path = helper.root/f"image-{row['ordinal']}"; path.write_bytes(synthetic_bytes(row["ordinal"]))
            return path
        good, invalid = helper.backend(), helper.backend("SYNTHETIC_INVALID")
        def generate(image, sample, binding, deadline):
            return (invalid if sample.name == "000103" else good).generate(image, sample, binding, deadline)
        backend = NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=generate)
        archive = helper.root/"200.zip"
        r.rehearse(helper.root/"200", archive, cohort, p, histories, lambda _: backend,
            image_path=image_path, tokenizer_sha="a"*64)
        result = r.verify_bundle(archive, sha(archive), p)
        ancestor = r.sealed_history(archive, sha(archive), p)
        self.assertEqual(result["model_calls"], 200, result)
        self.assertEqual(len(ancestor["records"]), 200, result)
        m.verify_scheduled_completion({"plan": p}, {"reserved_calls": 200}, result, ancestor)
        self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3563, "SUCCESS": 199, "INVALID": 1})
        self.assertEqual(len(ancestor["records"]), 200)
        self.assertEqual(ancestor["parent_history_sha256"], digest(histories))
        for change in (lambda a: a["records"].pop(), lambda a: a["records"].reverse(),
                lambda a: a["records"][0].update(ordinal=2), lambda a: a["records"][0].update(ordinal=203),
                lambda a: a["records"][1].update(ordinal=3), lambda a: a["records"][0].update(native_calls=0),
                lambda a: a["records"][0].update(status="TECHNICAL_ERROR")):
            changed = deepcopy(ancestor); change(changed)
            with self.assertRaisesRegex(ValueError, "EXACT_SCHEDULED_COMPLETION"):
                m.verify_scheduled_completion({"plan": p}, {"reserved_calls": 200}, result, changed)
        with self.assertRaisesRegex(ValueError, "EXACT_SCHEDULED_COMPLETION"):
            m.verify_scheduled_completion({"plan": p}, {"reserved_calls": 200}, {**result, "model_calls": 199}, ancestor)
        # Re-sealing cannot turn a missing trace into valid completion.
        import zipfile
        folder = helper.root/"trace-tamper"
        with zipfile.ZipFile(archive) as z: z.extractall(folder)  # synthetic files only
        (folder/"checksums.json").unlink()
        (folder/"samples/000003/trace-verification.json").unlink()
        altered = helper.root/"missing-trace.zip"; checksum = export(folder, altered)
        with self.assertRaisesRegex(ValueError, "TRACE_RECEIPT_REQUIRED"):
            r.verify_bundle(altered, checksum, p)
        wrong_plan = deepcopy(p); wrong_plan["scheduled_ordinals"][0] = 2
        with self.assertRaisesRegex(ValueError, "ARCHIVE_PLAN_BINDING"):
            r.verify_bundle(archive, sha(archive), wrong_plan)

    def test_same_slug_inventory_rejects_missing_unknown_aborted_and_repeated_pages(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, _ = fixture(Path(d)/"ledger")
            intent = {"kind": "INTENT", "request": req}
            ledger = NS(grant=grant, events=lambda: [intent], intents=lambda: [intent])
            response = NS(kernels=[NS(ref=req["job"])], next_page_token=None)
            client = NS(kernels_list_with_response=Mock(return_value=response))
            proof = m.inventory(client, ledger, intent, req["job"], mode=m.SAME_SLUG)
            self.assertFalse(proof["original_job_absent"])
            for refs in ([], [req["job"], req["job"]], [req["job"], req["job"][:-1]+"99"]):
                response.kernels = [NS(ref=ref) for ref in refs]
                with self.subTest(refs=refs), self.assertRaises(ValueError):
                    m.inventory(client, ledger, intent, req["job"], mode=m.SAME_SLUG)
            response.kernels, response.next_page_token = [], "SYNTHETIC_REPEATED_TOKEN"
            with self.assertRaisesRegex(ValueError, "REPEATED_INVENTORY_PAGE"):
                m.inventory(client, ledger, intent, req["job"], mode=m.SAME_SLUG)

    def test_same_slug_inventory_verifies_actual_distinct_and_same_slug_predecessors(self):
        with tempfile.TemporaryDirectory() as d:
            req, grant, _ = fixture(Path(d)/"ledger")
            first = {"kind": "INTENT", "request": req}
            second = {"kind": "INTENT", "request": {**req, "job": req["job"][:-1]+"2"}}
            current = {"kind": "INTENT", "request": {**req, "job": req["job"][:-1]+"3"}}
            closed = [{"kind": "COLLECTED", "intent_sha256": digest(previous),
                "provider": {"job_id": job, "state": "COMPLETE", "kernel_id": kernel}}
                for previous, job, kernel in ((first, "nguynanhtn/synthetic-ui-result", 111),
                    (second, second["request"]["job"], 222))]
            events = [first, closed[0], second, closed[1], current]
            ledger = NS(grant=grant, events=lambda: events, intents=lambda: [first, second, current])
            response = NS(kernels=[NS(ref=job) for job in ("nguynanhtn/synthetic-ui-result",
                second["request"]["job"], current["request"]["job"])], next_page_token=None)
            client = NS(kernels_list_with_response=Mock(return_value=response))
            content = b'{"cells":[]}'
            for previous in (first, second): previous["request"]["notebook_sha256"] = hashlib.sha256(content).hexdigest()
            for row, previous in zip(closed, (first, second)): row["intent_sha256"] = digest(previous)
            with patch.object(m.subprocess, "check_output", return_value=content), \
                    patch.object(m, "observe_kernel", return_value={"state": "COMPLETE"}) as observe:
                proof = m.inventory(client, ledger, current, current["request"]["job"], mode=m.SAME_SLUG)
                self.assertEqual(len(proof["predecessors"]), 2)
                self.assertEqual([call.args[1] for call in observe.call_args_list],
                    ["nguynanhtn/synthetic-ui-result", second["request"]["job"]])
                observe.side_effect = ValueError("MANUAL_PROVIDER_IDENTITY_OR_VERSION")
                with self.assertRaisesRegex(ValueError, "PROVIDER_IDENTITY_OR_VERSION"):
                    m.inventory(client, ledger, current, current["request"]["job"], mode=m.SAME_SLUG)
                observe.side_effect = None
                closed[0]["kind"] = "ABORTED_PRE_SUBMIT"
                response.kernels.append(NS(ref=first["request"]["job"]))
                with self.assertRaises(ValueError):
                    m.inventory(client, ledger, current, current["request"]["job"], mode=m.SAME_SLUG)

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

    def test_same_scheduled_slug_exact_five_inputs_and_latest_v1_are_required(self):
        job = "nguynanhtn/safeshift-train3763-synthetic180-9"
        self.meta.update(ref=job, datasetDataSources=["nguynanhtn/synthetic-"+str(n) for n in range(5)])
        self.sources["dataset_sources"] = [ref+"/1" for ref in self.meta["datasetDataSources"]]
        original = deepcopy(self.meta)
        def observe():
            with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                    patch.object(requests.adapters.HTTPAdapter, "send", self.send):
                return m.observe_kernel(self.client, job, 1, self.notebook, self.sources, kernel_id=123)
        self.assertEqual(observe()["job_id"], job)
        for refs in (original["datasetDataSources"][:-1], original["datasetDataSources"]+["nguynanhtn/extra"],
                original["datasetDataSources"]+[original["datasetDataSources"][0]]):
            self.meta = {**original, "datasetDataSources": refs}
            with self.subTest(refs=refs), self.assertRaisesRegex(ValueError, "INPUT_DRIFT"): observe()
        self.meta = original
        real_send = self.send
        def future(adapter, request, **kwargs):
            if "versionLabel" not in json.loads(request.body): self.meta["currentVersionNumber"] = 2
            return real_send(request, **kwargs)
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(requests.adapters.HTTPAdapter, "send", future), \
                self.assertRaisesRegex(ValueError, "IDENTITY_OR_VERSION"):
            m.observe_kernel(self.client, job, 1, self.notebook, self.sources, kernel_id=123)

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
            output = output_fixture(archive, gcs=True)
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
                    payload = sidecar if ".sha256.json?" in request.url else archive.read_bytes()
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


class ManualOutputUrlTests(unittest.TestCase):
    def test_canonical_cdn_and_signed_gcs_exact_zip_and_sidecar(self):
        for name in ("ivl35-train3763-8-synthetic.zip", "ivl35-train3763-8-synthetic.zip.sha256.json"):
            m.validate_output_url("https://www.kaggleusercontent.com/kf/367225876/SYNTHETIC_token-123/" + name, name)
            m.validate_output_url("https://storage.googleapis.com/bucket/output/" + name + "?X-Goog-Signature=SYNTHETIC%2F1", name)

    def test_observed_five_part_token_with_empty_second_field_is_one_path_segment(self):
        for name in ("synthetic.zip", "synthetic.zip.sha256.json"):
            for token in ("SYNTHETIC_header..SYNTHETIC_iv.SYNTHETIC_ciphertext.SYNTHETIC_tag",
                    "h"*47 + ".." + "i"*22 + "." + "c"*640 + "." + "t"*22):
                m.validate_output_url("https://www.kaggleusercontent.com/kf/367225876/" + token + "/" + name, name)

    def test_dotted_token_does_not_enable_traversal_escapes_or_arbitrary_punctuation(self):
        base = "https://www.kaggleusercontent.com/kf/367225876/"
        for token in (".", "..", "...", "header.iv.tag", "header.key.iv.cipher.tag", "header..iv.cipher.",
                ".key.iv.cipher.tag", "header...cipher.tag", "header..iv..tag", "header..iv.cipher.tag.extra",
                "header..iv.cipher.tag=", "header..iv.cipher.tag;", "header%2e%2eiv.cipher.tag",
                "header..iv.cipher%2ftag", "header..iv.cipher%5ctag", "header..iv/../tag", "header..iv?cipher.tag"):
            with self.subTest(token=token), self.assertRaisesRegex(ValueError, "^MANUAL_UNSAFE_OUTPUT_URL$"):
                m.validate_output_url(base + token + "/synthetic.zip", "synthetic.zip")

    def test_rejects_ambiguous_or_unsafe_origins_paths_tokens_and_names(self):
        name = "synthetic.zip"
        valid = "https://www.kaggleusercontent.com/kf/367225876/SYNTHETIC_token-123/" + name
        bad = [None, 123, "", valid + "x" * 16384]
        for host in ("kaggleusercontent.com", "evil.www.kaggleusercontent.com", "www.kaggleusercontent.com.evil.invalid",
                "WWW.KAGGLEUSERCONTENT.COM", "www.kaggleusercontent.com.", "www.kaggleusercontent.com:443",
                "www.kaggleusercontent.com:80", "user@www.kaggleusercontent.com", "www.kaggleusercontent.com@evil.invalid",
                "127.0.0.1", "[::1]", "169.254.169.254", "www.kaggleusercontent.com%2f.evil.invalid",
                "www.kaggleusercоntent.com", "[broken"):
            bad.append(valid.replace("www.kaggleusercontent.com", host))
        for path in ("/kf/0/token/", "/kf/-1/token/", "/kf/1.5/token/", "/kf/１２/token/", "/kf/1//",
                "/kf/1/../", "/kf/1/./", "/kf/1/token=/", "/kf/1/token;/", "/kf/1/tok%65n/",
                "/kf/1/tok%2fen/", "/kf/1/tok%5cen/", "/kf/1/tok%252fen/", "/kf/1/token/extra/",
                "//kf/1/token/", "/KF/1/token/", "/other/1/token/", "/kf/1/token/../"):
            bad.append("https://www.kaggleusercontent.com" + path + name)
        bad += [valid + suffix for suffix in ("?", "?signature=x", "#", "#fragment", "/", ".sha256.json", ";x")]
        bad += [valid.replace("synthetic.zip", ending) for ending in
            ("wrong.zip", "Synthetic.zip", "%73ynthetic.zip", "synthetic%2Ezip", "synthetic.zip%00", "synthetic.zip%2f")]
        bad += [valid.replace("https:", scheme) for scheme in ("http:", "file:", "ftp:", "HTTPS:")]
        bad += [" " + valid, valid + "\n", valid.replace("/kf/", "/kf\\"), valid.replace("token", "tok\ten")]
        gcs = "https://storage.googleapis.com/bucket/" + name + "?signed=1"
        bad += [gcs.split("?")[0], gcs.replace("?signed=1", "?"), gcs.replace("/bucket/", "/../"),
            gcs.replace("/bucket/", "/%2e%2e/"), gcs.replace(name, "wrong.zip"),
            gcs.replace("storage.googleapis.com", "storage.googleapis.com.evil.invalid"),
            gcs.replace("storage.googleapis.com", "storage.googleapis.com:443"), gcs + "#"]
        for url in bad:
            with self.subTest(case=bad.index(url)), self.assertRaisesRegex(ValueError, "^MANUAL_UNSAFE_OUTPUT_URL$"):
                m.validate_output_url(url, name)


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
class ManualDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / "synthetic.zip"
        # Real, tiny ZIP fixture, no real raw/model/image bytes.
        import zipfile
        with zipfile.ZipFile(self.archive, "w") as bundle:
            bundle.writestr("notice.txt", "SYNTHETIC_CPU_FIXTURE")
        self.transport = OutputTransport(self, self.archive)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.transport.install(self.stack)
        self.client = NS(build_kaggle_client=lambda: KaggleClient(api_token="SYNTHETIC_ONLY"))
        self.counter = 0

    def download(self):
        self.counter += 1
        destination = self.root / str(self.counter); destination.mkdir()
        proof = DOWNLOAD_OUTPUTS(self.client, "nguynanhtn/synthetic-ui-result", 1,
            self.archive, sha(self.archive), destination)
        return destination, proof

    def test_cdn_and_gcs_download_zip_sidecar_byte_for_byte(self):
        for gcs in (False, True):
            self.transport.output = output_fixture(self.archive, gcs=gcs)
            destination, proof = self.download()
            self.assertEqual((destination / self.archive.name).read_bytes(), self.archive.read_bytes())
            self.assertEqual(proof["sha256"], sha(self.archive))
            self.assertEqual(proof["sidecar_sha256"], sha(destination / (self.archive.name + ".sha256.json")))
            self.assertEqual(proof["bytes"], self.archive.stat().st_size)
            self.assertNotIn("SYNTHETIC_token", json.dumps(proof))
        self.assertEqual(len(self.transport.gets), 4)
        self.assertEqual(len(self.transport.listings), 2)

    def test_rejects_unsafe_sidecar_before_any_get_and_preserves_exact_listing(self):
        original = deepcopy(self.transport.output)
        mutations = [lambda o: o["files"][1].update(url="https://attacker.invalid/secret"),
            lambda o: o["files"].append(o["files"][0]),
            lambda o: o["files"].pop(),
            lambda o: o["files"].append({"fileName": "extra.zip", "url": "https://attacker.invalid"}),
            lambda o: o.update(nextPageToken="more"), lambda o: o.update(log=""),
            lambda o: o.update(log=None), lambda o: o.update(log="X" * (16*2**20 + 1))]
        for mutate in mutations:
            self.transport.output = deepcopy(original); mutate(self.transport.output)
            with self.assertRaises(ValueError): self.download()
            self.assertEqual(self.transport.gets, [])

    def test_redirect_and_http_errors_never_follow_or_retry(self):
        self.transport.headers = {"Location": "http://127.0.0.1/secret"}
        for status in (301, 302, 303, 307, 308, 404, 500):
            self.transport.status = status
            before = len(self.transport.gets)
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "OUTPUT_HTTP_STATUS"):
                self.download()
            self.assertEqual(len(self.transport.gets), before + 1)

    def test_length_stream_limits_and_sidecar_checksum_fail_closed(self):
        original = deepcopy(self.transport.payloads)
        cases = [({"Content-Length": str(self.archive.stat().st_size + 1)}, original),
            ({"Content-Length": "invalid"}, original), ({"Content-Encoding": "gzip"}, original),
            ({}, {**original, self.archive.name: original[self.archive.name] + b"extra"}),
            ({}, {**original, self.archive.name + ".sha256.json": b"X" * 4097}),
            ({}, {**original, self.archive.name + ".sha256.json": json.dumps({"sha256": "0" * 64}).encode()}),
            ({}, {**original, self.archive.name: original[self.archive.name][:-1]})]
        for headers, payloads in cases:
            self.transport.headers, self.transport.payloads = headers, payloads
            with self.assertRaises(ValueError): self.download()

    def test_total_deadline_before_get_during_stream_eof_and_between_files(self):
        # before GET, after headers, during chunk, EOF and before sidecar GET
        for moments in ([0, 241], [0, 0, 0, 241], [0, 0, 0, 0, 241],
                [0, 0, 0, 0, 0, 241], [0, 0, 0, 0, 0, 0, 0, 241]):
            with self.subTest(moments=moments), patch.object(m.time, "monotonic", side_effect=moments), \
                    self.assertRaisesRegex(ValueError, "DOWNLOAD_BOUND"):
                self.download()

    def test_verbose_sdk_and_transport_logs_never_print_tokens_and_logging_is_restored(self):
        from contextlib import redirect_stdout, redirect_stderr
        self.client.build_kaggle_client = lambda: KaggleClient(api_token="SYNTHETIC_ONLY", verbose=True)
        self.transport.diagnostics = True
        output = io.StringIO()
        before = logging.root.manager.disable
        with redirect_stdout(output), redirect_stderr(output):
            self.download()
        self.assertNotIn("SYNTHETIC_SECRET_URL", output.getvalue())
        self.assertNotIn("SYNTHETIC_header", output.getvalue())
        self.assertNotIn("Authorization", output.getvalue())
        self.assertEqual(logging.root.manager.disable, before)
        self.transport.error = requests.ReadTimeout("SYNTHETIC_SECRET_URL")
        with self.assertRaises(requests.ReadTimeout): self.download()
        self.assertEqual(logging.root.manager.disable, before)

    def test_declared_length_must_equal_bytes_including_sidecar(self):
        self.transport.headers = {"Content-Length": "1"}
        with self.assertRaisesRegex(ValueError, "OUTPUT_LENGTH_MISMATCH"): self.download()

    def test_disk_budget_failure_stops_before_listing_or_get(self):
        with patch.object(m.shutil, "disk_usage", return_value=NS(free=0)), \
                self.assertRaisesRegex(ValueError, "DOWNLOAD_DISK_BOUND"):
            self.download()
        self.assertEqual(self.transport.listings, [])
        self.assertEqual(self.transport.gets, [])

    def test_late_get_uses_remaining_budget_and_create_only_files(self):
        clock = [0]
        def now():
            value = clock[0]; clock[0] = 238
            return value
        self.transport.expected_timeout = (1, 1)
        with patch.object(m.time, "monotonic", side_effect=now):
            destination, _ = self.download()
        with self.assertRaises(FileExistsError):
            DOWNLOAD_OUTPUTS(self.client, "nguynanhtn/synthetic-ui-result", 1,
                self.archive, sha(self.archive), destination)


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
class ManualDeadlineTests(unittest.TestCase):
    def setUp(self):
        self.guard = patch("socket.socket", side_effect=AssertionError("NO_NETWORK"))
        self.guard.start(); self.addCleanup(self.guard.stop)

    def test_watchdog_interrupts_registered_tls_socket_and_never_changes_global_pool_registry(self):
        import socket
        from urllib3.connection import HTTPSConnection
        from urllib3.poolmanager import pool_classes_by_scheme
        before = dict(pool_classes_by_scheme)
        stopped = threading.Event()
        sock = Mock(); sock.shutdown.side_effect = lambda _: stopped.set()
        def connected(connection): connection.sock = sock
        started = time.monotonic()
        with patch.object(HTTPSConnection, "connect", connected), self.assertRaisesRegex(ValueError, "DOWNLOAD_BOUND"):
            with m.anonymous_output_session(started + .05) as http:
                pool = http.adapters["https://"].poolmanager.pool_classes_by_scheme["https"]
                connection = pool.ConnectionCls("www.kaggleusercontent.com")
                connection.connect()
                self.assertEqual(connection.debuglevel, 0)
                self.assertTrue(stopped.wait(2))
        sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        self.assertEqual(pool_classes_by_scheme, before)
        self.assertLess(time.monotonic() - started, 2)

    def test_watchdog_cleanup_on_success_exception_and_timer_start_failure(self):
        before = logging.root.manager.disable
        for error in (None, ValueError("SYNTHETIC_BODY_FAILURE")):
            timer = Mock()
            with patch.object(m.threading, "Timer", return_value=timer):
                if error:
                    with self.assertRaisesRegex(ValueError, "SYNTHETIC_BODY_FAILURE"):
                        with m.anonymous_output_session(time.monotonic() + 10): raise error
                else:
                    with m.anonymous_output_session(time.monotonic() + 10): pass
            timer.cancel.assert_called_once(); timer.join.assert_called_once()
            self.assertEqual(logging.root.manager.disable, before)
        timer = Mock(); timer.start.side_effect = RuntimeError("SYNTHETIC_THREAD_UNAVAILABLE")
        with patch.object(m.threading, "Timer", return_value=timer), self.assertRaises(RuntimeError):
            with m.anonymous_output_session(time.monotonic() + 10): pass
        timer.cancel.assert_called_once(); timer.join.assert_not_called()
        self.assertEqual(logging.root.manager.disable, before)

    def test_connection_completed_after_deadline_is_closed_without_admission(self):
        from urllib3.connection import HTTPSConnection
        sock = Mock()
        def connected(connection): connection.sock = sock
        clock = [0]
        with patch.object(m.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(HTTPSConnection, "connect", connected), patch.object(m.threading, "Timer"), \
                self.assertRaisesRegex(ValueError, "DOWNLOAD_BOUND"):
            with m.anonymous_output_session(10) as http:
                pool = http.adapters["https://"].poolmanager.pool_classes_by_scheme["https"]
                clock[0] = 11
                pool.ConnectionCls("www.kaggleusercontent.com").connect()
        sock.shutdown.assert_called_once()

if __name__ == "__main__":
    unittest.main()
