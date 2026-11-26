# Candidate160 production engineering qualification — 31/10/2026

**READY_FOR_TECHNICAL_REVIEW for both delivery routes.** MiniCPM official FP32
remains **BLOCKED_PENDING_SCIENTIFIC_DECISION**. Neither is READY_FOR_OWNER:
fresh exact-HEAD ChatGPT review, independent Antigravity audit and separately
authorized merge remain outstanding. Draft PR156, same branch, no full160/TEST.

Authority: [Owner follow-up](https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6540904325).
Session resumed clean worktree at `04fa29fa053d1a9fcc49361794a5140f3dc1678e`;
GitHub REST confirmed OPEN/DRAFT, main `6252a7de91d9d98bd68a33b9bc13ae9888f2b9da`.
No branch/PR creation, reset, rebase, force-push or merge.

## Exact Deliverables

- InternVL: `notebooks/SafeShift_CANDIDATE160_PRODUCTION_internvl35.ipynb`.
- MiniCPM: `notebooks/SafeShift_CANDIDATE160_PRODUCTION_minicpm4_FP32.ipynb`.
- Runtime commit: `b5448d031b287bc7adabd58ec36d98e671449b9d`.
- Tested Git export: `2a062e5d0896bd789a7c27db9876fe6406ae2bb6`.
- Shared source SHA256: `09d94fd27a6a5260526c981a55854e8217536e0499824400ea9df5d213fb2d08`.
- InternVL notebook SHA256: `54300f90b1d15119556986aff5e4bbb9e3b12dfbb16d0e46a07df0a7a9a27fec`.
- MiniCPM notebook SHA256: `7ed8821f03861705df4a2b7f2ef019da2901a59cc14d453ab77c2192646bf433`.

Numerical implementation is unchanged from the successful trial:
`minicpm4-resampler-attention-fp32-v1`, descriptor SHA256
`2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da`,
effective configuration `5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00`.
InternVL configuration is
`71dcd6b934fed7bae76ce6bb4cbeeefe2ad0c7e570889f9cf33bb5e9858d7206`.
The numerical descriptor identifies the arithmetic and its original technical
trial authority; it does not authorize production or import trial history.
The new execution profile separately binds campaign/slot/source/series/history.
Baseline/smoke/preflight notebooks were rebuilt deterministically, but the
two PRODUCTION files above are the qualified intended delivery routes.
Original MiniCPM FP16 remains a known numerical failure, not an alternative
qualified Owner notebook.

## Predeclared Live Checks

Profile `train160-production-engineering-v1` fixes ordinals0,15,111 before new
inference: first original image; minimum area; maximum height/width, first ties.
Dimensions are2336×1752,720×404,704×576. Selection used only locked manifest
metadata, not labels/predictions. Manifest/order160/C1/parser/HNLO/checkpoint/
revisions/FP16 weights/eager are unchanged. This is no new scientific cohort.

Default `qualify` uses the production supervisor/CLI/child/controller/history,
one model load,≤3 calls,3600 seconds including setup, metrics excluded.
Then the same exact notebook imports its sealed ZIP into a fresh workspace,
with no checkpoint Input, and verifies resume schedules no work and never
provisions software, observes CUDA, loads weights or calls a model again.
Both jobs used the original private pilot bundle and matching checkpoint
Notebook Output, pinned container, Internet ON, T4x2/GPU0 only. Pulled-back
cell sources, privacy, Inputs and container match the staged notebooks.
Kaggle canonicalized the MiniCPM title/slug; the actual kernel below is recorded.

| Check | InternVL3.5 | MiniCPM FP32 |
| --- | --- | --- |
| Kaggle version | `nguynanhtn/safeshift-internvl35-production-qa-20261031/1` | `nguynanhtn/safeshift-minicpm4-production-qa-20261031/1` |
| Real TRAIN images / calls / loads | 3 / 3 / 1 | 3 / 3 / 1 |
| Weights / inference / finite logits | PASS / PASS /38 of38 steps | PASS / PASS /33 of33 steps |
| Native image paths, ordinals0/15/111 |13/3/13 tiles including thumbnail |10/3/5 slices including global |
| Strict parser, same order | INVALID / SUCCESS / INVALID | SUCCESS / SUCCESS / SUCCESS |
| HNLO | Unaligned /7.301041903017601 validated /unaligned | All unaligned |
| Raw/native/tokenizer replay /ZIP/SHA256/cleanup | PASS | PASS |
| Fresh-workspace sealed-ZIP resume | PASS,0 calls/loads | PASS,0 calls/loads |
| Peak allocated GPU0 observed |13.165 GiB (rounded upward) |9.068 GiB (rounded upward) |
| Official full160 | NOT_RUN | BLOCKED_PENDING_SCIENTIFIC_DECISION /NOT_RUN |

