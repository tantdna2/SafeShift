"""CPU-only sealed shard merge and recomputation. Never averages shard AUROCs."""
import argparse
import csv
import io
from pathlib import Path

from safeshift.ls1.artifacts import write_json, write_new, seal, json_bytes, verify_run
from safeshift.protocol.d9r24_metrics import classification_metrics
from safeshift.protocol.metrics import ClassificationInput
from safeshift.protocol.schema import Classification, ParseResult
from . import analysis, native_audit, preflight, train
from .journal import Journal
from .native_score import pending, STATUSES


def metrics(rows, metadata, completed):
    analysis.validate(rows, metadata, completed)

    def one(selected):
        summary = analysis.summary(selected, metadata)
        hard = analysis.endpoint(selected, metadata, lambda r: float(r["generated_label"] != "Level04"))
        pa3 = summary["auroc"]
        # Existing four-class metric definitions, on the SAME score-valid IDs.
        valid = [r for r in selected if r["status"] == "SUCCESS"]
        def cls(r):
            m = metadata[r["sample_id"]]
            parsed = (ParseResult("SUCCESS", Classification(r["generated_label"]))
                      if r["status"] == "SUCCESS" else ParseResult("INVALID"))
            return ClassificationInput(r["sample_id"], m["level"], m["domain"], m["group"], parsed, frozenset())
        generated = classification_metrics([cls(r) for r in valid])
        failure_aware = classification_metrics([cls(r) for r in selected])
        binary = {t: {p: 0 for p in ("Anomaly", "Normal")} for t in ("Anomaly", "Normal")}
        for r in valid:
            binary[train.seminar.binary(metadata[r["sample_id"]]["level"])][train.seminar.binary(r["generated_label"])] += 1
        an, nn = sum(binary["Anomaly"].values()), sum(binary["Normal"].values())
        binary_metrics = {"confusion_matrix": binary, "eligible_n": len(valid),
            "accuracy": (binary["Anomaly"]["Anomaly"] + binary["Normal"]["Normal"])/len(valid) if valid else None,
            "balanced_accuracy": (binary["Anomaly"]["Anomaly"]/an + binary["Normal"]["Normal"]/nn)/2 if an and nn else None}
        return {"coverage": summary, "auroc_pa3": pa3, "auroc_generated_binary": hard,
                "delta_auroc_same_ids": pa3["value"] - hard["value"] if pa3["value"] is not None else None,
                "generated_on_score_valid_ids": generated, "generated_binary_on_score_valid_ids": binary_metrics,
                "generated_failure_aware": failure_aware}

    return {"schema": "pa3-full-train-metrics-v1", "completed": completed,
            "scope": "DESCRIPTIVE_FULL_TRAIN" if completed else "PARTIAL_TRAIN_DESCRIPTIVE",
            "direction": "HIGHER_IS_ANOMALY", "pa3_threshold": None,
            "classification_method": "GENERATED_FOUR_LEVEL_LABELS_ONLY",
            "overall": one(rows), "by_domain": {d: one([r for r in rows if metadata[r["sample_id"]]["domain"] == d])
                for d in sorted({m["domain"] for m in metadata.values()})},
            "limitations": ["Prior exposure, dependencies and domain/platform confounding; not independent evaluation.",
                            "AUROC and delta use identical SUCCESS IDs; invalid/failed/missing images are never imputed.",
                            "Accuracy and Balanced Accuracy are four-class generated-label metrics; Recall Level01 is exact Level01.",
                            "FPR is generated Anomaly among original Normal; undefined denominators remain null.",
                            "No threshold, CI, calibration, confirmation or improvement claim."]}


