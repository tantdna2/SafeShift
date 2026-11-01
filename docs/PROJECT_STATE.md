# SafeShift — PROJECT STATE

## Issue #163 — HNLO Method A, CPU synthetic engineering

[Owner authorization](https://github.com/tantdna2/SafeShift/issues/163#issuecomment-6555995581)
cho triển khai đường proof/evaluation riêng từ BASE/main
`c2fb0fadef0cfc855c3f164ed1f662e9de623d58`, trong một Draft PR mới.
**CPU synthetic engineering COMPLETE FOR DRAFT REVIEW; real MiniCPM qualification UNVERIFIED.**
Không thay trạng thái O2/O3/O4/O5/L1–L4; MiniCPM giữ peer label-only.
Các mục T4/T3/T2 bên dưới là snapshot lịch sử, không được nâng trạng thái.

- [API và hợp đồng](HNLO_METHOD_A.md): builder giữ actual token IDs, thử một
  token tại từng bước trên toàn vocabulary đã seal; verifier độc lập dựng lại
  divergence, kiểm exact actual path, context/EOS và tính duy nhất. Không thay
  4788 bằng10354, không dùng sparse logit keys làm toàn bộ miền tìm token.
- Chỉ lấy bốn raw logits cùng bước đã chứng minh. Gọi nguyên `hnlo/oracle`
  cũ với tolerance1e-10; mọi thiếu/mâu thuẫn/mơ hồ trả null có lý do. Không sửa
  parser, generation, production capture/replay, notebook, T2/T3 hay metric.
- API in-memory/stdlib, scope CPU_SYNTHETIC_ONLY, decoder/seal được inject.
  Seal phải đến từ nguồn độc lập; checksum do caller tự tạo và hai callable
  khác tên không chứng minh custody/decoder independence. Chưa có bridge đọc
  archive thật hoặc kiểm runtime tokenizer MiniCPM; xem hợp đồng trust boundary.
- Source runtime `c3c223bc69edd253d57bbba9344e0633b65b3de4` so với BASE: ba
  file `pilot/hnlo.py`, `candidates/backend.py`, `candidates/train_run.py` giống
  bytes. Release/T4 identities chỉ được đối chiếu từ tài liệu Git đã tracked.

Windows CPython3.11.9, `Windows-10-10.0.26200-SP0`, không dependency mới:
**34 Method A +8 HNLO cũ +71 T2/T3 =113 PASS,0 FAIL**.
Native candidate discovery: **15 SKIP** vì thiếu opt-in public snapshot/stack;
không gọi đó là native tokenizer PASS. Các lệnh tái lập ở HNLO_METHOD_A.
Full Windows không chạy lại trong task này; giới hạn INCOMPLETE/MAX_PATH lịch
sử ở T3 bên dưới giữ nguyên, không tuyên bố đã khắc phục.

Log/receipt tổng hợp local ignored: `data/processed/hnlo-method-a/`.
Windows log SHA256 `21c210c408d8b2757f4ba7531608d0cf1f2bd89768aa77d28fc10833c7fc188e`.
Source module SHA256 `4662d31c6d8a6de56240be8de7b366925a64d259bde1fd755a4145b35394bd9c`;
test SHA256 `07747a6a903719dacede49212e114a633b77872b04768d9cc651438d0faa3e75`.
Seed arithmetic163; fixture token/logit hoàn toàn viết tay.

Linux WSL2 x86_64/glibc2.43, CPython3.14.4, stdlib:
full `python3 -B -m unittest discover -s tests -v` **486 tests =446 PASS,
40 SKIP,0 FAIL/ERROR**,428,689s. Lượt này dùng snapshot trước hai chốt cuối
(native/EOS IDs phải integer và từ chối generation fields lạ): module SHA256
`1d6fa326c9d63a593a2b2be22bb628f39b930706df235bd12ff26df1a66369ef`,
tests `9bfeab014ebcecce3a8ad061a4056e0dbd7eac02c32133e1a1208712dc1d471b`.
Full log SHA256 `a42f01538227406752780667fda95d53e966ad5c4eb12620d8498aa12340caf8`.
Đây không phải claim full-suite trên final bytes.

Final bytes đúng hai hash mới ở trên đã kiểm lại trên Linux: **113/113 PASS**,
1,979s, gồm34 Method A +8 HNLO +71 T2/T3; Windows final113 cũng PASS.
Lệnh Linux: `PYTHONPATH=tests python3 -B -m unittest test_hnlo_method_a
test_pilot.HNLOTests test_triage test_triage_adapter -v`.
Final Linux log SHA256 `8632dbaae9c13eccbb18caa8b5d2bc98fba1c4ef8acc7244bb093c9e9beaa4e9`.
Mỗi checkout Linux lấy BASE và overlay đúng hai file mới, kiểm SHA trước chạy;
không copy dữ liệu local hay cài dependency. Full regression không lặp lại
sau hai chốt validation riêng đã có tests âm tính; native opt-in vẫn SKIP.

Không đọc private raw/logits/tokenizer/ảnh/GT/TEST, không Kaggle/GPU/inference/
weights. Giữ nguyên160 kết quả; khả năng tính HNLO cho155 SUCCESS vẫn
**UNVERIFIED**, không suy coverage từ tests tổng hợp. Việc kiểm dữ liệu lưu
thật cần quyền riêng và custody/artifact đúng danh tính trong tài liệu.

**NEXT:** dừng ở một Draft PR để ChatGPT kiểm GitHub trực tiếp; bắt buộc audit
độc lập trước hợp nhất. Không tự merge, gọi Antigravity hoặc backfill scores.

## T4 — hồ sơ lựa chọn kết quả O2, 01/11/2026

**T4 dossier COMPLETE FOR REVIEW; selection PROPOSED; phân tích thật BLOCKED.**
BASE/main kiểm trực tiếp GitHub `f10bac7dea054c8e199a807dadd768517579e164`,
T3 đã merge theo [Owner START T4](https://github.com/tantdna2/SafeShift/pull/161#issuecomment-6554558701).
Task/nhánh T4 mới, không tiếp tục triển khai T3. Các mục dưới là snapshot lịch sử.

[Hồ sơ T4-O2-SELECTION-v1](research/T4_O2_SELECTION_DOSSIER_20261101.md)
khuyến nghị khóa bốn Qwen3 V4 ORIGINAL và đúng official attempt mỗi peer trước
phân tích ghép đôi tiếp theo, giữ lỗi/missing và không pooling/thay thế.
InternVL3.5 official là **RECOVERY** được định danh, cần quyết định O2 chấp
nhận rõ; MiniCPM official FP32 là INITIAL, label-only, không numeric HNLO.
Không chọn theo latest/SUCCESS/metric hoặc gọi lựa chọn hồi cứu là chưa phơi nhiễm.

- Qwen3 giữ3763 planned/3539 SUCCESS/1 TECHNICAL_ERROR/223 NOT_ATTEMPTED;
  trên160 giữ148 SUCCESS/12 NOT_ATTEMPTED và4 false-safe/1 severe kế thừa T0.
- InternVL3.5 giữ135 SUCCESS/25 INVALID; MiniCPM giữ155/5. Không dùng toàn35
  lỗi Qwen làm support có hai peer hoặc suy peer đã phát hiện lỗi Qwen.
- [Receipt T4](research/evidence/t4_o2_metadata_20261101.json): **18 checker T1
  PASS +10 metadata cross-checks PASS,0 FAIL**; chỉ hashes/metadata, không
  archive/raw/per-image prediction recount. Full unit/native/GPU suite SKIP
  vì chỉ tài liệu/receipt; không thay T2/T3/code/tests/protocol.
- Blockers L1–L4: approval selection; Qwen legacy series/config representation;
  peer report/config/implementation binding và InternVL ancestor seals;
  paired ledger/access. UNKNOWN giữ nguyên, không tự đặt ID/hash/chữ ký.

**NEXT duy nhất:** Owner/người duyệt có thẩm quyền trả lời chấp thuận có điều
kiện hoặc từ chối quy tắc và exact sources tại T4 §8 sau ChatGPT review trực
tiếp một Draft PR. Hồ sơ đủ để quyết định, không phải O2 đã đóng hay GO chạy
phân tích; O3 final roster, O4/B1–B4, O5/B5–B6 và học vụ còn riêng. Không TEST,
ảnh/saved predictions/raw, Kaggle/GPU/inference, ranker hoặc hiệu quả mới.
Không merge, không gọi Antigravity; các quyền vận hành cũ không cấp selection.

## T3 — synthetic provenance adapter, 01/11/2026

**T3 CPU engineering COMPLETE / READY FOR DRAFT REVIEW; real-data activation
UNAVAILABLE.** Linux full-suite PASS với SKIP; full Windows INCOMPLETE.
BASE/main đã kiểm GitHub `7026c6fe687bada36a824b36dc1997e7ff844ae7`,
[PR160 MERGED](https://github.com/tantdna2/SafeShift/pull/160).
[Owner START T3](https://github.com/tantdna2/SafeShift/pull/160#issuecomment-6553995227)
cấp task code CPU synthetic, không mở science/real-data authority. Phần T2/T1
bên dưới là snapshot trước merge tương ứng; mục này cập nhật phạm vi hiện hành.

- `safeshift/evaluation/triage_adapter.py` xác minh manifest, opaque planned
  cohort, identity bảy trường từng model, report/row/input SHA256 và ledger
  lựa chọn đúng source/run/series/attempt; không tự chọn/pool kết quả.
- HNLO focal VALID cần evidence fixture gắn đúng identity/sample/input/value;
  peer HNLO bị từ chối. INVALID/TECHNICAL_ERROR/NOT_ATTEMPTED giữ nhãn null;
  thiếu rows giữ MISSING qua T2, thiếu source/selection bắt buộc thì dừng.
- Chỉ chín fixture tổng hợp có seal cố định trong source; không có file reader,
  real-data switch hoặc quyền từ JSON `approved`. T2 không đổi; adapter trả
  nguyên `ModelResults`/`ClassifiedResult` cùng immutable provenance receipt.
- [Hướng dẫn/API/checksum contract](TRIAGE_ADAPTER.md), demo CPU adapter→T2,
  33 tests mới với oracle độc lập, negative cases, no-I/O, immutable inputs,
  permutations và GT exclusion. Không dependency mới.

Windows AMD64 `Windows-10-10.0.26200-SP0`, CPython **3.11.9**:
`python -B -m unittest discover -s tests -p "test_triage*.py" -v`
→ **71 PASS (38 T2 +33 T3), 0 FAIL, 0 ERROR, 0 SKIP**, 2,903s.
`python -B -m unittest discover -s tests -v` trên Linux/WSL x86_64,
CPython **3.14.4**, kernel6.18.33.2/glibc2.43: **454 tests =414 PASS,
0 FAIL, 0 ERROR, 40 SKIP**, 563,093s. Checkout local đúng source commit
`68e8396f54a19967a5f84eb22701fa68b3cc6669`, có Git history cho `git show` và
thư mục `data/processed/` rỗng để tests tạo scratch. Không copy dữ liệu local.
Các commit sau chỉ cập nhật tài liệu; SHA256 adapter/demo/tests được đối chiếu
với source cuối, không thay code để vượt test.

SKIP: Torch CPU3, opt-in candidate stack/snapshot15, pinned worker/bundle1,
MiniCPM native4, Phi native6, Smol native9, real-network pip1, Windows junction1.
Không bật opt-in/tải dependencies/model. Đây là CPU engineering, không audit
độc lập, GPU/model-fit hoặc scientific qualification.

Full Windows đã chạy đúng lệnh nhưng dừng sau2057,625s tại
`test_oom_then_resume_then_noop_and_explicit_full_rerun_both_models`:
81 methods PASS,4 SKIP,1 đang chạy khi dừng; chưa đến phần còn lại.
**INCOMPLETE, không full Windows PASS.** Chưa quan sát FAIL/ERROR trong phần
đã kết thúc;8 subtest FAIL/MAX_PATH của PR160 là thông tin được cung cấp,
không tái hiện hoặc kết luận đã sửa ở lượt này. Code/tests recovery giữ nguyên.
Không suy lỗi mới T3 từ báo cáo lịch sử, không che giới hạn Windows.

Lưu cả lỗi chuẩn bị môi trường: lượt WSL archive thiếu Git history dừng sau
hai notebook ERROR (126,688s, không full-suite result); lượt checkout đầu có
413 PASS/1 ERROR/40 SKIP (498,640s), ERROR test Phi do thiếu `data/processed/`.
Tạo scratch rỗng rồi test Phi8/8 PASS (0,624s), full-suite cuối ở trên PASS.
Một lần tiếp tục checkout `/tmp` không còn bị chặn trước tests bởi hash check;
tạo checkout mới đúng commit, không thay source hoặc xóa log lỗi.

Demo CLI cuối `python -B -m scripts.demo_triage_adapter_cpu --budget 2
--tie-seed public-demo`: exit0/strict JSON PASS. Planned4/C3/M0/E3/K2,
HNLO-only review `[…01,…02]`, peer-only/combined `[…02,…01]`, backlog1.
Fixture hash `9fcdcf4a31e14be7ac259c7514c3a2cfc39e70cd9edd08c8f4ed1ffeed4e9b87`.
Không GT hoặc kết quả cải thiện thật. `git diff --check` PASS.

Source SHA256 (bytes, chung Windows/Linux):

| File | SHA256 |
| --- | --- |
| `safeshift/evaluation/triage_adapter.py` | `6fb368fc7713fe2a00160861bf4faab7f0ce37474e089ae30764c496744bcb7f` |
| `scripts/demo_triage_adapter_cpu.py` | `80846462261e472441e655ba28c89396a8180c1c3a3691bdbb21b260d12413ab` |
| `tests/test_triage_adapter.py` | `25cc8ffee8e1a9e41701a5c1d9bb80b843183c81c795f789a72190595bf5ade3` |

Full Linux log SHA256
`917c42131d486d6fa3d6162596db5d4e7442840e78d2e4eb41c8d35eb3499218`;
Windows partial log SHA256
`fab8a054160df23d593267cd280fc22bafc54170d5e3ad77d5fee391c7149f3b`.
Artifacts synthetic/log/receipt local ignored tại `data/processed/t3-synthetic-20261101/`;
không commit logs chứa đường dẫn máy hoặc dữ liệu riêng tư.

Giới hạn giữ nguyên: **O2 PENDING**, series-selection thực tế chưa duyệt;
**O4 PENDING/BLOCKED** về nguồn/quyền/custody V/T; **O5 PENDING** về budget,
gain/CI/precision/sample size. Không đọc TRAIN160/private reports/raw/ảnh/TEST,
không GPU/Kaggle/inference/model download/ranker/metric mới. Demo không chứng
minh cải thiện false-safe thật. Không thay M1/M2/T1 hoặc cấp quyền bên thứ ba.

**NEXT:** [Draft PR161](https://github.com/tantdna2/SafeShift/pull/161) duy nhất
để ChatGPT review GitHub trực tiếp. Chưa merge/audit độc lập; không yêu cầu
Antigravity audit/merge trong task T3.

## T2 — CPU synthetic triage, 01/11/2026

**T2 CPU engineering COMPLETE / READY FOR DRAFT REVIEW; khoa học chưa frozen.**
BASE/main xác minh `bf231c8d9c2c7fd9a46d1707095ac8e0177a34bb`,
[PR159 MERGED / T1 COMPLETE](https://github.com/tantdna2/SafeShift/pull/159).
[Owner T2](https://github.com/tantdna2/SafeShift/pull/159#issuecomment-6552925324)
cho triển khai phần mềm bằng fixture tổng hợp; thay NEXT TASK trong snapshot
T1 bên dưới cho phạm vi CPU engineering này, không tự duyệt khoa học.

- `safeshift/evaluation/triage.py`: planned opaque IDs, focal + tối đa hai peers,
  nhãn/status riêng, HNLO focal có eligibility tường minh; không sửa
  PredictionRecord, parser, HNLO, metrics hoặc protocol/config lịch sử.
- Ba mode không học HNLO-only/peer-only/combined; C/M/E/K theo phương án T0.
  Focal lỗi và feature bắt buộc thiếu vào M; mandatory + ranked dùng chung K,
  có backlog/OVERLOAD, coverage theo nguồn và lý do từng ca. Key bên ngoài,
  thứ tự độc lập input, GT không thuộc API xếp hạng.
- `compare_review_queues` trả operational M/E riêng và signal-control common
  M/E có cờ artificial workload; không chọn best baseline/fit weights. Demo
  chỉ dùng đáp án viết tay sau khi tạo queue, routing không là human detection
  hoặc correction. [API/contract và lệnh chạy](ARCHITECTURE.md#t2-cpu-synthetic-triage--01112026).
- Output luôn `SYNTHETIC_ONLY / PROPOSED_NOT_FROZEN /
  NOT_SCIENTIFICALLY_QUALIFIED`; không có kết quả cải thiện false-safe thật.

Validation hiện tại: Windows AMD64, CPython3.11.9, standard library; targeted
`python -B -m unittest discover -s tests -p test_triage.py -v`: **38 PASS,
0 FAIL/ERROR, 0 SKIP**. Demo CLI chạy bằng `python -S -B` với public seed
`public-demo`, K=0/1/3/99 và strict JSON PASS. K=3: planned6/C4/M2/E3,
slots3, backlog2; K=0/1 OVERLOAD, K=99 slots5/unused94. Đây là số fixture,
không kết quả nghiên cứu.

Full `python -B -m unittest discover -s tests -v` trên snapshot source cuối,
Linux/WSL CPython3.14.4: **421 tests = 381 PASS, 0 FAIL/ERROR, 40 SKIP**, 536,282s.
SKIP: Torch CPU3; opt-in candidate stack/snapshot15; pinned worker/bundle1;
MiniCPM native4; Phi native6; Smol native9; real-network pip1; Windows junction1.
Không bật opt-in hoặc tải dependency/model để đổi SKIP thành PASS. Source/test/
demo SHA256 snapshot được đối chiếu với file cuối; AST3, UTF-8 docs3,
`git diff --check` và strict JSON PASS. Lượt full-suite Windows ban đầu được
dừng để dùng lượt Linux source cuối, **không tính là full Windows PASS**;
38/38 T2 Windows là lượt targeted đã hoàn tất. Đây là kiểm tra của Codex,
không CI/independent audit, không model/GPU/scientific qualification.
Artifacts tổng hợp local ignored: `data/processed/t2-synthetic/`; fixture và
source được version control trong PR, không dataset/private output/secret.

**NEXT:** ChatGPT kiểm trực tiếp exact HEAD của một Draft PR và quyết định
audit/merge. Chưa audit độc lập hoặc merge. Dữ liệu thật TRAIN160 vẫn BLOCKED
đến O2 và series-selection; O4/O5, final roster/qualification, quyền nguồn/GT/
V/T và học vụ vẫn PENDING. Không đọc real TRAIN160/private saved reports/raw/
ảnh/TEST, không Kaggle/GPU/model download/inference, train hoặc pooling
Recovery224. T2 không tạo quyền khoa học hay yêu cầu thêm model thứ tư.

## T1 — kiểm quyền/nguồn và khả thi dữ liệu, 01/11/2026

**T1 assessment hoàn tất để review; thực nghiệm xác nhận BLOCKED.**
[Hồ sơ T1](research/THESIS_DATA_PROTOCOL.md) và
[receipt metadata](research/evidence/t1_feasibility_20261101.json) ghi nguồn,
quyền, exposure H/D/V/T, GO/BLOCKED/NO-GO, checklist custodian và quy trình
chốt budget/gain/severe/coverage/uncertainty/cost; chưa đặt giá trị được duyệt.

GitHub live xác nhận [PR158 MERGED](https://github.com/tantdna2/SafeShift/pull/158),
main `a113ef707970c50a7420c84e8a8e46fa2dc3db01`.
[Owner relay6552710543](https://github.com/tantdna2/SafeShift/pull/158#issuecomment-6552710543)
chấp nhận hướng false-safe/review, Q3 focal có điều kiện và hai peer ứng viên
InternVL3.5/MiniCPM resampler FP32, tạm dừng model thứ tư.
[Quyết định append-only](research/DECISIONS.md#dec-20261101-t1-owner-false-safe-direction)
chỉ ghi đúng phần này cùng E1–E5/T1 authorization; O2/O4/O5, phần còn lại
O1/O3, final qualification/roster và quyền/học vụ chưa được xác minh vẫn PENDING.

TRAIN/TRAIN160 đã phơi nhiễm: H và D thăm dò có điều kiện, không V/T độc lập.
T1 kiểm hash hai receipt/hai manifest160 và consistency số T0; không recount
archive/raw mới. Giữ Q3 V4 gốc 3763 planned/3539 SUCCESS/35 false-safe trên 2455
Normal; metadata160 148 SUCCESS/12 NOT_ATTEMPTED,4 false-safe/1 severe.
InternVL3.5 có 135 SUCCESS/25 INVALID; MiniCPM 155/5,0 HNLO số. Không pooling
Recovery224/composite, không metric/utility mới hoặc qualification tự động.

**GO:** kiểm hồ sơ, thăm dò saved TRAIN trong scope, chuẩn bị hợp đồng/CPU
synthetic. Phương pháp thật trên TRAIN160 còn O2/series/paired ledger;
learned ranker và xác nhận nguồn độc lập **BLOCKED**. Không có registry,
rights/custody V/T, nguồn/events/precision đủ bằng chứng. Giữ TEST đóng.

**NEXT TASK duy nhất:** hoàn thiện gói chứng từ nguồn/custody và quyết định
O2/O4/O5 theo checklist B1–B6 của T1, để kiểm hồ sơ được người có quyền cung
cấp; không mở T2 GPU/annotation/training/target. Dừng một Draft PR cho ChatGPT
review GitHub và quyết định audit, không merge. Các snapshot phía dưới giữ
nguyên; trạng thái T0 trước Owner relay không thay quyết định mới ở mục này.


## T0 false-safe — đề xuất trình giảng viên, 01/11/2026

**PROPOSED / O1–O5 PENDING; xác nhận thực nghiệm BLOCKED.**
[Thiết kế T0](research/T0_FALSE_SAFE_DESIGN_20261101.md) dựa trên báo cáo tư vấn
Owner đính kèm, đối chiếu main `89d886356c15064b5f1cc2021aa5d614e7e7f53f`.
Đề nghị chuyển primary của kế hoạch bốn peers/Macro-F1 sang phát hiện thêm
false-safe cùng ngân sách review; cần Owner/Research Lead quyết định và giảng
viên xác nhận CT1/chuẩn Khóa luận. Chưa áp dụng thay đổi khoa học.

Panel **ứng viên**, chưa final roster: Qwen3-VL-8B-Instruct focal có điều kiện,
InternVL3.5-4B-HF và MiniCPM-V-4 đúng resampler FP32 đã định danh làm peers.
Baseline/peer-only/combo HNLO hợp lệ, không học và learned optional được tách;
không mặc định ba model qualified hoặc MiniCPM có HNLO số. Giữ nguyên roster
Seminar, M1/M2/DECISIONS/protocol/config lịch sử. Không khóa review20%, gain10
điểm, CI95% hoặc giá trị thực nghiệm mới; có fallback trước target.

[Evidence/reproduction](research/T0_FALSE_SAFE_EVIDENCE_20261101.md) có recount
saved reports Q3 V4 gốc:3.763 planned =3.539 SUCCESS+1 error+223 not attempted;
35 false-safe/2.455 predicted Normal, gồm13 Level01/22 Level02, không recovery
pooling. Không raw audit mới. Chưa có verified source registry/V/T kín hoặc
precision/events đủ bằng chứng; H/TRAIN160 chỉ hồi cứu/thăm dò, TEST vẫn đóng.

**Cập nhật sự kiện #157, không hồi tố snapshot bên dưới:**
[GitHub hậu merge xác minh](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6546464187)
xác nhận PR157 MERGED, đúng main tham chiếu, đã audit/reconcile/merge được phép
và official TRAIN160 acquisition hoàn tất theo
[Owner đổi thứ tự run→audit→merge](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6545287909).
MiniCPM160:155 SUCCESS/5 INVALID/0 error/0 pending, HNLO số0/160; ZIP SHA256
`46a41359c3ab2978b9ee4ac010518e49a74141641d9334c29035bdc0c8eac877`.
InternVL160 theo receipt local:135 SUCCESS/25 INVALID, HNLO số135; không tự
nhận audit mới ở T0. Scientific selection/pooling, final thesis roster và
học vụ vẫn PENDING. Các đoạn NOT_RELEASED/NOT_RUN/chờ merge bên dưới là lịch
sử tiền sự kiện, không trạng thái hiện hành; giữ nguyên evidence/decision bytes.

Task này chỉ tài liệu/bằng chứng tổng hợp và kiểm tra CPU đọc báo cáo/metadata;
không code thuật toán, dataset/TEST/raw-logit replay, Kaggle/GPU, dữ liệu mới
hoặc UI. Dừng tại **một Draft PR** cho ChatGPT kiểm, không merge/tự duyệt.

## MiniCPM FP32 adoption implementation —31/10/2026

**READY_FOR_TECHNICAL_REVIEW / NOT_RELEASED.** Owner adopted the exact effective implementation
and authorized Codex to operate official original TRAIN160 after the new activation
PR is reviewed, independently audited, merged and verified by ChatGPT. Decision:
[Owner6544285481](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6544285481).
This supersedes the historical adoption BLOCKED status below; no separate Lead/
faculty signature is claimed. Scientific selection/pooling remains PENDING.

Activation pins effective config `5b85504f…`, descriptor `2fe99272…`, MiniCPM and
the original160 TRAIN manifest in trusted source policy. Numerical adapter bytes
remain unchanged; source/runtime have new source SHA256 `b1d6d821…`, runtime
`c3c223bc…` and final-source Kaggle verification. Direct workers also enforce
adoption/config/scope binding.
Default production notebook remains bounded engineering; no official run yet.

Local exact-export Linux suite:343 PASS/40 SKIP/0 FAIL/ERROR; native numerical8/8
PASS and both real pinned production CPU workers PASS. Final-source private
Kaggle `nguynanhtn/safeshift-minicpm4-adoption-qa-20261031/1` COMPLETE: one first
locked TRAIN image,1 load/1 call,11 finite logits steps, parser SUCCESS; HNLO
unaligned/null retained. ZIP SHA256/CRC/all74 members, raw/native tokenizer/
strict parser/HNLO replay and source inventory independently rechecked locally.
Technical only, no official history consumed. No queue cancellation/retry: first
check after Owner's conditional instruction observed RUNNING, then COMPLETE.

[Report and receipts](research/MINICPM4_FP32_OFFICIAL_ADOPTION_20261031.md) record
identities, retained errors, skips and private artifact locations. Stop at one
new Draft PR for ChatGPT exact-HEAD GitHub review and independent Antigravity
audit; PR156's waiver does not apply. Official160, real160 artifact verification
and actual complete-series no-call resume remain NOT_RUN. Synthetic INVALID160
ZIP/resume/no-load is locally verified; this is not a real160 completion claim.
No TEST or Accuracy/Macro-F1/model-choice analysis. Older entries remain historical.

## Hai production routes đã kiểm Kaggle thật —31/10/2026

**READY_FOR_TECHNICAL_REVIEW cả hai; MiniCPM official FP32 vẫn
BLOCKED_PENDING_SCIENTIFIC_DECISION. Chưa READY_FOR_OWNER.** Giữ Draft PR156,
chờ fresh ChatGPT exact-HEAD review, Antigravity audit độc lập và quyền merge
riêng. Không full160/TEST/kết quả khoa học chính thức trong task này.

Hai notebook mới `SafeShift_CANDIDATE160_PRODUCTION_internvl35.ipynb` và
`SafeShift_CANDIDATE160_PRODUCTION_minicpm4_FP32.ipynb` đã chạy đúng source/
cell bytes trên Kaggle private,3 ảnh TRAIN định trước0/15/111 mỗi model,
1 load/3 calls mỗi job. Cùng production entrypoint/child/controller/history;
raw/ZIP/SHA256/cleanup và import sealed ZIP sang workspace mới rồi resume
zero-load/zero-call đều PASS. Profile kỹ thuật/config/campaign/series tách
official, FP16 và FP32; metrics excluded, no pooling.

InternVL:38/38 logits steps hữu hạn; parser INVALID/SUCCESS/INVALID. Hai
INVALID do native model sinh code fence, independent decode khớp; không sửa
parser/prompt. Ảnh15 (chốt trước theo diện tích nhỏ nhất) có HNLO thực
7.301041903017601, native branch và Decimal oracle PASS; hai ảnh kia unaligned.
MiniCPM:33/33 steps hữu hạn,3 SUCCESS; HNLO vẫn unaligned vì native continuation
khác segmentation đã prove dù decoded JSON giống nhau. Không thay token/score.

Runtime `b5448d031b287bc7adabd58ec36d98e671449b9d`, tested export
`2a062e5d0896bd789a7c27db9876fe6406ae2bb6`, source
`09d94fd27a6a5260526c981a55854e8217536e0499824400ea9df5d213fb2d08`.
Final Linux374 =334 PASS/40 SKIP/0 FAIL/ERROR; native numerics8/8 PASS;
hai production CPU subprocess PASS, đủ160 images/8 processor sizes mỗi model.
Giữ lỗi setup/401/download và mọi evidence cũ. [Báo cáo chi tiết](research/CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md)
ghi notebook/source/config/ZIP SHA, receipts, giới hạn và cách Owner chạy.

Quyết định hẹp còn thiếu: Owner/Lead có dùng
`minicpm4-resampler-attention-fp32-v1` làm baseline official TRAIN160 hay không.
Gate fail-closed trước consumption/load; không mở bằng notebook flag/approval
giả. Chưa chứng minh forced VM kill, global lock/cross-VM concurrency hoặc
full160/12-hour resource behavior. Các mục dưới là lịch sử, không verdict mới.

## MiniCPM ngoại lệ hẹp: Kaggle technical smoke PASS —31/10/2026

**READY FOR REVIEW cho trial kỹ thuật, vẫn Draft PR156. Không READY FOR OWNER/
baseline khoa học/full160.** Owner cấp ngoại lệ trong quyết định mới bên dưới;
HOLD/FP16 BLOCKED phía sau giữ nguyên như lịch sử, không bị xóa hay hồi tố.

Runtime `0fa13ee610244a56d4d999cc5d73841267a28306`, Git export kiểm local
`0bb1b71f58818ed1e5c85aafa942f63ee9c72279`; source
`ae94d0033e8215fb3cf1e192c0ef0b5c0e5d76cc8eb904558dc4d9a26186ab7b`.
Effective ID `minicpm4-resampler-attention-fp32-v1`, digest
`2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`;
effective config SHA256 `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`.
Config FP16 gốc/hash/locks giữ nguyên. Full Linux365 =326 PASS/39 SKIP/0 lỗi;
8 native CPU tests PASS riêng (gồm oracle scalar thêm sau Git export), production
effective `--check-only` PASS thật,4 baseline notebook tests PASS Windows.

Kaggle private `nguynanhtn/safeshift-minicpm4-fp32-trial-20261031/1`:1 ảnh0
TRAIN160 gốc,1 load/1 native call; weights4.059.533.040 tham số FP16, eager,
T4x2/GPU0. Score/softmax/value product FP32 hữu hạn, output về FP16, logits
11/11 steps hữu hạn, parser SUCCESS. HNLO **RAW_LOGITS_AVAILABLE_BUT_UNALIGNED**,
numeric HNLO chưa được chứng minh; không sửa parser/prompt/continuation hoặc
chọn ảnh khác để lấy score. Raw/native/tokenizer/config custody, cleanup và
ZIP/sidecar được kiểm lại độc lập trên CPU. ZIP SHA256
`0c1fe3b00a56314cd3688465f59f0ccb8dce09761c349e1724ec0d242c175337`.
[Bằng chứng mới](research/evidence/minicpm_resampler_fp32_20261031/index.json)
giữ hash của5 archive trước nguyên vẹn; raw/private images/weights không commit.

NEXT: ChatGPT kiểm GitHub exact HEAD/notebook/effective implementation/receipts,
rồi quyết định Antigravity audit độc lập. Không tự merge hoặc chạy160/TEST.
Notebook effective chỉ kỹ thuật, không route full/resume/history; scientific
result selection vẫn PENDING, pooling=false.4 notebook baseline được rebuild
payload do source supervisor đổi; bằng chứng Kaggle cũ không tự qualify lại
chúng. Trial mới này chỉ chứng minh đúng notebook/effective route đã chạy.

## Owner mở lại thử kỹ thuật ngoại lệ hẹp —31/10/2026, PR156

Owner cấp **AUTHORIZED_FOR_BOUNDED_TECHNICAL_TRIAL** cho MiniCPM resampler
score/softmax/value product FP32, output về dtype gốc trước out_proj; weights
giữ FP16 và tất cả model/checkpoint/revision/TRAIN160/C1/eager/parser/HNLO/
scientific locks giữ nguyên. [Quyết định mới](research/DECISIONS.md#dec-20261031-minicpm-resampler-fp32-technical-exception)
thay HOLD chỉ trong phạm vi thử kỹ thuật này; không baseline khoa học/full160/
TEST/result selection/merge. Tiếp tục cùng session/branch/Draft PR156.

Effective implementation mới `minicpm4-resampler-attention-fp32-v1` gắn chỉ vào
instance resampler bằng method dẫn xuất từ source gốc đã hash-verify, thay đúng
4 expressions (2 nhánh score, softmax, value product). Không sửa snapshot/locks
gốc, không global monkeypatch, không đổi projection/query scaling/weights.
Config/hash/series/output/new smoke notebook riêng; raw custody khóa effective
ID và counter của cả3 phép FP32 hữu hạn. Chặn full-run action cho ngoại lệ.

CPU native regression đã tái hiện overflow lớp attention gốc rồi kiểm finite/
mask/dtype/weights/class/source không đổi. **KAGGLE SMOKE CHƯA KIỂM CHỨNG cho
implementation mới** cho tới receipt thật cuối. Bằng chứng FP16 cũ giữ nguyên;
không tự coi InternVL/legacy notebook được qualify lại sau thay embedded source.
[Hồ sơ trial mới](research/MINICPM4_FP32_ATTENTION_TECHNICAL_20261031.md).

## Owner xác nhận HOLD —31/10/2026, PR #156

Owner đã chọn **phương án1: giữ BLOCKED**, chưa cho phép thay precision hoặc
effective source. [Đánh giá GitHub của ChatGPT](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6540368755)
được đọc trực tiếp; đánh giá sơ bộ tại HEAD `51f6eec3be1e1c3eb6a69346e9bd1571be7c87d1`
không phải final review PASS, independent audit hoặc quyền merge. Nhận xét dựa
trên committed receipts, không phải kiểm độc lập private raw ZIP Kaggle.

Giữ Draft PR156, toàn bộ evidence và lỗi FP16; không merge, không chạy lại
cấu hình MiniCPM chưa sửa, không chạy chính thức160 ảnh. Ngoại lệ FP32 vẫn
**PENDING / NOT AUTHORIZED / NOT APPLIED**. Chờ quyết định Owner riêng về phạm
vi thay đổi số học rồi tiếp tục đúng session/branch/PR156. Quyết định này chỉ
ghi trạng thái HOLD; không sửa runtime/notebook/locks/receipts hoặc nâng trạng
thái khoa học. [Bản ghi append-only](research/DECISIONS.md#dec-20261031-owner-hold-minicpm-numerics).

## Khôi phục Kaggle và quy trình kiểm chứng thật —31/10/2026, PR #156

Session mới xác minh remote: PR156 OPEN/DRAFT, branch
`fix/candidate160-recovery-20261031`, HEAD ban đầu `b1a56d0ce3fbd484820f56fa921bfbba9ec7f1d9`,
main `6252a7de91d9d98bd68a33b9bc13ae9888f2b9da`. Tiếp tục cùng worktree/PR,
không tạo PR mới, force-push hoặc sửa lịch sử. Nguồn quy tắc toàn dự án:
[Owner directive](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161),
đã bổ sung append-only vào AGENTS. Các đoạn “task chỉ CPU”/Owner chạy diagnostic
bên dưới là snapshot cũ; task mới cho phép Codex bounded smoke trên TRAIN đã khóa.

Đã xác minh archive InternVL lỗi cũ SHA256
`aee7f4b782c6eb31c780afc8f3d7756c5f91e30a5d9eab506417c2817c818e8c`,
28 member checksums khớp; `cpu_native_and_images`,160 NOT_ATTEMPTED,
native calls0/consumed=false. Giữ nguyên archive. Đã tái hiện cùng str/lstat
ở cả hai production worker subprocess thật với pins Linux3.11.9/cu124,
locked source và bundle thật; sau chuẩn hóa Path, cả hai CPU CLI PASS.
Không mock native_setup/verify_snapshot/worker trong regression này.

Kaggle CLI2.2.5 cài trong environment local riêng; authenticated read-only
kernels/datasets/status/Output download PASS. Không ghi secrets vào Git.
Smoke mới dùng cùng production supervisor/worker, manifest160 nguyên vẹn,
chỉ ordinal0/1 call/3600 giây, evidence riêng, không production reservation/
history hoặc scientific metrics. Notebook mặc định technical_smoke để tránh
tự chạy full160. **KAGGLE INFERENCE NOT VERIFIED** cho tới receipt thật cuối.
Xem [runbook](CANDIDATE160_KAGGLE.md) và [bằng chứng task mới](research/CANDIDATE160_KAGGLE_VERIFICATION_20261031.md).

NEXT: local final suite + exact notebook Kaggle smoke từng model; giữ FAIL/PASS,
cập nhật receipt/source/notebook SHA; ChatGPT kiểm GitHub và Antigravity audit
độc lập trước merge. Scientific selection PENDING/pooling=false, TEST đóng.
Không tự tuyên bố READY FOR OWNER hoặc chạy chính thức160 thay Owner.

**Cập nhật thực thi cùng session:** full Linux Git export `c9c2f24680e4eb21290dbf2e3b8fb308a5c8bf2e`
PASS354 tests =321 PASS/33 SKIP/0 lỗi; source `c7a48bc8479137ca29647c94cfb71d2e7a867b8b7d7ab394776cf5c0105764f4`.
Hai CPU worker CLI cuối cùng PASS. Kaggle InternVL version1 đã nạp weights,
inference1 ảnh/1 call, ZIP/raw/checksum PASS; response có code fence nên parser
giữ INVALID và HNLO unaligned, chưa chứng minh numeric HNLO/quality. Kaggle
MiniCPM version1 đã load weights và gọi1 ảnh nhưng raw_nonfinite ở64/64 steps,
controller STOP/receipt BLOCKED; không OOM, peak allocated khoảng9,74GB.
Archive FAIL SHA256 `7d9e1947e8316dd2586feaa44bcdbc52fa7dcabe52bc8aaf95050c4de333c939`
được giữ nguyên. **Toàn gói vẫn BLOCKED**, không READY FOR OWNER.
Đang thêm một diagnostic chỉ quan sát weights/module outputs trên đúng ảnh0,
giữ nguyên FP16/eager/C1/checkpoint và dừng tại nonfinite đầu tiên; không sửa
hoặc tắt validation, không chọn ảnh khác để tìm output đẹp. Diagnostic không
qualification hoặc production run. Artifact thật/raw/weights vẫn private/ignored.

**Blocker đã đo trên Kaggle, sau2 diagnostic một ảnh/call:** toàn bộ4.059.533.040
tham số FP16 hữu hạn; Q/K/V hữu hạn, mask0/không hàng fully masked. Native
resampler `baddbmm` FP16 sinh60.522 +Inf, softmax kế tiếp sinh569.800 NaN.
Không đổi model/source/checkpoint/precision để vượt lỗi. ZIP probe cuối:
`f4c27ff30bc9eb9132a5d9d736b18bbce45f42464d91ca38a943ffe3335c3b5c`.
Đường nạp/mã nguồn đã sửa; MiniCPM chưa finite inference PASS. Dừng retry cùng
cấu hình đã chứng minh lỗi. [Đề xuất sửa tính toán attention — PENDING](research/MINICPM4_NUMERICS_PENDING_DECISION_20261031.md)
chỉ để review, chưa áp dụng. Cần Owner quyết định ngoại lệ hẹp cho precision/
effective source trước triển khai; mục9 task hiện tại cấm tự thay. Quy tắc
chọn kết quả khoa học vẫn PENDING; không pooling/metric/test hoặc full160.

**Kiểm cuối:** Git export `7bb353529f2ad29bee56620ab94586aaf87fdcea` PASS358
tests =322 PASS/36 SKIP/0 lỗi;4 native tracer CPU tests PASS riêng trong stack
3.11.9/cu124. Hai production `--check-only` CLI PASS thật. Cả4 Kaggle jobs
(InternVL smoke1, Mini smoke1, Mini diagnostic1/2) đã COMPLETE, tổng4 native
calls kỹ thuật, không phải kết quả khoa học. COMPLETE không biến Mini thành PASS.
Runtime/embedded source vẫn `ad6c6ed23d33d218fd199d77c817f002a3ec0944`/
`c7a48bc8479137ca29647c94cfb71d2e7a867b8b7d7ab394776cf5c0105764f4`.
[Index bằng chứng cuối](research/evidence/candidate160_kaggle_20261031/index.json)
giữ đủ FAIL/PASS/checksums,41 file frozen và2 prefix append-only. NEXT duy nhất
để sửa Mini: review/phê duyệt hoặc từ chối đề xuất numerical policy PENDING;
không chạy lại cùng FP16 lỗi, không tự merge hoặc báo READY FOR OWNER.

## Task retry/resume Candidate160 —31/10/2026

Base mới từ remote main `6252a7d` (PR155 đã merge). Một Draft PR mã nguồn thay
khóa vĩnh viễn bằng run/attempt/series riêng, snapshot lịch sử SHA256, resume
ảnh chưa hoàn thành từ Outputs directory/ZIP và rerun toàn bộ có truy vết.
Các marker BLOCKED_RESERVED_NO_RETRY/CONSUMED/replacement1 giữ nguyên bytes.
[Quyết định mới](research/CANDIDATE160_RECOVERY_DECISION_20261031.md) bổ sung
append-only; [runbook hiện hành](CANDIDATE160_KAGGLE.md) ghi thao tác và giới hạn.

Scientific result selection **PENDING**, pooling_allowed=false; không tự ghép
baseline/recovery hoặc chọn output. Không đổi160 TRAIN, revisions/locks, C1,
HNLO, metric/nhãn/protocol hoặc quyền dữ liệu. Không GPU/Kaggle/weights/private
data/attempt thực nghiệm trong task. **CPU CODE PASS:** exact Git export
`afbf0307178b2ecfb1d81b7ec2504628bacaaaf0`:347 tests =315 PASS/32 SKIP/0 lỗi,
10 notebook khớp builder;15 recovery tests mới PASS. Windows11 focused/notebook/
prefix checks PASS;49 file bất biến và2 prefix append-only đã đối chiếu.
Runtime `0f0d272c60c3a574814c1b0d3dc4a73ee169b30c`, source SHA256
`f2b6af6d23869acea7ed7e6ee35162f7d2d1b9c83bc24c06d3040f1bfc2439cb`.
[Báo cáo nghiệm thu](research/CANDIDATE160_RECOVERY_CPU_20261031.md) và
[receipts](research/evidence/candidate160_recovery_20261031/index.json) giữ cả
full run đầu2 assertion lỗi và full run cuối đã sửa, không waive. Native opt-ins,
live pip, full Windows suite và GPU/model-fit/inference chưa chạy trong task.

NEXT: ChatGPT kiểm exact Draft HEAD/diff/notebooks/receipts, Antigravity audit
độc lập trước merge, quyền merge riêng và hậu merge. Không tự nhận DONE audit,
GPU hoặc khoa học. Các mục bên dưới là snapshot lịch sử, không thủ tục retry
hiện hành hoặc chứng nhận HEAD mới.

Cập nhật **31/10/2026 (Asia/Bangkok)** trong cùng Draft PR #155, theo chỉ thị environment-first.
Main đã kiểm remote: `39ec489403753ada10f4924c4b0d6077e027f5e1`.
Đây là snapshot trạng thái, không quyền thực nghiệm; mở task mới phải kiểm GitHub lại.

## PROJECT IDENTITY

- SafeShift nghiên cứu độ tin cậy của VLM khi phân loại nguy cơ công nghiệp, kiểm tra chéo và ưu tiên người kiểm tra.
- Owner chuyển thẳng sang Khóa luận ngày 27/10; không tự đánh dấu Seminar/M3–M5 hoàn thành hoặc hủy lịch sử.
- [Kế hoạch Khóa luận](research/THESIS_EXECUTION_PLAN_2026.md) đề xuất bốn peers: phân loại độc lập → focal rotation → ensemble và review, hai endpoint cuối tách riêng.
- Thiết kế/primary/metric/final roster/nguồn mới vẫn **PROPOSED; O1–O8/T0 PENDING**. HNLO optional theo từng model, không xác suất nguy cơ hoặc confidence đã hiệu chuẩn.

## CURRENT STATUS

- **Yêu cầu environment-first 31/10 — IMPLEMENTED IN DRAFT / chưa COMPLETE.**
  [Chỉ thị Owner](https://github.com/tantdna2/SafeShift/pull/155#issuecomment-6533181366)
  được ghi append-only trong `AGENTS.md`. Cùng branch/PR155, không PR mới.
  Preflight v2 thêm inventory kernel/ABI/OS/RAM/cgroup/visibility, software
  qualification child riêng, receipt binding/đủ evidence, các mức PASS riêng,
  deadline từ đầu và final result fail-closed khi export/sidecar/cleanup lỗi.
  [Runbook](CANDIDATE160_KAGGLE.md) ghi facts OWNER_REPORTED và cách Owner chạy
  diagnostic với cùng Inputs/settings; còn thiếu bằng chứng Kaggle thực tế.
  Không đổi khoa học/model revision/metric/cohort hoặc cơ chế chống retry.
  Chưa chạy Kaggle/GPU/weights/private data/attempt hoặc merge ở Codex.
  Chỉ COMPLETE khi final HEAD được ChatGPT kiểm GitHub, Antigravity audit độc
  lập, merge được cấp quyền riêng và hậu merge xác minh quy tắc trên main.
  Các kiểm thử/bằng chứng30/10 bên dưới là snapshot cũ, không tự nâng HEAD mới.
  **CPU CODE PASS31/10:** runtime `f679e3153a1418cd521d1875cfa797b5aded8570`,
  tested snapshot `0363db4976f39f8c4249ab84a7c54986f41e1e99`;
  full Linux332 =300 PASS/32 SKIP/0 lỗi,10 notebook khớp builder;
  Windows focused43 =38 PASS/5 SKIP/0 lỗi. Hai actual worker CLI đều qua
  exact3.11.9/cu124 pins/NMS ABI/source-bound envelope +8 synthetic sizes,
  có guards cấm CUDA/weights/real-forward. Source/hash lịch sử được đối chiếu
  bằng Git objects; không sửa locks. [Receipts mới](research/evidence/candidate160_envfirst_20261031/index.json).
  LIVE_GPU_PREFLIGHT/WEIGHTS_LOADED/INFERENCE/SCIENTIFIC vẫn chưa được chứng minh
  trên Kaggle. Final HEAD mới phải được review/audit lại, không tự merge.

- **Snapshot bàn giao30/10 Candidate160 environment repair — DRAFT / chưa GPU PASS.**
  Thêm bounded Notebook Output discovery riêng cho Candidate160; giữ pilot cũ.
  CPython3.11.9 standalone20240726 đã tải/kiểm29.713.170 bytes/SHA upstream;
  venv copies cần libpython cùng SHA trong venv/lib. Preflight notebook riêng
  không execution/slot/attempt/weights/model call; receipt từng gate không suy READY.
  Ngoại lệ một replacement1 chỉ cho sealed incident InternVL checkpoint_source
  FOUND_0 có160 NOT_ATTEMPTED/attempts0/native_calls0 và consumed=false; giữ
  campaign/slot/marker cũ, chặn partial/consumed/unknown và lần thay thế thứ hai.
  [Quyết định/giới hạn](research/CANDIDATE160_KAGGLE_ENV_DECISION_20261030.md),
  [runbook](CANDIDATE160_KAGGLE.md). Bằng chứng Kaggle cũ chỉ OWNER_REPORTED;
  chưa có original private archive để xác nhận đủ điều kiện replacement.
  ChatGPT kiểm GitHub và Antigravity audit độc lập vẫn bắt buộc trước merge.
  Không GPU/private TRAIN/GT/TEST/weights hoặc merge trong task này.
  **CPU CODE PASS:** exact export `2306aecb280acfedd1dd11523f14b60f892c771f`,
  324 tests =292 PASS/32 SKIP/0 lỗi;10 notebook khớp builder. Windows focused
  13 tests =9 PASS/4 symlink SKIP;4 notebook tests PASS. Cả hai production
  CPython3.11.9/cu124 stacks qua exact pins/ABI/native meta +8 synthetic sizes.
  Native exact-export suite15/15 PASS/model, gồm160 ảnh tổng hợp/model qua
  production cu124 software với scripted logits; không model predictions thật.
  [Receipts](research/evidence/candidate160_env_20261030/index.json) và runbook
  ghi BASE-reproduced stale AGENTS assertion, correction và các giới hạn thật.

- **PR #153 MERGED**, GitHub `merged=true`, merge `fc1e454212455685e1775601ebfd6aab9535c932`.
  Owner đã trực tiếp yêu cầu bỏ thủ tục phê duyệt lặp lại cho một lượt/model
  InternVL3.5/MiniCPM-V-4, ≤160 TRAIN, dùng bundle/checkpoint Owner đã upload.
  [Record chỉ thị và phạm vi](research/CANDIDATE160_OWNER_DECISION_20261030.md),
  [runbook mới](CANDIDATE160_KAGGLE.md), [CPU acceptance](research/CANDIDATE160_OWNER_CPU_20261030.md).
  Hai notebook dùng Save & Run All làm kích hoạt, tự sinh run/attempt/slot và
  consumption log; không grant/reservation/CONTINUE thủ công hoặc approval ref giả.
  Cần ChatGPT kiểm GitHub và audit độc lập trước merge Draft PR này; task chỉ
  synthetic CPU, không GPU, real weights hoặc private TRAIN/GT/TEST.

  Technical errors/NaN/Inf/raw/custody/resources/time vẫn dừng; behavior và GT
  support chỉ ghi để review sau run vì chưa quyết định scientific thresholds.
  Đây là thay đổi chính sách dừng công khai trong PR, không silent approval.
  Giữ parser/HNLO/C1/model/checkpoint/cohort/order và mọi giới hạn160/no-retry/
  no-resume/no-overwrite. Không mở quyền bên thứ ba/TEST/FULL TRAIN/khác scope.
  Khóa fixed slot chống duplicate trong cùng output root và attached Outputs
  chuẩn; không distributed/global exactly-once cho VM mới thiếu lịch sử.
  Actual Kaggle Python/CUDA/T4/VRAM/weights/behavior/HNLO vẫn UNVERIFIED.
  **CPU CODE PASS:** exact-export310 tests =273 PASS/37 SKIP,0 failures/errors;
  native Windows67 tests/model =64 PASS/3 symlink SKIP,15/15 native PASS gồm
  đúng160 ảnh tổng hợp/model qua Owner path. Linux3/3 activation/scope/atomic
  slot PASS. [Receipts/checksum index](research/evidence/candidate160_owner_20261030/index.json).
  Tested snapshot `f427e59c90f15c5bb87db26ff1aad5e038310af8`; runtime
  `93bc2f110822c3cfd3c910da8f8adb11a0d9ac1f`; sau đó chỉ docs/receipts.

- **PR #152 MERGED**, GitHub `merged=true`, merge `f79f7bddeac62e8fb8378d6798c25387f45f0f37`.
  Gói batch #153 lịch sử **CODE PASS / execution BLOCKED** theo cơ chế cũ.
  [CPU report/receipts](research/CANDIDATE160_BATCH_CPU_20261030.md); quyền batch
  chưa duyệt, real weights/GPU/runtime/behavior UNVERIFIED.

- **PR #151 MERGED**, GitHub `merged=true`, merge `95eb4e8801ea746e1a760b9d529920bffb3c26cb`, xác minh live trong task này. Adapter CPU READY trong phạm vi #151; không cấp GPU/data/grant hoặc scientific qualification.

- **PR #150 MERGED**, merge `bbbd351e19e404f1108413578c7ed024f92e814d`, xác minh GitHub `merged=true` và origin/main trước task này. Findings CPU của #150 là baseline lịch sử; không phải kết luận về adapter mới bên dưới.

- **PR #137 MERGED**, merge `1488dcb5212164e2946a15055d1da6e8be9096d2`; [ChatGPT hậu merge PASS](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Hoàn tất phạm vi repository/technical của #137, không scientific approval hoặc GPU readiness.
- **PR #149 MERGED**, merge `6342b15b0d70c27b28f4bcb5e53f04f6951d6171`. Shortlist report hoàn tất phạm vi tài liệu; CPU G2/G3 mới có kết quả riêng bên dưới, không scientific approval/qualification.
- [Issue #148 cập nhật 29/10](https://github.com/tantdna2/SafeShift/issues/148) bỏ ON HOLD **chỉ cho public research/metadata/CPU không weights và shortlist report**. Dòng #137 DRAFT/#148 ON HOLD trong các tài liệu cũ là snapshot đã bị live evidence này thay thế trong phạm vi tương ứng.
- **M1 EFFECTIVE cấp dự án / M2 v1 FROZEN** theo [DECISIONS](research/DECISIONS.md), hai SHA và [hậu merge #135](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030). Không sửa bytes protocol/config để cập nhật cờ cũ.
- DEC-PA3-011 lịch sử giữ PROPOSED; successor M1 chỉ thay phần đã được duyệt của D9R22. Grant cũ không chuyển sang thesis/model/source mới.
- **M3 IN_PROGRESS:** [#136](https://github.com/tantdna2/SafeShift/pull/136) giữ OPEN/DRAFT/audit FAIL theo hồ sơ hậu merge #137; lỗi metadata R3/R4, chưa COMPLETE. Không sửa PR này trong #148.
- [#147 OPEN](https://github.com/tantdna2/SafeShift/issues/147) đã kiểm live: chẩn đoán Phi/Smol riêng, chưa chốt model-vs-integration causes.

## VERIFIED COMPLETED WORK

| Sản phẩm đã merge | Bằng chứng và giới hạn |
| --- | --- |
| Foundation V1, saved-score/source feasibility | [#130](https://github.com/tantdna2/SafeShift/pull/130), [#131](https://github.com/tantdna2/SafeShift/pull/131); records/exact join/CPU sensitivity, không raw audit mới cho mọi model. |
| Hướng/Execution Plan và M1/M2 | [#133](https://github.com/tantdna2/SafeShift/pull/133), [#134](https://github.com/tantdna2/SafeShift/pull/134), [#135](https://github.com/tantdna2/SafeShift/pull/135); M2 hiệu lực đúng hash/scope lịch sử. |
| Pilot PREP, storage, worker runtime và pip bootstrap | [#138](https://github.com/tantdna2/SafeShift/pull/138)–[#141](https://github.com/tantdna2/SafeShift/pull/141); không đồng nghĩa behavior PASS. |
| Phi attention/shared loader, Smol native/dependency rehearsal | [#142](https://github.com/tantdna2/SafeShift/pull/142), [#144](https://github.com/tantdna2/SafeShift/pull/144), [#146](https://github.com/tantdna2/SafeShift/pull/146); actual outcomes ở dưới. |
| Thesis plan PROPOSED, failure register và CPU release checker | [#137](https://github.com/tantdna2/SafeShift/pull/137), merge `1488dcb5212164e2946a15055d1da6e8be9096d2`; [hậu merge](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Không có thesis ensemble/triage/viewer engine đã nghiệm thu. |

Tests trước đây thuộc receipts/PR tương ứng; không nhận là đã tái chạy trong task nghiên cứu #148.

Các merge SHA, audit links và bundle receipts chi tiết vẫn được lưu trong [snapshot PROJECT_STATE tại BASE](https://github.com/tantdna2/SafeShift/blob/1488dcb5212164e2946a15055d1da6e8be9096d2/docs/PROJECT_STATE.md); snapshot đó có trạng thái #137/#148 cũ, không thay trạng thái hiện tại ở trên.

## PILOT EVIDENCE — KHÔNG TÁI AUDIT PRIVATE ARTIFACT

- Bundle lịch sử: 160 TRAIN IDs, 80 L04/48 L01/24 L02/8 L03; không TEST. [Quyền/receipt gốc](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6460760653), [runbook](KAGGLE_THREE_VLM_PILOT.md); không tái mở ZIP/GT trong #148.
- **Phi a6 CONSUMED / NO_GO_FULL_TRAIN:** [aggregate ChatGPT](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537), 160 native calls, 0/160 C1 valid, 8 sequences/142 lần lặp một sequence, HNLO validated 0. first 12 technical PASS không là classification PASS.
- **Smol a2 CONSUMED / NO_GO_FULL_TRAIN:** [aggregate ChatGPT](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647), 160 calls, 107 valid đều Level01, 53 INVALID, 2 responses, HNLO validated 0; frozen-continuation mismatch không giải thích căn nguyên collapse.
- Phi a1/a2/a4/a5 consumed; a3 FAILED_PRELEDGER/nonconsumed. Smol a1 RESERVED/NOT_EXECUTED lịch sử không là quyền source mới. [Incident/gate register](KAGGLE_FAILURES_AND_RELEASE_GATES.md) giữ chi tiết.
- **Gemma BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:** 10 config/tokenizer 401 ở audit cũ. #148 kiểm anonymous 7 metadata requests cũng 401; không phải GPU failure, không tự tạo lock/grant.
- `OWNER_SELECTED_CANDIDATES` Gemma/Phi/Smol ngày 27/10 là sự kiện lịch sử, chưa qualified ba peers. Không cứu parser/C1/HNLO surfaces hoặc tiêu attempt tiếp.

## TUYỂN CHỌN #148/#149 — SNAPSHOT PHẠM VI LỊCH SỬ

- Báo cáo [THESIS_VLM_CANDIDATE_SCREENING_20261029](research/THESIS_VLM_CANDIDATE_SCREENING_20261029.md) đã **[MERGED PR #149](https://github.com/tantdna2/SafeShift/pull/149)**, gồm bổ sung R3. Các bullet dưới đây ghi checks/quyền của task docs-only #148/#149, không nhận là native CPU status mới. [Review R1/R2](https://github.com/tantdna2/SafeShift/pull/149#issuecomment-6489345290) giữ phạm vi lịch sử; merge không tự qualified model.
- Đã đọc InspecSafe arXiv v2, publisher, Figure 6, Table 3, S2/S3 và repo tác giả pinned; phân biệt paper benchmark với strict C1 JSON và TRAIN lịch sử.
- Giữ longlist **12 ứng viên gốc**, bổ sung so sánh C01-HF và truy nguồn custom không hậu tố. Ưu tiên nghiên cứu mới: **(1) `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`, (2) `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; vị trí 3 VACANT**.
- R1: native HF giảm remote loader/manual preprocessing/hidden decode cleanup, nhưng khác training stage với `-Instruct`; tensor/inference parity **UNVERIFIED**. CPU qualification tương lai ưu tiên source Transformers 4.55.4; không sửa lock hoặc chạy native trong lần này.
- R2: LLaVA lợi hơn Idefics3/Llama3 về FP16/parameter/KV; Idefics3 là comparator non-Qwen chính, có câu hỏi license/instruction và BF16→FP16. Cả hai cần sharding hai T4 chưa kiểm; chưa có paired hazard/shared-error evidence để chốt slot 3. Không coi khác backbone là lỗi độc lập.
- R3: InternVL3-2B-hf lịch sử đúng **164/3.763 (4,36%)**, **3.014/3.014 Normal→Anomaly**; HNLO **0,8861824613751756** là saved-score, không raw-logit PASS. CUDA SONAME lookup thất bại ở child worker, cuInit chưa gọi; không suy driver cũ hoặc bản 3.5 đã sửa. Hai bản đều native HF, ba processor/template files trùng hash; image token 151667→151671 khác.
- Giữ InternVL #1 **chỉ qualification CPU đọc nguồn/không weights**, MiniCPM #2; prior behavioral risk lớn, chưa có bằng chứng chất lượng hơn MiniCPM. **Thứ tự Kaggle PENDING O3**, không kế thừa thứ tự CPU. G2 đúng token/template/raw, G4 actual isolated-child CUDA loader, G5 GT Normal/hazard đa miền + strict C1/repetition/early stop phải được duyệt trước 160/full; thresholds/GT/grants còn PENDING.
- R3 thực kiểm: sáu public metadata/template files 2B đúng revision, HTTP200/hash khớp audit, năm JSON; ba hash chung và arithmetic aggregate được đối chiếu, không raw/GT/HNLO recomputation. R1/R2 không nghiên cứu lại.
- QA R3: 20 bảng, 21 relative links/reference definitions, sáu source links mới HTTP200; scope đúng hai docs và nội dung R1/R2 giữ nguyên. C1/protected files không đổi; checks do Codex chạy, không independent audit/CI.
- **0 ứng viên mới qualified**; classification thật/peer utility/HNLO của shortlist **UNVERIFIED**, quyền execution **BLOCKED**. Không sửa official roster hoặc tự thay Qwen3.
- CPU nhẹ ở bản trước review, **Codex-reported, không independent/CI**: 13 Hub records; 114 source/config/card files + 9 tokenizer files đọc/hash; 123 hash checks, 69 JSON parses, 27 AST parses; 5 MiniCPM config cross-checks, token-ID checks và 2 text-stage Jinja/C1 checks. Đây không native processor/tokenizer/model PASS.
- Bổ sung R1/R2 thực chạy inline: 17 pinned source hashes/HTTP200, 6 HF JSON, 8 Python AST không import; HF text-stage Jinja/C1/image-token consistency PASS. Có bảng hash/link công khai; native processor/tokenizer/model **NOT_RUN**, không independent audit. Không tạo script mới.
- QA R1/R2: 19 bảng, 21 relative links, 19 source links HTTP200; kiểm lại identity/revision/hash lịch sử và KV arithmetic PASS. C1/protected files không đổi; chỉ hai tài liệu trong diff.
- Không cài Torch/Transformers, tải weights, inference/GPU/Kaggle/TEST/private artifacts, tạo grant/notebook hoặc sửa khoa học. Chỉ 2 file tài liệu trong PR; BASE/HEAD/validation nằm trong PR body và bàn giao.
- Ranking là ưu tiên kiểm chứng theo nguồn, không accuracy đã đo. T4×2 không pooled 32 GB; FP16/attention/tiles/native wrapper và per-GPU memory còn phải G2/G4/G5.
- Báo cáo so A cũ fixed-Q3+auxiliary với B peers hiện proposed; tách classifier, cross-check, fusion/review và HNLO optional; không đặt numerical thresholds hoặc phê duyệt ensemble rule.

## MERGED #151 — HAI CANDIDATE, TÍCH HỢP CPU TRƯỚC KAGGLE

- **CPU READY trong phạm vi phần mềm đã kiểm thử; GPU release BLOCKED.** [Báo cáo/tái lập](research/CANDIDATE_INTEGRATION_CPU_20261029.md), [receipts](research/evidence/candidate_integration_20261029/index.json), code commit `65640ddf91bd0ce75e594c372af098ecb59194eb`, nhánh `implement/candidate-integration-20261029`, từ main sau #150. PR #151 đã merge ở SHA phía trên; các receipts dưới đây là snapshot CPU của #151, không bằng chứng GPU hoặc scientific approval.
- `safeshift/candidates/` cung cấp hai adapter với source public đúng revision, native loader/processor, C1/generation cố định, explicit eager, raw IDs trước decode và bounded raw logits. Tái dùng runner/Store/parser/replay/archive qua tests; không ghi candidate vào registry/grants của pilot cũ.
- **InternVL3.5 HF:** `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`; native HF 4.55.4, image ID151671/256 tokens/view; 36+24 attention layers và 841 tensor keys qua native key conversion. Prefix phải khớp trước lấy continuation.
- **MiniCPM-V-4:** `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; native 4.51.3,32+27 layers/741 tensor keys. Sửa ambiguity RGB1×1 bằng trục HWC tường minh, giữ native resize/slices/normalize; dùng `generate(decode_text=False)` giữ generation contract/logits, continuation-only và hai EOS native. Native chat lỗi vẫn được tái lập, không dùng nó để classify.
- Kiểm native tensor/image plumbing với scripted towers, image bounds/shape/dtype/context, exact spatial parity, bốn nhãn/whitespace/INVALID/EOS/max64, lỗi load/decode/ENOSPC và raw-before-parse/tail/archive. Loader meta và file safetensors rỗng chỉ chứng minh phần mềm/cấu hình, không deserialization weights thật.
- Snapshot guard #150 giữ exact flat allowlist/no aliases; bổ sung kiểm dedicated remote cache trước import, implementation/version lock, checkpoint index/LFS metadata lock, protected science/source lock và verifier cho receipts. Không đổi public source lock13/15 file, CPU requirements hoặc C1.
- Mỗi model **Windows65=62 PASS+3 symlink SKIP**, **Linux65=64 PASS+1 Windows-junction SKIP**, không failure/error. Cả13 native tests PASS trên từng stack/OS. Full exact-export suite **Windows266=231 PASS+35 SKIP**, **Linux266=236 PASS+30 SKIP**; sáu notebook byte/builder/compile PASS, không execute cells. Skip details/phạm vi trong receipts; không nâng Phi/Smol native chưa rerun thành PASS. Bằng chứng do Codex thực chạy, không CI hoặc independent audit.
- Giữ pilot source digest `1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`; sáu notebooks không sửa. Không chạy notebook, weights, inference/GPU/CUDA/Kaggle, private TRAIN/TEST/GT/archive, không cấp grant, chọn model thứ tư hoặc đổi giao thức để đạt PASS.
- **GPU release BLOCKED**: cần ChatGPT review, G0/G1 đăng ký execution release/source/runtime/grant mới; G4 Linux/CUDA isolated-child/device/memory và G5 finite first image/quality/utility/HNLO bằng quyền riêng. O1–O8/T0/O3 PENDING, peer slot3 VACANT,0 candidates qualified.
- [CPU G2/G3 lịch sử #150](research/CPU_G2_G3_CANDIDATES_20261029.md) và receipts cũ giữ nguyên: MiniCPM native1×1/chat FAIL và InternVL tổng thể BLOCKED ở code cũ. Kết quả adapter mới không sửa hồi tố findings hay reviewer status của #150.

## MERGED #152 — HAI NOTEBOOK CANDIDATE160 PREP

- **PR #152 MERGED**, merge `f79f7bddeac62e8fb8378d6798c25387f45f0f37`,
  [GitHub](https://github.com/tantdna2/SafeShift/pull/152), verified30/10/2026.
  Các bullet bên dưới là bằng chứng CPU và giới hạn tại #152; trạng thái chờ merge
  trong snapshot cũ đã được thay bởi mục này. Không chuyển grants sang source mới.

- Task Owner mới: chuẩn bị tối đa160 ảnh/model, không dataset/weights/GPU/Kaggle execution. Nhánh/worktree riêng từ đúng SHA sau #151; dừng ở **một Draft PR**.
- [Runbook](CANDIDATE160_KAGGLE.md), [biên bản CPU](research/CANDIDATE160_CPU_20261029.md); hai notebook riêng [InternVL](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb) và [MiniCPM](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb), builder tái lập và source/ref/config pins.
- Cùng manifest lịch sử SHA `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`, đúng160 ID/order và quota80/48/24/8 theo receipt metadata công khai #138. Không mở private manifest/ảnh/TEST, không selector hoặc supplement; actual bundle bytes chưa được reverify trong task này.
- Tái dùng adapter #151, runner execute/Store/parser/HNLO/metrics/archive; giữ nguyên source runtime/pilot và sáu notebook cũ. First-image/early behavior nằm trong160, review gắn hash checkpoint; thiếu quyết định dừng/NOT_ATTEMPTED tail, no retry/resume/overwrite.
- `configs/candidate160/preparation.json` giữ grant=null, G0/T0/O3/runtime/driver/stop thresholds/mốc review PENDING. Không tự lấy numerical thresholds hoặc grants Phi/Smol/Gemma. CUDA tuple mới là PREP cần review; không claims VRAM fit hoặc quality/HNLO PASS.
- [Review ChatGPT #152](https://github.com/tantdna2/SafeShift/pull/152#issuecomment-6501983735) yêu cầu sửa metadata Phi kế thừa và provenance hai hash tại HEAD `65da8a3…`. Cùng PR đã sửa config/grant v2: tách legacy transport snapshot khỏi effective candidate; `legacy_transport_config_sha256` khác `candidate_execution_config_sha256`, đối soát raw trước parse và recovery, không đổi pilot/adapter/science/stop policy.
- Runtime #152 `820200bba7c6f5796961acb64befef0c651772b3`, notebook/release commit `c75113f4a62d8d30303269f4a8bd72fc71040c15`, source SHA `3b63d9cf92df66042cbd201861c50ab8f0cfd0b4d1a57d194493faf33c24524e`. Snapshot CPU mỗi model Windows64=61 PASS+3 SKIP, Linux64=63 PASS+1 SKIP; cả15 native tests PASS/model/OS, gồm160 scripted calls kiểm hai hash/request. Full exact-export Windows293=256 PASS+37 SKIP, Linux293=261 PASS+32 SKIP, không FAIL/ERROR; tám notebook kiểm PASS, candidate cells không grant CPU vẫn BLOCKED. Actual weights/CUDA/GPU/behavior **UNVERIFIED**; merge không nâng các bằng chứng này.
- External ledger snapshot không là chữ ký số/distributed one-shot enforcement; fresh reservation/current ledger và phương thức giao review vào saved VM cần review/approval riêng. Không vì code CPU PASS mà tự mở release.

## ACTIVE WORK — GÓI BATCH CANDIDATE160 SAU #152 (30/10/2026)

- Một nhánh/Draft PR từ đúng main `f79f7bd…`; hoàn thiện cả notebook, runtime,
  authority worksheets/checker, tests và handoff trong cùng phạm vi. Không Kaggle,
  GPU, tải weights hoặc truy cập private TRAIN/TEST trong task này.
- [Batch authority PROPOSED](research/CANDIDATE160_BATCH_DECISION_20261030.md):
  máy chỉ AUTO_CONTINUE khi Lead cho phép rõ đúng policy/execution binding và
  mọi điều kiện đạt. Missing approval chặn trước call; EXTERNAL review giữ được.
  Không giả CONTINUE, không tự duyệt chính sách khoa học hoặc numerical limits.
- Child CUDA FP16 preledger rồi kiểm lại trong worker; Linux NVIDIA/Triton pins
  đầy đủ từ official wheel metadata; RAM/cgroup/disk/GPU0 runtime headroom theo
  policy. Không đổi adapter/source/checkpoint locks #151, C1/parser/HNLO/generation,
  manifest/order160 hoặc sáu notebook cũ. Model/real weights/T4 fit còn UNVERIFIED.
- [Runbook và checklist duy nhất](CANDIDATE160_KAGGLE.md#checklist-bàn-giao-duy-nhất)
  nêu từng quyền, threshold/mốc/driver/resource limits, grants/reservations/Inputs
  thật còn thiếu. `preparation.json` giữ null/BLOCKED, không EXPERIMENT READY.
- [Nghiệm thu CPU mới](research/CANDIDATE160_BATCH_CPU_20261030.md): mỗi model
  Windows73=70 PASS+3 SKIP, Linux73=72 PASS+1 SKIP; cả15 native tests PASS/model/OS,
  gồm160 synthetic images qua native processor/generation và batch. Full immutable
  export Windows302=265 PASS+37 SKIP, Linux302=270 PASS+32 SKIP, không FAIL/ERROR.
  SKIP không tính PASS; tám notebook/source/builder/cells/archives kiểm PASS.
  Source `5189a456b62e5dbef631b712eb0b377044bc84066d6ffd190976e3ee26901e1d`,
  runtime `04090aeb182883da25726a12cbd6371d3d6c9913`. Không dùng receipts #152
  chứng nhận source mới. Dừng ở Draft PR cho ChatGPT kiểm exact HEAD và quyết
  định audit/merge; chưa independent audit, quyền thực nghiệm hoặc EXPERIMENT READY.

## KEY DECISIONS / LIMITS GIỮ NGUYÊN

- Roster lịch sử: Qwen2.5-VL-3B-Instruct, Qwen3-VL-8B-Instruct, InternVL3-2B-hf, Moondream2. Shortlist #148 không thay roster này.
- Owner chấp nhận Moondream2 HNLO TRAIN N/A cấp dự án; không suy ngoại lệ học vụ hoặc thesis final selection.
- Q25/IVL3 full 3.763; Q3 V4 gốc: 3.763 planned = 3.539 SUCCESS + 1 error + 223 not attempted. Recovery 224 riêng, không pooling; common panel đúng 3.539 original IDs.
- Q3 HNLO AUROC 0,9527927338600111 là saved-score verification đúng cohort, không raw PASS mới/generalization. [Results/limitations](RESULTS_AND_LIMITATIONS.md).
- False-safe V4-only phải đếm đúng original IDs; không dùng 38 hoặc khoảng 30–38 từ composite làm số chính thức. IVL3/Q3 saved-score verification không phải raw audit mới.
- B01/B02/B05 giữ 19 placeholders (12 atoms/7 groups), continuous controls N/A, mismatch/proxy BLOCKED; giữ 5 folder_domain, không source independence/causal claim.
- B03 provenance/raw limits chưa khép bởi receipt saved-score; không yêu cầu raw replay mới ngoài quyền chỉ vì có đường dẫn artifact.
- M2 hai hash và quyết định hiệu lực giữ nguyên; PENDING/frozen=false trong bytes cũ không được sửa để đổi cờ.
- H1 strict-majority vs dev-best single, 4 focal review, metric/guardrails/multiplicity đều đề xuất chờ O1/O2/O5; target phải kín và độc lập, không TRAIN đã lộ hoặc TEST.

## NEXT STEP / BLOCKERS

1. **ChatGPT review đúng một Draft PR batch160 mới sau #152 MERGED**: exact HEAD/diff/source/notebooks/receipts và CPU scope; không dùng CPU hoặc review adapter thay G0/G1/G4/G5 mới.
2. Sau review, cân nhắc independent methodology audit và Owner/giảng viên O1–O8/T0; O3 chốt bounded qualification sequence/attempt cap trước thực nghiệm, final roster sau evidence.
3. G0–G6 theo [runbook](KAGGLE_FAILURES_AND_RELEASE_GATES.md): CPU chỉ đúng phạm vi có receipt; real weights/CUDA, execution release và behavior/HNLO vẫn BLOCKED/NOT_RUN. G4/G5 cần quyền mới; CPU không vượt behavior gate.
4. Thiếu nguồn/GT/custody/reviewers/precision/quota hoặc không đủ 4 qualified → NO-GO thiết kế xác nhận; giảm scope cần quyết định, không mở model zoo hoặc target thay thế.

## REFERENCES / UPDATE RULES

- [AGENTS](../AGENTS.md), [README](../README.md), [ROADMAP](ROADMAP.md), [ARCHITECTURE](ARCHITECTURE.md); các snapshot premerge phải đối chiếu GitHub live.
- [Thesis plan/O1–O8](research/THESIS_EXECUTION_PLAN_2026.md), [DECISIONS](research/DECISIONS.md), [source gate](SOURCE_FEASIBILITY_GATE_20261024.md), [HISTORY](HISTORY.md).
- Cập nhật trạng thái trong cùng PR task, không PR phụ; giữ file ngắn, không raw/credentials hoặc toàn bộ chat.
- Tách DONE sản phẩm, audit/merge và khoa học/thực nghiệm. Codex không nhận Draft đã merged; ChatGPT xác minh hậu merge.
- Không sửa protocol/labels/split/metric/roster/legacy refs, không chuyển grant cũ; raw-before-parse khi có quyền chạy, derived local ở `data/processed/`, không commit weights/data.