Independent download verification replays all six raw records with the saved
Rust tokenizer, checks native IDs, every saved forward step/argmax/finite flag,
strict parser/HNLO, config/source inventories, image hashes and member/sidecar
checksums. No raw outputs or actual dataset/checkpoint files are committed.

Both jobs physically allocated28 GiB scratch and4 GiB output on separate
filesystems before consumption, then released the admission allocations.
Worker pre-load free RAM was9185 MiB (InternVL) and10531 MiB (MiniCPM);
cgroup observations and per-call GPU memory are in the receipts. The technical
deadline is3600 seconds including setup. These are measured admission checks,
not a guarantee of future provider quotas, sustained RAM/disk or full160 fit.

## INVALID And HNLO Findings

The retained original InternVL raw really includes code fences. Native IDs,
independent decode, empty logits processors and step alignment all match;
this is model format noncompliance, not string/Path, tokenizer or parser wiring.
Its true INVALID stays INVALID. On the predeclared minimum-area case15 the
actual continuation exactly matches a proven native branch; four finite raw
logits at decision step7 produce HNLO7.301041903017601, independently matched
by the Decimal oracle. No prompt/parser/continuation change was needed.
Cases0/111 remain unaligned because no valid strict label exists.

MiniCPM's original and new successful JSON records use a legal alternative
native segmentation: original first generated token4788 versus probe10354;
both decode to the same opening characters. In the original raw, all other
continuation IDs match. This is a non-injective tokenizer decode; identical
text does not prove the locked native continuation. Boundary, empty processors,
greedy alignment, finite logits and CPU tokenizer replay pass. The existing
replay therefore correctly returns
`ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS`.
No token is replaced, branch approximated or sequence likelihood substituted.
HNLO definition and code remain byte-identical. Numeric HNLO is unavailable
for these MiniCPM cases, not fabricated or presented as confidence.

## Local Checks And Recovery Limits

Final full Linux exact-export suite: **374 =334 PASS/40 SKIP/0 FAIL/0 ERROR**.
Separate pinned native numerical suite:8/8 PASS. Actual production
`--check-only --qualification` subprocess: PASS for each model, no mocks for
worker/native_setup/verify_snapshot,160 real authorized image admissions and
eight native processor sizes each. No actual CPU weight inference is claimed.

Initial suite failed one prerequisite: the clean Git archive lacked ignored
`data/processed`. A first rerun incorrectly reused a WSL temporary directory
that did not survive the invocation. The final fresh export created the
directory and passed. Two old native-suite attempts correctly rejected the
production CUDA-build stack because that historical suite requires CPU-only
torch; no pins/guards were weakened. The production native/meta worker checks
and resampler tests ran in their real required stacks and passed. Initial
local test syntax/fixture/path-length errors, stale-ref builder rejection,
OAuth401 and partial Windows download remain recorded; none consumed a GPU
inference attempt. Official SDK refresh restored OAuth without exposing secrets.

CPU faults cover actual load failure, OOM, NaN/Inf, raw before result write,
corrupt raw/ZIP/sidecar, retry/no-op/rerun, series segregation, conflicting
history, locks/process death and export errors. Actual Kaggle proves serial
multi-image operation and sealed-ZIP fresh-workspace recovery on the same VM.
A real forced VM kill, two independent live Kaggle VMs, sustained12-hour run,
all160 sizes/VRAM and global exactly-once are **not** established. Parent/worker
OS locks cover a shared workspace only; Owner must stop old jobs and attach
complete history before new-VM resume.

