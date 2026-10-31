"""Append-only Candidate160 attempts and portable, content-checked recovery.

No scientific result selector. Completed means durable technical evidence, and
INVALID counts as completed too. Every invocation gets its own immutable journal.
"""
from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from safeshift.pilot.artifacts import read, safe, sha, write, write_bytes, verify_archive
from safeshift.pilot.contract import digest, parse_label
from .source import require
from . import train_contract as c, train_owner as owner
from . import train_route as route

SCHEMA = "safeshift-candidate160-owner-execution-v2"
DECISION = "docs/research/CANDIDATE160_RECOVERY_DECISION_20261031.md"
MAX_FILES = 200000
MAX_BYTES = 8 * 2**30


@contextmanager
def lease(work, key):
    """Kernel lock, released on process death; the file is never deleted.

Linux children inherit the descriptor, keeping exclusion if the supervisor dies
while its worker still runs. Separate Kaggle VMs need Owner serialization.
"""
    path = safe(work, "attempts/active_" + owner.slot(key) + ".lock")
    path.parent.mkdir(exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, 0)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquired = True
        yield {} if os.name == "nt" else {"pass_fds": (fd,)}
    except OSError as error:
        if not acquired:
            raise FileExistsError("CANDIDATE160_ACTIVE_PROCESS") from error
        raise
    finally:
        # Closing the supervisor copy does not unlock inherited Linux copies.
        os.close(fd)


def _series_id(index, key, action, run_id):
    modern = {n: r for n, r in index["runs"].items() if r["schema"] == SCHEMA}
    ancestors = {n for r in modern.values() for n in r["ancestors"]}
    heads = set(modern) - ancestors
    require(action == "rerun" or len(heads) <= 1, "HISTORY_DIVERGENT_HEADS")
    return (run_id if action == "rerun" or not index["runs"] else
            modern[next(iter(heads))]["series_id"] if heads else owner.slot(key))


def execution(key, source, ref, index, *, action="resume", owner_start=False, implementation=None, qualification=False):
    require(action in ("resume", "rerun"), "RECOVERY_ACTION")
    value = owner.execution(key, source, ref, owner_start=owner_start,
                            implementation=implementation, qualification=qualification)
    require({k: index[k] for k in route.fields(implementation, qualification)} ==
            route.fields(implementation, qualification), "HISTORY_ROUTE_BINDING")
    value.update(schema=SCHEMA, owner_decision_record=DECISION, resume=True,
                 recovery_action=action, history_sha256=digest(index),
                 run_kind="FULL_RERUN" if action == "rerun" else "RECOVERY" if index["runs"] else "INITIAL",
                 scientific_selection="PENDING", series_id=_series_id(index, key, action, value["run_id"]))
    return value


def validate(value, key, source, ref, *, now=None):
    require(type(value) is dict and value.get("schema") == SCHEMA, "RECOVERY_EXECUTION_SCHEMA")
    extra = {"recovery_action", "history_sha256", "run_kind", "scientific_selection", "series_id"}
    old = {k: deepcopy(v) for k, v in value.items() if k not in extra}
    old.update(schema=owner.SCHEMA, owner_decision_record=(route.DECISION if
               value.get("technical_qualification") else owner.DECISION), resume=False)
    owner.validate(old, key, source, ref, now=now)
    require(set(value) == set(old) | extra and value["owner_decision_record"] == DECISION
            and value["resume"] is True and value["scientific_selection"] == "PENDING"
            and value["recovery_action"] in ("resume", "rerun")
            and re.fullmatch("[0-9a-f]{64}", value["history_sha256"])
            and isinstance(value["series_id"], str) and re.fullmatch(r"[A-Za-z0-9_]{1,100}", value["series_id"])
            and value["run_kind"] in ("INITIAL", "RECOVERY", "FULL_RERUN"), "RECOVERY_EXECUTION_BINDING")
    return value


