"""Owner-only ONLINE read-only verifier. Never run by Codex/Antigravity online.

Authority acquisition happens once after genuine release; full provider
reconciliation happens once at campaign end. No upload/submit/delete method.
Tests replace official SDK transport; JSON snapshots never replace provider GETs.
"""
import argparse
from pathlib import Path
import re
import tempfile
import time
import zipfile

from scripts import minicpm_offline_continuation as c


def acquire(locator, destination, *, owner_performs_network=False):
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    destination = c.private(destination)
    destination.mkdir(parents=True, exist_ok=False)
    exports = {}
    def reader(path):
        value = c.a.github_get(path)
        c.require(path not in exports or exports[path] == value, "MINICPM_AUTHORITY_CHANGED_DURING_EXPORT")
        exports[path] = value
        return value
    try:
        grant = c.a.load(locator, reader=reader)
        c.policy.validate_delegation(grant)
        c.authenticate(locator, exports)
        c.write(destination / "github-exports.json", exports)
        return {"status": "OWNER_ACQUIRED_AUTHORITY_EXPORTS", "endpoints": sorted(exports)}
    except BaseException as error:
        blocked(destination, error)


def serial8_proof(proposal, destination, *, owner_performs_network=False):
    """Compute the publishable digest after merge and four approval records."""
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    c.a.validate(proposal)
    c.require(c.a.uses_proof(proposal), "MINICPM_SERIAL8_PROPOSAL_REQUIRED")
    proof = c.a.collect_proof(proposal, {"comment_id": 0}, c.a.github_get)
    result = {c.a.PROOF_KEY: c.digest(proof)}
    c.write(c.private(destination), result)
    return {"status": "SERIAL8_PROOF_DIGEST_ONLY"}


def blocked(destination, error):
    # Only project gate identifiers may leave the exception. SDK exceptions
    # can include credentials in signed URLs or machine-specific paths.
    code = str(error).split(":", 1)[0]
    reason = code if re.fullmatch(r"(?:MINICPM|MANUAL|CAPSULE|UI)_[A-Z0-9_]{1,100}", code) else None
    c.write(destination / "BLOCKED.json", {"status": "BLOCKED", "error_type": type(error).__name__,
        "gate": reason,
        "partial_evidence": "PRESERVED", "automatic_retry": False, "journal_written": False})
    raise ValueError("MINICPM_OWNER_VERIFIER_BLOCKED:"+type(error).__name__) from None


def capsule(client, value, ticket, package, destination):
    """Check explicit version/private inventory AND every downloaded capsule byte."""
    from safeshift.internvl3763_operator import download_capsule, bounded_python_zip
    from safeshift.fulltrain.minicpm_execution import MARKER
    from scripts.submit_internvl_v2 import bounded_http
    from scripts.minicpm_fulltrain_transport import download_ancestor
    expected = {c.ui.MARKER, MARKER, *(x["file"] for x in value["ancestors"]),
        *(x["file"]+".sha256.json" for x in value["ancestors"])}
    c.require({f.name for f in (package/"dataset").iterdir()} == expected
        and c.read(package/"dataset"/c.ui.MARKER) == value and c.read(package/"dataset"/MARKER) == ticket
        and ticket["payload"]["value_sha256"] == c.digest(value), "MINICPM_FINAL_CAPSULE_REQUEST_AND_TICKET")
    for ancestor in value["ancestors"]:
        c.ui.pair(package/"dataset"/ancestor["file"], ancestor["sha256"])
    with bounded_http():
        result = c.old.verify_published_capsule(client, value, ticket, package)
    owner, slug, version = value["capsule_ref"].split("/")
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    for source in sorted((package / "dataset").iterdir()):
        c.snapshot_stat(source)
        target_dir = destination / source.name
        target_dir.mkdir()
        if source.name.endswith(".bin") and source.stat().st_size >= 63 * 2**20:
            downloaded = download_ancestor(client, owner, slug, version, source, target_dir)
        else:
            with bounded_http():
                downloaded = download_capsule(client, owner, slug, version, source.name, target_dir)
        if c.sha(downloaded) == c.sha(source):
            checksum = c.sha(downloaded)
        elif zipfile.is_zipfile(downloaded):
            # Dataset API may wrap a SINGLE requested file in a ZIP.
            bounded_python_zip(downloaded)
            with zipfile.ZipFile(downloaded) as bundle:
                info = bundle.infolist()[0]
                c.require(info.filename == source.name and info.file_size == source.stat().st_size, "MINICPM_FINAL_CAPSULE_WRAPPER")
                with bundle.open(info) as stream:
                    import hashlib
                    checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        else:
            checksum = c.sha(downloaded)
        c.require(checksum == c.sha(source), "MINICPM_FINAL_CAPSULE_EVERY_BYTE")
        files[source.name] = checksum
    return {"metadata": result, "files": files, "private": True, "version": 1}


