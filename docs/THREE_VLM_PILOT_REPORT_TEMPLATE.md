# Pilot report — template, NOT_RUN

Không điền kết quả giả. Điền từ archive đã hash-verify và CPU replay, giữ riêng
primary 160 và supplementary ≤20; ghi source/config/manifest/archive hashes,
approval refs, attempts và môi trường. Không đổi ngưỡng sau khi xem output.

| Model | Classification | HNLO capture | Alignment | CPU replay | Valid HNLO / planned | GPU overhead | Role / recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| google/gemma-3-4b-it | NOT_RUN | HNLO_UNVERIFIED | UNVERIFIED | NOT_RUN | N/A | NOT_MEASURED | INCONCLUSIVE/BLOCKED |
| microsoft/Phi-3.5-vision-instruct | NOT_RUN | HNLO_UNVERIFIED | UNVERIFIED | NOT_RUN | N/A | NOT_MEASURED | INCONCLUSIVE/BLOCKED |
| HuggingFaceTB/SmolVLM2-2.2B-Instruct | NOT_RUN | HNLO_UNVERIFIED | UNVERIFIED | NOT_RUN | N/A | NOT_MEASURED | INCONCLUSIVE/BLOCKED |

Đính kèm comparison.csv đủ mỗi planned ID, báo riêng ID thiếu/error/INVALID,
class/domain support, first12 và tail, retries/native calls, input/GT/Qwen-source
provenance. Qwen không verify thì để null, không suy từ composite counts.

Mỗi model cần primary counts (planned/attempted/SUCCESS/INVALID/ERROR/
NOT_ATTEMPTED), 4×5, accuracy/Macro-F1/BA/per-class recall, FNR/FPR denominators,
unavailable/bounds, label distribution/domain breakdown, time/image/total,
peak VRAM từng GPU, lỗi OOM/library/preprocessing. Ghi unweighted stratified
metrics là mô tả panel, không ước lượng đại diện TRAIN; Level03 chỉ 8 mẫu và các
ảnh phụ thuộc nhau, không trình CI độc lập ảnh như bằng chứng xác nhận.

Tập false-safe supplementary: số ca Qwen đã chọn, model nhận ra Anomaly, model
cũng false-safe, invalid/error/unattempted; danh sách ID giữ riêng. Không gọi là
tỷ lệ bắt lỗi của toàn TRAIN. HNLO AUROC chỉ validated rows với class supports
và coverage; không so xác nhận với Qwen3 khác cohort/protocol.

Mỗi kết luận nêu TECHNICAL_PASS/FAIL, QUALITY_RED_FLAG nếu có,
GO_FULL_TRAIN_RECOMMENDED/NO_GO_FULL_TRAIN/INCONCLUSIVE/BLOCKED và lý do. Tách
classification-only khỏi đủ điều kiện nghiên cứu HNLO. Đối chiếu ngưỡng đã duyệt,
không bù metric thiếu bằng Accuracy. Full TRAIN vẫn cần ChatGPT review archive
và Owner grant riêng; kết luận pilot không tự kích hoạt quyền chạy.
