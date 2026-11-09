"""TRAIN3763-only offline CPython Input, with no runtime download fallback.

The private dataset identity is a REQUIRED future publication, not a claim that
it exists. Actual metadata and independently downloaded bytes gate each submit.
Frozen Candidate160 source remains byte-identical.
"""
from contextlib import contextmanager
import base64
import hashlib
import os
from pathlib import Path
import shutil
import time
from urllib.parse import unquote, urlsplit

from safeshift.candidates.source import ROOT, require
from safeshift.candidates import train_python
from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest

REF = "nguynanhtn/safeshift-cpython3119-20240726/1"
MARKER = "safeshift_train3763_python.json"
PAYLOAD = "safeshift-cpython3119-base64.bin"
# RFC4648 standard alphabet, canonical padding, no whitespace, no compression.
# Independently computed from the unchanged, locally verified locked archive.
TRANSPORT = {"encoding": "base64-rfc4648-canonical-no-whitespace-v1",
    "filename": PAYLOAD, "size_bytes": 39617560,
    "sha256": "871cccab019cb6ef7417af6f3287233f3ba25e904fc007c429fdcb5e3a67b9f5"}
ENCODE_CHUNK = 49152  # multiple of three; decode chunks are exactly 65536 bytes
DECODE_CHUNK = 65536
LOCAL_SECONDS = 180


def manifest():
    lock = read(ROOT / "configs/candidate160/python3119.json")
    return {"schema": "train3763-python-input-v2", "ref": REF, "private": True,
        "filename": unquote(urlsplit(lock["url"]).path.rsplit("/", 1)[1]), "lock": lock,
        "transport": dict(TRANSPORT),
        "access": "OWNER_PRIVATE_CAMPAIGN_ONLY"}


def binding():
    return {"kind": "dataset_sources", "ref": REF, "private": True,
        "manifest_sha256": digest(manifest())}


def validate_binding(request):
    value = request["bindings"]["runtime"].get("python_input")
    require(type(value) is dict and digest(value) == digest(binding()), "EXACT_PRIVATE_PYTHON_INPUT_REQUIRED")
    require(request["bindings"]["dataset"]["dataset_sources"].count(REF) == 1,
        "ONE_PINNED_PYTHON_INPUT_REQUIRED")
    return value


def no_alias(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction())
        for p in (path, *path.parents)), "PYTHON_INPUT_PATH_ALIAS")
    require(not path.is_file() or path.stat().st_nlink == 1, "PYTHON_INPUT_HARDLINK")
    return path


def checked_bytes(path, size, expected_sha, deadline):
    """Bounded reads, including a final EOF check; never trust uploader hashes."""
    path = no_alias(path)
    require(path.is_file() and path.stat().st_size == size, "PYTHON_INPUT_SIZE")
    observed, total = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while True:
            require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
            block = stream.read(DECODE_CHUNK)
            if not block:
                break
            total += len(block)
            require(total <= size, "PYTHON_INPUT_SIZE")
            observed.update(block)
    require(total == size and observed.hexdigest() == expected_sha, "PYTHON_INPUT_SHA256")
    return {"sha256": expected_sha, "bytes": size}


def verify_archive(path, deadline=None):
    lock = manifest()["lock"]
    return checked_bytes(path, lock["size_bytes"], lock["sha256"],
        deadline if deadline is not None else time.monotonic() + LOCAL_SECONDS)


def encode(archive, target, deadline):
    """Verify original BEFORE creating payload. Preserve partials on failure."""
    verify_archive(archive, deadline)
    target = no_alias(target)
    size = manifest()["transport"]["size_bytes"]
    require(shutil.disk_usage(target.parent).free >= size, "PYTHON_INPUT_SCRATCH_SPACE")
    with Path(archive).open("rb") as source, target.open("xb") as out:
        total = 0
        while block := source.read(ENCODE_CHUNK):
            require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
            encoded = base64.b64encode(block)
            total += len(encoded)
            require(total <= size, "PYTHON_TRANSPORT_SIZE_BOUND")
            out.write(encoded)
        out.flush(); os.fsync(out.fileno())
    spec = manifest()["transport"]
    return checked_bytes(target, size, spec["sha256"], deadline)


