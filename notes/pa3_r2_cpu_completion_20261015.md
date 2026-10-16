# PA3-R2 Qwen2.5 CPU recomputation and baseline, 2026-10-15

**CPU_AUDIT: PASS on CPU Linux. Independent pooled AUROC:
0.8266558463706973.** The unchanged official reporter exited 0, completed all
four sealed R2 shards, and independently recomputed 3,763/3,763 SUCCESS rows.
INVALID/technical/interrupted/unprocessed/not-attempted counts are all zero.
The pooled AUROC rounds to the Lead's preliminary 0.8267. This is a descriptive
TRAIN recomputation verdict, not generalization or a Seminar pivot decision.

Task BASE is `5c8cb704522897a75a2a42604a1492714ee8610c`, main's PR #104 merge.
The scorer and audit execute from a clean detached checkout of the original
execution source, `c1527713ca7175b3d71248d51f1715693795e6e8`.
No production code, runtime, authority, dataset, labels, metrics, README, RQ or
research direction is changed. No new inference, GPU, weights or TEST access.

## Inputs and tokenizer

Only the four final R2 packages in the
[prior integrity handoff](pa3_r2_cpu_audit_20261015.md#inputs-and-provenance)
are used. The old failed Shard 0 Outputs are excluded. Journals and their report
and export siblings are read in place from that handoff's ignored evidence root;
no original or extracted input is overwritten. Before Linux staging, and again
after completion, all four original archive sizes and SHA-256s matched the
prior handoff. Fresh Linux extraction retained all report/export siblings.

| Shard | Final archive SHA-256 | Outer download receipt |
| --- | --- | --- |
| 0 | `5d9d017f058efd0c74cfcf9e098a4c3ae73507225ec7b4ce1840a2b4e108ae17` | MATCH |
| 1 | `ace50d1d0fcb83d680e8d922cef0a44ab88c29cb206c192db6861da87850c5b8` | MISSING |
| 2 | `dc5c3f5a98903c20075c7ed073acee06f1941563cf3181f149ae1cc7f9963c5b` | MATCH |
| 3 | `59d5ffea62df6979e9d40b17e66c55e07828ad2746e9249ccafdd56528d53635` | MATCH |

Downloaded exactly `chat_template.json`, `config.json`, `merges.txt`,
`tokenizer.json`, `tokenizer_config.json` and `vocab.json` from
`Qwen/Qwen2.5-VL-3B-Instruct` revision
`66285546d2b821cf421d4f5eb2576359d3770cd3`. T1's existing `verify_snapshot`
verified every pinned size and Git blob SHA-1 and recorded SHA-256s. The six
files total 11,488,442 bytes. No weight files were requested or loaded.

Initial ignored Windows environment: `data/processed/pa3_r2_cpu_env/`, Python
3.11.9, Windows 10 build 26200. Final CPU audit environment: Python **3.11.11**,
WSL2 Linux x86_64, glibc 2.43, separate `data/processed/cpu_env/` in a fresh Linux
checkout of the original execution commit. Both environments use Transformers
**4.51.3**, tokenizers **0.21.1**, huggingface-hub **0.30.2**. Windows `pip check`
and Linux `uv pip check` passed. `packages.txt`, `linux_packages.txt` and
`linux_environment.json` record the resolved packages. Neither audit environment
contains torch/TensorFlow/Flax. No production runtime was installed into or edited.

**T1: PASS on Windows and Linux**, 28/28 variants, `Qwen2TokenizerFast`, candidate decision-token
IDs `[16, 17, 18, 19]`. T1 itself ran offline with no model weights.
Dependency/tokenizer acquisition was online and limited to the packages and
six files above; full audit runs offline with `USE_TORCH=0`, `USE_TF=0`,
`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `CUDA_VISIBLE_DEVICES=''`.

## Official computation and evidence

The unchanged `safeshift.pa3.native.train_report` calls the existing T1,
`native_audit.audit`, `native_score.score`, `score_decision`,
`anomaly_log_odds` and rank-based `auc`. No replacement scorer, AUROC or audit
was implemented. PA3 is higher-is-Anomaly, mathematically
`logsumexp(z1,z2,z3) - z4`; Level01-03 are Anomaly, Level04 is Normal.
The official code computes from raw decision-token logits and pools image rows;
it does not average shard AUROCs or use saved scores as score inputs.

Local evidence root: `data/processed/pa3_r2_cpu_completed_20261015/` in the
`audit/pa3-r2-cpu-complete-20261015` worktree. The final copied-back report is
`official_report_linux/`; `verify_run` passed after copying it from Linux.
Raw inputs remain at the evidence root documented in the prior handoff.
The one-off `collect_completion.py` only validates/summarizes official output
and hashes; it does not calculate scores or metrics. Large raw/audit/CSV files,
environment, snapshot and logs remain ignored.

The first Windows reporter invocation rejected a `..` input path with
`JOURNAL_ALIAS_FORBIDDEN`, before creating an official report. The subsequent
invocation resolved paths first, then failed after 442.153 seconds with
`CPU_RECOMPUTATION_MISMATCH`. Failure localization using the existing scorer
found the first mismatch in Shard 0, sample index 0: one intermediate probability
was `0.16577163151667484` on Windows versus `0.16577163151667482` in the saved
Linux result (1 ULP). This finding alone was not a full audit or a pooled AUROC.
The existing function on Linux reproduced that saved probability exactly.

The **complete** official audit was then rerun on CPU Linux, with the same source,
six pinned tokenizer files and the four exact archives. It exited **0** after
**373.090 seconds**, with `completed=true` and `scope=DESCRIPTIVE_FULL_TRAIN`.
All raw per-image results matched the saved results under the original exact
comparison; saved per-shard report/export metrics also matched. No tolerance,
score, audit implementation or stored result was changed to obtain PASS.
The Windows failures and diagnosis remain in separate logs; Windows bitwise
portability is a limitation, not a result silently marked PASS.

| Shard | Recomputed SUCCESS / planned | Integrity / seal / completion | Clamp-triggered images |
| --- | ---: | --- | ---: |
| 0 | 941 / 941 | PASS / true / true | 9 |
| 1 | 941 / 941 | PASS / true / true | 5 |
| 2 | 941 / 941 | PASS / true / true | 6 |
| 3 | 940 / 940 | PASS / true / true | 4 |
| Total | 3763 / 3763 | Exact disjoint original TRAIN universe | 24 |

All 3,763 recomputed scores and their four raw decision logits are finite.
The pooled eligible denominators are **749 Anomaly / 3,014 Normal**, or
2,257,486 positive-negative pairs. Coverage is 100%; no row was imputed or dropped.
The source manifest retains Level01=490, Level02=251, Level03=8, Level04=3014.

Reviewed aggregate evidence is also provided as
[small JSON](pa3_r2_cpu_completion_20261015.summary.json), with no sample IDs,
raw outputs, image/annotation content or machine-specific absolute paths.

| Local artifact (relative to evidence root) | SHA-256 |
| --- | --- |
| `completion_summary.json` | `c04f56c304d28cd79e0bf10a8dade8d67f3c060570b7393310c48332d430e1ab` |
| `tokenizer_t1_linux.json` | `7336389a35b709a3fe36e8a3613bef2ae906e523281a06a43cf761f40fb8e328` |
| `official_report_linux/metrics.json` | `21cbb7fded176c657298ab0e3dc5f2098801211082a453952de6e9feecf4daf4` |
| `official_report_linux/audit.json` | `87b005541c7342c42967e7a4e48723401d12e33699103875917b583a25db894e` |
| `official_report_linux/samples.csv` | `59023ddd838a6e2d2b6bda66c58a2a49e77c5d9557ac7f89308d12db65330911` |
| `official_report_linux/metrics.csv` | `a1c54869d58f35e16e0e239583e98709e2ea0d653533c615908afaa4ceafe314` |
| `official_report_linux/checksums.json` | `d6f90c0562043a383bdf1d928dbc796871e2ab84e0e093165751e8c6dca2335e` |
| `linux_environment.json` | `615954e7f68eeb7a9b8b8e1d2f8f5524e0a2dd2ff0b15705f58cd52f4977e766` |
| `train_report_linux_execution.json` | `30924c80fc765a5dda54a961d27b137407f976c1bdcbddc4afb163be79a33bcd` |

Additional CPU regression: the existing `tests.test_pa3_full_train.MergeAndMetricTests`
passed **5/5** in 45.264 seconds on the existing host Python 3.11.9/Pillow 11.3.0.
Command: `python -P -m unittest tests.test_pa3_full_train.MergeAndMetricTests -v`,
with `PYTHONPATH` resolving to the clean original execution checkout.
This covers pooled-versus-shard AUROC, ties, single-class/zero coverage, nonfinite
scores, and sealed merge failures. An initial import-only attempt in the minimal
tokenizer environment lacked optional Pillow; its error log is retained, and
the suite was run on the host rather than changing the audit environment.
Expected synthetic failure-package messages are not failures of the real audit.
No full repository suite or GPU/model tests were run: no production code changed,
and T1 plus the real full official audit are the task's direct verification.
Documentation checks passed: `git diff --check`, local Markdown link targets,
code-fence balance/whitespace, JSON agreement with the official report, and no
sample IDs or absolute paths in the small versioned evidence summary. Protected
production/config/manifest/prompt/notebook and README/ROADMAP/DECISIONS diffs are empty.

## Reproduce the official commands

Run from the clean **Linux execution checkout** at the commit above after staging
the same hash-verified archives and six tokenizer files. Paths below are relative
to that checkout. The local `linux_audit.py` records environment/staging steps;
`linux_location.json` is an ignored locator for the temporary Linux checkout.
The source bundle includes the required history; staging fetches its explicit
`refs/remotes/origin/main` ref before checking out the exact execution commit.

```bash
export CUDA_VISIBLE_DEVICES='' USE_TORCH=0 USE_TF=0
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
audit_python=data/processed/cpu_env/bin/python
audit_root=data/processed/cpu_audit
snapshot=data/processed/tokenizer/66285546d2b821cf421d4f5eb2576359d3770cd3
"$audit_python" -m safeshift.ls1.tokenizer --model qwen2_5 \
  --snapshot "$snapshot" --output "$audit_root/tokenizer_t1_recheck.json"
audit_runs=()
for shard in 0 1 2 3; do
  audit_runs+=("$PWD/$audit_root/inputs/shard-$shard/pa3-qwen-r2-train-shard-$shard")
done
"$audit_python" -m safeshift.pa3.native.train_report --repo "$PWD" \
  --snapshot "$snapshot" --runs "${audit_runs[@]}" \
  --output "$audit_root/official_report_recheck"
```

Use fresh output names for another run; exclusive writes must remain enabled.
The executed run used `tokenizer_t1_linux.json` and `official_report_linux`.

## Baseline form

| Field | Verified value |
| --- | --- |
| Model | Qwen/Qwen2.5-VL-3B-Instruct |
| Model revision | `66285546d2b821cf421d4f5eb2576359d3770cd3` |
| Dataset / split | InspecSafe-V1, original full TRAIN, previously exposed descriptive evaluation |
| Planned images | 3,763 original IDs, execution shards 941/941/941/940 |
| Scored / class denominators | 3,763 / 3,763; Anomaly 749, Normal 3,014; all SUCCESS |
| Dataset identity | Original full manifest SHA-256 `a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`; R2 manifest SHA-256 `e842c9e08f7fa28f72fa8536bc35fd7b5e2ad751481cb812c73e9f201f95afcf` |
| Configuration | C1; FP16, no quantization, SDPA, single T4 at inference; batch 1; greedy `do_sample=false`, one beam, max 32 new tokens; native processor, min/max pixels 200704/1003520; R2 pre-merger clamp |
| Prompt | `prompts/p2_classification_c1_v1.txt`, SHA-256 `816a9c2602fc6ab8c4589a0df22b9d7063f9427b7bda2554788f8c92a95bfbe3` |
| Seeds | Generation seed null (greedy); ordering seed `pa3-full-train-2026-10-13-v1` |
| AUROC PA3 | **0.8266558463706973** |
| AUROC Qwen labels | **0.5**; binary endpoint from generated labels, same 3,763 score-valid IDs |
| Accuracy, generated four levels | **0.03454690406590486 = 3.454690%**, 130 / 3,763 |
| Accuracy, generated binary labels | **0.19904331650279034 = 19.904332%**, 749 / 3,763 |
| Audit status | **PASS on CPU Linux**, strict raw recomputation and official sealed pooled report; Windows exact comparison failed on a 1-ULP intermediate value |
| Limitations | Previously exposed TRAIN; dependencies, cross-split duplicate history, domain/platform confounding; Level03 only 8 TRAIN images; missing Shard 1 outer receipt; Windows exact-float portability; no independent generalization or confirmatory improvement claim |

| Domain | Images | Anomaly / Normal | AUROC PA3 | AUROC Qwen binary labels | Accuracy four levels | Accuracy binary |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| coal_conveyor | 822 | 172 / 650 | 0.8952638640 | 0.5 | 7.055961% | 20.924574% |
| metallurgy | 543 | 9 / 534 | 0.8404078236 | 0.5 | 0.000000% | 1.657459% |
| oil_chemical | 778 | 287 / 491 | 0.7548521470 | 0.5 | 3.856041% | 36.889460% |
| power | 656 | 81 / 575 | 0.8721417069 | 0.5 | 1.067073% | 12.347561% |
| tunnel | 964 | 200 / 764 | 0.8634816754 | 0.5 | 3.630705% | 20.746888% |

All 3,763 generated labels map to Anomaly: 749 true Anomaly predicted Anomaly,
3,014 true Normal predicted Anomaly, and zero generated Normal. Thus the hard
binary AUROC is 0.5 and generated Anomaly FPR is 1.0. The continuous PA3 score's
ranking discrimination must not be described as good generated classification,
a calibrated probability, or a verified performance improvement/generalization.

Model defaults in `generation_config` and actual per-call generation kwargs are
distinct. The recorded actual kwargs override the upstream sampling defaults;
the existing auditor checks these kwargs for every image. There is no fitted
PA3 threshold here, so generated-label accuracy must not be called PA3 accuracy.

## Four-model requirement and next steps

[All four models remain mandatory](pa3_four_model_seminar_scope.md).
Qwen3-VL-8B-Instruct, InternVL3-2B-hf and Moondream2 receive no PA3 baseline
numbers in this task: no compatible verified experimental results were supplied
for this audit. Historical qualification/P2/LS1 results are not relabeled PA3.

The Research Lead subsequently selected the internal-score direction for proposal;
[DEC-PA3-011](../DECISIONS.md#dec-pa3-011--proposed-seminar-internal-hazard-score-direction-2026-10-16)
records it as PROPOSED pending final PR review/approval. The next approved work
must verify each model's native raw-logit or proven-equivalent interface and token
mapping, then prepare the fair four-model evaluation. Any new execution, holdout
or TEST use needs its own approved scope; this audit grants none.
