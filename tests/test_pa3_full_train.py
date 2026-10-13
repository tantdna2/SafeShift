"""Synthetic CPU tests. Real TRAIN is used only by the explicit manifest builder."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from safeshift.pa3.native import access, train, train_manifest, train_report, train_workflow, workflow, preflight, kaggle
from safeshift.pa3.native.journal import Journal, run_path
from safeshift.pa3.native.native_score import pending, score
from safeshift.pa3.artifacts import json_bytes
from safeshift.ls1.evaluate import auc
from safeshift.ls1.evaluate import anomaly_log_odds
from safeshift.ls1 import tokenizer as token_module
from safeshift.data.manifest import TEXT_OPENINGS
from tests.test_pa3_native import Model, ROOT, TOK, raw_fixture
from tests import test_pa3_native as cpu
from tests.test_ls1 import fake_raw


@contextmanager
def small_universe():
    with patch.object(train, "COUNT", 8), patch.object(train, "SIZES", (2, 2, 2, 2)):
        yield


def fixture(root):
    """Actual original-helper verification of small synthetic JPG/JSON/TXT triplets."""
    rows, validation = [], []
    opening = TEXT_OPENINGS["power"][0]
    for i in range(8):
        level = ("Level01", "Level02", "Level03", "Level04")[i % 4]
        cls = "Normal" if level == "Level04" else "Anomaly"
        sid = f"power-{level}-Wheeled-{i:06d}-001"
        locator = f"DATA_PATH/train/Annotations/{cls}_data/{sid[:-4]}/{sid}.jpg"
        p = root / locator
        p.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (16, 16), (i * 20, 0, 0)).save(p)
        p.with_suffix(".json").write_text(json.dumps({"imageWidth": 16, "imageHeight": 16}), encoding="utf-8")
        p.with_suffix(".txt").write_text(opening + "synthetic", encoding="utf-8")
        r = {"sample_id": sid, "split": "train", "folder_domain": "power", "safety_level": level,
             "point_id": f"{i:06d}", "robot_platform": "Wheeled", "data_type": cls + "_data",
             "dimensions": [16, 16], "image_relpath": train_manifest.existing.TRAIN_PREFIX + locator,
             "byte_sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        rows.append(r)
        validation.append({**r, "text_domain": "power"})
    common = {"audit_complete": True, "input_sha256": train_manifest.existing.FINGERPRINT}
    audit = json_bytes({**common, "samples": rows, "git_commit": "a" * 40, "run_id": "SYNTHETIC",
                       "exact_pair_evidence": [], "sequential_pair_evidence": [], "near_pair_evidence": [],
                       "metadata_source_evidence": {"source_family_groups": []}})
    valid = json_bytes({**common, "samples": validation})
    with patch.object(train_manifest.existing, "AUDIT_SHA256", hashlib.sha256(audit).hexdigest()), \
         patch.object(train_manifest, "VALIDATION_SHA", hashlib.sha256(valid).hexdigest()):
        return train_manifest.build(audit, valid, root), audit, valid


def install(repo, full, shards):
    (repo / "data/manifests").mkdir(parents=True, exist_ok=True)
    (repo / train.FULL).write_bytes(full)
    for i, data in enumerate(shards):
        (repo / train.inference_path(i)).write_bytes(data)


@contextmanager
def running_fixture(tmp, failure_at=None):
    repo, inputs = Path(tmp) / "repo", Path(tmp) / "inputs"
    root = inputs / "train"
    with small_universe():
        (full, shards), _, _ = fixture(root)
        cpu.WorkflowTests().prepare_repo(repo)
        install(repo, full, shards)
        hashes = [hashlib.sha256(s).hexdigest() for s in shards]
        settings = {"mode": train.MODE, "run_id": train.run_id(0), "shard_id": 0,
                    "source_commit": preflight.BASE_SHA, "dataset_input": "train",
                    "full_manifest_sha256": hashlib.sha256(full).hexdigest(), "inference_manifest_sha256": hashes[0]}
        original_ticket = access.image_ticket

        class Failing(Model):
            def generate(self, **kwargs):
                out = super().generate(**kwargs)
                if failure_at and len(self.calls) == failure_at:
                    raise RuntimeError("CPU_SYNTHETIC_FAILURE")
                return out

        model = Failing()
        with ExitStack() as stack:
            stack.enter_context(cpu.WorkflowTests().prerequisites(model))
            stack.enter_context(patch.object(access, "image_ticket", original_ticket))
            stack.enter_context(patch.object(train, "require", return_value={"grant": {
                "shards": [{"inference_manifest_sha256": h} for h in hashes]}}))
            stack.enter_context(patch.object(train, "verify_prior", return_value={"completed": True}))
            yield repo, settings, inputs, model, full, shards


class ManifestTests(unittest.TestCase):
    def test_committed_full_universe_counts_and_four_disjoint_shards(self):
        full = json.loads((ROOT / train.FULL).read_bytes())
        shards = [(ROOT / train.inference_path(i)).read_bytes() for i in range(4)]
        metadata = train.validate_full(full, shards)
        self.assertEqual(len(metadata), 3763)
        self.assertEqual(full["counts"]["by_level"], {"Level01": 490, "Level02": 251, "Level03": 8, "Level04": 3014})
        for payload in shards:
            for row in json.loads(payload)["samples"]:
                self.assertEqual(set(row), {"sample_id", "image_locator", "image_sha256"})

    def test_synthetic_builder_verifies_original_helpers_and_no_test_scan(self):
        with tempfile.TemporaryDirectory() as tmp, small_universe():
            root = Path(tmp) / "train"
            (full, shards), audit, valid = fixture(root)
            self.assertEqual(len(train.validate_full(json.loads(full), shards)), 8)
            self.assertEqual(train.partition(list(reversed(json.loads(full)["samples"]))),
                             train.partition(json.loads(full)["samples"]))
            # Real TEST sentinel exists; builder has no path to it.
            (Path(tmp) / "test").mkdir()
            (Path(tmp) / "test" / "forbidden.jpg").write_bytes(b"NEVER_READ")
            row = json.loads(full)["samples"][0]
            (root / row["image_locator"]).write_bytes(b"changed")
            with patch.object(train_manifest.existing, "AUDIT_SHA256", hashlib.sha256(audit).hexdigest()), \
                 patch.object(train_manifest, "VALIDATION_SHA", hashlib.sha256(valid).hexdigest()):
                with self.assertRaisesRegex(ValueError, "TRAIN_VERIFICATION_FAILED"):
                    train_manifest.build(audit, valid, root)

    def test_duplicate_id_gt_injection_test_locator_overlap_and_count(self):
        full = json.loads((ROOT / train.FULL).read_bytes())
        shards = [(ROOT / train.inference_path(i)).read_bytes() for i in range(4)]
        for kind in ("label", "test", "duplicate", "count", "shard"):
            changed = json.loads(shards[0])
            if kind == "label": changed["samples"][0]["level"] = "Level01"
            if kind == "test": changed["samples"][0]["image_locator"] = "DATA_PATH/test/Annotations/a.jpg"
            if kind == "duplicate": changed["samples"][1] = deepcopy(changed["samples"][0])
            if kind == "count": changed["samples"].pop()
            if kind == "shard": changed["shard_id"] = 1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                train.validate_full(full, [json_bytes(changed), *shards[1:]])

    def test_wrong_upstream_hash_blocks_before_inventory_or_image_reads(self):
        with patch.object(train_manifest.existing, "train_inventory", side_effect=AssertionError("READ")):
            with self.assertRaisesRegex(ValueError, "W1_AUDIT"):
                train_manifest.build(b"{}", b"{}", "never-read")


class AuthorityTests(unittest.TestCase):
    def test_null_grant_and_direct_helpers_cannot_borrow_90_image_rights(self):
        settings = {"mode": train.MODE, "shard_id": 0, "run_id": train.run_id(0), "source_commit": train.BASE}
        for fn, args in ((train.require, (settings, ROOT)),
                         (train.inference_samples, (ROOT, settings)),
                         (train.open_image, (ROOT, settings, {}, "never-read")),
                         (train.preflight_dataset, (ROOT, settings, "never-read"))):
            with self.subTest(fn=fn.__name__), self.assertRaises(PermissionError), \
                 patch.object(preflight, "git", side_effect=AssertionError("GIT_BEFORE_NULL_DENIAL")):
                fn(*args)
        with self.assertRaises(PermissionError):
            access.require("test", settings, ROOT)

    def test_exact_shard_and_settings_scope(self):
        settings = {"mode": train.MODE, "shard_id": 0, "run_id": train.run_id(0)}
        grant = {k: "a"*64 for k in train.HASHES}
        grant["shards"] = [{"inference_manifest_sha256": "b"*64}] * 4
        settings.update({k: grant[k] for k in train.HASHES}, inference_manifest_sha256="b"*64)
        with patch.object(train, "authority", return_value={"grant": grant}):
            self.assertEqual(train.require(settings, ROOT)["grant"], grant)
            for change in ({"run_id": train.run_id(1)}, {"inference_manifest_sha256": "c"*64},
                           {"dataset_root": "test"}, {"approved": True}, {"full_manifest_sha256": "c"*64}):
                with self.subTest(change=change), self.assertRaises(PermissionError):
                    train.require({**settings, **change}, ROOT)

    def test_real_git_topology_blocks_draft_modified_scope_tree_and_old_grants(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
            git("init", "-b", "main"); git("config", "core.autocrlf", "false")
            git("config", "user.email", "cpu@example.invalid"); git("config", "user.name", "CPU fixture")
            for p in (access.AUTHORITY, access.DIAGNOSTIC_AUTHORITY):
                (repo / p).parent.mkdir(parents=True, exist_ok=True)
                (repo / p).write_text("{}\n", encoding="utf-8")
            git("add", "."); git("commit", "-m", "BASE")
            base = git("rev-parse", "HEAD")
            git("checkout", "-b", "prep")
            value = {"base": base, "implementation": None, "scope": train.SCOPE, "grant": None}
            path = repo / train.AUTHORITY
            path.write_bytes(json_bytes(value)); git("add", "."); git("commit", "-m", "F1")
            f1 = git("rev-parse", "HEAD")
            value["implementation"] = f1
            value["grant"] = {**{k: "a"*64 for k in train.HASHES}, "approval": "SYNTHETIC_TEST_ONLY", "decision": "DEC-PA3-007",
                "shards": [{"shard_id": i, "run_id": train.run_id(i), "max_images": train.SIZES[i],
                            "inference_manifest_sha256": "b"*64} for i in range(4)]}
            path.write_bytes(json_bytes(value)); git("add", "."); git("commit", "-m", "F2")
            with patch.object(train, "BASE", base):
                with self.assertRaisesRegex(PermissionError, "STANDARD_MERGE"):
                    train.authority(repo, git("rev-parse", "HEAD"))
                git("checkout", "main"); git("merge", "--no-ff", "prep", "-m", "M")
                merge = git("rev-parse", "HEAD")
                self.assertEqual(train.authority(repo, merge)["grant"], value["grant"])
                original = path.read_bytes()
                value["scope"]["max_images"] = 90
                path.write_bytes(json_bytes(value))
                with self.assertRaises(PermissionError): train.authority(repo, merge)
                value["scope"]["max_images"] = 3763
                path.write_bytes(original)
                (repo / access.DIAGNOSTIC_AUTHORITY).write_text('{"borrowed":true}')
                with self.assertRaises(PermissionError): train.authority(repo, merge)


class WorkflowTestsFullTrain(unittest.TestCase):
    def test_offline_launcher_reuses_runtime_restore_outside_saved_output_once(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, s, inputs, _, _, _):
            for name in ("runtime.tar", "model.tar", "inventory.json"):
                (inputs / name).write_bytes(b"CPU_FIXTURE")
            settings = {**s, "runtime_input": "runtime.tar", "model_input": "model.tar",
                        "runtime_inventory_input": "inventory.json", "runtime_inventory_sha256": "a"*64}
            runtime = {"python": "CPU_FAKE_PYTHON", "site_packages": None, "software_versions": {"fixture": True}}
            with patch.object(kaggle, "verify_runtime_input", return_value={}), \
                 patch.object(kaggle, "capacity", return_value={"required_bytes": 1}), \
                 patch.object(kaggle, "restore_model", return_value=Path(tmp) / "fake_snapshot") as restore, \
                 patch.object(kaggle, "runtime_interpreter", return_value=runtime) as interpreter, \
                 patch.object(kaggle.subprocess, "run", return_value=type("Child", (), {"returncode": 0})()) as child:
                output = kaggle.launch(repo, inputs, settings)
                target = restore.call_args.args[0]
                self.assertFalse(target.is_relative_to(repo))
                self.assertEqual(interpreter.call_args.args[0], target)
                self.assertEqual(child.call_count, 1)
                self.assertEqual((target / "configs/pre_freeze/qwen2_5_t4_runtime.v1.json").read_bytes(),
                                 (repo / "configs/pre_freeze/qwen2_5_t4_runtime.v1.json").read_bytes())
                self.assertTrue(Journal(output.parent / (output.name + "-launch")).verify())

    def test_native_mock_one_pass_seal_before_gt_export_and_no_replay(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, s, inputs, model, _, _):
            original = train.load_full
            def after_seal(*args):
                self.assertTrue(Journal(run_path(repo, s["run_id"])).verify())
                return original(*args)
            with patch.object(train, "load_full", side_effect=after_seal):
                root = workflow.execute(repo, s, "fixture", inputs)
            self.assertEqual(len(model.calls), 2)
            self.assertTrue(Journal(root.parent / (root.name + "-exposure")).verify())
            self.assertEqual(len(list(csv.DictReader(io.StringIO((root.parent / (root.name + "-exports") / "samples.csv").read_text())))), 2)
            self.assertEqual(len(list((root.parent / (root.name + "-tickets")).glob("sample-*.ticket"))), 2)
            with self.assertRaises(FileExistsError): workflow.execute(repo, s, "fixture", inputs)

    def test_error_stops_without_retry_preserves_raw_and_remaining_statuses(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp, failure_at=2) as (repo, s, inputs, model, _, _):
            with self.assertRaises(RuntimeError): workflow.execute(repo, s, "fixture", inputs)
            root = run_path(repo, s["run_id"])
            checked = Journal(root.parent / (root.name + "-report")).read("audit")
            self.assertEqual([r["status"] for r in checked["results"]], ["SUCCESS", "TECHNICAL_ERROR"])
            self.assertEqual(len(model.calls), 2)
            self.assertTrue(Journal(root).exists("sample-000000.raw"))
            self.assertFalse(checked["completed"])

    def test_pre_model_checksum_failure_exports_all_not_attempted(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, s, inputs, model, _, _):
            with patch.object(train, "preflight_dataset", side_effect=ValueError("HASH_FAILURE")):
                with self.assertRaises(ValueError): workflow.execute(repo, s, "fixture", inputs)
            checked = Journal(run_path(repo, s["run_id"]).parent / (s["run_id"] + "-report")).read("audit")
            self.assertEqual([r["status"] for r in checked["results"]], ["NOT_ATTEMPTED"] * 2)
            self.assertEqual(len(model.calls), 0)

    def test_first_image_error_keeps_unattempted_tail(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp, failure_at=1) as (repo, s, inputs, model, _, _):
            with self.assertRaises(RuntimeError): workflow.execute(repo, s, "fixture", inputs)
            checked = Journal(run_path(repo, s["run_id"]).parent / (s["run_id"] + "-report")).read("audit")
            self.assertEqual([r["status"] for r in checked["results"]], ["TECHNICAL_ERROR", "NOT_ATTEMPTED"])
            self.assertEqual(len(model.calls), 1)

    def test_pixel_identity_and_ticket_reuse_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, s, inputs, _, _, _):
            journal = Journal(run_path(repo, s["run_id"]), create=True)
            row = train.inference_samples(repo, s)[0]
            journal.write("sample-000000.attempt", row)
            settings = {**s, "train_inputs_root": str(inputs)}
            with train.open_image(repo, s, row, inputs) as image:
                access.image_ticket(repo, settings, image, journal, "sample-000000")
                with self.assertRaises(FileExistsError): access.image_ticket(repo, settings, image, journal, "sample-000000")
                image.putpixel((0, 0), (255, 255, 255))
                with self.assertRaisesRegex(PermissionError, "PIXELS"):
                    access.image_ticket(repo, settings, image, journal, "sample-000000")


class MergeAndMetricTests(unittest.TestCase):
    def test_merge_reaudits_four_shards_recomputes_auc_from_csv_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp, running_fixture(tmp) as (repo, s, inputs, _, _, shards):
            roots = []
            for i in range(4):
                current = {**s, "shard_id": i, "run_id": train.run_id(i), "inference_manifest_sha256": hashlib.sha256(shards[i]).hexdigest()}
                roots.append(workflow.execute(repo, current, "fixture", inputs))
            result = train_report.merge(repo, list(reversed(roots)), TOK, Path(tmp) / "merged")
            samples = list(csv.DictReader(io.StringIO((Path(tmp) / "merged/samples.csv").read_text())))
            valid = [r for r in samples if r["status"] == "SUCCESS"]
            expected = auc([r["true_level"] != "Level04" for r in valid], [float(r["pa3_score"]) for r in valid])
            self.assertEqual(result["overall"]["auroc_pa3"]["value"], expected)
            self.assertEqual(result["overall"]["coverage"]["scored"], 8)
            self.assertEqual(result["overall"]["auroc_pa3"]["eligible_ids"], result["overall"]["auroc_generated_binary"]["eligible_ids"])
            with self.assertRaisesRegex(ValueError, "DUPLICATE_TRAIN_SHARD"):
                train_report.merge(repo, [roots[0], roots[0], *roots[2:]], TOK, Path(tmp) / "duplicate")
            with self.assertRaises(ValueError): train_report.merge(repo, roots[:3], TOK, Path(tmp) / "missing")
            journal = Journal(roots[0]); data = journal.path("sample-000000.raw").read_bytes()
            journal.path("sample-000000.raw").write_bytes(data + b" ")
            with self.assertRaises(ValueError): train_report.merge(repo, roots, TOK, Path(tmp) / "tampered")

    def test_single_class_zero_coverage_ties_and_nonfinite(self):
        r = score("a", raw_fixture(), TOK)
        m = {"a": {"level": "Level04", "domain": "power", "group": "g"}}
        result = train_report.metrics([r], m, True)["overall"]
        self.assertIsNone(result["auroc_pa3"]["value"])
        self.assertIsNone(result["delta_auroc_same_ids"])
        self.assertEqual(result["auroc_pa3"]["reason"], "MISSING_SCORED_CLASS")
        out = train_report.metrics([pending("a")], m, False)["overall"]
        self.assertEqual(out["coverage"]["coverage"], 0)
        self.assertIsNone(out["generated_on_score_valid_ids"]["raw_accuracy_descriptive"]["value"])
        self.assertEqual(auc([True, False], [1.0, 1.0]), 0.5)
        bad = deepcopy(r); bad["score"] = float("nan")
        with self.assertRaises(ValueError): train_report.metrics([bad], m, False)

    def test_pooled_auc_differs_from_average_of_perfect_shard_aucs(self):
        # Independent synthetic endpoint fixture: four perfect shard rankings,
        # overlapping across-shard score ranges. Correct pooled AUROC is 10/16.
        rows, metadata = [], {}
        for i, offset in enumerate((10., 2., -6., -14.)):
            for j, positive in enumerate((True, False)):
                sid = f"s{i}-{j}"
                row = score(sid, raw_fixture(), TOK)
                logits = [offset + int(positive) - math.log(3)] * 3 + [0.]
                m = max(logits); normalizer = m + math.log(sum(math.exp(z-m) for z in logits))
                logs = [z-normalizer for z in logits]
                row["details"].update(raw_label_logits=logits, log_probabilities=logs)
                row["score"] = anomaly_log_odds(logs)
                rows.append(row)
                metadata[sid] = {"level": "Level01" if positive else "Level04", "domain": "power", "group": sid}
        self.assertEqual(sum(train_report.metrics(rows[i:i+2], {r["sample_id"]: metadata[r["sample_id"]] for r in rows[i:i+2]}, True)
                             ["overall"]["auroc_pa3"]["value"] for i in range(0, 8, 2))/4, 1.)
        self.assertEqual(train_report.metrics(rows, metadata, True)["overall"]["auroc_pa3"]["value"], 0.625)

    def test_notebook_compiles_offline_no_outputs_and_save_output_package(self):
        nb = json.loads((ROOT / "notebooks/pa3_qwen_full_train_kaggle.ipynb").read_bytes())
        self.assertFalse(nb["metadata"]["kaggle"]["isInternetEnabled"])
        for i, cell in enumerate(nb["cells"]):
            if cell["cell_type"] == "code":
                self.assertEqual(cell["outputs"], [])
                compile("".join(cell["source"]), f"cell-{i}", "exec")
        self.assertIn("PA3_TRAIN_SHARD_", json.dumps(nb))

    def test_notebook_bootstrap_failure_finishes_version_with_failure_archive(self):
        nb = json.loads((ROOT / "notebooks/pa3_qwen_full_train_kaggle.ipynb").read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                namespace = {}
                exec("".join(nb["cells"][1]["source"]), namespace)
                # Empty unapproved source SHA is rejected before model/runtime/data.
                exec("".join(nb["cells"][2]["source"]), namespace)
                self.assertTrue((Path(tmp) / "PA3_TRAIN_SHARD_0_OUTPUT.tar.gz").is_file())
                failure = json.loads(next(Path(tmp).rglob("failure.json")).read_bytes())
                self.assertFalse(failure["retry_permitted"])
                self.assertFalse(failure["runtime_pass_claim"])
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
