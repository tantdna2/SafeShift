"""M2 saved-report boundary. M3 accepts only bundled synthetic bytes, no paths.

Archive checks operate in memory and never extract files. Native SUCCESS is
strict; normalized records separately support INVALID and missing-score tests.
Nothing in the reference artifact allowlist grants filesystem access.
"""

from collections import Counter
import csv
import hashlib
import io
import json
import math
from math import isfinite
from safeshift.evaluation.sensitivity import index_rows, join_reports, weighted_auc
from pathlib import Path
import re
import stat
import subprocess
import tarfile
import zipfile

from .schema import SAFETY_LEVELS
from .validation import validate_identifier, validate_relative_path

NOTICE = "SYNTHETIC — NOT RESEARCH RESULT"
MERGE = "28fdf82512577f2ed0fb435fb2c12b88e82baf2f"
CONFIG_PATH = "docs/research/seminar_analysis_config.v1.json"
PROTOCOL_PATH = "docs/research/SEMINAR_PROTOCOL.md"
AUTHORITY_PATH = "docs/research/m3_cpu_authority.v1.json"
CONFIG_SHA = "dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff"
PROTOCOL_SHA = "54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1"
AUTHORITY_SHA = "49acdb5d7fbbdd86fdfd2c6f8c2a1304d73033fc226f6294b2b6f7c66def89b6"
MODELS = ("qwen25", "internvl3", "qwen3")
STATUSES = ("SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED")


class AuthorityError(ValueError):
    """Missing effective decision or a denied execution capability."""


