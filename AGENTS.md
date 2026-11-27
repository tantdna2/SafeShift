# SafeShift — Hướng dẫn làm việc

## Bắt đầu mỗi task

1. Đọc trọn file này, [README](README.md) và [ROADMAP](docs/ROADMAP.md).
   Với code, đọc thêm [ARCHITECTURE](docs/ARCHITECTURE.md) và chỉ mở
   module, test và hợp đồng liên quan. Đối chiếu [PROJECT_STATE](docs/PROJECT_STATE.md)
   và chỉ đạo Owner/PR hiện hành để xác định đúng source, phạm vi và quyền.
2. Trên Windows, `D:\SafeShift` là gốc dự án. Với Orca, chọn Worktree
   location riêng của SafeShift là `D:\SafeShift\.worktrees`, kiểm đường dẫn
   tuyệt đối Orca trả về trước khi giao việc. Tái sử dụng workspace phù hợp
   trên D, kể cả phiên Coordinator và worker Codex/Antigravity.
3. Tạo workspace, repo/worktree, file tạm, notebook, môi trường Python,
   cache model, dataset, checkpoints, artifacts và kết quả SafeShift trên D.
   Cấm chủ động tạo các tài nguyên này trên C. Chỉ giữ trên C dữ liệu bắt
   buộc của ứng dụng/hệ điều hành khi không có cơ chế chuyển phù hợp.
   Dùng `data/processed/` Git-ignored cho dẫn xuất và scratch, có đường
   dẫn dưới gốc dự án và có thể tái lập. Với từng process được hỗ trợ,
   ghim cwd, `TEMP`/`TMP`/`TMPDIR` và cache theo công cụ trên D. Giữ
   Windows system/user environment và profile dùng chung. Nếu Orca
   không truyền env cho chat/worker, cấu hình lại trong từng shell gọi
   subprocess trước khi tạo file. Xem [thao tác Windows và kiểm liên kết](docs/ARCHITECTURE.md#windows--workspace-và-tài-nguyên-safeshift).
4. Giữ file này tối đa **20.000 byte UTF-8**. Ghi chi tiết nhiệm vụ vào
   tài liệu chuyên biệt. Khi thay chỉ thị, kiểm tổng dung lượng các file
   Codex thực sự nạp từ gốc tới cwd, kể cả override và chỉ thị người dùng
   đang áp dụng. Xác minh phiên mới đọc hết ở mức nạp hiện có.

## Khóa luận hiện hành

[Owner chọn CT1–CT3](https://github.com/tantdna2/SafeShift/pull/136#issuecomment-7208108548)
sau phản biện độc lập. PR #136 đã merge và hậu kiểm tại
`77d625ad6b9f1bd52c1cc3b3bdc4e60aebf3251a`. Tiếp tục một PR triển khai
với [kế hoạch](docs/EXECUTION_PLAN.md), [thiết kế Khóa luận](docs/research/THESIS_EXECUTION_PLAN_2026.md)
và [hợp đồng CT1–CT3](docs/research/THESIS_CT123_PREPARATION.md).

- Benchmark First theo thứ tự baseline, lỗi, truy nguyên, đề xuất,
  phản biện, Owner chốt, triển khai và E1–E5. CT1 ưu tiên Qwen3 cùng
  revision, A C1 gốc, B ưu tiên tiêu chí ngành, C đối chứng trung tính.
  Audit ảnh mù trước inference mới. Chốt biên và quota theo bằng chứng.
- CT2 là hướng thuật toán riêng với M lượt model và K lượt review. CPU
  dùng ba projection Full-TRAIN đã niêm phong. Giữ cohort 3.763 TRAIN đã
  phơi nhiễm, GT chỉ chấm sau khi chọn hàng đợi, không dùng GT để xếp
  hạng hoặc sửa nhãn. Qwen3 Composite, InternVL3.5 Grammar V2 và MiniCPM
  Normalization V1 là ba sản phẩm nhãn dị thể. MiniCPM strict C1 là
  sensitivity. Báo `PROVISIONAL_PRE_FINAL_ADMISSION` của nguồn và giới
  hạn hồi cứu. HNLO đối chứng phụ theo nguồn, calibration cần score
  tương thích, validation và phạm vi học vụ.
- CT3 hỗ trợ audit và truy nguồn. Ảnh, reviewer, nghiên cứu người dùng,
  TEST 1.250, GPU, Kaggle, inference mới và thí nghiệm xác nhận cần quyền
  đúng phạm vi. Đọc [protocol dữ liệu](docs/research/THESIS_DATA_PROTOCOL.md)
  trước khi chia nhóm, kiểm overlap hoặc thiết kế validation/TEST.
- Giữ nguyên M1/M2/R1–R5, C1, GT/split và hồ sơ lịch sử. Đọc
  [quyết định append-only](docs/research/DECISIONS.md) trước khi thay phương
  pháp, score hoặc thí nghiệm. D9R22 và successor theo phạm vi đã chốt,
  DEC-PA3-011 còn PROPOSED. Roster bốn mô hình của Seminar là lịch sử.
  Bất kỳ thay đổi roster, split, GT, metric, protocol hoặc model revision
  cần quyền Research Lead và quyết định mới theo đúng phạm vi. Không
  suy từ merge, benchmark, shadow run hay pre-audit sang quyền khoa học.

## Dữ liệu, lịch sử và vị trí artifact

- Giữ bất biến dữ liệu gốc, journal, source lock, raw, lỗi, partial và
  provenance. Không ép 100% SUCCESS, dùng parser lax hoặc GT để chữa lỗi,
  loại ca lỗi hay trộn series. Chỉ dùng bảng dẫn xuất đúng quyết định
  như Qwen3 Composite V1. Chuyển source, repair và resume theo hợp đồng
  từng route, từng ticket và quyền hiện hành.
- Khi inference được cấp quyền, ghi raw từng sample/lần gọi trước parse,
  liên kết sample ID, prompt, model/revision, cấu hình sinh và run/attempt.
  Ghi source/input SHA, env, lệnh, seed, vị trí artifact, status và lỗi.
- Giữ `legacy/pre-reset-20261024` và tag
  `safeshift-pre-reset-20261024` bất biến, không viết lại lịch sử, force
  push, chỉnh source lock để dùng quyền cũ hoặc tự sửa/đóng/rebase/merge
  sáu Draft lịch sử. [HISTORY](docs/HISTORY.md) định tuyến commit lưu trữ
  và các PR. Chỉ tra exact revision, giữ code legacy ngoài main trừ phần
  được review và chấp thuận.
- Chỉ commit code, tài liệu, fixture tổng hợp nhỏ/được phép. Không commit
  ảnh/video thật, raw output, dataset, archive, weights/checkpoint, file
  lớn, secrets hoặc credentials, kể cả qua LFS. Không `git add -f`.
  Kiểm danh sách staged và toàn bộ staged diff. Dùng đường dẫn tương đối
  từ repo root trong code, manifest và cấu hình chia sẻ, với ngoại lệ
  đường dẫn quản trị máy trong chính sách Windows này.
- Khi chuyển tài nguyên, ghi branch, commit, trạng thái staged/unstaged
  và phiên liên quan. Dùng thao tác Git/Orca được hỗ trợ, kiểm SHA256 của
  artifact và dữ liệu, giữ bản gốc đến khi xác minh đích. Không ghi đè,
  di chuyển workspace đang chạy khi chưa bảo toàn trạng thái, hoặc xóa
  app state/cache dùng chung. Ghi alias cũ và điều kiện retarget khi có.

## Code, kiểm thử và điều phối

- Giữ bốn nhãn canonical và semantics INVALID/support/recall. Demo và
  test chỉ dùng fixture tổng hợp, ghi rõ khác kết quả nghiên cứu. Đọc
  ARCHITECTURE, tái sử dụng module hiện có, test lỗi/biên phù hợp, tránh
  backend dự đoán giả, dependency hoặc pipeline ngoài phạm vi.
- Chọn kiểm thử phù hợp. Smoke tổng quát
  `python -B -m unittest discover -s tests -v`. Test lịch sử dùng ref
  và môi trường tương ứng. Ghi rõ kết quả, giới hạn, giá trị chưa kiểm và
  bằng chứng có thể tái lập. Phân biệt kết quả đã kiểm chứng, thông tin
  do người khác cung cấp và giả thuyết.
- Điều phối qua Orca với skill đúng executable, tối đa hai worker đồng
  thời mặc định. Medium/High theo task. GPT-6.2 Astra và Gemini 4 Neon
  dành cho bài khó cần thiết, hạn chế Carbon, loại Claude và GPT-OSS 120B.
  Kiểm model/effort hiệu lực, vị trí và quota, lưu dispatch/receipt.
  Tái sử dụng session đúng vai trò. Khi quota hoặc liveness không rõ,
  bảo toàn công việc và kiểm lại qua Orca trước mọi thao tác retry.
- Phân biệt kiểm thử Codex, review trực tiếp đúng HEAD, audit Antigravity
  độc lập, quyền merge, hậu kiểm và exact-source release. Chỉ làm bước
  được cấp trong task. Review/audit/merge cũ không tự áp sang HEAD mới.
  Không tự cấp phép, suy từ QA sang kết quả khoa học hoặc bypass release.

## Định tuyến vận hành Kaggle và historical handoff

Đọc [Kaggle failure/release gates](docs/KAGGLE_FAILURES_AND_RELEASE_GATES.md)
trước khi thiết kế, sửa hoặc giao notebook. Áp dụng quy tắc môi trường,
preflight lặp được, thử kỹ thuật tối thiểu đúng source, G0–G6, raw trước parse,
checksums và receipt. [Owner đã cấp smoke có giới hạn](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161)
trong phạm vi tài nguyên họ kiểm soát. Chỉ thị hoặc route cụ thể CPU-only,
Owner-only, TEST đóng hay no-submit vẫn áp dụng. Khi Owner cấp quyền trực
tiếp trong phạm vi của họ, thực hiện theo gate kỹ thuật và giới hạn, không
hỏi lại quyền chung từng job. Phê duyệt học vụ và quyền bên thứ ba vẫn riêng.
Dùng xác thực chính thức, không yêu cầu/đăng credentials.
[Chỉ thị Owner về Kaggle](https://github.com/tantdna2/SafeShift/pull/153#issuecomment-6516812967)

| Khi mở task thuộc phạm vi này | Đọc trước khi thao tác |
| --- | --- |
| Candidate160, retry/resume, FP32 resampler | [Candidate160](docs/CANDIDATE160_KAGGLE.md), [quyết định recovery](docs/research/CANDIDATE160_RECOVERY_DECISION_20261031.md), [production engineering](docs/research/CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md), [DECISIONS](docs/research/DECISIONS.md). Candidate160 tối đa 160 calls/12 giờ mỗi lượt theo quyền đã cấp. Resume, rerun, repair, review và scientific selection là các việc riêng. |
| InternVL #177–#179 và Issue180 | [Orca/Antigravity](docs/INTERNVL3763_ANTIGRAVITY.md), [execution](docs/INTERNVL3763_EXECUTION.md), [campaign](docs/TRAIN3763_CAMPAIGN.md). Không tái dùng grants. Chỉ tiếp tục NOT_ATTEMPTED ở route được cấp, giữ caps, mirror và claims. Khi monitor được cấp, theo giới hạn 15 phút, ghi RUNNING_UNVERIFIED và resume cùng Operator session sau; uncertainty chặn retry. |
| Owner UI, deferred, PR196 | [manual reconciliation](docs/TRAIN3763_MANUAL_RECONCILIATION.md), [deferred reconciliation và official-report](docs/TRAIN3763_DEFERRED_RECONCILIATION.md). Giữ INTENT35, mọi lịch sử, raw/partial, không fake COLLECTED/MEASURED/refund. Owner tự thực hiện thao tác đã dành riêng cho họ. |
| MiniCPM PR198–200, source/RAM và Owner restart | [V3 recovery](docs/MINICPM_RUN1_RECOVERY.md), [V4-4](docs/MINICPM_V44_REPAIR.md), [V5 RAM](docs/MINICPM_V5_RAM_REPAIR.md), [offline continuation](docs/MINICPM_OFFLINE_CONTINUATION.md), [PROJECT_STATE](docs/PROJECT_STATE.md). Giữ mọi holds, grants, reservations và failure snapshots, signed 16 GiB floor và raw/hash custody. Không chuyển lịch sử/quyền giữa V1/V2/V3/V4/V5. Giữ same Operator khi bàn giao yêu cầu, người chạy theo đúng route, ≤3 bước khi quy trình Owner UI yêu cầu. |
| Full-TRAIN repair và lịch sử nhiệm vụ | [Issue #167](https://github.com/tantdna2/SafeShift/issues/167), [DECISIONS](docs/research/DECISIONS.md), [PROJECT_STATE](docs/PROJECT_STATE.md), [ảnh chụp chỉ thị trước khi rút gọn](https://github.com/tantdna2/SafeShift/blob/208a6b1f485fa492eb0c49e95dbc236d41bde0e0/AGENTS.md). Dùng nguồn lịch sử để xác định ràng buộc chính xác của task đã cấp, không áp ngược quyền lên task mới. |

Dấu kiểm cuối chỉ thị SafeShift — quyền chạy theo exact source và task.
