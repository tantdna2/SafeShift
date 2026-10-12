# Task 5 â€” Kaggle feasibility, not Seminar confirmation

Date: 2026-10-12, Asia/Bangkok. BASE: `747171e011e35bc8995338402a80ba7ea70d8ff7`.
This document supersedes Task 4's operational instructions for this narrow task.
No GPU, model download/load, actual tokenizer, or real InspecSafe input was used
in Codex. All reported CPU tests use synthetic fixtures/API doubles.

## Current readiness and exact scope

**Run All is BLOCKED today.** This PR supplies code and notebooks, not the actual
Kaggle inputs. Review, Antigravity audit, reconciliation and merge are pending.
The Draft does not authorize execution. Keep this PR Draft; do not merge here.

| Input / gate | Present in PR | Still required from owner |
| --- | --- | --- |
| Committed source and source-bundle builder | Yes | Audited merge SHA; build/hash/upload actual bundle |
| Qwen pinned snapshot manifest | Existing unchanged pins | Actual verified `pa3_model.tar.gz` and receipt |
| Linux relocatable runtime builder | New, CPU fixtures tested | Actual Prep run, relocation/import check and inventory |
| T4/FP16/SDPA/T1/raw-logit qualification | Prepared | Actual four-image technical run and CPU audit |
| Pilot candidate selector / runner | Prepared, separate gate | Custodian provenance, Lead-approved exact manifest, technical PASS, new reviewed authority release |
| TRAIN-holdout / TEST / calibration / RQ4 | No rights | Outside this task |