class IntegrityError(ValueError):
    """Content identity differs from the approved/bound bytes."""


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def strict_json(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError("nonfinite JSON number: " + value)

    return json.loads(payload, object_pairs_hook=pairs, parse_constant=nonfinite)


def checked(payload, expected, size=None):
    if sha256(payload) != expected or (size is not None and len(payload) != size):
        raise IntegrityError("SHA-256/size mismatch")
    return payload


def confined(root, relative, prefix=None):
    """Reject links/junctions at every existing ancestor, including output root."""
    validate_relative_path(relative, "path")
    if ":" in relative:
        raise ValueError("alternate data streams forbidden")
    parts = Path(relative).parts
    if prefix and tuple(parts[:len(prefix)]) != tuple(prefix):
        raise AuthorityError("path outside permitted root")
    root = Path(root).resolve()
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink() or (current.exists() and
                (getattr(current.lstat(), "st_file_attributes", 0) & 0x400)):
            raise AuthorityError("symlink/reparse point forbidden")
    if not current.resolve().is_relative_to(root):
        raise AuthorityError("path escape")
    return current


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    if result.returncode:
        raise AuthorityError("required Git evidence unavailable: " + " ".join(args))
    return result.stdout


def verify_authority(root, config_path=CONFIG_PATH):
    # Check spelling BEFORE opening anything; no caller-selected input payload.
    if config_path != CONFIG_PATH:
        raise AuthorityError("only the approved M2 config path is permitted")
    config_bytes = checked(confined(root, CONFIG_PATH).read_bytes(), CONFIG_SHA)
    protocol = checked(confined(root, PROTOCOL_PATH).read_bytes(), PROTOCOL_SHA)
    authority_bytes = checked(confined(root, AUTHORITY_PATH).read_bytes(), AUTHORITY_SHA)
    config, authority = strict_json(config_bytes), strict_json(authority_bytes)
    decision_path = "docs/research/DECISIONS.md"
    merged_decisions = git(root, "show", MERGE + ":" + decision_path)
    local_decisions = confined(root, decision_path).read_bytes()
    if not local_decisions.startswith(merged_decisions):
        raise AuthorityError("merged decisions absent or rewritten")
    records = [strict_json(x) for x in re.findall(rb"```json\s*\n(.*?)\n```", merged_decisions, re.S)]
    records = [r for r in records if r.get("decision_id") == "DEC-20261026-M2"]
    if len(records) != 1:
        raise AuthorityError("one merged M2 authority record required")
    decision = records[0]
    if (decision["status"] != "OWNER_APPROVED_FOR_PROJECT_SEMINAR"
            or decision["m3_scope"] != "CPU_SYNTHETIC_FIXTURES_ONLY"
            or authority["scope"] != decision["m3_scope"]
            or authority["merge_commit"] != MERGE or authority["merged"] is not True
            or authority["post_merge_verdict"] != "PASS" or authority["task_id"] != "M3-01"
            or not authority["task_grant_ref"] or not authority["post_merge_ref"]):
        raise AuthorityError("effective M2/post-merge/task grant required")
    denied = ("m4_real_artifact_access_granted",
              "gpu_inference_raw_replay_test_image_label_external_resource_access_granted",
              "thesis_execution_granted")
    if any(decision[k] is not False or authority[k] is not False for k in denied):
        raise AuthorityError("M3 must not gain real-data or execution permissions")
    if (decision["protocol"]["sha256"] != PROTOCOL_SHA
            or decision["config"]["sha256"] != CONFIG_SHA
            or config["protocol"]["sha256"] != sha256(protocol)):
        raise IntegrityError("decision/config/protocol binding mismatch")
    for path, expected in ((CONFIG_PATH, CONFIG_SHA), (PROTOCOL_PATH, PROTOCOL_SHA)):
        checked(git(root, "show", MERGE + ":" + path), expected)
    parents = git(root, "show", "-s", "--format=%P", MERGE).decode().strip().split()
    if parents != authority["merge_parents"]:
        raise AuthorityError("verified merge parents differ")
    git(root, "merge-base", "--is-ancestor", MERGE, "origin/main")
    git(root, "merge-base", "--is-ancestor", MERGE, "HEAD")
    evidence = config["evidence_lock"]
    checked(confined(root, evidence["path"]).read_bytes(), evidence["sha256"])
    return config, {"decision_id": decision["decision_id"], "merge_sha": MERGE,
                    "post_merge_ref": authority["post_merge_ref"],
                    "task_grant_ref": authority["task_grant_ref"], "scope": authority["scope"],
                    **{k: False for k in denied}, "protocol_sha256": PROTOCOL_SHA,
                    "config_sha256": CONFIG_SHA, "authority_sha256": AUTHORITY_SHA,
                    "merged_decision_sha256": sha256(merged_decisions),
                    "evidence_receipt_sha256": evidence["sha256"]}


def membership(ids):
    ids = list(ids)
    for sid in ids:
        validate_identifier(sid, "sample_id")
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate membership ID")
    return sha256("".join(s + "\n" for s in sorted(ids)).encode("utf-8"))


def archive_members(payload, expected_hash, members, kind):
    """Exact closed synthetic inventory; SHA/size/CRC; no extraction or links.

    `members` maps portable names to {sha256,size_bytes}. Nested archives must
    pass this function separately; checking the outer hash never replaces it.
    """
    checked(payload, expected_hash)
    for name in members:
        validate_relative_path(name, "member")
        if ":" in name:
            raise ValueError("invalid archive member")
    found = {}
    try:
        if kind == "zip":
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                infos = archive.infolist()
                for info in infos:
                    validate_relative_path(info.filename, "member")
                    mode = info.external_attr >> 16
                    if (info.filename in found or info.filename not in members
                            or info.is_dir() or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))):
                        raise ValueError("duplicate/unexpected/nonregular ZIP member")
                    spec = members[info.filename]
                    if info.file_size != spec["size_bytes"]:
                        raise IntegrityError("ZIP member size mismatch")
                    found[info.filename] = checked(archive.read(info), spec["sha256"], spec["size_bytes"])
        elif kind == "tar":
            with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
                for info in archive:
                    validate_relative_path(info.name, "member")
                    if info.name in found or info.name not in members or not info.isfile():
                        raise ValueError("duplicate/unexpected/nonregular TAR member")
                    spec = members[info.name]
                    if info.size != spec["size_bytes"]:
                        raise IntegrityError("TAR member size mismatch")
                    found[info.name] = checked(archive.extractfile(info).read(), spec["sha256"], info.size)
        else:
            raise ValueError("unknown archive kind")
    except (zipfile.BadZipFile, tarfile.TarError, EOFError) as exc:
        raise IntegrityError("archive/CRC failure") from exc
    if set(found) != set(members):
        raise ValueError("missing archive member")
    return found


