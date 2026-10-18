"""Maintainer-only notebook/source-lock builder; never overwrites a grant."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.internvl3_cuda.bootstrap import canonical, notebook_bytes
from safeshift.diagnostics.internvl3_cuda.contract import AUTHORITY, BASE_SHA, LOCK, NOTEBOOK, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_AN_AUTHORITY_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    code = (repo / "safeshift/diagnostics/internvl3_cuda/bootstrap.py").read_text(encoding="utf-8")
    code += "\n# The single Run All entrypoint.\nresult = bootstrap()\n"
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}, "accelerator": "GPU",
                     "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "model_weights": False}},
        "cells": [{"cell_type": "markdown", "metadata": {}, "id": "scope", "source": [
            "# SafeShift InternVL3 CUDA diagnostic PREP\n", "\n",
            "Upload unchanged. After independent audit, new Research Lead grant and verified release merge, select **T4 x2**, **Internet ON** for source/software preparation, then **Save & Run All once**. Owner edits no code, SHA, path or configuration. This Draft has no execution authority.\n", "\n",
            "The null-by-default authority is independent of PR #113. Each approved attempt compiles the same Python 3.11.11 and installs the locked InternVL3 software (torch 2.6.0+cu124, CUDA 12.4, Transformers 4.52.4). It downloads no model weights and performs no model load, inference, Qwen3 run or dataset access.\n", "\n",
            "First collect static host metadata only. Six fresh pinned workers then collect guarded metadata, load libcuda, load NVML, load the pinned CUDART, call cuInit(0), and call cudaGetDeviceCount. Loader-only stages call no CUDA/NVML initialization API; library constructors remain native code under the guards. Driver/runtime stages require explicit new GPU diagnostic approval. NVML is never used as CUDA admission.\n", "\n",
            "All worker stages use the unchanged sanitized child environment, CUDA_VISIBLE_DEVICES=0, TSYNC seccomp and Python network guard before driver libraries load. No unguarded CUDA control, environment repair, syscall allowance, network expansion, tracing, retry or fallback. Metadata cannot prove cgroup access; absence of monitored events cannot prove absence of native denials or relay traffic.\n", "\n",
            "Evidence distinguishes host and worker, records loader outcomes, mapped library identities, device-node metadata and original numeric CUDA return codes. Every stage has a new process to avoid cached counts. Results are observations, never an automatic root-cause, CUDA PASS or security PASS. Archives, manifest and independently checked SHA-256 receipts appear in Kaggle Output. A fatal guard/source/evidence failure stops later stages and preserves partial files.\n", "\n",
            "Research Lead must approve the exact source payload, diagnostic calls, software provisioning, metadata/retention and residual local-peer relay risk, then issue a unique attempt in authority-only F2 and standard merge M. Cross-session non-reuse needs Lead/Owner accounting. Stop after this Draft PR for direct GitHub review.\n"]},
          {"cell_type": "code", "metadata": {}, "id": "run-everything", "execution_count": None, "outputs": [],
           "source": code.splitlines(keepends=True)}]}
    (repo / NOTEBOOK).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, NOTEBOOK, "scripts/build_internvl3_cuda_diagnostic.py",
                 "tests/test_internvl3_cuda_diagnostic.py", "notes/internvl3_cuda_diagnostic_20261018.md"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/internvl3_cuda").glob("*.py")]
    files = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        data = (repo / name).read_bytes()
        files.append({"path": name, "sha256": hashlib.sha256(notebook_bytes(data) if name == NOTEBOOK else data).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": files}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    notebook["cells"][1]["source"] = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"', 'PAYLOAD_SHA256 = "' + payload + '"', code).splitlines(keepends=True)
    (repo / NOTEBOOK).write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return notebook, payload


if __name__ == "__main__":
    build()
