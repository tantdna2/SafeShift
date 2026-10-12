"""One-shot A-G workflow. Real execution remains locked in access.py."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from safeshift.protocol.classification_policy import render_prompt
from safeshift.protocol.schema import strict_json
from . import access, cohort, preflight
from .journal import Journal, run_path
from .native_score import score


def infer(journal, samples, scorer, tokenizer, open_image):
    """Internal orchestration; tests supply API-compatible CPU model doubles."""
    for i, sample in enumerate(samples):
        prefix = f"sample-{i:06d}"
        journal.write(prefix + ".attempt", sample)
        try:
            with open_image(sample) as image:
                scorer.generate(image, journal, prefix)
            # Never parse a return value; only verified, durably reread bytes.
            raw = journal.read(prefix + ".raw")
            result = score(sample["sample_id"], raw, tokenizer)
            journal.write(prefix + ".result", result)
        except BaseException as exc:
            journal.write(prefix + ".error", {"exception_type": type(exc).__name__,
                          "status": "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "TECHNICAL_ERROR"})
            raise
        if result["status"] == "TECHNICAL_ERROR":
            raise ValueError("RAW_SCORING_TECHNICAL_FAILURE")


def execute(repo, settings, snapshot, inputs=None):
    """No run ID reuse, retries, fallback or implicit grant from prep receipts."""
    journal = Journal(run_path(repo, settings["run_id"]), create=True)
    stage, terminal = "AUTHORITY", False
    images = []
    try:
        access.require(settings["mode"], settings)  # precedes source/runtime/data access
        access.require("technical", settings)
        stage = "A_SOURCE"
        source = preflight.source(repo, settings["source_commit"])
        journal.write("source", source)
        stage = "B_RUNTIME_SNAPSHOT"
        runtime = preflight.runtime(repo, snapshot)
        journal.write("runtime", runtime)
        stage = "C_T1"
        t1, tokenizer = preflight.tokenizer_check(repo, snapshot)
        journal.write("t1", t1)
        if t1["status"] != "PASS":
            raise ValueError("T1_" + t1["status"])
        stage = "D_QUALIFICATION"
        from safeshift.ls1.experiment import synthetic_samples
        from .qwen import QwenRawScorer
        from .native_audit import audit
        # Always qualify in this exact lifecycle before any TRAIN data access.
        images = synthetic_samples()
        samples = [{k: v for k, v in r.items() if k != "image"} for r in images]
        qualification = Journal(journal.root.parent / (journal.root.name + "-qualification"), create=True)
        try:
            qualification.write("manifest", {"schema": "pa3-qwen-run-v1", "source": source,
                "prompt": render_prompt("qwen2_5", repo=repo), "samples": samples,
                "model": preflight.plan("qwen2_5", repo)["model_id"],
                "revision": preflight.plan("qwen2_5", repo)["model_revision"],
                "run_id": settings["run_id"] + "-qualification", "mode": "technical",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(), "seed": None})
            qualification.write("t1", t1)
            qualification.write("runtime", runtime)
            scorer = QwenRawScorer(snapshot, tokenizer, t1["candidate_token_ids"], repo=repo,
                                   settings={**settings, "mode": "technical"})
            qualification.write("model", scorer.evidence())
            by_id = {r["sample_id"]: r["image"] for r in images}
            infer(qualification, samples, scorer, tokenizer, lambda r: by_id[r["sample_id"]].copy())
            qualification.write("finish", {"status": "FINISHED", "planned": len(samples)})
        except BaseException as exc:
            qualification.write("failure", {"stage": stage, "exception_type": type(exc).__name__, "retry_permitted": False})
            raise
        finally:
            try:
                qualification.seal()
            finally:
                qualification.package()
        qualified = audit(qualification.root, repo, tokenizer)
        if not qualified["completed"] or not any(r["status"] == "SUCCESS" for r in qualified["results"]):
            raise ValueError("QUALIFICATION_REQUIRES_AT_LEAST_ONE_AUDITED_SCORE")
        journal.write("qualification", qualified)
        if settings["mode"] == "technical":
            journal.write("finish", {"status": "TECHNICAL_QUALIFICATION_COMPLETE_NO_DATA_RIGHTS"})
            terminal = True
        else:
            stage = "E_COHORT"
            access.require(settings["mode"], settings)
            samples = cohort.load_plan(repo, settings, inputs)
            journal.write("model", scorer.evidence())
            journal.write("manifest", {"schema": "pa3-qwen-run-v1", "source": source,
                "prompt": render_prompt("qwen2_5", repo=repo), "samples": samples,
                "model": preflight.plan("qwen2_5", repo)["model_id"],
                "revision": preflight.plan("qwen2_5", repo)["model_revision"],
                "run_id": settings["run_id"], "mode": settings["mode"], "seed": None,
                "cohort_plan_sha256": settings["cohort_plan_sha256"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat()})
            stage = "F_TRAIN"
            # Same frozen scorer, fresh native cache per sample; grant checked again.
            scorer.settings = dict(settings)
            infer(journal, samples, scorer, tokenizer, lambda r: cohort.open_image(repo, settings, r, inputs))
            journal.write("finish", {"status": "FINISHED", "planned": len(samples)})
            terminal = True
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__,
                                   "retry_permitted": False, "real_runtime_pass_claim": False})
        raise
    finally:
        for row in images:
            row["image"].close()
        try:
            journal.seal()
        finally:
            journal.package()
    # Raw seal precedes GT join. Audit/report are separate immutable artifacts.
    if terminal and settings["mode"] != "technical":
        stage = "G_CPU_AUDIT_EVALUATION"
        reporting = Journal(journal.root.parent / (journal.root.name + "-report"), create=True)
        try:
            checked = audit(journal.root, repo, tokenizer)
            reporting.write("audit", checked)
            metadata = cohort.evaluation_metadata(repo, settings, [r["sample_id"] for r in checked["results"]], inputs)
            reporting.write("metadata", metadata)
            from .analysis import report
            reporting.write("evaluation", report(checked["results"], metadata, completed=checked["completed"]))
            reporting.write("finish", {"status": "DESCRIPTIVE_REPORT_COMPLETE_NO_CONFIRMATORY_CLAIM"})
        except BaseException as exc:
            reporting.write("failure", {"stage": stage, "exception_type": type(exc).__name__})
            raise
        finally:
            try:
                reporting.seal()
            finally:
                reporting.package()
    return journal.root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--inputs", type=Path)
    args = parser.parse_args()
    settings = strict_json(args.settings.read_bytes())
    from safeshift.runners.internvl3_snapshot import network_denied
    with network_denied():
        execute(Path(__file__).resolve().parents[3], settings, args.snapshot, args.inputs)


if __name__ == "__main__":
    main()