39 protected contract/source files and72 earlier committed evidence files
verify unchanged, with old private archives retained. Retained FAIL/PASS log
checksums and an invocation-error ledger are in the new [receipt index](evidence/candidate160_production_20261031/index.json).
The receipts are Codex verification, not independent Antigravity audit or CI.

Reproduction: build using
`python -B -m scripts.build_candidate160_notebooks --runtime-ref b5448d031b287bc7adabd58ec36d98e671449b9d`;
run `python -B -m unittest discover -s tests -v` from a clean export with the
ignored `data/processed` prerequisite created. In each pinned production
stack run `scripts.rehearse_candidate160_worker` with `--qualification`,
the locked bundle/snapshot and exact ref; MiniCPM additionally uses
`--implementation minicpm4-resampler-attention-fp32-v1`. Native arithmetic
tests require the pinned MiniCPM stack and `SAFESHIFT_NUMERICS_SNAPSHOT`.
For private archives, `verify_archive` checks members, `train_route.receipt`
recomputes the final qualification receipt and `hnlo.tokenizer_replay` /
`hnlo.replay` independently reproduce decode and numeric/unavailable outcomes.

## Required Scientific Decision

Owner/Lead must explicitly adopt or reject the named FP32-resampler effective
implementation/configuration as the baseline for official scientific TRAIN160.
This is the missing decision; blanket notebook permission is already present.
Official FP32 `resume`/`rerun` is fail-closed before Input/consumption/load,
including direct worker records. Enabling it requires a traced decision and
reviewed activation change; no notebook flag or fabricated approval reference
opens it. A source change still requires bounded final-version requalification.
Scientific result selection/pooling remains separately PENDING.

After fresh ChatGPT GitHub review, independent Antigravity audit and authorized
merge, Owner runs InternVL personally using the PRODUCTION notebook,
`candidate160_action = "resume"`, original Inputs and complete official
Outputs. `rerun` opens a new series. Technical `candidate160_q*` and smoke
Outputs cannot supply official completion. MiniCPM must wait for its scientific
decision and reviewed activation. See the [runbook](../CANDIDATE160_KAGGLE.md).

## Changed Files This Continuation

32 scoped paths relative to the supplied HEAD `04fa29fa053d1a9fcc49361794a5140f3dc1678e`:

```text
AGENTS.md
docs/CANDIDATE160_KAGGLE.md
docs/PROJECT_STATE.md
docs/research/CANDIDATE160_PRODUCTION_ENGINEERING_20261031.md
docs/research/DECISIONS.md
docs/research/evidence/candidate160_production_20261031/alignment-investigation.json
docs/research/evidence/candidate160_production_20261031/index.json
docs/research/evidence/candidate160_production_20261031/invocation-ledger.json
docs/research/evidence/candidate160_production_20261031/kaggle-internvl35.json
docs/research/evidence/candidate160_production_20261031/kaggle-minicpm4.json
docs/research/evidence/candidate160_production_20261031/local-checks.json
docs/research/evidence/candidate160_production_20261031/preserved-history.json
docs/research/evidence/candidate160_production_20261031/release.json
docs/research/evidence/candidate160_production_20261031/remote-internvl35.json
docs/research/evidence/candidate160_production_20261031/remote-minicpm4.json
notebooks/SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb
notebooks/SafeShift_CANDIDATE160_PREFLIGHT_internvl35.ipynb
notebooks/SafeShift_CANDIDATE160_PREFLIGHT_minicpm4.ipynb
notebooks/SafeShift_CANDIDATE160_PRODUCTION_internvl35.ipynb
notebooks/SafeShift_CANDIDATE160_PRODUCTION_minicpm4_FP32.ipynb
notebooks/SafeShift_CANDIDATE160_internvl35.ipynb
notebooks/SafeShift_CANDIDATE160_minicpm4.ipynb
safeshift/candidates/train_contract.py
safeshift/candidates/train_history.py
safeshift/candidates/train_owner.py
safeshift/candidates/train_route.py
safeshift/candidates/train_run.py
safeshift/candidates/train_runtime.py
scripts/build_candidate160_notebooks.py
scripts/rehearse_candidate160_worker.py
tests/test_candidate160_routes.py
tests/test_minicpm_resampler_fp32.py
```
