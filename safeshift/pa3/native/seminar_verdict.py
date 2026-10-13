"""Predeclared seminar-direction metrics, GO/NO-GO rule and verdict rendering.

CPU only, from CPU-audited raw rows and the post-seal GT join. No model call,
threshold search, score reversal, parameter learning, prompt change or CI.

python -m safeshift.pa3.native.seminar_verdict --run RUN_DIR --snapshot TOKENIZER_DIR --output OUT
python -m safeshift.pa3.native.seminar_verdict --not-executed REASON --output OUT
"""

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from safeshift.ls1.core import LEVELS
from safeshift.protocol.schema import strict_json
from ..artifacts import json_bytes
from . import analysis, seminar
from .journal import Journal
from .native_score import STATUSES

VERDICT = "PA3_SEMINAR_DIRECTION_VERDICT.md"
PER_IMAGE = "pa3_seminar_direction_per_image.csv"
METRICS = "pa3_seminar_direction_metrics.json"
GO, KEEP = "GO_PA3", "KEEP_CURRENT_DIRECTION"
COVERAGE, MACRO_AUROC, MACRO_DELTA, DOMAIN_WINS = Fraction(95, 100), Fraction(3, 4), Fraction(15, 100), 3
CRITERIA = {
    "C1_COVERAGE": "Four primary domains: >=95% of Normal AND >=95% of Anomaly have a valid PA3 score",
    "C2_MACRO_AUROC": "Macro-domain PA3 AUROC over the four primary domains >= 0.75 (all four defined)",
    "C3_MACRO_DELTA": "Macro PA3 AUROC - macro Qwen generated-binary-label AUROC >= 0.15, same eligible IDs",
    "C4_DOMAIN_WINS": "PA3 AUROC > generated-binary-label AUROC in at least 3 of 4 primary domains",
    "C5_TECHNICAL_INTEGRITY": "Sealed completed run, CPU audit/recomputation PASS, dataset checksums 90/90, "
                              "exposure sealed, zero TECHNICAL_ERROR/INTERRUPTED/UNPROCESSED/NOT_ATTEMPTED",
}
REASONS = ("NOT_EXECUTED", "INCOMPLETE", "TECHNICAL_FAIL", "INSUFFICIENT_VALID_DATA", "PERFORMANCE_NOT_CONVINCING")
NOT_PERMITTED = [
    "PA3 đã được xác nhận khoa học, hoặc kết quả là confirmatory benchmark / kết quả Seminar chính thức.",
    "Hiệu năng khái quát hóa sang TEST, miền khác, robot khác hoặc dữ liệu ngoài 90 ảnh InspecSafe TRAIN này.",
    "Cohort 90 ảnh là độc lập thống kê, chưa từng quan sát, clean holdout hoặc không liên hệ với TEST.",
    "Bất kỳ khoảng tin cậy, p-value hoặc kiểm định ý nghĩa nào từ lượt chẩn đoán này.",
    "PA3 cải thiện accuracy, an toàn vận hành hoặc giảm bỏ sót nguy hiểm; không có threshold nào được chọn.",
    "Kết quả Metallurgy hoặc Level03 là bằng chứng riêng; cả hai chỉ mang tính mô tả.",
    "Calibration, ngưỡng, prompt hoặc quy tắc dự đoán mới được học hay chọn từ 90 ảnh này.",
]


def num(value):
    return None if value is None else {"value": float(value), "exact": f"{value.numerator}/{value.denominator}"}


def exact(ep):
    """Mann-Whitney AUROC with 0.5 tie credit is a multiple of 1/(2*pairs)."""
    if ep["value"] is None:
        return None
    doubled = ep["value"] * ep["pair_denominator"] * 2
    if abs(doubled - round(doubled)) > 1e-6:
        raise ValueError("AUROC_NOT_HALF_INTEGER_PAIR_COUNT")
    return Fraction(round(doubled), 2 * ep["pair_denominator"])


def view(ep):
    return {**(num(exact(ep)) or {"value": None, "exact": None}), "positive_n": ep["positive_n"], "negative_n": ep["negative_n"], "pairs": ep["pair_denominator"],
            "eligible_n": len(ep["eligible_ids"]), "reason": ep["reason"], "tie_credit": ep["tie_credit"]}


def generated_binary(row):
    return float(row["generated_label"] != "Level04")


def ratio(k, n):
    return {"k": k, "n": n, "value": k / n if n else None}


