# D9R25 P2 production harness (2026-10-06)

Stacked on exact PR C HEAD `ac8825e7d0e21e437fda044cadc3aa8b4fc8f508`.
Status: `IMPLEMENTED_OFFLINE_SYNTHETIC_ONLY`. This is infrastructure and synthetic
validation, not a benchmark run, model qualification, or permission to execute.
P1 official-test baseline replication is separate and is not implemented here.

## Authority and identities

The current `production_run` raises
`NO_INSPECSAFE_INFERENCE_BEFORE_PROTOCOL_FREEZE` before dataset access, backend
factory construction or model load. No CLI flag, environment setting, caller
authority object, alternate freeze path, or developer bypass is accepted.
`configs/pre_freeze/d9r25_harness_contract.v1.json` keeps both freezes PENDING and
InspecSafe authorization false. A caller-created FROZEN JSON cannot open this gate.

The future gate contract requires a reviewed release plus a committed authority
at `configs/frozen/p2_execution_authority.v1.json`, read from executing HEAD using
Git, not an untracked local file. That authority must identify Research Lead,
FROZEN status, explicit authorization, an immutable ancestor freeze commit, exact
P2 dataset identity/count, and all D9R22/D9R23/C1/D9R24 hashes. The freeze commit
pins artifact bytes; a later authority commit records its SHA, avoiding a
self-referencing commit. Between freeze commit and execution HEAD only that
authority file may differ; changed executable code requires a new freeze.
Dirty tracked execution checkouts fail closed. There is
no such authority created by D9R25. Software cannot authenticate a human author
from a self-asserted JSON field: reviewed Git history remains the trust boundary.

The historical D9R23 adapter remains offline-only and byte-unchanged. D9R25 uses
its same strict native validators and additional Qwen condition checks behind
durable storage and the harness authority gate, with a separately versioned
adapter. No real input is relabelled synthetic. D9R22/23/24 identity hashes use
repository LF JSON bytes (CRLF checkout normalization only); the C1 prompt uses
its exact raw-byte SHA. The four-model registry comes from D9R23; no fifth model.

## Dataset and inference firewall

