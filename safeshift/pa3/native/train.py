"""Full TRAIN preparation boundary. No grant in this Draft; TEST always denied."""
import hashlib
import re
from pathlib import Path

from safeshift.data.p2_execution import safe_path
from safeshift.ls1.artifacts import digest
from safeshift.ls1.experiment import open_sample
from safeshift.protocol.schema import strict_json
from . import access, preflight, seminar
from .journal import Journal, no_alias, run_path

BASE = "3a52b549d623bdb4b8b6753abe3adf116bbc6100"
AUTHORITY = "configs/pa3/full_train_authority.v1.json"
FULL = "data/manifests/pa3_full_train.v1.json"
MODE = "full-train"
SEED = "pa3-full-train-2026-10-13-v1"
COUNT = 3763
SIZES = (941, 941, 941, 940)
SCOPE = {**{k: access.TECHNICAL[k] for k in ("model", "revision", "precision", "attention", "gpu", "prompt", "method")},
         "mode": MODE, "split": "TRAIN", "max_images": COUNT, "batch_size": 1,
         "max_runs_per_shard": 1, "shard_sizes": list(SIZES), "retry": False, "test_access": False,
         "technical_source_commit": access.DIAGNOSTIC["technical_source_commit"]}
HASHES = ("full_manifest_sha256", "technical_seal_sha256", "technical_source_bundle_sha256", "runtime_inventory_sha256")


def run_id(shard):
    if type(shard) is not int or not 0 <= shard < 4:
        raise ValueError("EXACT_TRAIN_SHARD_0_TO_3_REQUIRED")
    return f"pa3-qwen-full-train-shard-{shard}"


def inference_path(shard):
    return f"data/manifests/pa3_full_train_shard{shard}.v1.json"


def order_key(sid):
    return hashlib.sha256((SEED + "|" + sid).encode()).hexdigest(), sid


def partition(rows):
    """Execution partitions only; include every original TRAIN ID, without exclusions."""
    ordered = sorted(rows, key=lambda r: order_key(r["sample_id"]))
    return [ordered[i::4] for i in range(4)]


def validate_samples(rows, count):
    if type(rows) is not list or len(rows) != count:
        raise ValueError("EXACT_TRAIN_COUNT_REQUIRED")
    for row in rows:
        if type(row) is not dict or set(row) != {"sample_id", "image_locator", "image_sha256"}:
            raise ValueError("GT_FREE_TRAIN_ROW_REQUIRED")
        sid, locator = row["sample_id"], row["image_locator"]
        match = seminar.LOCATOR.fullmatch(locator) if type(locator) is str else None
        if (type(sid) is not str or not seminar.SAMPLE_ID.fullmatch(sid) or not match or match.group(1) != sid
                or ("/Normal_data/" in locator) != ("-Level04-" in sid)
                or not re.fullmatch(r"[0-9a-f]{64}", row["image_sha256"])):
            raise ValueError("ORIGINAL_TRAIN_ID_PATH_HASH_REQUIRED")
    if len({r["sample_id"] for r in rows}) != count or len({r["image_locator"] for r in rows}) != count:
        raise ValueError("UNIQUE_TRAIN_IDS_AND_PATHS_REQUIRED")
    return rows


def validate_inference(value, shard):
    if (set(value) != {"schema", "split", "seed", "shard_id", "run_id", "samples"}
            or value["schema"] != "pa3-full-train-inference-v1" or value["split"] != "TRAIN"
            or value["seed"] != SEED or type(value["shard_id"]) is not int
            or value["shard_id"] != shard or value["run_id"] != run_id(shard)):
        raise ValueError("TRAIN_SHARD_SCHEMA")
    rows = validate_samples(value["samples"], SIZES[shard])
    if rows != sorted(rows, key=lambda r: order_key(r["sample_id"])):
        raise ValueError("TRAIN_ORDER_CHANGED")
    return rows


def validate_full(value, shards):
    if (value["schema"] != "pa3-full-train-v1" or value["split"] != "TRAIN" or value["seed"] != SEED
            or value["execution_authority"] is not False or len(shards) != 4):
        raise ValueError("FULL_TRAIN_SCHEMA")
    samples = value["samples"]
    projection = [{k: r[k] for k in ("sample_id", "image_locator", "image_sha256")} for r in samples]
    validate_samples(projection, COUNT)
    if samples != sorted(samples, key=lambda r: r["sample_id"]):
        raise ValueError("FULL_TRAIN_ORDER_CHANGED")
    for row in samples:
        if (not row["sample_id"].startswith(row["domain"] + "-" + row["level"] + "-")
                or row["binary_class"] != seminar.binary(row["level"]) or not row["group"]):
            raise ValueError("TRAIN_GT_METADATA_MISMATCH")
    expected = partition(projection)
    for i, payload in enumerate(shards):
        if (validate_inference(strict_json(payload), i) != expected[i]
                or value["shards"][i] != {"shard_id": i, "run_id": run_id(i), "count": SIZES[i],
                    "path": inference_path(i), "sha256": hashlib.sha256(payload).hexdigest()}):
            raise ValueError("DISJOINT_COMPLETE_TRAIN_SHARDS_REQUIRED")
    return {r["sample_id"]: {k: r[k] for k in ("level", "domain", "group")} for r in samples}


