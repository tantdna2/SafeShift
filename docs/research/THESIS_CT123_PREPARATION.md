# SafeShift — Chuẩn bị CT1–CT3

[Quyết định Owner](DECISIONS.md#dec-20261127-owner-ct123-implementation) chọn
ba hướng sau [benchmark và truy nguyên Full-TRAIN](FULL_TRAIN_BENCHMARK_V1.md).
CT1 là trục chất lượng, CT2 là hướng thuật toán riêng, CT3 hỗ trợ cả hai.
Đợt này chuẩn bị giao thức và screening CPU từ nhãn đã lưu. Việc đọc ảnh,
reviewer study, GPU, inference, Kaggle và TEST cần phạm vi riêng. Giữ nguyên
GT, split, C1 và M2. Các giá trị minh họa dưới đây phục vụ dự toán.

## CT1 — Audit ảnh mù và đối chứng precedence

Qwen3 hạ 303/490 Level01 xuống Level02 trên TRAIN. Ví dụ PPE chung và bảng
ngành có các mức chồng lấn. Hồ sơ 24 ca đã xác minh xuất xứ của đầu ra lưu.
Để xác định ảnh có dấu hiệu đủ rõ và đúng xung đột rubric, cần audit visual
trước khi đề nghị inference. Bài công bố InspecSafe chọn nguy cơ nặng nhất
khi ảnh có nhiều nguy cơ. Phép thử precedence xét cùng một dấu hiệu được
gán mức khác nhau giữa bảng và ví dụ. [InspecSafe-V1](https://arxiv.org/html/2601.21173v2)
· [C1 hiện hành](../../configs/pilot/classification_c1.txt)

### Chuẩn bị và khóa phiếu

1. Sau khi có quyền ảnh, một điều phối viên dữ liệu tạo mẫu TRAIN có ID
   audit ngẫu nhiên. Lấy các ca Qwen3 01→02, đối chứng đúng Level01 ghép miền
   và nguồn khi biết, Normal dễ nhầm có dấu hiệu tương tự, cùng ca không
   thấy xung đột. Dùng mỗi nhóm ảnh trùng tối đa một lần trong audit chọn ca,
   ghi seed, quy tắc ghép và support trước khi mở ảnh. Các ca chọn chủ đích
   hỗ trợ truy nguyên. Muốn ước lượng tỷ lệ nguyên nhân trong 303 ca, cần chọn
   trong khung lấy mẫu đã định nghĩa và lưu xác suất hoặc trọng số.
2. Tách danh sách ghép ID và bảng chọn ca khỏi phiếu. Hai chuyên gia đánh
   giá độc lập, cùng rubric, mù GT, dự đoán, nhóm lấy mẫu, giả thuyết arm và
   kết luận của nhau. Ẩn tên file/metadata tiết lộ nhãn hoặc nhóm. Mỗi phiếu
   ghi `audit_case_id`, `reviewer_code`, phiên bản rubric, thời gian, dấu
   hiệu nhìn thấy, độ rõ, ngành suy ra từ ảnh hoặc chưa rõ, số nguy cơ,
   điều khoản chung/ngành áp dụng, xung đột trên cùng dấu hiệu, mức đề xuất,
   lý do và trạng thái thiếu căn cứ. Vùng chứng cứ chỉ lưu nếu người xem
   đánh dấu và quyền cho phép.
3. Khóa từng phiếu và hash trước khi mở GT/model để phân xử. Ghi đồng thuận
   và bất đồng, confidence của chuyên gia nếu được định nghĩa trong rubric,
   kết luận thứ ba và lý do. Ghi riêng các nhóm xung đột precedence có thể
   kiểm, không rõ ngành, đa nguy cơ, dấu hiệu khó thấy, discrepancy GT và
   không đủ căn cứ. Giữ GT gốc. Báo số ca và mẫu số từng nhóm, cả nhóm không
   xác định. Lưu phiếu và khóa ở vùng cục bộ đúng quyền.
4. Trước khi xin chạy pilot, trình bảng support và agreement. Nếu thiếu
   ca có dấu hiệu rõ và xung đột áp dụng được, hoặc người chấm bất đồng đến
   mức chưa định nghĩa được cơ chế, sửa rubric audit hoặc dừng giả thuyết
   này. Đổi sang phép thử max-severity, ngành hoặc grammar cần thiết kế riêng.

Còn thiếu quyền xem ảnh cho chính các reviewer, hai người có chuyên môn và
quy trình phân xử, nơi lưu hồ sơ đúng quyền. Kịch bản 80–120 ảnh × 2 reviewer
× 3–5 phút tương ứng 8–20 người-giờ trước phân xử. Cỡ audit minh họa này phục
vụ tính khả thi và cần điều chỉnh qua khung lấy mẫu.

### Thiết kế A/B/C

| Nhánh | Prompt tham chiếu và thay đổi đề nghị |
| --- | --- |
| A | C1 đúng bytes đã khóa. |
| B | Chèn trước bảng ngành: `When a general example and the relevant industry table assign different levels to the same hazard, follow the relevant industry table.` |
| C | Chèn cùng vị trí: `Use the assessment criteria below to assign the requested safety level for the scene and return it in the specified output format.` |

Chốt câu chữ, vị trí và độ dài token theo tokenizer đã ghim trước khi chạy.
Đối chứng C nhắc lại yêu cầu đã có. Lưu hash prompt dẫn xuất, giữ riêng A
và mọi series lịch sử. Dùng cùng Qwen3 revision, ảnh, preprocessing, input
miền, decoder, generation, parser và runtime. Qwen3 Composite V1 dùng làm
mốc hồi cứu. Chỉ tái sử dụng prediction A nếu khớp ảnh, revision, prompt,
generation, parser và điều kiện chạy đã freeze. Lập cùng lô hoặc block theo
thiết bị/job và cân bằng thứ tự arm để kiểm drift.

**Primary duy nhất** là B−A recall Level01 trên toàn bộ GT Level01 trong
planned. `01→02`, B−C và C−A là đối chiếu đã định trước để xem chuyển dịch
lỗi, nội dung precedence và độ nhạy khi thêm câu. Phân tầng nhóm có và
không có xung đột theo phiếu đã khóa để diễn giải, với support và CI khi có
đủ cụm. Báo Level01 precision và 02→01 để kiểm nâng mức quá tay, cùng
01→04, FNR, FPR, valid-label coverage, confusion 4 lớp, Macro-F1 và BA.
FNR false-safe dùng Hazard bị gọi Normal trên toàn GT Hazard, báo riêng
Hazard chưa có dự đoán hợp lệ và cận coi chúng là miss. Giữ riêng
`SUCCESS`, `INVALID`, `TECHNICAL_ERROR`, `NOT_ATTEMPTED`. Undefined khi
mẫu số bằng 0. Một kết quả âm giới hạn lợi ích của edit đã thử.

Pilot minh họa 200–400 ảnh cùng ba arm tương ứng 600–1.200 calls. Ước tính
cỡ mẫu xác nhận bằng chênh lệch paired trên các ca Level01 đổi chiều và
phân bổ cụm, kiểm đủ mẫu Normal và Level02 cho guardrail. Mô phỏng power và
độ rộng CI theo khoảng giả định, dùng pilot để cập nhật trước freeze.
Chốt với Owner mức tăng recall có ích, trần thay đổi có hại và coverage sàn
theo chi phí review. Điều kiện kết luận là cận dưới CI của B−A đạt mức lợi
ích đã đăng ký, guardrail đủ support và các cận tổn hại đạt yêu cầu. Thiếu
precision thì kết luận chưa đủ bằng chứng. Chưa có giá trị khoa học số
nào được cấp từ tài liệu này.

## CT2 — Sàng lọc CPU có chi phí

Dùng Qwen3 Composite V1 làm focal, InternVL3.5 Grammar V2 hoặc MiniCPM
Normalization V1 làm peer. Tái sử dụng manifest và checksum của benchmark.
Chỉ chọn ca Qwen3 dự đoán Level04 để tìm false-safe. M tính cả N lượt focal
và mỗi lượt peer mô phỏng. K giới hạn số hồ sơ người xem. Công bố cả trần
và lượt thực dùng. Đối chứng random và focal-only có thể dùng ít M hơn.
Trong tập đủ điều kiện, focal chỉ có một nhãn, nên tie-break không mang
thêm tín hiệu so với random. Dùng cùng K và ngân sách trần M. Với mỗi seed,
chọn tập mua peer trước khi biết nhãn peer, giữ tập đó chung giữa các arm
dùng peer. Sau mua mới dùng nhãn peer, ưu tiên bất đồng hoặc mức có thứ tự.
Ghi ca chưa mua peer, số hồ sơ duyệt, phần bù khi cờ chưa lấp K và hạn
chế của dữ liệu đầy đủ nhãn. GT chỉ tham gia scorer sau khi khóa hàng đợi.

Đo capture và precision cho false-safe, severe miss, residual false-safe/
severe, workload và chênh so với random cùng seed. Dùng seed lặp để kiểm
độ nhạy chính sách ràng buộc theo budget. Sự thay đổi giữa seed đo ngẫu
nhiên của policy trên cùng cohort. Ước lượng triển khai theo nguồn cần
validation riêng. N đặt theo planned ID. Nếu thử nhãn thiếu hay lỗi trong
protocol mới, ghi mandatory, backlog và overload, giữ chúng trong planned
và quy định ưu tiên trước khi chấm. Gắn cờ tạo hồ sơ review. Việc người
xác nhận hoặc sửa được ghi ở CT3 theo quyền riêng.

Giữ HNLO làm đối chứng phụ trên nhóm Qwen3 cùng series có điểm hợp lệ và
cùng eligible. Kiểm token/prefix/bước quyết định và lineage. Báo score
thiếu, tuyệt đối không ghép V4/Recovery hoặc tạo score cho peer. Calibration
cần xác định xác suất cần ước lượng, quyền, nhóm fit/validation tách nguồn
và đủ sự kiện, với Brier/log-loss, reliability và kiểm shift.
[Hợp đồng Qwen3](QWEN3_FULL_TRAIN_COMPOSITE_V1.md)

### Lệnh screening và lưới ngân sách thăm dò

Đặt bốn projection đã niêm phong vào thư mục Git-ignored theo
[hợp đồng đầu vào benchmark](FULL_TRAIN_BENCHMARK_V1.md). CLI kiểm size và
SHA256 của từng member trước khi đọc, xác minh join, rồi chỉ ghi
`screening.json` và `receipt.json` tổng hợp vào thư mục mới dưới
`data/processed/`. Lưới chọn trước khi xem kết quả gồm M = 4.139, 4.891,
6.372 và K = 37, 188, 376. Điểm K = 1.133 dùng đối chiếu mốc cờ thô hiện
có, với hai trần M nhỏ được giữ trong báo cáo đầy đủ. Dùng 20 seed từ 0
đến 19. Các mức này phục vụ khảo sát trên TRAIN, chưa phải M/K nghiệm thu.

```powershell
$screenSeeds = foreach ($seed in 0..19) { '--seed'; $seed }
python -B -m scripts.screen_full_train_triage `
  --input-dir data/processed/thesis-ct2/input `
  --output-dir data/processed/thesis-ct2/screening-v1 `
  --model-call-cap 4139 --model-call-cap 4891 --model-call-cap 6372 `
  --review-cap 37 --review-cap 188 --review-cap 376 --review-cap 1133 @screenSeeds
```

Thay đường dẫn đích nếu chạy lại. Dùng receipt để đối chiếu commit,
hash đầu vào/đầu ra và cấu hình. Đầu ra từng ca, ảnh, raw và giấy tờ
riêng nằm ngoài Git. Kết quả mang trạng thái `EXPLORATORY_EXPOSED_TRAIN`
và giữ `PROVISIONAL_PRE_FINAL_ADMISSION` của nguồn.

## CT3 — Hồ sơ và luồng kiểm toán

Giao diện nhỏ ưu tiên task review cụ thể. Luồng CT1 mở ảnh đúng quyền,
ghi và khóa phiếu mù, sau đó mới mở GT/prediction đã cấp để phân xử. Luồng
CT2 mở hàng review đã khóa M/K, hiển thị nhãn focal và peer đã mua, lý do
chuyển, nhãn thiếu và provenance, rồi ghi quyết định người review. Viewer
giữ trạng thái peer chưa mua khác peer dự đoán Normal. Giao diện có cờ
chứng cứ thiếu và số ca quá tải.

Giao diện đọc nội bộ lấy case theo ID audit được cấp, kiểm quyền từng mục,
kiểm digest và trả model/revision, run/attempt, input/prompt/config/artifact
digest, trạng thái, nhãn gốc/dẫn xuất hay bất đồng đã tính. Raw và ảnh
chỉ trả qua phạm vi riêng. Phiếu thêm sự kiện với ID case, quyết định,
người/thời gian, policy/rubric, lý do và khóa evidence đã xem. Giữ lịch sử
sự kiện append-only. Hash/source sai thì dừng hiển thị mục lỗi và ghi sự
kiện. Trạng thái evidence gồm verified, model-generated, unavailable và
conflict theo từng mục. Không suy vùng hazard từ polygon vật thể hoặc
tạo rationale khi artifact label-only.

Nếu có quyền study, so phiếu tĩnh với viewer cùng thông tin, đổi thứ tự
theo reviewer, tránh lặp ca trên cùng người. Đo truy đúng nguồn, sai sót
chấp nhận nguy hiểm và thời gian tại cùng mức chính xác. Chọn cỡ mẫu theo
reviewer và cụm case. Phiếu mù, truy nguồn và hàng review là phạm vi chức
năng hiện tại. Hiệu quả với người dùng cần study riêng.

## Dữ liệu, freeze, E1–E5 và chi phí

- **Development** dùng 3.763 TRAIN đã quan sát. Hồ sơ lưu 3.719 SHA phân biệt
  (44 cặp exact) và bảy cặp exact xuyên split. Near-duplicate là ứng viên
  cho đến khi xác minh. Cần kiểm site/robot/camera/video/session qua
  custodian, phân nhóm liên thông với exact/near-duplicate đã xác thực,
  giữ quan hệ nguồn chưa biết là unknown. Dùng grouped CV nếu tuning,
  nested khi cần chọn hyperparameter, purge nguồn nối trong stress theo miền.
  [Hồ sơ nguồn](THESIS_DATA_PROTOCOL.md)
- **Validation** ưu tiên nguồn hoặc đợt thu tách phát triển và TEST, kiểm
  quyền, GT tương thích, không trùng cụm. Để quyết định cấu hình, K hay
  ngưỡng ở validation. Fit calibration và chọn ngưỡng cần vai trò tách hoặc
  cross-fit theo nhóm. Nguồn V và độc lập chưa xác nhận. Phân tích TRAIN
  tiếp tục mang trạng thái development.
- **TEST 1.250 đóng.** Trước quyền mở, đăng ký protocol full split/sensitivity,
  nhóm trùng, đơn vị bootstrap và phân tích nguồn còn phụ thuộc. Giữ full
  split làm phép đo planned, kèm sensitivity loại overlap đã đăng ký qua
  custodian. Ghim model, prompt, arms, masks, M/K, seeds/ties, metric,
  biên, số cụm/sự kiện, rule thiếu và điều kiện dừng. Một lượt đánh giá đã
  freeze. A/B cần 2.500 calls nếu không có artifact khớp, thêm C cần
  1.250 calls. CT2 cần N cộng các lượt peer đã đặt trong policy. Paired CI
  theo cụm nguồn đã xác minh, chung resample giữa mọi arm. Thiếu support
  hoặc quá ít cụm thì ghi số đếm, CI chưa đủ hoặc undefined.
- **E1** cùng protocol, ID, support và ngân sách. **E2** câu trung tính CT1
  hoặc bỏ từng tín hiệu đã mua CT2. **E3** miền, lớp hiếm, phụ thuộc nhóm,
  peer thiếu và overload. **E4** audit tối thiểu ba nhóm lỗi và ba ca trước–sau
  có quyền, ghi tốt lên, giữ nguyên, xấu đi. **E5** chốt hashes, môi trường,
  lệnh, seeds và receipts, giữ raw trước parse khi có quyền chạy.
- **Tài nguyên** tính riêng số GPU và thời gian từng job, model calls, load,
  staging, export, chi phí reviewer, dự phòng lỗi trong trần được duyệt.
  Nếu giả định 10–20 giây/call cho Qwen3, 600–1.200 calls ~1,7–6,7 GPU-giờ
  với một GPU trước overhead. A/B full TEST ~6,9–13,9 GPU-giờ cùng giả định.
  Đo latency và peak memory đúng model/cấu hình khi được phép. Quota,
  giới hạn job, phí và run authority cần xác minh trước phân bổ.

Trình Owner sau đợt này quyền audit ảnh và chuyên gia, nguồn validation,
biên/chỉ tiêu khoa học, số giờ GPU và reviewer, M/K triển khai, điều kiện
mở TEST, mức hỗ trợ CT3 và chuẩn nghiệm thu học vụ.
