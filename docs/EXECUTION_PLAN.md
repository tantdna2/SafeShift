# SafeShift — Kế hoạch thực thi M1–M8

Ngày lập: **26/10/2026 (Asia/Bangkok)**. BASE đã đối chiếu GitHub và fetch main: `bffc6032e65b38cb04b33520275a089d87d0d37f`.
Đây là bản giao việc từ [hướng đã chọn](research/SEMINAR_THESIS_DIRECTION_LOCK_20261025.md) và [Master Plan](research/SEMINAR_THESIS_MASTER_PLAN_20261025.md), không thay hai tài liệu đó hoặc tạo quyết định khoa học mới.
Trạng thái tiếp nối ngắn gọn: [PROJECT_STATE](PROJECT_STATE.md).

## 1. Phạm vi, thẩm quyền và cách giao việc

**Đề tài:** SafeShift — Đánh giá và cải thiện độ tin cậy của quyết định nguy cơ an toàn công nghiệp bằng mô hình ngôn ngữ–thị giác.
Seminar đánh giá hồi cứu nhãn sinh ra, HNLO, lỗi nguy hiểm và bất đồng. Khóa luận kiểm chứng logistic có regularization để xếp ưu tiên ảnh cần người kiểm tra bằng HNLO+bất đồng, giữ Qwen3 predictor cố định theo protocol được duyệt.

