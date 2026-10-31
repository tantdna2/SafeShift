"""Candidate160 stdlib supervisor and separately invoked pinned worker.

No downloader for weights, alternate adapter or FULL TRAIN.
Official checkpoint/source must be attached offline; exact hashes precede load.
"""
import argparse
import importlib.metadata as metadata
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid
import shutil

from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import export, read, safe, sha, write, write_bytes
from safeshift.pilot.contract import digest, PROMPT_SHA
from .train_inputs import discover, checkpoint
from safeshift.pilot.runner import error_record
from .source import ROOT, LOCK, require, stage_snapshot
from .loading import verify_weights
from .train_contract import KEYS, MANIFEST, authorize, config, configuration_hashes, manifest, model, source_hash, sources
from .train_run import recover, run_calls, lineage_accounting
from . import train_owner as owner
from . import train_history as history
from . import train_smoke as smoke


def worker_command(python, repo, output, bundle, snapshot, weights, source, ref, *, execution=None, grant=None, ledger=None):
    """One OS argument boundary for supervisor and real CPU CLI regression."""
    command = [str(python), "-B", "-m", "safeshift.candidates.train_runtime"]
    for name, value in (("repo", repo), ("output", output), ("bundle", bundle),
                        ("snapshot", snapshot), ("weights", weights), ("source", source), ("ref", ref)):
        command += ["--" + name, str(value)]
    require((execution is not None) != (grant is not None), "ONE_WORKER_AUTHORITY_REQUIRED")
    if execution is not None:
        require(ledger is None, "EXECUTION_HAS_NO_EXTERNAL_LEDGER")
        command += ["--execution", str(execution)]
    else:
        require(ledger is not None, "LEGACY_LEDGER_REQUIRED")
        command += ["--grant", str(grant), "--ledger", str(ledger)]
    return command


def pins(key):
    expected = {}
    for line in (ROOT / f"configs/candidate160/{key}.requirements.txt").read_text().splitlines():
        if line and not line.startswith("#"):
            name, version = line.split("==")
            require(name not in expected, "DUPLICATE_DEPENDENCY_PIN")
            expected[name] = version
    return expected


def software(key, *, identity=True):
    if identity:
        identity_receipt = boot.runtime_identity(os.environ["SAFESHIFT_WORKER_PYTHON"],
                                                 os.environ["SAFESHIFT_RUNTIME_ROOT"])
        require(platform.python_version() == "3.11.9", "PINNED_PYTHON_3119_REQUIRED")
    else:
        identity_receipt = {"scope": "CPU_TEST_DOUBLE"}
    expected = pins(key)
    observed = {name: metadata.version(name) for name in expected}
    require(observed == expected, "PINNED_DEPENDENCY_MISMATCH")
    normalize = lambda name: name.lower().replace("_", "-").replace(".", "-")
    installed = {normalize(d.metadata["Name"]): d.version for d in metadata.distributions()}
    require(installed == {normalize(n): v for n, v in expected.items()}, "UNLOCKED_INSTALLED_DEPENDENCY")
    import torch
    import torchvision
    import transformers
    from torchvision.ops import nms
    require(torch.version.cuda == "12.4", "PINNED_CUDA_BUILD_REQUIRED")
    for module in (torch, torchvision, transformers):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), "FOREIGN_LIBRARY")
    require(nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), .5).tolist() == [0], "COMPILED_NMS_ABI")
    return {"identity": identity_receipt, "versions": observed, "cuda_build": torch.version.cuda,
            "compiled_cpu_nms": "PASS", "gpu": "NOT_CALLED"}


def hardware(policy):
    receipt = boot.gpu_preflight()
    for i, row in enumerate(receipt["physical_gpus"]):
        # CUDA 12.x minor-version compatibility floor, not a guarantee of kernel support.
        require(tuple(map(int, row[3].split("."))) >= (525, 60, 13), "CUDA12_LINUX_DRIVER_TOO_OLD")
        if policy.get("review_mode") != owner.MODE:
            require(row[3] in policy["driver_versions"], "UNAPPROVED_NVIDIA_DRIVER")
        require(int(row[2]) >= policy["free_mib_per_gpu"][i], "PER_GPU_FREE_MEMORY")
    return receipt


