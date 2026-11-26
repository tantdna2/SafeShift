"""Build or byte-check the private, CPU-only MiniCPM Full-TRAIN Normalization V1."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha, write_bytes
from safeshift.pilot.contract import LEVELS, PROMPT_SHA, STATUSES, digest, json_bytes, parse_label, require_hash
from scripts import minicpm_offline_fast as fast

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = "minicpm-fulltrain-normalization-v1"
DECISION = "DEC-20261126-OWNER-MINICPM-FULLTRAIN-NORMALIZATION-V1"
NORMAL_DESCRIPTION = "no abnormalities observed"
NORMAL_LABEL = "Level04"
COHORT_SCHEMA = "safeshift-fulltrain-cohort-v1"
PARENT = {
    "base_sha": "c95e7792283cdd406e218aef4e65529c615466be",
    "review": "https://github.com/tantdna2/SafeShift/pull/213#issuecomment-7184395149",
    "fast_source_sha": "5f12a752acd636878fb6044c00185e7af5e2ae63",
    "status": fast.v5.PROVISIONAL,
    "registration_sha256": "96929816544e07c1a9d91cba6e510b2aedc73da7ca37c042ebe68776c0c6ae07",
    "head_event": 30,
    "head_sha256": "62e6ba7650a5fba23286cb00cb88b96104de8c0d7c38945c77e0f1fe7ce820f3",
    "cohort_sha256": "524980d374daf6be3bedc743b6dc5ddc423dfe11c833609253cc5b2ce38586dc",
    "invalid_raw_sha256_list_digest": "5a27207cd44dad4cbc36473cbf1f8e1e1f3ec12ea110bf967ca8e6796db46a9a",
    "prompt_sha256": PROMPT_SHA,
}
SAMPLE_FIELDS = (
    "sample_id", "ordinal", "split", "image_sha256", "status", "generated_label",
    "original_status", "original_label", "normalization_applied", "raw_sha256",
    "completion_event", "run_id", "attempt_id", "hnlo_status",
)
CONVERSION_FIELDS = (
    "sample_id", "ordinal", "original_status", "original_label", "status", "generated_label",
    "run_id", "attempt_id", "completion_event", "archive", "archive_sha256", "raw_member", "raw_sha256",
)


def normalize_response(response):
    """Use C1 for canonical predictions and recognize exactly one additional value."""
    if not isinstance(response, str):
        return None
    try:
        label = parse_label(response)
        if label is not None:
            return label
        # An object becomes a tuple of pairs. A JSON array remains a list,
        # and extra or duplicate keys cannot match the single-pair tuple.
        pairs = json.loads(response, object_pairs_hook=tuple)
    except (ValueError, RecursionError):
        return None
    if pairs == (("safety_level", NORMAL_DESCRIPTION),):
        return NORMAL_LABEL
    return None


def mirrored_document(primary, mirror, name, expected):
    paths = [safe(root, name) for root in (primary, mirror)]
    for path in paths:
        fast.pinned(path, expected)
    value = read(paths[0])
    require(digest(value) == expected, f"Journal document SHA256 mismatch: {name}")
    return value


def parent_records(primary, mirror, parent):
    registration = mirrored_document(primary, mirror, "registration.json", parent["registration_sha256"])
    cohort = registration["initial"]["cohort"]
    require(digest(cohort) == parent["cohort_sha256"], "Cohort SHA256 mismatch")
    require(cohort["schema"] == COHORT_SCHEMA and cohort["split"] == "TRAIN", "Expected the TRAIN cohort")
    samples = cohort["samples"]
    require(samples and [s["ordinal"] for s in samples] == list(range(len(samples))), "Invalid cohort ordinals")
    require(len({s["sample_id"] for s in samples}) == len(samples), "Duplicate cohort ID")
    for sample in samples:
        require(isinstance(sample["sample_id"], str) and sample["sample_id"], "Missing cohort ID")
        require_hash(sample["image_sha256"])

    # Follow the pinned head backwards. Each event's previous digest binds
    # the actual bytes of the preceding event in both Fast journal copies.
    events = []
    expected = parent["head_sha256"]
    for number in range(parent["head_event"], 0, -1):
        event = mirrored_document(primary, mirror, f"event-{number:06d}.json", expected)
        require(event["number"] == number and event["schema"] == registration["schema"], "Journal chain mismatch")
        if event["kind"] == fast.v5.PROVISIONAL:
            events.append(event)
        expected = require_hash(event["previous"])
    require(expected == parent["registration_sha256"] and events and events[0]["number"] == parent["head_event"],
            "Journal chain does not bind the completed registration")
    return samples, reversed(events)


def convert_record(archive, record, source, cohort_sha256, ordinal):
    member = f"calls/{ordinal:06d}/run/samples/000000/raw.json"
    try:
        info = archive.getinfo(member)
    except KeyError as exc:
        raise ValueError(f"Missing raw member at ordinal {ordinal}") from exc
    raw = archive.read(info)
    require(hashlib.sha256(raw).hexdigest() == record["raw_sha256"], f"Raw SHA256 mismatch at ordinal {ordinal}")
    output = json.loads(raw)
    identity = output["identity"]
    require(identity["sample_id"] == record["sample_id"] and identity["input_sha256"] == record["image_sha256"]
            and identity["run_id"] == source["run_id"] and identity["manifest_sha256"] == cohort_sha256,
            f"Raw identity mismatch at ordinal {ordinal}")
    response = output["response"]
    require(parse_label(response) is None and normalize_response(response) == NORMAL_LABEL,
            f"C1 INVALID falls outside the authorized mapping at ordinal {ordinal}")
    return member


def summarize(rows, *, original):
    statuses = Counter(r["original_status" if original else "status"] for r in rows)
    labels = Counter(r["original_label" if original else "label"] for r in rows)
    return {"total_ids": len(rows), **{key: statuses[key] for key in STATUSES},
            **{key: labels[key] for key in LEVELS}, "valid_label_coverage": statuses["SUCCESS"] / len(rows)}


def csv_bytes(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def products(primary, mirror, parent):
    samples, events = parent_records(primary, mirror, parent)
    rows, conversions, sources = [], [], []
    for event in events:
        payload = event["payload"]
        report = payload["verification"]["report"]
        history = report["history"][-1]
        require(history["cohort_sha256"] == parent["cohort_sha256"]
                and history["identity"]["prompt_sha256"] == parent["prompt_sha256"],
                "Completion cohort or prompt SHA256 mismatch")
        source = {"completion_event": event["number"], "completion_sha256": digest(event),
                  "ticket_sha256": payload["ticket_sha256"], "archive": payload["attempt"],
                  "archive_sha256": require_hash(report["attempt_sha256"]),
                  "run_id": history["run_id"], "attempt_id": history["attempt_id"],
                  "series_id": history["series_id"], "identity": history["identity"]}
        sources.append(source)
        for root in (primary, mirror):
            fast.pinned(safe(root, source["archive"]), source["archive_sha256"])
        with zipfile.ZipFile(safe(primary, source["archive"])) as archive:
            require(len(archive.NameToInfo) == len(archive.infolist()), "Duplicate attempt ZIP member")
            for record in history["records"]:
                ordinal = len(rows)
                require(ordinal < len(samples), "Extra or duplicate parent ID")
                sample = samples[ordinal]
                require(record["sample_id"] == sample["sample_id"], f"ID or order mismatch at ordinal {ordinal}")
                require(record["image_sha256"] == sample["image_sha256"], f"Image SHA256 mismatch at ordinal {ordinal}")
                require_hash(record["raw_sha256"])
                status, label = record["status"], record["label"]
                require((status == "SUCCESS" and label in LEVELS) or (status == "INVALID" and label is None),
                        f"Unexpected parent prediction at ordinal {ordinal}")
                changed = status == "INVALID"
                row = {**record, "ordinal": ordinal, "split": "TRAIN", "status": "SUCCESS",
                       "label": NORMAL_LABEL if changed else label, "original_status": status, "original_label": label,
                       "normalization_applied": changed, "completion_event": event["number"],
                       "run_id": source["run_id"], "attempt_id": source["attempt_id"], "hnlo_status": "N/A"}
                rows.append(row)
                if changed:
                    member = convert_record(archive, record, source, parent["cohort_sha256"], ordinal)
                    conversions.append({**row, "generated_label": row["label"], "raw_member": member,
                                        "archive": source["archive"], "archive_sha256": source["archive_sha256"]})

    require(len(rows) == len(samples), "Missing parent IDs")
    require(digest([r["raw_sha256"] for r in conversions]) == parent["invalid_raw_sha256_list_digest"],
            "INVALID raw SHA256 list digest mismatch")
    summary = {"before": summarize(rows, original=True), "after": summarize(rows, original=False),
               "converted": len(conversions)}
    payload = {"schema": f"safeshift-{PRODUCT}", "product_id": PRODUCT, "parent": parent,
               "sources": sources, "samples": rows}
    stats = [{"measure": key, "before": before, "after": summary["after"][key]}
             for key, before in summary["before"].items()]
    files = {"predictions.json": json_bytes(payload),
             "samples.csv": csv_bytes(({**r, "generated_label": r["label"]} for r in rows), SAMPLE_FIELDS),
             "conversions.csv": csv_bytes(conversions, CONVERSION_FIELDS),
             "summary.csv": csv_bytes(stats, ("measure", "before", "after"))}
    receipt = {"schema": f"safeshift-{PRODUCT}-receipt", "product_id": PRODUCT, "parent": parent,
               "owner_decision": DECISION, "tool_sha256": sha(__file__),
               "rule": {"key": "safety_level", "exact_value": NORMAL_DESCRIPTION, "label": NORMAL_LABEL},
               "summary": summary, "files": {name: {"sha256": hashlib.sha256(data).hexdigest(),
                                                   "size_bytes": len(data)} for name, data in files.items()}}
    return {**files, "receipt.json": json_bytes(receipt)}, receipt


def build(primary, mirror, output, *, parent=PARENT, repo=ROOT):
    primary, mirror, output, repo = map(Path, (primary, mirror, output, repo))
    for root in (primary, mirror):
        snapshot_stat(root, directory=True)
    require(primary.resolve() != mirror.resolve(), "Distinct primary and mirror required")
    relative = output.absolute().relative_to(repo.absolute() / "data/processed").as_posix()
    output = safe(repo, "data/processed/" + relative)
    for root in (primary.resolve(), mirror.resolve()):
        require(not output.resolve().is_relative_to(root) and not root.is_relative_to(output.resolve()),
                "Output overlaps source custody")
    files, receipt = products(primary, mirror, parent)
    if not output.exists():
        output.mkdir(parents=True, exist_ok=False)
        # The receipt is the last file. A partial directory has no valid receipt.
        for name, data in files.items():
            write_bytes(output / name, data)
    else:
        snapshot_stat(output, directory=True)
        require({p.name for p in output.iterdir()} == set(files), "Existing output files differ")
        for name, data in files.items():
            path = safe(output, name)
            snapshot_stat(path)
            require(path.read_bytes() == data, f"Existing output differs: {name}")
    return {**receipt, "receipt_sha256": hashlib.sha256(files["receipt.json"]).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--mirror", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed" / PRODUCT)
    args = parser.parse_args(argv)
    result = build(args.primary, args.mirror, args.output)
    print(json.dumps({"output": str(args.output), **result}, indent=2))


if __name__ == "__main__":
    main()
