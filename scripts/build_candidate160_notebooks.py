"""Deterministic candidate notebooks using the existing notebook bootstrap.

The exact runtime commit must contain every embedded byte. A subsequent commit
can contain the generated notebooks/evidence without a self-referential SHA.
"""
import argparse
import base64
import copy
import json
from pathlib import Path
import re
import subprocess
import zlib

from scripts.build_three_vlm_notebooks import notebook as legacy_notebook
from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_contract import BASE, PACKAGE_BASE, KEYS, MANIFEST, config, configuration_hashes, model, sources, source_hash
from safeshift.pilot.contract import source_digest


def notebook(key, ref, repo=ROOT):
    require(key in KEYS and re.fullmatch(r"[0-9a-f]{40}", ref), "EXACT_RUNTIME_COMMIT_REQUIRED")
    repo = Path(repo)
    payload = {p: (repo / p).read_text(encoding="utf-8") for p in sources(repo)}
    # Byte identity is checked with Git, never inferred from a caller-provided SHA.
    for name, text in payload.items():
        saved = subprocess.check_output(["git", "show", f"{ref}:{name}"], cwd=repo, stderr=subprocess.PIPE)
        require(saved == text.encode(), "RUNTIME_REF_SOURCE_MISMATCH:" + name)
    result = copy.deepcopy(legacy_notebook("phi", repo))
    code = "".join(result["cells"][1]["source"])
    old_payload = {p: (repo / p).read_text(encoding="utf-8") for p in __import__(
        "safeshift.pilot.contract", fromlist=["source_files"]).source_files(repo)}
    def packed(value):
        return base64.b64encode(zlib.compress(json.dumps(value, sort_keys=True).encode(), 9)).decode()
    code = code.replace(repr(packed(old_payload)), repr(packed(payload)))
    code = code.replace(source_digest(repo), source_hash(repo))
    code = code.replace('root.mkdir(parents=True, exist_ok=True)', 'root.mkdir(parents=True, exist_ok=False)')
    code = code.replace('pathlib.Path("/kaggle/working/data/processed/three_vlm_code")',
                        'pathlib.Path.cwd() / "data/processed/candidate160_code"')
    code = code.replace('pathlib.Path("/kaggle/working/data/processed/three_vlm_bootstrap")',
                        '(pathlib.Path.cwd() / "data/processed/candidate160_bootstrap")')
    code = code.replace("from safeshift.pilot.bootstrap import launch", "from safeshift.candidates.train_runtime import launch_owner as launch")
    code = code.replace('launch(\'phi\', expected_source_sha256, root, mode="PILOT")',
                        f'launch({key!r}, expected_source_sha256, root, {ref!r}, owner_start=True)')
    require("safeshift.pilot.bootstrap import launch" not in code and 'mode="PILOT"' not in code,
            "CANDIDATE_LAUNCH_ROUTE_REQUIRED")
    compile(code, "candidate160_notebook", "exec")
    spec = model(key)
    instructions = f"""# SafeShift ? {spec['id']} ? m?t l??t, t?i ?a 160 TRAIN

**Owner k?ch ho?t b?ng Save Version ? Save & Run All m?t l?n**, sau khi PR n?y
???c ChatGPT ki?m GitHub v? audit ??c l?p tr??c merge. Kh?ng c?n grant,
reservation hay file CONTINUE th? c?ng. Thao t?c ch?y notebook l? y?u c?u
th?c thi c?a Owner trong ??ng ph?m vi quy?t ??nh ng?y 30/10/2026, ghi t?i
`docs/research/CANDIDATE160_OWNER_DECISION_20261030.md`; m?y kh?ng k? thay Lead.
??y l? code ch?a ???c ki?m GPU; ch?t l??ng th?t v? HNLO th?c nghi?m UNVERIFIED.

Model `{spec['id']}` @ `{spec['revision']}`; Transformers `{spec['transformers']}`.
Adapter base #151 `{BASE}`; package base #153 `{PACKAGE_BASE}`.
Runtime commit `{ref}`. C?ng manifest SHA256 `{MANIFEST}` v? ??ng 160 ?nh TRAIN
/th? t? l?ch s?, kh?ng ch?n l?i, TEST, supplement ho?c FULL TRAIN.
Kh?ng chuy?n quy?n n?y sang d? li?u b?n th? ba ho?c th? nghi?m kh?c.

1. M? ??ng notebook model trong m?t Kaggle session ch?a ch?y; ch?n **T4 ?2**,
   Internet ON ?? c?i software pinned. Kh?ng ch?y interactive tr??c khi Save.
2. Attach bundle Owner ?? upload: `pilot_manifest.json` v?
   `images/000000.jpg` ? `images/000159.jpg`.
3. Attach checkpoint ?? upload: `candidate_checkpoint_{key}.json`,
   `source/{spec['revision']}/` ??ng source allowlist v? `weights/` ??ng
   index + hai shards ?? kh?a SHA256. Xem `docs/CANDIDATE160_KAGGLE.md`.
4. Save Version ? **Save & Run All** m?t l?n. Kh?ng s?a cell, SHA, model,
   version ho?c input ?? ?i qua l?i. Kh?ng retry/resume ho?c ghi ??.
5. Download ZIP + `.sha256.json` ???c in ? cell cu?i, k? c? l?i/partial;
   gi? private. `COMPLETED_AWAITING_REVIEW` kh?ng ph?i model qualification.

Run ID/attempt ID v? consumption log ???c t?o t? ??ng. Kh?a slot c? ??nh theo
model/cohort ch?n ch?y tr?ng trong c?ng working filesystem, k? c? source ??i,
UUID m?i ho?c l?i admission. Kh?ng x?a kh?a/rerun. Kaggle session m?i kh?ng c?
ledger c? kh?ng cho ph?p kh?a local ch?ng minh ?? ch?ng tr?ng to?n c?c: Owner
ch? t?o m?t saved job/model, kh?ng ch?y concurrent ho?c t?o session thay th?.
Attached saved Outputs c? marker ? layout chu?n ???c ki?m ?? ch?n replay.

Worker ph?i l? CPython **3.11.9**, Linux x86_64, Torch **2.6.0+cu124**,
torchvision **0.21.0+cu124**, CUDA12.4, FP16/eager/batch1/cuda:0; GPU1 ch? quan
s?t. Kh?ng fallback Python, precision ho?c t?i weights. Ki?m t?t c? SHA256,
source/config/manifest, decode160 ?nh, dependencies/ABI, disk, RAM/cgroup,
CUDA/driver/T4/per-GPU VRAM v? child FP16 tr??c consumption; ki?m l?i sau ??.
Admission c?n28 GiB scratch +4 GiB output (32 GiB n?u c?ng filesystem).
Driver d?ng compatibility floor525.60.13 thay allowlist ch?a quy?t ??nh;
RAM>=4 GiB, live scratch/output>=1 GiB m?i n?i, GPU0 headroom>=256 MiB.
C?c reserve k? thu?t kh?ng ??m b?o checkpoint th?c fit; OOM v?n d?ng.

**Ch?nh s?ch d?ng ???c thay ??i c?ng khai ?? reviewer ??nh gi?:** l?i k? thu?t,
NaN/Inf, m?t raw/custody, thi?u t?i nguy?n ho?c h?t12 gi? d?ng ngay. INVALID,
l?p sequence, l?ch nh?n v? l?i Normal/hazard ???c ghi ?? review sau l??t ch?y;
ch?a c? ng??ng khoa h?c ???c quy?t ??nh n?n kh?ng t? ??t ng??ng hay d?ng v?
thi?u GT support ? m?c s?m. Kh?ng c? file CONTINUE ho?c quy?t ??nh Lead gi?.
C? th? ti?u ??160 calls d? behavior k?m; k?t qu? kh?ng ???c t? n?ng th?nh PASS.

Raw IDs/logits/request ???c l?u tr??c parser; parser/C1/HNLO, model revision,
checkpoint v? config effective/legacy hashes gi? nguy?n. ?nh ch?a g?i l?
NOT_ATTEMPTED. Archive ch?a execution/slot/consumption log,160 accounting,
raw/checkpoints/technical decisions, behavior observations v? receipts.
Kh?ng ch?a ?nh/weights. Hard kill/VM loss/disk failure c? th? m?t ZIP ho?n ch?nh;
gi? m?i bytes c?n l?i v? kh?ng ch?y l?i. CPU synthetic PASS kh?ng l? GPU PASS.
"""
    result["cells"][0]["source"] = instructions.splitlines(True)
    result["cells"][1]["source"] = code.splitlines(True)
    result["cells"][1]["id"] = "candidate160-launch"
    result["metadata"]["safeshift"] = {"mode": "CANDIDATE160_OWNER_ACTIVATED", "status": "AWAITING_INDEPENDENT_REVIEW",
        "base": BASE, "package_base": PACKAGE_BASE, "runtime_ref": ref, "model_key": key, "model": spec,
        "source_sha256": source_hash(repo), "manifest_sha256": MANIFEST,
        "config": config(key), "configuration_hashes": configuration_hashes(key),
        "max_images": 160, "gpu": "UNVERIFIED", "behavior": "UNVERIFIED"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-ref", required=True)
    args = parser.parse_args()
    for key in KEYS:
        path = ROOT / f"notebooks/SafeShift_CANDIDATE160_{key}.ipynb"
        path.write_text(json.dumps(notebook(key, args.runtime_ref), indent=1, ensure_ascii=False)+"\n",
                        encoding="utf-8", newline="\n")
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
