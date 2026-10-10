"""Static experimental prompt checks; no model, GPU or dataset access."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest

from safeshift.protocol import classification_policy as policy

ROOT = Path(__file__).resolve().parents[1]
BASE = "d93a1fc0b529a832da887a69687cf7d209a8aacd"
ORIGINAL_SHA256 = "816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3"
EXPERIMENTAL = "prompts/p2_classification_c1_evidence_gate_experimental_v1.txt"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


class EvidenceGateExperimentalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = (ROOT / policy.PROMPT_PATH).read_bytes()
        cls.experimental = (ROOT / EXPERIMENTAL).read_text(encoding="utf-8")

    def test_official_c1_bytes_hash_and_production_binding_unchanged(self):
        self.assertEqual(self.original, git("show", f"{BASE}:{policy.PROMPT_PATH}"))
        self.assertEqual(hashlib.sha256(self.original).hexdigest(), ORIGINAL_SHA256)
        self.assertEqual(policy.PROMPT_SHA256, ORIGINAL_SHA256)
        self.assertEqual(policy.PROMPT_PATH, "prompts/p2_classification_c1_v1.txt")
        self.assertEqual(policy.PROMPT_VERSION, "p2-classification-c1-v1")
        for model in policy.MODELS:
            with self.subTest(model=model):
                self.assertEqual(policy.render_prompt(model).encode("utf-8"), self.original)

    def test_only_evidence_gate_is_added_to_original_c1(self):
        header = "Evidence gate (EXPERIMENTAL):\n"
        self.assertEqual(self.experimental.count(header), 1)
        start = self.experimental.index(header)
        end = self.experimental.index("\n\n", start) + 2
        self.assertEqual(self.experimental[:start] + self.experimental[end:],
                         self.original.decode("utf-8"))
        self.assertEqual(end, self.experimental.index("Assess the safety level"))

    def test_five_industry_table_four_definitions_and_mapping_unchanged(self):
        original = self.original.decode("utf-8")
        table = lambda text: [line for line in text.splitlines() if line.startswith("|")]
        self.assertEqual(table(self.experimental), table(original))
        self.assertEqual(len(table(self.experimental)), 5)
        self.assertEqual(table(self.experimental)[0].split("|")[2:-1],
                         [" Oil & Gas / Chemical ", " Coal Conveyor Gallery ",
                          " Tunnel ", " Power ", " Metallurgy "])
        definitions = [line for line in original.splitlines() if line.startswith("   - ")]
        self.assertEqual(len(definitions), 4)
        self.assertEqual([line for line in self.experimental.splitlines()
                          if line.startswith("   - ")], definitions)
        for source, level in zip(("Level one", "Level two", "Level three",
                                  "no abnormalities observed"),
                                 ("Level01", "Level02", "Level03", "Level04")):
            self.assertIn(f"{source} -> {level}", self.experimental)

    def test_visible_hazard_required_before_classification(self):
        gate = self.experimental.split("Evidence gate (EXPERIMENTAL):\n", 1)[1].split("\n\n", 1)[0]
        for requirement in (
            "Before selecting Level01, Level02, or Level03, identify at least one specific hazard actually visible in the image.",
            "Do not treat machinery, industrial equipment, or normal activity as a hazard without visible evidence of an abnormality.",
            "Do not infer hazards that are not visible in the image.",
            "If no observable hazard is present, select Level04.",
            "If an observable hazard is present, apply the unchanged four-category definitions and five-industry assessment criteria below.",
            "Complete this evidence check before choosing the safety level; do not output the check or any explanation.",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, gate)

    def test_output_still_one_json_with_only_safety_level(self):
        output_instruction = self.experimental.splitlines()[-1]
        self.assertEqual(output_instruction, self.original.decode("utf-8").splitlines()[-1])
        self.assertIn('Return only one JSON object with exactly the key "safety_level"', output_instruction)
        self.assertIn("Do not include descriptions, explanations, code fences or additional keys.", output_instruction)
        examples = re.findall(r"\{[^{}]*\}", self.experimental)
        self.assertEqual(examples, ['{"safety_level":"Level01"}'])
        self.assertEqual(json.loads(examples[0]), {"safety_level": "Level01"})

    def test_official_p2_p21_protocol_unchanged_from_base(self):
        for path in (
            "safeshift/protocol/classification_policy.py", policy.POLICY_PATH,
            "configs/frozen/p2_execution_authority.v4.json",
            "configs/frozen/internvl3_p21_execution_plan.v1.json",
            "configs/frozen/p21_protocol_amendment.v1.json",
            "safeshift/protocol/schema.py", "safeshift/protocol/p21_schema.py",
            "safeshift/runners/production_classification.py",
            "safeshift/runners/p21_classification.py",
            "safeshift/runners/p21_authority.py", "safeshift/runners/internvl3.py",
            "safeshift/runners/p2_harness.py", "safeshift/runners/p2_bridge.py",
        ):
            with self.subTest(path=path):
                self.assertEqual((ROOT / path).read_bytes(), git("show", f"{BASE}:{path}"))


if __name__ == "__main__":
    unittest.main()
