# W2.6-D9R2D-QWEN3-GATE-PREP

Historical PREP record. The subsequent [Research Lead-audited real result](w2_qwen3_external_gate_result.md)
is **GATE_FAIL**, execution **COMPLETED**, with exactly eight native generations:
five canonical SUCCESS, two COORDINATE_ERROR and one SCHEMA_ERROR.
Current grounding is **NOT_PARTICIPATING / SPATIAL_GATE_FAILURE**;
classification remains CANDIDATE and resource KAGGLE_T4X2_VALIDATED_ANCHOR.
Human giant-box review is NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE.
The plan and instructions below preserve the pre-execution milestone; they do
not authorize a rerun. No prompt, parser, decoding, adapter or plan was changed.

Base: `90f36354e16eb66192692b526912e79c2981cce3`.
Branch: `validation/d9-qwen3-external-gate-prep`.
**PREP ONLY.** Tests use fake runtime objects and fake native outputs. No GPU,
weight download, provisioning, real inference, real gate or InspecSafe execution.

## Pinned plan and sources

The separate [Qwen3 gate plan](../configs/pre_freeze/qwen3_external_gate.v1.json)
pins the existing eight cases in order: A_1, A_2, B_1, B_2, C_1, C_2, D_1, D_2.
No case, generator, manifest, provenance or PNG was created, regenerated or edited.

| Input | SHA-256 |
|---|---|
| Gate plan, exact file bytes | `c7510570f553f3267e65f751b56193a337d3c370dd5c4db45da4d746711888c4` |
| Existing Qwen3 smoke plan, LF source bytes | `ecd34ba5a8880458734e26f2bf0932f5f820607c2b9f3233b4e092980bf79ef9` |
| Frozen manifest, exact bytes | `fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379` |
| Frozen provenance, exact bytes | `0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96` |

The new plan is forced to LF by `.gitattributes`; its SHA is a normal file hash,
not a canonical JSON hash. Existing smoke/protected text is hashed after CRLF-to-LF
conversion for cross-platform checkout equivalence. Image and raw-output hashes
always cover exact bytes. The smoke plan's LF hash matches the audited Linux run.

Model: `Qwen/Qwen3-VL-8B-Instruct`, revision
`0c351dd01ed87e9c1b53cbc748cba10e6187ff3b`.
Resource contract comes unchanged from
[`qwen_kaggle_smoke.v1.json`](../configs/pre_freeze/qwen_kaggle_smoke.v1.json):
KAGGLE / T4_X2 / FP16 / NONE / device placement `auto` /
`official_processor` / attention `native_default` / Transformers `4.57.1`.
No Qwen2.5 processor caps, qwen-vl-utils, single-device map or explicit SDPA
override is applied. SDPA was the observed Qwen3 native default in the audited run.
Placement inspection reuses Qwen3 smoke policy, including CPU/single-used-GPU
review notes and rejection of disk offload; it does not rewrite placement.

Decoding is exactly the smoke plan's `decoding`:
`{"do_sample": false, "max_new_tokens": 32}`. No tuning or output-based selection.
Software pins come from the existing
[audited smoke summary](../configs/pre_freeze/qwen_kaggle_smoke_result.v1.json):
Python 3.12.13, torch 2.10.0+cu128, CUDA runtime 12.8, Transformers 4.57.1,
accelerate 1.11.0, huggingface_hub 0.36.0, safetensors 0.6.2,
Pillow 11.3.0, zlib 1.2.11. These are existing observations, not new validation.

## Execution and evidence contract

[`scripts/w2_qwen3_external_gate.py`](../scripts/w2_qwen3_external_gate.py)
verifies the plan hashes, protected sources, model revision, exact manifest and
provenance, all eight image hashes and PNG 256x256 dimensions, reciprocal cases,
case order and per-case prompt hashes before creating the runner. Prompts come
only from `probe_request(..., case.target_query)` with
`external-target-draft-v1`. No prompt changes.

Preflight also requires an explicitly supplied exact 40-character execution commit
and clean Git status including untracked files (ignored runtime artifacts are
allowed), Linux x86_64, the Kaggle `KAGGLE_KERNEL_RUN_TYPE` environment marker,
the exact software pins and two T4s via existing Qwen3 hardware helpers. The Kaggle
marker is an environment check, not remote platform attestation.

Snapshot resolution and four weight-shard SHA/size checks reuse
`provision_qwen3vl_snapshot.cached_snapshot(..., offline=True)`, `weight_files`
and `verify_weights`. The snapshot directory must match the exact revision.
Three additional existing documentary hashes from
`local_model_provenance.d9.json#sources` verify `config.json`,
`preprocessor_config.json` and `generation_config.json`. No hashes are invented.
This verifies four shards and those three configs; other snapshot files are
resolved at the same pinned revision but do not have independent byte hashes in
this plan. No local snapshot bytes were inspected or verified in PREP.

