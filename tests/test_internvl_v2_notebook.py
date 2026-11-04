"""Notebook payload/credential/fence checks; never execute a Kaggle preflight."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zlib

from safeshift.internvl_v2_runtime import ROOT, IDENTITY, runtime_sources
from safeshift.pilot.contract import digest
from scripts.build_internvl_v2 import build

NOTEBOOK = ROOT / "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2.ipynb"


class NotebookTests(unittest.TestCase):
    def unpack(self):
        nb = json.loads(NOTEBOOK.read_text(encoding="utf8"))
        code = "".join(nb["cells"][1]["source"])
        tree = ast.parse(code)
        packed_call = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == "packed" for t in n.targets))
        packed = zlib.decompress(base64.b64decode(ast.literal_eval(packed_call.args[0].args[0])))
        payload = json.loads(packed)
        spec = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "spec" for t in n.targets))
        return nb, code, packed, payload, spec

    def test_committed_source_builder_reproducibility_and_empty_outputs(self):
        nb, code, packed, payload, spec = self.unpack()
        self.assertEqual(build(nb["metadata"]["safeshift"]["runtime_commit"],
            continuous=nb["metadata"]["safeshift"].get("operational_campaign") == "internvl-v2-6626498951"), nb)
        self.assertEqual(spec["identity"], IDENTITY)
        self.assertEqual(set(payload), set(runtime_sources()))
        self.assertEqual({n: hashlib.sha256(s.encode()).hexdigest() for n, s in payload.items()}, spec["manifest"])
        self.assertEqual(digest(spec["manifest"]), nb["metadata"]["safeshift"]["manifest_sha256"])
        self.assertIn(hashlib.sha256(packed).hexdigest(), code)
        self.assertIsNone(nb["metadata"]["safeshift"]["execution_authority"])
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])
                compile("".join(cell["source"]), "<notebook>", "exec")

    def test_no_embedded_credentials_private_inputs_or_outputs(self):
        nb, code, _, payload, _ = self.unpack()
        text = code + "\n" + "\n".join(payload.values())
        for pattern in (r"hf_[A-Za-z0-9]{20,}", r"gh[pousr]_[A-Za-z0-9]{20,}",
                        r"github_pat_[A-Za-z0-9_]{20,}", r"-----BEGIN .*PRIVATE KEY-----",
                        r"KGAT_[A-Za-z0-9_-]{20,}"):
            self.assertIsNone(re.search(pattern, text), pattern)
        self.assertFalse(any(n.startswith(("data/", "notes/")) for n in payload))
        self.assertNotIn("get_secret(", code)
        self.assertNotIn("kaggle.json", code)
        self.assertNotIn("kernels_push", code)
        self.assertNotIn("os.environ", code)
        self.assertIn("from scripts.internvl_v2_campaign import launch", code)
        self.assertIn("runtime_commit=", code)

    def test_embedded_execute_cli_fenced_in_empty_offline_process(self):
        _, _, _, payload, _ = self.unpack()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, content in payload.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content.encode())
            code = """import sys
sys.path.insert(0, sys.argv[1])
from scripts.internvl_v2 import main
for args in (['--mode','execute'], ['--worker','native']):
    try: main(['--spec','does-not-exist',*args])
    except PermissionError as error: assert 'NOT_AUTHORIZED' in str(error)
    else: raise AssertionError('NATIVE_FENCE_BYPASS')
from safeshift import internvl_v2_campaign as control
from safeshift.internvl_v2_runtime import source_spec
from scripts.internvl_v2_campaign import launch
control.active_submissions = lambda: []
try: launch(source_spec(), '0' * 40)
except ValueError as error: assert 'REVIEW_HOLD' in str(error)
else: raise AssertionError('CAMPAIGN_FENCE_BYPASS')
print('EMPTY_VM_NATIVE_FENCE_PASS')
"""
            result = subprocess.run([sys.executable, "-I", "-S", "-B", "-c", code, str(root)],
                                    cwd=root, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("EMPTY_VM_NATIVE_FENCE_PASS", result.stdout)

    def test_builder_rejects_uncommitted_runtime(self):
        from unittest.mock import patch
        nb, _, _, _, _ = self.unpack()
        with patch("scripts.build_internvl_v2.subprocess.check_output", return_value=b"CHANGED"), \
                self.assertRaisesRegex(ValueError, "UNCOMMITTED_RUNTIME"):
            build(nb["metadata"]["safeshift"]["runtime_commit"])
