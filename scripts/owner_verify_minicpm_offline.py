"""Owner-only ONLINE read-only verifier. Never run by Codex/Antigravity online.

Authority acquisition happens once after genuine release; full provider
reconciliation happens once at campaign end. No upload/submit/delete method.
Tests replace official SDK transport; JSON snapshots never replace provider GETs.
"""
import argparse
from pathlib import Path
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


def blocked(destination, error):
    c.write(destination / "BLOCKED.json", {"status": "BLOCKED", "error_type": type(error).__name__,
        "partial_evidence": "PRESERVED", "automatic_retry": False, "journal_written": False})
    raise ValueError("MINICPM_OWNER_VERIFIER_BLOCKED:"+type(error).__name__) from None


def capsule(client, value, ticket, package, destination):
    """Check explicit version/private inventory AND every downloaded capsule byte."""
    from safeshift.internvl3763_operator import download_capsule, bounded_python_zip
    from safeshift.fulltrain.minicpm_execution import MARKER
    expected = {c.ui.MARKER, MARKER, *(x["file"] for x in value["ancestors"]),
        *(x["file"]+".sha256.json" for x in value["ancestors"])}
    c.require({f.name for f in (package/"dataset").iterdir()} == expected
        and c.read(package/"dataset"/c.ui.MARKER) == value and c.read(package/"dataset"/MARKER) == ticket
        and ticket["payload"]["value_sha256"] == c.digest(value), "MINICPM_FINAL_CAPSULE_REQUEST_AND_TICKET")
    for ancestor in value["ancestors"]:
        c.ui.pair(package/"dataset"/ancestor["file"], ancestor["sha256"])
    result = c.old.verify_published_capsule(client, value, ticket, package)
    owner, slug, version = value["capsule_ref"].split("/")
    destination.mkdir(parents=True, exist_ok=False)
    files = {}
    for source in sorted((package / "dataset").iterdir()):
        c.snapshot_stat(source)
        target_dir = destination / source.name
        target_dir.mkdir()
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


def historical(route, client, destination):
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
    safety = recovery.current_safety(client, route.grant["recovery"],
        {item["value"]["job"] for item in route.manifest()["attempts"]} | {v44["job"], v5.JOB},
        "nguynanhtn/safeshift-minicpm-final-never-submit")
    # Original technical capsules also retain their original ticket and bytes.
    historical_capsules = []
    for number, active in ((4, events[3]["payload"]), (5, events[7]["payload"])):
        historical_capsules.append(capsule(client, active["value"], active["ticket"],
            c.safe(c.ROOT, active["package"]), destination / ("capsule-"+str(number))))
    return {"status": "ALL_HISTORICAL_CUSTODY_RECHECKED", "historical_sha256": c.digest(base),
        "v44": v44, "v5": v5proof, "current_account_safety": safety, "capsules": historical_capsules,
        "retired_disposition": "RETIRED_NO_USABLE_RESULTS_PROVIDER_UNCERTAINTY_PRESERVED", "refund": False}


def verify(route, destination, *, owner_performs_network=False, client=None):
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
        report = {"schema": c.SCHEMA, "status": "ALL_ORIGINALS_VERIFIED", "manifest_sha256": c.digest(manifest),
            "tools_sha256": c.digest(c.tools_manifest()), "reserved": manifest["reserved"],
            "billing_gpu_seconds": "NOT_OBSERVED", "attempts": [], "historical_sha256": c.digest(manifest["historical"]),
            "observed_unix": time.time(), "scientific_qualified": False}
        report["historical_verification"] = historical(route, client, destination / "historical")
        for i, item in enumerate(manifest["attempts"], 6):
            value, ticket, completion = item["value"], item["ticket"], item["completion"]
            c.require(route.recheck(item, completion) == completion["verification"], "MINICPM_FINAL_LOCAL_REPLAY")
            pkg = c.safe(route.root, item["package"])
            notebook = c.read(pkg / "notebook.ipynb")
            owner = completion["verification"]["owner_receipt"]
            provider = observe_kernel(client, value["job"], 1, notebook, value["input_sources"], kernel_id=owner["kernel_id"])
            folder = destination / ("job-"+str(i)); folder.mkdir()
            cap = capsule(client, value, ticket, pkg, folder / "capsule")
            attempt, supervisor = c.safe(route.root, completion["attempt"]), c.safe(route.root, completion["supervisor"])
            pairs = {"minicpm-fulltrain/"+attempt.name: attempt,
                "minicpm-fulltrain/supervision/"+supervisor.name: supervisor}
            output = download_outputs(client, value["job"], 1, attempt, c.sha(attempt), folder / "outputs", output_pairs=pairs)
            for remote_name, local in pairs.items():
                remote = folder / "outputs" / remote_name
                c.require(c.sha(remote) == c.sha(local) and c.sha(str(remote)+".sha256.json") == c.sha(str(local)+".sha256.json"),
                    "MINICPM_FINAL_EXACT_PROVIDER_OUTPUT_BYTES")
            c.require(provider == observe_kernel(client, value["job"], 1, notebook, value["input_sources"],
                kernel_id=owner["kernel_id"]), "MINICPM_PROVIDER_CHANGED_DURING_FINAL")
            proof = {"ticket_sha256": c.digest(ticket), "completion_sha256": c.digest(completion), "provider": provider,
                "capsule_verified": True, "output_verified": True, "local_replayed": True, "capsule": cap, "output": output}
            c.write(folder / "proof.json", proof); report["attempts"].append(proof)
        c.require(route.manifest() == manifest, "MINICPM_LOCAL_STATE_CHANGED_DURING_FINAL")
        c.validate_provider_report(manifest, report)
        c.write(destination / "github-exports.json", exports)
        c.write(destination / "report.json", report)
        c.write(destination / "owner-template.json", {"manifest_sha256": c.digest(manifest), "report_sha256": c.digest(report),
            "status": "PENDING_OWNER_AND_REVIEWER_RECORDS"})
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
    args = p.parse_args(argv)
    if args.authority_locator:
        result = acquire(c.read(args.authority_locator), args.output, owner_performs_network=args.owner_performs_network)
    else:
        result = verify(c.Continuation(args.directory), args.output, owner_performs_network=args.owner_performs_network)
    print(result["status"])


if __name__ == "__main__":
    main()
