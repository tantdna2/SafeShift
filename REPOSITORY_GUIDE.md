# SafeShift — bắt đầu từ đây

Hướng dẫn tại `main@934575e1c5064e37dc76a42e5267a639eb20dbbc`, ngày 24/10/2026.
Trang này bổ sung điều hướng và trạng thái bằng chứng mới hơn cho [README](README.md).
README được giữ nguyên vì đang được pin bằng hash trong các source lock thực nghiệm.

SafeShift nghiên cứu tín hiệu nguy cơ bên trong mô hình thị giác–ngôn ngữ trên
InspecSafe-V1, đối chiếu điểm liên tục với nhãn mô hình sinh ra và xem xét các
giới hạn theo miền, nguồn dữ liệu và yếu tố gây nhiễu. **HNLO** là tên trình bày
của phép tính lịch sử **PA3**: `logsumexp(z01, z02, z03) - z04`, với điểm cao hơn
nghiêng về Anomaly. Điểm này chưa phải xác suất hay quyết định theo ngưỡng.

## Đọc dự án trong vài phút

| Bạn cần tìm | Mở tại đây |
| --- | --- |
| Kết quả và giới hạn khoa học mới nhất đã vào main | [Phân tích ba mô hình ngày 23/10](notes/reports/three_model_scientific_analysis_20261023.md) |
| Bằng chứng baseline Qwen2.5 đã kiểm toán | [CPU completion](notes/pa3_r2_cpu_completion_20261015.md), [summary JSON](notes/pa3_r2_cpu_completion_20261015.summary.json) |
| Tài liệu hiện tại, lịch sử và nguồn bằng chứng | [Mục lục notes](notes/README.md) |
| Notebook nào phục vụ kết quả nào | [Mục lục notebooks](notebooks/README.md) |
| Cấu hình, manifest, source lock và authority | [Hướng dẫn configs](configs/README.md) |
| Kế hoạch và thẩm quyền nghiên cứu | [ROADMAP](ROADMAP.md), [DECISIONS](DECISIONS.md), [TASKS](TASKS.md) |
| Kiểm kê và phương án tổ chức giai đoạn 2 | [Báo cáo tổ chức repository](notes/reports/repository_organization_phase1_20261024.md) |
| Báo cáo tổng hợp và kết quả dọn giai đoạn 2 | [Mục lục reports](notes/reports/README.md), [phân loại và kế hoạch tiếp theo](notes/reports/repository_organization_phase2_20261024.md) |

## Trạng thái nghiên cứu và mức kiểm chứng

**DEC-PA3-011 vẫn PROPOSED**; D9R22 vẫn là phạm vi có hiệu lực theo
[decision log](DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16).
RQ1–RQ3 về HNLO và tên đề tài trong README là hướng đề xuất. Báo cáo mới hoặc PR
đã merge không tự phê duyệt hướng nghiên cứu, protocol hay lần chạy tiếp theo.
[ROADMAP](ROADMAP.md) là kế hoạch; các mục lịch sử trong TASKS cần đọc cùng các
bổ sung về sau và bằng chứng của từng lần chạy.

Các số dưới đây chỉ mô tả **TRAIN đã phơi nhiễm**. Level01–03 là Anomaly,
Level04 là Normal; cohort đầy đủ có 3.763 ảnh, 749 Anomaly / 3.014 Normal.

| Mô hình / cohort | HNLO AUROC | Coverage / mẫu số | Mức bằng chứng tại commit này |
| --- | ---: | --- | --- |
| Qwen2.5-VL-3B-Instruct, PA3-R2 | 0,826656 | 3.763/3.763 SUCCESS | Đã tái tính từ raw bằng auditor chính thức trên CPU Linux; còn thiếu outer receipt Shard 1. |
| InternVL3-2B-hf, TRAIN V4 | 0,886182 | 3.763/3.763 saved SUCCESS | Đã tái tính từ điểm lưu trong báo cáo; chưa phải raw audit mới. |
| Qwen3-VL-8B-Instruct, V4 gốc | 0,952793 | Được báo cáo 3.539/3.763 SUCCESS, 1 TECHNICAL_ERROR, 223 NOT_ATTEMPTED | Số do tổng hợp/hồ sơ cung cấp; chưa xác minh độc lập đầy đủ membership và vector điểm S2 gốc. |
| Qwen3, Recovery224 bổ sung | 0,954519 | Được báo cáo 224/224 SUCCESS | Cohort bổ sung; giữ riêng lịch sử V4 và trạng thái `baseline_pooling_allowed=false`. |
| Qwen3, ghép mô tả V4-success + Recovery224 | 0,952935 | Tổng hợp báo cáo 3.763 ảnh | Phân tích xuyên cohort; chưa tái tính độc lập AUROC gộp từ vector điểm gốc đầy đủ, không phải baseline V4 hoàn tất. |
| Moondream2 | N/A | Chưa có kết quả TRAIN HNLO tương thích đã kiểm toán | Vẫn thuộc phạm vi bốn mô hình bắt buộc; không tự loại bỏ hoặc thay bằng mô hình khác. |

