"""Small pinned CPU tokenizer checks, no weight bytes or network access."""
import json
from pathlib import Path

from ..one_click.artifacts import sha256
from .contract import MODELS


def verify(model, snapshot, repo):
    snapshot = Path(snapshot)
    if snapshot.name != MODELS[model]["revision"]:
        raise ValueError("PINNED_TOKENIZER_REVISION_REQUIRED")
    manifest = json.loads((Path(repo) / "notes/hnlo_t1_tokenizer_manifest_20261017.json").read_bytes())
    expected = next(r for r in manifest["models"] if r["model_key"] == model)
    if expected["revision"] != MODELS[model]["revision"] or expected["repo_id"] != MODELS[model]["id"]:
        raise ValueError("TOKENIZER_MANIFEST_IDENTITY_CHANGED")
    for row in expected["files"]:
        target = snapshot / row["path"]
        # HF blob symlinks may point only within this snapshot's cache repository.
        if not target.resolve().is_relative_to(snapshot.parent.parent.resolve()):
            raise ValueError("TOKENIZER_FILE_ESCAPE")
        if target.stat().st_size != row["size_bytes"] or sha256(target) != row["sha256"]:
            raise ValueError("PINNED_TOKENIZER_BYTES_CHANGED")
    return expected["files"]
