"""Synthetic integrity failures and independent T2 projection/queue oracles."""

import copy
from dataclasses import FrozenInstanceError, fields
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.evaluation.triage import (
    ClassifiedResult, HNLOSignal, ModelResults, SourceIdentity, build_review_queue,
)
from safeshift.evaluation.triage_adapter import adapt_synthetic_bundle, fixture_sha256
from scripts.demo_triage_adapter_cpu import CASES, IDS, build_report, synthetic_bundle

ROOT = Path(__file__).resolve().parents[1]
KEY = b"public-t3-test-seed"


def rehash(bundle):
    """Recompute dependency checksums, NEVER register content with the adapter.

    Lets negative tests reach semantic validators despite internally consistent
    untrusted metadata; the independent source seal must still reject it.
    """
    reports = {r["source_id"]: r for r in bundle["reports"]}
    for source in bundle["manifest"]["sources"]:
        source["report_sha256"] = fixture_sha256(reports[source["source_id"]])
    for entry in bundle["selection"]["entries"]:
        entry["report_sha256"] = fixture_sha256(reports[entry["source_id"]])
    bundle["selection"]["manifest_sha256"] = fixture_sha256(bundle["manifest"])
    return bundle


def queue(adapted, mode="combined", budget=2):
    return build_review_queue(adapted.planned_ids, adapted.focal, adapted.peers,
                              mode=mode, budget=budget, tie_key=KEY)


