# QWEN3_FULL_TRAIN_COMPOSITE_V1

Owner [decision6889519264](https://github.com/tantdna2/SafeShift/issues/171#issuecomment-6889519264),
15/11/2026, authorizes this derived TRAIN label table for subsequent SafeShift
TRAIN analyses. It contains **3539 original V4 SUCCESS + 224 Recovery224 SUCCESS**,
one record per original TRAIN ID. This is an implemented saved-report product,
not a proposed run or a claim that V4 completed in one execution. Repository
changes stop at one Draft PR; direct ChatGPT review, independent Antigravity
audit and separately authorized merge remain pending.

## Reproduce and consume

Use Python 3.11+ from the repository root, standard library only:

```console
python -B -m scripts.build_qwen3_composite --input-dir data/processed/qwen3-composite-v1/inputs --train-root data/raw/InspecSafe-V1/train --output data/processed/qwen3-composite-v1/reproduction
```

The output directory must not exist. The command does not change any input,
run, attempt or production ledger. `--train-root` hashes exactly the manifest's
TRAIN JPEG paths as bytes, without decoding or inference. Omitting it still
checks saved image identity against the original master, but explicitly reports
that image bytes were not rehashed. A missing or mismatched image in an explicitly
requested byte check blocks that build; it does not revoke the Owner decision.

Input directory: `qwen3_shard0.json`, `qwen3_shard1.json`, `qwen3_shard3.json`,
`recovery.json`, their four TAR basenames from their export records, and the
original `Qwen3-Shard2-V4.zip`. The
[versioned analysis configuration](../../configs/analysis/qwen3_full_train_composite.v1.json)
pins result/archive/manifest/release identities, exact historical Git files and
the [authenticated Owner export](evidence/qwen3_composite_20261115/owner-decision.json).
The existing immutable history commit must be available in Git. No network,
Kaggle, GPU, weights or raw-output access is required.

Outputs (private, ignored under `data/processed/`):

| File | Contract |
| --- | --- |
| `composite.json` | Versioned downstream handoff: ordered samples, original TRAIN master projection, immutable original status ledger, separate recovery ledger, full per-source identities. |
| `samples.csv` | Same selected records in portable tabular form, including original status/ordinal, selection reason, source/run/attempt/config/revision/source/archive/report hashes, saved HNLO and unavailability reasons. |
| `metrics.json`, `metrics.csv` | Complete ALL/domain/class/source confusion and metrics; CSV has deterministic metric paths and values. Ratio numerator/denominator are separate paths. |
| `audit.json` | Source/member checksums, original scopes and releases, runtime/generation-source summaries, environment, command, code/config hashes, Git HEAD, evidence limitations. |
| `image_verification.json` | Per-ID image SHA256 receipt when byte hashing was requested. |
| `manifest.json` | Sizes and SHA256 of all six output files. Retain its SHA separately as the trusted handoff. |

Validate before consuming, substituting the retained SHA256:

```console
python -B -m scripts.build_qwen3_composite --output data/processed/qwen3-composite-v1/reproduction --verify-manifest-sha256 <retained-manifest-sha256>
python -B -m scripts.check_qwen3_composite_metrics --product-dir data/processed/qwen3-composite-v1/reproduction --output data/processed/qwen3-composite-v1/reproduction-oracle.json
```

Python consumers use `scripts.build_qwen3_composite.read_product(Path(directory),
trusted_manifest_sha256)` and receive `(payload, analysis)`. The reader verifies
every sealed file, reconstructs source selection, checks image-receipt identity
and recomputes JSON/CSV metrics. Do not infer trust from a checksum inside the
same untrusted directory or discover an ambient `latest` file. Existing V4-only
exporters and historical Seminar v1 consumers retain their own contracts; this
versioned handoff is the explicit composite analysis input.

The second command uses a separate count/Fraction implementation and explicit
positive-negative pairs to check the arithmetic. It does not import the metric
implementation and is not an external scientific audit.

## Selection and provenance

The reader authenticates original S2 ZIP CRC/sidecars/TAR identity, all five
archive inventories and allowlisted metadata/report members, internal/external
results, exact original authorities/units, source/release/grant, ordered inputs,
journals, status flags and original master GT/domain/image hashes. Recovery's
PR123/124 mapping must equal original S2 ordinals717–940, including the original
TECHNICAL_ERROR at717 and223 NOT_ATTEMPTED, with both historical mapping and
opaque-worker projection SHA256 checked using the original canonicalization.
It reads saved `sample_journal` metadata, not raw journal/logit payloads.

Membership is determined before examining predictions, scores or GT correctness:
keep each original SUCCESS; use Recovery only for the exact remaining ID set.
Any extra, duplicate or missing record blocks the label table. A GT mismatch is
an error; it never causes selection of a more favorable output. Failed original
records and every prior artifact remain intact. No labels are parsed again,
rescued, reannotated or inferred from model outputs.

Every selected record carries its original `source_id`, `source_ordinal`,
`run_id`, `attempt_id`, model/revision, implementation/authority/merge commit,
source payload/config/archive/manifest/samples/result/inference SHA256.
`config_sha256` hashes the canonical `{unit, scope}` identity; it does not pretend
to be an historical execution-config field. Original scopes remain unchanged,
including historical `baseline_pooling_allowed=false`. The new Owner decision
authorizes only this separate derived analysis product.

## Metric definitions and verified result

`Level01`–`Level03` are Hazard/Anomaly; `Level04` is Normal. Rows of confusion
are GT; columns are the four canonical predictions plus INVALID. INVALID stays
in support and recall denominators. The accepted composite requires canonical
SUCCESS predictions, so its INVALID column is zero. Every planned denominator
is3763 for ALL; strata report their actual support, including zero support.

Accuracy is diagonal count/planned. Class precision is TP/predicted, recall is
TP/support, F1 is `2TP/(support+predicted)`. Macro-F1 and Balanced Accuracy
(macro recall) average over classes with positive GT support, reporting included
classes; a supported class with no correct predictions has F1=0. Undefined ratios
are null. Binary counts use TP=A→A, FN=A→N, FP=N→A, TN=N→N; INVALID U_A/U_N
are explicit. Hazard Recall=TP/hazard support, False-Safe=FN/hazard support,
False-Alarm=FP/normal support. Binary F1 penalizes U_A as missed hazard; binary
accuracy, precision, specificity, balanced accuracy and severe Level01 misses
are also reported. No threshold fitting, CI, calibration or statistical
superiority claim is added.

Recomputed from the exact private records, **not encoded in metric functions**:

| Endpoint | Result |
| --- | --- |
| Four-level Accuracy | 2932/3763 = 77.91655594% |
| Macro-F1 | 0.45315720192557896 |
| Balanced Accuracy (four-level) | 0.6448991518858818 |
| Hazard Recall | 711/749 = 94.92656876% |
| False-Safe | 38/749 = 5.07343124% |
| False-Alarm | 443/3014 = 14.69807565% |
| Binary Accuracy | 3282/3763 = 87.21764550% |
| Level01 false-safe | 14/490 |

| GT / predicted | Level01 | Level02 | Level03 | Level04 | INVALID |
| --- | ---: | ---: | ---: | ---: | ---: |
| Level01 | 163 | 303 | 10 | 14 | 0 |
| Level02 | 2 | 193 | 32 | 24 | 0 |
| Level03 | 0 | 3 | 5 | 0 | 0 |
| Level04 | 104 | 154 | 185 | 2571 | 0 |

See the [acceptance receipt](evidence/qwen3_composite_20261115/acceptance.json)
for final artifact seals, validation and reproduction evidence. Original V4's
ledger remains3539 SUCCESS/1 TECHNICAL_ERROR/223 NOT_ATTEMPTED. Composite counts
must never be substituted into that historical ledger.

## Separate HNLO compatibility gate

Saved-score AUROC is recomputed with exact ties receiving half credit; empty or
one-class support returns null, and missing/nonfinite scores have explicit
exclusions without blocking valid label analyses. Original V4 SUCCESS pooled
across its four shards reproduces **0.9527927338600111** (700 hazard/2839 Normal).
Recovery alone reproduces **0.9545189504373177** (49/175). Per-source results and
eligible denominators remain separate. No mean of source AUROCs is presented as
full-TRAIN AUROC.

Composite HNLO AUROC is **N/A**: matching model revision/runtime and inherited
method assertions do not independently verify cross-series token/decision
alignment and score comparability. This task reads no native/raw logit payloads
and does not claim a new raw audit. It therefore does not promote historical
pooled0.952935. A separate compatibility dossier/review would be needed before
exposing a pooled HNLO endpoint; this restriction does not block the label table.

## Limits retained

TRAIN has already been exposed. This is not a holdout, a new uniform fresh run,
TEST/generalization evidence, calibration, scientific superiority or faculty
approval. All3763 IDs are retained, including44 exact-content duplicate pairs:
3719 distinct image SHA256 values. Source identity remains unverified; folder
domain is the historical domain convention, not revalidated source identity.
Level03 has only8 examples. Cross-model analyses must explicitly join the exact
approved cohort and preserve each model's statuses/configuration/lineage; this
product does not qualify peers, change roster or license TEST/raw access.
