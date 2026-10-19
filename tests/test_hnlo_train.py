"""Synthetic CPU evidence only. Never reads real images, weights or calls CUDA."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.hnlo_train import audit, bootstrap as boot, capture, cohort, contract, engine, orchestrate
from safeshift.diagnostics.one_click.artifacts import write, sha256
from safeshift.ls1 import core, runtime
from safeshift.ls1.tokenizer import probe
from safeshift.pa3.native.journal import Journal
from safeshift.pa3.native.native_score import pending
from tests.test_hnlo_capture import TOK, CANDIDATES, Tensor, output
from tests import test_hnlo_one_click as old

ROOT = Path(__file__).resolve().parents[1]
ROWS = [{"sample_id": f"synthetic-{i}", "image_sha256": str(i + 1) * 64, "image_locator": f"unused/{i}.jpg"} for i in range(3)]
CONFIG = {"eos_token_id": 999}
KWARGS = {"do_sample": False, "num_beams": 1, "num_return_sequences": 1, "max_new_tokens": 32,
          "return_dict_in_generate": True, "output_logits": True, "output_scores": True}


def source():
    return {**old.source(), "pr_number": 999}


def approved(model="qwen3", shard=0):
    value = contract.template()
    value["grant"] = {"approved_by": "SYNTHETIC_TEST_ONLY", "role": "Research Lead", "approved_utc": "2026-10-19T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-decision",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/999#synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64,
        "units": [{"unit": contract.unit(model, shard), "approvals": {k: True for k in contract.FLAGS}}]}
    return value


def fill(cap, text='{"safety_level":"Level03"}', tokenizer=TOK, native=None):
    cap.write("runtime-t1", probe(TOK))
    cap.write("call", {"configuration": CONFIG, "kwargs": KWARGS, "input_shapes": {"input_ids": [1, 3]}})
    cap.write("raw-provenance", {"processors": []})
    cap.write("stopping", {"max_length": 35, "eos_token_ids": [999]})
    capture.persist(native or output(text, processed_delta=0), [11, 22, 33], CANDIDATES, tokenizer,
                    cap, CONFIG, KWARGS, lambda t, ids, token: runtime.summarize_vector(t.data[0], ids, token))


class FakeBackend:
    tokenizer = TOK

    def __init__(self, index, failure=None, invalid_at=None):
        self.index, self.calls, self.failure, self.invalid_at = index, [], failure, invalid_at

    def generate(self, row, cap):
        from safeshift.diagnostics.hnlo_train.backend import record_native_call
        record_native_call(self.index, cap, set(self.calls))
        self.calls.append(row["ordinal"])
        if self.failure == row["ordinal"]:
            raise RuntimeError("SYNTHETIC_CUDA_RESOURCE_FAILURE")
        fill(cap, 'invalid' if self.invalid_at == row["ordinal"] else '{"safety_level":"Level03"}')

    def close(self):
        self.index.write("fake-counts", {"calls": self.calls})


class CPUCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ("socket.socket.connect", "socket.create_connection"):
            self.enterContext(patch(name, side_effect=AssertionError("NETWORK_FORBIDDEN")))

    def cap(self, ordinal=0, name="sample"):
        return capture.SampleCapture(self.root / name, {"ordinal": ordinal, "image_sha256": "1" * 64})


class CohortTests(unittest.TestCase):
    def test_exact_original_bytes_3763_ids_four_sizes_and_full_alignment(self):
        shards = cohort.inference(ROOT)
        self.assertEqual(list(map(len, shards)), [941, 941, 941, 940])
        self.assertEqual(len({r["sample_id"] for part in shards for r in part}), 3763)
        metadata = cohort.metadata(ROOT)
        self.assertEqual(set(metadata), {r["sample_id"] for p in shards for r in p})
        self.assertEqual(sum(m["level"] == "Level03" for m in metadata.values()), 8)

    def test_changed_shard_bytes_rejected_before_parsing(self):
        original = Path.read_bytes
        def changed(path):
            data = original(path)
            return data + b" " if str(path).endswith("pa3_full_train_shard0.v1.json") else data
        with patch.object(Path, "read_bytes", changed), self.assertRaisesRegex(ValueError, "BYTES_CHANGED"):
            cohort.inference(ROOT)

    def test_worker_projection_removes_label_bearing_id_and_path(self):
        rows = [{"sample_id": "power-Level04-example", "image_locator": "Normal_data/Level04.jpg", "image_sha256": "a" * 64}]
        value = cohort.opaque_rows(rows)
        self.assertEqual(value, [{"ordinal": 0, "image_sha256": "a" * 64}])
        self.assertNotIn("Level", json.dumps(value))
        for extra in ("sample_id", "image_locator", "level", "domain", "group", "binary_class"):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                cohort.validate_opaque([{**value[0], extra: "GT"}], 1)

    def test_ordinal_count_order_bool_and_hash_fail_closed(self):
        good = cohort.opaque_rows(ROWS)
        for change in (lambda r: r.pop(), lambda r: r.reverse(), lambda r: r[0].update(ordinal=False),
                       lambda r: r[0].update(image_sha256="bad")):
            bad = deepcopy(good)
            change(bad)
            with self.assertRaises(ValueError):
                cohort.validate_opaque(bad, 3)


class AuthorityTests(CPUCase):
    def test_postseal_label_gate_precedes_all_metadata_reads(self):
        with patch.object(cohort, "metadata", side_effect=AssertionError("EARLY_GT")) as labels:
            with self.assertRaises((OSError, ValueError)):
                audit.evaluate(self.root, ROOT, TOK)
            labels.assert_not_called()

    def test_null_default_and_independent_unit_grant(self):
        self.assertEqual(json.loads((ROOT / contract.AUTHORITY).read_bytes()), contract.template())
        with self.assertRaises(PermissionError):
            contract.authorize(contract.template(), source(), "qwen3", 0)
        contract.authorize(approved(), source(), "qwen3", 0)
        for model, shard in (("internvl3", 0), ("qwen3", 1)):
            with self.assertRaisesRegex(PermissionError, "NOT_GRANTED"):
                contract.authorize(approved(), source(), model, shard)

    def test_old_grants_missing_approvals_changed_source_and_duplicate_units(self):
        variants = [old.approved()]
        for flag in contract.FLAGS:
            value = approved()
            value["grant"]["units"][0]["approvals"][flag] = False
            variants.append(value)
        for modify in (lambda v: v["grant"].update(implementation_commit="d" * 40),
                       lambda v: v["grant"].update(source_payload_sha256="d" * 64),
                       lambda v: v["grant"].update(approved_utc="2026-99-99T00:00:00Z"),
                       lambda v: v["grant"].update(decision_url="https://github.com/tantdna2/SafeShift/pull/116#old"),
                       lambda v: v["grant"]["units"].append(deepcopy(v["grant"]["units"][0])),
                       lambda v: v["grant"]["units"][0]["unit"].update(max_attempts=2),
                       lambda v: v["scope"].update(clamp="QWEN_R2")):
            value = approved()
            modify(value)
            variants.append(value)
        for value in variants:
            with self.subTest(value=value), self.assertRaises((PermissionError, ValueError)):
                contract.authorize(value, source(), "qwen3", 0)

    def test_null_run_blocks_before_cohort_data_build_or_gpu_and_exports(self):
        (self.root / contract.AUTHORITY).parent.mkdir(parents=True)
        write(self.root / contract.AUTHORITY, contract.template())
        work, out = self.root / "work", self.root / "out"
        out.mkdir()
        with patch.object(cohort, "inference", side_effect=AssertionError("COHORT_READ")), \
             patch.object(orchestrate, "Operations", side_effect=AssertionError("PROVISION_OR_GPU")):
            result = orchestrate.run(self.root, work, out, source(), "qwen3", 0)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["gpu_worker_started"])
        self.assertEqual(result["coverage"]["status_counts"]["NOT_ATTEMPTED"], 941)
        self.assertEqual(len(list(out.glob("*.tar.gz"))), 1)

    def test_consumed_unit_never_reenters_provisioning(self):
        write(self.root / contract.AUTHORITY, approved())
        out = self.root / "out"
        (out / "data/processed/hnlo_train_attempts" / contract.unit("qwen3", 0)["run_id"]).mkdir(parents=True)
        with patch.object(cohort, "inference", side_effect=AssertionError("REENTERED")):
            result = orchestrate.run(self.root, self.root / "work", out, source(), "qwen3", 0)
        self.assertEqual(result["error"]["type"], "FileExistsError")
        self.assertFalse(result["provisioning_started"])


class CaptureTests(CPUCase):
    def test_raw_summaries_persist_before_decode_and_match_baseline(self):
        cap = self.cap()
        class Observed:
            def decode(self, ids, **kw):
                self_outer.assertTrue(cap.journal.exists("raw-000"))
                self_outer.assertTrue(cap.journal.exists(f"processed-{len(ids)-1:03d}"))
                return TOK.decode(ids, **kw)
        self_outer = self
        fill(cap, tokenizer=Observed())
        with self.assertRaisesRegex(ValueError, "SEAL_REQUIRED"):
            capture.replay(cap.journal, TOK)
        cap.journal.seal()
        result = capture.replay(cap.journal, TOK)
        self.assertEqual(result["status"], "SUCCESS")
        z = result["details"]["raw_label_logits"]
        import math
        m = max(z[:3])
        expected = m + math.log(math.fsum(math.exp(x-m) for x in z[:3])) - z[3]
        self.assertAlmostEqual(result["score"], expected, places=12)

    def test_decode_failure_retains_every_raw_and_processed_summary(self):
        cap = self.cap()
        class Broken:
            def decode(self, *a, **kw):
                raise ValueError("SYNTHETIC_DECODE_FAILURE")
        with self.assertRaises(ValueError):
            fill(cap, tokenizer=Broken())
        n = cap.journal.read("native")["raw_steps"]
        self.assertTrue(all(cap.journal.exists(f"{k}-{i:03d}") for k in ("raw", "processed") for i in range(n)))
        self.assertFalse(cap.journal.exists("trace"))

    def test_invalid_stays_invalid_without_label_rescue(self):
        cap = self.cap()
        fill(cap, text="INVALID Level03")
        cap.journal.seal()
        result = capture.replay(cap.journal, TOK)
        self.assertEqual(result["status"], "INVALID")
        self.assertIsNone(result["score"])

    def test_raw_nonfinite_is_technical_failure_and_never_clamped(self):
        cap = self.cap()
        native = output(processed_delta=0)
        native.logits[0].data[0][1] = float("nan")
        fill(cap, native=native)
        cap.journal.seal()
        self.assertEqual(capture.replay(cap.journal, TOK)["status"], "TECHNICAL_ERROR")
        self.assertEqual(cap.journal.read("raw-000")["nonfinite"]["nan"], 1)

    def test_wrong_label_mapping_raw_summary_or_processor_is_rejected(self):
        for key in ("runtime-t1", "raw-provenance", "raw-000", "call"):
            cap = self.cap(name=key)
            fill(cap)
            # Create a self-consistent new synthetic seal to test semantic validation,
            # rather than merely testing the file hash detector.
            value = cap.journal.read(key)
            if key == "runtime-t1":
                value["checks"][0]["token_ids"].reverse()
            elif key == "raw-provenance":
                value["processors"] = ["ForcedProcessor"]
            elif key == "raw-000":
                value["argmax_id"] = 0
            else:
                value["kwargs"] = {**KWARGS, "max_new_tokens": 33}
            target = cap.journal.path(key)
            target.unlink()
            target.with_suffix(".sha256.json").unlink()
            cap.journal.write(key, value)
            cap.journal.seal()
            with self.subTest(key=key), self.assertRaises(ValueError):
                capture.replay(cap.journal, TOK)

    def test_budget_failure_stops_without_truncating_prior_observations(self):
        cap = capture.SampleCapture(self.root / "limited", {"ordinal": 0, "image_sha256": "1" * 64}, max_bytes=20000)
        with self.assertRaisesRegex(OSError, "NO_TRUNCATION"):
            cap.write("oversized", {"value": "x" * 21000})
        self.assertTrue(cap.journal.exists("identity"))
        self.assertFalse(cap.journal.exists("oversized"))


class LifecycleTests(CPUCase):
    def run_fake(self, failure=None, invalid_at=None, resources=lambda: None, clock=None):
        factory = lambda index: FakeBackend(index, failure=failure, invalid_at=invalid_at)
        kwargs = {"clock": clock} if clock else {}
        return engine.execute(self.root / "raw", cohort.opaque_rows(ROWS), 3, factory, resources=resources, **kwargs)

    def test_one_call_each_and_invalid_does_not_drop_or_retry(self):
        journal = self.run_fake(invalid_at=1)
        self.assertTrue(journal.verify())
        self.assertEqual(journal.read("fake-counts")["calls"], [0, 1, 2])
        rows, complete, integrity = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual([r["status"] for r in rows], ["SUCCESS", "INVALID", "SUCCESS"])
        self.assertTrue(complete)

    def test_resource_failure_preserves_failed_and_not_attempted_denominators(self):
        journal = self.run_fake(failure=1)
        rows, complete, integrity = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual([r["status"] for r in rows], ["SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED"])
        self.assertFalse(complete)
        self.assertEqual(journal.read("fake-counts")["calls"], [0, 1])
        with self.assertRaises(FileExistsError):
            self.run_fake()

    def test_preload_cuda_failure_keeps_all_not_attempted(self):
        self.run_fake(resources=lambda: (_ for _ in ()).throw(RuntimeError("CUDA_UNAVAILABLE")))
        rows, complete, _ = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual([r["status"] for r in rows], ["NOT_ATTEMPTED"] * 3)
        self.assertFalse(complete)

    def test_timeout_stops_before_next_sample_without_retry(self):
        ticks = iter((0, 1, 40000))
        self.run_fake(clock=lambda: next(ticks))
        rows, complete, _ = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual([r["status"] for r in rows], ["SUCCESS", "NOT_ATTEMPTED", "NOT_ATTEMPTED"])
        self.assertFalse(complete)

    def test_keyboard_interrupt_preserves_interrupted_and_tail(self):
        class Interrupted(FakeBackend):
            def generate(self, row, cap):
                raise KeyboardInterrupt()
        engine.execute(self.root / "raw", cohort.opaque_rows(ROWS), 3, Interrupted)
        rows, complete, _ = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual([r["status"] for r in rows], ["INTERRUPTED", "NOT_ATTEMPTED", "NOT_ATTEMPTED"])
        self.assertFalse(complete)

    def test_torn_bytes_preserved_and_detected_without_repair(self):
        self.run_fake(failure=1)
        torn = self.root / "raw/sample-000001/torn.json"
        torn.write_bytes(b'{"unfinished":')
        before = torn.read_bytes()
        audit.seal_raw(self.root)
        audit.verify_custody(self.root)
        rows, complete, integrity = audit.raw_rows(self.root, ROWS, TOK)
        self.assertEqual(rows[1]["status"], "INTERRUPTED")
        self.assertEqual(torn.read_bytes(), before)
        self.assertFalse(complete)
        self.assertIn("PARTIAL", integrity)

    def test_custody_blocks_tamper_or_extra_raw_before_label_read(self):
        self.run_fake()
        audit.seal_raw(self.root)
        audit.verify_custody(self.root)
        (self.root / "raw/extra.txt").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "CUSTODY_CHANGED"):
            audit.verify_custody(self.root)


class SupervisorTests(CPUCase):
    def test_authorized_synthetic_order_export_and_partial_coverage(self):
        events = []
        class Ops(orchestrate.Operations):
            def check_inputs(self, rows):
                return {"kind": "SYNTHETIC_METADATA"}
            def preflight(self):
                events.append("preflight")
                return {"kind": "SYNTHETIC_CPU_ONLY"}
            def software(self):
                events.append("software")
            def worker(self, mode):
                events.append(mode)
                if mode == "inference":
                    engine.execute(self.evidence / "raw", cohort.opaque_rows(ROWS), 3,
                                   lambda index: FakeBackend(index, failure=1))
                return {"status": "RETURNED"}
            def provision(self):
                events.append("checkpoint")
            def stage(self, rows):
                events.append("stage")
                self_outer.assertEqual(rows, ROWS)
            def evaluate(self):
                events.append("cpu")
                audit.verify_custody(self.evidence)
                rows, completed, _ = audit.raw_rows(self.evidence, ROWS, TOK)
                meta = {r["sample_id"]: {"level": "Level04", "domain": "synthetic", "group": str(i)} for i, r in enumerate(ROWS)}
                evaluation = audit.metrics(rows, meta, completed)
                audit.export(self.evidence / "report", rows, meta, evaluation, {"results": rows})
                return evaluation
        self_outer = self
        write(self.root / contract.AUTHORITY, approved())
        out = self.root / "out"
        out.mkdir()
        with patch.object(cohort, "inference", return_value=[ROWS] * 4):
            result = orchestrate.run(self.root, self.root / "work", out, source(), "qwen3", 0, operations_factory=Ops)
        self.assertEqual(events, ["preflight", "stage", "software", "inspect", "checkpoint", "inference", "cpu"])
        self.assertEqual(result["status"], "PARTIAL")
        counts = result["coverage"]["status_counts"]
        self.assertEqual((counts["SUCCESS"], counts["TECHNICAL_ERROR"], counts["NOT_ATTEMPTED"]), (1, 1, 1))
        self.assertEqual(len(list(out.glob("*.tar.gz"))), 1)

    def test_cuda_admission_failure_prevents_checkpoint_after_verified_staging(self):
        events = []
        class Ops(orchestrate.Operations):
            def check_inputs(self, rows):
                return {"kind": "SYNTHETIC_METADATA"}
            def preflight(self):
                return {"kind": "FAKE_CPU"}
            def software(self):
                pass
            def worker(self, mode):
                events.append(mode)
                raise RuntimeError("FAKE_CUDA_ADMISSION_FAILURE")
            def provision(self):
                raise AssertionError("WEIGHT_PROVISION_AFTER_FAILURE")
            def stage(self, rows):
                events.append("stage")
            def evaluate(self):
                raise RuntimeError("NO_RUNTIME_TOKENIZER_AVAILABLE")
        write(self.root / contract.AUTHORITY, approved())
        out = self.root / "out"
        out.mkdir()
        with patch.object(cohort, "inference", return_value=[ROWS] * 4):
            result = orchestrate.run(self.root, self.root / "work", out, source(), "qwen3", 0, operations_factory=Ops)
        self.assertEqual(events, ["stage", "inspect"])
        self.assertTrue(result["dataset_read"])
        self.assertFalse(result["inference_started"])

    def test_staging_reads_only_exact_images_and_removes_gt_names(self):
        locator = "DATA_PATH/train/Annotations/Normal_data/power-Level04-example/image.jpg"
        image = self.root / "dataset" / locator
        image.parent.mkdir(parents=True)
        image.write_bytes(b"SYNTHETIC_IMAGE_BYTES_NOT_A_REAL_JPEG")
        image.with_suffix(".json").write_bytes(b"FORBIDDEN_ANNOTATION")
        rows = [{"sample_id": "power-Level04-example", "image_locator": locator, "image_sha256": sha256(image)}]
        staged = self.root / "staged"
        orchestrate.stage_images(self.root / "dataset", rows, staged, self.root / "staging-receipt")
        self.assertEqual((staged / "000000.image").read_bytes(), image.read_bytes())
        self.assertEqual(json.loads((staged / "request.json").read_bytes()), cohort.opaque_rows(rows))
        self.assertEqual(sorted(p.name for p in staged.iterdir()), ["000000.image", "request.json"])
        self.assertTrue(Journal(self.root / "staging-receipt").verify())

    def test_staging_checksum_failure_keeps_sample_identity_and_stops(self):
        locator = "DATA_PATH/train/Annotations/Normal_data/synthetic/image.jpg"
        image = self.root / "dataset" / locator
        image.parent.mkdir(parents=True)
        image.write_bytes(b"SYNTHETIC_BAD_HASH")
        rows = [{"sample_id": "synthetic-0", "image_locator": locator, "image_sha256": "0" * 64}]
        evidence = self.root / "evidence"
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            orchestrate.stage_images(self.root / "dataset", rows, self.root / "staged", evidence / "input-staging")
        result = orchestrate.execution_inventory(evidence, rows)
        self.assertEqual(result[0]["status"], "TECHNICAL_ERROR")
        self.assertEqual(result[0]["sample_id"], "synthetic-0")
        self.assertFalse((self.root / "staged/000000.image").exists())


def metric_row(sid, score_value, predicted="Level03"):
    logs = core.distribution([score_value, score_value, score_value, 0.0])["log_probabilities"]
    from safeshift.ls1.evaluate import anomaly_log_odds
    return {**pending(sid, attempted=True, persisted=True), "parsed": True, "status": "SUCCESS",
            "score": anomaly_log_odds(logs), "details": {"log_probabilities": logs}, "generated_label": predicted}


class MetricTests(unittest.TestCase):
    def fixture(self):
        metadata = {str(i): {"level": "Level01" if i % 2 else "Level04", "domain": "power", "group": str(i)} for i in range(8)}
        rows = [metric_row(str(i), float(i)) for i in range(8)]
        return rows, metadata

    def test_pooled_auroc_is_recomputed_not_shard_average(self):
        rows, meta = self.fixture()
        shards = [(contract.unit("qwen3", i), rows[i*2:i*2+2], True, "PASS") for i in range(4)]
        pooled = audit.pool(shards, meta)
        result = audit.metrics(pooled, meta, True)
        mean_shards = sum(audit.metrics(s[1], {r["sample_id"]: meta[r["sample_id"]] for r in s[1]}, True)["overall"]["auroc_pa3"]["value"] for s in shards) / 4
        self.assertNotEqual(result["overall"]["auroc_pa3"]["value"], mean_shards)
        self.assertIsNone(result["pa3_threshold"])

    def test_duplicate_missing_mixed_shards_and_result_ids_rejected(self):
        rows, meta = self.fixture()
        good = [(contract.unit("qwen3", i), rows[i*2:i*2+2], True, "PASS") for i in range(4)]
        variants = [good[:3], [good[0], good[0], good[2], good[3]]]
        mixed = deepcopy(good)
        mixed[0][0]["model"] = "internvl3"
        variants.append(mixed)
        duplicate = deepcopy(good)
        duplicate[0][1][0]["sample_id"] = "1"
        variants.append(duplicate)
        for bad in variants:
            with self.assertRaises(ValueError):
                audit.pool(bad, meta)

    def test_full_coverage_and_common_valid_id_intersections(self):
        rows, meta = self.fixture()
        models = {m: deepcopy(rows) for m in ("qwen2_5", "qwen3", "internvl3")}
        models["qwen3"][0] = pending("0")
        models["internvl3"][1] = pending("1")
        result = audit.comparisons(models, meta)
        common = result["same_ids"]["internvl3|qwen2_5|qwen3"]
        self.assertEqual(common["n"], 6)
        self.assertEqual(common["coverage_of_planned"], 0.75)
        self.assertEqual(result["full_cohort"]["qwen3"]["overall"]["coverage"]["planned"], 8)
        self.assertEqual(result["full_cohort"]["qwen3"]["overall"]["coverage"]["scored"], 7)

    def test_zero_coverage_single_class_ties_and_accuracies(self):
        rows, meta = self.fixture()
        missing = [pending(str(i)) for i in range(8)]
        self.assertIsNone(audit.metrics(missing, meta, False)["overall"]["auroc_pa3"]["value"])
        ties = [metric_row(str(i), 0.0, "Level04") for i in range(8)]
        m = audit.metrics(ties, meta, True)["overall"]
        self.assertEqual(m["auroc_pa3"]["value"], 0.5)
        self.assertEqual(m["generated_binary_on_score_valid_ids"]["accuracy"], 0.5)
        single = {k: {**v, "level": "Level04"} for k, v in meta.items()}
        self.assertIsNone(audit.metrics(rows, single, True)["overall"]["auroc_pa3"]["value"])


class SourceTests(old.SourceTests):
    """Run the existing real-Git source/authority/merge fault tests on the new root."""
    def setUp(self):
        self.enterContext(patch.object(old, "boot", boot))
        self.enterContext(patch.object(old, "AUTHORITY", contract.AUTHORITY))
        self.enterContext(patch.object(old, "LOCK", contract.LOCK))
        super().setUp()


class NotebookTests(unittest.TestCase):
    def test_worker_source_hashing_never_opens_label_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            code = root / "code.py"
            code.write_bytes(b"# synthetic\n")
            gt = root / "data/manifests/labels.json"
            gt.parent.mkdir(parents=True)
            gt.write_bytes(b'{"fixture":"NO_REAL_LABELS"}')
            lock = {"schema": "hnlo-source-lock-v1", "base_sha": contract.BASE_SHA, "files": [
                {"path": "code.py", "sha256": sha256(code)},
                {"path": "data/manifests/labels.json", "sha256": sha256(gt)}]}
            write(root / contract.LOCK, lock)
            payload = hashlib.sha256(boot.canonical(lock)).hexdigest()
            names = ["code.py", "data/manifests/labels.json", contract.AUTHORITY, contract.LOCK]
            original = Path.read_bytes
            def no_gt(path):
                if path == gt:
                    raise AssertionError("WORKER_LABEL_FILE_READ")
                return original(path)
            with patch.object(boot, "git", side_effect=lambda repo, *args: "\0".join(names) if args[0] == "ls-files" else ""), \
                 patch.object(Path, "read_bytes", no_gt):
                boot.verify_payload(root, payload, worker=True)
                with self.assertRaisesRegex(AssertionError, "LABEL_FILE_READ"):
                    boot.verify_payload(root, payload)

    def test_eight_fixed_units_compile_and_bind_reviewed_payload(self):
        lock = json.loads((ROOT / contract.LOCK).read_bytes())
        expected = hashlib.sha256(boot.canonical(lock)).hexdigest()
        for model in ("qwen3", "internvl3"):
            for shard in range(4):
                name = f"notebooks/SafeShift_HNLO_TRAIN_{model}_SHARD{shard}_V4.ipynb"
                notebook = json.loads((ROOT / name).read_bytes())
                cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
                self.assertEqual(len(cells), 1)
                code = "".join(cells[0]["source"])
                module = ast.parse(code)
                compile(module, name, "exec")
                self.assertTrue(code.endswith(f'result = bootstrap("{model}", {shard})\n'))
                self.assertIn('PAYLOAD_SHA256 = "' + expected + '"', code)
                self.assertEqual(cells[0]["outputs"], [])
                self.assertIsNone(cells[0]["execution_count"])
        for row in lock["files"]:
            data = (ROOT / row["path"]).read_bytes()
            if row["path"] in boot.NOTEBOOK_PATHS:
                data = boot.notebook_bytes(data)
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"], row["path"])

    def test_historical_code_and_release_bytes_unchanged(self):
        import subprocess
        protected = ["safeshift/runners", "safeshift/ls1", "safeshift/pa3", "safeshift/diagnostics/one_click",
                     "safeshift/diagnostics/internvl3_hnlo", "configs/pa3", "data/manifests", "prompts"]
        diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", contract.BASE_SHA, "--", *protected])
        self.assertEqual(diff, b"")


if __name__ == "__main__":
    unittest.main()
