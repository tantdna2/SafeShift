# InternVL3.5 / MiniCPM-V-4 ? Owner Save & Run All

30/10/2026, Asia/Bangkok. Base sau **PR #153 MERGED**:
`fc1e454212455685e1775601ebfd6aab9535c932`, ?? ki?m GitHub v? remote main.
Thay ??i n?y c?n ChatGPT ki?m GitHub v? audit ??c l?p tr??c merge.
Task tri?n khai ch? CPU t?ng h?p; GPU/real weights/behavior v?n UNVERIFIED.

- [InternVL notebook](../notebooks/SafeShift_CANDIDATE160_internvl35.ipynb)
- [MiniCPM notebook](../notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb)
- [Quy?t ??nh Owner v? thay ??i ch?nh s?ch d?ng](research/CANDIDATE160_OWNER_DECISION_20261030.md)
- [CPU acceptance v? gi?i h?n](research/CANDIDATE160_OWNER_CPU_20261030.md)

Owner ?? y?u c?u b? th? t?c xin ph?p l?p l?i cho l??t thu?c quy?n Owner.
Lu?ng notebook m?i d?ng **Save & Run All l? k?ch ho?t tr?c ti?p**. Kh?ng y?u c?u
file grant, reservation, approval refs ho?c CONTINUE. Execution record l? nh?t k?
m?y g?n v?i quy?t ??nh Owner trong chat, kh?ng v?n b?n k? thay Research Lead.
Lu?ng grant/batch #153 v?n ???c gi? cho t??ng th?ch, kh?ng ph?i UI notebook m?i.

## Thao t?c tr?n Kaggle

Sau review/audit v? merge, Owner ch?y ri?ng t?ng notebook ??ng m?t l?n:

1. Fresh Kaggle notebook, **T4 ?2**, Internet ON cho pinned software.
   Kh?ng ch?y interactive r?i Save & Run All l?n n?a; ch? m?t saved job/model.
2. Attach bundle Owner ?? upload: `pilot_manifest.json` v?
   `images/000000.jpg` ? `images/000159.jpg`.
3. Attach checkpoint Owner ?? upload: `candidate_checkpoint_<key>.json`,
   `source/<revision>/` v? `weights/`. Key l? `internvl35` ho?c `minicpm4`.
   Marker ph?i ??ng `{"schema":"safeshift-candidate160-checkpoint-v1","model":...}`;
   `model` l? dict t? `train_contract.model(key)` g?m id/revision/transformers/
   attention/remote_code. Source ph?i ??ng 13/15 files allowlist; weights ??ng
   index + hai shards size/SHA c?a lock #151. Kh?ng links/extra files ho?c downloader.
   Discovery nh?n direct mounts v? `datasets/<owner>/<slug>`; t?n file duy nh?t.
4. **Save Version ? Save & Run All m?t l?n.** Kh?ng ch?nh cell, model, revision,
   SHA, Python ho?c precision ?? v??t preflight. Kh?ng c?n file CONTINUE.
5. Download private ZIP v? `.sha256.json` ???c in, k? c? failure. Kh?ng publish
   raw, manifest, GT ho?c checkpoint; kh?ng ch?y l?i khi l?i hay m?t archive.

Ch? c?n hai nh?m Inputs: bundle v? checkpoint. Kh?ng c?n authority Dataset.
N?u Input layout/bytes kh?ng kh?p, notebook xu?t BLOCKED evidence tr??c model call.
Owner kh?ng ph?i g? run ID, attempt ID, ng??ng, driver allowlist hay th?i h?n.

## Ph?m vi b?t bi?n

| Th?nh ph?n | Kh?a |
| --- | --- |
| InternVL | `OpenGVLab/InternVL3_5-4B-HF` @ `6bd4487402110ef9889ba50eb7aefeb302526fed`, Transformers4.55.4 |
| MiniCPM | `openbmb/MiniCPM-V-4` @ `6f69a8235885be89608f3a71ffd40695b379e1e7`, Transformers4.51.3 |
| Manifest SHA256 | `f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995` |
| Inventory SHA256 | `0a8a84e726e690622de311326680ecbbc4a04fa04a0a45ff14ff96412caae427` |
| C1 SHA256 | `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3` |
| Cohort | Exact160 TRAIN/th? t? c?; 80 L04/48 L01/24 L02/8 L03; kh?ng ch?n l?i/supplement/TEST |
| Execution | M?t load, batch1, FP16/eager/cuda:0, ?160 native calls/model, kh?ng retry/resume/overwrite |

