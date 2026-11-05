"""One bounded Owner grant, serial durable admission and explicit technical repair.

No provider imports on import, no implicit approval, no POST retry or refund.
The local single-writer threat model and recovery limits are in TRAIN3763_CAMPAIGN.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import inspect
import json
import os
import platform
from pathlib import Path
import re
import time

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import read, write, sha, safe
from safeshift.pilot.contract import digest, require_hash, MASTER_SHA

SCHEMA = "safeshift-train3763-campaign-v1"
SCOPE = "TRAIN3763_CAMPAIGN"
MARKER = "SAFESHIFT_TRAIN3763_CAMPAIGN_V1"
PLAN = "safeshift-train3763-campaign-plan-v1"
TERMINAL = ("COMPLETE", "ERROR", "CANCELLED")


def host_identity():
    import uuid
    return digest({"host": platform.node(), "node": uuid.getnode(), "platform": platform.system()})


def operator_binding(root):
    return digest({"host_sha256": host_identity(), "ledger_root": str(Path(root).resolve())})


def science():
    from safeshift import internvl3763 as runtime
    # Frozen inherited checkpoint/runtime/parser/prompt/grammar plus the actual
    # native generation, image preparation and raw-before-parse implementation.
    return {"inherited": runtime.capture.source_spec(), "configuration": runtime.configuration(),
        "native": {f.__name__: hashlib.sha256(inspect.getsource(f).encode()).hexdigest()
            for f in (runtime.generate_prepared, runtime.NativeBackend, runtime.trace_binding)}}


def identity():
    from safeshift import internvl3763 as runtime
    return {**runtime.identity(), "implementation_sha256": digest(science())}


def record(locator, marker, reader):
    from safeshift import internvl3763_release as old
    require(type(locator) is dict and set(locator) == {"comment_id", "body_sha256"}, "CAMPAIGN_LOCATOR")
    require(type(locator["comment_id"]) is int and locator["comment_id"] > 0, "CAMPAIGN_COMMENT_ID")
    require_hash(locator["body_sha256"])
    comment = reader("/issues/comments/" + str(locator["comment_id"]))
    require(comment["id"] == locator["comment_id"]
        and hashlib.sha256(comment["body"].encode()).hexdigest() == locator["body_sha256"], "COMMENT_HASH_ID_DRIFT")
    matches = re.findall(re.escape(marker) + r"\s*```json\s*(\{.*?\})\s*```", comment["body"], re.S)
    require(len(matches) == 1, "ONE_STRUCTURED_CAMPAIGN_RECORD")
    # Reuse duplicate-key/nonfinite rejection, without filesystem I/O.
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, "DUPLICATE_CAMPAIGN_KEY")
            result[k] = v
        return result
    return json.loads(matches[0], object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_CAMPAIGN"))), comment


def validate(grant, *, now=None, collection=False):
    from safeshift import internvl3763 as runtime
    from safeshift.candidates.fulltrain import token
    require(set(grant) == {"schema", "campaign_id", "authorization", "implementation_pr", "reviewed_head",
        "merged_sha", "science_sha256", "cohort_sha256", "input_marker_sha256", "inputs", "rights",
        "operator_id", "operator_root_sha256", "review_logins", "audit_logins", "issued_unix", "expires_unix", "caps", "policy"},
        "CAMPAIGN_EXACT_FIELDS")
    require(grant["schema"] == SCHEMA and grant["authorization"] == "GRANTED_FOR_BOUNDED_CAMPAIGN",
        "EXPLICIT_CAMPAIGN_AUTHORITY")
    token(grant["campaign_id"]); token(grant["operator_id"])
    require(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,19}", grant["campaign_id"]), "KAGGLE_SAFE_CAMPAIGN_ID")
    require(type(grant["implementation_pr"]) is int and grant["implementation_pr"] > 179, "NO_OLD_GRANT_MIGRATION")
    for key in ("reviewed_head", "merged_sha"):
        require(type(grant[key]) is str and re.fullmatch(r"[a-f0-9]{40}", grant[key]), "CAMPAIGN_COMMIT")
    for key in ("science_sha256", "cohort_sha256", "input_marker_sha256", "operator_root_sha256"):
        require_hash(grant[key])
    require(grant["science_sha256"] == digest(science()), "SCIENTIFIC_CHANGE_REQUIRES_NEW_DECISION")
    require(grant["input_marker_sha256"] == MASTER_SHA, "ORIGINAL_EXISTING_MASTER_REQUIRED")
    require(type(grant["issued_unix"]) is int and type(grant["expires_unix"]) is int
        and 0 < grant["expires_unix"] - grant["issued_unix"] <= 366 * 86400
        and (collection or grant["issued_unix"] <= (time.time() if now is None else now) < grant["expires_unix"]),
        "CAMPAIGN_WINDOW")
    for key in ("review_logins", "audit_logins"):
        require(type(grant[key]) is list and grant[key] and len(grant[key]) <= 16
            and all(type(x) is str and re.fullmatch(r"[A-Za-z0-9_\[\]-]{1,100}", x) for x in grant[key]),
            "EXPLICIT_REVIEW_AUDIT_IDENTITIES")
    require(type(grant["inputs"]) is dict and set(grant["inputs"]) == {"dataset_sources", "kernel_sources"}, "CAMPAIGN_INPUTS")
    for refs in grant["inputs"].values():
        require(type(refs) is list and len(refs) <= 16 and len(refs) == len(set(refs))
            and all(type(x) is str and re.fullmatch(r"[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-9][0-9]*", x) for x in refs),
            "VERSIONED_ORIGINAL_INPUTS")
    require(any(grant["inputs"].values()), "ORIGINAL_INPUTS_REQUIRED")
    require(type(grant["rights"]) is dict and set(grant["rights"]) == {"O2", "O3", "O4", "O5", "O6"}, "SEPARATE_RIGHTS_EVIDENCE")
    for value in grant["rights"].values():
        require(type(value) is dict and set(value) == {"status", "ref", "sha256"}
            and value["status"] in ("APPROVED", "NOT_REQUIRED_WITH_BASIS")
            and type(value["ref"]) is str and value["ref"].startswith("https://") and len(value["ref"]) <= 1000,
            "RIGHTS_PENDING_NO_EXECUTION")
        require_hash(value["sha256"])
    caps = grant["caps"]
    require(type(caps) is dict and set(caps) == {"total_calls", "total_jobs", "total_gpu_seconds", "job_calls",
        "job_seconds", "archive_bytes", "physical_gpus", "machine_shape", "max_repairs_per_image"}, "FINITE_CAMPAIGN_CAPS")
    require(all(type(v) is int and v > 0 for k, v in caps.items() if k != "machine_shape"), "POSITIVE_INTEGER_CAPS")
    require(caps["physical_gpus"] == 2 and caps["machine_shape"] == "NvidiaTeslaT4"
        and caps["job_calls"] <= 3763 and 120 <= caps["job_seconds"] <= 43200
        and caps["archive_bytes"] <= 7 * 2**30 and caps["total_jobs"] <= 10000
        and caps["max_repairs_per_image"] <= 100
        and caps["total_calls"] >= caps["job_calls"] and caps["total_gpu_seconds"] >= 240,
        "UNSUPPORTED_CAMPAIGN_CAPS")
    require(grant["policy"] == {"serial": True, "resume": "NOT_ATTEMPTED_ONLY", "repair": "DIAGNOSED_TECHNICAL_ONLY",
        "technical_fixes": "REVIEWED_MERGED_SCIENCE_UNCHANGED", "ambiguous": "STOP_READ_ONLY",
        "refund": False, "test": False, "scientific_selection": "PENDING", "pooling": False}, "CAMPAIGN_STOP_POLICY")
    return grant


def load(locator, *, reader=None, now=None, collection=False):
    from safeshift import internvl3763_release as old
    reader = old.get if reader is None else reader
    grant, comment = record(locator, MARKER, reader)
    validate(grant, now=now, collection=collection)
    require(comment["user"]["login"] == old.OWNER
        and comment["issue_url"] == old.API + "/issues/" + str(grant["implementation_pr"]), "AUTHENTIC_OWNER_CAMPAIGN")
    pr = reader("/pulls/" + str(grant["implementation_pr"]))
    require(pr["merged"] is True and pr["head"]["sha"] == grant["reviewed_head"]
        and pr["merge_commit_sha"] == grant["merged_sha"] and pr["base"]["ref"] == "main", "CAMPAIGN_MERGED_IMPLEMENTATION")
    return grant


def revision(grant, request, *, reader=None):
    """A reviewer attests technical qualification; this grants no new resources.

    Initial and later revisions use the same review path. The Owner need not
    issue another campaign grant. Reviewer identities come from that one grant.
    """
    from safeshift import internvl3763_release as old
    reader = old.get if reader is None else reader
    value, comment = record(request["bindings"]["runtime"]["technical_revision"],
        "SAFESHIFT_TRAIN3763_TECHNICAL_V1", reader)
    require(set(value) == {"campaign_sha256", "science_sha256", "implementation_pr", "reviewed_head", "merged_sha",
        "runtime_commit", "source_sha256", "notebook_sha256", "notebook_code_sha256", "regression_sha256", "audit"},
        "TECHNICAL_REVISION_FIELDS")
    require(comment["user"]["login"] in grant["review_logins"] and value["campaign_sha256"] == digest(grant)
        and value["science_sha256"] == grant["science_sha256"] == digest(science()), "TECHNICAL_REVIEW_SCOPE")
    require(type(value["implementation_pr"]) is int and value["implementation_pr"] >= grant["implementation_pr"]
        and comment["issue_url"] == old.API + "/issues/" + str(value["implementation_pr"]), "TECHNICAL_PR_REFERENCE")
    pr = reader("/pulls/" + str(value["implementation_pr"]))
    require(pr["merged"] is True and pr["base"]["ref"] == "main" and pr["head"]["sha"] == value["reviewed_head"]
        and pr["merge_commit_sha"] == value["merged_sha"] == request["commit_sha"], "REVIEWED_TECHNICAL_MERGE")
    require_hash(value["regression_sha256"])
    audit, auditor = record(value["audit"], "SAFESHIFT_TRAIN3763_AUDIT_V1", reader)
    require(auditor["user"]["login"] in grant["audit_logins"]
        and auditor["id"] != comment["id"] and auditor["issue_url"] == comment["issue_url"]
        and audit == {"campaign_sha256": digest(grant), "reviewed_head": value["reviewed_head"],
            "source_sha256": value["source_sha256"], "regression_sha256": value["regression_sha256"],
            "status": "PASS", "independent": True}, "INDEPENDENT_TECHNICAL_AUDIT")
    execution = request["bindings"]["runtime"]["execution_request"]
    require(value["runtime_commit"] == request["runtime_commit"] and value["source_sha256"] == digest(execution["source"])
        and value["notebook_sha256"] == request["notebook_sha256"], "TECHNICAL_SOURCE_BINDING")
    require_hash(value["notebook_code_sha256"])
    return value


def plan(cohort, history, *, action, run_id, attempt_id, max_calls, max_seconds, repair=None):
    from safeshift import internvl3763 as runtime
    from safeshift.candidates import fulltrain as planning
    require(action in ("initial", "resume", "repair"), "NO_CAMPAIGN_FULL_RERUN")
    value = planning.plan(cohort, digest(cohort), identity(), history, digest(history), action=action,
        series_id=runtime.SERIES, run_id=run_id, attempt_id=attempt_id,
        max_calls=max_calls, max_seconds=max_seconds, repair=repair)
    return {**value, "schema": PLAN, "science_sha256": digest(science()), "runtime_source": runtime.source_spec()}


def bind(grant, request, *, reader=None):
    from safeshift import internvl3763 as runtime
    from safeshift.kaggle_handoff import validate_request
    from safeshift.internvl3763_operator import input_sources
    validate_request(request)
    require(request["scope"] == SCOPE, "CAMPAIGN_ROUTE_REQUIRED")
    execution = request["bindings"]["runtime"]["execution_request"]
    p = runtime.validate_execution_request(execution)
    require(p["schema"] == PLAN and p["science_sha256"] == grant["science_sha256"]
        and digest(execution["cohort"]) == grant["cohort_sha256"]
        and execution["input_marker_sha256"] == grant["input_marker_sha256"], "CAMPAIGN_ORIGINAL_SCIENCE_COHORT")
    sources = input_sources(request)
    require(request["bindings"]["source"] == execution["source"]
        and request["bindings"]["rights"] == grant["rights"]
        and request["bindings"]["scientific_method"] == {"science_sha256": grant["science_sha256"]}, "CAMPAIGN_BINDING_EVIDENCE")
    for key in ("dataset_sources", "kernel_sources"):
        require(set(grant["inputs"][key]) <= set(sources[key]), "ORIGINAL_INPUT_REMOVED_OR_CHANGED")
        require(all(x in grant["inputs"][key] or x.startswith("nguynanhtn/") for x in sources[key]), "EXTRA_INPUT_OWNER")
    capsule = request["bindings"]["runtime"]["execution_input"]
    extras = [(key, ref) for key in ("dataset_sources", "kernel_sources") for ref in sources[key] if ref not in grant["inputs"][key]]
    require(type(capsule) is dict and set(capsule) == {"kind", "ref"} and capsule["kind"] == "dataset_sources"
        and extras == [(capsule["kind"], capsule["ref"])], "ONE_EXACT_PRIVATE_CAPSULE_INPUT")
    caps = grant["caps"]
    require(request["limits"]["max_calls"] == p["max_calls"] <= caps["job_calls"]
        and request["limits"]["job_seconds"] == p["max_seconds"] <= caps["job_seconds"]
        and p["max_seconds"] >= 120 and request["version"] == 1
        and re.fullmatch(r"nguynanhtn/safeshift-train3763-" + re.escape(grant["campaign_id"]) + r"-[1-9][0-9]*", request["job"]),
        "CAMPAIGN_JOB_CAPS_IDENTITY")
    reviewed = revision(grant, request, reader=reader)
    if p["action"] == "repair":
        require(p["repair"]["fix_sha256"] == reviewed["source_sha256"]
            and p["repair"]["regression_sha256"] == reviewed["regression_sha256"], "REPAIR_REVIEWED_FIX_REGRESSION")
    return execution


def admit_inputs(inputs, expected_master_sha, expected_projection):
    """Reuse #173's original mounts/locators; no copied 3763-image bundle.

    Only the hash-locked TRAIN master and its listed TRAIN JPGs are read. The
    existing verifier does not enumerate TEST, annotations or image sidecars.
    """
    from safeshift.candidates.train_inputs import discover, mounts
    from safeshift.candidates.source import snapshot_stat
    from safeshift.verification173 import verify_train
    master = discover(inputs, "master_manifest.json")
    require(snapshot_stat(master).st_size <= 16*2**20
        and sha(master) == expected_master_sha == MASTER_SHA, "ORIGINAL_EXISTING_MASTER_REQUIRED")
    original = [path for path in mounts(inputs) if path.name == "inspecsafe-v1-kaggle"]
    require(len(original) == 1, "UNIQUE_ORIGINAL_DATASET_MOUNT")
    image_root = safe(original[0], "InspecSafe-V1-Kaggle/train/DATA_PATH")
    require(image_root.is_dir(), "ORIGINAL_TRAIN_LAYOUT_REQUIRED")
    checked, cohort, mapping = verify_train(master, image_root)
    require(digest(cohort) == expected_projection and checked["verified_images"] == 3763
        and checked["status"] == "TRAIN_BYTES_PASS", "ORIGINAL_3763_INPUT_CUSTODY")
    rows = [{"ordinal": row["ordinal"], "sample_id": row["sample_id"], "image_sha256": row["image_sha256"],
        "image": row["image_locator"].removeprefix("DATA_PATH/")} for row in mapping]
    require(len(rows) == 3763 and all(row["image"].startswith("train/Annotations/") for row in rows), "TRAIN_LOCATORS_ONLY")
    return image_root, cohort, rows, {**checked, "input_copy_bytes": 0, "download_bytes": 0,
        "layout": "EXISTING_ISSUE173_ORIGINAL_MOUNTS", "labels_exported": False}


def _sync_directory(path):
    if os.name != "nt":
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


class Ledger:
    """Mirrored create-only journal. Loss/divergence is BLOCKED, never auto-init."""
    def __init__(self, root):
        self.root = Path(root)
        self.registration = read(self.root / "registration.json")
        require(self.registration["host_sha256"] == host_identity(), "CROSS_MACHINE_TAKEOVER_BLOCKED_READ_ONLY_RECOVERY")
        self.mirror = Path(self.registration["mirror"])
        require(self.mirror.resolve() != self.root.resolve() and not self.mirror.resolve().is_relative_to(self.root.resolve())
            and not self.root.resolve().is_relative_to(self.mirror.resolve()), "INDEPENDENT_CUSTODY_DIRECTORY")
        require(read(self.mirror / "registration.json") == self.registration, "LEDGER_REGISTRATION_LOST_OR_ROLLED_BACK")
        self.grant = self.registration["grant"]
        require(self.grant["operator_root_sha256"] == operator_binding(self.root), "CAMPAIGN_CANONICAL_OPERATOR_ROOT")
        guard = self.root.parent / (".train3763-"+self.grant["campaign_id"]+".initialized.json")
        require(read(guard) == self.registration, "CAMPAIGN_INITIALIZATION_GUARD_LOST")
        self.events()

    @classmethod
    def create(cls, root, mirror, grant, operator_id):
        validate(grant)
        require(operator_id == grant["operator_id"], "OPERATOR_MACHINE_SCOPE")
        root, mirror = Path(root), Path(mirror)
        require(grant["operator_root_sha256"] == operator_binding(root), "CAMPAIGN_CANONICAL_OPERATOR_ROOT")
        require(root.resolve() != mirror.resolve() and not root.resolve().is_relative_to(mirror.resolve())
            and not mirror.resolve().is_relative_to(root.resolve()), "INDEPENDENT_CUSTODY_DIRECTORY")
        value = {"schema": SCHEMA, "grant": grant, "operator_id": operator_id,
            "mirror": str(mirror.resolve()), "root": str(root.resolve()), "host_sha256": host_identity()}
        require(not root.exists() and not mirror.exists(), "CAMPAIGN_DIRECTORY_EXISTS_NO_REINITIALIZATION")
        root.parent.mkdir(parents=True, exist_ok=True)
        write(root.parent / (".train3763-"+grant["campaign_id"]+".initialized.json"), value)
        _sync_directory(root.parent)
        root.mkdir(parents=True, exist_ok=False); mirror.mkdir(parents=True, exist_ok=False)
        for destination in (root, mirror):
            write(destination / "registration.json", value)
            _sync_directory(destination)
        return cls(root)

    def events(self):
        names = sorted(p.name for p in self.root.glob("journal-*.json"))
        require(names == sorted(p.name for p in self.mirror.glob("journal-*.json")), "LEDGER_PARTIAL_ROLLBACK_OR_LOSS")
        result, previous = [], None
        for number, name in enumerate(names, 1):
            require(name == f"journal-{number:06d}.json", "LEDGER_GAP")
            path = self.root / name
            require(path.read_bytes() == (self.mirror / name).read_bytes(), "LEDGER_DIVERGENCE")
            event = read(path)
            require(event["previous"] == previous and event["campaign_sha256"] == digest(self.grant), "LEDGER_CHAIN")
            result.append(event); previous = digest(event)
        return result

    def append(self, kind, **values):
        # Caller holds the campaign-wide OS lock, including all external writes.
        events = self.events()
        value = {"campaign_sha256": digest(self.grant), "previous": digest(events[-1]) if events else None,
            "kind": kind, "unix": time.time(), **values}
        for destination in (self.root, self.mirror):
            write(destination / f"journal-{len(events)+1:06d}.json", value)
            _sync_directory(destination)
        return value

    def intents(self):
        return [x for x in self.events() if x["kind"] == "INTENT"]

    def open_intent(self):
        events = self.events()
        closed = {x["intent_sha256"] for x in events if x["kind"] in ("COLLECTED", "ABORTED_PRE_SUBMIT")}
        pending = [x for x in events if x["kind"] == "INTENT" and digest(x) not in closed]
        require(len(pending) <= 1, "MULTIPLE_ACTIVE_INTENTS")
        return pending[0] if pending else None

    def histories(self):
        from safeshift import internvl3763 as runtime
        result, custody = [], []
        for row in self.events():
            if row["kind"] == "COLLECTED":
                path = Path(row["archive"])
                require(sha(path) == row["sha256"], "ARCHIVE_CUSTODY_LOST")
                ancestor = runtime.sealed_history(path, row["sha256"], row["plan"])
                require(ancestor == row["history"] and ancestor["parent_history_sha256"] == digest(result), "COLLECTED_LINEAGE_DRIFT")
                result.append(ancestor)
                custody.append({"path": str(path), "sha256": row["sha256"], "plan": row["plan"]})
        return result, custody

    def reserve(self, request):
        from safeshift.kaggle_handoff import lock
        with lock(self.root):
            validate(self.grant)
            require(self.open_intent() is None, "AMBIGUOUS_OR_ACTIVE_INTENT_READ_ONLY")
            execution = bind(self.grant, request)
            history, _ = self.histories()
            require(execution["history"] == history, "COMPLETE_LEDGER_HISTORY_REQUIRED")
            intents, caps = self.intents(), self.grant["caps"]
            require(request["job"].endswith("-" + str(len(intents)+1)), "MONOTONIC_ATTEMPT_JOB")
            require(request["handoff_id"] == execution["plan"]["run_id"] == self.grant["campaign_id"]+"-"+str(len(intents)+1)
                and execution["plan"]["attempt_id"] == "attempt-"+str(len(intents)+1), "MONOTONIC_RUN_ATTEMPT_ID")
            require(not any(x["request"]["handoff_id"] == request["handoff_id"] for x in intents), "DUPLICATE_HANDOFF")
            capsule = request["bindings"]["runtime"]["execution_input"]["ref"]
            require(not any(x["request"]["bindings"]["runtime"]["execution_input"]["ref"].rsplit("/", 1)[0]
                == capsule.rsplit("/", 1)[0] for x in intents), "NEW_ATTEMPT_REQUIRES_NEW_CAPSULE")
            calls, seconds = execution["plan"]["max_calls"], execution["plan"]["max_seconds"]
            require(len(intents) < caps["total_jobs"] and sum(x["reserved_calls"] for x in intents)+calls <= caps["total_calls"]
                and sum(x["reserved_gpu_seconds"] for x in intents)+seconds*caps["physical_gpus"] <= caps["total_gpu_seconds"],
                "CAMPAIGN_BUDGET_EXHAUSTED_NO_REFUND")
            require(time.time()+seconds+120 < self.grant["expires_unix"], "FULL_CAMPAIGN_JOB_WINDOW")
            if not intents:
                require(execution["plan"]["scheduled_ordinals"] == [0] and calls == 1, "FIRST_FINAL_SOURCE_ORDINAL0_ONE_CALL")
            else:
                qualified = [x for x in self.events() if x["kind"] == "MEASURED" and x["source_sha256"] == digest(execution["source"])]
                require(qualified or calls == 1, "FINAL_SOURCE_MEASUREMENTS_REQUIRED_BEFORE_SHARDS")
                if qualified:
                    require(calls <= qualified[-1]["safe_calls"] and seconds >= qualified[-1]["minimum_seconds"], "MEASURED_SHARD_LIMIT")
            repair = execution["plan"].get("repair")
            if repair:
                for sample in repair["targets"]:
                    count = sum(sample in (x["request"]["plan"].get("repair") or {}).get("targets", {}) for x in intents)
                    require(count < caps["max_repairs_per_image"], "IMAGE_REPAIR_CAP")
            return self.append("INTENT", request=request, reserved_calls=calls, reserved_gpu_seconds=seconds*caps["physical_gpus"])

    def abort_pre_submit(self):
        from safeshift.kaggle_handoff import lock
        with lock(self.root):
            intent = self.open_intent()
            require(intent is not None and not any(x["kind"] == "PUSH_INTENT" and x["intent_sha256"] == digest(intent)
                for x in self.events()), "POSSIBLE_SUBMIT_READ_ONLY_RECONCILIATION_ONLY")
            from safeshift.internvl3763_operator import pre_submit_inventory
            proof = pre_submit_inventory(self, intent)
            require(proof["job_absent"] is True and proof["job"] == intent["request"]["job"]
                and proof["intent_sha256"] == digest(intent), "EXACT_PROVIDER_ABSENCE_REQUIRED")
            return self.append("ABORTED_PRE_SUBMIT", intent_sha256=digest(intent), refund=False, provider=proof)

    def submitted(self, intent, result):
        from safeshift.kaggle_handoff import lock
        with lock(self.root):
            require(self.open_intent() == intent and result == {"job_id": intent["request"]["job"], "version": 1}, "SUBMIT_EXACT_IDENTITY")
            return self.append("SUBMITTED", intent_sha256=digest(intent), result=result)

    def collect(self, request, archive, provider):
        from safeshift import internvl3763 as runtime
        from safeshift.kaggle_handoff import lock
        with lock(self.root):
            intent = self.open_intent()
            require(intent is not None and intent["request"] == request, "EXACT_OPEN_INTENT")
            require(any(x["kind"] == "PUSH_INTENT" and x["intent_sha256"] == digest(intent) for x in self.events()),
                "NO_POSSIBLE_PROVIDER_SUBMIT_TO_COLLECT")
            require(provider["state"] in TERMINAL and provider["job_id"] == request["job"] and provider["version"] == 1
                and provider["notebook_sha256"] == request["notebook_sha256"], "EXACT_PROVIDER_TERMINAL_REQUIRED")
            require(Path(archive).stat().st_size <= self.grant["caps"]["archive_bytes"], "CAMPAIGN_ARCHIVE_CAP")
            result = runtime.verify_bundle(archive, sha(archive), request["plan"])
            verify_native_custody(request, archive, intent, self.grant)
            history = runtime.sealed_history(archive, sha(archive), request["plan"])
            row = self.append("COLLECTED", intent_sha256=digest(intent), provider=provider, archive=str(Path(archive).resolve()),
                sha256=sha(archive), plan=request["plan"], history=history, verification=result)
            return row

    def summary(self):
        histories, _ = self.histories()
        statuses = {i: "NOT_ATTEMPTED" for i in range(3763)}
        lineage = {i: [] for i in range(3763)}
        for attempt in histories:
            for row in attempt["records"]:
                if row["status"] != "NOT_ATTEMPTED":
                    ordinal = row["ordinal"]
                    lineage[ordinal].append({"attempt_id": attempt["attempt_id"], "status": row["status"], "record_sha256": digest(row)})
                    statuses[ordinal] = row["status"]
        intents = self.intents()
        return {"planned": 3763, "counts": dict(Counter(statuses.values())), "lineage": lineage,
            "reserved_calls": sum(x["reserved_calls"] for x in intents),
            "reserved_gpu_seconds": sum(x["reserved_gpu_seconds"] for x in intents),
            "jobs": len(intents), "blocked_open_intent": self.open_intent() is not None,
            "accounting": "OPERATIONAL_LATEST_STATUS_ALL_OUTCOMES_RETAINED_NOT_SCIENTIFIC_SELECTION",
            "scientific_selection": "PENDING", "pooling": False, "scientific_qualified": False}

    def measure(self, archive, *, job_seconds):
        """Derive a conservative scheduling ceiling from a verified final-source job.

        This is resource planning, never a quality threshold. One observed image
        cannot prove worst-case fit; per-call live storage/time gates still apply.
        """
        import math
        import zipfile
        from safeshift import internvl3763 as runtime
        from safeshift.kaggle_handoff import lock
        require(type(job_seconds) is int and 120 <= job_seconds <= self.grant["caps"]["job_seconds"], "MEASUREMENT_JOB_SECONDS")
        with lock(self.root):
            closed = [x for x in self.events() if x["kind"] == "COLLECTED" and x["sha256"] == sha(archive)]
            require(len(closed) == 1 and closed[0]["provider"]["state"] == "COMPLETE"
                and closed[0]["verification"]["status"] == "PASS", "VERIFIED_FINAL_SOURCE_MEASUREMENT_REQUIRED")
            runtime.verify_bundle(archive, closed[0]["sha256"], closed[0]["plan"])
            with zipfile.ZipFile(archive) as bundle:
                telemetry = json.loads(bundle.read("run/telemetry.json"))
                require(telemetry["evidence_kind"] == "NATIVE" and telemetry["samples"]
                    and telemetry["gpu_peak_allocated_bytes"] > 0 and telemetry["gpu_peak_reserved_bytes"] > 0
                    and telemetry["memory"]["errors"] == [], "LIVE_GPU_RAM_TELEMETRY_REQUIRED")
                observed = [x["seconds"] for x in telemetry["samples"]]
                require(all(type(x) in (int, float) and math.isfinite(x) and x > 0 for x in observed)
                    and math.isfinite(telemetry["load_seconds"]) and telemetry["load_seconds"] >= 0, "FINITE_LIVE_LATENCY")
                sample_bytes = max(x["bytes"] for x in telemetry["samples"])
                raw_float32_bytes = sum(x.file_size for x in bundle.infolist() if x.filename.endswith(".f32"))
                require(sample_bytes > 0 and raw_float32_bytes > 0, "RAW_SIZE_MEASUREMENT_REQUIRED")
                # Twofold latency reserve, full uncompressed conservative capture
                # envelope, setup bound and export margin. Never assume compression.
                setup = json.loads(bundle.read("setup/setup-supervisor.json"))
                require(type(setup.get("seconds")) in (int, float)
                    and math.isfinite(setup["seconds"]) and setup["seconds"] > 0, "SETUP_LATENCY_REQUIRED")
                overhead = math.ceil(2*(setup["seconds"]+telemetry["load_seconds"])) + 120
                per_seconds = max(1, math.ceil(2*max(observed)))
                safe_calls = min(self.grant["caps"]["job_calls"], max(0, (job_seconds-overhead)//per_seconds),
                    max(0, (self.grant["caps"]["archive_bytes"]-2**20)//max(sample_bytes*2, runtime.capture_budget()["per_sample_bytes"])))
                require(safe_calls >= 1, "MEASURED_RESOURCE_ENVELOPE_TOO_SMALL")
                return self.append("MEASURED", source_sha256=digest(closed[0]["plan"]["runtime_source"]), safe_calls=safe_calls,
                    minimum_seconds=overhead+per_seconds*safe_calls, archive_sha256=sha(archive),
                    observed={"telemetry": telemetry, "raw_float32_bytes": raw_float32_bytes,
                        "zip_bytes": Path(archive).stat().st_size, "sample_bytes": sample_bytes},
                    basis="ENGINEERING_ENVELOPE_NOT_WORST_CASE_OR_SCIENTIFIC_QUALIFICATION")


def verify_native_custody(request, archive, intent, grant):
    import zipfile
    with zipfile.ZipFile(archive) as bundle:
        get = lambda name: json.loads(bundle.read(name))
        require(get("handoff.json") == request and get("release.json") == grant
            and get("campaign-intent.json") == intent, "SEALED_CAMPAIGN_INTENT_CUSTODY")
        members = bundle.namelist()
        require("launch-claim.json" in members, "MISSING_LAUNCH_CUSTODY")
        for kind, name in (("launch", "launch-claim.json"), ("worker", "environment/worker-claim.json"), ("load", "run/load-claim.json")):
            if name in members:
                claim = get(name)
                require(claim == native_receipt(kind, request, intent, grant), "NATIVE_CAMPAIGN_CLAIM_DRIFT")
        for row in get("run/summary.json")["records"]:
            name = f"run/samples/{row['ordinal']:06d}/call-claim.json"
            if row["native_calls"]:
                require("environment/worker-claim.json" in members and "run/load-claim.json" in members
                    and name in members and get(name) == native_receipt(f"call-{row['ordinal']:06d}", request, intent, grant),
                    "NATIVE_CALL_WITHOUT_CAMPAIGN_CLAIM")
            if name in members:
                require(row["status"] != "NOT_ATTEMPTED", "UNKNOWN_NATIVE_RESERVATION_STOP")


def native_receipt(kind, request, intent, grant):
    return {"created": True, "kind": kind, "request_sha256": digest(request),
        "intent_sha256": digest(intent), "campaign_sha256": digest(grant)}


class NativeClaims:
    def __init__(self, root, request, intent, grant):
        self.root, self.request, self.intent, self.grant = Path(root), request, intent, grant
        self.root.mkdir(parents=True, exist_ok=True)

    def claim(self, kind):
        from safeshift.kaggle_handoff import lock
        require(kind in ("launch", "worker", "load") or re.fullmatch(r"call-[0-9]{6}", kind), "LOCAL_NATIVE_CLAIM_KIND")
        with lock(self.root):
            parents = {"worker": "launch", "load": "worker"}
            parent = "load" if kind.startswith("call-") else parents.get(kind)
            if parent:
                require(read(self.root / (parent + ".json")) == native_receipt(parent, self.request, self.intent, self.grant), "NATIVE_PARENT_CLAIM")
            if kind.startswith("call-"):
                require(int(kind[5:]) in self.request["plan"]["scheduled_ordinals"], "NATIVE_SCHEDULED_CALL_ONLY")
                previous = sorted(self.root.glob("call-*.json"))
                require(len(previous) < len(self.request["plan"]["scheduled_ordinals"])
                    and int(kind[5:]) == self.request["plan"]["scheduled_ordinals"][len(previous)], "NATIVE_CALL_ORDER_OR_REPLAY")
            receipt = native_receipt(kind, self.request, self.intent, self.grant)
            write(self.root / (kind + ".json"), receipt)
            _sync_directory(self.root)
            return receipt
