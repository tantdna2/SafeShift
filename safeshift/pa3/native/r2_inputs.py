"""Unique hash-bound Kaggle Input discovery; never descend into TRAIN/TEST trees."""
import os
from pathlib import Path
from safeshift.ls1.artifacts import digest
from safeshift.protocol.schema import strict_json
from . import r2


def inventory(inputs):
    inputs = Path(inputs).absolute()
    files, datasets = [], []
    for root, dirs, names in os.walk(inputs, followlinks=False):
        root = Path(root)
        # Discover the wrapper only. No enumeration/reading inside DATA_PATH.
        if "DATA_PATH" in dirs and (root / "DATA_PATH/train/Annotations").is_dir():
            datasets.append(root)
        dirs[:] = [d for d in dirs if d.lower() not in {"data_path", "test"}
                   and not (root / d).is_symlink()]
        for name in names:
            path = root / name
            if not path.is_symlink() and path.resolve().is_relative_to(inputs.resolve()):
                files.append(path)
    return files, datasets


def unique(candidates, kind):
    candidates = list(candidates)
    if len(candidates) != 1:
        raise ValueError(f"R2_INPUT_{kind}_EXPECTED_ONE_FOUND_{len(candidates)}")
    return candidates[0]


def resolve(repo, inputs, shard, source_commit, source_bundle, bundle_hash):
    grant = r2.authority(repo, source_commit)["grant"]  # before scanning Inputs
    files, datasets = inventory(inputs)
    rel = lambda p: Path(p).relative_to(inputs).as_posix()
    by_hash = lambda candidates, sha, kind: unique((p for p in candidates if digest(p) == sha), kind)
    bundles = [p for p in files if p.suffix == ".bundle"]
    technical = by_hash(bundles, grant["technical_source_bundle_sha256"], "TECHNICAL_BUNDLE")
    seal = by_hash((p for p in files if p.name == "seal.json"), grant["technical_seal_sha256"], "TECHNICAL_SEAL")
    inv = by_hash((p for p in files if "runtime_inventory" in p.name and p.suffix == ".json"),
                  grant["runtime_inventory_sha256"], "RUNTIME_INVENTORY")
    entries = strict_json(inv.read_bytes())["files"]
    if len(entries) != 1:
        raise ValueError("R2_SINGLE_RUNTIME_ARCHIVE_REQUIRED")
    name, proof = next(iter(entries.items()))
    runtime = by_hash((p for p in files if p.name == name and p.stat().st_size == proof["size_bytes"]),
                      proof["sha256"], "RUNTIME_ARCHIVE")
    # Model candidate is only a locator; restore_model verifies every pinned byte.
    model = unique((p for p in files if "model" in p.name.lower()
                    and p.name.endswith((".tar", ".tar.gz", ".tgz"))), "MODEL_ARCHIVE")
    dataset = unique(datasets, "TRAIN_ROOT")
    if digest(source_bundle) != bundle_hash:
        raise ValueError("R2_SOURCE_BUNDLE_CHANGED")
    settings = {"mode": r2.MODE, "run_id": r2.run_id(shard), "shard_id": shard,
                "source_commit": source_commit, "source_bundle_input": rel(source_bundle),
                "source_bundle_sha256": bundle_hash, "runtime_site_packages": "",
                "model_input": rel(model), "runtime_input": rel(runtime),
                "runtime_inventory_input": rel(inv), "technical_source_bundle_input": rel(technical),
                "technical_run_input": rel(seal.parent), "dataset_input": rel(dataset),
                **{k: grant[k] for k in r2.HASHES},
                "inference_manifest_sha256": grant["shards"][shard]["inference_manifest_sha256"]}
    r2.require(settings, repo)
    return settings
