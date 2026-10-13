# PA3 Seminar redirect — kiểm tra phạm vi tài liệu (2026-10-13)

BASE xác minh bằng fetch origin/main:
`3a52b549d623bdb4b8b6753abe3adf116bbc6100`; local main HEAD khớp, tracked tree
sạch trước sửa. File untracked của người dùng giữ nguyên. Nhánh/worktree riêng
`docs/pa3-seminar-baseline-20261013`; HEAD cuối và URL Draft PR ghi trong handoff.

Phạm vi: README/ROADMAP, overlay TASKS/runbook, append DEC-PA3-006 và EXPERIMENTS,
trang điều hướng, Form guide, note kiểm tra này. **Xóa: không có; di chuyển: không có.**
Không có file dư thừa đã chứng minh đủ điều kiện xóa; giữ evidence và liên kết cũ.

Kết quả kiểm tra trên Windows, Python 3.11.9, Pillow 11.3.0 (môi trường kiểm
thử CPU, không phải runtime Kaggle đã pin):

| Kiểm tra | Kết quả |
| --- | --- |
| `git diff --check` | PASS, không lỗi whitespace. |
| Link/anchor tương đối trong tài liệu mới/phần cập nhật và runbook | PASS: 48 link/anchor; UTF-8 hợp lệ, không đường dẫn máy cá nhân mới. |
| Phạm vi và bảo toàn | PASS: đúng 9 file Markdown sửa/thêm, không xóa; 474 file BASE còn lại giữ nguyên byte. DECISIONS/EXPERIMENTS giữ nguyên toàn bộ prefix cũ; TASKS giữ nguyên suffix lịch sử. |
| Phân loại tài liệu | PASS: 107 Markdown = 21 CURRENT, 85 HISTORICAL, 1 DEPRECATED theo quy tắc trang điều hướng. |
| Metadata/hash/authority | PASS: cohort/inference hashes khớp pin; authority, code/config, prompt, manifest và placeholder verdict không đổi. Không kiểm pixels hay raw run thật. |
| PA3 CPU suite | **161 tests: 156 PASS, 4 SKIP, 1 FAIL**, 584.324 giây; không ghi overall PASS. |

Lệnh suite (từ repository root của worktree, trước commit tài liệu; implementation
và tests byte-identical BASE):

```text
python -m unittest tests.test_pa3_synthetic tests.test_pa3_boundaries tests.test_pa3_native tests.test_pa3_feasibility tests.test_pa3_runtime_prep tests.test_pa3_seminar_direction
```

FAIL kế thừa: `tests.test_pa3_seminar_direction.AuthorityTests.test_committed_grant_is_null_and_prior_authority_untouched`
ở assertion `assertIsNone(value["grant"])`. Main đã merge grant non-null;
test còn giả định PREP. Tái hiện riêng **1/1 FAIL** trên tracked main sạch tại
BASE bằng lệnh sau; không sửa test hoặc authority để làm suite xanh:

```text
python -m unittest tests.test_pa3_seminar_direction.AuthorityTests.test_committed_grant_is_null_and_prior_authority_untouched
```

4 SKIP gồm symlink không khả dụng, host interpreter khác volume của fixture và
hai real-Linux opt-in runtime checks;
không bật Internet/runtime build. Suite dùng synthetic fixtures/API doubles;
CPU PASS không là T1/runtime GPU hay hiệu năng PA3 thật. Không chạy lại toàn suite
vì chỉ tài liệu thay đổi và lỗi đã được đối chiếu riêng với BASE.

Log/helper local (không commit): `data/processed/pa3_redirect_validation/`
(`base_tests.txt`, `check_docs.py`; tên log không có nghĩa toàn suite đã chạy trên
main sạch). HEAD/PR, staged scope và source main được đối chiếu khi xuất handoff.

Không chạy full discovery, GPU/model, TEST, audit archive chẩn đoán thật hoặc CI
trong task này. Đây là thay đổi tài liệu; code/config/authority/manifest/prompt/
weights và placeholder verdict giữ nguyên. Chưa có archive/tokenizer của run
90 ảnh để CPU audit thật; không công nhận GO_PA3 hoặc số liệu hiệu năng.
