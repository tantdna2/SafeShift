"""CPU qualification guard/contract tests, public synthetic inputs only."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import GENERATION, MODELS
from scripts import rehearse_candidate_cpu as q
from scripts.pilot_source_audit import MODELS as SOURCE_MODELS


@contextmanager
def snapshot_case():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        snapshot = root / "public"
        snapshot.mkdir()
        write(snapshot / "config.json", {"synthetic": True})
        lock = root / "lock.json"
        write(lock, {"fixture": {"files": {"config.json": sha(snapshot / "config.json")}}})
        with patch.object(q, "LOCK", lock):
            yield root, snapshot


def make_symlink(test, link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except NotImplementedError:
        test.skipTest("OS symbolic links unavailable")
    except OSError as error:
        if error.errno in (errno.EPERM, errno.EACCES, errno.ENOSYS) or getattr(error, "winerror", None) == 1314:
            test.skipTest("OS symbolic link permission unavailable")
        raise


class CandidateCPUTests(unittest.TestCase):
    def test_exact_identity_does_not_enroll_production_candidates(self):
        self.assertEqual(SOURCE_MODELS["internvl35"], ("OpenGVLab/InternVL3_5-4B-HF", "6bd4487402110ef9889ba50eb7aefeb302526fed"))
        self.assertEqual(SOURCE_MODELS["minicpm4"], ("openbmb/MiniCPM-V-4", "6f69a8235885be89608f3a71ffd40695b379e1e7"))
        self.assertEqual(set(MODELS), {"gemma", "phi", "smolvlm2"})

    def test_snapshot_missing_corrupt_extra_and_weight_files_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            snapshot = root / "public"
            snapshot.mkdir()
            write(snapshot / "config.json", {"synthetic": True})
            lock = root / "lock.json"
            write(lock, {"fixture": {"files": {"config.json": sha(snapshot / "config.json")}}})
            with patch.object(q, "LOCK", lock):
                self.assertIn("files", q.verify_snapshot(snapshot, "fixture"))
                (snapshot / "config.json").write_text("changed")
                with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                    q.verify_snapshot(snapshot, "fixture")
                (snapshot / "config.json").unlink()
                with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                    q.verify_snapshot(snapshot, "fixture")
                (snapshot / "model.safetensors").write_bytes(b"NOT_WEIGHTS")
                with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                    q.verify_snapshot(snapshot, "fixture")

    def test_valid_exact_flat_snapshot_and_staging_pass(self):
        with snapshot_case() as (root, snapshot):
            spec = q.verify_snapshot(snapshot, "fixture")
            with patch.object(q.shutil, "copytree", side_effect=AssertionError("NO_RECURSIVE_COPY")):
                self.assertEqual(q.stage_snapshot(snapshot, root / "staged", "fixture"), spec)
            self.assertEqual({p.name for p in (root / "staged").iterdir()}, {"config.json"})
            self.assertEqual(sha(root / "staged/config.json"), spec["files"]["config.json"])

    def test_extra_directories_and_hidden_sources_are_rejected_before_copy(self):
        for name in ("extra", ".hidden"):
            with self.subTest(name=name), snapshot_case() as (root, snapshot):
                extra = snapshot / name
                extra.mkdir()
                (extra / "injected.py").write_text("raise AssertionError('MUST_NOT_IMPORT')")
                with patch.object(q.shutil, "copyfile", side_effect=AssertionError("MUST_NOT_COPY")), \
                        self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                    q.stage_snapshot(snapshot, root / "staged", "fixture")
                self.assertFalse((root / "staged").exists())

    def test_empty_extra_directory_is_rejected(self):
        with snapshot_case() as (_, snapshot):
            (snapshot / "empty").mkdir()
            with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                q.verify_snapshot(snapshot, "fixture")

    def test_locked_filename_cannot_be_a_directory(self):
        with snapshot_case() as (_, snapshot):
            (snapshot / "config.json").unlink()
            (snapshot / "config.json").mkdir()
            with self.assertRaisesRegex(ValueError, "REGULAR_FILE"):
                q.verify_snapshot(snapshot, "fixture")

    def test_hidden_extra_file_is_rejected(self):
        with snapshot_case() as (_, snapshot):
            (snapshot / ".injected.py").write_text("raise AssertionError('MUST_NOT_IMPORT')")
            with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                q.verify_snapshot(snapshot, "fixture")

    def test_symlinked_directory_is_rejected(self):
        with snapshot_case() as (root, snapshot):
            target = root / "external"
            target.mkdir()
            (target / "injected.py").write_text("raise AssertionError('MUST_NOT_IMPORT')")
            link = snapshot / "extra"
            make_symlink(self, link, target, directory=True)
            with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                q.verify_snapshot(snapshot, "fixture")
            # A link using an expected file name must also fail the type check.
            link.unlink()
            (snapshot / "config.json").unlink()
            make_symlink(self, snapshot / "config.json", target, directory=True)
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                q.verify_snapshot(snapshot, "fixture")

    def test_symlinked_root_is_rejected_without_resolving_it(self):
        with snapshot_case() as (root, snapshot):
            link = root / "root_alias"
            make_symlink(self, link, snapshot, directory=True)
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                q.stage_snapshot(link.absolute(), root / "staged", "fixture")

    def test_symlinked_file_and_dangling_link_are_rejected(self):
        with snapshot_case() as (root, snapshot):
            source = snapshot / "config.json"
            target = root / "config.json"
            source.rename(target)
            make_symlink(self, source, target)
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                q.verify_snapshot(snapshot, "fixture")
            source.unlink()
            target.rename(source)
            make_symlink(self, snapshot / "dangling.py", root / "absent")
            with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                q.verify_snapshot(snapshot, "fixture")

    @unittest.skipUnless(sys.platform == "win32", "Windows junction test")
    def test_windows_junction_root_and_child_are_rejected(self):
        for root_alias in (False, True):
            with self.subTest(root_alias=root_alias), snapshot_case() as (root, snapshot):
                target = root / "external"
                target.mkdir()
                (target / "injected.py").write_text("raise AssertionError('MUST_NOT_IMPORT')")
                link = root / "root_alias" if root_alias else snapshot / "config.json"
                if not root_alias:
                    link.unlink()
                result = subprocess.run(["cmd", "/d", "/c", "mklink", "/J", str(link), str(target)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                try:
                    self.assertTrue(link.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
                    with self.assertRaisesRegex(ValueError, "ALIAS"):
                        q.verify_snapshot(link if root_alias else snapshot, "fixture")
                finally:
                    # Remove only the junction entry; do not recurse into target.
                    os.rmdir(link)
                self.assertTrue((target / "injected.py").is_file())

    def test_reparse_attributes_are_rejected_for_regular_file_or_root(self):
        for root_alias in (False, True):
            with self.subTest(root_alias=root_alias), snapshot_case() as (_, snapshot):
                selected = snapshot if root_alias else snapshot / "config.json"
                original = Path.lstat
                def synthetic_reparse(path):
                    info = original(path)
                    if path == selected:
                        return SimpleNamespace(st_mode=info.st_mode, st_nlink=info.st_nlink,
                                               st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
                    return info
                with patch.object(Path, "lstat", synthetic_reparse), self.assertRaisesRegex(ValueError, "ALIAS"):
                    q.verify_snapshot(snapshot, "fixture")

    def test_hardlinked_source_is_rejected(self):
        with snapshot_case() as (root, snapshot):
            os.link(snapshot / "config.json", root / "other_name.json")
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                q.verify_snapshot(snapshot, "fixture")

    def test_source_directory_added_during_copy_is_rejected(self):
        with snapshot_case() as (root, snapshot):
            original = q.shutil.copyfile
            def changed_source(source, target, **kwargs):
                original(source, target, **kwargs)
                (snapshot / "extra").mkdir()
                (snapshot / "extra/injected.py").write_text("raise AssertionError('MUST_NOT_IMPORT')")
            with patch.object(q.shutil, "copyfile", changed_source), self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                q.stage_snapshot(snapshot, root / "staged", "fixture")
            self.assertFalse((root / "staged/extra").exists())

    def test_corrupt_staged_bytes_are_rejected_before_import(self):
        with snapshot_case() as (root, snapshot):
            original = q.shutil.copyfile
            def corrupt_copy(source, target, **kwargs):
                self.assertIs(kwargs["follow_symlinks"], False)
                original(source, target, **kwargs)
                target.write_text("changed during copy")
            with patch.object(q.shutil, "copyfile", corrupt_copy), self.assertRaisesRegex(ValueError, "CHECKSUM"):
                q.stage_snapshot(snapshot, root / "staged", "fixture")

    def test_scripted_actual_raw_writer_failure_does_not_parse(self):
        # Uses the existing engine's test rather than a second execution engine.
        from test_pilot import ArtifactAndEngineTests
        test = ArtifactAndEngineTests("test_raw_writer_error_keeps_tail_not_attempted")
        result = unittest.TestResult()
        test.run(result)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)

    def test_generation_constants_not_mutated_by_rehearsal(self):
        expected = {"do_sample": False, "num_beams": 1, "max_new_tokens": 64,
                    "use_cache": True, "return_dict_in_generate": True,
                    "output_scores": False, "output_logits": False}
        self.assertEqual(GENERATION, expected)

    def test_source_script_has_no_model_execution_or_snapshot_download(self):
        import ast
        tree = ast.parse(Path(q.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                self.assertNotIn(name, ("snapshot_download", "hf_hub_download", "forward", "generate"))


if __name__ == "__main__":
    unittest.main()
