"""End-to-end offline integration tests for PR177-vs-TRAIN3763 parity and Attempt 3 recovery.

Exercises real launcher -> stage supervisor -> setup provisioner -> worker -> grammar V2
capture/parser -> ZIP/sidecar -> pinned SDK GetKernel/output serializers -> verifier ->
mirrored campaign ledger -> measurement -> shard planning without network, GPU, weights or TEST.
"""
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import timedelta
import hashlib
import importlib.util
import json
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit
import zipfile

_TESTS_DIR = str(Path(__file__).resolve().parent)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

import test_internvl3763 as controller_fixtures
from test_internvl3763_campaign import fixture as campaign_fixture, synthetic_bytes, synthetic_cohort
from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as campaign
from safeshift import internvl3763_operator as op
from safeshift import internvl3763_python as py
from safeshift import internvl3763_release as release
from safeshift import kaggle_handoff as handoff
from safeshift.pilot.artifacts import export, read, sha, write
from safeshift.pilot.contract import MASTER_SHA, PROMPT_SHA, digest, json_bytes


HAS_KAGGLESDK = importlib.util.find_spec("kagglesdk") is not None
HAS_TORCH = (
    importlib.util.find_spec("torch") is not None
    and importlib.util.find_spec("transformers") is not None
    and importlib.util.find_spec("tokenizers") is not None
)


