"""Maintainer builder: source lock and single-cell notebook; never grants rights."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.internvl3_hnlo.bootstrap import canonical, notebook_bytes
from safeshift.diagnostics.internvl3_hnlo.contract import AUTHORITY, BASE_SHA, LOCK, NOTEBOOK, template


def build(repo=ROOT):
    repo = Path(repo)
    authority = repo / AUTHORITY
    if authority.exists() and json.loads(authority.read_bytes()) != template():
        raise ValueError("NEVER_OVERWRITE_AN_AUTHORITY_GRANT")
    authority.write_text(json.dumps(template(), indent=2) + "\n", encoding="utf-8", newline="\n")
    code = (repo / "safeshift/diagnostics/internvl3_hnlo/bootstrap.py").read_text(encoding="utf-8")
    code += "\n# The single Run All entrypoint.\nresult = bootstrap()\n"
    notebook = {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                     "language_info": {"name": "python"}, "accelerator": "GPU",
                     "safeshift": {"execution_authority": "REQUIRED_NOT_GRANTED", "HNLO_RESEARCH_VERIFIED": False}},
        "cells": [{"cell_type": "markdown", "metadata": {}, "id": "scope", "source": [
            "# SafeShift InternVL3 HNLO GPU probe — PREP ONLY\n", "\n",
            "After independent review, a NEW Research Lead grant and verified standard merge: upload this notebook unchanged, select **GPU T4 x2**, enable **Internet** for preparation, and **Save & Run All exactly once**. No code, hash, path or revision edits. This Draft blocks before provisioning/GPU.\n", "\n",
            "Only OpenGVLab/InternVL3-2B-hf at cb57a075cb75a2e6d1b668b128d48bb00ae321d2. Python 3.11.11, PyTorch 2.6.0+cu124, Transformers 4.52.4; FP16, no quantization, CUDA_VISIBLE_DEVICES=0. Locked C1, the PR #112 gray RGB 448x448 PNG, batch 1, greedy max 32 tokens; at most one model load and one generate. No retry, forced prefix, calibration, InspecSafe/TRAIN/TEST/labels/GT.\n", "\n",
            "Source/authority precede TSYNC seccomp, Python guard/monitor, sanitized environment, unchanged PR #115 verified-fd driver loading, and CUDA admission. Checkpoint download follows successful guarded CUDA inspection; probe repeats driver/CUDA gates before checkpoint verification/model loading. Driver handles survive to process exit; library mappings are recorded after CUDA, model load and generation. No LD_LIBRARY_PATH restoration, pre-guard driver load, guard relaxation or fallback.\n", "\n",
            "Runtime T1 28/28 with canonical Level01–Level04 order, all raw logits before decode/parse, separate full processed scores, actual processors/stopping criteria, EOS and decision position, and CPU replay are required. INVALID stays unchanged and yields N/A. TECHNICAL_HNLO_VALID requires all actual gates PASS. HNLO_RESEARCH_VERIFIED always stays false.\n", "\n",
            "Admission conservatively retains 24 GiB available RAM, 50 GiB scratch, 4 GiB Output and T4 x2 with 13 GiB free each. Full 32-step evidence is budgeted before load; insufficient resources stop without truncation. Archive, manifest, SHA-256 receipts, report and result JSON are exported with partial failure evidence.\n", "\n",
            "Separate approval must cover driver-loading/model execution, source-bound technical exception, full-vector provenance/tolerance/retention and AF_UNIX relay residual risk. Monitoring is PARTIAL/UNOBSERVABLE; no SECURITY_PASS/NO_LEAK claim. PR #112–#115 grants are rejected. A local attempt ledger blocks reruns in the same output filesystem; Lead/Owner must account for single use across fresh sessions.\n"]},
          {"cell_type": "code", "metadata": {}, "id": "run-everything", "execution_count": None,
           "outputs": [], "source": code.splitlines(keepends=True)}]}
    path = repo / NOTEBOOK
    path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().rstrip("\0").split("\0")
    additions = [AUTHORITY, LOCK, NOTEBOOK, "configs/diagnostics/internvl3_hnlo_generation_sources.v1.json", "scripts/build_internvl3_hnlo_probe.py",
                 "scripts/profile_internvl3_hnlo_vectors.py", "tests/test_internvl3_hnlo_probe.py",
                 "notes/internvl3_hnlo_gpu_probe_20261019.md"]
    additions += [p.relative_to(repo).as_posix() for p in (repo / "safeshift/diagnostics/internvl3_hnlo").glob("*.py")]
    rows = []
    for name in sorted(set(tracked + additions) - {AUTHORITY, LOCK}):
        data = (repo / name).read_bytes()
        rows.append({"path": name, "sha256": hashlib.sha256(notebook_bytes(data) if name == NOTEBOOK else data).hexdigest()})
    lock = {"schema": "hnlo-source-lock-v1", "base_sha": BASE_SHA, "files": rows}
    payload = hashlib.sha256(canonical(lock)).hexdigest()
    (repo / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8", newline="\n")
    notebook["cells"][1]["source"] = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"',
        'PAYLOAD_SHA256 = "' + payload + '"', code).splitlines(keepends=True)
    path.write_text(json.dumps(notebook, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("SOURCE_PAYLOAD_SHA256=" + payload)
    return notebook, payload


if __name__ == "__main__":
    build()
