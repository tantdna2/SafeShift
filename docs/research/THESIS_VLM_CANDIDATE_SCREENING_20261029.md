# SafeShift — Tuyển VLM cho thiết kế bốn mô hình ngang hàng

Ngày kiểm: **29/10/2026, Asia/Bangkok**. Task: [Issue #148 cập nhật](https://github.com/tantdna2/SafeShift/issues/148).
BASE: `1488dcb5212164e2946a15055d1da6e8be9096d2`. **RESEARCH ONLY / PROPOSED / STOP AT DRAFT PR**.

## 1. Kết luận để review

Đề xuất **ba ứng viên để kiểm chứng tiếp**, theo thứ tự:

1. **`OpenGVLab/InternVL3_5-4B-Instruct`** — ưu tiên cân bằng độ phân giải, khả năng instruction và chi phí tham số; đường attention không FA2 có trong source.
2. **`openbmb/MiniCPM-V-4`** — backbone MiniCPM4, xử lý ảnh theo slices, bộ nhớ tham số thấp hơn; phải kiểm chặt wrapper, processor và generation mặc định.
3. **`llava-hf/llava-onevision-qwen2-7b-ov-hf`** — bản tích hợp Transformers của LLaVA-OneVision, checkpoint FP16 và đường processor chuẩn; cần model sharding thật trên hai T4.

Đây là **thứ tự ưu tiên nghiên cứu**, không xếp hạng accuracy đã đo và không đổi roster. **Số ứng viên mới qualified cho thực nghiệm hiện tại: 0/3**. Strict C1 behavior, nhận đúng nguy cơ nhỏ, hiệu quả kiểm tra chéo và T4 end-to-end của cả ba đều **UNVERIFIED**; quyền chạy mới **BLOCKED**. Không có căn cứ để ghi READY hoặc đảm bảo đủ bốn thành viên. Nếu các ứng viên không vượt G0–G6/P1–P4 thì báo thiếu thành viên; không tự đưa ứng viên dự bị vào chạy.

Qwen3 vẫn là mô hình mốc được Owner đặt trong phạm vi. Trong thiết kế được đề xuất, nó cũng phải được đánh giá độc lập và luân phiên làm focal như ba peers; bằng chứng HNLO lịch sử không miễn qualification C1/cost/cohort mới. Không thay Qwen3 bằng Qwen3.5.

**VERIFIED — thẩm quyền:** [PR #137 đã merge](https://github.com/tantdna2/SafeShift/pull/137), đúng BASE trên và [biên bản ChatGPT hậu merge](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6488172066). Cập nhật đầu Issue #148 cho phép public research/metadata/CPU không weights, thay dòng ON HOLD cũ **chỉ trong phạm vi này**. O1–O8/T0 và O3 final roster vẫn pending; [#147](https://github.com/tantdna2/SafeShift/issues/147) còn OPEN, không thuộc task sửa lỗi này.

## 2. Cách đọc bằng chứng và phạm vi tìm kiếm

| Trạng thái | Ý nghĩa trong báo cáo |
| --- | --- |
| **VERIFIED** | Đã đọc được nguồn sơ cấp hoặc kiểm CPU cụ thể. Luôn giới hạn vào claim: model card khai báo không có nghĩa capability được tái lập. |
| **UNVERIFIED** | Chưa có phép kiểm thích hợp; bao gồm `UNKNOWN` trong issue/runbook. Giả thuyết triển vọng, ước tính bộ nhớ và ranking không phải empirical PASS. |
| **BLOCKED** | Có điều kiện chưa đáp ứng như HTTP401, thiếu quyền hoặc chưa có runtime được nghiệm thu. Không suy thành mô hình không có khả năng. |
| **FAIL** | Có quan sát không đạt trong đúng protocol/run đã dẫn. Không suy FAIL của một attempt sang mọi implementation hoặc model cùng họ. |

Đây là **targeted narrative/technical screening một người thực hiện**, không systematic review, PRISMA hay tuyên bố bao phủ toàn thị trường. Đọc InspecSafe trước khi chọn. Sau đó tìm qua web, arXiv, tác giả GitHub, model cards và Hub API; chỉ nguồn tác giả/nhà phát triển/framework được dùng làm bằng chứng. Không dùng thứ hạng popularity, bài Reddit hoặc số benchmark khác task để dự đoán điểm SafeShift. Model reports và model cards cùng họ không được tính như các nghiên cứu độc lập.

Tiêu chí trước ranking: có checkpoint xác định, single RGB + văn bản, khả năng instruction, nguồn processor/tokenizer, đường triển khai FP16 không bắt buộc FA2 trên T4, và khả năng giữ C1. Khả năng quan sát vật nhỏ/context được ưu tiên hơn tên kiến trúc. Loại khỏi shortlist khi có failure chưa giải quyết, access blocker, hoặc gánh nặng runtime cao hơn mà chưa có bằng chứng C1 bù lại. HNLO không là điều kiện lọc.

Nhật ký tìm kiếm thực hiện ngày trên; đây là truy vấn khám phá, không số lượng kết quả toàn cơ sở dữ liệu:

| Truy vấn / nguồn | Cách sử dụng |
| --- | --- |
| `site.huggingface.co OpenGVLab InternVL3_5-4B HuggingFace` | Tìm card; phân biệt `-Instruct`, bản hybrid và HF conversion. |
| `site.huggingface.co openbmb MiniCPM-V-4_5`; `site.huggingface.co/openbmb/MiniCPM-V-4 transformers license` | So MiniCPM4 với 4.5; không mặc định bản lớn hơn phù hợp hơn. |
| `site.huggingface.co HuggingFaceM4 Idefics3-8B-Llama3`; `site.huggingface.co allenai Molmo-7B-D-0924 llava onevision 7b` | Mở rộng ngoài Gemma/Phi/Smol; theo tới nguồn tác giả và Transformers. |
| `site.huggingface.co/Qwen/Qwen3.5-4B`; `site.huggingface.co/openbmb/MiniCPM-V-4.6` | Kiểm thêm thế hệ mới; không coi `transformers_version` lưu trong config là minimum runtime. |
| `site.nvidia.com T4 tensor core GPU 16 GB 70 W FP16`; `site.github.com/Dao-AILab/flash-attention Turing T4 Ampere` | Đối chiếu giới hạn phần cứng và attention với nguồn chính thức. |
| `site.pytorch.org scaled_dot_product_attention backend math float16`; `site.huggingface.co/docs/transformers idefics3 transformers 4.51.3` | Phân biệt SDPA API, CUDA kernel và mức kiểm chứng FP16. |
| GET `https://huggingface.co/api/models/{model_id}?blobs=true` | Resolve 12 ứng viên + Qwen3 mốc; lấy SHA, gating, inventory, số tham số/dtype/LFS metadata. Không lấy tensor bytes. |
| GET `/resolve/{full_sha}/{allowlisted_file}` | Đọc card/config/generation/processor/tokenizer metadata, source `.py` như văn bản, weight **index JSON**; thêm 9 file tokenizer cho shortlist. |

Không gọi inference API, import remote model code, `from_pretrained`, tải weights, mở ảnh/GT/TEST hay artifact riêng. PDF/figures/S3 công khai là tài liệu bài báo, không phải đọc TEST records. Không tạo notebook, grant, annotation hoặc package/runtime mới.

## 3. InspecSafe-V1: hiểu bài toán trước khi tuyển

### 3.1. Ngữ nghĩa phải giữ

**VERIFIED:** [arXiv v2](https://arxiv.org/html/2601.21173v2) và [bản Scientific Data](https://www.nature.com/articles/s41597-026-07796-x) mô tả 5.013 instances, 41 robots, 2.239 inspection points. RGB là đầu vào benchmark; các cảm biến khác của dataset không tự trở thành đầu vào SafeShift. Cùng vật/vi phạm có thể mang mức khác theo ngành. Nhãn toàn cảnh theo nguy cơ nghiêm trọng nhất; Level IV khi không có yếu tố nguy cơ.

Bảng dưới đối chiếu **Table 3 với chính bảng industry trong [C1 hiện hành](../../configs/pilot/classification_c1.txt)**; chỉ dùng một số tình huống phân biệt, không thay taxonomy:

| Miền | Điểm phân biệt cần mô hình hiểu | Hệ quả khi chọn VLM |
| --- | --- | --- |
| Oil & Gas / Chemical | Thiếu găng/mũ/mask thuộc I; dùng điện thoại II; vật lạ III. | Phải thấy PPE nhỏ và không áp rubric đường hầm. |
| Coal conveyor gallery | Thiếu mũ I; thiếu găng/mask, điện thoại và vật lạ II; nước đọng III. | Nhận đúng băng tải than, không nhầm thành petrochemical từ đường ống/nền tối. |
| Tunnel | Mũ thiếu/cửa tủ mở II; điện thoại, găng/mask thiếu và nước đọng III; gỗ/kim loại có thể I. | Quan hệ vật thể–làn đường–ngữ cảnh quan trọng, không chỉ object presence. |
| Power | Điện thoại, găng/mũ thiếu, cửa tủ mở II; mask thiếu III. | Cửa tủ/thiết bị nhỏ, chói và bóng tối có thể gây nhầm. |
| Metallurgy | Mũ thiếu I; găng/mask thiếu II; điện thoại và nước/dầu III. | Không học shortcut “miền này luôn Normal” từ mất cân bằng. |

`Level01` nghiêm trọng nhất, `Level02` trung bình, `Level03` nhẹ hơn, `Level04` Normal. Không có khoảng cách số học đã chứng minh giữa các mức; ordinal disagreement chỉ là feature đề xuất cần O2. Không tự thêm nhãn “không nhìn rõ” vào bốn nhãn C1.

**UNVERIFIED — suy luận ứng dụng:** RGB độ phân giải lớn chỉ tạo cơ hội nhìn điện thoại/găng/mũ; không chứng minh VLM phát hiện chúng. Tiling có thể tách vật nhỏ khỏi bối cảnh, resampling/compression có thể mất chi tiết. Một ảnh không đo được khí độc, nhiệt bên trong hoặc diễn tiến thời gian; “Normal” không phải bảo đảm an toàn vật lý. Những giới hạn này áp dụng chung cho cả bốn peers.

### 3.2. Hình 6 và S2/S3 đã được đọc trực tiếp

**VERIFIED:** đã đọc [PDF arXiv v2, trang 10, Figure 6](https://arxiv.org/pdf/2601.21173v2#page=10), và [supplement của publisher, S2 trang 3–4 / S3 trang 5](https://media.springernature.com/original/springer-static/esm/art%3A10.1038%2Fs41597-026-07796-x/MediaObjects/41597_2026_7796_MOESM1_ESM.pdf). S3 được xem dưới dạng hình, không chỉ OCR. Trang hình riêng của Nature gặp redirect/timeout; PDF arXiv và supplement truy cập được.

| Quan sát công khai | Diễn giải có giới hạn |
| --- | --- |
| Fig.6: Qwen3-VL-8B Instruct 0,6936; Thinking 0,7024. Cặp 32B: 0,6824 và 0,7688. | Chênh lệch tính từ hình là **0,88** và **8,64 điểm phần trăm**. Không gán câu “khoảng tám điểm” trong prose cho 8B; không chuyển Thinking vào C1. |
| Fig.6: Doubao 0,8128; paper báo 999/1.250 Normal. | Baseline luôn Normal tính từ aggregate = **79,92%**, so với 81,28% của Doubao; accuracy cao có thể che lỗi hazard. Đây không phải kết quả chạy baseline mới. |
| S3(i): Qwen3-8B Instruct, hàng Level IV có 27/73/122/772/5 ở I/II/III/IV/unrecognizable; hàng Level III 1/5/0/1/0. | Normal có false alarms lẫn unrecognizable; Level III chỉ support 7 và diagonal 0 trong hình. Không dùng accuracy chung để tuyển classifier bốn mức. |
| S3 có cột unrecognizable; S2 cho phép phản hồi không nhận diện được. | Cách xử lý missing/không rõ của bài báo khác C1 INVALID; không so valid-only score với planned-cohort score. |

Các số trên là **reported public benchmark**, không được dùng như kết quả, tuning target hay ngưỡng SafeShift. Figure 6 không đánh giá 12 checkpoint trong longlist này; Qwen3 mốc là ngoại lệ có tên tương ứng, nhưng service/runtime/revision paper không được chứng minh tương đương release SafeShift. Không chọn API đóng như Doubao/GPT/Gemini chỉ vì hình cao: chúng không cung cấp checkpoint local T4 theo phạm vi tuyển này. Qwen3 32B/235B không phải phương án FP16 hai T4 thực tế.

### 3.3. Bài báo, source tác giả và C1 không cùng một protocol

Đã resolve repo tác giả tại **`d2f66e0ada2edc4dc65c25213d37b00a4039910f`** và chỉ đọc code, không thực thi:
[generation](https://github.com/liuzy0708/InspecSafe/blob/d2f66e0ada2edc4dc65c25213d37b00a4039910f/model_api_generate_results.py),
[confusion parser](https://github.com/liuzy0708/InspecSafe/blob/d2f66e0ada2edc4dc65c25213d37b00a4039910f/model_confusion_matrix.py),
[semantic evaluation](https://github.com/liuzy0708/InspecSafe/blob/d2f66e0ada2edc4dc65c25213d37b00a4039910f/model_benchmark_evaluation.py).

| Thành phần | Paper/source tác giả — VERIFIED | SafeShift — VERIFIED |
| --- | --- | --- |
| Input/output | RGB + prompt; sinh mô tả cảnh và nhãn trong sections. S2 dùng `Level four`; source generation dùng `no abnormalities observed`. | C1 bắt đúng một JSON object, đúng key `safety_level`, một giá trị `Level01`–`Level04`, không mô tả/explanation/fence/extra key. |
| Parsing | Source confusion lấy từ cuối dòng cuối, bỏ một số dấu, có synonyms; chỉ join filenames chung và bỏ GT không parse được. | Không copy parser bài báo để “cứu” output. Giữ INVALID và planned-ID accounting hiện hành. |
| Evaluation | 1.250 TEST, accuracy và semantic similarity BGE-C03; source similarity đọc toàn văn TXT, skip empty, embedding error trả 0. | TRAIN lịch sử đã phơi nhiễm; C1 không sinh mô tả để đo SemSim. Không mở TEST hoặc chạy lại evaluator tác giả. |
| Reproducibility | Script generation gọi gateway API, temperature 0,1; source hiện tại chưa đủ xác nhận exact backend/checkpoint của mọi điểm Fig.6. | Pin model/source/template/generation, raw-before-parse. Không thay frozen settings để bắt chước paper. |

Các khác biệt source/S2/prose là **reproducibility questions**, không đủ chứng minh số paper sai. Không thực hiện denominator reconciliation bằng dữ liệu TEST.

C1 bytes tại BASE có SHA-256 **`816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3`**. Native image tokens/role delimiters phải được kiểm và ghi provenance quanh nguyên văn C1; không thêm reasoning instruction, examples, JSON grammar forcing, sửa ngành hoặc chuẩn hóa output. Nếu một candidate chỉ hoạt động sau sửa những nội dung đó: **BLOCKED / SCIENCE_DECISION_REQUIRED**, không tự áp dụng.

### 3.4. Giới hạn benchmark ảnh hưởng tuyển chọn

**VERIFIED từ bài báo:** normal/hazard lệch mạnh theo ngành; metallurgy hầu hết Normal; frame sampling trong inspection points và chất lượng annotation được kiểm qua mẫu. **UNVERIFIED:** các phép này không tự bảo đảm source-disjoint evaluation hoặc quan sát đầy đủ rare hazards. Không diễn giải nhiều frames thành nhiều nguồn độc lập.

**VERIFIED từ hồ sơ SafeShift, không tái audit data:** [source feasibility](../SOURCE_FEASIBILITY_GATE_20261024.md) và [results/limitations](../RESULTS_AND_LIMITATIONS.md) giữ vấn đề dependence/source identity, TRAIN exposure và coverage Qwen3. Vì thế final selection phải khóa trên development được cấp quyền, trước target độc lập; không chia lại TRAIN đã thấy rồi gọi holdout. Đa số model cùng nhầm glare/shadow/PPE nhỏ là giả thuyết hợp lý, nhưng correlation/shared errors phải đo, không khẳng định từ kiến trúc.

## 4. Longlist: identity, license và nguồn đã pin

**VERIFIED ở mức metadata:** 12 candidate IDs dưới đây resolve bằng API, tất cả public (`private=false`); chỉ Gemma `gated=manual`, các model khác `gated=false`. Card/config ở full revision được đọc qua anonymous GET. “Open access” ở đây không phải đã download/hash weights hoặc xác nhận quyền tài khoản Kaggle. Giấy phép là **khai báo publisher**, không chứng nhận pháp lý cho mọi downstream use.

Link tên model trỏ vào **card đúng revision**, tab Files dùng cùng SHA; file cụ thể và hash shortlist ở §10. Tên không rút gọn khi triển khai.

| ID | Checkpoint chính xác / nguồn sơ cấp | Full revision | License khai báo / access |
| --- | --- | --- | --- |
| C01 | [OpenGVLab/InternVL3_5-4B-Instruct][m1] | `a3fd3158be4027880d91ccee80ea8089559e0896` | Apache-2.0 checkpoint; source headers giữ MIT notices. Public. |
| C02 | [openbmb/MiniCPM-V-4][m2] | `6f69a8235885be89608f3a71ffd40695b379e1e7` | Apache-2.0; registration questionnaire optional theo card. Public. |
| C03 | [llava-hf/llava-onevision-qwen2-7b-ov-hf][m3] | `0d50680527681998e456c7b78950205bedd8a068` | Apache-2.0; HF integration, phân biệt bản tác giả `lmms-lab`. Public. |
| C04 | [HuggingFaceM4/Idefics3-8B-Llama3][m4] | `fddb4ff79181e55a994674777e06cd5456ce3dc3` | Card khai Apache-2.0, nêu parent Llama-3.1; không suy bỏ nghĩa vụ parent. Public. |
| C05 | [openbmb/MiniCPM-V-4_5][m5] | `daef484c35ec93210ec93c5e901f8f3e9b78ee34` | Apache-2.0; public. Không lẫn 4.0/quantized variants. |
| C06 | [allenai/Molmo-7B-D-0924][m6] | `cab33fb7f1a40091911f81165f8481920621948f` | Apache-2.0; public. Đây là D-0924, không O/quantized. |
| C07 | [Qwen/Qwen2.5-VL-3B-Instruct][m7] | `66285546d2b821cf421d4f5eb2576359d3770cd3` | **Qwen Research License**, không phải Apache; LICENSE nêu non-commercial research/evaluation. Public. |
| C08 | [microsoft/Phi-3.5-vision-instruct][m8] | `12b77fb40b63a2c73c68243d3f767aab688a1b2a` | MIT; public; revision khớp lock pilot. |
| C09 | [HuggingFaceTB/SmolVLM2-2.2B-Instruct][m9] | `482adb537c021c86670beed01cd58990d01e72e4` | Apache-2.0; public; revision khớp lock pilot. |
| C10 | [google/gemma-3-4b-it][m10] | `093f9f388b31de276ce2de164bdc2081324b9767` | Gemma terms, gated. **BLOCKED:** 7 file metadata được request lần này trả 401; không thay fact 10 file thất bại ở audit cũ. |
| C11 | [Qwen/Qwen3.5-4B][m11] | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | Apache-2.0; public. Kiến trúc hybrid mới; không thay Qwen3 mốc. |
| C12 | [openbmb/MiniCPM-V-4.6][m12] | `36f34a661a4bd35d0dc2294cb044d2584646c7d3` | Apache-2.0; public; Instruct, khác checkpoint Thinking. |

**Q3 mốc, không tính vào 12:** [Qwen/Qwen3-VL-8B-Instruct][q3], public Apache-2.0, revision public quan sát `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`. Đây là inventory observation, **không cập nhật source lock/run lịch sử**; equivalence với historical Q3 release phải đối chiếu riêng trước run mới.

C03 có nguồn [tác giả](https://github.com/LLaVA-VL/LLaVA-NeXT), [checkpoint gốc](https://huggingface.co/lmms-lab/llava-onevision-qwen2-7b-ov) và [tài liệu tích hợp chính thức Transformers 4.51.3](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/llava_onevision). Card HF có đoạn copy từ `si` và metadata mô tả BF16, trong khi checkpoint được chọn là `ov-hf`, tensor metadata F16. Dùng exact artifact identity, không suy hai bản byte-equivalent; conversion parity **UNVERIFIED**.

## 5. Khả năng nhận ảnh, bốn mức và triển khai: so đủ 12

### 5.1. Ma trận khả năng

**Quy tắc chung cho từng hàng:** RGB/interface và cơ chế image preprocessing dưới đây **VERIFIED trong card/config/source**, chưa native forward. Industry understanding, đúng bốn mức, phát hiện PPE/điện thoại thật và hữu ích kiểm tra chéo đều **UNVERIFIED**, trừ failure đã ghi rõ. Không một model card nào trong tập nguồn đã đọc cung cấp validation **đúng C1** của SafeShift.

| ID | Vision / chi tiết nhỏ / nhận ngành — cơ sở triển vọng, chưa hiệu quả thật | C1 và phân loại độc lập | Kiểm tra chéo / HNLO riêng | Quyết định nghiên cứu |
| --- | --- | --- | --- | --- |
| C01 | InternViT-300M + Qwen3; 448-pixel tiles, max 12 + thumbnail; 256 visual tokens/tile. Giữ global context cùng local views, nhưng seams/resize và instruction ngành còn phải kiểm. | **UNVERIFIED**; Instruct có đường hỏi ảnh, không cần thêm Thinking prompt. Native conversation khác tokenizer template. | Peers **UNVERIFIED**, có Qwen lineage chung với Q3; HNLO **UNVERIFIED**, logits interface không chứng minh alignment. | Ưu tiên 1, conditional. |
| C02 | SigLIP2 + MiniCPM4; 448 scale, tối đa 9 slices, 64 image features/slice trong config. Nén hiệu quả có thể mất chi tiết PPE. | **UNVERIFIED**; có image chat, nhưng wrapper tự đổi sampling/beam settings và xử lý text cuối. | Peers **UNVERIFIED**; backbone khác không bảo đảm lỗi độc lập; HNLO **UNVERIFIED**, raw-token custody cần đường native. | Ưu tiên 2, conditional. |
| C03 | SigLIP SO400M + Qwen2; 384 patches, `anyres_max_9`; giữ nhiều local views nhưng phải kiểm image-token grid/unpadding. | **UNVERIFIED**; instruction model và native HF generation; không áp ví dụ decode cắt cứng 2 tokens trong README. | Peers **UNVERIFIED**; Qwen2 chung lineage; HNLO **UNVERIFIED** dù có standard logits. | Ưu tiên 3, conditional, hai GPU. |
| C04 | SigLIP + Llama-3.1; longest edge 1456, tiles 364,169 tokens/tile. OCR/VQA có nguồn, không chứng minh hazard. | **UNVERIFIED**; card cảnh báo SFT-only có thể cần prompt iterations; các iterations/prefix gợi ý **không được áp vào C1**. | Peers/HNLO **UNVERIFIED**; architecture liên quan Smol, không suy cùng outcome. | Chưa shortlist: nặng hơn C03, instruction/parent-license questions chưa khép; không FAIL toàn model. |
| C05 | Qwen3-8B + SigLIP2, slices/64-query resampler; card hỗ trợ ảnh high-res và mode thinking tùy chọn. | **UNVERIFIED**; muốn fast mode phải khóa explicit flag/template, không strip reasoning để cứu JSON. | Peers/HNLO **UNVERIFIED**; Qwen3 backbone không chứng minh thêm thông tin cho Q3. | Chưa shortlist: 16,197 GiB FP16 chỉ tham số, custom multi-GPU + mode tăng rủi ro so C02. |
| C06 | CLIP + Qwen2; native 336 crop, `max_crops=12`; PixMo visual grounding là triển vọng, không ground-truth an toàn. | **UNVERIFIED**; custom `processor.process`/`generate_from_batch`, không lấy pointing làm C1. | Peers/HNLO **UNVERIFIED**; FP32→FP16 equivalence chưa kiểm. | Chưa shortlist: FP32 weights 32,084 GB; card kiểm FP32/autocast BF16, không bằng chứng T4 FP16 tương ứng. |
| C07 | Dynamic-resolution Qwen2.5 vision, 14 patch / merge 2; high-res có thể tăng activation rất mạnh. | **FAIL trong setting lịch sử được dẫn:** nhãn báo hazard cho toàn 3.014 Normal; C1 thesis mới **UNVERIFIED**. Không suy HNLO AUROC thành classifier tốt. | HNLO lịch sử có evidence, alignment cho setting mới **UNVERIFIED**; peers chưa chứng minh. | Chưa shortlist: prior behavior + cùng họ Qwen, không dùng để lấp slot. Roster cũ giữ nguyên. |
| C08 | CLIP HD crops, config 4 crops nhưng card single-image gợi ý 16; crop count phải theo lock, không âm thầm tăng. | **FAIL a6:** 0/160 strict C1; RGB calls thành công không cứu classifier. | Cross-check labels **FAIL trong a6** vì không có valid labels; HNLO **FAIL qualification a6**, không có valid alignment. | Không shortlist trước chẩn đoán #147 và authority mới. |
| C09 | SmolVLM/SigLIP, longest edge 1536, patches 384; 81 image tokens/patch. Card nhẹ không bảo đảm đọc PPE. | **FAIL a2:** 107/160 valid đều L01,53 INVALID; không xem diversity syntactic là đúng mức. | Utility **UNVERIFIED**, không qualified; HNLO **FAIL qualification a2**, continuation mismatch. | Không shortlist, không cứu dấu câu/parser. |
| C10 | Card Gemma3 khai ảnh 896,256 tokens; processor/pan-and-scan settings của exact pin chưa đọc được. | **BLOCKED** access; industrial/C1 behavior **UNVERIFIED**, không phải GPU FAIL. | Peers/HNLO **UNVERIFIED**, tokenizer evidence **BLOCKED**. | Không shortlist đến khi nguồn đầy đủ; không tự đăng nhập/chấp thuận terms. |
| C11 | Native vision + hybrid gated-delta/full attention; patch16/merge2. Có input ảnh nhưng runtime kernels khác Q3. | **UNVERIFIED**; thinking mode/template cần khóa; metadata `4.57.0.dev0` không chứng minh version đó hỗ trợ Qwen3.5. | Peers/HNLO **UNVERIFIED**; không coi mới hơn là complementary. | Chưa shortlist: chưa có exact compatible T4 stack/FP16 fallback đã kiểm; không loại vì cùng hãng đơn thuần. |
| C12 | 1,300B total theo Hub; SigLIP2/slices + Qwen3.5 text; nén token cao và ít tham số rất hấp dẫn cho quota. | **UNVERIFIED**; instruction checkpoint riêng, chưa chứng minh C1/khả năng đủ ở five-domain safety. | Peers/HNLO **UNVERIFIED**; hybrid state/logits validation mới. | Chưa shortlist: Transformers ≥5.7.0 và stack mới; source nhẹ không thay native CPU/T4 rehearsal. |

Không dùng “nhỏ hơn là yếu”, “lớn hơn là tốt” hoặc “khác backbone là độc lập” làm tiêu chí quyết định. C12 có thể thắng các ứng viên trên, nhưng tập bằng chứng hiện tại chưa cho phép kết luận đó. Longlist là tập sàng lọc hữu hạn, không danh sách tự động thử GPU cho đến khi tìm được winner.

### 5.2. Processor, tokenizer và library surface

| ID | Native model / tokenizer / processor đã quan sát | Phiên bản nguồn và vấn đề phải kiểm trước weights |
| --- | --- | --- |
| C01 | `InternVLChatModel`; `Qwen2Tokenizer`; `conversation.py` + `dynamic_preprocess` trong README, **không có AutoProcessor config ở pin**. | Card yêu cầu Transformers ≥4.52.1. `torch`, `torchvision`, `timm`, `einops`, `packaging`; optional FA2/apex phải kiểm fallback. Pin remote `.py`; `use_flash_attn=False` đặt vision non-FA2 và decoder eager trong constructor. |
| C02 | Custom `MiniCPMV`, `MiniCPMVTokenizerFast`, `MiniCPMVProcessor`/ImageProcessor. | Config lưu Transformers 4.51.0, **không phải compatibility certificate**. Torch/torchvision/Pillow/Transformers; remote tokenizer + processor + resampler. Card chỉ SDPA/FA2, không eager cho language path; source chọn vision eager khi không FA2. |
| C03 | `LlavaOnevisionForConditionalGeneration`, `Qwen2Tokenizer`, `LlavaOnevisionProcessor`. | Card ≥4.45.0; versioned 4.51.3 docs xác nhận API. Native Transformers, không cần model remote Python. Torch/torchvision/Pillow/Accelerate/tokenizers; inspect decoder **và** vision attention. |
| C04 | `Idefics3ForConditionalGeneration`, `PreTrainedTokenizerFast`, `Idefics3Processor`. | Card >4.46; API [4.51.3](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/idefics3). Config lưu 4.44.0.dev0 không là runtime đề xuất; native path/SDPA có docs, end-to-end **UNVERIFIED**. |
| C05 | Custom MiniCPMV/fast tokenizer/processor, Qwen3 text. | Config 4.51.0, exact end-to-end version **UNVERIFIED**; SDPA/FA2, custom cached vision và thinking flag phải cùng snapshot. |
| C06 | `MolmoForCausalLM`, `MolmoProcessor`, custom image processor, Qwen-family tokenizer. | Config 4.43.3; card thêm einops/torchvision, dùng `generate_from_batch`. Có cảnh báo vLLM preprocessing trong card, không tự thay framework. Exact FP16 stack **UNVERIFIED**. |
| C07 | `Qwen2_5_VLForConditionalGeneration`, `Qwen2Tokenizer`, `Qwen2_5_VLProcessor`. | Card có qwen-vl-utils 0.0.8; config 4.41.2 stale so model support. Không thay stack historical bằng `latest`; thesis stack **UNVERIFIED**. |
| C08 | `Phi3VForCausalLM`, `LlamaTokenizer`, `Phi3VProcessor`; remote CLIP path. | Card Torch 2.3.0/Transformers 4.43.0; repo pilot khóa Torch 2.6.0+cu124/Transformers 4.43.3/tokenizers 0.19.1. Cần shared loader fix a4/a5; không upgrade ngầm. |
| C09 | `SmolVLMForConditionalGeneration`, GPT2 tokenizer, `SmolVLMProcessor`. | Repo khóa Transformers 4.51.3/tokenizers 0.21.1/Torch 2.6.0+cu124, num2words 0.5.14/docopt 0.6.2. Config 4.47.1 không thay qualified lock. |
| C10 | Card dùng Gemma3 native class/AutoProcessor; exact tokenizer config **BLOCKED**. | Card hỗ trợ từ Transformers 4.50.0; repo dự kiến4.51.3. Không tuyên bố tokenizer/source PASS từ public README. |
| C11 | `Qwen3_5ForConditionalGeneration`, `Qwen2Tokenizer`, config trỏ Qwen3VL processor. | Card hướng Transformers source/main; chưa resolve immutable compatible implementation trong task này → **UNVERIFIED**, không dùng stored 4.57 làm pin. |
| C12 | `MiniCPMV4_6ForConditionalGeneration`, `Qwen2Tokenizer`, `MiniCPMV4_6Processor`. | Card/config yêu cầu Transformers ≥5.7.0. Card cảnh báo torchcodec/CUDA; still-image không tự cần video codec. Python/Torch/CUDA exact tuple **UNVERIFIED**. |

Mọi tokenizer/processor ở bảng mới chỉ được kiểm **source/config**, không chạy native encode/decode/vision processor. Riêng shortlist đã tải và hash vocabulary/tokenizer files không weights (§10); chưa chứng minh tokenization của bốn continuation hoặc JSON valid-rate.

## 6. T4×2: feasibility có điều kiện, không pooled 32 GB

**VERIFIED:** [NVIDIA T4 datasheet](https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-t4/t4-tensor-core-datasheet.pdf) mô tả Turing, 16 GB danh nghĩa và FP16. [FA2 v2.7.4.post1](https://github.com/Dao-AILab/flash-attention/tree/v2.7.4.post1#nvidia-cuda-support) không cung cấp đường CUDA T4 tương ứng. Không copy BF16/FA2 example trên A100 sang T4. [PyTorch SDPA](https://docs.pytorch.org/docs/stable/generated/torch.nn.functional.scaled_dot_product_attention) là dispatcher; gọi SDPA không chứng minh đang dùng FlashAttention, math fallback còn có intermediate FP32.

**VERIFIED arithmetic / UNVERIFIED peak:** cột dưới lấy `safetensors.total × 2 / 2^30`, tức chỉ dung lượng tham số **nếu** mọi tham số resident FP16. Chưa cộng KV cache, activations/vision, logits, allocator, kernels, buffers, temporary load hoặc offload staging. BF16→FP16 có thể overflow; F32→FP16 có thể đổi kết quả. Không weights nào đã được tải để tái đếm tensor.

| ID | Params Hub (tỷ) / dtype lưu | FP16 parameter-only GiB | Đường T4 đề xuất, chưa thử |
| --- | --- | ---: | --- |
| C01 | 4,732 / BF16 | 8,815 | Một T4 có triển vọng theo tham số; eager high-res activation vẫn có thể OOM. Không coi GPU thứ hai tự cứu. |
| C02 | 4,060 / BF16 | 7,561 | Một T4 có triển vọng; language SDPA + vision eager; kiểm FP16 finite. |
| C03 | 8,031 / F16 | 14,959 | **Không nhận single-T4 fit**. Shard modules/layers trên hai GPU, giữ margin riêng từng GPU. |
| C04 | 8,462 / BF16 | 15,762 | Hai-GPU model sharding; native dispatch chưa kiểm. |
| C05 | 8,696 / BF16 | 16,197 | Hai-GPU sharding; custom `.device`/vision-cache transfers cần rehearsal. |
| C06 | 8,021 / F32 | 14,940 | Native F32 riêng tham số ≈29,880 GiB, không có margin runtime phù hợp. FP16 split là giả thuyết mới. |
| C07 | 3,755 / BF16 | 6,994 | Tham số không phải blocker duy nhất; giữ lịch sử nonfinite/merger, không áp clamp mới. |
| C08 | 4,147 / BF16 | 7,724 | **VERIFIED a6 đúng envelope cũ:** GPU0 peak allocated 12,583/reserved 14,391 GiB, total 14,562; GPU1 unused. Không ngoại suy full run. |
| C09 | 2,247 / F32 | 4,185 | **VERIFIED a2 đúng envelope cũ:** GPU0 allocated 6.021.477.888/reserved 6.746.537.984 bytes; GPU1 unused. |
| C10 | 4,300 / BF16 | 8,010 | Metadata-only; access **BLOCKED**, chưa có measured T4 fit. |
| C11 | 4,660 / BF16 + chút F32 | 8,680 | Một T4 có thể đủ tham số, hybrid kernels/FP16/vision peak chưa kiểm. |
| C12 | 1,300 / BF16 | 2,422 | Rộng hơn về parameter budget, nhưng không native/behavior PASS. |

Q3 mốc: 8,767B, khoảng 16,330 GiB parameter-only FP16; không lấy Q3 OOM lịch sử làm bằng chứng tất cả model mới đều fail. Bằng chứng Phi/Smol ở [biên bản a6](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537) và [a2](https://github.com/tantdna2/SafeShift/pull/146#issuecomment-6485519647) là đọc aggregate, không re-audit private ZIP.

**UNVERIFIED — kế hoạch tài nguyên cho shortlist:** batch một ảnh, từng model tuần tự; không giữ cả bốn model resident. Với C03, cần map contiguous decoder blocks, vision/projector, embeddings/head và input/output transfers theo native modules; đo GPU0/GPU1 độc lập. `device_map="auto"` không đủ: kiểm `hf_device_map`, tránh CPU/disk fallback ngầm, giữ nguyên no-split blocks, finite/logits/image placement. DDP nhân bản model không cộng VRAM. [Accelerate 1.6 big-model inference](https://huggingface.co/docs/accelerate/v1.6.0/en/concept_guides/big_model_inference) hướng dẫn dispatch nhưng không chứng nhận checkpoint này trên Kaggle.

Điều kiện từng GPU: **weights trên GPU + KV + peak activations + output buffers + allocator margin < free memory thực**. Không ấn định một margin giả trước profiling. Tham số model có số “4B/7B” không gồm đúng cùng thành phần; dùng total ở metadata. T4 Phi từng báo chỉ 14,562 GiB usable, nên không dùng 16 GiB danh nghĩa làm giới hạn chắc chắn.

LFS metadata cho C01/C02/C03 lần lượt khoảng9,465/8,119/16,062 **GB** checkpoint; đây là disk/download dự kiến, không VRAM. RAM phải chứa load staging/offload nếu được duyệt; storage tách immutable evidence khỏi scratch cache, tính cả download bị hỏng và package cache. Không cộng nhầm F32 checkpoint size của Molmo/Smol thành runtime FP16 peak. Quantization/crop reduction/precision fallback chỉ là phương án cần duyệt riêng, không tự dùng để gọi T4 PASS.

**Runtime proposal, không lock mới:** worker CPython 3.11 hoặc 3.12 Linux riêng kernel Kaggle; C01 bắt đầu xem xét Transformers 4.52.1, C02/C03 xem xét4.51.3; tham khảo Torch 2.6.0+cu124/torchvision 0.21.0+cu124/Accelerate 1.6.0/Pillow 10.4.0 của repo. Các tuple này **UNVERIFIED đối với shortlist**, chưa pip-resolve/import/ABI/native rehearsal; timm/einops và dependency transitives chưa có lock. Không công bố “đã xác minh môi trường triển khai” từ bảng này. G2 phải pin đầy đủ, review exact implementation và thử CPU production path trước bất kỳ Kaggle session.

## 7. Shortlist: bằng chứng, bẫy và điều kiện giữ từng ứng viên

### Ưu tiên 1 — InternVL3_5-4B-Instruct (C01)

**VERIFIED:** [config][m1config] có dynamic image, 448/patch 14/downsample 0,5, thumbnail và 12 tiles; phép tính 256 tokens/tile khớp source. Card yêu cầu Transformers ≥4.52.1; source constructor dùng `use_flash_attn=False` để chọn decoder eager và vision non-FA2. Đây là lựa chọn nguồn thuận lợi hơn việc patch attention sau load kiểu Phi a5.

**UNVERIFIED — lý do ưu tiên:** multiscale input và instruction checkpoint tạo đường đánh giá chi tiết nhỏ/bối cảnh với 8,815 GiB parameter budget; chưa biết khả năng áp Table 3, obey C1 hoặc bổ trợ Q3. Qwen3 backbone chung làm independent-error claim đặc biệt không có căn cứ.

**Điều kiện trước G5:** model dùng `internvl2_5` conversation với system text sẵn có, không phải cứ `tokenizer.apply_chat_template` là tương đương. Metadata tokenizer còn chứa logic thinking; phải audit đúng đường `chat/get_prompt`, giữ C1 nguyên văn, không thêm R1 system prompt. Processor ở pin là recipe RGB/resize/normalize/tile trong README, không bịa `AutoProcessor`. Native CPU cần xác nhận cả 36 decoder và 24 vision layers, token `<IMG_CONTEXT>` ID 151671, tile-count↔256×tiles, mask/device/dtype, input envelope và raw IDs trước decode. 12 tiles + thumbnail không đồng nghĩa cả ảnh giữ nguyên độ phân giải. HNLO là nhánh optional chưa alignment.

### Ưu tiên 2 — MiniCPM-V-4 (C02)

**VERIFIED:** [config][m2config] và [processor][m2processor] khớp 5 trường image-feature-size/patch/use-image-id/max-slices/slice-mode khi kiểm CPU. Native source dùng 64-query resampling, language SDPA và vision eager ở non-FA2 path. Public tokenizer bytes đã hash.

**UNVERIFIED — lý do ưu tiên:**7,561 GiB parameter-only, backbone MiniCPM4 và xử lý slices là phương án khả thi đáng kiểm so C05 lớn hơn; không cho điểm đa dạng kiến trúc như một lợi ích đã đo.

**Điều kiện trước G5:** trong [modeling_minicpmv.py][m2code], `chat(processor=None)` gọi `AutoProcessor.from_pretrained(self.config._name_or_path, trust_remote_code=True)` không truyền revision. Native path phải nhận processor từ snapshot đã pin, không vô tình resolve `main`. `sampling=False` mặc định `num_beams=3`, `repetition_penalty=1.2`; không được mặc định nó bằng frozen greedy. API lọc kwargs nên phải kiểm giá trị **thực được dùng**, không chỉ kwargs request. `chat` trả decoded/stripped text; cần lưu raw generated IDs/bytes trước phần xử lý này. Nếu không làm được trong hợp đồng hiện hành, dừng để review adapter/science, không sửa C1. FP16 finite, SDPA dispatch và real compliance đều chưa kiểm.

### Ưu tiên 3 — LLaVA-OneVision-Qwen2-7B-OV-HF (C03)

**VERIFIED:** [config][m3config] và Hub tensor metadata là F16; native HF model/processor có tài liệu versioned, `anyres_max_9`, RGB conversion, image/video IDs 151646/151647 khớp added tokens. Cơ chế high-res thích hợp để **kiểm tra giả thuyết** về PPE nhỏ, không bằng chứng phát hiện PPE.

**UNVERIFIED — lý do ưu tiên:** FP16 checkpoint + native Transformers giảm một số rủi ro remote loader/mode so C05/C06; được xếp sau hai 4B vì 14,959 GiB parameter-only buộc giải quyết sharding. C04 cũng native nhưng nặng hơn và không có lợi thế C1 đã chứng minh; không loại C04 chỉ từ tuổi model/benchmark score.

**Điều kiện trước G5:** khóa exact HF conversion; card có template text và processor multimodal riêng, phải kiểm đường processor thật. Trong README có `output[0][2:]`; không copy offset cố định vì C1 dài khác ví dụ. Phải slice từ prompt length thật, lưu generated IDs nguyên vẹn, kiểm image-token count/patch grid/feature packing và EOS. Không tin `anyres_max_9` nghĩa là mọi bước vision chỉ có 9 crops: config grid có 36 aspect/resolution combinations, encoder/feature packing phải đo actual shapes. Native eager/SDPA, effective attention cả text/vision, cross-device transfer và peak mỗi T4 chưa kiểm. HNLO cũng chưa validated.

**Không ứng viên nào được bypass G2 vì có tên native class, bypass G5 vì CPU PASS, hoặc bypass P3 vì “khác family”.** Nếu một trong ba không thể giữ nguyên C1, slot đó để trống; việc xem lại C04–C12 cần O3/attempt cap, không vòng tìm kiếm vô hạn.

## 8. Học từng failure Phi, Smol, Gemma trước khi tốn Kaggle

Nguồn chuẩn: [failure register tại BASE](https://github.com/tantdna2/SafeShift/blob/1488dcb5212164e2946a15055d1da6e8be9096d2/docs/KAGGLE_FAILURES_AND_RELEASE_GATES.md). **VERIFIED** dưới đây nghĩa là đối chiếu public records, không tái tạo sự cố GPU hoặc kiểm private raw. Model-vs-integration root cause chưa rõ vẫn **UNVERIFIED**.

| Sự cố | Điều đã biết / chưa biết | Chặn tương tự trước hoặc ngay đầu lượt có quyền |
| --- | --- | --- |
| Phi a1 | Consumption được ghi; symptom/cause không đủ nguồn. | Không bịa root cause. G3 phải giữ stage/traceback/partial evidence để incident sau có thể chẩn đoán. |
| Phi a2 | **FAIL runtime:** kernel 3.13 không phù hợp worker 3.11/3.12; consumed dù 0 inference. | G2 kiểm chính interpreter con, wheel ABI/import/pip check; G4 lặp lại worker thực trước ledger nơi kỹ thuật cho phép. |
| Phi a3 | **FAIL bootstrap, FAILED_PRELEDGER:** venv có nhưng ensurepip thiếu. | Fresh venv `--without-pip`, pip wheel hash-lock vào đúng target; kiểm pip executable/prefix, không chỉ `import venv`. Không gọi a3 consumed. |
| Phi a4 | **FAIL load:** checkpoint/vision dispatch vẫn FA2 dù request eager; cơ chế CPU có reproduction. | G2 actual deserialization/production loader; assert effective attention từng subsystem, không chỉ request kwargs. |
| Phi a5 | **FAIL sau load shards:** AutoModel dynamic reload làm mất CLIP patch, vision SDPA drift. | Native shared loader/class provenance qua đúng AutoModel/direct path; mock constructor hoặc patch trước reload chưa đủ. Shortlist remote code cũng phải kiểm vấn đề này. |
| Phi a6 | **FAIL C1:**160 calls, 0 valid; 8 sequences, 142 lần cùng sequence; 64-token outputs; HNLO validated 0. **UNVERIFIED** căn nguyên behavior. | G3 scripted invalid/repetition/truncation/NaN tests; G5 first-image + stage nhỏ kiểm validity và behavior theo stop đã duyệt. first 12 technical PASS không được vượt behavior FAIL; không chờ hết 160. |
| Smol native readiness | **FAIL CPU dependency:** thiếu num2words/docopt, sau đó pin và kiểm production processor. Không gọi đây là GPU failure. | G2 import **và chạy processor** trên synthetic RGB/RGBA/ext-mismatch/envelope, native tokenizer/template; transitive packages phải lock. |
| Smol a1 | Hồ sơ giữ RESERVED/NOT_EXECUTED lịch sử, không là permission của source mới. | G0/G6 không reuse attempt hoặc suy quyền từ tên model. |
| Smol a2 | **FAIL qualification:**107 valid toàn L01,53 INVALID; 2 responses. HNLO continuation mismatch quan sát được, căn nguyên collapse **UNVERIFIED**. | G5 xem GT Normal/hazard/support, confusion, invalid và repetition cùng nhau. G3 test leading whitespace/EOS/extra punctuation/full continuation; valid JSON không đảm bảo HNLO mapping. Không buộc batch nhỏ phải có đủ 4 output labels. |
| Gemma | **BLOCKED source:**10 file 401 ở lịch sử; lần này 7 request metadata 401. README public không là quyền tải tokenizer. Chưa GPU failure. | G2 anonymous/authenticated approved allowlist read/hash trước weights. Kiểm quyền riêng từng account nhưng không log token; không sinh lock từ file chưa đọc. |

Phi a6/Smol a2 **CONSUMED / NO_GO_FULL_TRAIN**, không reset/retry. Không strip prose/dấu câu hoặc dùng first label token để cứu. HNLO=0 validated không có nghĩa không từng capture logits, và sửa surface alignment cũng không tự sửa label collapse. #147 giữ trách nhiệm chẩn đoán; task này không chốt nguyên nhân thay #147.

Các sự cố khác trong register vẫn là đối chứng thiết kế gate: Q3 nested mount→G1/G3 synthetic path layout; Q3 OOM→G2/G5 input envelope/per-GPU peak, không hứa chặn mọi allocator failure; InternVL driver lookup→G4 actual child loader; Q25 nonfinite→G5 finite first-step và custody; Moondream ValueError thiếu traceback→G3 error-chain retention. Không import fix legacy vào new runtime.

## 9. Phân loại độc lập, peers và nghiên cứu sau tuyển: proposal, không protocol mới

### 9.1. So hai thiết kế đúng lịch sử

Thiết kế A là **bản đề xuất cũ** Qwen3 fixed + tối đa một auxiliary tại [HEAD6b7b3b9 của #137](https://github.com/tantdna2/SafeShift/blob/6b7b3b9828a61440cb60733fe4640d9a237db0e0/docs/research/THESIS_EXECUTION_PLAN_2026.md). Thiết kế B là [bản ngang hàng đã merge nhưng vẫn PROPOSED](THESIS_EXECUTION_PLAN_2026.md). Không nói #137 hiện vẫn Draft hoặc bản merged vẫn cố định Q3.

| Vấn đề | A: fixed Q3 + auxiliary | B: bốn peers / focal rotation / ensemble và review |
| --- | --- | --- |
| CT1 chất lượng nhãn | Cải thiện xếp review chưa chứng minh sửa classification. | Đo từng classifier và ensemble vs dev-best single trực tiếp; chưa biết có cải thiện. |
| CT2 phương pháp | Hẹp hơn: feature của auxiliary cho lỗi Q3, ít contrasts. | Bốn focal, shared-error/leave-one-out/missingness; nhiều comparisons hơn, cần multiplicity plan. Voting tự thân không mới. |
| CT3 chức năng | Viewer/error review cho một focal dễ giới hạn hơn. | Viewer bốn labels/abstain/provenance, reviewer load lớn hơn; expert/user study và consent chưa có. C1 không cung cấp rationale/boxes, không bịa chúng. |
| Nguồn/GT/leakage | Cần development/calibration/target độc lập và đủ lỗi Q3. | Cùng yêu cầu, cộng support theo focal/miền/mức; số model không tăng số nguồn độc lập. |
| Compute | Q3 + tối đa 1 auxiliary; nếu chạy mọi mẫu là khoảng 2N calls. | Khoảng 4N classification calls, reuse cùng outputs cho 4 focal; không mặc định 16N hoặc peer tự sinh lần nữa. Tổng cost gồm failed candidates, load, HNLO nếu cần, storage và review. |
| Nghiệm thu | Dễ thu hẹp, nhưng vẫn cần học vụ chấp thuận. | Khớp ý định Owner mới hơn; không chứng minh novelty/academic acceptance hoặc lợi ích hơn A. Không đủ 4 qualified→negative feasibility và quyết định scope. |

**UNVERIFIED — khuyến nghị:** giữ B làm phương án để giảng viên/Owner review, một primary contrast và các secondary rõ ràng theo plan hiện hành. Không tự triển khai learned voting/weighted ensemble/threshold. Nếu không đủ nguồn/qualified/cost thì trình giảm scope **trước target**, không chọn A sau khi nhìn kết quả target cho đẹp.

### 9.2. Bằng chứng cần có cho từng tầng, chưa được chạy

1. **Independent classification:** cùng original IDs và planned ledger, C1/raw/config nguyên vẹn; báo 4×5 confusion, valid/INVALID/no-output/technical error/not-attempted, support/coverage, false-safe và severe errors theo domain/level. Các metric Macro-F1/BA/FPR/FNR cần đúng O2/frozen definitions, không tự biến đề xuất thành metric production. So trên toàn planned cohort và common evaluable IDs, không giấu failures bằng complete-case riêng từng model.
2. **Peer checking:** mỗi model làm focal một lượt, ba model khác là peers. Đếm lỗi focal được peers phát hiện thêm, focal đúng nhưng bị phản đối, shared mistakes và missed errors; báo mẫu số khi peers thiếu/INVALID. Disagreement chỉ tín hiệu, không là GT. Kiểm binary/ordinal và leave-one-out nếu được duyệt; chưa có paired predictions thì complementary utility của **từng** C01/C02/C03 vẫn UNVERIFIED.
3. **Fusion khác review triage:** so rule hợp nhất được phê duyệt với strongest single chọn trên development, có abstain/missing policy khóa trước; review capture so ở cùng ngân sách và full model cost. Một model làm triage tốt nhưng classifier yếu không tự đủ tiêu chí slot ngang hàng. Nếu ensemble thua single hoặc chi phí không đáng, giữ kết quả âm; không đổi primary sang review hậu nghiệm.

Bốn focal, nhiều domains và ablations tăng multiple testing. O2/O5 phải định primary/secondary, correction/CI, independent sampling unit, source clusters và thiếu support trước target. Không tự coi frame độc lập, tự đặt thresholds/counts hoặc dùng TRAIN lộ/TEST làm target. D/V/T/U và expert labels theo O4, còn **BLOCKED**. Selection protocol khóa development-only trước target; reviewer có quyền kiểm GT nhưng model không nhận GT hay nhãn của peers trong lượt independent.

### 9.3. HNLO optional, không trộn với hai tầng trên

**UNVERIFIED cho shortlist:** có `forward().logits` hoặc tokenizer vocabulary chưa đủ. Cần exact C1 continuation, decision prefix/vị trí thật, full token surfaces của cả 4 labels, finite raw logits, valid generated label, replay/oracle độc lập và provenance. Default decoding/strip/leading-space có thể khiến alignment sai như Smol. Nếu chưa có endpoint tương đương thì HNLO N/A, vẫn có thể đánh giá label-only classifier/peers sau khi qualified riêng.

Không trung bình raw logits/HNLO khác tokenizer, không lấy self-reported confidence thay score, không suy HNLO AUROC thành C1 accuracy hoặc independence. Q3 HNLO lịch sử giữ giới hạn saved-score/coverage; không tự kế thừa cho thesis cohort. C07 historical score không khắc phục classification failure. HNLO comparisons mới cần O2/O3, không sửa surfaces cũ.

## 10. Kiểm CPU đã làm và bằng chứng tái kiểm công khai

**VERIFIED — thực chạy:** Windows, CPython 3.11.9; stdlib urllib/JSON/AST/SHA-256 và Jinja2 3.1.6. Không Torch/Transformers/tokenizers được cài trong interpreter này; không cài thêm. Thu 13 Hub metadata records; 114 allowlisted source/config/card files HTTP200,7 HTTP401 Gemma; thêm 9 tokenizer files shortlist HTTP200. Hash kiểm lại **123/123 file đã tải**, parse **69 JSON**, AST syntax **27 `.py`** không import. Đây không phải full source security review hay native load.

Kiểm nhất quán C02 config–processor **5/5**; C01 image tokens/tile256 và `<IMG_CONTEXT>`151671; C03 image/video token IDs 151646/151647. Render Jinja **text-stage** của C02/C03 giữ C1 nguyên văn đúng 1 lần trong wrapper tổng hợp; chưa chạy tokenizer hay native multimodal processor, nên không xác nhận full rendered prompt/image tokens/runtime. Không dùng Jinja tokenizer template của C01 thay native conversation.

Local research files ở `data/processed/issue148_public/` (ignored), chỉ nguồn công khai/receipts/script kiểm một lần; không commit upstream source hoặc PDF. Receipt SHA-256: metadata/source `6217b41f719f3dbed40bfaec8f46e7ce8acb7c9e37cef77ec2ccdc53693b9328`; tokenizer `4b41baabb790b0ab565795d80dbf17d1f154635ae6e639756f2067372cd30ed2`; CPU `a2936516a910b7a772ba3013086ed1c7950dbf7519fff1c5abead92e0312efd4`. Các hash local chỉ xác định receipt, không yêu cầu reviewer tin file không có trên GitHub; nguồn pinned và các kết quả cốt lõi nằm ngay báo cáo.

### File receipts quan trọng cho ba ưu tiên

Tất cả URL file được xây bằng mẫu `https://huggingface.co/{exact_model_id}/resolve/{full_revision}/{filename}` từ §4; không dùng `main`. Links config/processor/source bên dưới và cards ở §4 dẫn đúng revision. Giá trị SHA là bytes trả từ GET, không tensor checkpoint hash.

Reviewer có thể tái kiểm một receipt bằng Python chuẩn như dưới đây; chỉ đọc public `config.json` vào RAM, không tải weights hoặc chạy remote code. Đây là ví dụ tái kiểm, không thay các native checks còn thiếu. Để kiểm file khác, dùng đúng model/revision/filename và expected SHA ở hai bảng tương ứng.

```python
import hashlib
import json
from urllib.request import Request, urlopen

model = "OpenGVLab/InternVL3_5-4B-Instruct"
revision = "a3fd3158be4027880d91ccee80ea8089559e0896"
filename = "config.json"
expected = "e6caafa67e776f07635197c68d3bad44f2d60a9415d3188cc284d64688a35c2c"
url = f"https://huggingface.co/{model}/resolve/{revision}/{filename}"
with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
    raw = response.read(1_000_001)
assert len(raw) <= 1_000_000, "Unexpected config size"
assert hashlib.sha256(raw).hexdigest() == expected, "Receipt mismatch"
print(json.loads(raw)["architectures"])
```

| ID / file | SHA-256 đã kiểm |
| --- | --- |
| C01 `config.json` | `e6caafa67e776f07635197c68d3bad44f2d60a9415d3188cc284d64688a35c2c` |
| C01 `tokenizer_config.json` | `2d0129d708f6433a0b09f1fc346d3e3c834e2b0ae6f817ad5b491779e39299ab` |
| C01 `vocab.json` | `87a257b04b17642a0688c98cd1df89c398bda4fee532d6f88b38a659ecb4ac8d` |
| C01 `merges.txt` | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` |
| C01 `added_tokens.json` | `e5c2531bd62d25dd2a7401203a20f7ffb0976a026299cb4d6ff2d559d7ac3e28` |
| C02 `config.json` | `a83a83259378c2684a96ce3a6cb96d418a1d97f46118af3aff2ac1222fc783b8` |
| C02 `preprocessor_config.json` | `1d9513a6613e3919dda231a4ea935073122fd92107ab5342abd8ab3c212ca8f5` |
| C02 `tokenizer_config.json` | `c13da6ff468cfed3d14eeccd4198cc304305660281cb91dc280aeb332e4d67e4` |
| C02 `tokenizer.json` | `028e74a0efb7bbe99dc7e8b5c216c5fe54da231f80f41bb658e21326883503f3` |
| C02 `tokenizer.model` | `63099373ce6901674187ba3d7233c5970a253e8e0874056823bf0d3abc8d96a1` |
| C03 `config.json` | `69277c2c9ba8a4f61d2e72f79fbe02e043b8c3af670858a606818527f971a0c2` |
| C03 `preprocessor_config.json` | `3644c108b9f0fa53e62ff422a9be6639642f0e64dab4a71f961c7911d4386384` |
| C03 `tokenizer_config.json` | `b3151cdc153a44fa4e28abc8fc83567fc663aef7cd9dc041f5d66e617fe10b8e` |
| C03 `tokenizer.json` | `3c0ce3213b50ff38d8aa1e91136a2d2cb142a3f569246170872e439cb2a29d15` |
| C03 `vocab.json` | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` |
| C03 `merges.txt` | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` |
| C03 `added_tokens.json` | `33e0fb93dadacb864bd2f2e8441e147daa2baceb67f94d3ef5283b495572cea0` |

**Giới hạn kiểm tra:** không native CPU processor/tokenizer, empty-weight constructor, pip ABI rehearsal, CUDA driver, allocation, FP16 forward, raw custody mới, output behavior, HNLO replay hoặc performance. Không chạy full repo inference/native opt-ins hoặc CPU saved-score audit vì không thay code và không được mở artifact riêng. Native checks phải báo NOT_RUN, không gộp với static PASS.

## 11. Quy trình G0–G6 phải qua trước lần chạy thật

Giữ **đúng tên/nghĩa G0–G6 của [runbook](../KAGGLE_FAILURES_AND_RELEASE_GATES.md)**; không tạo bộ gate khoa học trùng tên. T0/O1–O8 và P1–P4 là các quyết định/qualification bổ sung ở plan, không gate đã vượt bởi báo cáo này.

| Gate / người chịu trách nhiệm | Bằng chứng cần có và điều kiện dừng | Trạng thái tại Draft |
| --- | --- | --- |
| G0 Science + authority — Research Lead | Duyệt exact model/revision, C1/parser/preprocessing/metrics, cohort rights, release/run/attempt, counts/cost/stop; O1–O8/T0 theo scope. Thiếu quyền → dừng. Quyền research hiện tại không là grant. | **VERIFIED** research-only authority; **BLOCKED** execution/science approval. |
| G1 Git + notebook — developer/reviewer | Source SHA sạch, diff đúng scope, builder/payload hash, compile/static tests; notebooks reproducible, outputs rỗng, fresh Save & Run All. Không tạo notebook trong #148. | **VERIFIED** report source BASE; executable release cho shortlist **UNVERIFIED / NOT_PREPARED**. |
| G2 Source + environment — runtime reviewer | Public allowlist/license/code/tokenizer hash đầy đủ; fresh worker/pip/ABI; native production loader, image processor và template với synthetic RGB/RGBA, portrait/landscape, 1×1, lớn, PNG mang đuôi jpg; exact attention/layers/dtypes/image tokens/context. Thiếu native evidence → không đến GPU. | Source facts một phần **VERIFIED** (§10); native stack **UNVERIFIED**; Gemma access **BLOCKED**. |
| G3 Failure + custody — developer/reviewer | Dùng lại runner/artifact tests, bổ sung khi adapter thực sự được giao: 4 labels/INVALID/duplicate-extra keys/whitespace/EOS/truncation/repetition/NaN/OOM/load-write-export failure. Raw durable trước parse, traceback không locals/secrets, partial bytes/ledger/checksums/no overwrite. | Thiết kế kiểm tra, **UNVERIFIED** cho adapters mới; không claim suite/native PASS từ static metadata. |
| G4 Kaggle preledger — operator có quyền | VM/runtime/driver trong worker thật, 2 T4 và free memory từng GPU, RAM/scratch/output/source/access/input hashes, không stale cache; kiểm trước consumption nơi cho phép, recheck trong worker. | **BLOCKED**: không có VM/GPU authority mới; không chạy Kaggle. |
| G5 Small real-GPU qualification — operator + reviewer | Sau G0–G4 và grant riêng: một model/một cấu hình/một attempt, first-image finite/shape/raw/format → stage nhỏ technical **và behavioral** đã duyệt → review mới mở stage lớn. Đo support/validity/repetition/GT-stratified errors/latency/peak mỗi GPU; HNLO riêng nếu có quyền. Fail stop, không auto-retry/tune. | **BLOCKED / NOT_RUN** cho shortlist. First12 là bài học gate lịch sử, không tự đặt 12 hoặc 160 là batch mới. |
| G6 Release + postrun — independent reviewer | Pre-run review đúng hashes/quyền; postrun reconcile tất cả planned IDs/status/raw/partial evidence, outer/member SHA/CRC/source/env/consumption. Tách CODE_PASS, real technical, C1 quality, HNLO và utility; pilot không tự mở full run. | **BLOCKED** cho execution; Draft research chờ ChatGPT kiểm trực tiếp GitHub. |

**Trình tự stage G5 đề xuất, chưa được phê duyệt:** mở đầu bằng một ảnh có quyền để phát hiện load/shape/nonfinite/empty/truncated/raw-write failure, rồi panel nhỏ có Normal và hazard, bao phủ aspect/resolution/tile envelope và các ngành/mức khi có support hợp pháp. Reviewer phải định trước số mẫu tối đa/thời gian, tiêu chí validity/quality/cost, cách xử lý support thấp và điểm dừng trước khi xem outputs. Không ép mô hình phải phát ra đủ 4 nhãn trong một panel nhỏ. Sự lặp nhãn là tín hiệu cần đối chiếu GT và support, không bằng chứng tự thân của lỗi integration. Không dùng ảnh TEST, private bundle hay grant pilot cũ để lấp panel.

Việc tiết kiệm Kaggle đến từ **thứ tự gate và dừng sớm có phê duyệt**, không từ giả vờ CPU chứng minh hành vi thật. Nếu native CPU không thể dựng đúng production path hoặc không có input envelope đã cấp quyền thì **BLOCKED trước GPU**. Sau một lần consumed, failure vẫn giữ consumed kể cả 0 valid; mọi sửa source/config cần review và authority mới, không chuyển sang candidate dự bị tự động.

## 12. Những quyết định còn thiếu và bàn giao

| Quyết định | Chủ thể / bằng chứng cần thêm | Trạng thái |
| --- | --- | --- |
| Chấp nhận thiết kế bốn peers, primary/secondary và negative-result route theo CT1–CT3 | Owner/giảng viên, O1/O2/T0; báo cáo này không ký thay. | **BLOCKED** triển khai xác nhận. |
| Chấp nhận shortlist và thứ tự qualification; final roster | O3 sau ChatGPT review nguồn; final roster chỉ sau P1–P4 development evidence. | **UNVERIFIED** qualification; **BLOCKED** official promotion. |
| Nguồn độc lập, rights/GT/custodian, development/calibration/target, reviewer availability | O4/O7; không dùng TRAIN đã lộ hoặc TEST thay nguồn mới. | **BLOCKED**. |
| Exact runtime, image envelope, numeric stop/precision/cost và từng run grant | G2, O5/O6; source-only observation chưa đủ. | **UNVERIFIED** runtime, **BLOCKED** execution. |
| HNLO cho từng model | Native actual continuation/logit/replay evidence và O2 scope. | **UNVERIFIED**, optional; không chặn label-only nếu classification đủ điều kiện. |
| Chẩn đoán Phi/Smol và xử lý #136 | #147 và O8 thuộc task/PR riêng. | **BLOCKED** trong phạm vi #148; không tự sửa/đóng. |

Draft PR chỉ chứa báo cáo này và [PROJECT_STATE](../PROJECT_STATE.md). C1, parser, HNLO, M2, labels/split/metric/roster, source locks, notebooks và grants không thay đổi. BASE/HEAD, file inventory và các kiểm tra tài liệu thực chạy ghi trong PR body để tránh hash tự tham chiếu. **Dừng ở Draft PR để ChatGPT kiểm GitHub, từng checkpoint và bằng chứng; không merge, không chuyển Ready, không bắt đầu qualification.**

### Nguồn model đã pin

Các citations dưới đây là model cards/source artifacts đã đọc, không là xác nhận kết quả SafeShift. Các paper về model được kiểm như nguồn thiết kế, không đem benchmark số của chúng vào ranking task safety: [InternVL3.5](https://arxiv.org/abs/2508.18265), [LLaVA-OneVision](https://arxiv.org/abs/2408.03326), [MiniCPM-V4.5](https://arxiv.org/abs/2509.18154). Các nguồn còn lại đã đặt cạnh claim trong báo cáo.

[m1]: https://huggingface.co/OpenGVLab/InternVL3_5-4B-Instruct/blob/a3fd3158be4027880d91ccee80ea8089559e0896/README.md
[m2]: https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/README.md
[m3]: https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf/blob/0d50680527681998e456c7b78950205bedd8a068/README.md
[m4]: https://huggingface.co/HuggingFaceM4/Idefics3-8B-Llama3/blob/fddb4ff79181e55a994674777e06cd5456ce3dc3/README.md
[m5]: https://huggingface.co/openbmb/MiniCPM-V-4_5/blob/daef484c35ec93210ec93c5e901f8f3e9b78ee34/README.md
[m6]: https://huggingface.co/allenai/Molmo-7B-D-0924/blob/cab33fb7f1a40091911f81165f8481920621948f/README.md
[m7]: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/66285546d2b821cf421d4f5eb2576359d3770cd3/README.md
[m8]: https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/README.md
[m9]: https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/README.md
[m10]: https://huggingface.co/google/gemma-3-4b-it/blob/093f9f388b31de276ce2de164bdc2081324b9767/README.md
[m11]: https://huggingface.co/Qwen/Qwen3.5-4B/blob/851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a/README.md
[m12]: https://huggingface.co/openbmb/MiniCPM-V-4.6/blob/36f34a661a4bd35d0dc2294cb044d2584646c7d3/README.md
[q3]: https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b/README.md
[m1config]: https://huggingface.co/OpenGVLab/InternVL3_5-4B-Instruct/blob/a3fd3158be4027880d91ccee80ea8089559e0896/config.json
[m2config]: https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/config.json
[m2processor]: https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/preprocessor_config.json
[m2code]: https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/modeling_minicpmv.py
[m3config]: https://huggingface.co/llava-hf/llava-onevision-qwen2-7b-ov-hf/blob/0d50680527681998e456c7b78950205bedd8a068/config.json

### Phương pháp hỗ trợ

Sử dụng `literature-review` 1.11 để giữ nhật ký tìm kiếm/provenance và `scientific-critical-thinking` 1.5 để phân biệt quan sát–suy luận, mẫu số và giới hạn applicability. Không áp GRADE/RoB y khoa như một numerical model-ranking score. Nguồn phần mềm/phương pháp: Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065); metadata đã kiểm, current record v2, không dùng paper này làm evidence cho khả năng VLM.
