"""Independent pilot supervisor. Null authority blocks before data, setup or GPU."""
import json
from pathlib import Path
import shutil
import stat
import subprocess
import time

from safeshift.data.p2_execution import safe_path
from safeshift.pa3.native.journal import Journal, no_alias
from ..one_click.artifacts import package, sha256, write
from ..one_click.orchestrate import child_environment, host_conditions
from . import cohort, custody
from .contract import AUTHORITY, authorize, unit
from .resources import Sampler, projection, timed, tree_bytes


# Relative to a direct mount or datasets/<owner>/<slug>; never recurse.
TRAIN_LAYOUTS = ("", "InspecSafe-V1", "InspecSafe-V1-Kaggle/train")
MAX_DISCOVERY_ENTRIES = 512  # Total entries across input, owners and slugs.


class TrainInputError(ValueError):
    """Controlled, relative-path diagnostics safe to retain in pilot evidence."""
    def __init__(self, reason, **details):
        super().__init__(reason)
        self.details = {"reason": reason, **details}


def error_report(error, phase):
    report = {"type": type(error).__name__, "errno": getattr(error, "errno", None), "phase": phase}
    if isinstance(error, TrainInputError):
        report.update(error.details)
    return report


def discover_train(inputs=Path("/kaggle/input")):
    try:
        inputs = no_alias(inputs)
    except ValueError as error:
        raise TrainInputError("UNSAFE_TRAIN_DISCOVERY_PATH", path_relative_to_input=".",
                              safety_check=str(error)) from error
    candidates, visited = [], 0

    def checked(relative):
        try:
            return safe_path(inputs, relative)
        except ValueError as error:
            raise TrainInputError("UNSAFE_TRAIN_DISCOVERY_PATH", path_relative_to_input=relative,
                                  safety_check=str(error)) from error

    def directories(parent):
        nonlocal visited
        entries = []
        for entry in parent.iterdir():
            visited += 1
            if visited > MAX_DISCOVERY_ENTRIES:
                raise TrainInputError("TRAIN_DISCOVERY_ENTRY_LIMIT_EXCEEDED", limit=MAX_DISCOVERY_ENTRIES)
            relative = entry.relative_to(inputs).as_posix()
            # Check before is_dir: even a dangling symlink must fail closed.
            if checked(relative).is_dir():
                entries.append(entry)
        return sorted(entries)

    def inspect(mount):
        for relative in TRAIN_LAYOUTS:
            name = mount.relative_to(inputs).as_posix() + ("/" + relative if relative else "")
            p = checked(name)
            annotations = checked(name + "/DATA_PATH/train/Annotations")
            if annotations.is_dir():
                candidates.append(p)

    try:
        if inputs.is_dir():
            for mount in directories(inputs):
                inspect(mount)
                if mount.name == "datasets":
                    for owner in directories(mount):
                        for slug in directories(owner):
                            inspect(slug)
    except OSError as error:
        raise TrainInputError("TRAIN_DISCOVERY_METADATA_UNREADABLE", metadata_errno=error.errno) from error
    roots = [p.relative_to(inputs).as_posix() for p in candidates]
    if not candidates:
        raise TrainInputError("TRAIN_ROOT_NOT_FOUND", roots_relative_to_input=[])
    if len(candidates) > 1:
        raise TrainInputError("MULTIPLE_TRAIN_ROOTS", roots_relative_to_input=roots)
    return candidates[0]


def train_image(dataset, row):
    locator = row["image_locator"]
    if (not isinstance(locator, str) or not locator.startswith("DATA_PATH/train/Annotations/")
            or not locator.endswith(".jpg")):
        raise TrainInputError("TRAIN_JPEG_ONLY", image_locator=locator)
    try:
        source = safe_path(dataset, locator)
    except ValueError as error:
        raise TrainInputError("UNSAFE_TRAIN_IMAGE_PATH", image_locator=locator,
                              safety_check=str(error)) from error
    except OSError as error:
        raise TrainInputError("TRAIN_IMAGE_METADATA_UNREADABLE", image_locator=locator,
                              metadata_errno=error.errno) from error
    try:
        metadata = source.stat()
    except FileNotFoundError as error:
        raise TrainInputError("TRAIN_IMAGE_MISSING", image_locator=locator) from error
    except OSError as error:
        raise TrainInputError("TRAIN_IMAGE_METADATA_UNREADABLE", image_locator=locator,
                              metadata_errno=error.errno) from error
    if not stat.S_ISREG(metadata.st_mode):
        raise TrainInputError("TRAIN_IMAGE_NOT_REGULAR_FILE", image_locator=locator)
    if metadata.st_nlink != 1:
        raise TrainInputError("TRAIN_IMAGE_HARDLINK_ALIAS_FORBIDDEN", image_locator=locator,
                              expected_nlink=1, actual_nlink=metadata.st_nlink)
    return source