def checked_run(root, repo, tokenizer, full_hash=None):
    journal = Journal(root)
    if not journal.verify():
        raise ValueError("SEALED_TRAIN_RUN_REQUIRED")
    header = journal.read("manifest")
    shard = header.get("shard_id")
    if (header.get("mode") != train.MODE or header.get("run_id") != train.run_id(shard)
            or header.get("full_manifest_sha256") != (full_hash or header.get("full_manifest_sha256"))):
        raise ValueError("EXACT_TRAIN_RUN_BINDING")
    payload = (Path(repo) / train.inference_path(shard)).read_bytes()
    import hashlib
    if hashlib.sha256(payload).hexdigest() != header["inference_manifest_sha256"]:
        raise ValueError("TRAIN_HEADER_INFERENCE_CHECKSUM")
    from safeshift.protocol.schema import strict_json
    expected = train.validate_inference(strict_json(payload), shard)
    if header["samples"] != expected:
        raise ValueError("TRAIN_HEADER_MEMBERSHIP_MISMATCH")
    # Also validate the complete four-way universe before evaluating one shard.
    metadata = train.load_full(repo, header["full_manifest_sha256"])
    if journal.exists("model"):
        checked = native_audit.audit(root, repo, tokenizer)
    else:
        # Load/T1/preflight errors still leave one NOT_ATTEMPTED row per planned ID.
        if (not journal.exists("failure") or journal.exists("finish")
                or any(n.startswith("sample-") for n in journal.inventory())
                or journal.read("failure").get("retry_permitted") is not False
                or preflight.source(repo, header["source"]["source_commit"]) != header["source"]):
            raise ValueError("PRE_MODEL_FAILURE_PROOF_REQUIRED")
        checked = {"integrity": "PRE_MODEL_FAILURE_NO_SAMPLE_CALLS", "sealed": True, "completed": False,
                   "results": [pending(r["sample_id"]) for r in expected]}
    return header, checked, {r["sample_id"]: metadata[r["sample_id"]] for r in expected}


def csv_bytes(fields, rows):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def export(output, rows, metadata, evaluation, evidence):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "metrics.json", evaluation)
    write_json(output / "audit.json", evidence)
    # Recomputable endpoint inputs plus decision-step raw label logits.
    fields = ["sample_id", "domain", "true_level", "status", "attempted", "persisted", "parsed",
              "generated_label", "true_binary_label", "generated_binary_label", "pa3_score", "z1", "z2", "z3", "z4", "errors"]
    samples = []
    for row in rows:
        raw = row["details"]["raw_label_logits"] if row["details"] else [None] * 4
        samples.append({"sample_id": row["sample_id"], "domain": metadata[row["sample_id"]]["domain"],
            "true_level": metadata[row["sample_id"]]["level"],
            **{k: row[k] for k in ("status", "attempted", "persisted", "parsed", "generated_label")},
            "true_binary_label": train.seminar.binary(metadata[row["sample_id"]]["level"]),
            "generated_binary_label": train.seminar.binary(row["generated_label"]) if row["generated_label"] else None,
            "pa3_score": row["score"], **dict(zip(("z1", "z2", "z3", "z4"), raw)), "errors": "|".join(row["errors"])})
    write_new(output / "samples.csv", csv_bytes(fields, samples))
    totals, confusion = [], []
    for scope, result in [("ALL", evaluation["overall"]), *evaluation["by_domain"].items()]:
        g, cov = result["generated_on_score_valid_ids"], result["coverage"]
        totals.append({"domain": scope, "planned": cov["planned"], "scored": cov["scored"], "coverage": cov["coverage"],
            "auroc_pa3": result["auroc_pa3"]["value"], "auroc_generated_binary": result["auroc_generated_binary"]["value"],
            "delta_auroc_same_ids": result["delta_auroc_same_ids"],
            "accuracy_generated_4class": g["raw_accuracy_descriptive"]["value"], "balanced_accuracy_generated_4class": g["balanced_accuracy"],
            "accuracy_generated_binary": result["generated_binary_on_score_valid_ids"]["accuracy"],
            "balanced_accuracy_generated_binary": result["generated_binary_on_score_valid_ids"]["balanced_accuracy"],
            "recall_Level01_exact": g["level01_recall_parse_conditional"]["value"],
            "fpr_generated_anomaly": g["anomaly_fpr_parse_conditional"]["value"],
            "eligible_anomaly": result["auroc_pa3"]["positive_n"], "eligible_normal": result["auroc_pa3"]["negative_n"],
            "auroc_reason": result["auroc_pa3"]["reason"],
            **{s: cov["status_counts"][s] for s in STATUSES}})
        for truth, predictions in result["generated_failure_aware"]["confusion_matrix"].items():
            for pred, n in predictions.items():
                confusion.append({"domain": scope, "method": "GENERATED_4CLASS_FAILURE_AWARE", "true_label": truth, "generated_label": pred, "count": n})
        for truth, predictions in result["generated_binary_on_score_valid_ids"]["confusion_matrix"].items():
            for pred, n in predictions.items():
                confusion.append({"domain": scope, "method": "GENERATED_BINARY_SCORE_VALID", "true_label": truth, "generated_label": pred, "count": n})
    write_new(output / "metrics.csv", csv_bytes(list(totals[0]), totals))
    write_new(output / "confusion.csv", csv_bytes(list(confusion[0]), confusion))
    seal(output)


