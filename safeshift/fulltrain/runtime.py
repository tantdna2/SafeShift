"""Fresh native orchestration preparation; public worker/launch remain fenced.

The CPU rehearsal uses the SAME per-call controller with exact public byte
fixtures. Adapters are injected only by tests; no fake backend ships here.
"""
from pathlib import Path
import time

from safeshift.candidates import fulltrain_run as journal
from safeshift.candidates.train_history import lease_key
from safeshift.candidates.source import require, ROOT
from safeshift.pilot.artifacts import read, safe, sha, write, export
from safeshift.pilot.contract import digest
from safeshift.pilot.runner import execute, error_record
from . import contract


def native_factory(key, snapshot, weights, *, repo=ROOT):
    """Prepared native binding, deliberately behind the same release fence."""
    contract.authorize()
    return _native_factory(key, snapshot, weights, repo=repo)


def _native_factory(key, snapshot, weights, *, repo=ROOT):
    # Internal composition point for a future separately reviewed activation.
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
    verify_weights(weights, key)
    if key == "minicpm4":
        return numerical.backend(key, Path(snapshot), Path(weights), prompt.read_text(encoding="utf-8"), device="cuda:0")
    return CandidateBackend(key, Path(snapshot), Path(weights), prompt.read_text(encoding="utf-8"), device="cuda:0")


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
    # Must precede even Path conversion, directory creation or heavy imports.
    contract.authorize()
    return _worker(request, **kwargs)


def _worker(request, *, repo=ROOT):
    """Prepared peer native chain; never called by this release's public worker.

    Requires an already provisioned isolated pinned worker. Future activation
    must bind the request/caps to externally reviewed O2-O6 and a supervisor
    deadline; this function does not authenticate an approval document.
    """
    from .inputs import admit, verify_image_bytes
    from safeshift.candidates.train_inputs import checkpoint
    from safeshift.candidates.train_runtime import software, worker_cuda, resources, verify_images
    from safeshift.candidates.source import verify_snapshot
    from safeshift.candidates.loading import verify_weights
    from safeshift.pilot.hnlo import replay
    required = {"model_key", "source_sha256", "inputs", "marker_sha256", "projection_sha256",
                "campaign", "plan", "history", "work", "scratch", "resource_policy", "repair_case"}
    from .admission import REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS, checkpoint_binding, input_binding, input_bytes
    require(type(request) is dict and set(request) in (required, REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS), "EXACT_NATIVE_REQUEST")
    key = request["model_key"]
    require(key != "qwen3" or set(request) == REQUEST_FIELDS, "QWEN_SUPERVISED_REQUEST_REQUIRED")
    require(digest(contract.source_manifest(repo)) == request["source_sha256"], "FINAL_NATIVE_SOURCE")
    require(request["plan"]["identity"] == contract.native_identity(key, repo), "PINNED_NATIVE_IDENTITY")
    if "original_inputs" in request:
        # Direct internal entry must enforce the same binding/model validation.
        from .admission import validate_request
        validate_request(request, repo)
        bundle, cohort, rows = input_binding(request)
        input_bytes(request, bundle, cohort, rows)
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
    else:
        if set(request) in (REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS):
            _, snapshot, weights, _ = checkpoint_binding(request, repo)
        else:
            _, snapshot, weights = checkpoint(request["inputs"], key)
        verify_snapshot(snapshot, key)
        verify_weights(weights, key)
        software(key)  # actual isolated Python/pins/compiled ABI, no kernel fallback
    if "original_inputs" in request:
        from .original_inputs import verify_images as original_images
        original_images(bundle, cohort, rows)
    else:
        verify_images(bundle, rows)
    policy = request["resource_policy"]
    require(policy.get("review_mode") == "EXTERNAL", "NO_CANDIDATE160_OWNER_CAP_INHERITANCE")
    if key == "qwen3":
        environment.hardware(key, policy)
        environment.cuda(key, policy)
    else:
        worker_cuda(policy)
    def check_resources():
        if set(request) in (REQUEST_FIELDS, ORIGINAL_REQUEST_FIELDS):
            from . import environment
            environment.resources(key, policy, request["scratch"], request["work"])
            environment.hardware(key, policy)
            environment.cuda(key, policy)
        else:
            resources(policy, request["scratch"], request["work"], gpu=True)
    check_resources()
    return _execute(request["work"], bundle, cohort, request["campaign"], request["plan"], request["history"],
        lambda: _native_factory(key, snapshot, weights, repo=repo),
        image_path=lambda i: rows[i]["image"], evaluator=None if key == "minicpm4" else replay,
        before_call=check_resources, repair_case=request["repair_case"])


