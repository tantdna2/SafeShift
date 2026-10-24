"""CPU smoke checks for the new scaffold; standard library only."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ScaffoldSmokeTests(unittest.TestCase):
    def test_required_entry_points_exist(self):
        for name in (
            "README.md", "AGENTS.md", ".gitignore", ".gitattributes",
            "docs/HISTORY.md", "safeshift/__init__.py", "tests/test_smoke.py",
        ):
            with self.subTest(path=name):
                path = ROOT / name
                self.assertTrue(path.is_file())
                self.assertGreater(path.stat().st_size, 0)

    def test_import_without_site_packages_or_data(self):
        code = (
            "import sys; sys.path.insert(0, sys.argv[1]); import safeshift; "
            "assert not any(n.startswith('safeshift.') for n in sys.modules); "
            "print(safeshift.__file__)"
        )
        with tempfile.TemporaryDirectory() as empty_directory:
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-B", "-c", code, str(ROOT)],
                cwd=empty_directory, capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            Path(result.stdout.strip()).resolve(),
            (ROOT / "safeshift" / "__init__.py").resolve(),
        )


if __name__ == "__main__":
    unittest.main()
