# P2.1 static validation and audit handoff

All validation uses generated pixels, synthetic native envelopes, temporary
artifacts and local synthetic Git histories. No InspecSafe bytes, model weights,
model generation, GPU or external inference are accessed. Local verification
Python is 3.11.9; the owner production runtime remains pinned to 3.11.11.

Run focused regressions from the repository root:

```text
python scripts/verify_p21_offline.py
python -m unittest tests.test_p21_execution_authority.P21ExecutionAuthorityTests.test_actual_f2_structure_and_synthetic_final_merge -v
git diff --check
git diff --cached --check
```

The actual-F2 test is deferred before F1/F2 exist. After F2 it checks the real
Draft parents/tree/canonical commit bytes, rejects Draft execution, then tests
that same immutable F2 under a synthetic Standard Merge. This does not merge
any real branch. Exact commit SHAs and final test outcomes are in the Draft PR
handoff because F2 is created only after F1 and cannot alter F1 documentation.

| Required behavior | Synthetic verification |
| --- | --- |
| 1-9: plain/fenced JSON, missing canonical value, prose, multiple fences, schema, extra fields, wrong levels, duplicate keys | `tests/test_p21_classification.py` |
| 10-11: raw bytes unchanged; persistence, SHA/size reread before parser | parser persistence tests and `tests/test_p21_harness_evaluation.py` |
| 12-13: historical P2 unchanged; identical P2.1 acceptance for all models | parser byte checks, four-native-adapter tests, four-model full harness/export parity |
| 14-16: Draft blocked; correct Standard Merge; wrong parents/tree/F2 rejected | `tests/test_p21_execution_authority.py`, including real local Git objects and exact-F2 commit encoding |
| 17-20: missing/wrong previous manifest, reused run ID, unauthorized model/run/shard | authority lineage and before-dataset/backend negative tests |
| 21: missing/deleted/wrong v4 cannot reactivate v3 | source-marker dispatch and tracked-deletion negative tests |
| 22: static preflight cannot read dataset/model/GPU/network | fresh-process import/read/socket guards on Draft and synthetic final merge |
| 23: prompt, scientific metric engines, dataset contract, native runners/runtime and v1-v3 authorities unchanged | exact-BASE preservation checks and authority preservation pins |
| 24: no silent P2/P2.1 evaluation combination | explicit export/alignment selector, mismatched parser/amendment identities and mixed-version negatives |
| Stop before shards1-3 after shard0 zero yield/failure | progression rejection tests and a complete 1254-response generated-pixel positive fixture, including tampered-raw rejection |
| Kaggle source and one-shot offline workflow | `tests/test_p21_kaggle.py`: full local Git archive roundtrip, runtime metadata/ambiguity, historical byte restore, fake subprocess success/all-INVALID/FAILED packaging, notebook bootstrap failure and cell compilation |

The focused runner excludes exactly these two historical identities after
independent confirmation that they also FAIL on mandatory BASE:

- `tests.test_d9r23_classification_contract.ContractTests.test_exact_scope_history_and_append_only`
- `tests.test_classification_qualification.ProtectedStateTests.test_roster_grounding_d5_freeze_and_history_unchanged`

The former is a historical scope allowlist predating v2/v3; the latter requires
pre-amendment Qwen3 source bytes. Neither historical test is rewritten here.
Also checked on exact BASE: D9R22's
`test_scope_allowlist_and_no_dataset_weights_raw_outputs` fails its historical
allowlist; D9R22 is outside this focused runner. These are documented BASE
limitations, not a claim that the full repository suite passes.

Two affected D9R25 tests were updated for the explicit P2.1 consumer selector:
the historical v1 Git fixture declares absence of the P2.1 source marker, and
the byte-preservation assertion pins the old schema/candidate parser while
functional regressions retain default-P2 behavior. The v3 actual-release test
now locates its historical F2 at the original merge's second parent, as the
historical v2 test already does. Authority JSON files remain byte-identical.
Its preservation check excludes only the deliberately extended preflight,
evaluation and production consumers; historical schema/candidate parsing,
native runners, scientific contracts and all authority bytes remain protected.
The v2 preservation test likewise excludes the versioned evaluation consumer;
both historical suites keep exact durable-storage/rerun function checks while
the versioned parse/execution consumers have full default-P2 and P2.1
functional regressions. No historical authority implementation is changed.
Synthetic history constructors clone with `--no-checkout` before building the
target trees. This prevents newer release markers becoming untracked leftovers
after index-only `read-tree`, while preserving fail-closed source-marker dispatch.

No full repository suite, Kaggle venue run, actual FIX v2 attachment inspection,
real historical manifest inspection, audit, Antigravity call, merge or production
execution is performed by Codex. Owner artifact/runtime preflight and every
external review/merge gate remain mandatory. Prepared notebooks require only
release facts and attachment locators after merge; no further code or authority
session is required.
