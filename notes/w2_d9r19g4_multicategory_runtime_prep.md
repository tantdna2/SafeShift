# D9R19G4 multicategory runtime integration PREP

Date: 2026-10-04. Task:
`W2.6-D9R19G4-MULTICATEGORY-RUNTIME-INTEGRATION-QUALIFICATION-EXECUTION-PREP`.
Fetched `origin/main` equals required BASE
`685021ef974cc3feef968d7e920e7720ce6349f2` (G3 merged as PR #70).
Branch: `w2.6-d9r19g4-multicategory-runtime-prep`.
DECISIONS/TASKS append closure only; historical MERGE=NO statements remain.

## Status and scope

Separate [runtime](../safeshift/runners/grounding_multicategory_v3.py) and
[CLI](../scripts/run_grounding_multicategory_v3.py) implement G3's 12 positive
synthetic calls for each pinned model. G3/v3 artifacts and all historical runners,
parsers and gate results are unchanged. No model import/load/generate, GPU probe,
snapshot download, qualification or InspecSafe execution occurred in G4.

Offline integration: READY_FOR_EXTERNAL_EXECUTION_REVIEW after focused checks.
This does not mean runtime-ready. QWEN3_RUNTIME_INTEGRATION=BLOCKED and
PALIGEMMA_RUNTIME_INTEGRATION=BLOCKED for actual execution because the external
environment lock is unverified and execution authorization is absent.
The committed [environment contract](../configs/pre_freeze/grounding_multicategory_environment.v1.json)
states observed=false, runtime_ready=false, execution_authorized=false,
QUALIFICATION_EXECUTION=NOT_RUN. No model result is claimed or committed.

## Evidence and environment lock

| Model | Prospective hardware | Existing evidence |
| --- | --- | --- |
| Qwen3-VL-8B-Instruct | Kaggle Tesla T4 x2, CC 7.5, FP16/NONE, auto GPU placement without CPU/disk offload | `configs/pre_freeze/qwen_kaggle_smoke_result.v1.json` |
| PaliGemma-3B-mix-448 | Kaggle Tesla T4 x1, CC 7.5, FP16/NONE, cuda:0 | `configs/pre_freeze/paligemma_t4_runtime_result.v1.json` |

These are Research Lead-recorded historical smoke results, not direct G4 bundle
inspection and not v3 runtime validation. Qwen's recorded Python 3.12.13,
torch 2.10.0+cu128, CUDA 12.8, transformers 4.57.1, Pillow 11.3.0 environment lacks
a recorded tokenizers version. Pali's recorded Python 3.11.11, torch 2.6.0+cu124,
CUDA 12.4, transformers 4.57.1, tokenizers 0.22.1, Pillow 11.2.1 is complete for
those fields. G4 neither infers missing versions nor equates those records with
the next external venue. Actual package/GPU/snapshot inventory must be recorded
and independently approved before model load.

The [runtime lock](../configs/pre_freeze/grounding_multicategory_runtime_lock.v1.json)
binds runner, CLI, schema, parser, G3 plan/manifest/source/lock, environment template,
snapshot verification code and documentary snapshot inventories. G3's own lock
also verifies generator/geometry dependencies and 73 protected historical blobs.
Text hashes use G3's Git-normalized LF representation; raw and snapshot hashes use
exact bytes. Environment approval hashes `encode(environment)` (sorted-key JSON,
ASCII escaping, no NaN), not the pretty-printed document representation.

Future inventory captures Python, torch, CUDA, transformers, tokenizers, Pillow,
accelerate, Hub and safetensors, GPU model/count/CC, model/processor/tokenizer
revision, every snapshot file SHA256/size, code/contract hashes, generation config
and HEAD. Pali verifies all 14 files against its existing authoritative inventory.
Qwen verifies all four weight shards against recorded immutable provenance, then
inventories all metadata/tokenizer/template files. The external reviewer must
verify those Qwen metadata bytes belong to the exact revision before approving
the environment hash; G4 has not fetched or independently verified those bytes.
There is no implicit provisioning or revision fallback.

The runner re-observes the complete approved inventory before loading and requires
exact equality. Model/processor are loaded from that verified local snapshot,
with exact revision, local_files_only=true and trust_remote_code=false. Model
weight-key checks reject missing/unexpected/mismatched/error entries. Parameters
must be FP16 on CUDA. Transformers 4.57.1 is enforced for the audited processor API.
Future environment observation inspects GPUs but never loads a model; it was
not invoked in G4. Python socket denial plus offline HF variables supplement the
operator's independently attested venue Internet-OFF boundary.

## Call and persistence contract

Both models use exactly G3's fixed four-label prompt on every case, without GT or
case identity entering the native runtime. Qwen uses the pinned processor chat
template without system override. Pali receives exactly
`detect red square ; green circle ; yellow triangle ; cyan rectangle`; the native
processor alone appends LF. Decoded input must equal that text plus exactly one LF.
No manual EOS/whitespace stripping, lowercase, fuzzy matching, repair or salvage.

One model load, sequential batch-one native generate per case. The same isolated
generation config is used on all calls: do_sample=false, beams=1, return_sequences=1,
max_new_tokens=512. Explicit SDPA, use_cache=false and disabled auxiliary generation
outputs follow the existing runtime API; Pali logits_to_keep=1 limits returned
logits, not the token ceiling. Qwen's per-call RoPE/cache state is cleared uniformly.
The full effective generation config is retained in every raw envelope. Static and
fake-native tests assert 512 reaches generate; no model was run to size the budget.
Production all-12 query/token/context budget remains SEPARATE/PENDING.

For each call: native generation/decode -> exclusive raw bytes plus preparse
metadata -> flush/fsync/close each -> reread both -> SHA256/size verification ->
validate input prefix/full IDs/continuation/EOS/config -> unchanged candidate
parser receives only the persisted parser-decode continuation -> separate parse
and geometry record. Full generated rows/IDs, input IDs, continuation IDs, decode
with special tokens and parser decode are retained. The raw envelope records
effective config, EOS identity, termination and processed image dimensions/grid;
preparse metadata supplies run/call/sample, model/revision, prompt/hash, input/hash,
parser/plan/manifest/source/lock hashes, software/hardware, seed, commit and command.

Storage, hash, boundary, native or EOS/truncation failure stops the run before
parser and preserves available evidence. No unavailable output is fabricated.
Invalid parsed responses retain null canonical detections, and the fixed remaining
calls still execute without response-conditioned generation changes. A failed or
interrupted run has only actual call records; it never fills unattempted cases with
placeholder results. Partial persisted artifacts remain in the consumed run directory.
The directory cannot be reused, even if empty; there is no automatic retry.

## Preflight, results and human review

Preflight checks frozen hashes and identities, main==BASE, HEAD descended from
BASE, exact authorized HEAD, clean execution checkout, pinned model/revisions,
approved environment hash/lock, all 12 cases/positive targets/same labels,
512-token greedy config, exact synthetic image paths/hashes and a new run directory.
There are no retry/repair/prompt/budget override flags. Absolute/raw/InspecSafe paths
and traversal are rejected. If main advances, STOP for Research Lead review;
do not change the BASE guard to make execution proceed.

The [result schema](../schemas/grounding_multicategory_result.v1.schema.json) and
writer record RUN_ID, model/revision, environment, actual calls/raw hashes, parse
status, all canonical detections, geometry, tracking, human-review status and final
verdict. Completed runs require 12 calls; only BLOCKED/FAIL/PENDING_REVIEW/PASS are
valid verdicts. The runtime writer categorically rejects PASS. Automatic success
writes PENDING_REVIEW. Result and every successful raw/preparse/parsed artifact
are audited and indexed by SHA256/size. Failure cannot acquire a complete audit.

`human_review.template.json` contains every canonical detection, zero-based index,
case, synthetic image path, bbox/label and raw hash, with reviewer/rationale/decision
null. Reviewers inspect images and boxes, then provide NO_GIANT or GIANT plus named
reviewer and rationale for each detection. No numeric giant-area threshold is added.
Finalization rehashes indexed artifacts, rejects duplicates/extra identities/hash or
detection mismatch, and writes a new exclusive `human_review.final.json` bound to
the runtime result hash. Missing review/rationale -> PENDING_REVIEW; any GIANT or
automatic failure -> FAIL. Original runtime result is never overwritten. Human
reviews are entered externally; none were performed in G4.

## Exact future commands (NOT EXECUTED against models in G4)

Commands run from repository root in a reviewed checkout at the exact approved
HEAD. Prepare synthetic images using G3's generator environment (Python 3.11.9,
Pillow 11.3.0, zlib 1.3.1), and transfer/verify those ignored PNG bytes if the model
venue has a different Pillow/zlib. Do not regenerate a different manifest.

