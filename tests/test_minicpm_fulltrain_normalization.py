import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

from safeshift.pilot.contract import LEVELS, PROMPT_SHA, digest, json_bytes, parse_label
from scripts import normalize_minicpm_fulltrain as normalization


class ExactResponseTests(unittest.TestCase):
    def test_normal_description_is_c1_invalid_and_maps_to_level04(self):
        raw = ' { "safety_level" : "no abnormalities observed" }\n'
        self.assertIsNone(parse_label(raw))
        self.assertEqual(normalization.normalize_response(raw), "Level04")

    def test_canonical_labels_are_preserved(self):
        for label in LEVELS:
            with self.subTest(label=label):
                raw = json.dumps({"safety_level": label})
                self.assertEqual(normalization.normalize_response(raw), parse_label(raw))

    def test_rejects_every_out_of_rule_response(self):
        exact = '{"safety_level":"no abnormalities observed"}'
        for raw in (
            exact[:-1], exact + " trailing", "```json\n" + exact + "\n```", "", None, exact.encode(),
            '[[' + '"safety_level","no abnormalities observed"' + ']]', '[' + exact + ']',
            '{"safety_level":"no abnormalities observed","safety_level":"no abnormalities observed"}',
            '{"safety_level":"no abnormalities observed","extra":0}',
            '{"safety_level":"Level04","safety_level":"Level04"}',
            '{"safety_level":"Level04","extra":0}',
            '{"Safety_level":"no abnormalities observed"}',
            '{"safety_level":"No abnormalities observed"}',
            '{"safety_level":"no abnormalities observed "}',
            '{"safety_level":"no  abnormalities observed"}',
            '{"safety_level":"normal"}', '{"safety_level":"level04"}',
            '{"safety_level":["no abnormalities observed"]}', '{"safety_level":null}',
            '{"safety_level":NaN}',
        ):
            with self.subTest(raw=raw):
                self.assertIsNone(normalization.normalize_response(raw))


class BuildTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.primary = self.root / "primary"
        self.mirror = self.root / "mirror"
        self.output = self.root / "data/processed/result"
        self.primary.mkdir()
        self.mirror.mkdir()
        self.cohort = {"schema": normalization.COHORT_SCHEMA, "split": "TRAIN", "samples": [
            {"sample_id": f"synthetic-{ordinal}", "ordinal": ordinal, "image_sha256": digest(ordinal)}
            for ordinal in range(5)
        ]}
        self.records = [{"sample_id": s["sample_id"], "image_sha256": s["image_sha256"], "status": "SUCCESS",
                         "label": label, "raw_sha256": digest(label), "attempts": 1, "native_calls": 1}
                        for s, label in zip(self.cohort["samples"], LEVELS)]
        invalid = self.cohort["samples"][-1]
        self.raw = {"response": '{"safety_level":"no abnormalities observed"}', "identity": {
            "sample_id": invalid["sample_id"], "input_sha256": invalid["image_sha256"],
            "run_id": "synthetic-run", "manifest_sha256": digest(self.cohort)}}
        self.records.append({"sample_id": invalid["sample_id"], "image_sha256": invalid["image_sha256"],
                             "status": "INVALID", "label": None, "raw_sha256": digest(self.raw),
                             "attempts": 1, "native_calls": 1})
        self.archive_name = "custody/1/synthetic.zip"

    def fixture(self):
        archive = self.primary / self.archive_name
        archive.parent.mkdir(parents=True)
        with ZipFile(archive, "w") as stream:
            stream.writestr("calls/000004/run/samples/000000/raw.json", json_bytes(self.raw))
        registration = {"schema": "synthetic-offline", "initial": {"cohort": self.cohort}}
        history = {"run_id": "synthetic-run", "attempt_id": "synthetic-attempt", "series_id": "synthetic-series",
                   "identity": {"prompt_sha256": PROMPT_SHA}, "cohort_sha256": digest(self.cohort),
                   "records": self.records}
        event = {"schema": registration["schema"], "number": 1, "previous": digest(registration),
                 "kind": normalization.fast.v5.PROVISIONAL, "payload": {"attempt": self.archive_name,
                 "ticket_sha256": digest("synthetic-ticket"), "verification": {"report": {
                     "attempt_sha256": normalization.sha(archive), "history": [history]}}}}
        for root in (self.primary, self.mirror):
            (root / "registration.json").write_bytes(json_bytes(registration))
            (root / "event-000001.json").write_bytes(json_bytes(event))
        other = self.mirror / self.archive_name
        other.parent.mkdir(parents=True)
        other.write_bytes(archive.read_bytes())
        return {**normalization.PARENT, "registration_sha256": digest(registration), "head_event": 1,
                "head_sha256": digest(event), "cohort_sha256": digest(self.cohort),
                "invalid_raw_sha256_list_digest": digest([r["raw_sha256"] for r in self.records
                                                          if r["status"] == "INVALID"])}

    def build(self, parent, output=None):
        return normalization.build(self.primary, self.mirror, output or self.output, parent=parent, repo=self.root)

    def assert_rejected(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.build(self.fixture())
        self.assertFalse(self.output.exists())

    def test_retains_original_data_and_is_byte_reproducible(self):
        parent = self.fixture()
        original = {p: p.read_bytes() for root in (self.primary, self.mirror) for p in root.rglob("*") if p.is_file()}
        result = self.build(parent)
        second = self.output.with_name("second")
        self.assertEqual(self.build(parent, second), result)
        self.assertEqual(self.build(parent), result)
        self.assertEqual({p: p.read_bytes() for p in original}, original)
        for path in self.output.iterdir():
            self.assertEqual(path.read_bytes(), (second / path.name).read_bytes())
            expected = result["receipt_sha256"] if path.name == "receipt.json" else result["files"][path.name]["sha256"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        payload = json.loads((self.output / "predictions.json").read_bytes())
        rows = payload["samples"]
        for old, new in zip(self.records[:-1], rows[:-1]):
            self.assertEqual(old, {key: new[key] for key in old})
            self.assertFalse(new["normalization_applied"])
        self.assertEqual([r["ordinal"] for r in rows], list(range(5)))
        self.assertEqual((rows[-1]["original_status"], rows[-1]["original_label"]), ("INVALID", None))
        self.assertEqual((rows[-1]["status"], rows[-1]["label"]), ("SUCCESS", "Level04"))
        self.assertEqual(result["summary"]["before"]["SUCCESS"], 4)
        self.assertEqual(result["summary"]["after"]["SUCCESS"], 5)
        self.assertEqual(result["summary"]["after"]["Level04"], 2)
        rows = list(csv.DictReader(io.StringIO((self.output / "conversions.csv").read_text())))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["raw_sha256"], digest(self.raw))

    def test_rejects_wrong_id(self):
        self.records[0]["sample_id"] = "wrong"
        self.assert_rejected("ID or order mismatch")

    def test_rejects_missing_id(self):
        self.records.pop()
        self.assert_rejected("Missing parent IDs")

    def test_rejects_duplicate_id(self):
        self.records[1] = self.records[0].copy()
        self.assert_rejected("ID or order mismatch")

    def test_rejects_swapped_ids(self):
        self.records[0], self.records[1] = self.records[1], self.records[0]
        self.assert_rejected("ID or order mismatch")

    def test_rejects_duplicate_cohort_id(self):
        self.cohort["samples"][1]["sample_id"] = self.records[0]["sample_id"]
        self.assert_rejected("Duplicate cohort ID")

    def test_rejects_wrong_image_hash(self):
        self.records[0]["image_sha256"] = digest("wrong")
        self.assert_rejected("Image SHA256 mismatch")

    def test_rejects_wrong_raw_hash(self):
        self.records[-1]["raw_sha256"] = digest("wrong")
        self.assert_rejected("Raw SHA256 mismatch")

    def test_rejects_wrong_raw_identity(self):
        self.raw["identity"]["sample_id"] = "wrong"
        self.records[-1]["raw_sha256"] = digest(self.raw)
        self.assert_rejected("Raw identity mismatch")

    def test_rejects_canonical_or_other_invalid_raw_as_a_conversion(self):
        self.raw["response"] = '{"safety_level":"Level04"}'
        self.records[-1]["raw_sha256"] = digest(self.raw)
        self.assert_rejected("outside the authorized mapping")

    def test_rejects_wrong_head_cohort_and_invalid_list_pins(self):
        parent = self.fixture()
        for key, message in (("head_sha256", "CUSTODY_BYTES_CHANGED"), ("cohort_sha256", "Cohort SHA256 mismatch"),
                             ("invalid_raw_sha256_list_digest", "INVALID raw SHA256 list digest mismatch")):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, message):
                self.build({**parent, key: digest("wrong")})
        self.assertFalse(self.output.exists())

    def test_rejects_changed_mirror_archive(self):
        parent = self.fixture()
        (self.mirror / self.archive_name).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "CUSTODY_BYTES_CHANGED"):
            self.build(parent)
        self.assertFalse(self.output.exists())

    def test_fails_closed_on_existing_conflicting_output(self):
        parent = self.fixture()
        self.build(parent)
        path = self.output / "summary.csv"
        path.write_bytes(b"conflict")
        with self.assertRaisesRegex(ValueError, "Existing output differs"):
            self.build(parent)
        self.assertEqual(path.read_bytes(), b"conflict")

    def test_refuses_output_outside_ignored_location(self):
        with self.assertRaises(ValueError):
            self.build(self.fixture(), self.root / "outside")
        self.assertFalse((self.root / "outside").exists())


if __name__ == "__main__":
    unittest.main()
