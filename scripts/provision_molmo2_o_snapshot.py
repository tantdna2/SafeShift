"""Provision the pinned Molmo snapshot or verify its local bytes without inference.

Provisioning is the only online phase.  ``--verify-only`` resolves the same exact
Hugging Face cache entry with ``local_files_only=True`` and denies Python socket
connections. This module never imports the model, torch, or snapshot custom code.
"""

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from unittest.mock import patch


MODEL_ID = "allenai/Molmo2-O-7B"
RESOLVED_REPOSITORY_ID = "allenai/Molmo2-O-7B"
REVISION = "784410650d12be9bc086118fdefa32d2c3bced86"
PROVENANCE = "configs/pre_freeze/local_model_provenance.d9.json"
ROOT = Path(__file__).resolve().parents[1]

SNAPSHOT_REPOSITORY_DIR = "models--allenai--Molmo2-O-7B"
SNAPSHOT_SUFFIX = (SNAPSHOT_REPOSITORY_DIR, "snapshots", REVISION)
SNAPSHOT_IDENTITY = "/".join(SNAPSHOT_SUFFIX)

EXPECTED_WEIGHT_FILES = ({'path': 'model-00001-of-00007.safetensors',
  'size_bytes': 4883320888,
  'lfs_sha256': 'c59d83290b402186c5f07dbc1d3824049b7c45e2bf5f699d0149292370c834c1'},
 {'path': 'model-00002-of-00007.safetensors',
  'size_bytes': 4857403152,
  'lfs_sha256': '78cc21ba267dda59d9f4c861e7210c8ae349ec32c9b1b0b7c2d2d611618c3ade'},
 {'path': 'model-00003-of-00007.safetensors',
  'size_bytes': 4857403200,
  'lfs_sha256': '431192bae063707006a111b4fcd0d9a4f3728c84b31e9acaf477198063d29d5a'},
 {'path': 'model-00004-of-00007.safetensors',
  'size_bytes': 4857403200,
  'lfs_sha256': 'd2dfac91d5ce48477afd12741ccd6e3985094208bf59eebbe6854b9d139bdb68'},
 {'path': 'model-00005-of-00007.safetensors',
  'size_bytes': 4857403200,
  'lfs_sha256': '924470fc671372515ed78e7badd7aa50e0fd30ae4e7d9f2d0afd516c25d19874'},
 {'path': 'model-00006-of-00007.safetensors',
  'size_bytes': 4856272712,
  'lfs_sha256': '537acbfd6608f7ebc9c1a51452f98462b34d80986ac2a64fc0e20cbbd5022a28'},
 {'path': 'model-00007-of-00007.safetensors',
  'size_bytes': 1874035072,
  'lfs_sha256': '3f3ec2f54f58925598edcccef2ec19b4d97e28a459d663eaea1e9491a52fb286'})

