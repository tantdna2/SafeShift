# SafeShift

**SafeShift: Benchmarking Cross-Domain Generalization and Evidence Grounding in Vision-Language Models for Industrial Safety Assessment.**

Repository nghiên cứu cho đề tài Seminar về Computer Vision, sử dụng **InspecSafe-V1** để nghiên cứu khả năng khái quát hóa giữa các domain và mức độ gắn kết đánh giá an toàn công nghiệp của VLM với bằng chứng hình ảnh.

Mục tiêu **Week 1 là Dataset Audit**: hiểu cấu trúc, nhãn, chất lượng, split và khả năng hỗ trợ đánh giá cross-domain/evidence grounding của dataset trước khi chạy VLM. Repository hiện chỉ có cấu trúc và tài liệu; chưa có parser, inference hoặc kết quả nghiên cứu.

## Bắt đầu

1. Đọc [AGENTS.md](AGENTS.md), [ROADMAP.md](ROADMAP.md) và [TASKS.md](TASKS.md).
2. Đặt bản InspecSafe-V1 được phép sử dụng trên máy local theo [data/README.md](data/README.md). Dataset không được commit vào Git.
3. Thực hiện checklist W1; ghi phát hiện thực tế trong `notes/`, quyết định trong [DECISIONS.md](DECISIONS.md), và các lần chạy sau này trong [EXPERIMENTS.md](EXPERIMENTS.md).

Mọi đường dẫn được tính từ repository root. Dependency và lệnh chạy audit sẽ được bổ sung khi triển khai code; hiện chưa cần cài môi trường ML.

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
