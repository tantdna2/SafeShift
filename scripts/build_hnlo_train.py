"""Build eight fixed-unit notebooks and a full reviewed source lock; never grant."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.hnlo_train.bootstrap import canonical, notebook_bytes, NOTEBOOK_PATHS
from safeshift.diagnostics.hnlo_train.contract import AUTHORITY, LOCK, BASE_SHA, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_A_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    source = (repo / "safeshift/diagnostics/hnlo_train/bootstrap.py").read_text(encoding="utf-8")
    notebooks = {}
    for model in ("qwen3", "internvl3"):
        for shard in range(4):
            path = f"notebooks/SafeShift_HNLO_TRAIN_{model}_SHARD{shard}_V4.ipynb"
            code = source + f'\nresult = bootstrap("{model}", {shard})\n'
            notebook = {"nbformat": 4, "nbformat_minor": 5,
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                    "language_info": {"name": "python"}, "accelerator": "GPU",
                    "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "model": model, "shard": shard}},
                "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
                    f"# SafeShift HNLO TRAIN {model} / shard {shard} - PREP ONLY\n",
                    "\nNull grant: Run All blocks before dataset reads, provisioning or GPU. After separate review, Lead grant and verified release merge, upload unchanged, attach exactly one unpacked approved InspecSafe TRAIN input, select T4 x2 and Internet ON for setup, and Save & Run All once. No code, SHA or path edits. Worker runs offline with guards.\n",
                    "\nOne model/shard, unique single-use run ID, original image hashes/order and C1, greedy batch 1/max 32, no retries or clamp. GT-free opaque worker inputs; raw saved and sealed before parser; explicit CPU label approval after raw custody seal. Summary evidence is PROPOSED and needs separate Lead approval; no full-vocabulary reconstruction claim.\n",
                    "\nOriginal Kaggle input: /kaggle/input/datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH/train/Annotations/. Bounded discovery from PR120, exactly one safe root, all-shard CPU metadata/hash/staging before setup. No PREP Dataset or manual path edit.\n",
                    "\nPilot V3 exposed shard-0 ordinals 0..7 for each model. Keep these in the fixed cohort; new reads/calls require overlap approval and fresh evidence, never pilot output reuse. full_vocab_replay=false.\n",
                    "\nDo not run historical synthetic grants. Retain all outputs including failures. No TEST, fine-tuning, threshold, repair, generalization claim or Moondream removal. Throughput/real-image VRAM/session completion are unverified. See notes/hnlo_train_v4_20261019.md.\n"]},
                    {"cell_type": "code", "id": "run-unit", "metadata": {}, "execution_count": None,
                     "outputs": [], "source": code.splitlines(keepends=True)}]}
            notebooks[path] = (notebook, code)
            (repo / path).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, *NOTEBOOK_PATHS, "scripts/build_hnlo_train.py", "scripts/profile_hnlo_train.py",
                 "tests/test_hnlo_train.py", "tests/test_hnlo_train_v4.py", "configs/diagnostics/hnlo_train_provenance.v4.json", "notes/hnlo_train_v4_20261019.md", "notes/hnlo_train_v4_cpu_profile.json"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/hnlo_train").glob("*.py")]
    files = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        data = (repo / name).read_bytes()
        files.append({"path": name, "sha256": hashlib.sha256(notebook_bytes(data) if name in NOTEBOOK_PATHS else data).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    for name, (notebook, code) in notebooks.items():
        notebook["cells"][1]["source"] = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"',
            'PAYLOAD_SHA256 = "' + payload + '"', code).splitlines(keepends=True)
        (repo / name).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return payload


if __name__ == "__main__":
    build()
