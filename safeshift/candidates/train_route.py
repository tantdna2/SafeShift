"""Versioned execution scopes; technical recovery never becomes science approval."""
from .source import require

QUALIFICATION = "train160-production-engineering-v1"
ORDINALS = [0, 15, 111]
DECISION = "https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6540904325"


def fields(implementation=None, qualification=False):
    require(type(qualification) is bool, "QUALIFICATION_BOOLEAN")
    if implementation is not None:
        from .minicpm_resampler_fp32 import ID
        require(implementation == ID, "UNKNOWN_EFFECTIVE_IMPLEMENTATION")
    return {**({"effective_implementation": implementation} if implementation else {}),
            **({"technical_qualification": QUALIFICATION} if qualification else {})}


def options(value):
    qualification = value.get("technical_qualification")
    require(qualification in (None, QUALIFICATION), "UNKNOWN_QUALIFICATION_PROFILE")
    return {"implementation": value.get("effective_implementation"), "qualification": qualification is not None}


def admission(value):
    """An execution record or notebook switch cannot approve a new baseline."""
    opts = options(value)
    fields(**opts)
    if opts["implementation"] and not opts["qualification"]:
        from .train_official import authorize
        authorize(value)


def configuration_admission(key, implementation, qualification=False):
    """Check trusted policy before Inputs; worker admission also checks the record."""
    fields(implementation, qualification)
    if implementation:
        require(key == "minicpm4", "MINICPM_ONLY_NUMERICAL_EXCEPTION")
        if not qualification:
            from .train_official import binding
            binding(key, implementation)


def selection(rows):
    require(len(rows) == 160, "QUALIFICATION_MANIFEST160")
    require(min(range(160), key=lambda i: (rows[i]["width"] * rows[i]["height"], i)) == 15
            and max(range(160), key=lambda i: (rows[i]["height"] / rows[i]["width"], -i)) == 111,
            "PREDECLARED_DIMENSION_CASES_CHANGED")
    return {"profile": QUALIFICATION, "ordinals": ORDINALS,
            "reason": "Original first image, minimum area (first tie), maximum height/width (first tie); chosen before new inference",
            "samples": [{"ordinal": i, **{k: rows[i][k] for k in
                        ("sample_id", "image_sha256", "width", "height")}} for i in ORDINALS],
            "max_native_calls": 3, "scientific_selection": "EXCLUDED", "pooling_allowed": False}


