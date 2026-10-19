"""Preserve torn bytes; a custody hash does not certify capture correctness."""
from pathlib import Path
from safeshift.pa3.native.journal import Journal, no_alias
from ..one_click.artifacts import sha256


def inventory(root):
    result = {}
    for p in sorted(Path(root).rglob("*")):
        no_alias(p)
        if p.is_file():
            result[p.relative_to(root).as_posix()] = {"size_bytes": p.stat().st_size, "sha256": sha256(p)}
    return result


def seal(root):
    files = inventory(root)
    j = Journal(Path(root) / "custody", create=True)
    j.write("files", files)
    j.seal()


def verify(root):
    j = Journal(Path(root) / "custody")
    if not j.verify():
        raise ValueError("RAW_CUSTODY_SEAL_REQUIRED_BEFORE_REPLAY")
    actual = {k: v for k, v in inventory(root).items() if not k.startswith("custody/")}
    if actual != j.read("files"):
        raise ValueError("RAW_CUSTODY_CHANGED")
