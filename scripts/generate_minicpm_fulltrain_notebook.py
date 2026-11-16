"""Build the MiniCPM execution candidate from exact committed runtime bytes."""
import argparse
import json
from pathlib import Path

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.minicpm_resampler_fp32 import ID
from scripts.build_fresh_fulltrain_notebooks import notebook as fresh_notebook

OUTPUT = "notebooks/SafeShift_FULLTRAIN_MINICPM4_FP32.ipynb"


def notebook(ref, repo=ROOT, *, capsule_sha256=None):
    nb = fresh_notebook("minicpm4", ref, repo)
    code = "".join(nb["cells"][1]["source"])
    old_import = "from safeshift.fulltrain.preflight import prepare as launch"
    old_call = f"launch('minicpm4', expected_source_sha256, root, {ref!r}, kind='PREPARATION')"
    require(code.count(old_import) == code.count(old_call) == 1, "EXACT_SHARED_BOOTSTRAP")
    code = code.replace(old_import, "from safeshift.fulltrain.minicpm_notebook import prepare as launch")
    code = code.replace(old_call, f"launch(expected_source_sha256, root, {ref!r})")
    compile(code, OUTPUT, "exec")
    nb["cells"][1]["source"] = code.splitlines(True)
    nb["cells"][0]["source"] = """# SafeShift — MiniCPM-V-4 FP32 — fresh full TRAIN execution candidate

**BLOCKED / NOT LIVE VERIFIED.** This source version cannot run a model even
if a request file is supplied. Review, independent Antigravity audit, separately
authorized merge and source activation/authority are still required.

Original 3,763 TRAIN IDs/order/image SHA; series `fresh171-minicpm4-v1`.
FP16 weights, eager, `minicpm4-resampler-attention-fp32-v1`: only resampler
scores/softmax/value product FP32, output cast back to native dtype. Reuses the
reviewed adapter, isolated CPython3.11.9/Transformers4.51.3 worker, native
processor/generate path and strict C1 JSON parser. INVALID remains INVALID.
LABEL_ONLY, HNLO N/A. No Candidate160/smoke/history prediction imports.

Run the CPU preparation cell locally to export environment/source/checkpoint/
pipeline/readiness evidence and ZIP/SHA256, without Input reads, package installs,
scratch allocation, GPU, weights, attempts or production-ledger consumption.
Repeat runs use distinct directories. This is the diagnostic mode of this notebook.

The final cell targets the actual supervised native runtime, not a notebook-local
mock loop. Its release gate currently stops BEFORE reading even the request file.
Do not delete that gate or call internal functions to activate an experiment.

Exact attachment/version/mount/hash table and remaining gates:
`docs/QWEN_MINICPM_FULLTRAIN_REVIEW.md`. The pilot160 Input is not a full-TRAIN
bundle. Existing checkpoint `nguynanhtn/safeshift-prepare-minicpm4/1` can be reused;
the original TRAIN/master mounts can be bound explicitly without copying images
via the `original_inputs` request extension. Actual dataset versions, projection
seal, rights/release/caps still need admission; no version is guessed here.
No default 160-call shard or promised RAM/VRAM fit; limits must be explicitly
authorized and measured with allocation, cgroup, driver/CUDA and export reserves.

After a future reviewed activation: stop prior VM, import every same-series ancestor
ZIP with explicit SHA in order into a separate model workspace; pass the exact
reviewed request. Resume NOT_ATTEMPTED only. Missing/corrupt/unknown history STOP;
repair requires exact-target diagnosis/fix/regression and authority. No automatic
cross-machine takeover or global exactly-once claim. Retain every failure/raw/log.
Download attempt ZIP, `.zip.sha256.json` and supervisor ZIP/sidecar independently.
Never infer completion from scheduled count or pool scientific series. TEST closed.
""".splitlines(True)
    nb["cells"].append({"cell_type": "code", "id": "native-execution-boundary",
        "metadata": {}, "execution_count": None, "outputs": [], "source": """# No request, caps or execution grant is fabricated by this notebook.
REQUEST_FILE = None
REQUEST_SHA256 = None
if REQUEST_FILE is None:
    print("BLOCKED: no released execution request; native calls=0")
else:
    from safeshift.fulltrain.minicpm_notebook import run_request
    run_request(REQUEST_FILE, REQUEST_SHA256, repo=root)
""".splitlines(True)})
    nb["metadata"]["safeshift"].update(mode="FULLTRAIN_MINICPM_EXECUTION_CANDIDATE",
        status="BLOCKED_NOT_LIVE_VERIFIED", model_id="openbmb/MiniCPM-V-4",
        model_revision="6f69a8235885be89608f3a71ffd40695b379e1e7",
        implementation=ID, policy="LABEL_ONLY", planned_count=3763,
        execution_caps=None, final_source_live_verification="NOT_RUN")
    if capsule_sha256 is not None:
        from safeshift.pilot.contract import require_hash
        require_hash(capsule_sha256)
        bootstrap = "".join(nb["cells"][1]["source"])
        prep = f"evidence = launch(expected_source_sha256, root, {ref!r})\nprint(\"Evidence directory:\", evidence)"
        require(bootstrap.count(prep) == 1, "EXACT_MINICPM_PREPARATION_CALL")
        nb["cells"][1]["source"] = bootstrap.replace(prep,
            'print("Source verified; execution remains behind the release gate.")').splitlines(True)
        nb["cells"][-1]["source"] = ("# Capsule prepared by Antigravity; Owner does not edit code.\n"
            "from safeshift.fulltrain.minicpm_ui import run_capsule\n"
            f"run_capsule('/kaggle/input', {capsule_sha256!r}, repo=root)\n").splitlines(True)
        nb["metadata"]["safeshift"]["capsule_sha256"] = capsule_sha256
        nb["cells"][0]["source"] = """# MiniCPM-V-4 Full-TRAIN — Owner UI

**CANDIDATE / CHƯA PHÁT HÀNH.** Bản này giữ khóa quyền trước khi đọc Input.
Chỉ làm ba bước dưới đây khi đã nhận đúng bản được phát hành sau review/audit.

1. Gắn đúng năm Input/version trong handoff Antigravity bàn giao, gồm capsule riêng.
2. Kiểm tra Private, Python, Internet On, GPU T4 x2 và giới hạn lượt được giao.
3. Save Version > Save & Run All đúng một lần; gửi URL/version khi xong.

Không sửa cell, capsule hoặc batch. Lỗi/BLOCKED: giữ mọi Output/log/ZIP/SHA,
không chạy lại; Antigravity thu và đối soát trước lượt tiếp theo.
Giữ nguyên3.763 TRAIN IDs, MiniCPM FP32 resampler/FP16 weights, strict C1,
HNLO N/A. Capsule tự mang request và mọi history; không nhập dự đoán pilot/smoke.
""".splitlines(True)
    return nb


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime-ref", required=True)
    args = p.parse_args()
    (ROOT / OUTPUT).write_bytes((json.dumps(notebook(args.runtime_ref), indent=1,
                                          ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
