"""Reproducible F1 notebook/full Git-byte source lock. Never creates a grant."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.qwen3_recovery.bootstrap import canonical, notebook_bytes
from safeshift.diagnostics.qwen3_recovery.contract import AUTHORITY, LOCK, NOTEBOOK, BASE_SHA, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_A_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    code = (repo / "safeshift/diagnostics/qwen3_recovery/bootstrap.py").read_text(encoding="utf-8") + "\nresult = bootstrap()\n"
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"}, "accelerator": "GPU",
            "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "model": "qwen3",
                "count": 224, "original_ordinals": [717, 940], "baseline_pooling_allowed": False}},
        "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# SafeShift Qwen3 S2 Recovery224 V1 — PREP ONLY\n",
            "\nDo not run this Draft. New authority grant=null; V4 permissions do not apply.\n",
            "\nAfter GitHub review, independent audit, new Lead grant, verified standard release merge and cross-session reservation: attach the approved unpacked InspecSafe TRAIN Dataset, select T4 x2 and Internet ON for setup, Save & Run All once. No path, SHA or code edits. The worker denies network.\n",
            "\nExactly original ordinals 717–940, in PR123 order/hashes; no repeat of 0–716. New run and attempt, one model load, at most one native call per image, technical error stops with no retry/resume.\n",
            "\nBounded unique-root discovery includes datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train. All 224 paths/hashes/copies are checked on CPU before CUDA. Label-bearing IDs and paths stay outside the worker.\n",
            "\nSame pinned Qwen3 FP16/NONE/SDPA/placement, official processor, C1, HNLO, greedy max32 and raw logits/scores summaries as V4. Separately sealed per-image GPU observations and bounded original-error evidence; no OOM repair or GPU success claim.\n",
            "\nRecovery is a supplemental cohort. baseline_pooling_allowed=false; full_vocab_replay=false. Keep the archive and all five JSON receipts, including any failure. See notes/qwen3_s2_recovery224_20261022.md.\n"]},
            {"cell_type": "code", "id": "run-recovery", "metadata": {}, "execution_count": None,
             "outputs": [], "source": code.splitlines(keepends=True)}]}
    (repo / NOTEBOOK).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    # The historical working tree uses CRLF. Hash the original Git LF bytes,
    # overlaying only this task's tracked modifications and explicit additions.
    archive = subprocess.check_output(["git", "-C", str(repo), "archive", BASE_SHA])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        data = {m.name: stream.extractfile(m).read() for m in stream if m.isfile()}
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    changed = subprocess.check_output(["git", "-C", str(repo), "diff", "--name-only", BASE_SHA]).decode().splitlines()
    additions = [AUTHORITY, LOCK, NOTEBOOK, "scripts/build_qwen3_s2_recovery.py",
                 "tests/test_qwen3_recovery.py", "notes/qwen3_s2_recovery224_20261022.md"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/qwen3_recovery").glob("*.py")]
    for name in set(changed + additions):
        if name not in (AUTHORITY, LOCK):
            data[name] = (repo / name).read_bytes().replace(b"\r\n", b"\n")
    names = set(tracked + additions) - {AUTHORITY, LOCK}
    files = [{"path": name, "sha256": hashlib.sha256(
        notebook_bytes(data[name]) if name == NOTEBOOK else data[name]).hexdigest()} for name in sorted(names)]
    lock = {"schema": "qwen3-s2-recovery-source-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    notebook["cells"][1]["source"] = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"',
        'PAYLOAD_SHA256 = "' + payload + '"', code).splitlines(keepends=True)
    (repo / NOTEBOOK).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return payload


if __name__ == "__main__":
    build()
