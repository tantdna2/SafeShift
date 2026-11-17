"""Issue202 CPU synthetic custody. No real data/model/provider/key or authority.

RSA3072 signatures, controller/raw/C1/native markers, archives, history, mirrors
and final admission execute for real. Authority and native backend are explicit
synthetic boundaries. SDK tests mock transport, never declare provider success.
"""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import shutil
import socket
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import test_minicpm_fulltrain_execution as base
from test_fresh_fulltrain import Scripted
from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import contract, runtime as rt, minicpm_ui as ui, minicpm_release as a
from safeshift.fulltrain import minicpm_offline as p, minicpm_v5_incident as v5, minicpm_recovery as recovery
from safeshift.pilot.artifacts import read, write, export, sha
from safeshift.pilot.contract import digest
from scripts import minicpm_offline_continuation as c, owner_verify_minicpm_offline as online

REAL_LOAD, REAL_VALIDATE = a.load, a.validate


class FinalAdmissionIdentityTests(unittest.TestCase):
    """Synthetic GitHub responses; no signer/provider/model or authority issued."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.route=c.Continuation.__new__(c.Continuation)
        self.route.root=self.root/"primary";self.route.root.mkdir()
        self.route.mirror=self.root/"mirror";self.route.mirror.mkdir()
        self.route.grant={"offline":{"review_logins":["synthetic-reviewer"]}}
        self.route.registration={"locator":{"comment_id":1,"body_sha256":"a"*64}}
        self.manifest={"scope":"SYNTHETIC_FINAL_AUTH_ONLY"}
        self.report={"manifest_sha256":digest(self.manifest),"scope":"SYNTHETIC_PROVIDER_BOUNDARY"}
        self.exports={}
        self.owner=self.comment(101,p.FINAL,{"manifest_sha256":digest(self.manifest),"report_sha256":digest(self.report),
            "status":"APPROVED_FOR_FINAL_ADMISSION"},{"login":a.OWNER,"id":a.OWNER_ID})
        self.admission=self.comment(102,p.FINAL+"_ADMISSION",{"manifest_sha256":digest(self.manifest),
            "report_sha256":digest(self.report),"owner":self.owner,"status":"RELEASED_FOR_FINAL_ADMISSION"},
            {"login":"synthetic-reviewer","id":202000001})
        self.auth=patch.object(c,"authenticate",return_value=self.route.grant)
        self.auth.start();self.addCleanup(self.auth.stop)
        self.provider=patch.object(c,"validate_provider_report")
        self.provider_mock=self.provider.start();self.addCleanup(self.provider.stop)

    def comment(self,number,marker,payload,user):
        body=marker+"\n```json\n"+json.dumps(payload)+"\n```"
        self.exports["/issues/comments/"+str(number)]={"id":number,"issue_url":a.API+"/issues/202","body":body,"user":user}
        return {"comment_id":number,"body_sha256":hashlib.sha256(body.encode()).hexdigest()}

    def validate(self):
        return self.route.validate_final(self.manifest,self.report,self.exports,self.owner,self.admission)

    def test_independent_authorized_reviewer_passes_and_provider_still_validates(self):
        self.assertEqual(self.validate(),self.report)
        self.provider_mock.assert_called_once_with(self.manifest,self.report)

    def test_owner_different_comment_cannot_reconcile_or_enable_official_reader(self):
        self.exports["/issues/comments/102"]["user"]={"login":a.OWNER,"id":a.OWNER_ID}
        # Even an incorrectly broadened allowlist cannot bypass account checks.
        self.route.grant["offline"]["review_logins"].append(a.OWNER)
        with patch.object(self.route,"state",return_value={"final":None,"stopped":False}), \
             patch.object(self.route,"manifest",return_value=self.manifest),patch.object(self.route,"append") as append:
            with self.assertRaisesRegex(ValueError,"INDEPENDENT_FINAL_REVIEWER_ACCOUNT"):
                self.route.reconcile(self.report,self.exports,self.owner,self.admission)
            append.assert_not_called()
            self.assertFalse((self.route.root/"final").exists())
            with self.assertRaisesRegex(ValueError,"OFFICIAL_RESULTS_BLOCKED"):self.route.official_report()
        self.provider_mock.assert_not_called()

    def test_missing_invalid_or_owner_alias_account_identity_is_rejected(self):
        variants=[None,{}, {"login":"synthetic-reviewer"},{"id":202000001},
            {"login":"synthetic-reviewer","id":None},{"login":"synthetic-reviewer","id":True},
            {"login":"synthetic-reviewer","id":"202000001"},{"login":"synthetic-reviewer","id":0},
            {"login":"synthetic-reviewer","id":-1},{"login":"synthetic-reviewer","id":a.OWNER_ID},
            {"login":a.OWNER.upper(),"id":202000001},{"login":"unauthorized-reviewer","id":202000001}]
        for user in variants:
            with self.subTest(user=user):
                self.exports["/issues/comments/102"]["user"]=user
                with self.assertRaisesRegex(ValueError,"INDEPENDENT_FINAL_REVIEWER_ACCOUNT"):self.validate()
        del self.exports["/issues/comments/102"]["user"]
        with self.assertRaisesRegex(ValueError,"INDEPENDENT_FINAL_REVIEWER_ACCOUNT"):self.validate()

    def test_changed_body_comment_id_issue_or_locator_is_rejected(self):
        original=deepcopy(self.exports)
        for mutate in (lambda r:r.update(body=r["body"]+" changed"),lambda r:r.update(id=103),
                       lambda r:r.update(issue_url=a.API+"/issues/180")):
            self.exports=deepcopy(original);mutate(self.exports["/issues/comments/102"])
            with self.assertRaises(ValueError):self.validate()
        self.exports=original
        for locator in ({"comment_id":102},{"comment_id":True,"body_sha256":"a"*64},
                        {"comment_id":102,"body_sha256":"bad"}):
            with self.subTest(locator=locator),self.assertRaises(ValueError):
                self.route.validate_final(self.manifest,self.report,self.exports,self.owner,locator)

    def test_wrong_owner_and_rehashed_wrong_report_manifest_or_owner_binding_rejected(self):
        original=deepcopy(self.exports)
        for key,value in (("id",202000001),("login","synthetic-reviewer")):
            self.exports=deepcopy(original);self.exports["/issues/comments/101"]["user"][key]=value
            with self.assertRaises(ValueError):self.validate()
        self.exports=deepcopy(original)
        payload={"manifest_sha256":digest(self.manifest),"report_sha256":digest(self.report),
            "owner":self.owner,"status":"RELEASED_FOR_FINAL_ADMISSION"}
        for key,value in (("manifest_sha256","0"*64),("report_sha256","0"*64),
                          ("owner",{"comment_id":103,"body_sha256":"a"*64})):
            bad=deepcopy(payload);bad[key]=value
            self.admission=self.comment(102,p.FINAL+"_ADMISSION",bad,{"login":"synthetic-reviewer","id":202000001})
            with self.assertRaisesRegex(ValueError,"AUTHENTIC_FINAL_REVIEWER"):self.validate()

    def test_official_reader_revalidates_identity_even_with_consistent_final_hashes(self):
        self.exports["/issues/comments/102"]["user"]={"login":a.OWNER,"id":a.OWNER_ID}
        documents={"manifest":self.manifest,"report":self.report,"exports":self.exports}
        payload={"owner":self.owner,"admission":self.admission}
        for name,value in documents.items():
            for root in (self.route.root,self.route.mirror):write(root/"final"/(name+".json"),value)
            payload[name+"_sha256"]=digest(value)
        with patch.object(self.route,"state",return_value={"stopped":False,"final":{"payload":payload}}), \
             patch.object(self.route,"manifest",return_value=self.manifest):
            with self.assertRaisesRegex(ValueError,"INDEPENDENT_FINAL_REVIEWER_ACCOUNT"):self.route.official_report()


class OfflineTests(unittest.TestCase):
    setUpClass = classmethod(base.ExecutionTests.setUpClass.__func__)
    tearDownClass = classmethod(base.ExecutionTests.tearDownClass.__func__)
    make_ticket = base.ExecutionTests.make_ticket

    def setUp(self):
        base.ExecutionTests.setUp(self)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(c, "ROOT", self.root))
        self.stack.enter_context(patch.object(a, "CLAIMS", self.root / "claims"))
        self.grant.update(schema=a.RECOVERY_SCHEMA, authorization="OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY",
            implementation_pr=203, recovery={"journals": []}, repair={"schema": v5.SCHEMA, "journal_head_sha256": "f"*64})
        self.grant["caps"].update(total_calls=14163169, total_jobs=3766, total_gpu_seconds=108460800,
            job_calls=3763, job_seconds=14400)
        self.grant["sizing"] = {"export_seconds": 60, "first_call_seconds": 5, "safety_milli": 1000}
        self.grant["offline"] = {"schema": p.SCHEMA, "decision_issue": 202,
            "operator_session": "12345678-1234-1234-1234-123456789abc", "base_journal_head_sha256": "f"*64,
            "tools_sha256": digest(c.tools_manifest()), "tool_blobs": c.tool_blobs(), "unmeasured_calls": 2, "review_logins": ["synthetic-reviewer"]}
        self.stack.enter_context(patch.object(a, "load", return_value=self.grant))  # synthetic release boundary
        self.stack.enter_context(patch.object(a, "validate", side_effect=lambda grant, **_: grant))
        self.stack.enter_context(patch.object(c.old, "clean_source"))
        self.stack.enter_context(patch.object(rt, "validate_native_raw"))  # scripted adapter, not native logits
        self.stack.enter_context(patch("safeshift.fulltrain.memory.resource_check", return_value={"scope":"SYNTHETIC_ONLY"}))
        self.stack.enter_context(patch("scripts.generate_minicpm_fulltrain_notebook.notebook", side_effect=self.notebook))
        self.legacy = self.root / "data/processed/minicpm-v3-journal"; self.legacy.mkdir(parents=True)
        self.original = self.legacy / "event-00001.json"; write(self.original, {"synthetic": "unchanged"})
        self.base = {"files": c.snapshot_files([self.original]), "reserved": deepcopy(v5.RESERVED),
            "events": [], "v5_closure": {"disposition": "SYNTHETIC_PRE_NATIVE"}, "v5_directory": "data/processed/closure"}
        self.stack.enter_context(patch.object(c, "historical", return_value=self.base))
        self.route = c.Continuation.initialize(self.root / "data/processed/offline", self.root / "data/processed/mirror",
            self.locator, {}, self.value, self.root / "data/processed/closure", self.grant["offline"]["operator_session"])
        self.proof = self.root / "owner-proof.bin"; self.proof.write_bytes(b"SYNTHETIC OWNER UI PROOF - NOT PROVIDER EVIDENCE")

    def notebook(self, ref, *, capsule_sha256, release_locator, release_version):
        self.assertEqual(release_version, 7)
        return {"cells": [{"cell_type": "code", "source": ["# SYNTHETIC_BOOTSTRAP\n"]}],
            "metadata": {"safeshift": {"runtime_ref": ref, "source_sha256": self.grant["scope"]["source_sha256"],
                "capsule_sha256": capsule_sha256}}}

    def gate(self):
        serial = self.route.state()["reserved"]["jobs"] + 1
        name = self.grant["campaign_id"] + "-" + str(serial)
        inputs = deepcopy(self.value["input_sources"])
        inputs["dataset_sources"][-1] = "nguynanhtn/safeshift-minicpm-capsule-"+name+"/1"
        return {"observed_unix": int(time.time()), "quota": {"used": 0, "reserved": 0, "total": 1000000},
            "job": "nguynanhtn/safeshift-minicpm-"+name, "version": 1, "inputs": inputs,
            "no_active_job": True, "job_absent": True, "owner_checked": True, "proof_sha256": sha(self.proof)}

    def stage(self):
        return self.route.stage(self.key, self.gate(), self.proof)

    def outputs(self, *, invalid=True, before_call=None):
        state = self.route.state()
        active = state["active"]
        value, ticket = active["value"], active["ticket"]
        serial = ticket["payload"]["number"]
        r = value["request"]
        work, images = self.root / ("work-"+str(serial)), self.root / ("images-"+str(serial))
        images.mkdir()
        for i in r["plan"]["scheduled_ordinals"]:
            (images / f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        ui.restore_history(self.route.root / active["package"] / "dataset", value, work)
        class Backend(Scripted):
            def __init__(backend, outputs):
                super().__init__(outputs)
                backend.model = SimpleNamespace(generate=lambda image,sample: Scripted.generate(backend,image,sample))
            def generate(backend, image, sample):
                with redirect_stdout(io.StringIO()):
                    return backend.model.generate(image,sample)
        outputs = ['fenced INVALID' if invalid and n % 7 == 0 else '{"safety_level":"Level04"}'
            for n in r["plan"]["scheduled_ordinals"]]
        backend = Backend(outputs)
        def factory():
            contract.authorize("load")
            return backend
        with a._activated(self.grant, self.locator, ticket, value, "launch"): pass
        for stage in a.STAGES[1:-1]:
            with a._activated(self.grant, self.locator, ticket, value, stage, child=True): pass
        with a._activated(self.grant, self.locator, ticket, value, "native", child=True):
            result = rt._execute(work, images, value["cohort"], r["campaign"], r["plan"], r["history"], factory,
                image_path=lambda i: f"{i:06d}.bin", store_class=journal.BoundStore, before_call=before_call)
            claims = a.claims_snapshot()
        control = self.root / (f"{serial:032x}"); control.mkdir()
        write(control / "request.json", r)
        write(control / "capability.json", {"ticket": ticket})
        write(control / "claims.json", claims)
        write(control / "release.json", {"status": "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY",
            "source_sha256": r["source_sha256"], "diagnostic": False, "attempt_observed": True,
            "scientific_qualified": False, "failure": None, "last_stage": "native"})
        memory = {"status": "OBSERVED", "cgroup": {"memory.events": {"oom": 0, "oom_kill": 0}}}
        for mode in a.STAGES[1:]:
            write(control / (mode+"-process.json"), {"status": "EXITED", "returncode": 0, "group_exit": {"status": "NO_LIVE_MEMBERS"}})
            write(control / mode / "stage.json", {"status": "RETURNED", "stage": mode,
                "request_sha256": digest(r), "source_sha256": r["source_sha256"], "native_attempt_permitted": mode == "native"})
            for point in ("entry", "exit"): write(control / mode / ("stage-"+point+"-memory.json"), memory)
        write(control / "reclaim/owned-advice.json", {"scan_complete": True, "deleted_files": 0, "effect": "ADVISORY_NOT_RAM_PROOF"})
        write(control / "reclaim/post-advice-resources.json", {"memory": {"available_bytes": r["resource_policy"]["free_ram_mib"]*2**20}})
        write(control / "retention.json", {"status": "SEALED_ZIPS_IN_OUTPUT_RAW_BYTES_RETAINED_IN_SCRATCH", "raw_deleted": False,
            "retained": [{"run_id": h["run_id"], "archive_sha256": x["sha256"]} for h,x in zip(r["history"], value["ancestors"])]
                + [{"run_id": r["plan"]["run_id"], "archive_sha256": sha(str(result)+".zip")} ]})
        write(control / "final_timing.json", {"seconds_before_supervisor_export": time.time()-claims["launch.json"]["time_unix"],
            "export_reserve_seconds": self.grant["sizing"]["export_seconds"]})
        supervisor = Path(str(control)+".zip"); export(control, supervisor)
        attempt = Path(str(result)+".zip")
        receipt = {"job": value["job"], "version": 1, "kernel_id": serial, "state": "COMPLETE",
            "archive_sha256": sha(attempt), "supervisor_sha256": sha(supervisor), "owner_downloaded_unix": time.time(),
            "no_other_job_or_version": True, "no_api_submission": True, "proof_sha256": sha(self.proof)}
        return attempt, supervisor, receipt

    def accept(self):
        outputs = self.outputs()
        active = self.route.state()["active"]
        c.verify_local(self.grant,active,self.route.root/active["package"],*outputs,self.proof)
        try:
            return self.route.accept(*outputs, self.proof)
        except ValueError:
            for row in self.route.events():
                if row["kind"] == c.PROVISIONAL:
                    self.route.recheck(active,row["payload"])
            self.route.state(verify=False)
            raise

    def test_signed_offline_roundtrip_zero_refund_and_pending_resume(self):
        original = self.original.read_bytes()
        self.stage()
        first = self.route.state()["active"]
        self.assertEqual(first["ticket"]["payload"]["number"], 6)
        self.assertEqual(first["ticket"]["payload"]["reserved_before"], {"calls":10526,"jobs":5,"gpu_seconds":144000})
        with self.assertRaisesRegex(ValueError, "ACTIVE_STOP"): self.stage()
        accepted = self.accept()
        self.assertEqual(accepted["status"], c.PROVISIONAL)
        self.assertEqual(accepted["counts"], {"SUCCESS":1,"INVALID":1,"NOT_ATTEMPTED":3761})
        self.assertEqual(self.route.state()["next_ordinal"], 2)
        self.stage()
        active = self.route.state()["active"]
        self.assertEqual(active["value"]["request"]["plan"]["scheduled_ordinals"][0], 2)
        self.assertEqual(active["ticket"]["payload"]["number"], 7)
        self.assertEqual(self.original.read_bytes(), original)
        with self.assertRaisesRegex(ValueError, "OFFICIAL_RESULTS_BLOCKED"): self.route.official_report()

    def test_forged_expired_replayed_or_foreign_tickets_fail(self):
        self.stage()
        active = self.route.state()["active"]
        ticket = active["ticket"]
        for mutate in (lambda t: t.update(signature="0"*768), lambda t: t["payload"].update(number=5),
                       lambda t: t["payload"].update(grant_sha256="0"*64)):
            bad = deepcopy(ticket); mutate(bad)
            with self.assertRaises(ValueError): a.verify_ticket(self.grant, bad, active["value"])
        with patch.object(p.time, "time", return_value=self.grant["expires_unix"]+1):
            with self.assertRaisesRegex(ValueError, "TICKET_EXPIRED"): a.verify_ticket(self.grant, ticket, active["value"])
        with a._activated(self.grant,self.locator,ticket,active["value"],"launch"): pass
        with self.assertRaises(FileExistsError):
            with a._activated(self.grant,self.locator,ticket,active["value"],"launch"): pass

    def test_owner_quota_input_proof_and_session_fail_closed(self):
        for change in (lambda g:g["quota"].update(reserved=1), lambda g:g.update(observed_unix=1),
                       lambda g:g.update(no_active_job=False), lambda g:g.update(version=2),
                       lambda g:g["inputs"]["dataset_sources"].pop(), lambda g:g.update(proof_sha256="0"*64)):
            gate = self.gate(); change(gate)
            with self.assertRaises(ValueError): self.route.stage(self.key, gate, self.proof)
        self.assertEqual(self.route.events(), [])
        bad = deepcopy(self.grant); bad["offline"]["operator_session"] = p.EXCLUDED_SESSION
        with self.assertRaisesRegex(ValueError,"ORIGINAL_OPERATOR_SESSION"): p.validate_delegation(bad)
        bad = deepcopy(self.grant); bad["offline"]["unmeasured_calls"] = 3763
        with self.assertRaisesRegex(ValueError,"CONSERVATIVE_INITIAL"): p.validate_delegation(bad)
        for logins in ([a.OWNER],[a.OWNER.upper()],["synthetic-reviewer",a.OWNER],
                       ["synthetic-reviewer","SYNTHETIC-REVIEWER"],[None],[]):
            bad=deepcopy(self.grant);bad["offline"]["review_logins"]=logins
            with self.subTest(logins=logins),self.assertRaisesRegex(ValueError,"FINAL_REVIEWERS_REQUIRED"):
                p.validate_delegation(bad)

    def test_crash_after_reservation_exports_same_ticket_without_new_budget(self):
        with patch.object(self.route,"export_active",side_effect=RuntimeError("SYNTHETIC_CRASH")):
            with self.assertRaises(RuntimeError): self.stage()
        before = self.route.state()["reserved"]
        result = self.route.export_active()
        self.assertIn("NOT_SUBMITTED",result["status"])
        self.route.export_active()
        self.assertEqual(self.route.state()["reserved"], before)
        pkg = self.route.root/self.route.state()["active"]["package"]
        (pkg/"notebook.ipynb").write_bytes(b"SYNTHETIC_TORN")
        with self.assertRaisesRegex(ValueError,"PARTIAL_OR_CHANGED"):self.route.export_active()

    def test_mirror_partial_original_append_and_os_lock_stop(self):
        with c.lock(self.route.root):
            with self.assertRaisesRegex(RuntimeError,"ANOTHER_OPERATOR"): self.stage()
        self.stage()
        (self.route.mirror/"event-000001.json").unlink()
        with self.assertRaisesRegex(ValueError,"TORN_MIRROR"): self.route.state()
        write(self.legacy/"event-00002.json",{"synthetic":"unexpected"})
        with self.assertRaisesRegex(ValueError,"LEGACY_APPEND"): self.route.events()

    def test_missing_bad_sidecar_terminal_or_native_raw_preserved_and_stopped(self):
        self.stage()
        attempt, supervisor, receipt = self.outputs()
        Path(str(attempt)+".sha256.json").write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError,"ACCEPT_STOPPED"):
            self.route.accept(attempt,supervisor,receipt,self.proof)
        state = self.route.state()
        self.assertTrue(state["stopped"])
        self.assertIsNotNone(state["active"])
        self.assertTrue((self.route.root/"custody/6"/attempt.name).exists())
        with self.assertRaisesRegex(ValueError,"ACTIVE_STOP"): self.stage()
        with self.assertRaisesRegex(ValueError,"OFFICIAL_RESULTS_BLOCKED"): self.route.official_report()

    def test_wrong_terminal_version_foreign_job_and_missing_proof(self):
        self.stage()
        active = self.route.state()["active"]
        attempt, supervisor, receipt = self.outputs()
        for field,value in (("version",2),("state","RUNNING"),("job","foreign/job"),("no_other_job_or_version",False)):
            bad = deepcopy(receipt);bad[field]=value
            with self.assertRaisesRegex(ValueError,"TERMINAL_HASH_VERSION"):
                c.verify_local(self.grant,active,self.route.root/active["package"],attempt,supervisor,bad,self.proof)
        with self.assertRaises(FileNotFoundError):
            c.verify_local(self.grant,active,self.route.root/active["package"],attempt,supervisor,receipt,self.root/"missing")

    def test_signed_budget_reset_cap_exhaustion_and_peer_timing_rejected(self):
        gate = self.gate()
        for reserved in ({"calls":14163169,"jobs":5,"gpu_seconds":144000}, {"calls":10526,"jobs":3766,"gpu_seconds":144000}):
            with self.assertRaises(ValueError): p.proposal(self.grant,3763,reserved,gate)
        telemetry = {"model_key":"internvl35","source_sha256":self.grant["scope"]["source_sha256"],
            "overhead_seconds":2192,"call_seconds":[13.42],"provenance_sha256":"f"*64}
        with self.assertRaisesRegex(ValueError,"NO_PEER_THROUGHPUT"): p.proposal(self.grant,3763,v5.RESERVED,gate,telemetry)
        self.stage();active = self.route.state()["active"]
        bad = deepcopy(active["ticket"]["payload"]);bad["reserved_before"]["calls"]-=1
        signed = c.old.sign(self.key,self.public,bad)
        with self.assertRaisesRegex(ValueError,"NO_HOLD_RESET"):a.verify_ticket(self.grant,signed,active["value"])
        value=deepcopy(active["value"]);r=value["request"];plan=r["plan"]
        r["plan"]=contract.plan(r["campaign"],value["cohort"],plan["identity"],[],action="initial",
            run_id=plan["run_id"],attempt_id=plan["attempt_id"],max_calls=3,max_seconds=plan["max_seconds"])
        payload=deepcopy(active["ticket"]["payload"])
        payload.update(value_sha256=digest(value),capsule_sha256=digest(value))
        payload["sizing"]["calls"]=3;payload["reserved_after"]["calls"]=payload["reserved_before"]["calls"]+3
        signed=c.old.sign(self.key,self.public,payload)
        with self.assertRaisesRegex(ValueError,"UNMEASURED_RELEASE_CAP"):a.verify_ticket(self.grant,signed,value)

    def test_source_tools_drift_and_owner_network_boundary(self):
        self.grant["offline"]["tools_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"REVIEWED_OFFLINE_TOOLS"): c.authenticate(self.locator,{})
        with self.assertRaisesRegex(ValueError,"OWNER_MUST_PERSONALLY"): online.verify(self.route,self.root/"data/processed/provider")
        with self.assertRaisesRegex(ValueError,"OWNER_MUST_PERSONALLY"): online.acquire(self.locator,self.root/"data/processed/export")
        with self.assertRaisesRegex(ValueError,"MISSING_AUTHENTIC"): c.Exports({})("/pulls/203")

    def test_new_marker_exact_source_approvals_and_tool_tree_are_mandatory(self):
        exports = {}
        def add(i,marker,payload):
            body=marker+"\n```json\n"+json.dumps(payload)+"\n```"
            exports["/issues/comments/"+str(i)]={"id":i,"issue_url":a.API+"/issues/203","body":body,
                "user":{"login":a.OWNER,"id":a.OWNER_ID}}
            return {"comment_id":i,"body_sha256":hashlib.sha256(body.encode()).hexdigest()}
        self.grant["approvals"]={role:None for role in recovery.SOURCE_ROLES}
        for i,role in enumerate(recovery.SOURCE_ROLES,2):
            self.grant["approvals"][role]=add(i,a.APPROVAL,{"kind":role,"status":"APPROVED",
                "reviewed_head":self.grant["reviewed_head"],"subject_sha256":a.subject(self.grant)})
        locator=add(1,p.RELEASE,self.grant)
        exports["/pulls/203"]={"merged":True,"draft":False,"base":{"ref":"main"},
            "head":{"sha":self.grant["reviewed_head"]},"merge_commit_sha":self.grant["merged_sha"]}
        rows=[]
        repo=ui.ROOT
        for name in [*contract.sources(), *("scripts/"+name for name in p.TOOLS)]:
            raw=(repo/name).read_bytes()
            rows.append({"path":name,"type":"blob","mode":"100644","sha":hashlib.sha1(
                b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()})
        for ref in (self.grant["runtime_commit"],self.grant["reviewed_head"],self.grant["merged_sha"]):
            exports["/git/trees/"+ref+"?recursive=1"]={"tree":deepcopy(rows),"truncated":False}
        # Inherited V4/V5 contracts have separate real-signature regression
        # modules. Here only that historical graph is a synthetic boundary.
        with patch.object(a,"validate",side_effect=REAL_VALIDATE), \
             patch.object(recovery,"validate_recovery"), patch.object(recovery,"authenticate_recovery"), \
             patch.object(v5,"validate_repair"), patch.object(v5,"authenticate_repair"):
            self.assertEqual(REAL_LOAD(locator,reader=c.Exports(exports)),self.grant)
            # Kaggle embeds runtime sources, not local Operator scripts. The
            # signed root's blob IDs still verify those tools on GitHub.
            runtime_repo=self.root/"runtime-only"
            for name in contract.sources():
                target=runtime_repo/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(repo/name,target)
            self.assertFalse((runtime_repo/"scripts").exists())
            self.assertEqual(REAL_LOAD(locator,reader=c.Exports(exports),repo=runtime_repo),self.grant)
            bad=deepcopy(exports);bad["/pulls/203"]["merged"]=False
            with self.assertRaisesRegex(ValueError,"REVIEW_AUDIT_MERGE"):REAL_LOAD(locator,reader=c.Exports(bad))
            bad=deepcopy(exports)
            tree=bad["/git/trees/"+self.grant["merged_sha"]+"?recursive=1"]["tree"]
            tree[-1]["sha"]="0"*40
            with self.assertRaisesRegex(ValueError,"MERGED_RUNTIME_BYTES"):REAL_LOAD(locator,reader=c.Exports(bad))
            bad=deepcopy(exports);bad["/issues/comments/1"]["user"]["id"]=3
            with self.assertRaisesRegex(ValueError,"AUTHENTIC_OWNER"):REAL_LOAD(locator,reader=c.Exports(bad))
            bad=deepcopy(exports)
            modified=deepcopy(self.grant);modified["offline"]["review_logins"]=["unapproved-reviewer"]
            body=p.RELEASE+"\n```json\n"+json.dumps(modified)+"\n```"
            bad["/issues/comments/1"]["body"]=body
            changed_locator={"comment_id":1,"body_sha256":hashlib.sha256(body.encode()).hexdigest()}
            with self.assertRaisesRegex(ValueError,"APPROVAL_SOURCE_SCOPE"):REAL_LOAD(changed_locator,reader=c.Exports(bad))

    def test_native_claim_raw_mutation_and_missing_capsule_never_become_results(self):
        from safeshift.pilot.artifacts import import_archive
        self.stage(); active=self.route.state()["active"]
        attempt,supervisor,receipt=self.outputs()
        pkg=self.route.root/active["package"]
        marker=pkg/"dataset"/ui.MARKER
        saved=marker.read_bytes();marker.write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError,"CAPSULE_VALUE"):c.verify_local(self.grant,active,pkg,attempt,supervisor,receipt,self.proof)
        marker.write_bytes(saved)
        staged=import_archive(attempt,self.root/"mutated-attempt")
        raw=staged/"calls/000000/run/samples/000000/raw.json"
        value=read(raw);value["response"]='{"safety_level":"Level01"}';raw.write_bytes(c.json_bytes(value))
        (staged/"checksums.json").unlink(missing_ok=True)
        altered=self.root/"altered"/attempt.name;altered.parent.mkdir()
        export(staged,altered)
        receipt["archive_sha256"]=sha(altered)
        with self.assertRaises(ValueError):c.verify_local(self.grant,active,pkg,altered,supervisor,receipt,self.proof)

    def test_missing_output_stops_and_legacy_writer_is_fenced(self):
        self.stage()
        before=self.route.state()["reserved"]
        with self.assertRaisesRegex(ValueError,"LEGACY_WRITER_BLOCKED"):
            c.old.Journal(self.legacy,self.root/"data/processed/old-mirror").append("COLLECTED",{})
        with self.assertRaisesRegex(ValueError,"ACCEPT_STOPPED"):
            self.route.accept(self.root/"missing.zip",self.root/"supervisor.zip",{},self.proof)
        self.assertEqual(self.route.state()["reserved"],before)
        self.assertTrue(self.route.state()["stopped"])

    def test_every_capsule_byte_including_zip_ancestor_is_checked(self):
        from safeshift import internvl3763_operator as provider
        self.stage();active=self.route.state()["active"]
        pkg=self.route.root/active["package"]
        ziproot=self.root/"small-zip";ziproot.mkdir();write(ziproot/"synthetic.json",{"synthetic":True})
        ancestor=pkg/"dataset/ancestor-0000.bin";export(ziproot,ancestor)
        value=deepcopy(active["value"])
        value["ancestors"].append({"file":ancestor.name,"sha256":sha(ancestor),"plan_sha256":"a"*64})
        ticket=deepcopy(active["ticket"]);ticket["payload"]["value_sha256"]=digest(value)
        (pkg/"dataset"/ui.MARKER).write_bytes(c.json_bytes(value))
        from safeshift.fulltrain.minicpm_execution import MARKER
        (pkg/"dataset"/MARKER).write_bytes(c.json_bytes(ticket))
        requested=[]
        def download(client,owner,slug,version,name,destination):
            requested.append(name);target=destination/name
            c.copy(pkg/"dataset"/name,target)
            return target
        with patch.object(c.old,"verify_published_capsule",return_value={"synthetic":True}), \
             patch.object(provider,"download_capsule",side_effect=download):
            result=online.capsule(Mock(),value,ticket,pkg,self.root/"downloaded-capsule")
        self.assertEqual(set(requested),{f.name for f in (pkg/"dataset").iterdir()})
        self.assertEqual(result["files"][ancestor.name],sha(ancestor))

    def test_owner_verifier_network_failure_preserves_blocked_without_journal_write(self):
        before=self.route.events()
        with patch.object(a,"github_get",side_effect=OSError("https://private/signed-url")), \
             patch.object(a,"load",side_effect=REAL_LOAD):
            with self.assertRaisesRegex(ValueError,"VERIFIER_BLOCKED"):online.acquire(
                self.locator,self.root/"data/processed/failed-export",owner_performs_network=True)
        blocked=read(self.root/"data/processed/failed-export/BLOCKED.json")
        self.assertNotIn("private",json.dumps(blocked))
        self.assertEqual(self.route.events(),before)

    @unittest.skipUnless(sys.platform == "linux", "3763 real scripted archive/mirror path run on POSIX Linux")
    def test_all3763_multiple_jobs_tail_mock_provider_and_single_final_admission(self):
        # Each distinct ZIP pair is replayed through the actual verifier once.
        # Repeated state inspections in this large CPU fixture recheck outer
        # hashes and reuse that exact result to avoid redundant fsync/extraction
        # of tens of thousands of tiny synthetic files. Production has no cache.
        real_verify, verified_cache = c.verify_local, {}
        def verified_once(grant,active,package,attempt,supervisor,receipt,proof):
            key=(digest(grant),digest(active["value"]),digest(active["ticket"]),sha(attempt),sha(str(attempt)+".sha256.json"),sha(supervisor),
                sha(str(supervisor)+".sha256.json"),digest(receipt),sha(proof),sha(package/"notebook.ipynb"),
                sha(package/"dataset"/ui.MARKER))
            if key not in verified_cache:
                verified_cache[key]=real_verify(grant,active,package,attempt,supervisor,receipt,proof)
            return deepcopy(verified_cache[key])
        self.stack.enter_context(patch.object(c,"verify_local",side_effect=verified_once))
        self.grant["offline"]["unmeasured_calls"] = 1000
        # Registration binds the grant; fixture changes happen only before this
        # synthetic release is initialized, never in a running campaign.
        for root in (self.route.root,self.route.mirror):
            reg = read(root/"registration.json");reg["grant_sha256"]=digest(self.grant)
            (root/"registration.json").write_bytes(c.json_bytes(reg))
        self.route.registration=reg
        c.fence().write_bytes(c.json_bytes({"root":c.relative(self.route.root),"registration_sha256":digest(reg)}))
        self.stage(); self.accept()
        self.assertEqual(self.route.state()["next_ordinal"],1000)
        self.stage()
        tail=self.route.state()["active"]["value"]["request"]["plan"]["scheduled_ordinals"]
        self.assertEqual(tail,list(range(1000,3763)))
        self.accept()
        manifest=self.route.manifest()
        self.assertEqual([r["ordinal"] for r in manifest["rows"]],list(range(3763)))
        self.assertEqual(len(manifest["attempts"]),2)
        self.assertEqual(manifest["reserved"]["calls"],10526+3763)
        self.exercise_final(manifest)

    def exercise_final(self,manifest):
        """Mock SDK at transport boundaries; orchestration visits every job."""
        from scripts import reconcile_train3763_manual as manual
        sdk=Mock(name="SYNTHETIC_OFFICIAL_SDK")
        observations=[]
        def observe(client,job,version,nb,sources,**kw):
            self.assertIs(client,sdk); self.assertEqual(version,1)
            item=next(i for i in manifest["attempts"] if i["value"]["job"]==job)
            self.assertEqual(sources,item["value"]["input_sources"])
            observations.append(job)
            return {"job_id":job,"version":1,"state":"COMPLETE","kernel_id":kw["kernel_id"],
                "notebook_code_sha256":item["ticket"]["payload"]["notebook_code_sha256"],"safeshift_metadata":"MATCHED"}
        def download(client,job,version,attempt,checksum,destination,*,output_pairs):
            for name,source in output_pairs.items():
                c.copy(source,destination/name)
                c.copy(Path(str(source)+".sha256.json"),Path(str(destination/name)+".sha256.json"))
            return {"mock_sdk":"EXACT_SYNTHETIC_BYTES"}
        with patch.object(online,"historical",return_value={"status":"ALL_HISTORICAL_CUSTODY_RECHECKED",
                "historical_sha256":digest(manifest["historical"])}), \
             patch.object(online,"capsule",return_value={"mock_sdk":"CAPSULE_CHECKED"}), \
             patch.object(manual,"observe_kernel",side_effect=observe), \
             patch.object(manual,"download_outputs",side_effect=download):
            report=online.verify(self.route,self.root/"data/processed/provider",owner_performs_network=True,client=sdk)
        self.assertEqual(len(observations),2*len(manifest["attempts"]))
        for mutate in (lambda r:r["attempts"].pop(), lambda r:r["attempts"][0]["provider"].update(version=2),
                       lambda r:r["attempts"][0]["provider"].update(job_id="foreign/job"),
                       lambda r:r["attempts"][1]["provider"].update(kernel_id=6)):
            bad=deepcopy(report);mutate(bad)
            with self.assertRaises(ValueError):c.validate_provider_report(manifest,bad)
        exports={}
        def comment(i,marker,payload,*,user):
            body=marker+"\n```json\n"+json.dumps(payload)+"\n```"
            exports["/issues/comments/"+str(i)]={"id":i,"issue_url":a.API+"/issues/202","body":body,
                "user":user}
            return {"comment_id":i,"body_sha256":hashlib.sha256(body.encode()).hexdigest()}
        owner=comment(101,p.FINAL,{"manifest_sha256":digest(manifest),"report_sha256":digest(report),"status":"APPROVED_FOR_FINAL_ADMISSION"},
            user={"login":a.OWNER,"id":a.OWNER_ID})
        admission=comment(102,p.FINAL+"_ADMISSION",{"manifest_sha256":digest(manifest),"report_sha256":digest(report),
            "owner":owner,"status":"RELEASED_FOR_FINAL_ADMISSION"},user={"login":"synthetic-reviewer","id":202000001})
        self_review=deepcopy(exports)
        self_review["/issues/comments/102"]["user"]={"login":a.OWNER,"id":a.OWNER_ID}
        with self.assertRaisesRegex(ValueError,"INDEPENDENT_FINAL_REVIEWER_ACCOUNT"):
            self.route.reconcile(report,self_review,owner,admission)
        self.assertIsNone(self.route.state()["final"])
        with self.assertRaisesRegex(ValueError,"OFFICIAL_RESULTS_BLOCKED"):self.route.official_report()
        self.route.reconcile(report,exports,owner,admission)
        self.assertEqual(self.route.state()["status"],"FINAL_EVENT_PRESENT_USE_OFFICIAL_REPORT")
        official=self.route.official_report()
        self.assertEqual(official["status"],"OFFICIAL_RECONCILED_RESULTS")
        self.assertEqual(len(official["rows"]),3763)
        self.assertFalse(official["scientific_qualified"])
        self.assertEqual(official["budget"]["billing_gpu_seconds"],"NOT_OBSERVED")
        self.assertNotIn("manifest",self.route.state()["final"]["payload"])
        with self.assertRaisesRegex(ValueError,"DUPLICATE_FINAL"):self.route.reconcile(report,exports,owner,admission)
        with (self.route.mirror/"final/manifest.json").open("ab") as file:file.write(b" ")
        with self.assertRaisesRegex(ValueError,"FINAL_DOCUMENT_BYTES"):self.route.official_report()


if __name__ == "__main__": unittest.main()
