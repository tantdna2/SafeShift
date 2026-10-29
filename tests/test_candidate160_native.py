"""Opt-in real processor/native generation with scripted CPU logits, no VLM."""
import os
from pathlib import Path
import tempfile
import unittest

from safeshift.candidates import train_runtime as rt, train_run as run
from safeshift.pilot.artifacts import export, verify_archive, read
from test_candidate160 import fixture, grant, review
import test_candidate_native as native


@unittest.skipUnless(native.KEY and native.SNAPSHOT, "opt-in pinned public candidate CPU stack required")
class Candidate160NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.NativeCandidateTests.setUpClass.__func__(cls)

    def test_native_processor_tokens_raw_160_runner_and_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            for row, metadata in zip(rows, plan["main"]):
                # Only synthetic RGBA PNG bytes, with .jpg file extension.
                path = Path(row["image"])
                with self.Image.new("RGBA", (17, 1), (40, 80, 120, 50)) as image:
                    image.save(path, format="PNG")
                checksum = rt.sha(path)
                for value in (row, metadata):
                    value.update(image_sha256=checksum, width=17, height=1)
            backend, scripted_llm = native.NativeCandidateTests.backend(self)
            self.assertEqual(rt.verify_images(root, plan["main"])["verified_images"], 160)
            result, reason = run.run_calls(root/"out", plan, rows, lambda: backend,
                                          grant(native.KEY), reviewer=review)
            self.assertIsNone(reason)
            self.assertEqual(sum(v["native_calls"] for v in result.values()), 160)
            self.assertTrue(all(v["status"] == "SUCCESS" for v in result.values()))
            self.assertEqual(sum(v["status"] == "NOT_ATTEMPTED" for v in result.values()), 0)
            self.assertTrue(read(root/"out/calls/000000/run/samples/000000/raw.json")["generated_ids"])
            self.assertFalse(scripted_llm._forward_hooks)
            export(root/"out", root/"scripted.zip")
            verify_archive(root/"scripted.zip")
            self.assertTrue((root/"out/tokenizer/runtime_tokenizer.json").is_file())

    def test_corrupt_image_rejected_before_native_generation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            with self.assertRaises(Exception):
                rt.verify_images(root, plan["main"])


if __name__ == "__main__":
    unittest.main()
