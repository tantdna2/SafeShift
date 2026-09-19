# Pre-freeze implementation

Authoritative base: `main` at `ec40d9080f8c6847355ec22cc5bad54ea1dda876`.
Implementation branch: `implementation/pre-freeze`. D8 is approved; **D8 approval != protocol freeze**.
`protocol_freeze_commit_sha: PENDING`.

Scope follows [D8](../DECISIONS.md#dec-w2-d8-008),
[D5](w2_metrics_statistics_decision_brief.md), and
[D6 vocabulary/support definitions](w2_grounding_census_decision_brief.md).
No dataset, split, label or D5 formula was changed. No web/provider calls, model-output
inspection, InspecSafe inference or prompt tuning occurred. No secrets are required.

## Approved eight-item checklist

These are the eight prerequisites in [D8 section 34](w2_model_prompt_interface_decision_brief.md#34-pre-freeze-implementation-checklist-danh-sách-kiểm-tra-triển-khai-trước-đóng-băng-giao-thức).
An implemented interface is not evidence that its freeze prerequisite is complete.

| # | Approved prerequisite | Status | Evidence / remaining work |
|---|---|---|---|
| 1 | Exact Qwen Singapore workspace endpoint | PENDING | Region `ap-southeast-1` and `ROUTE_REGION_PINNED`; endpoint `UNRESOLVED / REQUIRED BEFORE FREEZE`. No WorkspaceId invented. |
| 2 | One supported Qwen decoding configuration | PENDING | `QWEN_DECODING_PENDING_ROUTE_CONFIRMATION`; precision `UNDISCLOSED_BY_PROVIDER`; `HOSTED_BACKEND_NOT_FULLY_PINNABLE`. |
| 3 | Prepare and freeze external Target+Distractor cases | PENDING | External case **format DONE**; external live/frozen cases **PENDING**. Example paths are placeholders; no image collection has been frozen. |
| 4 | Execute external capability gates for Level-3 models | PENDING | GPT gate **NOT RUN**; Claude gate **NOT RUN**. Dummy geometry tests are not provider capability evidence. |
| 5 | Assign final grounding eligibility and model roles | PENDING | Preserve D8 evidence assignments: Gemini/Qwen Level 1; GPT/Claude Level 3, grounding `NOT PARTICIPATING` pending a qualifying gate. |
| 6 | Verify exact model IDs and serving routes on live APIs | PENDING | IDs are copied from approved D8. Availability, wire formats and routes have not been checked live. |
| 7 | Freeze prompts, schema, adapters, parsers and metric engine | PENDING | Offline interfaces, schemas, adapter/parser tests **DONE**. Prompt drafts and metric contracts are versioned; final policies, live route integration and full D5 engine remain pending. |
| 8 | Record protocol freeze commit | PENDING | `protocol_freeze_commit_sha: PENDING`. Implementation commit is not a freeze commit. |

No item is marked BLOCKED: the remaining work is intentionally outside this offline task.

## Implemented contracts

- `safeshift/protocol/prompts.py`: Call 1 accepts image path + caller-supplied industry safety policy and requests only `safety_level`. Call 2 accepts image path + exactly the D6 closed 12-hazard vocabulary; its signature has no Call 1 output/history argument. Call 1 likewise has no Call 2 input. Exact industry policy text must still be pinned before freeze; no substitute safety policy was invented.
- `schemas/canonical.schema.json` and `schema.py`: canonical x-first `[xmin, ymin, xmax, ymax]`, normalized `[0,1]`, top-left origin. Python enforces strict coordinate inequalities in addition to JSON Schema. Extra task fields, unknown hazard IDs, duplicate JSON keys, non-finite values, string/bool coordinates and malformed JSON are rejected. Empty hazard/evidence arrays are retained as valid explicit outputs; missing evidence does not imply localization success.
- `adapters.py`: Gemini, Qwen DashScope, OpenAI and Anthropic offline skeletons. `prepare()` renders the provider coordinate convention; `extract_text()` supports explicitly selected handcrafted envelope contracts. Gemini y-first/1000 and Qwen x-first/1000 are reordered/scaled deterministically. OpenAI/Anthropic use canonical coordinates. There is no inference transport: every `send()` raises `OFFLINE_ONLY`. Qwen's compatible-chat envelope is a skeleton assumption awaiting route confirmation.
- `records.py`: `preserve_and_parse()` writes unchanged response bytes and metadata before extracting provider text or parsing. Metadata links run/sample/call IDs, image checksum, exact rendered prompt/hash, provider/model/version, endpoint, SDK, generation configuration, Git SHA and environment. Artifacts are local under `data/processed/`; existing call directories cannot be overwritten. Persistence failures abort parsing. This pre-freeze entrypoint accepts only `handcrafted_dummy` provenance.
- `metrics.py`: D5 interfaces for image-level classification, GT RQ2 atom lookups, complete Call 2 predictions, Direct/Weak Proxy candidate original polygons, explicit unsupported atoms and parse metadata. A missing membership raises an error; it is not treated as an empty/normal sample. Direct and Proxy support stay separate. Nonparticipants have no synthetic zero-score result. No metric formulas or tuned thresholds are implemented.
- `configs/pre_freeze/providers.json` and `freeze_manifest.template.json`: model/route placeholders and explicit pending freeze state. API key and endpoint environment variable **names** only; credentials are never loaded or embedded. Decoding fields describe approved policy, not verified SDK request kwargs.

Implementation follows approved D8 section 16 deterministic coordinate normalization:
provider-native reorder/scale, then clamp each coordinate to `[0,1]`, then strict
geometry validation (`xmin < xmax`, `ymin < ymax`). This applies to `xyxy_1`,
`xyxy_1000` and `yxyx_1000`. Clamping does not modify the stored raw response.
No sorting, coordinate-convention inference or semantic repair is performed;
reversed boxes and boxes that become degenerate after clamping remain invalid.
Mixed valid/invalid boxes yield `COORDINATE_ERROR`, with no successful canonical
response. Valid items survive only in `diagnostic_evidence`. `response_schema_valid`,
`boxes_attempted` (unknown = `null`) and `boxes_valid` support separate D5 response/box
parse diagnostics. End-to-end consumers must not promote diagnostics into success.

For future offline integration, build each request independently, call its adapter's
`prepare()` once, then pass that exact prepared request, unmodified dummy response
bytes and `CallMetadata` to `preserve_and_parse()`. Each attempt needs a new call ID.
The low-level `parse_text()` is a pure parser for already-persisted dummy strings;
future live ingestion must preserve the full raw response before calling it.

## External capability harness and firewall

`schemas/external_cases.schema.json` defines case ID, repository-relative image path,
target/distractor GT bboxes, target query, source provenance and swap group.
`tests/fixtures/pre_freeze/external_cases.example.json` is a small handcrafted format
example. It contains no embedded images or benchmark data. Format validation does
not assert that placeholder images exist, have verified licensing/checksums, or are
ready for a live gate; those checks belong to final case preparation.

`gate.py` validates separated target/distractor geometry, unique case IDs, fixed query
within each group and reciprocal target/distractor swaps on distinct image paths.
Every supplied case must pass: valid single-box schema, predicted center inside
target, exclusion of distractor center, movement following target positions, and no
giant/full-image behavior. Boundaries count as inside, including distractor exclusion.
Missing/malformed responses fail; unknown case IDs raise rather than being dropped.
IoU and predicted area are descriptive fields only, never pass/fail thresholds.

Full-image boxes are automatically rejected. Because D8 gives no numeric definition
of "near full-image / giant", a separate `GiantBoxReview` records `NO_GIANT`, `GIANT`
or `PENDING`, reviewer and rationale. Automated checks passing without that review
return `PENDING_REVIEW`, never PASS. This preserves the qualitative approved criterion
without inventing an area cutoff. The review procedure and actual cases still need
to be fixed before the live gate. A harness result does not update model roles.

`firewall.py` guards every new development CLI input, embedded case image path,
request builder, adapter preparation and artifact path before reading/writing inputs.
It rejects raw-dataset paths, case/separator variants, absolute paths, parent traversal
and resolved symlink/junction aliases into raw data or outside the repository.
The protected repository root is application-supplied, not manifest-controlled.
This detects paths, not copied/relabelled benchmark content; external provenance
review remains required. Existing W1 audit commands are unchanged and are not
pre-freeze capability/development entrypoints.

## Offline verification and reproduction

Run from repository root using the existing environment (Python 3.11.9, Pillow 12.3.0;
no new dependency). No random sampling is used in the new tests; seed is not applicable.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe scripts/pre_freeze.py validate-cases --manifest tests/fixtures/pre_freeze/external_cases.example.json
.\.venv\Scripts\python.exe scripts/pre_freeze.py replay-dummy-gate --manifest tests/fixtures/pre_freeze/external_cases.example.json --responses tests/fixtures/pre_freeze/dummy_predictions.json
git diff --check
```

Validation on 2026-09-18: **199/199 repository tests passed**, including **54 new
offline tests**. Coverage includes independent inputs, all four handcrafted provider
envelopes, native coordinate conversion, malformed/partial/empty outputs, preservation
before parsing, write failures and overwrite rejection, gate tracking/distractor/full-image
behavior, qualitative-review pending state, firewall paths and D5 consumer contracts.
Initial `python` invocation lacked Pillow and produced four test-import errors;
rerunning with the existing `.venv` resolved this without installation/network access.
Dummy CLI replay is explicitly labelled `handcrafted_dummy`, `live_gate: NOT RUN`.
Temporary test artifacts are synthetic and cleaned up; no benchmark artifacts are read.

D8 normalization correction verified on 2026-09-19: **205/205 repository tests
passed** using the same `.venv`, including six added regression tests for clamping
and invalid coordinates. Raw-preservation tests also cover clamped provider outputs.
`git diff --check` passed. Approved D8 and all other protocol policies are unchanged.

Not run: GPT/Claude live gates, provider/model availability verification, InspecSafe
inference, paid API calls, complete D5 metric evaluation and protocol freeze. These
are outside this task. The versioned source tree identifies the implementation commit;
when materializing the freeze template later, fill `git_commit_sha` from the reviewed
implementation revision while keeping the separate freeze SHA pending until approval.
