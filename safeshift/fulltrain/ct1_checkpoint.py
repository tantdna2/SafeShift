"""CT1-only, checked disk staging and a bounded comparison of read paths."""

import hashlib
import mmap
import os
from pathlib import Path
import re
import shutil
import time

from safeshift.candidates.source import require, snapshot_stat
from safeshift.data.saved_reports import strict_json
from safeshift.pilot.artifacts import safe, write
from . import ct1_run, memory, qwen

MIB = 2**20
STAGE_SECONDS = 600
IO_SECONDS = 30
LOAD_SECONDS = 900
SYNC_BYTES = 64 * MIB
DISK_MARGIN = 2**31
SAMPLE_BYTES = 4 * MIB
STAGE_RECORD = "checkpoint-stage.json"


def mount_details(path, mountinfo=Path("/proc/self/mountinfo")):
    target = Path(path).resolve()
    matches = []
    for line in mountinfo.read_text().splitlines():
        before, after = line.split(" - ", 1)
        fields = before.split()
        mountpoint = Path(re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), fields[4]))
        if target.is_relative_to(mountpoint):
            matches.append((len(mountpoint.parts), {"mountpoint": str(mountpoint),
                            "filesystem": after.split()[0], "mount_device": fields[2]}))
    require(matches, "CT1_MOUNT_UNOBSERVED")
    result = max(reversed(matches), key=lambda x: x[0])[1]
    result["device"] = target.stat().st_dev
    return result


def capacity(source, scratch, output, total, budgets):
    mounts = {name: mount_details(path) for name, path in
              (("input", source), ("scratch", scratch), ("output", output))}
    require(mounts["scratch"]["filesystem"] not in ("tmpfs", "ramfs", "devtmpfs", "hugetlbfs"),
            "CT1_CHECKPOINT_SCRATCH_NOT_DISK")
    require(scratch.stat().st_dev != source.stat().st_dev or
            mounts["scratch"]["mountpoint"] != mounts["input"]["mountpoint"],
            "CT1_CHECKPOINT_SCRATCH_IS_INPUT_MOUNT")
    scratch_free = shutil.disk_usage(scratch).free
    output_free = shutil.disk_usage(output).free
    output_floor = budgets["free_output_mib"] * MIB
    needed = total + DISK_MARGIN + budgets["free_scratch_mib"] * MIB
    if scratch.stat().st_dev == output.stat().st_dev:
        needed += output_floor
    require(scratch_free >= needed and output_free >= output_floor, "CT1_CHECKPOINT_STAGE_DISK")
    return {"mounts": mounts, "snapshot_bytes": total, "scratch_free_bytes": scratch_free,
            "scratch_required_bytes": needed, "output_free_bytes": output_free}


class _DiskCopy:
    def __init__(self, fd, deadline, advice_errors):
        self.fd, self.deadline, self.advice_errors = fd, deadline, advice_errors
        self.written = self.synced = 0

    def write(self, block):
        original = len(block)
        remaining = memoryview(block)
        while remaining:
            memory.check_deadline(self.deadline)
            written = os.write(self.fd, remaining)
            require(written > 0, "CT1_CHECKPOINT_STAGE_SHORT_WRITE")
            self.written += written
            remaining = remaining[written:]
        if self.written - self.synced >= SYNC_BYTES:
            self.sync()
        return original

    def sync(self):
        if self.written == self.synced:
            return
        memory.check_deadline(self.deadline)
        getattr(os, "fdatasync", os.fsync)(self.fd)
        if hasattr(os, "posix_fadvise") and hasattr(os, "POSIX_FADV_DONTNEED") and not self.advice_errors:
            # Keep the last partial page untouched. Only the job-owned,
            # successfully written and synced range is eligible for advice.
            page = os.sysconf("SC_PAGE_SIZE")
            start = self.synced - self.synced % page
            length = self.written - self.written % page - start
            try:
                if length:
                    os.posix_fadvise(self.fd, start, length, os.POSIX_FADV_DONTNEED)
            except OSError as error:
                self.advice_errors.append(error.errno)
        self.synced = self.written
        memory.check_deadline(self.deadline)


def _stage_root(scratch, revision, evidence):
    owned = strict_json(ct1_run.read_controller_record(evidence, "scratch-ownership.json"))
    info = snapshot_stat(scratch, directory=True)
    require(owned == {"device": info.st_dev, "inode": info.st_ino}, "CT1_CHECKPOINT_SCRATCH_OWNERSHIP")
    return safe(scratch, "checkpoint-stage/" + revision)


