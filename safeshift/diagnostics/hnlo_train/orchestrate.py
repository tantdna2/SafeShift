"""One-click one-model/one-shard unit, never resumes or retries failed samples."""
import json
from pathlib import Path
import shutil
import subprocess

from safeshift.data.p2_execution import safe_path
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


def discover_train(inputs=Path("/kaggle/input")):
    """Inspect directory names only; no dataset image, TEST or annotation scan."""
    candidates = []
    for mount in Path(inputs).iterdir():
        for relative in ("", "InspecSafe-V1"):
            candidate = mount / relative
            if (candidate / "DATA_PATH/train/Annotations").is_dir():
                candidates.append(candidate)
    unique = {str(no_alias(p)): p for p in candidates}
    if len(unique) != 1:
        raise ValueError("EXACTLY_ONE_UNPACKED_APPROVED_TRAIN_MOUNT_REQUIRED")
    return next(iter(unique.values()))


def stage_images(dataset, rows, dest, receipt_root=None):
    """Parent only: exact authorized TRAIN paths, images only, byte-identical copies."""
    dest = no_alias(dest)
    dest.mkdir(parents=True, exist_ok=False)
    journal = Journal(receipt_root, create=True) if receipt_root else None
    i = None
    try:
        for i, row in enumerate(rows):
            locator = row["image_locator"]
            if not locator.startswith("DATA_PATH/train/Annotations/") or not locator.endswith(".jpg"):
                raise PermissionError("ORIGINAL_TRAIN_IMAGE_ONLY")
            source = no_alias(safe_path(dataset, locator))
            actual = sha256(source)
            if journal:
                journal.write(f"image-{i:06d}", {"ordinal": i, "expected": row["image_sha256"], "actual": actual})
            if actual != row["image_sha256"]:
                raise ValueError("TRAIN_IMAGE_HASH_MISMATCH_NO_SKIP")
            target = dest / f"{i:06d}.image"
            with source.open("rb") as reader, target.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
            if sha256(target) != row["image_sha256"]:
                raise ValueError("STAGED_COPY_CHECKSUM_MISMATCH")
        write(dest / "request.json", cohort.opaque_rows(rows))
        if journal:
            journal.write("finish", {"count": len(rows)})
    except BaseException as error:
        if journal:
            journal.write("failure", {"ordinal": i, "type": type(error).__name__})
        raise
    finally:
        if journal:
            journal.seal()


class Operations:
    def __init__(self, repo, work, evidence, source_path, u):
        self.repo, self.work, self.evidence = Path(repo), Path(work), Path(evidence)
        self.source_path, self.u = Path(source_path), u
        self.cache = "data/processed/hnlo_train_cache/" + u["run_id"]
        self.inputs = self.repo / "data/processed/hnlo_train_inputs" / u["run_id"]

    def preflight(self):
        result = host_conditions(self.repo.parent)
        if shutil.disk_usage(self.work).free < 6 * 2**30:
            raise RuntimeError("OUTPUT_DISK_FREE_BELOW_6_GIB")
        return result

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
                                  stdout=stream, stderr=subprocess.STDOUT, close_fds=True)
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
        stage_images(discover_train(), rows, self.inputs, self.evidence / "input-staging")

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
    operations, bound, rows = None, False, None
    try:
        authority = json.loads((repo / AUTHORITY).read_bytes())
        authorize(authority, source, model, shard)  # before cohort/dataset discovery/build/GPU
        # The Lead/Owner must also enforce single use across fresh Kaggle sessions.
        ledger = no_alias(output / "data/processed/hnlo_train_attempts" / u["run_id"])
        ledger.mkdir(parents=True, exist_ok=False)
        write(ledger / "consumed.json", {"unit": u, "source": source["merge_commit"]})
        rows = cohort.inference(repo)[shard]
        write(evidence / "binding.json", {"unit": u, "samples": rows, "source": source, "authority": authority})
        write(evidence / "source.json", source)
        bound = True
        operations = operations_factory(repo, work, evidence, evidence / "source.json", u)
        write(evidence / "host.json", operations.preflight())
        result["provisioning_started"] = True
        operations.software()
        result["gpu_worker_started"] = True
        operations.worker("inspect")  # guarded CUDA admission, no weights or data
        operations.provision()
        result["dataset_read"] = True
        operations.stage(rows)
        result["inference_started"] = True
        operations.worker("inference")
        result["status"] = "RAW_RETURNED"
    except BaseException as error:
        result.update(status="STOPPED" if bound else "BLOCKED", error={"type": type(error).__name__,
                      "errno": getattr(error, "errno", None)})
    finally:
        write(evidence / "supervisor.json", result)
        seal_raw(evidence)  # includes torn/interrupted bytes; never fabricates worker success
    if bound and operations is not None:
        try:
            evaluation = operations.evaluate()  # label permission checked again on CPU
            result["status"] = "COMPLETE" if evaluation["completed"] else "PARTIAL"
            result["metrics"] = evaluation
            result["coverage"] = evaluation["overall"]["coverage"]
            report = evidence / "report/audit.json"
            if report.exists():
                audited = json.loads(report.read_bytes())["results"]
                result["sample_journal"] = [{k: r[k] for k in
                    ("sample_id", "status", "attempted", "persisted", "parsed", "errors")} for r in audited]
        except BaseException as error:
            result.update(cpu_audit="FAILED", cpu_audit_error={"type": type(error).__name__})
            if result["inference_started"]:
                result["coverage"] = {"planned": u["count"], "scored": 0, "coverage": 0.0,
                                      "reason": "CPU_AUDIT_REQUIRED_RAW_PRESERVED"}
    if bound and "sample_journal" not in result:
        result["sample_journal"] = execution_inventory(evidence, rows)
        result["coverage"]["status_counts"] = {s: sum(r["status"] == s for r in result["sample_journal"]) for s in
            ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "NOT_ATTEMPTED")}
    audit_log = work / "cpu-audit.log"
    if audit_log.exists():
        with audit_log.open("rb") as reader, (evidence / "cpu-audit.log").open("xb") as writer:
            shutil.copyfileobj(reader, writer)
    write(evidence / "result.json", result)
    write(output / (u["run_id"] + "_result.json"), result)
    package(evidence, output, u["run_id"])
    return result
