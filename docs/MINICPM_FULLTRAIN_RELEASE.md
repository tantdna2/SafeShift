# MiniCPM Full-TRAIN — phát hành và thực thi V2

Tiếp tục **cùng branch/session/Draft PR198** theo
[directive6907347740](https://github.com/tantdna2/SafeShift/pull/198#issuecomment-6907347740)
và [đính chính không có cap200](https://github.com/tantdna2/SafeShift/pull/198#issuecomment-6907239054).
BASE PR195: `6744c319152743f399c79f6c8b16acb527d5acb4`. Dossier commit0d9f7ee
và receipt ban đầu là lịch sử, không phải nghiệm thu phạm vi mở rộng này.

V2 có nhánh thực thi có điều kiện: live release GitHub + signed ticket + serial
reservation hợp lệ → pipeline PR195. Thiếu chứng từ thì BLOCKED; không có flag,
`approved=true` hoặc offline export mở GPU. **Phiên Codex này không chạy Kaggle/
API provider/GPU/inference/TEST, upload Input hoặc ghi production journal.**

## Quyền và source

`minicpm_release.load` chỉ đọc HTTPS API chính thức, không redirect/retry. Kiểm
Owner `tantdna2`/ID246929698, comment đúng PR198/body SHA, PR merged/main/reviewed
HEAD/merge và mọi runtime byte tại runtime/reviewed/merged Git trees. Chín
attestations riêng khóa source review, audit độc lập phạm vi mở rộng, quyền merge,
hậu merge và O2–O6. Không tái dùng review CPU6907210268 làm duyệt expanded diff.

Grant marker `SAFESHIFT_MINICPM_FULLTRAIN_RELEASE_V2`, schema
`safeshift-minicpm-fulltrain-release-v2`; `release-template` xuất chính xác fields.
`authorization=OWNER_MINICPM_TRAIN3763_SERIAL_UI_ONLY`. Scope khóa original
projection/master, MiniCPM source/revision/config, policy/driver/reserves,
checkpoint marker/Python Input. `subject_sha256` là digest toàn grant trừ
approval locators; thay caps/key/source/window làm approvals cũ không khớp.
Attestation marker `SAFESHIFT_MINICPM_FULLTRAIN_APPROVAL_V2` chứa chính xác
`{kind,status:"APPROVED",reviewed_head,subject_sha256}`. Owner dẫn chứng các quyết
định có thật; không tạo chữ ký ChatGPT/Antigravity hoặc quyền bên thứ ba.

Một campaign grant bao trùm các resume serial, không cần approval khoa học từng
shard. Owner duyệt RSA3072/e65537 public key và host hash của máy vận hành. Private
key chỉ ở máy đó, **không vào notebook/capsule/Input/Git/chat**. OpenSSL ký local;
worker dùng stdlib xác minh full PKCS1-v1_5 SHA256 encoding theo
[RFC8017 §8.2.2/9.2](https://www.rfc-editor.org/rfc/rfc8017#section-8.2.2).
Chữ ký xác thực delegation/reservation, không chứng nhận chất lượng model.

`contract.authorize` mặc định đóng. Context sau authentic release + signed ticket
mới mở đúng request MiniCPM. Parent và mỗi child kiểm authority/source; children
dùng signed delegation cho decisions đã kiểm, vẫn GET Owner record + merged PR
thật. Claims launch/admit/setup/cpu/gpu/native/load/call dùng fixed VM path,
create-only/fsync/OS lock. Sai request/model/ordinal, replay stage/load/call,
expired/cap/source đều chặn. Load một lần, raw trước parse, strict C1/HNLO N/A.

Local có thể tái dùng login `gh` hoặc token môi trường, chỉ giữ trong memory.
Clean worker không nhận token từ kernel; Kaggle public-repo reads có thể anonymous.
Rate-limit/disconnect là BLOCKED/partial, không bỏ check hoặc dùng exports thay API.
Không log credentials/bearer URL. Không cần remote server hoặc giữ AI nền.

## Chuẩn bị, giữ chỗ, Owner Run và thu

`scripts.minicpm_fulltrain_operator` dùng một máy và hai directories create-only
dưới `data/processed/`: REGISTERED → RESERVED → PUBLISH_INTENT → PUBLISHED →
COLLECTED. Ghi cả hai reservation trước publish/handoff. Gap/torn/divergence/open
reservation STOP, không refund/takeover/tự tạo job thay thế. Hai bản cùng ổ không
phải backup phần cứng. Không claim global exactly-once giữa các VM độc lập; Owner
phải giữ originals/backup và không chạy song song hoặc bấm lại cùng ticket.

`stage` kiểm đầy đủ account inventory, slug mới absent, mọi campaign predecessor
COMPLETE đúng Private/version/code/Inputs, Dataset Private owner và ListFiles ở
version cụ thể, checkpoint Output v1 COMPLETE, quota reserved=0. GetKernel chỉ
chứng minh refs không version; filesystem mount không là chứng cứ provider version.
Master/3763 JPG/checkpoint/Python/ancestor/capsule bytes được worker lặp admission
trên read-only mounts trước model. Không copy/reupload TRAIN hoặc checkpoint.

Writer PR195 giữ marker/request/cohort, ancestor `.bin`+sidecar nguyên byte; V2
thêm signed ticket. Notebook builder pin đúng runtime commit/capsule SHA/live
locator. `publish` chỉ tạo **Private metadata Dataset mới**, không push notebook
hoặc submit kernel. Kiểm exact inventory/size/version, tải kiểm ticket bytes rồi
kiểm lại Inputs/quota/no-active-VM trước `owner-handoff.json=RELEASED_FOR_OWNER_UI`.

Timeout upload giữ PUBLISH_INTENT; chỉ `publish --verify-only` đối soát existing
v1, không retry create. Gián đoạn package offline: `recover-package --output
<new-path>` tái dựng cùng ticket/reservation, giữ mọi partial cũ. Quá hạn hoặc
không xác minh được provider/history thì STOP, không tự gia hạn hay refund.
Không giao Owner Run từ handoff candidate cũ; chỉ dùng owner-handoff mới trong
start-before window. Owner làm [ba bước](MINICPM_FULLTRAIN_OWNER_UI.md).

Antigravity thu khi Owner báo terminal trong đúng conversation. `collect` kiểm
status bounded một lần; RUNNING/QUEUED trả RUNNING_UNVERIFIED và kết thúc lượt AI.
Terminal kiểm Private/latest1/code/Inputs rồi tải đúng **hai ZIP + hai sidecars**
qua SDK/URL/stream guards hiện hữu. Hết mọi trang trước GET; extra/missing ZIP,
URL lạ, redirect, byte/time/space vượt cap đều STOP. Giữ log/partial/error.

COLLECTED chỉ sau CRC/member SHA/raw/C1/native/process/accounting/ticket/claims
PASS. Native marker phải khớp signed-ticket claim; có claim mà thiếu marker là
unknown STOP. Lỗi/timeout/nonfinite không biến thành pending hoặc COMPLETE.
`stage` kế tiếp đối chiếu provider ZIP lại, tái tính history và telemetry từ
originals; sửa receipt/telemetry local không vượt gate. SUCCESS/INVALID/consumed
error không chạy lại; repair khoa học không thuộc route V2.

## Tự tính lượt, không mặc định200

Calls ceiling = min(pending, authorized job_calls, remaining total_calls).
Seconds = min(job_seconds, campaign GPU-time còn /2, available quota /2,
grant deadline trừ start window). Tính **hai GPU vật lý**, MiniCPM chỉ dùng GPU0;
không cộng VRAM. Cộng maxima calls/jobs/GPU-seconds, không refund sau early stop,
load error hoặc INVALID. Kiểm khả năng pending theo calls/jobs còn lại. Bound512
jobs khớp ancestry bound hiện hữu, không là số job dự báo/mặc định.

Chưa có telemetry MiniCPM cùng source: `UNKNOWN_ADAPTIVE_WITHIN_APPROVED_CAPS`,
không mượn throughput InternVL. Trong cùng job đã cấp quyền: admission → storage/
RAM/allocation → pinned Python/pins/CPU ABI/processor → T4/driver/child CUDA FP16
→ load một lần → native/raw/C1/ZIP. Sau load và trước sample-start tiếp, kiểm
thời gian dành cho call/export. Guard dùng approved first_call_seconds và safety
factor; chưa đo thì không bảo đảm worst-case latency/model-fit. Process-group
hard deadline giữ partial khi native treo. ADAPTIVE_TIME_STOP trước sample mới
giữ NOT_ATTEMPTED thật và seal/export để resume.

Lượt sau dùng timing **MiniCPM cùng source, ZIP/provider/claims verified**:
overhead × safety, max observed call × safety, approved first-call guard, export
reserve và caps. Chỉ đo overhead chưa call thì throughput vẫn UNKNOWN. RAM/VRAM/
disk vẫn phải qua live gates. Không thêm vòng smoke riêng hoặc hứa một job3763.

## Lệnh sau release thật

Không chạy placeholder. Từ checkout merged/clean, dùng SDK venv hiện có
kaggle2.2.5/kagglesdk0.1.38/requests2.34.2 và OpenSSL local. `plan` PR195 dựng
spec từ projection seal/policy thật; không import predictions cũ. Runtime ref phải
chứa đúng mọi runtime bytes. Notebook/ticket tạo sau release, không hash cycle.

```powershell
python -B -m scripts.minicpm_fulltrain_operator release-template --spec data/processed/<spec.json> --runtime-ref <runtime40> --output data/processed/<unsigned-release.json>
python -B -m scripts.minicpm_fulltrain_operator --directory data/processed/<journal> --mirror data/processed/<mirror> init --locator data/processed/<authentic-locator.json> --spec data/processed/<spec.json>
python -B -m scripts.minicpm_fulltrain_operator --directory data/processed/<journal> --mirror data/processed/<mirror> stage --private-key <local-key-path> --output data/processed/<new-package>
python -B -m scripts.minicpm_fulltrain_operator --directory data/processed/<journal> --mirror data/processed/<mirror> publish
python -B -m scripts.minicpm_fulltrain_operator --directory data/processed/<journal> --mirror data/processed/<mirror> collect --output data/processed/<new-collection>
```

Chỉ stage tiếp sau verified COLLECTED và còn pending. `status` không đo billing.
Key riêng có thể tạo offline trên máy Owner bằng OpenSSL; public modulus/e và
host hash phải được Owner/reviewer xác minh trước grant. Không dùng key test.
Không gọi helper nội bộ hoặc sửa source/journal để vượt BLOCKED.

## Chứng từ ngoại sinh còn thiếu / nghiệm thu

**Hành động duy nhất sau review/audit/merge:** cung cấp record release V2 thật
trên PR198 ràng buộc merged/runtime source, projection seal và quyền O2–O6,
finite total/job calls/jobs/GPU-seconds/deadline/policy/reserves, public key/host,
cùng locators review/audit/merge/postmerge. Directive giao lập trình không thay
record này. Antigravity tự thu current provider facts bằng read-only SDK sau
quyền đó; không bắt Owner nhập throughput hoặc đoán200.

Hiện chưa có record; **BLOCKED cho activation và Owner Run**. Không tự đặt số
cap/time/rights trong task. Checkpoint/Input lịch sử PR195 không là quan sát mới.
Final-source live ABI/VRAM/load/inference/export **NOT_RUN** theo lệnh cấm chạy thực.
Nghiệm thu code gồm signed authorized synthetic end-to-end, adversarial gates,
full3763 controller/failure/resume, exact-ref notebook và focused regressions.
Review/audit dossier cũ không áp dụng expanded diff. Không tuyên bố DONE/runnable
release cho Owner trước authority và concrete published capsule hợp lệ.
