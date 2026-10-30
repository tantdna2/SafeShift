# InternVL3.5 HF / MiniCPM-V-4 — Kaggle 160 PREP

30/10/2026, Asia/Bangkok. **BLOCKED cho thực nghiệm; GPU/behavior UNVERIFIED.**
Gói phần mềm sau [PR #152 MERGED](https://github.com/tantdna2/SafeShift/pull/152)
từ đúng main `f79f7bddeac62e8fb8378d6798c25387f45f0f37`, trong một Draft PR.
Không chạy Kaggle, tải weights hoặc mở private TRAIN/TEST trong task này.
Adapter contract base `95eb4e8…` vẫn giữ nguyên để không sửa provenance lịch sử.

- [InternVL notebook](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb)
- [MiniCPM notebook](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb)
- [Builder](../scripts/build_candidate160_notebooks.py)
- [Contract pending, grant=null](../configs/candidate160/preparation.json)
- [Unsigned worksheets / authority checker](../scripts/candidate160_authority.py)
- [Đề xuất thẩm quyền batch — chưa duyệt](research/DECISIONS.md#dec-20261030-candidate160-batch--proposed--unapproved)

Đây là executable PREP cần review, không `READY_FOR_GPU`, không qualification
classifier/peer/HNLO. Không mở FULL TRAIN, chọn slot 3, chuyển grant cũ hoặc thay
C1/parser/preprocess/precision/generation để đạt PASS. Sáu notebook cũ và adapter
PR #151 giữ nguyên bytes; không đổi protocol, split, nhãn hoặc metric.

Review [ChatGPT #6501983735](https://github.com/tantdna2/SafeShift/pull/152#issuecomment-6501983735)
yêu cầu sửa provenance trên cùng PR #152. Config/grant v2 dưới đây thay mô tả
candidate cũ; các receipts trước review chỉ chứng minh code tại HEAD cũ.

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
6. Kiểm authority offline bằng command dưới và đủ checklist cuối tài liệu.
   Với Save & Run All liên tục, bắt buộc có Lead approval thật cho
   `PREAPPROVED_BATCH`; EXTERNAL mode có thể dừng ở review checkpoint.
7. Save Version → Save & Run All một lần sau approval. Không chạy interactive
   rồi Save & Run All lần nữa. Không rerun reservation hoặc consumed attempt.
8. Chờ saved version kết thúc; xem stdout `supervisor_status`/failure và
   `summary.json` trong Outputs. Tải đúng thư mục evidence ZIP cùng
   `<ZIP>.sha256.json` được in ở cell cuối, giữ private. Không tải/publish toàn
   working tree hoặc đưa private raw/manifest/GT lên GitHub.

Worker yêu cầu CPython **3.11.9**, Linux x86_64; kernel có thể khác version nhưng
chỉ chạy stdlib. Dùng interpreter probe, fresh `venv --without-pip --copies` và
pip wheel hash-locked của bootstrap hiện có. Không tải/build Python, không
fallback 3.12/3.13 hoặc dùng kernel site-packages. Không có interpreter này thì
BLOCKED trước attempt; availability trên Kaggle **UNVERIFIED**.

Requirements riêng giữ pins CPU #151, chuyển Torch/torchvision sang
`2.6.0+cu124`/`0.21.0+cu124`, bỏ marker Windows; đây là CUDA tuple **PREP cần
runtime approval**, chưa được thử GPU. Bổ sung đủ14 Linux NVIDIA/Triton pins từ
[official cu124 METADATA](https://download.pytorch.org/whl/cu124/torch-2.6.0%2Bcu124-cp311-cp311-linux_x86_64.whl.metadata)
SHA256 `76581c0d424f2d45de443327dfe1d5e115fd5e090b553deca3c3e23fc31c8da0`.
[PyTorch official tuple](https://docs.pytorch.org/get-started/previous-versions/)
xác nhận Torch2.6/vision0.21/cu124. Cài `--no-deps` với toàn bộ pins, pip check,
freeze; worker từ chối cả dependency thừa/chưa khóa, version/path isolation và
compiled CPU NMS. Không suy metadata verification là CUDA wheel/ABI PASS. Trong child
preledger, native loader meta và processor tổng hợp dùng production path; hash/
decode ảnh thật chỉ sau authority. Không model forward ở CPU admission.

`nvidia-smi` trước ledger và trong worker ghi cả hai T4, driver và per-GPU total/
free VRAM. Giữ admission GPU0 >=14 GiB của bootstrap cũ và yêu cầu thêm minimum
riêng từng GPU/driver allowlist do Lead duyệt. Trong child sau consumption: một
visible T4 compute 7.5, CUDA build12.4, CUDA FP16 functional check và mem_get_info
trước weights. Per-image allocated/reserved/peak/free được giữ. Host nvidia-smi
PASS không thay CUDA child PASS hoặc đảm bảo fit checkpoint lâu dài.
Child CUDA FP16 probe nay chạy **trước consumption** (quyền GPU đã phải có),
không manifest/weights/model call; thiếu receipt đo thật hoặc lỗi cuInit → BLOCKED,
không consumed. Sau consumption child chính vẫn kiểm lại để phát hiện drift.
Driver phải nằm trong allowlist Lead duyệt và đạt ít nhất Linux525.60.13 theo
[CUDA12 minor compatibility floor](https://docs.nvidia.com/cuda/archive/12.4.0/cuda-toolkit-release-notes/index.html).
CUDA12.4 GA có toolkit driver550.54.14; minor compatibility có giới hạn, không
coi đạt floor là native kernels/real checkpoint PASS hoặc tự đổi driver/runtime.

Storage tái dùng physical allocation admission **28 GiB scratch +4 GiB output**;
cùng filesystem cần 32 GiB free, không cộng hai lần cùng free space. Không bỏ
cổng nếu Kaggle chỉ có khoảng20 GiB. Weights attached read-only, source/cache/
venv ở sibling Kaggle tmp, evidence ở working. Cleanup chỉ scratch session sở
hữu; lỗi cleanup được giữ và không được publish toàn working tree.
Policy còn yêu cầu minimum `free_ram_mib` (min host available và cgroup remaining),
`free_scratch_mib`, `free_output_mib`, `free_gpu0_runtime_mib`. CPU admission kiểm
RAM/disk, từng ảnh kiểm lại RAM/disk và GPU0 free; ở review batch kiểm thêm lần
nữa. Đây là giới hạn do Lead phải duyệt, không mặc định số. GPU admission trước
load `free_mib_per_gpu` khác runtime headroom sau load; không đòi14GiB còn trống
sau khi model đã chiếm bộ nhớ. Model load/forward OOM dừng, giữ consumed và evidence.

## Authority contract — phải do bên có thẩm quyền cung cấp

Không có grant thực trong Git; `preparation.json` giữ các giá trị chưa chốt là
null. Tests có fixture tự ghi rõ SYNTHETIC, không cấp quyền thật. Không dùng
thresholds Phi/Smol/Gemma hoặc suy approval từ request chuẩn bị160.

Grant schema `safeshift-candidate160-grant-v2` bắt buộc:

- Exact `model_key`, model dict, `base`, `runtime_ref`, `source_sha256`,
  `legacy_transport_config_sha256`, `candidate_execution_config_sha256`,
  `manifest_sha256`, `inventory_sha256`, `data_revision`,
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
- Live resource minima: `free_ram_mib`, `free_scratch_mib`, `free_output_mib`,
  `free_gpu0_runtime_mib`, đều số nguyên dương, không gộp VRAM.
- `policy.review_mode`: `EXTERNAL` hoặc `PREAPPROVED_BATCH`. Thiếu field giữ
  external review tương thích; không suy ra quyền batch. `batch_authorization`
  phải null khi external; batch cần object phê duyệt riêng dưới đây.

Ledger schema `safeshift-candidate160-reservation-v1` có đúng
`status=RESERVED_NOT_EXECUTED`, run/attempt/model/source/runtime_ref/manifest,
`expires_unix`, `external_ledger_ref` như grant và canonical `grant_sha256`.
Notebook kiểm cả hai trước data và ngay trước consumption; marker local độc quyền
chống chạy lại trong cùng filesystem. **Đây là reviewed record validation, không
chữ ký số hay distributed ledger**: Owner/Lead phải kiểm ledger thực hiện hành,
reserve duy nhất cho saved VM, cấm concurrent jobs/cross-session replay và cập nhật
consumption theo evidence. Snapshot attach không tự chứng minh global freshness.
Giới hạn này phải được reviewer chấp nhận trước release; không tự gắn READY.

## Hai cấu hình và hai hash, không hoán đổi

`safeshift-candidate160-config-v2` có hai phần tách biệt:

- `legacy_transport_compatibility.settings_snapshot` là bản sao nguyên vẹn của
  `pilot.settings(key)` khi enroll đúng model. Các chuỗi Phi cropping, generic
  outer-forward, pilot contract và selection seed ở đây **chỉ là descriptor lịch
  sử phục vụ transport**, không mô tả thao tác candidate hoặc chọn lại cohort.
- `effective_candidate` mô tả adapter PR #151 thực tế: InternVL native HF
  template/tiling, logits từ `internvl_outer`, sequence prompt+continuation;
  MiniCPM native slices/resize/normalize/patch packing với RGB HWC tường minh,
  native generate→_decode→LLM, logits từ `minicpm_llm_forward`, sequence chỉ
  continuation từ inputs_embeds. Cả hai giữ C1/generation/precision/eager đã khóa.
  Không có Phi `num_crops=16` hoặc seed selector mới trong phần này.

| Trường / nơi giữ | Nghĩa và phép kiểm |
| --- | --- |
| `legacy_transport_config_sha256` | Canonical digest của exact frozen `pilot.settings(key)`; chỉ nhận diện transport lịch sử. |
| `candidate_execution_config_sha256` | Canonical digest toàn bộ config v2, gồm khối legacy được dán nhãn và phần effective candidate; đây là config cần duyệt cho execution. |
| `raw.identity.config_sha256` | Alias lịch sử do frozen pilot runner ghi; phải bằng legacy transport hash, **không** bằng candidate execution hash. Không đổi tên/ghi lại trường này. |
| Grant v2, Store identity, `raw.execution_release` | Bắt buộc cả hai hash với tên đầy đủ, đúng model/source/ref/run/attempt; trường candidate mơ hồ `config_sha256` bị từ chối. |
| `configuration_binding.json`, `raw.configuration_provenance` | Giữ full config v2, mapping alias và execution binding để reviewer/recovery tính lại cả hai hash. |

Sau khi raw đã lưu bền vững và **trước parser**, CandidateStore đối soát config
với hợp đồng đúng model, tính lại hash hai scope, kiểm alias của runner, native
logit boundary và sequence semantics. Hash sai/hoán đổi, grant v1, model/source/
attempt sai, effective metadata bị gán Phi hoặc thiếu provenance đều fail closed;
raw tokens/logits đã nhận vẫn giữ nguyên. Recovery kiểm lại config với hợp đồng
và grant mà supervisor đang giữ; sửa raw rồi cập nhật checksum file vẫn không
làm provenance sai thành SUCCESS. Đây là kiểm chứng cấu hình, không đổi parser,
HNLO hoặc điều kiện dừng khoa học. Native step `origin` descriptor giữ nguyên
bytes của adapter; module capture thực tế được chỉ rõ ở effective logits/boundary.

Grant v1/cấu hình v1 không cấp quyền cho v2. Cần approval/source/ref/hash mới;
không sửa hoặc tự cấp grant lịch sử để đi qua cổng.

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

Đoạn trên chỉ áp dụng `EXTERNAL`. Saved VM không có delivery đã xác minh thì
để STOP/export, không hứa160 hoặc tự sinh CONTINUE. Nhánh batch giải quyết nhu cầu
thực thi liên tục bằng **ủy quyền trước**, hiện chỉ là đề xuất chưa được duyệt.

`PREAPPROVED_BATCH` cần grant `batch_authorization` schema
`safeshift-candidate160-batch-authorization-v1` với đúng:

```json
{
  "schema": "safeshift-candidate160-batch-authorization-v1",
  "allow_automatic_continuation": null,
  "research_lead_approval_ref": null,
  "policy_sha256": null,
  "execution_binding_sha256": null,
  "conditions": [
    "all_durable_results_recover_exactly",
    "no_technical_or_nonfinite_output",
    "all_behavior_limits_pass",
    "approved_support_at_early_and_later_reviews",
    "live_resource_limits_pass",
    "grant_and_deadline_current"
  ]
}
```

null nghĩa **chưa duyệt**, object trên không phải grant dùng được. Lead phải
cho phép rõ `allow_automatic_continuation=true` và viện dẫn approval thật chấp
thuận đúng điều kiện, mốc và numerical policy. Hash canonical dùng
`pilot.contract.digest(grant['policy'])` và
`digest(train_contract.execution_binding(grant))`; sau khi hoàn tất mọi trường,
ledger thật phải reserve `digest(grant)` chính xác. Không dùng SHA file JSON có
whitespace thay canonical digest. Mọi sửa policy/model/source/run/attempt/config
làm approval binding không còn hợp lệ. Không ký/approve bằng tool tạo worksheets.

Batch bắt buộc review sau ảnh1, early behavior và các mốc Lead chỉ định (<160).
Ở mỗi mốc máy recover journals đối soát exact cumulative result; kiểm technical,
NaN/Inf/replay, behavior thresholds, live resources, deadline/expiry. Từ early
checkpoint trở đi phải có valid >= `dominance_min_valid`, valid Normal >=
`normal_min_support`, valid hazard >= `anomaly_min_support`; thiếu support STOP,
không tự coi rate chưa xác định là PASS. Không đòi đủ bốn nhãn dự đoán.

`decisions/NNN.json` ghi `AUTO_CONTINUE|AUTO_STOP`, từng check, observations-bound
checkpoint hash, grant/policy hash, execution binding, resource observation và
Lead prior approval ref. Không dùng schema external review hoặc giả chữ ký Lead.
Giữa các mốc cũng ghi `WITHIN_APPROVED_STAGE`; mọi checkpoint/error và terminal
decision được giữ. Lỗi/vi phạm → STOP/NOT_ATTEMPTED, không retry/resume hoặc dùng
attempt lại. Chỉ khi tất cả điều kiện luôn đạt mới có thể tới160; chưa có approval
thật thì release vẫn BLOCKED, dù test CPU mô phỏng hoàn tất160.

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

## Checklist bàn giao duy nhất

Mọi ô dưới đây còn **PENDING/BLOCKED** cho run thật. Public PREP không chứa grant,
chữ ký, numerical thresholds hay Inputs riêng. Không cần task/PR kỹ thuật phụ để
điền quyền thật; nếu approval/source/runtime thay đổi ngoài hợp đồng thì phải
review lại release tương ứng. Owner/Lead giữ private các biểu mẫu đã hoàn tất.

| Ai cung cấp | Nội dung phải cung cấp/kiểm trước Save & Run All |
| --- | --- |
| ChatGPT / reviewer | Review đúng HEAD Draft PR mới, notebook/source/runtime SHA, hai config hashes, receipts/skips và các giới hạn; xác minh #152 MERGED, không chuyển grant #152/cũ. |
| Owner + Research Lead | G0/T0/O3, code/manifest/policy/runtime/external-ledger/owner/Lead approval refs thật cho từng model; O3 chốt thứ tự hai run và cap; G0/T0 giữ yêu cầu khoa học/giảng viên/custody theo scope thật, không suy từ merge/code PASS. |
| Owner + bên có thẩm quyền | Cho phép rõ TRAIN images, folder GT, official checkpoint, GPU, software install, private raw export và custody. Không annotation mới, TEST, supplement hoặc FULL TRAIN. |
| Research Lead | Duyệt chính sách **PREAPPROVED_BATCH** và prior delegation đúng binding/hash, mốc1/early/later, sáu điều kiện, tất cả count/rate/support/time/resource/driver limits; expiry finite. Mọi giá trị null phải được quyết định thật. Nếu không duyệt, giữ EXTERNAL/BLOCKED cho nhu cầu batch. |
| Owner / ledger custodian | Hai grant v2 độc lập, run/attempt IDs mới; hai reservation records hiện hành từ ledger ngoài, exact canonical grant hash, RESERVED_NOT_EXECUTED. Chỉ một saved VM/attempt, không concurrent/cross-session replay; xác nhận rủi ro snapshot không enforcement phân tán và quy trình ghi consumption/UNKNOWN theo evidence sau run. |
| Owner | Private bundle đúng manifest SHA/order160, đủ images/000000.jpg…000159.jpg; cùng Input cho hai notebook. Không chọn lại hoặc upload public. Giữ actual image SHA/dimensions cho preflight kiểm. |
| Owner / checkpoint custodian | Mỗi model một private Input marker đúng model dict, source/<pinned revision> đủ allowlist13/15, weights/index+hai shards đúng lock SHA/size; không extra files/links. Không tải hoặc provision weights trong task này. |
| Owner / runtime reviewer | Saved VM thực có CPython3.11.9 Linux x86_64 ở interpreter candidates/PATH, cài đủ locked cu124 tuple, driver allowlist + compatibility, hai T4 riêng, RAM/cgroup/storage đủ minima và32GiB admission nếu cùng filesystem. Không đổi Python/precision/model/checkpoint/attention để vượt cổng. Actual CUDA/weights/VRAM vẫn UNVERIFIED cho tới receipt thật. |
| Owner | Mở đúng notebook theo model, fresh session; attach đúng ba nhóm Inputs, T4×2, Internet cho pinned software; check authority trước, rồi một Save & Run All duy nhất. Thiếu preconditions → không tiêu attempt để thử vận may. |
| Owner / Research Lead sau run | Download ZIP+sidecar, đối soát consumed/UNKNOWN/planned160/native-call cap/NOT_ATTEMPTED/raw hashes/decisions, cập nhật ledger ngoài; final behavior/HNLO/utility review riêng. Không dùng COMPLETED làm qualification, không rerun khi lỗi hoặc thiếu archive. |

Tạo worksheets **chưa ký** trên checkout chứa hai notebook cuối (đường dẫn output
mới, không ghi đè), thực hiện riêng cho `internvl35` và `minicpm4`:

```console
python -B -m scripts.candidate160_authority --model internvl35 --templates data/processed/authority-internvl35
python -B -m scripts.candidate160_authority --model minicpm4 --templates data/processed/authority-minicpm4
python -B -m scripts.candidate160_authority --model internvl35 --check <approved-grant.json> --ledger <current-reservation.json>
python -B -m scripts.candidate160_authority --model minicpm4 --check <approved-grant.json> --ledger <current-reservation.json>
```

Tool chỉ điền facts về source/model/config/manifest; decisions/rights/IDs/time,
ledger reservation status/hash và batch authorization để null. File batch worksheet
là phần để Lead duyệt, sau đó object có thẩm quyền phải đặt vào grant. Checker
chỉ xác minh cấu trúc/binding và expiry, không chứng thực tác giả/chữ ký, freshness
phân tán hoặc GPU readiness; không đọc TRAIN/checkpoint hoặc sửa ledger.

Sau download, trên môi trường riêng được phép đọc raw, so SHA256 ZIP với field
`sha256` của sidecar rồi gọi `safeshift.pilot.artifacts.verify_archive` (CRC,
exact members/member SHA). `import_archive` tạo directory mới; `train_run.recover`
đối soát raw/native/request/token/logits/HNLO/config của các planned rows trong
archived manifest. Receipts CPU mới chứng minh roundtrip này trên fixture160,
không chứng minh archive thật chưa chạy. Hard kill/VM loss/đĩa đầy có thể chỉ còn
partial bytes; giữ evidence directory và mọi lỗi export, không hứa ZIP hợp lệ
khi thiết bị lưu trữ không ghi được.
