# SafeShift

**SafeShift: Evaluating the Validity and Cross-Domain Reliability of Internal
Hazard Scores in Vision-Language Models**

SafeShift nghiên cứu liệu tín hiệu nội tại của mô hình thị giác–ngôn ngữ (VLM)
có giúp phân biệt ảnh nguy cơ với ảnh bình thường trong bối cảnh an toàn công
nghiệp hay không, và tín hiệu đó còn đáng tin cậy đến mức nào khi miền dữ liệu
thay đổi. Trọng tâm của nghiên cứu là đánh giá tính hợp lệ, yếu tố gây nhiễu và
giới hạn chuyển miền; không đề xuất một thuật toán chấm điểm mới.

## Vấn đề khoa học và mục tiêu

Đầu ra nhãn do VLM sinh ra có thể không phản ánh đầy đủ thông tin có trong phân
phối nội tại của mô hình. SafeShift đánh giá một điểm liên tục được tính trực tiếp
từ logits của bốn nhãn an toàn, đối chiếu nó với các baseline dựa trên nhãn sinh
ra và kiểm tra xem kết quả có bị chi phối bởi con người trong ảnh, miền công
nghiệp hoặc nguồn dữ liệu hay không.

Ba câu hỏi nghiên cứu được lựa chọn là:

1. **RQ1 — Giá trị phân biệt:** Điểm nội tại có phân biệt nguy cơ tốt hơn các đối
   chứng công bằng dựa trên đầu ra sinh ra, khi so sánh trên cùng dữ liệu và cùng
   tập ID hợp lệ hay không?
2. **RQ2 — Dấu hiệu gây nhiễu:** Khả năng phân biệt còn duy trì đến đâu sau khi
   kiểm soát sự hiện diện của con người, miền công nghiệp và nguồn dữ liệu?
3. **RQ3 — Độ tin cậy khi chuyển miền:** Mức bỏ sót nguy cơ và báo động giả thay
   đổi thế nào giữa các miền, và đâu là giới hạn chuyển giao của điểm số?

RQ3 là đánh giá thực nghiệm, không phải bảo đảm thống kê về an toàn.

## Dữ liệu và mô hình

Nghiên cứu sử dụng **InspecSafe-V1**, gồm năm miền công nghiệp và bốn mức nhãn:
Level01–Level03 được ánh xạ thành *Anomaly*, Level04 thành *Normal* theo định
nghĩa hiện có của nghiên cứu. Baseline đã kiểm toán dùng toàn bộ **3.763 ảnh
TRAIN**: 749 Anomaly và 3.014 Normal.

Bộ Seminar cuối cùng bắt buộc đánh giá đủ bốn mô hình:

- **Qwen2.5-VL-3B-Instruct** — baseline hiện có;
- **Qwen3-VL-8B-Instruct**;
- **InternVL3-2B-hf**;
- **Moondream2**.

Chỉ Qwen2.5 hiện có kết quả điểm nội tại tương thích đã được kiểm toán. Ba mô
hình còn lại chưa có kết quả tương ứng được xác minh; không được ngầm tái sử dụng
token mapping hoặc cơ chế logits của Qwen cho các mô hình này.

## Hazard–Normal Label Log-Odds Score (HNLO)

**Hazard–Normal Label Log-Odds Score (HNLO)** — tiếng Việt: **Điểm log tỷ số
giữa các nhãn nguy cơ và nhãn bình thường** — là tên trình bày khoa học của phép
tính điểm đã tồn tại trong repository:

$$
\mathrm{HNLO}
= \operatorname{logsumexp}(z_{\mathrm{Level01}}, z_{\mathrm{Level02}},
z_{\mathrm{Level03}}) - z_{\mathrm{Level04}}.
$$

Điểm cao hơn biểu thị xu hướng nguy cơ cao hơn. HNLO là điểm xếp hạng liên tục
chưa hiệu chỉnh; nó không phải xác suất, nhãn dự đoán hoặc accuracy. Baseline
hiện chưa chọn ngưỡng HNLO, vì vậy chỉ báo cáo AUROC và coverage cho điểm này.

HNLO không thay đổi công thức, chiều điểm, nhãn, tokenizer, runtime, metric hay
kết quả trước đây. Các định danh và hồ sơ kỹ thuật lịch sử được giữ nguyên để
đảm bảo khả năng truy vết và tái lập kết quả.

## Baseline Qwen2.5 đã kiểm toán

Các kết quả dưới đây thuộc **InspecSafe-V1 TRAIN đã được thăm dò**, với
3.763/3.763 mẫu hợp lệ. Đây là bằng chứng mô tả trên TRAIN, không phải bằng chứng
về khả năng khái quát hóa.

