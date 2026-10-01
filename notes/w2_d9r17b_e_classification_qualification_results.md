# D9R17B–E — four classification qualification results

Task: `W2.6-D9R17B-E-FOUR-MODEL-CLASSIFICATION-QUALIFICATION-RESULTS`.
Recording date: 2026-10-01. Recording BASE and all four execution commits:
`3ad16f48da4f9ef5910dedede9a4ba950f268b7a`.

The Research Lead / ChatGPT directly inspected the four uploaded ZIP bundles,
recomputed their SHA256, read raw/metadata/result/runtime evidence and checked
it against the exact GitHub execution commit. This note and the
[combined record](../configs/pre_freeze/d9r17b_e_classification_qualification_results.v1.json)
transcribe those supplied findings. **Codex did not independently inspect or
rehash the external bundles.** Codex checks local transcription, prospective
contract consistency and repository preservation only. ZIP bundles, raw files,
weights and full runtime evidence remain outside Git; none are included here.
The earlier Qwen2.5 record is a schema/style reference, not evidence for these runs.

## Supplied execution identities

| Model | Run ID | Completion (UTC) | Execution authorization |
| --- | --- | --- | --- |
| InternVL3 | d9r17b-internvl3-classification | 2026-10-01T07:34:15.526059+00:00 | DEC-W2-D9R17B-INTERNVL3-CLASSIFICATION-QUALIFICATION-EXEC-001 |
| Moondream | d9r17c-moondream-classification | 2026-10-01T07:42:44.055714+00:00 | DEC-W2-D9R17C-MOONDREAM-CLASSIFICATION-QUALIFICATION-EXEC-001 |
| PaliGemma | d9r17d-paligemma-classification | 2026-10-01T08:51:54.551970+00:00 | DEC-W2-D9R17D-PALIGEMMA-CLASSIFICATION-QUALIFICATION-EXEC-001 |
| Qwen3 | d9r17e-qwen3-classification | 2026-10-01T09:04:14.041838+00:00 | DEC-W2-D9R17E-QWEN3-CLASSIFICATION-QUALIFICATION-EXEC-001 |

| Model ID | Immutable revision |
| --- | --- |
| OpenGVLab/InternVL3-2B-hf | cb57a075cb75a2e6d1b668b128d48bb00ae321d2 |
| vikhyatk/moondream2 | 9a7d4024050840e001defacec2b00727e89149e6 |
| google/paligemma-3b-mix-448 | ead2d9a35598cb89119af004f5d023b311d1c4a1 |
| Qwen/Qwen3-VL-8B-Instruct | 0c351dd01ed87e9c1b53cbc748cba10e6187ff3b |

Moondream tokenizer revision: `35192e10a54e36eabe0a7cc57a2c1aab371cafc5`.

| Bundle | SHA256 supplied after Research Lead rehash | Bytes |
| --- | --- | ---: |
| InternVL3 | d8a0c3463f716866a04c38daf40aafccf100e1d99eba9c2f966f6c4ddd5caa3f | 59204 |
| Moondream | 3486de253fb5775d864b54b376ed9f464547b1f796a0551c525580d70366b93c | 92830 |
| PaliGemma | ffb68b11f6a62bd716a81af634ed8fdb412c641d2e4ce08aaf8f224d89092d4c | 59123 |
| Qwen3 | ff1a49b8dc7ca43ca0b401e42ca1485f24651e9da639deb0029ae2bbf6205a69 | 51152 |

All four attempt records carry prospective manifest SHA256
`3b7c3ebdec0736580bbad27f782496e318372cda6c3a4f322c4cc19ca5749e92`
and plan SHA256
`c2e8990227e7378368b986352d88fe6c9975769cdeccda346e3070d321d77160`.
Prompt SHA256 is
`1b6da67a979a7c5bd53af35ce9a65516761da4008a2bb6519438dbd05c687348`
for InternVL3, Moondream and Qwen3; PaliGemma uses
`035ce849df10ef3b14982a8c9106ade8ef8e6889f1bbb7921c7dff08e98dc840`.

