# W2.6A — Local Runner Contracts

Base main: `c8a60f8a97589714b4b15d3ca13465174ec5b487` (PR #20 / D9 merged).
Branch: `implementation/d9-local-runner-contracts`.
Authority: the W2.6A implementation request, within
[D9](../DECISIONS.md#dec-w2-d9-009--p2-open-weight-self-hosted-model-roster).
The [active D9 checklist](../TASKS.md#w2--active-d9-pre-freeze-checklist-2026-09-20)
was confirmed before implementation. This milestone completes **contract/scaffolding
only**; checklist #2, model-specific execution and all freeze prerequisites remain
`PENDING`. No scientific decision, schema, label, split or metric is changed.

## Contract and ownership

`safeshift/runners/contracts.py` defines backend-neutral `LocalRunner`,
`OutputAdapter`, `RawStore`, `Request`, `RunContext` and `CallResult` contracts.
The core and storage use the Python standard library only, with no Hugging Face,
Transformers, SDK, model roster, dataset loader or metric dependency.

Each `execute_call` follows this sequence:

```text
validate/snapshot provenance
  -> initialize runtime -> load declared model -> prepare this input
  -> generate raw bytes -> preserve bytes AND metadata -> adapt/parse
  -> return canonical value + raw reference + task status + provenance
```

Each request has one task and no prior-call result/history parameter. The caller
builds classification and grounding requests independently. Future backends must
not retain generated history between calls. Loading/caching optimizations and
model-specific preprocessing implementations remain future work.

Task semantics and canonical validation belong to adapters. The dummy adapter
bridges to the **unchanged** `safeshift/protocol/schema.py` types and parser;
the generic core contains no safety-level or hazard-vocabulary logic. The dummy
syntax is handcrafted and establishes no native model format or qualification.
Future P2 integration must use the existing C1/A2/B2 prompt policy and Benchmark
Firewall before obtaining input bytes; this contract is not inference authorization.

## Evidence storage

`FileRawStore` writes only under a repository-relative `data/processed/` directory,
already excluded by `.gitignore`. The repository root is injected by the application.
Opaque run/sample/call IDs are retained in metadata and hashed for the attempt
directory; they are never interpreted as filesystem paths. Absolute paths,
traversal and resolved symlink/junction aliases are rejected for artifact roots.
The store assumes a trusted local filesystem without concurrent hostile link changes.

An exclusive attempt directory contains:

- `response.raw`: exact returned bytes, including native points or malformed text.
- `metadata.json`: pre-parse provenance with `parse_status = NOT_ATTEMPTED`.
- `result.json`: written explicitly with `store.save_result(result)` after return;
  includes the canonical result, final parse/error status and raw reference.

Both raw bytes and metadata are flushed/fsynced before adapter entry. No overwrite
is allowed. A failed or interrupted write leaves evidence in place and stops parsing;
retry with a **new call ID**. Saving a final result never rewrites raw metadata.
Final-result I/O failures propagate; callers must not claim a saved result in that
case. A pre-generation failure has no invented raw output and can still be recorded
with `save_result`. `GenerationFailure(partial_raw=...)` preserves available partial
bytes without parsing them. Backends must surface partial bytes through this contract;
an exception with no returned bytes cannot supply raw evidence.

The provenance snapshot contains run/call/sample/input IDs, input checksum and
caller-supplied source/version metadata; model ID and nullable immutable revision
with revision evidence; runner/adapter/parser versions; task and exact prompt/ID/hash;
decoding and preprocessing configurations; precision and quantization; device and
software/runtime versions; seed, command and Git revision; caller-supplied roles;
UTC timestamp; and raw relative path, SHA-256 and byte count. Final provenance adds
parse and error status. D4 explicitly permits/requires ISO-8601 UTC timestamps;
tests inject a fixed clock. There are no machine-specific paths in built-in metadata.
Caller-supplied metadata must likewise use relative artifact references, contain no
credentials, and accurately describe the eventual runtime.

An absent immutable revision remains `PENDING`. A supplied revision requires an
evidence identifier; obvious mutable aliases are rejected. `RECORDED` means metadata
was supplied, **not** that this infrastructure has verified weight provenance,
access/license, revision immutability or a protocol freeze. Tests use invented
synthetic identifiers solely to exercise this field; no real model revision is pinned.

## Independent status and spatial boundaries

`Roles` holds classification and grounding participation separately, defaulting to
`PENDING`. A caller can set classification `PARTICIPATING` and grounding
`NOT_PARTICIPATING`; the latter is skipped without an error, prediction or score.
Pending calls support contract tests and do not establish model eligibility.
Successful parsing never promotes participation. Failures never rewrite roles.

`SpatialKind` distinguishes `NATIVE_BOX`, `NATIVE_POINT`, `NO_SPATIAL_OUTPUT` and
`MALFORMED_SPATIAL_OUTPUT`; classification uses `NOT_APPLICABLE`. A native point
is retained as native evidence plus original raw bytes, with no canonical box value.
It reports `UNSUPPORTED_GROUNDING_INTERFACE` for the existing box contract, distinct
from malformed output. A valid empty canonical hazards array is a parsed box-interface
response, distinct from an interface with no spatial output.

No point-to-box conversion, native-point D5 track, IoU or other score exists here.
Grounding eligibility and final roles still require the later interface review and
applicable SYNTHETIC V1 gate. Per-call malformed outputs from an eventual qualified
participant remain available to the unchanged D5 consumer policy; runner errors do
not silently remove a participant from metric denominators.

Error codes distinguish model load, runner initialization, preprocessing,
generation/runtime, invalid classification, malformed grounding, unsupported
grounding, parser failure and raw-preservation failure. Parse status independently
records `NOT_ATTEMPTED`, `SUCCESS`, `INVALID`, `UNSUPPORTED` or `FAILED`.
Exception type and stage are recorded without copying arbitrary exception text
(which can contain private paths). Grounding-only exceptions leave the independent
classification result intact. No retries, backup factory, model selection, benchmark
score input or automatic replacement exist in the runner layer.

## Dummy cases and verification

`DummyRunner` emits small inline handcrafted byte fixtures; it opens no image,
loads no weights and calls no model. Cases cover valid classification with a box,
a native point, no spatial output, or malformed grounding; invalid classification;
generation failure; and parser failure. Generation/parser exceptions target one
explicit task, defaulting to grounding. Both tasks are independently exercised.
This is not the eight-image SYNTHETIC V1 suite or a capability gate.

From repository root, using the existing Python 3.11.9 / Pillow 12.3.0 environment:

```powershell
.venv/Scripts/python.exe -m unittest tests.test_local_runners -v
.venv/Scripts/python.exe -m unittest discover -s tests
git diff --check
```

Validation on 2026-09-21: **271/271 repository tests PASS**, including **38/38
new contract tests**, zero failures/errors. The pre-change baseline was **233/233
PASS**. `git diff --check` passes. No JSON/configuration file changed. The reviewed
change list contains only runner Python source, unit tests and implementation/task
documentation: no dataset/media assets, weights/checkpoints or large raw outputs.
The pre-existing `data/manifests/w2_grounding_census.json` remains untracked and
untouched. D1–D9 decisions, D5/schema code and SYNTHETIC V1 assets are unchanged.

No dependency changes or random sampling. Tests use temporary synthetic artifacts,
fixed timestamps and injected dummy settings, not frozen model decoding parameters.
The implementation commit on this branch identifies the source; it is not a protocol
freeze commit. Test artifacts are disposable and no inference run is claimed.

Still pending: model provenance and license/access completion, real runners,
model-specific preprocessing/decoding/precision, adapter qualification, interface
eligibility, synthetic gate execution, final roles, full D5 engine and protocol freeze.
No weights downloaded; no model/provider/GPU inference; no InspecSafe access or
inference; no census changes; no SYNTHETIC V1 gate run.
`protocol_freeze_commit_sha: PENDING`.
