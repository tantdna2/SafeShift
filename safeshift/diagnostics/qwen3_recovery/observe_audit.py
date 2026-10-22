"""CPU diagnostic-journal validation, independently of the native HNLO replay."""
from pathlib import Path
import re

from safeshift.pa3.native.journal import Journal, no_alias
from .cohort import NEW_RUN, NEW_ATTEMPT
from .observe import MAX_EVENTS, MAX_BYTES


def verify_observations(root, planned):
    root = Path(root)
    directory = root / "observations"
    index = Journal(root / "raw/index")
    if not directory.exists():
        return "NOT_STARTED"  # still permits a faithful failed/partial audit
    intact = True
    observed = set()
    for path in directory.iterdir():
        no_alias(path)
        if path.name != "lifecycle" and not re.fullmatch(r"sample-\d{6}", path.name):
            raise ValueError("UNKNOWN_OBSERVATION_JOURNAL")
        ordinal = None if path.name == "lifecycle" else int(path.name[-6:])
        if ordinal is not None and not 0 <= ordinal < len(planned):
            raise ValueError("OBSERVATION_OUTSIDE_RECOVERY")
        journal = Journal(path)
        try:
            if not journal.verify():
                intact = False
            inventory = journal.inventory()
        except (OSError, ValueError):
            intact = False
            continue
        events = sorted(n for n in inventory if n.startswith("event-"))
        if (set(inventory) - set(events) - {"failure"} or len(events) > MAX_EVENTS
                or events != [f"event-{i:03d}" for i in range(len(events))]
                or sum(p.stat().st_size for p in path.glob("*.json") if not p.name.endswith(".sha256.json")
                       and p.name != "seal.json") > MAX_BYTES):
            raise ValueError("OBSERVATION_BUDGET_OR_SEQUENCE_INVALID")
        last_clock = -1
        for name in events + (["failure"] if "failure" in inventory else []):
            record = journal.read(name)
            if (record["run_id"] != NEW_RUN or record["attempt_id"] != NEW_ATTEMPT
                    or record["recovery_ordinal"] != ordinal
                    or record["original_ordinal"] != (None if ordinal is None else 717 + ordinal)):
                raise ValueError("OBSERVATION_IDENTITY_CHANGED")
            if name != "failure":
                if record["monotonic_ns"] < last_clock:
                    raise ValueError("OBSERVATION_CLOCK_REVERSED")
                last_clock = record["monotonic_ns"]
        if ordinal is not None:
            observed.add(ordinal)
            if not events or journal.read(events[0])["stage"] != "sample_boundary_before_prepare":
                raise ValueError("MISSING_SAMPLE_BOUNDARY_OBSERVATION")
            if index.exists(f"sample-{ordinal:06d}.result"):
                if journal.read(events[-1])["stage"] != "after_sealed_cpu_replay":
                    intact = False
    attempted = {i for i in range(len(planned)) if index.exists(f"sample-{i:06d}.attempt")}
    if not (directory / "lifecycle").exists() or observed != attempted:
        intact = False
    return "PASS" if intact else "PARTIAL"
