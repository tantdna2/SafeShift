"""Offline handcrafted tests only: no real dataset access or provider calls."""

import contextlib
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.protocol import ADAPTER_VERSION, PARSER_VERSION, SCHEMA_VERSION
from safeshift.protocol.adapters import ADAPTERS
from safeshift.protocol.firewall import BenchmarkFirewallError, external_path
from safeshift.protocol.gate import ExternalCase, GiantBoxReview, evaluate_gate, load_cases
from safeshift.protocol.metrics import (
    ClassificationInput, GroundTruthAtom, InMemoryAtomMembership, METRIC_ENGINE_VERSION,
    OriginalRegion, SpatialInput,
)
from safeshift.protocol.prompts import classification_request, grounding_request, probe_request, PROMPT_VERSIONS
from safeshift.protocol.records import CallMetadata, preserve_and_parse
from safeshift.protocol.schema import HAZARDS, bbox, parse_text
from scripts.pre_freeze import main

REPO = Path(__file__).resolve().parents[1]
MANIFEST = "tests/fixtures/pre_freeze/external_cases.example.json"
DUMMIES = "tests/fixtures/pre_freeze/dummy_predictions.json"


def envelope(provider, text):
    """Handcrafted envelopes; deliberately no SDK import or recorded model data."""
    return json.dumps({
        "gemini": {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": text}]}}]},
        "qwen_dashscope": {"choices": [{"finish_reason": "stop", "message": {"content": text}}]},
        "openai": {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]},
        "anthropic": {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]},
    }[provider]).encode()


def grounding_text(boxes, hazard="SMOKE"):
    return json.dumps({"hazards": [{"hazard_type": hazard, "evidence": [{"bbox": b} for b in boxes]}]})


