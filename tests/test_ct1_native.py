"""CPU-only regressions for the CT1 production path. All payloads are synthetic."""

from collections import Counter
from itertools import permutations
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

from safeshift.data.saved_reports import json_bytes, sha256
from safeshift.evaluation.ct1_contract import ARMS
from safeshift.evaluation.ct1_pilot import replay
from safeshift.fulltrain import ct1_run, ct1_native
from safeshift.pilot.artifacts import sha, verify_archive, write, write_bytes
from scripts import build_ct1_kaggle_notebooks as nb
from scripts import run_ct1_native_pilot as controller


class FixtureBackend:
    """Injected by tests only. Used to exercise the normal journal and export."""
    def __init__(self, before=None, after=None):
        self.calls = []
        self.before, self.after = before, after

    def generate(self, payload, arm, begin, record_tokens):
        self.calls.append(arm)
        if self.before:
            self.before()
        begin({"prompt_tokens": 7, "max_new_tokens": 768, "memory_before": {}})
        record_tokens({"input_ids": [1], "returned_ids": [[1, 2]], "seconds": 0.0})
        if self.after:
            self.after()
        level = "Level01"
        text = {"safety_level": level}
        if arm != "A":
            text.update(evidence_status="INSUFFICIENT", evidence=[])
        return {"raw_text": json.dumps(text), "at_cap": False, "eos": True, "new_tokens": 1}, {}

    def decode(self, tokens):
        return {"raw_text": '{"safety_level":"Level02"}', "at_cap": False, "eos": True, "new_tokens": 1}

    def failure_memory(self):
        return {"fixture": True}


class NativeTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "pilot"
        self.data.mkdir()
        (self.data / "images").mkdir()
        self.exclusions = sorted(sha256(f"audit-{i}".encode()) for i in range(32))
        self.plan = {"kind": "TRAIN_DEVELOPMENT", "arms": list(ARMS), "cases": []}
        for i in range(48):
            case = f"p-{i:012x}"
            payload = f"opaque case bytes {i}".encode()
            write_bytes(self.data / "images" / (case + ".png"), payload)
            self.plan["cases"].append({"case_id": case, "image_sha256": sha256(payload)})
        self.plan_sha = write_bytes(self.data / "plan.json", json_bytes(self.plan))
        write_bytes(self.data / "exclusions.json", json_bytes(self.exclusions))
        self.binding = ct1_run.identity(self.plan_sha, "a" * 64, "b" * 64, "c" * 64, "ct1-000000000000")
        self.patch = patch("safeshift.evaluation.ct1_pilot.EXCLUSIONS_SHA256",
                           sha256(json_bytes(self.exclusions)))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def evidence(self, name):
        out = self.root / name
        out.mkdir()
        write(out / "identity.json", self.binding)
        write(out / "config-summary.json", {"mode": "pilot"})
        write(out / "resume-admission.json", {"status": "FRESH_ADMITTED"})
        return out

    def run_it(self, out, backend, *, seconds=60):
        return ct1_run.execute(out, self.plan, self.binding, self.data / "images", backend,
                              time.monotonic() + seconds)

    def test_exact_opaque_cohort_and_balanced_order(self):
        ct1_run.admit(self.data, self.plan_sha)
        rows = ct1_run.schedule(self.plan)
        self.assertEqual(len(rows), 144)
        by_image = Counter(tuple(r[1] for r in rows[i:i + 3]) for i in range(0, len(rows), 3))
        self.assertEqual(by_image, dict.fromkeys(permutations(ARMS), 8))
        (self.data / "truth.json").touch()
        with self.assertRaisesRegex(ValueError, "ALLOWLIST"):
            ct1_run.admit(self.data, self.plan_sha)

    def test_input_and_exclusions_tampering(self):
        with self.assertRaises(ValueError):
            ct1_run.admit(self.data, "d" * 64)
        p = self.data / "images" / (self.plan["cases"][0]["case_id"] + ".png")
        p.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "IMAGE_SEAL"):
            ct1_run.admit(self.data, self.plan_sha)

    def test_export_replay_all_144(self):
        output = self.evidence("good")
        fake = FixtureBackend()
        self.run_it(output, fake)
        self.assertEqual(len(fake.calls), 144)
        archive = self.root / "good.zip"
        ct1_run.checkpoint_results(output, archive, self.plan, self.binding)
        members = verify_archive(archive)
        self.assertIn("runs.json", members)
        self.assertNotIn("images", members)
        runs = json.loads((output / "runs.json").read_bytes())
        decoded = replay(self.plan, runs, self.plan_sha, self.exclusions)
        self.assertEqual(Counter(r["status"] for r in decoded.values()), {"SUCCESS": 144})
        self.run_it(output, fake)
        self.assertEqual(len(fake.calls), 144)

    def test_timeout_resume_does_not_repeat_ambiguous_intent(self):
        output = self.evidence("broken")
        first = FixtureBackend(after=lambda: (_ for _ in ()).throw(RuntimeError("fixture timeout")))
        with self.assertRaises(RuntimeError):
            self.run_it(output, first)
        self.assertEqual(len(first.calls), 1)
        archive = self.root / "broken.zip"
        ct1_run.checkpoint_results(output, archive, self.plan, self.binding)
        partial = json.loads((output / "summary.json").read_bytes())
        self.assertEqual((partial["durable_native_intents"], partial["not_attempted"]), (1, 143))
        recovered = self.evidence("resume")
        with self.assertRaisesRegex(ValueError, "ZIP_SEAL"):
            ct1_run.restore(archive, "0" * 64, recovered, self.binding)
        with self.assertRaisesRegex(ValueError, "IDENTITY"):
            ct1_run.restore(archive, sha(archive), recovered, {**self.binding, "max_calls": 143})
        ct1_run.restore(archive, sha(archive), recovered, self.binding)
        backend = FixtureBackend()
        self.run_it(recovered, backend)
        self.assertEqual(len(backend.calls), 143)
        self.assertTrue((recovered / "calls/000/failure.json").is_file())
        self.assertTrue((recovered / "calls/000/tokens.json").is_file())
        self.assertEqual(json.loads((recovered / "calls/000/result.json").read_bytes())["level"], "Level02")

    def test_no_native_when_expired_or_preprocessing_failed(self):
        output = self.evidence("early")
        fake = FixtureBackend()
        self.run_it(output, fake, seconds=-1)
        self.assertFalse(fake.calls)
        fake.before = lambda: (_ for _ in ()).throw(ValueError("invalid image"))
        with self.assertRaisesRegex(ValueError, "invalid image"):
            self.run_it(output, fake)
        self.assertFalse((output / "calls/000/intent.json").exists())
        self.assertTrue((output / "calls/000/failure.json").exists())

    def test_raw_exists_before_parsing_and_checksum_is_enforced(self):
        out = self.evidence("raw")
        invokes = []
        actual = ct1_run._parsed
        def observed(arm, row):
            if not invokes:
                self.assertTrue((out / "calls/000/raw.json").exists())
            invokes.append(arm)
            return actual(arm, row)
        with patch.object(ct1_run, "_parsed", side_effect=observed):
            self.run_it(out, FixtureBackend())
        self.assertEqual(len(invokes), 144)
        (out / "calls/000/tokens.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "TOKEN_BINDING"):
            ct1_run.checkpoint_results(out, self.root / "invalid.zip", self.plan, self.binding)

    def test_rejected_resume_and_torn_import_are_not_resumable(self):
        authoritative = self.evidence("parent")
        broken = FixtureBackend(after=lambda: (_ for _ in ()).throw(RuntimeError("fixture stop")))
        with self.assertRaises(RuntimeError):
            self.run_it(authoritative, broken)
        parent = self.root / "parent.zip"
        ct1_run.checkpoint_results(authoritative, parent, self.plan, self.binding)
        before = sha(parent)
        real_restore = ct1_run.restore
        for scenario in ("bad-seal", "interrupted"):
            job = self.root / scenario
            root = job / "evidence"
            root.mkdir(parents=True)
            write(root / "identity.json", self.binding)
            write(root / "config-summary.json", {"mode": "pilot"})
            digest = "0" * 64 if scenario == "bad-seal" else before

            def restore_with_cut(archive, expected, staging, binding):
                if scenario == "bad-seal":
                    return real_restore(archive, expected, staging, binding)
                write_bytes(staging / "calls/000/intent.json", b"{")
                raise OSError("fixture interrupted import")

            with patch.object(controller, "mount_path", return_value=parent), \
                 patch.object(ct1_run, "restore", side_effect=restore_with_cut):
                with self.assertRaises((ValueError, OSError)):
                    controller.admit_lineage(job, root, {"path": str(parent), "sha256": digest},
                                             self.plan, self.binding)
            self.assertFalse((root / "calls").exists())
            diagnostic = job / "diagnostic.zip"
            controller.export_job(root, diagnostic, self.plan, self.binding, "pilot")
            self.assertNotIn("runs.json", verify_archive(diagnostic))
            with self.assertRaisesRegex(ValueError, "RESUME_NOT_ADMITTED"):
                real_restore(diagnostic, sha(diagnostic), job / "unexpected", self.binding)
        self.assertEqual(sha(parent), before)

    def test_atomic_journal_cut_points_export_and_do_not_repeat_call(self):
        for record in ("intent", "tokens", "raw", "result"):
            with self.subTest(record=record):
                out = self.evidence(record)
                real_write = ct1_run.write_bytes

                def torn_write(path, payload):
                    if path.name.startswith(f".{record}.json."):
                        real_write(path, b"{")
                        raise RuntimeError("fixture torn write")
                    return real_write(path, payload)

                with patch.object(ct1_run, "write_bytes", side_effect=torn_write):
                    with self.assertRaisesRegex(RuntimeError, "torn write"):
                        self.run_it(out, FixtureBackend())
                self.assertFalse((out / "calls/000" / f"{record}.json").exists())
                archive = self.root / f"cut-{record}.zip"
                ct1_run.checkpoint_results(out, archive, self.plan, self.binding)
                members = verify_archive(archive)
                self.assertTrue(any(f"/.{record}.json." in m for m in members))
                recovered = self.evidence(f"recovered-{record}")
                ct1_run.restore(archive, sha(archive), recovered, self.binding)
                backend = FixtureBackend()
                self.run_it(recovered, backend)
                self.assertEqual(len(backend.calls), 143)
                if record in ("raw", "result"):
                    self.assertTrue((recovered / "calls/000/raw.json").is_file())

    def test_corrupt_published_record_exports_forensic_only(self):
        root = self.evidence("corrupt")
        write_bytes(root / "calls/000/intent.json", b"{")
        archive = self.root / "corrupt.zip"
        controller.export_job(root, archive, self.plan, self.binding, "pilot")
        members = verify_archive(archive)
        self.assertIn("calls/000/intent.json", members)
        self.assertIn("journal-export-failure.json", members)
        self.assertNotIn("runs.json", members)
        with self.assertRaisesRegex(ValueError, "FORENSIC_ARCHIVE_NOT_RESUMABLE"):
            ct1_run.restore(archive, sha(archive), self.root / "forbidden", self.binding)

    def test_observed_driver_changes_checkpoint_identity(self):
        cfg = {"source_commit": "a" * 40, "approved_drivers": ["570.26", "570.27"],
               "observed_driver": "570.26", "plan_sha256": self.plan_sha,
               "software_marker_sha256": "c" * 64, "source_capsule_sha256": "b" * 64,
               "run_id": "ct1-000000000000"}
        first = controller.binding(cfg, {})
        second = controller.binding({**cfg, "observed_driver": "570.27"}, {})
        self.assertNotEqual(first, second)

    def test_render_owner_notebook_is_exact_and_requires_seals(self):
        settings = {"source": "/kaggle/input/source", "source_commit": "a" * 40,
                    "source_zip_sha256": "b" * 64, "owner": {
                        "run_id": "ct1-000000000000", "pilot_input": "/kaggle/input/images",
                        "plan_sha256": self.plan_sha, "checkpoint": "/kaggle/input/checkpoint",
                        "software_input": "/kaggle/input/software",
                        "software_marker_sha256": "c" * 64, "approved_drivers": [], "resume": None}}
        for mode in ("pilot", "preflight"):
            payload = nb.content(mode, settings)
            self.assertEqual(payload, nb.content(mode, settings))
            row = next(c for c in json.loads(payload)["cells"] if c["id"] == "owner-settings")
            env = {}
            exec("".join(row["source"]), env)
            self.assertEqual(env["OWNER"], settings["owner"])
            self.assertEqual(env["SOURCE_COMMIT"], settings["source_commit"])
        with self.assertRaisesRegex(ValueError, "sealed source"):
            nb.content("pilot", {**settings, "source_zip_sha256": ""})

    def test_source_and_native_share_pixel_envelope(self):
        for size in ((2560, 1440), (1440, 2560), (720, 406)):
            self.assertTrue(ct1_native.image_size_allowed(size))
        for size in ((2336, 1752), (2561, 900), (0, 500)):
            self.assertFalse(ct1_native.image_size_allowed(size))

    def test_driver_and_resource_configuration(self):
        with self.assertRaises(ValueError):
            ct1_native.release_budgets([])
        policy = ct1_native.release_budgets(["570.26"])
        self.assertEqual(policy["free_mib_per_gpu"], [13000, 13000])
        self.assertEqual(controller.WALL_SECONDS, 10800)
        self.assertEqual(ct1_native.MAX_NEW, 768)
        self.assertEqual(ct1_native.MAX_INPUT, 4800)

    def test_notebooks_are_deterministic_and_share_bootstrap(self):
        preflight, pilot = (json.loads(nb.content(mode)) for mode in ("preflight", "pilot"))
        self.assertEqual(preflight["cells"][-1]["source"], pilot["cells"][-1]["source"])
        for n, book in ((nb.PREFLIGHT, preflight), (nb.PILOT, pilot)):
            self.assertEqual(json.loads((nb.ROOT / "notebooks" / n).read_bytes()), book)
            code = [c for c in book["cells"] if c["cell_type"] == "code"]
            for cell in code:
                compile("".join(cell["source"]), cell["id"], "exec")


if __name__ == "__main__":
    unittest.main()