# SHA-256 over official pinned HTTP response bytes; never weight/runtime verification.
CRITICAL_PROVENANCE_FILES = ({'path': 'README.md',
  'size_bytes': 16327,
  'sha256': 'f41a022d2f1e0c33829dd62e8aaf0ac81144bbc6afdeb990bf7c43691566d5dc',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/README.md',
  'evidence': 'molmo2_o_7b.README.md',
  'retrieved_on': '2026-09-24'},
 {'path': 'config.json',
  'size_bytes': 2966,
  'sha256': '918491a079e7c26062393a95b3eb5ee25e4b0ab7d4dbd262edc7b1c6b613a159',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/config.json',
  'evidence': 'molmo2_o_7b.config.json',
  'retrieved_on': '2026-09-24'},
 {'path': 'generation_config.json',
  'size_bytes': 117,
  'sha256': '27b93746ce5b6d57e999cec810501d9cefb494cb69fbe69db2646764b9ae8ae7',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/generation_config.json',
  'evidence': 'molmo2_o_7b.generation_config.json',
  'retrieved_on': '2026-09-24'},
 {'path': 'processor_config.json',
  'size_bytes': 301,
  'sha256': '1a976bcab088bcc4601906c345898558daa18f5e69ec4b1df8ab23a389db8bf2',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/processor_config.json',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'preprocessor_config.json',
  'size_bytes': 555,
  'sha256': '026ee03897ff86cb0d3f7c638145a04a253d4c0722fc5bcc3cf996bb0ebed211',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/preprocessor_config.json',
  'evidence': 'molmo2_o_7b.preprocessor_config.json',
  'retrieved_on': '2026-09-24'},
 {'path': 'video_preprocessor_config.json',
  'size_bytes': 984,
  'sha256': 'ab16df7a17cb94cf57daeab7c6760a8be8cfad1fa37258cb86ad48d09ffd1815',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/video_preprocessor_config.json',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'tokenizer_config.json',
  'size_bytes': 6431,
  'sha256': '0bfaf75fcb0332acb1329c6a40bdf9dd3619e18e57b875ce018b5e586544860b',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/tokenizer_config.json',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'configuration_molmo2.py',
  'size_bytes': 13905,
  'sha256': '1405b6760579de537521829b9641c8362d5d50e7ef2bdbe3434d2de4a2fc6416',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/configuration_molmo2.py',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'processing_molmo2.py',
  'size_bytes': 16627,
  'sha256': '61ef1329d8a02caebaa5e5acd07a329fdbf9772e18ff32cd7256c09a3231360b',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/processing_molmo2.py',
  'evidence': 'molmo2_o_7b.processing_molmo2.py',
  'retrieved_on': '2026-09-24'},
 {'path': 'modeling_molmo2.py',
  'size_bytes': 71559,
  'sha256': 'd3cafcb5300dee41dc9b6d6e8b59e7d3b710bce0408672e8fd78a3bcb28669ce',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/modeling_molmo2.py',
  'evidence': 'molmo2_o_7b.modeling_molmo2.py',
  'retrieved_on': '2026-09-24'},
 {'path': 'image_processing_molmo2.py',
  'size_bytes': 21116,
  'sha256': '613bc2436936cebb1ebf0bfddda666b5c979573ba503fb904eed6eb56a706181',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/image_processing_molmo2.py',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'video_processing_molmo2.py',
  'size_bytes': 37045,
  'sha256': '91c4c6404f58dde3213b060874ce35c7f3695002f761fadf5af3f2515f770ba3',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/video_processing_molmo2.py',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'chat_template.jinja',
  'size_bytes': 3169,
  'sha256': 'ec66862fda57dc1aef90a21b2a0f64c18a280e2483206449bd251a73b8993101',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/chat_template.jinja',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'},
 {'path': 'model.safetensors.index.json',
  'size_bytes': 72832,
  'sha256': 'dc8d217f46ece0d2de31b795e39da9fe8b95e3a3ba879fb442507ecab3dfd4d1',
  'url': 'https://huggingface.co/allenai/Molmo2-O-7B/raw/784410650d12be9bc086118fdefa32d2c3bced86/model.safetensors.index.json',
  'evidence': 'B3B_PREP_PINNED_SOURCE_RETRIEVAL_2026_09_24',
  'retrieved_on': '2026-09-24'})

# No expected hash recorded for these assets: record local bytes only.
REQUIRED_LOCAL_ASSETS = ("tokenizer.json", "vocab.json", "merges.txt",
                         "special_tokens_map.json", "added_tokens.json")


def sha256_file(path):
    """Return SHA-256 of the bytes reachable at *path*, streamed from disk."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    """Write one new deterministic JSON report; never overwrite an attempt."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def _provenance(repo=ROOT):
    data = json.loads((Path(repo) / PROVENANCE).read_text(encoding="utf-8"))
    matches = [model for model in data["models"] if model.get("model_id") == MODEL_ID]
    if len(matches) != 1:
        raise ValueError("EXPECTED_ONE_MOLMO_PROVENANCE_RECORD")
    model = matches[0]
    if model.get("resolved_repository_id") != RESOLVED_REPOSITORY_ID:
        raise ValueError("PROVENANCE_RESOLVED_REPOSITORY_MISMATCH")
    if model.get("immutable_revision") != REVISION:
        raise ValueError("PROVENANCE_REVISION_MISMATCH")
    return data, model


