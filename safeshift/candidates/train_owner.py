"""Owner-started TRAIN160 execution records, not grants or third-party consent.

The decision is recorded from the Owner's task of 2026-10-30. Save & Run All
activates one slot per model. Filesystem exclusion is local, not distributed.
"""
from copy import deepcopy
from pathlib import Path
import re
import time
import uuid

from safeshift.pilot import contract as pilot
from safeshift.pilot.artifacts import read, safe, sha, write
from . import train_contract as c
from .source import require
from .train_inputs import mounts
from . import train_route as route

SCHEMA = "safeshift-candidate160-owner-execution-v1"
MODE = "OWNER_ACTIVATED_TECHNICAL"
CAMPAIGN = "owner-train160-20261030"
DECISION = "docs/research/CANDIDATE160_OWNER_DECISION_20261030.md"
MAX_SECONDS = 43200


def policy():
    # Engineering reserves, not model quality thresholds. See the decision/PR.
    return {"review_mode": MODE, "behavior_limits": "NOT_DECIDED_OBSERVE_ONLY",
            "driver_versions": None, "free_mib_per_gpu": [14336, 1],
            "free_ram_mib": 4096, "free_scratch_mib": 1024,
            "free_output_mib": 1024, "free_gpu0_runtime_mib": 256}


def slot(key, *, implementation=None, qualification=False):
    require(key in c.KEYS, "ONLY_TWO_REVIEWED_CANDIDATES")
    # Intentionally excludes runtime hash and UUID: editing/restarting source
    # cannot silently obtain another local slot for this model/cohort.
    return pilot.digest({"campaign": CAMPAIGN, "model_key": key,
                         "model": c.model(key), "manifest_sha256": c.MANIFEST,
                         **route.fields(implementation, qualification)})


def execution(key, source, ref, *, owner_start=False, implementation=None, qualification=False):
    require(owner_start is True, "OWNER_START_REQUIRED")
    require(key in c.KEYS, "ONLY_TWO_REVIEWED_CANDIDATES")
    require(isinstance(source, str) and isinstance(ref, str)
            and re.fullmatch(r"[0-9a-f]{64}", source) and re.fullmatch(r"[0-9a-f]{40}", ref),
            "OWNER_SOURCE_IDENTITY")
    now = time.time()
    identity = uuid.uuid4().hex
    scope = route.fields(implementation, qualification)
    require(implementation is None or key == "minicpm4", "MINICPM_ONLY_NUMERICAL_EXCEPTION")
    value = {"schema": SCHEMA, "activation": "OWNER_SAVE_AND_RUN_ALL",
            "owner_decision_record": DECISION, "campaign": CAMPAIGN, "slot_sha256": slot(key),
            "model_key": key, "model": c.model(key), "base": c.BASE,
            "source_sha256": source, "runtime_ref": ref, **c.configuration_hashes(key),
            "manifest_sha256": c.MANIFEST, "inventory_sha256": c.INVENTORY,
            "data_revision": pilot.DATA_REVISION, "master_sha256": pilot.MASTER_SHA,
            "split": "TRAIN", "max_initial_ids": 160, "max_native_calls": 160,
            "retry_sample_ids": [], "resume": False,
            "run_id": f"owner_{key}_{identity}", "attempt_id": f"owner_{key}_{identity}_a1",
            "created_unix": now, "expires_unix": now + MAX_SECONDS,
            "max_seconds": MAX_SECONDS, "policy": policy()}
    if scope:
        value.update(scope, campaign=CAMPAIGN + "-" + pilot.digest(scope),
                     slot_sha256=slot(key, implementation=implementation, qualification=qualification),
                     **c.configuration_hashes(key, implementation=implementation))
    if qualification:
        value.update(owner_decision_record=route.DECISION, max_native_calls=3,
                     max_seconds=3600, expires_unix=now + 3600)
    elif implementation:
        from .train_official import binding
        value["official_numerical_approval"] = binding(key, implementation)
    return value


def validate(value, key, source, ref, *, now=None):
    require(type(value) is dict and value.get("schema") == SCHEMA, "OWNER_EXECUTION_SCHEMA")
    # Exact field set prevents fabricated approval/permission records being
    # smuggled into this distinct execution schema.
    expected = execution(key, source, ref, owner_start=True, **route.options(value))
    require(set(value) == set(expected), "OWNER_EXECUTION_FIELDS")
    variable = {"run_id", "attempt_id", "created_unix", "expires_unix"}
    for name in expected.keys() - variable:
        require(type(value[name]) is type(expected[name]) and pilot.digest(value[name]) == pilot.digest(expected[name]),
                "OWNER_EXECUTION_BINDING:" + name)
    require(isinstance(value["run_id"], str) and re.fullmatch(f"owner_{key}_[0-9a-f]{{32}}", value["run_id"])
            and value["attempt_id"] == value["run_id"] + "_a1", "OWNER_EXECUTION_IDS")
    import math
    require(all(type(value[n]) in (int, float) and math.isfinite(value[n])
                for n in ("created_unix", "expires_unix")), "OWNER_EXECUTION_TIME")
    now = time.time() if now is None else now
    require(value["created_unix"] <= now < value["expires_unix"]
            and value["expires_unix"] == value["created_unix"] + expected["max_seconds"], "OWNER_EXECUTION_EXPIRED")
    return value


