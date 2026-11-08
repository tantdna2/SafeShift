"""Fresh grammar-V2 TRAIN3763 preparation. Native authority is deliberately closed.

The test-only factory seam exercises the same controller with synthetic records;
there is no production backend that invents predictions.
"""
from collections import Counter
import hashlib
import re
from pathlib import Path
import shutil
import time
import traceback

from safeshift.candidates import fulltrain as planning
from safeshift.candidates.source import ROOT, require
from safeshift.internvl_grammar import HNLO_STATUS, POLICY
from safeshift import internvl_v2_runtime as capture
from safeshift.pilot.artifacts import read, write, sha, safe, export, verify_archive
from safeshift.pilot.contract import digest, parse_label, PROMPT_SHA

IDENTITY = "internvl35-grammar-v2-train3763-execution-candidate-v1"
SERIES = "train3763-internvl35-grammar-v2-v1"
OWN = ["safeshift/internvl3763.py", "scripts/internvl3763.py"]
MINIMUM_EXECUTION_SECONDS = 120
STAGE_EXPORT_RESERVE_SECONDS = 60
WORKER_EXIT_RESERVE_SECONDS = 15
LAUNCH_WORKER_HEADROOM_SECONDS = STAGE_EXPORT_RESERVE_SECONDS + WORKER_EXIT_RESERVE_SECONDS
PRE_CALL_RESERVE_SECONDS = 180
EXPORT_RESERVE_BYTES_PER_SECOND = 5 * 2**20
SUPERVISED_WORKER_LOG_SOFT_LIMIT_BYTES = 12 * 2**20
CGROUP_MIN_FREE_BYTES = 512 * 2**20


def authorize(stage="worker", **kwargs):
    from safeshift.internvl3763_release import authorize as check
    try:
        return check(stage, **kwargs)
    except ValueError as error:
        raise PermissionError(str(error)) from error


def source_spec():
    inherited = capture.source_spec()
    capture.check_source(inherited)
    return {"identity": IDENTITY, "manifest": {**inherited["manifest"],
        **{p: sha(ROOT / p) for p in [*OWN, "safeshift/internvl3763_release.py", "safeshift/kaggle_handoff.py",
            "safeshift/internvl3763_campaign.py", "safeshift/internvl3763_operator.py"]}}}


def check_source(spec):
    require(spec == source_spec(), "TRAIN3763_EXACT_SOURCE_REQUIRED")
    return digest(spec)


def configuration():
    old = read(ROOT / "configs/grammar/internvl35_v2_runtime.json")
    return {"schema": IDENTITY + "-config", "model": old["checkpoint"],
        "revision": old["revision"], "dtype": old["dtype"], "attention": old["attention"],
        "method": old["scientific_method"], "grammar_sha256": capture.FROZEN["safeshift/internvl_grammar.py"],
        "descriptor_sha256": capture.FROZEN["configs/grammar/internvl35_v2.json"],
        "prompt_sha256": PROMPT_SHA, "generation": dict(POLICY),
        "hnlo": None, "hnlo_status": HNLO_STATUS, "count": planning.COUNT,
        "resource_policy": old["resource_policy"], "prediction_inheritance": False,
        "execution_authority": None, "live_verification": "NOT_VERIFIED_FINAL_SOURCE"}


def identity():
    from safeshift.fulltrain.contract import native_identity
    old = native_identity("internvl35")
    return planning.identity({**old, "implementation_sha256": digest(source_spec()),
        "configuration_sha256": digest(configuration()), "hnlo_policy": "LABEL_ONLY",
        "generation_sha256": digest(POLICY)})


def plan(cohort, history, *, action, run_id, attempt_id, max_calls, max_seconds):
    require(action in ("initial", "resume"), "REPAIR_OR_RERUN_REQUIRES_SEPARATE_REVIEW")
    spec = identity()
    require(all(h["series_id"] == SERIES and h["identity"] == spec for h in history),
            "NO_FOREIGN_OR_HISTORICAL_PREDICTIONS")
    return planning.plan(cohort, digest(cohort), spec, history, digest(history), action=action,
        series_id=SERIES, run_id=run_id, attempt_id=attempt_id,
        max_calls=max_calls, max_seconds=max_seconds)


def trace_binding(spec, p, row, tokenizer_sha, plan_sha=None):
    return {"source_sha256": digest(spec), "tokenizer_sha256": tokenizer_sha,
        "model_revision_sha256": digest(configuration()["revision"]),
        "input_sha256": row["image_sha256"], "prompt_sha256": PROMPT_SHA,
        "generation_sha256": digest(POLICY), "series_sha256": digest({
            "series": p["series_id"], "plan": digest(p) if plan_sha is None else plan_sha, "ordinal": row["ordinal"]})}