def weight_files(repo=ROOT):
    """Read and strictly cross-check the seven documentary weight descriptors."""
    _, model = _provenance(repo)
    observed = model["weight_provenance"]["files"]
    normalized = [
        {
            "path": item.get("path"),
            "size_bytes": item.get("size_bytes"),
            "lfs_sha256": item.get("lfs_sha256"),
        }
        for item in observed
    ]
    expected = [dict(item) for item in EXPECTED_WEIGHT_FILES]
    if normalized != expected:
        raise ValueError("EXPECTED_EXACT_SEVEN_MOLMO_WEIGHT_SHARDS")
    return normalized


def critical_files(repo=ROOT):
    """Read and strictly cross-check the documentary critical-file hashes."""
    data, _ = _provenance(repo)
    result = []
    for expected in CRITICAL_PROVENANCE_FILES:
        source = data["sources"].get(expected["evidence"])
        if expected["evidence"].startswith("molmo2_o_7b.") and (
                not isinstance(source, dict) or source.get("content_sha256") != expected["sha256"]):
            raise ValueError("CRITICAL_PROVENANCE_HASH_MISMATCH")
        result.append(dict(expected))
    return result


def validate_snapshot_path(value):
    """Enforce the exact resolved-repository HF cache suffix used by the runner."""
    if not isinstance(value, (str, Path)):
        raise ValueError("SNAPSHOT_RESOLVER_MUST_RETURN_LOCAL_PATH")
    path = Path(value)
    if not path.is_absolute() or tuple(path.parts[-3:]) != SNAPSHOT_SUFFIX:
        raise ValueError("SNAPSHOT_PATH_IDENTITY_MISMATCH")
    resolved = path.resolve(strict=True)
    if not resolved.is_dir() or tuple(resolved.parts[-3:]) != SNAPSHOT_SUFFIX:
        raise ValueError("RESOLVED_SNAPSHOT_PATH_IDENTITY_MISMATCH")
    return resolved


def cached_snapshot(cache_dir=None, *, offline=True):
    """Resolve the exact full snapshot; online mode is provisioning only."""
    from huggingface_hub import snapshot_download

    snapshot = snapshot_download(
        repo_id=RESOLVED_REPOSITORY_ID,
        revision=REVISION,
        cache_dir=cache_dir,
        local_files_only=offline,
    )
    return validate_snapshot_path(snapshot)


def _identity():
    return {
        "model_id": MODEL_ID,
        "resolved_repository_id": RESOLVED_REPOSITORY_ID,
        "revision": REVISION,
    }


def _safe_asset_path(snapshot, relative_path):
    if type(relative_path) is not str or Path(relative_path).name != relative_path:
        raise ValueError("EXPECTED_SNAPSHOT_ROOT_ASSET")
    return Path(snapshot) / relative_path


def _snapshot_report(snapshot):
    report = {
        "schema_version": "molmo-local-snapshot-verification-v1",
        **_identity(),
        "expected_cache_suffix": SNAPSHOT_IDENTITY,
        "download_filter_policy": "NO_FILTERS",
        "verification_scope": "PINNED_REQUIRED_ASSETS",
        "SNAPSHOT_PATH_VERIFIED": False,
    }
    try:
        validate_snapshot_path(snapshot)
        report["SNAPSHOT_PATH_VERIFIED"] = True
    except Exception as exc:
        report["error_type"] = type(exc).__name__
    return report


