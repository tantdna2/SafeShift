"""Owner UI restart in PR199 and the SAME historical Operator journal.

CPU preparation and read-only observations never issue a production release.
Only after review/audit/merge/postmerge may Antigravity bind, stage and publish.
There is no notebook/API submit, live observer, account switch or cancellation.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
from datetime import datetime, timezone, timedelta

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.pilot.artifacts import read, write, safe, sha
from safeshift.pilot.contract import digest
from safeshift.kaggle_handoff import lock, private_root
from safeshift.fulltrain import contract, minicpm_release as a, minicpm_recovery as recovery, minicpm_ui as ui
from scripts import minicpm_fulltrain_operator as old

KNOWN = (("minicpm-v2-journal", "minicpm-v2-mirror"),
         ("minicpm-v2-2-journal", "minicpm-v2-2-mirror"), ("minicpm-v3-journal", "minicpm-v3-mirror"))
EXTENSIONS = {"RESTART_BOUND", "PENDING_RESERVED", "PENDING_PUBLISH_INTENT", "PENDING_PUBLISHED",
              "RESTART_COLLECTED", "PENDING_PACKAGE_RECOVERED", "REPAIR_BOUND"}


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


LOCAL_EVIDENCE = (
    (("data/processed/inspect_run_1/safeshift-minicpm-mcpm4-train3763-1.log", "LOCAL_LOG"),
     ("data/processed/inspect_run_1/minicpm-fulltrain/supervision/abcd3b0663fa4742a10c2f0016a517ba.zip", "LOCAL_SEALED_SUPERVISOR"),
     ("data/processed/inspect_run_1/minicpm-fulltrain/supervision/abcd3b0663fa4742a10c2f0016a517ba.zip.sha256.json", "LOCAL_SIDECAR")),
    (("data/processed/inspect_run_v2_1/safeshift-minicpm-mcpm4-train3763-v2-1.log", "LOCAL_LOG"),),
    (("data/processed/minicpm-v3-package-1/dataset/safeshift_minicpm_release_ticket.json", "LOCAL_TICKET"),))


def retirement_snapshot(directive):
    """Derived local report only. No old journal, ticket or remote status changes."""
    recovery.locator(directive)
    require(directive["comment_id"] == recovery.DIRECTIVE, "MINICPM_OWNER_RETIREMENT_DIRECTIVE")
    result = inspect_journals()
    result.pop("prior_jobs"); result.pop("budget_amendment")
    result.update(schema=recovery.SCHEMA, directive=directive, budget_policy=recovery.budget_policy(result["reserved"]))
    for row, evidence in zip(result["journals"], LOCAL_EVIDENCE):
        proofs = []
        for name, kind in evidence:
            path = safe(ROOT, name)
            require(snapshot_stat(path).st_size <= 64 * 2**20, "MINICPM_RETIRED_EVIDENCE_BOUND")
            if kind == "LOCAL_SEALED_SUPERVISOR":
                ui.pair(path)
            proofs.append({"path": name, "sha256": sha(path), "kind": kind})
        row.update(disposition="RETIRED_NO_USABLE_RESULTS", historical_status="PROVIDER_UNAVAILABLE_NOT_VERIFIED_DELETED",
            native_calls_evidence="OWNER_REPORTED_LOCAL_LOGS_NOT_PROVIDER_VERIFIED", evidence=proofs,
            evidence_sha256=digest(proofs))
    return result


def verify_retired(snapshot):
    baseline = inspect_journals()
    require(snapshot["reserved"] == baseline["reserved"] == recovery.HISTORICAL, "MINICPM_RETIRED_COUNTER_DRIFT")
    for original, retired in zip(baseline["journals"], snapshot["journals"]):
        require(original == {k: ("UNVERIFIED" if k == "disposition" else None if k == "evidence_sha256" else retired[k])
            for k in original}, "MINICPM_RETIRED_JOURNAL_HEAD_DRIFT")
        for proof in retired["evidence"]:
            path = safe(ROOT, proof["path"])
            require(snapshot_stat(path).st_size <= 64 * 2**20 and sha(path) == proof["sha256"], "MINICPM_RETIRED_EVIDENCE_DRIFT")
            if proof["kind"] == "LOCAL_SEALED_SUPERVISOR":
                ui.pair(path)
    return baseline


def restart_spec(initial, *, source_repair=False):
    require(not initial["ancestors"] and not initial["request"]["history"], "MINICPM_RESTART_NO_OLD_PREDICTIONS")
    prefix = "nguynanhtn/safeshift-minicpm-" + recovery.CAMPAIGN
    serial = "5" if source_repair else "4"
    return ui.initial(initial["cohort"], initial["request"]["projection_sha256"], initial["request"]["resource_policy"],
        checkpoint_marker_sha256=initial["request"]["checkpoint_marker_sha256"], run_id=recovery.CAMPAIGN + "-run-" + serial,
        attempt_id=recovery.CAMPAIGN + "-attempt-" + serial, job=prefix + "-" + serial,
        capsule_ref="nguynanhtn/safeshift-minicpm-capsule-" + recovery.CAMPAIGN + "-" + serial + "/1",
        max_calls=recovery.COUNT, max_seconds=recovery.JOB_SECONDS, nested_mounts=True,
        series={**contract.SERIES, "minicpm4": recovery.SERIES})


def current_safety(client, snapshot, known_jobs, target):
    """Retired unavailable jobs are not fabricated terminal predecessors.

    Owned inventory catches renamed/new-route conflicts. Current quota's reserved
    time detects active accelerator sessions, including interactive/unlisted VMs.
    Visible old jobs are checked for QUEUED/RUNNING independently of retirement.
    """
    from scripts.submit_internvl_v2 import bounded_http
    owned = account_jobs(client)
    prefix = "nguynanhtn/safeshift-minicpm-" + recovery.CAMPAIGN + "-"
    require(target not in owned and {ref for ref in owned if ref.startswith(prefix)} == set(known_jobs),
            "MINICPM_RESTART_DUPLICATE_OR_UNKNOWN_JOB")
    observed = []
    with bounded_http():
        for row in snapshot["journals"]:
            if row["job"] not in owned:
                observed.append({"job": row["job"], "visibility": "NOT_VISIBLE_NOW_NOT_VERIFIED_DELETED"})
                continue
            state = str(client.kernels_status(row["job"]).status).split(".")[-1]
            require(state in ("COMPLETE", "ERROR", "CANCELLED"), "MINICPM_VISIBLE_RETIRED_JOB_ACTIVE_OR_UNKNOWN")
            observed.append({"job": row["job"], "visibility": "VISIBLE", "current_state": state})
        q = client.quota_view().gpu_quota
        quota = {k: int(getattr(q, f).total_seconds()) for k, f in
            (("used", "time_used"), ("reserved", "time_reserved"), ("total", "total_time_allowed"))}
    require(0 <= quota["used"] <= quota["total"] and quota["reserved"] == 0,
            "MINICPM_CURRENT_QUOTA_OR_ACTIVE_SESSION_STOP")
    return {"retired_visibility": observed, "quota": quota, "owned_sha256": digest(sorted(owned)),
            "observed_unix": int(time.time()), "historical_provider_custody": "NOT_AUTHENTICATED_BY_RETIREMENT"}


class RecoveredSerialJournal(old.Journal):
    """Signed Owner UI only, same physical journal; no submit/monitor API route."""
    def __init__(self):
        super().__init__(ROOT / "data/processed/minicpm-v3-journal", ROOT / "data/processed/minicpm-v3-mirror")

    def append(self, kind, payload):
        mapping = {"RESERVED": "PENDING_RESERVED", "PUBLISH_INTENT": "PENDING_PUBLISH_INTENT",
            "PUBLISHED": "PENDING_PUBLISHED", "COLLECTED": "RESTART_COLLECTED", "PACKAGE_RECOVERED": "PENDING_PACKAGE_RECOVERED"}
        super().append(mapping.get(kind, kind), payload)

    def bound(self, events):
        repaired = [e["payload"] for e in events if e["kind"] == "REPAIR_BOUND"]
        require(len(repaired) <= 1, "MINICPM_NO_REPLAYED_SOURCE_REPAIR")
        if repaired:
            return repaired[0]
        found = [e["payload"] for e in events if e["kind"] == "RESTART_BOUND"]
        require(len(found) == 1, "MINICPM_ONE_SOURCE_BOUND_OWNER_RESTART")
        return found[0]

    def guard_path(self, grant):
        if "repair" in grant:
            return safe(ROOT, "data/processed/minicpm-release-registrations/" + grant["campaign_id"] + "-source-repair-v1.json")
        return super().guard_path(grant)

    def rebind_release(self, locator, value, closure_directory):
        """After fresh review/audit/merge: append one source-bound closure.

        The old active reservation remains immutable history and fully charged.
        It is never COLLECTED and cannot supply an ancestor or prediction.
        """
        from scripts.minicpm_v44_incident import prefix, verify_evidence
        from safeshift.fulltrain import minicpm_incident as incident
        with lock(self.root):
            events = self.events()
            prior = prefix(events)
            grant = a.load(locator)
            require("repair" in grant and grant["operator_host_sha256"] == old.host(), "MINICPM_FRESH_SOURCE_REPAIR_REQUIRED")
            old.clean_source(grant)
            verify_retired(grant["recovery"])
            a.bind(grant, value)
            recovery.mounted_inputs(value)
            report = verify_evidence(closure_directory, prior, online=True)
            require(digest(report) == grant["repair"]["closure_sha256"]
                and digest(events[-1]) == grant["repair"]["journal_head_sha256"]
                and prior["locator"] == grant["repair"]["previous_release"]
                and prior["ticket"] == grant["repair"]["previous_ticket"], "MINICPM_REPAIR_CLOSURE_HEAD_PIN")
            p = value["request"]["plan"]
            require(not value["request"]["history"] and not value["ancestors"] and p["action"] == "initial"
                and p["counts"] == {"NOT_ATTEMPTED": recovery.COUNT} and p["scheduled_ordinals"][0] == 0,
                "MINICPM_REPAIR_EMPTY_HISTORY_ORDINAL_ZERO")
            write(self.guard_path(grant), self.binding(grant))
            a.sync_directory(self.guard_path(grant).parent)
            self.append("REPAIR_BOUND", {"locator": locator, "grant_sha256": digest(grant), "initial": value,
                "retirement_sha256": digest(grant["recovery"]), "historical_reservations": incident.initial_reserved(grant),
                "closure_directory": Path(closure_directory).relative_to(ROOT).as_posix(), "closure_sha256": digest(report)})
            return {"status": "SOURCE_REBOUND_FAILED_PRE_NATIVE_NO_REFUND", "next_serial": 5}

    def bind_release(self, locator, value):
        with lock(self.root):
            require(not any(e["kind"] in EXTENSIONS for e in self.events()), "MINICPM_RESTART_NO_SECOND_BINDING")
            grant = a.load(locator)
            require(grant["schema"] == a.RECOVERY_SCHEMA and grant["operator_host_sha256"] == old.host(), "MINICPM_OWNER_UI_RELEASE_REQUIRED")
            old.clean_source(grant)
            verify_retired(grant["recovery"])
            a.bind(grant, value)
            recovery.mounted_inputs(value)
            p = value["request"]["plan"]
            require(not value["request"]["history"] and not value["ancestors"] and p["action"] == "initial"
                and p["counts"] == {"NOT_ATTEMPTED": recovery.COUNT}
                and p["scheduled_ordinals"][0] == 0, "MINICPM_OWNER_RESTART_FROM_ORDINAL_ZERO")
            guard = self.guard_path(grant)
            # Keep all three original registrations. This create-only guard is
            # one source-bound restart, not a reusable budget initializer.
            write(guard, self.binding(grant))
            a.sync_directory(guard.parent)
            self.append("RESTART_BOUND", {"locator": locator, "grant_sha256": digest(grant), "initial": value,
                "retirement_sha256": digest(grant["recovery"]), "historical_reservations": grant["recovery"]["reserved"]})
            return {"status": "BOUND_NOT_PUBLISHED_NOT_RUN", "grant_sha256": digest(grant)}

    def stage_initial(self, events):
        return self.bound(events)["initial"]

    def release_locator(self, events):
        return self.bound(events)["locator"]

    def state(self):
        events = self.events()
        binding = self.bound(events)
        grant = a.load(binding["locator"], collection=True)
        require(grant["schema"] == a.RECOVERY_SCHEMA and grant["operator_host_sha256"] == old.host()
            and binding["grant_sha256"] == digest(grant) and binding["retirement_sha256"] == digest(grant["recovery"])
            and read(self.guard_path(grant)) == self.binding(grant), "MINICPM_RESTART_BOUND_GRANT_DRIFT")
        verify_retired(grant["recovery"])
        from safeshift.fulltrain.minicpm_incident import initial_reserved
        if "repair" in grant:
            from scripts.minicpm_v44_incident import prefix, verify_evidence
            index = next(i for i, e in enumerate(events) if e["kind"] == "REPAIR_BOUND")
            prior = prefix(events[:index])
            require(digest(events[index - 1]) == grant["repair"]["journal_head_sha256"]
                and digest(verify_evidence(safe(ROOT, binding["closure_directory"]), prior))
                    == binding["closure_sha256"] == grant["repair"]["closure_sha256"], "MINICPM_REPAIR_CUSTODY_DRIFT")
        reserved, active, completed, begun = initial_reserved(grant), None, [], False
        for event in events:
            kind, payload = event["kind"], event["payload"]
            if kind == ("REPAIR_BOUND" if "repair" in grant else "RESTART_BOUND"):
                begun = True
                continue
            if not begun:
                continue
            require(kind in EXTENSIONS, "MINICPM_RESTART_UNKNOWN_EVENT_STOP")
            if kind == "PENDING_RESERVED":
                require(active is None and payload["ticket"]["payload"]["reserved_before"] == reserved
                    and payload["ticket"]["payload"]["previous_event_sha256"] == event["previous"], "MINICPM_OWNER_SERIAL_RESERVATION")
                a.verify_ticket(grant, payload["ticket"], payload["value"], collection=True)
                require(len(payload["value"]["ancestors"]) == len(completed), "MINICPM_NO_SKIPPED_NEW_HISTORY")
                active = deepcopy(payload)
                reserved = payload["ticket"]["payload"]["reserved_after"]
                continue
            require(active is not None and payload["ticket_sha256"] == digest(active["ticket"]), "MINICPM_OWNER_EVENT_ACTIVE_TICKET")
            if kind == "PENDING_PUBLISH_INTENT":
                require("publish_intent" not in active, "MINICPM_OWNER_NO_DUPLICATE_UPLOAD")
                active["publish_intent"] = payload
            elif kind == "PENDING_PUBLISHED":
                require("publish_intent" in active and "published" not in active, "MINICPM_OWNER_PUBLICATION_SEQUENCE")
                active["published"] = payload
            elif kind == "PENDING_PACKAGE_RECOVERED":
                require("publish_intent" not in active, "MINICPM_OWNER_RECOVER_BEFORE_UPLOAD_ONLY")
                active["package"] = payload["package"]
            elif kind == "RESTART_COLLECTED":
                require("published" in active, "MINICPM_OWNER_COLLECT_ONLY_PUBLISHED")
                active["collection"] = payload
                completed.append(active); active = None
            else:
                raise ValueError("MINICPM_OWNER_EVENT_SEQUENCE")
        return grant, events, reserved, active, completed

    def observe_provider(self, client, grant, value, prior):
        verify_retired(grant["recovery"])
        technical = []
        if "repair" in grant:
            from scripts.minicpm_v44_incident import prefix, verify_evidence
            events = self.events()
            index = next(i for i, e in enumerate(events) if e["kind"] == "REPAIR_BOUND")
            previous = prefix(events[:index])
            directory = safe(ROOT, self.bound(events)["closure_directory"])
            report = verify_evidence(directory, previous, online=True, client=client)
            require(digest(report) == grant["repair"]["closure_sha256"], "MINICPM_REPAIR_PROVIDER_CUSTODY_CHANGED")
            technical = [{"job": previous["value"]["job"], "notebook": read(directory / "notebook.ipynb"),
                "input_sources": previous["value"]["input_sources"], "kernel_id": report["provider"]["kernel_id"],
                "state": report["provider"]["state"]}]
        safety = current_safety(client, grant["recovery"], [p["job"] for p in technical + prior], value["job"])
        # Exact new-series predecessor code/Input/terminal checks and Input/quota
        # use PR198's verifier; historical retired records are not passed to it.
        result = old.provider(client, grant, value, technical + prior)
        if technical:
            result["technical_predecessor"] = result["prior_jobs"].pop(0)
        require(safety["owned_sha256"] == result["owned_sha256"], "MINICPM_ACCOUNT_CHANGED_DURING_RELEASE")
        result["current_account_safety"] = safety
        _, _, _, _, completed = self.state()
        require(len(completed) == len(prior), "MINICPM_NEW_RUN_PROVIDER_LINEAGE")
        for row, item in zip(result["prior_jobs"], completed):
            row["ticket"] = item["ticket"]
        return result

    def validate_package(self, grant, active):
        from safeshift.fulltrain.minicpm_execution import MARKER
        destination = safe(ROOT, active["package"])
        value = active["value"]
        expected = old.notebook(grant["runtime_commit"], capsule_sha256=digest(value),
            release_locator=self.release_locator(self.events()), release_version=5 if "repair" in grant else 4)
        require(read(destination / "notebook.ipynb") == expected, "MINICPM_OWNER_EXACT_SOURCE_NOTEBOOK")
        require(ui.verify_capsule(destination / "dataset", digest(value), release_ticket=True) == value
            and read(destination / "dataset" / MARKER) == active["ticket"], "MINICPM_OWNER_EXACT_CAPSULE_TICKET")

    def handoff_details(self, handoff, grant, value, ticket, destination):
        local = datetime.fromtimestamp(ticket["payload"]["start_before_unix"], timezone(timedelta(hours=7)))
        return {**handoff, "mode": "OWNER_UI_ONLY", "runtime_commit": grant["runtime_commit"],
            "notebook_release_version": 5 if "repair" in grant else 4,
            "source_transition": grant.get("repair", {}).get("schema"),
            "retained_before_new_source": grant.get("repair", {}).get("reserved_after"),
            "source_sha256": grant["scope"]["source_sha256"], "merged_sha": grant["merged_sha"],
            "release_locator": self.release_locator(self.events()), "input_mounts": recovery.mounted_inputs(value),
            "notebook_file": (destination / "notebook.ipynb").relative_to(ROOT).as_posix(),
            "start_before_local": local.isoformat(), "timezone": "Asia/Ho_Chi_Minh",
            "historical_reservations": grant["recovery"]["reserved"], "cumulative_reservations": ticket["payload"]["reserved_after"],
            "historical_provider_status": "UNVERIFIED_RETIRED_NO_USABLE_RESULTS", "scientific_inheritance": False,
            "owner_steps": ["Upload this exact notebook using job slug " + value["job"] + "; attach the five pinned Inputs.",
                "Select Private / Python / Internet On / GPU T4x2.",
                "Save Version > Save & Run All ONCE before start_before; send the version URL to Antigravity."]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("inspect")
    retire = sub.add_parser("retire")
    retire.add_argument("--directive-locator", type=Path, required=True); retire.add_argument("--output", type=Path, required=True)
    spec = sub.add_parser("prepare-spec")
    spec.add_argument("--initial-spec", type=Path, required=True); spec.add_argument("--output", type=Path, required=True)
    spec.add_argument("--source-repair", action="store_true")
    template = sub.add_parser("release-template")
    for name in ("spec", "snapshot", "output"):
        template.add_argument("--" + name, type=Path, required=True)
    template.add_argument("--runtime-ref", required=True)
    template.add_argument("--implementation-pr", type=int)
    template.add_argument("--repair-closure", type=Path)
    template.add_argument("--repair-directive", type=Path)
    binding = sub.add_parser("bind")
    binding.add_argument("--locator", type=Path, required=True); binding.add_argument("--spec", type=Path, required=True)
    rebinding = sub.add_parser("rebind-source")
    rebinding.add_argument("--locator", type=Path, required=True)
    rebinding.add_argument("--spec", type=Path, required=True)
    rebinding.add_argument("--closure", type=Path, required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--private-key", type=Path, required=True); stage.add_argument("--output", type=Path, required=True)
    pub = sub.add_parser("publish"); pub.add_argument("--verify-only", action="store_true")
    collect = sub.add_parser("collect"); collect.add_argument("--output", type=Path, required=True)
    recover = sub.add_parser("recover-package")
    recover.add_argument("--output", type=Path, required=True)
    sub.add_parser("status")
    args = p.parse_args()
    if args.action == "inspect":
        result = inspect_journals()
    elif args.action == "retire":
        result = retirement_snapshot(read(args.directive_locator))
        write(args.output, result)
    elif args.action == "prepare-spec":
        result = restart_spec(read(args.initial_spec), source_repair=args.source_repair)
        write(args.output, result)
    elif args.action == "release-template":
        value, snapshot = read(args.spec), read(args.snapshot)
        result = old.release_template(value, args.runtime_ref)
        result.update(schema=a.RECOVERY_SCHEMA, authorization="OWNER_MINICPM_TRAIN3763_RESTART_SERIAL_UI_ONLY",
            campaign_id=recovery.CAMPAIGN, implementation_pr=199, recovery=snapshot,
            caps=recovery.budget_policy(snapshot["reserved"])["caps"],
            approvals={kind: None for kind in recovery.SOURCE_ROLES})
        if args.repair_closure is not None:
            from scripts.minicpm_v44_incident import prefix, verify_evidence, repair_template
            require(args.implementation_pr is not None and args.implementation_pr > 199
                and args.repair_directive is not None, "MINICPM_REPAIR_NEW_PR_AND_DIRECTIVE_REQUIRED")
            prior = prefix(RecoveredSerialJournal().events())
            closure = verify_evidence(args.repair_closure, prior)
            result = repair_template(result, prior, closure, read(args.repair_directive))
            result["implementation_pr"] = args.implementation_pr
        else:
            require(args.implementation_pr is None and args.repair_directive is None,
                "MINICPM_REPAIR_CLOSURE_REQUIRED")
        write(args.output, result)
        print("UNSIGNED_PROPOSAL_NOT_AUTHORITY")
        return
    else:
        operator = RecoveredSerialJournal()
        if args.action == "bind":
            result = operator.bind_release(read(args.locator), read(args.spec))
        elif args.action == "rebind-source":
            result = operator.rebind_release(read(args.locator), read(args.spec), args.closure.absolute())
        elif args.action == "stage":
            result = {"package": str(operator.stage(args.private_key, args.output)), "status": "RESERVED_NOT_RELEASED"}
        elif args.action == "publish":
            result = operator.publish(verify_only=args.verify_only)
        elif args.action == "collect":
            result = operator.collect(args.output)
        elif args.action == "recover-package":
            result = {"package": str(operator.recover_package(args.output))}
        else:
            _, _, reserved, active, completed = operator.state()
            result = {"reserved": reserved, "open_reservation": active is not None, "verified_new_jobs": len(completed)}
    # Private metadata remains in local files, not printed with every operation.
    if args.action in ("inspect", "retire"):
        result = {"status": "LOCAL_REPORT_NOT_PROVIDER_AUTHORITY", "reserved": result["reserved"],
            "historical_status": "RETIRED_ONLY_BY_OWNER_DECISION_NOT_VERIFIED_DELETED"}
    elif args.action == "prepare-spec":
        result = {"status": "PREPARED_NOT_RELEASED", "first_ordinal": result["request"]["plan"]["scheduled_ordinals"][0]}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