@contextmanager
def cross_platform_stage_runner():
    """Run real child OS processes with exclusive log creation on non-Linux hosts."""
    import scripts.internvl3763 as launcher
    if sys.platform == "linux":
        yield
        return

    def run_windows_stage(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_roots=()):
        log, receipt = Path(log), Path(receipt)
        runtime.require(not receipt.exists(), "SUPERVISOR_RECEIPT_EXISTS")
        merged_env = {k: v for k, v in os.environ.items() if k in ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP", "PATH")}
        merged_env.update(env)
        begun = time.monotonic()
        reason, code, total_bytes = None, None, 0
        with log.open("xb") as stream:
            proc = subprocess.Popen(command, cwd=cwd, env=merged_env, stdout=stream, stderr=subprocess.STDOUT)
            code = proc.wait(timeout=max(1.0, deadline - time.monotonic()))
            stream.flush()
            self_stat = os.fstat(stream.fileno())
            total_bytes = self_stat.st_size
            for folder in watch_log_roots:
                root = Path(folder)
                if root.is_dir():
                    for entry in root.iterdir():
                        if entry.suffix == ".log" and entry.resolve() != log.resolve():
                            total_bytes += entry.stat().st_size
            if total_bytes > max_log_bytes:
                reason = "LOG_BUDGET_EXCEEDED"
            else:
                reason = "EXITED" if code == 0 else "CHILD_FAILURE"
        write(receipt, {"schema": "fresh-process-supervision-v1", "status": reason,
            "returncode": code, "seconds": time.monotonic() - begun, "log_bytes": total_bytes,
            "group_kill_sent": True, "automatic_retry": False,
            "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
        if reason != "EXITED":
            raise RuntimeError("SUPERVISED_" + reason)
        return {"status": reason, "returncode": code}

    with patch.object(launcher, "run_stage", side_effect=run_windows_stage):
        yield


def write_setup_harness(target_dir, *, fail_during_setup=False):
    """Create an offline Python shim that invokes real scripts.internvl_v2 setup -> prepare_runtime."""
    shim = Path(target_dir) / "offline_setup_harness.py"
    shim.write_text(
        f"""import os, pathlib, subprocess, sys
from unittest.mock import patch
sys.path.insert(0, {str(runtime.ROOT)!r})
from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import write
from scripts import internvl_v2
sys.path.insert(0, str(pathlib.Path({str(runtime.ROOT)!r}) / "tests"))
from safeshift import internvl3763_python as py
from test_internvl3763_python import synthetic_mount

fail_setup = {bool(fail_during_setup)!r}
print("SETUP_SUPERVISOR_STREAM_HEADER", flush=True)

def fake_probe(candidate, env):
    p = pathlib.Path(candidate)
    if "venv3119" in p.as_posix():
        return {{"path": str(p), "eligible": True, "version": [3, 11, 9], "prefix": str(p.parent.parent), "executable": str(p)}}
    return {{"path": str(p), "eligible": True, "version": [3, 11, 9], "prefix": str(p.parent), "executable": str(p)}}

def fake_run(argv, *, env=None, stdout=None, stderr=None, check=False, timeout=None, **kwargs):
    line = "OFFLINE_SETUP_STEP:" + " ".join(map(str, argv[:4])) + "\\n"
    if stdout is not None and hasattr(stdout, "write"):
        stdout.write(line.encode("utf8"))
        stdout.flush()
    if "--without-pip" in argv:
        venv_root = pathlib.Path(argv[-1])
        (venv_root / "bin").mkdir(parents=True, exist_ok=True)
        (venv_root / "lib").mkdir(parents=True, exist_ok=True)
        (venv_root / "bin/python").write_text("#!/bin/sh\\n", encoding="utf8")
    if fail_setup and "install" in argv:
        raise subprocess.CalledProcessError(1, argv)
    return subprocess.CompletedProcess(argv, 0)

wheel_dummy = pathlib.Path(sys.argv[sys.argv.index("--scratch") + 1]) / "pip_wheel_dummy.whl"

def fake_fetch(repo, scratch):
    wheel_dummy.parent.mkdir(parents=True, exist_ok=True)
    wheel_dummy.write_bytes(b"SYNTHETIC_WHEEL")
    return wheel_dummy, {{"wheel": wheel_dummy.name, "offline": True}}

with patch.object(boot, "interpreter_candidates", return_value=[pathlib.Path({str(sys.executable)!r})]), \\
        patch.object(boot, "probe_interpreter", side_effect=fake_probe), \\
        patch.object(boot, "pip_controller_probe", return_value={{"isolated": True}}), \\
        patch.object(boot, "fetch_pip_bootstrap", side_effect=fake_fetch), \\
        patch.object(boot, "pip_bootstrap_command", return_value=["pip-bootstrap", "offline"]), \\
        patch.object(boot, "inspect_worker_pip", return_value={{"version": "25.0.1"}}), \\
        patch("safeshift.candidates.train_runtime.subprocess.run", side_effect=fake_run), \\
        patch("safeshift.candidates.train_runtime.subprocess.check_output", return_value=b"pip==25.0.1\\ntorch==2.6.0+cu124\\n"):
    if "--request" in sys.argv and sys.argv[sys.argv.index("--request")+1] != "None":
        args = sys.argv
        inputs = pathlib.Path(args[args.index("--inputs")+1])
        with synthetic_mount(inputs), patch.object(py.train_python, "urlopen", side_effect=AssertionError("NO_PYTHON_DOWNLOAD")) as network:
            py.setup(args[args.index("--request")+1], args[args.index("--output")+1],
                args[args.index("--scratch")+1], inputs, __import__("time").monotonic()+60)
            network.assert_not_called()
        raise SystemExit(0)
    raise SystemExit(internvl_v2.main(sys.argv[1:]))
""",
        encoding="utf8",
    )
    return shim


class LauncherSupervisorSetupCompositionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_old_same_path_log_reproduces_exact_setup_log_file_exists_collision(self):
        shim = write_setup_harness(self.root)
        setup_dir = self.root / "setup"
        scratch_dir = self.root / "scratch"
        inputs_dir = self.root / "inputs"
        setup_dir.mkdir()
        scratch_dir.mkdir()
        inputs_dir.mkdir()
        spec_path = setup_dir / "source.json"
        write(spec_path, runtime.capture.source_spec())
        # Pre-fix bug: parent supervisor opened setup/setup.log with "xb" before spawning child.
        with (setup_dir / "setup.log").open("xb") as colliding_parent_log:
            proc = subprocess.run(
                [sys.executable, "-B", str(shim), "--worker", "setup", "--spec", str(spec_path),
                 "--output", str(setup_dir), "--scratch", str(scratch_dir), "--inputs", str(inputs_dir)],
                cwd=runtime.ROOT, stdout=colliding_parent_log, stderr=subprocess.STDOUT, timeout=30,
            )
        self.assertNotEqual(proc.returncode, 0)
        log_text = (setup_dir / "setup.log").read_text(encoding="utf8", errors="replace")
        self.assertIn("FileExistsError", log_text)
        self.assertIn("setup.log", log_text)

    def test_launch_composes_real_setup_worker_and_prepare_runtime_with_distinct_logs(self):
        import scripts.internvl3763 as launcher
        from scripts import internvl_v2 as old_v2
        request, grant, comments = campaign_fixture(self.root / "ledger", actual_source=True)
        ledger = campaign.Ledger.create(self.root / "ledger", self.root / "mirror", grant, "synthetic-machine")
        with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])):
            intent = ledger.reserve(request)
        capsule_dir = self.root / "capsule"
        write(capsule_dir / "request.json", request)
        write(capsule_dir / "campaign-intent.json", intent)
        shim = write_setup_harness(self.root)
        worker_shim = self.root / "offline_worker_shim.py"
        worker_shim.write_text(
            f"""import pathlib, sys
sys.path.insert(0, {str(runtime.ROOT)!r})
from safeshift import internvl3763 as rt
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest

args = sys.argv[1:]
req_path = pathlib.Path(args[args.index("--request") + 1])
out = pathlib.Path(args[args.index("--output") + 1])
handoff = read(req_path)
exec_req = handoff["bindings"]["runtime"]["execution_request"]
spec = exec_req["source"]
env_dir = out / "environment"
env_dir.mkdir(exist_ok=False)
write(env_dir / "worker-claim.json", {{"kind": "worker"}})
for name in ("software.json", "hardware.json", "cuda.json", "allocation.json",
             "checkpoint.json", "checkpoint-stream.json", "processor.json", "preload-resources.json"):
    write(env_dir / name, {{"notice": "SYNTHETIC_ENV_RECEIPT"}})
write(env_dir / "preflight.json", {{"status": "LIVE_GPU_PREFLIGHT_PASS", "source_sha256": digest(spec),
    "model_calls": 0, "weights_loaded": False, "owner_slots_consumed": 0}})
p = dict(exec_req["plan"], scheduled_ordinals=[])
rt._execute(out / "run", None, exec_req["cohort"], p,
    lambda _: (_ for _ in ()).throw(AssertionError("NO_LOAD")),
    image_path=lambda _: None, tokenizer_sha="a" * 64)
print("WORKER_STDOUT_OK", flush=True)
""",
            encoding="utf8",
        )

        def setup_cmd(python, stage, spec_path, out, scratch, inputs, req, deadline):
            return [sys.executable, "-B", str(shim), "--worker", stage, "--spec", str(spec_path),
                    "--output", str(out), "--scratch", str(scratch), "--inputs", str(inputs), "--request", str(req)]

        real_read = read

        def intercepted_read(path):
            value = real_read(path)
            if Path(path).name == "runtime.json":
                value = dict(value, python=sys.executable)
            return value

        self.addCleanup(setattr, release, "_active", None)
        release._active = None
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(release, "activate", return_value=grant), \
                patch.object(release, "bind", return_value=request["bindings"]["runtime"]["execution_request"]), \
                patch.object(release, "activation_claim", return_value={"kind": "launch"}), \
                patch.object(runtime, "authorize"), \
                patch.object(launcher, "setup_command", side_effect=setup_cmd), \
                patch("safeshift.pilot.artifacts.read", side_effect=intercepted_read), \
                cross_platform_stage_runner():
            stage_fn = launcher.run_stage

            def redirected_stage(command, **kwargs):
                if "-m" in command and "scripts.internvl3763" in command:
                    idx = command.index("-m")
                    command = [sys.executable, "-B", str(worker_shim), *command[idx + 2:]]
                return stage_fn(command, **kwargs)

            with patch.object(launcher, "run_stage", side_effect=redirected_stage):
                result = launcher.launch(capsule_dir / "request.json",
                    output=self.root / "working", scratch=self.root / "temp", inputs=self.root / "input")

        self.assertEqual(result["status"], "PASS")
        archives = list((self.root / "working").glob("*.zip"))
        self.assertEqual(len(archives), 1)
        with zipfile.ZipFile(archives[0]) as bundle:
            names = set(bundle.namelist())
            self.assertIn("setup/setup-supervisor.log", names)
            self.assertIn("setup/setup.log", names)
            self.assertIn("setup/setup-supervisor.json", names)
            self.assertIn("setup/runtime.json", names)
            self.assertIn("worker.log", names)
            self.assertIn("worker-supervisor.json", names)
            self.assertIn("SETUP_SUPERVISOR_STREAM_HEADER", bundle.read("setup/setup-supervisor.log").decode("utf8"))
            self.assertIn("OFFLINE_SETUP_STEP:pip-bootstrap offline", bundle.read("setup/setup.log").decode("utf8"))
            sup = json.loads(bundle.read("setup/setup-supervisor.json"))
            self.assertEqual(sup["status"], "EXITED")
            self.assertEqual(sup["returncode"], 0)
            self.assertGreaterEqual(
                sup["log_bytes"],
                len(bundle.read("setup/setup-supervisor.log")) + len(bundle.read("setup/setup.log")),
            )

    def test_setup_failure_preserves_partial_logs_receipts_and_exports_fail_bundle_without_retry(self):
        import scripts.internvl3763 as launcher
        from scripts import internvl_v2 as old_v2
        request, grant, comments = campaign_fixture(self.root / "ledger", actual_source=True)
        ledger = campaign.Ledger.create(self.root / "ledger", self.root / "mirror", grant, "synthetic-machine")
        with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])):
            intent = ledger.reserve(request)
        capsule_dir = self.root / "capsule"
        write(capsule_dir / "request.json", request)
        write(capsule_dir / "campaign-intent.json", intent)
        shim = write_setup_harness(self.root, fail_during_setup=True)
        invocations = []

        def setup_cmd(python, stage, spec_path, out, scratch, inputs, req, deadline):
            invocations.append(stage)
            return [sys.executable, "-B", str(shim), "--worker", stage, "--spec", str(spec_path),
                    "--output", str(out), "--scratch", str(scratch), "--inputs", str(inputs), "--request", str(req)]

        self.addCleanup(setattr, release, "_active", None)
        release._active = None
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(release, "activate", return_value=grant), \
                patch.object(release, "bind", return_value=request["bindings"]["runtime"]["execution_request"]), \
                patch.object(release, "activation_claim", return_value=campaign.native_receipt("launch", request, intent, grant)), \
                patch.object(runtime, "authorize"), \
                patch.object(launcher, "setup_command", side_effect=setup_cmd), \
                cross_platform_stage_runner():
            result = launcher.launch(capsule_dir / "request.json",
                output=self.root / "working", scratch=self.root / "temp", inputs=self.root / "input")

        self.assertEqual(invocations, ["setup"])
        self.assertEqual(result["status"], "FAIL")
        archive = next((self.root / "working").glob("*.zip"))
        verified = runtime.verify_bundle(archive, sha(archive), request["plan"])
        self.assertEqual(verified["status"], "FAIL")
        self.assertEqual(verified["model_calls"], 0)
        self.assertEqual(verified["counts"], {"NOT_ATTEMPTED": 3763})
        campaign.verify_native_custody(request, archive, intent, grant)
        with zipfile.ZipFile(archive) as bundle:
            names = set(bundle.namelist())
            self.assertIn("setup/setup-supervisor.log", names)
            self.assertIn("setup/setup.log", names)
            self.assertIn("setup/interpreters.json", names)
            self.assertNotIn("worker-supervisor.json", names)
            self.assertEqual(json.loads(bundle.read("terminal.json"))["status"], "FAIL")
            self.assertEqual(json.loads(bundle.read("setup/setup-supervisor.json"))["status"], "CHILD_FAILURE")

    @unittest.skipUnless(sys.platform == "linux", "real Linux process-group supervision check")
    def test_linux_run_stage_deduplicates_supervisor_log_and_enforces_exact_budget_and_deadline(self):
        import scripts.internvl3763 as launcher
        stage_dir = self.root / "linux_stage"
        stage_dir.mkdir()
        code = (
            "import pathlib, sys; "
            "sys.stdout.write('S' * 120); sys.stdout.flush(); "
            "pathlib.Path(sys.argv[1]).write_bytes(b'C' * int(sys.argv[2]))"
        )
        # 120B supervisor log + 200B child setup.log = 320B <= 360B (double-counting would yield 440B > 360B!).
        res = launcher.run_stage(
            [sys.executable, "-B", "-c", code, str(stage_dir / "setup.log"), "200"],
            cwd=runtime.ROOT, env=dict(os.environ), deadline=time.monotonic() + 15,
            log=stage_dir / "setup-supervisor.log", receipt=stage_dir / "setup-supervisor.json",
            max_log_bytes=360, watch_log_roots=(stage_dir,),
        )
        self.assertEqual(res["status"], "EXITED")
        receipt = read(stage_dir / "setup-supervisor.json")
        self.assertEqual(receipt["log_bytes"], 320)

        # Exceeding combined cap (120B + 260B = 380B > 360B) triggers LOG_BUDGET_EXCEEDED and preserves partials.
        over_dir = self.root / "linux_over"
        over_dir.mkdir()
        slow_code = (
            "import pathlib, sys, time; "
            "sys.stdout.write('S' * 120); sys.stdout.flush(); "
            "pathlib.Path(sys.argv[1]).write_bytes(b'C' * 260); "
            "time.sleep(2)"
        )
        with self.assertRaisesRegex(RuntimeError, "SUPERVISED_LOG_BUDGET_EXCEEDED"):
            launcher.run_stage(
                [sys.executable, "-B", "-c", slow_code, str(over_dir / "setup.log")],
                cwd=runtime.ROOT, env=dict(os.environ), deadline=time.monotonic() + 15,
                log=over_dir / "setup-supervisor.log", receipt=over_dir / "setup-supervisor.json",
                max_log_bytes=360, watch_log_roots=(over_dir,),
            )
        self.assertEqual(read(over_dir / "setup-supervisor.json")["status"], "LOG_BUDGET_EXCEEDED")
        self.assertEqual((over_dir / "setup.log").stat().st_size, 260)

        # Hard deadline kills hanging process group cleanly.
        hang_dir = self.root / "linux_hang"
        hang_dir.mkdir()
        with self.assertRaisesRegex(RuntimeError, "SUPERVISED_HARD_DEADLINE"):
            launcher.run_stage(
                [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                cwd=runtime.ROOT, env=dict(os.environ), deadline=time.monotonic() + 0.25,
                log=hang_dir / "setup-supervisor.log", receipt=hang_dir / "setup-supervisor.json",
                max_log_bytes=4096, watch_log_roots=(hang_dir,),
            )
        self.assertEqual(read(hang_dir / "setup-supervisor.json")["status"], "HARD_DEADLINE")

    def test_worker_inner_hard_deadline_stops_cleanly_before_supervisor_kill(self):
        cohort = synthetic_cohort()
        p = campaign.plan(cohort, [], action="initial", run_id="synthetic-dl", attempt_id="attempt-1",
            max_calls=2, max_seconds=1800)
        helper = controller_fixtures.PreparedControllerTests()
        backend = helper.backend('{"safety_level":"Level02"}', False)
        ticks = iter([100.0, 101.0, 112.0, 113.0, 125.0, 126.0, 127.0])
        def fake_clock():
            return next(ticks, 127.0)
        def img(row):
            path = self.root / f"img-{row['ordinal']}.jpg"
            path.write_bytes(synthetic_bytes(row["ordinal"]))
            return path
        # Even though max_seconds=1800 (begun+1800=1900), hard_deadline=300 stops cleanly at 126.0 (174s < 180s reserve)!
        summary = runtime._execute(self.root / "dl_run", self.root / "dl_run.zip", cohort, p,
            lambda _: backend, image_path=img, tokenizer_sha="a" * 64, clock=fake_clock, hard_deadline=300.0)
        self.assertEqual(summary["status"], "PASS")
        self.assertEqual(summary["model_calls"], 1)
        self.assertEqual(summary["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
        self.assertEqual(read(self.root / "dl_run/stop.json"), {"reason": "DEADLINE_BEFORE_NEXT_CALL"})


@unittest.skipUnless(HAS_KAGGLESDK, "pinned kagglesdk required for real GetKernel serializer checks")
class InstalledSdkGetKernelMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, self.grant, _ = campaign_fixture(
            self.root / "ledger", actual_source=True, kernel_sources=("nguynanhtn/safeshift-prepare-internvl35/1",),
        )
        self.notebook = {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC_NOTEBOOK')\n"]}]}
        self.notebook_bytes = json.dumps(self.notebook).encode("utf8")
        self.request["notebook_sha256"] = hashlib.sha256(self.notebook_bytes).hexdigest()

    def build_sdk_response(self, **overrides):
        from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelResponse
        inputs = self.request["bindings"]["dataset"]
        meta = {
            "id": 142976950,
            "ref": self.request["job"],
            "isPrivate": True,
            "currentVersionNumber": 1,
            "machineShape": "NvidiaTeslaT4",
            "datasetDataSources": [r.rsplit("/", 1)[0] for r in inputs["dataset_sources"]],
            "kernelDataSources": [r.rsplit("/", 1)[0] for r in inputs["kernel_sources"]],
            "competitionDataSources": [],
            "modelDataSources": [],
        }
        blob = {"source": json.dumps(self.notebook)}
        blob_override = overrides.pop("blob_source", None)
        if blob_override is not None:
            blob["source"] = blob_override
        meta.update(overrides)
        return ApiGetKernelResponse.from_dict({"metadata": meta, "blob": blob})

    def test_get_kernel_unversioned_slugs_pass_while_pinned_versions_remain_enforced(self):
        operator = handoff.Train3763Operator()
        response = self.build_sdk_response()
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(operator, "_api", return_value=NS()), \
                patch("scripts.submit_internvl_v2.get_kernel", return_value=response), \
                patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=self.notebook_bytes):
            ident = operator.identity(self.request)
        self.assertEqual(ident, {
            "job_id": self.request["job"],
            "version": 1,
            "kernel_id": 142976950,
            "notebook_sha256": self.request["notebook_sha256"],
        })
        # Local request and input_sources still strictly require /N pinned versions and unique owner/slugs.
        unversioned_req = deepcopy(self.request)
        unversioned_req["bindings"]["dataset"]["dataset_sources"][0] = "nguynanhtn/synthetic-input"
        with self.assertRaisesRegex(ValueError, "VERSIONED_INPUT_REFERENCE_REQUIRED"):
            op.input_sources(unversioned_req)
        dup_slug_req = deepcopy(self.request)
        dup_slug_req["bindings"]["dataset"]["dataset_sources"].append("nguynanhtn/synthetic-input/2")
        with self.assertRaisesRegex(ValueError, "BOUNDED_UNIQUE_INPUT_SOURCES"):
            op.input_sources(dup_slug_req)
        dup_kernel_req = deepcopy(self.request)
        dup_kernel_req["bindings"]["dataset"]["kernel_sources"].append("nguynanhtn/safeshift-prepare-internvl35/2")
        with self.assertRaisesRegex(ValueError, "BOUNDED_UNIQUE_INPUT_SOURCES"):
            op.input_sources(dup_kernel_req)

    def test_get_kernel_negative_matrix_fails_closed(self):
        operator = handoff.Train3763Operator()
        inputs = self.request["bindings"]["dataset"]
        ds_slugs = [r.rsplit("/", 1)[0] for r in inputs["dataset_sources"]]
        kn_slugs = [r.rsplit("/", 1)[0] for r in inputs["kernel_sources"]]
        cases = [
            ("wrong_dataset_slug", {"datasetDataSources": ["nguynanhtn/wrong-dataset", *ds_slugs[1:]]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("missing_dataset_slug", {"datasetDataSources": ds_slugs[:-1]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("extra_dataset_slug", {"datasetDataSources": [*ds_slugs, "nguynanhtn/extra-dataset"]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("duplicate_dataset_slug", {"datasetDataSources": [*ds_slugs, ds_slugs[0]]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("versioned_in_getkernel", {"datasetDataSources": list(inputs["dataset_sources"])}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("missing_kernel_slug", {"kernelDataSources": []}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("extra_kernel_slug", {"kernelDataSources": [*kn_slugs, "nguynanhtn/extra-kernel"]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("extra_competition", {"competitionDataSources": ["unexpected-comp"]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("extra_model", {"modelDataSources": ["owner/model"]}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("wrong_accelerator", {"machineShape": "NvidiaTeslaP100"}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("empty_accelerator", {"machineShape": ""}, "REMOTE_ACCELERATOR_OR_INPUT_DRIFT"),
            ("public_kernel", {"isPrivate": False}, "KAGGLE_JOB_PRIVACY_IDENTITY"),
            ("wrong_job_ref", {"ref": "nguynanhtn/other-job"}, "KAGGLE_JOB_PRIVACY_IDENTITY"),
            ("wrong_version_2", {"currentVersionNumber": 2}, "REMOTE_VERSION_SOURCE_DRIFT"),
            ("wrong_code_blob", {"blob_source": json.dumps({"cells": [{"cell_type": "code", "source": ["print('TAMPERED')"]}]})}, "KAGGLE_SOURCE_DRIFT"),
        ]
        for label, mutation, expected_err in cases:
            with self.subTest(case=label):
                resp = self.build_sdk_response(**mutation)
                with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                        patch.object(operator, "_api", return_value=NS()), \
                        patch("scripts.submit_internvl_v2.get_kernel", return_value=resp), \
                        patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=self.notebook_bytes), \
                        self.assertRaisesRegex(ValueError, expected_err):
                    operator.identity(self.request)

        # Boolean version guard (isinstance(True, int) is True in Python, type(True) is int is False).
        bool_resp = self.build_sdk_response()
        bool_resp.metadata._current_version_number = True
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(operator, "_api", return_value=NS()), \
                patch("scripts.submit_internvl_v2.get_kernel", return_value=bool_resp), \
                patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=self.notebook_bytes), \
                self.assertRaisesRegex(ValueError, "REMOTE_VERSION_SOURCE_DRIFT"):
            operator.identity(self.request)

    def test_historical_attempt3_identity_verifies_against_historical_commit_after_head_advance(self):
        operator = handoff.Train3763Operator()
        old_commit = "9f86424d14507fcc2fa08c2bf4a2f9a56e7dd481"
        self.request["commit_sha"] = old_commit
        resp = self.build_sdk_response()

        def git_show(argv, **kwargs):
            self.assertEqual(argv, ["git", "show", old_commit + ":" + self.request["notebook"]])
            return self.notebook_bytes

        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(operator, "_api", return_value=NS()), \
                patch("scripts.submit_internvl_v2.get_kernel", return_value=resp), \
                patch("safeshift.kaggle_handoff.subprocess.check_output", side_effect=git_show):
            ident = operator.identity(self.request)
        self.assertEqual(ident["version"], 1)
        self.assertEqual(ident["notebook_sha256"], self.request["notebook_sha256"])


class Attempt3TerminalFailCollectionAndPlanningTests(unittest.TestCase):
    def setUp(self):
        parent = runtime.ROOT / "data/processed"
        parent.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic-attempt3-", dir=parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request1, self.grant, self.comments = campaign_fixture(self.root / "ledger", actual_source=True)
        self.grant["caps"]["total_jobs"] = 10
        self.grant["caps"]["total_calls"] = 3763
        self.grant["caps"]["total_gpu_seconds"] = 360000
        self.comments[f"/issues/comments/{self.request1['execution_release']['comment_id']}"]["body"] = (
            campaign.MARKER + "\n```json\n" + json.dumps(self.grant) + "\n```"
        )
        self.request1["execution_release"]["body_sha256"] = hashlib.sha256(
            self.comments[f"/issues/comments/{self.request1['execution_release']['comment_id']}"]["body"].encode()
        ).hexdigest()
        # Re-sign technical & audit comments for updated grant digest.
        tech_id = self.request1["bindings"]["runtime"]["technical_revision"]["comment_id"]
        tech_body_obj = json.loads(self.comments[f"/issues/comments/{tech_id}"]["body"].split("```json\n")[1].split("\n```")[0])
        audit_id = tech_body_obj["audit"]["comment_id"]
        audit_obj = json.loads(self.comments[f"/issues/comments/{audit_id}"]["body"].split("```json\n")[1].split("\n```")[0])
        audit_obj["campaign_sha256"] = digest(self.grant)
        audit_body = "SAFESHIFT_TRAIN3763_AUDIT_V1\n```json\n" + json.dumps(audit_obj) + "\n```"
        self.comments[f"/issues/comments/{audit_id}"]["body"] = audit_body
        tech_body_obj["campaign_sha256"] = digest(self.grant)
        tech_body_obj["audit"]["body_sha256"] = hashlib.sha256(audit_body.encode()).hexdigest()
        tech_body = "SAFESHIFT_TRAIN3763_TECHNICAL_V1\n```json\n" + json.dumps(tech_body_obj) + "\n```"
        self.comments[f"/issues/comments/{tech_id}"]["body"] = tech_body
        self.request1["bindings"]["runtime"]["technical_revision"]["body_sha256"] = hashlib.sha256(tech_body.encode()).hexdigest()

        with patch.object(release, "get", side_effect=lambda p: deepcopy(self.comments[p])):
            self.ledger = campaign.Ledger.create(self.root / "ledger", self.root / "mirror", self.grant, "synthetic-machine")
            # Attempts 1 & 2: pre-submit aborts consuming reservations with no refund.
            for num in (1, 2):
                req_n = self._make_attempt_request(num, [])
                intent_n = self.ledger.reserve(req_n)
                with patch.object(op, "pre_submit_inventory", return_value={
                    "job": req_n["job"], "intent_sha256": digest(intent_n), "job_absent": True, "inventory": {}
                }):
                    self.ledger.abort_pre_submit()
            # Attempt 3: reserved, pushed, submitted, and blocked post-submit by GetKernel slug drift.
            self.request3 = self._make_attempt_request(3, [])
            self.intent3 = self.ledger.reserve(self.request3)
        with handoff.lock(self.ledger.root):
            self.ledger.append("PUSH_INTENT", intent_sha256=digest(self.intent3), inventory_sha256="b" * 64)
            self.ledger.append("SUBMITTED", intent_sha256=digest(self.intent3),
                result={"job_id": self.request3["job"], "version": 1})
        self.session3 = handoff.prepare(self.root / "attempt-3", self.request3)
        self.session3.event("AGY_INVOCATION_INTENT", phase="start", turn=1)
        self.session3.event("SUBMISSION_INTENT")
        self.session3.event("SUBMITTED", job_id=self.request3["job"], version=1)
        self.session3.report("BLOCKED", reason="ValueError", reason_code="REMOTE_ACCELERATOR_OR_INPUT_DRIFT",
            automatic_retry=False, job_cancelled=False)
        self.session3.event("AGY_RETURNED", cli_status="SUCCESS",
            conversation_id="cb8d4344-29c4-47d1-a255-01573fe975a8", returncode=0, stdout_sha256="c" * 64, turn=1)
        self.archive3 = self._build_attempt3_fail_archive(self.root / "remote_bundle")

    def _make_attempt_request(self, number, history, *, calls=1):
        req = deepcopy(self.request1)
        capsule = f"nguynanhtn/synthetic-capsule-attempt{number}/1"
        old_capsule = req["bindings"]["runtime"]["execution_input"]["ref"]
        req["bindings"]["runtime"]["execution_input"]["ref"] = capsule
        ds = req["bindings"]["dataset"]["dataset_sources"]
        ds[ds.index(old_capsule)] = capsule
        req["bindings"]["runtime"]["campaign_ledger"] = self.ledger.root.resolve().relative_to(runtime.ROOT.resolve()).as_posix()
        exec_req = req["bindings"]["runtime"]["execution_request"]
        p = campaign.plan(exec_req["cohort"], history, action="resume" if history else "initial",
            run_id=f"{self.grant['campaign_id']}-{number}", attempt_id=f"attempt-{number}",
            max_calls=calls, max_seconds=1800)
        exec_req.update(plan=p, history=history,
            history_archives=[{"archive": f"custody/{h['evidence_sha256']}.zip", "sha256": h["evidence_sha256"],
                "plan": {"run_id": h["run_id"], "attempt_id": h["attempt_id"]}} for h in history])
        req["bindings"]["dataset"]["execution_request_sha256"] = digest(exec_req)
        req.update(handoff_id=f"{self.grant['campaign_id']}-{number}",
            job=f"nguynanhtn/safeshift-train3763-{self.grant['campaign_id']}-{number}",
            plan=p, plan_sha256=digest(p),
            limits={"monitor_seconds": 900, "job_seconds": 1800, "max_calls": calls})
        return req

    def _build_attempt3_fail_archive(self, folder):
        out = folder / "ivl35-train3763-3-synthetic"
        out.mkdir(parents=True, exist_ok=True)
        exec_req = self.request3["bindings"]["runtime"]["execution_request"]
        write(out / "execution-request.json", exec_req)
        write(out / "handoff.json", self.request3)
        write(out / "release.json", self.grant)
        write(out / "campaign-intent.json", self.intent3)
        write(out / "launch-claim.json", campaign.native_receipt("launch", self.request3, self.intent3, self.grant))
        setup = out / "setup"
        setup.mkdir()
        write(setup / "source.json", runtime.capture.source_spec())
        write(setup / "interpreters.json", [])
        write(setup / "python_provider.json", {"provider": "SYNTHETIC_PBS"})
        (setup / "setup.log").write_text("FileExistsError: setup.log\n", encoding="utf8")
        write(setup / "setup-supervisor.json", {
            "schema": "fresh-process-supervision-v1", "status": "CHILD_FAILURE", "returncode": 1,
            "seconds": 4.31, "log_bytes": 28, "group_kill_sent": True, "automatic_retry": False,
            "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED",
        })
        err = {"type": "RuntimeError", "consumption": "RECONCILE_MARKERS_NO_RETRY"}
        runtime.interrupted_summary(out, exec_req, err)
        write(out / "terminal.json", {"status": "FAIL", "error": err})
        archive = Path(str(out) + ".zip")
        export(out, archive)
        return archive

    def _mock_operator_for_archive(self, archive_path, *, include_log=True):
        operator = handoff.Train3763Operator()
        notebook = read(runtime.ROOT / self.request3["notebook"])
        notebook_bytes = (runtime.ROOT / self.request3["notebook"]).read_bytes()
        inputs = self.request3["bindings"]["dataset"]
        remote_kernel = NS(
            metadata=NS(
                id=142976950, ref=self.request3["job"], is_private=True, current_version_number=1,
                machine_shape="NvidiaTeslaT4",
                dataset_data_sources=[r.rsplit("/", 1)[0] for r in inputs["dataset_sources"]],
                kernel_data_sources=[r.rsplit("/", 1)[0] for r in inputs["kernel_sources"]],
                competition_data_sources=[], model_data_sources=[],
            ),
            blob=NS(source=json.dumps(notebook)),
        )
        fake_api = NS(
            kernels_status=lambda ref: NS(status="COMPLETE"),
            kernels_output=lambda ref, dest, **kw: self._copy_outputs(archive_path, Path(dest), include_log=include_log),
        )
        return operator, fake_api, remote_kernel, notebook_bytes

    @staticmethod
    def _copy_outputs(archive_path, dest, *, include_log=True):
        shutil.copy2(archive_path, dest / archive_path.name)
        sidecar = Path(str(archive_path) + ".sha256.json")
        if sidecar.exists():
            shutil.copy2(sidecar, dest / sidecar.name)
        if include_log:
            (dest / "safeshift-train3763-3.log").write_text('{"status": "FAIL"}\n', encoding="utf8")

    def test_attempt3_complete_worker_fail_collects_cleanly_after_post_submit_block_preserving_budget(self):
        # abort_pre_submit is strictly forbidden once PUSH_INTENT exists.
        with self.assertRaisesRegex(ValueError, "POSSIBLE_SUBMIT_READ_ONLY_RECONCILIATION_ONLY"):
            self.ledger.abort_pre_submit()
        # Duplicate start is forbidden.
        self.assertEqual(handoff.operate(handoff.Session(self.session3.root), handoff.Train3763Operator(), "start")["status"], "BLOCKED")

        operator, fake_api, remote_kernel, notebook_bytes = self._mock_operator_for_archive(self.archive3)
        with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                patch.object(operator, "_api", return_value=fake_api), \
                patch("scripts.submit_internvl_v2.get_kernel", return_value=remote_kernel), \
                patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=notebook_bytes):
            collected_report = handoff.operate(handoff.Session(self.session3.root), operator, "collect")
            # Idempotent recollection of already-collected attempt does not duplicate COLLECTED.
            recollected = op.verify_remote_custody(self.request3, self.archive3, provider={"state": "COMPLETE", **operator.identity(self.request3)})

        self.assertEqual(collected_report["status"], "FAIL")
        self.assertEqual(collected_report["terminal"], "COMPLETE")
        self.assertEqual(collected_report["collection"], "FINISHED")
        self.assertEqual(collected_report["verification"]["status"], "FAIL")
        self.assertEqual(collected_report["verification"]["model_calls"], 0)
        self.assertEqual(collected_report["verification"]["counts"], {"NOT_ATTEMPTED": 3763})
        self.assertEqual(handoff.accept_report(handoff.Session(self.session3.root))["status"], "FAIL")
        self.assertEqual(recollected["status"], "RECONCILED")

        collected_events = [e for e in self.ledger.events() if e["kind"] == "COLLECTED"]
        self.assertEqual(len(collected_events), 1)
        self.assertEqual(collected_events[0]["verification"]["status"], "FAIL")
        summary = self.ledger.summary()
        self.assertFalse(summary["blocked_open_intent"])
        self.assertEqual(summary["jobs"], 3)
        self.assertEqual(summary["reserved_calls"], 3)
        self.assertEqual(summary["reserved_gpu_seconds"], 10800)
        self.assertEqual(summary["counts"], {"NOT_ATTEMPTED": 3763})

        # Next planning rules after a 0-call collected initial FAIL:
        histories, _ = self.ledger.histories()
        self.assertEqual(len(histories), 1)
        self.assertEqual(histories[0]["records"], [])
        cohort = self.request3["bindings"]["runtime"]["execution_request"]["cohort"]
        with self.assertRaisesRegex(ValueError, "NEW_SERIES_REQUIRED"):
            campaign.plan(cohort, histories, action="initial", run_id="r4", attempt_id="attempt-4", max_calls=1, max_seconds=1800)
        with self.assertRaisesRegex(ValueError, "EXPLICIT_REPAIR_CASE_REQUIRED|EXACT_REPAIR_TARGETS_REQUIRED"):
            campaign.plan(cohort, histories, action="repair", run_id="r4", attempt_id="attempt-4", max_calls=1, max_seconds=1800,
                repair={"targets": {}, "fix_sha256": "a" * 64, "regression_sha256": "b" * 64, "diagnosis": "none"})
        # Resume with calls=1 schedules ordinal 0; shards (calls > 1) stay blocked before MEASURED!
        req4_shard = self._make_attempt_request(4, histories, calls=2)
        with patch.object(release, "get", side_effect=lambda p: deepcopy(self.comments[p])), \
                self.assertRaisesRegex(ValueError, "FINAL_SOURCE_MEASUREMENTS_REQUIRED_BEFORE_SHARDS"):
            self.ledger.reserve(req4_shard)
        req4 = self._make_attempt_request(4, histories, calls=1)
        self.assertEqual(req4["plan"]["scheduled_ordinals"], [0])
        with patch.object(release, "get", side_effect=lambda p: deepcopy(self.comments[p])):
            intent4 = self.ledger.reserve(req4)
        self.assertEqual(intent4["reserved_calls"], 1)

    def test_damaged_modified_or_foreign_fail_bundle_blocks_and_leaves_ledger_unchanged(self):
        before_events = self.ledger.events()
        variants = ("corrupt_zip", "wrong_sidecar", "missing_log", "terminal_pass_lie", "missing_launch_claim", "foreign_intent")
        for index, variant in enumerate(variants):
            with self.subTest(variant=variant):
                work = self.root / f"bad-{index}"
                bad_archive = self._build_attempt3_fail_archive(work)
                include_log = True
                if variant == "corrupt_zip":
                    Path(str(bad_archive) + ".sha256.json").unlink()
                    raw = bytearray(bad_archive.read_bytes())
                    raw[len(raw) // 2] ^= 0x55
                    bad_archive.write_bytes(bytes(raw))
                    write(Path(str(bad_archive) + ".sha256.json"), {"sha256": sha(bad_archive)})
                elif variant == "wrong_sidecar":
                    Path(str(bad_archive) + ".sha256.json").unlink()
                    write(Path(str(bad_archive) + ".sha256.json"), {"sha256": "0" * 64})
                elif variant == "missing_log":
                    include_log = False
                elif variant in ("terminal_pass_lie", "missing_launch_claim", "foreign_intent"):
                    src_dir = work / "ivl35-train3763-3-synthetic"
                    bad_archive.unlink()
                    Path(str(bad_archive) + ".sha256.json").unlink()
                    (src_dir / "checksums.json").unlink()
                    if variant == "terminal_pass_lie":
                        (src_dir / "terminal.json").write_text(json.dumps({"status": "PASS", "error": None}), encoding="utf8")
                    elif variant == "missing_launch_claim":
                        (src_dir / "launch-claim.json").unlink()
                    elif variant == "foreign_intent":
                        tampered = dict(self.intent3, reserved_calls=99)
                        (src_dir / "campaign-intent.json").write_text(json.dumps(tampered), encoding="utf8")
                    export(src_dir, bad_archive)

                operator, fake_api, remote_kernel, notebook_bytes = self._mock_operator_for_archive(
                    bad_archive, include_log=include_log)
                with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                        patch.object(operator, "_api", return_value=fake_api), \
                        patch("scripts.submit_internvl_v2.get_kernel", return_value=remote_kernel), \
                        patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=notebook_bytes):
                    report = handoff.operate(handoff.Session(self.session3.root), operator, "collect")
                self.assertEqual(report["status"], "BLOCKED")
                self.assertEqual(self.ledger.events(), before_events)
                self.assertIsNotNone(self.ledger.open_intent())


@unittest.skipUnless(HAS_KAGGLESDK and HAS_TORCH, "pinned kagglesdk + CPU torch/tokenizers required for full native-grammar E2E")
class EndToEndOfflineCampaignPipelineTests(unittest.TestCase):
    def test_stage_submit_launch_native_grammar_capture_collect_measure_and_resume_shard_end_to_end(self):
        import torch
        from PIL import Image
        import requests
        from tokenizers import Tokenizer
        from tokenizers.models import WordLevel
        from kagglesdk import KaggleClient
        from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelResponse
        import scripts.internvl3763 as launcher
        from scripts import internvl_v2 as old_v2
        from scripts.train3763_campaign import stage
        from safeshift import verification173

        parent = runtime.ROOT / "data/processed"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="synthetic-e2e-", dir=parent) as tmp:
            root = Path(tmp)
            req_fixture, grant, comments = campaign_fixture(
                root / "ledger", actual_source=True, kernel_sources=("nguynanhtn/safeshift-prepare-internvl35/1",),
            )
            grant["caps"]["total_jobs"] = 8
            grant["caps"]["total_calls"] = 16
            grant["caps"]["total_gpu_seconds"] = 72000

            # Prepare synthetic original-mount layout for ordinal 0 (no TEST directory exists).
            inputs_mount = root / "kaggle_input"
            master_file = inputs_mount / "safeshift-pilot-input/master_manifest.json"
            write(master_file, {"notice": "SYNTHETIC_MASTER"})
            image_root = inputs_mount / "inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH"
            img0 = image_root / "train/Annotations/synthetic-000000.jpg"
            img0.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGB", (8, 8), (12, 34, 56)).save(img0, format="JPEG")
            cohort_img = deepcopy(req_fixture["bindings"]["runtime"]["execution_request"]["cohort"])
            cohort_img["samples"][0]["image_sha256"] = sha(img0)
            grant["cohort_sha256"] = digest(cohort_img)

            notebook_path = runtime.ROOT / "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb"
            notebook_json = read(notebook_path)
            notebook_raw = notebook_path.read_bytes()

            grant_cid = req_fixture["execution_release"]["comment_id"]
            grant_body = campaign.MARKER + "\n```json\n" + json.dumps(grant) + "\n```"
            comments[f"/issues/comments/{grant_cid}"]["body"] = grant_body
            req_fixture["execution_release"]["body_sha256"] = hashlib.sha256(grant_body.encode()).hexdigest()
            tech_cid = req_fixture["bindings"]["runtime"]["technical_revision"]["comment_id"]
            tech_obj = json.loads(comments[f"/issues/comments/{tech_cid}"]["body"].split("```json\n")[1].split("\n```")[0])
            audit_cid = tech_obj["audit"]["comment_id"]
            audit_obj = json.loads(comments[f"/issues/comments/{audit_cid}"]["body"].split("```json\n")[1].split("\n```")[0])
            audit_obj["campaign_sha256"] = digest(grant)
            audit_body = "SAFESHIFT_TRAIN3763_AUDIT_V1\n```json\n" + json.dumps(audit_obj) + "\n```"
            comments[f"/issues/comments/{audit_cid}"]["body"] = audit_body
            tech_obj["campaign_sha256"] = digest(grant)
            tech_obj["notebook_sha256"] = sha(notebook_path)
            tech_obj["notebook_code_sha256"] = op.code_hash(notebook_json)
            tech_obj["runtime_commit"] = notebook_json["metadata"]["safeshift"]["runtime_commit"]
            tech_obj["audit"]["body_sha256"] = hashlib.sha256(audit_body.encode()).hexdigest()
            tech_body = "SAFESHIFT_TRAIN3763_TECHNICAL_V1\n```json\n" + json.dumps(tech_obj) + "\n```"
            comments[f"/issues/comments/{tech_cid}"]["body"] = tech_body
            req_fixture["bindings"]["runtime"]["technical_revision"]["body_sha256"] = hashlib.sha256(tech_body.encode()).hexdigest()

            with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(op, "api", return_value=Mock()), \
                    patch.object(op, "verify_python_input", return_value={"scope": "SYNTHETIC_PYTHON_PROOF"}):
                ledger = campaign.Ledger.create(root / "ledger", root / "mirror", grant, "synthetic-machine")
                staged1 = stage(
                    ledger, req_fixture["execution_release"],
                    {"python_input": py.binding(), "technical_revision": req_fixture["bindings"]["runtime"]["technical_revision"],
                     "execution_input": {"kind": "dataset_sources", "ref": "nguynanhtn/synthetic-capsule-1/1"}},
                    cohort_img, directory=root / "attempt-1", calls=1, seconds=1800, action="initial",
                )
            self.assertEqual(staged1["status"], "STAGED_NOT_SUBMITTED")
            capsule_bytes = (root / "attempt-1/package/safeshift_train3763_execution.json").read_bytes()
            staged_pkg = json.loads(capsule_bytes)
            req1 = staged_pkg["request"]

            # Offline HTTPAdapter exercising REAL KaggleClient + bounded_http + capsule_http 302:443 + GetKernel v1/unversioned slugs.
            pushed_folders = []
            http_calls = []
            signed_url = (
                "https://storage.googleapis.com:443/kaggle-data-sets/synthetic/capsule1"
                "?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Signature=OPAQUE_SIG"
            )

            def fake_adapter_send(adapter_self, prepared, **kwargs):
                self.assertEqual(kwargs["timeout"], (10, 30))
                http_calls.append((prepared.method, prepared.url))
                resp = requests.Response()
                resp.request, resp.url = prepared, prepared.url
                resp.status_code = 200
                resp.headers["Content-Type"] = "application/json"
                if prepared.url.endswith("/GetDatasetMetadata"):
                    body = json.dumps({
                        "info": {"isPrivate": True, "ownerUser": "nguynanhtn", "datasetSlug": "synthetic-capsule-1"}
                    }).encode("utf8")
                elif prepared.url.endswith("/DownloadDataset"):
                    fields = json.loads(prepared.body)
                    self.assertEqual(fields, {
                        "ownerSlug": "nguynanhtn", "datasetSlug": "synthetic-capsule-1",
                        "datasetVersionNumber": 1, "fileName": "safeshift_train3763_execution.json",
                    })
                    resp.status_code = 302
                    resp.headers["Location"] = signed_url
                    body = b""
                elif urlsplit(prepared.url).netloc == "storage.googleapis.com:443":
                    self.assertEqual(prepared.method, "GET")
                    self.assertIsNone(prepared.body)
                    self.assertEqual(dict(prepared.headers), {"Accept-Encoding": "identity"})
                    body = capsule_bytes
                elif prepared.url.endswith("/GetKernel"):
                    fields = json.loads(prepared.body)
                    if fields.get("kernelSlug") == "safeshift-prepare-internvl35":
                        self.assertEqual(fields.get("versionLabel"), "v1")
                        body = json.dumps({
                            "metadata": {"id": 99, "ref": "nguynanhtn/safeshift-prepare-internvl35",
                                         "isPrivate": True, "currentVersionNumber": 1},
                            "blob": {"source": "{}"},
                        }).encode("utf8")
                    elif fields.get("kernelSlug") == req1["job"].split("/")[1]:
                        body = json.dumps({
                            "metadata": {
                                "id": 143000001, "ref": req1["job"], "isPrivate": True, "currentVersionNumber": 1,
                                "machineShape": "NvidiaTeslaT4",
                                "datasetDataSources": [r.rsplit("/", 1)[0] for r in req1["bindings"]["dataset"]["dataset_sources"]],
                                "kernelDataSources": [r.rsplit("/", 1)[0] for r in req1["bindings"]["dataset"]["kernel_sources"]],
                                "competitionDataSources": [], "modelDataSources": [],
                            },
                            "blob": {"source": json.dumps(notebook_json)},
                        }).encode("utf8")
                    else:
                        raise AssertionError("UNEXPECTED_GET_KERNEL:" + str(fields))
                else:
                    raise AssertionError("UNEXPECTED_HTTP_URL:" + str(prepared.url))
                resp.raw = io.BytesIO(body)
                resp.headers["Content-Length"] = str(len(body))
                return resp

            kernel_state = {"status": "RUNNING", "archive": None}
            owned_refs = []
            quota = NS(time_used=timedelta(0), time_reserved=timedelta(0), total_time_allowed=timedelta(seconds=72000))

            def push_kernel(folder, timeout=None, acc=None):
                pushed_folders.append((Path(folder), timeout, acc))
                owned_refs.append(req1["job"])
                return ApiSaveKernelResponse.from_dict({"ref": "/code/" + req1["job"], "versionNumber": 1})

            def status_rpc(ref):
                if ref.startswith("nguynanhtn/safeshift-prepare-internvl35"):
                    return NS(status="COMPLETE")
                return NS(status=kernel_state["status"])

            def output_rpc(ref, dest, **kwargs):
                dest = Path(dest)
                arc = kernel_state["archive"]
                shutil.copy2(arc, dest / arc.name)
                shutil.copy2(str(arc) + ".sha256.json", dest / (arc.name + ".sha256.json"))
                (dest / "provider.log").write_text('{"status": "PASS"}\n', encoding="utf8")

            fake_kaggle_api = NS(
                kernels_list_with_response=lambda **_: NS(kernels=[NS(ref=r) for r in owned_refs], next_page_token=None),
                dataset_list_files=lambda ref, **_: NS(error_message="", next_page_token="",
                    files=[NS(name="safeshift_train3763_execution.json", total_bytes=len(capsule_bytes))]),
                quota_view=lambda: NS(gpu_quota=quota),
                kernels_status=status_rpc,
                kernels_push=push_kernel,
                kernels_output=output_rpc,
                build_kaggle_client=lambda: KaggleClient(api_token="SYNTHETIC_TOKEN"),
            )

            operator = handoff.Train3763Operator()
            head_sha = req1["commit_sha"]
            real_check_output = subprocess.check_output

            def git_check_output(cmd, **kw):
                if "status" in cmd:
                    return "" if kw.get("text") else b""
                if "rev-parse" in cmd:
                    return (head_sha + "\n") if kw.get("text") else (head_sha + "\n").encode("utf8")
                if "show" in cmd and cmd[-1].endswith(".ipynb"):
                    return notebook_raw.decode("utf8") if kw.get("text") else notebook_raw
                return real_check_output(cmd, **kw)

            with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                    patch.object(requests.adapters.HTTPAdapter, "send", fake_adapter_send), \
                    patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(op, "api", return_value=fake_kaggle_api), \
                    patch.object(op, "verify_python_input", return_value={"scope": "SYNTHETIC_PYTHON_PROOF"}), \
                    patch.object(operator, "_api", return_value=fake_kaggle_api), \
                    patch.object(op, "check_sdk", return_value=op.SDK_PINS), \
                    patch("scripts.submit_internvl_v2.check_sdk", return_value=op.SDK_PINS), \
                    patch("subprocess.check_output", side_effect=git_check_output):
                start_report = handoff.operate(handoff.Session(root / "attempt-1"), operator, "start",
                    clock=iter([0.0, 850.0]).__next__, sleep=lambda _: None)
            self.assertEqual(start_report["status"], "RUNNING_UNVERIFIED", msg=str(start_report))
            self.assertEqual(len(pushed_folders), 1)

            # Now simulate the Kaggle VM executing real launch() -> setup -> worker -> grammar V2 capture + strict parser!
            vm_capsule = root / "vm_capsule"
            vm_capsule.mkdir()
            write(vm_capsule / "request.json", req1)
            write(vm_capsule / "campaign-intent.json", staged_pkg["campaign_intent"])
            shim = write_setup_harness(root)

            # Build real PreTrainedModel + GenerationMixin scripted backend under REAL runtime.NativeBackend!
            from test_internvl_v2_runtime import NativeCaptureTests as V2Helper
            V2Helper.setUpClass()
            v2_helper = V2Helper("test_all_labels_actual_generate_full_raw_before_processor_and_parse")
            tok_dir = root / "synthetic_checkpoint_source"
            tok_dir.mkdir()
            (tok_dir / "tokenizer.json").write_text('{"notice": "SYNTHETIC_TOKENIZER"}', encoding="utf8")

            def fake_candidate_backend(key, source, weights, prompt, *, device, weight_verifier):
                weight_verifier(weights, key)
                b = v2_helper.backend(label=1)
                b.prompt = prompt
                b.processor = NS()
                b.config = NS(text_config=NS(vocab_size=b.logit_width))
                b.device = "cpu"
                b.dtype = torch.float32
                b.environment = {
                    "model": {"id": runtime.configuration()["model"], "revision": runtime.configuration()["revision"]},
                    "prompt_sha256": PROMPT_SHA,
                }
                return b

            from safeshift import internvl_v2_memory as mem_lib
            real_snapshot = mem_lib.snapshot
            real_mem_snap = controller_fixtures.make_real_memory_snapshot(root / "vm_mem")
            vm_proc = root / "vm_mem/proc"
            vm_cg = root / "vm_mem/cgroup"
            res_payload = {
                "memory": real_mem_snap["gate_memory"],
                "devices": [66, 1794],
                "free_bytes": [20 * 2**30, 20 * 2**30],
                "requested_reserves_bytes": [24 * 2**30, 2**30],
                "model_fit": "NOT_ESTABLISHED",
            }

            def fake_preflight(spec, env_out, scratch, inputs, deadline):
                for name in ("software.json", "hardware.json", "cuda.json", "allocation.json",
                             "checkpoint.json", "checkpoint-stream.json", "processor.json"):
                    write(env_out / name, {"notice": "SYNTHETIC_PREFLIGHT"})
                write(env_out / "preload-resources.json", res_payload)
                write(env_out / "preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS",
                    "source_sha256": digest(spec), "model_calls": 0, "weights_loaded": False, "owner_slots_consumed": 0})
                return tok_dir, root / "weights"

            mapping = [{**row, "image_locator": f"DATA_PATH/train/Annotations/synthetic-{row['ordinal']:06d}.jpg"}
                       for row in cohort_img["samples"]]
            train_receipt = {"status": "TRAIN_BYTES_PASS", "verified_images": 3763, "labels_exported": False}

            def setup_cmd(python, stage_name, spec_path, out, scratch, inputs, req, deadline):
                return [sys.executable, "-B", str(shim), "--worker", stage_name, "--spec", str(spec_path),
                        "--output", str(out), "--scratch", str(scratch), "--inputs", str(inputs), "--request", str(req)]

            stage_errors = []

            def in_process_stage(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_roots=()):
                try:
                    log, receipt = Path(log), Path(receipt)
                    if "offline_setup_harness.py" in " ".join(command):
                        with log.open("xb") as stream:
                            proc = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=30)
                        assert proc.returncode == 0, log.read_text(encoding="utf8", errors="replace")
                        sz = log.stat().st_size + (Path(watch_log_roots[0]) / "setup.log").stat().st_size
                        write(receipt, {"schema": "fresh-process-supervision-v1", "status": "EXITED",
                            "returncode": 0, "seconds": 1.5, "log_bytes": sz, "group_kill_sent": True,
                            "automatic_retry": False, "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
                        return {"status": "EXITED", "returncode": 0}
                    # Worker stage in-process with patched preflight/backend/telemetry so zero GPU/weights are touched.
                    with log.open("xb") as stream:
                        stream.write(b"WORKER_IN_PROCESS\n")
                    out_dir = Path(command[command.index("--output") + 1])
                    req_path = Path(command[command.index("--request") + 1])
                    release._active = None
                    with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                            patch.object(runtime, "preflight", side_effect=fake_preflight), \
                            patch.object(campaign, "sha", side_effect=lambda p: MASTER_SHA if Path(p) == master_file else sha(p)), \
                            patch.object(verification173, "verify_train", return_value=(train_receipt, cohort_img, mapping)), \
                            patch("safeshift.candidates.backend.CandidateBackend", side_effect=fake_candidate_backend), \
                            patch("safeshift.internvl_v2_memory.verify_checkpoint", return_value={"status": "STREAM_VERIFIED"}), \
                            patch("safeshift.internvl_v2_memory.resource_check", return_value=res_payload), \
                            patch("safeshift.internvl_v2_memory.snapshot", side_effect=lambda *_: real_snapshot(vm_proc, vm_cg)), \
                            patch("safeshift.candidates.inputs.prepare_inputs", return_value=(
                                "SYNTHETIC_RENDERED",
                                {"input_ids": torch.tensor([[8]]), "attention_mask": torch.ones((1, 1), dtype=torch.long)},
                            )), \
                            patch("safeshift.candidates.inputs.validate_inputs", return_value={"patches": 1}), \
                            patch("safeshift.candidates.backend.transfer_inputs", side_effect=lambda x, *_: x), \
                            patch("torch.cuda.max_memory_allocated", return_value=4096), \
                            patch("torch.cuda.max_memory_reserved", return_value=8192):
                        w_res = runtime.worker(req_path, output=out_dir, scratch=root / "vm_temp", inputs=inputs_mount,
                            deadline=time.monotonic() + 600)
                        self.assertEqual(w_res["status"], "PASS", msg=str(w_res))
                    # Ensure positive nonzero clock floors in telemetry.json on fast CPUs for Ledger.measure().
                    tel_path = out_dir / "run/telemetry.json"
                    tel = read(tel_path)
                    tel["load_seconds"] = max(0.1, tel["load_seconds"])
                    tel["samples"][0]["seconds"] = max(0.05, tel["samples"][0]["seconds"])
                    tel_path.write_text(json.dumps(tel), encoding="utf8")
                    # Re-seal summary unaffected (telemetry.json is verified by archive checksums at export()).
                    write(receipt, {"schema": "fresh-process-supervision-v1", "status": "EXITED",
                        "returncode": 0, "seconds": 3.0, "log_bytes": log.stat().st_size, "group_kill_sent": True,
                        "automatic_retry": False, "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
                    return {"status": "EXITED", "returncode": 0}
                except BaseException as exc:
                    import traceback
                    stage_errors.append(traceback.format_exc())
                    raise

            real_claims = campaign.NativeClaims
            self.addCleanup(setattr, release, "_active", None)
            release._active = None
            with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                    patch.object(campaign, "NativeClaims",
                        side_effect=lambda _, r, it, gr: real_claims(root / "vm_claims" / gr["campaign_id"] / r["plan"]["attempt_id"], r, it, gr)), \
                    patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(launcher, "setup_command", side_effect=setup_cmd), \
                    patch.object(launcher, "run_stage", side_effect=in_process_stage):
                vm_result = launcher.launch(vm_capsule / "request.json",
                    output=root / "vm_working", scratch=root / "vm_temp", inputs=inputs_mount)

            self.assertEqual(vm_result["status"], "PASS", msg="\n".join(stage_errors) or str(vm_result))
            self.assertFalse((inputs_mount / "inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/test").exists())
            vm_archive = next((root / "vm_working").glob("*.zip"))
            with zipfile.ZipFile(vm_archive) as zf:
                vm_tel = json.loads(zf.read("run/telemetry.json"))
            self.assertEqual(vm_tel["memory"]["schema"], "internvl-v2-memory-v1")
            self.assertEqual(vm_tel["memory"]["status"], "OBSERVED")
            self.assertEqual(vm_tel["memory"]["errors"], [])
            self.assertNotIn("status", vm_tel["memory"]["cgroup"])
            kernel_state.update(status="COMPLETE", archive=vm_archive)

            # Operator terminal collection -> verify_bundle (including .f32 full-vocab trace!) -> mirrored Ledger COLLECTED.
            with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                    patch.object(requests.adapters.HTTPAdapter, "send", fake_adapter_send), \
                    patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(operator, "_api", return_value=fake_kaggle_api), \
                    patch("scripts.submit_internvl_v2.check_sdk", return_value=op.SDK_PINS), \
                    patch("safeshift.kaggle_handoff.subprocess.check_output", return_value=notebook_raw):
                collect_report = handoff.operate(handoff.Session(root / "attempt-1"), operator, "collect")

            self.assertEqual(collect_report["status"], "PASS", msg=str(collect_report))
            self.assertEqual(collect_report["verification"]["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})
            self.assertEqual(handoff.accept_report(handoff.Session(root / "attempt-1"))["status"], "PASS")

            # Measure final-source envelope and stage next resume shard (ordinals [1, 2], preserving ordinal 0).
            collected_arc = Path([e for e in ledger.events() if e["kind"] == "COLLECTED"][0]["archive"])
            measured = ledger.measure(collected_arc, job_seconds=1800)
            self.assertGreaterEqual(measured["safe_calls"], 2)
            with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                    patch.object(op, "api", return_value=Mock()), \
                    patch.object(op, "verify_python_input", return_value={"scope": "SYNTHETIC_PYTHON_PROOF"}):
                staged2 = stage(
                    ledger, req_fixture["execution_release"],
                    {"python_input": py.binding(), "technical_revision": req_fixture["bindings"]["runtime"]["technical_revision"],
                     "execution_input": {"kind": "dataset_sources", "ref": "nguynanhtn/synthetic-capsule-2/1"}},
                    cohort_img, directory=root / "attempt-2", calls=2, seconds=1800, action="resume",
                )
            self.assertEqual(staged2["status"], "STAGED_NOT_SUBMITTED")
            pkg2 = read(root / "attempt-2/package/safeshift_train3763_execution.json")
            self.assertEqual(pkg2["request"]["plan"]["scheduled_ordinals"], [1, 2])
            self.assertEqual(pkg2["request"]["plan"]["counts"], {"SUCCESS": 1, "NOT_ATTEMPTED": 3762})

    def test_multi_image_mixed_outcomes_mid_shard_fail_provider_ambiguity_and_tail_shard_e2e(self):
        # End-to-end negative & mixed-outcome shard test:
        # ordinal 0 -> SUCCESS, ordinal 1 -> INVALID (fenced JSON, retained .f32), ordinal 2 -> mid-shard TECHNICAL_ERROR,
        # ordinal 3 -> NOT_ATTEMPTED; provider RUNNING / UNKNOWN / timeout block read-only; COMPLETE collects FAIL ZIP;
        # next resume schedules ordinal 3+, while exact-target repair schedules only ordinal 2!
        cohort = synthetic_cohort()
        p = campaign.plan(cohort, [], action="initial", run_id="mixed-shard-1", attempt_id="attempt-1",
            max_calls=4, max_seconds=1800)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def img(row):
                path = root / f"img-{row['ordinal']}.bin"
                path.write_bytes(synthetic_bytes(row["ordinal"]))
                return path
            outcomes = {
                0: ('{"safety_level":"Level01"}', False),
                1: ('```json\n{"safety_level":"Level03"}\n```', False),
                2: ('{"safety_level":"Level04"}', True),
            }
            def mixed_generate(image, sample, binding, deadline):
                ord_num = int(Path(sample).name)
                resp, should_fail = outcomes[ord_num]
                write(Path(sample) / "native_call.json", {"binding": binding})
                raw = {"binding": binding, "response": resp, "hnlo": None, "hnlo_status": runtime.HNLO_STATUS,
                    "evidence_kind": "SYNTHETIC"}
                raw_sha = write(Path(sample) / "raw.json", raw)
                if should_fail:
                    raise RuntimeError("SYNTHETIC_MID_SHARD_CRASH")
                lbl = runtime.parse_label(resp)
                if lbl:
                    write(Path(sample) / "trace-verification.json", {"status": "SYNTHETIC_CONTROLLER_ONLY"})
                else:
                    write(Path(sample) / "trace-failure.json", {"status": "FAIL", "type": "ValueError"})
                return {"status": "SUCCESS" if lbl else "INVALID", "label": lbl,
                    "raw_sha256": raw_sha, "trace_verified": bool(lbl), "hnlo": None, "hnlo_status": runtime.HNLO_STATUS}

            backend = NS(environment={"scope": "SYNTHETIC_ONLY"}, generate=mixed_generate)
            arc = root / "mixed.zip"
            res = runtime.rehearse(root / "mixed_out", arc, cohort, p, [], lambda _: backend,
                image_path=img, tokenizer_sha="a" * 64)
            self.assertEqual(res["status"], "FAIL")
            self.assertEqual(res["model_calls"], 3)
            self.assertEqual(res["counts"], {"SUCCESS": 1, "INVALID": 1, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 3760})
            self.assertFalse((root / "mixed_out/samples/000003/started.json").exists())
            self.assertTrue((root / "mixed_out/samples/000000/raw.json").is_file())
            self.assertTrue((root / "mixed_out/samples/000001/raw.json").is_file())
            self.assertTrue((root / "mixed_out/samples/000002/raw.json").is_file())
            verified = runtime.verify_bundle(arc, sha(arc), p)
            self.assertEqual(verified["status"], "FAIL")
            h1 = runtime.sealed_history(arc, sha(arc), p)

            # Resume only schedules NOT_ATTEMPTED ordinals [3, 4], preserving SUCCESS(0), INVALID(1), TECHNICAL_ERROR(2)
            p_res = campaign.plan(cohort, [h1], action="resume", run_id="mixed-shard-2", attempt_id="attempt-2",
                max_calls=2, max_seconds=1800)
            self.assertEqual(p_res["scheduled_ordinals"], [3, 4])

            # Repair only schedules explicitly targeted failed records; targeting SUCCESS(0), NOT_ATTEMPTED(3), or wrong digest fails closed!
            rec0 = res["records"][0]
            rec2 = res["records"][2]
            rec3 = res["records"][3]
            for bad_targets in (
                {rec0["sample_id"]: digest(rec0)},
                {rec3["sample_id"]: digest(rec3)},
                {rec2["sample_id"]: "0" * 64},
            ):
                with self.assertRaises(ValueError):
                    campaign.plan(cohort, [h1], action="repair", run_id="bad-rep", attempt_id="attempt-2",
                        max_calls=1, max_seconds=1800, repair={
                            "targets": bad_targets,
                            "fix_sha256": digest(runtime.source_spec()), "regression_sha256": "e" * 64,
                            "diagnosis": "non-repairable or wrong-digest target must fail closed",
                        })
            p_rep = campaign.plan(cohort, [h1], action="repair", run_id="good-rep", attempt_id="attempt-2",
                max_calls=1, max_seconds=1800, repair={
                    "targets": {rec2["sample_id"]: digest(rec2)},
                    "fix_sha256": digest(runtime.source_spec()), "regression_sha256": "e" * 64,
                    "diagnosis": "SYNTHETIC mid-shard error repair",
                })
            self.assertEqual(p_rep["scheduled_ordinals"], [2])

            # Provider RUNNING, ambiguous status, and network timeout during collect all stop BLOCKED without ledger mutation
            req_f, grant_f, comments_f = campaign_fixture(root / "ledger")
            with patch.object(release, "get", side_effect=lambda k: deepcopy(comments_f[k])):
                ledger = campaign.Ledger.create(root / "ledger", root / "mirror", grant_f, "synthetic-machine")
                it = ledger.reserve(req_f)
            with handoff.lock(ledger.root):
                ledger.append("PUSH_INTENT", intent_sha256=digest(it))
            with patch.object(handoff, "private_root", side_effect=lambda p: Path(p).resolve()):
                sess = handoff.prepare(root / "sess", req_f)
                before_events = ledger.events()
                for bad_state in ("RUNNING", "QUEUED", "MYSTERY_PROVIDER_STATE", TimeoutError("PROVIDER_RPC_TIMEOUT")):
                    fake_op = handoff.Train3763Operator()
                    def fake_status(_req, _st=bad_state):
                        if isinstance(_st, Exception):
                            raise _st
                        return _st
                    with patch.object(fake_op, "status", side_effect=fake_status):
                        rep = handoff.operate(sess, fake_op, "collect")
                    self.assertEqual(rep["status"], "BLOCKED")
                    self.assertEqual(ledger.events(), before_events)
                    self.assertIsNotNone(ledger.open_intent())

    def test_native_backend_worker_graceful_stop_on_real_snapshot_hazards_and_blocks_measure(self):
        import torch
        from PIL import Image
        import scripts.internvl3763 as launcher
        from scripts import internvl_v2 as old_v2
        from safeshift import internvl_v2_memory as mem_lib
        from safeshift import verification173
        from test_internvl_v2_runtime import NativeCaptureTests as V2Helper

        real_snapshot = mem_lib.snapshot
        V2Helper.setUpClass()
        v2_helper = V2Helper("test_all_labels_actual_generate_full_raw_before_processor_and_parse")

        hazards = (
            ("cgroup_v1_incomplete", {"cgroup_v1_only": True}, "CGROUP_MEMORY_UNOBSERVED"),
            ("oom_kill_observed", {"mem_events": "oom 0\noom_kill 1\noom_group_kill 0\n"}, "CGROUP_OOM_OBSERVED"),
            ("low_cgroup_ram", {"mem_max": str(8 * 2**30), "mem_current": str(8 * 2**30 - 100 * 2**20)}, "CGROUP_MEMORY_HEADROOM_LOW"),
            ("low_host_ram_unlimited_cgroup", {"mem_max": "max", "mem_available_kb": 100 * 1024}, "CGROUP_MEMORY_HEADROOM_LOW"),
        )

        parent = runtime.ROOT / "data/processed"
        parent.mkdir(parents=True, exist_ok=True)
        for hazard_name, mem_kwargs, expected_reason in hazards:
            with self.subTest(hazard=hazard_name), tempfile.TemporaryDirectory(prefix="synthetic-mem-e2e-", dir=parent) as tmp:
                root = Path(tmp)
                req_fixture, grant, comments = campaign_fixture(
                    root / "ledger", actual_source=True, kernel_sources=("nguynanhtn/safeshift-prepare-internvl35/1",),
                )
                inputs_mount = root / "kaggle_input"
                master_file = inputs_mount / "safeshift-pilot-input/master_manifest.json"
                write(master_file, {"notice": "SYNTHETIC_MASTER"})
                image_root = inputs_mount / "inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH"
                img0 = image_root / "train/Annotations/synthetic-000000.jpg"
                img0.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (8, 8), (12, 34, 56)).save(img0, format="JPEG")
                cohort_img = deepcopy(req_fixture["bindings"]["runtime"]["execution_request"]["cohort"])
                cohort_img["samples"][0]["image_sha256"] = sha(img0)
                grant["cohort_sha256"] = digest(cohort_img)
                req_fixture["bindings"]["runtime"]["execution_request"]["cohort"] = cohort_img
                req_fixture["bindings"]["runtime"]["execution_request"]["projection_sha256"] = digest(cohort_img)
                p0 = campaign.plan(cohort_img, [], action="initial", run_id="synthetic180-1",
                    attempt_id="attempt-1", max_calls=1, max_seconds=1800)
                req_fixture["plan"] = p0
                req_fixture["plan_sha256"] = digest(p0)
                req_fixture["bindings"]["runtime"]["execution_request"]["plan"] = p0
                req_fixture["bindings"]["dataset"]["execution_request_sha256"] = digest(
                    req_fixture["bindings"]["runtime"]["execution_request"]
                )
                grant_cid = req_fixture["execution_release"]["comment_id"]
                grant_body = campaign.MARKER + "\n```json\n" + json.dumps(grant) + "\n```"
                comments[f"/issues/comments/{grant_cid}"]["body"] = grant_body
                req_fixture["execution_release"]["body_sha256"] = hashlib.sha256(grant_body.encode()).hexdigest()
                tech_cid = req_fixture["bindings"]["runtime"]["technical_revision"]["comment_id"]
                tech_obj = json.loads(comments[f"/issues/comments/{tech_cid}"]["body"].split("```json\n")[1].split("\n```")[0])
                audit_cid = tech_obj["audit"]["comment_id"]
                audit_obj = json.loads(comments[f"/issues/comments/{audit_cid}"]["body"].split("```json\n")[1].split("\n```")[0])
                audit_obj["campaign_sha256"] = digest(grant)
                audit_body = "SAFESHIFT_TRAIN3763_AUDIT_V1\n```json\n" + json.dumps(audit_obj) + "\n```"
                comments[f"/issues/comments/{audit_cid}"]["body"] = audit_body
                tech_obj["campaign_sha256"] = digest(grant)
                tech_obj["audit"]["body_sha256"] = hashlib.sha256(audit_body.encode()).hexdigest()
                tech_body = "SAFESHIFT_TRAIN3763_TECHNICAL_V1\n```json\n" + json.dumps(tech_obj) + "\n```"
                comments[f"/issues/comments/{tech_cid}"]["body"] = tech_body
                req_fixture["bindings"]["runtime"]["technical_revision"]["body_sha256"] = hashlib.sha256(tech_body.encode()).hexdigest()

                with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])):
                    ledger = campaign.Ledger.create(root / "ledger", root / "mirror", grant, "synthetic-machine")
                    intent = ledger.reserve(req_fixture)
                with handoff.lock(ledger.root):
                    ledger.append("PUSH_INTENT", intent_sha256=digest(intent))
                ledger.submitted(intent, {"job_id": req_fixture["job"], "version": 1})

                bad_snap = controller_fixtures.make_real_memory_snapshot(root / "bad_mem", **mem_kwargs)
                bad_proc = root / "bad_mem/proc"
                bad_cg = root / "bad_mem/cgroup"
                res_payload = {
                    "memory": {"available_bytes": 20 * 2**30, "cgroup_remaining_bytes": [20 * 2**30]},
                    "devices": [66, 1794],
                    "free_bytes": [20 * 2**30, 20 * 2**30],
                    "requested_reserves_bytes": [24 * 2**30, 2**30],
                    "model_fit": "NOT_ESTABLISHED",
                }
                tok_dir = root / "tok"
                tok_dir.mkdir()
                (tok_dir / "tokenizer.json").write_text('{"notice": "SYNTHETIC_TOKENIZER"}', encoding="utf8")
                shim = write_setup_harness(root)
                generate_invocations = []

                def fake_candidate_backend(key, source, weights, prompt, *, device, weight_verifier):
                    weight_verifier(weights, key)
                    b = v2_helper.backend(label=1)
                    orig_gen = b.model.generate
                    def fail_if_called(*a, **kw):
                        generate_invocations.append(1)
                        return orig_gen(*a, **kw)
                    b.model.generate = fail_if_called
                    b.prompt = prompt
                    b.processor = NS()
                    b.config = NS(text_config=NS(vocab_size=b.logit_width))
                    b.device = "cpu"
                    b.dtype = torch.float32
                    b.environment = {
                        "model": {"id": runtime.configuration()["model"], "revision": runtime.configuration()["revision"]},
                        "prompt_sha256": PROMPT_SHA,
                    }
                    return b

                def fake_preflight(spec, env_out, scratch, inputs, deadline):
                    for name in ("software.json", "hardware.json", "cuda.json", "allocation.json",
                                 "checkpoint.json", "checkpoint-stream.json", "processor.json"):
                        write(env_out / name, {"notice": "SYNTHETIC_PREFLIGHT"})
                    write(env_out / "preload-resources.json", res_payload)
                    write(env_out / "preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS",
                        "source_sha256": digest(spec), "model_calls": 0, "weights_loaded": False, "owner_slots_consumed": 0})
                    return tok_dir, root / "weights"

                mapping = [{**row, "image_locator": f"DATA_PATH/train/Annotations/synthetic-{row['ordinal']:06d}.jpg"}
                           for row in cohort_img["samples"]]
                train_receipt = {"status": "TRAIN_BYTES_PASS", "verified_images": 3763, "labels_exported": False}

                def setup_cmd(python, stage_name, spec_path, out, scratch, inputs, req, deadline):
                    return [sys.executable, "-B", str(shim), "--worker", stage_name, "--spec", str(spec_path),
                            "--output", str(out), "--scratch", str(scratch), "--inputs", str(inputs), "--request", str(req)]

                stage_errors = []

                def in_process_stage(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_roots=()):
                    try:
                        log, receipt = Path(log), Path(receipt)
                        if "offline_setup_harness.py" in " ".join(command):
                            with log.open("xb") as stream:
                                proc = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, timeout=30)
                            assert proc.returncode == 0, log.read_text(encoding="utf8", errors="replace")
                            sz = log.stat().st_size + (Path(watch_log_roots[0]) / "setup.log").stat().st_size
                            write(receipt, {"schema": "fresh-process-supervision-v1", "status": "EXITED",
                                "returncode": 0, "seconds": 1.0, "log_bytes": sz, "group_kill_sent": True,
                                "automatic_retry": False, "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
                            return {"status": "EXITED", "returncode": 0}
                        with log.open("xb") as stream:
                            stream.write(b"WORKER_IN_PROCESS\n")
                        out_dir = Path(command[command.index("--output") + 1])
                        req_path = Path(command[command.index("--request") + 1])
                        release._active = None
                        with patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                                patch.object(runtime, "preflight", side_effect=fake_preflight), \
                                patch.object(campaign, "sha", side_effect=lambda p: MASTER_SHA if Path(p) == master_file else sha(p)), \
                                patch.object(verification173, "verify_train", return_value=(train_receipt, cohort_img, mapping)), \
                                patch("safeshift.candidates.backend.CandidateBackend", side_effect=fake_candidate_backend), \
                                patch("safeshift.internvl_v2_memory.verify_checkpoint", return_value={"status": "STREAM_VERIFIED"}), \
                                patch("safeshift.internvl_v2_memory.resource_check", return_value=res_payload), \
                                patch("safeshift.internvl_v2_memory.snapshot", side_effect=lambda *_: real_snapshot(bad_proc, bad_cg)), \
                                patch("torch.cuda.max_memory_allocated", return_value=4096), \
                                patch("torch.cuda.max_memory_reserved", return_value=8192):
                            w_res = runtime.worker(req_path, output=out_dir, scratch=root / "vm_temp", inputs=inputs_mount,
                                deadline=time.monotonic() + 600)
                            self.assertEqual(w_res["status"], "PASS", msg=str(w_res.get("failure")))
                            self.assertEqual(w_res["model_calls"], 0)
                            self.assertEqual(w_res["counts"], {"NOT_ATTEMPTED": 3763})
                        write(receipt, {"schema": "fresh-process-supervision-v1", "status": "EXITED",
                            "returncode": 0, "seconds": 2.0, "log_bytes": log.stat().st_size, "group_kill_sent": True,
                            "automatic_retry": False, "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
                        return {"status": "EXITED", "returncode": 0}
                    except BaseException:
                        import traceback
                        stage_errors.append(traceback.format_exc())
                        raise

                vm_capsule = root / "vm_capsule"
                vm_capsule.mkdir()
                write(vm_capsule / "request.json", req_fixture)
                write(vm_capsule / "campaign-intent.json", intent)
                real_claims = campaign.NativeClaims
                release._active = None
                with patch("socket.socket", side_effect=AssertionError("NO_NETWORK")), \
                        patch.object(campaign, "NativeClaims",
                            side_effect=lambda _, r, it, gr: real_claims(root / "vm_claims", r, it, gr)), \
                        patch.object(release, "get", side_effect=lambda p: deepcopy(comments[p])), \
                        patch.object(launcher, "setup_command", side_effect=setup_cmd), \
                        patch.object(launcher, "run_stage", side_effect=in_process_stage):
                    vm_result = launcher.launch(vm_capsule / "request.json",
                        output=root / "vm_working", scratch=root / "vm_temp", inputs=inputs_mount)
                release._active = None

                self.assertEqual(vm_result["status"], "PASS", msg="\n".join(stage_errors) or str(vm_result))
                self.assertEqual(generate_invocations, [])
                vm_archive = next((root / "vm_working").glob("*.zip"))
                with zipfile.ZipFile(vm_archive) as zf:
                    stop_obj = json.loads(zf.read("run/stop.json"))
                    tel_obj = json.loads(zf.read("run/telemetry.json"))
                self.assertEqual(stop_obj, {"reason": expected_reason})
                # snapshot() timestamps each fresh observation. Compare the
                # stable proc/cgroup fields and independently prove freshness.
                self.assertGreaterEqual(tel_obj["memory"]["monotonic"], bad_snap["monotonic"])
                self.assertEqual(
                    {k: v for k, v in tel_obj["memory"].items() if k not in ("cuda_visible_devices", "monotonic")},
                    {k: v for k, v in bad_snap.items() if k not in ("cuda_visible_devices", "monotonic")},
                )
                self.assertEqual(runtime.inspect_memory_snapshot(tel_obj["memory"]), expected_reason)

                # Bundle collects cleanly (0 calls, 3763 NOT_ATTEMPTED), and Ledger.measure() blocks it fail-closed!
                ledger.collect(req_fixture, vm_archive, {
                    "state": "COMPLETE", "job_id": req_fixture["job"], "version": 1,
                    "notebook_sha256": req_fixture["notebook_sha256"],
                })
                with self.assertRaisesRegex(ValueError, "MEASUREMENT_RUN_STOPPED_EARLY"):
                    ledger.measure(vm_archive, job_seconds=1800)


if __name__ == "__main__":
    unittest.main()