def decode(payload, target, deadline):
    """Canonical, bounded streaming restore; verified archive is never executed here."""
    expected = manifest()
    spec, lock = expected["transport"], expected["lock"]
    checked_bytes(payload, spec["size_bytes"], spec["sha256"], deadline)
    target = no_alias(target)
    require(shutil.disk_usage(target.parent).free >= lock["size_bytes"], "PYTHON_INPUT_SCRATCH_SPACE")
    raw_hash, transport_hash = hashlib.sha256(), hashlib.sha256()
    raw_size, encoded_size = 0, 0
    with Path(payload).open("rb") as source, target.open("xb") as out:
        while block := source.read(DECODE_CHUNK):
            require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
            encoded_size += len(block)
            require(encoded_size <= spec["size_bytes"], "PYTHON_TRANSPORT_SIZE_BOUND")
            restored = base64.b64decode(block, validate=True)
            require(base64.b64encode(restored) == block and
                (b"=" not in block or encoded_size == spec["size_bytes"]), "PYTHON_TRANSPORT_CANONICAL")
            raw_size += len(restored)
            require(raw_size <= lock["size_bytes"], "PYTHON_DECODE_SIZE_BOUND")
            transport_hash.update(block); raw_hash.update(restored)
            out.write(restored)
        out.flush(); os.fsync(out.fileno())
    require(encoded_size == spec["size_bytes"] and transport_hash.hexdigest() == spec["sha256"],
        "PYTHON_TRANSPORT_SHA256")
    require(raw_size == lock["size_bytes"] and raw_hash.hexdigest() == lock["sha256"],
        "PYTHON_RESTORED_SHA256")
    # Re-read durable bytes, rather than only proving the buffers sent to write().
    return verify_archive(target, deadline)


def verify_directory(directory, deadline=None):
    directory = no_alias(directory)
    expected = manifest()
    entries = []
    for entry in directory.iterdir():
        entries.append(entry)
        require(len(entries) <= 2, "PYTHON_INPUT_EXACT_FILES")
    require(len(entries) == 2 and {p.name for p in entries} == {MARKER, expected["transport"]["filename"]},
        "PYTHON_INPUT_EXACT_FILES")
    marker = no_alias(directory / MARKER)
    require(marker.is_file() and marker.stat().st_size <= 16384, "PYTHON_INPUT_MARKER_BOUND")
    from safeshift.internvl3763 import _strict_json_loads
    require(digest(_strict_json_loads(marker.read_bytes())) == digest(expected), "PYTHON_INPUT_MANIFEST")
    spec = expected["transport"]
    payload = directory / spec["filename"]
    proof = checked_bytes(payload, spec["size_bytes"], spec["sha256"],
        deadline if deadline is not None else time.monotonic() + LOCAL_SECONDS)
    return payload, {"transport_sha256": proof["sha256"], "transport_bytes": proof["bytes"]}


def mounted(inputs, request, deadline=None):
    """Bounded legacy/current Kaggle mount layouts; no recursive file walk."""
    validate_binding(request)
    inputs = no_alias(inputs)
    matches = []
    from safeshift.candidates.train_inputs import mounts
    for child in mounts(inputs, limit=128):
        if child.is_dir() and (child / MARKER).exists():
            matches.append(child)
    require(len(matches) == 1, "ONE_PYTHON_INPUT_MOUNT_REQUIRED")
    directory = matches[0]
    owner, slug, _ = REF.split("/")
    require(directory.relative_to(inputs).as_posix() in (slug, "datasets/"+owner+"/"+slug),
        "PYTHON_INPUT_MOUNT_IDENTITY")
    # Kaggle Input is read-only. A writable copy/poisoned workspace is not Input.
    require(hasattr(os, "statvfs") and os.statvfs(directory).f_flag & os.ST_RDONLY,
        "PYTHON_INPUT_READ_ONLY_REQUIRED")
    return verify_directory(directory, deadline)


