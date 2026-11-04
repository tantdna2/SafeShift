"""Reproducible PR177 campaign notebook; no grant/credentials or submission API."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

from safeshift.internvl_v2_runtime import IDENTITY, LIMITS, runtime_sources
from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import write_bytes
from safeshift.pilot.contract import digest


def build(ref):
    require(len(ref) == 40 and all(c in "0123456789abcdef" for c in ref), "COMMITTED_SOURCE_REQUIRED")
    payload = {}
    for name in runtime_sources():
        content = subprocess.check_output(["git", "show", ref + ":" + name], cwd=ROOT)
        require(content == (ROOT / name).read_bytes(), "UNCOMMITTED_RUNTIME:" + name)
        payload[name] = content.decode("utf8")
    packed = json.dumps(payload, sort_keys=True).encode()
    manifest = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in payload.items()}
    spec = {"identity": IDENTITY, "manifest": manifest}
    code = f'''import base64, hashlib, json, sys, uuid, zlib
from pathlib import Path
packed = zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(packed, 9)).decode()!r}))
assert hashlib.sha256(packed).hexdigest() == {hashlib.sha256(packed).hexdigest()!r}
spec = {spec!r}
payload = json.loads(packed)
assert set(payload) == set(spec['manifest'])
root = Path('/kaggle/temp') / ('internvl-v2-source-' + uuid.uuid4().hex)
root.mkdir(parents=True, exist_ok=False)
for name, content in payload.items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name and '\\\\' not in name
    assert hashlib.sha256(content.encode()).hexdigest() == spec['manifest'][name]
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(content.encode())
sys.path.insert(0, str(root))
from scripts.internvl_v2_campaign import launch
result = launch(spec, runtime_commit={ref!r})
print(json.dumps(result, sort_keys=True))
if result['status'] not in ('LIVE_GPU_PREFLIGHT_PASS', 'SUCCESS', 'INVALID'):
    raise RuntimeError('V2_BLOCKED_SEE_PRIVATE_SEALED_OUTPUT')
'''
    compile(code, "<internvl-v2-notebook>", "exec")
    return {"nbformat": 4, "nbformat_minor": 5,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
            "safeshift": {"identity": IDENTITY, "runtime_commit": ref, "manifest_sha256": digest(manifest),
                "limits": LIMITS, "execution_authority": None, "live_verification": "NOT_RUN"}},
        "cells": [{"cell_type": "markdown", "id": "scope", "metadata": {}, "source": [
            "# InternVL3.5 grammar V2 — exact-release campaign\n",
            "STOP for ChatGPT review and independent Antigravity audit at the committed HEAD. No execution grant is embedded.\n",
            "Only scripts.submit_internvl_v2 may dispatch after a separate exact release; mode/job/request come from the create-only GitHub submission ledger. Manual runs and replay cannot obtain fresh load/call permits.\n",
            "Preflight attaches pinned checkpoint, original master metadata and original sealed smoke identity; no TRAIN/TEST image Input. Native attaches original TRAIN only under its own release.\n",
            "Side effects: pinned Python/package provisioning under /kaggle/temp, bounded scratch allocation/fsync/cleanup, CUDA FP16 probe. No weights load or model call.\n",
            "Uses two physical T4s, only GPU0 visible to the native worker; synthetic processor runs in a supervised CPU-only child and exits before final RAM check.\n",
            "Campaign dispatch caps each job at600 server seconds; three jobs reserve1200/2400/3600 physical-GPU seconds with no refund. Original16GiB RAM floor remains enforced.\n",
            "Memory evidence includes cgroup anon/file/limit/current and process RSS before/after checks and on failure. Clean-page advice is limited to this run's owned venv libraries; no shared-cache deletion or RAM guarantee.\n",
            "Private evidence: /kaggle/working/safeshift-internvl-v2-6622148168-j<N> and ZIP/SHA256. Preserve failures and partial files.\n",
            "No tokens or credentials in the VM. Only nonce challenges are relayed; raw/log archives stay private. Preflight consumes one of three campaign jobs, zero native slots.\n",
            "One load and one generation permit cumulatively across all VMs. A failed or unknown call never permits another call. Missing evidence is not zero-call proof.\n",
            "HNLO is always N/A. No historical completion import, full TRAIN dispatch, scientific pooling or retry.\n"]},
            {"cell_type": "code", "id": "preflight", "metadata": {}, "outputs": [],
             "execution_count": None, "source": code.splitlines(True)}]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-commit", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    write_bytes(args.output, (json.dumps(build(args.source_commit), indent=1) + "\n").encode())
