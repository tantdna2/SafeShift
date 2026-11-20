"""Shared native controller; MiniCPM V2 uses authenticated bounded capabilities.

The CPU rehearsal uses the SAME per-call controller with exact public byte
fixtures. Adapters are injected only by tests; no fake backend ships here.
"""
from pathlib import Path
import time

from safeshift.candidates import fulltrain_run as journal
from safeshift.candidates.train_history import lease_key
from safeshift.candidates.source import require, ROOT, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha, write, export
from safeshift.pilot.contract import digest
from safeshift.pilot.runner import execute, error_record
from . import contract, memory


def native_factory(key, snapshot, weights, *, repo=ROOT):
    """Prepared native binding, deliberately behind the same release fence."""
    contract.authorize()
    return _native_factory(key, snapshot, weights, repo=repo)


def _native_factory(key, snapshot, weights, *, repo=ROOT):
    # Internal native binding; activated MiniCPM requires its one-load claim.
    from .minicpm_release import current
    if current() is not None:
        require(key == "minicpm4", "MINICPM_CAPABILITY_CANNOT_OPEN_PEERS")
        contract.authorize("load")
    from safeshift.candidates.source import verify_snapshot
    from safeshift.candidates.loading import verify_weights
    from safeshift.pilot.contract import PROMPT_SHA
    from safeshift.candidates.backend import CandidateBackend
    from safeshift.candidates import minicpm_resampler_fp32 as numerical
    if key == "qwen3":
        from .qwen import QwenBackend
        require(Path(snapshot) == Path(weights), "QWEN_ONE_SEALED_SNAPSHOT")
        return QwenBackend(snapshot, repo=repo)
    require(key in ("internvl35", "minicpm4"), "NATIVE_MODEL_KEY")
    prompt = Path(repo) / "configs/pilot/classification_c1.txt"
    require(sha(prompt) == PROMPT_SHA, "FROZEN_C1_SHA")
    verify_snapshot(snapshot, key)
    if key == "minicpm4":
        # load_weight_model verifies both shards at deserialization in load_guard.
        return numerical.backend(key, Path(snapshot), Path(weights), prompt.read_text(encoding="utf-8"), device="cuda:0")
    verify_weights(weights, key)
    return CandidateBackend(key, Path(snapshot), Path(weights), prompt.read_text(encoding="utf-8"), device="cuda:0")


def _image_cache_advice(path, deadline):
    """Advise only within the worker budget, after native evidence is durable."""
    if time.monotonic() < deadline:
        try:
            return {"status": "RETURNED", **memory.evict_readonly_file(path, deadline=deadline)}
        except (OSError, ValueError) as error:
            if not (isinstance(error, ValueError) and str(error) == "READONLY_ADVICE_DEADLINE"):
                return {"status": "FAILED", "failure": error_record(error, "image-cache-advice")}
    return {"status": "DEADLINE"}


class NativeStore(journal.BoundStore):
    """Persist received raw first, then check native/config/numerical custody."""
    def raw(self, ordinal, record):
        checksum = super().raw(ordinal, record)
        validate_native_raw(self.root / f"samples/{ordinal:06d}", record, self.identity["execution_identity"])
        return checksum


def validate_native_raw(sample, record, spec):
    if spec["model_key"] == "qwen3":
        from .qwen import validate_raw
        return validate_raw(sample, record, spec)
    from safeshift.candidates.train_run import native_custody, validate_native_configuration
    native_custody(sample, record)
    d = contract.descriptor(spec["model_key"])
    require(digest(d) == spec["configuration_sha256"], "FRESH_NATIVE_CONFIGURATION_DRIFT")
    validate_native_configuration(sample, {"configuration_contract": d})
    require(record["logit_capture_boundary"] == d["effective_candidate"]["logits"]["boundary"],
            "FRESH_LOGIT_BOUNDARY")


def check_repair_case(p, repair_case):
    if p["action"] == "repair":
        require(type(repair_case) is dict and set(repair_case) ==
                {"plan_sha256", "cause_evidence_sha256", "fix_sha256", "regression_sha256"}, "REPAIR_CAUSE_EVIDENCE_REQUIRED")
        for value in repair_case.values():
            contract.require_hash(value)
        require(repair_case["plan_sha256"] == digest(p)
                and all(repair_case[n] == p["repair"][n] for n in ("fix_sha256", "regression_sha256")),
                "REPAIR_CASE_BINDING")
    else:
        require(repair_case is None, "REPAIR_CASE_ON_WRONG_ACTION")