def check_images(dataset, rows):
    """Metadata only: all eight must exist before any image bytes are read."""
    cohort.validate_opaque(cohort.opaque_rows(rows))
    if len({r["image_locator"] for r in rows}) != 8:
        raise ValueError("EIGHT_DISTINCT_TRAIN_JPEGS_REQUIRED")
    for i, row in enumerate(rows):
        try:
            train_image(dataset, row)
        except TrainInputError as error:
            error.details["ordinal"] = i
            raise


def stage_images(dataset, rows, dest, receipt_root):
    dest = no_alias(dest)
    dest.mkdir(parents=True, exist_ok=False)
    j, i = Journal(receipt_root, create=True), None
    try:
        for i, row in enumerate(rows):
            start = time.monotonic()
            j.write(f"image-{i:06d}.read-start", {"ordinal": i, "exposure": "SUPERVISOR_IMAGE_READ_STARTED"})
            try:
                source = train_image(dataset, row)
                actual = sha256(source)
                j.write(f"image-{i:06d}.hash", {"expected": row["image_sha256"], "actual": actual})
                if actual != row["image_sha256"]:
                    raise TrainInputError("TRAIN_IMAGE_HASH_MISMATCH_NO_SKIP", ordinal=i,
                        image_locator=row["image_locator"], expected_sha256=row["image_sha256"], actual_sha256=actual)
                target = dest / f"{i:06d}.image"
                with source.open("rb") as reader, target.open("xb") as writer:
                    shutil.copyfileobj(reader, writer)
                copied = sha256(target)
                if copied != row["image_sha256"]:
                    raise TrainInputError("STAGED_COPY_HASH_MISMATCH", ordinal=i,
                        image_locator=row["image_locator"], expected_sha256=row["image_sha256"], actual_sha256=copied)
            finally:
                j.write(f"image-{i:06d}.timing", {"seconds": time.monotonic() - start})
        write(dest / "request.json", cohort.opaque_rows(rows))
        j.write("finish", {"count": 8})
    except BaseException as e:
        if isinstance(e, TrainInputError):
            e.details["ordinal"] = i
        j.write("failure", {"ordinal": i, "type": type(e).__name__, "error": error_report(e, "image_staging")})
        raise
    finally:
        j.seal()


