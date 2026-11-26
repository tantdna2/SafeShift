"""Read-only Issue173 byte checks. No model imports, download or execution grant."""
import hashlib
import json
import math
from pathlib import Path
import struct

from safeshift.candidates.source import ROOT, require, snapshot_stat, verify_snapshot
from safeshift.candidates.train_contract import model
from safeshift.candidates.fulltrain import cohort, validate_cohort
from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest

DTYPES = {"F64": 8, "F32": 4, "F16": 2, "BF16": 2, "I64": 8,
          "I32": 4, "I16": 2, "I8": 1, "U8": 1, "BOOL": 1}


def pairs(items):
    result = {}
    for k, v in items:
        require(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def safetensors_header(path, expected_names):
    """Validate untrusted header, shape/byte spans and exact index membership.

    Reads at most 8 MiB, allocates no tensors and never imports safetensors/torch.
    The full file SHA is checked separately against the immutable public lock.
    """
    info = snapshot_stat(path)
    with Path(path).open("rb") as stream:
        prefix = stream.read(8)
        require(len(prefix) == 8, "SAFETENSORS_TRUNCATED_PREFIX")
        size = struct.unpack("<Q", prefix)[0]
        require(2 <= size <= 8 * 2**20 and 8 + size <= info.st_size, "SAFETENSORS_HEADER_BOUND")
        header = json.loads(stream.read(size), object_pairs_hook=pairs)
    require(type(header) is dict, "SAFETENSORS_HEADER_OBJECT")
    metadata = header.pop("__metadata__", {})
    require(type(metadata) is dict and all(type(k) is str and type(v) is str for k,v in metadata.items()),
            "SAFETENSORS_METADATA")
    require(set(header) == set(expected_names), "SAFETENSORS_INDEX_MEMBERSHIP")
    spans = []
    for row in header.values():
        require(type(row) is dict and set(row) == {"dtype", "shape", "data_offsets"}, "SAFETENSORS_TENSOR_FIELDS")
        require(row["dtype"] in DTYPES and type(row["shape"]) is list
                and len(row["shape"]) <= 16 and all(type(n) is int and 0 <= n <= 2**40 for n in row["shape"]),
                "SAFETENSORS_SHAPE_DTYPE")
        offsets = row["data_offsets"]
        require(type(offsets) is list and len(offsets) == 2
                and all(type(n) is int for n in offsets), "SAFETENSORS_OFFSETS")
        start, end = offsets
        require(0 <= start <= end <= info.st_size - 8 - size
                and end-start == math.prod(row["shape"]) * DTYPES[row["dtype"]], "SAFETENSORS_TENSOR_BYTES")
        spans.append((start, end))
    position = 0
    for start, end in sorted(spans):
        require(start == position, "SAFETENSORS_GAP_OR_OVERLAP")
        position = end
    require(position == info.st_size - 8 - size, "SAFETENSORS_TRAILING_OR_MISSING_DATA")
    return {"tensors": len(header), "tensor_bytes": position, "header_bytes": size}


def checkpoint_spec(key, repo=ROOT):
    if key == "qwen3":
        value = read(Path(repo)/"configs/fulltrain/qwen3.json")
        files = {r["path"]: {"sha256": r.get("sha256", r["expected_hash"]), "size": r["size_bytes"]}
                 for r in value["snapshot_files"]}
        return {"model": value["model"], "files": files,
                "index": "model.safetensors.index.json", "tensor_count": None}
    require(key in ("internvl35", "minicpm4"), "UNKNOWN_MODEL")
    value = read(Path(repo)/"configs/cpu_g2_g3/checkpoint_metadata_lock.json")[key]
    return {"model": {k:value[k] for k in ("id", "revision")},
            "files": {**value["weights"], value["index"]["filename"]: value["index"]},
            "index": value["index"]["filename"], "tensor_count": value["index"]["tensor_count"]}


def verify_files(root, spec):
    root = Path(root)
    snapshot_stat(root, directory=True)
    require({p.name for p in root.iterdir()} == set(spec["files"]), "CHECKPOINT_EXACT_INVENTORY")
    checked = {}
    # Check size before streaming and never copy a shard.
    for name, pin in spec["files"].items():
        p = safe(root, name)
        require(snapshot_stat(p).st_size == pin["size"], "CHECKPOINT_SIZE:" + name)
        actual = sha(p)
        require(actual == pin["sha256"], "CHECKPOINT_SHA256:" + name)
        checked[name] = {"size_bytes": pin["size"], "sha256": actual}
    index = read(safe(root, spec["index"]))
    wm = index["weight_map"]
    shards = {n for n in checked if n.endswith(".safetensors")}
    require(type(wm) is dict and wm and set(wm.values()) == shards, "CHECKPOINT_INDEX_SHARDS")
    require(spec["tensor_count"] is None or len(wm) == spec["tensor_count"], "CHECKPOINT_TENSOR_COUNT")
    headers = {name: safetensors_header(safe(root, name), {k for k,v in wm.items() if v == name}) for name in sorted(shards)}
    require(index["metadata"]["total_size"] == sum(r["tensor_bytes"] for r in headers.values()), "CHECKPOINT_TOTAL_TENSOR_BYTES")
    return {"status": "CHECKPOINT_BYTES_AND_HEADERS_PASS", "model": spec["model"], "files": checked,
            "headers": headers, "weights_loaded": False, "model_calls": 0}


def verify_peer(root, key):
    root = Path(root)
    marker = safe(root, f"candidate_checkpoint_{key}.json")
    require(snapshot_stat(marker).st_size <= 16384, "CHECKPOINT_MARKER_BOUND")
    require(read(marker) == {"schema": "safeshift-candidate160-checkpoint-v1", "model": model(key)}, "CHECKPOINT_MARKER")
    spec = verify_snapshot(safe(root, "source/" + model(key)["revision"]), key)
    result = verify_files(safe(root, "weights"), checkpoint_spec(key))
    result.update(marker_sha256=sha(marker), source_files=spec["files"])
    return result


def verify_qwen(root):
    root = Path(root)
    marker = safe(root, "QWEN3_MODEL_PROVISION_RESULT/qwen3_flat_snapshot_manifest.json")
    require(snapshot_stat(marker).st_size <= 128 * 1024, "QWEN_MANIFEST_BOUND")
    value = read(marker)
    spec = checkpoint_spec("qwen3")
    require(value["model_id"] == spec["model"]["id"] and value["revision"] == spec["model"]["revision"], "QWEN_MANIFEST_IDENTITY")
    expected = {n:{"size_bytes":r["size"], "sha256":r["sha256"]} for n,r in spec["files"].items()}
    rows = value["files"]
    require(len(rows) == len(expected) and {r["path"]:{k:r[k] for k in ("size_bytes", "sha256")} for r in rows} == expected,
            "QWEN_MANIFEST_INVENTORY")
    result = verify_files(safe(root, "QWEN3_MODEL_FLAT"), spec)
    result["marker_sha256"] = sha(marker)
    return result


def verify_train(master_path, image_root):
    """Use original locators; no image/GT copies, prints or reordering.

    Original-master validation reads existing schema labels solely for integrity;
    outputs contain only an ordered projection/hash, never GT or private IDs.
    The returned projection must be stored privately.
    """
    require(snapshot_stat(master_path).st_size <= 16 * 2**20, "MASTER_BOUND")
    raw = Path(master_path).read_bytes()
    projection = cohort(raw)  # original SHA before JSON/label schema integrity
    rows = validate_cohort(projection, digest(projection))
    originals = json.loads(raw)["samples"]
    mapping = []
    missing = changed = 0
    for row, original in zip(rows, originals):
        locator = original["image_locator"]
        require(locator.startswith("DATA_PATH/train/Annotations/"), "TRAIN_PATH_ONLY")
        path = safe(image_root, locator.removeprefix("DATA_PATH/"))
        if not path.is_file():
            missing += 1
        elif sha(path) != row["image_sha256"]:
            changed += 1
        mapping.append({**row, "image_locator": locator})
    require(missing == changed == 0, f"TRAIN_IMAGE_BYTES_MISSING_{missing}_CHANGED_{changed}")
    return {"status": "TRAIN_BYTES_PASS", "verified_images": len(rows), "missing": missing,
            "changed": changed, "duplicate_ids": 0, "master_sha256": hashlib.sha256(raw).hexdigest(),
            "projection_sha256": digest(projection), "mapping_sha256": digest(mapping),
            "decode": "NOT_RUN", "labels_exported": False}, projection, mapping


def storage_budget(free_bytes, download_bytes, *, temporary_bytes=0, reserve_bytes=2*2**30):
    require(all(type(v) is int and v >= 0 for v in (free_bytes, download_bytes, temporary_bytes, reserve_bytes)), "STORAGE_INTEGER_BYTES")
    require(free_bytes >= download_bytes + temporary_bytes + reserve_bytes, "INSUFFICIENT_DISK_FOR_DOWNLOAD_AND_TEMP")
    return {"free_bytes":free_bytes, "download_bytes":download_bytes, "temporary_bytes":temporary_bytes,
            "reserve_bytes":reserve_bytes}


def dispatch_smoke(*args, **kwargs):
    # Byte verification alone cannot confer final-source smoke admission.
    raise ValueError("SMOKE_NOT_IMPLEMENTED_OR_AUTHORIZED_BY_BYTE_RECEIPT")
