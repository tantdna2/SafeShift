"""Offline Owner-assisted continuation; never imports an SDK or opens a socket.

Execute this external companion with --approved-repo pointing to the ORIGINAL
operator checkout. It deliberately stays outside the runtime source manifest.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

if __name__ == "__main__":
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--approved-repo", type=Path, required=True)
    boot, _ = bootstrap.parse_known_args()
    sys.path.insert(0, str(boot.approved_repo.resolve()))

from safeshift import internvl3763 as runtime
from safeshift import internvl3763_campaign as campaign
from safeshift import internvl3763_operator as operator
from safeshift import internvl3763_release as authority
from safeshift.candidates.source import require
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write, write_bytes, sha, safe
from safeshift.pilot.contract import digest, json_bytes, require_hash
_manual_spec = importlib.util.spec_from_file_location("continuation_manual", Path(__file__).with_name("reconcile_train3763_manual.py"))
manual = importlib.util.module_from_spec(_manual_spec)
_manual_spec.loader.exec_module(manual)

SCHEMA = "safeshift-train3763-offline-continuation-v1"
DECISION_ID = 6816197123
DECISION_BODY_SHA256 = "50e416ea2d77606bbbdad7e1bc660be36af4d979720d47234ac22e234c03d5f8"
BASELINE_OWNER = {"comment_id": 6815882405, "body_sha256": "d47c1ed216fb0fea33456806e0331ac6f3dccb7c28f4cf7f7fb784abaa8fee3e"}
RELEASE = "SAFESHIFT_TRAIN3763_CONTINUATION_RELEASE_V1"
FINAL = "SAFESHIFT_TRAIN3763_CONTINUATION_FINAL_V1"
ADMISSION = "OFFLINE_CONTINUATION_ADMISSION"
RECONCILED = "OFFLINE_CONTINUATION_RECONCILED"


def result_tools():
    spec = importlib.util.spec_from_file_location("train3763_results", Path(__file__).with_name("train3763_results.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tool_manifest():
    return {name: sha(Path(__file__).with_name(name)) for name in
        ("train3763_continuation.py", "owner_verify_train3763_continuation.py", "reconcile_train3763_manual.py", "train3763_results.py")}


def archive_resources(archive, intent):
    return result_tools().resources(archive, intent)


class Exports:
    """Replay only explicit Owner-acquired GitHub responses; no network fallback.

    Offline JSON cannot prove its own origin. Custody starts with the Owner's
    authenticated export. Reviewers must verify the linked originals on GitHub.
    """
    def __init__(self, value):
        require(type(value) is dict and len(value) <= 128 and all(re.fullmatch(r"/(?:issues/comments|pulls)/[1-9][0-9]*", k)
            for k in value), "OWNER_GITHUB_EXPORTS_REQUIRED")
        self.value = value

    def __call__(self, path):
        require(path in self.value, "MISSING_REAL_GITHUB_EXPORT:" + path)
        return deepcopy(self.value[path])


def _copy(source, target):
    """Exclusive copy; leave any partial file after interruption for diagnosis."""
    source, target = Path(source), Path(target)
    require(source.is_file() and not source.is_symlink() and source.stat().st_nlink == 1, "REGULAR_EVIDENCE_REQUIRED")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        require(target.is_file() and target.stat().st_nlink == 1 and target.stat().st_size == source.stat().st_size
            and sha(target) == sha(source), "INTERRUPTED_COPY_CONFLICT_PRESERVED")
        return  # a complete create-only copy survived before receipt publication
    with source.open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst, 2**20)
        dst.flush()
        os.fsync(dst.fileno())
    require(sha(source) == sha(target), "COPY_CHANGED")
    campaign._sync_directory(target.parent)


def _pair(root, mirror, name, value):
    for directory in (root, mirror):
        write(safe(directory, name), value)
        campaign._sync_directory(directory)


def _relative(path):
    path = Path(path).resolve()
    require(path.is_relative_to(runtime.ROOT.resolve()), "OWNER_REPOSITORY_CUSTODY_REQUIRED")
    return path.relative_to(runtime.ROOT.resolve()).as_posix()


def _private(path):
    path = Path(path).absolute()
    name = path.relative_to(runtime.ROOT.resolve()).as_posix()
    safe(runtime.ROOT, name)
    require(path.resolve().is_relative_to((runtime.ROOT / "data/processed").resolve()), "PRIVATE_PROCESSED_CUSTODY_REQUIRED")
    return path


def original_handoff(ledger, intent):
    from safeshift.kaggle_handoff import Session
    return manual.handoff_snapshot(Session(ledger.root.parent / "attempt-11"), intent["request"], mode=manual.SAME_SLUG)


def baseline_owner(grant, intent, exports):
    value, comment = campaign.record(BASELINE_OWNER, manual.SAME_OWNER_MARKER, Exports(exports))
    request = intent["request"]
    require(comment["user"]["login"] == authority.OWNER and comment["user"]["id"] == 246929698
        and comment["issue_url"] == authority.API + "/issues/180" and value["campaign_sha256"] == digest(grant)
        and value["intent_sha256"] == digest(intent) and value["request_sha256"] == digest(request)
        and value["ledger_events"] == 35 and value["ledger_head_sha256"] == digest(intent)
        and value["plan_sha256"] == digest(request["plan"]) and value["scheduled_ordinals"] == list(range(323, 523))
        and value["input_sources"] == operator.input_sources(request) and value["job"] == request["job"]
        and value["version"] == 1 and value["mode"] == manual.SAME_SLUG and value["operator"] == manual.PROVENANCE
        and value["no_api_submission"] is True and value["no_other_job_or_version"] is True, "ORIGINAL_ATTEMPT11_OWNER_FACTS")
    return value


def provider_proof(proof, intent, archive, *, job, kernel_id=None, state="COMPLETE"):
    """Check the concrete provider-copy/capsule bindings in the Owner report."""
    request, archive = intent["request"], Path(archive)
    p = proof["provider"]
    expected = sha(archive)
    require(proof["intent_sha256"] == digest(intent) and proof["archive_sha256"] == expected
        and p["job_id"] == job and p["state"] == state and type(p["version"]) is int and p["version"] == 1
        and type(p["kernel_id"]) is int and p["kernel_id"] > 0 and (kernel_id is None or p["kernel_id"] == kernel_id)
        and proof["input_bytes_verified"] is True and proof["provider_copy_verified"] is True, "FINAL_PROVIDER_PROOF_BINDINGS")
    capsule = proof["capsule"]
    require(capsule["ref"] == request["bindings"]["runtime"]["execution_input"]["ref"]
        and type(capsule["version"]) is int and capsule["version"] == 1
        and capsule["sha256"] == digest({"request": request, "campaign_intent": intent})
        and capsule["request_sha256"] == digest(request) and capsule["intent_sha256"] == digest(intent), "FINAL_CAPSULE_PROOF_BINDINGS")
    output = proof["output"]
    require(output["sha256"] == expected and output["bytes"] == archive.stat().st_size
        and output["sidecar_sha256"] == sha(str(archive) + ".sha256.json"), "FINAL_PROVIDER_COPY_BINDINGS")
    require_hash(output["log_sha256"])


def merge_exports(base, comments):
    result = deepcopy(Exports(base).value)
    for comment in comments:
        require(type(comment.get("id")) is int and comment["id"] > 0, "REAL_COMMENT_EXPORT_REQUIRED")
        path = "/issues/comments/" + str(comment["id"])
        require(path not in result or result[path] == comment, "GITHUB_EXPORT_CONFLICT")
        result[path] = comment
    return Exports(result).value


def source_check(request):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=runtime.ROOT, text=True).strip()
    require(head == request["commit_sha"] and not subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=runtime.ROOT), "ORIGINAL_CLEAN_OPERATOR_CHECKOUT_REQUIRED")
    require(runtime.source_spec() == request["plan"]["runtime_source"]
        == request["bindings"]["runtime"]["execution_request"]["source"], "ORIGINAL_SOURCE_CHANGED")
    path = safe(runtime.ROOT, request["notebook"])
    require(sha(path) == request["notebook_sha256"], "ORIGINAL_NOTEBOOK_CHANGED")
    committed = subprocess.check_output(["git", "show", head + ":" + request["notebook"]], cwd=runtime.ROOT)
    require(hashlib.sha256(committed).hexdigest() == sha(path), "COMMITTED_NOTEBOOK_CHANGED")
    return path


def authenticate(grant, request, exports, locator):
    """One source-bound continuation release, never a release per batch."""
    reader = Exports(exports)
    config = runtime.configuration()
    require(request["bindings"]["checkpoint"] == {"model": config["model"], "revision": config["revision"],
        "sha256": campaign.identity()["checkpoint_sha256"]}, "CONTINUATION_CHECKPOINT_CHANGED")
    require(campaign.load(request["execution_release"], reader=reader, collection=True) == grant, "ORIGINAL_GRANT_DRIFT")
    campaign.bind(grant, request, reader=reader)
    decision = reader("/issues/comments/" + str(DECISION_ID))
    require(decision["id"] == DECISION_ID and decision["user"]["login"] == authority.OWNER
        and decision["user"]["id"] == 246929698 and decision["author_association"] == "OWNER"
        and decision["issue_url"] == authority.API + "/issues/180" and type(decision["body"]) is str
        and hashlib.sha256(decision["body"].encode()).hexdigest() == DECISION_BODY_SHA256, "REAL_OWNER_CONTINUATION_DECISION_REQUIRED")
    value, comment = campaign.record(locator, RELEASE, reader)
    expected = {"campaign_sha256", "decision_body_sha256", "implementation_pr", "reviewed_head", "merged_sha",
        "script_sha256", "tools_sha256", "audit", "source_sha256", "notebook_sha256", "scope", "base_head_sha256", "start_ordinal"}
    require(set(value) == expected and value["scope"] == "OFFLINE_SERIAL_DEFERRED_RECONCILIATION"
        and value["campaign_sha256"] == digest(grant) and value["start_ordinal"] == 323
        and value["decision_body_sha256"] == hashlib.sha256(decision["body"].encode()).hexdigest()
        and value["source_sha256"] == digest(request["plan"]["runtime_source"])
        and value["notebook_sha256"] == request["notebook_sha256"]
        and value["script_sha256"] == sha(__file__) and value["tools_sha256"] == digest(tool_manifest()), "CONTINUATION_EXACT_RELEASE")
    require(comment["user"]["login"] in grant["review_logins"]
        and comment["issue_url"] == authority.API + "/issues/" + str(value["implementation_pr"]), "CONTINUATION_REVIEWER")
    pr = reader("/pulls/" + str(value["implementation_pr"]))
    require(pr["merged"] is True and pr["base"]["ref"] == "main" and pr["head"]["sha"] == value["reviewed_head"]
        and pr["merge_commit_sha"] == value["merged_sha"], "CONTINUATION_NOT_MERGED")
    audit, auditor = campaign.record(value["audit"], RELEASE + "_AUDIT", reader)
    require(auditor["user"]["login"] in grant["audit_logins"] and auditor["id"] != comment["id"]
        and auditor["issue_url"] == comment["issue_url"] and audit == {"reviewed_head": value["reviewed_head"],
            "script_sha256": value["script_sha256"], "tools_sha256": value["tools_sha256"],
            "status": "PASS", "independent": True}, "INDEPENDENT_CONTINUATION_AUDIT_REQUIRED")
    require_hash(value["base_head_sha256"])
    return value


def quick_bundle(archive, expected, plan):
    """CRC/hash every byte and check metadata/raw custody, defer vector replay.

    This deliberately does not claim independent numerical trace verification.
    The unchanged full runtime verifier is mandatory at final reconciliation.
    """
    members = runtime.verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        get = lambda name: runtime._strict_json_loads(bundle.read(name))
        require(get("checksums.json") == members, "STRICT_ARCHIVE_MANIFEST")
        result, cohort = get("run/summary.json"), get("run/cohort.json")
        require(get("run/plan.json") == plan and get("run/source.json") == plan["runtime_source"]
            and get("run/configuration.json") == runtime.configuration()
            and plan["science_sha256"] == digest(campaign.science()), "QUICK_PLAN_SOURCE_SCIENCE")
        rows = runtime.planning.validate_cohort(cohort, plan["cohort_sha256"])
        require(cohort["scope"] == "PRIVATE_TRAIN_METADATA" and len(rows) == 3763
            and result["schema"] == runtime.IDENTITY + "-result"
            and result["scope"] == cohort["scope"] and result["planned"] == 3763
            and result["series_id"] == plan["series_id"] == runtime.SERIES
            and result["run_id"] == plan["run_id"] and result["attempt_id"] == plan["attempt_id"]
            and result["plan_sha256"] == digest(plan) and result["source_sha256"] == digest(plan["runtime_source"])
            and result["status"] == "PASS" and result["failure"] is None
            and result["hnlo"] is None and result["hnlo_status"] == runtime.HNLO_STATUS
            and get("terminal.json") == {"status": "PASS", "error": None}
            and len(result["records"]) == 3763 and "run/stop.json" not in members, "QUICK_COMPLETE_RESULT_REQUIRED")
        for name in ("setup/setup-supervisor.json", "worker-supervisor.json"):
            process = get(name)
            require(process["status"] == "EXITED" and process["returncode"] == 0 and process["automatic_retry"] is False,
                "QUICK_SUPERVISED_EXIT")
        scheduled = set(plan["scheduled_ordinals"])
        for name in members:
            if name.startswith("run/samples/"):
                match = re.fullmatch(r"run/samples/([0-9]{6})/(started\.json|native_call\.json|call-reservation\.json|call-claim\.json|raw\.json|result\.json|grammar\.json|request\.json|native\.json|processors\.json|trace-verification\.json|trace-failure\.json|steps/([0-9]{3})\.(f32|forward\.json|masked\.json))", name)
                require(match is not None and int(match[1]) in scheduled
                    and (match[3] is None or int(match[3]) < 64), "QUICK_UNPLANNED_SAMPLE_MEMBER")
        for row, record in zip(rows, result["records"]):
            require(all(record[k] == v for k, v in row.items()) and record["hnlo"] is None
                and record["hnlo_status"] == runtime.HNLO_STATUS, "QUICK_RECORD_IDENTITY")
            prefix = f"run/samples/{row['ordinal']:06d}/"
            if row["ordinal"] not in scheduled:
                require(record["status"] == "NOT_ATTEMPTED" and record["label"] is None
                    and type(record["native_calls"]) is int and record["native_calls"] == 0
                    and type(record["attempts"]) is int and record["attempts"] == 0, "QUICK_UNPLANNED_CALL")
                continue
            require(record["status"] in ("SUCCESS", "INVALID") and type(record["native_calls"]) is int
                and record["native_calls"] == 1 and type(record["attempts"]) is int and record["attempts"] == 1,
                "QUICK_MISSING_OR_FAILED_SAMPLE")
            raw = get(prefix + "raw.json")
            label = runtime.parse_label(raw["response"])
            binding = runtime.trace_binding(plan["runtime_source"], plan, row, raw["binding"]["tokenizer_sha256"], digest(plan))
            require(record["raw_sha256"] == members[prefix + "raw.json"] and raw["binding"] == binding
                and raw["evidence_kind"] == "NATIVE" and raw["capture_origin"] == "forward_before_processors"
                and raw["hnlo"] is None and raw["hnlo_status"] == runtime.HNLO_STATUS
                and get(prefix + "started.json") == {"row": row, "plan_sha256": digest(plan)}
                and get(prefix + "native_call.json")["binding"] == binding
                and record["label"] == label and record["status"] == ("SUCCESS" if label else "INVALID"), "QUICK_RAW_BEFORE_PARSE")
            ids, width = raw["generated_ids"], raw["logit_width"]
            from safeshift.internvl_grammar import PROCESSOR
            require(type(width) is int and 0 < width <= 200000 and 1 <= len(ids) <= 64
                and len(ids) == len(raw["raw_vector_hashes"]) == len(raw["masked_vector_hashes"])
                and raw["actual_logits_processors"] == [PROCESSOR] and raw["policy"] == runtime.POLICY, "QUICK_VECTOR_SHAPE")
            for index in range(len(ids)):
                stem = prefix + f"steps/{index:03d}"
                require(members.get(stem + ".f32") == raw["raw_vector_hashes"][index]
                    and members.get(stem + ".masked.json") == raw["masked_vector_hashes"][index]
                    and stem + ".forward.json" in members and bundle.getinfo(stem + ".f32").file_size == width * 4,
                    "QUICK_RAW_VECTOR_CUSTODY")
                forward = get(stem + ".forward.json")
                require(forward["step"] == index and forward["raw_sha256"] == raw["raw_vector_hashes"][index]
                    and forward["vocab"] == width and forward["origin"] == "forward_before_processors"
                    and forward["encoding"] == "float32-little-endian" and forward["all_finite"] is True,
                    "QUICK_FORWARD_RECEIPT")
            if label:
                trace = get(prefix + "trace-verification.json")
                require(record["trace_verified"] is True and trace["status"] == "TRACE_CONSISTENT"
                    and trace["evidence_kind"] == "NATIVE" and trace["label"] == label and trace["binding"] == binding,
                    "QUICK_WORKER_TRACE_RECEIPT")
            else:
                require(prefix + "trace-failure.json" in members or prefix + "trace-verification.json" in members, "QUICK_INVALID_TRACE_RETAINED")
        require(result["counts"] == dict(Counter(r["status"] for r in result["records"]))
            and result["model_calls"] == len(scheduled) == len(plan["scheduled_ordinals"]), "QUICK_COUNTS")
    return {"status": "PASS", "archive_sha256": expected, "members": len(members) + 1,
        "model_calls": result["model_calls"], "counts": result["counts"], "scope": result["scope"], "scientific_qualified": False}


def inspect_baseline(ledger, archive):
    """Read only: never acquire a mutating lock or change a production file."""
    before = {p.name: sha(p) for p in ledger.root.glob("*.json")}
    events = ledger.events()
    require(len(events) == 35 and ledger.open_intent() == events[-1], "EXACT_INTENT35_REQUIRED")
    intent, archive = events[-1], Path(archive)
    source_check(intent["request"])
    expected = read(str(archive) + ".sha256.json")["sha256"]
    require(sha(archive) == expected, "LOCAL_ZIP_SHA256")
    result = quick_bundle(archive, expected, intent["request"]["plan"])
    campaign.verify_native_custody(intent["request"], archive, intent, ledger.grant)
    manual.verify_inputs_in_archive(archive, intent["request"])
    original_handoff(ledger, intent)
    budget = ledger.budget()
    require(before == {p.name: sha(p) for p in ledger.root.glob("*.json")} and ledger.events() == events, "BASELINE_CHANGED_DURING_READ")
    return {"status": "READ_ONLY_LOCAL_CUSTODY_VERIFIED", "production_collection": "NOT_APPENDED",
        "provider": "NOT_QUERIED", "numeric_vector_replay": "DEFERRED_TO_FINAL", "journal_events": len(events),
        "journal_head_sha256": digest(intent), "historical_file_hashes": before, "verification": result,
        "budget": budget, "attempt11_ordinals": intent["request"]["plan"]["scheduled_ordinals"],
        "remaining_after_validated_attempt11": 3240, "scientific_qualified": False}


def verify_local(intent, grant, archive, evidence, *, full=True):
    """Bounded full local validation. PASS is provisional, never provider proof."""
    archive = Path(archive)
    request = intent["request"]
    expected = read(str(archive) + ".sha256.json")["sha256"]
    require(sha(archive) == expected, "LOCAL_ZIP_SHA256")
    require(archive.stat().st_size <= grant["caps"]["archive_bytes"], "ARCHIVE_CAP")
    result = (runtime.verify_bundle if full else quick_bundle)(archive, expected, request["plan"])
    require(result["status"] == "PASS" and result["scope"] == "PRIVATE_TRAIN_METADATA", "LOCAL_RUN_FAILED")
    campaign.verify_native_custody(request, archive, intent, grant)
    manual.verify_inputs_in_archive(archive, request)
    if full:
        ancestor = runtime.sealed_history(archive, expected, request["plan"])
    else:
        with zipfile.ZipFile(archive) as bundle:
            summary = runtime._strict_json_loads(bundle.read("run/summary.json"))
        p = request["plan"]
        ancestor = {"run_id": p["run_id"], "attempt_id": p["attempt_id"], "series_id": p["series_id"],
            "identity": p["identity"], "cohort_sha256": p["cohort_sha256"], "parent_history_sha256": p["history_sha256"],
            "action": p["action"], "repair": p["repair"], "evidence_sha256": expected,
            "records": [r for r in summary["records"] if r["status"] != "NOT_ATTEMPTED"]}
    manual.verify_scheduled_completion(request, intent, result, ancestor)
    require(ancestor["parent_history_sha256"] == digest(request["bindings"]["runtime"]["execution_request"]["history"]),
        "LOCAL_PARENT_LINEAGE")
    require(type(evidence) is dict and set(evidence) == {"job", "version", "kernel_id", "state", "archive_sha256",
        "no_other_job_or_version", "no_api_submission", "owner_downloaded_unix"}, "OWNER_LOCAL_RECEIPT_FIELDS")
    require(evidence["job"] == request["job"] and type(evidence["version"]) is int and evidence["version"] == 1
        and type(evidence["kernel_id"]) is int and evidence["kernel_id"] > 0 and evidence["state"] == "COMPLETE"
        and evidence["archive_sha256"] == expected and evidence["no_other_job_or_version"] is True
        and evidence["no_api_submission"] is True and type(evidence["owner_downloaded_unix"]) is int
        and intent["unix"] <= evidence["owner_downloaded_unix"] <= time.time(), "OWNER_COMPLETION_EVIDENCE_REQUIRED")
    return {"status": "OFFLINE_VERIFIED_PROVISIONAL", "verification": result, "history": ancestor,
        "sha256": expected, "sidecar_sha256": sha(str(archive) + ".sha256.json"), "owner_receipt": evidence,
        "formal_collection": "PENDING_CAMPAIGN_RECONCILIATION", "scientific_qualified": False}


class Continuation:
    def __init__(self, root, ledger):
        self.root, self.ledger = _private(root), ledger
        self.registration = read(safe(self.root, "registration.json"))
        self.mirror = _private(safe(runtime.ROOT, self.registration["mirror"]))
        require(self.root.resolve() != self.mirror.resolve() and not self.root.resolve().is_relative_to(self.mirror.resolve())
            and not self.mirror.resolve().is_relative_to(self.root.resolve()), "INDEPENDENT_CONTINUATION_MIRROR")
        require((self.root / "registration.json").read_bytes() == (self.mirror / "registration.json").read_bytes(), "CONTINUATION_REGISTRATION_DIVERGED")
        require(self.registration["host"] == campaign.host_identity() and self.registration["root"] == _relative(self.root)
            and self.registration["ledger"] == _relative(ledger.root), "CONTINUATION_SINGLE_OWNER_MACHINE")
        require(self.registration["schema"] == SCHEMA and self.registration["campaign_sha256"] == digest(ledger.grant), "CONTINUATION_GRANT_DRIFT")
        require(authenticate(ledger.grant, self.registration["initial_intent"]["request"], self.registration["github_exports"],
            self.registration["release_locator"]) == self.registration["release"], "REGISTERED_RELEASE_DRIFT")
        require(baseline_owner(ledger.grant, self.registration["initial_intent"], self.registration["github_exports"])
            == self.registration["attempt11_owner"], "BASELINE_OWNER_FACTS_DRIFT")
        self.events()

    @classmethod
    def initialize(cls, root, mirror, ledger, exports, release_locator):
        root, mirror = _private(root), _private(mirror)
        require(root.resolve() != mirror.resolve() and not root.resolve().is_relative_to(mirror.resolve())
            and not mirror.resolve().is_relative_to(root.resolve()), "INDEPENDENT_CONTINUATION_MIRROR")
        # Route migration is deliberately exact. There is no synthetic close of
        # INTENT35 and no assumption that journals36/37 were ever written.
        with lock(ledger.root):
            events = ledger.events()
            require(len(events) == 35 and events[-1]["kind"] == "INTENT" and ledger.open_intent() == events[-1], "MIGRATION_REQUIRES_ORIGINAL_INTENT35")
            intent = events[-1]
            handoff = original_handoff(ledger, intent)
            require(intent["request"]["plan"]["scheduled_ordinals"] == list(range(323, 523)), "MIGRATION_ATTEMPT11_RANGE")
            source_check(intent["request"])
            release = authenticate(ledger.grant, intent["request"], exports, release_locator)
            owner = baseline_owner(ledger.grant, intent, exports)
            require(release["base_head_sha256"] == digest(intent), "MIGRATION_REVIEWED_BASE_HEAD")
            history, custody = ledger.histories()
            records = [r for h in history for r in h["records"]]
            require([r["ordinal"] for r in records] == list(range(323))
                and all(r["status"] in ("SUCCESS", "INVALID") for r in records), "MIGRATION_ORIGINAL_PREFIX_INCOMPLETE")
            measured = [e for e in events if e["kind"] == "MEASURED"
                and e["source_sha256"] == digest(intent["request"]["plan"]["runtime_source"])][-1]
            require(not root.exists() and not mirror.exists(), "NO_CONTINUATION_REINITIALIZATION")
            require(not root.resolve().is_relative_to(ledger.root.resolve()) and not mirror.resolve().is_relative_to(ledger.root.resolve())
                and not root.resolve().is_relative_to(ledger.mirror.resolve()) and not mirror.resolve().is_relative_to(ledger.mirror.resolve()), "SEPARATE_OFFLINE_CUSTODY")
            registration = {"schema": SCHEMA, "campaign_sha256": digest(ledger.grant), "host": campaign.host_identity(),
                "root": _relative(root), "mirror": _relative(mirror), "ledger": _relative(ledger.root),
                "base_count": len(events), "base_head": digest(intent), "base_files": {p.name: sha(p)
                    for p in ledger.root.glob("*.json")}, "base_history": history,
                "base_custody": [{**c, "path": _relative(c["path"])} for c in custody],
                "budget": ledger.budget(), "measured": measured, "initial_intent": intent,
                "release_locator": release_locator, "release": release, "github_exports": exports}
            registration["initial_handoff"] = handoff
            registration["attempt11_owner"] = owner
            require(ledger.events() == events and original_handoff(ledger, intent) == handoff, "MIGRATION_LOCAL_STATE_CHANGED")
            _pair(root, mirror, "registration.json", registration)
            # This new truthful event keeps legacy open_intent() BLOCKED for the
            # entire route, and makes a restart/admission loss detectable.
            ledger.append(ADMISSION, continuation_registration_sha256=digest(registration),
                continuation=_relative(root), release_locator=release_locator, base_head_sha256=digest(intent))
            return cls(root, ledger)

    def events(self):
        ledger_events = self.ledger.events()
        require(original_handoff(self.ledger, self.registration["initial_intent"]) == self.registration["initial_handoff"], "ORIGINAL_HANDOFF_CHANGED")
        n = self.registration["base_count"]
        require(len(ledger_events) in (n + 1, n + 2) and digest(ledger_events[n-1]) == self.registration["base_head"], "PRODUCTION_LEDGER_CHANGED_STOP")
        for name, expected in self.registration["base_files"].items():
            require(sha(self.ledger.root / name) == expected == sha(self.ledger.mirror / name), "HISTORICAL_BYTES_CHANGED")
        admission = ledger_events[n]
        require(admission["kind"] == ADMISSION and admission["continuation_registration_sha256"] == digest(self.registration)
            and admission["continuation"] == _relative(self.root), "CONTINUATION_ADMISSION_LOST")
        if len(ledger_events) == n + 2:
            require(ledger_events[-1]["kind"] == RECONCILED, "UNEXPECTED_PRODUCTION_APPEND")
        names = sorted(p.name for p in self.root.glob("event-*.json"))
        require(names == sorted(p.name for p in self.mirror.glob("event-*.json")), "CONTINUATION_PARTIAL_WRITE_STOP")
        result, previous = [], digest(self.registration)
        pending = True  # original Attempt11
        next_ordinal = 323
        for number, name in enumerate(names, 1):
            require(name == f"event-{number:06d}.json" and (self.root / name).read_bytes() == (self.mirror / name).read_bytes(), "CONTINUATION_GAP_OR_DIVERGENCE")
            row = read(safe(self.root, name))
            require(row["previous"] == previous and row["schema"] == SCHEMA, "CONTINUATION_CHAIN")
            require(row["kind"] in ("RESERVED_OFFLINE", "OFFLINE_VERIFIED_PROVISIONAL", "STOPPED"), "UNKNOWN_CONTINUATION_EVENT")
            if row["kind"] == "RESERVED_OFFLINE":
                require(not pending, "OVERLAPPING_OFFLINE_JOB")
                pending = True
            elif row["kind"] == "OFFLINE_VERIFIED_PROVISIONAL":
                require(pending and row["ordinals"] == list(range(next_ordinal, next_ordinal + len(row["ordinals"])))
                    and row["ordinals"], "OFFLINE_GAP_OR_DUPLICATE")
                next_ordinal += len(row["ordinals"])
                pending = False
            previous = digest(row)
            result.append(row)
        return result

    def append(self, kind, **values):
        events = self.events()
        row = {"schema": SCHEMA, "kind": kind, "unix": time.time(),
            "previous": digest(events[-1]) if events else digest(self.registration), **values}
        _pair(self.root, self.mirror, f"event-{len(events)+1:06d}.json", row)
        self.events()
        return row

    def _active(self, events):
        reserved = [e for e in events if e["kind"] == "RESERVED_OFFLINE"]
        intent = reserved[-1]["intent"] if reserved else self.registration["initial_intent"]
        done = [e for e in events if e["kind"] == "OFFLINE_VERIFIED_PROVISIONAL"]
        return None if done and done[-1]["intent_sha256"] == digest(intent) else intent

    def state(self, *, verify_custody=True):
        events = self.events()
        require(not any(e["kind"] == "STOPPED" for e in events), "CAMPAIGN_STOPPED_READ_ONLY_RECONCILIATION")
        history = deepcopy(self.registration["base_history"])
        custody = deepcopy(self.registration["base_custody"])
        intents = [self.registration["initial_intent"]]
        budget = deepcopy(self.registration["budget"])
        caps = budget["caps"]
        for row in events:
            if row["kind"] == "RESERVED_OFFLINE":
                intent = row["intent"]
                request = intent["request"]
                require(request["bindings"]["runtime"]["execution_request"]["history"] == history, "OFFLINE_RESERVATION_HISTORY_DRIFT")
                self._limits(request, budget)
                budget["jobs"] += 1
                budget["reserved_calls"] += intent["reserved_calls"]
                budget["reserved_gpu_seconds"] += intent["reserved_gpu_seconds"]
                require(intent["reserved_calls"] == request["limits"]["max_calls"]
                    and intent["reserved_gpu_seconds"] == request["limits"]["job_seconds"] * caps["physical_gpus"], "OFFLINE_RESERVATION_ACCOUNTING")
                intents.append(intent)
            elif row["kind"] == "OFFLINE_VERIFIED_PROVISIONAL":
                intent = intents[-1]
                require(row["intent_sha256"] == digest(intent) and row["ordinals"] == intent["request"]["plan"]["scheduled_ordinals"], "OFFLINE_EXACT_INTENT")
                receipt = row["receipt"]
                require(receipt["history"]["parent_history_sha256"] == digest(history), "OFFLINE_HISTORY_CHAIN")
                archive = safe(self.root, row["archive"])
                mirrored = safe(self.mirror, row["archive"])
                if verify_custody:
                    for p in (archive, mirrored):
                        require(sha(p) == receipt["sha256"] and sha(str(p) + ".sha256.json") == receipt["sidecar_sha256"], "OFFLINE_ARCHIVE_LOST_OR_CHANGED")
                history.append(receipt["history"])
                custody.append({"path": _relative(archive), "sha256": receipt["sha256"], "plan": intent["request"]["plan"]})
        if verify_custody:
            for item in self.registration["base_custody"]:
                require(sha(safe(runtime.ROOT, item["path"])) == item["sha256"], "ORIGINAL_ARCHIVE_CUSTODY_LOST")
        rows = [r for h in history for r in h["records"]]
        require([r["ordinal"] for r in rows] == list(range(len(rows)))
            and len(rows) <= 3763 and all(r["status"] in ("SUCCESS", "INVALID") for r in rows), "COMPLETE_CONTIGUOUS_HISTORY_REQUIRED")
        return {"events": events, "history": history, "custody": custody, "budget": budget,
            "active": self._active(events), "next_ordinal": len(rows), "counts": dict(Counter(r["status"] for r in rows)),
            "formal_status": "FINAL_EVENT_PRESENT_USE_OFFICIAL_REPORT" if len(self.ledger.events()) == self.registration["base_count"] + 2
                else "PENDING_CAMPAIGN_RECONCILIATION"}

    def forecast(self):
        state = self.state()
        remaining = 3763 - state["next_ordinal"]
        measured, budget = self.registration["measured"], state["budget"]
        batch = min(200, measured["safe_calls"])
        shards = [min(batch, remaining - start) for start in range(0, remaining, batch)]
        seconds = [min(budget["caps"]["job_seconds"], max(7200, campaign.required_job_seconds(measured, n))) for n in shards]
        required_gpu = sum(seconds)*budget["caps"]["physical_gpus"]
        fits = (budget["reserved_calls"] + remaining <= budget["caps"]["total_calls"]
            and budget["jobs"] + len(shards) <= budget["caps"]["total_jobs"]
            and budget["reserved_gpu_seconds"] + required_gpu <= budget["caps"]["total_gpu_seconds"])
        return {"status": "MODELED_CAPS_FIT" if fits else "BLOCKED_INSUFFICIENT_CAMPAIGN_CAPS", "remaining_images": remaining,
            "calls_per_shard": shards, "seconds_per_shard": seconds, "future_jobs": len(shards),
            "future_reserved_gpu_seconds": required_gpu, "projected_total_reserved_gpu_seconds": budget["reserved_gpu_seconds"] + required_gpu,
            "deadline_and_weekly_quota": "OWNER_MUST_CHECK_BEFORE_EACH_RUN", "population_worst_case_fit": "NOT_ESTABLISHED"}

    def _limits(self, request, budget):
        c, seconds = request["limits"]["max_calls"], request["limits"]["job_seconds"]
        caps, measured = budget["caps"], self.registration["measured"]
        require(type(c) is int and 1 <= c <= min(caps["job_calls"], measured["safe_calls"])
            and type(seconds) is int and campaign.required_job_seconds(measured, c) <= seconds <= caps["job_seconds"], "OFFLINE_MEASURED_SHARD_CAP")
        require(budget["jobs"] + 1 <= caps["total_jobs"] and budget["reserved_calls"] + c <= caps["total_calls"]
            and budget["reserved_gpu_seconds"] + seconds*caps["physical_gpus"] <= caps["total_gpu_seconds"], "OFFLINE_BUDGET_EXHAUSTED_NO_REFUND")

    def accept(self, archive, owner_receipt):
        with lock(self.ledger.root), lock(self.root):
            require(len(self.ledger.events()) == self.registration["base_count"] + 1, "ALREADY_FORMALLY_RECONCILED")
            state = self.state()
            intent = state["active"]
            require(intent is not None, "NO_ACTIVE_OFFLINE_INTENT")
            try:
                receipt = verify_local(intent, self.ledger.grant, archive, owner_receipt, full=False)
                if intent == self.registration["initial_intent"]:
                    baseline = self.registration["attempt11_owner"]
                    require(receipt["sha256"] == baseline["archive_sha256"]
                        and receipt["owner_receipt"]["kernel_id"] == baseline["kernel_id"], "BASELINE_OWNER_ARCHIVE_OR_KERNEL_DRIFT")
                used_kernels = {e["receipt"]["owner_receipt"]["kernel_id"] for e in state["events"]
                    if e["kind"] == "OFFLINE_VERIFIED_PROVISIONAL"}
                used_kernels.update(e["provider"].get("kernel_id") for e in self.ledger.events() if e["kind"] == "COLLECTED")
                require(receipt["owner_receipt"]["kernel_id"] not in used_kernels, "REUSED_PROVIDER_KERNEL")
                # Mirrors must be independent copies, not a second path to the
                # same file. Interrupted copies are retained and STOP the route.
                name = "artifacts/" + digest(intent) + "/" + Path(archive).name
                pending_bytes = sum(Path(source).stat().st_size for root in (self.root, self.mirror)
                    for source, target in ((archive, name), (str(archive) + ".sha256.json", name + ".sha256.json"))
                    if not safe(root, target).exists())
                require(all(shutil.disk_usage(root).free >= pending_bytes + 64*2**20 for root in (self.root, self.mirror)),
                    "LOCAL_DURABLE_COPY_SPACE_INSUFFICIENT")
                for root in (self.root, self.mirror):
                    _copy(archive, safe(root, name))
                    _copy(str(archive) + ".sha256.json", safe(root, name + ".sha256.json"))
                    require(sha(safe(root, name)) == receipt["sha256"]
                        and sha(safe(root, name + ".sha256.json")) == receipt["sidecar_sha256"], "COPY_CHANGED_SINCE_VERIFICATION")
                return self.append("OFFLINE_VERIFIED_PROVISIONAL", intent_sha256=digest(intent), archive=name,
                    ordinals=intent["request"]["plan"]["scheduled_ordinals"], receipt=receipt)
            except Exception as error:
                # Failures are durable; there is no repeat/overwrite/retry path.
                forensic = {"original_download_name": Path(archive).name, "status": "ORIGINALS_RETAINED"}
                try:
                    for source, limit in ((Path(archive), self.ledger.grant["caps"]["archive_bytes"]),
                            (Path(str(archive) + ".sha256.json"), 64*2**20)):
                        if source.is_file() and source.stat().st_size <= limit:
                            name = "quarantine/" + digest(intent) + "/" + source.name
                            for root in (self.root, self.mirror):
                                _copy(source, safe(root, name))
                            forensic[source.name] = {"path": name, "observed_sha256": sha(source)}
                    forensic["status"] = "BOUNDED_EXISTING_BYTES_QUARANTINED_NO_VERIFICATION_CLAIM"
                except Exception as copy_error:
                    # Keep any successful/partial copies and the original
                    # downloads. A disk error must never authorize another job.
                    forensic.update(status="PARTIAL_QUARANTINE_ORIGINALS_RETAINED", error_type=type(copy_error).__name__)
                reason = str(error)
                reason = reason if isinstance(error, ValueError) and re.fullmatch(r"[A-Z0-9_:]{1,160}", reason) else type(error).__name__
                self.append("STOPPED", intent_sha256=digest(intent), error_type=type(error).__name__,
                    reason=reason, forensic=forensic, automatic_retry=False)
                raise

    def stage(self, *, calls=200, seconds=7200):
        with lock(self.ledger.root), lock(self.root):
            require(len(self.ledger.events()) == self.registration["base_count"] + 1, "ALREADY_FORMALLY_RECONCILED")
            state = self.state()
            require(state["active"] is None and state["next_ordinal"] < 3763, "ACTIVE_JOB_OR_ALL_IMAGES_DONE")
            require(self.forecast()["status"] == "MODELED_CAPS_FIT", "FULL_REMAINDER_EXCEEDS_CAMPAIGN_CAPS")
            old = self.registration["initial_intent"]["request"]
            notebook = source_check(old)
            authenticate(self.ledger.grant, old, self.registration["github_exports"], self.registration["release_locator"])
            campaign.validate(self.ledger.grant)
            number = state["budget"]["jobs"] + 1
            calls = min(calls, 3763 - state["next_ordinal"])
            name = self.ledger.grant["campaign_id"] + "-" + str(number)
            execution = deepcopy(old["bindings"]["runtime"]["execution_request"])
            plan = campaign.plan(execution["cohort"], state["history"], action="resume", run_id=name,
                attempt_id="attempt-" + str(number), max_calls=calls, max_seconds=seconds)
            require(plan["scheduled_ordinals"] == list(range(state["next_ordinal"], state["next_ordinal"] + calls)), "NO_SKIP_OR_REPLAY")
            request = deepcopy(old)
            request.update(handoff_id=name, job="nguynanhtn/safeshift-train3763-" + name, plan=plan,
                plan_sha256=digest(plan), limits={"max_calls": calls, "job_seconds": seconds, "monitor_seconds": 900})
            capsule = "nguynanhtn/safeshift-capsule-ivl35-attempt" + str(number) + "/1"
            binding = request["bindings"]["runtime"]
            old_capsule = binding["execution_input"]["ref"]
            binding["execution_input"]["ref"] = capsule
            request["bindings"]["dataset"]["dataset_sources"] = [capsule if x == old_capsule else x
                for x in request["bindings"]["dataset"]["dataset_sources"]]
            execution.update(plan=plan, history=state["history"], history_archives=[{"archive": "custody/" + x["sha256"] + ".zip",
                "sha256": x["sha256"], "plan": {"run_id": x["plan"]["run_id"], "attempt_id": x["plan"]["attempt_id"]}}
                for x in state["custody"]])
            binding["execution_request"] = execution
            binding["local_history"] = []  # Campaign worker uses sole-operator custody, not reupload.
            request["bindings"]["dataset"]["execution_request_sha256"] = digest(execution)
            campaign.bind(self.ledger.grant, request, reader=Exports(self.registration["github_exports"]))
            self._limits(request, state["budget"])
            require(time.time() + seconds + 120 < self.ledger.grant["expires_unix"], "CAMPAIGN_DEADLINE")
            intent = {"kind": "INTENT", "campaign_sha256": digest(self.ledger.grant), "previous": digest(state["events"][-1]),
                "unix": time.time(), "request": request, "reserved_calls": calls,
                "reserved_gpu_seconds": seconds*state["budget"]["caps"]["physical_gpus"],
                "o5_extension_sha256": digest(state["budget"]["extension"])}
            # Reserve BEFORE writing anything the Owner could upload. On crash,
            # active intent prevents another reservation; export may be resumed.
            self.append("RESERVED_OFFLINE", intent=intent)
            return self.export_active()

    def export_active(self):
        state = self.state()
        intent = state["active"]
        require(intent is not None, "NO_ACTIVE_INTENT")
        request = intent["request"]
        notebook = source_check(request)
        folder = "handoffs/" + request["handoff_id"]
        files = {folder + "/capsule/safeshift_train3763_execution.json": json_bytes({"request": request, "campaign_intent": intent}),
            folder + "/notebook.ipynb": notebook.read_bytes(), folder + "/owner-steps.json": json_bytes({
                "status": "OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED", "job": request["job"],
                "capsule": request["bindings"]["runtime"]["execution_input"]["ref"], "inputs": operator.input_sources(request),
                "calls": request["limits"]["max_calls"], "ordinals": request["plan"]["scheduled_ordinals"],
                "notebook_sha256": request["notebook_sha256"], "package_sha256": digest({"request": request, "campaign_intent": intent}),
                "steps": ["Upload ONLY the capsule JSON as the prescribed NEW PRIVATE Dataset slug/version1; import the unchanged notebook as the exact prescribed job slug/version1, without running.",
                    "Attach the five exact Input versions; check Private / Python / Internet On / T4 x2 and campaign quota/time limits.",
                    "Save & Run All ONCE; after real terminal completion, download original ZIP + sidecar and save job/version/kernel completion evidence locally."]})}
        for root in (self.root, self.mirror):
            for name, payload in files.items():
                path = safe(root, name)
                if path.exists():
                    require(path.read_bytes() == payload, "PARTIAL_OR_CHANGED_HANDOFF_STOP")
                else:
                    write_bytes(path, payload)
                    campaign._sync_directory(path.parent)
        return {"status": "OFFLINE_PREPARED_NOT_UPLOADED_NOT_SUBMITTED", "directory": _relative(self.root / folder)}

    def manifest(self):
        state = self.state()
        require(state["active"] is None and state["next_ordinal"] == 3763, "FULL_TRAIN_NOT_YET_COMPLETE")
        attempts, intent = [], self.registration["initial_intent"]
        for row in state["events"]:
            if row["kind"] == "RESERVED_OFFLINE":
                intent = row["intent"]
            elif row["kind"] == "OFFLINE_VERIFIED_PROVISIONAL":
                attempts.append({"intent": intent, "archive": _relative(self.root / row["archive"]), "receipt": row["receipt"],
                    "local_verified_unix": row["unix"]})
        base = self.ledger.events()[:self.registration["base_count"]]
        historical = []
        for intent in (e for e in base if e["kind"] == "INTENT" and e != self.registration["initial_intent"]):
            terminal = [e for e in base if e["kind"] in ("COLLECTED", "ABORTED_PRE_SUBMIT") and e["intent_sha256"] == digest(intent)]
            require(len(terminal) == 1, "AMBIGUOUS_ORIGINAL_ATTEMPT")
            historical.append({"intent": intent, "outcome": terminal[0]})
        return {"schema": SCHEMA, "campaign_sha256": digest(self.ledger.grant), "registration_sha256": digest(self.registration),
            "offline_head": digest(state["events"][-1]), "attempts": attempts, "base_custody": state["custody"][:len(self.registration["base_history"])],
            "historical_attempts": historical,
            "ordinals": list(range(3763)), "counts": state["counts"], "budget": state["budget"],
            "scientific_selection": "PENDING", "scientific_qualified": False}

    def validate_reconciliation(self, manifest, exports, final_locator, admission_locator):
        """Read-only validation shared by final admission and official readers."""
        reader = Exports(exports)
        authenticate(self.ledger.grant, self.registration["initial_intent"]["request"], exports, self.registration["release_locator"])
        value, comment = campaign.record(final_locator, FINAL, reader)
        require(comment["user"]["login"] == authority.OWNER and comment["user"]["id"] == 246929698
            and comment["issue_url"] == authority.API + "/issues/180", "AUTHENTIC_AGGREGATE_OWNER_RECORD")
        require(set(value) == {"manifest_sha256", "report", "status"}
            and value["manifest_sha256"] == digest(manifest) and value["status"] == "APPROVED_FOR_AGGREGATE_ADMISSION", "EXACT_AGGREGATE_APPROVAL")
        report = value["report"]
        require(report["manifest_sha256"] == digest(manifest) and report["status"] == "ALL_ORIGINALS_VERIFIED"
            and report["budget"] == manifest["budget"] and report["billing_gpu_seconds"] == "NOT_OBSERVED"
            and report["tool_sha256"] == sha(Path(__file__).with_name("owner_verify_train3763_continuation.py"))
            and len(report["attempts"]) == len(manifest["attempts"])
            and len(report["historical"]) == len(manifest["base_custody"]), "EVERY_PROVIDER_ORIGINAL_REQUIRED")
        aborted = [h for h in manifest["historical_attempts"] if h["outcome"]["kind"] == "ABORTED_PRE_SUBMIT"]
        require(report["aborted"] == [{"intent_sha256": digest(h["intent"]), "job": h["intent"]["request"]["job"],
            "original_abort_sha256": digest(h["outcome"]), "provider_absent_at_final": True,
            "reserved_calls": h["intent"]["reserved_calls"], "reserved_gpu_seconds": h["intent"]["reserved_gpu_seconds"]}
            for h in aborted], "ORIGINAL_ABORTED_RESERVATIONS_RETAINED")
        for item, proof in zip(manifest["attempts"], report["attempts"]):
            intent, receipt = item["intent"], item["receipt"]
            actual = verify_local(intent, self.ledger.grant, safe(runtime.ROOT, item["archive"]), receipt["owner_receipt"])
            require(actual == receipt and proof["intent_sha256"] == digest(intent)
                and proof["archive_sha256"] == receipt["sha256"] and proof["provider"]["job_id"] == intent["request"]["job"]
                and proof["provider"]["kernel_id"] == receipt["owner_receipt"]["kernel_id"]
                and proof["provider"]["state"] == "COMPLETE" and proof["provider"]["version"] == 1
                and proof["input_bytes_verified"] is True and proof["provider_copy_verified"] is True, "AGGREGATE_ATTEMPT_MISMATCH")
            provider_proof(proof, intent, safe(runtime.ROOT, item["archive"]), job=intent["request"]["job"],
                kernel_id=receipt["owner_receipt"]["kernel_id"])
            require(proof["resources"] == archive_resources(safe(runtime.ROOT, item["archive"]), intent), "FINAL_RESOURCE_PROOF_DRIFT")
        for item, proof in zip(manifest["base_custody"], report["historical"]):
            require(proof["archive_sha256"] == item["sha256"] and proof["provider_reverified"] is True
                and runtime.sealed_history(safe(runtime.ROOT, item["path"]), item["sha256"], item["plan"])
                    in self.registration["base_history"], "ORIGINAL_HISTORY_RECONCILIATION")
            base = self.ledger.events()[:self.registration["base_count"]]
            collected = next(e for e in base if e["kind"] == "COLLECTED" and e["sha256"] == item["sha256"])
            old_intent = next(e for e in base if e["kind"] == "INTENT" and digest(e) == collected["intent_sha256"])
            provider_proof(proof, old_intent, safe(runtime.ROOT, item["path"]), job=collected["provider"]["job_id"],
                kernel_id=collected["provider"].get("kernel_id"), state=collected["provider"]["state"])
            require(proof["resources"] == archive_resources(safe(runtime.ROOT, item["path"]), old_intent), "FINAL_RESOURCE_PROOF_DRIFT")
        admission, reviewer = campaign.record(admission_locator, FINAL + "_ADMISSION", reader)
        require(reviewer["user"]["login"] in self.ledger.grant["review_logins"] and reviewer["id"] != comment["id"]
            and admission == {"manifest_sha256": digest(manifest), "owner": final_locator,
                "report_sha256": digest(report), "status": "RELEASED_FOR_AGGREGATE_ADMISSION"}, "ONE_AGGREGATE_REVIEWER_RELEASE_REQUIRED")
        return report

    def official_report(self):
        return result_tools().official_report(self)

    def reconcile(self, exports, final_locator, admission_locator):
        """One aggregate approval; every attempt still has genuine provider proof.

        The Owner runs owner_verify_train3763_continuation.py online, posts its
        exact report under FINAL, and exports the authenticated comment. No
        verdict is accepted without that report binding every original proof.
        """
        with lock(self.ledger.root), lock(self.root):
            require(len(self.ledger.events()) == self.registration["base_count"] + 1, "NO_DUPLICATE_FINAL_APPEND")
            manifest = self.manifest()
            report = self.validate_reconciliation(manifest, exports, final_locator, admission_locator)
            # Preserve original INTENT35 forever. Old tools still see it open and
            # cannot forget these separately accounted reservations. This event
            # is the formal new-route record, never invented legacy COLLECTED,
            # SUBMITTED or MEASURED. Ordered attempts retain actual event times.
            row = self.ledger.append(RECONCILED, manifest=manifest, report=report, owner=final_locator,
                admission=admission_locator, github_exports=exports,
                status="FORMALLY_RECONCILED_NEW_ROUTE", counts=manifest["counts"],
                scientific_selection="PENDING", scientific_qualified=False)
            self.ledger.events()  # require both durable copies before reporting success
            return row


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--approved-repo", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--directory", type=Path, required=True)
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--mirror", type=Path, required=True)
    init.add_argument("--github-exports", type=Path, required=True)
    init.add_argument("--release-locator", type=Path, required=True)
    accept = sub.add_parser("accept")
    accept.add_argument("--archive", type=Path, required=True)
    accept.add_argument("--owner-receipt", type=Path, required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--calls", type=int, default=200)
    stage.add_argument("--seconds", type=int, default=7200)
    sub.add_parser("export-active")
    sub.add_parser("status")
    official = sub.add_parser("official-report")
    official.add_argument("--output", type=Path)
    sub.add_parser("forecast")
    inspect = sub.add_parser("inspect-baseline")
    inspect.add_argument("--archive", type=Path, required=True)
    merge = sub.add_parser("merge-exports")
    merge.add_argument("--base", type=Path, required=True)
    merge.add_argument("--comment", type=Path, action="append", required=True)
    merge.add_argument("--output", type=Path, required=True)
    manifest = sub.add_parser("manifest")
    manifest.add_argument("--output", type=Path, required=True)
    final = sub.add_parser("reconcile")
    final.add_argument("--github-exports", type=Path, required=True)
    final.add_argument("--final-locator", type=Path, required=True)
    final.add_argument("--admission-locator", type=Path, required=True)
    args = p.parse_args(argv)
    require(args.approved_repo.resolve() == runtime.ROOT.resolve(), "IMPORT_ORIGINAL_APPROVED_REPO")
    ledger = campaign.Ledger(args.ledger)
    if args.command == "merge-exports":
        value = merge_exports(read(args.base), [read(path) for path in args.comment])
        write(_private(args.output), value)
        result = {"status": "MERGED_OWNER_EXPORTS_OFFLINE", "endpoints": len(value)}
    elif args.command == "inspect-baseline":
        result = inspect_baseline(ledger, args.archive)
    elif args.command == "init":
        route = Continuation.initialize(args.directory, args.mirror, ledger, read(args.github_exports), read(args.release_locator))
        result = {"status": "ADMITTED_PENDING_ATTEMPT11_LOCAL_VERIFICATION", "production_events": len(ledger.events())}
    else:
        route = Continuation(args.directory, ledger)
        if args.command == "accept":
            result = route.accept(args.archive, read(args.owner_receipt))
        elif args.command == "stage":
            result = route.stage(calls=args.calls, seconds=args.seconds)
        elif args.command == "export-active":
            result = route.export_active()
        elif args.command == "manifest":
            result = route.manifest()
            write(_private(args.output), result)
        elif args.command == "reconcile":
            result = route.reconcile(read(args.github_exports), read(args.final_locator), read(args.admission_locator))
        elif args.command == "official-report":
            result = route.official_report()
            if args.output is not None:
                checksum = write(_private(args.output), result)
                write(_private(str(args.output) + ".sha256.json"), {"schema": result["schema"], "sha256": checksum,
                    "certificate": result["certificate"]})
        elif args.command == "forecast":
            result = route.forecast()
        else:
            state = route.state()
            result = {k: state[k] for k in ("next_ordinal", "counts", "budget", "formal_status")}
            result["active_job"] = state["active"]["request"]["job"] if state["active"] else None
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
