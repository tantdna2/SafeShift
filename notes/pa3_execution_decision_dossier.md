# PA3 — Hồ sơ quyết định thực nghiệm (TASK 3A)

Ngày 2026-10-11 (Asia/Bangkok). **PENDING Research Lead decision**.
BASE_SHA: `1790c63a22ee2a641b4b2c82bd100cde5f0b1c9a`, xác minh bằng
`git ls-remote origin refs/heads/main` trước khi làm việc.
GitHub xác nhận [PR #90](https://github.com/tantdna2/SafeShift/pull/90),
[PR #91](https://github.com/tantdna2/SafeShift/pull/91) và
[PR #92](https://github.com/tantdna2/SafeShift/pull/92) đã merge; dòng DRAFT trong
log/runbook cũ là lịch sử, không phải trạng thái PR hiện tại. Merge không cấp
quyền LS1/PA3 dùng dữ liệu thật.

**Khuyến nghị: CONDITIONAL GO cho PR chuẩn bị mã với dữ liệu tổng hợp;
NO-GO cho suy luận TRAIN hiện tại.** Research Lead cần quyết định riêng về
kiểm kê metadata, protocol/cohort và quyền từng lần chạy. Hồ sơ này không phê
duyệt thay Research Lead, không sửa lock hay tạo receipt tự mở khóa.

## 1. Phạm vi và bảng điều kiện

Phương án đề nghị giữ nguyên từ [proposal](pa3_research_protocol_proposal.md):
chỉ Qwen2.5-VL-3B-Instruct, raw label logits chưa hiệu chỉnh; không fine-tuning,
LoRA, calibration, threshold selection hoặc Level01 guard. Primary là
score-conditional AUROC Anomaly (Level01/02/03) so với Normal (Level04), với
`s = logsumexp(z1,z2,z3) - z4`, điểm cao nghiêng về Anomaly. TRAIN-dev/holdout là
overlay có bảo vệ nhóm, không đổi official split. TEST khóa; PA3 bổ sung Seminar,
không thay RQ3 hoặc dùng quyền P2/P2.1. Chưa có kết quả khoa học PA3.

PASS dưới đây chỉ có phạm vi ghi trong cột bằng chứng; không phải all-gate PASS.

| Điều kiện | Trạng thái và bằng chứng tại BASE | Rủi ro / việc còn phải quyết định |
| --- | --- | --- |
| Nguồn và trạng thái PR | **PASS kiểm tra trực tiếp**: remote main đúng SHA; API GitHub báo cả ba PR merged | Không dùng checklist DRAFT cũ làm blocker merge |
| Primitive raw scoring/AUROC | **PASS kiểm tra tĩnh**: `core.candidates/locate_decision/score_decision/distribution`; `evaluate.anomaly_log_odds/auc` | Có primitive không có nghĩa PA3 chạy được; prefix sinh tự do và parse-valid tạo selection bias |
| Chặn truy cập LS1 TRAIN/TEST | **PASS kiểm tra tĩnh**: `experiment.authorize` và `dataset_samples` luôn raise lock; launcher gọi `authorize` trước runtime | Đây là bằng chứng khóa hoạt động theo source, đồng thời **BLOCKED execution**; receipt/hash không phải quyền |
| CPU/synthetic LS1 lịch sử | **PASS có giới hạn, đã được ghi nhận**: 66 PASS / 2 SKIP của LS1; 19/19 diagnostics trong PR #91 | Không chạy lại ở TASK 3A. Focused regression lịch sử còn một FAIL allowlist D9R23; không gọi toàn suite xanh; hai SKIP không là T1 PASS |
| T1 Qwen thực tế | **BLOCKED**: runbook ghi thiếu pinned snapshot/matching libraries; không có artifact Qwen T1 PASS được kiểm chứng trong hồ sơ | T1 InternVL3 được báo cáo không thay thế T1 Qwen |
| Snapshot/runtime và qualification Qwen PA3 | **BLOCKED bằng chứng**: source có pin/validator, chưa kiểm chứng các input thật và raw-only runtime | Thành công P2 hoặc synthetic InternVL3 không chứng minh Qwen PA3 |
| Đường chạy chỉ raw | **BLOCKED kỹ thuật**: `experiment.run` gọi references/calibrate; `evaluate.report` và `audit.audit_run` đòi calibrated branch | Cần implementation riêng, giữ LS1 cũ và các khóa |
| GT, exposure, duplicate graph, cohort | **BLOCKED**: chưa kiểm kê được phép, chưa có ledger/group manifest đã audit | Không biết số nhóm đủ điều kiện; không giả định holdout độc lập |
| Protocol/authority | **BLOCKED quyết định**: DEC-LS1-001 PENDING (audit correction có hiệu lực); DEC-LS1-002 PROPOSED/PENDING; PA3 chưa frozen | Research Lead giải quyết phạm vi PA3 và exact rights; D9R22 không cấp thêm inference cho RQ3 |

Nguồn: [DECISIONS — D9R22, DEC-LS1-001/002](../DECISIONS.md),
[runbook](ls1_runbook.md), [failure analysis và validation lịch sử](ls1_calibration_failure_analysis.md),
[experiment](../safeshift/ls1/experiment.py), [core](../safeshift/ls1/core.py),
[evaluate](../safeshift/ls1/evaluate.py), [audit](../safeshift/ls1/audit.py),
[launcher](../safeshift/ls1/kaggle.py). Các nhận định source áp dụng đúng BASE trên.

## 2. Gói bằng chứng kỹ thuật trước suy luận TRAIN

| Gói cần có | Nội dung tối thiểu và tiêu chí chấp nhận |
| --- | --- |
| Qwen T1 offline, không weights | Artifact từ `tokenizer.t1` cho revision `66285546d2b821cf421d4f5eb2576359d3770cd3`: tokenizer/config/template inventory đúng size/hash, runtime-plan hash, class/vocab/token IDs, bare labels và đủ 28 cases; status PASS. Transformers 4.51.3, tokenizers 0.21.1, huggingface-hub 0.30.2. Thiếu file/library hoặc sai version = BLOCKED; hash/tokenization sai = FAIL. Fake tokenizer/SKIP không thay thế |
| Mapping trên response thực tế | Mỗi response parse-valid có cùng prefix/suffix giữa bốn variants, một vị trí phân nhánh, bốn ID khác nhau, decode round-trip, alignment continuation (tối đa một EOS cuối), generated label token đúng step. T1 không bảo đảm mọi response; sai thì dừng, không approximate/rescue INVALID |
| Full model snapshot | Kiểm toàn bộ `snapshot_files` theo pinned runtime plan, gồm weights, processor, config, tokenizer; directory revision đúng, size/hash từng file và SHA-256 inventory; loading keys không missing/unexpected/mismatched/error. T1 chỉ chứng minh tokenizer subset, không chứng minh weights |
| Runtime và source | Owner lưu source commit/archive hash được review độc lập; inventory hash Runtime Prep đáng tin, kiểm executable bytes trước chạy probe; exact Linux x86_64/Python 3.11.11, mọi package pin trong plan, T4 CC7.5/CUDA12.4; Internet OFF và không download/install/fallback. Checksum chứng minh tính nhất quán, không chứng minh quyền thực thi |
| Qualification raw-only | Sau review/audit và quyền technical tương ứng, owner chạy synthetic Qwen trên đúng code raw-only đã review: FP16/NONE, SDPA, batch 1, cuda:0, C1/native processor, pixel bounds 200704–1003520, 256–1280 visual tokens, greedy 32-token cap, fresh cache/rope. Lưu trace raw/processed từng bước; processed global argmax khớp generated token, mọi invariant/nonfinite checks PASS; CPU audit tái tính raw scores từ artifact đã seal. Có mẫu thực sự score được; toàn INVALID không đủ chứng minh extraction. Không reference/calibration calls |

Đối chiếu [tokenizer](../safeshift/ls1/tokenizer.py),
[runtime](../safeshift/ls1/runtime.py),
[Qwen runtime plan](../configs/pre_freeze/qwen2_5_t4_runtime.v1.json) và runbook.
Phiên bản còn lại phải khớp toàn bộ `software` trong plan, không chỉ ba thư viện
T1. Lưu raw text, input/continuation IDs, mapping/prefix/step, candidate raw và
processed values, full-vocab summaries, generation config/overrides, sample/run
ID, prompt/model/source identity, failure evidence và checksum inventory trước
parse/tổng hợp. Không cần lưu mọi full-vocabulary tensor, nhưng không được chỉ
lưu nhãn/điểm cuối. Raw-only là cách tính endpoint; vẫn giữ processed traces để audit.

## 3. Các thay đổi kỹ thuật còn thiếu (chỉ đề nghị cho PR sau)

1. **Orchestration/version riêng:** tái dùng primitive LS1 nhưng bỏ hẳn
   `reference_scores`, reference cache, `calibrate` và guard khỏi PA3. Không chỉ
   giấu cột calibrated sau khi đã chạy references. Pin Qwen-only/method/source;
   giữ LS1 v1 và lock hiện tại, không gọi helper trực tiếp để vòng khóa.
2. **Artifact và CPU audit raw-only:** version schema/manifest/results, kiểm
   nguyên vẹn raw-before-parse/reread/seal và tái tính mà không đòi `reference_key`
   hay calibrated branch. `audit_run` hiện luôn đọc references và calibrate nên
   chưa dùng được nguyên trạng. Không giả tạo calibrated=uncalibrated để vượt schema.
3. **Evaluator PA3 riêng:** dùng `auc/anomaly_log_odds`, exact unique GT join,
   tie=0,5, single-class=NA, không đảo dấu; loại missing scores minh bạch. Bổ sung
   flow planned/attempted/persisted/parsed/scored, denominator pairs, coverage
   theo lớp/domain/prefix, completed-run gate, controls, grouped CI và sensitivity
   theo phụ lục được duyệt. `report` hiện đòi hai modes, chưa cung cấp gói PA3 này.
4. **Cohort và thực thi được review riêng:** loader overlay TRAIN có kiểm membership,
   provenance, group/exclusion integrity và dev/holdout isolation; GT holdout chỉ
   join sau seal. Cần launcher/notebook/runbook cho raw-only cùng exact run IDs,
   stop/failure/no overwrite/no implicit retry. Đây không phải chỉnh một CLI flag
   là có quyền mở TRAIN; PR chuẩn bị phải từ chối dữ liệu thật trước mọi read.
5. **Kiểm thử cho implementation sau:** synthetic fixtures cho không gọi references,
   INVALID/alignment/nonfinite, ties/constant scores/NA, missing GT/duplicate IDs,
   checksum/recomputation, partial runs, nhóm bắc cầu/mixed strata, dev–holdout leak;
   fail-on-access kiểm mọi entrypoint vẫn khóa TRAIN/TEST. Sau đó mới qualification.

Không khôi phục được bốn logits từ nhãn/text/histogram P2. Tái dùng artifact cũ
chỉ được cân nhắc nếu có quyền riêng và audit chứng minh đủ trace/provenance;
hồ sơ này không mở archive hoặc coi P2 là nguồn logits đã sẵn sàng.

## 4. Kiểm kê metadata, exposure và bảo vệ nhóm

**Quyền metadata khác quyền ảnh và quyền inference.** TASK 3A không cấp bất kỳ
quyền nào trong ba loại đó. Bước sau cần Research Lead chỉ định custodian, nguồn,
trường và thao tác được phép; có thể kiểm kê metadata không cần model/GPU và
không thay LS1 lock. Metadata đọc được không tự cho phép suy luận.

| Công việc tương lai | Cách xác minh và ranh giới quyền |
| --- | --- |
| Provenance/GT | Custodian đối chiếu manifest W1/fingerprint/version/hash đã duyệt; unique IDs, official split, authoritative GT, folder_domain/mismatch semantics, locator tương đối và nguồn `point_id`/sequence/scene. Báo thiếu/xung đột; không suy GT từ tên file, không sửa nhãn. Chốt cả GT/hash của 10 ảnh exploratory |
| Exposure ledger | Ghi IDs/nhóm, người xem, thời điểm/mục đích, ảnh/GT/output đã xem và mức aggregate hay per-sample, model/protocol/run/artifact provenance; gồm 10 ảnh, audit/error analysis, P2 toàn 5.013 ảnh và TEST đã được báo cáo. Phân biệt model đã chạy với analyst đã xem; không rõ thì unknown/quarantine, không coi thiếu log là chưa exposure |
| Exact/near duplicates | So sánh hash đã có trong metadata được duyệt, xác nhận phạm vi hash (file bytes hay pixels) và độ phủ. Hash file trùng chứng minh trùng byte; hash khác không loại ảnh re-encode/crop/gần trùng. Tính hash mới, decode pixels, perceptual similarity hoặc visual review đều đọc ảnh thật, cần quyền riêng; không núp dưới tên metadata audit. Nếu chưa được phép thì ghi unresolved và không chứng nhận independence |
| Graph bảo vệ | Nối Normal cùng point_id, exact duplicates và quan hệ sequence/scene đã có evidence; lấy connected components kể cả bắc cầu, không mặc định Anomaly độc lập. Near-duplicate/source-family là candidate links cần rule adjudication đã duyệt; edge nguồn/lý do/độ chắc chắn truy vết được. Thiếu point_id/quan hệ mơ hồ phải xử lý bảo thủ, không tự biến thành singleton độc lập |
| TEST và quarantine | Quarantine cả component chứa per-sample exposure/unknown hoặc liên hệ đã biết với TEST đã quan sát; dùng ledger/quan hệ lịch sử được phép, không đọc TEST mới. Aggregate exposure phải disclosure và có quyết định về mức claim; mọi quan hệ không xác minh được là limitation/blocker, không chứng nhận sạch. Nếu cần kiểm tra TEST mới, dừng và đưa blocker về Research Lead |
| Overlay và blinding | Sau phê duyệt quy tắc, custodian lập group IDs, edge/exclusion log và role manifest có hash; thống kê ảnh/nhóm theo domain, binary class, level và mixed strata, kiểm overlap dev–holdout/excluded. Giữ official split; không dùng scores để phân nhóm/chọn salt. Custodian được xem metadata cần thiết; analyst không nhận GT/output holdout trong dev. Artifact dẫn xuất ở `data/processed/`, không commit dữ liệu thật |

P2 đã chạy toàn pool và aggregate đã thúc đẩy PA3: phân hoạch mới không xóa
retrospective motivation, kể cả nếu chưa xem LS1 scores. Không mặc định TRAIN-holdout
độc lập. Nếu không chứng minh được nhóm/exposure hoặc không còn đủ nhóm phù hợp,
không có confirmatory GO; chỉ đề xuất exploratory với disclosure, hoặc cohort mới
được duyệt riêng. Không tự thu thêm dữ liệu hay chuyển ảnh giữa split.

## 5. Mức sẵn sàng đóng băng và quyết định còn mở

**Chưa đủ để freeze toàn protocol.** Công thức/chiều score, GT binary mapping,
eligibility parse-valid, ties/NA, INVALID không được cứu, một model/raw-only,
TEST locked và vị trí bổ sung ngoài RQ3 đã đủ rõ để Research Lead duyệt về nguyên
tắc. Độ rõ của mô tả không đồng nghĩa đã phê duyệt. Các mục chưa thể tự chốt:

| Quyết định cần Research Lead chốt trước thực thi liên quan | Chi tiết còn PENDING |
| --- | --- |
| Scope và quyền | Giải quyết DEC-LS1-001/002 cho PA3 raw-only; đồng ý hay bác đề xuất ngưng calibrated decision rule; scope/inference bổ sung ngoài RQ3 theo D9R22, applicability overlay D2/D5/D9R24; owner, quyền metadata/ảnh/technical/dev/holdout tách riêng. Không kéo threshold/matched-null successors vào PA3; học threshold/calibration về sau cần ngoại lệ D9R22 riêng |
| Exposure/grouping | Rule aggregate vs per-sample exposure, unknown/quarantine và mức claim; nguồn dependency, exact/near-duplicate adjudication, unresolved edges, cross-TEST boundaries; graph đủ tin cậy hay chỉ exploratory. Chưa biết actual eligible counts |
| Allocation | Duyệt hoặc thay trước scores: 50/50 nhóm; salt `pa3-proposal-v1-2026-10-11`; hash/order/floor theo strata domain × binary, mixed-label/mixed-domain và singleton quarantine. Cần canonical serialization group_id từ sorted IDs, delimiter/encoding và hash-tie rule, exclusion manifest và actual image/group counts; không thử nhiều phân hoạch để chọn đẹp |
| Uncertainty/feasibility | Phụ lục PA3 resample whole protected components, domain strata/mixed-domain giữ nguyên; percentile 95%, B=2000, seed 42, shared draws. Không gọi đây là D9R24 nguyên bản. Chốt cách áp dụng tối thiểu 20 nhóm mỗi binary class, ≥95% draws hợp lệ, width ≤0,20; power/precision assumptions và kế hoạch mô phỏng trước scores, không coi ngưỡng đề xuất là power đã chứng minh |
| Missingness/decision rules | Duyệt coverage ≥95% từng binary class; completed run/audit/GT gates; lower CI >0,5 hỗ trợ H1, upper ≤0,5 không hỗ trợ đúng chiều, còn lại inconclusive. Chốt mốc thực tiễn 0,55 và vai trò completion bounds; không gọi bounds là CI/full-cohort measured AUROC. Đây là ngưỡng diễn giải thống kê, không phải threshold phân loại |
| Reports và lifecycle | Chốt controls/secondary của proposal (within-domain, leave-one-group-out, generated-Level03, OVR/pairwise, supports/coverage; Level03 luôn exploratory), không dùng để cứu primary; exact source/prompt/model/method/cohort hashes, run IDs/budget, failure/attempt policy, custodian/analyst access và một lần mở holdout. Dev chỉ kiểm kỹ thuật, không chọn phương pháp. Sửa phương pháp cần version/decision mới trước holdout |

## 6. Thứ tự PR, quyền thực thi và điểm dừng

Các PR dưới đây là **đề nghị**, không phải quyền được cấp bởi TASK 3A. Có thể
chuẩn bị mã tổng hợp sau quyết định phạm vi ban đầu; quyền dữ liệu vẫn xét riêng.

| Thứ tự | PR / hoạt động và bằng chứng đầu ra | Quyền tối đa đề nghị |
| --- | --- | --- |
| 0 — TASK 3A này | Draft hồ sơ + TASKS PENDING → ChatGPT kiểm GitHub trực tiếp | Tài liệu/kiểm tra tĩnh; dừng, không merge |
| 1 — Quyết định phạm vi/kiểm kê | Research Lead quyết định raw-only, scope bổ sung, các rule kiểm kê/grouping/exposure và custodian; ghi decision theo quy trình repo trong PR riêng | Chuẩn bị CPU/synthetic; metadata audit chỉ theo nguồn/trường được duyệt. Chưa inference TRAIN/TEST; ảnh cần quyền riêng |
| 2 — Chuẩn bị implementation vẫn khóa | PR PA3 raw-only schema/scorer/audit/evaluator/cohort tooling, synthetic tests và runbook; ChatGPT review → independent audit → reconciliation và merge chỉ theo quy trình được duyệt | Không dữ liệu thật/GPU trong PR code. Owner T1 offline và qualification synthetic Qwen sau review, theo quyền technical tương ứng; lưu gói mục 2 |
| 3 — Cohort/protocol freeze | Custodian kiểm kê đúng quyền PR 1, giải quyết duplicate/exposure blockers; PR tóm tắt evidence và quyết định Research Lead chốt graph/exclusions/counts/allocation/CI/gates/blinding. Manifest chi tiết ngoài Git nếu chứa dữ liệu thật | Metadata/ảnh đúng phạm vi được cấp; chưa inference TRAIN. Không freeze một holdout “độc lập” chỉ vì có hash |
| 4 — Quyền và implementation TRAIN-dev riêng | Sau PR 2–3 và qualification PASS: Research Lead duyệt exact dev cohort/model/source/method/run/owner; PR thực thi hẹp được review/audit, xác minh commit được duyệt trước chạy | Chỉ owner chạy dev đã duyệt; TEST và holdout chưa được mở. Giữ LS1 v1 khóa; không receipt/checksum tự cấp quyền, không monkeypatch/helper bypass |
| 5 — Holdout một lần | Seal/audit dev; Research Lead xác nhận phương pháp không bị chọn/tune từ dev, freeze cuối source/protocol và cấp exact holdout rights trong decision/PR riêng; nếu code đổi phải review/qualification lại phù hợp | Owner chấm holdout đã khóa một lần, raw seal trước GT join; chỉ báo cáo sau CPU audit. Failure không tự cho retry; TEST tiếp tục khóa |

Trước mở TRAIN-dev phải có quyết định có hiệu lực, implementation đã review/audit,
T1 + full snapshot/runtime + raw-only qualification PASS, GT/exposure/grouping
và cohort/protocol được duyệt, quyền owner/run cụ thể và artifact plan.
Trước mở holdout cần thêm dev audit, xác nhận blinding/exposure còn đúng, final
freeze và quyền holdout riêng. PASS kỹ thuật không đủ để cấp quyền dữ liệu.

Khuyến nghị cuối để Research Lead xem xét: **GO cho review hồ sơ;
CONDITIONAL GO cho chuẩn bị implementation; NO-GO cho TRAIN hiện tại và TEST**.
Nếu blockers về độc lập/precision không giải quyết được, không nâng exploratory
thành xác nhận và không suy kết luận về discrimination, accuracy hay safety.

## 7. Kiểm tra TASK 3A

Chỉ đối chiếu tài liệu/source và metadata GitHub; kiểm UTF-8, relative links,
`git diff --check`, staged allowlist đúng hai file và bảo toàn byte prefix TASKS.
Kết quả thực tế, BASE/HEAD và URL Draft PR ghi trong bàn giao PR.
Không chạy test suite, tokenizer/evaluator/pipeline, GPU, model load, hay đọc
metadata/ảnh TRAIN/TEST/archives thật vì task chỉ chuẩn bị quyết định. Không sửa
DECISIONS, mã chạy, frozen contracts, lock hoặc lịch sử. Dừng cho ChatGPT review.
