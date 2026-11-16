"""MiniCPM serial Owner UI operations; no kernel push/submit endpoint exists.

Official read-only provider checks and private capsule upload are explicit
future authorized operations. All real execution is Owner Save & Run All.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import time
import uuid

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.pilot.artifacts import read, write, write_bytes, safe, sha, import_archive
from safeshift.pilot.contract import digest, json_bytes
from safeshift.kaggle_handoff import lock, private_root
from safeshift.fulltrain import contract, minicpm_release as authority, minicpm_sizing as sizing, minicpm_ui as ui
from safeshift.fulltrain.minicpm_execution import MARKER
from scripts.generate_minicpm_fulltrain_notebook import notebook

SCHEMA = "safeshift-minicpm-serial-journal-v2"


def host():
    return digest({"host": platform.node(), "node": uuid.getnode(), "platform": platform.system()})


def sign(private_key, public, payload):
    """Private key is local only; OpenSSL handles private RSA operations."""
    authority.public_key(public)
    key = Path(private_key)
    require(snapshot_stat(key).st_size <= 16384, "MINICPM_SIGNING_KEY_BOUND")
    with tempfile.TemporaryDirectory() as tmp:
        message, signature = Path(tmp) / "payload.json", Path(tmp) / "signature.bin"
        message.write_bytes(json_bytes(payload))
        result = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key), "-out", str(signature), str(message)],
            capture_output=True, timeout=15)
        require(result.returncode == 0, "MINICPM_LOCAL_SIGNING_FAILED")
        sig = signature.read_bytes().hex()
    authority.verify_signature(public, payload, sig)
    return {"payload": payload, "signature": sig}


def public_from_private(private_key):
    """Emit public modulus only. Never print, copy or serialize the private key."""
    require(snapshot_stat(private_key).st_size <= 16384, "MINICPM_SIGNING_KEY_BOUND")
    result = subprocess.run(["openssl", "rsa", "-in", str(private_key), "-modulus", "-noout"],
        capture_output=True, timeout=15)
    require(result.returncode == 0, "MINICPM_OPENSSL_PUBLIC_KEY_FAILED")
    value = {"n_hex": result.stdout.decode().strip().removeprefix("Modulus=").lower(), "e": 65537}
    authority.public_key(value)
    # Also prove that this private key has the pinned exponent, not just length.
    sign(private_key, value, {"scope":"PUBLIC_KEY_PAIR_CHECK_ONLY_NOT_AUTHORITY"})
    return value


def clean_source(grant, repo=ROOT):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    require(head == grant["merged_sha"] and not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo), "MINICPM_CLEAN_MERGED_OPERATOR_REQUIRED")
    # Runtime commit may precede the delivery-only notebook/docs commit.
    for name, expected in contract.source_manifest(repo).items():
        raw = subprocess.check_output(["git", "show", grant["runtime_commit"] + ":" + name], cwd=repo)
        require(hashlib.sha256(raw).hexdigest() == expected, "MINICPM_RUNTIME_REF_NOT_MERGED_BYTES")


def release_template(value, runtime_ref):
    ui.validate(value)
    require(len(runtime_ref) == 40 and all(c in "0123456789abcdef" for c in runtime_ref), "MINICPM_TEMPLATE_RUNTIME_REF")
    return {"schema": authority.SCHEMA, "authorization": None, "campaign_id": None, "implementation_pr": 198,
        "reviewed_head": None, "merged_sha": None, "runtime_commit": runtime_ref, "scope": authority.scope(value),
        "public_key": None, "operator_host_sha256": host(), "caps": {n: None for n in
            ("total_calls", "total_jobs", "total_gpu_seconds", "job_calls", "job_seconds", "physical_gpus", "loads_per_job", "archive_bytes")},
        "sizing": {n: None for n in ("export_seconds", "first_call_seconds", "safety_milli")},
        "issued_unix": None, "expires_unix": None, "provider_max_age_seconds": None,
        "approvals": {k: None for k in authority.ROLES}}


def provider(client, grant, value, prior):
    """Real SDK metadata and quota; no outputs/model/image download here.

    Dataset version availability is the explicit versioned ListFiles request;
    mount names/GetKernel's unversioned attachments do not prove versions.
    """
    from scripts.submit_internvl_v2 import bounded_http
    from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetMetadataRequest
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    from scripts.reconcile_train3763_manual import observe_kernel
    observed_unix, deadline = int(time.time()), time.monotonic() + 900
    def within_bound():
        require(time.monotonic() < deadline, "MINICPM_PROVIDER_ADMISSION_TIME_BOUND")
    owned, tokens, token = set(), set(), None
    with bounded_http():
        for page in range(1, 17):
            within_bound()
            response = client.kernels_list_with_response(mine=True, page_size=100, page_token=token,
                page=None if token else page)
            refs = [row.ref for row in response.kernels]
            require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(type(ref) is str and ref.startswith("nguynanhtn/") for ref in refs), "MINICPM_OWNED_ACCOUNT_INVENTORY")
            owned.update(refs)
            token = response.next_page_token
            if not token and len(refs) < 100:
                break
            if token:
                require(type(token) is str and token not in tokens and len(token) <= 4096, "MINICPM_INVENTORY_TOKEN")
                tokens.add(token)
        else:
            raise ValueError("MINICPM_ACCOUNT_INVENTORY_INCOMPLETE")
        prefix = "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-"
        require(value["job"] not in owned and {ref for ref in owned if ref.startswith(prefix)} == {v["job"] for v in prior},
            "MINICPM_PROVIDER_HISTORY_OR_REPLAY")
        predecessors = []
        for item in prior:
            within_bound()
            proof = observe_kernel(client, item["job"], 1, item["notebook"], item["input_sources"],
                kernel_id=item["kernel_id"])
            predecessors.append({"job": proof["job_id"], "version": 1, "state": proof["state"], "kernel_id": proof["kernel_id"]})
        versions = {}
        for ref in value["input_sources"]["dataset_sources"][:-1]:
            within_bound()
            owner, slug, number = ref.split("/")
            query = ApiGetDatasetMetadataRequest(); query.owner_slug, query.dataset_slug = owner, slug
            with client.build_kaggle_client() as remote:
                metadata = remote.datasets.dataset_api_client.get_dataset_metadata(query)
            require(not metadata.error_message and metadata.info is not None and metadata.info.is_private is True
                and metadata.info.owner_user == owner and metadata.info.dataset_slug == slug, "MINICPM_PRIVATE_DATASET_OWNER")
            files = client.dataset_list_files(ref, page_size=1)
            require(not files.error_message and files.files, "MINICPM_PINNED_DATASET_VERSION_UNAVAILABLE")
            versions[ref] = {"ref": ref, "version": int(number), "private": True}
        for ref in value["input_sources"]["kernel_sources"]:
            within_bound()
            owner, slug, number = ref.split("/")
            query = ApiGetKernelRequest(); query.user_name, query.kernel_slug, query.version_label = owner, slug, "v" + number
            with client.build_kaggle_client() as remote:
                metadata = remote.kernels.kernels_api_client.get_kernel(query).metadata
            require(metadata is not None and metadata.ref == owner + "/" + slug and metadata.is_private is True
                and type(metadata.current_version_number) is int and metadata.current_version_number == int(number)
                and str(client.kernels_status(ref).status).split(".")[-1] == "COMPLETE", "MINICPM_PRIVATE_CHECKPOINT_VERSION")
            versions[ref] = {"ref": ref, "version": int(number), "private": True}
        q = client.quota_view().gpu_quota
        quota = {k: int(getattr(q, f).total_seconds()) for k, f in
            (("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
        require(0 <= quota["used"] <= quota["total"] and quota["reserved"] == 0, "MINICPM_QUOTA_OR_OUTSTANDING_VM")
    within_bound()
    return {"observed_unix": observed_unix, "quota": quota, "input_versions": versions,
        "prior_jobs": predecessors, "job_absent": True, "owned_sha256": digest(sorted(owned))}


class Journal:
    """One local operator, two create-only mirrors; divergence/partial always STOP."""
    def __init__(self, root, mirror):
        self.root, self.mirror = Path(root), Path(mirror)
        require(self.root.resolve() != self.mirror.resolve(), "MINICPM_DISTINCT_MIRROR")

    def events(self):
        for root in (self.root, self.mirror):
            snapshot_stat(root, directory=True)
        names = sorted(p.name for p in self.root.glob("event-*.json"))
        require(names and names == sorted(p.name for p in self.mirror.glob("event-*.json")), "MINICPM_MIRROR_DIVERGENCE")
        events, previous = [], "0" * 64
        for i, name in enumerate(names, 1):
            require(i <= 20000 and name == f"event-{i:05d}.json", "MINICPM_JOURNAL_GAP")
            a, b = safe(self.root, name), safe(self.mirror, name)
            require(snapshot_stat(a).st_size <= 128 * 2**20 and a.read_bytes() == b.read_bytes(), "MINICPM_MIRROR_BYTES")
            event = read(a)
            require(set(event) == {"schema", "number", "previous", "kind", "payload"} and event["schema"] == SCHEMA
                and event["number"] == i and event["previous"] == previous, "MINICPM_JOURNAL_CHAIN")
            events.append(event); previous = digest(event)
        require(events[0]["kind"] == "REGISTERED" and events[0]["payload"]["host"] == host(), "MINICPM_OPERATOR_HOST_NO_TAKEOVER")
        return events

    def append(self, kind, payload):
        events = self.events()
        self._pair({"schema": SCHEMA, "number": len(events) + 1, "previous": digest(events[-1]), "kind": kind, "payload": payload})

    def _pair(self, event):
        for root in (self.root, self.mirror):
            write(safe(root, f"event-{event['number']:05d}.json"), event)
            authority.sync_directory(root)

    def binding(self, grant):
        return {"grant_sha256": digest(grant), "host": host(),
            "root": self.root.resolve().relative_to(ROOT.resolve()).as_posix(),
            "mirror": self.mirror.resolve().relative_to(ROOT.resolve()).as_posix()}

    def guard_path(self, grant):
        return safe(ROOT, "data/processed/minicpm-release-registrations/" + grant["campaign_id"] + ".json")

    @classmethod
    def initialize(cls, root, mirror, locator, value):
        grant = authority.load(locator)
        authority.bind(grant, value)
        require(grant["operator_host_sha256"] == host(), "MINICPM_APPROVED_OPERATOR_HOST")
        clean_source(grant)
        journal = cls(private_root(root), private_root(mirror))
        guard = journal.guard_path(grant)
        guard.parent.mkdir(parents=True, exist_ok=True)
        # A second pair of local journals must never reset the campaign budget.
        # Interrupted initialization keeps this guard; no automatic reclamation.
        write(guard, journal.binding(grant))
        authority.sync_directory(guard.parent)
        for path in (journal.root, journal.mirror):
            path.mkdir(parents=True, exist_ok=False)
        journal._pair({"schema": SCHEMA, "number": 1, "previous": "0" * 64, "kind": "REGISTERED",
            "payload": {"host": host(), "locator": locator, "grant_sha256": digest(grant), "initial": value}})
        return journal

    def state(self):
        events = self.events()
        grant = authority.load(events[0]["payload"]["locator"], collection=True)
        require(digest(grant) == events[0]["payload"]["grant_sha256"] and grant["operator_host_sha256"] == host(),
            "MINICPM_REGISTERED_AUTHORITY_DRIFT")
        require(read(self.guard_path(grant)) == self.binding(grant), "MINICPM_REGISTERED_ROOT_NO_REINITIALIZE")
        reserved, active, completed = {"calls": 0, "jobs": 0, "gpu_seconds": 0}, None, []
        for e in events[1:]:
            v = e["payload"]
            if e["kind"] == "RESERVED":
                require(active is None and v["ticket"]["payload"]["reserved_before"] == reserved
                    and v["ticket"]["payload"]["previous_event_sha256"] == e["previous"], "MINICPM_SERIAL_RESERVATION")
                authority.verify_ticket(grant, v["ticket"], v["value"], collection=True)
                reserved = v["ticket"]["payload"]["reserved_after"]
                active = deepcopy(v)
            elif e["kind"] == "PUBLISHED":
                require(active is not None and "publish_intent" in active and "published" not in active
                    and v["ticket_sha256"] == digest(active["ticket"]), "MINICPM_PUBLISH_SEQUENCE")
                active["published"] = v
            elif e["kind"] == "PUBLISH_INTENT":
                require(active is not None and "publish_intent" not in active
                    and v["ticket_sha256"] == digest(active["ticket"]), "MINICPM_NO_DUPLICATE_CAPSULE_UPLOAD")
                active["publish_intent"] = v
            elif e["kind"] == "PACKAGE_RECOVERED":
                require(active is not None and "publish_intent" not in active
                    and v["ticket_sha256"] == digest(active["ticket"]), "MINICPM_RECOVERY_EXACT_TICKET")
                active["package"] = v["package"]
            elif e["kind"] == "COLLECTED":
                require(active is not None and "published" in active and v["ticket_sha256"] == digest(active["ticket"]), "MINICPM_COLLECT_SEQUENCE")
                active["collection"] = v
                completed.append(active); active = None
            else:
                raise ValueError("MINICPM_UNEXPECTED_JOURNAL_EVENT")
        return grant, events, reserved, active, completed

    def stage(self, private_key, destination):
        with lock(self.root):
            grant, events, reserved, active, completed = self.state()
            require(active is None, "MINICPM_OPEN_RESERVATION_NO_RETRY")
            clean_source(grant)
            value = deepcopy(events[0]["payload"]["initial"])
            prior, telemetry = [], None
            for item in completed:
                collection = item["collection"]
                # Original ZIP/provider custody is rechecked on every subsequent
                # stage, never trusted merely because a journal says COLLECTED.
                report, observed = verify_collection(item["value"], item["ticket"], grant, collection["directory"], online=True)
                require(digest(report) == collection["verification_sha256"], "MINICPM_COLLECTED_RESULT_DRIFT")
                if not report["counts"].get("NOT_ATTEMPTED", 0):
                    raise ValueError("MINICPM_ALL_3763_ACCOUNTED_NO_MORE_JOBS")
                value = ui.next_capsule(item["value"], report, run_id="pending", attempt_id="pending-attempt",
                    job="nguynanhtn/pending", capsule_ref="nguynanhtn/safeshift-minicpm-capsule-pending/1", max_calls=1, max_seconds=1)
                prior.append({"job": item["value"]["job"], "notebook": read(safe(ROOT, item["package"] + "/notebook.ipynb")),
                    "input_sources": item["value"]["input_sources"], "kernel_id": observed["kernel_id"]})
                directory = safe(ROOT, collection["directory"])
                paths = read(directory / "paths.json")
                old_attempt, old_supervisor = safe(directory, paths["attempt"]), safe(directory, paths["supervisor"])
                checked_timing = verify_claims(item["value"], item["ticket"], grant, old_attempt, old_supervisor)
                telemetry = telemetry_record(checked_timing, old_attempt, old_supervisor, item["ticket"])
                require(digest(telemetry) == digest(collection["telemetry"]), "MINICPM_MEASURED_TELEMETRY_CUSTODY")
            number = len(completed) + 1
            value["job"] = "nguynanhtn/safeshift-minicpm-" + grant["campaign_id"] + "-" + str(number)
            value["capsule_ref"] = "nguynanhtn/safeshift-minicpm-capsule-" + grant["campaign_id"] + "-" + str(number) + "/1"
            value["input_sources"]["dataset_sources"][-1] = value["capsule_ref"]
            from safeshift.internvl3763_operator import api
            evidence = provider(api(), grant, value, prior)
            pending = value["request"]["plan"]["counts"]["NOT_ATTEMPTED"]
            proposal = sizing.propose(grant, pending, reserved, evidence, telemetry)
            r = value["request"]
            p = r["plan"]
            r["plan"] = contract.plan(r["campaign"], value["cohort"], p["identity"], r["history"], action=p["action"],
                run_id=grant["campaign_id"] + "-run-" + str(number), attempt_id=grant["campaign_id"] + "-attempt-" + str(number),
                max_calls=proposal["calls"], max_seconds=proposal["seconds"])
            # Exact package is built BEFORE sign, but reservation is durable BEFORE
            # any capsule publication or Owner handoff. Failure leaves it OPEN.
            destination = private_root(destination)
            require(not destination.exists(), "MINICPM_PACKAGE_CREATE_ONLY")
            locator = events[0]["payload"]["locator"]
            pin = digest(value)
            nb = notebook(grant["runtime_commit"], capsule_sha256=pin, release_locator=locator)
            from safeshift.internvl3763_operator import code_hash
            now = int(time.time())
            ticket = {"schema": authority.TICKET, "grant_sha256": digest(grant), "value_sha256": pin,
                "capsule_sha256": pin, "notebook_code_sha256": code_hash(nb), "number": number,
                "previous_event_sha256": digest(events[-1]), "reserved_before": reserved,
                "reserved_after": {"calls": reserved["calls"] + proposal["calls"], "jobs": reserved["jobs"] + 1,
                    "gpu_seconds": reserved["gpu_seconds"] + 2 * proposal["seconds"]},
                "issued_unix": now, "start_before_unix": evidence["observed_unix"] + grant["provider_max_age_seconds"],
                "provider": evidence, "sizing": proposal}
            envelope = sign(private_key, grant["public_key"], ticket)
            authority.verify_ticket(grant, envelope, value)
            package_rel = destination.relative_to(ROOT).as_posix()
            self.append("RESERVED", {"value": value, "ticket": envelope, "package": package_rel})
            ancestors = [safe(ROOT, item["collection"]["directory"] + "/" + read(safe(ROOT,
                item["collection"]["directory"] + "/paths.json"))["attempt"]) for item in completed]
            # Reuse the exact PR195 capsule writer; V2 adds its authenticated ticket
            # outside the immutable payload directory to avoid a hash cycle.
            ui.package(value, ancestors, destination, lambda _: nb)
            write(destination / "dataset" / MARKER, envelope)
            write(destination / "release.json", {"status": "RESERVED_NOT_PUBLISHED", "ticket": envelope, "locator": locator})
            return destination

    def publish(self, *, verify_only=False):
        """Private metadata Dataset only; no notebook upload/API submit.

        A timed-out create is ambiguous. --verify-only reconciles its actual
        existing provider bytes; it never retries creation or starts a new job.
        """
        from safeshift.internvl3763_operator import api
        with lock(self.root):
            grant, _, _, active, completed = self.state()
            require(active is not None and "published" not in active, "MINICPM_EXACT_UNPUBLISHED_RESERVATION")
            clean_source(grant)
            destination = safe(ROOT, active["package"])
            value, ticket = active["value"], active["ticket"]
            authority.verify_ticket(grant, ticket, value)
            require(time.time() < ticket["payload"]["start_before_unix"], "MINICPM_PROVIDER_TICKET_STALE_RECONCILE")
            client = api()
            if not verify_only:
                require("publish_intent" not in active, "MINICPM_UPLOAD_UNKNOWN_VERIFY_ONLY")
                # Separate upload folder avoids publishing handoff/notebook or
                # altering the exact capsule inventory checked in the worker.
                upload = destination / "private-upload"
                upload.mkdir(exist_ok=False)
                for p in (destination / "dataset").iterdir():
                    require(p.is_file(), "MINICPM_FLAT_CAPSULE_ONLY")
                    _copy(p, upload / p.name)
                _copy(destination / "dataset-metadata.json", upload / "dataset-metadata.json")
                self.append("PUBLISH_INTENT", {"ticket_sha256": digest(ticket)})
                from scripts.submit_internvl_v2 import bounded_http
                with bounded_http():
                    result = client.dataset_create_new(str(upload), public=False, quiet=True, convert_to_csv=False, dir_mode="skip")
                require(not result.error_message, "MINICPM_PRIVATE_CAPSULE_CREATE_FAILED_NO_RETRY")
            require(not verify_only or "publish_intent" in active, "MINICPM_PUBLISH_INTENT_REQUIRED")
            proof = verify_published_capsule(client, value, ticket, destination)
            prior = [{"job": item["value"]["job"], "notebook": read(safe(ROOT, item["package"] + "/notebook.ipynb")),
                "input_sources": item["value"]["input_sources"], "kernel_id": read(safe(ROOT,
                    item["collection"]["directory"] + "/provider.json"))["kernel_id"]} for item in completed]
            fresh = provider(client, grant, value, prior)
            require(fresh["quota"]["total"] - fresh["quota"]["used"] >= 2 * value["request"]["plan"]["max_seconds"],
                "MINICPM_QUOTA_CHANGED_BEFORE_HANDOFF")
            require(time.time() < ticket["payload"]["start_before_unix"], "MINICPM_PUBLISH_EXPIRED_DURING_UPLOAD")
            self.append("PUBLISHED", {"ticket_sha256": digest(ticket), "proof": proof})
            handoff = {"status": "RELEASED_FOR_OWNER_UI", "job": value["job"], "version": 1,
                "notebook_sha256": sha(destination / "notebook.ipynb"), "capsule_sha256": digest(value),
                "input_sources": value["input_sources"], "calls": value["request"]["plan"]["max_calls"],
                "seconds": value["request"]["plan"]["max_seconds"], "physical_gpus": 2, "worker_gpu": 0,
                "start_before_unix": ticket["payload"]["start_before_unix"], "ticket_sha256": digest(ticket),
                "live_model_fit": "NOT_ESTABLISHED_INTEGRATED_PREFLIGHT_REQUIRED", "provider": proof,
                "fresh_provider": fresh}
            write(destination / "owner-handoff.json", handoff)
            return handoff

    def collect(self, destination):
        """Bounded terminal check; RUNNING returns without downloading/resubmitting."""
        from safeshift.internvl3763_operator import api
        from scripts.reconcile_train3763_manual import observe_kernel
        from scripts.minicpm_fulltrain_transport import fetch_outputs
        from scripts.submit_internvl_v2 import bounded_http
        with lock(self.root):
            grant, _, _, active, _ = self.state()
            require(active is not None and "published" in active, "MINICPM_EXACT_OWNER_RUN_RESERVATION")
            value, ticket = active["value"], active["ticket"]
            pkg = safe(ROOT, active["package"])
            client = api()
            with bounded_http():
                remote = client.kernels_status(value["job"] + "/1")
            state = str(remote.status).split(".")[-1]
            if state in ("QUEUED", "RUNNING"):
                return {"status": "RUNNING_UNVERIFIED", "job": value["job"], "version": 1,
                    "action": "END_AI_TURN_RESUME_SAME_CONVERSATION_AFTER_OWNER_REPORT"}
            require(state in ("COMPLETE", "ERROR", "CANCELLED"), "MINICPM_PROVIDER_UNKNOWN_STOP")
            observed = observe_kernel(client, value["job"], 1, read(pkg / "notebook.ipynb"),
                value["input_sources"], expected_state=state)
            destination = private_root(destination)
            destination.mkdir(parents=True, exist_ok=False)
            write(destination / "provider.json", observed)
            write(destination / "package.json", {"path": active["package"]})
            # ERROR/partial is retained and never turned into COMPLETE or refunded.
            attempt, supervisor = fetch_outputs(client, value, destination / "provider", grant["caps"]["archive_bytes"])
            write(destination / "paths.json", {"attempt": attempt.relative_to(destination).as_posix(),
                "supervisor": supervisor.relative_to(destination).as_posix()})
            require(state == "COMPLETE", "MINICPM_TERMINAL_ERROR_PRESERVED_STOP")
            directory = destination.relative_to(ROOT).as_posix()
            report, _ = verify_collection(value, ticket, grant, directory, online=False)
            write(destination / "verification.json", report)
            telemetry = verify_claims(value, ticket, grant, attempt, supervisor)
            telemetry = telemetry_record(telemetry, attempt, supervisor, ticket)
            self.append("COLLECTED", {"ticket_sha256": digest(ticket), "directory": directory,
                "verification_sha256": digest(report), "telemetry": telemetry})
            return {"status": "VERIFIED_TERMINAL_CUSTODY", "counts": report["counts"], "scientific_qualified": False,
                "next": "COMPLETE_COVERAGE" if report["counts"].get("NOT_ATTEMPTED", 0) == 0 else "STAGE_PENDING_ONLY"}

    def recover_package(self, destination):
        """Reproduce the exact OPEN reservation after an interrupted offline write.

        Existing partial package bytes are preserved. No new ticket, calls,
        provider operation, budget refund or alternate VM is created.
        """
        with lock(self.root):
            grant, _, _, active, completed = self.state()
            require(active is not None and "publish_intent" not in active, "MINICPM_RECOVERY_OFFLINE_UNPUBLISHED_ONLY")
            clean_source(grant)
            value, envelope = active["value"], active["ticket"]
            authority.verify_ticket(grant, envelope, value)
            locator = self.events()[0]["payload"]["locator"]
            ancestors = [safe(ROOT, item["collection"]["directory"] + "/" + read(safe(ROOT,
                item["collection"]["directory"] + "/paths.json"))["attempt"]) for item in completed]
            nb = notebook(grant["runtime_commit"], capsule_sha256=digest(value), release_locator=locator)
            destination = private_root(destination)
            require(not destination.exists(), "MINICPM_RECOVERY_KEEP_PARTIAL_USE_NEW_PATH")
            ui.package(value, ancestors, destination, lambda _: nb)
            write(destination / "dataset" / MARKER, envelope)
            write(destination / "release.json", {"status":"RESERVED_NOT_PUBLISHED", "ticket":envelope,"locator":locator})
            self.append("PACKAGE_RECOVERED", {"ticket_sha256":digest(envelope),"package":destination.relative_to(ROOT).as_posix()})
            return destination


def _copy(source, target):
    import shutil
    snapshot_stat(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open("rb") as src, Path(target).open("xb") as dst:
        shutil.copyfileobj(src, dst, 2**20)
        dst.flush(); os.fsync(dst.fileno())
    require(sha(source) == sha(target), "MINICPM_EXCLUSIVE_COPY_SHA")


def telemetry_record(timing, attempt, supervisor, ticket):
    result = {k: timing[k] for k in ("model_key", "source_sha256", "overhead_seconds", "call_seconds")}
    result["provenance_sha256"] = digest({"attempt": sha(attempt), "supervisor": sha(supervisor), "ticket": digest(ticket)})
    return result


def verify_published_capsule(client, value, ticket, package):
    import zipfile
    from safeshift.internvl3763_operator import download_capsule, bounded_python_zip
    from kagglesdk.datasets.types.dataset_api_service import ApiGetDatasetMetadataRequest
    from scripts.submit_internvl_v2 import bounded_http
    owner, slug, number = value["capsule_ref"].split("/")
    expected = {p.name: p.stat().st_size for p in (package / "dataset").iterdir()}
    with bounded_http():
        query = ApiGetDatasetMetadataRequest(); query.owner_slug, query.dataset_slug = owner, slug
        with client.build_kaggle_client() as remote:
            result = remote.datasets.dataset_api_client.get_dataset_metadata(query)
        require(not result.error_message and result.info.is_private is True
            and result.info.owner_user == owner and result.info.dataset_slug == slug, "MINICPM_CAPSULE_PRIVATE_OWNER")
        files = client.dataset_list_files(value["capsule_ref"], page_size=1000)
        require(not files.error_message and not files.next_page_token
            and len(files.files) == len(expected) and {f.name: f.total_bytes for f in files.files} == expected,
            "MINICPM_PUBLISHED_CAPSULE_VERSION_FILES")
    # Exact signed ticket bytes at explicit version1; payload/ancestor hashes are
    # then independently rechecked from read-only mounts before preflight/load.
    with tempfile.TemporaryDirectory() as tmp:
        downloaded = download_capsule(client, owner, slug, number, MARKER, Path(tmp))
        raw = downloaded.read_bytes()
        if zipfile.is_zipfile(downloaded):
            bounded_python_zip(downloaded)
            with zipfile.ZipFile(downloaded) as bundle:
                info = bundle.infolist()[0]
                require(info.filename == MARKER and info.file_size == len(json_bytes(ticket)), "MINICPM_CAPSULE_WRAPPER")
                raw = bundle.read(info)
        require(raw == json_bytes(ticket), "MINICPM_PROVIDER_SIGNED_CAPSULE_BYTES")
    return {"ref": value["capsule_ref"], "private": True, "files": expected,
        "ticket_sha256": digest(ticket), "observed_unix": int(time.time())}


def verify_collection(value, envelope, grant, directory, *, online):
    """Local full replay plus fresh provider code/Input/output verification."""
    from scripts.reconcile_train3763_manual import observe_kernel, download_outputs
    from safeshift.internvl3763_operator import api
    directory = safe(ROOT, directory)
    authority.verify_ticket(grant, envelope, value, collection=True)
    paths = read(directory / "paths.json")
    attempt, supervisor = safe(directory, paths["attempt"]), safe(directory, paths["supervisor"])
    package = read(directory / "package.json")
    pkg = safe(ROOT, package["path"])
    expected = read(pkg / "notebook.ipynb")
    from safeshift.internvl3763_operator import code_hash
    require(code_hash(expected) == envelope["payload"]["notebook_code_sha256"], "MINICPM_SIGNED_NOTEBOOK_CODE")
    meta = expected["metadata"]["safeshift"]
    require(meta["runtime_ref"] == grant["runtime_commit"] and meta["source_sha256"] == grant["scope"]["source_sha256"]
        and meta["capsule_sha256"] == digest(value), "MINICPM_PACKAGE_RUNTIME_PIN")
    observed = read(directory / "provider.json")
    require(observed["state"] == "COMPLETE" and observed["job_id"] == value["job"] and observed["version"] == 1,
        "MINICPM_COLLECTION_PROVIDER_BINDING")
    require(observed["notebook_code_sha256"] == envelope["payload"]["notebook_code_sha256"], "MINICPM_PROVIDER_CODE_PIN")
    if online:
        observed = observe_kernel(api(), value["job"], 1, expected, value["input_sources"], kernel_id=observed["kernel_id"])
        with tempfile.TemporaryDirectory() as tmp:
            pairs = {"minicpm-fulltrain/" + value["request"]["plan"]["run_id"] + ".zip": attempt,
                "minicpm-fulltrain/supervision/" + supervisor.name: supervisor}
            download_outputs(api(), value["job"], 1, attempt, sha(attempt), Path(tmp), output_pairs=pairs)
    with tempfile.TemporaryDirectory() as tmp:
        report = ui.verify_results(value, pkg / "dataset", attempt, supervisor, Path(tmp) / "verified")
    require(report["continuation"] == "REVIEW_CAPS_AND_RELEASE", "MINICPM_FAILED_ATTEMPT_STOP_RECONCILE")
    verify_claims(value, envelope, grant, attempt, supervisor)
    return report, observed


def verify_claims(value, envelope, grant, attempt, supervisor):
    """Every native marker must have the exact signed-ticket permanent claim."""
    for path in (attempt, supervisor):
        require(snapshot_stat(path).st_size <= grant["caps"]["archive_bytes"], "MINICPM_ARCHIVE_BUDGET")
    with tempfile.TemporaryDirectory() as tmp:
        root = import_archive(attempt, Path(tmp) / "attempt")
        control = import_archive(supervisor, Path(tmp) / "supervisor")
        require(read(root / "capability.json")["ticket"] == envelope
            and read(control / "capability.json")["ticket"] == envelope, "MINICPM_ARCHIVE_SIGNED_TICKET")
        claims = read(root / "claims.json")
        require(read(control / "claims.json") == claims and set(authority.STAGES) <= {n.removesuffix(".json") for n in claims},
            "MINICPM_FULL_STAGE_CLAIMS")
        require(all(c["ticket_sha256"] == digest(envelope) and c["request_sha256"] == digest(value["request"])
            and c["kind"] + ".json" == name and c["number"] == envelope["payload"]["number"]
            and type(c["time_unix"]) in (int,float) and math.isfinite(c["time_unix"]) for name, c in claims.items()),
            "MINICPM_CLAIM_TICKET_BINDING")
        launch_time = claims["launch.json"]["time_unix"]
        require(envelope["payload"]["issued_unix"] <= launch_time < envelope["payload"]["start_before_unix"]
            and all(launch_time <= c["time_unix"] < launch_time + value["request"]["plan"]["max_seconds"]
                for c in claims.values()), "MINICPM_CLAIM_DEADLINE_CUSTODY")
        native = {i for i in value["request"]["plan"]["scheduled_ordinals"] if
            (root / f"calls/{i:06d}/run/samples/000000/native_call.json").exists()}
        called = {int(n[5:-5]) for n in claims if n.startswith("call-")}
        require(called == native and (not called or "load.json" in claims), "MINICPM_UNKNOWN_CALL_CLAIM_STOP")
        timing = read(root / "timing.json")
        require(timing["observed_complete_calls"] == len(timing["call_seconds"]) == len(native)
            and timing["model_key"] == "minicpm4" and timing["source_sha256"] == value["request"]["source_sha256"]
            and timing["population_bound"] is False, "MINICPM_TIMING_NATIVE_CUSTODY")
        return timing


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path)
    p.add_argument("--mirror", type=Path)
    sub = p.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init")
    init.add_argument("--locator", required=True, type=Path); init.add_argument("--spec", required=True, type=Path)
    sub.add_parser("status")
    publish = sub.add_parser("publish")
    publish.add_argument("--verify-only", action="store_true")
    collect = sub.add_parser("collect")
    collect.add_argument("--output", required=True, type=Path)
    template = sub.add_parser("release-template")
    template.add_argument("--spec", required=True, type=Path)
    template.add_argument("--runtime-ref", required=True)
    template.add_argument("--output", required=True, type=Path)
    pub = sub.add_parser("public-key")
    pub.add_argument("--private-key", required=True, type=Path)
    pub.add_argument("--output", required=True, type=Path)
    recovery = sub.add_parser("recover-package")
    recovery.add_argument("--output", required=True, type=Path)
    stage = sub.add_parser("stage")
    stage.add_argument("--private-key", required=True, type=Path); stage.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    if args.action == "public-key":
        write(args.output, public_from_private(args.private_key))
        print("PUBLIC_KEY_ONLY; grant and independent verification still required")
        return
    if args.action == "release-template":
        write(args.output, release_template(read(args.spec), args.runtime_ref))
        print("UNSIGNED_PROPOSAL; no authority created")
        return
    require(args.directory is not None and args.mirror is not None, "MINICPM_JOURNAL_AND_MIRROR_REQUIRED")
    if args.action == "init":
        Journal.initialize(args.directory, args.mirror, read(args.locator), read(args.spec))
        print("REGISTERED; no job submitted")
    elif args.action == "stage":
        print(Journal(args.directory, args.mirror).stage(args.private_key, args.output))
    elif args.action == "publish":
        print(json.dumps(Journal(args.directory, args.mirror).publish(verify_only=args.verify_only)))
    elif args.action == "collect":
        print(json.dumps(Journal(args.directory, args.mirror).collect(args.output)))
    elif args.action == "recover-package":
        print(Journal(args.directory, args.mirror).recover_package(args.output))
    else:
        _, _, reserved, active, completed = Journal(args.directory, args.mirror).state()
        print(json.dumps({"reserved": reserved, "open_reservation": active is not None,
            "verified_jobs": len(completed), "billing": "NOT_OBSERVED"}))


if __name__ == "__main__":
    main()
