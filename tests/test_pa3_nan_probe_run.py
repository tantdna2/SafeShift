"""DEC-PA3-009 authority, four-prefill budget, durable journal and crash recovery.

CPU only: temporary Git repositories, synthetic images and API doubles. Never
loads a model, reads the dataset, touches GPU or grants anything.
"""

from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.pa3.artifacts import json_bytes, receipt
from safeshift.pa3.native import nan_probe_run as r
from safeshift.pa3.native.journal import run_path

ROOT = Path(__file__).resolve().parents[1]
INV = "b" * 64
GRANT = {"approval": "synthetic test approval, not a Research Lead record", "decision": "DEC-PA3-009",
         "runtime_inventory_sha256": INV}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                                    "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
                                   stderr=subprocess.STDOUT).decode().strip()


def authority(base=None, implementation=None, grant=None, scope=None):
    return json.dumps({"base": base, "implementation": implementation, "grant": grant,
                       "scope": r.SCOPE if scope is None else scope}, indent=2, sort_keys=True) + "\n"


class Repo:
    """B (Draft, null grant) -> F1 (code) -> F2 (authority only) -> standard merge M."""

    def __init__(self, f2_grant=GRANT, f2_scope=None, f2_extra=None):
        self.path = Path(tempfile.mkdtemp())
        p = self.path
        git(p, "init", "-q", "-b", "main")
        for prior in r.PRIOR_AUTHORITIES:
            self.write(prior, (ROOT / prior).read_text(encoding="utf-8"))
        self.write(r.AUTHORITY, authority(base="0" * 40))
        self.write("DECISIONS.md", "# Decision log\n\nDEC-PA3-009 status: PROPOSED_NOT_APPROVED\n")
        self.write("safeshift/probe.py", "VERSION = 0\n")
        self.base = self.commit("B")
        git(p, "checkout", "-q", "-b", "release")
        self.write("safeshift/probe.py", "VERSION = 1\n")
        self.f1 = self.commit("F1")
        self.write(r.AUTHORITY, authority(self.base, self.f1, f2_grant, f2_scope))
        if f2_extra:
            self.write(*f2_extra)
        self.f2 = self.commit("F2")
        git(p, "checkout", "-q", "main")
        git(p, "merge", "-q", "--no-ff", "-m", "M", "release")
        self.merge = git(p, "rev-parse", "HEAD")

    def write(self, name, text):
        path = self.path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def commit(self, message):
        git(self.path, "add", "-A")
        git(self.path, "commit", "-q", "-m", message)
        return git(self.path, "rev-parse", "HEAD")


@contextmanager
def anchored(repo, source=None):
    with patch.object(r, "NAN_BASE", repo.base), \
            patch.object(r.preflight, "source", source or (lambda path, sha: {"source_commit": sha})):
        yield