def stage(source, scratch, output, evidence, repo, budgets, deadline):
    """Read the Input once, then verify the exact files the loader will open."""
    lock = qwen.reference(repo)
    rows = lock["snapshot_files"]
    staged = _stage_root(scratch, lock["model"]["revision"], evidence)
    floor = budgets["free_ram_mib"] * MIB
    memory.ct1_ram_gate(evidence, "before-checkpoint-stage-ram-gate", floor)
    write(evidence / "checkpoint-stage-storage.json",
          capacity(source, scratch, output, sum(row["size_bytes"] for row in rows), budgets))
    staged.parent.mkdir(mode=0o700)
    staged.mkdir(mode=0o700)
    progress = evidence / "checkpoint-stage"
    progress.mkdir()
    hints, receipts = [], {}
    started = time.monotonic()

    def copy(path, size):
        memory.check_deadline(deadline)
        dest = safe(staged, path.name)
        row = {"file": path.name, "size_bytes": size, "copy_started": time.monotonic()}
        number = len(receipts)
        write(progress / f"{number:02}-start.json", row)
        dest_hints = []
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
        fd = os.open(dest, flags, 0o600)
        try:
            stream = _DiskCopy(fd, deadline, dest_hints)
            digest = memory.stream_readonly_sha256(path, expected_size=size, deadline=deadline,
                                                  copy_to=stream, advice_errors=hints, advise_whole_file=False)
            stream.sync()
            require(stream.written == size and os.fstat(fd).st_size == size, "CT1_CHECKPOINT_STAGE_SIZE")
        finally:
            os.close(fd)
        dest.chmod(0o400)
        receipts[path.name] = row
        write(progress / f"{number:02}-copied.json", {**row, "copy_seconds": time.monotonic() - row["copy_started"],
                                                    "destination_advice_errors": dest_hints})
        return digest

    source_receipt = qwen.verify_snapshot(source, repo=repo, hash_reader=copy)
    if os.name == "posix":
        for directory in (staged, staged.parent, scratch):
            fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
    copied = time.monotonic()
    write(evidence / "checkpoint-stage-copy.json", {"seconds": copied - started, "source_advice_errors": hints,
                                                   "files": len(receipts)})
    identities = {}
    local_hints = []

    def readback(path, size):
        identity = memory.identity(snapshot_stat(path))
        digest = memory.stream_readonly_sha256(path, expected_size=size, deadline=deadline,
                                              expected_identity=identity, advice_errors=local_hints,
                                              advise_whole_file=False)
        identities[path.name] = list(identity)
        return digest

    verified = qwen.verify_snapshot(staged, repo=repo, hash_reader=readback)
    require(verified == source_receipt, "CT1_CHECKPOINT_STAGE_READBACK")
    write(evidence / "checkpoint-stage-storage-after.json",
          capacity(source, scratch, output, 0, budgets))
    memory.ct1_ram_gate(evidence, "after-checkpoint-stage-ram-gate", floor)
    write(evidence / STAGE_RECORD, {"status": "READBACK_VERIFIED", "checkpoint": verified,
                                    "identities": identities, "readback_seconds": time.monotonic() - copied,
                                    "readback_advice_errors": local_hints})


def verified_stage(scratch, evidence, repo):
    lock = qwen.reference(repo)
    staged = _stage_root(scratch, lock["model"]["revision"], evidence)
    snapshot_stat(staged, directory=True)
    receipt = strict_json(ct1_run.read_controller_record(evidence, STAGE_RECORD))
    expected = {row["path"]: row.get("sha256", row["expected_hash"]) for row in lock["snapshot_files"]}
    require(receipt["status"] == "READBACK_VERIFIED" and receipt["checkpoint"] == {
        "model": lock["model"], "files": expected, "weight_bytes_verified": True,
        "deserialized_weights": False,
    }, "CT1_CHECKPOINT_STAGE_RECEIPT")
    identities = {p.name: list(memory.identity(snapshot_stat(p))) for p in staged.iterdir()}
    require(identities == receipt["identities"] and set(identities) == set(expected), "CT1_CHECKPOINT_STAGE_CHANGED")
    return staged, receipt["checkpoint"]


def compare_reads(source, staged, evidence, deadline):
    """Four equal-work samples, with separate windows for buffered and mmap reads."""
    shard = "model-00001-of-00004.safetensors"
    digests = {}
    for number, (label, snapshot, mode, offset) in enumerate((
        ("input", source, "buffered", 0), ("scratch", staged, "mmap", SAMPLE_BYTES),
        ("scratch", staged, "buffered", 0), ("input", source, "mmap", SAMPLE_BYTES),
    )):
        started = time.monotonic()
        # A cooperative stop may omit unstarted samples. An interrupted I/O
        # call, which may have failed before recording evidence, cannot admit load.
        if started >= deadline - 2:
            write(evidence / ct1_run.IO_SUMMARY,
                  {"status": "CENSORED_BEFORE_SAMPLE", "completed": number})
            return
        record = {"location": label, "method": mode, "offset": offset, "bytes": SAMPLE_BYTES}
        write(evidence / f"checkpoint-io-{number}-start.json", record)
        with memory.readonly_fd(safe(snapshot, shard), None, deadline, advise_whole_file=False) as (fd, size, _):
            require(size >= offset + SAMPLE_BYTES, "CT1_CHECKPOINT_IO_RANGE")
            if mode == "mmap":
                with mmap.mmap(fd, SAMPLE_BYTES, access=mmap.ACCESS_READ, offset=offset) as view:
                    data = view[:]
            else:
                with os.fdopen(os.dup(fd), "rb") as stream:
                    stream.seek(offset)
                    data = stream.read(SAMPLE_BYTES)
            require(len(data) == SAMPLE_BYTES, "CT1_CHECKPOINT_IO_SHORT_READ")
            digest = hashlib.sha256(data).hexdigest()
        require(digests.setdefault(mode, digest) == digest, "CT1_CHECKPOINT_IO_BYTES_CHANGED")
        write(evidence / f"checkpoint-io-{number}-result.json",
              {**record, "sha256": digest, "seconds": time.monotonic() - started,
               "cache_state": "UNCONTROLLED_AFTER_STAGE"})
    write(evidence / ct1_run.IO_SUMMARY, {"status": "COMPLETE", "completed": 4})
