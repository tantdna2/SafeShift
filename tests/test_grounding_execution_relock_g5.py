"""G5 governance only: synthetic/fake evidence, no venue or model imports."""

import ast
import builtins
from pathlib import Path
import subprocess
from types import ModuleType
import unittest
from unittest.mock import patch

from safeshift.runners import grounding_multicategory_v3 as r

ROOT = Path(__file__).resolve().parents[1]
BASE = "b3bf4dc770c1b87a9e353a75aab759f67641c2c2"
FAKE_HEAD = "a" * 40


def base_bytes(name):
    return subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)


class RelockTests(unittest.TestCase):
    def setUp(self):
        self.key = "qwen3"
        self.run_id = r.RUN_IDS[self.key]
        self.lock = r.read_json(ROOT / r.RUNTIME_LOCK)
        revision = r.MODELS[self.key][1]
        self.env = {
            "schema_version": "grounding-v3-environment-observation-v1",
            "model_key": self.key, "model_id": r.MODELS[self.key][0],
            "revision": revision, "processor_revision": revision, "tokenizer_revision": revision,
            "observed": True, "git_commit": FAKE_HEAD, "cuda": "FAKE_TEST_ONLY",
            "hardware": [{"name": "Tesla T4", "compute_capability": [7, 5]}] * 2,
            "software_versions": {k: "FAKE_TEST_ONLY" for k in
                                  ("python", "torch", "tokenizers", "Pillow", "accelerate", "huggingface-hub", "safetensors")},
            "snapshot_files": {k: {"sha256": "0" * 64, "size_bytes": 1} for k in
                               ("config.json", "generation_config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json")},
            "generation_config": r.DECODING, "code_and_contract_hashes": self.lock["sha256"],
        }
        self.env["software_versions"]["transformers"] = "4.57.1"
        self.authority = {
            "execution_authorized": True, "model_key": self.key, "run_id": self.run_id,
            "head_sha": FAKE_HEAD, "main_sha": BASE,
            "environment_sha256": r.sha(r.encode(self.env)),
            "runtime_lock_sha256": r.text_hash(ROOT / r.RUNTIME_LOCK),
            "internet_off_attested": True, "research_lead": "FAKE_LEAD",
            "independent_auditor": "FAKE_AUDITOR", "review_reference": "OFFLINE_TEST_ONLY",
        }

    def git(self, repo, *args):
        if args == ("rev-parse", "HEAD"):
            return FAKE_HEAD
        if args[0] == "status":
            return ""
        return BASE

    def check(self, environment, authority):
        return r.preflight(ROOT, self.key, self.run_id, environment, authority, images=False)

    def test_g4_actual_guard_is_blocked_after_merge(self):
        # Execute the original Git blob, without changing its BASE or guard.
        old = ModuleType("safeshift.runners.g4_historical_test")
        old.__file__ = str(ROOT / r.RUNNER)
        exec(compile(base_bytes(r.RUNNER), "G4_GIT_BLOB", "exec"), old.__dict__)
        self.assertEqual(old.BASE, "685021ef974cc3feef968d7e920e7720ce6349f2")
        with patch.object(old, "frozen", return_value=r.frozen(ROOT)), patch.object(old, "git", side_effect=self.git):
            with self.assertRaisesRegex(ValueError, "MAIN_IDENTITY_CHANGED"):
                old.preflight(ROOT, self.key, self.run_id, images=False)

    def test_g5_accepts_base_identity_with_exact_fake_authority(self):
        self.assertEqual(r.BASE, BASE)
        with patch.object(r, "git", side_effect=self.git):
            self.assertEqual(self.check(self.env, self.authority)["status"], "PREFLIGHT_PASS")
        # This is a static test, not qualification or a real environment approval.

    def test_missing_environment_or_authorization_blocks(self):
        with patch.object(r, "git", side_effect=self.git):
            for env, auth in ((None, self.authority), (self.env, None), (None, None)):
                with self.subTest(env_missing=env is None, auth_missing=auth is None):
                    self.assertEqual(self.check(env, auth)["status"], "BLOCKED")

    def test_authority_mutations_block(self):
        mutations = {
            "head_sha": ("b" * 40, "AUTHORITY_GIT_IDENTITY"),
            "main_sha": ("b" * 40, "AUTHORITY_GIT_IDENTITY"),
            "environment_sha256": ("f" * 64, "APPROVED_ENVIRONMENT_HASH"),
            "runtime_lock_sha256": ("f" * 64, "APPROVED_RUNTIME_LOCK"),
            "execution_authorized": (False, "EXECUTION_NOT_AUTHORIZED"),
            "internet_off_attested": (False, "VENUE_OFFLINE_ATTESTATION"),
            "independent_auditor": (" fake_lead ", "INDEPENDENT_REVIEW_REQUIRED"),
            "run_id": ("g4-qwen3-v3-001", "AUTHORITY_SCOPE"),
        }
        with patch.object(r, "git", side_effect=self.git):
            for field, (value, reason) in mutations.items():
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, reason):
                    self.check(self.env, {**self.authority, field: value})

    def test_wrong_main_or_non_descendant_or_base_head_blocks(self):
        for target, value, reason in (
            (("rev-parse", "origin/main"), "b" * 40, "MAIN_IDENTITY_CHANGED"),
            (("merge-base", BASE, FAKE_HEAD), "b" * 40, "HEAD_NOT_DESCENDED"),
            (("rev-parse", "HEAD"), BASE, "HEAD_NOT_DESCENDED"),
        ):
            def git(repo, *args):
                return value if args == target else self.git(repo, *args)
            with self.subTest(target=target), patch.object(r, "git", side_effect=git):
                with self.assertRaisesRegex(ValueError, reason):
                    self.check(self.env, self.authority)

    def test_predeclared_run_id_cannot_follow_outputs(self):
        with patch.object(r, "git", side_effect=self.git), self.assertRaisesRegex(ValueError, "PREDECLARED_RUN_ID"):
            r.preflight(ROOT, self.key, "g5-qwen3-v3-002", self.env,
                        {**self.authority, "run_id": "g5-qwen3-v3-002"}, images=False)

    def test_model_import_and_load_unreachable_before_full_preflight(self):
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "transformers"}:
                raise AssertionError("MODEL_IMPORT_BEFORE_PREFLIGHT")
            return original_import(name, *args, **kwargs)
        original_preflight = r.preflight
        def static(*args, **kwargs):
            return original_preflight(*args, **kwargs, images=False)
        with patch.object(builtins, "__import__", side_effect=guarded), \
             patch.object(r, "git", side_effect=self.git), patch.object(r, "preflight", side_effect=static), \
             patch.object(r, "NativeRuntime") as native, patch.object(r, "inspect_environment") as observation:
            for field in self.authority:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    r.execute(ROOT, self.key, self.run_id, self.env, {**self.authority, field: None}, [])
            with self.assertRaisesRegex(ValueError, "EXECUTION_BLOCKED"):
                r.execute(ROOT, self.key, self.run_id, None, None, [])
            native.assert_not_called()
            observation.assert_not_called()

    def test_observation_checks_main_before_torch(self):
        original_import = builtins.__import__
        def guarded(name, *args, **kwargs):
            if name == "torch":
                raise AssertionError("GPU_IMPORT_BEFORE_IDENTITY")
            return original_import(name, *args, **kwargs)
        def wrong_main(repo, *args):
            return "b" * 40 if args == ("rev-parse", "origin/main") else self.git(repo, *args)
        with patch.object(builtins, "__import__", side_effect=guarded), patch.object(r, "git", side_effect=wrong_main):
            with self.assertRaisesRegex(ValueError, "MAIN_IDENTITY_CHANGED"):
                r.inspect_environment(ROOT, self.key, "data/processed/unused")

    def test_g3_g4_history_and_scientific_code_unchanged(self):
        old_lock = r.read_json(ROOT / "configs/pre_freeze/grounding_multicategory_runtime_lock.v1.json")
        names = set(old_lock["sha256"]) - {r.RUNNER, "scripts/run_grounding_multicategory_v3.py"}
        names |= {"configs/pre_freeze/grounding_multicategory_runtime_lock.v1.json",
                  "notes/w2_d9r19g4_multicategory_runtime_prep.md"}
        for name in names:
            self.assertEqual((ROOT / name).read_bytes().replace(b"\r\n", b"\n"), base_bytes(name), name)
        before = ast.parse(base_bytes(r.RUNNER))
        after = ast.parse((ROOT / r.RUNNER).read_text(encoding="utf-8"))
        changed = {"frozen", "preflight", "inspect_environment"}
        current = {node.name: ast.dump(node) for node in after.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        for node in before.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name not in changed:
                self.assertEqual(ast.dump(node), current[node.name], node.name)
        for name, digest in self.lock["historical_g4"]["sha256"].items():
            self.assertEqual(r.sha(base_bytes(name)), digest)
        self.assertEqual(old_lock["base_sha"], "685021ef974cc3feef968d7e920e7720ce6349f2")
        self.assertFalse(old_lock["execution_authorized"])
        self.assertEqual(old_lock["QUALIFICATION_EXECUTION"], "NOT_RUN")

    def test_templates_are_unverified_not_authorization(self):
        plan = r.read_json(ROOT / r.EXECUTION_PLAN)
        auth = r.read_json(ROOT / plan["authorization_template"])
        self.assertFalse(auth["execution_authorized"])
        self.assertIsNone(auth["head_sha"])
        self.assertEqual(set(auth), set(plan["authorization_required_fields"]))
        self.assertEqual(plan["run_ids"], r.RUN_IDS)
        self.assertEqual(plan["environment_status"], "UNVERIFIED_EXTERNAL_VENUE_LOCK_PENDING")
        self.assertFalse(plan["execution_authorized"])
        self.assertEqual(plan["QUALIFICATION_EXECUTION"], "NOT_RUN")
        for name in ("DECISIONS.md", "TASKS.md"):
            self.assertTrue((ROOT / name).read_bytes().replace(b"\r\n", b"\n").startswith(base_bytes(name)))


if __name__ == "__main__":
    unittest.main()