def recover(root, cohort, plan_sha):
    """Fresh campaign and native custody on top of the unchanged journal reader.

    A torn native raw is not promoted just because it parses. Native evidence
    must also verify; otherwise recovery blocks and preserves all original bytes.
    """
    root = Path(root)
    spec = read(root / "plan.json")["identity"]
    if spec["model_key"] == "qwen3" and not spec["model_id"].startswith("synthetic/"):
        from .engine import recover as qwen_recover
        from .qwen import parser
        h = qwen_recover(root, cohort, plan_sha, label_parser=parser)
    else:
        h = journal.recover(root, cohort, plan_sha)
    p, campaign = read(root / "plan.json"), read(root / "campaign.json")
    require(p == contract.plan(campaign, cohort, p["identity"], read(root / "history.json"),
        action=p["action"], run_id=p["run_id"], attempt_id=p["attempt_id"],
        max_calls=p["max_calls"], max_seconds=p["max_seconds"], repair=p["repair"]), "FRESH_RECOVERY_PLAN")
    repair_path = root / "repair_case.json"
    check_repair_case(p, read(repair_path) if repair_path.exists() else None)
    if cohort["scope"] != "SYNTHETIC_ONLY":
        for i in p["scheduled_ordinals"]:
            sample = root / f"calls/{i:06d}/run/samples/000000"
            if (sample / "raw.json").exists():
                validate_native_raw(sample, read(sample / "raw.json"), p["identity"])
    return h


def worker(request, **kwargs):
    # Must precede keyword validation, Path conversion, or heavy imports.
    contract.authorize(request=request)
    require(set(kwargs) <= {"repo", "memory_output"}, "UNSUPPORTED_WORKER_OPTIONS")
    return _worker(request, **kwargs)


