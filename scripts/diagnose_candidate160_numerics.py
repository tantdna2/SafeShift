"""Bounded MiniCPM diagnostic: observe unchanged FP16 weights/native outputs.

Not a production runner or qualification. One locked first TRAIN image, at most
one native call; stop at the first nonfinite module output. Hooks never replace
values, cast computations or alter model/config/source/checkpoint bytes.
"""
import argparse
from collections import Counter
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


def tensors(value, path="output", depth=0):
    import torch
    if isinstance(value, torch.Tensor):
        if value.is_floating_point():
            yield path, value
    elif depth < 8 and isinstance(value, dict):
        for key, item in list(value.items())[:128]:
            yield from tensors(item, path + "." + str(key), depth + 1)
    elif depth < 8 and isinstance(value, (tuple, list)):
        for i, item in enumerate(value[:128]):
            yield from tensors(item, path + "." + str(i), depth + 1)


def describe(tensor):
    import torch
    finite = torch.isfinite(tensor)
    return {"shape": list(tensor.shape), "dtype": str(tensor.dtype),
        "nan": int(torch.isnan(tensor).sum().item()), "positive_inf": int(torch.isposinf(tensor).sum().item()),
        "negative_inf": int(torch.isneginf(tensor).sum().item()),
        "finite_abs_max": float(torch.where(finite, tensor.abs(), 0).max().item()) if tensor.numel() else 0.0}


def observe_model(model, output):
    """Install observation-only hooks; caller removes handles in finally."""
    from safeshift.pilot.artifacts import write
    import torch
    handles = []
    def hook(name):
        def inspect(module, args, kwargs, value):
            for path, tensor in tensors(value):
                if not bool(torch.isfinite(tensor).all()):
                    write(output / "first_nonfinite.json", {"module": name, "class": type(module).__name__,
                        "output_path": path, "output": describe(tensor),
                        "inputs": [{"path": p, **describe(t)} for p, t in tensors((args, kwargs), "inputs")]})
                    raise FloatingPointError("NATIVE_NONFINITE_MODULE:" + name)
        return inspect
    for name, module in model.named_modules():
        handles.append(module.register_forward_hook(hook(name), with_kwargs=True))
    return handles