def stage(inputs, request, scratch, output, env, deadline):
    receipt = {"schema": "train3763-python-stage-v2", "status": "BLOCKED",
        "ref": REF, "python_downloads": 0, "model_calls": 0}
    try:
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
        payload, proof = mounted(inputs, request, deadline)
        receipt.update(proof)
        lock = manifest()["lock"]
        scratch = no_alias(scratch)
        require(shutil.disk_usage(no_alias(output)).free >= 2**20, "PYTHON_INPUT_OUTPUT_SPACE")
        require(shutil.disk_usage(scratch).free >= lock["max_uncompressed_bytes"] + lock["size_bytes"],
            "PYTHON_INPUT_SCRATCH_SPACE")
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
        archive = scratch / manifest()["filename"]
        receipt.update(decode(payload, archive, deadline))
        python, extraction = train_python.extract(archive, scratch / "input-cpython3119", lock)
        receipt["extraction"] = extraction
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
        probe = boot.probe_interpreter(python, env)
        receipt["probe"] = probe
        require(probe.get("eligible") and probe.get("version") == [3, 11, 9]
            and Path(probe["executable"]).resolve() == python.resolve(), "PYTHON_INPUT_INTERPRETER")
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
        receipt.update(status="PASS", selected_python=str(python))
        return python
    except BaseException as error:
        receipt["error"] = {"type": type(error).__name__, "code": str(error)[:500]}
        raise
    finally:
        write(Path(output) / "python-input.json", receipt)


@contextmanager
def selected_interpreter(python, scratch):
    """Process-local adapter around unchanged inherited setup primitives.

    Runs only in the dedicated serial setup child. Restrict ALL candidates,
    including inherited absolute/PATH candidates, to the verified extraction;
    allow the derived venv probe and explicitly disable the historical provider.
    No unittest.mock dependency and no global/environment source-lock override.
    """
    original_candidates, original_probe, original_provider = (
        boot.interpreter_candidates, boot.probe_interpreter, train_python.provision)
    allowed = {Path(python).absolute(), (Path(scratch) / "venv3119/bin/python").absolute()}
    def probe(candidate, env=None):
        if Path(candidate).absolute() not in allowed:
            return {"candidate": str(candidate), "eligible": False, "reason": "NOT_VERIFIED_INPUT_PYTHON"}
        return original_probe(candidate, env)
    def forbidden(*args, **kwargs):
        raise ValueError("TRAIN3763_PYTHON_DOWNLOAD_FORBIDDEN")
    boot.interpreter_candidates = lambda: [python]
    boot.probe_interpreter = probe
    train_python.provision = forbidden
    try:
        yield
    finally:
        boot.interpreter_candidates, boot.probe_interpreter, train_python.provision = (
            original_candidates, original_probe, original_provider)


def setup(request_path, output, scratch, inputs, deadline):
    from safeshift import internvl3763 as runtime
    from safeshift.fulltrain import provision
    from scripts import internvl_v2
    output, scratch = Path(output), Path(scratch)
    request = read(request_path)
    require(request["scope"] == "TRAIN3763_CAMPAIGN", "CAMPAIGN_PYTHON_ONLY")
    runtime.check_source(request["bindings"]["runtime"]["execution_request"]["source"])
    env = provision.clean_env(ROOT, scratch)
    python = stage(inputs, request, scratch, output, env, deadline)
    with selected_interpreter(python, scratch):
        internvl_v2.worker("setup", runtime.capture.source_spec(), output, scratch, inputs, deadline=deadline)
    observed = read(output / "runtime.json")
    require(Path(observed["python"]).absolute() == (scratch / "venv3119/bin/python").absolute(),
        "PYTHON_INPUT_SETUP_SELECTION")
