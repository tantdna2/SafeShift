# Tổ chức repository SafeShift — giai đoạn 2

Ngày 24/10/2026. BASE: `934575e1c5064e37dc76a42e5267a639eb20dbbc`,
[main sau PR #127](https://github.com/tantdna2/SafeShift/commit/934575e1c5064e37dc76a42e5267a639eb20dbbc).
Branch: `docs/repository-organization-phase2-20261024`.
HEAD và kết quả bàn giao được ghi trong Draft PR của branch này để tránh tự tham chiếu SHA.

## Phạm vi thực hiện

Đã fetch main và tạo worktree riêng từ đúng BASE. Main local đang được một
worktree khác sử dụng và cũ hơn remote; không reset/checkout worktree đó.
Đã kiểm tra GitHub: PR #127 MERGED; sáu PR #67, #99, #101, #102, #117, #121
vẫn OPEN/DRAFT, giữ nguyên HEAD. Không sửa file local ngoài Git của người dùng.

Chỉ chuyển hai báo cáo dưới đây, giữ trang dẫn tại đường dẫn cũ; thêm mục lục
reports và báo cáo này; cập nhật liên kết ở bốn trang điều hướng giai đoạn 1.
Không chuyển/xóa thêm file. Các đoạn “chưa triển khai giai đoạn 2” trong báo cáo
giai đoạn 1 là lịch sử được bảo toàn, không phải trạng thái bàn giao hiện tại.

| Đường dẫn cũ / trang dẫn giữ lại | Bản đầy đủ |
| --- | --- |
| [three_model_scientific_analysis_20261023.md](../three_model_scientific_analysis_20261023.md) | [reports/three_model_scientific_analysis_20261023.md](three_model_scientific_analysis_20261023.md) |
| [repository_organization_phase1_20261024.md](../repository_organization_phase1_20261024.md) | [reports/repository_organization_phase1_20261024.md](repository_organization_phase1_20261024.md) |

Git biểu diễn việc chuyển có trang dẫn bằng file mới cộng file cũ được sửa;
không tuyên bố đây là hai rename thuần túy. Số file trực tiếp trong notes chưa
giảm vì còn trang dẫn tương thích; thay đổi này gom nội dung báo cáo dài và tạo
điểm đến cho báo cáo mới, chưa phải đợt giảm mạnh số lượng file.

## Bằng chứng đủ điều kiện di chuyển

Quét toàn bộ 689 blob Git tại BASE, không quét dữ liệu local hoặc worktree cũ:
tìm đường dẫn, basename, SHA-256 và Git blob SHA của hai ứng viên trong mọi loại
file, gồm JSON, notebook, script, test, receipt và manifest. Kiểm tra cấu trúc
JSON `path`/`sha256`: 5.983 bản ghi trỏ file trong cây Git, thuộc 19 tệp chứa pin,
gồm đủ 10 source lock diagnostics. Hai ứng viên không có bản ghi pin hoặc
tham chiếu từ mã thực thi; các hit tên file chỉ thuộc tài liệu điều hướng,
TASKS và bảng kế hoạch giai đoạn 1. Không sửa TASKS; liên kết lịch sử đi qua trang dẫn.

SHA-256 dưới đây tính trên blob UTF-8/LF tại BASE, không phải hash của bản đã đổi liên kết:

| Báo cáo | SHA-256 tại BASE | Liên kết tương đối đã đổi | Anchor giữ tại trang dẫn |
| --- | --- | ---: | ---: |
| Ba mô hình | `9b81f4ec57c8ebc163a5185d3ebbae9b414bc419d2bd086828e8df42f9632c33` | 18 | 12 |
| Tổ chức giai đoạn 1 | `b026362ba9fec32b68f7c5042a92175f5999cc22f7ecf97012daa31e4a8214bb` | 6 | 8 |

Đối chiếu bản mới với blob BASE sau đúng phép biến đổi đích liên kết tương đối:
toàn bộ văn bản còn lại, bảng, số liệu, trạng thái kiểm toán, ngày, lệnh chạy và
đường dẫn root trong code block giữ nguyên. Mọi heading/anchor cũ có đích tương
ứng ở bản đầy đủ; các liên kết đi ra vẫn trỏ đúng file và fragment ban đầu.

Đã đọc [bootstrap Recovery224](../../safeshift/diagnostics/qwen3_recovery/bootstrap.py),
[bootstrap TRAIN](../../safeshift/diagnostics/hnlo_train/bootstrap.py),
[generator recovery](../../scripts/build_qwen3_s2_recovery.py) và
[generator TRAIN](../../scripts/build_hnlo_train.py): chúng kiểm tra toàn inventory,
hash và release cụ thể. HEAD tài liệu không phải release mới; không chạy generator,
không sửa lock và không chạy notebook tại HEAD này. Các release cũ vẫn tra từ commit gốc.

## Phân loại để dọn sâu tiếp

Đếm bằng Git tại BASE, các nhóm dưới đây có thể chồng vai trò. “Có pin” nghĩa
xuất hiện trong bản ghi JSON `path`/`sha256`, chưa bao hàm mọi hợp đồng khác;
không có pin trong thống kê không đồng nghĩa an toàn để di chuyển.

| Khu vực | File được theo dõi | Có pin trực tiếp | Nguồn phân loại |
| --- | ---: | ---: | --- |
| notes/ | 129, gồm 120 Markdown | 120 | [Mục lục notes](../README.md), báo cáo/receipt, các lock |
| notebooks/ | 34, gồm 32 notebook | 33 | [Mục lục notebook](../../notebooks/README.md), generator/bootstrap/test |
| configs/ | 103, gồm 102 JSON | 100 | [Mục lục config](../../configs/README.md), code/authority/lock |
| safeshift/diagnostics/ | 80 Python | 80 | Import, entrypoint, source lock và kiểm thử |
| Root | 18 | 17 | Governance, môi trường, pin và literal path |

### Cần cho nghiên cứu và kiểm chứng hiện tại

| Khu vực | File / nhóm cụ thể | Vì sao giữ và cách giảm nhầm lẫn |
| --- | --- | --- |
| notes/ | Hai báo cáo vừa chuyển; `pa3_r2_cpu_completion_20261015.md` và `.summary.json`; `hnlo_train_v4_20261019.md`; `qwen3_s2_oom_20261022.md`; `qwen3_s2_recovery224_20261022.md`; `evidence/three_model_20261023/*` | Theo dõi kết quả, failure và ranh giới bằng chứng. Mục lục dẫn đến báo cáo mới; runbook/receipt/evidence giữ đường dẫn. |
| notes/ | `source_license_audit.md`, `dataset_schema.md`, `manifest_builder.md`, `dataset_validation.md`, `duplicate_leakage_audit.md`, `visual_provenance_review.md`, `distribution_imbalance_audit.md`, `research_feasibility_audit.md`, `w1_dataset_audit.md` | Nền tảng nguồn, split/label, leakage và giới hạn miền; không xếp vào archive chỉ vì là W1. |
| notes/ | `pa3_four_model_seminar_scope.md`, `hnlo_phase2_capability_audit.md`, `hnlo_t1_cpu_results_20261017.md`, `hnlo_t1_tokenizer_manifest_20261017.json`, `hnlo_raw_logit_capture_prep_20261017.md`; `w2_d9r22_seminar_scope_redesign.md` | Roster, T1/tokenizer và scope có hiệu lực. PREP/capability không phải kết quả GPU mới; giữ D9R22 effective, DEC-PA3-011 proposed. |
| notebooks/ | `pa3_r2_full_train_kaggle.ipynb`; tám `SafeShift_HNLO_TRAIN_*_SHARD*_V4.ipynb`; `SafeShift_QWEN3_S2_RECOVERY224_V1.ipynb` | 10 notebook gắn với kết quả gần đây; source/release/attempt riêng, không chạy từ HEAD dọn tài liệu. |
| notebooks/ | `SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb`; bốn `SafeShift_InternVL3_*`; hai `SafeShift_HNLO_RESOURCE_PILOT8_*_DATASET_PATH_V3.ipynb` | 7 notebook hỗ trợ kỹ thuật, có authority và source lock riêng; không biến pilot thành full TRAIN. |
| configs/ | `pa3/r2_authority.v1.json`; `diagnostics/hnlo_train_{authority,source,provenance}.v4.json`; `diagnostics/qwen3_s2_recovery_{authority,source}.v1.json`; `pre_freeze/d9r22_seminar_scope.v1.json` | Execution identity, pin và scope; không sửa grant, cohort hoặc lock. |
| safeshift/diagnostics/ | `hnlo_train/*`, `qwen3_recovery/*`, `qwen3_s2_oom.py`; `hnlo_capture.py`, `hnlo_hf.py`, `hnlo_moondream.py` | Capture/audit/evaluate và chẩn đoán gắn bằng chứng hiện có. Không suy tên diagnostics thành code phụ có thể xóa. |
| Root | `REPOSITORY_GUIDE.md`; `AGENTS.md`, `ROADMAP.md`, `DECISIONS.md`, `TASKS.md`, `EXPERIMENTS.md`; `.gitignore`, `.gitattributes` | Điều hướng, quản trị và bảo vệ bytes/data. README vẫn bị pin, giữ nguyên. |

### Lịch sử cần giữ và ứng viên archive có điều kiện

Các ứng viên sau là danh sách để xét ở PR riêng, chưa được chứng minh có thể
di chuyển ngay. Phân loại dựa trên vai trò và phụ thuộc, không dựa trên từ old,
backup, diagnostic hay legacy trong tên.

| Khu vực | File / nhóm lịch sử | Điều kiện trước khi xét archive |
| --- | --- | --- |
| notes/ | `ls1_runbook.md`, `ls1_validation.md`, `ls1_calibration_failure_analysis.md` | Giữ bằng chứng calibration failure; runbook có pin Recovery224 và tài liệu/notebook LS1 còn tham chiếu. Code LS1 vẫn được PA3/aggregate import; không archive cả tuyến LS1. |
| notes/ | `pa3_synthetic_runbook.md`, `pa3_qwen_runbook.md`, `pa3_qwen_validation.md`, `pa3_full_train_kaggle_runbook.md`, `pa3_task5_*.md`, `pa3_task6_runtime_prep.md`, `pa3_r2_cpu_audit_20261015.md` | Tuyến trước completion và handoff lịch sử; giữ pin, lệnh, failure và liên kết log. Chỉ xét sau khi có bản đồ release và trang dẫn an toàn. |
| notes/ | `resource_pilot8_20261019.md`, `resource_pilot8_dataset_path_v2_20261019.md`, `w2_ovis_gpu_smoke_runbook.md`, `w2_ovis_gpu_smoke_result.md` | V1/V2/smoke có replacement hoặc vai trò lịch sử nhưng vẫn source-pinned; không xóa failed prep/diagnostic. V3 vẫn hỗ trợ truy vết TRAIN. |
| notes/ | Các hồ sơ `w2_*` còn lại về roster/runner/qualification/P2/P2.1 | Chia theo hợp đồng và release tại mục lục; chưa tuyên bố toàn nhóm hết hiệu lực. Các decision brief, qualification FAIL và freeze/authority vẫn là provenance. |
| notebooks/ | Hai `ls1_*`; bốn `pa3_*` trước R2; bốn pilot V1/V2; hai `w2_internvl3_p21_*`; ba `w2_paligemma_*` | Đúng 15 notebook lịch sử trong index. Cả 32 notebook đều nằm trong lock Recovery224, có generator/test/bootstrap; chưa ứng viên nào chuyển an toàn trong task này. |
| configs/ | `experiments/ls1.v1.json`, các authority PA3 trước R2; `diagnostics/resource_pilot_*` V1/V2; `pre_freeze/*`, `frozen/*` ngoài nhóm đang tra cứu | Frozen/pre_freeze không quyết định hiệu lực bằng tên. Phải đối chiếu consumer, source/release/grant và đường dẫn test từng file; không gom/archive JSON theo thư mục. |
| safeshift/diagnostics/ | `one_click/*`, `resource_pilot/*`, `internvl3_cuda/*`, `internvl3_driver/*`, `internvl3_hnlo/*`, `internvl3_recovery/*` | Còn import dùng lại từ TRAIN/recovery và còn hợp đồng replay. Không có package nào được chứng minh bỏ được. |
| Root | `requirements-d9r20-{kosmos,ovis,plamo}.txt`, `requirements-{internvl3-t4,moondream-bridge,moondream-t4,paligemma-t4,validation}.txt`; `PA3_SEMINAR_DIRECTION_VERDICT.md`, README | Đủ 8 requirements; script/test/runbook dùng literal path, ví dụ `scripts/w2_internvl3_t4_smoke.py` và `tests/test_internvl3_prep.py`. 17/18 file root có pin; chỉ guide mới không có pin trực tiếp. Không chuyển môi trường/placeholder verdict hoặc sửa README. |

`.gitkeep`, `__init__.py` và các mục lục giữ vai trò cấu trúc; không coi chúng là
rác vì ngắn hoặc giống nhau. Những file không liệt kê riêng tiếp tục giữ nguyên;
kiểm kê toàn bộ tên file có thể tái tạo bằng lệnh ở cuối báo cáo.

### Trùng lặp có bằng chứng, chưa đủ điều kiện xóa

Hai file `safeshift/diagnostics/hnlo_train/tokenizer.py` và
`safeshift/diagnostics/resource_pilot/tokenizer.py` cùng blob Git
`9769acc02042ccdc141011f3c40d95249ddfad6e`. Tuy nhiên chúng dùng relative import
`.contract.MODELS` khác package; cả hai được auditor riêng import, TRAIN còn có
evaluator dùng. Đây là trùng bytes, chưa chứng minh dư thừa ngữ nghĩa hoặc xóa
an toàn. Ngoài cặp này và placeholder `.gitkeep`, không có cặp blob không rỗng giống nhau
khác trong năm khu vực tại BASE. Không có file nào được kết luận đủ bằng chứng
để xóa; bản có tên/version gần nhau không mặc nhiên là bản sao dư thừa.

## Ưu tiên dọn tiếp và ranh giới tái lập

1. Đặt báo cáo tổng hợp mới thẳng vào reports, dẫn từ index; tránh tạo thêm báo
   cáo dài cạnh runbook. Giai đoạn này đã tạo cấu trúc và hai trang dẫn đầu tiên.
2. Trước PR chuyển nhiều file, lập bảng từng đường dẫn → consumer/import →
   container pin/checksum → release SHA → đích mới → trang dẫn/anchor. Ưu tiên
   tài liệu không có pin mới phát sinh; không chuyển nguyên nhóm theo prefix.
3. Muốn giảm file phẳng của notes thực sự, xét các ứng viên lịch sử nêu trên sau
   khi xác định phạm vi release bất biến và cách người đọc tra bản lịch sử.
   Không sửa lock/authority cũ để hợp thức hóa relocation. Với file còn pin,
   giữ bản gốc tại chỗ; mọi thay đổi chiến lược release cần task riêng.
4. Notebook/config/code/env chỉ xét sau khi có thiết kế source mới được review:
   giữ nguyên release cũ và thêm consumer mới có kiểm thử ở phạm vi được duyệt.
   Không tái tạo notebook hoặc dùng refactor để cấp quyền thực nghiệm. Tách
   code chung của cặp tokenizer chỉ khi kiểm chứng hai contract và CPU regression.
5. Mỗi PR sau phải so BASE/HEAD, kiểm tra toàn bộ pin và link/anchor; chạy các
   suite CPU đúng consumer bị ảnh hưởng. Bất kỳ lỗi kế thừa nào phải được tái hiện
   nguyên trạng ở BASE; không sửa test/lock để đạt PASS. Sáu Draft PR cũ do người
   dùng xử lý riêng. Nghiên cứu A/C không thuộc kế hoạch thực hiện của PR này.

## Kiểm tra và tái tạo bằng chứng

Môi trường Python 3.11.9, Git 2.52.0.windows.1, Windows; standard library,
không cài dependency, không ngẫu nhiên. Artifact local mới tại
`data/processed/repository_organization_phase2_20261024/`, được ignore.

| Kiểm tra | Kết quả |
| --- | --- |
| CPU aggregate tại BASE và sau relocation | PASS; hai JSON đối chiếu bằng nhau, dùng đúng đầu vào đã commit. |
| CPU tập trung tại BASE và sau relocation | Mỗi lượt 16/16 PASS, 0 skip; cùng lệnh, cùng identity. |
| Hai báo cáo đầy đủ | Chỉ 24 đích liên kết tương đối đổi; nội dung còn lại khớp blob BASE sau biến đổi đó. |
| Link, anchor, trang dẫn cũ, UTF-8 | PASS: 206 liên kết nội bộ trong phạm vi và 1 incoming link từ TASKS; thêm 40 phép thử hai đầu của đủ 20 anchor cũ; tổng 65 lượt kiểm tra fragment. UTF-8 strict, không BOM, không đường dẫn máy cá nhân. |
| Phạm vi | 10 Markdown: 6 sửa và 4 thêm; không xóa. 683 file BASE ngoài phạm vi giữ nguyên blob, gồm toàn bộ code/test/notebook/JSON/authority/evidence và logs quản trị; đủ 10 source lock và cả 673 đường dẫn có pin giữ nguyên bytes. |
| Workspace gốc | Đối chiếu status, branch/HEAD và SHA-256 của 11 file ngoài Git trước/sau; giữ nguyên. Không duyệt/sửa worktree cũ. |
| Whitespace và staged diff | `git diff --check`, `git diff --cached --check`; đối chiếu danh sách file và toàn diff trước commit. |

Lệnh từ repository root, dùng output chưa tồn tại:

```powershell
git ls-tree -r --name-only 934575e1c5064e37dc76a42e5267a639eb20dbbc -- notes notebooks configs safeshift/diagnostics
git ls-tree --name-only 934575e1c5064e37dc76a42e5267a639eb20dbbc
git grep -n -e three_model_scientific_analysis_20261023 -e repository_organization_phase1_20261024 934575e1c5064e37dc76a42e5267a639eb20dbbc
python -m scripts.analyze_three_model_summaries --output data/processed/repository_organization_phase2_20261024/base_aggregate.json
python -m scripts.analyze_three_model_summaries --output data/processed/repository_organization_phase2_20261024/head_aggregate.json
python -m unittest tests.test_three_model_summaries tests.test_ls1.EvaluationTests.test_auc_ranking_survives_probability_saturation tests.test_ls1.EvaluationTests.test_auc_ties_and_absence -v
git diff --check
git diff --cached --check
git diff --cached --name-status
```

Hai lệnh aggregate phải chạy lần lượt trước/sau thay đổi ở cùng BASE checkout;
tên base/head không tự chứng minh provenance. Không chạy full repository suite,
release bootstrap, raw auditor, GPU, inference hoặc truy cập dữ liệu bị khóa:
phạm vi chỉ relocation tài liệu, không thay consumer/production. Không tuyên bố
toàn suite hay source inventory ở HEAD là PASS thực thi. Source lock, authority,
manifest, notebook, dữ liệu và code cũ bất biến; không thêm dữ liệu vào Git.
Giữ Draft PR để ChatGPT kiểm tra trực tiếp GitHub; dừng sau khi mở, không merge
hoặc gọi Antigravity.
