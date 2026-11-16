"""Build/verify QWEN3_FULL_TRAIN_COMPOSITE_V1 from exact historical saved reports.

CPU/stdlib only. Reads explicit metadata/report members, never raw logits, image
files, weights, TEST, Kaggle or mutable production ledgers. New output only.
"""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import sys

from safeshift.evaluation.qwen_composite import (
    PRODUCT, PROVENANCE_FIELDS, compose, digest, finite_score, index, report, require,
)
from safeshift.pilot.manifest import validate_master
from scripts.analyze_source_sensitivity import (
    checked_bytes, original_s2_zip, relative_path, report_rows, verified_archive_members,
)

CONFIG = "configs/analysis/qwen3_full_train_composite.v1.json"
MASTER = "data/manifests/pa3_full_train.v1.json"
V4_AUTHORITY = "configs/diagnostics/hnlo_train_authority.v4.json"
REC_AUTHORITY = "configs/diagnostics/qwen3_s2_recovery_authority.v1.json"
MEMBERS = {"evidence/report/samples.csv", "evidence/binding.json", "evidence/result.json",
           "evidence/source.json", "evidence/inference/runtime.json",
           "evidence/inference/generation-sources.json"}
SOURCE_KEYS = ("implementation_commit", "authority_commit", "merge_commit", "payload_sha256", "pr_number")


def bytes_sha(value):
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def historical_digest(value):
    # The PR123/124 contract includes a terminal LF and ASCII JSON escaping.
    return bytes_sha((json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=True, allow_nan=False) + "\n").encode())


def historical(config):
    output = {}
    for path, expected in config["historical_files_sha256"].items():
        raw = subprocess.check_output(["git", "show", config["history_commit"] + ":" + path])
        require(bytes_sha(raw) == expected, "historical source checksum mismatch: " + path)
        output[path] = json.loads(raw)
    return output


def validate_unit(result, binding, rows, unit, authority, planned, master):
    """Exact source config/status/ordered-input validation, independent of score availability."""
    require(result["unit"] == binding["unit"] == result["export"]["unit"] == unit,
            "wrong run/attempt/revision/config unit")
    require(binding["authority"] == authority and binding["samples"] == planned,
            "wrong authority/config/ordered image hashes")
    require(result["schema"] == "hnlo-train-unit-result-v1" and
            result["retry"] is False and result["research_generalization_claim"] is False,
            "wrong saved-result scope")
    recovery = "cohort" in unit
    require(result["scope"] == ("SUPPLEMENTAL_RECOVERY_NOT_V4_BASELINE" if recovery
                                 else "DESCRIPTIVE_FULL_TRAIN"), "wrong result scope")
    if recovery:
        require(result["resume"] is False and result["baseline_pooling_allowed"] is False,
                "historical recovery contract changed")
    ids = [r["sample_id"] for r in planned]
    require(len(index(rows)) == unit["count"] and [r["sample_id"] for r in rows] == ids,
            "exact unique ordered planned report IDs required")
    journal = result["sample_journal"]
    require([r["sample_id"] for r in journal] == ids and
            [r["ordinal"] for r in journal] == list(range(len(ids))), "journal ID/order mismatch")
    for i, (r, sample, event) in enumerate(zip(rows, planned, journal)):
        m = master[r["sample_id"]]
        require(r["true_level"] == m["level"] and r["domain"] == m["domain"] and
                sample["image_sha256"] == m["image_sha256"] and
                sample["image_locator"] == m["image_locator"] and m["split"] == "TRAIN",
                "saved ID/image hash/GT/domain/split mismatch")
        require(r["true_binary_label"] == ("Normal" if m["level"] == "Level04" else "Anomaly"),
                "binary GT mismatch")
        status = r["status"]
        require(status in {"SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED"}, "invalid source status")
        flags = (status != "NOT_ATTEMPTED", status == "SUCCESS", status == "SUCCESS")
        require(event["status"] == status and
                tuple(r[k] for k in ("attempted", "persisted", "parsed")) == tuple(str(x) for x in flags) and
                all(event[k] is v for k, v in zip(("attempted", "persisted", "parsed"), flags)),
                "status/attempt/persistence/parse mismatch")
        if status == "SUCCESS":
            require(r["generated_label"] in ("Level01", "Level02", "Level03", "Level04"),
                    "invalid generated label")
            require(r["generated_binary_label"] ==
                    ("Normal" if r["generated_label"] == "Level04" else "Anomaly"),
                    "generated binary label mismatch")
        else:
            require(r["generated_label"] == "" and r["pa3_score"] == "", "failure has prediction/score")
        if recovery:
            require(status == "SUCCESS" and event["original_ordinal"] == 717 + i,
                    "recovery status/original ordinal mismatch")
    coverage = result["coverage"]
    counts = Counter(r["status"] for r in rows)
    require(all(coverage["status_counts"].get(s) == n for s, n in counts.items()) and
            not any(n for s, n in coverage["status_counts"].items() if s not in counts),
            "saved status totals mismatch")
    for key, expected in {"planned": len(rows), "scored": counts["SUCCESS"],
                          "persisted": counts["SUCCESS"], "parsed": counts["SUCCESS"],
                          "attempted": counts["SUCCESS"] + counts["TECHNICAL_ERROR"],
                          "anomaly_n": sum(r["true_level"] != "Level04" for r in rows),
                          "normal_n": sum(r["true_level"] == "Level04" for r in rows)}.items():
        require(coverage[key] == expected, "coverage mismatch: " + key)
    require(coverage["coverage"] == counts["SUCCESS"] / len(rows) and
            all(coverage["level_counts"].get(t, 0) == sum(r["true_level"] == t for r in rows)
                for t in ("Level01", "Level02", "Level03", "Level04")), "saved class coverage mismatch")
    require(result["status"] == ("COMPLETE" if counts["SUCCESS"] == len(rows) else "PARTIAL"),
            "saved terminal status mismatch")


