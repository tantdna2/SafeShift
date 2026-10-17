"""Offline synthetic Run All, source topology, isolated env and failure tests."""

import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.one_click import bootstrap as boot, orchestrate as flow, provision, worker
from safeshift.diagnostics.one_click.artifacts import package, sha256, write
from safeshift.diagnostics.one_click.contract import AUTHORITY, BASE_SHA, LOCK, MODELS, NOTEBOOK, ORDER, authorize, canonical, scope, synthetic_png, template
from safeshift.diagnostics.hnlo_capture import Capture, persist_hf
from tests.test_hnlo_capture import CANDIDATES, TOK, metadata, output

ROOT = Path(__file__).resolve().parents[1]


def source():
    return {"merge_commit": "a" * 40, "implementation_commit": "b" * 40, "payload_sha256": "c" * 64,
            "github_pr": {"fixture": "SYNTHETIC_NOT_GITHUB_EVIDENCE"}}


def approved():
    value = template()
    value["grant"] = {"approved_by": "Synthetic Lead", "role": "Research Lead", "approved_utc": "2026-10-17T00:00:00Z",
        "decision_url": "https://github.com/tantdna2/SafeShift/pull/1#issuecomment-synthetic",
        "independent_audit_url": "https://github.com/tantdna2/SafeShift/pull/1#issuecomment-synthetic-audit",
        "implementation_commit": "b" * 40, "source_payload_sha256": "c" * 64, "attempt_id": "fake-cpu-only",
        **{flag: True for flag in ("provisioning_approved", "gpu_probe_approved", "technical_probe_exception_approved",
                                  "raw_provenance_criteria_approved", "numerical_tolerance_approved", "artifact_retention_approved")}}
    return value


class FakeOperations(flow.Operations):
    """Produces only synthetic CPU vectors, using the merged capture/replay code."""
    failure = None
    events = []

    def preflight(self):
        self.events.append(("preflight",))
        if self.failure == "missinggpu":
            raise RuntimeError("EXACT_HOST_T4_X2_REQUIRED")
        return {"kind": "FAKE_CPU", "gpu_executed": False}

    def prepare(self, model):
        self.events.append(("prepare", model))
        (self.evidence / model).mkdir()
        write(self.evidence / model / "fake-provision.json", {"kind": "FAKE_CPU_NO_DOWNLOAD"})
        if model == "internvl3" and self.failure in ("download", "checksum"):
            raise RuntimeError("DOWNLOAD_FAILED" if self.failure == "download" else "CHECKSUM_MISMATCH")
        return {"status": "FAKE_CPU_ONLY"}

    def worker(self, mode, model):
        self.events.append((mode, model))
        state = worker.empty(model)
        state.update(environment="EXACT_MATCH_FAKE", result="ENVIRONMENT_VALID")
        state["memory_after"] = {"synthetic_phase": mode}
        if mode == "inspect":
            if model == "internvl3" and self.failure == "environment":
                state.update(environment="FAIL", result="FAILED", reason="ENVIRONMENT_MISMATCH")
            return state
        if mode == "replay":
            state.update(worker.replay(self.work, "hnlo-" + self.grant["attempt_id"] + "-" + model, TOK))
            state["result"] = "TECHNICAL_VALID" if state["TECHNICAL_HNLO_VALID"] else "N/A"
            return state
        directory = self.evidence / model / "probe"
        directory.mkdir()
        for kind in ("load", "generate"):
            write(directory / ("native-" + kind + "-start.json"), {"kind": "FAKE_CPU"})
        state.update(load_calls=1, generate_calls=1, t1="PASS_28_OF_28")
        if model == "internvl3" and self.failure == "oom":
            state.update(result="FAILED", reason="FAKE_CUDA_OOM")
            return state
        if model == "internvl3" and self.failure == "killed":
            raise RuntimeError("WORKER_TERMINATED_WITHOUT_FINAL_RECORD:-9")
        doc = metadata(model)
        doc["run_id"] = "hnlo-" + self.grant["attempt_id"] + "-" + model
        cap = Capture(self.work, doc)
        cap.runtime_t1(TOK)
        cap.write("raw-provenance", {"processors": [], "criterion": "EMPTY_ACTUAL_PROCESSOR_LIST_WITH_PINNED_GREEDY_GENERATION_SOURCE"})
        cap.write("stopping-criteria", {"classes": ["MaxLengthCriteria", "EosTokenCriteria"]})
        native = output()
        if model == "internvl3":
            if self.failure == "invalid":
                native = output("invalid response")
            if self.failure == "wrongalignment":
                # Special token removed by decode, but not terminal EOS.
                native.sequences.data[0].insert(3, 999)
                native.logits.insert(0, native.logits[-1])
                native.scores.insert(0, native.scores[-1])
            if self.failure == "nonfinite":
                native.logits[0].data[0][1] = float("nan")
            if self.failure == "torn":
                (cap.journal.root / "raw-000.json").write_bytes(b'{"interrupted":')
                state.update(result="FAILED", reason="TORN_WRITE:raw-000", common_fatal=True)
                return state
        persist_hf(native, [11, 22, 33], CANDIDATES, TOK, cap, {"eos_token_id": 999}, {"do_sample": False})
        cap.journal.seal()
        write(directory / "native-load-return.json", {"kind": "FAKE_CPU"})
        write(directory / "native-generate-return.json", {"kind": "FAKE_CPU"})
        state["result"] = "AWAITING_CPU_REPLAY"
        return state

    def release(self, model):
        self.events.append(("release", model))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo, self.out = self.root / "repo", self.root / "out"
        self.repo.mkdir()
        self.out.mkdir()
        write(self.repo / AUTHORITY, approved())
        self.events = []

    def run_flow(self, failure=None, name="session"):
        work = self.out / name
        work.mkdir()
        fake = type("IsolatedFake", (FakeOperations,), {"failure": failure, "events": self.events})
        with redirect_stdout(io.StringIO()):
            result = flow.run(self.repo, work, self.out, source(), operations_factory=fake)
        return result, work


