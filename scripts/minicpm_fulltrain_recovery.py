"""Source-reviewed recovery, one SDK submission, bounded native-start handoff.

Use the SAME historical Operator journal. No automatic refund, fourth campaign,
retry, cancellation, science change, or inference in any preparation command.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
from unittest.mock import patch

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.pilot.artifacts import read, write, write_bytes, safe, sha, import_archive
from safeshift.pilot.contract import digest, json_bytes
from safeshift.kaggle_handoff import lock, private_root
from safeshift.fulltrain import contract, minicpm_release as a, minicpm_recovery as recovery, minicpm_ui as ui
from safeshift.fulltrain.minicpm_execution import MARKER
from scripts import minicpm_fulltrain_operator as old

KNOWN = (("minicpm-v2-journal", "minicpm-v2-mirror"),
         ("minicpm-v2-2-journal", "minicpm-v2-2-mirror"), ("minicpm-v3-journal", "minicpm-v3-mirror"))
EXTENSIONS = {"RECOVERY_RESERVED", "RECOVERY_PUBLISH_INTENT", "RECOVERY_PUBLISHED", "CODEX_PUSH_INTENT",
              "CODEX_SUBMITTED", "CODEX_NATIVE_HANDOFF", "CODEX_OBSERVATION", "RECOVERY_COLLECTED",
              "PENDING_RESERVED", "PENDING_PUBLISH_INTENT", "PENDING_PUBLISHED", "PENDING_PACKAGE_RECOVERED"}


def inspect_journals():
    """Read-only conservative accounting; never treats local evidence as rights."""
    rows, reserved = [], {"calls": 0, "jobs": 0, "gpu_seconds": 0}
    for campaign, (root_name, mirror_name) in zip(recovery.CAMPAIGNS, KNOWN):
        journal = old.Journal(ROOT / "data/processed" / root_name, ROOT / "data/processed" / mirror_name)
        events = journal.events()
        registration = read(ROOT / "data/processed/minicpm-release-registrations" / (campaign + ".json"))
        initial = events[0]["payload"]
        require(registration == {"grant_sha256": initial["grant_sha256"], "host": old.host(),
            "root": journal.root.relative_to(ROOT).as_posix(), "mirror": journal.mirror.relative_to(ROOT).as_posix()},
                "MINICPM_RECOVERY_REGISTRATION_OR_ROOT_DRIFT")
        require(all(e["kind"] in {"REGISTERED", "RESERVED", "PUBLISH_INTENT", "PUBLISHED"} | EXTENSIONS for e in events),
                "MINICPM_RECOVERY_UNKNOWN_EVENT_STOP")
        tickets = [e["payload"] for e in events if e["kind"] == "RESERVED"]
        require(len(tickets) == 1, "MINICPM_RECOVERY_EXACT_OLD_RESERVATION")
        item = tickets[0]
        require(item["ticket"]["payload"]["grant_sha256"] == initial["grant_sha256"]
            and item["ticket"]["payload"]["value_sha256"] == digest(item["value"])
            and item["value"]["job"] == "nguynanhtn/safeshift-minicpm-" + campaign + "-1",
                "MINICPM_RECOVERY_OLD_PACKAGE_BINDING")
        ticket = item["ticket"]["payload"]
        require(ticket["reserved_before"] == {"calls": 0, "jobs": 0, "gpu_seconds": 0}
            and ticket["reserved_after"] == {"calls": item["value"]["request"]["plan"]["max_calls"], "jobs": 1,
                "gpu_seconds": 2 * item["value"]["request"]["plan"]["max_seconds"]}, "MINICPM_OLD_NO_REFUND_ACCOUNTING")
        for field in reserved:
            reserved[field] += ticket["reserved_after"][field]
        # Only a prefix of the old publication sequence is allowed.
        historical = [e["kind"] for e in events if e["kind"] not in EXTENSIONS]
        require(historical in (["REGISTERED", "RESERVED"], ["REGISTERED", "RESERVED", "PUBLISH_INTENT"],
            ["REGISTERED", "RESERVED", "PUBLISH_INTENT", "PUBLISHED"]), "MINICPM_OLD_JOURNAL_SEQUENCE")
        for e in events[2:]:
            if e["kind"] in ("PUBLISH_INTENT", "PUBLISHED"):
                require(e["payload"]["ticket_sha256"] == digest(item["ticket"]), "MINICPM_OLD_PUBLICATION_TICKET")
        rows.append({"campaign_id": campaign, "root": journal.root.relative_to(ROOT).as_posix(),
            "mirror": journal.mirror.relative_to(ROOT).as_posix(),
            "head_sha256": next((e["previous"] for e in events if e["kind"] in EXTENSIONS), digest(events[-1])),
            "grant_locator": initial["locator"], "ticket": item["ticket"], "job": item["value"]["job"],
            "publication": historical[-1], "disposition": "UNVERIFIED", "evidence_sha256": None})
    return {"schema": recovery.SCHEMA, "journals": rows, "reserved": reserved, "prior_jobs": [],
        "directive": {"comment_id": 6914854993, "body_sha256": None}, "budget_amendment": None}


def account_jobs(client):
    """Complete bounded Owner inventory, never a search result or guessed slug."""
    from scripts.submit_internvl_v2 import bounded_http
    owned, tokens, token = set(), set(), None
    with bounded_http():
        for page in range(1, 17):
            result = client.kernels_list_with_response(mine=True, page_size=100, page_token=token,
                page=None if token else page)
            refs = [k.ref for k in result.kernels]
            require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(type(ref) is str and ref.startswith("nguynanhtn/") for ref in refs), "MINICPM_RECOVERY_OWNER_INVENTORY")
            owned.update(refs)
            token = result.next_page_token
            if not token and len(refs) < 100:
                return owned
            require(token is None or type(token) is str and (not token or len(token) <= 4096 and token not in tokens),
                    "MINICPM_RECOVERY_INVENTORY_TOKEN")
            if token:
                tokens.add(token)
    raise ValueError("MINICPM_RECOVERY_INCOMPLETE_PROVIDER_INVENTORY")


def authenticate_old(row):
    """Verify original source/reviews at its frozen Git bytes, not changed HEAD."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        ref = "507e9817b91054fa7af324c6a915c35d56b5acf1"
        names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", ref], cwd=ROOT, text=True).splitlines()
        for name in set(contract.sources()).intersection(names):
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(subprocess.check_output(["git", "show", ref + ":" + name], cwd=ROOT))
        grant = a.load(row["grant_locator"], repo=repo, collection=True)
    a.verify_signature(grant["public_key"], row["ticket"]["payload"], row["ticket"]["signature"])
    require(grant["campaign_id"] == row["campaign_id"]
        and row["ticket"]["payload"]["grant_sha256"] == digest(grant), "MINICPM_OLD_AUTHENTIC_GRANT_BINDING")
    return grant


