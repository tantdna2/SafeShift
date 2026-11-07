"""Synthetic campaign grant/serial operator/custody tests. No Kaggle or data."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import zipfile

from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as c
from safeshift import internvl3763_operator as op
from safeshift import internvl3763_release as old
from safeshift.candidates.fulltrain_run import synthetic_cohort, synthetic_bytes
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import write, read, sha, export
from safeshift.pilot.contract import digest, MASTER_SHA
from test_internvl3763_execution import fixture as legacy_fixture
import test_internvl3763 as controller_fixtures


def fixture(ledger_root, *, actual_source=False, kernel_sources=()):
    request, _, _ = legacy_fixture()
    request["bindings"]["dataset"]["kernel_sources"] = list(kernel_sources)
    if actual_source:
        notebook = "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb"
        request.update(notebook=notebook, notebook_sha256=sha(runtime.ROOT/notebook),
            runtime_commit=read(runtime.ROOT/notebook)["metadata"]["safeshift"]["runtime_commit"],
            commit_sha=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime.ROOT, text=True).strip())
    cohort = request["bindings"]["runtime"]["execution_request"]["cohort"]
    grant = {"schema": c.SCHEMA, "campaign_id": "synthetic180", "operator_id": "synthetic-machine",
        "operator_root_sha256": c.operator_binding(ledger_root),
        "authorization": "GRANTED_FOR_BOUNDED_CAMPAIGN", "implementation_pr": 181,
        "reviewed_head": "a"*40, "merged_sha": request["commit_sha"], "science_sha256": digest(c.science()),
        "cohort_sha256": digest(cohort), "input_marker_sha256": MASTER_SHA,
        "inputs": {"dataset_sources": ["nguynanhtn/synthetic-input/1"], "kernel_sources": list(kernel_sources)},
        "rights": {key: {"status": "APPROVED", "ref": "https://evidence.invalid/synthetic/"+key,
            "sha256": "1"*64} for key in ("O2", "O3", "O4", "O5", "O6")},
        "review_logins": ["synthetic-reviewer"], "audit_logins": ["synthetic-auditor"],
        "issued_unix": int(time.time())-10, "expires_unix": int(time.time())+86400,
        "caps": {"total_calls": 10, "total_jobs": 10, "total_gpu_seconds": 36000, "job_calls": 4,
            "job_seconds": 1800, "physical_gpus": 2, "machine_shape": "NvidiaTeslaT4",
            "archive_bytes": 7*2**30, "max_repairs_per_image": 2},
        "policy": {"serial": True, "resume": "NOT_ATTEMPTED_ONLY", "repair": "DIAGNOSED_TECHNICAL_ONLY",
            "technical_fixes": "REVIEWED_MERGED_SCIENCE_UNCHANGED", "ambiguous": "STOP_READ_ONLY", "refund": False,
            "test": False, "scientific_selection": "PENDING", "pooling": False}}
    p = c.plan(cohort, [], action="initial", run_id="synthetic180-1", attempt_id="attempt-1", max_calls=1, max_seconds=1800)
    execution = request["bindings"]["runtime"]["execution_request"]
    execution.update(plan=p, source=runtime.source_spec(), input_marker_sha256=MASTER_SHA)
    request.update(scope=c.SCOPE, handoff_id="synthetic180-1", job="nguynanhtn/safeshift-train3763-synthetic180-1", plan=p,
        plan_sha256=digest(p), limits={"monitor_seconds": 900, "job_seconds": 1800, "max_calls": 1})
    request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
    request["bindings"].update(source=execution["source"], rights=grant["rights"], scientific_method={"science_sha256": grant["science_sha256"]})
    comments = {"/pulls/181": {"merged": True, "head": {"sha": "a"*40}, "merge_commit_sha": grant["merged_sha"], "base": {"ref": "main"}}}
    def comment(number, marker, value, login):
        body = marker+"\n```json\n"+json.dumps(value)+"\n```"
        comments["/issues/comments/"+str(number)] = {"id": number, "body": body, "user": {"login": login},
            "issue_url": old.API+"/issues/181"}
        return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
    locator = comment(2000, c.MARKER, grant, old.OWNER)
    audit = comment(2001, "SAFESHIFT_TRAIN3763_AUDIT_V1", {"campaign_sha256": digest(grant), "reviewed_head": "a"*40,
        "source_sha256": digest(runtime.source_spec()), "regression_sha256": "e"*64, "status": "PASS", "independent": True}, "synthetic-auditor")
    reviewed = comment(2002, "SAFESHIFT_TRAIN3763_TECHNICAL_V1", {"campaign_sha256": digest(grant),
        "science_sha256": grant["science_sha256"], "implementation_pr": 181, "reviewed_head": "a"*40,
        "merged_sha": grant["merged_sha"], "runtime_commit": request["runtime_commit"], "source_sha256": digest(runtime.source_spec()),
        "notebook_sha256": request["notebook_sha256"], "notebook_code_sha256": "d"*64, "regression_sha256": "e"*64,
        "audit": audit}, "synthetic-reviewer")
    request["execution_release"] = locator
    request["bindings"]["runtime"].update(technical_revision=reviewed, campaign_ledger="data/processed/synthetic-ledger",
        execution_input={"kind": "dataset_sources", "ref": "nguynanhtn/synthetic-capsule/1"})
    request["bindings"]["dataset"]["dataset_sources"].append("nguynanhtn/synthetic-capsule/1")
    return request, grant, comments


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, self.grant, self.comments = fixture(self.root/"ledger")
        self.reader = lambda path: deepcopy(self.comments[path])
        self.patch = patch.object(old, "get", side_effect=self.reader)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.ledger = c.Ledger.create(self.root/"ledger", self.root/"mirror", self.grant, "synthetic-machine")
        absence = patch.object(op, "pre_submit_inventory", side_effect=lambda ledger, intent: {
            "job": intent["request"]["job"], "intent_sha256": digest(intent), "job_absent": True,
            "inventory": {"notice": "SYNTHETIC_PROVIDER_ABSENCE_ONLY"}})
        self.absence = absence.start(); self.addCleanup(absence.stop)

    def test_one_authentic_campaign_grant_and_no_per_job_release(self):
        self.assertEqual(c.load(self.request["execution_release"]), self.grant)
        self.assertEqual(c.bind(self.grant, self.request), self.request["bindings"]["runtime"]["execution_request"])
        intent = self.ledger.reserve(self.request)
        self.assertEqual(intent["reserved_calls"], 1)
        self.assertNotIn("witness", self.grant)
        self.assertNotIn("attempt", self.grant)
        self.assertEqual(self.ledger.summary()["counts"], {"NOT_ATTEMPTED": 3763})

    def test_pending_rights_bool_caps_expiry_old_grants_and_science_drift_block(self):
        for mutate in (lambda g: g["rights"]["O3"].update(status="PENDING"),
                lambda g: g["caps"].update(total_jobs=True), lambda g: g.update(science_sha256="0"*64),
                lambda g: g.update(implementation_pr=179), lambda g: g["caps"].update(total_calls=0),
                lambda g: g.update(expires_unix=g["issued_unix"]-1)):
            bad = deepcopy(self.grant); mutate(bad)
            with self.subTest(bad=bad["caps"]), self.assertRaises(ValueError):
                c.validate(bad)
        with self.assertRaisesRegex(ValueError, "WINDOW"):
            c.validate(self.grant, now=self.grant["expires_unix"]+1)
        c.validate(self.grant, now=self.grant["expires_unix"]+1, collection=True)

    def test_owner_comment_tampering_wrong_owner_and_no_self_approval(self):
        original = deepcopy(self.comments)
        for mutate in (lambda: self.comments["/issues/comments/2000"]["user"].update(login="attacker"),
                lambda: self.comments["/issues/comments/2000"].update(body="edited"),
                lambda: self.comments["/pulls/181"].update(merged=False)):
            self.comments = deepcopy(original); mutate()
            with self.assertRaises(ValueError):
                c.load(self.request["execution_release"])

    def test_revision_requires_actual_review_audit_merge_and_frozen_science(self):
        for number, login in ((2002, "attacker"), (2001, "attacker")):
            original = self.comments[f"/issues/comments/{number}"]["user"]["login"]
            self.comments[f"/issues/comments/{number}"]["user"]["login"] = login
            with self.assertRaises(ValueError):
                c.bind(self.grant, self.request)
            self.comments[f"/issues/comments/{number}"]["user"]["login"] = original
        bad = deepcopy(self.request)
        bad["bindings"]["runtime"]["execution_request"]["source"]["manifest"]["safeshift/internvl_grammar.py"] = "0"*64
        with self.assertRaises(ValueError):
            c.bind(self.grant, bad)

    def test_missing_original_input_checkpoint_or_changed_order_is_blocked(self):
        bad = deepcopy(self.request); bad["bindings"]["dataset"]["dataset_sources"] = ["nguynanhtn/other/2"]
        with self.assertRaisesRegex(ValueError, "ORIGINAL_INPUT"):
            c.bind(self.grant, bad)
        bad = deepcopy(self.request)
        bad["bindings"]["runtime"]["execution_request"]["cohort"]["samples"].reverse()
        with self.assertRaises(ValueError):
            c.bind(self.grant, bad)

    def test_duplicate_intent_and_parallel_stagers_cannot_reserve_twice(self):
        def reserve(_):
            try:
                self.ledger.reserve(self.request)
                return True
            except (ValueError, RuntimeError):
                return False
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(sorted(pool.map(reserve, range(2))), [False, True])
        self.assertEqual(len(self.ledger.intents()), 1)

    def test_two_real_processes_exclude_same_campaign_lock(self):
        with lock(self.ledger.root):
            code = "from safeshift.kaggle_handoff import lock; import sys;\nwith lock(sys.argv[1]): print('BAD')"
            result = subprocess.run([sys.executable, "-B", "-c", code, str(self.ledger.root)], cwd=runtime.ROOT,
                capture_output=True, text=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ANOTHER_OPERATOR_ACTIVE", result.stderr)

    def test_partial_journal_write_rollback_loss_and_mirror_divergence_block(self):
        intent = self.ledger.reserve(self.request)
        name = "journal-000001.json"
        original = (self.ledger.mirror/name).read_bytes()
        (self.ledger.mirror/name).unlink()  # synthetic rollback of one durable copy
        with self.assertRaisesRegex(ValueError, "ROLLBACK"):
            c.Ledger(self.ledger.root)
        (self.ledger.mirror/name).write_bytes(original+b" ")
        with self.assertRaisesRegex(ValueError, "DIVERGENCE"):
            c.Ledger(self.ledger.root)
        self.assertEqual(intent["kind"], "INTENT")

    def test_torn_second_copy_never_opens_new_attempt(self):
        real_write = c.write
        def writer(path, value):
            if Path(path).parent == self.ledger.mirror and Path(path).name.startswith("journal"):
                raise OSError("SYNTHETIC_DISK_FULL")
            return real_write(path, value)
        with patch.object(c, "write", side_effect=writer), self.assertRaises(OSError):
            self.ledger.reserve(self.request)
        with self.assertRaisesRegex(ValueError, "ROLLBACK"):
            self.ledger.reserve(self.request)

    def test_unknown_submit_burns_budget_and_only_allows_collection(self):
        intent = self.ledger.reserve(self.request)
        with lock(self.ledger.root):
            self.ledger.append("PUSH_INTENT", intent_sha256=digest(intent))
        reopened = c.Ledger(self.ledger.root)
        self.assertTrue(reopened.summary()["blocked_open_intent"])
        self.assertEqual(reopened.summary()["reserved_gpu_seconds"], 3600)
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS"):
            reopened.reserve(self.request)
        with self.assertRaisesRegex(ValueError, "POSSIBLE_SUBMIT"):
            reopened.abort_pre_submit()

    def test_pre_submit_abort_never_refunds_and_requires_provider_proof(self):
        self.ledger.reserve(self.request)
        self.ledger.abort_pre_submit()
        self.assertIsNone(self.ledger.open_intent())
        self.assertEqual(self.ledger.summary()["reserved_calls"], 1)
        self.absence.assert_called_once()

    def test_unknown_provider_or_existing_job_preserves_both_original_journals(self):
        self.ledger.reserve(self.request)
        before = {p.name: p.read_bytes() for p in self.ledger.root.glob("journal-*.json")}
        for failure in (TimeoutError("SYNTHETIC_PROVIDER_UNKNOWN"), ValueError("JOB_EXISTS_NO_NEW_VERSION_OR_RETRY")):
            self.absence.side_effect = failure
            with self.assertRaises(type(failure)):
                self.ledger.abort_pre_submit()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.ledger.root.glob("journal-*.json")})
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.ledger.mirror.glob("journal-*.json")})
            self.assertIsNotNone(self.ledger.open_intent())

    def test_recovery_preserves_attempt1_then_binds_new_source_capsule_and_review_for_attempt2(self):
        first = self.ledger.reserve(self.request)
        original = (self.ledger.root/"journal-000001.json").read_bytes()
        closed = self.ledger.abort_pre_submit()
        self.assertFalse(closed["refund"])
        self.assertEqual(closed["provider"]["intent_sha256"], digest(first))
        next_request = self.next_request([])
        prior_source = runtime.source_spec()
        changed = deepcopy(prior_source)
        changed["manifest"]["safeshift/internvl3763_operator.py"] = "9"*64
        new_merge, new_runtime = "b"*40, "c"*40
        with patch.object(runtime, "source_spec", return_value=changed):
            execution = next_request["bindings"]["runtime"]["execution_request"]
            execution["source"] = changed
            execution["plan"]["runtime_source"] = changed
            next_request["bindings"]["source"] = changed
            next_request["plan"] = execution["plan"]
            next_request["plan_sha256"] = digest(next_request["plan"])
            next_request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
            # An operational change still cannot reuse old technical attestations.
            with self.assertRaisesRegex(ValueError, "TECHNICAL_SOURCE_BINDING"):
                c.bind(self.grant, next_request)
            technical = json.loads(self.comments["/issues/comments/2002"]["body"].split("```json\n")[1].split("\n```")[0])
            technical.update(implementation_pr=182, merged_sha=new_merge, runtime_commit=new_runtime,
                source_sha256=digest(changed), notebook_sha256="8"*64, notebook_code_sha256="7"*64)
            next_request.update(commit_sha=new_merge, runtime_commit=new_runtime, notebook_sha256="8"*64)
            self.comments["/pulls/182"] = {"merged": True, "head": {"sha": "a"*40}, "merge_commit_sha": new_merge, "base": {"ref": "main"}}
            for number, marker, value in ((2001, "SAFESHIFT_TRAIN3763_AUDIT_V1", {
                    "campaign_sha256": digest(self.grant), "reviewed_head": "a"*40, "source_sha256": digest(changed),
                    "regression_sha256": "e"*64, "status": "PASS", "independent": True}),
                    (2002, "SAFESHIFT_TRAIN3763_TECHNICAL_V1", technical)):
                if number == 2002:
                    value["audit"]["body_sha256"] = hashlib.sha256(self.comments["/issues/comments/2001"]["body"].encode()).hexdigest()
                comment = self.comments[f"/issues/comments/{number}"]
                comment.update(issue_url=old.API+"/issues/182", body=marker+"\n```json\n"+json.dumps(value)+"\n```")
            next_request["bindings"]["runtime"]["technical_revision"]["body_sha256"] = hashlib.sha256(
                self.comments["/issues/comments/2002"]["body"].encode()).hexdigest()
            second = self.ledger.reserve(next_request)
            self.assertEqual(second["request"]["execution_release"], first["request"]["execution_release"])
            self.assertNotEqual(digest(changed), digest(prior_source))
            self.assertEqual(next_request["plan"]["science_sha256"], self.grant["science_sha256"])
            self.assertEqual(next_request["plan"]["scheduled_ordinals"], [0])
            self.assertEqual(execution["cohort"], self.request["bindings"]["runtime"]["execution_request"]["cohort"])
            self.assertEqual(execution["history"], [])
        self.assertEqual(original, (self.ledger.root/"journal-000001.json").read_bytes())
        self.assertEqual(original, (self.ledger.mirror/"journal-000001.json").read_bytes())
        summary = self.ledger.summary()
        self.assertEqual((summary["jobs"], summary["reserved_calls"], summary["reserved_gpu_seconds"]), (2, 2, 7200))

    def test_reused_capsule_or_existing_handoff_does_not_reserve_attempt2(self):
        from scripts.train3763_campaign import stage
        self.ledger.reserve(self.request); self.ledger.abort_pre_submit()
        second = self.next_request([])
        previous = self.request["bindings"]["runtime"]["execution_input"]["ref"]
        current = second["bindings"]["runtime"]["execution_input"]["ref"]
        second["bindings"]["runtime"]["execution_input"]["ref"] = previous
        sources = second["bindings"]["dataset"]["dataset_sources"]
        sources[sources.index(current)] = previous
        with self.assertRaisesRegex(ValueError, "NEW_CAPSULE"):
            self.ledger.reserve(second)
        handoff = self.root/"existing"; handoff.mkdir(); write(handoff/"evidence.json", {"preserve": True})
        with self.assertRaisesRegex(ValueError, "EXISTING_HANDOFF_PRESERVED"):
            stage(self.ledger, {}, {}, {}, directory=handoff, calls=1, seconds=1800, action="initial")
        self.assertEqual(len(self.ledger.intents()), 1)
        self.assertTrue(read(handoff/"evidence.json")["preserve"])

    def test_host_change_never_silently_takes_over(self):
        with patch.object(c, "host_identity", return_value="0"*64), self.assertRaisesRegex(ValueError, "TAKEOVER"):
            c.Ledger(self.ledger.root)

    def test_second_directory_cannot_create_another_campaign_authority(self):
        with self.assertRaisesRegex(ValueError, "CANONICAL_OPERATOR_ROOT"):
            c.Ledger.create(self.root/"other-ledger", self.root/"other-mirror", self.grant, "synthetic-machine")
        with self.assertRaises((FileExistsError, ValueError)):
            c.Ledger.create(self.ledger.root, self.root/"other-mirror", self.grant, "synthetic-machine")

    def test_lost_journals_cannot_be_reinitialized_as_empty_campaign(self):
        self.ledger.reserve(self.request)
        self.assertTrue(self.ledger.root.resolve().is_relative_to(self.root.resolve()))
        self.assertTrue(self.ledger.mirror.resolve().is_relative_to(self.root.resolve()))
        self.ledger.root.rename(self.root/"lost-ledger")
        self.ledger.mirror.rename(self.root/"lost-mirror")
        with self.assertRaises(FileExistsError):
            c.Ledger.create(self.ledger.root, self.ledger.mirror, self.grant, "synthetic-machine")

    def test_first_source_job_is_exactly_one_call_ordinal0(self):
        execution = deepcopy(self.request["bindings"]["runtime"]["execution_request"])
        p = c.plan(execution["cohort"], [], action="initial", run_id="synthetic180-1", attempt_id="attempt-1", max_calls=2, max_seconds=1800)
        execution["plan"] = p
        self.request["bindings"]["runtime"]["execution_request"] = execution
        self.request.update(plan=p, plan_sha256=digest(p))
        self.request["limits"]["max_calls"] = 2
        self.request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        with self.assertRaisesRegex(ValueError, "ONE_CALL"):
            self.ledger.reserve(self.request)

    def test_native_parent_order_load_and_call_replay_prevention(self):
        intent = self.ledger.reserve(self.request)
        claims = c.NativeClaims(self.root/"native", self.request, intent, self.grant)
        with self.assertRaises((FileNotFoundError, ValueError)):
            claims.claim("load")
        for kind in ("launch", "worker", "load", "call-000000"):
            self.assertTrue(claims.claim(kind)["created"])
            with self.assertRaises((FileExistsError, ValueError)):
                claims.claim(kind)
        with self.assertRaisesRegex(ValueError, "SCHEDULED"):
            claims.claim("call-000001")

    def test_production_activation_uses_campaign_not_per_attempt_witness(self):
        intent = self.ledger.reserve(self.request)
        real_claims = c.NativeClaims
        def claims(_root, request, reserved, grant):
            return real_claims(self.root/"activation-native", request, reserved, grant)
        self.addCleanup(setattr, old, "_active", None)
        self.addCleanup(setattr, old, "_activation_claim", None)
        old._active = None
        with patch.object(c, "NativeClaims", side_effect=claims), \
                patch.object(old.Witness, "claim", side_effect=AssertionError("NO_HTTPS_WITNESS")):
            self.assertEqual(old.activate(self.request, "launch", intent=intent), self.grant)
            self.assertEqual(old.authorize("execute"), self.grant)
            with self.assertRaisesRegex(ValueError, "PHASE_MISMATCH"):
                old.authorize("load")
            old._active = None  # distinct worker process capability
            self.assertEqual(old.activate(self.request, "worker", intent=intent), self.grant)
            self.assertTrue(old.authorize("load")["created"])
            self.assertTrue(old.authorize("call", ordinal=0)["created"])
            with self.assertRaisesRegex(ValueError, "REPLAY"):
                old.authorize("call", ordinal=0)

    def test_production_worker_routes_campaign_to_original_mounts_before_model_load(self):
        from safeshift.fulltrain import inputs as packed
        request_path = self.root/"worker-request.json"
        write(request_path, self.request)
        intent = self.ledger.reserve(self.request)
        write(self.root/"campaign-intent.json", intent)
        cohort = self.request["bindings"]["runtime"]["execution_request"]["cohort"]
        out = self.root/"worker-output"; out.mkdir()
        source = self.root/"checkpoint-source"; source.mkdir()
        (source/"tokenizer.json").write_text("SYNTHETIC_TOKENIZER_BYTES", encoding="utf8")
        rows = [{**row, "image": f"train/Annotations/synthetic-{row['ordinal']:06d}.jpg"} for row in cohort["samples"]]
        self.addCleanup(setattr, old, "_active", None)
        old._active = None
        with patch.object(old, "activate", return_value=self.grant), \
                patch.object(runtime, "authorize"), patch.object(old, "activation_claim", return_value={"scope": "SYNTHETIC"}), \
                patch.object(runtime, "preflight", return_value=(source, self.root/"weights")), \
                patch.object(packed, "admit", side_effect=AssertionError("NO_NEW_PACKED_3763_BUNDLE")), \
                patch.object(packed, "verify_image_bytes", side_effect=AssertionError("NO_OPAQUE_COPY_VALIDATION")), \
                patch.object(c, "admit_inputs", return_value=(self.root/"original", cohort, rows, {"input_copy_bytes": 0})) as admission, \
                patch.object(runtime, "_execute", return_value={"scope": "SYNTHETIC_DISPATCH_CHECK"}) as execute:
            result = runtime.worker(request_path, output=out, scratch=self.root/"scratch", inputs=self.root/"inputs", deadline=1000)
        self.assertEqual(result["scope"], "SYNTHETIC_DISPATCH_CHECK")
        admission.assert_called_once_with(self.root/"inputs", MASTER_SHA, digest(cohort))
        self.assertEqual(execute.call_args.kwargs["image_path"](rows[0]), self.root/"original/train/Annotations/synthetic-000000.jpg")
        self.assertEqual(read(out/"environment/image-bytes.json"), {"input_copy_bytes": 0})

    def test_duplicate_notebook_launch_survives_new_claim_object(self):
        intent = self.ledger.reserve(self.request)
        c.NativeClaims(self.root/"native", self.request, intent, self.grant).claim("launch")
        with self.assertRaises(FileExistsError):
            c.NativeClaims(self.root/"native", self.request, intent, self.grant).claim("launch")

    def test_no_authority_network_means_no_sdk_no_private_input(self):
        with patch.object(c, "load", side_effect=ConnectionError("SYNTHETIC_OFFLINE")), \
                patch.object(op, "api", side_effect=AssertionError("NO_AUTH")), self.assertRaises(ConnectionError):
            op.admit(self.request)

    def test_submit_ambiguous_return_has_one_post_and_durable_push_intent(self):
        intent = self.ledger.reserve(self.request)
        client = NS(kernels_push=Mock(side_effect=TimeoutError("SYNTHETIC_LOST_RESPONSE")))
        notebook = self.root/"notebook.ipynb"; write(notebook, {"cells": []})
        root = self.root/"handoff"; root.mkdir()
        with patch.object(op, "campaign_ledger", return_value=self.ledger), \
                patch.object(op, "admit_campaign", return_value=(self.grant, self.request["bindings"]["runtime"]["execution_request"])), \
                patch.object(op, "api", return_value=client), patch.object(op, "campaign_inventory", return_value={"scope": "SYNTHETIC"}), \
                patch.object(op, "verify_execution_input", return_value={"scope": "SYNTHETIC_INPUT_PROOF"}), \
                patch.object(op, "safe", return_value=notebook), self.assertRaises(TimeoutError):
            op.submit_campaign(self.request, self.grant, self.request["bindings"]["runtime"]["execution_request"], root)
        self.assertEqual(client.kernels_push.call_count, 1)
        self.assertTrue(read(root/"submission/kernel-metadata.json")["is_private"])
        self.assertEqual(self.ledger.open_intent(), intent)
        self.assertIn("PUSH_INTENT", [x["kind"] for x in self.ledger.events()])

    def test_provider_running_or_wrong_identity_cannot_close_intent(self):
        intent = self.ledger.reserve(self.request)
        with lock(self.ledger.root):
            self.ledger.append("PUSH_INTENT", intent_sha256=digest(intent))
        with self.assertRaisesRegex(ValueError, "TERMINAL"):
            self.ledger.collect(self.request, self.root/"missing.zip", {"state": "RUNNING", "job_id": self.request["job"],
                "version": 1, "notebook_sha256": self.request["notebook_sha256"]})
        self.assertIsNotNone(self.ledger.open_intent())

    def test_wrong_capsule_blocks_the_actual_submit_path_before_push_intent(self):
        self.ledger.reserve(self.request)
        client = NS(kernels_push=Mock(side_effect=AssertionError("NO_GPU_SUBMIT")))
        root = self.root/"handoff"; root.mkdir()
        execution = self.request["bindings"]["runtime"]["execution_request"]
        with patch.object(op, "campaign_ledger", return_value=self.ledger), \
                patch.object(op, "admit_campaign", return_value=(self.grant, execution)), \
                patch.object(op, "api", return_value=client), patch.object(op, "campaign_inventory", return_value={}), \
                patch.object(op, "verify_execution_input", side_effect=ValueError("STALE_OR_WRONG_CAPSULE_NO_GPU_SUBMIT")), \
                self.assertRaisesRegex(ValueError, "STALE_OR_WRONG"):
            op.submit_campaign(self.request, self.grant, execution, root)
        client.kernels_push.assert_not_called()
        self.assertNotIn("PUSH_INTENT", [x["kind"] for x in self.ledger.events()])

    def test_collect_uses_the_committed_job_notebook_after_operator_source_update(self):
        from safeshift.kaggle_handoff import Train3763Operator
        notebook = {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC')"]}]}
        content = json.dumps(notebook).encode()
        request = deepcopy(self.request)
        request["notebook_sha256"] = hashlib.sha256(content).hexdigest()
        inputs = request["bindings"]["dataset"]
        unversioned_datasets = [ref.rsplit("/", 1)[0] for ref in inputs["dataset_sources"]]
        unversioned_kernels = [ref.rsplit("/", 1)[0] for ref in inputs["kernel_sources"]]
        remote = NS(metadata=NS(ref=request["job"], is_private=True, current_version_number=1, id=123,
            machine_shape="NvidiaTeslaT4", dataset_data_sources=unversioned_datasets,
            kernel_data_sources=unversioned_kernels, competition_data_sources=[], model_data_sources=[]),
            blob=NS(source=json.dumps(notebook)))
        operator = Train3763Operator()
        with patch.object(operator, "_api", return_value=NS()), patch("scripts.submit_internvl_v2.get_kernel", return_value=remote), \
                patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=content) as git:
            result = operator.identity(request)
        self.assertEqual(result["notebook_sha256"], request["notebook_sha256"])
        self.assertIn(request["commit_sha"]+":"+request["notebook"], git.call_args.args[0])

    def next_request(self, history, number=2, *, calls=1):
        request = deepcopy(self.request)
        previous = request["bindings"]["runtime"]["execution_input"]["ref"]
        capsule = f"nguynanhtn/synthetic-capsule-attempt{number}/1"
        request["bindings"]["runtime"]["execution_input"]["ref"] = capsule
        sources = request["bindings"]["dataset"]["dataset_sources"]
        sources[sources.index(previous)] = capsule
        execution = request["bindings"]["runtime"]["execution_request"]
        p = c.plan(execution["cohort"], history, action="resume" if history else "initial",
            run_id=f"synthetic180-{number}", attempt_id=f"attempt-{number}", max_calls=calls, max_seconds=1800)
        execution.update(plan=p, history=history,
            history_archives=[{"archive": f"history/{i}.zip", "sha256": h["evidence_sha256"], "plan": self.request["plan"]} for i, h in enumerate(history)])
        request.update(handoff_id=f"synthetic180-{number}", job=f"nguynanhtn/safeshift-train3763-synthetic180-{number}",
            plan=p, plan_sha256=digest(p))
        request["limits"]["max_calls"] = calls
        request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        return request

    def test_two_completed_jobs_use_same_campaign_comment_and_remaining_caps(self):
        # Ledger/protocol integration seam: real ZIP/hash/member export, scripted
        # status metadata. Native vector verification is tested separately by
        # the real controller tests; this fixture never claims GPU/inference.
        history_by_sha = {}
        def history(archive, checksum, plan):
            return deepcopy(history_by_sha[checksum])
        with patch.object(runtime, "verify_bundle", return_value={"status": "PASS", "scope": "SYNTHETIC_ONLY"}), \
                patch.object(runtime, "sealed_history", side_effect=history):
            request = self.request
            for number, status in ((1, "INVALID"), (2, "TECHNICAL_ERROR")):
                intent = self.ledger.reserve(request)
                with lock(self.ledger.root):
                    self.ledger.append("PUSH_INTENT", intent_sha256=digest(intent))
                ordinal = request["plan"]["scheduled_ordinals"][0]
                row = request["bindings"]["runtime"]["execution_request"]["cohort"]["samples"][ordinal]
                record = {**row, "status": status, "label": None, "attempts": 1, "native_calls": 1,
                    "hnlo": None, "hnlo_status": runtime.HNLO_STATUS}
                if status == "INVALID":
                    record["raw_sha256"] = "f"*64
                root = self.root/f"export-{number}"
                write(root/"handoff.json", request); write(root/"release.json", self.grant)
                write(root/"campaign-intent.json", intent)
                write(root/"run/summary.json", {"records": [record], "notice": "SYNTHETIC_CUSTODY_FIXTURE"})
                for kind, name in (("launch", "launch-claim.json"), ("worker", "environment/worker-claim.json"),
                        ("load", "run/load-claim.json"), (f"call-{ordinal:06d}", f"run/samples/{ordinal:06d}/call-claim.json")):
                    write(root/name, c.native_receipt(kind, request, intent, self.grant))
                archive = self.root/f"export-{number}.zip"; checksum = export(root, archive)
                p = request["plan"]
                h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": runtime.SERIES,
                    "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"],
                    "action": p["action"], "records": [record], "evidence_sha256": checksum, "repair": p["repair"]}
                history_by_sha[checksum] = h
                provider = {"state": "COMPLETE", "job_id": request["job"], "version": 1, "notebook_sha256": request["notebook_sha256"]}
                self.ledger.collect(request, archive, provider)
                if number == 1:
                    request = self.next_request([h])
                    self.assertEqual(request["execution_release"], self.request["execution_release"])
                    self.assertEqual(request["plan"]["scheduled_ordinals"], [1])
            result = self.ledger.summary()
            self.assertEqual(result["counts"], {"INVALID": 1, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3761})
            self.assertEqual(result["jobs"], 2)
            self.assertEqual(result["reserved_gpu_seconds"], 7200)
            self.assertFalse(result["blocked_open_intent"])
            self.assertFalse(result["pooling"])

    def test_caps_no_refund_pre_submit_failures_eventually_stop(self):
        # Ten planned single-call attempts exhaust the finite campaign. No new
        # Owner comment is made for a technical staging failure or continuation.
        for number in range(1, 11):
            request = self.request if number == 1 else self.next_request([], number)
            self.ledger.reserve(request)
            self.ledger.abort_pre_submit()
        self.assertEqual(self.ledger.summary()["jobs"], 10)
        with self.assertRaisesRegex(ValueError, "BUDGET_EXHAUSTED"):
            self.ledger.reserve(self.next_request([], 11))

    def test_shards_require_measured_source(self):
        self.ledger.reserve(self.request); self.ledger.abort_pre_submit()
        with self.assertRaisesRegex(ValueError, "MEASUREMENTS_REQUIRED"):
            self.ledger.reserve(self.next_request([], 2, calls=2))

    def test_repair_requires_the_reviewed_source_and_regression_receipt(self):
        request = deepcopy(self.request)
        execution = request["bindings"]["runtime"]["execution_request"]
        row = execution["cohort"]["samples"][0]
        failed = {**row, "status": "TECHNICAL_ERROR", "label": None, "attempts": 1, "native_calls": 1}
        h = {"run_id": "synthetic180-1", "attempt_id": "attempt-1", "series_id": runtime.SERIES, "identity": c.identity(),
            "cohort_sha256": digest(execution["cohort"]), "parent_history_sha256": digest([]), "action": "initial",
            "records": [failed], "evidence_sha256": "f"*64, "repair": None}
        repair = {"targets": {row["sample_id"]: digest(failed)}, "fix_sha256": "0"*64,
            "regression_sha256": "e"*64, "diagnosis": "SYNTHETIC transport diagnosis"}
        p = c.plan(execution["cohort"], [h], action="repair", run_id="synthetic180-2", attempt_id="attempt-2",
            max_calls=1, max_seconds=1800, repair=repair)
        execution.update(plan=p, history=[h], history_archives=[{"archive": "custody/prior.zip", "sha256": "f"*64,
            "plan": {"run_id": h["run_id"], "attempt_id": h["attempt_id"]}}])
        request.update(plan=p, plan_sha256=digest(p), job="nguynanhtn/safeshift-train3763-synthetic180-2")
        request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
        with self.assertRaisesRegex(ValueError, "REPAIR_REVIEWED"):
            c.bind(self.grant, request)

    def test_measured_shard_envelope_uses_sealed_latency_ram_gpu_and_raw_sizes(self):
        # Scripted telemetry tests resource arithmetic only. Native qualification
        # is deliberately a verifier seam here, never a fake inference claim.
        root = self.root/"telemetry-fixture"
        write(root/"setup/setup-supervisor.json", {"seconds": 10})
        write(root/"run/telemetry.json", {"evidence_kind": "NATIVE", "samples": [{"seconds": 2, "bytes": 1000}],
            "load_seconds": 5, "gpu_peak_allocated_bytes": 100, "gpu_peak_reserved_bytes": 200,
            "memory": {"errors": []}, "notice": "SYNTHETIC_RESOURCE_ARITHMETIC_ONLY"})
        (root/"run/scripted.f32").write_bytes(b"\x00"*16)
        archive = self.root/"telemetry-fixture.zip"; checksum = export(root, archive)
        with lock(self.ledger.root):
            self.ledger.append("COLLECTED", sha256=checksum, plan=self.request["plan"],
                provider={"state": "COMPLETE"}, verification={"status": "PASS", "scope": "SYNTHETIC_FIXTURE"})
        with patch.object(runtime, "verify_bundle", return_value={"status": "PASS", "scope": "SYNTHETIC_FIXTURE"}):
            measured = self.ledger.measure(archive, job_seconds=1800)
            self.assertEqual(measured["safe_calls"], 4)
            self.assertEqual(measured["minimum_seconds"], 166)
            self.assertEqual(measured["observed"]["raw_float32_bytes"], 16)
            self.assertEqual(measured["source_sha256"], digest(runtime.source_spec()))
            with self.assertRaisesRegex(ValueError, "TOO_SMALL"):
                self.ledger.measure(archive, job_seconds=120)


class CampaignLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cohort = synthetic_cohort()

    def attempt(self, history, action, number, *, response="invalid", fail=False, repair=None, calls=1):
        p = c.plan(self.cohort, history, action=action, run_id="synthetic-"+str(number), attempt_id="a-"+str(number),
            max_calls=calls, max_seconds=120, repair=repair)
        helper = controller_fixtures.PreparedControllerTests()
        backend = helper.backend(response, fail)
        def image(row):
            path = self.root/(str(number)+"-"+str(row["ordinal"]))
            path.write_bytes(synthetic_bytes(row["ordinal"]))
            return path
        archive = self.root/(str(number)+".zip")
        summary = runtime.rehearse(self.root/str(number), archive, self.cohort, p, history,
            lambda _: backend, image_path=image, tokenizer_sha="a"*64)
        return p, summary, runtime.sealed_history(archive, sha(archive), p)

    def test_resume_only_pending_repair_exact_errors_and_preserve_original_outcomes(self):
        p1, first, h1 = self.attempt([], "initial", 1)
        p2, second, h2 = self.attempt([h1], "resume", 2, fail=True)
        self.assertEqual(p2["scheduled_ordinals"], [1])
        targets = {h["records"][0]["sample_id"]: digest(h["records"][0]) for h in (h1, h2)}
        repair = {"targets": targets, "fix_sha256": digest(runtime.source_spec()), "regression_sha256": "e"*64,
            "diagnosis": "SYNTHETIC transport/storage regression, same science"}
        p3, third, h3 = self.attempt([h1, h2], "repair", 3, response='{"safety_level":"Level02"}', repair=repair, calls=2)
        self.assertEqual(p3["scheduled_ordinals"], [0, 1])
        self.assertEqual(first["records"][0]["status"], "INVALID")
        self.assertEqual(second["records"][1]["status"], "TECHNICAL_ERROR")
        self.assertEqual(third["counts"], {"SUCCESS": 2, "NOT_ATTEMPTED": 3761})
        p4 = c.plan(self.cohort, [h1, h2, h3], action="resume", run_id="r4", attempt_id="a4", max_calls=3, max_seconds=120)
        self.assertEqual(p4["scheduled_ordinals"], [2, 3, 4])
        self.assertEqual(p4["scientific_selection"], "PENDING")
        with self.assertRaises(ValueError):
            c.plan(self.cohort, [h1, h2, h3], action="repair", run_id="r5", attempt_id="a5", max_calls=1, max_seconds=120, repair=repair)

    def test_corrupt_zip_and_modified_sidecar_block_history(self):
        p, _, _ = self.attempt([], "initial", 1)
        path = self.root/"1.zip"
        original = path.read_bytes()
        path.write_bytes(original[:50])
        with self.assertRaises((ValueError, zipfile.BadZipFile)):
            runtime.sealed_history(path, sha(path), p)

    def test_wrong_cohort_or_foreign_series_not_imported(self):
        _, _, h = self.attempt([], "initial", 1)
        h["series_id"] = "legacy-qwen-recovery224"
        with self.assertRaises(ValueError):
            c.plan(self.cohort, [h], action="resume", run_id="r2", attempt_id="a2", max_calls=1, max_seconds=120)

    def test_reviewable_operational_source_revision_preserves_science_identity_and_history(self):
        _, _, h = self.attempt([], "initial", 1)
        changed = deepcopy(runtime.source_spec())
        changed["manifest"]["scripts/internvl3763.py"] = "0"*64
        before = c.identity()
        with patch.object(runtime, "source_spec", return_value=changed):
            self.assertEqual(c.identity(), before)
            p = c.plan(self.cohort, [h], action="resume", run_id="r2", attempt_id="a2", max_calls=1, max_seconds=120)
            self.assertEqual(p["scheduled_ordinals"], [1])
            self.assertEqual(p["runtime_source"], changed)


class CampaignStagingTests(unittest.TestCase):
    def test_frozen_science_and_checkpoint_match_exact_2484095_base(self):
        self.assertEqual(digest(c.science()), "ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50")
        locked = read(runtime.ROOT/"configs/cpu_g2_g3/checkpoint_metadata_lock.json")["internvl35"]
        evidence = read(runtime.ROOT/"docs/research/evidence/issue173/checkpoint-bytes-v1.json")["result"]["models"]["internvl35"]
        self.assertEqual(runtime.configuration()["model"], locked["id"])
        self.assertEqual(runtime.configuration()["revision"], locked["revision"])
        self.assertEqual(evidence["model"], {"id": locked["id"], "revision": locked["revision"]})
        for name, expected in locked["weights"].items():
            self.assertEqual(evidence["files"][name], {"sha256": expected["sha256"], "size_bytes": expected["size"]})

    def test_existing_original_mounts_reuse_issue173_verifier_without_new_image_bundle(self):
        from safeshift import verification173
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            master = root/"safeshift-pilot-input/master_manifest.json"
            write(master, {"notice": "SYNTHETIC_MASTER_ADAPTER_FIXTURE"})
            image_root = root/"inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH"
            image_root.mkdir(parents=True)
            cohort = synthetic_cohort()
            mapping = [{**row, "image_locator": f"DATA_PATH/train/Annotations/synthetic-{row['ordinal']:06d}.jpg"}
                for row in cohort["samples"]]
            receipt = {"status": "TRAIN_BYTES_PASS", "verified_images": 3763, "labels_exported": False}
            with patch.object(c, "MASTER_SHA", sha(master)), patch.object(verification173, "verify_train", return_value=(receipt, cohort, mapping)) as verifier:
                actual_root, actual, rows, checked = c.admit_inputs(root, sha(master), digest(cohort))
                verifier.assert_called_once_with(master, image_root)
                self.assertEqual(actual_root, image_root)
                self.assertEqual(actual, cohort)
                self.assertEqual(rows[0]["image"], "train/Annotations/synthetic-000000.jpg")
                self.assertEqual(checked["input_copy_bytes"], 0)
                self.assertFalse((root/"fresh_fulltrain_input.json").exists())
                self.assertNotIn("level", rows[0])
                self.assertNotIn("domain", rows[0])
                with self.assertRaisesRegex(ValueError, "ORIGINAL_3763"):
                    c.admit_inputs(root, sha(master), "0"*64)
                write(root/"another-master/master_manifest.json", {"notice": "DUPLICATE_SYNTHETIC_MASTER"})
                with self.assertRaisesRegex(ValueError, "FOUND_2"):
                    c.admit_inputs(root, sha(master), digest(cohort))

    def test_original_input_admission_rejects_wrong_master_before_image_bytes(self):
        from safeshift import verification173
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write(root/"safeshift-pilot-input/master_manifest.json", {"notice": "SYNTHETIC_WRONG_MASTER"})
            with patch.object(verification173, "verify_train", side_effect=AssertionError("NO_IMAGE_ACCESS")), \
                    self.assertRaisesRegex(ValueError, "ORIGINAL_EXISTING_MASTER"):
                c.admit_inputs(root, MASTER_SHA, "0"*64)

    def test_extracted_runtime_binds_campaign_without_repository_site_packages_or_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request, grant, comments = fixture(root/"ledger")
            extracted = root/"extracted"
            for name in runtime.source_spec()["manifest"]:
                destination = extracted/name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((runtime.ROOT/name).read_bytes())
            write(root/"fixture.json", {"request": request, "comments": comments})
            code = """import sys, json, socket, ssl