class AuthorityTests(unittest.TestCase):
    def test_positive_control_standard_release_passes(self):
        repo = Repo()
        calls = []
        with anchored(repo, lambda path, sha: calls.append(sha) or {"source_commit": sha}):
            proof = r.require_authority(repo.path, repo.merge, INV)
        self.assertEqual(proof["authority"]["grant"], GRANT)
        self.assertEqual(calls, [repo.merge])  # committed-bytes/untracked-shadow proof runs too

    def test_committed_draft_denies_before_any_git_model_journal_or_data_access(self):
        self.assertIsNone(json.loads((ROOT / r.AUTHORITY).read_text(encoding="utf-8"))["grant"])
        for mode in (["--launch"], ["--snapshot", "s", "--dataset-root", "d"]):  # parent and child
            with self.subTest(mode=mode), patch.object(r.preflight, "git") as git_call, \
                    patch.object(r, "launch") as launch, patch.object(r, "run") as run, \
                    patch("safeshift.ls1.runtime.NativeScorer") as scorer, \
                    patch("safeshift.ls1.experiment.open_sample") as opened, \
                    self.assertRaisesRegex(PermissionError, "GRANT_PENDING"):
                r.main(["--repo", str(ROOT), "--source-commit", "a" * 40,
                        "--runtime-inventory-sha256", INV, *mode])
            for mock in (git_call, launch, run, scorer, opened):
                mock.assert_not_called()
        self.assertFalse(run_path(ROOT, r.RUN_ID).exists())

    def test_decisions_text_or_local_edits_cannot_self_grant(self):
        repo = Repo()
        git(repo.path, "checkout", "-q", repo.base)  # Draft source, null grant
        repo.write("DECISIONS.md", "DEC-PA3-009 status: APPROVED_FOR_NAN_LOCALIZATION\n"
                                   "DEC-PA3-009 grant: APPROVED\n")
        sha = repo.commit("edit decisions")
        with anchored(repo), self.assertRaisesRegex(PermissionError, "GRANT_PENDING"):
            r.require_authority(repo.path, sha, INV)
        # Writing a grant locally (uncommitted) or as an ordinary commit is not a release.
        repo.write(r.AUTHORITY, authority(repo.base, repo.f1, GRANT))
        with anchored(repo), self.assertRaisesRegex(PermissionError, "STANDARD_MERGE_REQUIRED"):
            r.require_authority(repo.path, sha, INV)
        plain = repo.commit("self grant")
        with anchored(repo), self.assertRaisesRegex(PermissionError, "STANDARD_MERGE_REQUIRED"):
            r.require_authority(repo.path, plain, INV)

    def test_wrong_source_or_dirty_tree_or_binding_denies(self):
        repo = Repo()
        with anchored(repo):
            for sha in (repo.f2, repo.base, "c" * 40, None):
                with self.subTest(sha=sha), self.assertRaisesRegex(PermissionError, "STANDARD_MERGE_REQUIRED"):
                    r.require_authority(repo.path, sha, INV)
            with self.assertRaisesRegex(PermissionError, "BINDING"):
                r.require_authority(repo.path, repo.merge, "c" * 64)
            repo.write("safeshift/probe.py", "VERSION = 2\n")
            with self.assertRaisesRegex(PermissionError, "DIRTY_SOURCE"):
                r.require_authority(repo.path, repo.merge, INV)
            git(repo.path, "checkout", "--", "safeshift/probe.py")
            text = (repo.path / r.AUTHORITY).read_text(encoding="utf-8")
            repo.write(r.AUTHORITY, text.replace("synthetic test approval", "edited approval"))
            with self.assertRaisesRegex(PermissionError, "BYTES_CHANGED"):
                r.require_authority(repo.path, repo.merge, INV)
        with anchored(repo, lambda path, sha: (_ for _ in ()).throw(ValueError("UNTRACKED_EXECUTION_INPUT"))):
            git(repo.path, "checkout", "--", r.AUTHORITY)
            with self.assertRaisesRegex(PermissionError, "SOURCE_PROOF_MISSING"):
                r.require_authority(repo.path, repo.merge, INV)

    def test_release_may_change_only_the_authority_file(self):
        repo = Repo(f2_extra=("safeshift/probe.py", "VERSION = 99\n"))
        with anchored(repo), self.assertRaisesRegex(PermissionError, "AUTHORITY_ONLY"):
            r.require_authority(repo.path, repo.merge, INV)

    def test_added_replaced_or_resha_images_deny(self):
        extra = dict(r.SAMPLES[0], sample_id="power-Level04-Wheeled-001764-003")
        scopes = {"added": [*r.SCOPE["samples"], extra],
                  "replaced": [extra, r.SCOPE["samples"][1]],
                  "sha_swapped": [dict(r.SAMPLES[0], image_sha256=r.SAMPLES[1]["image_sha256"]),
                                  dict(r.SAMPLES[1], image_sha256=r.SAMPLES[0]["image_sha256"])],
                  "budget": None}
        for name, samples in scopes.items():
            scope = deepcopy(r.SCOPE)
            if samples is None:
                scope["max_prefills"] = 5
            else:
                scope["samples"] = samples
            repo = Repo(f2_scope=scope)
            with self.subTest(name=name), anchored(repo), self.assertRaisesRegex(PermissionError, "SCOPE_CHANGED"):
                r.require_authority(repo.path, repo.merge, INV)

    def test_bad_grant_schema_denies(self):
        for grant in ({**GRANT, "decision": "DEC-PA3-007"}, {**GRANT, "approval": " "},
                      {**GRANT, "extra": True}, {**GRANT, "runtime_inventory_sha256": "B" * 64}):
            repo = Repo(f2_grant=grant)
            with self.subTest(grant=grant), anchored(repo), self.assertRaisesRegex(PermissionError, "GRANT_SCHEMA"):
                r.require_authority(repo.path, repo.merge, INV)