def child(args, grant):
    import torch
    from safeshift.candidates import train_runtime as rt, train_contract as c
    from safeshift.candidates.backend import CandidateBackend
    from safeshift.pilot.artifacts import write, safe, read, sha
    from safeshift.pilot.runner import error_record
    output = args.output
    write(output / "diagnostic_software.json", rt.software("minicpm4"))
    write(output / "diagnostic_cuda.json", rt.worker_cuda(grant["policy"]))
    plan, rows = c.manifest(args.bundle)
    write(output / "diagnostic_images.json", rt.verify_images(args.bundle, rows))
    prompt = (args.repo / "configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
    backend = CandidateBackend("minicpm4", args.snapshot, args.weights, prompt, device="cuda:0")
    write(output / "diagnostic_model_runtime.json", backend.environment)
    bad, dtypes = [], Counter()
    for name, parameter in backend.model.named_parameters():
        dtypes[str(parameter.dtype)] += parameter.numel()
        if not bool(torch.isfinite(parameter).all()):
            bad.append({"name": name, **describe(parameter)})
            if len(bad) >= 8:
                break
    write(output / "weight_numerics.json", {"all_parameters_finite": not bad, "bad_parameters": bad,
        "parameter_dtypes": dict(dtypes), "weights_loaded": True, "native_calls": 0})
    if bad:
        from safetensors import safe_open
        index = read(args.weights / "model.safetensors.index.json")
        originals = []
        for entry in bad:
            name = entry["name"]
            with safe_open(str(args.weights / index["weight_map"][name]), framework="pt", device="cpu") as file:
                originals.append({"name": name, **describe(file.get_tensor(name))})
        write(output / "original_checkpoint_numerics.json", originals)
        return
    handles = observe_model(backend.model, output)
    try:
        # CandidateBackend owns native_call.json immediately before generate.
        raw = backend.generate(safe(args.bundle, rows[0]["image"]), output / "sample")
        write(output / "diagnostic_raw.json", raw)
        write(output / "diagnostic_outcome.json", {"status": "ONE_NATIVE_CALL_FINISHED", "raw_nonfinite": raw["raw_nonfinite"]})
    except BaseException as error:
        write(output / "diagnostic_outcome.json", {"status": "STOPPED_AT_OBSERVED_FAILURE",
              "failure": error_record(error, "native_numerics")})
    finally:
        for handle in handles:
            handle.remove()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo", "output", "bundle", "snapshot", "weights"):
        parser.add_argument("--" + name, type=Path, required=name == "repo")
    for name in ("source", "ref"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    sys.path.insert(0, str(args.repo))
    from safeshift.candidates import train_runtime as rt, train_contract as c, train_smoke as smoke
    from safeshift.candidates.source import require, stage_snapshot
    from safeshift.pilot.artifacts import write, read, sha, export
    from safeshift.pilot.runner import error_record
    require(c.source_hash(args.repo) == args.source, "DIAGNOSTIC_SOURCE_MISMATCH")
    if args.worker:
        grant = read(args.output / "diagnostic_execution.json")
        smoke.validate(grant, "minicpm4", args.source, args.ref)
        require(sha(__file__) == read(args.output / "diagnostic_binding.json")["driver_sha256"], "DIAGNOSTIC_DRIVER_CHANGED")
        child(args, grant)
        return
    started = time.monotonic()
    grant = smoke.execution("minicpm4", args.source, args.ref)
    output = Path.cwd() / "data/processed/candidate160_diagnostics" / ("minicpm4-" + uuid.uuid4().hex)
    output.mkdir(parents=True, exist_ok=False)
    scratch, scratch_root = None, None
    write(output / "diagnostic_execution.json", grant)
    write(output / "diagnostic_binding.json", {"source_sha256": args.source, "runtime_ref": args.ref,
          "driver_sha256": sha(__file__), "max_seconds": 3600, "max_native_calls": 1,
          "purpose": "NUMERICAL_DIAGNOSIS_ONLY_NOT_RELEASE_QUALIFICATION"})
    try:
        bundle = rt.discover(Path("/kaggle/input"), "pilot_manifest.json").parent
        plan, rows = c.manifest(bundle)
        write(output / "technical_selection.json", smoke.selection(rows, grant))
        _, source, weights = rt.checkpoint(Path("/kaggle/input"), "minicpm4")
        write(output / "checkpoint_admission.json", rt.verify_weights(weights, "minicpm4"))
        scratch_root = rt.boot.provision_scratch_root(Path.cwd(), "/kaggle/tmp")
        scratch, env = rt.boot.prepare_scratch(scratch_root, output.name)
        snapshot = scratch / c.model("minicpm4")["revision"]
        write(output / "source_admission.json", stage_snapshot(source, snapshot, "minicpm4"))
        storage = rt.boot.storage_admission(scratch, output)
        write(output / "storage.json", storage)
        require(storage["admitted"], "INSUFFICIENT_PHYSICAL_STORAGE")
        deadline = started + 3600
        python, env = rt.prepare_runtime(args.repo, "minicpm4", scratch, output, env, deadline)
        env["CUDA_VISIBLE_DEVICES"] = "0"
        command = [str(python), "-B", str(Path(__file__).absolute()), "--worker", "--repo", str(args.repo),
                   "--source", args.source, "--ref", args.ref, "--output", str(output),
                   "--bundle", str(bundle), "--snapshot", str(snapshot), "--weights", str(weights)]
        with (output / "diagnostic.log").open("xb") as log:
            subprocess.run(command, env=env, check=True, timeout=max(1, deadline-time.monotonic()),
                           stdout=log, stderr=subprocess.STDOUT)
    except BaseException as error:
        write(output / "diagnostic_failure.json", error_record(error, "numerics_diagnostic"))
    finally:
        if scratch:
            rt.boot.cleanup_scratch(scratch_root, scratch, output.name)
        archive = Path(str(output) + ".zip")
        export(output, archive)
        print("DIAGNOSTIC_ONLY_NO_QUALIFICATION", archive, sha(archive), flush=True)


if __name__ == "__main__":
    main()
