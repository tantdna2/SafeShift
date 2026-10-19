"""One-click one-model/one-shard unit, never resumes or retries failed samples."""
import json
from pathlib import Path
import shutil
import subprocess
import time

from ..resource_pilot.resources import timed, Sampler, tree_bytes
from .inputs import discover_train, check_images, stage_images, error_report
from .budget import estimate, admit, admit_gpu

from safeshift.pa3.native.journal import Journal, no_alias
from ..one_click.artifacts import package, sha256, write
from ..one_click.orchestrate import child_environment, host_conditions
from . import cohort
from .audit import seal_raw
from .contract import AUTHORITY, authorize, unit


def execution_inventory(evidence, rows):
    """Failure-only accounting without GT/tokenizer; never labels an unaudited SUCCESS."""
    index = Journal(Path(evidence) / "raw/index")
    result = []
    for i, row in enumerate(rows):
        name = f"sample-{i:06d}"
        status, reported = "NOT_ATTEMPTED", None
        try:
            if index.root.exists() and index.exists(name + ".attempt"):
                status = "INTERRUPTED"
                if index.exists(name + ".result"):
                    reported = index.read(name + ".result")["status"]
                    status = reported if reported in ("INVALID", "TECHNICAL_ERROR", "INTERRUPTED") else "TECHNICAL_ERROR"
                else:
                    cap = Journal(Path(evidence) / "raw" / name)
                    if cap.root.exists() and cap.exists("error"):
                        status = cap.read("error")["status"]
        except (OSError, ValueError):
            status = "INTERRUPTED"
        result.append({"sample_id": row["sample_id"], "image_sha256": row["image_sha256"],
                       "status": status, "worker_reported_status": reported,
                       "score": None, "eligible": False, "reason": "CPU_AUDIT_NOT_VERIFIED"})
    staging = Journal(Path(evidence) / "input-staging")
    try:
        if staging.root.exists() and staging.exists("failure"):
            failure = staging.read("failure")
            i = failure["ordinal"]
            if type(i) is int and 0 <= i < len(result):
                result[i].update(status="TECHNICAL_ERROR", reason="INPUT_STAGING:" + failure["type"])
    except (OSError, ValueError):
        pass
    return result


class Operations:
    kaggle_inputs = Path("/kaggle/input")

    def __init__(self, repo, work, evidence, source_path, u):
        self.repo, self.work, self.evidence = Path(repo), Path(work), Path(evidence)
        self.source_path, self.u = Path(source_path), u
        self.cache = "data/processed/hnlo_train_cache/" + u["run_id"]
        self.inputs = self.repo / "data/processed/hnlo_train_inputs" / u["run_id"]

    def check_inputs(self, rows):
        self.dataset = discover_train(self.kaggle_inputs)
        self.input_metadata = check_images(self.dataset, rows)
        return {"dataset_root_relative_to_input": self.dataset.relative_to(self.kaggle_inputs).as_posix(),
                "count": len(rows), "images": self.input_metadata, "image_bytes_read": False,
                "labels_or_gt_read": False}

    def preflight(self):
        plan = estimate(self.u["count"], sum(r["size_bytes"] for r in self.input_metadata))
        output = self.output
        result = admit(plan, output_free=shutil.disk_usage(self.work).free,
            scratch_free=shutil.disk_usage(self.repo.parent).free,
            same_device=self.work.stat().st_dev == self.repo.parent.stat().st_dev,
            existing_output=tree_bytes(output))
        write(self.evidence / "budget.json", result)
        host = host_conditions(self.repo.parent)  # nvidia-smi only; no torch/CUDA initialization.
        host['gpu_budget'] = admit_gpu(self.u['model'], host['nvidia_smi'])
        return {**host, "budget": result}

    def software(self):
        from ..one_click.provision import build_environment
        self.python = build_environment(self.u["model"], self.repo,
            self.repo.parent / "runtime" / self.u["model"], self.evidence / "software")

    def worker(self, mode):
        env = child_environment(self.u["model"], self.repo, self.cache)
        command = [str(self.python), "-m", "safeshift.diagnostics.hnlo_train.worker", "--mode", mode,
            "--model", self.u["model"], "--shard", str(self.u["shard"]), "--cache", self.cache,
            "--evidence", str(self.evidence / mode), "--source", str(self.source_path),
            "--inputs", str(self.inputs), "--raw", str(self.evidence / "raw")]
        with (self.evidence / (mode + ".log")).open("xb") as stream:
            proc = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL,
                                  stdout=stream, stderr=subprocess.STDOUT, close_fds=True, timeout=36600)
        path = self.evidence / mode / "result.json"
        if not path.exists():
            raise RuntimeError("WORKER_KILLED_RAW_PRESERVED_NO_RETRY")
        result = json.loads(path.read_bytes())
        if proc.returncode or result["status"] != "RETURNED":
            raise RuntimeError("WORKER_FAILED_RAW_PRESERVED_NO_RETRY")
        return result

    def provision(self):
        from ..one_click.provision import invoke
        env = child_environment(self.u["model"], self.repo, self.cache, offline=False, cpu=True)
        invoke([self.python, "-m", "safeshift.diagnostics.one_click.provision", "--model", self.u["model"],
            "--cache", self.cache, "--evidence", self.evidence / "checkpoint"], self.repo,
            self.evidence / "checkpoint.log", env=env)

    def stage(self, rows):
        stage_images(self.dataset, rows, self.inputs, self.evidence / "input-staging")

    def evaluate(self):
        # A new CPU-only interpreter, no torch import or checkpoint loading.
        env = child_environment(self.u["model"], self.repo, self.cache, cpu=True)
        env.update(USE_TORCH="0", USE_TF="0", USE_FLAX="0")
        command = [str(self.python), "-m", "safeshift.diagnostics.hnlo_train.evaluate", "--root", str(self.evidence),
                   "--cache", self.cache, "--model", self.u["model"]]
        with (self.work / "cpu-audit.log").open("xb") as stream:
            process = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL,
                                     stdout=stream, stderr=subprocess.STDOUT, close_fds=True)
        # Log is outside immutable raw custody; export it as an outer sibling.
        if process.returncode not in (0, 2) or not (self.evidence / "report/metrics.json").is_file():
            raise RuntimeError("CPU_AUDIT_FAILED_OR_PARTIAL_NO_REPAIR")
        return json.loads((self.evidence / "report/metrics.json").read_bytes())


