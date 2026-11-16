"""V3 recovery evidence; no credential, model, provider mutation or budget refund.

Old tickets and mirrored journal heads are carried into a newly reviewed release.
Only proven pre-native failures/expired unpublished tickets may use this route.
Unknown, native claims, torn history and partial archives require reconciliation.
"""
from copy import deepcopy
import json
import hashlib
import math
import time

from safeshift.candidates.source import require
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_release as a, minicpm_ui as ui

SCHEMA = "safeshift-minicpm-recovery-snapshot-v3"
PROJECT_GPU_SECONDS = 72000
CAMPAIGNS = ("mcpm4-train3763", "mcpm4-train3763-v2", "mcpm4-train3763-v3")
EVENT_PREFIX = "SAFESHIFT_MINICPM_LIVE_V3 "
AMENDMENT = "SAFESHIFT_MINICPM_PROJECT_BUDGET_AMENDMENT_V1"


def mounted_inputs(value):
    """Exact five nested mount roots, not recursive discovery or path guessing."""
    ui.validate(value)
    table = {}
    for kind, refs in value["input_sources"].items():
        for ref in refs:
            owner, slug, version = ref.split("/")
            table[ref] = {"mount": ("notebooks/" if kind == "kernel_sources" else "datasets/") + owner + "/" + slug,
                          "version": int(version)}
    for name in ("master_dataset", "train_dataset"):
        row = value["request"]["original_inputs"][name]
        require(row["mount"] == table[row["ref"] + "/" + str(row["version"])]["mount"],
                "MINICPM_RECOVERY_NESTED_BINDING_REQUIRED")
    require(len(table) == 5, "MINICPM_RECOVERY_FIVE_INPUTS")
    return table


def validate_recovery(grant):
    r = grant["recovery"]
    require(type(r) is dict and set(r) == {"schema", "journals", "reserved", "prior_jobs", "directive",
        "budget_amendment"} and r["schema"] == SCHEMA, "MINICPM_RECOVERY_SNAPSHOT")
    require(grant["campaign_id"] == CAMPAIGNS[-1], "MINICPM_NO_FOURTH_CAMPAIGN")
    require(type(r["journals"]) is list and len(r["journals"]) == 3, "MINICPM_ALL_PRIOR_JOURNALS_REQUIRED")
    totals = {"calls": 0, "jobs": 0, "gpu_seconds": 0}
    seen, paths, jobs = set(), set(), []
    for campaign, journal in zip(CAMPAIGNS, r["journals"]):
        require(type(journal) is dict and set(journal) == {"campaign_id", "root", "mirror", "head_sha256",
            "grant_locator", "ticket", "job", "publication", "disposition", "evidence_sha256"}
            and journal["campaign_id"] == campaign, "MINICPM_COMPLETE_ORDERED_RECOVERY_LINEAGE")
        from safeshift.pilot.artifacts import relative
        for field in ("root", "mirror"):
            path = journal[field]
            relative(path)
            require(path.startswith("data/processed/") and path not in paths, "MINICPM_RECOVERY_DISTINCT_JOURNALS")
            paths.add(path)
        for field in ("head_sha256", "evidence_sha256"):
            require_hash(journal[field])
        envelope = journal["ticket"]
        require(type(envelope) is dict and set(envelope) == {"payload", "signature"}, "MINICPM_OLD_SIGNED_TICKET")
        a.verify_signature(grant["public_key"], envelope["payload"], envelope["signature"])
        t = envelope["payload"]
        require(t["schema"] == a.TICKET and t["number"] == 1 and digest(envelope) not in seen,
                "MINICPM_RECOVERY_TICKET_REPLAY")
        seen.add(digest(envelope))
        before, after = t["reserved_before"], t["reserved_after"]
        size = t["sizing"]
        require(before == {"calls": 0, "jobs": 0, "gpu_seconds": 0}
            and all(type(size[k]) is int and size[k] > 0 for k in ("calls", "seconds"))
            and after == {"calls": size["calls"], "jobs": 1, "gpu_seconds": 2 * size["seconds"]},
                "MINICPM_RECOVERY_KEEP_FULL_RESERVATIONS")
        for field in totals:
            totals[field] += after[field]
        job = "nguynanhtn/safeshift-minicpm-" + campaign + "-1"
        require(journal["job"] == job and journal["disposition"] in ("FAILED_PRE_NATIVE", "EXPIRED_UNPUBLISHED"),
                "MINICPM_RECOVERY_UNKNOWN_OR_NATIVE_STOP")
        require(journal["publication"] in ("RESERVED", "PUBLISH_INTENT", "PUBLISHED")
            and (journal["disposition"] != "EXPIRED_UNPUBLISHED" or journal["publication"] == "RESERVED"),
                "MINICPM_PUBLISHED_JOB_ABSENCE_IS_AMBIGUOUS")
        jobs.append(job)
    require(r["reserved"] == totals, "MINICPM_RECOVERY_NO_REFUND_OR_RESET")
    require(type(r["prior_jobs"]) is list and len(r["prior_jobs"]) == 3, "MINICPM_RECOVERY_PROVIDER_HISTORY")
    for journal, proof, job in zip(r["journals"], r["prior_jobs"], jobs):
        require(set(proof) == {"job", "version", "state", "evidence_sha256"} and proof["job"] == job
            and type(proof["version"]) is int and proof["version"] == 1
            and proof["evidence_sha256"] == journal["evidence_sha256"]
            and proof["state"] in (("ERROR", "CANCELLED", "COMPLETE") if journal["disposition"] == "FAILED_PRE_NATIVE"
                                  else ("ABSENT_EXPIRED",)), "MINICPM_RECOVERY_TERMINAL_PROOF")
    for locator in [r["directive"], *[j["grant_locator"] for j in r["journals"]]]:
        require(type(locator) is dict and set(locator) == {"comment_id", "body_sha256"}
            and type(locator["comment_id"]) is int and locator["comment_id"] > 0, "MINICPM_RECOVERY_AUTHENTIC_LOCATOR")
        require_hash(locator["body_sha256"])
    require(r["directive"]["comment_id"] == 6914854993, "MINICPM_EXACT_OWNER_SUBMIT_DIRECTIVE")
    cap = grant["caps"]["total_gpu_seconds"]
    require(r["budget_amendment"] is not None or cap <= PROJECT_GPU_SECONDS,
            "MINICPM_AUTHENTIC_PROJECT_CAP_AMENDMENT_REQUIRED")
    require(all(totals[k] < grant["caps"]["total_" + k] for k in totals),
            "MINICPM_PROJECT_BUDGET_EXHAUSTED_NO_REFUND")
    # Bind both TRAIN/master mount strings now. Capsule/Python/checkpoint roots
    # are verified before admission by verify_mounted_inputs.
    for row in grant["scope"]["original_inputs"].values():
        if type(row) is dict and "ref" in row:
            require(row["mount"] == "datasets/" + row["ref"], "MINICPM_RECOVERY_NESTED_BINDING_REQUIRED")
    return r


