"""Build the MiniCPM execution candidate from exact committed runtime bytes."""
import argparse
import json
from pathlib import Path

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.minicpm_resampler_fp32 import ID
from scripts.build_fresh_fulltrain_notebooks import notebook as fresh_notebook

OUTPUT = "notebooks/SafeShift_FULLTRAIN_MINICPM4_FP32.ipynb"


def notebook(ref, repo=ROOT, *, capsule_sha256=None, release_locator=None, release_version=2):
    require(type(release_version) is int and release_version in (2, 4, 5, 6, 7, 8)
        and (release_version == 2 or release_locator is not None), "MINICPM_NOTEBOOK_RELEASE_VERSION")
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
    if release_locator is not None:
        require(capsule_sha256 is not None and type(release_locator) is dict
            and set(release_locator) == {"comment_id", "body_sha256"}
            and type(release_locator["comment_id"]) is int and release_locator["comment_id"] > 0,
            "MINICPM_EXACT_RELEASE_LOCATOR")
        require_hash(release_locator["body_sha256"])
        nb["cells"][1]["source"] = ["import time\n", "minicpm_notebook_started_unix = time.time()\n", *nb["cells"][1]["source"]]
        nb["cells"][-1]["source"] = ("from safeshift.fulltrain.minicpm_execution import run_capsule\n"
            f"run_capsule('/kaggle/input', {capsule_sha256!r}, {release_locator!r}, repo=root, "
            "started_unix=minicpm_notebook_started_unix)\n").splitlines(True)
        nb["metadata"]["safeshift"].update(mode="MINICPM_FULLTRAIN_RELEASE_V" + str(release_version),
            status="AUTHENTIC_RELEASE_AND_SIGNED_TICKET_REQUIRED", execution_release=release_locator)
        nb["cells"][0]["source"] = """# MiniCPM-V-4 — Full TRAIN — Owner UI

Chỉ chạy khi handoff đã kiểm quyền nguồn, Input/version, quota và signed ticket.
1. Import notebook này và gắn đúng năm Input/version trong handoff.
2. Kiểm Private, Internet On, T4 x2 và thời hạn/caps hiển thị trong handoff.
3. Save Version > Save & Run All một lần; gửi URL/version khi terminal.

Không sửa cell hoặc chạy lại version. Preflight tích hợp trước load/calls.
Một job có thể dừng an toàn trước hết TRAIN; Antigravity kiểm ZIP/history rồi
chuẩn bị NOT_ATTEMPTED tiếp theo. Giữ tất cả raw/lỗi. Strict C1, FP32 resampler,
FP16 weights, HNLO N/A; TEST đóng. Không có quyền thật/ticket thì BLOCKED.
""".splitlines(True)
        if release_version == 4:
            nb["cells"][0]["source"] = """# MiniCPM-V-4 — Full TRAIN — Owner UI restart V4

Run only with the current signed RELEASED_FOR_OWNER_UI handoff from Antigravity.
1. Upload this exact notebook and attach its five pinned nested Input versions.
2. Select Private / Python / Internet On / GPU T4x2.
3. Save Version > Save & Run All ONCE before start_before; send the version URL.
Integrated admit/setup/cpu/gpu precede model load and native generate.
Do not run cells manually, restart, create a second version or resubmit.
Owner starts the job; Antigravity continues its same Operator session to observe
and collect. Old attempts supply zero inherited predictions; start at ordinal0.
Historical reservations/errors/raw stay recorded; project reservation ceiling
is distinct from current Kaggle quota. No automatic account switching.
Original3763 TRAIN, strict C1, FP16 weights/FP32 resampler, HNLO N/A; TEST closed.
""".splitlines(True)
        if release_version == 5:
            nb["metadata"]["safeshift"]["source_transition"] = "safeshift-minicpm-v44-source-repair-v1"
            nb["cells"][0]["source"] = """# MiniCPM-V-4 — Full TRAIN — reviewed V4-4 source repair V5

Run only with the current signed RELEASED_FOR_OWNER_UI handoff from Antigravity.
1. Import this exact notebook and attach its five pinned Input versions.
2. Select Private / Python / Internet On / GPU T4x2; check the signed expiry.
3. Save Version > Save & Run All ONCE before expiry; send the version URL.
Real Master/TRAIN layout and native PIL/RGB input bytes were checked read-only.
Integrated admit/setup/cpu/gpu still precede native load/generate; model fit is
not established by CPU rehearsal. Preserve all raw/errors/receipts and old holds.
Do not reuse V4-4's notebook, capsule or ticket. No manual cell edits or retry.
Original3763 TRAIN, FP16 weights/FP32 resampler, strict C1, HNLO N/A; TEST closed.
""".splitlines(True)
        if release_version in (6, 7, 8):
            nb['metadata']['safeshift']['source_transition'] = 'safeshift-minicpm-v5-ram-repair-v1'
            nb['metadata']['safeshift']['resource_stages'] = ['admit', 'setup', 'reclaim', 'cpu', 'gpu', 'native']
            nb['cells'][0]['source'] = '''# MiniCPM-V-4 — Full TRAIN — RAM repair V6

Use only the current RELEASED_FOR_OWNER_UI handoff from the historical Operator.
1. Import this exact notebook and attach its five pinned Input versions.
2. Select Private / Python / Internet On / GPU T4x2; check signed expiry.
3. Save Version > Save & Run All ONCE before expiry; send the version URL.

Integrated preflight verifies all 3,763 TRAIN images, software, RAM and storage.
Each stage runs under a hard supervisor. Runtime-owned cache advice after setup
is followed by the unchanged 16 GiB RAM gate; recovery is never assumed.
Failure: retain all Output/log/ZIP/SHA and stop; no edited cell or reused ticket.
Full coverage may require serial continuation over NOT_ATTEMPTED images only.
FP16 weights, FP32 resampler, strict C1, HNLO N/A; TEST closed.
CPU checks do not prove final-source model fit or full-run completion.
'''.splitlines(True)
        if release_version == 7:
            nb['metadata']['safeshift']['continuation_route'] = 'safeshift-minicpm-offline-continuation-v3'
            nb['cells'][0]['source'] = '''# MiniCPM-V-4 Full TRAIN — offline serial continuation V7

Chỉ dùng handoff có vé ký mới từ Operator MiniCPM gốc, sau release đúng source.
1. Import notebook đúng slug/version1; upload capsule mới Private và gắn 5 Input.
2. Kiểm Private/Python/Internet On/T4x2, quota tuần thật và hạn vé; VM cũ đã terminal.
3. Save Version > Save & Run All một lần. Tải cả hai ZIP/sidecar và proof terminal.

Antigravity chỉ kiểm offline và chuẩn bị NOT_ATTEMPTED tiếp theo. Không gọi API,
không duyệt GitHub từng job. OFFLINE_VERIFIED_PROVISIONAL chưa là kết quả chính thức.
Chỉ đối soát provider từng job và admission một lần sau đủ 3763 ordinal.
admit → setup → reclaim → cpu → gpu → native, signed RAM floor 16384 MiB.
FP16 weights/FP32 resampler/C1 strict/HNLO N/A; TEST đóng. Giữ mọi raw/lỗi/holds.
KAGGLE_VENV_LAYOUT_UNVERIFIED; FAIL_CLOSED_BUT_OWNER_RUN_CAN_STILL_ABORT.
Không sửa cell, tái dùng vé, tạo version2 hoặc tự retry; quota vẫn có thể bị tiêu.
'''.splitlines(True)
        if release_version == 8:
            nb["metadata"]["safeshift"]["continuation_route"] = "safeshift-minicpm-offline-continuation-v4"
            nb["cells"][0]["source"] = """# MiniCPM-V-4 Full TRAIN — Serial 8 source transition

Use the current private capsule and signed handoff from the original Operator.
1. Import the exact notebook and attach the five versioned Inputs in the handoff.
2. Check Private, Python, Internet On, T4 x2, current quota and signed expiry.
3. Save Version > Save & Run All once. Preserve every Output and the version URL.

The parent verifies GitHub source authority. Each stage rechecks the release and PR
directly and verifies the pinned proof before starting work. The signed 16 GiB
floor and supervised page-cache stage still apply. An authority or resource failure
requires custody review before another job. Preserve all historical reservations.
TRAIN only. FP16 weights, FP32 resampler, strict C1, HNLO N/A.
""".splitlines(True)
    return nb


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime-ref", required=True)
    p.add_argument('--ram-repair-candidate', action='store_true')
    args = p.parse_args()
    output = 'notebooks/SafeShift_FULLTRAIN_MINICPM4_RAM_V6_CANDIDATE.ipynb' if args.ram_repair_candidate else OUTPUT
    nb = notebook(args.runtime_ref)
    if args.ram_repair_candidate:
        nb['metadata']['safeshift'].update(planned_release_version=6,
            source_transition='safeshift-minicpm-v5-ram-repair-v1',
            resource_stages=['admit', 'setup', 'reclaim', 'cpu', 'gpu', 'native'])
        nb['cells'][0]['source'] = ['# MiniCPM-V-4 Full-TRAIN — V6 RAM repair candidate\n',
            '\n', '**DRAFT / BLOCKED.** CPU preparation only. No signed release, ticket or Owner Run.\n',
            'The Operator generates the exact executable V6 notebook only after review/audit/merge/release.\n',
            'Owned runtime cache advice follows isolated setup; unchanged 16 GiB RAM gates apply throughout.\n',
            'Original 3,763 TRAIN IDs; FP16 weights, FP32 resampler, strict C1; HNLO N/A; TEST closed.\n']
    (ROOT / output).write_bytes((json.dumps(nb, indent=1,
                                          ensure_ascii=False) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
