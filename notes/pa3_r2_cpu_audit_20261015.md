# PA3-R2 Qwen2.5: CPU audit handoff, 2026-10-15

**Update after PR #104:** the subsequent [CPU Linux completion audit](pa3_r2_cpu_completion_20261015.md)
is **PASS**, with 3,763/3,763 independently recomputed SUCCESS rows and pooled
AUROC **0.8266558463706973**. The original BLOCKED handoff below is retained as
history. It does not describe the current audit status. Windows' later exact-float
failure, its Linux resolution, evidence hashes and baseline limitations are in
the completion note. Seminar direction and the four-model requirement are unchanged.

**Official CPU score audit: BLOCKED. Independent pooled AUROC: NOT COMPUTED.**
The existing `train_report` was invoked with all four R2 journals and exited 1
at `CPU_TOKENIZER_T1_REQUIRED`. The independent tokenizer preflight returned
`BLOCKED / PINNED_SNAPSHOT_NOT_SUPPLIED`. No saved report substitutes for a
fresh token-alignment, raw-score and pooled-AUROC audit.

Research Lead reports 3,763/3,763 successful TRAIN images and preliminary AUROC
0.8267. Those figures are not an independently audited result. Qwen2.5 is only
the baseline; [all four Seminar models remain required](pa3_four_model_seminar_scope.md).
PA3 has not been approved to replace the current Seminar direction.

## Inputs and provenance

