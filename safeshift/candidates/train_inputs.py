"""Bounded Candidate160 mounts, including Kaggle saved Notebook Outputs.

The historical pilot discovery contract is deliberately unchanged.
"""
from pathlib import Path

from safeshift.pilot.artifacts import relative, safe, read
from .source import require
from .train_contract import model


def mounts(inputs, limit=512):
    inputs = Path(inputs)
    # Check all ancestors, including a symlink used as the input root.
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
                    for p in (inputs, *inputs.parents)), "INPUT_ROOT_ALIAS")
    visited = 0
    def directories(parent):
        nonlocal visited
        result = []
        for entry in parent.iterdir():
            visited += 1
            require(visited <= limit, "DISCOVERY_BOUND")
            checked = safe(inputs, entry.relative_to(inputs).as_posix())
            if checked.is_dir():
                result.append(checked)
        return sorted(result)
    result = []
    for mount in directories(inputs):
        result.append(mount)
        if mount.name in ("datasets", "notebooks"):
            for account in directories(mount):
                result.extend(directories(account))
    return result


def discover(inputs, filename, limit=512):
    relative(filename)
    require("/" not in filename, "MARKER_BASENAME_REQUIRED")
    found = []
    for mount in mounts(inputs, limit):
        for prefix in ("", "safeshift-pilot-input/"):
            candidate = safe(inputs, (mount.relative_to(inputs) / (prefix + filename)).as_posix())
            if candidate.exists():
                require(candidate.is_file(), "MARKER_REGULAR_FILE_REQUIRED")
                # Historical evidence carries a copy of the manifest, not images.
                # Attaching a direct run directory must not create a second bundle.
                if filename == "pilot_manifest.json" and safe(candidate.parent, "owner_execution.json").is_file():
                    continue
                found.append(candidate)
    require(len(found) == 1, f"UNIQUE_{filename}_REQUIRED_FOUND_{len(found)}")
    return found[0]


def checkpoint(inputs, key):
    marker = discover(inputs, f"candidate_checkpoint_{key}.json")
    require(marker.stat().st_size <= 16384, "CHECKPOINT_MARKER_SIZE_BOUND")
    require(read(marker) == {"schema": "safeshift-candidate160-checkpoint-v1", "model": model(key)},
            "OFFICIAL_CHECKPOINT_MARKER")
    weights = safe(marker.parent, "weights")
    source = safe(marker.parent, "source/" + model(key)["revision"])
    require(weights.is_dir() and source.is_dir(), "CHECKPOINT_SOURCE_AND_WEIGHTS_REQUIRED")
    return marker, source, weights
