"""CPU only: generated vectors/bytes; never opens dataset images or annotations."""
import ast
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from safeshift.diagnostics.resource_pilot import audit, bootstrap as boot, capture, cohort, contract, custody, engine, orchestrate as flow, resources, worker
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.ls1 import runtime
from safeshift.ls1.tokenizer import probe
from safeshift.pa3.native.journal import Journal
from tests.test_hnlo_capture import TOK, CANDIDATES, output
from tests import test_hnlo_one_click as old

ROOT = Path(__file__).resolve().parents[1]
ROWS = [{"sample_id": f"synthetic-{i}", "image_locator": f"DATA_PATH/train/Annotations/synthetic-{i}.jpg",
         "image_sha256": h} for i, h in enumerate(cohort.IMAGE_SHA256)]
CONFIG = {"eos_token_id": 999}
KWARGS = {"do_sample": False, "num_beams": 1, "num_return_sequences": 1, "max_new_tokens": 32,
          "return_dict_in_generate": True, "output_logits": True, "output_scores": True}


def source():
    return {**old.source(), "pr_number": 999}


def approved(model="qwen3"):
    v = contract.template()
    v["grant"] = {"approved_by": "SYNTHETIC_TEST_ONLY", "role": "Research Lead", "approved_utc": "2026-10-19T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-decision",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64,
        "units": [{"unit": contract.unit(model), "approvals": {f: True for f in contract.FLAGS}}]}
    return v


def fill(cap, text='{"safety_level":"Level03"}', tokenizer=TOK, native=None):
    cap.write("runtime-t1", probe(TOK))
    cap.write("call", {"configuration": CONFIG, "kwargs": KWARGS, "input_shapes": {"input_ids": [1, 3]}})
    cap.write("raw-provenance", {"processors": []})
    cap.write("stopping", {"max_length": 35, "eos_token_ids": [999]})
    cap.write("complexity", {"input_tokens": 3, "image_patches": 1, "patch_unit": "SYNTHETIC"})
    capture.persist(native or output(text, processed_delta=0), [11, 22, 33], CANDIDATES, tokenizer,
                    cap, CONFIG, KWARGS, lambda t, ids, token: runtime.summarize_vector(t.data[0], ids, token))


class Backend:
    tokenizer = TOK
    def __init__(self, journal, failure=None):
        self.calls, self.failure, self.journal = [], failure, journal
    def generate(self, row, cap):
        self.calls.append(row["ordinal"])
        if self.failure == ("error", row["ordinal"]):
            raise OSError("SYNTHETIC_OOM_OR_DISK_FAILURE")
        if self.failure == ("interrupt", row["ordinal"]):
            raise KeyboardInterrupt()
        fill(cap, 'invalid' if self.failure == ("invalid", row["ordinal"]) else '{"safety_level":"Level03"}')
    def close(self):
        self.journal.write("native-counts", {"load_calls": 1, "generate_ordinals": self.calls})


class Case(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.enterContext(patch("socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")))


