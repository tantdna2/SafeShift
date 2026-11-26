"""CPU fixtures for the V5-compatible Operator fast path."""
from copy import deepcopy
import hashlib
import shutil
import time
from pathlib import Path
import zipfile
import unittest
from unittest.mock import patch

import test_minicpm_offline_continuation as fixtures
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest, json_bytes
from scripts import minicpm_offline_fast as fast

v5 = fast.v5


class FastTests(fixtures.OfflineTests):
    def setUp(self):
        super().setUp()
        self.initialize_serial9()
        self.legacy_route = self.route
        self.stage()

    def released_route(self, *, index=None, mutate=None, route=None, **options):
        route = route or self.legacy_route
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
            names = {"scripts/minicpm_offline_fast.py"}
            if "companion_dependencies" in body:
                names.update(fast.contract.sources())
                names.update("scripts/" + name for name in v5.policy.TOOLS)
            tree = {"truncated": False, "tree": []}
            for name in sorted(names):
                raw = (fast.contract.ROOT / name).read_bytes()
                tree["tree"].append({"path": name, "mode": "100644", "type": "blob",
                    "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()})
            for ref in (body["reviewed_head"], body["merged_sha"]):
                exports["/git/trees/" + ref + "?recursive=1"] = tree
            self.release_artifacts = locator, exports
        return fast.Continuation(route.root, *self.release_artifacts, **options)

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

    def test_unannounced_serial12_keeps_hold_and_exports_same_package(self):
        quick = self.released_route()
        self.route = quick
        propose = fast.policy.proposal
        with patch.object(fast.policy, "proposal", side_effect=lambda *args: propose(*args) | {"calls": 2}):
            for number in (9, 10, 11):
                self.assertEqual(quick.state()["active"]["ticket"]["payload"]["number"], number)
                self.accept_fast(quick, self.outputs(invalid=False))
                if number < 11:
                    self.stage()
        owner_gate = self.gate()
        with patch.object(quick, "export_package", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                quick.stage(self.key, owner_gate, self.proof)
        quick = self.released_route()
        active = quick.state()["active"]
        self.assertEqual(active["ticket"]["payload"]["number"], 12)
        self.assertFalse((quick.root / "handoffs/12").exists())
        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            quick.forecast()
        with self.assertRaisesRegex(ValueError, "ACTIVE"):
            quick.stage(self.key, owner_gate, self.proof)
        quick.export_active()
        self.assertEqual(quick.state()["active"], active)
        self.assertEqual(len(quick.events()), 7)

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

    def forecast_gate(self, route):
        return route.forecast()["owner_gate_template"] | {"observed_unix": int(time.time()),
            "quota": {"used": 0, "reserved": 0, "total": 1000000}, "owner_checked": True,
            "no_active_job": True, "job_absent": True, "proof_sha256": fast.sha(self.proof)}

    def expire_window(self, active):
        return patch.object(time, "time", return_value=active["ticket"]["payload"]["start_before_unix"] + 1)

    def close_fast(self, quick, evidence, *, kernel_id=191):
        return quick.close_pre_native(*evidence, private_key=self.key, kernel_id=kernel_id)

    def test_supervisor_only_hard_deadline_fast_closure_and_restart_then_reserve_once(self):
        self.accept_fast(self.released_route(), self.outputs())
        quick = self.released_route()
        quick.stage(self.key, self.forecast_gate(quick), self.proof)
        before = quick.state()
        active = before["active"]
        evidence = self.failure_evidence("cpu", hard_deadline=True, item=active)
        with self.expire_window(active), patch.object(fast.runtime, "recover") as replay:
            with patch.object(quick, "commit", side_effect=RuntimeError("restart")):
                with self.assertRaisesRegex(RuntimeError, "restart"):
                    self.close_fast(quick, evidence)
            self.assertEqual(self.released_route().state()["active"], active)
            closed = self.close_fast(self.released_route(), evidence)
            self.assertEqual(closed["reserved"], before["reserved"])
            with patch.object(zipfile, "ZipFile", side_effect=AssertionError("NO_CLOSED_ZIP_REOPEN")):
                quick = self.released_route()
                self.assertEqual(quick.state()["records"], before["records"])
                self.assertEqual(quick.forecast()["next_ordinal"], before["next_ordinal"])
                self.assertEqual(self.close_fast(quick, evidence)["status"], "ALREADY_CLOSED")
                gate = self.forecast_gate(quick)
                quick.stage(self.key, gate, self.proof)
                current = quick.state()["active"]
                self.assertEqual(self.close_fast(quick, evidence)["active_serial"], 11)
                with self.assertRaisesRegex(ValueError, "ACTIVE_STOP"):
                    quick.stage(self.key, gate, self.proof)
                self.assertEqual(quick.export_active(), quick.export_active())
                self.assertEqual(quick.state()["active"], current)
                pending = current["value"]["request"]["plan"]
                self.assertEqual(pending["scheduled_ordinals"] + pending["deferred_ordinals"],
                                 list(range(before["next_ordinal"], 3763)))
                self.assertEqual(current["ticket"]["payload"]["reserved_before"], before["reserved"])
            replay.assert_not_called()
        with self.expire_window(active):
            legacy = v5.Continuation(quick.root).state()
            self.assertEqual(legacy["records"], before["records"])
            self.assertEqual(legacy["closed"][0]["summary"]["number"], 10)

    def test_pre_native_negative_evidence_and_mirror_stop_without_new_event(self):
        quick = self.released_route()
        active = quick.state()["active"]
        folder, closure = self.failure_evidence("cpu", hard_deadline=True, item=active)
        archive = folder / closure["local"]["supervisor"]
        sidecar = archive.with_name(archive.name + ".sha256.json")
        claim = folder / "minicpm-fulltrain-claims" / self.grant["campaign_id"] / "9" / "load.json"
        with self.expire_window(active):
            with self.assertRaisesRegex(ValueError, "EXPECTED_KERNEL_ID"):
                self.close_fast(quick, (folder, closure), kernel_id=192)
            for unexpected in ("load.json", "call-000000.json", "native.json"):
                extra = claim.with_name(unexpected)
                write(extra, {})
                with self.assertRaisesRegex(ValueError, "LOOSE_CLAIMS"):
                    self.close_fast(quick, (folder, closure))
                extra.unlink()
            initial = sidecar.read_bytes()
            sidecar.write_bytes(initial.replace(closure["local"]["supervisor_sha256"].encode(), b"0" * 64))
            with self.assertRaisesRegex(ValueError, "SIDECAR"):
                self.close_fast(quick, (folder, closure))
            sidecar.write_bytes(initial)
            original = archive.read_bytes()
            archive.write_bytes(original[:40])
            with self.assertRaises(zipfile.BadZipFile):
                self.close_fast(quick, (folder, closure))
            archive.write_bytes(original)
            wrong = deepcopy(closure)
            wrong["provider"]["kernel_id"] = quick.registration["base"]["serial7_closure"]["provider"]["kernel_id"]
            with self.assertRaisesRegex(ValueError, "DUPLICATE_OWNER_KERNEL"):
                self.close_fast(quick, (folder, wrong), kernel_id=wrong["provider"]["kernel_id"])
            self.assertEqual(quick.state()["active"], active)
            count = len(quick.events())
            original_write = v5.write

            def torn(path, value):
                if path.parent == quick.mirror and value["kind"] == fast.prenative.DISPOSITION:
                    raise RuntimeError("mirror lost")
                return original_write(path, value)

            with patch.object(v5, "write", side_effect=torn), self.assertRaisesRegex(RuntimeError, "mirror lost"):
                self.close_fast(quick, (folder, closure))
            with self.assertRaisesRegex(ValueError, "TORN_MIRROR"):
                self.close_fast(self.released_route(), (folder, closure))
            self.assertEqual(len(list(quick.root.glob("event-*.json"))), count + 1)
            self.assertEqual(len(list(quick.mirror.glob("event-*.json"))), count)

    def prepare_source_transition(self, quick):
        before = quick.state()
        # Freeze the fixture source and V5 tool bytes under a separate checkout.
        current_manifest = fast.contract.source_manifest()
        historical = self.root / "frozen-v5"
        for name in [*current_manifest, *("scripts/" + name for name in v5.policy.TOOLS)]:
            destination = historical / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fast.contract.ROOT / name, destination)
        real_manifest = fast.contract.source_manifest
        self.stack.enter_context(patch.object(fast.contract, "V5_SOURCE", digest(current_manifest)))
        self.stack.enter_context(patch.object(fast.contract, "source_manifest",
            side_effect=lambda repo=fast.contract.ROOT: (current_manifest | {"safeshift/fulltrain/admission.py": "c" * 64}
                if Path(repo).resolve() == fast.contract.ROOT else real_manifest(repo))))
        upgraded_locator = {"comment_id": 420, "body_sha256": "b" * 64}
        original = v5.Continuation(quick.root, historical_repo=historical)
        proposal = original.runtime_proposal()
        self.assertEqual(proposal["continuation"]["first_serial"], before["reserved"]["jobs"] + 1)
        self.assertTrue(all(value is None for value in proposal["approvals"].values()))
        new = proposal | {"implementation_pr": 999, "runtime_commit": "d" * 40,
            "merged_sha": "b" * 40, "reviewed_head": "a" * 40, "issued_unix": int(time.time()) - 1,
            "expires_unix": int(time.time()) - 1 + v5.policy.RELEASE_SECONDS}
        self.stack.enter_context(patch.object(v5.a, "load",
            side_effect=lambda locator, **_: new if locator == upgraded_locator else self.grant))

        def notebook(ref, *, capsule_sha256, release_locator, release_version):
            nb = self.notebook(ref, capsule_sha256=capsule_sha256, release_locator=release_locator,
                               release_version=release_version)
            nb["metadata"]["safeshift"]["source_sha256"] = new["scope"]["source_sha256"]
            return nb

        self.stack.enter_context(patch("scripts.generate_minicpm_fulltrain_notebook.notebook", side_effect=notebook))
        pins = {str(item["summary"]["number"]): fast.closure_snapshot(fast.v5.ROOT / item["download"])
            for item in before["closed"]}
        del self.release_artifacts
        def release_scope(body):
            body.update(closure_snapshots=pins, companion_dependencies={
                "source_sha256": new["scope"]["source_sha256"], "tools_sha256": new["offline"]["tools_sha256"]})

        upgraded = self.released_route(route=original, mutate=release_scope, historical_repo=historical,
            runtime_release=(upgraded_locator, {}))
        return upgraded, original, new

    def test_signed_source_transition_keeps_old_results_and_reads_both_generations(self):
        self.accept_fast(self.released_route(), self.outputs())
        quick = self.released_route()
        real_time = time.time
        offset = 0
        self.stack.enter_context(patch.object(time, "time", side_effect=lambda: real_time() + offset))
        for serial in range(10, 20):
            quick.stage(self.key, self.forecast_gate(quick), self.proof)
            active = quick.state()["active"]
            evidence = self.failure_evidence("cpu", hard_deadline=True, kernel_id=serial, item=active)
            offset += self.grant["provider_max_age_seconds"] + 1
            self.close_fast(quick, evidence, kernel_id=serial)
        state = quick.state()
        old_events = {path.name: path.read_bytes() for path in quick.root.glob("event-*.json")}
        gate = self.forecast_gate(quick)
        upgraded, old_reader, new = self.prepare_source_transition(quick)
        self.assertEqual(old_reader.state(), state)
        for mutation in ({"caps": new["caps"] | {"total_jobs": 3000}},
                         {"public_key": {"n_hex": "aa", "e": 65537}}):
            with self.assertRaisesRegex(ValueError, "TRANSITION_SCOPE"):
                upgraded.check_runtime_transition(new | mutation)
        bad_gate = gate | {"job_absent": False}
        with self.assertRaisesRegex(ValueError, "OWNER_QUOTA_INPUT_GATE"):
            upgraded.stage(self.key, bad_gate, self.proof)
        short = v5.policy.recovery_pre_native_seconds(new) + new["sizing"]["export_seconds"] + new["sizing"]["first_call_seconds"]
        with self.assertRaisesRegex(ValueError, "STAGE_RESERVE_CANNOT_FIT"):
            upgraded.stage(self.key, gate | {"quota": {"total": 2 * short, "used": 0, "reserved": 0}}, self.proof)
        self.assertEqual(upgraded.events()[-1]["kind"], fast.prenative.DISPOSITION)
        upgraded.stage(self.key, gate, self.proof)
        active = upgraded.state()["active"]
        self.assertEqual(active["ticket"]["payload"]["number"], 20)
        self.assertEqual(active["ticket"]["payload"]["grant_sha256"], digest(new))
        self.assertEqual(active["ticket"]["payload"]["reserved_before"], state["reserved"])
        self.assertEqual(self.close_fast(upgraded, evidence, kernel_id=19)["active_serial"], 20)
        with self.assertRaisesRegex(ValueError, "ACTIVE_STOP"):
            upgraded.stage(self.key, gate, self.proof)
        self.assertEqual(old_events, {name: (quick.root / name).read_bytes() for name in old_events})
        self.assertEqual(upgraded.full_verifier().state(), upgraded.state())
        self.assertEqual(upgraded.export_active(), upgraded.export_active())
        with self.assertRaisesRegex(ValueError, "TICKET_BINDING"):
            old_reader.state()
        old_grant, locator, route = self.grant, self.locator, self.route
        try:
            self.grant, self.locator, self.route = new, upgraded.runtime_locator, upgraded
            self.accept_fast(upgraded, self.outputs())
        finally:
            self.grant, self.locator, self.route = old_grant, locator, route
        self.assertEqual(upgraded.full_verifier().state(), upgraded.state())
        self.assertEqual(upgraded.state()["records"][:len(state["records"])], state["records"])
        self.assertEqual(len(upgraded.state()["closed"]), 10)

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
