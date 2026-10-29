# CPU G2/G3 — InternVL3.5 HF và MiniCPM-V-4

29/10/2026, Asia/Bangkok. **Codex thực chạy bản sửa guard; chờ ChatGPT review lại và independent audit.**
GitHub xác nhận PR #149 MERGED, main đúng
`6342b15b0d70c27b28f4bcb5e53f04f6951d6171` bằng connector, fetch và `ls-remote`.
Cùng session/nhánh/worktree `audit/cpu-g2-g3-20261029`, Draft PR #150.
[ChatGPT review](https://github.com/tantdna2/SafeShift/pull/150#issuecomment-6492535296)
yêu cầu sửa guard tại HEAD cũ `f7318a3851c040808c140e0aab2f4c50c37bab0e`.
Lượt mới chạy đúng code commit `15c0e72993ebe44912c0b1858bc42fc28bc31315`,
sau đó chỉ thêm docs/receipts; không tự nhận reviewer PASS.

Phạm vi Owner giao: môi trường CPU riêng, public source/tokenizer và ảnh tổng hợp;
không weights, model construction/forward/inference, CUDA/GPU/Kaggle, private
TRAIN/TEST/GT/raw archive, grant hay thay khoa học. Không đăng ký backend mới.
[Kế hoạch Khóa luận](THESIS_EXECUTION_PLAN_2026.md), O1–O8/T0 và
[gates G0–G6](../KAGGLE_FAILURES_AND_RELEASE_GATES.md) giữ phạm vi hiện hành.

## Kết quả và mức bằng chứng

| Kiểm tra | `OpenGVLab/InternVL3_5-4B-HF` | `openbmb/MiniCPM-V-4` |
| --- | --- | --- |
| Exact revision | `6bd4487402110ef9889ba50eb7aefeb302526fed` | `6f69a8235885be89608f3a71ffd40695b379e1e7` |
| Public source hash / native code | **PASS** 13 file; native Transformers, `trust_remote_code=False` | **PASS** 15 file, gồm 7 Python; local hash-locked remote code, `trust_remote_code=True` |
| Isolated venv / pip check / compiled CPU ABI | **PASS** | **PASS** |
| AutoProcessor / AutoTokenizer / AutoConfig / class import | **PASS**; chưa model loader | **PASS**; chưa model loader |
| RGB, size, tiles/slices, tokens, normalization, context | **PASS** 6/6 sizes + RGBA→RGB/PNG-under-jpg | **FAIL** RGB 1×1; 5/6 sizes + RGBA→RGB/PNG-under-jpg **PASS** |
| C1 giữ nguyên trong rendered và expanded input | **PASS** các inputs đã tạo | **PASS** các inputs đã tạo; 1×1 chưa tạo được input |
| Generation contract trước model boundary | **PASS** cấu tạo native GenerationConfig; actual generate **BLOCKED** | **FAIL** native `chat()` không truyền nguyên generation/raw contract |
| Native input bị làm sai có chủ đích | **PASS** 5/5 lỗi bị từ chối | **PASS** 5/5 lỗi bị từ chối |
| Mock IDs qua tokenizer/Store/parser/diagnostics | **PASS** 15 ca | **PASS** 15 ca |
| G3 reused + snapshot unit suite | **42 PASS / 3 SKIP**, 0 failure/error | **42 PASS / 3 SKIP**, 0 failure/error |
| Real weight loader / effective per-layer attention | **BLOCKED** thiếu weights | **BLOCKED** thiếu weights |
| Actual continuation/raw custody/FP16/VRAM/quality/HNLO | **BLOCKED** thiếu weights/quyền GPU | **BLOCKED** thiếu weights/quyền GPU |
| Tổng thể trước release GPU | **BLOCKED** | **FAIL**, đồng thời còn các mục **BLOCKED** trên |

Không model nào qualified hoặc READY_FOR_GPU. PASS là phạm vi phần mềm/source
đã chạy trong từng hàng, không real classifier/behavior PASS. Bằng chứng đầy đủ
và SHA nằm trong [index](evidence/cpu_g2_g3_20261029/index.json),
[InternVL receipt](evidence/cpu_g2_g3_20261029/internvl35.json),
[MiniCPM receipt](evidence/cpu_g2_g3_20261029/minicpm4.json) và
[unittest receipt](evidence/cpu_g2_g3_20261029/unittest.json). Không chỉ dẫn một
hash local không đọc được: các receipts nhỏ này được version control, không chứa
ảnh, tokenizer bytes, weights, private IDs/GT hoặc raw model output.

## Môi trường và đường nạp thực chạy

Hai venv CPython **3.11.9 / Windows 10 build 26200**, không system/user packages.
Torch **2.6.0+cpu**, torchvision **0.21.0+cpu**, Accelerate **1.6.0**, NumPy
**1.26.4**, Pillow **10.4.0**; compiled `torchvision.ops.nms` thực chạy và
`pip check` đều PASS. InternVL: Transformers **4.55.4**, tokenizers **0.21.4**,
Hub **0.34.4**. MiniCPM: Transformers **4.51.3**, tokenizers **0.21.1**, Hub
**0.30.2**. Hai [requirements](../../configs/cpu_g2_g3/internvl35.requirements.txt)
[riêng](../../configs/cpu_g2_g3/minicpm4.requirements.txt) khóa cả dependencies
gián tiếp/pip/setuptools; receipt ghi `pip freeze --all`, class source hashes,
script/test/config hashes và Git SHA. Đây là CPU Windows, **chưa nghiệm thu Linux
worker/CUDA wheel tuple**. Không đổi runtime/source locks của pilot hiện hành.

Dùng lại `scripts.pilot_source_audit`, chỉ thêm hai lựa chọn explicit và đuôi
`.jinja`; mặc định ba model cũ giữ nguyên. Download anonymous ở full revisions,
không `snapshot_download` weights. [Public source lock](../../configs/cpu_g2_g3/public_source_lock.json)
ghi từng filename/hash và URL pattern. Một GET InternVL `vocab.json` timeout
60 giây; thử lại đúng URL/revision thành công, 2.776.833 bytes, hash trong index.
Đây là lỗi lấy source lịch sử, không model failure. Không sửa receipt lần lỗi
thành PASS. Lượt sửa guard dùng lại đúng 28 file public đã khóa hash; không tải lại.

Trước import remote MiniCPM ở lượt đầu, parser AST đã đọc cả 7 Python files; kiểm imports,
processor/image processor và `chat/generate/decode` source liên quan. Đây không
phải full independent security audit. Native probe kiểm exact allowlist/hash,
stage vào snapshot local tên revision và cache riêng, dùng `local_files_only=True`
với `revision/code_revision` cụ thể. Socket network, CUDA và weight-loader bị
guard; không thay class bằng class giả. Chỉ import class/model mapping, **không
gọi constructor/from_pretrained của model**, không empty weights rồi gọi loader PASS.

### Bản sửa guard theo review — trước copy và import

`verify_snapshot` cũ chỉ đếm `is_file()`, bỏ qua thư mục/link thư mục trong khi
`copytree` vẫn chép chúng. Bản sửa kiểm root bằng `lstat`, liệt kê **mọi direct
entry** gồm tên ẩn/dangling links, đối chiếu exact filenames rồi chỉ chấp nhận
regular file có một hard link. Từ chối directory/symlink và mọi Windows
`FILE_ATTRIBUTE_REPARSE_POINT`, gồm junction; không resolve root alias trước kiểm.
Danh sách 13/15 file và expected hashes giữ nguyên.

`stage_snapshot` thay recursive `copytree`: chỉ chép từng tên đã khóa bằng
`copyfile(follow_symlinks=False)` vào thư mục mới, kiểm lại toàn source và đích
(types, exact entries, hashes) trước remote import. Thư mục thêm giữa hai bước
không được chép; source thay đổi hoặc staged bytes hỏng làm dừng. Đây là kiểm
source/staging trong CPU harness, không tuyên bố sandbox hệ điều hành cho remote code.

Focused suite **18 = 15 PASS + 3 SKIP, 0 failure/error**: snapshot hợp lệ, missing/
corrupt/extra/weight/hidden files, thư mục rỗng/thư mục chứa `.py`, thay file bằng
directory, hard link, reparse attributes, root/child junction thật trên Windows,
source thêm thư mục khi copy và bytes đích bị sửa. Ba real-symlink tests (root,
file/dangling, directory) SKIP vì OS không cho tạo symbolic link; không gọi là
PASS. Junction thật và mocked reparse attribute checks đã chạy PASS trên Windows.
Thay đổi AST chỉ ở guard/staging/main wiring; environment/native setup/C1/
generation/preprocessing/mock outputs/input checks không đổi so HEAD đã review.

## Ảnh và token — không đổi cấu hình gốc

Ảnh tổng hợp xác định RGB `(40,80,120)`, không ngẫu nhiên; kiểm normalization/
channel order bằng giá trị RGB độc lập. Có portrait, landscape, square, 1×1,
large; PNG RGBA được lưu tên `.jpg`, decode theo content rồi `.convert('RGB')`.
Đây là đường chuyển RGB explicit trong probe, chưa production image loader.
Ảnh màu đồng nhất không chứng minh spatial crop order/pixel parity với custom
implementation, khả năng nhìn PPE hay chất lượng công nghiệp.

| RGB width×height | InternVL tiles (gồm thumbnail) / image tokens | MiniCPM views (gồm global) / image tokens |
| --- | --- | --- |
| 1×1 | 1 / 256 | **FAIL**, chưa có tokens |
| 448×448 | 1 / 256 | 1 / 64 |
| 640×480 | 13 / 3.328 | 3 / 192 |
| 200×1200 | 7 / 1.792 | 4 / 256 |
| 1200×200 | 7 / 1.792 | 4 / 256 |
| 2048×1536 | 13 / 3.328 | 10 / 640 |

InternVL thực dùng `InternVLProcessor` + `GotOcr2ImageProcessorFast` +
`Qwen2TokenizerFast`; stored image processor `crop_to_patches=false` nhưng native
processor mở tiling. 13 views là 12 patches + thumbnail; không gọi image processor
đơn lẻ rồi kết luận không chia ảnh. Tensors `[views,3,448,448]` CPU float32 finite,
image ID **151671**, đúng **256/view**; input lengths 806–3.878. Implementation
hashes của processor/image/model khớp nguồn Transformers đã dẫn ở #149.

MiniCPM thực dùng `MiniCPMVProcessor` + `MiniCPMVImageProcessor` +
`MiniCPMVTokenizerFast`; đối chiếu query64/patch14/max9/448/use-image-id/slice-mode.
Tối đa **9 local slices + global**, không gọi tổng 10 là vi phạm max9. Kiểm từng
image bound dài 64, `<unk>` placeholders đúng, grids khớp pixel count, input IDs
int32, masks bool và pixels float32 finite. Các input thành công dài 755–1.353.
Không tự ép dtype native sang kiểu của model khác. Mọi input phải giữ C1 một lần
sau decode expanded IDs, còn chỗ cho max64 theo context config.

**MiniCPM 1×1 FAIL thực:** `ValueError: mean must have 448 elements if it is an
iterable, got 3`. Source `image_processing_minicpmv.py` infer channel format từ
ảnh gốc trước resize và tái dùng khi normalize; RGB `(1,1,3)` phát warning ambiguous
channel. Cơ chế phù hợp lỗi quan sát, nhưng không suy mọi ảnh nhỏ đều hỏng hoặc
thay upstream bằng fix chưa review. Receipt có error/stage/redacted traceback.
Giữ FAIL; thêm resize/input-format override hay loại 1×1 khỏi envelope cần quyết
định/review riêng, không phải thay giao thức trong task này.

## C1 và generation — MiniCPM cần adapter review

C1 SHA-256 giữ **`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`**.
Không system/thinking/examples; không sửa labels/parser, không ép grammar hoặc
strip reasoning. Native rendered wrapper có đúng C1 nguyên văn một lần; expanded
IDs decode cũng giữ nguyên. C1 bị sửa một ký tự bị từ chối trước processor.

InternVL dùng lại `pilot.backend.native_generation_config` trên native config;
explicit `do_sample=false`, beam1, max64, cache/return_dict và score/logit flags
khớp `pilot.contract.GENERATION`, repetition penalty 1.0. **Chỉ kiểm construction
và source, chưa kiểm actual generation hoặc generated-ID slicing.**

MiniCPM gọi **unbound method thật** `MiniCPMV.chat` với config/processor/tokenizer
thật và stand-in chỉ chặn tại `self.generate`; không tạo model hoặc sinh logits.
Đường không truyền processor bị tránh bằng local processor đã pin; đây là probe,
chưa approved production adapter. Hai trace:

- Chỉ `sampling=False`: wrapper gửi beam3, repetition penalty1.2, max2048.
- Truyền frozen kwargs: beam1/max64 được giữ, nhưng `do_sample`, `use_cache`,
  `return_dict_in_generate`, `output_scores`, `output_logits` **bị lọc bỏ**;
  repetition penalty vẫn1.2 và `decode_text=True`. Không suy giá trị default thực
  của model từ việc kwargs mất; **chưa chứng minh generation tương đương C1**.

`chat()`/`_decode_text()` trả text đã bỏ token đặc biệt/strip; không đủ raw-ID
custody qua API này. Giữ **FAIL contract ở wrapper boundary**, không gọi là model
quality FAIL. Source có `generate(decode_text=False)`, nhưng tích hợp raw-ID path,
termination/pad/prefix handling và generation policy cần review riêng. Không sửa
remote code, không override repetition penalty, chuyển API hoặc đổi C1 để cứu PASS.

## G3 và độ bao phủ thực chạy

Tái dùng `Store`, strict `parse_label`, `output_diagnostics.summarize` và tests
`ParserTests`, `ArtifactAndEngineTests`, `test_phi_evidence`, `test_smol_evidence`.
Không viết engine/runner thứ hai; không thêm grant hoặc candidate production backend.
Mỗi stack chạy **45 unit tests = 42 PASS + 3 SKIP, 0 failure/error**, gồm raw durable trước parse,
ENOSPC/write failure/tail NOT_ATTEMPTED, no overwrite, partial archive/CRC/hash,
load/OOM/error/redaction và report/export failures. Tests mô phỏng không xác nhận
filesystem luôn durable khi mất điện/hard-kill hoặc disk full tuyệt đối.

Mỗi tokenizer thật còn qua **15 mock-ID cases**: bốn labels, whitespace, invalid
JSON, duplicate key, lặp label trong value, lặp object, extra key, empty IDs, mất
token cuối, cùng valid response lặp lại, JSON đúng không EOS và cắt max64. Raw
synthetic được Store ghi/fsync trước parse. Kết quả **7 valid/8 INVALID** là fixture
accounting, không tỷ lệ model. Sequence lặp ghi nhận 2 lần; không đặt threshold
collapse/early stop. JSON đúng không EOS vẫn theo parser cũ, EOS diagnostic tách
riêng; không sửa label bằng EOS. Mô phỏng token IDs, không scripted model forward.

**5 native input faults/model** đều bị từ chối: IDs float, mask zero, thiếu image
token/placeholder, pixels half và C1 thay đổi. Toàn repo: **246 discovered = 224
PASS + 22 SKIP, 0 failures/errors**. SKIP là 6 Phi native, 9 Smol native, 1 network
pip-bootstrap opt-in, 3 Linux filesystem/allocation và 3 real-symlink tests thiếu
quyền OS ở trên. Không suy những SKIP thành
PASS; không tái audit/diagnose behavior Phi/Smol hoặc đóng #147.

## Tái lập

Chạy từ repo root tại code commit ở trên. Windows commands; chọn tên output mới
mỗi lần, tool từ chối overwrite. Source/weights cache và artifact lớn ở ignored
`data/processed/cpu_g2_g3/`, không commit source upstream/ảnh/tokenizer/model bytes.

```powershell
python -m venv data/processed/cpu_g2_g3/env-internvl
python -m venv data/processed/cpu_g2_g3/env-minicpm
data/processed/cpu_g2_g3/env-internvl/Scripts/python.exe -m pip install -r configs/cpu_g2_g3/internvl35.requirements.txt
data/processed/cpu_g2_g3/env-minicpm/Scripts/python.exe -m pip install -r configs/cpu_g2_g3/minicpm4.requirements.txt
python -B -m scripts.pilot_source_audit --models internvl35 minicpm4 --output data/processed/cpu_g2_g3/public
data/processed/cpu_g2_g3/env-internvl/Scripts/python.exe -B -m scripts.rehearse_candidate_cpu --model internvl35 --snapshot data/processed/cpu_g2_g3/public/internvl35 --output data/processed/cpu_g2_g3/ivl-r1
data/processed/cpu_g2_g3/env-minicpm/Scripts/python.exe -B -m scripts.rehearse_candidate_cpu --model minicpm4 --snapshot data/processed/cpu_g2_g3/public/minicpm4 --output data/processed/cpu_g2_g3/mcp-r1
python -B -m unittest discover -s tests -v
```

Nếu source downloader báo unavailable, dừng và lấy lại đúng file/revision để so
lock; không bỏ file khỏi lock. CLI trả nonzero khi FAIL/BLOCKED (hàm main: 1/2),
receipt quyết định trạng thái từng check. Không tạo lock mới từ revision khác để
ép chạy. Trong task này cài Torch CPU trước rồi áp requirements; freeze cuối đã
khớp toàn pins. Một dependency thử trước đó (`einops`) không cần và đã gỡ trước
lượt cuối. Native warnings và lỗi phát triển đầu tiên được giữ local; run đầu
dừng sớm ở MiniCPM 1×1, harness sau đó được sửa để giữ FAIL và kiểm tiếp các ca
độc lập, không bỏ lỗi. Receipts bàn giao thuộc code commit cuối, không lẫn lượt đó.

## Điều kiện trước GPU đầu tiên — vẫn chưa được cấp quyền

1. ChatGPT review lại bản sửa guard và receipts; sau đó handoff independent
   security/technical audit theo review, trước mọi merge. Không tự gọi audit hoặc
   nhận audit PASS từ task này. Runtime reviewer kiểm source/license/lock
   và native CPU findings. InternVL cần candidate adapter dùng cùng native path;
   MiniCPM phải khép generation/raw API và lỗi 1×1 bằng thay đổi có review. Không
   cho hai checkpoint chạy bằng backend khác hoặc tự dùng wrapper mặc định.
2. G0/O3/O5/O6: phê duyệt exact model/revision, preprocessing/generation/parser,
   finite bounded sequence/attempt cap, input envelope/GT rights, sample/time/cost,
   stop rules và run/source/release/grant mới. Thứ tự CPU không là thứ tự Kaggle;
   0 qualified, slot peer thứ ba vẫn VACANT, không tự sửa roster/M2/DECISIONS.
3. Fresh Linux worker/dependency/CUDA ABI rehearsal và G1 builder/source release
   review. G4 kiểm **child worker sau isolation** nạp driver/NVML/CUDART, actual
   device initialization/count/free VRAM từng T4; host visibility không đủ.
   Không chuyển legacy repair/grant sang runtime này.
4. Chỉ sau quyền riêng mới load weights, kiểm effective attention từng decoder/
   vision layer, precision/finite first-step/actual continuation/raw-before-parse,
   memory peak từng GPU. Những mục này hiện **BLOCKED**, không meta PASS thay thế.
5. G5 first-image rồi panel nhỏ có GT Normal/hazard và nhiều miền được duyệt;
   predeclared stops bao phủ all-Normal→Anomaly lịch sử InternVL, invalid/repetition/
   truncation và budget. Không mặc định 12/160, không buộc sinh đủ bốn labels;
   quality/utility và HNLO optional cần bằng chứng thật riêng, không CPU threshold.

Không weights/GPU/inference/Kaggle hoặc permission được thực hiện từ tài liệu này.
Dừng tại **Draft PR** để ChatGPT kiểm GitHub; không Ready for Review/merge.