class ContractTests(Case):
    def test_default_grant_and_exact_two_new_units(self):
        self.assertIsNone(contract.template()["grant"])
        self.assertEqual(json.loads((ROOT / contract.AUTHORITY).read_bytes()), contract.template())
        self.assertEqual(len({contract.unit(m)["attempt_id"] for m in contract.MODELS}), 2)
        self.assertFalse(contract.template()["scope"]["full_vocab_replay"])
    def test_valid_model_specific_grant(self):
        contract.authorize(approved(), source(), "qwen3")
        with self.assertRaisesRegex(PermissionError, "MODEL_NOT_GRANTED"):
            contract.authorize(approved(), source(), "internvl3")
    def test_old_grants_wrong_source_scope_and_missing_flags(self):
        values = [contract.template(), old.approved()]
        for flag in contract.FLAGS:
            v = approved(); v["grant"]["units"][0]["approvals"][flag] = False; values.append(v)
        for modify in (lambda v: v["grant"].update(implementation_commit="f" * 40),
                       lambda v: v["grant"].update(source_payload_sha256="e" * 64),
                       lambda v: v["grant"].update(decision_url="https://github.com/tantdna2/SafeShift/pull/117#old"),
                       lambda v: v["grant"].update(approved_utc="invalid"),
                       lambda v: v["grant"]["units"].append(deepcopy(v["grant"]["units"][0])),
                       lambda v: v["scope"].update(retry=True),
                       lambda v: v["grant"]["units"][0]["unit"].update(ordinals=list(range(1,9)))):
            v = approved(); modify(v); values.append(v)
        for v in values:
            with self.subTest(v=v), self.assertRaises((PermissionError, ValueError)):
                contract.authorize(v, source(), "qwen3")
    def test_exact_original_first_eight_manifest_only(self):
        from safeshift.pa3.native import train
        # Only tracked inference metadata is read. Never train.load_full or dataset.
        with patch.object(train, "load_full", side_effect=AssertionError("GT_FORBIDDEN")):
            rows = cohort.planned(ROOT)
        self.assertEqual(len(rows), 8)
        self.assertEqual(tuple(r["image_sha256"] for r in rows), cohort.IMAGE_SHA256)
        data = (ROOT / train.inference_path(0)).read_bytes()
        self.assertEqual(rows, train.validate_inference(json.loads(data), 0)[:8])
    def test_changed_manifest_rejected(self):
        with patch.object(Path, "read_bytes", return_value=b"changed source"):
            with self.assertRaisesRegex(ValueError, "BYTES_CHANGED"):
                cohort.planned(ROOT)
    def test_wrong_ordinal_image_or_gt_in_worker_request_rejected(self):
        good = cohort.opaque_rows(ROWS)
        for modify in (lambda v: v.reverse(), lambda v: v[0].update(image_sha256="0" * 64),
                       lambda v: v[0].update(ordinal=False), lambda v: v[0].update(sample_id="GT"), lambda v: v.pop()):
            v = deepcopy(good); modify(v)
            with self.assertRaises(ValueError): cohort.validate_opaque(v)
    def test_worker_null_authority_stops_before_guard_or_torch(self):
        write(self.root / contract.AUTHORITY, contract.template())
        with patch.object(boot, "verify_topology", return_value=source()), patch("safeshift.diagnostics.one_click.network.deny_inet", side_effect=AssertionError("EARLY_GPU")) as guard:
            r = worker.execute("inspect", self.root, self.root / "evidence", source(), "qwen3", "unused", self.root, self.root)
        self.assertEqual(r["status"], "FAILED")
        self.assertEqual(r["error"]["type"], "PermissionError")
        guard.assert_not_called()


class EngineTests(Case):
    def execute(self, failure=None, **kwargs):
        def factory(j):
            self.backend = Backend(j, failure)
            return self.backend
        return engine.execute(self.root / "raw", cohort.opaque_rows(ROWS), factory, **kwargs)
    def test_eight_successes_one_load_exact_order_and_seals(self):
        j = self.execute()
        self.assertTrue(j.verify())
        self.assertTrue(j.exists("finish"))
        self.assertEqual(self.backend.calls, list(range(8)))
        self.assertTrue(all(r["seconds"] >= 0 for r in j.read("accounting")))
        self.assertTrue(Journal(self.root / "raw/sample-000000").verify())
    def test_oom_stops_and_accounts_unattempted_tail(self):
        j = self.execute(("error", 2))
        self.assertEqual(self.backend.calls, [0,1,2])
        self.assertEqual([r["status"] for r in j.read("accounting")], ["SUCCESS"]*2+["TECHNICAL_ERROR"]+["NOT_ATTEMPTED"]*5)
        self.assertFalse(j.exists("finish"))
    def test_invalid_stops_without_repair_or_skip(self):
        j = self.execute(("invalid", 1))
        self.assertEqual(self.backend.calls, [0,1])
        self.assertEqual(j.read("accounting")[1]["status"], "INVALID")
    def test_interrupt_preserved(self):
        j = self.execute(("interrupt", 0))
        self.assertEqual(j.read("accounting")[0]["status"], "INTERRUPTED")
        self.assertTrue(j.verify())
    def test_missing_resources_prevents_load(self):
        with patch.object(self, "unused", create=True):
            j = self.execute(resources=lambda: (_ for _ in ()).throw(OSError("LOW_RAM")))
        self.assertTrue(all(r["status"] == "NOT_ATTEMPTED" for r in j.read("accounting")))
        self.assertFalse(hasattr(self, "backend"))
    def test_load_failure_retains_timing_and_all_eight(self):
        def fail(j): raise OSError("MODEL_TOO_LARGE")
        j = engine.execute(self.root / "raw", cohort.opaque_rows(ROWS), fail)
        self.assertEqual(json.loads((self.root / "raw/model-load-timing.json").read_bytes())["status"], "FAILED")
        self.assertEqual(len(j.read("accounting")), 8)
    def test_no_same_root_resume(self):
        self.execute(("error", 0))
        with self.assertRaises(FileExistsError): self.execute()
    def test_raw_before_decode_and_seal_before_parse(self):
        cap = capture.SampleCapture(self.root / "cap", cohort.opaque_rows(ROWS)[0])
        class Tokenizer:
            def decode(inner, *args, **kwargs):
                self.assertTrue(cap.journal.exists("raw-000"))
                self.assertTrue(cap.journal.exists("processed-000"))
                raise RuntimeError("DECODE_FAILURE")
        with self.assertRaisesRegex(RuntimeError, "DECODE_FAILURE"): fill(cap, tokenizer=Tokenizer())
        with self.assertRaisesRegex(ValueError, "SEAL_REQUIRED"): capture.replay(cap.journal, TOK)
    def test_raw_processed_distinct_and_cpu_score(self):
        cap = capture.SampleCapture(self.root / "cap", cohort.opaque_rows(ROWS)[0])
        fill(cap)
        cap.journal.seal()
        r = capture.replay(cap.journal, TOK)
        self.assertEqual(r["status"], "SUCCESS")
        self.assertIsInstance(r["score"], float)
    def test_nonfinite_raw_and_separate_processed_preserved_every_step(self):
        cap = capture.SampleCapture(self.root / "cap", cohort.opaque_rows(ROWS)[0])
        native = output(processed_delta=2)
        native.logits[0].data[0][CANDIDATES[0]] = float("nan")
        fill(cap, native=native)
        self.assertEqual(cap.journal.read("raw-000")["nonfinite"]["nan"], 1)
        self.assertEqual(cap.journal.read("processed-000")["nonfinite"]["nan"], 0)
        self.assertEqual(len([k for k in cap.journal.inventory() if k.startswith("raw-") and k != "raw-provenance"]), len(native.logits))
    def test_torn_bytes_retained_by_custody(self):
        p = self.root / "raw/sample/torn.json"; p.parent.mkdir(parents=True); p.write_bytes(b'{"torn":')
        custody.seal(self.root / "raw")
        custody.verify(self.root / "raw")
        self.assertEqual(p.read_bytes(), b'{"torn":')
        p.write_bytes(b"altered")
        with self.assertRaisesRegex(ValueError, "CUSTODY_CHANGED"): custody.verify(self.root / "raw")