Base and recorded execution source:
`c1527713ca7175b3d71248d51f1715693795e6e8` (main, PR #103 merge).
Branch: `audit/pa3-r2-cpu-four-model-scope`.
No inference, GPU, model weights, original image/annotation access, TEST read,
data/label/metric/authority change, or modification of original archives.

The requested `data/local/pa3_r2_audit_inputs/` was absent in the active checkout
and the R2 release checkout. All four selected packages were found in the
user-provided Downloads directory `Output-PA3-Qwen2.5`. The separate 644-byte
Shard 0 Output at the Downloads top level was excluded. Only the final Shard 0
package below was used for this audit; no older failed run was pooled.

| Shard | Archive (`PA3_R2_TRAIN_SHARD_<n>_OUTPUT.tar.gz`) bytes | SHA-256 | External receipt |
| --- | ---: | --- | --- |
| 0 | 15080070 | `5d9d017f058efd0c74cfcf9e098a4c3ae73507225ec7b4ce1840a2b4e108ae17` | MATCH |
| 1 | 15117669 | `ace50d1d0fcb83d680e8d922cef0a44ab88c29cb206c192db6861da87850c5b8` | MISSING |
| 2 | 15074574 | `dc5c3f5a98903c20075c7ed073acee06f1941563cf3181f149ae1cc7f9963c5b` | MATCH |
| 3 | 15074981 | `59d5ffea62df6979e9d40b17e66c55e07828ad2746e9249ccafdd56528d53635` | MATCH |

All four SHA-256 values were unchanged after extraction. Archive traversal,
duplicate paths, links and special-file entries were rejected before extraction;
files were created exclusively in a new ignored derived directory. Shard 1's
download receipt should be supplied for transport provenance; computing a local
hash does not reconstruct an independently supplied receipt or authenticity.
The existing merger validates internal journals and does not require that outer
receipt; its absence is separate from the blocking tokenizer prerequisite.

R2 manifest SHA-256:
`e842c9e08f7fa28f72fa8536bc35fd7b5e2ad751481cb812c73e9f201f95afcf`.
The original full metadata manifest and all four original inference manifests
are pinned through `data/manifests/pa3_r2_full_train.v1.json`; their validation
uses `r2.manifest`, `r2.inference_payload` and `r2.load_full`. Execution ordering
seed remains `pa3-full-train-2026-10-13-v1`; this audit introduces no randomness.

Local evidence root, relative to this worktree:
`data/processed/pa3_r2_cpu_audit_20261015/`. It contains `input_inventory.json`,
`source_verified.json`, `tokenizer_search.json`, `tokenizer_candidates_checked.json`,
`tokenizer_gate.json`, `train_report_attempt.log`, `targeted_tests.log`, the
one-off `check_integrity.py`, and `unpacked/shard-0` through `unpacked/shard-3`.
Detailed logs, source receipts, raw outputs and extracted packages stay local.
The one-off integrity collector was run from the clean execution-source worktree
before committing these notes (the source proof was saved before tracked edits):

```powershell
$env:PYTHONPATH = (Get-Location).Path
python data/processed/pa3_r2_cpu_audit_20261015/check_integrity.py
```

It reads all four journals through the existing APIs and writes only new local
summary files. To repeat the collection, use a new evidence directory; its
exclusive-create writes deliberately refuse to replace previous summaries.
`package_consistency.json` additionally records successful checksum verification
of all four bootstrap directories and all 24 nested package receipts, with every
nested archive member byte-matched to its extracted counterpart. This checks
packaging consistency without using saved scores as audit inputs.

## Integrity checks and limits

The existing `preflight.source` verified all 194 protected source/config/prompt
files against the exact execution commit before documentation edits. Journal
checks reuse `Journal.verify/read`, raw trace schema checks reuse `validate_trace`,
and export checks reuse `verify_run`. This is an integrity prerequisite, not
tokenizer validation or a replacement scorer.

All four integrity collections completed successfully. Each journal is sealed,
has a matching FINISHED record and no failure record, and matches the exact R2
mode/run ID/source/full manifest/projected shard membership. The four ID sets
are disjoint and their union is exactly the committed 3,763-image TRAIN universe.
Every listed sample has its matching attempt, raw trace and result record.

| Shard | Planned IDs | Attempt/raw/result triples | Stored SUCCESS (not recomputed) | Recorded clamp activations | Journal seal / raw trace schema |
| --- | ---: | ---: | ---: | ---: | --- |
| 0 | 941 | 941 | 941 | 9 | VERIFIED / VERIFIED |
| 1 | 941 | 941 | 941 | 5 | VERIFIED / VERIFIED |
| 2 | 941 | 941 | 941 | 6 | VERIFIED / VERIFIED |
| 3 | 940 | 940 | 940 | 4 | VERIFIED / VERIFIED |
| Total | 3763 | 3763 | 3763 | 24 | Integrity prerequisites only |

All 20 sealed exposure/launch/preflight/report/telemetry sibling journals and
the four export checksum inventories were also verified. Saved result statuses
and clamp counts above are checksummed observations, not independent score or
performance conclusions. In particular, saved evaluation values were not used
to calculate an AUROC.

Raw journal `seal.json` SHA-256, Shards 0 through 3 respectively:

```text
6870abc28d4ad427d6fdd21fc8e29addbfcae7a4ac27f39eed2a040b5aa5407e
c9d1b88328b429f173dc22c4ee4b0920875b02c69c7bbd6d709bb1f40d7f9f9a
99f8ba081d584471767d1d7cf4a135dba4491a04af33588573eec9d36b5f761b
f9a448c760ef82160f60bd379ead684a12dd5b28ea665ce45a9b648012018261
```

Local evidence SHA-256 (no raw data embedded in this note):

| Artifact | SHA-256 |
| --- | --- |
| integrity_summary.json | `b846c33b6d5040e363c3e8b7859467cbc9531057797147fd2e72d2d33f8d6daa` |
| package_consistency.json | `0f36d859f0d5e664287373f810bc289e5c2ef270e53656f7a02373616d55fcae` |
| check_integrity.py | `fd1a661c9b8691c618ea579f4f27497947b7c1d83c7ce2dfe46ef82737258876` |

`integrity_summary.json` explicitly has `status=BLOCKED`,
`scope=INTEGRITY_ONLY_NOT_SCORE_AUDIT` and `independent_auroc=null`.
Local hashes establish internal integrity, not external authenticity or the
completeness of an external attempt ledger.

The unchanged score implementation is `native_score.score` -> `score_decision`
-> `anomaly_log_odds`: PA3 = `logsumexp(z1,z2,z3) - z4`, higher means Anomaly,
Level01–03 are Anomaly and Level04 is Normal. The tokenizer must independently
locate the decision step and four candidate tokens. Processed scores are not
substituted for raw logits. `train_report.merge` re-audits each journal, compares
saved reports/exports when present, validates the disjoint complete universe and
then pools all eligible rows. It never averages shard AUROCs. `auc` uses average
ranks for ties (0.5 credit); missing/invalid scores are not imputed.

These code-path observations do **not** establish that all real scores pass
recomputation. T1, token/text alignment, independent per-image scores, comparisons
against saved metrics, and the 3,763-image pooled AUROC remain unexecuted because
the prerequisite is missing. Even a future CPU PASS is an integrity/recomputation
verdict on previously exposed TRAIN, not generalization or execution authority.

## Exact missing tokenizer and dependencies

Model: `Qwen/Qwen2.5-VL-3B-Instruct`.
Revision directory name must be `66285546d2b821cf421d4f5eb2576359d3770cd3`.
`safeshift/ls1/tokenizer.py` intersects `TOKENIZER_FILES` with the pinned runtime
plan; **these six files** are required (no model weights):

| File | Bytes | Expected Git blob SHA-1 |
| --- | ---: | --- |
| chat_template.json | 1050 | `732bd68bc5427d1fb6c06a59b3bf2456b2155d24` |
| config.json | 1373 | `0ae1866f05ab0153ad293bdc92bb1b842c4d95b1` |
| merges.txt | 1671839 | `20024bfe7c83998e9aeaf98a0cd6a2ce6306c2f0` |
| tokenizer.json | 7031645 | `443909a61d429dff23010e5bddd28ff530edda00` |
| tokenizer_config.json | 5702 | `91684ea3dc135a7d815e2c932054ce88c1aab41f` |
| vocab.json | 2776833 | `4783fe10ac3adce15ac8f358ef5462739852c569` |

Source: `configs/pre_freeze/qwen2_5_t4_runtime.v1.json`; Git blob SHA-1 includes
the `blob <size>\0` header, not a plain file SHA-1. `verify_snapshot` checks size
and pinned hash, and also records SHA-256. Do not substitute latest/main files.

Observed CPU host: Python 3.11.9, Windows 10 build 26200 (platform report).

| Dependency | Required by T1 | Observed in audit interpreter |
| --- | --- | --- |
| transformers | 4.51.3 | MISSING |
| tokenizers | 0.21.1 | MISSING |
| huggingface-hub | 0.30.2 | 2.0.0 |

The repository `.venv` also lacks Transformers. No dependencies were installed.
T1 checks the three versions above; GPU runtime pins in the recorded inference
evidence are a separate check and do not require installing CUDA for this audit.

Search covered accessible files on drive D, Downloads, Documents, OneDrive and
the Hugging Face cache, plus member lists of 34 archives with PA3/Qwen/model/
runtime/SafeShift names. Fifteen tokenizer-name candidates were hash-checked;
none matched the pinned file. The diagnostic archive's `tokenizer.json` is only
11,717 bytes, not the required 7,031,645-byte tokenizer. Other candidates belong
to unrelated models. Protected system/recycle directories were inaccessible;
this is a bounded search, not a claim that every disk location was readable.

## How the owner can supply the missing files

Option A: use the **same Model Prep Input used on Kaggle**. Locate the pinned
revision directory in that Input; copy only the six files above, preserving
their bytes, into `data/processed/pa3_r2_tokenizer/<revision>/`. If it is archived,
inspect its member paths first and extract only those six files into a new
directory. Supply the Model Prep receipt too. Do not rename an unrelated
tokenizer to the pinned revision; the checksum gate must actually pass.

Option B: fetch only those six files at the exact Hugging Face revision. The
[pinned model tree](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/tree/66285546d2b821cf421d4f5eb2576359d3770cd3)
and [Hub v0.30.2 download documentation](https://huggingface.co/docs/huggingface_hub/v0.30.2/guides/download)
support selecting filenames and a full commit revision. The following PowerShell
commands are **instructions, not executed in this task**; run from repo root in
a fresh CPU environment:

```powershell
python -m venv data/processed/pa3_r2_tokenizer_env
$auditPython = 'data/processed/pa3_r2_tokenizer_env/Scripts/python.exe'
& $auditPython -m pip install transformers==4.51.3 tokenizers==0.21.1 huggingface-hub==0.30.2
& $auditPython -m pip check
& $auditPython -m pip freeze > data/processed/pa3_r2_tokenizer_env/packages.txt
$revision = '66285546d2b821cf421d4f5eb2576359d3770cd3'
$snapshot = "data/processed/pa3_r2_tokenizer/$revision"
$env:HF_HUB_OFFLINE = '0'
$env:TRANSFORMERS_OFFLINE = '0'
& data/processed/pa3_r2_tokenizer_env/Scripts/huggingface-cli.exe download Qwen/Qwen2.5-VL-3B-Instruct chat_template.json config.json merges.txt tokenizer.json tokenizer_config.json vocab.json --revision $revision --local-dir $snapshot
```

This selects six filenames, about 11.49 MB in total, and excludes all weights.
Keep the environment and snapshot local/ignored. Do not use the whole-model
provisioning command for this tokenizer-only need.

## Resume the official CPU audit

Keep the sealed journals and all report/export siblings together. The audit must
check the **original execution source**, not a newer docs commit; `preflight.source`
requires HEAD to equal the source in the journals and a clean tracked tree.
Create a detached checkout at that commit, with committed byte-preserving checkout
settings. Run these PowerShell commands from the documentation worktree root:

```powershell
git -c core.autocrlf=false worktree add --detach data/processed/pa3_r2_execution_source c1527713ca7175b3d71248d51f1715693795e6e8
$auditRepo = (Resolve-Path data/processed/pa3_r2_execution_source).Path
$auditRoot = 'data/processed/pa3_r2_cpu_audit_20261015'
$auditPython = 'data/processed/pa3_r2_tokenizer_env/Scripts/python.exe'
$snapshot = 'data/processed/pa3_r2_tokenizer/66285546d2b821cf421d4f5eb2576359d3770cd3'
$env:CUDA_VISIBLE_DEVICES = ''
$env:USE_TORCH = '0'
$env:USE_TF = '0'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
& $auditPython -m safeshift.ls1.tokenizer --model qwen2_5 --snapshot $snapshot --output "$auditRoot/tokenizer_t1_retry.json"
if ($LASTEXITCODE -ne 0) { throw 'Tokenizer T1 did not PASS' }
$auditRuns = 0..3 | ForEach-Object { "$auditRoot/unpacked/shard-$_/pa3-qwen-r2-train-shard-$_" }
& $auditPython -m safeshift.pa3.native.train_report --repo $auditRepo --snapshot $snapshot --runs $auditRuns --output "$auditRoot/official_report"
if ($LASTEXITCODE -ne 0) { throw 'Official CPU audit did not complete' }
```

Use new output names if any already exist; never overwrite raw evidence or an
earlier report. An exit-zero partial report is not by itself a full-run PASS:
check `completed=true`, all four integrity results, exact 3,763-ID coverage,
SUCCESS/INVALID/error counts, finite raw-score recomputation, and pooled eligible
class denominators. Compare the recomputed AUROC with the reported 0.8267 only
then; report any discrepancy. Keep the resulting sealed audit/CSV/JSON local and
add only a reviewed small evidence summary to a later PR.

## Validation and remaining research work

Existing CPU-only synthetic tests, no real model: **25/25 PASS**, 161.333 seconds,
0 skips/failures/errors. Command:

```powershell
python -m unittest tests.test_pa3_native.PreflightTests tests.test_pa3_native.JournalAuditTests tests.test_pa3_native.EvaluationTests tests.test_pa3_full_train.MergeAndMetricTests tests.test_pa3_r2.DurabilityTests tests.test_pa3_r2.R2WorkflowTests tests.test_pa3_r2.R2PreparationTests.test_manifest_exact_original_3763_and_distinct_runs tests.test_pa3_r2.R2PreparationTests.test_merge_refuses_old_shard_before_auditing_it -v
```

Failure-packaging messages in the test log are expected synthetic negative cases;
the unittest exit status is zero. Full repository suite and model/GPU tests were
not run: changes are documentation only and no model execution is authorized.
Local Markdown links, code fences, PowerShell instruction syntax and
`git diff --check` are checked before handoff. Synthetic tests do not substitute
for the blocked real audit.

- [ ] Supply pinned tokenizer and compatible CPU dependencies; obtain real T1 PASS.
- [ ] Complete all four raw audits, per-image recomputation and pooled AUROC.
- [ ] Supply Shard 1's outer receipt and retain external run-attempt provenance.
- [ ] Verify PA3/raw-logit or equivalent support for every required model; report
  obstacles without silently dropping/substituting a model.
- [ ] Review a fair four-model protocol and credible generalization design that
  accounts for prior exposure, dependence and domain/platform confounding.
- [ ] Obtain a new explicit Research Lead decision before any Seminar pivot,
  protocol change or further execution. No such decision is created here.
- [ ] ChatGPT direct GitHub review of the Draft PR. Stop; no merge/Antigravity.