def authenticate_recovery(grant, reader):
    """Fresh authentic historical records; offline exports never confer rights."""
    r = validate_recovery(grant)
    def fetch(loc):
        row = reader("/issues/comments/" + str(loc["comment_id"]))
        require(row["id"] == loc["comment_id"] and row["user"] == {**row["user"], "login": a.OWNER, "id": a.OWNER_ID}
            and row["issue_url"] == a.API + "/issues/198"
            and hashlib.sha256(row["body"].encode()).hexdigest() == loc["body_sha256"],
                "MINICPM_AUTHENTIC_RECOVERY_RECORD")
        return row
    fetch(r["directive"])
    for journal in r["journals"]:
        old = a.record(fetch(journal["grant_locator"])["body"], a.MARKER)
        require(old["schema"] == a.SCHEMA and old["authorization"] == "OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY"
            and old["campaign_id"] == journal["campaign_id"] and old["public_key"] == grant["public_key"]
            and old["merged_sha"] == "507e9817b91054fa7af324c6a915c35d56b5acf1"
            and old["scope"]["source_sha256"] == "7c76a2c331aef2383e9d8f2fe236f0c4302cabb587a759925b5d3dadae206b5c"
            and digest(old) == journal["ticket"]["payload"]["grant_sha256"], "MINICPM_HISTORICAL_GRANT_TICKET_BINDING")
        previous = deepcopy(old["scope"])
        current = deepcopy(grant["scope"])
        # Only source provenance and mount layout may change. No scientific
        # selection, config/parser/model/data/checkpoint/precision drift.
        for s in (previous, current):
            s.pop("source_sha256")
            s["identity"].pop("implementation_sha256")
            for name in ("master_dataset", "train_dataset"):
                s["original_inputs"][name].pop("mount")
        require(previous == current, "MINICPM_RECOVERY_SCIENCE_DRIFT")
    if r["budget_amendment"] is not None:
        amendment = a.record(fetch(r["budget_amendment"])["body"], AMENDMENT)
        require(amendment == {"previous_gpu_seconds": PROJECT_GPU_SECONDS,
            "total_gpu_seconds": grant["caps"]["total_gpu_seconds"], "reserved": r["reserved"],
            "journal_heads": [j["head_sha256"] for j in r["journals"]], "refund": False},
                "MINICPM_PROJECT_CAP_AMENDMENT_SCOPE")


