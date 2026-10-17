"""Maintainer-only deterministic notebook/source-lock build; no release or grant."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.one_click.bootstrap import canonical, notebook_bytes
from safeshift.diagnostics.one_click.contract import AUTHORITY, BASE_SHA, LOCK, NOTEBOOK, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    authority.parent.mkdir(parents=True, exist_ok=True)
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_AN_AUTHORITY_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    bootstrap = (repo / "safeshift/diagnostics/one_click/bootstrap.py").read_text(encoding="utf-8")
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}, "accelerator": "GPU", "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "real_model_execution_in_codex": False}},
        "cells": [{"cell_type": "markdown", "metadata": {}, "id": "scope",
                   "source": ["# SafeShift — HNLO Qwen3 + InternVL3\n", "\n",
                    "Upload this notebook unchanged. Select **GPU T4 ×2** and **Internet ON** for preparation, then **Save & Run All once**. No configuration cell or path/SHA edits.\n",
                    "\n", "Execution remains BLOCKED until the independently audited release is merged and the Research Lead grants this exact two-model synthetic attempt. The notebook discovers that release, provisions separate exact interpreters/libraries/checkpoints, then denies inference networking in native and Python code.\n",
                    "\n", "One fixed synthetic RGB image, unchanged C1, InternVL3 first, Qwen3 second; one load/generate per model, no retries. Outputs and partial failure evidence are exported to `/kaggle/working/`. HNLO_RESEARCH_VERIFIED always remains false.\n",
                    "\n", "Runtime admission: Linux x86_64, ≥24 GiB available RAM, ≥50 GiB free disk, two T4s with ≥13 GiB free VRAM each, build tools/headers and libseccomp-compatible kernel. Missing conditions produce BLOCKED. Fresh-session grant reuse requires Owner/Lead accounting.\n"]},
                  {"cell_type": "code", "metadata": {}, "id": "run-everything", "execution_count": None,
                   "outputs": [], "source": (bootstrap + "\n# The single Run All entrypoint.\nresult = bootstrap()\n").splitlines(keepends=True)}]}
    path = repo / NOTEBOOK
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, NOTEBOOK, "scripts/build_hnlo_one_click.py", "tests/test_hnlo_one_click.py",
                 "notes/hnlo_one_click_runbook_20261017.md", "configs/diagnostics/hnlo_one_click_build.v1.json"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/one_click").glob("*.py")]
    files = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        content = (repo / name).read_bytes()
        if name == NOTEBOOK:
            content = notebook_bytes(content)
        files.append({"path": name, "sha256": hashlib.sha256(content).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    cell = notebook["cells"][1]
    code = "".join(cell["source"])
    code = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"', 'PAYLOAD_SHA256 = "' + payload + '"', code)
    cell["source"] = code.splitlines(keepends=True)
    path.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return notebook, payload


if __name__ == "__main__":
    build()
