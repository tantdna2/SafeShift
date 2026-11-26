"""Read-only official observations for the deferred TRAIN3763 route.

No provider/network imports, ledger append, model execution or metric computation.
Authority is authenticated GitHub account authorship as exported by the Owner;
it cannot establish which human or application operated that account.
"""
from collections import Counter
from copy import deepcopy
import math
from pathlib import Path
import zipfile

from safeshift import internvl3763 as runtime
from safeshift.candidates.source import require
from safeshift.pilot.artifacts import safe, sha
from safeshift.pilot.contract import digest

SCHEMA = "safeshift-train3763-official-results-v1"
FINAL_KIND = "OFFLINE_CONTINUATION_RECONCILED"


def resources(archive, intent):
    """Same concrete ZIP telemetry for the online verifier and offline reader."""
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        get = lambda name: runtime._strict_json_loads(bundle.read(name)) if name in names else {}
        summary = get("run/summary.json")
        telemetry = get("run/telemetry.json")
        setup, worker = get("setup/setup-supervisor.json"), get("worker-supervisor.json")
    return {"setup_seconds": setup.get("seconds"), "worker_seconds": worker.get("seconds"),
        "load_seconds": telemetry.get("load_seconds"), "gpu_peak_allocated_bytes": telemetry.get("gpu_peak_allocated_bytes"),
        "gpu_peak_reserved_bytes": telemetry.get("gpu_peak_reserved_bytes"), "zip_bytes": Path(archive).stat().st_size,
        "reserved_gpu_seconds": intent["reserved_gpu_seconds"], "reserved_calls": intent["reserved_calls"],
        "actual_model_calls": summary.get("model_calls"), "status": summary.get("status"), "counts": summary.get("counts"),
        "missing_telemetry": "NOT_OBSERVED" if not telemetry else None, "numerical_replay": "FULL_RUNTIME_VERIFIED"}


def _reservations(route, manifest, state):
    base = route.ledger.events()[:route.registration["base_count"]]
    original = [e for e in base if e["kind"] == "INTENT"]
    deferred = [e["intent"] for e in state["events"] if e["kind"] == "RESERVED_OFFLINE"]
    require(manifest["attempts"] and manifest["attempts"][0]["intent"] == original[-1]
        and [a["intent"] for a in manifest["attempts"][1:]] == deferred, "OFFICIAL_RESERVATION_MANIFEST")
    legacy_budget = route.ledger.budget()  # original accounting, not the aggregate totals
    require(route.registration["budget"] == legacy_budget, "OFFICIAL_BASE_BUDGET_DRIFT")
    caps = legacy_budget["caps"]
    identities, jobs, capsules = set(), set(), set()
    previous_time = None
    for intent in original + deferred:
        request, plan = intent["request"], intent["request"]["plan"]
        calls, seconds = intent["reserved_calls"], plan["max_seconds"]
        require(type(calls) is int and type(seconds) is int and type(intent["reserved_gpu_seconds"]) is int
            and 0 < calls == plan["max_calls"] == request["limits"]["max_calls"] <= caps["job_calls"]
            and 120 <= seconds == request["limits"]["job_seconds"] <= caps["job_seconds"]
            and intent["reserved_gpu_seconds"] == seconds*caps["physical_gpus"], "OFFICIAL_RESERVATION_AMOUNT")
        when = intent["unix"]
        require(type(when) in (int, float) and math.isfinite(when)
            and (previous_time is None or previous_time <= when), "OFFICIAL_RESERVATION_ORDER")
        previous_time = when
        capsule = request["bindings"]["runtime"]["execution_input"]["ref"]
        require(digest(intent) not in identities and request["job"] not in jobs and capsule not in capsules,
            "OFFICIAL_DUPLICATE_RESERVATION")
        identities.add(digest(intent)); jobs.add(request["job"]); capsules.add(capsule)

    def total(intents):
        return {"jobs": len(intents), "reserved_calls": sum(i["reserved_calls"] for i in intents),
            "reserved_gpu_seconds": sum(i["reserved_gpu_seconds"] for i in intents)}
    baseline, future, combined = total(original), total(deferred), total(original + deferred)
    require(all(baseline[k] == legacy_budget[k] for k in baseline), "OFFICIAL_BASE_RESERVATIONS_MISMATCH")
    require(all(combined[k] == manifest["budget"][k] == state["budget"][k] for k in combined)
        and combined["jobs"] <= caps["total_jobs"] and combined["reserved_calls"] <= caps["total_calls"]
        and combined["reserved_gpu_seconds"] <= caps["total_gpu_seconds"], "OFFICIAL_TOTAL_BUDGET_DRIFT")
    return {**combined, "caps": deepcopy(caps), "original_caps": deepcopy(route.ledger.grant["caps"]),
        "o5_extension_sha256": digest(legacy_budget["extension"]) if legacy_budget["extension"] else None,
        "original_reservations": baseline, "deferred_reservations": future,
        "remaining_jobs": caps["total_jobs"] - combined["jobs"],
        "remaining_calls": caps["total_calls"] - combined["reserved_calls"],
        "remaining_gpu_seconds": caps["total_gpu_seconds"] - combined["reserved_gpu_seconds"],
        "accounting": "ACTUAL_RESERVATIONS_NO_REFUND_NOT_PROVIDER_BILLING", "billing_gpu_seconds": "NOT_OBSERVED"}