class FlowTests(Fixture):
    def test_two_models_order_one_call_each_and_real_cpu_replay(self):
        result, work = self.run_flow()
        self.assertEqual(result["result"], "TECHNICAL_VALID")
        self.assertEqual([e for e in self.events if e[0] in ("probe", "release", "replay")],
                         [(mode, model) for model in ORDER for mode in ("probe", "release", "replay")])
        last_prepare = max(i for i, e in enumerate(self.events) if e[0] == "prepare")
        first_probe = min(i for i, e in enumerate(self.events) if e[0] == "probe")
        self.assertLess(last_prepare, first_probe)
        self.assertFalse((self.repo / "data/processed/hnlo_capture").exists())
        self.assertTrue((work / "data/processed/hnlo_capture/hnlo-fake-cpu-only-internvl3/raw-000.json").is_file())
        for row in result["models"]:
            self.assertEqual((row["load_calls"], row["generate_calls"]), (1, 1))
            self.assertTrue(row["CAPTURE_VALID"] and row["ALIGNMENT_VALID"] and row["TECHNICAL_HNLO_VALID"])
            self.assertFalse(row["HNLO_RESEARCH_VERIFIED"])
            self.assertIsInstance(row["hnlo"], float)
            self.assertEqual(row["memory_after"]["synthetic_phase"], "probe")
            self.assertEqual(row["cpu_replay_memory_after"]["synthetic_phase"], "replay")
        archive = self.out / (work.name + ".tar.gz")
        proof = json.loads((self.out / (work.name + "_sha256.json")).read_bytes())
        self.assertEqual(sha256(archive), proof["sha256"])
        with tarfile.open(archive) as stream:
            names = stream.getnames()
            self.assertTrue(any("internvl3/capture/raw-000" in n for n in names))
            self.assertTrue(any("qwen3/capture/raw-000" in n for n in names))

    def test_model_local_failures_continue_without_retry(self):
        for failure in ("download", "environment", "invalid", "oom", "wrongalignment", "nonfinite"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                # Independent attempt storage for each synthetic test.
                self.out = Path(temp)
                self.events.clear()
                result, _ = self.run_flow(failure)
                first, second = result["models"]
                self.assertIsNone(first["hnlo"])
                self.assertFalse(first["TECHNICAL_HNLO_VALID"])
                self.assertTrue(second["TECHNICAL_HNLO_VALID"])
                self.assertLessEqual(self.events.count(("probe", "internvl3")), 1)
                self.assertEqual(self.events.count(("probe", "qwen3")), 1)

    def test_common_failures_stop_second_model_and_package_partial(self):
        for failure in ("missinggpu", "checksum", "torn", "killed"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temp:
                self.out = Path(temp)
                self.events.clear()
                result, work = self.run_flow(failure)
                self.assertNotIn(("probe", "qwen3"), self.events)
                self.assertFalse(result["models"][1]["TECHNICAL_HNLO_VALID"])
                self.assertTrue((self.out / (work.name + ".tar.gz")).is_file())
                if failure == "torn":
                    with tarfile.open(self.out / (work.name + ".tar.gz")) as archive:
                        member = archive.extractfile("evidence/internvl3/capture/raw-000.json")
                        self.assertEqual(member.read(), b'{"interrupted":')
                if failure == "killed":
                    self.assertEqual(result["models"][0]["generate_calls"], 1)

    def test_grant_missing_no_provision_or_gpu(self):
        (self.repo / AUTHORITY).write_text(json.dumps(template()))
        result, _ = self.run_flow()
        self.assertFalse(self.events)
        self.assertEqual(result["result"], "BLOCKED")
        self.assertEqual(result["gpu_probe_status"], "NOT_RUN")

    def test_second_run_all_same_attempt_blocked_with_no_second_calls(self):
        self.run_flow()
        before = list(self.events)
        second, _ = self.run_flow(name="second-session")
        self.assertEqual(self.events, before)
        self.assertEqual(second["result"], "BLOCKED")

    def test_partial_archive_write_never_becomes_pass(self):
        with patch.object(flow, "package", side_effect=OSError("DISK_FULL")):
            result, work = self.run_flow("oom")
        self.assertTrue((work / "evidence/result.json").exists())
        self.assertTrue((self.out / (work.name + "_export_failure.json")).exists())
        self.assertEqual(result["result"], "EXPORT_FAILED")

    def test_notebook_single_code_cell_run_all_simulation(self):
        notebook = json.loads((ROOT / NOTEBOOK).read_bytes())
        code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(code_cells), 1)
        code = "".join(code_cells[0]["source"])
        tree = ast.parse(code)
        namespace = {"__name__": "__notebook__"}
        # Declarations and the one invocation execute from the actual cell AST;
        # replace only external I/O with the synthetic CPU operations boundary.
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), NOTEBOOK, "exec"), namespace)
        work = self.out / "notebook-session"
        work.mkdir()
        namespace["fetch_source"] = lambda session: (self.repo, source())
        original = flow.run
        fake = type("NotebookFake", (FakeOperations,), {"events": self.events, "failure": None})
        with patch.object(flow, "run", side_effect=lambda repo, session, out, src: original(repo, session, out, src, operations_factory=fake)), redirect_stdout(io.StringIO()):
            # Same bootstrap invocation, with only the test's output venue changed.
            namespace["bootstrap"].__defaults__ = (self.out,)
            exec(compile(ast.Module(body=tree.body[-1:], type_ignores=[]), NOTEBOOK, "exec"), namespace)
        self.assertEqual(namespace["result"]["result"], "TECHNICAL_VALID")
        self.assertEqual(self.events.count(("probe", "qwen3")), 1)

    def test_bootstrap_failure_exports_specific_blocked_report(self):
        with patch.object(boot, "fetch_source", side_effect=PermissionError("DRAFT_OR_UNMERGED_SOURCE_NO_EXECUTION")), redirect_stdout(io.StringIO()):
            result = boot.bootstrap(self.out)
        self.assertEqual(result["result"], "BLOCKED")
        self.assertEqual(len(list(self.out.glob("*.tar.gz"))), 1)
        self.assertTrue(all(row["generate_calls"] == 0 for row in result["models"]))


