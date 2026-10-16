# SafeShift

**SafeShift: Evaluating the Validity and Cross-Domain Reliability of Internal Hazard Scores in Vision-Language Models**

Đây là định hướng Seminar được Research Lead chọn để chuẩn bị chốt trên
**InspecSafe-V1**. [DEC-PA3-011](DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
đang ở trạng thái **PROPOSED** và chờ quy trình review/approval của PR; lịch sử
[D9R22](DECISIONS.md#d9r22--prospective-seminar-rq3-disagreement-redesign-2026-10-05)
không bị viết lại và vẫn là phạm vi hiệu lực cho đến khi đề xuất mới được duyệt.

- **RQ1 — Giá trị của tín hiệu nội tại:** điểm nguy cơ nội tại có phân biệt nguy
  cơ tốt hơn các mốc khai thác đầu ra sinh ra trên cùng dữ liệu và cùng tập ID hợp lệ?
- **RQ2 — Tín hiệu nguy cơ hay dấu hiệu gây nhiễu:** khả năng phân biệt còn duy
  trì đến đâu sau khi kiểm soát sự hiện diện của con người, miền công nghiệp và
  nguồn gốc dữ liệu?
- **RQ3 — Độ tin cậy khi chuyển miền:** tỷ lệ bỏ sót nguy cơ và báo động giả của
  quyết định dựa trên điểm nội tại thay đổi thế nào giữa các miền, và giới hạn
  chuyển giao là gì?

RQ3 là đánh giá thực nghiệm, không phải bảo đảm thống kê về an toàn. Kiểm soát
rủi ro nâng cao được dành cho hướng phát triển khóa luận. PA3 là một điểm nội tại
cần kiểm định, không được mô tả là thuật toán mới. Đóng góp dự kiến là giao thức
so sánh công bằng, phân tích gây nhiễu/tính hợp lệ và đánh giá giới hạn chuyển miền.

Seminar cuối cùng bắt buộc đủ bốn mô hình: **Qwen2.5-VL-3B-Instruct** (baseline),
**Qwen3-VL-8B-Instruct**, **InternVL3-2B-hf** và **Moondream2**. Chỉ Qwen2.5 hiện
có PA3-R2 được [kiểm toán CPU Linux](notes/pa3_r2_cpu_completion_20261015.md):
3.763/3.763 TRAIN SUCCESS, AUROC PA3 0,8266558463706973. Ba mô hình còn lại chưa
có kết quả PA3 tương thích đã xác minh và không được tự gán công thức/token mapping
của Qwen. [Hồ sơ baseline](notes/seminar_baseline_review_2026.md) phân biệt rõ
kết quả đã đo, N/A và các bước cần phê duyệt.

Không có quyền thực thi mới từ tài liệu này. Mọi phép đo mới, truy cập nhãn hoặc
annotation, lựa chọn ngưỡng, GPU inference và TEST cần quyết định cùng authority
riêng. Protocol freeze vẫn PENDING; raw output phải được lưu trước parse/tổng hợp.

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md) và [TASKS.md](TASKS.md).
2. Đặt bản InspecSafe-V1 được phép sử dụng trên máy local theo [data/README.md](data/README.md). Dataset không được commit vào Git.
3. Theo dõi trạng thái trong [TASKS.md](TASKS.md); ghi phát hiện trong `notes/`, quyết định trong [DECISIONS.md](DECISIONS.md), và các lần chạy được duyệt trong [EXPERIMENTS.md](EXPERIMENTS.md).

Mọi đường dẫn được tính từ repository root. Dữ liệu, tokenizer, model weights và
raw model outputs giữ local; tài liệu chỉ version-control các tổng hợp nhỏ đã kiểm tra.

Hạ tầng pre-freeze, lệnh kiểm thử offline và trạng thái 8 prerequisite được ghi tại
[notes/pre_freeze_implementation.md](notes/pre_freeze_implementation.md).
Config/template: `configs/pre_freeze/`; schema: `schemas/`; code: `safeshift/protocol/`.
`protocol_freeze_commit_sha: PENDING`. Adapter chưa có transport gọi API.

## Cấu trúc

```text
SafeShift/
├── AGENTS.md          # Quy tắc làm việc và reproducibility
├── ROADMAP.md         # Kế hoạch W1–W8
├── TASKS.md           # Checklist chi tiết W1
├── DECISIONS.md       # Template quyết định nghiên cứu
├── EXPERIMENTS.md     # Template log thí nghiệm
├── README.md
├── .gitignore
├── data/
│   ├── README.md      # Hướng dẫn dữ liệu local
│   ├── raw/           # InspecSafe-V1 gốc, không đưa lên Git
│   ├── manifests/     # Inventory/manifest nhỏ được kiểm tra
│   └── processed/     # Dữ liệu dẫn xuất local, không đưa lên Git
├── scripts/           # Script audit/thực thi sẽ bổ sung sau
├── safeshift/         # Code dùng lại sẽ bổ sung cùng test
├── notebooks/         # Khảo sát có thể tái lập
├── outputs/
│   └── figures/       # Figure nhỏ được phép chia sẻ
├── notes/             # Ghi chú và báo cáo audit
├── tests/             # Test cho code dùng lại
└── paper/             # Bản thảo bài báo
```

Các file `.gitkeep` giữ thư mục trống trong Git. Dữ liệu, raw model outputs và checkpoint được giữ local; chỉ chọn manifest/figure nhỏ đã kiểm tra quyền chia sẻ để version control.