def indexed(rows):
    table = {}
    for row in rows:
        sid = row["sample_id"]
        validate_identifier(sid, "sample_id")
        if sid in table:
            raise ValueError("duplicate sample ID")
        table[sid] = row
    return table


def validate_ledger(metadata, reports, config):
    """Exact planned joins; validation also protects direct metric callers."""
    meta = indexed(metadata)
    if set(reports) != set(MODELS):
        raise ValueError("exact three-model quantitative roster required")
    for row in meta.values():
        if row["split"] != "train" or row["true_level"] not in SAFETY_LEVELS or row["folder_domain"] not in config["domains"]:
            raise ValueError("TRAIN/canonical label/domain required")
    tables = {}
    for model, rows in reports.items():
        table = indexed(rows)
        if set(table) != set(meta):
            raise ValueError("exact planned ID equality required, including no-output rows")
        for sid, row in table.items():
            if row["schema_version"] != "safeshift-seminar-record-v1":
                raise ValueError("unsupported normalized record version")
            if any(row[k] != meta[sid][k] for k in ("split", "true_level", "folder_domain")):
                raise ValueError("exact label/domain/split join required")
            if row["model_id"] != model or row["evidence_level"] != "SYNTHETIC":
                raise AuthorityError("only synthetic normalized reports permitted in M3")
            if row["release"] != {"qwen25": "PA3_R2", "internvl3": "V4", "qwen3": "V4_ORIGINAL"}[model]:
                raise ValueError("release mismatch; Recovery224 cannot enter baseline")
            shard = row["shard"]
            if type(shard) is not int or shard not in range(4):
                raise ValueError("four original shard identities required")
            spec = config["models"][model]
            native = None if model == "qwen25" else spec["units"][shard]
            expected_revision = spec["revision"] if native is None else native["revision"]
            expected_run = "synthetic/" + (spec["run_ids"][shard] if native is None else native["run_id"])
            expected_attempt = None if native is None else "synthetic/" + native["attempt_id"]
            if (row["revision"] != expected_revision or row["run_id"] != expected_run
                    or row["attempt_id"] != expected_attempt or row["source_commit"] != MERGE
                    or row["config_sha256"] != CONFIG_SHA):
                raise IntegrityError("normalized source/revision/run/attempt/config mismatch")
            for key in ("revision", "run_id", "input_ref", "source_commit"):
                validate_identifier(row[key], key)
            if row["attempt_id"] is not None:
                validate_identifier(row["attempt_id"], "attempt_id")
            for key in ("attempted", "persisted", "parsed"):
                if type(row[key]) is not bool:
                    raise ValueError("boolean flags required")
            if row["native_status"] not in STATUSES:
                raise ValueError("unexpected native status")
            label, score = row["generated_label"], row["hnlo_score"]
            if label is not None and label not in SAFETY_LEVELS:
                raise ValueError("canonical prediction or explicit null required")
            if score is not None and (type(score) not in (int, float) or not math.isfinite(score)):
                raise ValueError("nonfinite score is an error, not missing")
            if row["native_status"] != "SUCCESS":
                if (row["persisted"] or row["parsed"] or label is not None or score is not None
                        or row["attempted"] != (row["native_status"] == "TECHNICAL_ERROR")):
                    raise ValueError("no-output row cannot become INVALID/Normal/score")
            elif (not row["attempted"] or not row["persisted"] or row["parsed"] != (label is not None)):
                raise ValueError("output/parse flags disagree")
            if label is None and not row["label_reason"]:
                raise ValueError("missing/INVALID label reason required")
            if score is None and not row["score_reason"]:
                raise ValueError("missing score reason required")
            if label is None and score is not None and row.get("score_independent_of_parse") is not True:
                raise ValueError("score on INVALID requires explicit synthetic contract")
        tables[model] = table
    return meta, tables


