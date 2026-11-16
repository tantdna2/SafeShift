# MiniCPM Full-TRAIN — Owner UI

**Hiện BLOCKED cho Owner Run:** PR198 mở rộng chờ review/audit/merge và release
V2 đúng source/quyền/caps. PR195 đã merge tại
`6744c319152743f399c79f6c8b16acb527d5acb4`; merge đó không cấp quyền thực thi.
[Cổng release và lệnh Antigravity](MINICPM_FULLTRAIN_RELEASE.md) ghi đầy đủ.

## Owner chỉ làm ba bước khi nhận handoff đã phát hành

1. Import `notebook.ipynb` Antigravity bàn giao; gắn đúng **năm Input/version**
   trong `owner-handoff.json` có trạng thái `RELEASED_FOR_OWNER_UI`.
2. Kiểm **Private, Python, Internet On, T4 x2**, calls/time và `start_before_unix`
   trong handoff. Không chạy bản quá hạn hoặc khi VM cũ chưa terminal.
3. **Save Version → Save & Run All một lần** trên slug/version1 đã giao. Gửi
   URL/version cho Antigravity khi terminal; giữ Output/log/ZIP kể cả lỗi.

Không sửa cell/request/parser, bấm lại hoặc tạo version2. Preflight nằm trong
cùng job trước load/calls, không cần vòng smoke riêng. Antigravity thu hai cặp
ZIP/sidecar, kiểm provider/raw/history/caps rồi chỉ chuẩn bị NOT_ATTEMPTED tiếp.
RUNNING thì lưu conversation và kết thúc lượt AI; không AI nền hoặc submit thêm.
Unknown/partial/error phải đối soát; không refund hoặc chạy lại consumed.
Raw đã seal được giữ nguyên trong ZIP và scratch; Output giữ hai cặp ZIP cùng
control files nhỏ để Antigravity thu được cả chiến dịch, không tràn inventory.

## Năm Input dùng lại

| Loại | Ref/version | Byte admission |
| --- | --- | --- |
| TRAIN | `nguynanhtn/inspecsafe-v1-kaggle/1` | Original3763 IDs/order/JPG SHA; TEST đóng |
| Master | `nguynanhtn/safeshift-pilot-input/1` | `master_manifest.json`, SHA `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008` |
| Checkpoint Output | `nguynanhtn/safeshift-prepare-minicpm4/1` | Marker SHA `6ff382a6d1951d8224221c7ab1b4cb77830efb7abd5c1a72166482ed3a133040`, source/two shards theo lock |
| CPython | `nguynanhtn/safeshift-cpython3119-20240726/1` | Shared exact manifest/transport/archive SHA như InternVL; không tải Python mới |
| Capsule Private mới | `nguynanhtn/safeshift-minicpm-capsule-<campaign>-<number>/1` | Request/cohort/ancestor bytes + signed reservation; SHA khóa trong notebook |

Version1 TRAIN/master và checkpoint Private/v1 có metadata lịch sử PR195;
không là quyền/provider observation mới. Antigravity kiểm live version/Private/
quota và signed capsule trước handoff; worker kiểm bytes trên read-only mounts.
Không reupload TRAIN/checkpoint hoặc chuyển grant InternVL/Candidate160.

Không mặc định160/200 ảnh/lượt, không hứa19 lượt hoặc3763 ảnh vừa một job.
Antigravity dùng approved caps/quota/time và MiniCPM telemetry cùng source;
chưa đo thì UNKNOWN và giới hạn thích ứng. Reservation tính cả hai GPU vật lý,
MiniCPM chỉ GPU0, không cộng VRAM. Giữ mọi lỗi/raw/history, INVALID đã consumed.

MiniCPM revision `6f69a8235885be89608f3a71ffd40695b379e1e7`, strict C1,
FP16 weights/eager/batch1/greedy max64, resampler FP32 và HNLO N/A không đổi.
Không nhập pilot predictions, đổi GT/labels/prompt/parser/precision hoặc mở TEST.
Final-source live model-fit/inference/export NOT_RUN trong task Codex này.
