# InternVL3.5 HF / MiniCPM-V-4 — Kaggle 160 PREP

29/10/2026, Asia/Bangkok. **BLOCKED cho thực nghiệm.** Owner yêu cầu chuẩn bị
hai notebook, không cấp quyền đọc dữ liệu, checkpoint hoặc dùng GPU. Không chạy
Kaggle, tải weights hoặc mở private TRAIN/TEST trong task này. Công cụ hiện tại
không tạo được phiên chat Codex mới; nhánh/worktree độc lập bắt đầu đúng main
`95eb4e8801ea746e1a760b9d529920bffb3c26cb`, sau PR #151 đã merge.

- [InternVL notebook](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb)
- [MiniCPM notebook](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb)
- [Builder](../scripts/build_candidate160_notebooks.py)
- [Contract pending, grant=null](../configs/candidate160/preparation.json)

Đây là executable PREP cần review, không `READY_FOR_GPU`, không qualification
classifier/peer/HNLO. Không mở FULL TRAIN, chọn slot 3, chuyển grant cũ hoặc thay
C1/parser/preprocess/precision/generation để đạt PASS. Sáu notebook cũ và adapter
PR #151 giữ nguyên bytes; không đổi protocol, split, nhãn hoặc metric.

## Nguồn và manifest chung

| Thành phần | Khóa / mức bằng chứng |
| --- | --- |
| InternVL | `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`; Transformers 4.55.4 |
| MiniCPM | `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`; Transformers 4.51.3 |
| C1 | SHA256 `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3` |
| Manifest | SHA256 `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995` |
| Dimension inventory lịch sử | SHA256 `0a8a84e726e690622de311326680ecbbc4a04fa04a0a45ff14ff96412caae427`; chỉ dùng khóa, không mở inventory |
| Cohort | 160 TRAIN IDs/thứ tự gốc; Level04=80, Level01=48, Level02=24, Level03=8; không supplement |
| Checkpoint/source | Exact file allowlists/index/shard size+SHA trong `configs/cpu_g2_g3/`; loader PR #151 kiểm lại trước load |
| Runtime | Full Git SHA + từng embedded file SHA trong notebook metadata/payload; source commit có trước generated notebook commit |