def read_unit(files, contract, metadata):
    """Synthetic analogue of native manifest/binding/result/ordered-ID checks.

    Expected identity comes from the caller's separately bound contract, never
    from the untrusted result itself. Native SUCCESS requires label AND score.
    """
    binding = strict_json(files["binding.json"])
    result = strict_json(files["result.json"])
    manifest = strict_json(files["manifest.json"])
    csv_payload = files["samples.csv"]
    expected_manifest = {k: {"sha256": sha256(v), "size_bytes": len(v)}
                         for k, v in files.items() if k != "manifest.json"}
    if manifest != expected_manifest or binding != contract or result["identity"] != contract["identity"]:
        raise IntegrityError("manifest/source/revision/run/attempt/config binding mismatch")
    if result["ordered_ids"] != contract["ordered_ids"]:
        raise ValueError("ordered result membership mismatch")
    reader = csv.DictReader(io.StringIO(csv_payload.decode("utf-8")))
    fields = ["sample_id", "true_level", "domain", "status", "generated_label", "pa3_score",
              "attempted", "persisted", "parsed"]
    if reader.fieldnames != fields:
        raise ValueError("exact native CSV schema required")
    rows = list(reader)
    ids = [r["sample_id"] for r in rows]
    if ids != contract["ordered_ids"] or len(set(ids)) != len(ids):
        raise ValueError("exact unique native ordered membership required")
    if len(result["journal"]) != len(rows):
        raise ValueError("journal membership mismatch")
    normalized = []
    for ordinal, row in enumerate(rows):
        if None in row or any(v is None for v in row.values()):
            raise ValueError("malformed CSV row")
        sid, status = row["sample_id"], row["status"]
        meta = metadata[sid]
        if (row["true_level"] != meta["true_level"] or row["domain"] != meta["folder_domain"]
                or contract["image_hashes"][ordinal] != meta["byte_sha256"]):
            raise ValueError("native label/domain/image identity mismatch")
        flags = [status != "NOT_ATTEMPTED", status == "SUCCESS", status == "SUCCESS"]
        journal = {"sample_id": sid, "ordinal": ordinal, "status": status,
                   **dict(zip(("attempted", "persisted", "parsed"), flags))}
        if (status not in STATUSES or result["journal"][ordinal] != journal
                or [row[k] for k in ("attempted", "persisted", "parsed")] != list(map(str, flags))):
            raise ValueError("native status/journal/flags mismatch")
        label, score = row["generated_label"], row["pa3_score"]
        if status == "SUCCESS":
            if label not in SAFETY_LEVELS or not score or not math.isfinite(float(score)):
                raise ValueError("native SUCCESS requires canonical label and finite score")
        elif label or score:
            raise ValueError("no-output native row contains prediction")
        normalized.append({"schema_version": "safeshift-seminar-record-v1",
                           **meta, **contract["identity"], "native_status": status,
                           **dict(zip(("attempted", "persisted", "parsed"), flags)),
                           "generated_label": label or None, "hnlo_score": float(score) if score else None,
                           "label_reason": None if label else status,
                           "score_reason": None if score else status,
                           "input_ref": contract["identity"]["run_id"] + "/samples.csv",
                           "evidence_level": "SYNTHETIC"})
    counts = {s: sum(r["status"] == s for r in rows) for s in STATUSES}
    if (result["status_counts"] != counts or result["planned"] != len(rows)
            or result["status"] != ("COMPLETE" if counts["SUCCESS"] == len(rows) else "PARTIAL")):
        raise ValueError("native coverage/status mismatch")
    return normalized


