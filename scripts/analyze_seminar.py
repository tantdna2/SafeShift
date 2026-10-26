"""One-command M3 CPU synthetic rehearsal; real inputs are deliberately closed."""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from safeshift.data.saved_reports import (
    AUTHORITY_PATH, CONFIG_PATH, CONFIG_SHA, PROTOCOL_PATH, AuthorityError, IntegrityError,
    NOTICE, confined, git, json_bytes, membership, read_synthetic, sha256, verify_authority,
)
from safeshift.evaluation.seminar import analyze, long_rows

ROOT = Path(__file__).resolve().parents[1]
LONG_FIELDS = ["notice", "output_id", "row_id", "cohort_id", "model_or_pair", "stratum", "metric_id",
               "signal_id", "variant_id", "numerator", "denominator", "value", "status", "reason",
               "membership_sha256", "planned_n", "eligible_n", "positive_n", "negative_n",
               "excluded_by_reason", "run_refs", "input_refs", "evidence_level", "json_pointer"]
NAMES = {"R2": "R2_classification_ranking", "R3": "R3_dangerous_errors_sensitivity", "R4": "R4_disagreement_errors"}
LIMITS = ["B01: 19 hazard placeholders BLOCKED; no sample-to-atom/group mapping.",
          "B02: continuous logit controls N/A; no superiority/confounding claim against unavailable controls.",
          "B03: saved-report provenance limitation; no new raw audit, no inferred attempts/native semantics.",
          "B05: mismatch/proxy BLOCKED; five folder domains retained; no verified source/causal claim.",
          "Moondream2 retained in four-model roster, quantitative TRAIN N/A at project level only.",
          "Exposed TRAIN is not holdout/generalization evidence; no source CI or independent-source claim.",
          "Qwen3 original partial coverage and assumed completion bounds are not full-TRAIN measured results.",
          "Recovery224 reference-only, never pooled. HNLO hazard ranking is not calibrated probability.",
          "No academic approval is inferred. M4 requires separate real-artifact authority."]


def write_json(path, value):
    with path.open("xb") as stream:
        stream.write(json_bytes(value))


def write_csv(path, rows, fields=None):
    fields = fields or sorted({key for row in rows for key in row})
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False, sort_keys=True, allow_nan=False)
                             if isinstance(v, (list, dict)) else v for k, v in row.items()})


