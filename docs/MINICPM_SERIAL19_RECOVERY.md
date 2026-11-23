# MiniCPM-V-4 Serial 19 và chuyển nguồn cho Serial 20

## Bằng chứng và giới hạn

Operator báo Serial 19 `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-19`,
kernel `146811245`, dừng ở CPU với `HARD_DEADLINE`, `returncode=-9` sau
600,06 giây. Supervisor ZIP được báo là
`9c2665185ac443e5afbc3e49b3e0b2b4.zip`. Không tìm thấy
`inspect_run_19_full`, `minicpm-s19-provider-closure.json` hoặc journal
production trong workspace giao cho Codex. Việc chưa load, chưa gọi native,
chưa có kết quả dùng được và tình trạng ghi closure vẫn cần kiểm bằng bộ bằng
chứng thật. Các số dưới đây là báo cáo Operator.

| Serial | Thời gian CPU |
| --- | ---: |
| 16 | 538,97 giây |
| 17 | 587,33 giây |
| 18 | 554,96 giây |
| 19 | 600,06 giây, bị kill |

| Trạng thái TRAIN | Ảnh |
| --- | ---: |
| SUCCESS | 2.559 |
| INVALID | 118 |
| NOT_ATTEMPTED | 1.086 |
| Tổng | 3.763 |

