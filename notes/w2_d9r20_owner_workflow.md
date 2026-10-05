# D9R20 — future owner workflow

NOT EXECUTED. Merge/review of this PREP plus separate Research Lead authorization
are prerequisites for owner model execution. No authorization is issued by this
PR. Run candidates separately in order Ovis, PLaMo, Kosmos. Each run remains
single T4 16GB, FP16, NONE, batch one, no model offload/fallback. A kernel/load/OOM
failure is a resource/runtime NO-GO, never a grounding semantic FAIL. Stop rather
than changing hardware, precision, parser, prompt, budget or checkpoint.

## 1. Pin post-merge code and prepare synthetic inputs

Use a clean checkout of the exact post-merge main commit approved for observation.
Fetch `origin/main`; record `git rev-parse HEAD`, `git rev-parse origin/main` and
the PREP BASE `668aae839bbde91b67686d143259e07c8a89608c`. Both live HEAD and main
must match the later signed-off authorization; PREP BASE must be an ancestor.
Do not fill HEAD with the PREP BASE or invent a future merge SHA now.
Changing main/HEAD/environment/snapshot requires fresh review, not auto-relock.

The classification eight PNG fixtures are already in Git. Generate the existing
twelve synthetic grounding images with the unchanged renderer:

```sh
python scripts/prepare_grounding_multicategory_v3.py
```

Renderer provenance is Python 3.11.9 / Pillow 11.3.0 / zlib 1.3.1 (existing v3
contract). It verifies byte-identical manifest hashes and refuses mismatches;
use a small separate rendering environment if needed, then use the model-specific
environment. This does not impose a common model environment. Never regenerate
or replace the manifest to accommodate a rendering mismatch. No dataset path or
image override is accepted by the owner runtime. All inputs are 256x256 synthetic.

## 2. Provision one model in its independent environment

Follow its specific runbook. This future step can download weights only after
separate owner authorization and, for PLaMo, owner license acceptance. The PREP
task downloaded none. Provision online, then turn venue Internet **off** before
observation/run. The runner also enables HF/Transformers offline mode and blocks
Python socket connections during model load and calls; the socket guard is not
an OS sandbox, so venue Internet-off remains required for custom code.

Download only the exact revision into the model-specific local directory, using
`hf download --include` from its runbook. Snapshot inventory verifies every
required safetensors/code/config/tokenizer file against HF LFS SHA256/size or Git
blob ID/size; records SHA256 of all local files. No `.bin` duplicate weights,
media or alternate revision. No symlink/alias snapshot paths. The directory name
alone is never treated as byte verification. Weights stay under ignored `.cache/`.

## 3. Observe before model load, then obtain separate authority

The model runbooks give exact commands. `observe` inspects Git, all installed
distributions, required dependency pins, CUDA runtime, driver, T4 properties and
local snapshot hashes/sizes. No model is loaded and no inference runs. It writes
an exclusive observation JSON, including phase/reason if observation fails.
Bundle an observation for audit, including failed provisioning/environment checks:

```sh
python scripts/run_d9r20_candidate.py bundle --model ovis --observation data/processed/d9r20/ovis-observation.json
```

The corresponding PLaMo/Kosmos runbooks use their own observation names. A failed
observation cannot authorize loading. Fixing provisioning needs a separately
reviewed observation with a new filename; never overwrite evidence or change
the scientific contract to rescue a run.

Research Lead reviews the observation and issues a separate local authorization
based on `configs/pre_freeze/d9r20_authorization.template.v1.json`. The committed
template stays false. The owner-created authorization must bind the exact
model/revision/run ID, PREP BASE, current merged HEAD/main, observation SHA256,
reviewer/reference, `prep_merged=true`, `execution_authorized=true`, and the scope
`RESOURCE_SMOKE_AND_SINGLE_TARGET_SYNTHETIC_ONLY`. PLaMo additionally requires
`owner_license_accepted=true`, supplied only by the owner. Never include tokens,
credentials or license-account details in artifacts. This is documentary
authorization, not a cryptographic signature or automatic approval service.

## 4. One load and one fixed 22-call sequence

`run` repeats observation and requires byte-equivalent identities/environment/
snapshot before load. One model load per owner-run; failed load consumes the
attempt. It checks FP16 model parameters and cuda:0 placement, rejects quantized
models/device maps, and supplies no automatic placement/offload arguments.
Native FP32 algorithm buffers/calculations are not a BF16/model-precision fallback.
First completed generation supplies resource-smoke observation only. Classification
parse validity and semantic correctness remain separate fields.

The fixed sequence is eight D9R16 classification calls plus fourteen single-target
grounding calls defined in the PREP note. Every call has a fresh image/text input,
no saved conversation or KV state supplied across calls. Greedy generation,
max_new_tokens=512, one beam/sequence, seed 0; no cross-device bitwise reproducibility
claim. Native generation defaults are recorded per call. No retry, repair,
temperature/budget adjustment, fallback or mid-run parser change.

Native generated IDs and input IDs are written exclusively, fsynced and read back
before decode/boundary validation or parsing. Separate special/plain decodes are
then persisted. EOS/truncation is checked without regex stripping. Ovis completion
IDs are handled differently from the exact HF prompt-prefix outputs. On blocking
`generate` exception, the backend may not expose partial tokens: record that
failure without inventing unavailable raw output. Existing earlier raws survive.

Run directories are independent and exclusive:

| model | run directory |
|---|---|
| Ovis | data/processed/d9r20/d9r20-ovis-fp16-001 |
| PLaMo | data/processed/d9r20/d9r20-plamo-fp16-001 |
| Kosmos | data/processed/d9r20/d9r20-kosmos-fp16-001 |

Never delete a failed attempt to rerun under the same ID. A subsequent attempt
requires a separate prospective decision/contract; no rerun CLI switch exists.

## 5. Bounded result bundle and human audit

Use the model's `bundle` command after execution, successful or failed. The CLI
checks raw/decoded hashes/sizes and writes an exclusive ZIP, bounded to 32 MiB
uncompressed JSON. It includes result/observation, exact Git HEAD/main/BASE,
model/revision, dependencies/hardware, snapshot file hashes/sizes, load status,
resource smoke status, peak memory, all attempted call IDs, full prompts and hashes,
raw IDs/hashes/sizes, parse/canonical results, capability witnesses/tracking,
all-box semantic diagnostics, and failure phase/reason. It contains no input
media, weights, secrets or InspecSafe data. Raw outputs and ZIP stay ignored,
outside Git; share the bundle with Research Lead manually after checking it.

The result's `PENDING_REVIEW` is unconditional: no runtime path writes PASS,
participant status or roster files. Human review must separately assess the
mandatory target/position tracking witnesses and matched-box NO_GIANT findings,
classify objective interface failures, retain every semantic error, and keep
Call2 orchestration blocked. A later production contract and separate participation
decision are still required even if single-target capability is demonstrated.
Result structural contract: `schemas/d9r20_result.v1.schema.json`.

Pipeline/storage faults may prevent writing a complete report. Preserve the
exclusive partial directory and report the storage fault to Research Lead; never
fill in missing raw hashes/results or claim the bundle is complete.