## Documentary outcomes

| Model | RUN_STATUS | CAUSES | Parser SUCCESS | Parser INVALID | Exact expected |
| --- | --- | --- | ---: | ---: | ---: |
| InternVL3 | FAIL | SEMANTIC_CLASSIFICATION_FAILURE | 8/8 | 0/8 | 6/8 |
| Moondream | FAIL | SEMANTIC_CLASSIFICATION_FAILURE | 8/8 | 0/8 | 2/8 |
| PaliGemma | FAIL | INTERFACE_OR_FORMAT_FAILURE | 0/8 | 8/8 | 0/8 |
| Qwen3 | PASS | [] | 8/8 | 0/8 | 8/8 |

All four have `RUNTIME_FAILURE=null`. These counts describe only the fixed
eight-case external synthetic qualification. They are not accuracy, an InspecSafe
benchmark or a model ranking. The prospective PASS rule requires all eight
canonical levels to match, in addition to the format/raw/runtime conditions.

| Case | Expected | InternVL3 canonical | Moondream canonical | PaliGemma native decoded_text | PaliGemma canonical | Qwen3 canonical |
| --- | --- | --- | --- | --- | --- | --- |
| cq_01 | Level01 | Level01 | Level01 | `level01` | null / INVALID | Level01 |
| cq_02 | Level01 | Level01 | Level01 | `level01` | null / INVALID | Level01 |
| cq_03 | Level02 | Level02 | Level01 | `blue diamond` | null / INVALID | Level02 |
| cq_04 | Level02 | Level02 | Level01 | `blue diamond` | null / INVALID | Level02 |
| cq_05 | Level03 | Level03 | Level01 | `yellow circle` | null / INVALID | Level03 |
| cq_06 | Level03 | Level03 | Level01 | `yellow circle` | null / INVALID | Level03 |
| cq_07 | Level04 | Level01 | Level01 | `green square` | null / INVALID | Level04 |
| cq_08 | Level04 | Level01 | Level01 | `green square` | null / INVALID | Level04 |

The three non-PaliGemma runs have SUCCESS parsing on every case. Moondream's
native answer is the JSON string `{"safety_level": "Level01"}` on all eight
calls; the supplied multiline form is retained in the record. Its eight raw
files have the same SHA256 and size (136 bytes). Per-case SHA256/byte sizes for
all 32 raw outputs are preserved in the machine-readable record.

PaliGemma native text remains native text. No lowercase normalization, alias,
marker-name mapping or reinterpretation produces a canonical level. It has
zero canonical exact-expected matches and is not a semantic PASS. This result
does not authorize prompt, parser or interface repair.

## Integrity and runtime evidence supplied by the Research Lead

For all 32 calls, the Lead confirms computed response.raw SHA256 and size match
the qualification records; metadata SHA/size match the actual raw; metadata
parse_status before parser is NOT_ATTEMPTED; source_kind is
EXTERNAL_CLASSIFICATION_QUALIFICATION; NOT_INSPECSAFE and NOT_ACCURACY_BENCHMARK
are true; and per-case image SHA matches the prospective manifest. For each
attempt, top-level `result.json` exactly equals `calls/qualification_result.json`.
Paths in that comparison are relative to the execution attempt directory.

Each run has one model load, eight classification calls, zero grounding calls,
FP16 precision and no quantization. InternVL3, Moondream and PaliGemma each use
one Tesla T4; Qwen3 uses exactly two. Every GPU has compute capability [7,5]
and 15636037632 bytes VRAM.

- InternVL3 and PaliGemma: CUDA 12.4, exact snapshot local_bytes_verified=true,
  14 snapshot files and 25 state audit records each; no runtime failure.
- Moondream: query_call_count=8, detect_call_count=0, exact model and tokenizer
  snapshots verified, provision/online/offline manifests matched, state audits
  17/17 VALID and 24 image boundaries; no runtime failure.