def block(rows, metadata):
    gt = {r["sample_id"]: metadata[r["sample_id"]]["level"] for r in rows}
    scored = [r for r in rows if r["status"] == "SUCCESS"]
    label = lambda r: r["generated_label"] if r["parsed"] else None
    four = lambda r: label(r) == gt[r["sample_id"]]
    two = lambda r: label(r) is not None and (label(r) == "Level04") == (gt[r["sample_id"]] == "Level04")
    pa3, gen = analysis.endpoint(rows, metadata), analysis.endpoint(rows, metadata, generated_binary)
    a, b = exact(pa3), exact(gen)
    predictions = Counter(label(r) or "UNPARSED" for r in rows)
    coverage = {}
    for cls in ("Normal", "Anomaly"):
        members = [r for r in rows if seminar.binary(gt[r["sample_id"]]) == cls]
        coverage[cls] = ratio(sum(r["status"] == "SUCCESS" for r in members), len(members))
    return {"planned": len(rows), "status_counts": {s: sum(r["status"] == s for r in rows) for s in STATUSES},
            "gt_level_counts": {k: sum(v == k for v in gt.values()) for k in LEVELS}, "coverage": coverage,
            "four_class_accuracy": {"all_planned": ratio(sum(map(four, rows)), len(rows)),
                                    "scored_only": ratio(sum(map(four, scored)), len(scored))},
            "binary_accuracy": {"all_planned": ratio(sum(map(two, rows)), len(rows)),
                                "scored_only": ratio(sum(map(two, scored)), len(scored))},
            "auroc_pa3": view(pa3), "auroc_generated_binary_label": view(gen),
            "delta_auroc": num(a - b) if a is not None and b is not None else None,
            "same_eligible_ids": pa3["eligible_ids"] == gen["eligible_ids"],
            "generated_prediction_distribution": {k: ratio(predictions[k], len(rows)) for k in (*LEVELS, "UNPARSED")},
            "raw_argmax_distribution_scored": {k: sum(r["details"]["prediction"] == k for r in scored) for k in LEVELS},
            "pa3_score_by_class": {cls: analysis.quantiles([r["score"] for r in scored
                                                            if seminar.binary(gt[r["sample_id"]]) == cls])
                                   for cls in ("Normal", "Anomaly")}}


def macro(rows, metadata):
    """Strict macro over the four primary domains: undefined if any domain is."""
    domains = {}
    for d in seminar.PRIMARY:
        subset = [r for r in rows if metadata[r["sample_id"]]["domain"] == d]
        domains[d] = (exact(analysis.endpoint(subset, metadata)),
                      exact(analysis.endpoint(subset, metadata, generated_binary)))
    pa3 = None if any(a is None for a, _ in domains.values()) else sum(a for a, _ in domains.values()) / 4
    gen = None if any(b is None for _, b in domains.values()) else sum(b for _, b in domains.values()) / 4
    wins = sum(a is not None and b is not None and a > b for a, b in domains.values())
    return {"pa3": pa3, "generated": gen, "delta": pa3 - gen if pa3 is not None and gen is not None else None,
            "wins": wins, "undefined": sorted(d for d, (a, b) in domains.items() if a is None or b is None)}


def macro_view(m):
    return {"macro_pa3_auroc": num(m["pa3"]), "macro_generated_label_auroc": num(m["generated"]),
            "macro_delta": num(m["delta"]), "domains_pa3_greater": m["wins"], "undefined_domains": m["undefined"]}


def holds(m):
    if m["pa3"] is None or m["delta"] is None:
        return False
    return m["pa3"] >= MACRO_AUROC and m["delta"] >= MACRO_DELTA and m["wins"] >= DOMAIN_WINS


def baselines(rows, metadata):
    levels = [metadata[r["sample_id"]]["level"] for r in rows]
    counts, n = Counter(levels), len(levels)
    majority = max(LEVELS, key=lambda k: (counts[k], -LEVELS.index(k)))  # ties: earliest in LEVELS order
    return {"four_class_constant_accuracy": {"always_" + k: ratio(counts[k], n) for k in LEVELS},
            "four_class_majority": {"label": majority, "accuracy": ratio(counts[majority], n),
                                    "tie_rule": "highest GT count; ties broken by Level01..Level04 order"},
            "binary_constant_accuracy": {"always_Anomaly": ratio(n - counts["Level04"], n),
                                         "always_Normal": ratio(counts["Level04"], n)},
            "constant_score_auroc": view(analysis.endpoint(rows, metadata, lambda r: 0.0)),
            "tie_rule": "AUROC ties receive 0.5 credit (average ranks); a two-valued generated label therefore "
                        "has AUROC = (TPR + TNR) / 2 on scored images"}