def verify_weights(snapshot, files=None):
    """Hash and size every expected local shard, returning all observations."""
    files = weight_files() if files is None else list(files)
    observations = []
    for item in files:
        row = {
            "path": item["path"],
            "expected_sha256": item["lfs_sha256"],
            "expected_size_bytes": item["size_bytes"],
            "sha256": None,
            "size_bytes": None,
            "verified": False,
            "verification_status": "MISSING_OR_UNREADABLE",
        }
        try:
            path = _safe_asset_path(snapshot, item["path"])
            row["sha256"] = sha256_file(path)
            row["size_bytes"] = path.stat().st_size
            row["verified"] = (
                row["sha256"] == row["expected_sha256"]
                and row["size_bytes"] == row["expected_size_bytes"]
            )
            row["verification_status"] = (
                "VERIFIED_AGAINST_PROVENANCE" if row["verified"] else "HASH_OR_SIZE_MISMATCH"
            )
        except OSError as exc:
            row["error_type"] = type(exc).__name__
        observations.append(row)
    return {
        "schema_version": "molmo-local-weight-verification-v1",
        **_identity(),
        "files": observations,
        "LOCAL_WEIGHT_BYTES_VERIFIED": len(observations) == 7
        and all(row["verified"] for row in observations),
    }


def verify_critical_files(snapshot, files=None, local_hash_only_assets=None):
    """Verify documentary hashes and record, without promoting, other local hashes."""
    files = critical_files() if files is None else list(files)
    local_hash_only_assets = (
        REQUIRED_LOCAL_ASSETS if local_hash_only_assets is None else tuple(local_hash_only_assets)
    )
    observations = []
    provenance_ok = True
    for item in files:
        row = {
            "path": item["path"],
            "evidence": item.get("evidence"),
            "source_url": item.get("url"),
            "source_retrieved_on": item.get("retrieved_on"),
            "verification_basis": "PROVENANCE_SHA256",
            "expected_sha256": item["sha256"],
            "sha256": None,
            "size_bytes": None,
            "exists": False,
            "verified": False,
            "verification_status": "MISSING_OR_UNREADABLE",
        }
        try:
            path = _safe_asset_path(snapshot, item["path"])
            row["sha256"] = sha256_file(path)
            row["size_bytes"] = path.stat().st_size
            row["exists"] = True
            row["verified"] = row["sha256"] == row["expected_sha256"]
            row["verification_status"] = (
                "VERIFIED_AGAINST_PROVENANCE" if row["verified"] else "HASH_MISMATCH"
            )
        except OSError as exc:
            row["error_type"] = type(exc).__name__
        provenance_ok = provenance_ok and row["verified"]
        observations.append(row)

    assets_present = True
    for name in local_hash_only_assets:
        row = {
            "path": name,
            "evidence": None,
            "verification_basis": "LOCAL_HASH_ONLY",
            "expected_sha256": None,
            "sha256": None,
            "size_bytes": None,
            "exists": False,
            # Deliberately false: there is no documentary expected hash.
            "verified": False,
            "verification_status": "MISSING_OR_UNREADABLE",
        }
        try:
            path = _safe_asset_path(snapshot, name)
            row["sha256"] = sha256_file(path)
            row["size_bytes"] = path.stat().st_size
            row["exists"] = True
            row["verification_status"] = "RECORDED_LOCAL_HASH_ONLY"
        except OSError as exc:
            row["error_type"] = type(exc).__name__
        assets_present = assets_present and row["exists"]
        observations.append(row)

    return {
        "schema_version": "molmo-critical-file-verification-v1",
        **_identity(),
        "files": observations,
        "CRITICAL_PROVENANCE_HASHES_VERIFIED": len(files) == len(CRITICAL_PROVENANCE_FILES) and provenance_ok,
        "REQUIRED_LOCAL_ASSETS_PRESENT": (
            len(local_hash_only_assets) == len(REQUIRED_LOCAL_ASSETS) and assets_present
        ),
    }


def _not_attempted_weights(files, error_type):
    report = verify_weights(Path("."), [])
    report["files"] = [
        {
            "path": item["path"],
            "expected_sha256": item["lfs_sha256"],
            "expected_size_bytes": item["size_bytes"],
            "sha256": None,
            "size_bytes": None,
            "verified": False,
            "verification_status": "NOT_ATTEMPTED_INVALID_SNAPSHOT",
        }
        for item in files
    ]
    report["error_type"] = error_type
    return report


