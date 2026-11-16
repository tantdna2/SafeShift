# MiniCPM Full-TRAIN — gói phát hành có ràng buộc source

Ngày16/11/2026, BASE `6744c319152743f399c79f6c8b16acb527d5acb4`, sau
[PR195 MERGED](https://github.com/tantdna2/SafeShift/pull/195). Owner cung cấp
trạng thái ChatGPT hậu merge PASS; phiên này kiểm GitHub xác nhận merge,
không tự nhận là ChatGPT review/audit đó. Phạm vi: CPU code/tests/docs,
một Draft PR mới; không Kaggle/API provider/GPU/inference/TEST/production writes.

**BLOCKED cho thực thi.** Chưa có authentic campaign release MiniCPM, quyền dữ
liệu/model/caps, chứng cứ provider/version/quota hiện tại hoặc source activation.
Không có gói đã được phép chạy thật trong PR này. Phần mềm cung cấp đường
chuẩn bị/đối chiếu hồ sơ trong quyền CPU hiện có; `contract.authorize` giữ nguyên.
JSON candidate, receipt CPU và PR195 merge không thay các chứng từ còn thiếu.

## Gói dùng lại và phần bổ sung

Giữ nguyên byte mọi runtime, notebook lịch sử, checkpoint/locks và science của
PR195. Dùng lại `minicpm_fulltrain_ui plan/prepare/next`, capsule năm Input,
controller supervised, Python Input InternVL, strict C1, FP32 resampler/FP16
weights, HNLO N/A, raw-before-parse, complete ancestry và verifier hai cặp ZIP.
Không tạo Dataset ảnh/checkpoint mới, parser/loop mới, pilot hay series mới.

Companion CPU `scripts/minicpm_fulltrain_release.py` nằm ngoài runtime manifest:

- `inspect_package` kiểm capsule/ancestor bằng verifier hiện hữu; dựng lại toàn
  notebook từ Git commit chính xác và so cả bytes, không chỉ tin hash handoff.
  Kiểm Private/settings, đúng năm Input/version và metadata capsule. Binding ghi
  source/runtime, identity, policy, notebook/request/capsule/settings và tool SHA.
- `template` xuất đề xuất **unsigned**, để quyền, caps, ngày, PR và mọi approval
  là `null`. Không tự chọn số calls/giây hoặc ký quyền thay Owner.
- `check` phát lại mọi package theo thứ tự và hai cặp ZIP của từng lượt trước.
  Mọi source/identity/Input/policy phải khớp, job/capsule/run/attempt không lặp,
  history phải đúng kết quả verifier tái tính. Receipt JSON sửa thành PASS không
  vượt được lỗi trong ZIP. SUCCESS/INVALID/consumed error không trở thành pending.
- Tính cả proposed job: tổng `max_calls`, số jobs và **2 × max_seconds** cho từng
  job T4x2. GPU0 chạy MiniCPM, nhưng reservation tính cả hai GPU vật lý. Không
  refund maxima chưa dùng, không coi số SUCCESS là số calls hay billing đo được.
  Kiểm cap từng job/toàn chiến dịch, archive-size, deadline và khả năng bao phủ
  pending theo số calls/jobs. Đủ số calls không chứng minh đủ latency/VRAM/quota.
- Thiếu chứng từ trả receipt BLOCKED. Metadata hỏng, ZIP thiếu/tamper, source
  lệch, lỗi kỹ thuật hoặc cap/window sai bị từ chối trước khi xuất receipt mới.
  Mọi output create-only; partial/evidence cũ giữ nguyên để đối soát.

Ngân sách trên là phép kiểm kế hoạch CPU, **không phải durable reservation**.
Không dùng nó thay journal/claim đã được duyệt. Chưa có runtime nhận capability
MiniCPM mới; companion không mở gate bằng cờ, grant-file hoặc environment.
Nếu còn job/intention không có ZIP, không dùng receipt này để chạy job khác.

## Chứng từ cần bổ sung trước phát hành

| Gate | Bằng chứng cụ thể cần có | Tình trạng phiên này |
| --- | --- | --- |
| Source/review/audit/merge | PR mới, exact reviewed HEAD/merge, source/runtime/tool/notebook/capsule SHA; ChatGPT direct review, audit độc lập theo quyết định ChatGPT, quyền merge và hậu merge | PENDING; PR195 không là quyền chạy |
| O2 | Full original3763 TRAIN projection seal từ master SHA đã khóa, IDs/order/image SHA; TEST đóng | Chưa được cấp seal thật cho gói mới |
| O3/O4 | Quyền dữ liệu/ảnh/model/checkpoint và đúng MiniCPM Full-TRAIN/FP32/C1/HNLO N/A, không chuyển quyền Candidate160/InternVL | Thiếu chứng từ xác thực cho campaign này |
| O5 | Owner cung cấp total calls/jobs/physical GPU-seconds; cap calls/seconds mỗi job; 1 load/job; finite issued/expiry, archive bound, resource policy/driver/reserves | Không có số được cấp; không mặc định160/200 |
| O6 / provider | Private account/job version1, code notebook SHA; TRAIN/master/Python Dataset version1, checkpoint Output version1, capsule mới/version1; rights, current availability, quota, deadline và không VM khác | Chỉ có metadata lịch sử nêu trong Owner UI; không hỏi Kaggle trong phiên này |
| Kết quả/resume | Provider COMPLETE/version/code/Inputs; inventory đủ mọi trang, đúng hai ZIP và sidecar; SHA provider bằng local; complete ancestry và raw/markers/process accounting | Chưa có lượt MiniCPM Full-TRAIN mới |
| Activation | Thay đổi phát hành được review riêng để capability có authority/custody/caps được kiểm ở mọi entrypoint/child/load/call, durable serial reservation trước Owner Run, chống replay trong VM | Runtime PR195 vẫn hard-fenced; không được bỏ fence |
| Live kỹ thuật | Admission → storage/RAM/allocation → pinned Python/pins/ABI/processor → T4/driver/CUDA FP16 → weights/native → C1/raw → ZIP/SHA trong chính job được cấp quyền | NOT_RUN; không thêm mặc định vòng smoke độc lập |

Antigravity không được tự điền chứng từ Owner hoặc gọi helper nội bộ để vượt
gate. Khi ChatGPT quyết định audit/merge/release tiếp theo, cần đối chiếu các
bằng chứng này với bản gốc. Không có claim READY, global exactly-once hay
SCIENTIFIC_QUALIFIED từ một dossier hợp lệ về cấu trúc.

## Hợp đồng authority đề xuất để review

Schema `safeshift-minicpm-fulltrain-release-candidate-v1` chỉ dành cho đường này.
Một Owner campaign record có thể bao trùm các resume serial cùng scope/caps;
không thiết kế xin quyền khoa học lại cho từng shard. Schema chưa được runtime
tiêu thụ, chưa thay bất kỳ grant/decision lịch sử nào. `template` sinh đúng field
và source binding; các cột chưa có chứng từ luôn để null.

Nếu có bản gốc mới, `authenticate` đọc record marker
`SAFESHIFT_MINICPM_FULLTRAIN_CAMPAIGN_V1` trong đúng comment GitHub của
`tantdna2`, hash toàn body và đúng PR mới (>195). Nó kiểm PR merged/main,
reviewed HEAD/merge và chín attestations riêng (`source_review`,
`independent_audit`, `merge`, `postmerge`, `O2`–`O6`). Mỗi attestation mang marker
`SAFESHIFT_MINICPM_FULLTRAIN_APPROVAL_V1`, kind/status/head và `scope_sha256`.
API Contents phải cung cấp đúng bytes từng tool tại cả reviewed HEAD và merge
commit; chỉ metadata PR hoặc hash local không đủ. Hash scope bao gồm
source/Input/science, first package, caps và window; thay cap
hoặc tool/source làm attestation cũ không khớp. Đây là Owner dẫn chứng các quyết
định độc lập, không phải tool tự phát hành chữ ký ChatGPT/Antigravity/học vụ.

CLI **chỉ replay exports offline**, không tự lên GitHub hoặc Kaggle. Exports là
map từ `/pulls/<PR>`, `/issues/comments/<id>` và `/contents/<tool-path>?ref=<commit40>`
tới JSON nguyên bản (Contents gồm path/size/encoding/base64 content); locator là
`{comment_id, body_sha256}`. JSON local không chứng minh nguồn tải hay người thao
tác. Ngay cả replay PASS vẫn ghi `OFFLINE_REPLAY_ONLY_ORIGIN_NOT_AUTHENTICATED`
và BLOCKED. Cần đối chiếu bản gốc độc lập trước mọi activation thực sự. Không có
approval/record thật nào được tạo, gửi comment hoặc publish bởi công cụ này.

## Lệnh CPU cho Antigravity

Chạy từ checkout đúng source. Đầu vào phải là gói `prepare` thật có sealed
projection, caps/policy đã được cung cấp, không dùng synthetic fixture cho Owner.
Giữ artifacts tại `data/processed/`, không commit ảnh/weights/raw/archive/secrets.
Ví dụ dưới có placeholder, **không copy chạy trước khi thay đúng bằng chứng**.

```powershell
python -B -m scripts.minicpm_fulltrain_release template --package data/processed/<initial-package> --output data/processed/<unsigned-campaign.json>
python -B -m scripts.minicpm_fulltrain_release check --package data/processed/<initial-package> --output data/processed/<new-blocked-receipt.json>
python -B -m scripts.minicpm_fulltrain_release check --package data/processed/<initial-package> --package data/processed/<next-package> --attempt <original-first-run.zip> --supervisor <original-first-supervisor.zip> --locator data/processed/<owner-locator.json> --github-exports data/processed/<github-original-exports.json> --output data/processed/<new-replay-receipt.json>
```

Mỗi ancestor cần đúng một `--package`, `--attempt` và `--supervisor`, oldest
first; gói cuối proposed chưa có kết quả. ZIP sidecar phải ở cạnh file ZIP.
Không có `--approve`, `--activate`, `--submit` hoặc cờ tự authenticate export.
Vẫn dùng `plan/prepare/next` như [Owner UI](MINICPM_FULLTRAIN_OWNER_UI.md).

## Luồng khi đã được phát hành riêng

Antigravity chuẩn bị notebook/capsule/Input và hồ sơ đã đối chiếu → Owner kiểm
Private/T4x2/Input/caps rồi **Save Version → Save & Run All một lần** →
Antigravity theo dõi tối đa15 phút, lưu conversation/job/version và
RUNNING_UNVERIFIED rồi thoát lượt AI. Owner báo xong thì resume đúng conversation,
thu/kiểm provider và đủ ZIP/raw/log/sidecars; sau đó mới chuẩn bị pending kế tiếp.
Owner giữ hướng dẫn [ba bước ngắn](MINICPM_FULLTRAIN_OWNER_UI.md).

Không chia TRAIN thành các vòng thử vì thói quen. Initial có thể đề xuất đủ3763
nếu đúng caps; preflight an toàn nằm trong cùng controller trước load/call.
Một job có thể dừng ở cap/time hoặc lỗi, không bảo đảm xử lý hết. Chỉ sau verified
terminal/custody mới resume NOT_ATTEMPTED; lỗi consumed/unknown/partial STOP, giữ
toàn bộ raw/error/history. Không refund, repair ngầm, GT rescue hoặc mở TEST.

Kiểm thử mới: `python -B -m unittest discover -s tests -p test_minicpm_fulltrain_release.py -v`.
Acceptance và giới hạn nằm trong [hồ sơ CPU](research/MINICPM_FULLTRAIN_RELEASE_20261116.md).
