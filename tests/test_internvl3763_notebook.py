"""Committed-source PREP packaging, not Kaggle execution."""
import ast
import base64
import hashlib
import json
import unittest
from unittest.mock import patch
import zlib
from scripts.build_internvl3763 import build
from safeshift import internvl3763 as runtime
from safeshift.pilot.artifacts import read


class NotebookTests(unittest.TestCase):
    def test_rebuild_empty_outputs_exact_source_manifest_and_closed_preparation(self):
        path = runtime.ROOT / "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763_PREP.ipynb"
        notebook = read(path)
        metadata = notebook["metadata"]["safeshift"]
        self.assertEqual(build(metadata["runtime_commit"]), notebook)
        self.assertIsNone(metadata["execution_authority"])
        self.assertEqual(metadata["status"], "BLOCKED_PREPARATION_ONLY")
        cell = notebook["cells"][1]
        self.assertEqual(cell["outputs"], [])
        self.assertIsNone(cell["execution_count"])
        code = "".join(cell["source"])
        compile(code, "<prep>", "exec")
        expression = ast.parse(code).body[2].value
        encoded = ast.literal_eval(expression.args[0].args[0])
        payload = json.loads(zlib.decompress(base64.b64decode(encoded)))
        self.assertEqual({name: hashlib.sha256(text.encode()).hexdigest() for name, text in payload.items()},
            runtime.source_spec()["manifest"])
        self.assertIn("'--mode', 'prepare'", code)
        self.assertNotIn("kernels_push", code)

    def test_builder_rejects_uncommitted_runtime_or_nonexact_ref(self):
        with self.assertRaises(ValueError):
            build("main")
        with patch("scripts.build_internvl3763.subprocess.check_output", return_value=b"changed"), \
                self.assertRaisesRegex(ValueError, "UNCOMMITTED_RUNTIME"):
            build("a"*40)


if __name__ == "__main__":
    unittest.main()