Mã đã merge áp dụng `diagnostic_seconds` cho CPU. Release V5 xác nhận 600
giây cho diagnostic, 1.800 giây cho setup, 600 giây dự trữ xuất evidence,
trần 14.400 giây/job và hai GPU vật lý tính vào reservation. CPU trước đó đã
dùng 89,8–97,9% trần. Mã xác nhận đường thực thi dẫn tới hạn trên, còn log
được giao chưa đủ để định lượng SHA ảnh, checkpoint, lịch sử hay PIL cho lượt
bị kill. [Release runtime V5](https://github.com/tantdna2/SafeShift/pull/209#issuecomment-7033394502).

## Công việc trong mỗi stage

| Stage | Trước | Runtime đề xuất |
| --- | --- | --- |
| Launch | Replay capsule vào workspace tạm rồi replay lại để dựng workspace chạy | Dựng cây lịch sử một lần từ capsule read-only. Giữ pin outer SHA, ZIP, lịch sử, raw và thứ tự. Cài cây đã xác minh bằng rename sau claim |
| Admit | Kiểm source, plan, replay mọi ancestor, kiểm đủ SHA ảnh và checkpoint | Giữ các kiểm tra để chặn trước setup |
| Setup | Lặp admission đầy đủ trước cấp phát và cài môi trường | Kiểm source, cấu trúc reservation, sau đó cấp phát và kiểm riêng Python/wheel đã khóa |
| CPU | Lặp admission và đọc lại byte ảnh cho PIL, rồi kiểm processor và reclaim | Kiểm source, projection, plan, cấu trúc lịch sử, SHA ảnh/file checkpoint, PIL, processor và reclaim. Ảnh nén tối đa 8 MiB được giải mã từ cùng bộ đệm đã băm. Ảnh lớn được mở lại với kiểm danh tính file |
| GPU | Lặp admission đầy đủ trước kiểm môi trường GPU | Kiểm source, cấu trúc reservation, pin môi trường, driver, CUDA và tài nguyên |
| Native | Admission đầy đủ, rồi replay lịch sử lần nữa trong controller trước attempt | Đọc lại byte ảnh/checkpoint. Replay raw/custody một lần dưới khóa trong controller, trước attempt. Giữ SHA ảnh trước từng call và kiểm weights khi load |

Khi số Serial và bản ghi tăng, mỗi lần replay đi qua các ancestor đã phục hồi,
đối chiếu raw, tái tính plan và lịch sử tích lũy của từng ancestor. Chi phí đó
lặp giữa các stage và theo số ancestor, ngoài chi phí cố định của 3.763 ảnh
và checkpoint. CPU vẫn kiểm lại byte dù admit đã PASS, để bắt cả thay đổi
ảnh/checkpoint giữa hai tiến trình. Stage dùng package/runtime có kiểm tra
nguồn riêng. Không dùng biên nhận PASS của stage trước để cấp quyền đọc byte
khác. Luồng native vẫn kiểm đầy đủ raw, kế hoạch và SHA tại điểm sử dụng.

Chọn 1.200 giây cho CPU riêng trên release mới, gấp đôi mức 600 giây vì ba
lượt hoàn tất sát trần và lượt sau bị kill. Dữ liệu hiện có chưa đủ căn cứ
để cấp 1.800 giây hay dự đoán thời gian Kaggle. Setup, GPU và reclaim theo
policy cũ. Deadline child luôn là mốc nhỏ hơn giữa ngân sách stage và thời
gian job còn lại sau khi trừ export reserve. Khi hết khoảng chạy, supervisor
giữ evidence BLOCKED và không mở child. Phần retention/export do supervisor
xử lý trong khoảng dự trữ của job. Mốc hết hạn vé áp dụng lúc launch và grant
phải còn hiệu lực suốt ngân sách đã cấp. Ticket vẫn kiểm quota hai GPU, trần
job và giới hạn chiến dịch trước khi reserve. Nguồn mới yêu cầu quota và thời
hạn đủ cho trần năm stage pre-native, export và khoảng khởi động call theo
sizing đã ký. Gate thiếu thời gian bị từ chối trước khi ghi reservation.

Trong supervisor, xem `history-restore-timing.json` cùng
`<stage>-process.json` và `<stage>-budget.json`.
Dưới `<stage>/timing/` có thời gian kiểm authority, cấu trúc lịch sử,
projection, plan, replay raw, checkpoint, môi trường, processor và cache
advice. CPU ghi các mốc cộng dồn SHA và decode sau mỗi 256 ảnh và khi xong,
kèm số byte băm. Mốc bắt đầu thiếu mốc kết thúc cho biết pha đang chạy lúc
bị kill. Một lượt thật từ nguồn mới mới cung cấp số đo từng phần trên Kaggle.

## Chứng cứ đóng lượt và restart

Companion dùng nguyên `verify_download`, `verify_provider` và event
`FAILED_PRE_NATIVE_NO_USABLE_RESULTS`. V5 gốc đọc event này ngay trên
registration hiện tại. Bằng chứng phải có supervisor-only, prefix stage đúng
và các process đã reap, ticket/context, capsule bytes, provider kernel ID,
output inventory và cặp ZIP/SHA. Mọi dấu load, native call, attempt hay
kết quả sử dụng được đều chặn đóng pre-native.

Companion xác minh mỗi byte trong hai bản custody/capsule của các lượt có kết
quả. Các lượt đóng đã audit dùng hash snapshot được Owner ghim vào release.
Lượt đóng mới dùng chữ ký Operator trên event digest và hash inventory của
download đã kiểm chuyên sâu. Các lệnh sau xác minh chữ ký, mirror, prefix và
SHA256 từ byte hiện thời, không cần mở ZIP lịch sử. Trình đối soát đầy đủ vẫn
replay mọi ZIP và xác thực lại provider. Closure cũ ngoài companion thiếu
chữ ký đính kèm sẽ dùng trình xác minh đầy đủ cho tới khi được audit vào prefix.

Nếu cả hai event đã có, dùng `status` để xác định active Serial và kiểm
closure chính xác. Lặp lệnh với cùng chứng cứ trả `ALREADY_CLOSED`; lệnh
cũng chỉ ra nếu Serial kế tiếp đã reserve. Nếu restart trước event, chạy lại
với đúng download, provider closure và khóa Operator hiện có để hoàn tất ghi
create-only. Nếu event chỉ có một bên, hai bên lệch hoặc seal dở/hỏng, dừng tại
đối soát chỉ đọc, giữ mọi file để Owner kiểm tra. Nếu Serial 20 đã reserve,
giữ đúng ticket và `export-active` sau khi xác nhận trạng thái Owner UI và
cửa sổ chạy. Ticket hết hạn hoặc có custody đang thu cần đối soát hiện trạng.

## Hồ sơ phê duyệt nguồn

| Thành phần | Đã phát hành | Ứng viên trong Draft PR |
| --- | --- | --- |
| Runtime source manifest SHA256 | `81ddb4df4a13e08f98e8944b3a7070b90d8b484d4a0f3605667829ca1a4f9b41` | `4c3698d804c92ac81ec11c0dbcf783ae646c8e5fdaa8f8ac73f37ee183b990b1` |
| V5 tool manifest SHA256 | `52c900bd4b1adac38f11119b7787fcdb0fd004b8f81dcdacbfab8aad86014975` | `5a4c12c32872e2c3c99e043d3e974fb10ed5dccfc3ea9a0c53d99bae8f06b6d8` |
| Fast companion file SHA256 | `4fdf4fe10bb69f40dd8e1a6e3fb9e130ffda588839855d41438363196a5aee77` | `5a4acf9fc690c8dbd8eee81e47c6d1531519d432b4057b91e39816c30195e3be` |

Nguồn runtime đổi ở `admission.py`, `contract.py`, `minicpm_execution.py`,
`minicpm_offline.py`, `minicpm_release.py`, `minicpm_ui.py`,
`original_inputs.py` và `runtime.py`. Tool manifest đổi qua
`scripts/minicpm_offline_continuation.py` và
`scripts/owner_verify_minicpm_offline.py`. Notebook builder sẽ tạo notebook
mới ghim commit runtime đã duyệt và digest capsule của ticket kế tiếp.
Các notebook đã phát hành giữ đúng mã theo commit cũ.

```console
python -B -c "from safeshift.fulltrain import contract; from safeshift.pilot.contract import digest; from scripts import minicpm_offline_continuation as v5, minicpm_offline_fast as fast; print(digest(contract.source_manifest())); print(digest(v5.tools_manifest())); print(fast.sha(fast.__file__)); print(v5.tool_blobs())"
```

Runtime V5 cũ tiếp tục xác minh registration, vé và kết quả từ nguồn cũ với
checkout nguồn đã phát hành, chẳng hạn `57fb693648a03469eb25778e7a63f5be4ac0f501`
cho các file runtime và V5 tools đã ghim. Release Fast của PR #210 chỉ
xác thực đúng byte script cũ. Chuyển sang runtime mới giữ cùng event schema,
registration, khóa, caps, sizing, journal và hold. Grant mới ghim SHA của
grant cũ, registration, số/hash của event cuối đã đối soát và Serial đầu
tiên dùng nguồn mới. Ticket mới ký SHA grant mới và hash của event liền trước.
Trình V5 cập nhật xác minh mọi reservation dưới grant tương ứng. V5 gốc xác
minh closure và prefix cũ; ticket sau chuyển nguồn cần trình cập nhật.

Nguồn mới đổi đúng dấu vết `implementation_sha256` trong identity. Planner
kiểm chain gốc và dùng một phép chiếu identity trong bộ nhớ để gọi planner
chung. Trên đĩa, plan mới giữ hash của lịch sử gốc, và archive/history cũ giữ
identity nguyên thủy. Chỉ cho phép chiều V5 → nguồn mới với các trường khoa
học giống nhau và resume NOT_ATTEMPTED theo thứ tự. Sizing của Serial đầu từ
nguồn mới dùng trần bảo thủ chưa đo cùng nguồn. Telemetry nguồn cũ không được
dùng để tính tốc độ của nguồn mới.

## Bàn giao sau khi có quyền

1. Sau review, audit, merge được cấp riêng và hậu kiểm, Operator kiểm hai
   mirror và xác minh prefix bằng V5 đầy đủ trên checkout nguồn cũ. Giữ một
   checkout chỉ chứa source V5 đã khóa cho `--historical-repo`. Cập nhật mã
   đã merge trong chính checkout Operator đang giữ `data/processed` để
   primary, mirror, registration và khóa vẫn ở đúng đường dẫn hiện hành.
   Owner phát hành lại record `SAFESHIFT_MINICPM_OFFLINE_OPERATOR_FAST_V1`
   theo [hợp đồng release Fast](MINICPM_OFFLINE_CONTINUATION.md#chuyển-tiếp-trên-cùng-chiến-dịch),
   cộng `companion_dependencies` với `source_sha256`, `tools_sha256` và
   `closure_snapshots` là mapping Serial đã đóng trong prefix tới digest
   `closure_snapshot(download)` trên đúng bằng chứng đã audit. Nếu prefix
   chưa có closure thì mapping rỗng. Git tree reviewed/merged phải chứa file
   companion, runtime manifest và V5 tool blobs tương ứng.
2. Khi Serial 19 còn active, Owner lấy hồ sơ provider thật bằng verifier
   online read-only với tham số kernel ID. Operator kiểm và đóng đúng
   reservation. Nếu đã có closure, dùng event hiện có và giữ nguyên active
   Serial khác. Sau đó xác minh prefix đã settled và tạo mẫu release runtime
   chưa ký. Owner điền commit, thời điểm 30 ngày và bốn approval thật,
   tính supporting proof theo luồng V5 và phát hành
   `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V5` trên PR đã merge. Khi tính digest
   supporting proof bằng `--serial9-proof-proposal`, dùng hash 64 chữ số 0
   làm giá trị giữ chỗ trong bản proposal cục bộ rồi thay bằng digest thật
   trước khi phát hành. Owner giao locator và export GitHub chính gốc.
3. Operator tải lại trạng thái với hai release và checkout cũ. Dùng duy
   nhất companion làm writer sau cutover. Owner xác nhận quota tuần, năm
   Input, job/capsule mới và không có lượt active. Operator dùng khóa cũ cấp
   đúng một ticket và xuất notebook/capsule. Owner chạy một lần khi còn hạn.

```console
# Owner-only. Nếu cần lấy closure và Serial 19 còn active.
python -B -m scripts.owner_verify_minicpm_offline --owner-performs-network --historical-repo <frozen-v5> --pre-native-closure <primary> --download <inspect_run_19_full> --kernel-id 146811245 --output <new-private-evidence-dir>

# Operator. Kiểm status với cùng tiền tố trước lệnh closure.
python -B -m scripts.minicpm_offline_fast --directory <primary> --historical-repo <frozen-v5> --operator-release <new-fast-locator> --owner-exports <fast-exports> close-pre-native --download <inspect_run_19_full> --provider-closure <minicpm-s19-provider-closure.json> --kernel-id 146811245 --private-key <original-key>

# Operator. Xuất proposal để Owner review sau khi prefix settled.
python -B -m scripts.minicpm_offline_continuation --directory <primary> --historical-repo <frozen-v5> runtime-release-template --output <unsigned-runtime-proposal>

# Operator. Sau khi có runtime release, dùng cùng tiền tố cho forecast, stage và export-active.
python -B -m scripts.minicpm_offline_fast --directory <primary> --historical-repo <frozen-v5> --operator-release <new-fast-locator> --owner-exports <fast-exports> --runtime-release <runtime-locator> --runtime-exports <runtime-exports> forecast
```

Khi đối soát cuối, truyền `--historical-repo`, `--runtime-release` và
`--runtime-exports` cho V5 và Owner verifier cập nhật. Chuỗi phải phủ đúng
3.763 ID, đủ custody từng lượt và có phê duyệt cuối thật. CPU mô phỏng chỉ xác
minh phần mềm và sổ journal. Khả năng chạy Kaggle, GPU và inference thuộc lần
xác minh thật do Owner chỉ định.

## Benchmark CPU

```console
python -B -m scripts.benchmark_minicpm_offline --close-serial19
```

Fixture tổng hợp 3.763 ID, Serial 9–18 gồm hai lần có kết quả và tám closure
đã xác minh. Serial 19 có 2.559 SUCCESS, 118 INVALID và 1.086 NOT_ATTEMPTED.
Đây là cùng kích cỡ cohort, số Serial và số kết quả báo cáo, với phân bổ
theo Serial tổng hợp. Cả hai lệnh nhận cùng bản sao journal và bằng chứng
CPU supervisor-only. Tạo fixture, sao chép snapshot và kiểm đường tiếp nối
nằm ngoài đồng hồ đo. `file_bytes_read` là byte Python đọc từ file nhị phân,
bao gồm đọc để băm, còn số byte giải nén được ghi riêng. Chạy trên WSL2
tmpfs, Python 3.14.4. Không suy các số này thành thời gian production.

| Đường đóng lượt | Giây | Mở ZIP | Replay lịch sử | Byte đọc từ file | Byte ZIP nén đọc | Byte giải nén | SHA256 | Lần gọi SHA file |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V5 đầy đủ | 232,9506 | 56 | 6 | 968.744.502 | 434.580.278 | 268.365.301 | 377.210 | 66.494 |
| Companion | 6,0243 | 2 | 0 | 487.970.223 | 219.567.644 | 7.927.335 | 29.546 | 4.598 |

Sau phần đo thời gian, fixture đã đi qua forecast, release chuyển nguồn tổng
hợp, gate, một lần reserve Serial 20 và export lại capsule. Kiểm lại đúng
2.677 bản ghi, cùng toàn bộ 1.086 ordinal còn lại theo thứ tự. Luồng fast
sau chuyển nguồn hoàn thành các bước này với thao tác mở ZIP bị chặn.