def members(directory):
    """Bounded direct journal inventory. Histories are flattened, never nested."""
    result, size = {}, 0
    pending = [(Path(directory), "")]
    visited = 0
    while pending:
        parent, prefix = pending.pop()
        for entry in parent.iterdir():
            visited += 1
            require(visited <= MAX_FILES, "HISTORY_FILE_BOUND")
            name = prefix + entry.name
            checked = safe(directory, name)
            if name == "history" and checked.is_dir():
                continue
            if checked.is_dir():
                pending.append((checked, name + "/"))
            else:
                require(checked.is_file(), "HISTORY_REGULAR_FILE_REQUIRED")
                size += checked.stat().st_size
                require(size <= MAX_BYTES, "HISTORY_BYTE_BOUND")
                result[name] = sha(checked)
    return dict(sorted(result.items()))


def _scope(directory, key):
    execution_file = safe(directory, "owner_execution.json")
    require(execution_file.stat().st_size <= 16384, "HISTORY_EXECUTION_SIZE_BOUND")
    g = read(execution_file)
    route.admission(g)
    expected = owner.execution(key, g["source_sha256"], g["runtime_ref"], owner_start=True, **route.options(g))
    require(g.get("model_key") == key and g.get("campaign") == expected["campaign"]
            and g.get("slot_sha256") == expected["slot_sha256"], "HISTORY_CAMPAIGN_BINDING")
    validator = validate if g.get("schema") == SCHEMA else owner.validate
    validator(g, key, g["source_sha256"], g["runtime_ref"], now=g["created_unix"])
    terminal = safe(directory, "owner_consumption_log.json")
    if terminal.exists():
        require(terminal.stat().st_size <= 16384, "HISTORY_TERMINAL_SIZE_BOUND")
        log = read(terminal)
        require(log.get("run_id") == g["run_id"] and log.get("attempt_id") == g["attempt_id"]
                and log.get("execution_sha256") == digest(g)
                and (log.get("attempt_consumed") is None or type(log["attempt_consumed"]) is bool),
                "HISTORY_TERMINAL_BINDING")
        consumption = safe(directory, "consumption.json")
        if consumption.exists():
            require(read(consumption) == {"attempt_consumed": True, "attempt_id": g["attempt_id"]}
                    and log["attempt_consumed"] is not False, "HISTORY_CONTRADICTORY_CONSUMPTION")
    return g


