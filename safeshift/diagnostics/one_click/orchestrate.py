"""Sequential, no-resume Run All state machine, with injectable CPU test boundary."""

from copy import deepcopy
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import traceback

from .artifacts import package, table, write
from .contract import AUTHORITY, MODELS, ORDER, authorize
from .worker import empty


def child_environment(model, repo, cache, *, offline=True, cpu=False):
    # Do not inherit host Python, CUDA, proxy, token or allocator configuration.
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update(PYTHONNOUSERSITE="1", PYTHONPATH=str(repo), PYTHONDONTWRITEBYTECODE="1",
               CUDA_VISIBLE_DEVICES="" if cpu else MODELS[model]["cuda_visible_devices"],
               HF_HUB_CACHE=str(Path(repo) / cache), HF_HOME=str(Path(repo) / cache / "home"),
               HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_XET="1", HF_HUB_ENABLE_HF_TRANSFER="0",
               HF_HUB_OFFLINE="1" if offline else "0", TRANSFORMERS_OFFLINE="1" if offline else "0",
               TOKENIZERS_PARALLELISM="false", PIP_CONFIG_FILE=os.devnull)
    if model == "qwen3":
        env["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    return env


def host_conditions(output):
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("KAGGLE_LINUX_X86_64_REQUIRED")
    if not Path("/kaggle/working").is_dir():
        raise RuntimeError("KAGGLE_WORKING_DIRECTORY_REQUIRED")
    for name in ("git", "gcc", "make", "pkg-config", "nvidia-smi"):
        if shutil.which(name) is None:
            raise RuntimeError("BUILD_OR_GPU_TOOL_MISSING:" + name)
    info = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    available = int(info["MemAvailable"].strip().split()[0]) * 1024
    free = shutil.disk_usage(output).free
    if available < 24 * 2**30:
        raise RuntimeError("HOST_RAM_BELOW_24_GIB")
    if free < 50 * 2**30:
        raise RuntimeError("DISK_FREE_BELOW_50_GIB_TWO_ENVS_AND_WEIGHTS")
    raw = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version",
                                   "--format=csv,noheader,nounits"], text=True)
    rows = [r.split(",") for r in raw.strip().splitlines()]
    if len(rows) != 2 or any(r[0].strip() not in ("Tesla T4", "NVIDIA T4", "T4") for r in rows):
        raise RuntimeError("EXACT_HOST_T4_X2_REQUIRED")
    if any(int(r[2]) < 13 * 1024 for r in rows):
        raise RuntimeError("HOST_GPU_FREE_VRAM_BELOW_13_GIB")
    return {"available_ram_bytes": available, "free_disk_bytes": free, "nvidia_smi": raw,
            "ram_requirement": "24 GiB available", "disk_requirement": "50 GiB available (conservative admission estimate)"}


