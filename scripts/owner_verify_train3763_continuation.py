"""ONLINE tool for the Owner to run PERSONALLY, once at campaign end.

Antigravity/Codex must not execute this command against real services. The
offline companion never calls it. This uses the existing pinned official SDK
and read-only GitHub/Kaggle verification, never push/upload/submit/model calls.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
import zipfile


def load_companion():
    spec = importlib.util.spec_from_file_location("offline_continuation", Path(__file__).with_name("train3763_continuation.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def acquire_authority(ledger, release_locator, destination, *, owner_performs_network=False):
    """Owner-only authenticated export closure, once after source release."""
    c = load_companion()
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    destination = c._private(destination)
    c.require(not destination.exists(), "FRESH_AUTHORITY_EXPORT_DIRECTORY")
    paths = {"/issues/comments/" + str(c.DECISION_ID), "/issues/comments/" + str(release_locator["comment_id"]),
        "/issues/comments/" + str(c.BASELINE_OWNER["comment_id"])}
    result = {}

    def discover(value):
        if type(value) is dict:
            if set(value) == {"comment_id", "body_sha256"}:
                c.require(type(value["comment_id"]) is int and value["comment_id"] > 0, "EXPORT_COMMENT_ID")
                paths.add("/issues/comments/" + str(value["comment_id"]))
            if type(value.get("implementation_pr")) is int:
                paths.add("/pulls/" + str(value["implementation_pr"]))
            for child in value.values():
                discover(child)
        elif type(value) is list:
            for child in value:
                discover(child)
    discover(ledger.grant)
    discover(ledger.open_intent())
    destination.mkdir(parents=True, exist_ok=False)
    try:
        while paths - result.keys():
            c.require(len(paths) <= 128, "AUTHORITY_EXPORT_BOUND")
            path = sorted(paths - result.keys())[0]
            value = c.authority.get(path)
            result[path] = value
            discover(value)
            if "body" in value:
                for block in re.findall(r"```json\s*(\{.*?\})\s*```", value["body"], re.S):
                    discover(c.runtime._strict_json_loads(block))
        intent = ledger.open_intent()
        c.require(intent is not None, "EXISTING_INTENT_REQUIRED")
        c.authenticate(ledger.grant, intent["request"], result, release_locator)
        c.write(destination / "github-exports.json", result)
        return {"status": "OWNER_ACQUIRED_AUTHENTICATED_EXPORTS", "endpoints": sorted(result)}
    except BaseException as error:
        try:
            c.write(destination / "BLOCKED.json", {"status": "BLOCKED", "error_type": type(error).__name__, "automatic_retry": False})
        except BaseException as persistence:
            raise ValueError("OWNER_AUTHORITY_EXPORT_BLOCKED:EVIDENCE_WRITE_" + type(persistence).__name__) from None
        raise ValueError("OWNER_AUTHORITY_EXPORT_BLOCKED:" + type(error).__name__) from None


def verify(route, destination, *, owner_performs_network=False):
    """All network is below this explicit boundary; tests replace only transport."""
    c = load_companion()
    c.require(owner_performs_network is True, "OWNER_MUST_PERSONALLY_RUN_EXTERNAL_VERIFICATION")
    destination = c._private(destination)
    c.require(not destination.exists(), "FRESH_FINAL_EVIDENCE_DIRECTORY_REQUIRED")
    manifest = route.manifest()
    c.source_check(route.registration["initial_intent"]["request"])
    destination.mkdir(parents=True, exist_ok=False)
    exports = {}

    def reader(path):
        result = c.authority.get(path)  # genuine authenticated read, no JSON fallback
        if path in exports:
            c.require(exports[path] == result, "GITHUB_CHANGED_DURING_FINAL_VERIFICATION")
        exports[path] = result
        return result

    try:
        # Retrieve every pinned original/technical/O5/audit/comment and merged PR
        # from GitHub again. Offline snapshots never substitute for these GETs.
        for path in route.registration["github_exports"]:
            reader(path)
        c.authenticate(route.ledger.grant, route.registration["initial_intent"]["request"],
            exports, route.registration["release_locator"])
        client = c.operator.api()  # official pinned SDK, read-only operations below
        report = {"status": "ALL_ORIGINALS_VERIFIED", "manifest_sha256": c.digest(manifest),
            "tool_sha256": c.sha(__file__), "attempts": [], "historical": [], "aborted": [],
            "observed_unix": time.time(), "budget": manifest["budget"],
            "billing_gpu_seconds": "NOT_OBSERVED", "scientific_selection": "PENDING", "scientific_qualified": False}
        seen_kernels, seen_jobs = set(), set()

        resources = c.result_tools().resources

        def verify_one(intent, archive, expected_sha, folder, expected_provider=None):
            request = intent["request"]
            c.campaign.load(request["execution_release"], reader=reader, collection=True)
            # Original sources may differ for old failed attempts. Verify their
            # immutable committed notebooks rather than substitute current HEAD.
            notebook_bytes = c.subprocess.check_output(["git", "show", request["commit_sha"] + ":" + request["notebook"]], cwd=c.runtime.ROOT)
            c.require(hashlib.sha256(notebook_bytes).hexdigest() == request["notebook_sha256"], "ORIGINAL_COMMITTED_NOTEBOOK")
            notebook = c.runtime._strict_json_loads(notebook_bytes)
            sources = c.operator.input_sources(request)
            expected_state = expected_provider["state"] if expected_provider else "COMPLETE"
            kernel_id = expected_provider.get("kernel_id") if expected_provider else None
            actual_job = expected_provider.get("job_id", request["job"]) if expected_provider else request["job"]
            args = (client, actual_job, 1, notebook, sources)
            provider = c.manual.observe_kernel(*args, kernel_id=kernel_id, expected_state=expected_state)
            c.require(provider["kernel_id"] not in seen_kernels and provider["job_id"] not in seen_jobs, "FINAL_DUPLICATE_PROVIDER")
            seen_kernels.add(provider["kernel_id"])
            seen_jobs.add(provider["job_id"])
            folder.mkdir(parents=True, exist_ok=False)
            capsule = c.operator.verify_execution_input(client, request, intent, folder / "capsule")
            output = c.manual.download_outputs(client, actual_job, 1, archive, expected_sha, folder)
            c.require(c.manual.observe_kernel(*args, kernel_id=provider["kernel_id"], expected_state=expected_state) == provider, "FINAL_PROVIDER_CHANGED")
            c.require(c.sha(folder / Path(archive).name) == expected_sha
                and c.sha(str(folder / Path(archive).name) + ".sha256.json") == c.sha(str(archive) + ".sha256.json"), "FINAL_ORIGINAL_PROVIDER_COPY")
            c.write(folder / "proof.json", {"provider": provider, "capsule": capsule, "output": output})
            return {"intent_sha256": c.digest(intent), "archive_sha256": expected_sha, "provider": provider,
                "input_bytes_verified": True, "provider_copy_verified": True, "capsule": capsule, "output": output}

        events = route.ledger.events()[:route.registration["base_count"]]
        for number, item in enumerate(manifest["base_custody"], 1):
            collected = [e for e in events if e["kind"] == "COLLECTED" and e["sha256"] == item["sha256"]]
            c.require(len(collected) == 1, "HISTORICAL_EXACT_COLLECTION")
            intent = next(e for e in events if e["kind"] == "INTENT" and c.digest(e) == collected[0]["intent_sha256"])
            # Manual Attempt8 had a distinct actual slug. Preserve that fact.
            archive = c.safe(c.runtime.ROOT, item["path"])
            c.runtime.sealed_history(archive, item["sha256"], item["plan"])
            proof = verify_one(intent, archive, item["sha256"], destination / ("historical-" + str(number)), collected[0]["provider"])
            report["historical"].append({**proof, "provider_reverified": True, "resources": resources(archive, intent)})
        for number, item in enumerate(manifest["attempts"], 1):
            intent, receipt = item["intent"], item["receipt"]
            c.campaign.bind(route.ledger.grant, intent["request"], reader=reader)
            archive = c.safe(c.runtime.ROOT, item["archive"])
            c.require(c.verify_local(intent, route.ledger.grant, archive, receipt["owner_receipt"]) == receipt, "FINAL_LOCAL_RECHECK")
            proof = verify_one(intent, archive, receipt["sha256"], destination / ("attempt-" + str(number)), receipt["owner_receipt"])
            proof["resources"] = resources(archive, intent)
            report["attempts"].append(proof)
        # Check complete account inventory once, all pages, no active campaign
        # jobs or extra versions. No fabricated SUBMITTED/PUSH_INTENT events.
        owned, token, tokens = {}, None, set()
        from scripts.submit_internvl_v2 import bounded_http
        for page in range(1, 65):
            with bounded_http():
                response = client.kernels_list_with_response(mine=True, page_size=100, page_token=token, page=None if token else page)
            for row in response.kernels:
                c.require(row.ref not in owned, "FINAL_DUPLICATE_INVENTORY_ENTRY")
                owned[row.ref] = True
            token = response.next_page_token
            if not token and len(response.kernels) < 100:
                break
            if token:
                c.require(token not in tokens, "FINAL_INVENTORY_TOKEN_CYCLE")
                tokens.add(token)
        else:
            raise ValueError("FINAL_INCOMPLETE_ACCOUNT_INVENTORY")
        prefix = "nguynanhtn/safeshift-train3763-" + route.ledger.grant["campaign_id"] + "-"
        expected = {proof["provider"]["job_id"] for proof in report["attempts"] + report["historical"]}
        c.require({job for job in owned if job.startswith(prefix)} == {job for job in expected if job.startswith(prefix)}
            and expected <= set(owned), "FINAL_ACCOUNT_JOB_HISTORY_MISMATCH")
        for old in manifest["historical_attempts"]:
            if old["outcome"]["kind"] == "ABORTED_PRE_SUBMIT":
                intent = old["intent"]
                c.require(intent["request"]["job"] not in owned, "ABORTED_JOB_PRESENT_AT_FINAL")
                report["aborted"].append({"intent_sha256": c.digest(intent), "job": intent["request"]["job"],
                    "original_abort_sha256": c.digest(old["outcome"]), "provider_absent_at_final": True,
                    "reserved_calls": intent["reserved_calls"], "reserved_gpu_seconds": intent["reserved_gpu_seconds"]})
        c.require(route.manifest() == manifest, "LOCAL_STATE_CHANGED_DURING_FINAL_VERIFICATION")
        c.write(destination / "github-exports.json", exports)
        c.write(destination / "report.json", report)
        c.write(destination / "owner-comment-template.json", {"manifest_sha256": c.digest(manifest), "report": report,
            "status": "PENDING_OWNER_AND_REVIEWER_RECORDS"})
        return report
    except BaseException as error:
        try:
            c.write(destination / "BLOCKED.json", {"status": "BLOCKED", "error_type": type(error).__name__,
                "production_appended": False, "automatic_retry": False, "partial_evidence": "PRESERVED"})
        except BaseException as persistence:
            raise ValueError("OWNER_FINAL_VERIFICATION_BLOCKED:EVIDENCE_WRITE_" + type(persistence).__name__) from None
        # Provider exceptions can embed signed bearer URLs. Do not print their
        # messages or chained tracebacks to the terminal or evidence receipt.
        raise ValueError("OWNER_FINAL_VERIFICATION_BLOCKED:" + type(error).__name__) from None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approved-repo", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--directory", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--authority-only", action="store_true")
    p.add_argument("--release-locator", type=Path)
    p.add_argument("--owner-performs-network", action="store_true", required=True)
    a = p.parse_args()
    sys.path.insert(0, str(a.approved_repo.resolve()))
    c = load_companion()
    c.require(a.approved_repo.resolve() == c.runtime.ROOT.resolve(), "ORIGINAL_OPERATOR_IMPORTS")
    ledger = c.campaign.Ledger(a.ledger)
    if a.authority_only:
        c.require(a.release_locator is not None, "SOURCE_RELEASE_LOCATOR_REQUIRED")
        result = acquire_authority(ledger, c.read(a.release_locator), a.output, owner_performs_network=a.owner_performs_network)
    else:
        c.require(a.directory is not None, "CONTINUATION_DIRECTORY_REQUIRED")
        route = c.Continuation(a.directory, ledger)
        result = verify(route, a.output, owner_performs_network=a.owner_performs_network)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