def report_rows(report_id, result, config):
    """Add denominator, membership, provenance and eligibility to long rows."""
    rows = long_rows(report_id, result[report_id], {})
    ledger = result["ledger"]
    for row in rows:
        path = row["metric_id"].split("/")
        cohort = next((p for p in path if p in ("T3763", "V3539")), None)
        if "three_model_main" in path:
            cohort = "V3539"
        elif "two_model_secondary" in path or "completion_bounds" in path or "missing_composition" in path:
            cohort = "T3763"
        stratum = next((p for p in path if p in ("ALL", *config["domains"])), "ALL")
        model = next((p for p in path if p in (*config["models"],)), None)
        pair = next((p for p in path if "|" in p or "->" in p), None)
        variant = next((p for p in path if p in config["sensitivity"]["variants"]), "")
        if report_id == "R4" and model is None:
            model = pair or ("qwen25|internvl3|qwen3" if cohort == "V3539" else "qwen25|internvl3")
        if "completion_bounds" in path or "missing_composition" in path:
            model = "qwen3"
        if model is None and cohort:
            model = "|".join(config["cohorts"][cohort]["models"])
        selection = [r for r in ledger if r["cohort_id"] == cohort and
                     (stratum == "ALL" or r["folder_domain"] == stratum) and
                     (r["model_id"] in (model or "").replace("->", "|").split("|"))]
        ids = sorted({r["sample_id"] for r in selection})
        planned_ids = ids[:]
        if report_id == "R3" and "sensitivity" in path and cohort:
            panel = result["R3"]["sensitivity"][cohort]
            if variant:
                retained = set(panel["variants"][variant]["weights"])
                selection = [r for r in selection if r["sample_id"] in retained]
                ids = sorted({r["sample_id"] for r in selection})
            elif "exact_consistency" in path:
                position = path.index("exact_consistency") + 1
                retained = set(panel["exact_consistency"][int(path[position])]["ids"])
                selection = [r for r in selection if r["sample_id"] in retained]
                ids = sorted({r["sample_id"] for r in selection})
        excluded = {}
        # Resolve the closest explicit eligibility object along the JSON path.
        node, info, parent_node = result[report_id], None, None
        for part in path:
            if isinstance(node, dict) and "eligibility" in node:
                info = node["eligibility"]
            try:
                parent_node = node
                node = node[int(part)] if isinstance(node, list) else node[part]
            except (KeyError, IndexError, TypeError, ValueError):
                break
        if info:
            eligible_set = "J" if "paired_J" in path or "delta" in path else "F" if "hnlo_F" in path else "O"
            row["eligible_n"] = info["counts"][eligible_set]
            digest = info["membership"][eligible_set]
            excluded = info["excluded"][eligible_set]
        else:
            if report_id == "R4" and cohort and model != "moondream2":
                panel_name = "three_model_main" if cohort == "V3539" else "two_model_secondary"
                panel = result["R4"][panel_name][stratum]
                ids = panel["joint_ids"]
                association = next((p for p in path if p in ("joint", "B04", "B04_matched")), None)
                if "association" in path and association:
                    ids = panel["association"][association]["ids"]
                excluded = {"non_joint_or_signal_missing": len(planned_ids) - len(ids)}
            elif report_id == "R3" and model in config["models"] and "completion_bounds" not in path:
                ids = sorted({r["sample_id"] for r in selection if r["persisted"]})
                excluded = {"no_output": len(planned_ids) - len(ids)}
            row["eligible_n"] = row.get("eligible_n") if row.get("eligible_n") is not None else len(ids)
            digest = membership(ids)
        applicable = cohort is not None and model != "moondream2"
        row.update({"cohort_id": cohort or "NOT_APPLICABLE", "model_or_pair": model or "NOT_APPLICABLE",
                    "stratum": stratum, "variant_id": variant, "membership_sha256": digest,
                    "planned_n": len(planned_ids) if applicable else None,
                    "excluded_by_reason": excluded, "run_refs": sorted({r["run_id"] for r in selection}),
                    "input_refs": sorted({r["input_ref"] for r in selection}), "evidence_level": "SYNTHETIC"})
        if not applicable:
            row["eligible_n"] = None
        if "completion_bounds" in path and path[-1] in ("lower", "upper"):
            row["denominator"] = parent_node["denominator"]
            row["numerator"] = parent_node["observed_errors"] + (parent_node["missing_support"] if path[-1] == "upper" else 0)
        if row["positive_n"] is None and applicable and report_id != "R4":
            eligible_ids = set(ids)
            if info:
                eligible_ids = {r["sample_id"] for r in selection if r["persisted"] and
                    (eligible_set != "F" or r["hnlo_score"] is not None) and
                    (eligible_set != "J" or (r["hnlo_score"] is not None and r["generated_label"] is not None))}
            truth = {r["sample_id"]: r["true_level"] for r in selection if r["sample_id"] in eligible_ids}
            row["positive_n"] = sum(level != "Level04" for level in truth.values())
            row["negative_n"] = len(truth) - row["positive_n"]
        # Every CSV column is explicit; JSON keeps full structured details.
        for field in LONG_FIELDS:
            row.setdefault(field, None)
    return rows


