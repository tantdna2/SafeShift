"""Sealed, image-only CT1 input contract and hard-capped checkpoint orchestration."""

import base64
import binascii
from collections import Counter
from itertools import permutations
import os
from pathlib import Path
import re
import stat
import time
from uuid import uuid4
from zipfile import ZipFile

from safeshift.data.saved_reports import checked, json_bytes, sha256, strict_json
from safeshift.evaluation.ct1_contract import ARMS, parse, prompt_hashes
from safeshift.evaluation.ct1_pilot import MODEL_ID, REVISION, validate_plan
from safeshift.evaluation.full_train_benchmark import is_sha256
from safeshift.fulltrain.qwen_semantics import fields
from safeshift.pilot.artifacts import export, safe, sha, verify_archive, write, write_bytes
from safeshift.candidates.source import require
from safeshift.fulltrain.supervision import process_group_closed

N_IMAGES = 48
N_CALLS = 144
SMOKE_CALLS = len(ARMS)
PROCESS_RECEIPTS = ("setup-supervisor.json", "worker-supervisor.json")
CONTROLLER_RECORD_BYTES = 65536
IMAGE_BYTES = 12 * 2**20
RUN_ID = re.compile(r"ct1-(?:smoke-)?[0-9a-f]{12}")
RECORD = r"(intent|tokens|raw|result|failure)\.json"
ENTRY = re.compile(r"calls/[0-9]{3}/" + RECORD)
PENDING = re.compile(r"calls/[0-9]{3}/\." + RECORD + r"\.[a-f0-9]{32}\.pending")


def publish_slot(path, value):
    """Flush a private staging name before publishing a finished slot record.

    Only the supervised child writes this journal. The supervisor reads or
    exports it after reaping that child. Orphans stay under their staging name.
    """
    require(not path.exists(), "CT1_JOURNAL_ALREADY_PUBLISHED")
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.pending")
    write_bytes(temporary, json_bytes(value))
    require(not path.exists(), "CT1_JOURNAL_ALREADY_PUBLISHED")
    os.rename(temporary, path)
    if os.name == "posix":
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def read_sealed(path, expected, limit):
    require(path.is_file() and path.stat().st_size <= limit, "CT1_INPUT_SIZE")
    return checked(path.read_bytes(), expected)


SOFTWARE_ARCHIVE_LIMIT = 64 * 2**20
SOFTWARE_ARCHIVES = ("python_source", "zlib_source")
SOFTWARE_MARKER = "fresh_qwen_software.json"
SOURCE_TRANSPORT = "ct1-source-base64.bin"


def software_transport_name(filename):
    return filename + "-base64.bin"


