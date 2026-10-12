"""CPU regression; the opt-in Linux tests are the only real runtime evidence."""
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pa3.native import prep
from safeshift.ls1.kaggle import inventory_runtime, verify_runtime_input
from safeshift.ls1.tokenizer import plan

ROOT = Path(__file__).resolve().parents[1]
REAL_GIT_OUTPUT = subprocess.check_output
REAL_RUN = subprocess.run


def git_fixture(repo, *args):
    return REAL_GIT_OUTPUT(["git", "-C", str(repo), "-c", "user.name=CPU fixture",
                            "-c", "user.email=fixture@example.invalid", *args], text=True).strip()


def commit(repo, files, message="fixture"):
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
        git_fixture(repo, "add", name)
    git_fixture(repo, "commit", "-qm", message)
    return git_fixture(repo, "rev-parse", "HEAD")


def new_repo(path):
    path.mkdir(parents=True)
    git_fixture(path, "init", "-q")
    return path


class RuntimePrepTests(unittest.TestCase):
    def test_managed_python_install_uses_separate_target_and_all_pins(self):
        pins = plan("qwen2_5", ROOT)["software"]
        command = prep.package_command(Path("managed/bin/python3.11"),
                                       Path("packages/site-packages"), Path("constraints.txt"), pins)
        self.assertIn("--target", command)
        self.assertIn("--python", command)
        self.assertIn("copy", command)
        for name, version in pins.items():
            if name not in {"python", "torch", "torchvision"}:
                self.assertIn(name + "==" + version, command)
        self.assertTrue(any("torch-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl" in s for s in command))
        self.assertTrue(any("torchvision-0.21.0%2Bcu124-cp311" in s for s in command))
        for forbidden in ("ensurepip", "--break-system-packages", "--system", "--no-deps"):
            self.assertNotIn(forbidden, command)

    def test_prep_never_invokes_ensurepip_or_pep668_bypass(self):
        source = Path(prep.__file__).read_text(encoding="utf-8")
        for forbidden in ('"ensurepip"', "break-system-packages", "EXTERNALLY-MANAGED"):
            self.assertNotIn(forbidden, source)

    def test_dangling_or_external_links_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "payload"; root.mkdir()
            try:
                (root / "bad").symlink_to("missing")
            except OSError:
                self.skipTest("Host symlink unavailable; Linux regression required")
            with self.assertRaises(FileNotFoundError): prep.check_links(root)
            (root / "bad").unlink()
            (Path(tmp) / "outside").write_text("fixture")
            (root / "bad").symlink_to("../outside")
            with self.assertRaisesRegex(ValueError, "ESCAPES"): prep.check_links(root)
            with self.assertRaisesRegex(ValueError, "ESCAPES"): prep.pack_tree(root, Path(tmp) / "a.tar.gz")

    def test_probe_propagates_selected_packages_and_does_not_use_host_packages(self):
        root = Path("restored").resolve()
        selected = {"python": str(root / "python/bin/python3.11"),
                    "site_packages": str(root / "packages/site-packages"), "software_versions": {}}
        calls = []
        with patch.object(prep, "check_links", return_value={}), \
             patch.object(prep, "runtime_interpreter", return_value=selected):
            prep.probe_runtime(ROOT, root, root, {"CUDA_VISIBLE_DEVICES": "", "PYTHONPATH": "host",
                                                  "PYTHONHOME": "host"},
                               lambda c, e: calls.append((c, e)))
        self.assertEqual(len(calls), 2)
        for command, env in calls:
            self.assertEqual(env["PYTHONPATH"], selected["site_packages"])
            self.assertNotIn("PYTHONHOME", env)
            self.assertEqual(env["CUDA_VISIBLE_DEVICES"], "")
        self.assertEqual(calls[0][0][:4], [selected["python"], "-B", "-s", "-c"])
        self.assertEqual(calls[0][0][-1], str(root))
        self.assertEqual(calls[1][0][-3:], ["--python", selected["python"], "check"])

    def test_selection_outside_root_or_without_packages_never_runs(self):
        root = Path("restored").resolve()
        for selected in ({"python": str(root.parent / "old/bin/python3.11"),
                          "site_packages": str(root / "packages/site-packages")},
                         {"python": str(root / "python/bin/python3.11"),
                          "site_packages": str(root.parent / "old/site-packages")},
                         {"python": str(root / "python/bin/python3.11"), "site_packages": None}):
            with self.subTest(selected=selected), patch.object(prep, "runtime_interpreter", return_value=selected):
                with self.assertRaisesRegex(ValueError, "NOT_SELECTED_INSIDE_ROOT"):
                    prep.probe_runtime(ROOT, root, root, {}, lambda *a: self.fail("ran"))

    def test_import_or_dependency_failure_cannot_be_pass(self):
        root = Path("restored").resolve()
        selected = {"python": str(root / "python"), "site_packages": str(root / "site")}
        with patch.object(prep, "check_links", return_value={}), \
             patch.object(prep, "runtime_interpreter", return_value=selected):
            with self.assertRaises(subprocess.CalledProcessError):
                prep.probe_runtime(ROOT, root, root, {},
                    lambda *a: (_ for _ in ()).throw(subprocess.CalledProcessError(1, "probe")))

    def test_roundtrip_link_or_version_change_is_rejected(self):
        reference = {"software_versions": {"torch": "2.6.0+cu124"}}
        prep.require_same(reference, {"a": "b"}, dict(reference), {"a": "b"})
        with self.assertRaisesRegex(ValueError, "ROUNDTRIP_CHANGED"):
            prep.require_same(reference, {"a": "b"}, dict(reference), {})
        with self.assertRaisesRegex(ValueError, "ROUNDTRIP_CHANGED"):
            prep.require_same(reference, {}, {"software_versions": {"torch": "2.6.0"}}, {})

    def test_offline_child_import_uses_launcher_pythonpath(self):
        calls = []
        selected = {"python": "runtime/python/bin/python3.11", "site_packages": "runtime/site"}
        prep.probe_offline_child(Path("repo"), selected, {"PYTHONHOME": "host", "PYTHONPATH": "host"},
                                 lambda c, e: calls.append((c, e)))
        (command, env), = calls
        self.assertEqual(command, [selected["python"], "-B", "-s", "-c", "import safeshift.pa3.native.workflow"])
        self.assertEqual(env["PYTHONPATH"], "repo" + os.pathsep + "runtime/site")
        self.assertEqual(env["HF_HUB_OFFLINE"], "1")
        self.assertNotIn("PYTHONHOME", env)

    def test_inventory_lives_outside_archive_directory_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            archive = output / prep.ARCHIVE; archive.parent.mkdir()
            archive.write_bytes(b"synthetic archive")
            # BASE placed the inventory beside the archive; the ls1 rule rejects that.
            with self.assertRaisesRegex(ValueError, "WRITE_RUNTIME_INVENTORY_OUTSIDE_PREP_INPUT"):
                inventory_runtime(archive, archive.parent / "pa3_runtime_inventory.json")
            inventory = output / "pa3_runtime_inventory.json"
            trusted = inventory_runtime(archive, inventory)
            self.assertEqual(set(verify_runtime_input(archive, inventory, trusted)["files"]), {archive.name})
            with self.assertRaisesRegex(ValueError, "TRUSTED_RUNTIME_INVENTORY_CHECKSUM_REQUIRED"):
                verify_runtime_input(archive, inventory, "0" * 64)
            archive.write_bytes(b"synthetic archivE")
            with self.assertRaisesRegex(ValueError, "RUNTIME_INPUT_CHECKSUM_MISMATCH"):
                verify_runtime_input(archive, inventory, trusted)