def event_record(kind, **details):
    c = a.current()
    if c is None:
        return
    return {"kind": kind, "ticket_sha256": digest(c["ticket"]),
        "request_sha256": digest(c["value"]["request"]), "source_sha256": c["value"]["request"]["source_sha256"],
        "time_unix": time.time(), **details}


def emit(kind, **details):
    record = event_record(kind, **details)
    if record is None:
        return
    print(EVENT_PREFIX + json.dumps(record, sort_keys=True, separators=(",", ":")), flush=True)
    return record


def native_started(ordinal, sample_id, image_sha256):
    """Called at the actual model.generate boundary after image prep/model load."""
    c = a.current()
    require(c is not None and c["phase"] == "native", "MINICPM_NATIVE_OBSERVATION_CAPABILITY")
    from safeshift.pilot.artifacts import read, write
    claim = read(c["claims"] / f"call-{ordinal:06d}.json")
    require(claim["ticket_sha256"] == digest(c["ticket"]), "MINICPM_NATIVE_OBSERVATION_CLAIM")
    row = c["value"]["cohort"]["samples"][ordinal]
    require(row["sample_id"] == sample_id and row["image_sha256"] == image_sha256,
            "MINICPM_NATIVE_OBSERVATION_TRAIN_ID_SHA")
    receipt = event_record("native_generate_started", ordinal=ordinal, sample_id=sample_id,
        image_sha256=image_sha256, claim=claim, model_loaded=True)
    write(c["claims"] / f"generate-{ordinal:06d}.json", {"kind": f"generate-{ordinal:06d}",
        "ticket_sha256": digest(c["ticket"]), "request_sha256": digest(c["value"]["request"]),
        "number": c["ticket"]["payload"]["number"], "time_unix": receipt["time_unix"], "observation": receipt})
    a.sync_directory(c["claims"])
    print(EVENT_PREFIX + json.dumps(receipt, sort_keys=True, separators=(",", ":")), flush=True)
    return receipt


