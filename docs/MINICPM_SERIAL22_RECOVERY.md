# MiniCPM Full-TRAIN sau Serial 22

## Trạng thái bàn giao

Base đã xác minh là `f520688adef4c73a142a69d1542a630a147854ac`. Operator báo
`nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-22`, kernel `147046083`, bị kill ở admit sau 600,06 giây
(`SUPERVISED_HARD_DEADLINE`, mã −9). Chỉ có claim launch và admit. Emit
`image-sha256-start.json` đã có, còn `image-sha256-end.json` chưa có.
Thời gian admit là 393,81 giây ở S18, 431,46 ở S19, 549,36 ở S20,
545,91 ở S21 và 600,06 ở S22.

| Pha S22 | Giây do Operator báo |
| --- | ---: |
| Launch phục hồi lịch sử | 1.285,45 |
| Admit authority | 1,64 |
| Admit workspace history | 0,42 |
| Admit input projection | 86,15 |
| Admit plan | 0,41 |
| Admit history replay | 158,19 |
| Admit trước SHA ảnh | 246,81 |

Operator đã đóng Serial 22 qua companion PR #211, tải đủ 196 file Output
và xác nhận chữ ký `closure-verifications/22.json`. Event #28 có disposition
`FAILED_PRE_NATIVE_NO_USABLE_RESULTS` và SHA256
`3f6a0424f22913a5e0bf27be43c4b5c147ad22e72a420a008286e53495220f79`.
Tiến độ báo cáo là 2.947 SUCCESS, 147 INVALID và 669 NOT_ATTEMPTED.
`next_ordinal=3094` và Serial 23 chưa reserve. Workspace Codex chưa có
`inspect_run_22_full`, `minicpm-s22-provider-closure.json`, supervisor ZIP
`3c9b2cbbf0e84a79985f08c9bf5683e4.zip` hoặc journal production để đối chiếu độc lập.
Timing chi tiết setup, reclaim, CPU, GPU, load và native của S20–S22 chưa được bàn giao.

## Ngân sách đã đối chiếu với release

| Stage | PR #211 (giây) | Nguồn đề xuất (giây) | Căn cứ |
| --- | ---: | ---: | --- |
| Bootstrap, authority, capsule và launch restore | Tính trong job, chưa có trần riêng | 2.400 tổng | Restore S22 báo 1.285,45. Phần còn lại dành cho bootstrap, I/O và tăng trưởng lịch sử |
| Admit | 600 | 1.800 | S20–S22 đã chạm hoặc gần trần. Hạn mới bao gồm projection, SHA ảnh và checkpoint |
| Setup | 1.800 | 1.800 | Giữ trần đã ký cho Python, wheel và storage probe |
| Reclaim | 600 | 600 | Giữ trần hiện tại cho cache advice độc lập |
| CPU | 1.200 | 1.200 | Giữ trần PR #211 cho SHA, PIL, checkpoint, processor và reclaim |
| GPU | 600 | 600 | Giữ trần hiện tại cho driver, CUDA và kiểm tài nguyên |
| Tổng trước native | 4.800 cộng launch | 8.400 | Cùng công thức dùng trong forecast và cấp vé |
| Native | Phần còn trước export | Phần còn trước export | Forecast chừa 900 cho admission/load và 300 cho đối soát, ZIP/SHA attempt. Trần child tính theo tổng job |
| Export supervisor và giữ raw | 600 | 600 | Các child dừng trước vùng này. Chừa 120 trong 600 giây để niêm phong supervisor |
| Job | 14.400 | 14.400 | Giữ quota hai GPU, thời hạn ticket, caps chiến dịch, RAM và tài nguyên |

Trần trước native là tổng các stage ở bảng. Forecast có sàn overhead
9.600 giây, gồm launch, pre-native, dự phòng trước call và niêm phong attempt.
Vé chỉ được cấp nếu giới hạn thấp nhất giữa trần job, quota hiện tại, quota
chiến dịch còn lại và thời hạn release còn đủ overhead, 600 giây export
và cửa sổ call đã ký. Bootstrap, launch restore và xuất evidence dùng bộ
hẹn giờ hữu hạn. Supervisor vẫn theo dõi và reap các process group từ admit
đến native. Vùng 300 giây ở cuối native nằm trong thời gian child.