def authority(repo, source_commit, *, protocol=None):
    """Exact BASE -> implementation F1 -> authority-only F2 -> standard merge M.

    Topology attests source integrity, not human approval. Lead must independently
    review/approve F2 and maintain the global one-attempt ledger across Kaggle versions.
    """
    if protocol is None:
        import sys
        protocol = sys.modules[__name__]
    AUTHORITY, BASE, SCOPE = protocol.AUTHORITY, protocol.BASE, protocol.SCOPE
    run_id, SIZES = protocol.run_id, protocol.SIZES
    repo = Path(repo)
    value = strict_json((repo / AUTHORITY).read_bytes())
    if set(value) != {"base", "implementation", "scope", "grant"} or value["scope"] != SCOPE:
        raise PermissionError("TRAIN_AUTHORITY_SCHEMA_OR_SCOPE")
    grant = value["grant"]
    if grant is None:
        raise PermissionError("TRAIN_GRANT_PENDING_RESEARCH_LEAD_AND_AUDIT")
    if (type(grant) is not dict or set(grant) != {*HASHES, "approval", "decision", "shards"}
            or any(type(grant[k]) is not str or not re.fullmatch(r"[0-9a-f]{64}", grant[k]) for k in HASHES)
            or grant["decision"] != getattr(protocol, "DECISION", "DEC-PA3-007") or not isinstance(grant["approval"], str) or not grant["approval"].strip()
            or type(grant["shards"]) is not list or len(grant["shards"]) != 4):
        raise PermissionError("TRAIN_GRANT_SCHEMA")
    for i, entry in enumerate(grant["shards"]):
        if (set(entry) != {"shard_id", "run_id", "max_images", "inference_manifest_sha256"}
                or type(entry["shard_id"]) is not int or entry["shard_id"] != i
                or entry["run_id"] != run_id(i) or type(entry["max_images"]) is not int or entry["max_images"] != SIZES[i]
                or not re.fullmatch(r"[0-9a-f]{64}", entry["inference_manifest_sha256"])):
            raise PermissionError("TRAIN_EXACT_SHARD_BUDGET_REQUIRED")
    try:
        head = preflight.git(repo, "rev-parse", "HEAD").decode()
        parents = preflight.git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if head != source_commit or len(parents) != 3 or parents[1] != value["base"]:
            raise PermissionError("TRAIN_STANDARD_MERGE_REQUIRED_DRAFT_LOCKED")
        preflight.git(repo, "merge-base", "--is-ancestor", BASE, value["base"])
        f2, f1 = parents[2], value["implementation"]
        if (preflight.git(repo, "rev-list", "--parents", "-n", "1", f1).decode().split() != [f1, value["base"]]
                or preflight.git(repo, "rev-list", "--parents", "-n", "1", f2).decode().split() != [f2, f1]
                or preflight.git(repo, "diff", "--name-only", f1, f2).decode() != AUTHORITY):
            raise PermissionError("TRAIN_AUTHORITY_ONLY_F2_REQUIRED")
        if (preflight.git(repo, "rev-parse", head + "^{tree}") != preflight.git(repo, "rev-parse", f2 + "^{tree}")
                or (repo / AUTHORITY).read_bytes() != preflight.git_blob(repo, f2, AUTHORITY)
                or preflight.git(repo, "status", "--porcelain", "--untracked-files=no")):
            raise PermissionError("TRAIN_SOURCE_TREE_CHANGED")
        prior = (access.AUTHORITY, access.DIAGNOSTIC_AUTHORITY)
        if protocol.MODE != MODE:
            prior += ("configs/pa3/full_train_authority.v1.json",)
        for path in prior:
            if preflight.git_blob(repo, head, path) != preflight.git_blob(repo, value["base"], path):
                raise PermissionError("TRAIN_PRIOR_AUTHORITY_CHANGED")
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("TRAIN_SOURCE_PROOF_MISSING") from exc
    return value


