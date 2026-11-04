"""Offline synthetic campaign integration; no Kaggle/GitHub/model/data access."""
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch, Mock

from safeshift import internvl_v2_campaign as c, internvl_v2_runtime as runtime
from safeshift.pilot.artifacts import write, read, export, sha
from safeshift.pilot.contract import digest
from scripts import internvl_v2_campaign as run, submit_internvl_v2 as submit


def grant(slot=1, mode="preflight"):
    spec = runtime.source_spec()
    request = {"schema": c.CAMPAIGN + "-request", "source_sha256": digest(spec),
        "master_sha256": c.MASTER_SHA, "original_archive_sha256": c.ORIGINAL_ARCHIVE,
        "ordinal": 0, "sample_id_sha256": "a" * 64, "image_locator_sha256": "b" * 64,
        "image_sha256": "c" * 64}
    return {"campaign": c.CAMPAIGN, "reviewed_head": "d" * 40, "runtime_commit": "e" * 40,
        "manifest_sha256": digest(spec["manifest"]), "notebook_sha256": "f" * 64,
        "notebook_code_sha256": "1" * 64, "request": request, "request_sha256": digest(request),
        "slot": slot, "mode": mode, "job": c.job(slot), "version": 1,
        "issued_unix": int(time.time()) - 10, "expires_unix": int(time.time()) + 1790,
        "limits": dict(c.LIMITS), "chatgpt_review_comment": 6622148200,
        "antigravity_audit_comment": 6622148300, "predecessors": ["9" * 64] * (slot-1)}