def sensitivity(rows, metadata):
    primary = [r for r in rows if metadata[r["sample_id"]]["domain"] in seminar.PRIMARY]
    sizes = Counter(metadata[r["sample_id"]]["group"] for r in primary)
    out = []
    for component, size in sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0])):
        m = macro([r for r in primary if metadata[r["sample_id"]]["group"] != component], metadata)
        out.append({"component": component, "removed_primary_images": size, **macro_view(m),
                    "c2_c3_c4_would_hold": holds(m)})
    by_class = {cls: len({metadata[r["sample_id"]]["group"] for r in primary
                          if seminar.binary(metadata[r["sample_id"]]["level"]) == cls}) for cls in ("Normal", "Anomaly")}
    largest = max(sizes.values()) if sizes else 0
    return {"scope": "DESCRIPTIVE_SENSITIVITY_NOT_A_DECISION_INPUT",
            "grouping": "Conservative W1 components incl. UNRESOLVED near-duplicate/source-family candidate links",
            "primary_components": len(sizes), "primary_components_by_class": by_class,
            "largest_component_primary_images": largest, "primary_images": len(primary),
            "leave_one_component_out": out,
            "flips_under_leave_one_out": sum(1 for o in out if not o["c2_c3_c4_would_hold"]),
            "confidence_interval": None,
            "confidence_interval_reason": "NO_DEFENSIBLE_CI: dependency groups rest on unresolved candidate links "
                                          f"and the largest component holds {largest}/{len(primary)} primary images; "
                                          "image-level resampling would treat dependent images as independent"}


def per_image(rows, metadata, cohort):
    table = []
    for i, r in enumerate(rows):
        c, d = cohort[r["sample_id"]], r["details"] or {}
        table.append({"index": i, "sample_id": r["sample_id"], "domain": c["domain"], "primary": c["primary"],
                      "gt_level": c["level"], "gt_binary": c["binary_class"], "status": r["status"],
                      "generated_label": r["generated_label"] if r["parsed"] else None,
                      "raw_argmax_label": d.get("prediction"),
                      "z_Level01": None, "z_Level02": None, "z_Level03": None, "z_Level04": None,
                      **({f"z_{k}": v for k, v in zip(LEVELS, d["raw_label_logits"])} if d else {}),
                      "pa3_score": r["score"], "decision_step": d["decision"]["step"] if d else None,
                      "errors": "|".join(r["errors"]), "text_domain": c["text_domain"],
                      "domain_conflict": c["domain_conflict"], "conservative_component": c["conservative_component"]})
    return table


def errors(table):
    primary = [t for t in table if t["primary"]]
    scored = [t for t in primary if t["status"] == "SUCCESS"]
    pick = lambda rows: [{k: t[k] for k in ("sample_id", "domain", "gt_level", "generated_label", "pa3_score")} for t in rows[:5]]
    anomalies = sorted((t for t in scored if t["gt_binary"] == "Anomaly"), key=lambda t: (t["pa3_score"], t["sample_id"]))
    normals = sorted((t for t in scored if t["gt_binary"] == "Normal"), key=lambda t: (-t["pa3_score"], t["sample_id"]))
    alarms = [t for t in normals if t["generated_label"] != "Level04"]
    misses = [t for t in anomalies if t["generated_label"] == "Level04"]
    return {"rule": "Deterministic, primary domains, no threshold: lowest-PA3 Anomaly, highest-PA3 Normal, "
                    "generated-label errors ordered by PA3 score",
            "lowest_pa3_anomalies": pick(anomalies), "highest_pa3_normals": pick(normals),
            "generated_label_false_alarms": {"n": len(alarms), "examples": pick(alarms)},
            "generated_label_misses": {"n": len(misses), "examples": pick(misses)},
            "unscored": [{k: t[k] for k in ("sample_id", "domain", "gt_level", "status", "errors")}
                         for t in table if t["status"] != "SUCCESS"]}


def cohort_summary(cohort):
    rows = list(cohort.values())
    return {"planned": len(rows), "by_domain_class": {f"{d}/{c}": sum(r["domain"] == d and r["binary_class"] == c for r in rows)
                                                      for d, _ in seminar.STRATA for c in ("Normal", "Anomaly")},
            "gt_level_counts": {k: sum(r["level"] == k for r in rows) for k in LEVELS},
            "domain_conflicts": sorted(r["sample_id"] for r in rows if r["domain_conflict"]),
            "ls1_documentary_overlap": sum(r["exposure"]["ls1_documentary_per_sample"] for r in rows),
            "largest_conservative_component_images": max(Counter(r["conservative_component"] for r in rows).values())}


