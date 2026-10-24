"""CPU-only PROPOSED sensitivity of existing, hash-locked TRAIN reports.

No dataset/image/annotation loader. Read only historical receipt, metadata audit
and samples.csv members; never extract or replay raw model outputs from archives.
"""

import argparse
import csv
import hashlib
import io
import json
import platform
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

from safeshift.evaluation.sensitivity import (
    components, evaluate, exact_score_consistency, index_rows, join_reports, partition_edges, weighted_auc,
)

HISTORY = "31a04e6f7175cca818c63b4de0153246b3f3ecdb"
RECEIPT = "notes/evidence/three_model_20261023/verification_20261023.json"


def relative_path(value):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or ":" in value:
        raise ValueError("repo-relative portable paths required")
    if not path.parts or path.parts[:2] != ("data", "processed"):
        raise ValueError("local inputs/output must be under data/processed")
    if not path.resolve().is_relative_to((Path.cwd() / "data/processed").resolve()):
        raise ValueError("path escapes local processed directory")
    return path


def checked_bytes(path, expected):
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError(f"checksum mismatch: {path.as_posix()}")
    return payload


def report_rows(payload):
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))


def internvl_rows(payload, expected_members):
    rows = []
    with zipfile.ZipFile(io.BytesIO(payload)) as outer:
        names = [n for n in outer.namelist() if n.endswith(".tar.gz")]
        if len(names) != len(set(names)) or set(names) != set(expected_members):
            raise ValueError("exact unique receipt archive members required")
        for name in sorted(names):
            found = []
            with tarfile.open(fileobj=io.BytesIO(outer.read(name)), mode="r|gz") as archive:
                for member in archive:
                    if member.name == "evidence/report/samples.csv":
                        if not member.isfile():
                            raise ValueError("report must be a regular archive member")
                        found.append(archive.extractfile(member).read())
            if len(found) != 1 or hashlib.sha256(found[0]).hexdigest() != expected_members[name]:
                raise ValueError("unique samples member with receipt checksum required")
            rows.extend(report_rows(found[0]))
    return rows


def archive_report(payload, result):
    """Bind Qwen3 saved CSV to the hash-pinned result and inventory manifest.

    Read only manifest and CSV payloads. Raw logit/journal files are not opened.
    Even a valid archive binding establishes saved-score evidence, not raw PASS.
    """
    export = result["export"]
    if (len(payload) != export["archive_bytes"]
            or hashlib.sha256(payload).hexdigest() != export["archive_sha256"]):
        raise ValueError("Qwen3 archive checksum/size mismatch")
    found = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r|gz") as archive:
        for member in archive:
            if member.name in ("manifest.json", "evidence/report/samples.csv"):
                if member.name in found or not member.isfile():
                    raise ValueError("unique regular manifest/report members required")
                found[member.name] = archive.extractfile(member).read()
    if set(found) != {"manifest.json", "evidence/report/samples.csv"}:
        raise ValueError("missing Qwen3 manifest/report")
    if hashlib.sha256(found["manifest.json"]).hexdigest() != export["manifest_sha256"]:
        raise ValueError("Qwen3 manifest checksum mismatch")
    entries = [entry for entry in json.loads(found["manifest.json"])["files"]
               if entry["path"] == "report/samples.csv"]
    if len(entries) != 1:
        raise ValueError("unique report inventory entry required")
    saved = found["evidence/report/samples.csv"]
    entry = entries[0]
    if len(saved) != entry["size_bytes"] or hashlib.sha256(saved).hexdigest() != entry["sha256"]:
        raise ValueError("Qwen3 saved CSV inventory mismatch")
    rows = report_rows(saved)
    table = index_rows(rows, "true_level")
    expected = result["metrics"]["overall"]["auroc_pa3"]
    if (len(expected["eligible_ids"]) != len(set(expected["eligible_ids"]))
            or set(table) != set(expected["eligible_ids"])):
        raise ValueError("Qwen3 report/result exact eligible IDs required")
    actual = weighted_auc([r["true_level"] != "Level04" for r in rows],
                          [float(r["pa3_score"]) for r in rows])
    if actual is None or abs(actual - expected["value"]) > 1e-12:
        raise ValueError("Qwen3 saved-score AUROC differs from pinned result")
    return rows, {"archive_sha256": export["archive_sha256"],
                  "manifest_sha256": export["manifest_sha256"], "samples_sha256": entry["sha256"],
                  "n_saved_rows": len(rows), "run_id": result["unit"]["run_id"]}