class Operations:
    worker_module = "safeshift.diagnostics.one_click.worker"

    def __init__(self, repo, work, evidence, source_path, grant):
        self.repo, self.work, self.evidence = Path(repo), Path(work), Path(evidence)
        self.source_path, self.grant = Path(source_path), grant
        self.pythons = {}

    def preflight(self):
        result = host_conditions(self.repo.parent)
        output_free = shutil.disk_usage(self.work).free
        if output_free < 4 * 2**30:
            raise RuntimeError("OUTPUT_DISK_FREE_BELOW_4_GIB")
        return {**result, "output_free_bytes": output_free, "output_requirement": "4 GiB available"}

    def cache(self, model):
        return "data/processed/hnlo-one-click/" + self.grant["attempt_id"] + "/cache/" + model

    def prepare(self, model):
        from .provision import build_environment, invoke
        evidence = self.evidence / model
        evidence.mkdir()
        python = build_environment(model, self.repo, self.repo.parent / "runtime" / model, evidence / "build")
        self.pythons[model] = python
        env = child_environment(model, self.repo, self.cache(model), offline=False, cpu=True)
        # Public ungated models normally need no token. Kaggle Secret is optional,
        # passed only to this preparation child, never the notebook/log/manifest.
        try:
            from kaggle_secrets import UserSecretsClient
            token = UserSecretsClient().get_secret("HF_TOKEN")
        except Exception:
            token = None
        if token:
            env["HF_TOKEN"] = token
        invoke([python, "-m", "safeshift.diagnostics.one_click.provision", "--model", model,
                "--cache", self.cache(model), "--evidence", evidence], self.repo,
               evidence / "model-provision.log", env=env)
        return {"status": "PROVISIONED", "python_scratch_relative": python.relative_to(self.repo.parent).as_posix()}

    def worker(self, mode, model):
        evidence = self.evidence / model / mode
        env = child_environment(model, self.repo, self.cache(model), cpu=mode == "replay")
        command = [str(self.pythons[model]), "-m", self.worker_module, "--mode", mode,
                   "--model", model, "--cache", self.cache(model), "--evidence", str(evidence),
                   "--source", str(self.source_path), "--capture-root", str(self.work)]
        with (self.evidence / model / (mode + ".log")).open("xb") as stream:
            process = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, close_fds=True)
        if not (evidence / "result.json").is_file():
            raise RuntimeError("WORKER_TERMINATED_WITHOUT_FINAL_RECORD:" + str(process.returncode))
        result = json.loads((evidence / "result.json").read_bytes())
        if process.returncode not in (0, 2) or (process.returncode == 2 and result["result"] != "FAILED"):
            raise RuntimeError("WORKER_EXIT_AND_RECORD_MISMATCH")
        return result

    def release(self, model):
        # subprocess.run has waited for termination; all CUDA allocations belong
        # to that exited interpreter. Recheck host memory before the next child.
        raw = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], text=True)
        write(self.evidence / model / "resource-release.json", {"child_process_exited": True, "free_vram_mib": raw.splitlines()})
        if len(raw.splitlines()) != 2 or any(int(v) < 13 * 1024 for v in raw.splitlines()):
            raise RuntimeError("GPU_RESOURCES_NOT_RELEASED")

    def collect(self, model, row):
        # Copy byte-for-byte only this run's capture, including any torn files.
        run_id = "hnlo-" + self.grant["attempt_id"] + "-" + model
        original = self.work / "data/processed/hnlo_capture" / run_id
        if original.is_dir():
            copied = self.evidence / model / "capture"
            shutil.copytree(original, copied, symlinks=False)
            if row["CAPTURE_VALID"]:
                from safeshift.pa3.native.journal import Journal
                if not Journal(copied).verify():
                    raise ValueError("EXPORTED_CAPTURE_NOT_SEALED")
        # Durable start/return markers survive a killed worker and do not imply
        # successful return when only the start marker is present.
        for kind in ("load", "generate"):
            start = self.evidence / model / "probe" / ("native-" + kind + "-start.json")
            row[kind + "_calls"] = int(start.is_file())
            row[kind + "_returned"] = (start.parent / ("native-" + kind + "-return.json")).is_file()
        return row


def common_error(error):
    return isinstance(error, (PermissionError, OSError)) or any(s in str(error) for s in
        ("CHECKSUM", "SOURCE", "INVENTORY", "AUTHORITY", "WORKER_TERMINATED", "WORKER_EXIT", "RESOURCES_NOT_RELEASED"))


def fail(row, status, error):
    row.update(result=status, reason=str(error), error_type=type(error).__name__, failure_traceback=traceback.format_exc(),
               hnlo=None, technical_hnlo="N/A", TECHNICAL_HNLO_VALID=False,
               alignment="N/A", ALIGNMENT_VALID=False)