```text
python scripts/prepare_grounding_multicategory_v3.py
python scripts/run_grounding_multicategory_v3.py --model qwen3 --run-id g4-qwen3-v3-001 --dry-run
python scripts/run_grounding_multicategory_v3.py --model paligemma --run-id g4-paligemma-v3-001 --dry-run
```

Those dry-runs remain BLOCKED until externally supplied environment/authority are
present. Future venue inventory after separate operator approval and existing exact
snapshot provisioning (G4 does not provision):

```text
python scripts/run_grounding_multicategory_v3.py --model qwen3 --run-id g4-qwen3-v3-001 --inspect-environment --snapshot data/processed/qwen3_hf_cache/models--Qwen--Qwen3-VL-8B-Instruct/snapshots/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b --output data/processed/grounding_v3_review/qwen3.environment.json
python scripts/run_grounding_multicategory_v3.py --model paligemma --run-id g4-paligemma-v3-001 --inspect-environment --snapshot data/processed/paligemma_hf_cache/models--google--paligemma-3b-mix-448/snapshots/ead2d9a35598cb89119af004f5d023b311d1c4a1 --output data/processed/grounding_v3_review/paligemma.environment.json
```

Research Lead plus independent auditor must review this Draft PR and the actual
environment before creating separate `qwen3.authorization.json` and
`paligemma.authorization.json` under `data/processed/grounding_v3_review/`.
Required fields are enumerated in the environment contract. `head_sha` must be the
exact reviewed commit, `main_sha` the required BASE, and model/run IDs the exact
command values. Named distinct reviewers, a traceable review reference and Internet
OFF attestation are mandatory. G4 supplies no true authorization file. JSON is an
operator-supplied governance attestation, not a cryptographic signature service.

