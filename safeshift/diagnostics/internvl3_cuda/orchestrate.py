"""Software-only preparation and six isolated observations; no model snapshot."""
import json
from pathlib import Path
import platform
import subprocess

from ..one_click.artifacts import package, write
from ..one_click.orchestrate import child_environment
from ..one_click.provision import build_environment
from .contract import AUTHORITY, STAGES, authorize
from .probes import error_metadata, static_metadata


class Operations:
    def __init__(self, repo, work, evidence, source_path):
        self.repo, self.work, self.evidence, self.source = repo, work, evidence, source_path

    def prepare(self):
        if platform.system() != "Linux" or platform.machine() != "x86_64" or not Path("/kaggle/working").is_dir():
            raise RuntimeError("KAGGLE_LINUX_X86_64_REQUIRED")
        write(self.evidence / "host-metadata.json", static_metadata("HOST_STATIC_UNGUARDED_NO_CUDA"))
        self.python = build_environment("internvl3", self.repo, self.repo.parent / "runtime/internvl3", self.evidence / "build")
        # build_environment installs locked software only. Never invoke model provisioning.

    def worker(self, stage):
        destination = self.evidence / stage
        env = child_environment("internvl3", self.repo, Path("data/processed/cuda-diagnostic-unused-cache"))
        command = [str(self.python), "-m", "safeshift.diagnostics.internvl3_cuda.worker", "--stage", stage,
                   "--evidence", str(destination), "--source", str(self.source)]
        with (self.evidence / (stage + ".log")).open("xb") as stream:
            process = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=subprocess.STDOUT, close_fds=True, timeout=120)
        if not (destination / "result.json").is_file():
            raise RuntimeError("DIAGNOSTIC_CHILD_MISSING_RESULT")
        result = json.loads((destination / "result.json").read_bytes())
        if process.returncode != (2 if result["fatal"] else 0):
            raise RuntimeError("DIAGNOSTIC_EXIT_RECORD_MISMATCH")
        return result


def run(repo, work, output, source, *, operations_factory=Operations):
    repo, work, output = Path(repo), Path(work), Path(output)
    evidence = work / "evidence"
    evidence.mkdir()
    result = {"schema": "internvl3-cuda-diagnostic-v1", "result": "BLOCKED", "stages": [],
              "CUDA_ROOT_CAUSE_CONFIRMED": False, "load_calls": 0, "generate_calls": 0,
              "source": source, "gpu_initialization_attempted": False,
              "interpretation": "OBSERVATIONS_ONLY;NO_AUTOMATIC_CUDA_OR_SECURITY_PASS"}
    try:
        grant = authorize(json.loads((repo / AUTHORITY).read_bytes()), source)
        ledger = output / (".internvl3-cuda-diagnostic-" + grant["attempt_id"])
        ledger.mkdir(exist_ok=False)
        write(ledger / "claim.json", {"attempt_id": grant["attempt_id"], "source": source["merge_commit"]})
        write(evidence / "authority.json", json.loads((repo / AUTHORITY).read_bytes()))
        write(evidence / "source.json", source)
        ops = operations_factory(repo, work, evidence, evidence / "source.json")
        ops.prepare()
        for stage in STAGES:
            # This marker records launch intent, never successful initialization.
            if stage in ("cuinit", "runtime_count"):
                result["gpu_initialization_attempted"] = True
                write(evidence / (stage + "-launch.json"), {"stage": stage, "scope": "LAUNCH_INTENT_NOT_API_RETURN"})
            row = ops.worker(stage)
            result["stages"].append(row)
            if row["fatal"]:
                break
        if len(result["stages"]) == len(STAGES) and not any(r["fatal"] for r in result["stages"]):
            result["result"] = "DIAGNOSTICS_COMPLETED"
    except BaseException as error:
        result["error"] = error_metadata(error)
    finally:
        write(evidence / "result.json", result)
        write(output / (work.name + "_result.json"), result)
        try:
            archive = package(evidence, output, work.name)
            print("Diagnostic evidence:", archive.name)
        except BaseException as error:
            result["result"] = "EXPORT_FAILED"
            write(output / (work.name + "_export_failure.json"), {"error": error_metadata(error), "probe_result": result})
        print("CUDA root cause remains unconfirmed. No model load or inference. Result:", result["result"])
    return result
