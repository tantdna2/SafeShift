# W2.6-D9R2C-GATE-PREP — Frozen external gate execution preparation

Base: `c967969e31566288917c0aa56f402ab4a45730f3`.
Branch: `validation/d9-qwen2_5-external-gate-prep`.
**PREP ONLY: no real model output observed, no GPU/model load, no real gate result.**
All model outputs used by tests are fake. The eight cases predate this task; no
case was designed, regenerated or tuned. No InspecSafe content is used.

## Pinned inputs and execution plan

The [gate plan](../configs/pre_freeze/qwen2_5_external_gate.v1.json) is separate
from the unchanged runtime qualification plan. Canonical plan hashes use UTF-8
JSON with sorted keys, separators `(',', ':')`, and `allow_nan=False` (no newline).
Manifest/provenance/image hashes cover exact file bytes, as in frozen provenance.
Protected Python source hashes normalize CRLF to LF for Windows/Linux checkouts.

| Pin | Value |
|---|---|
| Gate plan SHA-256 | `d7e09c1400e23a534b97e91aa432d87108ece137ff60f8a918e3c0f977f2bb4b` |
| Runtime plan SHA-256 | `aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb` |
| Manifest SHA-256 | `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379` |
| Provenance SHA-256 | `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96` |
| Suite / source statement | `synthetic-v1` / `NO_INSPECSAFE_CONTENT_USED` |
| Case order | `A_1, A_2, B_1, B_2, C_1, C_2, D_1, D_2` |
| Prompt version | `external-target-draft-v1` |
| Decoding | `{"do_sample": false, "max_new_tokens": 32}` |
| Decoding provenance | `PRE_EXISTING_RUNTIME_DECODING_REUSED_PRE_GATE` |

Decoding is copied exactly from `qwen2_5_t4_runtime.v1.json#smoke.decoding`;
no new generation values are selected. `probe_request(...)` renders the existing
target query and coordinate instruction without edits. Each rendered prompt SHA
is pinned in the gate plan and checked again before loading. The harness pins the
canonical plan hash; changing this plan after audit requires a separately reviewed
revision before execution. This is gate execution pinning, not protocol freeze.

Model/revision remain `Qwen/Qwen2.5-VL-3B-Instruct` /
`66285546d2b821cf421d4f5eb2576359d3770cd3`. Single Tesla T4 / FP16 / SDPA / NONE /
batch 1 / cuda:0, no CPU/disk offload, caps 200704/1003520 and exact software pins
are inherited unchanged from the PASS_VALIDATED runtime plan.

## Harness and evidence contract

`scripts/w2_qwen2_5_external_gate.py` verifies the gate/runtime plans, fixed manifest
and provenance hashes, exact eight image paths/hashes, PNG 256x256 dimensions,
case order and reciprocal swaps via `load_cases` before any runner/backend/model
load. Verified image bytes are held for those requests; no dataset path input is
accepted. The reviewed exact Git commit and clean tracked worktree are required.
It reuses the smoke's offline variables, socket denial, software/hardware checks,
snapshot verify-only path, placement gate, visual observations and memory helpers.
It never provisions or downloads a snapshot.

One runner initializes once and loads once. A complete run dispatches exactly
eight native generations sequentially, with a per-case dispatch guard preventing
duplicates or a ninth call. There is no retry. Invalid strict parses still allow
all eight cases to execute and lead to GATE_FAIL. A runtime/I/O/OOM failure stops
execution, records the failed case and remaining `not_attempted_case_ids`, and
returns GATE_EXECUTION_FAILURE; it cannot masquerade as a completed eight-case run.
OOM remains identified through the existing exception cause-chain logic. Evidence
includes safe error types/substages, never exception messages/repr/tracebacks.

The harness-owned `ProbeInput` carries in-memory bytes, the exact prompt and the
`external_probe` task to the existing task-agnostic prepare/generate primitives.
It does not add a production Task enum or adapter branch. The Qwen2.5 production
adapter is neither invoked nor changed; grounding remains UNSUPPORTED there.