def evaluate(checked, cohort, evidence):
    """checked: native_audit result or None; cohort: post-seal GT rows or None."""
    out = {"schema": "pa3-seminar-direction-diagnostic-v1", "run_id": seminar.RUN_ID,
           "scope": "EXPLORATORY_DECISION_DIAGNOSTIC_NOT_CONFIRMATORY", "criteria_text": CRITERIA,
           "thresholds": {"coverage": num(COVERAGE), "macro_auroc": num(MACRO_AUROC),
                          "macro_delta": num(MACRO_DELTA), "domain_wins": DOMAIN_WINS},
           "evidence": evidence, "cohort": cohort_summary(cohort) if cohort else None,
           "not_permitted_claims": NOT_PERMITTED}
    if checked is None and evidence.get("audit_error"):
        # A run header exists but the CPU audit rejects the evidence: scores are untrustworthy.
        out.update(results=None, criteria={**{k: "NOT_EVALUATED" for k in CRITERIA}, "C5_TECHNICAL_INTEGRITY": "FAIL"},
                   decision={"DIRECTION_RECOMMENDATION": KEEP, "reason_category": "TECHNICAL_FAIL",
                             "failed_criteria": list(CRITERIA)})
        return out
    attempted = bool(checked) and any(r["attempted"] for r in checked["results"])
    if not attempted or not cohort:
        out.update(results=None, criteria={k: "NOT_EVALUATED" for k in CRITERIA},
                   decision={"DIRECTION_RECOMMENDATION": KEEP, "reason_category": "NOT_EXECUTED",
                             "failed_criteria": list(CRITERIA)})
        return out
    rows = checked["results"]
    metadata = {sid: {"level": r["level"], "domain": r["domain"], "group": r["conservative_component"]}
                for sid, r in cohort.items()}
    primary = [r for r in rows if cohort[r["sample_id"]]["primary"]]
    m = macro(primary, metadata)
    table = per_image(rows, metadata, cohort)
    out["results"] = {
        "overall": block(rows, metadata), "primary": block(primary, metadata),
        "metallurgy": {**block([r for r in rows if not cohort[r["sample_id"]]["primary"]], metadata),
                       "role": "DESCRIPTIVE_ONLY_NOT_A_DECISION_INPUT"},
        "by_domain": {d: block([r for r in rows if cohort[r["sample_id"]]["domain"] == d], metadata) for d, _ in seminar.STRATA},
        "macro_primary": macro_view(m),
        "confusion_generated": analysis.report(rows, metadata, completed=checked["completed"])["confusion"]["generated"],
        "baselines_primary": baselines(primary, metadata), "baselines_overall": baselines(rows, metadata),
        "sensitivity": sensitivity(rows, metadata), "representative_errors": errors(table), "per_image": table}
    cov = out["results"]["primary"]["coverage"]
    technical = (checked["completed"] and checked["sealed"] and evidence["audit_integrity"] == "PASS"
                 and evidence["preflight_verified"] == seminar.PLANNED and evidence["exposure_sealed"]
                 and all(r["status"] in {"SUCCESS", "INVALID"} for r in rows))
    criteria = {
        "C1_COVERAGE": all(c["n"] and Fraction(c["k"], c["n"]) >= COVERAGE for c in cov.values()),
        "C2_MACRO_AUROC": m["pa3"] is not None and m["pa3"] >= MACRO_AUROC,
        "C3_MACRO_DELTA": m["delta"] is not None and m["delta"] >= MACRO_DELTA,
        "C4_DOMAIN_WINS": m["wins"] >= DOMAIN_WINS,
        "C5_TECHNICAL_INTEGRITY": bool(technical)}
    failed = [k for k, v in criteria.items() if not v]
    if not checked["completed"]:
        reason = "INCOMPLETE"
    elif not criteria["C5_TECHNICAL_INTEGRITY"]:
        reason = "TECHNICAL_FAIL"
    elif not criteria["C1_COVERAGE"] or m["undefined"]:
        reason = "INSUFFICIENT_VALID_DATA"
    elif failed:
        reason = "PERFORMANCE_NOT_CONVINCING"
    else:
        reason = None
    if not checked["completed"]:
        criteria = {k: "NOT_EVALUABLE_INCOMPLETE_RUN" for k in CRITERIA}
        failed = list(CRITERIA)
    else:
        criteria = {k: "PASS" if v else "FAIL" for k, v in criteria.items()}
    out.update(criteria=criteria, decision={"DIRECTION_RECOMMENDATION": GO if reason is None else KEEP,
                                            "reason_category": reason, "failed_criteria": failed})
    return out