def serial7_closure(destination, *, owner_performs_network=False, client=None):
    """Independent read-only provider check of the frozen failed reservation."""
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    from scripts.reconcile_train3763_manual import observe_kernel, download_outputs
    from scripts.submit_internvl_v2 import bounded_http

    seventh = c.serial7
    processed = c.ROOT / "data/processed"
    local, active, _ = seventh.verify_local(processed)
    destination = c.private(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        if client is None:
            from safeshift.internvl3763_operator import api
            client = api()
        with bounded_http():
            state = str(client.kernels_status(seventh.JOB + "/1").status).split(".")[-1]
        c.require(state in ("COMPLETE", "ERROR"), "MINICPM_SERIAL7_TERMINAL_REQUIRED")
        value, ticket = active["value"], active["ticket"]
        notebook, sources = active["notebook"], value["input_sources"]
        provider = observe_kernel(client, seventh.JOB, 1, notebook, sources, expected_state=state)
        download = processed / "inspect_run_7"
        archive = download / seventh.ARCHIVE
        output = download_outputs(client, seventh.JOB, 1, archive, seventh.ZIP_SHA, destination,
            output_pairs={seventh.ARCHIVE: archive}, known_names=seventh.inventory(download))
        output["sidecar_sha256"] = c.sha(destination / (seventh.ARCHIVE + ".sha256.json"))
        package = c.safe(processed / seventh.PRIMARY, active["package"])
        cap = capsule(client, value, ticket, package, destination / "capsule")
        # The repeatable closure binds identity and bytes, independent of lookup time.
        cap["metadata"].pop("observed_unix")
        c.require(provider == observe_kernel(client, seventh.JOB, 1, notebook, sources,
            expected_state=state, kernel_id=provider["kernel_id"]), "MINICPM_SERIAL7_PROVIDER_CHANGED")
        result = {"local": local, "provider": provider, "capsule": cap, "output": output}
        seventh.verify_closure(result, local, active)
        c.write(destination / "serial7-closure.json", result)
        return result
    except BaseException as error:
        blocked(destination, error)


def resolve_kernel(client, candidates, kernel_id=None):
    from scripts.minicpm_fulltrain_recovery import account_jobs
    ids = {}
    c.require(all(isinstance(ref, str) and c.prenative.SLUG.fullmatch(ref) for ref in candidates),
        "MINICPM_PRE_NATIVE_PROVIDER_CANDIDATES")
    owned = account_jobs(client, kernel_ids=ids)
    matches = (set(candidates) & owned) | {ref for ref, number in ids.items()
        if kernel_id is not None and number == kernel_id}
    c.require(len(matches) == 1, "MINICPM_PRE_NATIVE_PROVIDER_SLUG_ABSENT_OR_AMBIGUOUS")
    return matches.pop()


def provider_closure(client, active, local, download, package, destination, candidates, *, kernel_id=None):
    """Read-only provider custody for one signed reservation closed before native.

    The kernel is identified by its numeric ID, exact notebook code, private
    capsule bytes and supervisor-only Output, not by a slug: Kaggle UI imports
    may run under an auto-generated slug and a later rename changes it. Exactly
    one candidate slug must exist in the complete Owner inventory.
    """
    from scripts.reconcile_train3763_manual import download_outputs, observe_kernel
    from scripts.submit_internvl_v2 import bounded_http

    value, ticket = active["value"], active["ticket"]
    c.require(time.time() >= ticket["payload"]["start_before_unix"], "MINICPM_PRE_NATIVE_START_WINDOW_OPEN")
    c.require(value["job"] in candidates, "MINICPM_PRE_NATIVE_PROVIDER_CANDIDATES")
    job = resolve_kernel(client, candidates, kernel_id)
    with bounded_http():
        state = str(client.kernels_status(job + "/1").status).split(".")[-1]
    c.require(state in ("COMPLETE", "ERROR"), "MINICPM_PRE_NATIVE_TERMINAL_REQUIRED")
    notebook, sources = active["notebook"], value["input_sources"]
    provider = observe_kernel(client, job, 1, notebook, sources, expected_state=state,
        kernel_id=kernel_id, record_accelerator=True)
    archive = download / local["supervisor"]
    output = download_outputs(client, job, 1, archive, local["supervisor_sha256"], destination,
        output_pairs={local["supervisor"]: archive}, known_names=set(c.prenative.inventory(download)))
    output["sidecar_sha256"] = c.sha(destination / (local["supervisor"] + ".sha256.json"))
    cap = capsule(client, value, ticket, package, destination / "capsule")
    cap["metadata"].pop("observed_unix")
    c.require(provider == observe_kernel(client, job, 1, notebook, sources, expected_state=state,
        kernel_id=provider["kernel_id"], record_accelerator=True), "MINICPM_PRE_NATIVE_PROVIDER_CHANGED")
    c.require(resolve_kernel(client, candidates, provider["kernel_id"]) == job, "MINICPM_PRE_NATIVE_PROVIDER_SLUG_CHANGED")
    accelerator = {"enable_gpu": provider.pop("enable_gpu"), "machine_shape": provider.pop("machine_shape"),
        "scope": "CURRENT_KERNEL_METADATA_NOT_EXECUTION_TIME_PROOF"}
    return {"schema": c.prenative.PROVIDER_SCHEMA, "local": local, "provider": provider, "accelerator": accelerator,
        "ticket_job": value["job"], "provider_job": job, "capsule": cap, "output": output}


def serial8_closure(destination, *, owner_performs_network=False, client=None, provider_job=None):
    """Owner-side, read-only custody for the actual Serial 8 kernel."""
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    incident = c.serial8
    processed = c.ROOT / "data/processed"
    local, active, _ = incident.verify_local(processed)
    destination = c.private(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        if client is None:
            from safeshift.internvl3763_operator import api
            client = api()
        result = provider_closure(client, active, local, processed / incident.DOWNLOAD,
            c.safe(processed / incident.PRIMARY, active["package"]), destination,
            {*incident.PROVIDER_JOBS, provider_job or incident.TICKET_JOB},
            kernel_id=incident.KERNEL_ID)
        incident.verify_closure(result, local, active)
        c.write(destination / "serial8-closure.json", result)
        return result
    except BaseException as error:
        blocked(destination, error)


def pre_native_closure(directory, download, destination, *, provider_job=None, owner_performs_network=False,
                       client=None):
    """Generic Owner provider closure for the active reservation of any serial."""
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    route = c.Continuation(directory)
    active = route.state()["active"]
    c.require(active is not None, "MINICPM_PRE_NATIVE_ACTIVE_RESERVATION_REQUIRED")
    download = c.private(download)
    local = route.pre_native_local(download, active)
    destination = c.private(destination)
    destination.mkdir(parents=True, exist_ok=False)
    try:
        if client is None:
            from safeshift.internvl3763_operator import api
            client = api()
        candidates = {active["value"]["job"]} | ({provider_job} if provider_job else set())
        package = c.safe(route.root, active["package"])
        result = provider_closure(client, active, local, download, package, destination, candidates)
        c.prenative.verify_provider(result, local, active, c.prenative.package_files(package))
        c.write(destination / "pre-native-closure.json", result)
        return result
    except BaseException as error:
        blocked(destination, error)


def historical(route, client, destination, *, observed_jobs, aliases):
    """Recheck both failed jobs; preserve retired unknowns, never assert deletion."""
    from scripts import minicpm_v5_incident, minicpm_fulltrain_recovery as recovery
    from safeshift.fulltrain import minicpm_v5_incident as v5
    base = route.registration["base"]
    events = base["events"]
    c.require(recovery.verify_retired(route.grant["recovery"]) is not None, "MINICPM_HISTORICAL_RESERVATIONS")
    v44 = recovery.verify_v44_prefix(events, online=True, client=client)
    v5proof = minicpm_v5_incident.verify_evidence(c.safe(c.ROOT, base["v5_directory"]),
        minicpm_v5_incident.prefix(events), online=True, client=client)
    c.require(v5proof == base["v5_closure"], "MINICPM_FINAL_V5_CLOSURE_DRIFT")
    from scripts.reconcile_train3763_manual import observe_kernel, download_outputs
    sixth = c.serial6
    processed = c.ROOT / "data/processed"
    local, _ = sixth.verify_local(processed)
    c.require(local == base["serial6"], "MINICPM_FINAL_SERIAL6_CUSTODY")
    active = c.read(processed / "minicpm-offline/event-000001.json")["payload"]
    value = active["value"]
    from scripts.submit_internvl_v2 import bounded_http
    with bounded_http():
        state = str(client.kernels_status(sixth.JOB + "/1").status).split(".")[-1]
    c.require(state in ("COMPLETE", "ERROR"), "MINICPM_SERIAL6_TERMINAL_REQUIRED")
    provider = observe_kernel(client, sixth.JOB, 1, active["notebook"], value["input_sources"],
                              expected_state=state)
    archive = processed / "inspect_run_6" / sixth.ARCHIVE
    folder = destination / "serial6"
    folder.mkdir(parents=True, exist_ok=False)
    download_outputs(client, sixth.JOB, 1, archive, sixth.ZIP_SHA, folder,
                     output_pairs={sixth.ARCHIVE: archive})
    c.ui.pair(folder / sixth.ARCHIVE, sixth.ZIP_SHA)
    sixth_capsule = capsule(client, value, active["ticket"],
        c.safe(processed / "minicpm-offline", active["package"]), folder / "capsule")
    c.require(provider == observe_kernel(client, sixth.JOB, 1, active["notebook"], value["input_sources"],
        expected_state=state, kernel_id=provider["kernel_id"]), "MINICPM_SERIAL6_PROVIDER_CHANGED")
    known_jobs = set(observed_jobs) | {v44["job"], v5.JOB, sixth.JOB}
    failures = {}
    if "serial7_closure" in base:
        checked = serial7_closure(destination / "serial7", owner_performs_network=True, client=client)
        c.require(checked == base["serial7_closure"], "MINICPM_FINAL_SERIAL7_CLOSURE_DRIFT")
        failures["serial7_closure"] = checked
        known_jobs.add(c.serial7.JOB)
    if "serial8_closure" in base:
        checked = serial8_closure(destination / "serial8", owner_performs_network=True, client=client,
            provider_job=aliases.get(str(c.serial8.KERNEL_ID), base["serial8_closure"]["provider_job"]))
        c.prenative.same_execution(base["serial8_closure"], checked)
        failures["serial8_closure"] = checked
        if checked["provider_job"].startswith("nguynanhtn/safeshift-minicpm-" + route.grant["campaign_id"] + "-"):
            known_jobs.add(checked["provider_job"])
    known_jobs = {job for job in known_jobs if job.startswith("nguynanhtn/safeshift-minicpm-" + route.grant["campaign_id"] + "-")}
    safety = recovery.current_safety(client, route.grant["recovery"], known_jobs,
        "nguynanhtn/safeshift-minicpm-final-never-submit")
    # Original technical capsules also retain their original ticket and bytes.
    historical_capsules = []
    for number, active in ((4, events[3]["payload"]), (5, events[7]["payload"])):
        historical_capsules.append(capsule(client, active["value"], active["ticket"],
            c.safe(c.ROOT, active["package"]), destination / ("capsule-"+str(number))))
    return {"status": "ALL_HISTORICAL_CUSTODY_RECHECKED", "historical_sha256": c.digest(base), **failures,
        "v44": v44, "v5": v5proof, "serial6": provider, "serial6_capsule": sixth_capsule,
        "serial6_supervisor_sha256": sixth.ZIP_SHA, "current_account_safety": safety, "capsules": historical_capsules,
        "retired_disposition": "RETIRED_NO_USABLE_RESULTS_PROVIDER_UNCERTAINTY_PRESERVED", "refund": False}


def verify(route, destination, *, owner_performs_network=False, client=None, aliases=None):
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    destination = c.private(destination)
    manifest = route.manifest()
    destination.mkdir(parents=True, exist_ok=False)
    try:
        exports = {path: c.a.github_get(path) for path in route.registration["exports"]}
        c.authenticate(route.registration["locator"], exports, collection=True)
        if client is None:
            from safeshift.internvl3763_operator import api
            client = api()
        from scripts.reconcile_train3763_manual import observe_kernel, download_outputs
        report = {"schema": manifest["schema"], "status": "ALL_ORIGINALS_VERIFIED", "manifest_sha256": c.digest(manifest),
            "tools_sha256": c.digest(c.tools_manifest()), "reserved": manifest["reserved"],
            "billing_gpu_seconds": "NOT_OBSERVED", "attempts": [], "historical_sha256": c.digest(manifest["historical"]),
            "observed_unix": time.time(), "scientific_qualified": False}
        aliases = aliases or {}
        jobs = set()
        if "closed" in manifest:
            report["closed"] = []
            for item in manifest["closed"]:
                active, original = item["active"], item["closure"]
                folder = destination / ("closed-" + str(active["ticket"]["payload"]["number"]))
                folder.mkdir()
                download = c.private(c.safe(c.ROOT, item["download"]))
                fresh = provider_closure(client, active, route.pre_native_local(download, active), download,
                    c.safe(route.root, active["package"]), folder, {active["value"]["job"], original["provider_job"],
                        aliases.get(str(original["provider"]["kernel_id"]), original["provider_job"])},
                    kernel_id=original["provider"]["kernel_id"])
                c.prenative.same_execution(original, fresh)
                report["closed"].append(fresh)
                jobs.add(fresh["provider_job"])
        for item in manifest["attempts"]:
            i = item["ticket"]["payload"]["number"]
            value, ticket, completion = item["value"], item["ticket"], item["completion"]
            c.require(route.recheck(item, completion) == completion["verification"], "MINICPM_FINAL_LOCAL_REPLAY")
            pkg = c.safe(route.root, item["package"])
            notebook = c.read(pkg / "notebook.ipynb")
            owner = completion["verification"]["owner_receipt"]
            candidates = {value["job"], aliases.get(str(owner["kernel_id"]), value["job"])}
            job = resolve_kernel(client, candidates, owner["kernel_id"]) if "closed" in manifest else value["job"]
            provider = observe_kernel(client, job, 1, notebook, value["input_sources"], kernel_id=owner["kernel_id"])
            jobs.add(job)
            folder = destination / ("job-"+str(i)); folder.mkdir()
            cap = capsule(client, value, ticket, pkg, folder / "capsule")
            attempt, supervisor = c.safe(route.root, completion["attempt"]), c.safe(route.root, completion["supervisor"])
            pairs = {"minicpm-fulltrain/"+attempt.name: attempt,
                "minicpm-fulltrain/supervision/"+supervisor.name: supervisor}
            (folder / "outputs").mkdir()
            output = download_outputs(client, job, 1, attempt, c.sha(attempt), folder / "outputs", output_pairs=pairs)
            for remote_name, local in pairs.items():
                remote = folder / "outputs" / remote_name
                c.require(c.sha(remote) == c.sha(local) and c.sha(str(remote)+".sha256.json") == c.sha(str(local)+".sha256.json"),
                    "MINICPM_FINAL_EXACT_PROVIDER_OUTPUT_BYTES")
            c.require(provider == observe_kernel(client, job, 1, notebook, value["input_sources"],
                kernel_id=owner["kernel_id"]), "MINICPM_PROVIDER_CHANGED_DURING_FINAL")
            proof = {"ticket_sha256": c.digest(ticket), "completion_sha256": c.digest(completion), "provider": provider,
                "capsule_verified": True, "output_verified": True, "local_replayed": True, "capsule": cap, "output": output}
            c.write(folder / "proof.json", proof); report["attempts"].append(proof)
        report["historical_verification"] = historical(route, client, destination / "historical", observed_jobs=jobs, aliases=aliases)
        c.require(route.manifest() == manifest, "MINICPM_LOCAL_STATE_CHANGED_DURING_FINAL")
        c.validate_provider_report(manifest, report)
        c.write(destination / "github-exports.json", exports)
        c.write(destination / "report.json", report)
        c.write(destination / "owner-template.json", {"manifest_sha256": c.digest(manifest), "report_sha256": c.digest(report),
            "status": "PENDING_AUTHENTIC_OWNER_FINAL_COMMENT"})
        return report
    except BaseException as error:
        blocked(destination, error)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--owner-performs-network", action="store_true", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--authority-locator", type=Path)
    group.add_argument("--directory", type=Path)
    group.add_argument("--serial7-closure", action="store_true")
    group.add_argument("--serial8-closure", action="store_true")
    group.add_argument("--pre-native-closure", type=Path, metavar="PRIMARY_DIRECTORY")
    group.add_argument("--serial8-proof-proposal", "--serial9-proof-proposal", type=Path)
    p.add_argument("--download", type=Path, help="Owner-downloaded Output of the failed serial")
    p.add_argument("--provider-job", help="Actual owner/slug if Kaggle ran the notebook under another slug")
    p.add_argument("--aliases", type=Path, help="Final verification only: JSON mapping kernel ID to current Owner slug")
    args = p.parse_args(argv)
    c.require((args.download is not None) == (args.pre_native_closure is not None)
        and (args.provider_job is None or args.pre_native_closure is not None or args.serial8_closure)
        and (args.aliases is None or args.directory is not None), "MINICPM_PRE_NATIVE_ARGUMENTS")
    if args.authority_locator:
        result = acquire(c.read(args.authority_locator), args.output, owner_performs_network=args.owner_performs_network)
    elif args.serial7_closure:
        serial7_closure(args.output, owner_performs_network=args.owner_performs_network)
        result = {"status": "SERIAL7_PROVIDER_CLOSURE_EXPORTED"}
    elif args.serial8_closure:
        serial8_closure(args.output, owner_performs_network=args.owner_performs_network, provider_job=args.provider_job)
        result = {"status": "SERIAL8_PROVIDER_CLOSURE_EXPORTED"}
    elif args.pre_native_closure:
        pre_native_closure(args.pre_native_closure, args.download, args.output, provider_job=args.provider_job,
            owner_performs_network=args.owner_performs_network)
        result = {"status": "PRE_NATIVE_PROVIDER_CLOSURE_EXPORTED"}
    elif args.serial8_proof_proposal:
        result = serial8_proof(c.read(args.serial8_proof_proposal), args.output,
            owner_performs_network=args.owner_performs_network)
    else:
        result = verify(c.Continuation(args.directory), args.output, owner_performs_network=args.owner_performs_network,
            aliases=c.read(args.aliases) if args.aliases else None)
    print(result["status"])


if __name__ == "__main__":
    main()
