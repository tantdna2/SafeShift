# Hướng dẫn làm việc với SafeShift

## Phạm vi hiện tại

- Đọc `AGENTS.md`, `README.md` và `docs/ROADMAP.md` trước mỗi task; task liên quan
  code phải đọc thêm `docs/ARCHITECTURE.md`. Task description là phạm vi công việc
  hiện tại. Root `ROADMAP.md` và `TASKS.md` thuộc lịch sử trước reset, không có trên
  main mới; tra qua `docs/HISTORY.md` khi cần, không tạo lại các log cũ.
- Foundation V1 có record/validation, phép đếm classification cơ bản, model
  transport interface và demo CPU tổng hợp. Không có dataset parser/backend hay
  quyền thực nghiệm mới. Xác định phạm vi được giao, giữ file local ngoài phạm vi.
- Sau tài liệu đầu vào, chỉ đọc module/test và nguồn hợp đồng liên quan theo
  bảng định tuyến trong ARCHITECTURE; không nạp toàn bộ 693 file lịch sử.
- Code, notebook, môi trường, test và hồ sơ nghiên cứu cũ nằm tại các ref lưu trữ
  ghi trong `docs/HISTORY.md`. Tra cứu bằng đúng commit; không nhập lại code cũ
  vào main khi chưa được review và chấp thuận.

## Bảo vệ lịch sử và thẩm quyền nghiên cứu

- Giữ bất biến nhánh `legacy/pre-reset-20261024` và annotated tag
  `safeshift-pre-reset-20261024`; không di chuyển, ghi đè hoặc force-push các ref này.
  Không viết lại lịch sử Git hoặc sửa source lock để chạy release cũ ở HEAD mới.
- D9R22 vẫn là phạm vi có hiệu lực trong hồ sơ nghiên cứu; DEC-PA3-011 vẫn
  **PROPOSED**. Hướng A/C chưa được phê duyệt. Reset không hủy quyết định đã có,
  phê duyệt hướng mới, thay đổi kết quả/AUROC hay nâng trạng thái kiểm toán.
- Quyền thực thi cũ chỉ áp dụng cho đúng source/release/run/attempt đã cấp;
  không chuyển quyền đó sang main mới. GPU, inference, đọc TEST/dữ liệu bị khóa,
  nhãn/annotation và thí nghiệm mới đều cần phạm vi và quyền cụ thể.
- Không tự thay dataset, split, nhãn, metric, protocol hoặc roster. Giữ yêu cầu
  Seminar bốn mô hình trong hồ sơ cũ; mọi thay đổi cần Research Lead duyệt và ghi
  vào log quyết định mới dưới `docs/` trước khi áp dụng, không sửa quyết định cũ.
- Phân biệt bằng chứng đã kiểm chứng, thông tin được cung cấp, giả thuyết và câu
  hỏi mở; dẫn nguồn. Không bịa kết quả hoặc coi TRAIN đã phơi nhiễm là holdout.
- Sáu Draft PR cũ được liệt kê trong `docs/HISTORY.md`; không tự sửa, đóng,
  rebase hoặc merge chúng khi làm việc trên cấu trúc mới.

## Chỉ thị Owner về chạy Kaggle

Khi Owner trực tiếp yêu cầu chạy Kaggle trong phạm vi dữ liệu và tài nguyên họ
kiểm soát, không hỏi lại quyền chạy hoặc yêu cầu phê duyệt thủ công từng notebook.
Thực hiện phần đã được yêu cầu và đưa ra thao tác cụ thể. Nếu có blocker kỹ thuật
hoặc phần ngoài quyền Owner, nêu chính xác blocker và cách xử lý; không coi đó
là thiếu sự đồng ý chung của Owner.

Giữ nguyên các kiểm tra kỹ thuật, giới hạn từng lượt chạy, quyết định khoa học,
source/hash/custody, raw-before-parse, chống retry/replay và xuất evidence theo
hợp đồng hiện hành. TEST vẫn đóng; không tự đổi dataset/split/nhãn/metric/HNLO/
protocol/model revision. Chỉ thị này không cấp quyền của chủ dữ liệu/bên thứ ba
hoặc cho GPU job ngoài phạm vi, và không thay phê duyệt học vụ. Không giả approval
ref, tự đặt ngưỡng khoa học hoặc bỏ cổng kỹ thuật để vượt blocker.

