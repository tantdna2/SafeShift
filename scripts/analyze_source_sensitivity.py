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
from collections import Counter
from math import isfinite

from safeshift.evaluation.sensitivity import (
    components, evaluate, exact_score_consistency, index_rows, join_reports, partition_edges, weighted_auc,
)

HISTORY = "31a04e6f7175cca818c63b4de0153246b3f3ecdb"
RECEIPT = "notes/evidence/three_model_20261023/verification_20261023.json"
S2_ORIGINAL_SHA256 = "2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920"
S2_ORIGINAL_SIZE = 12031765


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


def auc_matches(actual, expected):
    if actual is None or expected is None:
        return actual is expected
    return type(expected) in (int, float) and isfinite(expected) and abs(actual - expected) <= 1e-12


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


def verified_archive_members(payload, export, names):
    """Read only an explicit metadata/report allowlist, bound to the inventory."""
    if (len(payload) != export["archive_bytes"]
            or hashlib.sha256(payload).hexdigest() != export["archive_sha256"]):
        raise ValueError("Qwen3 archive checksum/size mismatch")
    found = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r|gz") as archive:
        for member in archive:
            if member.name in {"manifest.json", *names}:
                if member.name in found or not member.isfile():
                    raise ValueError("unique regular manifest/report members required")
                found[member.name] = archive.extractfile(member).read()
    if set(found) != {"manifest.json", *names}:
        raise ValueError("missing Qwen3 manifest/report")
    if hashlib.sha256(found["manifest.json"]).hexdigest() != export["manifest_sha256"]:
        raise ValueError("Qwen3 manifest checksum mismatch")
    entries = json.loads(found["manifest.json"])["files"]
    inventory = {entry["path"]: entry for entry in entries}
    if len(inventory) != len(entries):
        raise ValueError("unique inventory paths required")
    for name in names:
        entry = inventory[name.removeprefix("evidence/")]
        if len(found[name]) != entry["size_bytes"] or hashlib.sha256(found[name]).hexdigest() != entry["sha256"]:
            raise ValueError("Qwen3 saved metadata/report inventory mismatch")
    return found


def archive_report(payload, result):
    """Bind complete saved reports; this is never raw-logit replay/PASS."""
    found = verified_archive_members(payload, result["export"], {"evidence/report/samples.csv"})
    saved = found["evidence/report/samples.csv"]
    rows = report_rows(saved)
    table = index_rows(rows, "true_level")
    expected = result["metrics"]["overall"]["auroc_pa3"]
    if (len(expected["eligible_ids"]) != len(set(expected["eligible_ids"]))
            or set(table) != set(expected["eligible_ids"])):
        raise ValueError("Qwen3 report/result exact eligible IDs required")
    actual = weighted_auc([r["true_level"] != "Level04" for r in rows],
                          [float(r["pa3_score"]) for r in rows])
    if not auc_matches(actual, expected["value"]):
        raise ValueError("Qwen3 saved-score AUROC differs from pinned result")
    return rows, {"archive_sha256": result["export"]["archive_sha256"],
                  "manifest_sha256": result["export"]["manifest_sha256"], "samples_sha256": hashlib.sha256(saved).hexdigest(),
                  "n_saved_rows": len(rows), "run_id": result["unit"]["run_id"]}