Nguồn và phạm vi kiểm chứng: [báo cáo ba mô hình](notes/reports/three_model_scientific_analysis_20261023.md),
[receipt kiểm tra](notes/evidence/three_model_20261023/verification_20261023.json)
và [CPU audit Qwen2.5](notes/pa3_r2_cpu_completion_20261015.md).
Sidecar S2 chạy lại chỉ kiểm tra nhất quán, không chứng minh lượt S2 đầu tiên.

AUROC nhãn nhị phân được báo cáo là 0,5 cho Qwen2.5/InternVL3 và 0,901142 cho
Qwen3 ghép. Hai mô hình đầu luôn sinh Anomaly. Accuracy/FNR/FPR của nhãn sinh ra
khác với chỉ số của điểm HNLO; chưa có ngưỡng HNLO được phê duyệt. RQ1 mới được
hỗ trợ ở mức mô tả; RQ2 chưa kiểm soát confounder, RQ3 mới có khác biệt theo miền.
Chưa có CI phù hợp phụ thuộc nguồn, calibration hoặc bằng chứng khái quát hóa.

## Tìm code và kết quả

| Đường dẫn | Vai trò |
| --- | --- |
| [safeshift/pa3](safeshift/pa3/) | Scorer PA3/HNLO, raw audit và workflow Qwen2.5 native/R2. |
| [safeshift/diagnostics](safeshift/diagnostics/) | Capture, T1, pilot, TRAIN V4, CUDA/driver và Recovery224; gồm code chuẩn bị lẫn code gắn với kết quả đã báo cáo. |
| [safeshift/data](safeshift/data/) | Manifest, validation, duplicate/distribution audit và dữ liệu thực thi. |
| [safeshift/protocol](safeshift/protocol/), [runners](safeshift/runners/), [qualification](safeshift/qualification/) | Hợp đồng, metric, adapter và qualification của các giai đoạn W2/P2. |
| [safeshift/ls1](safeshift/ls1/) | Nghiên cứu LS1 trước đó; một số hàm đánh giá vẫn được code hiện tại dùng lại. |
| [scripts](scripts/) | CLI audit, tổng hợp, generator và công cụ hỗ trợ; không phải mọi script đều là điểm chạy hiện tại. |
| [tests](tests/) | Kiểm thử, fixture tổng hợp và các ràng buộc lịch sử. |
| [notes/evidence](notes/evidence/), [outputs/figures](outputs/figures/) | Bản tổng hợp/receipt nhỏ được phép version control và hình W1. Raw outputs không nằm trong Git. |

Không có một môi trường cài đặt chung cho mọi mô hình. Dùng dependency/version và
commit được runbook tương ứng chỉ định. Từ repository root, kiểm tra tổng hợp đã
commit bằng CPU/standard library, không cần dataset hay checkpoint:

```powershell
python -m scripts.analyze_three_model_summaries --output data/processed/repository_guide_check/aggregate.json
```

Chọn output chưa tồn tại vì script từ chối ghi đè. Lệnh chỉ đối soát aggregate,
không kiểm toán raw, không xác nhận S2 gốc hoặc quyền inference.

## Đọc lịch sử và tái lập an toàn

W1 là nền tảng audit dữ liệu; W2/D9/P2/P2.1, LS1 và PA3 đời đầu là các tuyến lịch
sử có hợp đồng riêng. Nhãn “lịch sử” không có nghĩa file hết phụ thuộc hoặc được
phép xóa. Các runbook chứa PREP/PENDING phản ánh thời điểm viết; tìm receipt và
source thực thi tương ứng trước khi kết luận một lần chạy đã hoàn tất.

[AGENTS](AGENTS.md) quy định giữ dữ liệu gốc, raw-before-parse và provenance.
Dataset, checkpoints và raw outputs lớn được giữ ngoài Git; sản phẩm kiểm tra
local mới đặt trong `data/processed/`. Không chạy notebook từ HEAD tài liệu này:
bootstrap kiểm tra đúng release/commit, inventory và hash. Hướng dẫn này không
thay thế source thực thi đã khóa hoặc cấp quyền GPU, TEST hay đọc annotation.