**Hiện tại: chờ M1 khoa học.** [PR #133 hậu merge](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399480255) xác nhận hoàn thành tài liệu, không phê duyệt M1. D9R22 vẫn có hiệu lực; HNLO/DEC-PA3-011 vẫn **PROPOSED**. Quyền legacy không chuyển sang main mới. Không mở TEST, inference, GPU, annotation hoặc setup bằng tài liệu này.

Mỗi task dưới đây là **một sản phẩm hoàn chỉnh trong một Draft PR**: code nếu cần, kiểm thử lỗi/biên, cấu hình thật sự dùng, hướng dẫn, bằng chứng chạy, cập nhật trạng thái và PR có BASE/HEAD/diff. Không tách folder/interface/test/docs của cùng chức năng thành các PR riêng. Tên file mới dưới đây là **dự kiến**, chưa tồn tại/chưa được lệnh tạo; file hiện hữu có link để truy nguồn. Nếu phải đổi tên, giữ trách nhiệm và tiêu chí nghiệm thu.

Ba trục trạng thái phải ghi riêng trong mỗi bàn giao:

| Trục | DONE/PASS cần bằng chứng gì? | Không được suy ra |
| --- | --- | --- |
| Sản phẩm code/tài liệu | Đủ đầu ra task, kiểm tra phù hợp PASS, giới hạn ghi rõ; Draft PR có thể đạt trục này | Chưa có nghĩa đã review/merge hoặc được phép chạy thật |
| Kiểm toán GitHub/merge | ChatGPT kiểm tra trực tiếp đúng HEAD/diff; audit theo chỉ định Owner; findings xử lý; merge được cấp quyền; ChatGPT xác minh merge commit/main và ghi biên bản GitHub | Draft, approval review hay merge riêng lẻ không hoàn tất khoa học |
| Khoa học/thực nghiệm | Người có thẩm quyền xác nhận quyết định/gate; với run có authority, receipt và kết quả được nghiệm thu; bảo vệ có xác nhận thật | Không cộng số PR/test thành milestone, không xem kết quả âm hợp lệ là lỗi thực thi |

Không audit lại toàn bộ lịch sử mỗi task: kiểm main/HEAD, quyết định liên quan, input hashes và phần thay đổi. Tái kiểm artifact chỉ khi cần chạy/phép tính mới hoặc có mismatch; giữ nguyên mức bằng chứng kế thừa. HEAD đổi sau review thì kiểm phần thay đổi và hiệu lực review trước merge. Audit độc lập không tự mở thêm PR.

Luồng giao việc: **M1-01 → M2-01 → M3-01 → M4-01 → M5-01 → M6-01 → M6-02 → M7-01 → M7-02 → M8-01**.
M1–M5/M8 mỗi milestone một task. M6 tách vì phải có quyền thu thập/nhãn/pilot trước xử lý dữ liệu; M7 tách vì phải khóa implementation/phương pháp trước khi mở target. Đây là các cổng thực chất, không PR chuẩn bị hình thức. Không mở nhánh task tiếp theo trong nhiệm vụ lập kế hoạch này.

## 2. Hồ sơ M1 sẵn để trình Research Lead/giảng viên

Người thực hiện chuyển nguyên mục này cùng hai tài liệu PR #133 tới người duyệt. **Không cần một PR khác để soạn lại hồ sơ M1.** Tất cả ô quyết định dưới đây hiện **PENDING**; phần “phương án” là lựa chọn đã chốt trong đề xuất, chưa là chấp thuận. Ghi câu trả lời/phạm vi/người duyệt/ngày/link bằng chứng vào quyết định mới append-only sau khi nhận được, không điền thay người duyệt.

| ID / câu hỏi cần quyết định | Phương án trình duyệt duy nhất và hệ quả |
| --- | --- |
| A1 — Duyệt trục và sản phẩm hai học kỳ? | Giữ tên đề tài trên; Seminar hồi cứu; Khóa luận kiểm chứng triage logistic trên VLM cố định. Không yêu cầu kiến trúc VLM mới hoặc mở lại P1/P2/P3. |
| A2 — Duyệt điều chỉnh RQ và vai trò HNLO nào? | S-RQ1: nhãn so với HNLO qua miền; S-RQ2: lỗi nghiêm trọng, hazard và sensitivity coverage/trùng; S-RQ3: bất đồng/điểm liên hệ lỗi. Giữ ba lõi D9R22, thêm endpoint HNLO/sensitivity theo hướng §5.1; liệt kê chính xác phần được bổ sung/thay thế. HNLO là đối tượng kiểm định và feature ứng viên, không probability đã hiệu chuẩn. |
| A3 — Duyệt cohort/estimand hồi cứu? | Q25/IVL3 đầy đủ 3.763; so ba model trên đúng 3.539 SUCCESS V4 gốc; Q3 coverage mẫu số 3.763; Recovery224 riêng. Per-image là mốc mô tả, exact/heuristic là sensitivity đã định danh, không nguồn độc lập/CI nguồn. Hợp đồng công thức chi tiết phê duyệt ở M2. |
| A4 — Duyệt ngoại lệ Moondream2 cho Seminar? | Bảng **bốn model**, định lượng ba; Moondream2 HNLO TRAIN **N/A do thiếu bằng chứng tương thích**, kèm hồ sơ kỹ thuật/giới hạn. Không xóa roster, không gán 0, không thay endpoint bằng textual confidence. Nếu không duyệt: M1 chưa PASS; Lead phải xác định quyền/tài nguyên/sản phẩm Moondream2 cần bổ sung trước khi sửa kế hoạch, không tự triển khai nhánh GPU. |
| A5 — Duyệt cách xử lý hazard/control thiếu? | 12 hazard atoms, 7 nhóm phụ, chính sách miền D3 giữ nguyên. M2 đối soát map và continuous controls; thiếu bằng chứng thì N/A cụ thể và giới hạn claim, phải được Lead chấp nhận trước M2 PASS. Không tự coi tất cả N/A đều được chấp thuận hoặc lấy lời VLM làm nhãn. |
| A6 — Khóa luận thực nghiệm này có đủ chuẩn học phần? | Logistic có regularization, Q3 cố định, HNLO+bất đồng; so baseline đơn tín hiệu mạnh nhất khóa trên development, cùng ngân sách review và tính toàn bộ chi phí model phụ. Cần giảng viên xác nhận đóng góp thực nghiệm có đối chứng/ablation, không claim kiến trúc mới. Kết quả âm/chưa đủ bằng chứng chỉ đủ chuẩn khi thiết kế hợp lệ và giảng viên xác nhận; không mặc định được chấp nhận. |
| A7 — Điều kiện xác nhận/thu hẹp claim Khóa luận? | M6 bắt buộc nguồn độc lập, nhãn chuyên gia không xem VLM, đủ nguồn/sự kiện lỗi theo precision plan, target giữ kín. Nếu FAIL: không xác nhận H-T, trình duyệt riêng mức sản phẩm hồi cứu/phát triển; không dùng TRAIN chia lại hoặc TEST làm lối tắt. Moondream2/feature set ba model Khóa luận cần quyết định riêng trước target, không kế thừa tự động ngoại lệ Seminar. |
| A8 — Ai chịu trách nhiệm và quyền gì được cấp tiếp? | Xác nhận Research Lead/giảng viên, Owner, reviewer, người giữ artifact; trước M6 xác nhận người giữ target/chuyên gia nhãn. Tách quyền thiết kế M2, setup CPU M3, đọc saved artifact M4, raw replay, ảnh/nhãn, GPU và target. Ghi deadline/nguồn lực chỉ khi người phụ trách cung cấp; hiện chưa có. |

**Chuẩn tối thiểu xin duyệt:** Seminar có bảng coverage/bốn model, đủ S-RQ1–3 trong phạm vi và N/A được duyệt, bảng/figure tái lập, báo cáo/slide/giới hạn. Khóa luận có phương pháp chạy được, đối chứng và ablation công bằng, nhãn/nguồn độc lập và đánh giá giữ kín khi gate PASS, chi phí, kết luận H-T có tiêu chí bác bỏ, code/receipt/báo cáo tái lập. Không hứa cải thiện, công bố, deadline, chi phí hoặc cỡ mẫu chưa có cơ sở.

Mang theo [điều kiện hậu audit PR #133](https://github.com/tantdna2/SafeShift/pull/133#issuecomment-6399375594): chưa biết chính xác false-safe V4-only; chưa chứng minh bất đồng suy biến trong tập triage; baseline Q3-HNLO-only và toàn bộ cost bắt buộc; tiêu chí đủ sự kiện phải đặt trước xem target, dùng development/pilot hoặc giao thức curator mù được cấp quyền. TrustVLM/LMN là đối chiếu ở giai đoạn viết, không khảo sát lại đề tài trong task này.

**M1 PASS chỉ khi:** A1–A8 có quyết định rõ cho phần thuộc M1, người duyệt/ngày/bằng chứng, phạm vi còn pending chuyển tới đúng gate; không để HNLO/ngoại lệ Seminar/chuẩn học phần chỉ là đồng ý tên đề tài. Quyết định không cấp tự động protocol freeze hay quyền thực nghiệm.

## 3. Đối chiếu mã thật và setup tối thiểu sau M2

Đã đọc [ARCHITECTURE](ARCHITECTURE.md), [README](../README.md), [ROADMAP](ROADMAP.md) và các module/hợp đồng liên quan tại BASE. Cây main hiện có 31 file tracked; các inventory 24/29 file trong tài liệu là snapshot trước PR #133. Không cần sửa những snapshot đó trong PR này.

| Khả năng hiện hữu / điểm tái sử dụng chính xác | Dùng cho Seminar | Khoảng thiếu và xử lý trong M3-01 |
| --- | --- | --- |
| [schema.py](../safeshift/data/schema.py): `SAFETY_LEVELS`, `SampleRecord`, `PredictionRecord` | Bốn nhãn canonical, ID opaque, `None` là INVALID tường minh | Không có split/domain/run/score/status/provenance. Thêm record phân tích có version trong `safeshift/data/saved_reports.py` dự kiến; projection sang record hiện hữu, không nới schema gốc tùy tiện. |
| [validation.py](../safeshift/data/validation.py): mapping strict, ID duy nhất, portable relative path | Từ chối sửa nhãn/ID ngầm, path sai | Bổ sung kiểm provenance/hash/schema và quyền cohort ở reader; path spelling không chứng minh file hay quyền truy cập. |
| [metrics.py](../safeshift/evaluation/metrics.py): `classification_metrics` | Exact ID set; confusion 4×5, support, recall có INVALID, `None` khi support=0 | Bọc bằng bảng planned/status riêng; hàm này từ chối thiếu ID nên không truyền 3.763 GT với 3.539 prediction hoặc lấp 224 bằng Normal/INVALID. Thêm binary/severe error, strata, disagreement và controls trong `evaluation/seminar.py` dự kiến sau M2. |
| [sensitivity.py](../safeshift/evaluation/sensitivity.py): `weighted_auc`, `join_reports`, `components`, `evaluate`, `exact_score_consistency` | AUROC tie=0,5, exact ID/GT/domain; thành phần bắc cầu; trọng số/đại diện và undefined | `join_reports` yêu cầu SUCCESS + canonical label + score hữu hạn: chỉ dùng đúng subset, không làm reader cho toàn planned hoặc drop INVALID âm thầm. Chỉ dùng estimand được M2 duyệt; giữ API/snapshot PROPOSED cũ. |
| [analyze_source_sensitivity.py](../scripts/analyze_source_sensitivity.py): `checked_bytes`, `internvl_rows`, `verified_archive_members`, `original_s2_zip`, `verify_v4_shard`, `verify_v4_cohort` | Kiểm checksum/CRC, allowlist member, unit/binding/config, bốn shard V4 và status đầy đủ; chống recovery/diagnostic thay thế | Reader CLI gắn hợp đồng lịch sử, không production framework. Trích các helper cần dùng sang `data/saved_reports.py` cùng test tương đương trong M3 nếu cần dùng chung; giữ CLI cũ tương thích/không đổi kết quả. Không phục hồi legacy pipeline. |
| [contracts.py](../safeshift/models/contracts.py): `ModelInput`, `ModelOutput`, `VisionLanguageModel` | Chỉ tham chiếu provenance/typing cho kế hoạch tương lai | Không backend/raw writer/scorer; không dùng nó làm bằng chứng raw đã lưu. Seminar saved-report không cần triển khai model transport mới. |
| [test_schema.py](../tests/test_schema.py), [test_metrics.py](../tests/test_metrics.py), [test_source_sensitivity.py](../tests/test_source_sensitivity.py) | Có lỗi ID, INVALID, zero support, AUROC oracle pairwise, archive tamper, V4 status/identity, recovery boundary | Bổ sung synthetic tests cho reader/report/RQ2/RQ3 và CLI; tái dùng fixtures nhỏ, không copy dataset thật. Demo hiện hữu giữ nhãn synthetic, không đưa vào kết quả. |
| [pyproject.toml](../pyproject.toml) | Python 3.11+, standard library, không runtime dependencies | M3 ưu tiên JSON/CSV/Markdown bằng stdlib. Chỉ thêm dependency khi chức năng approved cần và có version/reproducibility; không cài torch/transformers/training stack cho Seminar. |

**Setup M3 là một lần giao sản phẩm**, không thêm task “lập kế hoạch kỹ thuật” trước setup:

1. Đọc M2 đã duyệt và source hiện tại; chạy smoke/unit baseline `python -B -m unittest discover -s tests -v` trên synthetic. Dùng Python 3.11+ hiện hữu; virtualenv chỉ nếu thực sự cần dependency. Không tải dữ liệu/model.
2. Hoàn thành reader hash-bound, status/cohort ledger và metric/report engine trong hai module dự kiến ở bảng trên; giữ chức năng cũ, không thêm abstraction registry/adapter factory chưa dùng.
3. Thêm một CLI `scripts/analyze_seminar.py` dự kiến, nhận config duy nhất `--config` và `--output-dir`, từ chối overwrite; input/output local ở `data/processed/`. Config duyệt dự kiến `docs/research/seminar_analysis_config.v1.json`: protocol SHA, allowlist relative artifact path/hash, cohort IDs/hash, model contracts, metric/variant IDs, N/A decision refs; không nhúng dữ liệu/credentials. Không nhân bản cùng tham số vào nhiều config.
4. Hoàn thiện toàn bộ tests, fixture synthetic nhỏ và hướng dẫn trong `docs/SEMINAR_ANALYSIS.md` dự kiến; cập nhật README/ARCHITECTURE khi triển khai thật. Chạy CLI synthetic end-to-end, có bằng chứng không mở ảnh/raw payload/TEST và chỉ ghi thư mục output được phép.
5. Draft PR M3 gồm tất cả thành phần trên và PROJECT_STATE. Sau review/merge + authority M4, dùng đúng CLI/source/protocol/hash để phân tích thật. Lệnh mới chỉ là hợp đồng dự kiến, **chưa chạy được tại BASE**; M3 phải bàn giao câu lệnh đầy đủ đã thử.

Không tạo `train.py`, notebook GPU, folder rỗng, dataset image parser, backend hoặc HNLO raw scorer trong setup Seminar. Saved score đã có không cần tính HNLO lại. Raw replay/scorer chỉ có khi Lead giao việc với hợp đồng/token alignment và quyền riêng; không là điều kiện ngầm để nâng mọi kết quả lên raw PASS.

| Công việc | Tài nguyên tối thiểu / điều kiện |
| --- | --- |
| M1/M2, M3 fixtures, M4 saved reports/sensitivity, M5/M8 | CPU; đọc saved artifact thật vẫn cần authority cụ thể. Viết tài liệu không cấp quyền artifact. |
| Học logistic, baseline/ablation/CI trên output frozen hợp lệ | CPU ở M7; dependency chỉ bổ sung lúc có implementation cần dùng. |
| Kiểm metadata/quyền/source/nhãn M6 | CPU + người có chuyên môn/quyền dữ liệu; không thay người bằng VLM. |
| Qualification và inference VLM mới trên development/target | Cần GPU thực tế cho đường chạy dự kiến Q25/IVL3/Q3; resource sizing từ pilot được duyệt, không hứa VRAM/giờ/cost. Chạy sequential/cache vẫn tính tất cả calls. |
| Raw replay từ artifact đã lưu | Có thể CPU theo contract/source/môi trường từng model; không đồng nghĩa mọi replay đủ input hoặc được phép. Không tự chạy GPU để “kiểm tra” saved score. |

## 4. Các invariant và bằng chứng nghiệm thu bắt buộc

Đây là yêu cầu cho M2 đặc tả, M3 kiểm synthetic, M4 kiểm artifact đã được phép. Các số là **bằng chứng kế thừa**, không kết quả tái tính trong task lập kế hoạch. Nguồn: [direction §2/§5](research/SEMINAR_THESIS_DIRECTION_LOCK_20261025.md), [receipt](SOURCE_FEASIBILITY_RECEIPT_20261024.json), [results](RESULTS_AND_LIMITATIONS.md).

| Check ID | Phép kiểm và điều kiện PASS / lỗi phải chặn |
| --- | --- |
| C01 — cohort/labels/domain | Exact ID–GT–domain join, unique IDs; TRAIN-only projection từ metadata được phép, không đọc ảnh/annotation/TEST. Q25/IVL3: 3.763, A/N=749/3.014, L01/02/03/04=490/251/8/3.014. Domain A/N lần lượt coal_conveyor 172/650, metallurgy 9/534, oil_chemical 287/491, power 81/575, tunnel 200/764. Giữ D3/mismatch policy; không sửa nhãn để khớp tổng. |
| C02 — V4 gốc | Bốn shard S0–S3, đúng run/attempt/source/release/revision/config, thứ tự/membership lịch sử và checksum chain. S2 TAR SHA-256 `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`; ZIP CRC/sidecars/binding/manifest phải khớp. Planned 3.763 = 3.539 SUCCESS + 1 TECHNICAL_ERROR + 223 NOT_ATTEMPTED. Coverage=3.539/3.763, không gọi run COMPLETE. |
| C03 — common/recovery | Ba model dùng cùng 3.539 V4-success IDs: A/N=700/2.839, levels=460/232/8/2.839. Phần thiếu 224=49 A/175 N. Recovery224 có run/config/receipt riêng dù khớp phần ID thiếu; `baseline_pooling_allowed=false`. Cấm thay bằng diagnostic/rerun, cộng AUROC hay lấy FN composite. Cohort 2.822 cũ chỉ phụ lục, không thay cohort chính. |
| C04 — phép tính/scope HNLO | Saved `pa3_score` hữu hạn, đúng ID/run/phiên bản/chiều (cao hơn là hazard). Nếu sau này được phép tính từ logits: `logsumexp(z1,z2,z3)-z4`, cùng bước/prefix/token alignment và revision; test offset invariance/extreme logits, reject token/prefix sai. Không dùng max logit, generated label hoặc sigmoid làm xác suất nguy cơ. Không trung bình raw HNLO giữa model. |
| C05 — evidence/AUROC | Reproduce với tolerance đã duyệt (helper hiện có `1e-12`) và oracle pairwise độc lập trên synthetic. Q25 full=0,8266558463706973; IVL3 full=0,8861824613751756; common Q25/IVL3/Q3=0,8243818245861219 / 0,88286846475117 / 0,9527927338600111. Sai khác phải truy input/estimand, không sửa kỳ vọng cho PASS. Q25 raw CPU Linux PASS là lịch sử có giới hạn outer receipt shard 1/Windows 1-ULP; IVL3/Q3 saved-score không nâng thành raw PASS. |
| C06 — denominator/status | `INVALID`, TECHNICAL_ERROR, NOT_ATTEMPTED và missing score là các trạng thái khác nhau. Classification 4×5 giữ INVALID trong support/recall; no-output nằm ledger planned riêng. Báo N eligible/planned và lớp/miền bị loại; AUROC một lớp/rỗng là null, không 0/0,5. Không dùng complete-case join để che missingness. |
| C07 — lỗi/bất đồng | Đếm lại false-safe/severe miss từ đúng V4-success prediction IDs; **không có số 38 hoặc khoảng 30–38 mặc định cho V4-only**. Hazard-positive=Level01–03; error-positive là định nghĩa lỗi của predictor cố định, không nhầm hai AUROC. Đo binary/ordinal disagreement trong tập triage eligible, kiểm all-agree/all-invalid/không lỗi/thiếu model/kappa denominator=0; ghi undefined và support. |
| C08 — nguồn/hazard/controls | Chỉ dùng map hazard hợp lệ; 12 atoms chồng lấp không cộng thành N ảnh. Exact pairs đúng hash; catalog visual cũ 0/7 ID-pair khớp không được dùng làm registry. Point/family/dHash là sensitivity, không site/video/camera/session đã xác minh; không CI nguồn hoặc causal claim. Entropy/margin/confidence chỉ khi field và token semantics đủ, nếu thiếu dùng N/A đã duyệt. |
| C09 — Moondream2 | Có hàng trong coverage/result/limitations; N/A có lý do và link ngoại lệ được duyệt. Thiếu approval chặn đóng Seminar; token test CPU hoặc confidence văn bản không là HNLO TRAIN. Không tự loại model khỏi feature roster Khóa luận. |
| C10 — reproducibility | Receipt liên kết input/config/protocol/source SHA, môi trường/dependency versions, command, seed hoặc lý do không ngẫu nhiên, output hashes và mức audit. Refuse overwrite/path escape/hash tamper/duplicate archive member; output JSON không NaN. Raw gốc giữ nguyên, chỉ đọc member được phép; derived ở `data/processed/`, chỉ figure/manifest nhỏ có quyền vào Git. |

M2 phải biến từng C01–C10 thành tiêu chí ứng với output; M3 chứng minh phần thuộc saved-report bằng fixture/oracle, M4 bằng dữ liệu được cấp quyền. Nhánh raw-logit/token-alignment của C04 chỉ áp dụng khi có task capture/scorer riêng được duyệt ở M6/M7, không yêu cầu viết raw scorer trong M3. Không cần tái chạy raw inference để kiểm C05. Thiếu input → STOP bảng phụ thuộc và ghi blocker/N/A theo quyết định, không “sửa” dataset, không điền score giả.

## 5. Task cards để giao Codex

Các bước trong từng card là phạm vi tương lai sau điều kiện bắt đầu; không là quyền được cấp hôm nay. Mọi card kế thừa ba trục DONE ở §1, C01–C10 khi liên quan và cập nhật PROJECT_STATE trong cùng PR nếu trạng thái đổi. Không tạo PR riêng để test/docs/state hoặc audit sửa cùng sản phẩm.

### M1-01 — Nhận và ghi quyết định khoa học chính thức

1. **Mục tiêu:** biến hồ sơ §2 thành một quyết định có thẩm quyền, mở được M2.
2. **Trước bắt đầu:** Draft kế hoạch này được ChatGPT kiểm tra và xử lý theo quy trình merge; có giao việc trình duyệt. Có thể chuyển hồ sơ cho Lead bằng người có thẩm quyền; Codex không tự gửi tin bên ngoài nếu chưa được chỉ định. Chỉ ghi approved khi có phản hồi thực.
3. **Phạm vi:** dùng nguyên hồ sơ đã soạn; thu quyết định A1–A8, điều kiện/ngoại lệ, vai trò và quyền bước tiếp; ghi append-only, dẫn D9R22/DEC-PA3-011 và chỉ rõ thay đổi có hiệu lực; đồng bộ trạng thái/docs thẩm quyền liên quan sau duyệt.
4. **File:** mới dự kiến `docs/research/DECISIONS.md`; cập nhật `docs/PROJECT_STATE.md`, `docs/RESEARCH_OVERVIEW.md`, `docs/ROADMAP.md` nếu quyết định làm đổi trạng thái. Không sửa log legacy.
5. **Bàn giao:** một quyết định có người duyệt/ngày/link bằng chứng, bảng approved/pending/rejected và task M2 được phép; một Draft PR đầy đủ.
6. **Kiểm/bằng chứng:** đối chiếu nguyên văn phạm vi chấp thuận với A1–A8; kiểm link/UTF-8/diff; không lấy merge #133 làm khoa học approval.
7. **DONE/PASS:** tài liệu đủ và kiểm tra PASS; GitHub merge được xác minh riêng; M1 khoa học PASS khi đủ các điều kiện §2. Từ chối hoặc phản hồi thiếu → M1 BLOCKED/PENDING, không đánh dấu DONE.
8. **Ngoài scope:** code, setup, protocol chi tiết M2, artifact thật, GPU, TEST, thay roster tự ý.
9. **Mở tiếp:** M2-01 chỉ khi M1 PASS, quyết định đã được ghi và giao task thiết kế; không yêu cầu soạn thêm brief M1.
10. **Lý do là một task:** chuẩn bị brief đã hoàn thành tại đây; phần còn lại là một sản phẩm quyết định, không tách “xin duyệt” và “ghi biên bản” thành nhiều PR.

### M2-01 — Bàn giao hợp đồng phân tích Seminar đã duyệt

1. **Mục tiêu:** mỗi ô báo cáo truy được input, cohort, công thức, mức bằng chứng và quyền, để M3 triển khai không cần tự chọn khoa học.
2. **Trước bắt đầu:** M1-01 PASS; quyền chỉ đọc đúng metadata/saved-summary cần kiểm tính khả dụng được ghi rõ. Nếu quyền chưa có, hoàn thiện phần từ docs nhưng không khép gate khả dụng.
3. **Phạm vi:** khóa model/revision/run/attempt/prompt/preprocessing/precision/decoding/parser; cohort/status ledger C01–C03; S-RQ1–3, metric/denominator/ties/undefined; controls, D3/12 atoms/7 nhóm; duyệt N/A từng ô và sensitivity không chọn theo gap. Chốt reporting eligible set cho S-RQ3; không biến đường risk–coverage hồi cứu thành ngưỡng vận hành.
4. **File:** mới `docs/research/SEMINAR_PROTOCOL.md`, `docs/research/seminar_analysis_config.v1.json`; append quyết định duyệt nếu cần; PROJECT_STATE. Config là manifest hợp đồng nhỏ, không mẫu thật. Input inventory lớn ở `data/processed/` sau quyền.
5. **Bàn giao:** protocol version/hash và config hợp lệ dùng trực tiếp cho M3, ma trận output R1–R5 bên dưới, artifact allowlist/permission refs, acceptance mapping C01–C10. Không thêm báo cáo “chuẩn bị” riêng.
6. **Kiểm/bằng chứng:** parse JSON; mỗi field có source hoặc explicit unavailable; kiểm công thức bằng ví dụ tay; đối soát ID/hash/nhãn/miền khi có quyền, không đọc raw logits. Continuous controls thiếu không được nhận là đã khả dụng; map hazard chưa hợp lệ chặn ô phụ thuộc.
7. **DONE/PASS:** tài liệu/config đầy đủ, không còn lựa chọn metric/denominator ngầm; reviewer/Lead duyệt version, N/A và claim. GitHub DONE riêng; M2 chưa PASS nếu chỉ merge bản đề xuất. AP mới, kappa, entropy, ordinal, risk–coverage cần định nghĩa cụ thể trước code.
8. **Ngoài scope:** inference, annotations mới, fit ngưỡng, CI nguồn không có source registry, triển khai pipeline.
9. **Mở tiếp:** M3-01 sau protocol M2 được duyệt và nhiệm vụ setup CPU được cấp; M4 chưa được mở.
10. **Gom việc:** model/cohort/metric/control/config/checklist là cùng hợp đồng; không tách thành nhiều PR đặc tả.

| Output M2 phải khóa | Nội dung M4 phải tạo |
| --- | --- |
| R1 — evidence/coverage | Bốn model, full/common/recovery riêng; planned/status/eligible/INVALID/missing, provenance và audit level |
| R2 — S-RQ1 | Confusion 4×5/support/recall/accuracy, nhị phân FN/FP, HNLO hazard AUROC theo miền; hard/ordinal/always-N/always-A và controls khả dụng/N/A |
| R3 — S-RQ2 | Anomaly→Normal, Level01→Level04, Level03 counts, 12 atoms/7 nhóm có map; coverage bounds nếu duyệt, exact và heuristic sensitivity đầy đủ |
| R4 — S-RQ3 | Joint parse availability, unanimous agreement, pairwise kappa, vote entropy, ordinal disagreement, shared blind spots/error complementarity, liên hệ HNLO với lỗi; support/tập eligible/undefined |
| R5 — kết luận/giới hạn | Một trả lời cho mỗi S-RQ, trace tới R1–R4; missingness, exposed TRAIN, source/CI/control/N/A và cầu nối H-T |

### M3-01 — Hoàn thiện hệ thống phân tích Seminar CPU

1. **Mục tiêu:** một lệnh có thể kiểm chứng để tạo R1–R5 theo protocol, không cần dựng thêm project trước khi sử dụng.
2. **Trước bắt đầu:** M2 PASS, code/setup task được giao; synthetic-only authority là đủ để triển khai và test, không tự đọc artifact thật.
3. **Phạm vi:** thực hiện trọn setup §3: reader/provenance/status, projection không mất mẫu, metric/lỗi/disagreement/controls đã duyệt, sensitivity, output JSON/CSV/Markdown và receipt; cấu hình, CLI, tests, usage docs. R5 xuất trace/limitations theo contract; kết luận khoa học do người phân tích viết và nghiệm thu ở M4, không tự sinh claim từ AUROC. Refactor helper có giới hạn nếu cần; không làm giảm strict checks cũ.
4. **File:** `safeshift/data/saved_reports.py`, `safeshift/evaluation/seminar.py`, `scripts/analyze_seminar.py`, `tests/test_seminar.py` dự kiến; sửa các module/test hiện hữu chỉ để tái sử dụng; config M2, `docs/SEMINAR_ANALYSIS.md`, README/ARCHITECTURE/PROJECT_STATE. Không tạo folder mới ngoài cấu trúc hiện hành.
5. **Bàn giao:** một Draft PR có code/test/config/docs hoàn chỉnh; fixture synthetic, lệnh CLI thật và output mẫu ghi SYNTHETIC, input/output schema, error exit codes và receipt mẫu.
6. **Kiểm/bằng chứng:** toàn bộ unittest hiện hành + tests mới; oracle pairwise AUROC, confusion và disagreement tính tay khác thuật toán; C01–C10 synthetic, archive/hash/path tamper, partial/no-output/INVALID/empty/one-class, overlapping atoms, transitive groups, missing model; CLI end-to-end deterministic/refuse overwrite. Chứng minh không tải model hoặc đọc ảnh/TEST qua mock/allowlist và test I/O.
7. **DONE/PASS:** không còn stub ở đường R1–R5 được duyệt, một lần chạy synthetic tái tạo được, test pass/no skip che chức năng; GitHub review/merge được xác minh. Đây là M3 phần mềm, **không** M4 kết quả thật/M1 khoa học.
8. **Ngoài scope:** backend, raw scorer/replay, dataset ảnh parser, GPU, VLM training, triage Khóa luận, đổi metric tự chọn.
9. **Mở tiếp:** M4-01 khi M3 merge đã được xác minh, source/config/protocol được khóa và có authority CPU/artifact cụ thể.
10. **Gom việc:** reader → metric → CLI → tests/docs → state nằm cùng PR; không có PR chỉ dựng thư mục/interface.

### M4-01 — Bàn giao toàn bộ gói kết quả Seminar hồi cứu

1. **Mục tiêu:** trả lời S-RQ1–3 bằng R1–R5 tái lập và đúng mức bằng chứng.
2. **Trước bắt đầu:** M3 và M2 đúng version; authority đọc các artifact cụ thể/hash ở allowlist; Owner cung cấp input hợp lệ; ngoại lệ/N/A đã duyệt. Thiếu một artifact thì giữ blocker phần tương ứng, không tự tìm dữ liệu khóa thay thế.
3. **Phạm vi:** kiểm C01–C10 trên input thật được phép; chạy CPU; đối soát bảng và sensitivity; tính chính xác V4-only false-safe, variation disagreement trong eligible candidates; ghi output, receipt, limitations và figure nhỏ. Nếu bug, sửa code/test/docs trong cùng PR task, chạy lại phần chịu ảnh hưởng với source SHA mới và giữ receipt cũ; không chia PR sửa vặt.
4. **File:** mới dự kiến `docs/research/SEMINAR_RESULTS.md`, figure nhỏ trong `docs/research/` khi cần, PROJECT_STATE; code/tests chỉ nếu sửa lỗi trong scope. Artifact đầy đủ ở `data/processed/seminar/<run_id>/` ignored.
5. **Bàn giao:** R1–R5, command/environment/config/input/output hashes/source SHA, bảng mới tái tính vs kế thừa, N/A refs, verdict từng S-RQ, một Draft PR.
6. **Kiểm/bằng chứng:** coverage trước metrics; exact ID joins và oracle số độc lập; hai lần cùng config ở hai output dir phải cho kết quả số ổn định (timestamp receipt có thể khác); reviewer đối soát counts/FN/FP và selected tables từ input được phép. Không gọi reanalysis là raw audit.
7. **DONE/PASS:** đủ outputs M2, C checks PASS hoặc N/A đã duyệt với claim tương ứng, reviewer nghiệm thu; GitHub DONE riêng. HNLO không thắng/disagreement không hữu ích vẫn được nghiệm thu. Checksum/cohort sai hoặc thiếu Moondream2 exception thì không M4 PASS.
8. **Ngoài scope:** inference để lấp dữ liệu, pooling, mở ảnh review định tính khi chưa được cấp riêng, target/TEST, ngưỡng vận hành hoặc generalization claim.
9. **Mở tiếp:** M5-01 sau kết quả M4 đã nghiệm thu, GitHub kiểm chứng và tiêu chí Seminar được giảng viên xác nhận.
10. **Lý do tách M3:** đây là sản phẩm kết quả thật cần artifact authority/source đã review; không tách từng model hoặc từng bảng thành PR.

### M5-01 — Hoàn thiện báo cáo, slide và hồ sơ bảo vệ Seminar

1. **Mục tiêu:** bộ sản phẩm học phần thống nhất từ M4, dẫn trực tiếp tới H-T.
2. **Trước bắt đầu:** M4 PASS; format/tiêu chí học phần và quyền chia sẻ figure được xác nhận; lịch bảo vệ chỉ ghi khi có thật.
3. **Phạm vi:** báo cáo, slide, speaker notes/traceability, định nghĩa metric/coverage, giới hạn, câu trả lời phản biện và kết luận S-RQ1–3; đối chiếu literature gần ở phần viết theo phạm vi đã chốt, không mở lại chọn hướng. Áp dụng skill slide repo ở task slide này.
4. **File:** `docs/research/SEMINAR_REPORT.md`, nguồn slide/phụ lục nhỏ trong `docs/research/` dự kiến và PROJECT_STATE; bản xuất lớn ở `data/processed/`, không tự commit binary lớn.
5. **Bàn giao:** báo cáo và deck xuất được, notes/trace bảng→artifact, feedback giảng viên; một Draft PR chứa nguồn chia sẻ được và vị trí artifact.
6. **Kiểm/bằng chứng:** mọi số/claim đối chiếu M4; render/visual QA đủ trang, links/citations, kiểm N/A/model roster, tránh nhầm hazard ranking với error detection/calibration.
7. **DONE/PASS:** bộ tài liệu kỹ thuật DONE khi render/trace PASS; GitHub DONE sau quy trình; **M5 học phần chỉ DONE sau xác nhận nghiệm thu/bảo vệ thật**, ghi pending nếu chưa xảy ra.
8. **Ngoài scope:** sửa kết quả để hợp narrative, claim chuyển nguồn/kiến trúc mới, làm thí nghiệm thêm cho slide.
9. **Mở tiếp:** M6-01 khi M5 được nghiệm thu và hướng tiếp nối H-T được ghi nhận; không chờ thành công Khóa luận để đóng Seminar.
10. **Gom việc:** báo cáo/deck/QA/notes là một gói truyền đạt, không PR phụ cập nhật trạng thái thường kỳ.

### M6-01 — Khóa quyền dữ liệu, nhãn và giao thức pilot Khóa luận

1. **Mục tiêu:** một hồ sơ GO/NO-GO có thể cấp quyền thu nhận dữ liệu và pilot, tránh triển khai rồi mới phát hiện thiếu nguồn/quyền.
2. **Trước bắt đầu:** M5 PASS; có đầu mối người sở hữu nguồn/chuyên gia/target custodian để xin xác nhận. Chỉ tiếp cận metadata/hồ sơ trong quyền, chưa xem target scores/labels.
3. **Phạm vi:** chốt nguồn công nghiệp và tương thích nhãn, license/access, vai trò phát triển/calibration/target, registry site/video/camera/session, duplicate procedure; nhãn mù VLM/adjudication; quyền pilot development, model/revision/capture/resource constraints, điều kiện dừng; cách đặt precision criteria từ development hoặc curator mù trước mở target. Ghi rõ ngân sách/b/δ/precision còn phải chốt từ pilot M6-02, không bịa số.
4. **File:** `docs/research/THESIS_DATA_PROTOCOL.md`, log quyết định append-only, PROJECT_STATE dự kiến; hồ sơ nhạy cảm giữ ngoài Git, chỉ link/ref có quyền.
5. **Bàn giao:** protocol thu nhận/nhãn/pilot đã duyệt, access matrix ai được xem gì, artifact schema/source registry contract, curator procedure, tài nguyên được xác nhận hoặc NO-GO có lý do. Một Draft PR cho sản phẩm này.
6. **Kiểm/bằng chứng:** bằng chứng quyền và chuyên môn/người giữ target thực; không dùng filename/point/family như source verified; trace từng grant tới dataset/model/source/release/run/attempt, không chuyển grant cũ. Kiểm không rò nhãn vào người phát triển.
7. **DONE/PASS:** hồ sơ có thể DONE dù NO-GO; gate mở thu nhận chỉ PASS khi quyền/phương pháp nhãn/pilot/custodian đủ. **M6 tổng chưa PASS** ở đây. GitHub DONE không thay access grant.
8. **Ngoài scope:** tải/annotation/inference chưa được cấp, tự thêm dataset/split, xem target để lựa nguồn nhiều lỗi, lập khảo sát paper rộng.
9. **Mở tiếp:** M6-02 khi hồ sơ GO và quyền cụ thể được cấp; nếu NO-GO xin quyết định mức claim/cách giải blocker, không chạy target hay chuyển sang đề tài mới.
10. **Lý do tách:** quyền của chủ dữ liệu/chuyên gia/GPU là đầu vào ngoại sinh trước sản phẩm dữ liệu/pilot; không thể mặc định cấp trong PR code.

### M6-02 — Bàn giao dữ liệu có nguồn/nhãn và gate xác nhận Khóa luận

1. **Mục tiêu:** tạo bộ dữ liệu phát triển–calibration–target được quản lý đúng vai trò và protocol xác nhận đã khóa, hoặc NO-GO có bằng chứng.
2. **Trước bắt đầu:** M6-01 GO, quyền thu nhận/nhãn/pilot chi tiết; người giữ target hoạt động; code/native runner pilot có qualification và authority mới. Nếu runner cũ không tương thích cohort mới, phải triển khai phần tối thiểu cần dùng cùng tests/docs trong task này, được review/khóa trước chạy GPU.
3. **Phạm vi:** người có quyền thu nhận/nhãn/adjudicate; kiểm source/duplicate/label compatibility; manifest nghiên cứu riêng bất biến, giữ InspecSafe nguyên bản/TEST đóng. Development pilot đo sự kiện false-safe, biến thiên feature, calls/VRAM/latency/annotation effort. Dùng bằng chứng này chốt đủ nguồn/sự kiện/độ chính xác, b, δ, confidence level, cost/workload/group limits, eligibility/budget basis, ties/INVALID/overload, baselines/ablation/search budget; không nhìn target kết quả. Duyệt feature set ba model/Moondream2 riêng.
4. **File:** mở rộng `docs/research/THESIS_DATA_PROTOCOL.md`, mới `docs/research/THESIS_PROTOCOL.md`; `safeshift/data/` và `safeshift/models/` chỉ module reader/capture/native adapter thật sự cần pilot, `scripts/` entry point pilot, `tests/` synthetic và usage docs đi cùng; PROJECT_STATE. Dữ liệu/nhãn/raw/manifests lớn ở `data/processed/` theo quyền, không Git; tên adapter chốt theo runner/model đã được cấp, không tạo generic framework trước.
5. **Bàn giao:** receipt quyền/nguồn/nhãn, manifest/hash và chứng nhận custodian target chưa lộ; pilot report/cost thực; protocol xác nhận version/hash; đủ numerical gates đã phê duyệt hoặc NO-GO cụ thể. Có code pilot mới thì bàn giao trọn code/test/docs/config, raw-before-parse và qualification receipt trong cùng PR.
6. **Kiểm/bằng chứng:** zero source/duplicate overlap giữa vai trò theo registry đã xác minh; label provenance/adjudication; raw persist trước parse/error; token alignment model-specific; synthetic I/O/missing/raw-write-failure tests; pilot chỉ development, stop OOM/error theo grant. Adequacy đánh giá theo tiêu chí định trước bằng development/pilot hoặc curator mù được duyệt; không tuyển lại target theo score/lỗi để đạt benchmark.
7. **DONE/PASS:** **M6 PASS** chỉ khi dữ liệu/nguồn/nhãn, đủ precision/events/groups, đối chứng/capture và nguồn lực hợp lệ; protocol/target boundary đã duyệt, code review/merge nếu có. Nếu thiếu, bàn giao NO-GO, phần xác nhận chưa hoàn thành; không hạ chuẩn để PASS.
8. **Ngoài scope:** huấn luyện VLM, fitting triage/feature selection trên target, mở TEST, source giả, số mẫu/power giả. Qualification/pilot không là kết quả target hoặc quyền run lớn.
9. **Mở tiếp:** M7-01 chỉ sau M6 PASS và authority phát triển; nếu NO-GO, chỉ đi M8 theo quyết định giảng viên về mức claim giảm. Development-only thêm chỉ bằng phạm vi được cấp riêng, không tự kích hoạt M7 xác nhận.
10. **Gom việc:** dữ liệu/nhãn/source, pilot tối thiểu và protocol khóa là sản phẩm gate chung; không tách hàng loạt PR scaffold. Các lần review trước GPU có thể nằm trong cùng PR, source/run phải được khóa rõ.

### M7-01 — Hoàn thiện và khóa bộ triage cùng đối chứng trên development

1. **Mục tiêu:** một implementation có thể đánh giá xác nhận, giữ predictor Q3 cố định và toàn bộ pipeline không rò target.
2. **Trước bắt đầu:** M6 PASS; source/data/model/protocol/authority phát triển, development/calibration riêng; target vẫn kín. Reuse capture/adapter đã qualified ở M6-02, chỉ hoàn thiện phần còn thiếu cho run được cấp.
3. **Phạm vi:** feature HNLO theo model + nhãn/bất đồng hữu hạn; normalization trong fold development, regularization chọn theo nguồn, source-weighting đã duyệt; fit logistic và tất cả baselines/ablation cùng supervision/search budget. Qualification/raw capture nếu mới, tests lỗi, batching/mandatory errors/overload, CLI/train/evaluate docs; calibration riêng; khóa model artifacts, baseline chính, threshold nếu có, seeds/config/source trước target.
4. **File:** mới dự kiến `safeshift/evaluation/triage.py`, `scripts/fit_triage.py`, `tests/test_triage.py`; reuse `data/saved_reports.py` và model modules đã cần ở M6; `docs/THESIS_TRIAGE.md`, protocol/config nhỏ trong `docs/research/`, PROJECT_STATE. Artifact fit/raw ngoài Git.
5. **Bàn giao:** bộ triage chạy được, baselines + ablation + tests/config/docs, development/calibration report, freeze manifest/hash và một Draft PR. Không tách PR head/interface/test.
6. **Kiểm/bằng chứng:** không feature nào chứa GT/Level trong ID/source ID; fold/train-only normalization; target read guard; source weighting đúng, input nonfinite/thiếu model, tie deterministic không nhãn, budget equality/mandatory failure/overload; capture_FS zero-error=null; raw-write failure không parse. Chi phí full VLM và cache/fit đều báo, không chỉ logistic.
7. **DONE/PASS:** implementation/qualification/development đủ, protocol compliance và freeze được review; GitHub merge/source khóa xác minh trước target. Baseline mạnh nhất chọn development; bất đồng suy biến báo thật, không thay target/phương pháp để cứu giả thuyết. Đây chưa là M7 xác nhận DONE.
8. **Ngoài scope:** target evaluation, fine-tune VLM, LMN “tái lập” thiếu input; không bình quân raw HNLO hoặc đổi Q3 giữa arm.
9. **Mở tiếp:** M7-02 sau freeze manifest được duyệt, code merge/source final đúng hash, custodian cho quyền một lượt target riêng.
10. **Lý do tách:** sản phẩm phương pháp phải khóa trước target; dùng chung code cho mọi arm, không một PR mỗi baseline.

Các baseline bắt buộc: no-review/all-review làm mốc; random toàn eligible và random predicted-Level04 có seed; Q3-HNLO-only; entropy/margin/confidence nếu đủ capture (N/A cần duyệt); disagreement-only; logistic labels/disagreement-only, HNLO-only và image-weighted. Ablation: bỏ HNLO, bỏ bất đồng, chỉ Q3, bỏ source weighting, đổi đích sang mọi lỗi phân loại. Khóa strongest single-signal comparator trên development. LMN thích nghi chỉ khi đủ input/cùng supervision và được duyệt, không bắt buộc tạo embedding/backend ngoài scope để có tên đối chứng.

### M7-02 — Đánh giá target đã khóa và kết luận H-T

1. **Mục tiêu:** một gói kết quả xác nhận có thể kiểm toán, kể cả phủ định/chưa kết luận.
2. **Trước bắt đầu:** M7-01 freeze PASS, M6 còn hợp lệ, authority đúng dataset/model/revision/source/release/run/attempt; custodian mở quyền đúng bước, không mở TEST.
3. **Phạm vi:** một lượt target theo protocol; inference/capture nếu được cấp hoặc output frozen đúng contract; cùng predictor/cohort/budget và mandatory-error policy cho mọi arm; lưu raw trước parse, lỗi/run dở/overload; CPU metric/paired-source CI, source/domain slices, cost, deviations. OOM dừng, config/run mới cần quyền mới, không pooling âm thầm.
4. **File:** mới `docs/research/THESIS_RESULTS.md`, figures/receipt nhỏ có quyền, PROJECT_STATE; dùng CLI/engine M7-01, thêm test sửa bug trong cùng PR nếu cần. Artifact target/raw/weights ở storage được phép, derived local `data/processed/`.
5. **Bàn giao:** bảng chính/ablation/cost/support/undefined, audit trail và freeze checks, H-T verdict và limitations, một Draft PR. Thay đổi sau khi nhìn target là exploratory, không chạy lại để gọi xác nhận trên cùng target.
6. **Kiểm/bằng chứng:** eligible set và review budget đúng protocol; `capture_FS=Σ(d*e_FS)/Σe_FS`, mẫu số 0=null; residual false-safe số ca và chia tổng Anomaly, severe miss riêng; workload/autoprocess/planned và technical coverage tách biệt. Paired cluster CI giữ cặp arm/source, ghi undefined resamples/ít nguồn; oracle toy capture/budget/CI mechanics và audit input/output hashes. Không coi review là tự động sửa đúng lỗi.
7. **DONE/PASS:** M7 thực hiện PASS khi đủ đối chứng/ablation/receipt/protocol và được nghiệm thu, dù kết quả âm. Lợi ích chỉ PASS nếu cận dưới chênh capture vượt δ tại cùng budget và thỏa cost/workload/group constraints; cận trên <δ bác bỏ lợi ích tối thiểu; CI phủ δ là chưa đủ bằng chứng. Rò target/đổi predictor/giấu chi phí là FAIL thiết kế, không “kết quả âm”. GitHub DONE riêng.
8. **Ngoài scope:** chọn lại b/δ/baseline/target sau thấy kết quả, CI ảnh thay CI nguồn cho đẹp, hiệu quả giảm tai nạn thực địa, nâng HNLO thành calibrated probability.
9. **Mở tiếp:** M8-01 khi kết quả và audit M7 đã nghiệm thu; không yêu cầu H-T thắng.
10. **Gom việc:** target run, mọi bảng/CI/ablation/cost/limitations là một sản phẩm xác nhận; không PR tách theo model/metric.

### M8-01 — Bàn giao luận văn, bảo vệ và gói tái lập cuối cùng

1. **Mục tiêu:** hoàn tất sản phẩm Khóa luận đúng mức kết luận được giảng viên duyệt.
2. **Trước bắt đầu:** M5 và M7 đã nghiệm thu, hoặc quyết định giảng viên cho phạm vi giảm sau M6 NO-GO; format/lịch/quyền chia sẻ thực được xác nhận.
3. **Phạm vi:** luận văn, slide, appendix nguồn/protocol/metric/reproducibility, kết quả âm/chưa xác nhận và limitations; đối chiếu LMN/TrustVLM/công trình gần đúng phần viết; render/visual QA, phản hồi học phần; bảo toàn artifact/ref, cập nhật trạng thái cùng PR.
4. **File:** `docs/research/THESIS_REPORT.md`, nguồn slide/appendix và figure nhỏ có quyền trong `docs/research/`, PROJECT_STATE; exports/artifacts lớn local ignored.
5. **Bàn giao:** luận văn/deck xuất được, code/config/fixture/manifest nhỏ truy vết, hướng dẫn tái lập, bằng chứng nghiệm thu/bảo vệ khi xảy ra; một Draft PR.
6. **Kiểm/bằng chứng:** trace mọi số tới M4/M7 và mọi ngoại lệ tới quyết định; link/source/visual QA; fresh reproduction phần được quyền hoặc ghi rõ phần chưa chạy/lý do; review quyền chia sẻ, không commit dữ liệu/raw/checkpoint.
7. **DONE/PASS:** tài liệu/code artifact hoàn chỉnh; GitHub merge được xác minh; **M8 chỉ DONE khi nghiệm thu/bảo vệ thực tế được xác nhận**. Nhánh scope giảm phải ghi “xác nhận độc lập chưa hoàn thành”, không đổi M6/M7 thành PASS.
8. **Ngoài scope:** triển khai an toàn thật, hứa bài báo được nhận, làm thí nghiệm để che thất bại thiết kế, tự nâng claim thuật toán/causal/generalization.
9. **Mở tiếp:** kết thúc lộ trình được giao; công bố/deployment chỉ với task/quyền mới, không tự mở PR.
10. **Gom việc:** report/deck/QA/reproducibility/state nằm cùng sản phẩm cuối; chờ bảo vệ ghi pending, không PR phụ thường kỳ.

## 6. Tự kiểm độ tinh gọn và quy tắc tiếp nối

| Câu hỏi tự kiểm | Xử lý trong bản cuối |
| --- | --- |
| Có giấy tờ không phục vụ bước thực tế? | M1 là quyết định mở M2, M2 là contract thực thi M3, M6-01 là quyền mở thu nhận/pilot; không task khảo sát thêm/brief M1/kế hoạch setup lần hai. |
| Có chia nhỏ cùng chức năng? | M3 gộp reader/metrics/CLI/config/tests/docs; M4 gộp mọi bảng/model; M7-01 gộp baseline/ablation; sửa lỗi và state trong cùng PR. |
| Có việc bắt đầu trước authority? | M1 pending; mỗi card có precondition và quyền artifact/GPU/target riêng. Pilot M6-02 phải review/khóa code trước run; không chờ M7 mới có runner rồi mắc vòng phụ thuộc. |
| Có audit trùng lặp? | Kế thừa post-merge #130/#131/#133 đúng phạm vi; chỉ xác minh HEAD/diff/input cần thiết, không tái audit raw cho bảng saved-score. |
| Có module/dependency thừa? | M3 dùng cấu trúc hiện hữu, hai module và một CLI cho chức năng thật; model/capture/triage chỉ tạo lúc M6/M7 có quyền/cần dùng. |
| Có gate không có tiêu chí khách quan? | M1 A1–A8; M2 R1–R5/C01–C10; M3 test/CLI; M4 receipt/results; M5/M8 xác nhận học phần; M6 precision/rights/source; M7 freeze/contrast/protocol. Các giá trị chưa biết do M6 pilot + Lead quyết, phải khóa trước target. |
| Có bỏ HNLO/Moondream2/đánh giá độc lập? | HNLO giữ cả hai học kỳ; Moondream2 hàng N/A có ngoại lệ riêng; M6 NO-GO chặn xác nhận, không đổi TRAIN thành holdout. |

Mở một chat/task mới: đọc PROJECT_STATE rồi AGENTS/README/ROADMAP và nguồn đúng task; đối chiếu main, PR active, merge commit và biên bản GitHub thực tế. Nếu state khác GitHub, ghi trạng thái đã kiểm chứng trong PR của task đang làm; không làm PR riêng để đồng bộ thường kỳ. Biên bản hoàn tất GitHub là bằng chứng có thẩm quyền về merge/audit; quyết định của Lead mới có thẩm quyền khoa học.

**NEXT TASK duy nhất sau bàn giao/review kế hoạch: M1-01.** Đầu vào và hồ sơ sẵn ở §2; xin quyết định chính thức rồi ghi append-only, không giao setup M3 trước M1/M2. Trong task này chỉ tạo EXECUTION_PLAN và PROJECT_STATE, kiểm diff/link/nhất quán và dừng ở đúng một Draft PR để ChatGPT kiểm tra trực tiếp GitHub.