def original_s2_zip(payload):
    """Require the supplied original TAR identity, never the same-attempt rerun."""
    prefix = "Qwen3-Shard2-V4/hnlo-train-v4-qwen3-s2-a1"
    suffixes = (".tar.gz", "_export.json", "_export_sha256.json", "_manifest.json", "_result.json", "_sha256.json")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = archive.namelist()
        expected = {prefix + suffix for suffix in suffixes}
        if len(names) != len(set(names)) or set(names) - {"Qwen3-Shard2-V4/"} != expected:
            raise ValueError("exact unique original S2 ZIP members required")
        if archive.testzip() is not None:
            raise ValueError("S2 ZIP CRC mismatch")
        files = {suffix: archive.read(prefix + suffix) for suffix in suffixes}
    tar = files[".tar.gz"]
    if len(tar) != S2_ORIGINAL_SIZE or hashlib.sha256(tar).hexdigest() != S2_ORIGINAL_SHA256:
        raise ValueError("original S2 archive identity mismatch; diagnostic substitution forbidden")
    result = json.loads(files["_result.json"])
    export = json.loads(files["_export.json"])
    checksum = json.loads(files["_sha256.json"])
    if hashlib.sha256(files["_export.json"]).hexdigest() != json.loads(files["_export_sha256.json"])["sha256"]:
        raise ValueError("S2 export checksum mismatch")
    if export != {**result["export"], "result_sha256": hashlib.sha256(files["_result.json"]).hexdigest()}:
        raise ValueError("S2 result/export mismatch")
    if (export["archive"] != prefix.split("/")[-1] + ".tar.gz"
            or export["archive_bytes"] != len(tar) or export["archive_sha256"] != S2_ORIGINAL_SHA256
            or export["status"] != "EXPORTED" or export["unit"] != result["unit"]
            or checksum["status"] != "EXPORT_VALID" or checksum["sha256"] != S2_ORIGINAL_SHA256
            or checksum["archive"] != export["archive"] or checksum["size_bytes"] != len(tar)
            or checksum["manifest_sha256"] != export["manifest_sha256"]
            or hashlib.sha256(files["_manifest.json"]).hexdigest() != export["manifest_sha256"]
            or checksum["verified_evidence_members"] != len(json.loads(files["_manifest.json"])["files"])):
        raise ValueError("S2 archive/manifest/export binding mismatch")
    # Later compare this sidecar manifest to the hash-bound member inside TAR.
    return tar, result, {
        "S2_ORIGINAL_IDENTITY": "PASS", "zip_sha256": hashlib.sha256(payload).hexdigest(),
        "zip_size_bytes": len(payload), "zip_crc": "PASS", "zip_member_count": len(names),
        "sidecars": {prefix.split("/")[-1] + suffix: {"sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
                     for suffix, b in files.items()},
    }


def verify_v4_shard(payload, result, expected_unit, inference, scope, train_metadata):
    """Validate all planned rows/statuses before selecting SUCCESS for AUROC."""
    unit = result["unit"]
    if unit != expected_unit or unit["model"] != "qwen3" or result["export"]["unit"] != unit:
        raise ValueError("original V4 unit identity required; recovery/rerun pooling forbidden")
    found = verified_archive_members(payload, result["export"],
                                     {"evidence/report/samples.csv", "evidence/binding.json", "evidence/result.json"})
    binding = json.loads(found["evidence/binding.json"])
    inside = json.loads(found["evidence/result.json"])
    if inside != {k: v for k, v in result.items() if k != "export"}:
        raise ValueError("internal and external result mismatch")
    if (binding["unit"] != unit or binding["authority"]["scope"] != scope
            or binding["samples"] != inference):
        raise ValueError("V4 config or historical ordered shard membership mismatch")
    if (result["schema"] != "hnlo-train-unit-result-v1" or result["scope"] != "DESCRIPTIVE_FULL_TRAIN"
            or result["retry"] is not False or result["research_generalization_claim"] is not False):
        raise ValueError("original V4 result scope mismatch")
    rows = report_rows(found["evidence/report/samples.csv"])
    table = index_rows(rows, "true_level")
    planned = [r["sample_id"] for r in inference]
    if (len(set(planned)) != len(planned) or len(planned) != unit["count"]
            or [r["sample_id"] for r in rows] != planned):
        raise ValueError("exact planned report IDs/order required")
    journal = result["sample_journal"]
    if [r["sample_id"] for r in journal] != planned or [r["ordinal"] for r in journal] != list(range(len(planned))):
        raise ValueError("exact journal membership/order required")
    statuses = Counter()
    for position, row in enumerate(rows):
        sid, status = row["sample_id"], row["status"]
        meta = train_metadata[sid]
        if (row["true_level"] != meta["safety_level"] or row["domain"] != meta["folder_domain"]
                or inference[position]["image_sha256"] != meta["byte_sha256"]
                or row["true_binary_label"] != ("Normal" if row["true_level"] == "Level04" else "Anomaly")):
            raise ValueError("planned ID/ground truth/domain/image-hash mismatch")
        if status not in {"SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED"}:
            raise ValueError("unexpected V4 status")
        flags = (status != "NOT_ATTEMPTED", status == "SUCCESS", status == "SUCCESS")
        entry = journal[position]
        if (entry["status"] != status
                or tuple(row[k] for k in ("attempted", "persisted", "parsed")) != tuple(str(x) for x in flags)
                or tuple(entry[k] for k in ("attempted", "persisted", "parsed")) != flags):
            raise ValueError("saved status/journal/flags mismatch")
        if status != "SUCCESS" and (row["pa3_score"] != "" or row["generated_label"] != ""):
            raise ValueError("non-success row must not become a scored prediction")
        statuses[status] += 1
    saved_coverage = result["coverage"]
    expected_counts = {key: statuses[key] for key in saved_coverage["status_counts"]}
    if (set(statuses) - set(expected_counts) or saved_coverage["status_counts"] != expected_counts
            or saved_coverage["planned"] != len(rows) or saved_coverage["scored"] != statuses["SUCCESS"]
            or saved_coverage["attempted"] != statuses["SUCCESS"] + statuses["TECHNICAL_ERROR"]
            or saved_coverage["parsed"] != statuses["SUCCESS"] or saved_coverage["persisted"] != statuses["SUCCESS"]
            or saved_coverage["anomaly_n"] != sum(r["true_level"] != "Level04" for r in rows)
            or saved_coverage["normal_n"] != sum(r["true_level"] == "Level04" for r in rows)
            or saved_coverage["level_counts"] != dict(Counter(r["true_level"] for r in rows))
            or abs(saved_coverage["coverage"] - statuses["SUCCESS"] / len(rows)) > 1e-12
            or result["status"] != ("COMPLETE" if statuses["SUCCESS"] == len(rows) else "PARTIAL")):
        raise ValueError("saved coverage/counts mismatch")
    success = [r for r in rows if r["status"] == "SUCCESS"]
    metadata = [train_metadata[r["sample_id"]] for r in success]
    join_reports(metadata, {"qwen3": success})
    expected = result["metrics"]["overall"]["auroc_pa3"]
    positives = sum(r["true_level"] != "Level04" for r in success)
    negatives = len(success) - positives
    auc = weighted_auc([r["true_level"] != "Level04" for r in success], [float(r["pa3_score"]) for r in success])
    for endpoint in (expected, saved_coverage["auroc"]):
        ids = endpoint["eligible_ids"]
        if (len(set(ids)) != len(ids) or set(ids) != {r["sample_id"] for r in success}
                or endpoint["positive_n"] != positives or endpoint["negative_n"] != negatives
                or endpoint["pair_denominator"] != positives * negatives or endpoint["tie_credit"] != 0.5
                or not auc_matches(auc, endpoint["value"])):
            raise ValueError("saved eligible IDs/support/AUROC mismatch")
    return rows, {
        "status": "PASS_SAVED_SCORE_NOT_RAW_AUDIT", "unit": unit,
        "archive_sha256": result["export"]["archive_sha256"], "archive_size_bytes": len(payload),
        "manifest_sha256": result["export"]["manifest_sha256"],
        "members": {name: {"sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
                    for name, b in found.items()},
        "source": {k: binding["source"][k] for k in
                   ("implementation_commit", "authority_commit", "merge_commit", "payload_sha256", "pr_number")},
        "planned_n": len(rows), "status_counts": dict(sorted(statuses.items())),
        "success_positive_n": positives, "success_negative_n": negatives, "auroc_recomputed": auc,
        "ordered_ids_and_image_hashes_match_history": True, "config_scope_matches_history": True,
    }


def verify_v4_cohort(shards, metadata):
    """Keep all planned statuses; no recovery or duplicate-diagnostic substitution."""
    if set(shards) != {0, 1, 2, 3}:
        raise ValueError("four original V4 shards required")
    if shards[2][1]["archive_sha256"] != S2_ORIGINAL_SHA256:
        raise ValueError("original S2 hash required; diagnostic substitution forbidden")
    rows, sources = [], []
    for shard in range(4):
        saved, verified = shards[shard]
        unit = verified["unit"]
        if (unit["run_id"] != f"hnlo-train-v4-qwen3-s{shard}-a1"
                or unit["attempt_id"] != f"hnlo-train-v4-qwen3-s{shard}-20261019-a1"
                or unit["shard"] != shard or unit["count"] != len(saved)):
            raise ValueError("original V4 shard identity required; recovery pooling forbidden")
        rows.extend(saved)
        sources.append(verified["source"])
    if any(source != sources[0] for source in sources):
        raise ValueError("V4 source/release disagreement")
    common = ("model", "id", "revision", "python", "cuda", "cuda_visible_devices")
    if any(tuple(shards[k][1]["unit"][f] for f in common) !=
           tuple(shards[0][1]["unit"][f] for f in common) for k in shards):
        raise ValueError("V4 model/runtime disagreement")
    table = index_rows(rows, "true_level")
    if set(table) != set(metadata):
        raise ValueError("exact full planned TRAIN cohort required")
    counts = Counter(r["status"] for r in rows)
    if counts != Counter({"SUCCESS": 3539, "TECHNICAL_ERROR": 1, "NOT_ATTEMPTED": 223}) or len(rows) != 3763:
        raise ValueError("original V4 status totals mismatch")
    # All rows, including failures/not-attempted, remain in this coverage receipt.
    return [r for r in rows if r["status"] == "SUCCESS"], {
        "V4_ORIGINAL_COHORT_VERIFICATION": "PASS", "planned_n": len(rows), "status_counts": dict(counts),
        "success_n": counts["SUCCESS"], "coverage": counts["SUCCESS"] / len(rows),
        "baseline_pooling_allowed": False, "raw_audit_performed": False,
        "shards": {str(k): v[1] for k, v in shards.items()},
    }


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
    parser.add_argument("--qwen3-original-s2-zip",
                        help="optional original S2 ZIP; adds original V4-success cohort, never recovery pooling")
    args = parser.parse_args(argv)
    try:
        directory, metadata, output = map(relative_path, (args.input_dir, args.metadata_audit, args.output))
        if output.exists():
            raise ValueError("output already exists; historical results must not be overwritten")
        if args.qwen3_original_s2_zip and not args.include_qwen3_available:
            raise ValueError("original S2 requires the other verified Qwen3 archives")
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
            original, historical = {}, {}
            train_metadata = {r["sample_id"]: r for r in audit_object["samples"] if r["split"] == "train"}
            if args.qwen3_original_s2_zip:
                authority_path = "configs/diagnostics/hnlo_train_authority.v4.json"
                authority_bytes = subprocess.check_output(["git", "show", f"{HISTORY}:{authority_path}"])
                scope = json.loads(authority_bytes)["scope"]
                units = {u["shard"]: u for u in scope["units"] if u["model"] == "qwen3"}
                historical[authority_path] = hashlib.sha256(authority_bytes).hexdigest()
                inference = {}
                for shard in range(4):
                    path = f"data/manifests/pa3_full_train_shard{shard}.v1.json"
                    payload = subprocess.check_output(["git", "show", f"{HISTORY}:{path}"])
                    digest = hashlib.sha256(payload).hexdigest()
                    if digest != units[shard]["inference_sha256"]:
                        raise ValueError("historical inference manifest hash mismatch")
                    historical[path] = digest
                    inference[shard] = json.loads(payload)["samples"]
            for name in ("qwen3_shard0.json", "qwen3_shard1.json", "qwen3_shard3.json", "recovery.json"):
                result = json.loads(checked_bytes(directory / name, hashes[name]))
                archive = result["export"]["archive"]
                if Path(archive).name != archive or "/" in archive or "\\" in archive:
                    raise ValueError("archive basename required")
                payload = checked_bytes(directory / archive, result["export"]["archive_sha256"])
                if args.qwen3_original_s2_zip and name != "recovery.json":
                    shard = result["unit"]["shard"]
                    all_rows, binding = verify_v4_shard(payload, result, units[shard], inference[shard], scope, train_metadata)
                    original[shard] = (all_rows, binding)
                    rows = [r for r in all_rows if r["status"] == "SUCCESS"]
                else:
                    rows, binding = archive_report(payload, result)
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
            if args.qwen3_original_s2_zip:
                zip_path = relative_path(args.qwen3_original_s2_zip)
                payload, result, zip_receipt = original_s2_zip(zip_path.read_bytes())
                original[2] = verify_v4_shard(payload, result, units[2], inference[2], scope, train_metadata)
                success, verification = verify_v4_cohort(original, train_metadata)
                zip_receipt["S2_SAVED_SCORE_VERIFICATION"] = "PASS"
                cohorts["qwen3_original_v4_success_only"] = success
                report["original_qwen3_v4"] = {**verification, "s2_supplied_zip": zip_receipt,
                                               "historical_contract_sha256": historical}
                # Do not pool success with recovery, even when they complement.
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
            if args.qwen3_original_s2_zip:
                original_auc = report["separate_qwen3_cohorts"]["qwen3_original_v4_success_only"]["scenarios"]["image"]["strata"]["ALL"]["auroc"]["qwen3"]
                report["original_qwen3_v4"]["V4_ORIGINAL_AUROC_RECOMPUTED"] = original_auc
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