def synthetic_fixture(config):
    """Twelve hand-designed records; no images, real predictions or real IDs.

    Four units/model exercise source/run/attempt binding. A ZIP contains each
    TAR and a hash-bound sidecar; all containers are generated only in memory.
    """
    metadata, units = [], []
    truth = ["Level01", "Level04", "Level02", "Level04", "Level03", "Level04",
             "Level01", "Level04", "Level02", "Level04", "Level01", "Level04"]
    predictions = {
        "qwen25": ["Level04", "Level01", "Level02", "Level04", "Level01", "Level04",
                   "Level01", "Level02", "Level04", "Level04", "Level02", "Level04"],
        "internvl3": ["Level04", "Level04", "Level01", "Level04", "Level03", "Level04",
                     "Level02", "Level04", "Level02", "Level04", "Level01", "Level04"],
        "qwen3": ["Level04", "Level04", "Level02", "Level01", "Level03", "Level04",
                  "Level04", "Level04", "Level01", "Level04", None, None],
    }
    scores = [2, 1, 1, 0, 3, -1, 0, 0, 2, -2, 1, -1]
    for i, level in enumerate(truth):
        exact = 0 if i in (0, 1) else i
        metadata.append({"sample_id": f"synthetic-{i:02d}", "split": "train", "true_level": level,
                         "folder_domain": config["domains"][i % 5],
                         "byte_sha256": sha256(f"synthetic-byte-{exact}".encode()),
                         "pixel_sha256": sha256(f"synthetic-pixel-{exact}".encode()),
                         "point_id": "point-a" if i in (1, 2) else None,
                         "source_family": "family-a" if i in (2, 3) else None})
    for model in MODELS:
        spec = config["models"][model]
        for shard in range(4):
            ids = list(range(3 * shard, 3 * shard + 3))
            native = None if model == "qwen25" else spec["units"][shard]
            identity = {"model_id": model, "revision": spec["revision"] if native is None else native["revision"],
                        "release": spec["release"], "source_commit": MERGE,
                        "config_sha256": CONFIG_SHA, "shard": shard,
                        "run_id": "synthetic/" + (spec["run_ids"][shard] if native is None else native["run_id"]),
                        "attempt_id": None if native is None else "synthetic/" + native["attempt_id"]}
            contract = {"identity": identity, "ordered_ids": [metadata[i]["sample_id"] for i in ids],
                        "image_hashes": [metadata[i]["byte_sha256"] for i in ids]}
            native_rows, journal = [], []
            for ordinal, i in enumerate(ids):
                status = "TECHNICAL_ERROR" if model == "qwen3" and i == 10 else (
                    "NOT_ATTEMPTED" if model == "qwen3" and i == 11 else "SUCCESS")
                flags = {"attempted": status != "NOT_ATTEMPTED", "persisted": status == "SUCCESS",
                         "parsed": status == "SUCCESS"}
                native_rows.append({"sample_id": metadata[i]["sample_id"], "true_level": truth[i],
                                    "domain": metadata[i]["folder_domain"], "status": status,
                                    "generated_label": predictions[model][i] or "",
                                    "pa3_score": scores[i] + (0.5 if model == "internvl3" else 0) if status == "SUCCESS" else "",
                                    **flags})
                journal.append({"sample_id": metadata[i]["sample_id"], "ordinal": ordinal,
                                "status": status, **flags})
            stream = io.StringIO(newline="")
            writer = csv.DictWriter(stream, fieldnames=list(native_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(native_rows)
            result = {"identity": identity, "ordered_ids": contract["ordered_ids"], "journal": journal,
                      "planned": len(ids), "status": "PARTIAL" if model == "qwen3" and shard == 3 else "COMPLETE",
                      "status_counts": {s: sum(r["status"] == s for r in native_rows) for s in STATUSES}}
            files = {"binding.json": json_bytes(contract), "result.json": json_bytes(result),
                     "samples.csv": stream.getvalue().encode()}
            files["manifest.json"] = json_bytes(inventory(files))
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
                for name, data in sorted(files.items()):
                    entry = tarfile.TarInfo(name)
                    entry.size = len(data)
                    archive.addfile(entry, io.BytesIO(data))
            tar = tar_buffer.getvalue()
            outer_files = {"unit.tar": tar, "export.json": json_bytes({"identity": identity,
                           "archive_sha256": sha256(tar), "archive_size": len(tar), "members": inventory(files)})}
            outer = io.BytesIO()
            with zipfile.ZipFile(outer, "w") as archive:
                for name, data in sorted(outer_files.items()):
                    archive.writestr(zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0)), data)
            units.append({"contract": contract, "payload": outer.getvalue(),
                          "sha256": sha256(outer.getvalue()), "members": inventory(outer_files),
                          "inner_members": inventory(files)})
    return metadata, units, [("synthetic-03", "synthetic-04", 8)]


