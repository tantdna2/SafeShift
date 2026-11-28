"""CT1 CPU prototype: verify pinned weights, then read them through the HF seam."""

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from hashlib import sha256
import math
import mmap
import os
from pathlib import Path
from threading import get_ident
import time
from unittest.mock import patch

from safeshift.candidates.source import require, snapshot_stat
from safeshift.data.saved_reports import strict_json
from . import memory, qwen

CHUNK = 8 * 2**20
MAX_HEADER = 2**20
MAX_TENSOR = 1244659712
MAX_TENSORS = 750


@dataclass(frozen=True)
class TensorRange:
    shape: tuple[int, ...]
    start: int
    end: int


@dataclass(frozen=True)
class Shard:
    path: Path
    fd: int
    size: int
    identity: tuple
    metadata: dict
    tensors: dict[str, TensorRange]


def _header(prefix, size):
    require(len(prefix) >= 8, "CT1_DIRECT_HEADER_SHORT")
    length = int.from_bytes(prefix[:8], "little")
    start = 8 + length
    require(0 < length <= MAX_HEADER and start <= len(prefix), "CT1_DIRECT_HEADER_SIZE")
    rows = strict_json(bytes(prefix[8:start]))
    require(isinstance(rows, dict), "CT1_DIRECT_HEADER_TYPE")
    metadata = rows.pop("__metadata__", None)
    require(isinstance(metadata, dict) and metadata.get("format") == "pt"
            and all(isinstance(v, str) for v in metadata.values()), "CT1_DIRECT_METADATA")
    require(0 < len(rows) <= MAX_TENSORS, "CT1_DIRECT_TENSOR_COUNT")
    tensors = {}
    for name, row in rows.items():
        require(isinstance(row, dict) and set(row) == {"dtype", "shape", "data_offsets"}
                and row["dtype"] == "BF16", "CT1_DIRECT_TENSOR_TYPE")
        shape, offsets = row["shape"], row["data_offsets"]
        require(isinstance(shape, list) and len(shape) <= 8
                and all(type(n) is int and 0 < n <= MAX_TENSOR // 2 for n in shape),
                "CT1_DIRECT_TENSOR_SHAPE")
        require(isinstance(offsets, list) and len(offsets) == 2
                and all(type(n) is int for n in offsets), "CT1_DIRECT_TENSOR_OFFSETS")
        lo, hi = offsets
        require(0 <= lo <= hi <= size - start and hi - lo == 2 * math.prod(shape)
                and hi - lo <= MAX_TENSOR, "CT1_DIRECT_TENSOR_RANGE")
        tensors[name] = TensorRange(tuple(shape), start + lo, start + hi)
    offset = start
    for row in sorted(tensors.values(), key=lambda row: (row.start, row.end)):
        require(offset == row.start, "CT1_DIRECT_TENSOR_COVERAGE")
        offset = row.end
    require(offset == size, "CT1_DIRECT_TENSOR_COVERAGE")
    return metadata, tensors


class VerifiedCheckpoint:
    """Own the same open weight descriptors from hashing through materialization."""

    def __init__(self, snapshot, repo, *, deadline):
        require(math.isfinite(deadline), "CT1_DIRECT_DEADLINE_REQUIRED")
        self.snapshot = Path(snapshot).absolute()
        self.repo = Path(repo)
        self.deadline = deadline
        self._stack = ExitStack()
        self._live = False
        self._used = False
        self._shards = {}
        self._handles = set()
        self._file_identities = {}
        self._io = {}
        self._reads = []
        self._materialized = set()
        self._owner = None
        self._opens = []
        self._phase = "verify"
        self._alignment = mmap.PAGESIZE
        self.receipt = None
        self.verify_seconds = None

    def __enter__(self):
        require(not self._used, "CT1_DIRECT_CONTEXT_REUSED")
        self._used = True
        self._owner = get_ident()
        require(hasattr(os, "O_DIRECT") and hasattr(os, "preadv")
                and CHUNK % self._alignment == 0, "CT1_DIRECT_IO_UNAVAILABLE")
        started = time.monotonic()
        try:
            self._buffer = self._stack.enter_context(mmap.mmap(-1, CHUNK))
            receipt = qwen.verify_snapshot(self.snapshot, repo=self.repo, hash_reader=self._verify_file,
                                           index_reader=self._read_verified_index)
            expected = {name: shard.path.name for shard in self._shards.values() for name in shard.tensors}
            require(sum(len(s.tensors) for s in self._shards.values()) == len(expected)
                    and expected == self._index["weight_map"], "CT1_DIRECT_INDEX_KEYS")
            self.check_identity()
            self.verify_seconds = time.monotonic() - started
            self.receipt = receipt
            self._phase = "materialize"
            self._live = True
            return self
        except BaseException:
            self._stack.close()
            raise

    def __exit__(self, *exc):
        for handle in tuple(self._handles):
            handle.close()
        self._live = False
        return self._stack.__exit__(*exc)

    def _stats(self, file):
        return self._io.setdefault((self._phase, file), {
            "calls": 0, "requested": 0, "returned": 0, "short": 0, "interrupted": 0, "io_seconds": 0.0,
        })

    @contextmanager
    def _span(self, fd, file, size, start, length):
        require(0 <= start < size and 0 < length <= min(CHUNK, size - start), "CT1_DIRECT_READ_RANGE")
        total = (length + self._alignment - 1) // self._alignment * self._alignment
        require(start % self._alignment == 0 and total <= CHUNK, "CT1_DIRECT_ALIGNMENT")
        stats = self._stats(file)
        filled = calls = 0
        with memoryview(self._buffer)[:total] as block:
            while filled < length:
                memory.check_deadline(self.deadline)
                need = total - filled
                require(calls < 32 and filled % self._alignment == 0, "CT1_DIRECT_PARTIAL_LIMIT")
                stats["calls"] += 1
                stats["requested"] += need
                calls += 1
                began = time.monotonic()
                try:
                    with block[filled:] as dest:
                        count = os.preadv(fd, [dest], start + filled)
                except InterruptedError:
                    stats["interrupted"] += 1
                    continue
                finally:
                    stats["io_seconds"] += time.monotonic() - began
                memory.check_deadline(self.deadline)
                require(0 < count <= min(need, size - start - filled), "CT1_DIRECT_EOF_OR_SHORT_READ")
                stats["returned"] += count
                if count < need:
                    stats["short"] += 1
                filled += count
            with block[:length] as result:
                yield result

    def _verify_file(self, path, size):
        before = memory.identity(snapshot_stat(path))
        self._file_identities[path] = before
        if not path.name.endswith(".safetensors"):
            if path.name == "model.safetensors.index.json":
                require(size <= MAX_HEADER, "CT1_DIRECT_INDEX_SIZE")
                with memory.readonly_fd(path, size, self.deadline, expected_identity=before,
                                        advise_whole_file=False) as (fd, _, _):
                    with os.fdopen(os.dup(fd), "rb") as stream:
                        self._index = stream.read(size + 1)
                require(len(self._index) == size, "CT1_DIRECT_INDEX_SHORT_READ")
                return sha256(self._index).hexdigest()
            return memory.stream_readonly_sha256(path, expected_size=size, deadline=self.deadline,
                                                 expected_identity=before, advise_whole_file=False)

        require(size >= 8, "CT1_DIRECT_SHARD_SIZE")
        fd, _, _ = self._stack.enter_context(memory.readonly_fd(
            path, size, self.deadline, expected_identity=before, direct=True, advise_whole_file=False))
        digest = sha256()
        for offset in range(0, size, CHUNK):
            with self._span(fd, path.name, size, offset, min(size - offset, CHUNK)) as block:
                digest.update(block)
                if offset == 0:
                    metadata, tensors = _header(block, size)
        self._shards[path] = Shard(path, fd, size, before, metadata, tensors)
        return digest.hexdigest()

    def _read_verified_index(self, path):
        require(memory.identity(snapshot_stat(path)) == self._file_identities[path], "CT1_DIRECT_INDEX_CHANGED")
        self._index = strict_json(self._index)
        return self._index

    def check_identity(self):
        memory.check_deadline(self.deadline)
        require(all(memory.identity(snapshot_stat(path)) == recorded
                    for path, recorded in self._file_identities.items()), "CT1_DIRECT_PATH_CHANGED")
        for shard in self._shards.values():
            self._check_shard(shard)

    @staticmethod
    def _check_shard(shard):
        require(memory.identity(os.fstat(shard.fd)) == shard.identity
                and memory.identity(snapshot_stat(shard.path)) == shard.identity, "CT1_DIRECT_SHARD_CHANGED")



    def _require_live(self):
        require(self._live and self._owner == get_ident(), "CT1_DIRECT_SESSION_CLOSED_OR_WRONG_THREAD")

    def index(self):
        self._require_live()
        return {"weight_map": dict(self._index["weight_map"]),
                "metadata": dict(self._index.get("metadata", {}))}

    def inventory(self):
        self._require_live()
        files = {}
        for shard in self._shards.values():
            origin = min(row.start for row in shard.tensors.values())
            files[shard.path.name] = {
                "metadata": dict(shard.metadata),
                "header_bytes": origin - 8,
                "tensors": {name: {
                    "dtype": "BF16", "shape": list(row.shape),
                    "data_offsets": [row.start - origin, row.end - origin],
                } for name, row in shard.tensors.items()},
            }
        return files

    def open(self, filename, framework="pt", device="cpu"):
        self._require_live()
        require(framework == "pt" and str(device) == "cpu", "CT1_DIRECT_FRAMEWORK_OR_DEVICE")
        path = Path(filename).absolute()
        require(path in self._shards, "CT1_DIRECT_SHARD_NOT_IN_VERIFIED_SET")
        shard = self._shards[path]
        self._check_shard(shard)
        require(len(self._opens) < 64, "CT1_DIRECT_OPEN_LIMIT")
        self._opens.append(shard.path.name)
        handle = _Handle(self, shard)
        self._handles.add(handle)
        return handle

    def _tensor(self, shard, name):
        import torch

        self._require_live()
        memory.check_deadline(self.deadline)
        key = (shard.path.name, name)
        require(key not in self._materialized and len(self._reads) < MAX_TENSORS,
                "CT1_DIRECT_MATERIALIZATION_LIMIT")
        self._check_shard(shard)
        item = shard.tensors[name]
        began = time.monotonic()
        payload = bytearray(item.end - item.start)
        cursor = item.start
        with memoryview(payload) as result:
            while cursor < item.end:
                memory.check_deadline(self.deadline)
                aligned = cursor - cursor % self._alignment
                skip = cursor - aligned
                length = min(CHUNK, item.end - aligned)
                with self._span(shard.fd, shard.path.name, shard.size, aligned, length) as block:
                    progress = length - skip
                    destination = cursor - item.start
                    result[destination:destination + progress] = block[skip:]
                cursor += progress
        self._check_shard(shard)
        # Storage is owned by the returned tensor through frombuffer. The
        # reusable mmap above is never exposed as live tensor storage.
        tensor = torch.frombuffer(payload, dtype=torch.bfloat16).reshape(item.shape)
        memory.check_deadline(self.deadline)
        self._materialized.add(key)
        self._reads.append({"shard": shard.path.name, "key": name, "payload_bytes": len(payload),
                            "seconds": time.monotonic() - began})
        return tensor

    def require_complete_trace(self):
        expected = {(shard.path.name, key) for shard in self._shards.values() for key in shard.tensors}
        require(self._materialized == expected, "CT1_DIRECT_TRACE_KEYS")
        self.check_identity()

    def telemetry(self):
        return {"alignment": self._alignment, "buffer_bytes": CHUNK, "verify_seconds": self.verify_seconds,
                "opens": list(self._opens), "tensors": list(self._reads),
                "io": {phase: {file: dict(stats) for (kind, file), stats in self._io.items() if kind == phase}
                       for phase in ("verify", "materialize")}}

    @contextmanager
    def install(self):
        """Patch only the pinned Transformers symbol in this CT1 worker."""
        import safetensors
        import transformers
        from transformers import modeling_utils

        self._require_live()
        require(transformers.__version__ == "4.57.1"
                and safetensors.__version__ == "0.6.2"
                and modeling_utils.safe_open is safetensors.safe_open, "CT1_DIRECT_HF_BINDING")
        source = Path(modeling_utils.__file__)
        require(memory.stream_readonly_sha256(source, deadline=self.deadline, advise_whole_file=False)
                == "bf1c6b2a43cf7c36fb79f37c981424dd6ae78eb863fcaa5d2a37e76c9828611d",
                "CT1_DIRECT_HF_SOURCE")
        require(os.environ.get("HF_ENABLE_PARALLEL_LOADING", "").upper() not in {"1", "ON", "YES", "TRUE"},
                "CT1_DIRECT_PARALLEL_DISABLED")
        try:
            with patch.object(modeling_utils, "safe_open", self.open):
                yield
            self.require_complete_trace()
        finally:
            for handle in tuple(self._handles):
                handle.close()


class _Handle:
    def __init__(self, checkpoint, shard):
        self._checkpoint = checkpoint
        self._shard = shard
        self._live = True

    def _require_live(self):
        require(self._live, "CT1_DIRECT_HANDLE_CLOSED")
        self._checkpoint._require_live()

    def __enter__(self):
        self._require_live()
        return self

    def close(self):
        self._live = False
        self._checkpoint._handles.discard(self)

    def __exit__(self, *exc):
        self.close()

    def metadata(self):
        self._require_live()
        return dict(self._shard.metadata)

    def keys(self):
        self._require_live()
        return sorted(self._shard.tensors)

    def get_slice(self, key):
        self._require_live()
        return _Slice(self, key, self._shard.tensors[key])

    def get_tensor(self, key):
        return self.get_slice(key)[...]


@dataclass(frozen=True)
class _Slice:
    handle: _Handle
    key: str
    item: TensorRange

    def get_dtype(self):
        self.handle._require_live()
        return "BF16"

    def get_shape(self):
        self.handle._require_live()
        return list(self.item.shape)

    def __getitem__(self, selection):
        require(selection is Ellipsis, "CT1_DIRECT_FULL_SLICE_REQUIRED")
        self.handle._require_live()
        return self.handle._checkpoint._tensor(self.handle._shard, self.key)