def challenge(g, phase, parent="", nonce="a"):
    return {"campaign": c.CAMPAIGN, "slot": g["slot"], "binding": digest(g),
            "phase": phase, "parent_nonce": parent, "nonce": nonce * 64}


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        # Accidental network calls fail, even when a test misses a specific mock.
        self.stack.enter_context(patch.object(c, "public_get", side_effect=AssertionError("NO_NETWORK")))
        self.stack.enter_context(patch.object(c, "github_post", side_effect=AssertionError("NO_NETWORK")))
        self.stack.enter_context(patch.object(c, "_capability", None))

    def test_release_requires_new_owner_comment_exact_head_independent_audit(self):
        g = grant()
        def comments(number, marker):
            if marker == "INTERNVL_V2_RELEASE_V1":
                return g
            return {"role": "CHATGPT" if number == g["chatgpt_review_comment"] else "ANTIGRAVITY",
                "head": g["reviewed_head"], "request_sha256": g["request_sha256"], "verdict": "PASS"}
        with patch.object(c, "comment_record", side_effect=comments), patch.object(c, "check_head"):
            self.assertEqual(c.read_grant(6622148400), g)
            for field, value in (("slot", 4), ("version", True), ("limits", {**c.LIMITS, "calls": 2}),
                ("request_sha256", "0" * 64), ("expires_unix", 1), ("expires_unix", int(time.time()) + 9999),
                ("antigravity_audit_comment", g["chatgpt_review_comment"]), ("predecessors", ["9" * 64])):
                old = g[field]
                g[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    c.read_grant(6622148400)
                g[field] = old

    def test_comment_owner_pr_old_scope_and_missing_machine_release_rejected(self):
        with self.assertRaises(ValueError):
            c.comment_record(6622148168, "INTERNVL_V2_RELEASE_V1")
        for owner, issue, body in (("other", 177, "x"), ("tantdna2", 175, "x"), ("tantdna2", 177, "approved")):
            with patch.object(c, "public_get", return_value={"user": {"login": owner},
                "issue_url": c.API + "/issues/" + str(issue), "body": body}), self.assertRaises(ValueError):
                c.comment_record(6622148400, "INTERNVL_V2_RELEASE_V1")

    def test_review_head_branch_merge_and_state_drift(self):
        g = grant()
        pr = {"head": {"sha": g["reviewed_head"], "ref": c.BRANCH}, "state": "open", "draft": True, "merged": False}
        with patch.object(c, "public_get", return_value=pr):
            c.check_head(g)
            for key, value in (("draft", False), ("merged", True), ("state", "closed"),
                               ("head", {"sha": "0" * 40, "ref": c.BRANCH})):
                bad = {**pr, key: value}
                with patch.object(c, "public_get", return_value=bad), self.assertRaises(ValueError):
                    c.check_head(g)

    def test_request_original_master_ordinal_hash_and_extra_fields(self):
        r = grant()["request"]
        self.assertEqual(c.validate_request(r), digest(r))
        for key, value in (("ordinal", 1), ("ordinal", False), ("master_sha256", "0" * 64),
                           ("original_archive_sha256", "0" * 64), ("sample_id_sha256", "bad"), ("split", "TEST")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                c.validate_request({**r, key: value})

    def test_create_only_atomic_ref_no_branch_update_no_retry_lost_response(self):
        head = "a" * 40
        key = c.record_name("submission", 1)
        with patch.object(c, "github_post", side_effect=[{"sha": "b" * 40},
            {"ref": "refs/tags/" + key, "object": {"sha": "b" * 40}}]) as post:
            self.assertEqual(c.create_record("submission", {}, head, 1), "b" * 40)
            self.assertEqual([r.args[0] for r in post.call_args_list], ["/git/tags", "/git/refs"])
        with patch.object(c, "github_post", side_effect=[{"sha": "b" * 40}, TimeoutError("lost")]) as post:
            with self.assertRaises(TimeoutError):
                c.create_record("submission", {}, head, 1)
            self.assertEqual(post.call_count, 2)

    def test_two_vm_coordinators_race_global_call_never_twice(self):
        g = grant(2, "native")
        records = {}
        def create(name, value, head, slot=None):
            key = (name, slot)
            if key in records:
                raise ValueError("CONFLICT")
            records[key] = value
        with patch.object(c, "check_head"), patch.object(c, "create_record", side_effect=create):
            a, b = c.Coordinator(g), c.Coordinator(g)
            parent = ""
            for i, phase in enumerate(c.PHASES):
                event = challenge(g, phase, parent, str(i))
                a.accept(event)
                a.accept(event)  # Read-only log replay, no second write.
                parent = event["nonce"]
            self.assertEqual(len(records), 7)
            with self.assertRaises(ValueError):
                b.accept(challenge(g, "launch", nonce="f"))
            with self.assertRaisesRegex(ValueError, "DUPLICATE_VM"):
                a.accept(challenge(g, "call", "3" * 64, "f"))

    def test_reorder_wrong_parent_expiry_and_preflight_native_denied(self):
        for g, event in ((grant(), challenge(grant(), "load")),
                         (grant(2, "native"), challenge(grant(2, "native"), "call")),
                         (grant(), challenge(grant(), "launch", "bad"))):
            with patch.object(c, "create_record") as create, patch.object(c, "check_head"), self.assertRaises(ValueError):
                c.Coordinator(g).accept(event)
            create.assert_not_called()

    def test_permit_fresh_nonce_existing_vm_mismatch_and_timeout(self):
        g = grant()
        ctx = {"grant": g, "binding": digest(g)}
        with patch.object(c, "remote_record", return_value={}), self.assertRaisesRegex(ValueError, "ALREADY_RESERVED"):
            c.permit(ctx, "launch", "", emit=Mock())
        with patch.object(c, "remote_record", side_effect=[None, {}]), self.assertRaisesRegex(ValueError, "NONCE_MISMATCH"):
            c.permit(ctx, "launch", "", emit=Mock())
        with patch.object(c, "remote_record", return_value=None), patch.object(c.time, "monotonic", side_effect=[0, 0, 999]), \
                self.assertRaises(TimeoutError):
            c.permit(ctx, "launch", "", emit=Mock())

    def test_context_missing_multiple_or_changed_source_never_activates(self):
        spec = runtime.source_spec()
        with patch.object(c, "remote_record", return_value=None), self.assertRaisesRegex(ValueError, "REVIEW_HOLD"):
            c.context(spec, "e" * 40)
        g = grant()
        def record(name, slot=None):
            return {"grant": g, "approval_comment": 6622148400} if name == "submission" and slot == 1 else None
        with patch.object(c, "remote_record", side_effect=record), patch.object(c, "read_grant", return_value=g):
            self.assertEqual(c.context(spec, "e" * 40)["binding"], digest(g))
            with self.assertRaisesRegex(ValueError, "SOURCE_RELEASE"):
                c.context(spec, "0" * 40)

    def test_direct_loader_generate_denied_and_local_capability_single_use(self):
        with self.assertRaises(PermissionError):
            runtime.NativeBackend("missing", "missing")
        g = grant(2, "native")
        ctx = {"grant": g, "binding": digest(g)}
        permission = challenge(g, "worker")
        with tempfile.TemporaryDirectory() as d, patch.object(c, "remote_record", return_value=permission), \
                patch.object(c, "permit", side_effect=lambda ctx, phase, parent: challenge(g, phase, parent)) as permit:
            c.activate_worker(ctx, runtime.source_spec(), permission, Path(d))
            runtime.authorize("load")
            runtime.authorize("call")
            with self.assertRaises(ValueError):
                runtime.authorize("call")
            self.assertEqual(permit.call_count, 2)
            self.assertTrue((Path(d) / "call-permit.json").exists())

    def test_cli_paths_and_child_stage_gate_before_input(self):
        with patch.object(run, "worker") as worker:
            run.main(["--worker", "setup", "--packet", "p", "--output", "o", "--scratch", "s",
                      "--inputs", "i", "--deadline", "1"])
            self.assertTrue(all(isinstance(p, Path) for p in worker.call_args.args[1:5]))
        with tempfile.TemporaryDirectory() as d:
            packet = Path(d) / "packet.json"
            write(packet, {"spec": {}, "runtime_commit": "e" * 40, "slot": 1})
            with patch.object(c, "context", side_effect=ValueError("NO_GRANT")), \
                    patch.object(run, "original_metadata") as original, self.assertRaisesRegex(ValueError, "NO_GRANT"):
                run.worker("worker", packet, Path(d), Path(d), Path(d), 1)
            original.assert_not_called()

    def test_preflight_has_no_real_image_input_or_native_action(self):
        datasets, _ = submit.input_sources("preflight")
        self.assertNotIn("nguynanhtn/inspecsafe-v1-kaggle", datasets)
        g = grant(); ctx = {"grant": g, "binding": digest(g)}
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            write(out / "packet.json", {"spec": {}, "runtime_commit": "e" * 40, "slot": 1})
            write(out / "setup-permit.json", {"nonce": "a" * 64})
            with patch.object(c, "context", return_value=ctx), patch.object(c, "remote_record", return_value={"nonce": "a" * 64}), \
                patch.object(c, "permit", return_value={}), patch.object(run, "original_metadata", return_value=(g["request"], {}, "")), \
                patch.object(run, "native_request", side_effect=AssertionError("NO_IMAGES")), patch.object(run.engine, "worker") as worker:
                run.worker("worker", out / "packet.json", out, out, out, 1)
            self.assertEqual(worker.call_args.args[0], "preflight")

    def test_native_request_exact_identity_image_hash(self):
        spec = runtime.source_spec()
        with tempfile.TemporaryDirectory() as d:
            inputs = Path(d)
            image = inputs / "mount/InspecSafe-V1-Kaggle/train/synthetic.bin"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"SYNTHETIC_ONLY")
            recipe = grant()["request"]
            recipe["image_sha256"] = sha(image)
            first = {"ordinal": 0, "sample_id": "SYNTHETIC", "image_sha256": sha(image)}
            with patch.object(run, "original_metadata", return_value=(recipe, first, "synthetic.bin")), \
                    patch.object(run, "unique_mount", return_value=inputs / "mount"):
                request = run.native_request(inputs, spec, recipe)
                self.assertEqual(request["sample_id"], "SYNTHETIC")
                image.write_bytes(b"DRIFT")
                with self.assertRaisesRegex(ValueError, "IMAGE_SHA256"):
                    run.native_request(inputs, spec, recipe)

    def test_controller_supervision_failure_preserves_partial_and_positive_ledger(self):
        g = grant(); ctx = {"grant": g, "binding": digest(g)}
        for failure in (TimeoutError("synthetic"), OSError("synthetic"), RuntimeError("LOAD_ERROR")):
            with tempfile.TemporaryDirectory() as d, patch.object(c, "context", return_value=ctx), \
                patch.object(c, "permit", return_value={}), patch.object(run.environment, "resources", return_value={}), \
                patch.object(run.supervision, "run", side_effect=failure):
                result = run.launch(runtime.source_spec(), "e" * 40, output=Path(d) / "out", scratch_parent=Path(d) / "scratch")
                self.assertEqual(result["status"], "TECHNICAL_ERROR")
                archives = list((Path(d) / "out").glob("*.zip"))
                self.assertEqual(len(archives), 1)
                from safeshift.pilot.artifacts import verify_archive
                self.assertIn("campaign-end.json", verify_archive(archives[0]))
                # No logs: deliberately cannot claim positive zero-call remotely.
                with patch.object(c, "remote_record", return_value=None), self.assertRaisesRegex(ValueError, "LOG_CUSTODY"):
                    submit.verify_result(archives[0], g, "ERROR")

    def test_submit_timeout_burns_slot_and_no_second_post_even_unknown(self):
        g = grant(); records = {}
        def create(name, value, head, slot=None):
            if (name, slot) in records:
                raise ValueError("EXISTS")
            records[(name, slot)] = value
        api = Mock()
        api.kernels_push.side_effect = TimeoutError("SECRET_URL")
        api.kernels_status.return_value = NS(status="UNRECOGNIZED")
        with tempfile.TemporaryDirectory() as d, patch.object(submit, "validate_local_release", return_value=g), \
            patch.object(c, "check_head"), patch.object(c, "remote_record", side_effect=lambda name, slot=None: records.get((name, slot))), \
            patch.object(c, "create_record", side_effect=create), patch.object(submit, "predecessors", return_value=[]), \
            patch.object(submit, "inventory", return_value={}):
            notebook = Path(d) / "n.ipynb"; notebook.write_text("{}")
            with self.assertRaisesRegex(ValueError, "UNKNOWN_JOB"):
                submit.submit(api, g, 6622148400, notebook, Path(d) / "first", Path(d))
            with self.assertRaisesRegex(ValueError, "NONEMPTY_LEDGER"):
                submit.submit(api, g, 6622148400, notebook, Path(d) / "second", Path(d))
            self.assertEqual(api.kernels_push.call_count, 1)
            self.assertNotIn("SECRET_URL", (Path(d) / "first/dispatch-error.json").read_text())

    def test_missing_grant_blocks_before_kaggle_import(self):
        with patch.object(submit, "validate_local_release", side_effect=ValueError("NO_RELEASE")), \
                patch.object(submit, "submit") as send, self.assertRaisesRegex(ValueError, "NO_RELEASE"):
            submit.main(["--approval-comment", "6622148400", "--notebook", "missing", "--stage", "missing",
                         "--predecessor-directory", "missing"])
        send.assert_not_called()

    def test_transport_partial_replayed_lines_and_terminal_end(self):
        g = grant(); event = challenge(g, "launch")
        text = c.PREFIX + json.dumps(event)
        api = Mock()
        api.kernels_logs_stream.return_value = iter([{"data": text[:20]}, {"data": text[20:]}, {"data": text + "\n"}])
        api.kernels_status.return_value = NS(status="COMPLETE")
        with patch.object(submit, "live_identity"), patch.object(c, "check_head"), patch.object(c, "create_record") as create:
            result = submit.coordinate(api, g, 2)
        self.assertEqual(result["permits"], ["launch"])
        self.assertEqual(create.call_count, 1)

    def test_transport_malformed_event_and_deadline_preserve_error(self):
        api = Mock(); api.kernels_logs_stream.return_value = iter([{"data": 7}])
        with tempfile.TemporaryDirectory() as d, self.assertRaisesRegex(ValueError, "TRANSPORT_ERROR"):
            submit.coordinate(api, grant(), 2, Path(d))
        api.kernels_logs_stream.return_value = iter([])
        api.kernels_status.return_value = NS(status="RUNNING")
        with self.assertRaises(TimeoutError):
            submit.coordinate(api, grant(), 0)

    def test_sdk_no_redirect_no_retry_bounded_timeout(self):
        try:
            import requests
        except ImportError:
            self.skipTest("requests optional local SDK transport dependency")
        response = Mock()
        with patch.object(requests.Session, "send", return_value=response) as original:
            with submit.bounded_http():
                session = requests.Session()
                request = requests.Request("GET", "https://www.kaggle.com/synthetic").prepare()
                session.send(request)
                self.assertEqual(original.call_args.kwargs["timeout"], (10, 30))
                self.assertFalse(original.call_args.kwargs["allow_redirects"])
                session.adapters["https://"].max_retries.total = 1
                with self.assertRaisesRegex(ValueError, "RETRIES_FORBIDDEN"):
                    session.send(request)

    def test_sdk_version_mismatch_and_native_no_release_do_not_import_kaggle(self):
        with patch.object(submit.importlib.metadata, "version", side_effect=lambda name: submit.SDK_PINS[name]):
            self.assertEqual(submit.check_sdk(), submit.SDK_PINS)
        with patch.object(submit.importlib.metadata, "version", return_value="unexpected"), \
                self.assertRaisesRegex(ValueError, "SDK_PINS"):
            submit.check_sdk()

    def test_inventory_owner_target_quota_and_input_version_fail(self):
        g = grant()
        api = Mock()
        api.kernels_list_with_response.return_value = NS(kernels=[NS(ref=x) for x in submit.input_sources("preflight")[1]], next_page_token=None)
        api.kernels_status.return_value = NS(status="COMPLETE")
        from datetime import timedelta
        api.quota_view.return_value = NS(gpu_quota=NS(time_used=timedelta(0), time_reserved=timedelta(0), time_allowed=timedelta(hours=30), total_time_allowed=timedelta(hours=30)))
        with patch.object(submit, "get_kernel", side_effect=lambda api, ref: NS(metadata=NS(ref=ref, current_version_number=1, id=1))):
            self.assertEqual(submit.inventory(api, g)["owned_count"], 2)
            api.quota_view.return_value.gpu_quota.time_reserved = timedelta(seconds=1)
            with self.assertRaisesRegex(ValueError, "QUOTA"):
                submit.inventory(api, g)
            api.kernels_list_with_response.return_value.kernels.append(NS(ref=g["job"]))
            with self.assertRaisesRegex(ValueError, "JOB_EXISTS"):
                submit.inventory(api, g)

    def test_zero_call_requires_complete_previous_zip_logs_ledger_and_preflight(self):
        g = grant(2, "native")
        with patch.object(c, "remote_record", return_value=None), self.assertRaisesRegex(ValueError, "MISSING_TERMINAL"):
            submit.predecessors(Mock(), g, Path("missing"))
        with patch.object(c, "remote_record", return_value={}), self.assertRaisesRegex(ValueError, "ALREADY_RESERVED"):
            submit.predecessors(Mock(), g, Path("missing"))
        with patch.object(c, "remote_record", return_value=None), self.assertRaisesRegex(ValueError, "PREFLIGHT_REQUIRED"):
            submit.predecessors(Mock(), grant(1, "native"), Path("missing"))

    def test_successful_preflight_controller_archive_and_tampering(self):
        g = grant(); ctx = {"grant": g, "binding": digest(g)}
        def supervised(command, **kw):
            out = kw["receipt"].parent
            kw["log"].write_bytes(b"SYNTHETIC_LOG_ONLY\n")
            write(kw["receipt"], {"schema": "fresh-process-supervision-v1", "status": "EXITED", "automatic_retry": False})
            if command[command.index("--worker")+1] == "setup":
                write(out / "runtime.json", {"python": "synthetic-python", "env": {}})
            else:
                write(out / "original-binding.json", g["request"])
                for name in ("checkpoint.json", "processor.json", "cuda.json", "preload-resources.json", "preflight.json"):
                    write(out / name, {"scope": "SYNTHETIC"})
        with tempfile.TemporaryDirectory() as d, patch.object(c, "context", return_value=ctx), \
                patch.object(c, "permit", return_value={}), patch.object(c, "remote_record", return_value=None), \
                patch.object(run.environment, "resources", return_value={}), patch.object(run.supervision, "run", side_effect=supervised):
            result = run.launch(runtime.source_spec(), "e" * 40, output=Path(d) / "out", scratch_parent=Path(d) / "scratch")
            archive = next((Path(d) / "out").glob("*.zip"))
            verified = submit.verify_result(archive, g, "COMPLETE")
            self.assertEqual(verified["proof"], "ZERO_CALL_CONFIRMED")
            self.assertEqual(result["status"], "LIVE_GPU_PREFLIGHT_PASS")
            with patch.object(c, "remote_record", return_value={}), self.assertRaises(ValueError):
                submit.verify_result(archive, g, "COMPLETE")
            with self.assertRaisesRegex(ValueError, "NOT_TERMINAL"):
                submit.verify_result(archive, g, "RUNNING")
            archive.write_bytes(archive.read_bytes() + b"CORRUPTION")
            with self.assertRaisesRegex(ValueError, "SIDECAR"):
                submit.verify_result(archive, g, "COMPLETE")

    def test_original_recipe_rejects_tampered_master_before_prior_or_image_io(self):
        with patch.object(run, "verify_archive") as verify, self.assertRaisesRegex(ValueError, "MASTER_CHECKSUM"):
            run.original_recipe(b"SYNTHETIC_NOT_ORIGINAL_MASTER", Path("missing"), runtime.source_spec())
        verify.assert_not_called()

    def test_remote_ledger_checks_tag_type_name_and_commit(self):
        key = c.record_name("submission", 1)
        ref = {"ref": "refs/tags/" + key, "object": {"type": "tag", "sha": "a" * 40}}
        tag = {"tag": key, "object": {"type": "commit", "sha": "b" * 40},
               "message": json.dumps({"campaign": c.CAMPAIGN, "name": key, "head": "b" * 40, "value": {"test": 1}})}
        with patch.object(c, "public_get", side_effect=[ref, tag]):
            self.assertEqual(c.remote_record("submission", 1), {"test": 1})
        tag["object"]["sha"] = "c" * 40
        with patch.object(c, "public_get", side_effect=[ref, tag]), self.assertRaisesRegex(ValueError, "BINDING"):
            c.remote_record("submission", 1)

    def test_archive_export_error_never_reports_completed(self):
        g = grant(); ctx = {"grant": g, "binding": digest(g)}
        with tempfile.TemporaryDirectory() as d, patch.object(c, "context", return_value=ctx), \
                patch.object(c, "permit", side_effect=TimeoutError), patch.object(run, "export", side_effect=OSError("DISK_FULL")), \
                self.assertRaises(OSError):
            run.launch(runtime.source_spec(), "e" * 40, output=Path(d) / "out", scratch_parent=Path(d) / "scratch")


if __name__ == "__main__":
    unittest.main()
