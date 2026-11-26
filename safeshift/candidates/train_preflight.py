"""Repeatable environment-first diagnostics; no reservation, weights or inference."""
import argparse
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import time
import uuid

from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import export, read, safe, sha, verify_archive, write
from safeshift.pilot.runner import error_record
from .source import require, stage_snapshot
from .train_contract import KEYS, manifest, model, source_hash
from .train_inputs import discover, checkpoint
from .loading import verify_weights
from . import train_owner as owner

CHILD_SCHEMA = "safeshift-candidate160-preflight-child-v1"
REQUIRED = ("source_binding", "environment", "host_abi", "manifest", "checkpoint", "scratch", "storage",
            "runtime_setup", "software_cpu", "cpu_native", "images_cpu", "live_resources", "gpu_driver", "cuda_child")


def environment_observation():
    """Only fixed stdlib observations; no package/GPU imports or secret inventory."""
    observed = {"kernel": {"implementation": platform.python_implementation(), "version": platform.python_version(),
        "system": platform.system(), "machine": platform.machine(), "pointer_bits": struct.calcsize("P") * 8},
        "inherited_cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET"),
        "worker_cuda_visible_devices_required": "0", "physical_gpu_count_required": 2,
        "worker": {"version": "3.11.9", "strategy": "eligible installed interpreter, otherwise source/hash/size-locked PBS20240726"},
        "resource_observations": {}, "limits": "RAM/cgroup enforced in isolated child; quotas need actual allocation; model fit UNVERIFIED"}
    for name in ("/proc/meminfo", "/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory.current",
                 "/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/memory/memory.usage_in_bytes"):
        path = Path(name)
        if path.is_file():
            with path.open() as stream:
                value = stream.read(16385)
            require(len(value) <= 16384, "RESOURCE_OBSERVATION_SIZE_BOUND")
            observed["resource_observations"][name] = value.strip()
    return observed


def native_cpu(key, snapshot, repo, *, implementation=None):
    from .loading import native_setup, load_meta_model
    from .inputs import prepare_inputs, validate_inputs
    from PIL import Image
    from safeshift.pilot.contract import PROMPT_SHA
    snapshot, repo = Path(snapshot), Path(repo)
    prompt = repo / "configs/pilot/classification_c1.txt"
    require(sha(prompt) == PROMPT_SHA, "C1_HASH")
    evidence = {}
    processor, tokenizer, config, cls = native_setup(snapshot, key, evidence)
    empty, attention = load_meta_model(snapshot, key, config, cls)
    if implementation is not None:
        from . import minicpm_resampler_fp32 as numerical
        require(key == "minicpm4" and implementation == numerical.ID, "UNKNOWN_EFFECTIVE_IMPLEMENTATION")
        evidence["effective_implementation"] = numerical.install(empty)
    evidence["meta_loader"] = attention
    evidence["synthetic_images"] = []
    for size in ((1, 1), (1, 17), (17, 1), (3, 19), (19, 3), (640, 480), (200, 1200), (2048, 1536)):
        with Image.new("RGB", size, (40, 80, 120)) as image:
            rendered, inputs = prepare_inputs(processor, key, prompt.read_text(), image)
            evidence["synthetic_images"].append(validate_inputs(processor, key, config, rendered, inputs, prompt.read_text()))
    del empty, processor, tokenizer
    return evidence


def evidence_levels(checks):
    def level(names):
        states = [checks[n]["status"] for n in names]
        return "PASS" if all(s == "PASS" for s in states) else "BLOCKED" if "BLOCKED" in states else "NOT_RUN"
    return {"ENVIRONMENT_OBSERVED": level(("environment",)),
            "CPU_SOFTWARE_PASS": level(("runtime_setup", "software_cpu", "cpu_native")),
            "LIVE_GPU_PREFLIGHT_PASS": level(("software_cpu", "gpu_driver", "cuda_child")),
            "WEIGHTS_LOADED": "NOT_RUN", "INFERENCE_VERIFIED": "NOT_RUN", "SCIENTIFIC_QUALIFIED": "UNVERIFIED"}