def run(root, config_path, output_dir, command):
    config, authority = verify_authority(root, config_path)
    output = confined(root, output_dir, ("data", "processed", "seminar"))
    if len(Path(output_dir).parts) < 4:
        raise ValueError("output must name a new run directory")
    if output.exists():
        raise FileExistsError("output directory already exists; overwrite refused")
    metadata, reports, near, inputs = read_synthetic(config)
    result = analyze(metadata, reports, near, config)
    # Compute everything before reserving the new run directory. mkdir is atomic;
    # a failed write leaves an incomplete directory, never a success receipt.
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    write_json(output / "cohort_membership.json", {"notice": NOTICE, "cohorts": result["memberships"]})
    write_csv(output / "ledger.csv", result["ledger"])
    for row in result["R1"]:
        row["row_id"] = "R1_" + sha256(json_bytes([row["cohort_id"], row["model_id"], row["stratum"]]))[:20]
    write_csv(output / "R1_evidence_coverage.csv", result["R1"])
    rows_by_report = {}
    for report_id, name in NAMES.items():
        rows = report_rows(report_id, result, config)
        rows_by_report[report_id] = rows
        write_json(output / (name + ".json"), {"schema_version": "safeshift-seminar-output-v1", "notice": NOTICE, "output_id": report_id,
                   "receipt": "receipt.json", "details": result[report_id], "rows": rows})
        write_csv(output / (name + ".csv"), rows, LONG_FIELDS)
    trace = {}
    for rq, reports_for_rq in (("S-RQ1", ("R1", "R2")), ("S-RQ2", ("R1", "R3")), ("S-RQ3", ("R1", "R4"))):
        trace[rq] = {"status": "PENDING_ANALYST_M4", "conclusion": None,
                     "row_ids": {r: [x["row_id"] for x in (result["R1"] if r == "R1" else rows_by_report[r])]
                                 for r in reports_for_rq},
                     "input_refs": sorted({r["input_ref"] for r in result["ledger"]})}
    summary = {"notice": NOTICE, "status": "PENDING_ANALYST_M4", "task": "M3-01",
               "scientific_conclusions": None, "roster": list(config["models"]), "trace": trace,
               "limitations": LIMITS, "real_artifact_access": False, "receipt": "receipt.json"}
    write_json(output / "summary.json", summary)
    text = NOTICE + "\n\nR5 — PENDING_ANALYST_M4\n\n"
    for rq, entry in trace.items():
        text += rq + ": PENDING_ANALYST_M4. Exact row IDs and input refs: summary.json#/trace/" + rq + ".\n\n"
        text += "Example trace: " + ", ".join(ids[0] for ids in entry["row_ids"].values() if ids) + ".\n\n"
    text += "\n".join("- " + line for line in LIMITS) + "\n"
    with (output / "R5_trace_limits.md").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    source_paths = ["safeshift/data/saved_reports.py", "safeshift/evaluation/seminar.py",
                    "safeshift/evaluation/metrics.py", "safeshift/evaluation/sensitivity.py",
                    "safeshift/data/schema.py", "safeshift/data/validation.py", "scripts/analyze_seminar.py"]
    receipt = {"notice": NOTICE, "status": "PASS_SYNTHETIC_SOFTWARE_ONLY", "authority": authority,
               "source_sha": git(root, "rev-parse", "HEAD").decode().strip(),
               "source_files": {p: sha256(confined(root, p).read_bytes()) for p in source_paths},
               "source_dirty": bool(git(root, "status", "--porcelain", "--", *source_paths).strip()),
               "inputs": inputs, "protocol_path": PROTOCOL_PATH, "config_path": CONFIG_PATH,
               "authority_path": AUTHORITY_PATH, "command": command, "seed": None,
               "fixture": "hand-authored-twelve-records-v1", "output_dir": output_dir,
               "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                               "platform": sys.platform, "dependencies": "Python standard library only"},
               "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "outputs": {p.name: sha256(p.read_bytes()) for p in sorted(output.iterdir()) if p.is_file()},
               "artifact_checks": "NOT_RUN_NO_M4_AUTHORITY", "model_execution": False,
               "limitations": LIMITS}
    write_json(output / "receipt.json", receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=NOTICE + "; bundled CPU fixtures only")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    command = ["python", "-B", "scripts/analyze_seminar.py", "--config", args.config, "--output-dir", args.output_dir]
    try:
        receipt = run(ROOT, args.config, args.output_dir, command)
    except AuthorityError as exc:
        print("AUTHORITY: " + str(exc), file=sys.stderr)
        return 3
    except IntegrityError as exc:
        print("INTEGRITY: " + str(exc), file=sys.stderr)
        return 4
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        print("DATA: " + str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print("IO: " + str(exc), file=sys.stderr)
        return 5
    print(json.dumps({"notice": NOTICE, "output_dir": args.output_dir, "files": sorted([*receipt["outputs"], "receipt.json"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