class ContractTests(unittest.TestCase):
    def test_notebook_json_compiles_and_binds_complete_source_payload(self):
        notebook = json.loads((ROOT / NOTEBOOK).read_bytes())
        self.assertEqual((notebook["nbformat"], notebook["nbformat_minor"]), (4, 5))
        self.assertEqual(len({c["id"] for c in notebook["cells"]}), len(notebook["cells"]))
        cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["outputs"], [])
        self.assertIsNone(cells[0]["execution_count"])
        code = "".join(cells[0]["source"])
        compile(code, NOTEBOOK, "exec")
        module = ast.parse(code)
        assigned = next(n.value.value for n in module.body if isinstance(n, ast.Assign)
                        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == "PAYLOAD_SHA256")
        lock = json.loads((ROOT / LOCK).read_bytes())
        self.assertEqual(hashlib.sha256(canonical(lock)).hexdigest(), assigned)
        normalized = code.replace('PAYLOAD_SHA256 = "' + assigned + '"', 'PAYLOAD_SHA256 = "' + "0" * 64 + '"')
        expected = (ROOT / "safeshift/diagnostics/one_click/bootstrap.py").read_text(encoding="utf-8")
        self.assertEqual(normalized, expected + "\n# The single Run All entrypoint.\nresult = bootstrap()\n")
        # A released notebook binds its historical F1 bytes, not future code.
        grant = json.loads((ROOT / AUTHORITY).read_bytes()).get("grant")
        historical = None
        if grant:
            archive = subprocess.check_output(["git", "-C", str(ROOT), "archive", grant["implementation_commit"]])
            historical = self.enterContext(tarfile.open(fileobj=io.BytesIO(archive)))
        for row in lock["files"]:
            content = historical.extractfile(row["path"]).read() if historical else (ROOT / row["path"]).read_bytes()
            if row["path"] == NOTEBOOK:
                content = boot.notebook_bytes(content)
            self.assertEqual(hashlib.sha256(content).hexdigest(), row["sha256"], row["path"])

    def test_environment_builds_use_distinct_exact_interpreters(self):
        commands = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(provision, "fetch"), patch.object(provision, "extract"), patch.object(
                provision, "invoke", side_effect=lambda command, cwd, log, env=None: commands.append((command, env))):
                intern = provision.build_environment("internvl3", ROOT, root / "intern", root / "e-intern")
                qwen = provision.build_environment("qwen3", ROOT, root / "qwen", root / "e-qwen")
            self.assertEqual(intern.name, "python3.11")
            self.assertEqual(qwen.name, "python3.12")
            self.assertNotEqual(intern.parent.parent, qwen.parent.parent)
            installs = [c for c, env in commands if "--only-binary=:all:" in c]
            self.assertEqual(len(installs), 2)
            self.assertIn("torch==2.6.0+cu124", installs[0])
            self.assertIn("torch==2.10.0+cu128", installs[1])
            self.assertNotIn("torch==2.10.0+cu128", installs[0])
            self.assertTrue(any(Path(env.get("ZLIB_CFLAGS", "")[2:]).as_posix().endswith("qwen/zlib/include") for c, env in commands))

    def test_tracked_authority_contract_preserved_after_release(self):
        self.assertEqual({**json.loads((ROOT / AUTHORITY).read_bytes()), "grant": None}, template())
        self.assertEqual(list(scope()["models"]), list(ORDER))
        self.assertFalse(scope()["dataset_access"])
        self.assertFalse(scope()["research_verified"])

    def test_grant_bindings_flags_and_foreign_models_rejected(self):
        authorize(approved(), source())
        for key in approved()["grant"]:
            value = approved()
            del value["grant"][key]
            with self.subTest(key=key), self.assertRaises(PermissionError):
                authorize(value, source())
        for mutate in (lambda v: v["scope"].update(max_new_tokens=33),
                       lambda v: v["scope"]["models"].update(moondream={}),
                       lambda v: v["grant"].update(implementation_commit="f" * 40),
                       lambda v: v["grant"].update(gpu_probe_approved=False)):
            value = approved()
            mutate(value)
            with self.assertRaises(PermissionError):
                authorize(value, source())

    def test_fixed_rgb_png_matches_hash_and_pixels(self):
        from PIL import Image
        data = synthetic_png()
        self.assertEqual(hashlib.sha256(data).hexdigest(), scope()["input_sha256"])
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual((image.mode, image.size, image.getextrema()), ("RGB", (448, 448), ((128, 128),) * 3))

    def test_subprocess_environment_separates_gpu_and_libraries(self):
        with patch.dict(os.environ, {"HF_TOKEN": "SECRET_SENTINEL", "PYTHONHOME": "wrong", "CUDA_VISIBLE_DEVICES": "4", "PYTORCH_CUDA_ALLOC_CONF": "bad"}):
            intern = flow.child_environment("internvl3", ROOT, "data/processed/cache-intern")
            qwen = flow.child_environment("qwen3", ROOT, "data/processed/cache-qwen")
            replay_env = flow.child_environment("qwen3", ROOT, "data/processed/cache-qwen", cpu=True)
        self.assertEqual(intern["CUDA_VISIBLE_DEVICES"], "0")
        self.assertEqual(qwen["CUDA_VISIBLE_DEVICES"], "0,1")
        self.assertEqual(replay_env["CUDA_VISIBLE_DEVICES"], "")
        self.assertNotEqual(intern["HF_HUB_CACHE"], qwen["HF_HUB_CACHE"])
        for env in (intern, qwen, replay_env):
            self.assertNotIn("HF_TOKEN", env)
            self.assertNotIn("PYTHONHOME", env)
            self.assertNotIn("PYTORCH_CUDA_ALLOC_CONF", env)
            self.assertEqual(env["HF_HUB_OFFLINE"], "1")

    def test_environment_real_version_and_gpu_checks_with_fakes(self):
        from safeshift.protocol.classification_policy import load_policy
        for model in ORDER:
            expected = load_policy(ROOT, qwen3_runtime=True)["classification"][model]["software_versions"]
            if model == "qwen3":
                expected = {**expected, **json.loads((ROOT / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())["qwen3_additional_pins"]}
            count = 1 if model == "internvl3" else 2
            cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: count,
                get_device_properties=lambda i: SimpleNamespace(name="Tesla T4", major=7, minor=5, total_memory=15 * 2**30),
                mem_get_info=lambda i: (14 * 2**30, 15 * 2**30))
            torch = SimpleNamespace(cuda=cuda, version=SimpleNamespace(cuda=MODELS[model]["cuda"]))
            with patch("platform.system", return_value="Linux"), patch("platform.machine", return_value="x86_64"), patch("platform.python_version", return_value=MODELS[model]["python"]), patch("zlib.ZLIB_RUNTIME_VERSION", "1.2.11"), patch("zlib.ZLIB_VERSION", "1.2.11"), patch("importlib.metadata.version", side_effect=expected.__getitem__), patch("importlib.metadata.distributions", return_value=[]), patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": MODELS[model]["cuda_visible_devices"]}):
                self.assertEqual(worker.environment(model, ROOT, torch)["actual"], expected)
                cuda.device_count = lambda: 0
                with self.assertRaisesRegex(ValueError, "EXACT_CUDA"):
                    worker.environment(model, ROOT, torch)

    def test_native_counters_reject_second_load_and_generate(self):
        class Native:
            @classmethod
            def from_pretrained(cls):
                return cls()

            def generate(self):
                return "UNCHANGED_NATIVE_RESULT"

        module = SimpleNamespace(InternVLForConditionalGeneration=Native)
        with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"transformers": module}):
            state = worker.empty("internvl3")
            with worker.count_native("internvl3", Path(temp), state):
                model = Native.from_pretrained()
                self.assertEqual(model.generate(), "UNCHANGED_NATIVE_RESULT")
                with self.assertRaisesRegex(RuntimeError, "SECOND_MODEL_LOAD"):
                    Native.from_pretrained()
                with self.assertRaisesRegex(RuntimeError, "SECOND_GENERATE"):
                    model.generate()
            self.assertEqual((state["load_calls"], state["generate_calls"]), (1, 1))

    def test_actual_processor_observer_preserves_empty_list_and_rejects_unproved_raw(self):
        for processors in ([], [object()]):
            records = {}

            class Native:
                @classmethod
                def from_pretrained(cls):
                    return cls()

                def _get_logits_processor(self):
                    return processors

                def _get_stopping_criteria(self):
                    return [type("MaxLengthCriteria", (), {"max_length": 42})()]

                def generate(self):
                    self._get_logits_processor()
                    self._get_stopping_criteria()
                    return "NATIVE_UNCHANGED"

            module = SimpleNamespace(InternVLForConditionalGeneration=Native)
            with tempfile.TemporaryDirectory() as temp, patch.dict(sys.modules, {"transformers": module}):
                cap = SimpleNamespace(write=lambda name, value: records.update({name: value}))
                with worker.count_native("internvl3", Path(temp), worker.empty("internvl3"), cap):
                    native = Native.from_pretrained()
                    if processors:
                        with self.assertRaisesRegex(ValueError, "UNVERIFIED_RAW_LOGIT_PROCESSOR"):
                            native.generate()
                    else:
                        self.assertEqual(native.generate(), "NATIVE_UNCHANGED")
                        self.assertEqual(records["raw-provenance"]["processors"], [])
                        self.assertEqual(records["stopping-criteria"]["classes"], ["MaxLengthCriteria"])
            self.assertEqual(len(processors), len(records["raw-provenance"]["processors"]))

    @unittest.skipUnless(sys.platform == "linux", "Native seccomp requires Linux; no GPU implication")
    def test_native_seccomp_in_fresh_cpu_child(self):
        code = ("from safeshift.diagnostics.one_click.network import deny_inet; "
                "print(deny_inet()); import socket; "
                "s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); s.close()")
        process = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("SECCOMP", process.stdout)

    def test_download_hash_failure_retains_original_bytes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(provision, "urlopen", return_value=io.BytesIO(b"corrupt")):
            path = Path(temp) / "source.tar.xz"
            with self.assertRaisesRegex(ValueError, "DOWNLOAD_CHECKSUM_MISMATCH"):
                provision.fetch("https://official.invalid/pinned", path, "0" * 64)
            self.assertEqual(path.read_bytes(), b"corrupt")

    def test_snapshot_checksum_inventory_and_revision_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / MODELS["qwen3"]["revision"]
            snapshot.mkdir()
            (snapshot / "one").write_bytes(b"bad")
            rows = [{"path": "one", "size_bytes": 3, "hash_algorithm": "sha256", "expected_hash": "0" * 64}]
            with patch.object(provision, "qwen_files", return_value=rows):
                with self.assertRaisesRegex(ValueError, "CHECKSUM"):
                    provision.verify_qwen(snapshot, root)
                (snapshot / "unexpected").touch()
                with self.assertRaisesRegex(ValueError, "INVENTORY"):
                    provision.verify_qwen(snapshot, root)

    def test_no_forced_checkpoint_defaults(self):
        for field in ("forced_bos_token_id", "forced_eos_token_id", "forced_decoder_ids", "force_words_ids", "constraints"):
            with self.assertRaisesRegex(ValueError, "FORCING"):
                worker.no_forcing(SimpleNamespace(to_dict=lambda: {field: [1]}))

    def test_package_integrity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence = root / "evidence"
            evidence.mkdir()
            (evidence / "torn.json").write_bytes(b'{"broken"')
            archive = package(evidence, root, "test")
            self.assertTrue(archive.is_file())
            with self.assertRaises(FileExistsError):
                package(evidence, root, "test")


