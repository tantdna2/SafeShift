"""Synthetic owner preparation/restore/packaging tests; no model or dataset."""

import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import subprocess
from unittest.mock import patch
from types import SimpleNamespace

from safeshift.runners import p21_kaggle as owner


class KaggleP21Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def confirmation(self):
        return {"final_merge_sha": "a" * 40, "independent_audit": "PASS", "chatgpt_code_audit": "PASS",
                "research_lead_confirmed": True, "chatgpt_merge_main_verification": "PASS",
                "audit_evidence_reference": "synthetic audit", "merge_evidence_reference": "synthetic Git check"}

    def make_tar(self, name, items):
        path = self.root / name
        with tarfile.open(path, "w:gz") as archive:
            for filename, raw in items:
                item = tarfile.TarInfo(filename)
                if isinstance(raw, str):
                    item.type = tarfile.SYMTYPE
                    item.linkname = raw
                    archive.addfile(item)
                else:
                    item.size = len(raw)
                    archive.addfile(item, io.BytesIO(raw))
        return path

    def test_external_gates_and_sha_fail_closed(self):
        self.assertEqual(owner.validate_confirmation(self.confirmation()), self.confirmation())
        for key in ("independent_audit", "chatgpt_code_audit", "research_lead_confirmed", "chatgpt_merge_main_verification"):
            value = self.confirmation()
            value[key] = False
            with self.assertRaises(PermissionError):
                owner.validate_confirmation(value)
        for value in ("", "b" * 39, "B" * 40, "main"):
            confirmation = self.confirmation()
            confirmation["final_merge_sha"] = value
            with self.assertRaises(ValueError):
                owner.validate_confirmation(confirmation)

    def test_source_verification_requires_effective_v4_and_exact_confirmed_sha(self):
        from safeshift.runners.p21_authority import SCHEMA
        authority = {"schema_version": SCHEMA, "model_key": "internvl3"}
        with patch("safeshift.runners.p2_harness.authorize_production", return_value=("a" * 40, authority)):
            self.assertEqual(owner.verify_source(self.root, self.confirmation()), "a" * 40)
            confirmation = self.confirmation()
            confirmation["final_merge_sha"] = "b" * 40
            with self.assertRaises(PermissionError):
                owner.verify_source(self.root, confirmation)
        with patch("safeshift.runners.p2_harness.authorize_production", side_effect=PermissionError("DRAFT")):
            with self.assertRaises(PermissionError):
                owner.verify_source(self.root, self.confirmation())

    def test_archive_rejects_escape_before_extraction(self):
        for index, entries in enumerate(([('ok', b'x'), ('../escape', b'y')], [('bin/python', '/outside/python')])):
            archive = self.make_tar(str(index) + ".tgz", entries)
            destination = self.root / ("out" + str(index))
            with self.assertRaises(ValueError):
                owner.safe_extract(archive, destination)
            self.assertFalse((self.root / "escape").exists())
            self.assertFalse((destination / "ok").exists())

    def test_runtime_skips_external_venv_link_preserves_regular_bytes(self):
        archive = self.make_tar("runtime.tgz", [("venv/bin/python", "/old/managed/python"),
                                                ("managed/bin/python3.11", b"exact executable"),
                                                ("venv/lib/python3.11/site-packages/pinned.py", b"exact package")])
        restored = owner.safe_extract(archive, self.root / "runtime", skip_external_runtime_links=True)
        self.assertFalse((restored / "venv/bin/python").exists())
        self.assertEqual((restored / "managed/bin/python3.11").read_bytes(), b"exact executable")
        self.assertEqual((restored / "venv/lib/python3.11/site-packages/pinned.py").read_bytes(), b"exact package")

    def test_historical_manifest_and_status_actual_bytes_hash_checked_and_unchanged(self):
        inputs = self.root / "input"
        inputs.mkdir()
        manifest, status = b'{"run_id":"synthetic-old"}\n', b'{"status":"COMPLETED"}\n'
        (inputs / "run_manifest.json").write_bytes(manifest)
        (inputs / "run_status.json").write_bytes(status)
        with patch.object(owner, "OLD_MANIFEST", hashlib.sha256(manifest).hexdigest()), \
                patch.object(owner, "OLD_STATUS", hashlib.sha256(status).hexdigest()):
            restored = owner.restore_history(self.root / "repo", inputs)
        self.assertEqual((restored / "run_manifest.json").read_bytes(), manifest)
        self.assertEqual((restored / "run_status.json").read_bytes(), status)
        with self.assertRaises(ValueError):
            owner.restore_history(self.root / "wrong", inputs)

    def test_historical_archive_restores_actual_bytes_without_full_result_extraction(self):
        manifest, status = b"manifest exact\r\n", b"status exact\r\n"
        archive = self.make_tar("results.tgz", [("previous/run_manifest.json", manifest),
                                               ("previous/run_status.json", status), ("ignored/response.raw", b"private")])
        with patch.object(owner, "OLD_MANIFEST", hashlib.sha256(manifest).hexdigest()), \
                patch.object(owner, "OLD_STATUS", hashlib.sha256(status).hexdigest()):
            restored = owner.restore_history(self.root / "repo", self.root, archive.name)
        self.assertEqual((restored / "run_manifest.json").read_bytes(), manifest)
        self.assertFalse((restored / "response.raw").exists())

    def test_packages_100_percent_invalid_and_failed_runs(self):
        for state, samples in (("COMPLETED", {str(i): "INVALID" for i in range(1254)}),
                               ("FAILED", {str(i): ("FAILED" if i == 0 else "NOT_ATTEMPTED") for i in range(1254)})):
            repo = self.root / state
            run = repo / "data/processed/benchmark/p2/internvl3" / owner.RUN_ID
            run.mkdir(parents=True)
            (run / "run_status.json").write_text(json.dumps({"status": state, "samples": samples, "failure": None}))
            (run / "response.raw").write_bytes(b"```json\n{}\n```\r\n")
            summary = owner.package_result(repo, repo / "package")
            self.assertEqual(summary["execution_status"], state)
            self.assertTrue(summary["zero_canonical_yield"])
            self.assertTrue(summary["stop_before_shards_1_3"])
            self.assertEqual(sum(summary[k] for k in owner.STATUSES), 1254)
            with tarfile.open(repo / "package" / (owner.RUN_ID + "_results.tar.gz")) as archive:
                self.assertEqual(archive.extractfile("run/" + owner.RUN_ID + "/response.raw").read(), b"```json\n{}\n```\r\n")

    def test_unknown_partial_status_is_not_fabricated(self):
        run = self.root / "partial"
        run.mkdir()
        value = owner.result_summary(run)
        self.assertFalse(value["sample_accounting_known"])
        self.assertIsNone(value["SUCCESS"])
        self.assertIsNone(value["zero_canonical_yield"])
        self.assertTrue(value["stop_before_shards_1_3"])

    def test_failure_before_history_stops_without_model_dataset_or_launch_and_packages(self):
        repo = self.root / "repo"
        (repo / owner.RECEIPT).parent.mkdir(parents=True)
        (repo / owner.RECEIPT).write_text(json.dumps({"confirmation": self.confirmation()}))
        settings = {"final_merge_sha": "a" * 40, "kaggle_internet_off_confirmed": True}
        with patch.object(owner, "verify_source"), \
                patch("safeshift.runners.p2_preflight.static_preflight", return_value={"effective_authorization": True, "models": ["internvl3"]}), \
                patch.object(owner, "restore_history", side_effect=ValueError("MISSING_PRIOR")), \
                patch.object(owner, "restore_model") as model, patch.object(owner, "locate_dataset") as dataset, \
                patch.object(owner.subprocess, "Popen") as launch:
            summary = owner.run_offline(repo, self.root, settings, self.root / "result")
        model.assert_not_called()
        dataset.assert_not_called()
        launch.assert_not_called()
        self.assertEqual(summary["NOT_ATTEMPTED"], 1254)
        self.assertEqual(summary["failure"]["message"], "MISSING_PRIOR")
        self.assertTrue((self.root / "result" / (owner.RUN_ID + "_results.tar.gz")).is_file())

    def test_production_child_calls_only_once_with_fixed_shard0_identity(self):
        repo = self.root / "repo"
        (repo / owner.RECEIPT).parent.mkdir(parents=True)
        (repo / owner.RECEIPT).write_text(json.dumps({"confirmation": self.confirmation()}))
        with patch.object(owner, "verify_source"), \
                patch("safeshift.runners.p2_harness.production_run", side_effect=ValueError("generation failure")) as call:
            with self.assertRaises(ValueError):
                owner.production_child(repo, "synthetic", "manifest", "provenance")
        call.assert_called_once()
        self.assertEqual(call.call_args.kwargs["run_id"], owner.RUN_ID)
        self.assertEqual((call.call_args.kwargs["shard_count"], call.call_args.kwargs["shard_index"]), (4, 0))

    def test_runtime_reuses_managed_python_and_unchanged_sites_metadata_only(self):
        runtime = self.root / "runtime"
        python = runtime / "managed/bin/python3.11"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"synthetic bundled executable")
        site = runtime / "venv/lib/python3.11/site-packages"
        site.mkdir(parents=True)
        marker = site / "torch_metadata_fixture"
        marker.write_bytes(b"unchanged package metadata fixture")
        expected = {"python": "3.11.11", "torch": "2.6.0+cu124"}
        calls = []

        def probe(command, **kwargs):
            calls.append((command, kwargs))
            self.assertNotIn("import torch", command[2])
            self.assertIn("importlib.metadata", command[2])
            valid = kwargs["env"].get("PYTHONPATH") == str(site)
            return SimpleNamespace(returncode=0 if valid else 2, stdout=json.dumps(expected))

        with patch("safeshift.runners.internvl3_snapshot.load_plan", return_value={"software": expected}), \
                patch.object(owner.subprocess, "run", side_effect=probe):
            value = owner.runtime_interpreter(self.root / "repo", runtime)
        self.assertEqual(value["python"], str(python))
        self.assertEqual(value["site_packages"], str(site))
        self.assertTrue(all(item[1]["env"]["CUDA_VISIBLE_DEVICES"] == "0" for item in calls))
        self.assertEqual(marker.read_bytes(), b"unchanged package metadata fixture")

    def test_multiple_matching_site_trees_fail_without_explicit_selection(self):
        runtime = self.root / "runtime"
        python = runtime / "managed/bin/python3.11"
        python.parent.mkdir(parents=True)
        python.write_bytes(b"synthetic executable")
        sites = [runtime / name / "lib/python3.11/site-packages" for name in ("venv-a", "venv-b")]
        for site in sites:
            site.mkdir(parents=True)
        expected = {"python": "3.11.11"}
        def probe(command, **kwargs):
            return SimpleNamespace(returncode=0 if kwargs["env"].get("PYTHONPATH") else 2,
                                   stdout=json.dumps(expected))
        with patch("safeshift.runners.internvl3_snapshot.load_plan", return_value={"software": expected}), \
                patch.object(owner.subprocess, "run", side_effect=probe):
            with self.assertRaisesRegex(ValueError, "AMBIGUOUS_EXACT_RUNTIME"):
                owner.runtime_interpreter(self.root / "repo", runtime)
            value = owner.runtime_interpreter(self.root / "repo", runtime, site_packages=sites[1])
        self.assertEqual(value["site_packages"], str(sites[1]))

    def test_source_archive_includes_full_local_git_excludes_untracked_model_and_data(self):
        repo = self.root / "source"
        repo.mkdir()
        (repo / "README.md").write_text("synthetic source\n")
        subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
        for name, value in (("user.name", "Synthetic Test"), ("user.email", "synthetic@example.invalid")):
            subprocess.run(["git", "-C", str(repo), "config", name, value], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "synthetic source"], check=True, capture_output=True)
        head = owner.git(repo, "rev-parse", "HEAD")
        (repo / "untracked_model.bin").write_bytes(b"synthetic excluded model marker")
        with patch.object(owner, "verify_source", return_value=head):
            metadata = owner.prepare_source(repo, self.confirmation(), self.root / "source-output")
        archive = self.root / "source-output" / metadata["archive"]
        self.assertEqual(owner.digest_file(archive), metadata["archive_sha256"])
        restored = owner.safe_extract(archive, self.root / "source-restored") / "SafeShift"
        self.assertEqual(owner.git(restored, "rev-parse", "HEAD"), head)
        self.assertEqual(owner.git(restored, "show", "HEAD:README.md"), "synthetic source")
        self.assertFalse((restored / "untracked_model.bin").exists())
        self.assertTrue((restored / owner.RECEIPT).is_file())

    def test_source_archive_rejects_shared_object_store(self):
        repo = self.root / "shared-source"
        (repo / ".git/objects/info").mkdir(parents=True)
        (repo / ".git/objects/info/alternates").write_text("external fixture path")
        with patch.object(owner, "verify_source", return_value="a" * 40), patch.object(owner, "git", return_value="false"):
            with self.assertRaisesRegex(ValueError, "EXTERNAL_OR_PROMISOR"):
                owner.prepare_source(repo, self.confirmation(), self.root / "package")

    def test_full_offline_launch_once_packages_success_invalid_and_failed(self):
        for state in ("success", "invalid", "failed"):
            repo = self.root / state
            (repo / owner.RECEIPT).parent.mkdir(parents=True)
            (repo / owner.RECEIPT).write_text(json.dumps({"confirmation": self.confirmation()}))
            old = repo / "old"
            old.mkdir()
            (old / "run_manifest.json").write_bytes(b"synthetic manifest")
            (old / "run_status.json").write_bytes(b"synthetic status")
            runtime = {"python": str(repo / "synthetic-python"), "site_packages": str(repo / "synthetic-site"), "software_versions": {}}

            def launch(command, **kwargs):
                self.assertEqual(command[0], runtime["python"])
                self.assertEqual(kwargs["env"]["CUDA_VISIBLE_DEVICES"], "0")
                self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
                self.assertEqual(kwargs["env"]["PYTHONPATH"], str(repo) + owner.os.pathsep + runtime["site_packages"])
                run = repo / "data/processed/benchmark/p2/internvl3" / owner.RUN_ID
                run.mkdir(parents=True)
                samples = {str(i): "INVALID" for i in range(1254)}
                if state == "success":
                    samples["0"] = "SUCCESS"
                elif state == "failed":
                    samples = {str(i): ("FAILED" if i == 0 else "NOT_ATTEMPTED") for i in range(1254)}
                (run / "run_status.json").write_text(json.dumps({"samples": samples,
                    "status": "FAILED" if state == "failed" else "COMPLETED", "failure": None}))
                return SimpleNamespace(stdout=io.StringIO("synthetic child log\n"), wait=lambda: 2 if state == "failed" else 0)

            with patch.object(owner, "verify_source"), \
                    patch("safeshift.runners.p2_preflight.static_preflight", return_value={"effective_authorization": True, "models": ["internvl3"]}), \
                    patch.object(owner, "restore_history", return_value=old), \
                    patch("safeshift.runners.p2_harness.authorize_production", return_value=("a" * 40, {})), \
                    patch("safeshift.runners.p21_authority.verify_lineage"), \
                    patch.object(owner, "attachment", return_value=self.root), \
                    patch.object(owner, "restore_model", return_value={}), \
                    patch.object(owner, "runtime_interpreter", return_value=runtime), \
                    patch.object(owner, "locate_dataset", return_value=("synthetic-dataset", "manifest", "provenance")), \
                    patch.object(owner.subprocess, "Popen", side_effect=launch) as child:
                value = owner.run_offline(repo, self.root, {"final_merge_sha": "a" * 40,
                    "kaggle_internet_off_confirmed": True}, repo / "output")
            child.assert_called_once()
            self.assertEqual(value["stop_before_shards_1_3"], state != "success")
            self.assertEqual(value["zero_canonical_yield"], state != "success")
            self.assertTrue((repo / "output" / (owner.RUN_ID + "_results.tar.gz")).is_file())
            self.assertIn("synthetic child log", (repo / "output/production_child.log").read_text())
            receipt = json.loads((repo / "data/processed/p21_kaggle/launch_receipt.json").read_text())
            self.assertEqual(receipt["runtime"]["path_base"], "REPOSITORY_ROOT")
            self.assertFalse(Path(receipt["runtime"]["python"]).is_absolute())
            self.assertFalse(Path(receipt["runtime"]["site_packages"]).is_absolute())

    def test_notebooks_compile_and_have_required_production_metadata(self):
        root = Path(__file__).resolve().parents[1]
        for stage in ("source_prep", "shard0"):
            path = root / "notebooks" / ("w2_internvl3_p21_" + stage + "_kaggle.ipynb")
            notebook = json.loads(path.read_text(encoding="utf-8"))
            for i, cell in enumerate(notebook["cells"]):
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), str(path) + ":" + str(i), "exec")
            self.assertEqual(notebook["metadata"]["kaggle"]["isInternetEnabled"], stage == "source_prep")
            self.assertEqual(notebook["metadata"]["safeshift"]["production_attempts"], 0 if stage == "source_prep" else 1)
            if stage == "shard0":
                self.assertEqual(notebook["metadata"]["kaggle"]["accelerator"], "nvidiaTeslaT4")

    def test_notebook_bootstrap_failure_packages_without_helper_or_model_access(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "notebooks/w2_internvl3_p21_shard0_kaggle.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        code = "".join(next(cell["source"] for cell in notebook["cells"]
                            if cell["cell_type"] == "code" and "# Single Run All" in "".join(cell["source"])))
        settings = {"final_merge_sha": "", "kaggle_internet_off_confirmed": False}
        with patch.object(Path, "cwd", return_value=self.root):
            exec(compile(code, "offline-bootstrap-synthetic", "exec"), {"SETTINGS": settings})
        output = self.root / "internvl3_p21_shard0_output"
        summary = json.loads((output / "owner_result_summary.json").read_text())
        self.assertEqual(summary["execution_status"], "BOOTSTRAP_FAILED_NO_PRODUCTION_CALL")
        self.assertEqual(summary["NOT_ATTEMPTED"], 1254)
        self.assertTrue((output / (owner.RUN_ID + "_results.tar.gz")).is_file())


if __name__ == "__main__":
    unittest.main()
