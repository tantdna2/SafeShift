"""Synthetic fixtures and fake native backend only; no ML imports or data access."""

import builtins
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import w2_moondream_external_gate as gate
from safeshift.protocol.gate import GiantBoxReview, evaluate_gate
from safeshift.runners import moondream2 as runner
from safeshift.runners import storage
from tests import test_moondream_runner_smoke as fakes

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40


def native(box):
    return {"objects": [dict(zip(gate.COORDINATES, box))]}


class AdaptationTests(unittest.TestCase):
    def test_one_box_is_canonical_with_clamp_visible_and_extra_fields_lossless(self):
        value = native([-0.1, 0.2, 0.3, 1.2])
        value["uninterpreted"] = [True, None, -0.0]
        raw = runner.serialize_native(value)
        decoded = runner.deserialize_native(raw)
        parsed, detail = gate.adapt_native(decoded)
        self.assertTrue(parsed.success)
        self.assertEqual(parsed.value.bbox, (0, 0.2, 0.3, 1))
        self.assertEqual(detail["raw_coordinates"], [-0.1, 0.2, 0.3, 1.2])
        self.assertEqual(detail["normalized_coordinates"], parsed.value.bbox)
        self.assertTrue(detail["clamped"])
        self.assertEqual(raw, runner.serialize_native(decoded))

    def test_zero_and_multiple_objects_never_cherry_pick(self):
        box = native([0.1, 0.2, 0.3, 0.4])["objects"][0]
        for objects in ([], [box, box], [box, {"malformed": True}]):
            parsed, detail = gate.adapt_native({"objects": objects})
            self.assertEqual(parsed.status, "SCHEMA_ERROR")
            self.assertFalse(parsed.response_schema_valid)
            self.assertIsNone(parsed.value)
            self.assertIsNone(detail["normalized_coordinates"])

    def test_malformed_nonfinite_and_point_outputs_fail(self):
        values = [None, [], {"objects": {}}, {"points": [{"x": 0.2, "y": 0.4}]},
                  {"objects": [{"x": 0.2, "y": 0.4}]}, {"objects": [None]}]
        for bad in (None, True, "0.1", float("nan"), float("inf"), -float("inf"), 10**400):
            values.append(native([bad, 0.2, 0.3, 0.4]))
        for value in values:
            with self.subTest(value=value):
                parsed, detail = gate.adapt_native(value)
                self.assertFalse(parsed.success)
                self.assertIsNone(parsed.value)
                json.dumps(detail, allow_nan=False)

    def test_reversed_and_degenerate_boxes_not_repaired(self):
        for box in ([0.4, 0.2, 0.1, 0.3], [0.1, 0.4, 0.3, 0.2], [0, 0, 0, 1], [2, 2, 3, 3]):
            parsed, detail = gate.adapt_native(native(box))
            self.assertEqual(parsed.status, "COORDINATE_ERROR")
            self.assertEqual(detail["raw_coordinates"], box)
            self.assertIsNone(detail["normalized_coordinates"])


class GateTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.repo = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        plan, self.runtime = gate.load_gate_plan(ROOT)
        paths = [gate.PLAN, gate.MANIFEST, gate.PROVENANCE, *plan["protected_source_sha256_lf"]]
        paths += [f"tests/fixtures/pre_freeze/frozen_external_gate/{c}.png" for c in gate.CASE_IDS]
        for path in paths:
            dest = self.repo / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, dest)
        self.cases, _ = gate.verify_suite(self.repo)
        self.values = {c.case_id: native(c.target_gt_bbox) for c in self.cases}
        self.cache = self.repo / gate.CACHE_DIR
        self.cache.mkdir(parents=True)
        self.artifact = self.repo / gate.ARTIFACT_ROOT
        self.stack.enter_context(patch.dict(gate.os.environ, {"CUDA_VISIBLE_DEVICES": "0"}))
        for name, value in (("system", "Linux"), ("machine", "x86_64"), ("python_version", "3.11.11")):
            self.stack.enter_context(patch.object(gate.platform, name, return_value=value))
        self.git = self.stack.enter_context(patch.object(gate.subprocess, "check_output",
            side_effect=lambda cmd, **kw: COMMIT if cmd[1] == "rev-parse" else ""))
        # Real runner orchestration, fake native model/tensors; never native ML.
        self.stack.enter_context(patch.object(runner, "deny_network_permanently"))
        self.stack.enter_context(patch.object(runner, "require_offline"))
        self.stack.enter_context(patch.object(runner, "_load_claimed", False))
        self.verify = self.stack.enter_context(patch.object(runner, "verify_snapshot",
            return_value={"manifest_sha256": "b" * 64, "local_bytes_verified": True}))
        self.model = fakes.fake_model()
        self.events = []
        @contextmanager
        def installed():
            self.events.extend({"boundary": b} for b in ("bridge_cpu", "transfer", "vision_consumption"))
            yield
        self.binding = SimpleNamespace(valid=True, events=self.events, installed=installed)
        self.backend = SimpleNamespace(
            software=dict(self.runtime["software"]),
            torch=SimpleNamespace(**vars(fakes.TORCH), cuda=SimpleNamespace(
                reset_peak_memory_stats=Mock(), max_memory_allocated=lambda d: 100,
                max_memory_reserved=lambda d: 200)),
            image=SimpleNamespace(open=Mock(return_value=SimpleNamespace(load=Mock()))),
            metadata=Mock(return_value={"cuda_available": True, "gpu_count": 1, "name": "Tesla T4",
                "compute_capability": [7, 5], "total_memory": 15636037632}),
            load=Mock(return_value=(self.model, self.binding)))
        self.model.query = Mock(side_effect=AssertionError("query forbidden"))
        self.active = None
        def detect(image, prompt, settings):
            case = next(c for c in self.cases if c.case_id == self.active)
            self.assertEqual(prompt, case.target_query)
            self.assertEqual(settings, {"max_objects": 50, "variant": None})
            return self.values[self.active]
        self.model.detect = Mock(side_effect=detect)
        self.factory = Mock(side_effect=self.construct)
        original_import, original_open = builtins.__import__, Path.open
        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers", "huggingface_hub", "tokenizers"}:
                raise AssertionError("ML import forbidden in fake tests: " + name)
            return original_import(name, *args, **kwargs)
        def guarded_open(path, *args, **kwargs):
            text = path.as_posix().lower()
            if "/data/raw/" in text or "inspecsafe" in text:
                raise AssertionError("benchmark access forbidden")
            return original_open(path, *args, **kwargs)
        self.stack.enter_context(patch.object(builtins, "__import__", side_effect=guarded_import))
        self.stack.enter_context(patch.object(Path, "open", guarded_open))

    def construct(self, *paths):
        self.assertTrue((self.artifact / "ATTEMPT.json").is_file())
        self.assertTrue((self.artifact / "result.json").is_file())
        self.assertEqual(paths[0], self.cache / "models--vikhyatk--moondream2" / "snapshots" / gate.REVISION)
        self.assertEqual(paths[1], self.cache / "models--moondream--starmie-v1" / "snapshots" / gate.TOKENIZER_REVISION)
        self.runner = runner.Moondream2Runner(*paths, backend_factory=lambda: self.backend)
        original = self.runner.prepare_input
        def prepare(request, ctx):
            self.active = ctx.call_id
            self.assertEqual(request.task, gate.Task.GROUNDING)
            return original(request, ctx)
        self.runner.prepare_input = prepare
        return self.runner

    def run_fake(self, **kwargs):
        return gate.run_gate(repo=self.repo, run_id="moondream-external-gate-fake",
            expected_commit=COMMIT, venue_network_disabled=True, runner_factory=self.factory, **kwargs)

    def assert_consumed(self):
        before = {p.relative_to(self.artifact): p.read_bytes() for p in self.artifact.rglob("*") if p.is_file()}
        count = self.factory.call_count
        for name in ("fake", "another-id"):
            with self.assertRaises(FileExistsError):
                gate.run_gate(repo=self.repo, run_id="moondream-external-gate-" + name,
                    expected_commit=COMMIT, venue_network_disabled=True, runner_factory=self.factory)
        self.assertEqual(self.factory.call_count, count)
        self.assertEqual(before, {p.relative_to(self.artifact): p.read_bytes()
                                 for p in self.artifact.rglob("*") if p.is_file()})

    def test_exact_order_hashes_native_calls_pending_review_and_one_attempt(self):
        self.assertEqual(tuple(c.case_id for c in self.cases), ("A_1", "A_2", "B_1", "B_2", "C_1", "C_2", "D_1", "D_2"))
        for path, digest in ((gate.MANIFEST, gate.MANIFEST_SHA256), (gate.PROVENANCE, gate.PROVENANCE_SHA256)):
            self.assertEqual(hashlib.sha256((self.repo / path).read_bytes()).hexdigest(), digest)
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_PENDING_REVIEW")
        self.assertTrue(result["completed_gate"])
        self.assertEqual(result["not_attempted_case_ids"], [])
        self.assertEqual([c["case_id"] for c in result["calls"]], list(gate.CASE_IDS))
        self.assertEqual(self.model.detect.call_count, 8)
        self.model.query.assert_not_called()
        self.backend.load.assert_called_once()
        self.assertEqual(self.verify.call_count, 2)
        self.assertEqual(len(result["runtime"]["state_audits"]), 17)
        self.assertTrue(result["gate"]["systematic_tracking"])
        self.assertTrue(all(r["giant_box_review"]["status"] == "PENDING" for r in result["gate"]["cases"]))
        self.assertTrue((self.artifact / "giant_review.template.json").is_file())
        self.assert_consumed()

    def test_raw_metadata_checksum_before_deserialize_adapt_evaluate(self):
        original = gate.deserialize_native
        seen = []
        def decode(raw):
            paths = list(self.artifact.glob("raw/*/metadata.json"))
            self.assertEqual(len(paths), len(seen) + 1)
            metadata = next(json.loads(p.read_bytes()) for p in paths
                            if json.loads(p.read_bytes())["sample_id"] == self.active)
            ref = metadata["raw_output"]
            self.assertEqual((self.repo / ref["path"]).read_bytes(), raw)
            self.assertEqual(ref["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            self.assertEqual(metadata["git_commit_sha"], COMMIT)
            self.assertEqual(metadata["prompt"], next(c.target_query for c in self.cases if c.case_id == self.active))
            seen.append(self.active)
            return original(raw)
        def evaluate(*args, **kwargs):
            self.assertEqual(seen, list(gate.CASE_IDS))
            self.assertIsNone(kwargs["reviews"])
            return evaluate_gate(*args, **kwargs)
        with patch.object(gate, "deserialize_native", side_effect=decode), \
                patch.object(gate, "evaluate_gate", side_effect=evaluate):
            self.assertEqual(self.run_fake()["status"], "GATE_PENDING_REVIEW")

    def test_swap_tracking_failure(self):
        self.values["A_1"], self.values["A_2"] = self.values["A_2"], self.values["A_1"]
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_FAIL")
        self.assertFalse(result["gate"]["systematic_tracking"])

    def test_full_image_rejected(self):
        self.values["A_1"] = native([0, 0, 1, 1])
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_FAIL")
        self.assertTrue(result["gate"]["cases"][0]["full_image"])

    def test_center_outside_target_rejected(self):
        self.values["A_1"] = native([0, 0, 0.1, 0.1])
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_FAIL")
        self.assertFalse(result["gate"]["cases"][0]["center_in_target"])

    def test_distractor_center_included_rejected(self):
        self.values["A_1"] = native([0, 0.375, 0.76, 0.625])
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_FAIL")
        self.assertFalse(result["gate"]["cases"][0]["excludes_distractor_center"])

    def test_iou_and_area_have_no_new_threshold_and_giant_review_is_human(self):
        predictions = {c.case_id: gate.adapt_native(self.values[c.case_id])[0] for c in self.cases}
        for box in ([0.2499, 0.4999, 0.2501, 0.5001], [0, 0, 0.74, 1]):
            predictions["A_1"] = gate.adapt_native(native(box))[0]
            self.assertEqual(evaluate_gate(self.repo, self.cases, predictions).status, "PENDING_REVIEW")
        reviews = {c.case_id: GiantBoxReview("NO_GIANT", "fake-human", "synthetic test only") for c in self.cases}
        self.assertEqual(evaluate_gate(self.repo, self.cases, predictions, reviews).status, "PASS")
        reviews["A_1"] = GiantBoxReview("GIANT", "fake-human", "test only")
        self.assertEqual(evaluate_gate(self.repo, self.cases, predictions, reviews).status, "FAIL")
        del reviews["A_1"]
        self.assertEqual(evaluate_gate(self.repo, self.cases, predictions, reviews).status, "PENDING_REVIEW")

    def test_invalid_native_output_is_completed_gate_fail_not_retry(self):
        self.values["A_1"] = {"objects": []}
        self.values["A_2"]["objects"] *= 2
        self.values["B_1"] = native([float("nan"), 0, 1, 1])
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_FAIL")
        self.assertTrue(result["completed_gate"])
        self.assertEqual(self.model.detect.call_count, 8)
        self.assertTrue(all(not c["schema_valid"] for c in result["gate"]["cases"][:3]))
        self.assert_consumed()

    def test_failure_mid_suite_stops_remaining_cases_and_consumes(self):
        original = self.model.detect.side_effect
        def fail(*args, **kwargs):
            if self.active == "A_2":
                raise RuntimeError("private error text")
            return original(*args, **kwargs)
        self.model.detect.side_effect = fail
        result = self.run_fake()
        self.assertEqual(result["status"], "GATE_EXECUTION_FAILURE")
        self.assertFalse(result["completed_gate"])
        self.assertEqual(result["not_attempted_case_ids"], list(gate.CASE_IDS[2:]))
        self.assertIsNone(result["gate"])
        self.assertIsNotNone(result["calls"][0]["raw"])
        self.assertIsNone(result["calls"][1]["raw"])
        self.assertEqual(self.model.detect.call_count, 2)
        self.assertNotIn("private error text", json.dumps(result))
        self.assert_consumed()

    def test_interruption_consumes_and_records_not_attempted(self):
        self.backend.load.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_fake()
        result = json.loads((self.artifact / "result.json").read_bytes())
        self.assertFalse(result["completed_gate"])
        self.assertEqual(result["not_attempted_case_ids"], list(gate.CASE_IDS))
        self.assertEqual(result["failure"]["type"], "KeyboardInterrupt")
        self.assert_consumed()

    def test_post_native_failure_preserves_partial_without_adaptation(self):
        with patch.object(runner, "audit_model_state", side_effect=[[], [], ValueError("fake audit")]), \
                patch.object(gate, "adapt_native") as adapt:
            result = self.run_fake()
        adapt.assert_not_called()
        self.assertTrue(result["calls"][0]["partial"])
        self.assertIsNotNone(result["calls"][0]["raw"])
        self.assertEqual(result["not_attempted_case_ids"], list(gate.CASE_IDS[1:]))
        self.assert_consumed()

    def test_raw_metadata_failure_never_deserializes(self):
        original = storage._write_new
        def fail(path, content):
            if path.name == "metadata.json":
                raise OSError("fake persistence failure")
            return original(path, content)
        with patch.object(storage, "_write_new", side_effect=fail), patch.object(gate, "deserialize_native") as decode:
            result = self.run_fake()
        decode.assert_not_called()
        self.assertEqual(result["failure"]["stage"], "raw_preserve")
        self.assert_consumed()

    def test_corrupt_persisted_raw_never_deserializes(self):
        original = storage.FileRawStore.preserve
        def corrupt(store, raw, provenance):
            ref = original(store, raw, provenance)
            (store.repo / ref.path).write_bytes(b"corrupt")
            return ref
        with patch.object(storage.FileRawStore, "preserve", corrupt), patch.object(gate, "deserialize_native") as decode:
            result = self.run_fake()
        decode.assert_not_called()
        self.assertEqual(result["status"], "GATE_EXECUTION_FAILURE")
        self.assert_consumed()

    def test_wrong_commit_dirty_checkout_and_absent_cache_prevent_runtime(self):
        for head, dirty in (("b" * 40, ""), (COMMIT, " M x.py"), (COMMIT, "?? x.py")):
            self.git.side_effect = [head, dirty]
            with self.assertRaisesRegex(ValueError, "CLEAN_EXACT"):
                self.run_fake()
        self.git.side_effect = [COMMIT, ""]
        self.cache.rmdir()
        with self.assertRaisesRegex(ValueError, "EXISTING_CACHE"):
            self.run_fake()
        self.factory.assert_not_called()
        self.assertFalse(self.artifact.exists())

    def test_mask_os_arch_python_requirements_before_runtime(self):
        for mask in ("", "1", "0,1"):
            with patch.dict(gate.os.environ, {"CUDA_VISIBLE_DEVICES": mask}), self.assertRaises(ValueError):
                self.run_fake()
        for key, value in (("system", "Windows"), ("machine", "aarch64"), ("python_version", "3.11.9")):
            with patch.object(gate.platform, key, return_value=value), self.assertRaises(ValueError):
                self.run_fake()
        self.factory.assert_not_called()

    def test_missing_network_attestation_and_bad_run_identity_prevent_runtime(self):
        for run_id, commit, venue in (("moondream-external-gate-fake", COMMIT, False),
                ("../escape", COMMIT, True), ("moondream-external-gate-fake", "main", True)):
            with self.assertRaises(ValueError):
                gate.run_gate(repo=self.repo, run_id=run_id, expected_commit=commit,
                    venue_network_disabled=venue, runner_factory=self.factory)
        self.factory.assert_not_called()

    def test_wrong_software_consumes_without_native_load(self):
        self.backend.software["torch"] = "wrong"
        result = self.run_fake()
        self.assertEqual(result["failure"]["stage"], "initialize")
        self.backend.load.assert_not_called()
        self.assert_consumed()

    def test_two_visible_gpus_consumes_without_native_load(self):
        self.backend.metadata.return_value["gpu_count"] = 2
        self.assertEqual(self.run_fake()["failure"]["stage"], "initialize")
        self.backend.load.assert_not_called()
        self.assert_consumed()

    def test_snapshot_mismatch_consumes_without_native_load(self):
        self.verify.side_effect = ValueError("synthetic cache corruption")
        self.assertEqual(self.run_fake()["failure"]["stage"], "load")
        self.backend.load.assert_not_called()
        self.model.detect.assert_not_called()
        self.assert_consumed()

    def test_frozen_files_and_protected_source_tamper_rejected(self):
        for relative in (gate.PLAN, gate.MANIFEST, gate.PROVENANCE, self.cases[0].image_path,
                         "safeshift/runners/moondream2.py"):
            path = self.repo / relative
            original = path.read_bytes()
            path.write_bytes(original + b"changed")
            with self.assertRaises(ValueError):
                self.run_fake()
            path.write_bytes(original)
        self.factory.assert_not_called()

    def test_case_order_and_inspecsafe_inaccessible_even_if_hash_guard_mocked(self):
        manifest = json.loads((self.repo / gate.MANIFEST).read_bytes())
        for rows in (list(reversed(manifest["cases"])), manifest["cases"][:-1],
                     [{**manifest["cases"][0], "image_path": "data/raw/InspecSafe-V1/a.png"}, *manifest["cases"][1:]]):
            content = json.dumps({**manifest, "cases": rows}).encode()
            (self.repo / gate.MANIFEST).write_bytes(content)
            with patch.object(gate, "MANIFEST_SHA256", hashlib.sha256(content).hexdigest()), self.assertRaises(ValueError):
                self.run_fake()
        self.factory.assert_not_called()

    def test_evaluator_cannot_grant_automatic_pass(self):
        def unexpected(*args, **kwargs):
            return replace(evaluate_gate(*args, **kwargs), status="PASS")
        with patch.object(gate, "evaluate_gate", side_effect=unexpected):
            result = self.run_fake()
        self.assertEqual(result["status"], "GATE_EXECUTION_FAILURE")
        self.assertFalse(result["completed_gate"])


if __name__ == "__main__":
    unittest.main()
