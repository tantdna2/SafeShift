"""Offline v3 release/identity checks using temporary Git and synthetic data only."""

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.data.p2_execution import sha, shard
from safeshift.protocol.classification_policy import load_policy
from safeshift.runners import internvl3_authority as a
from safeshift.runners import p2_bridge as bridge, p2_harness as h
from safeshift.runners import p2_owner as owner, p2_preflight as pre

ROOT = Path(__file__).resolve().parents[1]
F1_FILES = (a.PLAN_PATH, "safeshift/runners/internvl3_authority.py",
            "safeshift/runners/p2_harness.py", "safeshift/runners/p2_bridge.py",
            "notes/w2_internvl3_p2_authority_v3_runbook.md")


def git(repo, *args, raw=False, content=None):
    result = subprocess.check_output(["git", *args], cwd=repo, input=content,
                                     stderr=subprocess.DEVNULL)
    return result if raw else result.decode().strip()


class InternVL3ExecutionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.temp.name) / "source"
        # Only local tracked Git objects; no ignored dataset/snapshot copied.
        git(ROOT, "clone", "--shared", "-c", "core.autocrlf=false", str(ROOT), str(cls.repo))
        git(cls.repo, "config", "user.name", "Synthetic authority test")
        git(cls.repo, "config", "user.email", "synthetic@example.invalid")
        cls.f1_tree = cls.edit_tree(a.BASE, {p: (ROOT / p).read_bytes() for p in F1_FILES})
        cls.f1 = git(cls.repo, "commit-tree", cls.f1_tree, "-p", a.BASE, "-m", "synthetic F1")
        cls.authority = a.expected_authority(cls.f1, cls.f1_tree)
        cls.f2_tree = cls.edit_tree(cls.f1, {a.AUTHORITY_PATH: a.authority_bytes(cls.authority)})
        cls.f2 = cls.authority_commit(cls.f1, cls.f2_tree)
        cls.merge = git(cls.repo, "commit-tree", cls.f2_tree, "-p", a.BASE, "-p", cls.f2,
                        "-m", "synthetic Standard Merge Commit")
        cls.checkout(cls.merge)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def authority_commit(cls, f1, tree):
        return git(cls.repo, "hash-object", "-t", "commit", "-w", "--stdin",
                   content=a.f2_commit_bytes(f1, tree))

    @classmethod
    def edit_tree(cls, tree, changes):
        git(cls.repo, "read-tree", tree)
        for path, raw in changes.items():
            blob = git(cls.repo, "hash-object", "-w", "--stdin", content=raw)
            git(cls.repo, "update-index", "--add", "--cacheinfo", "100644", blob, path)
        return git(cls.repo, "write-tree")

    @classmethod
    def checkout(cls, commit):
        # Force applies exclusively to this test-owned temporary checkout.
        git(cls.repo, "switch", "--detach", "--force", commit)

    def setUp(self):
        self.checkout(self.merge)

    def final(self, *, f2=None, tree=None, parent1=None):
        f2 = f2 or self.f2
        tree = tree or git(self.repo, "rev-parse", f2 + "^{tree}")
        result = git(self.repo, "commit-tree", tree, "-p", parent1 or a.BASE, "-p", f2,
                     "-m", "synthetic final")
        self.checkout(result)
        return result

    def assert_blocked(self):
        with self.assertRaises(PermissionError):
            h.authorize_production(self.repo)

    def test_synthetic_standard_merge_scoped_preflight_pass(self):
        self.assertEqual(h.authorize_production(self.repo), (self.merge, self.authority))
        result = pre.static_preflight(self.repo)
        self.assertTrue(result["effective_authorization"])
        self.assertEqual(result["models"], ["internvl3"])
        self.assertEqual(result["authorized_runs"], a.execution_plan()["runs"])
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["model_load"])

    def test_draft_f2_squash_rebase_one_parent_fail(self):
        one = git(self.repo, "commit-tree", self.f2_tree, "-m", "root")
        squash = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "squash")
        for commit in (self.f1, self.f2, one, squash):
            with self.subTest(commit=commit):
                self.checkout(commit)
                self.assert_blocked()
        self.checkout(self.f2)
        self.assertFalse(pre.static_preflight(self.repo)["effective_authorization"])
        self.final(f2=squash)
        self.assert_blocked()

    def test_wrong_parent1_parent2_intermediate_multi_parent_fail(self):
        self.final(parent1=git(self.repo, "rev-parse", a.BASE + "^1"))
        self.assert_blocked()
        for parents in ((self.f2,), (a.BASE,), (self.f1, a.BASE)):
            args = [arg for parent in parents for arg in ("-p", parent)]
            f2 = git(self.repo, "commit-tree", self.f2_tree, *args, "-m", "wrong F2")
            self.final(f2=f2)
            self.assert_blocked()
        merge = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-p", self.f2,
                    "-p", self.f1, "-m", "three-parent final")
        self.checkout(merge)
        self.assert_blocked()

    def test_same_tree_different_f2_commit_is_rejected(self):
        twin = git(self.repo, "commit-tree", self.f2_tree, "-p", self.f1, "-m", a.F2_MESSAGE)
        self.assertNotEqual(twin, self.f2)
        self.final(f2=twin)
        with self.assertRaisesRegex(PermissionError, "EXACT_FINAL_MERGE_PARENT_2_REQUIRED"):
            h.authorize_production(self.repo)

    def test_f1_must_be_direct_single_parent_child_of_base(self):
        for parents in ((git(self.repo, "rev-parse", a.BASE + "^1"),), (a.BASE, self.f1)):
            args = [arg for parent in parents for arg in ("-p", parent)]
            f1 = git(self.repo, "commit-tree", self.f1_tree, *args, "-m", "wrong F1")
            doc = a.expected_authority(f1, self.f1_tree)
            tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(doc)})
            self.final(f2=self.authority_commit(f1, tree))
            self.assert_blocked()

    def test_f2_only_adds_authority_and_final_tree_must_match(self):
        for path in ("safeshift/runners/p2_harness.py", F1_FILES[-1], a.PLAN_PATH, a.HISTORICAL_PATH):
            tree = self.edit_tree(self.f2, {path: git(self.repo, "show", self.f2 + ":" + path, raw=True) + b"\n"})
            self.final(f2=self.authority_commit(self.f1, tree))
            self.assert_blocked()
        tree = self.edit_tree(self.f2, {F1_FILES[-1]: b"synthetic merge drift\n"})
        self.final(tree=tree)
        with self.assertRaisesRegex(PermissionError, "FINAL_MERGE_TREE_MISMATCH"):
            h.authorize_production(self.repo)
        tree = self.edit_tree(self.f2, {a.AUTHORITY_PATH: a.authority_bytes(self.authority) + b"\n"})
        self.final(tree=tree)
        self.assert_blocked()

    def test_dirty_tracked_checkout_fail(self):
        path = self.repo / "safeshift/runners/p2_harness.py"
        path.write_bytes(path.read_bytes() + b"\n# dirty\n")
        with self.assertRaisesRegex(PermissionError, "DIRTY_EXECUTION_COMMIT"):
            h.authorize_production(self.repo)

    def test_missing_deleted_untracked_or_mutated_v3_never_falls_back(self):
        path = self.repo / a.AUTHORITY_PATH
        path.unlink()
        self.assert_blocked()
        self.checkout(self.merge)
        path.write_bytes(a.authority_bytes({**self.authority, "model_key": "qwen3"}))
        self.assert_blocked()
        self.checkout(a.BASE)
        path.write_bytes(a.authority_bytes(self.authority))
        try:
            self.assert_blocked()
        finally:
            path.unlink()

    def test_each_authority_field_exact_model_revision_runtime_pin_required(self):
        changes = [(key, None) for key in self.authority]
        changes += [("model_id", "OpenGVLab/InternVL3-8B-hf"), ("immutable_revision", "main"),
                    ("runtime_plan_sha256", "0" * 64), ("sample_count", True),
                    ("supersedes_authority_sha256", "0" * 64)]
        for key, value in changes:
            with self.subTest(field=key, value=value):
                doc = {**self.authority, key: value}
                tree = self.edit_tree(self.f1, {a.AUTHORITY_PATH: a.authority_bytes(doc)})
                self.final(f2=self.authority_commit(self.f1, tree))
                self.assert_blocked()

    def test_exact_four_runs_no_extra_missing_reordered_shards_or_reruns(self):
        changes = [("run_id", "internvl3-p2-shard0-rerun1"), ("shard_count", 1),
                   ("shard_index", 1), ("sample_count", 1253), ("model_key", "qwen3"),
                   ("rerun_of", {"run_id": "old", "run_manifest_sha256": "0" * 64})]
        docs = []
        for key, value in changes:
            doc = deepcopy(self.authority)
            doc["authorized_runs"][0][key] = value
            docs.append(doc)
        for mode in ("missing", "extra", "reverse", "reruns"):
            doc = deepcopy(self.authority)
            if mode == "missing":
                doc["authorized_runs"].pop()
            elif mode == "extra":
                doc["authorized_runs"].append(deepcopy(doc["authorized_runs"][0]))
            elif mode == "reverse":
                doc["authorized_runs"].reverse()
            else:
                doc["reruns"] = [deepcopy(doc["authorized_runs"][0])]
            docs.append(doc)
        for doc in docs:
            tree = self.edit_tree(self.f1, {a.AUTHORITY_PATH: a.authority_bytes(doc)})
            self.final(f2=self.authority_commit(self.f1, tree))
            self.assert_blocked()

    def test_each_protected_artifact_hash_and_plan_required_in_f1(self):
        for path in (a.PLAN_PATH, *a.PRESERVED_SHA256):
            with self.subTest(path=path):
                raw = git(self.repo, "show", self.f1 + ":" + path, raw=True) + b"\n"
                tree = self.edit_tree(self.f1, {path: raw})
                f1 = git(self.repo, "commit-tree", tree, "-p", a.BASE, "-m", "wrong freeze bytes")
                doc = a.expected_authority(f1, tree)
                f2_tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(doc)})
                self.final(f2=self.authority_commit(f1, f2_tree))
                with self.assertRaisesRegex(PermissionError, "PINNED_ARTIFACT_MISMATCH"):
                    h.authorize_production(self.repo)

    def test_authority_must_be_absent_from_f1(self):
        f1 = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "early authority")
        doc = a.expected_authority(f1, self.f2_tree)
        tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(doc)})
        self.final(f2=self.authority_commit(f1, tree))
        self.assert_blocked()

    def test_correct_run_and_shard_pass_wrong_ids_indices_counts_any_rerun_fail(self):
        for run in a.execution_plan()["runs"]:
            self.assertIsNone(a.bind_run(self.authority, "internvl3", run["run_id"], 4, run["shard_index"], None))
            for count, index in ((1, 0), (5, 0), (4, (run["shard_index"] + 1) % 4), (True, 0), (4, True)):
                with self.assertRaises(PermissionError):
                    a.bind_run(self.authority, "internvl3", run["run_id"], count, index, None)
            for ref in ({}, False, "old", {"run_id": "old", "run_manifest_sha256": "0" * 64}):
                with self.assertRaises(PermissionError):
                    a.bind_run(self.authority, "internvl3", run["run_id"], 4, run["shard_index"], ref)
        for run_id in ("other", "internvl3-p2-shard4-first", "internvl3-p2-shard0-rerun1"):
            with self.assertRaises(PermissionError):
                a.bind_run(self.authority, "internvl3", run_id, 4, 0, None)

    def test_entrypoint_rejects_bad_run_shard_rerun_other_models_before_dataset_backend(self):
        args = dict(model="internvl3", run_id="internvl3-p2-shard1-first", shard_count=4, shard_index=1,
                    dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ", repo=self.repo)
        cases = [{"run_id": "wrong"}, {"shard_count": 1}, {"shard_index": 0}, {"rerun_of": {}},
                 {"model": "qwen3", "run_id": "qwen3-p2-shard1-first"},
                 {"model": "qwen3", "run_id": "qwen3-p2-shard0-rerun1", "rerun_of": {}},
                 {"model": "qwen2_5", "run_id": "qwen2_5-rerun", "rerun_of": {}},
                 {"model": "moondream", "run_id": "moondream-first"}]
        for changes in cases:
            with self.subTest(changes=changes), \
                    patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET")) as dataset, \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("BACKEND")) as backend:
                with self.assertRaises(PermissionError):
                    h.production_run(**{**args, **changes})
                dataset.assert_not_called()
                backend.assert_not_called()

    def test_reuse_run_id_rejected_before_dataset_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_id = "internvl3-p2-shard0-first"
            h._run_path(tmp, "internvl3", run_id).mkdir(parents=True)
            with patch.object(h, "authorize_production", return_value=(self.merge, self.authority)), \
                    patch.object(h, "_model", return_value={}), \
                    patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET")) as dataset, \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("BACKEND")) as backend:
                with self.assertRaisesRegex(FileExistsError, "EXISTING_RUN_RESUME_FORBIDDEN"):
                    h.production_run(model="internvl3", run_id=run_id, shard_count=4, shard_index=0,
                                     dataset_root="NEVER_READ", manifest_path="NEVER_READ",
                                     provenance_path="NEVER_READ", repo=tmp)
                dataset.assert_not_called()
                backend.assert_not_called()

    def test_native_context_exact_ids_and_conditions_enforced(self):
        from safeshift.runners.internvl3 import InternVL3Runner
        entry = load_policy(self.repo)["classification"]["internvl3"]
        for run in a.execution_plan()["runs"]:
            context = bridge.context_for("internvl3", entry, bridge.RunIdentity(run["run_id"], self.merge, "INSPECSAFE"))
            bridge.require_production_context("internvl3", context, self.repo)
        for run_id in ("wrong", "internvl3-p2-shard0-rerun1", "qwen3-p2-shard1-first"):
            context = bridge.context_for("internvl3", entry, bridge.RunIdentity(run_id, self.merge, "INSPECSAFE"))
            with self.assertRaisesRegex(PermissionError, "EXACT_INTERNVL3_RUN_ID_REQUIRED"):
                bridge.require_production_context("internvl3", context, self.repo)
            def forbidden_backend():
                raise AssertionError("NATIVE_BACKEND_MUST_NOT_BE_CREATED")
            runner = InternVL3Runner(repo=self.repo, backend_factory=forbidden_backend)
            with self.assertRaisesRegex(PermissionError, "EXACT_INTERNVL3_RUN_ID_REQUIRED"):
                runner.initialize(context)
            self.assertIsNone(runner.backend)
            self.assertEqual(runner.model_load_count, 0)
        for model in ("qwen3", "qwen2_5", "moondream"):
            entry = load_policy(self.repo, qwen3_runtime=model == "qwen3")["classification"][model]
            context = bridge.context_for(model, entry, bridge.RunIdentity(model + "-first", self.merge, "INSPECSAFE"))
            with self.assertRaisesRegex(PermissionError, "INTERNVL3_ONLY"):
                bridge.require_production_context(model, context, self.repo)

    def test_owner_exact_four_first_attempts_reach_dataset_boundary(self):
        for run in a.execution_plan()["runs"]:
            with patch.object(h, "verify_dataset", side_effect=ValueError("SYNTHETIC_DATASET_BOUNDARY")) as dataset, \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("BACKEND")) as backend, \
                    redirect_stdout(io.StringIO()) as output:
                result = owner.main(["run", "--repo", str(self.repo), "--model", "internvl3",
                                     "--run-id", run["run_id"], "--shard-count", "4",
                                     "--shard-index", str(run["shard_index"]), "--dataset-root", "NEVER_READ",
                                     "--manifest-path", "NEVER_READ", "--provenance-path", "NEVER_READ"])
                self.assertEqual(result, 2)
                self.assertIn("SYNTHETIC_DATASET_BOUNDARY", output.getvalue())
                dataset.assert_called_once()
                backend.assert_not_called()

    def test_dataset_success_precedes_backend_resolution(self):
        rows = [{"sample_id": f"synthetic-{i:05d}", "image_locator": f"synthetic/{i}.png",
                 "image_sha256": "a" * 64} for i in range(5013)]
        seen = []
        def verified(*args):
            seen.append("verified")
            return rows, a.MANIFEST_SHA
        def backend(*args, **kwargs):
            self.assertEqual(seen, ["verified"])
            raise ValueError("SYNTHETIC_BACKEND_BOUNDARY")
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(h, "authorize_production", return_value=(self.merge, self.authority)), \
                patch.object(h, "_model", return_value={}), \
                patch.object(h, "contract", return_value={"dataset_fingerprint": a.FINGERPRINT}), \
                patch.object(h, "verify_dataset", side_effect=verified), \
                patch.object(h, "resolve_production_backend", side_effect=backend):
            with self.assertRaisesRegex(ValueError, "SYNTHETIC_BACKEND_BOUNDARY"):
                h.production_run(model="internvl3", run_id="internvl3-p2-shard0-first", shard_count=4, shard_index=0,
                                 dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ", repo=tmp)
        for i, count in enumerate((1254, 1253, 1253, 1253)):
            selected, _ = shard(rows, 4, i, a.MANIFEST_SHA)
            self.assertEqual(len(selected), count)
            self.assertEqual(list(selected), rows[i::4])

    def test_historical_authorities_runtime_scientific_and_runner_bytes_unchanged(self):
        paths = (*a.PRESERVED_SHA256, "safeshift/runners/qwen3_authority.py",
                 "safeshift/runners/qwen3_placement.py", "safeshift/runners/qwen3_vl.py",
                 "safeshift/runners/p2_owner.py", "safeshift/runners/p2_preflight.py",
                 "safeshift/data/p2_execution.py", "safeshift/protocol/p2_evaluation.py",
                 "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/classification_policy.py",
                 "safeshift/runners/production_classification.py", "safeshift/qualification/classification.py")
        for path in paths:
            raw = git(ROOT, "show", a.BASE + ":" + path, raw=True)
            self.assertEqual((ROOT / path).read_bytes(), raw, path)
            if path in a.PRESERVED_SHA256:
                self.assertEqual(sha(raw), a.PRESERVED_SHA256[path])
        self.assertEqual(sha((ROOT / a.PLAN_PATH).read_bytes()), a.PLAN_SHA256)
        self.assertEqual(json.loads((ROOT / a.PLAN_PATH).read_bytes()), a.execution_plan())
        plan = a.execution_plan()
        self.assertEqual(plan["dataset_fingerprint"], "7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5")
        self.assertEqual(plan["source_manifest_sha256"], "3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577")
        self.assertEqual(plan["sample_count"], 5013)
        def functions(raw):
            return {n.name: ast.dump(n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
        old = functions(git(ROOT, "show", a.BASE + ":safeshift/runners/p2_harness.py", raw=True))
        new = functions((ROOT / "safeshift/runners/p2_harness.py").read_bytes())
        for name in ("atomic_new", "persist_native", "verified_raw", "parse_stored", "_execute", "_rerun"):
            self.assertEqual(old[name], new[name], name)

    def test_fresh_process_static_preflight_no_dataset_model_gpu_network(self):
        code = r'''
import builtins, contextlib, io, socket, sys
from pathlib import Path
from unittest.mock import patch
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'accelerate', 'bitsandbytes'}:
        raise AssertionError('MODEL_GPU_IMPORT:' + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
def forbidden(*args, **kwargs):
    raise AssertionError('DATASET_MODEL_GPU_NETWORK_ACCESS')
socket.socket.connect = socket.socket.connect_ex = socket.create_connection = socket.getaddrinfo = forbidden
from safeshift.runners import p2_harness as h, p2_preflight as p, p2_owner as owner
repo, expected = Path(sys.argv[1]), sys.argv[2] == 'true'
original_read = Path.read_bytes
original_open = builtins.open
def guarded_read(path):
    if 'data' in path.parts:
        forbidden()
    return original_read(path)
def guarded_open(path, *args, **kwargs):
    if isinstance(path, (str, Path)) and 'data' in Path(path).parts:
        forbidden()
    return original_open(path, *args, **kwargs)
with patch.object(h, 'verify_dataset', forbidden), patch.object(h, 'resolve_production_backend', forbidden), \
     patch.object(h.ProductionRunnerBridge, 'load', forbidden), patch.object(p, 'runtime_observation', forbidden), \
     patch.object(Path, 'read_bytes', guarded_read), patch.object(builtins, 'open', guarded_open):
    result = p.static_preflight(repo)
    assert result['effective_authorization'] is expected
    assert result['dataset_read'] is False and result['model_load'] is False
    assert result['runtime_observation'] == 'NOT_EXECUTED'
    if expected:
        assert result['models'] == ['internvl3']
        assert len(result['authorized_runs']) == 4
    with contextlib.redirect_stdout(io.StringIO()):
        assert owner.main(['preflight', '--repo', str(repo)]) == (0 if expected else 2)
assert not (repo / 'data/processed/benchmark/p2').exists()
'''
        for commit, expected in ((self.f2, "false"), (self.merge, "true")):
            self.checkout(commit)
            subprocess.run([sys.executable, "-c", code, str(self.repo), expected], cwd=ROOT, check=True)

    def test_actual_release_structure_when_f2_exists(self):
        path = ROOT / a.AUTHORITY_PATH
        if not path.exists():
            self.skipTest("F2 authority is added only after F1 is committed")
        doc = json.loads(path.read_bytes())
        f1 = doc["implementation_freeze_commit_sha"]
        f2 = git(ROOT, "rev-parse", "HEAD")
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f1).split(), [f1, a.BASE])
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f2).split(), [f2, f1])
        self.assertEqual(git(ROOT, "diff", "--name-status", f1, f2), "A\t" + a.AUTHORITY_PATH)
        self.assertEqual(doc, a.expected_authority(f1, git(ROOT, "rev-parse", f1 + "^{tree}")))
        self.assertEqual(git(ROOT, "cat-file", "commit", f2, raw=True),
                         a.f2_commit_bytes(f1, git(ROOT, "rev-parse", f2 + "^{tree}")))
        with self.assertRaises(PermissionError):
            h.authorize_production(ROOT)
        # Verify the actual immutable Draft F2 tree under a synthetic final
        # merge in the test-owned repository, without merging any real branch.
        self.final(f2=f2)
        _, effective = h.authorize_production(self.repo)
        self.assertEqual(effective, doc)
        result = pre.static_preflight(self.repo)
        self.assertTrue(result["effective_authorization"])
        self.assertEqual(result["models"], ["internvl3"])
        self.assertEqual(result["authorized_runs"], a.execution_plan()["runs"])


if __name__ == "__main__":
    unittest.main()