def live_proof(log, value, envelope):
    """Positive provider log evidence only; stage-entry claims are insufficient."""
    require(type(log) is str and len(log.encode()) <= 16 * 2**20, "MINICPM_LIVE_LOG_BOUND")
    expected = {"ticket_sha256": digest(envelope), "request_sha256": digest(value["request"]),
                "source_sha256": value["request"]["source_sha256"]}
    stages, call, last = [], None, -1
    # Kaggle may expose the log as JSON stream chunks (the downloaded .log
    # format). Reassemble stdout before reading complete receipt lines.
    payload = log
    if log.lstrip().startswith("["):
        chunks = a.strict_json(log)
        require(type(chunks) is list and len(chunks) <= 200000, "MINICPM_PROVIDER_LOG_CHUNKS")
        stdout = []
        for chunk in chunks:
            require(type(chunk) is dict and chunk.get("stream_name") in ("stdout", "stderr")
                and type(chunk.get("data")) is str, "MINICPM_PROVIDER_LOG_CHUNK")
            if chunk["stream_name"] == "stdout":
                stdout.append(chunk["data"])
        payload = "".join(stdout)
    for line in payload.splitlines():
        if not line.startswith(EVENT_PREFIX):
            continue
        row = a.strict_json(line[len(EVENT_PREFIX):])
        require(all(row.get(k) == v for k, v in expected.items()), "MINICPM_LIVE_LOG_SOURCE_TICKET_DRIFT")
        now = row.get("time_unix")
        require(type(now) in (float, int) and math.isfinite(now) and last <= now <= time.time()
            and envelope["payload"]["issued_unix"] <= now < envelope["payload"]["start_before_unix"]
                + value["request"]["plan"]["max_seconds"], "MINICPM_LIVE_EVENT_TIME")
        last = now
        if row["kind"] == "stage_returned":
            stage = row["stage"]
            if stage in ("admit", "setup", "cpu", "gpu"):
                require(stages == list(("admit", "setup", "cpu", "gpu"))[:len(stages)]
                    and len(stages) < 4 and stage == ("admit", "setup", "cpu", "gpu")[len(stages)],
                        "MINICPM_LIVE_STAGE_ORDER")
                stages.append(stage)
        elif row["kind"] == "native_generate_started" and call is None:
            require(stages == ["admit", "setup", "cpu", "gpu"] and row["model_loaded"] is True,
                    "MINICPM_LIVE_NATIVE_BEFORE_POSITIVE_PREFLIGHT")
            ordinal = row["ordinal"]
            require(type(ordinal) is int and ordinal == value["request"]["plan"]["scheduled_ordinals"][0],
                    "MINICPM_LIVE_FIRST_ORDERED_CALL")
            sample = value["cohort"]["samples"][ordinal]
            claim = row["claim"]
            require(row["sample_id"] == sample["sample_id"] and row["image_sha256"] == sample["image_sha256"]
                and claim["kind"] == f"call-{ordinal:06d}" and claim["ticket_sha256"] == digest(envelope)
                and claim["request_sha256"] == digest(value["request"])
                and claim["number"] == envelope["payload"]["number"]
                and type(claim["time_unix"]) in (int, float) and math.isfinite(claim["time_unix"])
                and envelope["payload"]["issued_unix"] <= claim["time_unix"] <= now, "MINICPM_LIVE_CALL_CUSTODY")
            call = row
    return {"status": "NATIVE_STARTED" if call else "RUNNING_UNVERIFIED", "stages": stages,
        "first_native_call": call, "log_sha256": hashlib.sha256(log.encode()).hexdigest()}


def failure_receipt(value, envelope, provider, log, *, release=None, claims=None, inventory_complete=False):
    """A deterministic classification, never provider authentication by itself.

    Caller must verify remote code/version/Inputs and the full sealed supervisor
    output. No ZIP for an observed attempt, missing claims or native entry STOP.
    Expiry happens before launch/claims in the exact source, so it has no ZIP.
    """
    require(inventory_complete is True and provider["state"] in ("COMPLETE", "ERROR", "CANCELLED")
        and provider["job_id"] == value["job"] and provider["version"] == 1
        and provider["notebook_code_sha256"] == envelope["payload"]["notebook_code_sha256"],
            "MINICPM_FAILURE_EXACT_TERMINAL_PROVIDER_REQUIRED")
    require(type(log) is str and len(log.encode()) <= 16 * 2**20, "MINICPM_FAILURE_LOG_BOUND")
    if release is None:
        require(claims is None and "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH" in log,
                "MINICPM_FAILURE_NO_CLAIMS_IS_NOT_ZERO_CALLS_PROOF")
        cause = "MINICPM_STALE_PROVIDER_BEFORE_LAUNCH"
    else:
        require(type(claims) is dict and release["failure"] is not None
            and release["attempt_observed"] is False and release["recovery"] == "NO_ATTEMPT"
            and release["last_stage"] in ("admit", "setup", "cpu", "gpu")
            and release["source_sha256"] == value["request"]["source_sha256"]
            and "native.json" not in claims and "load.json" not in claims
            and all(not n.startswith(("call-", "generate-")) for n in claims),
                "MINICPM_FAILURE_NATIVE_PARTIAL_OR_UNKNOWN_STOP")
        require("launch.json" in claims and set(claims) <= {s + ".json" for s in a.STAGES[:-1]},
                "MINICPM_FAILURE_COMPLETE_CLAIMS_REQUIRED")
        for name, claim in claims.items():
            require(claim["kind"] + ".json" == name and claim["ticket_sha256"] == digest(envelope)
                and claim["request_sha256"] == digest(value["request"]), "MINICPM_FAILURE_CLAIM_BINDING")
        cause = release["failure"]["message"]
    return {"schema": "safeshift-minicpm-failed-pre-native-v3", "status": "FAILED_PRE_NATIVE",
        "provider": provider, "cause": cause, "ticket_sha256": digest(envelope),
        "reservation_preserved": envelope["payload"]["reserved_after"], "refund": False,
        "native_calls": 0, "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        "claims_sha256": digest(claims), "release_sha256": digest(release), "scientific_qualified": False}