class FakeOps(flow.Operations):
    failure = None
    calls = []
    def gpu_memory(self): return {0: 456}
    def preflight(self):
        self.calls.append("preflight")
        if self.failure == "preflight": raise OSError("LOW_RESOURCE")
        return {"synthetic": True}
    def software(self):
        self.calls.append("software")
        if self.failure == "software": raise OSError("ENV_SETUP_FAILED")
    def provision(self):
        self.calls.append("checkpoint")
        if self.failure == "checkpoint": raise OSError("CHECKPOINT_UNAVAILABLE")
    def stage(self, rows):
        self.calls.append("stage")
        if self.failure == "stage": raise ValueError("HASH_MISMATCH")
    def worker(self, mode):
        self.calls.append(mode)
        if self.failure == mode: raise RuntimeError("WORKER_KILLED")
        if mode == "inference":
            engine.execute(self.evidence / "raw", cohort.opaque_rows(ROWS), lambda j: Backend(j))
        return {"status": "RETURNED"}
    def audit(self):
        return audit.checked(self.evidence, self.repo, TOK)


class FlowTests(Case):
    def run_pilot(self, grant=None, failure=None, work="work"):
        if not (self.root / contract.AUTHORITY).exists(): write(self.root / contract.AUTHORITY, grant or approved())
        out = self.root / "out"; out.mkdir(exist_ok=True)
        FakeOps.calls, FakeOps.failure = [], failure
        with patch.object(cohort, "planned", return_value=ROWS), patch.object(boot, "verify_topology", return_value=source()):
            return flow.run(self.root, self.root / work, out, source(), "qwen3", operations_factory=FakeOps,
                sampler_factory=lambda roots, **kw: resources.Sampler(roots, observe_rss=lambda: 123, **kw))
    def test_null_grant_exports_eight_not_attempted_before_operations(self):
        r = self.run_pilot(contract.template())
        self.assertEqual(r["status"], "BLOCKED")
        self.assertEqual(FakeOps.calls, [])
        self.assertEqual([x["status"] for x in r["samples"]], ["NOT_ATTEMPTED"] * 8)
        self.assertEqual(r["export"]["status"], "EXPORTED")
    def test_complete_cpu_simulation_export_and_projection(self):
        r = self.run_pilot()
        self.assertEqual(r["status"], "COMPLETE")
        self.assertEqual(r["cpu_replay"]["cpu_hnlo_replay"], "PASS")
        self.assertEqual(r["projection"]["successful"], 8)
        self.assertGreater(r["journal_bytes"], 0)
        self.assertEqual(r["export"]["resources"]["process_tree_peak_rss_bytes"], 123)
        self.assertEqual(r["export"]["resources"]["sampled_device_peak_used_bytes"], {"0": 456})
        self.assertFalse(r["full_vocab_replay"])
    def test_failures_export_every_planned_ordinal(self):
        for name in ("preflight", "software", "inspect", "checkpoint", "stage", "inference"):
            with self.subTest(name=name):
                # Separate synthetic session/repo per failure, no ledger removal.
                original = self.root; self.root = original / name; self.root.mkdir()
                r = self.run_pilot(failure=name)
                self.assertIn(r["status"], ("FAILED", "PARTIAL"))
                self.assertEqual(len(r["samples"]), 8)
                self.assertEqual(r["export"]["status"], "EXPORTED")
                self.root = original
    def test_consumed_attempt_blocks_new_setup(self):
        self.run_pilot()
        r = self.run_pilot(work="second-work")
        self.assertEqual(r["error"]["type"], "FileExistsError")
        self.assertEqual(FakeOps.calls, [])
    def test_staging_wrong_bytes_stop_without_reading_later_images(self):
        rows = deepcopy(ROWS)
        data = b"synthetic-only-not-an-image"
        p = self.root / rows[0]["image_locator"]; p.parent.mkdir(parents=True); p.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            flow.stage_images(self.root, rows, self.root / "staged", self.root / "receipt")
        j = Journal(self.root / "receipt")
        self.assertTrue(j.verify())
        self.assertEqual(j.read("failure")["ordinal"], 0)
        self.assertFalse(j.exists("image-000001.read-start"))
    def test_backend_wrong_staged_image_rejected_before_native_generate(self):
        from safeshift.diagnostics.resource_pilot.backend import Backend as NativeBackend
        (self.root / "000000.image").write_bytes(b"synthetic-wrong-bytes")
        backend = NativeBackend.__new__(NativeBackend)
        backend.inputs = self.root
        cap = capture.SampleCapture(self.root / "cap", cohort.opaque_rows(ROWS)[0])
        with self.assertRaisesRegex(ValueError, "STAGED_IMAGE_CHECKSUM_MISMATCH"):
            backend.generate(cohort.opaque_rows(ROWS)[0], cap)
        self.assertFalse(cap.journal.exists("call"))
    def test_cpu_audit_refuses_unsealed_bytes(self):
        with self.assertRaises((OSError, ValueError)): audit.checked(self.root, ROOT, TOK)


