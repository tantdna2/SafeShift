"""Repeatable admission diagnostics: no execution record, reservation or attempt.

Reads attached metadata/source/shard hashes, installs only software, constructs
an empty meta model and probes CUDA FP16. Never loads weights or calls a model.
"""
import argparse
import os
from pathlib import Path
import subprocess
import time
import uuid

from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import export, safe, sha, write
from .source import require, stage_snapshot
from .train_contract import KEYS, manifest, model, source_hash
from .train_inputs import discover, checkpoint
from .loading import verify_weights
from . import train_owner as owner


def native_cpu(key, snapshot, repo):
    from .loading import native_setup, load_meta_model
    from .inputs import prepare_inputs, validate_inputs
    from PIL import Image
    from safeshift.pilot.contract import PROMPT_SHA
    prompt = Path(repo) / "configs/pilot/classification_c1.txt"
    require(sha(prompt) == PROMPT_SHA, "C1_HASH")
    evidence = {}
    processor, tokenizer, config, cls = native_setup(snapshot, key, evidence)
    empty, attention = load_meta_model(snapshot, key, config, cls)
    evidence["meta_loader"] = attention
    evidence["synthetic_images"] = []
    for size in ((1, 1), (1, 17), (17, 1), (3, 19), (19, 3), (640, 480), (200, 1200), (2048, 1536)):
        with Image.new("RGB", size, (40, 80, 120)) as image:
            rendered, inputs = prepare_inputs(processor, key, prompt.read_text(), image)
            evidence["synthetic_images"].append(validate_inputs(processor, key, config, rendered, inputs, prompt.read_text()))
    del empty, processor, tokenizer
    return evidence


