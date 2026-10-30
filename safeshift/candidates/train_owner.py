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
from safeshift.pilot.artifacts import safe, write
from . import train_contract as c
from .source import require

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


def slot(key):
    require(key in c.KEYS, "ONLY_TWO_REVIEWED_CANDIDATES")
    # Intentionally excludes runtime hash and UUID: editing/restarting source
    # cannot silently obtain another local slot for this model/cohort.
    return pilot.digest({"campaign": CAMPAIGN, "model_key": key,
                         "model": c.model(key), "manifest_sha256": c.MANIFEST})


def execution(key, source, ref, *, owner_start=False):
    require(owner_start is True, "OWNER_START_REQUIRED")
    require(key in c.KEYS, "ONLY_TWO_REVIEWED_CANDIDATES")
    require(isinstance(source, str) and isinstance(ref, str)
            and re.fullmatch(r"[0-9a-f]{64}", source) and re.fullmatch(r"[0-9a-f]{40}", ref),
            "OWNER_SOURCE_IDENTITY")
    now = time.time()
    identity = uuid.uuid4().hex
    return {"schema": SCHEMA, "activation": "OWNER_SAVE_AND_RUN_ALL",
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


def validate(value, key, source, ref, *, now=None):
    require(type(value) is dict and value.get("schema") == SCHEMA, "OWNER_EXECUTION_SCHEMA")
    # Exact field set prevents fabricated approval/permission records being
    # smuggled into this distinct execution schema.
    expected = execution(key, source, ref, owner_start=True)
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
            and value["expires_unix"] == value["created_unix"] + MAX_SECONDS, "OWNER_EXECUTION_EXPIRED")
    return value


def reserve(work, value, inputs):
    """Exclusive fixed slot; no release/retry even after failed admission.

An attached previous output is also a replay barrier. No claim is made about
another VM whose filesystem/output is not available to this process.
"""
    name = "owner_slot_" + value["slot_sha256"] + ".json"
    # Reuse bounded Kaggle mount discovery; do not walk image/weight trees.
    inputs = Path(inputs)
    visited = 0
    def directories(parent):
        nonlocal visited
        found = []
        for entry in parent.iterdir():
            visited += 1
            require(visited <= 512, "OWNER_HISTORY_DISCOVERY_BOUND")
            checked = safe(inputs, entry.relative_to(inputs).as_posix())
            if checked.is_dir():
                found.append(checked)
        return found
    mounts = directories(inputs)
    for mount in mounts.copy():
        if mount.name == "datasets":
            for owner in directories(mount):
                mounts.extend(directories(owner))
    for mount in mounts:
        for relative in (name, "data/processed/candidate160/attempts/" + name):
            require(not safe(inputs, (mount.relative_to(inputs) / relative).as_posix()).exists(),
                    "OWNER_SLOT_PRESENT_IN_ATTACHED_OUTPUT")
    attempts = safe(work, "attempts")
    attempts.mkdir(exist_ok=True)
    record = {"schema": "safeshift-candidate160-owner-slot-v1", "status": "RESERVED_NO_RETRY",
              "slot_sha256": value["slot_sha256"], "execution_sha256": pilot.digest(value),
              "run_id": value["run_id"], "attempt_id": value["attempt_id"],
              "model_key": value["model_key"], "manifest_sha256": c.MANIFEST}
    write(safe(attempts, name), record)  # O_EXCL + fsync, never overwrite/release.
    return name, deepcopy(record)
