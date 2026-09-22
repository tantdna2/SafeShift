"""Exclusive local evidence storage under repository-relative data/processed/."""

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

from .contracts import CallResult, RawReference


def _write_new(path: Path, content: bytes):
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


class FileRawStore:
    """Never overwrite an attempt, including an interrupted/partial write.

    Retrying requires a new call_id. Root is application-supplied, never taken
    from model output. The writer assumes a trusted local filesystem (no hostile
    concurrent changes to directory links). No input media are opened here.
    """

    def __init__(self, repo: Path, artifact_root: str = "data/processed/local_runs"):
        self.repo = repo.resolve()
        text = str(artifact_root).replace("\\", "/")
        relative = PurePosixPath(text)
        if (relative.is_absolute() or PureWindowsPath(text).drive or ":" in text
                or ".." in relative.parts or relative.parts[:2] != ("data", "processed")):
            raise ValueError("artifact root must be relative and under data/processed/")
        self.root = self.repo / relative
        self._check_path(self.root)

    def _check_path(self, path: Path):
        resolved = path.resolve()
        # Check against the lexical repository path, not a possibly aliased data root.
        if not resolved.is_relative_to(self.repo / "data" / "processed"):
            raise ValueError("artifact path escapes repository data/processed/")
        current = path
        while current != self.repo:
            if current.is_symlink() or current.resolve() != current:
                raise ValueError("artifact paths must not contain symlink/junction aliases")
            current = current.parent

    def _directory(self, provenance: dict) -> Path:
        # Hash opaque identifiers rather than treating sample IDs as paths.
        key = json.dumps([provenance[k] for k in ("run_id", "sample_id", "call_id")],
                         ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        path = self.root / hashlib.sha256(key).hexdigest()
        self._check_path(path)
        return path

    def preserve(self, raw: bytes, provenance: dict) -> RawReference:
        if type(raw) is not bytes:
            raise TypeError("raw output must be bytes")
        directory = self._directory(provenance)
        reference = RawReference((directory / "response.raw").relative_to(self.repo).as_posix(),
                                 hashlib.sha256(raw).hexdigest(), len(raw))
        metadata = json.dumps({**provenance, "raw_output": asdict(reference)},
                              ensure_ascii=False, indent=2, allow_nan=False).encode("utf-8")
        directory.mkdir(parents=True, exist_ok=False)
        _write_new(directory / "response.raw", raw)
        _write_new(directory / "metadata.json", metadata)
        return reference

    def save_result(self, result: CallResult) -> str:
        """Explicitly persist the returned result without rewriting raw metadata.

        Also supports calls that failed before producing any bytes. An I/O error
        propagates to the caller; it must never be reported as successful saving.
        """
        content = json.dumps(asdict(result), ensure_ascii=False, indent=2,
                             allow_nan=False).encode("utf-8")
        directory = self._directory(result.provenance)
        if result.raw_output is None:
            directory.mkdir(parents=True, exist_ok=False)
        path = directory / "result.json"
        _write_new(path, content)
        return path.relative_to(self.repo).as_posix()
