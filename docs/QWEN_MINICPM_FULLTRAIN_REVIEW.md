# Qwen3 / MiniCPM full TRAIN technical review — 12 November 2026

BASE: `341ab626ff2af7ef79ced0d9c3119794eea4a820`, verified against the GitHub
main branch API and `git fetch origin main`. Scope: CPU synthetic engineering,
one branch and one Draft PR. No Kaggle submit, GPU, real inference, TEST, private
image/raw access or production-ledger writes. `operator-asus-win` is outside scope.

The supplied untracked notebook, test and generator were found in the original
workspace and preserved under the ignored task evidence directory before edits.
They are not main-branch deliverables. The notebook has no model load or native
inference loop, yet counts scheduled ordinals as completed. Its FP32 wrapper only
increments counters; its parser accepts prose/bare labels; history ZIP discovery
trusts filenames and ordinals, ignores series/checksums and continues on corruption.
The tests duplicate these implementations rather than exercising the runner.
RAM falls back to 32 GiB on observation failure; reported free VRAM is total VRAM;
the suggested 160-call/7,200-second batch has no measured or authorized basis.
Claims of faculty approval and READY_FOR_OWNER are unsupported.

Implementation reuses the reviewed fresh171 native pipeline and exact
MiniCPM numerical adapter, retain strict C1 and HNLO N/A, package a reproducible
notebook, and exercise the actual controller/history/archive and failure paths.
The immutable fresh171 release fence stays closed. This task does not manufacture
an execution grant, source activation or final-source Kaggle evidence.

Qwen V4 ORIGINAL remains 3,539 SUCCESS + 1 TECHNICAL_ERROR + 223 NOT_ATTEMPTED.
Recovery224 remains 224 SUCCESS in its own series. Neither is fresh171 completion.
MiniCPM official Candidate160 FP32 remains 155 SUCCESS + 5 INVALID; it cannot be
imported into fresh171. Detailed Inputs, test evidence and operating instructions
are recorded below. No private results were reopened to recompute these counts.

## Model and series findings

| Model / series | Evidence and status | Reuse / limits |
| --- | --- | --- |
| Qwen3 V4 ORIGINAL | 3,763 planned; 3,539 SUCCESS, 1 TECHNICAL_ERROR, 223 NOT_ATTEMPTED | Historical source/semantics/checkpoint references only; no fresh completion inheritance |
| Qwen3 Recovery224 | 224 SUCCESS, separate recovery | No pooling with V4 or fresh171 |
| `fresh171-qwen3-v1` | No completed-series evidence in the reviewed dossier; BLOCKED | Pinned `qwen.py`, historical P2.1 and raw HNLO bodies, offline runtime/checkpoint inventories reusable; no Qwen rerun authorized |
| MiniCPM official FP32 Candidate160 | 155 SUCCESS, 5 INVALID, label-only | Numerical implementation reused; predictions, caps and authority cannot move to fresh171 |
| MiniCPM Issue173 v3 | Historical one original ordinal0 native SUCCESS; terminal COMPLETE | [Receipt](research/evidence/issue173/mini-once/execution-v3.json), source `140f6d8`; not full TRAIN or new-source verification |
| `fresh171-minicpm4-v1` | New execution candidate and original-mount binding CPU-tested; no fresh native results claimed | BLOCKED_NOT_LIVE_VERIFIED; full original 3,763 IDs, strict C1, HNLO N/A |

Sources: append-only decisions of 02/11 in [DECISIONS](research/DECISIONS.md),
[fresh171 contract](FRESH_FULLTRAIN_171.md), [historical byte checks](KAGGLE_CHECKPOINTS_173.md),
[Mini v3 terminal record](ISSUE173_DIAGNOSTICS.md). Earlier fresh171 descriptions
of unmeasured software/checkpoint bytes are historical: Issue173 subsequently
verified the actual original 3,763 JPG bytes and model shards, and PR174 software
v2 verified the isolated native processors/ABI/CUDA tensor path. Those source-bound
receipts are reusable evidence, not live verification of this new notebook.

Qwen's retained runtime is CPython3.12.13/zlib1.2.11, torch2.10.0+cu128,
Transformers4.57.1, FP16/SDPA, greedy max32, batch1, CPU embeddings and two-T4
layer placement. Its parser is historical P2.1, not the peer C1 parser. Preserve
the unchanged `qwen.py`, `qwen_semantics.py` and nine pinned Transformers sources.
The 4,209,365,519-byte [offline software bundle](research/evidence/issue173/qwen-bundle-custody-v2.json)
SHA256 is `b068aeb381cb3cff2b0978e7b5a398e009cb44dc4a43e6410083a766a252308f`;
its 48-wheel runtime lock is tracked under Issue173. No replacement download or
runtime re-provisioning was attempted in this task. Fresh-Qwen activation still
needs an exact source/release, original projection/Input layout binding, current
transport/history/rights/caps and final-source verification. The Mini-only
original-mount extension does not silently activate Qwen's historical flat layout.