class Operations:
    kaggle_inputs = Path("/kaggle/input")

    def __init__(self, repo, work, evidence, u):
        self.repo, self.work, self.evidence, self.u = repo, work, evidence, u
        self.cache = "data/processed/resource_pilot_cache/" + u["run_id"]
        self.inputs = repo / "data/processed/resource_pilot_inputs" / u["run_id"]

    def preflight(self):
        result = host_conditions(self.repo.parent)
        if shutil.disk_usage(self.work).free < 2 * 2**30:
            raise OSError("OUTPUT_FREE_BELOW_2_GIB")
        return result

    def check_inputs(self, rows):
        inputs = self.kaggle_inputs
        self.dataset = discover_train(inputs)
        check_images(self.dataset, rows)
        return {"dataset_root_relative_to_input": self.dataset.relative_to(inputs).as_posix(),
                "count": 8, "image_bytes_read": False, "labels_or_gt_read": False}

    def gpu_memory(self):
        from .resources import gpu_memory
        selected = {int(i) for i in self.u["cuda_visible_devices"].split(",")}
        return {i: v for i, v in gpu_memory().items() if i in selected}

    def software(self):
        from ..one_click.provision import build_environment
        self.python = build_environment(self.u["model"], self.repo,
            self.repo.parent / "runtime" / self.u["model"], self.evidence / "software")

    def provision(self):
        from ..one_click.provision import invoke
        env = child_environment(self.u["model"], self.repo, self.cache, offline=False, cpu=True)
        invoke([self.python, "-m", "safeshift.diagnostics.one_click.provision", "--model", self.u["model"],
            "--cache", self.cache, "--evidence", self.evidence / "checkpoint"], self.repo,
            self.evidence / "checkpoint.log", env=env)

    def worker(self, mode):
        env = child_environment(self.u["model"], self.repo, self.cache)
        command = [str(self.python), "-m", "safeshift.diagnostics.resource_pilot.worker", "--mode", mode,
            "--model", self.u["model"], "--cache", self.cache, "--evidence", str(self.evidence / mode),
            "--source", str(self.evidence / "source.json"), "--inputs", str(self.inputs),
            "--raw", str(self.evidence / "raw")]
        with (self.evidence / (mode + ".log")).open("xb") as log:
            proc = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, close_fds=True, timeout=3600)
        report = json.loads((self.evidence / mode / "result.json").read_bytes())
        if proc.returncode or report["status"] != "RETURNED":
            raise RuntimeError("WORKER_FAILED_NO_RETRY")
        return report

    def stage(self, rows):
        stage_images(self.dataset, rows, self.inputs, self.evidence / "input-staging")

    def audit(self):
        env = child_environment(self.u["model"], self.repo, self.cache, cpu=True)
        env.update(USE_TORCH="0", USE_TF="0", USE_FLAX="0")
        command = [str(self.python), "-m", "safeshift.diagnostics.resource_pilot.audit", "--root", str(self.evidence),
                   "--model", self.u["model"], "--cache", self.cache]
        with (self.work / "cpu-audit.log").open("xb") as log:
            proc = subprocess.run(command, cwd=self.repo, env=env, stdin=subprocess.DEVNULL,
                                  stdout=log, stderr=subprocess.STDOUT, close_fds=True, timeout=600)
        if proc.returncode not in (0, 2):
            raise RuntimeError("CPU_REPLAY_FAILED")
        return json.loads((self.work / "cpu-audit.json").read_bytes())


def accounting(evidence, rows):
    result = [{"ordinal": i, "status": "NOT_ATTEMPTED", "seconds": None} for i in range(8)]
    j = Journal(evidence / "raw/index")
    staging = Journal(evidence / "input-staging")
    if j.root.exists():
        for i in range(8):
            try:
                name = f"sample-{i:06d}"
                if j.exists(name + ".attempt"):
                    result[i]["status"] = "INTERRUPTED"
                if j.exists(name + ".timing"):
                    result[i].update(j.read(name + ".timing"))
                result[i]["native_call_start_recorded"] = j.exists(name + ".native-call")
            except (OSError, ValueError):
                result[i].update(status="INTERRUPTED", integrity="PARTIAL")
    if staging.root.exists():
        try:
            if staging.exists("failure"):
                f = staging.read("failure")
                result[f["ordinal"]].update(status="TECHNICAL_ERROR", stage="IMAGE_STAGING")
        except (OSError, ValueError, TypeError):
            pass
    for i, r in enumerate(result):
        if rows:
            r.update(sample_id=rows[i]["sample_id"], image_sha256=rows[i]["image_sha256"])
        r["staging_read_started"] = staging.root.exists() and (staging.root / f"image-{i:06d}.read-start.json").exists()
    return result


