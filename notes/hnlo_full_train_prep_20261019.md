# Two-model HNLO full TRAIN baseline — PREP, 2026-10-19

**PREP ONLY. No TRAIN/TEST image, annotation, checkpoint, CUDA or model call is
performed in this task.** The new authority has `grant=null`. DEC-PA3-011 remains
PROPOSED, D9R22 EFFECTIVE. Moondream2 is deferred from this execution preparation
and remains mandatory for the eventual four-model Seminar.

Base: `1b2a2bdafdcc30c2144637829ab04396821f5e73`, verified against fetched
`origin/main`. Branch: `prep/hnlo-two-model-full-train-20261019`. Worktree:
`.worktrees/hnlo-two-model-full-train/`. Historical Qwen2.5 code/results,
production runners, LS1 formula/parser, C1, original manifests and every previous
release/authority are unchanged. Only append new decision/task entries.

## Existing evidence and what it establishes

The two linked GitHub comments were read directly on 2026-10-19. This task does
not re-open their large raw archives or repeat synthetic generation.

| Model | Verified documentary record | Condition and limitation |
| --- | --- | --- |
| Qwen3-VL-8B-Instruct | [PR #112 technical result](https://github.com/tantdna2/SafeShift/pull/112#issuecomment-6259305190), actual 2026-10-17 | Python 3.12.13, torch 2.10.0+cu128, Transformers 4.57.1, 2 T4, T1 28/28, 10 steps, decision 7; TECHNICAL_HNLO_VALID=true, HNLO_RESEARCH_VERIFIED=false. |
| InternVL3-2B-hf | [PR #116 technical result](https://github.com/tantdna2/SafeShift/pull/116#issuecomment-6259226428), actual 2026-10-19 | Python 3.11.11, torch 2.6.0+cu124, Transformers 4.52.4, visible GPU 0, 14 steps, decision 10; TECHNICAL_HNLO_VALID=true, HNLO_RESEARCH_VERIFIED=false. |

Both grants are consumed. Their one-image PASS establishes the exact synthetic
technical path; it provides no TRAIN performance, real-image throughput, accuracy,
worst-case resource guarantee or new data authority. InternVL3's source record
discloses a combined-result driver flag overwritten by CPU replay. This PREP keeps
that history, uses the individual worker's final driver observation, and never
relabels the old result. Monitoring remains PARTIAL, local relay UNOBSERVABLE;
neither absence of events nor technical PASS is a SECURITY_PASS/NO_LEAK claim.

The [Qwen2.5 CPU completion](pa3_r2_cpu_completion_20261015.md) supplies the
historical comparison: all 3,763 SUCCESS, raw recomputation on Linux, pooled HNLO
AUROC 0.8266558463706973, generated binary-label AUROC 0.5, four-level accuracy
130/3763 and binary accuracy 749/3763. TRAIN was previously exposed. Missing
Shard 1 outer receipt and Windows 1-ULP portability remain limitations.

## Exact cohort and label separation

Use the existing four inference manifests byte-for-byte, retaining order, IDs
and image SHA-256. The full manifest's hash is
`a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`.
Shard sizes are **941/941/941/940**. `cohort.inference` pins all four original
file hashes, verifies unique complete membership and the original seeded
partition; it does not enumerate raw data. CPU tests use those tracked manifests
as documentary identity evidence and synthetic objects for runtime tests.

Original IDs and image locators encode level/domain even without explicit GT
fields. Therefore the supervisor alone holds original ID/locator/hash rows.
After the new unit's TRAIN approval, it opens **only** each original listed JPEG,
hash-verifies and copies unchanged bytes under ignored
`data/processed/hnlo_train_inputs/<run_id>/<ordinal>.image`. It never opens the
neighboring JSON/TXT or TEST. A private, unpacked TRAIN mount is a prerequisite;
automatic discovery checks fixed directory names in mounted inputs, never scans
TEST or extracts a mixed archive. More than one matching mount blocks.

The inference request contains only consecutive ordinal and image hash. The
worker receives no canonical sample ID, class, domain, group, original locator
or annotation. Predictions are free C1 generations. Full-manifest GT is opened
only by the separately authorized CPU evaluator, after verifying an immutable
custody seal of raw files. This is an audited code/data-flow boundary; the
network guards are not an OS filesystem sandbox against malicious replacement
code. The parent verifies the complete source lock; the worker rechecks executable
Python/config/prompt bytes and Git topology without hash-reading data manifests
or historical result documents. Source locking is necessary to this claim. The
CPU label approval covers reading/validating the original full TRAIN metadata
table, with per-unit metrics using only its approved shard IDs.

No filtering of hard, duplicate, failed or historically cross-split-linked images;
no split, GT, level mapping or group changes. Every planned ID receives a result
row. The inferential limits of previously exposed TRAIN remain unchanged.

## Proposed evidence contract — Lead decision required

`BASELINE_SUFFICIENT_RAW_SUMMARIES_V1_PROPOSED` is an explicit proposal for the
two new runs. It is **not approved** by this PR. The new per-unit
`evidence_contract_approved` flag must be true in a later Lead release before any
data/provisioning/GPU step. This proposal follows the existing Qwen2.5
`QwenRawScorer.generate` / `summarize_tensor` retention level; it does **not** claim
to offer the full-vocabulary replay of the earlier synthetic probes.

For every native generation, before the first decode, fsync/read-back/hash:

1. Native input IDs, complete native generated sequence, generation config and
   actual kwargs, candidate IDs in **Level01–04 order**, tensor dtype/shape/device,
   raw/processed step counts, and actual input shapes.
2. For **every** returned step, separately for native raw logits and processed
   scores: exact four candidate values, generated-token value, global argmax
   ID/value, full-vocabulary logsumexp and NaN/+Inf/-Inf counts. These are the
   unchanged baseline reductions; no clipping, normalization or softmax is
   applied before selecting raw logits. Nonfinite observations are retained.
3. Actual empty logits-processor list and native MaxLength/EOS settings. The
   pinned generation-source checks establish the raw-output semantics under
   an empty processor pipeline; raw/processed equality alone is insufficient.
4. Then decoded native text and the complete trace. Seal this sample before
   parser/alignment/scorer. Native malformed output remains INVALID; no rescue.

Unit provenance records exact model/revision, tokenizer file checksums/T1,
processor class/config, software inventory, snapshot inventory, source/authority,
prompt, generation defaults, placement, memory, command arguments, UTC sample
start and native invocation counts. CPU reports record their Python/platform,
tokenizer package versions and exact source commit.
The supervisor binding provides canonical ID/image hash/run association without
passing class-bearing identifiers to inference. Ordinals bind each sample's raw
seal to that immutable mapping.

CPU replay independently re-runs the existing strict parser, all 28 runtime T1
mappings, decision alignment, `score_decision`, `native_score.score` and existing
HNLO calculation. It checks four raw values by label ID, native/trace/step
agreement, greedy/stop settings, canonical identities, source and custody hashes.
Mathematically the unchanged score is `logsumexp(z01,z02,z03)-z04`; processed
scores never enter it. No HNLO threshold is introduced.
Saved/recomputed result comparison remains exact; this PREP introduces no
floating-point tolerance or repair for the historical Windows portability issue.

**Audit boundary:** the retained four raw decision logits suffice to recompute
HNLO. Full-vocabulary reductions and nonfinite counts can be checked for internal
consistency, but cannot be independently regenerated without discarded native
vectors. The audit says `full_vocab_replay=false`, explicitly. Local checksums
establish integrity, not authenticity or correctness of a reduction made by the
trusted source/runtime. If Lead requires full-vector independent reduction
replay, this contract must be rejected and redesigned before release; do not
claim the synthetic full-vector standard has been met.

Each sample has a conservative **2 MiB primary-JSON** evidence cap (plus receipts
and seal). Exceeding it stops the unit and retains prior bytes; it never truncates
records to manufacture compliance. A filesystem failure can leave torn files;
those bytes are retained and inventoried by the supervisor custody seal, with
PARTIAL capture integrity and INTERRUPTED/failed rows. Custody sealing does not
turn a torn capture into a valid sample. Hard venue termination can prevent even
the supervisor export; no code can guarantee persistence after total VM loss.

## Kaggle execution units and resource evidence

Eight generated notebooks: `notebooks/SafeShift_HNLO_TRAIN_<model>_SHARD<0..3>.ipynb`.
Each has one Run All cell, an embedded complete source-payload digest and fixed
model/shard. Owner makes no code/SHA/path edits. Each unit has its own
`hnlo-train-v1-<model>-s<shard>-a1` run ID, one attempt, one load, at most one
generate per planned ordinal. No resume, fallback, repeated failed image,
automatic redistribution or retry is implemented. Fresh sessions require a
Lead/Owner global attempt ledger; the local exclusive ledger alone cannot stop
someone deleting outputs or opening a fresh Kaggle VM.

After approvals/release only: upload the matching notebook unchanged, attach
exactly one private unpacked approved TRAIN input, select T4 x2, enable Internet
for source/software/checkpoint provisioning, and Save & Run All once. The fixed
release branch discovers its one reviewed PR. Bootstrap rejects Draft/unmerged
source, requires the exact BASE → F1 → authority-only F2 → standard merge,
unchanged merge tree, full tracked-byte lock and exact detached release checkout.
Any source change requires a newly reviewed release and cannot reuse this grant.

Sequence: source/authority → consume unit ledger → host preflight → exact isolated
Python/software build → fresh guarded CUDA inspect (no model/data) → CPU-only
pinned official checkpoint provisioning → exact TRAIN image staging → fresh
guarded inference → raw custody seal → CPU-only audit/GT join → export.

Qwen3 reuses the audited explicit 2-T4 placement (embedding CPU, visual GPU 1,
layers 0–20 GPU 0, 21–35 GPU 1, head/norm GPU 1), FP16/no quantization/SDPA,
CUDA 12.8, Python 3.12.13 and pinned allocator. InternVL3 reuses NativeScorer's
official tiling/processor at max 12 patches (+thumbnail), FP16/no quantization/
SDPA, T4 GPU 0/CUDA 12.4/Python 3.11.11, with the **unchanged PR #115 loader
after PR #116 guards**, driver handles retained to process exit. No Qwen2.5
pre-merger clamp is applied to either model. Cache/state is cleared each call.
Production runners and historical diagnostic adapters are not changed.

Checkpoint/env and staged images live in ephemeral scratch under ignored
`data/processed/`; weights and input images are excluded from evidence/export.
Cache is verified for the fixed revision before use. A separate unit/VM builds
only its selected environment and obtains its selected model; no mixed Python,
torch or CUDA installation, no cross-model in-memory cache. This costs repeated
setup/download time. Persistent verified checkpoint inputs or a resource pilot
would require a separately reviewed preparation/authority, not an implicit cache
shortcut or reuse of the old synthetic grant.

[Kaggle notebook documentation](https://www.kaggle.com/docs/notebooks), checked
2026-10-19 through web search (the live page is client-rendered), lists up to
20 GB saved output and 12-hour CPU/GPU sessions. The older official
[GPU tips page](https://www.kaggle.com/page/GPU-tips-and-tricks) search excerpt
mentions 30 GPU hours/week and a 9-hour session, so venue/account display must
be observed at execution; neither quota nor session duration is guaranteed here.
The worker's 10-hour maximum is a stop reserve, **not** an assertion it will
finish before a venue cut-off; an observed shorter venue limit requires review
before granting. Setup consumes session time too.

Storage arithmetic from the observed vocab sizes, **not measured TRAIN output**:

| Model | Full raw+processed float32, 32 steps/image | 941 images | 3,763 images |
| --- | ---: | ---: | ---: |
| Qwen3 (151,936 vocab) | 38,895,616 bytes | 36,600,774,656 bytes | 146,364,203,008 bytes |
| InternVL3 (151,674 vocab) | 38,828,544 bytes | 36,537,659,904 bytes | 146,111,811,072 bytes |

These exclude metadata and coexistence with an archive; JSON vectors can be
larger and compression is not assumed. The maximum-step float32 full-vector
contract cannot be promised within 20 GB output even per shard. The proposed
summary cap is 1,973,420,032 primary-JSON bytes for 941 images, plus sidecars,
logs, seal and archive. Runtime guards require 6 GiB free output before start,
512 MiB remaining before each image, conservative inherited 24 GiB available
host RAM/50 GiB scratch, and 13 GiB free VRAM per T4 at admission. These are
admission estimates, not measured peak resources for this real cohort.

InternVL3's historical **one gray image** reached ~3.97 GiB allocated, ~4.18 GiB
reserved and ~8.58 GiB host RSS, per the linked PR #116 comment. Larger/multitile
TRAIN images may require more. Qwen3/InternVL3 TRAIN throughput, RAM, VRAM,
download/build time, disk peaks and 941-image session feasibility are **UNKNOWN**.
No numerical throughput estimate or completion promise is made. An optional
separate pilot proposal must name prospective IDs, consume its own grant, preserve
all failures and explicitly decide how pilot exposure relates to later attempts;
this PREP does not authorize or run that pilot.

Concrete **separate pilot proposal, not covered by this authority**: prospectively
select the first eight original ordinals of shard 0 for each model, unchanged
order/hashes, one load and at most eight calls/model, no retries, separate run
IDs. Record setup/download/load time separately from each image's processing,
generation, fsync, CPU audit/export time, shape/tiling, disk peak, host RSS and
per-device VRAM. Report all eight including failures, never a sample selected
after observing speed. Lead must decide prospective overlap/attempt accounting
with full baseline before approving; no exclusion or rerun is implied. Eight
images cannot establish worst-case throughput or certify a 941-image session.

## CPU evaluation and export

Raw package: per-sample journals and receipts/seals, native IDs, text, summaries,
runtime/source/checkpoint records, per-unit canonical mapping, worker/supervisor
failure records and custody inventory. Every error/partial run is exported where
the host is still alive. Final outputs include archive, manifest, archive and
manifest SHA-256 receipt, result JSON, and the sealed CPU audit report when it can
be produced. Raw image/checkpoint bytes are never in the archive.

The existing `train_report.metrics` and exporter are reused unchanged. They
report pooled HNLO AUROC, generated binary-label AUROC, generated four-class and
binary accuracies, full planned/attempted/persisted/parsed/scored denominators,
SUCCESS/INVALID/TECHNICAL_ERROR/INTERRUPTED/NOT_ATTEMPTED (and inherited
UNPROCESSED field, expected zero), and each domain. Missing classes yield null
AUROC with reasons. Generated accuracy is not HNLO accuracy. Partial runs are
marked PARTIAL_TRAIN_DESCRIPTIVE, with the intended cohort still 3,763.

After copying exact exported evidence trees into `data/processed/` and making
the pinned tokenizer files/source checkout available, independent CPU merge:

```text
python -m safeshift.diagnostics.hnlo_train.audit --repo . --model qwen3 --tokenizer data/processed/tokenizers/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b --runs data/processed/qwen3/s0/evidence data/processed/qwen3/s1/evidence data/processed/qwen3/s2/evidence data/processed/qwen3/s3/evidence --output data/processed/qwen3/pooled
python -m safeshift.diagnostics.hnlo_train.audit --repo . --model internvl3 --tokenizer data/processed/tokenizers/cb57a075cb75a2e6d1b668b128d48bb00ae321d2 --runs data/processed/internvl3/s0/evidence data/processed/internvl3/s1/evidence data/processed/internvl3/s2/evidence data/processed/internvl3/s3/evidence --output data/processed/internvl3/pooled
python -m safeshift.diagnostics.hnlo_train.compare --qwen25 data/processed/qwen25/official_report_linux --qwen3 data/processed/qwen3/pooled --internvl3 data/processed/internvl3/pooled --output data/processed/hnlo_three_model_comparison
```

Commands are future examples, not executed experiments. Use the exact released
source checkout and its retained Git history. Hash-verified tokenizer files only
are required on CPU, not weights. Run each model's audit in its pinned tokenizer
environment; hide GPUs and keep HF offline. Reports are exclusively written;
existing results cannot be overwritten. The pooled evaluator replays raw outputs
and verifies four disjoint shard IDs and all 3,763 result IDs, never averages
shard AUROCs. The comparison importer accepts only the hash-pinned official
Qwen2.5 Linux audit/metrics artifacts from the linked completion note. It retains
that baseline unchanged and shows each model's full coverage, every paired and
three-model SUCCESS intersection, the same eligible IDs and per-domain tables.

## Decisions and remaining release gates

DEC-PA3-016 below is PROPOSED. Research Lead must separately approve the
descriptive TRAIN exception under D9R22/DEC-PA3-011, exact 3,763 cohort and
TRAIN-image reads, selected model/shard attempts, provision/GPU, this summary
evidence contract and its audit limit, raw provenance/retention, post-seal CPU
label evaluation, known duplicate/exposure/confounding risks, resource/venue
interruption risks, unchanged security boundaries and InternVL3 AF_UNIX relay
residual risk. Each selected unit needs all flags and exact identity/source
binding. No omitted model/shard is implicitly approved. No TEST/threshold/tuning,
new data labels, Moondream deletion or protocol freeze follows from these flags.

GitHub review of the Draft PREP comes first. Independent audit is a subsequent
separate user request. Only then a separate source-bound authority-only F2,
Lead-controlled release/merge and Owner execution may occur. No automatic grant,
merge, Antigravity call or Kaggle execution here. Stop after the Draft PR.

## Validation record

Host: Python **3.11.9**, Windows **10.0.26200**. No torch/Transformers installation,
model or real-tokenizer snapshot is provisioned by this task. CPU simulations
inject synthetic native outputs, tokenizers and errors; they are not model
evidence. Actual new-model backend loading/generation with the pinned ML packages,
Linux guard integration for the new unit launcher and Kaggle execution are NOT RUN.

| Check actually run | Result |
| --- | --- |
| `python -m unittest tests.test_hnlo_train -q` | **37/37 OK**, final code run 83.759 s, no skips. Includes original 3,763 manifest identity, opaque GT boundary, staging/hash errors, grant/source/duplicate/retry rejection, raw-before-decode/seal-before-parse, nonfinite/INVALID/error/torn/timeout/interruption retention, pooled AUROC and same-ID/coverage, real-Git release faults, notebook/source hashes and synthetic supervisor export. |
| `python -m unittest tests.test_ls1 tests.test_pa3_native tests.test_pa3_full_train tests.test_pa3_r2 tests.test_qwen_runner tests.test_qwen3_runtime_placement tests.test_internvl3_prep tests.test_internvl3_runtime_result -q` | **257 OK, 6 skipped**, 237.525 s. Two opt-in pinned tokenizers and four unavailable pinned CPU-ML cases; no GPU implication. Expected synthetic failure-package messages are retained. |
| `python -m unittest tests.test_hnlo_capture tests.test_hnlo_t1_cpu tests.test_hnlo_one_click tests.test_internvl3_hnlo_probe -q` | **97 run, 2 failures, 9 skipped**, 236.465 s. Not a PASS. The two exact identities and BASE comparison are below; no historical tests were edited. |
| Same four-module suite with only those two historical identities excluded | **95 OK, 9 skipped**, 163.022 s. Skips are Windows-unavailable directory-link/native Linux seccomp/guarded-ELF checks. |
| `python scripts/profile_hnlo_train.py` | CPU-only synthetic **27-step / 1,000-vocab** journal = **56,800 bytes** including receipts/seal; synthetic 941-image multiplication = 53,448,800 bytes. Not a TRAIN-output estimate. Full-vector arithmetic is tabulated above. |
| Compile all 13 new package modules, two scripts and test | **16/16 compile OK**; worker import leaves `torch` absent from `sys.modules`. |
| Original release locks checked against their own immutable F1 Git archives | PR #112 **534/534**, PR #115 **572/572**, PR #116 **588/588** source-file hashes PASS; each payload digest matches its historical grant. |
| `git diff --check`, append-only decision/task prefixes and protected-path diffs | PASS. New grant remains null; no raw image/data/model/output artifact is staged. |

Historical failure identities:

- `tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt`
  also **fails at exact BASE**: the historical test requires `grant=null`, while
  PR #116's released source has its real grant. The old grant is preserved.
- `tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export`
  passes at BASE but rejects this PREP's required appended `DECISIONS.md` against
  the old F1 lock when run on today's tree. This is an explicit historical
  whole-tree guard conflict, not claimed as a pre-existing failure. The original
  588/588 F1 hashes independently pass; its executable/source bytes are unchanged.

The exact BASE comparison used `git archive` of
`1b2a2bdafdcc30c2144637829ab04396821f5e73` into ignored
`data/processed/hnlo_train_base_checks/`, then the two test identities above;
**2 run / 1 failure**, 3.497 s. Original-source checks use `git archive` for F1
`f7b4201f0ac6b68ada6bd7a2dc90d1cf2b035fcf`,
`3c24b26233954a5ba7410f57d6bcbab112de5b3b`, and
`509d5ab594e5729403b92b268660377278d483e1`; only each lock's own notebook hash
is normalized according to its unchanged bootstrap. An initial verification
helper used the wrong driver notebook name; correcting that helper gives the
572/572 result, with no source change.

The 95-case selection is reproducible with the same four module names and this
standard unittest selector (no production/test-file changes):

```python
import unittest
modules = ["tests.test_hnlo_capture", "tests.test_hnlo_t1_cpu",
           "tests.test_hnlo_one_click", "tests.test_internvl3_hnlo_probe"]
excluded = {
    "tests.test_internvl3_hnlo_probe.ContractTests.test_null_exact_scope_and_new_attempt",
    "tests.test_internvl3_hnlo_probe.NotebookTests.test_single_cell_source_lock_and_bootstrap_failure_export",
}
def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
selected = unittest.TestSuite(t for t in flatten(suite) if t.id() not in excluded)
result = unittest.TextTestRunner().run(selected)
raise SystemExit(not result.wasSuccessful())
```

An initial 31-case PREP run caught a stale generated source-lock digest after
bootstrap editing; regeneration fixed it. Subsequent 35-case and final 37-case
runs passed. The final notebook/source-lock check is rerun after documentary
validation updates and staging. No full-repository suite or real raw-archive
recomputation for the two new models is claimed: there are no new model outputs,
and legacy whole-tree governance tests have the disclosed historical conflicts.