def resources(policy, scratch, output, *, gpu=False):
    """Observe live RAM/cgroup, scratch and output separately; no pooled VRAM."""
    import psutil
    ram = psutil.virtual_memory().available
    limits = []
    # Kaggle containers can have a lower limit than host psutil reports.
    for limit, used in (("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current"),
                        ("/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes")):
        path = Path(limit)
        if path.is_file():
            text = path.read_text().strip()
            if text != "max":
                remaining = max(0, int(text) - int(Path(used).read_text()))
                limits.append(remaining)
                ram = min(ram, remaining)
    observed = {"free_ram_mib": ram // 2**20, "free_scratch_mib": shutil.disk_usage(scratch).free // 2**20,
                "free_output_mib": shutil.disk_usage(output).free // 2**20, "cgroup_remaining_bytes": limits}
    for name in ("free_ram_mib", "free_scratch_mib", "free_output_mib"):
        require(observed[name] >= policy[name], f"LIVE_RESOURCE_LIMIT:{name}:{observed[name]}<{policy[name]}")
    if gpu:
        import torch
        observed["free_gpu0_runtime_mib"] = torch.cuda.mem_get_info(0)[0] // 2**20
        require(observed["free_gpu0_runtime_mib"] >= policy["free_gpu0_runtime_mib"], "LIVE_RESOURCE_LIMIT:gpu0")
    return observed


def worker_cuda(policy):
    """Runs in the actual isolated child before checkpoint deserialization."""
    receipt = hardware(policy)
    import torch
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1
            and torch.cuda.get_device_capability(0) == (7, 5), "ISOLATED_SINGLE_VISIBLE_T4_REQUIRED")
    require(torch.version.cuda == "12.4", "WORKER_CUDA_BUILD")
    free, total = torch.cuda.mem_get_info(0)
    require(free >= policy["free_mib_per_gpu"][0] * 2**20, "WORKER_GPU0_FREE_MEMORY")
    test = torch.ones(1, device="cuda:0", dtype=torch.float16)
    require(float(test.sum().item()) == 1.0, "WORKER_CUDA_FP16_FUNCTIONAL_FAILURE")
    del test
    torch.cuda.synchronize(0)
    receipt.update(worker_cuda="MEASURED_FP16_FUNCTIONAL", worker_visible_gpus=1,
                   worker_free_bytes=free, worker_total_bytes=total, worker_device=torch.cuda.get_device_name(0))
    return receipt


def memory(reset):
    import torch
    if reset:
        torch.cuda.reset_peak_memory_stats(0)
    free, total = torch.cuda.mem_get_info(0)
    return {"gpu0_free": free, "gpu0_total": total, "gpu0_allocated": torch.cuda.memory_allocated(0),
            "gpu0_reserved": torch.cuda.memory_reserved(0),
            "gpu0_peak_allocated": torch.cuda.max_memory_allocated(0),
            "gpu0_peak_reserved": torch.cuda.max_memory_reserved(0), "gpu1_inference": "UNUSED"}


def verify_images(bundle, rows):
    from PIL import Image
    for row in rows:
        path = safe(bundle, row["image"])
        require(sha(path) == row["image_sha256"], "IMAGE_HASH")
        with Image.open(path) as image:
            require(image.size == (row["width"], row["height"]) and getattr(image, "n_frames", 1) == 1,
                    "IMAGE_DIMENSIONS_OR_FRAMES")
            image.load()
            with image.convert("RGB") as rgb:
                require(rgb.mode == "RGB", "RGB_CONVERSION")
    return {"verified_images": len(rows), "method": "SHA256+native_PIL_decode+RGB; no image rewritten"}


