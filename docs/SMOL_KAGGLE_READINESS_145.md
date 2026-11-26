# SmolVLM2 Kaggle readiness — Issue #145

29/10/2026, Asia/Bangkok. BASE `a7dacd6ebb1d0bb9ee3fd2c0fb63a0a1001e90e4`.
One isolated worktree and one Draft PR. No tool creates a new Codex UI session;
isolation is a new branch/worktree, not a claimed new UI session. No Kaggle API,
GPU, trained weights, real model forward, grant issuance or merge in this task.

This is software acceptance, not a Smol prediction/quality/HNLO result. The
[Phi a6 aggregate evidence](https://github.com/tantdna2/SafeShift/pull/144#issuecomment-6480224537)
records 160 actual calls, 0 valid C1 JSON, 142 identical sequences and zero
validated HNLO. Its ZIP SHA-256 is
`19b9c201bde2c018b501b5eefd4cd00f8f4f6e9b7fe92b9cd79e6a9bfcfdb161`.
This task verified that GitHub record; it did not reopen the private a6 archive.
The a6 attempt is CONSUMED. Root cause of its output behavior is unresolved.

## Pinned API and source review

- Checkpoint: `HuggingFaceTB/SmolVLM2-2.2B-Instruct`, revision
  `482adb537c021c86670beed01cd58990d01e72e4`. Eleven public config/tokenizer files
  retain the original SHA-256 lock. No model/class/revision change.
- [Versioned 4.51.3 docs](https://huggingface.co/docs/transformers/v4.51.3/en/model_doc/smolvlm)
  use `AutoModelForImageTextToText`. Its pinned mapping resolves `SmolVLMConfig`
  to the same `SmolVLMForConditionalGeneration` used here, checked by a native test.
  The page's example uses a different model/precision/placement; those settings
  do not override this pilot's FP16/eager/GPU0/batch1/greedy max64 contract.
- Read the [frozen model card](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct/blob/482adb537c021c86670beed01cd58990d01e72e4/README.md)
  and exact [4.51.3 config](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/smolvlm/configuration_smolvlm.py),
  [model](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/smolvlm/modeling_smolvlm.py),
  [Llama dispatch](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/llama/modeling_llama.py),
  [loader](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/modeling_utils.py),
  [processor](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/smolvlm/processing_smolvlm.py)
  and [generation](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/utils.py).
  Library-source hashes are included in the CPU receipt. The Hub UI may display
  automatically generated examples from newer libraries; those are not used.
- Original config declares outer float32, text bfloat16, legacy
  `_flash_attn_2_enabled=true`, outer `use_cache=false`, pad 128002. Pinned native
  Llama attention dispatch reads `_attn_implementation`; the legacy flash flag
  does not select FA2. Text padding is 2; checkpoint generation tokens are
  BOS=0, EOS=49279, PAD=2. The existing fresh GenerationConfig still explicitly
  uses cache=true and original `GENERATION`; no inherited forcing/suppression.
  Cache usage is distinct from the two `_use_flash_attention_2` dispatch flags.
- Native processor requires `num2words` even for still images; the original
  runtime reproduced ImportError. Add only `num2words==0.5.14` and its
  `docopt==0.6.2` dependency to Smol requirements/runtime lock. See official
  [num2words metadata](https://pypi.org/pypi/num2words/0.5.14/json) and
  [docopt metadata](https://pypi.org/pypi/docopt/0.6.2/json).
  Existing pins, scientific contract and Gemma/Phi dependency sets are unchanged.

## Shared admission and production path

`pilot/smol.py` is used by both `cpu_software_probe` and NativeBackend. Source
hashes precede processor import/load. Config is deserialized from the locked
checkpoint; eager is explicit in outer/text/vision configs. Native
`from_pretrained` constructs the original full architecture on meta with an
empty state dict. A separate native test exercises the actual local checkpoint
path using an empty safetensors fixture. No loader/constructor mock substitutes
for either loader. Imports resolve before entering meta because Torch's lazy
dynamo import performs scalar introspection that cannot run on meta tensors.
Unlike Phi's 4.43.3 loader, 4.51.3 explicitly relocates missing parameters back
to CPU. CPU admission therefore also uses the official Accelerate 1.6.0
[`init_empty_weights(include_buffers=False)`](https://github.com/huggingface/accelerate/blob/v1.6.0/src/accelerate/big_modeling.py)
parameter registration context, with Torch's meta context for buffer construction.
This context is CPU-only; it is never applied to the production weight load.
The plain-meta/empty-state development rehearsal was rejected by tensor checks;
the final receipt records the qualified route. Temporary native missing-key
allocation behavior is not a measurement of real weight-load peak RAM.

Acceptance checks actual dispatch configs on all 24 Llama + 27 vision attention
layers and both cached flash flags, not just class names or the loading kwarg.
All meta parameters/buffers remain on meta and floating parameters are FP16.
Native rotary buffers retain float32, as in the pinned implementation; their
dtypes are recorded rather than changed to satisfy an assertion.
Parameter footprint is 2,246,784,880 × 2 = 4,493,569,760 bytes, **not peak RAM,
VRAM or a T4 fit estimate**. Runtime repeats strict attention checks after real
weight load and saves config/runtime receipts. SDPA/FA2 drift is rejected.

Processor uses the existing two-step API: `apply_chat_template(tokenize=False,
add_generation_prompt=True)`, then `processor(text=...,images=[image],
add_special_tokens=False,return_tensors='pt')`. This preserves one image marker,
one conversation prefix and the assistant suffix. Locked native preprocessing
remains size=1536, max tile=384, splitting/padding/RGB enabled, 81 image tokens
per tile, image ID=49190 and vocab=49280. Input IDs/text mask/pixel mask stay
int64; pixels start float32 and only floating tensors transfer to FP16. Token
prefix, native image expansion, masks, finite pixels and input+64 ≤8192 are checked.

CPU admission handles 1×1, medium and large synthetic RGB images, verifies native
label branches against the prior locked tokenizer evidence, and checks Hub
revision/inventory/two-shard LFS metadata with `token=False`. The separate
`smol_checkpoint_metadata.json` locks the verified names, sizes and LFS hashes;
the 63,881-byte public index has 657 tensors and is hash-checked before weights.
Meta state-dict keys must match that index. Checkpoint storage is 8,987,224,056
bytes (float32 saved tensors plus headers), distinct from the FP16 parameter footprint.
That is metadata identity, not downloaded-weight hash proof. Additional tests
cover portrait/landscape, PNG bytes with a .jpg suffix, RGBA→RGB and corrupted
prefix/dtypes/prompt. No TRAIN image is a test fixture.

The order remains: embedded source/grant → source review/input/hash checks →
28 GiB scratch + 4 GiB output admission → independent Linux CPython 3.12/3.11
venv without pip → verified pip wheel/bootstrap → pinned installs/check/freeze →
CPU native admission → nvidia-smi T4×2/GPU0 free≥14 GiB and durable receipts →
exclusive ledger consumption → worker CUDA FP16 check → actual weights/model.
Missing prerequisites stop before ledger. Worker independently checks identity,
CUDA, source and attention after ledger. GPU1 does not pool memory with GPU0.

Diagnostics preserve subcomponent/stage, bounded redacted traceback and resource
observations before backend construction and during image processing/generation.
Partial native IDs and raw step evidence precede decoding/validation. Existing
report/export failure receipts and partial evidence retention remain active.

## CPU acceptance and limits

Final Linux CPython 3.11.13: **211 tests, 205 PASS, 6 SKIP, zero errors/failures**;
the six skips are native Phi 4.43.3 opt-ins, not Smol skips. Real pip bootstrap
opt-in ran and passed. Windows CPython 3.11.9: **211 tests, 192 PASS, 19 SKIP**
(9 Smol + 6 Phi native opt-ins, 3 Linux-only and 1 real-pip opt-in).
Source/test/script stayed unchanged during final acceptance. Source digest:
`1d76c3a4e5cf9c5fe32d6fd94b846a2879eca268a6023ce34203794dc801d884`.
All six notebooks regenerate byte-for-byte, share that embedded source, have
no outputs/execution counts and compile. Protected scientific files and
`git diff --check` PASS. Receipts/checksums are in
[SMOL_CPU_RECEIPT_145.json](SMOL_CPU_RECEIPT_145.json) and its
[SHA-256 sidecar](SMOL_CPU_RECEIPT_145.sha256.json).

Fresh venv creation, verified pip bootstrap, both ordered dependency installs,
pip check/freeze and pins all passed. The initial setup receipt remains BLOCKED
because its development CPU gate assumed one shard; it is preserved. Corrected
native CPU admission was rerun on the same fresh pinned environment without
reinstalling unchanged dependencies. Plain-meta tensor rejection was also
preserved during development. The final receipt requires actual loader/native
processor, both 160-call cases and live source admission PASS; it does not reuse
those rejected receipt statuses or the intermediate run whose tests were edited.

The valid synthetic ZIP has 3,693 members and 160 raw records, SHA-256
`58e22eea8fa97a258f6824fd7aab3d981ca95e599656f1e48f4f3edc19fe33e8`;
the INVALID synthetic ZIP has 2,734 members and 160 raw records, SHA-256
`d480d76de62c4b8d1bf5c92522dc9724a6a6d650db192adb7f62462143f146db`.
CRC, exact membership, every member SHA and external sidecars PASS; valid native
raw→HNLO/report CLI replay validates all 160 scripted records, while the INVALID
case validates none. A separate scripted label-prefix/prose case reaches max64
without EOS and remains INVALID/HNLO unvalidated. These are **not model predictions**.

Reproduce from the repository root in the pinned Smol venv:

```console
python -B -m scripts.build_three_vlm_notebooks
python -B -m unittest discover -s tests -v
SAFESHIFT_REAL_PIP_BOOTSTRAP=1 python -B -m scripts.rehearse_smol_end_to_end --snapshot data/processed/approved_smol_public_source --output data/processed/smol_cpu_acceptance_v1 --base-commit a7dacd6ebb1d0bb9ee3fd2c0fb63a0a1001e90e4 --live-source-probe
git diff --check
```

`--snapshot` is a reviewer input containing the eleven locked public files plus
the separately hash-locked public safetensors index;
Owner never edits a notebook path/SHA. Native tests opt in with
`SAFESHIFT_SMOL_SNAPSHOT`; no default test downloads model files. The rehearsal
requires both 160-call cases to execute before it can report PASS. Scripted
models run native Transformers `.generate` with test-only deterministic logits;
actual Smol forward and real CUDA are forbidden. All raw records/ZIPs carry
explicit synthetic provenance, including imported report runtime metadata.

| Check | CPU evidence | Still requires authorized real Kaggle GPU run |
| --- | --- | --- |
| Real loader/config/attention/tokenizer | Full original meta architecture, local empty-safetensors loader, explicit 24+27 eager, SDPA/FA2 regression | Weights download/hash/deserialization, Accelerate placement, true load peak |
| Processor | Shared function, synthetic image envelope/token/mask/dtype/context checks | Actual first TRAIN image and full dimension envelope on the saved Kaggle session |
| Generation/raw/HNLO | 160 scripted valid calls, raw-before-parse, prefix/EOS/step/argmax and independent tokenizer/numeric replay, reports/ZIP/import | Native Smol logits/decision alignment, valid C1 rate, HNLO coverage/quality |
| Invalid/repeated output | Separate 160 scripted INVALID calls: raw retained, zero label rescue/HNLO, descriptive repetition counts | Whether real Smol produces repeated or invalid outputs; no quality guarantee |
| Failure custody | OOM/nonfinite/prefix/decode/capture I/O/tokenizer/report/export faults; exact planned tail and archive checks | Real OOM/disk exhaustion/hard-kill/VM retention behavior |
| Runtime/notebook | Linux 3.11 pinned stack/ABI/bootstrap, stdlib fault tests, six regenerated notebooks with one source digest | Kaggle CPython3.12 clean install, T4×2 observation, CUDA FP16/VRAM/latency |

`early12.technical_gate=PASS` remains possible when all first 12 responses are
INVALID. Tests expose that risk; no early validity stop, threshold, parser,
prompt, HNLO formula or scientific protocol was changed. `output_diagnostics.json`
counts raw sequence/response repetition, lengths, EOS and strict JSON validity;
it has no threshold or recommendation effect and does not establish a cause.
The same read-only diagnostic can verify an already saved private archive:

```console
python -B -m scripts.diagnose_pilot_outputs --archive data/processed/private_result.zip --output data/processed/output_diagnostic.json
```

## Gemma and handoff boundary

Unauthenticated source audit on the frozen Gemma revision returned 401 for all
ten config/tokenizer resources; only README was public. `files={}` and the ten
unavailable entries remain unchanged in the source lock. Gate remains
`BLOCKED_SOURCE_TOKENIZER_AUDIT_INCOMPLETE:gemma`. Public
[model card/terms](https://huggingface.co/google/gemma-3-4b-it) do not prove gated
read permission. Owner must accept terms on the authorized HF account, provide
read access via Kaggle Secret HF_TOKEN, then obtain valid source/hash/tokenizer
review and a separately reviewed release/grant. No credentials were used here;
no Gemma lock was invented or grant created.

After ChatGPT reviews the one Draft PR and decides independent audit, merge
requires separate authority and verification. Only then may a separate grant
bind the merged source/config/accepted manifest and a fresh ledger-backed attempt.
Historical Smol a1 is RESERVED/NOT_EXECUTED and its old grant is not transferable.
This PR supplies no new/modified grant or attempt reservation.

Future Owner operation: attach the approved private 160-image input Dataset and
exactly one current private `grant_smolvlm2.json` Dataset; remove old grants;
import the released notebook unchanged, Internet ON, T4×2; Save Version → Save &
Run All once. Download printed ZIP + `.sha256.json` from saved Outputs including
BLOCKED/partial results. Scratch is cleaned outside working; never publish cache
or the whole working tree. The [Kaggle notebook docs](https://www.kaggle.com/docs/notebooks)
are dynamically rendered and were unavailable to this browser retrieval; the
official [CLI metadata docs](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels_metadata.md)
define saved private inputs/Internet/accelerator settings. No Kaggle call was made.
