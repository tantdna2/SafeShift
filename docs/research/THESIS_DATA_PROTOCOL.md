# SafeShift — T1: quyền, nguồn và tính khả thi dữ liệu

Ngày kiểm: **01/11/2026, Asia/Bangkok**. BASE:
`a113ef707970c50a7420c84e8a8e46fa2dc3db01`.
**T1 hồ sơ kiểm tra: hoàn tất để review; xác nhận cải tiến: BLOCKED.**
Đây là assessment và quy trình đề nghị chốt điều kiện, chưa là protocol frozen,
grant, final roster hoặc chứng nhận độc lập nguồn. Không chạy phương pháp triage.

## 1. Thẩm quyền, phạm vi và cách đọc bằng chứng

GitHub live xác nhận [PR158](https://github.com/tantdna2/SafeShift/pull/158)
MERGED lúc `2026-11-01T02:49:58Z`, merge đúng BASE; `git fetch origin main`
xác nhận main tại BASE. [Owner relay6552710543](https://github.com/tantdna2/SafeShift/pull/158#issuecomment-6552710543)
chấp nhận hướng false-safe, Qwen3 focal có điều kiện, tối đa hai peer ứng viên,
tạm dừng model thứ tư và cho làm T1. Quyết định ghi append-only tại
[DEC-20261101-T1](DECISIONS.md#dec-20261101-t1-owner-false-safe-direction).
Không diễn giải câu “chấp nhận hết” thành chữ ký học vụ, O2/O4/O5 hoặc quyền dữ liệu.

Đã đọc AGENTS/README/docs/ROADMAP/PROJECT_STATE và các phần liên quan của
DECISIONS, [kế hoạch Khóa luận](THESIS_EXECUTION_PLAN_2026.md),
[thiết kế T0](T0_FALSE_SAFE_DESIGN_20261101.md),
[evidence T0](T0_FALSE_SAFE_EVIDENCE_20261101.md),
[source gate](../SOURCE_FEASIBILITY_GATE_20261024.md),
[source receipt](../SOURCE_FEASIBILITY_RECEIPT_20261024.json),
[DATA_AND_ETHICS](../DATA_AND_ETHICS.md). Root ROADMAP/TASKS được tra ở checkout
lịch sử; main reset không có hai file này, theo AGENTS không tạo lại chúng.
T1 dùng lại T0 và source gate, không chạy lại recount/AUROC hoặc đọc metadata
audit toàn dataset có TEST. Source gate chứa bảng lịch sử xuyên split: chỉ đọc
tài liệu đã version control, không truy cập TEST hoặc sao chép ID vào sản phẩm T1.

| Mức bằng chứng | T1 thực sự làm / không suy rộng |
| --- | --- |
| VERIFIED_T1_METADATA | Hash/parse đúng hai receipt kỹ thuật TRAIN160 và hai manifest đã được T0 định danh; đối chiếu tổng status/HNLO/identity, không đọc ảnh hoặc ZIP. Kiểm tính nhất quán JSON T0 với source receipt. |
| INHERITED_T0_AUDIT | 35/2455/13 và join160 148/12/67/4/1 là recount T0; [ChatGPT reconciliation](https://github.com/tantdna2/SafeShift/pull/158#issuecomment-6552506855) ghi Antigravity độc lập kiểm archive gốc. T1 không nhận đã rerun archive hoặc audit raw. |
| INHERITED_SOURCE_AUDIT | License, inventory, duplicate và thiếu provenance từ DATA_AND_ETHICS/source gate; không mới kiểm ảnh, nhãn, upstream archive hoặc pháp lý. |
| UNKNOWN / PENDING | Số nguồn độc lập, nguồn V/T, quyền mới, đủ error events, final qualification và thresholds. Unknown không bằng 0 nguồn tồn tại ngoài phạm vi đã kiểm. |

## 2. Registry mức hồ sơ: nguồn, số lượng, quyền và H/D/V/T

H = lịch sử đã quan sát; D = phát triển/thăm dò; V = chọn/kiểm cấu hình trước
freeze; T = đánh giá cuối độc lập, kín với phát triển. H có thể dùng làm D với
claim hồi cứu rõ ràng; đổi tên hoặc chia lại H không tạo V/T độc lập.

| Nguồn/cohort hiện có | Nguồn gốc và quyền có bằng chứng | Ảnh/nhãn có bằng chứng | Exposure, phụ thuộc và vai trò |
| --- | --- | --- | --- |
| InspecSafe-V1 TRAIN | HF `Tetrabot2026/InspecSafe-V1` revision `f3cb7d3e7827c1afc1c5bfd0524257984bba46ab`; Zenodo v1.0.1. Audit kế thừa ghi CC-BY-4.0; SafeShift chỉ nghiên cứu phi thương mại, không redistribute raw. Backup local chưa được chứng minh byte-identical upstream. | 3763 ảnh; Level01/02/03/04 = 490/251/8/3014. Nhãn mức ảnh từ hợp đồng folder token, không expert adjudication mới. | Đã phân tích lặp lại. H; D thăm dò trên saved metadata/output có quyền. V/T độc lập: không. |
| TRAIN160 của hai candidate peers | Subset TRAIN cùng manifest SHA `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`; kế thừa quyền nguồn, không nguồn phát hành mới. | 160 unique TRAIN; 48/24/8/80; có domain/group/dimensions/image hash. T1 kiểm hai manifest cùng bytes; supplement rỗng, `qwen_verified` rỗng. | Đã chọn có phân tầng/envelope kích thước, đã chạy và xem outputs. H/engineering, D có điều kiện series/paired ledger; không prevalence tự nhiên, V hoặc T. |
| Qwen3 V4, Qwen2.5, InternVL3-2B saved TRAIN reports | Sản phẩm dẫn xuất từ TRAIN, source/archive pins ở T0 và source receipt. Quyền chạy cũ không chuyển sang run mới. | Q3 planned3763/success3539; Q2.5 và IVL3 lịch sử3763 SUCCESS mỗi model. Đây là output trên cùng dữ liệu, không thêm ảnh/nguồn độc lập. | H; saved-output D đúng scope. InternVL3-2B không phải InternVL3.5. Q3 gốc giữ riêng Recovery224/composite. |
| InternVL3.5 và MiniCPM FP32 official160 | Receipt đúng hash T0; MiniCPM đúng resampler FP32, weights vẫn FP16/eager, không phải toàn model FP32. Exact model revisions/config/descriptor ở T0 §4 và quyết định adoption. | IVL3.5:135 SUCCESS/25 INVALID,135 HNLO số. MiniCPM:155 SUCCESS/5 INVALID,0 HNLO số. Mỗi model160 planned; không tạo320 ảnh khác nhau. | H/technical evidence. Scientific series selection/pooling PENDING; technical PASS không final thesis qualification. D paired analysis phải ghi rule và quyền riêng trước dùng kết quả. |
| Recovery224, S2 diagnostic, smoke/failed/recovery histories | Cùng TRAIN/attempts lịch sử; source gate giữ lineage riêng. | Recovery224 có224 SUCCESS theo source gate, không phải224 ảnh mới ngoài TRAIN. T1 không tái đọc archive. | H riêng; không bổ sung vào baseline Q3 V4 gốc, không chọn output thuận lợi hoặc tạo T. |
| InspecSafe TEST | Chỉ trích inventory tài liệu lịch sử, không mở trong T1. | 1250 theo audit; không kiểm lại ảnh/nhãn/manifest TEST. | LOCKED. Không là T thay thế. Lịch sử W1 đã xem thông tin và có bằng chứng overlap; chưa đủ chứng nhận độc lập hoặc giữ kín. |
| Nguồn công nghiệp ngoài InspecSafe / V / T | Chưa có source dossier/custodian/rights được định danh đủ trong gói đã kiểm. Không tìm/tải dataset mới. | UNKNOWN; không khai báo đã có ảnh, nhãn, site hay người gán nhãn. | Chưa gán D/V/T; BLOCKED đến khi có hồ sơ và quyền cụ thể. |

License CC-BY-4.0 ở đây là **kết luận audit kế thừa**, không phê duyệt pháp lý
mới. Hai lần thử đọc public README đúng revision qua web (blob/raw) không truy
cập được; không nâng license thành VERIFIED_T1. Cần bản điều khoản đúng release
và chain-of-custody do người có quyền cung cấp nếu mở nguồn/quyền mới. Quyền
ảnh/annotation, paper figures, code, weights, dịch vụ cloud và public export
phải được xét riêng; không suy license của một loại sang loại khác. Không tải
ảnh/weights hoặc liên hệ bên thứ ba. Chính sách dự án chặt hơn license được
ghi trong DATA_AND_ETHICS vẫn giữ nguyên.

### Metadata nguồn và nguy cơ liên quan

Source gate xác minh lịch sử **44 exact TRAIN pairs/88 ảnh**, 3636 cạnh
near-pool TRAIN (ứng viên, không confirmed duplicates). Audit kế thừa ghi
7 exact pairs xuyên split; không tái kiểm TEST. Source gate cũng tìm **0/7**
pair mappings trong visual catalog khớp đầy đủ bảng đúng hash: không dùng
narrative đó làm membership/source certificate. Không sao chép ID riêng tư.

Folder-domain là năm ngành; point ID, platform, filename/family heuristic,
group của manifest và hash không cung cấp map chính thức đủ coverage tới
site/video/camera/session. Metadata manifest160 không có các trường source
đã xác minh đó. Cùng video/góc máy có thể phụ thuộc; khác hash/point/domain
không chứng minh độc lập. Hiện chưa đếm được số nguồn độc lập của3763,160,
35 lỗi hoặc4 lỗi. Các group counts của source receipt là sensitivity, không
effective sample size. Unknown source phải giữ unknown, không tạo singleton
nguồn giả cho từng ảnh. Khả năng overlap với dữ liệu pretraining VLM cũng
chưa được xác minh; source-disjoint của dự án không chứng minh pretraining-clean.

## 3. Tư cách thực nghiệm và bảng GO/BLOCKED/NO-GO

GO = khả thi trong phạm vi nêu rõ, không tự cấp run grant. BLOCKED = thiếu
bằng chứng/quyền có thể bổ sung. NO-GO = cách làm hiện tại không hợp lệ; phải
đổi cách thiết kế/được quyết định riêng, không chữa bằng thêm ảnh cùng nguồn.

| Hạng mục | Verdict | Bằng chứng / điều kiện mở hoặc giới hạn |
| --- | --- | --- |
| Kiểm hồ sơ, hash/receipt và mô tả TRAIN | **GO; đã thực hiện T1** | Chỉ inputs cho phép, phép kiểm §6; không tạo kết quả phương pháp. |
| Phân tích khám phá TRAIN từ saved outputs | **GO về dữ liệu, development-only** | T0 cho35 lỗi Q3/2455 Normal,13 severe; nhận dạng/run/status đã có. Task phân tích tiếp phải pin cohort/output/selection và giữ224 missing, không claim generalization hay quyền ảnh mới. |
| Chuẩn bị/thử CPU không học | **GO cho fixtures tổng hợp và chuẩn bị hợp đồng** | Có thể kiểm denominator, tie, missing, overload, no-score bằng synthetic sau task riêng; T1 không triển khai triage. Chạy phương pháp thật trên saved TRAIN160 còn **BLOCKED** bởi O2 và rule chọn series/paired ledger; không cần V/T để debug synthetic. |
| Xây dựng/fit ranker học từ dữ liệu thật | **BLOCKED; không huấn luyện T1** | 35 lỗi toàn Q3 nhưng peers chỉ có160; intersection lỗi Q3 chỉ4 (1 severe), không được lấy35 làm positive support panel. Nguồn độc lập chưa biết, V chưa có. Cần O2/O4/O5, paired D/GT/source/event ledger và feasibility precision; không áp quy tắc số events/feature máy móc. |
| Đánh giá xác nhận trên nguồn độc lập | **BLOCKED** | B1–B6 bên dưới; không V/T lawful, source/custody/GT/precision đủ bằng chứng; mọi kết quả hiện tại chỉ H/D. T1 vẫn hoàn tất assessment. |
| Gọi TRAIN chia lại hoặc năm miền là T/5 nguồn độc lập | **NO-GO** | Exposure và source confounding không mất bởi random/group split. Chỉ internal sensitivity được ghi rõ khi có task. |
| MiniCPM HNLO score arm hiện tại | **NO-GO với artifact hiện tại** | 0 numeric HNLO; finite logits không bảo đảm alignment. Label-only peer vẫn là ứng viên; không sửa parser/token để ép score. |
| Pool Recovery224/composite thay Q3 V4 hoặc chọn run đẹp | **NO-GO** | Giữ35/13 gốc, không dùng38/14 composite. Series selection phải quyết định trước phân tích tiếp, bảo toàn mọi failures. |
| Mở TEST, GPU/inference, annotation/thu thập mới trong T1 | **NO-GO trong scope T1** | Owner cấm rõ; không xem approval hướng nghiên cứu là grant. |

Điều kiện dùng số hiện có: planned/status luôn tách khỏi valid-label cohort;
Q3 V4 **3763=3539+1 TECHNICAL_ERROR+223 NOT_ATTEMPTED**; join160
**148 SUCCESS+12 NOT_ATTEMPTED**,67 Normal/4 false-safe/1 Level01.
Hai peer counts không cho biết họ bắt được bao nhiêu lỗi Q3: cần exact join
ID/image/GT/prompt/config/run/status và bảng gained/lost trên cùng focal outputs.
T1 không tính capture gain, peer utility, CI hoặc đổi tiêu chí metric.
Một lỗi thay capture trên4 lỗi tới25 điểm phần trăm chỉ là độ phân giải đếm,
không phải CI hay minh chứng đủ cỡ mẫu. Không dùng lỗi của peer làm lỗi focal.

## 4. Checklist Owner và điều kiện đóng từng blocker

Mỗi hàng cần người có thẩm quyền, artifact/version/hash, ngày, phạm vi và trạng
thái kiểm. Đây là yêu cầu chuẩn bị; T1 không gửi tin nhắn cho bên thứ ba hoặc
tự điền tên/chữ ký. Chứng từ/ID riêng tư giữ ngoài Git; chỉ commit receipt sạch.

| Blocker | Người cần cung cấp | Checklist và điều kiện đóng |
| --- | --- | --- |
| B1 — rights/provenance | Chủ dữ liệu hoặc người được ủy quyền; Owner lưu hồ sơ | [ ] Release/license hoặc văn bản cho phép đúng tập; chain-of-custody từ acquisition tới manifest/checksum; phạm vi research/model processing/cloud/annotation/storage/export, retention và hạn chế riêng tư; bằng chứng quyền với ảnh/người/site. Không dùng lời đồng ý Owner thay quyền bên thứ ba. |
| B2 — source independence | Nhà cung cấp nguồn + custodian | [ ] Registry private: opaque sample key, image hash, source owner/site/video/sequence/camera/session/time, version, evidence ref, verified/unknown và coverage. [ ] Map liên kết xuyên nguồn/duplicate, phương pháp/threshold/review false negatives và unresolved links. Không cắt connected component đã xác minh qua H/D/V/T. Không coi absence of exact duplicate là chứng nhận độc lập. |
| B3 — exposure/custody V/T | Custodian có quyền; Owner chỉ định vai trò/access | [ ] Exposure ledger: ai đã thấy ảnh/GT/predictions/kết quả, lúc nào, mục đích nào; đối chiếu H/D. [ ] T manifest/GT seal và hash, quyền truy cập, nhật ký mở, release sau freeze. [ ] Chứng nhận overlap theo quyền với H/D/V và nguồn khóa do custodian tự kiểm, không chuyển TEST cho developer. Chứng nhận phải nêu phạm vi chưa kiểm, không chỉ “không trùng ID”. |
| B4 — nhãn tương thích | Chuyên gia an toàn + người sở hữu annotation | [ ] Rubric Level01–04 tương thích ngữ nghĩa, version và rights; kế hoạch hai annotator độc lập mù VLM, adjudicator, bất đồng/uncertain/ungradable và agreement criterion chờ duyệt. [ ] Sampling/quality audit và costs. Không dùng VLM làm GT, không sửa raw labels InspecSafe; polygon vật thể không là hazard-rationale GT. |
| B5 — protocol, events, cost | Owner quyết định phạm vi dự án; người duyệt khoa học/học vụ có thẩm quyền | [ ] O2 version, O5 numerical register từ §5, qualification/series rule, nguồn lực examiner/GPU/storage. [ ] Xác nhận contribution/negative route học vụ hoặc ghi rõ chưa xác minh. Không tự ký thay Research Lead/giảng viên. |
| B6 — model/run qualification | Người giữ outputs và người có quyền chạy | [ ] Exact model/revision/source/config/parser/HNLO/env/rights, raw-before-parse, run/attempt selection ledger, paired outputs và missing coverage. [ ] Final roster/utility rule trên D/V, grant riêng từng run nếu cần. Old PASS/release không tự cấp quyền nguồn mới. |

Quy trình đóng B2/B3: custodian kiểm map và liên kết bằng dữ liệu họ được phép
truy cập; gửi certificate có hash, số verified/unknown, phương pháp và ngoại lệ.
Assignment D/V/T chỉ là đề nghị sau certificate, phải được chấp thuận append-only
trước áp dụng; T1 không tạo manifest split mới. V phục vụ chọn baseline/policy;
T không được dùng chọn model/budget/feature. Nếu registry không đủ hoặc cùng
nguồn qua tập, xác nhận tiếp tục BLOCKED; không cho split hiện hữu “PASS tạm”.

## 5. Quy trình chốt O2/O4/O5 trước thí nghiệm xác nhận

Tất cả giá trị dưới đây **PENDING**. Đây là trình tự tạo bằng chứng để người
có thẩm quyền quyết định; chưa thu thập, mô phỏng power hoặc chọn số tối thiểu.
Giữ estimands/queue đề xuất ở T0 §§6–10, không sửa M2.

| Đại lượng cần chốt | Quy trình dựa trên bằng chứng / artifact cần duyệt |
| --- | --- |
| Review capacity K/b | Định nghĩa batch/time window và population planned P trước; đo thời gian review có quyền trên D/U-development, thời gian ca khó/adjudication, số examiner và phút thực có. Tính capacity thực, dành workload cho mandatory missing; trình b/K và chính sách overload. Không dùng b=20% mặc định. |
| Gain false-safe delta | Chọn baseline mạnh nhất trên D/V theo rule/search budget được duyệt, cùng P/C/F/K. Người phụ trách xác định số lỗi bổ sung đáng giá so chi phí; dùng paired gained/lost và khoảng gain khả dĩ để đề xuất delta. Báo absolute cases và capture numerator/denominator;10 điểm phần trăm chưa được duyệt. |
| Severe guardrail | Định nghĩa Level01 false-safe còn ngoài queue so baseline, absolute severe missed và rate với denominator rõ; giữ GT unresolved riêng. Người có thẩm quyền chốt harm margin và one-sided uncertainty criterion trước target. Không có observed severe harm hoặc0 severe support không chứng minh an toàn/noninferiority. |
| Coverage và INVALID | Planned/status từng model, GT valid/unresolved, score missing và mandatory slots phải đủ kế toán. INVALID không Normal, không dropped SUCCESS-only denominator. Pin từng arm M/E, same K; mandatory>K phải OVERLOAD/backlog, không PASS bằng cách bỏ ca. Báo operational comparison và common-signal comparison riêng; MiniCPM score N/A nhưng label có thể dùng. Coverage minima/overload tolerance cần workload và O5, chưa có giá trị. |
| Số nguồn và số lỗi cần thiết | Sau registry và pilot D có quyền: thống kê source sizes, focal-Normal, FS/severe, paired discordance và missingness theo source. Dùng dải event rates/cluster dependence, không extrapolate35/3763 hoặc4/160 thành prevalence T. Mô phỏng thiết kế paired theo source cho gain/precision/severe/cost, thêm kịch bản ít nguồn/zero events/cluster lệch. Chọn số nguồn, FS và severe events từ precision và feasibility đã chấp nhận; không có N ảnh cố định bảo đảm đủ. |
| Uncertainty và stopping | Đề nghị paired cluster resampling trên **nguồn đã xác minh**, giữ arms cùng draw, tính queue theo batch policy frozen; nếu nguồn lồng site/session phải xác định cấp độc lập. Chốt CI level, số draws/seeds, estimand, undefined/zero-event draws, multiplicity và success/inconclusive/failure rules trước T. Nguồn quá ít/không xác minh → không CI nguồn; không bootstrap ảnh giả độc lập, không tự khóa95%/80%. Không kéo dài T đến khi có ý nghĩa; kế hoạch bổ sung chỉ qua review mới, bảo toàn exposure. |
| Chi phí ba model và người | Lập ledger calls/loads, GPU-time/wall time, failed/recovery/screening, peak RAM/VRAM, storage và giá/quota thực; full panel tối đa3N calls, peer-on-focal-Normal khoảng N+2C chỉ khi policy duyệt. Cached ablation không làm inference gốc miễn phí. Human cost gồm sourcing/annotation/adjudication/review/queue backlog. Chưa có giá hoặc latency đủ để báo số tiền; receipt160 chỉ chứng minh calls/trạng thái đã ghi. |
| Freeze và dừng | Hash O2/O4/O5, source/GT/custody, final roster/qualification, series policy và code/env trước target; grant target riêng. Hash/custody sai → dừng input; không source/rights/events/precision → BLOCKED xác nhận; model không đạt → giữ negative qualification, trình giảm peer/scope trước T. Không tìm model thứ tư hay đổi endpoint sau thấy T. |

Phương pháp phải giữ E1 baseline công bằng, E2 ablation (bỏ h/từng peer,
không học vs learned nếu được phép), E3 stress (shared errors, missing,
overload/shift), E4 lỗi tốt hơn/tệ hơn/không đổi và E5 tái lập raw/provenance.
Chưa có phép nào được chạy T1. Capture chỉ đo đưa lỗi tới review, không chứng
minh người sửa đúng hay giảm tai nạn; user study cần O7 riêng.

## 6. Tái lập kiểm tra đã chạy và giới hạn

Receipt sạch: [T1 receipt](evidence/t1_feasibility_20261101.json). Chỉ kiểm
metadata/consistency, không parser dataset hoặc pipeline mới. Python standard
library; seed=null; không cài dependency. Script bên dưới là phép kiểm một lần
được nhúng để tái lập, không module sản phẩm. Tạo bản local ignored tại
`data/processed/t1_20261101/check.py` từ fenced block (LF + một newline cuối).
Chạy từ repository root T1, với hai receipt và hai manifest ở root artifact
riêng đã được cho phép; đường dẫn đối số là tương đối, không copy ảnh/ZIP.

```console
python -B data/processed/t1_20261101/check.py --artifact-root ../.. --output data/processed/t1_20261101/receipt.json
git diff --check
```

`../..` áp dụng cho worktree dưới `.worktrees/`; clean clone dùng `.` nếu đã
được cấp đúng artifacts private. Thiếu/hash sai phải FAIL, không tìm dataset
hoặc dùng artifact khác. Output có sẵn bị từ chối; so JSON với receipt commit.

```python
import argparse, hashlib, json, platform, subprocess
from collections import Counter
from pathlib import Path

BASE = 'a113ef707970c50a7420c84e8a8e46fa2dc3db01'
p = argparse.ArgumentParser()
p.add_argument('--artifact-root', required=True)
p.add_argument('--output', required=True)
a = p.parse_args()
root = Path(a.artifact_root)
sha = lambda b: hashlib.sha256(b).hexdigest()
inputs = {}
checks = []

def check(name, condition):
    if not condition:
        raise RuntimeError(name)
    checks.append(name)

def tracked(path):
    b = Path(path).read_bytes()
    original = subprocess.check_output(['git', 'show', BASE + ':' + path])
    check('base_bytes:' + path, b == original)
    inputs[path] = sha(b)
    return json.loads(b)

t = tracked('docs/research/evidence/t0_false_safe_20261101/summary.json')
s = tracked('docs/SOURCE_FEASIBILITY_RECEIPT_20261024.json')
r = t['saved_report_recount']
j = r['original160_metadata_join']
check('q3_original_counts', r['planned'] == 3763 and
      r['status'] == {'SUCCESS':3539, 'TECHNICAL_ERROR':1, 'NOT_ATTEMPTED':223}
      and r['predicted_normal'] == 2455 and r['false_safe'] == 35
      and r['false_safe_gt_levels'] == {'Level01':13, 'Level02':22})
check('q3_denominators', sum(r['status'].values()) == r['planned'] and
      sum(r['success_gt_levels'].values()) == r['status']['SUCCESS'] and
      sum(r['false_safe_gt_levels'].values()) == r['false_safe'])
check('q3_join_inherited', j['qwen_status_counts'] ==
      {'SUCCESS':148, 'NOT_ATTEMPTED':12} and
      (j['qwen_predicted_normal'],j['qwen_false_safe'],j['qwen_severe_false_safe'])
      == (67,4,1) and j['image_hash_level_domain_matches'] == 160)
check('source_claim_limits', s['source_identity_verified'] is False and
      r['verified_independent_source_count'] is None and
      t['V_independent_cohort'] is None and t['T_independent_cohort'] is None
      and r['recovery_pooled'] is False and r['TEST_access'] is False)
check('source_receipt_count', s['original_qwen3_v4']['success_n'] == 3539 and
      s['original_qwen3_v4']['status_counts'] == r['status'])
for model, expected, hnlo in [('minicpm4',155,0), ('internvl35',135,135)]:
    projection = t['official160_receipt_projections'][model]
    path = projection['receipt_path']
    b = (root / path).read_bytes()
    check(model + ':receipt_hash', sha(b) == projection['receipt_sha256'])
    inputs[path] = sha(b)
    v = json.loads(b)
    keys = ['run_id','attempt_id','series_id','run_kind','archive_sha256',
            'counts','native_calls','native_steps','numeric_hnlo_count',
            'pooling_allowed','hnlo_status_counts']
    check(model + ':projection', all(v[k] == projection[k] for k in keys))
    check(model + ':counts', v['counts'] == {'SUCCESS':expected,
          'INVALID':160-expected,'TECHNICAL_ERROR':0,'NOT_ATTEMPTED':0}
          and v['numeric_hnlo_count'] == hnlo and v['native_calls'] == 160)
paths = ['data/processed/m160/verified/pilot_manifest.json',
 'data/processed/p160/work/review-only/history/'
 'owner_internvl35_55badcf1d55d44d98b74324c58b552bf/pilot_manifest.json']
for i,path in enumerate(paths):
    b = (root / path).read_bytes()
    check('manifest_hash:' + str(i), sha(b) == t['official160_manifest']['sha256'])
    inputs[path] = sha(b)
m = json.loads(b)
rows = m['main']
check('manifest_train_membership', len(rows) == 160 and
      len({x['sample_id'] for x in rows}) == 160 and
      all(x['split'] == 'TRAIN' for x in rows) and not m['supplement'])
check('manifest_levels', Counter(x['level'] for x in rows) ==
      {'Level01':48,'Level02':24,'Level03':8,'Level04':80})
check('manifest_no_source_certificate', not m['qwen_verified'] and
      all(not ({'site','video','camera','session'} & set(x)) for x in rows))
out = {'schema':'safeshift-t1-metadata-check-v1', 'base':BASE,
       'python':platform.python_version(), 'platform':platform.platform(),
       'dependencies':[], 'seed':None, 'input_sha256':inputs,
       'script_sha256':sha(Path(__file__).read_bytes()),
       'checks':checks, 'PASS':len(checks), 'FAIL':0, 'SKIP':0,
       'scope':'METADATA_ONLY_NOT_RAW_REPLAY_OR_NEW_RECOUNT',
       'model_calls':0, 'TEST_accessed':False}
dest = Path(a.output)
dest.parent.mkdir(parents=True, exist_ok=True)
with dest.open('x', encoding='utf-8', newline='\n') as f:
    f.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'PASS':len(checks),'FAIL':0,'SKIP':0}))
```

Kiểm cuối: **18 metadata checks PASS, 0 SKIP, 0 FAIL** trong receipt;
**10 documentation checks PASS, 0 SKIP, 0 FAIL** riêng: prefix DECISIONS bằng
bytes BASE; suffix PROJECT_STATE lịch sử nguyên byte; UTF-8; scan đường dẫn
máy/sample IDs/token/conflict;13 local links tồn tại; fences cân bằng;
compile/hash script nhúng khớp receipt; receipt khớp bản local; đúng bốn file;
`git diff --check`. Để tái kiểm, lấy bytes BASE bằng `git show BASE:path`,
so prefix/suffix, trích code như hướng dẫn rồi compile/SHA256, kiểm các link
tương đối trong phần thêm và đối chiếu `git diff --name-only BASE` cùng
`git ls-files --others --exclude-standard` với bốn file bàn giao.
Đây là **28 checks**, không phải28 unit tests sản phẩm. Không nhận các tests51
lịch sử của source gate thành tests T1. Bốn nhóm
**SKIP có chủ đích**: (1) full unit/native/GPU suite vì không code sản phẩm;
(2) archive/raw recount vì kế thừa T0 đã audit; (3) TEST/new data vì ngoài quyền;
(4) ranker/triage/CI/power vì ngoài T1 và gates chưa đủ. Không raw/ảnh/ZIP được đọc.
Các lỗi công cụ ban đầu: đọc docs/ROADMAP tại checkout cũ không có; GitHub
comment tool cần `repo_full_name`; tạo worktree cần quyền ghi Git metadata;
inspection thử khóa `samples` sai với manifest dùng `main`; lần kiểm đầu
FAIL ở split do checker đòi `train` trong khi metadata thực là `TRAIN`, đã
sửa checker, không sửa dữ liệu. Một lần ghi nháp qua PowerShell mất Unicode
bị assertion chặn; đã phục hồi prefix BASE và viết UTF-8 trước kiểm cuối.
Checker privacy ban đầu nhận nhầm phần cuối scheme HTTPS là đường dẫn Windows;
đã sửa ranh giới regex và chạy lại; ví dụ literal trong ghi chú lỗi cũng được
bỏ để tránh false positive. Các checker FAIL ban đầu (split và privacy) được
giữ trong lịch sử thao tác; kết quả cuối ở trên không che chúng.
Đây là lỗi thao tác đã xử lý, không bằng chứng dataset hỏng hoặc tests PASS.
Public README license không truy cập được vẫn là giới hạn chưa khép.

T1 dùng skill experimental-design để kiểm đơn vị độc lập và phụ thuộc, không
chạy scripts DOE. Ghi nhận công cụ: Kassis, T., Agarwal, V., He, Y., Patel, D.,
& Brueckner, A. M. (2026), [Scientific Agent Skills](https://doi.org/10.48550/arXiv.2609.00065),
metadata arXiv hiện hành v2 được đọc01/11/2026; không là evidence khoa học SafeShift.
Nguyên tắc kiểm dependence tham chiếu [NIST về autocorrelation](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35c.htm);
T1 không giả đã đo autocorrelation hoặc chọn được bootstrap hợp lệ.

## 7. Bàn giao và NEXT TASK duy nhất

T1 hoàn tất assessment khi Draft PR có hồ sơ này, receipt, quyết định đúng
phạm vi và PROJECT_STATE; không yêu cầu V/T phải GO mới được hoàn tất T1.
Hiện **development CPU tổng hợp/chuẩn bị hợp đồng GO; learned ranker và xác
nhận độc lập BLOCKED**. O1/O3 chỉ ghi phần ý chí Owner; O2/O4/O5, qualification
cuối, học vụ và quyền mới tiếp tục PENDING. Giữ toàn bộ hồ sơ Seminar/T0 cũ.

**NEXT TASK duy nhất:** hoàn thiện **gói chứng từ nguồn/custody và quyết định
O2/O4/O5** theo checklist B1–B6 để review: Owner thu xếp hồ sơ từ người có quyền,
Codex kiểm metadata/chứng từ được cung cấp và ghi phần thực sự khép. Không
thu thập ảnh, annotation, training, inference hoặc mở T trong task giấy tờ này.
Có thể làm mà không giả nguồn V/T đã tồn tại; không mở T2 thực nghiệm khi gates
chưa đạt. Dừng T1 tại một Draft PR cho ChatGPT kiểm GitHub và quyết định audit.