def worker(repo, output, bundle, snapshot, weights, grant, ledger, source, ref, *, check_only=False, cuda_check_only=False):
    repo, output, bundle, snapshot, weights = map(Path, (repo, output, bundle, snapshot, weights))
    require(not (check_only and cuda_check_only), "ONE_WORKER_CHECK_MODE_REQUIRED")
    authorize(grant, grant["model_key"], source, ref, ledger)
    require(source_hash(repo) == source, "WORKER_SOURCE_CHANGED")
    if cuda_check_only:
        # Authorized GPU probe but no native calls, weights, manifest or consumption.
        write(output / "preledger_cuda_software.json", software(grant["model_key"]))
        write(output / "preledger_cuda.json", worker_cuda(grant["policy"]))
        return
    if not check_only:
        require(read(output / "consumption.json") == {"attempt_consumed": True, "attempt_id": grant["attempt_id"]},
                "SUPERVISOR_CONSUMPTION_REQUIRED_BEFORE_GPU")
    write(output / ("software_cpu.json" if check_only else "worker_software.json"), software(grant["model_key"]))
    write(output / ("resources_cpu.json" if check_only else "worker_resources.json"),
          resources(grant["policy"], os.environ["SAFESHIFT_RUNTIME_ROOT"], output))
    plan, rows = manifest(bundle)
    write(output / ("images_cpu.json" if check_only else "worker_images.json"), verify_images(bundle, rows))
    prompt = (repo / "configs/pilot/classification_c1.txt").read_bytes()
    require(sha(repo / "configs/pilot/classification_c1.txt") == PROMPT_SHA, "C1_HASH")
    if check_only:
        # Real production source/native processor/meta loader, no weights/forward/CUDA.
        from .train_preflight import native_cpu
        write(output / "native_cpu.json", native_cpu(grant["model_key"], snapshot, repo,
            implementation=grant.get("effective_implementation")))
        return
    write(output / "worker_hardware_observation.json", hardware(grant["policy"]))
    write(output / "worker_cuda.json", worker_cuda(grant["policy"]))
    # Repeat all checks inside the actual process after isolation/consumption.
    from .backend import CandidateBackend
    write(output / "worker_source.json", {"source_sha256": source, "runtime_ref": ref,
                                         "model": model(grant["model_key"])})
    execution = [{**row, "image": str(safe(bundle, row["image"]))} for row in rows]
    def factory():
        if "effective_implementation" in grant:
            from .minicpm_resampler_fp32 import backend
            return backend(grant["model_key"], snapshot, weights, prompt.decode(), device="cuda:0")
        return CandidateBackend(grant["model_key"], snapshot, weights, prompt.decode(), device="cuda:0")
    run_calls(output, plan, execution, factory,
              grant, memory=memory, reviews=os.environ["SAFESHIFT_REVIEW_DIRECTORY"],
              resources=lambda: resources(grant["policy"], os.environ["SAFESHIFT_RUNTIME_ROOT"], output, gpu=True),
              deadline=float(os.environ["SAFESHIFT_DEADLINE_MONOTONIC"]))