def restore_software(mount, marker_sha, runtime_lock, scratch, repo):
    from .qwen import reference

    marker = safe(mount, SOFTWARE_MARKER)
    value = strict_json(read_sealed(marker, marker_sha, 2**20))
    require(value["runtime_lock"] == runtime_lock, "CT1_SOFTWARE_RUNTIME_LOCK")
    ref = reference(repo)
    rows = []
    for component in SOFTWARE_ARCHIVES:
        row = value[component]
        expected_name = ref[component]["url"].rsplit("/", 1)[1]
        require(set(row) == {"file", "size", "sha256"} and row["file"] == expected_name
                and row["sha256"] == ref[component]["sha256"]
                and type(row["size"]) is int and 0 < row["size"] <= SOFTWARE_ARCHIVE_LIMIT,
                "CT1_SOFTWARE_ARCHIVE_PIN")
        rows.append(row)
    names = {software_transport_name(row["file"]) for row in rows}
    require({path.name for path in mount.iterdir()} == {SOFTWARE_MARKER, "wheels", *names},
            "CT1_SOFTWARE_TRANSPORT_ALLOWLIST")
    root = scratch / "ct1-build-archives"
    root.mkdir(exist_ok=False)
    for row in rows:
        transport = safe(mount, software_transport_name(row["file"]))
        size = row["size"]
        encoded_size = 4 * ((size + 2) // 3)
        require(transport.is_file() and transport.stat().st_size == encoded_size, "CT1_SOFTWARE_TRANSPORT_SIZE")
        with transport.open("rb") as stream:
            encoded = stream.read(encoded_size + 1)
        require(len(encoded) == encoded_size, "CT1_SOFTWARE_TRANSPORT_SIZE")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except binascii.Error as exc:
            raise ValueError("CT1_SOFTWARE_TRANSPORT_ENCODING") from exc
        require(len(raw) == size and base64.b64encode(raw) == encoded, "CT1_SOFTWARE_TRANSPORT_ENCODING")
        require(sha256(raw) == row["sha256"], "CT1_SOFTWARE_ARCHIVE_SHA256")
        write_bytes(root / row["file"], raw)
    return root


def admit(mount, plan_sha):
    require(mount.is_dir() and not mount.is_symlink(), "CT1_ISOLATED_INPUT_REQUIRED")
    require({p.name for p in mount.iterdir()} == {"plan.json", "exclusions.json", "images"}, "CT1_INPUT_ALLOWLIST")
    raw = read_sealed(safe(mount, "plan.json"), plan_sha, 65536)
    plan = strict_json(raw)
    exclusion = safe(mount, "exclusions.json")
    require(exclusion.stat().st_size <= 4096, "CT1_EXCLUSION_SIZE")
    exclusions = strict_json(exclusion.read_bytes())
    validate_plan(plan, exclusions)
    files = {r["case_id"] + ".png": r["image_sha256"] for r in plan["cases"]}
    images = safe(mount, "images")
    require(plan["kind"] == "TRAIN_DEVELOPMENT" and plan["arms"] == list(ARMS)
            and len(files) == N_IMAGES and {p.name for p in images.iterdir()} == files.keys(),
            "CT1_EXACT_48_IMAGE_ONLY_A_E_S")
    for name, expected in files.items():
        path = safe(mount, "images/" + name)
        require(path.is_file() and path.stat().st_size <= IMAGE_BYTES and sha(path) == expected, "CT1_IMAGE_SEAL")
    return plan, exclusions


def schedule(plan):
    orders = list(permutations(ARMS))
    return [(row["case_id"], arm, row["image_sha256"]) for i, row in enumerate(plan["cases"])
            for arm in orders[i % len(orders)]]


def identity(plan_sha, source_sha, capsule_sha, software_sha, run_id, *, smoke=False):
    require(RUN_ID.fullmatch(run_id) and is_sha256(source_sha) and is_sha256(capsule_sha)
            and is_sha256(plan_sha) and is_sha256(software_sha), "CT1_EXACT_RUN_IDENTITY")
    require(run_id.startswith("ct1-smoke-") == smoke, "CT1_RUN_SCOPE")
    return {"schema": "ct1-native-48-v1", "run_id": run_id, "plan_sha256": plan_sha,
            "source_sha256": source_sha, "capsule_sha256": capsule_sha, "software_sha256": software_sha,
            "model": MODEL_ID, "revision": REVISION, "prompt_sha256": prompt_hashes(ARMS),
            "max_calls": SMOKE_CALLS if smoke else N_CALLS}


def stability(read_receipt):
    seals = {}
    for name in PROCESS_RECEIPTS:
        payload = read_receipt(name)
        require(len(payload) <= CONTROLLER_RECORD_BYTES and process_group_closed(strict_json(payload)),
                "CT1_PROCESS_GROUP_UNVERIFIED")
        seals[name] = sha256(payload)
    return {"status": "LEDGER_STABLE", "process_receipts_sha256": seals}


def read_controller_record(root, name):
    """Read a bounded, regular controller record without following a leaf alias."""
    path = safe(root, name)
    original = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(original.st_mode) and original.st_nlink == 1
            and original.st_size <= CONTROLLER_RECORD_BYTES, "CT1_CONTROLLER_RECORD_TYPE_OR_SIZE")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        before = os.fstat(stream.fileno())
        require(os.path.samestat(original, before) and stat.S_ISREG(before.st_mode)
                and before.st_nlink == 1 and before.st_size <= CONTROLLER_RECORD_BYTES,
                "CT1_CONTROLLER_RECORD_CHANGED")
        data = stream.read(CONTROLLER_RECORD_BYTES + 1)
        after = os.fstat(stream.fileno())
        require(after.st_nlink == 1 and len(data) == before.st_size == after.st_size
                and len(data) <= CONTROLLER_RECORD_BYTES and before.st_mtime_ns == after.st_mtime_ns
                and before.st_ctime_ns == after.st_ctime_ns, "CT1_CONTROLLER_RECORD_CHANGED")
    return data


def stable_journal(root):
    return stability(lambda name: read_controller_record(root, name))