def require(settings, repo, *, protocol=None):
    if protocol is None:
        import sys
        protocol = sys.modules[__name__]
    shard = settings.get("shard_id")
    if settings.get("mode") != protocol.MODE or settings.get("run_id") != protocol.run_id(shard):
        raise PermissionError("TRAIN_EXACT_MODE_AND_RUN_REQUIRED")
    allowed = {"mode", "run_id", "shard_id", "source_commit", "source_bundle_input", "source_bundle_sha256",
               "model_input", "runtime_input", "runtime_inventory_input", "runtime_site_packages", "dataset_input",
               "inference_manifest_sha256", "technical_run_input", "technical_source_bundle_input", "train_inputs_root", *HASHES}
    if set(settings) - allowed:
        raise PermissionError("TRAIN_SETTINGS_OUTSIDE_SCOPE")
    value = protocol.authority(repo, settings.get("source_commit"))
    for key in HASHES:
        if settings.get(key) != value["grant"][key]:
            raise PermissionError("TRAIN_APPROVAL_BINDING:" + key)
    if settings.get("inference_manifest_sha256") != value["grant"]["shards"][shard]["inference_manifest_sha256"]:
        raise PermissionError("TRAIN_SHARD_MANIFEST_BINDING")
    return value


def inference_samples(repo, settings):
    grant = require(settings, repo)["grant"]  # deny before manifest/data reads
    payload = (Path(repo) / inference_path(settings["shard_id"])).read_bytes()
    if hashlib.sha256(payload).hexdigest() != grant["shards"][settings["shard_id"]]["inference_manifest_sha256"]:
        raise ValueError("TRAIN_INFERENCE_MANIFEST_CHECKSUM")
    return validate_inference(strict_json(payload), settings["shard_id"])


def load_full(repo, expected):
    """CPU metadata join only, after raw seal; no dataset or execution right."""
    payload = (Path(repo) / FULL).read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("FULL_TRAIN_MANIFEST_CHECKSUM")
    shards = [(Path(repo) / inference_path(i)).read_bytes() for i in range(4)]
    return validate_full(strict_json(payload), shards)


def preflight_dataset(repo, settings, inputs):
    rows = inference_samples(repo, settings)
    root = seminar.dataset_root(settings, inputs)
    for row in rows:
        if digest(safe_path(root, row["image_locator"])) != row["image_sha256"]:
            raise ValueError("TRAIN_IMAGE_CHECKSUM:" + row["sample_id"])
    return {"planned": len(rows), "verified": len(rows), "decoded": False, "samples": rows}


def open_image(repo, settings, row, inputs):
    if row not in inference_samples(repo, settings):
        raise PermissionError("IMAGE_OUTSIDE_TRAIN_SHARD")
    return open_sample(row, seminar.dataset_root(settings, inputs))


def verify_prior(repo, settings, inputs, tokenizer, *, require_gate=None):
    (require_gate or require)(settings, repo)
    # Reuse the audited four-image CPU recheck with the same pinned technical source.
    from . import pilot
    import subprocess
    from safeshift.ls1.kaggle import attached_path
    bundle = attached_path(inputs, settings["technical_source_bundle_input"])
    if digest(bundle) != settings["technical_source_bundle_sha256"]:
        raise ValueError("TECHNICAL_SOURCE_BUNDLE_CHECKSUM")
    technical_repo = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-technical-source")
    if not technical_repo.exists():
        subprocess.run(["git", "-c", "core.autocrlf=false", "clone", "--no-checkout", str(bundle), str(technical_repo)], check=True)
        subprocess.run(["git", "-C", str(technical_repo), "-c", "core.autocrlf=false", "checkout", "--detach",
                        SCOPE["technical_source_commit"]], check=True)
    root = attached_path(inputs, settings["technical_run_input"])
    if Journal(root).read("manifest")["source"]["source_commit"] != SCOPE["technical_source_commit"]:
        raise ValueError("TECHNICAL_SOURCE_COMMIT_MISMATCH")
    return pilot.prior_technical(root, technical_repo, tokenizer, settings["technical_seal_sha256"])


def image_ticket(repo, settings, image, journal, prefix):
    rows = inference_samples(repo, settings)
    if journal.root != run_path(repo, settings["run_id"]):
        raise PermissionError("EXACT_TRAIN_JOURNAL_REQUIRED")
    index = next((i for i in range(len(rows)) if prefix == f"sample-{i:06d}"), None)
    if index is None or journal.read(prefix + ".attempt") != rows[index]:
        raise PermissionError("TRAIN_SAMPLE_IDENTITY")
    with open_image(repo, settings, rows[index], settings["train_inputs_root"]) as expected:
        if (image.mode, image.size, image.tobytes()) != (expected.mode, expected.size, expected.tobytes()):
            raise PermissionError("TRAIN_IMAGE_PIXELS")
    tickets = no_alias(journal.root.parent / (journal.root.name + "-tickets"))
    tickets.mkdir(exist_ok=True)
    with (tickets / (prefix + ".ticket")).open("xb") as stream:
        stream.write(rows[index]["image_sha256"].encode())