[Receipt ChatGPT #138](https://github.com/tantdna2/SafeShift/pull/138#issuecomment-6461830997)
xác nhận metadata và thứ tự, **không** independently audit ZIP/image bytes.
Task này chỉ đọc receipt công khai, không xác minh lại private manifest/ảnh.
Không công khai danh sách ID/GT hoặc dựng lại selector. Sau **quyền mới**, notebook
yêu cầu đúng manifest bytes, TRAIN/master/revision/inventory/quota và opaque image
order; hash+decode đủ 160 ảnh trước consumption. Mỗi ảnh được hash lại ngay trước
gọi model. Nếu bundle thiếu/sai hoặc cần chọn lại ảnh: BLOCKED, không tự thay mẫu.

## Kaggle setup sau quyền riêng

Chỉ sau ChatGPT review source/HEAD, Research Lead phê duyệt G0/T0/O3 và các quyền
liên quan, runtime tuple/policy được review, grant mới và external ledger hiện
hành. Không upload private data hoặc weights bằng task PREP này.

1. Fresh Kaggle session, T4 ×2, Internet ON để cài software. Hai GPU độc lập;
   chỉ GPU0 nhận model FP16/eager/batch1. Không tự shard sang GPU1.
2. Attach private bundle lịch sử đã được Owner duyệt, giải nén với
   `pilot_manifest.json` và `images/000000.jpg` … `images/000159.jpg`. Không cần
   master/inventory/annotations/TEST để chọn hoặc tái dựng cohort.
3. Attach private authority Dataset có đúng `grant_candidate160_<key>.json` và
   `ledger_candidate160_<key>.json`. Không để grant từ run/model cũ ở Inputs.
4. Owner provision official checkpoint **riêng** sau quyền: một private Input với
   `candidate_checkpoint_<key>.json`, `source/<revision>/` đúng 13/15 flat public
   files theo source lock, `weights/` đúng index và hai safetensors shards theo
   checkpoint metadata lock. Không symlink/hardlink/junction/extra files. Marker
   phải đúng `{"schema":"safeshift-candidate160-checkpoint-v1","model":...}`;
   `model` là dict từ `train_contract.model(key)`, gồm id/revision/transformers/
   attention/remote_code. Không có downloader weights trong notebook.
5. File discovery dùng bounded helper có sẵn: direct mounts hoặc
   `datasets/<owner>/<slug>`, filename duy nhất. Không edit path/SHA/cell để cứu.
6. Save Version → Save & Run All một lần sau approval. Không chạy interactive
   rồi Save & Run All lần nữa. Không rerun reservation hoặc consumed attempt.

Worker yêu cầu CPython **3.11.9**, Linux x86_64; kernel có thể khác version nhưng
chỉ chạy stdlib. Dùng interpreter probe, fresh `venv --without-pip --copies` và
pip wheel hash-locked của bootstrap hiện có. Không tải/build Python, không
fallback 3.12/3.13 hoặc dùng kernel site-packages. Không có interpreter này thì
BLOCKED trước attempt; availability trên Kaggle **UNVERIFIED**.

Requirements riêng giữ pins CPU #151, chỉ chuyển Torch/torchvision sang
`2.6.0+cu124`/`0.21.0+cu124`, bỏ marker Windows; đây là CUDA tuple **PREP cần
runtime approval**, chưa được thử GPU. Cài cu124 từ index chính thức trước pins
còn lại, pip check/freeze, version/path isolation và compiled CPU NMS. Trong child
preledger, native loader meta và processor tổng hợp dùng production path; hash/
decode ảnh thật chỉ sau authority. Không model forward ở CPU admission.

`nvidia-smi` trước ledger và trong worker ghi cả hai T4, driver và per-GPU total/
free VRAM. Giữ admission GPU0 >=14 GiB của bootstrap cũ và yêu cầu thêm minimum
riêng từng GPU/driver allowlist do Lead duyệt. Trong child sau consumption: một
visible T4 compute 7.5, CUDA build12.4, CUDA FP16 functional check và mem_get_info
trước weights. Per-image allocated/reserved/peak/free được giữ. Host nvidia-smi
PASS không thay CUDA child PASS hoặc đảm bảo fit checkpoint lâu dài.

Storage tái dùng physical allocation admission **28 GiB scratch +4 GiB output**;
cùng filesystem cần 32 GiB free, không cộng hai lần cùng free space. Không bỏ
cổng nếu Kaggle chỉ có khoảng20 GiB. Weights attached read-only, source/cache/
venv ở sibling Kaggle tmp, evidence ở working. Cleanup chỉ scratch session sở
hữu; lỗi cleanup được giữ và không được publish toàn working tree.

## Authority contract — phải do bên có thẩm quyền cung cấp

Không có grant thực trong Git; `preparation.json` giữ các giá trị chưa chốt là
null. Tests có fixture tự ghi rõ SYNTHETIC, không cấp quyền thật. Không dùng
thresholds Phi/Smol/Gemma hoặc suy approval từ request chuẩn bị160.

Grant schema `safeshift-candidate160-grant-v1` bắt buộc:

- Exact `model_key`, model dict, `base`, `runtime_ref`, `source_sha256`,
  `config_sha256`, `manifest_sha256`, `inventory_sha256`, `data_revision`,
  `master_sha256`, `split=TRAIN`. Giá trị runtime/config có trong notebook metadata.
- `max_initial_ids=160`, `max_native_calls=160`, `retry_sample_ids=[]`,
  `resume=false`; fresh `run_id`/`attempt_id`, explicit `max_seconds` gồm setup,
  finite grant expiry `expires_unix`.
- Review/approval refs không trống: `G0`, `T0`, `O3`, `code_review_ref`,
  `manifest_review_ref`, `policy_approval_ref`, `runtime_approval_ref`,
  `external_ledger_ref`, `owner_approval_ref`, `research_lead_review_ref`.
- Explicit true: `allow_train_images`, `allow_folder_gt`, `allow_checkpoint_read`,
  `allow_gpu`, `allow_raw_export`, `allow_software_install`,
  `private_custody_approved`. Không đặt credentials/token trong grant.
- `policy` đã được Lead duyệt; không có production default. `early_behavior_after`
  phải nằm sau first image và trước160; `review_after` là danh sách mốc tăng dần
  chứa mốc behavior đó; `review_wait_seconds` là thời gian chờ quyết định bên ngoài.
- Numerical policy: `invalid_max_count`, `repeat_max_count`, `dominance_min_valid`,
  `dominance_max_fraction`, `normal_min_support`, `normal_fpr_max`,
  `anomaly_min_support`, `anomaly_fnr_max`, `driver_versions`,
  `free_mib_per_gpu=[GPU0,GPU1]`. Count/rate là **maximum được phép**; dừng khi
  vượt (`>`), rate chỉ xét khi đủ minimum support hợp lệ. Không bắt batch nhỏ phải
  xuất đủ bốn nhãn. Giới hạn này không phải ngưỡng chứng minh scientific utility.

Ledger schema `safeshift-candidate160-reservation-v1` có đúng
`status=RESERVED_NOT_EXECUTED`, run/attempt/model/source/runtime_ref/manifest,
`expires_unix`, `external_ledger_ref` như grant và canonical `grant_sha256`.
Notebook kiểm cả hai trước data và ngay trước consumption; marker local độc quyền
chống chạy lại trong cùng filesystem. **Đây là reviewed record validation, không
chữ ký số hay distributed ledger**: Owner/Lead phải kiểm ledger thực hiện hành,
reserve duy nhất cho saved VM, cấm concurrent jobs/cross-session replay và cập nhật
consumption theo evidence. Snapshot attach không tự chứng minh global freshness.
Giới hạn này phải được reviewer chấp nhận trước release; không tự gắn READY.

## First image, behavior và review

`train_run` điều phối `pilot.runner.execute` cho từng ảnh với Store riêng; cache
chỉ một backend load. Registry enrollment chỉ trong process/context candidate,
khôi phục khi thoát; không thay source hoặc grants của pilot cũ. Transport giữ
native generation/C1/parser/replay; candidate execution config được khóa riêng.

First image và early stage nằm **trong160**, không là extra probe. Mỗi ảnh giữ
request, returned/generated token IDs, per-step bounded raw candidate logits và
finite flags, raw JSON trước parser, label/INVALID/error, input/model/run/config/
source binding và tokenizer serialization. Không đổi candidate surfaces hoặc
HNLO formula nếu mapping không tương thích; classification/HNLO báo riêng.

Technical error, NaN/Inf, OOM, không lưu raw hoặc mất custody dừng. Behavior policy
xét JSON INVALID, trùng token sequence, label dominance và lỗi Normal/hazard theo
support GT có quyền. Không clamp, retry, thay ảnh, hạ precision hoặc sửa nhãn.

Mỗi checkpoint `checkpoints/NNN.json` gồm observations, cumulative result hash,
source/attempt/manifest và SHA có thể tính bằng `pilot.contract.digest`. Tại mốc
review, worker chờ record **do Research Lead quyết định**, schema
`safeshift-candidate160-review-v1` với `checkpoint_sha256`, run/attempt/model/source/
manifest khớp, `research_lead_review_ref` thật và `decision=CONTINUE|STOP`.
Tên record là `<checkpoint_sha256>.json` trong drop directory in trước worker.
Notebook không viết decision và không chấp nhận quyết định của checkpoint cũ.

Delivery vào saved Kaggle VM phải được Owner/Lead phê duyệt và xác minh riêng;
chưa đo khả năng tương tác UI/service thực tế trong PREP. Nếu không có phương
thức delivery hợp lệ, để hold kết thúc và export; **không vượt gate**. Thiếu
record, sai binding, STOP hoặc hết deadline → dừng, mọi ảnh chưa gọi giữ
NOT_ATTEMPTED. Khi attempt đã kết thúc, không hỗ trợ resume/retry; continuation
cần quyết định và implementation/release riêng, không tái dùng notebook/attempt.

## Archive và kiểm tra kết quả thật

Download ZIP và `.sha256.json`, giữ private kể cả failure. Archive gồm manifest,
per-image journals/raw/tokens/logits, tokenizer, release config/dependency/source
inventory, approvals/ledger binding, environment/CUDA/memory receipts, checkpoints/
reviews, `accounting.json`, `summary.json`, supervisor recovery/status và member
checksums. Không có ảnh, checkpoint hoặc cache. Outer SHA + CRC qua ZIP read +
exact members/SHA được kiểm bằng archive helper hiện có.

ChatGPT cần đối soát160 ordinals/ID/order, tổng SUCCESS+INVALID+TECHNICAL_ERROR+
NOT_ATTEMPTED=160, native calls≤160, no retries, first/early stage/review, raw hash/
IDs/logits/parser/HNLO replay, model/runtime/source/grant/ledger và actual CUDA/VRAM.
Không coi NOT_ATTEMPTED/INVALID là SUCCESS hoặc HNLO unaligned là validated.
`COMPLETED_AWAITING_REVIEW` không phải chất lượng PASS hoặc quyền FULL TRAIN.

Supervisor phục hồi từ durable journals khi worker timeout/kill; output bị ghi dở
không được overwrite. Disk failure có thể ngăn cả finalizer/ZIP/sidecar; luôn thử
export dù receipt lỗi, giữ directory/partial bytes và stdout failure. Không hứa
archive hoàn chỉnh khi hết đĩa, hard kill hoặc mất VM. Consumption-marker write/
fsync không rõ kết quả → UNKNOWN/do-not-retry, không tuyên bố nonconsumed.

## Kiểm thử CPU và tái lập

Chạy từ repo root, chuẩn bị `data/processed/` cho test fixture tạm lịch sử. Không
cần dataset thật. Builder yêu cầu full40 runtime ref có đúng mọi embedded byte;
metadata notebook ghi ref đã dùng, có thể nằm trước commit notebook/docs/evidence.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref <runtime_ref_in_notebook_metadata>
python -B -m scripts.rehearse_candidate160 --output data/processed/candidate160/cpu-new
python -B -m unittest discover -s tests -v
```

Native CPU opt-in dùng **môi trường #151 đã pin và source/index public đã có**,
không tự tải weights/source để biến SKIP thành PASS:

```console
python -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public_snapshot> --index <public_index> --output data/processed/candidate160/internvl35-new
python -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public_snapshot> --index <public_index> --output data/processed/candidate160/minicpm4-new
```

Rehearsal giữ offline/no-visible-CUDA, native tests chặn network/CUDA/real model
forward/weights; chỉ empty/meta loader, processor thật và scripted generation.
So đủ160 IDs/order/call cap, raw-before-parse, no overwrite, first/behavior/review,
faults và ZIP reimport. Tất cả cells/payload/pins/Git SHA được kiểm; notebook cells
thật được chạy trên CPU trong sandbox tổng hợp **không grant**, kỳ vọng BLOCKED.
Kết quả thực chạy và giới hạn trong [biên bản CPU](research/CANDIDATE160_CPU_20261029.md).