def official_report(route):
    """Validate the actual final certificate/custody, then expose all observations.

    Reconstructing the route refreshes registration/authority validation. There
    is no lock-file write: compare complete ledger/journal snapshots at the end.
    Missing final proof or any concurrent change fails without a partial result.
    """
    route = type(route)(route.root, route.ledger)
    before = route.ledger.events()
    n = route.registration["base_count"]
    require(len(before) == n + 2 and before[-1]["kind"] == FINAL_KIND, "OFFICIAL_FINAL_RECONCILIATION_REQUIRED")
    final = before[-1]
    require(set(final) == {"campaign_sha256", "previous", "kind", "unix", "manifest", "report", "owner", "admission",
        "github_exports", "status", "counts", "scientific_selection", "scientific_qualified"}
        and final["status"] == "FORMALLY_RECONCILED_NEW_ROUTE"
        and final["scientific_selection"] == "PENDING" and final["scientific_qualified"] is False,
        "OFFICIAL_FINAL_EVENT_FIELDS")
    state = route.state()
    manifest = route.manifest()
    require(final["manifest"] == manifest and final["counts"] == manifest["counts"], "OFFICIAL_SEALED_MANIFEST_DRIFT")
    report = route.validate_reconciliation(manifest, final["github_exports"], final["owner"], final["admission"])
    require(final["report"] == report and report["budget"] == manifest["budget"]
        and report["billing_gpu_seconds"] == "NOT_OBSERVED", "OFFICIAL_SEALED_REPORT_DRIFT")
    budget = _reservations(route, manifest, state)
    historical = {digest(h["intent"]): h for h in manifest["historical_attempts"]}
    local_times = {digest(a["intent"]): a["local_verified_unix"] for a in manifest["attempts"]}
    original_custody = {c["sha256"]: c for c in manifest["base_custody"]}
    old_proofs = {p["intent_sha256"]: p for p in report["historical"]}
    require(len(old_proofs) == len(report["historical"]), "OFFICIAL_DUPLICATE_HISTORICAL_PROOF")
    executions = []
    attempts = []
    for entry in manifest["historical_attempts"]:
        intent, outcome = entry["intent"], entry["outcome"]
        if outcome["kind"] == "ABORTED_PRE_SUBMIT":
            attempt = _attempt(intent, "ABORTED_PRE_SUBMIT", None, None, None)
            attempt["original_outcome"] = {"kind": outcome["kind"], "event_sha256": digest(outcome), "unix": outcome["unix"]}
            attempts.append(attempt)
        else:
            require(outcome["kind"] == "COLLECTED", "OFFICIAL_ORIGINAL_OUTCOME")
            custody = original_custody[outcome["sha256"]]
            proof = old_proofs[digest(intent)]
            history = runtime.sealed_history(safe(runtime.ROOT, custody["path"]), custody["sha256"], custody["plan"])
            executions.append((intent, custody["path"], custody["sha256"], history, proof))
    for entry, proof in zip(manifest["attempts"], report["attempts"]):
        executions.append((entry["intent"], entry["archive"], entry["receipt"]["sha256"], entry["receipt"]["history"], proof))
    require(len({digest(i) for i, *_ in executions}) == len(executions), "OFFICIAL_DUPLICATE_EXECUTION")
    histories, rows = [], {}
    cohort = route.registration["initial_intent"]["request"]["bindings"]["runtime"]["execution_request"]["cohort"]
    samples = cohort["samples"]
    for intent, path, checksum, history, proof in executions:
        request, plan = intent["request"], intent["request"]["plan"]
        require(history["parent_history_sha256"] == digest(histories) and history["evidence_sha256"] == checksum
            and history["series_id"] == plan["series_id"] == runtime.SERIES
            and history["identity"] == plan["identity"] and history["cohort_sha256"] == route.ledger.grant["cohort_sha256"]
            and history["run_id"] == plan["run_id"] and history["attempt_id"] == plan["attempt_id"], "OFFICIAL_ATTEMPT_LINEAGE")
        observed = resources(safe(runtime.ROOT, path), intent)
        require(proof["resources"] == observed, "OFFICIAL_RESOURCE_PROOF_DRIFT")
        histories.append(deepcopy(history))
        attempt = _attempt(intent, observed["status"], checksum, proof["provider"], observed)
        attempt["archive"] = path
        old = historical.get(digest(intent))
        attempt["original_outcome"] = {"kind": old["outcome"]["kind"], "event_sha256": digest(old["outcome"]),
            "unix": old["outcome"]["unix"]} if old else None
        attempt["local_verified_unix"] = local_times.get(digest(intent))
        attempt["failure_evidence_member"] = "terminal.json" if observed["status"] == "FAIL" else None
        attempts.append(attempt)
        for record in history["records"]:
            ordinal = record["ordinal"]
            require(type(ordinal) is int and 0 <= ordinal < 3763 and ordinal not in rows
                and record["sample_id"] == samples[ordinal]["sample_id"] and record["image_sha256"] == samples[ordinal]["image_sha256"]
                and record["status"] in ("SUCCESS", "INVALID") and type(record["native_calls"]) is int
                and record["native_calls"] == record["attempts"] == 1
                and ((record["status"] == "INVALID" and record["label"] is None) or
                    (record["status"] == "SUCCESS" and record["label"] in ("Level01", "Level02", "Level03", "Level04"))),
                "OFFICIAL_ORDINAL_COVERAGE_OR_STATUS")
            rows[ordinal] = {"record": deepcopy(record), "ordinal": ordinal, "series_id": history["series_id"],
                "cohort_sha256": history["cohort_sha256"], "lineage": [{
                    "run_id": history["run_id"], "attempt_id": history["attempt_id"], "action": history["action"],
                    "intent_sha256": digest(intent), "record_sha256": digest(record), "archive_sha256": checksum,
                    "source_sha256": digest(plan["runtime_source"]), "source_commit": request["commit_sha"],
                    "notebook_sha256": request["notebook_sha256"], "checkpoint": deepcopy(request["bindings"]["checkpoint"]),
                    "provider": deepcopy(proof["provider"]), "capsule": deepcopy(proof["capsule"])}]}
    require(sorted(rows) == list(range(3763)) and histories == state["history"], "OFFICIAL_FULL_TRAIN_HISTORY_REQUIRED")
    counts = dict(Counter(r["record"]["status"] for r in rows.values()))
    require(counts == final["counts"], "OFFICIAL_COUNTS_DRIFT")
    attempts.sort(key=lambda a: a["reserved_unix"])
    require(len(attempts) == budget["jobs"], "OFFICIAL_ATTEMPT_INVENTORY")
    observed = _observed(attempts)
    require(route.ledger.events() == before and route.events() == state["events"]
        and route.manifest() == manifest, "OFFICIAL_CUSTODY_CHANGED_DURING_READ")
    return {"schema": SCHEMA, "status": "OFFICIAL_RECONCILED_RESULTS", "scope": "PRIVATE_TRAIN_METADATA", "planned": 3763,
        "series_id": runtime.SERIES, "cohort_sha256": route.ledger.grant["cohort_sha256"],
        "science_sha256": route.ledger.grant["science_sha256"], "counts": counts, "records": [rows[i] for i in range(3763)],
        "histories": histories, "attempts": attempts, "budget": budget, "observed_resources": observed,
        "certificate": {"event_sha256": digest(final), "journal_number": len(before), "manifest_sha256": digest(manifest),
            "report_sha256": digest(report), "owner": final["owner"], "admission": final["admission"]},
        "authority_boundary": "AUTHENTICATED_GITHUB_ACCOUNT_EXPORT_NOT_HUMAN_CLICK_PROOF",
        "legacy": {"status": "HISTORICAL_ONLY_INTENT35_REMAINS_OPEN", "new_route_results_included": False},
        "analysis_handoff": "OFFICIAL_OBSERVATIONS_SEPARATE_ANALYSIS_PROTOCOL_AUTHORIZATION_REQUIRED",
        "scientific_selection": "PENDING", "scientific_qualified": False}


