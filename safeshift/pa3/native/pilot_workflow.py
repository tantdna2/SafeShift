"""Prepared conditional pilot path. No grant is issued by this implementation."""
from pathlib import Path
from datetime import datetime, timezone

from safeshift.ls1.kaggle import attached_path
from safeshift.protocol.classification_policy import render_prompt
from . import access, pilot, preflight
from .journal import Journal, run_path


def execute_pilot(repo, settings, snapshot, inputs):
    journal = Journal(run_path(repo, settings["run_id"]), create=True)
    stage = "PILOT_AUTHORITY"
    try:
        access.require("pilot-train", settings, repo)
        stage = "SOURCE_RUNTIME_T1"
        source = preflight.source(repo, settings["source_commit"])
        runtime = preflight.runtime(repo, snapshot)
        t1, tokenizer = preflight.tokenizer_check(repo, snapshot)
        journal.write("t1", t1)
        journal.write("runtime", runtime)
        if t1["status"] != "PASS":
            raise ValueError("PILOT_T1_REQUIRED")
        stage = "PRIOR_TECHNICAL_CPU_AUDIT"
        pilot.verify_prior(repo, settings, inputs, tokenizer)
        stage = "APPROVED_MANIFEST"
        manifest, _ = pilot.checked(repo, settings, inputs)
        samples = pilot.samples(repo, settings, inputs)
        # Record complete dependency closure as observed BEFORE the first image
        # read; conservatively reserve all planned samples if the run then fails.
        exposure = Journal(journal.root.parent / (journal.root.name + "-exposure"), create=True)
        exposure.write("observed", {"sample_ids": manifest["observed_ids"],
            "groups": manifest["observed_groups"], "reason": "PILOT_PLANNED_EXPOSURE",
            "future_independent_evaluation": False,
            "manifest_sha256": settings["pilot_manifest_sha256"]})
        exposure.seal()
        exposure.package()
        journal.write("manifest", {"schema": "pa3-qwen-run-v1", "source": source,
            "prompt": render_prompt("qwen2_5", repo=repo), "samples": samples,
            "model": preflight.plan("qwen2_5", repo)["model_id"],
            "revision": preflight.plan("qwen2_5", repo)["model_revision"],
            "run_id": settings["run_id"], "mode": "pilot-train", "seed": pilot.SEED,
            "pilot_manifest_sha256": settings["pilot_manifest_sha256"],
            "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        stage = "PILOT_INFERENCE"
        from .qwen import QwenRawScorer
        from .workflow import infer
        scorer = QwenRawScorer(snapshot, tokenizer, t1["candidate_token_ids"], repo=repo,
                               settings={**settings, "pilot_inputs_root": str(Path(inputs).absolute())})
        journal.write("model", scorer.evidence())
        infer(journal, samples, scorer, tokenizer, lambda row: pilot.open_image(repo, settings, row, inputs))
        journal.write("finish", {"status": "FINISHED", "planned": len(samples)})
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__,
                                  "retry_permitted": False})
        raise
    finally:
        try:
            journal.seal()
        finally:
            journal.package()
    reporting = Journal(journal.root.parent / (journal.root.name + "-report"), create=True)
    try:
        from .native_audit import audit
        from .analysis import report
        checked = audit(journal.root, repo, tokenizer)
        metadata = pilot.metadata(repo, settings, inputs)
        reporting.write("audit", checked)
        reporting.write("metadata", metadata)
        reporting.write("evaluation", report(checked["results"], metadata, completed=checked["completed"]))
        reporting.write("limitations", {"scope": "EXPLORATORY_SMALL_TRAIN_PILOT_ONLY",
            "warning": "Small selected sample, score-conditional AUROC, known/unknown dependencies; not independent or confirmatory Seminar evidence.",
            "threshold_learning": False, "calibration": False})
        reporting.write("finish", {"status": "DESCRIPTIVE_PILOT_COMPLETE"})
    except BaseException as exc:
        reporting.write("failure", {"stage": "CPU_AUDIT_REPORT", "exception_type": type(exc).__name__})
        raise
    finally:
        try:
            reporting.seal()
        finally:
            reporting.package()
    return journal.root
