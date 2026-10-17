# Two-model synthetic HNLO one-click PREP — 2026-10-17

Base: `main@6143717b1647df1ed1b2d5b0a0f23e9b03f4a9e5`, merged PR #111.
This task prepares code and CPU simulations only. **Real GPU/model execution:
NOT RUN. HNLO_RESEARCH_VERIFIED=false.** DEC-PA3-011 remains PROPOSED; D9R22
remains EFFECTIVE. No InspecSafe, TEST, labels, GT or baseline result is read.
Moondream2 is outside this two-model technical probe, without changing the
four-model proposed Seminar roster.

The complete upload artifact is
`notebooks/SafeShift_HNLO_Qwen3_InternVL3_ONE_CLICK.ipynb`. It has one executable
cell, no editable configuration, and actual orchestration. After the release
and authority gates below, Owner uploads it unchanged, selects GPU T4 x2 and
Internet ON for provisioning, then uses Save & Run All **once**. Owner does not
edit source, SHA, revision, paths or dependency versions. Public checkpoints do
not normally require a token. If authentication becomes necessary, an optional
Kaggle Secret named `HF_TOKEN` is read without displaying it and passed only to
the model-provision child; inference receives no token.

## Source verification and the remaining human approval

Preparation does not authorize execution. The new authority contract is
`configs/diagnostics/hnlo_one_click_authority.v1.json`, with **grant=null**.
Historical P2/PA3 authorities do not apply. The scope fixes two immutable
revisions, the exact gray RGB image hash, C1 hash, FP16/NONE, runtimes, order,
one load/generate per model, no retry/prefix/calibration, no data/GT, offline
boundary and proposed numerical tolerance. Success never approves research HNLO.

The existing PR #111 PREP note requires a separate Lead research/protocol
decision and exact GPU-probe authority, raw-provenance criteria, numerical
tolerance and retention approval. ROADMAP's stage 3→4 also requires a research
decision before GPU work. A merge alone supplies none of these permissions.
To keep DEC-PA3-011 PROPOSED, the Lead would need to record an **explicit exception
limited to this synthetic technical capability probe**, without approving the
Seminar protocol or data inference. The `technical_probe_exception_approved`
field and decision URL are mandatory. This PREP proposes that route; it does
not assert that the Lead has accepted an exception. Otherwise GPU work remains
BLOCKED pending the decisions required by the current roadmap.

The following are **release maintainer actions in this same PR**, not notebook
edits or Owner commands:

1. ChatGPT reviews the Draft directly on GitHub; Antigravity performs the
   separately requested independent audit. This task invokes neither audit nor
   merge. Reconcile findings before freezing.
2. Final reviewed implementation is one F1 child of the exact BASE above, with
   null grant. `scripts/build_hnlo_one_click.py` deterministically builds the
   notebook and whole tracked-source lock. If any payload bytes change, rebuild
   and review the resulting notebook/lock before F1. No silent repinning.
3. Only the Research Lead may add an F2 child changing **only** the authority
   file's `grant`. Fill all schema fields, bind F1 SHA and notebook payload
   SHA-256, give a unique attempt ID and durable Lead/audit review URLs. All six
   approval flags must explicitly be true. `approved_by` text is not an electronic
   signature: authenticity comes from the reviewed repository release and its
   external Lead/audit records, which the reviewer must inspect.
4. Standard Merge Commit M, parents `[BASE,F2]`, tree identical to F2. Squash,
   rebase, unrelated main movement or payload drift fail closed and require a
   reviewed new freeze; the Owner does not fix a notebook locally.

The notebook discovers exactly one PR for its fixed repository/head branch via
GitHub API. Discovery uses a mutable listing **only to locate M**; it never
executes latest main. It clones without checkout, selects M by immutable SHA,
verifies F1/F2/M topology, origin/main ancestry and every tracked file against
the embedded payload SHA. The lock excludes itself and the authority file;
the latter is checked against the immutable contract and authority-only diff.
Notebook hash normalization replaces only its embedded payload digest with 64
zeros, resolving self-reference without excluding its executable cell. A dirty
tracked checkout or changed file inventory is rejected. All child workers repeat
the local topology/payload/authority checks before importing ML.

## Provisioning and isolation

There are two fresh interpreter prefixes and two fresh Hub caches. Neither uses
the Kaggle kernel's Python/site-packages. Source checkout, weights, build trees
and environments live in a fresh temporary workspace **outside** Kaggle Output;
they are not exported as tens of GB of notebook Output. Raw capture journals
are written directly below the session's `data/processed/hnlo_capture/` inside
`/kaggle/working/` before parse, and later copied/verified into the evidence
package. Thus a kill before collection still leaves already-written raw files
in the Output venue. No failure evidence is deleted to save space.
CPython source tarballs come from
python.org with pinned SHA-256; `configure`, `make -j2`, `make install`, bundled
ensurepip and one package install per prefix run automatically. Source downloads
and build/install logs remain in the session. Build tools and development headers
must exist on the venue; failure is retained with no fallback interpreter.