def restore(archive, expected, root, binding):
    """Read an archive for offline reconciliation; a digest cannot authorize a new VM."""
    require(archive.is_file() and archive.stat().st_size <= 32 * 2**20 and sha(archive) == expected,
            "CT1_RESUME_ZIP_SEAL")
    with ZipFile(archive) as z:
        infos = z.infolist()
        require(len(infos) <= 1000 and sum(x.file_size for x in infos) <= 32 * 2**20, "CT1_RESUME_BOUND")
        names = verify_archive(archive)
        require("diagnostic-status.json" not in names, "CT1_FORENSIC_ARCHIVE_NOT_RESUMABLE")
        require("identity.json" in names and strict_json(z.read("identity.json")) == binding,
                "CT1_RESUME_IDENTITY")
        # Only the ledger is restored. Output snapshots and receipts keep their original custody.
        call_files = [name for name in names if name.startswith("calls/")]
        require(all((ENTRY.fullmatch(name) or PENDING.fullmatch(name))
                    and int(name.split("/")[1]) < N_CALLS for name in call_files), "CT1_RESUME_MEMBER")
        require("config-summary.json" in names
                and strict_json(z.read("config-summary.json"))["mode"] == "pilot", "CT1_RESUME_PILOT_ONLY")
        require("resume-admission.json" in names and strict_json(z.read("resume-admission.json")).get("status")
                in ("FRESH_ADMITTED", "PARENT_VERIFIED_AND_INHERITED"), "CT1_RESUME_NOT_ADMITTED")
        require("summary.json" in names and "runs.json" in names
                and "journal-export-failure.json" not in names, "CT1_FORENSIC_ARCHIVE_NOT_RESUMABLE")
        require({"checkpoint-stability.json", *PROCESS_RECEIPTS} <= names.keys(),
                "CT1_CHECKPOINT_STABILITY_REQUIRED")
        for name in PROCESS_RECEIPTS:
            require(z.getinfo(name).file_size <= 65536, "CT1_PROCESS_RECEIPT_BOUND")
        require(strict_json(z.read("checkpoint-stability.json")) == stability(z.read),
                "CT1_CHECKPOINT_STABILITY_MISMATCH")
        for name in call_files:
            write_bytes(safe(root, name), z.read(name))


def slot_state(sample, case, arm, image_sha, binding_sha):
    members = list(sample.iterdir()) if sample.exists() else []
    require(all(p.is_file() and not p.is_symlink() and
                (ENTRY.fullmatch("calls/000/" + p.name) or PENDING.fullmatch("calls/000/" + p.name))
                for p in members), "CT1_UNEXPECTED_JOURNAL_MEMBER")
    records = {p.stem: p for p in members if ENTRY.fullmatch("calls/000/" + p.name)}
    uncertain_intent = any(
        (match := PENDING.fullmatch("calls/000/" + p.name)) and match[1] == "intent"
        for p in members
    )
    if "intent" in records:
        intent = strict_json(records["intent"].read_bytes())
        require((intent["case_id"], intent["arm"], intent["image_sha256"], intent["binding_sha256"]) ==
                (case, arm, image_sha, binding_sha),
                "CT1_JOURNAL_CASE_MISMATCH")
    if "raw" in records:
        require("intent" in records and "tokens" in records, "CT1_UNBOUND_RAW")
        raw = strict_json(records["raw"].read_bytes())
        require(raw["tokens_sha256"] == sha(records["tokens"]), "CT1_RAW_TOKEN_BINDING")
        if "result" in records:
            require(strict_json(records["result"].read_bytes()) == _parsed(arm, raw),
                    "CT1_RESULT_REPLAY_MISMATCH")
        return "RETURNED", raw["raw_text"]
    require("result" not in records, "CT1_RESULT_WITHOUT_RAW")
    if "intent" in records or "failure" in records or "tokens" in records or uncertain_intent:
        require("tokens" not in records or "intent" in records, "CT1_TOKENS_WITHOUT_INTENT")
        return "TECHNICAL_ERROR", None
    return "NOT_ATTEMPTED", None


def _parsed(arm, raw):
    parsed = parse(arm, raw["raw_text"])
    return {"status": parsed.status, "level": parsed.level, "wrapped": parsed.wrapped,
            "error": parsed.error, "evidence_status": parsed.evidence_status}


