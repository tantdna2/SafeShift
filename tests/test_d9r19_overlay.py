"""Current implementation delta and immutable historical evidence protection."""

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = "5538064e6ea015f8c15475d488064cae95461cd0"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def base(path):
    return json.loads(subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT))


class OverlayTests(unittest.TestCase):
    def test_exact_authorized_delta_in_current_overlays(self):
        policy = load("configs/pre_freeze/production_execution_policy.d9r19.v1.json")
        for path in ("configs/pre_freeze/local_models.d9.json", "configs/pre_freeze/freeze_manifest.d9.template.json"):
            old, new = base(path), load(path)
            self.assertEqual(new["backups_in_order"], old["backups_in_order"])
            self.assertEqual(new["exploratory_grounding_track"], old["exploratory_grounding_track"])
            self.assertEqual(new["primary_models"][-1], old["primary_models"][-1])
            for previous, current in zip(old["primary_models"][:4], new["primary_models"][:4]):
                entry = next(r for r in policy["classification"].values() if r["model_id"] == current["model_id"])
                expected = dict(previous)
                for field in ("decoding_policy_id", "precision_or_quantization", "preprocessing_id"):
                    expected[field] = entry[field]
                expected.update(production_adapter_classification="IMPLEMENTED_STRICT_SYNTHETIC_VALIDATED",
                                classification_adapter_version=entry["adapter_version"],
                                classification_parser_version=entry["parser_version"],
                                execution_policy_scope="CLASSIFICATION_ONLY; GROUNDING_BLOCKED")
                if "production_adapter_status" in expected:
                    expected["production_adapter_status"] = "CLASSIFICATION_IMPLEMENTED_GROUNDING_NOT_QUALIFIED"
                self.assertEqual(current, expected)
            allowed = {"primary_models", "production_implementation_overlay", "classification_state_semantics", "current_status_overlay"}
            self.assertEqual({k: v for k, v in new.items() if k not in allowed},
                             {k: v for k, v in old.items() if k not in allowed})

    def test_pending_freeze_and_honest_checklist(self):
        roster = load("configs/pre_freeze/local_models.d9.json")
        freeze = load("configs/pre_freeze/freeze_manifest.d9.template.json")
        checklist = roster["d9_checklist"]
        for key, value in checklist.items():
            if key[0] in "3478":
                self.assertEqual(value, "PENDING")
            if key[0] in "125":
                self.assertEqual(value, "COMPLETE")
        self.assertTrue(all(v == "PENDING" for v in freeze["frozen_components"].values()))
        self.assertFalse(roster["inspecsafe_inference_authorized"])
        self.assertFalse(freeze["inspecsafe_inference_authorized"])
        self.assertFalse(roster["backups_in_order"][0]["activated"])

    def test_historical_artifacts_and_native_runner_bytes_unchanged(self):
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE,
            "configs/pre_freeze", "safeshift/runners", "safeshift/qualification", "safeshift/protocol/schema.py",
            "safeshift/protocol/prompts.py", "tests/fixtures/pre_freeze/classification_qualification_v1"], cwd=ROOT, text=True).splitlines()
        allowed = {"configs/pre_freeze/local_models.d9.json", "configs/pre_freeze/freeze_manifest.d9.template.json"}
        for path in paths:
            if path in allowed:
                continue
            actual = subprocess.check_output(["git", "hash-object", "--path=" + path, path], cwd=ROOT)
            expected = subprocess.check_output(["git", "rev-parse", f"{BASE}:{path}"], cwd=ROOT)
            self.assertEqual(actual, expected, path)

    def test_decisions_and_tasks_append_only(self):
        for path in ("DECISIONS.md", "TASKS.md"):
            before = subprocess.check_output(["git", "cat-file", "--filters", f"{BASE}:{path}"], cwd=ROOT)
            self.assertTrue((ROOT / path).read_bytes().startswith(before))

    def test_no_dataset_or_media_in_changes(self):
        paths = subprocess.check_output(["git", "diff", "--name-only", BASE], cwd=ROOT, text=True).splitlines()
        self.assertFalse(any(p.startswith("data/") or p.endswith((".png", ".jpg", ".zip", ".safetensors")) for p in paths))


if __name__ == "__main__":
    unittest.main()
