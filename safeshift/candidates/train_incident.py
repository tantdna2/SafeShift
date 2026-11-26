"""One replacement for a sealed, provably unconsumed checkpoint-discovery stop.

This is not resume or release of the original slot. Missing/partial/consumed
history is always a barrier. Local files cannot authenticate a remote VM.
"""
from pathlib import Path

from safeshift.pilot.artifacts import read, safe, sha
from safeshift.pilot.contract import digest
from .source import require
from .train_contract import MANIFEST, model, configuration_hashes

DECISION = "docs/research/CANDIDATE160_KAGGLE_ENV_DECISION_20261030.md"
INCIDENT = "internvl35-checkpoint-source-found0-20261030"


def verify(directory, reservation):
    """Accept only complete sealed zero-call evidence, never a claimed counter."""
    directory = Path(directory)
    require(safe(directory, "checksums.json").stat().st_size <= 16384, "INCIDENT_SEAL_SIZE_BOUND")
    checksums = read(safe(directory, "checksums.json"))
    require(type(checksums) is dict and 1 <= len(checksums) <= 64, "INCIDENT_SEAL_REQUIRED")
    # The zero-call failure layout is flat. Extra trees/raw/consumption, including
    # unlisted files, make the evidence incomplete or contradictory.
    require({p.name for p in directory.iterdir()} == {*checksums, "checksums.json"}, "INCIDENT_EXACT_SEALED_MEMBERS")
    for name, checksum in checksums.items():
        require("/" not in name and safe(directory, name).is_file()
                and safe(directory, name).stat().st_size <= 2**20
                and sha(safe(directory, name)) == checksum, "INCIDENT_CHECKSUM:" + name)
    required = {"owner_execution.json", "owner_consumption_log.json", "supervisor_status.json",
                "supervisor_failure.json", "supervisor_accounting.json", "pilot_manifest.json"}
    require(required <= checksums.keys(), "INCIDENT_COMPLETE_EVIDENCE_REQUIRED")
    execution = read(directory / "owner_execution.json")
    from . import train_owner as owner
    owner.validate(execution, "internvl35", execution["source_sha256"], execution["runtime_ref"], now=execution["created_unix"])
    name = "owner_slot_" + reservation["slot_sha256"] + ".json"
    allowed = required | {name, "authorization_binding.json", "release_config.json", "dependency_pins.json", "source_inventory.json"}
    require(set(checksums) <= allowed and name in checksums and read(directory / name) == reservation,
            "INCIDENT_PRECONSUMPTION_MEMBERS_ONLY")
    terminal = read(directory / "owner_consumption_log.json")
    status = read(directory / "supervisor_status.json")
    failure = read(directory / "supervisor_failure.json")
    require(execution["model_key"] == "internvl35" and execution["model"] == model("internvl35")
            and execution["manifest_sha256"] == MANIFEST and execution["split"] == "TRAIN"
            and all(execution[n] == v for n, v in configuration_hashes("internvl35").items()), "INCIDENT_SCOPE")
    require(execution["slot_sha256"] == reservation["slot_sha256"]
            and digest(execution) == reservation["execution_sha256"]
            and execution["run_id"] == reservation["run_id"]
            and execution["attempt_id"] == reservation["attempt_id"], "INCIDENT_EXECUTION_BINDING")
    require(all(terminal.get(k) == v for k, v in reservation.items() if k != "status")
            and terminal["status"] == "BLOCKED_RESERVED_NO_RETRY"
            and terminal["attempt_consumed"] is False and terminal["stage"] == "checkpoint_source",
            "INCIDENT_NOT_UNCONSUMED_CHECKPOINT_STOP")
    require(status["status"] == "BLOCKED" and status["attempt_consumed"] is False
            and status["stage"] == "checkpoint_source" and status["failure"] == failure == terminal["failure"]
            and status["source_sha256"] == execution["source_sha256"]
            and status["runtime_ref"] == execution["runtime_ref"], "INCIDENT_STATUS_BINDING")
    require(failure["message"] == "UNIQUE_candidate_checkpoint_internvl35.json_REQUIRED_FOUND_0"
            and failure["type"] == "ValueError" and failure["stage"] == "checkpoint_source", "INCIDENT_REASON")
    require(sha(directory / "pilot_manifest.json") == MANIFEST, "INCIDENT_MANIFEST_HASH")
    rows = read(directory / "pilot_manifest.json")["main"]
    accounting = read(directory / "supervisor_accounting.json")
    require(len(rows) == len(accounting) == 160, "INCIDENT_160_ACCOUNTING_REQUIRED")
    for i, (row, result) in enumerate(zip(rows, accounting)):
        require(result["ordinal"] == i and result["sample_id"] == row["sample_id"]
                and result["status"] == "NOT_ATTEMPTED" and result["label"] is None
                and type(result["attempts"]) is int and result["attempts"] == 0
                and type(result["native_calls"]) is int and result["native_calls"] == 0,
                "INCIDENT_ZERO_NATIVE_CALLS_REQUIRED")
    return {"incident_id": INCIDENT, "decision_record": DECISION,
            "original_run_id": execution["run_id"], "original_attempt_id": execution["attempt_id"],
            "original_source_sha256": execution["source_sha256"], "original_runtime_ref": execution["runtime_ref"],
            "sealed_members_sha256": digest(checksums), "seal_sha256": sha(directory / "checksums.json"),
            "original_terminal_sha256": sha(directory / "owner_consumption_log.json"),
            "attempt_consumed": False, "native_calls": 0, "replacement_limit": 1}


def replacement(history, reservations, key):
    require(key == "internvl35", "INCIDENT_REPLACEMENT_INTERNVL_ONLY")
    require(reservations and all(record == reservations[0] for record in reservations), "INCIDENT_CONFLICTING_RESERVATIONS")
    reservation = reservations[0]
    require(reservation.get("schema") == "safeshift-candidate160-owner-slot-v1"
            and reservation.get("status") == "RESERVED_NO_RETRY", "INCIDENT_ORIGINAL_SLOT_REQUIRED")
    verified = []
    for directory in history:
        log = safe(directory, "owner_consumption_log.json")
        if log.is_file():
            require(log.stat().st_size <= 16384, "INCIDENT_LOG_SIZE_BOUND")
        if log.is_file() and read(log).get("run_id") == reservation["run_id"]:
            verified.append(verify(directory, reservation))
    require(verified and all(v == verified[0] for v in verified), "INCIDENT_COMPLETE_UNAMBIGUOUS_HISTORY_REQUIRED")
    return verified[0]
