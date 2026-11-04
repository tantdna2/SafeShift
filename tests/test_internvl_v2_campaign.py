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


def positive_files(g):
    """Small synthetic receipts with the actual production field contracts."""
    from safeshift.candidates.train_runtime import pins
    from scripts.internvl_v2 import policy
    b = policy()
    resources = {"memory": {"available_bytes": 32 * 2**30}, "devices": [1, 1],
        "free_bytes": [40 * 2**30] * 2, "requested_reserves_bytes": [b[k] * 2**20 for k in ("free_scratch_mib", "free_output_mib")]}
    descriptor = read(runtime.ROOT / "configs/grammar/internvl35_v2_runtime.json")
    values = {"original-binding.json": g["request"],
        "checkpoint.json": {"status": "ACTUAL_BYTES_VERIFIED", "weights_loaded": False,
            "model": descriptor["checkpoint"], "revision": descriptor["revision"]},
        "processor.json": {"status": "CPU_SOFTWARE_PASS", "scope": "SYNTHETIC_PROCESSOR_NO_MODEL_FORWARD",
            "loads": 0, "calls": 0, "mask_steps": 40, "logit_width": 151936, "tokenizer_size": 151679},
        "software.json": {"versions": pins("internvl35"), "cuda_build": "12.4", "compiled_cpu_nms": "PASS"},
        "hardware.json": {"physical_gpus": [{"index": i, "name": "Tesla T4", "driver": b["driver_versions"][0],
            "free_mib": 15000} for i in range(2)]},
        "cuda.json": {"fp16": "MEASURED", "weights_loaded": False, "gpus": [{"index": 0, "free_bytes": 15 * 2**30}]},
        "allocation.json": {"cleanup_verified": True, "allocations": [{"requested_bytes": 2**20,
            "written_bytes": 2**20, "allocated_bytes": 2**20, "fsync": True} for _ in range(2)]},
        "preflight.json": {"status": "LIVE_GPU_PREFLIGHT_PASS", "weights_loaded": False, "inference_verified": False,
            "scientific_qualified": False, "loads": 0, "calls": 0, "owner_slots_consumed": 0, "native_execution": "BLOCKED"}}
    for name in ("initial-resources.json", "resources.json", "preload-resources.json"):
        values[name] = copy.deepcopy(resources)
    parent = ""
    for i, phase in enumerate(("launch", "setup", "worker")):
        values[phase + "-permit.json"] = challenge(g, phase, parent, str(i))
        parent = str(i) * 64
    for stage in ("setup", "worker"):
        values[stage + "-supervisor.json"] = {"schema": "fresh-process-supervision-v1", "status": "EXITED",
            "returncode": 0, "group_kill_sent": True, "automatic_retry": False, "seconds": 1.0, "log_bytes": 19}
    return values


def remote(g, values=None):
    values = positive_files(g) if values is None else values
    def record(name, slot=None):
        if name == "submission" and slot == g["slot"]:
            return {"grant": g, "gpu_budget": submit.gpu_budget(g)}
        if name in ("launch", "setup", "worker") and slot == g["slot"]:
            return values[name + "-permit.json"]
        return None
    return record


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
                with patch.object(c, "remote_record", side_effect=remote(g)), self.assertRaisesRegex(ValueError, "LOG_CUSTODY"):
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
            self.assertEqual(api.kernels_push.call_args.kwargs["timeout"], "600")
            self.assertEqual(records[("submission", 1)]["gpu_budget"]["reserved_physical_gpu_seconds"], 1200)
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
        values = positive_files(g)
        def supervised(command, **kw):
            out = kw["receipt"].parent
            kw["log"].write_bytes(b"SYNTHETIC_LOG_ONLY\n")
            write(kw["receipt"], values[kw["receipt"].name])
            if command[command.index("--worker")+1] == "setup":
                write(out / "runtime.json", {"python": "synthetic-python", "env": {}})
                write(out / "setup-permit.json", values["setup-permit.json"])
            else:
                for name, value in values.items():
                    if not (out / name).exists():
                        write(out / name, value)
        with tempfile.TemporaryDirectory() as d, patch.object(c, "context", return_value=ctx), \
                patch.object(c, "permit", return_value=values["launch-permit.json"]), patch.object(c, "remote_record", side_effect=remote(g, values)), \
                patch.object(run.environment, "resources", return_value=values["initial-resources.json"]), patch.object(run.supervision, "run", side_effect=supervised):
            result = run.launch(runtime.source_spec(), "e" * 40, output=Path(d) / "out", scratch_parent=Path(d) / "scratch")
            archive = next((Path(d) / "out").glob("*.zip"))
            verified = submit.verify_result(archive, g, "COMPLETE")
            self.assertEqual(verified["proof"], "ZERO_CALL_CONFIRMED")
            self.assertEqual(result["status"], "LIVE_GPU_PREFLIGHT_PASS")
            with patch.object(c, "remote_record", side_effect=lambda name, slot=None: {} if name in ("load", "call") else remote(g, values)(name, slot)), self.assertRaises(ValueError):
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


class ReviewBlockerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(c, "public_get", side_effect=AssertionError("NO_NETWORK")))
        self.stack.enter_context(patch.object(c, "github_post", side_effect=AssertionError("NO_NETWORK")))

    def archive(self, root, g, *, mutate=None, native_status=None):
        files = positive_files(g)
        files.update({"release.json": {"grant": g}, "source.json": runtime.source_spec(),
            "campaign-start.json": {"binding": digest(g), "slot": g["slot"], "mode": g["mode"],
                "native_calls_at_start": 0, "loads_at_start": 0},
            "campaign-end.json": {"binding": digest(g), "native_call_markers": 0, "call_reservations": 0,
                "weights_loaded": False, "load_permit": False, "call_permit": False},
            "summary.json": {"campaign": c.CAMPAIGN, "slot": g["slot"], "binding": digest(g), "mode": g["mode"],
                "status": "LIVE_GPU_PREFLIGHT_PASS", "error": None, "native_call_markers": 0,
                "call_reservations": 0, "weights_loaded": False}})
        ledger = {("submission", g["slot"]): {"grant": g, "gpu_budget": submit.gpu_budget(g)}}
        for phase in ("launch", "setup", "worker"):
            ledger[phase, g["slot"]] = copy.deepcopy(files[phase + "-permit.json"])
        if native_status:
            from test_internvl_v2_runtime import request
            r = request(runtime.source_spec(), g["request"]["image_sha256"])
            # Synthetic identity must match the release even in archive-only tests.
            r["sample_id"] = "SYNTHETIC"
            self.assertEqual(digest(r["sample_id"]), g["request"]["sample_id_sha256"])
            files["execution-request.json"] = r
            files["loaded.json"] = {"scope": "SYNTHETIC"}
            for name in ("sample/native_call.json", "sample/reservation.json", "sample/native.json",
                         "sample/processors.json", "sample/grammar.json"):
                files[name] = {"scope": "SYNTHETIC"}
            files["sample/raw.json"] = {"hnlo": None, "hnlo_status": runtime.HNLO_STATUS,
                "binding": {"input_sha256": r["image_sha256"]}}
            files["sample/result.json"] = {"status": native_status, "hnlo": None, "hnlo_status": runtime.HNLO_STATUS,
                "raw_sha256": digest(files["sample/raw.json"])}
            files["summary.json"].update(status=native_status, native_call_markers=1, call_reservations=1, weights_loaded=True)
            files["campaign-end.json"].update(native_call_markers=1, call_reservations=1, weights_loaded=True,
                                               load_permit=True, call_permit=True)
            for phase in ("load", "call"):
                event = challenge(g, phase)
                files[phase + "-permit.json"] = event
                ledger[phase, None] = ledger[phase, g["slot"]] = event
        if mutate:
            mutate(files)
        out = root / "output"
        out.mkdir()
        for name, value in files.items():
            if value is not None:
                write(out / name, value)
        for stage in ("setup", "worker"):
            if files.get(stage + "-supervisor.log", True) is not None:
                (out / (stage + "-supervisor.log")).write_bytes(b"SYNTHETIC_LOG_ONLY\n")
        archive = root / (g["job"].split("/")[1] + ".zip")
        export(out, archive)
        return archive, ledger

    def test_failed_kaggle_job_never_preflight_pass_complete_is_pass(self):
        for state in ("COMPLETE", "ERROR", "CANCELLED"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as d:
                g = grant()
                archive, ledger = self.archive(Path(d), g)
                with patch.object(c, "remote_record", side_effect=lambda name, slot=None: ledger.get((name, slot))):
                    result = submit.verify_result(archive, g, state)
                self.assertEqual(result["internal_status"], "LIVE_GPU_PREFLIGHT_PASS")
                self.assertEqual(result["status"], "LIVE_GPU_PREFLIGHT_PASS" if state == "COMPLETE" else "TECHNICAL_ERROR")
                self.assertEqual(result["gpu_budget"]["reserved_physical_gpu_seconds"], 1200)
                self.assertEqual(result["proof"], "ZERO_CALL_CONFIRMED")

    def test_missing_logs_worker_receipts_and_conflicting_environment_fail_closed(self):
        mutations = []
        for name in ("setup-supervisor.log", "worker-supervisor.log", "worker-supervisor.json", "setup-supervisor.json",
                     "worker-permit.json", "preflight.json", "hardware.json", "software.json", "allocation.json"):
            mutations.append(lambda f, name=name: f.update({name: None}))
        for name, field, value in (("worker-supervisor.json", "status", "CHILD_FAILURE"),
            ("worker-supervisor.json", "returncode", 1), ("worker-supervisor.json", "seconds", -1),
            ("worker-supervisor.json", "group_kill_sent", False), ("preflight.json", "status", "BLOCKED"),
            ("preflight.json", "calls", 1), ("processor.json", "status", "FAIL"),
            ("cuda.json", "fp16", "NOT_RUN"), ("checkpoint.json", "revision", "0" * 40),
            ("summary.json", "slot", 3), ("summary.json", "error", {"type": "Error"}),
            ("worker-permit.json", "parent_nonce", "f" * 64)):
            mutations.append(lambda f, name=name, field=field, value=value: f[name].update({field: value}))
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i), tempfile.TemporaryDirectory() as d:
                g = grant(); archive, ledger = self.archive(Path(d), g, mutate=mutate)
                with patch.object(c, "remote_record", side_effect=lambda name, slot=None: ledger.get((name, slot))), \
                        self.assertRaises((ValueError, KeyError)):
                    submit.verify_result(archive, g, "COMPLETE")

    def test_native_success_invalid_also_require_complete_no_second_call(self):
        for internal in ("SUCCESS", "INVALID", "TECHNICAL_ERROR"):
            for state in ("COMPLETE", "ERROR", "CANCELLED"):
                with self.subTest(internal=internal, state=state), tempfile.TemporaryDirectory() as d:
                    g = grant(2, "native")
                    g["request"]["sample_id_sha256"] = digest("SYNTHETIC")
                    g["request_sha256"] = digest(g["request"])
                    archive, ledger = self.archive(Path(d), g, native_status=internal)
                    with patch.object(c, "remote_record", side_effect=lambda name, slot=None: ledger.get((name, slot))):
                        result = submit.verify_result(archive, g, state)
                        self.assertEqual(result["status"], internal if state == "COMPLETE" else "TECHNICAL_ERROR")
                        with self.assertRaisesRegex(ValueError, "NATIVE_ALREADY_RESERVED"):
                            submit.predecessors(Mock(), grant(3, "native"), Path(d))

    def test_predecessor_complete_required_to_unlock_native(self):
        for state in ("COMPLETE", "ERROR", "CANCELLED"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as d:
                prior = grant()
                archive, ledger = self.archive(Path(d), prior)
                reader = lambda name, slot=None: ledger.get((name, slot))
                with patch.object(c, "remote_record", side_effect=reader), patch.object(submit, "live_identity"):
                    finished = submit.verify_result(archive, prior, state)
                    ledger["finished", 1] = finished
                    next_grant = grant(2, "native")
                    next_grant["predecessors"] = [digest(finished)]
                    api = Mock(); api.kernels_status.return_value = NS(status=state)
                    if state == "COMPLETE":
                        self.assertEqual(submit.predecessors(api, next_grant, Path(d)), [finished])
                    else:
                        with self.assertRaisesRegex(ValueError, "PREFLIGHT_REQUIRED"):
                            submit.predecessors(api, next_grant, Path(d))
                        # Failed zero-call job can still be a preflight repair predecessor.
                        next_grant["mode"] = "preflight"
                        self.assertEqual(submit.predecessors(api, next_grant, Path(d)), [finished])

    def test_one_two_three_jobs_never_exceed_cumulative_physical_budget(self):
        history = []
        for slot, state in enumerate(("COMPLETE", "ERROR", "CANCELLED"), 1):
            g = grant(slot)
            budget = submit.cumulative_budget(g, history)
            self.assertEqual(budget["cumulative_reserved_physical_gpu_seconds"], slot * 1200)
            self.assertEqual(budget["server_timeout_seconds"], 600)
            self.assertIsNone(budget["measured_usage"])
            history.append({"slot": slot, "terminal": state, "gpu_budget": budget})
        with self.assertRaisesRegex(ValueError, "THREE_JOB_BUDGET"):
            submit.gpu_budget({**g, "slot": 4})
        with patch.object(submit, "JOB_SECONDS", 601), self.assertRaisesRegex(ValueError, "EXHAUSTED"):
            submit.gpu_budget(grant(3))

    def test_missing_invalid_timing_cannot_refund_or_unlock_budget(self):
        g = grant()
        good = submit.gpu_budget(g)
        for bad in (None, {}, {**good, "server_timeout_seconds": -1}, {**good, "server_timeout_seconds": True},
            {**good, "server_timeout_seconds": 600.0}, {**good, "reserved_physical_gpu_seconds": 0},
            {**good, "physical_gpus": 1}, {**good, "binding": "f" * 64},
            {**good, "measured_usage": 1}, {**good, "cumulative_reserved_physical_gpu_seconds": 3601}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                submit.check_budget(bad, g)
        for prior in ([], [{"slot": 1, "terminal": "RUNNING", "gpu_budget": good}],
            [{"slot": 1, "terminal": "ERROR", "gpu_budget": {**good, "reserved_physical_gpu_seconds": 0}}]):
            with self.assertRaises(ValueError):
                submit.cumulative_budget(grant(2), prior)

    def test_old_or_missing_submission_budget_blocks_even_valid_zip(self):
        with tempfile.TemporaryDirectory() as d:
            g = grant(); archive, ledger = self.archive(Path(d), g)
            for value in (None, {"grant": g}, {"grant": g, "gpu_budget": {}}):
                ledger["submission", 1] = value
                with patch.object(c, "remote_record", side_effect=lambda name, slot=None: ledger.get((name, slot))), \
                        self.assertRaises(ValueError):
                    submit.verify_result(archive, g, "COMPLETE")

    def test_each_slot_sends_only_reserved_server_cap_and_failure_never_refunds(self):
        for slot in (1, 2, 3):
            with self.subTest(slot=slot), tempfile.TemporaryDirectory() as d:
                g = grant(slot)
                prior = [{"slot": i, "terminal": "ERROR", "gpu_budget": submit.gpu_budget(grant(i))}
                         for i in range(1, slot)]
                records = {}
                def create(name, value, head, slot=None):
                    self.assertNotIn((name, slot), records)
                    records[name, slot] = value
                api = Mock(); api.kernels_push.side_effect = TimeoutError("unknown")
                api.kernels_status.return_value = NS(status="UNKNOWN")
                notebook = Path(d) / "synthetic.ipynb"; notebook.write_text("{}")
                with patch.object(submit, "validate_local_release", return_value=g), patch.object(c, "check_head"), \
                    patch.object(c, "remote_record", side_effect=lambda name, slot=None: records.get((name, slot))), \
                    patch.object(c, "create_record", side_effect=create), patch.object(submit, "predecessors", return_value=prior), \
                    patch.object(submit, "inventory", return_value={}):
                    with self.assertRaisesRegex(ValueError, "UNKNOWN_JOB"):
                        submit.submit(api, g, 6622148400, notebook, Path(d) / "stage", Path(d))
                    with self.assertRaisesRegex(ValueError, "NONEMPTY_LEDGER"):
                        submit.submit(api, g, 6622148400, notebook, Path(d) / "again", Path(d))
                self.assertEqual(api.kernels_push.call_count, 1)
                self.assertEqual(api.kernels_push.call_args.kwargs, {"timeout": "600", "acc": "NvidiaTeslaT4"})
                self.assertEqual(records["submission", slot]["gpu_budget"]["cumulative_reserved_physical_gpu_seconds"], slot * 1200)


if __name__ == "__main__":
    unittest.main()
