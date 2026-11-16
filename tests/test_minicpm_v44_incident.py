"""Synthetic pre-native closure/source-release tests. No real data/network/GPU."""
from copy import deepcopy
import hashlib
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch, Mock

import test_minicpm_run1_recovery as fixtures
from safeshift.fulltrain import minicpm_incident as incident, minicpm_release as a, minicpm_recovery as recovery
from safeshift.pilot.artifacts import read, write, write_bytes, export
from safeshift.pilot.contract import digest
from scripts import minicpm_v44_incident as op, minicpm_fulltrain_recovery as journal, minicpm_fulltrain_operator as old


class IncidentTests(unittest.TestCase):
    setUpClass = classmethod(fixtures.RecoveryTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.RecoveryTests.tearDownClass.__func__)
    make_ticket = fixtures.RecoveryTests.make_ticket
    build = fixtures.RecoveryTests.build
    staged_operator = fixtures.RecoveryTests.staged_operator

    def setUp(self):
        fixtures.RecoveryTests.setUp(self)
        self.operator = self.staged_operator()
        with patch.object(a, "load", return_value=self.grant):
            self.active = self.operator.state()[3]
        self.value, self.ticket = self.active["value"], self.active["ticket"]
        self.operator.append("PUBLISH_INTENT", {"ticket_sha256": digest(self.ticket)})
        self.operator.append("PUBLISHED", {"ticket_sha256": digest(self.ticket), "proof": {"synthetic": True}})
        for name, value in {"PREVIOUS_GRANT": digest(self.grant), "PREVIOUS_TICKET": digest(self.ticket),
            "PREVIOUS_VALUE": digest(self.value), "PREVIOUS_SOURCE": self.value["request"]["source_sha256"],
            "PREVIOUS_MERGE": self.grant["merged_sha"], "RESERVED": self.ticket["payload"]["reserved_after"]}.items():
            p = patch.object(incident, name, value); p.start(); self.addCleanup(p.stop)
        self.previous = op.prefix(self.operator.events())
        self.directory = self.root / "data/processed/incident"
        self.directory.mkdir()
        self.provider_receipt = {"state": "COMPLETE", "job_id": incident.JOB, "version": 1, "kernel_id": 10,
            "notebook_code_sha256": self.ticket["payload"]["notebook_code_sha256"], "safeshift_metadata": "MATCHED"}
        self.name = "minicpm-fulltrain/supervision/" + "a" * 32 + ".zip"
        self.control = self.root / "synthetic-supervisor"
        self.control.mkdir()
        failure = {"stage": "admit", "category": "TECHNICAL", "message": "SUPERVISED_CHILD_FAILURE"}
        write(self.control / "failure.json", failure)
        write(self.control / "release.json", {"status": "BLOCKED", "last_stage": "admit", "attempt_observed": False,
            "diagnostic": False, "recovery": "NO_ATTEMPT", "scientific_qualified": False,
            "source_sha256": incident.PREVIOUS_SOURCE, "failure": failure})
        write(self.control / "admit-process.json", {"schema": "fresh-process-supervision-v1", "status": "CHILD_FAILURE",
            "returncode": 1, "group_kill_sent": True, "automatic_retry": False})
        write(self.control / "request.json", self.value["request"])
        write(self.control / "capability.json", {"ticket": self.ticket})
        claims = {kind + ".json": {"kind": kind, "number": 4, "request_sha256": digest(self.value["request"]),
            "ticket_sha256": digest(self.ticket), "time_unix": self.ticket["payload"]["issued_unix"] + i}
            for i, kind in enumerate(("launch", "admit"))}
        write(self.control / "claims.json", claims)
        for name in ("final_timing.json", "retention.json", "admit/failure.json"):
            write(self.control / name, {"synthetic": True})
        write_bytes(self.control / "admit.log", b"synthetic missing master before setup\n")
        self.archive = self.directory / "provider" / self.name
        self.archive.parent.mkdir(parents=True)
        export(self.control, self.archive)
        write(self.directory / "provider.json", self.provider_receipt)
        write(self.directory / "inventory.json", [self.name, self.name + ".sha256.json"])
        write(self.directory / "full-inventory.json", [self.name, self.name + ".sha256.json"])
        write(self.directory / "value.json", self.value)
        write(self.directory / "ticket.json", self.ticket)
        write(self.directory / "notebook.ipynb", read(self.root / self.active["package"] / "notebook.ipynb"))
        write_bytes(self.directory / "provider.log", b"synthetic provider log\n")

    def verify_receipt(self):
        return op.verify_evidence(self.directory, self.previous)

    def replace_member(self, name, mutate):
        value = read(self.control / name); mutate(value)
        (self.control / name).write_text(__import__("json").dumps(value), encoding="utf8")
        (self.control / "checksums.json").unlink()
        self.archive.unlink(); Path(str(self.archive) + ".sha256.json").unlink()
        export(self.control, self.archive)

    def test_supervisor_only_closes_technical_failure_without_result_or_refund(self):
        report = self.verify_receipt()
        self.assertEqual(report["disposition"], "FAILED_PRE_NATIVE_NO_USABLE_RESULTS")
        self.assertEqual(report["native_calls"], 0)
        self.assertEqual(report["reserved_after"], self.ticket["payload"]["reserved_after"])
        self.assertFalse(report["history_import"])
        self.assertEqual(len(self.operator.events()), 6)
        for state in ("RUNNING", "QUEUED", "CANCELLED", "UNKNOWN"):
            bad = {**self.provider_receipt, "state": state}
            with self.subTest(state=state), self.assertRaisesRegex(ValueError, "TERMINAL_PROVIDER"):
                incident.verify_supervisor(self.value, self.ticket, self.archive, bad)

    def test_unexpected_call_claim_and_attempt_stage_block_even_with_valid_zip(self):
        self.replace_member("claims.json", lambda c:c.update({"call-000000.json": c["admit.json"]}))
        with self.assertRaisesRegex(ValueError, "NO_NATIVE_OR_UNKNOWN_CLAIM"): self.verify_receipt()

    def test_attempt_observed_or_nonreaped_child_cannot_be_closed(self):
        self.replace_member("release.json", lambda c:c.update(attempt_observed=True))
        with self.assertRaisesRegex(ValueError, "ADMIT_FAILURE"): self.verify_receipt()

    def test_nonreaped_child_is_not_a_terminal_pre_native_proof(self):
        self.replace_member("admit-process.json", lambda c:c.update(group_kill_sent=False))
        with self.assertRaisesRegex(ValueError, "REAPED_CHILD"): self.verify_receipt()

    def test_new_release_authenticates_original_owner_record_and_unchanged_science(self):
        import json
        directive_body = "SYNTHETIC repair directive; not actual permission"
        old_body = a.RECOVERY_MARKER + "\n```json\n" + json.dumps(self.grant) + "\n```"
        previous = deepcopy(self.previous)
        previous["locator"] = {"comment_id": 12, "body_sha256": hashlib.sha256(old_body.encode()).hexdigest()}
        directive = {"comment_id": incident.DIRECTIVE, "body_sha256": hashlib.sha256(directive_body.encode()).hexdigest()}
        grant = op.repair_template(self.grant, previous, self.verify_receipt(), directive)
        grant["implementation_pr"] = 200
        def record(number, body):
            return {"id": number, "body": body, "issue_url": a.API + "/issues/199",
                "user": {"id": a.OWNER_ID, "login": a.OWNER}}
        graph = {"/issues/comments/12": record(12, old_body),
            "/issues/comments/" + str(incident.DIRECTIVE): record(incident.DIRECTIVE, directive_body)}
        incident.authenticate_repair(grant, graph.__getitem__)
        bad = deepcopy(grant); bad["scope"]["identity"]["configuration_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SCIENCE_OR_INPUT_DRIFT"):
            incident.authenticate_repair(bad, graph.__getitem__)
        graph["/issues/comments/12"]["user"]["id"] = 1
        with self.assertRaisesRegex(ValueError, "AUTHENTIC_RECORD"):
            incident.authenticate_repair(grant, graph.__getitem__)

    def test_unknown_extra_output_partial_pair_or_duplicate_zip_blocks(self):
        for names in ([self.name], [self.name, self.name + ".sha256.json", "minicpm-fulltrain/attempt.zip"],
                      [self.name, self.name + ".sha256.json", "unknown.zip"]):
            with self.subTest(names=names), self.assertRaises(ValueError): op.output_names(names)
        with self.assertRaisesRegex(ValueError, "UNEXPECTED_OUTPUT"):
            op.validate_inventory([self.name, self.name + ".sha256.json", "minicpm-fulltrain/calls/000000/native_call.json"],
                self.value, self.name)
        (self.directory / "provider.log").write_bytes(b"tampered")
        self.assertNotEqual(self.verify_receipt()["provider_log_sha256"], hashlib.sha256(b"synthetic provider log\n").hexdigest())

    def test_authenticated_new_source_rebind_preserves_holds_and_signs_serial5(self):
        closure = self.verify_receipt()
        grant = op.repair_template(self.grant, self.previous, closure,
            {"comment_id": incident.DIRECTIVE, "body_sha256": "d" * 64})
        grant["implementation_pr"] = 200  # synthetic review graph, not an actual approval
        a.validate(grant)
        new_value = journal.restart_spec(self.value, source_repair=True)
        a.bind(grant, new_value)
        provider = deepcopy(self.provider)
        provider["technical_predecessor"] = {"job": incident.JOB, "version": 1, "state": "COMPLETE", "kernel_id": 10}
        selected = {n: Mock() for n in (self.name, self.name + ".sha256.json")}
        def download(selected, expected, target):
            for name in expected:
                path = Path(target) / name; path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.directory / "provider" / name, path)
        before = {p:p.read_bytes() for p in self.operator.root.glob("event-*.json")}
        with patch.object(a, "load", return_value=grant), patch.object(old, "clean_source"), \
             patch("scripts.reconcile_train3763_manual.observe_kernel", return_value=self.provider_receipt), \
             patch.object(op, "inventory", return_value=(selected, "synthetic provider log\n", sorted(selected))), \
             patch.object(op.transport, "download_selected", side_effect=download), \
             patch("safeshift.internvl3763_operator.api", return_value=Mock()):
            result = self.operator.rebind_release(self.locator, new_value, self.directory)
            self.assertEqual(result["next_serial"], 5)
            self.assertEqual(self.operator.state()[2], incident.RESERVED)
            with self.assertRaises(ValueError): self.operator.rebind_release(self.locator, new_value, self.directory)
            with patch.object(self.operator, "observe_provider", return_value=provider), \
                 patch.object(old, "notebook", side_effect=self.build), \
                 patch.object(old.sizing, "propose", return_value={"calls": 3, "seconds": 600}):
                self.operator.stage(self.key, self.root / "data/processed/fresh-source")
            _, events, reserved, active, complete = self.operator.state()
            self.assertEqual(active["ticket"]["payload"]["number"], 5)
            self.assertEqual(active["ticket"]["payload"]["reserved_before"], incident.RESERVED)
            self.assertEqual(reserved["calls"], incident.RESERVED["calls"] + 3)
            self.assertEqual(active["value"]["request"]["history"], [])
            self.assertEqual(active["value"]["request"]["plan"]["scheduled_ordinals"][0], 0)
            self.assertEqual(complete, [])
            self.assertNotIn("RESTART_COLLECTED", [e["kind"] for e in events])
        for path, raw in before.items(): self.assertEqual(path.read_bytes(), raw)
        bad = deepcopy(grant); bad["implementation_pr"] = 199
        with self.assertRaisesRegex(ValueError, "IMPLEMENTATION_PR"): a.validate(bad)
        bad = deepcopy(grant); bad["repair"]["reserved_after"]["calls"] = 0
        with self.assertRaisesRegex(ValueError, "NO_REFUND"): a.validate(bad)


class NotebookTests(unittest.TestCase):
    def test_v5_builder_requires_fresh_release_and_identifies_source_transition(self):
        from scripts.generate_minicpm_fulltrain_notebook import notebook
        from safeshift.candidates.source import ROOT
        ref = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        with self.assertRaisesRegex(ValueError, "RELEASE_VERSION"):
            notebook(ref, capsule_sha256="0" * 64, release_version=5)
        nb = notebook(ref, capsule_sha256="0" * 64,
            release_locator={"comment_id": 1, "body_sha256": "0" * 64}, release_version=5)
        self.assertEqual(nb["metadata"]["safeshift"]["mode"], "MINICPM_FULLTRAIN_RELEASE_V5")
        self.assertEqual(nb["metadata"]["safeshift"]["source_transition"], incident.SCHEMA)
        for cell in nb["cells"]:
            if cell["cell_type"] == "code":
                compile("".join(cell["source"]), "synthetic-not-activated-v5-notebook", "exec")
                self.assertEqual(cell["outputs"], [])
                self.assertIsNone(cell["execution_count"])


if __name__ == "__main__": unittest.main()