def observe_predecessor(client, row, destination):
    from scripts.reconcile_train3763_manual import observe_kernel, output_inventory
    from scripts.minicpm_fulltrain_transport import download_selected
    from scripts.submit_internvl_v2 import bounded_http
    journal = old.Journal(safe(ROOT, row["root"]), safe(ROOT, row["mirror"]))
    item = next(e["payload"] for e in journal.events() if e["kind"] == "RESERVED")
    pkg = safe(ROOT, item["package"])
    value = item["value"]
    nb = read(pkg / "notebook.ipynb")
    from safeshift.internvl3763_operator import code_hash
    require(code_hash(nb) == row["ticket"]["payload"]["notebook_code_sha256"], "MINICPM_OLD_SIGNED_NOTEBOOK")
    with bounded_http():
        state = str(client.kernels_status(row["job"] + "/1").status).split(".")[-1]
    require(state in ("COMPLETE", "ERROR", "CANCELLED"), "MINICPM_PREDECESSOR_RUNNING_OR_UNKNOWN")
    proof = observe_kernel(client, row["job"], 1, nb, value["input_sources"], expected_state=state)
    write(destination / "provider.json", proof)
    selected, log = output_inventory(client, row["job"], 1)
    write_bytes(destination / "provider.log", log.encode())
    supervisors = [n for n in selected if re.fullmatch(r"minicpm-fulltrain/supervision/[0-9a-f]{32}\.zip", n)]
    release, claims = None, None
    if selected:
        require(len(supervisors) == 1 and set(selected) == {supervisors[0], supervisors[0] + ".sha256.json"},
                "MINICPM_PREDECESSOR_ATTEMPT_PARTIAL_OR_UNKNOWN_ZIP")
        limits = {supervisors[0]: 64 * 2**20, supervisors[0] + ".sha256.json": 4096}
        download_selected(selected, limits, destination / "outputs")
        archive = destination / "outputs" / supervisors[0]
        ui.pair(archive)
        with tempfile.TemporaryDirectory() as tmp:
            tree = import_archive(archive, Path(tmp) / "supervisor")
            require(read(tree / "request.json") == value["request"], "MINICPM_OLD_SUPERVISOR_REQUEST")
            capability = read(tree / "capability.json")
            require(capability == {"locator": row["grant_locator"], "ticket": row["ticket"]},
                    "MINICPM_OLD_SUPERVISOR_TICKET")
            release, claims = read(tree / "release.json"), read(tree / "claims.json")
            # Preserve the actual child error, not just SUPERVISED_CHILD_FAILURE.
            failure = tree / release["last_stage"] / "failure.json"
            if failure.is_file():
                release = {**release, "failure": read(failure)}
    receipt = recovery.failure_receipt(value, row["ticket"], proof, log, release=release, claims=claims,
                                       inventory_complete=True)
    write(destination / "failed-pre-native.json", receipt)
    return receipt


