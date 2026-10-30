# InternVL3.5 / MiniCPM-V-4 — Owner Save & Run All

30/10/2026, Asia/Bangkok. Environment repair base **PR #154 MERGED**:
`39ec489403753ada10f4924c4b0d6077e027f5e1`, đã kiểm remote main.
PR này cần ChatGPT kiểm GitHub và audit độc lập trước merge.
Task chỉ synthetic CPU; GPU/real weights/behavior vẫn UNVERIFIED.

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

Sau review/audit và merge, chạy notebook preflight riêng trước; có thể lặp lại
preflight vì không tạo Owner slot/attempt. Dùng cùng Inputs/Internet/T4×2 như
notebook160. Download ZIP/sidecar, đọc `preflight.json`: từng gate
PASS/BLOCKED/NOT_RUN. `PRELOAD_CHECKS_PASS_MODEL_UNVERIFIED` chỉ là admission
trước load; không READY hoặc model-fit/quality/HNLO PASS. Không tự launch160.

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
