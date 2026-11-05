"""Synthetic exact-release/official-SDK protocol tests. No Kaggle or images."""
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import HTTPServer
import json
from pathlib import Path
import sqlite3
import os
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import zipfile

from safeshift import internvl3763 as runtime
from safeshift import internvl3763_release as auth
from safeshift import internvl3763_operator as operator
from safeshift.internvl3763_witness import Store, handler
from safeshift.candidates.fulltrain_run import synthetic_cohort
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest
from scripts.rehearse_kaggle_handoff import request as old_request


def fixture():
    """PRIVATE_TRAIN_METADATA-shaped synthetic metadata; never dataset evidence."""
    cohort = synthetic_cohort()
    cohort["scope"] = "PRIVATE_TRAIN_METADATA"
    plan = runtime.plan(cohort, [], action="initial", run_id="synthetic-execution", attempt_id="synthetic-1",
        max_calls=3, max_seconds=1800)
    execution = {"source": runtime.source_spec(), "cohort": cohort, "history": [], "history_archives": [],
        "plan": plan, "input_marker_sha256": "a"*64, "projection_sha256": digest(cohort)}
    request = old_request("synthetic-candidate")
    request.update(scope="TRAIN3763_EXECUTION_CANDIDATE", commit_sha="b"*40, runtime_commit="c"*40,
        job="nguynanhtn/safeshift-train3763-synthetic-test", plan=plan, plan_sha256=digest(plan),
        limits={"monitor_seconds": 900, "job_seconds": 1800, "max_calls": 3})
    request["bindings"]["runtime"] = {"execution_request": execution, "local_history": []}
    request["bindings"]["dataset"] = {"dataset_sources": ["nguynanhtn/synthetic-input/1"],
        "kernel_sources": [], "execution_request_sha256": digest(execution)}
    now = int(time.time())
    grant = {"schema": auth.SCHEMA, "implementation_pr": 179, "reviewed_head": "a"*40,
        "merged_sha": "b"*40, "runtime_commit": "c"*40, "source_sha256": digest(runtime.source_spec()),
        "execution_request_sha256": digest(execution), "request_sha256": auth.request_hash(request),
        "notebook_sha256": request["notebook_sha256"], "notebook_code_sha256": "d"*64,
        "job": request["job"], "version": 1, "series": runtime.SERIES, "attempt": 1,
        "issued_unix": now-10, "expires_unix": now+7200, "witness": "https://witness.invalid", "witness_id": "f"*64,
        "caps": {"calls": 3, "seconds": 1800, "loads": 1, "physical_gpus": 2,
            "machine_shape": "NvidiaTeslaT4", "attempt_gpu_seconds": 3600,
            "campaign_gpu_seconds": 7200, "archive_bytes": 7*2**30},
        "predecessors": [], "approvals": {}, "authorization": "GRANTED_FOR_THIS_EXACT_ATTEMPT"}
    comments = {}
    for i, kind in enumerate(("chatgpt_review", "independent_audit", "merge", "O2", "O3", "O4", "O5", "O6"), 1000):
        body = "SAFESHIFT_TRAIN3763_APPROVAL_V1\n```json\n" + json.dumps({"kind": kind,
            "reviewed_head": grant["reviewed_head"], "status": "APPROVED", "scope": "TRAIN3763_EXACT_RELEASE"}) + "\n```"
        comments["/issues/comments/"+str(i)] = {"id": i, "user": {"login": auth.OWNER},
            "issue_url": auth.API+"/issues/179", "body": body}
        grant["approvals"][kind] = {"ref": "https://github.com/tantdna2/SafeShift/pull/179#issuecomment-"+str(i),
            "sha256": hashlib.sha256(body.encode()).hexdigest()}
    comments["/pulls/179"] = {"merged": True, "head": {"sha": grant["reviewed_head"]},
        "merge_commit_sha": grant["merged_sha"], "base": {"ref": "main"}}
    return request, grant, comments