Exact model: `Qwen/Qwen2.5-VL-3B-Instruct`, revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`. One visible NVIDIA T4,
FP16, SDPA, no quantization, C1, greedy, batch 1, 32 generated tokens,
unchanged PA3 validity/decision-step/raw-logit score rules. No calibration,
threshold learning, LS1 reference calls or semantic accuracy claim on drawings.

| Package | Locked version |
| --- | --- |
| Python | 3.11.11 |
| torch | 2.6.0+cu124 |
| torchvision | 0.21.0+cu124 |
| transformers | 4.51.3 |
| qwen-vl-utils | 0.0.8 |
| accelerate | 1.6.0 |
| pillow | 11.2.1 |
| huggingface-hub | 0.30.2 |
| tokenizers | 0.21.1 |
| safetensors | 0.5.3 |

Linux x86_64 is mandatory. Ten existing version pins are unchanged; a complete
prospective transitive lock did not exist. Prep records `pip freeze --all` and
hashes the actual runtime archive. Preserve and reuse those exact bytes; a new
build is a different artifact requiring inventory review. Do not silently update
these pins if an index, download, import or dependency check fails.

Pinned model files total **7,520,918,095 bytes** (~7.00 GiB). Model Prep needs
cache + archive + 1 GiB, checked before download (~15.01 GiB free). This is a
storage bound, not a GPU fit measurement. Runtime size depends on resolved
transitive wheels and must be measured in Prep. Offline inference additionally
needs extracted model + extracted runtime + journals; check Kaggle free storage
against actual archive/expanded sizes before starting. T4 load/activation/KV
memory feasibility remains UNKNOWN until the real run; OOM is a valid outcome.

## 1. Review and source release (owner, only after audit/merge)

The PR has implementation commit F1 and direct child F2 changing only
`configs/pa3/feasibility_authority.v1.json`. Use **standard Merge Commit** with
first parent BASE and second parent F2, and exactly F2's tree. Squash/rebase or
main advancing changes the required topology: stop and re-review/re-pin. The
gate checks exact source, parents, tree, committed authority bytes and dirty
source. It does not claim Git topology cryptographically attests human review.
ChatGPT/Lead must verify the actual merge on `tantdna2/SafeShift` main.

On a clean Linux checkout of the approved merge M:

```text
git -c core.autocrlf=false clone https://github.com/tantdna2/SafeShift.git source
cd source
git checkout --detach M
python -m safeshift.pa3.native.kaggle --bundle-source --output data/processed/pa3_release
```

Replace `M` with the verified full SHA. Build fails on altered executable bytes.
Upload only `pa3_source.bundle` and `pa3_source_release.json` as a **private
Kaggle Dataset** named, for example, `pa3-reviewed-source`. Keep the bundle hash
independently from `bundle_sha256` in the release receipt. Do not upload the
working repo/data/cache. The bundle contains committed history, not raw data.

## 2. Runtime Prep â€” one fresh CPU notebook, Internet ON

Create a Kaggle notebook by importing
`notebooks/pa3_inputs_prep_kaggle.ipynb`. Set accelerator **None**, Internet **ON**.
Add Input â†’ your private `pa3-reviewed-source` Dataset. In the only SETTINGS
cell fill:

```python
KIND = "runtime"
SOURCE_COMMIT = "<verified M>"
SOURCE_BUNDLE_INPUT = "pa3-reviewed-source/pa3_source.bundle"
SOURCE_BUNDLE_SHA256 = "<independently verified bundle_sha256>"
```

Use the exact path shown by Kaggle's Input browser, relative to its input root;
the example slug is not auto-discovered. **Run All once.** This explicitly
installs uv 0.6.14, downloads managed Python 3.11.11, installs exact package pins,
runs `pip check`, moves the interpreter tree, checks exact versions and imports
the Qwen class without loading weights or invoking CUDA. It then creates a
portable archive, restores it to a new location, repeats version/import checks
and hashes it. Contained Python aliases remain relative symlinks. Failed Prep is not runtime PASS.

Output directory printed by notebook:
`data/processed/pa3-prep-runtime/data/processed/pa3-runtime-prep/`.
Download `pa3_runtime.tar.gz`, `pa3_runtime_inventory.json`, `runtime_prep.json`,
`resolved-requirements.txt`, `constraints.txt`, `commands.json`, plus notebook
logs. Upload those six files to private Dataset `pa3-runtime-input`.
Do not upload the temporary `build`, `relocated` or `archive-roundtrip` directories. Preserve the
inventory SHA from `runtime_prep.json` independently.

Runtime Prep is deliberately separate from inference. Its implementation uses
[uv managed standalone Python](https://docs.astral.sh/uv/guides/install-python/)
and the [official PyTorch 2.6.0 CUDA 12.4 wheel index](https://pytorch.org/get-started/previous-versions/).
These sources document the preparation mechanism, not evidence our build ran.

## 3. Model Prep â€” another fresh CPU notebook, Internet ON

Import the same Prep notebook into a **new** Kaggle notebook. Accelerator None,
Internet ON; attach the reviewed source Dataset. Fill the same three source
fields and set `KIND = "model"`. **Run All once.** It installs only the pinned
Hub downloader in the Prep host, requests the exact revision and allowlisted
files, validates existing authoritative size/hash pins, and writes regular
bytes to an archive whose top directory is the exact revision. No tokenizer
or model is loaded. There is no inferred hash or mutable `main` revision.

From `data/processed/pa3-prep-model/data/processed/pa3-model-prep/`, download
`pa3_model.tar.gz`, `model_prep.json`, and notebook logs. Upload archive and
receipt to private Dataset `pa3-model-input`. Do not upload `cache`.
Keep every per-file SHA-256 and archive hash. Download failure, disk shortage
or checksum mismatch is a blocker; do not switch model/revision/precision.

Existing Task 4 Prep may be reused only if it passes the same pins and can be
supplied as one explicit model archive and one explicit portable runtime archive
with trusted inventory. This launcher rejects directory discovery/scans.

## 4. Technical inference â€” existing Task 4 notebook, Internet OFF

Import `notebooks/pa3_qwen2_5_kaggle.ipynb` into a **fresh** notebook. Set GPU T4;
if Kaggle offers a pair, the child exposes device 0 only and checks exactly one
visible T4. Set Internet **OFF**. Add Input â†’ the three private Datasets above.
Do not attach InspecSafe or a pilot manifest to the technical notebook.

In the SETTINGS cell fill only these fields:

```python
"mode": "technical",
"run_id": "pa3-qwen-technical-first",
"source_commit": "<verified M>",
"source_bundle_input": "pa3-reviewed-source/pa3_source.bundle",
"source_bundle_sha256": "<bundle hash>",
"model_input": "pa3-model-input/pa3_model.tar.gz",
"runtime_input": "pa3-runtime-input/pa3_runtime.tar.gz",
"runtime_inventory_input": "pa3-runtime-input/pa3_runtime_inventory.json",
"runtime_inventory_sha256": "<independently verified inventory hash>",
```

Leave all other fields empty, including runtime_site_packages/dataset/cohort/
pilot fields. An extracted runtime carries its own site-packages. Record the
attempt in the Lead's persistent run ledger **before Run All** (one technical
run; four images; no retry). Click **Run All once**. No pip, model download,
precision/revision fallback or automatic retry occurs in this notebook.

The source gate is checked before touching model/runtime/data. T1 runs 28
variants. Exactly the four generated drawings are processed; native generate
checks IDs, order, pixel hashes and durable per-index tickets. Real images,
including TEST, cannot be substituted under technical authority. Original
Task 4 completion permits some INVALID; **Task 5 pilot eligibility is stricter**:
T1 PASS + completed four-image run + all four SUCCESS + independent CPU audit.
Read `feasibility.json`'s `four_sample_score_audit`, not just notebook exit status.

## 5. Download after EVERY inference attempt, including failure

The notebook prints bootstrap and run artifact paths. Under
`data/processed/pa3_source/RUN/data/processed/pa3_qwen/`, download all matching
`RUN*` directories, `.tar.gz` archives and `.sha256.json` receipts, including
`RUN-launch`, `RUN`, `RUN-qualification`, and `RUN-tickets` if present. Also
download `data/processed/pa3_bootstrap/RUN*` and Kaggle execution logs. Keep the
exact source bundle and the model/runtime receipts beside these artifacts.
Hard kill/disk failure can leave an unsealed directory: keep it, never repair or
delete it to retry. Request a separately reviewed budget for another attempt.

`RUN/feasibility.json` gives processed count, T1, GPU/model evidence,
SUCCESS/INVALID/TECHNICAL_ERROR counts, generated labels, and scored rows.
For each SUCCESS, `details.raw_label_logits` contains ordered Level01â€“Level04;
`details.decision.step` locates the native generation step. `score` is
`logsumexp(z1,z2,z3)-z4`. Raw/processed step summaries, token IDs, text, prompt,
model/revision, timestamps, generation settings and hashes are retained before
parsing; these are raw audit summaries, not the full vocabulary tensors.
INVALID has no fabricated score. Synthetic AUROC is not reported.

On a CPU machine with the pinned tokenizer dependencies and exact source:

```text
python -m safeshift.pa3.native.native_audit --run data/processed/pa3_qwen/RUN-qualification --snapshot TOKENIZER_REVISION_DIRECTORY
```

Only the pinned tokenizer files are needed for CPU audit, not GPU or weights.
Preserve the audit JSON/log and its checksum. Failures preserve stage/type,
per-sample attempt/error/raw records when available, and sealed packages. A
failure before loading the model provides no model-load PASS claim.

## 6. Conditional pilot â€” do not Run All yet

Current authority has `pilot: null`. No local receipt, SETTINGS field, manifest
hash or environment flag can fill it. After actual technical PASS, a custodian
must supply TRAIN-only original-label/provenance/exposure/link metadata using
the existing internal schema in `native/cohort.py`. This is not an automatic
InspecSafe parser. Check the prior ten observed LS1 IDs and all known linked
groups against the historical exposure ledger; unknown exposure or TEST
relationships are quarantined. Do not read/scan TEST to obtain these records.
Record unavailable scene/sequence information as a limitation, not independence.

The pure `pilot.propose(inventory, links)` function uses fixed seed
`pa3-task5-pilot-2026-10-12-v1`; ranks by SHA-256(seed + `|` + sample ID), with
sample ID breaking ties; takes 4 Normal and 4 Anomaly per each of the five fixed
domains, one image per transitive dependency group. Exact image duplicates,
Normal point IDs and reviewed sequence/scene/source-family/near-duplicate links
form groups. Observed/unknown/unresolved groups are excluded. There is no model
score input. Any shortage reports missing counts and emits no selected IDs:
stop, do not redistribute, lower N, relax rules, choose another seed or replace
samples. This proposes 40 total, 20/20; it creates no official split.

The Lead reviews the resulting exact JSON manifest and checksum, original GT
sources, sample and related group IDs, exclusion evidence and metadata coverage.
All selected and related IDs/groups must enter the persistent observed ledger
and remain excluded from any later independent evaluation. The runner writes
a sealed `RUN-exposure` closure before its first image read, conservatively
reserving every planned image even if inference subsequently fails.

Only then prepare a **separate audited authority release** binding the literal
approved manifest hash, technical seal hash, technical source commit/bundle hash,
Lead approval reference, model/revision/C1/PA3/T4/FP16/SDPA, one
`pa3-qwen-pilot-train-first` run and 40-image budget. This is a later Lead action,
not a second PR opened by Task 5. The existing gate supports the same reviewed
BASEâ†’F1â†’F2â†’merge structure for that later release; the technical journal is
recomputed against its own retained source bundle before loading the pilot model.

Use the same offline inference notebook with the later approved source and:
`mode=pilot-train`, `run_id=pa3-qwen-pilot-train-first`, `pilot_manifest_input`,
`pilot_manifest_sha256`, `dataset_input`, `technical_run_input` (unpacked sealed
qualification directory), `technical_seal_sha256`, `technical_source_commit`,
`technical_source_bundle_input`, `technical_source_bundle_sha256`. Hashes must
match the committed grant. Attach only the approved TRAIN images, retaining
manifest-relative locators; every read checks membership and byte checksum
before decoding. No synthetic rerun, holdout/TEST access or calibration occurs.

Download `RUN*`, including exposure/report packages. `RUN-report/evaluation.json`
contains score-conditional exploratory AUROC, valid Normal/Anomaly counts,
coverage and status denominators. Its separate limitations record flags the
small selected/dependent sample. Audit with `--run .../RUN --report .../RUN-report`
and the same tokenizer snapshot. Never present these pilot numbers as confirmed
Seminar results or tune thresholds on them.

Local journals/tickets prevent repeated use while retained. An offline notebook
cannot prevent an operator deleting files or replaying a fresh session: the
Lead's external attempt ledger and artifact retention enforce the global budget.
Do not claim cryptographic replay protection or external authenticity from hashes.