Gi? adapter/native generation/checkpoint/public locks #151, strict parser/C1/HNLO
v? s?u notebook pilot c?. Hai configuration hashes v?n t?ch bi?t:
`legacy_transport_config_sha256` l? snapshot transport l?ch s?;
`candidate_execution_config_sha256` l? full config v2/effective candidate.
`raw.identity.config_sha256` v?n alias transport. Full config v? execution binding
???c ki?m tr??c parser/recovery; kh?ng ho?n ??i hash ho?c m? t? Phi th?nh candidate.

Quy?t ??nh ch? ?p d?ng m?t l??t/model trong campaign Owner n?y, bundle TRAIN v?
checkpoint Owner ?? upload. Kh?ng c?p quy?n b?n th? ba, TEST, annotation m?i,
FULL TRAIN, model/ngu?n kh?c ho?c khoa h?c/roster m?i. C?n quy?n ??c l?p th?c c?
cho t?i nguy?n ngo?i quy?n Owner; notebook kh?ng ch?ng th?c quy?n ph?p l? c?a upload.

## K?ch ho?t, nh?t k? v? ch?ng tr?ng

`launch_owner(..., owner_start=True)` ???c g?i t? cell shipped. API kh?ng c?
activation r? r?ng s? t? ch?i. T? t?o execution schema ri?ng, UUID run/attempt,
source/ref/config/manifest binding, th?i gian t?o/h?n v? slot c? ??nh theo
campaign/model/revision/cohort. Kh?ng t?o grant, G0/T0/O3, ch? k?, external ledger
ref ho?c Lead approval gi?. Ph?m vi khoa h?c O1?O8/T0 kh?c v?n gi? tr?ng th?i c?.

Tr??c ??c manifest/checkpoint, ghi marker ??c quy?n O_EXCL+fsync v?o
`data/processed/candidate160/attempts/owner_slot_<slot_sha256>.json`.
UUID m?i ho?c source/ref kh?c kh?ng ??i slot. Marker gi? nguy?n c? khi preflight
BLOCKED; kh?ng release/resume/retry. Tr??c worker ghi consumed marker, r?i worker
ki?m consumption; l?i create/fsync kh?ng ch?c ch?n ? UNKNOWN_DO_NOT_RETRY.
Terminal log t? t?o, kh?ng c?n Owner c?p nh?t ledger quy?n th? c?ng.

C?ng output root ch?n duplicate v? concurrent launch b?ng exclusive create.
N?u attach saved Outputs c?, discovery ki?m marker ? mount root ho?c
`data/processed/candidate160/attempts/` (direct ho?c datasets/owner/slug), k? c?
marker c?n RESERVED/kh?ng ??c ???c. Kh?ng qu?t c?y ?nh/weights.
**Gi?i h?n:** filesystem ephemeral kh?ng ph?i distributed ledger. Session m?i
kh?ng attach l?ch s?, hai VM ??ng th?i ho?c layout l?ch s? kh?c kh?ng c? b?ng
ch?ng to?n c?c ?? ch?n. Owner ch? kh?i t?o m?t saved job/model; kh?ng t?o session
thay th? sau l?i/m?t VM, kh?ng x?a marker. Kh?ng tuy?n b? global exactly-once.

## C?c c?ng k? thu?t v?n b?t bu?c

SHA256 embedded runtime/Git ref, C1, hai config hashes, public source, checkpoint
index/shards, manifest/membership/order v? ?nh ??u ph?i kh?p. Decode/RGB160 ?nh
tr??c consumption; hash l?i ngay tr??c native call. Kh?ng t?i weights/Python.

Kernel ch? stdlib; worker CPython3.11.9 Linux x86_64 ri?ng, venv/pip bootstrap
hash-locked; Torch2.6.0+cu124/vision0.21.0+cu124, CUDA12.4, exact pins/no extra
libraries, pip check/freeze/native CPU ABI. Thi?u ??ng interpreter ? BLOCKED.
Hai physical T4, GPU0?14GiB free tr??c load, GPU1 kh?ng pooled/sharded; isolated
child ch? th?y GPU0 compute7.5. Child CUDA FP16 probe tr??c consumption v? ki?m
l?i trong actual worker. Per-image memory/headroom receipts gi? nguy?n.

