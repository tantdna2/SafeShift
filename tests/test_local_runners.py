"""W2.6A contracts using handcrafted bytes only; no model or gate execution."""

import ast
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.protocol.schema import Classification, Grounding
from safeshift.runners.contracts import (
    AdaptedOutput, ErrorCode, GenerationFailure, ModelIdentity, ParseStatus,
    Participation, Request, Roles, RunContext, SpatialKind, Task, execute_call,
)
from safeshift.runners.dummy import DummyAdapter, DummyCase, DummyRunner
from safeshift.runners.storage import FileRawStore


FIXED_TIME = datetime(2026, 9, 21, tzinfo=timezone.utc)


def context(call_id="call-1", **changes):
    return replace(RunContext(
        run_id="unit-run", call_id=call_id, decoding={"mode": "dummy-fixed", "seed": 7},
        preprocessing={"mode": "identity"}, precision="NOT_APPLICABLE_DUMMY",
        quantization="NONE_DUMMY", device={"kind": "dummy-no-compute"},
        software_versions={"runtime": "dummy-v1"}, git_commit_sha="a" * 40,
        command="python -m unittest tests.test_local_runners", source_kind="handcrafted_dummy",
        seed=7, input_provenance={"source_version": "synthetic-v1"},
    ), **changes)


def request(task=Task.CLASSIFICATION):
    return Request(task, "opaque/sample:1", "synthetic-input", b"handcrafted input",
                   "dummy-" + task.value, "Handcrafted " + task.value + " task.")


class LocalRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.store = FileRawStore(self.repo)
        self.adapter = DummyAdapter()

    def execute(self, case=DummyCase.BOX, task=Task.CLASSIFICATION, *, runner=None,
                adapter=None, store=None, ctx=None, req=None):
        return execute_call(runner or DummyRunner(case), adapter or self.adapter,
                            store or self.store, req or request(task), ctx or context(task.value),
                            clock=lambda: FIXED_TIME)

    def pair(self, case, **kwargs):
        return self.execute(case, **kwargs), self.execute(case, Task.GROUNDING, **kwargs)

    def read_raw(self, result):
        return (self.repo / result.raw_output.path).read_bytes()

    def test_valid_classification_and_bbox_use_existing_canonical_types(self):
        classification, grounding = self.pair(DummyCase.BOX)
        self.assertEqual(classification.canonical, Classification("Level04"))
        self.assertIsInstance(grounding.canonical, Grounding)
        self.assertEqual(grounding.canonical.hazards[0].evidence[0].bbox, (.1, .2, .3, .4))
        self.assertEqual(grounding.spatial_kind, SpatialKind.NATIVE_BOX)
        self.assertIsNone(classification.error)
        self.assertIsNone(grounding.error)
        # Operability is not capability qualification or a final role assignment.
        self.assertEqual(grounding.participation, Participation.PENDING)

    def test_point_is_preserved_without_box_or_canonical_metric_value(self):
        classification, grounding = self.pair(DummyCase.POINT)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(grounding.spatial_kind, SpatialKind.NATIVE_POINT)
        self.assertEqual(grounding.parse_status, ParseStatus.UNSUPPORTED)
        self.assertEqual(grounding.error.code, ErrorCode.UNSUPPORTED_GROUNDING)
        self.assertIsNone(grounding.canonical)
        self.assertEqual(grounding.native_evidence, json.loads(self.read_raw(grounding)))
        self.assertEqual(grounding.native_evidence["native_points"], [[.25, .75]])
        self.assertNotIn("bbox", json.dumps(asdict(grounding)))

    def test_no_spatial_output_is_not_a_malformed_box(self):
        classification, grounding = self.pair(DummyCase.NONE)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(grounding.spatial_kind, SpatialKind.NONE)
        self.assertEqual(grounding.error.code, ErrorCode.UNSUPPORTED_GROUNDING)
        self.assertIsNone(grounding.canonical)

    def test_malformed_grounding_does_not_fail_classification(self):
        classification, grounding = self.pair(DummyCase.MALFORMED)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertIsNone(classification.error)
        self.assertEqual(grounding.parse_status, ParseStatus.INVALID)
        self.assertEqual(grounding.error.code, ErrorCode.MALFORMED_GROUNDING)
        self.assertEqual(grounding.spatial_kind, SpatialKind.MALFORMED)
        self.assertIsNone(grounding.canonical)

    def test_invalid_classification_is_distinct_and_grounding_can_succeed(self):
        classification, grounding = self.pair(DummyCase.INVALID_CLASSIFICATION)
        self.assertEqual(classification.error.code, ErrorCode.INVALID_CLASSIFICATION)
        self.assertEqual(classification.parse_status, ParseStatus.INVALID)
        self.assertEqual(grounding.parse_status, ParseStatus.SUCCESS)
        self.assertIsNone(grounding.error)

    def test_generation_failure_is_task_local_and_has_no_fabricated_raw(self):
        classification, grounding = self.pair(DummyCase.GENERATION_FAILURE)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(grounding.error.code, ErrorCode.GENERATION_FAILURE)
        self.assertEqual(grounding.parse_status, ParseStatus.NOT_ATTEMPTED)
        self.assertIsNone(grounding.raw_output)

    def test_parser_failure_retains_raw_and_does_not_fail_other_task(self):
        classification, grounding = self.pair(DummyCase.PARSER_FAILURE)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(grounding.error.code, ErrorCode.PARSER_FAILURE)
        self.assertEqual(grounding.parse_status, ParseStatus.FAILED)
        self.assertEqual(self.read_raw(grounding), b"DUMMY_PARSER_EXCEPTION")

    def test_participation_roles_are_independent_and_nonparticipant_is_skipped(self):
        roles = Roles(Participation.PARTICIPATING, Participation.NOT_PARTICIPATING)
        classification = self.execute(ctx=context("c", roles=roles))
        runner = DummyRunner()
        grounding = self.execute(task=Task.GROUNDING, runner=runner, ctx=context("g", roles=roles))
        self.assertEqual(classification.participation, Participation.PARTICIPATING)
        self.assertEqual(classification.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(grounding.participation, Participation.NOT_PARTICIPATING)
        self.assertEqual(grounding.parse_status, ParseStatus.NOT_ATTEMPTED)
        self.assertIsNone(grounding.error)
        self.assertEqual(runner.events, [])

    def test_grounding_error_does_not_rewrite_caller_roles(self):
        roles = Roles(Participation.PARTICIPATING, Participation.PARTICIPATING)
        result = self.execute(DummyCase.MALFORMED, Task.GROUNDING, ctx=context(roles=roles))
        self.assertEqual(result.participation, Participation.PARTICIPATING)
        self.assertEqual(result.provenance["roles"], asdict(roles))
        self.assertEqual(result.error.code, ErrorCode.MALFORMED_GROUNDING)

    def test_no_artificial_iou_or_other_scores_in_any_result(self):
        for case in DummyCase:
            for task in Task:
                with self.subTest(case=case, task=task):
                    result = self.execute(case, task, ctx=context(case.value + task.value))
                    serialized = json.dumps(asdict(result)).lower()
                    for metric in ("iou", "score", "pointing_hit"):
                        self.assertNotIn(metric, serialized)

    def test_raw_and_metadata_are_on_disk_before_adapter_runs(self):
        real_adapt = self.adapter.adapt

        def inspect(raw, task):
            paths = list(self.repo.glob("data/processed/local_runs/*/response.raw"))
            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].read_bytes(), raw)
            metadata = json.loads(paths[0].with_name("metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["parse_status"], "NOT_ATTEMPTED")
            self.assertIsNone(metadata["error_status"])
            self.assertEqual(metadata["raw_output"]["sha256"], hashlib.sha256(raw).hexdigest())
            return real_adapt(raw, task)

        with patch.object(self.adapter, "adapt", side_effect=inspect) as spy:
            result = self.execute()
        spy.assert_called_once()
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)

    def test_raw_write_failure_blocks_parsing(self):
        with patch("safeshift.runners.storage._write_new", side_effect=OSError), \
                patch.object(self.adapter, "adapt") as spy:
            result = self.execute()
        spy.assert_not_called()
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        self.assertEqual(result.parse_status, ParseStatus.NOT_ATTEMPTED)

    def test_metadata_write_failure_blocks_parsing_even_when_raw_exists(self):
        from safeshift.runners.storage import _write_new

        def write(path, content):
            if path.name == "metadata.json":
                raise OSError("synthetic disk failure")
            _write_new(path, content)

        with patch("safeshift.runners.storage._write_new", side_effect=write), \
                patch.object(self.adapter, "adapt") as spy:
            result = self.execute()
        spy.assert_not_called()
        self.assertEqual(result.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        self.assertEqual(len(list(self.repo.glob("data/processed/local_runs/*/response.raw"))), 1)

    def test_attempt_cannot_be_overwritten_and_retry_needs_new_call_id(self):
        first = self.execute()
        raw = self.read_raw(first)
        with patch.object(self.adapter, "adapt") as spy:
            duplicate = self.execute(DummyCase.INVALID_CLASSIFICATION)
        spy.assert_not_called()
        self.assertEqual(duplicate.error.code, ErrorCode.RAW_PRESERVATION_FAILURE)
        self.assertEqual(self.read_raw(first), raw)
        retry = self.execute(DummyCase.INVALID_CLASSIFICATION, ctx=context("retry"))
        self.assertEqual(retry.error.code, ErrorCode.INVALID_CLASSIFICATION)
        self.assertNotEqual(first.raw_output.path, retry.raw_output.path)

    def test_required_provenance_survives_storage_and_result(self):
        runner = DummyRunner()
        runner.identity = ModelIdentity("synthetic/frozen-dummy", "a" * 64, "synthetic-evidence-id")
        result = self.execute(runner=runner)
        metadata = json.loads((self.repo / result.raw_output.path).with_name("metadata.json").read_text())
        for key in ("run_id", "call_id", "model_id", "immutable_revision", "revision_evidence",
                    "runner_version", "adapter_version", "parser_version", "task", "prompt_id",
                    "prompt", "prompt_sha256", "decoding", "preprocessing", "precision", "quantization",
                    "device", "software_versions", "sample_id", "input_id", "input_sha256", "timestamp",
                    "source_kind", "git_commit_sha", "command", "seed", "input_provenance", "raw_output"):
            self.assertIn(key, metadata)
            self.assertEqual(metadata[key], result.provenance[key])
        self.assertEqual(result.provenance["immutable_revision"], "a" * 64)
        self.assertEqual(result.provenance["timestamp"], FIXED_TIME.isoformat())
        self.assertEqual(result.provenance["parse_status"], "SUCCESS")
        self.assertIsNone(result.provenance["error_status"])

    def test_pending_revision_is_not_falsely_frozen(self):
        result = self.execute()
        self.assertIsNone(result.provenance["immutable_revision"])
        self.assertEqual(result.provenance["revision_status"], "PENDING")

    def test_revision_without_evidence_or_mutable_alias_is_rejected(self):
        for revision, evidence in (("abc", None), (None, "proof"), ("main", "proof"),
                                   ("PENDING", "proof"), ("", "proof"), ("abc", "")):
            with self.subTest(revision=revision, evidence=evidence), self.assertRaises(ValueError):
                ModelIdentity("synthetic/dummy", revision, evidence)

    def test_naive_timestamp_is_rejected_before_execution(self):
        runner = DummyRunner()
        with self.assertRaises(ValueError):
            execute_call(runner, self.adapter, self.store, request(), context(), clock=lambda: datetime(2026, 1, 1))
        self.assertEqual(runner.events, [])

    def test_invalid_provenance_fails_before_backend_side_effects(self):
        for changes in ({"device": {}}, {"software_versions": {}}, {"precision": ""},
                        {"decoding": {"bad": float("nan")}}, {"roles": Roles(classification="bogus")}):
            runner = DummyRunner()
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.execute(runner=runner, ctx=context(**changes))
            self.assertEqual(runner.events, [])

    def test_backend_mutation_does_not_corrupt_provenance_or_caller_context(self):
        runner = DummyRunner()
        ctx = context()

        def mutate(config):
            config.decoding["mode"] = "changed"

        with patch.object(runner, "initialize", side_effect=mutate):
            result = self.execute(runner=runner, ctx=ctx)
        self.assertEqual(ctx.decoding["mode"], "dummy-fixed")
        self.assertEqual(result.provenance["decoding"]["mode"], "dummy-fixed")

    def test_initialize_failure_taxonomy(self):
        self.assert_stage_failure("initialize", ErrorCode.INITIALIZATION_FAILURE)

    def test_load_failure_taxonomy(self):
        self.assert_stage_failure("load", ErrorCode.MODEL_LOAD_FAILURE)

    def test_preprocessing_failure_taxonomy(self):
        self.assert_stage_failure("prepare_input", ErrorCode.PREPROCESSING_FAILURE)

    def assert_stage_failure(self, stage, code):
        runner = DummyRunner()
        with patch.object(runner, stage, side_effect=RuntimeError), \
                patch.object(runner, "generate_raw") as generate, patch.object(self.adapter, "adapt") as adapt:
            result = self.execute(runner=runner)
        generate.assert_not_called()
        adapt.assert_not_called()
        self.assertEqual(result.error.code, code)
        self.assertEqual(result.error.stage, stage)
        self.assertIsNone(result.raw_output)

    def test_lifecycle_order_and_no_cross_call_output(self):
        runner = DummyRunner()
        self.execute(runner=runner)
        self.execute(task=Task.GROUNDING, runner=runner)
        for offset, task in ((0, Task.CLASSIFICATION), (4, Task.GROUNDING)):
            self.assertEqual(runner.events[offset:offset + 2], ["initialize", "load"])
            self.assertEqual(runner.events[offset + 2], ("prepare_input", request(task)))
            self.assertEqual(runner.events[offset + 3], ("generate_raw", task))

    def test_partial_generation_bytes_survive_without_parsing(self):
        runner = DummyRunner()
        with patch.object(runner, "generate_raw", side_effect=GenerationFailure(b"unfinished native point")), \
                patch.object(self.adapter, "adapt") as spy:
            result = self.execute(runner=runner)
        spy.assert_not_called()
        self.assertEqual(self.read_raw(result), b"unfinished native point")
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)

    def test_invalid_raw_return_is_generation_failure(self):
        runner = DummyRunner()
        with patch.object(runner, "generate_raw", return_value="not bytes"), \
                patch.object(self.adapter, "adapt") as spy:
            result = self.execute(runner=runner)
        spy.assert_not_called()
        self.assertEqual(result.error.code, ErrorCode.GENERATION_FAILURE)

    def test_invalid_utf8_is_preserved_as_classification_error(self):
        runner = DummyRunner()
        with patch.object(runner, "generate_raw", return_value=b"\xff\x00"):
            result = self.execute(runner=runner)
        self.assertEqual(self.read_raw(result), b"\xff\x00")
        self.assertEqual(result.error.code, ErrorCode.INVALID_CLASSIFICATION)

    def test_adapter_cannot_promote_point_or_failed_output_to_canonical_success(self):
        bad_outputs = [
            AdaptedOutput(ParseStatus.SUCCESS, {"bbox": [0, 0, 1, 1]}, SpatialKind.NATIVE_POINT),
            AdaptedOutput(ParseStatus.INVALID, {"bbox": [0, 0, 1, 1]}, SpatialKind.MALFORMED),
            AdaptedOutput(ParseStatus.SUCCESS, None, SpatialKind.NATIVE_BOX),
        ]
        for i, output in enumerate(bad_outputs):
            with self.subTest(output=output), patch.object(self.adapter, "adapt", return_value=output):
                result = self.execute(task=Task.GROUNDING, ctx=context(str(i)))
            self.assertEqual(result.error.code, ErrorCode.PARSER_FAILURE)
            self.assertIsNone(result.canonical)
            self.assertIsNotNone(result.raw_output)

    def test_malformed_native_points_are_not_treated_as_valid_point_evidence(self):
        runner = DummyRunner()
        for i, point in enumerate(([.1], [True, .2], ["0.1", .2], [-.1, .2], [.1, 2])):
            raw = json.dumps({"native_points": [point], "coordinate_system": "xy_1"}).encode()
            with self.subTest(point=point), patch.object(runner, "generate_raw", return_value=raw):
                result = self.execute(task=Task.GROUNDING, runner=runner, ctx=context(str(i)))
            self.assertEqual(result.error.code, ErrorCode.MALFORMED_GROUNDING)
            self.assertEqual(self.read_raw(result), raw)

    def test_empty_canonical_hazards_are_distinct_from_no_spatial_interface(self):
        runner = DummyRunner()
        with patch.object(runner, "generate_raw", return_value=b'{"hazards":[]}'):
            result = self.execute(task=Task.GROUNDING, runner=runner)
        self.assertEqual(result.canonical, Grounding(()))
        self.assertEqual(result.parse_status, ParseStatus.SUCCESS)
        self.assertEqual(result.spatial_kind, SpatialKind.NATIVE_BOX)

    def test_dummy_results_are_deterministic_across_repository_locations(self):
        with tempfile.TemporaryDirectory() as second_repo:
            for case in DummyCase:
                for task in Task:
                    with self.subTest(case=case, task=task):
                        ctx = context(case.value + task.value)
                        first = self.execute(case, task, ctx=ctx)
                        second = self.execute(case, task, ctx=ctx, store=FileRawStore(Path(second_repo)))
                        self.assertEqual(asdict(first), asdict(second))
                        if first.raw_output is not None:
                            self.assertEqual(self.read_raw(first),
                                             (Path(second_repo) / second.raw_output.path).read_bytes())
                        self.assertNotIn(str(self.repo), json.dumps(asdict(first)))

    def test_storage_rejects_absolute_traversal_and_nonprocessed_paths(self):
        for path in (str(self.repo), "/tmp/run", "C:/private/run", "../run", "data/raw/run",
                     "data/processed/../raw", "data/processed/C:run", "outputs/run"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                FileRawStore(self.repo, path)

    def test_opaque_identifiers_cannot_escape_artifact_root(self):
        result = self.execute(req=replace(request(), sample_id="../../outside", input_id="opaque:input"))
        self.assertTrue(result.raw_output.path.startswith("data/processed/local_runs/"))
        self.assertNotIn("..", result.raw_output.path)
        self.assertEqual(result.provenance["sample_id"], "../../outside")

    def test_resolved_alias_cannot_escape_processed_directory(self):
        # Portable simulation of a resolved symlink/junction, no Windows privilege needed.
        original = Path.resolve
        aliased = self.repo / "data" / "processed" / "alias"

        def resolve(path, *args, **kwargs):
            return self.repo / "elsewhere" if path == aliased else original(path, *args, **kwargs)

        with patch.object(Path, "resolve", resolve), self.assertRaises(ValueError):
            FileRawStore(self.repo, "data/processed/alias")

    def test_save_result_keeps_raw_snapshot_and_final_error_separate(self):
        result = self.execute(DummyCase.INVALID_CLASSIFICATION)
        raw_path = self.repo / result.raw_output.path
        before = raw_path.with_name("metadata.json").read_bytes()
        result_path = self.store.save_result(result)
        final = json.loads((self.repo / result_path).read_text())
        self.assertEqual(final["error"]["code"], "INVALID_CLASSIFICATION_OUTPUT")
        self.assertEqual(final["provenance"]["parse_status"], "INVALID")
        self.assertEqual(raw_path.with_name("metadata.json").read_bytes(), before)
        with self.assertRaises(FileExistsError):
            self.store.save_result(result)

    def test_generation_failure_result_can_be_saved_without_raw(self):
        result = self.execute(DummyCase.GENERATION_FAILURE, Task.GROUNDING)
        path = self.store.save_result(result)
        saved = json.loads((self.repo / path).read_text())
        self.assertIsNone(saved["raw_output"])
        self.assertEqual(saved["error"]["code"], "GENERATION_RUNTIME_FAILURE")

    def test_all_failures_return_same_model_without_retry_or_backup(self):
        for case in DummyCase:
            runner = DummyRunner(case, fail_task=Task.CLASSIFICATION)
            with self.subTest(case=case):
                result = self.execute(runner=runner, ctx=context(case.value))
                self.assertEqual(result.provenance["model_id"], "synthetic/dummy")
                self.assertEqual(runner.events.count("load"), 1)
                self.assertEqual(sum(e[0] == "generate_raw" for e in runner.events if isinstance(e, tuple)), 1)

    def test_generic_core_has_only_standard_library_and_contract_dependencies(self):
        root = Path(__file__).resolve().parents[1] / "safeshift/runners"
        allowed = {"abc", "copy", "dataclasses", "datetime", "enum", "hashlib", "json",
                   "typing", "os", "pathlib", "contracts"}
        for name in ("contracts.py", "storage.py"):
            tree = ast.parse((root / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(alias.name.split(".")[0] in allowed for alias in node.names))
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split(".")[0], allowed)


if __name__ == "__main__":
    unittest.main()