def launch_preflight(key, source, repo, ref, *, inputs=None, work=None, scratch_root=None):
    """The shipped diagnostic notebook has no call path to launch_owner."""
    from .train_runtime import prepare_runtime, hardware
    require(key in KEYS, "CANDIDATE_KEY")
    inputs = Path(inputs or "/kaggle/input")
    work = Path(work or Path.cwd() / "data/processed/candidate160_preflight")
    work.mkdir(parents=True, exist_ok=True)
    output = safe(work, key + "-" + uuid.uuid4().hex)
    output.mkdir(exist_ok=False)
    checks, scratch = {}, None
    report = {"schema": "safeshift-candidate160-preflight-v1", "model_key": key,
              "source_sha256": source, "runtime_ref": ref, "checks": checks,
              "attempt_consumed": False, "owner_slot_created": False, "native_calls": 0,
              "weights_loaded": False, "model_fit_behavior_hnlo": "UNVERIFIED",
              "limitation": "No reservation or permission to replay; observations expire as resources change."}
    def check(name, action):
        try:
            value = action()
            checks[name] = {"status": "PASS", "evidence": value}
            return value
        except BaseException as error:
            checks[name] = {"status": "BLOCKED", "error": {"type": type(error).__name__, "message": str(error)[:2000]}}
            if hasattr(error, "gpu_preflight_receipt"):
                checks[name]["evidence"] = error.gpu_preflight_receipt
            return None
    for name in ("source_binding", "manifest", "checkpoint", "scratch", "storage", "python_software",
                 "cpu_native", "images_cpu", "live_resources", "gpu_driver", "cuda_child"):
        checks[name] = {"status": "NOT_RUN"}
    try:
        def binding():
            require(source_hash(repo) == source, "PREFLIGHT_SOURCE_MISMATCH")
            return {"source_sha256": source}
        bound = check("source_binding", binding)
        def bundle_check():
            bundle = discover(inputs, "pilot_manifest.json").parent
            plan, rows = manifest(bundle)
            for row in rows:
                require(safe(bundle, row["image"]).is_file(), "IMAGE_MISSING")
            return {"manifest_sha256": sha(bundle / "pilot_manifest.json"), "images_present": len(rows),
                    "image_hash_decode": "DEFERRED_TO_RUN_PRECONSUMPTION"}
        admitted_manifest = check("manifest", bundle_check)
        def checkpoint_check():
            marker, source_dir, weights = checkpoint(inputs, key)
            from .source import verify_snapshot
            verify_snapshot(source_dir, key)
            verify_weights(weights, key)
            return {"marker_relative_to_inputs": marker.relative_to(inputs).as_posix(),
                    "source_hashes": "PASS", "index_and_shard_hashes": "PASS", "weights_loaded": False}
        admitted_checkpoint = check("checkpoint", checkpoint_check)
        def scratch_check():
            nonlocal scratch, scratch_root, env
            scratch_root = boot.provision_scratch_root(Path.cwd(), scratch_root or "/kaggle/tmp")
            scratch, env = boot.prepare_scratch(scratch_root, output.name)
            return {"writable_fsynced": True}
        env = None
        if check("scratch", scratch_check):
            def storage_check():
                receipt = boot.storage_admission(scratch, output)
                write(output / "storage.json", receipt)
                require(receipt["admitted"], "PHYSICAL_ALLOCATION_NOT_ADMITTED:" + receipt.get("reason", "UNKNOWN"))
                return receipt
            storage = check("storage", storage_check)
            if storage and bound:
                deadline = time.monotonic() + owner.MAX_SECONDS
                runtime = check("python_software", lambda: prepare_runtime(Path(repo), key, scratch, output, env, deadline))
                if runtime:
                    python, env = runtime
                    # Runtime paths/environment are not JSON evidence; the durable
                    # setup/provider/freeze receipts carry the full qualification.
                    checks["python_software"]["evidence"] = {"worker_version_required": "3.11.9", "pins_installed": True}
                    command = [str(python), "-B", "-m", "safeshift.candidates.train_preflight", "--worker",
                               "--key", key, "--repo", str(repo), "--output", str(output)]
                    def child(suffix, extra, cuda):
                        with (output / (suffix + ".log")).open("xb") as log:
                            subprocess.run(command + extra, env={**env, "CUDA_VISIBLE_DEVICES": cuda},
                                           stdout=log, stderr=subprocess.STDOUT, check=True,
                                           timeout=max(1, deadline-time.monotonic()))
                        from safeshift.pilot.artifacts import read
                        return read(output / (suffix + ".json"))
                    check("live_resources", lambda: child("live_resources", ["--resources"], ""))
                    if admitted_manifest:
                        bundle = discover(inputs, "pilot_manifest.json").parent
                        check("images_cpu", lambda: child("images_cpu", ["--images", "--bundle", str(bundle)], ""))
                    if admitted_checkpoint:
                        _, source_dir, _ = checkpoint(inputs, key)
                        snapshot = scratch / model(key)["revision"]
                        def cpu():
                            stage_snapshot(source_dir, snapshot, key)
                            return child("cpu_native", ["--snapshot", str(snapshot)], "")
                        check("cpu_native", cpu)
                    check("cuda_child", lambda: child("cuda_child", ["--cuda"], "0"))
        check("gpu_driver", lambda: hardware(owner.policy()))
    finally:
        if scratch:
            check("cleanup", lambda: boot.cleanup_scratch(scratch_root, scratch, output.name))
        report["status"] = ("PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED" if all(c["status"] == "PASS" for c in checks.values())
                            else "BLOCKED")
        write(output / "preflight.json", report)
        export(output, Path(str(output) + ".zip"))
        print("Preflight:", report["status"], "(no slot, no attempt, no model calls)", output, flush=True)
    return output


def main():
    from .train_runtime import software, resources, worker_cuda
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true", required=True)
    parser.add_argument("--key", choices=KEYS, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--cuda", action="store_true")
    modes.add_argument("--resources", action="store_true")
    modes.add_argument("--images", action="store_true")
    modes.add_argument("--snapshot")
    parser.add_argument("--bundle")
    args = parser.parse_args()
    output = Path(args.output)
    write(output / ("software_cuda.json" if args.cuda else "software_resources.json" if args.resources else "software_images.json" if args.images else "software_cpu.json"),
          software(args.key))
    if args.cuda:
        write(output / "cuda_child.json", worker_cuda(owner.policy()))
    elif args.resources:
        write(output / "live_resources.json", resources(owner.policy(), os.environ["SAFESHIFT_RUNTIME_ROOT"], output))
    elif args.images:
        from .train_runtime import verify_images
        require(args.bundle, "BUNDLE_REQUIRED")
        _, rows = manifest(Path(args.bundle))
        write(output / "images_cpu.json", verify_images(Path(args.bundle), rows))
    else:
        require(args.snapshot, "PUBLIC_SNAPSHOT_REQUIRED")
        write(output / "cpu_native.json", native_cpu(args.key, Path(args.snapshot), Path(args.repo)))


if __name__ == "__main__":
    main()
