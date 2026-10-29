"""Stage controller around the existing execute/Store/parser/HNLO engine.

Each call has an exclusive subjournal. This permits policy/review between calls
without changing the released pilot engine or its historical notebook bytes.
"""
from collections import Counter
from pathlib import Path
import time

from safeshift.pilot.artifacts import Store, read, safe, sha, write, write_bytes
from safeshift.pilot.contract import digest, parse_label
from safeshift.pilot.hnlo import replay
from safeshift.pilot.runner import execute, error_record
from safeshift.pilot.report import measurements
from .source import require
from .train_contract import enrollment, model, policy_check


def not_attempted():
    return {"status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0,
            "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None}}


def native_custody(sample, raw):
    native = read(Path(sample) / "native.json")
    require(native["generated_ids"] == raw["generated_ids"] and raw["generated_ids"]
            and len(raw["steps"]) == len(raw["generated_ids"]), "NATIVE_RAW_TOKEN_CUSTODY")
    for n, step in enumerate(raw["steps"]):
        require(read(Path(sample) / f"steps/{n:03d}.json") == step, "RAW_LOGIT_CUSTODY")
    require(raw.get("cpu_tokenizer_replay", {}).get("status") == "PASS", "RAW_TOKENIZER_REPLAY_FAILURE")


class CandidateStore(Store):
    def raw(self, ordinal, record):
        checksum = super().raw(ordinal, record)  # preserve received raw before validation/parse
        native_custody(self.root / f"samples/{ordinal:06d}", record)
        return checksum


def recover(output, rows):
    """Reconcile disk, including torn raw/result writes and interrupted calls."""
    results = {}
    for i, row in enumerate(rows):
        sample = Path(output) / f"calls/{i:06d}/run/samples/000000"
        started = (sample / "started.json").exists()
        native = int((sample / "native_call.json").exists())
        value = not_attempted()
        if started:
            value = {"status": "TECHNICAL_ERROR", "label": None, "attempts": 1,
                     "native_calls": native, "reason": "INTERRUPTED_OR_TORN_EVIDENCE",
                     "hnlo": {"status": "HNLO_UNVERIFIED", "hnlo": None}}
        if (sample / "result.json").exists():
            try:
                saved = read(sample / "result.json")
                require(started and saved["attempts"] == 1 and saved["native_calls"] == native,
                        "JOURNAL_CALL_ACCOUNTING")
                require(saved["status"] in ("SUCCESS", "INVALID", "TECHNICAL_ERROR"), "JOURNAL_STATUS")
                if saved["status"] in ("SUCCESS", "INVALID"):
                    raw = read(sample / "raw.json")
                    require(native == 1 and sha(sample / "raw.json") == saved["raw_sha256"]
                            and parse_label(raw["response"]) == saved["label"]
                            and (saved["status"] == "SUCCESS") == (saved["label"] is not None), "RAW_CUSTODY")
                    native_custody(sample, raw)
                    require(raw["identity"]["sample_id"] == row["sample_id"]
                            and raw["identity"]["input_sha256"] == row["image_sha256"], "RAW_INPUT_IDENTITY")
                    if saved["hnlo"].get("replay_status") != "FAIL":
                        require(replay(raw, saved["label"]) == saved["hnlo"], "HNLO_REPLAY")
                value = saved
            except (OSError, ValueError, KeyError, TypeError):
                value.update(status="TECHNICAL_ERROR", label=None, reason="EVIDENCE_CUSTODY_LOSS")
        results[row["sample_id"]] = value
    return results


def observations(output, rows, results, sequence_counts=None):
    attempted = [r for r in rows if results[r["sample_id"]]["attempts"]]
    labels = Counter(results[r["sample_id"]]["label"] for r in attempted
                     if results[r["sample_id"]]["status"] == "SUCCESS")
    raw_sequences = sequence_counts
    if raw_sequences is None:
        raw_sequences = Counter()
        for i, row in enumerate(rows):
            path = Path(output) / f"calls/{i:06d}/run/samples/000000/raw.json"
            if path.exists():
                raw_sequences[digest(read(path)["generated_ids"])] += 1
    normals = [r for r in attempted if r["level"] == "Level04" and results[r["sample_id"]]["label"]]
    anomalies = [r for r in attempted if r["level"] != "Level04" and results[r["sample_id"]]["label"]]
    return {"attempted": len(attempted), "invalid": sum(v["status"] == "INVALID" for v in results.values()),
            "valid": sum(labels.values()), "label_counts": dict(labels),
            "max_identical_token_sequences": max(raw_sequences.values(), default=0),
            "normal_support": len(normals), "normal_false_alarms": sum(results[r["sample_id"]]["label"] != "Level04" for r in normals),
            "anomaly_support": len(anomalies), "false_safe": sum(results[r["sample_id"]]["label"] == "Level04" for r in anomalies)}


def behavior_stop(o, policy):
    if o["invalid"] > policy["invalid_max_count"]:
        return "JSON_INVALID_LIMIT"
    if o["max_identical_token_sequences"] > policy["repeat_max_count"]:
        return "REPEATED_TOKEN_SEQUENCE_LIMIT"
    if (o["valid"] >= policy["dominance_min_valid"]
            and max(o["label_counts"].values(), default=0) / o["valid"] > policy["dominance_max_fraction"]):
        return "LABEL_DOMINANCE_LIMIT"
    if (o["normal_support"] >= policy["normal_min_support"]
            and o["normal_false_alarms"] / o["normal_support"] > policy["normal_fpr_max"]):
        return "NORMAL_FALSE_ALARM_LIMIT"
    if (o["anomaly_support"] >= policy["anomaly_min_support"]
            and o["false_safe"] / o["anomaly_support"] > policy["anomaly_fnr_max"]):
        return "FALSE_SAFE_LIMIT"
    return None


def review_record(value, checkpoint, grant):
    require(type(value) is dict and value.get("schema") == "safeshift-candidate160-review-v1",
            "EXTERNAL_REVIEW_REQUIRED")
    for n, expected in {"checkpoint_sha256": digest(checkpoint), "attempt_id": grant["attempt_id"],
                        "run_id": grant["run_id"], "model_key": grant["model_key"],
                        "source_sha256": grant["source_sha256"], "manifest_sha256": grant["manifest_sha256"]}.items():
        require(value.get(n) == expected, "REVIEW_BINDING:" + n)
    require(value.get("decision") in ("CONTINUE", "STOP") and
            isinstance(value.get("research_lead_review_ref"), str) and value["research_lead_review_ref"].strip(),
            "RESEARCH_LEAD_DECISION_REQUIRED")
    return value["decision"]


def await_review(checkpoint, grant, reviews, deadline):
    """Only an external observation-bound Lead decision can open the next stage.

Missing decision/time cap closes the attempt; no resume or implicit retry.
The Owner may deliver an approved review record to this separate drop directory.
"""
    target = digest(checkpoint) + ".json"
    end = min(deadline, time.monotonic() + grant["policy"]["review_wait_seconds"])
    while True:
        path = safe(reviews, target)
        if path.is_file():
            value = read(path)
            review_record(value, checkpoint, grant)
            return value
        if time.monotonic() >= end:
            return None
        time.sleep(min(1, max(0, end - time.monotonic())))


class GuardedBackend:
    """No generation/parser changes: validate durable native evidence and memory."""
    def __init__(self, native, row, binding, *, memory=None):
        self.native, self.row, self.binding, self.memory = native, row, binding, memory
        self.environment = native.environment

    @property
    def stage(self):
        return self.native.stage

    def generate(self, image, sample):
        require(sha(image) == self.row["image_sha256"], "IMAGE_CHANGED_BEFORE_CALL")
        before = self.memory(True) if self.memory else None
        raw = self.native.generate(image, sample)
        raw["execution_release"] = self.binding
        if self.memory:
            raw["memory"] = self.memory(False)
            raw["memory_before"] = before
        return raw


def run_calls(output, plan, rows, factory, grant, *, memory=None, reviewer=await_review,
              reviews=None, deadline=None, clock=time.monotonic):
    """At most 160 one-call engine invocations; one cached checkpoint load.

Factory/reviewer/memory injection is for CPU tests. Production supplies only the
reviewed CandidateBackend and measured CUDA observers in the isolated worker.
"""
    require(len(rows) == len({r["sample_id"] for r in rows}) == 160, "EXACT_SHARED_160_PLAN")
    policy = policy_check(grant["policy"])
    output = Path(output)
    deadline = clock() + grant["max_seconds"] if deadline is None else deadline
    native, reason, sequence_counts = None, None, Counter()
    results = {r["sample_id"]: not_attempted() for r in rows}
    actual_config = grant["config_sha256"]
    try:
        with enrollment(grant["model_key"]):
            for i, row in enumerate(rows):
                if time.time() >= grant["expires_unix"]:
                    reason = "GRANT_EXPIRED_BEFORE_NEXT_CALL"
                    break
                if clock() >= deadline:
                    reason = "TIME_CAP_BEFORE_NEXT_CALL"
                    break
                store = CandidateStore(output / f"calls/{i:06d}/run", {
                    "ordinal": i, "sample_id": row["sample_id"], "model": model(grant["model_key"]),
                    "run_id": grant["run_id"], "attempt_id": grant["attempt_id"],
                    "source_sha256": grant["source_sha256"], "manifest_sha256": grant["manifest_sha256"],
                    "config_sha256": actual_config})
                def cached_factory():
                    nonlocal native
                    if native is None:
                        native = factory()
                        require(isinstance(native.serialized_tokenizer, bytes) and native.serialized_tokenizer,
                                "RAW_TOKENIZER_SERIALIZATION_REQUIRED")
                        write_bytes(output / "tokenizer/runtime_tokenizer.json", native.serialized_tokenizer)
                    return GuardedBackend(native, row, {n: grant[n] for n in
                        ("config_sha256", "source_sha256", "runtime_ref", "attempt_id", "run_id", "manifest_sha256")},
                        memory=memory)
                one, blocked = execute(store, [row], cached_factory, grant, grant["model_key"], plan,
                                       time_budget=max(0, deadline - clock()))
                results[row["sample_id"]] = one[row["sample_id"]]
                if blocked or results[row["sample_id"]]["status"] in ("TECHNICAL_ERROR", "NOT_ATTEMPTED"):
                    reason = "TECHNICAL_STOP"
                    break
                if results[row["sample_id"]]["raw_nonfinite"]:
                    reason = "NONFINITE_RAW_MODEL_OUTPUT"
                    break
                if results[row["sample_id"]]["hnlo"].get("replay_status") == "FAIL":
                    reason = "RAW_REPLAY_TECHNICAL_FAILURE"
                    break
                raw_path = store.root / "samples/000000/raw.json"
                sequence_counts[digest(read(raw_path)["generated_ids"])] += 1
                o = observations(output, rows, results, sequence_counts)
                reason = behavior_stop(o, policy)
                checkpoint = {"completed": i + 1, "observations": o,
                              "kind": "FIRST_IMAGE_TECHNICAL" if i == 0 else "EARLY_BEHAVIOR" if i + 1 == policy["early_behavior_after"] else "OBSERVATION",
                              "results_sha256": digest(results), "stop_reason": reason,
                              "model_key": grant["model_key"], "source_sha256": grant["source_sha256"],
                              "manifest_sha256": grant["manifest_sha256"], "attempt_id": grant["attempt_id"]}
                write(output / f"checkpoints/{i+1:03d}.json", checkpoint)
                if reason:
                    break
                if i + 1 in policy["review_after"]:
                    value = reviewer(checkpoint, grant, reviews, deadline)
                    if value is None:
                        reason = "RESEARCH_LEAD_REVIEW_REQUIRED"
                        break
                    decision = review_record(value, checkpoint, grant)
                    write(output / f"reviews/{i+1:03d}.json", value)
                    if decision != "CONTINUE":
                        reason = "RESEARCH_LEAD_STOP"
                        break
    except BaseException as error:
        reason = "CONTROLLER_FAILURE"
        write(output / "controller_failure.json", error_record(error, "candidate160_controller"))
    finally:
        results = recover(output, rows)
        if any(v["status"] == "TECHNICAL_ERROR" for v in results.values()):
            reason = reason or "EVIDENCE_CUSTODY_LOSS"
        write(output / "accounting.json", [{"ordinal": i, "sample_id": r["sample_id"], **results[r["sample_id"]]}
                                           for i, r in enumerate(rows)])
        write(output / "summary.json", {"status": "STOPPED" if reason else "COMPLETED_AWAITING_REVIEW",
              "reason": reason, "metrics": measurements(rows, results),
              "classification_quality": "AWAITING_RESEARCH_LEAD_REVIEW", "gpu_qualification": "SEE_MEASURED_WORKER_RECEIPTS",
              "full_train_authorized": False, "retry_or_resume_allowed": False})
    return results, reason