class AdapterTests(unittest.TestCase):
    def test_complete_exact_t2_projection_against_handwritten_oracle(self):
        a = adapt_synthetic_bundle(synthetic_bundle())
        expected = []
        for model, labels in (
            ("qwen3", ("Level04", "Level04", "Level04", "Level01")),
            ("internvl35", ("Level03", "Level02", "Level04", "Level01")),
            ("minicpm4", ("Level04", "Level01", "Level04", "Level04")),
        ):
            identity = SourceIdentity("synthetic-" + model, "fixture-revision-" + model + "-v1",
                                      "fixture-impl-" + model + "-v1", "fixture-config-" + model + "-v1",
                                      "fixture-run-" + model, "fixture-series-" + model, "fixture-attempt-1")
            rows = tuple(ClassifiedResult(sid, "SUCCESS", label,
                         HNLOSignal((9, 2, 1)[n], True) if model == "qwen3" and n < 3 else None)
                         for n, (sid, label) in enumerate(zip(IDS, labels)))
            expected.append(ModelResults(identity, rows))
        self.assertEqual((a.planned_ids, a.focal, a.peers), (IDS, expected[0], tuple(expected[1:])))
        self.assertEqual(queue(a), build_review_queue(IDS, expected[0], expected[1:],
                         mode="combined", budget=2, tie_key=KEY))
        self.assertEqual([r["sample_id"] for r in queue(a)["review"]], [IDS[1], IDS[0]])
        self.assertEqual([r["sample_id"] for r in queue(a, "hnlo_only")["review"]], [IDS[0], IDS[1]])
        self.assertEqual([r["sample_id"] for r in queue(a, "peer_only")["review"]], [IDS[1], IDS[0]])
        self.assertEqual([m["statuses"]["SUCCESS"] for m in queue(a)["coverage"]["models"]], [4, 4, 4])

    def test_all_original_fixture_seals_are_accepted(self):
        for case in CASES:
            with self.subTest(case=case):
                a = adapt_synthetic_bundle(synthetic_bundle(case))
                self.assertEqual(a.planned_ids, IDS)
                self.assertEqual(len(a.sources), 3)
                json.dumps(build_report(case=case, budget=2, tie_key=KEY), allow_nan=False)

    def test_missing_row_is_explicit_missing_with_unchanged_denominator(self):
        a = adapt_synthetic_bundle(synthetic_bundle("missing_row"))
        q = queue(a)
        self.assertEqual(a.sources[1].source_id, "fixture-source-minicpm4")
        self.assertEqual(a.sources[1].missing_ids, (IDS[0],))
        self.assertEqual(q["coverage"]["models"][2]["statuses"]["MISSING"], 1)
        self.assertEqual(q["coverage"]["models"][2]["denominator"], 4)
        self.assertEqual(q["mandatory_count"], 1)
        self.assertEqual(q["review"][0]["sample_id"], IDS[0])

    def test_entire_model_without_rows_stays_missing_not_omitted(self):
        a = adapt_synthetic_bundle(synthetic_bundle("missing_model"))
        self.assertEqual(a.peers[1].records, ())
        q = queue(a)
        self.assertEqual(q["coverage"]["models"][2]["statuses"]["MISSING"], 4)
        self.assertEqual((q["mandatory_count"], q["status"]), (3, "OVERLOAD"))
        self.assertEqual(q["backlog"]["mandatory"], 1)

    def test_absent_model_identity_report_is_error(self):
        b = synthetic_bundle()
        b["reports"].pop()
        with self.assertRaisesRegex(ValueError, "three sources/reports/selection"):
            adapt_synthetic_bundle(b)

    def test_failure_statuses_preserved_never_normal(self):
        for case, status in (("invalid", "INVALID"), ("technical_error", "TECHNICAL_ERROR"),
                             ("not_attempted", "NOT_ATTEMPTED")):
            with self.subTest(status=status):
                a = adapt_synthetic_bundle(synthetic_bundle(case))
                self.assertEqual(a.peers[1].records[0], ClassifiedResult(IDS[0], status))
                q = queue(a)
                self.assertEqual(q["mandatory_count"], 1)
                self.assertEqual(q["review"][0]["reasons"], ["PEER_" + status + ":synthetic-minicpm4"])
        q = queue(adapt_synthetic_bundle(synthetic_bundle("focal_invalid")))
        self.assertEqual(q["review"][0]["reasons"], ["FOCAL_INVALID"])

    def test_every_identity_field_missing_or_wrong_in_report_row_and_selection(self):
        for field in fields(SourceIdentity):
            for location in ("report", "row", "selection"):
                for missing in (False, True):
                    b = synthetic_bundle()
                    obj = {"report": b["reports"][1], "row": b["reports"][1]["rows"][0],
                           "selection": b["selection"]["entries"][1]}[location]["identity"]
                    if missing:
                        obj.pop(field.name)
                    else:
                        obj[field.name] = "conflicting-identity"
                    with self.subTest(field=field.name, location=location, missing=missing):
                        with self.assertRaisesRegex(ValueError, "identity"):
                            adapt_synthetic_bundle(rehash(b))

    def test_model_ids_cannot_be_reused(self):
        b = synthetic_bundle()
        for collection in (b["manifest"]["sources"], b["selection"]["entries"], b["reports"]):
            collection[2]["identity"]["model_id"] = "synthetic-internvl35"
        with self.assertRaisesRegex(ValueError, "model IDs must be distinct"):
            adapt_synthetic_bundle(rehash(b))

    def test_two_attempts_same_sample_cannot_be_selected_implicitly(self):
        b = synthetic_bundle()
        another = copy.deepcopy(b["reports"][1]["rows"][0])
        another["identity"]["attempt_id"] = "fixture-attempt-2"
        b["reports"][1]["rows"].append(another)
        with self.assertRaisesRegex(ValueError, "duplicate sample_id"):
            adapt_synthetic_bundle(rehash(b))
        b = synthetic_bundle()
        another = copy.deepcopy(b["reports"][1])
        another["identity"]["run_id"] = "later-successful-run"
        b["reports"].append(another)
        with self.assertRaisesRegex(ValueError, "external selection required.*duplicate"):
            adapt_synthetic_bundle(b)

    def test_selection_missing_conflicting_or_automatic_is_rejected(self):
        for field in ("selection_id", "authority_id", "rule", "manifest_sha256", "entries"):
            b = synthetic_bundle()
            del b["selection"][field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "selection"):
                adapt_synthetic_bundle(b)
        for rule in ("latest", "best", "prefer-success", "recovery", "approved"):
            b = synthetic_bundle()
            b["selection"]["rule"] = rule
            with self.subTest(rule=rule), self.assertRaisesRegex(ValueError, "exact selection"):
                adapt_synthetic_bundle(b)
        b = synthetic_bundle()
        b["selection"]["entries"].pop()
        with self.assertRaisesRegex(ValueError, "three sources"):
            adapt_synthetic_bundle(b)

    def test_planned_cohort_mismatch_duplicate_and_nonopaque_id(self):
        for ids in ([IDS[0]], [*IDS, IDS[0]], [*IDS[:-1], "domain-Level04.jpg"]):
            b = synthetic_bundle()
            b["reports"][1]["planned_ids"] = ids
            with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, "planned"):
                adapt_synthetic_bundle(rehash(b))
        b = synthetic_bundle()
        b["manifest"]["planned_ids"].pop()
        with self.assertRaisesRegex(ValueError, "cohort mismatch"):
            adapt_synthetic_bundle(b)

    def test_duplicate_and_outside_result_id(self):
        for outside in (False, True):
            b = synthetic_bundle()
            row = copy.deepcopy(b["reports"][2]["rows"][0])
            if outside:
                row["sample_id"] = "f" * 32
            b["reports"][2]["rows"].append(row)
            with self.subTest(outside=outside), self.assertRaisesRegex(ValueError, "outside|duplicate"):
                adapt_synthetic_bundle(rehash(b))

    def test_checksum_oracle_and_content_tampering(self):
        # Independent canonical-byte oracle, not the adapter's serialization.
        expected = hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
        self.assertEqual(fixture_sha256({"b": 2, "a": 1}), expected)
        a = adapt_synthetic_bundle(synthetic_bundle())
        self.assertEqual(a.input_sha256[0][1], hashlib.sha256(b"handwritten synthetic input 0").hexdigest())
        mutations = (
            lambda b: b["inputs"][0].update(content="tampered"),
            lambda b: b["reports"][1]["rows"][0].update(predicted_safety_level="Level04"),
            lambda b: b["selection"].update(manifest_sha256="0" * 64),
            lambda b: b["selection"]["entries"][0].update(report_sha256="0" * 64),
            lambda b: b["manifest"]["sources"][0].update(report_sha256="0" * 64),
        )
        for mutate in mutations:
            b = synthetic_bundle()
            mutate(b)
            with self.assertRaisesRegex(ValueError, "checksum"):
                adapt_synthetic_bundle(b)

    def test_row_input_hash_must_match_other_models_and_manifest(self):
        b = synthetic_bundle()
        b["reports"][2]["rows"][0]["input_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "row input checksum"):
            adapt_synthetic_bundle(rehash(b))

    def test_invalid_status_label_combinations_are_errors(self):
        for status, label in (("SUCCESS", None), ("SUCCESS", "Normal"), ("SUCCESS", "Level05"),
                              ("INVALID", "Level04"), ("TECHNICAL_ERROR", "Level04"),
                              ("NOT_ATTEMPTED", "Level04"), ("MISSING", None), ("ERROR", None)):
            b = synthetic_bundle()
            b["reports"][2]["rows"][0].update(status=status, predicted_safety_level=label)
            with self.subTest(status=status, label=label), self.assertRaises(ValueError):
                adapt_synthetic_bundle(rehash(b))

    def test_missing_and_ineligible_hnlo_are_mandatory_never_imputed(self):
        for case, state in (("hnlo_missing", "MISSING"), ("hnlo_ineligible", "INELIGIBLE")):
            a = adapt_synthetic_bundle(synthetic_bundle(case))
            q = queue(a)
            self.assertEqual(q["review"][0]["sample_id"], IDS[0])
            self.assertEqual(q["review"][0]["reasons"], ["FOCAL_HNLO_" + state])
            self.assertIsNone(next(c for c in q["cases"] if c["sample_id"] == IDS[0])["focal_hnlo"]["value"])
            self.assertEqual(queue(a, "peer_only")["mandatory_count"], 0)

    def test_malformed_hnlo_rejected_without_coercion(self):
        for value in (None, True, "9", float("nan"), float("inf"), -float("inf"), 10**400):
            b = synthetic_bundle()
            b["reports"][0]["rows"][0]["hnlo"]["value"] = value
            with self.subTest(value=str(value)[:30]), self.assertRaises(ValueError):
                adapt_synthetic_bundle(rehash(b))

    def test_valid_hnlo_requires_exact_bound_upstream_evidence(self):
        for field, value in (("sample_id", IDS[1]), ("input_sha256", "0" * 64),
                             ("value", 99), ("qualification", "APPROVED")):
            b = synthetic_bundle()
            b["evidence"][0][field] = value
            h = b["reports"][0]["rows"][0]["hnlo"]
            h["evidence_sha256"] = fixture_sha256(b["evidence"][0])
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "HNLO evidence"):
                adapt_synthetic_bundle(rehash(b))
        b = synthetic_bundle()
        b["evidence"].pop(0)
        with self.assertRaisesRegex(ValueError, "HNLO evidence"):
            adapt_synthetic_bundle(b)
        b = synthetic_bundle()
        b["reports"][0]["rows"][0]["hnlo"]["evidence_sha256"] = None
        with self.assertRaisesRegex(ValueError, "evidence_sha256"):
            adapt_synthetic_bundle(rehash(b))

    def test_evidence_identity_cannot_be_transferred_from_another_attempt(self):
        b = synthetic_bundle()
        b["evidence"][0]["identity"]["attempt_id"] = "attempt-other"
        b["reports"][0]["rows"][0]["hnlo"]["evidence_sha256"] = fixture_sha256(b["evidence"][0])
        with self.assertRaisesRegex(ValueError, "HNLO evidence"):
            adapt_synthetic_bundle(rehash(b))

    def test_minicpm_label_only_and_all_peer_hnlo_rejected(self):
        a = adapt_synthetic_bundle(synthetic_bundle())
        self.assertTrue(all(r.hnlo is None for r in a.peers[1].records))
        for peer in (1, 2):
            b = synthetic_bundle()
            b["reports"][peer]["rows"][0]["hnlo"] = {"state": "VALID", "value": 2,
                                                            "evidence_sha256": "0" * 64}
            with self.subTest(peer=peer), self.assertRaisesRegex(ValueError, "peer HNLO forbidden"):
                adapt_synthetic_bundle(rehash(b))

    def test_input_permutations_preserve_entire_adaptation_and_queue(self):
        original = synthetic_bundle()
        expected = adapt_synthetic_bundle(original)
        for order in itertools.permutations(range(3)):
            b = copy.deepcopy(original)
            b["reports"] = [b["reports"][i] for i in order]
            for r in b["reports"]:
                r["rows"].reverse()
                r["planned_ids"].reverse()
            for items in (b["inputs"], b["evidence"], b["manifest"]["samples"],
                          b["manifest"]["sources"], b["manifest"]["planned_ids"],
                          b["selection"]["entries"]):
                items.reverse()
            actual = adapt_synthetic_bundle(b)
            self.assertEqual(actual, expected)
            self.assertEqual(queue(actual), queue(expected))

    def test_gt_paths_domains_raw_and_approval_cannot_enter_contract(self):
        for field in ("ground_truth", "true_safety_level", "domain", "filename", "raw", "approved"):
            for location in ("bundle", "manifest", "selection", "report", "row"):
                b = synthetic_bundle()
                target = {"bundle": b, "manifest": b["manifest"], "selection": b["selection"],
                          "report": b["reports"][1], "row": b["reports"][1]["rows"][0]}[location]
                target[field] = "Level01"
                with self.subTest(field=field, location=location), self.assertRaisesRegex(ValueError, "fields"):
                    adapt_synthetic_bundle(rehash(b))

    def test_unknown_but_consistently_hashed_content_cannot_activate_real_data(self):
        b = synthetic_bundle()
        b["reports"][2]["rows"][0]["predicted_safety_level"] = "Level01"
        with self.assertRaisesRegex(ValueError, "unregistered.*activation is unavailable"):
            adapt_synthetic_bundle(rehash(b))
        b = synthetic_bundle()
        b["selection"]["authority_id"] = "Owner-approved-real-TRAIN160"
        with self.assertRaisesRegex(ValueError, "unregistered"):
            adapt_synthetic_bundle(b)

    def test_inputs_are_immutable_on_success_and_failure_and_outputs_frozen(self):
        for broken in (False, True):
            b = synthetic_bundle()
            if broken:
                b["inputs"][0]["content"] = "corrupt"
            before = copy.deepcopy(b)
            if broken:
                with self.assertRaises(ValueError):
                    adapt_synthetic_bundle(b)
            else:
                a = adapt_synthetic_bundle(b)
                with self.assertRaises(FrozenInstanceError):
                    a.sources[0].report_sha256 = "changed"
                q = queue(a)
                q["cases"].clear()
                self.assertEqual(len(queue(a)["cases"]), 4)
            self.assertEqual(b, before)

    def test_adapter_has_no_file_network_process_or_model_side_effects(self):
        b = synthetic_bundle()
        with patch("builtins.open", side_effect=AssertionError("file access")), \
             patch("io.open", side_effect=AssertionError("file access")), \
             patch("socket.socket", side_effect=AssertionError("network")), \
             patch("subprocess.Popen", side_effect=AssertionError("process")):
            queue(adapt_synthetic_bundle(b))
            for invalid in ("data/processed/private/report.json", Path("private.zip"), b"{}", None,
                            {"approved": True, "path": "TEST"}):
                with self.assertRaises(ValueError):
                    adapt_synthetic_bundle(invalid)

    def test_import_and_demo_do_not_import_model_backends(self):
        code = (
            "import sys; from scripts.demo_triage_adapter_cpu import build_report; "
            "build_report(case='complete', budget=2, tie_key=b'public'); "
            "assert not any(n.startswith(('safeshift.pilot', 'torch', 'transformers', "
            "'safeshift.candidate')) for n in sys.modules)"
        )
        result = subprocess.run([sys.executable, "-S", "-B", "-c", code], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_manifest_inputs_selection_and_evidence_rejected(self):
        for collection in ("samples", "sources", "inputs", "selection", "evidence"):
            b = synthetic_bundle()
            items = {"samples": b["manifest"]["samples"], "sources": b["manifest"]["sources"],
                     "inputs": b["inputs"], "selection": b["selection"]["entries"],
                     "evidence": b["evidence"]}[collection]
            items.append(copy.deepcopy(items[0]))
            with self.subTest(collection=collection), self.assertRaisesRegex(ValueError, "duplicate"):
                adapt_synthetic_bundle(rehash(b))

    def test_unreferenced_evidence_and_failure_claiming_valid_hnlo_rejected(self):
        b = synthetic_bundle()
        proof = copy.deepcopy(b["evidence"][0])
        proof["value"] = 10
        b["evidence"].append(proof)
        with self.assertRaisesRegex(ValueError, "unreferenced"):
            adapt_synthetic_bundle(b)
        b = synthetic_bundle()
        b["reports"][0]["rows"][0].update(status="INVALID", predicted_safety_level=None)
        with self.assertRaisesRegex(ValueError, "VALID HNLO requires SUCCESS"):
            adapt_synthetic_bundle(rehash(b))

    def test_roles_and_source_identity_cannot_be_reassigned(self):
        b = synthetic_bundle()
        b["manifest"]["sources"][2]["role"] = "focal"
        with self.assertRaisesRegex(ValueError, "exactly one focal"):
            adapt_synthetic_bundle(rehash(b))
        b = synthetic_bundle()
        b["reports"][1]["source_id"] = "unselected-source"
        with self.assertRaisesRegex(ValueError, "three sources"):
            adapt_synthetic_bundle(b)

    def test_public_identity_fields_cannot_contain_paths_or_free_text(self):
        b = synthetic_bundle()
        b["manifest"]["sources"][0]["identity"]["run_id"] = "private/Level04/run"
        with self.assertRaisesRegex(ValueError, "sanitized public fixture identifier"):
            adapt_synthetic_bundle(rehash(b))

    def test_provenance_receipt_is_separate_and_verifiable(self):
        b = synthetic_bundle()
        a = adapt_synthetic_bundle(b)
        self.assertEqual(a.fixture_sha256, fixture_sha256(b))
        self.assertEqual(a.selection_sha256, fixture_sha256(b["selection"]))
        self.assertEqual(a.manifest_sha256, fixture_sha256(b["manifest"]))
        for source in a.sources:
            r = next(r for r in b["reports"] if r["source_id"] == source.source_id)
            self.assertEqual(source.report_sha256, fixture_sha256(r))
            self.assertEqual(source.row_sha256, tuple((row["sample_id"], fixture_sha256(row)) for row in r["rows"]))
        serialized_queue = json.dumps(queue(a))
        for field in ("content", "input_sha256", "evidence_sha256", "authority_id", "selection_id"):
            self.assertNotIn('"' + field + '"', serialized_queue)


class AdapterDemoTests(unittest.TestCase):
    def test_actual_cli_stdlib_only_empty_working_directory(self):
        code = ("import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); "
                "runpy.run_module('scripts.demo_triage_adapter_cpu',run_name='__main__')")
        with tempfile.TemporaryDirectory() as empty:
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(ROOT),
                                     "--budget", "2", "--tie-seed", KEY.decode()],
                                    cwd=empty, capture_output=True, text=True, check=False)
            self.assertEqual(list(Path(empty).iterdir()), [])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), json.loads(json.dumps(
                         build_report(case="complete", budget=2, tie_key=KEY))))

    def test_cli_has_no_real_input_switch_and_requires_policy(self):
        for args in ([], ["--input", "private.json"], ["--approved", "true"],
                     ["--budget", "-1", "--tie-seed", "public"],
                     ["--budget", "2", "--tie-seed", ""]):
            result = subprocess.run([sys.executable, "-S", "-B", "-m", "scripts.demo_triage_adapter_cpu", *args],
                                    cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