Set HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1, HF_HUB_DISABLE_TELEMETRY=1,
HF_HUB_ENABLE_HF_TRANSFER=0 and HF_HUB_DISABLE_XET=1 before Python. Expose exactly
two T4s for Qwen or one T4 for Pali in separate model environments/processes. Then,
only after separate approval, the exact future execution commands are:

```text
python scripts/run_grounding_multicategory_v3.py --model qwen3 --run-id g4-qwen3-v3-001 --execute --environment data/processed/grounding_v3_review/qwen3.environment.json --authorization data/processed/grounding_v3_review/qwen3.authorization.json
python scripts/run_grounding_multicategory_v3.py --model paligemma --run-id g4-paligemma-v3-001 --execute --environment data/processed/grounding_v3_review/paligemma.environment.json --authorization data/processed/grounding_v3_review/paligemma.authorization.json
```

Use the same flags with `--dry-run` instead of `--execute` for approved static
preflight. After real execution and human review, offline finalization commands:

```text
python scripts/run_grounding_multicategory_v3.py --model qwen3 --run-id g4-qwen3-v3-001 --finalize --reviews data/processed/grounding_v3_review/qwen3.reviews.json
python scripts/run_grounding_multicategory_v3.py --model paligemma --run-id g4-paligemma-v3-001 --finalize --reviews data/processed/grounding_v3_review/paligemma.reviews.json
```

Do not create reviews before actual detections exist. New authorization is needed
for any subsequent run; this is not permission to retry a failed qualification.
Preserve complete run folders and external artifact-index hashes for independent
audit, outside Git. Successful software integration/qualification never grants
production/982-sample execution or model promotion.

## Validation

G4 local environment: Python 3.11.9, Pillow 11.3.0; fake-native/handcrafted tests only.

```text
python -m unittest tests.test_grounding_multicategory_runtime_v3 tests.test_grounding_multicategory_v3 tests.test_grounding_interface_v2 tests.test_grounding_absence_semantics_audit -q
python -m unittest tests.test_qwen3_external_gate tests.test_qwen3_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result tests.test_paligemma_interface_candidate tests.test_external_gate_cases tests.test_d9r7_paligemma_source_api_audit tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_qwen_runner tests.test_paligemma_prep -q
python scripts/run_grounding_multicategory_v3.py --help
git diff --check
```

103 focused tests (26 new) and 267 relevant regressions PASS: 370 total.
Full suite was not run; no full-suite PASS claim. CLI help, synthetic preparation,
two unauthorized dry-runs (expected BLOCKED), strict JSON, append-only/history and
diff checks are recorded as PREP-only verification. No tests use InspecSafe content.
Unchanged historical task-specific diff allowlists are outside this focused scope.

PR #67 was read only and matched OPEN/DRAFT at
`e85300ab3ec122f819a2685613332578f7e203d8`. Historical Qwen3 gate=GATE_FAIL and
PaliGemma gate=FAIL; both primary grounding roles=NOT_PARTICIPATING. Both absence
blockers=UNRESOLVED; production budget=PENDING; 982 production scope NOT_RUN.
QUALIFICATION_EXECUTION=NOT_RUN; EXECUTION_AUTHORIZED=NO; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; PROMOTION=NO; PR67_UNCHANGED=YES; MERGE=NO.
