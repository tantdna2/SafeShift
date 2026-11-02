# Issue #167 — full TRAIN readiness và controlled repair

Phạm vi: [Issue #167](https://github.com/tantdna2/SafeShift/issues/167),
[quyết định Owner](research/DECISIONS.md#dec-20261102-owner-thesis-fulltrain-repair).
BASE `0295172783dcf82426923d1af621dde9db8ed42c`; commit tài liệu trước code
`ff64958c22684e8713b428b439521f8f3cb1222a`; cùng branch
`thesis/fulltrain-3763-repair-20261102`, một Draft PR. Chỉ CPU synthetic;
không Kaggle/GPU/inference/TEST/private images, GT hoặc raw trong task này.

## Khả năng phần mềm và giới hạn

`safeshift/candidates/fulltrain.py` kiểm 3.763 ID duy nhất theo ordinal,
checksum/order giống nhau giữa ba ứng viên, nguồn master TRAIN đã khóa và
identity model/revision/implementation/config/prompt/parser/generation/
preprocessing/checkpoint/runtime. Không có GT/path trong projection thực thi.
`cohort(master_bytes)` chỉ nhận đúng SHA256 master lịch sử từ
`pilot.contract.MASTER_SHA`, rồi tái dùng `validate_master`; không tự tạo
manifest thật hoặc đọc dữ liệu. Hash projection do custodian/reviewer khóa
sau khi so với nguồn gốc; tự tính hash không chứng minh quyền/custody.

`fulltrain_run.py` dùng lại `pilot.runner.execute`, `Store`, strict C1 parser,
exclusive write+fsync, bounded ZIP/member SHA verification/import và process
lease của recovery Candidate160. Engine thêm hai keyword tùy chọn
`transport`/`hnlo_replay`; đường cũ giữ defaults. Lease được tách primitive
`lease_key`, wrapper160 giữ cùng khóa. Không sửa C1/parser/nhãn, numerical
adapter FP32, HNLO hay quy tắc recovery160 cũ.

Controller mới chỉ chạy qua `rehearse` với đúng 3.763 byte fixtures công khai,
ID `synthetic-*`, model `synthetic/*`, factory do test inject. Package không
chứa backend sinh dự đoán giả. Test fixture không là model inference. MiniCPM
label-only không gọi HNLO evaluator; không mở lại điều tra #165.

**Đây là CPU readiness/controller, chưa là runtime full TRAIN được phát hành.**
`fulltrain.launch` luôn từ chối trước đọc Input/history/credentials, provision,
reservation hoặc model load. Không có cờ `approved`/grant JSON để tự mở.
Qwen3 chưa có native fulltrain mapping được review trên main; không nhập runner
legacy vào main hay gắn grant V4 cũ vào runtime mới. Candidate160 backend,
Python provisioning, pin/ABI, checkpoint/input/storage/CUDA checks đã có là
đường tái sử dụng cho một release được duyệt sau; chúng chưa được đo lại cho
3763 và notebook mới. Không gọi khả năng synthetic là READY FOR OWNER.

## Chế độ và lịch sử bất biến

| Action | Scheduling | Ràng buộc |
| --- | --- | --- |
| `initial` | ID chưa chạy, theo ordinal, cắt theo cap | Không có history; series/run/attempt mới |
| `resume` | Chỉ NOT_ATTEMPTED trong series đang chỉ định | Identity không đổi; SUCCESS, INVALID, consumed error không tự chạy lại |
| `repair` | Đúng INVALID/TECHNICAL_ERROR đã chỉ định | Hash outcome cụ thể, chẩn đoán, hash bản sửa và receipt hồi quy; không retry nội bộ |
| `rerun` | Tất cả 3763 trong series mới, chia attempts có giới hạn | Không lấy completion series trước; thay identity bắt buộc series mới |

Khác recovery160 lịch sử: đường fulltrain cố ý yêu cầu repair tường minh cho
consumed technical error. INVALID durable vẫn là việc cần điều tra, có remedy
và lineage; không coi là lỗi đã giải quyết. Bản ghi kết quả sửa không ghi đè
bản gốc. Trạng thái gần nhất trong **series vận hành được chỉ định** chỉ phục
vụ scheduling, không là lựa chọn khoa học. Không tìm latest/best series.
Mọi plan có `scientific_selection=PENDING`, `pooling_allowed=false`.

History là chain có `parent_history_sha256`, run/attempt/series identity,
cohort và raw/evidence hashes. Duplicate IDs/attempts, thiếu ancestor, đổi input,
đổi identity cùng series hoặc lặp consumed ID ngoài repair đều bị chặn.
Trước rehearsal resume, mỗi ancestor phải hiện diện trong workspace và khớp
projection đã kiểm; summary tự khai không đủ. Import sealed ZIP vào thư mục
run mới bằng `import_attempt`: kiểm outer SHA trước bounded member verification
và extraction, không overwrite. Giữ mọi archive/receipt gốc; không xóa lock.
Khóa chỉ cùng workspace, không distributed exactly-once giữa các VM.

`recover` kiểm plan bằng cách dựng lại từ cohort/history, kiểm sealed directory,
native/start marker, raw identity/hash và strict parser. Raw hợp lệ chưa kịp
result được phục hồi thành projection mới; raw/result mâu thuẫn hoặc checksum
sai chặn. Native call dang dở không có raw thành TECHNICAL_ERROR/INTERRUPTED;
load fail trước start giữ NOT_ATTEMPTED và failure riêng. Parse exception có
result TECHNICAL_ERROR giữ lỗi, không tự nâng SUCCESS từ raw. Nonfinite giữ
technical error. Mất điện/ENOSPC có thể ngăn ZIP/final receipt; giữ partial
bytes và reservation, đối soát trước repair. Không hứa export mọi hard kill.

Nguyên nhân là phân loại vận hành từ **evidence đã cung cấp**, không suy luận
nguyên nhân thật của 25/5 INVALID: load/environment, OOM, timeout, pipeline,
interrupted, INVALID và UNKNOWN. Thiếu bằng chứng giữ UNKNOWN. Sửa prompt,
parser, generation, preprocessing, precision/model hoặc runtime identity yêu
cầu version/series riêng và O2 comparability; không dùng GT cứu nhãn hoặc
regex bóc nhãn từ prose/fence. INVALID còn sau sửa là negative result có thật.

## API và tái lập CPU

Từ repository root, Python3.11+, stdlib, không dependency mới:

```console
python -B -m unittest discover -s tests -p test_fulltrain.py -v
python -B -m unittest discover -s tests -p test_fulltrain_notebooks.py -v
python -B -m scripts.prepare_fulltrain --output data/processed/issue167/preparation-01 --max-calls 160 --max-seconds 600
```

CLI tạo cohort/plan **synthetic** cho ba ứng viên, đầy đủ 3763 statuses,
receipt môi trường/commit/lệnh và ZIP/SHA256; zero model calls. Cap ở lệnh là
test parameter, không phê duyệt O5 hoặc chuyển giới hạn160 thành quyền full.
Dùng output mới mỗi lượt. Không sử dụng con số fixture trong luận văn.

Luồng API (xem tests để có fixture chạy được):

1. `validate_cohort(cohort, pinned_projection_sha256)`;
   `same_cohort({model_key: cohort, ...})` kiểm exact ba projection.
2. `plan(cohort, cohort_sha, identity, history, history_sha, action=...,
   series_id=..., run_id=..., attempt_id=..., max_calls=..., max_seconds=...)`.
   Cap1..3763, time1..43200 là giới hạn phần mềm; O5/O6 còn phải duyệt giới hạn
   thực tế. Plan luôn có3763 rows, `scheduled_ordinals` và deferred riêng.
3. Repair truyền `repair={targets: {sample_id: failed_record_sha256},
   fix_sha256: ..., regression_sha256: ..., diagnosis: ...}`. Các reference
   này là hồ sơ chuẩn bị, không chữ ký khoa học hoặc grant.
4. `rehearse(work, synthetic_bundle, cohort, plan, history, test_factory)`
   chỉ chấp nhận fixture byte chính xác. Một cached load/attempt, raw trước
   parse, checkpoint mỗi call; dừng technical failure/time/cap, không retry.
5. `recover` / `import_attempt` → history entry mới; giữ history cùng series
   cho resume/repair hoặc mở series mới cho rerun. Không dùng historical
   report có format khác làm history mới bằng cách đổi schema.

Legacy Qwen V4, Recovery224, InternVL RECOVERY, MiniCPM INITIAL và smoke/rerun
giữ riêng. Import legacy thật cần exact O2 selection/representation và custody
bridge đã review, không tạo dữ liệu từ các counts đã báo. Task này không đọc
raw/GT thật để tạo bridge receipts hoặc giả hashes còn thiếu.

## Notebook/preflight và release gates

Builder hiện có được mở rộng:

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref <committed-runtime-SHA> --fulltrain-prep-only
```

Sinh ba `SafeShift_FULLTRAIN_PREP_{qwen3,internvl35,minicpm4}.ipynb`.
Builder kiểm từng byte source trong commit, compile cell, outputs rỗng;
bootstrap/extraction và artifact export dùng lại hệ thống hiện có.
Notebook chỉ xuất preparation receipt **BLOCKED**, không đo môi trường Kaggle,
không provision package, đọc Input/weights hoặc cấp phát scratch. Local cell
tests chạy child `-S` trong thư mục rỗng, không site-packages. Không upload hay
chạy Kaggle trong task này.

`fulltrain_preflight.inspect_receipts` kiểm cấu trúc/hash/binding của receipts
đã được một preflight có quyền cung cấp: source, marker duy nhất, cohort/order,
checkpoint allowlist, Python/ABI/pins, native processor, decode3763, mount/devices,
allocated bytes/write/fsync/cleanup, dung lượng/RAM/quota/time, GPU/driver/
visibility và CUDA FP16 đúng child runtime. Thiếu check → NOT_RUN/BLOCKED;
PASS word không đủ. `receipt_reported_levels` chỉ là nội dung được cung cấp,
không nâng `levels` measured hoặc release từ self-authored evidence.

G0 BLOCKED O2–O6; G1/G3 CPU build/test có receipt riêng; G2 cuối runtime/Input
NOT VERIFIED; G4/G5 Kaggle/real weights/inference NOT RUN; G6 BLOCKED.
Không tái định nghĩa G0–G6 ở [knowledge base](KAGGLE_FAILURES_AND_RELEASE_GATES.md).
Notebook cũ được tái sinh do dùng chung engine/source payload; runtime refs mới
là release mới **chưa qualify**, không chuyển authority/evidence run cũ sang
HEAD mới. Checkpoint/model/science locks không đổi, bản cũ vẫn ở commit lịch sử.

## Bàn giao và những điều còn BLOCKED

- O2: exact source/series selection, legacy mapping và scientific comparability.
- O3: final roster/roles; không tự tuyển ứng viên thứ tư.
- O4: rights/custody của manifest, ảnh, private history và export thực tế.
- O5: cap/budget/stopping/precision và selection policy thực tế.
- O6: exact source/runtime/notebook/Input/model/run/attempt grant mới.
- Final-runtime native/Kaggle preflight, weights/inference/export verification,
  ChatGPT GitHub review, Antigravity audit, quyền merge và hậu merge.

Counts gốc được **cung cấp bởi Issue167/tài liệu**, không recount trong task:
Qwen3539 SUCCESS/1 TECHNICAL_ERROR/223 NOT_ATTEMPTED; InternVL135 SUCCESS/25
INVALID trong160; MiniCPM155 SUCCESS/5 INVALID trong160. Hai peer còn3603 ảnh
ngoài pilot. Không có claim3763 SUCCESS, accuracy/Macro-F1 hoặc baseline mới.
Test counts, final HEAD và file inventory nằm trong cùng Draft PR; dừng ở đó.
