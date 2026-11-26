"""Bounded V2 RAM observations and advisory reads of this run's owned venv.

No shared-cache deletion, GC, threshold change or experimental authority.
"""
import os
import hashlib
from pathlib import Path
import stat
import time

from safeshift.candidates.source import require
from safeshift.fulltrain import environment
from safeshift.pilot.artifacts import write, safe


def stream_checkpoint_file(path, *, expected_size, deadline, observations, chunk_bytes=8 * 2**20):
    """Hash actual bytes once, advising only already-read ranges on this RO fd.

    No Input write/fsync, mmap, global cache control, hash substitution or RAM
    accounting adjustment. The final unchanged resource gate proves headroom.
    """
    from safeshift.candidates.source import snapshot_stat
    require(hasattr(os, "posix_fadvise"), "CHECKPOINT_ADVICE_REQUIRES_POSIX")
    require(type(expected_size) is int and 0 < expected_size <= 16 * 2**30, "CHECKPOINT_SIZE_BOUND")
    page = os.sysconf("SC_PAGESIZE")
    require(type(chunk_bytes) is int and page <= chunk_bytes <= 8 * 2**20
            and chunk_bytes % page == 0, "CHECKPOINT_CHUNK_BOUND")
    path = Path(path)
    for parent in (path.parent, *path.parent.parents):
        snapshot_stat(parent, directory=True)
    before = snapshot_stat(path)
    require(before.st_size == expected_size, "CHECKPOINT_EXPECTED_SIZE")
    def identity(info):
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    count, advised, chunks, hashed = 0, 0, 0, hashlib.sha256()
    started = time.monotonic()
    try:
        require(identity(os.fstat(fd)) == identity(before), "CHECKPOINT_OPEN_CHANGED")
        # Disables readahead on this descriptor; contiguous bounded reads remain.
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_RANDOM)
        while count < expected_size:
            require(time.monotonic() < deadline, "CHECKPOINT_HASH_DEADLINE")
            block = os.read(fd, min(chunk_bytes, expected_size - count))
            require(bool(block), "CHECKPOINT_SHORT_READ")
            hashed.update(block)
            count += len(block)
            chunks += 1
            # Short reads are legal. Only release fully consumed aligned pages.
            end = count - count % page
            if end > advised:
                os.posix_fadvise(fd, advised, end - advised, os.POSIX_FADV_DONTNEED)
                advised = end
        require(os.read(fd, 1) == b"", "CHECKPOINT_GREW")
        require(identity(os.fstat(fd)) == identity(before)
                and identity(snapshot_stat(path)) == identity(before), "CHECKPOINT_CHANGED_DURING_HASH")
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        checksum = hashed.hexdigest()
        observations.append({"file": path.name, "bytes_hashed": count, "sha256": checksum,
            "chunks": chunks, "chunk_bound": chunk_bytes, "advised_aligned_bytes": advised,
            "seconds": time.monotonic() - started, "descriptor_identity_unchanged": True,
            "method": "READONLY_SHA256_RANDOM_DONTNEED", "effect": "ADVISORY_NOT_RAM_PROOF"})
        return checksum
    finally:
        os.close(fd)


def verify_checkpoint(weights, key, out, name, deadline):
    from safeshift.candidates.loading import verify_weights
    from safeshift.candidates.source import LOCK
    from safeshift.pilot.artifacts import read
    require(key == "internvl35", "V2_CHECKPOINT_MODEL_ONLY")
    locked = read(LOCK.with_name("checkpoint_metadata_lock.json"))[key]
    rows = []
    write(out / (name + "-memory-before.json"), snapshot())
    error = None
    try:
        def reader(path):
            return stream_checkpoint_file(path, expected_size=locked["weights"][path.name]["size"],
                deadline=deadline, observations=rows)
        return verify_weights(weights, key, hash_reader=reader)
    except BaseException as failure:
        error = type(failure).__name__
        raise
    finally:
        write(out / (name + ".json"), {"files": rows, "error": error,
            "status": "ACTUAL_BYTES_VERIFIED" if error is None else "FAIL",
            "weights_modified": False, "ram_floor_changed": False})
        write(out / (name + "-memory-after.json"), snapshot())


