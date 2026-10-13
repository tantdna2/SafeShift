# Qwen2.5 PA3 — 3,763 TRAIN images, preparation only

2026-10-13 (Asia/Bangkok). Baseline deadline: 15/10/2026. Draft source is
**LOCKED**, with no real inference or Seminar performance numbers. BASE:
`3a52b549d623bdb4b8b6753abe3adf116bbc6100`. PR #99 is an independent docs-only
Draft at `6effffea024b664b68366e05c8df1d7ad50de8af`; its files/history are not
imported. The decision entry is near the top and the task entry is at the end,
away from PR #99's respective insertion points. Do not merge either PR in this task.

## Kaggle: five steps after authorization

1. Download `notebooks/pa3_qwen_full_train_kaggle.ipynb` from audited merge M.
   Import it into Kaggle; select **GPU T4**, **Internet OFF**. The launcher exposes
   only GPU 0, preserving the existing single-T4 contract.
2. **Add Input**: approved InspecSafe TRAIN source, pinned Qwen Model Prep archive,
   pinned Runtime Prep archive + inventory, M's `pa3_source.bundle`, and the
   unpacked four-image technical qualification + its original source bundle.
   Use the existing preparation procedures in `pa3_task6_runtime_prep.md`.
   Do not redistribute the raw dataset or rebuild/change the runtime pins.
3. Fill SETTINGS with release SHA/hashes and exact Input-relative paths (omit the
   Kaggle Input prefix). `dataset_input` must be the TRAIN root containing
   `DATA_PATH/train/Annotations`. Set SHARD_ID to 0, 1, 2 or 3 and its corresponding
   inference hash. No input discovery, alternate model, installation or fallback.
4. Record that exact shard/run ID in the Lead's persistent external attempt
   ledger. Click **Save Version → Save & Run All** once. Repeat for the other
   three *different* shards only if their budgets remain unused. Never execute
   the GPU cell in the interactive editor or rerun a failed shard/version.
5. At **Versions → the saved version → Output**, download
   `PA3_TRAIN_SHARD_<id>_OUTPUT.tar.gz` and its `.sha256.json`. It contains raw
   journals, tickets, launch/preflight/exposure/telemetry/report evidence and
   `RUN-exports/{samples.csv,metrics.csv,metrics.json,confusion.csv,audit.json,checksums.json}`.
   Notebook completion means artifacts were saved; check `metrics.completed`,
   coverage and failure records before calling the shard complete.