def run(repo, work, output, source, *, operations_factory=Operations,
        order=ORDER, authority_path=AUTHORITY, authorizer=authorize,
        result_schema="hnlo-two-model-probe-v1"):
    repo, work, output = Path(repo), Path(work), Path(output)
    evidence = work / "evidence"
    evidence.mkdir()
    rows = {model: empty(model) for model in order}
    result = {"schema": result_schema, "source": source,
              "HNLO_RESEARCH_VERIFIED": False, "models": [], "common_blocker": None}
    fatal = False
    ops = None
    try:
        authority = json.loads((repo / authority_path).read_bytes())
        grant = authorizer(authority, source)
        # A second Run All cannot erase/reuse a partial or successful attempt.
        # Across brand-new Kaggle sessions, non-reuse also needs Lead/Owner
        # accounting; no offline local filesystem can attest global non-replay.
        ledger = output / (".hnlo-attempt-" + grant["attempt_id"])
        ledger.mkdir(exist_ok=False)
        write(ledger / "claim.json", {"attempt_id": grant["attempt_id"], "source": source["merge_commit"], "work": work.name})
        write(evidence / "authority.json", authority)
        write(evidence / "source.json", source)
        ops = operations_factory(repo, work, evidence, evidence / "source.json", grant)
        write(evidence / "host.json", ops.preflight())
        # Finish all online work before the first model inference.
        for model in order:
            if fatal:
                break
            try:
                rows[model]["provision"] = ops.prepare(model)
                rows[model].update(ops.worker("inspect", model))
            except BaseException as error:
                fail(rows[model], "BLOCKED", error)
                rows[model]["common_fatal"] = common_error(error)
            fatal = bool(rows[model].get("common_fatal"))
        # No call to prepare occurs after this point. Probe/replay workers enforce
        # offline flags, irreversible kernel filter and reused Python guard.
        for model in order:
            if fatal:
                if rows[model]["result"] in ("ENVIRONMENT_VALID", "NOT_ATTEMPTED"):
                    rows[model].update(result="BLOCKED", reason="COMMON_SAFETY_GATE_FAILED")
                continue
            if rows[model]["result"] != "ENVIRONMENT_VALID":
                continue
            try:
                native = ops.worker("probe", model)
                rows[model].update(native)
                fatal = bool(native.get("common_fatal"))
                # Wait/exit/release precedes CPU replay and the next GPU child.
                ops.release(model)
                if native["result"] == "AWAITING_CPU_REPLAY":
                    reviewed = ops.worker("replay", model)
                    for key in ("environment", "t1", "load_calls", "generate_calls"):
                        reviewed.pop(key, None)
                    for key in ("memory_before", "memory_after", "elapsed_seconds", "memory_collection_error"):
                        if key in reviewed:
                            reviewed["cpu_replay_" + key] = reviewed.pop(key)
                    rows[model].update(reviewed)
                    fatal |= bool(reviewed.get("common_fatal"))
            except BaseException as error:
                fail(rows[model], "FAILED", error)
                fatal = common_error(error)
            finally:
                try:
                    rows[model] = ops.collect(model, rows[model])
                except BaseException as error:
                    fail(rows[model], "FAILED", error)
                    rows[model]["evidence_collection_error"] = str(error)
                    fatal = True
    except BaseException as error:
        result["common_blocker"] = {"error_type": type(error).__name__, "reason": str(error), "traceback": traceback.format_exc()}
        for row in rows.values():
            if row["result"] in ("NOT_ATTEMPTED", "ENVIRONMENT_VALID"):
                row.update(result="BLOCKED", reason=str(error))
    finally:
        result["models"] = [deepcopy(rows[k]) for k in order]
        result["result"] = "TECHNICAL_VALID" if all(r["TECHNICAL_HNLO_VALID"] and r["result"] == "TECHNICAL_VALID" for r in rows.values()) else "BLOCKED" if all(r["load_calls"] == 0 for r in rows.values()) else "PARTIAL_OR_NA"
        result["result_scope"] = "PROBE_AND_CPU_REPLAY_BEFORE_EXPORT"
        result["export_status"] = "SEE_SHA256_OR_EXPORT_FAILURE_RECEIPT"
        result["gpu_probe_status"] = "ATTEMPTED" if any(r["load_calls"] for r in rows.values()) else "NOT_RUN"
        stem = work.name
        errors = []
        if result["common_blocker"]:
            errors.append(result["common_blocker"]["traceback"])
        errors.extend(row["failure_traceback"] for row in rows.values() if row.get("failure_traceback"))
        if errors:
            with (evidence / "errors.log").open("x", encoding="utf-8") as stream:
                stream.write("\n".join(errors))
                stream.flush()
                os.fsync(stream.fileno())
        write(evidence / "result.json", result)
        write(output / (stem + "_result.json"), result)
        report = ("# SafeShift technical HNLO probe\n\n" + table(result["models"])
                  + "\nHNLO_RESEARCH_VERIFIED=false. Technical synthetic evidence; no Seminar performance metric.\n\n")
        for row in result["models"]:
            report += ("- " + row["model"] + ": load=" + str(row["load_calls"]) + ", generate=" + str(row["generate_calls"])
                       + "; HNLO=" + str(row["hnlo"]) + "; " + row.get("reason", "") + "\n")
        if result["common_blocker"]:
            report += "\nBLOCKED: " + result["common_blocker"]["reason"] + "\n"
        for target in (evidence / "report.md", output / (stem + "_report.md")):
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(report)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            archive = package(evidence, output, stem)
            print("Evidence:", archive.name)
        except BaseException as error:
            print("EVIDENCE_EXPORT_FAILED; completed source files retained:", type(error).__name__, str(error))
            # A distinct record; never overwrite the earlier result or partial tar.
            result["export_status"], result["result"] = "FAILED", "EXPORT_FAILED"
            write(output / (stem + "_export_failure.json"), {"result": "EXPORT_FAILED", "reason": str(error), "traceback": traceback.format_exc(), "probe_result": result})
            report += "\nEXPORT_FAILED: " + str(error) + ". Earlier JSON describes probe state before export.\n"
            with (output / (stem + "_export_failure.md")).open("x", encoding="utf-8") as stream:
                stream.write(report)
        print(report)
    return result