def validate_child_evidence(name, evidence, key):
    """Exit code zero and a PASS word do not establish a complete child check."""
    require(type(evidence) is dict, "CHILD_EVIDENCE_OBJECT_REQUIRED")
    if name == "software_cpu":
        from .train_runtime import pins
        require(evidence.get("versions") == pins(key) and evidence.get("compiled_cpu_nms") == "PASS"
                and evidence.get("cuda_build") == "12.4" and type(evidence.get("identity")) is dict,
                "CHILD_SOFTWARE_EVIDENCE_INCOMPLETE")
    elif name == "cuda_child":
        require(evidence.get("worker_cuda") == "MEASURED_FP16_FUNCTIONAL" and evidence.get("worker_visible_gpus") == 1,
                "CHILD_CUDA_EVIDENCE_INCOMPLETE")
    elif name == "cpu_native":
        require(evidence.get("meta_loader", {}).get("status") == "EAGER_MODULES_VERIFIED"
                and type(evidence.get("synthetic_images")) is list and len(evidence["synthetic_images"]) == 8,
                "CHILD_NATIVE_EVIDENCE_INCOMPLETE")
    elif name == "images_cpu":
        require(type(evidence.get("verified_images")) is int and evidence["verified_images"] == 160,
                "CHILD_IMAGES_EVIDENCE_INCOMPLETE")
    elif name == "live_resources":
        require(all(type(evidence.get(n)) is int and evidence[n] >= owner.policy()[n]
                    for n in ("free_ram_mib", "free_scratch_mib", "free_output_mib")), "CHILD_RESOURCES_EVIDENCE_INCOMPLETE")
    else:
        raise ValueError("UNKNOWN_CHILD_CHECK")
    return evidence


