"""One fixed TRAIN shard, no retry. Sealed raw evidence precedes every GT join."""
from datetime import datetime, timezone
from pathlib import Path

from safeshift.protocol.classification_policy import render_prompt
from . import access, preflight, train, train_report
from .journal import Journal, run_path
from .seminar_workflow import Telemetry, _close


def execute_train(repo, settings, snapshot, inputs):
    journal = Journal(run_path(repo, settings["run_id"]), create=True)
    sibling = lambda suffix: journal.root.parent / (journal.root.name + "-" + suffix)
    stage, tokenizer, telemetry, failure = "TRAIN_AUTHORITY", None, None, None
    try:
        access.require(train.MODE, settings, repo)
        stage = "A_SOURCE_AND_MANIFEST"
        source = preflight.source(repo, settings["source_commit"])
        samples = train.inference_samples(repo, settings)
        journal.write("manifest", {"schema": "pa3-qwen-run-v1", "source": source,
            "prompt": render_prompt("qwen2_5", repo=repo), "samples": samples,
            "model": train.SCOPE["model"], "revision": train.SCOPE["revision"],
            "run_id": settings["run_id"], "mode": train.MODE, "seed": train.SEED, "shard_id": settings["shard_id"],
            "full_manifest_sha256": settings["full_manifest_sha256"],
            "inference_manifest_sha256": settings["inference_manifest_sha256"],
            "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        stage = "B_RUNTIME_T1_TECHNICAL_AUDIT"
        journal.write("runtime", preflight.runtime(repo, snapshot))
        t1, tokenizer = preflight.tokenizer_check(repo, snapshot)
        journal.write("t1", t1)
        if t1["status"] != "PASS":
            raise ValueError("TRAIN_T1_REQUIRED")
        train.verify_prior(repo, settings, inputs, tokenizer)
        stage = "C_TRAIN_CHECKSUMS"
        check = Journal(sibling("preflight"), create=True)
        try:
            check.write("dataset", train.preflight_dataset(repo, settings, inputs))
        finally:
            _close(check)
        stage = "D_EXPOSURE_RESERVATION"
        exposure = Journal(sibling("exposure"), create=True)
        try:
            exposure.write("observed", {"sample_ids": sorted(r["sample_id"] for r in samples),
                "run_id": settings["run_id"], "shard_id": settings["shard_id"], "max_runs": 1,
                "max_images": len(samples), "retry_permitted": False, "future_independent_evaluation": False,
                "full_manifest_sha256": settings["full_manifest_sha256"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        finally:
            _close(exposure)
        stage = "E_ONE_MODEL_LOAD"
        from .qwen import QwenRawScorer
        from .workflow import infer
        scorer = QwenRawScorer(snapshot, tokenizer, t1["candidate_token_ids"], repo=repo,
                               settings={**settings, "train_inputs_root": str(Path(inputs).absolute())})
        journal.write("model", scorer.evidence())
        from .state_guard import StateGuard
        stage = "E_MODEL_STATE_BASELINE"
        guard = StateGuard(scorer, journal)
        stage = "F_ONE_PASS"
        telemetry = Journal(sibling("telemetry"), create=True)
        infer(journal, samples, Telemetry(scorer, telemetry), tokenizer,
              lambda row: train.open_image(repo, settings, row, inputs), state_guard=guard)
        if any(journal.read(f"sample-{i:06d}.result")["status"] == "TECHNICAL_ERROR"
               for i in range(len(samples))):
            # Exhausting the manifest is not a successful/complete baseline.
            raise ValueError("TRAIN_EXHAUSTED_WITH_TECHNICAL_ERRORS")
        journal.write("finish", {"status": "FINISHED", "planned": len(samples)})
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__,
                                  "reason": str(exc), "retry_permitted": False})
        failure = exc
    finally:
        try:
            _close(journal)
        finally:
            _close(telemetry)
    reporting = Journal(sibling("report"), create=True)
    try:
        if journal.exists("manifest"):
            header, checked, metadata = train_report.checked_run(journal.root, repo, tokenizer)
            reporting.write("audit", checked)
            reporting.write("metadata", metadata)
            evaluated = train_report.metrics(checked["results"], metadata, checked["completed"])
            reporting.write("evaluation", evaluated)
            train_report.export(sibling("exports"), checked["results"], metadata, evaluated,
                                {"run_id": header["run_id"], "shard_id": header["shard_id"], "audit": checked})
        else:
            reporting.write("failure", {"stage": "AUTHORITY_OR_SOURCE_BLOCKED", "metrics": None})
    except BaseException as exc:
        reporting.write("failure", {"stage": "G_CPU_REPORT", "exception_type": type(exc).__name__})
        if failure is None:
            failure = exc
    finally:
        _close(reporting)
    if failure is not None:
        raise failure
    return journal.root