C?c thay ??i engineering ???c c?ng khai ?? review: thay driver allowlist ch?a
???c quy?t ??nh b?ng CUDA12 Linux compatibility floor525.60.13 + measured child
probe; kh?ng kh?ng ??nh m?i driver tr?n floor ??u ch?y model. Admission disk c?
28GiB scratch +4GiB output/32GiB n?u chung filesystem gi? nguy?n. Live minima:
RAM/cgroup4GiB, scratch1GiB, output1GiB, GPU0 free256MiB sau load/tr??c m?i call.
??y l? reserve k? thu?t ?? xu?t c?a implementation, kh?ng scientific thresholds
ho?c b?o ??m peak fit. H?t12 gi? t? b?t ??u supervisor/setup c?ng d?ng; kh?ng gia h?n.

## Ch?nh s?ch d?ng thay ??i ? c?n reviewer ??nh gi? tr??c merge

Lu?ng Owner kh?ng d?ng c?c ng??ng behavior/support ch?a ???c Owner quy?t ??nh.
Kh?ng ?i?n ch?ng b?ng s? permissive ?? gi? th?nh policy ?? duy?t. M?i call v?n
l?u INVALID, raw sequence repetition, label counts v? conditional valid GT
Normal/hazard counters theo code c?; k?t qu?/custody ???c replay t?ng call v?
??i so?t to?n b? cu?i l??t. Ghi technical decision ri?ng; kh?ng gi? Lead CONTINUE.

D?ng ngay khi l?i k? thu?t/load/OOM/decode/raw/request/token/config/replay/custody,
NaN/Inf, resource ho?c deadline. INVALID/repetition/dominance/false-safe/false-alarm
**ch? quan s?t**, kh?ng t? d?ng theo scientific threshold ho?c thi?u support s?m.
V? v?y behavior k?m c? th? ti?u ??160 calls; kh?ng coi COMPLETED l? quality PASS.
??y l? thay ??i ch?nh s?ch so v?i #153, ch?a ph?i scientific protocol approval.
Full result review/qualification v? HNLO evidence v?n ri?ng; kh?ng c?u parser/score.

## Archive v? t?i l?p CPU

Archive g?m owner execution/slot/consumption log, source/config/dependency receipts,
manifest,160 accounting rows (SUCCESS+INVALID+TECHNICAL_ERROR+NOT_ATTEMPTED=160),
per-call request/native IDs/raw/logits tr??c parser, tokenizer, checkpoints,
technical decisions, behavior observations, summary/recovery/member checksums.
Kh?ng ?nh/weights. Ki?m ZIP CRC/exact member hashes b?ng
`safeshift.pilot.artifacts.verify_archive`; SHA outer ph?i kh?p sidecar.
Import v?o directory m?i v? `train_run.recover` ??i so?t v?i manifest/execution.
Hard kill/disk failure/VM loss c? th? ch? c?n partial evidence, kh?ng h?a ZIP ??y ??.

```console
python -B -m scripts.build_candidate160_notebooks --runtime-ref <metadata.runtime_ref>
python -B -m unittest discover -s tests -v
python -B -m scripts.rehearse_candidate160 --model internvl35 --snapshot <public-source> --index <public-index> --output data/processed/owner160/internvl-new
python -B -m scripts.rehearse_candidate160 --model minicpm4 --snapshot <public-source> --index <public-index> --output data/processed/owner160/minicpm-new
```

Native CPU tests ch? d?ng stack pinned/cache public ?? c?, empty/meta model,
160 ?nh t?ng h?p v? scripted logits; network/CUDA/real forward/weights b? ch?n.
Kh?ng nh?n synthetic behavior l? ch?t l??ng model th?t. Runbook #153 v? c?c
worksheets c? l? [snapshot l?ch s?](https://github.com/tantdna2/SafeShift/blob/fc1e454212455685e1775601ebfd6aab9535c932/docs/CANDIDATE160_KAGGLE.md),
kh?ng th? t?c b? sung cho hai notebook Owner n?y.
