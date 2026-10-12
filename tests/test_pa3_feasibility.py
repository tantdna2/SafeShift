"""Task 5 CPU/synthetic tests. No downloads, GPU or InspecSafe access."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pa3.native import access, pilot, prep, workflow, preflight
from safeshift.pa3.native.journal import Journal, run_path
from safeshift.pa3.artifacts import json_bytes
from safeshift.ls1.experiment import synthetic_samples

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = {"mode": "technical", "run_id": access.TECHNICAL["run_id"], "source_commit": "a"*40}


def inventory():
    rows = []
    for domain in pilot.DOMAINS:
        for label in ("Level04", "Level01"):
            for i in range(6):
                sid = domain + "-" + label + "-" + str(i)
                rows.append({"sample_id": sid, "split": "TRAIN", "image_locator": "train/" + sid + ".png",
                    "image_sha256": hashlib.sha256(sid.encode()).hexdigest(), "level": label,
                    "domain": domain, "point_id": sid, "exposure": "unseen",
                    "exposure_source": "synthetic-ledger", "gt_source": "synthetic-original-label",
                    "metadata_source": "synthetic-inventory", "test_link": "none_verified"})
    return rows


class AuthorityTests(unittest.TestCase):
    def test_settings_and_receipts_do_not_authorize(self):
        for operation in ("technical", "pilot-train", "metadata", "images", "test", "train-dev", "train-holdout", "statistics"):
            with self.subTest(operation=operation), self.assertRaises(PermissionError):
                access.require(operation, {**SETTINGS, "approved": True, "receipt_sha256": "a"*64,
                                           "source_commit": access.BASE})

    def test_wrong_scope_denied_before_git_or_file_reads(self):
        with patch.object(access, "authority", side_effect=AssertionError("SOURCE_READ")):
            for change in ({"mode": "test"}, {"run_id": "pa3-qwen-retry"}, {"revision": "main"},
                           {"model": "InternVL3"}, {"precision": "BF16"}, {"dataset_input": "test"},
                           {"pilot_manifest_input": "train.json"}, {"cohort_plan_sha256": "a"*64}):
                with self.subTest(change=change), self.assertRaises(PermissionError):
                    access.require("technical", {**SETTINGS, **change})

    def test_real_git_draft_merge_dirty_and_source_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", "-C", tmp, *args], stderr=subprocess.DEVNULL).decode().strip()
            git("init", "-b", "main")
            git("config", "core.autocrlf", "false")
            git("config", "user.email", "fixture@example.invalid")
            git("config", "user.name", "CPU fixture")
            (repo/"code.txt").write_text("base")
            git("add", "."); git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "candidate")
            (repo/"code.txt").write_text("implementation")
            git("add", "."); git("commit", "-m", "F1")
            f1 = git("rev-parse", "HEAD")
            path = repo/access.AUTHORITY
            path.parent.mkdir(parents=True)
            path.write_bytes(json_bytes({"base": base, "implementation": f1,
                                         "technical": access.TECHNICAL, "pilot": None}))
            git("add", "."); git("commit", "-m", "F2")
            f2 = git("rev-parse", "HEAD")
            with patch.object(access, "BASE", base):
                with self.assertRaisesRegex(PermissionError, "DRAFT_LOCKED"):
                    access.authority(repo, f2)
                git("checkout", "main"); git("merge", "--no-ff", "candidate", "-m", "fixture merge")
                merge = git("rev-parse", "HEAD")
                self.assertEqual(access.authority(repo, merge)["implementation"], f1)
                with self.assertRaises(PermissionError): access.authority(repo, f2)
                with self.assertRaises(PermissionError):
                    access.require("pilot-train", {"mode": "pilot-train", "source_commit": merge}, repo)
                (repo/"code.txt").write_text("dirty")
                with self.assertRaisesRegex(PermissionError, "DIRTY"):
                    access.authority(repo, merge)
                git("add", "."); git("commit", "-m", "later source")
                with self.assertRaises(PermissionError): access.authority(repo, git("rev-parse", "HEAD"))

    def test_approved_pilot_binding_is_not_caller_authority(self):
        grant = {k: v for k, v in access.TECHNICAL.items() if k not in {"mode", "max_images"}}
        grant.update(run_id="pa3-qwen-pilot-train-first", max_images=40, approval="LEAD-REVIEW-FIXTURE",
                     pilot_manifest_sha256="a"*64, technical_seal_sha256="b"*64,
                     technical_source_commit="c"*40, technical_source_bundle_sha256="d"*64)
        s = {**grant, "mode": "pilot-train", "source_commit": "e"*40}
        with patch.object(access, "authority", return_value={"pilot": grant}):
            self.assertEqual(access.require("pilot-train", s)["pilot"], grant)
            for key in ("run_id", "pilot_manifest_sha256", "technical_seal_sha256", "technical_source_commit"):
                with self.subTest(key=key), self.assertRaises(PermissionError):
                    access.require("pilot-train", {**s, key: "wrong"})


class ImageBoundaryTests(unittest.TestCase):
    def test_one_model_load_attempt_and_workflow_required(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, "require"):
            with self.assertRaises(PermissionError): access.model_ticket(tmp, SETTINGS)
            Journal(run_path(tmp, SETTINGS["run_id"]), create=True)
            access.model_ticket(tmp, SETTINGS)
            with self.assertRaises(FileExistsError): access.model_ticket(tmp, SETTINGS)

    def test_exact_four_pixels_and_persistent_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, "require"):
            repo = Path(tmp)
            j = Journal(run_path(repo, SETTINGS["run_id"] + "-qualification"), create=True)
            rows = synthetic_samples()
            try:
                for i, row in enumerate(rows):
                    prefix = f"sample-{i:06d}"
                    j.write(prefix + ".attempt", {k: v for k,v in row.items() if k != "image"})
                    access.image_ticket(repo, SETTINGS, row["image"], j, prefix)
                    with self.assertRaises(FileExistsError): access.image_ticket(repo, SETTINGS, row["image"], j, prefix)
                with self.assertRaises(PermissionError): access.image_ticket(repo, SETTINGS, rows[0]["image"], j, "sample-000004")
                rows[0]["image"].putpixel((0,0), (0,0,0))
                with self.assertRaisesRegex(PermissionError, "SYNTHETIC_PIXELS"):
                    access.image_ticket(repo, SETTINGS, rows[0]["image"], j, "sample-000000")
            finally:
                for row in rows: row["image"].close()

    def test_denial_packages_before_any_protected_read(self):
        for mode in ("technical", "pilot-train", "test", "train-holdout"):
            with tempfile.TemporaryDirectory() as tmp, patch.object(preflight, "runtime", side_effect=AssertionError("MODEL_READ")):
                with self.assertRaises(PermissionError):
                    workflow.execute(tmp, {**SETTINGS, "mode": mode}, "never-read", "never-read")
                self.assertTrue(Journal(run_path(tmp, SETTINGS["run_id"])).verify())


class PilotTests(unittest.TestCase):
    def test_fixed_selection_balance_and_order_independence(self):
        rows = inventory()
        a, b = pilot.propose(rows, []), pilot.propose(list(reversed(rows)), [])
        self.assertEqual(a["selected_ids"], b["selected_ids"])
        self.assertEqual(len(a["selected_ids"]), 40)
        indexed = pilot.validate(a)
        self.assertEqual(sum(indexed[i]["level"] == "Level04" for i in a["selected_ids"]), 20)
        self.assertEqual(a["observed_ids"], sorted(a["selected_ids"]))
        altered = deepcopy(a); altered["selected_ids"].reverse()
        with self.assertRaises(ValueError): pilot.validate(altered)

    def test_exposed_unknown_test_relation_and_dependencies_quarantine(self):
        for field, value in (("exposure", "observed"), ("exposure", "unknown"), ("test_link", "unknown"), ("test_link", "observed_test")):
            rows = inventory()
            for r in rows[:3]: r[field] = value
            proposed = pilot.propose(rows, [])
            self.assertEqual(proposed["status"], "STOP_INSUFFICIENT_ELIGIBLE_GROUPS")
            self.assertEqual(proposed["selected_ids"], [])
            self.assertEqual(proposed["shortages"]["coal_conveyor/Normal"], 1)

    def test_duplicate_and_normal_point_groups_no_double_selection(self):
        rows = inventory()
        rows[1]["image_sha256"] = rows[0]["image_sha256"]
        rows[2]["point_id"] = rows[0]["point_id"]
        result = pilot.propose(rows, [])
        selected = set(result["selected_ids"])
        self.assertEqual(sum(r["sample_id"] in selected for r in rows[:3]), 1)
        self.assertTrue(set(r["sample_id"] for r in rows[:3]).issubset(result["observed_ids"]))

    def test_transitive_closure_and_unknown_link(self):
        rows = inventory()
        links = [{"a": rows[a]["sample_id"], "b": rows[b]["sample_id"], "kind": "sequence",
                  "review": "accepted", "evidence": "fixture"} for a,b in ((0,1),(1,2))]
        result = pilot.propose(rows, links)
        self.assertTrue(set(r["sample_id"] for r in rows[:3]).issubset(result["observed_ids"]))
        links[0]["review"] = "unresolved"
        self.assertEqual(pilot.propose(rows, links)["status"], "STOP_INSUFFICIENT_ELIGIBLE_GROUPS")

    def test_test_rows_and_missing_label_provenance_rejected(self):
        for key,value in (("split", "TEST"), ("gt_source", ""), ("image_locator", "../test/a.png"), ("domain", "invented")):
            rows = inventory(); rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): pilot.propose(rows, [])

    def test_real_helpers_deny_before_path_read(self):
        with patch.object(Path, "read_bytes", side_effect=AssertionError("PROTECTED_READ")):
            for fn,args in ((pilot.checked, (ROOT, {}, "no-input")),
                            (pilot.open_image, (ROOT, {}, {}, "no-input")),
                            (pilot.metadata, (ROOT, {}, "no-input"))):
                with self.assertRaises(PermissionError): fn(*args)


class PilotExecutionTests(unittest.TestCase):
    def test_actual_cpu_pipeline_and_exposure_before_images(self):
        from PIL import Image
        from tests.test_pa3_native import WorkflowTests
        fixture = WorkflowTests()
        with tempfile.TemporaryDirectory() as tmp, fixture.prerequisites(), patch.object(pilot, "verify_prior", return_value={"completed": True}):
            repo = fixture.prepare_repo(tmp)
            inputs = repo / "inputs"; inputs.mkdir()
            images = inputs / "images"; images.mkdir()
            rows = inventory()
            for i,row in enumerate(rows):
                path = images / row["image_locator"]; path.parent.mkdir(exist_ok=True)
                Image.new("RGB", (8,8), (i,0,0)).save(path)
                row["image_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest = pilot.propose(rows, [])
            path = inputs / "manifest.json"; path.write_bytes(json_bytes(manifest))
            settings = {"mode": "pilot-train", "run_id": "pa3-qwen-pilot-train-first",
                "source_commit": preflight.BASE_SHA, "pilot_manifest_input": "manifest.json",
                "pilot_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "dataset_input": "images"}
            original = pilot.open_image
            def after_exposure(*args):
                exposure = Journal(run_path(repo, settings["run_id"] + "-exposure"))
                self.assertTrue(exposure.verify())
                self.assertEqual(exposure.read("observed")["sample_ids"], manifest["observed_ids"])
                return original(*args)
            with patch.object(pilot, "open_image", side_effect=after_exposure):
                root = workflow.execute(repo, settings, "CPU-fixture", inputs)
            report = Journal(root.parent/(root.name+"-report"))
            self.assertTrue(report.verify())
            evaluation = report.read("evaluation")["overall"]
            self.assertEqual(evaluation["planned"], 40)
            self.assertEqual(evaluation["scored"], 40)
            self.assertEqual(evaluation["auroc"]["positive_n"], 20)
            self.assertEqual(evaluation["auroc"]["negative_n"], 20)
            self.assertEqual(len(report.read("audit")["results"][0]["details"]["raw_label_logits"]), 4)
            with self.assertRaises(FileExistsError): workflow.execute(repo, settings, "CPU-fixture", inputs)

    def test_prior_technical_cpu_audit_and_corrupt_seal(self):
        from tests.test_pa3_native import WorkflowTests, TOK
        fixture = WorkflowTests()
        with tempfile.TemporaryDirectory() as tmp, fixture.prerequisites():
            repo = fixture.prepare_repo(tmp)
            root = workflow.execute(repo, SETTINGS, "CPU-fixture")
            qualification = root.parent / (root.name + "-qualification")
            sha = hashlib.sha256(Journal(qualification).path("seal").read_bytes()).hexdigest()
            self.assertTrue(pilot.prior_technical(qualification, repo, TOK, sha)["completed"])
            with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                pilot.prior_technical(qualification, repo, TOK, "a"*64)

    def test_pilot_image_hash_and_unselected_image_fail(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, "require"):
            inputs = Path(tmp); (inputs/"images/train").mkdir(parents=True)
            manifest = pilot.propose(inventory(), [])
            (inputs/"manifest.json").write_bytes(json_bytes(manifest))
            settings = {"pilot_manifest_input": "manifest.json", "pilot_manifest_sha256": hashlib.sha256((inputs/"manifest.json").read_bytes()).hexdigest(), "dataset_input": "images"}
            row = pilot.samples(ROOT, settings, inputs)[0]
            Image.new("RGB", (8,8)).save(inputs/"images"/row["image_locator"])
            with self.assertRaisesRegex(ValueError, "IMAGE_CHANGED"):
                pilot.open_image(ROOT, settings, row, inputs)
            with self.assertRaises(PermissionError): pilot.open_image(ROOT, settings, {**row, "sample_id": "test"}, inputs)
            settings["pilot_manifest_sha256"] = "a"*64
            with self.assertRaisesRegex(ValueError, "CHECKSUM"): pilot.samples(ROOT, settings, inputs)


class PrepTests(unittest.TestCase):
    def test_exact_plan_and_explicit_online_commands(self):
        commands = prep.commands(ROOT, Path("data/processed/prep"))
        self.assertIn("uv==0.6.14", commands[0])
        self.assertIn("3.11.11", commands[1])
        self.assertEqual(sum(r["size_bytes"] for r in preflight.plan("qwen2_5", ROOT)["snapshot_files"]), 7520918095)

    def test_runtime_requires_linux_without_subprocess(self):
        with patch.object(prep.platform, "system", return_value="Windows"), patch.object(prep.platform, "machine", return_value="x86_64"), patch.object(subprocess, "run", side_effect=AssertionError("INSTALL")):
            with self.assertRaises(ValueError): prep.runtime(ROOT, Path("unused"))

    def test_portable_archive_roundtrip(self):
        from safeshift.runners.p21_kaggle import safe_extract
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"runtime"; (root/"bin").mkdir(parents=True)
            (root/"bin/python3.11").write_bytes(b"CPU fixture executable placeholder")
            archive = Path(tmp)/"runtime.tar.gz"
            prep.pack_tree(root, archive)
            destination = Path(tmp)/"restored"
            safe_extract(archive, destination)
            self.assertEqual((destination/"runtime/bin/python3.11").read_bytes(), (root/"bin/python3.11").read_bytes())
            with tarfile.open(archive) as stream: self.assertTrue(all(m.isfile() for m in stream))

    def test_runtime_python_alias_survives_archive(self):
        import os
        from safeshift.runners.p21_kaggle import safe_extract
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"runtime"; (root/"bin").mkdir(parents=True)
            (root/"bin/python3.11").write_bytes(b"fixture")
            try:
                os.symlink("python3.11", root/"bin/python")
            except OSError:
                self.skipTest("Host does not permit symlink creation; actual Linux Prep roundtrip remains required")
            archive = Path(tmp)/"runtime.tar.gz"; prep.pack_tree(root, archive)
            destination = Path(tmp)/"restored"; safe_extract(archive, destination)
            self.assertEqual((destination/"runtime/bin/python").resolve(), (destination/"runtime/bin/python3.11").resolve())

    def test_model_prep_packs_only_revision_pinned_files_without_loading(self):
        from types import SimpleNamespace
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/"prep"
            cached = Path(tmp)/"cached"; cached.mkdir()
            (cached/"weights.fixture").write_bytes(b"not-a-model")
            (cached/"unlisted.txt").write_bytes(b"excluded")
            config = {"model_id": access.TECHNICAL["model"], "model_revision": access.TECHNICAL["revision"],
                      "snapshot_files": [{"path": "weights.fixture", "size_bytes": 11}]}
            calls = []
            def download(**kwargs): calls.append(kwargs); return str(cached)
            with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(snapshot_download=download)}), \
                 patch.object(prep, "plan", return_value=config), patch.object(prep, "verify_snapshot", return_value={"fixture": True}):
                prep.model(ROOT, output)
            self.assertEqual(calls[0]["revision"], access.TECHNICAL["revision"])
            self.assertEqual(calls[0]["allow_patterns"], ["weights.fixture"])
            with tarfile.open(output/"pa3_model.tar.gz") as stream:
                self.assertEqual(stream.getnames(), [access.TECHNICAL["revision"] + "/weights.fixture"])
                self.assertEqual(stream.extractfile(stream.getmembers()[0]).read(), b"not-a-model")
            self.assertEqual(json.loads((output/"model_prep.json").read_text())["model_load"], "NOT_RUN")

    def test_capacity_reports_actual_runtime_and_stops_on_shortage(self):
        from safeshift.pa3.native import kaggle
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"runtime"; root.mkdir(); (root/"fixture").write_bytes(b"small")
            archive = Path(tmp)/"runtime.tar.gz"; prep.pack_tree(root, archive)
            with patch.object(kaggle.shutil, "disk_usage", return_value=SimpleNamespace(free=100*2**30)):
                proof = kaggle.capacity(ROOT, archive)
                self.assertEqual(proof["runtime_expanded_bytes"], 5)
                self.assertEqual(proof["model_expanded_bytes"], 7520918095)
            with patch.object(kaggle.shutil, "disk_usage", return_value=SimpleNamespace(free=1)):
                with self.assertRaisesRegex(OSError, "DISK_SHORTAGE"): kaggle.capacity(ROOT, archive)

    def test_notebooks_compile_and_inference_has_no_installs(self):
        for filename in ("pa3_qwen2_5_kaggle.ipynb", "pa3_inputs_prep_kaggle.ipynb"):
            notebook = json.loads((ROOT/"notebooks"/filename).read_text(encoding="utf-8"))
            code = "\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
            compile(code, filename, "exec")
            if filename == "pa3_qwen2_5_kaggle.ipynb":
                self.assertNotIn("pip install", code)
                self.assertNotIn("snapshot_download", code)


if __name__ == "__main__":
    unittest.main()
