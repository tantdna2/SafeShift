# MiniCPM-V-4 Full-TRAIN — Hoàn thành thực thi và phân tích 205 ca INVALID

Hồ sơ ngày 26/11/2026 (Asia/Bangkok), dựa trên main
`5f12a752acd636878fb6044c00185e7af5e2ae63`. Owner xác nhận đã hoàn thành
thực thi Full-TRAIN. Kết quả của Operator đã được kiểm lại trên máy và có
trạng thái `OFFLINE_VERIFIED_PROVISIONAL`. Final Admission còn chờ đối soát.
[Bản ghi Owner](DECISIONS.md#dec-20261126-owner-minicpm3763-execution-completed),
[PR #212](https://github.com/tantdna2/SafeShift/pull/212).

## Đối chiếu Full-TRAIN

| Chỉ tiêu | Báo cáo Operator | Đối chiếu cục bộ |
| --- | ---: | ---: |
| ID kết quả duy nhất trên cohort | 3.763/3.763 | 3.763/3.763, ordinal 0–3762, ID và SHA ảnh trong record khớp projection đã khóa |
| `SUCCESS` | 3.558 | 3.558 (94,55% trên 3.763) |
| `INVALID` | 205 | 205 (5,45% trên 3.763) |
| `TECHNICAL_ERROR` / `NOT_ATTEMPTED` | 0 / 0 | 0 / 0 |
| Level01 / Level02 / Level03 / Level04 | 145 / 206 / 286 / 2.921 | 145 / 206 / 286 / 2.921 trên các dự đoán `SUCCESS` |
| Serial 23 | 669 ảnh cuối | Ordinal 3094–3762, 611 `SUCCESS` và 58 `INVALID` |
| Lượt có kết quả | 13 | 9–18, 20, 21 và 23 |
| Tổng thời gian các lượt có kết quả | 56.648,2 giây | 56.648,1846 giây từ tổng `overhead_seconds` (43.806,3454) và `call_seconds` (12.841,8392) |

Fast `status` từ checkout Operator tại đúng main trên đã trả
`PENDING_FINAL_RECONCILIATION`, `next_ordinal=3763`, `active=null` và
`stopped=false`. Đối chiếu dùng Fast release PR #212 và hai runtime release
chuyển tiếp PR #211/#212 với hai checkout lịch sử đã khóa. Fast kiểm release
từ bản export, chuỗi journal và hai mirror, chữ ký seal, package/custody và
các closure theo cơ chế đã phát hành. Phép cộng thời gian dùng telemetry trong
13 completion event. Hai closure trước native của Serial 19 và 22 vẫn nằm
trong lịch sử. Reservation và physical GPU-seconds thuộc sổ theo dõi riêng.
[Cách chạy lại Fast `status`](../MINICPM_SERIAL22_RECOVERY.md#hồ-sơ-nguồn-và-thao-tác-operator),
[mã Fast](../../scripts/minicpm_offline_fast.py).

| Bằng chứng | Vị trí tương đối trong checkout Operator và SHA256 |
| --- | --- |
| Journal primary và mirror | `data/processed/minicpm-offline-s9/` và `data/processed/minicpm-offline-s9-mirror/`. 30 event khớp byte giữa hai bản. Cuối chuỗi là `event-000030.json`, SHA256 `62e6ba7650a5fba23286cb00cb88b96104de8c0d7c38945c77e0f1fe7ce820f3`. |
| Cohort TRAIN đã khóa | `registration.json` → `initial.cohort`, digest `524980d374daf6be3bedc743b6dc5ddc423dfe11c833609253cc5b2ce38586dc`. |
| Serial 23 | `custody/23/mcpm4-restart-v1-23.zip`, SHA256 `04e664ec69d9bfabad07fa8752a9fd3f52c3b4a269f375d8a3c0ebdae94824c2`. |
| Tập `INVALID` được kiểm | `digest()` của danh sách 205 `raw_sha256` theo ordinal là `5a27207cd44dad4cbc36473cbf1f8e1e1f3ec12ea110bf967ca8e6796db46a9a`. |
| Prompt C1 | `configs/pilot/classification_c1.txt`, SHA256 `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`. |

Ba `implementation_sha256` trong lịch sử khớp ba nguồn thực thi qua các lần
chuyển tiếp. Các trường danh tính còn lại trong 13 completion giữ cùng giá trị,
gồm model/revision, checkpoint, configuration, generation, prompt, parser,
preprocessing, runtime và chính sách HNLO. Hồ sơ hiện tại dùng kết quả kiểm
Fast cục bộ. Đối soát provider thuộc luồng Final Admission.
[Quy trình đối soát](../MINICPM_OFFLINE_CONTINUATION.md).

## Nguyên nhân của 205 ca INVALID

| Nhóm theo đầu ra lưu trước parse | Số ca | Kết luận |
| --- | ---: | --- |
| JSON một khóa `safety_level`, giá trị là đúng cụm mô tả Normal trong prompt | 205 | Mô hình sinh cách diễn đạt ngoài tập bốn mã canonical. C1 từ chối đúng hợp đồng. |
| JSON hỏng, thiếu khóa, khóa lặp, ký tự thừa, fence hoặc đầu ra rỗng | 0 | Không có ca chỉ cần làm sạch cú pháp hay bỏ lớp bao ngoài. |
| C1 chấp nhận chuỗi gốc hoặc dấu hiệu lỗi decode/cắt theo giới hạn sinh | 0 | Replay C1 từ chối cả 205. Cả 205 có tokenizer replay `PASS` và `generated_decode=MATCH`, cùng một chuỗi 11 token kết thúc bằng EOS, dưới giới hạn 64 token. |

Trong prompt công khai, mục **Canonical output vocabulary** định nghĩa
`no abnormalities observed → Level04`. Cả 205 giá trị trùng chính xác cụm
mô tả này. Đầu ra có đúng cú pháp JSON, nhưng mô hình dùng cụm mô tả thay cho
mã được yêu cầu ở câu cuối prompt. Tokenizer và parser cho kết quả nhất quán
với chuỗi đã lưu. Dữ liệu hiện có xác định kiểu vi phạm biểu diễn. Nguyên nhân
khiến mô hình chọn cụm mô tả trên từng ảnh và chất lượng dự đoán trên những
ảnh đó chưa được xác định. [Prompt công khai](../../configs/pilot/classification_c1.txt),
[parser C1](../../safeshift/pilot/contract.py).

Số `INVALID` theo Serial là 12→1, 14→1, 15→15, 16→10, 17→35, 18→56,
20→13, 21→16, 23→58. Các Serial 9, 10, 11 và 13 có 0 ca. Cùng loại đầu
ra xuất hiện trước và sau các chuyển tiếp nguồn. Các Serial xử lý các khoảng
ordinal khác nhau, nên các tỷ lệ theo lượt không xác định hiệu ứng runtime.

**Cách tái kiểm cục bộ.** Sau `status` của Fast, đối chiếu `event-*.json`
giữa hai mirror và dùng `initial.cohort.samples` của `registration.json` để
nối `sample_id` với ordinal và SHA ảnh. Từ mỗi event
`OFFLINE_VERIFIED_PROVISIONAL`, lấy riêng `payload.verification.report.history[-1]`
của attempt được event đó chấp nhận. Ghép các record đã có output theo đúng
ordinal và kiểm số ID duy nhất, trạng thái, phân bố mã. Lấy ZIP từ
`payload.attempt`. Với từng record `INVALID`, đọc đúng member
`calls/{ordinal:06d}/run/samples/000000/raw.json` bằng `zipfile`. Đối chiếu
SHA256 của member với `raw_sha256`, so `identity.sample_id` và
`identity.input_sha256` với record. Dùng Python 3.11 và kiểm `response` qua
`safeshift.pilot.contract.parse_label` nguyên bản. Kiểm JSON chỉ có một cặp
khóa–giá trị, so giá trị với cụm Normal trong prompt, rồi đếm chuỗi response,
`generated_ids`, EOS và receipt của tokenizer. Phân nhóm dùng 205 member từ
chín ZIP đã niêm phong. Bảng trên chỉ chứa số tổng hợp. Hồ sơ tái kiểm dùng
byte có sẵn trên máy, không cần tải lại từ Kaggle, mở ảnh hay dùng nhãn gốc.

## Phương án đề xuất và khả năng so sánh

**Ưu tiên một phép ánh xạ chính xác trên CPU trong bản dẫn xuất có phiên bản.**
Sau khi được duyệt, xét 205 record `INVALID` của parent đã ghim hash. Chỉ áp
dụng khi toàn bộ response là đúng một object JSON với đúng một khóa
`safety_level` và giá trị chuỗi khớp chính xác cụm Normal trong prompt. Chuỗi
bên trong giá trị phải khớp từng ký tự. Mọi dạng khác giữ trạng thái gốc.
Parser C1 đang dùng tiếp tục cung cấp kết quả strict cho bản gốc. Bản dẫn xuất
lưu riêng phiên bản quy tắc, digest của parent/cohort, liên kết đến raw SHA,
attempt/source và trạng thái trước/sau. Dữ liệu gốc là nguồn đối soát của mọi
record. Chạy lặp trên cùng đầu vào phải cho cùng bản dẫn xuất; đích đã tồn tại
chỉ chấp nhận khi khớp byte. Tiêu chí này cần được chốt trước khi tạo bản dẫn
xuất. [Quyết định Full-TRAIN ngày 02/11](DECISIONS.md#dec-20261102-owner-thesis-fulltrain-repair).

| Phương án | Chi phí và giới hạn |
| --- | --- |
| Giữ strict C1 cho phân tích gốc | 0 call mới. Giữ 205 `INVALID` trên đúng 3.763 ID. Đây là kết quả của cấu hình thực thi đã đăng ký. |
| Ánh xạ đúng cụm Normal trong bản dẫn xuất | 0 call mới, tái sử dụng raw đã lưu. Trên snapshot hiện tại, mức bao phủ nhãn có thể tăng từ 94,55% lên 100%, với 205 chuyển đổi từ `INVALID` sang dự đoán Level04. Phân bố dự kiến là 145 / 206 / 286 / 3.126. Đây là hệ quả tính từ quy tắc đề xuất, chưa phải kết quả của một bản dẫn xuất đã tạo hay đã duyệt. |
| Gọi lại 205 ảnh với cấu hình cũ | Tối đa 205 call nếu được cấp riêng, cộng chi phí stage/load/export. Telemetry của 205 call gốc cộng khoảng 715,1 giây trước overhead theo lượt. Generation hiện dùng greedy, và cả 205 chuỗi sinh giống nhau. Chưa có bằng chứng gọi lại cùng cấu hình sẽ giải quyết lỗi. |
| Đổi prompt hoặc dùng giải mã ràng buộc | Cần thẩm định method/source mới vì có thể làm thay đổi cả nhãn ở các ảnh đã `SUCCESS`. Chỉ chạy 205 ảnh sẽ tạo chế độ xử lý theo trạng thái ban đầu, làm thay đổi đối tượng so sánh. Chi phí và quyền vượt nhu cầu của hồ sơ này. |

So sánh trước/sau phải ghép theo cùng **3.763 ID**, giữ hai cột kết quả và
báo riêng 205 chuyển đổi. Đây là phân tích độ nhạy trên TRAIN đã phơi nhiễm,
với quy tắc chọn sau khi quan sát lỗi. Khi đủ quyền phân tích, báo coverage
trên cùng mẫu số và dùng quy ước `INVALID` của giao thức cho bản gốc. Mọi chuyển
đổi đề xuất đều tăng số dự đoán Normal. Với những ảnh thực sự thuộc Hazard,
chuyển đổi đó sẽ biến một `INVALID` thành false-safe. Chưa thể kết luận về
accuracy, false-safe hay bất đồng từ số ca đổi nhãn. Các chỉ số bất đồng còn
phải ghi rõ thay đổi eligibility nếu số cặp có nhãn tăng. MiniCPM vẫn là
label-only, HNLO N/A. Bản dẫn xuất có thể dùng cho phân tích độ nhạy sau khi
được duyệt riêng. Quyền dùng trong bảng so sánh chính thức cần quyết định
riêng về comparability và phiên bản. [Quy ước coverage, INVALID và phân tích
bất đồng](SEMINAR_PROTOCOL.md).

## Kiểm thử CPU và quyền còn cần

- Bộ test CPU hiện hành đã có ca canonical, sai kiểu, khóa thừa/lặp, fence và
  trailing text. Bổ sung regression tổng hợp cho cụm Normal trong prompt,
  biến thể hoa thường, khoảng trắng trong giá trị và dạng mã ngoài chuẩn.
  `Level04` vẫn parse thành công. Trên Windows/Python 3.11.9, bộ `test_pilot.py`
  đạt 49/49 và `test_fulltrain.py` đạt 24/24. Bộ Full-TRAIN kiểm việc giữ
  `INVALID` khi resume và yêu cầu ủy quyền đúng phạm vi đối với repair.
  [Parser tests](../../tests/test_pilot.py),
  [Full-TRAIN tests](../../tests/test_fulltrain.py).
- Nếu phép ánh xạ được phê duyệt, kiểm thử CPU cho bản dẫn xuất phải bao phủ
  đúng cụm mô tả, bốn mã canonical không đổi, mọi near-match và JSON ngoài quy
  tắc giữ `INVALID`, parent/ID/raw SHA thiếu hoặc lệch thì dừng, kết quả lặp
  lại giống byte. Fixture cần kiểm cả việc giữ 3.558 record gốc và thứ tự 3.763
  ID, ghi vào đích riêng, cùng ca giả lập Hazard→Normal để xác nhận cách báo
  false-safe theo giao thức khi phân tích đã được cấp quyền.
- **Quyền còn cần cho bản dẫn xuất.** Quyết định O2 cho phép quy tắc chính
  xác, phiên bản, parent hash và phạm vi dùng. Xác nhận quyền O4 phù hợp cho
  bất kỳ lần đọc/xuất artifact bổ sung hoặc đối chiếu nhãn để đánh giá. O3
  roster và các gate O5/O6 áp dụng theo phạm vi công việc sau này. Mọi lần
  gọi mô hình mới cần ngân sách, điều kiện dừng và scope/release riêng. Hồ sơ
  này đề xuất lộ trình CPU, chưa tạo dự đoán sửa.
- **Quyền và chứng từ còn cần cho bản gốc.** Owner thực hiện đối soát provider
  theo quy trình gốc, dùng đủ ba release. Final Admission cần phê duyệt Owner
  gắn SHA256 của manifest và report, certificate và kiểm `official-report`.
  Việc review Draft PR tài liệu/kiểm thử độc lập với các quyết định này.
  [Luồng final của MiniCPM](../MINICPM_OFFLINE_CONTINUATION.md).
