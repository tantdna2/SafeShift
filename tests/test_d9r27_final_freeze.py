"""D9R27 authority-gate tests using real temporary Git histories only."""

import ast
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.runners import p2_harness as harness
from safeshift.runners import p2_preflight as preflight

ROOT = Path(__file__).resolve().parents[1]
BASE = "e7628d68f87cf53b5343ea912b7e332064c285af"
REVIEWED_MERGE = "031958a5ce668057f763973a722a3506d73f39f0"
CANDIDATE = "configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json"
AUTHORITY = "configs/frozen/p2_execution_authority.v1.json"
CANDIDATE_SHA = "0901bab9b0dbd648b263071d5fdbd677120880eb91a2a5d4724c064905ab2ec2"


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL).decode().strip()


def git_bytes(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL)


class D9R27FinalFreezeTests(unittest.TestCase):
    def setUp(self):
        self.f1 = json.loads((ROOT / AUTHORITY).read_bytes())["protocol_freeze_commit_sha"]
        # Historical F2 belongs to the reviewed release, even on later branches.
        self.f2 = git(ROOT, "rev-parse", REVIEWED_MERGE + "^2")

    def _clone(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        repo = Path(directory.name)
        subprocess.run(["git", "clone", "-c", "core.autocrlf=false", "--no-local", str(ROOT), str(repo)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.name", "D9R27 synthetic"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "d9r27@example.invalid"], cwd=repo, check=True)
        return repo

    def _commit_from_f1(self, repo, mutate=None):
        authority_bytes = git_bytes(repo, "show", f"{self.f2}:{AUTHORITY}")
        subprocess.run(["git", "switch", "--detach", self.f1], cwd=repo, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        path = repo / AUTHORITY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(authority_bytes)
        if mutate is not None:
            value = json.loads(path.read_bytes())
            mutate(value)
            path.write_bytes(json.dumps(value, indent=2).encode() + b"\n")
        subprocess.run(["git", "add", AUTHORITY], cwd=repo, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "synthetic authority"], cwd=repo,
                       check=True, stdout=subprocess.DEVNULL)
        return git(repo, "rev-parse", "HEAD")

    def _edited_tree(self, repo, tree, changes):
        """Edit only a temporary repository's index; no authority logic is mocked."""
        git(repo, "read-tree", tree)
        for path, content in changes.items():
            blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"],
                                           cwd=repo, input=content).decode().strip()
            git(repo, "update-index", "--add", "--cacheinfo", "100644", blob, path)
        return git(repo, "write-tree")

    def _merge_fixture(self, *, parent1=None, parent2=None, merge_tree=None,
                       authority_mutate=None, parent2_mode="valid", dirty=False):
        repo = self._clone()
        if authority_mutate is not None:
            parent2 = self._commit_from_f1(repo, mutate=authority_mutate)
        elif parent2_mode == "extra_intermediate":
            direct = self._commit_from_f1(repo)
            subprocess.run(["git", "commit", "--allow-empty", "-m", "extra intermediate"],
                           cwd=repo, check=True, stdout=subprocess.DEVNULL)
            parent2 = git(repo, "rev-parse", "HEAD")
            self.assertEqual(git(repo, "rev-parse", f"{parent2}^"), direct)
        elif parent2_mode == "multi_parent":
            tree = git(repo, "rev-parse", f"{self.f2}^{{tree}}")
            parent2 = git(repo, "commit-tree", tree, "-p", self.f1, "-p", BASE, "-m", "multi-parent F2")
        elif parent2_mode == "wrong_parent":
            parent2 = git(repo, "commit-tree", f"{self.f2}^{{tree}}", "-p", BASE, "-m", "skipped F1")
        elif parent2_mode in ("executable_change", "wrong_tree"):
            source = "safeshift/runners/p2_harness.py"
            tree = self._edited_tree(repo, self.f2, {
                source: git_bytes(repo, "show", f"{self.f1}:{source}") + b"\n# post-freeze edit\n"})
            parent2 = git(repo, "commit-tree", tree, "-p", self.f1, "-m", "changed executable")
            if parent2_mode == "wrong_tree":
                # HEAD only adds authority to F1, but differs from parent2's tree.
                merge_tree = git(repo, "rev-parse", f"{self.f2}^{{tree}}")
        elif parent2_mode == "authority_mismatch":
            parent2 = self.f2
            raw = git_bytes(repo, "show", f"{self.f2}:{AUTHORITY}") + b"\n"
            merge_tree = self._edited_tree(repo, self.f2, {AUTHORITY: raw})
        elif parent2_mode == "missing_authority":
            parent2 = git(repo, "commit-tree", f"{self.f1}^{{tree}}", "-p", self.f1,
                          "-m", "missing committed authority")
        else:
            parent2 = parent2 or self.f2
        parent1 = parent1 or BASE
        merge_tree = merge_tree or git(repo, "rev-parse", f"{parent2}^{{tree}}")
        # Restore the clone's index before switching away from its checkout.
        git(repo, "read-tree", "HEAD")
        merge = git(repo, "commit-tree", merge_tree, "-p", parent1, "-p", parent2, "-m", "synthetic merge")
        subprocess.run(["git", "switch", "--detach", merge], cwd=repo, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if dirty:
            target = repo / "safeshift/runners/p2_harness.py"
            target.write_bytes(target.read_bytes() + b"\n# dirty synthetic tracked edit\n")
        return repo

    def test_exact_base_f1_f2_parent_and_authority_only_diff(self):
        self.assertEqual(harness.IMPLEMENTATION_BASE_SHA, BASE)
        self.assertEqual(harness.contract()["implementation_base_sha"], BASE)
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", self.f1).split(), [self.f1, BASE])
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", self.f2).split(), [self.f2, self.f1])
        self.assertEqual(git(ROOT, "diff", "--name-only", self.f1, self.f2), AUTHORITY)
        self.assertNotIn(AUTHORITY, git(ROOT, "ls-tree", "-r", "--name-only", self.f1).splitlines())

    def test_candidate_and_scientific_contract_preservation(self):
        candidate = git_bytes(ROOT, "show", f"{BASE}:{CANDIDATE}")
        self.assertEqual(git_bytes(ROOT, "show", f"HEAD:{CANDIDATE}"), candidate)
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), CANDIDATE_SHA)
        for path in (
            "configs/pre_freeze/d9r22_seminar_scope.v1.json",
            "configs/pre_freeze/production_classification_policy.d9r23.v1.json",
            "configs/pre_freeze/d9r24_metric_contract.v1.json",
            "prompts/p2_classification_c1_v1.txt",
            "safeshift/data/p2_execution.py",
            "safeshift/protocol/p2_evaluation.py",
            "safeshift/protocol/d9r24_metrics.py",
            "safeshift/protocol/reporting.py",
        ):
            self.assertEqual(git_bytes(ROOT, "show", f"HEAD:{path}"), git_bytes(ROOT, "show", f"{BASE}:{path}"), path)
        # Qwen3 runtime amendments may change the active bridge; frozen source
        # remains pinned to its original merge and cannot become rerun authority.
        path = "safeshift/runners/p2_bridge.py"
        self.assertEqual(git_bytes(ROOT, "show", f"{REVIEWED_MERGE}:{path}"),
                         git_bytes(ROOT, "show", f"{BASE}:{path}"))
        contract = harness.contract()
        self.assertEqual(tuple(harness._PRODUCTION_BACKENDS), ("qwen3", "qwen2_5", "internvl3", "moondream"))
        self.assertEqual(contract["primary_grounding"], "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE")
        self.assertEqual(contract["raw_before_parse"], "ATOMIC_EXCLUSIVE_PUBLICATION_FSYNC_HASH_SIZE_REREAD_VERIFIED")
        before = json.loads(git_bytes(ROOT, "show", f"{BASE}:{harness.CONTRACT_PATH}"))
        for key in ("production_backend_registry", "model_payload_fields", "backend_payload_fields",
                    "semantic_retry", "automatic_retry", "resume", "rerun", "shard_algorithm_version"):
            self.assertEqual(contract[key], before[key], key)
        # Prove raw storage/parse order, no-GT execution payload, retry and shard
        # implementation remain unchanged, beyond the configuration assertions.
        def functions(raw):
            return {n.name: ast.dump(n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
        old = functions(git_bytes(ROOT, "show", f"{BASE}:safeshift/runners/p2_harness.py"))
        current = functions((ROOT / "safeshift/runners/p2_harness.py").read_bytes())
        for name in ("production_run", "atomic_new", "verified_raw", "persist_native", "parse_stored", "_execute", "_rerun"):
            self.assertEqual(current[name], old[name], name)

    def test_schema_and_authority_fields(self):
        authority = json.loads((ROOT / AUTHORITY).read_bytes())
        self.assertEqual(authority["schema_version"], "p2-execution-authority-v1")
        self.assertEqual(authority["protocol_freeze_commit_sha"], self.f1)
        self.assertEqual(authority["implementation_base_sha"], BASE)
        self.assertEqual(authority["expected_pre_merge_main_sha"], BASE)
        self.assertEqual(authority["freeze_candidate_path"], CANDIDATE)
        self.assertEqual(authority["freeze_candidate_sha256"], CANDIDATE_SHA)
        self.assertEqual(authority["dataset_fingerprint"], harness.contract()["dataset_fingerprint"])
        self.assertEqual(authority["sample_count"], 5013)
        self.assertEqual(authority["reruns"], [])
        self.assertEqual(authority["authority"], "RESEARCH_LEAD")
        self.assertEqual(authority["status"], "FROZEN")
        self.assertTrue(authority["inspecsafe_inference_authorized"])

    def test_draft_one_parent_fails_and_static_preflight_is_not_ready(self):
        with self.assertRaisesRegex(PermissionError, "FINAL_MERGE_REQUIRED"):
            harness.authorize_production(ROOT)
        result = preflight.static_preflight(ROOT)
        self.assertFalse(result["effective_authorization"])
        self.assertFalse(result["ready_to_run_inspecsafe"])
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["model_load"])
        self.assertEqual(result["runtime_observation"], "NOT_EXECUTED")

    def test_valid_synthetic_standard_merge_passes_actual_authorizer(self):
        repo = self._merge_fixture()
        head, authority = harness.authorize_production(repo)
        self.assertEqual(head, git(repo, "rev-parse", "HEAD"))
        self.assertEqual(authority["protocol_freeze_commit_sha"], self.f1)
        result = preflight.static_preflight(repo)
        self.assertTrue(result["effective_authorization"])
        self.assertTrue(result["ready_to_run_inspecsafe"])
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["model_load"])

    def test_wrong_parent_tree_executable_and_dirty_reject(self):
        wrong_parent = git(ROOT, "rev-parse", f"{BASE}^")
        cases = {
            "FINAL_MERGE_PARENT_1_REQUIRED": self._merge_fixture(parent1=wrong_parent),
            "FINAL_MERGE_TREE_MISMATCH": self._merge_fixture(parent2_mode="wrong_tree"),
            "EXECUTABLE_CHANGED_AFTER_FREEZE": self._merge_fixture(parent2_mode="executable_change"),
            "FINAL_MERGE_AUTHORITY_PARENT_REQUIRED": self._merge_fixture(parent2_mode="authority_mismatch"),
            "DIRTY_EXECUTION_COMMIT": self._merge_fixture(dirty=True),
        }
        for reason, repo in cases.items():
            with self.subTest(reason=reason), self.assertRaisesRegex(PermissionError, reason):
                harness.authorize_production(repo)

    def test_non_direct_and_multi_parent_f2_reject(self):
        for mode in ("wrong_parent", "extra_intermediate", "multi_parent"):
            with self.subTest(mode=mode), self.assertRaisesRegex(
                    PermissionError, "FINAL_MERGE_PARENT_2_MUST_BE_DIRECT_F2_CHILD_OF_FREEZE"):
                harness.authorize_production(self._merge_fixture(parent2_mode=mode))

    def test_authority_mutations_reject(self):
        mutations = {
            "schema": lambda a: a.pop("schema_version"),
            "wrong_schema": lambda a: a.update(schema_version="wrong"),
            "f1": lambda a: a.update(protocol_freeze_commit_sha="a" * 40),
            "base": lambda a: a.update(implementation_base_sha="b" * 40),
            "expected": lambda a: a.update(expected_pre_merge_main_sha="c" * 40),
            "candidate_path": lambda a: a.update(freeze_candidate_path="wrong"),
            "candidate_sha": lambda a: a.update(freeze_candidate_sha256="d" * 64),
            "identity": lambda a: a.update(identity_sha256={}),
            "fingerprint": lambda a: a.update(dataset_fingerprint="e" * 64),
            "count": lambda a: a.update(sample_count=1),
            "reruns": lambda a: a.update(reruns=[{"run_id": "x"}]),
            "authority": lambda a: a.update(authority="OTHER"),
            "status": lambda a: a.update(status="PENDING"),
            "authorized": lambda a: a.update(inspecsafe_inference_authorized=False),
            "protocol": lambda a: a.update(protocol_id="P1"),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name), self.assertRaises(PermissionError):
                harness.authorize_production(self._merge_fixture(authority_mutate=mutation))

    def test_missing_or_untracked_authority_rejects(self):
        repo = self._merge_fixture(parent2_mode="missing_authority")
        path = repo / AUTHORITY
        self.assertFalse(path.exists())
        with self.assertRaises(PermissionError):
            harness.authorize_production(repo)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(git_bytes(ROOT, "show", f"{self.f2}:{AUTHORITY}"))
        self.assertIn("?? " + AUTHORITY, git(repo, "status", "--porcelain", "--untracked-files=all"))
        with self.assertRaises(PermissionError):
            harness.authorize_production(repo)

    def test_production_boundary_and_public_signature(self):
        with patch.object(harness, "verify_dataset", side_effect=AssertionError("DATASET_READ")) as dataset, \
                patch.object(harness, "resolve_production_backend", side_effect=AssertionError("BACKEND_LOAD")) as backend:
            with self.assertRaises(PermissionError):
                harness.production_run(model="moondream", run_id="blocked", dataset_root="missing",
                                       manifest_path="missing", provenance_path="missing", repo=ROOT)
            dataset.assert_not_called()
            backend.assert_not_called()
        names = set(inspect.signature(harness.production_run).parameters)
        self.assertEqual(names, {"model", "run_id", "dataset_root", "manifest_path", "provenance_path",
                                 "shard_count", "shard_index", "repo", "rerun_of"})

    def test_preflight_and_owner_cli_have_no_dataset_model_gpu_network_access(self):
        code = r'''
import builtins, contextlib, io, json, socket, sys
from pathlib import Path
from unittest.mock import patch
original_import = builtins.__import__
def guarded_import(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'accelerate', 'bitsandbytes'}:
        raise AssertionError('MODEL_GPU_IMPORT:' + name)
    return original_import(name, *args, **kwargs)
builtins.__import__ = guarded_import
def forbidden(*args, **kwargs):
    raise AssertionError('DATASET_MODEL_GPU_OR_NETWORK_ACCESS')
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = socket.getaddrinfo = forbidden
from safeshift.runners import p2_harness as h, p2_preflight as p, p2_owner as owner
repo, expected = Path(sys.argv[1]), sys.argv[2] == 'true'
artifact = repo / 'data/processed/benchmark/p2'
assert not artifact.exists()
with patch.object(h, 'verify_dataset', forbidden), patch.object(h, 'resolve_production_backend', forbidden), \
     patch.object(h.ProductionRunnerBridge, 'load', forbidden), patch.object(p, 'runtime_observation', forbidden):
    result = p.static_preflight(repo)
    assert result['effective_authorization'] is expected
    assert result['ready_to_run_inspecsafe'] is expected
    assert result['dataset_read'] is False and result['model_load'] is False
    assert result['runtime_observation'] == 'NOT_EXECUTED'
    with contextlib.redirect_stdout(io.StringIO()):
        assert owner.main(['preflight', '--repo', str(repo)]) == (0 if expected else 2)
assert not artifact.exists()
'''
        draft = self._clone()
        git(draft, "switch", "--detach", self.f2)
        for repo, expected in ((draft, "false"), (self._merge_fixture(), "true")):
            with self.subTest(effective_authorization=expected):
                subprocess.run([sys.executable, "-c", code, str(repo), expected], cwd=ROOT, check=True)

    def test_preserved_roster_grounding_p1_and_pali_boundaries(self):
        contract = harness.contract()
        self.assertFalse(contract["p1_implemented"])
        self.assertEqual(contract["primary_grounding"], "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE")
        policy = json.loads((ROOT / "configs/pre_freeze/production_classification_policy.d9r23.v1.json").read_bytes())
        self.assertNotIn("paligemma", policy["classification"])
        participation = json.loads((ROOT / "configs/pre_freeze/d9r18_final_participation_decision.v1.json").read_bytes())
        pali = next(model for model in participation["models"]
                    if model["model_id"] == "google/paligemma-3b-mix-448")
        self.assertEqual(pali["classification_participation"], "NOT_PARTICIPATING")
        with self.assertRaisesRegex(ValueError, "CLASSIFICATION_NOT_PARTICIPATING"):
            harness.resolve_production_backend("paligemma")


if __name__ == "__main__":
    unittest.main()
