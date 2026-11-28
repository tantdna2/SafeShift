#!/usr/bin/env python3
"""Offline CT1 checkpoint reader parity, CPU only; this is not production admission.

Run from the repository root with --snapshot and a *new* --output directory
under data/processed. The snapshot must be the locked Qwen3 revision. No model
is instantiated and no inference, accelerator operation or download occurs.
Both readers run in fresh, sequential processes; their exclusive JSON receipts
are retained even if a subsequent step fails.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
COUNT = 750
EMBED = "model.language_model.embed_tokens.weight"
HEAD = "lm_head.weight"
BLOCK_BYTES = 8 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def read_json(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=unique_pairs)


def write_exclusive(path, value):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def host():
    result = {"platform": platform.platform(), "rss_peak_bytes": None,
              "proc_status": {}, "meminfo": {}, "cgroup": {}}
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        result["rss_peak_bytes"] = rss if sys.platform == "darwin" else rss * 1024
    except ImportError:
        pass
    for filename, dest, wanted in (
        ("/proc/self/status", "proc_status", {"VmRSS", "VmHWM"}),
        ("/proc/meminfo", "meminfo", {"MemTotal", "MemAvailable"}),
    ):
        try:
            for line in Path(filename).read_text().splitlines():
                key, _, value = line.partition(":")
                if key in wanted:
                    result[dest][key] = value.strip()
        except OSError:
            pass
    # Resolve the current v2 cgroup rather than assuming it is mounted at root.
    try:
        lines = Path("/proc/self/cgroup").read_text().splitlines()
        rel = next(line[3:] for line in lines if line.startswith("0::"))
        mounts = Path("/proc/self/mountinfo").read_text().splitlines()
        mount = next(line for line in mounts if " - cgroup2 " in line)
        fields = mount.split(" - ")[0].split()
        root, point = fields[3].replace("\\040", " "), fields[4].replace("\\040", " ")
        relative = os.path.relpath(rel, root)
        require(relative != ".." and not relative.startswith("../"), "cgroup outside mount")
        base = Path(point) / relative
        for name in ("memory.current", "memory.peak", "memory.max", "memory.stat", "memory.events"):
            try:
                result["cgroup"][name] = (base / name).read_text().strip()
            except OSError:
                pass
    except (OSError, StopIteration, ValueError):
        pass
    return result


def header(path, expected):
    from safeshift.verification173 import safetensors_header
    accounting = safetensors_header(path, expected)
    with path.open("rb") as stream:
        size = struct.unpack("<Q", stream.read(8))[0]
        raw = stream.read(size)
    obj = json.loads(raw, object_pairs_hook=unique_pairs)
    metadata = obj.pop("__metadata__", None)
    return obj, metadata, accounting


def versions():
    import torch
    import safetensors
    import numpy
    lock = read_json(REPO / "configs/fulltrain/qwen3.json")["software"]
    found = {"python": platform.python_version(), "torch": torch.__version__,
             "safetensors": safetensors.__version__, "numpy": numpy.__version__}
    require(all(found[k] == lock[k] for k in found),
            "dependency mismatch: found %s, required %s" % (found, {k: lock[k] for k in found}))
    require(sys.byteorder == "little", "little-endian host required for byte digests")
    return found


def digest_tensor(tensor, digest):
    # A uint8 view preserves BF16/FP16 bits, including NaNs and signed zero.
    import torch

    digest.update(memoryview(tensor.contiguous().reshape(-1).view(torch.uint8).numpy()).cast("B"))


def worker(args):
    import torch
    from safetensors import safe_open
    from safeshift.fulltrain.ct1_direct import VerifiedCheckpoint
    from safeshift.fulltrain.qwen import verify_snapshot

    torch.set_num_threads(2)

    started = time.monotonic()
    version = versions()
    baseline = host()
    snapshot = Path(args.snapshot)
    # Both processes verify all source files; oracle never trusts candidate receipt.
    verify_started = time.monotonic()
    if args.worker == "oracle":
        verification = verify_snapshot(snapshot, repo=REPO)
        context = None
    else:
        context = VerifiedCheckpoint(snapshot, REPO, deadline=time.monotonic() + args.seconds)
        verified = context.__enter__()
        verification = verified.receipt
    verify_seconds = time.monotonic() - verify_started
    rows, file_rows = {}, {}
    totals = {"read_seconds": 0.0, "cast_seconds": 0.0, "h2d_seconds": 0.0}
    retained = None
    overlap_before = overlap_after = None
    temporary_bytes = 0
    try:
        index = (read_json(snapshot / "model.safetensors.index.json") if context is None else verified.index())
        mapping = index["weight_map"]
        require(type(mapping) is dict and len(mapping) == COUNT, "expected exactly 750 indexed tensors")
        require(EMBED in mapping and HEAD in mapping, "missing embedding or lm_head")
        shards = sorted(set(mapping.values()))
        before = host()
        headers = {}
        inventory = verified.inventory() if context is not None else None
        for shard in shards:
            require(Path(shard).name == shard and shard.endswith(".safetensors"), "invalid shard name")
            keys = {k for k, v in mapping.items() if v == shard}
            if inventory is None:
                headers[shard] = header(snapshot / shard, keys)
            else:
                row = inventory[shard]
                entries = row["tensors"]
                headers[shard] = (entries, row["metadata"], {
                    "tensors": len(entries), "header_bytes": row["header_bytes"],
                    "tensor_bytes": max(entry["data_offsets"][1] for entry in entries.values()),
                })
        require(index["metadata"]["total_size"] == sum(h[2]["tensor_bytes"] for h in headers.values()),
                "index total size mismatch")
        for shard in shards:
            entries, metadata, accounting = headers[shard]
            with (safe_open(str(snapshot / shard), framework="pt", device="cpu") if context is None
                  else verified.open(snapshot / shard, framework="pt", device="cpu")) as handle:
                keys = list(handle.keys())
                require(len(keys) == len(set(keys)) and set(keys) == set(entries), "reader keys mismatch")
                require(handle.metadata() == metadata, "reader metadata mismatch")
                file_rows[shard] = {"metadata": handle.metadata(), "keys": keys, "accounting": accounting}
                for key in keys:
                    require(time.monotonic() - started < args.seconds, "worker deadline exceeded")
                    view = handle.get_slice(key)
                    shape, dtype = list(view.get_shape()), view.get_dtype()
                    entry = entries[key]
                    require(shape == entry["shape"] and dtype == entry["dtype"] == "BF16", "shape/dtype mismatch")
                    raw_hash, half_hash = hashlib.sha256(), hashlib.sha256()
                    read_time = cast_time = 0.0
                    if context is not None:
                        began = time.monotonic()
                        full = view[...]
                        read_time += time.monotonic() - began
                        require(full.device.type == "cpu" and full.dtype == torch.bfloat16
                                and list(full.shape) == shape and full.is_contiguous(), "candidate tensor contract")
                        if key == HEAD:
                            require(retained is not None, "embedding not retained")
                            overlap_before = host()
                        began = time.monotonic()
                        half = full.to(dtype=torch.float16)
                        cast_time += time.monotonic() - began
                        temporary_bytes = max(temporary_bytes, full.untyped_storage().nbytes()
                                              + half.untyped_storage().nbytes())
                        if key == HEAD:
                            overlap_after = host()
                        if key == EMBED:
                            retained = half
                        digest_tensor(full, raw_hash)
                        digest_tensor(half, half_hash)
                        del full, half
                    else:
                        row_elements = math.prod(shape[1:]) if shape else 1
                        block_rows = max(1, BLOCK_BYTES // max(1, row_elements * 2))
                        count = shape[0] if shape else 1
                        for start in range(0, count, block_rows):
                            stop = min(count, start + block_rows)
                            began = time.monotonic()
                            block = view[start:stop] if shape else view[...]
                            read_time += time.monotonic() - began
                            digest_tensor(block, raw_hash)
                            began = time.monotonic()
                            converted = block.to(dtype=torch.float16)
                            cast_time += time.monotonic() - began
                            digest_tensor(converted, half_hash)
                            del block, converted
                    rows[key] = {"shard": shard, "shape": shape, "dtype": dtype,
                                 "data_offsets": entry["data_offsets"], "bf16_sha256": raw_hash.hexdigest(),
                                 "fp16_sha256": half_hash.hexdigest()}
                    totals["read_seconds"] += read_time
                    totals["cast_seconds"] += cast_time
                del view
        if context is not None:
            verified.require_complete_trace()
            retained_hash = hashlib.sha256()
            digest_tensor(retained, retained_hash)
            require(retained_hash.hexdigest() == rows[EMBED]["fp16_sha256"], "retained embedding changed")
        require(len(rows) == COUNT and len(file_rows) == len(shards), "incomplete traversal")
        telemetry = verified.telemetry() if context is not None else None
        result = {"schema": "ct1-direct-cpu-reader-v1", "reader": args.worker,
                  "versions": version, "verification": verification, "verification_seconds": verify_seconds,
                  "files": file_rows, "tensors": rows, "timing": totals, "telemetry": telemetry,
                  "timing_note": "Read times cover slice/materialization calls; lazy oracle page faults during hashing are included only in elapsed_seconds. H2D is zero because no device transfer is performed.",
                  "host_before_verify": baseline, "host_before": before, "host_after": host(),
                  "overlap": {"embedding_retained_fp16": retained_hash.hexdigest(), "head_full_bf16_fp16": True,
                              "persistent_embed_bytes": retained.untyped_storage().nbytes(),
                              "max_managed_temporary_bytes": temporary_bytes + telemetry["buffer_bytes"],
                              "before_cast": overlap_before, "after_cast": overlap_after} if context else None,
                  "elapsed_seconds": time.monotonic() - started}
    finally:
        if context is not None:
            context.__exit__(*sys.exc_info())
    write_exclusive(args.output, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seconds", type=float, default=7200)
    parser.add_argument("--worker", choices=("oracle", "candidate"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(math.isfinite(args.seconds) and args.seconds > 0, "invalid deadline")
    snapshot = Path(args.snapshot).resolve(strict=True)
    supplied = Path(args.output)
    output = supplied.parent.resolve(strict=True) / supplied.name
    roots = [path / "data" / "processed" for path in (REPO, *REPO.parents)]
    require(supplied.name not in ("", ".", "..")
            and any(path.is_dir() and output.parent.is_relative_to(path.resolve())
                for path in roots), "output must be under data/processed")
    require(not snapshot.is_relative_to(output) and not output.is_relative_to(snapshot), "output overlaps snapshot")
    if args.worker:
        args.snapshot, args.output = snapshot, output
        os.environ.update(cpu_environment(output.parent))
        sys.dont_write_bytecode = True
        worker(args)
        return
    output.mkdir(mode=0o700)  # exclusive; never reuse or overwrite an output directory
    env = os.environ.copy()
    env.update(cpu_environment(output))
    subprocesses = {}
    for name in ("oracle", "candidate"):
        destination = output / (name + ".json")
        command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", name,
                   "--snapshot", str(snapshot), "--output", str(destination), "--seconds", str(args.seconds)]
        try:
            run = subprocess.run(command, cwd=REPO, env=env, capture_output=True, text=True,
                                 timeout=args.seconds, check=False)
            subprocesses[name] = {"returncode": run.returncode, "stderr": run.stderr[-16000:]}
            require(run.returncode == 0 and destination.is_file(), name + " subprocess failed")
        except (subprocess.TimeoutExpired, ValueError) as error:
            write_exclusive(output / "manifest.json", {"schema": "ct1-direct-cpu-parity-v1",
                "status": "ERROR", "error": str(error), "subprocesses": subprocesses,
                "scope": "CPU only; no production admission or change to 16 GiB gates"})
            raise
    oracle, candidate = (read_json(output / (name + ".json")) for name in ("oracle", "candidate"))
    mismatches = [key for key in sorted(set(oracle["tensors"]) | set(candidate["tensors"]))
                  if oracle["tensors"].get(key) != candidate["tensors"].get(key)]
    files_equal = oracle["files"] == candidate["files"]
    stats = candidate["telemetry"]["io"]
    expected_bytes = sum(file.stat().st_size for file in snapshot.glob("*.safetensors"))
    verify_bytes = sum(r["returned"] for r in stats["verify"].values())
    total_requested = sum(r["requested"] for part in stats.values() for r in part.values())
    limits = {"verify_exact_bytes": verify_bytes == expected_bytes,
              "requested_le_2_10x": total_requested * 100 <= expected_bytes * 210,
              "verify_le_360s": candidate["verification_seconds"] <= 360,
              "materialize_read_le_360s": candidate["timing"]["read_seconds"] <= 360,
              "transport_le_16_mib": candidate["telemetry"]["buffer_bytes"] <= 16 * 2**20,
              "temporary_storage_le_2_5_gib": candidate["overlap"]["max_managed_temporary_bytes"] <= 5 * 2**29}
    parity = not mismatches and files_equal and len(oracle["tensors"]) == len(candidate["tensors"]) == COUNT
    passed = parity and all(limits.values())
    write_exclusive(output / "manifest.json", {"schema": "ct1-direct-cpu-parity-v1",
        "status": "PASS" if passed else "FAIL", "tensor_count": COUNT, "mismatched_keys": mismatches,
        "file_metadata_keys_offsets_accounting_match": files_equal, "subprocesses": subprocesses,
        "tensor_parity_passed": parity, "limits": limits,
        "read_requests_bytes": total_requested, "shard_bytes": expected_bytes,
        "receipts": {name + ".json": hashlib.sha256((output / (name + ".json")).read_bytes()).hexdigest()
                     for name in ("oracle", "candidate")},
        "scope": "CPU parity and host observations only; no production admission or change to 16 GiB gates",
        "model_inference": False, "gpu_operations": False})
    require(passed, "checkpoint parity or CPU resource limit failed; see manifest.json")


def cpu_environment(output):
    return {"TEMP": str(output), "TMP": str(output), "TMPDIR": str(output),
            "PYTHONDONTWRITEBYTECODE": "1", "HF_HOME": str(output / "hf-cache"),
            "XDG_CACHE_HOME": str(output / "cache"), "CUDA_VISIBLE_DEVICES": "",
            "HF_HUB_OFFLINE": "1"}


if __name__ == "__main__":
    main()