def generate_prepared(backend, inputs, sample, binding, deadline, *, ordinal=None):
    """Same approved V2 capture/grammar/replay, with separate closed authority.

    No patch of the old campaign's authorization or qualification identity.
    """
    authorize("worker")
    import torch
    from unittest.mock import patch
    from safeshift.candidates.backend import persist_ids
    from safeshift.internvl_grammar import VERSION, PROCESSOR
    sample = Path(sample)
    grammar = capture.native_grammar(backend.tokenizer, backend.generation.eos_token_id,
        inputs["input_ids"][0].tolist(), backend.logit_width)
    require(backend.key == "internvl35" and all(getattr(backend.generation, k) == v
        for k, v in POLICY.items() if k != "batch_size"), "FROZEN_V2_GENERATION")
    write(sample / "grammar.json", grammar.receipt())
    observer = capture.Capture(grammar, sample, deadline)
    original = backend.model._get_logits_processor
    handle = backend.model.register_forward_hook(observer.forward, with_kwargs=True)
    try:
        with patch.object(backend.model, "_get_logits_processor",
                lambda *a, **k: observer.processors(original, *a, **k)), torch.inference_mode():
            observer.check_time()
            write(sample / "call-reservation.json", {"binding": binding, "outcome": "UNKNOWN_UNTIL_CLAIM_RETURN"})
            claim = authorize("call", ordinal=ordinal)
            write(sample / "call-claim.json", claim)
            observer.check_time()  # a slow/ambiguous remote claim never extends the call window
            write(sample / "native_call.json", {"identity": IDENTITY, "binding": binding, "calls": 1})
            generated = backend.model.generate(**inputs, generation_config=backend.generation,
                prefix_allowed_tokens_fn=grammar.callback())
    finally:
        handle.remove()
    input_ids, generated_ids = persist_ids(generated, inputs, "internvl35", sample / "native.json")
    response = backend.tokenizer.decode(generated_ids, skip_special_tokens=True,
        clean_up_tokenization_spaces=False)
    raw = {"schema": VERSION + "-trace", "binding": binding, "grammar": grammar.receipt(),
        "policy": dict(POLICY), "actual_logits_processors": observer.actual,
        "capture_origin": "scripted_before_processors" if getattr(backend, "evidence_kind", "NATIVE") == "SYNTHETIC" else "forward_before_processors",
        "evidence_kind": getattr(backend, "evidence_kind", "NATIVE"),
        "capture_error": None, "input_ids": input_ids, "generated_ids": generated_ids,
        "response": response, "raw_vector_hashes": observer.raw_hashes,
        "masked_vector_hashes": observer.step_hashes, "logit_width": grammar.vocab,
        "tokenizer_size": len(backend.tokenizer), "hnlo": None, "hnlo_status": HNLO_STATUS}
    checksum = write(sample / "raw.json", raw)  # fsync BEFORE parse and replay
    label = parse_label(read(sample / "raw.json")["response"])
    require(observer.actual == [PROCESSOR], "EXACT_NATIVE_PROCESSOR")
    verified = True
    try:
        replay = capture.replay_saved(sample, backend.tokenizer, backend.cpu_tokenizer, binding, checksum)
        write(sample / "trace-verification.json", replay)
    except ValueError as error:
        verified = False
        write(sample / "trace-failure.json", {"status": "FAIL", "type": type(error).__name__})
    status = "INVALID" if label is None else "SUCCESS" if verified else "TECHNICAL_ERROR"
    return {"status": status, "label": label if status == "SUCCESS" else None,
        "raw_sha256": checksum, "trace_verified": verified, "hnlo": None, "hnlo_status": HNLO_STATUS}


