# MiniCPM Full-TRAIN — Owner UI

**PR #195 đã MERGED tại `6744c319152743f399c79f6c8b16acb527d5acb4`.** Owner
báo ChatGPT xác minh hậu merge PASS. Đây là nghiệm thu mã nguồn; quyền chạy
MiniCPM Full-TRAIN, caps và provider hiện tại vẫn **BLOCKED**. Lượt tiếp nối
16/11 chỉ CPU, một Draft PR mới. ChatGPT kiểm GitHub và quyết định audit độc lập,
sau đó mới xét quyền merge/phát hành riêng. Xem
[gói phát hành, chứng từ thiếu và lệnh kiểm CPU](MINICPM_FULLTRAIN_RELEASE.md).
Không xóa `contract.authorize`, dùng JSON
`approved=true`, hoặc chuyển grant InternVL/Candidate160 sang MiniCPM.

## Owner làm đúng ba bước sau khi nhận bản đã phát hành

1. Import `notebook.ipynb` Antigravity bàn giao; gắn đúng **năm Input/version**
   ghi trong handoff bên dưới, gồm capsule riêng của lượt này.
2. Kiểm tra **Private, Python, Internet On, GPU T4 x2** và giới hạn lượt đã giao.
3. Chọn **Save Version → Save & Run All đúng một lần**; gửi URL/version khi xong.

Owner không sửa cell, request, batch hoặc parser. Nếu BLOCKED/lỗi, giữ toàn bộ
Output/log/ZIP; không bấm lại hay tạo version tiếp. Antigravity đối soát trước.

## Input dùng lại

| Loại | Ref/version | Kiểm bytes và giới hạn bằng chứng |
| --- | --- | --- |
| Dataset TRAIN | `nguynanhtn/inspecsafe-v1-kaggle/1` | 3.763 JPG theo master/order/SHA gốc; không đọc TEST |
| Dataset master | `nguynanhtn/safeshift-pilot-input/1` | `master_manifest.json`, SHA `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`; không lấy pilot160 làm full |
| Notebook Output checkpoint | `nguynanhtn/safeshift-prepare-minicpm4/1` | Marker `6ff382a6d1951d8224221c7ab1b4cb77830efb7abd5c1a72166482ed3a133040`; source revision và hai shards theo lock Issue173 |
| Dataset CPython | `nguynanhtn/safeshift-cpython3119-20240726/1` | Cùng transport Base64/manifest/archive SHA của InternVL; không tải Python từ GitHub |
| Dataset capsule riêng | `nguynanhtn/safeshift-minicpm-capsule-<luot>/1` | Marker/request/cohort và mọi ancestor; hash khóa trong notebook; chỉ xuất bản sau release |

Hai version Dataset `/1` được đối chiếu từ **metadata local đã lưu của lượt
InternVL23**, không phải mới hỏi Kaggle: capsule lịch sử SHA
`8e277b16f46c750c1411371a2bfcec191606f07424ecb98348a455e6c22fa09c`.
Metadata checkpoint MiniCPM đã lưu: ref đúng, `currentVersionNumber=1`,
`isPrivate=true`, SHA
`a79db081d2d5eb91d315c28ca1f442b970eb880dedb0acf2cbf5b3c63b00a135`.
Đây là evidence phiên bản lịch sử; **không phải quyền thực thi hay quan sát provider
hiện tại**. Operator phải xác minh metadata/version/rights/bytes trước phát hành.
Không tạo Dataset TRAIN/checkpoint mới hoặc tải lại weights.

## Antigravity chuẩn bị → Owner chạy → Antigravity thu → chuẩn bị lượt kế

Dùng đúng conversation đã lưu; không mở session mới để giành quyền chạy. Luồng
này dùng lại fresh171 controller, native adapter, history verifier và các primitive
provider/transport Owner UI của InternVL. Không có scheduler hay ledger khoa học
mới. Handoff/capsule là metadata candidate, không phải PUSH_INTENT/SUBMITTED hoặc
COLLECTED/MEASURED. Không sửa ledger, notebook hay checkout Operator InternVL.