def recovery_mapping(binding, original, planned, unit):
    require(len(original) == len(planned) == 941, "exact original S2 required")
    mapping = []
    for i in range(717, 941):
        wanted = "TECHNICAL_ERROR" if i == 717 else "NOT_ATTEMPTED"
        require(original[i]["status"] == wanted and
                original[i]["sample_id"] == planned[i]["sample_id"], "wrong original recovery suffix")
        mapping.append({"recovery_ordinal": i - 717, "original_shard": 2, "original_ordinal": i,
                        "sample_id": planned[i]["sample_id"], "image_sha256": planned[i]["image_sha256"],
                        "prior_status": wanted})
    require(binding["recovery_mapping"] == mapping and historical_digest(mapping) == unit["mapping_sha256"],
            "recovery original status/ID/hash mapping mismatch")
    worker = [{"ordinal": i, "image_sha256": row["image_sha256"]} for i, row in enumerate(planned[717:])]
    require(historical_digest(worker) == unit["inference_sha256"], "recovery worker hash mismatch")


def load_sources(directory, config):
    history = historical(config)
    master = [{**r, "split": "TRAIN"} for r in validate_master(history[MASTER])]
    by_id = index(master)
    original, recovery, sources, proofs, shard_rows = [], [], {}, {}, {}
    v4_authority, rec_authority = history[V4_AUTHORITY], history[REC_AUTHORITY]
    v4_units = {u["shard"]: u for u in v4_authority["scope"]["units"] if u["model"] == "qwen3"}
    s2_proof = None
    source_ids = [f"v4_s{k}" for k in range(4)] + ["recovery224"]
    require(set(config["sources"]) == set(source_ids), "exact four V4 shards plus recovery required")
    for source_id in source_ids:
        lock = config["sources"][source_id]
        is_rec = lock["kind"] == "RECOVERY224"
        if source_id == "v4_s2":
            raw_zip = checked_bytes(directory / "Qwen3-Shard2-V4.zip", config["s2_zip_sha256"])
            archive, result, s2_proof = original_s2_zip(raw_zip)
            result_sha = s2_proof["sidecars"]["hnlo-train-v4-qwen3-s2-a1_result.json"]["sha256"]
        else:
            raw_result = checked_bytes(directory / lock["result_file"], lock["result_sha256"])
            result, result_sha = json.loads(raw_result), bytes_sha(raw_result)
            name = result["export"]["archive"]
            require(Path(name).name == name and "/" not in name and "\\" not in name and ":" not in name,
                    "archive basename required")
            archive = checked_bytes(directory / name, lock["archive_sha256"])
        require(result_sha == lock["result_sha256"] and
                result["export"]["archive_sha256"] == lock["archive_sha256"] and
                result["export"]["manifest_sha256"] == lock["manifest_sha256"], "source seal mismatch")
        found = verified_archive_members(archive, result["export"], MEMBERS)
        binding = json.loads(found["evidence/binding.json"])
        require(json.loads(found["evidence/result.json"]) == {k: v for k, v in result.items() if k != "export"},
                "internal/external result mismatch")
        require(json.loads(found["evidence/source.json"]) == binding["source"], "source/binding mismatch")
        authority = rec_authority if is_rec else v4_authority
        unit = rec_authority["scope"]["unit"] if is_rec else v4_units[lock["unit"]["shard"]]
        if not is_rec:
            require(unit == lock["unit"], "locked original unit mismatch")
        source = {k: binding["source"][k] for k in SOURCE_KEYS}
        grant = authority["grant"]
        require(source["implementation_commit"] == grant["implementation_commit"] and
                source["payload_sha256"] == grant["source_payload_sha256"] and
                source["authority_commit"] == binding["source"]["github_pr"]["head"]["sha"] and
                binding["source"]["github_pr"]["merged"] is True and
                source["merge_commit"] == binding["source"]["github_pr"]["merge_commit_sha"],
                "source/release/grant mismatch")
        require(source == lock["source"], "source/release differs from historical receipt")
        shard = unit["shard"]
        planned = history[f"data/manifests/pa3_full_train_shard{shard}.v1.json"]["samples"]
        if is_rec:
            recovery_mapping(binding, shard_rows[2], planned, unit)
            planned = planned[717:]
        rows = report_rows(found["evidence/report/samples.csv"])
        validate_unit(result, binding, rows, unit, authority, planned, by_id)
        provenance = {"kind": lock["kind"], "run_id": unit["run_id"], "attempt_id": unit["attempt_id"],
                      "model_id": unit["id"], "revision": unit["revision"],
                      "source_commit": source["implementation_commit"], "authority_commit": source["authority_commit"],
                      "merge_commit": source["merge_commit"], "source_payload_sha256": source["payload_sha256"],
                      "config_sha256": digest({"unit": unit, "scope": authority["scope"]}),
                      "archive_sha256": lock["archive_sha256"], "manifest_sha256": lock["manifest_sha256"],
                      "samples_sha256": bytes_sha(found["evidence/report/samples.csv"]),
                      "result_sha256": result_sha, "inference_sha256": unit["inference_sha256"]}
        sources[source_id] = provenance
        proofs[source_id] = {"unit": unit, "source": source, "historical_scope": authority["scope"],
                             "status_counts": dict(Counter(r["status"] for r in rows)),
                             "member_sha256": {name: bytes_sha(raw) for name, raw in found.items()},
                             "runtime_actual": json.loads(found["evidence/inference/runtime.json"])["actual"],
                             "generation_sources": json.loads(found["evidence/inference/generation-sources.json"])}
        normalized = [{"sample_id": r["sample_id"], "split": "TRAIN", "true_level": r["true_level"],
                       "domain": r["domain"], "image_sha256": by_id[r["sample_id"]]["image_sha256"],
                       "status": r["status"], "generated_label": r["generated_label"],
                       "hnlo_score": r["pa3_score"], "source_id": source_id,
                       "source_ordinal": i, **{k: provenance[k] for k in PROVENANCE_FIELDS}}
                      for i, r in enumerate(rows)]
        if is_rec:
            recovery.extend(normalized)
        else:
            shard_rows[shard] = rows
            original.extend(normalized)
    return master, original, recovery, sources, {"units": proofs, "original_s2_zip": s2_proof}


