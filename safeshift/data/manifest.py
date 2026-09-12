"""InspecSafe-V1 manifest, restricted to notes/dataset_schema.md (sections 1–11, 15).

Only one annotation JSON is decoded at a time; imageData is immediately dropped.
No image pixels, polygon coordinates, or embedded image data enter the manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


FIELDS = (
    "sample_id", "point_id", "instance_id", "split", "data_type",
    "folder_domain", "text_domain", "domain_mismatch", "safety_level",
    "safety_level_int", "robot_platform", "image_relpath", "json_relpath",
    "txt_relpath", "text_description", "object_labels", "num_shapes",
    "image_width", "image_height", "image_format", "has_other_modalities",
)
SPLITS = ("train", "test")
DATA_TYPES = ("Normal_data", "Anomaly_data")
DOMAINS = ("coal_conveyor", "metallurgy", "oil_chemical", "power", "tunnel")
LEVELS = ("Level01", "Level02", "Level03", "Level04")
POINT_PATTERN = re.compile(
    r"(?P<folder_domain>[a-zA-Z0-9_]+)-(?P<safety_level>Level[0-9]{2})-"
    r"(?P<robot_platform>[a-zA-Z0-9_]+)-(?P<point_id>[0-9]{6})"
)

# All 24 actual opening clauses attested in schema section 15.3. Deliberately
# case-sensitive: new wording, whitespace or punctuation is unknown, not guessed.
TEXT_OPENINGS = {
    "coal_conveyor": (
        "In the coal conveyor bridge scene,",
        "In the coal conveyor bridge scenario,",
        "In the coal conveying trestle scenario,",
        "In the coal conveying bridge scenario,",
        "In the coal conveying trestle scene,",
        "In the coal transportation trestle scenario,",
        "In the coal transportation bridge scene,",
        "In the coal transportation bridge scenario,",
        "In the coal conveyor belt bridge scene,",
        "In the coal conveying bridge scene,",
        "In the coal conveyor gallery scene,",
    ),
    "metallurgy": ("In the metallurgical plant scene,", "In the metallurgical scene,"),
    "oil_chemical": (
        "In the oil, gas, and chemical plant scene,",
        "In the oil and gas chemical environment,",
        "In the oil and gas chemical scene,",
        "In the oil and gas chemical scenario,",
        "In the oil, gas, and chemical industry scenario,",
        "In the oil, gas, and chemical industry setting,",
        "In the oil, gas, and chemical industry scenarios,",
    ),
    "power": ("In the power facility scene,", "In the power scenario,"),
    "tunnel": ("In the tunnel scene,", "In the tunnel scenario,"),
}
W1_EXPECTED = {
    "total_samples": 5013, "train": 3763, "test": 1250,
    "domain_mismatch": 36, "JPEG": 4969, "PNG": 44,
    # Section 11's audit matrix assigns a text domain to all 5,013 samples.
    # Report coverage differences without widening the evidenced opening rules.
    "unknown_text_domain": 0,
}


class ManifestError(ValueError):
    """Controlled validation failure, with no dataset contents in the message."""


@dataclass
class BuildResult:
    rows: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    incomplete_malformed: int = 0
    structural_errors: int = 0
    discovered_samples: int = 0
    input_sha256: str = ""

    def summary(self) -> dict[str, Any]:
        splits = Counter(row["split"] for row in self.rows)
        types = Counter(row["data_type"] for row in self.rows)
        domains = Counter(row["folder_domain"] for row in self.rows)
        levels = Counter(row["safety_level"] for row in self.rows)
        formats = Counter(row["image_format"] for row in self.rows)
        return {
            "total_samples": len(self.rows),
            **{name: splits[name] for name in SPLITS},
            **{name: types[name] for name in DATA_TYPES},
            "folder_domain": {name: domains[name] for name in DOMAINS},
            "safety_level": {name: levels[name] for name in LEVELS},
            "domain_mismatch": sum(row["domain_mismatch"] is True for row in self.rows),
            "unknown_text_domain": sum(row["text_domain"] is None for row in self.rows),
            "JPEG": formats["JPEG"], "PNG": formats["PNG"],
            "incomplete_malformed": self.incomplete_malformed,
            "structural_errors": self.structural_errors,
            "discovered_samples": self.discovered_samples,
        }

    def discrepancies(self) -> list[str]:
        summary = self.summary()
        return [f"{key}: expected {value}, observed {summary[key]}"
                for key, value in W1_EXPECTED.items() if summary[key] != value]


def infer_text_domain(text: str) -> str | None:
    """Match only a documented opening, never keywords later in the description."""
    for domain, openings in TEXT_OPENINGS.items():
        if text.startswith(openings):
            return domain
    return None


def repository_path(path: Path, repo_root: Path) -> Path:
    """Resolve repository-relative inputs and reject paths escaping the root."""
    resolved = (repo_root / path).resolve()
    if not resolved.is_relative_to(repo_root.resolve()):
        raise ManifestError("path must stay inside the repository root")
    return resolved


def _digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _annotation(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        annotation = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise ManifestError("JSON cannot be parsed") from exc
    finally:
        del raw
    if not isinstance(annotation, dict):
        raise ManifestError("JSON top level must be an object")
    annotation.pop("imageData", None)
    # Release all other unused fields before validation or returning metadata.
    metadata = {key: annotation.get(key) for key in ("shapes", "imageWidth", "imageHeight")}
    del annotation
    for key in ("imageWidth", "imageHeight"):
        if type(metadata[key]) is not int or metadata[key] <= 0:
            raise ManifestError(f"{key} must be a positive integer")
    shapes = metadata.pop("shapes")
    if not isinstance(shapes, list):
        raise ManifestError("shapes must be an array")
    labels = []
    for index, shape in enumerate(shapes):
        if not isinstance(shape, dict) or not isinstance(shape.get("label"), str):
            raise ManifestError(f"shapes[{index}].label must be a string")
        labels.append(shape["label"])
    return {"image_width": metadata["imageWidth"], "image_height": metadata["imageHeight"],
            "object_labels": labels, "num_shapes": len(shapes)}, digest


def image_format_from_header(header: bytes) -> str:
    """Identify the two audited formats independently of filename extension."""
    if header.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if header[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    raise ManifestError("unrecognized image magic bytes (expected JPEG or PNG)")


def _image(path: Path) -> tuple[str, str]:
    with path.open("rb") as stream:
        header = stream.read(8)
        image_format = image_format_from_header(header)
        digest = hashlib.sha256(header)
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return image_format, digest.hexdigest()


def sample_metadata(point_dir: Path, stem: str, *, split: str, data_type: str) -> dict[str, str]:
    """Validate the audited naming convention, shared by inventory and quality checks."""
    match = POINT_PATTERN.fullmatch(point_dir.name)
    if not match:
        raise ManifestError("malformed folder name")
    metadata = match.groupdict()
    if metadata["folder_domain"] not in DOMAINS:
        raise ManifestError("folder domain is not documented in dataset_schema.md")
    if metadata["safety_level"] not in LEVELS:
        raise ManifestError("safety level is not documented in dataset_schema.md")
    if metadata["robot_platform"] not in ("SuspendedRail", "Wheeled"):
        raise ManifestError("robot platform is not documented in dataset_schema.md")
    if split not in SPLITS or data_type not in DATA_TYPES:
        raise ManifestError("invalid split or data_type")
    if not re.fullmatch(re.escape(point_dir.name) + r"-[0-9]{3}", stem):
        raise ManifestError("sample stem does not match folder name and instance pattern")
    return metadata


def parse_sample(
    point_dir: Path, stem: str, *, split: str, data_type: str, repo_root: Path,
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    """Validate one triplet and return a row plus relative file SHA-256 records."""
    metadata = sample_metadata(point_dir, stem, split=split, data_type=data_type)
    paths = {ext: point_dir / f"{stem}.{ext}" for ext in ("jpg", "json", "txt")}
    missing = [ext for ext, path in paths.items() if not path.is_file()]
    if missing:
        raise ManifestError(f"missing {', '.join(missing)}; triplet stems must match")
    for path in paths.values():
        repository_path(path, repo_root)
    annotation, json_digest = _annotation(paths["json"])
    image_format, image_digest = _image(paths["jpg"])
    text_bytes = paths["txt"].read_bytes()
    # bytes.decode preserves CRLF, BOM, trailing spaces and the final newline.
    text = text_bytes.decode("utf-8")
    text_digest = hashlib.sha256(text_bytes).hexdigest()
    text_domain = infer_text_domain(text)
    modalities = point_dir.parents[2] / "Other_modalities" / point_dir.name
    repository_path(modalities, repo_root)
    has_modalities = any(
        (modalities / f"{point_dir.name}-{suffix}").is_file()
        for suffix in ("visible.mp4", "infrared.mp4", "sensor.txt", "audio.wav")
    )
    relpaths = {ext: path.relative_to(repo_root).as_posix() for ext, path in paths.items()}
    row = {
        "sample_id": stem, **metadata, "instance_id": stem[-3:],
        "split": split, "data_type": data_type, "text_domain": text_domain,
        "domain_mismatch": None if text_domain is None else metadata["folder_domain"] != text_domain,
        "safety_level_int": int(metadata["safety_level"][-2:]),
        "image_relpath": relpaths["jpg"], "json_relpath": relpaths["json"],
        "txt_relpath": relpaths["txt"], "text_description": text,
        **annotation, "image_format": image_format, "has_other_modalities": has_modalities,
    }
    return row, [(relpaths[ext], digest) for ext, digest in
                 (("jpg", image_digest), ("json", json_digest), ("txt", text_digest))]


def iter_sample_candidates(dataset_root: Path, repo_root: Path, structural):
    """Yield (point directory, stem, split, type), reporting layout issues to a callback.

    Inventory the union of file stems, including orphan annotations. Directory
    enumeration failures propagate: callers cannot claim a complete audit then.
    """
    for split in SPLITS:
        annotations = dataset_root / split / "DATA_PATH" / split / "Annotations"
        repository_path(annotations, repo_root)
        if not annotations.is_dir():
            structural(annotations, "missing Annotations directory")
            continue
        for entry in sorted(annotations.iterdir()):
            if entry.name not in DATA_TYPES:
                structural(entry, "unexpected entry in Annotations")
        for data_type in DATA_TYPES:
            data_dir = annotations / data_type
            if not data_dir.is_dir():
                structural(data_dir, "missing data_type directory")
                continue
            for point_dir in sorted(data_dir.iterdir()):
                repository_path(point_dir, repo_root)
                if not point_dir.is_dir():
                    structural(point_dir, "expected point directory")
                    continue
                files = list(point_dir.iterdir())
                stems = sorted({path.stem for path in files if path.is_file()})
                for path in files:
                    if not path.is_file() or path.suffix not in (".jpg", ".json", ".txt"):
                        structural(path, "unexpected sample entry")
                if not stems:
                    structural(point_dir, "empty point directory")
                for stem in stems:
                    yield point_dir, stem, split, data_type


def collect_manifest(dataset_root: Path, repo_root: Path) -> BuildResult:
    """Collect every candidate error; refuse publication when any errors exist."""
    repo_root = repo_root.resolve()
    dataset_root = repository_path(dataset_root, repo_root)
    result = BuildResult()
    fingerprint = hashlib.sha256()
    seen: set[str] = set()

    def structural(path: Path, reason: str) -> None:
        result.errors.append(f"{path.relative_to(repo_root).as_posix()}: {reason}")
        result.structural_errors += 1

    for point_dir, stem, split, data_type in iter_sample_candidates(dataset_root, repo_root, structural):
        result.discovered_samples += 1
        try:
            row, records = parse_sample(
                point_dir, stem, split=split, data_type=data_type, repo_root=repo_root,
            )
            if stem in seen:
                raise ManifestError("duplicate sample_id")
            seen.add(stem)
        except (ManifestError, OSError, UnicodeError) as exc:
            reason = exc.strerror if isinstance(exc, OSError) else str(exc)
            if isinstance(exc, UnicodeError):
                reason = "TXT is not valid UTF-8"
            result.errors.append(
                f"{point_dir.relative_to(repo_root).as_posix()}/{stem}: {reason}"
            )
            result.incomplete_malformed += 1
            continue
        result.rows.append(row)
        for record in records:
            fingerprint.update(json.dumps(record, ensure_ascii=True).encode("ascii") + b"\n")
        fingerprint.update(json.dumps([stem, row["has_other_modalities"]]).encode("ascii") + b"\n")
    if result.discovered_samples == 0:
        structural(dataset_root, "no sample candidates found")
    result.input_sha256 = fingerprint.hexdigest()
    return result


def _csv_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, list)):
        return json.dumps(value, ensure_ascii=False)
    return value


def write_manifest(result: BuildResult, output: Path) -> None:
    """Publish an atomic UTF-8 CSV only after the entire inventory validates."""
    if result.errors:
        raise ManifestError("manifest not written because validation failed")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=output.parent, delete=False,
        ) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            for row in result.rows:
                writer.writerow({key: _csv_value(row[key]) for key in FIELDS})
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_provenance(result: BuildResult, dataset_root: Path, output: Path, repo_root: Path) -> None:
    """Record source fingerprint, runtime, source revisions and regeneration command."""
    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=repo_root, text=True, stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    dataset_rel = dataset_root.relative_to(repo_root).as_posix()
    output_rel = output.relative_to(repo_root).as_posix()
    sources = ("safeshift/data/manifest.py", "scripts/build_manifest.py", "notes/dataset_schema.md")
    created = datetime.now(timezone.utc)
    provenance = {
        "run_id": created.strftime("manifest-%Y%m%dT%H%M%S%fZ"),
        "created_utc": created.isoformat(),
        "dataset": "InspecSafe-V1", "dataset_root": dataset_rel,
        "source": "local extracted dataset; structure documented in notes/dataset_schema.md",
        "upstream_release": None, "upstream_url": None, "archive_checksums": None,
        "input_sha256": result.input_sha256,
        "input_sha256_method": "SHA-256 of UTF-8 JSON lines: [repo-relative path, full-file SHA-256] "
            "for jpg/json/txt per valid sample, then [sample_id, has_other_modalities]. "
            "Traversal: train/test, Normal_data/Anomaly_data, sorted point names and stems. "
            "Covers triplet bytes and modality presence; excludes archives and modality contents.",
        "git_commit": git("rev-parse", "HEAD"),
        "git_tracked_changes": git("diff", "HEAD", "--name-only"),
        "git_source_status": git("status", "--porcelain", "--", *sources),
        "source_sha256": {name: _digest_file(repo_root / name) for name in sources},
        "python": sys.version.split()[0], "os": platform.system(),
        "dependencies": "Python standard library only", "seed": None,
        "ordering": "deterministic; no random operations",
        "command": ["python", "scripts/build_manifest.py", "--dataset-root", dataset_rel, "--output", output_rel],
        "output": output_rel, "output_sha256": _digest_file(output),
        "summary": result.summary(), "w1_discrepancies": result.discrepancies(),
    }
    output.with_suffix(".provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
