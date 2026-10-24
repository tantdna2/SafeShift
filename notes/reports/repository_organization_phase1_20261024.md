# Tổ chức repository SafeShift — giai đoạn 1

Ngày 24/10/2026. BASE: `cf6d4d633fd8bf5179672733211061686c7af6e9`
([main sau PR #126](https://github.com/tantdna2/SafeShift/commit/cf6d4d633fd8bf5179672733211061686c7af6e9)).
Branch: `docs/repository-organization-phase1-20261024`.

## Phạm vi và trạng thái ban đầu

Đã fetch `origin/main` và đối chiếu SHA trực tiếp bằng `git ls-remote`.
Checkout ban đầu ở branch Recovery224, HEAD `484b40355b0971832f81bc7a4c377cd190bbdd91`;
không có tracked diff, có các file ngoài Git của người dùng. Branch tài liệu được
tạo từ BASE trong worktree riêng, không checkout lại hoặc stage file của workspace gốc.
Không đọc nội dung nghiên cứu local chưa được yêu cầu đưa vào commit.

Đã đọc AGENTS, README, ROADMAP và các mục liên quan của DECISIONS/TASKS
(D9R22, PA3-R2, DEC-PA3-011/018, V4, S2 OOM, Recovery224 và PR #126).
**README hiện khớp hash trong 10 source lock. Người dùng đã chọn giữ nguyên README**
sau khi được thông báo xung đột với yêu cầu chỉnh README. Vì vậy thêm
[REPOSITORY_GUIDE](../../REPOSITORY_GUIDE.md) cùng ba mục lục mới; không sửa tài liệu
hiện hữu, quyết định, task log, code, notebook, cấu hình, dữ liệu hoặc test.

## Kiểm kê chọn lọc tại BASE

`git ls-files` cho **684 file**, không phải 729. Đếm theo Git để loại file local,
cache và worktree khỏi phạm vi; không đọc sâu mọi file. Dùng `git grep`/`rg` để
xác định import, link, literal path, generator và pin. Nhóm sau có thể chồng vai trò.

| Nhóm | Đường dẫn và số lượng | Nhận định |
| --- | --- | --- |
| Code gắn kết quả HNLO/PA3 | `safeshift/pa3/` 36 file; `safeshift/diagnostics/` 80 file | PA3 native/R2, capture, TRAIN V4, pilot và recovery. Tên diagnostics không có nghĩa chỉ code phụ. |
| Hạ tầng dùng lại | `safeshift/data/` 6, `protocol/` 20, `runners/` 31, `qualification/` 7, `ls1/` 11 | LS1 là hướng nghiên cứu lịch sử nhưng `ls1.evaluate.auc` vẫn được `scripts/analyze_three_model_summaries.py` dùng. Tổng package có 193 file kể cả hai file gốc. |
| Script hỗ trợ/chẩn đoán | `scripts/` 52 Python + `.gitkeep` | CLI W1, qualification/smoke, provision, generator, CPU tổng hợp ba mô hình; chưa di chuyển script nào. |
| Notebook cần giữ để truy vết kết quả gần đây | R2 1, V4 8, Recovery224 1 | 10 file; phân biệt baseline gốc, failed tail và cohort bổ sung. |
| Notebook hỗ trợ và lịch sử | Kỹ thuật 7, lịch sử 15 | Đủ 32 notebook; chi tiết trong [notebook index](../../notebooks/README.md). Không notebook nào được xem là rác. |
| Config/manifest đang được tham chiếu | `configs/` 102 JSON; `data/manifests/` 10 JSON | D9R22 vẫn có hiệu lực; frozen/pre_freeze cùng có dependency; source lock/authority, cohort/order/hash phải giữ. |
| Tài liệu và bằng chứng | `notes/` 127 file, gồm 118 Markdown, 5 JSON, 2 CSV, 2 file khác | Có báo cáo hiện tại, runbook PREP và lịch sử xen nhau. Gói evidence ba mô hình giữ nguyên bytes. |
| Kiểm thử và giao diện dữ liệu | `tests/` 133 file; `schemas/` 4; `prompts/` 3 | Test source/hash/topology, fixture tổng hợp, schema/prompt là hợp đồng. |
| Nhóm còn lại | `data/` tổng 14; `outputs/` 4; `paper/` 1; root 17 file | Hình W1 nhỏ, placeholder, log và 8 requirements; không có thư mục results được theo dõi. |

Điểm gây nhầm: README chưa phản ánh báo cáo đã merge ở #126; ROADMAP là kế hoạch
đề xuất, không phải bảng receipt hiện thời; runbook PREP và báo cáo hoàn tất ở
cạnh nhau; “lịch sử” vẫn có hàm được dùng lại; `pre_freeze/` vẫn được tham chiếu.
Các file local ngoài Git không phải kết quả đã xuất bản của repository.
[Hướng dẫn mới](../../REPOSITORY_GUIDE.md) phân biệt raw audit Qwen2.5,
saved-score recomputation InternVL3 và Qwen3 được cung cấp/chưa xác minh S2 gốc;
giữ DEC-PA3-011 PROPOSED, Moondream2 và giới hạn TRAIN.

## Ràng buộc đường dẫn và hash

[Recovery224 source lock](../../configs/diagnostics/qwen3_s2_recovery_source.v1.json)
bao phủ 673/684 đường dẫn BASE, gồm cả 32 notebook. 11 file ngoài danh sách đó
không mặc nhiên được di chuyển: còn authority/lock, evidence PR #126, script và
test có checksum trong receipt. [Gitattributes](../../.gitattributes) và
[evidence attributes](../evidence/three_model_20261023/.gitattributes) bảo vệ bytes/EOL.

Ví dụ dependency đã xác minh:

- `scripts/build_hnlo_train.py` và `scripts/build_qwen3_s2_recovery.py` cố định tên notebook, lock, authority, runbook và danh sách source; không chạy build để sửa cấu trúc.
- `safeshift/diagnostics/*/bootstrap.py` yêu cầu inventory/hash và đúng release checkout. HEAD tài liệu mới không phải source thực thi thay thế.
- `scripts/analyze_three_model_summaries.py` cố định `notes/evidence/three_model_20261023` và summary Qwen2.5; receipt pin hash script/test/đầu vào.
- `requirements-internvl3-t4.txt` được smoke script/test tham chiếu; `scripts/audit_distribution.py` được code, test, tài liệu và protected fixture tham chiếu.
- Các log TASKS/DECISIONS chứa liên kết lịch sử; di chuyển tài liệu không được làm hỏng các liên kết đó hoặc sửa lại lịch sử.

## Phương án giai đoạn 2 — đề xuất, chưa triển khai

Ưu tiên **một thư mục mới `notes/reports/`**, chỉ cho tài liệu tổng hợp không
bị pin sau khi kiểm tra lại tại BASE của PR giai đoạn 2. Giữ nguyên package,
scripts, notebook, configs, manifest, prompts, requirements và evidence. Không
thêm tầng `src/`, không gom mọi “diagnostics” vào archive.

```text
REPOSITORY_GUIDE.md
notes/
  README.md
  reports/               # hai báo cáo đủ điều kiện ở bảng dưới
  evidence/              # giữ vị trí và bytes
  ...                    # audit/runbook và tài liệu pin giữ nguyên
notebooks/README.md       # phân biệt vai trò bằng mục lục
configs/README.md         # chỉ dẫn hợp đồng tại chỗ
safeshift/, scripts/, tests/, data/, outputs/, prompts/, schemas/  # giữ cấu trúc
```

| Đường dẫn cũ | Đường dẫn đề xuất | Điều kiện / phụ thuộc |
| --- | --- | --- |
| `notes/three_model_scientific_analysis_20261023.md` | `notes/reports/three_model_scientific_analysis_20261023.md` | Ứng viên không có trong lock Recovery224 và không là đầu vào hash của receipt đã kiểm tra. Sửa relative links trong báo cáo và các mục lục mới; để trang dẫn ở đường dẫn cũ cho TASKS và URL lịch sử. Kiểm tra pin mới trước khi làm. |
| `notes/repository_organization_phase1_20261024.md` | `notes/reports/repository_organization_phase1_20261024.md` | Báo cáo mới của task này; có thể chuyển trong PR giai đoạn 2 nếu chưa phát sinh pin. Cập nhật guide/index và relative links; giữ trang dẫn cũ để PR này còn truy cập được. |
| `notes/ls1_runbook.md`, `notes/w2_ovis_gpu_smoke_runbook.md` | Chỉ cân nhắc `notes/archive/<tên-cũ>` ở một đợt riêng | **Giữ tại chỗ lúc này**: source pin, notebook/link/log và protected fixture. Chưa đủ điều kiện đưa vào PR giai đoạn 2 tối thiểu. |
| `notebooks/pa3_qwen_full_train_kaggle.ipynb` và notebook lịch sử khác | Chỉ cân nhắc `notebooks/archive/<tên-cũ>` ở một đợt riêng | **Giữ tại chỗ**: notebook/generator/test/bootstrap/source lock; không đổi attempt hoặc tái tạo notebook cũ. |
| `requirements-*.txt` | Có thể cân nhắc `configs/environments/<tên-cũ>` về sau | **Giữ tại chỗ**: literal path trong script/test/runbook, hash nguồn và môi trường lịch sử. |
| `safeshift/`, `scripts/`, `configs/`, `data/manifests/`, `prompts/`, `schemas/`, `notes/evidence/` | Giữ nguyên | Hợp đồng/import/hash/provenance; chưa có lý do đủ mạnh để di chuyển. |

**Có thể chuyển với cập nhật liên kết:** hai báo cáo đầu bảng, chỉ sau khi rà pin
mới và giữ đường dẫn cũ bằng trang dẫn. Không có file lịch sử nào được chứng minh
an toàn để di chuyển ngay mà không xử lý dependency. **Tuyệt đối chưa chuyển/xóa**
README, logs quản trị, source/authority/lock, manifest, prompt/schema, evidence/
receipt, notebook, code và các file có protected hash. Việc mở khóa hoặc phát
hành source mới là phạm vi nghiên cứu riêng, không gộp vào PR tổ chức thư mục.

## Sáu Draft PR cũ cần người dùng xem xét

Đã tra GitHub metadata và toàn bộ danh sách file thay đổi ngày 24/10/2026;
cả sáu OPEN, DRAFT, chưa merge. Khuyến nghị dưới đây không phải quyết định đóng.

| PR / HEAD lúc kiểm tra | Giao nhau và xử lý đề xuất |
| --- | --- |
| [#67](https://github.com/tantdna2/SafeShift/pull/67), `e85300ab` | D5 engine/adapter và logs cũ; có implementation riêng chưa hiện diện nguyên vẹn trên main. Giữ để review riêng hoặc trích phần còn cần sau đối chiếu contract; không merge nguyên nhánh cũ khi dọn tài liệu. |
| [#99](https://github.com/tantdna2/SafeShift/pull/99), `6effffea` | Sửa README/ROADMAP/log và đề xuất index cũ. Đề nghị cân nhắc đóng sau khi giữ thông tin độc nhất; hướng dẫn mới không áp dụng DEC-PA3-006 từ PR này. |
| [#101](https://github.com/tantdna2/SafeShift/pull/101), `0e40bd8f` | StateGuard và chẩn đoán NaN trước R2. Giữ hồ sơ chẩn đoán để review riêng; nếu đóng cần lưu lý do, không coi guard là đã được áp dụng. |
| [#102](https://github.com/tantdna2/SafeShift/pull/102), `78b45b68` | Nan probe có source/authority/test riêng. Giữ hoặc đóng sau đối chiếu bằng chứng clamp/R2; không nhập grant/runner cũ vào tuyến hiện hành. |
| [#117](https://github.com/tantdna2/SafeShift/pull/117), `b2c38104` | Full TRAIN V1, overlap code V4; đang HOLD theo DEC-PA3-018. Cân nhắc đóng như bản đã được thay thế, giữ provenance và lịch sử review. |
| [#121](https://github.com/tantdna2/SafeShift/pull/121), `81ae8b10` | V4 cũ thiếu GPU sampling, đã có hồ sơ replacement trong DEC-PA3-018. Cân nhắc đóng bản HOLD sau đối chiếu replacement; không sửa branch/source lock. |

Không đụng branch của các PR trên; không tự đóng hoặc yêu cầu merge/audit.

## Kiểm tra bắt buộc cho giai đoạn 2

1. Fetch main, ghi BASE/HEAD, kiểm tra status/file local và PR còn mở; rà lại toàn bộ nguồn pin và literal references của từng file định chuyển.
2. Với hai báo cáo: kiểm tra link/anchor mới và trang dẫn cũ, kể cả link từ TASKS/DECISIONS và URL đã công bố. Diff chỉ gồm báo cáo/mục lục, không thay kết quả hay lịch sử.
3. Đối chiếu bytes Git của mọi file ngoài danh sách cho phép, đặc biệt toàn bộ lock/authority/manifest/prompt/notebook/evidence. Không tái sinh hash để che việc di chuyển.
4. Chạy `git diff --check`, kiểm tra UTF-8, path tương đối, staged inventory và không có dữ liệu/secrets/local research ngoài nhiệm vụ.
5. Chạy CPU aggregate và `tests.test_three_model_summaries` để bảo đảm đường dẫn evidence/receipt còn đúng; không đọc dataset hay chạy inference.
6. Nếu đề xuất mở rộng sang code/config/notebook: dừng phạm vi PR tối thiểu; cần review release/pin riêng và các suite PA3 boundaries/native/R2, HNLO capture/T1/train/V4, recovery, resource pilot, qualification theo phần bị ảnh hưởng. So lỗi BASE/HEAD, không sửa test/lock lịch sử để nhận PASS. Kiểm tra topology/source tại đúng release commit, không tuyên bố current HEAD là release.

## Kiểm tra giai đoạn 1

Môi trường: Python 3.11.9 trên Windows, không thêm dependency, không ngẫu nhiên.
Artifact kiểm tra local nằm ở `data/processed/repository_organization_phase1_20261024/`,
được ignore và không đưa vào PR.

| Kiểm tra | Kết quả |
| --- | --- |
| Liên kết nội bộ của năm trang mới | 148 liên kết, gồm 3 anchor: PASS; target thuộc cây Git hoặc năm trang mới, không trỏ file local chưa được theo dõi. |
| UTF-8, whitespace, đường dẫn tương đối | PASS; không có đường dẫn máy cá nhân trong năm trang. |
| Phạm vi thay đổi | Chỉ thêm năm Markdown; 684 file BASE giữ nguyên, gồm README, logs, lock, authority, notebook, code, test và evidence. |
| Workspace gốc | Status giữ nguyên; checksum của 11 file ngoài Git ở cấp file khớp trước/sau. Không duyệt hay sửa các worktree cũ. |
| CPU aggregate hiện có | PASS, dùng đúng đầu vào đã commit; không đọc raw/data. |
| Test CPU tập trung | 16/16 PASS, 0 skip, 0 fail. |
| `git diff --check` và staged inventory | PASS, chỉ năm trang thuộc nhiệm vụ; không rename/delete. |

Lệnh CPU đã chạy từ repository root:

```powershell
python -m scripts.analyze_three_model_summaries --output data/processed/repository_organization_phase1_20261024/aggregate.json
python -m unittest tests.test_three_model_summaries tests.test_ls1.EvaluationTests.test_auc_ranking_survives_probability_saturation tests.test_ls1.EvaluationTests.test_auc_ties_and_absence -v
git diff --check
git diff --cached --check
```

Không chạy full repository suite vì chỉ thêm tài liệu; không tuyên bố toàn suite
PASS. Không chạy generator/source-lock test ở HEAD như thể đây là release mới:
bootstrap yêu cầu inventory/commit thực thi gốc. Không chạy GPU, inference,
notebook, raw auditor hoặc đọc dữ liệu bị khóa. Không thêm nghiên cứu local,
không gọi Antigravity, không đóng PR cũ và không merge.
Giai đoạn 2 chưa được triển khai; bàn giao một Draft PR để ChatGPT kiểm tra
trực tiếp GitHub trước khi có bước tiếp theo.
