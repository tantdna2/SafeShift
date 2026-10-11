"""PA3 native append-only journal; SHA-256 is integrity, not authenticity."""

import os
import re
import tarfile
from pathlib import Path

from safeshift.protocol.schema import strict_json
from ..artifacts import json_bytes, receipt, unpack


def safe_relative(value):
    if (type(value) is not str or not value or "\\" in value or ":" in value
            or value.startswith("/") or any(p in ("", ".", "..") for p in value.split("/"))):
        raise ValueError("CANONICAL_RELATIVE_PATH_REQUIRED")
    return value


def no_alias(path):
    path = Path(path).absolute()
    if any(p.resolve() != p.absolute() for p in (path, *path.parents)):
        raise ValueError("JOURNAL_ALIAS_FORBIDDEN")
    return path


def run_path(repo, run_id):
    if type(run_id) is not str or not re.fullmatch(r"pa3-qwen-[a-z0-9][a-z0-9_-]{0,63}", run_id):
        raise ValueError("PA3_UNIQUE_RUN_ID_REQUIRED")
    return no_alias(Path(repo) / "data/processed/pa3_qwen" / run_id)


class Journal:
    def __init__(self, root, *, create=False):
        self.root = no_alias(root)
        if create:
            self.root.mkdir(parents=True, exist_ok=False)

    def path(self, name):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", name):
            raise ValueError("JOURNAL_NAME_REQUIRED")
        return no_alias(self.root / (name + ".json"))

    def write(self, name, value):
        if self.path("seal").exists():
            raise ValueError("SEALED_JOURNAL_IMMUTABLE")
        path = self.path(name)
        side = no_alias(path.with_suffix(".sha256.json"))
        if path.exists() or side.exists():
            raise FileExistsError("NO_OVERWRITE_OR_RETRY:" + name)
        data = json_bytes(value)
        for target, payload in ((path, data), (side, json_bytes(receipt(data)))):
            with target.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        return self.read(name)

    def read(self, name):
        path = self.path(name)
        data = path.read_bytes()
        proof = strict_json(no_alias(path.with_suffix(".sha256.json")).read_bytes())
        if receipt(data) != proof:
            raise ValueError("PA3_CHECKSUM_MISMATCH:" + name)
        return unpack(strict_json(data))

    def exists(self, name):
        path = self.path(name)
        a, b = path.exists(), no_alias(path.with_suffix(".sha256.json")).exists()
        if a != b:
            raise ValueError("TORN_WRITE:" + name)
        return a

    def inventory(self):
        names = {p.name for p in self.root.iterdir()}
        result = {}
        for filename in sorted(names):
            if filename.endswith(".sha256.json") or filename == "seal.json":
                continue
            if not filename.endswith(".json"):
                raise ValueError("UNEXPECTED_JOURNAL_FILE")
            name = filename[:-5]
            self.read(name)
            result[name] = receipt(self.path(name).read_bytes())
        expected = {n + ext for n in result for ext in (".json", ".sha256.json")}
        if self.exists("seal"):
            expected |= {"seal.json", "seal.sha256.json"}
        if names != expected:
            raise ValueError("JOURNAL_INVENTORY_MISMATCH")
        return result

    def seal(self):
        self.write("seal", self.inventory())

    def verify(self):
        inventory = self.inventory()
        sealed = self.exists("seal")
        if sealed and self.read("seal") != inventory:
            raise ValueError("SEAL_MISMATCH")
        return sealed

    def package(self):
        # Even a torn journal is retained as failure evidence, never repaired.
        archive = no_alias(self.root.with_suffix(".tar.gz"))
        with tarfile.open(archive, "x:gz") as stream:
            for path in sorted(self.root.iterdir()):
                no_alias(path)
                if not path.is_file():
                    raise ValueError("UNEXPECTED_JOURNAL_DIRECTORY")
                stream.add(path, arcname=self.root.name + "/" + path.name, recursive=False)
        from safeshift.ls1.artifacts import digest
        side = no_alias(archive.with_suffix(".sha256.json"))
        with side.open("xb") as stream:
            stream.write(json_bytes({"archive": archive.name, "sha256": digest(archive),
                                     "size_bytes": archive.stat().st_size}))
        return archive