def _worker(request, *, repo=ROOT, memory_output=None, stage_deadline=None, admitted_checkpoint=None):
    """Prepared peer native chain; never called by this release's public worker.

    Requires an already provisioned isolated pinned worker. Future activation
    must bind the request/caps to externally reviewed O2-O6 and a supervisor
    deadline; this function does not authenticate an approval document.
    """
    from .minicpm_release import current
    if current() is not None:
        contract.authorize(request=request)
    from .inputs import admit, verify_image_bytes
    from safeshift.candidates.train_inputs import checkpoint
    from safeshift.candidates.train_runtime import software, worker_cuda, resources, verify_images
    from safeshift.candidates.source import verify_snapshot
    from safeshift.candidates.loading import verify_weights
    from safeshift.pilot.hnlo import replay
    required = {"model_key", "source_sha256", "inputs", "marker_sha256", "projection_sha256",
                "campaign", "plan", "history", "work", "scratch", "resource_policy", "repair_case"}
    from .admission import REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS, UI_REQUEST_FIELDS, checkpoint_binding, input_binding
    supervised = (REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS, UI_REQUEST_FIELDS)
    require(type(request) is dict and set(request) in (required, *supervised), "EXACT_NATIVE_REQUEST")
    key = request["model_key"]
    require(key != "qwen3" or set(request) == REQUEST_FIELDS, "QWEN_SUPERVISED_REQUEST_REQUIRED")
    require(digest(contract.source_manifest(repo)) == request["source_sha256"], "FINAL_NATIVE_SOURCE")
    require(request["plan"]["identity"] == contract.native_identity(key, repo), "PINNED_NATIVE_IDENTITY")
    original_stage = None
    if "original_inputs" in request:
        require(admitted_checkpoint is None, "ORIGINAL_STAGE_CHECKPOINT_OVERRIDE")
        from .admission import _current_original_stage, validate_request
        original_stage = _current_original_stage("native", request, repo, stage_deadline)
        if original_stage is None:
            # Independent entry still checks the original binding and all image bytes.
            validate_request(request, repo)
            bundle, cohort, rows = input_binding(request, deadline=stage_deadline)
        else:
            (bundle, cohort, rows, snapshot, weights, _), verified_files = original_stage
    else:
        bundle, cohort, rows = admit(request["inputs"], request["marker_sha256"], request["projection_sha256"])
        verify_image_bytes(bundle, cohort, rows)
    if key == "qwen3":
        from . import qwen, environment
        from .admission import checkpoint_binding
        _, snapshot, weights, _ = checkpoint_binding(request, repo)
        environment.software(key, repo, request["runtime_lock"])
        qwen.native_setup(snapshot, repo)
        replay = qwen.replay
    elif original_stage is None:
        if admitted_checkpoint is not None:
            require(key == 'minicpm4' and set(request) in supervised, 'MINICPM_STAGE_CHECKPOINT_ONLY')
            snapshot, weights = admitted_checkpoint
        elif set(request) in supervised:
            _, snapshot, weights, _ = checkpoint_binding(request, repo, deadline=stage_deadline)
        else:
            _, snapshot, weights = checkpoint(request["inputs"], key)
        if key != "minicpm4" or set(request) not in supervised:
            verify_snapshot(snapshot, key)
            if key == "minicpm4":
                verify_weights(weights, key, hash_reader=memory.stream_readonly_sha256)
            else:
                verify_weights(weights, key)
    if key != "qwen3":
        software(key)  # actual isolated Python/pins/compiled ABI, no kernel fallback
    if original_stage is not None:
        from .original_inputs import _decode_files
        _decode_files(verified_files, deadline=stage_deadline)
    elif "original_inputs" in request:
        from .original_inputs import verify_images as original_images
        original_images(bundle, cohort, rows, deadline=stage_deadline)
    else:
        verify_images(bundle, rows)
    policy = request["resource_policy"]
    require(policy.get("review_mode") == "EXTERNAL", "NO_CANDIDATE160_OWNER_CAP_INHERITANCE")
    supervised_minicpm = key == 'minicpm4' and set(request) in supervised
    if key == "qwen3":
        environment.hardware(key, policy)
        environment.cuda(key, policy)
    elif not supervised_minicpm:
        worker_cuda(policy)
    resource_index = 0
    memory_out = None
    driver = None
    model_loaded = False
    if supervised_minicpm:
        require(memory_output is not None, 'SUPERVISED_NATIVE_MEMORY_OUTPUT_REQUIRED')
        memory_out = Path(memory_output)
        memory_out.mkdir(exist_ok=False)
        # The clean worker has no loader path: bind the mounted host driver and
        # scope NVML to nvidia-smi, as in the successful InternVL worker.
        from . import environment, gpu_driver
        driver = gpu_driver.bind(memory_out)
    def check_resources():
        nonlocal resource_index
        if set(request) in supervised:
            from . import environment
            label = f'pre-call-{resource_index:06d}'
            if memory_out is not None:
                memory.resource_check(request, memory_out, label)
                resource_index += 1
            else:
                environment.resources(key, policy, request["scratch"], request["work"])
            if driver is None:
                environment.hardware(key, policy)
                environment.cuda(key, policy)
            elif model_loaded and current() and "resident_gpu0_min_free_mib" in current()["grant"].get("offline", {}):
                floor = current()["grant"]["offline"]["resident_gpu0_min_free_mib"]
                write(memory_out / (label + '-loaded-gpu.json'), gpu_driver.loaded(key, policy, driver, memory_out, label, floor))
            else:
                write(memory_out / (label + '-physical-gpu.json'), gpu_driver.hardware(key, policy, driver, memory_out, label))
                write(memory_out / (label + '-worker-cuda.json'), environment.cuda(key, policy))
        else:
            resources(policy, request["scratch"], request["work"], gpu=True)
    check_resources()
    def factory():
        nonlocal model_loaded
        if memory_out is not None:
            with memory.load_guard(request, memory_out.parent, deadline=stage_deadline):
                backend = _native_factory(key, snapshot, weights, repo=repo)
            model_loaded = True
            return backend
        return _native_factory(key, snapshot, weights, repo=repo)
    return _execute(request["work"], bundle, cohort, request["campaign"], request["plan"], request["history"],
        factory,
        image_path=lambda i: rows[i]["image"], evaluator=None if key == "minicpm4" else replay,
        before_call=check_resources, repair_case=request["repair_case"], stage_deadline=stage_deadline,
        stage_request=(request, repo) if original_stage is not None else None)


def launch(*args, **kwargs):
    contract.authorize(request=args[0] if args else kwargs.get("request"))
    from .admission import launch_prepared
    return launch_prepared(*args, **kwargs)


def worker_command(python, request, output):
    return [str(python), "-B", "-m", "safeshift.fulltrain.runtime",
            "--request", str(request), "--output", str(output)]


