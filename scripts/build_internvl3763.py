"""Build a committed-source PREP notebook; no embedded grant or real dataset."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib
from safeshift import internvl3763 as runtime
from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import write_bytes
from safeshift.pilot.contract import digest


def build(ref):
    require(len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), "COMMITTED_RUNTIME_REQUIRED")
    spec = runtime.source_spec()
    payload = {}
    for name in spec["manifest"]:
        content = subprocess.check_output(["git", "show", ref + ":" + name], cwd=ROOT)
        require(content == (ROOT / name).read_bytes(), "UNCOMMITTED_RUNTIME:" + name)
        payload[name] = content.decode("utf8")
    packed = json.dumps(payload, sort_keys=True).encode()
    encoded = base64.b64encode(zlib.compress(packed, 9)).decode()
    code = f'''import base64, hashlib, json, sys, uuid, zlib
from pathlib import Path
packed = zlib.decompress(base64.b64decode({encoded!r}))
assert hashlib.sha256(packed).hexdigest() == {hashlib.sha256(packed).hexdigest()!r}
spec = {spec!r}
payload = json.loads(packed)
assert set(payload) == set(spec['manifest'])
root = Path('/kaggle/temp') / ('internvl3763-prep-' + uuid.uuid4().hex)
root.mkdir(parents=True, exist_ok=False)
for name, content in payload.items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name and '\\\\' not in name
    assert hashlib.sha256(content.encode()).hexdigest() == spec['manifest'][name]
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(content.encode())
sys.path.insert(0, str(root))
from scripts.internvl3763 import main
main(['--mode', 'prepare', '--output', '/kaggle/working/internvl3763-readiness.json'])
'''
    compile(code, "<train3763-prep>", "exec")
    return {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "safeshift": {"identity": runtime.IDENTITY, "runtime_commit": ref, "source_sha256": digest(spec),
            "status": "BLOCKED_PREPARATION_ONLY", "execution_authority": None,
            "model_calls": 0, "live_verification": "NOT_RUN_FINAL_SOURCE"}},
        "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# InternVL grammar V2 — TRAIN3763 PREP\n",
            "Preparation only. Do not submit to Kaggle without a new exact execution scope/release.\n",
            "This cell exports a BLOCKED readiness receipt; it never loads weights, reads images or calls a model.\n",
            "Native/preflight/submit authority remains closed even if notebook cells/flags are edited.\n",
            "Original3763 IDs/order/SHA, a new separate series, FP16/eager/C1/strict parser/grammarV2 and HNLO N/A are required.\n",
            "No pilot/smoke prediction import, GT/TEST, pooling, automatic retry or source-lock bypass.\n",
            "Side effects: extract reviewed public source into unique /kaggle/temp; write readiness JSON to /kaggle/working. No dependency installation/GPU/Inputs.\n",
            "Final live environment/weights/inference/export validation NOT_RUN. Historical PR177 ordinal0 success does not validate this runtime/cohort.\n",
            "Operations transfer uses scripts/kaggle_handoff.ps1; pause at RUNNING_UNVERIFIED, resume the saved conversation for terminal collection.\n"]},
            {"cell_type": "code", "id": "readiness", "metadata": {}, "source": code.splitlines(True),
             "outputs": [], "execution_count": None}]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    write_bytes(a.output, (json.dumps(build(a.source_commit), indent=1) + "\n").encode())
