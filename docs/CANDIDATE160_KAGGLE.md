# InternVL3.5 / MiniCPM-V-4 — Owner Save & Run All

30/10/2026, Asia/Bangkok. Environment repair base **PR #154 MERGED**:
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
Exact Git export kiểm cuối: `2306aecb280acfedd1dd11523f14b60f892c771f`;
cập nhật sau đó chỉ tài liệu/receipts. Cả10 notebook (gồm4 candidate) khớp
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
