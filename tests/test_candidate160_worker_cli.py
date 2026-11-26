"""Path boundary regressions; native CLI opt-in uses real locked assets, no mocks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from safeshift.candidates.source import ROOT, snapshot_stat, verify_snapshot, stage_snapshot
from safeshift.pilot.artifacts import sha, write


class PathBoundaryTests(unittest.TestCase):
    def test_snapshot_string_and_path_have_identical_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "source"
            snapshot.mkdir()
            (snapshot / "config.json").write_bytes(b'{"synthetic":true}\n')
            spec = {"revision": "synthetic", "files": {"config.json": sha(snapshot / "config.json")}}
            lock = root / "lock.json"
            write(lock, {"fixture": spec})
            for value in (snapshot, str(snapshot)):
                with self.subTest(type=type(value).__name__):
                    self.assertEqual(verify_snapshot(value, "fixture", lock), spec)
                    self.assertTrue(snapshot_stat(value, directory=True))
            target = root / "staged"
            self.assertEqual(stage_snapshot(str(snapshot), str(target), "fixture", lock), spec)
            (target / "config.json").write_bytes(b"CHANGED")
            with self.assertRaisesRegex(ValueError, "SOURCE_CHECKSUM"):
                verify_snapshot(str(target), "fixture", lock)


@unittest.skipUnless(os.environ.get("SAFESHIFT_CANDIDATE_KEY") and
                     os.environ.get("SAFESHIFT_CANDIDATE_SNAPSHOT") and
                     os.environ.get("SAFESHIFT_CANDIDATE_BUNDLE"),
                     "opt-in pinned Linux stack, public snapshot and authorized locked bundle required")
class NativeWorkerCLITests(unittest.TestCase):
    def test_production_check_only_subprocess_without_module_mocks(self):
        # The child is the production -m entrypoint. All its argument values are
        # strings at the OS boundary; real authorization/manifest/PIL/native/meta
        # checks execute. No CUDA, weights or generation is requested.
        with tempfile.TemporaryDirectory(dir=ROOT / "data/processed") as temporary:
            command = [sys.executable, "-B", "-m", "scripts.rehearse_candidate160_worker",
                       "--key", os.environ["SAFESHIFT_CANDIDATE_KEY"],
                       "--snapshot", os.environ["SAFESHIFT_CANDIDATE_SNAPSHOT"],
                       "--bundle", os.environ["SAFESHIFT_CANDIDATE_BUNDLE"],
                       "--output", str(Path(temporary) / "check"), "--ref", "b1a56d0ce3fbd484820f56fa921bfbba9ec7f1d9"]
            child = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=600)
            self.assertEqual(child.returncode, 0, child.stdout[-6000:])


if __name__ == "__main__":
    unittest.main()