def run(repo, work, output, source, model, shard, *, operations_factory=Operations):
    repo, work, output = Path(repo), Path(work), Path(output)
    evidence = work / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    u = unit(model, shard)
    result = {"schema": "hnlo-train-unit-result-v1", "unit": u, "status": "BLOCKED",
              "scope": "DESCRIPTIVE_FULL_TRAIN", "dataset_read": False, "provisioning_started": False,
              "gpu_worker_started": False, "inference_started": False, "retry": False,
              "research_generalization_claim": False,
              "coverage": {"planned": u["count"], "scored": 0, "coverage": 0.0,
                           "status_counts": {s: (u["count"] if s == "NOT_ATTEMPTED" else 0) for s in
                            ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "NOT_ATTEMPTED")}}}
    operations, bound, rows, sampler = None, False, None, None
    phases, current_phase = {}, "authority"
    result["full_vocab_replay"] = False
    result["pilot_overlap"] = {"shard0_ordinals": list(range(8)), "keep_in_cohort": True,
        "pilot_output_reused": False, "new_attempts_journaled": True}
    def phase(name, callback):
        nonlocal current_phase
        current_phase = name
        began = time.monotonic()
        try:
            return timed(evidence / (name + "-timing.json"), callback)
        finally:
            phases[name] = time.monotonic() - began
    try:
        authority = json.loads((repo / AUTHORITY).read_bytes())
        authorize(authority, source, model, shard)
        current_phase = "attempt_consumption"
        ledger = no_alias(output / "data/processed/hnlo_train_attempts" / u["run_id"])
        ledger.mkdir(parents=True, exist_ok=False)
        write(ledger / "consumed.json", {"unit": u, "source": source["merge_commit"]})
        result["status"] = "FAILED"
        current_phase = "manifest_binding"
        rows = cohort.inference(repo)[shard]
        write(evidence / "binding.json", {"unit": u, "samples": rows, "source": source, "authority": authority})
        write(evidence / "source.json", source)
        bound = True
        operations = operations_factory(repo, work, evidence, evidence / "source.json", u)
        operations.output = output
        write(evidence / "train-preflight.json", phase("train_preflight", lambda: operations.check_inputs(rows)))
        write(evidence / "host.json", phase("resource_preflight", operations.preflight))
        sampler = Sampler({"scratch": repo.parent, "output": output})
        sampler.start()
        result["dataset_read"] = True
        phase("image_staging", lambda: operations.stage(rows))
        result["provisioning_started"] = True
        phase("environment_setup", operations.software)
        result["gpu_worker_started"] = True
        phase("guarded_cuda_admission", lambda: operations.worker("inspect"))
        phase("checkpoint_provision", operations.provision)
        result["inference_started"] = True
        phase("inference_worker", lambda: operations.worker("inference"))
        result["status"] = "RAW_RETURNED"
    except BaseException as error:
        result.update(error=error_report(error, current_phase))
        if current_phase == "train_preflight" and not (evidence / "train-preflight.json").exists():
            write(evidence / "train-preflight.json", {"status": "FAILED", "error": result["error"],
                "image_bytes_read": False, "labels_or_gt_read": False})
    result["phases_seconds"] = phases
    write(evidence / "supervisor.json", result)
    custody_ok = False
    try:
        seal_raw(evidence)
        custody_ok = True
    except BaseException as error:
        result.update(status="PARTIAL" if result["inference_started"] else result["status"],
            custody_error=error_report(error, "raw_custody"))
    if bound and operations is not None and custody_ok and result["inference_started"]:
        try:
            evaluation = timed(work / "cpu-audit-timing.json", operations.evaluate)  # label permission checked again on CPU
            result["status"] = "COMPLETE" if evaluation["completed"] and "error" not in result else "PARTIAL"
            result["metrics"] = evaluation
            result["coverage"] = evaluation["overall"]["coverage"]
            report = evidence / "report/audit.json"
            if report.exists():
                audited = json.loads(report.read_bytes())["results"]
                result["sample_journal"] = [{k: r[k] for k in
                    ("sample_id", "status", "attempted", "persisted", "parsed", "errors")} for r in audited]
        except BaseException as error:
            result.update(status="PARTIAL", cpu_audit="FAILED", cpu_audit_error={"type": type(error).__name__})
            if result["inference_started"]:
                result["coverage"] = {"planned": u["count"], "scored": 0, "coverage": 0.0,
                                      "reason": "CPU_AUDIT_REQUIRED_RAW_PRESERVED"}
    if bound and "sample_journal" not in result:
        result["sample_journal"] = execution_inventory(evidence, rows)
        result["coverage"]["status_counts"] = {s: sum(r["status"] == s for r in result["sample_journal"]) for s in
            ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "NOT_ATTEMPTED")}
    if not bound:
        result["sample_journal"] = [{"ordinal": i, "status": "NOT_ATTEMPTED"} for i in range(u["count"])]
    for i, entry in enumerate(result["sample_journal"]):
        entry.setdefault("ordinal", i)
        entry["native_call_start_recorded"] = (evidence / "raw/index" / f"sample-{i:06d}.native-call.json").exists()
        entry["staging_read_started"] = (evidence / "input-staging" / f"image-{i:06d}.read-start.json").exists()
    if current_phase == "train_preflight" and result.get("error", {}).get("ordinal") is not None:
        entry = result["sample_journal"][result["error"]["ordinal"]]
        entry.update(status="TECHNICAL_ERROR", reason=result["error"]["reason"])
        result["coverage"]["status_counts"] = {s: sum(r["status"] == s for r in result["sample_journal"])
            for s in ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "NOT_ATTEMPTED")}
    # Outer audit files are allowed siblings of immutable custody.
    for name in ("cpu-audit.log", "cpu-audit-timing.json"):
        path = work / name
        if path.exists():
            # Timing lives beside raw evidence so custody verification remains unchanged.
            if name.endswith(".log"):
                shutil.copyfile(path, evidence / name)
    def read_timing(path):
        if not path.exists():
            return None
        try:
            return json.loads(path.read_bytes())["seconds"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            result.setdefault("timing_errors", []).append({"artifact": path.name,
                **error_report(error, "timing_readback")})
            return None
    result["model_load_seconds"] = read_timing(evidence / "raw/model-load-timing.json")
    image_timings = [read_timing(p) for p in (evidence / "raw/timings").glob("*.json")]
    measured = [v for v in image_timings if isinstance(v, (int, float))]
    result["measured_image_seconds"] = sum(measured) if measured else None
    result["resources"] = sampler.finish() if sampler else {"coverage": "NOT_STARTED"}
    result["phases_seconds"]["cpu_audit"] = read_timing(work / "cpu-audit-timing.json")
    write(evidence / "result.json", result)
    begin = time.monotonic()
    receipt = {"status": "FAILED", "unit": u, "full_vocab_replay": False}
    try:
        archive = package(evidence, output, u["run_id"])
        receipt.update(status="EXPORTED", archive=archive.name, archive_bytes=archive.stat().st_size,
            archive_sha256=sha256(archive), manifest_sha256=sha256(output / (u["run_id"] + "_manifest.json")))
    except BaseException as error:
        if result["status"] != "BLOCKED":
            result["status"] = "PARTIAL" if result["inference_started"] else "FAILED"
        receipt["error"] = error_report(error, "export")
        # A torn archive is retained and clearly marked, never called EXPORT_VALID.
        checksum = output / (u["run_id"] + "_sha256.json")
        partial_archive = output / (u["run_id"] + ".tar.gz")
        manifest = output / (u["run_id"] + "_manifest.json")
        if not checksum.exists():
            try:
                write(checksum, {"status": "EXPORT_FAILED_NOT_VALIDATED",
                    "archive_sha256": sha256(partial_archive) if partial_archive.exists() else None,
                    "manifest_sha256": sha256(manifest) if manifest.exists() else None})
            except (OSError, ValueError) as checksum_error:
                receipt["checksum_error"] = error_report(checksum_error, "partial_export_checksum")
    receipt["seconds"] = time.monotonic() - begin
    result["export"] = receipt
    write(output / (u["run_id"] + "_result.json"), result)
    receipt = {**receipt, "result_sha256": sha256(output / (u["run_id"] + "_result.json"))}
    write(output / (u["run_id"] + "_export.json"), receipt)
    write(output / (u["run_id"] + "_export_sha256.json"),
          {"sha256": sha256(output / (u["run_id"] + "_export.json"))})
    return result
