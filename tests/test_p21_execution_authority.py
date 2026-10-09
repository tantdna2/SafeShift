"""P2.1 release and lineage checks; local synthetic Git/artifacts only."""

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

from safeshift.data.p2_execution import execution_records, json_bytes, sha
from safeshift.protocol.classification_policy import load_policy
from safeshift.runners import p21_authority as a
from safeshift.runners import p2_bridge as bridge, p2_harness as h
from safeshift.runners import p2_owner as owner, p2_preflight as pre

ROOT = Path(__file__).resolve().parents[1]
F1_FILES = (a.PLAN_PATH, a.AMENDMENT_PATH, a.SOURCE_MARKER,
            "safeshift/runners/p2_harness.py", "safeshift/runners/p2_bridge.py",
            "safeshift/runners/p2_preflight.py", "safeshift/protocol/p2_evaluation.py",
            "safeshift/runners/p21_classification.py", "safeshift/protocol/p21_schema.py",
            "safeshift/runners/production_classification.py")


def git(repo, *args, raw=False, content=None):
    value = subprocess.check_output(["git", *args], cwd=repo, input=content,
                                    stderr=subprocess.DEVNULL)
    return value if raw else value.decode().strip()


class P21ExecutionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls.temp.name) / "source"
        git(ROOT, "clone", "--shared", "--no-checkout", "-c", "core.autocrlf=false", str(ROOT), str(cls.repo))
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
        # Force only restores this class's temporary synthetic checkout.
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

    def test_synthetic_standard_merge_scoped_static_preflight_passes(self):
        self.assertEqual(h.authorize_production(self.repo), (self.merge, self.authority))
        result = pre.static_preflight(self.repo)
        self.assertTrue(result["effective_authorization"])
        self.assertEqual(result["models"], ["internvl3"])
        self.assertEqual(result["authorized_runs"], a.execution_plan()["runs"])
        self.assertFalse(result["dataset_read"])
        self.assertFalse(result["model_load"])

    def test_draft_f1_f2_squash_rebase_never_effective(self):
        squash = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "squash")
        root = git(self.repo, "commit-tree", self.f2_tree, "-m", "root")
        for commit in (self.f1, self.f2, squash, root):
            self.checkout(commit)
            self.assert_blocked()
        self.checkout(self.f2)
        self.assertFalse(pre.static_preflight(self.repo)["effective_authorization"])

    def test_wrong_parents_intermediate_and_multi_parent_fail(self):
        self.final(parent1=git(self.repo, "rev-parse", a.BASE + "^1"))
        self.assert_blocked()
        for parents in ((self.f2,), (a.BASE,), (self.f1, a.BASE)):
            args = [arg for parent in parents for arg in ("-p", parent)]
            other = git(self.repo, "commit-tree", self.f2_tree, *args, "-m", "wrong F2")
            self.final(f2=other)
            self.assert_blocked()
        triple = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-p", self.f2,
                     "-p", self.f1, "-m", "three parents")
        self.checkout(triple)
        self.assert_blocked()

    def test_exact_f2_commit_encoding_required_even_with_same_tree(self):
        other = git(self.repo, "commit-tree", self.f2_tree, "-p", self.f1, "-m", a.F2_MESSAGE)
        self.assertNotEqual(other, self.f2)
        self.final(f2=other)
        with self.assertRaisesRegex(PermissionError, "EXACT_FINAL_MERGE_PARENT_2_REQUIRED"):
            h.authorize_production(self.repo)

    def test_f1_must_be_direct_single_parent_child_of_base(self):
        for parents in ((git(self.repo, "rev-parse", a.BASE + "^1"),), (a.BASE, self.f1)):
            args = [arg for parent in parents for arg in ("-p", parent)]
            f1 = git(self.repo, "commit-tree", self.f1_tree, *args, "-m", "wrong F1")
            tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(a.expected_authority(f1, self.f1_tree))})
            self.final(f2=self.authority_commit(f1, tree))
            self.assert_blocked()

    def test_f2_only_adds_v4_and_final_tree_exact(self):
        for path in ("safeshift/runners/p2_harness.py", a.PLAN_PATH, a.HISTORICAL_PATH):
            tree = self.edit_tree(self.f2, {path: git(self.repo, "show", self.f2 + ":" + path, raw=True) + b"\n"})
            self.final(f2=self.authority_commit(self.f1, tree))
            self.assert_blocked()
        tree = self.edit_tree(self.f2, {"synthetic_merge_drift.txt": b"drift\n"})
        self.final(tree=tree)
        with self.assertRaisesRegex(PermissionError, "FINAL_MERGE_TREE_MISMATCH"):
            h.authorize_production(self.repo)

    def test_missing_deleted_untracked_mutated_v4_never_falls_back(self):
        path = self.repo / a.AUTHORITY_PATH
        path.unlink()
        self.assert_blocked()
        self.checkout(self.merge)
        path.write_bytes(a.authority_bytes({**self.authority, "model_key": "qwen3"}))
        self.assert_blocked()
        self.checkout(self.f1)
        self.assert_blocked()
        path.write_bytes(a.authority_bytes(self.authority))
        try:
            self.assert_blocked()
        finally:
            path.unlink()
        # Even removing tracked v4 from a later tree cannot dispatch to v3.
        git(self.repo, "read-tree", self.f2)
        git(self.repo, "update-index", "--force-remove", a.AUTHORITY_PATH)
        tree = git(self.repo, "write-tree")
        self.final(tree=tree)
        self.assert_blocked()

    def test_deleted_tracked_implementation_marker_still_requires_v4(self):
        (self.repo / a.SOURCE_MARKER).unlink()
        (self.repo / a.AUTHORITY_PATH).unlink()
        self.assert_blocked()

    def test_dirty_tracked_checkout_fail(self):
        path = self.repo / "safeshift/runners/p2_harness.py"
        path.write_bytes(path.read_bytes() + b"\n# dirty\n")
        with self.assertRaisesRegex(PermissionError, "DIRTY_EXECUTION_COMMIT"):
            h.authorize_production(self.repo)

    def test_every_authority_field_is_exact(self):
        changes = [(key, None) for key in self.authority]
        changes += [("immutable_revision", "main"), ("protocol_id", "P2"),
                    ("parser_version", "d9r23-native-strict-classification-v1"),
                    ("sample_count", True), ("supersedes_authority_sha256", "0" * 64)]
        for key, value in changes:
            with self.subTest(field=key):
                tree = self.edit_tree(self.f1, {a.AUTHORITY_PATH: a.authority_bytes({**self.authority, key: value})})
                self.final(f2=self.authority_commit(self.f1, tree))
                self.assert_blocked()

    def test_protected_hashes_amendment_and_plan_fail_closed(self):
        for path in (a.PLAN_PATH, a.AMENDMENT_PATH, *a.PRESERVED_SHA256):
            with self.subTest(path=path):
                tree = self.edit_tree(self.f1, {path: git(self.repo, "show", self.f1 + ":" + path, raw=True) + b"\n"})
                f1 = git(self.repo, "commit-tree", tree, "-p", a.BASE, "-m", "wrong freeze bytes")
                f2_tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(a.expected_authority(f1, tree))})
                self.final(f2=self.authority_commit(f1, f2_tree))
                with self.assertRaisesRegex(PermissionError, "PINNED_ARTIFACT_MISMATCH"):
                    h.authorize_production(self.repo)

    def test_v4_must_be_absent_from_f1(self):
        f1 = git(self.repo, "commit-tree", self.f2_tree, "-p", a.BASE, "-m", "early v4")
        tree = self.edit_tree(f1, {a.AUTHORITY_PATH: a.authority_bytes(a.expected_authority(f1, self.f2_tree))})
        self.final(f2=self.authority_commit(f1, tree))
        self.assert_blocked()

    def test_exact_four_run_plan_lineage_and_model_authority(self):
        for run in a.execution_plan()["runs"]:
            self.assertEqual(a.bind_run(self.authority, "internvl3", run["run_id"], 4,
                                        run["shard_index"], None), run["rerun_of"])
            for count, index in ((1, 0), (5, 0), (4, (run["shard_index"] + 1) % 4), (True, 0), (4, True)):
                with self.assertRaises(PermissionError):
                    a.bind_run(self.authority, "internvl3", run["run_id"], count, index, None)
            for ref in ({}, False, "old", {"run_id": "old", "run_manifest_sha256": "0" * 64}):
                with self.assertRaises(PermissionError):
                    a.bind_run(self.authority, "internvl3", run["run_id"], 4, run["shard_index"], ref)
        for model in ("qwen3", "qwen2_5", "moondream"):
            with self.assertRaises(PermissionError):
                a.authorized_run(self.authority, model, a.execution_plan()["runs"][0]["run_id"])
        for run_id in (a.OLD_RUN_ID, "internvl3-p21-shard4-first", "internvl3-p21-shard0-rerun2"):
            with self.assertRaises(PermissionError):
                a.authorized_run(self.authority, "internvl3", run_id)
        for key in ("run_id", "shard_index", "sample_count", "attempt_kind", "protocol_id", "lineage"):
            doc = deepcopy(self.authority)
            doc["authorized_runs"][0][key] = None
            with self.assertRaises(PermissionError):
                a.authorized_run(doc, "internvl3", a.execution_plan()["runs"][0]["run_id"])
        for mode in ("extra", "missing", "reverse"):
            doc = deepcopy(self.authority)
            if mode == "extra":
                doc["authorized_runs"].append(deepcopy(doc["authorized_runs"][0]))
            elif mode == "missing":
                doc["authorized_runs"].pop()
            else:
                doc["authorized_runs"].reverse()
            with self.assertRaises(PermissionError):
                a.authorized_run(doc, "internvl3", a.execution_plan()["runs"][0]["run_id"])

    def test_missing_previous_manifest_wrong_hash_and_reuse_fail_before_dataset(self):
        run = a.execution_plan()["runs"][0]
        args = dict(model="internvl3", run_id=run["run_id"], shard_count=4, shard_index=0,
                    dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ")
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(h, "authorize_production", return_value=(self.merge, self.authority)), \
                patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET")) as dataset, \
                patch.object(h, "resolve_production_backend", side_effect=AssertionError("BACKEND")) as backend:
            with self.assertRaisesRegex(ValueError, "PREVIOUS_MANIFEST_AND_STATUS_REQUIRED"):
                h.production_run(**args, repo=tmp)
            old = h._run_path(tmp, "internvl3", a.OLD_RUN_ID)
            old.mkdir(parents=True)
            (old / "run_manifest.json").write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "RERUN_REFERENCE_MISMATCH"):
                h.production_run(**args, repo=tmp)
            h._run_path(tmp, "internvl3", run["run_id"]).mkdir(parents=True)
            with self.assertRaisesRegex(FileExistsError, "EXISTING_RUN_RESUME_FORBIDDEN"):
                h.production_run(**args, repo=tmp)
            dataset.assert_not_called()
            backend.assert_not_called()

    def synthetic_previous(self, repo):
        manifest = {"version": "d9r26-run-v1", "run_id": a.OLD_RUN_ID, "model_key": "internvl3",
                    "git_commit": a.BASE, "rerun_of": None,
                    "protocol_identity": {"protocol_id": "P2", "source_kind": "INSPECSAFE",
                                          "dataset_fingerprint": a.FINGERPRINT,
                                          "source_manifest_sha256": a.MANIFEST_SHA},
                    "model_condition": load_policy(ROOT)["classification"]["internvl3"]}
        status = {"status": "COMPLETED", "failure": None,
                  "samples": {f"synthetic-{i:04d}": "INVALID" for i in range(1254)}}
        old = h._run_path(repo, "internvl3", a.OLD_RUN_ID)
        old.mkdir(parents=True)
        raw, state = json_bytes(manifest), json_bytes(status)
        (old / "run_manifest.json").write_bytes(raw)
        (old / "run_status.json").write_bytes(state)
        return raw, state, manifest, status

    def test_synthetic_lineage_hash_then_schema_and_status_are_verified(self):
        # Real owner bytes are unavailable. Patch pins only inside this synthetic
        # test, never create a substitute for the actual supplied manifest hash.
        with tempfile.TemporaryDirectory() as tmp:
            raw, state, manifest, status = self.synthetic_previous(tmp)
            old = h._run_path(tmp, "internvl3", a.OLD_RUN_ID)
            with patch.object(a, "OLD_MANIFEST_SHA256", sha(raw)), patch.object(a, "OLD_STATUS_SHA256", sha(state)), \
                    patch.object(a, "load_policy", return_value=load_policy(ROOT)):
                authority = a.expected_authority(self.f1, self.f1_tree)
                run = a.execution_plan()["runs"][0]
                a.verify_lineage(tmp, authority, "internvl3", run["run_id"], run["rerun_of"])
                (old / "run_status.json").write_bytes(state + b"\n")
                with self.assertRaisesRegex(ValueError, "STATUS_SHA_MISMATCH"):
                    a.verify_lineage(tmp, authority, "internvl3", run["run_id"], run["rerun_of"])
                (old / "run_status.json").write_bytes(state)
                for key, value in (("git_commit", "0" * 40), ("model_key", "qwen3"), ("rerun_of", {})):
                    bad = json_bytes({**manifest, key: value})
                    (old / "run_manifest.json").write_bytes(bad)
                    with patch.object(a, "OLD_MANIFEST_SHA256", sha(bad)):
                        doc = a.expected_authority(self.f1, self.f1_tree)
                        ref = a.execution_plan()["runs"][0]["rerun_of"]
                        with self.assertRaisesRegex(ValueError, "EXACT_PREVIOUS_P2_MANIFEST_REQUIRED"):
                            a.verify_lineage(tmp, doc, "internvl3", run["run_id"], ref)
                (old / "run_manifest.json").write_bytes(raw)
                bad_status = json_bytes({**status, "status": "FAILED"})
                (old / "run_status.json").write_bytes(bad_status)
                with patch.object(a, "OLD_STATUS_SHA256", sha(bad_status)):
                    doc = a.expected_authority(self.f1, self.f1_tree)
                    with self.assertRaisesRegex(ValueError, "EXACT_PREVIOUS_P2_STATUS_REQUIRED"):
                        a.verify_lineage(tmp, doc, "internvl3", run["run_id"], run["rerun_of"])

    def test_unauthorized_runs_shards_models_and_lineage_before_dataset_backend(self):
        args = dict(model="internvl3", run_id=a.execution_plan()["runs"][0]["run_id"], shard_count=4, shard_index=0,
                    dataset_root="NEVER_READ", manifest_path="NEVER_READ", provenance_path="NEVER_READ", repo=self.repo)
        for changes in ({"run_id": "wrong"}, {"shard_count": 1}, {"shard_index": 1}, {"rerun_of": {}},
                        {"model": "qwen3"}, {"model": "qwen2_5"}, {"model": "moondream"}):
            with self.subTest(changes=changes), \
                    patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET")) as dataset, \
                    patch.object(h, "resolve_production_backend", side_effect=AssertionError("BACKEND")) as backend:
                with self.assertRaises(PermissionError):
                    h.production_run(**{**args, **changes})
                dataset.assert_not_called()
                backend.assert_not_called()

    def test_first_attempts_require_positive_completed_shard0_progression(self):
        for run in a.execution_plan()["runs"][1:]:
            with self.subTest(run=run["run_id"]), \
                    patch.object(h, "verify_dataset", side_effect=AssertionError("DATASET")) as dataset:
                with self.assertRaisesRegex(PermissionError, "P21_SHARD0_SUCCESS_REQUIRED"):
                    h.production_run(model="internvl3", run_id=run["run_id"], shard_count=4,
                                     shard_index=run["shard_index"], dataset_root="NEVER_READ",
                                     manifest_path="NEVER_READ", provenance_path="NEVER_READ", repo=self.repo)
                dataset.assert_not_called()

    def test_progression_rejects_zero_yield_failed_not_attempted_and_corrupt_artifacts(self):
        shard0, shard1 = a.execution_plan()["runs"][:2]
        with tempfile.TemporaryDirectory() as tmp:
            root = h._run_path(tmp, "internvl3", shard0["run_id"])
            root.mkdir(parents=True)
            manifest = {"version": "p21-run-v1", "run_id": shard0["run_id"],
                        "model_key": "internvl3", "git_commit": self.merge,
                        "protocol_identity": {"protocol_id": a.PROTOCOL_ID, "parser_version": a.PARSER_VERSION,
                                              "source_kind": "INSPECSAFE", "dataset_fingerprint": a.FINGERPRINT,
                                              "source_manifest_sha256": a.MANIFEST_SHA},
                        "rerun_of": shard0["rerun_of"], "attempt_kind": shard0["attempt_kind"],
                        "lineage": shard0["lineage"]}
            (root / "run_manifest.json").write_bytes(json_bytes(manifest))
            status = {"status": "COMPLETED", "failure": None,
                      "samples": {f"synthetic-{i:04d}": "INVALID" for i in range(1254)},
                      "artifact_sha256": {"run_manifest.json": sha(json_bytes(manifest))}}
            path_for = h._run_path
            with patch.object(h, "_run_path", side_effect=lambda repo, model, run_id: path_for(tmp, model, run_id)):
                for kind in ("all_invalid", "FAILED", "NOT_ATTEMPTED", "missing_index", "tamper"):
                    bad = deepcopy(status)
                    if kind != "all_invalid":
                        bad["samples"]["synthetic-0000"] = "SUCCESS"
                    if kind in ("FAILED", "NOT_ATTEMPTED"):
                        bad["samples"]["synthetic-0001"] = kind
                    elif kind == "missing_index":
                        bad["artifact_sha256"] = {}
                    elif kind == "tamper":
                        bad["artifact_sha256"]["run_manifest.json"] = "0" * 64
                    (root / "run_status.json").write_bytes(json_bytes(bad))
                    with self.subTest(kind=kind), self.assertRaisesRegex(PermissionError, "P21_SHARD0_SUCCESS_REQUIRED"):
                        a.verify_progression(self.repo, self.authority, "internvl3", shard1["run_id"])

    def test_progression_positive_synthetic_durable_shard_and_raw_integrity(self):
        from tests.test_d9r23_classification_contract import native
        shard0, shard1 = a.execution_plan()["runs"][:2]
        image = h.synthetic_image()
        rows = execution_records({"sample_id": f"synthetic-{i:05d}", "image_locator": "generated.png",
                                  "image_sha256": sha(image)} for i in range(5013))
        responses = []
        for row in rows[::4]:
            payload = json.loads(native("internvl3", '```json\n{"safety_level":"Level03"}\n```'))
            payload.update(run_id=shard0["run_id"], call_id=h.call_identity(row["sample_id"]))
            responses.append(json_bytes(payload))
        with tempfile.TemporaryDirectory() as tmp:
            # Private scripted executor simulates production metadata with generated
            # pixels only. It makes no model, GPU or benchmark dataset call.
            root = h._execute(repo=self.repo, artifact_repo=tmp, model="internvl3",
                              entry=load_policy(self.repo)["classification"]["internvl3"],
                              run_id=shard0["run_id"], rows=rows, source_hash=a.MANIFEST_SHA,
                              dataset_fingerprint=a.FINGERPRINT, source="INSPECSAFE",
                              image_reader=lambda row: image, shard_count=4, shard_index=0, commit=self.merge,
                              backend_factory=lambda: h.ScriptedBackend(responses), protocol_version=a.PROTOCOL_ID,
                              execution_plan_run=shard0)
            # Explicit synthetic fixture lineage; historical hashes remain untouched.
            manifest = json.loads((root / "run_manifest.json").read_bytes())
            manifest["rerun_of"] = shard0["rerun_of"]
            (root / "run_manifest.json").write_bytes(json_bytes(manifest))
            status = json.loads((root / "run_status.json").read_bytes())
            self.assertEqual(status["status"], "COMPLETED")
            status["artifact_sha256"]["run_manifest.json"] = sha(json_bytes(manifest))
            (root / "run_status.json").write_bytes(json_bytes(status))
            path_for = h._run_path
            with patch.object(h, "_run_path", side_effect=lambda repo, model, run_id: path_for(tmp, model, run_id)):
                a.verify_progression(self.repo, self.authority, "internvl3", shard1["run_id"])
                raw = next(root.glob("calls/*/response.raw"))
                raw.write_bytes(raw.read_bytes() + b"\ncorrupt")
                with self.assertRaisesRegex(PermissionError, "RAW_PERSISTENCE_INTEGRITY_FAILURE"):
                    a.verify_progression(self.repo, self.authority, "internvl3", shard1["run_id"])

    def test_native_guard_denies_old_and_unauthorized_ids_without_model_load(self):
        entry = load_policy(self.repo)["classification"]["internvl3"]
        for run_id in ("wrong", a.OLD_RUN_ID, "internvl3-p21-shard0-rerun2"):
            context = bridge.context_for("internvl3", entry, bridge.RunIdentity(run_id, self.merge, "INSPECSAFE"))
            with self.assertRaisesRegex(PermissionError, "EXACT_P21_RUN_ID_REQUIRED"):
                bridge.require_production_context("internvl3", context, self.repo)
        for model in ("qwen3", "qwen2_5", "moondream"):
            entry = load_policy(self.repo, qwen3_runtime=model == "qwen3")["classification"][model]
            context = bridge.context_for(model, entry, bridge.RunIdentity(model + "-first", self.merge, "INSPECSAFE"))
            with self.assertRaisesRegex(PermissionError, "INTERNVL3_ONLY_P21"):
                bridge.require_production_context(model, context, self.repo)

    def test_plan_and_historical_scientific_authority_runtime_bytes_unchanged(self):
        for path, digest in a.PRESERVED_SHA256.items():
            raw = git(ROOT, "show", a.BASE + ":" + path, raw=True)
            self.assertEqual((ROOT / path).read_bytes(), raw, path)
            self.assertEqual(sha(raw), digest, path)
        self.assertEqual(sha((ROOT / a.PLAN_PATH).read_bytes()), a.PLAN_SHA256)
        self.assertEqual(json.loads((ROOT / a.PLAN_PATH).read_bytes()), a.execution_plan())
        self.assertEqual(sha((ROOT / a.AMENDMENT_PATH).read_bytes()), a.AMENDMENT_SHA256)
        self.assertEqual([r["sample_count"] for r in a.execution_plan()["runs"]], [1254, 1253, 1253, 1253])
        self.assertEqual([r["attempt_kind"] for r in a.execution_plan()["runs"]],
                         ["CROSS_PROTOCOL_RERUN", "FIRST_ATTEMPT", "FIRST_ATTEMPT", "FIRST_ATTEMPT"])

    def test_fresh_process_static_preflight_never_reads_dataset_model_gpu_network(self):
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
original_read, original_open = Path.read_bytes, builtins.open
def guarded_read(path):
    if 'data' in path.parts and 'safeshift' not in path.parts:
        forbidden()
    return original_read(path)