def _execute(work, bundle, cohort, campaign, p, history, factory, *, image_path,
             store_class=NativeStore, evaluator=None, before_call=None, repair_case=None, clock=time.monotonic,
             stage_deadline=None, stage_request=None):
    """Shared bounded controller; requires pre-admitted inputs and explicit plan.

    Internal only, not an execution authority. Public real-data entries are
    closed. Future activation must supply admission and live resource checks.
    """
    require(p == contract.plan(campaign, cohort, p["identity"], history, action=p["action"],
        run_id=p["run_id"], attempt_id=p["attempt_id"], max_calls=p["max_calls"],
        max_seconds=p["max_seconds"], repair=p["repair"]), "FRESH_PLAN_CHANGED")
    require(p["run_id"] not in ("attempts", "campaign.json"), "RESERVED_RUN_NAME")
    check_repair_case(p, repair_case)
    from . import minicpm_release as capability
    active = capability.current()
    adaptive = None
    if active is not None:
        require(digest(p) == digest(active["value"]["request"]["plan"]), "MINICPM_ACTIVE_PLAN")
        from .minicpm_sizing import CallBudget
        started = read(active["claims"] / "launch.json")["time_unix"]
        adaptive = CallBudget(clock() + max(0, started + p["max_seconds"] - time.time()), active["grant"]["sizing"], clock=clock)
    if p["identity"]["hnlo_policy"] == "LABEL_ONLY":
        require(evaluator is None, "LABEL_ONLY_MUST_NOT_REOPEN_HNLO")
        evaluator = journal.label_only
    else:
        require(callable(evaluator), "LOCKED_HNLO_REQUIRED")
    work, bundle = Path(work), Path(bundle)
    verified_files = None
    if stage_request is not None:
        from .admission import _current_original_stage
        request, repo = stage_request
        admitted = _current_original_stage("native", request, repo, stage_deadline)
        require(admitted is not None and p is request["plan"]
                and cohort is admitted[0][1] and bundle == admitted[0][0], "ORIGINAL_STAGE_EXECUTION_BINDING")
        verified_files = admitted[1]
    work.mkdir(parents=True, exist_ok=True)
    lock = digest({"campaign": campaign, "model": p["identity"]["model_key"]})
    with lease_key(work, lock):
        campaign_file = work / "campaign.json"
        if campaign_file.exists():
            require(read(campaign_file) == campaign, "WORKSPACE_CAMPAIGN_CHANGED")
        else:
            require(not history, "FRESH_WORKSPACE_REQUIRES_EXPLICIT_HISTORY_IMPORT")
            write(campaign_file, campaign)
        for h in history:
            prior = safe(work, h["run_id"])
            require(read(prior / "campaign.json") == campaign, "FOREIGN_CAMPAIGN_HISTORY")
            require(recover(prior, cohort, digest(read(prior / "plan.json"))) == h,
                    "HISTORY_EVIDENCE_CHANGED")
        # Refuse omitted partial/reserved attempts even if caller supplies a
        # plausible complete subset of the history. No implicit retry after kill.
        reservations = work / "attempts"
        known = {h["attempt_id"] + ".json" for h in history}
        if reservations.exists():
            require({v.name for v in reservations.iterdir()} == known | {"active_" + lock + ".lock"},
                    "UNRECONCILED_RESERVATION")
            for h in history:
                require(read(reservations / (h["attempt_id"] + ".json"))["plan_sha256"]
                        == digest(read(work / h["run_id"] / "plan.json")), "RESERVATION_PLAN_CHANGED")
        elif history:
            raise ValueError("IMPORTED_HISTORY_RESERVATIONS_REQUIRED")
        root = safe(work, p["run_id"])
        require(not root.exists() and not Path(str(root) + ".zip").exists(), "RUN_ALREADY_EXISTS")
        def image_hash(path):
            if p["identity"]["model_key"] == "minicpm4":
                return memory.stream_readonly_sha256(path, deadline=stage_deadline)
            return sha(path)

        for i in p["scheduled_ordinals"]:
            path = safe(bundle, image_path(i))
            if verified_files is None:
                require(image_hash(path) == cohort["samples"][i]["image_sha256"], "INPUT_CHECKSUM")
            else:
                expected_path, expected_identity = verified_files[i]
                memory.check_deadline(stage_deadline)
                require(path == expected_path and memory.identity(snapshot_stat(path)) == expected_identity,
                        "ORIGINAL_IMAGE_CHANGED_BEFORE_RESERVATION")
        write(work / "attempts" / (p["attempt_id"] + ".json"), {"plan_sha256": digest(p), "campaign_sha256": digest(campaign)})
        root.mkdir()
        write(root / "campaign.json", campaign)
        write(root / "plan.json", p)
        write(root / "history.json", history)
        if active is not None:
            write(root / "capability.json", {"locator": active["locator"], "ticket": active["ticket"]})
        if repair_case is not None:
            write(root / "repair_case.json", repair_case)
        backend, stop, count = None, None, 0
        deadline = clock() + p["max_seconds"]
        try:
            for i in p["scheduled_ordinals"]:
                if adaptive is not None and not adaptive.can_start():
                    stop = "ADAPTIVE_TIME_STOP"
                    break
                if clock() >= deadline:
                    stop = "TIME_CAP"
                    break
                if before_call is not None:
                    try:
                        before_call()
                    except ValueError as error:
                        if active is not None and str(error) in ("SHARED_DISK_RESERVES", "SEPARATE_DISK_RESERVES"):
                            stop = "ADAPTIVE_STORAGE_STOP"
                            break
                        raise
                if active is not None and backend is None:
                    # Load once under its permanent claim, then reassess actual
                    # time *before* creating a sample start/native-call marker.
                    write(root / "model_load.json", {"load_attempts": 1})
                    backend = factory()
                    if before_call is not None:
                        before_call()  # model load/processor/hash churn cannot inherit an earlier PASS
                    if not adaptive.can_start():
                        stop = "ADAPTIVE_TIME_STOP"
                        break
                row = {**cohort["samples"][i], "image": str(safe(bundle, image_path(i)))}
                require(image_hash(row["image"]) == row["image_sha256"], "INPUT_CHANGED_BEFORE_CALL")
                store = store_class(root / f"calls/{i:06d}/run", journal._identity(p, row))
                def cached():
                    nonlocal backend
                    if backend is None:
                        write(root / "model_load.json", {"load_attempts": 1})
                        backend = factory()
                    return capability.GuardedBackend(backend, i) if active is not None else backend
                call_started = clock()
                engine, options = execute, {}
                if p["identity"]["model_key"] == "qwen3" and not p["identity"]["model_id"].startswith("synthetic/"):
                    from .engine import execute as engine
                    from .qwen import parser
                    options["label_parser"] = parser
                call_deadline = deadline if adaptive is None else adaptive.deadline - adaptive.policy["export_seconds"]
                native_seconds = max(0, call_deadline - clock())
                result, blocked = engine(store, [row], cached,
                    {"run_id": p["run_id"], "attempt_id": p["attempt_id"]}, p["identity"]["model_key"], cohort,
                    time_budget=native_seconds, transport=journal._identity(p, row)["transport"],
                    hnlo_replay=evaluator, **options)
                if blocked and result[row["sample_id"]]["status"] == "NOT_ATTEMPTED":
                    reason = read(store.root / "stop.json")["reason"] if (store.root / "stop.json").exists() else None
                    if reason in ("TIME_BUDGET_STOP_BEFORE_NEXT_CALL", "OUTPUT_FREE_BELOW_1GIB_KEEP_EXPORT_RESERVE") \
                            and not (store.root / "samples/000000/started.json").exists():
                        if active is not None:
                            stop = "ADAPTIVE_TIME_STOP" if reason.startswith("TIME_") else "ADAPTIVE_STORAGE_STOP"
                        else:
                            stop = "TIME_CAP" if reason.startswith("TIME_") else "TECHNICAL_STOP"
                        break
                count += result[row["sample_id"]]["native_calls"]
                if adaptive is not None:
                    adaptive.observed(clock() - call_started)
                require(count <= p["max_calls"], "CALL_CAP")
                write(root / f"checkpoints/{i:06d}.json", {"result_sha256": digest(result), "native_calls": count})
                advice_status = None
                if p["identity"]["model_key"] == "minicpm4" and (store.root / "samples/000000/started.json").exists():
                    # The engine has already persisted raw/result or the original failure.
                    # Keep fadvise inside the hard-supervised stage and the call budget.
                    advice_deadline = time.monotonic() + max(0, call_deadline - clock())
                    if stage_deadline is not None:
                        advice_deadline = min(advice_deadline, stage_deadline)
                    advice = _image_cache_advice(row["image"], advice_deadline)
                    write(store.root / "image-cache-advice.json", advice)
                    advice_status = advice["status"]
                if blocked:
                    stop = "TECHNICAL_STOP"
                    break
                if advice_status == "FAILED":
                    stop = "IMAGE_CACHE_ADVICE_FAILURE"
                    break
                if advice_status == "DEADLINE":
                    stop = "TIME_CAP" if adaptive is None else "ADAPTIVE_TIME_STOP"
                    break
        except BaseException as error:
            stop = "CONTROLLER_FAILURE"
            write(root / "failure.json", error_record(error, "pipeline"))
            raise
        finally:
            observed = sum((root / f"calls/{i:06d}/run/samples/000000/native_call.json").is_file()
                           for i in p["scheduled_ordinals"])
            write(root / "receipt.json", {"native_calls": count, "load_attempts": int((root / "model_load.json").exists()),
                "observed_native_markers": observed,
                "loads": int(backend is not None), "stop": stop, "planned_ids": 3763,
                "scope": cohort["scope"], "scientific_selection": "PENDING", "pooling_allowed": False})
            if active is not None:
                write(root / "claims.json", capability.claims_snapshot())
                write(root / "timing.json", {"model_key": "minicpm4", "source_sha256": p["identity"]["implementation_sha256"],
                    "call_seconds": adaptive.timings, "overhead_seconds": max(0.001, time.time() - started - sum(adaptive.timings)),
                    "observed_complete_calls": len(adaptive.timings), "population_bound": False})
            try:
                # An accounting projection never chooses scientific outputs.
                h = recover(root, cohort, digest(p))
                current = {r["sample_id"]: {"status": r["status"], "ordinal": r["ordinal"], "sample_id": r["sample_id"]}
                           for r in p["samples"]}
                for r in h["records"]:
                    if r["status"] != "NOT_ATTEMPTED":
                        current[r["sample_id"]]["status"] = r["status"]
                write(root / "accounting.json", {"planned_ids": 3763, "samples": list(current.values()),
                    "scientific_selection": "PENDING", "pooling_allowed": False})
            except Exception as error:
                write(root / "accounting_failure.json", error_record(error, "reconciliation"))
            export(root, Path(str(root) + ".zip"))
        return root