def merge(repo, roots, tokenizer, output):
    if len(roots) != 4:
        raise ValueError("EXACT_FOUR_SHARD_PACKAGES_REQUIRED")
    rows, seen, evidence = [], set(), []
    full_hash = None
    for root in roots:
        root = Path(root)
        header, checked, shard_metadata = checked_run(root, repo, tokenizer, full_hash)
        if header["shard_id"] in seen:
            raise ValueError("DUPLICATE_TRAIN_SHARD")
        seen.add(header["shard_id"])
        full_hash = header["full_manifest_sha256"]
        rows.extend(checked["results"])
        # Optional saved reports/exports are compared, never used as score inputs.
        expected = metrics(checked["results"], shard_metadata, checked["completed"])
        reporting = Journal(root.parent / (root.name + "-report"))
        if reporting.root.exists():
            if not reporting.verify():
                raise ValueError("UNSEALED_TRAIN_REPORT")
            if reporting.exists("evaluation") and (reporting.read("metadata") != shard_metadata
                    or json_bytes(reporting.read("evaluation")) != json_bytes(expected)):
                raise ValueError("TRAIN_EVALUATION_RECOMPUTATION_MISMATCH")
        exported = root.parent / (root.name + "-exports")
        if exported.exists():
            verify_run(exported)
            from safeshift.protocol.schema import strict_json
            if json_bytes(strict_json((exported / "metrics.json").read_bytes())) != json_bytes(expected):
                raise ValueError("TRAIN_EXPORT_RECOMPUTATION_MISMATCH")
        evidence.append({"run_id": header["run_id"], "shard_id": header["shard_id"],
                         "seal": Journal(root).read("seal"), "audit": checked})
    metadata = train.load_full(repo, full_hash)
    if seen != {0, 1, 2, 3} or {r["sample_id"] for r in rows} != set(metadata) or len(rows) != train.COUNT:
        raise ValueError("DISJOINT_COMPLETE_TRAIN_RESULT_UNIVERSE_REQUIRED")
    rows.sort(key=lambda r: r["sample_id"])
    evaluated = metrics(rows, metadata, all(e["audit"]["completed"] for e in evidence))
    export(output, rows, metadata, evaluated, {"full_manifest_sha256": full_hash, "shards": evidence,
           "result_universe": train.COUNT, "method": "RAW_RECOMPUTED_THEN_POOLED_NOT_SHARD_AUC_AVERAGE"})
    return evaluated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--snapshot", type=Path, required=True, help="Pinned tokenizer files; no weights/GPU")
    parser.add_argument("--runs", type=Path, nargs=4, required=True, help="Unpacked raw journals for all four shards")
    parser.add_argument("--output", type=Path, default=Path("data/processed/pa3_full_train_report"))
    args = parser.parse_args()
    t1, tokenizer = preflight.tokenizer_check(args.repo, args.snapshot)
    if t1["status"] != "PASS":
        raise ValueError("CPU_TOKENIZER_T1_REQUIRED")
    report = merge(args.repo, args.runs, tokenizer, args.output)
    print(json_bytes({"completed": report["completed"], "overall": report["overall"]}).decode())


if __name__ == "__main__":
    main()
