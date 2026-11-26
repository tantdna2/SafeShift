"""Release proposals cannot turn CPU/local/provider claims into run authority."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_minicpm_fulltrain_ui as fixtures
from safeshift.fulltrain import contract, minicpm_ui as ui
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest
from scripts import minicpm_fulltrain_release as release
from scripts.generate_minicpm_fulltrain_notebook import notebook

BASE = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ui.ROOT, text=True).strip()


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real exact-commit builder; reuse only its immutable result across tests.
        cls.nb = notebook(BASE, capsule_sha256="f" * 64)

    def setUp(self):
        self.fixture = fixtures.OwnerUITests("test_initial_package_complete_inputs_and_unchanged_fence")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root, self.value = self.fixture.root, self.fixture.value
        self.denied = patch.object(socket, "socket", side_effect=AssertionError("NETWORK_FORBIDDEN"))
        self.denied.start()
        self.addCleanup(self.denied.stop)
        self.package = self.root / "package"
        self.builds = {}

        def build(pin):
            nb = deepcopy(self.nb)
            nb["metadata"]["safeshift"]["capsule_sha256"] = pin
            nb["cells"][-1]["source"] = [s.replace("f" * 64, pin) for s in nb["cells"][-1]["source"]]
            self.builds[pin] = deepcopy(nb)
            return nb
        self.build = build
        ui.package(self.value, [], self.package, self.build)
        self.binding = {"runtime_commit": BASE, "source_sha256": self.value["request"]["source_sha256"],
            "tools_sha256": digest(release.tool_manifest()), "job": self.value["job"], "version": 1,
            "capsule_ref": self.value["capsule_ref"], "files": {n: sha(self.package / n) for n in
                ("handoff.json", "notebook.ipynb", "kernel-metadata.json", "dataset-metadata.json", "dataset/" + ui.MARKER)}}

    def inspect(self, package=None):
        # Other tests isolate corruption outside the already-reproduced payload.
        with patch.object(release, "notebook", side_effect=lambda ref, repo, capsule_sha256: deepcopy(self.builds[capsule_sha256])):
            return release.inspect_package(package or self.package)

    def sequence(self):
        return {"first": (self.value, self.binding), "current": (self.value, self.binding),
            "reserved": {"calls": 2, "jobs": 1, "gpu_seconds": 240},
            "archive_sizes": [],
            "job_limits": [{"calls": 2, "seconds": 120}], "counts_before_proposed_job": self.value["request"]["plan"]["counts"]}

    def grant(self):
        g = release.template(self.value, self.binding)
        g.update(authorization="OWNER_GRANTED_SERIAL_TRAIN3763_UI_ONLY", implementation_pr=999,
            reviewed_head="a" * 40, merged_sha="b" * 40, issued_unix=100, expires_unix=10000)
        g["caps"] = {"total_calls": 3763, "total_jobs": 30, "total_gpu_seconds": 500000,
            "job_calls": 3763, "job_seconds": 7200, "physical_gpus": 2, "loads_per_job": 1, "archive_bytes": 2**30}
        return g

    def exports(self, grant=None):
        g = deepcopy(grant or self.grant())
        exports = {"/pulls/999": {"merged": True, "draft": False, "base": {"ref": "main"},
            "head": {"sha": g["reviewed_head"]}, "merge_commit_sha": g["merged_sha"]}}
        for ref in (g["reviewed_head"], g["merged_sha"]):
            for name in release.TOOLS:
                raw = (ui.ROOT / name).read_bytes()
                exports["/contents/" + name + "?ref=" + ref] = {"type": "file", "path": name,
                    "encoding": "base64", "size": len(raw), "content": base64.b64encode(raw).decode()}
        def add(number, marker, value):
            body = marker + "\n```json\n" + json.dumps(value) + "\n```"
            exports["/issues/comments/" + str(number)] = {"id": number, "user": {"login": "tantdna2"},
                "issue_url": release.API + "/issues/999", "body": body}
            return {"comment_id": number, "body_sha256": hashlib.sha256(body.encode()).hexdigest()}
        for i, kind in enumerate(release.ROLES, 2):
            g["approvals"][kind] = add(i, release.APPROVAL, {"kind": kind, "status": "APPROVED",
                "reviewed_head": g["reviewed_head"], "scope_sha256": release.grant_scope(g)})
        return add(1, release.MARKER, g), exports

    def test_real_exact_builder_matches_packaged_notebook_and_all_bindings(self):
        got, binding = release.inspect_package(self.package)
        self.assertEqual(got, self.value)
        self.assertEqual(binding, self.binding)
        self.assertEqual(binding["source_sha256"], digest(contract.source_manifest()))

    def test_template_never_supplies_caps_approvals_authorization_or_dates(self):
        t = release.template(self.value, self.binding)
        self.assertTrue(all(v is None for v in t["caps"].values()))
        self.assertTrue(all(v is None for v in t["approvals"].values()))
        for n in ("authorization", "implementation_pr", "reviewed_head", "merged_sha", "issued_unix", "expires_unix"):
            self.assertIsNone(t[n])
        with self.assertRaisesRegex(ValueError, "NO_IMPLICIT_GRANT"):
            release.validate_grant(t, self.value, self.binding)

    def test_rehashing_modified_notebook_does_not_repair_source_binding(self):
        nb = read(self.package / "notebook.ipynb")
        nb["cells"][-1]["source"].append("print('unreviewed')\n")
        (self.package / "notebook.ipynb").write_text(json.dumps(nb), encoding="utf8")
        h = read(self.package / "handoff.json"); h["notebook_sha256"] = sha(self.package / "notebook.ipynb")
        (self.package / "handoff.json").write_text(json.dumps(h), encoding="utf8")
        with self.assertRaisesRegex(ValueError, "EXACT_NOTEBOOK_BYTES"): self.inspect()

    def test_private_gpu_inputs_and_capsule_metadata_are_exact(self):
        for name, mutate in (("kernel-metadata.json", lambda v: v.update(is_private=False)),
                            ("dataset-metadata.json", lambda v: v.update(isPrivate=False)),
                            ("handoff.json", lambda v: v.update(native_calls=3763))):
            path = self.package / name
            original = path.read_bytes()
            value = read(path); mutate(value); path.write_text(json.dumps(value), encoding="utf8")
            with self.subTest(name=name), self.assertRaises(ValueError): self.inspect()
            path.write_bytes(original)

    def test_missing_authority_receipt_is_blocked_with_exact_reservations(self):
        report = release.assess(self.sequence())
        self.assertEqual(report["status"], "BLOCKED")
        self.assertEqual(report["authority"], "MISSING")
        self.assertEqual(report["reserved_including_proposed_job"]["gpu_seconds"], 240)
        self.assertFalse(report["execution_authorized"])
        self.assertEqual(report["native_calls"], 0)

    def test_offline_authentic_shape_replay_still_blocks_execution(self):
        locator, exports = self.exports()
        g = release.authenticate(locator, self.value, self.binding, reader=release.Exports(exports))
        self.assertEqual(g["caps"]["total_calls"], 3763)
        report = release.assess(self.sequence(), locator=locator, exports=exports, now=200)
        self.assertEqual(report["authority"], "OFFLINE_REPLAY_ONLY_ORIGIN_NOT_AUTHENTICATED")
        self.assertEqual(report["status"], "BLOCKED")
        with self.assertRaises(PermissionError): contract.authorize(g)

    def test_forged_wrong_author_body_or_unmerged_pr_rejected(self):
        locator, exports = self.exports()
        for change in (lambda x: x["/issues/comments/1"]["user"].update(login="codex"),
                       lambda x: x["/issues/comments/1"].update(body="approved=true"),
                       lambda x: x["/pulls/999"].update(merged=False),
                       lambda x: x["/pulls/999"]["head"].update(sha="c" * 40),
                       lambda x: x.pop("/issues/comments/2")):
            bad = deepcopy(exports); change(bad)
            with self.subTest(change=change), self.assertRaises(ValueError):
                release.authenticate(locator, self.value, self.binding, reader=release.Exports(bad))

    def test_source_rights_caps_science_and_prior_grants_cannot_be_transferred(self):
        for change in (lambda x: x.update(implementation_pr=195),
                       lambda x: x["scope"].update(source_sha256="f" * 64),
                       lambda x: x["scope"]["identity"].update(hnlo_policy="LOCKED_EXISTING_METHOD"),
                       lambda x: x["first_package"].update(job="other/job"),
                       lambda x: x["first_package"].update(version=True),
                       lambda x: x["caps"].update(physical_gpus=1),
                       lambda x: x["caps"].update(total_calls=True),
                       lambda x: x["caps"].update(total_calls=160),
                       lambda x: x["caps"].update(loads_per_job=2),
                       lambda x: x.update(stop_rules=[])):
            g = self.grant(); change(g)
            with self.subTest(change=change), self.assertRaises(ValueError):
                release.validate_grant(g, self.value, self.binding)

    def test_caps_dates_and_job_limits_exhaust_without_refund(self):
        sequence = self.sequence()
        sequence["reserved"] = {"calls": 3764, "jobs": 2, "gpu_seconds": 480}
        with self.assertRaisesRegex(ValueError, "CUMULATIVE_CAP_NO_REFUND"):
            release.budget(sequence, self.grant(), now=200)
        for field, count in (("jobs", 31), ("gpu_seconds", 500001)):
            sequence = self.sequence(); sequence["reserved"][field] = count
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "CUMULATIVE_CAP_NO_REFUND"):
                release.budget(sequence, self.grant(), now=200)
        with self.assertRaisesRegex(ValueError, "DEADLINE_HEADROOM"):
            release.budget(self.sequence(), self.grant(), now=9880)
        with self.assertRaisesRegex(ValueError, "DEADLINE_HEADROOM"):
            release.budget(self.sequence(), self.grant(), now=99)
        g = self.grant(); g["caps"]["job_calls"] = 1
        with self.assertRaisesRegex(ValueError, "PER_JOB_CAP"):
            release.budget(self.sequence(), g, now=200)

    def test_duplicate_or_nonfinite_authority_json_and_missing_exports_fail(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            release.record(release.MARKER + '\n```json\n{"x":1,"x":2}\n```', release.MARKER)
        with self.assertRaisesRegex(ValueError, "NONFINITE"):
            release.record(release.MARKER + '\n```json\n{"x":NaN}\n```', release.MARKER)
        with self.assertRaisesRegex(ValueError, "EXPORT_PATHS"): release.Exports({"https://evil": {}})
        with self.assertRaisesRegex(ValueError, "MISSING_GITHUB_EXPORT"): release.Exports({})("/pulls/999")
        with self.assertRaisesRegex(ValueError, "TOGETHER"): release.assess(self.sequence(), locator={})

    def test_archive_cap_and_impossible_remaining_capacity_block(self):
        seq = self.sequence(); seq["archive_sizes"] = [2**30 + 1]
        with self.assertRaisesRegex(ValueError, "ARCHIVE_CAP"):
            release.budget(seq, self.grant(), now=200)
        g = self.grant(); g["caps"]["total_jobs"] = 1
        with self.assertRaisesRegex(ValueError, "CAPACITY_CANNOT_COVER_PENDING"):
            release.budget(self.sequence(), g, now=200)

    def test_approval_cannot_be_reused_after_cap_change(self):
        locator, exports = self.exports()
        comment = exports["/issues/comments/1"]
        grant = release.record(comment["body"], release.MARKER)
        grant["caps"]["total_gpu_seconds"] += 1
        comment["body"] = release.MARKER + "\n```json\n" + json.dumps(grant) + "\n```"
        locator["body_sha256"] = hashlib.sha256(comment["body"].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "APPROVAL_ROLE_SCOPE"):
            release.authenticate(locator, self.value, self.binding, reader=release.Exports(exports))

    def test_reviewed_and_merged_tool_bytes_are_both_required(self):
        locator, exports = self.exports()
        for ref in ("a" * 40, "b" * 40):
            bad = deepcopy(exports)
            item = bad["/contents/scripts/minicpm_fulltrain_release.py?ref=" + ref]
            item["content"] = base64.b64encode(b"unreviewed bytes").decode()
            item["size"] = len(b"unreviewed bytes")
            with self.subTest(ref=ref), self.assertRaisesRegex(ValueError, "REVIEWED_TOOL_BYTES"):
                release.authenticate(locator, self.value, self.binding, reader=release.Exports(bad))

    def test_real_custody_resume_counts_full_reservations_and_keeps_invalid_consumed(self):
        attempt, supervisor, backend = self.fixture.results()
        report = ui.verify_results(self.value, self.package / "dataset", attempt, supervisor, self.root / "verified")
        second = ui.next_capsule(self.value, report, run_id="second", attempt_id="second-a",
            job="nguynanhtn/second", capsule_ref="nguynanhtn/safeshift-minicpm-capsule-second/1", max_calls=3761, max_seconds=7200)
        package2 = ui.package(second, [attempt], self.root / "second", self.build)
        with patch.object(release, "notebook", side_effect=lambda ref, repo, capsule_sha256: deepcopy(self.builds[capsule_sha256])):
            sequence = release.replay_sequence([self.package, package2], [attempt], [supervisor])
        self.assertEqual(sequence["reserved"], {"calls": 3763, "jobs": 2, "gpu_seconds": 14640})
        self.assertEqual(sequence["counts_before_proposed_job"], {"SUCCESS": 1, "INVALID": 1, "NOT_ATTEMPTED": 3761})
        self.assertEqual(second["request"]["plan"]["scheduled_ordinals"], list(range(2, 3763)))
        self.assertEqual(backend.calls, 2)
        # A previous package cannot disappear simply because ancestry ZIPs exist.
        with patch.object(release, "notebook", side_effect=lambda ref, repo, capsule_sha256: deepcopy(self.builds[capsule_sha256])):
            with self.assertRaisesRegex(ValueError, "INITIAL_PACKAGE_REQUIRED"):
                release.replay_sequence([package2], [], [])
            with self.assertRaisesRegex(ValueError, "ALL_PRIOR_PAIRS"):
                release.replay_sequence([self.package, package2], [], [])

    def test_failed_attempt_cannot_be_hidden_by_a_planning_report(self):
        attempt, supervisor, _ = self.fixture.results([RuntimeError("CUDA out of memory")])
        report = ui.verify_results(self.value, self.package / "dataset", attempt, supervisor, self.root / "verified")
        self.assertEqual(report["continuation"], "STOP_RECONCILE_FAILURE")
        # Simulate an untrusted report edited before the old CPU next planner.
        report["continuation"] = "REVIEW_CAPS_AND_RELEASE"
        second = ui.next_capsule(self.value, report, run_id="second", attempt_id="second-a",
            job="nguynanhtn/second", capsule_ref="nguynanhtn/safeshift-minicpm-capsule-second/1", max_calls=1, max_seconds=120)
        package2 = ui.package(second, [attempt], self.root / "second", self.build)
        with patch.object(release, "notebook", side_effect=lambda ref, repo, capsule_sha256: deepcopy(self.builds[capsule_sha256])):
            with self.assertRaisesRegex(ValueError, "SERIAL_HISTORY_OR_FAILURE"):
                release.replay_sequence([self.package, package2], [attempt], [supervisor])

    def test_cli_runs_offline_and_refuses_output_overwrite(self):
        guard = """import sys
def audit(event, args):
    if event.startswith('socket.'):
        raise AssertionError('NETWORK_FORBIDDEN:' + event)
sys.addaudithook(audit)
from scripts.minicpm_fulltrain_release import main
main()
"""
        output = self.root / "blocked.json"
        command = [sys.executable, "-B", "-c", guard, "check", "--package", str(self.package), "--output", str(output)]
        result = subprocess.run(command, cwd=ui.ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(read(output)["status"], "BLOCKED")
        self.assertFalse(read(output)["execution_authorized"])
        original = output.read_bytes()
        result = subprocess.run(command, cwd=ui.ROOT, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CREATE_ONLY", result.stderr)
        self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
