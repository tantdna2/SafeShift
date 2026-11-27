"""One-command M3 CPU synthetic rehearsal; real inputs are deliberately closed."""

import argparse
import csv
from collections import Counter
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
from safeshift.evaluation.seminar import analyze, eligibility, exclusion_reason, long_rows

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


def row_scope(path, config, panels):
    """Read model/cohort keys only in schema positions that name them."""
    section = path[0]
    cohort, stratum, model, variant = None, "ALL", None, ""
    if section in panels:
        spec = panels[section]
        cohort, stratum = spec["cohort"], path[1]
        if path[2] in ("pairwise", "complementarity"):
            model = path[3]
        elif path[2] in ("hnlo_true_predicted_binary", "hnlo_global_error_detection"):
            model = "qwen3"
        else:
            model = "|".join(spec["models"])
    elif section in ("missing_composition", "completion_bounds"):
        cohort = "M224" if section == "missing_composition" else "T3763"
        stratum, model = path[1], "qwen3"
    elif section in ("T3763", "V3539"):
        cohort, stratum, model = path[:3]
    elif section == "sensitivity":
        cohort = path[1]
        if path[2] == "variants":
            variant = path[3]
            if path[4] == "strata":
                stratum = path[5]
                if path[6] == "models":
                    model = path[7]
        elif path[2] == "exact_consistency":
            model = path[5]
        model = model or "|".join(config["cohorts"][cohort]["models"])
    elif section == "moondream2":
        model = section
    return cohort, stratum, model, variant


def disagreement_members(path, panel, selection):
    field = path[2]
    if field in ("panel_n", "missing_invalid_combinations"):
        return set(panel["panel_ids"]), None
    if field == "hnlo_true_predicted_binary":
        return set(panel[field][path[3]]["ids"]), "outside_finite_qwen3_joint_cell"
    if field == "hnlo_global_error_detection":
        return set(), "not_in_v1"
    if field == "signals":  # One disagreement score per joint sample.
        return {path[3]}, "other_panel_ids"
    if field == "association":
        group = panel[field][path[3]]
        ids = set(group["ids"])
        if path[4:5] == ["signals"] and path[6:7] == ["risk_coverage"] and path[-1] == "risk4":
            signal = path[5]
            threshold = group["signals"][signal]["risk_coverage"][int(path[7])]["threshold"]
            if threshold is None:
                return set(), "outside_retained_tie_blocks"
            if signal == "HNLO_Q3":
                retained = {r["sample_id"] for r in selection if r["model_id"] == "qwen3" and
                            r["sample_id"] in ids and r["hnlo_score"] <= threshold}
            else:
                retained = {sid for sid in ids if panel["signals"][sid][signal] <= threshold}
            return retained, "outside_retained_tie_blocks"
        return ids, "outside_association_panel"
    return set(panel["joint_ids"]), "outside_joint_panel"


def ranking_members(path, sets, info):
    """Resolve both metric populations and the diagnostic counts about them."""
    if "eligibility" in path:
        kind, name, *bucket = path[path.index("eligibility") + 1:]
        if kind == "excluded":
            accepted = {r["sample_id"] for r in sets[name]}
            rows = [r for r in sets["P"] if r["sample_id"] not in accepted]
            if bucket[0] == "by_reason":
                rows = [r for r in rows if exclusion_reason(r) == bucket[1]]
            elif bucket[0] in ("by_level", "by_domain"):
                key = "true_level" if bucket[0] == "by_level" else "folder_domain"
                rows = [r for r in rows if r[key] == bucket[1]]
            return rows, None
    else:
        name = "J" if "paired_J" in path or "delta" in path else "F" if "hnlo_F" in path else "O"
    return sets[name], info["excluded"][name]


def ranking_exclusions(breakdown, variant_rows, planned_rows):
    if len(variant_rows) == len(planned_rows):
        return breakdown
    retained = {r["sample_id"] for r in variant_rows}
    outside = [r for r in planned_rows if r["sample_id"] not in retained]
    return {"n": breakdown["n"] + len(outside),
            "by_reason": {**breakdown["by_reason"], "outside_variant": len(outside)},
            "by_level": dict(Counter(breakdown["by_level"]) + Counter(r["true_level"] for r in outside)),
            "by_domain": dict(Counter(breakdown["by_domain"]) + Counter(r["folder_domain"] for r in outside))}