def _not_attempted_critical(files, local_hash_only_assets, error_type):
    report = verify_critical_files(Path("."), [], ())
    report["files"] = []
    for item in files:
        report["files"].append(
            {
                "path": item["path"],
                "evidence": item.get("evidence"),
                "verification_basis": "PROVENANCE_SHA256",
                "expected_sha256": item["sha256"],
                "sha256": None,
                "size_bytes": None,
                "exists": False,
                "verified": False,
                "verification_status": "NOT_ATTEMPTED_INVALID_SNAPSHOT",
            }
        )
    for name in local_hash_only_assets:
        report["files"].append(
            {
                "path": name,
                "evidence": None,
                "verification_basis": "LOCAL_HASH_ONLY",
                "expected_sha256": None,
                "sha256": None,
                "size_bytes": None,
                "exists": False,
                "verified": False,
                "verification_status": "NOT_ATTEMPTED_INVALID_SNAPSHOT",
            }
        )
    report["error_type"] = error_type
    return report


def verify_snapshot(snapshot, repo=ROOT):
    """Verify the exact path plus all bytes/assets required by the smoke contract."""
    files = weight_files(repo)
    critical = critical_files(repo)
    snapshot_report = _snapshot_report(snapshot)
    if snapshot_report["SNAPSHOT_PATH_VERIFIED"]:
        weight_report = verify_weights(snapshot, files)
        critical_report = verify_critical_files(snapshot, critical, REQUIRED_LOCAL_ASSETS)
    else:
        error_type = snapshot_report.get("error_type", "SNAPSHOT_PATH_INVALID")
        weight_report = _not_attempted_weights(files, error_type)
        critical_report = _not_attempted_critical(
            critical, REQUIRED_LOCAL_ASSETS, error_type
        )
    passed = (
        snapshot_report["SNAPSHOT_PATH_VERIFIED"]
        and weight_report["LOCAL_WEIGHT_BYTES_VERIFIED"]
        and critical_report["CRITICAL_PROVENANCE_HASHES_VERIFIED"]
        and critical_report["REQUIRED_LOCAL_ASSETS_PRESENT"]
    )
    return {
        "schema_version": "molmo-local-snapshot-contract-verification-v1",
        **_identity(),
        "snapshot": snapshot_report,
        "weights": weight_report,
        "critical_files": critical_report,
        "LOCAL_SNAPSHOT_VERIFIED": passed,
    }


