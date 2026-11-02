"""Full-cohort journal controller, exercised only by synthetic CPU fixtures.

Reuses the released execute/Store/strict C1 parser/archive and process lease.
There is no native factory, image discovery or credential access in this route.
Real activation is fenced in fulltrain.launch until a separate release review.
"""
import hashlib
from pathlib import Path
import platform
import sys
import time

from safeshift.pilot.artifacts import Store, read, safe, sha, write, export, import_archive
from safeshift.pilot.contract import digest, parse_label
from safeshift.pilot.runner import execute, error_record
from .source import require
from .train_history import lease_key, members
from . import fulltrain as f


def synthetic_bytes(ordinal):
    return f"SYNTHETIC ONLY issue167 input {ordinal}\n".encode()


def synthetic_cohort():
    """Public deterministic byte fixtures, never images or model predictions."""
    from safeshift.pilot.contract import MASTER_SHA, DATA_REVISION
    return {"schema": "safeshift-fulltrain-cohort-v1", "split": "TRAIN", "master_sha256": MASTER_SHA,
        "data_revision": DATA_REVISION, "scope": "SYNTHETIC_ONLY",
        "samples": [{"ordinal": i, "sample_id": f"synthetic-{i:04d}",
                     "image_sha256": hashlib.sha256(synthetic_bytes(i)).hexdigest()} for i in range(f.COUNT)]}


def label_only(raw, label):
    return {"status": "HNLO_NOT_REQUESTED_LABEL_ONLY", "hnlo": None}


class BoundStore(Store):
    def raw(self, ordinal, record):
        checksum = super().raw(ordinal, record)
        expected = self.identity
        require(record.get("identity") == expected["transport"], "RAW_TRANSPORT_BINDING")
        require((self.root / f"samples/{ordinal:06d}/native_call.json").is_file(), "NATIVE_CALL_MARKER_REQUIRED")
        return checksum


def _record(root, row, p):
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
        label = parse_label(value["response"])
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
                    and value["label"] == parse_label(read(raw)["response"]), "RESULT_RAW_CUSTODY")
            require((value["status"] == "SUCCESS") == (value["label"] is not None), "RESULT_STATUS")
        else:
            require(value["status"] == "TECHNICAL_ERROR", "RESULT_STATUS_CONFLICT")
            result.update(status="TECHNICAL_ERROR", label=None, error=value.get("error", {}))
            if value.get("error"):
                result.pop("reason", None)
    return result


def _identity(p, row):
    return {"plan_sha256": digest(p), "ordinal": row["ordinal"], "series_id": p["series_id"],
        "attempt_id": p["attempt_id"], "execution_identity": p["identity"],
        "transport": {"sample_id": row["sample_id"], "run_id": p["run_id"],
                      "input_sha256": row["image_sha256"],
                      "model": {"id": p["identity"]["model_id"], "revision": p["identity"]["model_revision"]},
                      "config_sha256": digest(p["identity"]), "manifest_sha256": p["cohort_sha256"]}}


def recover(root, cohort_value, expected_plan_hash):
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
    records = [_record(root, rows[i], p) for i in p["scheduled_ordinals"]]
    # A failed load has no sample start and remains pending, with failure retained.
    h = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
         "identity": p["identity"], "cohort_sha256": p["cohort_sha256"],
         "parent_history_sha256": p["history_sha256"], "action": p["action"], "repair": p["repair"],
         "records": records, "evidence_sha256": digest(snapshot)}
    f.checked_history([*prior, h], rows, p["cohort_sha256"], digest([*prior, h]))
    return h


def import_attempt(archive, expected_sha256, destination, cohort_value, plan_hash):
    """Existing bounded ZIP verifier/importer; outer hash before any extraction."""
    require(sha(archive) == expected_sha256, "OUTER_ARCHIVE_CHECKSUM")
    root = import_archive(archive, destination)
    # import_archive intentionally omits checksums.json; content snapshot excludes it.
    return recover(root, cohort_value, plan_hash)


