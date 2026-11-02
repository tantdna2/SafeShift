"""Exact generated payload, clean child execution and preservation of old notebooks."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zlib

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import contract
from safeshift.pilot.artifacts import read, verify_archive
from safeshift.pilot.contract import digest
from scripts.build_fresh_fulltrain_notebooks import notebook


class FreshNotebookTests(unittest.TestCase):
    def paths(self):
        for key in contract.planning.MODELS:
            for diagnostic in (False, True):
                kind = "DIAGNOSTIC" if diagnostic else "PREP"
                yield key, diagnostic, ROOT / f"notebooks/SafeShift_FRESH_FULLTRAIN_{kind}_{key}.ipynb"

    def test_exact_committed_payload_builder_compile_empty_outputs(self):
        for key, diagnostic, path in self.paths():
            with self.subTest(path=path.name):
                nb = read(path)
                ref = nb["metadata"]["safeshift"]["runtime_ref"]
                self.assertEqual(path.read_bytes(), (json.dumps(notebook(key, ref, diagnostic=diagnostic),
                                                               indent=1, ensure_ascii=False) + "\n").encode())
                for cell in nb["cells"]:
                    if cell["cell_type"] != "code":
                        continue
                    self.assertEqual(cell["outputs"], [])
                    self.assertIsNone(cell["execution_count"])
                    code = "".join(cell["source"])
                    compile(code, path.name, "exec")
                    encoded = re.search(r"base64\.b64decode\('([^']+)'\)", code).group(1)
                    payload = json.loads(zlib.decompress(base64.b64decode(encoded)))
                    self.assertEqual(set(payload), set(contract.sources()))
                    for name, text in payload.items():
                        self.assertEqual(text.encode(), (ROOT / name).read_bytes())
                    self.assertEqual(digest({n: hashlib.sha256(t.encode()).hexdigest() for n, t in payload.items()}),
                                     nb["metadata"]["safeshift"]["source_sha256"])

    def test_every_notebook_clean_cpu_child_repeated_no_attempt_or_input(self):
        for key, diagnostic, path in self.paths():
            with self.subTest(path=path.name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                code = "\n".join("".join(c["source"]) for c in read(path)["cells"] if c["cell_type"] == "code")
                script = root / "run.py"
                script.write_text(code, encoding="utf-8")
                for _ in range(2):
                    result = subprocess.run([sys.executable, "-B", "-S", str(script)], cwd=root,
                        env={**os.environ, "PYTHONPATH": "", "CUDA_VISIBLE_DEVICES": ""},
                        capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stderr)
                archives = list((root / "data/processed/fresh_fulltrain").glob("*.zip"))
                self.assertEqual(len(archives), 2)
                for archive in archives:
                    self.assertEqual(set(verify_archive(archive)),
                                     {"release.json", "source_manifest.json", "environment.json", "native_contract.json"})
                    r = read(archive.with_suffix("") / "release.json")
                    self.assertEqual(r["status"], "BLOCKED")
                    self.assertEqual(r["native_calls"], 0)
                    self.assertFalse(r["attempt_consumed"])
                    self.assertFalse(r["owner_slot_created"])
                    self.assertEqual(r["levels"]["ENVIRONMENT_OBSERVED"], "PASS")
                    self.assertEqual(r["levels"]["WEIGHTS_LOADED"], "NOT_RUN")

    def test_corrupt_payload_fails_before_prepare_and_preserves_failure(self):
        _, _, path = next(self.paths())
        nb = read(path)
        code = "".join(nb["cells"][1]["source"])
        checksum = nb["metadata"]["safeshift"]["source_sha256"]
        code = code.replace(checksum, "0" * 64)
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "run.py"
            script.write_text(code, encoding="utf-8")
            r = subprocess.run([sys.executable, "-B", "-S", str(script)], cwd=tmp,
                               capture_output=True, text=True, timeout=60)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("EMBEDDED_SOURCE_CORRUPT", r.stderr)
            self.assertFalse((Path(tmp) / "data/processed/fresh_fulltrain").exists())
            archives = list((Path(tmp) / "data/processed/fresh_fulltrain_bootstrap").glob("*.zip"))
            self.assertEqual(len(archives), 1)
            self.assertEqual(set(verify_archive(archives[0])), {"failure.json"})

    def test_historical_notebooks_contracts_and_science_bytes_unchanged(self):
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", contract.BASE,
            "notebooks", "configs/candidate160", "configs/cpu_g2_g3", "safeshift/candidates", "safeshift/pilot",
            "configs/pilot", "docs/research/SEMINAR_PROTOCOL.md", "docs/research/seminar_analysis_config.v1.json"],
            cwd=ROOT, text=True).splitlines()
        for name in names:
            with self.subTest(name=name):
                original = subprocess.check_output(["git", "show", f"{contract.BASE}:{name}"], cwd=ROOT)
                self.assertEqual((ROOT / name).read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