| Chỉ số | Kết quả | Diễn giải |
| --- | ---: | --- |
| AUROC HNLO gộp | **0,8266558463706973** | Phân biệt theo thứ hạng trên toàn bộ TRAIN |
| AUROC HNLO trung bình bốn miền chính | **xấp xỉ 0,846435** | Trung bình không trọng số của coal_conveyor, oil_chemical, power và tunnel; không phải AUROC gộp |
| AUROC nhãn nhị phân sinh ra | **0,500000** | Đối chứng từ nhãn sinh ra trên cùng ID |
| Accuracy nhãn sinh ra, bốn mức | **3,4547%** | 130/3.763; không phải accuracy HNLO |
| Accuracy nhãn sinh ra, nhị phân | **19,9043%** | 749/3.763; không phải accuracy HNLO |
| Coverage HNLO | **100%** | 3.763/3.763 mẫu được chấm điểm |

Qwen2.5 sinh nhãn *Anomaly* cho cả 3.763 ảnh, nên AUROC nhãn nhị phân bằng 0,5
và accuracy nhị phân phản ánh tỷ lệ Anomaly trong tập này. Kết quả HNLO cho thấy
tín hiệu xếp hạng đáng để tiếp tục kiểm định, nhưng chưa chứng minh calibration,
ngưỡng quyết định an toàn, hiệu năng bốn mô hình hoặc khả năng chuyển sang dữ
liệu độc lập. Baseline còn chịu giới hạn bởi phụ thuộc chuỗi/nguồn, lịch sử mẫu
trùng xuyên split, nhiễu miền–nền tảng, Level03 thưa và một receipt tải ngoài bị
thiếu; kiểm toán nội bộ gói dữ liệu vẫn đạt yêu cầu đã ghi nhận.

## Đóng góp dự kiến

- Một giao thức so sánh công bằng giữa HNLO và các baseline từ đầu ra sinh ra,
  với cùng cohort, cùng tập ID hợp lệ và báo cáo đầy đủ coverage/INVALID.
- Phân tích tính hợp lệ của tín hiệu sau khi kiểm soát human presence, domain và
  provenance, đồng thời giữ rõ các giới hạn phụ thuộc dữ liệu.
- Đánh giá độ tin cậy khi chuyển miền qua tỷ lệ bỏ sót nguy cơ, báo động giả và
  mẫu số theo miền sau khi quy tắc ngưỡng được phê duyệt trước.
- Hồ sơ raw-before-parse và bằng chứng tái lập cho từng model/run/config được
  phép thực hiện.

## Hướng phát triển thành khóa luận

Hướng khóa luận có thể mở rộng Seminar bằng đánh giá bốn mô hình trên cohort đã
được phê duyệt, thiết kế holdout/group-aware phù hợp, lựa chọn ngưỡng theo hướng
prospective, ước lượng bất định có xét phụ thuộc và nghiên cứu cơ chế kiểm soát
rủi ro hoặc từ chối dự đoán. Đây là hướng tương lai; chưa có nội dung nào trong
tài liệu này cấp quyền dùng GPU, đọc TEST/annotation, chọn ngưỡng hoặc thay đổi
protocol.

Hướng HNLO hiện vẫn là đề xuất chờ Research Lead phê duyệt chính thức. Cho đến
khi có phê duyệt, phạm vi Seminar đang có hiệu lực và trạng thái protocol freeze
không thay đổi. Xem [hồ sơ quyết định](DECISIONS.md) và [roadmap](ROADMAP.md) để
theo dõi ranh giới quản trị nghiên cứu.

## Tài liệu và bằng chứng

- [Tóm tắt baseline dành cho giảng viên](notes/seminar_baseline_review_2026.md)
- [Báo cáo tái tính và kiểm toán CPU Qwen2.5](notes/pa3_r2_cpu_completion_20261015.md)
- [Tổng hợp kết quả máy đọc được](notes/pa3_r2_cpu_completion_20261015.summary.json)
- [Yêu cầu phạm vi bốn mô hình](notes/pa3_four_model_seminar_scope.md)
- [Báo cáo audit dữ liệu Week 1](notes/w1_dataset_audit.md)
- [Quy tắc làm việc và tính toàn vẹn nghiên cứu](AGENTS.md)

Dữ liệu gốc, model weights và raw model outputs không được đưa vào Git. Mọi
đường dẫn trong code, cấu hình, manifest và tài liệu tái lập phải tương đối so
với repository root.