Tại trần 14.400 giây, sàn overhead để lại 4.200 giây cho xử lý mẫu.
Để dự kiến đủ 669 mẫu, chỉ số đã làm tròn sau hệ số an toàn phải tối đa
6 giây/ảnh nếu overhead giữ ở sàn và quota đủ 28.800 physical GPU-seconds.
Hold call 30 giây đã ký vẫn dùng trước từng native call và trừ một lần ở cuối
forecast có throughput. Có thể xin Owner phê duyệt bound từ completion PR #211
đã xác minh. Grant mới ghim digest telemetry, overhead và call bound. Companion
đối chiếu các giá trị với completion đã niêm phong. Khi thiếu phê duyệt và
telemetry cùng nguồn, cap vẫn là tối đa 100 ảnh và có thể giảm theo quota.
Con số 6 giây là ngưỡng tính từ ngân sách. Chưa có số đo Operator đủ để xác
nhận một lượt 669 ảnh. [Release V5](https://github.com/tantdna2/SafeShift/pull/209#issuecomment-7033394502),
[release runtime PR #211](https://github.com/tantdna2/SafeShift/pull/211#issuecomment-7119513730).

## Xác minh lịch sử và dữ liệu

- Launch ghim SHA256 ZIP ngoài, sidecar, membership và SHA từng member trên
  Input chỉ đọc. Mỗi ZIP có một lần xác minh và một lần giải nén vào cây
  staging. Runtime replay raw/C1 một lần, kiểm kế hoạch và chuỗi cha, so sánh
  bản ghi với ticket rồi cài cây đã kiểm bằng rename. PR #211 còn mở lại ZIP
  để kiểm ancestry và import, sau đó recover khi staging và sau khi cài.
- Admit và native dùng hash inventory trong lịch sử đã ký để băm byte hiện
  thời của cây cài đặt, với kiểm SHA plan. Native làm việc này dưới khóa
  trước khi tạo attempt. Chỉnh byte, thêm/bớt member hoặc đổi plan chặn lượt.
  Setup, CPU và GPU tiếp tục kiểm cấu trúc reservation. Retention đối chiếu
  byte cây nguồn và đích với inventory đã xác minh, tránh mở lại các ZIP
  ancestor khi xuất. ZIP attempt mới vẫn xác minh đầy đủ.
- Admit, CPU và native vẫn kiểm projection, byte ảnh và checkpoint độc lập
  ở nơi sử dụng. CPU giữ SHA và PIL, native giữ kiểm danh tính trước reserve,
  SHA ảnh trước từng call và kiểm weights khi deserialize. Fast giữ chữ ký,
  hash hai mirror, capsule, seal và raw/C1 cho kết quả mới. Owner verifier
  vẫn thực hiện đối soát ZIP, raw và provenance đầy đủ cho final admission.
  Cách dùng pin archive và thứ tự dựa trên đường sealed history của InternVL3.5.

## Hồ sơ nguồn và thao tác Operator

| Thành phần ứng viên | SHA256 |
| --- | --- |
| Runtime source manifest | `3204960b386b8625d289a9a3dc95e98373712d44ee5e359df6e0a25db6de0e14` |
| V5 tool manifest | `13462015682a4bc62cad8a72622afe88e1d0734661e2c96895ed218b2cbcb9ff` |
| Fast companion | `f23bfbcbe81dd27bc697f13c5cb6b1beb08fb81f2f3f9d5e8a340f807df8b45e` |

1. Sau review, audit, merge được cấp riêng và hậu kiểm, giữ hai checkout
   chỉ chứa byte nguồn đã phát hành. V5 gốc dùng `57fb693648a03469eb25778e7a63f5be4ac0f501`.
   PR #211 dùng `f520688adef4c73a142a69d1542a630a147854ac`. Giữ nguyên
   checkout Operator có primary, mirror và khóa gốc. Owner phát hành Fast
   companion cho source/tool SHA mới. Có thể mang nguyên prefix #21 và
   `closure_snapshots` từ Fast release PR #211 khi hai mirror khớp. Các event
   sau prefix, gồm S22, dùng seal và hash evidence hiện có.
   [Fast PR #210](https://github.com/tantdna2/SafeShift/pull/210#issuecomment-7063393426),
   [Fast PR #211](https://github.com/tantdna2/SafeShift/pull/211#issuecomment-7119365972).
2. Dùng cùng tiền tố lệnh bên dưới cho `status` và `runtime-release-template`.
   Proposal xuất từ Fast, kiểm mirror/chữ ký/hash mà không replay sâu cả
   3.094 kết quả khi đủ seal. Chọn thêm `--review-pr211-throughput` khi cần
   đưa bound của completion PR #211 vào hồ sơ review. Với trạng thái đã báo,
   proposal phải ghim grant PR #211, registration, event #28, first Serial 23
   và đúng prefix hash. Owner điền commit, cửa sổ 30 ngày và bốn approval thật,
   lập supporting proof theo runbook trước. Bản proposal dùng để tính proof
   cần placeholder 64 chữ số 0 ở `authority_proof_sha256`. Thay placeholder
   bằng digest thật trước khi phát hành marker
   `SAFESHIFT_MINICPM_OFFLINE_RELEASE_V5`. [Luồng supporting proof](MINICPM_SERIAL19_RECOVERY.md#bàn-giao-sau-khi-có-quyền).
3. Sau khi có release mới, thêm `--runtime-release` và `--runtime-exports` vào
   tiền tố, dùng `forecast` rồi `stage` với Owner gate thật. Kiểm ordinals bắt
   đầu từ 3094. Nếu S22 còn active, xử lý theo hồ sơ và companion PR #211.
   Nếu S23 đã reserve, giữ ticket, hold, source và capsule của lượt đó.
   Dùng `export-active` theo grant đã reserve sau khi xác nhận trạng thái Owner UI
   và hạn vé. Nếu S23 reserve với PR #211, chỉ tạo proposal cutover sau khi S23
   được đối soát. Khi đủ 3.763 kết quả, truyền cả ba release cho Owner verifier
   và final admission. Grant, ticket và source của từng Serial được đối chiếu riêng.

```console
python -B -m scripts.minicpm_offline_fast --directory <primary> --historical-repo <v5> --previous-runtime-repo <pr211> --previous-runtime-release <pr211-locator> --previous-runtime-exports <pr211-exports> --operator-release <new-fast-locator> --owner-exports <new-fast-exports> runtime-release-template --output <unsigned-proposal>

python -B -c "from safeshift.fulltrain import contract; from safeshift.pilot.contract import digest; from scripts import minicpm_offline_continuation as v5, minicpm_offline_fast as fast; print(digest(contract.source_manifest())); print(digest(v5.tools_manifest())); print(fast.sha(fast.__file__)); print(v5.tool_blobs())"
```

## Timeout và custody

- Runtime ghi claim launch sau khi xác thực release, ticket và capsule.
  Nếu restore chạm 2.400 giây trước khi dispatch child và dọn xong bản sao
  staging, supervisor niêm phong `launch-stop.json`, claim và lỗi trong
  cặp ZIP/SHA. Owner dùng `--pre-native-closure` với đúng kernel ID và toàn
  bộ Output. Sau khi khớp job terminal, notebook, capsule và chứng cứ, Operator
  dùng `close-pre-native` hiện có. Hold và ordinal kế tiếp giữ nguyên.
- Khi retention timeout, supervisor giữ ZIP/SHA của attempt đã niêm phong
  và ghi `retention_failure.json`. Khi supervisor export timeout, giữ
  cây control, file `.zip.partial` nếu có và ghi `*-export-failure.json`
  trong thời gian còn lại. Log in trạng thái BLOCKED nếu thiếu thời gian ghi
  receipt. Owner đối chiếu ZIP/SHA, claims và provider Output trước khi
  quyết định cách thu hồi kết quả đã niêm phong.
- Bootstrap hoặc install thiếu receipt, staging dọn dở, native đã dispatch
  với chứng cứ thiếu, hoặc supervisor thiếu cặp ZIP/SHA đầy đủ đều cần
  đối soát Owner. Giữ reservation, toàn bộ Output và log của đúng kernel.
  Chỉ đóng theo đường đã xác minh. Thiếu file không chứng minh zero load/call.

## Kiểm thử CPU

Trước review, 23 test trọng điểm PASS trên WSL2, Python 3.14.4. Các bài gồm admit qua 600
giây theo đồng hồ mô phỏng, giới hạn từng stage, reserve export, thiếu
quota, launch timeout và reap process group thật, sửa ảnh/checkpoint/lịch sử,
12 ancestor với 3.094 bản ghi, thứ tự 669 ordinal, closure Fast, giữ hold
khi đã reserve và kiểm ba release trước đối soát cuối. Notebook ứng viên
được tạo từ commit local và biên dịch đủ hai cell code.
[Regression Serial 22](../tests/test_minicpm_serial22_recovery.py).

Sau review, 7 test trực tiếp PASS trên WSL2. Các test kiểm restore timeout
với ticket RSA và ZIP thật, thiếu receipt/Output, retention/export timeout
và closure Fast hiện có. Provider dùng fixture tổng hợp.

Các fixture dùng dữ liệu tổng hợp. Timing, GPU/RAM thực tế và khả năng
chạy đủ 669 ảnh trong một lượt thuộc lần chạy được Owner phê duyệt.