def launch(*args, **kwargs):
    contract.authorize()
    from .admission import launch_prepared
    return launch_prepared(*args, **kwargs)


def worker_command(python, request, output):
    return [str(python), "-B", "-m", "safeshift.fulltrain.runtime",
            "--request", str(request), "--output", str(output)]


def _execute(work, bundle, cohort, campaign, p, history, factory, *, image_path,
             store_class=NativeStore, evaluator=None, before_call=None, repair_case=None, clock=time.monotonic):
    """Shared bounded controller; requires pre-admitted inputs and explicit plan.

    Internal only, not an execution authority. Public real-data entries are
    closed. Future activation must supply admission and live resource checks.
    """
    require(p == contract.plan(campaign, cohort, p["identity"], history, action=p["action"],
        run_id=p["run_id"], attempt_id=p["attempt_id"], max_calls=p["max_calls"],
        max_seconds=p["max_seconds"], repair=p["repair"]), "FRESH_PLAN_CHANGED")
    require(p["run_id"] not in ("attempts", "campaign.json"), "RESERVED_RUN_NAME")
    check_repair_case(p, repair_case)
    if p["identity"]["hnlo_policy"] == "LABEL_ONLY":
        require(evaluator is None, "LABEL_ONLY_MUST_NOT_REOPEN_HNLO")
        evaluator = journal.label_only
    else:
        require(callable(evaluator), "LOCKED_HNLO_REQUIRED")
    work, bundle = Path(work), Path(bundle)
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
        for i in p["scheduled_ordinals"]:
            require(sha(safe(bundle, image_path(i))) == cohort["samples"][i]["image_sha256"], "INPUT_CHECKSUM")
        write(work / "attempts" / (p["attempt_id"] + ".json"), {"plan_sha256": digest(p), "campaign_sha256": digest(campaign)})
        root.mkdir()
        write(root / "campaign.json", campaign)
        write(root / "plan.json", p)
        write(root / "history.json", history)
        if repair_case is not None:
            write(root / "repair_case.json", repair_case)
        backend, stop, count = None, None, 0
        deadline = clock() + p["max_seconds"]
        try:
            for i in p["scheduled_ordinals"]:
                if clock() >= deadline:
                    stop = "TIME_CAP"
                    break
                if before_call is not None:
                    before_call()
                row = {**cohort["samples"][i], "image": str(safe(bundle, image_path(i)))}
                require(sha(row["image"]) == row["image_sha256"], "INPUT_CHANGED_BEFORE_CALL")
                store = store_class(root / f"calls/{i:06d}/run", journal._identity(p, row))
                def cached():
                    nonlocal backend
                    if backend is None:
                        write(root / "model_load.json", {"load_attempts": 1})
                        backend = factory()
                    return backend
                engine, options = execute, {}
                if p["identity"]["model_key"] == "qwen3" and not p["identity"]["model_id"].startswith("synthetic/"):
                    from .engine import execute as engine
                    from .qwen import parser
                    options["label_parser"] = parser
                result, blocked = engine(store, [row], cached,
                    {"run_id": p["run_id"], "attempt_id": p["attempt_id"]}, p["identity"]["model_key"], cohort,
                    time_budget=max(0, deadline - clock()), transport=journal._identity(p, row)["transport"],
                    hnlo_replay=evaluator, **options)
                count += result[row["sample_id"]]["native_calls"]
                require(count <= p["max_calls"], "CALL_CAP")
                write(root / f"checkpoints/{i:06d}.json", {"result_sha256": digest(result), "native_calls": count})
                if blocked:
                    stop = "TECHNICAL_STOP"
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