def inventory(files):
    return {k: {"sha256": sha256(v), "size_bytes": len(v)} for k, v in sorted(files.items())}


def read_synthetic(config):
    metadata, units, near = synthetic_fixture(config)
    meta = indexed(metadata)
    reports, receipts, seen = {m: [] for m in MODELS}, [], set()
    for unit in units:
        identity = unit["contract"]["identity"]
        key = (identity["model_id"], identity["shard"])
        if key in seen:
            raise ValueError("duplicate model/unit")
        seen.add(key)
        outer = archive_members(unit["payload"], unit["sha256"], unit["members"], "zip")
        export = strict_json(outer["export.json"])
        if (export["identity"] != identity or export["members"] != unit["inner_members"]
                or export["archive_size"] != len(outer["unit.tar"])):
            raise IntegrityError("outer sidecar identity/member binding mismatch")
        files = archive_members(outer["unit.tar"], export["archive_sha256"], export["members"], "tar")
        reports[identity["model_id"]].extend(read_unit(files, unit["contract"], meta))
        receipts.append({"identity": identity, "zip_sha256": unit["sha256"],
                         "zip_members": unit["members"], "tar_sha256": export["archive_sha256"],
                         "members": export["members"], "zip_crc": "PASS"})
    if seen != {(m, s) for m in MODELS for s in range(4)}:
        raise ValueError("four original units per quantitative model required")
    validate_ledger(metadata, reports, config)
    return metadata, reports, near, {"metadata_sha256": sha256(json_bytes(metadata)),
                                    "near_edges_sha256": sha256(json_bytes(near)), "units": receipts}


# Native saved-report adapters reused from the reviewed main CLI.
# Bytes only: these helpers do not open artifact paths or grant M4 access.

def report_rows(payload):
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError("unique CSV headers required")
    rows = list(reader)
    if any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("malformed CSV row")
    return rows


def auc_matches(actual, expected):
    if actual is None or expected is None:
        return actual is expected
    return type(expected) in (int, float) and isfinite(expected) and abs(actual - expected) <= 1e-12