`verify_dataset(root, manifest, provenance)` implements the original W1 contract:
5013 unique image samples, original CSV schema, source manifest SHA
`3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`, and fingerprint
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`.
Sources: `notes/manifest_builder.md`, `safeshift/data/manifest.py`. Pinning the
exact original CSV also prevents silent changes to labels, splits or point IDs.
Re-serialization requires an explicitly reviewed manifest revision.

The physical root is owner-supplied. The fingerprint preserves the historical
logical namespace `data/raw/InspecSafe-V1`, triplet jpg/json/txt order, full-byte
hashes, modality-presence bit and original traversal. It is not a hash of image
bytes alone or a hash supplied without verification. Paths must remain below
the root without traversal, symlinks or junction aliases; all image hashes are
rechecked at dispatch. No dataset copy or private manifest is versioned.

Preflight hashes annotation/TXT bytes but does not decode them into model input.
It projects only `sample_id`, safe image locator and image SHA into execution
records; extra fields, including GT/hazards, are rejected. Sample IDs may contain
original naming information but are operational only, never sent to the model.
Backend `generate` receives only image bytes and the exact fixed C1 prompt.
Backend `load` receives D9R23 execution conditions, not sample/evaluation data.

## Backend and synthetic boundary

The public `production_run` accepts operational inputs only. It has no backend,
factory or generation callback parameter. The internal versioned registry
`d9r25-production-backend-binding-v1` binds exactly `qwen3`, `qwen2_5`, `internvl3`
and `moondream` to `PENDING_D9R26_SOURCE_BACKED_BRIDGE`. Current internal resolution
fails with `PRODUCTION_BACKEND_BRIDGE_NOT_FROZEN`, after authorization, dataset,
shard and prior-attempt checks, before any backend load or run reservation.
Fake dependency injection is confined to the private executor/tests.

The future bound-backend interface is `load(condition)`, `observe()` and
`generate(image_bytes=..., prompt=...)`. Its observation must match the exact
D9R23 software/hardware contract; unknown observation fields are rejected.
Generation returns the complete losslessly serialized native envelope as bytes
or UTF-8 text. Native runner integration and actual environment observations
remain unexecuted; no model library is imported or downloaded by the harness.
Self-reported observation metadata alone is not scientific model binding.
D9R26 must reuse the existing validated native runners for the exact four
source-backed bridges, without duplicating model inference/loader code, and add
static/fake integration tests. No model execution in Codex is authorized. This
pending integration is not a runtime qualification failure.

`rehearse` is a separate entrypoint: images are generated 1x1 PNGs and the backend
must be the built-in `ScriptedBackend`. It accepts neither image paths/dataset
roots nor arbitrary backend callbacks. Scripted outputs can be native bytes,
text or `GenerationFailure` with optional partial bytes. Observations are
explicitly SIMULATED. It cannot become a real-image execution bypass.

For rehearsal, `repo` names the actual Git source/config root; its own HEAD is
recorded in run and call metadata. It must be a Git repository root. There is no
fallback to this module's ROOT or to the current working directory. Optional
`artifact_repo` names a separate storage root, under which the usual relative
`data/processed/benchmark/p2/...` layout is used. Temporary output directories
are never passed off as source repositories. Tests cover an independent Git
source commit A and two temporary storage roots from another working directory.

## Artifacts and scientific attempts

Artifacts live in ignored repository-relative
`data/processed/benchmark/p2/<model>/<run_id>/`. A new directory is exclusively
reserved before load. `run_manifest.json`, `environment.json`,
`execution_manifest.json`, `shard_manifest.json`, `run_status.json` are separate.
Calls use SHA-256 of opaque sample IDs as directory names and preserve sample ID
and `call1` in metadata. Each call has an immutable attempt record, raw response,
metadata and parsed record. No source image is copied into artifacts.

Raw publication writes/fsyncs a same-directory temporary file, then uses an
exclusive hard link to publish complete bytes. Unsupported filesystems fail
closed; existing destinations are never replaced. A reread must match SHA-256
and byte size before parser dispatch, which independently re-verifies the raw.
The local artifact directory must be trusted against hostile concurrent edits;
these checks are not an OS sandbox or an authenticity signature.

Provenance records model/revision, prompt/hash, policy identity, git commit,
adapter/parser, decoding/preprocessing/precision/quantization, software/hardware,
image hash, shard identity, timestamps, termination stage, sanitized cause,
raw receipt and parse status. Exception messages, env dumps and credentials are
not recorded. Raw native responses remain local and are never embedded in exports.

INVALID is a completed call with null canonical label, never Level04. There is
no semantic retry, repair or fallback. Generation failures preserve any received
partial raw without parsing; absence of response never fabricates bytes. A
runtime/persistence failure stops the shard. Remaining samples are NOT_ATTEMPTED.
FAILED runtime calls are not silently treated as parse INVALID in metric input.
An uncatchable termination may leave an attempt marker without final status;
export then fails closed. Partial files are evidence, never grounds for overwrite.

Resume under the same run ID is deliberately rejected, including failed runs.
Rerun requires a new ID, exact prior run-manifest SHA and Research Lead authority
in the committed freeze manifest's `reruns` list. Current real reruns remain
blocked. No heuristic retry of failed answers is implemented.
Selecting a fresh run ID without a rerun reference also fails if this model has
already attempted any selected sample. Multiple overlapping previous runs fail
closed rather than guessing a rerun relation. Truly NOT_ATTEMPTED images may be
assigned to a new shard/run. Existing artifact directories must remain available
for this local attempt-history check; moving/deleting them is outside the harness
contract and cannot be used to claim a first attempt.

## Shards, export and evaluation

`sample-id-lexical-modulo-v1` sorts sample IDs and assigns stable index modulo
shard count, independent of all labels/predictions. Different shards use distinct
run IDs. The immutable shard manifest records count/index, ordered cohort and
shard IDs, source manifest hash and its own hash. No GT-based ordering occurs.

`export_predictions(run_root)` accepts COMPLETED shards only, validates the
artifact hash index and raw receipts, and emits deterministic label-free tables.
`align_four_models(exports)` requires all shards for each of the four models,
same exact protocol/cohort, no duplicate image/model, no missing shard, and no
runtime-failed calls. A 5013-image check applies to InspecSafe tables. Synthetic
tables carry a distinct identity and cannot be mixed with InspecSafe tables.

Only `join_evaluation(exports, evaluation_records)` accepts GT, folder domain,
split, point ID and atom memberships, after full alignment. It returns D9R24
`DisagreementSample` objects plus retained evaluation metadata (including split).
A-G summaries derive from unchanged D9R24 atom mapping; no memberships enter the
prompt. No metric calculation runs inside the inference harness. The export API
is the deterministic programmatic entrypoint; no execution CLI is introduced.

## Current readiness

`RAW_BEFORE_PARSE=ENFORCED`; `NO_GT_LEAKAGE=ENFORCED_BY_CONTRACT_AND_TESTS`;
`DETERMINISTIC_SHARDING=IMPLEMENTED`.
`MODEL_GPU_EXECUTION=NO`; `INSPECSAFE=NOT_RUN`;
`inspecsafe_inference_authorized=false`; `PROTOCOL_FREEZE=PENDING`;
`IMPLEMENTATION_FREEZE=PENDING`. Grounding remains deferred.
`PRODUCTION_BACKEND_BINDING=FAIL_CLOSED_PENDING_D9R26_SOURCE_BACKED_BRIDGES`;
caller backend injection is FORBIDDEN.
Next separately authorized task: D9R26 rehearsal/runbooks/freeze candidate.
No D9R26 work is performed here.

## Validation (2026-10-06)

- Focused: `python -m unittest tests.test_d9r25_harness -v`: **40/40 PASS**.
- Focused plus D9R22/D9R23/D9R24, manifest, local-runner/raw-persistence and
  pre-freeze/firewall regressions: **219/219 PASS**. Command:
  `python -m unittest tests.test_d9r25_harness tests.test_d9r22_seminar_scope tests.test_d9r23_classification_contract tests.test_d9r24_metrics tests.test_manifest tests.test_local_runners tests.test_pre_freeze -v`.
- Full discovery: `python -m unittest discover -v`. Exact BASE
  `ac8825e7d0e21e437fda044cadc3aa8b4fc8f508`: **1533 tests, 4 failures,
  2 errors, 2 skips**. HEAD: **1573 tests, 4 failures, 2 errors, 2 skips**.
  Full suite is **NOT PASS**. Same six failure/error identities, none added or
  removed: `NEW_FAILURE_IDENTITIES_VS_BASE=0`.
- Both ran with the same installed Python/dependencies. The isolated BASE
  worktree matched HEAD's per-file LF/CRLF checkout conventions; canonical BASE
  contents were unchanged. The earlier unmatched-newline diagnostic runs are
  not the comparison reported above. Torch is absent in this environment;
  no dependency/model installation or download was performed.
- `git diff --check` and `git diff --cached --check`: PASS. Staged files contain
  no dataset, weights, native responses, local manifests or private paths.

Historical failures (left unchanged):

1. `tests.test_d9_t4_roster_revision.D9T4RosterRevisionTests.test_23_only_explicitly_authorized_post_d9r1_runner_source`
2. `tests.test_d9r18_final_participation_decision.FinalParticipationTests.test_only_explicit_decision_documentation_and_test_files_change`
3. `tests.test_ovis_gpu_smoke_result.OvisSmokeResultTests.test_research_claims_grounding_and_checklist_remain_pending`
4. `tests.test_qwen_kaggle_smoke_result.SmokeResultTests.test_claims_grounding_and_checklist_boundaries`

Historical/environment errors:

1. `tests.test_grounding_multicategory_runtime_v3.ContractTests.test_dry_preflight_blocks_without_authority`
   (`MAIN_IDENTITY_CHANGED_RESEARCH_LEAD_REQUIRED`, old main identity guard).
2. `unittest.loader._FailedTest.tests.test_moondream_precision`
   (`ModuleNotFoundError: torch`, at test-module import).

Only D9R22/D9R23 scope-test allowlists were extended for the explicit D9R25
files; no active scientific contract or unrelated failing test was rewritten.

## Backend-binding correction (2026-10-06)

Research Lead identified a production integrity gap in the original PR #82
head `2aa5a0a731a1c84b48be503184dfdf21690bed1c`: callers could supply a fake
backend after freeze. This correction removes that public choice and adds the
internal pending registry described above. It also corrects rehearsal source
provenance rather than borrowing ROOT's SHA for a different repo. The preceding
validation record describes the original implementation; correction-specific
same-environment BASE/HEAD evidence follows separately.

Correction validation: focused **45/45 PASS**; the same regression command
listed above **224/224 PASS**. `python -m unittest discover -v` was rerun on
exact BASE `ac8825e7d0e21e437fda044cadc3aa8b4fc8f508` and corrected HEAD using
the same Python/dependency state and matching per-file checkout newlines.
`BASE_TOTAL=1533`; `HEAD_TOTAL=1578`;
`BASE_FAILURE_ERROR_IDENTITIES=6`; `HEAD_FAILURE_ERROR_IDENTITIES=6`;
`NEW_FAILURE_IDENTITIES_VS_BASE=0`; removed identities=0.
Both runs have 4 failures, 2 errors, 2 skips: exactly the four historical failures
and two historical/environment errors enumerated above. Full suite is NOT PASS.
No inference/runtime dependency was installed, loaded or executed. Counts are
specific to this environment (torch absent), not an assertion about older runs.
`git diff --check` and `git diff --cached --check` pass.
