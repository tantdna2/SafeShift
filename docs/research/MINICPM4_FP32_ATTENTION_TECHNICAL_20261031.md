# MiniCPM resampler attention FP32 — bounded technical trial

Status: TECHNICAL_SMOKE_PASS / READY FOR REVIEW, keep Draft PR156. Owner authorized this narrow engineering
exception after the prior HOLD; [decision](DECISIONS.md#dec-20261031-minicpm-resampler-fp32-technical-exception)
is distinct from scientific baseline approval, result selection or merge.
Same session, branch and Draft PR156; no official160-image experiment or TEST.

The original Kaggle FP16 failure, two native diagnostics and prior source/
notebook/ZIP hashes remain unchanged in the prior evidence index. The verified
failure is score baddbmm overflow followed by softmax NaN with finite Q/K/V and
valid masks. The new implementation is `minicpm4-resampler-attention-fp32-v1`.

The effective adapter verifies the complete original resampler.py hash, reads
the actual native method, requires exactly one occurrence of each of four
declared expressions, and derives an instance-only method. Original source
files/classes/cache/checkpoint locks are not changed. Projections, normalization,
query scaling, eager mode, FP16 weights and output projection remain native.
Only masked/unmasked scores, softmax and value product compute in FP32; the
value product casts back to the native dtype before out_proj. Unsupported
training/dropout/need_weights=False paths fail closed. No SDPA/flash fallback.

The descriptor contains original file hash, adapter file hash, expression map,
dtype boundaries and an implementation digest. Native/derived method hashes
are recorded at load. A distinct effective configuration/hash is bound through
execution, raw custody and runtime. Each engineering invocation has a new run/
series and output tree; no history import/resume/scientific metrics/pooling.
No production authority is granted for this effective configuration. Original
configuration hashes remain available for legacy history, without relabeling
historical results as if they used new arithmetic.

The new notebook `SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb`
hard-codes the one-image technical route and has no full-run action. It uses
the production supervisor/CLI/child/software/checkpoint/bundle/native loader,
the unchanged first TRAIN image and original C1/parser/HNLO. Caps:1 load,
1 image/1 native call,3600 seconds including setup. GPU0 on T4x2 only.

CPU tests compare original native FP16 overflow with finite effective results,
an independent FP32 reference, mask/error paths, return dtype, unchanged weight
bytes/parameter identities/class/source, distinct config and raw recovery
rejection across implementations. Real production --check-only must additionally
load/install the native meta model in the exact3.11.9/cu124 stack before GPU.

Only an actual final-source Kaggle run with loaded weights, measured CUDA,
finite raw inference, parser/defined HNLO handling, effective counters, cleanup,
ZIP/member checksums/sidecar can establish technical smoke PASS. INVALID and
HNLO unavailable outcomes remain visible; numerical HNLO/quality/full160 are
not implied by one-image finite inference. Any failures remain in their own
immutable output directories and receipts. No alternate prompt/data/precision
outside the authorized boundary is used to obtain a favorable response.

## Observed verification

- Exact Linux Git export `0bb1b71f58818ed1e5c85aafa942f63ee9c72279`:365 tests,
  **326 PASS/39 SKIP/0 failures/errors**. Opt-in torch/native tests ran separately:
  **8/8 PASS**, including the independent scalar oracle added after the export.
- Windows:4/4 existing notebook tests PASS and effective notebook/isolated
  control tests PASS. Actual production effective `--check-only` subprocess
  passed in3.11.9/cu124, with no worker/native-setup/source-verification mocks:
  all160 real authorized images verified,8 processor sizes, native meta loader
  and effective installation on4,059,533,040 FP16 parameters.
- Initial local invocation with a7-character SHA was correctly blocked before
  child/model load. A WSL notebook test initially lacked explicit Git worktree
  environment; corrected environment then passed. These records are retained;
  no failing effective GPU trial was concealed or overwritten.
- Real private Kaggle kernel
  `nguynanhtn/safeshift-minicpm4-fp32-trial-20261031`,version1: COMPLETE and
  **TECHNICAL_SMOKE_PASS**. Exact notebook cell code, privacy, container, original
  dataset and checkpoint Output were pulled back and compared before execution
  results were accepted. T4x2, GPU0 inference only, same image0 at2336x1752.
- One real model load/one native call. All model parameters remain FP16 and
  their parameter objects/storage/dtypes/devices are preserved by installation.
  Effective score/softmax/value checks each ran once, with finite results and
  FP16 return.11/11 full-vocabulary raw-logit steps are finite; raw_nonfinite=false.
  Peak GPU0 allocated9,736,494,592 bytes, reserved9,888,071,680 bytes.
- Parser status **SUCCESS**. The unchanged HNLO logic returns
  **RAW_LOGITS_AVAILABLE_BUT_UNALIGNED**, reason
  ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS; numeric HNLO is not
  established. This is not a scientific/parser/HNLO qualification or an accuracy
  claim. No alternate image, prompt or parser was tried to obtain a score.
- Raw/native tokens/logit steps, CPU tokenizer replay, configuration/implementation
  binding, all73 member checksums, sidecar, cleanup and final receipt were verified
  independently after download. The strict native/derived method hashes match
  between CPU meta admission and actual loaded GPU runtime.

Runtime commit `0fa13ee610244a56d4d999cc5d73841267a28306`;
embedded source SHA256 `ae94d0033e8215fb3cf1e192c0ef0b5c0e5d76cc8eb904558dc4d9a26186ab7b`.
Effective descriptor SHA256 `2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`;
effective configuration SHA256 `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`.
Notebook SHA256 `531f0ccbbd23000706c8491ba8f6a3dcf70ddf14d5a5ef33ccd1fb23b0e244ef`.
ZIP SHA256 `0c1fe3b00a56314cd3688465f59f0ccb8dce09761c349e1724ec0d242c175337`.
[Receipt index](evidence/minicpm_resampler_fp32_20261031/index.json) links sanitized
configuration/native/CPU/Kaggle/preservation records. Private outputs remain under
ignored data/processed/minicpm-fp32-20261031. Five earlier private ZIPs and all prior
committed receipt hashes were reverified unchanged; no history or old lock edited.

## Limits and next step

This verifies only the new one-image effective technical notebook. Model/checkpoint/
revision,160-image manifest/order, original weights dtype, C1, eager, parser/HNLO
and scientific decisions are unchanged. No full160/TEST/GT analysis, scientific
baseline approval, selection or pooled result was produced. Finite behavior on
this image does not establish rare inputs, sustained memory/time or numeric HNLO.

The shared supervisor source changed, so four baseline notebooks were rebuilt
to keep their payload/source bindings consistent. Their previous Kaggle evidence
remains historical and does not qualify the rebuilt payloads. No new baseline
FP16 failure was run. Only the effective notebook/route has new live evidence.
Keep Draft for ChatGPT exact-HEAD GitHub review, then an independent Antigravity
audit decision. No merge or official Owner full experiment is authorized here.
