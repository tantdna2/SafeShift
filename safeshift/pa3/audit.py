"""Read-only CPU recomputation of intact synthetic journals, including partial runs."""

from . import artifacts
from .evaluate import report
from .policy import authorize, identity
from .runner import source_provenance
from .scoring import check_raw, pending, score_raw
from .synthetic import ground_truth, specimen


def audit_run(repo, settings):
    settings = authorize(settings)  # no arbitrary archive, dataset or run path
    sealed = artifacts.verify(repo, settings)
    manifest = artifacts.read(repo, settings, "manifest")
    if (manifest["identity"] != identity(settings)
            or manifest["cohort"] != [specimen(settings, n) for n in settings["cases"]]):
        raise PermissionError("SYNTHETIC_MANIFEST_IDENTITY_MISMATCH")
    try:
        current_sources = source_provenance()
    except OSError as exc:
        raise ValueError("PA3_SOURCE_PROVENANCE_UNREADABLE: required source file unavailable") from exc
    # Compare exact file membership, hashes, sizes and JSON types. The caller's
    # source_commit remains provenance only; it is not checked against Git HEAD.
    if artifacts.json_bytes(manifest.get("source_files")) != artifacts.json_bytes(current_sources):
        raise ValueError("PA3_SOURCE_PROVENANCE_MISMATCH: source file set, SHA-256 or size differs")
    rows, stopped = [], False
    for i, name in enumerate(settings["cases"]):
        attempted, persisted, calculated = [artifacts.exists(repo, settings, f"{i:03d}.{kind}")
                                            for kind in ("attempt", "raw", "result")]
        if (persisted and not attempted) or (calculated and not persisted) or (stopped and attempted):
            raise ValueError("ATTEMPT_SEQUENCE_MISMATCH")
        if attempted and artifacts.read(repo, settings, f"{i:03d}.attempt") != specimen(settings, name):
            raise ValueError("ATTEMPT_SAMPLE_MISMATCH")
        row = pending(settings, name, attempted=attempted, persisted=persisted)
        if persisted:
            raw = artifacts.read(repo, settings, f"{i:03d}.raw")
            check_raw(settings, name, raw)
        if calculated:
            row = score_raw(settings, name, raw)
            saved = artifacts.read(repo, settings, f"{i:03d}.result")
            if artifacts.json_bytes(row) != artifacts.json_bytes(saved):
                raise ValueError("PA3_RECOMPUTATION_MISMATCH")
        stopped = not calculated or row["status"] in ("TECHNICAL_ERROR", "INTERRUPTED")
        rows.append(row)
    finish = artifacts.exists(repo, settings, "finish")
    failure = artifacts.exists(repo, settings, "failure")
    if finish and (failure or stopped):
        raise ValueError("FINISHED_JOURNAL_MISMATCH")
    if finish and artifacts.read(repo, settings, "finish") != {"status": "FINISHED", "planned": len(rows)}:
        raise ValueError("FINISH_RECORD_MISMATCH")
    if sealed and not (finish or failure):
        raise ValueError("SEALED_RUN_MISSING_TERMINAL_RECORD")
    if failure:
        failed = artifacts.read(repo, settings, "failure")
        attempted_indices = [i for i, row in enumerate(rows) if row["attempted"]]
        if (failed.get("status") != "STOPPED" or failed.get("retry_permitted") is not False
                or failed.get("at_index") != (attempted_indices[-1] if attempted_indices else None)):
            raise ValueError("FAILURE_RECORD_MISMATCH")
    return {"integrity": "PASS", "sealed": sealed, "results": rows,
            "evaluation": report(settings, rows, ground_truth(settings), completed=sealed and finish),
            "limitations": "Checksums and deterministic recomputation do not prove external authenticity, runtime qualification or model performance."}