def reconstruct(root, plan, binding, *, smoke=False):
    require(len(schedule(plan)) == binding['max_calls'], 'CT1_CALL_PLAN_MISMATCH')
    records, calls, uncertain = [], 0, 0
    parses = {arm: Counter() for arm in ARMS}
    token_cap = Counter()
    binding_sha = sha256(json_bytes(binding))
    for i, (case, arm, image_sha) in enumerate(schedule(plan)):
        path = root / "calls" / f"{i:03}"
        status, raw = slot_state(path, case, arm, image_sha, binding_sha)
        parses[arm][parse(arm, raw).status if status == "RETURNED" else status] += 1
        if status == "RETURNED":
            token_cap[arm] += strict_json((path / "raw.json").read_bytes())["at_cap"]
        intent_present = (path / "intent.json").exists()
        calls += intent_present
        uncertain += not intent_present and any(path.glob(".intent.json.*.pending"))
        records.append({"case_id": case, "arm": arm, "attempt_status": status, "raw_text": raw})
    runs = {k: binding[k] for k in ("plan_sha256", "prompt_sha256")}
    runs.update(model_id=MODEL_ID, revision=REVISION, runtime_sha256=sha256(json_bytes(binding)), records=records)
    if smoke:
        runs["scope"] = "TECHNICAL_SMOKE_NOT_RESEARCH"
    write(root / ("smoke-runs.json" if smoke else "runs.json"), runs)
    write(root / "summary.json", {"scope": "TECHNICAL_SMOKE" if smoke else "PILOT",
                                  "planned_calls": binding["max_calls"], "durable_native_intents": calls, "uncertain_intents": uncertain,
                                  "returned": sum(r["attempt_status"] == "RETURNED" for r in records),
                                  "technical_error": sum(r["attempt_status"] == "TECHNICAL_ERROR" for r in records),
                                  "not_attempted": sum(r["attempt_status"] == "NOT_ATTEMPTED" for r in records),
                                  "arm_status_counts": {arm: dict(x) for arm, x in parses.items()},
                                  "token_cap_hits_by_arm": {arm: token_cap[arm] for arm in ARMS},
                                  "interpretation": "NATIVE_INTENT_IS_A_RESERVATION_NOT_COMPLETION"})


def checkpoint_results(root, output, plan, binding):
    write(root / "checkpoint-stability.json", stable_journal(root))
    reconstruct(root, plan, binding)
    export(root, output)


def execute(root, plan, binding, image_dir, backend, deadline):
    """Exactly one reserved slot per scheduled case/arm. Never retry an intent."""
    require(len(schedule(plan)) == binding["max_calls"], "CT1_CALL_PLAN_MISMATCH")
    binding_sha = sha256(json_bytes(binding))
    for i, (case, arm, image_sha) in enumerate(schedule(plan)):
        sample = root / "calls" / f"{i:03}"
        status, _ = slot_state(sample, case, arm, image_sha, binding_sha)
        if status != "NOT_ATTEMPTED":
            # Finish parse, or decode durable tokens locally, without rerunning generate.
            if (sample / "tokens.json").exists() and not (sample / "raw.json").exists():
                obj = backend.decode(strict_json((sample / "tokens.json").read_bytes()))
                publish_slot(sample / "raw.json", {**obj, "tokens_sha256": sha(sample / "tokens.json")})
            if (sample / "raw.json").exists() and not (sample / "result.json").exists():
                publish_slot(sample / "result.json", _parsed(arm, strict_json((sample / "raw.json").read_bytes())))
            continue
        if time.monotonic() >= deadline:
            break
        try:
            payload = read_sealed(safe(image_dir, case + ".png"), image_sha, IMAGE_BYTES)
            def begin(detail):
                publish_slot(sample / "intent.json", {"case_id": case, "arm": arm, "image_sha256": image_sha,
                                               "binding_sha256": binding_sha, **detail})
            def record_tokens(detail):
                require((sample / "intent.json").is_file(), "CT1_INTENT_REQUIRED")
                publish_slot(sample / "tokens.json", detail)
            raw, memory_after = backend.generate(payload, arm, begin, record_tokens)
            publish_slot(sample / "raw.json", {**raw, "memory_after": memory_after,
                                        "tokens_sha256": sha(sample / "tokens.json")})
            publish_slot(sample / "result.json", _parsed(arm, raw))
        except Exception as exc:
            details = {"type": type(exc).__name__, "message": str(exc)[:2000],
                       "seconds_monotonic": time.monotonic(), "automatic_retry": False}
            try:
                details["memory_at_failure"] = backend.failure_memory()
            except Exception as memory_error:
                details["memory_probe_failure"] = type(memory_error).__name__
            publish_slot(sample / "failure.json", details)
            raise