def rehearse(work, bundle, cohort, campaign, p, history, factory, **kwargs):
    require(cohort == journal.synthetic_cohort(), "CPU_SYNTHETIC_FIXTURE_ONLY")
    require(p["identity"]["model_id"] == "synthetic/" + p["identity"]["model_key"], "SYNTHETIC_MODEL_REQUIRED")
    require(set(kwargs) <= {"clock", "evaluator", "before_call", "repair_case"}, "NO_REHEARSAL_PATH_OR_STORE_OVERRIDE")
    return _execute(work, bundle, cohort, campaign, p, history, factory,
                    image_path=lambda i: f"{i:06d}.bin", store_class=journal.BoundStore, **kwargs)


def import_history(work, archive, expected_archive_sha, cohort, campaign, plan_sha):
    """Import one explicitly selected sealed attempt; no auto-discovery of outputs."""
    from safeshift.pilot.artifacts import verify_archive, import_archive
    require(sha(archive) == expected_archive_sha, "OUTER_ARCHIVE_CHECKSUM")
    entries = verify_archive(archive)
    require("campaign.json" in entries, "NO_LEGACY_HISTORY_IMPORT")
    # Validate before installing an immutable directory (including campaign and
    # complete prior chain). A rejected archive never becomes admissible history.
    import tempfile
    with tempfile.TemporaryDirectory() as temporary:
        stage = import_archive(archive, Path(temporary) / "attempt")
        require(read(stage / "campaign.json") == campaign, "FOREIGN_CAMPAIGN_HISTORY")
        h = recover(stage, cohort, plan_sha)
        p = read(stage / "plan.json")
        contract.plan(campaign, cohort, p["identity"], read(stage / "history.json"), action=p["action"],
            run_id=p["run_id"], attempt_id=p["attempt_id"], max_calls=p["max_calls"], max_seconds=p["max_seconds"], repair=p["repair"])
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    with lease_key(work, digest({"campaign": campaign, "model": h["identity"]["model_key"]})):
        cf = work / "campaign.json"
        if cf.exists():
            require(read(cf) == campaign, "WORKSPACE_CAMPAIGN_CHANGED")
        else:
            write(cf, campaign)
        target = safe(work, h["run_id"])
        reservation = safe(work, "attempts/" + h["attempt_id"] + ".json")
        require(not target.exists() and not reservation.exists(), "HISTORY_IMPORT_NO_OVERWRITE")
        write(reservation, {"plan_sha256": plan_sha, "campaign_sha256": digest(campaign)})
        installed = import_archive(archive, target)
        require(sha(archive) == expected_archive_sha and recover(installed, cohort, plan_sha) == h,
                "HISTORY_CHANGED_DURING_IMPORT")
        return h


if __name__ == "__main__":
    worker(None)  # No argument can bypass the release fence.
