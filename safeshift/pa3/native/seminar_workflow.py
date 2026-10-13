"""One-pass seminar-direction diagnostic. No retry, fallback, second pass or TEST.

Order: authority -> source/runtime/T1 -> prior technical CPU audit -> 90/90
byte checksums (no decode) -> sealed exposure reservation -> one model load ->
one pass over the GT-free inference manifest -> raw seal -> GT join, CPU audit,
evaluation and verdict. A failure still seals evidence and renders a
conservative KEEP_CURRENT_DIRECTION verdict before the exception propagates.
"""

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from safeshift.protocol.classification_policy import render_prompt
from . import access, analysis, preflight, seminar, seminar_verdict
from .journal import Journal, run_path


class Telemetry:
    """Delegating scorer proxy: per-call wall time and CUDA memory, separate journal."""

    def __init__(self, scorer, journal):
        self.scorer, self.journal = scorer, journal

    def generate(self, image, journal, prefix):
        cuda = getattr(getattr(self.scorer, "torch", None), "cuda", None)
        probe = lambda name: getattr(cuda, name)() if hasattr(cuda, name) else None
        if hasattr(cuda, "reset_peak_memory_stats"):
            cuda.reset_peak_memory_stats()
        start, began, error = datetime.now(timezone.utc).isoformat(), time.perf_counter(), None
        try:
            return self.scorer.generate(image, journal, prefix)
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            self.journal.write(prefix, {"start_utc": start, "seconds": time.perf_counter() - began,
                                        "cuda_memory_allocated_bytes": probe("memory_allocated"),
                                        "cuda_max_memory_allocated_bytes": probe("max_memory_allocated"),
                                        "exception_type": error})


def _close(journal):
    if journal is not None:
        try:
            journal.seal()
        finally:
            journal.package()


def execute_diagnostic(repo, settings, snapshot, inputs):
    journal = Journal(run_path(repo, settings["run_id"]), create=True)
    sibling = lambda suffix: journal.root.parent / (journal.root.name + "-" + suffix)
    stage, tokenizer, telemetry, failure = "DIAGNOSTIC_AUTHORITY", None, None, None
    try:
        access.require(seminar.MODE, settings, repo)  # precedes source/runtime/data access
        stage = "A_SOURCE_RUNTIME_T1"
        source = preflight.source(repo, settings["source_commit"])
        runtime = preflight.runtime(repo, snapshot)
        t1, tokenizer = preflight.tokenizer_check(repo, snapshot)
        journal.write("t1", t1)
        journal.write("runtime", runtime)
        if t1["status"] != "PASS":
            raise ValueError("DIAGNOSTIC_T1_REQUIRED")
        stage = "B_PRIOR_TECHNICAL_CPU_AUDIT"
        seminar.verify_prior(repo, settings, inputs, tokenizer)
        stage = "C_MANIFEST_AND_DATASET_CHECKSUMS"
        samples = seminar.inference_samples(repo, settings)
        check = Journal(sibling("preflight"), create=True)
        try:
            check.write("dataset", seminar.preflight_dataset(repo, settings, inputs))
        finally:
            _close(check)
        stage = "D_EXPOSURE_RESERVATION"
        # All 90 enter the diagnostic exposure history BEFORE the first image decode.
        exposure = Journal(sibling("exposure"), create=True)
        try:
            exposure.write("observed", {"sample_ids": sorted(r["sample_id"] for r in samples),
                "reason": "SEMINAR_DIRECTION_DIAGNOSTIC_PLANNED_EXPOSURE", "future_independent_evaluation": False,
                "closure": "cohort manifest exposure_reservation (hash bound)",
                "cohort_manifest_sha256": settings["cohort_manifest_sha256"],
                "inference_manifest_sha256": settings["inference_manifest_sha256"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        finally:
            _close(exposure)
        journal.write("manifest", {"schema": "pa3-qwen-run-v1", "source": source,
            "prompt": render_prompt("qwen2_5", repo=repo), "samples": samples,
            "model": preflight.plan("qwen2_5", repo)["model_id"],
            "revision": preflight.plan("qwen2_5", repo)["model_revision"],
            "run_id": settings["run_id"], "mode": seminar.MODE, "seed": seminar.SEED,
            "scope": access.DIAGNOSTIC["purpose"],
            "cohort_manifest_sha256": settings["cohort_manifest_sha256"],
            "inference_manifest_sha256": settings["inference_manifest_sha256"],
            "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        stage = "E_MODEL_LOAD"
        from .qwen import QwenRawScorer
        from .workflow import infer
        scorer = QwenRawScorer(snapshot, tokenizer, t1["candidate_token_ids"], repo=repo,
                               settings={**settings, "diagnostic_inputs_root": str(Path(inputs).absolute())})
        journal.write("model", scorer.evidence())
        stage = "F_ONE_PASS_INFERENCE"
        telemetry = Journal(sibling("telemetry"), create=True)
        infer(journal, samples, Telemetry(scorer, telemetry), tokenizer,
              lambda row: seminar.open_image(repo, settings, row, inputs))
        journal.write("finish", {"status": "FINISHED", "planned": len(samples)})
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__, "retry_permitted": False})
        failure = exc
    finally:
        try:
            _close(journal)
        finally:
            _close(telemetry)
    try:
        report(repo, settings, journal.root, tokenizer)
    except BaseException:
        if failure is None:
            raise
        # The run failure stays primary; the report failure is sealed in its own journal.
    if failure is not None:
        raise failure
    return journal.root


def report(repo, settings, root, tokenizer):
    """Post-seal GT join and CPU evaluation; renders the verdict in every case."""
    reporting = Journal(root.parent / (root.name + "-report"), create=True)
    try:
        # Evidence comes only from sealed journals, exactly as the offline recheck reads it.
        checked, evidence = seminar_verdict.collect(root, repo, tokenizer)
        cohort = None
        if checked is not None:
            cohort = seminar.evaluation_metadata(repo, settings)
            metadata = {sid: {"level": r["level"], "domain": r["domain"], "group": r["conservative_component"]}
                        for sid, r in cohort.items()}
            reporting.write("audit", checked)
            reporting.write("metadata", metadata)
            # Same record native_audit --report recomputes independently.
            reporting.write("evaluation", analysis.report(checked["results"], metadata, completed=checked["completed"]))
        diagnostic = seminar_verdict.evaluate(checked, cohort, evidence)
        reporting.write("diagnostic", diagnostic)
        reporting.write("finish", {"status": "DIAGNOSTIC_REPORT_COMPLETE",
                                   "decision": diagnostic["decision"]["DIRECTION_RECOMMENDATION"]})
    except BaseException as exc:
        reporting.write("failure", {"stage": "G_CPU_EVALUATION", "exception_type": type(exc).__name__})
        raise
    finally:
        _close(reporting)
    seals = {name: hashlib.sha256(Journal(path).path("seal").read_bytes()).hexdigest()
             for name, path in (("run", root), ("report", reporting.root))}
    seminar_verdict.render(diagnostic, root.parent / (root.name + "-verdict"), seals)
    return reporting.root
