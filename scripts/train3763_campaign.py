"""Campaign staging/status only. Live submit/collect use the existing agy handoff."""
import argparse
import json
from pathlib import Path
from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as campaign
from safeshift.candidates.source import ROOT, require
from safeshift.kaggle_handoff import private_root, prepare, lock, SCHEMA as HANDOFF_SCHEMA
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest


def stage(ledger, locator, template, cohort, *, directory, calls, seconds, action, repair=None):
    directory = private_root(directory)
    require(not Path(directory).exists(), "EXISTING_HANDOFF_PRESERVED_USE_NEW_ATTEMPT_DIRECTORY")
    grant = campaign.load(locator)
    require(grant == ledger.grant and ledger.open_intent() is None, "CAMPAIGN_BUSY_OR_GRANT_DRIFT")
    history, custody = ledger.histories()
    number = len(ledger.intents())+1
    name = grant["campaign_id"]+"-"+str(number)
    p = campaign.plan(cohort, history, action=action, run_id=name, attempt_id="attempt-"+str(number),
        max_calls=calls, max_seconds=seconds, repair=repair)
    require(p["scheduled_ordinals"], "NO_ELIGIBLE_IMAGES_NO_MODEL_LOAD")
    from safeshift import internvl3763_python as python_input
    require(set(template) == {"technical_revision", "execution_input", "python_input"}, "CAMPAIGN_CONTEXT_FIELDS")
    require(template["python_input"] == python_input.binding(), "CAMPAIGN_PYTHON_CONTEXT")
    require(set(template["execution_input"]) == {"kind", "ref"}
        and template["execution_input"]["kind"] == "dataset_sources", "EXECUTION_INPUT_KIND")
    notebook = "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb"
    import subprocess
    metadata = read(ROOT / notebook)["metadata"]["safeshift"]
    sources = {key: list(value) for key, value in grant["inputs"].items()}
    sources[template["execution_input"]["kind"]].append(template["execution_input"]["ref"])
    sources["dataset_sources"].append(python_input.REF)
    request = {"schema": HANDOFF_SCHEMA, "commit_sha": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "runtime_commit": metadata["runtime_commit"],
        "notebook": notebook, "coordinator_required": False,
        "bindings": {"dataset": sources, "checkpoint": {"model": runtime.configuration()["model"],
                "revision": runtime.configuration()["revision"], "sha256": campaign.identity()["checkpoint_sha256"]},
            "source": runtime.source_spec(), "rights": grant["rights"],
            "scientific_method": {"science_sha256": grant["science_sha256"]},
            "runtime": {"technical_revision": template["technical_revision"], "execution_input": template["execution_input"],
                "python_input": template["python_input"]}}}
    execution = {"source": runtime.source_spec(), "cohort": cohort, "history": history,
        "history_archives": [{"archive": "custody/"+item["sha256"]+".zip", "sha256": item["sha256"],
            "plan": {"run_id": item["plan"]["run_id"], "attempt_id": item["plan"]["attempt_id"]}}
            for i, item in enumerate(custody, 1)], "plan": p, "input_marker_sha256": grant["input_marker_sha256"],
        "projection_sha256": digest(cohort)}
    request.update(scope=campaign.SCOPE, handoff_id=name, job="nguynanhtn/safeshift-train3763-"+name,
        version=1, execution_release=locator, plan=p, plan_sha256=digest(p),
        notebook_sha256=sha(ROOT / request["notebook"]), limits={"max_calls": calls, "job_seconds": seconds, "monitor_seconds": 900})
    request["bindings"]["runtime"].update(execution_request=execution,
        campaign_ledger=ledger.root.resolve().relative_to(ROOT.resolve()).as_posix(),
        local_history=[])
    request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
    from safeshift import internvl3763_operator as operator
    operator.verify_python_input(operator.api(), request, Path(str(directory) + "-python-proof"))
    campaign.bind(grant, request)
    # reserve() independently holds the global campaign lock and revalidates
    # histories/caps. A racing stager cannot get a second intent.
    intent = ledger.reserve(request)
    session = prepare(private_root(directory), request)
    write(session.root / "package/safeshift_train3763_execution.json", {"request": request, "campaign_intent": intent})
    # Exact prior ZIPs remain in checked local custody and original Kaggle
    # Outputs. The intent binds their complete metadata lineage; do not upload
    # cumulative private raw again for every shard. The serial operator is the
    # authority for history admission in this route, not a remote witness.
    return {"status": "STAGED_NOT_SUBMITTED", "directory": session.root.relative_to(ROOT).as_posix(),
        "job": request["job"], "intent_sha256": digest(intent), "calls_reserved": calls,
        "gpu_seconds_reserved": seconds*grant["caps"]["physical_gpus"], "owner_reapproval_required": False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("identity", "init", "plan", "status", "abort-pre-submit", "measure", "forecast"))
    p.add_argument("--directory", type=Path)
    p.add_argument("--mirror", type=Path)
    p.add_argument("--grant", type=Path)
    p.add_argument("--operator-id")
    p.add_argument("--template", type=Path)
    p.add_argument("--cohort", type=Path)
    p.add_argument("--handoff", type=Path)
    p.add_argument("--calls", type=int)
    p.add_argument("--seconds", type=int)
    p.add_argument("--mode", choices=("initial", "resume", "repair"), default="resume")
    p.add_argument("--repair", type=Path)
    p.add_argument("--archive", type=Path)
    p.add_argument("--weekly-remaining", type=int)
    args = p.parse_args(argv)
    if args.action == "forecast":
        kwargs = {}
        if args.weekly_remaining is not None:
            kwargs["weekly_quota_remaining_seconds"] = args.weekly_remaining
        if args.directory is not None:
            ledger = campaign.Ledger(private_root(args.directory))
            state = ledger.summary()
            current_source = digest(runtime.source_spec())
            measured = [x for x in ledger.events() if x["kind"] == "MEASURED" and x["source_sha256"] == current_source]
            kwargs.update(
                caps=ledger.grant["caps"],
                planned_total=state["planned"],
                completed_images=state["planned"] - state["counts"].get("NOT_ATTEMPTED", 0),
                pending_repair_images=state["counts"].get("TECHNICAL_ERROR", 0),
                already_reserved_calls=state["reserved_calls"],
                already_reserved_jobs=state["jobs"],
                already_reserved_gpu_seconds=state["reserved_gpu_seconds"],
                source_changed=not bool(measured),
            )
            if measured:
                obs = measured[-1].get("observed") or {}
                tel = obs.get("telemetry") or {}
                samples_tel = tel.get("samples") or []
                if samples_tel and "setup_seconds" in obs and "worker_non_sample_seconds" in obs and "raw_float32_bytes" in obs:
                    from decimal import Decimal
                    max_sample_dec = max(Decimal(str(x["seconds"])) for x in samples_tel)
                    setup_dec = Decimal(str(obs["setup_seconds"]))
                    load_dec = Decimal(str(tel.get("load_seconds", 0)))
                    non_sample_dec = setup_dec + Decimal(str(obs["worker_non_sample_seconds"]))
                    kwargs.update(
                        setup_seconds=str(setup_dec),
                        load_seconds=str(load_dec),
                        sample_seconds=str(max_sample_dec),
                        wall_clock_seconds=str(non_sample_dec + max_sample_dec),
                        non_sample_seconds=str(non_sample_dec),
                        sample_bytes=obs["sample_bytes"],
                        raw_float32_bytes=obs["raw_float32_bytes"],
                        zip_bytes=obs["zip_bytes"],
                        capture_per_sample_bytes=measured[-1].get("capture_per_sample_bytes"),
                        output_free_bytes=obs.get("output_free_bytes"),
                        verify_f32_geometry=False,
                    )
        result = campaign.project_campaign_budget(**kwargs)
        print(json.dumps(result, sort_keys=True))
        return 0
    require(args.directory is not None, "DIRECTORY_REQUIRED")
    root = private_root(args.directory)
    if args.action == "identity":
        from safeshift.internvl3763_operator import code_hash
        notebook = ROOT / "notebooks/SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb"
        result = {"status": "IDENTITY_ONLY_NO_GRANT", "operator_root_sha256": campaign.operator_binding(root),
            "science_sha256": digest(campaign.science()), "source_sha256": digest(runtime.source_spec()),
            "notebook_sha256": sha(notebook), "notebook_code_sha256": code_hash(read(notebook)),
            "runtime_commit": read(notebook)["metadata"]["safeshift"]["runtime_commit"]}
    elif args.action == "init":
        require(args.grant is not None and args.mirror is not None and args.operator_id is not None, "INIT_ARGUMENTS")
        grant = campaign.load(read(args.grant))
        campaign.Ledger.create(root, private_root(args.mirror), grant, args.operator_id)
        result = {"status": "INITIALIZED_NO_SUBMIT", "campaign_sha256": digest(grant)}
    else:
        ledger = campaign.Ledger(root)
        if args.action == "plan":
            require(all(x is not None for x in (args.grant, args.template, args.cohort, args.handoff, args.calls, args.seconds)), "PLAN_ARGUMENTS")
            result = stage(ledger, read(args.grant), read(args.template), read(args.cohort), directory=args.handoff,
                calls=args.calls, seconds=args.seconds, action=args.mode, repair=read(args.repair) if args.repair else None)
        elif args.action == "measure":
            require(args.archive is not None and args.seconds is not None, "MEASURE_ARGUMENTS")
            result = ledger.measure(args.archive, job_seconds=args.seconds)
        elif args.action == "abort-pre-submit":
            result = ledger.abort_pre_submit()
        else:
            with lock(root):
                result = ledger.summary()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
