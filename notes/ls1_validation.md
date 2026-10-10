# LS1 CPU validation and Draft review handoff

Date: 2026-10-10 (Asia/Bangkok). Verified main BASE:
`1722f82d5ced5624e5182a3311c7e0e24fca9458`.
Branch: `codex/ls1-label-scoring`. Final HEAD and Draft PR URL are recorded in
the PR handoff; embedding a commit's own SHA in its tree would be circular.

## Actual validation

Host: Windows x86_64, Python 3.11.9, existing Pillow 11.3.0 and numpy 2.4.6.
No torch, transformers or tokenizers installation was present. No dependency
installation, model weight load, GPU execution or InspecSafe experiment occurred.

| Check | Actual result |
| --- | --- |
| Final `python -m unittest tests.test_ls1 -q` | 64 run: **62 PASS, 2 SKIP/BLOCKED**, 0 failures/errors; 11.931 s |
| Model-specific real tokenizer tests | Both SKIP with explicit missing snapshot reason; neither counted PASS |
| T1 Qwen2.5 CLI | **BLOCKED**, `PINNED_SNAPSHOT_NOT_SUPPLIED`; pinned revision absent in checked repo/HF cache locations |
| T1 InternVL3 CLI | **BLOCKED**, same reason; pinned revision absent in checked repo/HF cache locations |
| Notebook cells | Both notebooks compile, empty outputs, Internet OFF/T4 metadata, technical default, locked research defaults |
| Import boundary | Fresh process imports all LS1 modules without torch/transformers or dataset/model access |
| Official tracked code/config/prompt/script/notebook/manifest bytes | All existing files in those trees equal exact BASE Git blobs |
| DECISIONS.md and TASKS.md | Exact old byte prefixes preserved; append-only LS1 entries |
| `git diff --check` and Python compilation | PASS |

The final LS1 suite covers analytic/uniform/extreme probabilities, model-specific
token IDs, 28 format cases, multi-token/escaped/ambiguous representations,
wrong generated positions, EOS framing, raw versus processed scores, missing
tokens/steps, NaN/Inf, processed negative-infinity masking, greedy argmax
consistency, full-vocab probability mass, exact reference pixels, fixed prior,
optional guard behavior and its missed-hazard limitation, stable AUROC ranking
under probability saturation, INVALID/undefined denominators, explicit downgrade
counts, exclusive storage/checksums/inventory, raw-before-parse failures,
sealed failure/no-retry behavior, CPU recomputation, split-bound authorization,
runtime checksum-before-execution, portable prep/source packaging and unchanged
official tree bytes. Fake model/tokenizer results are visibly synthetic fixtures;
they establish logic behavior, not actual T1 or runtime qualification.

## Regression against the same BASE

Initial full-suite sandbox runs hit a Windows Git shell failure:
`couldn't create signal pipe, Win32 error 5`. Both BASE and branch had the same
35 failures/38 errors there. The full suite was rerun with the needed filesystem
permission, in isolated worktrees with identical LF checkout handling and
Python environment. This removed the sandbox obstacle, not the historical failures.

| Full `python -m unittest discover -s tests` | Run | PASS | Failure | Error | Skip | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Exact clean BASE | 1741 | 1690 | 36 | 13 | 2 | 891.905 |
| LS1 branch during broad regression | 1804 | 1751 | 36 | 13 | 4 | 912.694 |

The normalized failing/error case-name multisets match: **no branch-only or
BASE-only problem cases** in that comparison. These are existing failures,
including historical phase allowlists/pins/authority expectations and the
missing torch-dependent Moondream precision test. The full suite is **not
green**. No protected historical test/protocol/authority was edited to suppress
those failures. The broad run loaded 63 LS1 tests. Subsequent LS1-only numerical
and audit checks added one case and were revalidated on the final code by the
64-test run above; the untouched historical modules were not rerun needlessly.

Focused regression command:

```powershell
python -m unittest tests.test_ls1 tests.test_d9r23_classification_contract tests.test_d9r24_metrics tests.test_d9r25_harness tests.test_d9r26_bridges tests.test_p21_classification tests.test_p21_harness_evaluation tests.test_p21_kaggle tests.test_qwen2_5_runner tests.test_internvl3_prep -q
```

It ran 302 tests: 299 PASS, 1 existing D9R23 historical allowlist failure,
2 SKIP/BLOCKED, no errors (52.629 s). That same allowlist case fails on BASE.
Final LS1 changes were separately checked again as described above. Logs and
comparison receipts stay ignored under `data/processed/ls1_dev/` in each worktree;
they are not committed because raw test logs include temporary machine paths.

## Changed files (17)

```text
DECISIONS.md
TASKS.md
configs/experiments/ls1.v1.json
notebooks/ls1_internvl3_kaggle.ipynb
notebooks/ls1_qwen2_5_kaggle.ipynb
notes/ls1_runbook.md
notes/ls1_validation.md
safeshift/ls1/__init__.py
safeshift/ls1/artifacts.py
safeshift/ls1/audit.py
safeshift/ls1/core.py
safeshift/ls1/evaluate.py
safeshift/ls1/experiment.py
safeshift/ls1/kaggle.py
safeshift/ls1/runtime.py
safeshift/ls1/tokenizer.py
tests/test_ls1.py
```

No production runner, C1 prompt, P2/P2.1 parser/evaluator/authority, original
dataset definition/splits/labels, historical result or fixture was changed.
Original user worktree files remain untouched. No raw data, media, weights,
bulk output, credentials or generated experiment artifacts are staged.

## Readiness and unresolved evidence

Scorer, evaluator, recomputation tool and two notebooks: **IMPLEMENTED,
CPU/SYNTHETIC TESTED; real runtime NOT_RUN**. T1 for both models: **BLOCKED**.
Train/test: **LOCKED**, with a PENDING LS1 study proposal and no new permission.

Before any owner GPU run: supply existing pinned model/runtime prep bytes,
trusted source/archive/runtime-inventory checksums, matching library versions,
real model-specific T1 PASS, correct offline T4 preflight and independent review.
Before any InspecSafe run: Research Lead approval resolving DEC-LS1-001 plus
the exact split/run/model/source/method-bound receipt. No test tuning is allowed.
Physical Kaggle prep outputs, restoration on Kaggle, native logits alignment,
T4 memory/latency and full real tokenizer behavior remain unverified.

LS1 has not established that either model discriminates normal from abnormal,
that output bias explains the historical failures, that the three references
estimate a useful bias, or that calibration improves Accuracy/BA/F1/AUROC.
It may reduce Level01/anomaly recall while increasing Level04 predictions.
The optional guard has no general safety guarantee. LS1 remains outside RQ3.

Stop at the Draft PR for ChatGPT direct review and independent Antigravity audit;
do not merge or promote this handoff into research completion.
