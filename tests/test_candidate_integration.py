"""Stdlib admission/evidence regressions; no ML libraries or dataset access."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import read, sha, write
from safeshift.pilot.contract import GENERATION, MODELS, PROMPT_SHA, source_digest
from safeshift.candidates import loading
from safeshift.candidates.source import ROOT, LOCK, verify_module_cache
from scripts import verify_candidate_evidence as audit


class CandidateIntegrationTests(unittest.TestCase):
    def test_remote_cache_poisoning_rejected_before_import(self):
        import hashlib
        spec = {"revision": "a"*40, "files": {"module.py": hashlib.sha256(b"# harmless\n").hexdigest()}}
        for defect in (None, "initializer", "source", "bytecode", "extra", "hardlink"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d)/"cache"
                leaf = root/"transformers_modules"/spec["revision"]
                leaf.mkdir(parents=True)
                for folder in (root, leaf.parent, leaf): (folder/"__init__.py").write_bytes(b"")
                (leaf/"module.py").write_bytes(b"# harmless\n")
                if defect == "initializer": (leaf.parent/"__init__.py").write_text("raise RuntimeError('do not execute')")
                if defect == "source": (leaf/"module.py").write_bytes(b"changed")
                if defect == "bytecode": (leaf/"__pycache__").mkdir()
                if defect == "extra": (root/"unexpected.py").write_text("raise RuntimeError()")
                if defect == "hardlink": __import__("os").link(leaf/"module.py", Path(d)/"alias")
                if defect is None: verify_module_cache(root, spec)
                else:
                    with self.assertRaises(ValueError): verify_module_cache(root, spec)

    def test_protected_pilot_c1_generation_and_source_bytes(self):
        for filename, checksum in read(LOCK.with_name("protected_source_lock.json"))["files"].items():
            if filename == "AGENTS.md":
                # PR154 merged Owner instructions after the historical source
                # lock. Preserve that lock; assert the exact verified main BASE
                # 39ec489403753ada10f4924c4b0d6077e027f5e1 instructions separately.
                self.assertEqual(checksum, "aa2f1830012fe73ba8859ceea0e87442510cc57bd5d115042dd40ec27def0183")
                checksum = "ad4309eae94bd270a0080eb51d91291239e337fd3fd3612f899a1703bc61e3d2"
            self.assertEqual(sha(ROOT/filename), checksum, filename)
        self.assertEqual(sha(ROOT/"configs/pilot/classification_c1.txt"), PROMPT_SHA)
        self.assertEqual(set(MODELS), {"phi", "smolvlm2", "gemma"})
        self.assertEqual(source_digest(ROOT), "1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884")
        self.assertEqual(GENERATION, {"do_sample": False, "num_beams": 1, "max_new_tokens": 64,
            "use_cache": True, "return_dict_in_generate": True, "output_scores": False, "output_logits": False})

    def test_metadata_lock_exact_model_revision_and_sha(self):
        public, metadata = read(LOCK), read(LOCK.with_name("checkpoint_metadata_lock.json"))
        for key in public:
            self.assertEqual({k: metadata[key][k] for k in ("id", "revision")},
                             {k: public[key][k] for k in ("id", "revision")})
            self.assertEqual(len(metadata[key]["weights"]), 2)
            for name, item in metadata[key]["weights"].items():
                self.assertTrue(name.endswith(".safetensors"))
                self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(item["size"], 0)

    def test_missing_weights_never_reach_loader(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
                loading.verify_weights(Path(d), "internvl35")

    def test_checkpoint_index_corruption_and_alias_fail(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"index.json"
            write(path, {"weight_map": {}})
            for key in ("internvl35", "minicpm4"):
                with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                    loading.checkpoint_index(path, key)

    def test_dependency_mismatch_before_ml_import(self):
        import site
        from scripts import rehearse_candidate_cpu as old
        with patch.object(old.sys, "prefix", "synthetic-isolated-prefix"), \
             patch.object(site, "ENABLE_USER_SITE", False), \
             patch.object(old.metadata, "version", return_value="WRONG"), \
             self.assertRaisesRegex(ValueError, "DEPENDENCY_VERSION"):
            old.environment("internvl35")

    def synthetic_receipts(self, root):
        paths = {"script.py": "synthetic source\n"}
        for name, text in paths.items(): (root/name).write_text(text)
        lock = root/"configs/cpu_g2_g3/public_source_lock.json"
        write(lock, read(LOCK))
        spec = read(LOCK)
        evidence = root/"evidence"
        evidence.mkdir()
        manifest = {"receipts": {}}
        for key in spec:
            receipt = {"schema": "safeshift-candidate-integration-cpu-v1", "model_key": key,
                "model": {k: spec[key][k] for k in ("id", "revision")},
                "source_sha256": {"script.py": sha(root/"script.py")}, "pilot_source_sha256": "fixture",
                "sources_unchanged_during_run": True, "status": "CPU_CHECKS_PASS", "failures": 0, "errors": 0,
                "tests_run": 1, "skips": 0,
                "test_events": [{"test": "test_candidate_native.example", "status": "PASS"}],
                "weights": "NOT_DOWNLOADED_OR_DESERIALIZED", "inference": "NOT_RUN", "gpu": "NOT_CALLED"}
            path = evidence/(key+".json")
            write(path, receipt)
            manifest["receipts"][path.name] = sha(path)
        write(evidence/"index.json", manifest)
        return evidence/"index.json"

    def test_evidence_tampering_model_test_accounting_and_scope_rejected(self):
        for defect in (None, "hash", "source", "identity", "native_skip", "scope", "missing_source", "count", "missing_model"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                index = self.synthetic_receipts(root)
                path = index.parent/"internvl35.json"
                receipt = read(path)
                if defect == "source": (root/"script.py").write_text("corrupted")
                if defect == "identity": receipt["model"]["revision"] = "incorrect"
                if defect == "native_skip":
                    receipt["test_events"][0]["status"] = "SKIP"
                    receipt["skips"] = 1
                if defect == "scope": receipt["inference"] = "PASS"
                if defect == "missing_source": receipt["source_sha256"] = {}
                if defect == "count": receipt["tests_run"] = 2
                # Fixtures may be replaced; actual evidence writer is exclusive.
                path.write_text(__import__("json").dumps(receipt))
                manifest = read(index)
                if defect != "hash": manifest["receipts"][path.name] = sha(path)
                if defect == "missing_model": del manifest["receipts"]["minicpm4.json"]
                index.write_text(__import__("json").dumps(manifest))
                with patch.object(audit, "source_digest", return_value="fixture"), \
                     patch("scripts.rehearse_candidate_integration.evidence_sources", return_value=["script.py"]):
                    if defect is None: self.assertEqual(audit.verify(index, root)["status"], "PASS")
                    else:
                        with self.assertRaises(ValueError): audit.verify(index, root)


if __name__ == "__main__":
    unittest.main()
