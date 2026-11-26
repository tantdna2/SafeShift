"""Synthetic continuous-attempt and read-only checkpoint regressions."""
from contextlib import ExitStack
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from safeshift import internvl_v2_campaign as c, internvl_v2_memory as memory
from safeshift import internvl_v2_runtime as runtime
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest
from scripts import submit_internvl_v2 as submit, internvl_v2 as engine
from test_internvl_v2_campaign import grant, challenge


def continuous_grant(slot=1):
    value = grant(slot, "native")
    value.pop("chatgpt_review_comment")
    value.pop("antigravity_audit_comment")
    value.update(authorization_mode="OWNER_CONTINUOUS_TECHNICAL_V1", authority_comment=6626498951,
        authority_sha256=c.CONTINUOUS_AUTHORITY_SHA, independent_audit="PENDING_POST_RESULT",
        research_scientific_qualification="NOT_ESTABLISHED", quota_cap_gpu_seconds=None)
    return value


class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        for key in ("CONTINUOUS", "CAMPAIGN", "LIMITS", "_capability"):
            self.stack.enter_context(patch.object(c, key, getattr(c, key)))
        self.stack.enter_context(patch.object(c, "public_get", side_effect=AssertionError("NO_NETWORK")))
        self.stack.enter_context(patch.object(c, "github_post", side_effect=AssertionError("NO_NETWORK")))
        c.select_continuous()

    def test_new_attempts_beyond_three_but_no_global_or_historical_writes(self):
        self.assertTrue(c.job(14).endswith("6626498951-j14"))
        self.assertEqual(submit.gpu_budget(continuous_grant(14))["cumulative_reserved_physical_gpu_seconds"], 50400)
        with self.assertRaisesRegex(ValueError, "ATTEMPT_SPECIFIC"):
            c.record_name("call")
        with patch.object(c, "CONTINUOUS", False), patch.object(c, "CAMPAIGN", "internvl-v2-6622148168"):
            with self.assertRaisesRegex(ValueError, "THREE_JOB"):
                c.job(4)
            self.assertEqual(c.record_name("call"), "internvl-v2-6622148168/call")

    def test_limits_per_attempt_and_optional_cap(self):
        g = continuous_grant(2)
        b = submit.gpu_budget(g)
        self.assertEqual((b["physical_gpus"], b["server_timeout_seconds"], b["reserved_physical_gpu_seconds"]), (2, 1800, 3600))
        g["quota_cap_gpu_seconds"] = 7199
        with self.assertRaisesRegex(ValueError, "BUDGET"):
            submit.gpu_budget(g)
        g["quota_cap_gpu_seconds"] = 7200
        self.assertEqual(submit.gpu_budget(g)["campaign_limit_physical_gpu_seconds"], 7200)

    def test_owner_auth_exact_release_and_expiry(self):
        g = continuous_grant()
        body = "synthetic owner directive"
        with patch.object(c, "CONTINUOUS_AUTHORITY_SHA", hashlib.sha256(body.encode()).hexdigest()):
            g["authority_sha256"] = c.CONTINUOUS_AUTHORITY_SHA
            authority = {"user": {"login": "tantdna2"}, "issue_url": c.API + "/issues/177", "body": body}
            with patch.object(c, "comment_record", return_value=g), patch.object(c, "public_get", return_value=authority), \
                    patch.object(c, "historical_preserved"), patch.object(c, "check_head"):
                self.assertEqual(c.read_grant(6626498952), g)
                for key, value in (("mode", "preflight"), ("authority_comment", 6625594194),
                        ("independent_audit", "PASS"), ("version", True), ("expires_unix", 1),
                        ("predecessors", ["a" * 64]), ("quota_cap_gpu_seconds", True)):
                    old = g[key]; g[key] = value
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        c.read_grant(6626498952)
                    g[key] = old
                authority["user"]["login"] = "other"
                with self.assertRaisesRegex(ValueError, "AUTHENTICATION"):
                    c.read_grant(6626498952)

    def test_historical_refs_extra_missing_changed_all_block(self):
        rows = [{"ref": "refs/tags/internvl-v2-6622148168/" + k,
                 "object": {"sha": v, "type": "tag"}} for k, v in c.HISTORICAL_REFS.items()]
        with patch.object(c, "public_get", return_value=rows):
            self.assertEqual(c.historical_preserved(), digest(c.HISTORICAL_REFS))
        for bad in (rows[:-1], rows + [rows[0]], [{**rows[0], "object": {"sha": "a" * 40, "type": "tag"}}, *rows[1:]]):
            with patch.object(c, "public_get", return_value=bad), self.assertRaisesRegex(ValueError, "HISTORICAL"):
                c.historical_preserved()

    def test_only_attempt_scoped_load_call_and_duplicate_vm_rejected(self):
        g = continuous_grant(5)
        coordinator = c.Coordinator(g)
        with patch.object(c, "check_head"), patch.object(c, "create_record") as create:
            parent = ""
            for index, phase in enumerate(c.PHASES):
                row = challenge(g, phase, parent, str(index))
                coordinator.accept(row)
                coordinator.accept(row)
                parent = row["nonce"]
            self.assertEqual(create.call_count, 5)
            self.assertTrue(all(call.args[3] == 5 for call in create.call_args_list))
            with self.assertRaisesRegex(ValueError, "DUPLICATE_VM"):
                coordinator.accept(challenge(g, "call", "3" * 64, "f"))

    def test_unknown_active_predecessor_no_api_or_submission(self):
        with patch.object(c, "active_submissions", return_value=[(1, {})]), self.assertRaisesRegex(ValueError, "ACTIVE_OR_UNKNOWN"):
            submit.predecessors(Mock(), continuous_grant(2), Path("unused"))

    def test_native_permit_requires_internal_preflight(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cap = {"ctx": {"grant": continuous_grant()}, "spec": {}, "out": root, "used": set()}
            with patch.object(c, "_capability", cap), patch.object(runtime, "check_source"), patch.object(c, "permit") as permit:
                with self.assertRaises(FileNotFoundError):
                    c.authorize("load")
                write(root / "internal-preflight.json", {"status": "FAIL"})
                with self.assertRaises(ValueError):
                    c.authorize("load")
                permit.assert_not_called()

    def test_ram_failure_prevents_deferred_image_and_native(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            out = Path(d)
            callback = Mock()
            stack.enter_context(patch.object(runtime, "authorize"))
            stack.enter_context(patch.object(runtime, "check_source"))
            stack.enter_context(patch.object(memory, "snapshot", return_value={}))
            stack.enter_context(patch.object(memory, "resource_check", side_effect=[{}, ValueError("HOST_OR_CGROUP_RAM")]))
            stack.enter_context(patch("safeshift.fulltrain.preflight.storage_probe", return_value={}))
            stack.enter_context(patch("scripts.smoke_kaggle173.bind_cuda_driver"))
            stack.enter_context(patch("scripts.smoke_kaggle173.driver_check", return_value={}))
            for key in ("software", "cuda"):
                stack.enter_context(patch.object(engine.environment, key, return_value={}))
            stack.enter_context(patch.object(engine, "check_checkpoint", return_value=(out, out)))
            stack.enter_context(patch.object(engine, "run_processor_check"))
            stack.enter_context(patch.object(engine, "reclaim_owned"))
            native = stack.enter_context(patch.object(runtime, "execute_attempt"))
            with self.assertRaisesRegex(ValueError, "HOST_OR_CGROUP_RAM"):
                engine.worker("native", {}, out, out, out, callback, time.monotonic() + 30)
            callback.assert_not_called()
            native.assert_not_called()
            self.assertFalse((out / "internal-preflight.json").exists())

    def test_positive_preflight_is_durable_before_deferred_image_and_native(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            out = Path(d)
            events = []
            stack.enter_context(patch.object(runtime, "authorize"))
            stack.enter_context(patch.object(runtime, "check_source", return_value="a" * 64))
            stack.enter_context(patch.object(memory, "snapshot", return_value={}))
            stack.enter_context(patch.object(memory, "resource_check", side_effect=lambda *a: events.append("ram") or {}))
            stack.enter_context(patch("safeshift.fulltrain.preflight.storage_probe", return_value={}))
            stack.enter_context(patch("scripts.smoke_kaggle173.bind_cuda_driver"))
            stack.enter_context(patch("scripts.smoke_kaggle173.driver_check", return_value={}))
            for key in ("software", "cuda"):
                stack.enter_context(patch.object(engine.environment, key, return_value={}))
            def checkpoint(*args):
                for name in ("checkpoint.json", "checkpoint-stream.json"):
                    write(out / name, {"scope": "SYNTHETIC"})
                return out, out
            stack.enter_context(patch.object(engine, "check_checkpoint", side_effect=checkpoint))
            def processor(*args):
                for name in ("processor.json", "processor-supervisor.json"):
                    write(out / name, {"scope": "SYNTHETIC"})
            stack.enter_context(patch.object(engine, "run_processor_check", side_effect=processor))
            stack.enter_context(patch.object(engine, "reclaim_owned"))
            def image_request():
                self.assertEqual(events, ["ram", "ram"])
                self.assertEqual(read(out / "internal-preflight.json")["status"], "LIVE_GPU_PREFLIGHT_PASS")
                events.append("image")
                write(out / "request.json", {})
                return out / "request.json"
            stack.enter_context(patch.object(runtime, "execute_attempt", side_effect=lambda *a: events.append("native")))
            engine.worker("native", {}, out, out, out, image_request, time.monotonic()+30)
            self.assertEqual(events, ["ram", "ram", "image", "native"])


@unittest.skipUnless(sys.platform == "linux", "Linux readonly checkpoint cache advice")
class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "synthetic.safetensors"
        self.payload = bytes(range(256)) * 32768 + b"tail"
        self.path.write_bytes(self.payload)

    def run_hash(self, **kwargs):
        rows = []
        result = memory.stream_checkpoint_file(self.path, expected_size=len(self.payload),
            deadline=time.monotonic() + 30, observations=rows, **kwargs)
        return result, rows

    def test_exact_full_hash_and_only_aligned_consumed_ranges(self):
        real = os.posix_fadvise
        with patch.object(os, "posix_fadvise", wraps=real) as advise:
            checksum, rows = self.run_hash()
        self.assertEqual(checksum, hashlib.sha256(self.payload).hexdigest())
        self.assertEqual(rows[0]["bytes_hashed"], len(self.payload))
        self.assertEqual(self.path.read_bytes(), self.payload)
        self.assertEqual(rows[0]["chunks"], 2)
        for call in advise.call_args_list[1:-1]:
            _, offset, length, advice = call.args
            self.assertEqual(advice, os.POSIX_FADV_DONTNEED)
            self.assertEqual(offset % 4096, 0)
            self.assertEqual(length % 4096, 0)
            self.assertLessEqual(offset + length, len(self.payload))

    def test_short_reads_still_hash_every_byte(self):
        real = os.read
        with patch.object(os, "read", side_effect=lambda fd, n: real(fd, min(n, 10003))):
            checksum, rows = self.run_hash()
        self.assertEqual(checksum, hashlib.sha256(self.payload).hexdigest())
        self.assertGreater(rows[0]["chunks"], 2)

    def test_advice_error_deadline_size_and_chunk_fail_closed(self):
        with patch.object(os, "posix_fadvise", side_effect=OSError("unsupported")), self.assertRaises(OSError):
            self.run_hash()
        with self.assertRaisesRegex(ValueError, "DEADLINE"):
            memory.stream_checkpoint_file(self.path, expected_size=len(self.payload), deadline=0, observations=[])
        for size in (True, 0, len(self.payload) - 1, 17 * 2**30):
            with self.subTest(size=size), self.assertRaises(ValueError):
                memory.stream_checkpoint_file(self.path, expected_size=size, deadline=time.monotonic()+1, observations=[])
        with self.assertRaisesRegex(ValueError, "CHUNK_BOUND"):
            self.run_hash(chunk_bytes=8193)

    def test_alias_hardlink_and_truncation_rejected(self):
        original = self.path
        alias = self.root / "alias"
        alias.symlink_to(original)
        self.path = alias
        with self.assertRaisesRegex(ValueError, "ALIAS"):
            self.run_hash()
        alias.unlink()
        os.link(original, alias)
        with self.assertRaisesRegex(ValueError, "ALIAS"):
            self.run_hash()
        alias.unlink()
        self.path = original
        real = os.read
        def truncate(fd, n):
            value = real(fd, n)
            original.write_bytes(b"bad")
            return value
        with patch.object(os, "read", side_effect=truncate), self.assertRaisesRegex(ValueError, "SHORT_READ|CHANGED"):
            self.run_hash()

    def test_sha_mismatch_is_not_a_verified_checkpoint(self):
        from safeshift.candidates import loading
        lock = {"internvl35": {"weights": {self.path.name: {"size": len(self.payload), "sha256": "0" * 64}},
                              "index": {"filename": "index.json"}}}
        (self.root / "index.json").write_text("{}")
        with patch.object(loading, "read", return_value=lock), patch.object(loading, "checkpoint_index"), \
                self.assertRaisesRegex(ValueError, "WEIGHT_CHECKSUM"):
            loading.verify_weights(self.root, "internvl35", hash_reader=lambda path: self.run_hash()[0])


if __name__ == "__main__":
    unittest.main()
