"""Sealed synthetic saved-result fixtures -> unchanged T2 input types.

No filesystem/network/model I/O and no real-data activation switch. Integrity
checks are not data rights or scientific approval. See docs/TRIAGE_ADAPTER.md.
"""

from dataclasses import dataclass, fields
import hashlib
import json
import math
import re

from safeshift.evaluation.triage import (
    ClassifiedResult, HNLOSignal, ModelResults, SourceIdentity,
)


# Reviewed, wholly handwritten fixture content, not caller-provided trust roots.
# Adding a fixture requires a source change and review. No runtime registration.
_FIXTURE_SEALS = frozenset({
    "9fcdcf4a31e14be7ac259c7514c3a2cfc39e70cd9edd08c8f4ed1ffeed4e9b87",  # complete
    "d29e09bf3bb41fbf36195149e2ffd29e389d268aa9100597a97470643b3570df",  # missing_row
    "25b81f3d459afc37fe17fc2e437f08d8328abc45f8bc8fd0164c856e69183d83",  # missing_model
    "8034cadeff519ae47026ba84a4a3f3bbedd92adaeba22207da960e42e94afcd3",  # invalid
    "5430f670d6ab2103aa91fb47b972eddedf3485993852b3cd5a81b444bd077e91",  # technical_error
    "48633ecc0544defb195923665202adf8df9c49e51ad831656d37894e0189e16e",  # not_attempted
    "3873ee6880a142a31bb47562849310eec5ec26a0d5a675c7a14b8060969a143e",  # focal_invalid
    "2ffbef4d4037d02c2cbf047e6f2dafa078fa3b54f9aec9531f83575800e7ae7b",  # hnlo_missing
    "0b6db3d12d8e4784f61a6976fc79a7ed7b1ee212ab4dd9d5342c4507b480d494",  # hnlo_ineligible
})


def _canonical(value):
    """Strict JSON values; all arrays in this contract are unordered collections."""
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise ValueError("fixture object keys must be strings")
        return {k: _canonical(v) for k, v in sorted(value.items())}
    if type(value) is list:
        return sorted((_canonical(v) for v in value),
                      key=lambda v: json.dumps(v, sort_keys=True, allow_nan=False))
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise ValueError("expected finite strict JSON fixture content; no paths/objects/NaN/Infinity")


def fixture_sha256(value) -> str:
    """Hash canonical UTF-8 JSON (sorted keys/collections, compact, ASCII escaped).

    This is a content checksum, never an authorization or fixture registration.
    """
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _object(value, keys, context):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError(f"{context}: exact required fields missing or unexpected")


def _text(value, context):
    if type(value) is not str or re.fullmatch(r"[a-zA-Z0-9_.-]{1,100}", value) is None:
        raise ValueError(f"{context}: expected sanitized public fixture identifier")


def _hash(value, context):
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{context}: expected SHA256")


def _index(rows, key, context):
    if type(rows) is not list:
        raise ValueError(f"{context}: expected list")
    result = {}
    for row in rows:
        if type(row) is not dict or type(row.get(key)) is not str:
            raise ValueError(f"{context}: missing {key}")
        if row[key] in result:
            raise ValueError(f"{context}: duplicate {key}")
        result[row[key]] = row
    return result


def _identity(value):
    names = " ".join(f.name for f in fields(SourceIdentity))
    _object(value, names, "identity")
    for name, item in value.items():
        _text(item, name)
    return SourceIdentity(**value)


def _planned(value):
    if type(value) is not list or any(
        type(s) is not str or re.fullmatch(r"[0-9a-f]{32}", s) is None for s in value
    ):
        raise ValueError("planned_ids: expected preassigned opaque tokens")
    if len(set(value)) != len(value):
        raise ValueError("duplicate planned ID")
    return tuple(sorted(value))


@dataclass(frozen=True)
class VerifiedSource:
    """Fixture integrity receipt, kept separately from ranking features."""

    source_id: str
    identity: SourceIdentity
    report_sha256: str
    row_sha256: tuple[tuple[str, str], ...]
    missing_ids: tuple[str, ...]