class ResourceTests(Case):
    def test_projection_partial_failure_and_nonrandom_limits(self):
        r = resources.projection([{"status": "SUCCESS", "seconds": 2}, {"status": "TECHNICAL_ERROR", "seconds": 9}])
        self.assertEqual(r["attempted"], 2)
        self.assertEqual(r["successful"], 1)
        self.assertEqual(r["estimate_941_seconds"], 1882)
        self.assertIn("CENSORED", r["estimate_status"])
        self.assertIsNone(resources.projection([])["estimate_941_seconds"])
    def test_sampler_faults_explicitly_partial(self):
        s = resources.Sampler({"output": self.root}, observe_rss=lambda: (_ for _ in ()).throw(OSError()))
        s.start(); r = s.finish()
        self.assertEqual(r["coverage"], "PARTIAL_SAMPLED")
        self.assertIsNone(r["process_tree_peak_rss_bytes"])
        self.assertEqual(r["errors"], ["OSError"])
    def test_timing_failure_retained(self):
        with self.assertRaises(OSError): resources.timed(self.root / "time.json", lambda: (_ for _ in ()).throw(OSError()))
        self.assertEqual(json.loads((self.root / "time.json").read_bytes())["status"], "FAILED")
    def test_physical_device_memory_query_is_cpu_mocked(self):
        with patch.object(resources.subprocess, "check_output", return_value="0, 512\n1, 1024\n"):
            self.assertEqual(resources.gpu_memory(), {0:512*2**20, 1:1024*2**20})


