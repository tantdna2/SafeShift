"""Synthetic recovery/signatures/provider doubles; no account/model/image IO."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, MagicMock, patch

import test_minicpm_fulltrain_execution as fixtures
from safeshift.fulltrain import minicpm_release as a, minicpm_recovery as r, minicpm_ui as ui
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.artifacts import export
from safeshift.pilot.contract import digest
from scripts import minicpm_fulltrain_operator as old, minicpm_fulltrain_recovery as op


@unittest.skipUnless(sys.platform == "linux", "Linux guardian/process groups required")
class LiveSupervisionTests(unittest.TestCase):
    def test_native_event_forwarded_before_child_finishes_with_full_log_retained(self):
        from safeshift.fulltrain.supervision import run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seen, captured = [], []
            class Sink:
                def write(self, text):
                    captured.append(text)
                    if text.startswith(r.EVENT_PREFIX): seen.append(not (root / "finished").exists())
                def flush(self): pass
            code = ("import pathlib,time; print('private diagnostic',flush=True); "
                "print('SAFESHIFT_MINICPM_LIVE_V3 {\\\"kind\\\":\\\"synthetic\\\"}',flush=True); "
                "time.sleep(2); pathlib.Path('finished').write_text('done')")
            with patch("sys.stdout", new=Sink()):
                run([sys.executable, "-B", "-c", code], cwd=root, env=dict(os.environ),
                    deadline=time.monotonic() + 10, log=root / "native.log", receipt=root / "process.json",
                    max_log_bytes=10000, live_prefix=r.EVENT_PREFIX)
            self.assertEqual(seen, [True])
            self.assertNotIn("private diagnostic", "".join(captured))
            self.assertIn("private diagnostic", (root / "native.log").read_text())
            self.assertTrue((root / "finished").exists())


class RecoveryTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.ExecutionTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.ExecutionTests.tearDownClass.__func__)
    make_ticket = fixtures.ExecutionTests.make_ticket
    fake_graph = fixtures.ExecutionTests.fake_graph

    def setUp(self):
        fixtures.ExecutionTests.setUp(self)
        p = patch.object(op, "ROOT", self.root)
        p.start(); self.addCleanup(p.stop)
        p = patch.object(op, "private_root", side_effect=lambda path: Path(path))
        p.start(); self.addCleanup(p.stop)
        self.old_grants = []
        for campaign, (root_name, mirror_name) in zip(r.CAMPAIGNS, op.KNOWN):
            grant = deepcopy(self.grant)
            grant["campaign_id"] = campaign
            grant["merged_sha"] = "507e9817b91054fa7af324c6a915c35d56b5acf1"
            grant["scope"]["source_sha256"] = "7c76a2c331aef2383e9d8f2fe236f0c4302cabb587a759925b5d3dadae206b5c"
            grant["scope"]["identity"]["implementation_sha256"] = grant["scope"]["source_sha256"]
            value = deepcopy(self.value)
            value["job"] = "nguynanhtn/safeshift-minicpm-" + campaign + "-1"
            value["capsule_ref"] = "nguynanhtn/safeshift-minicpm-capsule-" + campaign + "-1/1"
            value["input_sources"]["dataset_sources"][-1] = value["capsule_ref"]
            journal = old.Journal(self.root / "data/processed" / root_name, self.root / "data/processed" / mirror_name)
            journal.root.mkdir(parents=True); journal.mirror.mkdir(parents=True)
            body = a.MARKER + "\n```json\n" + json.dumps(grant) + "\n```"
            loc = {"comment_id": len(self.old_grants) + 20, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
            self.old_grants.append((grant, body))
            journal._pair({"schema": old.SCHEMA, "number": 1, "previous": "0" * 64, "kind": "REGISTERED",
                "payload": {"host": old.host(), "locator": loc, "grant_sha256": digest(grant), "initial": value}})
            write(journal.guard_path(grant), journal.binding(grant))
            ticket = deepcopy(self.ticket["payload"])
            ticket.update(grant_sha256=digest(grant), value_sha256=digest(value), previous_event_sha256=digest(journal.events()[-1]))
            signed = old.sign(self.key, self.public, ticket)
            journal.append("RESERVED", {"ticket": signed, "value": value, "package": "data/processed/old"})
        snapshot = op.inspect_journals()
        self.value = ui.initial(self.cohort, digest(self.cohort), self.value["request"]["resource_policy"],
            checkpoint_marker_sha256="b" * 64, run_id="recovery-run", attempt_id="recovery-attempt",
            job="nguynanhtn/safeshift-minicpm-mcpm4-train3763-v3-4",
            capsule_ref="nguynanhtn/safeshift-minicpm-capsule-mcpm4-train3763-v3-4/1",
            max_calls=3, max_seconds=600, nested_mounts=True)
        self.grant.update(schema=a.RECOVERY_SCHEMA, authorization="OWNER_MINICPM_TRAIN3763_CODEX_SUBMIT_ONCE",
            campaign_id=r.CAMPAIGNS[-1], implementation_pr=199, scope=a.scope(self.value), recovery=snapshot)
        self.grant["caps"]["total_gpu_seconds"] = 72000
        for row in snapshot["journals"]:
            row.update(disposition="EXPIRED_UNPUBLISHED", evidence_sha256="9" * 64)
            snapshot["prior_jobs"].append({"job": row["job"], "version": 1, "state": "ABSENT_EXPIRED", "evidence_sha256": "9" * 64})
        directive_body = "Owner authorizes exact one postmerge submission"
        snapshot["directive"]["body_sha256"] = hashlib.sha256(directive_body.encode()).hexdigest()
        self.directive_body = directive_body
        self.provider["prior_jobs"] = deepcopy(snapshot["prior_jobs"])
        self.provider["observed_unix"] = int(time.time())
        self.ticket = self.recovery_ticket()
        self.logs = self.events_log()

    def recovery_ticket(self):
        ticket = deepcopy(self.ticket["payload"])
        before = self.grant["recovery"]["reserved"]
        ticket.update(schema=a.RECOVERY_TICKET, grant_sha256=digest(self.grant), value_sha256=digest(self.value),
            capsule_sha256=digest(self.value), number=4, reserved_before=before,
            reserved_after={"calls": before["calls"] + 3, "jobs": 4, "gpu_seconds": before["gpu_seconds"] + 1200},
            issued_unix=int(time.time()), provider=deepcopy(self.provider),
            start_before_unix=self.provider["observed_unix"] + self.grant["provider_max_age_seconds"])
        return old.sign(self.key, self.public, ticket)

    def events_log(self):
        now = time.time()
        base = {"ticket_sha256": digest(self.ticket), "request_sha256": digest(self.value["request"]),
            "source_sha256": self.value["request"]["source_sha256"], "time_unix": now}
        rows = [{**base, "kind": "stage_returned", "stage": stage} for stage in ("admit", "setup", "cpu", "gpu")]
        sample = self.value["cohort"]["samples"][0]
        rows.append({**base, "kind": "native_generate_started", "model_loaded": True, "ordinal": 0,
            "sample_id": sample["sample_id"], "image_sha256": sample["image_sha256"],
            "claim": {"kind": "call-000000", "ticket_sha256": digest(self.ticket),
                "request_sha256": digest(self.value["request"]), "number": 4, "time_unix": now}})
        return rows

    def encoded(self, rows=None):
        return "\n".join(r.EVENT_PREFIX + json.dumps(row) for row in (self.logs if rows is None else rows)) + "\n"

    def graph(self):
        locator, graph = self.fake_graph()
        graph["/pulls/199"] = graph.pop("/pulls/198")
        for row in graph.values():
            if "issue_url" in row:
                row["issue_url"] = a.API + "/issues/199"
        for i, (_, body) in enumerate(self.old_grants, 20):
            graph["/issues/comments/" + str(i)] = {"id": i, "user": {"id": a.OWNER_ID, "login": a.OWNER},
                "issue_url": a.API + "/issues/198", "body": body}
        graph["/issues/comments/6914854993"] = {"id": 6914854993, "user": {"id": a.OWNER_ID, "login": a.OWNER},
            "issue_url": a.API + "/issues/198", "body": self.directive_body}
        root = graph["/issues/comments/1"]
        root["body"] = root["body"].replace(a.MARKER, a.RECOVERY_MARKER)
        locator["body_sha256"] = hashlib.sha256(root["body"].encode()).hexdigest()
        return locator, graph

    def test_v3_live_graph_requires_new_merged_pr_approvals_and_original_grants(self):
        loc, graph = self.graph()
        self.assertEqual(a.load(loc, reader=graph.__getitem__), self.grant)
        for mutate in (lambda g:g["/pulls/199"].update(merged=False),
                       lambda g:g["/issues/comments/20"]["user"].update(id=1),
                       lambda g:g["/issues/comments/6914854993"].update(body="edited")):
            bad = deepcopy(graph); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                a.load(loc, reader=bad.__getitem__)

    def test_signed_replacement_keeps_every_reservation_and_number(self):
        a.validate(self.grant)
        a.verify_ticket(self.grant, self.ticket, self.value)
        for mutate in (lambda t:t.update(number=1), lambda t:t["reserved_before"].update(gpu_seconds=0),
                       lambda t:t["provider"].update(prior_jobs=[])):
            bad = deepcopy(self.ticket["payload"]); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                a.verify_ticket(self.grant, old.sign(self.key, self.public, bad), self.value)

    def test_actual_86400_reservations_cannot_fit_old_72000_cap(self):
        grant = deepcopy(self.grant)
        for row in grant["recovery"]["journals"]:
            t = deepcopy(row["ticket"]["payload"])
            t["sizing"] = {"calls": 1000, "seconds": 14400}
            t["reserved_after"] = {"calls": 1000, "jobs": 1, "gpu_seconds": 28800}
            row["ticket"] = old.sign(self.key, self.public, t)
        grant["recovery"]["reserved"] = {"calls": 3000, "jobs": 3, "gpu_seconds": 86400}
        with self.assertRaisesRegex(ValueError, "PROJECT_BUDGET_EXHAUSTED_NO_REFUND"):
            a.validate(grant)
        grant["caps"]["total_gpu_seconds"] = 200000
        with self.assertRaisesRegex(ValueError, "CAP_AMENDMENT_REQUIRED"):
            a.validate(grant)

    def test_unknown_native_duplicate_fourth_campaign_and_torn_mirror_stop(self):
        for mutate in (lambda g:g["recovery"]["journals"][0].update(disposition="UNKNOWN"),
                       lambda g:g.update(campaign_id="mcpm4-train3763-v4"),
                       lambda g:g["recovery"]["journals"].pop(),
                       lambda g:g["recovery"]["reserved"].update(calls=0),
                       lambda g:g["recovery"]["journals"][0].update(publication="PUBLISHED"),
                       lambda g:g["recovery"]["journals"][0]["ticket"].update(signature="0" * 768)):
            grant = deepcopy(self.grant); mutate(grant)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): a.validate(grant)
        mirror = self.root / "data/processed/minicpm-v2-mirror/event-00002.json"
        mirror.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "MIRROR_BYTES"): op.inspect_journals()

    def test_five_nested_paths_and_direct_layout_denied(self):
        table = r.mounted_inputs(self.value)
        self.assertEqual(len(table), 5)
        self.assertEqual(table[ui.CHECKPOINT]["mount"], "notebooks/nguynanhtn/safeshift-prepare-minicpm4")
        self.assertTrue(all(v["mount"].startswith("datasets/nguynanhtn/") for k, v in table.items() if k != ui.CHECKPOINT))
        direct = deepcopy(self.value)
        for name in ("master_dataset", "train_dataset"):
            row = direct["request"]["original_inputs"][name]
            row["mount"] = row["ref"].split("/")[1]
        direct["request"]["marker_sha256"] = digest(direct["request"]["original_inputs"])
        with self.assertRaisesRegex(ValueError, "NESTED_BINDING"): r.mounted_inputs(direct)

    def test_pre_native_failure_requires_positive_complete_terminal_evidence(self):
        provider = {"state": "ERROR", "job_id": self.value["job"], "version": 1,
            "notebook_code_sha256": self.ticket["payload"]["notebook_code_sha256"]}
        receipt = r.failure_receipt(self.value, self.ticket, provider,
            "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH", inventory_complete=True)
        self.assertEqual(receipt["status"], "FAILED_PRE_NATIVE")
        self.assertFalse(receipt["refund"])
        self.assertEqual(receipt["reservation_preserved"], self.ticket["payload"]["reserved_after"])
        for kwargs in ({"log": "no output"}, {"log": "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH", "inventory_complete": False}):
            with self.assertRaises(ValueError):
                r.failure_receipt(self.value, self.ticket, provider, **kwargs)
        release = {"failure": {"message": "UNIQUE_ORIGINAL_MOUNT_REQUIRED"}, "attempt_observed": False,
            "recovery": "NO_ATTEMPT", "last_stage": "admit", "source_sha256": self.value["request"]["source_sha256"]}
        claim = {"kind": "launch", "ticket_sha256": digest(self.ticket), "request_sha256": digest(self.value["request"])}
        claims = {"launch.json": claim}
        r.failure_receipt(self.value, self.ticket, provider, "", release=release, claims=claims, inventory_complete=True)
        for mutate in (lambda c:c.update({"native.json": claim}), lambda c:c.update({"call-000000.json": claim}), lambda c:c.clear()):
            bad = deepcopy(claims); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                r.failure_receipt(self.value, self.ticket, provider, "", release=release, claims=bad, inventory_complete=True)

    def test_running_stage_entries_and_model_load_alone_never_pass(self):
        self.assertEqual(r.live_proof("RUNNING", self.value, self.ticket)["status"], "RUNNING_UNVERIFIED")
        self.assertEqual(r.live_proof(self.encoded(self.logs[:-1]), self.value, self.ticket)["status"], "RUNNING_UNVERIFIED")
        self.assertEqual(r.live_proof(self.encoded(), self.value, self.ticket)["status"], "NATIVE_STARTED")
        for mutate in (lambda rows:rows.pop(0), lambda rows:rows[-1].update(ordinal=1),
                       lambda rows:rows[-1].update(model_loaded=False),
                       lambda rows:rows[-1]["claim"].update(ticket_sha256="0" * 64),
                       lambda rows:rows[-1].update(source_sha256="0" * 64),
                       lambda rows:rows[-1].update(image_sha256="0" * 64)):
            rows = deepcopy(self.logs); mutate(rows)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                r.live_proof(self.encoded(rows), self.value, self.ticket)

    def test_provider_json_stdout_chunks_reassembled_stderr_never_proves_calls(self):
        text = self.encoded()
        chunks = [{"stream_name": "stdout", "data": text[:100]}, {"stream_name": "stdout", "data": text[100:]}]
        self.assertEqual(r.live_proof(json.dumps(chunks), self.value, self.ticket)["status"], "NATIVE_STARTED")
        chunks = [{"stream_name": "stderr", "data": text}]
        self.assertEqual(r.live_proof(json.dumps(chunks), self.value, self.ticket)["status"], "RUNNING_UNVERIFIED")

    def test_native_observation_is_at_model_generate_after_processing(self):
        with patch.object(a, "CLAIMS", self.root / "claims"):
            with a._activated(self.grant, self.locator, self.ticket, self.value, "launch"):
                pass
            for stage in a.STAGES[1:-1]:
                with a._activated(self.grant, self.locator, self.ticket, self.value, stage, child=True): pass
            with a._activated(self.grant, self.locator, self.ticket, self.value, "native", child=True) as c:
                a.authorize("load")
                order = []
                model = NS(generate=lambda: order.append("real-generate"))
                backend = NS(model=model, generate=lambda *_: (order.append("image-prepared"), model.generate()))
                with patch.object(r, "native_started", side_effect=lambda *_: order.append("observed-native")):
                    a.GuardedBackend(backend, 0).generate("synthetic", "synthetic")
                self.assertEqual(order, ["image-prepared", "observed-native", "real-generate"])
                self.assertFalse((c["claims"] / "generate-000000.json").exists())
                # The real receipt writer also rejects an unclaimed ordinal.
                sample = self.value["cohort"]["samples"][0]
                with patch("sys.stdout", new=io.StringIO()):
                    receipt = r.native_started(0, sample["sample_id"], sample["image_sha256"])
                self.assertTrue(receipt["model_loaded"])
                with self.assertRaises(FileExistsError):
                    with patch("sys.stdout", new=io.StringIO()):
                        r.native_started(0, sample["sample_id"], sample["image_sha256"])

    def test_expired_ticket_cannot_publish_or_submit(self):
        item = {"ticket": self.ticket, "value": self.value}
        with patch.object(a.time, "time", return_value=self.ticket["payload"]["start_before_unix"]):
            with self.assertRaisesRegex(ValueError, "EXPIRED_NO_TICKET_REUSE"): op.check_window(self.grant, item)

    def staged_operator(self):
        operator = op.RecoveryOperator()
        nb = {"cells": [{"cell_type": "code", "source": ["pass\n"]}], "metadata": {"safeshift": {}}}
        nb["metadata"]["safeshift"] = {"runtime_ref": self.grant["runtime_commit"],
            "source_sha256": self.value["request"]["source_sha256"], "capsule_sha256": digest(self.value)}
        reconciliation = self.root / "data/processed/reconcile"
        write(reconciliation / "snapshot.json", self.grant["recovery"])
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(op, "live_provider", return_value=self.provider), \
             patch("scripts.generate_minicpm_fulltrain_notebook.notebook", return_value=nb), \
             patch("safeshift.internvl3763_operator.api", return_value=Mock()):
            operator.stage(self.locator, self.value, self.key, self.root / "data/processed/package", reconciliation)
        return operator

    def test_real_journal_stage_and_duplicate_stage_keep_all_old_bytes(self):
        before = {p: p.read_bytes() for p in (self.root / "data/processed").rglob("event-*.json")}
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant):
            grant, item, order = operator.state()
        self.assertEqual(order, ["RECOVERY_RESERVED"])
        self.assertEqual(item["ticket"]["payload"]["reserved_before"], grant["recovery"]["reserved"])
        for p, raw in before.items(): self.assertEqual(p.read_bytes(), raw)
        with self.assertRaisesRegex(ValueError, "ALREADY_STAGED"):
            operator.stage(self.locator, self.value, self.key, self.root / "new", self.root / "reconcile")

    def test_ambiguous_submit_is_exactly_one_post_and_never_automatic_retry(self):
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant):
            _, item, _ = operator.state()
        ticket = digest(item["ticket"])
        operator.journal.append("RECOVERY_PUBLISH_INTENT", {"ticket_sha256": ticket})
        operator.journal.append("RECOVERY_PUBLISHED", {"ticket_sha256": ticket, "proof": {}})
        client = Mock()
        client.kernels_push.side_effect = TimeoutError("ambiguous POST")
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(op, "verify_package"), patch.object(old, "verify_published_capsule"), \
             patch.object(op, "live_provider", return_value=self.provider), \
             patch("safeshift.internvl3763_operator.api", return_value=client):
            with self.assertRaises(TimeoutError): operator.submit_once()
            with self.assertRaisesRegex(ValueError, "SUBMIT_ONCE_UNKNOWN_NO_RETRY"): operator.submit_once()
        self.assertEqual(client.kernels_push.call_count, 1)
        self.assertEqual(operator.journal.events()[-1]["kind"], "CODEX_PUSH_INTENT")

    def test_provider_inventory_pagination_duplicate_or_wrong_account_denied(self):
        client = Mock()
        client.kernels_list_with_response.return_value = NS(kernels=[NS(ref="nguynanhtn/synthetic")], next_page_token=None)
        self.assertEqual(op.account_jobs(client), {"nguynanhtn/synthetic"})
        for refs in (["nguynanhtn/synthetic", "nguynanhtn/synthetic"], ["another/synthetic"]):
            client.kernels_list_with_response.return_value = NS(kernels=[NS(ref=ref) for ref in refs], next_page_token=None)
            with self.assertRaises(ValueError): op.account_jobs(client)

    @unittest.skipUnless(importlib.util.find_spec("kagglesdk"), "Existing pinned SDK required; Windows operator suite covers this boundary")
    def test_single_launch_then_positive_running_handoff_preserves_live_kernel(self):
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant):
            _, item, _ = operator.state()
        self.ticket = item["ticket"]
        self.logs = self.events_log()
        client = MagicMock()
        client.dataset_create_new.return_value = NS(status="ok", error="")
        response = {"ref": self.value["job"], "versionNumber": 1, "kernelId": 1234}
        client.kernels_push.return_value = NS(to_dict=lambda: response)
        client.kernels_status.return_value = NS(status="RUNNING")
        client.quota_view.return_value = NS(gpu_quota=NS(time_used=timedelta(seconds=10),
            time_reserved=timedelta(seconds=1200), total_time_allowed=timedelta(seconds=10000)))
        meta = NS(ref=self.value["job"], is_private=True, current_version_number=1, id=1234,
            machine_shape="NvidiaTeslaT4", dataset_data_sources=[v.rsplit("/", 1)[0] for v in self.value["input_sources"]["dataset_sources"]],
            kernel_data_sources=[ui.CHECKPOINT.rsplit("/", 1)[0]])
        nb = read(self.root / item["package"] / "notebook.ipynb")
        client.build_kaggle_client.return_value.__enter__.return_value.kernels.kernels_api_client.get_kernel.return_value = NS(
            metadata=meta, blob=NS(source=json.dumps(nb)))
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(op, "verify_package"), patch.object(old, "verify_published_capsule", return_value={"private": True}), \
             patch.object(op, "live_provider", return_value=self.provider), \
             patch("safeshift.internvl3763_operator.api", return_value=client), \
             patch("scripts.reconcile_train3763_manual.output_inventory", return_value=({}, self.encoded())):
            operator.publish()
            result = operator.submit_once()
            self.assertEqual(result["status"], "SUBMITTED_UNVERIFIED")
            with self.assertRaisesRegex(ValueError, "SUBMIT_ONCE_UNKNOWN_NO_RETRY"): operator.submit_once()
            result = operator.observe(self.root / "data/processed/handoff")
            self.assertEqual(result["status"], "PASS_NATIVE_STARTED_JOB_RUNNING")
            self.assertEqual(result["kernel_action"], "LEAVE_RUNNING_DO_NOT_CANCEL")
            self.assertEqual(result["journal_head_after"], digest(operator.journal.events()[-1]))
            with self.assertRaisesRegex(ValueError, "OBSERVE_EXACT_LAUNCH_ONCE"):
                operator.observe(self.root / "data/processed/second")
        self.assertEqual(client.kernels_push.call_count, 1)
        client.kernels_stop.assert_not_called()
        client.kernels_cancel.assert_not_called()

    def test_antigravity_same_journal_collects_real_synthetic_zips_and_stages_pending_only(self):
        from safeshift.fulltrain import runtime as rt, contract
        from safeshift.candidates import fulltrain_run as journal
        from safeshift.fulltrain.minicpm_execution import retain_sealed_trees
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant): _, item, _ = operator.state()
        value, ticket = item["value"], item["ticket"]
        checksum = digest(ticket)
        operator.journal.append("RECOVERY_PUBLISH_INTENT", {"ticket_sha256": checksum})
        operator.journal.append("RECOVERY_PUBLISHED", {"ticket_sha256": checksum, "proof": {}})
        serial = op.RecoveredSerialJournal()
        bundle, work, scratch = self.root / "images", self.root / "work", self.root / "scratch"
        bundle.mkdir(); scratch.mkdir()
        for i in range(3): (bundle / f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        class Backend(fixtures.Scripted):
            def __init__(self):
                super().__init__(['{"safety_level":"Level04"}', 'INVALID', '{"safety_level":"Level01"}'])
                self.model = NS(generate=lambda: None)
            def generate(self, *args):
                self.model.generate()
                return super().generate(*args)
        backend = Backend()
        def factory(): a.authorize("load"); return backend
        def observed(client, job, version, nb, sources, **kwargs):
            from safeshift.internvl3763_operator import code_hash
            return {"state": "COMPLETE", "job_id": job, "version": 1, "kernel_id": 1, "notebook_code_sha256": code_hash(nb)}
        with ExitStack() as stack:
            stack.enter_context(patch.object(a, "load", return_value=self.grant))
            stack.enter_context(patch.object(a, "CLAIMS", self.root / "claims"))
            stack.enter_context(patch.object(rt, "validate_native_raw"))
            stack.enter_context(patch.object(old, "private_root", side_effect=lambda path: Path(path)))
            stack.enter_context(patch.object(old, "clean_source"))
            remote = Mock(); remote.kernels_status.return_value = NS(status="COMPLETE")
            stack.enter_context(patch("safeshift.internvl3763_operator.api", return_value=remote))
            stack.enter_context(patch("scripts.reconcile_train3763_manual.observe_kernel", side_effect=observed))
            stack.enter_context(patch("scripts.reconcile_train3763_manual.download_outputs", return_value={}))
            with patch("sys.stdout", new=io.StringIO()):
                with a._activated(self.grant, self.locator, ticket, value, "launch"): pass
                for phase in a.STAGES[1:-1]:
                    with a._activated(self.grant, self.locator, ticket, value, phase, child=True): pass
                with a._activated(self.grant, self.locator, ticket, value, "native", child=True):
                    result = rt._execute(work, bundle, self.cohort, value["request"]["campaign"], value["request"]["plan"],
                        [], factory, image_path=lambda i: f"{i:06d}.bin", store_class=journal.BoundStore)
                    claims = a.claims_snapshot()
            control = self.root / ("f" * 32); control.mkdir()
            write(control / "request.json", value["request"])
            write(control / "capability.json", {"locator": self.locator, "ticket": ticket})
            write(control / "claims.json", claims)
            write(control / "release.json", {"status": "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY",
                "source_sha256": value["request"]["source_sha256"], "diagnostic": False, "attempt_observed": True,
                "scientific_qualified": False, "failure": None, "last_stage": "native"})
            for mode in a.STAGES[1:]:
                write(control / (mode + "-process.json"), {"status": "EXITED", "returncode": 0})
                write(control / mode / "stage.json", {"status": "RETURNED", "stage": mode,
                    "request_sha256": digest(value["request"]), "source_sha256": value["request"]["source_sha256"],
                    "native_attempt_permitted": mode == "native"})
            owned = {**value["request"], "work": str(work), "scratch": str(scratch)}
            write(control / "retention.json", retain_sealed_trees(owned, work, scratch, self.root / item["package"] / "dataset"))
            write(control / "final_timing.json", {"seconds_before_supervisor_export": time.time() - claims["launch.json"]["time_unix"],
                "export_reserve_seconds": self.grant["sizing"]["export_seconds"], "billing": "NOT_OBSERVED"})
            export(control, Path(str(control) + ".zip"))
            def fetch(client, v, directory, limit):
                attempt = directory / "minicpm-fulltrain" / (v["request"]["plan"]["run_id"] + ".zip")
                supervisor = directory / "minicpm-fulltrain/supervision" / ("f" * 32 + ".zip")
                for source, target in ((Path(str(result) + ".zip"), attempt), (Path(str(control) + ".zip"), supervisor)):
                    old._copy(source, target); old._copy(Path(str(source) + ".sha256.json"), Path(str(target) + ".sha256.json"))
                return attempt, supervisor
            stack.enter_context(patch("scripts.minicpm_fulltrain_transport.fetch_outputs", side_effect=fetch))
            collected = serial.collect(self.root / "data/processed/collection")
            self.assertEqual(collected["counts"], {"SUCCESS": 2, "INVALID": 1, "NOT_ATTEMPTED": 3760})
            def provider(client, grant, v, reconciliation, *, recovered=()):
                proof = deepcopy(self.provider)
                proof["prior_jobs"] += [{"job": c["value"]["job"], "version": 1, "state": "COMPLETE", "kernel_id": 1,
                    "ticket": c["ticket"]} for c in recovered]
                return proof
            def build(ref, *, capsule_sha256, **kwargs):
                return {"cells": [{"cell_type": "code", "source": ["pass\n"]}], "metadata": {"safeshift": {
                    "runtime_ref": ref, "source_sha256": self.value["request"]["source_sha256"], "capsule_sha256": capsule_sha256}}}
            stack.enter_context(patch.object(op, "live_provider", side_effect=provider))
            stack.enter_context(patch.object(old, "notebook", side_effect=build))
            serial.stage(self.key, self.root / "data/processed/pending")
            _, _, reserved, active, completed = serial.state()
            self.assertEqual(active["value"]["request"]["plan"]["scheduled_ordinals"][0], 3)
            self.assertEqual(active["ticket"]["payload"]["number"], 5)
            self.assertEqual(active["ticket"]["payload"]["reserved_before"], ticket["payload"]["reserved_after"])
            self.assertEqual(len(completed), 1)
            self.assertGreater(reserved["gpu_seconds"], ticket["payload"]["reserved_after"]["gpu_seconds"])
        self.assertEqual(backend.calls, 3)


if __name__ == "__main__":
    unittest.main()
