# InternVL3.5 grammar V2 native integration

**Current PR177 continuation:** [exact-release campaign runbook](INTERNVL_V2_CAMPAIGN.md)
supersedes the initial scope/authorization/notebook statements below. Native
execution now requires an externally reviewed/audited HEAD and job-specific
release plus GitHub create-only process/load/call permits. The current task
stops before Kaggle at the new HEAD review boundary. Capture/grammar/parser
semantics remain as described here. The remainder preserves the initial
`00dae6a` CPU preparation snapshot and its evidence; it is not the active
submission procedure or permission to run.

## Initial CPU preparation snapshot (superseded operational scope)

Scope: implementation and CPU synthetic verification only, based on merged
PR #176 (`4578c175e0011783c3573d0003fc5341eaf3ef72`) and its
[post-merge handoff](https://github.com/tantdna2/SafeShift/pull/176#issuecomment-6621575815).
The Owner-approved method, immutable grammar/descriptor, checkpoint, C1,
official parser and HNLO N/A policy remain fixed. This document is the design
record before implementation; verification results will be added in this PR.

The new runtime will use a separate technical qualification identity, with no
historical prediction import and no enrollment in a scientific full-TRAIN series.
Its conservative engineering ceiling is one load, one call and 1800 seconds;
these limits do not grant a call. All public native entrypoints must reject
execution before Input/model access. No editable notebook flag or JSON approval
field may open the fence. A later reviewed exact-run release must establish
authority, remote anti-replay custody, Input/sample hashes and resource bounds.

Native generation uses the existing offline InternVL loader and preprocessing,
then the approved V2 callback. Each full vocabulary forward vector must be saved
and fsynced before the native prefix processor runs. The actual processor list,
prefixes and masked vectors are recorded; native returned IDs precede decode,
and exact response bytes precede official parsing. Independent tokenizer/trace
verification is required. Every result, including failures, has numeric HNLO
null and `HNLO_NA_GRAMMAR_POLICY_V2`.

The notebook will package hash-bound sources and run isolated setup/preflight
children with bounded logs and process-group deadlines. Preflight checks unique
Input/checkpoint markers, source/weight hashes, pinned Python/packages/ABI,
physical GPU/driver and child CUDA, RAM/cgroup, filesystem reserves and actual
scratch allocation, plus synthetic native tokenizer/image-processor/grammar
composition. No model weights are loaded by preflight. Repeated preflight uses
new diagnostic output directories and consumes no execution attempt.

CPU tests must exercise the shared controller/native capture path with scripted
synthetic logits, plus malformed JSON, EOS/prefix/processor drift, hash mutation,
write/log failures, timeout and load failure. Outputs are private by default;
only sanitized synthetic receipts belong in Git. CPU evidence never establishes
Kaggle readiness, real model fit, inference quality or scientific qualification.

Stop at one Draft PR for ChatGPT review. No Kaggle submission, GPU/model load,
TRAIN/TEST image access, full3763 inference or merge in this task.

## Implemented route and evidence format

`scripts/internvl_v2.py` → `worker(setup)` → isolated CPython3.11.9 with the
existing InternVL pins → `worker(preflight)` or fenced `worker(native)`.
Native: exact request/source/checkpoint admission → exclusive attempt/load
reservation → unchanged `CandidateBackend` loader → unchanged C1 image
preprocessing → V2 `generate_prepared` → native Transformers4.55.4 generation.
There is no model downloader, submission client, remote log relay or cohort loop.
The controller supervises the entire child process group, including hanging
loads; its 1800-second ceiling and stage limits are engineering bounds only.

Capture writes `steps/NNN.f32` as little-endian float32 full output-head logits,
then a forward receipt. The processor observer saves the actual class list and
requires exactly the approved native prefix processor. It verifies scores equal
the saved forward vector, runs that processor, and saves prefix/masked scores
(`null` represents minus infinity). Disallowed padded head columns remain in
both vectors. The pinned model has151936 output columns versus151679 tokenizer
IDs; a read-only vocabulary view extends only the verifier's numeric domain.
The four paths, EOS, receipt and allowed-token sets are identical to the approved
grammar; no token resize, extra path or grammar source modification occurs.

Returned IDs are stored before decode in `native.json`. `raw.json` stores exact
response, token IDs, binding and vector hashes before `parse_label`. No fences
are stripped. `replay_saved` checks vector sizes/hashes and the unchanged V2
verifier with an independent Rust tokenizer. Invalid JSON is durable INVALID;
valid JSON with failed trace is TECHNICAL_ERROR. NaN/Inf bytes, partial files,
load/call reservations and failure receipts remain preserved. Errors never
authorize retry. No numerical HNLO or scientific metrics are calculated.

The technical request fixes ordinal0, TRAIN, one opaque sample ID/image hash,
source digest, identity/series/attempt and exact call/time limits. Its schema
rejects extra approval/history fields, TEST, cohort loops and other series.
Hashes establish byte identity, not permission or a trusted dataset projection.
The next execution task must externally bind this request to the original master
and approved image; this release cannot admit any real request. Local exclusive
reservations exclude replay in one workspace. They do **not** establish global
exactly-once across fresh Kaggle VMs: remote submission/process permits and
custody must be added/reviewed under the next exact-run authority before opening
the permanent fence. Neither an empty VM nor edited notebook mode enables native
execution today. A future full3763 series remains separate from this technical
qualification and must cover the original whole cohort without backfill.

## Notebook and preflight

`notebooks/SafeShift_INTERNVL35_GRAMMAR_V2.ipynb` embeds only committed code,
public configuration and SHA256 bindings. Builder rejects uncommitted runtime
bytes. All outputs/execution counts are empty. **Do not submit this notebook in
the current task.** It is executable preparation, not READY FOR OWNER or a grant.

For a later authorized preflight, attach the existing InternVL checkpoint Input
with unique `candidate_checkpoint_internvl35.json`, `source/<locked-revision>`
and flat `weights/` allowlists. No real image or historical prediction Output is
needed. Default mode is `preflight`; `execute` and direct native worker/loader
calls fail before Input access. No Kaggle/HF token is requested or embedded.

Preflight provisions pinned public software in isolated scratch, checks actual
source/checkpoint SHA256 before model loading, and measures package/compiled ABI,
driver/T4 counts, child CUDA/FP16/visibility, RAM/cgroup, shared/separate storage
reserves and actual fsynced allocation/cleanup. It exercises native processor,
tokenizer and all four grammar paths with a generated grey image and scripted
scores, without model construction/weights/forward. Existing Issue173 resource
floors and driver580.178.04 are retained explicitly; another driver blocks until
review, never silently falls back. Repeated preflights use distinct directories
and consume no Owner slot/attempt/call.

G0 always remains BLOCKED for native authority; G1 records Input/hash admission,
G2 pinned software/ABI, G3 synthetic native grammar/processor, G4 measured
resources/driver/CUDA; G5 weights/inference stays NOT_RUN. G6 is successful only
after ZIP/member hashes and sidecar export verify. CPU mocks cannot certify any
live gate. Missing Python/package, duplicate marker, bad bytes, RAM/quota/GPU,
timeout, unknown child output or log/write error stops the following stages.

Side effects when later authorized: pinned Python/package downloads, scratch
venv/cache, 1MiB fsynced probes on scratch/output (then removal of those exact
probe files), GPU FP16 tensor probe; no weight download/load. Evidence roots and
ZIP/SHA256 live under `/kaggle/working/<identity>-preflight-<id>`; runtime under
`/kaggle/temp`. Keep archives private: they may contain runtime paths and, after
a future authorized native call, raw/tokens/logits and sample identifiers. Only
sanitized status/hash receipts belong in Git or public review. Never publish full
private logs. Export failure leaves the original directory/partial archive and
does not report PASS; preserve them for diagnosis without repeating inference.

## CPU reproduction

From repository root (new output directory each time):

```console
python -B -m scripts.qualify_internvl_v2_runtime --output data/processed/v2-stdlib-new
```

For native scripted generation, use an isolated CPU stack (torch2.6.0+cpu,
torchvision0.21.0+cpu, transformers4.55.4, tokenizers0.21.4). The exact observed
versions are in the receipt. No install or network is required by default:

```console
python -B -m scripts.qualify_internvl_v2_runtime --output data/processed/v2-native-new --native-source data/processed/internvl_v2_native/public-source --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
```

`--fetch-public-source` optionally fetches only the13 bounded public text files
in the existing source lock and verifies every SHA. No weights or private data.
Linux stdlib tests also exercise real child process-group timeout/log failure.
Synthetic model forwards supply handwritten logits; the actual native image
processor, Transformers generation loop/prefix processor and decoder are used.
This is software integration evidence, not checkpoint inference or model fit.

Rebuild the notebook using its metadata `runtime_commit`:

```console
python -B -m scripts.build_internvl_v2 --source-commit <runtime_commit> --output data/processed/v2-notebook-rebuild.ipynb
python -B -m unittest discover -s tests -p test_internvl_v2_notebook.py -v
```

Live constraints still unverified: actual Kaggle provisioning/Input mount,
weight deserialization, GPU/peak memory, final native forward/capture, response
quality/false-safe, full3763 duration and all scientific/O2–O6 permissions.
Review/independent audit/merge remain separate; no claim that CPU PASS completes
the AGENTS live-notebook requirement. The explicit current Owner task forbids
Kaggle/model execution and assigns real-model verification to a later task.

## Verification and handoff

Tested implementation/test HEAD: `110ec3f08bdfbe7ca880bff7cc038dcef0ad9a5a`.
Notebook embedded runtime: `01256505ecf4597d1eea4dd4d97325e98ee766cf`; all runtime
bytes match tested source. Later receipt/docs commits do not change those bytes.

| Check | Result | Receipt |
| --- | --- | --- |
| Windows CPython3.11.9, native CPU stack | 91 selected:88 PASS,3 Linux-only SKIP; all10 native integration tests PASS | [native-cpu.json](research/evidence/internvl_v2_native/native-cpu.json) |
| Linux CPython3.14.4 stdlib | 91 selected:81 PASS,10 native-only SKIP; all3 real process supervision tests PASS | [linux-cpu.json](research/evidence/internvl_v2_native/linux-cpu.json) |
| Notebook rebuild/hash/credential patterns/empty-VM native fence | 4/4 PASS, no skips; no notebook preflight executed | [notebook.json](research/evidence/internvl_v2_native/notebook.json) |
| Frozen method/science/legacy source/notebooks | Unchanged against verified main | [preservation.json](research/evidence/internvl_v2_native/preservation.json) |

95 distinct selected tests are covered across these environments. No failure or
error in final runs; skipped tests are not counted as PASS. No full-repository
suite or independent CI/audit result is claimed. The earlier CPU timeout and
scripted-fixture signature failure remain in ignored local logs, with hashes and
root-cause resolution in [validation.json](research/evidence/internvl_v2_native/validation.json).
Native synthetic tests use the unchanged generation-config constructor including
cache policy. Actual checkpoint forward/KV behavior still needs live validation.

Changed-file inventory for this one PR:

| Files | Purpose |
| --- | --- |
| `safeshift/internvl_v2_runtime.py` | Native adapter, capture/replay, identity, manifest, code fence, exclusive attempt/call accounting |
| `scripts/internvl_v2.py` | Worker/controller/preflight/CLI and sealed failure export |
| `scripts/build_internvl_v2.py` | Reproducible committed-source notebook builder |
| `scripts/qualify_internvl_v2_runtime.py` | CPU qualification and machine-readable receipts |
| `configs/grammar/internvl35_v2_runtime.json` | Separate runtime descriptor and explicit engineering limits |
| `notebooks/SafeShift_INTERNVL35_GRAMMAR_V2.ipynb` | Unsubmitted executable preflight with native execution fenced |
| `tests/test_internvl_v2_runtime.py`, `tests/test_internvl_v2_notebook.py` | Synthetic native/controller/error and notebook regressions |
| `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`, `docs/INTERNVL_GRAMMAR_V2_RUNTIME.md` | Current status, corrected PR176 merge snapshot, routing and runbook |
| `docs/research/evidence/internvl_v2_native/{native-cpu,linux-cpu,notebook,preservation,validation}.json` | Five sanitized receipts, no raw/model/private data |
