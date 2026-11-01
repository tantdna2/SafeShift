# SafeShift

SafeShift nghiên cứu độ tin cậy của mô hình thị giác–ngôn ngữ (VLM) khi đánh giá
ảnh an toàn công nghiệp: mô hình phân loại sai ở đâu, lỗi nguy hiểm tập trung
ở nhóm nào, và bất đồng giữa các mô hình có giúp nhận diện quyết định thiếu
tin cậy hay không. Một nhãn có vẻ hợp lý hoặc AUROC cao chưa đủ để kết luận
hệ thống có thể dùng cho quyết định an toàn.

**Foundation V1** cung cấp package Python, validation, phép đếm đánh giá cơ bản
và demo CPU tổng hợp. Code hiện tại chưa chạy mô hình hoặc đọc dataset thật;
các kết quả nghiên cứu được dẫn dưới đây thuộc snapshot lịch sử.

## Phạm vi nghiên cứu

Dataset là **InspecSafe-V1**, với năm miền công nghiệp và bốn mức nhãn nguyên
gốc `Level01`–`Level04`; Level01 nguy hiểm nhất, Level04 là Normal. Theo audit
lịch sử, có 5.013 ảnh: 3.763 TRAIN và 1.250 TEST. Giữ split và nhãn nguyên bản;
xem [nguồn, dữ liệu và giới hạn](docs/DATA_AND_ETHICS.md).

Bốn mô hình thuộc yêu cầu Seminar: **Qwen2.5-VL-3B-Instruct,
Qwen3-VL-8B-Instruct, InternVL3-2B-hf và Moondream2**.
[D9R22 và successor Owner](docs/RESEARCH_OVERVIEW.md) giữ ba lõi phân loại xuyên
miền, lỗi nghiêm trọng và bất đồng. [Quyết định M1](docs/research/DECISIONS.md)
ghi lựa chọn Owner tích hợp HNLO trong Seminar hồi cứu và dùng HNLO+bất đồng
để xếp ưu tiên kiểm tra ở Khóa luận. Successor có hiệu lực sau kiểm chứng/merge;
khi PR còn Draft, D9R22 vẫn có hiệu lực. Moondream2 N/A được chấp nhận ở cấp
dự án cho định lượng Seminar, không tuyên bố ngoại lệ học vụ đã được duyệt.

Hướng dùng **Hazard–Normal Label Log-Odds (HNLO, tên kỹ thuật lịch sử PA3)**
để nghiên cứu giá trị điểm nội tại, yếu tố gây nhiễu và khả năng chuyển miền
được chọn trong phạm vi M1 trên; DEC-PA3-011 lịch sử vẫn **PROPOSED**, không
sửa hồi tố hoặc duyệt toàn bộ hướng A/C độc lập. HNLO không phải xác suất nguy
cơ đã hiệu chuẩn. [Protocol/config M2](docs/research/SEMINAR_PROTOCOL.md) đã soạn,
**còn review độc lập và Owner duyệt version/N/A**, chưa frozen hoặc mở M3.
Quyền dữ liệu/GPU/TEST và yêu cầu học vụ chưa được cấp từ quyết định đề tài.

## Bằng chứng lịch sử tiêu biểu

Các số sau chỉ mô tả TRAIN đã phơi nhiễm, không chứng minh khả năng khái quát hóa:

| Mô hình | HNLO AUROC | Mức bằng chứng và giới hạn |
| --- | ---: | --- |
| Qwen2.5 | 0,8266558463706973 | Raw audit CPU Linux lịch sử PASS, 3.763/3.763 SUCCESS; nhãn sinh ra cảnh báo cả 3.014 Normal. |
| InternVL3 | ≈0,886182 | Tái tính từ saved score, không phải raw audit mới; nhãn cũng cảnh báo cả 3.014 Normal. |
| Qwen3 V4-success gốc | 0,9527927338600111 | Đã khép S2 gốc/saved-score ngày 25/10: 3.539/3.763 SUCCESS (94,0473%); không raw audit mới. Recovery224 giữ riêng, không pooling baseline. |
| Moondream2 | Chưa có kết quả tương thích đã audit | Vẫn là mô hình bắt buộc; chưa hoàn tất raw-logit capture/validation và kết quả TRAIN cho hướng HNLO. |

Nguồn: [CPU audit Qwen2.5](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md)
và [báo cáo ba mô hình ngày 23/10](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/reports/three_model_scientific_analysis_20261023.md).
Xem [kết quả và giới hạn](docs/RESULTS_AND_LIMITATIONS.md) trước khi sử dụng các số này.
Foundation V1 không tái chạy hoặc nâng trạng thái kiểm toán của bằng chứng cũ.