class ImageScopeTests(unittest.TestCase):
    def test_only_pinned_triplets_and_hash_before_decode(self):
        root = Path(tempfile.mkdtemp())
        for bad in (dict(r.SAMPLES[0], sample_id="other"), dict(r.SAMPLES[0], image_sha256="0" * 64),
                    dict(r.SAMPLES[0], image_locator="DATA_PATH/test/x.jpg"),
                    {"sample_id": "x", "image_locator": "DATA_PATH/train/x.jpg", "image_sha256": "0" * 64}):
            with self.subTest(bad=bad), self.assertRaisesRegex(PermissionError, "OUTSIDE_SCOPE"):
                r.open_authorized(bad, root)
        path = root / r.SAMPLES[0]["image_locator"]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"swapped bytes")  # pinned name, wrong content
        with patch("PIL.Image.open") as decoded, self.assertRaisesRegex(ValueError, "IMAGE_CHANGED"):
            r.open_authorized(r.SAMPLES[0], root)
        decoded.assert_not_called()


class FakeImage:
    def __init__(self, sample):
        self.sample = sample

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_scorer():
    return SimpleNamespace(hardware={"gpu_name": "CPU_DOUBLE"}, software={}, snapshot_receipt={})


def fake_raw(tag):
    data = tag.encode() * 4
    return {"dtype": "float32", "shape": [1, 1], "sha256": hashlib.sha256(data).hexdigest(),
            "base64": __import__("base64").b64encode(data).decode()}


def probe_double(crash_after=None, calls=None):
    """Return identical raw bytes per sample so the comparison is checkable."""
    calls = [] if calls is None else calls

    def probe(scorer, image, *, clamp):
        if crash_after is not None and len(calls) == crash_after:
            os._exit(137)  # hard stop: no except/finally, no seal, no package
        calls.append((image.sample["sample_id"], clamp))
        return {"localization": "NO_NONFINITE"}, fake_raw(image.sample["sample_id"])
    return probe


