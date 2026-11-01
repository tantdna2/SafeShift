# Issue #165 — kiểm chứng HNLO từ official160 đã lưu

**RESULT: KHÔNG — 0/155**, tương ứng **0/160 planned** theo Method A hiện hành.
Đây là kết luận kỹ thuật Codex từ evidence thật, **chờ ChatGPT review và
Antigravity audit độc lập trước chấp nhận khoa học/merge**. Không suy rộng thành
MiniCPM nói chung không thể có HNLO; không thay quy tắc bằng cách chọn một alias.

Phạm vi: [Owner Issue #165](https://github.com/tantdna2/SafeShift/issues/165),
BASE/main đã kiểm GitHub `41e25fe4de37f2049e81ce978710ad80e682e740`.
Chỉ CPU trên archive official FP32 INITIAL, tokenizer serialization, IDs,
logits, configuration và custody đã lưu. Không Kaggle/GPU/inference/weights,
không đọc nội dung ảnh hoặc GT/TEST, không đọc raw model khác.
Manifest chỉ được hash ở mức bytes, không parse các trường nhãn/ảnh.
Sample IDs chỉ dùng exact join, không diễn giải các thành phần filename.

## Kết quả đầy đủ

| Kiểm tra | Số lượng / kết quả |
| --- | --- |
| Planned / original SUCCESS / original INVALID | 160 / 155 / 5 |
| SUCCESS đã kiểm custody, native path và strict parser | 155/155 |
| HNLO hợp lệ theo Method A | **0/155 SUCCESS; 0/160 planned** |
| SUCCESS thiếu HNLO: `AMBIGUOUS_TOKEN_BRANCH` | **155** |
| Independent negative proof đồng ý | 155/155 |
| Cùng một decision position nhưng hai token cho mỗi label | 155/155 |
| Sparse logits thiếu các alias thay thế | 155/155, cùng nhóm ambiguity, không cộng hai lần |
| Bốn tọa độ đã lưu cùng bước: finite + ba công thức số học đồng ý | 155/155; **không phải HNLO qualified** |
| INVALID giữ nguyên, không cứu nhãn | 5 |
| Missing archive/custody, decoder mismatch, resource bound, technical FAIL, chưa kết luận | 0 |
| Native steps đối chiếu bản riêng với raw | 1.760 |
| CRC/member SHA256/membership/sidecar | 4.210 payload + checksum manifest; PASS |
| Inference calls trong task | 0 |

Ở mỗi SUCCESS, tại position 8 (zero-based), cả bốn nhãn đều có **hai** token
khác ID thỏa cùng surface, actual prefix/suffix, fixed native context và EOS.
Một token trong mỗi cặp có sparse logit; token kia không có. Danh sách token,
step, alias, bốn logits và SHA từng member nằm trong receipt private; không
đưa raw theo mẫu vào Git.

Method A yêu cầu **đúng một token cho mỗi nhãn** trên toàn vocabulary, không
chỉ trên sparse keys. Do đó cả155 dừng ở ambiguity. Argmax, all-finite và
logits ở bước khác không khôi phục được logit còn thiếu hoặc chứng minh một
alias là duy nhất. Không dùng public tokenizer thay runtime, encode lại output,
thay prefix, chọn token theo logit sẵn có, gộp alias hoặc thay metric để tạo PASS.

`logsumexp(z01,z02,z03)-z04` được kiểm trên bốn tọa độ **đã lưu** bằng hàm
HNLO cũ, Decimal60 oracle cũ và Decimal90 direct exponent/sum/log độc lập;
`rel_tol=abs_tol=1e-10`. Các phép tính đồng ý chỉ chứng minh arithmetic.
Tất cả155 `derived.hnlo` vẫn `null`; không backfill 160 kết quả gốc.

## Nguồn và custody

| Identity | Giá trị |
| --- | --- |
| Archive SHA256 | `46a41359c3ab2978b9ee4ac010518e49a74141641d9334c29035bdc0c8eac877` |
| Runtime commit | `c3c223bc69edd253d57bbba9344e0633b65b3de4` |
| Source inventory SHA256 | `b1d6d8210b9b5b03c52b59cd339c75a4ec60f0dafb1fc0106623a9e25a2ec2a3` |
| Model | `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7` |
| Implementation | `minicpm4-resampler-attention-fp32-v1` |
| Descriptor SHA256 | `2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da` |
| Official config SHA256 | `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00` |
| Runtime tokenizer SHA256 | `8f7ccf860a471f0cf4bd0b75cba2b08ea1035013cadc825000befa6a0f95da56` |
| Run / series | `owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36` |
| Attempt / kind | `owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36_a1` / INITIAL |

Source: [T4 exact-source dossier](research/T4_O2_SELECTION_DOSSIER_20261101.md#32-hai-official-train160),
Issue165 pins và local `data/processed/m160/HANDOFF.md`.
Archive tại `data/processed/m160/final/minicpm4-0074f8bb22c4466ea33e0c5619ffc576.zip`.
Đọc trực tiếp ZIP chế độ read-only, không extract hay sửa thư mục `m160/verified/`.
Hash toàn archive trước và sau; mọi payload hash kiểm trước semantic reads.
Reader chỉ cho parse allowlist metadata/call/native/tokenizer; không parse
`pilot_manifest.json`, logs, ảnh hoặc GT. Original manifest hash vẫn được khóa.

Bridge đối chiếu execution/config/source/descriptor, INITIAL history/lineage,
authorization/consumption, accounting đủ160/unique/order, per-call identity,
raw-result hash, request/native/returned IDs, raw step bản riêng và processors.
Configuration projection dùng hash riêng; không giả hash projection là official
config hash. Derived packet seal chỉ được tạo sau kiểm custody từ archive pin
độc lập. Archive mới tự seal không được nhận bởi CLI này.

Runtime source của capture/custody/parser/HNLO/effective implementation được
đối chiếu `git show` tại đúng runtime commit với source inventory. Parser và
HNLO hiện tại còn phải giống bytes đã phát hành (chuẩn hóa CRLF khi đọc checkout).
Không claim chạy lại capture/model hay xác minh toàn-vocab argmax từ sparse logits;
phần đó vẫn dựa vào capture/source custody gốc.

## Decoder và giới hạn tài nguyên

[Bridge](../safeshift/evaluation/minicpm_saved_hnlo.py) dùng Rust
`tokenizers==0.21.1`, đúng version trong freeze gốc, và decoder Python độc lập
cho chain runtime chính xác: Replace metaspace → ByteFallback → Fuse → Strip.
Vocab BPE + added/special IDs được dựng riêng, đối chiếu đủ73.448 ID và decode
từng ID ở cả hai chế độ skip specials. Không Transformers/torch/model forward.

Verifier Python đi qua **mọi non-special vocabulary ID tại mọi body position**;
mọi candidate hợp standalone surface phải qua fixed context và original EOS.
Independent negative proof chạy cả khi builder từ chối ambiguity. Có bốn
actual body/context signatures; tám search độc lập (builder/verifier tách biệt).
Cache32 entries dùng exact decoder object/body/context/prefix/surfaces/EOS;
không dùng response đơn lẻ hoặc subset sparse làm key/search domain. Cache
không chứa custody, packet validity, step/logit values hoặc arithmetic.
Mọi155 record vẫn kiểm lại seals, toàn native path, steps và logits riêng.

Giữ nguyên `MAX_TRIALS=2_000_000`; không nâng cap hay cắt vocabulary.
10 body tokens ×73.448 IDs =734.480 trials/signature, dưới cap. Negative search
được cache nhưng không biến resource/decoder/technical refusal thành NO.
ByteFallback invalid UTF-8, mixed specials và contextual whitespace có tests
riêng đối chiếu Rust/Python, ngoài exhaustive replay trên evidence thật.

## Tái lập và evidence

Từ repo root, CPython3.11.9 Windows; seed=null. Dependency duy nhất thêm cho
verifier thực là tokenizers0.21.1, cài local ignored, không runtime dependency
mới của package nền. Đã dùng wheel `tokenizers-0.21.1-cp39-abi3-win_amd64`.

```powershell
python -m pip install --index-url https://pypi.org/simple --target data/processed/issue165-deps --no-deps tokenizers==0.21.1
$env:PYTHONPATH='data/processed/issue165-deps'
python -B -m scripts.verify_minicpm_saved_hnlo --archive data/processed/m160/final/minicpm4-0074f8bb22c4466ea33e0c5619ffc576.zip --output data/processed/issue165/reproduce-new
python -B -m unittest discover -s tests -p test_minicpm_saved_hnlo.py -v
python -B -m unittest discover -s tests -p test_hnlo_method_a.py -v
```

Output phải là thư mục **chưa tồn tại** dưới `data/processed/`. Lỗi giữ receipt
BLOCKED, không ghi đè hoặc thay evidence. Để tái lập lần nữa dùng output mới.
`records.private.json` chứa từng packet/proof/negative proof, tọa độ thiếu,
member lineage và kết quả null. `verification.json` chứa aggregate + read list;
`environment.json` chứa command/Git HEAD/platform/source hashes;
`runtime_source.json` chứa đối chiếu source gốc. `public_receipt.json` chỉ dùng
allowlist counts/identities/checksums. Không upload archive/raw/records private.

[Public receipt](research/evidence/issue165_hnlo/public_receipt.json) ghi kết quả
real run03; checksum private records:
`fa544e077faf8048029060946636f8d028977eea69ac79e913f23bb14e15684c`.
Tám searches và302 cache hits; 155 independent negative proofs,155 arithmetic
checks. Các files local ở `data/processed/issue165/run03/`.
Run01 dừng ở engineering inspection để bổ sung memoization và negative verifier;
giữ `interrupted.json`, không claim kết quả của lượt dở. Run02 đầy đủ có cùng
private-record hash; run03 bổ sung all160 independent output decode, parser/
HNLO source equality và aggregate fields. Không artifact gốc nào bị ghi đè.

Tests và final-HEAD rerun được ghi ở PROJECT_STATE và Draft PR. Tracked receipt
khóa exact proof-source file hashes; final-HEAD check không tự xác nhận audit.
Không sửa O2/L1–L4, selection/pooling, T2/T3, nhãn/parser, scientific protocol,
không Accuracy/Macro-F1/AUROC hay model selection. Dừng tại một Draft PR.