def rehearse(work, bundle, cohort_value, p, history, factory, *, hnlo_replay=None, clock=time.monotonic):
    """Test-only integration through the existing engine, with exact synthetic bytes.

    factory must be supplied by a test; no production/synthetic backend ships.
    This API cannot be opened for private inputs by a flag or an approval JSON.
    """
    require(cohort_value == synthetic_cohort(), "CPU_SYNTHETIC_FIXTURE_ONLY")
    expected = f.plan(cohort_value, digest(cohort_value), p["identity"], history, digest(history),
        action=p["action"], series_id=p["series_id"], run_id=p["run_id"], attempt_id=p["attempt_id"],
        max_calls=p["max_calls"], max_seconds=p["max_seconds"], repair=p["repair"])
    require(p == expected, "PLAN_CHANGED_BEFORE_EXECUTION")
    require(p["identity"]["model_id"].startswith("synthetic/"), "SYNTHETIC_MODEL_ID_REQUIRED")
    if p["identity"]["hnlo_policy"] == "LABEL_ONLY":
        require(hnlo_replay is None, "LABEL_ONLY_MUST_NOT_REOPEN_HNLO")
        evaluator = label_only
    else:
        require(callable(hnlo_replay), "EXISTING_LOCKED_HNLO_EVALUATOR_REQUIRED")
        evaluator = hnlo_replay
    work, bundle = Path(work), Path(bundle)
    work.mkdir(parents=True, exist_ok=True)
    lock_key = digest({"campaign": "issue167-synthetic", "model": p["identity"]["model_key"]})
    with lease_key(work, lock_key):
        # Every ancestor must be present as a verified directory/imported ZIP.
        # A caller-authored summary/hash alone is never sufficient for resume.
        for ancestor in history:
            prior_root = safe(work, ancestor["run_id"])
            require(prior_root.is_dir(), "MISSING_HISTORY_EVIDENCE")
            require(recover(prior_root, cohort_value, digest(read(prior_root / "plan.json"))) == ancestor,
                    "HISTORY_EVIDENCE_CHANGED")
        root = safe(work, p["run_id"])
        require(not root.exists(), "RUN_ALREADY_EXISTS")
        reservation = safe(work, "attempts/" + p["attempt_id"] + ".json")
        require(not reservation.exists(), "ATTEMPT_ALREADY_RESERVED")
        for i in p["scheduled_ordinals"]:
            require(sha(safe(bundle, f"{i:06d}.bin")) == cohort_value["samples"][i]["image_sha256"], "INPUT_CHECKSUM")
        write(reservation, {"plan_sha256": digest(p), "scope": "SYNTHETIC_ONLY"})
        root.mkdir()
        write(root / "plan.json", p)
        write(root / "history.json", history)
        write(root / "environment.json", {"python": sys.version, "platform": platform.platform(),
            "scope": "CPU_SYNTHETIC_ONLY", "randomness": "NONE", "dependencies": "stdlib",
            "source_identity": p["identity"]["implementation_sha256"]})
        native, stop, count = None, None, 0
        deadline = clock() + p["max_seconds"]
        try:
            for i in p["scheduled_ordinals"]:
                if clock() >= deadline:
                    stop = "TIME_CAP"
                    break
                row = {**cohort_value["samples"][i], "image": str(safe(bundle, f"{i:06d}.bin"))}
                require(sha(row["image"]) == row["image_sha256"], "INPUT_CHANGED_BEFORE_CALL")
                store = BoundStore(root / f"calls/{i:06d}/run", _identity(p, row))
                def cached():
                    nonlocal native
                    if native is None:
                        write(root / "model_load.json", {"loads": 1, "scope": "SYNTHETIC_ONLY"})
                        native = factory()
                    return native
                grant = {"run_id": p["run_id"], "attempt_id": p["attempt_id"]}
                result, blocked = execute(store, [row], cached, grant, p["identity"]["model_key"], cohort_value,
                    time_budget=max(0, deadline - clock()), transport=_identity(p, row)["transport"], hnlo_replay=evaluator)
                count += result[row["sample_id"]]["native_calls"]
                require(count <= p["max_calls"], "CALL_CAP")
                write(root / f"checkpoints/{i:06d}.json", {"sample_id": row["sample_id"],
                    "result_sha256": digest(result), "native_calls": count, "plan_sha256": digest(p)})
                if blocked:
                    stop = "TECHNICAL_STOP"
                    break
        except BaseException as error:
            stop = "CONTROLLER_FAILURE"
            write(root / "controller_failure.json", error_record(error, "pipeline"))
            raise
        finally:
            actual_calls = sum((root / f"calls/{i:06d}/run/samples/000000/native_call.json").is_file()
                               for i in p["scheduled_ordinals"])
            write(root / "receipt.json", {"scope": "CPU_SYNTHETIC_ONLY", "native_calls": count,
                "observed_native_markers": actual_calls, "load_attempts": int((root / "model_load.json").exists()),
                "loads": int(native is not None), "stop": stop, "scientific_selection": "PENDING",
                "pooling_allowed": False, "planned_ids": f.COUNT, "plan_sha256": digest(p)})
            export(root, Path(str(root) + ".zip"))
        return root
