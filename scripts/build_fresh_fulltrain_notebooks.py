"""Issue171 notebooks with a separate exact-commit payload; old notebooks untouched."""
import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import zlib

from scripts.build_candidate160_notebooks import fulltrain_notebook
from safeshift.candidates.train_contract import sources as old_sources, source_hash as old_hash
from safeshift.candidates.source import ROOT, require
from safeshift.fulltrain import contract
from safeshift.pilot.contract import digest


def packed(payload):
    return base64.b64encode(zlib.compress(json.dumps(payload, sort_keys=True).encode(), 9)).decode()


def notebook(key, ref, repo=ROOT, *, diagnostic=False):
    require(re.fullmatch(r"[0-9a-f]{40}", ref), "EXACT_RUNTIME_COMMIT")
    repo = Path(repo)
    payload = {name: (repo / name).read_text(encoding="utf-8") for name in contract.sources(repo)}
    for name, text in payload.items():
        require(subprocess.check_output(["git", "show", f"{ref}:{name}"], cwd=repo) == text.encode(),
                "RUNTIME_REF_SOURCE_MISMATCH:" + name)
    nb = fulltrain_notebook(key, ref, repo)
    code = "".join(nb["cells"][1]["source"])
    old = {name: (repo / name).read_text(encoding="utf-8") for name in old_sources(repo)}
    require(code.count(repr(packed(old))) == 1, "EXACT_OLD_PAYLOAD")
    code = code.replace(repr(packed(old)), repr(packed(payload)))
    code = code.replace(old_hash(repo), digest(contract.source_manifest(repo)))
    code = code.replace("fulltrain_prep_code", "fresh_fulltrain_code").replace("fulltrain_prep_bootstrap", "fresh_fulltrain_bootstrap")
    code = code.replace("from safeshift.candidates.fulltrain_preflight import prepare_notebook as launch",
                        "from safeshift.fulltrain.preflight import prepare as launch")
    kind = "DIAGNOSTIC" if diagnostic else "PREPARATION"
    code = code.replace(f"launch({key!r}, expected_source_sha256, root, {ref!r})",
                        f"launch({key!r}, expected_source_sha256, root, {ref!r}, kind={kind!r})")
    require("safeshift.fulltrain.preflight import prepare as launch" in code, "PREP_ENTRYPOINT_REQUIRED")
    compile(code, "fresh-fulltrain", "exec")
    nb["cells"][1]["source"] = code.splitlines(True)
    nb["cells"][0]["source"] = f"""# SafeShift fresh full TRAIN - {key} - {kind}

Issue #171: OWNER_FRESH_FULLTRAIN_ONLY. **PREPARATION / RELEASE BLOCKED**.
Each model has its own new series, with the same original 3,763 TRAIN IDs,
order and image hashes. No historical predictions or completion inheritance.
The three new series plan 11,289 initial calls; none have run in this task.

Save/Run All in this preparation version only observes the local kernel with
stdlib and exports source/native-contract/remaining-gate evidence. It does not
discover Inputs, provision software, allocate GPU, load weights or infer.
No grant JSON, action switch or Owner edit unlocks this notebook version.
Both preparation and diagnostic notebooks remain non-consuming and repeatable.
Local rehearsal writes embedded sources and unique ZIP/SHA256 under data/processed.

Before a later executable release: independently seal original master projection
and opaque image mapping; attach one fresh_fulltrain_input.json Input and the
exact model checkpoint/source; verify all hashes, native CPU processor/meta
and isolated Python/pins/compiled ABI; measure scratch/output devices, actual
allocation/fsync/cleanup, RAM/cgroup/quota/deadline, per-GPU memory/driver and
CUDA FP16 in that same child. Allocation and run caps must come from O5/O6,
not from Candidate160 defaults. Full load/real inference/export need separate
authorized final-source verification. See docs/FRESH_FULLTRAIN_171.md.

Resume only NOT_ATTEMPTED in the named new series. INVALID/consumed errors need
an explicit repair case with cause evidence, failed outcome, fix and regression
hashes and authority/caps. Semantic/config changes open another series. Retain
every raw/partial/failed attempt and sealed archive. No GT rescue, lax parser,
pooling, metric changes, final roster claim or guarantee of all SUCCESS.
MiniCPM stays FP32-resampler/FP16-weights/eager and label-only. Qwen now has a
prepared offline native adapter with exact public revision/source/processor,
FP16/SDPA/two-T4 placement and original V4 P2.1/raw HNLO semantics. Its pinned
CPython3.12.13/zlib1.2.11 build and closed cp312 wheelhouse remain unverified.
Internal admission/setup/CPU/GPU/native stages use process-group hard deadlines
and parent-death cleanup. These CPU-tested mechanisms do not open public run
authority or establish Kaggle/model-fit PASS. No historical grant is reused.

O2-O6 and live G0-G6 remain separate. Download all evidence including failures.
Do not upload or execute this preparation on Kaggle in Issue171. Stop at one
Draft PR for ChatGPT review, independent Antigravity audit and separate merge.
""".splitlines(True)
    nb["metadata"]["safeshift"] = {"mode": "FRESH_FULLTRAIN_" + kind, "status": "BLOCKED",
        "model_key": key, "runtime_ref": ref, "source_sha256": digest(contract.source_manifest(repo)),
        "planned_ids": 3763, "series_id": contract.SERIES[key], "release": contract.release_report(key)}
    return nb


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-ref", required=True)
    args = parser.parse_args()
    for key in contract.planning.MODELS:
        for diagnostic in (False, True):
            kind = "DIAGNOSTIC" if diagnostic else "PREP"
            value = notebook(key, args.runtime_ref, diagnostic=diagnostic)
            (ROOT / f"notebooks/SafeShift_FRESH_FULLTRAIN_{kind}_{key}.ipynb").write_bytes(
                (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