def launch_preflight(key, source, repo, ref, *, inputs=None, work=None, scratch_root=None):
    """Independent diagnostics; no call path to execution/reservation/run_calls."""
    from .train_runtime import prepare_runtime, hardware
    require(key in KEYS, "CANDIDATE_KEY")
    inputs = Path(inputs or "/kaggle/input")
    work = Path(work or Path.cwd() / "data/processed/candidate160_preflight")
    work.mkdir(parents=True, exist_ok=True)
    output = safe(work, key + "-" + uuid.uuid4().hex)
    output.mkdir(exist_ok=False)
    checks = {name: {"status": "NOT_RUN"} for name in REQUIRED}
    scratch, env = None, None
    started = time.monotonic()
    deadline = started + owner.MAX_SECONDS
    report = {"schema": "safeshift-candidate160-preflight-v2", "model_key": key,
              "source_sha256": source, "runtime_ref": ref, "checks": checks,
              "attempt_consumed": False, "owner_slot_created": False, "native_calls": 0,
              "weights_loaded": False, "model_fit_behavior_hnlo": "UNVERIFIED", "max_seconds": owner.MAX_SECONDS,
              "evidence_export": "PENDING_READ_FINAL_RESULT_AND_VERIFY_ZIP_SIDECAR",
              "side_effects": ["read attached manifest/images/source/shard bytes for verification",
                  "install pinned software in owned scratch; never download weights",
                  "simultaneous temporary physical allocation: 28GiB scratch + 4GiB output",
                  "CPU empty meta/processor and CUDA FP16 tensor probe; no model inference",
                  "remove owned scratch; retain private evidence, ZIP, checksum sidecar and final result"],
              "limitation": "No execution permission or replay eligibility; observations expire; model peak fit remains UNVERIFIED."}
    def remaining():
        value = deadline - time.monotonic()
        require(value > 0, "PREFLIGHT_TIME_CAP")
        return value
    def check(name, action, *, cleanup=False):
        began = time.monotonic()
        try:
            if not cleanup:
                remaining()
            value = action()
            if not cleanup:
                remaining()
            checks[name] = {"status": "PASS", "evidence": value, "seconds": time.monotonic() - began}
            return value
        except Exception as error:
            checks[name] = {"status": "BLOCKED", "error": error_record(error, name), "seconds": time.monotonic() - began}
            if hasattr(error, "gpu_preflight_receipt"):
                checks[name]["evidence"] = error.gpu_preflight_receipt
            return None
    try:
        def binding():
            require(re.fullmatch(r"[0-9a-f]{40}", ref) and source_hash(repo) == source, "PREFLIGHT_SOURCE_MISMATCH")
            return {"source_sha256": source}
        if not check("source_binding", binding):
            return output
        observed = check("environment", environment_observation)
        if observed is not None:
            write(output / "environment.json", observed)
            def abi():
                kernel = observed["kernel"]
                require(kernel["system"] == "Linux" and kernel["machine"].lower() in ("x86_64", "amd64")
                        and kernel["pointer_bits"] == 64, "PREFLIGHT_LINUX_X86_64_HOST_REQUIRED")
                return kernel
            check("host_abi", abi)
        check("gpu_driver", lambda: hardware(owner.policy()))
        def bundle_check():
            bundle = discover(inputs, "pilot_manifest.json").parent
            _, rows = manifest(bundle)
            for row in rows:
                require(safe(bundle, row["image"]).is_file(), "IMAGE_MISSING")
            return {"manifest_sha256": sha(bundle / "pilot_manifest.json"), "images_present": len(rows),
                    "image_hash_decode": "SEE_IMAGES_CPU_CHECK"}
        admitted_manifest = check("manifest", bundle_check)
        def checkpoint_check():
            marker, source_dir, weights = checkpoint(inputs, key)
            from .source import verify_snapshot
            spec = verify_snapshot(source_dir, key)
            locked_weights = verify_weights(weights, key)
            return {"marker_relative_to_inputs": marker.relative_to(inputs).as_posix(), "marker_sha256": sha(marker),
                    "source_hashes": spec, "index_and_shard_hashes": locked_weights, "weights_loaded": False}
        admitted_checkpoint = check("checkpoint", checkpoint_check)
        def scratch_check():
            nonlocal scratch, scratch_root, env
            scratch_root = boot.provision_scratch_root(Path.cwd(), scratch_root or "/kaggle/tmp")
            try:
                scratch, env = boot.prepare_scratch(scratch_root, output.name)
            except BaseException:
                candidate = safe(scratch_root, "safeshift-pilot-" + output.name)
                if candidate.exists():
                    scratch = candidate  # cleanup still requires the original ownership marker
                raise
            write(output / "output_write_probe.json", {"exclusive_write_fsync": "PASS"})
            return {"writable_fsynced": True, "scratch": boot.filesystem_usage(scratch), "output": boot.filesystem_usage(output)}
        if check("scratch", scratch_check):
            def storage_check():
                receipt = boot.storage_admission(scratch, output)
                write(output / "storage.json", receipt)
                require(receipt["admitted"], "PHYSICAL_ALLOCATION_NOT_ADMITTED:" + receipt.get("reason", "UNKNOWN"))
                return receipt
            storage = check("storage", storage_check)
            if storage and admitted_manifest and admitted_checkpoint and checks["host_abi"]["status"] == "PASS":
                runtime = check("runtime_setup", lambda: prepare_runtime(Path(repo), key, scratch, output, env, deadline))
                if runtime:
                    python, env = runtime
                    checks["runtime_setup"]["evidence"] = {"worker_version_required": "3.11.9", "pins_installed": True,
                        "qualification": "SEE_SOFTWARE_CPU_CHECK"}
                    command = [str(python), "-B", "-m", "safeshift.candidates.train_preflight", "--worker", "--key", key,
                               "--repo", str(repo), "--output", str(output), "--source", source, "--ref", ref]
                    def child(name, extra=(), cuda=""):
                        with (output / (name + ".log")).open("xb") as log:
                            subprocess.run(command + list(extra), env={**env, "CUDA_VISIBLE_DEVICES": cuda},
                                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=remaining())
                        path = safe(output, name + ".json")
                        require(path.is_file() and path.stat().st_size <= 2**20, "CHILD_RECEIPT_MISSING_OR_OVERSIZE")
                        value = read(path)
                        require(type(value) is dict and value.get("schema") == CHILD_SCHEMA
                                and value.get("status") == "PASS" and value.get("check") == name
                                and value.get("model_key") == key and value.get("source_sha256") == source
                                and value.get("runtime_ref") == ref and type(value.get("evidence")) is dict,
                                "CHILD_RECEIPT_BINDING_OR_STATUS")
                        return validate_child_evidence(name, value["evidence"], key)
                    qualified = check("software_cpu", lambda: child("software_cpu", ["--software-only"]))
                    if qualified is not None:
                        check("live_resources", lambda: child("live_resources", ["--resources"]))
                        if admitted_manifest:
                            bundle = discover(inputs, "pilot_manifest.json").parent
                            check("images_cpu", lambda: child("images_cpu", ["--images", "--bundle", str(bundle)]))
                        if admitted_checkpoint:
                            _, source_dir, _ = checkpoint(inputs, key)
                            snapshot = scratch / model(key)["revision"]
                            def cpu():
                                stage_snapshot(source_dir, snapshot, key)
                                return child("cpu_native", ["--snapshot", str(snapshot)])
                            check("cpu_native", cpu)
                        if checks["gpu_driver"]["status"] == "PASS":
                            check("cuda_child", lambda: child("cuda_child", ["--cuda"], "0"))
    except BaseException as error:
        checks["orchestration"] = {"status": "BLOCKED", "error": error_record(error, "preflight")}
        raise
    finally:
        if scratch:
            check("cleanup", lambda: boot.cleanup_scratch(scratch_root, scratch, output.name), cleanup=True)
        report["status"] = ("PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED" if all(c["status"] == "PASS" for c in checks.values()) else "BLOCKED")
        report["levels"] = evidence_levels(checks)
        report["elapsed_seconds"] = time.monotonic() - started
        archive = Path(str(output) + ".zip")
        result_file = Path(str(output) + ".preflight-result.json")
        result = {**report, "schema": "safeshift-candidate160-preflight-result-v1", "evidence_export": "BLOCKED"}
        try:
            write(output / "preflight.json", report)
            export(output, archive)
            verify_archive(archive)
            archive_sha = sha(archive)
            require(read(Path(str(archive) + ".sha256.json"))["sha256"] == archive_sha, "PREFLIGHT_ARCHIVE_SIDECAR_MISMATCH")
            result.update(evidence_export="VERIFIED", archive_sha256=archive_sha)
        except BaseException as error:
            result.update(status="BLOCKED", export_error=error_record(error, "preflight_export"))
            raise
        finally:
            write(result_file, result)
            print("Preflight:", result["status"], "(no slot, no attempt, no model calls)", flush=True)
            print("Download:", archive, str(archive) + ".sha256.json", result_file, flush=True)
            if result["evidence_export"] != "VERIFIED":
                print("EXPORT BLOCKED: retain directory/partial files; read final result; do not start production.", output, flush=True)
    return output


