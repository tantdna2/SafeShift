# V4-4: successful Kaggle references and real Input rehearsal

Owner [incident6922592580](https://github.com/tantdna2/SafeShift/pull/199#issuecomment-6922592580)
and [mandatory comparison6922725439](https://github.com/tantdna2/SafeShift/pull/199#issuecomment-6922725439).
New coding task/branch from merged PR199 `92e7af41b3102cac16609908c88688f4049b4cc1`;
stop at one new Draft PR. Observations started 16/11 and completed 17/11/2026,
Asia/Bangkok. No new Kaggle job, GPU, model load/inference or TEST body access.

## Actual successful source, rather than current notebook summaries

The official pinned SDK retrieved **version1 notebook source and metadata** for
all three references. Their embedded payloads were statically decoded, hashed
and opened; nothing from those payloads was executed. Current repository copies
of the Candidate160 notebooks have subsequently been rebuilt and are not the
successful payloads. Historical reports/receipts remain authoritative only for
their own runs, not for this repair's GPU readiness.

| Route | Actual version1 source and Input use | Observed root-relative image path / first bytes | Reused code boundary |
| --- | --- | --- | --- |
| MiniCPM one image, `nguynanhtn/safeshift-minicpm4-fp32-trial-20261031/1` | Runtime `0fa13ee610244a56d4d999cc5d73841267a28306`; embedded53-file SHA `ae94d0033e8215fb3cf1e192c0ef0b5c0e5d76cc8eb904558dc4d9a26186ab7b`. Historical attached slugs: pilot Input and prepare-minicpm4 Output; metadata alone does not authenticate attachment versions. Current explicit pilot Dataset `/1` and checkpoint Output `/1` were separately inspected. | Under pilot mount: `safeshift-pilot-input/pilot_manifest.json`, `safeshift-pilot-input/images/000000.jpg`. First Candidate160 image:543131 bytes, SHA `761f0b03f442a5f3648bd544b0035117f04d7f38bfeb726573b4ecaf92160d14`. Real original local bundle bytes match the manifest and current provider file size. | `train_runtime.launch_owner` technical action; `train_inputs.discover/checkpoint`; `train_contract.manifest`; native PIL/RGB/backend/loading; sealed ZIP and raw custody. |
| MiniCPM three-image production QA, `nguynanhtn/safeshift-minicpm4-production-qa-20261031/1` | Runtime `b5448d031b287bc7adabd58ec36d98e671449b9d`; embedded54-file SHA `09d94fd27a6a5260526c981a55854e8217536e0499824400ea9df5d213fb2d08`. Same pilot/checkpoint slugs. | Same pilot roots and first-image bytes; `train_route.selection` fixes ordinals0/15/111 of **Candidate160**. These are not Full-TRAIN ordinals. | Same loader/FP16/eager and FP32 resampler; `train_route.receipt/verify_portable_recovery` verifies3 calls, then zero-load/zero-call sealed-history resume. |
| InternVL Full-TRAIN route, version1 `nguynanhtn/safeshift-train3763-ivl35-train3763-4` | Retrieved actual90-file payload SHA `e772f2dac6f10a1e9b07208227d4bc8eb8008a3708a1a0287fa5b5a6c9a994b8`; opened actual `internvl3763_campaign.admit_inputs` and worker. The separately inspected later approved Operator source is `4407dc939e045d115f4147e2d1d49605ec8b2f7a`. The campaign continued through later attempts; this particular version is the successful first-image checkpoint, not a claim that Attempt4 alone completed3763. | Pilot mount: nested Master; original Dataset mount: `InspecSafe-V1-Kaggle/train/DATA_PATH/train/Annotations/.../<locked-id>.jpg`. First Full-TRAIN image:546411 bytes, SHA `a13ac091662772ec644b5382904dcdcd1606c296d145f41b7de4d513b8261d86`. | `discover` already accepts the nested Master. `admit_inputs -> verification173.verify_train` checks original3763 order/SHA. Shared original mounts, offline Python conventions, serial journal and immutable archive conventions apply; InternVL grammar/model/configuration/throughput do not transfer. |
| Failed MiniCPM V4-4, `nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-4/1` | Embedded80-file SHA `4b4f6bcccaaaa1793da3240bf9f4640e7a0796c9d1b615db0a627d4965a356c9`, current five pinned Inputs. Provider COMPLETE, kernel145432984, but supervisor BLOCKED at admit. | `original_inputs.admit` incorrectly appended `master_manifest.json` directly to the outer pilot mount. TRAIN inner root was separately verified and is correct. Original full-cohort first image is the InternVL Full-TRAIN image above, not the Candidate160 first image. | Keep native/backend/checkpoint/parser/raw unchanged. Repair bounded Master discovery and CPU image admission; reconcile supervisor-only terminal failure and require fresh source-bound release. |

Historical evidence opened:
[one-image report](MINICPM4_FP32_ATTENTION_TECHNICAL_20261031.md),
[receipt index](evidence/minicpm_resampler_fp32_20261031/index.json),
[three-image report](CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md),
[QA receipt](evidence/candidate160_production_20261031/kaggle-minicpm4.json),
[campaign](../TRAIN3763_CAMPAIGN.md), [collection](../TRAIN3763_MANUAL_RECONCILIATION.md),
[Operator contract](../INTERNVL3763_ANTIGRAVITY.md).

Actual downloaded notebook SHA256, respectively: one-image
`864d365cd4596200e72d91324aeab92a623697ef69989b63f7fa26709c231a7c`,
three-image `ccffabaec503ad745609d49580da90c39d4e9754d07098469947c0095b0b6d26`,
InternVL `cecd5e84dc98704cd97aa7dfda277b67f1b2ac1d90d53383effb92410f0928c7`.
Provider serialization/metadata differs from historical staged-notebook hashes;
the extracted MiniCPM payload hashes exactly match their successful receipts.
Private sources, metadata and per-file hash inventory stay in ignored
`data/processed/minicpm-v44-repair/reference-source/` and `reference-source-proof.json`.

## Verified current five Input layouts

| Pinned Input | Relative content under the approved outer mount | Read-only evidence |
| --- | --- | --- |
| `nguynanhtn/safeshift-pilot-input/1` | `safeshift-pilot-input/master_manifest.json` | Complete166-file listing; downloaded2488945-byte Master SHA `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`, verified before parse. |
| `nguynanhtn/inspecsafe-v1-kaggle/1` | `InspecSafe-V1-Kaggle/train/DATA_PATH` plus original `train/Annotations/...` locators | Exhausted121 pages/24057 metadata entries; all3763 locked TRAIN JPEG-named paths exist with matching sizes. TEST filenames occurred in provider metadata; no TEST file body/annotation was downloaded or opened. |
| `nguynanhtn/safeshift-prepare-minicpm4/1` | Flat `candidate_checkpoint_minicpm4.json`; `source/6f69a8235885be89608f3a71ffd40695b379e1e7/`; `weights/` | Exact19-file inventory matches public source/weight allowlists. Downloaded marker SHA `6ff382a6d1951d8224221c7ab1b4cb77830efb7abd5c1a72166482ed3a133040`; index SHA `803b4c6605fd33df8ba4386c787f914e75d4d382f937e4e2c3f640d47e1f6d5c`. No weights load or current full-weight rehash; existing same-version historical verification is not a new GPU qualification. |
| `nguynanhtn/safeshift-cpython3119-20240726/1` | Flat `safeshift_train3763_python.json` and `safeshift-cpython3119-base64.bin` | Both current files downloaded; exact manifest and39617560-byte transport SHA `871cccab019cb6ef7417af6f3287233f3ba25e904fc007c429fdcb5e3a67b9f5`; bounded decode restores29713170-byte locked archive SHA `f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d`. Windows does not execute this Linux interpreter. |
| V4-4 capsule `nguynanhtn/safeshift-minicpm-capsule-mcpm4-restart-v1-4/1` | Flat execution JSON and signed-ticket JSON | Versioned exact inventory and independently downloaded signed ticket match. This is historical custody, never authority to reuse that capsule/ticket with new source. |

The production outer roots remain `datasets/nguynanhtn/<slug>` and
`notebooks/nguynanhtn/safeshift-prepare-minicpm4`. Master resolution allows only
the verified nested prefix and the existing flat exported-bundle variant;
duplicates, aliases, unknown depth, wrong types or a missing approved path block.
TRAIN has one observed allowlisted root, not a speculative recursive fallback.

## Real-file rehearsal and limits

Master-derived ordered projection SHA:
`524980d374daf6be3bedc743b6dc5ddc423dfe11c833609253cc5b2ce38586dc`.
All3763 original local TRAIN files were rehashed against the downloaded Kaggle
Master and provider names/sizes, copied to a separate Kaggle-shaped local tree,
then passed the actual repaired `admit`, `verify_bytes` and `verify_images`.
The admission/verifier copied zero bytes and rewrote no images; construction of
the separate rehearsal copy is explicitly recorded. Total image bytes2420332674.

73 JPEG-named files were independently downloaded from current Kaggle version1
and SHA-verified. The larger download attempt stopped on transport failures;
partial downloads/logs remain. **This is not3763 newly downloaded remote files.**
The other3690 rehearsal files are original authentic local bytes with the same
frozen hashes, corroborated by the complete current provider listing. No
synthetic master/projector/image fixture substitutes for this check.

CPU decode found **3724 JPEG +39 PNG**, all single-frame and valid native PIL/RGB
inputs. The old new-route `image.format == "JPEG"` preflight would have failed at
Full-TRAIN ordinal13 even after the Master fix. It is corrected to the unchanged
successful native loader's still-image decode/RGB behavior; original `.jpg`
locators, SHA256, images and model preprocessing are preserved. There is no
format conversion on disk, parser relaxation, relabeling or science change.

Reproduce on authentic read-only copies, from repository root:

```powershell
python -B -m scripts.check_minicpm_original_inputs --inputs data/processed/minicpm-v44-repair/mounted --spec data/processed/minicpm-v4-package-4/dataset/safeshift_minicpm_fulltrain_execution.json --output data/processed/minicpm-v44-repair/new-rehearsal.json
```

Receipt: [public evidence index](evidence/minicpm_v44_repair_20261117/index.json).
Real Input layout/bytes and CPU decode are verified within the stated custody
limits. Final-source GPU/model fit is NOT_RUN, not implied by this PASS.
See [source-repair handoff](../MINICPM_V44_REPAIR.md) for the release gates.