1. **Chuẩn bị offline.** Đọc projection TRAIN đã được custodian seal riêng, policy
   tài nguyên và caps có quyền. `plan` dựng request/identity từ code hiện tại;
   worker vẫn phải tái lập projection từ đúng master SHA trước ảnh. `prepare`
   kiểm source commit, plan, mọi ancestor ZIP/sidecar/custody và xuất cùng nhau:
   `notebook.ipynb`, `kernel-metadata.json`, `dataset/`, `dataset-metadata.json`,
   `handoff.json`. Capsule chỉ có marker và ancestor `.bin` cùng sidecar; `.bin`
   giữ nguyên bytes ZIP để tránh Kaggle tự bung archive. Chỉ công bố nội dung
   `dataset/`; metadata CLI ở thư mục cha, không lẫn vào Input.
2. **Đối chiếu gói phát hành.** Chạy `minicpm_fulltrain_release template/check`
   theo tài liệu liên kết trên; kiểm toàn bộ packages và cả hai cặp ZIP của mỗi
   lượt trước, không chỉ receipt do `next` đọc. Ngân sách cộng maxima đã dành
   trước của từng job, kể cả phần chưa dùng; không hoàn calls/time sau INVALID,
   lỗi hay abort. Một quyền campaign có thể bao trùm các lượt resume serial trong
   caps; không xin quyền khoa học mới từng shard. Công cụ CPU chưa reserve hoặc
   cấp quyền chạy. Xác minh Private/version1 của capsule, đúng năm Input,
   request/capsule/notebook/source SHA, quyền dữ liệu/model/source và finite
   call/job/GPU-time/deadline/stop rules. `evidence_refs` thiếu giữ `null`;
   string/receipt không xác thực tác giả và không mở fence. Final source phải
   được phát hành qua cơ chế authority đã review; không sửa code trong notebook.
   `CANDIDATE_RELEASE_BLOCKED` không phải READY. Không publish notebook bằng lệnh
   sẽ tự GPU-submit. Owner nhận file import và ba bước trên sau đúng release.
3. **Theo dõi/thu.** Owner chạy một version1 trên slug riêng mỗi lượt; không API
   submit, không version2 thay thế, không chạy VM song song. Theo dõi tối đa15
   phút, lưu RUNNING_UNVERIFIED/conversation/job/version rồi kết thúc lượt AI.
   Khi Owner báo xong, resume đúng session; chỉ thu khi provider COMPLETE. Giữ
   cả ERROR/partial và đối soát riêng; không giả COMPLETE để thu lỗi.
4. **Kiểm kết quả.** Tải giữ nguyên hai cặp attempt ZIP/sidecar và supervisor
   ZIP/sidecar (đúng đường dẫn Output). Sau quyền riêng, `collect` kiểm bằng SDK
   hiện có: Private/job/latest1/code/Inputs, hết mọi trang Output, chỉ bốn GET
   ẩn danh tới đúng cặp. SHA bytes provider phải khớp bản local; thêm ZIP, URL
   sai, partial, source/history/raw/native/process/accounting sai đều STOP.
   ZIP/CRC/member SHA, request/plan/campaign, raw-before-parse, từng trạng thái
   và mẫu số3.763 dùng verifier hiện hữu. Không claim cơ chế chữ ký mật mã hoặc
   global exactly-once. SDK GetKernel chỉ trả ref Input không có version: cần
   chứng cứ provider version riêng + byte admission; không suy version từ mount.
5. **Lượt kế.** `next` tạo resume candidate từ verified history, caps/time mới
   được duyệt và slug/capsule riêng. `prepare --ancestor ...` luôn kiểm lại mọi
   archive, oldest first. SUCCESS/INVALID/lỗi consumed không chạy lại. OOM,
   timeout, unknown markers, history thiếu hoặc output không xác minh → giữ lỗi
   và STOP để chẩn đoán; không tự chuyển sang repair. Không chọn kết quả thuận
   lợi, ghép series hoặc dùng GT. Không có default160/200 calls hay hứa fit RAM.