class SourceTests(unittest.TestCase):
    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True, stderr=subprocess.STDOUT).strip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.git("init")
        self.git("config", "user.name", "Synthetic")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.git("config", "core.autocrlf", "false")
        (self.repo / "code.py").write_bytes(b"# synthetic\n")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.git("branch", "-M", "main")
        self.git("checkout", "-b", boot.HEAD_BRANCH)
        write(self.repo / AUTHORITY, {"grant": None, "scope": "synthetic"})
        lock = {"schema": "hnlo-source-lock-v1", "base_sha": self.base, "files": [
            {"path": "code.py", "sha256": sha256(self.repo / "code.py")}]}
        write(self.repo / LOCK, lock)
        self.payload = hashlib.sha256(canonical(lock)).hexdigest()
        self.git("add", ".")
        self.git("commit", "-m", "F1")
        self.f1 = self.git("rev-parse", "HEAD")
        (self.repo / AUTHORITY).write_text(json.dumps({"grant": {"fixture": True}, "scope": "synthetic"}))
        self.git("add", ".")
        self.git("commit", "-m", "F2 authority only")
        self.f2 = self.git("rev-parse", "HEAD")
        self.git("checkout", "main")
        self.git("merge", "--no-ff", boot.HEAD_BRANCH, "-m", "standard merge")
        self.merge = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/remotes/origin/main", self.merge)
        self.pr = {"merged_at": "synthetic", "draft": False, "base": {"ref": "main"},
                   "head": {"ref": boot.HEAD_BRANCH, "sha": self.f2, "repo": {"full_name": boot.REPO}},
                   "merge_commit_sha": self.merge, "html_url": "https://github.com/tantdna2/SafeShift/pull/1", "number": 1}

    def test_real_git_f1_f2_merge_and_locked_tree(self):
        with patch.object(boot, "BASE_SHA", self.base):
            proof = boot.verify_topology(self.repo, self.pr, self.payload)
            self.assertEqual(proof["implementation_commit"], self.f1)
            (self.repo / "code.py").write_bytes(b"# altered\n")
            with self.assertRaisesRegex(ValueError, "AUDITED_FILE"):
                boot.verify_topology(self.repo, self.pr, self.payload)

    def test_unmerged_wrong_base_wrong_head_and_mutable_checkout_rejected(self):
        for mutation in (lambda p: p.update(merged_at=None), lambda p: p["head"].update(sha="f" * 40),
                         lambda p: p["base"].update(ref="other"), lambda p: p.update(draft=True)):
            pr = deepcopy(self.pr)
            mutation(pr)
            with patch.object(boot, "BASE_SHA", self.base), self.assertRaises(PermissionError):
                boot.verify_topology(self.repo, pr, self.payload)
        self.git("checkout", "--detach", self.f2)
        with patch.object(boot, "BASE_SHA", self.base), self.assertRaisesRegex(PermissionError, "EXACT_RELEASE_CHECKOUT"):
            boot.verify_topology(self.repo, self.pr, self.payload)

    def test_source_lock_and_added_inventory_rejected(self):
        with patch.object(boot, "BASE_SHA", self.base):
            with self.assertRaisesRegex(ValueError, "PAYLOAD_MISMATCH"):
                boot.verify_payload(self.repo, "0" * 64)
            (self.repo / "extra.py").write_text("# extra")
            self.git("add", "extra.py")
            with self.assertRaisesRegex(ValueError, "INVENTORY"):
                boot.verify_payload(self.repo, self.payload)

    def test_extra_code_in_authority_commit_rejected(self):
        self.git("checkout", "-b", "changed-authority", self.f1)
        (self.repo / AUTHORITY).write_text(json.dumps({"grant": {"fixture": True}, "scope": "synthetic"}))
        (self.repo / "code.py").write_bytes(b"# code changed in F2\n")
        self.git("add", ".")
        self.git("commit", "-m", "invalid F2")
        bad_head = self.git("rev-parse", "HEAD")
        self.git("checkout", "-b", "other-main", self.base)
        self.git("merge", "--no-ff", bad_head, "-m", "invalid release merge")
        self.pr["head"]["sha"] = bad_head
        self.pr["merge_commit_sha"] = self.git("rev-parse", "HEAD")
        with patch.object(boot, "BASE_SHA", self.base), self.assertRaisesRegex(PermissionError, "AUTHORITY_ONLY_CHILD"):
            boot.verify_topology(self.repo, self.pr, self.payload)


if __name__ == "__main__":
    unittest.main()