MiniCPM is `openbmb/MiniCPM-V-4` @
`6f69a8235885be89608f3a71ffd40695b379e1e7`, implementation
`minicpm4-resampler-attention-fp32-v1`. FP16 parameters, eager, greedy max64,
batch1/GPU0; only native resampler scores, softmax and value product use FP32,
with native dtype restored before output projection. Model processing/resize/
slices/generate remain in the reviewed adapter. No new model adapter was written.
The real numerical CPU tests compare the hash-locked native resampler to scalar
and FP32 references, verify FP16 parameters/return dtype, masking/nonfinite failures
and refuse altered source. CPU software here uses torch2.6.0+cpu; this does not
certify the target cu124 worker or whole-model VRAM fit.

## Exact Kaggle Inputs — evidence table, not a live account observation

The original Antigravity choice `tetrabot2026/...` is unsupported by the retained
submission metadata. Use only the explicit sources below. Version gaps remain
unknown; neither the code nor this report guesses a Dataset version.

| Source / Owner | Version evidence | Required mount content | Verification / remaining gap |
| --- | --- | --- | --- |
| Dataset `nguynanhtn/inspecsafe-v1-kaggle` | Dataset version not retained in reviewed sanitized receipt | `<mount>/InspecSafe-V1-Kaggle/train/DATA_PATH/train/Annotations/...jpg` | Historical byte PASS on all 3,763; fresh binding requires actual positive version and original projection seal |
| Dataset `nguynanhtn/safeshift-pilot-input` | Dataset version not retained in reviewed sanitized receipt | `<mount>/master_manifest.json` | Original full master SHA256 `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`; pilot160 images alone insufficient |
| Notebook Output `nguynanhtn/safeshift-prepare-minicpm4` | Historical version1 | `candidate_checkpoint_minicpm4.json`, `source/6f69a8235885be89608f3a71ffd40695b379e1e7/`, `weights/` | 2 shards, 741 tensors, 8,119,153,016 weight bytes; marker SHA in byte receipt; reuses existing Input |
| Notebook Output `nguynanhtn/safeshift-qwen3-m1-model-provision-kaggle` | Historical version1 referenced in Issue173 | `QWEN3_MODEL_FLAT/` and `QWEN3_MODEL_PROVISION_RESULT/qwen3_flat_snapshot_manifest.json` | 4 shards, 750 tensors, 17,534,339,512 weight bytes; Qwen fresh layout/release still separate |
| Qwen software bundle retained from Issue173 software version2 | Historical v2, exact bundle hash above | `fresh_qwen_software.json`, 48 wheels and Python/zlib archives | 51 exact members checked historically; not a new Kaggle Input publication in this task |
| MiniCPM same-series ancestors | None provided/required for a genuinely new initial | Every explicitly named attempt ZIP + `.zip.sha256.json`, oldest first | No Candidate160, smoke, foreign series or filename-based ZIP discovery; unknown/partial history STOP |

Direct mounts `/kaggle/input/<slug>` and nested
`/kaggle/input/datasets/nguynanhtn/<slug>` are supported for the two Datasets;
bounded discovery rejects duplicate mounts. The existing checkpoint discovery
also supports `/kaggle/input/notebooks/<owner>/<slug>`. No recursive TEST walk,
annotation JSON read, image copy or Dataset upload is needed by the new Mini path.
Version/ref fields bind the reviewed request; a filesystem mount cannot prove
provider version, owner rights or current quota. Those require operator evidence
and exact source release before production. This task made no new Kaggle probe.

The explicit request extension `original_inputs` uses schema
`safeshift-original-mounted-train-v1`, exact `master_dataset`/`train_dataset`
objects `{ref, version, mount}`, locked `master_sha256` and private
`projection_sha256`. Set the request `marker_sha256` to the canonical digest of
that entire binding. Do not supply invented versions or synthetic projection IDs.
Both admission and native worker verify it, frozen master SHA before parse, exact
ordinal/ID/image SHA and TRAIN locator. Image hashes are checked before setup;
the pinned CPU child decodes the same JPGs before GPU/load. No GT leaves admission.
The prior opaque fresh Input route remains supported without implicit fallback.