Các lệnh cho Operator từ repository root (chỉ `plan/prepare/next` là CPU metadata;
`collect` hiện **luôn bị fence chặn trước path/provider/raw I/O**):

```powershell
python -B -m scripts.minicpm_fulltrain_ui plan --cohort <sealed-cohort.json> --projection-sha256 <custodian-sha> --resource-policy <approved-policy.json> --checkpoint-marker-sha256 6ff382a6d1951d8224221c7ab1b4cb77830efb7abd5c1a72166482ed3a133040 --run-id <run> --attempt-id <attempt> --job nguynanhtn/<new-job> --capsule-ref nguynanhtn/safeshift-minicpm-capsule-<new-run>/1 --max-calls <approved-calls> --max-seconds <approved-seconds> --mount-layout <direct-or-nested> --output data/processed/<new-spec.json>
python -B -m scripts.minicpm_fulltrain_ui prepare --spec data/processed/<spec.json> --runtime-ref <exact-committed-runtime-sha> --output data/processed/<new-package>
python -B -m scripts.minicpm_fulltrain_ui collect --package data/processed/<package> --attempt <downloaded-run.zip> --supervisor <downloaded-supervisor.zip> --output data/processed/<new-collection>
python -B -m scripts.minicpm_fulltrain_ui next --spec <prior-spec.json> --verification <collection/verification.json> --run-id <new-run> --attempt-id <new-attempt> --job nguynanhtn/<new-job> --capsule-ref nguynanhtn/safeshift-minicpm-capsule-<new-run>/1 --max-calls <approved-calls> --max-seconds <approved-seconds> --output data/processed/<new-spec.json>
python -B -m scripts.minicpm_fulltrain_ui prepare --spec <new-spec.json> --ancestor <oldest.zip> --ancestor <next.zip> --runtime-ref <same-released-runtime-sha> --output data/processed/<new-package>
```

Đường dẫn mới/create-only bắt buộc. Không chạy lệnh với placeholder. Caps, policy,
projection, scientific/source release không do script tự điền. Notebook đã đóng
gói nhận capsule tự động, Owner không nhập đường dẫn máy hoặc sửa cell.

## Kiểm môi trường và giới hạn hiện tại

Giữ MiniCPM revision `6f69a8235885be89608f3a71ffd40695b379e1e7`, FP16 weights,
eager/batch1/GPU0, greedy max64, đúng resampler FP32, strict C1, LABEL_ONLY/HNLO
N/A. Không sửa nhãn, prompt, token/resize/slices, split, parser hoặc scientific
selection. Không nhập dự đoán Candidate160/Issue173 vào series mới.

Thứ tự native đã có: source/Input/checkpoint/history admission → storage thật/
RAM+cgroup/reserves → Python3.11.9 từ Input và venv/pins cu124 → CPU processor/
ABI/JPEG → physical T4/driver/free VRAM → CUDA/FP16 trong child → load/native
raw-before-parse → C1 → ZIP/SHA. Hai GPU vật lý được kiểm riêng, MiniCPM chỉ thấy
GPU0; không cộng VRAM. Chung filesystem phải cộng cả scratch/output reserves.
Provision pinned packages cần Internet; không tải images/weights/Python mới.
Supervision giữ process-group deadline và bounded logs, không retry. Giữ scratch,
partial/raw/exception/markers; unknown không được coi như NOT_ATTEMPTED.

Final-source Kaggle ABI/VRAM/model-fit/load/inference/export **NOT_RUN**, không có
quyền smoke trong task này. Không đặt thêm vòng smoke/pilot riêng làm mặc định.
Sau khi được cấp đúng quyền, preflight ở ngay job thực thi, trước load/calls;
inference/export của chính job cung cấp bằng chứng, không hứa trước model-fit.
Lỗi/timeout vẫn giữ partial và STOP đối soát. Trước release chạy thật còn phải xác minh authority,
caps/rights/projection, provider/version/capsule, quota/history và live gates.
Đây là giới hạn được giữ nguyên; CPU PASS và Draft không hoàn tất DONE vận hành.