class SchemaTests(unittest.TestCase):
    def test_canonical_bbox(self):
        self.assertEqual(bbox([0, 0, 1, 1]), (0, 0, 1, 1))
        self.assertEqual(bbox([0.1, 0.2, 0.3, 0.4]), (0.1, 0.2, 0.3, 0.4))

    def test_invalid_boxes_are_not_repaired(self):
        invalid = [[], [0, 1, 2], [0, 0, 1, 1, 1], [0.8, 0, 0.2, 1],
                   [0, 0.8, 1, 0.2], [-0.1, 0, 1, 1], [0, 0, 1.1, 1],
                   [0, 0, 0, 1], [0, 0, 1, 0], [False, 0, 1, 1],
                   ["0", 0, 1, 1], [0, 0, float("inf"), 1], [0, float("nan"), 1, 1], None]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                bbox(value)

    def test_explicit_provider_coordinate_conversion(self):
        self.assertEqual(bbox([200, 100, 400, 300], "yxyx_1000"), (0.1, 0.2, 0.3, 0.4))
        self.assertEqual(bbox([100, 200, 300, 400], "xyxy_1000"), (0.1, 0.2, 0.3, 0.4))
        with self.assertRaises(ValueError):
            bbox([-1, 0, 1000, 1000], "xyxy_1000")
        with self.assertRaises(ValueError):
            bbox([0, 0, 1, 1], "guessed")

    def test_classification_only_accepts_exact_output(self):
        for level in ("Level01", "Level02", "Level03", "Level04"):
            result = parse_text(json.dumps({"safety_level": level}), "classification")
            self.assertTrue(result.success)
            self.assertEqual(result.value.safety_level, level)
        for value in ({"safety_level": "level01"}, {"safety_level": 1}, {},
                      {"safety_level": "Level01", "hazards": []}, {"safety_level": []}):
            self.assertFalse(parse_text(json.dumps(value), "classification").success)

    def test_multiple_hazards_and_multiple_evidence_boxes(self):
        result = parse_text(json.dumps({"hazards": [
            {"hazard_type": "SMOKE", "evidence": [{"bbox": [0, 0, 0.1, 0.2]}, {"bbox": [0.3, 0.4, 0.5, 0.6]}]},
            {"hazard_type": "NO_HELMET", "evidence": [{"bbox": [0.6, 0.6, 0.8, 0.9], "label": "Person"}]},
        ]}), "grounding")
        self.assertTrue(result.success)
        self.assertEqual(len(result.value.hazards), 2)
        self.assertEqual(result.boxes_attempted, 3)
        self.assertEqual(result.boxes_valid, 3)

    def test_empty_hazard_list_is_success_not_parse_failure(self):
        result = parse_text('{"hazards": []}', "grounding")
        self.assertTrue(result.success)
        self.assertEqual(result.value.hazards, ())
        self.assertEqual(result.boxes_attempted, 0)

    def test_claim_without_evidence_is_preserved(self):
        result = parse_text(grounding_text([]), "grounding")
        self.assertTrue(result.success)
        self.assertEqual(result.value.hazards[0].evidence, ())

    def test_malformed_json_and_duplicate_keys(self):
        for text in ('', 'not JSON', '{', '```json\n{"hazards": []}\n```',
                     '{"hazards": [], "hazards": []}', '{"bbox": [NaN, 0, 1, 1]}',
                     '{"hazards": []} trailing'):
            with self.subTest(text=text):
                result = parse_text(text, "grounding")
                self.assertEqual(result.status, "JSON_ERROR")
                self.assertIsNone(result.value)
                self.assertTrue(result.errors)
                self.assertIsNone(result.boxes_attempted)

    def test_wrong_schema_and_unknown_hazards(self):
        values = [[], None, {"hazards": None}, {"hazards": "[]"},
                  {"hazards": [], "safety_level": "Level04"},
                  {"hazards": [{"hazard_type": "INVENTED", "evidence": []}]},
                  {"hazards": [{"hazard_type": "SMOKE", "evidence": None}]},
                  {"hazards": [{"hazard_type": "SMOKE", "evidence": [{"bbox": [0, 0, 1, 1], "label": 1}]}]}]
        for value in values:
            with self.subTest(value=value):
                result = parse_text(json.dumps(value), "grounding")
                self.assertEqual(result.status, "SCHEMA_ERROR")
                self.assertIsNone(result.value)

    def test_partial_coordinates_do_not_become_success(self):
        result = parse_text(grounding_text([[0, 0, 0.2, 0.3], [0.5, 0, 0.1, 1]]), "grounding")
        self.assertFalse(result.success)
        self.assertIsNone(result.value)
        self.assertEqual(result.status, "COORDINATE_ERROR")
        self.assertTrue(result.response_schema_valid)
        self.assertEqual((result.boxes_attempted, result.boxes_valid), (2, 1))
        self.assertEqual(len(result.diagnostic_evidence), 1)

    def test_probe_requires_single_box(self):
        self.assertTrue(parse_text('{"bbox": [0, 0, 1, 1]}', "external_probe").success)
        self.assertFalse(parse_text('{"boxes": [[0, 0, 1, 1]]}', "external_probe").success)


