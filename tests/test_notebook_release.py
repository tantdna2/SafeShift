"""Adversarial notebook/snapshot checks; tiny synthetic source, no model calls."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zlib

from scripts.check_notebook_release import (
    canonical, child_env, evaluate, inspect_notebook, main, sha, strict_json,
    unpack_snapshot,
)


def fixture(sources=None):
    sources = sources if sources is not None else {"safeshift/example.py": "VALUE = 1\n"}
    digest = sha(canonical({p: sha(t.encode()) for p, t in sources.items()}))
    blob = base64.b64encode(zlib.compress(json.dumps(sources).encode())).decode()
    code = ("import base64,json,zlib\n"
            f"payload=json.loads(zlib.decompress(base64.b64decode({blob!r})))\n"
            f"expected_source_sha256={digest!r}\n")
    nb = {"nbformat": 4, "nbformat_minor": 5,
          "metadata": {"safeshift": {"source_sha256": digest}},
          "cells": [{"cell_type": "code", "id": "synthetic", "source": code.splitlines(True),
                     "outputs": [], "execution_count": None}]}
    return nb, sources, digest


class NotebookReviewTests(unittest.TestCase):
    def setUp(self):
        self.nb, self.sources, self.digest = fixture()
        self.expected = canonical(self.nb)

    def check(self, nb=None, expected=None, sources=None, digest=None):
        return inspect_notebook(canonical(self.nb if nb is None else nb),
                                self.expected if expected is None else expected,
                                self.sources if sources is None else sources,
                                self.digest if digest is None else digest)

    def test_valid_source_and_hash_without_executing_cell(self):
        self.nb["cells"][0]["source"].append("raise RuntimeError('MUST_NOT_EXECUTE')\n")
        result = self.check(expected=canonical(self.nb))
        self.assertEqual(result["status"], "PASS")

    def test_stale_builder_or_owner_cell_edit_rejected(self):
        self.nb["cells"][0]["source"].append("OTHER_PATH = 'manual-edit'\n")
        with self.assertRaisesRegex(ValueError, "BUILDER_BYTES_DIFFER"):
            self.check()

    def test_executed_output_or_count_rejected(self):
        for key, value in (("outputs", [{"text": "private"}]), ("execution_count", 1)):
            nb = copy.deepcopy(self.nb)
            nb["cells"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "EXECUTED"):
                self.check(nb)

    def test_missing_duplicate_or_empty_cell_ids(self):
        for cid in (None, ""):
            nb = copy.deepcopy(self.nb); nb["cells"][0]["id"] = cid
            with self.assertRaisesRegex(ValueError, "CELL_ID"):
                self.check(nb)
        self.nb["cells"].append(copy.deepcopy(self.nb["cells"][0]))
        with self.assertRaisesRegex(ValueError, "CELL_ID"):
            self.check()

    def test_duplicate_json_keys_and_nonfinite_rejected(self):
        for text in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(ValueError):
                strict_json(text)

    def test_source_changed_despite_self_consistent_payload(self):
        nb, _, _ = fixture({"safeshift/example.py": "VALUE = 2\n"})
        with self.assertRaises(ValueError):
            self.check(nb)
        with self.assertRaisesRegex(ValueError, "EMBEDDED_SOURCE"):
            self.check(sources={"safeshift/example.py": "VALUE = 2\n"})

    def test_metadata_digest_drift(self):
        self.nb["metadata"]["safeshift"]["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "METADATA_DIGEST"):
            self.check(expected=canonical(self.nb))

    def test_traversal_and_windows_paths_inside_payload(self):
        for name in ("../bad.py", "/bad.py", "C:/bad.py", "a\\bad.py"):
            nb, sources, digest = fixture({name: "VALUE=1\n"})
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "UNSAFE_PATH"):
                self.check(nb, canonical(nb), sources, digest)

    def test_corrupt_encoded_payload_and_syntax(self):
        nb = copy.deepcopy(self.nb)
        nb["cells"][0]["source"][1] = "payload=json.loads(zlib.decompress(base64.b64decode('???')))\n"
        with self.assertRaises(ValueError):
            self.check(nb)
        self.nb["cells"][0]["source"].append("if broken\n")
        with self.assertRaises(SyntaxError):
            self.check()

    def test_nonliteral_payload_not_executed(self):
        self.nb["cells"][0]["source"][1] = "payload=base64.b64decode(open('secret').read())\n"
        with self.assertRaisesRegex(ValueError, "NONLITERAL"):
            self.check()

    def test_trailing_compressed_stream_rejected(self):
        blob = base64.b64encode(zlib.compress(b'{}') + b'extra').decode()
        self.nb["cells"][0]["source"][1] = f"payload=base64.b64decode({blob!r})\n"
        with self.assertRaisesRegex(ValueError, "PAYLOAD_LIMIT_OR_TRAILING"):
            self.check()

    def test_secret_pattern_even_if_builder_agrees(self):
        self.nb["cells"][0]["source"].append("TOKEN = 'hf_" + "x" * 25 + "'\n")
        with self.assertRaisesRegex(ValueError, "CREDENTIAL"):
            self.check(expected=canonical(self.nb))

    def test_secret_inside_compressed_source_rejected(self):
        nb, sources, digest = fixture({"safeshift/example.py": "TOKEN = 'hf_" + "x" * 25 + "'\n"})
        with self.assertRaisesRegex(ValueError, "CREDENTIAL"):
            self.check(nb, canonical(nb), sources, digest)


class SnapshotAndAuthorityTests(unittest.TestCase):
    def archive(self, name, kind=tarfile.REGTYPE, duplicate=False):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as tar:
            for _ in range(2 if duplicate else 1):
                item = tarfile.TarInfo(name); item.type = kind
                if kind == tarfile.REGTYPE:
                    item.size = 1; tar.addfile(item, io.BytesIO(b'x'))
                else:
                    item.linkname = "outside"; tar.addfile(item)
        return stream.getvalue()

    def test_regular_snapshot_and_reject_duplicate_symlink_traversal_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            unpack_snapshot(self.archive("src/file.py"), Path(tmp))
            self.assertEqual((Path(tmp) / "src/file.py").read_bytes(), b'x')
        for name, kind, duplicate in (("../bad", tarfile.REGTYPE, False),
                                      ("alias", tarfile.SYMTYPE, False),
                                      ("same", tarfile.REGTYPE, True),
                                      ("model.safetensors", tarfile.REGTYPE, False),
                                      ("data/private.json", tarfile.REGTYPE, False)):
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
                unpack_snapshot(self.archive(name, kind, duplicate), Path(tmp))

    def test_no_native_live_or_credentials_inherited(self):
        with patch.dict(os.environ, {"SAFESHIFT_SMOL_SNAPSHOT": "private", "HF_TOKEN": "secret",
                                    "PYTHONPATH": "stale", "SAFESHIFT_REAL_PIP_BOOTSTRAP": "1"}):
            env = child_env()
        for key in ("SAFESHIFT_SMOL_SNAPSHOT", "HF_TOKEN", "PYTHONPATH", "SAFESHIFT_REAL_PIP_BOOTSTRAP"):
            self.assertNotIn(key, env)
        self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_nonexact_ref_fail_closed_without_git_or_authority(self):
        with patch("scripts.check_notebook_release.command") as command:
            result = evaluate(Path('.'), "main")
        command.assert_not_called()
        self.assertEqual(result["software_status"], "FAIL")
        self.assertEqual(result["release_status"], "BLOCKED")
        self.assertEqual(result["gates"]["G5_behavior"], "REQUIRES_AUTHORIZED_GPU")

    def test_receipt_cannot_overwrite_or_issue_grant(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"; path.write_bytes(b'original')
            with self.assertRaises(FileExistsError):
                main(["--runtime-ref", "0" * 40, "--output", str(path)])
            self.assertEqual(path.read_bytes(), b'original')


if __name__ == "__main__":
    unittest.main()
