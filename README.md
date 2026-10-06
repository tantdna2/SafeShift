# SafeShift

**SafeShift: Benchmarking Cross-Domain Robustness and Disagreement-Aware Reliability in Vision-Language Models for Industrial Safety Assessment**

Repository nghiên cứu Seminar trên **InspecSafe-V1**, theo quyết định prospective
[D9R22](DECISIONS.md#d9r22--prospective-seminar-rq3-disagreement-redesign-2026-10-05).
Phạm vi chính hiện tại là classification-only trên frozen VLM:

- RQ1 không đổi: zero-shot classification robustness giữa 5 miền công nghiệp và
  đồng biến thiên với robot platform; không phát biểu nhân quả.
- RQ2 không đổi: safety-critical error concentration theo Level01–Level04;
  12 Hazard Atoms là primary strata, 7 nhóm A–G là secondary exploratory summaries.
- RQ3 mới: Cross-Model Decision Consistency and Disagreement-Aware Reliability
  under Domain Shift; chỉ tái sử dụng classification predictions của RQ1/RQ2,
  không thêm model call, textual confidence, training hay ensemble model thứ năm.

Bốn classification participants giữ nguyên theo D9R18: Qwen3-VL-8B-Instruct,
Qwen2.5-VL-3B-Instruct, InternVL3-2B-hf và moondream2. PaliGemma vẫn
NOT_PARTICIPATING; SmolVLM2 không được kích hoạt.
`PRIMARY_SEMINAR_GROUNDING=DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE`:
grounding được giữ làm future thesis extension, không phải scientific FAIL,
không còn là Seminar freeze blocker; mọi historical FAIL/PASS được bảo toàn.

Current authority: [scope JSON](configs/pre_freeze/d9r22_seminar_scope.v1.json),
[readiness](notes/w2_d9r22_seminar_readiness.md)
và [redesign/validation note](notes/w2_d9r22_seminar_scope_redesign.md).
Chúng thay thế phạm vi RQ3/grounding và readiness cũ cho Seminar hiện tại;
các briefs D1–D9 và config D9 cũ vẫn là hồ sơ lịch sử, không phải production
contract D9R22. `inspecsafe_inference_authorized=false`; protocol freeze=PENDING.

**Week 1 là Dataset Audit**: hiểu cấu trúc, nhãn, chất lượng, split và khả năng hỗ trợ đánh giá cross-domain/evidence grounding của dataset trước khi chạy VLM. Repository hiện có công cụ audit và hạ tầng pre-freeze offline theo D8. **D8 đã duyệt chưa đồng nghĩa protocol freeze**; chưa chạy inference VLM trên InspecSafe.

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md) và [TASKS.md](TASKS.md).
2. Đặt bản InspecSafe-V1 được phép sử dụng trên máy local theo [data/README.md](data/README.md). Dataset không được commit vào Git.
3. Thực hiện checklist W1; ghi phát hiện thực tế trong `notes/`, quyết định trong [DECISIONS.md](DECISIONS.md), và các lần chạy sau này trong [EXPERIMENTS.md](EXPERIMENTS.md).

Mọi đường dẫn được tính từ repository root. Dependency và lệnh chạy audit sẽ được bổ sung khi triển khai code; hiện chưa cần cài môi trường ML.

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