[Hồ sơ PR #131](docs/SOURCE_FEASIBILITY_GATE_20261024.md) bổ sung CPU saved-score
verification và 40 sensitivity variants **PROPOSED**; ba model so cùng 3.539
V4-success IDs, giữ riêng kết quả Q2.5/IVL3 đầy đủ và recovery. Bản ghép V4+
recovery 0,952935 trong hồ sơ lịch sử vẫn REPORTED, không benchmark chính thức.

## Chạy trên CPU

Từ repository root, dùng **Python 3.11+**. Tests và demo chỉ dùng standard library:

```console
python -B -m unittest discover -s tests -v
python -B -m scripts.demo_cpu
python -B -m scripts.demo_triage_cpu --budget 3 --tie-seed public-demo
```

Demo tạo sáu bản ghi viết tay, gồm một dự đoán INVALID, rồi xuất JSON có thông
báo **SYNTHETIC DEMO — NOT RESEARCH RESULT**. Không cần GPU, ảnh hoặc thư viện AI.
Không đưa số demo vào bảng kết quả khoa học. Dùng lệnh module từ root để Python
tìm package; demo không được đóng gói như một backend hoặc công cụ suy luận.

Demo T2 so ba queue không học: HNLO-only, peer-only và combined; tính chung
ca bắt buộc và ca xếp hạng trong K, giữ missingness/backlog/OVERLOAD. API và
quy tắc đề xuất ở [kiến trúc T2](docs/ARCHITECTURE.md#t2-cpu-synthetic-triage--01112026).
Chỉ dùng fixture tổng hợp; seed demo công khai, không secret thật. Đưa một ảnh
vào queue không chứng minh phát hiện/sửa nguy hiểm hoặc cải thiện false-safe.

Cài package để import từ dự án khác (tùy chọn, trong virtual environment):

```console
python -m venv .venv
```

Kích hoạt bằng `.venv\Scripts\Activate.ps1` trên PowerShell hoặc
`source .venv/bin/activate` trên Linux/macOS, rồi chạy:

```console
python -m pip install -e .
python -c "import safeshift; print(safeshift.__file__)"
```

Package không có runtime dependencies. Pip cần setuptools/wheel cho bước build;
không cần cài package để chạy tests/demo từ repository root.

## Đọc và phát triển code

| Vị trí | Chức năng |
| --- | --- |
| `safeshift/data/` | Bản ghi trong bộ nhớ, nhãn chuẩn và validation; không phải dataset parser. |
| `safeshift/evaluation/` | Ma trận nhầm lẫn, support, recall; giữ INVALID trong mẫu số. |
| `safeshift/models/` | Hợp đồng đầu vào/đầu ra và typing interface; inference chưa triển khai. |
| `scripts/demo_cpu.py` | Ví dụ tổng hợp xác định, JSON ra stdout. |
| `tests/` | Smoke tests và kiểm thử tổng hợp cho code đang hoạt động. |
| `docs/` | Phạm vi, kiến trúc, dữ liệu, bằng chứng, lộ trình và lịch sử. |

Đọc [AGENTS.md](AGENTS.md) và [ARCHITECTURE](docs/ARCHITECTURE.md) trước task code.
Theo dõi phần thiếu và điều kiện phê duyệt ở [ROADMAP](docs/ROADMAP.md).
Code dùng lại nằm trong package, chỉ thêm thư mục khi có chức năng cụ thể.

## Kaggle TRAIN pilot ba VLM — PREP

[Issue #145: Smol readiness và Gemma gate](docs/SMOL_KAGGLE_READINESS_145.md)
bổ sung real-loader CPU meta, native synthetic processor và 160-call scripted
raw/HNLO/report/ZIP; yêu cầu `num2words/docopt` được khóa riêng cho Smol 4.51.3.
Đây là nghiệm thu phần mềm, không dự đoán Smol thật. Phi a6 đã consumed với
0/160 C1 JSON hợp lệ theo biên bản GitHub; Gemma vẫn BLOCKED do 10 file gated 401.
Không tự đổi C1/parser/HNLO hoặc chạy/cấp grant từ Draft này.

[Runbook pilot](docs/KAGGLE_THREE_VLM_PILOT.md) mô tả ba notebook Gemma/Phi/Smol,
selector 160+≤20 TRAIN, native runner/raw writer, HNLO probe/replay, report và
resume. Đây là code PREP chờ review/grant, chưa là kết quả Kaggle/HNLO hoặc thay
roster lịch sử. FULL TRAIN khóa, TEST đóng; xem [technical audit](docs/THREE_VLM_TECHNICAL_AUDIT.md).

Kernel Kaggle Python 3.13 chỉ điều phối stdlib. Phi/Smol dùng worker CPython
3.12/3.11 trong scratch venv độc lập; thiếu `ensurepip` được xử lý bằng venv
`--without-pip` và wheel pip source/hash-locked cài đúng target qua `pip --python`.
Hai notebook environment preflight kiểm pins/CPU ABI mà không đọc grant/data,
gọi GPU hoặc tải weights. Xem
[runtime audit và đối chiếu Qwen3](docs/KAGGLE_PYTHON_RUNTIME_AUDIT_20261028.md).

Toàn bộ 693 file trước reset vẫn ở các ref bất biến, được liệt kê trong
[HISTORY](docs/HISTORY.md). Không phục hồi hệ thống cũ vào main, chuyển quyền
thực thi cũ sang code mới, hoặc tự sửa sáu Draft PR cũ. Dữ liệu, raw output,
checkpoint và secrets nằm ngoài Git.
