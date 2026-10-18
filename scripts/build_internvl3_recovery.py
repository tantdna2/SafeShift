"""Maintainer-only source lock and notebook build; preserves every PR #112 lock."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.internvl3_recovery.bootstrap import canonical, notebook_bytes
from safeshift.diagnostics.internvl3_recovery.contract import AUTHORITY, BASE_SHA, LOCK, NOTEBOOK, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_AN_AUTHORITY_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    bootstrap = (repo / "safeshift/diagnostics/internvl3_recovery/bootstrap.py").read_text(encoding="utf-8")
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}, "accelerator": "GPU",
                     "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "real_model_execution_in_codex": False}},
        "cells": [{"cell_type": "markdown", "metadata": {}, "id": "scope", "source": [
            "# SafeShift InternVL3 recovery only\n", "\n",
            "Upload unchanged. Select **GPU T4 x2**, **Internet ON** for preparation; **Save & Run All once**, only after separate approval and merge. No code, SHA or path edits. Qwen3 is excluded.\n", "\n",
            "Default grant is null. This notebook discovers its own reviewed release, verifies F1/F2/merge topology and every tracked source byte, then validates the new grant before provisioning or GPU checks. PR #112 authority and attempt cannot authorize recovery.\n", "\n",
            "One pinned InternVL3 environment/checkpoint, CUDA_VISIBLE_DEVICES=0, one fixed synthetic RGB image, unchanged C1/FP16/greedy/max 32 tokens, at most one load and one generate. No retries or dataset access. Raw/processed logits, CPU replay and SHA-256 evidence export reuse PR #112.\n", "\n",
            "The proposed seccomp/Python boundary permits local AF_UNIX connect and requires explicit Research Lead security approval, including local-peer relay risk. INET/INET6, sendmsg/sendto, descriptor receipt and io_uring remain blocked. CUDA causality and Kaggle compatibility are unproven.\n", "\n",
            "Unprivileged monitoring exports Python connection metadata and bounded /proc socket snapshots. Native connection events, transient sockets and peer forwarding remain PARTIAL/UNOBSERVABLE. No NO_LEAK or SECURITY_PASS claim. Forbidden Python operations, worker IP sockets, or a peer with an observed connected IP channel stop the attempt; the latter is a risk signal, not proof of payload forwarding. No automatic retry or expanded permissions.\n", "\n",
            "Conservative inherited admission: Linux x86_64, 24 GiB available RAM, 50 GiB scratch, 4 GiB Output, T4 x2 with 13 GiB free each, build tools and seccomp TSYNC. Evidence and partial failures go to /kaggle/working/. HNLO_RESEARCH_VERIFIED stays false. Fresh-session single-use needs Lead/Owner accounting.\n"]},
          {"cell_type": "code", "metadata": {}, "id": "run-everything", "execution_count": None,
           "outputs": [], "source": (bootstrap + "\n# The single Run All entrypoint.\nresult = bootstrap()\n").splitlines(keepends=True)}]}
    path = repo / NOTEBOOK
    path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, NOTEBOOK, "scripts/build_internvl3_recovery.py",
                 "tests/test_internvl3_recovery.py", "tests/test_internvl3_monitor.py", "notes/internvl3_cuda_recovery_20261017.md"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/internvl3_recovery").glob("*.py")]
    files = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        content = (repo / name).read_bytes()
        if name == NOTEBOOK:
            content = notebook_bytes(content)
        files.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    code = "".join(notebook["cells"][1]["source"])
    code = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"', 'PAYLOAD_SHA256 = "' + payload + '"', code)
    notebook["cells"][1]["source"] = code.splitlines(keepends=True)
    path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return notebook, payload


if __name__ == "__main__":
    build()
