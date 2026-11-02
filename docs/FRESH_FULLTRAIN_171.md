# Issue171: fresh full TRAIN preparation

Source: [Issue #171](https://github.com/tantdna2/SafeShift/issues/171),
[Owner decision](research/DECISIONS.md#dec-20261102-owner-fresh-fulltrain-only).
BASE `1acb3ef7c0deadbbde7da0b1c63b71296e3950e5`; document-first commit
`8fdfc8d`; one branch `feat/issue171-fresh-fulltrain`, one [Draft PR #172](https://github.com/tantdna2/SafeShift/pull/172).
Date: 02/11/2026, Asia/Bangkok. No GPU, real inference, private images/GT/raw
or TEST accessed. Existing local handoff/download tabs are outside this task.

## What this preparation implements

`safeshift/fulltrain/` composes the existing fulltrain planner, pilot execution
engine, strict C1 parser, immutable Store/archive and OS lease. It has a separate
source inventory; no existing candidate/pilot source, numerical implementation,
config or notebook bytes change. It does not import historical predictions.

| Model | New series | Native preparation | Still blocked |
| --- | --- | --- | --- |
| Qwen3-VL-8B-Instruct | `fresh171-qwen3-v1` | Exact public checkpoint inventory, processor/Transformers source hashes, offline native factory, V4 FP16/SDPA/two-GPU placement, raw/processed summaries and unchanged P2.1/HNLO functions | Exact CPython3.12.13/zlib1.2.11 build and closed cp312 wheelhouse not installed; native processor/load/model-fit/live inference not verified |
| InternVL3.5-4B-HF | `fresh171-internvl35-v1` | Shared pinned CandidateBackend, native checkpoint/source/CPU/image/CUDA/resource checks, full cohort controller and native raw custody; supervised isolated setup/stages | Final pinned native CPU integration and live model/load/inference/export not verified; release authority blocked |
| MiniCPM-V-4 | `fresh171-minicpm4-v1` | Same controller; exact existing `minicpm4-resampler-attention-fp32-v1` backend and numerical evidence validator | Same release gaps; **label-only**, no HNLO evaluator, no new score method |

The peer descriptor keeps the existing effective generation/preprocessing,
model revisions, requirements, FP16 weights/eager and batch1/GPU0 placement.
It removes the historical160 selection from the effective configuration and
records it as reference-only; a new configuration digest binds3763. The old
configuration and numerical descriptor remain unchanged, including historical
authority text. Their hashes do not grant a fresh run.

Qwen source review began with tracked metadata and the exact historical
[V4 runbook at31a04e6](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/hnlo_train_v4_20261019.md).
It specifies Python3.12.13, torch2.10.0+cu128, transformers4.57.1, FP16/SDPA,
greedy max32 and CPU embedding/two-GPU layer placement. These differ from the
peer runtime/max64/eager. Copying peer defaults would change science; importing
the old grant/source lock would not qualify a new implementation. Historical
prediction bridges are unnecessary for fresh initial. The review follow-up now
implements the native adapter from those exact source contracts. Public HF
revision metadata matches all16 checkpoint inventory entries; the12 non-weight
files were independently fetched and hashed. Nine official Transformers4.57.1
source files are pinned, including generation, Qwen modeling/processing and
image/tokenizer implementations. No weights or legacy authority were imported.

`qwen_semantics.py` preserves exact historical function bodies for P2.1 parsing,
28-case tokenizer T1, decision alignment, full-vocabulary checks and raw HNLO
log odds. Tests compare ASTs against the recorded historical Git objects.
Qwen's P2.1 whole-response fence rule is historical and applies only to Qwen;
the peer strict C1 parser is unchanged. `engine.py` adapts the existing engine/
recovery with explicit parser injection; raw strings are never rewritten.
Public pinned tokenizers0.22.2 on Windows CPU passed28 synthetic text cases
with ordered candidate IDs16/17/18/19. This does not qualify the target native
Transformers processor, CPython/zlib ABI, weights or GPU implementation.

## Exact cohort and fresh history

`inputs.project_master` first verifies the original master byte SHA through
the existing `fulltrain.cohort`, then verifies the independently supplied
projection digest. Projection retains exact3763 ID/order/image SHA and excludes
GT/paths. Actual master/projection custody is **NOT VERIFIED** in this task;
fixture counts and self-computed hashes cannot establish original membership.
All three plans must have an identical projection digest. The planner refuses
160 rows, reordered/duplicate IDs, image SHA changes and mixed cohorts.

Future authorized Input format (not created from private data in this PR):

```text
<one attached dataset>/
  fresh_fulltrain_input.json
  original_train_master.json
  image_mapping.json
  images/000000.jpg ... images/003762.jpg
```

Marker schema `safeshift-fresh-input-v1` has only `schema`, original
`master_sha256`, `projection_sha256`, `mapping_sha256`. Its outer SHA must be
pinned separately. Discovery reuses the bounded512-entry direct/nested Kaggle
dataset/notebook mount logic and requires exactly one marker. Master size is
bounded16MiB, mapping4MiB. Mapping rows have exactly ordinal/sample_id/image SHA,
opaque image path and positive width/height, with no GT. Validate all image
hashes and native PIL decode before reservation. Image bytes are never rewritten.

Peer checkpoint Inputs reuse `candidate_checkpoint_<key>.json` and the exact
source/revision/weights layout and allowlists in the existing contracts.
This is checkpoint identity reuse only; Candidate160 grants/history/caps are
not accepted as fresh authority. Fresh requests separately pin each marker's
byte SHA. Qwen uses `fresh_checkpoint_qwen3.json` with schema
`safeshift-fresh-qwen-checkpoint-v1`, exact model ID/revision and
`inventory_sha256=digest(configs/fulltrain/qwen3.json.snapshot_files)`. Its
`snapshot/<revision>/` must contain exactly16 regular, single-link files, with
byte size and SHA256 matching the pinned public inventory. All four weight
shards and index are checked before deserialization; no weight downloader exists.

`initial` has all3763 planned statuses/model and no history. A bounded attempt
schedules the next explicit portion; `scheduled_ordinals` plus deferred cover
the entire pending plan. Across the three initial plans:11289 planned calls,
not executed calls or predicted SUCCESS. No O5 number is supplied by default.
Software planner bounds1..3763 calls and1..43200 seconds are validation bounds
in the reused planner, not O5/O6 authorization.

`resume` accepts only the named fresh campaign/series with exactly the same
identity. SUCCESS, INVALID and consumed technical errors never become pending.
`repair` requires exact failed outcome hashes, diagnosis, cause-evidence hash,
fix hash, regression hash and plan binding. These are evidence references,
not approval signatures. All production entries remain closed to repairs too.
A configuration/semantic change requires an explicitly versioned new campaign
and series plus comparability approval; there is no automatic rerun/best-series
selector. Old Candidate160 retry semantics remain unchanged.

Use a separate workspace per model. Under a process lease the controller checks
all ancestor directories and reservations. Missing, extra, conflicting or
unreconciled attempts block before further calls. A hard kill between reservation
and journal creation stays blocked; no automatic deletion/retry. Locks release
on process exit but are not distributed across Kaggle VMs. Stop the prior VM
and preserve every Output before a subsequent attempt; no global exactly-once
claim is made.

Each attempt preserves campaign/plan/history, raw-before-parse, native token/
step evidence, execution identity, checkpoints, receipt and all3763 operational
statuses in `accounting.json`. One cached model load per attempt; technical or
nonfinite output stops, INVALID remains durable. Partial valid raw can be
reconciled; native raw must also pass native/configuration/numerical custody.
Raw corruption, contradictory results or unknown reservations block recovery.
Parser exceptions remain errors, not silently reconstructed successes.

`runtime.import_history` checks outer ZIP SHA, bounded member hashes, campaign,
plan and recovery projection before installing into a new destination. Import
every ancestor ZIP in order; attach them all, since later ZIPs carry projections
but do not embed copies of earlier raw archives. Duplicate targets refuse
overwrite. Failed import reservations remain for reconciliation. A sealed ZIP
with a historical/foreign campaign is rejected. Call `runtime.recover`, not the
generic old journal reader, for fresh native history.

Export uses the reviewed bounded ZIP verifier (8GiB total,64MiB/member); future
O5 attempts must budget raw/token evidence, disk and export reserves accordingly.
ENOSPC/hard kill can prevent an archive or final receipt. Preserve partial files,
reservation and logs; a partial archive is not successful export. Time checks
between calls remain cooperative within the controller, and the new supervisor
also enforces an absolute process deadline across admission/setup/diagnostics/
native work. A hanging call/load is killed with its Linux process group; no
retry occurs. See the detailed supervisor limits below.

## Notebook and environment checks

Six new notebooks: `SafeShift_FRESH_FULLTRAIN_{PREP,DIAGNOSTIC}_{model}.ipynb`.
Each embeds an exact committed source inventory, rejects corruption/stale code,
compiles with empty outputs, and runs through the same preparation entrypoint.
PREP and DIAGNOSTIC are deliberately non-executing in this release: they observe
only stdlib kernel/platform/cgroup information and export immutable source,
native-contract and release evidence. They do not inspect Inputs, install
packages, allocate scratch/GPU, load weights or consume attempts. They export
`BLOCKED`, never `READY_TO_RUN_GPU`. Do not run them on Kaggle during this task.

The module also supplies an explicit-budget storage probe: validate roots,
combine requested sizes on a shared device, allocate both files simultaneously,
write/fsync and remove only its owned files. Linux st_blocks verifies physical
allocation; Windows reports allocation bytes unknown rather than claiming quota
proof. Tests use tiny synthetic allocations, not campaign-sized capacity.
`cpu_native_checks` composes the existing isolated pinned software/compiled ABI
and public-source meta/processor path with CUDA hidden, including the exact
MiniCPM patch. It is explicit opt-in, not run by notebook cells or default tests.

The receipt inspector verifies binding/check completeness; supplied receipts
cannot promote observed levels or unlock execution. Required final-source live
checks remain: unique Input marker and cohort seal, source/checkpoint hashes,
Python executable/prefix/ABI, exact dependency set/pip check/native ops, all3763
hash/decode, scratch/output device/free space/actual allocation/quota, RAM/cgroup,
deadline, physical GPU model/count/free memory, allowed driver, visibility and
CUDA FP16 in the same isolated worker. Missing evidence remains NOT_RUN/BLOCKED.

The follow-up wires provisioning/supervision into the internal fresh pipeline
without importing Candidate160 caps or authority. Peers reuse existing CPython
provisioning and `venv --without-pip`/pinned pip-wheel checks; no kernel Python3.13
fallback or package mixing. Qwen's offline source-build/wheelhouse route is
specified below. Final-source pinned native CPU evidence for each adapter and
separately authorized live checks remain required. The preparation API's
public `launch`, `worker`, `native_factory` and `live_preflight` fail before
private I/O or model/GPU imports. Internal composition functions are not grants
and are not an approved execution route.

| Prior failure | Relevant protection / remaining limit |
| --- | --- |
| Phi Python3.13/ensurepip/package ABI | Existing isolated worker/software path reused; no new live provisioning claim |
| Phi eager override/AutoModel re-exec | Existing shared reviewed peer loader retained; no replacement AutoModel path |
| MiniCPM FP16 attention/nonfinite | Exact FP32 resampler adapter retained; raw numerical evidence checked; label-only |
| InternVL code-fenced output | Strict parser unchanged; INVALID durable, repair explicit, no fence stripping |
| Nested/duplicate Kaggle Input | Existing bounded discovery plus fresh marker/mapping/hash checks |
| Qwen OOM/two-GPU constraints | Exact CPU embedding/two-T4 map; per-device headroom and child CUDA probes, no pooled VRAM claim or measured model-fit |
| Partial/raw/parser/export failure | Immutable raw first, reservation reconciliation, repair hashes, archive checks |

## Prepared supervised release route and exact external prerequisites

This implements the changes requested by
[ChatGPT review6572757952](https://github.com/tantdna2/SafeShift/pull/172#issuecomment-6572757952).
The prior review remains FAIL for its reviewed HEAD542e4dd; only a new review
can change that verdict. No audit/merge permission is inferred.

Public `runtime.launch`, `runtime.worker`, `native_factory`, `live_preflight`
and the new `admission` CLI call `contract.authorize()` before private request
I/O. It always raises in this PR. Internals implement the future authorized
route; they are not a documented permission bypass. No approval JSON can unlock
them through a public entrypoint. A later reviewed activation must authenticate
exact O2-O6/source/rights/run bindings in both parent and child.

`admission.REQUEST_FIELDS` is the exact machine-readable request schema:
model/source, fresh campaign/plan/history, original projection and Input marker,
checkpoint marker SHA, distinct Input/work/scratch paths, explicit resource
policy and repair case. Qwen additionally needs `runtime_lock`, its canonical
SHA, `software_input` and `software_marker_sha256`; peer software fields must be
null. Every child rechecks source/request/plan/Input/checkpoint/history before
its stage. Unknown reservations and unknown work-root entries block before
setup. Complete resume performs only bounded admission; no setup, GPU or load.

The stages are `admit -> setup -> cpu -> gpu -> native`. Diagnostic omits native
and creates no campaign attempt/reservation/Owner slot. The CPU stage hashes and
decodes all3763 images, checks isolated Python/dependency/native ABI and exercises
the pinned native processor with synthetic input only. GPU stage observes exact
physical two-T4 identities, driver allowlist and per-device free memory, then
checks CUDA build, visibility, capability and FP16 tensors inside the isolated
child. Qwen requires two visible devices; peers retain one visible GPU. Model
fit remains unknown until separately authorized weight loading/inference.

Resource policy requires explicit positive values for RAM/scratch/output
reserves, each physical GPU's free MiB, GPU0 runtime reserve, simultaneous
scratch/output allocation probes, log budget, setup and diagnostic seconds.
It also requires `review_mode=EXTERNAL` and an exact driver allowlist. These are
supplied release constraints, not defaults or new scientific O5 decisions.
RAM uses the minimum of `/proc/meminfo` and cgroup remaining capacity. Shared
filesystems require the sum of both reserves; different devices are checked
separately. Allocation writes/fsyncs both probes concurrently and removes only
the owned probe files. All blocking stage work runs under the process supervisor.

Qwen software Input has `fresh_qwen_software.json` with schema
`fresh-qwen-software-v1`, `runtime_lock`, `python_source` and `zlib_source`.
Each source entry has a safe basename, byte size and the exact historical
public source SHA recorded in `configs/fulltrain/qwen3.json`. The runtime lock
contains exact normalized distribution versions and one wheel per distribution
with basename/name/version/size/SHA. Its `wheels/` directory must match exactly,
include every recorded Qwen software pin and pinned pip25.0.1, and stay within
the256-member/16GiB software archive bounds. These are software validation
bounds, not experiment caps. Runtime installation checks the complete installed
distribution set and `pip check`; missing/transitive/foreign packages block.

The prepared build compiles zlib1.2.11 then CPython3.12.13 with the audited zlib
paths, `--with-ensurepip=no`, and creates a copied `venv --without-pip`.
The sealed pip wheel bootstraps itself; all remaining wheels install offline
with `--no-index --no-deps`. No resolver, alternate Python or global package
fallback is allowed. Setup, compiler, pip and worker descendants share one
supervised process group. Qwen's exact closed cp312 Linux wheelhouse is **not
present or validated in this task**: the historical source records top-level
versions, not a complete immutable wheel closure. Supplying and independently
sealing that closure, building CPython/zlib and verifying native ABI are exact
release prerequisites. The implemented gate fails before Input/model use if
the closure or its seals are absent; a checksum is not approval.

Linux supervision uses an absolute deadline shared across stages, stage-specific
sub-budgets, bounded log monitoring, process-group SIGKILL and `wait()` reaping.
A guardian sets Linux parent-death signaling and holds the process lease across
children. Tests kill a synthetic hung child/grandchild, kill the parent, exceed
an internal setup log budget, and verify partial bytes survive. Exit0 still
kills lingering descendants. No retry, lock deletion or partial-output overwrite
occurs. Limits: this controls cooperative reviewed processes, not malicious
code that escapes the group; kernel uninterruptible I/O and SIGKILL directly to
the guardian need container/VM termination. Log monitoring can overshoot by one
poll interval, so filesystem quotas remain necessary. Export after process stop
may fail due to disk/VM loss; retain original directories and partial archives.
Scratch is retained for inspection, with no recursive deletion or hidden reuse.

## O2-O6, B1-B6 and G0-G6

| Item | Current status | Required evidence before release/claim |
| --- | --- | --- |
| Owner fresh direction | RECORDED | Three new series; no prediction inheritance |
| O2 | PENDING | Comparability and scientific selection/method remain separate from operational scheduling |
| O3 | PENDING | Final roster/roles/qualification; three candidates, no fourth recruitment |
| O4 | BLOCKED | Exact master projection, image mapping and rights/custody seals |
| O5 | PENDING | Actual caps/resource budgets/stopping/precision, no invented defaults |
| O6 | BLOCKED | Exact final source/notebook/runtime/Input/model/run/attempt authorization |
| B1 | BLOCKED | Source/rights/custody registry and permitted uses |
| B2 | BLOCKED | Independent source/dependence verification; TRAIN not holdout |
| B3 | BLOCKED | Independent V/T exposure/custodian/access/overlap seals; TEST closed |
| B4 | BLOCKED | External expert/rubric/blinding/annotation rights for new sources |
| B5 | BLOCKED | O2/O5 numbers, resources and academic/negative-route acceptance |
| B6 | BLOCKED | Fresh native model/run release and scientific qualification |
| G0 | BLOCKED | Exact science/rights/authority, beyond Owner's fresh direction |
| G1 | CPU checks only | Exact source/payload/old-byte tests; ChatGPT review still required |
| G2 | PARTIAL / NOT VERIFIED | Pure admission checks; pinned native stacks and real Input not measured here |
| G3 | CPU tests only | Synthetic planner/custody/failure evidence; native opt-ins explicitly skipped |
| G4 | NOT_RUN | Kaggle runtime/resources/driver/CUDA before consumption |
| G5 | NOT_RUN | Authorized real weights/inference/raw/HNLO where eligible/export |
| G6 | BLOCKED | Independent Antigravity audit, separate merge and release/postmerge verification |

Use original definitions in [release gates](KAGGLE_FAILURES_AND_RELEASE_GATES.md)
and [T4 dossier](research/T4_O2_SELECTION_DOSSIER_20261101.md). These are not
new science thresholds. Academic approval, measured fresh results and all-SUCCESS
claims are not supplied by software tests; planned count is exactly3763/model.

## Reproduce and review

[Exact CPU receipts, failures, rerun and source hashes](research/evidence/issue171/README.md)
are included in this Draft. They establish preparation behavior only; the native
and live release gaps above remain open. Do not close Issue171 as fully native
qualified on the strength of these tests.

From repository root, Python3.11+, no additional dependencies:

```console
python -B -m unittest discover -s tests -p "test_fresh_fulltrain*.py" -v
python -B -m scripts.prepare_fresh_fulltrain --output data/processed/issue171/prep-new --max-calls 3763 --max-seconds 60
python -B -m scripts.check_fresh_fulltrain_cpu --output data/processed/issue171/cpu-new
python -B -m scripts.build_fresh_fulltrain_notebooks --runtime-ref <exact-committed-runtime-SHA>
```

Numbers in the synthetic CLI are test parameters only. The builder requires
each embedded byte to exist at the given commit. Commit runtime first, generate
notebooks, then commit notebooks/evidence; no self-referential source hash.
New output paths are mandatory. Test logs/receipts record command, commit,
source hashes, interpreter, platform, skips, failures and limitations; public
sanitized evidence is linked from PROJECT_STATE in the same PR.

After review/independent audit/separate merge, a later release must close the
listed native/runtime/custody/authority gaps and regenerate exact notebooks.
Only then perform authorized live preflight and minimal real qualification,
preserving failures. Full official experiments are a separately granted next
task on these fresh series; do not modify this notebook or reuse an old grant
to bypass the fence. No merge, audit PASS or scientific success is claimed here.