def prepare_runtime(repo, key, scratch, output, env, deadline):
    """Reuse reviewed interpreter/venv/pip primitives; candidate-specific pins."""
    candidates = []
    observations = []
    paths = boot.interpreter_candidates() + [Path("/usr/local/bin/python3.11"), Path("/opt/conda/bin/python3.11")]
    located = shutil.which("python3.11")
    if located:
        paths.append(Path(located))
    for candidate in dict.fromkeys(paths):
        value = boot.probe_interpreter(candidate, env)
        observations.append(value)
        if value.get("eligible") and value.get("version", [])[:3] == [3, 11, 9]:
            candidates.append(candidate)
    write(output / "interpreters.json", observations)
    if not candidates:
        from .train_python import provision
        candidates.append(provision(repo, scratch, output, env, deadline))
    runtime = scratch / "venv3119"
    python = runtime / "bin/python"
    def call(command, log):
        remaining = deadline - time.monotonic()
        require(remaining > 0, "TIME_CAP_DURING_RUNTIME_SETUP")
        subprocess.run(list(map(str, command)), env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=remaining)
    with (output / "setup.log").open("xb") as log:
        call([candidates[0], "-I", "-B", "-m", "venv", "--without-pip", "--copies", runtime], log)
        # PBS uses $ORIGIN/../lib for libpython. A copied venv executable
        # therefore needs the same verified library in its own lib directory.
        # Keep copies and library isolation; do not add a global LD_LIBRARY_PATH.
        library = Path(candidates[0]).parent.parent / "lib/libpython3.11.so.1.0"
        if library.is_file():
            require(not library.is_symlink(), "PYTHON_RUNTIME_LIBRARY_ALIAS")
            destination = runtime / "lib/libpython3.11.so.1.0"
            require(not destination.exists(), "PYTHON_RUNTIME_LIBRARY_ALREADY_EXISTS")
            shutil.copyfile(library, destination)
            require(sha(destination) == sha(library), "PYTHON_RUNTIME_LIBRARY_COPY_HASH")
            write(output / "python_venv_library.json", {"sha256": sha(destination),
                  "method": "verified libpython copied for PBS executable ORIGIN; no loader environment change"})
        venv_probe = boot.probe_interpreter(python, env)
        write(output / "venv_interpreter.json", venv_probe)
        require(venv_probe.get("eligible") and venv_probe.get("version") == [3, 11, 9]
                and Path(venv_probe["prefix"]).resolve() == runtime.resolve(), "ISOLATED_VENV_PROBE_FAILED")
        write(output / "pip_controller.json", boot.pip_controller_probe(env))
        wheel, receipt = boot.fetch_pip_bootstrap(repo, scratch)
        write(output / "pip_bootstrap.json", receipt)
        call(boot.pip_bootstrap_command(python, repo, wheel), log)
        write(output / "worker_pip.json", boot.inspect_worker_pip(python, runtime, "25.0.1", env))
        pip = [python, "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check"]
        call(pip + ["install", "--no-deps", "--no-cache-dir", "--index-url", "https://download.pytorch.org/whl/cu124",
                    "torch==2.6.0+cu124", "torchvision==0.21.0+cu124"], log)
        call(pip + ["install", "--no-deps", "--no-cache-dir", "-r", repo / f"configs/candidate160/{key}.requirements.txt"], log)
        call(pip + ["check"], log)
        log.flush()
        os.fsync(log.fileno())
    freeze = subprocess.check_output(list(map(str, pip + ["freeze", "--all"])), env=env,
                                     timeout=max(1, deadline-time.monotonic()))
    write_bytes(output / "freeze.txt", freeze)
    env.update(PYTHONPATH=str(repo), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
               SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(runtime),
               SAFESHIFT_NOTEBOOK_PYTHON=str(Path(sys.executable).resolve()),
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="",
               TOKENIZERS_PARALLELISM="false", HF_HUB_DISABLE_TELEMETRY="1")
    return python, env