def internvl_rows(payload, expected_members):
    rows = []
    with zipfile.ZipFile(io.BytesIO(payload)) as outer:
        seen = set()
        for info in outer.infolist():
            validate_relative_path(info.filename.rstrip("/"), "ZIP member")
            if (info.filename in seen or ":" in info.filename
                    or stat.S_IFMT(info.external_attr >> 16) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("unsafe/duplicate ZIP member")
            seen.add(info.filename)
        names = [n for n in outer.namelist() if n.endswith(".tar.gz")]
        if len(names) != len(set(names)) or set(names) != set(expected_members):
            raise ValueError("exact unique receipt archive members required")
        for name in sorted(names):
            found = []
            with tarfile.open(fileobj=io.BytesIO(outer.read(name)), mode="r|gz") as archive:
                seen = set()
                for member in archive:
                    validate_relative_path(member.name.rstrip("/"), "TAR member")
                    if member.name in seen or ":" in member.name or not (member.isfile() or member.isdir()):
                        raise ValueError("unsafe/duplicate TAR member")
                    seen.add(member.name)
                    if member.name == "evidence/report/samples.csv":
                        if not member.isfile():
                            raise ValueError("report must be a regular archive member")
                        found.append(archive.extractfile(member).read())
            if len(found) != 1 or hashlib.sha256(found[0]).hexdigest() != expected_members[name]:
                raise ValueError("unique samples member with receipt checksum required")
            rows.extend(report_rows(found[0]))
    return rows


def verified_archive_members(payload, export, names):
    """Read only an explicit metadata/report allowlist, bound to the inventory."""
    if (len(payload) != export["archive_bytes"]
            or hashlib.sha256(payload).hexdigest() != export["archive_sha256"]):
        raise ValueError("Qwen3 archive checksum/size mismatch")
    found = {}
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r|gz") as archive:
        seen = set()
        for member in archive:
            validate_relative_path(member.name.rstrip("/"), "TAR member")
            if member.name in seen or ":" in member.name or not (member.isfile() or member.isdir()):
                raise ValueError("unsafe/duplicate TAR member")
            seen.add(member.name)
            if member.name in {"manifest.json", *names}:
                if member.name in found or not member.isfile():
                    raise ValueError("unique regular manifest/report members required")
                found[member.name] = archive.extractfile(member).read()
    if set(found) != {"manifest.json", *names}:
        raise ValueError("missing Qwen3 manifest/report")
    if hashlib.sha256(found["manifest.json"]).hexdigest() != export["manifest_sha256"]:
        raise ValueError("Qwen3 manifest checksum mismatch")
    entries = strict_json(found["manifest.json"])["files"]
    for entry in entries:
        validate_relative_path(entry["path"], "inventory path")
    inventory = {entry["path"]: entry for entry in entries}
    if len(inventory) != len(entries):
        raise ValueError("unique inventory paths required")
    for name in names:
        entry = inventory[name.removeprefix("evidence/")]
        if len(found[name]) != entry["size_bytes"] or hashlib.sha256(found[name]).hexdigest() != entry["sha256"]:
            raise ValueError("Qwen3 saved metadata/report inventory mismatch")
    return found


def archive_report(payload, result):
    """Bind complete saved reports; this is never raw-logit replay/PASS."""
    found = verified_archive_members(payload, result["export"], {"evidence/report/samples.csv"})
    saved = found["evidence/report/samples.csv"]
    rows = report_rows(saved)
    table = index_rows(rows, "true_level")
    expected = result["metrics"]["overall"]["auroc_pa3"]
    if (len(expected["eligible_ids"]) != len(set(expected["eligible_ids"]))
            or set(table) != set(expected["eligible_ids"])):
        raise ValueError("Qwen3 report/result exact eligible IDs required")
    actual = weighted_auc([r["true_level"] != "Level04" for r in rows],
                          [float(r["pa3_score"]) for r in rows])
    if not auc_matches(actual, expected["value"]):
        raise ValueError("Qwen3 saved-score AUROC differs from pinned result")
    return rows, {"archive_sha256": result["export"]["archive_sha256"],
                  "manifest_sha256": result["export"]["manifest_sha256"], "samples_sha256": hashlib.sha256(saved).hexdigest(),
                  "n_saved_rows": len(rows), "run_id": result["unit"]["run_id"]}


def verify_v4_shard(payload, result, expected_unit, inference, scope, train_metadata):
    """Validate all planned rows/statuses before selecting SUCCESS for AUROC."""
    unit = result["unit"]
    if unit != expected_unit or unit["model"] != "qwen3" or result["export"]["unit"] != unit:
        raise ValueError("original V4 unit identity required; recovery/rerun pooling forbidden")
    found = verified_archive_members(payload, result["export"],
                                     {"evidence/report/samples.csv", "evidence/binding.json", "evidence/result.json"})
    binding = json.loads(found["evidence/binding.json"])
    inside = json.loads(found["evidence/result.json"])
    if inside != {k: v for k, v in result.items() if k != "export"}:
        raise ValueError("internal and external result mismatch")
    if (binding["unit"] != unit or binding["authority"]["scope"] != scope
            or binding["samples"] != inference):
        raise ValueError("V4 config or historical ordered shard membership mismatch")
    if (result["schema"] != "hnlo-train-unit-result-v1" or result["scope"] != "DESCRIPTIVE_FULL_TRAIN"
            or result["retry"] is not False or result["research_generalization_claim"] is not False):
        raise ValueError("original V4 result scope mismatch")
    rows = report_rows(found["evidence/report/samples.csv"])
    table = index_rows(rows, "true_level")
    planned = [r["sample_id"] for r in inference]
    if (len(set(planned)) != len(planned) or len(planned) != unit["count"]
            or [r["sample_id"] for r in rows] != planned):
        raise ValueError("exact planned report IDs/order required")
    journal = result["sample_journal"]
    if [r["sample_id"] for r in journal] != planned or [r["ordinal"] for r in journal] != list(range(len(planned))):
        raise ValueError("exact journal membership/order required")
    statuses = Counter()
    for position, row in enumerate(rows):
        sid, status = row["sample_id"], row["status"]
        meta = train_metadata[sid]
        if (row["true_level"] != meta["safety_level"] or row["domain"] != meta["folder_domain"]
                or inference[position]["image_sha256"] != meta["byte_sha256"]
                or row["true_binary_label"] != ("Normal" if row["true_level"] == "Level04" else "Anomaly")):
            raise ValueError("planned ID/ground truth/domain/image-hash mismatch")
        if status not in {"SUCCESS", "TECHNICAL_ERROR", "NOT_ATTEMPTED"}:
            raise ValueError("unexpected V4 status")
        flags = (status != "NOT_ATTEMPTED", status == "SUCCESS", status == "SUCCESS")
        entry = journal[position]
        if (entry["status"] != status
                or tuple(row[k] for k in ("attempted", "persisted", "parsed")) != tuple(str(x) for x in flags)
                or tuple(entry[k] for k in ("attempted", "persisted", "parsed")) != flags):
            raise ValueError("saved status/journal/flags mismatch")
        if status != "SUCCESS" and (row["pa3_score"] != "" or row["generated_label"] != ""):
            raise ValueError("non-success row must not become a scored prediction")
        statuses[status] += 1
    saved_coverage = result["coverage"]
    expected_counts = {key: statuses[key] for key in saved_coverage["status_counts"]}
    if (set(statuses) - set(expected_counts) or saved_coverage["status_counts"] != expected_counts
            or saved_coverage["planned"] != len(rows) or saved_coverage["scored"] != statuses["SUCCESS"]
            or saved_coverage["attempted"] != statuses["SUCCESS"] + statuses["TECHNICAL_ERROR"]
            or saved_coverage["parsed"] != statuses["SUCCESS"] or saved_coverage["persisted"] != statuses["SUCCESS"]
            or saved_coverage["anomaly_n"] != sum(r["true_level"] != "Level04" for r in rows)
            or saved_coverage["normal_n"] != sum(r["true_level"] == "Level04" for r in rows)
            or saved_coverage["level_counts"] != dict(Counter(r["true_level"] for r in rows))
            or abs(saved_coverage["coverage"] - statuses["SUCCESS"] / len(rows)) > 1e-12
            or result["status"] != ("COMPLETE" if statuses["SUCCESS"] == len(rows) else "PARTIAL")):
        raise ValueError("saved coverage/counts mismatch")
    success = [r for r in rows if r["status"] == "SUCCESS"]
    metadata = [train_metadata[r["sample_id"]] for r in success]
    join_reports(metadata, {"qwen3": success})
    expected = result["metrics"]["overall"]["auroc_pa3"]
    positives = sum(r["true_level"] != "Level04" for r in success)
    negatives = len(success) - positives
    auc = weighted_auc([r["true_level"] != "Level04" for r in success], [float(r["pa3_score"]) for r in success])
    for endpoint in (expected, saved_coverage["auroc"]):
        ids = endpoint["eligible_ids"]
        if (len(set(ids)) != len(ids) or set(ids) != {r["sample_id"] for r in success}
                or endpoint["positive_n"] != positives or endpoint["negative_n"] != negatives
                or endpoint["pair_denominator"] != positives * negatives or endpoint["tie_credit"] != 0.5
                or not auc_matches(auc, endpoint["value"])):
            raise ValueError("saved eligible IDs/support/AUROC mismatch")
    return rows, {
        "status": "PASS_SAVED_SCORE_NOT_RAW_AUDIT", "unit": unit,
        "archive_sha256": result["export"]["archive_sha256"], "archive_size_bytes": len(payload),
        "manifest_sha256": result["export"]["manifest_sha256"],
        "members": {name: {"sha256": hashlib.sha256(b).hexdigest(), "size_bytes": len(b)}
                    for name, b in found.items()},
        "source": {k: binding["source"][k] for k in
                   ("implementation_commit", "authority_commit", "merge_commit", "payload_sha256", "pr_number")},
        "planned_n": len(rows), "status_counts": dict(sorted(statuses.items())),
        "success_positive_n": positives, "success_negative_n": negatives, "auroc_recomputed": auc,
        "ordered_ids_and_image_hashes_match_history": True, "config_scope_matches_history": True,
    }
