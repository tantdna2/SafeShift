"""Synthetic Owner-UI restart/retirement/source/signature tests; zero live IO."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

import test_minicpm_fulltrain_execution as fixtures
from safeshift.fulltrain import contract, minicpm_release as a, minicpm_recovery as r, minicpm_ui as ui
from safeshift.pilot.artifacts import read, write, sha, export
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

    def setUp(self):
        fixtures.ExecutionTests.setUp(self)
        for module, attr, value in ((op, "ROOT", self.root), (op, "private_root", lambda p: Path(p)),
                                    (old, "private_root", lambda p: Path(p))):
            patcher = patch.object(module, attr, value); patcher.start(); self.addCleanup(patcher.stop)
        self.old_grants = []
        for campaign, pair in zip(r.CAMPAIGNS, op.KNOWN):
            g, value = deepcopy(self.grant), deepcopy(self.value)
            g.update(campaign_id=campaign, merged_sha="507e9817b91054fa7af324c6a915c35d56b5acf1")
            g["scope"]["source_sha256"] = "7c76a2c331aef2383e9d8f2fe236f0c4302cabb587a759925b5d3dadae206b5c"
            g["scope"]["identity"]["implementation_sha256"] = g["scope"]["source_sha256"]
            value["job"] = "nguynanhtn/safeshift-minicpm-" + campaign + "-1"
            value["request"]["plan"] = contract.plan(value["request"]["campaign"], self.cohort,
                value["request"]["plan"]["identity"], [], action="initial", run_id=campaign + "-r", attempt_id=campaign + "-a",
                max_calls=1000, max_seconds=r.JOB_SECONDS)
            body = a.MARKER + "\n```json\n" + json.dumps(g) + "\n```"
            loc = {"comment_id": 20 + len(self.old_grants), "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
            self.old_grants.append(g)
            journal = old.Journal(*(self.root / "data/processed" / name for name in pair))
            journal.root.mkdir(parents=True); journal.mirror.mkdir(parents=True)
            journal._pair({"schema": old.SCHEMA, "kind": "REGISTERED", "number": 1, "previous": "0" * 64,
                "payload": {"host": old.host(), "locator": loc, "grant_sha256": digest(g), "initial": value}})
            write(journal.guard_path(g), journal.binding(g))
            payload = deepcopy(self.ticket["payload"])
            payload.update(grant_sha256=digest(g), value_sha256=digest(value), previous_event_sha256=digest(journal.events()[-1]),
                reserved_after={"calls": 1000, "jobs": 1, "gpu_seconds": 28800}, sizing={"calls": 1000, "seconds": 14400})
            envelope = old.sign(self.key, self.public, payload)
            journal.append("RESERVED", {"value": value, "ticket": envelope, "package": "data/processed/old"})
            if campaign != r.CAMPAIGNS[-1]:
                journal.append("PUBLISH_INTENT", {"ticket_sha256": digest(envelope)})
                journal.append("PUBLISHED", {"ticket_sha256": digest(envelope), "proof": {"synthetic": True}})
        # Tiny local evidence, never genuine model data or a provider assertion.
        self.evidence = []
        for i in range(3):
            name = "data/processed/local-evidence-" + str(i) + ".json"
            write(self.root / name, {"fixture": "SYNTHETIC_LOCAL_HISTORY_NOT_PROVIDER_AUTHORITY"})
            self.evidence.append(((name, "LOCAL_TICKET"),))
        self.directive_body = "SYNTHETIC Owner restart decision fixture, not an actual grant"
        self.directive = {"comment_id": r.DIRECTIVE, "body_sha256": hashlib.sha256(self.directive_body.encode()).hexdigest()}
        with patch.object(op, "LOCAL_EVIDENCE", self.evidence):
            snapshot = op.retirement_snapshot(self.directive)
        self.value = ui.initial(self.cohort, digest(self.cohort), self.value["request"]["resource_policy"],
            checkpoint_marker_sha256="b" * 64, run_id="restart-r", attempt_id="restart-a",
            job="nguynanhtn/safeshift-minicpm-" + r.CAMPAIGN + "-4",
            capsule_ref="nguynanhtn/safeshift-minicpm-capsule-" + r.CAMPAIGN + "-4/1",
            max_calls=3, max_seconds=600, nested_mounts=True, series={**contract.SERIES, "minicpm4": r.SERIES})
        self.grant.update(schema=a.RECOVERY_SCHEMA, authorization="OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY",
            campaign_id=r.CAMPAIGN, implementation_pr=199, scope=a.scope(self.value), recovery=snapshot,
            caps=r.budget_policy(snapshot["reserved"])["caps"], approvals={role: None for role in r.SOURCE_ROLES})
        self.provider["current_account_safety"] = {"retired_visibility": [{"job": j["job"],
            "visibility": "NOT_VISIBLE_NOW_NOT_VERIFIED_DELETED"} for j in snapshot["journals"]],
            "quota": deepcopy(self.provider["quota"]), "owned_sha256": self.provider["owned_sha256"],
            "observed_unix": self.provider["observed_unix"], "historical_provider_custody": "NOT_AUTHENTICATED_BY_RETIREMENT"}
        payload = deepcopy(self.ticket["payload"])
        payload.update(schema=a.RECOVERY_TICKET, grant_sha256=digest(self.grant), value_sha256=digest(self.value),
            capsule_sha256=digest(self.value), number=4, reserved_before=r.HISTORICAL,
            reserved_after={"calls": 3003, "jobs": 4, "gpu_seconds": 87600}, provider=deepcopy(self.provider))
        self.ticket = old.sign(self.key, self.public, payload)

    def build(self, ref, *, capsule_sha256, **kwargs):
        return {"cells": [{"cell_type": "code", "source": ["pass\n"]}], "metadata": {"safeshift": {
            "runtime_ref": ref, "source_sha256": self.value["request"]["source_sha256"], "capsule_sha256": capsule_sha256}}}

    def graph(self):
        grant = deepcopy(self.grant)
        graph = {"/pulls/199": {"merged": True, "draft": False, "base": {"ref": "main"},
            "head": {"sha": grant["reviewed_head"]}, "merge_commit_sha": grant["merged_sha"]}}
        def add(i, issue, marker, value):
            body = marker + "\n```json\n" + json.dumps(value) + "\n```"
            graph["/issues/comments/" + str(i)] = {"id": i, "issue_url": a.API + "/issues/" + str(issue),
                "user": {"id": a.OWNER_ID, "login": a.OWNER}, "body": body}
            return {"comment_id": i, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
        graph["/issues/comments/" + str(r.DIRECTIVE)] = {"id": r.DIRECTIVE, "issue_url": a.API + "/issues/199",
            "user": {"id": a.OWNER_ID, "login": a.OWNER}, "body": self.directive_body}
        for i, old_grant in enumerate(deepcopy(self.old_grants)):
            if i == 2:
                for number, role in enumerate(("O2", "O3", "O4", "O5", "O6"), 100):
                    old_grant["approvals"][role] = add(number, 198, a.APPROVAL,
                        {"kind": role, "status": "APPROVED", "reviewed_head": old_grant["reviewed_head"],
                         "subject_sha256": a.subject(old_grant)})
            row = grant["recovery"]["journals"][i]
            row["grant_locator"] = add(20 + i, 198, a.MARKER, old_grant)
            payload = deepcopy(row["ticket"]["payload"]); payload["grant_sha256"] = digest(old_grant)
            row["ticket"] = old.sign(self.key, self.public, payload)
        for number, role in enumerate(r.SOURCE_ROLES, 2):
            grant["approvals"][role] = add(number, 199, a.APPROVAL, {"kind": role, "status": "APPROVED",
                "reviewed_head": grant["reviewed_head"], "subject_sha256": a.subject(grant)})
        locator = add(1, 199, a.RECOVERY_MARKER, grant)
        rows = []
        for name in contract.sources():
            raw = (ui.ROOT / name).read_bytes()
            rows.append({"path": name, "type": "blob", "mode": "100644",
                "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()})
        for ref in (grant["runtime_commit"], grant["reviewed_head"], grant["merged_sha"]):
            graph["/git/trees/" + ref + "?recursive=1"] = {"truncated": False, "tree": deepcopy(rows)}
        return locator, graph, grant

    def test_one_authentic_directive_derived_policy_and_fresh_source_graph_not_fake_amendment(self):
        loc, graph, grant = self.graph()
        self.assertEqual(a.load(loc, reader=graph.__getitem__), grant)
        self.assertEqual(set(grant["approvals"]), set(r.SOURCE_ROLES))
        self.assertNotIn("budget_amendment", grant["recovery"])
        for mutate in (lambda g:g["/pulls/199"].update(merged=False),
                       lambda g:g["/issues/comments/" + str(r.DIRECTIVE)]["user"].update(id=1),
                       lambda g:g["/issues/comments/104"].update(body="wrong old rights"),
                       lambda g:g["/git/trees/" + grant["runtime_commit"] + "?recursive=1"]["tree"][0].update(sha="0" * 40)):
            bad = deepcopy(graph); mutate(bad)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): a.load(loc, reader=bad.__getitem__)

    def staged_operator(self):
        operator = op.RecoveredSerialJournal()
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(operator, "observe_provider", return_value=self.provider), \
             patch.object(old.sizing, "propose", return_value={"calls": 3, "seconds": 600}), \
             patch.object(old, "notebook", side_effect=self.build), patch("safeshift.internvl3763_operator.api", return_value=Mock()):
            operator.bind_release(self.locator, self.value)
            operator.stage(self.key, self.root / "data/processed/package")
        return operator

    def test_restart_starts_zero_with_all3763_and_no_historical_predictions(self):
        initial = op.restart_spec(self.value)
        self.assertEqual(initial["request"]["plan"]["scheduled_ordinals"], list(range(3763)))
        self.assertEqual(initial["request"]["plan"]["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(initial["request"]["history"], [])
        self.assertEqual(initial["request"]["campaign"]["series"]["minicpm4"], r.SERIES)
        self.assertEqual(initial["cohort"], self.cohort)

    def test_retirement_preserves_published_mismatch_uncertainty_and_old_bytes(self):
        before = {p: p.read_bytes() for p in (self.root / "data/processed").rglob("event-*.json")}
        snapshot = self.grant["recovery"]
        self.assertEqual(snapshot["reserved"], {"calls": 3000, "jobs": 3, "gpu_seconds": 86400})
        self.assertEqual(snapshot["journals"][0]["publication"], "PUBLISHED")
        self.assertTrue(all(j["historical_status"] == "PROVIDER_UNAVAILABLE_NOT_VERIFIED_DELETED" for j in snapshot["journals"]))
        op.verify_retired(snapshot)
        for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)
        for mutate in (lambda g:g["recovery"]["reserved"].update(calls=0),
                       lambda g:g["recovery"]["journals"][0].update(disposition="FAILED_PRE_NATIVE"),
                       lambda g:g["recovery"]["journals"][0].update(historical_status="VERIFIED_DELETED")):
            grant = deepcopy(self.grant); mutate(grant)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): a.validate(grant)

    def test_finite_derived_policy_covers_all_scheduler_reservations_not_weekly_quota(self):
        policy = r.budget_policy(r.HISTORICAL)
        self.assertEqual(policy["caps"], self.grant["caps"])
        self.assertGreater(policy["caps"]["total_gpu_seconds"], 108000)
        reserved = dict(r.HISTORICAL)
        for _ in range(3763):
            reserved = {"calls": reserved["calls"] + 3763, "jobs": reserved["jobs"] + 1,
                        "gpu_seconds": reserved["gpu_seconds"] + 28800}
        self.assertEqual(reserved, {k: policy["caps"]["total_" + k] for k in reserved})
        a.validate(self.grant)
        for key in self.grant["caps"]:
            bad = deepcopy(self.grant); bad["caps"][key] += 1
            with self.subTest(key=key), self.assertRaises(ValueError): a.validate(bad)

    def test_old_self_submit_authorization_and_cli_are_absent_or_denied(self):
        bad = deepcopy(self.grant); bad["authorization"] = "OWNER_MINICPM_TRAIN3763_CODEX_SUBMIT_ONCE"
        with self.assertRaises(ValueError): a.validate(bad)
        self.assertFalse(hasattr(op, "RecoveryOperator"))
        source = Path(op.__file__).read_text(encoding="utf-8")
        self.assertNotIn("kernels_push", source)
        self.assertNotIn("submit-once", source)
        self.assertNotIn("output_inventory", source)
        self.assertNotIn("def observe(", source)
        with patch.object(sys, "argv", ["recovery", "submit-once"]), patch("sys.stderr", new=io.StringIO()):
            with self.assertRaises(SystemExit): op.main()

    def test_expired_ticket_old_signature_and_source_drift_fail_closed(self):
        a.verify_ticket(self.grant, self.ticket, self.value)
        changed = deepcopy(self.value); changed["request"]["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError): a.verify_ticket(self.grant, self.ticket, changed)
        with patch.object(a.time, "time", return_value=self.grant["expires_unix"]):
            with self.assertRaisesRegex(ValueError, "TICKET_EXPIRED"): a.verify_ticket(self.grant, self.ticket, self.value)
        bad = deepcopy(self.ticket); bad["signature"] = "0" * 768
        with self.assertRaises(ValueError): a.verify_ticket(self.grant, bad, self.value)
        for mutate in (lambda t:t["provider"]["current_account_safety"]["quota"].update(reserved=1),
                       lambda t:t["provider"]["current_account_safety"]["retired_visibility"][0].update(visibility="VERIFIED_DELETED"),
                       lambda t:t["reserved_before"].update(calls=0)):
            payload = deepcopy(self.ticket["payload"]); mutate(payload)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                a.verify_ticket(self.grant, old.sign(self.key, self.public, payload), self.value)

    def test_duplicate_binding_stage_and_torn_history_never_reset_budget(self):
        before = {p: p.read_bytes() for p in (self.root / "data/processed").rglob("event-*.json")}
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant):
            _, _, reserved, item, _ = operator.state()
            self.assertEqual(reserved, item["ticket"]["payload"]["reserved_after"])
            with self.assertRaisesRegex(ValueError, "SECOND_BINDING"): operator.bind_release(self.locator, self.value)
            with self.assertRaisesRegex(ValueError, "OPEN_RESERVATION"): operator.stage(self.key, self.root / "duplicate")
        for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)
        (operator.mirror / "event-00003.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "MIRROR_BYTES"): op.inspect_journals()

    def test_retired_evidence_tamper_blocks_even_when_owner_excludes_predictions(self):
        file = self.root / self.evidence[0][0][0]
        file.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "EVIDENCE_DRIFT"): op.verify_retired(self.grant["recovery"])

    def test_current_quota_active_vm_and_unknown_new_job_block_without_old_get(self):
        client = Mock()
        client.kernels_list_with_response.return_value = NS(kernels=[], next_page_token="")
        quota = NS(time_used=timedelta(seconds=26745), time_reserved=timedelta(0), total_time_allowed=timedelta(seconds=108000))
        client.quota_view.return_value = NS(gpu_quota=quota)
        proof = op.current_safety(client, self.grant["recovery"], [], self.value["job"])
        client.kernels_status.assert_not_called()
        self.assertEqual(proof["historical_provider_custody"], "NOT_AUTHENTICATED_BY_RETIREMENT")
        quota.time_reserved = timedelta(seconds=1)
        with self.assertRaisesRegex(ValueError, "ACTIVE_SESSION"): op.current_safety(client, self.grant["recovery"], [], self.value["job"])
        quota.time_reserved = timedelta(0)
        client.kernels_list_with_response.return_value = NS(kernels=[NS(ref=self.value["job"])], next_page_token="")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_UNKNOWN"): op.current_safety(client, self.grant["recovery"], [], self.value["job"])
        client.kernels_list_with_response.return_value = NS(kernels=[NS(ref=r.CAMPAIGNS[0].join(["nguynanhtn/safeshift-minicpm-", "-1"]))], next_page_token="")
        client.kernels_status.return_value = NS(status="RUNNING")
        with self.assertRaisesRegex(ValueError, "RETIRED_JOB_ACTIVE"): op.current_safety(client, self.grant["recovery"], [], self.value["job"])

    def test_five_nested_mounts_and_accelerator_are_enforced_in_collection(self):
        table = r.mounted_inputs(self.value)
        self.assertEqual(len(table), 5)
        from safeshift.internvl3763_operator import verify_kernel_metadata_inputs
        meta = NS(machine_shape="NvidiaTeslaT4", dataset_data_sources=[v.rsplit("/", 1)[0] for v in self.value["input_sources"]["dataset_sources"]],
            kernel_data_sources=[ui.CHECKPOINT.rsplit("/", 1)[0]])
        verify_kernel_metadata_inputs(meta, self.value["input_sources"])
        for shape in ("NvidiaTeslaP100", None, "UNKNOWN"):
            meta.machine_shape = shape
            with self.subTest(shape=shape), self.assertRaises(ValueError): verify_kernel_metadata_inputs(meta, self.value["input_sources"])

    def test_publish_is_real_owner_ui_handoff_no_notebook_submit_and_no_duplicate_create(self):
        operator = self.staged_operator()
        client = Mock(); client.dataset_create_new.return_value = NS(status="ok", error="")
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(operator, "observe_provider", return_value=self.provider), \
             patch.object(old, "notebook", side_effect=self.build), \
             patch.object(old, "verify_published_capsule", return_value={"private": True, "version": 1}), \
             patch("safeshift.internvl3763_operator.api", return_value=client):
            result = operator.publish()
            self.assertEqual(result["status"], "RELEASED_FOR_OWNER_UI")
            self.assertEqual(result["mode"], "OWNER_UI_ONLY")
            self.assertEqual(result["timezone"], "Asia/Ho_Chi_Minh")
            self.assertEqual(len(result["input_mounts"]), 5)
            self.assertEqual(result["historical_reservations"], r.HISTORICAL)
            self.assertFalse(result["scientific_inheritance"])
            self.assertTrue((self.root / result["notebook_file"]).is_file())
            with self.assertRaisesRegex(ValueError, "UNPUBLISHED_RESERVATION"): operator.publish()
        client.kernels_push.assert_not_called()
        self.assertEqual(client.dataset_create_new.call_count, 1)

    def test_upload_timeout_stays_ambiguous_preserves_reservation_and_never_retries(self):
        operator = self.staged_operator()
        client = Mock(); client.dataset_create_new.side_effect = TimeoutError("synthetic ambiguous upload")
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(old, "notebook", side_effect=self.build), \
             patch("safeshift.internvl3763_operator.api", return_value=client):
            with self.assertRaises(TimeoutError): operator.publish()
            with self.assertRaisesRegex(ValueError, "UPLOAD_UNKNOWN_VERIFY_ONLY"): operator.publish()
            self.assertEqual(operator.state()[2]["gpu_seconds"], 87600)
        self.assertEqual(client.dataset_create_new.call_count, 1)

    def test_expired_owner_start_window_never_publishes_or_refreshes_ticket(self):
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant): item = operator.state()[3]
        client = Mock()
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(old, "notebook", side_effect=self.build), \
             patch.object(a.time, "time", return_value=item["ticket"]["payload"]["start_before_unix"]), \
             patch("safeshift.internvl3763_operator.api", return_value=client):
            with self.assertRaisesRegex(ValueError, "PROVIDER_TICKET_STALE"): operator.publish()
            self.assertEqual(operator.state()[2], item["ticket"]["payload"]["reserved_after"])
        client.dataset_create_new.assert_not_called()

    def test_project_budget_never_overrides_exhausted_real_quota(self):
        provider = deepcopy(self.provider)
        provider["quota"] = {"used": 108000, "reserved": 0, "total": 108000}
        with self.assertRaisesRegex(ValueError, "BUDGET_EXHAUSTED"):
            old.sizing.propose(self.grant, 3763, r.HISTORICAL, provider)

    def test_local_notebook_tamper_blocks_owner_ready_before_capsule_post(self):
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant): item = operator.state()[3]
        path = self.root / item["package"] / "notebook.ipynb"
        nb = read(path); nb["cells"][0]["source"] = ["raise RuntimeError('tampered')\n"]
        path.write_text(json.dumps(nb), encoding="utf-8")
        client = Mock()
        with patch.object(a, "load", return_value=self.grant), patch.object(old, "clean_source"), \
             patch.object(old, "notebook", side_effect=self.build), \
             patch("safeshift.internvl3763_operator.api", return_value=client):
            with self.assertRaisesRegex(ValueError, "EXACT_SOURCE_NOTEBOOK"): operator.publish()
        client.dataset_create_new.assert_not_called()


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
    def test_antigravity_same_journal_collects_real_synthetic_zips_and_stages_pending_only(self):
        from safeshift.fulltrain import runtime as rt, contract
        from safeshift.candidates import fulltrain_run as journal
        from safeshift.fulltrain.minicpm_execution import retain_sealed_trees
        operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant): _, _, _, item, _ = operator.state()
        value, ticket = item["value"], item["ticket"]
        checksum = digest(ticket)
        operator.append("PUBLISH_INTENT", {"ticket_sha256": checksum})
        operator.append("PUBLISHED", {"ticket_sha256": checksum, "proof": {}})
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
            stack.enter_context(patch.object(serial, "observe_provider", side_effect=lambda client, grant, v, prior: provider(client, grant, v, None, recovered=serial.state()[4])))
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
