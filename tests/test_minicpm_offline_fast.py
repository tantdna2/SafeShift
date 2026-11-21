"""CPU fixtures for the V5-compatible Operator fast path."""
from copy import deepcopy
import hashlib
from pathlib import Path
import unittest
from unittest.mock import patch

import test_minicpm_offline_continuation as fixtures
from safeshift.pilot.artifacts import read
from safeshift.pilot.contract import digest, json_bytes
from scripts import minicpm_offline_fast as fast

v5 = fast.v5


class FastTests(fixtures.OfflineTests):
    def setUp(self):
        super().setUp()
        self.initialize_serial9()
        self.legacy_route = self.route
        self.stage()

    def released_route(self, *, index=None, mutate=None):
        route = self.legacy_route
        if not getattr(self, "synthetic_inventories", False):
            self.stack.enter_context(patch.object(fast.Continuation, "check_original_inventories", create=True))
            self.synthetic_inventories = True
        if not hasattr(self, "release_artifacts"):
            events = route.events()
            item = events[-1] if index is None else events[index]
            body = {"status": "RELEASED_OPERATOR_FAST_PATH", "implementation_pr": 999,
                "reviewed_head": "a" * 40, "merged_sha": "b" * 40, "grant_sha256": digest(self.grant),
                "registration_sha256": digest(route.registration), "prefix_event_number": item["number"],
                "prefix_head_sha256": digest(item), "tool_sha256": fast.sha(fast.__file__)}
            if mutate:
                mutate(body)
            subject = digest(body)
            exports = {}
            def comment(num, marker, data):
                content = marker + "\n```json\n" + json_bytes(data).decode() + "```\n"
                exports[f"/issues/comments/{num}"] = {"id": num, "body": content,
                    "issue_url": fast.a.API + "/issues/999", "user": {"login": fast.a.OWNER, "id": fast.a.OWNER_ID}}
                return {"comment_id": num, "body_sha256": hashlib.sha256(content.encode()).hexdigest()}
            body["approvals"] = {role: comment(i, fast.a.APPROVAL, {"kind": role, "status": "APPROVED",
                "reviewed_head": body["reviewed_head"], "subject_sha256": subject})
                for i, role in enumerate(("source_review", "independent_audit", "merge", "postmerge"), 1)}
            locator = comment(10, fast.RELEASE, body)
            exports["/pulls/999"] = {"merged": True, "draft": False, "base": {"ref": "main"},
                "head": {"sha": body["reviewed_head"]}, "merge_commit_sha": body["merged_sha"]}
            raw = Path(fast.__file__).read_bytes()
            tree = {"truncated": False, "tree": [{"path": "scripts/minicpm_offline_fast.py", "mode": "100644",
                "type": "blob", "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}]}
            for ref in (body["reviewed_head"], body["merged_sha"]):
                exports["/git/trees/" + ref + "?recursive=1"] = tree
            self.release_artifacts = locator, exports
        return fast.Continuation(route.root, *self.release_artifacts)

    def accept_fast(self, route, outputs):
        return route.accept(*outputs, self.proof, private_key=self.key)

    def test_state_accept_forecast_stage_export_match_v5_and_never_replay_old(self):
        active = self.route.state()["active"]
        new = self.outputs()
        expected = v5.verify_local(self.grant, active, self.route.root / active["package"], *new, self.proof)
        quick = self.released_route()
        with patch.object(fast.runtime, "recover", wraps=fast.runtime.recover) as raw, \
                patch.object(v5.ui, "restore_history", side_effect=AssertionError("historical replay")), \
                patch.object(v5, "verify_local", side_effect=AssertionError("deep replay")):
            self.accept_fast(quick, new)
            self.assertEqual(raw.call_count, 1)
            quick = self.released_route()
            observed = quick.state()
            self.assertEqual(observed["completed"][0]["completion"]["verification"], expected)
            forecast = quick.forecast()
            self.assertEqual(forecast["next_ordinal"], 2)
            self.route = quick
            staged = self.stage()
            self.assertEqual(quick.export_active(), staged)
            self.assertEqual(raw.call_count, 1)
        self.assertEqual(quick.state(), self.legacy_route.state())
        self.assertEqual(self.legacy_route.export_active(), staged)
        self.assertEqual([e["kind"] for e in quick.events()],
            ["RESERVED_OFFLINE", v5.PROVISIONAL, "RESERVED_OFFLINE"])

    def test_restart_before_event_recovers_exact_files_and_after_event_stops_repeat(self):
        outputs = self.outputs(invalid=False)
        quick = self.released_route()
        with patch.object(quick, "commit", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.accept_fast(quick, outputs)
        self.assertEqual(len(list((quick.root / "custody/9").iterdir())), 6)
        self.assertEqual(self.released_route().state()["active"]["ticket"]["payload"]["number"], 9)
        with self.assertRaisesRegex(ValueError, "ACCEPT_ALREADY_STARTED"):
            self.released_route().export_active()
        self.accept_fast(self.released_route(), outputs)
        with patch.object(quick, "state", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                quick.forecast()
        quick = self.released_route()
        self.assertEqual(quick.forecast()["next_ordinal"], 2)
        with self.assertRaisesRegex(ValueError, "NO_ACTIVE_ACCEPT"):
            self.accept_fast(quick, outputs)
        self.assertEqual(len(quick.events()), 2)

    def test_unannounced_active_ticket_keeps_hold_and_exports_same_package(self):
        outputs = self.outputs()
        quick = self.released_route()
        self.accept_fast(quick, outputs)
        self.route = quick
        owner_gate = self.gate()
        with patch.object(quick, "export_package", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                quick.stage(self.key, owner_gate, self.proof)
        quick = self.released_route()
        active = quick.state()["active"]
        self.assertEqual(active["ticket"]["payload"]["number"], 10)
        self.assertFalse((quick.root / "handoffs/10").exists())
        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            quick.forecast()
        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            quick.stage(self.key, owner_gate, self.proof)
        quick.export_active()
        self.assertEqual(quick.state()["active"], active)
        self.assertEqual(len(quick.events()), 3)

    def test_tamper_or_missing_copy_blocks_even_if_event_is_valid(self):
        quick = self.released_route()
        self.accept_fast(quick, self.outputs())
        completion = quick.state()["completed"][0]["completion"]
        for name in (completion["attempt"], completion["supervisor"] + ".sha256.json",
                     completion["proof"], "custody/9/owner-receipt.json",
                     "handoffs/9/notebook.ipynb", "accept-verifications/9.json", "event-000002.json"):
            path = quick.mirror / name
            data = path.read_bytes()
            path.unlink()
            try:
                with self.subTest(missing=name), self.assertRaises((ValueError, FileNotFoundError)):
                    self.released_route().forecast()
                path.write_bytes(data + b" ")
                # A seal uses signed JSON values. Formatting alone is blocked
                # by requiring identical bytes across both copies.
                with self.subTest(changed=name), self.assertRaises((ValueError, FileNotFoundError)):
                    self.released_route().forecast()
            finally:
                path.write_bytes(data)
        for root in (quick.root, quick.mirror):
            event = root / "event-000002.json"
            changed = read(event)
            changed["unix"] += 1
            event.write_bytes(json_bytes(changed))
        with self.assertRaisesRegex(ValueError, "SEAL_DRIFT"):
            self.released_route().forecast()

    def test_old_prefix_and_new_tail_cannot_be_rewritten_in_both_mirrors(self):
        outputs = self.outputs()
        self.route.accept(*outputs, self.proof)
        quick = self.released_route()
        self.assertEqual(quick.forecast()["next_ordinal"], 2)
        paths = [root / "event-000002.json" for root in (quick.root, quick.mirror)]
        old = paths[0].read_bytes()
        changed = read(paths[0])
        changed["payload"]["verification"]["owner_receipt"]["kernel_id"] += 200
        for path in paths:
            path.write_bytes(json_bytes(changed))
        with self.assertRaisesRegex(ValueError, "RELEASED_PREFIX_CHANGED"):
            quick.forecast()
        for path in paths:
            path.write_bytes(old)
        del self.release_artifacts
        quick = self.released_route(index=0)
        with self.assertRaises(FileNotFoundError):  # Legacy result after the approved prefix is unsigned.
            quick.forecast()

    def test_authority_missing_review_or_wrong_tool_does_not_open_route(self):
        with self.assertRaisesRegex(ValueError, "TOOL_SHA256"):
            self.released_route(mutate=lambda body: body.update(tool_sha256="0" * 64))
        del self.release_artifacts
        self.released_route()
        locator, exports = self.release_artifacts
        bad = deepcopy(exports)
        bad.pop("/issues/comments/2")
        with self.assertRaisesRegex(ValueError, "MISSING_AUTHENTIC"):
            fast.Continuation(self.route.root, locator, bad)

    def test_torn_completion_append_preserves_custody_and_blocks_both_writers(self):
        quick = self.released_route()
        outputs = self.outputs()
        write = v5.write

        def torn(path, value):
            if path == quick.mirror / "event-000002.json":
                raise OSError("synthetic unavailable mirror")
            return write(path, value)

        with patch.object(v5, "write", side_effect=torn), self.assertRaises(OSError):
            self.accept_fast(quick, outputs)
        for root in (quick.root, quick.mirror):
            self.assertEqual(len(list((root / "custody/9").iterdir())), 6)
            self.assertTrue((root / "accept-verifications/9.json").is_file())
        for route in (self.legacy_route, self.released_route()):
            with self.assertRaisesRegex(ValueError, "TORN_MIRROR"):
                route.forecast()

    def test_corrupt_incoming_sidecar_stops_without_committing_provisional(self):
        attempt, supervisor, receipt = self.outputs()
        sidecar = attempt.with_suffix(".zip.sha256.json")
        sidecar.write_bytes(json_bytes({"sha256": "0" * 64, "members": 1}))
        quick = self.released_route()
        with self.assertRaisesRegex(ValueError, "OFFLINE_ACCEPT_STOPPED"):
            self.accept_fast(quick, (attempt, supervisor, receipt))
        state = self.released_route().state()
        self.assertTrue(state["stopped"])
        self.assertEqual(state["next_ordinal"], 0)
        self.assertEqual(state["reserved"]["jobs"], 9)
        self.assertEqual([row["kind"] for row in quick.events()], ["RESERVED_OFFLINE", "STOPPED"])

    def test_owner_kernel_reuse_stops_before_raw_replay(self):
        attempt, supervisor, receipt = self.outputs()
        receipt["kernel_id"] = self.route.registration["base"]["serial7_closure"]["provider"]["kernel_id"]
        quick = self.released_route()
        with patch.object(fast.runtime, "recover") as replay, self.assertRaisesRegex(ValueError, "OFFLINE_ACCEPT_STOPPED"):
            self.accept_fast(quick, (attempt, supervisor, receipt))
        replay.assert_not_called()
        self.assertTrue(quick.state()["stopped"])


# Reuse fixture methods without collecting unrelated inherited tests twice.
for name in dir(fixtures.OfflineTests):
    if name.startswith("test_") and name not in FastTests.__dict__:
        setattr(FastTests, name, None)


if __name__ == "__main__":
    unittest.main()
