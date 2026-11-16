"""Synthetic signed-release/controller/serial custody; zero provider/model IO."""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace as NS
from contextlib import ExitStack

from safeshift.candidates import fulltrain_run as journal
from safeshift.fulltrain import contract, minicpm_release as a, minicpm_sizing as sizing, runtime as rt
from safeshift.fulltrain import minicpm_ui as ui
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import digest
from scripts import minicpm_fulltrain_operator as op
from test_fresh_fulltrain import Scripted
from test_fresh_fulltrain_revision import budgets


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("openssl"):
            raise unittest.SkipTest("OpenSSL signing fixture unavailable; runtime RSA verifier itself is stdlib")
        cls.keys = tempfile.TemporaryDirectory()
        cls.key = Path(cls.keys.name) / "synthetic-private.pem"
        result = subprocess.run(["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072",
            "-out", str(cls.key)], capture_output=True, timeout=30)
        assert result.returncode == 0
        modulus = subprocess.check_output(["openssl", "rsa", "-in", str(cls.key), "-noout", "-modulus"], stderr=subprocess.DEVNULL)
        cls.public = {"n_hex": modulus.decode().strip().split("=")[1].lower(), "e": 65537}

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "keys"): cls.keys.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.operator_root = patch.object(op,"ROOT",self.root)
        self.operator_root.start();self.addCleanup(self.operator_root.stop)
        self.cohort = journal.synthetic_cohort()
        # Still entirely synthetic bytes, but exercise production binding schema.
        # This is a mocked authority/adapter fixture, never a real private grant.
        self.cohort["scope"] = "PRIVATE_TRAIN_METADATA"
        self.value = ui.initial(self.cohort, digest(self.cohort), budgets(), checkpoint_marker_sha256="b"*64,
            run_id="synthetic-run", attempt_id="synthetic-attempt", job="nguynanhtn/safeshift-minicpm-synthetic-1",
            capsule_ref="nguynanhtn/safeshift-minicpm-capsule-synthetic-1/1", max_calls=3, max_seconds=600, nested_mounts=False)
        now = int(time.time())
        self.grant = {"schema": a.SCHEMA, "authorization": "OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY",
            "campaign_id": "synthetic", "implementation_pr": 198, "runtime_commit": "c"*40,
            "reviewed_head": "a"*40, "merged_sha": "b"*40, "scope": a.scope(self.value),
            "public_key": self.public, "operator_host_sha256": op.host(),
            "caps": {"total_calls": 5000, "total_jobs": 100, "total_gpu_seconds": 1000000,
                "job_calls": 3763, "job_seconds": 7200, "physical_gpus": 2, "loads_per_job": 1, "archive_bytes": 2**30},
            "sizing": {"export_seconds": 30, "first_call_seconds": 10, "safety_milli": 2000},
            "issued_unix": now-100, "expires_unix": now+86400, "provider_max_age_seconds": 1800,
            "approvals": {k: None for k in a.ROLES}}
        self.locator = {"comment_id": 1, "body_sha256": "f"*64}
        self.provider = {"observed_unix": now, "quota": {"used": 0, "reserved": 0, "total": 100000},
            "input_versions": {ref: {"ref": ref, "version": 1, "private": True} for ref in
                [*self.value["input_sources"]["dataset_sources"][:-1], *self.value["input_sources"]["kernel_sources"]]},
            "prior_jobs": [], "job_absent": True, "owned_sha256": "d"*64}
        self.ticket = self.make_ticket(self.value)
        self.network = patch.object(socket.socket, "connect", side_effect=AssertionError("NETWORK_FORBIDDEN"))
        self.network.start(); self.addCleanup(self.network.stop)

    def make_ticket(self, value, number=1, before=None):
        before = before or {"calls": 0, "jobs": 0, "gpu_seconds": 0}
        p = value["request"]["plan"]
        provider = deepcopy(self.provider)
        provider["prior_jobs"] = [{"job": "nguynanhtn/safeshift-minicpm-synthetic-"+str(i), "version":1,
            "state":"COMPLETE", "kernel_id":i} for i in range(1,number)]
        payload = {"schema": a.TICKET, "grant_sha256": digest(self.grant), "value_sha256": digest(value),
            "capsule_sha256": digest(value), "notebook_code_sha256": "e"*64, "number": number,
            "previous_event_sha256": "0"*64, "reserved_before": before,
            "reserved_after": {"calls": before["calls"]+p["max_calls"], "jobs": before["jobs"]+1,
                "gpu_seconds": before["gpu_seconds"]+2*p["max_seconds"]},
            "issued_unix": int(time.time()), "start_before_unix": provider["observed_unix"]+1800,
            "provider": provider, "sizing": {"calls":p["max_calls"],"seconds":p["max_seconds"]}}
        return op.sign(self.key, self.public, payload)

    def fake_graph(self):
        exports = {"/pulls/198": {"merged": True, "draft":False, "base":{"ref":"main"},
            "head":{"sha":self.grant["reviewed_head"]}, "merge_commit_sha": self.grant["merged_sha"]}}
        def add(i, marker, payload):
            body = marker+"\n```json\n"+json.dumps(payload)+"\n```"
            exports["/issues/comments/"+str(i)] = {"id":i,"issue_url":a.API+"/issues/198",
                "user":{"id":a.OWNER_ID,"login":a.OWNER},"body":body}
            return {"comment_id":i,"body_sha256":hashlib.sha256(body.encode()).hexdigest()}
        for i, role in enumerate(a.ROLES,2):
            self.grant["approvals"][role] = add(i,a.APPROVAL,{"kind":role,"status":"APPROVED",
                "reviewed_head":self.grant["reviewed_head"],"subject_sha256":a.subject(self.grant)})
        loc = add(1,a.MARKER,self.grant)
        rows=[]
        for name in contract.sources():
            raw=(ui.ROOT/name).read_bytes()
            rows.append({"path":name,"type":"blob","mode":"100644",
                "sha":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()})
        for ref in ("a"*40,"b"*40,"c"*40):
            exports["/git/trees/"+ref+"?recursive=1"]={"truncated":False,"tree":deepcopy(rows)}
        return loc,exports

    def test_real_rsa_roundtrip_and_tamper_bad_padding_wrong_key(self):
        self.assertEqual(op.public_from_private(self.key),self.public)
        a.verify_ticket(self.grant,self.ticket,self.value)
        for change in (lambda t:t["payload"].update(number=2), lambda t:t.update(signature="0"*768),
                       lambda t:t.update(signature="f"*768)):
            bad=deepcopy(self.ticket); change(bad)
            with self.subTest(change=change),self.assertRaises(ValueError): a.verify_ticket(self.grant,bad,self.value)
        bad=deepcopy(self.public); bad["e"]=3
        with self.assertRaises(ValueError): a.verify_signature(bad,self.ticket["payload"],self.ticket["signature"])

    def test_live_authority_graph_and_all_reviewed_tree_bytes(self):
        locator,graph=self.fake_graph()
        self.assertEqual(a.load(locator,reader=graph.__getitem__),self.grant)
        for ref in ("a"*40,"b"*40,"c"*40):
            bad=deepcopy(graph); bad["/git/trees/"+ref+"?recursive=1"]["tree"][0]["sha"]="f"*40
            with self.subTest(ref=ref),self.assertRaisesRegex(ValueError,"MERGED_RUNTIME_BYTES"):
                a.load(locator,reader=bad.__getitem__)
        bad=deepcopy(graph); bad["/issues/comments/1"]["user"]["id"]=2
        with self.assertRaisesRegex(ValueError,"AUTHENTIC_OWNER"):a.load(locator,reader=bad.__getitem__)
        bad=deepcopy(graph); bad["/pulls/198"]["merged"]=False
        with self.assertRaisesRegex(ValueError,"REVIEW_AUDIT_MERGE"):a.load(locator,reader=bad.__getitem__)

    def test_unsigned_grants_flags_and_inactive_entrypoints_remain_closed(self):
        with self.assertRaises(PermissionError): contract.authorize(approved=True)
        class Poison:
            def __fspath__(self):raise AssertionError("PRIVATE_IO")
        from safeshift.fulltrain.minicpm_execution import run_capsule
        with patch.object(a,"load",side_effect=PermissionError("MISSING_REAL_RELEASE")):
            with self.assertRaisesRegex(PermissionError,"MISSING_REAL_RELEASE"):run_capsule(Poison(),"f"*64,self.locator)

    def test_signed_ticket_caps_quota_deadline_synthetic_and_source_drift(self):
        for mutate in (lambda t:t["reserved_after"].update(calls=5001),
                       lambda t:t["provider"]["quota"].update(reserved=1),
                       lambda t:t["provider"]["input_versions"].pop(ui.TRAIN),
                       lambda t:t.update(start_before_unix=t["issued_unix"]-1)):
            payload=deepcopy(self.ticket["payload"]);mutate(payload)
            signed=op.sign(self.key,self.public,payload)
            with self.subTest(mutate=mutate),self.assertRaises(ValueError):a.verify_ticket(self.grant,signed,self.value)
        changed=deepcopy(self.value);changed["request"]["source_sha256"]="f"*64
        with self.assertRaises(ValueError):a.verify_ticket(self.grant,self.ticket,changed)

    def test_context_claims_replay_phase_and_cross_model_denial(self):
        with patch.object(a,"CLAIMS",self.root/"claims"):
            with a._activated(self.grant,self.locator,self.ticket,self.value,"launch"):
                contract.authorize(request=self.value["request"])
                with self.assertRaisesRegex(ValueError,"NATIVE_PHASE"):contract.authorize("load")
                changed=deepcopy(self.value["request"]);changed["model_key"]="qwen3"
                with self.assertRaisesRegex(ValueError,"CAPABILITY_REQUEST"):contract.authorize(request=changed)
            with self.assertRaises(FileExistsError):
                with a._activated(self.grant,self.locator,self.ticket,self.value,"launch"):pass
            for phase in a.STAGES[1:]:
                with a._activated(self.grant,self.locator,self.ticket,self.value,phase,child=True):
                    if phase=="native":
                        contract.authorize("load");contract.authorize("call",ordinal=0)
                        with self.assertRaises((ValueError,FileExistsError)):contract.authorize("call",ordinal=0)
                        with self.assertRaises(FileExistsError):contract.authorize("load")
            with self.assertRaises(PermissionError):contract.authorize()

    def test_sizing_unknown_and_measured_minicpm_not_peer_or_default200(self):
        blank={"calls":0,"jobs":0,"gpu_seconds":0}
        p=sizing.propose(self.grant,3763,blank,self.provider)
        self.assertEqual(p["calls"],3763)
        self.assertIn("UNKNOWN",p["status"])
        telemetry={"model_key":"minicpm4","source_sha256":self.value["request"]["source_sha256"],
            "overhead_seconds":900,"call_seconds":[20,30,40],"provenance_sha256":"f"*64}
        p=sizing.propose(self.grant,3763,blank,self.provider,telemetry)
        self.assertEqual(p["calls"],(p["seconds"]-1800-30)//80)
        self.assertNotEqual(p["calls"],200)
        telemetry["model_key"]="internvl35"
        with self.assertRaisesRegex(ValueError,"NO_PEER_THROUGHPUT"):sizing.propose(self.grant,3763,blank,self.provider,telemetry)
        provider=deepcopy(self.provider);provider["quota"]["total"]=60
        with self.assertRaisesRegex(ValueError,"BUDGET_EXHAUSTED"):sizing.propose(self.grant,3763,blank,provider)

    def test_adaptive_time_reserves_export_and_stops_before_next_call(self):
        now=[0]
        b=sizing.CallBudget(100,self.grant["sizing"],clock=lambda:now[0])
        self.assertTrue(b.can_start());b.observed(20)
        now[0]=31
        self.assertFalse(b.can_start())
        with self.assertRaises(ValueError):b.observed(float("nan"))

    def test_mirrored_journal_torn_write_gap_host_and_open_intent(self):
        root,mirror=self.root/"journal",self.root/"mirror"
        root.mkdir();mirror.mkdir()
        j=op.Journal(root,mirror)
        j._pair({"schema":op.SCHEMA,"number":1,"previous":"0"*64,"kind":"REGISTERED",
            "payload":{"host":op.host(),"locator":self.locator,"grant_sha256":digest(self.grant),"initial":self.value}})
        write(j.guard_path(self.grant),j.binding(self.grant))
        with patch.object(a,"load",return_value=self.grant):
            j.append("RESERVED",{"ticket":self.ticket,"value":self.value,"package":"data/processed/synthetic"})
            # ticket must bind actual prior chain, not a copied reservation.
            with self.assertRaisesRegex(ValueError,"SERIAL_RESERVATION"):j.state()
        (mirror/"event-00002.json").unlink()
        with self.assertRaisesRegex(ValueError,"MIRROR_DIVERGENCE"):j.events()

    def test_operator_stage_publish_owner_collect_and_pending_resume(self):
        # Only source/authority/provider/signing boundaries are synthetic doubles.
        # Real mirrored journal, signatures, capsule/history, controller, C1,
        # archive and claim verifiers all execute without bypassing authorize.
        self.grant["caps"]["job_calls"]=12
        self.grant["caps"]["total_jobs"]=512
        self.grant["caps"]["job_seconds"]=600
        remote=Mock()
        remote.dataset_create_new.return_value=NS(error_message="")
        remote.kernels_status.return_value=NS(status="COMPLETE")
        def provider(client,grant,value,prior):
            result=deepcopy(self.provider)
            result["prior_jobs"]=[{"job":p["job"],"version":1,"state":"COMPLETE","kernel_id":i}
                for i,p in enumerate(prior,1)]
            return result
        def build(ref, capsule_sha256=None, release_locator=None):
            return {"cells":[{"cell_type":"code","source":["# SYNTHETIC BOOTSTRAP BOUNDARY\n"]}],
                "metadata":{"safeshift":{"runtime_ref":ref,"source_sha256":self.value["request"]["source_sha256"],
                    "capsule_sha256":capsule_sha256}}}
        def observe(client,job,version,nb,sources,**kwargs):
            from safeshift.internvl3763_operator import code_hash
            return {"state":"COMPLETE","job_id":job,"version":1,"kernel_id":1,"notebook_code_sha256":code_hash(nb)}
        with ExitStack() as stack:
            for target,replacement in (("ROOT",self.root),("private_root",lambda p:Path(p)),("clean_source",Mock()),
                ("provider",provider),("notebook",build),("verify_published_capsule",lambda *args:{"private":True})):
                stack.enter_context(patch.object(op,target,replacement))
            stack.enter_context(patch.object(a,"load",return_value=self.grant))
            stack.enter_context(patch.object(a,"CLAIMS",self.root/"claims"))
            stack.enter_context(patch.object(rt,"validate_native_raw"))
            stack.enter_context(patch("safeshift.internvl3763_operator.api",return_value=remote))
            stack.enter_context(patch("scripts.reconcile_train3763_manual.observe_kernel",side_effect=observe))
            j=op.Journal.initialize(self.root/"journal",self.root/"mirror",self.locator,self.value)
            pkg=j.stage(self.key,self.root/"data/processed/pkg1")
            active=j.state()[3]
            with self.assertRaisesRegex(ValueError,"OPEN_RESERVATION"):j.stage(self.key,self.root/"data/processed/duplicate")
            handoff=j.publish()
            self.assertEqual(handoff["status"],"RELEASED_FOR_OWNER_UI")
            self.assertEqual(remote.dataset_create_new.call_count,1)
            with self.assertRaisesRegex(ValueError,"UNPUBLISHED_RESERVATION"):j.publish()
            value,ticket=active["value"],active["ticket"]
            work,bundle=self.root/"work",self.root/"images";bundle.mkdir()
            for i in value["request"]["plan"]["scheduled_ordinals"]:(bundle/f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
            backend=Scripted(['{"safety_level":"Level04"}',"INVALID",'{"safety_level":"Level01"}']*4)
            def factory():contract.authorize("load");return backend
            with a._activated(self.grant,self.locator,ticket,value,"launch"):pass
            for phase in a.STAGES[1:-1]:
                with a._activated(self.grant,self.locator,ticket,value,phase,child=True):pass
            with a._activated(self.grant,self.locator,ticket,value,"native",child=True):
                result=rt._execute(work,bundle,self.cohort,value["request"]["campaign"],value["request"]["plan"],[],factory,
                    image_path=lambda i:f"{i:06d}.bin",store_class=journal.BoundStore)
                claims=a.claims_snapshot()
            control=self.root/("f"*32);control.mkdir()
            write(control/"request.json",value["request"])
            write(control/"capability.json",{"locator":self.locator,"ticket":ticket})
            write(control/"claims.json",claims)
            write(control/"release.json",{"status":"TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY",
                "source_sha256":value["request"]["source_sha256"],"diagnostic":False,"attempt_observed":True,
                "scientific_qualified":False,"failure":None,"last_stage":"native"})
            for mode in a.STAGES[1:]:
                write(control/(mode+"-process.json"),{"status":"EXITED","returncode":0})
                write(control/mode/"stage.json",{"status":"RETURNED","stage":mode,
                    "request_sha256":digest(value["request"]),"source_sha256":value["request"]["source_sha256"],
                    "native_attempt_permitted":mode=="native"})
            export(control,Path(str(control)+".zip"))
            def fetch(client,v,directory,limit):
                attempt=directory/"minicpm-fulltrain"/(v["request"]["plan"]["run_id"]+".zip")
                supervisor=directory/"minicpm-fulltrain/supervision"/("f"*32+".zip")
                for source,target in ((Path(str(result)+".zip"),attempt),(Path(str(control)+".zip"),supervisor)):
                    op._copy(source,target);op._copy(Path(str(source)+".sha256.json"),Path(str(target)+".sha256.json"))
                return attempt,supervisor
            stack.enter_context(patch("scripts.minicpm_fulltrain_transport.fetch_outputs",side_effect=fetch))
            collected=j.collect(self.root/"data/processed/collection1")
            self.assertEqual(collected["counts"],{"SUCCESS":8,"INVALID":4,"NOT_ATTEMPTED":3751})
            stack.enter_context(patch("scripts.reconcile_train3763_manual.download_outputs",return_value={"mock":"provider bytes"}))
            second=j.stage(self.key,self.root/"data/processed/pkg2")
            current=j.state()[3]
            self.assertEqual(current["value"]["request"]["plan"]["scheduled_ordinals"],list(range(12,24)))
            self.assertEqual(current["ticket"]["payload"]["reserved_before"],{"calls":12,"jobs":1,"gpu_seconds":1200})
            self.assertEqual(remote.dataset_create_new.call_count,1)
            self.assertEqual(backend.calls,12)

    def test_claimed_native_controller_raw_invalid_and_adaptive_resume(self):
        # Real controller + C1 + archive/history, synthetic adapter boundary only.
        work,bundle=self.root/"work",self.root/"images";bundle.mkdir()
        for i in range(3):(bundle/f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        backend=Scripted(['{"safety_level":"Level04"}',"fenced INVALID",'{"safety_level":"Level01"}'])
        def factory():contract.authorize("load");return backend
        with patch.object(a,"CLAIMS",self.root/"claims"),patch.object(rt,"validate_native_raw"):
            with a._activated(self.grant,self.locator,self.ticket,self.value,"launch"):pass
            for phase in a.STAGES[1:-1]:
                with a._activated(self.grant,self.locator,self.ticket,self.value,phase,child=True):pass
            with a._activated(self.grant,self.locator,self.ticket,self.value,"native",child=True):
                result=rt._execute(work,bundle,self.cohort,self.value["request"]["campaign"],self.value["request"]["plan"],[],factory,
                    image_path=lambda i:f"{i:06d}.bin",store_class=journal.BoundStore)
            history=rt.recover(result,self.cohort,digest(self.value["request"]["plan"]))
        self.assertEqual(backend.calls,3)
        self.assertEqual([r["status"] for r in history["records"]],["SUCCESS","INVALID","SUCCESS"])
        claims=read(result/"claims.json")
        self.assertEqual(len([n for n in claims if n.startswith("call-")]),3)
        p=contract.plan(self.value["request"]["campaign"],self.cohort,contract.native_identity("minicpm4"),[history],
            action="resume",run_id="resume",attempt_id="resume-a",max_calls=3763,max_seconds=600)
        self.assertEqual(p["scheduled_ordinals"],list(range(3,3763)))
        self.assertTrue(Path(str(result)+".zip.sha256.json").exists())

    def test_actual_load_overhead_stops_before_first_sample_start_and_exports_pending(self):
        work,bundle=self.root/"load-work",self.root/"load-images";bundle.mkdir()
        for i in range(3):(bundle/f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        now=[0]
        backend=Scripted([])
        def factory():
            contract.authorize("load")
            now[0]=580
            return backend
        with patch.object(a,"CLAIMS",self.root/"claims"):
            with a._activated(self.grant,self.locator,self.ticket,self.value,"launch"):pass
            for phase in a.STAGES[1:-1]:
                with a._activated(self.grant,self.locator,self.ticket,self.value,phase,child=True):pass
            with a._activated(self.grant,self.locator,self.ticket,self.value,"native",child=True):
                root=rt._execute(work,bundle,self.cohort,self.value["request"]["campaign"],self.value["request"]["plan"],[],factory,
                    image_path=lambda i:f"{i:06d}.bin",store_class=journal.BoundStore,clock=lambda:now[0])
        self.assertEqual(read(root/"receipt.json")["stop"],"ADAPTIVE_TIME_STOP")
        self.assertEqual(backend.calls,0)
        self.assertFalse((root/"calls").exists())
        h=rt.recover(root,self.cohort,digest(self.value["request"]["plan"]))
        self.assertTrue(all(r["status"]=="NOT_ATTEMPTED" for r in h["records"]))
        self.assertTrue(Path(str(root)+".zip.sha256.json").exists())

    def test_duplicate_upload_intent_and_torn_mirror_never_release_budget(self):
        root,mirror=self.root/"journal",self.root/"mirror"
        root.mkdir();mirror.mkdir();j=op.Journal(root,mirror)
        j._pair({"schema":op.SCHEMA,"number":1,"previous":"0"*64,"kind":"REGISTERED",
            "payload":{"host":op.host(),"locator":self.locator,"grant_sha256":digest(self.grant),"initial":self.value}})
        write(j.guard_path(self.grant),j.binding(self.grant))
        payload=deepcopy(self.ticket["payload"])
        payload["previous_event_sha256"]=digest(j.events()[0])
        ticket=op.sign(self.key,self.public,payload)
        with patch.object(a,"load",return_value=self.grant):
            j.append("RESERVED",{"ticket":ticket,"value":self.value,"package":"data/processed/synthetic"})
            self.assertEqual(j.state()[2],payload["reserved_after"])
            j.append("PUBLISH_INTENT",{"ticket_sha256":digest(ticket)})
            j.append("PUBLISH_INTENT",{"ticket_sha256":digest(ticket)})
            with self.assertRaisesRegex(ValueError,"NO_DUPLICATE_CAPSULE_UPLOAD"):j.state()

    def test_all3763_once_through_controller_export_and_complete_resume_no_calls(self):
        value=deepcopy(self.value)
        r=value["request"]
        r["plan"]=contract.plan(r["campaign"],self.cohort,contract.native_identity("minicpm4"),[],action="initial",
            run_id="synthetic-full3763",attempt_id="synthetic-full3763-a",max_calls=3763,max_seconds=7200)
        ticket=self.make_ticket(value)
        work,bundle=self.root/"full-work",self.root/"full-images";bundle.mkdir()
        for i in range(3763):(bundle/f"{i:06d}.bin").write_bytes(journal.synthetic_bytes(i))
        class FullScripted(Scripted):
            def generate(inner,image,sample):
                value=super().generate(image,sample)
                if inner.calls % 1000 == 0:
                    print(f"SYNTHETIC_FULL3763_PROGRESS calls={inner.calls}",flush=True)
                return value
        backend=FullScripted(['{"safety_level":"Level04"}']*3763)
        def factory():contract.authorize("load");return backend
        with patch.object(a,"CLAIMS",self.root/"full-claims"),patch.object(rt,"validate_native_raw"):
            with a._activated(self.grant,self.locator,ticket,value,"launch"):pass
            for phase in a.STAGES[1:-1]:
                with a._activated(self.grant,self.locator,ticket,value,phase,child=True):pass
            with a._activated(self.grant,self.locator,ticket,value,"native",child=True):
                result=rt._execute(work,bundle,self.cohort,r["campaign"],r["plan"],[],factory,
                    image_path=lambda i:f"{i:06d}.bin",store_class=journal.BoundStore)
            history=rt.recover(result,self.cohort,digest(r["plan"]))
        self.assertEqual(backend.calls,3763)
        self.assertEqual([v["sample_id"] for v in history["records"]],
            [v["sample_id"] for v in self.cohort["samples"]])
        self.assertEqual(read(result/"receipt.json")["observed_native_markers"],3763)
        self.assertEqual(len([n for n in read(result/"claims.json") if n.startswith("call-")]),3763)
        p=contract.plan(r["campaign"],self.cohort,r["plan"]["identity"],[history],action="resume",
            run_id="finished",attempt_id="finished-a",max_calls=3763,max_seconds=600)
        self.assertEqual(p["scheduled_ordinals"],[])
        with self.assertRaisesRegex(ValueError,"PENDING_COUNT"):
            sizing.propose(self.grant,0,ticket["payload"]["reserved_after"],self.provider)
        with tempfile.TemporaryDirectory() as tmp:
            restored=Path(tmp)/"empty-vm"
            self.assertEqual(rt.import_history(restored,Path(str(result)+".zip"),sha(str(result)+".zip"),
                self.cohort,r["campaign"],digest(r["plan"])),history)


if __name__=="__main__":unittest.main()
