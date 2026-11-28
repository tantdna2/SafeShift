"""Fault tests for CT1's opt-in direct reader. Fixtures contain no model data."""

import hashlib
from importlib.util import find_spec
import json
import mmap
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.fulltrain import ct1_direct, qwen
from scripts import verify_ct1_direct_cpu


def encoded(rows, payload):
    data = json.dumps({"__metadata__": {"format": "pt"}, **rows}, separators=(",", ":")).encode()
    return len(data).to_bytes(8, "little") + data + payload


class DirectCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "revision"
        self.root.mkdir()
        self.shard = self.root / "model-00001-of-00001.safetensors"
        self.values = {"a": b"\x00\x80" * 7000, "b": b"\x80\x3f" * 701}
        edge = 0
        self.rows = {}
        for key, data in self.values.items():
            self.rows[key] = {"dtype": "BF16", "shape": [len(data) // 2], "data_offsets": [edge, edge + len(data)]}
            edge += len(data)
        self.src = encoded(self.rows, b"".join(self.values.values()))
        self.shard.write_bytes(self.src)
        self.index = self.root / "model.safetensors.index.json"
        self.write_index({key: self.shard.name for key in self.rows})
        self.lock = patch.object(qwen, "reference", side_effect=lambda repo: self.manifest)
        self.lock.start()
        self.addCleanup(self.lock.stop)

    def write_index(self, mapping):
        self.index.write_text(json.dumps({"weight_map": mapping}), encoding="utf-8")
        self.manifest = {"model": {"revision": self.root.name}, "snapshot_files": [
            {"path": path.name, "size_bytes": path.stat().st_size, "hash_algorithm": "sha256",
             "expected_hash": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in (self.shard, self.index)]}

    def checkpoint(self, timeout=10):
        return ct1_direct.VerifiedCheckpoint(self.root, self.root, deadline=time.monotonic() + timeout)

    def preadv(self, fd, vectors, offset):
        original = os.lseek(fd, 0, os.SEEK_CUR)
        try:
            os.lseek(fd, offset, os.SEEK_SET)
            data = os.read(fd, len(vectors[0]))
            vectors[0][:len(data)] = data
            return len(data)
        finally:
            os.lseek(fd, original, os.SEEK_SET)

    def test_alignment_partial_eintr_and_tail(self):
        actions = ["interrupted", "short"]
        calls = []

        def partial(fd, vectors, offset):
            calls.append((offset, len(vectors[0])))
            if actions:
                action = actions.pop(0)
                if action == "interrupted":
                    raise InterruptedError
                with vectors[0][:mmap.PAGESIZE] as first_page:
                    return self.preadv(fd, [first_page], offset)
            return self.preadv(fd, vectors, offset)

        with (patch.object(os, "O_DIRECT", 0, create=True), patch.object(os, "preadv", partial, create=True),
              self.checkpoint() as session):
            self.assertTrue(session.receipt["weight_bytes_verified"])
            self.assertTrue(all(offset % mmap.PAGESIZE == length % mmap.PAGESIZE == 0
                                for offset, length in calls))
            stats = session.telemetry()["io"]["verify"][self.shard.name]
            self.assertEqual(stats["returned"], len(self.src))
            self.assertEqual(stats["interrupted"], 1)
            self.assertEqual(stats["short"], 2)  # one forced partial and an actual EOF

    def test_early_eof_unaligned_partial_and_io_error_fail(self):
        for fault, expected in (
            (lambda *_: 0, ValueError), (lambda *_: 1, ValueError),
            (lambda *_: self.raise_io(), OSError),
        ):
            with (patch.object(os, "O_DIRECT", 0, create=True),
                  patch.object(os, "preadv", fault, create=True), self.assertRaises(expected)):
                with self.checkpoint():
                    self.fail("admitted bad I/O")

    @staticmethod
    def raise_io():
        raise OSError("injected direct I/O failure")

    def test_deadline_before_admission(self):
        with (patch.object(os, "O_DIRECT", 0, create=True), patch.object(os, "preadv", self.preadv, create=True),
              self.assertRaisesRegex(ValueError, "DEADLINE")):
            with self.checkpoint(timeout=-1):
                self.fail("admitted expired verification")

    def test_candidate_uses_the_sealed_index_without_a_second_open(self):
        original = qwen.read

        def check(path):
            self.assertNotEqual(path, self.index)
            return original(path)

        with (patch.object(os, "O_DIRECT", 0, create=True), patch.object(os, "preadv", self.preadv, create=True),
              patch.object(qwen, "read", side_effect=check), self.checkpoint() as session):
            result = session.index()
            result["weight_map"].clear()
            self.assertEqual(set(session.index()["weight_map"]), set(self.rows))

    def test_reopened_shard_mismatch_index_and_wrong_path(self):
        with (patch.object(os, "O_DIRECT", 0, create=True), patch.object(os, "preadv", self.preadv, create=True)):
            self.write_index({"a": self.shard.name, "missing": self.shard.name})
            with self.assertRaisesRegex(ValueError, "INDEX_KEYS"):
                with self.checkpoint():
                    self.fail("admitted wrong index")
            self.write_index({key: self.shard.name for key in self.rows})
            with self.assertRaisesRegex(ValueError, "READONLY_FILE_CHANGED"), self.checkpoint() as session:
                with self.assertRaisesRegex(ValueError, "VERIFIED_SET"):
                    session.open(self.root.parent / self.shard.name)
                stat = self.shard.stat()
                os.utime(self.shard, ns=(stat.st_atime_ns, stat.st_mtime_ns - 2_000_000_000))
                with self.assertRaisesRegex(ValueError, "SHARD_CHANGED"):
                    session.open(self.shard)

    def test_storage_is_owned_after_handles_and_session_close(self):
        class Tensor:
            def __init__(self, payload):
                self.payload = memoryview(payload)

            def reshape(self, shape):
                self.shape = shape
                return self

        torch = SimpleNamespace(bfloat16=object(), frombuffer=lambda payload, dtype: Tensor(payload))
        with (patch.object(os, "O_DIRECT", 0, create=True), patch.object(os, "preadv", self.preadv, create=True),
              patch.dict(sys.modules, {"torch": torch}), self.checkpoint() as session):
            with session.open(self.shard) as first:
                self.assertEqual(first.keys(), ["a", "b"])
                reference = first.get_slice("a")
                a = reference[...]
            with self.assertRaisesRegex(ValueError, "HANDLE_CLOSED"):
                reference.get_shape()
            second = session.open(self.shard)
            b = second.get_tensor("b")
            self.assertEqual(bytes(a.payload), self.values["a"])
            self.assertEqual(bytes(b.payload), self.values["b"])
            session.require_complete_trace()
            with self.assertRaisesRegex(ValueError, "MATERIALIZATION_LIMIT"):
                second.get_tensor("a")
        self.assertEqual(bytes(a.payload), self.values["a"])
        self.assertEqual(bytes(b.payload), self.values["b"])
        with self.assertRaisesRegex(ValueError, "HANDLE_CLOSED"):
            second.keys()

    def test_header_rejects_gap_oversized_or_wrong_dtype(self):
        row = {"a": {"dtype": "BF16", "shape": [1], "data_offsets": [2, 4]}}
        data = encoded(row, b"abcd")
        with self.assertRaisesRegex(ValueError, "COVERAGE"):
            ct1_direct._header(data, len(data))
        data = (2 * ct1_direct.MAX_HEADER).to_bytes(8, "little")
        with self.assertRaisesRegex(ValueError, "HEADER_SIZE"):
            ct1_direct._header(data, len(data))
        row["a"]["dtype"] = "F16"
        data = encoded(row, b"abcd")
        with self.assertRaisesRegex(ValueError, "TENSOR_TYPE"):
            ct1_direct._header(data, len(data))

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux direct I/O")
    def test_kernel_direct_verify_without_loading_tensor(self):
        import fcntl

        with self.checkpoint() as session:
            fd = session._shards[self.shard].fd
            self.assertTrue(fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_DIRECT)
            self.assertEqual(session.telemetry()["io"]["verify"][self.shard.name]["returned"], len(self.src))


class DirectVerifierPathsTests(unittest.TestCase):
    def test_output_canonicalization_guards_both_cli_entries(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "data" / "processed"
            staging = processed / "staging"
            staged = processed / "revision"
            staging.mkdir(parents=True)
            staged.mkdir()
            for hidden in ([], ["--worker", "candidate"]):
                argv = ["verify", "--snapshot", str(staged), "--output", str(staging / ".." / "revision" / "new")]
                with (patch.object(verify_ct1_direct_cpu, "REPO", root), patch.object(sys, "argv", argv + hidden),
                      self.assertRaisesRegex(ValueError, "overlaps snapshot")):
                    verify_ct1_direct_cpu.main()
                self.assertFalse((staged / "new").exists())


@unittest.skipUnless(sys.platform.startswith("linux") and all(find_spec(name) for name in
    ("torch", "transformers", "safetensors", "accelerate")), "pinned Linux loader dependencies required")
class DirectTransformersTests(unittest.TestCase):
    def test_from_pretrained_cpu_lifecycle(self):
        import safetensors
        import torch
        import transformers
        from transformers import Qwen3VLConfig, Qwen3VLForConditionalGeneration, modeling_utils

        if transformers.__version__ != "4.57.1" or safetensors.__version__ != "0.6.2":
            self.skipTest("pinned loader required")
        for tied in (False, True):
            with self.subTest(tied=tied), TemporaryDirectory() as directory:
                path = Path(directory)
                config = Qwen3VLConfig(
                    text_config={"vocab_size": 64, "hidden_size": 32, "intermediate_size": 64,
                                 "num_hidden_layers": 1, "num_attention_heads": 4, "num_key_value_heads": 2,
                                 "head_dim": 8, "tie_word_embeddings": tied,
                                 "rope_scaling": {"rope_type": "default", "mrope_section": [2, 1, 1]}},
                    vision_config={"depth": 1, "hidden_size": 16, "intermediate_size": 32,
                                   "out_hidden_size": 32, "num_heads": 2, "patch_size": 2,
                                   "deepstack_visual_indexes": []},
                    tie_word_embeddings=tied,
                )
                original = Qwen3VLForConditionalGeneration(config).to(torch.bfloat16)
                original.save_pretrained(path, max_shard_size=20000)
                files = [{"path": file.name, "size_bytes": file.stat().st_size, "hash_algorithm": "sha256",
                          "expected_hash": hashlib.sha256(file.read_bytes()).hexdigest()}
                         for file in path.iterdir()]
                lock = {"model": {"revision": path.name}, "snapshot_files": files}
                kwargs = {"dtype": torch.float16, "attn_implementation": "sdpa", "device_map": {"": "cpu"},
                          "local_files_only": True, "output_loading_info": True}
                expected, expected_info = Qwen3VLForConditionalGeneration.from_pretrained(path, **kwargs)
                with (patch.object(qwen, "reference", return_value=lock),
                      ct1_direct.VerifiedCheckpoint(path, path, deadline=time.monotonic() + 60) as reader):
                    with reader.install():
                        actual, actual_info = Qwen3VLForConditionalGeneration.from_pretrained(path, **kwargs)
                self.assertIs(modeling_utils.safe_open, safetensors.safe_open)
                self.assertEqual(actual_info, expected_info)
                self.assertTrue(all(not items for items in actual_info.values()))
                self.assertEqual(actual.hf_device_map, expected.hf_device_map)
                self.assertEqual(actual.generation_config.to_dict(), expected.generation_config.to_dict())
                self.assertEqual(actual.config._attn_implementation, "sdpa")
                self.assertEqual(actual.get_input_embeddings().weight is actual.get_output_embeddings().weight,
                                 tied)
                for actual_values, expected_values in ((actual.state_dict(), expected.state_dict()),
                        (dict(actual.named_buffers()), dict(expected.named_buffers()))):
                    self.assertEqual(actual_values.keys(), expected_values.keys())
                    for name, value in actual_values.items():
                        reference = expected_values[name]
                        self.assertEqual((value.shape, value.dtype, value.device),
                                         (reference.shape, reference.dtype, reference.device), name)
                        self.assertTrue(torch.equal(value, reference), name)


if __name__ == "__main__":
    unittest.main()