The exact MiniCPM shards are:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `model-00001-of-00002.safetensors` | 4,966,445,072 | `c1636a5c21c7fedb3f6f0ff3f3a4e35103e6208c1144f320a0c5a92c22a16af6` |
| `model-00002-of-00002.safetensors` | 3,152,707,944 | `cd6ee63b0a3ae1ad24790f954cca3448392cd3a0d9d2d208cb2b14e0da53d32e` |

Index/source/config/marker and all four Qwen shard sizes/full SHA256s are in the
[sanitized byte receipt](research/evidence/issue173/checkpoint-bytes-v1.json) and
unchanged checkpoint locks. New tests compare those inventories field by field;
they do not reopen or claim to rehash multi-GB weights locally.

## Pipeline, failure handling and operational handoff

The new notebook embeds exact committed source and calls
`minicpm_notebook.prepare` for CPU diagnostics and `run_request` for the execution
boundary. The latter calls `contract.authorize` before request/path/Input I/O,
then validates the pinned request/model and delegates to `runtime.launch`.
**This source always blocks execution.** A JSON request, READY flag or edit to
`REQUEST_FILE` cannot confer permission. A separately reviewed source activation
is still necessary; do not call internal functions to bypass it.

The fully implemented native pipeline is admission → isolated setup → CPU
software/processor/image checks → measured GPU/CUDA → `runtime._worker` → existing
FP32 backend → shared controller/NativeStore/raw-before-parse → strict C1 → archive.
CPU integration exercises the actual worker, controller, numerical custody, parser
and ZIP generation with explicit model/hardware doubles, for both Input layouts.
The new binding does not create a scientific series, migrate historical authority
or alter prompt/generation/parser/checkpoint/numerical semantics.

Plans require explicit call/time caps. Resource policy requires approved drivers,
per-physical-GPU headroom, GPU0 runtime reserve, RAM/cgroup, separate scratch/output
reserves (summed if shared device), actual allocation budgets, setup/diagnostic
deadlines and log bounds. Unknown RAM never becomes32 GiB; total VRAM never stands
in for free VRAM. Missing packages/hashes/images/history/resources block load.
The supervised CPU diagnostic exits before the native child loads weights. Process
deadlines kill the child group and preserve partial raw/error/reservation evidence.
No cap, latency projection or safe160-image claim is manufactured from smoke.

Resume only NOT_ATTEMPTED with identical campaign/model/config/series. SUCCESS,
INVALID and consumed technical errors remain durable. Repair requires exact failed
outcome digests, diagnosis/cause evidence, fix/regression and separate authority.
Import every ancestor ZIP explicitly with expected outer SHA, validate bounded
members/checksums/campaign/native custody and preserve all originals. Duplicate,
omitted, corrupted, interrupted or ambiguous history stops; no auto retry/overwrite.
One model workspace/process lease is not a cross-VM lock. Stop prior VM and
reconcile provider history before another attempt; no global exactly-once claim.

After ChatGPT GitHub review, independent Antigravity audit, separate merge and
reviewed activation/authority, the future Owner procedure is:

1. Bind the exact merged source/notebook/request SHA, true Dataset/Output versions,
   original projection seal, model/checkpoint/rights, finite job/call/GPU-time/
   deadline/stop rules. Do not copy InternVL's grant or operate its running session.
2. Attach only the exact TRAIN/master and MiniCPM checkpoint sources in the table;
   use the isolated pinned worker (`minicpm4.requirements.txt`). Allocate reviewed
   scratch/output reserves and measure environment/CPU/GPU gates on the same path.
3. Use a fresh Mini workspace for initial, or import all verified same-series
   ancestors for resume and recompute the bounded plan. Supply the exact reviewed
   request to the notebook entry only after source activation. No default calls.
4. Save Version/Save & Run All on Kaggle only inside that future authorized release.
   Antigravity observes for at most15 minutes, checkpoints RUNNING_UNVERIFIED and
   exits if running; resume the same conversation for terminal collection. Do not
   submit another job because a monitor timed out.
5. Collect per-attempt ZIP + sidecar and supervisor ZIP + sidecar, all raw/native/
   request/sample identities/logs/errors/accounting, source/notebook/Input hashes,
   provider job/version/status and receipts. Independently verify SHA/CRC/members,
   full3,763 operational status coverage and lineage. INVALID is not a success.

Current missing gates: ChatGPT review; independent Antigravity audit; separately
authorized merge and executable source release; authentic original projection and
Dataset-version bindings; O2–O6/rights/budgets where not evidenced; current provider
history/quota; final-source target ABI/GPU/model-fit/load/inference/export evidence.
Existing PR177/174/Issue173 evidence is retained; none is silently promoted to this
new source or to scientific qualification. No live smoke is permitted by this task.