class RequestAdapterTests(unittest.TestCase):
    def test_calls_are_independent(self):
        call1 = classification_request(REPO, "tests/synthetic.png", "SYNTHETIC_POLICY_MARKER")
        call2 = grounding_request(REPO, "tests/synthetic.png")
        self.assertIn("SYNTHETIC_POLICY_MARKER", call1.prompt)
        self.assertNotIn("SYNTHETIC_POLICY_MARKER", call2.prompt)
        self.assertNotIn("NO_GLOVES", call1.prompt)
        self.assertTrue(all(hazard in call2.prompt for hazard in HAZARDS))
        with self.assertRaises(TypeError):
            grounding_request(REPO, "tests/synthetic.png", classification_output="Level01")
        with self.assertRaises(TypeError):
            classification_request(REPO, "tests/synthetic.png", "policy", grounding_output={})

    def test_policy_and_vocabulary_are_required(self):
        with self.assertRaises(ValueError):
            classification_request(REPO, "tests/synthetic.png", "")
        with self.assertRaises(ValueError):
            grounding_request(REPO, "tests/synthetic.png", ("SMOKE",))

    def test_each_provider_unwraps_handcrafted_text(self):
        for provider, adapter in ADAPTERS.items():
            with self.subTest(provider=provider):
                self.assertEqual(adapter.extract_text(envelope(provider, '{"hazards": []}')), '{"hazards": []}')

    def test_provider_prompts_agree_with_coordinate_contracts(self):
        request = grounding_request(REPO, "tests/synthetic.png")
        gemini = ADAPTERS["gemini"].prepare(REPO, request)
        self.assertIn("[ymin, xmin, ymax, xmax]", gemini.prompt)
        self.assertNotIn("[xmin, ymin, xmax, ymax]", gemini.prompt)
        self.assertNotIn("[0,1]", gemini.prompt)
        qwen = ADAPTERS["qwen_dashscope"].prepare(REPO, request)
        self.assertIn("[xmin, ymin, xmax, ymax] coordinates in [0,1000]", qwen.prompt)
        self.assertNotEqual(gemini.prompt_sha256, request.prompt_sha256)
        classification = classification_request(REPO, "tests/synthetic.png", "synthetic policy")
        self.assertEqual(ADAPTERS["gemini"].prepare(REPO, classification), classification)

    def test_malformed_envelopes_and_refusals(self):
        cases = {
            "gemini": {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{}"}]}}]},
            "qwen_dashscope": {"choices": [{"finish_reason": "length", "message": {"content": "{}"}}]},
            "openai": {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]},
            "anthropic": {"stop_reason": "max_tokens", "content": [{"type": "text", "text": "{}"}]},
        }
        for provider, adapter in ADAPTERS.items():
            for raw in (b'{}', b'[]', b'null', b'broken', b'{"error": "dummy"}', json.dumps(cases[provider]).encode()):
                with self.subTest(provider=provider, raw=raw), self.assertRaises(ValueError):
                    adapter.extract_text(raw)

    def test_no_adapter_can_make_a_network_call(self):
        request = probe_request(REPO, "tests/synthetic.png", "Find red square")
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            for adapter in ADAPTERS.values():
                with self.assertRaisesRegex(RuntimeError, "OFFLINE_ONLY"):
                    adapter.send(request)


class RawPreservationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve()
        self.request = grounding_request(self.repo, "synthetic.png")
        self.metadata = CallMetadata("run1", "sample1", "call2", "dummy-model", "dummy-version",
                                     "UNRESOLVED", "NO_SDK", {}, "a" * 40, "b" * 64,
                                     {"python": "synthetic-test"}, "python -m unittest", None)

    def persist(self, raw, adapter=None, metadata=None):
        return preserve_and_parse(self.repo, "data/processed/pre_freeze", raw,
                                  adapter or ADAPTERS["openai"], self.request, metadata or self.metadata)

    def test_raw_is_on_disk_before_extract_text(self):
        raw = envelope("openai", '{"hazards": []}')
        from safeshift.protocol.adapters import ProviderAdapter
        extract = ProviderAdapter.extract_text

        def assert_saved(adapter, content):
            directory = self.repo / "data/processed/pre_freeze/run1/sample1/call2"
            self.assertEqual((directory / "response.raw").read_bytes(), raw)
            self.assertTrue((directory / "metadata.json").is_file())
            return extract(adapter, content)

        with patch.object(ProviderAdapter, "extract_text", assert_saved):
            result = self.persist(raw)
        self.assertTrue(result.success)
        metadata = json.loads((self.repo / result.raw_artifact).with_name("metadata.json").read_text())
        self.assertEqual(metadata["raw_response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(metadata["prompt_sha256"], self.request.prompt_sha256)
        self.assertEqual(metadata["sample_id"], "sample1")
        self.assertEqual(metadata["protocol_freeze_commit_sha"], "PENDING")
        self.assertFalse(Path(result.raw_artifact).is_absolute())

    def test_unparseable_raw_bytes_are_preserved_verbatim(self):
        raw = b'\xff\x00unparseable raw response'
        result = self.persist(raw)
        self.assertEqual(result.status, "ENVELOPE_ERROR")
        self.assertEqual((self.repo / result.raw_artifact).read_bytes(), raw)
        self.assertIsNone(result.value)

    def test_parse_failure_is_saved_not_replaced_by_empty_hazards(self):
        result = self.persist(envelope("openai", "{broken"))
        self.assertEqual(result.status, "JSON_ERROR")
        saved = json.loads((self.repo / result.raw_artifact).with_name("parsed.json").read_text())
        self.assertIsNone(saved["value"])
        self.assertTrue(saved["errors"])

    def test_disk_failure_prevents_parser(self):
        with patch.object(Path, "write_bytes", side_effect=OSError("disk full")), \
                patch("safeshift.protocol.records.parse_text") as parser:
            with self.assertRaises(OSError):
                self.persist(b"raw")
            parser.assert_not_called()

    def test_retry_cannot_overwrite_raw(self):
        first = self.persist(b"first")
        with self.assertRaises(FileExistsError):
            self.persist(b"second")
        self.assertEqual((self.repo / first.raw_artifact).read_bytes(), b"first")

    def test_live_source_and_unsafe_ids_are_rejected(self):
        for metadata in (replace(self.metadata, source_kind="provider_live"),
                         replace(self.metadata, run_id="../escape"),
                         replace(self.metadata, protocol_freeze_commit_sha="a" * 40)):
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                self.persist(b"raw", metadata=metadata)

    def test_all_provider_envelopes_normalize_after_preservation(self):
        coordinates = {"gemini": [200, 100, 400, 300], "qwen_dashscope": [100, 200, 300, 400],
                       "openai": [.1, .2, .3, .4], "anthropic": [.1, .2, .3, .4]}
        for provider, adapter in ADAPTERS.items():
            with self.subTest(provider=provider):
                request = adapter.prepare(self.repo, self.request)
                raw = envelope(provider, grounding_text([coordinates[provider]]))
                result = preserve_and_parse(self.repo, "data/processed/pre_freeze", raw, adapter, request,
                                            replace(self.metadata, call_id=provider))
                self.assertTrue(result.success)
                self.assertEqual(result.value.hazards[0].evidence[0].bbox, (.1, .2, .3, .4))
                self.assertEqual((self.repo / result.raw_artifact).read_bytes(), raw)

    def test_artifact_directory_cannot_escape_processed_or_target_raw(self):
        for root in ("tests/artifacts", "data/raw/InspecSafe-V1", "../outside"):
            with self.subTest(root=root), self.assertRaises(ValueError):
                preserve_and_parse(self.repo, root, b"raw", ADAPTERS["openai"], self.request, self.metadata)

    def test_metadata_write_failure_prevents_parse(self):
        with patch.object(Path, "write_text", side_effect=OSError("metadata write failed")), \
                patch("safeshift.protocol.records.parse_text") as parser:
            with self.assertRaises(OSError):
                self.persist(b"raw")
            parser.assert_not_called()
        self.assertEqual((self.repo / "data/processed/pre_freeze/run1/sample1/call2/response.raw").read_bytes(), b"raw")


class GateTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases(REPO, MANIFEST)
        self.predictions = {case.case_id: parse_text(json.dumps({"bbox": case.target_gt_bbox}), "external_probe") for case in self.cases}
        self.reviews = {case.case_id: GiantBoxReview("NO_GIANT", "unit-test", "Exact synthetic small target") for case in self.cases}

    def evaluate(self, predictions=None, reviews=None, cases=None):
        return evaluate_gate(REPO, cases or self.cases, predictions if predictions is not None else self.predictions,
                             reviews if reviews is not None else self.reviews)

    def test_correct_tracking_passes(self):
        result = self.evaluate()
        self.assertEqual(result.status, "PASS")
        self.assertTrue(result.systematic_tracking)
        self.assertEqual(result.cases[0].target_iou_diagnostic, 1)

    def test_iou_is_never_a_pass_fail_threshold(self):
        tiny = {}
        for case in self.cases:
            x0, y0, x1, y1 = case.target_gt_bbox
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
            tiny[case.case_id] = parse_text(json.dumps({"bbox": [x - .001, y - .001, x + .001, y + .001]}), "external_probe")
        result = self.evaluate(tiny)
        self.assertEqual(result.status, "PASS")
        self.assertLess(result.cases[0].target_iou_diagnostic, .001)

    def test_stationary_predictions_fail_tracking(self):
        same = self.predictions[self.cases[0].case_id]
        result = self.evaluate({case.case_id: same for case in self.cases})
        self.assertEqual(result.status, "FAIL")
        self.assertFalse(result.systematic_tracking)

    def test_full_image_predictions_fail(self):
        full = parse_text('{"bbox": [0, 0, 1, 1]}', "external_probe")
        result = self.evaluate({case.case_id: full for case in self.cases})
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(all(row.full_image for row in result.cases))
        self.assertTrue(all(not row.excludes_distractor_center for row in result.cases))

    def test_qualitative_giant_fails_without_numeric_area_threshold(self):
        reviews = dict(self.reviews)
        reviews[self.cases[0].case_id] = GiantBoxReview("GIANT", "unit-test", "Handcrafted negative review fixture")
        self.assertEqual(self.evaluate(reviews=reviews).status, "FAIL")

    def test_giant_review_cannot_default_to_pass(self):
        self.assertEqual(self.evaluate(reviews={}).status, "PENDING_REVIEW")
        with self.assertRaises(ValueError):
            GiantBoxReview("NO_GIANT", "", "")

    def test_parse_failure_and_missing_responses_fail(self):
        results = dict(self.predictions)
        results[self.cases[0].case_id] = parse_text("malformed", "external_probe")
        result = self.evaluate(results)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.cases[0].parse_status, "JSON_ERROR")
        self.assertEqual(self.evaluate({}).status, "FAIL")

    def test_wrong_target_fails(self):
        distractors = {case.case_id: parse_text(json.dumps({"bbox": case.distractor_gt_bbox}), "external_probe") for case in self.cases}
        self.assertEqual(self.evaluate(distractors).status, "FAIL")

    def test_unknown_response_id_is_not_dropped(self):
        with self.assertRaises(ValueError):
            self.evaluate({**self.predictions, "unexpected": next(iter(self.predictions.values()))})

    def test_malformed_suites_are_rejected(self):
        a, b = self.cases
        for cases in ((a,), (a, a), (replace(a, target_gt_bbox=a.distractor_gt_bbox), b),
                      (a, replace(b, target_query="different target")),
                      (a, replace(b, image_path=a.image_path))):
            with self.subTest(cases=cases), self.assertRaises(ValueError):
                self.evaluate(cases=cases)

    def test_manifest_missing_fields_and_unknown_source_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            path = repo / "cases.json"
            for obj in ({}, {"schema_version": "external-target-distractor-v1", "source_kind": "InspecSafe",
                              "provenance": "invalid", "cases": []}):
                path.write_text(json.dumps(obj), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_cases(repo, "cases.json")

    def test_distractor_on_prediction_boundary_is_included(self):
        from safeshift.protocol.gate import contains
        self.assertTrue(contains((.1, .1, .5, .5), (.5, .3)))

    def test_empty_suite_cannot_pass_vacuously(self):
        with self.assertRaises(ValueError):
            evaluate_gate(REPO, (), {})


class FirewallTests(unittest.TestCase):
    def test_raw_paths_alias_spelling_and_traversal_are_blocked(self):
        paths = ["data/raw/InspecSafe-V1/test/example.png", "DATA/RAW/anything.json",
                 "data\\raw\\InspecSafe-V1\\x.png", "other/InSpEcSaFe-V1/image.png",
                 "data/raw/../processed/a.png", "../outside.json", "C:/raw/image.png",
                 "C:relative.png", "//host/share/image.png", "tests/file:stream", ""]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(BenchmarkFirewallError):
                external_path(REPO, path)

    def test_safe_relative_external_path_is_allowed(self):
        self.assertEqual(external_path(REPO, MANIFEST), REPO / MANIFEST)

    def test_resolved_alias_to_benchmark_is_blocked_without_reading_dataset(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp).resolve()
            original = Path.resolve

            def resolve(path, *args, **kwargs):
                if path == repo / "alias.png":
                    return repo / "data/raw/InspecSafe-V1/image.png"
                return original(path, *args, **kwargs)

            with patch.object(Path, "resolve", resolve), self.assertRaises(BenchmarkFirewallError):
                external_path(repo, "alias.png")

    def test_all_request_builders_guard_benchmark_inputs(self):
        for builder, args in ((classification_request, ("policy",)), (grounding_request, ()), (probe_request, ("target",))):
            with self.subTest(builder=builder), self.assertRaises(BenchmarkFirewallError):
                builder(REPO, "data/raw/InspecSafe-V1/test/image.png", *args)

    def test_cli_fails_loudly_before_opening_raw_manifest(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), patch.object(Path, "read_bytes", side_effect=AssertionError("must not read")):
            status = main(["validate-cases", "--manifest", "data/raw/InspecSafe-V1/cases.json"])
        self.assertEqual(status, 2)
        self.assertIn("BENCHMARK FIREWALL", stderr.getvalue())

    def test_cli_checks_unused_response_path_before_opening_manifest(self):
        with contextlib.redirect_stderr(io.StringIO()), patch.object(Path, "read_bytes", side_effect=AssertionError("must not read")):
            self.assertEqual(main(["validate-cases", "--manifest", MANIFEST, "--responses", "data/raw/InspecSafe-V1/raw.json"]), 2)

    def test_embedded_manifest_image_path_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            obj = json.loads((REPO / MANIFEST).read_text())
            obj["cases"][0]["image_path"] = "data/raw/InspecSafe-V1/image.png"
            (Path(temp) / "cases.json").write_text(json.dumps(obj))
            with self.assertRaises(BenchmarkFirewallError):
                load_cases(Path(temp), "cases.json")

    def test_offline_cli_format_and_dummy_replay(self):
        for command, extra in (("validate-cases", []), ("replay-dummy-gate", ["--responses", DUMMIES])):
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout), patch("socket.socket", side_effect=AssertionError("network forbidden")):
                self.assertEqual(main([command, "--manifest", MANIFEST, *extra]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["live_gate"], "NOT RUN")


class MetricContractTests(unittest.TestCase):
    def test_rq2_is_gt_membership_not_predicted_hazard(self):
        lookup = InMemoryAtomMembership({"multi": frozenset({"SMOKE", "NO_HELMET"}), "normal": frozenset()})
        prediction = parse_text('{"safety_level": "Level04"}', "classification")
        sample = ClassificationInput("multi", "Level01", "synthetic", "point1", prediction, lookup.atoms_for_sample("multi"))
        self.assertEqual(len(sample.rq2_atom_memberships), 2)
        self.assertEqual(sample.prediction.value.safety_level, "Level04")
        self.assertEqual(lookup.atoms_for_sample("normal"), frozenset())
        with self.assertRaises(KeyError):
            lookup.atoms_for_sample("missing")
        with self.assertRaises(ValueError):
            InMemoryAtomMembership({"x": frozenset({"INVENTED"})})

    def test_direct_proxy_and_unsupported_tracks_remain_separate(self):
        person = OriginalRegion("p", "Person", ((0, 0), (1, 0), (0, 1)), (0, 0, 1, 1), "normalized", 10, 10)
        smoke = replace(person, region_id="s", label="Smoke")
        direct = GroundTruthAtom("a", "SMOKE", "DIRECT", (smoke,))
        proxy = GroundTruthAtom("b", "NO_HELMET", "WEAK_PROXY", (person,))
        unsupported = GroundTruthAtom("c", "DOOR_OPEN", "NO_CURRENT_SPATIAL_GT", (), "No state-specific spatial annotation")
        failure = parse_text("broken", "grounding")
        sample = SpatialInput("sample1", "PARTICIPATING", failure, (direct,), (proxy,), (unsupported,))
        self.assertEqual(sample.prediction.status, "JSON_ERROR")
        self.assertEqual(sample.direct_atoms[0].candidate_regions[0].original_polygon, smoke.original_polygon)
        with self.assertRaises(ValueError):
            replace(sample, direct_atoms=(proxy,))
        with self.assertRaises(ValueError):
            GroundTruthAtom("u", "SMOKE", "NO_CURRENT_SPATIAL_GT", (), None)

    def test_nonparticipant_is_not_a_parse_failure(self):
        sample = SpatialInput("sample1", "NOT PARTICIPATING", None, (), (), ())
        self.assertIsNone(sample.prediction)
        with self.assertRaises(ValueError):
            replace(sample, prediction=parse_text("broken", "grounding"))
        with self.assertRaises(ValueError):
            replace(sample, participation="PARTICIPATING")

    def test_classification_contract_rejects_grounding_as_call1(self):
        with self.assertRaises(ValueError):
            ClassificationInput("sample", "Level01", "domain", "point", parse_text('{"hazards": []}', "grounding"), frozenset())


class ConfigTests(unittest.TestCase):
    def test_qwen_unresolved_fields_and_adapter_contracts(self):
        config = json.loads((REPO / "configs/pre_freeze/providers.json").read_text())
        qwen = config["providers"]["qwen_dashscope"]
        self.assertEqual(qwen["model_id"], "qwen3-vl-8b-instruct")
        self.assertEqual(qwen["region"], "ap-southeast-1")
        self.assertEqual(qwen["status"], "ROUTE_REGION_PINNED")
        self.assertEqual(qwen["workspace_endpoint"], "UNRESOLVED")
        self.assertEqual(qwen["decoding"], "QWEN_DECODING_PENDING_ROUTE_CONFIRMATION")
        self.assertEqual(qwen["precision"], "UNDISCLOSED_BY_PROVIDER")
        self.assertEqual(qwen["hosted_reproducibility"], "HOSTED_BACKEND_NOT_FULLY_PINNABLE")
        self.assertNotIn("WorkspaceId", qwen)
        for provider, adapter in ADAPTERS.items():
            self.assertEqual(config["providers"][provider]["coordinate_convention"], adapter.convention)
            self.assertEqual(config["providers"][provider]["api_key_env"], adapter.api_key_env)
            self.assertFalse(config["providers"][provider]["live_route_verified"])

    def test_freeze_template_versions_match_code_but_remain_pending(self):
        manifest = json.loads((REPO / "configs/pre_freeze/freeze_manifest.template.json").read_text())
        self.assertEqual(manifest["protocol_freeze_commit_sha"], "PENDING")
        self.assertEqual(manifest["schema_version"], SCHEMA_VERSION)
        self.assertEqual(manifest["parser_version"], PARSER_VERSION)
        self.assertEqual(manifest["prompt_versions"], PROMPT_VERSIONS)
        self.assertEqual(set(manifest["adapter_versions"].values()), {ADAPTER_VERSION})
        self.assertEqual(manifest["metric_engine_version"], METRIC_ENGINE_VERSION)
        self.assertEqual(manifest["external_gate_artifacts"], {"openai": "NOT RUN", "anthropic": "NOT RUN"})

    def test_json_schema_closed_vocabulary_matches_parser(self):
        schema = json.loads((REPO / "schemas/canonical.schema.json").read_text())
        self.assertEqual(tuple(schema["$defs"]["hazard"]["properties"]["hazard_type"]["enum"]), HAZARDS)
        self.assertFalse(schema["$defs"]["classification"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["grounding"]["additionalProperties"])


if __name__ == "__main__":
    unittest.main()