def snapshot(proc=Path("/proc"), cgroup=Path("/sys/fs/cgroup")):
    observed = {"schema": "internvl-v2-memory-v1", "pid": os.getpid(),
                "monotonic": time.monotonic(), "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"), "errors": []}
    def text(path):
        try:
            with path.open("r", encoding="utf8") as stream:
                value = stream.read(65537)
            require(len(value) <= 65536, "MEMORY_OBSERVATION_BOUND")
            return value
        except (OSError, ValueError) as error:
            observed["errors"].append({"file": path.name, "type": type(error).__name__})
            return ""
    try:
        observed["gate_memory"] = environment.host_memory(proc / "meminfo", cgroup)
    except (OSError, ValueError, KeyError) as error:
        observed["gate_memory"] = None
        observed["errors"].append({"file": "gate_memory", "type": type(error).__name__})
    observed["cgroup"] = {}
    for name in ("memory.current", "memory.max", "memory.peak", "memory.stat", "memory.events"):
        if name == "memory.peak" and not (cgroup / name).is_file():
            observed["optional_unavailable"] = [name]
            continue
        value = text(cgroup / name)
        if not value:
            continue
        try:
            if name in ("memory.stat", "memory.events"):
                observed["cgroup"][name] = {k: int(v) for k, v in (line.split() for line in value.splitlines())}
            else:
                observed["cgroup"][name] = value.strip() if value.strip() == "max" else int(value)
        except ValueError:
            observed["errors"].append({"file": name, "type": "ValueError"})
    observed["process"] = {}
    for name in ("status", "smaps_rollup"):
        value = text(proc / "self" / name)
        observed["process"][name] = {k: int(rest.split()[0]) * 1024
            for line in value.splitlines() if ":" in line for k, rest in [line.split(":", 1)]
            if rest.strip().endswith("kB") and rest.split()[0].isdigit()}
    cg = observed["cgroup"]
    stats = cg.get("memory.stat", {})
    if (not all(k in cg for k in ("memory.current", "memory.max", "memory.events"))
            or not all(type(stats.get(k)) is int and stats[k] >= 0 for k in ("anon", "file"))
            or type(observed["process"]["status"].get("VmRSS")) is not int):
        observed["errors"].append({"file": "required_fields", "type": "MISSING_OR_INVALID_MEMORY_FIELDS"})
    observed["status"] = "OBSERVED" if not observed["errors"] else "INCOMPLETE"
    return observed


def resource_check(out, name, budgets, scratch):
    """Save a real observation before the unchanged gate, and after any failure.

    The gate retains its own fresh reads. Snapshots are near-sampled observations,
    not a fabricated exact value for an intervening failed read.
    """
    before = snapshot()
    write(out / (name + "-memory-before.json"), before)
    try:
        require(before["status"] == "OBSERVED", "MEMORY_DIAGNOSTICS_INCOMPLETE")
        return environment.resources("internvl35", budgets, scratch, out)
    except BaseException as error:
        after = snapshot()
        after["failure_type"] = type(error).__name__
        write(out / (name + "-memory-failure.json"), after)
        raise


def advise_owned_venv(scratch, prefix, *, max_entries=100000):
    """DONTNEED is a hint for clean pages, never proof of recovered headroom.

    Require the actual worker prefix to be this scratch's copied venv. Never
    visit Inputs, another runtime, aliases, hard links or writable shared caches.
    A bounded scan or syscall failure remains explicit and prevents a PASS claim.
    """
    scratch, prefix = Path(scratch), Path(prefix)
    root = scratch / "venv3119"
    require(root.resolve() == prefix.resolve() and root.is_dir(), "ADVICE_OWNED_WORKER_VENV_ONLY")
    require(not any(p.is_symlink() for p in (root, *root.parents)), "ADVICE_ROOT_ALIAS")
    require(hasattr(os, "posix_fadvise"), "ADVICE_REQUIRES_POSIX")
    require(type(max_entries) is int and 0 < max_entries <= 100000, "ADVICE_BOUND")
    todo, visited, files, total = [root / "lib"], 0, 0, 0
    while todo:
        directory = todo.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                visited += 1
                require(visited <= max_entries, "ADVICE_SCAN_LIMIT")
                path = safe(root, Path(entry.path).relative_to(root).as_posix())
                info = path.lstat()
                require(not stat.S_ISLNK(info.st_mode), "ADVICE_FILE_ALIAS")
                if stat.S_ISDIR(info.st_mode):
                    todo.append(path)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size >= 8 * 2**20:
                    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    try:
                        actual = os.fstat(descriptor)
                        require(actual.st_ino == info.st_ino and actual.st_dev == info.st_dev
                                and actual.st_nlink == 1 and stat.S_ISREG(actual.st_mode), "ADVICE_FILE_CHANGED")
                        os.posix_fadvise(descriptor, 0, 0, os.POSIX_FADV_DONTNEED)
                        files += 1
                        total += actual.st_size
                    finally:
                        os.close(descriptor)
    return {"method": "POSIX_FADV_DONTNEED_OWNED_VENV_LIB_ONLY", "entries": visited,
            "advised_files": files, "advised_bytes": total, "deleted_files": 0,
            "effect": "ADVISORY_NOT_RAM_PROOF", "scan_complete": True}
