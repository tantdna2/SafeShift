"""Existing engine/journal operations adapted ONLY for model-specific parsing.

Peer modules stay byte-identical. Qwen preserves its V4 P2.1 parser; no new
label repair rule is introduced. Pure parser injection replaces module globals.
"""
from pathlib import Path
import shutil
import time
from safeshift.pilot.artifacts import read, safe, sha, write
from safeshift.pilot.contract import MODELS, digest, settings, parse_label
from safeshift.pilot.hnlo import replay
from safeshift.pilot.runner import error_record
from safeshift.candidates.source import require
from safeshift.candidates.train_history import members
from safeshift.candidates import fulltrain as f
from safeshift.candidates.fulltrain_run import _identity


def execute(store, rows, backend_factory, grant, key, plan, time_budget=None,
            *, transport=None, hnlo_replay=replay, label_parser=parse_label):
    """Dependency injection exists for CPU tests; production always NativeBackend."""
    results, pending = {}, []
    for i, row in enumerate(rows):
        previous = store.previous(i)
        if previous:
            if previous["status"] == "SUCCESS":
                raw = read(store.parent / f"samples/{i:06d}/raw.json")
                if (label_parser(raw["response"]) != previous["label"]
                        or hnlo_replay(raw, previous["label"]) != previous["hnlo"]):
                    raise ValueError("RESUME_CLASSIFICATION_OR_HNLO_REPLAY_MISMATCH")
                store.retain(i)
                results[row["sample_id"]] = previous
                continue
            # INVALID/error/interrupted calls are consumed. Never retry implicitly.
            if row["sample_id"] not in grant.get("retry_sample_ids", []):
                store.retain(i)
                results[row["sample_id"]] = previous
                continue
            if previous.get("attempts", 1) >= 2:
                raise PermissionError("AT_MOST_ONE_EXPLICIT_RETRY_PER_ID_IN_V1")
        pending.append((i, row, previous))
    if not set(grant.get("retry_sample_ids", [])) <= {r["sample_id"] for _, r, p in pending if p}:
        raise PermissionError("RETRY_IDS_MUST_BE_PREVIOUSLY_FAILED_PLANNED_IDS")
    started = time.monotonic()
    backend, blocked, active = None, False, None
    try:
        if pending:
            backend = backend_factory()
            write(store.root / "runtime.json", backend.environment)
        for i, row, previous in pending:
            if shutil.disk_usage(store.root).free < 2**30:
                blocked = True
                write(store.root / "stop.json", {"reason": "OUTPUT_FREE_BELOW_1GIB_KEEP_EXPORT_RESERVE", "ordinal": i})
                break
            if time_budget is not None and time.monotonic() - started >= time_budget:
                blocked = True
                write(store.root / "stop.json", {"reason": "TIME_BUDGET_STOP_BEFORE_NEXT_CALL", "ordinal": i})
                break
            active = (i, row, previous)
            attempts = previous.get("attempts", 1) + 1 if previous else 1
            store.start(i, {"sample_id": row["sample_id"], "input_sha256": row["image_sha256"],
                            "attempts": attempts, "attempt_id": grant["attempt_id"],
                            "prior_native_calls": previous.get("native_calls", 0) if previous else 0,
                            "is_retry": previous is not None, "wall_time_unix": time.time()})
            sample_start = time.monotonic()
            value = backend.generate(row["image"], store.root / f"samples/{i:06d}")
            value["identity"] = {"sample_id": row["sample_id"], "run_id": grant["run_id"],
                                 "input_sha256": row["image_sha256"],
                                 "model": MODELS[key] if transport is None else transport["model"],
                                 "config_sha256": digest(settings(key)) if transport is None else transport["config_sha256"],
                                 "manifest_sha256": digest(plan)}
            raw_hash = store.raw(i, value)  # durable before parse/HNLO/report
            label = label_parser(value["response"])
            try:
                h = hnlo_replay(value, label)
            except Exception as error:
                h = {"status": "HNLO_TECHNICAL_FAILURE", "hnlo": None,
                     "reason": error_record(error, "hnlo_replay"), "replay_status": "FAIL"}
            result = {"status": "SUCCESS" if label else "INVALID", "label": label,
                      "raw_sha256": raw_hash, "attempts": attempts,
                      "native_calls": (previous.get("native_calls", 0) if previous else 0) + 1,
                      "hnlo": h, "seconds": time.monotonic() - sample_start,
                      "generation_seconds": value.get("seconds"), "memory": value.get("memory"),
                      "hnlo_overhead": value.get("hnlo_overhead"), "raw_nonfinite": value.get("raw_nonfinite", False)}
            store.result(i, result)
            results[row["sample_id"]] = result
            active = None
            # HNLO incompatibility/failure never changes a successful classification.
            # Nonfinite model output itself blocks further calls as unreliable.
            if value.get("raw_nonfinite"):
                blocked = True
                write(store.root / "stop.json", {"reason": "NONFINITE_RAW_MODEL_OUTPUT", "ordinal": i})
                break
            if i == 11:
                write(store.root / "early12.json", {"completed_ordinals": list(range(12)),
                      "extra_inference_calls": 0, "technical_gate": "PASS",
                      "hnlo_probe": "SEE_PER_SAMPLE_EVIDENCE; classification continues independently"})
    except BaseException as error:
        blocked = True
        e = error_record(error, getattr(error, "stage", getattr(backend, "stage", "model_load")))
        from safeshift.pilot.diagnostics import failure_detail
        write(store.root / "failure_detail.json", failure_detail(error, e["stage"], e["subcomponent"]))
        write(store.root / "failure.json", e)
        if active:
            i, row, previous = active
            native = int((store.root / f"samples/{i:06d}/native_call.json").exists())
            result = {"status": "TECHNICAL_ERROR", "label": None,
                      "attempts": previous.get("attempts", 1) + 1 if previous else 1,
                      "native_calls": (previous.get("native_calls", 0) if previous else 0) + native,
                      "error_category": e["category"], "error": e,
                      "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None, "reason": "CLASSIFICATION_FAILED"}}
            # A torn result is never overwritten; finalizer accounts it as error.
            if not (store.root / f"samples/{i:06d}/result.json").exists():
                store.result(i, result)
            results[row["sample_id"]] = result
    finally:
        for r in rows:
            results.setdefault(r["sample_id"], {"status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0,
                                               "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None, "reason": "NOT_ATTEMPTED"}})
        write(store.root / "results.json", results)
    return results, blocked


def _record(root, row, p, label_parser):
    base = safe(root, f"calls/{row['ordinal']:06d}/run")
    sample = base / "samples/000000"
    result = {"sample_id": row["sample_id"], "image_sha256": row["image_sha256"],
              "status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0}
    started = sample / "started.json"
    native = sample / "native_call.json"
    raw = sample / "raw.json"
    saved = sample / "result.json"
    require(not native.exists() or started.exists(), "ORPHAN_NATIVE_MARKER")
    require(not raw.exists() or native.exists(), "ORPHAN_RAW")
    require(not saved.exists() or started.exists(), "ORPHAN_RESULT")
    if not started.exists():
        return result
    require(row["ordinal"] in p["scheduled_ordinals"], "UNSCHEDULED_CALL")
    start = read(started)
    require(start["sample_id"] == row["sample_id"] and start["input_sha256"] == row["image_sha256"]
            and start["attempt_id"] == p["attempt_id"] and start["attempts"] == 1, "START_BINDING")
    result.update(status="TECHNICAL_ERROR", attempts=1, native_calls=int(native.exists()),
                  reason="INTERRUPTED_OR_TORN_EVIDENCE")
    if raw.exists():
        value = read(raw)
        require(read(base / "identity.json") == _identity(p, row), "STORE_IDENTITY_CHANGED")
        require(value.get("identity") == _identity(p, row)["transport"], "RAW_INPUT_OR_RELEASE_CHANGED")
        label = label_parser(value["response"])
        if value.get("raw_nonfinite"):
            result.update(raw_sha256=sha(raw), reason="NONFINITE_RAW_MODEL_OUTPUT")
        else:
            result.update(status="SUCCESS" if label else "INVALID", label=label, raw_sha256=sha(raw))
            result.pop("reason", None)
    if saved.exists():
        value = read(saved)
        require(value["native_calls"] == result["native_calls"] and value["attempts"] == 1, "RESULT_CALL_ACCOUNTING")
        if value["status"] in ("SUCCESS", "INVALID"):
            # Nonfinite generated output remains a technical error, even if JSON parsed.
            require(raw.exists() and value["raw_sha256"] == sha(raw)
                    and value["label"] == label_parser(read(raw)["response"]), "RESULT_RAW_CUSTODY")
            require((value["status"] == "SUCCESS") == (value["label"] is not None), "RESULT_STATUS")
        else:
            require(value["status"] == "TECHNICAL_ERROR", "RESULT_STATUS_CONFLICT")
            result.update(status="TECHNICAL_ERROR", label=None, error=value.get("error", {}))
            if value.get("error"):
                result.pop("reason", None)
    return result


def recover(root, cohort_value, expected_plan_hash, *, label_parser=parse_label):
    """Read only a checked attempt. Torn valid raw is replayed into a new projection."""
    root = Path(root)
    snapshot = members(root)
    snapshot.pop("checksums.json", None)
    if (root / "checksums.json").exists():
        require(read(root / "checksums.json") == snapshot, "SEALED_JOURNAL_CHANGED")
    p = read(root / "plan.json")
    require(digest(p) == expected_plan_hash, "PLAN_CHECKSUM")
    rows = f.validate_cohort(cohort_value, p["cohort_sha256"])
    prior = read(root / "history.json")
    require(p == f.plan(cohort_value, p["cohort_sha256"], p["identity"], prior, p["history_sha256"],
        action=p["action"], series_id=p["series_id"], run_id=p["run_id"], attempt_id=p["attempt_id"],
        max_calls=p["max_calls"], max_seconds=p["max_seconds"], repair=p["repair"]), "PLAN_RECOMPUTE_MISMATCH")
    if (root / "calls").exists():
        expected = {f"{i:06d}" for i in p["scheduled_ordinals"]}
        require({v.name for v in (root / "calls").iterdir()} <= expected, "UNPLANNED_CALL_DIRECTORY")
    records = [_record(root, rows[i], p, label_parser) for i in p["scheduled_ordinals"]]
    # A failed load has no sample start and remains pending, with failure retained.
    h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
         "identity": p["identity"], "cohort_sha256": p["cohort_sha256"],
         "parent_history_sha256": p["history_sha256"], "action": p["action"], "repair": p["repair"],
         "records": records, "evidence_sha256": digest(snapshot)}
    f.checked_history([*prior, h], rows, p["cohort_sha256"], digest([*prior, h]))
    return h