def seal(request, grant, comments):
    body = auth.MARKER+"\n```json\n"+json.dumps(grant)+"\n```"
    locator = {"comment_id": 999, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
    request["execution_release"] = locator
    comments["/issues/comments/999"] = {"id": 999, "user": {"login": auth.OWNER},
        "issue_url": auth.API+"/issues/"+str(grant["implementation_pr"]), "body": body}
    return locator


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request, self.grant, self.comments = fixture()
        self.locator = seal(self.request, self.grant, self.comments)
        self.reader = lambda path: copy.deepcopy(self.comments[path])
        with patch("safeshift.internvl3763_witness.secrets.token_hex", return_value=self.grant["witness_id"]):
            self.store = Store(self.root/"claims.sqlite3", reader=self.reader)
        self.addCleanup(setattr, auth, "_active", None)

    def claim(self, kind, store=None, request=None, grant=None):
        request, grant = request or self.request, grant or self.grant
        payload = {"request": request, "release": request["execution_release"], "kind": kind}
        return (store or self.store).claim(grant["series"], grant["attempt"], kind, payload)

    def chain(self):
        return [self.claim(kind) for kind in ("submit", "launch", "worker", "load")]

    def test_authentic_exact_release_and_request_bind(self):
        self.assertEqual(auth.load(self.locator, reader=self.reader), self.grant)
        self.assertEqual(auth.bind(self.grant, self.request), self.request["bindings"]["runtime"]["execution_request"])

    def test_caller_flags_missing_release_and_old_pr_never_activate(self):
        for value in (None, True, {"approved": True}, {"comment_id": 1, "body_sha256": "x"}):
            with self.subTest(value=value), patch.object(auth, "get", side_effect=AssertionError("NO_REMOTE")), self.assertRaises(ValueError):
                auth.load(value)
        for pr in (177, 178):
            self.grant["implementation_pr"] = pr
            locator = seal(self.request, self.grant, self.comments)
            with self.assertRaisesRegex(ValueError, "REUSE"):
                auth.load(locator, reader=self.reader)

    def test_wrong_owner_body_unmerged_head_and_separate_approvals_block(self):
        cases = [lambda: self.comments["/issues/comments/999"]["user"].update(login="attacker"),
            lambda: self.comments["/issues/comments/999"].update(body="modified"),
            lambda: self.comments["/pulls/179"].update(merged=False),
            lambda: self.comments["/pulls/179"]["head"].update(sha="e"*40),
            lambda: self.comments["/issues/comments/1001"].update(body="fake audit PASS")]
        original = copy.deepcopy(self.comments)
        for change in cases:
            self.comments = copy.deepcopy(original)
            change()
            with self.subTest(change=change), self.assertRaises(ValueError):
                auth.load(self.locator, reader=self.reader)

    def test_expired_release_blocks_execution_but_allows_bound_readonly_collection(self):
        when = self.grant["expires_unix"]+1
        with self.assertRaisesRegex(ValueError, "EXPIRED"):
            auth.load(self.locator, reader=self.reader, now=when)
        self.assertEqual(auth.load(self.locator, reader=self.reader, now=when, for_collection=True), self.grant)

    def test_invalid_resource_caps_bool_revision_and_missing_approval_block(self):
        for key, value in (("physical_gpus", 1), ("seconds", True), ("calls", 3764),
                ("attempt_gpu_seconds", 1), ("archive_bytes", 8*2**30), ("loads", 2)):
            request, grant, comments = fixture()
            grant["caps"][key] = value
            locator = seal(request, grant, comments)
            with self.subTest(key=key), self.assertRaises(ValueError):
                auth.load(locator, reader=comments.__getitem__)
        self.grant["approvals"].pop("O6")
        locator = seal(self.request, self.grant, self.comments)
        with self.assertRaisesRegex(ValueError, "APPROVAL"):
            auth.load(locator, reader=self.reader)

    def test_execution_request_plan_source_and_limits_cannot_drift(self):
        for change in (lambda r: r["limits"].update(max_calls=4),
                lambda r: r.update(runtime_commit="a"*40),
                lambda r: r["bindings"]["runtime"]["execution_request"].update(input_marker_sha256="e"*64),
                lambda r: r["plan"]["scheduled_ordinals"].reverse()):
            value = copy.deepcopy(self.request)
            change(value)
            with self.subTest(change=change), self.assertRaises(ValueError):
                auth.bind(self.grant, value)

    def test_even_owner_hashed_divergent_outer_plan_and_bad_marker_block(self):
        # An exact release still cannot bind two different execution plans.
        value = copy.deepcopy(self.request)
        value["plan"] = copy.deepcopy(value["plan"])
        value["plan"]["run_id"] = "different-outer-run"
        value["plan_sha256"] = digest(value["plan"])
        grant = copy.deepcopy(self.grant)
        grant["request_sha256"] = auth.request_hash(value)
        with self.assertRaisesRegex(ValueError, "BINDING"):
            auth.bind(grant, value)
        execution = copy.deepcopy(self.request["bindings"]["runtime"]["execution_request"])
        execution["input_marker_sha256"] = "bad"
        with self.assertRaises(ValueError):
            runtime.validate_execution_request(execution)

    def test_collection_reconciles_remote_calls_and_blocks_missing_receipts(self):
        claims = self.chain()
        call = self.claim("call-000000")
        snapshot = self.store.observe(runtime.SERIES, 1, "snapshot")
        names = [("handoff.json", self.request), ("release.json", self.grant),
            ("launch-claim.json", claims[1]), ("environment/worker-claim.json", claims[2]),
            ("run/load-claim.json", claims[3]), ("run/samples/000000/call-claim.json", call),
            ("run/summary.json", {"records": [{"status": "TECHNICAL_ERROR"}]+[{"status": "NOT_ATTEMPTED"}]*3762})]
        archive = self.root/"custody.zip"
        def bundle(omit=None):
            with zipfile.ZipFile(archive, "w") as z:
                for name, value in names:
                    if name != omit:
                        z.writestr(name, json.dumps(value))
        with patch.object(auth, "load", return_value=self.grant), patch.object(auth, "http", return_value=snapshot):
            bundle()
            self.assertEqual(operator.verify_remote_custody(self.request, archive)["status"], "RECONCILED")
            bundle("run/samples/000000/call-claim.json")
            with self.assertRaisesRegex(ValueError, "UNKNOWN_CALL"):
                operator.verify_remote_custody(self.request, archive)

    def test_missing_input_unversioned_input_and_content_mismatch(self):
        for datasets in ([], ["owner/no-version"]):
            value = copy.deepcopy(self.request)
            value["bindings"]["dataset"]["dataset_sources"] = datasets
            with self.assertRaises(ValueError):
                operator.input_sources(value)
        self.request["bindings"]["dataset"]["execution_request_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError, "CONTENT_BINDING"):
            operator.input_sources(self.request)

    def test_sdk_mismatch_is_rejected_without_kaggle_import(self):
        with patch.dict(sys.modules, {"kaggle": None}), patch.object(operator.importlib.metadata, "version",
                side_effect=lambda name: "0.1.23" if name == "kagglesdk" else operator.SDK_PINS[name]), self.assertRaisesRegex(ValueError, "SDK_PINS"):
            operator.api()
        with patch.object(operator.importlib.metadata, "version", side_effect=operator.SDK_PINS.__getitem__):
            self.assertEqual(operator.check_sdk(), operator.SDK_PINS)

    def test_two_independent_clients_one_submit_claim_no_ttl_or_refund(self):
        second = Store(self.root/"claims.sqlite3", reader=self.reader)
        def attempt(store):
            try:
                return self.claim("submit", store)["created"]
            except (ValueError, sqlite3.IntegrityError):
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(attempt, (self.store, second))), [False, True])
        reopened = Store(self.root/"claims.sqlite3", reader=self.reader)
        self.assertTrue(reopened.observe(runtime.SERIES, 1, "submit")["found"])
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            self.claim("submit", reopened)

    def test_two_real_processes_cannot_launch_same_worker(self):
        self.claim("submit")
        payload = {"request": self.request, "release": self.locator, "kind": "launch"}
        write(self.root/"payload.json", payload)
        code = "from safeshift.internvl3763_witness import Store; from safeshift.pilot.artifacts import read; import sys; p=read(sys.argv[2]); Store(sys.argv[1]).claim(p['request']['plan']['series_id'],1,'launch',p)"
        args = [sys.executable, "-B", "-c", code, str(self.root/"claims.sqlite3"), str(self.root/"payload.json")]
        processes = [subprocess.Popen(args, cwd=runtime.ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for process in processes:
            process.communicate(timeout=30)
        self.assertEqual(sorted(p.returncode for p in processes), [0, 1])

    def test_permanent_worker_load_call_claims_require_parent_caps_and_order(self):
        with self.assertRaisesRegex(ValueError, "SUBMISSION"):
            self.claim("worker")
        self.chain()
        with self.assertRaisesRegex(ValueError, "ORDER"):
            self.claim("call-000001")
        self.claim("call-000000")
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            self.claim("call-000000")
        for i in (1, 2):
            self.claim(f"call-{i:06d}")
        with self.assertRaisesRegex(ValueError, "SCHEDULE"):
            self.claim("call-000003")
        with self.assertRaises(sqlite3.IntegrityError):
            self.claim("load")

    def test_sealed_release_avoids_github_reads_per_sample_and_survives_restart(self):
        self.chain()
        reopened = Store(self.root/"claims.sqlite3", reader=Mock(side_effect=AssertionError("NO_GITHUB_PER_IMAGE")))
        self.claim("call-000000", reopened)
        snapshot = reopened.observe(runtime.SERIES, 1, "snapshot")["claims"]
        self.assertEqual(set(snapshot), {"submit", "launch", "worker", "load", "call-000000"})

    def test_reset_or_other_database_cannot_reuse_release(self):
        other = Store(self.root/"other.sqlite3", reader=self.reader)
        self.assertNotEqual(other.identity, self.store.identity)
        with self.assertRaisesRegex(ValueError, "DATABASE"):
            self.claim("submit", other)
        fake = Mock(return_value={"witness_id": "0"*64, "claims": {}})
        with self.assertRaisesRegex(ValueError, "DATABASE_ID_DRIFT"):
            auth.Witness(self.grant, self.locator, transport=fake).observe("snapshot")

    def test_sealed_claim_expiry_survives_restart_and_cannot_be_reclaimed(self):
        self.chain()
        expired = Store(self.root/"claims.sqlite3", now=self.grant["expires_unix"]+1)
        with self.assertRaisesRegex(ValueError, "EXPIRED"):
            self.claim("call-000000", expired)

    def test_cumulative_gpu_budget_and_global_consumed_ordinal_survive_new_attempt(self):
        first = self.chain()[0]
        self.claim("call-000000")
        execution = self.request["bindings"]["runtime"]["execution_request"]
        original = execution["plan"]
        # A deliberately contradictory, structurally valid synthetic history:
        # server's consumed ordinal must still win over a claimed zero-call past.
        history = {"run_id": original["run_id"], "attempt_id": original["attempt_id"],
            "series_id": runtime.SERIES, "identity": original["identity"],
            "cohort_sha256": original["cohort_sha256"], "parent_history_sha256": digest([]),
            "action": "initial", "records": [], "evidence_sha256": "e"*64, "repair": None}
        execution["history"] = [history]
        execution["history_archives"] = [{"archive": "synthetic.zip", "sha256": "e"*64, "plan": original}]
        plan = runtime.plan(execution["cohort"], [history], action="resume", run_id="synthetic-second",
            attempt_id="synthetic-2", max_calls=3, max_seconds=1800)
        execution["plan"] = plan
        self.request.update(plan=plan, plan_sha256=digest(plan), job="nguynanhtn/safeshift-train3763-synthetic-second")
        self.request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        self.grant.update(attempt=2, predecessors=[digest(first)], request_sha256=auth.request_hash(self.request),
            execution_request_sha256=digest(execution), job=self.request["job"])
        self.grant["caps"]["campaign_gpu_seconds"] = 3600
        self.locator = seal(self.request, self.grant, self.comments)
        with self.assertRaisesRegex(ValueError, "BUDGET"):
            self.claim("submit")
        self.grant["caps"]["campaign_gpu_seconds"] = 7200
        self.locator = seal(self.request, self.grant, self.comments)
        second = self.claim("submit")
        self.assertEqual(second["cumulative_gpu_seconds"], 7200)
        for kind in ("launch", "worker", "load"):
            self.claim(kind)
        with self.assertRaises(sqlite3.IntegrityError):
            self.claim("call-000000")

    def test_witness_post_timeout_or_conflict_never_retries(self):
        transport = Mock(side_effect=TimeoutError("UNKNOWN_CLAIM"))
        with self.assertRaises(TimeoutError):
            auth.Witness(self.grant, self.locator, transport=transport).claim("submit", self.request)
        self.assertEqual(transport.call_count, 1)
        fake = Mock(return_value={"created": False})
        with self.assertRaisesRegex(ValueError, "NO_RETRY"):
            auth.Witness(self.grant, self.locator, transport=fake).claim("submit", self.request)
        self.assertEqual(fake.call_count, 1)

    def test_actual_http_claim_and_process_exit_persistent_reopen(self):
        server = HTTPServer(("127.0.0.1", 0), handler(self.store))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = "http://127.0.0.1:"+str(server.server_port)
            def transport(url, payload):
                return auth.http(url.replace(self.grant["witness"], base), payload)
            witness = auth.Witness(self.grant, self.locator, transport=transport)
            self.assertTrue(witness.claim("submit", self.request)["created"])
            with self.assertRaises(Exception):
                witness.claim("submit", self.request)
            self.assertIn("submit", witness.observe("snapshot")["claims"])
        finally:
            server.shutdown(); thread.join(timeout=5); server.server_close()

    def test_network_loss_before_authority_touches_no_sdk_or_witness(self):
        with patch.object(auth, "get", side_effect=ConnectionError("OFFLINE")), \
                patch.object(operator, "api", side_effect=AssertionError("NO_SDK")), self.assertRaises(ConnectionError):
            operator.admit(self.request)

    def test_interrupted_setup_or_model_call_keeps_full_denominator_and_no_repair(self):
        execution = self.request["bindings"]["runtime"]["execution_request"]
        out = self.root/"interrupted"
        out.mkdir()
        sample = out/"run/samples/000000"
        row = execution["cohort"]["samples"][0]
        write(sample/"started.json", {"row": row, "plan_sha256": digest(execution["plan"])})
        write(sample/"native_call.json", {"binding": "SYNTHETIC_INTERRUPTED"})
        write(sample/"raw.json", {"response": "do not rescue this retained raw"})
        value = runtime.interrupted_summary(out, execution, {"type": "TimeoutError"})
        self.assertEqual(value["counts"], {"TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(value["model_calls"], 1)
        self.assertIsNone(value["records"][0]["label"])
        self.assertEqual(read(sample/"raw.json")["response"], "do not rescue this retained raw")
        self.assertEqual(runtime.interrupted_summary(out, execution, {}), value)

    def test_package_is_release_free_and_never_submits(self):
        from scripts.prepare_train3763_package import package
        self.request["execution_release"] = None
        value = package(self.request, 999)
        self.assertIsNone(value["request"]["execution_release"])
        self.assertEqual(value["release_comment_id"], 999)

    def test_controller_time_and_archive_bounds_stop_before_another_call(self):
        cohort = synthetic_cohort()
        plan = runtime.plan(cohort, [], action="initial", run_id="synthetic-bounds", attempt_id="bounds-1",
            max_calls=3, max_seconds=10)
        backend = NS(environment={"scope": "SYNTHETIC"}, generate=Mock(side_effect=AssertionError("NO_NATIVE_CALL")))
        for case in ("time", "archive"):
            kwargs = {"clock": iter([0, 10]).__next__} if case == "time" else {"archive_limit_bytes": 1}
            result = runtime.rehearse(self.root/case, None, cohort, plan, [], lambda _: backend,
                image_path=Mock(side_effect=AssertionError("NO_IMAGE_READ")), tokenizer_sha="a"*64, **kwargs)
            self.assertEqual(result["counts"], {"NOT_ATTEMPTED": 3763})
            self.assertEqual(result["model_calls"], 0)
        backend.generate.assert_not_called()

    def test_same_processor_child_spec_path_exists_before_supervised_preflight(self):
        from scripts import internvl_v2 as old
        from safeshift import internvl_v2_memory as memory
        from safeshift.fulltrain import environment, preflight
        from safeshift.candidates import train_inputs, source
        from scripts import smoke_kaggle173 as smoke
        from contextlib import ExitStack
        out = self.root/"environment"
        out.mkdir()
        marker = self.root/"marker.json"
        write(marker, {"scope": "SYNTHETIC"})
        def processor(*args):
            self.assertEqual(read(out/"source.json"), runtime.capture.source_spec())
            write(out/"processor.json", {"scope": "SYNTHETIC_MOCK_ONLY"})
        with ExitStack() as stack:
            stack.enter_context(patch.object(runtime, "authorize"))
            for obj, name, value in ((memory, "resource_check", {}), (preflight, "storage_probe", {}),
                    (environment, "software", {}), (environment, "cuda", {}), (smoke, "driver_check", {}),
                    (smoke, "bind_cuda_driver", None), (source, "verify_snapshot", {}),
                    (memory, "verify_checkpoint", {}), (train_inputs, "checkpoint", (marker, self.root, self.root))):
                stack.enter_context(patch.object(obj, name, return_value=value))
            stack.enter_context(patch.object(old, "run_processor_check", side_effect=processor))
            stack.enter_context(patch.object(old, "reclaim_owned"))
            runtime.preflight(runtime.source_spec(), out, self.root, self.root, time.monotonic()+60)
        self.assertTrue((out/"processor.json").is_file())

    def test_interruption_preserves_already_durable_invalid_completion(self):
        execution = self.request["bindings"]["runtime"]["execution_request"]
        out = self.root/"durable"
        out.mkdir()
        row = execution["cohort"]["samples"][0]
        sample = out/"run/samples/000000"
        write(sample/"started.json", {"row": row, "plan_sha256": digest(execution["plan"])})
        write(sample/"native_call.json", {"binding": "SYNTHETIC"})
        checksum = write(sample/"raw.json", {"response": "invalid retained text"})
        durable = {**row, "status": "INVALID", "label": None, "attempts": 1, "native_calls": 1,
            "raw_sha256": checksum, "hnlo": None, "hnlo_status": runtime.HNLO_STATUS}
        write(sample/"result.json", durable)
        result = runtime.interrupted_summary(out, execution, {"type": "TimeoutError"})
        self.assertEqual(result["records"][0], durable)
        self.assertEqual(result["counts"], {"INVALID": 1, "NOT_ATTEMPTED": 3762})

    def test_supervised_launch_timeout_cannot_promote_existing_summary_to_pass(self):
        from scripts.internvl3763 import launch
        from safeshift.fulltrain import provision, supervision
        execution = self.request["bindings"]["runtime"]["execution_request"]
        package = self.root/"handoff.json"
        write(package, self.request)
        def supervised(command, **kwargs):
            receipt = kwargs["receipt"]
            if receipt.name == "setup-supervisor.json":
                write(receipt, {"status": "EXITED", "returncode": 0})
                write(receipt.parent/"runtime.json", {"python": sys.executable, "env": {}})
                return
            write(receipt, {"status": "TIMEOUT", "returncode": -1})
            write(receipt.parent/"run/summary.json", {"status": "PASS", "scope": "SYNTHETIC_SUPERVISOR_FIXTURE"})
            raise TimeoutError("SYNTHETIC_AFTER_SUMMARY_BEFORE_CHILD_EXIT")
        with patch.object(auth, "activate", return_value=self.grant), patch.object(auth, "bind", return_value=execution), \
                patch.object(auth, "activation_claim", return_value={"scope": "SYNTHETIC"}), \
                patch.object(runtime, "authorize"), patch.object(provision, "clean_env", return_value={}), \
                patch.object(supervision, "run", side_effect=supervised):
            result = launch(package, output=self.root/"output", scratch=self.root/"scratch", inputs=self.root/"input")
        self.assertEqual(result["status"], "FAIL")
        archive = next((self.root/"output").glob("*.zip"))
        with zipfile.ZipFile(archive) as z:
            terminal = json.loads(z.read("terminal.json"))
            self.assertEqual(terminal["status"], "FAIL")
            self.assertEqual(terminal["error"]["type"], "TimeoutError")

    def test_remote_parent_missing_or_corrupt_receipt_cannot_create_capability(self):
        response = {"created": True, "claim_sha256": "0"*64, "release_sha256": digest(self.grant)}
        with self.assertRaisesRegex(ValueError, "UNCONFIRMED"):
            auth.Witness(self.grant, self.locator, transport=lambda *_: response).claim("launch", self.request)
        with patch.object(auth, "get", side_effect=self.reader), \
                patch.object(auth.Witness, "claim", side_effect=TimeoutError("UNKNOWN_LAUNCH")), self.assertRaises(TimeoutError):
            auth.activate(self.request, "launch")
        self.assertIsNone(auth._active)

    def test_sdk_submit_one_site_preserves_timeout_privacy_input_pins_and_unknown(self):
        execution = self.request["bindings"]["runtime"]["execution_request"]
        notebook = self.root/"synthetic.ipynb"
        write(notebook, {"cells": [], "nbformat": 4})
        client = NS(kernels_push=Mock(side_effect=TimeoutError("UNKNOWN_SUBMIT")))
        stage = self.root/"handoff"
        stage.mkdir()
        receipt = {"created": True}
        with patch.object(operator, "admit", return_value=(self.grant, execution)), \
                patch.object(operator, "api", return_value=client), \
                patch.object(operator, "inventory", return_value={"scope": "SYNTHETIC"}), \
                patch.object(operator, "safe", return_value=notebook), \
                patch.object(auth.Witness, "claim", return_value=receipt), self.assertRaises(TimeoutError):
            operator.submit(self.request, self.grant, execution, stage)
        self.assertEqual(client.kernels_push.call_count, 1)
        self.assertEqual(client.kernels_push.call_args.kwargs, {"timeout": "1800", "acc": "NvidiaTeslaT4"})
        meta = read(stage/"submission/kernel-metadata.json")
        self.assertTrue(meta["is_private"])
        self.assertEqual(meta["dataset_sources"], ["nguynanhtn/synthetic-input/1"])
        self.assertEqual(read(stage/"submission/remote-submission-claim.json"), receipt)

    def test_raw_numeric_vector_readback_rejects_missing_or_modified_mask(self):
        import struct
        from safeshift.internvl_grammar import POLICY, PROCESSOR
        raw = {"generated_ids": [1], "input_ids": [3], "logit_width": 4,
            "raw_vector_hashes": [], "masked_vector_hashes": [],
            "actual_logits_processors": [PROCESSOR], "policy": dict(POLICY)}
        binary = struct.pack("<ffff", 5, 4, 3, 2)
        masked = {"step": 0, "prefix_ids": [3], "masked_logits": [None, 4, None, None],
            "raw_sha256": hashlib.sha256(binary).hexdigest()}
        forward = {"step": 0, "raw_sha256": masked["raw_sha256"], "vocab": 4,
            "origin": "forward_before_processors", "encoding": "float32-little-endian", "all_finite": True}
        members = {}
        archive = self.root/"numeric.zip"
        with zipfile.ZipFile(archive, "w") as z:
            for name, content in (("steps/000.f32", binary), ("steps/000.masked.json", json.dumps(masked).encode()),
                    ("steps/000.forward.json", json.dumps(forward).encode())):
                z.writestr(name, content); members[name] = hashlib.sha256(content).hexdigest()
        raw["raw_vector_hashes"] = [members["steps/000.f32"]]
        raw["masked_vector_hashes"] = [members["steps/000.masked.json"]]
        with zipfile.ZipFile(archive) as z:
            runtime.verify_numeric_members(z, "", raw, members)
            raw["generated_ids"] = [0]
            with self.assertRaisesRegex(ValueError, "GREEDY"):
                runtime.verify_numeric_members(z, "", raw, members)


@unittest.skipUnless(os.environ.get("SAFESHIFT3763_SDK_CPU") == "1", "opt-in isolated official SDK CPU serialization")
class InstalledSdkTests(unittest.TestCase):
    def test_actual_sdk_inventory_rejects_missing_input_quota_and_active_predecessor(self):
        from datetime import timedelta
        request, grant, _ = fixture()
        quota = NS(time_used=timedelta(0), time_reserved=timedelta(0), total_time_allowed=timedelta(seconds=7200))
        client = NS(kernels_list_with_response=lambda **_: NS(kernels=[], next_page_token=None),
            dataset_list_files=lambda *a, **k: NS(files=[NS(name="SYNTHETIC")]),
            quota_view=lambda: NS(gpu_quota=quota), kernels_status=lambda _: NS(status="RUNNING"))
        with patch("socket.socket", side_effect=AssertionError("NO_KAGGLE_NETWORK")):
            self.assertEqual(operator.inventory(client, request, grant)["quota"]["total"], 7200)
            client.dataset_list_files = lambda *a, **k: NS(files=[])
            with self.assertRaisesRegex(ValueError, "MISSING_DATASET"):
                operator.inventory(client, request, grant)
            client.dataset_list_files = lambda *a, **k: NS(files=[NS(name="SYNTHETIC")])
            quota.time_reserved = timedelta(seconds=1)
            with self.assertRaisesRegex(ValueError, "QUOTA"):
                operator.inventory(client, request, grant)
            quota.time_reserved = timedelta(0)
            quota.total_time_allowed = timedelta(seconds=1)
            with self.assertRaisesRegex(ValueError, "QUOTA"):
                operator.inventory(client, request, grant)
            previous = {"source_sha256": grant["source_sha256"], "job": "nguynanhtn/synthetic-previous", "version": 1}
            grant["predecessors"] = [digest(previous)]
            with patch.object(auth, "http", return_value={"witness_id": grant["witness_id"], "claims": {"submit": previous}}), \
                    self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_RUNNING"):
                operator.inventory(client, request, grant)

    def test_real_pinned_sdk_push_builds_exact_request_without_auth_or_network(self):
        import ast
        from contextlib import nullcontext
        import importlib.metadata
        from typing import Optional, List, cast
        from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest, ApiSaveKernelResponse
        operator.check_sdk()
        path = importlib.metadata.distribution("kaggle").locate_file("kaggle/api/kaggle_api_extended.py")
        tree = ast.parse(Path(path).read_text(encoding="utf8"))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "KaggleApi")
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "kernels_push")
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        namespace = {"os": os, "json": json, "Optional": Optional, "List": List, "cast": cast,
            "ApiSaveKernelRequest": ApiSaveKernelRequest, "ApiSaveKernelResponse": ApiSaveKernelResponse,
            "slugify": lambda x: x, "_warn_if_retired_accelerator": lambda _: None}
        exec(compile(module, str(path), "exec"), namespace)
        received = []
        def save(request):
            received.append(request)
            return ApiSaveKernelResponse()
        fake = NS(KERNEL_METADATA_FILE="kernel-metadata.json", valid_push_language_types=["python"],
            valid_push_kernel_types=["notebook"], valid_push_pinning_types=[],
            get_or_default=lambda data, key, default: data.get(key, default),
            get_bool=lambda data, key, default: data.get(key, default),
            parse_kernel_string=lambda value: (*value.split("/"), None),
            validate_dataset_string=lambda _: None, validate_kernel_string=lambda _: None,
            build_kaggle_client=lambda: nullcontext(NS(kernels=NS(kernels_api_client=NS(save_kernel=save)))))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root/"kernel-metadata.json", {"id": "nguynanhtn/synthetic-sdk", "title": "synthetic-sdk",
                "code_file": "synthetic.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
                "dataset_sources": ["owner/synthetic/2"], "kernel_sources": ["owner/synthetic-kernel/1"]})
            write(root/"synthetic.ipynb", {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC')"], "outputs": []}]})
            with patch("socket.socket", side_effect=AssertionError("NO_KAGGLE_NETWORK")), patch.dict(sys.modules, {"kaggle": None}):
                namespace["kernels_push"](fake, str(root), timeout="1800", acc="NvidiaTeslaT4")
        self.assertEqual(len(received), 1)
        request = received[0]
        self.assertEqual(request.session_timeout_seconds, 1800)
        self.assertEqual(request.machine_shape, "NvidiaTeslaT4")
        self.assertTrue(request.is_private)
        self.assertEqual(request.dataset_data_sources, ["owner/synthetic/2"])
        self.assertEqual(request.kernel_data_sources, ["owner/synthetic-kernel/1"])
        self.assertEqual(json.loads(request.text)["cells"][0]["source"], "print('SYNTHETIC')")


if __name__ == "__main__":
    unittest.main()