def write_verification_reports(report_dir, verification, operation=None):
    """Create the three small reports consumed by the later evidence bundle."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=False)
    operation = dict(operation or {})
    components = {
        "snapshot_path": verification["snapshot"]["SNAPSHOT_PATH_VERIFIED"],
        "weight_bytes": verification["weights"]["LOCAL_WEIGHT_BYTES_VERIFIED"],
        "critical_provenance_hashes": verification["critical_files"][
            "CRITICAL_PROVENANCE_HASHES_VERIFIED"
        ],
        "required_local_assets": verification["critical_files"][
            "REQUIRED_LOCAL_ASSETS_PRESENT"
        ],
    }
    snapshot_report = {
        **verification["snapshot"],
        "component_verdicts": components,
        "LOCAL_SNAPSHOT_VERIFIED": verification["LOCAL_SNAPSHOT_VERIFIED"],
        "operation": operation,
    }
    weight_report = {**verification["weights"], "operation": operation}
    critical_report = {**verification["critical_files"], "operation": operation}
    write_json(report_dir / "snapshot_verification.json", snapshot_report)
    write_json(report_dir / "weight_verification.json", weight_report)
    write_json(
        report_dir / "critical_file_verification.json", critical_report
    )


def block_network(*args, **kwargs):
    raise RuntimeError("NETWORK_FORBIDDEN_DURING_VERIFY_ONLY")


class VerifyOnlyFirewall:
    """Count and deny common TCP, UDP and DNS entry points during local verify."""

    def __init__(self):
        self.violation_count = 0

    def deny(self, *args, **kwargs):
        self.violation_count += 1
        return block_network(*args, **kwargs)


def _resolution_failure(error, stage="SNAPSHOT_RESOLUTION"):
    # Use embedded pins so malformed/unreadable provenance can still produce all
    # three deterministic failure reports instead of failing while reporting.
    files = [dict(item) for item in EXPECTED_WEIGHT_FILES]
    critical = [dict(item) for item in CRITICAL_PROVENANCE_FILES]
    error_type = type(error).__name__
    snapshot_report = {
        "schema_version": "molmo-local-snapshot-verification-v1",
        **_identity(),
        "expected_cache_suffix": SNAPSHOT_IDENTITY,
        "download_filter_policy": "NO_FILTERS",
        "verification_scope": "PINNED_REQUIRED_ASSETS",
        "SNAPSHOT_PATH_VERIFIED": False,
        "failure_stage": stage,
        "error_type": error_type,
    }
    return {
        "schema_version": "molmo-local-snapshot-contract-verification-v1",
        **_identity(),
        "snapshot": snapshot_report,
        "weights": _not_attempted_weights(files, error_type),
        "critical_files": _not_attempted_critical(
            critical, REQUIRED_LOCAL_ASSETS, error_type
        ),
        "LOCAL_SNAPSHOT_VERIFIED": False,
    }


def _paths_overlap(first, second):
    first = Path(first).resolve()
    second = Path(second).resolve()
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument(
        "--cache-dir", help="Optional repository-relative HF hub cache under data/processed/"
    )
    parser.add_argument(
        "--report-dir",
        required=True,
        help="New repository-relative report directory under data/processed/",
    )
    args = parser.parse_args()

    # Reuse the storage boundary's repository-relative path and alias checks.
    sys.path.insert(0, str(ROOT))
    from safeshift.runners.storage import FileRawStore

    report_dir = FileRawStore(ROOT, args.report_dir).root
    if report_dir.exists():
        parser.error("report directory exists; every attempt requires a new path")
    cache_dir = None
    if args.cache_dir:
        cache_dir = FileRawStore(ROOT, args.cache_dir).root

    if cache_dir is not None and _paths_overlap(report_dir, cache_dir):
        parser.error("cache and report directories must be disjoint")

    firewall = VerifyOnlyFirewall()
    operation = {
        "mode": "VERIFY_ONLY_LOCAL" if args.verify_only else "PROVISION_ONLINE",
        "local_files_only": bool(args.verify_only),
        "network_firewall_enabled": bool(args.verify_only),
        "network_violation_count": 0,
    }
    failure_stage = "SNAPSHOT_RESOLUTION"
    try:
        if args.verify_only:
            with ExitStack() as stack:
                stack.enter_context(patch.dict(os.environ, {
                    "HF_HUB_OFFLINE": "1",
                    "TRANSFORMERS_OFFLINE": "1",
                    "HF_HUB_DISABLE_TELEMETRY": "1",
                }))
                stack.enter_context(patch.object(socket.socket, "connect", firewall.deny))
                stack.enter_context(patch.object(socket.socket, "connect_ex", firewall.deny))
                stack.enter_context(patch.object(socket.socket, "sendto", firewall.deny))
                stack.enter_context(patch.object(socket, "create_connection", firewall.deny))
                stack.enter_context(patch.object(socket, "getaddrinfo", firewall.deny))
                snapshot = cached_snapshot(cache_dir, offline=True)
                failure_stage = "LOCAL_BYTE_VERIFICATION"
                verification = verify_snapshot(snapshot, ROOT)
        else:
            snapshot = cached_snapshot(cache_dir, offline=False)
            failure_stage = "LOCAL_BYTE_VERIFICATION"
            verification = verify_snapshot(snapshot, ROOT)
    except Exception as exc:
        verification = _resolution_failure(exc, failure_stage)

    if firewall.violation_count:
        verification["LOCAL_SNAPSHOT_VERIFIED"] = False
    operation["network_violation_count"] = firewall.violation_count
    write_verification_reports(report_dir, verification, operation)
    summary = {
        "LOCAL_SNAPSHOT_VERIFIED": verification["LOCAL_SNAPSHOT_VERIFIED"],
        "report_dir": args.report_dir,
        "verify_only": args.verify_only,
    }
    print(json.dumps(summary, sort_keys=True))
    return 0 if verification["LOCAL_SNAPSHOT_VERIFIED"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