def journal_at(repo):
    return r.DurableJournal(run_path(repo, r.RUN_ID), create=True)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())

    def test_atomic_receipts_no_overwrite_and_stale_temp(self):
        journal = journal_at(self.repo)
        journal.write("x", {"a": 1})
        data = journal.path("x").read_bytes()
        side = json.loads(journal.path("x").with_suffix(".sha256.json").read_bytes())
        self.assertEqual(side, receipt(data))
        self.assertEqual(data, json_bytes({"a": 1}))
        self.assertEqual(list(journal.staging().iterdir()), [])
        with self.assertRaises(FileExistsError):
            journal.write("x", {"a": 2})
        self.assertEqual(journal.path("x").read_bytes(), data)
        (journal.staging() / "y.json.tmp").write_bytes(b"stale")
        with self.assertRaises(FileExistsError):
            journal.write("y", {"b": 1})
        self.assertFalse(journal.path("y").exists())
        journal.path("x").write_bytes(data.replace(b"1", b"2"))
        with self.assertRaisesRegex(ValueError, "CHECKSUM"):
            journal.read("x")

    def test_budget_order_and_exhaustion(self):
        journal = journal_at(self.repo)
        samples = {s["sample_id"]: s for s in r.SAMPLES}
        with self.assertRaisesRegex(PermissionError, "OUTSIDE_AUTHORIZED_PLAN"):
            r.begin_prefill(journal, 0, samples[r.PLAN[0][0]], "candidate_merger_clamp")
        with self.assertRaisesRegex(PermissionError, "OUTSIDE_AUTHORIZED_PLAN"):
            r.begin_prefill(journal, 1, samples[r.PLAN[1][0]], r.PLAN[1][1])
        for index, (sample_id, mode) in enumerate(r.PLAN):
            r.begin_prefill(journal, index, samples[sample_id], mode)
            if index == 1:  # repeating a started prefill mid-plan is refused, not retried
                with self.assertRaisesRegex(PermissionError, "OUTSIDE_AUTHORIZED_PLAN"):
                    r.begin_prefill(journal, 1, samples[sample_id], mode)
        for index in (4, 3, 0):
            with self.assertRaisesRegex(PermissionError, "BUDGET_EXHAUSTED"):
                r.begin_prefill(journal, index, samples[r.PLAN[0][0]], "baseline")
        self.assertEqual(len(r.PLAN), 4)

    def test_complete_run_uses_exactly_four_prefills_and_compares_bitwise(self):
        calls = []
        journal = journal_at(self.repo)
        r.execute(journal, fake_scorer, FakeImage, probe_double(calls=calls))
        self.assertEqual(calls, [(s, m != "baseline") for s, m in r.PLAN])
        self.assertEqual(journal.read("finish")["prefills"], 4)
        self.assertEqual(set(journal.read("comparison").values()), {True})
        with self.assertRaises(FileExistsError):  # second invocation never retries
            r.execute(journal, fake_scorer, FakeImage, probe_double())


