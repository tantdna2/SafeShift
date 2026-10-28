# Three-VLM TRAIN pilot v1 — PREP, chưa cấp quyền chạy

Ngày 27/10/2026 (Asia/Bangkok). BASE/main đã fetch và đối chiếu GitHub:
`28fdf82512577f2ed0fb435fb2c12b88e82baf2f`. Đây là task code do Owner giao,
không phải kích hoạt kế hoạch Draft [#137](https://github.com/tantdna2/SafeShift/pull/137).
Không sửa #136/#137, M2, roster hoặc kết quả lịch sử. Các ngưỡng, cách lấy mẫu,
parser và hợp đồng HNLO dưới đây là **PROPOSED FOR THIS PILOT**, cần Research Lead
duyệt đúng source/config/manifest trước dùng. Không sửa protocol/config M2.

**CODE PREP ≠ KAGGLE PASS ≠ HNLO PASS.** Không ảnh/annotation thật, weights,
raw Qwen artifact, GPU hoặc inference nào được đọc/chạy trong task code.
Chỉ public source/tokenizer của model đã được tải để kiểm CPU. Bộ notebook này
có backend native thật; thiếu grant hoặc điều kiện sẽ xuất BLOCKED, không sinh
dự đoán demo. Quyền cũ không dùng được cho schema grant mới.

## Sản phẩm và đường chạy

| Thành phần | Đường dẫn |
| --- | --- |
| Gemma | [notebook](../notebooks/SafeShift_TRAIN_PILOT_gemma.ipynb) |
| Phi | [notebook](../notebooks/SafeShift_TRAIN_PILOT_phi.ipynb) |
| SmolVLM2 | [notebook](../notebooks/SafeShift_TRAIN_PILOT_smolvlm2.ipynb) |
| CPU-only storage preflight | [notebook](../notebooks/SafeShift_STORAGE_PREFLIGHT.ipynb) |
| Mã chung | [safeshift/pilot](../safeshift/pilot/) |
| Source/config/model/code hashes | [configs/pilot](../configs/pilot/) |
| Tests CPU tổng hợp | [test_pilot.py](../tests/test_pilot.py) |
| Báo cáo bàn giao và nguồn | [technical audit](THREE_VLM_TECHNICAL_AUDIT.md) |

Notebook chứa source payload đã hash; không clone main hoặc Draft PR lúc chạy.
Builder [build_three_vlm_notebooks.py](../scripts/build_three_vlm_notebooks.py)
tạo cùng payload cho cả ba, chỉ key model khác. `source_digest()` ràng buộc cả
package runtime, prompt, dependency pins, source lock và CPU token evidence.
Owner không nhập revision, SHA, đường dẫn, prompt hoặc thay cell.
Source SHA-256 của payload storage-fix Draft:
`b2d549d36adb5dda97ef6563059f3725185fe1bdf71d2ce28a5bd8f06a1f4c1e`.
Grant cũ bind source trước thay đổi không tự áp dụng cho source này.

Luồng sau khi **được cấp quyền**: kiểm source/grant → consume attempt local →
kiểm source/tokenizer lock đủ evidence → original TRAIN master/manifest/dimension
inventory/toàn bộ ảnh selected → đo storage → nhập resume archive được phép →
kiểm hai GPU bằng nvidia-smi → venv riêng →
kiểm versions/CUDA FP16 nhỏ trước weights → pinned snapshot/safetensors/custom
code → native greedy từng ảnh → raw fsync → strict parser → CPU HNLO replay →
report đủ planned IDs → ZIP/checksum. First-12 gate là các ordinal 0–11 trong
manifest, bao gồm capture nhỏ ngay ảnh đầu; không gọi model thêm để probe.
Không có lỗi chặn thì tiếp tục phần còn lại. Lỗi HNLO riêng không dừng phần
classification thành công. Lỗi model/config/OOM/preprocessing/I/O hoặc raw
nonfinite dừng model, giữ tail NOT_ATTEMPTED. INVALID không được sửa/cứu nhãn.

## Dữ liệu và chọn manifest trước khi chạy model

Nguồn identity: đúng [master lịch sử](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/data/manifests/pa3_full_train.v1.json),
SHA-256 `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`,
3.763 IDs duy nhất, folder domain/level, input JPEG SHA-256. Nguồn upstream
InspecSafe-V1 `f3cb7d3e7827c1afc1c5bfd0524257984bba46ab` theo W1, không tuyên bố
upstream tar đã được hash-verify lại; giữ giới hạn provenance trong DATA_AND_ETHICS.

Chỉ sau grant CPU preparation riêng mới được dùng công cụ dưới đây. Grant này
cho phép đọc hash/header của **toàn bộ 3.763 TRAIN JPEG và folder GT** để chọn
kích thước; không có quyền model/GPU. Không chạy lệnh này trong task code:

```console
python -B -m scripts.prepare_three_vlm_pilot --grant data/processed/permissions/prepare.json --dataset-root data/raw/InspecSafe-V1 --output data/processed/three_vlm_inputs/safeshift-pilot-input
```

`--dataset-root` là root chứa `DATA_PATH/train/Annotations`; với layout Kaggle
gốc là `InspecSafe-V1-Kaggle/train`. Công cụ chỉ mở các locators trong master,
không scan ảnh hay tìm TEST. Tên ID nguyên vẹn = filename stem, nhãn/domain giữ
theo folder gốc, không dựa polygon/text-domain. Hash từng ảnh và verify JPEG
header trước đóng gói; không resize/re-encode. Thiếu/ảnh hỏng/hash sai thì BLOCKED,
không giảm N, đổi seed hay bỏ qua ảnh.

Pilot chính luôn 80 Level04 + 48 Level01 + 24 Level02 + 8 Level03. Lịch sử TRAIN
chỉ có 8 Level03; phải đủ 8 hợp lệ. Seed cố định
`safeshift-three-vlm-pilot-20261027-v1`. Trong từng level, chia đều có giới hạn
capacity giữa năm folder domains; miền hết mẫu thì cấp phần còn lại sang miền
còn capacity theo thứ tự SHA-256 đã khóa. Không giả phân bố đều khi dữ liệu
không cho phép. Trong mỗi cell level/domain: giữ ảnh diện tích lớn nhất, rồi
round-robin area quartile × aspect bin `<0.8`, `0.8–1.25`, `>1.25`, tie bằng
SHA-256(seed|purpose|ID). Thứ tự đầu lấy ảnh lớn nhất mỗi level, sau đó seeded
order. Tất cả group IDs lịch sử được giữ; không coi ảnh là độc lập thống kê.

Dimension inventory/hash được lưu; notebook chạy lại selector và so ordered IDs
với manifest đã duyệt. Cả ba grant phải bind cùng manifest hash. Không có output
của model mới trong selector. Owner/Lead phải xem phân bố domain×level và
width/height/aspect trong manifest trước cấp inference grant. Metadata nằm trong
private bundle; worker native chỉ nhận PIL image và prompt C1, không sample ID,
domain, GT, filename hay thư mục mang nhãn trong chat template.

Gói `safeshift-pilot-input` gồm `bundle.json`, `master_manifest.json`,
`dimension_inventory.json`, `pilot_manifest.json`, `prepare_receipt.json` và
`images/000000.jpg`… (bytes gốc, tên opaque). Không đưa ảnh hoặc bundle lên Git.
Chỉ upload **private Kaggle Dataset** sau quyền packaging/upload được Lead/Owner
cấp; không tự upload ở task này. Gắn bundle đã review vào cả ba notebook.

## Tập Qwen3 false-safe tùy quyền truy cập

Nếu không được đọc artifact gốc, supplementary giữ
`NOT_RUN/BLOCKED_NO_VERIFIED_QWEN_ARTIFACT_GRANT`, N=0. Không bịa 20 IDs và không
lấy 38/composite Recovery224 làm membership. Không ảnh hưởng quota 160 chính.

Công cụ [export_pilot_qwen_verified.py](../scripts/export_pilot_qwen_verified.py)
dùng các verifier saved-score đã merge của PR131, chỉ bốn V4 gốc, original S2
ZIP đúng checksum/sidecars, historical ordered IDs/input hashes/labels/statuses.
Không chạy sensitivity toàn bộ, không đọc raw logits hoặc Recovery224. Cần grant
artifact riêng; không chạy trong task code:

```console
python -B -m scripts.export_pilot_qwen_verified --grant data/processed/permissions/qwen_export.json --input-dir data/processed/approved_v4 --original-s2-zip data/processed/approved_v4/original_s2.zip --output data/processed/qwen_verified.json
```

Thêm `--qwen-verified-export data/processed/qwen_verified.json` vào lệnh preparation
khi prepare grant cho phép đọc đúng export hash. Chọn tối đa 20 SUCCESS,
GT Level01–03, generated Level04; không trùng main, seeded rank. Nếu chỉ có k<20
ca hợp lệ thì dùng đúng k. Receipt saved-score/provenance giữ trong bundle; đây
không phải raw Qwen audit mới. Qwen label trong bảng chỉ có khi exact-ID/input/GT
match export đã verify. Báo supplementary riêng, không trộn vào metric main hoặc
claim cải thiện đại diện toàn TRAIN.

## Hồ sơ grant — không bắt Owner sửa notebook

`configs/pilot/authority_template.json` có grant/prepare/full bằng null. File đó
không cấp quyền. Sau code review và quyết định audit độc lập của ChatGPT, Lead
phát hành grant data-preparation trước. Sau review manifest và ngưỡng, Lead phát
hành ba file `grant_gemma.json`, `grant_phi.json`, `grant_smolvlm2.json` để Owner
attach như private input; không sửa mẫu null thành quyền tự cấp.

Inference grant schema `safeshift-pilot-grant-v1` phải có:

| Trường | Hợp đồng |
| --- | --- |
| `mode`, `split`, `model_key` | `PILOT`, `TRAIN`, đúng một model key |
| `source_sha256`, `config_sha256`, `manifest_sha256` | Source digest được builder in; `digest(settings(model))`; `digest(plan)` được preparation in |
| `data_revision`, `master_sha256` | Đúng constants trong contract |
| `run_id`, `attempt_id`, `external_ledger_ref` | IDs mới đã đối chiếu ledger ngoài; attempt riêng mỗi phiên; run giữ khi resume |
| `owner_approval_ref`, `research_lead_review_ref`, `chatgpt_code_review_ref` | Bằng chứng thật gắn đúng source/config/manifest; không placeholder |
| `max_initial_ids` | Chính xác 160+k, k≤20; tối đa 180/model, 540 ba model |
| `max_seconds` | Cap Owner cấp trước chạy, 60–43200; setup/provision/worker được supervisor tính chung |
| `allow_train_images`, `allow_folder_gt`, `allow_model_download`, `allow_gpu`, `allow_raw_export`, `approve_thresholds` | Từng quyền phải true theo quyết định có thật |
| `thresholds` | Chính xác THRESHOLDS dưới đây, không chỉnh sau kết quả |
| `retry_sample_ids` | Mặc định `[]`; chỉ IDs đã lỗi/INVALID được cấp riêng |

Grant là tài liệu phê duyệt có hash binding, không chữ ký số hay hệ thống xác
thực Owner. Code kiểm scope/hash và ledger local; reviewer/Owner chịu trách nhiệm
xác minh approval refs và ledger ngoài. Kaggle VM mới không giữ được local ledger.
Không dùng topology/grant cũ hoặc hiểu một chuỗi URL là tự chứng minh phê duyệt.

## CPU-only storage preflight trước grant/attempt

Sau khi ChatGPT kiểm GitHub và quyết định audit độc lập cho Draft này, Owner có
thể chạy notebook `SafeShift_STORAGE_PREFLIGHT.ipynb` trong phiên Kaggle dự kiến.
Notebook không cần dataset, grant, GPU, weights hoặc inference. Nó ghi receipt
và SHA-256 riêng dưới `/kaggle/working/data/processed/three_vlm_preflight/`, in
đường dẫn; nếu không ghi được receipt thì in lỗi JSON ra notebook output. Tải cả
receipt và sidecar. Mỗi lần là session mới, không ghi đè.

Scratch cố định `/kaggle/tmp`, output cố định `/kaggle/working`. Nếu scratch root
chưa tồn tại, cả preflight và pilot dùng chung cơ chế kiểm cha `/kaggle` rồi tạo
duy nhất `tmp` bằng mkdir exclusive, mode 0700. Root có sẵn hoặc được tạo đồng
thời được kiểm lại: directory thật, không symlink/junction, có quyền ghi/traverse,
không chồng working. Trên Linux dùng directory descriptor với O_NOFOLLOW và so
device/inode để phát hiện thay cha/root trong lúc tạo. Không tạo thư mục cha,
không sửa quyền root có sẵn; lỗi quyền/alias/identity thì BLOCKED với receipt.
Root chung được giữ lại; chỉ scratch theo session có marker được cleanup.
Delta tạo root: 12 tests CPU mới; toàn bộ suite Windows Python 3.11 có
140 PASS + 3 SKIP (Linux-only), WSL Linux Python 3.14 có 143/143 PASS.
Supervisor dùng runtime gate mô phỏng; đây không là Kaggle/Python 3.11–3.12 hay
GPU qualification. Các test kiểm root thiếu/có sẵn, EEXIST đồng thời, quyền,
alias/non-directory, identity thay đổi, shared filesystem và giữ receipt khi lỗi.
Đo mount,
device, total/used/free, và cấp phát vật lý độc quyền đồng thời **28 GiB scratch
+ 4 GiB output**, kiểm số block và fsync để kiểm writability/quota thực tế tại
thời điểm đó. Có thể tốn thời gian và tạm chiếm ≥32 GiB; không chạy song song với
công việc dùng chung quota. Nếu không đủ chỗ, quota từ chối, allocation không
được hỗ trợ, đường dẫn alias hoặc không ghi được: BLOCKED, không fallback. Giải
phóng allocation sau kiểm tra; PASS không đặt chỗ, không chứng minh quota dịch vụ
khác, delayed-write, peak dùng đĩa, khả năng GPU, hay cấp quyền thực nghiệm. Nếu
không thể dọn probe hoặc scratch, BLOCKED và giữ thông báo để xử lý có kiểm soát.
Preflight là ảnh chụp nhất thời; thực tế có thể thay đổi trước hoặc trong pilot.

Nguồn đối chiếu Qwen3 tại `31a04e6`: `hnlo_train/bootstrap.py` dùng
`tempfile.gettempdir()` ngoài working; `orchestrate.py`/`budget.py` đo scratch và
output, cộng nhu cầu khi chung `st_dev`; `one_click/provision.py` tạo runtime và
cache ngoài evidence. Bản này không phục hồi code Qwen3: dùng root `/kaggle/tmp`
tường minh, kiểm alias/marker, cấp phát để thăm dò quota và fail closed; không
khẳng định Qwen3 lịch sử đã kiểm quota theo cùng phương pháp.

## Owner: Save & Run All sau review và grant

1. Chờ review code, grant manifest/ngưỡng/model/GPU/export và input release được
   Lead phát hành. Giữ Internet ON; upload notebook nguyên bản từ release đã review.
2. Attach đúng một private bundle và grant file tương ứng. Discovery chỉ hỗ trợ
   direct mount hoặc `datasets/<owner>/<slug>`, tối đa 512 directory entries;
   zero/multiple bundle/grant bị chặn, không yêu cầu sửa đường dẫn thủ công.
3. Chọn **T4 ×2**. Preflight đòi hai T4 khoảng 16 GB/card, GPU0 free ≥14 GiB;
   GPU1 để trống. Không cộng VRAM. Scratch riêng từng session nằm dưới
   `/kaggle/tmp/safeshift-pilot-<session>`; venv, HF/model/custom-code
   cache và `TMPDIR/TMP/TEMP` của pip/worker đều vào vùng này.
   `storage_admission.json` ghi `st_dev`, mount, total/used/free thực đo.
   Cần 28 GiB scratch + 4 GiB output; **chung filesystem phải còn tổng ≥32 GiB**,
   khác filesystem phải đủ từng phần. Không cộng hai quan sát free của cùng device.
   Resume cộng thêm 4× số byte giải nén archive vào output allowance (extraction,
   retained sample copies và ZIP). Thiếu thì BLOCKED trước cài thư viện/weights;
   không tự giảm ngưỡng hay chuyển root. Allocation được thử lại trước cài đặt;
   nó được giải phóng sau kiểm tra, không giữ chỗ hay chứng minh peak disk/ảnh fit.
   Kaggle mount, quota/driver/RAM/retention thực tế vẫn chưa được đo trong task này.
4. Với Gemma, tài khoản HF phải chấp nhận [Gemma terms/model access](https://huggingface.co/google/gemma-3-4b-it),
   dùng read token hợp lệ của Owner, lưu Kaggle Secret tên `HF_TOKEN`, cho notebook dùng secret.
   Không dán token vào cell/grant/log. Thiếu quyền/401/403 giữ BLOCKED hoặc failure
   model-access với 0 attempted, không fallback sang revision/model khác.
   **Bản hiện tại còn chặn Gemma bởi source/tokenizer audit chưa hoàn tất**, kể cả
   token hợp lệ; phải theo quy trình dưới đây trước phát hành grant/notebook mới.
5. Save & Run All một lần cho attempt đã cấp. Mỗi model có fresh venv riêng,
   pinned packages, FP16/eager, batch1, greedy max64, không FA2/BF16/quantization,
   không thay preprocessing để cứu OOM. Không đổi cell rồi rerun attempt.
6. Download ZIP và `.sha256.json` in ở cuối, kể cả BLOCKED/FAILED/PARTIAL.
   Save Version/Outputs và tải ngay; working/temp có thể mất khi session kết thúc.
   Notebook không upload kết quả hoặc gửi thông tin cho ai.

Sau worker kết thúc hoặc timeout, supervisor chỉ dọn scratch có đúng marker và
đường dẫn session thuộc `/kaggle/tmp`; không xóa evidence/input/attempt ledger. Nếu dọn
thất bại, xuất ZIP vẫn được thử và in `SCRATCH_CLEANUP_FAILED`: chỉ tải ZIP evidence,
không publish cả working tree chứa venv/cache/weights. Nếu kernel/VM bị hủy cứng,
finalizer có thể không chạy; giữ giới hạn ephemeral/retention đã nêu. Raw/partial
ZIP không bị ghi đè. Lỗi ghi session/failure metadata không ngăn thử export.

### Gemma: quyền truy cập và audit trước GPU

| Trục trạng thái | Bằng chứng hiện tại |
| --- | --- |
| Access | BLOCKED: lần audit public trước trả HTTP 401 cho 10 tài nguyên; không thử token trong task sửa. |
| Source/tokenizer | Chưa đủ bằng chứng: lock `files:{}`/`unavailable` chưa được bổ sung; fail closed trước dataset/GPU/weights. |
| HNLO | HNLO_UNVERIFIED: chưa biết mapping thật/decision alignment/raw logits/replay. |
| GPU/classification | NOT_RUN; không có T4 hoặc ảnh TRAIN trong task code. |

Owner đăng nhập tài khoản HF được cấp quyền và chấp nhận điều khoản tại model
chính thức; xem [HF gated access](https://huggingface.co/docs/hub/models-gated).
Chỉ sau quyền **source/tokenizer audit riêng**, Owner/reviewer cung cấp token đọc
qua biến môi trường `HF_TOKEN` bằng secret manager, không qua command argument,
notebook, grant, Git hoặc chat. Công cụ dưới đây chỉ lấy text/code/tokenizer ở
revision đã khóa, không tải weights/ảnh, không import code model:

```console
python -B -m scripts.pilot_source_audit --models gemma --authenticated --output data/processed/gemma_authorized_source_audit
```

Output mới/exclusive, không overwrite audit cũ. HTTP redirect bỏ Authorization;
token không lưu vào inventory hoặc log. Với CPU environment đã cài đúng
`tokenizers==0.21.1`, `Jinja2==3.1.6`, kiểm text-only C1/chat template:

```console
python -B -m scripts.pilot_tokenizer_audit --models gemma --source data/processed/gemma_authorized_source_audit --output data/processed/gemma_authorized_tokenizer_evidence.json
```

Reviewer kiểm inventory/checksum/revision, config/auto_map/processor/chat template,
tokenizer và bất kỳ executable source nào; đánh giá kết quả probe kể cả negative.
Chỉ sau review, cập nhật hashes/`unavailable` trong source lock và CPU evidence,
regenerate **cả ba** notebook rồi review source digest mới trong cùng PR/release
được phép. Không yêu cầu Owner sửa notebook/revision thủ công. Cấp grant mới bind
source/config/manifest sau khi release được duyệt. Không đổi model revision, nhãn
hay prompt để làm mapping thuận tiện. Quyền access và CPU probe không là HNLO PASS:
runtime vẫn phải kiểm generated IDs/raw decision step/CPU oracle trên ảnh thật.
Phi/Smol có lock riêng và không bị khóa theo Gemma; vẫn cần grant riêng của chúng.

### Phi và hardlink: giữ chính sách, ghi đúng phần chưa biết

Phi giữ **16 crops, FP16, eager, GPU0**. Ảnh lớn trong first-12 vẫn có thể OOM trên
T4 16 GiB; chưa có phép đo GPU để khẳng định fit. OOM dừng, giữ raw/error/tail
NOT_ATTEMPTED; không giảm crop/độ phân giải hoặc đổi backend. Mọi cấu hình khác
chỉ là phương án cần Owner/Lead duyệt riêng trước dùng, không fallback tự động.

`safe()` tiếp tục yêu cầu regular file, không symlink/junction và `st_nlink == 1`.
Chưa có stat trace của mount Kaggle thật chứng minh false rejection, nên rủi ro
đó là **UNVERIFIED**, không thêm ngoại lệ. Nếu một lần chạy được cấp quyền bị chặn,
lưu stat/link count/mount và manifest/hash đã được phép đọc để reviewer đánh giá;
không bỏ kiểm tra hoặc tự copy/đổi bundle ngay trong notebook.

## Raw, capture, replay và báo cáo

Mỗi sample lưu `started.json`, request/prompt/native config/input IDs,
`native_call.json`, từng step summary fsync từ outer-forward hook trước logits
processors, `native.json` trước decode, `raw.json` trước label parse/HNLO,
`result.json` chứa raw SHA-256 và trạng thái. Hook không thay output và không giữ
full-vocabulary history; chỉ candidate logits, full-vocab argmax/finite reductions,
dtype và step. Giữ partial/torn files và lỗi; checksum không chứng minh runtime
trung thực. Không raw authenticity hoặc full-vocab replay claim.

HNLO chỉ được VALIDATED khi native tokenizer có bốn complete continuations khác
đúng một token, chung prefix/suffix; fixed actual input boundary và output IDs
khớp; actual processors rỗng; tất cả raw argmax khớp generated IDs; logits hữu hạn;
Rust decoder độc lập khôi phục từ serialized runtime tokenizer kiểm output và
bốn candidate contexts; CPU formula khớp Decimal oracle. Đây là **log odds tại
decision step có điều kiện theo prefix chung**, không full-label sequence
likelihood hoặc xác suất nguy cơ. Nhiều token nhưng không có branch chung hợp lệ
thì INCOMPATIBLE; output khác dạng đã chứng minh giữ UNALIGNED; không sửa prompt
để ép mapping. Model có internal softcap dùng chính native forward logits sau
phép biến đổi nội tại, trước generation processors; nguồn/model config được lưu.

Artifacts lưu tokenizer serialization/hash, mappings, generated IDs, bốn logits,
decision index, label alignment, model/processor/tokenizer revisions, input/run/
config/prompt hashes, replay và reason. Năm trạng thái HNLO theo contract tách
khỏi SUCCESS/INVALID/TECHNICAL_ERROR/NOT_ATTEMPTED của classification. CPU replay
không cần model/GPU; comparison CLI cần `tokenizers==0.21.1` hoặc version đúng
runtime archive, để kiểm decoder; numeric oracle dùng standard library.

```console
python -B -m scripts.report_three_vlm_pilot --gemma data/processed/results/gemma.zip --phi data/processed/results/phi.zip --smolvlm2 data/processed/results/smolvlm2.zip --output data/processed/three_vlm_comparison
```

CLI hash-verifies archive/member/raw, exact shared manifest và replay trước join.
Có thể giao một/hai archive; model còn thiếu ghi NOT_ATTEMPTED, không gọi thất bại
khoa học. Output gồm `comparison.csv/json` với từng ID/domain/GT/Qwen-verified/
ba model/status và ba model reports. Không overwrite output cũ.

Mỗi report tách main/supplement; planned, attempted, success, invalid, error,
not-attempted, retries/native calls; 4×5, support/per-class recall, accuracy,
Macro-F1, balanced accuracy, binary FNR/FPR kèm denominators/unavailable/bounds,
predicted distribution, domain breakdown, timing/VRAM/error categories. Cột thứ
năm 4×5 gom mọi prediction không khả dụng; các trạng thái vẫn có counts riêng.
Accuracy/recall/F1 chính giữ toàn planned trong support; thêm accuracy-valid-only
được ghi rõ. FNR=FN/(TP+FN) và FPR=FP/(TN+FP) trên nhãn hợp lệ, không coi missing
là Normal; báo unavailable và bounds trên planned bên cạnh. Mean macro chỉ trên
lớp có support, danh sách/support rõ; mẫu số 0 trả null.

HNLO report có capture/alignment/replay counts, validated/planned coverage,
AUROC mô tả + eligible class supports; không loại missing khỏi bảng. Observer
time gồm reductions/CPU/fsync; peak VRAM thực và estimated temporary capture bytes
được lưu. **Paired GPU overhead / hook-off latency delta = NOT_RUN/null**: không
tạo thêm inference để đo đối chứng ngoài budget. Passive-hook argmax proof kiểm
nhãn greedy không bị sửa, không thay cho thực nghiệm paired memory overhead.
Muốn đo paired overhead phải cấp lượt gọi riêng; chưa có số đo thật nào ở đây.

## Ngưỡng đề xuất khóa trước pilot

| Quy tắc vận hành đề xuất | Giá trị |
| --- | ---: |
| Valid canonical / planned để technical pass | ≥0.98 (160 main: tối đa 3 INVALID) |
| Technical errors, missing attempts, raw nonfinite | 0 để technical pass |
| Normal→Anomaly hoặc Anomaly→Normal red flag | ≥0.95 ở một trong hai tỷ lệ valid-label |
| GO screening: FNR / FPR | ≤0.20 / ≤0.50 |
| GO screening: Macro-F1 (planned support) | ≥0.40 |

TECHNICAL_PASS chỉ khi toàn bộ main được hạch toán/attempted, không lỗi chặn và
đủ valid rate. Output INVALID có thể nằm trong allowance, không phải SUCCESS.
Lỗi chặn/thiếu coverage sau attempted → TECHNICAL_FAIL/NO_GO; 0 attempted hoặc
thiếu quyền/bằng chứng → INCONCLUSIVE/BLOCKED. Red flags giống pathology Q25/IVL3
được nêu riêng. GO cần technical pass, không red flag và đồng thời FNR/FPR/F1
trên; không quyết chỉ Accuracy. Đây là ngưỡng tài nguyên/sàng lọc **chờ duyệt**,
không scientific threshold cuối hoặc bằng chứng thêm utility cho Khóa luận.

Kết luận model phải tách classification/capture/alignment/replay/coverage/GPU
overhead/role HNLO. Dùng [mẫu bàn giao](THREE_VLM_PILOT_REPORT_TEMPLATE.md).
Kết quả âm hoặc thiếu bằng chứng không được ép PASS; không sửa prompt/parser,
seed, crop, số ảnh, threshold hoặc retry để có kết quả đẹp.

## Resume và FULL TRAIN đang khóa

Resume cần archive nguyên vẹn và grant mới có `resume_parent_archive_sha256`,
`resume_approval_ref`, cùng run/model/source/config/input identity, attempt ID mới
trong external ledger. Attach archive tên `resume_<key>.zip`; Owner chỉ rename
file, không sửa notebook. Archive/member hashes, model/config/ordered IDs/input
hashes được kiểm trước resume. Prior archive được giữ nguyên dưới `prior/` trong
archive mới, không ghi đè. SUCCESS skip; INVALID/error/torn/started-only bị coi
đã consume. Chỉ retry ID trong `retry_sample_ids` + `retry_approval_ref`, v1 tối đa
một retry/ID; mọi attempts được đếm, không gọi nó là ảnh mới. Tail chưa attempted
được tiếp tục sau grant resume. Không tự resume từ working hoặc tự tăng retry.
Archive tự chứa prior evidence nên dung lượng tăng qua các phiên. Admission
archive: tối đa 8 GiB uncompressed, 1.000.000 regular members, 64 MiB/member;
vượt cap thì export FAIL và giữ directory/partial ZIP, không mất raw hay giả
archive hợp lệ. Full deployment phải review storage/session budget riêng.

FULL TRAIN chưa có grant, notebook literal PILOT không đọc mode từ input, không
chuyển mode sau first12/160. Preparation FULL cần grant packaging riêng; runner
CLI hỗ trợ `--mode FULL_TRAIN`, exact 3.763 IDs/main, supplementary rỗng, same
revision/preprocess/prompt/parser/config. Grant phải FULL_TRAIN riêng,
`full_train_explicit=true`, `pilot_review_ref`,
`pilot_recommendation=GO_FULL_TRAIN_RECOMMENDED` và HNLO disposition VALIDATED
hoặc CLASSIFICATION_ONLY_ACCEPTED được Owner duyệt. Có resume qua verified
`--resume-archive`, accounting/raw/report/archive; không directory resume tự nhận.
Future launcher/environment/release/grant vẫn phải được review trong task sau;
không đổi notebook PILOT bằng Owner code edits. Không chạy TEST. Nếu sửa config
vì pilot FAIL, cần source/config version mới và review trước so sánh/full run.

## Kiểm tra và ranh giới bàn giao

```console
python -B -m scripts.build_three_vlm_notebooks
python -B -m unittest discover -s tests -v
git diff --check
```

Tests gồm fixtures tổng hợp, parser/selector/master/TRAIN-only/quota/no duplicate,
source/code pin trước remote import, grant/null/full lock, raw/no-overwrite,
resume/no-success-rerun/explicit retry, partial/OOM/ENOSPC/time cap, all-status
metrics/oracles và notebook payload parity. Không test fixture nào từ dataset.
Native weights/load/T4/actual-image preprocessing, real HNLO alignment, Kaggle
quota/driver/retention, Gemma access và utility vẫn **NOT_RUN/UNVERIFIED**.

Task này dừng ở một Draft PR để ChatGPT kiểm GitHub và quyết định audit độc lập.
Chưa có grant thực nghiệm mới được phát hành. Không merge hoặc tự gọi audit.
