"""TRAIN3763-only offline CPython Input, with no runtime download fallback.

The private dataset identity is a REQUIRED future publication, not a claim that
it exists. Actual metadata and independently downloaded bytes gate each submit.
Frozen Candidate160 source remains byte-identical.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import time
from urllib.parse import unquote, urlsplit

from safeshift.candidates.source import ROOT, require
from safeshift.candidates import train_python
from safeshift.pilot import bootstrap as boot
from safeshift.pilot.artifacts import read, sha, write
from safeshift.pilot.contract import digest

REF = "nguynanhtn/safeshift-cpython3119-20240726/1"
MARKER = "safeshift_train3763_python.json"


def manifest():
    lock = read(ROOT / "configs/candidate160/python3119.json")
    return {"schema": "train3763-python-input-v1", "ref": REF, "private": True,
        "filename": unquote(urlsplit(lock["url"]).path.rsplit("/", 1)[1]), "lock": lock,
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
    return path


def verify_archive(path):
    path = no_alias(path)
    lock = manifest()["lock"]
    require(path.is_file() and path.stat().st_size == lock["size_bytes"], "PYTHON_INPUT_SIZE")
    require(sha(path) == lock["sha256"], "PYTHON_INPUT_SHA256")
    return {"sha256": lock["sha256"], "bytes": lock["size_bytes"]}


def verify_directory(directory):
    directory = no_alias(directory)
    expected = manifest()
    entries = []
    for entry in directory.iterdir():
        entries.append(entry)
        require(len(entries) <= 2, "PYTHON_INPUT_EXACT_FILES")
    require(len(entries) == 2 and {p.name for p in entries} == {MARKER, expected["filename"]},
        "PYTHON_INPUT_EXACT_FILES")
    marker = no_alias(directory / MARKER)
    require(marker.is_file() and marker.stat().st_size <= 16384, "PYTHON_INPUT_MARKER_BOUND")
    from safeshift.internvl3763 import _strict_json_loads
    require(digest(_strict_json_loads(marker.read_bytes())) == digest(expected), "PYTHON_INPUT_MANIFEST")
    archive = directory / expected["filename"]
    return archive, verify_archive(archive)


def mounted(inputs, request):
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
    return verify_directory(directory)


def stage(inputs, request, scratch, output, env, deadline):
    receipt = {"schema": "train3763-python-stage-v1", "status": "BLOCKED",
        "ref": REF, "python_downloads": 0, "model_calls": 0}
    try:
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
        archive, proof = mounted(inputs, request)
        receipt.update(proof)
        lock = manifest()["lock"]
        scratch = no_alias(scratch)
        require(shutil.disk_usage(scratch).free >= lock["max_uncompressed_bytes"] + lock["size_bytes"],
            "PYTHON_INPUT_SCRATCH_SPACE")
        require(time.monotonic() < deadline, "PYTHON_INPUT_DEADLINE")
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