Nguồn: [bản ghi chỉ thị Owner do ChatGPT chuyển lên GitHub ngày 30/10/2026](https://github.com/tantdna2/SafeShift/pull/153#issuecomment-6516812967).

## Dữ liệu và Git

- Giữ nguyên dữ liệu gốc. Sản phẩm dẫn xuất local đặt trong `data/processed/`,
  có quy trình tạo lại rõ ràng; cả `data/` được ignore mặc định trên main mới.
- Không commit dataset, ảnh/video thật, archive dữ liệu, checkpoint, raw model
  output hoặc artifact lớn, secrets hay credentials, kể cả qua Git LFS.
- Chỉ version control code, tài liệu và fixture nhỏ tổng hợp/được phép chia sẻ
  sau review. Không dùng `git add -f`; kiểm tra toàn bộ staged diff và danh sách
  file trước commit. Manifest không chứa dữ liệu nhúng hoặc đường dẫn máy cá nhân.
- Khi được phép chạy VLM, lưu raw output của từng mẫu/lần gọi **trước** parse
  hoặc tổng hợp; liên kết sample ID, prompt, model/version, cấu hình sinh và run ID.
  Giữ cả lỗi, lần chạy dở và provenance, không chỉ nhãn hoặc điểm tổng hợp.

## Code và bằng chứng kiểm tra

- Dùng đường dẫn tương đối từ repository root trong code, cấu hình và tài liệu.
- Giữ bốn nhãn canonical và quy tắc INVALID/support/recall theo nguồn lịch sử
  đã dẫn trong ARCHITECTURE. Application records/model transport mới không phải
  production schema/parser hoặc protocol freeze. Không tự bổ sung metric pending.
- Demo và tests chỉ dùng bản ghi tổng hợp, phải phân biệt rõ với kết quả thật;
  không đưa số demo vào báo cáo khoa học, không viết backend sinh dự đoán giả.
- Chỉ thêm code/module/thư mục có chức năng được giao; không tạo train.py,
  notebook GPU, inference pipeline hoặc nhập lại stub/hệ thống cũ cho đủ cấu trúc.
- Ghi nguồn/version/checksum đầu vào, môi trường/dependency versions, lệnh chạy,
  cấu hình, seed nếu có ngẫu nhiên, Git commit và vị trí artifact cho mỗi lần chạy.
- Code dùng lại cần test phù hợp, gồm lỗi/biên có ý nghĩa. Không lấy mẫu dataset
  thật làm fixture được commit; không thêm dependency khi chưa cần.
- Smoke test hiện tại: `python -B -m unittest discover -s tests -v`.
  Chạy kiểm tra phù hợp thay đổi; ghi rõ kết quả, giới hạn và kiểm tra chưa chạy
  trong PR/log. Chỉ đánh dấu hoàn thành khi có bằng chứng.
- Test lịch sử thuộc commit lưu trữ và môi trường tương ứng; không chạy chúng
  trên scaffold mới rồi kết luận hệ thống cũ lỗi.

## Thiết kế notebook Kaggle: kiểm môi trường trước thực nghiệm

Nguồn bắt buộc: [chỉ thị Owner ngày 31/10/2026 tại PR #155](https://github.com/tantdna2/SafeShift/pull/155#issuecomment-6533181366).
Đây là yêu cầu thiết kế, không approval review/merge hoặc kết quả GPU.

- Trước thiết kế/phát hành notebook thực nghiệm, thu thập bằng chứng target:
  kernel/worker Python và ABI/OS/kiến trúc, cách provision worker đúng phiên bản,
  pins/torch/transformers/compiled ABI; layout Input/unique marker, manifest/source/
  weights SHA256 và allowlist; scratch/output device, free space, cấp phát thật,
  ghi/fsync/cleanup, RAM/cgroup/quota/time; GPU count/model/driver/visibility và
  CUDA/FP16 trong child đúng môi trường. Ghi rõ giới hạn chưa load weights thật.
- Nếu chưa đo Kaggle thực tế, bàn giao trước một diagnostic cell có giới hạn
  hoặc notebook preflight độc lập cho Owner chạy với cùng Inputs/settings.
  Không dùng lượt production để phát hiện rồi vá dần lỗi môi trường cơ bản.
  Preflight lặp lại được, không Owner execution slot/consumption/native inference,
  không tải weights hoặc walk đệ quy không giới hạn. Công khai side effects
  provision phần mềm pinned, cấp phát/xóa scratch và vị trí evidence/export.
- Tách rõ `ENVIRONMENT_OBSERVED`, `CPU_SOFTWARE_PASS`, `LIVE_GPU_PREFLIGHT_PASS`,
  `WEIGHTS_LOADED`, `INFERENCE_VERIFIED`, `SCIENTIFIC_QUALIFIED`. Chỉ claim mức
  đã có bằng chứng; local mock/CPU synthetic không là Kaggle GPU/model-fit PASS.
  Thiếu/lỗi bằng chứng phải BLOCKED/NOT_RUN/UNVERIFIED, không im lặng thành READY.
- Thiếu/sai Input/hash/path/package ABI/allocation/GPU/driver/CUDA/technical gate
  hoặc lịch sử không rõ phải chặn production trước consumption khi có thể.
  Giữ nguyên no-retry/resume/replacement/overwrite theo hợp đồng; không né science,
  source/nhãn/split/metric/protocol/model revision/TEST hoặc bịa approval. Không
  hỏi lại quyền notebook đã được Owner cấp trong phạm vi quyền của họ; quyền
  bên ngoài và cổng khoa học vẫn riêng.
- Bàn giao cùng nhau notebook production, diagnostic/preflight không tiêu lượt,
  tests/receipts máy đọc được, lệnh tái lập, hướng dẫn chạy/export/xử lý lỗi và
  danh sách live constraints chưa kiểm. Không hứa không còn lỗi GPU/model nếu
  chưa thể chứng minh load weights bằng hành động GPU thực tế được phép.
- Kiểm thử âm tính: marker thiếu/trùng/sai, source/weights/hash sai, Python thiếu/
  tải sai/package mismatch, mount sai, cùng/khác filesystem/thiếu dung lượng/quota,
  CUDA/driver thiếu, output partial/unknown và preflight lặp. Assert preflight
  không Owner slot, không attempt, không model call. Giữ đối chiếu BASE/hash lịch sử.

Quy tắc này chỉ COMPLETE sau final HEAD được ChatGPT review, Antigravity audit,
merge được cho phép riêng và hậu merge xác minh có quy tắc trên main; Draft/CPU
PASS hoặc comment không tự hoàn tất yêu cầu.

## Candidate160 retry/resume — chỉ thị Owner 31/10/2026

Nguồn: task trực tiếp của Owner “Loại bỏ cơ chế One-Shot/No-Retry” cho
InternVL3.5 và MiniCPM-V-4, ghi tại
[DEC-20261031-CANDIDATE160-RECOVERY](docs/research/CANDIDATE160_RECOVERY_DECISION_20261031.md).
Đây là bổ sung vận hành, thay các lệnh cấm retry/resume/replacement và khóa
vĩnh viễn **chỉ cho hai notebook Candidate160 Owner**. Không sửa hoặc hồi tố
quyết định cũ; luồng grant/pilot khác giữ hợp đồng riêng.

- Owner có thể tiếp tục/chạy lại sau lỗi trong phạm vi đã giao, kể cả lỗi load,
  mà không xin phép thủ công từng lần. Mỗi kích hoạt tạo run/attempt riêng;
  tối đa160 calls và12 giờ/lượt, không retry nội bộ vô hạn hoặc job trùng.
- Giữ mọi raw/error/attempt/hash/marker cũ; resume dùng lịch sử kiểm checksum và
  custody, kể cả Outputs Kaggle cũ. Không xóa khóa hoặc sửa source lock để chạy.
  Thiếu/mâu thuẫn lịch sử phải ghi BLOCKED và yêu cầu bổ sung evidence có sẵn.
- Rerun toàn bộ tạo series riêng; resume tiếp tục series vận hành hiện hành.
  INITIAL/RECOVERY/FULL_RERUN không tự trộn vào khoa học. Quy tắc chọn kết quả
  phân tích là **PENDING**; không chọn output thuận lợi, gộp AUROC hoặc nâng PASS.
- Khóa tiến trình tự nhả khi tiến trình/worker kết thúc. Kaggle VM độc lập không
  có shared lock: Owner phải dừng phiên trước và attach đủ Outputs trước resume;
  không claim global exactly-once khi thiếu shared state.
- Giữ nguyên160 TRAIN/order/revisions/source/checkpoint hashes/C1/HNLO/metric/
  nhãn/protocol/raw-before-parse, preflight môi trường và mọi quyền dữ liệu.
  Task mã nguồn chỉ CPU synthetic, không GPU hoặc tiêu lượt thực nghiệm.
- Dừng ở một Draft PR. ChatGPT kiểm GitHub và Antigravity audit độc lập trước
  merge; không tự nhận audit hoặc merge đã hoàn thành.

## Quy trình bắt buộc cho mọi notebook Kaggle — Owner 31/10/2026

Nguồn: [chỉ thị Owner tại PR #156](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161)
và task trực tiếp khôi phục thực nghiệm ngày31/10/2026. Đây là bổ sung có truy
vết, áp dụng cho mọi model/cohort/notebook Kaggle hiện tại và tương lai, kể cả
phiên Codex mới; không hồi tố sửa các quyết định lịch sử.

- Khi phát triển bất kỳ notebook SafeShift nào dự kiến chạy trên Kaggle,
  Codex phải kiểm mã nguồn và local integration, rồi **tự chạy trên Kaggle
  thật** bằng CLI/API chính thức, với dữ liệu thật trong phạm vi được phép,
  dùng số mẫu tối thiểu đủ kiểm các đường kỹ thuật quan trọng. Ban đầu một
  ảnh theo thứ tự đã khóa; thêm trường hợp chỉ khi có lý do kỹ thuật ghi rõ.
- Kiểm cùng production entrypoint/child/CLI/path types, runtime/pins/Input,
  source/checkpoint/revision/precision/C1; phải nạp weights thật, inference
  thật trên GPU, raw-before-parse, parser/HNLO liên quan và export ZIP/SHA256.
  Preflight, CPU mock/unit tests hoặc GPU tensor probe không đủ bàn giao.
- Smoke có ID, sample ID/hash, cấu hình, source/notebook hash, giới hạn ảnh/
  calls/time/resource và evidence riêng. Không tiêu/sửa production history,
  không trộn vào kết quả khoa học, không tạo cohort khoa học hoặc đổi dữ liệu/
  split/nhãn/prompt/model/precision/parser/HNLO/metric/protocol để đạt PASS.
- Lỗi phải giữ cả log/raw/archive/receipt FAIL, sửa tận gốc, thêm regression,
  chạy local rồi kiểm Kaggle lại có giới hạn. Không retry vô hạn/job trùng.
  Chỉ phiên bản notebook/source cuối có bằng chứng thật mới được bàn giao
  **READY FOR REVIEW**; source/runtime/Input thay đổi phải kiểm lại tương ứng.
- Không kết nối/xác thực được, thiếu Input/GPU/quota/quyền hoặc chưa chạy
  inference/export thật → **BLOCKED / NOT VERIFIED**, không READY FOR OWNER.
  Không yêu cầu Owner trở thành người phát hiện lỗi cơ bản bằng production.
- Owner đã cho phép các smoke kỹ thuật có giới hạn trên dữ liệu/tài nguyên họ
  kiểm soát; không hỏi lại quyền chung từng lần. Dùng xác thực chính thức,
  không yêu cầu token/password/kaggle.json qua chat, không log/commit/upload
  credentials và không đổi privacy hoặc suy quyền sang TEST/bên thứ ba.
- Sau ChatGPT review, Antigravity audit độc lập và merge được cấp quyền,
  **Owner tự chạy thực nghiệm chính thức đầy đủ**, gửi Output cho ChatGPT.
  Codex không tự chạy toàn bộ cohort thay Owner. Một smoke PASS không chứng
  minh cả160 ảnh/long-run/quality hoặc hoàn tất quyết định khoa học PENDING.

Trong phạm vi này, quy tắc mới thay hướng dẫn cũ cho phép bàn giao chỉ với
preflight/Owner diagnostic và giới hạn task chỉ CPU ở snapshot Candidate160
phía trên. Retry/resume production vẫn theo quyết định recovery; smoke một
call riêng không dùng production reservation/history. Không xóa artifact
CONSUMED/BLOCKED_RESERVED_NO_RETRY/UNKNOWN/replacement1. Dừng ở Draft PR #156;
không tự merge, tự nhận audit PASS hoặc đổi scientific selection=PENDING.