def receipt(output, archive, grant):
    from pathlib import Path
    from safeshift.pilot.artifacts import read, sha, verify_archive
    from . import train_history as history
    from .train_run import recover
    output, archive = Path(output), Path(archive)
    verify_archive(archive)
    require(read(Path(str(archive) + ".sha256.json"))["sha256"] == sha(archive), "QUALIFICATION_SIDECAR")
    require(not (output / "finalizer_errors.json").exists(), "QUALIFICATION_FINALIZER_ERROR")
    status = read(output / "supervisor_status.json")
    require(status["failure"] is None, "QUALIFICATION_SUPERVISOR_FAILURE:" + str(status["failure"]))
    rows = read(output / "pilot_manifest.json")["main"]
    require(read(output / "technical_selection.json") == selection(rows), "QUALIFICATION_SELECTION")
    plan = history.recovery_plan(output, rows, grant)
    results = recover(output, rows, grant)
    attempted = [i for i, r in enumerate(rows) if results[r["sample_id"]]["native_calls"]]
    require(set(attempted) <= set(plan["pending_ordinals"]), "QUALIFICATION_UNPLANNED_CALL")
    if not plan["pending_ordinals"]:
        require(status["status"] == "ALREADY_DURABLE_NO_WORK" and not attempted
                and status["attempt_consumed"] is False and not (output / "model_load_attempt.json").exists(),
                "QUALIFICATION_NOOP_DID_WORK")
        measured = "RECOVERY_NO_LOAD_NO_INFERENCE"
    else:
        require(attempted == plan["pending_ordinals"], "QUALIFICATION_INCOMPLETE")
        require(status["attempt_consumed"] is True and
                read(output / "summary.json")["status"] == "COMPLETED_AWAITING_REVIEW" and
                read(output / "summary.json")["metrics"] is None and
                read(output / "cleanup.json")["status"] == "OWNED_SCRATCH_REMOVED" and
                read(output / "model_load_attempt.json")["load_attempts"] == 1, "QUALIFICATION_EXECUTION_REQUIRED")
        cuda = read(output / "worker_cuda.json")
        require(cuda["worker_cuda"] == "MEASURED_FP16_FUNCTIONAL" and cuda["worker_visible_gpus"] == 1,
                "QUALIFICATION_GPU_REQUIRED")
        measured = "WEIGHTS_LOADED_REAL_GPU_INFERENCE"
    outcomes = []
    for i in attempted:
        value = results[rows[i]["sample_id"]]
        sample = output / f"calls/{i:06d}/run/samples/000000"
        raw = read(sample / "raw.json")
        runtime = read(output / f"calls/{i:06d}/run/runtime.json")
        require(value["status"] in ("SUCCESS", "INVALID") and not raw["raw_nonfinite"] and
                value["hnlo"].get("replay_status") != "FAIL" and
                raw["cpu_tokenizer_replay"]["status"] == "PASS" and
                len(raw["steps"]) == len(raw["generated_ids"]) and all(s["all_finite"] for s in raw["steps"]),
                "QUALIFICATION_FINITE_DURABLE_RAW")
        require(runtime["native"]["implementation_sha256"] and
                runtime["attention"]["status"] == "EAGER_MODULES_VERIFIED", "QUALIFICATION_NATIVE_MODEL")
        if grant.get("effective_implementation"):
            from .minicpm_resampler_fp32 import descriptor
            installed = runtime["effective_implementation"]
            observed = read(sample / "effective_numerics.json")
            require(installed["descriptor"] == observed["implementation"] == descriptor() and
                    installed["all_parameter_dtypes"] == ["float16"] and
                    installed["parameter_identity_preserved"] is True, "QUALIFICATION_EFFECTIVE_MODEL")
        outcomes.append({"ordinal": i, "status": value["status"], "hnlo": value["hnlo"],
                         "finite_steps": len(raw["steps"]), "raw_sha256": sha(sample / "raw.json")})
    return {"schema": "safeshift-production-engineering-qualification-v1", "status": "TECHNICAL_QUALIFICATION_PASS",
            "run_id": grant["run_id"], "series_id": grant["series_id"], "attempt_id": grant["attempt_id"],
            "source_sha256": grant["source_sha256"], "runtime_ref": grant["runtime_ref"],
            "candidate_execution_config_sha256": grant["candidate_execution_config_sha256"],
            "scope": fields(**options(grant)), "measured": measured, "selection": selection(rows),
            "native_calls": len(attempted), "previously_durable": plan["already_durable_ordinals"],
            "outcomes": outcomes, "archive_sha256": sha(archive), "scientific_baseline_approved": False,
            "scientific_selection": "EXCLUDED", "pooling_allowed": False,
            "limits": "Three predeclared TRAIN cases; no full160, sustained-runtime or science qualification"}


def verify_portable_recovery(output, key, source, repo, ref, implementation=None):
    """Import only the sealed ZIP into a fresh workspace and require zero work."""
    from pathlib import Path
    import shutil
    from safeshift.pilot.artifacts import read, verify_archive
    from .train_runtime import launch_owner
    output = Path(output)
    final = read(Path(str(output) + ".qualification-result.json"))
    require(final["status"] == "TECHNICAL_QUALIFICATION_PASS", "QUALIFICATION_PASS_BEFORE_RECOVERY_PROBE")
    archive = Path(str(output) + ".zip")
    verify_archive(archive)
    suffix = "_q" + ("_fp32" if implementation else "")
    probe = output.parent.with_name(output.parent.name + "_portable_probe")
    probe.mkdir(exist_ok=False)
    base = probe / "base"
    work = base.with_name(base.name + suffix)
    work.mkdir()
    for path in (archive, Path(str(archive) + ".sha256.json")):
        shutil.copyfile(path, work / path.name)
    # A fresh empty Input root ensures admission is satisfied only by the ZIP.
    inputs = probe / "empty-input"
    inputs.mkdir()
    # The manifest is authenticated from the sealed history; the supervisor
    # still needs the authorized bundle before it can declare a no-op.
    original = read(output / "pilot_manifest.json")
    bundle = inputs / "locked-bundle"
    bundle.mkdir()
    with (bundle / "pilot_manifest.json").open("xb") as stream:
        stream.write((output / "pilot_manifest.json").read_bytes())
    require(original["split"] == "TRAIN", "RECOVERY_PROBE_TRAIN")
    resumed = launch_owner(key, source, repo, ref, owner_start=True, action="qualify",
                           implementation=implementation, work=base, inputs=inputs)
    value = read(Path(str(resumed) + ".qualification-result.json"))
    require(value["status"] == "TECHNICAL_QUALIFICATION_PASS" and value["native_calls"] == 0
            and value["previously_durable"] == ORDINALS
            and value["measured"] == "RECOVERY_NO_LOAD_NO_INFERENCE",
            "PORTABLE_RECOVERY_PROBE_FAILED:" + str(value.get("failure", value.get("measured"))))
    return resumed
