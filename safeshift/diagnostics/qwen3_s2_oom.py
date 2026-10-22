"""Offline V4 S2 artifact forensics and NON-EXECUTABLE recovery planning.

Standard library only. Never imports torch, opens images, loads a tokenizer,
invokes a worker, grants authority, or rewrites/extracts an input archive.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

RELEASE = "c9e2279296165d5a0e77fae03a465e216508b5d3"
FIRST_SHA = "2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920"
RERUN_SHA = "508a2e122ee999da728e8d09c66f5157331e6fe1a40adaa82e2869a30c6e0147"
STEM = "hnlo-train-v4-qwen3-s2-a1"
NEW_RUN = "hnlo-qwen3-s2-recovery224-v1-20261022"
NEW_ATTEMPT = NEW_RUN + "-a1"
ORIGINAL_SHARD_SHA = "f9d2370dd5feece46c91ffe88171cb7cd5e838d3a7818000894b7f71d3829695"
MAX_MEMBER = 32 * 2**20
MAX_TOTAL = 512 * 2**20


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return digest((json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                              allow_nan=False) + "\n").encode())


def file_digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def load(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError("NONFINITE_JSON:" + value)
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def relative(name):
    require(type(name) is str and bool(name) and "\\" not in name and ":" not in name
            and not name.startswith("/")
            and all(p not in ("", ".", "..") for p in name.split("/")), "UNSAFE_MEMBER_PATH")
    return name


def verify_archive(archive, manifest_bytes):
    """Hash every member, every journal sidecar and every nested seal; no extraction.

    Returns only small JSON observations needed for this case. Hashes establish
    integrity, not authenticity, execution permission, or scientific eligibility.
    """
    manifest = load(manifest_bytes)
    require(manifest["schema"] == "hnlo-evidence-inventory-v1", "INVENTORY_SCHEMA")
    expected = {}
    for row in manifest["files"]:
        name = "evidence/" + relative(row["path"])
        require(name not in expected, "DUPLICATE_INVENTORY_PATH")
        require(type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= MAX_MEMBER
                and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None, "INVALID_INVENTORY_ROW")
        expected[name] = {k: row[k] for k in ("sha256", "size_bytes")}
    require(len(expected) <= 100000 and sum(r["size_bytes"] for r in expected.values()) <= MAX_TOTAL,
            "ARCHIVE_BUDGET_EXCEEDED")
    observed, sidecars, seals, selected, journals = {}, {}, {}, {}, {}
    exact = {"binding.json", "result.json", "inference/result.json", "raw/index/model.json", "custody/files.json",
             "raw/index/manifest.json", "raw/index/failure.json", "raw/index/native-counts.json"}
    with tarfile.open(archive, "r|gz") as stream:
        for member in stream:
            name = relative(member.name)
            require(member.isfile() and not member.issparse(), "REGULAR_MEMBERS_ONLY")
            require(name not in observed, "DUPLICATE_ARCHIVE_MEMBER")
            require(name in expected or name == "manifest.json", "EXTRA_ARCHIVE_MEMBER")
            require(0 <= member.size <= MAX_MEMBER, "MEMBER_BUDGET_EXCEEDED")
            data = stream.extractfile(member).read(MAX_MEMBER + 1)
            proof = {"sha256": digest(data), "size_bytes": len(data)}
            observed[name] = proof
            if name == "manifest.json":
                require(data == manifest_bytes, "INNER_OUTER_MANIFEST_MISMATCH")
                continue
            require(proof == expected[name], "ARCHIVE_CHECKSUM_MISMATCH:" + name)
            parent, filename = name.rsplit("/", 1)
            if filename.endswith(".json") and not filename.endswith(".sha256.json") and filename != "seal.json":
                journals.setdefault(parent, {})[filename[:-5]] = proof
            short = name.removeprefix("evidence/")
            if name.endswith(".sha256.json"):
                sidecars[name] = load(data)
            elif name.endswith("/seal.json"):
                seals[name] = load(data)
            if short in exact or re.fullmatch(r"raw/sample-\d{6}/(call|native|error)\.json", short):
                value = load(data)
                # Native sequences and vectors are unnecessary for shape analysis.
                if short.endswith("/native.json"):
                    value = {"raw_steps": value["raw_steps"], "tensor_layouts": value["tensor_layouts"]}
                selected[short] = value
    require(set(observed) == set(expected) | {"manifest.json"}, "MISSING_ARCHIVE_MEMBER")
    for name, proof in sidecars.items():
        target = name.removesuffix(".sha256.json") + ".json"
        require(observed.get(target) == proof, "JOURNAL_SIDECAR_MISMATCH:" + name)
    for name, seal in seals.items():
        parent = name.rsplit("/", 1)[0] + "/"
        actual = journals.get(parent[:-1], {})
        require(actual == seal, "JOURNAL_SEAL_MISMATCH:" + name)
        require(all(parent + key + ".sha256.json" in sidecars for key in (*actual, "seal")),
                "JOURNAL_SIDECAR_MISSING")
    require("evidence/raw/index/seal.json" in seals and "evidence/custody/seal.json" in seals,
            "UNIT_AND_CUSTODY_SEALS_REQUIRED")
    custody = {p.removeprefix("evidence/"): proof for p, proof in expected.items()
               if not p.startswith(("evidence/custody/", "evidence/report/"))
               and p not in ("evidence/result.json", "evidence/cpu-audit.log")}
    require(custody == selected["custody/files.json"], "RAW_CUSTODY_MISMATCH")
    return selected, {"members": len(observed), "evidence_members": len(expected),
                      "journal_seals": len(seals), "integrity": "PASS_NOT_AUTHENTICITY_OR_HNLO_RECOMPUTATION"}


def recovery_plan(rows, planned, source, archive_sha):
    """Exact original suffix only; never executable authority or baseline pooling."""
    require(source["merge_commit"] == RELEASE, "WRONG_RELEASE")
    require(len(planned) == len(rows) == 941, "EXACT_S2_COUNT_REQUIRED")
    ids = [p["sample_id"] for p in planned]
    require(len(set(ids)) == 941, "DUPLICATE_SAMPLE_ID")
    for i, (row, original) in enumerate(zip(rows, planned)):
        wanted = "SUCCESS" if i < 717 else "TECHNICAL_ERROR" if i == 717 else "NOT_ATTEMPTED"
        require(type(row["ordinal"]) is int and row["ordinal"] == i and row["sample_id"] == original["sample_id"]
                and row["status"] == wanted, "UNEXPECTED_COVERAGE_OR_ORDER")
        require(row["attempted"] is (i <= 717) and row["native_call_start_recorded"] is (i <= 717)
                and row["persisted"] is (i < 717), "EXPOSURE_OR_PERSISTENCE_MISMATCH")
        require(type(original["image_sha256"]) is str
                and re.fullmatch(r"[0-9a-f]{64}", original["image_sha256"]) is not None, "IMAGE_HASH_REQUIRED")
    mapping = [{"recovery_ordinal": i - 717, "original_shard": 2, "original_ordinal": i,
                "sample_id": planned[i]["sample_id"], "image_sha256": planned[i]["image_sha256"],
                "prior_status": rows[i]["status"]} for i in range(717, 941)]
    # Only this projection may reach a future worker; preserve original order/hash.
    worker = [{"ordinal": i, "image_sha256": planned[717 + i]["image_sha256"]} for i in range(224)]
    return {"schema": "qwen3-s2-recovery224-plan-v1", "status": "PROPOSED_NON_EXECUTABLE",
            "grant": None, "execution_allowed": False, "run_id": NEW_RUN, "attempt_id": NEW_ATTEMPT,
            "baseline_release": RELEASE, "input_artifact_sha256": archive_sha,
            "source_lock": {"schema": "qwen3-s2-recovery224-input-lock-v1", "baseline_release": RELEASE,
                "original_inference_sha256": ORIGINAL_SHARD_SHA, "mapping_sha256": canonical_digest(mapping),
                "worker_projection_sha256": canonical_digest(worker), "implementation_commit": None,
                "execution_payload_sha256": None, "execution_lock_complete": False},
            "authority_contract": {"schema": "qwen3-s2-recovery224-authority-proposal-v1", "grant": None,
                "required_binding": ["new run_id and attempt_id", "complete execution source lock",
                    "direct GitHub review and independent audit", "Lead recovery-specific decision",
                    "new explicit execution permission", "exposure ledger and retention approval"]},
            "audit_contract": {"schema": "qwen3-s2-recovery224-audit-proposal-v1", "implementation_reviewed": False,
                "expected_original_ordinals": [717, 940], "expected_count": 224,
                "worker_fields": ["ordinal", "image_sha256"], "max_calls_per_ordinal": 1,
                "raw_contract": "BASELINE_SUFFICIENT_RAW_SUMMARIES_V1_PROPOSED",
                "full_vocab_replay": False, "raw_before_decode": True, "seal_before_hnlo": True,
                "labels_only_after_custody_and_new_approval": True, "stop_on_technical_error": True,
                "diagnostic_journal": "SEPARATE_SEALED_RECOVERY_OBSERVATIONS_NO_TENSORS_OR_LABELS",
                "baseline_replacement_or_pooling": "FORBIDDEN_PENDING_SEPARATE_DECISION"},
            "missing_prerequisites": ["independent GitHub audit", "reviewed recovery implementation and source lock",
                "separate Lead decision and new source-bound authority", "new execution permission",
                "cross-session exposure ledger reservation", "separate recovery custody and CPU audit contract"],
            "baseline_pooling_allowed": False, "max_loads": 1, "max_native_calls": 224,
            "retry": False, "resume": False, "mapping": mapping, "worker_projection": worker}


def investigate(archive, receipts, repo):
    """Verify the supplied rerun independently. The first archive is not substituted."""
    receipts, repo, archive = Path(receipts), Path(repo), Path(archive)
    blobs = {suffix: (receipts / (STEM + suffix + ".json")).read_bytes()
             for suffix in ("_sha256", "_manifest", "_result", "_export", "_export_sha256")}
    checksum, result, export, export_sha = (load(blobs[s]) for s in
                                           ("_sha256", "_result", "_export", "_export_sha256"))
    sha, size, manifest_sha = file_digest(archive), archive.stat().st_size, digest(blobs["_manifest"])
    require(sha == RERUN_SHA, "EXACT_SUPPLIED_RERUN_REQUIRED")
    require(checksum == {"archive": STEM + ".tar.gz", "sha256": sha, "size_bytes": size,
            "status": "EXPORT_VALID", "manifest_sha256": manifest_sha,
            "verified_evidence_members": len(load(blobs["_manifest"])["files"])}, "ARCHIVE_RECEIPT_MISMATCH")
    require(export_sha == {"sha256": digest(blobs["_export"])}, "EXPORT_RECEIPT_MISMATCH")
    require(export["status"] == "EXPORTED" and export["archive"] == STEM + ".tar.gz"
            and export["archive_sha256"] == sha and export["archive_bytes"] == size
            and export["manifest_sha256"] == manifest_sha
            and export["result_sha256"] == digest(blobs["_result"]), "EXPORT_BINDING_MISMATCH")
    selected, integrity = verify_archive(archive, blobs["_manifest"])
    binding = selected["binding.json"]
    from .hnlo_train import cohort, contract
    planned = cohort.inference(repo)[2]  # committed GT-free inference manifests only
    require(binding["samples"] == planned, "ORIGINAL_COHORT_CHANGED")
    require(binding["unit"] == result["unit"] == export["unit"] == contract.unit("qwen3", 2), "UNIT_CHANGED")
    require(selected["result.json"] == {k: v for k, v in result.items() if k != "export"},
            "INNER_OUTER_RESULT_MISMATCH")
    require(result["export"] == {k: v for k, v in export.items() if k != "result_sha256"},
            "RESULT_EXPORT_BINDING_MISMATCH")
    rows = result["sample_journal"]
    plan = recovery_plan(rows, planned, binding["source"], sha)
    require(selected["raw/index/manifest.json"] == {"samples": cohort.opaque_rows(planned), "expected_count": 941},
            "WORKER_COHORT_CHANGED")
    failure = selected["raw/index/failure.json"]
    require(failure == {"ordinal": 717, "type": "OutOfMemoryError", "interrupted": False, "retry": False},
            "UNEXPECTED_FAILURE")
    call = selected["raw/sample-000717/call.json"]
    matching = [i for i in range(717) if selected[f"raw/sample-{i:06d}/call.json"]["input_shapes"] == call["input_shapes"]]
    counts = selected["raw/index/native-counts.json"]
    require(counts["load_calls"] == 1 and counts["generate_ordinals"] == list(range(718)), "NATIVE_COUNTS_CHANGED")
    report = {"schema": "qwen3-s2-oom-forensics-v1", "release": RELEASE, "archive_sha256": sha,
              "artifact_role": "RERUN_DIAGNOSTIC_ONLY_DUPLICATED_ATTEMPT_ID",
              "first_artifact": {"sha256": FIRST_SHA, "verification": "HANDOFF_REPORTED_NOT_LOCALLY_REVERIFIED"},
              "integrity": integrity, "receipt_sha256": {s: digest(b) for s, b in blobs.items()},
              "coverage": dict(Counter(r["status"] for r in rows)), "failure": failure,
              "failed_sample_id": planned[717]["sample_id"], "input_shapes": call["input_shapes"],
              "same_shape_successes": [{"ordinal": i, "steps": selected[f"raw/sample-{i:06d}/native.json"]["raw_steps"]}
                                       for i in matching], "worker_memory": counts["memory"],
              "sampled_resources": result["resources"], "root_cause": "UNDETERMINED",
              "failed_device": None, "failed_allocation_bytes": None, "gpu_used": False,
              "hnlo_recomputed": False, "baseline_modified": False}
    return report, plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report, plan = investigate(args.archive, args.receipts, args.repo)
    # A fresh directory is required. Never overwrite any earlier investigation.
    args.output.mkdir(parents=True, exist_ok=False)
    from .one_click.artifacts import write
    write(args.output / "forensics.json", report)
    write(args.output / "recovery-plan.json", plan)
    print(json.dumps({"integrity": report["integrity"], "coverage": report["coverage"],
                      "root_cause": report["root_cause"], "execution_allowed": False}))


if __name__ == "__main__":
    main()