def reconcile(destination):
    """Read-only provider reconciliation; originals and journal bytes untouched."""
    destination = private_root(destination)
    destination.mkdir(parents=True, exist_ok=False)
    snapshot = inspect_journals()
    from safeshift.internvl3763_operator import api
    client = api()
    owned = account_jobs(client)
    expected = {j["job"] for j in snapshot["journals"]}
    require({j for j in owned if j.startswith("nguynanhtn/safeshift-minicpm-mcpm4-train3763")}
        <= expected, "MINICPM_UNKNOWN_JOB_OR_DUPLICATE_STOP")
    from scripts.submit_internvl_v2 import bounded_http
    with bounded_http():
        q = client.quota_view().gpu_quota
        quota = {k: int(getattr(q, f).total_seconds()) for k, f in
            (("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
    require(quota["reserved"] == 0, "MINICPM_OUTSTANDING_VM_STOP")
    write(destination / "account.json", {"quota": quota, "owned_sha256": digest(sorted(owned)), "observed_unix": int(time.time())})
    directive = a.github_get("/issues/comments/6914854993")
    require(directive["user"]["id"] == a.OWNER_ID and directive["user"]["login"] == a.OWNER
        and directive["issue_url"] == a.API + "/issues/198", "MINICPM_OWNER_DIRECTIVE_REQUIRED")
    snapshot["directive"]["body_sha256"] = hashlib.sha256(directive["body"].encode()).hexdigest()
    for i, row in enumerate(snapshot["journals"]):
        authenticate_old(row)
        directory = destination / str(i + 1)
        directory.mkdir()
        if row["job"] in owned:
            receipt = observe_predecessor(client, row, directory)
            row["disposition"] = "FAILED_PRE_NATIVE"
            state = receipt["provider"]["state"]
        else:
            require(row["publication"] == "RESERVED", "MINICPM_PUBLISHED_HISTORICAL_JOB_MISSING_RECONCILE_READ_ONLY")
            require(time.time() >= row["ticket"]["payload"]["start_before_unix"], "MINICPM_ABSENT_TICKET_NOT_EXPIRED")
            receipt = {"status": "EXPIRED_UNPUBLISHED", "job": row["job"], "refund": False,
                "owned_sha256": digest(sorted(owned)), "ticket_sha256": digest(row["ticket"]), "observed_unix": int(time.time())}
            write(directory / "absent-expired.json", receipt)
            row["disposition"], state = "EXPIRED_UNPUBLISHED", "ABSENT_EXPIRED"
        row["evidence_sha256"] = digest(receipt)
        snapshot["prior_jobs"].append({"job": row["job"], "version": 1, "state": state, "evidence_sha256": digest(receipt)})
    write(destination / "snapshot.json", snapshot)
    # No grant, release, journal event or rights are issued by this command.
    return {"status": "RECONCILED_NOT_RELEASED", "reserved": snapshot["reserved"],
        "project_gpu_seconds": recovery.PROJECT_GPU_SECONDS,
        "budget_status": "BLOCKED" if snapshot["reserved"]["gpu_seconds"] >= recovery.PROJECT_GPU_SECONDS else "REVIEW_REQUIRED"}


class RecoveryOperator:
    def __init__(self):
        self.journal = old.Journal(ROOT / "data/processed/minicpm-v3-journal", ROOT / "data/processed/minicpm-v3-mirror")

    def state(self):
        baseline = inspect_journals()
        events = self.journal.events()
        additions = [e for e in events if e["kind"] in EXTENSIONS]
        reservations = [e["payload"] for e in additions if e["kind"] == "RECOVERY_RESERVED"]
        require(len(reservations) == 1 and additions[0]["kind"] == "RECOVERY_RESERVED", "MINICPM_EXACT_ONE_RECOVERY_RESERVATION")
        item = reservations[0]
        grant = a.load(item["locator"], collection=True)
        require(grant["schema"] == a.RECOVERY_SCHEMA and grant["operator_host_sha256"] == old.host(), "MINICPM_RECOVERY_OPERATOR")
        require(baseline["journals"] == [{**j, "disposition": "UNVERIFIED", "evidence_sha256": None}
            for j in grant["recovery"]["journals"]], "MINICPM_RECOVERY_BASELINE_CHANGED")
        a.verify_ticket(grant, item["ticket"], item["value"], collection=True)
        require(item["ticket"]["payload"]["previous_event_sha256"] == additions[0]["previous"], "MINICPM_RECOVERY_CHAIN_BINDING")
        order = [e["kind"] for e in additions]
        main = [k for k in order if k not in ("CODEX_OBSERVATION", "CODEX_NATIVE_HANDOFF")]
        sequence = ["RECOVERY_RESERVED", "RECOVERY_PUBLISH_INTENT", "RECOVERY_PUBLISHED", "CODEX_PUSH_INTENT", "CODEX_SUBMITTED"]
        require(main == sequence[:len(main)] and len(main) <= len(sequence)
            and order.count("CODEX_NATIVE_HANDOFF") <= 1, "MINICPM_RECOVERY_SEQUENCE_NO_REPLAY")
        for e in additions[1:]:
            require(e["payload"]["ticket_sha256"] == digest(item["ticket"]), "MINICPM_RECOVERY_EVENT_TICKET")
        return grant, item, order

    def stage(self, locator, value, private_key, destination, reconciliation):
        with lock(self.journal.root):
            baseline = inspect_journals()
            require(not any(e["kind"] in EXTENSIONS for e in self.journal.events()), "MINICPM_RECOVERY_ALREADY_STAGED")
            grant = a.load(locator)
            require(grant["schema"] == a.RECOVERY_SCHEMA and grant["operator_host_sha256"] == old.host(), "MINICPM_RECOVERY_RELEASE_REQUIRED")
            old.clean_source(grant)
            fresh = read(reconciliation / "snapshot.json")
            require(fresh == grant["recovery"], "MINICPM_REVIEWED_RECONCILIATION_REQUIRED")
            require(baseline["journals"] == [{**j, "disposition": "UNVERIFIED", "evidence_sha256": None} for j in fresh["journals"]]
                and baseline["reserved"] == fresh["reserved"], "MINICPM_RECOVERY_ALL_JOURNAL_HEADS")
            recovery.mounted_inputs(value)
            a.bind(grant, value)
            number = fresh["reserved"]["jobs"] + 1
            require(value["job"] == "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-" + str(number),
                    "MINICPM_RECOVERY_EXACT_JOB_NUMBER")
            from safeshift.internvl3763_operator import api, code_hash
            client = api()
            evidence = live_provider(client, grant, value, reconciliation)
            from scripts.generate_minicpm_fulltrain_notebook import notebook
            nb = notebook(grant["runtime_commit"], capsule_sha256=digest(value), release_locator=locator, release_version=3)
            before, plan = fresh["reserved"], value["request"]["plan"]
            payload = {"schema": a.RECOVERY_TICKET, "grant_sha256": digest(grant), "value_sha256": digest(value),
                "capsule_sha256": digest(value), "notebook_code_sha256": code_hash(nb), "number": number,
                "previous_event_sha256": digest(self.journal.events()[-1]), "reserved_before": before,
                "reserved_after": {"calls": before["calls"] + plan["max_calls"], "jobs": before["jobs"] + 1,
                    "gpu_seconds": before["gpu_seconds"] + 2 * plan["max_seconds"]}, "issued_unix": int(time.time()),
                "start_before_unix": evidence["observed_unix"] + grant["provider_max_age_seconds"], "provider": evidence,
                "sizing": {"calls": plan["max_calls"], "seconds": plan["max_seconds"]}}
            envelope = old.sign(private_key, grant["public_key"], payload)
            a.verify_ticket(grant, envelope, value)
            destination = private_root(destination)
            require(not destination.exists(), "MINICPM_RECOVERY_PACKAGE_CREATE_ONLY")
            item = {"locator": locator, "ticket": envelope, "value": value,
                "package": destination.relative_to(ROOT).as_posix(), "reconciliation": reconciliation.relative_to(ROOT).as_posix()}
            self.journal.append("RECOVERY_RESERVED", item)
            ui.package(value, [], destination, lambda _: nb)
            write(destination / "dataset" / MARKER, envelope)
            write(destination / "release.json", {"status": "RECOVERY_RESERVED", "locator": locator, "ticket": envelope})
            return {"status": "RECOVERY_RESERVED_NOT_SUBMITTED", "ticket_sha256": digest(envelope)}

    def publish(self, verify_only=False):
        from safeshift.internvl3763_operator import api
        from scripts.submit_internvl_v2 import bounded_http
        with lock(self.journal.root):
            grant, item, order = self.state()
            require("RECOVERY_PUBLISHED" not in order and "CODEX_PUSH_INTENT" not in order, "MINICPM_RECOVERY_NO_REPUBLISH")
            old.clean_source(grant)
            check_window(grant, item)
            pkg, client = safe(ROOT, item["package"]), api()
            verify_package(grant, item, pkg)
            live_provider(client, grant, item["value"], safe(ROOT, item["reconciliation"]))
            if not verify_only:
                require("RECOVERY_PUBLISH_INTENT" not in order, "MINICPM_RECOVERY_UPLOAD_UNKNOWN_VERIFY_ONLY")
                upload = pkg / "private-upload"
                upload.mkdir(exist_ok=False)
                for path in (pkg / "dataset").iterdir():
                    old._copy(path, upload / path.name)
                old._copy(pkg / "dataset-metadata.json", upload / "dataset-metadata.json")
                self.journal.append("RECOVERY_PUBLISH_INTENT", {"ticket_sha256": digest(item["ticket"])})
                with bounded_http(), patch.object(client, "with_retry", lambda fn, *args, **kwargs: fn):
                    result = client.dataset_create_new(str(upload), public=False, quiet=True, convert_to_csv=False, dir_mode="skip")
                old.check_create_response(result)
            else:
                require("RECOVERY_PUBLISH_INTENT" in order, "MINICPM_RECOVERY_PUBLISH_INTENT_REQUIRED")
            proof = old.verify_published_capsule(client, item["value"], item["ticket"], pkg)
            check_window(grant, item)
            self.journal.append("RECOVERY_PUBLISHED", {"ticket_sha256": digest(item["ticket"]), "proof": proof})
            return {"status": "RECOVERY_PUBLISHED_NOT_SUBMITTED"}

    def submit_once(self):
        from safeshift.internvl3763_operator import api
        from scripts.submit_internvl_v2 import bounded_http
        with lock(self.journal.root):
            grant, item, order = self.state()
            require("RECOVERY_PUBLISHED" in order and "CODEX_PUSH_INTENT" not in order,
                    "MINICPM_CODEX_SUBMIT_ONCE_UNKNOWN_NO_RETRY")
            old.clean_source(grant)
            check_window(grant, item)
            pkg, value, client = safe(ROOT, item["package"]), item["value"], api()
            verify_package(grant, item, pkg)
            old.verify_published_capsule(client, value, item["ticket"], pkg)
            evidence = live_provider(client, grant, value, safe(ROOT, item["reconciliation"]))
            stage = pkg / "submission"
            stage.mkdir(exist_ok=False)
            write_bytes(stage / "notebook.ipynb", (pkg / "notebook.ipynb").read_bytes())
            write(stage / "kernel-metadata.json", {"id": value["job"], "title": value["job"].split("/")[1],
                "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
                "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
                **value["input_sources"], "competition_sources": [], "model_sources": []})
            # Re-authenticate after slow provider checks. The intent is durable
            # BEFORE the sole mutating call and survives an ambiguous timeout.
            require(a.load(item["locator"]) == grant, "MINICPM_RECOVERY_AUTHORITY_CHANGED")
            check_window(grant, item)
            self.journal.append("CODEX_PUSH_INTENT", {"ticket_sha256": digest(item["ticket"]),
                "provider_sha256": digest(evidence), "notebook_sha256": sha(pkg / "notebook.ipynb")})
            with bounded_http(), patch.object(client, "with_retry", lambda fn, *args, **kwargs: fn):
                response = client.kernels_push(str(stage), timeout=str(value["request"]["plan"]["max_seconds"]), acc="NvidiaTeslaT4")
            returned = response.to_dict()
            write(stage / "submit-return.json", returned)
            require(returned.get("error") in (None, "") and type(returned.get("versionNumber")) is int
                and returned["versionNumber"] == 1 and returned.get("ref") == value["job"]
                and type(returned.get("kernelId")) is int and returned["kernelId"] > 0
                and all(not returned.get(k) for k in ("invalidTags", "invalidDatasetSources", "invalidKernelSources",
                    "invalidCompetitionSources", "invalidModelSources")),
                    "MINICPM_SUBMIT_RETURN_AMBIGUOUS_RECONCILE_NO_RETRY")
            self.journal.append("CODEX_SUBMITTED", {"ticket_sha256": digest(item["ticket"]), "response_sha256": digest(returned)})
            return {"status": "SUBMITTED_UNVERIFIED", "job": value["job"], "version": 1}

    def observe(self, destination):
        """ONE observation; no sleep, cancel, submit, terminal wait or background AI."""
        from safeshift.internvl3763_operator import api, code_hash, verify_kernel_metadata_inputs
        from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
        from scripts.reconcile_train3763_manual import output_inventory
        from scripts.submit_internvl_v2 import bounded_http
        with lock(self.journal.root):
            grant, item, order = self.state()
            require("CODEX_PUSH_INTENT" in order and "CODEX_NATIVE_HANDOFF" not in order, "MINICPM_OBSERVE_EXACT_LAUNCH_ONCE")
            client, value = api(), item["value"]
            query = ApiGetKernelRequest()
            query.user_name, query.kernel_slug = value["job"].split("/")
            with bounded_http():
                # Latest must still be v1. No status-only inference claim.
                with client.build_kaggle_client() as remote:
                    remote_value = remote.kernels.kernels_api_client.get_kernel(query)
                state = str(client.kernels_status(value["job"] + "/1").status).split(".")[-1]
                q = client.quota_view().gpu_quota
                quota = {k: int(getattr(q, f).total_seconds()) for k, f in
                    (("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
            meta = remote_value.metadata
            require(meta is not None and meta.ref == value["job"] and meta.is_private is True
                and type(meta.current_version_number) is int and meta.current_version_number == 1
                and type(meta.id) is int and meta.id > 0 and remote_value.blob is not None,
                    "MINICPM_LIVE_REMOTE_ID_VERSION_PRIVATE")
            require(code_hash(a.strict_json(remote_value.blob.source)) == item["ticket"]["payload"]["notebook_code_sha256"],
                    "MINICPM_LIVE_REMOTE_SOURCE")
            verify_kernel_metadata_inputs(meta, value["input_sources"])
            _, log = output_inventory(client, value["job"], 1)
            proof = recovery.live_proof(log, value, item["ticket"])
            with bounded_http():
                state = str(client.kernels_status(value["job"] + "/1").status).split(".")[-1]
            require(state in ("QUEUED", "RUNNING", "COMPLETE", "ERROR", "CANCELLED"), "MINICPM_LIVE_UNKNOWN_STATE")
            status = "PASS_NATIVE_STARTED_JOB_RUNNING" if state == "RUNNING" and proof["status"] == "NATIVE_STARTED" else (
                "RUNNING_UNVERIFIED" if state in ("QUEUED", "RUNNING") else "TERMINAL_RECONCILIATION_REQUIRED")
            pkg = safe(ROOT, item["package"])
            result = {"status": status, "job": value["job"], "url": "https://www.kaggle.com/code/" + value["job"],
                "version": 1, "kernel_id": meta.id, "provider_state": state, "runtime_commit": grant["runtime_commit"],
                "merged_sha": grant["merged_sha"], "notebook_sha256": sha(pkg / "notebook.ipynb"),
                "capsule_ref": value["capsule_ref"], "capsule_sha256": digest(value), "input_sources": value["input_sources"],
                "ticket_sha256": digest(item["ticket"]), "grant_locator": item["locator"],
                "reserved": item["ticket"]["payload"]["reserved_after"], "calls": value["request"]["plan"]["max_calls"],
                "seconds": value["request"]["plan"]["max_seconds"], "physical_gpus": 2, "quota": quota,
                "proof": proof, "journal": str(self.journal.root.relative_to(ROOT).as_posix()),
                "journal_head_before": digest(self.journal.events()[-1]), "kernel_action": "LEAVE_RUNNING_DO_NOT_CANCEL",
                "operator_action": "RESUME_SAME_HISTORICAL_OPERATOR_SESSION", "scientific_qualified": False}
            destination = private_root(destination)
            destination.mkdir(parents=True, exist_ok=False)
            write_bytes(destination / "provider.log", log.encode())
            self.journal.append("CODEX_NATIVE_HANDOFF" if status == "PASS_NATIVE_STARTED_JOB_RUNNING" else "CODEX_OBSERVATION",
                {"ticket_sha256": digest(item["ticket"]), "proof_sha256": digest(result),
                 "directory": destination.relative_to(ROOT).as_posix()})
            result["journal_head_after"] = digest(self.journal.events()[-1])
            write(destination / "handoff.json", result)
            return result


def check_window(grant, item):
    a.verify_ticket(grant, item["ticket"], item["value"])
    require(time.time() < item["ticket"]["payload"]["start_before_unix"], "MINICPM_RECOVERY_EXPIRED_NO_TICKET_REUSE")


def verify_package(grant, item, pkg):
    from scripts.generate_minicpm_fulltrain_notebook import notebook
    expected = notebook(grant["runtime_commit"], capsule_sha256=digest(item["value"]), release_locator=item["locator"], release_version=3)
    require(read(pkg / "notebook.ipynb") == expected, "MINICPM_RECOVERY_EXACT_FINAL_NOTEBOOK")
    require(ui.verify_capsule(pkg / "dataset", digest(item["value"]), release_ticket=True) == item["value"]
        and read(pkg / "dataset" / MARKER) == item["ticket"], "MINICPM_RECOVERY_EXACT_CAPSULE_TICKET")


class RecoveredSerialJournal(old.Journal):
    """Antigravity continues the same journal using PR198 collection/serial UI.

    This class has no API submit method. The sole Codex POST remains guarded by
    RecoveryOperator; later jobs are signed pending-only Owner UI handoffs.
    """
    def __init__(self):
        super().__init__(ROOT / "data/processed/minicpm-v3-journal", ROOT / "data/processed/minicpm-v3-mirror")

    def append(self, kind, payload):
        mapped = {"RESERVED": "PENDING_RESERVED", "PUBLISH_INTENT": "PENDING_PUBLISH_INTENT",
            "PUBLISHED": "PENDING_PUBLISHED", "COLLECTED": "RECOVERY_COLLECTED", "PACKAGE_RECOVERED": "PENDING_PACKAGE_RECOVERED"}
        super().append(mapped.get(kind, kind), payload)

    def first(self, events):
        return next(e["payload"] for e in events if e["kind"] == "RECOVERY_RESERVED")

    def stage_initial(self, events):
        return self.first(events)["value"]

    def release_locator(self, events):
        return self.first(events)["locator"]

    def state(self):
        baseline, events = inspect_journals(), self.events()
        first = self.first(events)
        grant = a.load(first["locator"], collection=True)
        require(grant["schema"] == a.RECOVERY_SCHEMA and grant["operator_host_sha256"] == old.host()
            and baseline["journals"] == [{**j, "disposition": "UNVERIFIED", "evidence_sha256": None}
                for j in grant["recovery"]["journals"]], "MINICPM_SERIAL_RECOVERY_BASELINE")
        reserved, active, completed, pushes = grant["recovery"]["reserved"], None, [], 0
        for event in events:
            kind, payload = event["kind"], event["payload"]
            if kind not in EXTENSIONS:
                continue
            if kind in ("RECOVERY_RESERVED", "PENDING_RESERVED"):
                require(active is None and (kind == "RECOVERY_RESERVED") == (not completed)
                    and payload["ticket"]["payload"]["reserved_before"] == reserved
                    and payload["ticket"]["payload"]["previous_event_sha256"] == event["previous"],
                        "MINICPM_PENDING_SERIAL_RESERVATION")
                a.verify_ticket(grant, payload["ticket"], payload["value"], collection=True)
                active = deepcopy(payload)
                reserved = payload["ticket"]["payload"]["reserved_after"]
                continue
            require(active is not None and payload["ticket_sha256"] == digest(active["ticket"]),
                    "MINICPM_PENDING_EVENT_EXACT_ACTIVE_TICKET")
            if kind in ("RECOVERY_PUBLISH_INTENT", "PENDING_PUBLISH_INTENT"):
                require("publish_intent" not in active, "MINICPM_PENDING_DUPLICATE_PUBLICATION")
                active["publish_intent"] = payload
            elif kind in ("RECOVERY_PUBLISHED", "PENDING_PUBLISHED"):
                require("publish_intent" in active and "published" not in active, "MINICPM_PENDING_PUBLICATION_SEQUENCE")
                active["published"] = payload
            elif kind == "PENDING_PACKAGE_RECOVERED":
                require("publish_intent" not in active, "MINICPM_PENDING_RECOVERY_BEFORE_UPLOAD_ONLY")
                active["package"] = payload["package"]
            elif kind == "CODEX_PUSH_INTENT":
                require(not completed and "published" in active and pushes == 0, "MINICPM_SINGLE_CODEX_PUSH_ONLY")
                pushes += 1
                active["push_intent"] = payload
            elif kind == "CODEX_SUBMITTED":
                require("push_intent" in active and "submitted" not in active, "MINICPM_SUBMITTED_SEQUENCE")
                active["submitted"] = payload
            elif kind in ("CODEX_OBSERVATION", "CODEX_NATIVE_HANDOFF"):
                require("push_intent" in active, "MINICPM_OBSERVE_AFTER_PUSH_ONLY")
            elif kind == "RECOVERY_COLLECTED":
                require("published" in active, "MINICPM_COLLECT_PUBLISHED_ONLY")
                active["collection"] = payload
                completed.append(active)
                active = None
        return grant, events, reserved, active, completed

    def observe_provider(self, client, grant, value, prior):
        first = self.first(self.events())
        _, _, _, _, completed = self.state()
        require(len(prior) == len(completed), "MINICPM_ALL_PENDING_PREDECESSORS")
        return live_provider(client, grant, value, safe(ROOT, first["reconciliation"]), recovered=completed)


def live_provider(client, grant, value, reconciliation, *, recovered=()):
    """Re-observe old failures and all account jobs; reuse V2 Input/quota gates."""
    require(read(reconciliation / "snapshot.json") == grant["recovery"], "MINICPM_RECOVERY_RECONCILIATION_CUSTODY")
    owned = account_jobs(client)
    expected = {j["job"] for j in grant["recovery"]["journals"] if j["disposition"] == "FAILED_PRE_NATIVE"}
    expected.update(item["value"]["job"] for item in recovered)
    require(value["job"] not in owned and {j for j in owned if j.startswith(
        "nguynanhtn/safeshift-minicpm-mcpm4-train3763")} == expected, "MINICPM_RECOVERY_DUPLICATE_OR_UNKNOWN_JOB")
    with tempfile.TemporaryDirectory(dir=ROOT / "data/processed") as tmp:
        for i, row in enumerate(grant["recovery"]["journals"]):
            if row["disposition"] == "FAILED_PRE_NATIVE":
                receipt = observe_predecessor(client, row, Path(tmp) / str(i))
                require(digest(receipt) == row["evidence_sha256"], "MINICPM_RECOVERY_PREDECESSOR_EVIDENCE_CHANGED")
            else:
                require(row["job"] not in owned and time.time() >= row["ticket"]["payload"]["start_before_unix"],
                        "MINICPM_RECOVERY_EXPIRED_ABSENCE_CHANGED")
    # Provider's V2 inventory is scoped to this campaign. Present the terminal
    # original v3 job only when it genuinely exists; no invented predecessor.
    prior = []
    for row in grant["recovery"]["journals"][-1:]:
        if row["job"] in owned:
            j = old.Journal(safe(ROOT, row["root"]), safe(ROOT, row["mirror"]))
            original = next(e["payload"] for e in j.events() if e["kind"] == "RESERVED")
            prior.append({"job": row["job"], "notebook": read(safe(ROOT, original["package"] + "/notebook.ipynb")),
                "input_sources": original["value"]["input_sources"], "kernel_id": read(reconciliation / "3/provider.json")["kernel_id"],
                "state": grant["recovery"]["prior_jobs"][2]["state"]})
    recovered_proofs = []
    for item in recovered:
        directory = safe(ROOT, item["collection"]["directory"])
        proof = read(directory / "provider.json")
        row = {"job": item["value"]["job"], "notebook": read(safe(ROOT, item["package"] + "/notebook.ipynb")),
            "input_sources": item["value"]["input_sources"], "kernel_id": proof["kernel_id"]}
        prior.append(row)
        recovered_proofs.append({"job": row["job"], "version": 1, "state": "COMPLETE", "kernel_id": proof["kernel_id"],
            "ticket": item["ticket"]})
    evidence = old.provider(client, grant, value, prior)
    evidence["prior_jobs"] = [*deepcopy(grant["recovery"]["prior_jobs"]), *recovered_proofs]
    require(evidence["quota"]["total"] - evidence["quota"]["used"] >= 2 * value["request"]["plan"]["max_seconds"],
            "MINICPM_RECOVERY_LIVE_QUOTA")
    return evidence


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("inspect")
    spec = sub.add_parser("prepare-spec")
    spec.add_argument("--initial-spec", type=Path, required=True)
    spec.add_argument("--calls", type=int, required=True); spec.add_argument("--seconds", type=int, required=True)
    spec.add_argument("--output", type=Path, required=True)
    template = sub.add_parser("release-template")
    for name in ("spec", "snapshot", "output"):
        template.add_argument("--" + name, type=Path, required=True)
    template.add_argument("--runtime-ref", required=True)
    template.add_argument("--implementation-pr", required=True, type=int)
    r = sub.add_parser("reconcile"); r.add_argument("--output", type=Path, required=True)
    s = sub.add_parser("stage")
    for name in ("locator", "spec", "private-key", "output", "reconciliation"):
        s.add_argument("--" + name, type=Path, required=True)
    pub = sub.add_parser("publish"); pub.add_argument("--verify-only", action="store_true")
    sub.add_parser("submit-once")
    obs = sub.add_parser("observe"); obs.add_argument("--output", type=Path, required=True)
    collect = sub.add_parser("collect"); collect.add_argument("--output", type=Path, required=True)
    pending = sub.add_parser("stage-pending")
    pending.add_argument("--private-key", type=Path, required=True); pending.add_argument("--output", type=Path, required=True)
    pub_pending = sub.add_parser("publish-pending"); pub_pending.add_argument("--verify-only", action="store_true")
    args = p.parse_args()
    if args.action == "inspect":
        snapshot = inspect_journals()
        result = {"status": "LOCAL_ONLY_UNAUTHENTICATED", "reserved": snapshot["reserved"],
            "project_gpu_seconds": recovery.PROJECT_GPU_SECONDS, "billing": "NOT_OBSERVED",
            "journal_heads": [j["head_sha256"] for j in snapshot["journals"]]}
    elif args.action == "prepare-spec":
        initial = read(args.initial_spec)
        require(not initial["request"]["history"] and not initial["ancestors"], "MINICPM_PRE_NATIVE_HISTORY_ONLY")
        job = "nguynanhtn/safeshift-minicpm-mcpm4-train3763-v3-4"
        value = ui.initial(initial["cohort"], initial["request"]["projection_sha256"], initial["request"]["resource_policy"],
            checkpoint_marker_sha256=initial["request"]["checkpoint_marker_sha256"],
            run_id="mcpm4-train3763-v3-run-4", attempt_id="mcpm4-train3763-v3-attempt-4", job=job,
            capsule_ref="nguynanhtn/safeshift-minicpm-capsule-mcpm4-train3763-v3-4/1",
            max_calls=args.calls, max_seconds=args.seconds, nested_mounts=True)
        recovery.mounted_inputs(value)
        write(args.output, value)
        result = {"status": "METADATA_PREPARATION_NOT_AUTHORITY", "input_mounts": recovery.mounted_inputs(value)}
    elif args.action == "release-template":
        proposal = old.release_template(read(args.spec), args.runtime_ref)
        proposal.update(schema=a.RECOVERY_SCHEMA, implementation_pr=args.implementation_pr,
            recovery=read(args.snapshot))
        write(args.output, proposal)
        result = {"status": "UNSIGNED_PROPOSAL_NOT_AUTHORITY"}
    elif args.action == "reconcile":
        result = reconcile(args.output)
    elif args.action == "stage":
        result = RecoveryOperator().stage(read(args.locator), read(args.spec), args.private_key, args.output, args.reconciliation)
    elif args.action == "publish":
        result = RecoveryOperator().publish(args.verify_only)
    elif args.action == "submit-once":
        result = RecoveryOperator().submit_once()
    elif args.action == "collect":
        result = RecoveredSerialJournal().collect(args.output)
    elif args.action == "stage-pending":
        result = {"package": str(RecoveredSerialJournal().stage(args.private_key, args.output))}
    elif args.action == "publish-pending":
        result = RecoveredSerialJournal().publish(verify_only=args.verify_only)
    else:
        result = RecoveryOperator().observe(args.output)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
