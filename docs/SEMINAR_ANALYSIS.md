# Seminar CPU analysis — M3-01

M3 implements SHA-bound M2 v1 formulas and R1–R5 on **SYNTHETIC — NOT RESEARCH
RESULT** inputs. Status remains IN_PROGRESS / DRAFT, pending review and verified
merge. R5 scientific conclusions remain `PENDING_ANALYST_M4`.

From the repository root, Python 3.11+ and Git are sufficient; no installation,
image, model, dataset or runtime dependency is needed:

```console
python -B scripts/analyze_seminar.py --config docs/research/seminar_analysis_config.v1.json --output-dir data/processed/seminar/m3-synthetic-review
python -B -m unittest discover -s tests -v
```

The output directory must be new and below `data/processed/seminar/`. Even an
existing empty directory is refused. All derived files are Git-ignored. A failed
write may leave an incomplete directory without a success receipt; diagnose the
failure and use a new directory. Nothing is silently removed or overwritten.

## Authority and immutable contract

[PR #135](https://github.com/tantdna2/SafeShift/pull/135) merged at
`28fdf82512577f2ed0fb435fb2c12b88e82baf2f`. The
[ChatGPT post-merge verification and M3 assignment](https://github.com/tantdna2/SafeShift/pull/135#issuecomment-6409830030)
was read directly through the GitHub connector before implementation. The small
[authority receipt](research/m3_cpu_authority.v1.json) records those verified
facts and the bounded grant; it is not a new scientific decision.

Before constructing the fixture, the CLI checks the approved config path, both
scientific hashes, pinned authority receipt, M2 decision JSON from the verified
merge, immutable local decision prefix, merge parents, ancestry of HEAD and local
`origin/main`, task/permission fields, `config.protocol.sha256`, scientific Git
blobs and the Git-tracked evidence receipt hash. Missing Git objects/refs or
authority fail closed. Runtime verification is offline against pinned evidence;
it does not claim to refresh live GitHub state.

| Immutable file | SHA-256 |
| --- | --- |
| `docs/research/SEMINAR_PROTOCOL.md` | `54c5be6b67e768f8d4819193c5d06867edf02e2008db258731f6e5947ed06dc1` |
| `docs/research/seminar_analysis_config.v1.json` | `dd3b86660f0795dba099abac0d8a3b8bd3498e625e49b128aa9c50e72639e5ff` |

Original `frozen=false`, PENDING and null refs remain unchanged. Approval comes
from DEC-20261026-M2 plus verified merge and assignment. No real-artifact, GPU,
inference, raw replay, TEST, image/label, external-resource or thesis right is inferred.

## Inputs and implementation

The CLI accepts only `--config` and `--output-dir`; there is no input-path,
real-data or override switch. It never opens `reference_artifact_allowlist` paths.
Marking an external file SYNTHETIC cannot admit it to the CLI.

`saved_reports.synthetic_fixture` builds twelve hand-authored records and twelve
unit archives in memory: four per quantitative model. Q3 has ten SUCCESS, one
TECHNICAL_ERROR and one NOT_ATTEMPTED. IDs, predictions, scores and grouping
metadata are invented. No research payload is copied. Unit run/attempt IDs have
a `synthetic/` prefix; source identifies the verified base, not a model execution.
No randomness or threshold fitting is used.

T3763/V3539/M224 identify protocol **roles** in this rehearsal, with actual
counts 12/10/2 explicitly distinguished from unvalidated real expected counts.
REC224 is reference-only, never pooled. Synthetic transport is ZIP → TAR →
manifest/binding/result/CSV. Each layer checks hash/size, closed member inventory,
duplicates, file type, CRC, source/revision/release/run/attempt/config, ordered IDs,
image-hash metadata, journal flags and totals. No extraction occurs. Portable
paths and existing symlinks/Windows reparse points are rejected before file I/O.

Native byte-only adapters `report_rows`, `internvl_rows`, `archive_report`,
`verified_archive_members`, `verify_v4_shard` were moved from the existing CLI
into `saved_reports.py`; the old CLI imports them. Existing tests remain in place.
Archive checks now reject unsafe/duplicate names even outside readable members.
The original S2 ZIP/sidecar checker retains its original pins in the old CLI and
is exercised by existing synthetic tests. M3 never runs that legacy CLI or
acquires its historical artifact permissions.

Normalized record version `safeshift-seminar-record-v1`:

| Fields | Contract |
| --- | --- |
| sample_id, split, true_level, folder_domain | Exact TRAIN metadata join, canonical GT, no coercion |
| model_id, revision, release, shard, run_id, attempt_id, source_commit, config_sha256 | Bound identity; Q25 unknown attempt remains null |
| native_status, attempted, persisted, parsed | Separate execution/output axes; no-output excluded from confusion |
| generated_label, hnlo_score, label_reason, score_reason | Explicit INVALID/missingness; finite supplied scores; null needs reason |
| input_ref, evidence_level | Member reference and SYNTHETIC evidence |
| byte_sha256, pixel_sha256, point_id, source_family | Invented grouping metadata, never image loading/source identity |

Native SUCCESS requires canonical label and finite score. The normalized API
also tests INVALID and missing score without relaxing the native rule. Score
with INVALID needs an explicit synthetic independent-score contract. Missing,
extra or duplicate planned IDs fail. P/O/L/F/J are established before metrics.

The metric engine reuses `classification_metrics`, `weighted_auc`, `components`
and `summarize_groups`. It implements M2 binary denominators, macro recall over
present classes, same-J controls, dangerous errors/bounds, kappa/entropy/ordinal
disagreement, shared errors/complementarity, error-positive association, B04 and
whole-tie-block risk–coverage. Ten sensitivity variants run on both cohorts;
domain panels retain full-cohort weights. No new metric or threshold is selected.

## Outputs and trace

| Report | Files |
| --- | --- |
| R1 | `R1_evidence_coverage.csv`, `cohort_membership.json`, `ledger.csv` |
| R2 | `R2_classification_ranking.json`, `R2_classification_ranking.csv` |
| R3 | `R3_dangerous_errors_sensitivity.json`, `R3_dangerous_errors_sensitivity.csv` |
| R4 | `R4_disagreement_errors.json`, `R4_disagreement_errors.csv` |
| R5 | `R5_trace_limits.md`, `summary.json` |
| Provenance | `receipt.json` |

There are **12 files**. JSON report schema is `safeshift-seminar-output-v1`, with
notice, structured `details` and long `rows`. CSV includes M2 keys, stable row ID,
numerator/denominator/value/status/reason/membership plus planned/eligible/support,
exclusions/run/input refs/evidence and JSON pointer (relative to `details`).
Counts stay counts; AUC numerator is pair concordance. Null becomes an empty CSV
cell with a reason, never NaN/Inf. Confusion and curve arrays remain in JSON.

R5 maps S-RQs to exact R1–R4 row IDs/input refs in `summary.json`, with no generated
scientific answer. B01 has exactly 19 BLOCKED placeholders; B02 controls N/A,
B03 saved-report provenance limits and B05 mismatch/proxy BLOCKED remain explicit.
Moondream2 stays N/A in applicable model tables, never zero or a fabricated vote.

Receipt includes authority/merge/source SHA, source file hashes and dirty flag,
protocol/config/evidence/input/archive/member/output hashes, command/environment,
seed=null and output path. Eleven outputs are hashed; receipt has no self hash.
Timestamp and path are receipt metadata; reports are deterministic across run dirs.

| Exit | Meaning |
| ---: | --- |
| 0 | Complete synthetic output and receipt |
| 2 | Invalid arguments/data/schema/cohort |
| 3 | Missing authority/Git evidence or denied path/capability |
| 4 | Hash/size/archive integrity failure |
| 5 | I/O failure, including overwrite refusal |

## Acceptance evidence

Validation on 26/10/2026: `python -B -m unittest discover -s tests -v` completed
**77 tests, OK, 0 skipped** (15.349 seconds). The suite includes two full CLI
runs with equal output hashes and rejected overwrite attempts. An additional
direct CLI run to `data/processed/seminar/m3-validation/` exited 0 and produced
all 12 files. The directory is Git-ignored. The approved protocol/config hashes
above were rechecked unchanged. The final clean-source rehearsal and exact HEAD
are recorded in the Draft PR; source-file hashes also bind uncommitted rehearsals.

| Check | Synthetic tests |
| --- | --- |
| C01 | ID/label/domain/TRAIN exact joins and literal membership digest oracle |
| C02–C03 | Four units, source/run/revision/attempt/config/order, partial ledger, Recovery separation; native S2/V4 tests retained |
| C04–C05 | Finite score/direction, exhaustive pair-enumeration oracle with ties/nonuniform weights, paired controls |
| C06 | P/O/L/F/J, INVALID, missing/nonfinite score, missing model, empty/one-class |
| C07 | Hand confusion/error/bounds/entropy/kappa/curve oracles, B04, error-positive, all-agree/all-invalid/zero-error |
| C08 | Ten variants × two cohorts, independent BFS/transitivity, no outside bridge, null keys, representatives/domain weights |
| C09 | Moondream2 N/A, B01/B02/B05 and R5 limits |
| C10 | Authority/hash tamper, archive/CRC/member/path/link rejection, complete CLI/schema/receipt, determinism/overwrite |

No skipped tests. CLI runs with `python -S -B` under an audit hook fencing
application file reads, forbidding network/model imports and allowing only Git
subprocesses. The pure reader/analysis test denies all filesystem opens. Windows
link/reparse rejection uses mocked OS metadata without administrator link-creation
rights; this test runs rather than skipping.

Real-artifact counts/AUC, image/raw/token validation and M4 findings are
**NOT_RUN / NOT_AUTHORIZED**. M4-01 follows only after verified M3 merge and a
separate grant naming artifacts/hashes/members. Tests do not grant merge rights
or establish scientific acceptance.
