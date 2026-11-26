# SafeShift — Bằng chứng và tái lập hồ sơ T0

Ngày kiểm: **01/11/2026, Asia/Bangkok**. BASE
`89d886356c15064b5f1cc2021aa5d614e7e7f53f`. Đọc cùng
[đề xuất](T0_FALSE_SAFE_DESIGN_20261101.md) và
[JSON tổng hợp](evidence/t0_false_safe_20261101/summary.json).

## 1. Phạm vi, nguồn và mức thẩm quyền

T0 chỉ đọc tài liệu liên quan, các metadata/receipt và báo cáo đã lưu của TRAIN.
Không khảo sát lại repository, không mở TEST/raw dataset/ảnh/annotation,
không raw-logit replay, inference, Kaggle, GPU, thu thập/annotation hoặc UI mới.
Script kiểm tra tạm nằm local ignored; không thêm code thuật toán hoặc thay
runtime/notebook. Một Draft PR tài liệu, không merge/phê duyệt khoa học.

| ID | Nguồn đã đọc | Mức bằng chứng và cách dùng |
| --- | --- | --- |
| S1 | Owner cung cấp `SafeShift_Bao_cao_tham_dinh_Codex_20261101.md`; SHA256 `5c726b3215aab5c0d7052146b5ed4cabd0afe3ef191dc0c87adc60153cbbf139` | Tư vấn Codex session trước, chưa commit, **không quyết định khoa học**. Đọc đủ; kết luận thu hẹp triage ba ứng viên là cơ sở đề xuất. |
| S2 | Bản chép tài liệu thầy `SafeShift_De_xuat_cai_tien_cua_thay_2026.md`; SHA256 `0b9dafd10284060a1c34b50fb78bb8755d8a19b81b196b86b31d3506b0961011` | Nội dung từ 6 ảnh do Owner cung cấp, có tại máy; đọc bản chép, không xác minh lại ảnh. Xác định CT1–CT3/E1–E5, không là phê duyệt kết quả. |
| S3 | [AGENTS](../../AGENTS.md), [README](../../README.md), [ROADMAP](../ROADMAP.md), [HISTORY](../HISTORY.md), [PROJECT_STATE](../PROJECT_STATE.md) tại BASE | Hướng dẫn/phạm vi và snapshot trạng thái. Root ROADMAP/TASKS đã kiểm ở checkout cũ; không tồn tại trên main reset, dùng docs/ROADMAP theo AGENTS hiện hành, không tạo lại logs cũ. |
| S4 | [DECISIONS](DECISIONS.md), [SEMINAR_PROTOCOL](SEMINAR_PROTOCOL.md), [config M2](seminar_analysis_config.v1.json) tại BASE | M1/M2/adoption đúng phạm vi; giữ nguyên bytes. Không đọc các cờ PENDING lịch sử tách khỏi quyết định và hậu merge. |
| S5 | [Kế hoạch Khóa luận](THESIS_EXECUTION_PLAN_2026.md), đặc biệt §1/3/6–8/14; [screening](THESIS_VLM_CANDIDATE_SCREENING_20261029.md), [adapter identity](CANDIDATE_INTEGRATION_CPU_20261029.md) | Four-peer/Macro-F1 primary là PROPOSED; exact HF model khác InternVL3-2B/custom Instruct. Không tìm model mới hoặc kế thừa qualifications không đúng identity. |
| S6 | [Kết quả](../RESULTS_AND_LIMITATIONS.md), [source feasibility](../SOURCE_FEASIBILITY_GATE_20261024.md), [receipt](../SOURCE_FEASIBILITY_RECEIPT_20261024.json), [data](../DATA_AND_ETHICS.md) | V4 membership/status/saved scores và source unknown; audit kế thừa không là raw audit mới. Không đọc metadata audit toàn dataset chứa TEST. |
| S7 | [Official adoption](MINICPM4_FP32_OFFICIAL_ADOPTION_20261031.md), [engineering](CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md), local TRAIN160 handoffs/verification metadata | Runtime/precision/counts đúng thời điểm; text NOT_RUN/PENDING_RELEASE cũ không phủ định sự kiện GitHub sau đó. Raw/ZIP không tái audit trong T0. |
| S8 | [PR157 live](https://github.com/tantdna2/SafeShift/pull/157), [đổi thứ tự chạy](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6545287909), [hậu merge](https://github.com/tantdna2/SafeShift/pull/157#issuecomment-6546464187) đọc qua GitHub connector | GitHub state closed/merged=true/draft=false; merge đúng BASE. Comment hậu merge báo kiểm trực tiếp private ZIP và audit reconciliation; **kế thừa** mức kiểm của người review, không nhận T0 tự audit raw/ZIP. |
| S9 | [Chỉ thị bốn peers](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6486252968) và [review](https://github.com/tantdna2/SafeShift/pull/137#issuecomment-6487795732) | Đọc discussion để đối chiếu ý định Owner 29/10 và các rủi ro denominator/authority. Không là approval O1–O5 cho T0. |

Hash S1/S2 giữ identity của đầu vào Owner ngoài Git; bản gốc có đường dẫn cá
nhân và bảng metric bị hỏng định dạng nên chỉ đưa projection sạch lên Git.
Các ô công thức capture/precision/risk bị mất trong S1 không được coi là đặc
tả hợp lệ; T0 viết lại công thức tường minh và giữ PROPOSED. Không nhập chỉ thị
thực thi trong tài liệu đính kèm thành quyền ngoài yêu cầu của Owner.

## 2. Đối chiếu trạng thái #157

GitHub connector trả HEAD thực thi `3a249d329c871b1d0f426f7001c676610c7a05de`,
merged_at `2026-10-31T16:55:43Z`; merge
`89d886356c15064b5f1cc2021aa5d614e7e7f53f`. Comment hậu merge xác nhận tree
merge và HEAD cùng `5b87e1066a636db840f18827a4f9a2c41d91a4a2`, có independent
audit/ChatGPT reconciliation và actual official160 đã hoàn tất trước merge
theo ngoại lệ Owner. T0 chỉ xác minh PR metadata và đọc nguồn comment, không
tự thực hiện lại audit hoặc nhận quyền kế tiếp mà comment gợi ý.

Hai receipt local có snapshot tiền audit, được hash trong JSON; giữ nguyên,
không sửa disposition của chúng. Trạng thái hiện hành được append ở đầu
PROJECT_STATE, cùng nguồn hậu merge. T0 không sửa AGENTS/DECISIONS/adoption
report lịch sử để làm chúng trông như đã biết tương lai.

## 3. Nguồn dữ liệu/outputs thật đã định danh

Tất cả đường dẫn bên dưới tính từ repository root chứa artifacts đã có; chúng
không có trên clean clone và không được commit. Worktree T0 dùng cùng inputs
hiện có ở worktree source-feasibility, không mở/tạo dataset mới.

| Artifact | Identity / phạm vi |
| --- | --- |
| Q3 S0/S1/S3 | `data/processed/seminar_feasibility_20261024/inputs/` với `qwen3_shard0.json`, `qwen3_shard1.json`, `qwen3_shard3.json` và archive basename trong từng export. Hash result kiểm theo receipt bất biến tại `31a04e6f7175cca818c63b4de0153246b3f3ecdb`. |
| Q3 S2 V4 gốc | `data/processed/seminar_feasibility_20261025/inputs/Qwen3-Shard2-V4.zip`; TAR bên trong SHA256 `2dc356fcba9fe2ce5dfc4e3dc9a45286fe5382f574c02d38d7517580e38cd920`. Hàm có sẵn kiểm exact ZIP members/CRC/sidecars và TAR. Không S2 diagnostic/recovery. |
| Ordered TRAIN manifests/authority | `git show 31a04e6f7175cca818c63b4de0153246b3f3ecdb:data/manifests/pa3_full_train_shard{k}.v1.json`, k=0…3 và `configs/diagnostics/hnlo_train_authority.v4.json`; SHA khóa trong authority, không truy cập TEST. |
| MiniCPM official receipt/manifest | `data/processed/m160/verification.json`, `data/processed/m160/verified/pilot_manifest.json`, `data/processed/m160/HANDOFF.md`; ZIP đã có SHA256 `46a41359c3ab2978b9ee4ac010518e49a74141641d9334c29035bdc0c8eac877` theo S8, không rehash/replay raw ZIP tại T0. |
| InternVL official receipt/manifest | `data/processed/official160-20261031/verification-result.json`, `data/processed/p160/work/review-only/history/owner_internvl35_55badcf1d55d44d98b74324c58b552bf/pilot_manifest.json`, handoff cùng official160 directory. ZIP đã có SHA256 `e1f9c50cb162e6d14f0f5ca42927799e8d3595ccf6dab8d72d0ac90840ebbaf6` theo handoff, không re-audit ZIP trong T0. |

Handoff MiniCPM kỹ thuật hiện có 155 SUCCESS/5 INVALID/0 ERROR/0 NOT_ATTEMPTED,
160 HNLO null; InternVL 135 SUCCESS/25 INVALID/0 ERROR/0 NOT_ATTEMPTED,
135 HNLO số. Hai manifest được kiểm cùng SHA256
`f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995`,
cùng 160 unique TRAIN IDs, quota Level01/02/03/04 = 48/24/8/80.
Đây không là source-independent cohort hay final result selection/pooling.

S1 báo thêm thăm dò: InternVL có 2 false-safe/80 hazard và 20 hazard INVALID;
MiniCPM 30/80 false-safe và 0 hazard INVALID. Trong 30 false-safe MiniCPM,
InternVL cảnh báo hazard 22, INVALID 6, cùng Normal 2; InternVL tạo 34 cảnh
báo hazard sai trên Normal MiniCPM trả đúng. Các số này **kế thừa advisory,
không tái tính paired performance/raw tại T0**. Chúng chứng minh vì sao cần
đánh giá false alerts/missingness và utility theo focal; không phải 22 lỗi đã
sửa, không chứng minh phát hiện lỗi Q3 hoặc ích lợi trong budget K.

## 4. Recount Qwen3 V4 gốc và kiểm chéo

T0 đọc đúng ba saved-report/result/manifest members trong bốn TAR có hash
khóa, không đọc raw logits/images. Kiểm lại archive/member SHA, result trong/
ngoài archive, exact authority/unit/config, historical ordered IDs/image hashes,
canonical labels và status. Không dùng metadata audit chứa TEST; GT/domain là
**nhãn tham chiếu trong saved reports**, chưa adjudication mới.

Kết quả toàn V4 planned 3.763: SUCCESS 3.539, TECHNICAL_ERROR 1,
NOT_ATTEMPTED 223. SUCCESS support Level01/02/03/04 = 460/232/8/2.839.
Q3-Normal 2.455, false-safe **35**, gồm Level01 **13**, Level02 **22**,
Level03 **0**. Focal-Normal GT Normal = 2.420. Mọi failure giữ nguyên.

Đếm từng CSV row rồi kiểm độc lập bằng tổng các ô Level01/02/03→Level04 trong
confusion summaries đã lưu ở từng shard; đồng thời kiểm Normal prediction
column và severe cell. Cả hai đường cho 35/2.455/13. Đây là kiểm chéo arithmetic
cùng task, không independent scientific audit. Per-shard archive/sample/ordered
manifest hashes, counts và source pins nằm trong JSON sạch; không vector ID/score.

TRAIN160 metadata join được trình bày trong JSON: hash manifest bắt buộc,
160 unique TRAIN IDs, ID/image hash/level/domain phải khớp V4 saved report và
ordered historical manifest. Trường `qwen_verified` của manifest gốc vẫn rỗng;
T0 không sửa manifest hoặc nâng thành three-model qualification/utility PASS.
Không tính ranker/gain/capture trên TRAIN160 hoặc gọi nó là target.

Join cho Q3 V4 gốc **148 SUCCESS/12 NOT_ATTEMPTED**, **67 predicted Normal,
4 false-safe, 1 severe false-safe** trên đúng160 ID. Phép tính chỉ đếm output
focal cũ để kiểm feasibility; không ghép recovery, không chọn kết quả/series
cho scientific pooling. Với4 sự kiện, độ phân giải capture là25 điểm phần
trăm; không coi đó là đủ support hoặc precision, dù peers có nhiều lỗi hơn.

## 5. Tái lập phép đếm, không chạy mô hình

Python **3.11.9**, Windows, standard library; `python -B`, seed=null vì phép
đếm xác định. Không cài dependency. Dùng helper read-only hiện hữu
`scripts/analyze_source_sensitivity.py` ở BASE; checksum source/helper trong
JSON để phân biệt với release thực thi VLM cũ. Lệnh kiểm tra private chỉ dùng
inputs có quyền, không chạy toàn CLI sensitivity đọc metadata toàn dataset.

Đặt các saved inputs vào bố cục §3 dưới `data/processed/` trong clone/worktree
có BASE, lấy script Python từ fenced block bên dưới thành
`data/processed/t0_20261101/recount.py` (tạo thư mục local nếu cần). Sau đó:

```console
python -B data/processed/t0_20261101/recount.py --input-root data/processed --panel-manifest data/processed/m160/verified/pilot_manifest.json --output data/processed/t0_20261101/saved-report-counts.json
```

Output có sẵn thì từ chối ghi đè. So toàn bộ JSON phép đếm với trường
`saved_report_recount` của JSON sạch; phần projection receipt/advisory và
validation không được trộn vào output recount. Lệnh không tái audit raw,
không tạo ranking hoặc metric protocol mới.

```python
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from collections import Counter
sys.path.insert(0, str(Path.cwd()))
from scripts.analyze_source_sensitivity import checked_bytes, original_s2_zip, verified_archive_members, report_rows
H='31a04e6f7175cca818c63b4de0153246b3f3ecdb'
def hist(p): return subprocess.check_output(['git','show',H+':'+p])
receipt=json.loads(hist('notes/evidence/three_model_20261023/verification_20261023.json'))
locked=receipt['available_export_checks']['inputs_sha256']
scope=json.loads(hist('configs/diagnostics/hnlo_train_authority.v4.json'))['scope']
units={u['shard']:u for u in scope['units'] if u['model']=='qwen3'}
parser=argparse.ArgumentParser()
parser.add_argument('--input-root',required=True)
parser.add_argument('--panel-manifest',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args()
root=Path(args.input_root)
a=root/'seminar_feasibility_20261024/inputs'
b=root/'seminar_feasibility_20261025/inputs/Qwen3-Shard2-V4.zip'
allrows=[]; shard_receipts=[]; image_hashes={}; summary_fs=0; summary_normal=0; summary_severe=0
for k in range(4):
    if k==2:
        payload,result,z=original_s2_zip(b.read_bytes())
    else:
        name=f'qwen3_shard{k}.json'
        result=json.loads(checked_bytes(a/name,locked[name]))
        payload=checked_bytes(a/result['export']['archive'],result['export']['archive_sha256'])
    assert result['unit']==units[k]
    members=verified_archive_members(payload,result['export'],{'evidence/report/samples.csv','evidence/binding.json','evidence/result.json'})
    binding=json.loads(members['evidence/binding.json'])
    assert binding['unit']==units[k] and binding['authority']['scope']==scope
    assert json.loads(members['evidence/result.json'])=={x:y for x,y in result.items() if x!='export'}
    mp=f'data/manifests/pa3_full_train_shard{k}.v1.json'
    manifest=hist(mp)
    assert hashlib.sha256(manifest).hexdigest()==units[k]['inference_sha256']
    samples=json.loads(manifest)['samples']
    assert binding['samples']==samples
    image_hashes.update({r['sample_id']:r['image_sha256'] for r in samples})
    rows=report_rows(members['evidence/report/samples.csv'])
    assert [r['sample_id'] for r in rows]==[r['sample_id'] for r in samples]
    assert len(rows)==units[k]['count']
    assert Counter(r['status'] for r in rows)==Counter(result['coverage']['status_counts'])
    for r in rows:
        assert r['true_level'] in {'Level01','Level02','Level03','Level04'}
        assert r['true_binary_label']==('Normal' if r['true_level']=='Level04' else 'Anomaly')
        assert r['status'] in {'SUCCESS','TECHNICAL_ERROR','NOT_ATTEMPTED'}
        assert r['generated_label'] in ({'Level01','Level02','Level03','Level04'} if r['status']=='SUCCESS' else {''})
    allrows.extend(rows)
    cm=result['metrics']['overall']['generated_on_score_valid_ids']['confusion_matrix']
    summary_fs+=sum(cm[level]['Level04'] for level in ('Level01','Level02','Level03'))
    summary_normal+=sum(cm[level]['Level04'] for level in ('Level01','Level02','Level03','Level04'))
    summary_severe+=cm['Level01']['Level04']
    shard_receipts.append({'shard':k,'archive_sha256':result['export']['archive_sha256'],'samples_sha256':hashlib.sha256(members['evidence/report/samples.csv']).hexdigest(),'manifest_sha256':units[k]['inference_sha256'],'planned':len(rows),'status':dict(Counter(r['status'] for r in rows))})
assert len(allrows)==3763 and len({r['sample_id'] for r in allrows})==3763
success=[r for r in allrows if r['status']=='SUCCESS']
fs=[r for r in success if r['true_level']!='Level04' and r['generated_label']=='Level04']
normal=[r for r in success if r['generated_label']=='Level04']
assert (len(fs),len(normal),sum(r['true_level']=='Level01' for r in fs))==(summary_fs,summary_normal,summary_severe)
summary={'confusion_summary_crosscheck':'PASS', 'schema':'safeshift-t0-saved-report-counts-v1','base':'89d886356c15064b5f1cc2021aa5d614e7e7f53f','history':H,'evidence_level':'HASH_BOUND_SAVED_REPORT_RECOUNT_NOT_RAW_AUDIT','raw_replay':False,'TEST_access':False,'recovery_pooled':False,'planned':len(allrows),'status':dict(Counter(r['status'] for r in allrows)),'success_gt_levels':dict(sorted(Counter(r['true_level'] for r in success).items())),'predicted_normal':len(normal),'false_safe':len(fs),'false_safe_gt_levels':dict(sorted(Counter(r['true_level'] for r in fs).items())),'false_safe_folder_domain':dict(sorted(Counter(r['domain'] for r in fs).items())),'verified_independent_source_count':None,'shards':shard_receipts}
panel_bytes=Path(args.panel_manifest).read_bytes()
assert hashlib.sha256(panel_bytes).hexdigest()=='f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995'
panel=json.loads(panel_bytes)
assert panel['split']=='TRAIN' and len(panel['main'])==160 and len({r['sample_id'] for r in panel['main']})==160
byid={r['sample_id']:r for r in allrows}
selected=[]
for row in panel['main']:
    assert row['split']=='TRAIN'
    saved=byid[row['sample_id']]
    assert row['image_sha256']==image_hashes[row['sample_id']]
    assert (row['level'],row['domain'])==(saved['true_level'],saved['domain'])
    selected.append(saved)
summary['original160_metadata_join']={'manifest_sha256':hashlib.sha256(panel_bytes).hexdigest(),'qwen_verified_entries_in_original_manifest':len(panel['qwen_verified']),'qwen_status_counts':dict(Counter(r['status'] for r in selected)),'qwen_predicted_normal':sum(r['status']=='SUCCESS' and r['generated_label']=='Level04' for r in selected),'qwen_false_safe':sum(r['status']=='SUCCESS' and r['generated_label']=='Level04' and r['true_level']!='Level04' for r in selected),'qwen_severe_false_safe':sum(r['status']=='SUCCESS' and r['generated_label']=='Level04' and r['true_level']=='Level01' for r in selected),'image_hash_level_domain_matches':160,'classification_qualification':'NOT_ESTABLISHED_BY_METADATA_JOIN','three_model_utility_evaluated':False}
out=Path(args.output)
with out.open('x',encoding='utf8') as f: json.dump(summary,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'false_safe':summary['false_safe'],'crosscheck':summary['confusion_summary_crosscheck'],'original160_metadata_join':summary['original160_metadata_join']},ensure_ascii=False,indent=2))
```

## 6. Điều chưa xác minh và điều kiện khoa học

- Chưa có source registry đủ coverage, V/T độc lập, custodian/GT authority hoặc
  precision plan; không tạo số independent sources. `null` nghĩa chưa biết,
  không phải 0 nguồn tồn tại.
- TRAIN/H đã dùng phát triển; source split/CV hồi cứu không xóa exposure.
  S1/S2 và dữ liệu 160 đều chưa là benchmark xác nhận.
- HNLO Q3 saved-score không là raw audit mới hay error probability; MiniCPM
  numeric HNLO không có. Q3 hazard AUROC toàn SUCCESS không là error AP/capture.
- TRAIN160 paired metadata không là proof peer utility hoặc license/grant cho
  protocol mới. Technical receipts và audit #157 không approve O1–O5.
- Không tái tính toàn bảng classification metrics của S1 hoặc đọc lại raw
  artifacts để tự nhận independent audit. Thực nghiệm E1–E5, target, CI,
  cỡ mẫu/power, GPU/native weights, UI/user study đều NOT_RUN trong T0.

## 7. Kiểm tra bàn giao

Các kết quả sau chạy tại chính worktree T0; source/output hashes trong JSON,
HEAD cuối ở PR để tránh hash tự tham chiếu.

- **PASS:** recount bốn Q3 V4 saved reports đúng archive/member/authority/ordered
  manifest, 3.763 planned/status đầy đủ; CSV counts khớp saved confusion summaries.
- **PASS:** metadata160 join: manifest hash, 160 unique TRAIN IDs và image
  hash/GT/domain; 148 SUCCESS/12 NOT_ATTEMPTED/67 Normal/4 false-safe/1 severe.
- **PASS:** 76 local Markdown links tồn tại; UTF-8 không BOM/replacement,
  fences/tables, không conflict markers/đường dẫn cá nhân/token patterns trong
  bốn file bàn giao. JSON parse, aggregate identities/denominators/source pins,
  embedded recount source/compile và protected files so BASE khớp.
- `git diff --check` PASS; staged diff/phạm vi bốn file được kiểm trước commit.
  Script embedded hash chuẩn UTF-8/LF với một newline cuối; JSON giữ riêng
  SHA256 bytes Windows của helper đã chạy. Lỗi validator local ban đầu nhận
  nhầm URL là drive path và khác newline đã sửa ở checker, không thay phép đếm.
- **NOT_RUN:** repository full unit suite/native weight tests/GPU/CI, vì chỉ
  thay tài liệu/projection, không đổi runtime/code thuật toán. E1–E5 thực nghiệm,
  power/CI, raw replay, TEST, target và independent audit T0 không chạy.
- Đây là self-verification của Codex, chưa là ChatGPT review, CI PASS,
  Antigravity audit hoặc scientific approval. Final HEAD/BASE/files ở Draft PR.

Giữ lịch sử lỗi helper local: lượt đầu định vị worktree inputs sai mức thư mục,
FileNotFoundError trước phép đếm; bản bổ sung join ban đầu giả định split
`train` trong khi manifest pin dùng `TRAIN`, assertion dừng trước ghi output.
Sửa helper kiểm tra theo schema thực, giữ files/lỗi cũ local ignored, không sửa
input/schema/manifest hoặc runtime VLM. Kiểm đếm v1/v2 và bản cuối giữ số
35/2.455/13; chỉ bản cuối có join metadata160. Không gọi các lượt lỗi là PASS.

## 8. Ghi công hướng dẫn phương pháp

Đã dùng skill `experimental-design` v1.5 để kiểm đơn vị nguồn, paired controls,
blocking và tránh pseudoreplication; không chạy scripts DOE hoặc statistical
power. Theo yêu cầu ghi công của skill: Kassis, T., Agarwal, V., He, Y., Patel,
D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural
Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
Metadata arXiv kiểm ngày01/11/2026: v2, revised02/09/2026; DOI không suffix.
Đây là nguồn quy trình, không là bằng chứng hiệu quả SafeShift hay peer review.