| Model | Exact environment | Visibility and load |
|---|---|---|
| InternVL3 | Python 3.11.11; torch 2.6.0+cu124; Transformers 4.52.4; complete existing runtime plan pins including torchvision 0.21.0+cu124 | Child env `CUDA_VISIBLE_DEVICES=0`, one T4, existing NativeScorer FP16/SDPA |
| Qwen3 | Python 3.12.13; torch 2.10.0+cu128; Transformers 4.57.1; accelerate 1.11.0; hub 0.36.0; safetensors 0.6.2; Pillow 11.3.0; zlib 1.2.11 | Child env `CUDA_VISIBLE_DEVICES=0,1`; existing exact audited embedding-on-CPU device map; allocator set before torch |

The Qwen environment explicitly adds tokenizers 0.22.2 (the previous CPU T1
version), NumPy 1.26.4 and matching torchvision 0.25.0+cu128 for the official
processor. These dependencies are reviewable in the build config and runtime
check; they do not change the audited loader, preprocessing or precision. All
other resolved distribution versions and pip download hashes are retained.
This PREP has not installed/executed either complete GPU environment.

Qwen's previously audited zlib 1.2.11 pin is easy to miss. The builder compiles
that exact official fossil archive into Qwen's own prefix and links CPython via
explicit include/library flags and rpath; runtime requires both compile-time and
loaded zlib versions to be 1.2.11. It does not accept a managed interpreter with
a newer zlib. CPython release sources and hashes: [3.12.13](https://www.python.org/downloads/release/python-31213/),
[3.11.11 archive](https://www.python.org/ftp/python/3.11.11/Python-3.11.11.tar.xz),
[zlib 1.2.11 archive](https://zlib.net/fossils/zlib-1.2.11.tar.gz).
The latter two were streamed and hashed during preparation; no model weights
were fetched. Python 3.12.13 SHA is also published on its official release page.

InternVL uses the existing `provision_or_verify`, full committed inventory and
checksum verifier. Qwen uses `cached_snapshot`, `weight_files`, `verify_weights`
from the existing provision script, extended with the entire exact-revision
flat inventory (config, index, tokenizer, processor, generation config, all four
shards, README and attributes). Metadata was read from the official pinned
Hugging Face revision endpoint; original documentary weight hashes are checked
for consistency. Both offline workers rehash full snapshots again. No `main`
revision, replacement checkpoint, resume/repair of a failed cache or weights
in Git. Hub HTTP transport may retry connections internally; the orchestrator
never retries a provision stage, model load or generate call.

All online preparation finishes before either inference. Each inference/replay
child starts with offline Hub/Transformers flags, no inherited token or proxy,
and installs an irreversible x86_64 Linux seccomp filter before ML imports.
It denies INET/INET6 socket creation and native network calls, namespace changes
and io_uring; ordinary Python sockets are additionally denied by the reused
`network_denied` guard. Children have no inherited network descriptors. A filter
installation/self-test failure blocks execution. The Kaggle Internet UI toggle
stays ON; **this is process-level native network denial, not a claim that the
venue toggle was programmatically disabled**. Historical P2's venue-OFF instructions
are not reused as an execution grant. The new scope explicitly declares this
boundary for Lead review. CUDA/driver interaction with the filter remains a real
Kaggle risk; the code must not relax it after a failure.

Host admission requires Linux x86_64, two T4s, ≥13 GiB free VRAM/device, ≥24 GiB
available RAM, ≥50 GiB free scratch disk, ≥4 GiB free Output disk and required build tools. The disk/RAM figures
are conservative engineering admission estimates, **not measured feasibility**.
The two checkpoints alone total about 22 GB decimal; environments, build trees,
pip unpacking and evidence need additional space. Smaller Kaggle volumes produce
an explicit BLOCKED result. No quota/GPU/precision fallback is implemented.

## Actual probe and evidence

The fixed input is one 448×448 solid gray (128,128,128) RGB PNG for both models.
Its stored DEFLATE encoding is deterministic across zlib versions. The unmodified
prompt is loaded by `render_prompt`, which checks the committed C1 SHA.

InternVL3 runs first, its process exits and GPU memory is checked, then CPU replay
runs with `CUDA_VISIBLE_DEVICES=''`; Qwen3 follows the same sequence. One native
load and one native `generate` at most, batch 1, greedy, max 32 tokens. Method
instrumentation logs invocation and return separately, rejects a second call
and returns native values unchanged. No second generation, response repair,
calibration, forced prefix, hidden control or output pooling.

The merged PR #111 capture is reused unchanged. It saves sequences/input IDs,
all step raw logits/processed scores, runtime T1's 28 checks and ordered four
label IDs, effective config and full provenance before semantic parse. Raw
failure data stays append-only. Native checkpoint forcing defaults are rejected
before generate. RAM/VRAM peak/current snapshots and elapsed time are recorded.
The temporary invocation observer also records the **actual constructed** logits
processor and stopping-criteria lists without changing either returned list.
The pinned [4.57.1 generation source](https://github.com/huggingface/transformers/blob/v4.57.1/src/transformers/generation/utils.py)
and [4.52.4 source](https://github.com/huggingface/transformers/blob/v4.52.4/src/transformers/generation/utils.py)
append raw logits after the processor call. This probe requires an empty actual
processor list to exclude in-place mutation, plus only native length/EOS stopping
criteria. An unexpected processor makes the attempt N/A without clearing it or
retrying. Raw/processed equality alone is never accepted as provenance proof.
An exception inside a blocking native generation cannot produce invented partial
tokens; counts/traceback remain, and unavailable tensors are reported unavailable.

The fresh CPU replay reopens and verifies the sealed journal, cross-checks native
IDs/step counts against trace, reuses `review_trace`, and retrieves the four
values again from the full saved vector at its proven decision step. It computes
the unchanged `anomaly_log_odds(log_softmax(four))` only on valid finite alignment.
The proposed tolerance (absolute and relative 1e-6) requires explicit approval;
it concerns same-evidence scalar comparisons, never different generations.
No GPU/CPU bitwise equality claim or new Seminar metric is made.

`CAPTURE_VALID`, `ALIGNMENT_VALID`, `TECHNICAL_HNLO_VALID` are independent observed
flags; `HNLO_RESEARCH_VERIFIED` always remains false. INVALID, alignment failures,
nonfinite values, OOM and runtime errors keep HNLO=null/N/A. EOS positions and
terminal EOS versus exact token cap are reported; unexplained early stopping
cannot become valid. InternVL's model-local failure can leave Qwen runnable;
permission/source/checksum/storage/network/shared-resource failures stop both.
An unrecorded/killed worker is conservatively a common failure. No retry.

Each run exports directly under `/kaggle/working/` a fresh `.tar.gz`, manifest,
SHA-256 receipt, JSON result, Markdown report and logs. The tar contains both
models' completed/partial evidence, journals (including torn bytes) and reports;
it excludes environments, cached weights and secrets. Every archive member is
rehash-verified against its manifest. A packaging failure leaves its partial tar
and evidence plus a separate export-failure record; no overwrite or deletion.
The final Markdown table is populated from returned states, never default PASS.

A persistent local attempt claim rejects a second Run All with the same grant
even after failure. An isolated brand-new Kaggle filesystem has no trusted
cross-session counter: the Lead/Owner must not reuse the one-attempt grant in a
new session. Enforcing global single-use against deliberate fresh-session replay
would need an approved external transactional authority service; this PREP does
not invent one or claim local state proves global non-replay.

## CPU validation and limits

Tests run the actual notebook cell declarations/invocation with external venue
operations replaced by synthetic CPU fakes. Real journal/persistence/replay,
HNLO formula and tar/manifest code are exercised. A separate temporary real-Git
fixture checks F1/F2/M topology and whole-file/inventory rejection. Fake runtime
objects verify exact Python/distribution/CUDA/visibility constraints, separate
interpreter install targets and native call limits. Injected cases include
download error, wrong checksum, wrong environment, missing GPU, INVALID,
misalignment, nonfinite raw vector, OOM, killed process, interrupted journal and
failed packaging. No fake result is checked in as GPU evidence.

CPU validation on CPython 3.11.9 / Windows (Pillow 11.3.0):

```text
python -m unittest tests.test_hnlo_one_click tests.test_hnlo_capture tests.test_hnlo_t1_cpu -q
68 tests: OK; four skip events (Linux seccomp whole test + three inherited Windows symlink subcases).

python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q
222 tests: OK; two opt-in real-tokenizer tests skipped because snapshots were not supplied.

python -m unittest tests.test_hnlo_one_click -q
26 tests: final one-click recheck after export/log/resource-report/scratch-placement changes; OK (one Linux seccomp skip).
```

Notebook JSON structure, all code-cell ASTs, its embedded bootstrap/source-lock
binding and all 534 locked source-file hashes are checked by the new tests.
`py_compile` is run for every new Python module, builder and test;
`git diff --check` and staged-file review are required before the F1 commit.
No `nbformat` package is installed in the CPU interpreter; validation uses
stdlib JSON/AST plus explicit notebook v4/cell/outputs/source-lock checks.
An initial test used a Windows-incompatible path assertion; it was corrected.
An initial regression invocation named a nonexistent `test_internvl3_runner`
module; the correct InternVL3 prep/runtime modules passed in the 222-test run.
These were test-invocation/fixture issues, not GPU outcomes.

Actual
Kaggle compilation, package availability/resolution, driver/ABI compatibility,
seccomp/CUDA interaction, exact zlib dynamic linking, both full model loads,
response validity, capture memory cost, host kill/output retention and Hub/GitHub
access remain unverified. A technical success on the gray image would prove only
that particular capture, not Seminar performance or research validity.

Stop at one Draft PR for direct GitHub review, then independent audit. No merge,
grant, real model execution or change to dataset/parser/C1/HNLO formula/runners.