[Kaggle's notebook documentation](https://www.kaggle.com/docs/notebooks) specifies
that Save & Run All starts a clean session and saves a Version; its Output lives
in the working directory. Raw journals stay there throughout inference. Expanded
weights/runtime go to system temporary storage; they are not saved as Output.
Caught execution errors finish the notebook after packaging failure evidence.
A host kill/disk failure can prevent final sealing/export: retain any saved partial
files and record the blocker, never rerun or claim missing results. Actual Kaggle
throughput and session-limit feasibility remain unmeasured in this preparation.

## Required release, still missing

DEC-PA3-007 approves preparation only. Before GPU: GitHub review, independent
audit, Lead approval of the exact full/shard manifests and TRAIN scope, actual
technical CPU recomputation PASS, verified runtime inventory and four budget
reservations. The effective TRAIN grant is **null** today. SETTINGS, CPU tests,
the 90-image authority or its reported results cannot grant TRAIN execution.

The existing authority pattern is retained: exact base B → one reviewed
implementation commit F1 → **authority-only** F2 → standard two-parent merge M.
F2 changes only `configs/pa3/full_train_authority.v1.json`, binding `base=B`,
`implementation=F1`, unchanged scope and this grant schema:

```json
{
  "approval": "<actual Lead approval and independent audit references>",
  "decision": "DEC-PA3-007",
  "full_manifest_sha256": "<approved full manifest SHA-256>",
  "runtime_inventory_sha256": "<actual verified inventory SHA-256>",
  "technical_seal_sha256": "<CPU-audited four-image qualification seal SHA-256>",
  "technical_source_bundle_sha256": "<retained original technical bundle SHA-256>",
  "shards": [
    {"shard_id": 0, "run_id": "pa3-qwen-full-train-shard-0", "max_images": 941, "inference_manifest_sha256": "<shard0 SHA-256>"},
    {"shard_id": 1, "run_id": "pa3-qwen-full-train-shard-1", "max_images": 941, "inference_manifest_sha256": "<shard1 SHA-256>"},
    {"shard_id": 2, "run_id": "pa3-qwen-full-train-shard-2", "max_images": 941, "inference_manifest_sha256": "<shard2 SHA-256>"},
    {"shard_id": 3, "run_id": "pa3-qwen-full-train-shard-3", "max_images": 940, "inference_manifest_sha256": "<shard3 SHA-256>"}
  ]
}
```

Those placeholders are documentation, never a valid grant. No F2 is created by
Codex. Lead approval must be independently recorded before F2; review of F2 and
M's main provenance is required. Git topology/hashes prove integrity, not human
approval. If main advances (including PR #99), rebase/review F1 onto the new B
before authority release; retain its exact one-parent topology. Subsequent main
commits do not inherit M's execution source: use M exactly.

At clean M, build the source Input on CPU:

```console
python -m safeshift.pa3.native.kaggle --bundle-source --output data/processed/pa3_full_train_source_input
```

Use M as SETTINGS.source_commit and the generated bundle SHA-256 as
SETTINGS.source_bundle_sha256. Use the original technical source
`13ea2fba67f36883518db8a2add1b249c951e48e`; audit all four SUCCESS traces against
that retained source, never against the TRAIN source or the 90-image result.

## CPU merge/recheck after four downloads

Verify archive SHA-256, unpack each raw journal into the corresponding path
below, and use clean M plus its pinned tokenizer directory and existing CPU
dependencies. No model weights/GPU are needed for recomputation:

```console
python -m safeshift.pa3.native.train_report --snapshot data/processed/tokenizer/66285546d2b821cf421d4f5eb2576359d3770cd3 --runs data/processed/pa3_train_downloads/pa3-qwen-full-train-shard-0 data/processed/pa3_train_downloads/pa3-qwen-full-train-shard-1 data/processed/pa3_train_downloads/pa3-qwen-full-train-shard-2 data/processed/pa3_train_downloads/pa3-qwen-full-train-shard-3 --output data/processed/pa3_full_train_report
```

This reuses native CPU audit/raw-score recomputation, checks committed source,
exact IDs, hashes and seals, rejects duplicate/missing shards or corrupt evidence,
and pools all 3,763 status rows before computing AUROC. It also compares saved
shard reports/exports when supplied. It never averages shard AUROCs. A sealed
failed shard is supported, with an explicit missing-score tail and partial-run
status; a missing/unsealed package is a blocker rather than invented rows.

`metrics.csv/json` contain overall/domain PA3 AUROC, generated-binary AUROC,
paired delta on identical SUCCESS IDs, coverage/status denominators, generated
four-class and binary Accuracy/Balanced Accuracy, exact Level01 Recall and
generated-Anomaly FPR among original Normal. Four-class Balanced Accuracy requires
all four original classes; absent classes yield null, with support in JSON.
`confusion.csv` distinguishes generated four-class failure-aware and generated
binary score-valid matrices. Invalid/failed/missing images stay explicit; PA3 has
no threshold or classification metrics. `samples.csv` carries endpoint inputs,
generated labels, scores and decision-step z1–z4; raw journals retain every captured
step, token IDs, raw/processed summaries and generation/model/runtime provenance.

## Manifest and validation evidence

CPU builder reused W1 inventory/metadata verification and grouping code; it opened
only TRAIN image/JSON/TXT bytes, without decode or any TEST file. It verified 3,763
unique original IDs/locators, all image SHA-256s, JSON dimensions, TXT domain history,
folder label/domain/platform/point consistency and the complete TRAIN image tree.
Original distributions: Level01=490, Level02=251, Level03=8, Level04=3,014;
coal_conveyor=822, metallurgy=543, oil_chemical=778, power=656, tunnel=964.
JSON/TXT checksums and historical TEST links are metadata only, never model input.
Names/IDs encode original labels, but the scorer receives only decoded RGB pixels
and unchanged C1; no ID, locator, annotation, domain or GT enters its processor.

Reproduction from the repository root:

```console
python -m safeshift.pa3.native.train_manifest
python -m unittest tests.test_pa3_full_train -q
```

The actual worktree invocation used `--duplicate-audit ../../data/manifests/duplicate_leakage_audit.json
--validation ../../data/manifests/dataset_validation.json --dataset-root ../../data/raw/InspecSafe-V1/train`.
Generated files reside under `data/processed/pa3_full_train_manifests`; only compact,
reviewable manifests/receipt were copied to `data/manifests`. No raw data is committed.
Receipt records builder code hashes at BASE with uncommitted preparation code;
this is not a claim that the new builder already existed at BASE.

Full manifest SHA-256: `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`.
Shard hashes are in `pa3_full_train_receipt.v1.json`; deterministic round-robin over
SHA-256(seed + ID) retains every TRAIN ID, including historical exact cross-split
duplicates. These are execution partitions, not new dataset splits or holdouts.
Prior P2 exposure, PA3 diagnostic exposure, dependencies and domain confounding
remain disclosed. Results of the 90-image diagnostic are not Seminar metrics here.

CPU validation results are recorded below after the final checks. Real tokenizer,
Kaggle Inputs/layout, real model/runtime/GPU, full discovery and TEST execution are
not run in this task; no Kaggle success, throughput or baseline AUROC is claimed.

- New synthetic CPU suite: **18/18 PASS**, including actual native API doubles,
  raw recomputation, GT-after-seal, stop/no retry/remaining statuses, exact pixels,
  one-use tickets, Git authority topology, temp restore, bootstrap failure Output,
  full-universe partition validation and pooled AUROC versus shard-AUROC averaging.
- Existing PA3 command: `python -m unittest tests.test_pa3_synthetic tests.test_pa3_native
  tests.test_pa3_boundaries tests.test_pa3_feasibility tests.test_pa3_runtime_prep
  tests.test_pa3_seminar_direction -q`: **161 run, 156 PASS, 4 SKIP, 1 inherited FAIL**.
  The failure asserts that the previously merged 90-image grant is still null;
  the actual grant is non-null. That test/authority is preserved. SKIPs cover
  symlink/host-volume constraints and opt-in real Linux runtime checks.
- Windows Python 3.11.9, host version 10.0.26200; only synthetic CPU model doubles.
  `compileall`, notebook compilation, `git diff --check`, manifest/receipt/code
  hashes and protected scorer/audit/runtime/authority byte comparisons PASS.
- BASE comparison: the same 161-test command on the existing main checkout ran
  with 33 failure events and 4 SKIPs: 32 protected-byte subtest failures caused
  by its CRLF working files, plus the same historical grant-null assertion.
  No user's existing files were normalized or changed. On a fresh clean checkout
  of the exact BASE, the two affected test methods ran: byte protection PASS,
  the same grant-null assertion FAIL. Full discovery and a second full 161-test
  run on that fresh checkout were not performed; regression is not claimed green.
- `git merge-tree --write-tree HEAD 6effffea024b664b68366e05c8df1d7ad50de8af`
  produced a conflict-free tree for this implementation and PR #99. This checks
  coexistence only; neither branch was merged.