class ProbeScriptTests(unittest.TestCase):
    """The real probe script in a real child interpreter (host Python), synthetic packages."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.root = self.tmp / "runtime"
        self.site = self.root / "packages/site-packages"
        self.old = self.tmp / "old/site-packages"
        for site in (self.site, self.old):
            (site / "ssfixture").mkdir(parents=True)
            (site / "ssfixture/__init__.py").write_text("")
            (site / "ssfixture-1.0.dist-info").mkdir()
            (site / "ssfixture-1.0.dist-info/METADATA").write_text(
                "Metadata-Version: 2.1\nName: ssfixture\nVersion: 1.0\n")

    def probe(self, pythonpath, root=None, version="1.0"):
        expected = {"python": platform.python_version(), "ssfixture": version}
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
        if pythonpath:
            env["PYTHONPATH"] = os.pathsep.join(str(p) for p in pythonpath)
        return subprocess.run([sys.executable, "-B", "-s", "-c", prep.probe_script(expected, ("ssfixture",)),
                               str(root or self.root)], env=env, capture_output=True, text=True)

    def assertFails(self, result, code):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(code, result.stderr)

    def test_full_pass_when_interpreter_and_packages_are_inside_root(self):
        anchor = Path(self.tmp.anchor)
        if not all(Path(p).resolve().is_relative_to(anchor) for p in (sys.executable, sys.base_prefix)):
            self.skipTest("Host interpreter on another volume than the temporary fixture")
        result = self.probe([self.site], root=anchor)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["ssfixture"], "1.0")

    def test_packages_inside_root_still_require_runtime_interpreter(self):
        # Module/metadata/version checks pass; host interpreter is then rejected.
        self.assertFails(self.probe([self.site]), "INTERPRETER_OUTSIDE_RUNTIME")

    def test_old_or_host_path_cannot_satisfy_probe(self):
        self.assertFails(self.probe([self.old]), "MODULE_OUTSIDE_RUNTIME:ssfixture")

    def test_metadata_from_outside_root_is_rejected(self):
        shutil.rmtree(self.site / "ssfixture-1.0.dist-info")
        self.assertFails(self.probe([self.site, self.old]), "METADATA_OUTSIDE_RUNTIME:ssfixture")

    def test_missing_required_library_fails(self):
        self.assertFails(self.probe([]), "ModuleNotFoundError")

    def test_version_mismatch_fails(self):
        self.assertFails(self.probe([self.site], version="2.0"), "RUNTIME_VERSION_MISMATCH")

    def test_real_script_checks_every_pin_and_qwen_class(self):
        script = prep.probe_script(plan("qwen2_5", ROOT)["software"])
        compile(script, "probe", "exec")
        for text in ("Qwen2_5_VLForConditionalGeneration", "torch.version.cuda != '12.4'",
                     "torch.cuda.is_initialized()", "'transformers': '4.51.3'", "'python': '3.11.11'"):
            self.assertIn(text, script)


class RuntimeSequenceTests(unittest.TestCase):
    """CPU mock of runtime(): order, deletion, consumer path and receipts. No install."""

    def run_prep(self, fail_consumer=False):
        pins = plan("qwen2_5", ROOT)["software"]
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        repo = new_repo(Path(tmp.name) / "repo")
        commit(repo, {"fixture": "synthetic"})
        output = repo / "data/processed/prep"
        consumer = repo / prep.CONSUMER_ROOT
        self.output, self.consumer = output, consumer
        children = []

        def state():
            return {name: path.exists() for name, path in (
                ("relocated", output / "relocated"), ("build", output / "build"),
                ("roundtrip", output / "archive-roundtrip"), ("consumer", consumer))}

        def fake_run(command, **kwargs):
            if command[0] == "git":
                return REAL_RUN(command, **kwargs)
            env = kwargs["env"]
            if command == ["UV_PYTHON_INSTALL"]:
                python = output / "build/managed/cpython-3.11.11-fixture/bin/python3.11"
                python.parent.mkdir(parents=True)
                python.write_bytes(b"fixture interpreter")
                (python.parent.parent / "lib/python3.11").mkdir(parents=True)
                (python.parent.parent / "lib/python3.11/EXTERNALLY-MANAGED").write_text("[externally-managed]")
            elif "--target" in command:
                site = Path(command[command.index("--target") + 1])
                (site / "pkg").mkdir(parents=True)
                (site / "pkg/__init__.py").write_text("")
                (site / "bin").mkdir()
                (site / "bin/tool").write_text("#!/install/time/shebang")
            else:
                children.append((command, env, state()))
                if fail_consumer and str(consumer) in command[0]:
                    raise subprocess.CalledProcessError(1, command)

        def fake_selector(repo_arg, source, key):
            source = Path(source)
            if source.is_file():
                from safeshift.runners.p21_kaggle import safe_extract
                base = safe_extract(source, Path(repo_arg) / prep.CONSUMER_ROOT / "part-0",
                                    skip_external_runtime_links=True) / "runtime"
            else:
                base = source
            self.assertTrue((base / "python/bin/python3.11").is_file())
            return {"python": str(base / "python/bin/python3.11"),
                    "site_packages": str(base / "packages/site-packages"), "software_versions": dict(pins)}

        def fake_output(command, **kwargs):
            return REAL_GIT_OUTPUT(command, **kwargs) if command[0] == "git" else b"pkg==1\n"

        with patch.object(prep.platform, "system", return_value="Linux"), \
             patch.object(prep.platform, "machine", return_value="x86_64"), \
             patch.object(prep, "commands", return_value=[["UV_PYTHON_INSTALL"]]), \
             patch.object(prep, "plan", side_effect=lambda key, _: plan(key, ROOT)), \
             patch.object(prep, "runtime_interpreter", side_effect=fake_selector), \
             patch.object(prep.subprocess, "run", side_effect=fake_run), \
             patch.object(prep.subprocess, "check_output", side_effect=fake_output):
            try:
                prep.runtime(repo, output)
            finally:
                self.commands = json.loads((output / "commands.json").read_text())
        return repo, output, consumer, children

    def test_full_sequence_deletes_old_trees_and_uses_offline_consumer_path(self):
        repo, output, consumer, children = self.run_prep()
        receipt = json.loads((output / "runtime_prep.json").read_text())
        self.assertEqual(receipt["status"], "CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN")
        self.assertEqual(set(receipt["checks"].values()), {"PASS"})
        self.assertEqual(len(receipt["checks"]), 4)
        self.assertEqual(receipt["software"], plan("qwen2_5", ROOT)["software"])
        archive, inventory = output / prep.ARCHIVE, output / receipt["inventory"]
        self.assertEqual(receipt["archive_sha256"], prep.digest(archive))
        # Exactly what the unchanged OFFLINE launcher will verify on Kaggle.
        verify_runtime_input(archive, inventory, receipt["inventory_sha256"])
        with tarfile.open(archive) as stream:
            names = stream.getnames()
        self.assertIn("runtime/python/bin/python3.11", names)
        self.assertIn("runtime/python/lib/python3.11/EXTERNALLY-MANAGED", names)
        self.assertIn("runtime/packages/site-packages/pkg/__init__.py", names)
        self.assertFalse(any("/bin/tool" in n for n in names))
        self.assertTrue((output / "excluded-console-scripts/tool").is_file())
        for path in (output / "relocated", output / "build", output / "archive-roundtrip", consumer):
            self.assertFalse(path.exists(), path)
        probes = [c for c in children if "-c" in c[0] and "workflow" not in c[0][-1]]
        self.assertEqual(len(probes), 3)
        relocated, roundtrip, consumed = (c[2] for c in probes)
        self.assertTrue(relocated["relocated"])
        self.assertEqual(roundtrip, {"relocated": False, "build": False, "roundtrip": True, "consumer": False})
        self.assertEqual(consumed, {"relocated": False, "build": False, "roundtrip": False, "consumer": True})
        self.assertTrue(probes[2][0][0].startswith(str(consumer)))
        workflow = children[-1]
        self.assertEqual(workflow[0][-1], "import safeshift.pa3.native.workflow")
        self.assertTrue(workflow[1]["PYTHONPATH"].startswith(str(repo) + os.pathsep + str(consumer)))
        exported = " ".join(s for c in self.commands for s in c)
        self.assertNotIn(str(repo), exported)
        self.assertIn("<repo>", exported)

    def test_consumer_failure_writes_no_pass_receipt_and_keeps_evidence(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.run_prep(fail_consumer=True)
        self.assertFalse((self.output / "runtime_prep.json").exists())
        self.assertTrue(self.consumer.is_dir())
        self.assertTrue((self.output / prep.ARCHIVE).is_file())
        self.assertTrue(any(c[0].replace("\\", "/").startswith("<repo>/" + prep.CONSUMER_ROOT)
                            for c in self.commands))

    def test_existing_consumer_path_stops_before_any_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / prep.CONSUMER_ROOT).mkdir(parents=True)
            with patch.object(prep.platform, "system", return_value="Linux"), \
                 patch.object(prep.platform, "machine", return_value="x86_64"), \
                 patch.object(prep.subprocess, "run", side_effect=AssertionError("INSTALL")):
                with self.assertRaisesRegex(FileExistsError, "CONSUMER_RESTORE_PATH_EXISTS"):
                    prep.runtime(repo, repo / "data/processed/prep")
            self.assertFalse((repo / "data/processed/prep").exists())


class SourceSeparationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.repo = new_repo(self.tmp / "repo")
        self.offline = commit(self.repo, {"safeshift/pa3/native/prep.py": "v1", "configs/pins": "v1"})
        offline = patch.object(prep, "OFFLINE_SOURCE_COMMIT", self.offline)
        offline.start(); self.addCleanup(offline.stop)

    def test_prep_bundle_is_distinct_and_has_no_authority(self):
        head = commit(self.repo, {"safeshift/pa3/native/prep.py": "v2", "notes/x.md": "doc"})
        receipt = prep.bundle_prep_source(self.repo, self.tmp / "release")
        self.assertEqual(receipt["prep_source_commit"], head)
        self.assertEqual(receipt["offline_source_commit"], self.offline)
        self.assertEqual(receipt["changed_paths_since_offline_source"],
                         ["notes/x.md", "safeshift/pa3/native/prep.py"])
        self.assertFalse(receipt["execution_authority"])
        self.assertEqual(receipt["bundle"], "pa3_prep_source.bundle")
        self.assertNotEqual(receipt["bundle"], "pa3_source.bundle")
        self.assertEqual(receipt["bundle_sha256"], prep.digest(self.tmp / "release" / receipt["bundle"]))
        git_fixture(self.repo, "bundle", "verify", str(self.tmp / "release" / receipt["bundle"]))
        on_disk = json.loads((self.tmp / "release/pa3_prep_source_release.json").read_text())
        self.assertEqual(on_disk, receipt)

    def test_dirty_prep_source_is_refused(self):
        (self.repo / "configs/pins").write_text("dirty")
        with self.assertRaisesRegex(ValueError, "COMMIT_PREP"):
            prep.bundle_prep_source(self.repo, self.tmp / "release")
        self.assertFalse((self.tmp / "release").exists())

    def test_prep_source_that_changes_offline_execution_inputs_is_refused(self):
        for name in ("configs/pins", "safeshift/pa3/native/access.py", "prompts/c1.txt",
                     "notebooks/pa3_qwen2_5_kaggle.ipynb"):
            with self.subTest(name=name):
                head = commit(self.repo, {name: "changed " + name})
                with self.assertRaisesRegex(ValueError, "CHANGES_OFFLINE_EXECUTION_INPUTS:" + name):
                    prep.prep_source_scope(self.repo, head)
                git_fixture(self.repo, "reset", "-q", "--hard", self.offline)

    def test_prep_source_not_descending_from_offline_source_is_refused(self):
        git_fixture(self.repo, "checkout", "-q", "--orphan", "unrelated")
        unrelated = commit(self.repo, {"safeshift/pa3/native/prep.py": "other"})
        with self.assertRaisesRegex(ValueError, "NOT_DESCENDANT_OF_OFFLINE_SOURCE"):
            prep.prep_source_scope(self.repo, unrelated)
        with self.assertRaisesRegex(ValueError, "NOT_DESCENDANT_OF_OFFLINE_SOURCE"):
            prep.bundle_prep_source(self.repo, self.tmp / "release")
        with patch.object(prep, "OFFLINE_SOURCE_COMMIT", "f" * 40):
            with self.assertRaisesRegex(ValueError, "NOT_DESCENDANT_OF_OFFLINE_SOURCE"):
                prep.prep_source_scope(self.repo, unrelated)

    def test_cli_checks_source_scope_before_runtime_or_model(self):
        for kind in ("runtime", "model"):
            with self.subTest(kind=kind), \
                 patch.object(sys, "argv", ["prep", kind, "--output", "data/processed/x",
                                            "--execute-online-owner-prep"]), \
                 patch.object(prep, "prep_source_scope", side_effect=ValueError("SCOPE")), \
                 patch.object(prep, kind, side_effect=AssertionError("BUILT")):
                with self.assertRaisesRegex(ValueError, "SCOPE"):
                    prep.main()

    def test_offline_constant_is_the_reviewed_pr96_merge(self):
        self.assertEqual(prep.OFFLINE_SOURCE_COMMIT.__class__, str)
        source = Path(prep.__file__).read_text(encoding="utf-8")
        self.assertIn('OFFLINE_SOURCE_COMMIT = "13ea2fba67f36883518db8a2add1b249c951e48e"', source)


class PrepNotebookTests(unittest.TestCase):
    def setUp(self):
        nb = json.loads((ROOT / "notebooks/pa3_inputs_prep_kaggle.ipynb").read_text(encoding="utf-8"))
        self.settings_code = "".join(nb["cells"][1]["source"])
        self.bootstrap = "".join(nb["cells"][2]["source"])

    def test_online_notebook_pins_separate_source_and_receipt(self):
        code = self.settings_code + "\n" + self.bootstrap
        compile(code, "prep notebook", "exec")
        for value in ("PREP_SOURCE_COMMIT", "PREP_SOURCE_BUNDLE_SHA256", "prep_source_input.json",
                      prep.OFFLINE_SOURCE_COMMIT, "runtime-archive/pa3_runtime.tar.gz",
                      "pa3_runtime_inventory.json"):
            self.assertIn(value, code)
        self.assertNotIn('SOURCE_COMMIT = ""', code.replace('PREP_SOURCE_COMMIT = ""', ''))
        self.assertNotIn("ensurepip", code)
        settings = {}
        exec(self.settings_code, settings)
        self.assertEqual(settings["OFFLINE_SOURCE_COMMIT"], prep.OFFLINE_SOURCE_COMMIT)
        self.assertEqual(settings["PREP_SOURCE_COMMIT"], "")

    def run_bootstrap(self, settings, receipt=None, work=None):
        with patch.object(Path, "cwd", return_value=work), \
             patch.object(subprocess, "run", side_effect=AssertionError("CHECKOUT_OR_INSTALL")), \
             patch.object(subprocess, "check_output", side_effect=AssertionError("CHECKOUT")):
            exec(self.bootstrap, dict(settings))

    def test_notebook_rejects_source_mismatch_before_checkout_or_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); work = root / "working"; work.mkdir()
            # Kaggle may mount Datasets under /kaggle/input/datasets/<owner>/<dataset>/.
            source = root / "input/datasets/owner/pa3-reviewed-prep-source"; source.mkdir(parents=True)
            bundle = source / "pa3_prep_source.bundle"; bundle.write_bytes(b"synthetic bundle")
            settings = {"KIND": "runtime", "PREP_SOURCE_COMMIT": "a" * 40,
                        "PREP_SOURCE_BUNDLE_INPUT": "datasets/owner/pa3-reviewed-prep-source/pa3_prep_source.bundle",
                        "PREP_SOURCE_BUNDLE_SHA256": prep.digest(bundle),
                        "OFFLINE_SOURCE_COMMIT": prep.OFFLINE_SOURCE_COMMIT}
            receipt = {"schema": "pa3-online-prep-source-v1", "prep_source_commit": "a" * 40,
                       "bundle_sha256": prep.digest(bundle), "execution_authority": False,
                       "offline_source_commit": prep.OFFLINE_SOURCE_COMMIT}
            release = source / "pa3_prep_source_release.json"
            with self.assertRaisesRegex(ValueError, "PREP_RELEASE_RECEIPT_MISSING"):
                self.run_bootstrap(settings, work=work)
            for field, value in (("prep_source_commit", "b" * 40),
                                 ("offline_source_commit", "b" * 40),
                                 ("bundle_sha256", "0" * 64), ("execution_authority", True),
                                 ("schema", "pa3-source-release-v1")):
                release.write_text(json.dumps({**receipt, field: value}))
                with self.subTest(field=field):
                    with self.assertRaisesRegex(ValueError, "SEPARATE_REVIEWED_PREP"):
                        self.run_bootstrap(settings, work=work)
            release.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, "SOURCE_BUNDLE_CHECKSUM"):
                self.run_bootstrap({**settings, "PREP_SOURCE_BUNDLE_SHA256": "0" * 64}, work=work)
            with self.assertRaisesRegex(ValueError, "OFFLINE_SOURCE_COMMIT_IS_FIXED"):
                self.run_bootstrap({**settings, "OFFLINE_SOURCE_COMMIT": "b" * 40}, work=work)
            with self.assertRaisesRegex(ValueError, "SET_KIND_AND_REVIEWED_SOURCE_SHA"):
                self.run_bootstrap({**settings, "PREP_SOURCE_COMMIT": "13ea2fb"}, work=work)
            for bad in ("/kaggle/input/datasets/owner/x/pa3_prep_source.bundle", "../x.bundle"):
                with self.assertRaisesRegex(ValueError, "INPUT_RELATIVE_SOURCE_BUNDLE_REQUIRED"):
                    self.run_bootstrap({**settings, "PREP_SOURCE_BUNDLE_INPUT": bad}, work=work)
            # A correct receipt with the original OFFLINE bundle name is still refused.
            renamed = source / "pa3_source.bundle"; shutil.copy(bundle, renamed)
            with self.assertRaisesRegex(ValueError, "SEPARATE_REVIEWED_PREP"):
                self.run_bootstrap({**settings, "PREP_SOURCE_BUNDLE_INPUT":
                                    "datasets/owner/pa3-reviewed-prep-source/pa3_source.bundle"}, work=work)
            # All checks passed: only now would the clone run.
            with self.assertRaisesRegex(AssertionError, "CHECKOUT_OR_INSTALL"):
                self.run_bootstrap(settings, work=work)


@unittest.skipUnless(platform.system() == "Linux" and platform.machine() == "x86_64"
                     and os.environ.get("SAFESHIFT_PA3_LINUX_PREP") == "1",
                     "BLOCKED unless explicitly enabled on Linux x86_64 with Internet and runtime storage")
class RealLinuxRuntimeTests(unittest.TestCase):
    OUTPUT = ROOT / "data/processed/pa3-task6-linux-regression"

    def test_real_uv_pep668_failure_then_full_runtime_roundtrip(self):
        # Keep all downloaded/generated evidence in the ignored processed tree.
        output = self.OUTPUT
        output.mkdir(parents=True, exist_ok=False)
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONNOUSERSITE": "1",
               "UV_PYTHON_BIN_DIR": str(output / "bin")}
        env.pop("PYTHONPATH", None); env.pop("PYTHONHOME", None)
        for command in prep.commands(ROOT, output):
            subprocess.run(command, env=env, check=True)
        python = next((output / "managed").glob("*/bin/python3.11"))
        marker = python.parent.parent / "lib/python3.11/EXTERNALLY-MANAGED"
        self.assertTrue(marker.is_file())
        before = marker.read_bytes()
        failed = subprocess.run([str(python), "-m", "ensurepip"], env=env,
                                capture_output=True, text=True)
        (output / "original-ensurepip.log").write_text(failed.stdout + failed.stderr)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("externally-managed-environment", failed.stderr)
        self.assertEqual(before, marker.read_bytes())
        prep.runtime(ROOT, output / "fixed")
        receipt = json.loads((output / "fixed/runtime_prep.json").read_text())
        self.assertEqual(receipt["software"], plan("qwen2_5", ROOT)["software"])
        self.assertEqual(receipt["status"], "CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN")
        self.assertEqual(len(receipt["checks"]), 4)
        self.assertEqual(set(receipt["checks"].values()), {"PASS"})
        for name in ("relocated", "build", "archive-roundtrip"):
            self.assertFalse((output / "fixed" / name).exists())
        self.assertFalse((ROOT / prep.CONSUMER_ROOT).exists())

    def test_restored_archive_through_unchanged_offline_launcher_path(self):
        # Fresh process after prep finished: the OFFLINE launcher's verify + select.
        fixed = self.OUTPUT / "fixed"
        receipt = json.loads((fixed / "runtime_prep.json").read_text())
        archive, inventory = fixed / receipt["archive"], fixed / receipt["inventory"]
        verify_runtime_input(archive, inventory, receipt["inventory_sha256"])
        consumer = ROOT / prep.CONSUMER_ROOT
        self.assertFalse(consumer.exists())
        self.addCleanup(shutil.rmtree, consumer, True)
        env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONNOUSERSITE": "1"}
        env.pop("PYTHONPATH", None); env.pop("PYTHONHOME", None)
        run = lambda c, e: subprocess.run(c, env=e, check=True)
        selected, _, links = prep.probe_runtime(ROOT, archive, consumer, env, run)
        self.assertEqual(links, receipt["symlinks"])
        self.assertEqual(selected["software_versions"], receipt["software"])
        prep.probe_offline_child(ROOT, selected, env, run)


if __name__ == "__main__":
    unittest.main()
