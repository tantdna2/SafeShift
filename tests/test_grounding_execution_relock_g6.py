"""G6 governance tests: fake/static only; never load models or GPUs."""

import builtins
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from safeshift.runners import grounding_multicategory_v3_g6 as r


ROOT = Path(__file__).resolve().parents[1]
BASE = "069d780b6590a32a19cbe6e341ffa19cedbcd712"
FAKE_HEAD = "a" * 40


class G6RelockTests(unittest.TestCase):
    def setUp(self):
        self.lock = r.read_json(ROOT / r.RUNTIME_LOCK)
        revision = r.MODELS["paligemma"][1]
        self.env = {
            "schema_version": "grounding-v3-environment-observation-v1",
            "model_key": "paligemma", "model_id": r.MODELS["paligemma"][0],
            "revision": revision, "processor_revision": revision, "tokenizer_revision": revision,
            "observed": True, "git_commit": FAKE_HEAD, "main_sha": BASE,
            "cuda": "FAKE_TEST_ONLY",
            "hardware": [{"name": "Tesla T4", "compute_capability": [7, 5]}],
            "software_versions": {k: "FAKE_TEST_ONLY" for k in
                                  ("python", "torch", "tokenizers", "Pillow", "accelerate", "huggingface-hub", "safetensors")},
            "snapshot_files": {k: {"sha256": "0" * 64, "size_bytes": 1} for k in
                               ("config.json", "generation_config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json")},
            "generation_config": r.DECODING, "code_and_contract_hashes": self.lock["sha256"],
        }
        self.env["software_versions"]["transformers"] = "4.57.1"
        self.authority = {
            "execution_authorized": True, "model_key": "paligemma", "run_id": r.RUN_IDS["paligemma"],
            "head_sha": FAKE_HEAD, "main_sha": BASE,
            "environment_sha256": r.sha(r.encode(self.env)),
            "runtime_lock_sha256": r.text_hash(ROOT / r.RUNTIME_LOCK),
            "internet_off_attested": True, "research_lead": "FAKE_LEAD",
            "independent_auditor": "FAKE_AUDITOR", "review_reference": "OFFLINE_TEST_ONLY",
        }

    def fake_git(self, repo, *args):
        if args == ("rev-parse", "HEAD"):
            return FAKE_HEAD
        if args[0] == "status":
            return ""
        return BASE

    def test_g6_is_exact_base_and_paligemma_only(self):
        self.assertEqual(r.BASE, BASE)
        self.assertEqual(r.RUN_IDS, {"paligemma": "g6-paligemma-v3-001"})
        self.assertEqual(r.MODELS["paligemma"], ("google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1"))
        with self.assertRaisesRegex(ValueError, "G6_PALIGEMMA_ONLY"):
            r.preflight(ROOT, "qwen3", "g6-paligemma-v3-001", images=False)

    def test_exact_fake_authority_passes_static_preflight(self):
        with patch.object(r, "git", side_effect=self.fake_git):
            result = r.preflight(ROOT, "paligemma", r.RUN_IDS["paligemma"], self.env, self.authority, images=False)
        self.assertEqual(result["status"], "PREFLIGHT_PASS")
        self.assertEqual(result["main_sha"], BASE)
        self.assertEqual(result["decoding"]["max_new_tokens"], 512)

    def test_missing_or_false_authority_blocks_without_model_import(self):
        with patch.object(r, "git", side_effect=self.fake_git):
            for env, authority in ((None, self.authority), (self.env, None), (None, None)):
                with self.subTest(env=env is None, authority=authority is None):
                    value = r.preflight(ROOT, "paligemma", r.RUN_IDS["paligemma"], env, authority, images=False)
                    self.assertEqual(value["status"], "BLOCKED")
        with self.assertRaisesRegex(ValueError, "EXECUTION_NOT_AUTHORIZED"):
            with patch.object(r, "git", side_effect=self.fake_git):
                r.preflight(ROOT, "paligemma", r.RUN_IDS["paligemma"], self.env,
                            {**self.authority, "execution_authorized": False}, images=False)

    def test_identity_mutations_block(self):
        with patch.object(r, "git", side_effect=self.fake_git):
            for field, value, reason in (
                ("head_sha", "b" * 40, "AUTHORITY_GIT_IDENTITY"),
                ("main_sha", "b" * 40, "AUTHORITY_GIT_IDENTITY"),
                ("runtime_lock_sha256", "f" * 64, "APPROVED_RUNTIME_LOCK"),
                ("run_id", "g6-paligemma-v3-002", "AUTHORITY_SCOPE"),
                ("independent_auditor", " fake_lead ", "INDEPENDENT_REVIEW_REQUIRED"),
            ):
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, reason):
                    r.preflight(ROOT, "paligemma", r.RUN_IDS["paligemma"], self.env,
                                {**self.authority, field: value}, images=False)

    def test_observation_checks_main_before_torch(self):
        original_import = builtins.__import__

        def guarded(name, *args, **kwargs):
            if name == "torch":
                raise AssertionError("GPU_IMPORT_BEFORE_IDENTITY")
            return original_import(name, *args, **kwargs)

        def wrong_main(repo, *args):
            return "b" * 40 if args == ("rev-parse", "origin/main") else self.fake_git(repo, *args)

        with patch.object(builtins, "__import__", side_effect=guarded), patch.object(r, "git", side_effect=wrong_main):
            with self.assertRaisesRegex(ValueError, "MAIN_IDENTITY_CHANGED"):
                r.inspect_environment(ROOT, "paligemma", "data/processed/unused")

    def test_new_versions_and_template_are_inert_and_history_is_unchanged(self):
        plan = r.read_json(ROOT / r.EXECUTION_PLAN)
        auth = r.read_json(ROOT / plan["authorization_template"])
        self.assertFalse(auth["execution_authorized"])
        self.assertIsNone(auth["head_sha"])
        self.assertEqual(plan["execution_base"], BASE)
        self.assertEqual(plan["run_ids"], r.RUN_IDS)
        self.assertEqual(self.lock["historical_g5_lock"], "configs/pre_freeze/grounding_multicategory_runtime_lock.v2.json")
        for name in ("configs/pre_freeze/grounding_multicategory_runtime_lock.v2.json",
                     "configs/pre_freeze/grounding_multicategory_execution_plan.v1.json",
                     "configs/pre_freeze/grounding_multicategory_authorization.template.v1.json"):
            actual = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            expected = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
            self.assertEqual(actual, expected, name)

    def test_delegated_core_runner_and_firewall_are_locked_without_drift(self):
        core = "safeshift/runners/grounding_multicategory_v3.py"
        firewall = "safeshift/protocol/firewall.py"
        historical = r.read_json(ROOT / "configs/pre_freeze/grounding_multicategory_runtime_lock.v2.json")
        for name in (core, firewall):
            with self.subTest(name=name):
                self.assertIn(name, self.lock["sha256"])
                current = r.text_hash(ROOT / name)
                self.assertEqual(current, self.lock["sha256"][name])
                if name == core:
                    self.assertEqual(self.lock["sha256"][name],
                                     "bcde90c2d7484a24cd4ef17667d98425d3e5360d565752cb35bad88b2bdea246")
                    self.assertEqual(self.lock["sha256"][name], historical["sha256"][name])


if __name__ == "__main__":
    unittest.main()
