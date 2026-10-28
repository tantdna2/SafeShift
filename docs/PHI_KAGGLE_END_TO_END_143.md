# Phi Kaggle end-to-end — Issue #143, 29/10/2026

BASE: `f8ba79cf17fb12a9745c555a692cbb42f32be45d` (PR #142 merge), verified
against origin/main and [Issue #143](https://github.com/tantdna2/SafeShift/issues/143).
Branch: `fix/phi-kaggle-end-to-end-143`. One Draft PR; no grant a6, Kaggle API,
GPU, checkpoint download, actual model forward/inference, dataset read or merge.
This is implementation acceptance by Codex; independent audit remains pending.

Runtime/notebook source SHA-256:
`df1a36ac670e28f511011746265bf5ff19819360744fc9e5e89f08535addd071`.
The six notebooks are builder-generated with identical embedded source, hashes,
metadata and empty outputs. Git HEAD and changed-file inventory accompany the PR
handoff; a document cannot contain its own final commit SHA.

## Incident evidence and root cause

The [Owner's a5 incident](https://github.com/tantdna2/SafeShift/pull/142#issuecomment-6476943083)
reports ZIP SHA `b7041c9fe174d06d34d000aee276824bc2cfb9d92698e3cdc78dcdb74a30192f`,
25 member hashes/CRC checked by ChatGPT, two shards loaded, zero images attempted,
`attempt_consumed=true`. This task read the incident; it did not independently
re-open the private ZIP. The published record does not identify the failing config.
Historical a1/a2/a4/a5 remain consumed; do not restart or reuse them. a3 includes
pre-consumption failures. No historical result or grant is rewritten.

The pinned CPU integration reproduces both failures with original hash-verified
remote source and Transformers 4.43.3 `from_pretrained`, no loader replacement:

| Case | Before repair | After repair |
| --- | --- | --- |
| a4 | `from_dict(..., attn_implementation="eager")` still reads checkpoint private FA2 field; real loader raises ImportError for flash_attn. | Explicit post-deserialization Phi config remains eager. |
| a5 | AutoModel re-executes `modeling_phi3_v.py`; it replaces the scoped CLIP config constant. Phi root/decoder remain eager; `model.model.vision_embed_tokens.img_processor.config` becomes **sdpa**, with CLIPSdpaAttention. Strict guard rejects it. | Resolve the reviewed class once; call that class's real `from_pretrained` directly within the CLIP eager scope. All 32 Phi3Attention and 24 CLIPAttention layers/configs pass. |

The decisive upstream code is [dynamic_module_utils.py, 4.43.3 L205–213](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/dynamic_module_utils.py#L205)
(module execution on each lookup), [Auto factory L548–561](https://github.com/huggingface/transformers/blob/v4.43.3/src/transformers/models/auto/auto_factory.py#L548),
and [pinned Phi modeling L139–149](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/modeling_phi3_v.py#L139).
This is a genuine non-eager CLIP selection in the loader reproduction, not a reason
to loosen `require_eager`. We do not claim that SDPA forward executed in a5.

`load_phi` is shared by CPU admission and NativeBackend. Auto-only
`code_revision`/`trust_remote_code` stop at reviewed class resolution; they are
not forwarded to Phi's constructor. The revision remains checked before import.
No checkpoint/remote bytes, attention forward functions or library capabilities
are modified. Guards still require explicit AND effective eager, cached Phi mode,
exact attention classes, full layer coverage and absence of extra FA/SDPA modules.

## What the CPU acceptance actually exercises

The real-loader fixture is an **empty** safetensors file with format metadata,
full original architecture on meta, and no trained/random weight data. The CPU
gate uses `from_pretrained(None, state_dict={})` on the same reviewed class.
All parameters/buffers remain meta. Actual Phi/CLIP forward and CUDA are forbidden;
GPU0 device dispatch, real shard materialization and inference remain UNVERIFIED.

Processor tests use all original public files/hash locks, native tokenizer/chat
template and processor with `num_crops=16`. Dimensions include 1×1, square,
landscape, portrait and wide images. Native tensor has **17** entries (16 HD crop
budget plus global crop), not a changed 17-crop protocol. Tests check expanded
negative image tokens, vocabulary bounds, int64 IDs/masks/sizes, float32 CPU pixels,
grid/token counts, finite pixels and FP16 transfer requests. Production decodes by
file content and converts RGB, including original PNG bytes with a `.jpg` suffix;
tests use synthetic RGBA PNG with that suffix, not any original TRAIN image.

The 160-image smoke invokes production `NativeBackend.prepare/generate`, real
Transformers `.generate()` greedy/max64, forward hooks, tokenizer replay,
`execute`, strict parser, HNLO/oracle, first12, raw writer, reports, archive import
and `combine_archives`. Only model logits and the CUDA transfer/observer boundary
are test doubles. Scripted logits and resulting labels/scores are **SYNTHETIC
SOFTWARE TEST DATA — NOT RESEARCH RESULTS**; no quality or scientific metric is
reported from them. This proves plumbing, not actual model feasibility or quality.

## Coverage and acceptance table

PASS for a negative case means the expected failure was observed and retained.

| Layer | Success / failure evidence | Result and limit |
| --- | --- | --- |
| Grant/source | Model/mode/config/input binding, old/mixed source, null/full grant, duplicates, concurrent ledger winner, no overwrite. | PASS CPU; external cross-session ledger remains a human/release obligation. |
| Notebook clean session | Six deterministic payloads; corrupt payload exports BLOCKED ZIP/sidecar before import; stale imported source and path aliases rejected. | PASS CPU; actual Kaggle clean-session execution UNVERIFIED. |
| Runtime/venv/pip | Interpreter isolation, pip-free venv/bootstrap hash/controller/ABI/pins, failures before ledger. | PASS regression; live Linux 3.11 pinned ABI PASS; local Linux 3.12 unavailable. |
| Source/weights metadata | Hash all reviewed public files before import; live Hub exact revision/code inventory/two LFS shard identities; no weight request at CPU gate. | PASS metadata/source; actual worker weight hashes UNVERIFIED. |
| Model loader | Real a4/a5 before/after, direct shared loader, 32/24 layers, FA2/SDPA/implicit eager rejected. | PASS CPU meta; real checkpoint/GPU dispatch UNVERIFIED. |
| Processor | Native 16 crops, RGB/PNG, diverse dimensions, token/grid/mask/dtype/shape negatives. | PASS CPU synthetic; all 160 original images on this version UNVERIFIED. |
| CUDA/FP16 | GPU0/FP16 request preserved; hardware/receipt failures before ledger; worker CUDA gate after ledger. | PASS fault tests; actual CUDA/T4 RAM/VRAM peaks UNVERIFIED. |
| Generation | Native greedy64/EOS/decode, empty logits processors, prefix/NaN/OOM/decode/I/O faults; hooks removed. | PASS scripted CPU; actual Phi forward/KV cache/output UNVERIFIED. |
| Parser/HNLO | Strict JSON/INVALID, token decision mapping, candidate hook, alignment, Rust decoder, Decimal oracle, missing/nonfinite/changed processors. | PASS CPU; real model HNLO alignment UNVERIFIED. |
| Raw/accounting/first12 | Raw fsync before parse, native tokens even on prefix/decode failure, first12/13th failure, interruption/time cap/ENOSPC, tail not attempted. | PASS CPU; hard VM loss can prevent finalization. |
| Reports/export | 160-ID accounting, raw/tokenizer/request/step provenance replay, ZIP CRC/member SHA/sidecar/import, bounded log tail. | PASS CPU; Kaggle saved Output retention UNVERIFIED. |

The small [acceptance receipt](PHI_KAGGLE_CPU_ACCEPTANCE_143.json) and its
[checksum](PHI_KAGGLE_CPU_ACCEPTANCE_143.sha256.json) bind source, tests, script,
versions, loader/config observations and synthetic pipeline counts. Full logs and
synthetic ZIP stay ignored under `data/processed/phi143/`. Development failures
(fixture default dtype after a4; Windows command length) were corrected; the
final run is authoritative. Python 3.12 is **NOT RUN** locally: WSL system offers
3.14; the reusable pinned environment is 3.11.13, an allowed production version.
This is not a claim about Kaggle's installed interpreters.

Reproduce in an isolated environment with unchanged `phi.requirements.txt`:

```console
python -B -m scripts.build_three_vlm_notebooks
python -B -m unittest discover -s tests -v
python -B -m scripts.rehearse_phi_end_to_end --snapshot data/processed/approved_phi_public_source --output data/processed/phi_acceptance --base-commit f8ba79cf17fb12a9745c555a692cbb42f32be45d --live-source-probe
git diff --check
```

`--snapshot` is a reviewer/rehearsal input, never an Owner notebook edit. It must
contain the eleven source-locked public text/tokenizer files; no weights/data.
Native tests opt in via `SAFESHIFT_PHI_SNAPSHOT`; default stdlib suite skips them.

Final checks: Windows CPython 3.11.9 `unittest discover`: **195 tests, 185 PASS,
10 SKIP, 0 errors/failures** (six native opt-in, three Linux-only, one real pip
opt-in). Linux CPython 3.11.13 with original Torch 2.6.0+cu124 / Transformers
4.43.3 and both opt-ins enabled: **195/195 PASS, no skips or open test failures**.
The rehearsal uses the same complete unittest discovery as the documented command.
Live source-only Hub CPU admission also PASS. The real pip-free-venv bootstrap
was additionally run alone: **1/1 PASS**. Builder/parity and `git diff --check`
PASS. No production pins, contract, HNLO formula, manifest/selector or report
metrics were changed. Local full logs are linked by hash in the receipt.

## Diagnostics and remaining limits before any a6

Pre-ledger CPU diagnostics live under `cpu_probe/diagnostics`; constructor/model
and worker admission under `diagnostics`; per-image stages under
`run/samples/<ordinal>/diagnostics`. Start/pass/failure events identify stage and
subcomponent, bounded redacted traceback, errno, RAM/cgroup observations and all
attention config values/classes when available. GPU memory observations include
free/total/allocated/reserved/peaks after the boundary and on generation failure.
`native.json` is saved before response decoding/prefix enforcement. Technical
errors stop; HNLO-only failures keep successful classification separately.

Export keeps ordinary logs intact. Logs over 8 MiB export a distinct `.tail.txt`
with original byte count/full SHA and tail SHA in `log_exports.json`; originals
remain in the evidence directory. Raw/model output is never truncated. Disk-full
or hard kill can still prevent any further write/export; existing evidence stays.
Report-stage failure is a structured worker event; export failure also attempts
a separate `<archive>.export_failure.json` containing truthful consumption state,
because a failed/partially sealed archive cannot be modified in place.

Before a6, ChatGPT must review this one Draft PR, decide independent audit, then
authorize merge and verify main. Later release/grant must bind the final source,
manifest, config, reviewed ledger and fresh attempt. No such grant is created here.
Kaggle 3.12 clean setup, real weights/Accelerate dispatch, 16-crop eager T4 fit,
first-image native logits, HNLO validity, 160-image completion and retention are
all **UNVERIFIED** for this source. A fixed-conditions OOM must stop with evidence;
do not change crops/FP16/eager, use GPU1, quantize or retry to bypass it.

## Official Kaggle/HF review and Owner operation

Reviewed [Kaggle notebook docs](https://www.kaggle.com/docs/notebooks): Save & Run
All runs top-to-bottom in a separate session. Do not rely on interactive installs
or files. The dynamically rendered page was partially unavailable to the browser
tool; the official indexed passage confirms the separate-session behavior.
[Metadata docs](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)
define the Internet/GPU/private/input fields and `NvidiaTeslaT4` as T4×2;
[CLI docs](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) say push
runs the kernel, and `--no-run` saves without running. No Kaggle API is invoked.

[Kaggle docker-python](https://github.com/Kaggle/docker-python) describes image
builds, not this session's resource guarantee. The a5 incident reports ~14912 MiB
free / 15360 MiB total on GPU0 and 28+4 GiB storage admission; these are historical
observations, not new measurements. RAM/cgroup limits and peaks must be observed
again. Two T4 cards do not provide pooled VRAM for GPU0.

The [Phi card at the frozen revision](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/README.md)
and its [native processor source](https://huggingface.co/microsoft/Phi-3.5-vision-instruct/blob/12b77fb40b63a2c73c68243d3f767aab688a1b2a/processing_phi3_v.py)
were reviewed. Preserve repository Torch 2.6.0+cu124 / Transformers 4.43.3 pins,
original revision, C1/generation/HNLO/thresholds, original 160 TRAIN, GPU0 FP16
eager and 16 crops. The card's other configurations do not authorize a change.

After the separate release/grant process, Owner operation is:

1. Create a **private Kaggle Dataset** containing exactly the approved release
   `grant_phi.json` at its root. Keep the already accepted 160-image input Dataset
   private. Upload the supplied files unchanged; no manual JSON/code/path/SHA edit.
2. Import the released `SafeShift_TRAIN_PILOT_phi.ipynb`. Add Input: the accepted
   bundle Dataset and the single current grant Dataset. Remove stale grant inputs.
   Duplicate/missing files or a source-bound old grant stop before consumption.
3. Set Internet ON and GPU T4×2 for the saved version. Choose **Save Version →
   Save & Run All once**. Do not run interactively first or rerun a consumed attempt.
   The clean session repeats CPU admission, then physical GPU receipt, ledger,
   worker CUDA, weights and generation in that order.
4. In saved Outputs download the printed ZIP and matching `.sha256.json` under
   `data/processed/three_vlm/`, including BLOCKED/partial results. Scratch is under
   `/kaggle/tmp` and is cleaned; never publish cache/weights or the whole working
   tree after cleanup failure. Retain evidence promptly; hard VM loss remains a risk.

Release preparers can use `python -B -m scripts.package_phi_kaggle --help` to
prepare local CLI metadata with supplied approved kernel/input/grant identifiers.
It generates private/Internet/T4×2 settings and the same notebook, no credentials,
grant issuance, upload or run. Actual CLI submission is outside this task.
