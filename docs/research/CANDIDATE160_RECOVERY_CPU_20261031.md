# Candidate160 recovery — bằng chứng CPU31/10/2026

BASE: `6252a7de91d9d98bd68a33b9bc13ae9888f2b9da` (main sau PR155).
Phạm vi: code/notebooks/tests/docs, chỉ fixtures tổng hợp; không Kaggle/GPU,
weights, private TRAIN/GT/TEST hoặc attempt thực nghiệm. Antigravity chưa audit,
không merge. Scientific result selection PENDING; không scientific pooling.

## Các tình huống kiểm thử

`tests/test_candidate160_recovery.py` bao phủ hai model: GPU admission lỗi giả,
load lỗi, OOM giữa chừng, raw write ENOSPC, raw đã bền nhưng mất result, INVALID
hoàn thành, directory/ZIP ở phiên khác và ít nhất hai thế hệ recovery, duplicate
copies, orphan/contradictory/tampered history, history plan đổi, legacy blocked/
consumed/replacement1, resume no-op, rerun toàn bộ và tiếp tục đúng series mới.
Khóa threads/process exit và Linux worker giữ descriptor sau supervisor chết
được kiểm riêng. V1 authority/slot/pilot tests giữ đường gọi compatibility cũ;
production v2 được kiểm qua supervisor thật với các child test doubles.

Notebook tests kiểm mọi cell, source payload/hash/pins, deterministic builder,
repeat bootstrap chỉ tái dùng bytes giống nhau, Inputs vắng → BLOCKED archive
không GPU, và preflight không slot/consumption/model call. Bốn notebook candidate
được rebuild cùng runtime; sáu notebook pilot/history giữ nguyên bytes.

## Tái lập

```console
python -B -m unittest discover -s tests -p test_candidate160_recovery.py -v
python -B -m unittest discover -s tests -v
python -B -m scripts.build_candidate160_notebooks --runtime-ref <exact-runtime-commit>
python -B -m scripts.check_notebook_release --runtime-ref <tested-snapshot-commit> --output data/processed/candidate160-recovery-proof/release-new.json
```

Runtime `0f0d272c60c3a574814c1b0d3dc4a73ee169b30c`; candidate source SHA256
`f2b6af6d23869acea7ed7e6ee35162f7d2d1b9c83bc24c06d3040f1bfc2439cb`.
Exact tested Git export `afbf0307178b2ecfb1d81b7ec2504628bacaaaf0`.
Các thay đổi sau snapshot này chỉ docs/receipts; runtime/tests/notebooks giữ
nguyên. [Index/checksums và receipts](evidence/candidate160_recovery_20261031/index.json).

| Kiểm tra | Kết quả | Phạm vi |
| --- | --- | --- |
| Full exact Linux export |347 =315 PASS +32 SKIP,0 FAIL/ERROR |Python3.14.4, stdlib/scripted CPU; không production worker qualification |
| Notebook release inspection |10/10 PASS |Hai production +hai preflight candidate, sáu historical; builder/embedded bytes/hash/cells |
| Recovery tests mới trong full suite |15/15 PASS |Gồm hai model/supervisor, series/rerun/resume, inherited Linux worker lock |
| Windows CPython3.11.9 |6 focused +4 notebook +1 protected-prefix PASS |11 checks, không full Windows suite/native opt-ins |
| BASE invariants |49 file byte-identical;2 prefix append-only |Pilot/adapter/locks/science/sáu notebook lịch sử, AGENTS/decision log |

Linux full receipt ghi chính xác Python/OS thực tế; stdlib3.14 không là worker
production3.11.9/cu124.32 SKIP:15 candidate native +6 Phi native +9 Smol native,
1 live pip/network,1 Windows junction. Không tính SKIP là PASS hoặc chạy lại
native/weights/GPU chỉ để lấp skips. Các kiểm tra native cũ không chứng nhận
source mới; thay đổi này xác minh orchestration/custody trên fixtures tổng hợp.

Full run đầu ở `568abd37f02aeb0f6655d8d2efaeb3c3e4b48b8e` có347 tests,
313 PASS/32 SKIP/2 FAIL. Test replacement1 lịch sử gọi production v2 rồi đòi
marker v1; đã chuyển về entrypoint compatibility v1. Test protected decisions
đòi whole-file hash trong khi Owner yêu cầu append quyết định; đã kiểm Git object
lịch sử đúng checksum và giữ nguyên toàn prefix main. Lock cũ không sửa.
Correction `afbf030` chỉ đổi hai test; full run cuối0 lỗi như bảng. Receipt lỗi
ban đầu và hash stdout/stderr được giữ riêng, không waive hoặc gọi là BASE lỗi.

Local đầy đủ: `data/processed/candidate160-recovery-proof/release-linux.json`
(lần đầu) và `release-linux-final.json` (lần cuối). Public receipts bỏ stdout/
stderr có temporary paths tổng hợp, giữ checksum log/counts/skip reasons và
original-receipt hashes. Không có ảnh, raw prediction hoặc dữ liệu thật trong Git.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref 0f0d272c60c3a574814c1b0d3dc4a73ee169b30c
python -B -m scripts.check_notebook_release --runtime-ref afbf0307178b2ecfb1d81b7ec2504628bacaaaf0 --output data/processed/candidate160-recovery-proof/release-new.json
```

## Giới hạn

CPU scripted responses không kiểm actual checkpoint loading/model-fit, Kaggle
quota/driver/CUDA/T4 hoặc inference/behavior/HNLO thật. Không chạy native opt-ins,
network/live-pip tests hay GPU trong task. Các lớp adapter/processor/pins/locks
không đổi; không tái dùng CPU report cũ để tự chứng nhận runtime mới.

OS lock chỉ bảo vệ workspace dùng chung; không distributed lock giữa VM. Lịch
sử bị bỏ khỏi Inputs không thể phát hiện từ filesystem trống. Owner phải dừng
job cũ và attach đủ Outputs. Corrupt/torn/missing provenance có thể BLOCKED cho
đến khi bổ sung đúng evidence; không tự xóa hoặc viết lại history để vượt cổng.
History discovery/copy có bounds; dữ liệu lớn hơn bounds cần phương án được
review, không âm thầm bỏ lịch sử để chạy tiếp.