class NativeBackend:
    def __init__(self, source, weights, out, deadline):
        claim = authorize("load")
        write(Path(out) / "load-claim.json", claim)
        from safeshift.candidates.backend import CandidateBackend
        from safeshift import internvl_v2_memory as memory
        from scripts.internvl_v2 import policy
        import sys
        def verifier(path, key):
            receipt = memory.verify_checkpoint(path, key, out, "loader-checkpoint-stream", deadline)
            write(Path(out) / "loader-resources.json", memory.resource_check(out,
                "loader-resources", policy(), Path(sys.prefix).parent))
            return receipt
        require(time.monotonic() < deadline, "DEADLINE_BEFORE_MODEL_LOAD")
        self.backend = CandidateBackend("internvl35", source, weights,
            (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf8"),
            device="cuda:0", weight_verifier=verifier)
        self.backend.logit_width = self.backend.config.text_config.vocab_size
        self.backend.evidence_kind = "NATIVE"
        self.environment = self.backend.environment

    def generate(self, image, sample, binding, deadline):
        authorize("worker")
        from PIL import Image
        from safeshift.candidates.inputs import prepare_inputs, validate_inputs
        from safeshift.candidates.backend import transfer_inputs
        b = self.backend
        with Image.open(image) as original:
            require(getattr(original, "n_frames", 1) == 1, "STILL_IMAGE_REQUIRED")
            original.load()
            with original.convert("RGB") as converted:
                rendered, inputs = prepare_inputs(b.processor, "internvl35", b.prompt, converted)
                detail = validate_inputs(b.processor, "internvl35", b.config, rendered, inputs, b.prompt)
        write(Path(sample) / "request.json", {"prompt": b.prompt, "rendered_prompt": rendered,
            "input_ids": inputs["input_ids"][0].tolist(), "input_detail": detail,
            "generation": b.generation.to_dict(), "binding": binding})
        return generate_prepared(b, transfer_inputs(inputs, b.device, b.dtype), sample, binding, deadline,
            ordinal=int(Path(sample).name))


def capture_budget(vocab=200000, steps=64):
    require(type(vocab) is int and 0 < vocab <= 200000 and type(steps) is int
        and 0 < steps <= 64, "CAPTURE_DIMENSION_BOUND")
    # Full f32 vector + masked JSON (null outside <=4 allowed IDs), metadata.
    # Two copies reserve room for an uncompressed-size ZIP; compression is not assumed.
    per_sample = steps * (9 * vocab + 65536) + 2**20
    return {"per_sample_bytes": per_sample, "sample_and_export_bytes": 2 * per_sample,
        "all3763_uncompressed_bytes": per_sample * planning.COUNT,
        "archive_verifier_limit_bytes": 8 * 2**30,
        "basis": "CONSERVATIVE_ENGINEERING_BOUND_NOT_MEASURED_THROUGHPUT"}


def _backend_capture_budget(backend):
    inner = getattr(backend, "backend", backend)
    tokenizer = getattr(inner, "tokenizer", None)
    generation = getattr(inner, "generation", None)
    width = getattr(inner, "logit_width", None)
    if tokenizer is not None and generation is not None and type(width) is int and 0 < width <= 200000:
        eos = getattr(generation, "eos_token_id", None)
        if eos is not None and all(getattr(generation, k, None) == v for k, v in POLICY.items() if k != "batch_size"):
            from safeshift.internvl_grammar import LEVELS, PROCESSOR, VERSION
            grammar = capture.native_grammar(tokenizer, eos, [0], width)
            receipt = grammar.receipt()
            lengths = receipt["path_lengths"]
            require(receipt["id"] == VERSION and receipt["policy"] == dict(POLICY)
                and receipt["actual_processors_required"] == [PROCESSOR]
                and receipt["language"] == [f'{{"safety_level":"{lv}"}}' for lv in LEVELS]
                and len(lengths) == len(LEVELS) and len(set(lengths)) == 1
                and receipt["required_tokens_including_eos"] == lengths[0] + 1
                and 0 < grammar.required_tokens <= POLICY["max_new_tokens"] <= 64,
                "CAPTURE_DIMENSION_BOUND")
            return capture_budget(vocab=width, steps=grammar.required_tokens)
    return capture_budget()


def _sample_files_and_bytes(sample):
    files = [path for path in Path(sample).rglob("*") if path.is_file()]
    return len(files), sum(path.stat().st_size for path in files)


def _supervised_log_bytes(export_root):
    total = 0
    for folder in (export_root, export_root / "environment"):
        if folder.is_dir():
            for entry in folder.iterdir():
                if entry.suffix == ".log" and not entry.is_symlink() and entry.is_file():
                    total += entry.stat().st_size
    return total


def _strict_json_loads(payload):
    import json
    def pairs(items):
        obj = {}
        for k, v in items:
            if k in obj:
                raise ValueError("DUPLICATE_JSON_KEY")
            obj[k] = v
        return obj
    return json.loads(payload, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def inspect_memory_snapshot(snap, *, min_free_bytes=CGROUP_MIN_FREE_BYTES):
    """Validate real internvl_v2_memory.snapshot() v2 schema; fail closed on any defect.

    snapshot() observes Linux cgroup v2 files plus /proc host/process telemetry and sets
    top-level status == 'OBSERVED' only when errors == [] and all required fields exist.
    Missing, malformed, cgroup-v1-only ('INCOMPLETE'), OOM, or low-headroom states return
    an explicit stop/rejection code instead of silently passing.
    """
    require(type(min_free_bytes) is int and min_free_bytes > 0, "CGROUP_MIN_FREE_BYTES")
    if type(snap) is not dict:
        return "CGROUP_MEMORY_UNOBSERVED"
    if (snap.get("schema") != "internvl-v2-memory-v1"
            or snap.get("status") != "OBSERVED"
            or type(snap.get("errors")) is not list
            or len(snap["errors"]) != 0):
        return "CGROUP_MEMORY_UNOBSERVED"
    cg = snap.get("cgroup")
    proc = snap.get("process")
    gate = snap.get("gate_memory")
    if type(cg) is not dict or type(proc) is not dict or type(gate) is not dict:
        return "CGROUP_MEMORY_UNOBSERVED"
    if not set(cg).issubset({"memory.current", "memory.max", "memory.peak", "memory.stat", "memory.events"}):
        return "CGROUP_MEMORY_UNOBSERVED"
    if set(gate) != {"available_bytes", "cgroup_remaining_bytes"}:
        return "CGROUP_MEMORY_UNOBSERVED"
    proc_status = proc.get("status")
    smaps = proc.get("smaps_rollup")
    if (type(proc_status) is not dict
            or type(proc_status.get("VmRSS")) is not int
            or proc_status["VmRSS"] < 0
            or not all(type(k) is str and type(v) is int and v >= 0 for k, v in proc_status.items())
            or type(smaps) is not dict
            or not all(type(k) is str and type(v) is int and v >= 0 for k, v in smaps.items())):
        return "CGROUP_MEMORY_UNOBSERVED"
    stats = cg.get("memory.stat")
    events = cg.get("memory.events")
    if (type(stats) is not dict
            or not all(k in stats for k in ("anon", "file"))
            or not all(type(k) is str and type(v) is int and v >= 0 for k, v in stats.items())
            or type(events) is not dict
            or "oom_kill" not in events
            or not all(type(k) is str and type(v) is int and v >= 0 for k, v in events.items())):
        return "CGROUP_MEMORY_UNOBSERVED"
    current = cg.get("memory.current")
    limit = cg.get("memory.max")
    if type(current) is not int or current < 0:
        return "CGROUP_MEMORY_UNOBSERVED"
    if not (limit == "max" or (type(limit) is int and limit >= 0)):
        return "CGROUP_MEMORY_UNOBSERVED"
    if "memory.peak" in cg:
        peak = cg["memory.peak"]
        if not (peak == "max" or (type(peak) is int and peak >= 0)):
            return "CGROUP_MEMORY_UNOBSERVED"
    avail = gate.get("available_bytes")
    cg_rem = gate.get("cgroup_remaining_bytes")
    if (type(avail) is not int or avail < 0
            or type(cg_rem) is not list
            or not all(type(x) is int and x >= 0 for x in cg_rem)):
        return "CGROUP_MEMORY_UNOBSERVED"
    if any(events.get(k, 0) > 0 for k in ("oom", "oom_kill", "oom_group_kill")):
        return "CGROUP_OOM_OBSERVED"
    if type(limit) is int and limit - current < min_free_bytes:
        return "CGROUP_MEMORY_HEADROOM_LOW"
    if avail < min_free_bytes or any(x < min_free_bytes for x in cg_rem):
        return "CGROUP_MEMORY_HEADROOM_LOW"
    return None


def _cgroup_memory_issue(backend):
    if not isinstance(backend, NativeBackend) and not getattr(backend, "check_cgroup_memory", False):
        return None
    from safeshift.internvl_v2_memory import snapshot
    return inspect_memory_snapshot(snapshot())


def _cgroup_memory_low(backend):
    return _cgroup_memory_issue(backend) is not None


def _execute(out, archive, cohort, p, factory, *, image_path, tokenizer_sha, clock=time.monotonic,
             archive_limit_bytes=7 * 2**30, hard_deadline=None, pre_call_reserve_seconds=PRE_CALL_RESERVE_SECONDS):
    """Bounded shared controller. Public entrypoints gate before reaching here."""
    require(type(archive_limit_bytes) is int and archive_limit_bytes > 0, "ARCHIVE_LIMIT_BYTES")
    require(type(pre_call_reserve_seconds) is int and pre_call_reserve_seconds >= PRE_CALL_RESERVE_SECONDS,
        "PRE_CALL_RESERVE_SECONDS")
    rows = planning.validate_cohort(cohort, digest(cohort))
    plan_sha = digest(p)
    from safeshift import internvl3763_campaign as campaign
    expected_identity = campaign.identity() if p["schema"] == campaign.PLAN else identity()
    require(p["identity"] == expected_identity and p["cohort_sha256"] == digest(cohort)
            and p["series_id"] == SERIES, "EXACT_PLAN_IDENTITY")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    spec = source_spec()
    write(out / "source.json", spec)
    write(out / "plan.json", p)
    write(out / "configuration.json", configuration())
    write(out / "cohort.json", cohort)
    begun = clock()
    deadline = begun + p["max_seconds"] if hard_deadline is None else min(begun + p["max_seconds"], hard_deadline)
    telemetry = {"evidence_kind": "UNVERIFIED", "load_seconds": 0, "samples": []}
    records = [{**r, "status": "NOT_ATTEMPTED", "label": None, "attempts": 0, "native_calls": 0,
                "hnlo": None, "hnlo_status": HNLO_STATUS} for r in rows]
    failure, calls, backend = None, 0, None
    try:
        if p["scheduled_ordinals"]:
            write(out / "load-reservation.json", {"loads": 1, "plan_sha256": plan_sha})
            backend = factory(deadline)
            write(out / "loaded.json", backend.environment)
            telemetry["load_seconds"] = clock() - begun
        sample_budget = _backend_capture_budget(backend) if backend is not None else capture_budget()
        inner_backend = getattr(backend, "backend", backend) if backend is not None else None
        raw_vocab = getattr(inner_backend, "logit_width", None)
        fallback_vocab = raw_vocab if (type(raw_vocab) is int and 0 < raw_vocab <= 200000) else 200000
        supervised = (out.parent / "handoff.json").is_file()
        export_root = out.parent if supervised else out
        existing = [path for path in export_root.rglob("*") if path.is_file()]
        retained = sum(path.stat().st_size for path in existing)
        member_count = len(existing)
        summary_margin = 16 * 2**20 if archive_limit_bytes > 64 * 2**20 else 0
        effective_archive_limit = min(archive_limit_bytes, sample_budget["archive_verifier_limit_bytes"]) - summary_margin
        for ordinal in p["scheduled_ordinals"]:
            require(calls < p["max_calls"], "CALL_CAP")
            max_observed_bytes = max((x["bytes"] for x in telemetry["samples"]), default=0)
            per_sample_bound = sample_budget["per_sample_bytes"]
            if max_observed_bytes > per_sample_bound:
                per_sample_bound = max(2 * max_observed_bytes,
                    capture_budget(vocab=fallback_vocab, steps=64)["per_sample_bytes"])
            written_sample_bytes = sum(x["bytes"] for x in telemetry["samples"])
            export_payload_bytes = (retained if written_sample_bytes == 0 else max(retained, written_sample_bytes)) + per_sample_bound
            extra_export_reserve = (max(0.0, export_payload_bytes / EXPORT_RESERVE_BYTES_PER_SECOND
                - STAGE_EXPORT_RESERVE_SECONDS)
                if (written_sample_bytes > 0 or retained > STAGE_EXPORT_RESERVE_SECONDS * EXPORT_RESERVE_BYTES_PER_SECOND)
                else 0.0)
            now = clock()
            next_call_reserve = max(pre_call_reserve_seconds,
                2 * max((x["seconds"] for x in telemetry["samples"]), default=0)) + extra_export_reserve
            if now >= deadline or now + next_call_reserve >= deadline:
                write(out / "stop.json", {"reason": "DEADLINE_BEFORE_NEXT_CALL"})
                break
            free_spaces = [shutil.disk_usage(export_root).free]
            if supervised:
                free_spaces.append(shutil.disk_usage(export_root.parent).free)
            if archive is not None:
                Path(archive).parent.mkdir(parents=True, exist_ok=True)
                free_spaces.append(shutil.disk_usage(Path(archive).parent).free)
            if min(free_spaces) < retained + 2 * per_sample_bound + 2**30:
                write(out / "stop.json", {"reason": "CAPTURE_AND_EXPORT_SPACE_NOT_AVAILABLE"})
                break
            if retained + per_sample_bound > effective_archive_limit or member_count + 256 >= 1000000:
                write(out / "stop.json", {"reason": "ARCHIVE_VERIFIER_8GIB_BOUND_EXPORT_MARGIN"})
                break
            if supervised and _supervised_log_bytes(export_root) >= SUPERVISED_WORKER_LOG_SOFT_LIMIT_BYTES:
                write(out / "stop.json", {"reason": "WORKER_LOG_BUDGET_MARGIN"})
                break
            memory_issue = _cgroup_memory_issue(backend)
            if memory_issue is not None:
                write(out / "stop.json", {"reason": memory_issue})
                break
            row = rows[ordinal]
            image = Path(image_path(row))
            require(sha(image) == row["image_sha256"], "EXACT_IMAGE_SHA256")
            sample = safe(out, f"samples/{ordinal:06d}")
            write(sample / "started.json", {"row": row, "plan_sha256": plan_sha})
            binding = trace_binding(spec, p, row, tokenizer_sha, plan_sha)
            sample_started = clock()
            try:
                value = backend.generate(image, sample, binding, deadline)
                marker = read(sample / "native_call.json")
                require(marker["binding"] == binding, "CALL_BINDING")
                raw = read(sample / "raw.json")
                require(sha(sample / "raw.json") == value["raw_sha256"]
                    and raw["binding"] == binding and raw["hnlo"] is None
                    and raw["hnlo_status"] == HNLO_STATUS, "RAW_BINDING_OR_HNLO")
                label = parse_label(raw["response"])
                if value["status"] == "TECHNICAL_ERROR":
                    records[ordinal].update(value, attempts=1, native_calls=1)
                    write(sample / "result.json", records[ordinal])
                    raise RuntimeError("TRACE_VERIFICATION_FAILED")
                require(value["status"] == ("SUCCESS" if label else "INVALID")
                    and value["label"] == label
                    and ((value["trace_verified"] is True and (sample / "trace-verification.json").is_file())
                         or (label is None and (sample / "trace-failure.json").is_file())), "STRICT_RESULT_TRACE")
                records[ordinal].update(value, attempts=1, native_calls=1)
                write(sample / "result.json", records[ordinal])
            except BaseException:
                records[ordinal].update(status="TECHNICAL_ERROR", label=None, attempts=1,
                    native_calls=int((sample / "native_call.json").exists()))
                raise
            finally:
                sample_file_count, sample_bytes = _sample_files_and_bytes(sample)
                calls += int((sample / "native_call.json").exists())
                retained += sample_bytes
                member_count += sample_file_count
                telemetry["samples"].append({"ordinal": ordinal, "seconds": clock()-sample_started,
                    "bytes": sample_bytes})
    except BaseException as error:
        failure = {"type": type(error).__name__, "cause": "SEE_PRIVATE_STAGE_EVIDENCE",
            "message_sha256": hashlib.sha256(str(error).encode()).hexdigest(),
            "frames": [{"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
                for frame in traceback.extract_tb(error.__traceback__)[-8:]]}
        write(out / "failure.json", failure)
    telemetry["elapsed_seconds"] = clock()-begun
    if isinstance(backend, NativeBackend):
        import torch
        from safeshift.internvl_v2_memory import snapshot
        telemetry.update(evidence_kind="NATIVE", memory=snapshot(),
            gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(0),
            gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(0))
    write(out / "telemetry.json", telemetry)
    summary = {"schema": IDENTITY + "-result", "plan_sha256": plan_sha, "source_sha256": digest(spec),
        "series_id": SERIES, "run_id": p["run_id"], "attempt_id": p["attempt_id"],
        "status": "FAIL" if failure else "PASS", "failure": failure, "model_calls": calls,
        "planned": planning.COUNT, "counts": dict(Counter(r["status"] for r in records)),
        "hnlo": None, "hnlo_status": HNLO_STATUS, "records": records,
        "scope": cohort["scope"], "scientific_selection": "PENDING", "scientific_qualified": False}
    summary["accounting"] = "THIS_ATTEMPT_ONLY_NOT_A_SERIES_COMPLETION_UNION"
    summary["cohort_complete_this_attempt"] = all(r["status"] != "NOT_ATTEMPTED" for r in records)
    write(out / "summary.json", summary)
    if archive is not None:
        export(out, archive)
    return summary


def rehearse(out, archive, cohort, p, history, factory, **kwargs):
    require(cohort["scope"] == "SYNTHETIC_ONLY", "SYNTHETIC_ONLY")
    from safeshift import internvl3763_campaign as campaign
    planner = campaign.plan if p["schema"] == campaign.PLAN else plan
    options = {"repair": p["repair"]} if p["schema"] == campaign.PLAN else {}
    require(p == planner(cohort, history, action=p["action"], run_id=p["run_id"],
        attempt_id=p["attempt_id"], max_calls=p["max_calls"], max_seconds=p["max_seconds"], **options), "PLAN_DRIFT")
    return _execute(out, archive, cohort, p, factory, **kwargs)


def interrupted_summary(output, request, failure):
    """Supervisor-only conservative accounting after setup failure/child death.

    Preserve every byte. Unfinished started samples are consumed technical errors,
    even with a raw response; no implicit recovery to SUCCESS or another call.
    """
    out = Path(output) / "run"
    out.mkdir(exist_ok=True)
    if (out / "summary.json").exists():
        return read(out / "summary.json")
    p, cohort, spec = request["plan"], request["cohort"], request["source"]
    for name, value in (("source", spec), ("plan", p), ("cohort", cohort), ("configuration", configuration())):
        path = out / (name + ".json")
        if not path.exists():
            write(path, value)
        else:
            require(read(path) == value, "INTERRUPTED_RUNTIME_DRIFT")
    rows = planning.validate_cohort(cohort, digest(cohort))
    records = []
    for row in rows:
        sample = safe(out, f"samples/{row['ordinal']:06d}")
        started = (sample / "started.json").exists()
        native = (sample / "native_call.json").exists()
        durable = sample / "result.json"
        if durable.exists():
            try:
                value = read(durable)
                require(started and all(value[k] == v for k, v in row.items())
                    and value["attempts"] == 1 and value["native_calls"] == int(native)
                    and value["status"] in ("SUCCESS", "INVALID", "TECHNICAL_ERROR"), "DURABLE_RESULT_BINDING")
                if value["status"] in ("SUCCESS", "INVALID"):
                    require(native and sha(sample / "raw.json") == value["raw_sha256"]
                        and parse_label(read(sample / "raw.json")["response"]) == value["label"]
                        and ((value["status"] == "SUCCESS") == (value["label"] is not None)), "DURABLE_RAW_RESULT")
                records.append(value)  # already committed result; no reparse rescue
                continue
            except (ValueError, KeyError, OSError):
                pass  # torn/contradictory files survive; conservative error below
        records.append({**row, "status": "TECHNICAL_ERROR" if started else "NOT_ATTEMPTED",
            "label": None, "attempts": int(started), "native_calls": int(native),
            "hnlo": None, "hnlo_status": HNLO_STATUS,
            "reason": "INTERRUPTED_OR_TORN_EVIDENCE" if started else "WORKER_STOPPED_BEFORE_SAMPLE"})
    result = {"schema": IDENTITY + "-result", "plan_sha256": digest(p), "source_sha256": digest(spec),
        "series_id": SERIES, "run_id": p["run_id"], "attempt_id": p["attempt_id"],
        "status": "FAIL", "failure": failure, "model_calls": sum(r["native_calls"] for r in records),
        "planned": planning.COUNT, "counts": dict(Counter(r["status"] for r in records)),
        "records": records, "hnlo": None, "hnlo_status": HNLO_STATUS, "scope": cohort["scope"],
        "scientific_selection": "PENDING", "scientific_qualified": False,
        "accounting": "THIS_ATTEMPT_ONLY_NOT_A_SERIES_COMPLETION_UNION",
        "cohort_complete_this_attempt": all(r["status"] != "NOT_ATTEMPTED" for r in records)}
    write(out / "summary.json", result)
    return result


def validate_execution_request(request):
    from safeshift.pilot.contract import require_hash
    from safeshift.pilot.artifacts import relative
    require(set(request) == {"source", "cohort", "history", "history_archives", "plan", "input_marker_sha256",
        "projection_sha256"}, "EXECUTION_REQUEST_FIELDS")
    check_source(request["source"])
    require_hash(request["input_marker_sha256"])
    require(request["cohort"]["scope"] == "PRIVATE_TRAIN_METADATA", "PRIVATE_ORIGINAL_PROJECTION_REQUIRED")
    p = request["plan"]
    require(p["max_seconds"] >= MINIMUM_EXECUTION_SECONDS, "EXECUTION_MINIMUM_120_SECONDS")
    from safeshift import internvl3763_campaign as campaign
    planner = campaign.plan if p["schema"] == campaign.PLAN else plan
    options = {"repair": p["repair"]} if p["schema"] == campaign.PLAN else {}
    require(p == planner(request["cohort"], request["history"], action=p["action"], run_id=p["run_id"],
        attempt_id=p["attempt_id"], max_calls=p["max_calls"], max_seconds=p["max_seconds"], **options), "EXACT_EXECUTION_PLAN")
    require(request["projection_sha256"] == digest(request["cohort"]), "ORIGINAL_PROJECTION_BINDING")
    require(type(request["history_archives"]) is list
        and len(request["history_archives"]) == len(request["history"]), "SEALED_HISTORY_ARCHIVES_REQUIRED")
    for ancestor, custody in zip(request["history"], request["history_archives"]):
        require(type(custody) is dict and set(custody) == {"archive", "sha256", "plan"}, "HISTORY_ARCHIVE_CUSTODY_FIELDS")
        relative(custody["archive"])
        require(custody["sha256"] == ancestor["evidence_sha256"]
            and custody["plan"]["run_id"] == ancestor["run_id"]
            and custody["plan"]["attempt_id"] == ancestor["attempt_id"], "HISTORY_ARCHIVE_PLAN_BINDING")
    return p


def preflight(spec, out, scratch, inputs, deadline):
    """Shared measured environment preparation, no weights load/model call."""
    authorize("preflight")
    from scripts import internvl_v2 as old
    from safeshift import internvl_v2_memory as memory
    from safeshift.fulltrain import environment
    from safeshift.fulltrain.preflight import storage_probe
    from safeshift.candidates.train_inputs import checkpoint
    from safeshift.candidates.source import verify_snapshot
    from scripts.smoke_kaggle173 import bind_cuda_driver, driver_check
    check_source(spec)
    budgets = old.policy()
    write(out / "resources.json", memory.resource_check(out, "resources", budgets, scratch))
    write(out / "allocation.json", storage_probe(scratch, out,
        scratch_bytes=budgets["scratch_probe_bytes"], output_bytes=budgets["output_probe_bytes"]))
    bind_cuda_driver(out)
    write(out / "software.json", environment.software("internvl35"))
    write(out / "hardware.json", driver_check("internvl35", budgets, out, "worker"))
    write(out / "cuda.json", environment.cuda("internvl35", budgets))
    marker, source, weights = checkpoint(inputs, "internvl35")
    native = verify_snapshot(source, "internvl35")
    actual = memory.verify_checkpoint(weights, "internvl35", out, "checkpoint-stream", deadline)
    write(out / "checkpoint.json", {"marker_sha256": sha(marker), "source": native,
        "weights": actual, "weights_loaded": False})
    write(out / "source.json", capture.source_spec())  # exact legacy CPU child --spec path
    old.run_processor_check(capture.source_spec(), out, scratch, inputs, budgets, deadline)
    old.reclaim_owned(scratch, out)
    write(out / "preload-resources.json", memory.resource_check(out, "preload-resources", budgets, scratch))
    write(out / "preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS", "source_sha256": digest(spec),
        "model_calls": 0, "weights_loaded": False, "owner_slots_consumed": 0})
    return source, weights


def worker(request_path=None, *, output=None, scratch=None, inputs=None, deadline=None):
    if request_path is None:
        authorize()
    from safeshift import internvl3763_release as authority
    handoff = read(request_path)
    if handoff["scope"] == "TRAIN3763_CAMPAIGN":
        grant = authority.activate(handoff, "worker", intent=read(Path(request_path).parent / "campaign-intent.json"))
    else:
        grant = authority.activate(handoff, "worker")
    authorize()
    from safeshift.fulltrain.inputs import admit, verify_image_bytes
    request = authority.bind(grant, handoff)
    p = validate_execution_request(request)
    # A structurally valid caller-authored history alone is insufficient.
    # Reconcile each exact sealed ancestor before any environment/load work.
    for ancestor, custody in zip(request["history"], request["history_archives"]):
        require(set(custody) == {"archive", "sha256", "plan"}, "HISTORY_ARCHIVE_CUSTODY_FIELDS")
        if handoff["scope"] == "TRAIN3763_CAMPAIGN":
            # The authenticated campaign delegates custody admission to the
            # sole operator. Its durable intent binds the full checked lineage.
            # Reuploading every previous raw ZIP is neither needed nor implied.
            continue
        require(sealed_history(safe(inputs, custody["archive"]), custody["sha256"], custody["plan"]) == ancestor,
            "HISTORY_ARCHIVE_ANCESTOR_MISMATCH")
    environment_out = Path(output) / "environment"
    environment_out.mkdir(exist_ok=False)
    write(environment_out / "worker-claim.json", authority.activation_claim())
    source, weights = preflight(request["source"], environment_out, scratch, inputs, deadline)
    if handoff["scope"] == "TRAIN3763_CAMPAIGN":
        from safeshift.internvl3763_campaign import admit_inputs
        root, cohort, rows, image_receipt = admit_inputs(inputs, request["input_marker_sha256"], request["projection_sha256"])
    else:
        root, cohort, rows = admit(inputs, request["input_marker_sha256"], request["projection_sha256"])
        image_receipt = verify_image_bytes(root, cohort, rows)
    require(cohort == request["cohort"], "ORIGINAL_MASTER_CUSTODY")
    write(environment_out / "image-bytes.json", image_receipt)
    return _execute(Path(output) / "run", None, cohort, p,
        lambda end: NativeBackend(source, weights, Path(output) / "run", min(end, deadline)),
        image_path=lambda row: safe(root, rows[row["ordinal"]]["image"]),
        tokenizer_sha=sha(source / "tokenizer.json"), archive_limit_bytes=grant["caps"]["archive_bytes"],
        hard_deadline=deadline)


def verify_bundle(archive, expected_sha, expected_plan):
    import zipfile
    plan_sha = digest(expected_plan)
    require(sha(archive) == expected_sha == read(str(archive) + ".sha256.json")["sha256"], "ZIP_SIDECAR")
    members = verify_archive(archive)  # membership, paths, bounds, all hashes and CRC
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, "ZIP_CRC")
        prefix = "" if "summary.json" in members else "run/"
        get = lambda name: _strict_json_loads(z.read(prefix + name))
        require(get("plan.json") == expected_plan, "ARCHIVE_PLAN_BINDING")
        result, cohort, spec = get("summary.json"), get("cohort.json"), get("source.json")
        from safeshift import internvl3763_campaign as campaign
        if expected_plan["schema"] == campaign.PLAN:
            require(spec == expected_plan["runtime_source"] and expected_plan["science_sha256"] == digest(campaign.science())
                and get("configuration.json") == configuration(), "HISTORICAL_CAMPAIGN_SOURCE_SCIENCE")
            inherited = capture.source_spec()["manifest"]
            require(all(spec["manifest"].get(k) == v for k, v in inherited.items()), "FROZEN_NATIVE_HISTORY_DRIFT")
        else:
            check_source(spec)
        if cohort["scope"] != "SYNTHETIC_ONLY":
            require(prefix == "run/", "SUPERVISED_NATIVE_ARCHIVE_REQUIRED")
            outer = lambda name: _strict_json_loads(z.read(name))
            require(outer("execution-request.json")["source"] == spec
                and outer("execution-request.json")["plan"] == expected_plan, "OUTER_RUNTIME_BINDING")
            require("terminal.json" in members and outer("terminal.json").get("status") == result["status"],
                "TERMINAL_RECEIPT_STATUS_MISMATCH")
            for name in ("setup/setup-supervisor.json", "worker-supervisor.json"):
                if name in members:
                    process = outer(name)
                    require(process.get("schema") == "fresh-process-supervision-v1"
                        and process.get("automatic_retry") is False, "SUPERVISOR_RECEIPT_CONTRACT")
            if result["status"] == "FAIL":
                require(outer("terminal.json").get("error") is not None or result["failure"] is not None,
                    "TERMINAL_FAIL_REASON_REQUIRED")
            if result["status"] == "PASS":
                for name in ("setup/setup-supervisor.json", "worker-supervisor.json"):
                    process = outer(name)
                    require(process["status"] == "EXITED" and process["returncode"] == 0
                        and process["automatic_retry"] is False, "SUPERVISED_NATIVE_EXIT_REQUIRED")
                require(outer("terminal.json")["status"] == "PASS"
                    and outer("environment/preflight.json")["source_sha256"] == digest(spec)
                    and outer("environment/preflight.json")["status"] == "LIVE_GPU_PREFLIGHT_PASS",
                    "POSITIVE_ENVIRONMENT_REQUIRED")
                for name in ("software.json", "hardware.json", "cuda.json", "allocation.json",
                             "checkpoint.json", "checkpoint-stream.json", "processor.json", "preload-resources.json"):
                    require("environment/" + name in members, "MISSING_ENVIRONMENT_RECEIPT")
        rows = planning.validate_cohort(cohort, expected_plan["cohort_sha256"])
        for name in members:
            local = name[len(prefix):] if name.startswith(prefix) else name
            if local.startswith("samples/"):
                match = re.fullmatch(r"samples/([0-9]{6})/(started\.json|native_call\.json|call-reservation\.json|call-claim\.json|raw\.json|result\.json|grammar\.json|request\.json|native\.json|processors\.json|trace-verification\.json|trace-failure\.json|steps/([0-9]{3})\.(f32|forward\.json|masked\.json))", local)
                require(match is not None and int(match[1]) in expected_plan["scheduled_ordinals"]
                    and (match[3] is None or int(match[3]) < 64), "UNEXPECTED_SAMPLE_ARCHIVE_MEMBER")
        require(result["plan_sha256"] == plan_sha and result["source_sha256"] == digest(spec)
            and result["scope"] == cohort["scope"] and len(result["records"]) == len(rows), "SUMMARY_BINDINGS")
        require(result["series_id"] == expected_plan["series_id"] == SERIES
            and result["run_id"] == expected_plan["run_id"]
            and result["attempt_id"] == expected_plan["attempt_id"]
            and result["hnlo"] is None and result["hnlo_status"] == HNLO_STATUS
            and result["status"] == ("FAIL" if result["failure"] else "PASS"), "RESULT_IDENTITY_STATUS")
        calls = 0
        for row, record in zip(rows, result["records"]):
            require(all(record[k] == v for k, v in row.items()) and record["status"] in planning.STATUSES
                and record["hnlo"] is None and record["hnlo_status"] == HNLO_STATUS, "RECORD_BINDING")
            sample = f"samples/{row['ordinal']:06d}/"
            native = prefix + sample + "native_call.json" in members
            require(type(record["native_calls"]) is int and record["native_calls"] == int(native), "CALL_ACCOUNTING")
            calls += int(native)
            started = prefix + sample + "started.json" in members
            require(type(record["attempts"]) is int and record["attempts"] == int(started)
                and (not native or started), "ATTEMPT_ACCOUNTING")
            if started:
                require(row["ordinal"] in expected_plan["scheduled_ordinals"]
                    and get(sample + "started.json") == {"row": row, "plan_sha256": plan_sha}, "SCHEDULED_START")
            if record["status"] in ("TECHNICAL_ERROR", "NOT_ATTEMPTED"):
                require(record["label"] is None, "ERROR_PENDING_HAS_LABEL")
            if record["status"] == "NOT_ATTEMPTED":
                require(not started and not native, "NOT_ATTEMPTED_WITH_MARKER")
            if record["status"] in ("SUCCESS", "INVALID"):
                raw = get(sample + "raw.json")
                label = parse_label(raw["response"])
                expected_binding = trace_binding(spec, expected_plan, row, raw["binding"]["tokenizer_sha256"], plan_sha)
                require(native and record["raw_sha256"] == members[prefix + sample + "raw.json"]
                    and raw["binding"] == expected_binding and raw["hnlo"] is None
                    and raw["hnlo_status"] == HNLO_STATUS
                    and get(sample + "native_call.json")["binding"] == expected_binding
                    and record["label"] == label
                    and record["status"] == ("SUCCESS" if label else "INVALID"), "RAW_BEFORE_PARSE_EVIDENCE")
                require((record["trace_verified"] is True and prefix + sample + "trace-verification.json" in members)
                    or (label is None and prefix + sample + "trace-failure.json" in members), "TRACE_RECEIPT_REQUIRED")
                if cohort["scope"] != "SYNTHETIC_ONLY":
                    require(raw["evidence_kind"] == "NATIVE" and raw["capture_origin"] == "forward_before_processors",
                        "NATIVE_CAPTURE_REQUIRED")
                    if label:
                        trace = get(sample + "trace-verification.json")
                        require(trace["status"] == "TRACE_CONSISTENT" and trace["evidence_kind"] == "NATIVE"
                            and trace["label"] == label and trace["binding"] == expected_binding, "POSITIVE_NATIVE_TRACE")
                        verify_numeric_members(z, prefix + sample, raw, members)
                    else:
                        verify_retained_raw_vectors(z, prefix + sample, raw, members)
        require(calls == result["model_calls"] <= expected_plan["max_calls"]
            and result["counts"] == dict(Counter(r["status"] for r in result["records"])), "COUNTS")
        require(not result["counts"].get("TECHNICAL_ERROR") or result["status"] == "FAIL", "TECHNICAL_ERROR_CANNOT_PASS")
    return {"status": result["status"], "archive_sha256": expected_sha, "members": len(members) + 1,
        "model_calls": calls, "counts": result["counts"], "scope": result["scope"],
        "scientific_qualified": False}


def verify_retained_raw_vectors(archive, prefix, raw, members):
    """Verify full-vocab .f32/masked/forward custody even on INVALID native outputs."""
    import json
    import math
    import struct
    from safeshift.internvl_grammar import PROCESSOR
    ids, width = raw["generated_ids"], raw["logit_width"]
    raw_hashes, masked_hashes = raw.get("raw_vector_hashes"), raw.get("masked_vector_hashes")
    require(type(width) is int and 0 < width <= 200000 and isinstance(ids, list)
        and isinstance(raw_hashes, list) and isinstance(masked_hashes, list)
        and 1 <= len(raw_hashes) == len(masked_hashes) <= 64 and len(ids) == len(raw_hashes)
        and raw.get("actual_logits_processors") == [PROCESSOR] and raw.get("policy") == POLICY,
        "NATIVE_INVALID_RAW_VECTOR_CUSTODY")
    for index, (raw_sha, masked_sha) in enumerate(zip(raw_hashes, masked_hashes)):
        stem = prefix + f"steps/{index:03d}"
        require(members.get(stem + ".f32") == raw_sha and members.get(stem + ".masked.json") == masked_sha
            and (stem + ".forward.json") in members, "NATIVE_INVALID_VECTOR_MEMBER_HASH")
        binary = archive.read(stem + ".f32")
        require(len(binary) == width * 4, "FULL_VOCAB_BINARY_SIZE")
        vector = struct.unpack("<" + "f" * width, binary)
        require(all(math.isfinite(x) for x in vector), "NONFINITE_NATIVE_RAW")
        masked = _strict_json_loads(archive.read(stem + ".masked.json"))
        forward = _strict_json_loads(archive.read(stem + ".forward.json"))
        require(masked["step"] == index and masked["raw_sha256"] == raw_sha
            and forward["step"] == index and forward["raw_sha256"] == raw_sha
            and forward["vocab"] == width and forward["origin"] == "forward_before_processors"
            and forward["encoding"] == "float32-little-endian" and forward["all_finite"] is True,
            "NATIVE_INVALID_STEP_CUSTODY")


def verify_numeric_members(archive, prefix, raw, members):
    """Stdlib full-vector readback; no model/tokenizer, label repair or HNLO.

    Worker already performed approved tokenizer/independent decoder replay. This
    separately verifies every retained vector/hash/prefix/mask/greedy choice.
    """
    import math
    import struct
    from safeshift.internvl_grammar import PROCESSOR, greedy_token
    ids, width = raw["generated_ids"], raw["logit_width"]
    require(type(width) is int and 0 < width <= 200000 and 1 <= len(ids) <= 64
        and len(ids) == len(raw["raw_vector_hashes"]) == len(raw["masked_vector_hashes"])
        and raw["actual_logits_processors"] == [PROCESSOR] and raw["policy"] == POLICY,
        "NATIVE_TRACE_DIMENSION_POLICY")
    for index, token in enumerate(ids):
        stem = prefix + f"steps/{index:03d}"
        require(members.get(stem + ".f32") == raw["raw_vector_hashes"][index]
            and members.get(stem + ".masked.json") == raw["masked_vector_hashes"][index],
            "NATIVE_VECTOR_MEMBER_HASH")
        binary = archive.read(stem + ".f32")
        require(len(binary) == width * 4, "FULL_VOCAB_BINARY_SIZE")
        vector = struct.unpack("<" + "f" * width, binary)
        require(all(math.isfinite(x) for x in vector), "NONFINITE_NATIVE_RAW")
        masked = _strict_json_loads(archive.read(stem + ".masked.json"))
        forward = _strict_json_loads(archive.read(stem + ".forward.json"))
        require(masked["step"] == index and masked["prefix_ids"] == raw["input_ids"] + ids[:index]
            and masked["raw_sha256"] == raw["raw_vector_hashes"][index]
            and forward["step"] == index and forward["raw_sha256"] == raw["raw_vector_hashes"][index]
            and forward["vocab"] == width and forward["origin"] == "forward_before_processors"
            and forward["encoding"] == "float32-little-endian" and forward["all_finite"] is True,
            "NATIVE_VECTOR_STEP_CUSTODY")
        scores = masked["masked_logits"]
        require(len(scores) == width and all(x is None or (type(x) in (int, float)
            and math.isfinite(x) and x == vector[i]) for i, x in enumerate(scores))
            and sum(x is not None for x in scores) <= 4 and greedy_token(scores) == token,
            "NATIVE_MASK_OR_GREEDY_DRIFT")


def sealed_history(archive, expected_sha, expected_plan):
    """Import only an exact selected attempt; callers retain the entire chain.

    This is custody, never result selection or permission to resume/repair.
    """
    import zipfile
    verify_bundle(archive, expected_sha, expected_plan)
    with zipfile.ZipFile(archive) as z:
        name = "summary.json" if "summary.json" in z.namelist() else "run/summary.json"
        result = _strict_json_loads(z.read(name))
    from safeshift.internvl3763_campaign import PLAN as CAMPAIGN_PLAN
    records = result["records"]
    if expected_plan["schema"] == CAMPAIGN_PLAN:
        # Archived summary always contains3763 rows. The checked scheduling
        # projection retains only consumed records, avoiding repeated pending
        # rows in every later Input; absence means NOT_ATTEMPTED, never dropped GT.
        records = [row for row in records if row["status"] != "NOT_ATTEMPTED"]
    return {"run_id": expected_plan["run_id"], "attempt_id": expected_plan["attempt_id"],
        "series_id": SERIES, "identity": expected_plan["identity"], "cohort_sha256": expected_plan["cohort_sha256"],
        "parent_history_sha256": expected_plan["history_sha256"], "action": expected_plan["action"],
        "records": records, "evidence_sha256": expected_sha, "repair": expected_plan["repair"]}