For every case: prepare once, generate once, persist exact raw bytes and SHA using
FileRawStore's exclusive/fsynced writer, verify the saved hash, then inspect the
versioned native envelope and call `parse_text(decoded_for_parser, "external_probe")`.
No stripping, extraction, normalization heuristic or repair is added. Fenced JSON
remains a strict JSON_ERROR. Post-generate GenerationFailure.partial_raw is retained;
pre-observable failures never fabricate raw. Raw remains primary evidence.

Exclusive output: `data/processed/external_gate/w2_qwen2_5/<run_id>/`:

- `run_metadata.json`: execution commit, timestamps, immutable plan/hashes, model,
  resource condition, original decoding and prompt pins.
- `environment.json`, `snapshot_manifest.json`: validated runtime observations.
- `<case_id>/response.raw`, `metadata.json`, `result.json`: exact raw/hash, image
  and prompt hashes, decoded parser text, strict status, valid bbox, GT boxes and
  memory/visual observations. Partial failed cases may have raw/metadata only.
- `summary.json`, `summary.json.sha256`: artifact hashes, case records, native
  errors, gate case diagnostics and systematic tracking. Run IDs never overwrite.

## Gate decision and required human review

The harness calls the unchanged `evaluate_gate(repo, cases, predictions, reviews=None)`.
Schema, center-in-target, distractor-center exclusion, non-full-image box and
reciprocal tracking requirements remain unchanged. IoU and area are diagnostics
only: neither is thresholded. Output statuses are GATE_EXECUTION_FAILURE, GATE_FAIL
or GATE_PENDING_REVIEW. The harness has no automatic GATE_PASS path or review input.

If all automatic conditions pass, the result remains **GATE_PENDING_REVIEW**.
Research Lead/auditor must separately inspect each raw prediction and image with
target/distractor locations, qualitatively assess whether the box is giant, and
supply eight explicit `GiantBoxReview` records with reviewer/rationale. Use only
the existing NO_GIANT / GIANT / PENDING statuses, with no invented area boundary.
Only an offline audit using the existing evaluator with eight explicit NO_GIANT
reviews and passing automatic criteria can yield PASS; a missing review remains
pending and GIANT fails. A gate result itself never mutates production roles.

## Future separately authorized execution — NOT_RUN

Use the already qualified pinned environment and an independently provisioned,
verified exact snapshot. Before Python starts, set the existing offline flags:

```sh
export CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_ENABLE_HF_TRANSFER=0
python scripts/w2_qwen2_5_external_gate.py --run-id <unique-run-id> --expected-commit <reviewed-40-character-commit>
```

Use the reviewed commit containing this harness, not the pre-PREP base or a
mutable ref. If using `--cache-dir`, set matching HF_HUB_CACHE before starting.
No prompt/decoding/output-based retry is permitted. Exit 0 means pending human
review only, never gate PASS; other statuses exit 1.

QWEN2_5_RESOURCE: **PASS_VALIDATED**. EXTERNAL_GATE_HARNESS: **PREPARED**.
EXTERNAL_8_CASE_EXECUTION and GIANT_BOX_REVIEW: **NOT_RUN**.
GROUNDING_QUALIFICATION: **NOT_YET_QUALIFIED**. CLASSIFICATION: **CANDIDATE**.
INSPECSAFE: **NOT_RUN**. `protocol_freeze_commit_sha: PENDING`.

## Offline validation

New fake harness tests: **36 PASS**. Regressions: roster **33**, runner **73**,
runtime PREP **58**, load diagnostics **15**, initialize diagnostics **20** PASS.
Full suite: **786 PASS**. Harness `py_compile`, JSON validation for gate/runtime
plans and frozen manifest/provenance, and `git diff --check` PASS. The roster source
allowlist adds only this authorized script; existing protected hashes remain intact.
All specified production files, generator, manifest/provenance and eight PNGs are
unchanged against exact base. Census stays untracked/untouched with SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
