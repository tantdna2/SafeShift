# TASK 4 CPU validation

BASE_SHA: `540078902370c88aede1d6c30be73f29fce6722e` (remote main verified).
Environment: Windows, Python 3.11.9, existing dependencies only; no installs.
All new fixtures are synthetic. API doubles execute the native Qwen wrapper,
LS1 loader/preprocessing logic and journal pipeline on CPU; they are not real
T1/runtime evidence. Original synthetic modules/tests are unchanged.

```text
python -m unittest tests.test_pa3_native -q
python -m unittest tests.test_pa3_synthetic tests.test_pa3_boundaries tests.test_ls1 tests.test_ls1_diagnostics tests.test_p21_classification tests.test_p21_harness_evaluation tests.test_d9r23_classification_contract tests.test_d9r24_metrics tests.test_qwen2_5_runner tests.test_qwen2_5_t4_runtime_prep tests.test_qwen2_5_t4_load_diagnostics tests.test_qwen2_5_initialize_diagnostics -q
git diff --check
```

Final new suite: **36/36 PASS** (38.329 seconds). This includes a real temporary
Git source-bundle roundtrip and a fresh-process CPU-auditor import tripwire.
The regression command above ran on both this candidate and an isolated exact
BASE checkout: **362 tests, 359 PASS, 1 FAIL, 2 SKIP, 0 errors** on each.
The sole failing identity on both is
`tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only`;
its historical allowlist rejects work already present at BASE. It remains
unchanged and the regression is **not wholly green**. Both real tokenizer
tests are SKIP/BLOCKED, never T1 PASS. No full repository discovery, actual
model/tokenizer snapshot read, GPU, real-data read or execution.

Protection check: **149 existing files byte-identical** to BASE across
PA3 synthetic, LS1, protocol, runners, configs, prompts and original PA3 tests.
DECISIONS/TASKS retain their complete BASE byte prefixes (append-only).
New native source AST contains no reference/calibration calls. Notebook
execution cells compile with no stored outputs; working diff check PASS.
No dataset, model, runtime binaries or raw output is included in the change.

Coverage includes native loader flags and cache reset, per-step raw persistence
before parser, raw/processed distinction, token/text/nonfinite/missing-step
errors, T1 PASS/BLOCKED/FAIL with API doubles, real file hash/revision failures
on fabricated snapshot directories, dependency/version refusal, source Git
commit/bytes/dirty/untracked checks, torn records and resealed result tampering,
CPU recomputation, partial/interrupted runs, one-shot qualification and complete
fixture TRAIN/report flow, all-INVALID qualification blocking data access,
metadata/GT/exposure/transitive-group/overlap errors, bootstrap mixed-domain
whole groups, and direct helper/launcher/model denial before protected input
reads despite caller receipts/environment flags. Notebook cells compile and
bootstrap errors produce checksum packages.