def _f(x, digits=3):
    return "NA" if x is None else f"{x:.{digits}f}"


def _v(d):
    return "NA" if d is None or d.get("value") is None else f"{d['value']:.3f} ({d['exact']})"


def _r(d):
    return "NA" if d["value"] is None else f"{d['k']}/{d['n']} = {d['value']:.3f}"


CONFUSION_COLUMNS = (*LEVELS, "INVALID", "TECHNICAL_ERROR", "INTERRUPTED", "UNPROCESSED", "NOT_ATTEMPTED")


def render_markdown(diag):
    # Explicit orders: identical bytes from the in-memory record and its sealed JSON.
    dec = diag["decision"]
    lines = ["# PA3 Seminar Direction Verdict", "",
             f"`DIRECTION_RECOMMENDATION = {dec['DIRECTION_RECOMMENDATION']}`", "",
             f"- Lý do: `{dec['reason_category'] or 'ALL_PREDECLARED_CRITERIA_PASS'}`",
             f"- Run ID: `{diag['run_id']}`; phạm vi: exploratory decision diagnostic, KHÔNG phải pilot, "
             "holdout hay confirmatory benchmark.", "- Tiêu chí được chốt trong code trước inference; không sửa sau khi xem kết quả.", "",
             "## Bằng chứng thực thi", "", "```json", json.dumps(diag["evidence"], indent=2, sort_keys=True), "```", ""]
    if diag["cohort"]:
        c = diag["cohort"]
        lines += ["## Cohort đã khóa", "",
                  f"- {c['planned']} ảnh TRAIN; GT levels: " + ", ".join(f"{k}={c['gt_level_counts'][k]}" for k in LEVELS),
                  "- Theo miền/lớp: " + ", ".join(f"{d}/{k}={c['by_domain_class'][d + '/' + k]}"
                                                  for d, _ in seminar.STRATA for k in ("Normal", "Anomaly")),
                  f"- Xung đột folder/text domain: {len(c['domain_conflicts'])} ({', '.join(c['domain_conflicts']) or 'none'})",
                  f"- Trùng 10 ID LS1 (tài liệu): {c['ls1_documentary_overlap']}; thành phần bảo thủ lớn nhất: "
                  f"{c['largest_conservative_component_images']} ảnh", ""]
    res = diag["results"]
    if res is None:
        why = ("CPU audit từ chối bằng chứng raw (xem audit_error); không tính chỉ số từ dữ liệu không đáng tin."
               if dec["reason_category"] == "TECHNICAL_FAIL" else
               "lượt GPU chưa được thực thi hoặc không có ảnh nào được thử.")
        lines += ["## Kết quả", "", "Không có chỉ số: " + why + " Không ngụy tạo số liệu.", ""]
    else:
        p, o = res["primary"], res["overall"]
        lines += ["## Kết quả chính (bốn miền chính, 80 ảnh)", "",
                  f"- Chạy thành công (SUCCESS): {o['status_counts']['SUCCESS']}/{o['planned']} ảnh tổng; "
                  f"{p['status_counts']['SUCCESS']}/{p['planned']} ở nhóm chính. Status tổng: "
                  + ", ".join(f"{k}={o['status_counts'][k]}" for k in STATUSES if o["status_counts"][k]),
                  f"- Coverage Normal: {_r(p['coverage']['Normal'])}; Anomaly: {_r(p['coverage']['Anomaly'])}",
                  f"- Accuracy 4 mức (mọi ảnh dự kiến / chỉ ảnh có điểm): {_r(p['four_class_accuracy']['all_planned'])} / "
                  f"{_r(p['four_class_accuracy']['scored_only'])}",
                  f"- Accuracy nhị phân từ nhãn Qwen: {_r(p['binary_accuracy']['all_planned'])} / {_r(p['binary_accuracy']['scored_only'])}",
                  f"- AUROC PA3 (pooled): {_v(p['auroc_pa3'])}; AUROC nhãn nhị phân Qwen: {_v(p['auroc_generated_binary_label'])}; "
                  f"Delta: {_v(p['delta_auroc'])}; cùng eligible IDs: {p['same_eligible_ids']}",
                  f"- Macro-domain AUROC PA3: {_v(res['macro_primary']['macro_pa3_auroc'])}; nhãn Qwen: "
                  f"{_v(res['macro_primary']['macro_generated_label_auroc'])}; Delta: {_v(res['macro_primary']['macro_delta'])}; "
                  f"PA3 > nhãn ở {res['macro_primary']['domains_pa3_greater']}/4 miền", "",
                  "## Phân bố dự đoán Qwen (nhãn sinh, mọi ảnh)", "",
                  "| Nhóm | " + " | ".join((*LEVELS, "UNPARSED")) + " |", "|---|" + "---:|" * 5]
        for name, b in (("Tổng 90", o), ("Chính 80", p), ("Metallurgy 10", res["metallurgy"])):
            lines.append(f"| {name} | " + " | ".join(_r(b["generated_prediction_distribution"][k]) for k in (*LEVELS, "UNPARSED")) + " |")
        lines += ["", "Đối chiếu P2 (bối cảnh, không cùng cohort): Qwen2.5 P2 trước đây gần như không dự đoán Level04 và tập "
                  "trung vào Level03. Tỷ lệ Level03/Level04 ở trên chỉ mô tả 90 ảnh này.", "",
                  "## Theo miền", "", "| Miền | Vai trò | SUCCESS | Cov N | Cov A | Acc4 | AccBin | AUROC PA3 | AUROC nhãn | Delta |",
                  "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for d, _ in seminar.STRATA:
            b = res["by_domain"][d]
            lines.append(f"| {d} | {'chính' if d in seminar.PRIMARY else 'mô tả phụ'} | {b['status_counts']['SUCCESS']}/{b['planned']} | "
                         f"{_f(b['coverage']['Normal']['value'])} | {_f(b['coverage']['Anomaly']['value'])} | "
                         f"{_f(b['four_class_accuracy']['all_planned']['value'])} | {_f(b['binary_accuracy']['all_planned']['value'])} | "
                         f"{_v(b['auroc_pa3'])} | {_v(b['auroc_generated_binary_label'])} | {_v(b['delta_auroc'])} |")
        mt = res["metallurgy"]
        lines += ["", f"Metallurgy (mô tả phụ, không dùng để cứu hoặc đảo quyết định): AUROC PA3 {_v(mt['auroc_pa3'])}, "
                  f"nhãn {_v(mt['auroc_generated_binary_label'])}; 5 Normal + 5 Anomaly, nhiều xung đột folder/text domain.", "",
                  "## Confusion matrix 4 mức (GT hàng × nhãn sinh/status cột, 90 ảnh)", "",
                  "| GT | " + " | ".join(CONFUSION_COLUMNS) + " |", "|---|" + "---:|" * len(CONFUSION_COLUMNS)]
        for gt in LEVELS:
            row = res["confusion_generated"][gt]
            lines.append(f"| {gt} | " + " | ".join(str(row[k]) for k in CONFUSION_COLUMNS) + " |")
        bp = res["baselines_primary"]
        lines += ["", "## Baseline lớp cố định (nhóm chính)", "",
                  "- 4 mức: " + ", ".join(f"always_{k}={_r(bp['four_class_constant_accuracy']['always_' + k])}" for k in LEVELS)
                  + f"; majority={bp['four_class_majority']['label']}",
                  f"- Nhị phân: luôn Anomaly={_r(bp['binary_constant_accuracy']['always_Anomaly'])}, "
                  f"luôn Normal={_r(bp['binary_constant_accuracy']['always_Normal'])}; AUROC điểm hằng={_v(bp['constant_score_auroc'])}",
                  f"- Ties: {bp['tie_rule']}", "", "## Ảnh sai tiêu biểu (quy tắc xác định, không threshold)", ""]
        re_ = res["representative_errors"]
        for key in ("lowest_pa3_anomalies", "highest_pa3_normals"):
            lines.append(f"- {key}: " + "; ".join(f"{e['sample_id']} ({e['gt_level']}, gen={e['generated_label']}, S={_f(e['pa3_score'])})"
                                                  for e in re_[key]))
        for key in ("generated_label_false_alarms", "generated_label_misses"):
            lines.append(f"- {key}: n={re_[key]['n']}; " + "; ".join(e["sample_id"] for e in re_[key]["examples"]))
        lines.append(f"- Không có điểm: {len(re_['unscored'])} " + "; ".join(f"{e['sample_id']}={e['status']}" for e in re_["unscored"]))
        s = res["sensitivity"]
        lines += ["", "## Độ nhạy theo nhóm phụ thuộc (mô tả, không là input quyết định)", "",
                  f"- {s['primary_components']} thành phần bảo thủ ở nhóm chính (Normal {s['primary_components_by_class']['Normal']}, "
                  f"Anomaly {s['primary_components_by_class']['Anomaly']}); lớn nhất {s['largest_component_primary_images']}/{s['primary_images']} ảnh.",
                  f"- Leave-one-component-out: {s['flips_under_leave_one_out']}/{len(s['leave_one_component_out'])} lần bỏ một thành phần làm C2–C4 không còn cùng đạt.",
                  f"- Khoảng tin cậy: không báo cáo. {s['confidence_interval_reason']}"]
    lines += ["", "## Đối chiếu tiêu chí đã chốt", "", "| Tiêu chí | Nội dung | Kết quả |", "|---|---|---|"]
    lines += [f"| {k} | {CRITERIA[k]} | {diag['criteria'][k]} |" for k in CRITERIA]
    lines += ["", "## Lý do khoa học cho Research Lead", ""]
    reason = dec["reason_category"]
    lines.append({None: "Mọi tiêu chí chốt trước đều đạt: có bằng chứng khám phá đáng để chuyển trọng tâm Seminar sang "
                        "raw-logit anomaly discrimination. Đây không phải xác nhận khoa học; cần protocol/holdout riêng.",
                  "NOT_EXECUTED": "Lượt GPU chưa chạy (hoặc dừng trước ảnh đầu tiên). Không có bằng chứng hiệu năng; giữ hướng hiện tại.",
                  "INCOMPLETE": "Lượt chạy dừng giữa chừng; bằng chứng từng phần không đủ để đánh giá tiêu chí. Không chạy lại.",
                  "TECHNICAL_FAIL": "Có lỗi kỹ thuật/kiểm toán khiến điểm PA3 không đáng tin cậy; đây là FAIL kỹ thuật, không phải kết luận hiệu năng.",
                  "INSUFFICIENT_VALID_DATA": "Không đủ ảnh có điểm hợp lệ (coverage hoặc AUROC miền không xác định); đây là thiếu dữ liệu, không phải kết luận hiệu năng.",
                  "PERFORMANCE_NOT_CONVINCING": "Lượt chạy hợp lệ nhưng hiệu năng PA3 chưa vượt các ngưỡng đã chốt; chưa đủ lý do đổi hướng Seminar."}[reason])
    lines += ["", "## Giới hạn dữ liệu/nhóm/GT", "",
              "- 90 ảnh TRAIN đã bị Qwen2.5 P2 xử lý toàn pool (exposure aggregate); thiết kế được thúc đẩy sau khi xem P2.",
              "- Quan hệ near-duplicate/source-family chưa phân xử; một thành phần bảo thủ chứa phần lớn ảnh; không có tính độc lập.",
              "- GT là nhãn thư mục gốc của benchmark; Level03 rất hiếm; Metallurgy ít Anomaly và có xung đột miền.",
              "- 10 Normal + 10 Anomaly mỗi miền: AUROC theo miền dao động lớn; không có CI đáng bảo vệ.", "",
              "## Những khẳng định chưa được phép đưa vào báo cáo Seminar", ""]
    lines += [f"- {c}" for c in diag["not_permitted_claims"]]
    return ("\n".join(lines) + "\n").encode("utf-8")


def render_csv(diag):
    stream = io.StringIO(newline="")
    fields = ["index", "sample_id", "domain", "primary", "gt_level", "gt_binary", "status", "generated_label",
              "raw_argmax_label", "z_Level01", "z_Level02", "z_Level03", "z_Level04", "pa3_score", "decision_step",
              "errors", "text_domain", "domain_conflict", "conservative_component"]
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in (diag["results"] or {}).get("per_image", []):
        writer.writerow({k: "" if row[k] is None else repr(row[k]) if type(row[k]) is float else row[k] for k in fields})
    return stream.getvalue().encode("utf-8")


def render(diag, output, seals=None):
    """Deterministic files from the diagnostic record; never overwrites."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    files = {VERDICT: render_markdown(diag), PER_IMAGE: render_csv(diag), METRICS: json_bytes(diag)}
    for name, data in files.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    receipt = {"files": {n: {"sha256": hashlib.sha256(d).hexdigest(), "size_bytes": len(d)} for n, d in files.items()},
               "sealed_journals": seals or {}, "scope": "INTEGRITY_NOT_AUTHENTICITY"}
    with (output / "checksums.json").open("xb") as stream:
        stream.write(json_bytes(receipt))
    return output


def collect(root, repo, tokenizer):
    """Re-read sealed run siblings; the same function serves Kaggle and offline CPU audit."""
    from .native_audit import audit
    root = Path(root)
    sibling = lambda suffix: root.parent / (root.name + "-" + suffix)
    journal = Journal(root)
    failure = journal.read("failure") if journal.exists("failure") else None
    evidence = {"sealed": journal.verify(), "failure": failure,
                "stage_reached": failure["stage"] if failure else "FINISHED" if journal.exists("finish") else "UNKNOWN",
                "audit_integrity": None, "audit_error": None, "preflight_verified": 0, "exposure_sealed": False,
                "telemetry": None}
    checked = None
    if journal.exists("manifest") and tokenizer is None:
        evidence["audit_error"] = "NO_T1_TOKENIZER"
    elif journal.exists("manifest"):
        try:
            checked = audit(root, repo, tokenizer)
            evidence["audit_integrity"] = checked["integrity"]
        except Exception as exc:
            evidence["audit_error"] = type(exc).__name__ + ":" + str(exc)
    if sibling("preflight").is_dir():
        check = Journal(sibling("preflight"))
        if check.verify() and check.exists("dataset"):
            evidence["preflight_verified"] = check.read("dataset")["verified"]
    if sibling("exposure").is_dir():
        exposure = Journal(sibling("exposure"))
        evidence["exposure_sealed"] = exposure.verify() and exposure.exists("observed")
    if sibling("telemetry").is_dir():
        tele = Journal(sibling("telemetry"))
        tele.verify()
        records = [tele.read(n) for n in sorted(tele.inventory()) if n.startswith("sample-")]
        evidence["telemetry"] = {"calls": len(records),
                                 "seconds_total": sum(r["seconds"] for r in records),
                                 "seconds_max": max((r["seconds"] for r in records), default=None),
                                 "cuda_max_memory_allocated_bytes": max((r["cuda_max_memory_allocated_bytes"] or 0 for r in records), default=None),
                                 "exceptions": [r["exception_type"] for r in records if r["exception_type"]]}
    return checked, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--run", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--not-executed", help="Reason code; renders the conservative verdict with no metrics")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.not_executed:
        receipt = strict_json((args.repo / "data/manifests/pa3_seminar_direction_cohort_receipt.v1.json").read_bytes())
        cohort = seminar.load_cohort(args.repo, receipt["cohort_manifest_sha256"], receipt["inference_manifest_sha256"])
        diag = evaluate(None, cohort, {"stage": args.not_executed, "gpu_runs": 0, "audit_integrity": None})
        render(diag, args.output)
        print(json.dumps(diag["decision"]))
        return 0
    from . import preflight
    t1, tokenizer = preflight.tokenizer_check(args.repo, args.snapshot)
    if t1["status"] != "PASS":
        raise ValueError("T1_REQUIRED_FOR_CPU_RECOMPUTATION")
    diag = recheck(args.run, args.repo, tokenizer, args.output)
    print(json.dumps({"recomputation": "PASS", **diag["decision"]}))
    return 0


def recheck(run, repo, tokenizer, output):
    """Offline: CPU-audit raw, recompute everything, byte-compare sealed report and verdict files."""
    run = Path(run)
    header = Journal(run).read("manifest")
    cohort = seminar.load_cohort(repo, header["cohort_manifest_sha256"], header["inference_manifest_sha256"])
    checked, evidence = collect(run, repo, tokenizer)
    diag = evaluate(checked, cohort, evidence)
    report = Journal(run.parent / (run.name + "-report"))
    if not report.verify() or json_bytes(report.read("diagnostic")) != json_bytes(diag):
        raise ValueError("DIAGNOSTIC_RECOMPUTATION_MISMATCH")
    render(diag, output)
    sealed = run.parent / (run.name + "-verdict")
    for name in (VERDICT, PER_IMAGE, METRICS):
        if (sealed / name).read_bytes() != (Path(output) / name).read_bytes():
            raise ValueError("VERDICT_RENDER_MISMATCH:" + name)
    return diag


if __name__ == "__main__":
    raise SystemExit(main())
