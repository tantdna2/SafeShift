# Task 5 CPU validation and limitations

BASE_SHA: `747171e011e35bc8995338402a80ba7ea70d8ff7`, verified remote main.
Environment: Windows, Python 3.11.9; existing dependencies only. No GPU,
InspecSafe metadata/images, model/tokenizer snapshot or dependency download.

```text
python -m unittest tests.test_pa3_feasibility tests.test_pa3_native -q
```

**58/58 PASS**, 116.979 seconds. Synthetic API doubles only. This run includes
the single-model-load ticket and source checks. After adding archive alias
preservation and an actual archive-restoration/import step to the owner Prep
tool, the affected checks were run separately:

```text
python -m unittest tests.test_pa3_feasibility.PrepTests tests.test_pa3_feasibility.ImageBoundaryTests -q
```

**10 run, 9 PASS, 1 SKIP**, 0.882 seconds. The additional real symlink test was
SKIP because this Windows host lacks symlink creation permission. Thus the
current combined suites contain 59 tests; the complete combined invocation
was not repeated after that isolated Prep change. Linux alias preservation is
not claimed verified here: actual owner Prep must pass its archive roundtrip
and exact version/import checks before inference. The regular-file archive
roundtrip, model allowlist packaging, disk shortage, image and model tickets
all passed. No online Prep run was performed in Codex.

Coverage includes real temporary Git F1/F2/standard-merge fixtures, Draft/wrong
source/dirty refusal, pilot grant and manifest/seal binding, direct helper denial
before protected reads, exact synthetic pixels/IDs/order, duplicate generation
and model-load refusal, fixed-seed 40-image 20/20 selection, shortage/no-fallback,
exposure/unknown TEST relations, exact duplicates/Normal point/transitive groups,
original-label provenance, per-image membership/checksum refusal, an end-to-end
40-image CPU fixture pilot with observed closure persisted before image access,
raw-before-parse/CPU recomputation and descriptive reporting, prior technical
audit/seal tamper refusal, notebook code compilation, no inference installs,
and Task 4 journal/failure/bootstrap regression coverage.

The existing Task 4 test helper now patches the new authority/source/ticket
boundary only inside its CPU model-double context; this does not add a runtime
injection point. The runtime-hash-denial fixture now uses an explicit archive,
matching the new no-directory-discovery launcher. Scientific assertions and
existing LS1/PA3 mock regression files were not weakened or changed.

## BASE comparison

Exactly this command ran independently on the candidate and an isolated exact
BASE worktree:

```text
python -m unittest tests.test_pa3_synthetic tests.test_pa3_boundaries tests.test_ls1 tests.test_ls1_diagnostics tests.test_p21_classification tests.test_p21_harness_evaluation tests.test_d9r23_classification_contract tests.test_d9r24_metrics tests.test_qwen2_5_runner tests.test_qwen2_5_t4_runtime_prep tests.test_qwen2_5_t4_load_diagnostics tests.test_qwen2_5_initialize_diagnostics -q
```

Both: **362 run, 359 PASS, 1 FAIL, 2 SKIP, 0 errors**. Candidate 73.948 seconds;
BASE 71.109 seconds. The same failing identity is
`tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only`.
Its historical source allowlist already rejects files present at BASE. This
test remains unchanged; regression is **not wholly green**. The two real
tokenizer tests remain SKIP/BLOCKED, not real T1 PASS.

No full-repository discovery was run: these suites cover the modified native
path and its source/runtime/tokenizer/parser/evaluator/protocol dependencies.
The subsequent isolated Prep/ticket edits were checked by the targeted commands
above; no new scientific/protocol implementation changed after the comparison.

## Integrity and handoff

`git diff --check`: PASS. **150 original files byte-identical to BASE** across
LS1, protocol, runners, existing configs/prompts, original PA3 mock code/tests
and ROADMAP. DECISIONS.md and TASKS.md retain their complete BASE byte prefixes;
only Task 5 entries are appended. Existing native scorer mathematics, CPU audit,
cohort candidate algorithms and frozen runtime plans are unchanged.

F1 contains code/tests/docs/notebooks; F2 adds only the literal technical
authority descriptor pinning F1, with pilot null. Exact commit and Draft PR
identities are in the PR handoff because they do not exist before committing.
The release's Draft rejection is checked again after F2 exists. No audit or
merge is performed by Codex. No model/runtime/source release artifacts, raw
outputs, credentials or real manifests/images are committed.

KAGGLE_PREP_STATUS: tools prepared and CPU-fixture checked; physical inputs
absent/unverified. TECHNICAL_RUN: BLOCKED pending audit/merge and actual source,
model/runtime inputs. PILOT_RUN: BLOCKED additionally on real technical PASS,
custodian metadata/exposure evidence, exact Lead manifest approval and separately
reviewed committed pilot grant. No T4 feasibility or PA3 discrimination result
has been obtained. See [owner steps](pa3_task5_kaggle_runbook.md).