class CrashTests(unittest.TestCase):
    CHILD = ("import sys; sys.path.insert(0, sys.argv[3]); from pathlib import Path;"
             "from safeshift.pa3.native import nan_probe_run as r;"
             "from tests.test_pa3_nan_probe_run import journal_at, fake_scorer, FakeImage, probe_double;"
             "r.execute(journal_at(Path(sys.argv[1])), fake_scorer, FakeImage, probe_double(int(sys.argv[2])))")

    def test_hard_stop_after_one_two_or_three_prefills_keeps_results_and_never_retries(self):
        for done in (1, 2, 3):
            with self.subTest(done=done):
                repo = Path(tempfile.mkdtemp())
                child = subprocess.run([sys.executable, "-c", self.CHILD, str(repo), str(done), str(ROOT)])
                self.assertEqual(child.returncode, 137)
                root = run_path(repo, r.RUN_ID)
                before = {p.name: p.read_bytes() for p in root.iterdir()}
                report = r.recover(repo)
                statuses = [p["status"] for p in report["prefills"]]
                self.assertEqual(statuses, ["COMPLETE"] * done + ["INCOMPLETE_STARTED_NO_RESULT"]
                                 + ["NOT_STARTED"] * (3 - done))
                self.assertFalse(report["completed"] or report["sealed"] or report["retry_permitted"])
                self.assertTrue(all(v == "VALID" for v in report["files"].values()))
                self.assertEqual({p.name: p.read_bytes() for p in root.iterdir()}, before)  # never repaired
                archive = root.with_suffix(".tar.gz")
                side = json.loads(archive.with_suffix(".sha256.json").read_bytes())
                self.assertEqual(side["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
                if done >= 2:
                    self.assertIs(report["comparison"][r.SAMPLES[0]["sample_id"]], True)
                recovery = root.parent / (root.name + "-recovery.json")
                saved = recovery.read_bytes()
                r.recover(repo)  # idempotent: report and package are never overwritten
                self.assertEqual(recovery.read_bytes(), saved)
                with self.assertRaises(FileExistsError):
                    journal_at(repo)
                with self.assertRaises(FileExistsError):
                    r.execute(r.DurableJournal(root), fake_scorer, FakeImage, probe_double())

    def test_torn_result_and_staging_leftover_are_reported_not_repaired(self):
        repo = Path(tempfile.mkdtemp())
        journal = journal_at(repo)
        journal.write("model-load.attempt", {})
        sample = r.SAMPLES[0]
        r.begin_prefill(journal, 0, sample, "baseline")
        torn = journal.path("prefill-0.result")
        torn.write_bytes(b'{"partial":')  # payload without receipt
        (journal.staging() / "prefill-0.result.sha256.json.tmp").write_bytes(b"")
        report = r.recover(repo)
        self.assertEqual(report["prefills"][0]["status"], "INCOMPLETE_STARTED_INVALID_RESULT")
        self.assertIn("TORN_WRITE", report["files"]["prefill-0.result"])
        self.assertEqual(report["staging_leftovers"], ["prefill-0.result.sha256.json.tmp"])
        self.assertEqual(torn.read_bytes(), b'{"partial":')


class LaunchTests(unittest.TestCase):
    def args(self, repo):
        return SimpleNamespace(repo=repo, inputs="in", runtime_input="rt.tar", runtime_inventory_input="inv.json",
                               runtime_inventory_sha256=INV, runtime_site_packages=None, model_input="m.tar",
                               dataset_input="train", source_commit="d" * 40)

    def patched(self, calls, returncode):
        record = lambda name, value=None: (lambda *a, **k: calls.append(name) or value)
        return [patch("safeshift.ls1.kaggle.attached_path", side_effect=lambda root, rel: Path(root) / rel),
                patch("safeshift.ls1.kaggle.verify_runtime_input", record("verify")),
                patch("safeshift.ls1.kaggle.restore_model", record("restore", Path("snap"))),
                patch("safeshift.ls1.kaggle.runtime_interpreter",
                      record("runtime", {"python": "py", "site_packages": None})),
                patch.object(r.subprocess, "run", side_effect=lambda *a, **k: calls.append("child")
                             or subprocess.CompletedProcess([], returncode)),
                patch.object(r, "recover", record("recover"))]

    def test_runtime_verified_before_restore_one_child_rechecks_authority_then_recovery(self):
        repo = Path(tempfile.mkdtemp())
        (repo / r.RUNTIME_PLAN).parent.mkdir(parents=True)
        (repo / r.RUNTIME_PLAN).write_text("{}", encoding="utf-8")
        run_path(repo, r.RUN_ID).mkdir(parents=True)  # as if the child created its journal
        for returncode in (0, 1):
            calls = []
            mocks = self.patched(calls, returncode)
            with mocks[0], mocks[1], mocks[2], mocks[3], mocks[4] as run, mocks[5]:
                if returncode:
                    with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
                        r.launch(self.args(repo))
                else:
                    self.assertEqual(r.launch(self.args(repo)), 0)
            self.assertEqual(calls, ["verify", "restore", "runtime", "child", "recover"])
            command, kwargs = run.call_args.args[0], run.call_args.kwargs
            self.assertEqual(command[:4], ["py", "-s", "-m", "safeshift.pa3.native.nan_probe_run"])
            self.assertEqual(command[command.index("--source-commit") + 1], "d" * 40)
            self.assertEqual(command[command.index("--runtime-inventory-sha256") + 1], INV)
            self.assertNotIn("--launch", command)
            self.assertFalse(kwargs["check"])
            self.assertEqual((kwargs["env"]["HF_HUB_OFFLINE"], kwargs["env"]["CUDA_VISIBLE_DEVICES"]), ("1", "0"))

    def test_existing_run_denied_even_with_authority(self):
        repo = Path(tempfile.mkdtemp())
        run_path(repo, r.RUN_ID).mkdir(parents=True)
        with patch.object(r, "require_authority", return_value={}), patch.object(r, "launch") as launch, \
                self.assertRaisesRegex(FileExistsError, "NO_RETRY"):
            r.main(["--repo", str(repo), "--source-commit", "d" * 40, "--runtime-inventory-sha256", INV, "--launch"])
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