def run(repo, work, output, source, model, *, operations_factory=Operations, sampler_factory=Sampler):
    repo, work, output = Path(repo), Path(work), Path(output)
    evidence = work / "evidence"
    evidence.mkdir(parents=True, exist_ok=False)
    u, rows, sampler, ops = unit(model), None, None, None
    result = {"schema": "resource-pilot8-result-v1", "unit": u, "status": "BLOCKED",
        "full_vocab_replay": False, "labels_or_gt_read": False, "retry": False,
        "HNLO_RESEARCH_VERIFIED": False, "network_coverage": "PARTIAL_RELAY_UNOBSERVABLE"}
    phases, current_phase = {}, "authority"
    def phase(name, callback):
        nonlocal current_phase
        current_phase = name
        start = time.monotonic()
        try:
            return timed(evidence / (name + "-timing.json"), callback)
        finally:
            phases[name] = time.monotonic() - start
    try:
        authority = json.loads((repo / AUTHORITY).read_bytes())
        authorize(authority, source, model)
        current_phase = "attempt_consumption"
        ledger = no_alias(output / "data/processed/resource_pilot_attempts" / u["attempt_id"])
        ledger.mkdir(parents=True, exist_ok=False)
        write(ledger / "consumed.json", {"unit": u, "source": source})
        result["status"] = "FAILED"
        current_phase = "manifest_binding"
        rows = cohort.planned(repo)
        write(evidence / "binding.json", {"unit": u, "source": source, "authority": authority, "samples": rows})
        write(evidence / "source.json", source)
        ops = operations_factory(repo, work, evidence, u)
        write(evidence / "train-preflight.json", phase("train_preflight", lambda: ops.check_inputs(rows)))
        write(evidence / "host.json", phase("preflight", ops.preflight))
        sampler = sampler_factory({"scratch": repo.parent, "output": output}, observe_gpu=ops.gpu_memory)
        sampler.start()
        # Hash/read/copy uses the existing exposure journal and consumed attempt.
        # Fail before installing software or downloading any checkpoint.
        phase("image_staging", lambda: ops.stage(rows))
        phase("environment_setup", ops.software)
        phase("guarded_cuda_admission", lambda: ops.worker("inspect"))
        phase("checkpoint_provision", ops.provision)
        phase("inference_worker", lambda: ops.worker("inference"))
        result["status"] = "RAW_RETURNED"
    except BaseException as e:
        result["error"] = error_report(e, current_phase)
        if current_phase == "train_preflight" and not (evidence / "train-preflight.json").exists():
            write(evidence / "train-preflight.json", {"status": "FAILED", "error": result["error"],
                  "image_bytes_read": False, "labels_or_gt_read": False})
    result["phases_seconds"] = phases
    result["samples"] = accounting(evidence, rows)
    write(evidence / "supervisor.json", result)
    try:
        custody.seal(evidence)
        if rows and ops and (evidence / "raw").exists():
            audit = timed(work / "cpu-audit-timing.json", ops.audit)
            result["status"] = audit["status"] if "error" not in result else "PARTIAL"
            result["cpu_replay"] = audit
    except BaseException as e:
        result.update(cpu_replay="FAILED", cpu_replay_error=type(e).__name__)
        if result["status"] == "RAW_RETURNED":
            result["status"] = "PARTIAL"
    if result["status"] == "RAW_RETURNED":
        result["status"] = "PARTIAL"
    load_time = evidence / "raw/model-load-timing.json"
    load_seconds = json.loads(load_time.read_bytes())["seconds"] if load_time.exists() else 0
    result["projection"] = projection(result["samples"], load_seconds + sum(v for k, v in phases.items() if k not in ("inference_worker", "image_staging")))
    result["projection"]["cpu_audit_status"] = result.get("cpu_replay", "NOT_RUN") if isinstance(result.get("cpu_replay"), str) else result.get("cpu_replay", {}).get("status", "NOT_RUN")
    result["journal_bytes"] = tree_bytes(evidence / "raw") if (evidence / "raw").exists() else 0
    write(work / "result.json", result)
    # Raw custody stays immutable. Outer CPU reports/results join it only at export.
    begin = time.monotonic()
    bundle = work / "bundle"
    bundle.mkdir()
    shutil.copytree(evidence, bundle / "raw-evidence")
    for p in work.iterdir():
        if p.is_file():
            shutil.copyfile(p, bundle / p.name)
    stem = u["run_id"] + "-" + work.name
    export = {"status": "FAILED", "full_vocab_replay": False}
    try:
        archive = package(bundle, output, stem)
        export.update(status="EXPORTED", archive_bytes=archive.stat().st_size)
    except BaseException as e:
        result["status"] = "PARTIAL" if rows else "BLOCKED"
        export["error"] = type(e).__name__
    finally:
        export["seconds"] = time.monotonic() - begin
        export["resources"] = sampler.finish() if sampler else {"coverage": "NOT_STARTED"}
        export["bundle_bytes"] = tree_bytes(bundle)
        audit_time = work / "cpu-audit-timing.json"
        cpu_seconds = json.loads(audit_time.read_bytes())["seconds"] if audit_time.exists() else 0
        base = result["projection"]["estimate_941_seconds"]
        export["illustrative_941_end_to_end_seconds"] = (base + 941 / 8 * (phases.get("image_staging", 0) + cpu_seconds + export["seconds"])) if base is not None else None
        export["projection_limit"] = "Linear staging/CPU/export scaling, including model load and setup; archive compression and disk growth may be nonlinear. Not a feasibility guarantee."
        write(output / (stem + "_export.json"), export)
        write(output / (stem + "_export_sha256.json"), {"sha256": sha256(output / (stem + "_export.json"))})
    result["export"] = export
    return result