def launch(key, source, repo, ref, *, inputs=None, work=None, scratch_root=None, owner_start=False,
           recovery_action=None, child_options=None, technical_smoke=False, implementation=None, qualification=False):
    """Owner activation or legacy authority precedes inputs and hardware reads."""
    require(key in KEYS, "CANDIDATE_KEY")
    require(type(owner_start) is bool, "EXPLICIT_OWNER_ACTIVATION_BOOLEAN")
    require(type(qualification) is bool and (not qualification or (owner_start and recovery_action is not None)),
            "QUALIFICATION_OWNER_RECOVERY_REQUIRED")
    require(type(technical_smoke) is bool and (not technical_smoke or
            (owner_start and recovery_action is None)), "ISOLATED_TECHNICAL_SMOKE_REQUIRED")
    require(implementation is None or ((technical_smoke or recovery_action is not None) and key == "minicpm4"),
            "EFFECTIVE_IMPLEMENTATION_TECHNICAL_ONLY")
    if implementation and not technical_smoke:
        from .train_route import configuration_admission
        configuration_admission(key, implementation, qualification)
    inputs = Path(inputs or "/kaggle/input")
    work = Path(work or Path.cwd() / "data/processed/candidate160")
    work.mkdir(parents=True, exist_ok=True)
    output = safe(work, key + "-" + uuid.uuid4().hex)
    output.mkdir(exist_ok=False)
    consumed, grant, plan, rows, scratch = False, None, None, [], None
    slot_name, slot_record, owns_slot = None, None, False
    stage, reason = "authority", None
    started = time.monotonic()
    try:
        require(source_hash(repo) == source, "NOTEBOOK_RUNTIME_SOURCE_MISMATCH")
        if technical_smoke:
            grant = smoke.execution(key, source, ref, implementation=implementation)
            ledger, ledger_file = None, None
            grant_file = output / "technical_execution.json"
            write(grant_file, grant)
        elif owner_start is True:
            index = history.collect(work, inputs, output, key, implementation=implementation,
                                    qualification=qualification) if recovery_action is not None else None
            grant = (history.execution(key, source, ref, index, action=recovery_action, owner_start=True,
                                      implementation=implementation, qualification=qualification)
                     if index is not None else owner.execution(key, source, ref, owner_start=True))
            ledger = None
            authorize(grant, key, source, ref, ledger)
            # A deterministic slot, not the new random run ID, excludes duplicates.
            if index is None:
                slot_name, slot_record = owner.reserve(work, grant, inputs)
            else:
                slot_name = "owner_slot_" + grant["slot_sha256"] + "." + grant["run_id"] + ".json"
                slot_record = {"schema": "safeshift-candidate160-owner-slot-v2", "status": "ATTEMPT_RESERVED",
                    "slot_sha256": grant["slot_sha256"], "execution_sha256": digest(grant),
                    "run_id": grant["run_id"], "attempt_id": grant["attempt_id"], "model_key": key,
                    "manifest_sha256": MANIFEST, "history_sha256": grant["history_sha256"]}
                write(safe(work, "attempts/" + slot_name), slot_record)
            owns_slot = True
            write(output / slot_name, slot_record)
            grant_file, ledger_file = output / "owner_execution.json", None
            write(grant_file, grant)
        else:
            grant_file = discover(inputs, f"grant_candidate160_{key}.json")
            grant = read(grant_file)
            ledger_file = discover(inputs, f"ledger_candidate160_{key}.json")
            ledger = read(ledger_file)
        authorize(grant, key, source, ref, ledger)
        deadline = min(started + grant["max_seconds"], time.monotonic() + grant["expires_unix"] - time.time())
        write(output / "authorization_binding.json", {"execution_sha256" if owner_start else "grant_sha256": digest(grant),
              "runtime_ref": ref, "source_sha256": source, "manifest_sha256": MANIFEST,
              **configuration_hashes(key, implementation=implementation),
              **({"official_numerical_approval": grant["official_numerical_approval"]}
                 if "official_numerical_approval" in grant else {}),
              **({"owner_decision_record": grant["owner_decision_record"], "activation": grant["activation"]} if owner_start else
                 {"ledger_sha256": digest(ledger),
                  "approval_refs": {n: grant[n] for n in ("G0", "T0", "O3", "research_lead_review_ref")}})})
        if not owner_start:
            write(output / "grant.json", grant)
            write(output / "ledger_reservation.json", ledger)
        write(output / "release_config.json", config(key, implementation=implementation))
        write(output / "dependency_pins.json", pins(key))
        write(output / "source_inventory.json", {p: sha(Path(repo)/p) for p in sources(repo)})
        # Local marker supplements, and cannot replace, the external ledger.
        attempts = work / "attempts"
        attempts.mkdir(exist_ok=True)
        if not owner_start:
            reservation = safe(attempts, grant["attempt_id"] + ".reserved.json")
            write(reservation, {"grant_sha256": digest(grant), "external_ledger_ref": grant["external_ledger_ref"]})
        stage = "manifest"
        bundle = discover(inputs, "pilot_manifest.json").parent
        plan, rows = manifest(bundle)
        write(output / "pilot_manifest.json", plan)
        if qualification:
            from .train_route import selection
            write(output / "technical_selection.json", selection(rows))
        if technical_smoke:
            write(output / "technical_selection.json", smoke.selection(rows, grant))
        if recovery_action is not None:
            recovery = history.recovery_plan(output, rows, grant)
            write(output / "recovery_plan.json", recovery)
            # A complete lineage is a no-op under resume: no software/GPU/load.
            if not recovery["pending_ordinals"]:
                stage = "already_durable_no_work"
                return output
        stage = "checkpoint_source"
        marker, source_dir, weights = checkpoint(inputs, key)
        write(output / "checkpoint_admission.json", verify_weights(weights, key))
        scratch_root = boot.provision_scratch_root(Path.cwd(), scratch_root or "/kaggle/tmp")
        scratch, env = boot.prepare_scratch(scratch_root, output.name)
        snapshot = scratch / model(key)["revision"]
        write(output / "public_source_admission.json", stage_snapshot(source_dir, snapshot, key))
        stage = "storage"
        receipt = boot.storage_admission(scratch, output)
        write(output / "storage.json", receipt)
        require(receipt["admitted"], "INSUFFICIENT_PHYSICAL_STORAGE")
        stage = "software"
        python, env = prepare_runtime(Path(repo), key, scratch, output, env, deadline)
        review_dir = safe(work, "reviews/" + grant["attempt_id"])
        review_dir.mkdir(parents=True, exist_ok=False)
        env.update(SAFESHIFT_REVIEW_DIRECTORY=str(review_dir), SAFESHIFT_DEADLINE_MONOTONIC=str(deadline))
        command = worker_command(python, repo, output, bundle, snapshot, weights, source, ref,
            execution=grant_file if owner_start else None, grant=None if owner_start else grant_file, ledger=ledger_file)
        stage = "cpu_native_and_images"
        with (output / "cpu.log").open("xb") as log:
            subprocess.run(command + ["--check-only"], env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=max(1, deadline-time.monotonic()), **(child_options or {}))
        stage = "gpu_preledger"
        write(output / "hardware_preledger.json", hardware(grant["policy"]))
        stage = "cuda_child_preledger"
        with (output / "cuda_preledger.log").open("xb") as log:
            subprocess.run(command + ["--cuda-check-only"], env={**env, "CUDA_VISIBLE_DEVICES": "0"},
                           stdout=log, stderr=subprocess.STDOUT, check=True,
                           timeout=max(1, deadline-time.monotonic()), **(child_options or {}))
        require(read(output / "preledger_cuda.json")["worker_cuda"] == "MEASURED_FP16_FUNCTIONAL",
                "PRELEDGER_CUDA_RECEIPT_REQUIRED")
        # Check expiry/source/ledger/input hashes again immediately before consume.
        require(read(grant_file) == grant and (ledger_file is None or read(ledger_file) == ledger), "AUTHORITY_CHANGED")
        authorize(grant, key, source, ref, ledger)
        if owner_start and not technical_smoke:
            require(read(safe(attempts, slot_name)) == slot_record
                    and read(output / slot_name) == slot_record, "OWNER_SLOT_CUSTODY_CHANGED")
        require(source_hash(repo) == source and manifest(bundle)[0] == plan, "PRELEDGER_SOURCE_CHANGED")
        require(time.monotonic() < deadline, "TIME_CAP_PRELEDGER")
        consumed = None  # A failed exclusive create/fsync is never asserted unconsumed.
        consumption_record = {"run_id": grant["run_id"],
              "attempt_id": grant["attempt_id"], "source_sha256": source,
              "execution_sha256" if owner_start else "grant_sha256": digest(grant),
              **({"slot_sha256": grant["slot_sha256"]} if owner_start else {"external_ledger_ref": grant["external_ledger_ref"]}),
              "attempt_consumed": True}
        if technical_smoke:
            write(output / "technical_consumption.json", consumption_record)
        else:
            write(safe(attempts, (slot_name.removesuffix(".json") if owner_start else grant["attempt_id"]) + ".consumed.json"), consumption_record)
        consumed = True
        write(output / "consumption.json", {"attempt_consumed": True, "attempt_id": grant["attempt_id"]})
        stage = "worker"
        env["CUDA_VISIBLE_DEVICES"] = "0"
        print("Owner execution (no review file required):" if owner_start else "Research Lead review drop directory:",
              grant["run_id"] if owner_start else review_dir, flush=True)
        with (output / "worker.log").open("xb") as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=max(1, deadline-time.monotonic()), **(child_options or {}))
    except BaseException as error:
        reason = error_record(error, stage)
        try:
            write(output / "supervisor_failure.json", reason)
            if hasattr(error, "gpu_preflight_receipt"):
                write(output / "hardware_failure.json", error.gpu_preflight_receipt)
        except BaseException as failure:
            print("Failure receipt unavailable; retain directory:", output, type(failure).__name__, flush=True)
    finally:
        finalizer_errors = []
        def retain(name, value):
            try:
                write(output / name, value)
            except BaseException as error:
                finalizer_errors.append(error_record(error, "finalize_" + name))
                print("Finalizer write failed:", name, type(error).__name__, flush=True)
        if rows:
            try:
                results = recover(output, rows, grant)
                retain("supervisor_accounting.json", [{"ordinal": i, "sample_id": r["sample_id"], **results[r["sample_id"]]}
                                                      for i, r in enumerate(rows)])
                if recovery_action is not None and (output / "recovery_plan.json").is_file() and not (output / "lineage_accounting.json").exists():
                    retain("lineage_accounting.json", lineage_accounting(read(output / "recovery_plan.json"), rows, results, grant))
            except BaseException as error:
                finalizer_errors.append(error_record(error, "supervisor_recovery"))
        retain("supervisor_status.json", {"status": ("ALREADY_DURABLE_NO_WORK" if stage == "already_durable_no_work" else "BLOCKED" if consumed is False else
               "CONSUMPTION_UNCERTAIN_DO_NOT_RETRY" if consumed is None else "CONSUMED_REVIEW_EVIDENCE"),
              "attempt_consumed": consumed, "stage": stage, "failure": reason,
              "cpu_checks": "SEE_CPU_RECEIPTS", "gpu": "UNVERIFIED_UNLESS_MEASURED_WORKER_RECEIPT",
              "classification_quality": "UNVERIFIED_PENDING_RESULT_REVIEW", "source_sha256": source,
              "runtime_ref": ref, "manifest_sha256": MANIFEST, "model_key": key,
              "accounting": "160_PRIVATE_PLANNED_ROWS" if rows else "NOT_READ_NO_DATA_AUTHORITY"})
        if owns_slot:
            terminal = {**slot_record, "status": "CONSUMED" if consumed is True else
                        "UNKNOWN_DO_NOT_RETRY" if consumed is None else "BLOCKED_RESERVED_NO_RETRY",
                        "attempt_consumed": consumed, "stage": stage, "failure": reason}
            if recovery_action is not None:
                terminal.update(status="ATTEMPT_ENDED", recovery_available=True,
                                run_kind=grant["run_kind"], scientific_selection="PENDING")
            retain("owner_consumption_log.json", terminal)
            try:
                write(safe(work / "attempts", slot_name + ".terminal.json"), terminal)
            except BaseException as error:
                finalizer_errors.append(error_record(error, "owner_slot_terminal"))
        if scratch:
            # Keep scratch outside saved Outputs, using the existing owned cleanup.
            try:
                boot.cleanup_scratch(scratch_root, scratch, output.name)
                retain("cleanup.json", {"status": "OWNED_SCRATCH_REMOVED"})
            except BaseException as error:
                retain("cleanup_failure.json", error_record(error, "cleanup"))
        if finalizer_errors:
            retain("finalizer_errors.json", finalizer_errors.copy())
        archive = Path(str(output) + ".zip")
        try:
            export(output, archive)
        except BaseException as error:
            print("EXPORT_FAILED; retain evidence directory/partial archive:", output, type(error).__name__, flush=True)
            raise
        print("Download private evidence:", archive, "and", str(archive)+".sha256.json", flush=True)
        if technical_smoke:
            try:
                final = smoke.receipt(output, archive, grant)
            except BaseException as error:
                final = {"status": "BLOCKED_NOT_VERIFIED", "source_sha256": source, "runtime_ref": ref,
                         "archive_sha256": sha(archive), "failure": error_record(error, "technical_smoke_receipt")}
            write(Path(str(output) + ".smoke-result.json"), final)
            print("Technical smoke:", final["status"], flush=True)
        if qualification:
            from .train_route import receipt
            try:
                final = receipt(output, archive, grant)
            except BaseException as error:
                final = {"status": "BLOCKED_NOT_VERIFIED", "source_sha256": source, "runtime_ref": ref,
                         "archive_sha256": sha(archive), "failure": error_record(error, "qualification_receipt")}
            write(Path(str(output) + ".qualification-result.json"), final)
            print("Production engineering qualification:", final["status"], flush=True)
    return output