def csv_bytes(rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=sorted(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def metric_rows(value, path=""):
    if isinstance(value, dict):
        for key in sorted(value):
            yield from metric_rows(value[key], path + "/" + key)
    elif not isinstance(value, list):
        yield {"metric_path": path, "value": value}


def verify_train_images(train_root, master):
    """Hash exactly the locked TRAIN image paths; never enumerate/open TEST or decode images."""
    root = Path(train_root)
    require(not root.is_absolute() and ".." not in root.parts and root.parts[:2] == ("data", "raw"),
            "repo-relative data/raw TRAIN root required")
    allowed = (root / "DATA_PATH/train/Annotations").resolve()
    require(allowed.is_relative_to(Path("data/raw").resolve()), "TRAIN root escapes data/raw")
    receipts = []
    for row in master:
        loc = Path(row["image_locator"])
        require(not loc.is_absolute() and ".." not in loc.parts and
                loc.parts[:3] == ("DATA_PATH", "train", "Annotations") and loc.suffix == ".jpg",
                "locked TRAIN image locator required")
        path = root / loc
        require(path.resolve().is_relative_to(allowed), "image path escapes TRAIN Annotations")
        sha = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                sha.update(block)
        require(sha.hexdigest() == row["image_sha256"], "TRAIN image byte SHA256 mismatch: " + row["sample_id"])
        receipts.append({"sample_id": row["sample_id"], "image_sha256": sha.hexdigest()})
    return {"status": "PASS_TRAIN_IMAGE_BYTES_SHA256", "verified_n": len(receipts),
            "train_root": root.as_posix(), "images": receipts, "images_decoded": False, "test_accessed": False}


def build(directory, output, train_root=None):
    config_raw = Path(CONFIG).read_bytes()
    config = json.loads(config_raw)
    require(config["product_id"] == PRODUCT, "wrong product config")
    protocol = config["protocol"]
    protocol_raw = Path(protocol["path"]).read_bytes()
    prefix_size = protocol["original_prefix_size_bytes"]
    require(bytes_sha(protocol_raw) == protocol["amended_sha256"] and
            bytes_sha(protocol_raw[:prefix_size]) == protocol["original_prefix_sha256"] and
            bytes_sha(protocol_raw[prefix_size:]) == protocol["amendment_sha256"],
            "versioned protocol/amendment checksum mismatch")
    decision = config["owner_decision_export"]
    authority_raw = checked_bytes(Path(decision["path"]), decision["sha256"])
    owner = json.loads(authority_raw)
    require(owner["id"] == decision["comment_id"] and owner["author"] == decision["author"] and
            owner["author_association"] == decision["author_association"] and
            owner["html_url"] == config["owner_decision"], "Owner decision export mismatch")
    require(not output.exists(), "new output directory required; never overwrite historical evidence")
    master, original, recovery, sources, proof = load_sources(directory, config)
    images = verify_train_images(train_root, master) if train_root else {
        "status": "SAVED_IMAGE_IDENTITY_MATCH_ONLY_BYTES_NOT_REHASHED", "verified_n": 0}
    rows = compose(master, original, recovery, sources, config["original_status_counts"])
    require(len(rows) == config["planned_n"] and len(recovery) == config["recovery_n"], "product count mismatch")
    analysis = report(rows, sources)
    master_projection = [{k: r[k] for k in ("sample_id", "split", "image_sha256", "level", "domain")}
                         for r in master]
    payload = {"schema": "safeshift-qwen3-full-train-composite-v1", "product_id": PRODUCT,
               "samples": rows, "sources": sources, "master": master_projection,
               "original_ledger": original, "recovery_ledger": recovery,
               "original_status_counts": config["original_status_counts"]}
    command = ["python", "-B", "-m", "scripts.build_qwen3_composite", "--input-dir", directory.as_posix(),
               "--output", output.as_posix()]
    if train_root:
        command.extend(["--train-root", Path(train_root).as_posix()])
    proof.update({"schema": "safeshift-qwen3-composite-audit-v1", "owner_decision": config["owner_decision"],
                  "owner_decision_export_sha256": bytes_sha(authority_raw),
                  "config_sha256": bytes_sha(config_raw), "history_commit": config["history_commit"],
                  "historical_files_sha256": config["historical_files_sha256"],
                  "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                  "source_sha256": {p: bytes_sha(Path(p).read_bytes()) for p in
                                    ("scripts/build_qwen3_composite.py", "safeshift/evaluation/qwen_composite.py",
                                     "scripts/analyze_source_sensitivity.py", "safeshift/pilot/manifest.py",
                                     "safeshift/evaluation/sensitivity.py")},
                  "implementation_uncommitted_at_execution": bool(subprocess.check_output(
                      ["git", "status", "--porcelain", "--untracked-files=no"])),
                  "command": command, "python": platform.python_version(), "platform": platform.platform(),
                  "dependencies": [], "seed": None, "raw_audit_performed": False,
                  "independent_audit": "PENDING", "test_accessed": False, "gpu_or_kaggle": False,
                  "label_verification": "PASS", "input_directory": directory.as_posix()})
    proof["image_verification"] = {k: v for k, v in images.items() if k != "images"}
    files = {"composite.json": json_bytes(payload), "samples.csv": csv_bytes(rows),
             "metrics.json": json_bytes(analysis), "metrics.csv": csv_bytes(list(metric_rows(analysis))),
             "audit.json": json_bytes(proof), "image_verification.json": json_bytes(images)}
    seal = {"schema": "safeshift-qwen3-composite-seal-v1", "product_id": PRODUCT,
            "files": {n: {"sha256": bytes_sha(raw), "size_bytes": len(raw)} for n, raw in files.items()}}
    output.mkdir(parents=True, exist_ok=False)
    for name, raw in {**files, "manifest.json": json_bytes(seal)}.items():
        with (output / name).open("xb") as f:
            f.write(raw)
    return {"label_status": analysis["label_status"], "planned_n": len(rows),
            "manifest_sha256": bytes_sha(json_bytes(seal)), "output": output.as_posix()}


def read_product(directory, manifest_sha256):
    """Downstream handoff: require a separately retained trusted seal SHA256.

    Recompute all label metrics and selection semantics, not just file checksums.
    No ambient 'latest' discovery and no implicit HNLO pooling.
    """
    seal = json.loads(checked_bytes(directory / "manifest.json", manifest_sha256))
    require(seal["schema"] == "safeshift-qwen3-composite-seal-v1" and seal["product_id"] == PRODUCT,
            "wrong product seal")
    require(set(seal["files"]) == {"composite.json", "samples.csv", "metrics.json", "metrics.csv", "audit.json",
                                  "image_verification.json"},
            "exact product members required")
    found = {}
    for name, entry in seal["files"].items():
        found[name] = checked_bytes(directory / name, entry["sha256"])
        require(len(found[name]) == entry["size_bytes"], "product size mismatch")
    payload = json.loads(found["composite.json"])
    require(payload["schema"] == "safeshift-qwen3-full-train-composite-v1" and payload["product_id"] == PRODUCT,
            "wrong composite schema")
    rows = compose(payload["master"], payload["original_ledger"], payload["recovery_ledger"],
                   payload["sources"], payload["original_status_counts"])
    images = json.loads(found["image_verification.json"])
    if images.get("status") == "PASS_TRAIN_IMAGE_BYTES_SHA256":
        require(images["verified_n"] == len(rows) and images["images"] ==
                [{"sample_id": r["sample_id"], "image_sha256": r["image_sha256"]} for r in rows],
                "image verification/master mismatch")
    require(rows == payload["samples"] and csv_bytes(rows) == found["samples.csv"], "product row/CSV mismatch")
    analysis = report(rows, payload["sources"])
    require(json_bytes(analysis) == found["metrics.json"] and
            csv_bytes(list(metric_rows(analysis))) == found["metrics.csv"], "metric recomputation mismatch")
    return payload, analysis


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir")
    parser.add_argument("--output", required=True)
    parser.add_argument("--verify-manifest-sha256")
    parser.add_argument("--train-root", help="optional local dataset parent of DATA_PATH/train/Annotations")
    args = parser.parse_args(argv)
    try:
        output = relative_path(args.output)
        if args.verify_manifest_sha256:
            _, analysis = read_product(output, args.verify_manifest_sha256)
            result = {"status": "PASS_RECOMPUTED", "planned_n": analysis["planned_n"]}
        else:
            require(bool(args.input_dir), "--input-dir required for build")
            result = build(relative_path(args.input_dir), output, args.train_root)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "product_id": PRODUCT}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
