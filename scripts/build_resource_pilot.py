"""Build two pilot-only Run All notebooks and their independent byte source lock."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.resource_pilot.bootstrap import canonical, notebook_bytes, NOTEBOOK_PATHS
from safeshift.diagnostics.resource_pilot.contract import AUTHORITY, LOCK, BASE_SHA, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_A_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    source = (repo / "safeshift/diagnostics/resource_pilot/bootstrap.py").read_text(encoding="utf-8")
    notebooks = {}
    for model, name in zip(("qwen3", "internvl3"), NOTEBOOK_PATHS):
        code = source + f'\nresult = bootstrap("{model}")\n'
        nb = {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python"}, "accelerator": "GPU",
                "safeshift": {"authority": "REQUIRED_NOT_GRANTED", "model": model, "shard": 0, "ordinals": list(range(8))}},
            "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
                f"# SafeShift resource pilot Dataset-path V3: {model}, first eight TRAIN shard-0 ordinals\n",
                "\nRun All is BLOCKED until this independent PR is audited, newly granted and standard-merged. No code/SHA/path edits. After approval only: upload unchanged, attach exactly one private unpacked approved TRAIN mount, select T4 x2, Internet ON for setup. Qwen3 uses two T4/CUDA 12.8; InternVL3 uses visible GPU 0/CUDA 12.4 and the post-guard PR115 loader.\n",
                "\nOne fixed model, one new attempt, 8 original images/hashes/order, C1 greedy max 32/batch 1, no retry/resume/clamp/calibration/forced prefix. Stop on any sample failure; preserve all eight statuses and raw evidence. Worker receives ordinal/hash only. No GT or TEST access anywhere in pilot.\n",
                "\nReads the original Dataset directly. Mount prefixes: /kaggle/input/<dataset-mount>/ and /kaggle/input/datasets/<owner>/<slug>/. Only three TRAIN roots per prefix: the mount itself, InspecSafe-V1/, or InspecSafe-V1-Kaggle/train/, each containing DATA_PATH/train/Annotations/. Matches the Owner-confirmed datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/ layout. Exactly one safe root; only two extra directory levels under datasets/, at most 512 total discovery entries, no recursive search or dataset preparation/re-upload. After new authority and attempt consumption, checks all eight JPEG paths, then hashes/stages the exact images with exposure receipts before software installation/checkpoint download. Missing/unsafe/wrong-hash input stops this one attempt with a specific reason and relative locator in exported evidence.\n",
                "\nFour raw label logits at every step; processed summaries separate; raw-before-decode; seal-before-parser; CPU HNLO replay only, full_vocab_replay=false. Partial AF_UNIX observations cannot establish SECURITY_PASS or NO_LEAK. Setup, checkpoint, load, per-image, memory/disk and export are measured. Eight images provide no worst-case or 941-image completion guarantee.\n",
                "\nSee notes/resource_pilot8_dataset_path_v3_20261019.md for this release and pending per-model approvals; notes/resource_pilot8_20261019.md retains historical scope, exposure policy and resource limits. PR #118/#119 grants do not authorize V3. Qwen3 V2 consumed its attempt; InternVL3 V2 is unrun and its grant cannot transfer. Retain failed/partial outputs and export sidecars; never rerun a consumed attempt.\n"]},
                {"cell_type": "code", "id": "run-pilot", "metadata": {}, "execution_count": None,
                 "outputs": [], "source": code.splitlines(keepends=True)}]}
        notebooks[name] = nb
        (repo / name).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, *NOTEBOOK_PATHS, "scripts/build_resource_pilot.py",
                 "tests/test_resource_pilot.py", "tests/test_resource_pilot_dataset_path.py",
                 "notes/resource_pilot8_dataset_path_v3_20261019.md",
                 "configs/diagnostics/resource_pilot_provenance.v1.json"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/resource_pilot").glob("*.py")]
    files = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        data = (repo / name).read_bytes()
        files.append({"path": name, "sha256": hashlib.sha256(notebook_bytes(data) if name in NOTEBOOK_PATHS else data).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, nb in notebooks.items():
        code = "".join(nb["cells"][1]["source"])
        nb["cells"][1]["source"] = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"',
            'PAYLOAD_SHA256 = "' + payload + '"', code).splitlines(keepends=True)
        (repo / name).write_text(json.dumps(nb, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return payload


if __name__ == "__main__":
    build()