The complete path has one runner instance, one initialize, one load and exactly
eight sequential native generations. A dispatch guard forbids duplicate,
out-of-order and ninth native calls. There is no retry or fallback. Invalid model
JSON is retained and the remaining cases proceed; execution/I/O failures stop
immediately and mark remaining cases unattempted. Exceptions retain stage/type
and native OOM evidence without arbitrary messages, reprs or tracebacks.

For each case: `generate_raw` -> exclusive fsynced `FileRawStore` persistence of
exact bytes with SHA-256 -> read-back byte/size/hash verification -> native
`decoded_for_parser` extraction -> `parse_text(decoded_for_parser, "external_probe")`.
Persistence or verification failure prevents extraction and parsing. Observable
`GenerationFailure.partial_raw` is also preserved and verified, never parsed.
Failures with no observable raw return no fabricated output.

No Markdown stripping, JSON repair, field renaming, regex extraction, coordinate
conversion or reordering is added by the harness. The required existing parser
itself retains its pre-existing `bbox()` clamping semantics; PREP does not change
that parser or reinterpret it as a new range-rejection policy. Fenced JSON remains
JSON_ERROR. `Qwen3VLAdapter` is neither invoked nor edited; its grounding branch
remains UNSUPPORTED / UNCERTAIN_REQUIRES_EXTERNAL_GATE.

Artifacts remain ignored under `data/processed/external_gate/w2_qwen3/<run_id>/`:
run metadata and command/commit, pinned plan/resource condition, environment,
snapshot verification, per-case `response.raw`, pre-parse `metadata.json`,
`result.json`, and summary with artifact hashes plus `summary.json.sha256`.
Metadata links raw to run/case/model/revision, original prompt and hash, image hash,
decoding, software and input provenance. Existing run IDs cannot be overwritten.
Fatal process termination or failure of the evidence filesystem can prevent a
final summary; preserve existing artifacts and never infer a completed gate.

## Human review boundary

The existing `load_cases` and `evaluate_gate(..., reviews=None)` are reused.
Center in target, exclusion of distractor center, non-full-image box and reciprocal
systematic tracking are unchanged. IoU and area remain diagnostic only, with no
thresholds. Automatic statuses are only GATE_FAIL, GATE_PENDING_REVIEW and
GATE_EXECUTION_FAILURE. There is no GATE_PASS or review-input path in this harness.

All automatic checks passing yields GATE_PENDING_REVIEW. A separate task must
perform qualitative giant-box review of all eight cases with explicit reviewer
and rationale, using the existing review/evaluator interface. No roles change
automatically and no fabricated NO_GIANT records are supplied.

## Future execution, separately authorized, NOT_RUN

Use the existing [Qwen3 smoke provisioning policy](w2_qwen_kaggle_smoke_runbook.md)
and exact validated environment. Provision outside the gate process, then set
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`
before launching Python. Runtime reuses the smoke's socket connect/connect_ex/
create_connection denial. This is the existing Python network boundary, not an
OS sandbox. No snapshot download or dependency repair occurs in the gate.

From a clean checkout of the reviewed commit containing this harness:

```sh
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
python scripts/w2_qwen3_external_gate.py --run-id UNIQUE_RUN_ID --expected-commit REVIEWED_40_CHARACTER_COMMIT
```

Keep both T4s visible. If selecting `--cache-dir data/processed/hf-cache`, set
`HF_HUB_CACHE` to that same resolved location before process start. No arbitrary
case list or decoding/resource CLI overrides exist. Do not retry or tune after
observing outputs. Exit 0 means pending human review only; other statuses exit 1.

## Status and validation

QWEN3_RESOURCE: PASS_VALIDATED / KAGGLE_T4X2_VALIDATED_ANCHOR.
QWEN3_CLASSIFICATION: CANDIDATE.
QWEN3_GROUNDING: PENDING_SYNTHETIC_GATE (roster remains
DOC_SUPPORTED_PENDING_SYNTHETIC_GATE).
QWEN3_EXTERNAL_GATE_HARNESS: PREPARED.
QWEN3_EXTERNAL_GATE_EXECUTION: NOT_RUN. INSPECSAFE: NOT_RUN.
`protocol_freeze_commit_sha: PENDING`.

Validation: **56 fake harness tests PASS**, included in **850/850 full-suite PASS**
with `.venv/Scripts/python.exe -m unittest discover -s tests -q`.
The focused command is
`.venv/Scripts/python.exe -m unittest tests.test_qwen3_external_gate -q`.
Python compilation, plan/asset hash verification and `git diff --check` pass.
All 22 protected source/config/fixture paths are unchanged against the exact base.
The source allowlist adds only the newly authorized Qwen3 harness. An initial
848-test run failed only that old allowlist; after its update and two further
failure-path tests, all 850 pass. Test guards forbid real ML imports and socket
access; fake outputs do not establish grounding capability.
No real experiment is added to EXPERIMENTS.md. Dataset/split/label/metric
definitions and protocol decisions remain unchanged.