def main():
    from .train_runtime import software, resources, worker_cuda
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--key", choices=KEYS, required=True)
    for name in ("repo", "output", "source", "ref"):
        parser.add_argument("--" + name, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--software-only", action="store_true")
    modes.add_argument("--cuda", action="store_true")
    modes.add_argument("--resources", action="store_true")
    modes.add_argument("--images", action="store_true")
    modes.add_argument("--snapshot")
    parser.add_argument("--bundle")
    args = parser.parse_args()
    require(source_hash(args.repo) == args.source and re.fullmatch(r"[0-9a-f]{40}", args.ref), "CHILD_SOURCE_BINDING")
    qualification = software(args.key)
    if args.software_only:
        name, evidence = "software_cpu", qualification
    elif args.cuda:
        name, evidence = "cuda_child", worker_cuda(owner.policy())
    elif args.resources:
        name, evidence = "live_resources", resources(owner.policy(), os.environ["SAFESHIFT_RUNTIME_ROOT"], args.output)
    elif args.images:
        from .train_runtime import verify_images
        require(args.bundle, "BUNDLE_REQUIRED")
        _, rows = manifest(Path(args.bundle))
        name, evidence = "images_cpu", verify_images(Path(args.bundle), rows)
    else:
        name, evidence = "cpu_native", native_cpu(args.key, Path(args.snapshot), Path(args.repo))
    write(Path(args.output) / (name + ".json"), {"schema": CHILD_SCHEMA, "status": "PASS", "check": name,
          "model_key": args.key, "source_sha256": args.source, "runtime_ref": args.ref, "evidence": evidence})


if __name__ == "__main__":
    main()
