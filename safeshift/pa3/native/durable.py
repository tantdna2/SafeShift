"""Atomic no-overwrite records; CPU recovery reports torn tails, never retries."""
import argparse
import os
from pathlib import Path
from .journal import Journal, no_alias
from ..artifacts import json_bytes, receipt


class DurableJournal(Journal):
    """PR #102 staging/fsync/link pattern, independent of diagnostic authority."""
    def write(self, name, value):
        if self.path("seal").exists():
            raise ValueError("SEALED_JOURNAL_IMMUTABLE")
        path = self.path(name)
        side = no_alias(path.with_suffix(".sha256.json"))
        if path.exists() or side.exists():
            raise FileExistsError("NO_OVERWRITE_OR_RETRY:" + name)
        staging = no_alias(self.root.parent / (self.root.name + "-staging"))
        staging.mkdir(exist_ok=True)
        data = json_bytes(value)
        for target, payload in ((path, data), (side, json_bytes(receipt(data)))):
            temp = staging / (target.name + ".tmp")
            with temp.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temp, target)
            temp.unlink()
            if os.name != "nt":
                fd = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(fd)
                finally:
                    os.close(fd)
        return self.read(name)


def recover(root, output):
    """No tokenizer, GPU, dataset access or journal modification; integrity only."""
    journal = Journal(root)
    header = journal.read("manifest")
    if header.get("mode") != "full-train-r2":
        raise ValueError("R2_RECOVERY_ONLY")
    states, records = {}, {}
    names = {p.name.removesuffix(".sha256.json").removesuffix(".json")
             for p in journal.root.iterdir() if p.name.endswith(".json")}
    for name in sorted(names):
        try:
            records[name] = journal.read(name)
            states[name] = "VALID"
        except (ValueError, OSError):
            states[name] = "CORRUPT_OR_TORN"
    rows = []
    for i, sample in enumerate(header["samples"]):
        prefix = f"sample-{i:06d}"
        relevant = [n for n in states if n.startswith(prefix + ".")]
        status = ("CORRUPT_OR_TORN" if any(states[n] != "VALID" for n in relevant)
                  else "COMPLETE" if prefix + ".result" in records
                  else "ERROR" if prefix + ".error" in records
                  else "INCOMPLETE" if relevant else "NOT_ATTEMPTED")
        rows.append({"sample_id": sample["sample_id"], "recovery_status": status,
                     "result_status": records.get(prefix + ".result", {}).get("status"),
                     "merger_clamp": records.get(prefix + ".clamp-00")})
    staging = journal.root.parent / (journal.root.name + "-staging")
    result = {"run_id": header["run_id"], "scope": "INTEGRITY_ONLY_NOT_SCORE_AUDIT",
              "retry_permitted": False, "records": states, "samples": rows,
              "staging_leftovers": sorted(p.name for p in staging.iterdir()) if staging.exists() else []}
    report = DurableJournal(output, create=True)
    report.write("recovery", result)
    report.seal()
    report.package()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    recover(args.run, args.output)
