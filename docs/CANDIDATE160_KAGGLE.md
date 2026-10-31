# InternVL3.5 / MiniCPM-V-4 — Owner Save & Run All

## Trial kỹ thuật mới: MiniCPM resampler FP32, chưa cấp quyền production

Owner đã cho phép ngoại lệ hẹp trong [quyết định mới](research/DECISIONS.md#dec-20261031-minicpm-resampler-fp32-technical-exception).
HOLD phía dưới là lịch sử; chỉ score/softmax/value product trong resampler dùng
FP32, weights FP16/model/checkpoint/ảnh/C1/eager/parser/HNLO không đổi. Dùng
notebook riêng `SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb`,
không đổi notebook160 thành full-run. Route mới chỉ1 ảnh ordinal0/1 native call/
3600 giây, output candidate160_smoke_resampler_fp32_v1 và series/config/hash
riêng. Không attach smoke như production history, không resume/pooling với FP16.

Codex kiểm local/native CLI trước, rồi submit private Kaggle với cùng
`nguynanhtn/safeshift-pilot-input`, Output `nguynanhtn/safeshift-prepare-minicpm4`,
container target cũ, T4x2/Internet ON. Tải vào thư mục mới, giữ mọi FAIL/PASS.
Receipt cuối phải kiểm actual weights/inference/finite/effective ID/counters/
raw/parser/HNLO handling/cleanup/ZIP/SHA256. Chưa có evidence thật cuối thì
NOT VERIFIED; CPU/preflight không đủ. [Hồ sơ trial](research/MINICPM4_FP32_ATTENTION_TECHNICAL_20261031.md).
Ngay cả khi trial PASS: giữ Draft PR156, báo ChatGPT kiểm GitHub rồi quyết định
Antigravity audit; chưa được chạy chính thức160 hoặc dùng làm baseline khoa học.

## Quy trình hiện hành PR156: Codex kiểm Kaggle thật trước bàn giao

Nguồn: [Owner31/10](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6539523161),
áp dụng cho mọi notebook Kaggle. Các hướng dẫn bên dưới về Owner chạy preflight
đầu tiên/task chỉ CPU là snapshot trước chỉ thị này, không đủ điều kiện release.

**Trạng thái thực tế31/10: BLOCKED.** InternVL đã qua weights/inference/raw/ZIP
smoke1 ảnh nhưng strict parser giữ INVALID/HNLO unaligned. MiniCPM nạp weights
được nhưng native attention FP16 overflow; hai diagnostic giữ nguyên cấu hình
đã đo nguyên nhân. Không chạy production160 để lặp lỗi này. Xem
[bằng chứng](research/CANDIDATE160_KAGGLE_VERIFICATION_20261031.md) và
[quyết định còn PENDING](research/MINICPM4_NUMERICS_PENDING_DECISION_20261031.md).

Codex dùng Kaggle CLI chính thức trong virtual environment riêng (Python3.11+).
`kaggle --version`, `kaggle kernels push --help` xác minh phiên bản/cú pháp;
`kaggle kernels list --mine`, `kaggle datasets list --mine`, `kaggle quota`,
`kaggle kernels status <owner/slug>` kiểm read-only trước submit. Nếu chưa auth,
Owner tự chạy `kaggle auth login` qua browser theo [tài liệu chính thức](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md#authentication).
Không dán token/password/kaggle.json vào chat; không ghi credentials trong repo.

Notebook cuối mặc định `candidate160_action = "technical_smoke"`; upload chính
file này, không chỉnh source/locks. Private kernel mới chỉ dành smoke, cùng
dataset `nguynanhtn/safeshift-pilot-input`, đúng checkpoint Notebook Output của
model, Internet ON, accelerator `NvidiaTeslaT4` (T4×2). Không attach TEST hoặc
dataset gốc đầy đủ. Metadata `is_private=true`; không thay quyền nguồn cũ.
`kaggle kernels push -p <ignored-staging-folder> --accelerator NvidiaTeslaT4 -t 3900`
submit một lần; ghi version, notebook SHA256 và source SHA256 trước upload.
Theo dõi status có giới hạn; không submit trùng khi job còn QUEUED/RUNNING.
`kaggle kernels output <owner/slug/version> -p <new-private-evidence-folder>`
tải bằng chứng vào vị trí mới, không dùng --force ghi đè evidence cũ.

Smoke vẫn kiểm manifest/order/hash/decode160 và checkpoint/shards/source/pins/
storage/driver/CUDA như production, nhưng chỉ gọi ảnh ordinal0 theo manifest:
max1 native call,1 load,3600 giây gồm setup. Sample ID/hash/kích thước/lý do
trong technical_selection.json; output ở candidate160_smoke, không production
execution/reservation/history/scientific metrics. Khóa tiến trình dùng chung
chỉ để ngăn duplicate; không consumption production. Không attach smoke Output
làm production history. Preflight giữ chức năng diagnostic riêng.

Phải kiểm ZIP/checksums/sidecar và `.smoke-result.json`: TECHNICAL_SMOKE_PASS
chỉ khi actual native model/weights/GPU/inference/raw/parser/HNLO/custody,
controller và cleanup/export đều đạt. COMPLETE của Kaggle hoặc CPU preflight
không tự là PASS. Lỗi: giữ thư mục/ZIP/log/receipt, sửa cùng branch, thêm
regression, local integration và kiểm lại tối thiểu. Không retry vô hạn.
Không có GPU/Input/quota/auth → BLOCKED/NOT VERIFIED, không bàn giao READY.

**Owner chạy chính thức sau review/audit/merge:**

1. Chọn notebook đúng model và đúng authorized Inputs như smoke đã kiểm;
   dừng job cũ. Attach đủ production Outputs cũ để resume, giữ mọi marker.
2. Đặt `candidate160_action = "resume"` (hoặc `"rerun"` cho series mới160),
   giữ nguyên mọi cấu hình nghiên cứu. Save Version → Save & Run All.
3. Tải ZIP + SHA256 dù PASS/FAIL/partial, giữ private và gửi ChatGPT phân tích.

Codex không tự chạy full160. Scientific selection=PENDING/pooling=false;
một ảnh không chứng minh cả160, rare sizes, long-run OOM hoặc chất lượng.
Xem [bằng chứng mới](research/CANDIDATE160_KAGGLE_VERIFICATION_20261031.md).

## Hướng dẫn hiện hành — retry/resume31/10/2026

Main base `6252a7de91d9d98bd68a33b9bc13ae9888f2b9da`, sau PR155.
[Quyết định vận hành mới](research/CANDIDATE160_RECOVERY_DECISION_20261031.md)
thay khóa one-shot/no-retry cho đúng hai notebook Owner. Các phần phía dưới mục
“Snapshot trước thay đổi recovery” là lịch sử; cấm retry/resume/replacement2 ở
đó không áp dụng cho production v2 mới. Giữ mọi scientific/data/technical gates.

1. Sau review/audit/merge, chạy preflight riêng với cùng bundle/checkpoint,
   Internet ON/T4×2. Preflight không tạo execution/attempt/slot hoặc nạp weights;
   kiểm receipt cuối `.preflight-result.json` + ZIP + SHA256. Mức GPU tensor PASS
   không chứng minh model-fit. Production vẫn kiểm admission lại.
2. Mở notebook production đúng model. Giữ bundle160 TRAIN và checkpoint Inputs
   như đã khóa. Dừng phiên/job cũ trước khi khôi phục; không chạy hai jobs cùng
   model đồng thời. Không xin lại approval/grant/CONTINUE trong scope Owner.
3. Phiên Kaggle mới: attach toàn bộ Outputs cũ. Runtime nhận:
   `notebooks/<owner>/<slug>/data/processed/candidate160/<key>-<uuid>/`, thư mục
   run trực tiếp ở mount, hoặc evidence `<key>-<uuid>.zip` ở mount/parent chuẩn.
   ZIP phải nguyên vẹn với checksums; sidecar nếu có phải khớp. Giữ thư mục
   `attempts/`, history/markers và mọi partial/error. Không chỉ attach summary
   hoặc raw rời rạc, không sửa/xóa trạng thái cũ để vượt cổng.
4. **Save Version → Save & Run All**, `candidate160_action = "resume"` mặc định.
   Mỗi kích hoạt có ID mới. Chỉ ảnh chưa có durable raw/custody trong series
   hiện hành được gọi; INVALID hợp lệ cũng đã hoàn thành. Raw hợp lệ chưa có
   result được replay trong plan mới; không sửa file lịch sử. Không tự retry
   bên trong attempt; GPU/load/raw/resource/time error dừng để giữ evidence.
5. Khi cần chạy lại toàn bộ160 ảnh, đổi duy nhất cấu hình
   `candidate160_action = "rerun"` ở đầu code cell; Save & Run All tạo FULL_RERUN
   và series mới. Lần tiếp tục để `resume` sẽ tiếp nối series này, không lấy
   completion của baseline trước đó. Không đổi protocol/hash/model để sửa lỗi.
6. Download private ZIP + `.sha256.json` được in kể cả STOPPED/BLOCKED/partial.
   Nếu kill chưa kịp ZIP, giữ saved Output directory. Phiên sau attach lại đầy đủ.
   Không có ảnh/weights trong evidence ZIP; không publish raw/nhãn hoặc secrets.

`recovery_plan.json` ghi pending/durable ordinals và toàn bộ lineage/raw hashes;
`history_index.json` khóa snapshots/ancestors; `lineage_accounting.json` đếm
attempts/native calls theo run và toàn lịch sử. `model_load_attempt.json` phân
biệt lần thử load với native calls=0. Bản sao cùng run ID/hash chỉ tính một lần;
copies khác nhau, thiếu ancestor hoặc marker orphan → BLOCKED trước load.
`BLOCKED_RESERVED_NO_RETRY`, `CONSUMED`, UNKNOWN và `replacement1` cũ được nhập
nguyên trạng; không còn là khóa vĩnh viễn. Bổ sung đúng Output/evidence bị thiếu
rồi chạy lại, không cần approval thủ công hoặc xóa marker. Hai nhánh lịch sử
độc lập làm resume BLOCKED; explicit rerun tạo series mới giữ cả hai nhánh.

Mỗi attempt ≤160 calls, một call/ảnh được schedule, một load,12 giờ. Resume đã
đủ160 durable sẽ tạo evidence no-op, không setup/GPU/weights/model call. Lock OS
tự nhả khi supervisor/worker kết thúc; Linux child giữ lock nếu supervisor chết.
Lock này không liên lạc giữa VM Kaggle riêng biệt: Owner phải dừng job cũ và
cung cấp đầy đủ Outputs. Không claim global exactly-once khi không shared state.

**Scientific result selection=PENDING; pooling_allowed=false.** INITIAL,
RECOVERY, FULL_RERUN và mỗi series giữ riêng; completion union chỉ phục vụ
scheduling kỹ thuật. Không chọn best/first/latest cho nghiên cứu, không ghép
metric/AUROC hoặc tự nâng qualification. Metrics trong summary chỉ thuộc attempt
đó; decisions khoa học mới phải được ghi trước khi áp dụng.

Manifest/order160 TRAIN, model revisions, checkpoint/source locks, C1, HNLO,
parser/nhãn/metric/protocol và quyền dữ liệu không đổi. Task mã nguồn không GPU,
Kaggle, weights hoặc attempt thực nghiệm. [Bằng chứng CPU mới](research/CANDIDATE160_RECOVERY_CPU_20261031.md).
Dừng ở **một Draft PR** cho ChatGPT kiểm GitHub; Antigravity audit độc lập bắt
buộc trước merge. Không tự merge hoặc coi CPU synthetic là GPU PASS.

CPU acceptance: export `afbf030` có347 tests =315 PASS/32 SKIP/0 lỗi;10 notebooks
khớp builder,15 recovery tests mới PASS; Windows11 focused/notebook/prefix checks
PASS. [Receipts/checksums](research/evidence/candidate160_recovery_20261031/index.json)
giữ cả lần kiểm đầu có2 assertion lỗi và correction chỉ trong tests. Runtime
`0f0d272c60c3a574814c1b0d3dc4a73ee169b30c`, candidate source SHA256
`f2b6af6d23869acea7ed7e6ee35162f7d2d1b9c83bc24c06d3040f1bfc2439cb`.
Không native opt-in/live pip/full Windows hoặc actual Kaggle/model fit ở Codex.

## Snapshot trước thay đổi recovery — không phải thủ tục hiện hành

31/10/2026, Asia/Bangkok; tiếp tục cùng Draft PR #155. Environment repair base **PR #154 MERGED**:
`39ec489403753ada10f4924c4b0d6077e027f5e1`, đã kiểm remote main.
PR này cần ChatGPT kiểm GitHub và audit độc lập trước merge.
Task chỉ synthetic CPU; GPU/real weights/behavior vẫn UNVERIFIED.

## Chỉ thị environment-first ngày 31/10/2026 — cùng Draft PR #155

[Owner directive](https://github.com/tantdna2/SafeShift/pull/155#issuecomment-6533181366)
yêu cầu kiểm môi trường trước khi thiết kế/phát hành notebook thực nghiệm.
Quy tắc đã được bổ sung append-only vào `AGENTS.md` trong Draft này; chưa
COMPLETE trên main. Mỗi HEAD mới cần ChatGPT kiểm GitHub và Antigravity audit
độc lập trước quyền merge riêng và xác minh hậu merge. Không tái sử dụng audit
hoặc quyền merge của HEAD cũ.

Bằng chứng sau là **OWNER_REPORTED** tại comment, không phép đo mới của Codex:

| Điều kiện | Điều đã được báo | Điều còn thiếu |
| --- | --- | --- |
| InternVL Input | Đúng1 marker trong `/kaggle/input/notebooks/<owner>/<slug>/`, có source/ và weights/ cạnh marker | SHA/allowlist/index/shards và load chưa được chứng minh |
| Python | Kernel3.13.15; worker3.11.9 không thấy ở các vị trí đã probe | Provision/venv/pins/ABI trong saved Kaggle session thực tế |
| Output | working19,50 GiB free, device1794 | Writability/fsync và cấp phát thật4 GiB hiện tại |
| Scratch | kaggle1048,77 GiB free, device56; tmp thiếu trong probe đầu | Safe creation/quyền/ghi/fsync/cấp phát28 GiB/cleanup, không dựa vào sự tồn tại tmp |
| GPU và mô hình | Chưa có GPU/driver/CUDA/weights/behavior/HNLO PASS từ screenshots | Toàn bộ live GPU/weight-load/model-fit/inference/scientific qualification |

Không đặt runtime vào working chỉ vì output còn19,50 GiB. Preflight đo devices
thực tế: khác filesystem cần28+4 GiB riêng; cùng device cần32 GiB cộng lại,
và xác nhận cấp phát đồng thời, không cộng dung lượng free hai lần.

Preflight v2 ghi inventory kernel/ABI/OS/kiến trúc/visibility và RAM/cgroup
trước provisioning; chặn host sai, source/ref sai hoặc Inputs không hợp lệ.
Runtime setup chưa là software PASS: child riêng kiểm actual pins/identity/NMS
ABI. Mỗi child receipt phải đúng schema/check/model/source/ref/status và đủ
evidence. Nguồn sai, receipt thiếu/partial/khác binding, package sai, hết budget,
allocation/quota/fsync/cleanup hoặc export sai đều không đủ admission.
GPU/driver được quan sát riêng; child CUDA chỉ chạy sau GPU và software admission.
Deadline12 giờ tính từ đầu preflight, không reset sau hash/provision.

Receipt tách sáu mức `ENVIRONMENT_OBSERVED`, `CPU_SOFTWARE_PASS`,
`LIVE_GPU_PREFLIGHT_PASS`, `WEIGHTS_LOADED`, `INFERENCE_VERIFIED`,
`SCIENTIFIC_QUALIFIED`. Preflight giữ ba mức cuối NOT_RUN/UNVERIFIED; CUDA tensor
PASS cũng chưa chứng minh load weights, peak RAM/VRAM hoặc chất lượng model.

- [InternVL notebook](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb)
- [MiniCPM notebook](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb)
- [InternVL preflight không tiêu lượt](../notebooks/SafeShift_CANDIDATE160_PREFLIGHT_internvl35.ipynb)
- [MiniCPM preflight không tiêu lượt](../notebooks/SafeShift_CANDIDATE160_PREFLIGHT_minicpm4.ipynb)
- [Quyết định môi trường và replacement incident](research/CANDIDATE160_KAGGLE_ENV_DECISION_20261030.md)
- [Quyết định Owner và thay đổi chính sách dừng](research/CANDIDATE160_OWNER_DECISION_20261030.md)
- [CPU acceptance và giới hạn](research/CANDIDATE160_OWNER_CPU_20261030.md)

Owner yêu cầu bỏ thủ tục xin phép lặp lại cho lượt thuộc quyền Owner.
Notebook mới dùng **Save & Run All là kích hoạt trực tiếp**. Không cần file
grant, reservation, approval refs hoặc CONTINUE. Execution record là nhật ký
máy gắn với chỉ thị Owner trong chat, không văn bản ký thay Research Lead.
Luồng grant/batch #153 giữ compatibility, không phải UI notebook mới.

## Thao tác trên Kaggle

Khi cần thông tin target thực tế, Owner dùng notebook preflight độc lập đã được
bàn giao/kiểm nguồn trước notebook thực nghiệm, với cùng Inputs/Internet/T4×2.
Không cần grant/CONTINUE hoặc xin lại quyền notebook đã được Owner cấp. Không
chạy production để phát hiện lỗi môi trường cơ bản. Preflight có thể lặp lại
vì không tạo Owner execution/slot/attempt; không tự launch160.

1. Mở đúng `SafeShift_CANDIDATE160_PREFLIGHT_<key>.ipynb` trong Kaggle session
   riêng. Attach cùng bundle160/checkpoint đã upload (Dataset hoặc Notebook
   Output); không đổi file/path/hash. Chọn Internet ON và T4×2.
2. Run All/Save & Run All **chỉ preflight**. Software pinned có thể được tải/cài;
   hash/decode Inputs, cấp phát tạm28+4 GiB, CPU empty meta/processor và CUDA
   FP16 tensor probe có thể chạy. Không nạp/tải weights hoặc gọi mô hình.
   Scratch session được dọn theo ownership marker; lỗi dọn giữ BLOCKED/evidence.
3. Download cả ZIP, `.zip.sha256.json`, và `.preflight-result.json` được in.
   File cuối phải có `evidence_export=VERIFIED`; checksum phải khớp ZIP.
   `preflight.json` bên trong ZIP còn ghi export PENDING do được seal trước
   export. Dùng receipt cuối để xét status; thiếu file cuối/ZIP/sidecar, checksum
   sai hoặc export partial đều BLOCKED. Giữ mọi bytes còn lại khi lỗi/hard kill.
4. Đọc `status`, `checks` và `levels` ở receipt cuối; gửi receipt/lỗi hoặc ZIP
   qua kênh private cho người review nếu cần thông tin thực tế. Không publish
   ảnh/weights/manifest nhãn/secrets. Mỗi check ghi PASS/BLOCKED/NOT_RUN và lỗi.
   `PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED` chỉ là admission trước load, không
   READY hoặc model-fit/quality/HNLO PASS. Output/caches lớn nằm ngoài Git.

Không có Kaggle preflight mới được chạy bởi Codex trong task này. Sau review,
audit và merge được cho phép riêng, notebook160 vẫn kiểm admission lại trong
saved session vì tài nguyên có thể thay đổi; receipt preflight không cấp retry.

Sau đó chạy riêng mỗi notebook160 đúng một lần trong saved session sạch:

1. Fresh Kaggle notebook, **T4 ×2**, Internet ON cho pinned software.
   Chỉ một saved job/model; không chạy interactive trước Save & Run All.
2. Attach bundle Owner đã upload: `pilot_manifest.json` và
   `images/000000.jpg` … `images/000159.jpg`.
3. Attach checkpoint Owner đã upload: `candidate_checkpoint_<key>.json`,
   `source/<revision>/` và `weights/`. Key: `internvl35` hoặc `minicpm4`.
   Marker: `{"schema":"safeshift-candidate160-checkpoint-v1","model":...}`;
   model dict từ `train_contract.model(key)` gồm id/revision/transformers/
   attention/remote_code. Đúng 13/15 source files allowlist, index + hai shards
   đúng size/SHA của lock #151. Không links/extra files hoặc downloader weights.
   Discovery nhận direct mounts, `datasets/<owner>/<slug>` và
   `notebooks/<owner>/<slug>`, tên file duy nhất; tối đa512 entries, độ sâu cố
   định. Checkpoint Notebook Output hiện có giữ nguyên source/weights, không
   chuyển Dataset hoặc tải lại nhiều GB. Layout chuẩn của sự cố Owner:
   `/kaggle/input/notebooks/nguynanhtn/safeshift-prepare-internvl35/`.
4. **Save Version → Save & Run All một lần.** Không sửa cell, SHA, model,
   revision, Python hoặc precision để vượt lỗi; không retry/resume/overwrite.
5. Download private ZIP và `.sha256.json` được in, kể cả failure/partial.
   Không publish raw/manifest/GT/checkpoint; không chạy lại khi mất archive.

Hai nhóm Inputs thường: bundle và checkpoint. Riêng sự cố InternVL FOUND_0,
attach thêm saved Output cũ nguyên vẹn, gồm `data/processed/candidate160/attempts/`
và evidence directory đã sealed của run cũ. Runtime tự kiểm nguyên nhân/bindings/
160 NOT_ATTEMPTED/attempts0/native_calls0/attempt_consumed=false trước khi tạo
duy nhất `replacement1`, cùng campaign/slot, UUID run/attempt mới và incident
hashes. Không sửa/xóa marker cũ. Thiếu/partial/consumed/unknown hoặc replacement
đã có → BLOCKED; không retry/resume/replacement2. Không có bằng chứng cũ đầy đủ
trong task Codex này nên chưa khẳng định run Owner đủ điều kiện.

Không cần authority Dataset hoặc
gõ run/attempt ID, threshold, driver allowlist/thời hạn. Sai Input → BLOCKED
trước model call. Không upload dữ liệu hoặc chạy Kaggle trong task code này.

## Phạm vi bất biến

| Thành phần | Khóa |
| --- | --- |
| InternVL | `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`; Transformers4.55.4 |
| MiniCPM | `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; Transformers4.51.3 |
| Manifest SHA256 | `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995` |
| Inventory SHA256 | `0a8a84e726e690622de311326680ecbbc4a04fa04a0a45ff14ff96412caae427` |
| C1 SHA256 | `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3` |
| Cohort | Exact160 TRAIN/thứ tự cũ; 80 L04/48 L01/24 L02/8 L03, không selector/supplement/TEST |
| Execution | Một load, batch1, FP16/eager/cuda:0, ≤160 native calls/model, không retry/resume/overwrite |

Giữ adapter/native generation/checkpoint/public locks #151, strict parser/C1/HNLO
và sáu notebook pilot cũ. Hai config hashes vẫn tách biệt:
`legacy_transport_config_sha256` là snapshot transport lịch sử;
`candidate_execution_config_sha256` là full config v2/effective candidate.
`raw.identity.config_sha256` vẫn alias transport. Full config và execution binding
được kiểm trước parser/recovery, không hoán đổi hash hoặc mô tả Phi thành candidate.

Chỉ áp dụng một lượt/model trong campaign Owner, bundle TRAIN/checkpoint đã upload.
Không cấp quyền bên thứ ba, TEST, annotation mới, FULL TRAIN, model/nguồn khác
hoặc khoa học/roster mới. Cần quyền thực có cho tài nguyên ngoài quyền Owner;
notebook không chứng thực quyền pháp lý của upload.

## Kích hoạt, nhật ký và chống trùng

`launch_owner(..., owner_start=True)` được gọi từ cell shipped. API thiếu
activation rõ ràng từ chối. Tự tạo execution schema riêng, UUID run/attempt,
source/ref/config/manifest binding, thời gian/hạn và slot cố định theo
campaign/model/revision/cohort. Không tạo grant, G0/T0/O3, chữ ký, external ledger
ref hoặc Lead approval giả. Các quyết định khoa học/academic khác giữ trạng thái cũ.

Trước private inputs, exclusive O_EXCL+fsync marker:
`data/processed/candidate160/attempts/owner_slot_<slot_sha256>.json`.
UUID/source/ref mới không đổi slot. Giữ marker cả khi admission notebook160
BLOCKED; không release/resume/retry. Preflight riêng không tạo marker. Ngoại lệ
incident FOUND_0 đủ sealed evidence mới tạo một replacement1 riêng, giữ slot cũ.
Kiểm lại marker/execution/source/input trước consume.
Ghi consumed marker trước worker; lỗi create/fsync không rõ → UNKNOWN_DO_NOT_RETRY.
Terminal log tự ghi, không cần Owner ký/cập nhật permission record thủ công.

Cùng output root chặn duplicate/concurrent bằng exclusive create. Attached saved
Outputs cũ được kiểm marker ở mount root hoặc
`data/processed/candidate160/attempts/` (direct, datasets hoặc notebooks/owner/slug),
kể cả marker RESERVED/không đọc được. Không quét cây ảnh/weights.
**Giới hạn:** filesystem ephemeral không phải distributed ledger. VM mới không
attach lịch sử, concurrent VM hoặc layout lịch sử khác không có bằng chứng
toàn cục để chặn. Owner chỉ tạo một saved job/model, không tạo session thay thế
sau lỗi/mất VM hoặc xóa marker. Không tuyên bố global exactly-once.

## Các cổng kỹ thuật vẫn bắt buộc

SHA256 embedded runtime/Git ref, C1, hai config hashes, public source, checkpoint
index/shards, manifest/membership/order và ảnh phải khớp. Decode/RGB160 ảnh trước
consumption; hash lại trước native call. Không tải weights.

Kernel stdlib; worker CPython3.11.9 Linux x86_64 riêng, venv/pip bootstrap
hash-locked; Torch2.6.0+cu124/vision0.21.0+cu124, CUDA12.4, exact pins/no extra
libraries, pip check/freeze/native CPU ABI. Thiếu đúng interpreter có sẵn thì
provision từ python-build-standalone20240726 đã khóa URL/size/SHA256 tại
`configs/candidate160/python3119.json` (29.713.170 bytes). Kiểm safe extraction,
stdlib và venv/libpython trước dùng; lỗi download/hash/runtime → BLOCKED.
Không thay LD_LIBRARY_PATH hoặc dùng Python3.13 làm worker.
Hai physical T4, GPU0≥14GiB free trước load, GPU1 không pooled/sharded.
Child chỉ thấy GPU0 compute7.5; CUDA FP16 probe trước consume và kiểm lại trong
actual worker. Per-image memory/headroom receipts giữ nguyên.

Engineering settings công khai để review: thay driver allowlist chưa quyết định
bằng CUDA12 Linux compatibility floor525.60.13 + measured child probe, không
khẳng định mọi driver trên floor đều chạy model. Disk admission cũ28GiB scratch
+4GiB output/32GiB nếu chung filesystem giữ nguyên. Live minima: RAM/cgroup4GiB,
scratch/output1GiB mỗi nơi, GPU0 free256MiB sau load/trước call. Đây là reserve
kỹ thuật của implementation, không scientific thresholds hoặc bảo đảm peak fit.
Hết12 giờ từ bắt đầu supervisor/setup dừng, không gia hạn.

## Chính sách dừng thay đổi — cần reviewer đánh giá trước merge

Luồng Owner không dùng behavior/support thresholds chưa được quyết định.
Không điền số permissive để giả thành policy đã duyệt. Mỗi call giữ INVALID,
raw sequence repetition, label counts và conditional valid GT Normal/hazard
counters theo code cũ; replay custody mỗi call và đối soát toàn bộ cuối lượt.
Ghi technical decision riêng, không giả Lead CONTINUE.

Dừng ngay khi lỗi kỹ thuật/load/OOM/decode/raw/request/token/config/replay/custody,
NaN/Inf, resource hoặc deadline. INVALID/repetition/dominance/false-safe/false-alarm
**chỉ quan sát**; không scientific early stop hoặc dừng vì thiếu support sớm.
Behavior kém có thể tiêu đủ160 calls; COMPLETED không là quality PASS.
Đây là thay đổi so với #153 để review, chưa phải scientific protocol approval.
Full result review/qualification và HNLO evidence vẫn riêng, không cứu parser/score.

## Archive và tái lập CPU

Archive gồm owner execution/slot/consumption log, source/config/dependency receipts,
manifest,160 accounting (SUCCESS+INVALID+TECHNICAL_ERROR+NOT_ATTEMPTED=160),
request/native IDs/raw/logits trước parser, tokenizer, checkpoints, technical
decisions, behavior observations, summary/recovery/member checksums; không ảnh/weights.
Kiểm ZIP CRC/exact member SHA bằng `safeshift.pilot.artifacts.verify_archive`;
outer SHA phải khớp sidecar. Import vào directory mới, `train_run.recover`
đối soát manifest/execution. Hard kill/disk failure/VM loss có thể chỉ còn partial
evidence; không hứa ZIP đầy đủ và không retry.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref <metadata.runtime_ref>
python -B -m unittest discover -s tests -v
python -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public-source> --index <public-index> --output data/processed/owner160/internvl-new
python -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public-source> --index <public-index> --output data/processed/owner160/minicpm-new
```

Native CPU tests chỉ dùng pinned stack/cache public đã có, empty/meta loader,
160 ảnh tổng hợp/scripted logits; network/CUDA/real forward/weights bị chặn.
Không nhận synthetic behavior là chất lượng thật. Worksheets và
[runbook #153](https://github.com/tantdna2/SafeShift/blob/fc1e454212455685e1775601ebfd6aab9535c932/docs/CANDIDATE160_KAGGLE.md)
là snapshot lịch sử, không thủ tục bổ sung cho hai notebook Owner này.

## Nghiệm thu environment repair — 30/10/2026

Runtime commit `e55aab81f66c81d3e295f9065ecec1b4fdb23ad0`, embedded source SHA256
`c01902bc0b96e1aa89159311e0ae48417b72e99a897ec24b1d96da628ff2853b`.
Exact Git export của lần bàn giao30/10: `2306aecb280acfedd1dd11523f14b60f892c771f`;
HEAD `bf45a9766000582d67538278c5b848f7bcf8e242` lúc đó chỉ thêm tài liệu/receipts.
Đây là bằng chứng lịch sử, không tự áp cho runtime mới31/10. Cả10 notebook (gồm4 candidate) khớp
deterministic builder, payload/hash/pins, cells compile và không execution output.

| Kiểm tra | Kết quả | Giới hạn |
| --- | --- | --- |
| Full stdlib suite, exact Linux export | 324 =292 PASS +32 SKIP,0 FAIL/ERROR | Native opt-ins15/Phi6/Smol9/live pip1/Windows junction1 tách riêng |
| Windows environment/incident suite | 13 =9 PASS +4 symlink SKIP | Gồm replacement160 tổng hợp và chặn lần chạy tiếp theo |
| Windows notebook suite | 4/4 PASS | Cells thật trong subprocess CPU, hardware commands bị chặn; preflight chạy lặp không slot |
| Standalone production software, cả hai model | PASS | CPython3.11.9 Linux x86_64/stdlib/venv, exact cu124 distributions, pip check/freeze, compiled CPU NMS |
| Production native meta/processor, cả hai model | 8 synthetic sizes/model PASS | Empty-state loader, không weights/model forward/CUDA |
| Native suite trong exact export, production cu124 worker | InternVL15/15 +MiniCPM15/15 PASS,0 SKIP/FAIL/ERROR | Gồm160 ảnh tổng hợp/model; native processor/generation với scripted logits, raw/replay/archive và negative cases |

[Receipts nhỏ và checksum index](research/evidence/candidate160_env_20261030/index.json)
giữ exact source hashes, phiên bản thực và test outcomes; không private data,
ảnh, runtime binaries hoặc raw model output. Full stdout/logs ở ignored
`data/processed/candidate160-env-audit/`, không phải Kaggle evidence.

Full suite bao phủ path/marker/source/shard admission, cùng/khác filesystem,
allocation/quota/fsync/cleanup, live RAM/cgroup/disk/VRAM limit doubles,
failure/partial/archive, consumed/unknown/replay, raw-before-parse và160
accounting/order cho cả hai model. Không coi simulated CUDA receipt là GPU PASS.

BASE có lỗi test sẵn: `protected_source_lock.json` khóa AGENTS từ trước #154
(`aa2f183…`), trong khi chính BASE có `ad4309e…`. Đã tái hiện targeted test trên
export BASE. Không sửa lock lịch sử hoặc AGENTS; assertion ghi riêng exact
AGENTS của main đã xác minh, còn các protected scientific/runtime bytes giữ nguyên.
Lượt full trước correction324 có1 FAIL/32 SKIP; lượt cuối ở snapshot trên0 lỗi.

Development audit cũng phát hiện PBS venv copies thiếu libpython (đã sửa và
kiểm lại). `/tmp` local WSL là tmpfs3,9 GiB gây ENOSPC khi cài software; nghiệm
thu cuối dùng filesystem Linux đủ chỗ, không giảm pins/reserves. NTFS có terminfo
case collisions nên kiểm archive trên Linux. Các rehearsal cũ bị thay thế hoặc
dừng được giữ logs, không cộng vào counts PASS. Không phải Kaggle attempts.

```console
python -B -m scripts.rehearse_candidate160_environment --key internvl35 --snapshot <public-source> --scratch-root <linux-scratch> --output data/processed/env-proof/internvl-new
python -B -m scripts.rehearse_candidate160_environment --key minicpm4 --snapshot <public-source> --scratch-root <linux-scratch> --output data/processed/env-proof/minicpm-new
python -B -m scripts.check_notebook_release --runtime-ref 2306aecb280acfedd1dd11523f14b60f892c771f --output data/processed/env-proof/release-new.json
```

Native suite dùng `test_candidate_native`, public snapshot/index đã khóa và
worker3.11.9/cu124 nói trên, threads2. Legacy `rehearse_candidate_cpu.environment`
chỉ nhận CPU wheel; riêng nghiệm thu cu124 thay validator đó bằng production
`train_runtime.software` (exact distributions/identity/compiled CPU ABI).
Các generation tests và network/CUDA/weights/real-forward guards giữ nguyên.
Từ exact export với `PYTHONPATH=.:tests`, các biến
`SAFESHIFT_CANDIDATE_KEY`, `SAFESHIFT_CANDIDATE_SNAPSHOT`,
`SAFESHIFT_CANDIDATE_INDEX`, `SAFESHIFT_WORKER_PYTHON`, `SAFESHIFT_RUNTIME_ROOT`,
`PYTHONNOUSERSITE=1`, chạy đoạn sau bằng worker cho từng model:

```python
import torch, unittest
from scripts import rehearse_candidate_cpu as old
from safeshift.candidates.train_runtime import software
def production_cpu_environment(key):
    receipt = software(key)
    torch.set_num_threads(2)
    return receipt
old.environment = production_cpu_environment
unittest.main(module="test_candidate_native", verbosity=2)
```

**Còn chưa kiểm:** Kaggle allocation28+4 GiB thật, driver/T4×2/isolated CUDA
FP16 thật, load/peak RAM/VRAM của checkpoint,160 real predictions/behavior/HNLO,
và eligibility incident từ private Output cũ. Thiếu điều kiện thực tế thì BLOCKED.
Không grant/merge/GPU/data run hoặc independent audit được thực hiện ở Codex.

## Nghiệm thu tiếp tục31/10 — environment-first, cùng PR #155

Bắt đầu từ HEAD `bf45a9766000582d67538278c5b848f7bcf8e242`, BASE main giữ nguyên
`39ec489403753ada10f4924c4b0d6077e027f5e1`. Runtime mới
`f679e3153a1418cd521d1875cfa797b5aded8570`, source SHA256
`ed5e9f677efac015990d3fceb35ef1057cc4ac52dae468afb6c5491713bc47de`;
exact tested snapshot `0363db4976f39f8c4249ab84a7c54986f41e1e99`.
Các thay đổi sau snapshot này chỉ docs/receipts; không dùng kết quả30/10 để tự
chứng nhận HEAD mới. Không có lỗi test cuối nào được waive.

| Kiểm tra mới | Kết quả | Bằng chứng và giới hạn |
| --- | --- | --- |
| Full stdlib suite, exact Linux export | 332 =300 PASS +32 SKIP,0 FAIL/ERROR | Cả10 notebook khớp builder/payload; native opt-ins15/Phi6/Smol9/live pip1/Windows junction1 chưa chạy trong suite này |
| Windows focused | 43 =38 PASS +5 SKIP,0 FAIL/ERROR | Environment/incident/preflight/notebook/protected BASE/storage;4 symlink +1 Linux allocation API không có trên Windows |
| Actual worker CLI, InternVL3.5 | PASS | Exact3.11.9/cu124 distributions, compiled CPU NMS, envelope/source binding và meta/native processor8 synthetic sizes |
| Actual worker CLI, MiniCPM-V-4 | PASS | Cùng kiểm chứng, đúng riêng pins4.51.3; network/CUDA/weights/real-forward bị guard chặn |

[Index/receipts mới](research/evidence/candidate160_envfirst_20261031/index.json)
giữ hashes/code/test outcomes/versions và scope CPU; không chứa máy cá nhân,
dataset, weights hoặc raw model output. Logs gốc ở ignored
`data/processed/candidate160-envfirst-20261031/`. Meta/processor function không
đổi từ30/10; không lặp native160 suite trước đó để nhận thành bằng chứng GPU.

Các negative tests bao phủ marker thiếu/trùng/layout sai, source/weights sai,
Python/setup/download/hash/package lỗi, receipt thiếu/sai status/check/model/
source/ref/evidence, source/ref/deadline từ đầu, interrupt, GPU/driver/CUDA
failure doubles, đồng thời allocation cùng/khác device/quota/fsync, scratch
partial/cleanup, export/sidecar failure dù mọi check trước đó PASS, và preflight
lặp. Mọi trường hợp đều assert không slot/attempt/model call. Test hồi quy owner,
incident/replay/custody/raw/HNLO vẫn chạy trong full suite; code của chúng không đổi.

`AGENTS.md` chỉ append quy tắc mới: test đối chiếu Git object `bbbd351e…`
với lock lịch sử và object BASE `39ec489…` với SHA riêng, rồi kiểm nguyên prefix
BASE trong file hiện tại. Không sửa quá khứ/source lock để cho hash mới đi qua.
Một development test inventory ban đầu trên Windows bị guard chặn lệnh OS của
stdlib platform; đã sửa double OS của test, chạy lại PASS. Không phải Kaggle attempt.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref f679e3153a1418cd521d1875cfa797b5aded8570
python -B -m unittest discover -s tests -v
python -B -m scripts.check_notebook_release --runtime-ref 0363db4976f39f8c4249ab84a7c54986f41e1e99 --output data/processed/envfirst-proof/release-new.json
```

Worker CLI qualification dùng cùng worker/env do `prepare_runtime` tạo:
`PYTHONPATH=<repo>`, `PYTHONNOUSERSITE=1`,
`SAFESHIFT_WORKER_PYTHON=<venv>/bin/python`, `SAFESHIFT_RUNTIME_ROOT=<venv>`,
`CUDA_VISIBLE_DEVICES=""`, dedicated `HF_MODULES_CACHE` và offline public cache.
Với output mới riêng từng model, chạy hai chế độ sau (không `--cuda` trong CPU audit):

```console
<worker> -B -m safeshift.candidates.train_preflight --worker --key <internvl35-or-minicpm4> --repo <repo> --output <new-output> --source ed5e9f677efac015990d3fceb35ef1057cc4ac52dae468afb6c5491713bc47de --ref f679e3153a1418cd521d1875cfa797b5aded8570 --software-only
<worker> -B -m safeshift.candidates.train_preflight --worker --key <internvl35-or-minicpm4> --repo <repo> --output <new-output> --source ed5e9f677efac015990d3fceb35ef1057cc4ac52dae468afb6c5491713bc47de --ref f679e3153a1418cd521d1875cfa797b5aded8570 --snapshot <locked-public-source>
```

**Vẫn chưa kiểm:** target Kaggle hiện tại và allocation28+4 GiB, T4×2/driver/
CUDA FP16 thực tế, real weight loading/peak fit, inference/behavior/HNLO và
private incident eligibility. Preflight thực tế có thể BLOCKED; không cam kết
không còn lỗi GPU/model. Quy tắc mới vẫn DRAFT/PENDING review/audit/merge/hậu merge.
