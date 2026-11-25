"""Released Operator-only fast path for the existing MiniCPM V5 journal.

The companion requires its own Owner release over an audited V5 journal prefix.
A separately authenticated runtime continuation can issue new V5-format tickets
against the same journal and hold chain.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.fulltrain import contract, memory, minicpm_execution, runtime
from safeshift.internvl3763_operator import code_hash
from safeshift.pilot.artifacts import read, safe, sha, verify_archive
from safeshift.pilot.contract import digest, json_bytes, require_hash
from scripts import minicpm_offline_continuation as v5

a, policy, ui = v5.a, v5.policy, v5.ui
RELEASE = "SAFESHIFT_MINICPM_OFFLINE_OPERATOR_FAST_V1"
SEAL = "safeshift-minicpm-offline-accept-verification-v1"
CLOSURE_SEAL = "safeshift-minicpm-offline-closure-verification-v1"
prenative = v5.prenative


def authenticate_release(locator, exports, registration, grant):
    """Authenticate Owner-acquired GitHub originals using the V5 trust boundary."""
    reader = v5.Exports(exports)
    comment = reader("/issues/comments/" + str(locator["comment_id"]))
    release = a.record(comment["body"], RELEASE)
    pr_number = release["implementation_pr"]
    a.owner_comment(comment, locator, pr_number)
    fields = {"status", "implementation_pr", "reviewed_head", "merged_sha", "grant_sha256",
        "registration_sha256", "prefix_event_number", "prefix_head_sha256", "tool_sha256", "approvals"}
    optional = {"closure_snapshots", "companion_dependencies"}
    require(fields <= set(release) <= fields | optional and release["status"] == "RELEASED_OPERATOR_FAST_PATH"
        and release["grant_sha256"] == digest(grant) and release["registration_sha256"] == digest(registration)
        and type(release["prefix_event_number"]) is int and 1 <= release["prefix_event_number"] <= 20000,
        "MINICPM_FAST_EXACT_EXISTING_CAMPAIGN_RELEASE")
    if "closure_snapshots" in release:
        pins = release["closure_snapshots"]
        require(type(pins) is dict and len(pins) <= release["prefix_event_number"], "MINICPM_FAST_CLOSURE_PREFIX_SCOPE")
        for pin in pins.values():
            require_hash(pin)
    for key in ("prefix_head_sha256", "tool_sha256"):
        require_hash(release[key])
    pr = reader("/pulls/" + str(pr_number))
    require(pr["merged"] is True and pr["draft"] is False and pr["base"]["ref"] == "main"
        and pr["head"]["sha"] == release["reviewed_head"] and pr["merge_commit_sha"] == release["merged_sha"],
        "MINICPM_FAST_REVIEWED_MERGED_PR_REQUIRED")
    roles = {"source_review", "independent_audit", "merge", "postmerge"}
    require(set(release["approvals"]) == roles, "MINICPM_FAST_SEPARATE_REVIEWS_REQUIRED")
    subject = digest({key: value for key, value in release.items() if key != "approvals"})
    seen = {comment["id"]}
    for role, approval in release["approvals"].items():
        original = a.owner_comment(reader("/issues/comments/" + str(approval["comment_id"])), approval, pr_number)
        require(original["id"] not in seen and a.record(original["body"], a.APPROVAL) ==
            {"kind": role, "status": "APPROVED", "reviewed_head": release["reviewed_head"], "subject_sha256": subject},
            "MINICPM_FAST_REVIEW_SCOPE")
        seen.add(original["id"])
    path = Path(__file__)
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == release["tool_sha256"], "MINICPM_FAST_TOOL_SHA256")
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    expected = {"scripts/" + path.name: blob}
    if "companion_dependencies" in release:
        sources = contract.source_manifest()
        tools = v5.tools_manifest()
        require(release["companion_dependencies"] ==
            {"source_sha256": digest(sources), "tools_sha256": digest(tools)}, "MINICPM_FAST_DEPENDENCY_SHA256")
        for name in sources:
            raw = (contract.ROOT / name).read_bytes()
            expected[name] = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        expected.update(v5.tool_blobs())
    for ref in {release["reviewed_head"], release["merged_sha"]}:
        require(type(ref) is str and len(ref) == 40 and all(c in "0123456789abcdef" for c in ref),
            "MINICPM_FAST_GIT_REF")
        tree = reader("/git/trees/" + ref + "?recursive=1")
        require(tree.get("truncated") is False and len(tree["tree"]) <= 20000, "MINICPM_FAST_TOOL_GIT_TREE")
        observed = {item["path"]: (item["type"], item["mode"], item["sha"]) for item in tree["tree"]}
        require(len(observed) == len(tree["tree"])
            and all(observed.get(name) == ("blob", "100644", checksum) for name, checksum in expected.items()),
            "MINICPM_FAST_TOOL_GIT_TREE")
    return release


def pinned(path, expected):
    snapshot_stat(path)
    require(sha(path) == expected, "MINICPM_FAST_CUSTODY_BYTES_CHANGED")


def notebook_bytes(notebook):
    # V5 exports its notebook after loading the canonical, sorted journal event.
    return (json.dumps(notebook, sort_keys=True, indent=1, ensure_ascii=False) + "\n").encode()


def open_archive(path, destination, expected, limit):
    """Check CRC, membership and SHA, then materialize disposable replay bytes."""
    require(0 < snapshot_stat(path).st_size <= limit, "MINICPM_ARCHIVE_BUDGET")
    pinned(path, expected)
    side = path.with_suffix(path.suffix + ".sha256.json")
    require(snapshot_stat(side).st_size <= 4096, "UI_SIDECAR_BOUND")
    entries = verify_archive(path)
    side_sha = sha(side)
    require(read(side) == {"sha256": expected, "members": len(entries) + 1}, "UI_ARCHIVE_SIDECAR")
    pinned(side, side_sha)
    destination.mkdir()
    with zipfile.ZipFile(path) as archive:
        for name, expected_member in entries.items():
            payload = archive.read(name)
            require(hashlib.sha256(payload).hexdigest() == expected_member, "MINICPM_FAST_ARCHIVE_CHANGED")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(payload)
    return destination, side_sha


def verify_supervisor(control, request):
    require(read(control / "request.json") == request, "UI_SUPERVISOR_REQUEST")
    release = read(control / "release.json")
    require(release["source_sha256"] == request["source_sha256"] and release["diagnostic"] is False
        and release["attempt_observed"] is True and release["scientific_qualified"] is False
        and release["status"] == "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY"
        and release["failure"] is None and release["last_stage"] == "native", "UI_SUPERVISOR_BINDING")
    from safeshift.fulltrain.memory import complete
    request_sha = digest(request)
    for mode in a.STAGES[1:]:
        process = read(control / (mode + "-process.json"))
        require(process["status"] == "EXITED" and process["returncode"] == 0
            and process.get("group_exit", {}).get("status") == "NO_LIVE_MEMBERS", "UI_STAGE_PROCESS")
        require(read(control / mode / "stage.json") == {"status": "RETURNED", "stage": mode,
            "request_sha256": request_sha, "source_sha256": request["source_sha256"],
            "native_attempt_permitted": mode == "native"}, "UI_STAGE_REQUEST")
        for point in ("entry", "exit"):
            complete(read(control / mode / ("stage-" + point + "-memory.json")))
    advice = read(control / "reclaim/owned-advice.json")
    require(advice["scan_complete"] is True and advice["deleted_files"] == 0
        and advice["effect"] == "ADVISORY_NOT_RAM_PROOF", "UI_OWNED_ADVICE_UNVERIFIED")
    post = read(control / "reclaim/post-advice-resources.json")
    require(post["memory"]["available_bytes"] >= request["resource_policy"]["free_ram_mib"] * 2**20,
        "UI_UNCHANGED_RAM_FLOOR")


def verify_claims(value, envelope, grant, root, control, attempt_sha):
    """V5 claim/retention checks on the same scratch trees used for raw replay."""
    ticket_sha, request_sha = digest(envelope), digest(value["request"])
    require(read(root / "capability.json")["ticket"] == envelope
        and read(control / "capability.json")["ticket"] == envelope, "MINICPM_ARCHIVE_SIGNED_TICKET")
    claims = read(root / "claims.json")
    require(read(control / "claims.json") == claims and set(a.STAGES) <= {n.removesuffix(".json") for n in claims},
        "MINICPM_FULL_STAGE_CLAIMS")
    require(all(c["ticket_sha256"] == ticket_sha and c["request_sha256"] == request_sha
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
    if grant["schema"] == a.RECOVERY_SCHEMA:
        generated = {int(n[9:-5]) for n in claims if n.startswith("generate-")}
        require(generated == native, "MINICPM_GENERATE_OBSERVATION_CUSTODY")
        for i in generated:
            observation = claims[f"generate-{i:06d}.json"]["observation"]
            require(observation["ordinal"] == i and observation["kind"] == "native_generate_started"
                and observation["claim"] == claims[f"call-{i:06d}.json"], "MINICPM_GENERATE_CALL_CLAIM_CUSTODY")
    timing = read(root / "timing.json")
    require(timing["observed_complete_calls"] == len(timing["call_seconds"]) == len(native)
        and timing["model_key"] == "minicpm4" and timing["source_sha256"] == value["request"]["source_sha256"]
        and timing["population_bound"] is False, "MINICPM_TIMING_NATIVE_CUSTODY")
    retained = read(control / "retention.json")
    expected_archives = {h["run_id"]:v["sha256"] for h,v in zip(value["request"]["history"],value["ancestors"])}
    expected_archives[value["request"]["plan"]["run_id"]] = attempt_sha
    require(retained["status"] == "SEALED_ZIPS_IN_OUTPUT_RAW_BYTES_RETAINED_IN_SCRATCH"
        and retained["raw_deleted"] is False and len(retained["retained"]) == len(expected_archives)
        and {v["run_id"]:v["archive_sha256"] for v in retained["retained"]} == expected_archives,
        "MINICPM_SEALED_OUTPUT_RETENTION_CUSTODY")
    timing["overhead_seconds"] = policy.verify_export_timing(
        grant, value, read(control / "final_timing.json"), timing["call_seconds"])
    return timing


def verify_new(grant, active, attempt, supervisor, receipt, proof):
    """Same V5 completion document, with raw/C1 replay of the incoming ZIP only."""
    value, ticket = active["value"], active["ticket"]
    request, cohort = value["request"], value["cohort"]
    attempt_sha, supervisor_sha = receipt["archive_sha256"], receipt["supervisor_sha256"]
    policy.terminal(receipt, value, attempt_sha, supervisor_sha)
    require(0 < snapshot_stat(proof).st_size <= 16*2**20, "MINICPM_TERMINAL_PROOF_BOUND")
    pinned(proof, receipt["proof_sha256"])
    require(attempt.name == request["plan"]["run_id"] + ".zip", "MINICPM_EXACT_OUTPUT_NAME")
    require(len(supervisor.stem) == 32 and all(c in "0123456789abcdef" for c in supervisor.stem),
        "MINICPM_EXACT_SUPERVISOR_NAME")
    limit = grant["caps"]["archive_bytes"]
    with tempfile.TemporaryDirectory() as temp:
        result, attempt_sidecar = open_archive(attempt, Path(temp) / "attempt", attempt_sha, limit)
        control, supervisor_sidecar = open_archive(supervisor, Path(temp) / "supervisor", supervisor_sha, limit)
        verify_supervisor(control, request)
        require(read(result / "plan.json") == request["plan"] and read(result / "history.json") == request["history"]
            and read(result / "campaign.json") == request["campaign"], "UI_ATTEMPT_REQUEST")
        current = runtime.recover(result, cohort, digest(request["plan"]))
        run = read(result / "receipt.json")
        require(run["native_calls"] == run["observed_native_markers"] <= request["plan"]["max_calls"]
            and run["load_attempts"] <= 1 and run["loads"] <= 1
            and not (result / "accounting_failure.json").exists(), "UI_NATIVE_ACCOUNTING")
        require(run["stop"] in (None, "ADAPTIVE_TIME_STOP", "ADAPTIVE_STORAGE_STOP"),
            "MINICPM_TECHNICAL_FAILURE_STOP_NO_RETRY")
        timing = verify_claims(value, ticket, grant, result, control, attempt_sha)
    rows = [row for row in current["records"] if row["status"] != "NOT_ATTEMPTED"]
    require(rows and all(row["status"] in ("SUCCESS", "INVALID") for row in rows), "MINICPM_ONLY_DURABLE_COMPLETION")
    scheduled = request["plan"]["scheduled_ordinals"]
    require([ordinal for ordinal, row in zip(scheduled, current["records"]) if row["status"] != "NOT_ATTEMPTED"]
        == scheduled[:len(rows)]
        and len(rows) == run["native_calls"] == timing["observed_complete_calls"], "MINICPM_OFFLINE_NO_SKIP_DUPLICATE_OR_ERROR")
    history = [*request["history"], current]
    preview = contract.plan(request["campaign"], cohort, request["plan"]["identity"], history, action="resume",
        run_id="preview-next", attempt_id="preview-next-attempt", max_calls=1, max_seconds=1)
    report = {"status": "LOCAL_VERIFIED_NOT_PROVIDER_AUTHORITY", "continuation": "REVIEW_CAPS_AND_RELEASE",
        "request_sha256": digest(request), "attempt_sha256": attempt_sha, "supervisor_sha256": supervisor_sha,
        "history": history, "counts": preview["counts"], "native_calls": run["native_calls"],
        "source_sha256": request["source_sha256"], "scientific_selection": "PENDING", "pooling_allowed": False}
    # Read the durable pairs again after the replay before signing their result.
    pinned(attempt, attempt_sha)
    pinned(supervisor, supervisor_sha)
    return {"report": report, "telemetry": v5.old.telemetry_record(timing, attempt, supervisor, ticket),
        "owner_receipt": receipt, "terminal_proof_sha256": receipt["proof_sha256"],
        "sidecars": {"attempt": attempt_sidecar, "supervisor": supervisor_sidecar},
        "provider_verification": "PENDING_FINAL_RECONCILIATION", "scientific_qualified": False}


def package_files(active, completed):
    value, ticket = active["value"], active["ticket"]
    nb = active["notebook"]
    meta = nb["metadata"]["safeshift"]
    signed = ticket["payload"]
    require(code_hash(nb) == signed["notebook_code_sha256"] and meta["capsule_sha256"] == digest(value)
        and meta["source_sha256"] == value["request"]["source_sha256"], "MINICPM_RECOVERY_NOTEBOOK_PIN")
    require(len(value["ancestors"]) == len(completed), "MINICPM_FAST_EXACT_ANCESTORS")
    files = {"dataset/" + ui.MARKER: digest(value), "dataset/" + minicpm_execution.MARKER: digest(ticket),
        "notebook.ipynb": hashlib.sha256(notebook_bytes(nb)).hexdigest()}
    for entry, prior in zip(value["ancestors"], completed):
        verification = prior["completion"]["verification"]
        require(entry["sha256"] == verification["report"]["attempt_sha256"]
            and entry["plan_sha256"] == digest(prior["value"]["request"]["plan"]), "MINICPM_FAST_ANCESTOR_PIN")
        files["dataset/" + entry["file"]] = entry["sha256"]
        files["dataset/" + entry["file"] + ".sha256.json"] = verification["sidecars"]["attempt"]
    return files


def check_package(package, files):
    dataset = safe(package, "dataset")
    snapshot_stat(dataset, directory=True)
    require({entry.name for entry in dataset.iterdir()} == {Path(name).name for name in files if name.startswith("dataset/")},
        "UI_CAPSULE_EXACT_FILES")
    for name, expected in files.items():
        pinned(safe(package, name), expected)


def custody_files(completion):
    verified = completion["verification"]
    report, receipt = verified["report"], verified["owner_receipt"]
    return {completion["attempt"]: report["attempt_sha256"], completion["supervisor"]: report["supervisor_sha256"],
        completion["attempt"] + ".sha256.json": verified["sidecars"]["attempt"],
        completion["supervisor"] + ".sha256.json": verified["sidecars"]["supervisor"],
        completion["proof"]: verified["terminal_proof_sha256"],
        str(Path(completion["proof"]).parent.as_posix()) + "/owner-receipt.json": digest(receipt)}


def closure_snapshot(download):
    """Hash the current bounded inventory, including loose evidence and claims."""
    def checked_sha(name):
        path = safe(download, name)
        before = memory.identity(snapshot_stat(path))
        checksum = sha(path)
        require(before == memory.identity(snapshot_stat(path)), "MINICPM_FAST_CLOSURE_EVIDENCE_DRIFT")
        return checksum

    return digest({name: checked_sha(name) for name in prenative.inventory(download)})


class Continuation(v5.Continuation):
    """Operator view only. V5 still owns final manifest and provider admission."""

    def __init__(self, root, locator, exports, *, historical_repo=None, runtime_release=None, previous_runtime=None):
        self.root = v5.private(root)
        path = safe(self.root, "registration.json")
        require(snapshot_stat(path).st_size <= 64*2**20, "MINICPM_REGISTRATION_BOUND")
        self.registration = read(path)
        self.mirror = v5.private(safe(v5.ROOT, self.registration["mirror"]))
        self.distinct(self.root, self.mirror)
        self.load_authority(historical_repo, runtime_release, previous_runtime)
        require(policy.first_serial(self.grant) == 9, "MINICPM_FAST_REQUIRES_V5")
        self.release = authenticate_release(locator, exports, self.registration, self.grant)
        if self.historical_repo != contract.ROOT:
            require({"companion_dependencies", "closure_snapshots"} <= set(self.release),
                "MINICPM_FAST_TRANSITION_RELEASE_REQUIRED")
        self.check_registration()

    @classmethod
    def initialize(cls, *args, **kwargs):
        raise ValueError("MINICPM_FAST_EXISTING_V5_REGISTRATION_REQUIRED")

    def check_registration(self):
        registration_sha = self.release["registration_sha256"]
        require(self.registration["schema"] == self.grant["offline"]["schema"]
            and self.registration["root"] == v5.relative(self.root)
            and self.registration["grant_sha256"] == digest(self.grant)
            and self.registration["operator_session"] == self.grant["offline"]["operator_session"]
            and read(v5.registration_fence(self.grant)) ==
                {"root": v5.relative(self.root), "registration_sha256": registration_sha},
            "MINICPM_OFFLINE_SINGLE_REGISTRATION")
        for root in (self.root, self.mirror):
            pinned(safe(root, "registration.json"), registration_sha)

    def events(self):
        self.check_registration()
        self.check_original_inventories()
        rows = super().events()
        prefix = self.release["prefix_event_number"]
        require(len(rows) >= prefix and digest(rows[prefix - 1]) == self.release["prefix_head_sha256"],
            "MINICPM_FAST_RELEASED_PREFIX_CHANGED")
        for row in rows:
            if row["kind"] == "RESERVED_OFFLINE":
                active = row["payload"]
                signed = active["ticket"]["payload"]
                require(active["package"] == f"handoffs/{signed['number']}"
                    and active["gate_proof"] == "gates/" + signed["owner_gate"]["proof_sha256"] + ".bin",
                    "MINICPM_FAST_CANONICAL_RESERVATION_PATHS")
        self._completions = {row["payload"]["ticket_sha256"]: row for row in rows if row["kind"] == v5.PROVISIONAL}
        self._closures = {row["payload"]["summary"]["ticket_sha256"]: row for row in rows
            if row["kind"] == prenative.DISPOSITION}
        if "closure_snapshots" in self.release:
            require(set(self.release["closure_snapshots"]) ==
                {str(row["payload"]["summary"]["number"]) for row in rows[:prefix]
                    if row["kind"] == prenative.DISPOSITION}, "MINICPM_FAST_CLOSURE_PREFIX_SCOPE")
        self._rows = rows
        return rows

    @staticmethod
    def check_original_inventories():
        processed = v5.ROOT / "data/processed"
        v5.serial7.inventory(safe(processed, "inspect_run_7"))
        v5.serial8.inventory(safe(processed, v5.serial8.DOWNLOAD))

    def seal_payload(self, event):
        return {"schema": SEAL, "grant_sha256": self.release["grant_sha256"],
            "registration_sha256": self.release["registration_sha256"], "reservation_event_sha256": event["previous"],
            "completion_event_sha256": digest(event), "event_unix": event["unix"]}

    @staticmethod
    def seal_name(active):
        return f"accept-verifications/{active['ticket']['payload']['number']}.json"

    def recheck(self, active, completion):
        event = self._completions[completion["ticket_sha256"]]
        if event["number"] > self.release["prefix_event_number"]:
            envelopes, copies = [], []
            for root in (self.root, self.mirror):
                path = safe(root, self.seal_name(active))
                require(snapshot_stat(path).st_size <= 8192, "MINICPM_FAST_SEAL_BOUND")
                copies.append(path.read_bytes())
                envelopes.append(read(path))
            seal, mirror = envelopes
            require(copies[0] == copies[1] and seal == mirror and set(seal) == {"payload", "signature"}
                and seal["payload"] == self.seal_payload(event), "MINICPM_FAST_SEAL_DRIFT")
            a.verify_signature(self.grant["public_key"], seal["payload"], seal["signature"])
        files = package_files(active, self._accepted)
        grant, _, _ = self.authority_for(active)
        require(active["notebook"]["metadata"]["safeshift"]["runtime_ref"] == grant["runtime_commit"],
            "MINICPM_FAST_V5_RUNTIME_REF")
        for root in (self.root, self.mirror):
            for name, expected in custody_files(completion).items():
                pinned(safe(root, name), expected)
            check_package(safe(root, active["package"]), files)
        self._accepted.append({**active, "completion": completion})
        return completion["verification"]

    @staticmethod
    def closure_seal_name(serial):
        return f"closure-verifications/{serial}.json"

    def closure_seal_payload(self, event, evidence_sha256):
        return {"schema": CLOSURE_SEAL, "registration_sha256": self.release["registration_sha256"],
            "event_sha256": digest(event), "event_unix": event["unix"], "evidence_sha256": evidence_sha256}

    def closure_seals(self, serial):
        return [safe(root, self.closure_seal_name(serial)) for root in (self.root, self.mirror)]

    @staticmethod
    def read_closure_seal(path):
        require(snapshot_stat(path).st_size <= 8192, "MINICPM_FAST_CLOSURE_SEAL_BOUND")
        return read(path)

    def check_closure(self, active, download, closure):
        serial = active["ticket"]["payload"]["number"]
        event = self._closures[digest(active["ticket"])]
        if event["number"] <= self.release["prefix_event_number"]:
            expected = self.release.get("closure_snapshots", {}).get(str(serial))
            if expected is None:
                return super().check_closure(active, download, closure)
        else:
            seals = self.closure_seals(serial)
            # A V5 closure written outside the companion has no seal. Replay
            # it with the original verifier until an Owner release audits it.
            if not any(path.exists() for path in seals):
                return super().check_closure(active, download, closure)
            seal, mirror = map(self.read_closure_seal, seals)
            require(seal == mirror and set(seal) == {"payload", "signature"}, "MINICPM_FAST_CLOSURE_SEAL_MIRROR")
            expected = seal["payload"]["evidence_sha256"]
            require(seal["payload"] == self.closure_seal_payload(event, expected), "MINICPM_FAST_CLOSURE_SEAL_DRIFT")
            a.verify_signature(self.grant["public_key"], seal["payload"], seal["signature"])
        require(closure_snapshot(v5.private(safe(v5.ROOT, download))) == expected,
            "MINICPM_FAST_CLOSURE_EVIDENCE_DRIFT")
        return super().check_closure(active, download, closure, verified_local=closure["local"])

    def close_pre_native(self, download, closure, *, private_key, kernel_id):
        path = v5.relative(download)
        with v5.lock(self.root):
            state = self.state()
            require(type(kernel_id) is int and kernel_id > 0 and closure.get("provider", {}).get("kernel_id") == kernel_id,
                "MINICPM_PRE_NATIVE_EXPECTED_KERNEL_ID")
            for item in state["closed"]:
                if item["summary"]["ticket_sha256"] == closure.get("local", {}).get("ticket_sha256"):
                    require(item["download"] == path and item["closure"] == closure, "MINICPM_PRE_NATIVE_EXISTING_CLOSURE_DRIFT")
                    return {"status": "ALREADY_CLOSED", "reserved": state["reserved"],
                        "next_ordinal": state["next_ordinal"],
                        "active_serial": state["active"]["ticket"]["payload"]["number"] if state["active"] else None}
            active = state["active"]
            require(active is not None and not state["stopped"] and state["final"] is None,
                "MINICPM_NO_ACTIVE_CLOSURE")
            require(closure.get("local", {}).get("ticket_sha256") == digest(active["ticket"]),
                "MINICPM_PRE_NATIVE_ACTIVE_TICKET")
            require(v5.old.public_from_private(private_key) == self.grant["public_key"],
                "MINICPM_ORIGINAL_PRIVATE_KEY_REQUIRED")
            used = {item["closure"]["provider"]["kernel_id"] for item in state["closed"]}
            used.update(item["completion"]["verification"]["owner_receipt"]["kernel_id"] for item in state["completed"])
            used.update(self.registration["base"][name]["provider"]["kernel_id"]
                for name in ("serial7_closure", "serial8_closure"))
            require(kernel_id not in used, "MINICPM_DUPLICATE_OWNER_KERNEL")
            serial = active["ticket"]["payload"]["number"]
            require(not any((root / f"custody/{serial}").exists() or (root / self.seal_name(active)).exists()
                for root in (self.root, self.mirror)), "MINICPM_FAST_ACCEPT_ALREADY_STARTED")
            source = v5.private(safe(v5.ROOT, path))
            evidence = closure_snapshot(source)
            summary = super().check_closure(active, path, closure)
            require(closure_snapshot(source) == evidence, "MINICPM_FAST_CLOSURE_EVIDENCE_DRIFT")
            payload = {"download": path, "closure": closure, "summary": summary}
            seals = self.closure_seals(serial)
            existing = next((seal for seal in seals if seal.exists()), None)
            unix = self.read_closure_seal(existing)["payload"]["event_unix"] if existing else time.time()
            event = self.next_event(prenative.DISPOSITION, payload, unix=unix)
            envelope = v5.old.sign(private_key, self.grant["public_key"], self.closure_seal_payload(event, evidence))
            for seal in seals:
                v5.put(seal, json_bytes(envelope))
            self.commit(prenative.DISPOSITION, payload, unix=unix)
            return {"status": prenative.DISPOSITION, "reserved": state["reserved"], "next_ordinal": state["next_ordinal"]}

    def state(self):
        self._accepted = []
        state = super().state()
        # A package/custody/ticket file outside the visible journal requires
        # investigation. This also catches a removed reservation with files left.
        serials = {str(row["payload"]["ticket"]["payload"]["number"]) for row in self._rows
            if row["kind"] == "RESERVED_OFFLINE"}
        close_serials = {str(item["summary"]["number"]) for item in state["closed"]}
        if state["active"] is not None:
            close_serials.add(str(state["active"]["ticket"]["payload"]["number"]))
        for root in (self.root, self.mirror):
            for folder, expected in (("handoffs", serials), ("custody", serials),
                                      ("accept-verifications", {n + ".json" for n in serials}),
                                      ("closure-verifications", {n + ".json" for n in close_serials})):
                path = safe(root, folder)
                if path.exists():
                    snapshot_stat(path, directory=True)
                    require(all(item.name in expected for item in path.iterdir()), "MINICPM_FAST_UNJOURNALED_CUSTODY")
        return state

    def forecast(self):
        forecast = super().forecast()
        remaining = {key: self.grant["caps"]["total_" + key] - forecast["reserved"][key]
            for key in ("calls", "jobs", "gpu_seconds")}
        if self.historical_repo != contract.ROOT:
            forecast["runtime_release"] = "VERIFIED" if self.runtime_grant else "REQUIRED_BEFORE_STAGE"
            telemetry = forecast["telemetry"]
            if telemetry is not None and (self.runtime_grant is None
                or telemetry["source_sha256"] != self.runtime_grant["scope"]["source_sha256"]):
                forecast["telemetry"] = None
        max_calls = self.grant["caps"]["job_calls"]
        forecast["grant_capacity"] = {
            "remaining_reservations": remaining,
            "minimum_jobs_at_call_ceiling": (forecast["remaining_images"] + max_calls - 1) // max_calls,
            "max_seconds_per_job": self.grant["caps"]["job_seconds"],
            "weekly_quota": "FRESH_OWNER_GATE_REQUIRED",
        }
        if self.runtime_grant is not None and policy.serial22_recovery(self.runtime_grant):
            forecast["pre_native_seconds"] = policy.recovery_pre_native_seconds(self.runtime_grant)
            forecast["overhead_floor_seconds"] = policy.recovery_overhead_seconds(self.runtime_grant)
            forecast["approved_pr211_call_bound"] = self.runtime_grant["continuation"]["pr211_call_bound"]
        return forecast

    def next_event(self, kind, payload, *, unix):
        last = self._rows[-1]
        require(last["kind"] not in ("STOPPED", policy.RECONCILED), "MINICPM_OFFLINE_CLOSED")
        return {"schema": self.registration["schema"], "number": last["number"] + 1,
            "previous": digest(last), "kind": kind, "unix": unix, "payload": payload}

    def commit(self, kind, payload, *, unix=None):
        """Append under the V5 writer lock using the state just verified."""
        row = self.next_event(kind, payload, unix=time.time() if unix is None else unix)
        name = f"event-{row['number']:06d}.json"
        previous = f"event-{row['number'] - 1:06d}.json"
        for root in (self.root, self.mirror):
            pinned(safe(root, previous), row["previous"])
            require(not (root / name).exists(), "MINICPM_OFFLINE_TORN_MIRROR_STOP")
        expected = digest(row)
        for root in (self.root, self.mirror):
            v5.write(root / name, row)
            a.sync_directory(root)
            pinned(safe(root, name), expected)
        return row

    def accept(self, attempt, supervisor, receipt, proof, *, private_key):
        with v5.lock(self.root):
            state = self.state()
            require(not state["stopped"] and state["final"] is None and state["active"] is not None,
                "MINICPM_NO_ACTIVE_ACCEPT")
            active = state["active"]
            require(v5.old.public_from_private(private_key) == self.grant["public_key"],
                "MINICPM_ORIGINAL_PRIVATE_KEY_REQUIRED")
            serial = active["ticket"]["payload"]["number"]
            require(not any(path.exists() for path in self.closure_seals(serial)), "MINICPM_FAST_CLOSURE_ALREADY_STARTED")
            grant, _, _ = self.authority_for(active)
            folder = f"custody/{serial}"
            sources = {p.name: p for out in (Path(attempt), Path(supervisor))
                for p in (out, Path(str(out) + ".sha256.json"))}
            try:
                require(len(sources) == 4 and all(p.name.endswith((".zip", ".sha256.json")) for p in sources.values()),
                    "MINICPM_FAST_DISTINCT_OUTPUTS")
                for root in (self.root, self.mirror):
                    for name, source in {**sources, "terminal-proof.bin": Path(proof)}.items():
                        v5.copy(source, safe(root, folder + "/" + name))
                    v5.put(safe(root, folder + "/owner-receipt.json"), json_bytes(receipt))
                files = package_files(active, state["completed"])
                require(active["notebook"]["metadata"]["safeshift"]["runtime_ref"] == grant["runtime_commit"],
                    "MINICPM_FAST_V5_RUNTIME_REF")
                for root in (self.root, self.mirror):
                    check_package(safe(root, active["package"]), files)
                used = {entry["completion"]["verification"]["owner_receipt"]["kernel_id"] for entry in state["completed"]}
                used.update(entry["closure"]["provider"]["kernel_id"] for entry in state["closed"])
                used.update(self.registration["base"][name]["provider"]["kernel_id"]
                    for name in ("serial7_closure", "serial8_closure"))
                require(receipt["kernel_id"] not in used, "MINICPM_DUPLICATE_OWNER_KERNEL")
                result = {"ticket_sha256": digest(active["ticket"]), "attempt": folder + "/" + Path(attempt).name,
                    "supervisor": folder + "/" + Path(supervisor).name, "proof": folder + "/terminal-proof.bin"}
                verified = verify_new(grant, active, safe(self.root, result["attempt"]),
                    safe(self.root, result["supervisor"]), receipt, safe(self.root, result["proof"]))
                result["verification"] = verified
                for root in (self.root, self.mirror):
                    for name, expected in custody_files(result).items():
                        pinned(safe(root, name), expected)
            except Exception as error:
                self.commit("STOPPED", {"error_type": type(error).__name__, "ticket_sha256": digest(active["ticket"]),
                    "partial_evidence": "PRESERVED", "refund": False, "automatic_retry": False})
                raise ValueError("MINICPM_OFFLINE_ACCEPT_STOPPED:" + type(error).__name__) from None
            # A process can die here. Both signed verification files must precede
            # the event. A retry of the same active reservation can only finish
            # identical files. A torn event pair stops during journal loading.
            seals = [safe(root, self.seal_name(active)) for root in (self.root, self.mirror)]
            existing = next((path for path in seals if path.exists()), None)
            if existing:
                require(snapshot_stat(existing).st_size <= 8192, "MINICPM_FAST_SEAL_BOUND")
            unix = read(existing)["payload"]["event_unix"] if existing else time.time()
            event = self.next_event(v5.PROVISIONAL, result, unix=unix)
            envelope = v5.old.sign(private_key, self.grant["public_key"], self.seal_payload(event))
            for path in seals:
                v5.put(path, json_bytes(envelope))
            self.commit(v5.PROVISIONAL, result, unix=unix)
            return {"status": v5.PROVISIONAL, "counts": verified["report"]["counts"], "official": False}

    def stage(self, private_key, gate, gate_proof):
        with v5.lock(self.root):
            state = self.state()
            require(not state["stopped"] and state["final"] is None and state["active"] is None
                and state["next_ordinal"] < 3763, "MINICPM_ACTIVE_STOP_FINAL_OR_FINISHED")
            grant = self.runtime_grant or self.grant
            locator = self.runtime_locator or self.registration["locator"]
            exports = self.runtime_exports if self.runtime_grant else self.registration["exports"]
            require(self.runtime_grant is not None or self.historical_repo == contract.ROOT,
                "MINICPM_NEW_RUNTIME_RELEASE_REQUIRED_TO_STAGE")
            require(v5.authenticate(locator, exports) == grant, "MINICPM_STAGE_RUNTIME_AUTHORITY")
            v5.require_live_transition(grant, locator, exports)
            require(v5.old.public_from_private(private_key) == grant["public_key"],
                "MINICPM_ORIGINAL_PRIVATE_KEY_REQUIRED")
            require(0 < snapshot_stat(gate_proof).st_size <= 16*2**20, "MINICPM_OWNER_GATE_PROOF_BOUND")
            pinned(gate_proof, gate["proof_sha256"])
            completed = state["completed"]
            serial = state["reserved"]["jobs"] + 1
            name = self.grant["campaign_id"] + "-" + str(serial)
            job = "nguynanhtn/safeshift-minicpm-" + name
            capsule = "nguynanhtn/safeshift-minicpm-capsule-" + name + "/1"
            # The reviewed prefix may contain failure closures with no completion.
            if completed:
                prior = completed[-1]
                value = ui.next_capsule(prior["value"], prior["completion"]["verification"]["report"],
                    run_id=name, attempt_id=name+"-attempt", job=job, capsule_ref=capsule, max_calls=1, max_seconds=120)
            else:
                value = deepcopy(self.registration["initial"])
                value.update(job=job, capsule_ref=capsule)
                value["input_sources"]["dataset_sources"][-1] = capsule
            policy.owner_gate(grant, gate, value)
            telemetry = completed[-1]["completion"]["verification"]["telemetry"] if completed else None
            if telemetry is not None and telemetry["source_sha256"] != grant["scope"]["source_sha256"]:
                telemetry = None
            proposal = policy.proposal(grant, 3763-state["next_ordinal"], state["reserved"], gate, telemetry)
            request = value["request"]
            if self.runtime_grant is not None:
                t = self.runtime_grant["continuation"]
                require(serial >= t["first_serial"]
                    and (serial == t["first_serial"]) == (len(self._rows) == t["prefix_number"]),
                    "MINICPM_V5_TRANSITION_NEXT_SERIAL")
            request["source_sha256"] = grant["scope"]["source_sha256"]
            request["plan"] = contract.plan(request["campaign"], value["cohort"], grant["scope"]["identity"],
                request["history"], action="resume" if completed else "initial", run_id=name, attempt_id=name+"-attempt",
                max_calls=proposal["calls"], max_seconds=proposal["seconds"])
            from scripts.generate_minicpm_fulltrain_notebook import notebook
            options = {"bounded_launch": True} if policy.serial22_recovery(grant) else {}
            nb = notebook(grant["runtime_commit"], capsule_sha256=digest(value),
                release_locator=locator, release_version=policy.first_serial(grant), **options)
            before = state["reserved"]
            payload = {"schema": policy.ticket_schema(grant), "grant_sha256": digest(grant),
                "value_sha256": digest(value), "capsule_sha256": digest(value), "notebook_code_sha256": code_hash(nb),
                "number": serial, "previous_event_sha256": digest(self._rows[-1]), "reserved_before": before,
                "reserved_after": {"calls": before["calls"]+proposal["calls"], "jobs": before["jobs"]+1,
                    "gpu_seconds": before["gpu_seconds"]+2*proposal["seconds"]},
                "issued_unix": int(time.time()), "start_before_unix": gate["observed_unix"]+grant["provider_max_age_seconds"],
                "owner_gate": gate, "sizing": proposal, "lineage": self.lineage(completed),
                "closures": [row["summary"] for row in state["closed"]]}
            ticket = v5.old.sign(private_key, grant["public_key"], payload)
            a.verify_ticket(grant, ticket, value)
            proof_name = "gates/" + gate["proof_sha256"] + ".bin"
            for root in (self.root, self.mirror):
                v5.copy(gate_proof, safe(root, proof_name))
                pinned(safe(root, proof_name), gate["proof_sha256"])
            active = {"value": value, "ticket": ticket, "notebook": nb, "package": f"handoffs/{serial}", "gate_proof": proof_name}
            self.commit("RESERVED_OFFLINE", active)
            return self.export_package(active, completed)

    def export_active(self):
        with v5.lock(self.root):
            state = self.state()
            require(not state["stopped"] and state["final"] is None and state["active"] is not None,
                "MINICPM_NO_RECOVERABLE_ACTIVE_JOB")
            active = state["active"]
            serial = active["ticket"]["payload"]["number"]
            require(not any((root / f"custody/{serial}").exists() or (root / self.seal_name(active)).exists()
                for root in (self.root, self.mirror)), "MINICPM_FAST_ACCEPT_ALREADY_STARTED")
            require(not any(path.exists() for path in self.closure_seals(serial)), "MINICPM_FAST_CLOSURE_ALREADY_STARTED")
            return self.export_package(active, state["completed"])

    def export_package(self, active, completed):
        files = package_files(active, completed)
        value, ticket = active["value"], active["ticket"]
        signed = ticket["payload"]
        grant, _, _ = self.authority_for(active)
        require(time.time() < signed["start_before_unix"] and time.time() < grant["expires_unix"],
            "MINICPM_OFFLINE_TICKET_EXPIRED")
        require(active["notebook"]["metadata"]["safeshift"]["runtime_ref"] == grant["runtime_commit"],
            "MINICPM_FAST_V5_RUNTIME_REF")
        steps = {"status": "OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED", "job": value["job"], "version": 1,
            "capsule": value["capsule_ref"], "input_sources": value["input_sources"], "ticket_sha256": digest(ticket),
            "notebook_sha256": files["notebook.ipynb"], "ordinals": value["request"]["plan"]["scheduled_ordinals"],
            "limits": signed["sizing"], "start_before_unix": signed["start_before_unix"], "provider_verified": False,
            "steps": [
                'Upload capsule th\xe0nh Dataset Private m\u1edbi \u0111\xfang slug/version1; import notebook \u0111\xfang job/version1.',
                'G\u1eafn \u0111\xfang 5 Input; ki\u1ec3m Private/Python/Internet On/T4x2, quota tu\u1ea7n v\xe0 h\u1ea1n v\xe9; kh\xf4ng c\xf3 VM kh\xe1c.',
                'Save Version > Save & Run All m\u1ed9t l\u1ea7n; sau terminal t\u1ea3i c\u1ea3 hai ZIP/sidecar v\xe0 l\u01b0u proof/receipt th\u1eadt.',
            ]}
        for root in (self.root, self.mirror):
            pkg = safe(root, active["package"])
            v5.put(safe(pkg, "dataset/" + ui.MARKER), json_bytes(value))
            v5.put(safe(pkg, "dataset/" + minicpm_execution.MARKER), json_bytes(ticket))
            for prior, entry in zip(completed, value["ancestors"]):
                for suffix in ("", ".sha256.json"):
                    source = safe(root, prior["completion"]["attempt"] + suffix)
                    v5.copy(source, safe(pkg, "dataset/" + entry["file"] + suffix))
            v5.put(safe(pkg, "notebook.ipynb"), notebook_bytes(active["notebook"]))
            check_package(pkg, files)
            require(time.time() < signed["start_before_unix"], "MINICPM_OFFLINE_TICKET_EXPIRED")
            v5.put(safe(pkg, "owner-steps.json"), json_bytes(steps))
        return {"status": steps["status"], "directory": v5.relative(self.root / active["package"])}

    def full_verifier(self):
        historical = self.historical_repo if self.historical_repo != contract.ROOT else None
        release = (self.runtime_locator, self.runtime_exports) if self.runtime_grant else None
        return v5.Continuation(self.root, historical_repo=historical, runtime_release=release,
                               previous_runtime=self.previous_runtime)

    def manifest(self):
        return self.full_verifier().manifest()

    def reconcile(self, report, exports, owner_locator):
        return self.full_verifier().reconcile(report, exports, owner_locator)

    def official_report(self):
        return self.full_verifier().official_report()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("directory", "operator-release", "owner-exports"):
        parser.add_argument("--" + name, type=Path, required=True)
    v5.add_runtime_options(parser)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "forecast", "export-active"):
        sub.add_parser(name)
    proposal = sub.add_parser("runtime-release-template")
    proposal.add_argument("--output", type=Path, required=True)
    proposal.add_argument("--review-pr211-throughput", action="store_true")
    accept = sub.add_parser("accept")
    for name in ("attempt", "supervisor", "owner-receipt", "proof", "private-key"):
        accept.add_argument("--" + name, type=Path, required=True)
    close = sub.add_parser("close-pre-native")
    for name in ("download", "provider-closure", "private-key"):
        close.add_argument("--" + name, type=Path, required=True)
    close.add_argument("--kernel-id", type=int, required=True)
    stage = sub.add_parser("stage")
    for name in ("private-key", "owner-gate", "proof"):
        stage.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    route = Continuation(args.directory, read(v5.private(args.operator_release)), read(v5.private(args.owner_exports)),
        **v5.runtime_options(args))
    if args.command == "runtime-release-template":
        value = route.runtime_proposal(review_pr211_throughput=args.review_pr211_throughput)
        write(v5.private(args.output), value)
        result = {"status": "UNSIGNED_PROPOSAL_BLOCKED_NOT_AUTHORITY", "marker_required": policy.SERIAL9_RELEASE,
            "first_serial": value["continuation"]["first_serial"]}
    elif args.command == "accept":
        result = route.accept(args.attempt, args.supervisor, read(args.owner_receipt), args.proof, private_key=args.private_key)
    elif args.command == "close-pre-native":
        result = route.close_pre_native(args.download, read(args.provider_closure), private_key=args.private_key,
            kernel_id=args.kernel_id)
    elif args.command == "stage":
        result = route.stage(args.private_key, read(args.owner_gate), args.proof)
    elif args.command == "export-active":
        result = route.export_active()
    elif args.command == "forecast":
        result = route.forecast()
    else:
        state = route.state()
        result = {key: state[key] for key in ("status", "counts", "reserved", "next_ordinal", "stopped")}
        result["closed_pre_native"] = [{"serial": item["summary"]["number"],
            "kernel_id": item["closure"]["provider"]["kernel_id"], "ticket_sha256": item["summary"]["ticket_sha256"]}
            for item in state["closed"]]
        result["active"] = None if state["active"] is None else {
            "serial": state["active"]["ticket"]["payload"]["number"], "job": state["active"]["value"]["job"],
            "ticket_sha256": digest(state["active"]["ticket"])}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
