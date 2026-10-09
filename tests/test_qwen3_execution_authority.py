"""Offline superseding-authority checks with local synthetic Git/artifacts."""

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
from safeshift.runners import p2_bridge as bridge, p2_harness as h
from safeshift.runners import p2_owner as owner, p2_preflight as pre
from safeshift.runners import qwen3_authority as a

ROOT = Path(__file__).resolve().parents[1]
F1_FILES = (a.PLAN_PATH, "safeshift/runners/qwen3_authority.py",
            "safeshift/runners/p2_harness.py", "safeshift/runners/p2_bridge.py",
            "safeshift/runners/p2_preflight.py")


def git(repo, *args, raw=False, content=None):
    result = subprocess.check_output(["git", *args], cwd=repo, input=content,
                                     stderr=subprocess.DEVNULL)
    return result if raw else result.decode().strip()


class Qwen3ExecutionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.temp.name) / "source"
        # Local Git objects only; no network or ignored data is copied.
        git(ROOT, "clone", "--shared", "-c", "core.autocrlf=false", str(ROOT), str(cls.repo))
        git(cls.repo, "config", "user.name", "Synthetic authority test")
        git(cls.repo, "config", "user.email", "synthetic@example.invalid")
        # Remove later tracked authorities before rebuilding the historical
        # index; otherwise a v3 checkout can leave its authority untracked.
        cls.checkout(a.BASE)
        cls.f1_tree = cls.edit_tree(a.BASE, {p: (ROOT / p).read_bytes() for p in F1_FILES})
        cls.f1 = git(cls.repo, "commit-tree", cls.f1_tree, "-p", a.BASE, "-m", "synthetic F1")
        cls.authority = a.expected_authority(cls.f1, cls.f1_tree)
        cls.f2_tree = cls.edit_tree(cls.f1, {a.AUTHORITY_PATH: cls.encode(cls.authority)})
        cls.f2 = git(cls.repo, "commit-tree", cls.f2_tree, "-p", cls.f1, "-m", "synthetic F2")
        cls.merge = git(cls.repo, "commit-tree", cls.f2_tree, "-p", a.BASE, "-p", cls.f2,
                        "-m", "synthetic Standard Merge Commit")
        cls.checkout(cls.merge)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def encode(value):
        return (json.dumps(value, indent=2) + "\n").encode()

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

    def test_synthetic_standard_merge_and_scoped_static_preflight_pass(self):
        head, authority = h.authorize_production(self.repo)
        self.assertEqual(head, self.merge)
        self.assertEqual(authority, self.authority)
        result = pre.static_preflight(self.repo)
        self.assertTrue(result["effective_authorization"])
        self.assertEqual(result["models"], ["qwen3"])
        self.assertEqual(result["authorized_runs"], a.execution_plan()["runs"])
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["model_load"])

    def test_draft_squash_and_rebase_are_blocked(self):
        squash = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "squash")
        for commit in (self.f1, self.f2, squash):
            with self.subTest(commit=commit):
                self.checkout(commit)
                with self.assertRaisesRegex(PermissionError, "FINAL_MERGE_REQUIRED"):
                    h.authorize_production(self.repo)
        rebased = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "rebased F2")
        self.final(f2=rebased)
        with self.assertRaisesRegex(PermissionError, "DIRECT_F2_CHILD"):
            h.authorize_production(self.repo)

    def test_wrong_parents_intermediate_and_multi_parent_fail(self):
        self.final(parent1=git(self.repo, "rev-parse", a.BASE + "^1"))
        with self.assertRaisesRegex(PermissionError, "PARENT_1_REQUIRED"):
            h.authorize_production(self.repo)
        for parents in ((self.f2,), (a.BASE,), (self.f1, a.BASE)):
            args = [arg for parent in parents for arg in ("-p", parent)]
            f2 = git(self.repo, "commit-tree", self.f2_tree, *args, "-m", "wrong F2")
            self.final(f2=f2)
            with self.subTest(parents=parents), self.assertRaisesRegex(PermissionError, "DIRECT_F2_CHILD"):
                h.authorize_production(self.repo)
        wrong_f1 = git(self.repo, "commit-tree", self.f1_tree, "-p", a.BASE, "-p", self.f1,
                       "-m", "multi-parent F1")
        doc = a.expected_authority(wrong_f1, self.f1_tree)
        tree = self.edit_tree(wrong_f1, {a.AUTHORITY_PATH: self.encode(doc)})
        f2 = git(self.repo, "commit-tree", tree, "-p", wrong_f1, "-m", "wrong freeze")
        self.final(f2=f2)
        with self.assertRaisesRegex(PermissionError, "FREEZE_COMMIT_PARENT_REQUIRED"):
            h.authorize_production(self.repo)

    def test_executable_docs_and_authority_mutation_outside_expected_file_fail(self):
        for path in ("safeshift/runners/p2_harness.py", "notes/w2_d9r26_qwen3_p2_runbook.md",
                     a.HISTORICAL_PATH, a.PLAN_PATH):
            raw = git(self.repo, "show", self.f2 + ":" + path, raw=True) + b"\n"
            tree = self.edit_tree(self.f2, {path: raw})
            f2 = git(self.repo, "commit-tree", tree, "-p", self.f1, "-m", "post-F1 drift")
            self.final(f2=f2)
            with self.subTest(path=path), self.assertRaisesRegex(PermissionError, "EXECUTABLE_CHANGED_AFTER_FREEZE"):
                h.authorize_production(self.repo)

    def test_merge_tree_authority_bytes_and_dirty_checkout_fail(self):
        tree = self.edit_tree(self.f2, {a.AUTHORITY_PATH: self.encode(self.authority) + b"\n"})
        self.final(tree=tree)
        with self.assertRaisesRegex(PermissionError, "AUTHORITY_PARENT_REQUIRED"):
            h.authorize_production(self.repo)
        tree = self.edit_tree(self.f2, {"notes/w2_d9r26_qwen3_p2_runbook.md": b"synthetic drift\n"})
        self.final(tree=tree)
        with self.assertRaisesRegex(PermissionError, "FINAL_MERGE_TREE_MISMATCH"):
            h.authorize_production(self.repo)
        self.checkout(self.merge)
        path = self.repo / "safeshift/runners/p2_harness.py"
        path.write_bytes(path.read_bytes() + b"\n# dirty\n")
        with self.assertRaisesRegex(PermissionError, "DIRTY_EXECUTION_COMMIT"):
            h.authorize_production(self.repo)

    def test_each_authority_pin_and_exact_plan_required(self):
        mutations = {key: None for key in self.authority}
        mutations.update(schema_version="wrong", model_key="qwen2_5", sample_count=True,
                         source_manifest_sha256="0" * 64, runtime_id="wrong")
        for key, value in mutations.items():
            doc = {**self.authority, key: value}
            tree = self.edit_tree(self.f1, {a.AUTHORITY_PATH: self.encode(doc)})
            f2 = git(self.repo, "commit-tree", tree, "-p", self.f1, "-m", "mutated authority")
            self.final(f2=f2)
            with self.subTest(field=key), self.assertRaises(PermissionError):
                h.authorize_production(self.repo)
        for change in ("missing", "extra", "old_id", "wrong_index", "wrong_rerun", "other_model"):
            doc = deepcopy(self.authority)
            if change == "missing":
                doc["authorized_runs"].pop()
            elif change == "extra":
                doc["authorized_runs"].append(deepcopy(doc["authorized_runs"][0]))
            else:
                key, value = {"old_id": ("run_id", a.OLD_RUN_ID), "wrong_index": ("shard_index", 1),
                              "wrong_rerun": ("rerun_of", None), "other_model": ("model_key", "qwen2_5")}[change]
                doc["authorized_runs"][0][key] = value
            tree = self.edit_tree(self.f1, {a.AUTHORITY_PATH: self.encode(doc)})
            f2 = git(self.repo, "commit-tree", tree, "-p", self.f1, "-m", "wrong plan")
            self.final(f2=f2)
            with self.subTest(change=change), self.assertRaisesRegex(PermissionError, "EXACT_QWEN3_AUTHORITY_REQUIRED"):
                h.authorize_production(self.repo)

    def test_runtime_amendment_plan_and_dataset_contract_drift_in_f1_fail(self):
        for path in (a.PLAN_PATH, *a.PRESERVED_SHA256):
            raw = git(self.repo, "show", self.f1 + ":" + path, raw=True) + b"\n"
            tree = self.edit_tree(self.f1, {path: raw})
            f1 = git(self.repo, "commit-tree", tree, "-p", a.BASE, "-m", "wrong freeze bytes")
            doc = a.expected_authority(f1, tree)
            f2_tree = self.edit_tree(f1, {a.AUTHORITY_PATH: self.encode(doc)})
            f2 = git(self.repo, "commit-tree", f2_tree, "-p", f1, "-m", "F2")
            self.final(f2=f2)
            with self.subTest(path=path), self.assertRaisesRegex(PermissionError, "PINNED_ARTIFACT_MISMATCH"):
                h.authorize_production(self.repo)

    def test_missing_deleted_or_untracked_authority_fail(self):
        self.checkout(self.merge)
        (self.repo / a.AUTHORITY_PATH).unlink()
        with self.assertRaises(PermissionError):
            h.authorize_production(self.repo)
        self.checkout(self.merge)
        raw = (self.repo / a.AUTHORITY_PATH).read_bytes()
        self.checkout(a.BASE)
        (self.repo / a.AUTHORITY_PATH).write_bytes(raw)
        try:
            with self.assertRaises(PermissionError):
                h.authorize_production(self.repo)
        finally:
            (self.repo / a.AUTHORITY_PATH).unlink()

    def test_exact_four_identities_and_authority_derived_rerun(self):
        for run in a.execution_plan()["runs"]:
            with self.subTest(run=run["run_id"]):
                ref = a.bind_run(self.authority, "qwen3", run["run_id"], 4, run["shard_index"], None)
                self.assertEqual(ref, run["rerun_of"])
                for count, index in ((1, 0), (5, run["shard_index"]), (4, (run["shard_index"] + 1) % 4),
                                     (4, True), (True, 0)):
                    with self.assertRaises(PermissionError):
                        a.bind_run(self.authority, "qwen3", run["run_id"], count, index, None)
        for run_id in (a.OLD_RUN_ID, "qwen3-p2-shard0-rerun2", "hidden-rerun", "qwen3-p2-shard1-rerun1"):
            with self.assertRaises(PermissionError):
                a.bind_run(self.authority, "qwen3", run_id, 4, 0, None)
        ref = a.execution_plan()["runs"][0]["rerun_of"]
        for wrong in ({**ref, "run_id": "wrong"}, {**ref, "run_manifest_sha256": "0" * 64}, {}):
            with self.assertRaises(PermissionError):
                a.bind_run(self.authority, "qwen3", "qwen3-p2-shard0-rerun1", 4, 0, wrong)
        for i in (1, 2, 3):
            with self.assertRaises(PermissionError):
                a.bind_run(self.authority, "qwen3", f"qwen3-p2-shard{i}-first", 4, i, ref)

    def test_prior_artifact_missing_or_wrong_bytes_fail_before_dataset(self):
        for content in (None, b"synthetic wrong old manifest\n"):
            with tempfile.TemporaryDirectory() as tmp:
                storage = Path(tmp)
                if content is not None:
                    path = h._run_path(storage, "qwen3", a.OLD_RUN_ID) / "run_manifest.json"
                    path.parent.mkdir(parents=True)
                    path.write_bytes(content)
                with self.assertRaises((ValueError, PermissionError)):
                    a.verify_lineage(storage, self.authority, "qwen3", "qwen3-p2-shard0-rerun1",
                                     a.execution_plan()["runs"][0]["rerun_of"])
        args = dict(model="qwen3", run_id="qwen3-p2-shard0-rerun1", shard_count=4, shard_index=0,
                    dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ",
                    repo=self.repo)
        with patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET_ACCESS")) as dataset:
            with self.assertRaisesRegex(ValueError, "PREVIOUS_MANIFEST_REQUIRED"):
                h.production_run(**args)
            dataset.assert_not_called()

    def test_rerun_hash_verification_and_research_lead_invariant_with_synthetic_bytes(self):
        # The real failed manifest bytes were not supplied. Exercise SHA success
        # with synthetic bytes; exact production identity is tested separately.
        with tempfile.TemporaryDirectory() as tmp:
            path = h._run_path(tmp, "qwen3", a.OLD_RUN_ID) / "run_manifest.json"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"synthetic prior bytes\n")
            ref = {"run_id": a.OLD_RUN_ID, "run_manifest_sha256": sha(path.read_bytes())}
            auth = [{"run_id": "qwen3-p2-shard0-rerun1", "model_key": "qwen3",
                     "rerun_of": ref, "authority": "RESEARCH_LEAD"}]
            h._rerun(tmp, "qwen3", "qwen3-p2-shard0-rerun1", ref, auth)
            for run_id, model, permissions in ((a.OLD_RUN_ID, "qwen3", auth),
                                               ("qwen3-p2-shard0-rerun1", "qwen3", [])):
                with self.assertRaises((ValueError, PermissionError)):
                    h._rerun(tmp, model, run_id, ref, permissions)

    def test_wrong_production_identity_fails_before_dataset_and_backend(self):
        args = dict(model="qwen3", run_id="qwen3-p2-shard1-first", shard_count=4, shard_index=1,
                    dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ",
                    repo=self.repo)
        ref = a.execution_plan()["runs"][0]["rerun_of"]
        cases = [{"run_id": a.OLD_RUN_ID}, {"run_id": "hidden-rerun"}, {"shard_index": 2},
                 {"shard_count": 1}, {"rerun_of": ref},
                 {"run_id": "qwen3-p2-shard0-rerun1", "shard_index": 0,
                  "rerun_of": {**ref, "run_manifest_sha256": "0" * 64}}]
        for changes in cases:
            with self.subTest(changes=changes), \
                    patch.object(h, "verify_dataset", side_effect=AssertionError("NO_DATASET")) as dataset, \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("NO_BACKEND")) as backend:
                with self.assertRaises(PermissionError):
                    h.production_run(**{**args, **changes})
                dataset.assert_not_called()
                backend.assert_not_called()

    def test_native_context_obeys_same_exact_qwen3_identity(self):
        entry = load_policy(self.repo, qwen3_runtime=True)["classification"]["qwen3"]
        for run_id in ("qwen3-p2-shard1-first", "qwen3-p2-shard2-first", "qwen3-p2-shard3-first"):
            context = bridge.context_for("qwen3", entry, bridge.RunIdentity(run_id, self.merge, "INSPECSAFE"))
            bridge.require_production_context("qwen3", context, self.repo)
        for run_id in (a.OLD_RUN_ID, "qwen3-p2-shard0-first-again", "qwen3-p2-shard0-rerun2"):
            context = bridge.context_for("qwen3", entry, bridge.RunIdentity(run_id, self.merge, "INSPECSAFE"))
            with self.assertRaisesRegex(PermissionError, "EXACT_QWEN3_RUN_ID"):
                bridge.require_production_context("qwen3", context, self.repo)

    def test_production_and_native_context_reject_other_models_before_reads(self):
        for model in ("qwen2_5", "internvl3", "moondream"):
            with self.subTest(model=model), patch.object(h, "verify_dataset", side_effect=AssertionError("NO_DATASET")), \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("NO_MODEL")):
                with self.assertRaisesRegex(PermissionError, "QWEN3_ONLY"):
                    h.production_run(model=model, run_id=model + "-rerun", dataset_root="NEVER_READ",
                                     manifest_path="NEVER_READ", provenance_path="NEVER_READ", repo=self.repo)
                entry = load_policy(self.repo)["classification"][model]
                context = bridge.context_for(model, entry, bridge.RunIdentity(model + "-rerun", self.merge, "INSPECSAFE"))
                with self.assertRaisesRegex(PermissionError, "QWEN3_ONLY"):
                    bridge.require_production_context(model, context, self.repo)

    def test_cli_first_attempts_reach_dataset_boundary_and_shard0_binds_exact_reference(self):
        for run in a.execution_plan()["runs"]:
            with self.subTest(run=run["run_id"]), patch.object(a, "verify_lineage") as lineage, \
                    patch.object(h, "verify_dataset", side_effect=ValueError("SYNTHETIC_DATASET_BOUNDARY")) as dataset, \
                    redirect_stdout(io.StringIO()) as output:
                result = owner.main(["run", "--repo", str(self.repo), "--model", "qwen3",
                                     "--run-id", run["run_id"], "--shard-count", "4",
                                     "--shard-index", str(run["shard_index"]), "--dataset-root", "NEVER_READ",
                                     "--manifest-path", "NEVER_READ", "--provenance-path", "NEVER_READ"])
                self.assertEqual(result, 2)
                self.assertIn("SYNTHETIC_DATASET_BOUNDARY", output.getvalue())
                dataset.assert_called_once()
                self.assertEqual(lineage.call_args.args[-1], run["rerun_of"])

    def test_full_shard_selection_includes_previous_successes(self):
        rows = [{"sample_id": f"synthetic-{i:05d}", "image_locator": f"synthetic/{i}.png",
                 "image_sha256": "a" * 64} for i in range(5013)]
        selected, meta = shard(rows, 4, 0, a.MANIFEST_SHA)
        self.assertEqual(len(selected), 1254)
        self.assertEqual([row["sample_id"] for row in selected], [row["sample_id"] for row in rows[::4]])
        self.assertEqual(meta["source_manifest_sha256"], a.MANIFEST_SHA)

    def test_v1_runtime_prompt_metrics_and_scientific_consumers_unchanged(self):
        for path in (*a.PRESERVED_SHA256, "safeshift/runners/qwen3_placement.py", "safeshift/runners/qwen3_vl.py",
                     "safeshift/runners/qwen2_5_vl.py", "safeshift/runners/internvl3.py", "safeshift/runners/moondream2.py",
                     "safeshift/data/p2_execution.py", "safeshift/protocol/p2_evaluation.py",
                     "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/classification_policy.py"):
            self.assertEqual((ROOT / path).read_bytes(), git(ROOT, "show", a.BASE + ":" + path, raw=True), path)
        old = load_policy()["classification"]
        new = load_policy(qwen3_runtime=True)["classification"]
        for model in ("qwen2_5", "internvl3", "moondream"):
            self.assertEqual(old[model], new[model])
        self.assertEqual(a.execution_plan()["sample_count"], 5013)
        self.assertEqual(a.execution_plan()["dataset_fingerprint"], a.FINGERPRINT)
        self.assertEqual(a.execution_plan()["source_manifest_sha256"], a.MANIFEST_SHA)
        def functions(raw):
            return {n.name: ast.dump(n) for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef)}
        old = functions(git(ROOT, "show", a.BASE + ":safeshift/runners/p2_harness.py", raw=True))
        new = functions((ROOT / "safeshift/runners/p2_harness.py").read_bytes())
        for name in ("atomic_new", "persist_native", "verified_raw", "parse_stored", "_execute", "_rerun"):
            self.assertEqual(old[name], new[name])

    def test_fresh_process_preflight_guards_dataset_model_gpu_network(self):
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
with patch.object(h, 'verify_dataset', forbidden), patch.object(h, 'resolve_production_backend', forbidden), \
     patch.object(h.ProductionRunnerBridge, 'load', forbidden), patch.object(p, 'runtime_observation', forbidden):
    result = p.static_preflight(repo)
    assert result['effective_authorization'] is expected
    assert result['dataset_read'] is False and result['model_load'] is False
    assert result['runtime_observation'] == 'NOT_EXECUTED'
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
            self.skipTest("F2 declaration is created only after F1 is committed")
        doc = json.loads(path.read_bytes())
        f1 = doc["implementation_freeze_commit_sha"]
        # Historical v2 F2 is parent2 of its reviewed merge, not a later HEAD.
        f2 = git(ROOT, "rev-parse", "e46e98ed0c53f6c189f4069cc5f2f5d7d4295e5e^2")
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f1).split(), [f1, a.BASE])
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f2).split(), [f2, f1])
        self.assertEqual(git(ROOT, "diff", "--name-status", f1, f2), "A\t" + a.AUTHORITY_PATH)
        self.assertEqual(doc, a.expected_authority(f1, git(ROOT, "rev-parse", f1 + "^{tree}")))
        with self.assertRaises(PermissionError):
            h.authorize_production(ROOT)


if __name__ == "__main__":
    unittest.main()
