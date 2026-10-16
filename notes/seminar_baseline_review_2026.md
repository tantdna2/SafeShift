# Tóm tắt học thuật baseline SafeShift — Baseline Review 2026

Tài liệu này trình bày ngắn gọn baseline đã được kiểm toán để giới thiệu với
giảng viên. Các kết quả là mô tả trên InspecSafe-V1 TRAIN đã được thăm dò, không
phải chứng cứ về khả năng khái quát hóa hoặc một protocol đã đóng băng.

## 1. Đề tài và vấn đề nghiên cứu

**Tên đề tài:** *SafeShift: Evaluating the Validity and Cross-Domain Reliability
of Internal Hazard Scores in Vision-Language Models*.

SafeShift nghiên cứu liệu tín hiệu nội tại của VLM có phân biệt ảnh nguy cơ với
ảnh bình thường tốt hơn các đối chứng lấy từ đầu ra nhãn sinh ra hay không. Nghiên
cứu đồng thời kiểm tra tác động của dấu hiệu gây nhiễu và mức độ tin cậy của tín
hiệu khi miền công nghiệp thay đổi.

## 2. Câu hỏi và mục tiêu nghiên cứu

1. **RQ1 — Giá trị phân biệt:** Đánh giá giá trị phân biệt của điểm nội tại với
   các đối chứng công bằng trên cùng dữ liệu và cùng tập ID hợp lệ.
2. **RQ2 — Dấu hiệu gây nhiễu:** Kiểm tra ảnh hưởng của sự hiện diện của con
   người, miền công nghiệp và nguồn dữ liệu.
3. **RQ3 — Độ tin cậy khi chuyển miền:** Đánh giá sự đánh đổi giữa bỏ sót nguy
   cơ và báo động giả theo miền, cùng giới hạn chuyển giao của điểm số.

Mục tiêu là xây dựng một đánh giá có thể kiểm toán cho tính hợp lệ và độ tin cậy
của điểm nội tại. RQ3 là đánh giá thực nghiệm, không phải bảo đảm an toàn.

## 3. Dữ liệu, mô hình và phương pháp

Baseline sử dụng toàn bộ **3.763 ảnh InspecSafe-V1 TRAIN**, gồm 749 Anomaly
(Level01–Level03) và 3.014 Normal (Level04). Tập dữ liệu bao phủ năm miền công
nghiệp nhưng có phụ thuộc chuỗi/nguồn, lịch sử mẫu trùng xuyên split, nhiễu
miền–nền tảng và hỗ trợ Level03 thưa.

Bốn mô hình bắt buộc của Seminar là **Qwen2.5-VL-3B-Instruct**,
**Qwen3-VL-8B-Instruct**, **InternVL3-2B-hf** và **Moondream2**. Hiện chỉ
Qwen2.5 có kết quả điểm nội tại tương thích đã được kiểm toán; ba mô hình còn lại
chưa có kết quả tương ứng được xác minh.

Điểm đánh giá được trình bày với tên khoa học:

**Hazard–Normal Label Log-Odds Score (HNLO)** — **Điểm log tỷ số giữa các nhãn
nguy cơ và nhãn bình thường**.

$$
\mathrm{HNLO} = \ln\left(e^{z_{01}} + e^{z_{02}} + e^{z_{03}}\right) - z_{04}
$$

Trong đó, $z_{01}$, $z_{02}$, $z_{03}$ và $z_{04}$ là các raw logits tương ứng
với các nhãn Level01–Level04.

Điểm cao hơn biểu thị xu hướng nguy cơ cao hơn. HNLO là tên mô tả của phép tính
đã có, không phải thuật toán mới. Tên này không làm thay đổi công thức, nhãn,
tokenizer, runtime, metric hoặc kết quả. HNLO chưa được hiệu chỉnh và chưa có
ngưỡng quyết định trong baseline này, nên không có “accuracy HNLO”.

## 4. Kết quả baseline Qwen2.5

Kiểm toán CPU đã tái tính thành công 3.763/3.763 mẫu từ raw output; coverage đạt
100%. Kết quả chính:

| Chỉ số | Giá trị |
| --- | ---: |
| AUROC HNLO gộp | **0,8266558463706973** |
| AUROC HNLO trung bình bốn miền chính | **xấp xỉ 0,846435** |
| AUROC nhãn nhị phân sinh ra | **0,500000** |
| Accuracy nhãn sinh ra, bốn mức | **3,4547%** |
| Accuracy nhãn sinh ra, nhị phân | **19,9043%** |
| Coverage HNLO | **100%** |

Giá trị trung bình bốn miền là trung bình không trọng số của coal_conveyor,
oil_chemical, power và tunnel; nó không thay thế AUROC gộp. Metallurgy được giữ
trong AUROC gộp nhưng không nằm trong trung bình này do hỗ trợ Anomaly rất thưa.

Nhãn Qwen2.5 sinh ra suy biến thành *Anomaly* cho toàn bộ 3.763 ảnh. Vì vậy,
AUROC nhãn nhị phân bằng 0,5 và accuracy nhị phân 19,9043% không phải accuracy
của HNLO. AUROC HNLO cho thấy tín hiệu xếp hạng có giá trị nghiên cứu trên TRAIN,
nhưng chưa chứng minh calibration, quyết định an toàn hoặc khả năng khái quát hóa.

## 5. Đóng góp dự kiến và giới hạn

Đóng góp dự kiến gồm: (i) giao thức so sánh công bằng giữa HNLO và baseline đầu
ra sinh ra; (ii) phân tích gây nhiễu theo human presence, domain và provenance;
và (iii) đánh giá mức bỏ sót, báo động giả và giới hạn chuyển miền với coverage,
INVALID và mẫu số được báo cáo minh bạch.

Các giới hạn cần giữ rõ gồm TRAIN đã thăm dò, phụ thuộc giữa mẫu, rủi ro duplicate
xuyên split, nhiễu miền–nền tảng, Level03 thưa, thiếu một receipt tải ngoài và
chưa có kết quả HNLO tương thích cho ba mô hình còn lại. Kiểm toán nội bộ của
gói kết quả Qwen2.5 vẫn đạt yêu cầu đã ghi nhận.

## 6. Hướng khóa luận và bằng chứng kỹ thuật

Hướng phát triển khóa luận là đánh giá đủ bốn mô hình trên cohort được phê duyệt,
thiết kế holdout/group-aware, lựa chọn ngưỡng theo hướng prospective, ước lượng
bất định có xét phụ thuộc và nghiên cứu kiểm soát rủi ro hoặc từ chối dự đoán.
Mọi truy cập annotation/TEST, lựa chọn ngưỡng, metric mới và GPU inference vẫn
cần phê duyệt riêng; hướng HNLO hiện chưa thay thế phạm vi Seminar đang có hiệu lực.

Bằng chứng để kiểm tra hoặc điền form:

- [Báo cáo tái tính và kiểm toán CPU](pa3_r2_cpu_completion_20261015.md)
- [Tổng hợp kết quả máy đọc được](pa3_r2_cpu_completion_20261015.summary.json)
- [Yêu cầu đánh giá đủ bốn mô hình](pa3_four_model_seminar_scope.md)
- [Audit tính khả thi và giới hạn dữ liệu](research_feasibility_audit.md)
- [Hồ sơ quyết định và ranh giới thẩm quyền](../DECISIONS.md)

Raw outputs, tokenizer snapshot, model weights và artifact kiểm toán dung lượng
lớn được giữ ngoài Git theo chính sách dữ liệu; báo cáo kỹ thuật lưu checksum và
lệnh tái lập cần thiết.
