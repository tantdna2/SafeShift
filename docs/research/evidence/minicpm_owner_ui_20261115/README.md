# MiniCPM Owner UI — CPU evidence,15/11/2026

Same branch and Draft PR195. Runtime commit
`a7ac5f9d90b921d2db9bdb7de1c89681956d9878`; the later delivery changes notebook,
documentation, validation runner and historical-snapshot test context only.
Runtime inventory SHA256:
`1ae53f138508c35e2863367f052d3268c862b944294be810e23600d675948335`.

| Run | PASS | FAIL | SKIP | Scope |
| --- | ---: | ---: | ---: | --- |
| core | 113 | 0 | 5 | Existing fulltrain/original Input/resource/history/raw tests +11 new UI cases + packaged notebook |
| native | 19 | 0 | 0 | Pinned CPU processors/meta-loader/scripted generation and numerical resampler/scalar reference; no weights/real forward |
| linux | 5 | 0 | 0 | The five Windows process-group/deadline/parent-death skips |
| operator-initial | 129 | 2 | 1 | Complete existing collector/Python Input suites plus three new two-pair SDK transport cases |
| snapshot-corrected | 2 | 0 | 0 | Both historical identity assertions, now checked at exact original BASE |
| alias-linux | 1 | 0 | 0 | The Windows symlink skip, exercised on Linux |
| notebook | 9 | 0 | 0 | Final generator after Vietnamese Owner UI markdown changed; embedded runtime unchanged |

**269 distinct test cases have a PASS across these runs.** This is a combined
coverage statement, not a claim that the first132-case operator invocation passed.
All original failure/skip receipts remain. The9-case notebook run is a subset
of core, and the5 Linux cases are the core Windows skips. Zero model/provider/
GPU calls, zero network attempts, zero private image reads and production-ledger
writes. This is author CPU testing, not independent audit or live readiness.

The first operator run failed two assertions that equated the MiniCPM candidate's
dynamic source inventory with the frozen InternVL Operator. These assertions
also fail against PR195's **prior HEAD18351f8**, before this continuation.
The corrected tests keep the exact original digest constants and materialize
only the92 runtime files from BASE341ab626 in a disposable fixture via Git objects.
They additionally verify unchanged native functions and scientific configuration,
and require an explicit seven-file candidate-only source delta. No historical
source lock, expected digest, Operator checkout or grant was edited to make PASS.
The candidate has its own new source identity and cannot execute with InternVL's
old release. See `tests/frozen_internvl_snapshot.py` and the two corrected tests.

Each JSON receipt retains original source/test/log hashes, platform/interpreter,
counts, skips and limitations. [summary.json](summary.json) contains final file
SHA256s, original-versus-candidate identity evidence, distinct-case count and
export provenance. Exported logs normalize CRLF to LF and replace the absolute
repository prefix in the initial failure traceback with `<repo>`; original logs
and their hashes remain under ignored `data/processed/`. No real raw outputs or
large/private model artifacts are included. The new source payload is identical
in every receipt; final notebook regression covers the later markdown-only
generator change. The historical-snapshot helper is included in the final manifest.

Reproduce from this worktree, using the retained operator and native CPU stacks:

```console
python -B -m scripts.qualify_qwen_minicpm_fulltrain --output data/processed/<new-core>
<existing-pinned-operator-python> -B -m scripts.qualify_qwen_minicpm_fulltrain --component operator --output data/processed/<new-operator>
<existing-pinned-native-cpu-python> -B -m scripts.qualify_qwen_minicpm_fulltrain --component native --native-snapshot <existing-public-minicpm-source> --native-index <existing-locked-public-index> --output data/processed/<new-native>
python3 -B -m scripts.qualify_qwen_minicpm_fulltrain --component supervision --output data/processed/<new-linux>
```

For WSL on a Windows worktree, set GIT_DIR/GIT_WORK_TREE to its Linux Git/worktree
paths; do not edit the Git pointer. Two infrastructure attempts were retained
locally: sandbox denied WSL before escalation, and a nested PowerShell/WSL `-c`
quote failed before tests. The corrected file-based Linux invocation passed.
No dependency installation, Kaggle probing, model load or scientific qualification.

The actual candidate packager was also exercised with synthetic metadata and the
exact committed notebook builder under ignored `data/processed/minicpm-ui-synthetic-package`.
Its status remains CANDIDATE_RELEASE_BLOCKED. It is a rehearsal, **not an Owner-run
production capsule**. Authentic projection/rights/caps/release/provider versions,
final-source live verification, ChatGPT review and independent audit remain gates.