- Qwen3: all four weight shards verified; device map uses only GPUs 0 and 1;
  no CPU/disk placement observed. Python 3.12.13, torch 2.10.0+cu128, CUDA 12.8,
  transformers 4.57.1, accelerate 1.11.0, huggingface_hub 0.36.0, safetensors
  0.6.2, pillow 11.3.0 and zlib 1.2.11; no runtime failure.

The record does not invent absent per-shard hashes, software versions or audit
details. Runtime findings retain Research Lead attribution. The no-retry/repair
contract is explicitly sourced to the unchanged prospective plan; recording
these results performs no runtime verification or replay.

## Role and authorization boundaries

For **every** run: MODEL_ROLE_AFTER_RUN=PENDING_RESEARCH_LEAD_REVIEW,
REVIEW_STATUS=PENDING_REVIEW and CLASSIFICATION_PARTICIPATION_DECISION=PENDING.
Qwen3 PASS does not freeze the protocol, promote an adapter, change a roster
role or authorize InspecSafe. FAIL does not remove a model, assign classification
NOT_PARTICIPATING, activate SmolVLM2, initiate repair or trigger a rerun.

Roster membership, backup activation, production promotion, automatic rerun and
real model rerun all remain false. PROTOCOL_FREEZE=PENDING;
INSPECSAFE=NOT_RUN / unauthorized. Model/InspecSafe execution and merge are not
performed by this recording task.

The four protected configs are byte-identical to BASE: prospective plan,
prospective cases, local_models.d9.json and freeze_manifest.d9.template.json.
Historical D9R16 `classification_results=NOT_RUN` and
`execution_authorized_in_prep=false` remain intact. Prompt/parser, runners,
runtime plans, D5, grounding state/history and exploratory grounding policy
remain unchanged.

## Local validation

The initial checkout had one unrelated untracked census manifest. It was left
untouched; this task uses a clean isolated worktree created at the exact BASE.
Local HEAD/main and remote main were verified at BASE before recording. The
BASE suite ran there before edits; the result-branch suite ran in that same
worktree with the same existing Windows validation environment: Python 3.11.9,
Pillow 12.3.0 and zlib 1.3.1. No dependency installation, model loading,
GPU execution, bundle inspection or InspecSafe run was performed.

Commands below use that validation interpreter as `python`, from the worktree
root. No randomness is introduced by the documentary checks.

```text
python -m unittest tests.test_d9r17b_e_classification_qualification_results -q
python -m unittest tests.test_d9r17b_e_classification_qualification_results tests.test_qwen2_5_classification_qualification_result tests.test_classification_qualification -q
python -m unittest discover -s tests -q
git diff --check
git diff --cached --check
```

New focused module: **23/23 PASS**. Expanded focused set: **67/67 PASS**.
Strict JSON loading, execution/model/bundle/raw/prompt pins, descriptive counts,
runtime summaries, pending roles, no retry/repair/rerun, protected byte checks,
and append-only history checks PASS. The pure existing verdict function is
checked without replaying the model or parser against reconstructed raw envelopes.

The earlier D9R17A protection test originally rejected the new result artifact
because its config allowance included only Qwen2.5's artifact. Its sole change
adds the exact new documentary artifact path to that allowance. The new focused
test locks this exact one-path amendment and preserves every other byte of the
older test. No historical BASE failure is repaired or suppressed.

Full suite: **BASE 1,276 tests; result branch 1,299 tests; both 4 failures and
24 errors**. All 28 failure/error identities match, including error/failure
category; no new identity. This is **not a full-suite PASS**. The four existing
failures are the D9R1 runner-source allowlist, historical Moondream protected
roster hash, and Ovis/Qwen smoke checklist expectations. The 24 existing errors
are PaliGemma notebook fresh-kernel guards after discovery imports CPU torch.

Local validation artifacts (ignored, relative to this worktree):
`data/processed/d9r17b-e-validation/base-suite.log`, `head-suite.log` and
`comparison.json`. The comparison parses complete unittest identities across
PowerShell line wraps and verifies identical sorted sets and categories.
Diff checks and the explicit staged file list were reviewed. No protected
implementation or runtime was changed, and no bundle/raw/weight file was staged.