@dataclass(frozen=True)
class AdaptedInputs:
    planned_ids: tuple[str, ...]
    focal: ModelResults
    peers: tuple[ModelResults, ...]
    sources: tuple[VerifiedSource, ...]
    input_sha256: tuple[tuple[str, str], ...]
    evidence_sha256: tuple[str, ...]
    manifest_sha256: str
    selection_sha256: str
    fixture_sha256: str


def adapt_synthetic_bundle(bundle: dict) -> AdaptedInputs:
    """Validate one sealed fixture and project it to T2, without choosing runs.

    Absent rows are retained as missing IDs; T2 emits MISSING. Missing report
    identity/selection evidence is an error, even for an entirely absent model.
    Callers must provide exactly one externally selected report per model.
    Unregistered content is rejected even with internally consistent hashes.
    """
    if type(bundle) is not dict:
        raise ValueError("only sealed in-memory synthetic fixtures; real-data paths refused")
    # Detached strict-JSON snapshot: no arbitrary Python objects or input mutation.
    b = _canonical(bundle)
    _object(b, "manifest inputs reports selection evidence", "bundle")
    manifest = b["manifest"]
    _object(manifest, "schema planned_ids samples sources", "manifest")
    if manifest["schema"] != "safeshift-t3-synthetic-v1":
        raise ValueError("unsupported fixture schema; real data is not enabled")
    planned = _planned(manifest["planned_ids"])
    samples = _index(manifest["samples"], "sample_id", "manifest samples")
    inputs = _index(b["inputs"], "sample_id", "inputs")
    if set(samples) != set(planned) or set(inputs) != set(planned):
        raise ValueError("manifest/input planned cohort mismatch")
    for sid in planned:
        _object(samples[sid], "sample_id input_sha256", "sample")
        _object(inputs[sid], "sample_id content", "input")
        _hash(samples[sid]["input_sha256"], "input_sha256")
        content = inputs[sid]["content"]
        if type(content) is not str:
            raise ValueError("fixture input content must be text")
        if hashlib.sha256(content.encode("utf-8")).hexdigest() != samples[sid]["input_sha256"]:
            raise ValueError("input checksum mismatch")

    sources = _index(manifest["sources"], "source_id", "manifest sources")
    reports = _index(b["reports"], "source_id", "reports (external selection required)")
    selection = b["selection"]
    _object(selection, "selection_id authority_id rule manifest_sha256 entries", "selection")
    for name in ("selection_id", "authority_id"):
        _text(selection[name], name)
    if selection["rule"] != "EXPLICIT_FIXTURE_SELECTION_NO_POOLING":
        raise ValueError("external exact selection required; no latest/best/recovery policy")
    if selection["manifest_sha256"] != fixture_sha256(manifest):
        raise ValueError("selection manifest checksum mismatch")
    entries = _index(selection["entries"], "source_id", "selection entries")
    if len(sources) != 3 or set(sources) != set(reports) or set(sources) != set(entries):
        raise ValueError("exactly three sources/reports/selection entries required")
    evidence = {}
    if type(b["evidence"]) is not list:
        raise ValueError("evidence must be a list")
    for proof in b["evidence"]:
        digest = fixture_sha256(proof)
        if digest in evidence:
            raise ValueError("duplicate HNLO evidence")
        evidence[digest] = proof
    used_evidence = set()
    streams, receipts, roles = {}, [], {}
    model_ids = set()
    for source_id in sorted(sources):
        _text(source_id, "source_id")
        spec, report, entry = sources[source_id], reports[source_id], entries[source_id]
        _object(spec, "source_id role identity report_sha256", "source specification")
        _object(report, "source_id identity planned_ids rows", "report")
        _object(entry, "source_id identity report_sha256", "selection entry")
        identity = _identity(spec["identity"])
        if identity.model_id in model_ids:
            raise ValueError("model IDs must be distinct")
        model_ids.add(identity.model_id)
        if spec["role"] not in ("focal", "peer"):
            raise ValueError("source role must be focal or peer")
        roles[source_id] = spec["role"]
        if _identity(report["identity"]) != identity or _identity(entry["identity"]) != identity:
            raise ValueError("report/selection identity mismatch")
        if _planned(report["planned_ids"]) != planned:
            raise ValueError("report planned cohort mismatch")
        digest = fixture_sha256(report)
        if spec["report_sha256"] != digest or entry["report_sha256"] != digest:
            raise ValueError("report checksum mismatch")
        rows = _index(report["rows"], "sample_id", "report rows")
        if not set(rows) <= set(planned):
            raise ValueError("result ID outside planned cohort")
        converted = []
        for sid in sorted(rows):
            row = rows[sid]
            _object(row, "sample_id identity input_sha256 status predicted_safety_level hnlo", "row")
            if _identity(row["identity"]) != identity:
                raise ValueError("row identity mismatch: mixed model/revision/config/run/series/attempt")
            if row["input_sha256"] != samples[sid]["input_sha256"]:
                raise ValueError("row input checksum mismatch across models")
            signal = None
            h = row["hnlo"]
            if h is not None:
                if spec["role"] != "focal":
                    raise ValueError("peer HNLO forbidden, including MiniCPM")
                _object(h, "state value evidence_sha256", "HNLO")
                state, score, ref = h["state"], h["value"], h["evidence_sha256"]
                if state not in ("VALID", "MISSING", "INELIGIBLE"):
                    raise ValueError("HNLO state invalid")
                if state == "MISSING":
                    if score is not None or ref is not None:
                        raise ValueError("MISSING HNLO must have null value/evidence")
                else:
                    if type(score) not in (int, float):
                        raise ValueError("HNLO must be a finite number without coercion")
                    try:
                        finite = math.isfinite(score)
                    except OverflowError:
                        finite = False
                    if not finite:
                        raise ValueError("HNLO must be finite")
                if state == "VALID":
                    _hash(ref, "HNLO evidence_sha256")
                    expected_proof = {
                        "sample_id": sid, "identity": row["identity"],
                        "input_sha256": row["input_sha256"], "value": score,
                        "qualification": "SYNTHETIC_UPSTREAM_VALIDATED",
                    }
                    if evidence.get(ref) != expected_proof:
                        raise ValueError("missing or conflicting HNLO evidence")
                    if row["status"] != "SUCCESS":
                        raise ValueError("VALID HNLO requires SUCCESS")
                    used_evidence.add(ref)
                elif ref is not None:
                    raise ValueError("unqualified HNLO cannot claim evidence")
                signal = HNLOSignal(score, state == "VALID")
            converted.append(ClassifiedResult(sid, row["status"], row["predicted_safety_level"], signal))
        streams[source_id] = ModelResults(identity, tuple(converted))
        receipts.append(VerifiedSource(source_id, identity, digest,
                        tuple((sid, fixture_sha256(rows[sid])) for sid in sorted(rows)),
                        tuple(sorted(set(planned) - set(rows)))))
    if list(roles.values()).count("focal") != 1:
        raise ValueError("exactly one focal and two peers required")
    if used_evidence != set(evidence):
        raise ValueError("unreferenced HNLO evidence")
    seal = fixture_sha256(b)
    if seal not in _FIXTURE_SEALS:
        raise ValueError("unregistered synthetic fixture; real-data activation is unavailable")
    focal_id = next(s for s in roles if roles[s] == "focal")
    peers = tuple(sorted((streams[s] for s in roles if roles[s] == "peer"),
                         key=lambda s: s.identity.model_id))
    return AdaptedInputs(planned, streams[focal_id], peers, tuple(receipts),
                         tuple((sid, samples[sid]["input_sha256"]) for sid in planned),
                         tuple(sorted(evidence)), fixture_sha256(manifest),
                         fixture_sha256(selection), seal)