def collect(work, inputs, output, key, *, implementation=None, qualification=False):
    """Snapshot available local/attached directories or sealed ZIPs before work.

Orphan markers and conflicting copies block admission, rather than silently
claiming a fresh baseline. All old statuses, including replacement1, are evidence.
"""
    from .train_inputs import mounts
    work, output = Path(work), Path(output)
    scope = route.fields(implementation, qualification)
    slot = owner.slot(key, implementation=implementation, qualification=qualification)
    roots = [work, *mounts(inputs)]
    candidates, markers, archives = set(), [], set()
    visited = 0
    for root in roots:
        suffix = "_q" + ("_fp32" if implementation else "") if qualification else ""
        for base in dict.fromkeys((root, safe(root, "data/processed/candidate160"),
                                   safe(root, "data/processed/candidate160" + suffix))):
            if not base.is_dir():
                continue
            if safe(base, "owner_execution.json").is_file() or safe(base, "supervisor_status.json").is_file():
                candidates.add(base)
            for entry in base.iterdir():
                visited += 1
                require(visited <= 4096, "HISTORY_DISCOVERY_BOUND")
                entry = safe(base, entry.name)
                if entry == output:
                    continue
                if entry.is_dir() and (safe(entry, "owner_execution.json").is_file() or
                        (re.fullmatch(key + r"-[0-9a-f]{32}", entry.name) and safe(entry, "supervisor_status.json").is_file())):
                    candidates.add(entry)
                if entry.is_file() and re.fullmatch(key + r"-[0-9a-f]{32}\.zip", entry.name):
                    archives.add(entry)
            attempts = safe(base, "attempts")
            if attempts.is_dir():
                for entry in attempts.iterdir():
                    visited += 1
                    require(visited <= 4096, "HISTORY_DISCOVERY_BOUND")
                    entry = safe(attempts, entry.name)
                    if entry.name.startswith("owner_slot_" + slot) and entry.suffix == ".json":
                        markers.append(entry)
            for entry in base.glob("owner_slot_" + slot + "*.json"):
                markers.append(safe(base, entry.name))
    found, diagnostics = {}, {}
    total_files = total_bytes = 0
    def add(directory, expected=None):
        nonlocal total_files, total_bytes
        execution_file = safe(directory, "owner_execution.json")
        if not execution_file.exists():
            # Admission/history/source failures before execution creation are
            # diagnostics, not orphan consumed runs. Keep them without turning
            # their own exported ZIP into another permanent retry barrier.
            status = read(safe(directory, "supervisor_status.json"))
            if status.get("model_key") not in (None, key):
                return
            require(status.get("attempt_consumed") is False
                    and not safe(directory, "consumption.json").exists()
                    and not safe(directory, "calls").exists(), "HISTORY_MISSING_EXECUTION")
            inventory = members(directory)
            seal = safe(directory, "checksums.json")
            if seal.exists():
                require(all(inventory.get(n) == v for n, v in read(seal).items() if not n.startswith("history/")),
                        "HISTORY_DIAGNOSTIC_SEAL")
            checksum = digest(inventory)
            if checksum not in diagnostics:
                total_files += len(inventory)
                total_bytes += sum(safe(directory, n).stat().st_size for n in inventory)
                require(total_files <= MAX_FILES and total_bytes <= MAX_BYTES, "HISTORY_TOTAL_BOUND")
                for name in inventory:
                    destination = safe(output, "history_diagnostics/" + checksum + "/" + name)
                    write_bytes(destination, safe(directory, name).read_bytes())
                    require(sha(destination) == inventory[name], "HISTORY_DIAGNOSTIC_CHANGED")
                diagnostics[checksum] = {"members": inventory, "snapshot_sha256": checksum,
                    "scope": "PRE_EXECUTION_FAILURE_NOT_A_MODEL_ATTEMPT"}
            return
        require(execution_file.stat().st_size <= 16384, "HISTORY_EXECUTION_SIZE_BOUND")
        g = read(execution_file)
        if g.get("model_key") != key:
            return
        if route.fields(**route.options(g)) != scope:
            return  # Different arithmetic/technical scope cannot supply completion.
        g = _scope(directory, key)
        inventory = members(directory)
        if expected is not None:
            require(inventory == expected["members"], "HISTORY_SNAPSHOT_CHECKSUM")
        seal = safe(directory, "checksums.json")
        if seal.exists():
            for name, checksum in read(seal).items():
                if not name.startswith("history/"):
                    require(inventory.get(name) == checksum, "HISTORY_SEAL_MISMATCH:" + name)
        run_id = g["run_id"]
        snapshot = {"members": inventory, "snapshot_sha256": digest(inventory),
                    "execution_sha256": digest(g), "attempt_id": g["attempt_id"],
                    "schema": g["schema"], "series_id": g.get("series_id", owner.slot(key)),
                    "ancestors": sorted(read(directory / "history_index.json")["runs"]) if g["schema"] == SCHEMA else []}
        if run_id in found:
            require(found[run_id] == snapshot, "HISTORY_CONFLICTING_RUN:" + run_id)
            return
        total_files += len(inventory)
        total_bytes += sum(safe(directory, n).stat().st_size for n in inventory)
        require(total_files <= MAX_FILES and total_bytes <= MAX_BYTES, "HISTORY_TOTAL_BOUND")
        target = safe(output, "history/" + run_id)
        for name in inventory:
            source = safe(directory, name)
            destination = safe(target, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as before, destination.open("xb") as after:
                shutil.copyfileobj(before, after, 2**20)
                after.flush()
                os.fsync(after.fileno())
            require(sha(destination) == inventory[name], "HISTORY_CHANGED_DURING_COPY")
        found[run_id] = snapshot
        nested = safe(directory, "history_index.json")
        if nested.exists() and safe(directory, "history").is_dir():
            index = read(nested)
            require(g.get("history_sha256") == digest(index), "HISTORY_INDEX_BINDING")
            for parent, record in index["runs"].items():
                add(safe(directory, "history/" + parent), record)
    for directory in sorted(candidates):
        add(directory)
    # ZIP-only Outputs work too; extraction stays temporary and never mutates input.
    archive_index = []
    for archive in sorted(archives):
        verify_archive(archive)
        archive_index.append({"name": archive.name, "sha256": sha(archive)})
        sidecar = Path(str(archive) + ".sha256.json")
        if sidecar.exists():
            require(read(sidecar)["sha256"] == sha(archive), "HISTORY_ARCHIVE_SIDECAR")
        with tempfile.TemporaryDirectory(prefix="candidate160-history-") as temporary:
            with zipfile.ZipFile(archive) as zipped:
                for info in zipped.infolist():
                    write_bytes(safe(temporary, info.filename), zipped.read(info))
            add(Path(temporary))
    marker_index = []
    for marker in sorted(set(markers)):
        require(marker.stat().st_size <= 16384, "HISTORY_MARKER_BOUND")
        value = read(marker)
        run_id = value.get("run_id")
        require(run_id in found, "HISTORY_MISSING_RUN_FOR_MARKER")
        g = read(safe(output, "history/" + run_id + "/owner_execution.json"))
        require(value.get("attempt_id") == g["attempt_id"]
                and value.get("execution_sha256") == digest(g), "HISTORY_MARKER_BINDING")
        terminal = safe(output, "history/" + run_id + "/owner_consumption_log.json")
        if marker.name.endswith(".consumed.json") and terminal.exists():
            require(read(terminal).get("attempt_consumed") is not False, "HISTORY_CONTRADICTORY_CONSUMPTION")
        checksum = sha(marker)
        target = safe(output, "history_markers/" + checksum + ".json")
        if not target.exists():
            write_bytes(target, marker.read_bytes())
        require(sha(target) == checksum, "HISTORY_MARKER_CHANGED")
        item = {"name": marker.name, "sha256": checksum}
        if item not in marker_index:
            marker_index.append(item)
    index = {"schema": "safeshift-candidate160-history-v1", "model_key": key,
             "manifest_sha256": c.MANIFEST, "runs": dict(sorted(found.items())),
             "markers": sorted(marker_index, key=lambda v: (v["name"], v["sha256"])),
             "archives": archive_index, "diagnostics": dict(sorted(diagnostics.items())), **scope}
    write(output / "history_index.json", index)
    return index


def recovery_plan(output, rows, g):
    """Reconcile every attempt; choose no scientific result or preferred score."""
    from .train_run import (recover, validate_context, validate_raw_configuration,
                            validate_native_configuration, native_custody)
    from safeshift.pilot.hnlo import replay
    require(len(rows) == len({r["sample_id"] for r in rows}) == 160, "EXACT_SHARED_160_PLAN")
    index = read(Path(output) / "history_index.json")
    require(digest(index) == g["history_sha256"] and index["model_key"] == g["model_key"]
            and index["manifest_sha256"] == c.MANIFEST, "RECOVERY_HISTORY_BINDING")
    expected_kind = "FULL_RERUN" if g["recovery_action"] == "rerun" else "RECOVERY" if index["runs"] else "INITIAL"
    require(g["run_kind"] == expected_kind, "RECOVERY_RUN_KIND")
    require(g["series_id"] == _series_id(index, g["model_key"], g["recovery_action"], g["run_id"]), "RECOVERY_ACTIVE_SERIES")
    for marker in index["markers"]:
        require(sha(safe(output, "history_markers/" + marker["sha256"] + ".json")) == marker["sha256"],
                "RECOVERY_MARKER_CHANGED")
    lineage = {r["sample_id"]: [] for r in rows}
    completed = set()
    for run_id, record in index["runs"].items():
        directory = safe(output, "history/" + run_id)
        require(members(directory) == record["members"]
                and digest(record["members"]) == record["snapshot_sha256"], "RECOVERY_HISTORY_CHANGED")
        previous = _scope(directory, g["model_key"])
        require(digest(previous) == record["execution_sha256"], "RECOVERY_EXECUTION_CHANGED")
        require(record["series_id"] == previous.get("series_id", owner.slot(g["model_key"])), "RECOVERY_SERIES_BINDING")
        if previous["schema"] == SCHEMA:
            parents = read(directory / "history_index.json")
            require(digest(parents) == previous["history_sha256"]
                    and all(index["runs"].get(n) == v for n, v in parents["runs"].items())
                    and run_id not in parents["runs"] and record["ancestors"] == sorted(parents["runs"]),
                    "RECOVERY_MISSING_OR_CONFLICTING_ANCESTOR")
        recovered = recover(directory, rows, previous)
        if safe(directory, "calls").exists():
            validate_context(read(directory / "configuration_binding.json"), previous)
        for i, row in enumerate(rows):
            value = recovered[row["sample_id"]]
            sample = safe(directory, f"calls/{i:06d}/run/samples/000000")
            raw_path = sample / "raw.json"
            require(not (sample / "native_call.json").exists() or (sample / "started.json").exists(),
                    "HISTORY_NATIVE_WITHOUT_START")
            require(not raw_path.exists() or (sample / "native_call.json").exists(), "HISTORY_RAW_WITHOUT_NATIVE")
            terminal = directory / "owner_consumption_log.json"
            if (sample / "started.json").exists() and terminal.is_file():
                require(read(terminal).get("attempt_consumed") is not False, "HISTORY_CONTRADICTORY_CONSUMPTION")
            durable = False
            # A valid raw written just before a kill is recoverable even if its
            # result/summary wasn't written. Derived evidence lives in this plan.
            if raw_path.is_file():
                try:
                    raw = read(raw_path)
                    context = validate_context(read(directory / "configuration_binding.json"), previous)
                    identity = read(directory / f"calls/{i:06d}/run/identity.json")
                    validate_raw_configuration(raw, identity, context)
                    validate_native_configuration(sample, context)
                    native_custody(sample, raw)
                    started = read(sample / "started.json")
                    require(started["sample_id"] == row["sample_id"]
                            and started["input_sha256"] == row["image_sha256"]
                            and started["attempt_id"] == previous["attempt_id"]
                            and (sample / "native_call.json").is_file()
                            and identity["ordinal"] == i and identity["sample_id"] == row["sample_id"]
                            and identity["input_sha256"] == row["image_sha256"], "RECOVERY_INPUT_IDENTITY")
                    label = parse_label(raw["response"])
                    h = replay(raw, label)
                    durable = not raw.get("raw_nonfinite", False) and h.get("replay_status") != "FAIL"
                    if (sample / "result.json").exists():
                        durable = (durable and value["status"] in ("SUCCESS", "INVALID")
                                   and not value.get("raw_nonfinite", False)
                                   and value.get("hnlo", {}).get("replay_status") != "FAIL")
                except (OSError, ValueError, KeyError, TypeError):
                    durable = False
            same_series = record["series_id"] == g["series_id"]
            if durable and same_series:
                completed.add(i)
            lineage[row["sample_id"]].append({"run_id": run_id, "attempt_id": previous["attempt_id"],
                "snapshot_sha256": record["snapshot_sha256"], "status": value["status"],
                "attempts": value["attempts"], "native_calls": value["native_calls"],
                "raw_sha256": record["members"].get(f"calls/{i:06d}/run/samples/000000/raw.json"),
                "durable_completion": durable, "same_series": same_series})
    require(route.fields(**route.options(index)) == route.fields(**route.options(g)), "RECOVERY_ROUTE_BINDING")
    selected = route.ORDINALS if g.get("technical_qualification") else range(160)
    pending = [i for i in selected if g["recovery_action"] == "rerun" or i not in completed]
    return {"schema": "safeshift-candidate160-recovery-plan-v1", "run_id": g["run_id"],
            "history_sha256": g["history_sha256"], "run_kind": g["run_kind"], "series_id": g["series_id"],
            "action": g["recovery_action"], "pending_ordinals": pending,
            "already_durable_ordinals": sorted(completed), "lineage": lineage,
            "scientific_selection": "PENDING", "pooling_allowed": False}
