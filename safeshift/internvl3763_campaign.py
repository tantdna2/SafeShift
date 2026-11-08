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
MEASURED_TIME_MARGIN_SECONDS = 255
LOCKED_INTERNVL35_VOCAB = 151936
LOCKED_INTERNVL35_TOKENIZER_SIZE = 151679
LOCKED_INTERNVL35_GRAMMAR_GEOMETRY = {
    "id": "internvl35-canonical-json-grammar-v2",
    "language": [
        '{"safety_level":"Level01"}',
        '{"safety_level":"Level02"}',
        '{"safety_level":"Level03"}',
        '{"safety_level":"Level04"}',
    ],
    "eos": [151645],
    "decision_step": 7,
    "decision_tokens": [16, 17, 18, 19],
    "path_lengths": [9, 9, 9, 9],
    "required_tokens_including_eos": 10,
    "paths_sha256": "4c71a3235bec580cb95f78016e3138625528fccbf4b45df5d96cb39f59ff72e1",
}


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
                    require(calls <= qualified[-1]["safe_calls"]
                        and seconds >= required_job_seconds(qualified[-1], calls), "MEASURED_SHARD_LIMIT")
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
                names = set(bundle.namelist())
                if "run/stop.json" in names:
                    stop_obj = runtime._strict_json_loads(bundle.read("run/stop.json"))
                    reason = stop_obj.get("reason", "STOPPED") if type(stop_obj) is dict else "STOPPED"
                    require(False, "MEASUREMENT_RUN_STOPPED_EARLY:" + str(reason))
                telemetry = runtime._strict_json_loads(bundle.read("run/telemetry.json"))
                require(type(telemetry) is dict and telemetry.get("evidence_kind") == "NATIVE"
                    and type(telemetry.get("samples")) is list and len(telemetry["samples"]) >= 1
                    and all(type(s) is dict for s in telemetry["samples"])
                    and type(telemetry.get("gpu_peak_allocated_bytes")) is int and telemetry["gpu_peak_allocated_bytes"] > 0
                    and type(telemetry.get("gpu_peak_reserved_bytes")) is int and telemetry["gpu_peak_reserved_bytes"] > 0,
                    "LIVE_GPU_RAM_TELEMETRY_REQUIRED")
                memory_issue = runtime.inspect_memory_snapshot(telemetry.get("memory"))
                require(memory_issue is None, memory_issue or "CGROUP_MEMORY_UNOBSERVED")
                require(all(type(x.get("seconds")) in (int, float) and math.isfinite(x["seconds"]) and x["seconds"] > 0
                    and type(x.get("bytes")) is int and x["bytes"] > 0
                    and (x.get("ordinal") is None or (type(x["ordinal"]) is int and 0 <= x["ordinal"] < 3763))
                    for x in telemetry["samples"])
                    and type(telemetry.get("load_seconds")) in (int, float)
                    and math.isfinite(telemetry["load_seconds"]) and telemetry["load_seconds"] >= 0, "FINITE_LIVE_LATENCY")
                observed = [x["seconds"] for x in telemetry["samples"]]
                sample_bytes = max(x["bytes"] for x in telemetry["samples"])
                raw_float32_bytes = sum(x.file_size for x in bundle.infolist() if x.filename.endswith(".f32"))
                require(type(sample_bytes) is int and sample_bytes > 0 and raw_float32_bytes > 0, "RAW_SIZE_MEASUREMENT_REQUIRED")
                # Twofold latency reserve, full uncompressed conservative capture
                # envelope, setup/worker non-sample bound and launch(75s)+pre-call(180s) margin.
                setup = runtime._strict_json_loads(bundle.read("setup/setup-supervisor.json"))
                require(type(setup) is dict and type(setup.get("seconds")) in (int, float)
                    and math.isfinite(setup["seconds"]) and setup["seconds"] > 0, "SETUP_LATENCY_REQUIRED")
                worker_non_sample = telemetry["load_seconds"]
                if "worker-supervisor.json" in names:
                    worker_sup = runtime._strict_json_loads(bundle.read("worker-supervisor.json"))
                    require(type(worker_sup) is dict and type(worker_sup.get("seconds")) in (int, float)
                        and math.isfinite(worker_sup["seconds"]) and worker_sup["seconds"] > 0, "WORKER_LATENCY_REQUIRED")
                    worker_non_sample = max(telemetry["load_seconds"], worker_sup["seconds"] - sum(observed))
                overhead = math.ceil(2*(setup["seconds"]+worker_non_sample)) + MEASURED_TIME_MARGIN_SECONDS
                per_seconds = max(1, math.ceil(2*max(observed) + sample_bytes / runtime.EXPORT_RESERVE_BYTES_PER_SECOND))
                sample_budget = _archive_capture_budget(bundle, raw_float32_bytes)
                effective_sample_bytes = max(sample_bytes*2, sample_budget["per_sample_bytes"])
                base_archive_reserve = 64*2**20 if self.grant["caps"]["archive_bytes"] > 512*2**20 else 2**20
                archive_limit = min(self.grant["caps"]["archive_bytes"], sample_budget["archive_verifier_limit_bytes"])
                archive_cap = max(0, (archive_limit-base_archive_reserve)//effective_sample_bytes)
                time_cap = max(0, (job_seconds-overhead)//per_seconds)
                require("environment/preload-resources.json" in names, "OUTPUT_DISK_TELEMETRY_REQUIRED")
                disk_caps, output_free_values = [], []
                for res_name in ("environment/preload-resources.json", "run/loader-resources.json", "environment/resources.json"):
                    if res_name in names:
                        res_obj = runtime._strict_json_loads(bundle.read(res_name))
                        free_pair = res_obj.get("free_bytes") if type(res_obj) is dict else None
                        require(type(free_pair) is list and len(free_pair) == 2
                            and all(type(v) is int and v >= 0 for v in free_pair),
                            "OUTPUT_DISK_TELEMETRY_REQUIRED")
                        output_free_values.append(free_pair[1])
                        per_sample_disk = 2 * effective_sample_bytes
                        disk_caps.append(max(0, (free_pair[1]-2**30-base_archive_reserve)//per_sample_disk))
                require(bool(disk_caps), "OUTPUT_DISK_TELEMETRY_REQUIRED")
                safe_calls = min(self.grant["caps"]["job_calls"], time_cap, archive_cap, *disk_caps)
                require(safe_calls >= 1, "MEASURED_RESOURCE_ENVELOPE_TOO_SMALL")
                return self.append("MEASURED", source_sha256=digest(closed[0]["plan"]["runtime_source"]), safe_calls=safe_calls,
                    minimum_seconds=overhead+per_seconds*safe_calls, overhead_seconds=overhead, per_call_seconds=per_seconds,
                    capture_per_sample_bytes=sample_budget["per_sample_bytes"], effective_sample_bytes=effective_sample_bytes,
                    archive_sha256=sha(archive),
                    observed={"telemetry": telemetry, "raw_float32_bytes": raw_float32_bytes,
                        "zip_bytes": Path(archive).stat().st_size, "sample_bytes": sample_bytes,
                        "setup_seconds": setup["seconds"], "worker_non_sample_seconds": worker_non_sample,
                        "output_free_bytes": min(output_free_values)},
                    basis="ENGINEERING_ENVELOPE_NOT_WORST_CASE_OR_SCIENTIFIC_QUALIFICATION")


def verify_native_custody(request, archive, intent, grant):
    import zipfile
    from safeshift import internvl3763 as runtime
    with zipfile.ZipFile(archive) as bundle:
        get = lambda name: runtime._strict_json_loads(bundle.read(name))
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


def required_job_seconds(measured, calls):
    """Exact minimum job seconds for a shard or repair under a MEASURED envelope.

    Full shards reserve overhead + per_call_seconds * safe_calls (== minimum_seconds).
    Smaller tail shards and targeted repairs reserve overhead + per_call_seconds * calls
    instead of burning a full-shard reservation. Historical MEASURED entries without
    decomposed fields fall back fail-closed to minimum_seconds.
    """
    require(type(measured) is dict and type(calls) is int and calls >= 1, "MEASURED_CALLS_POSITIVE_INT")
    safe_calls = measured.get("safe_calls")
    require(type(safe_calls) is int and safe_calls >= 1, "MEASURED_SAFE_CALLS_REQUIRED")
    require(calls <= safe_calls, "MEASURED_SHARD_LIMIT")
    if "overhead_seconds" in measured and "per_call_seconds" in measured:
        overhead, per_call = measured["overhead_seconds"], measured["per_call_seconds"]
        require(type(overhead) is int and overhead >= 120 and type(per_call) is int and per_call >= 1,
            "MEASURED_ENVELOPE_FIELDS")
        return max(120, overhead + per_call * calls)
    minimum = measured.get("minimum_seconds")
    require(type(minimum) is int and minimum >= 120, "MEASURED_MINIMUM_SECONDS")
    return minimum


def _archive_capture_budget(bundle, raw_float32_bytes):
    from safeshift import internvl3763 as runtime
    from safeshift.internvl_grammar import HNLO_STATUS, LEVELS, POLICY, PROCESSOR, VERSION
    descriptor_path = runtime.ROOT / "configs/grammar/internvl35_v2.json"
    require(sha(descriptor_path) == runtime.capture.FROZEN["configs/grammar/internvl35_v2.json"],
        "FROZEN_GRAMMAR_DESCRIPTOR_DRIFT")
    descriptor = read(descriptor_path)
    expected_language = [f'{{"safety_level":"{lvl}"}}' for lvl in LEVELS]
    require(descriptor.get("schema") == "safeshift-proposed-generation-method-v1"
        and descriptor.get("id") == VERSION and descriptor.get("policy") == dict(POLICY)
        and descriptor.get("language") == expected_language
        and descriptor.get("actual_logits_processors_required") == [PROCESSOR],
        "FROZEN_GRAMMAR_DESCRIPTOR_CONTRACT")
    names = set(bundle.namelist())
    raw_members = sorted(name for name in names if re.fullmatch(r"(?:run/)?samples/[0-9]{6}/raw\.json", name))
    if not raw_members:
        return runtime.capture_budget()
    widths, steps_list, expected_f32_bytes, has_invalid = set(), set(), 0, False
    for raw_name in raw_members:
        prefix_dir = raw_name[:-len("raw.json")]
        grammar_name = prefix_dir + "grammar.json"
        if grammar_name not in names:
            return runtime.capture_budget()
        raw = runtime._strict_json_loads(bundle.read(raw_name))
        grammar = runtime._strict_json_loads(bundle.read(grammar_name))
        width = raw.get("logit_width")
        tok_size = raw.get("tokenizer_size")
        path_lengths = grammar.get("path_lengths")
        eos_ids = grammar.get("eos")
        decision_tokens = grammar.get("decision_tokens")
        decision_step = grammar.get("decision_step")
        required_steps = grammar.get("required_tokens_including_eos")
        require(grammar.get("id") == VERSION and grammar.get("language") == expected_language
            and grammar.get("policy") == dict(POLICY)
            and grammar.get("actual_processors_required") == [PROCESSOR]
            and grammar.get("posthoc_cleanup") is False
            and grammar.get("hnlo") is None and grammar.get("hnlo_status") == HNLO_STATUS,
            "MEASURED_GRAMMAR_RECEIPT_CONTRACT")
        require(type(width) is int and type(tok_size) is int
            and 0 < tok_size <= width <= 200000
            and isinstance(path_lengths, list) and len(path_lengths) == len(LEVELS)
            and len(set(path_lengths)) == 1 and type(path_lengths[0]) is int and path_lengths[0] >= 1
            and type(required_steps) is int and required_steps == path_lengths[0] + 1
            and 0 < required_steps <= POLICY["max_new_tokens"] <= 64
            and isinstance(decision_tokens, list) and len(decision_tokens) == len(LEVELS)
            and len(set(decision_tokens)) == len(LEVELS)
            and type(decision_step) is int and 0 <= decision_step < path_lengths[0]
            and isinstance(eos_ids, list) and len(eos_ids) >= 1
            and all(type(e) is int and 0 <= e < width for e in eos_ids)
            and set(eos_ids).isdisjoint(decision_tokens), "MEASURED_CAPTURE_TRACE_GEOMETRY")
        if width == LOCKED_INTERNVL35_VOCAB:
            require(tok_size == LOCKED_INTERNVL35_TOKENIZER_SIZE
                and all(grammar.get(k) == v for k, v in LOCKED_INTERNVL35_GRAMMAR_GEOMETRY.items()),
                "LOCKED_INTERNVL35_GRAMMAR_GEOMETRY_DRIFT")
        generated = raw.get("generated_ids")
        raw_hashes = raw.get("raw_vector_hashes")
        require(raw.get("grammar") == grammar and raw.get("policy") == dict(POLICY)
            and raw.get("actual_logits_processors") == [PROCESSOR]
            and raw.get("evidence_kind") == "NATIVE" and raw.get("capture_origin") == "forward_before_processors"
            and isinstance(generated, list) and isinstance(raw_hashes, list)
            and 0 < len(generated) == len(raw_hashes) <= 64, "MEASURED_RAW_CAPTURE_CONTRACT")
        for step_idx in range(len(generated)):
            step_f32 = f"{prefix_dir}steps/{step_idx:03d}.f32"
            require(step_f32 in names and bundle.getinfo(step_f32).file_size == width * 4,
                "MEASURED_F32_BYTES_MISMATCH")
        expected_f32_bytes += len(generated) * width * 4
        parsed = runtime.parse_label(raw.get("response", "")) if isinstance(raw.get("response"), str) else None
        if parsed is None and (prefix_dir + "trace-failure.json") in names and (prefix_dir + "trace-verification.json") not in names:
            has_invalid = True
        else:
            trace_name = prefix_dir + "trace-verification.json"
            require(parsed in LEVELS and len(generated) == required_steps
                and generated[-1] in eos_ids and generated[decision_step] in decision_tokens
                and trace_name in names, "MEASURED_CAPTURE_TRACE_GEOMETRY")
            trace = runtime._strict_json_loads(bundle.read(trace_name))
            require(trace.get("status") == "TRACE_CONSISTENT" and trace.get("evidence_kind") == "NATIVE"
                and trace.get("steps") == required_steps and trace.get("label") == parsed,
                "MEASURED_CAPTURE_TRACE_CONSISTENCY")
        widths.add(width)
        steps_list.add(required_steps)
    require(len(widths) == 1 and len(steps_list) == 1 and expected_f32_bytes == raw_float32_bytes,
        "MEASURED_F32_BYTES_MISMATCH")
    if has_invalid:
        return runtime.capture_budget()
    return runtime.capture_budget(vocab=next(iter(widths)), steps=next(iter(steps_list)))


ATTEMPT4_PUBLIC_BASELINE = {
    "provenance": "PUBLIC_GITHUB_RECEIPTS_6658142293_AND_6703549766_NO_PRIVATE_ZIP_READ",
    "caps": {
        "total_calls": 4500,
        "total_jobs": 100,
        "total_gpu_seconds": 80000,
        "job_calls": 1000,
        "job_seconds": 7200,
        "archive_bytes": 7516192768,
        "physical_gpus": 2,
        "machine_shape": "NvidiaTeslaT4",
        "max_repairs_per_image": 10,
    },
    "planned_total": 3763,
    "completed_images": 1,
    "already_reserved_calls": 4,
    "already_reserved_jobs": 4,
    "already_reserved_gpu_seconds": 14400,
    "setup_seconds": "267.21",
    "load_seconds": "73.41",
    "sample_seconds": "13.42",
    "wall_clock_seconds": "872.777",
    "sample_bytes": 14055278,
    "raw_float32_bytes": 6077440,
    "zip_bytes": 5617751,
    "logit_width": 151936,
    "grammar_steps": 10,
    "gpu_peak_allocated_bytes": 14134920704,
    "gpu_peak_reserved_bytes": 14558429184,
    "cgroup_peak_bytes": 21298180096,
    "output_free_bytes": 20937965568,
    "weekly_quota_remaining_seconds": 20727,
    "weekly_quota_limit_seconds": 108000,
    "legacy_source_sha256": "deef3c26eb55e5fb7196cba96220a79a92a058f028cf957a390fad9e010d14ad",
}


def _exact_decimal(value, *, allow_zero=False):
    from decimal import Decimal, InvalidOperation
    require(type(value) is not bool and isinstance(value, (int, float, str, Decimal)), "EXACT_NUMERIC_INPUT")
    if isinstance(value, float):
        import math
        require(math.isfinite(value), "FINITE_NUMERIC_INPUT")
        dec = Decimal(str(value))
    else:
        try:
            dec = Decimal(value)
        except InvalidOperation as error:
            raise ValueError("EXACT_NUMERIC_INPUT") from error
    require(dec.is_finite() and (dec >= 0 if allow_zero else dec > 0) and dec <= Decimal(10**15), "BOUNDED_NUMERIC_INPUT")
    return dec


def _ceil_int(dec):
    from decimal import ROUND_CEILING
    return int(dec.to_integral_exact(rounding=ROUND_CEILING))


def _weekly_quota_plan(job_wall_seconds, job_calls, week1_remaining, weekly_limit):
    basis = "CONDITIONAL_ON_ATTEMPT4_OBSERVED_RATE_AND_QUOTA_AVAILABILITY_NOT_GUARANTEED"
    if not job_wall_seconds:
        return {"feasible": True, "basis": basis, "weeks_required": 0, "week1_images_completed": 0, "weeks": []}
    if any(sec > weekly_limit for sec in job_wall_seconds):
        return {"feasible": False, "basis": basis, "reason": "SINGLE_JOB_EXCEEDS_WEEKLY_QUOTA",
            "weeks_required": None, "week1_images_completed": 0, "weeks": []}
    weeks = []
    week_num = 1
    available = week1_remaining
    used, jobs_in_week, images_in_week = 0, 0, 0
    for sec, calls in zip(job_wall_seconds, job_calls):
        if used + sec > available:
            weeks.append({"week": week_num, "quota_available_seconds": available, "jobs": jobs_in_week,
                "images": images_in_week, "wall_seconds_used": used, "quota_remaining_seconds": available - used})
            week_num += 1
            available = weekly_limit
            used, jobs_in_week, images_in_week = 0, 0, 0
        used += sec
        jobs_in_week += 1
        images_in_week += calls
    if jobs_in_week or not weeks:
        weeks.append({"week": week_num, "quota_available_seconds": available, "jobs": jobs_in_week,
            "images": images_in_week, "wall_seconds_used": used, "quota_remaining_seconds": available - used})
    week1_imgs = weeks[0]["images"] if weeks and weeks[0]["week"] == 1 else 0
    return {"feasible": True, "basis": basis, "weeks_required": weeks[-1]["week"],
        "week1_images_completed": week1_imgs, "weeks": weeks}


def project_campaign_budget(*, caps=None, planned_total=3763, completed_images=1, pending_repair_images=0,
        already_reserved_calls=4, already_reserved_jobs=4, already_reserved_gpu_seconds=14400,
        setup_seconds="267.21", load_seconds="73.41", sample_seconds="13.42", wall_clock_seconds="872.777",
        non_sample_seconds=None, sample_bytes=14055278, raw_float32_bytes=6077440, zip_bytes=5617751,
        logit_width=151936, grammar_steps=10, capture_per_sample_bytes=None, output_free_bytes=20937965568,
        weekly_quota_remaining_seconds=20727, weekly_quota_limit_seconds=108000,
        source_changed=True, measurement_job_seconds=1800, alt_job_seconds=10800,
        contingency_repair_calls=100, contingency_extra_jobs=4, verify_f32_geometry=True):
    """Deterministic offline resource & O5 feasibility model for remaining TRAIN images.

    Read-only pure calculation: zero network/Kaggle/GPU calls, zero ledger mutation,
    and never modifies approved Grant/O5 caps. Distinguishes reserved 2xT4 physical
    GPU-seconds from 1x modeled Kaggle quota wall-clock consumption, and never claims
    single-image latency as a population-wide bound or calendar guarantee.
    """
    from decimal import Decimal
    from safeshift import internvl3763 as runtime
    caps = deepcopy(ATTEMPT4_PUBLIC_BASELINE["caps"] if caps is None else caps)
    require(type(caps) is dict and set(caps) == {"total_calls", "total_jobs", "total_gpu_seconds", "job_calls",
        "job_seconds", "archive_bytes", "physical_gpus", "machine_shape", "max_repairs_per_image"}, "FINITE_CAMPAIGN_CAPS")
    require(all(type(v) is int and 0 < v <= 10**12 for k, v in caps.items() if k != "machine_shape"), "POSITIVE_INTEGER_CAPS")
    require(caps["physical_gpus"] == 2 and caps["machine_shape"] == "NvidiaTeslaT4"
        and caps["job_calls"] <= 3763 and 120 <= caps["job_seconds"] <= 43200
        and caps["archive_bytes"] <= 7 * 2**30, "UNSUPPORTED_CAMPAIGN_CAPS")
    require(type(source_changed) is bool and type(verify_f32_geometry) is bool, "BOOLEAN_FLAG_REQUIRED")
    for name, val, low, high in (
        ("planned_total", planned_total, 1, 100000),
        ("completed_images", completed_images, 0, planned_total),
        ("pending_repair_images", pending_repair_images, 0, completed_images),
        ("already_reserved_calls", already_reserved_calls, 0, 10**9),
        ("already_reserved_jobs", already_reserved_jobs, 0, 10**9),
        ("already_reserved_gpu_seconds", already_reserved_gpu_seconds, 0, 10**12),
        ("sample_bytes", sample_bytes, 1, 8 * 2**30),
        ("raw_float32_bytes", raw_float32_bytes, 1, 8 * 2**30),
        ("zip_bytes", zip_bytes, 1, 8 * 2**30),
        ("logit_width", logit_width, 1, 200000),
        ("grammar_steps", grammar_steps, 1, 64),
        ("weekly_quota_remaining_seconds", weekly_quota_remaining_seconds, 0, 10**9),
        ("weekly_quota_limit_seconds", weekly_quota_limit_seconds, 120, 10**9),
        ("measurement_job_seconds", measurement_job_seconds, 120, 43200),
        ("alt_job_seconds", alt_job_seconds, 120, 43200),
        ("contingency_repair_calls", contingency_repair_calls, 0, 10**6),
        ("contingency_extra_jobs", contingency_extra_jobs, 0, 10**5),
    ):
        require(type(val) is int and low <= val <= high, "BUDGET_INT_BOUND:" + name)
    require(weekly_quota_remaining_seconds <= weekly_quota_limit_seconds, "WEEKLY_QUOTA_REMAINING_BOUND")
    require(measurement_job_seconds <= caps["job_seconds"], "MEASUREMENT_JOB_EXCEEDS_CAP")
    if output_free_bytes is not None:
        require(type(output_free_bytes) is int and 0 <= output_free_bytes <= 10**15, "OUTPUT_FREE_BYTES_BOUND")
    if verify_f32_geometry:
        require(raw_float32_bytes == grammar_steps * logit_width * 4, "F32_GEOMETRY_MISMATCH")

    setup_dec = _exact_decimal(setup_seconds)
    load_dec = _exact_decimal(load_seconds, allow_zero=True)
    sample_dec = _exact_decimal(sample_seconds)
    wall_dec = _exact_decimal(wall_clock_seconds)
    require(wall_dec >= sample_dec, "WALL_CLOCK_LESS_THAN_SAMPLE")
    non_sample_dec = (wall_dec - sample_dec) if non_sample_seconds is None else _exact_decimal(non_sample_seconds)
    require(non_sample_dec >= setup_dec + load_dec, "NON_SAMPLE_LESS_THAN_SETUP_LOAD")

    remaining_images = planned_total - completed_images
    total_work_images = remaining_images + pending_repair_images
    gpus = caps["physical_gpus"]
    rem_calls_cap = caps["total_calls"] - already_reserved_calls
    rem_jobs_cap = caps["total_jobs"] - already_reserved_jobs
    rem_gpu_sec_cap = caps["total_gpu_seconds"] - already_reserved_gpu_seconds
    require(rem_calls_cap >= 0 and rem_jobs_cap >= 0 and rem_gpu_sec_cap >= 0, "ALREADY_EXCEEDED_CAPS")

    legacy_capture = runtime.capture_budget()
    proven_capture = runtime.capture_budget(vocab=logit_width, steps=grammar_steps)
    if capture_per_sample_bytes is not None:
        require(type(capture_per_sample_bytes) is int
            and 1 <= capture_per_sample_bytes <= legacy_capture["per_sample_bytes"],
            "BUDGET_INT_BOUND:capture_per_sample_bytes")
        proven_capture = {**proven_capture, "per_sample_bytes": capture_per_sample_bytes,
            "sample_and_export_bytes": 2 * capture_per_sample_bytes,
            "all3763_uncompressed_bytes": capture_per_sample_bytes * planning_count if (planning_count := planned_total) else 0}
    legacy_overhead = _ceil_int(Decimal(2) * (setup_dec + load_dec)) + 120
    legacy_per_call_sec = max(1, _ceil_int(Decimal(2) * sample_dec))
    legacy_archive_cap = max(0, (caps["archive_bytes"] - 2**20) // max(sample_bytes * 2, legacy_capture["per_sample_bytes"]))
    legacy_time_cap = max(0, (caps["job_seconds"] - legacy_overhead) // legacy_per_call_sec)
    legacy_safe_calls = min(caps["job_calls"], legacy_time_cap, legacy_archive_cap)
    require(legacy_safe_calls >= 1, "LEGACY_ENVELOPE_ZERO")
    legacy_min_sec = legacy_overhead + legacy_per_call_sec * legacy_safe_calls

    export_sec_per_call = Decimal(sample_bytes) / Decimal(runtime.EXPORT_RESERVE_BYTES_PER_SECOND)
    opt_per_call_sec = max(1, _ceil_int(Decimal(2) * sample_dec + export_sec_per_call))
    base_archive_reserve = 64 * 2**20 if caps["archive_bytes"] > 512 * 2**20 else 2**20
    archive_limit = min(caps["archive_bytes"], proven_capture["archive_verifier_limit_bytes"])
    effective_sample_bytes = max(sample_bytes * 2, proven_capture["per_sample_bytes"])
    proven_archive_cap = max(0, (archive_limit - base_archive_reserve) // effective_sample_bytes)
    disk_cap = None
    if output_free_bytes is not None:
        per_sample_disk = 2 * effective_sample_bytes
        disk_cap = max(0, (output_free_bytes - 2**30 - base_archive_reserve) // per_sample_disk)
    full_overhead = _ceil_int(Decimal(2) * non_sample_dec) + MEASURED_TIME_MARGIN_SECONDS

    def _append_batch_jobs(count, safe_calls, job_sec_cap, overhead_sec, per_call_s, fixed_min_sec, label,
                           job_calls_list, job_res_sec_list, job_obs_sec_list):
        full_shards, tail_calls = divmod(count, safe_calls)
        for _ in range(full_shards):
            sec = fixed_min_sec if fixed_min_sec is not None else max(120, overhead_sec + per_call_s * safe_calls)
            require(sec <= job_sec_cap, "SHARD_SECONDS_EXCEED_JOB_CAP:" + label)
            job_calls_list.append(safe_calls)
            job_res_sec_list.append(sec)
            job_obs_sec_list.append(_ceil_int(non_sample_dec + sample_dec * Decimal(safe_calls)))
        if tail_calls:
            sec = fixed_min_sec if fixed_min_sec is not None else max(120, overhead_sec + per_call_s * tail_calls)
            require(sec <= job_sec_cap, "TAIL_SECONDS_EXCEED_JOB_CAP:" + label)
            job_calls_list.append(tail_calls)
            job_res_sec_list.append(sec)
            job_obs_sec_list.append(_ceil_int(non_sample_dec + sample_dec * Decimal(tail_calls)))
        return tail_calls

    def evaluate_envelope(label, *, job_sec_cap, safe_calls, overhead_sec, per_call_s, fixed_min_sec=None, needs_re_measure=False):
        job_calls_list, job_res_sec_list, job_obs_sec_list = [], [], []
        rem_resume = remaining_images
        rem_repair = pending_repair_images
        measured_via_job = False
        if (rem_resume + rem_repair) > 0 and needs_re_measure:
            job_calls_list.append(1)
            job_res_sec_list.append(measurement_job_seconds)
            job_obs_sec_list.append(_ceil_int(non_sample_dec + sample_dec))
            measured_via_job = True
            if rem_resume > 0:
                rem_resume -= 1
            else:
                rem_repair -= 1
        resume_tail = _append_batch_jobs(rem_resume, safe_calls, job_sec_cap, overhead_sec, per_call_s, fixed_min_sec, label,
            job_calls_list, job_res_sec_list, job_obs_sec_list) if rem_resume > 0 else 0
        if rem_repair > 0:
            _append_batch_jobs(rem_repair, safe_calls, job_sec_cap, overhead_sec, per_call_s, fixed_min_sec, label + "_repair",
                job_calls_list, job_res_sec_list, job_obs_sec_list)
        fut_jobs = len(job_calls_list)
        fut_calls = sum(job_calls_list)
        fut_wall_res = sum(job_res_sec_list)
        fut_gpu_res = fut_wall_res * gpus
        pre_export_wall_obs = sum(job_obs_sec_list)
        # Attempt4's setup + worker clock excludes parent ZIP/export. Account
        # for that phase explicitly; 5 MiB/s is an engineering assumption, not
        # measured provider throughput or a bound on compression/CRC time.
        export_seconds = [_ceil_int(Decimal(base_archive_reserve + sample_bytes * n)
            / Decimal(runtime.EXPORT_RESERVE_BYTES_PER_SECOND)) for n in job_calls_list]
        quota_seconds = [wall + sealing for wall, sealing in zip(job_obs_sec_list, export_seconds)]
        fut_wall_obs = sum(quota_seconds)
        tot_jobs = already_reserved_jobs + fut_jobs
        tot_calls = already_reserved_calls + fut_calls
        tot_gpu_res = already_reserved_gpu_seconds + fut_gpu_res
        shortfall_gpu = max(0, tot_gpu_res - caps["total_gpu_seconds"])
        shortfall_calls = max(0, tot_calls - caps["total_calls"])
        shortfall_jobs = max(0, tot_jobs - caps["total_jobs"])
        headroom_gpu = max(0, caps["total_gpu_seconds"] - tot_gpu_res)
        feasible = (shortfall_gpu == 0 and shortfall_calls == 0 and shortfall_jobs == 0)

        # Max completable remaining unattempted images under current remaining budget without changing caps
        avail_gpu = rem_gpu_sec_cap
        avail_jobs = rem_jobs_cap
        avail_calls = rem_calls_cap
        max_completable = 0
        if remaining_images > 0 and needs_re_measure:
            if avail_jobs >= 1 and avail_calls >= 1 and avail_gpu >= measurement_job_seconds * gpus:
                avail_jobs -= 1
                avail_calls -= 1
                avail_gpu -= measurement_job_seconds * gpus
                max_completable += 1
            else:
                avail_jobs = 0
        if max_completable < remaining_images and avail_jobs > 0 and avail_calls > 0:
            full_sec = (fixed_min_sec if fixed_min_sec is not None else max(120, overhead_sec + per_call_s * safe_calls)) * gpus
            n_full = min(avail_jobs, avail_calls // safe_calls, avail_gpu // full_sec,
                (remaining_images - max_completable) // safe_calls)
            max_completable += n_full * safe_calls
            avail_jobs -= n_full
            avail_calls -= n_full * safe_calls
            avail_gpu -= n_full * full_sec
            leftover = min(remaining_images - max_completable, avail_calls, safe_calls - 1)
            if avail_jobs >= 1 and leftover >= 1:
                if fixed_min_sec is not None:
                    if avail_gpu >= fixed_min_sec * gpus:
                        max_completable += leftover
                else:
                    affordable = (avail_gpu // gpus - overhead_sec) // per_call_s
                    if affordable >= 1:
                        max_completable += min(leftover, affordable)

        weekly = _weekly_quota_plan(quota_seconds, job_calls_list,
            weekly_quota_remaining_seconds, weekly_quota_limit_seconds)
        tail_sec = (fixed_min_sec if fixed_min_sec is not None else max(120, overhead_sec + per_call_s * resume_tail)) if resume_tail else 0
        return {
            "job_seconds_cap": job_sec_cap,
            "safe_calls_per_job": safe_calls,
            "overhead_seconds": overhead_sec,
            "per_call_seconds": per_call_s,
            "full_shard_seconds": fixed_min_sec if fixed_min_sec is not None else max(120, overhead_sec + per_call_s * safe_calls),
            "tail_shard_calls": resume_tail,
            "tail_shard_seconds": tail_sec,
            "requires_new_source_1call_measurement": measured_via_job,
            "future_jobs": fut_jobs,
            "future_calls": fut_calls,
            "future_reserved_wall_seconds": fut_wall_res,
            "future_reserved_gpu_seconds": fut_gpu_res,
            "campaign_total_jobs": tot_jobs,
            "campaign_total_calls": tot_calls,
            "campaign_total_reserved_gpu_seconds": tot_gpu_res,
            "feasible_under_current_o5": feasible,
            "shortfall_gpu_seconds": shortfall_gpu,
            "shortfall_calls": shortfall_calls,
            "shortfall_jobs": shortfall_jobs,
            "headroom_gpu_seconds": headroom_gpu,
            "max_completable_remaining_images_under_current_o5": max_completable,
            "unattempted_images_left_under_current_o5": remaining_images - max_completable,
            "estimated_observed_kaggle_quota_seconds": fut_wall_obs,
            "attempt4_rate_pre_export_wall_seconds": pre_export_wall_obs,
            "modeled_export_seconds": sum(export_seconds),
            "quota_estimate_basis": "ATTEMPT4_RATE_PLUS_MODELED_EXPORT_NOT_LIVE_QUOTA_OR_THROUGHPUT_PROOF",
            "weekly_quota_schedule": weekly,
        }

    opt_7200_time_cap = max(0, (caps["job_seconds"] - full_overhead) // opt_per_call_sec)
    opt_7200_caps = [caps["job_calls"], opt_7200_time_cap, proven_archive_cap] + ([disk_cap] if disk_cap is not None else [])
    opt_7200_safe_calls = min(opt_7200_caps)
    require(opt_7200_safe_calls >= 1, "OPTIMIZED_7200_ENVELOPE_ZERO")

    opt_alt_time_cap = max(0, (alt_job_seconds - full_overhead) // opt_per_call_sec)
    opt_alt_caps = [caps["job_calls"], opt_alt_time_cap, proven_archive_cap] + ([disk_cap] if disk_cap is not None else [])
    opt_alt_safe_calls = min(opt_alt_caps)
    require(opt_alt_safe_calls >= 1, "OPTIMIZED_ALT_ENVELOPE_ZERO")

    scen_legacy = evaluate_envelope("legacy_current_main", job_sec_cap=caps["job_seconds"],
        safe_calls=legacy_safe_calls, overhead_sec=legacy_overhead, per_call_s=legacy_per_call_sec,
        fixed_min_sec=legacy_min_sec, needs_re_measure=False)
    scen_opt_7200 = evaluate_envelope("optimized_safe_current_job_cap", job_sec_cap=caps["job_seconds"],
        safe_calls=opt_7200_safe_calls, overhead_sec=full_overhead, per_call_s=opt_per_call_sec,
        fixed_min_sec=None, needs_re_measure=source_changed)
    scen_opt_alt = evaluate_envelope("optimized_safe_alt_job_cap", job_sec_cap=alt_job_seconds,
        safe_calls=opt_alt_safe_calls, overhead_sec=full_overhead, per_call_s=opt_per_call_sec,
        fixed_min_sec=None, needs_re_measure=source_changed)

    obs_inf_wall = sample_dec * Decimal(total_work_images)
    obs_inf_gpu = _ceil_int(obs_inf_wall * Decimal(gpus))
    obs_with_shard_wall = Decimal(scen_opt_7200["future_jobs"]) * non_sample_dec + obs_inf_wall
    obs_with_shard_gpu = _ceil_int(obs_with_shard_wall * Decimal(gpus))
    scen_observed = {
        "basis": "ILLUSTRATIVE_SINGLE_IMAGE_EXTRAPOLATION_NOT_POPULATION_LOWER_BOUND_OR_GUARANTEE",
        "proven_population_lower_bound": False,
        "inference_only_at_attempt4_rate_wall_seconds": _ceil_int(obs_inf_wall),
        "inference_only_at_attempt4_rate_physical_gpu_seconds": obs_inf_gpu,
        "inference_only_at_attempt4_rate_exceeds_remaining_o5_by_gpu_seconds": max(0, obs_inf_gpu - rem_gpu_sec_cap),
        "with_1x_shard_overhead_wall_seconds": _ceil_int(obs_with_shard_wall),
        "with_1x_shard_overhead_physical_gpu_seconds": obs_with_shard_gpu,
        "campaign_total_equivalent_physical_gpu_seconds": already_reserved_gpu_seconds + obs_with_shard_gpu,
        "within_current_o5_if_extrapolated": (already_reserved_gpu_seconds + obs_inf_gpu) <= caps["total_gpu_seconds"],
    }

    sensitivity_rows = []
    for mult_str in ("1.00", "1.25", "1.50"):
        mult = Decimal(mult_str)
        adj_per_call = max(1, _ceil_int((Decimal(2) * sample_dec + export_sec_per_call) * mult))
        t_cap = max(0, (caps["job_seconds"] - full_overhead) // adj_per_call)
        s_calls = min([caps["job_calls"], t_cap, proven_archive_cap] + ([disk_cap] if disk_cap is not None else []))
        if s_calls < 1:
            sensitivity_rows.append({"latency_multiplier": mult_str, "per_call_seconds": adj_per_call, "safe_calls": 0, "feasible_job_cap": False})
            continue
        rem_res_m = remaining_images
        rem_rep_m = pending_repair_images
        base_wall = 0
        if source_changed and (rem_res_m + rem_rep_m) > 0:
            base_wall += measurement_job_seconds
            if rem_res_m > 0:
                rem_res_m -= 1
            else:
                rem_rep_m -= 1
        for batch_count in (rem_res_m, rem_rep_m):
            if batch_count > 0:
                f_shards, t_calls = divmod(batch_count, s_calls)
                base_wall += f_shards * max(120, full_overhead + adj_per_call * s_calls)
                if t_calls:
                    base_wall += max(120, full_overhead + adj_per_call * t_calls)
        contingency_wall = contingency_extra_jobs * full_overhead + contingency_repair_calls * adj_per_call
        tot_gpu = already_reserved_gpu_seconds + (base_wall + contingency_wall) * gpus
        sensitivity_rows.append({
            "latency_multiplier": mult_str,
            "per_call_seconds": adj_per_call,
            "safe_calls_at_current_job_cap": s_calls,
            "zero_error_campaign_gpu_seconds": already_reserved_gpu_seconds + base_wall * gpus,
            "with_contingency_campaign_gpu_seconds": tot_gpu,
        })

    recommended_gpu_cap = max(360000, ((sensitivity_rows[1]["with_contingency_campaign_gpu_seconds"] + 9999) // 10000) * 10000)
    return {
        "schema": "safeshift-train3763-budget-projection-v1",
        "scientific_qualified": False,
        "o5_caps_modified": False,
        "inputs": {
            "caps": caps,
            "planned_total": planned_total,
            "completed_images": completed_images,
            "pending_repair_images": pending_repair_images,
            "remaining_images": remaining_images,
            "contingency": {
                "repair_calls": contingency_repair_calls,
                "extra_jobs": contingency_extra_jobs,
                "basis": "EXTRA_JOB_OVERHEAD_PLUS_REPAIR_CALL_TIME_NOT_FULL_JOB_TIMEOUTS",
            },
            "observation": {
                "setup_seconds": str(setup_dec), "load_seconds": str(load_dec),
                "sample_seconds": str(sample_dec), "wall_clock_seconds": str(wall_dec),
                "non_sample_seconds": str(non_sample_dec), "sample_bytes": sample_bytes,
                "raw_float32_bytes": raw_float32_bytes, "zip_bytes": zip_bytes,
                "output_free_bytes": output_free_bytes,
                "population_latency_distribution_verified": False,
                "export_throughput_measured": False,
            },
            "already_reserved": {
                "jobs": already_reserved_jobs,
                "calls": already_reserved_calls,
                "gpu_seconds": already_reserved_gpu_seconds,
            },
            "grant_remaining": {
                "jobs": rem_jobs_cap,
                "calls": rem_calls_cap,
                "gpu_seconds": rem_gpu_sec_cap,
                "max_wall_seconds_on_2xt4": rem_gpu_sec_cap // gpus,
            },
            "weekly_quota": {
                "remaining_seconds_week1": weekly_quota_remaining_seconds,
                "weekly_limit_seconds": weekly_quota_limit_seconds,
            },
        },
        "envelope_constants": {
            "contract_minimum_job_seconds": 120,
            "stage_export_reserve_seconds": 60,
            "worker_exit_reserve_seconds": 15,
            "launch_worker_headroom_seconds": 75,
            "pre_call_reserve_seconds": 180,
            "measured_time_margin_seconds": MEASURED_TIME_MARGIN_SECONDS,
            "export_reserve_bytes_per_second": runtime.EXPORT_RESERVE_BYTES_PER_SECOND,
            "new_source_1call_measurement_job_seconds": measurement_job_seconds,
        },
        "capture_envelope": {
            "legacy_64step_200k_per_sample_bytes": legacy_capture["per_sample_bytes"],
            "legacy_archive_safe_calls": legacy_archive_cap,
            "grammar_v2_proven_per_sample_bytes": proven_capture["per_sample_bytes"],
            "effective_twofold_sample_bytes": effective_sample_bytes,
            "effective_twofold_disk_bytes_per_sample": 2 * effective_sample_bytes,
            "base_archive_reserve_bytes": base_archive_reserve,
            "proven_archive_safe_calls": proven_archive_cap,
            "output_disk_safe_calls": disk_cap,
        },
        "scenarios": {
            "legacy_current_main": scen_legacy,
            "optimized_safe_current_job_cap": scen_opt_7200,
            "optimized_safe_alt_job_cap": scen_opt_alt,
            "observed_extrapolation_not_guarantee": scen_observed,
        },
        "sensitivity": sensitivity_rows,
        "verdict": {
            "completable_under_current_o5": scen_opt_7200["feasible_under_current_o5"],
            "population_latency_distribution_verified": False,
            "primary_blocker": "NONE" if scen_opt_7200["feasible_under_current_o5"] else "TOTAL_GPU_SECONDS_CAP_INSUFFICIENT_UNDER_MODELED_SAFE_ENVELOPE",
            "new_source_measurement_required": source_changed and total_work_images > 0,
            "new_source_measurement_target": (
                "ordinal_1_via_resume_1call_1800s_preserving_ordinal_0_success"
                if completed_images == 1 and pending_repair_images == 0 and source_changed
                else ("ordinal_0_via_initial_1call" if completed_images == 0 and source_changed else "next_pending_ordinal_or_already_measured")
            ),
            "minimum_zero_margin_o5_gpu_seconds_current_job_cap": scen_opt_7200["campaign_total_reserved_gpu_seconds"],
            "minimum_zero_margin_o5_gpu_seconds_alt_job_cap": scen_opt_alt["campaign_total_reserved_gpu_seconds"],
            "recommended_owner_o5_decision": {
                "status": "PROPOSED_PENDING_OWNER_DECISION_NOT_ACTIVE" if not scen_opt_7200["feasible_under_current_o5"] else "NOT_REQUIRED",
                "requires_owner_authorization": not scen_opt_7200["feasible_under_current_o5"],
                "current_active_total_gpu_seconds": caps["total_gpu_seconds"],
                "proposed_total_gpu_seconds": recommended_gpu_cap,
                "proposed_total_calls": caps["total_calls"],
                "proposed_total_jobs": caps["total_jobs"],
                "optional_job_seconds_for_264_call_shards": alt_job_seconds,
            },
        },
    }