sys.path.insert(0,sys.argv[1])
socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('NO_NETWORK'))
from safeshift import internvl3763_campaign as c
value=json.load(open(sys.argv[2], encoding='utf8'))
reader=lambda path:value['comments'][path]
grant=c.load(value['request']['execution_release'],reader=reader)
c.bind(grant,value['request'],reader=reader)
print('PACKAGED_CAMPAIGN_BIND_PASS')
"""
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(extracted), str(root/"fixture.json")],
                cwd=extracted, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PACKAGED_CAMPAIGN_BIND_PASS", result.stdout)

    def test_actual_staging_entrypoint_builds_bounded_capsule_without_sdk_or_upload(self):
        from scripts.train3763_campaign import stage
        base = runtime.ROOT/"data/processed"
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic-stage-", dir=base) as temporary:
            root = Path(temporary)
            request, grant, comments = fixture(root/"ledger", actual_source=True)
            ledger = c.Ledger.create(root/"ledger", root/"mirror", grant, "synthetic-machine")
            context = {"technical_revision": request["bindings"]["runtime"]["technical_revision"],
                "execution_input": {"kind": "dataset_sources", "ref": "nguynanhtn/synthetic-capsule/1"}}
            with patch.object(old, "get", side_effect=lambda path: deepcopy(comments[path])), \
                    patch.object(op, "api", side_effect=AssertionError("NO_KAGGLE")):
                result = stage(ledger, request["execution_release"], context,
                    request["bindings"]["runtime"]["execution_request"]["cohort"],
                    directory=root/"handoff", calls=1, seconds=1800, action="initial")
            self.assertEqual(result["status"], "STAGED_NOT_SUBMITTED")
            package = read(root/"handoff/package/safeshift_train3763_execution.json")
            self.assertEqual(package["request"]["plan"]["scheduled_ordinals"], [0])
            self.assertEqual(len(package["request"]["plan"]["samples"]), 3763)
            self.assertEqual(package["campaign_intent"], ledger.open_intent())
            self.assertEqual(list((root/"handoff/package").iterdir()), [root/"handoff/package/safeshift_train3763_execution.json"])
            self.assertFalse(result["owner_reapproval_required"])


@unittest.skipUnless(os.environ.get("SAFESHIFT3763_SDK_CPU") == "1", "opt-in pinned official SDK CPU inventory")
class CampaignSdkTests(unittest.TestCase):
    def test_capsule_download_is_exact_private_version_and_stale_bytes_never_submit(self):
        from contextlib import nullcontext
        from safeshift.pilot.contract import json_bytes
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request, grant, _ = fixture(root/"ledger")
            intent = {"notice": "SYNTHETIC_INPUT_CUSTODY_ONLY", "request": request}
            raw = json_bytes({"request": request, "campaign_intent": intent})
            name = "safeshift_train3763_execution.json"
            metadata = NS(error_message="", info=NS(is_private=True, owner_user="nguynanhtn", dataset_slug="synthetic-capsule"))
            client = NS(build_kaggle_client=lambda: nullcontext(NS(datasets=NS(dataset_api_client=NS(get_dataset_metadata=lambda _: metadata)))),
                dataset_list_files=lambda *a, **k: NS(error_message="", next_page_token="", files=[NS(name=name, total_bytes=len(raw))]))
            downloaded = []
            def download(ref, file_name, **kwargs):
                downloaded.append((ref, file_name))
                (Path(kwargs["path"])/file_name).write_bytes(raw)
            def download_capsule(client, owner, slug, version, file_name, destination):
                return download(owner+"/"+slug+"/"+version, file_name, path=destination)
            with patch("socket.socket", side_effect=AssertionError("NO_KAGGLE_NETWORK")), \
                    patch.object(op, "download_capsule", side_effect=download_capsule):
                proof = op.verify_execution_input(client, request, intent, root/"good")
                self.assertEqual(proof["ref"], "nguynanhtn/synthetic-capsule/1")
                self.assertEqual(proof["sha256"], hashlib.sha256(raw).hexdigest())
                original = raw
                raw = raw.replace(b"synthetic180-1", b"synthetic180-0")  # same size, wrong durable intent
                with self.assertRaisesRegex(ValueError, "STALE_OR_WRONG"):
                    op.verify_execution_input(client, request, intent, root/"stale")
                raw = original
                metadata.info.is_private = False
                with self.assertRaisesRegex(ValueError, "PRIVATE_OWNER"):
                    op.verify_execution_input(client, request, intent, root/"public")
                self.assertEqual(len(downloaded), 2)

    def test_readonly_inventory_blocks_quota_active_job_and_orphan_after_rollback(self):
        from datetime import timedelta
        request, grant, _ = fixture(Path(tempfile.gettempdir())/"synthetic-campaign-sdk")
        quota = NS(time_used=timedelta(0), time_reserved=timedelta(0), total_time_allowed=timedelta(seconds=7200))
        owned = []
        client = NS(kernels_list_with_response=lambda **_: NS(kernels=[NS(ref=x) for x in owned], next_page_token=None),
            dataset_list_files=lambda *a, **k: NS(files=[NS(name="SYNTHETIC")]),
            quota_view=lambda: NS(gpu_quota=quota))
        effective = {"caps": {"attempt_gpu_seconds": 3600}, "predecessors": []}
        prefix = "nguynanhtn/safeshift-train3763-synthetic180-"
        with patch("socket.socket", side_effect=AssertionError("NO_KAGGLE_NETWORK")):
            self.assertEqual(op.inventory(client, request, effective, campaign_prefix=prefix, known_jobs=set())["quota"]["total"], 7200)
            quota.time_reserved = timedelta(seconds=1)
            with self.assertRaisesRegex(ValueError, "QUOTA"):
                op.inventory(client, request, effective, campaign_prefix=prefix, known_jobs=set())
            quota.time_reserved = timedelta(0); quota.total_time_allowed = timedelta(seconds=1)
            with self.assertRaisesRegex(ValueError, "QUOTA"):
                op.inventory(client, request, effective, campaign_prefix=prefix, known_jobs=set())
            quota.total_time_allowed = timedelta(seconds=7200)
            owned.append(prefix+"99")
            with self.assertRaisesRegex(ValueError, "ROLLBACK"):
                op.inventory(client, request, effective, campaign_prefix=prefix, known_jobs=set())


if __name__ == "__main__":
    unittest.main()
