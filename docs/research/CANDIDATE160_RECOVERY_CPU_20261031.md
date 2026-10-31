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

Runtime/tested snapshot/checksums/counts sẽ được ghi tại đây và receipt sau khi
suite final chạy xong; không dùng kết quả development để chứng nhận HEAD final.

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
