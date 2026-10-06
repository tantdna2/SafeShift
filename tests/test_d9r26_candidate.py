"""Candidate identity is not authorization; all tests are metadata/synthetic."""

import ast
from contextlib import redirect_stdout
import hashlib
import inspect
import io
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from safeshift.protocol import freeze_candidate as f
from safeshift.protocol.classification_policy import ROOT
from safeshift.runners import p2_harness as h, p2_preflight as p, p2_owner as owner


class CandidateTests(unittest.TestCase):
    def test_candidate_exact_hashes_and_git_repository_bytes(self):
        candidate = f.verify_candidate()
        self.assertEqual(set(candidate["identity_sha256"]), set(f.PINNED))
        for name, digest in candidate["identity_sha256"].items():
            raw = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            raw.decode("utf-8")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest, name)
            # Compare the actual Git clean-filter blob identity, including new files.
            blob = subprocess.check_output(["git", "hash-object", "--path=" + name, name], cwd=ROOT).decode().strip()
            self.assertEqual(blob, hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(), name)
            self.assertFalse(name.startswith(("data/", "outputs/", "weights/")))
        self.assertEqual(len(f.PINNED), len(set(f.PINNED)))

    def test_changed_active_source_requires_explicit_candidate_update(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (*f.PINNED, f.PATH):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            f.verify_candidate(root)
            path = root / "safeshift/runners/p2_bridge.py"
            path.write_bytes(path.read_bytes() + b"\n# changed\n")
            with self.assertRaisesRegex(ValueError, "CANDIDATE_IDENTITY_MISMATCH"):
                f.verify_candidate(root)

    def test_freeze_authority_roster_dataset_and_readiness(self):
        c = f.verify_candidate()
        self.assertEqual(c["status"], "FREEZE_CANDIDATE_NOT_FROZEN")
        for name in ("protocol_freeze", "protocol_freeze_commit_sha", "implementation_freeze"):
            self.assertEqual(c[name], "PENDING")
        self.assertFalse(c["inspecsafe_inference_authorized"])
        self.assertFalse(h.contract()["inspecsafe_inference_authorized"])
        self.assertEqual(set(c["models"]), set(h.MODELS))
        self.assertEqual(c["dataset"]["sample_count"], 5013)
        self.assertEqual(c["governance"]["grounding"], "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE")
        self.assertFalse(c["governance"]["p1_implemented"])
        self.assertFalse(c["governance"]["model_gpu_execution"])
        self.assertFalse(c["readiness"]["ready_to_run_inspecsafe"])

    def test_cli_static_preflight_is_no_gpu_dataset_or_backend_and_blocks_run(self):
        with patch.object(h, "verify_dataset", side_effect=AssertionError("NO_DATASET")) as data, \
                patch.object(h, "resolve_production_backend", side_effect=AssertionError("NO_BACKEND")) as backend, \
                patch.object(p, "runtime_observation", side_effect=AssertionError("NO_GPU")) as gpu, redirect_stdout(io.StringIO()) as out:
            self.assertEqual(owner.main(["preflight"]), 2)
            self.assertIn("PROTOCOL_FREEZE_REQUIRED", out.getvalue())
            self.assertEqual(owner.main(["run", "--model", "qwen3", "--run-id", "blocked",
                "--dataset-root", "NEVER_READ", "--manifest-path", "NEVER_READ", "--provenance-path", "NEVER_READ"]), 2)
            data.assert_not_called()
            backend.assert_not_called()
            gpu.assert_not_called()
        self.assertNotIn("backend_factory", inspect.signature(h.production_run).parameters)

    def test_historical_generation_and_active_science_unchanged(self):
        from scripts.w2_moondream_external_gate import load_gate_plan
        with self.assertRaisesRegex(ValueError, "PROTECTED_SOURCE_CHANGED"):
            load_gate_plan(ROOT)  # D9R26 never silently repins a historical gate.
        # Compare exact method ASTs, allowing only authorized condition guards.
        for name, cls in (("internvl3.py", "InternVL3Runner"), ("moondream2.py", "Moondream2Runner")):
            path = "safeshift/runners/" + name
            before = subprocess.check_output(["git", "show", f.BASE + ":" + path], cwd=ROOT)
            after = (ROOT / path).read_bytes()
            def methods(raw):
                body = next(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == cls)
                return {n.name: ast.dump(n) for n in body.body if isinstance(n, ast.FunctionDef)}
            a, z = methods(before), methods(after)
            for method in ("generate_raw", "initialize", "load"):
                self.assertEqual(a[method], z[method], path + ":" + method)
        for path in ("configs/pre_freeze/d9r22_seminar_scope.v1.json",
                     "configs/pre_freeze/production_classification_policy.d9r23.v1.json",
                     "configs/pre_freeze/d9r24_metric_contract.v1.json", "prompts/p2_classification_c1_v1.txt",
                     "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/reporting.py"):
            self.assertEqual(subprocess.check_output(["git", "show", f.BASE + ":" + path], cwd=ROOT),
                             (ROOT / path).read_bytes().replace(b"\r\n", b"\n"), path)


if __name__ == "__main__":
    unittest.main()