class GuardedWorkerTests(Case):
    def test_internvl3_order_driver_handles_and_gate_failures(self):
        from safeshift.diagnostics.internvl3_recovery import network, monitor
        from safeshift.diagnostics.internvl3_cuda import worker as cuda_worker
        from safeshift.diagnostics.internvl3_hnlo import driver
        from safeshift.diagnostics.one_click import worker as common
        for fault in (None, "seccomp", "clean_env", "driver", "cuda", "maps_final"):
            with self.subTest(fault=fault):
                root = self.root / str(fault); root.mkdir()
                write(root / contract.AUTHORITY, approved("internvl3"))
                events = []
                def step(name, result=None):
                    events.append(name)
                    if name == fault: raise ValueError("SYNTHETIC_GATE")
                    return result
                @contextmanager
                def guarded(*args):
                    step("python_guard")
                    try: yield
                    finally: step("guard_exit")
                class Drivers:
                    def __init__(self, evidence): step("driver")
                    def observe(self, stage): step("maps_" + stage)
                fake_torch = SimpleNamespace()
                def environment(*args, **kwargs):
                    result = step("cuda", {})
                    sys.modules["torch"] = fake_torch
                    return result
                fake_monitor = SimpleNamespace(finish=lambda: {"coverage": "PARTIAL"})
                with patch.object(boot, "verify_topology", side_effect=lambda *a, **k: step("source", source())), \
                     patch.object(network, "deny_inet", side_effect=lambda: step("seccomp", {})), \
                     patch.object(network, "network_denied", guarded), patch.object(monitor, "Monitor", return_value=fake_monitor), \
                     patch.object(cuda_worker, "check_environment", side_effect=lambda *a: step("clean_env")), \
                     patch.object(driver, "DriverSession", Drivers), patch.object(common, "environment", environment), \
                     patch.object(common, "memory", return_value={}), patch.dict(sys.modules):
                    r = worker.execute("inspect", root, root / "evidence", source(), "internvl3", "unused", root, root)
                self.assertTrue((root / "evidence/result.json").exists())
                if fault is None:
                    self.assertEqual(events, ["source", "seccomp", "python_guard", "clean_env", "driver", "cuda", "maps_after_cuda", "maps_final", "guard_exit"])
                    self.assertEqual(r["status"], "RETURNED")
                    self.assertTrue(r["driver_handles_retained_through_finalization"])
                else:
                    self.assertEqual(r["status"], "FAILED")
                    if fault in ("seccomp", "clean_env", "driver"):
                        self.assertNotIn("cuda", events)


class ReleaseTests(old.SourceTests):
    def setUp(self):
        self.enterContext(patch.multiple(old, boot=boot, AUTHORITY=contract.AUTHORITY, LOCK=contract.LOCK))
        super().setUp()


class SourceNotebookTests(unittest.TestCase):
    def test_notebooks_compile_empty_outputs_fixed_model_and_payload(self):
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        digest = hashlib.sha256(boot.canonical(lock)).hexdigest()
        for name in boot.NOTEBOOK_PATHS:
            nb = json.loads((ROOT / name).read_bytes()); code = "".join(nb["cells"][1]["source"])
            ast.parse(code)
            self.assertEqual(nb["cells"][1]["outputs"], [])
            self.assertIn(digest, code)
            self.assertIn('bootstrap("' + nb["metadata"]["safeshift"]["model"] + '")', code)
            self.assertEqual(nb["metadata"]["safeshift"]["ordinals"], list(range(8)))
    def test_selective_upstream_provenance_bytes_and_no_draft_dependency(self):
        v = json.loads((ROOT / "configs/diagnostics/resource_pilot_provenance.v1.json").read_bytes())
        self.assertEqual(len(v["records"]), 5)
        for r in v["records"]:
            data = subprocess.check_output(["git", "-C", str(ROOT), "show", r["upstream_commit"] + ":" + r["upstream_path"]])
            self.assertEqual(hashlib.sha256(data).hexdigest(), r["upstream_sha256"])
            ast.parse((ROOT / r["destination"]).read_bytes())
        for p in (ROOT / "safeshift/diagnostics/resource_pilot").glob("*.py"):
            self.assertNotIn("from safeshift.diagnostics.hnlo_train", p.read_text())
            self.assertNotIn("from ..hnlo_train", p.read_text())
    def test_source_lock_all_bytes(self):
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        for r in lock["files"]:
            data = (ROOT / r["path"]).read_bytes()
            if r["path"] in boot.NOTEBOOK_PATHS: data = boot.notebook_bytes(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), r["sha256"], r["path"])


if __name__ == "__main__":
    unittest.main()