def report_rows(report_id, result, config):
    """Attach planned and eligible populations to the unchanged numeric endpoints."""
    rows = long_rows(report_id, result[report_id], {})
    panels = {spec["id"]: spec for spec in config["disagreement_panels"]}
    ledger = result["ledger"]
    missing = set(result["memberships"]["M224"]["ids"])
    ranking_cache = {}
    for row in rows:
        path = [part.replace("~1", "/").replace("~0", "~") for part in row["json_pointer"][1:].split("/")]
        cohort, stratum, model, variant = row_scope(path, config, panels)
        ledger_cohort = "T3763" if cohort == "M224" else cohort
        # Parent-planned coverage ratios use T3763 even in the V3539 panel.
        if report_id == "R4" and path[-1] in ("joint_to_parent_planned", "panel_to_planned"):
            ledger_cohort = "T3763"
        models = (model or "").replace("->", "|").split("|")
        selection = [r for r in ledger if r["cohort_id"] == ledger_cohort and r["model_id"] in models and
                     (stratum == "ALL" or r["folder_domain"] == stratum) and
                     (cohort != "M224" or r["sample_id"] in missing)]
        planned_ids = {r["sample_id"] for r in selection}
        ids = planned_ids
        excluded, reason = {}, None
        if path[0] in panels:
            panel = result["R4"][path[0]][stratum]
            ids, reason = disagreement_members(path, panel, selection)
        elif path[0] == "missing_composition":
            ids = {r["sample_id"] for r in selection if r["true_level"] == path[2]}
            reason = "other_missing_levels"
        elif path[0] == "completion_bounds":
            bounds = result["R3"]["completion_bounds"][stratum][path[2]]
            if path[-1] in ("lower", "upper"):
                row["denominator"] = bounds["denominator"]
                row["numerator"] = bounds["observed_errors"] + (bounds["missing_support"] if path[-1] == "upper" else 0)
        elif model and model != "moondream2":
            if variant:
                details = result["R3"]["sensitivity"][cohort]["variants"][variant]
                if path[4] == "weights":
                    ids, reason = {path[5]}, "other_variant_ids"
                elif path[4] == "strata":
                    ids, reason = planned_ids.intersection(details["weights"]), "outside_variant"
            elif path[0] == "sensitivity" and path[2] == "exact_consistency":
                group = result["R3"]["sensitivity"][cohort]["exact_consistency"][int(path[3])]
                ids, reason = set(group["ids"]), "outside_exact_group"
                if path[-1] in ("score_available_n", "score_spread", "within_group_hazard_auc"):
                    ids &= {r["sample_id"] for r in selection if r["hnlo_score"] is not None}
                    reason = "outside_scored_exact_group"
            is_ranking = (report_id == "R2" or (variant and path[4] == "strata" and path[6] == "models"))
            if is_ranking:
                key = cohort, stratum, model, variant
                if key not in ranking_cache:
                    ranking_cache[key] = eligibility([r for r in selection if r["sample_id"] in ids])
                sets, info = ranking_cache[key]
                eligible_rows, breakdown = ranking_members(path, sets, info)
                ids = {r["sample_id"] for r in eligible_rows}
                if breakdown is not None:
                    excluded = ranking_exclusions(breakdown, sets["P"], selection)
                    reason = None
                else:
                    reason = "outside_exclusion_bucket"
            elif path[0] in ("T3763", "V3539"):
                ids = {r["sample_id"] for r in selection if r["persisted"]}
                reason = "no_output"
        if not ids <= planned_ids or row["eligible_n"] not in (None, len(ids)):
            raise ValueError("metric membership disagrees with its population: " + row["metric_id"])
        if reason:
            excluded = {reason: len(planned_ids) - len(ids)}
        eligible_rows = [r for r in selection if r["sample_id"] in ids]
        applicable = cohort is not None and model != "moondream2"
        row.update({"cohort_id": cohort or "NOT_APPLICABLE", "model_or_pair": model or "NOT_APPLICABLE",
                    "stratum": stratum, "variant_id": variant, "membership_sha256": membership(ids),
                    "planned_n": len(planned_ids) if applicable else None, "eligible_n": len(ids) if applicable else None,
                    "excluded_by_reason": excluded, "run_refs": sorted({r["run_id"] for r in eligible_rows}),
                    "input_refs": sorted({r["input_ref"] for r in eligible_rows}), "evidence_level": "SYNTHETIC"})
        if row["positive_n"] is None and applicable and (report_id != "R4" or path[2] == "hnlo_true_predicted_binary"):
            positive = {r["sample_id"] for r in eligible_rows if r["true_level"] != "Level04"}
            row["positive_n"], row["negative_n"] = len(positive), len(ids) - len(positive)
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