def guarded_open(path, *args, **kwargs):
    if isinstance(path, (str, Path)) and 'data' in Path(path).parts and 'safeshift' not in Path(path).parts:
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
        assert result['models'] == ['internvl3'] and len(result['authorized_runs']) == 4
    with contextlib.redirect_stdout(io.StringIO()):
        assert owner.main(['preflight', '--repo', str(repo)]) == (0 if expected else 2)
assert not (repo / 'data/processed/benchmark/p2').exists()
'''
        for commit, expected in ((self.f2, "false"), (self.merge, "true")):
            self.checkout(commit)
            subprocess.run([sys.executable, "-c", code, str(self.repo), expected], cwd=ROOT, check=True)

    def test_actual_f2_structure_and_synthetic_final_merge(self):
        path = ROOT / a.AUTHORITY_PATH
        if not path.exists():
            self.skipTest("F2 authority is added only after F1 is committed")
        doc = json.loads(path.read_bytes())
        f1, f2 = doc["implementation_freeze_commit_sha"], git(ROOT, "rev-parse", "HEAD")
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f1).split(), [f1, a.BASE])
        self.assertEqual(git(ROOT, "rev-list", "--parents", "-n", "1", f2).split(), [f2, f1])
        self.assertEqual(git(ROOT, "diff", "--name-status", f1, f2), "A\t" + a.AUTHORITY_PATH)
        self.assertEqual(doc, a.expected_authority(f1, git(ROOT, "rev-parse", f1 + "^{tree}")))
        self.assertEqual(git(ROOT, "cat-file", "commit", f2, raw=True),
                         a.f2_commit_bytes(f1, git(ROOT, "rev-parse", f2 + "^{tree}")))
        with self.assertRaises(PermissionError):
            h.authorize_production(ROOT)
        self.final(f2=f2)
        self.assertEqual(h.authorize_production(self.repo)[1], doc)


if __name__ == "__main__":
    unittest.main()
