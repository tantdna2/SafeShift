"""MiniCPM serial companion. New ticket preparation rechecks live GitHub authority.

An authentic NEW merged-source release and original Operator identity/key are
required. Originals are frozen; all new events live in a separate mirrored
create-only journal. Local verification is provisional until final admission.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write, write_bytes, sha, safe, import_archive
from safeshift.pilot.contract import digest, json_bytes
from safeshift.fulltrain import contract, minicpm_release as a, minicpm_ui as ui
from safeshift.fulltrain import minicpm_offline as policy, minicpm_v5_incident as v5, minicpm_serial6 as serial6
from safeshift.fulltrain import minicpm_serial7 as serial7
from scripts import minicpm_fulltrain_operator as old

SCHEMA = policy.SCHEMA
PROVISIONAL = "OFFLINE_VERIFIED_PROVISIONAL"


class Exports:
    """Owner-acquired evidence only; never fallback to a network transport.

    JSON cannot authenticate its own origin. Owner export custody and direct
    inspection of GitHub originals are the explicit trust boundary, as in PR196.
    """
    def __init__(self, values):
        require(type(values) is dict and len(values) <= 256, "MINICPM_OWNER_EXPORT_BOUND")
        self.values = values

    def __call__(self, path):
        require(path in self.values, "MINICPM_MISSING_AUTHENTIC_OWNER_EXPORT:" + path)
        return deepcopy(self.values[path])


def tools_manifest():
    return {name: sha(Path(__file__).with_name(name)) for name in policy.TOOLS}


def tool_blobs():
    result = {}
    for name in policy.TOOLS:
        raw = Path(__file__).with_name(name).read_bytes()
        result["scripts/"+name] = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    return result


def private(path):
    path = Path(path).absolute()
    require(path.is_relative_to(ROOT / "data/processed"), "MINICPM_IGNORED_PRIVATE_CUSTODY_REQUIRED")
    safe(ROOT, path.relative_to(ROOT).as_posix())
    return path


def relative(path):
    return private(path).relative_to(ROOT).as_posix()


def fence():
    return ROOT / "data/processed/minicpm-release-registrations/mcpm4-restart-v1-offline-post-serial6.json"


def transition_fence():
    return ROOT / "data/processed/minicpm-release-registrations/mcpm4-restart-v1-offline-post-serial7.json"


def put(path, payload):
    """Recovery may finish a missing file; never replace partial/conflicting bytes."""
    if path.exists():
        snapshot_stat(path)
        require(path.read_bytes() == payload, "MINICPM_PARTIAL_OR_CHANGED_FILE_PRESERVED_STOP")
    else:
        write_bytes(path, payload)
        a.sync_directory(path.parent)


def copy(source, target):
    snapshot_stat(source)
    if target.exists():
        snapshot_stat(target)
        require(sha(source) == sha(target), "MINICPM_PARTIAL_COPY_PRESERVED_STOP")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    with Path(source).open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst, 2**20)
        dst.flush(); os.fsync(dst.fileno())
    require(sha(source) == sha(target), "MINICPM_COPY_CHANGED")
    a.sync_directory(target.parent)


def authenticate(locator, exports, *, collection=False):
    grant = a.load(locator, reader=Exports(exports), collection=collection)
    policy.validate_delegation(grant)
    require(grant["operator_host_sha256"] == old.host(), "MINICPM_ORIGINAL_OPERATOR_HOST_REQUIRED")
    require(grant["offline"]["tools_sha256"] == digest(tools_manifest()), "MINICPM_REVIEWED_OFFLINE_TOOLS")
    require(grant["offline"]["tool_blobs"] == tool_blobs(), "MINICPM_REVIEWED_OFFLINE_TOOL_BLOBS")
    return grant


def require_live_transition(grant, locator, exports):
    if a.uses_proof(grant):
        proof = a.collect_proof(grant, locator, Exports(exports))
        require(a.load(locator, stage_proof=proof) == grant, "MINICPM_SERIAL8_LIVE_RELEASE_REQUIRED")


def snapshot_files(paths):
    result = {}
    for path in paths:
        snapshot_stat(path)
        result[relative(path)] = sha(path)
    return result


def tree_files(root):
    """Bounded custody walk of explicit Operator evidence, never TRAIN/TEST."""
    pending, found, count = [Path(root)], [], 0
    while pending:
        parent = pending.pop()
        snapshot_stat(parent, directory=True)
        for item in parent.iterdir():
            count += 1
            require(count <= 20000, "MINICPM_CUSTODY_SCAN_BOUND")
            if item.is_dir():
                snapshot_stat(item, directory=True); pending.append(item)
            else:
                snapshot_stat(item); found.append(item)
    return found


def historical(grant, closure):
    """Read the exact original prefix and failures without appending any event."""
    from scripts import minicpm_fulltrain_recovery as recovery, minicpm_v5_incident as incident
    journal = recovery.RecoveredSerialJournal()
    events = journal.events()
    previous = incident.prefix(events)
    require(previous["journal_head_sha256"] == grant["offline"]["base_journal_head_sha256"],
        "MINICPM_EXACT_UNCHANGED_PRE_SERIAL6_JOURNAL")
    recovery.verify_retired(grant["recovery"])
    recovery.verify_v44_prefix(events)
    report = incident.verify_evidence(closure, previous)
    require(digest(report) == grant["repair"]["closure_sha256"], "MINICPM_V5_CLOSURE_PIN")
    paths = tree_files(closure)
    paths += tree_files(safe(ROOT, events[6]["payload"]["closure_directory"]))
    for row in grant["recovery"]["journals"]:
        for key in ("root", "mirror"):
            root = safe(ROOT, row[key])
            paths += [p for p in root.iterdir() if p.name.startswith("event-") and p.suffix == ".json"]
        for proof in row["evidence"]:
            paths.append(safe(ROOT, proof["path"]))
        paths.append(ROOT / "data/processed/minicpm-release-registrations" / (row["campaign_id"] + ".json"))
    sixth, local_files = serial6.verify_local(ROOT / "data/processed")
    return {"files": snapshot_files(paths + local_files), "serial6": sixth, "events": events, "v5_closure": report,
        "v5_directory": relative(closure), "reserved": deepcopy(serial6.RESERVED),
        "disposition": "HISTORICAL_HOLDS_UNCHANGED_NO_PREDICTIONS_NO_REFUND"}


def verify_local(grant, active, package, attempt, supervisor, receipt, proof):
    """Reuse actual strict raw/parser/native/ancestor and PR201 RAM verifiers."""
    value, ticket = active["value"], active["ticket"]
    a.verify_ticket(grant, ticket, value, collection=True)
    require(0 < snapshot_stat(proof).st_size <= 16*2**20, "MINICPM_TERMINAL_PROOF_BOUND")
    require(sha(proof) == receipt["proof_sha256"], "MINICPM_TERMINAL_PROOF_BYTES_REQUIRED")
    policy.terminal(receipt, value, sha(attempt), sha(supervisor))
    require(attempt.name == value["request"]["plan"]["run_id"] + ".zip", "MINICPM_EXACT_OUTPUT_NAME")
    require(len(supervisor.stem) == 32 and all(c in "0123456789abcdef" for c in supervisor.stem),
        "MINICPM_EXACT_SUPERVISOR_NAME")
    from safeshift.internvl3763_operator import code_hash
    nb = read(package / "notebook.ipynb")
    require(code_hash(nb) == ticket["payload"]["notebook_code_sha256"]
        and nb["metadata"]["safeshift"]["source_sha256"] == grant["scope"]["source_sha256"]
        and nb["metadata"]["safeshift"]["capsule_sha256"] == digest(value)
        and nb["metadata"]["safeshift"]["runtime_ref"] == grant["runtime_commit"], "MINICPM_EXACT_SIGNED_NOTEBOOK")
    require(read(package / "dataset" / ui.MARKER) == value, "MINICPM_CAPSULE_VALUE_CUSTODY")
    from safeshift.fulltrain.minicpm_execution import MARKER
    require(read(package / "dataset" / MARKER) == ticket, "MINICPM_CAPSULE_TICKET_CUSTODY")
    timing = old.verify_claims(value, ticket, grant, attempt, supervisor)
    with tempfile.TemporaryDirectory() as tmp:
        report = ui.verify_results(value, package / "dataset", attempt, supervisor,
            Path(tmp) / "verified", memory_required=True)
    require(report["continuation"] == "REVIEW_CAPS_AND_RELEASE", "MINICPM_TECHNICAL_FAILURE_STOP_NO_RETRY")
    rows = [r for r in report["history"][-1]["records"] if r["status"] != "NOT_ATTEMPTED"]
    require(rows and all(r["status"] in ("SUCCESS", "INVALID") for r in rows),
        "MINICPM_ONLY_DURABLE_COMPLETION")
    return {"report": report, "telemetry": old.telemetry_record(timing, attempt, supervisor, ticket),
        "owner_receipt": receipt, "terminal_proof_sha256": sha(proof),
        "sidecars": {"attempt": sha(str(attempt) + ".sha256.json"), "supervisor": sha(str(supervisor) + ".sha256.json")},
        "provider_verification": "PENDING_FINAL_RECONCILIATION", "scientific_qualified": False}


class Continuation:
    def __init__(self, root):
        self.root = private(root)
        require(snapshot_stat(safe(self.root, "registration.json")).st_size <= 64*2**20, "MINICPM_REGISTRATION_BOUND")
        self.registration = read(safe(self.root, "registration.json"))
        self.mirror = private(safe(ROOT, self.registration["mirror"]))
        self.distinct(self.root, self.mirror)
        require((self.root / "registration.json").read_bytes() == (self.mirror / "registration.json").read_bytes(),
            "MINICPM_OFFLINE_REGISTRATION_MIRROR")
        self.grant = authenticate(self.registration["locator"], self.registration["exports"], collection=True)
        transition = a.uses_proof(self.grant)
        require(self.registration["schema"] == (policy.TRANSITION_SCHEMA if transition else SCHEMA)
            and self.registration["root"] == relative(self.root)
            and read(transition_fence() if transition else fence()) ==
                {"root": relative(self.root), "registration_sha256": digest(self.registration)},
            "MINICPM_OFFLINE_SINGLE_REGISTRATION")
        require(self.registration["grant_sha256"] == digest(self.grant), "MINICPM_OFFLINE_REGISTERED_GRANT")
        if transition:
            report, active, _ = serial7.verify_local(ROOT / "data/processed")
            closure = self.registration["base"]["serial7_closure"]
            serial7.verify_closure(closure, report, active)
            require(digest(closure) == self.grant["offline"]["serial7"]["provider_closure_sha256"],
                "MINICPM_SERIAL8_OWNER_CLOSURE_PIN")

    @staticmethod
    def distinct(root, mirror):
        require(root != mirror and not root.is_relative_to(mirror) and not mirror.is_relative_to(root),
            "MINICPM_OFFLINE_DISTINCT_MIRRORS")

    @classmethod
    def initialize(cls, root, mirror, locator, exports, initial, closure, operator_session, *, serial7_closure=None):
        root, mirror, closure = private(root), private(mirror), private(closure)
        cls.distinct(root, mirror)
        grant = authenticate(locator, exports)
        transition = a.uses_proof(grant)
        require(transition == (serial7_closure is not None), "MINICPM_SERIAL8_CLOSURE_REQUIRED")
        registration_fence = transition_fence() if transition else fence()
        require(operator_session == grant["offline"]["operator_session"], "MINICPM_ORIGINAL_SESSION_ACK_REQUIRED")
        old.clean_source(grant)
        require_live_transition(grant, locator, exports)
        a.bind(grant, initial)
        require(initial["request"]["history"] == initial["ancestors"] == []
            and initial["request"]["plan"]["action"] == "initial"
            and initial["request"]["plan"]["counts"] == {"NOT_ATTEMPTED": 3763}
            and initial["request"]["plan"]["scheduled_ordinals"][0] == 0, "MINICPM_OFFLINE_EMPTY_HISTORY")
        require(not root.exists() and not mirror.exists() and not registration_fence.exists(),
            "MINICPM_NO_OFFLINE_REINITIALIZATION")
        for dest in (root, mirror):
            names = ("minicpm-offline", "minicpm-offline-mirror", "inspect_run_6")
            if transition:
                names += (serial7.PRIMARY, serial7.MIRROR, "inspect_run_7")
            for name in names:
                cls.distinct(dest, ROOT / "data/processed" / name)
        legacy = ROOT / "data/processed/minicpm-v3-journal"
        with lock(legacy):
            base = historical(grant, closure)
            if transition:
                local, active, files = serial7.verify_local(ROOT / "data/processed")
                serial7.verify_closure(serial7_closure, local, active)
                require(digest(serial7_closure) == grant["offline"]["serial7"]["provider_closure_sha256"]
                    and initial["cohort"] == active["value"]["cohort"],
                    "MINICPM_SERIAL8_OWNER_CLOSURE_OR_TRAIN_COHORT")
                base["files"].update(snapshot_files(files))
                base["serial7_closure"] = serial7_closure
                base["reserved"] = dict(serial7.RESERVED)
            for p in (root, mirror):
                require(not any(p.is_relative_to(safe(ROOT, row[k])) or safe(ROOT, row[k]).is_relative_to(p)
                    for row in grant["recovery"]["journals"] for k in ("root", "mirror")),
                    "MINICPM_NEW_CUSTODY_OUTSIDE_ORIGINALS")
            registration = {"schema": policy.TRANSITION_SCHEMA if transition else SCHEMA,
                "root": relative(root), "mirror": relative(mirror),
                "locator": locator, "exports": exports, "grant_sha256": digest(grant), "initial": initial,
                "base": base, "operator_session": operator_session}
            # Durable fence first. A torn initialization blocks every route;
            # never guess how to fill missing state or consume another slot.
            registration_fence.parent.mkdir(parents=True, exist_ok=True)
            write(registration_fence, {"root": relative(root), "registration_sha256": digest(registration)})
            a.sync_directory(registration_fence.parent)
            for p in (root, mirror):
                p.mkdir(parents=True, exist_ok=False)
                write(p / "registration.json", registration); a.sync_directory(p)
        return cls(root)

    def events(self):
        for name, expected in self.registration["base"]["files"].items():
            require(sha(safe(ROOT, name)) == expected, "MINICPM_ORIGINAL_BYTES_CHANGED_STOP")
        # Detect extra legacy events as well as edits/deletions of old files.
        for root in {str(Path(n).parent) for n in self.registration["base"]["files"] if Path(n).name.startswith("event-")}:
            expected = {n for n in self.registration["base"]["files"] if str(Path(n).parent) == root and Path(n).name.startswith("event-")}
            require({relative(p) for p in safe(ROOT, Path(root).as_posix()).glob("event-*.json")} == expected,
                "MINICPM_LEGACY_APPEND_AFTER_MIGRATION_STOP")
        names = sorted(p.name for p in self.root.glob("event-*.json"))
        require(len(names) <= 20000 and names == sorted(p.name for p in self.mirror.glob("event-*.json")),
            "MINICPM_OFFLINE_TORN_MIRROR_STOP")
        rows, previous = [], digest(self.registration)
        for i, name in enumerate(names, 1):
            for root in (self.root, self.mirror):
                require(snapshot_stat(safe(root, name)).st_size <= 128*2**20, "MINICPM_OFFLINE_EVENT_BOUND")
            require(name == f"event-{i:06d}.json" and (self.root / name).read_bytes() == (self.mirror / name).read_bytes(),
                "MINICPM_OFFLINE_GAP_OR_DIVERGENCE")
            row = read(safe(self.root, name))
            require(row["schema"] == self.registration.get("schema", SCHEMA)
                and row["previous"] == previous and row["number"] == i,
                "MINICPM_OFFLINE_CHAIN")
            previous = digest(row); rows.append(row)
        return rows

    def append(self, kind, payload):
        rows = self.events()
        require(not rows or rows[-1]["kind"] not in ("STOPPED", policy.RECONCILED), "MINICPM_OFFLINE_CLOSED")
        row = {"schema": self.registration.get("schema", SCHEMA), "number": len(rows) + 1,
            "previous": digest(rows[-1]) if rows else digest(self.registration),
            "kind": kind, "unix": time.time(), "payload": payload}
        for p in (self.root, self.mirror):
            write(p / f"event-{len(rows)+1:06d}.json", row); a.sync_directory(p)
        self.events()
        return row

    def state(self, *, verify=True):
        reserved, active, completed = policy.initial_hold(self.grant), None, []
        history, rows, stopped, final = [], self.events(), False, None
        kernels, jobs = set(), set()
        for e in rows:
            p = e["payload"]
            require(not stopped and final is None, "MINICPM_OFFLINE_EVENT_AFTER_STOP_OR_FINAL")
            if e["kind"] == "RESERVED_OFFLINE":
                require(active is None, "MINICPM_ONLY_ONE_ACTIVE_JOB")
                a.verify_ticket(self.grant, p["ticket"], p["value"], collection=True)
                require(p["ticket"]["payload"]["previous_event_sha256"] == e["previous"]
                    and p["ticket"]["payload"]["reserved_before"] == reserved
                    and p["value"]["request"]["history"] == history
                    and p["ticket"]["payload"]["lineage"] == self.lineage(completed), "MINICPM_OFFLINE_RESERVATION_HISTORY")
                require(p["value"]["job"] not in jobs, "MINICPM_DUPLICATE_JOB")
                for root in (self.root, self.mirror):
                    require(sha(safe(root, p["gate_proof"])) == p["ticket"]["payload"]["owner_gate"]["proof_sha256"],
                        "MINICPM_OWNER_GATE_CUSTODY")
                jobs.add(p["value"]["job"])
                reserved = p["ticket"]["payload"]["reserved_after"]
                active = p
            elif e["kind"] == PROVISIONAL:
                require(active is not None and p["ticket_sha256"] == digest(active["ticket"]), "MINICPM_OFFLINE_COMPLETION_ORDER")
                if verify:
                    require(self.recheck(active, p) == p["verification"], "MINICPM_OFFLINE_CUSTODY_DRIFT")
                history = p["verification"]["report"]["history"]
                kernel = p["verification"]["owner_receipt"]["kernel_id"]
                require(kernel not in kernels, "MINICPM_DUPLICATE_OWNER_KERNEL")
                kernels.add(kernel)
                completed.append({**active, "completion": p}); active = None
            elif e["kind"] == "STOPPED":
                stopped = True
            elif e["kind"] == policy.RECONCILED:
                require(active is None and len(completed) > 0, "MINICPM_FINAL_SEQUENCE")
                final = e
            else:
                raise ValueError("MINICPM_UNKNOWN_OFFLINE_EVENT")
        ordinals = {r["sample_id"]: r["ordinal"] for r in self.registration["initial"]["cohort"]["samples"]}
        records = [{**r, "ordinal": ordinals[r["sample_id"]]} for h in history for r in h["records"] if r["status"] != "NOT_ATTEMPTED"]
        require([r["ordinal"] for r in records] == list(range(len(records))) and len(records) <= 3763
            and all(r["status"] in ("SUCCESS", "INVALID") for r in records), "MINICPM_OFFLINE_NO_SKIP_DUPLICATE_OR_ERROR")
        return {"reserved": reserved, "active": active, "completed": completed, "history": history, "records": records,
            "next_ordinal": len(records), "counts": dict(Counter(r["status"] for r in records)) | {"NOT_ATTEMPTED": 3763-len(records)},
            "stopped": stopped, "final": final, "status": "STOPPED" if stopped else
                "FINAL_EVENT_PRESENT_USE_OFFICIAL_REPORT" if final is not None else "PENDING_FINAL_RECONCILIATION"}

    @staticmethod
    def lineage(completed):
        return [{"number": item["ticket"]["payload"]["number"], "ticket_sha256": digest(item["ticket"]),
            "history_sha256": digest(item["completion"]["verification"]["report"]["history"][-1]),
            "owner_receipt_sha256": digest(item["completion"]["verification"]["owner_receipt"]),
            "reserved_after": item["ticket"]["payload"]["reserved_after"]} for item in completed]

    def forecast(self):
        state = self.state()
        require(not state["stopped"] and state["final"] is None and state["active"] is None
            and state["next_ordinal"] < 3763, "MINICPM_FORECAST_ACTIVE_STOP_FINAL_OR_FINISHED")
        serial = state["reserved"]["jobs"]+1
        name = self.grant["campaign_id"]+"-"+str(serial)
        inputs = deepcopy(self.registration["initial"]["input_sources"])
        inputs["dataset_sources"][-1] = "nguynanhtn/safeshift-minicpm-capsule-"+name+"/1"
        return {"status": "OWNER_GATE_REQUIRED_NOT_A_TICKET", "remaining_images": 3763-state["next_ordinal"],
            "next_ordinal": state["next_ordinal"], "reserved": state["reserved"], "caps": self.grant["caps"],
            "sizing_policy": self.grant["sizing"], "unmeasured_calls": self.grant["offline"]["unmeasured_calls"],
            "telemetry": state["completed"][-1]["completion"]["verification"]["telemetry"] if state["completed"] else None,
            "population_model_fit": "NOT_ESTABLISHED", "fixed_job_count": None,
            "owner_gate_template": {"observed_unix": None, "quota": {"used": None, "reserved": None, "total": None},
                "job": "nguynanhtn/safeshift-minicpm-"+name, "version": 1, "inputs": inputs,
                "no_active_job": False, "job_absent": False, "owner_checked": False, "proof_sha256": None}}

    def recheck(self, active, completion):
        paths = {k: safe(self.root, completion[k]) for k in ("attempt", "supervisor", "proof")}
        for key, path in paths.items():
            mirror = safe(self.mirror, completion[key])
            require(sha(path) == sha(mirror), "MINICPM_OFFLINE_EVIDENCE_MIRROR")
            if key != "proof":
                require(sha(str(path)+".sha256.json") == sha(str(mirror)+".sha256.json"), "MINICPM_OFFLINE_SIDECAR_MIRROR")
        return verify_local(self.grant, active, safe(self.root, active["package"]), paths["attempt"], paths["supervisor"],
            completion["verification"]["owner_receipt"], paths["proof"])

    def stage(self, private_key, gate, gate_proof):
        with lock(self.root):
            state = self.state()
            require(not state["stopped"] and state["final"] is None and state["active"] is None
                and state["next_ordinal"] < 3763, "MINICPM_ACTIVE_STOP_FINAL_OR_FINISHED")
            authenticate(self.registration["locator"], self.registration["exports"])
            require_live_transition(self.grant, self.registration["locator"], self.registration["exports"])
            require(old.public_from_private(private_key) == self.grant["public_key"], "MINICPM_ORIGINAL_PRIVATE_KEY_REQUIRED")
            require(0 < snapshot_stat(gate_proof).st_size <= 16*2**20, "MINICPM_OWNER_GATE_PROOF_BOUND")
            require(sha(gate_proof) == gate["proof_sha256"], "MINICPM_OWNER_GATE_PROOF_BYTES")
            completed = state["completed"]
            serial = state["reserved"]["jobs"] + 1
            name = self.grant["campaign_id"] + "-" + str(serial)
            job, capsule = "nguynanhtn/safeshift-minicpm-" + name, "nguynanhtn/safeshift-minicpm-capsule-" + name + "/1"
            if completed:
                prior = completed[-1]
                value = ui.next_capsule(prior["value"], prior["completion"]["verification"]["report"],
                    run_id=name, attempt_id=name+"-attempt", job=job, capsule_ref=capsule, max_calls=1, max_seconds=120)
            else:
                value = deepcopy(self.registration["initial"])
                value.update(job=job, capsule_ref=capsule)
                value["input_sources"]["dataset_sources"][-1] = capsule
            policy.owner_gate(self.grant, gate, value)
            telemetry = completed[-1]["completion"]["verification"]["telemetry"] if completed else None
            proposal = policy.proposal(self.grant, 3763-state["next_ordinal"], state["reserved"], gate, telemetry)
            r = value["request"]
            r["plan"] = contract.plan(r["campaign"], value["cohort"], r["plan"]["identity"], r["history"],
                action="resume" if completed else "initial", run_id=name, attempt_id=name+"-attempt",
                max_calls=proposal["calls"], max_seconds=proposal["seconds"])
            from scripts.generate_minicpm_fulltrain_notebook import notebook
            from safeshift.internvl3763_operator import code_hash
            nb = notebook(self.grant["runtime_commit"], capsule_sha256=digest(value),
                release_locator=self.registration["locator"], release_version=policy.first_serial(self.grant))
            events = self.events()
            before = state["reserved"]
            payload = {"schema": policy.TRANSITION_TICKET if a.uses_proof(self.grant) else policy.TICKET,
                "grant_sha256": digest(self.grant), "value_sha256": digest(value),
                "capsule_sha256": digest(value), "notebook_code_sha256": code_hash(nb), "number": serial,
                "previous_event_sha256": digest(events[-1]) if events else digest(self.registration),
                "reserved_before": before, "reserved_after": {"calls": before["calls"]+proposal["calls"],
                    "jobs": before["jobs"]+1, "gpu_seconds": before["gpu_seconds"]+2*proposal["seconds"]},
                "issued_unix": int(time.time()), "start_before_unix": gate["observed_unix"]+self.grant["provider_max_age_seconds"],
                "owner_gate": gate, "sizing": proposal, "lineage": self.lineage(completed)}
            ticket = old.sign(private_key, self.grant["public_key"], payload)
            a.verify_ticket(self.grant, ticket, value)
            proof_name = "gates/"+gate["proof_sha256"]+".bin"
            for root in (self.root, self.mirror): copy(gate_proof, root / proof_name)
            # Reserve BEFORE exposing any uploadable file. Failures keep it active.
            self.append("RESERVED_OFFLINE", {"value": value, "ticket": ticket, "notebook": nb,
                "package": "handoffs/"+str(serial), "gate_proof": proof_name})
            return self.export_active()

    def export_active(self):
        state = self.state()
        require(not state["stopped"] and state["final"] is None and state["active"] is not None, "MINICPM_NO_RECOVERABLE_ACTIVE_JOB")
        item = state["active"]
        value, ticket = item["value"], item["ticket"]
        from safeshift.fulltrain.minicpm_execution import MARKER
        from safeshift.internvl3763_operator import code_hash
        require(code_hash(item["notebook"]) == ticket["payload"]["notebook_code_sha256"], "MINICPM_RECOVERY_NOTEBOOK_PIN")
        steps = {"status": "OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED", "job": value["job"], "version": 1,
            "capsule": value["capsule_ref"], "input_sources": value["input_sources"], "ticket_sha256": digest(ticket),
            "notebook_sha256": hashlib.sha256((json.dumps(item["notebook"], indent=1, ensure_ascii=False)+"\n").encode()).hexdigest(),
            "ordinals": value["request"]["plan"]["scheduled_ordinals"], "limits": ticket["payload"]["sizing"],
            "start_before_unix": ticket["payload"]["start_before_unix"], "provider_verified": False,
            "steps": ["Upload capsule thành Dataset Private mới đúng slug/version1; import notebook đúng job/version1.",
                "Gắn đúng 5 Input; kiểm Private/Python/Internet On/T4x2, quota tuần và hạn vé; không có VM khác.",
                "Save Version > Save & Run All một lần; sau terminal tải cả hai ZIP/sidecar và lưu proof/receipt thật."]}
        ancestors = [safe(self.root, c["completion"]["attempt"]) for c in state["completed"]]
        for root in (self.root, self.mirror):
            pkg = safe(root, item["package"])
            put(pkg / "dataset" / ui.MARKER, json_bytes(value))
            put(pkg / "dataset" / MARKER, json_bytes(ticket))
            for source, entry in zip(ancestors, value["ancestors"]):
                copy(source, pkg / "dataset" / entry["file"])
                copy(Path(str(source)+".sha256.json"), pkg / "dataset" / (entry["file"]+".sha256.json"))
            put(pkg / "notebook.ipynb", (json.dumps(item["notebook"], indent=1, ensure_ascii=False)+"\n").encode())
            put(pkg / "owner-steps.json", json_bytes(steps))
            ui.verify_capsule(pkg / "dataset", digest(value), release_ticket=True)
        return {"status": steps["status"], "directory": relative(self.root / item["package"])}

    def accept(self, attempt, supervisor, receipt, proof):
        with lock(self.root):
            state = self.state()
            require(not state["stopped"] and state["final"] is None and state["active"] is not None, "MINICPM_NO_ACTIVE_ACCEPT")
            active = state["active"]
            folder = "custody/" + str(active["ticket"]["payload"]["number"])
            # Preserve originals first, including bad/partial evidence, then STOP.
            try:
                for root in (self.root, self.mirror):
                    for p in (Path(attempt), Path(str(attempt)+".sha256.json"), Path(supervisor),
                              Path(str(supervisor)+".sha256.json")):
                        copy(p, root / folder / p.name)
                    copy(proof, root / folder / "terminal-proof.bin")
                    put(root / folder / "owner-receipt.json", json_bytes(receipt))
                attempt_path, supervisor_path = self.root/folder/Path(attempt).name, self.root/folder/Path(supervisor).name
                verified = verify_local(self.grant, active, safe(self.root, active["package"]), attempt_path,
                    supervisor_path, receipt, self.root/folder/"terminal-proof.bin")
                result = {"ticket_sha256": digest(active["ticket"]), "verification": verified,
                    "attempt": folder+"/"+attempt_path.name, "supervisor": folder+"/"+supervisor_path.name,
                    "proof": folder+"/terminal-proof.bin"}
                self.append(PROVISIONAL, result)
                self.state()
                return {"status": PROVISIONAL, "counts": verified["report"]["counts"], "official": False}
            except BaseException as error:
                # Exception text can contain private paths/URLs. Preserve only type.
                self.append("STOPPED", {"error_type": type(error).__name__, "ticket_sha256": digest(active["ticket"]),
                    "partial_evidence": "PRESERVED", "refund": False, "automatic_retry": False})
                raise ValueError("MINICPM_OFFLINE_ACCEPT_STOPPED:"+type(error).__name__) from None

    def manifest(self):
        state = self.state()
        require(not state["stopped"] and state["active"] is None and state["next_ordinal"] == 3763, "MINICPM_FINAL_FULL3763_ONLY")
        attempts = state["completed"]
        return {"schema": self.registration.get("schema", SCHEMA),
            "registration_sha256": digest(self.registration), "grant_sha256": digest(self.grant),
            "historical": self.registration["base"], "attempts": attempts, "rows": state["records"],
            "ordinals": list(range(3763)), "counts": state["counts"], "reserved": state["reserved"],
            "caps": self.grant["caps"], "billing_gpu_seconds": "NOT_OBSERVED", "scientific_qualified": False}

    def validate_final(self, manifest, report, exports, owner_locator):
        from safeshift.fulltrain.minicpm_incident import owner_record
        reader = Exports(exports)
        authenticate(self.registration["locator"], exports, collection=True)
        owner = owner_record(reader, owner_locator, 202)
        require(a.record(owner["body"], policy.FINAL) == {"manifest_sha256": digest(manifest),
            "report_sha256": digest(report), "status": "APPROVED_FOR_FINAL_ADMISSION"}, "MINICPM_AUTHENTIC_FINAL_OWNER")
        validate_provider_report(manifest, report)
        return report

    def reconcile(self, report, exports, owner_locator):
        with lock(self.root):
            require(self.state()["final"] is None, "MINICPM_NO_DUPLICATE_FINAL_ADMISSION")
            manifest = self.manifest()
            self.validate_final(manifest, report, exports, owner_locator)
            # Keep the one final event small even for many jobs. The complete
            # ordered documents are separate, mirrored, create-only and bound
            # by the certificate; never duplicate all cumulative histories in
            # a journal event with its stricter 128 MiB envelope.
            documents = {"manifest": manifest, "report": report, "exports": exports}
            for name, value in documents.items():
                raw = json_bytes(value)
                require(len(raw) <= 8*2**30, "MINICPM_FINAL_DOCUMENT_BOUND")
                for root in (self.root, self.mirror): put(root/"final"/(name+".json"), raw)
            return self.append(policy.RECONCILED, {**{name+"_sha256": digest(value) for name,value in documents.items()},
                "owner": owner_locator})

    def official_report(self):
        state = self.state()
        require(state["final"] is not None and not state["stopped"], "MINICPM_OFFICIAL_RESULTS_BLOCKED_PENDING_FINAL_ADMISSION")
        p = state["final"]["payload"]
        documents = {}
        for name in ("manifest", "report", "exports"):
            for root in (self.root,self.mirror):
                path=safe(root,"final/"+name+".json")
                require(snapshot_stat(path).st_size <= 8*2**30 and sha(path)==p[name+"_sha256"], "MINICPM_FINAL_DOCUMENT_BYTES")
            documents[name]=read(self.root/"final"/(name+".json"))
        manifest = self.manifest()
        require(documents["manifest"] == manifest, "MINICPM_FINAL_MANIFEST_DRIFT")
        self.validate_final(manifest, documents["report"], documents["exports"], p["owner"])
        ordinals = {r["sample_id"]: r["ordinal"] for r in self.registration["initial"]["cohort"]["samples"]}
        lineage = [{"ordinal": ordinals[row["sample_id"]], "sample_id": row["sample_id"], "run_id": item["value"]["request"]["plan"]["run_id"],
            "attempt_id": item["value"]["request"]["plan"]["attempt_id"], "job": item["value"]["job"],
            "ticket_sha256": digest(item["ticket"]), "source_sha256": item["value"]["request"]["source_sha256"],
            "archive_sha256": item["completion"]["verification"]["report"]["attempt_sha256"],
            "supervisor_sha256": item["completion"]["verification"]["report"]["supervisor_sha256"]}
            for item in manifest["attempts"] for row in item["completion"]["verification"]["report"]["history"][-1]["records"]
            if row["status"] != "NOT_ATTEMPTED"]
        return {"status": "OFFICIAL_RECONCILED_RESULTS", "rows": manifest["rows"], "history": state["history"], "lineage": lineage,
            "attempts": manifest["attempts"], "historical": manifest["historical"], "budget": {"reserved": state["reserved"],
                "caps": self.grant["caps"], "billing_gpu_seconds": "NOT_OBSERVED"},
            "certificate_sha256": digest(state["final"]), "scientific_selection": "PENDING", "scientific_qualified": False}


def validate_provider_report(manifest, report):
    require(report["schema"] == manifest.get("schema", SCHEMA) and report["status"] == "ALL_ORIGINALS_VERIFIED"
        and report["manifest_sha256"] == digest(manifest) and report["tools_sha256"] == digest(tools_manifest())
        and report["reserved"] == manifest["reserved"] and report["billing_gpu_seconds"] == "NOT_OBSERVED"
        and len(report["attempts"]) == len(manifest["attempts"])
        and report["historical_sha256"] == digest(manifest["historical"]), "MINICPM_FINAL_EVERY_ORIGINAL_REQUIRED")
    kernels = set()
    for item, proof in zip(manifest["attempts"], report["attempts"]):
        v, c = item["value"], item["completion"]
        owner = c["verification"]["owner_receipt"]
        provider = proof["provider"]
        require(proof["ticket_sha256"] == digest(item["ticket"]) and proof["completion_sha256"] == digest(c)
            and provider["job_id"] == v["job"] and provider["version"] == 1 and provider["state"] == "COMPLETE"
            and provider["kernel_id"] == owner["kernel_id"] and provider["kernel_id"] not in kernels
            and provider["notebook_code_sha256"] == item["ticket"]["payload"]["notebook_code_sha256"]
            and provider["safeshift_metadata"] == "MATCHED" and proof["capsule_verified"] is True
            and proof["output_verified"] is True and proof["local_replayed"] is True,
            "MINICPM_FINAL_JOB_VERSION_OUTPUT_OR_CAPSULE_MISMATCH")
        kernels.add(provider["kernel_id"])
    sixth = report["historical_verification"].get("serial6", {})
    require(sixth.get("job_id") == serial6.JOB and sixth.get("version") == 1
        and sixth.get("state") in ("COMPLETE", "ERROR") and type(sixth.get("kernel_id")) is int
        and sixth["kernel_id"] > 0 and sixth["kernel_id"] not in kernels
        and report["historical_verification"].get("serial6_supervisor_sha256") == serial6.ZIP_SHA,
        "MINICPM_FINAL_SERIAL6_PROVIDER_REQUIRED")
    require(report["historical_verification"]["status"] == "ALL_HISTORICAL_CUSTODY_RECHECKED"
        and report["historical_verification"]["historical_sha256"] == digest(manifest["historical"]),
        "MINICPM_FINAL_FAILED_AND_RETIRED_HOLDS_REQUIRED")
    if manifest.get("schema") == policy.TRANSITION_SCHEMA:
        seventh = report["historical_verification"].get("serial7_closure", {})
        require(seventh == manifest["historical"]["serial7_closure"]
            and seventh["provider"]["kernel_id"] not in kernels | {sixth["kernel_id"]},
            "MINICPM_FINAL_SERIAL7_PROVIDER_REQUIRED")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    template = sub.add_parser("release-template")
    template.add_argument("--v6-proposal", type=Path, required=True)
    template.add_argument("--output", type=Path, required=True)
    transition = sub.add_parser("serial8-release-template")
    for name in ("initial", "serial7-closure", "output"):
        transition.add_argument("--" + name, type=Path, required=True)
    spec = sub.add_parser("serial8-spec")
    spec.add_argument("--output", type=Path, required=True)
    init = sub.add_parser("init")
    for name in ("mirror", "locator", "exports", "initial", "closure"):
        init.add_argument("--"+name, type=Path, required=True)
    init.add_argument("--operator-session", required=True)
    init.add_argument("--serial7-closure", type=Path)
    stage = sub.add_parser("stage")
    for name in ("private-key", "owner-gate", "proof"):
        stage.add_argument("--"+name, type=Path, required=True)
    accept = sub.add_parser("accept")
    for name in ("attempt", "supervisor", "owner-receipt", "proof"):
        accept.add_argument("--"+name, type=Path, required=True)
    for name in ("status", "forecast", "export-active", "official-report"):
        sub.add_parser(name)
    manifest = sub.add_parser("manifest"); manifest.add_argument("--output", type=Path, required=True)
    final = sub.add_parser("reconcile")
    for name in ("report", "exports", "owner-locator"):
        final.add_argument("--"+name, type=Path, required=True)
    args = p.parse_args(argv)
    if args.command == "release-template":
        proposal = read(args.v6_proposal)
        require(proposal["schema"] == a.RECOVERY_SCHEMA and proposal["repair"]["schema"] == v5.SCHEMA
            and "offline" not in proposal, "MINICPM_V6_UNSIGNED_PROPOSAL_REQUIRED")
        proposal.update(implementation_pr=None, reviewed_head=None, merged_sha=None,
            issued_unix=None, expires_unix=None,
            approvals={k: None for k in ("source_review", "independent_audit", "merge", "postmerge")})
        proposal["offline"] = {"schema": SCHEMA, "decision_issue": 202, "operator_session": policy.ORIGINAL_SESSION,
            "base_journal_head_sha256": proposal["repair"]["journal_head_sha256"], "tools_sha256": digest(tools_manifest()),
            "tool_blobs": tool_blobs(), "unmeasured_calls": 100,
            "serial6_event_sha256": serial6.EVENT_SHA, "serial6_supervisor_sha256": serial6.ZIP_SHA}
        write(private(args.output), proposal)
        result = {"status": "UNSIGNED_PROPOSAL_BLOCKED_NOT_AUTHORITY", "marker_required": policy.RELEASE}
    elif args.command == "serial8-spec":
        _, active, _ = serial7.verify_local(ROOT / "data/processed")
        value = active["value"]
        r = value["request"]
        plan = r["plan"]
        name = r["plan"]["run_id"].removesuffix("-7") + "-8"
        initial = ui.initial(value["cohort"], r["projection_sha256"], r["resource_policy"],
            checkpoint_marker_sha256=r["checkpoint_marker_sha256"], run_id=name, attempt_id=name + "-attempt",
            job=value["job"].removesuffix("-7") + "-8", capsule_ref=value["capsule_ref"].removesuffix("-7/1") + "-8/1",
            max_calls=plan["max_calls"], max_seconds=plan["max_seconds"], nested_mounts=True,
            series=r["campaign"]["series"])
        write(private(args.output), initial)
        result = {"status": "UNSIGNED_SPEC_BLOCKED_NOT_AUTHORITY", "next_ordinal": 0}
    elif args.command == "serial8-release-template":
        processed = ROOT / "data/processed"
        report, active, _ = serial7.verify_local(processed)
        provider_closure = read(args.serial7_closure)
        serial7.verify_closure(provider_closure, report, active)
        initial = read(args.initial)
        ui.validate(initial)
        require(initial["cohort"] == active["value"]["cohort"], "MINICPM_SERIAL8_EXACT_TRAIN_COHORT")
        registration = read(processed / serial7.PRIMARY / "registration.json")
        proposal = serial7.old_release(registration["exports"]["/issues/comments/" + str(serial7.RELEASE["comment_id"])])
        proposal.update(implementation_pr=None, reviewed_head=None, merged_sha=None, runtime_commit=None,
            issued_unix=None, expires_unix=None, scope=a.scope(initial),
            approvals={**{k: None for k in proposal["approvals"]}, a.PROOF_KEY: "0" * 64})
        proposal["offline"].update(schema=policy.TRANSITION_SCHEMA, tools_sha256=digest(tools_manifest()),
            tool_blobs=tool_blobs(), serial7={"event_sha256": serial7.EVENT_SHA,
            "provider_closure_sha256": digest(provider_closure)})
        write(private(args.output), proposal)
        result = {"status": "UNSIGNED_PROPOSAL_BLOCKED_NOT_AUTHORITY", "marker_required": policy.TRANSITION_RELEASE}
    elif args.command == "init":
        Continuation.initialize(args.directory, args.mirror, read(args.locator), read(args.exports),
            read(args.initial), args.closure, args.operator_session,
            serial7_closure=read(args.serial7_closure) if args.serial7_closure else None)
        result = {"status": "OFFLINE_REGISTERED_NOT_RUN"}
    else:
        route = Continuation(args.directory)
        if args.command == "stage": result = route.stage(args.private_key, read(args.owner_gate), args.proof)
        elif args.command == "accept": result = route.accept(args.attempt, args.supervisor, read(args.owner_receipt), args.proof)
        elif args.command == "export-active":
            with lock(route.root): result = route.export_active()
        elif args.command == "manifest":
            result = route.manifest(); write(private(args.output), result)
        elif args.command == "reconcile": result = route.reconcile(read(args.report), read(args.exports), read(args.owner_locator))
        elif args.command == "official-report": result = route.official_report()
        elif args.command == "forecast": result = route.forecast()
        else:
            state = route.state()
            result = {k: state[k] for k in ("status", "counts", "reserved", "next_ordinal", "stopped")}
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