def launch_owner(key, source, repo, ref, *, owner_start=False, action="resume", implementation=None, **kwargs):
    """One bounded, exclusive attempt per invocation; never an automatic loop."""
    require(owner_start is True, "OWNER_START_REQUIRED")
    work = Path(kwargs.pop("work", None) or Path.cwd() / "data/processed/candidate160")
    work.mkdir(parents=True, exist_ok=True)
    with history.lease(work, key) as child_options:
        if action in ("qualify", "qualify_rerun"):
            suffix = "_q" + ("_fp32" if implementation else "")
            return launch(key, source, repo, ref, work=work.with_name(work.name + suffix),
                          owner_start=True, recovery_action="rerun" if action == "qualify_rerun" else "resume",
                          implementation=implementation, qualification=True, child_options=child_options, **kwargs)
        if action == "technical_smoke_resampler_fp32_v1":
            from .minicpm_resampler_fp32 import ID
            require(key == "minicpm4", "MINICPM_ONLY_NUMERICAL_EXCEPTION")
            return launch(key, source, repo, ref, work=work.with_name(work.name + "_smoke_resampler_fp32_v1"),
                          owner_start=True, technical_smoke=True, implementation=ID,
                          child_options=child_options, **kwargs)
        if action == "technical_smoke":
            require(implementation is None, "USE_EFFECTIVE_SMOKE_ACTION")
            return launch(key, source, repo, ref, work=work.with_name(work.name + "_smoke"),
                          owner_start=True, technical_smoke=True, child_options=child_options, **kwargs)
        from .train_route import configuration_admission
        configuration_admission(key, implementation)
        return launch(key, source, repo, ref, work=work, owner_start=True,
                      recovery_action=action, implementation=implementation, child_options=child_options, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "output", "bundle", "snapshot", "weights"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("source", "ref"):
        parser.add_argument("--" + name, required=True)
    authority = parser.add_mutually_exclusive_group(required=True)
    authority.add_argument("--execution", type=Path, help="Owner execution record, not an external grant")
    authority.add_argument("--grant", type=Path, help="Legacy external grant")
    parser.add_argument("--ledger", type=Path, help="Required only with legacy --grant")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true")
    mode.add_argument("--cuda-check-only", action="store_true")
    a = parser.parse_args()
    if a.execution:
        require(a.ledger is None, "OWNER_EXECUTION_IS_NOT_AN_EXTERNAL_GRANT")
        execution, ledger = read(a.execution), None
        require(execution.get("schema") in (owner.SCHEMA, history.SCHEMA, smoke.SCHEMA), "OWNER_EXECUTION_SCHEMA")
    else:
        require(a.ledger is not None, "LEGACY_LEDGER_REQUIRED")
        execution, ledger = read(a.grant), read(a.ledger)
        require(execution.get("schema") not in (owner.SCHEMA, history.SCHEMA, smoke.SCHEMA), "USE_OWNER_EXECUTION_ARGUMENT")
    worker(a.repo, a.output, a.bundle, a.snapshot, a.weights, execution, ledger, a.source, a.ref,
           check_only=a.check_only, cuda_check_only=a.cuda_check_only)


if __name__ == "__main__":
    main()