def reserve(work, value, inputs):
    """Exclusive fixed slot; only the documented sealed zero-call incident can
receive one distinct replacement. The original slot is never changed.

An attached previous output is also a replay barrier. No claim is made about
another VM whose filesystem/output is not available to this process.
"""
    name = "owner_slot_" + value["slot_sha256"] + ".json"
    # Reuse bounded Kaggle mount discovery; do not walk image/weight trees.
    inputs = Path(inputs)
    roots = mounts(inputs)
    attempts = safe(work, "attempts")
    attempts.mkdir(exist_ok=True)
    original, history, terminals = [], [], []
    locations = [attempts]
    scanned = 0
    for mount in roots:
        locations += [mount, safe(mount, "data/processed/candidate160/attempts")]
        history.append(mount)
        parent = safe(mount, "data/processed/candidate160")
        if parent.is_dir():
            for entry in parent.iterdir():
                scanned += 1
                require(scanned <= 512, "INCIDENT_HISTORY_BOUND")
                checked = safe(parent, entry.name)
                if checked.is_dir() and checked.name != "attempts" and checked.name != "reviews":
                    history.append(checked)
    # Local failed evidence uses the same bounded, one-level layout.
    for entry in Path(work).iterdir():
        scanned += 1
        require(scanned <= 512, "INCIDENT_HISTORY_BOUND")
        checked = safe(work, entry.name)
        if checked.is_dir() and checked.name not in ("attempts", "reviews"):
            history.append(checked)
    replacement_name = name.removesuffix(".json") + ".replacement1.json"
    locations += history
    for location in locations:
        require(not safe(location, replacement_name).exists(), "OWNER_REPLACEMENT_ALREADY_RESERVED_DO_NOT_RETRY")
        require(not safe(location, replacement_name.removesuffix(".json") + ".consumed.json").exists(),
                "OWNER_REPLACEMENT_ALREADY_CONSUMED_DO_NOT_RETRY")
        require(not safe(location, name.removesuffix(".json") + ".consumed.json").exists(),
                "OWNER_CONSUMED_HISTORY_DO_NOT_RETRY")
        path = safe(location, name)
        if path.exists():
            require(path.is_file() and path.stat().st_size <= 16384, "OWNER_HISTORY_MARKER_INVALID")
            original.append(read(path))
        terminal = safe(location, name + ".terminal.json")
        if terminal.exists():
            require(terminal.is_file() and terminal.stat().st_size <= 16384
                    and read(terminal).get("attempt_consumed") is False, "OWNER_TERMINAL_CONSUMED_OR_UNKNOWN")
            terminals.append(terminal)
    incident = None
    observed_history = bool(terminals)
    for directory in history:
        for filename in ("owner_execution.json", "owner_consumption_log.json"):
            path = safe(directory, filename)
            if path.is_file():
                require(path.stat().st_size <= 16384, "OWNER_HISTORY_RECORD_SIZE_BOUND")
                record = read(path)
                if record.get("slot_sha256") == value["slot_sha256"]:
                    observed_history = True
                    if filename == "owner_consumption_log.json":
                        require(record.get("attempt_consumed") is False, "OWNER_CONSUMED_OR_UNKNOWN_HISTORY")
    require(not observed_history or original, "OWNER_PARTIAL_HISTORY_WITHOUT_RESERVATION")
    if original:
        from .train_incident import replacement
        try:
            incident = replacement(history, original, value["model_key"])
            require(all(sha(path) == incident["original_terminal_sha256"] for path in terminals),
                    "INCIDENT_CONFLICTING_TERMINAL")
        except (ValueError, OSError, KeyError, TypeError) as error:
            # Preserve the historical attached/local replay failure categories.
            if any(safe(location, name).exists() for location in locations[1:]):
                raise ValueError("OWNER_SLOT_PRESENT_IN_ATTACHED_OUTPUT:" + str(error)) from error
            raise FileExistsError("OWNER_SLOT_RESERVED_NO_RETRY:" + str(error)) from error
        name = replacement_name
    record = {"schema": "safeshift-candidate160-owner-slot-v1", "status": "RESERVED_NO_RETRY",
              "slot_sha256": value["slot_sha256"], "execution_sha256": pilot.digest(value),
              "run_id": value["run_id"], "attempt_id": value["attempt_id"],
              "model_key": value["model_key"], "manifest_sha256": c.MANIFEST}
    if incident is not None:
        record["replacement_incident"] = incident
    write(safe(attempts, name), record)  # O_EXCL + fsync, never overwrite/release.
    return name, deepcopy(record)