def analyze(audit, reports, cohort_ids=None):
    if audit["audit_complete"] is not True or audit["exit_code"] != 0 or audit["max_hamming"] != 8:
        raise ValueError("complete historical max_hamming=8 metadata audit required")
    # Only existing TRAIN metadata is projected; no raw paths are opened.
    train = [r for r in audit["samples"] if r["split"] == "train"]
    if cohort_ids is not None:
        if not cohort_ids or not set(cohort_ids) <= {r["sample_id"] for r in train}:
            raise ValueError("explicit nonempty subset of TRAIN IDs required")
        train = [r for r in train if r["sample_id"] in cohort_ids]
    meta, reports = join_reports(train, reports)
    edges = {name: partition_edges(meta, field) for name, field in (
        ("exact", "byte_sha256"), ("pixel", "pixel_sha256"),
        ("point", "point_id"), ("family", "source_family"))}
    if components(meta, edges["exact"]) != components(meta, edges["pixel"]):
        raise ValueError("byte/pixel partition disagreement; do not silently select one")
    near = []
    for p in audit["near_pair_evidence"]:
        if p["split_a"] != "train" or p["split_b"] != "train":
            continue
        a, b, distance = p["sample_id_a"], p["sample_id_b"], p["dhash_distance"]
        if cohort_ids is not None and (a not in cohort_ids or b not in cohort_ids):
            continue
        if a not in meta or b not in meta or type(distance) is not int or not 0 <= distance <= 8:
            raise ValueError("invalid TRAIN near-candidate edge")
        near.append((a, b))
    exact, point, family = edges["exact"], edges["point"], edges["family"]
    scenarios = {"image": [], "exact": exact, "point": point, "family": family,
                 "exact_point": exact + point, "exact_point_family": exact + point + family,
                 "exact_point_near8": exact + point + near,
                 "exact_point_family_near8": exact + point + family + near}
    result = {name: evaluate(meta, reports, components(meta, pairs)) for name, pairs in scenarios.items()}
    for pick in ("first", "last"):
        result[f"exact_representative_{pick}"] = evaluate(meta, reports, components(meta, exact), pick)
    return {
        "status": "PROPOSED_EXPLORATORY_NOT_OFFICIAL_BENCHMARK",
        "scope": "EXISTING_TRAIN_METADATA_AND_SAVED_SCORES_NOT_RAW_AUDIT",
        "source_identity_verified": False, "ci_computed": False, "seed": None,
        "weight_rule": "w_i=1/size_of_assumed_group; retain image labels/scores; global weights within domains",
        "coverage": {"metadata_n": len(meta), "same_id_label_domain_n": len(meta),
                     "saved_success_by_model": {name: len(rows) for name, rows in reports.items()},
                     "support": {level: sum(r["safety_level"] == level for r in meta.values())
                                 for level in ("Level01", "Level02", "Level03", "Level04")}},
        "train_near8_edges_n": len(near), "exact_consistency": exact_score_consistency(meta, reports),
        "scenarios": result,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--metadata-audit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--include-qwen3-available", action="store_true",
                        help="separate S0/S1/S3 and Recovery224 cohorts; never pool or use S2 diagnostic")
    args = parser.parse_args(argv)
    try:
        directory, metadata, output = map(relative_path, (args.input_dir, args.metadata_audit, args.output))
        if output.exists():
            raise ValueError("output already exists; historical results must not be overwritten")
        receipt_bytes = subprocess.check_output(["git", "show", f"{HISTORY}:{RECEIPT}"])
        receipt = json.loads(receipt_bytes)
        locked = receipt["available_export_checks"]
        hashes = locked["inputs_sha256"]
        q25 = checked_bytes(directory / "qwen25_samples.csv", hashes["qwen25_samples.csv"])
        intern = checked_bytes(directory / "InterVL3_Output.zip", hashes["InterVL3_Output.zip"])
        audit = checked_bytes(metadata, receipt["existing_metadata_census"]["source_sha256"])
        audit_object = json.loads(audit)
        reports = {
            "qwen25": report_rows(q25),
            "internvl3": internvl_rows(intern, locked["internvl_report_member_sha256"]),
        }
        report = analyze(audit_object, reports)
        if report["coverage"]["metadata_n"] != receipt["existing_metadata_census"]["n"]:
            raise ValueError("receipt cohort count mismatch")
        for model, key in (("qwen25", "qwen25_saved_score_auroc_recomputed"),
                           ("internvl3", "internvl_saved_score_auroc_recomputed")):
            actual = report["scenarios"]["image"]["strata"]["ALL"]["auroc"][model]
            if actual is None or abs(actual - locked[key]) > 1e-12:
                raise ValueError("saved-score baseline does not reproduce historical receipt")
        if args.include_qwen3_available:
            cohorts, bindings, v4 = {}, {}, []
            for name in ("qwen3_shard0.json", "qwen3_shard1.json", "qwen3_shard3.json", "recovery.json"):
                result = json.loads(checked_bytes(directory / name, hashes[name]))
                archive = result["export"]["archive"]
                if Path(archive).name != archive or "/" in archive or "\\" in archive:
                    raise ValueError("archive basename required")
                rows, binding = archive_report(checked_bytes(directory / archive, result["export"]["archive_sha256"]), result)
                bindings[name] = {**binding, "result_sha256": hashes[name]}
                if name == "recovery.json":
                    cohorts["qwen3_recovery224_only"] = rows
                else:
                    v4.extend(rows)
            # Validate disjoint archived shard membership before forming the
            # S0/S1/S3 subset. Original S2 and recovery never join this cohort.
            index_rows(v4, "true_level")
            cohorts["qwen3_non_s2_shards_only"] = v4
            if {r["sample_id"] for r in v4} & {r["sample_id"] for r in cohorts["qwen3_recovery224_only"]}:
                raise ValueError("unexpected overlap between independent result cohorts")
            report["separate_qwen3_cohorts"] = {}
            for name, rows in cohorts.items():
                ids = {r["sample_id"] for r in rows}
                selected = {model: [r for r in saved if r["sample_id"] in ids] for model, saved in reports.items()}
                selected["qwen3"] = rows
                analysis = analyze(audit_object, selected, ids)
                analysis["cohort_rule"] = name
                analysis["parent_train_n"] = report["coverage"]["metadata_n"]
                analysis["baseline_pooling_allowed"] = False
                report["separate_qwen3_cohorts"][name] = analysis
            report["qwen3_archive_bindings"] = bindings
        report["provenance"] = {
            "history_commit": HISTORY, "receipt_path": RECEIPT,
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "inputs_sha256": {"qwen25_samples.csv": hashes["qwen25_samples.csv"],
                              "InterVL3_Output.zip": hashes["InterVL3_Output.zip"],
                              "duplicate_metadata_audit.json": receipt["existing_metadata_census"]["source_sha256"]},
            "internvl_report_member_sha256": locked["internvl_report_member_sha256"],
            "input_dir": directory.as_posix(), "metadata_audit": metadata.as_posix(),
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "implementation_uncommitted_at_execution": bool(subprocess.check_output(["git", "status", "--porcelain"])),
            "source_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in
                              ("scripts/analyze_source_sensitivity.py", "safeshift/evaluation/sensitivity.py")},
            "python": platform.python_version(), "platform": platform.platform(), "dependencies": [],
            "command": ["python", "-B", "-m", "scripts.analyze_source_sensitivity", *(argv if argv is not None else sys.argv[1:])],
            "output": output.as_posix(),
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
        print(f"PROPOSED saved-score sensitivity written: {output.as_posix()}")
    except (ValueError, KeyError, OSError, csv.Error, zipfile.BadZipFile, tarfile.TarError,
            subprocess.CalledProcessError) as exc:
        parser.exit(2, f"analysis failed: {exc}\n")


if __name__ == "__main__":
    main()