def _attempt(intent, status, checksum, provider, observed):
    request = intent["request"]
    return {"run_id": request["plan"]["run_id"], "attempt_id": request["plan"]["attempt_id"],
        "request_sha256": digest(request), "scheduled_ordinals": list(request["plan"]["scheduled_ordinals"]),
        "reserved_job_seconds": request["plan"]["max_seconds"], "series_id": request["plan"]["series_id"],
        "cohort_sha256": request["plan"]["cohort_sha256"],
        "intent_sha256": digest(intent), "reserved_unix": intent["unix"], "scheduled_job": request["job"],
        "status": status, "archive_sha256": checksum, "provider": deepcopy(provider), "resources": deepcopy(observed),
        "reserved_calls": intent["reserved_calls"], "reserved_gpu_seconds": intent["reserved_gpu_seconds"],
        "source_sha256": digest(request["plan"]["runtime_source"]), "source_commit": request["commit_sha"],
        "notebook_sha256": request["notebook_sha256"], "checkpoint": deepcopy(request["bindings"]["checkpoint"])}


def _observed(attempts):
    measured = [a["resources"] for a in attempts if a["resources"] is not None]
    result = {"billing_gpu_seconds": "NOT_OBSERVED", "executed_attempts": len(measured),
        "aborted_before_submit": len(attempts)-len(measured)}
    for field in ("setup_seconds", "worker_seconds", "load_seconds", "actual_model_calls"):
        values = [r[field] for r in measured if r[field] is not None]
        require(all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values), "OFFICIAL_NONFINITE_RESOURCE")
        result[field] = {"observed_sum": sum(values) if values else None, "observed_attempts": len(values),
            "missing_attempts": len(measured)-len(values), "coverage": "COMPLETE" if len(values) == len(measured) else "PARTIAL_NOT_ZERO_FILLED"}
    return result
