# Issue167 CPU validation — 02/11/2026

Scope: software preparation/synthetic CPU only; no Kaggle/GPU/model forward,
private image/raw/GT/TEST access, full TRAIN grant or scientific selection.
One branch `thesis/fulltrain-3763-repair-20261102`, BASE
`0295172783dcf82426923d1af621dde9db8ed42c`, document-first
`ff64958c22684e8713b428b439521f8f3cb1222a`.

Runtime source `58c94be9c263b4d96a0111df3d2941c3e4c670ad`; code/tests/notebooks
snapshot `e711d241f61743fe888db59906434e5655a0e59e`. Subsequent validation docs
do not change these executable bytes. Final PR HEAD is recorded on GitHub.

## Validation records

Windows CPython3.11.9 focused command (from root, `PYTHONPATH=tests`):

```console
python -B -m unittest test_candidate_integration test_fulltrain test_fulltrain_notebooks test_candidate160_routes test_minicpm_resampler_fp32 test_candidate160_notebooks -v
```

54 tests: **50 PASS,4 SKIP,0 failure/error**,80.387s. Four native MiniCPM tests
require a locked public source/isolated stack, not enabled in this task. Log
`data/processed/issue167/windows-focused.log`, SHA256
`389a77c6600f24d0c2401eb51edf77d80f815dd6c093e89b871f13f03a14f05f`.

The27 new tests comprise24 planner/journal/preflight tests and3 notebook/CLI
tests. They exercise3763 planned IDs for each candidate, tail/no-op scheduling,
SUCCESS/INVALID/technical error, explicit repair and rerun, changes requiring a
new series, raw-before-parse, torn raw, load failure, deadline, import/export,
checksum/history/duplicate/permission failures and preparation cells in empty
CPU processes without site-packages. This is not3763 native model calls.

Full Linux regression is run from a `git archive` export of the fixed snapshot
above into a fresh `/tmp` directory. Only read-only Git object context points
back to the original repository; no ignored/local files are copied. All
SAFESHIFT opt-in environment variables are removed. Command:

```console
python3 -B -m unittest discover -s tests -v
```

Linux WSL2 x86_64/glibc2.43, CPython3.14.4: **542 tests,500 PASS,41 SKIP,
1 setup ERROR**,449.598s. The error was an unchanged Phi packaging test calling
`TemporaryDirectory(dir=ROOT / "data/processed")` while a clean Git export has
no ignored `data/processed` directory. No fulltrain/runtime test failed.
Full log `data/processed/issue167/linux-final-snapshot.log`, SHA256
`bce90a5304056cbf30a309dec5b29c3c2938a512601fdbf07360d855e9c5330c`.

The same exact Git snapshot was re-exported, an empty `data/processed` was
created, and the single affected test rerun: **1 PASS**,0.033s, source unchanged.
Command (with `PYTHONPATH=tests`):

```console
python3 -B -m unittest test_phi_evidence.DiagnosticTests.test_cli_package_is_private_t4x2_and_never_runs_or_issues_grant -v
```

Rerun log `data/processed/issue167/linux-setup-rerun-v3.log`, SHA256
`568285ee19f2176666205f69fbf34e3cd63bc4e403c1cf62dc953d5e05de901e`.
Two preliminary rerun harness attempts failed to import the test because WSL
had removed the prior `/tmp` snapshot between invocations; both logs are retained.
The successful rerun re-exports the snapshot and tests it within one process.
Thus501 executable tests have PASS evidence plus41 explicit skips; **not a
claim that the single full-suite invocation returned success**. Skips cover
unavailable native/public-source CPU stacks, optional bootstrap and platform
checks; no GPU or model qualification is implied. Full suite was not repeated
after this isolated fixture-directory setup correction.

## Failure preservation and checks

First full Linux run in the mutable workspace:542 tests,497 PASS,41 SKIP,
2 FAIL,2 ERROR,1248.652s. Log SHA256
`fa8b62bf98d9a09c1e1f313a2b851089d41923974d2b67d11c01435620c625b3`, retained at
`data/processed/issue167/linux-full.log`. Three errors/failures were notebook
exact-source mismatch while source was updated during that run; one regression
still required old AGENTS prefix after the authorized document-first prepend.
The test now verifies exact Owner document commit and separately verifies
historical objects/locks; historical source locks were not changed. The stable
snapshot run replaces this failed run as final evidence, without deleting it.

All16 generated notebooks: embedded source matches on-disk source, inventory
SHA256 matches metadata, every code cell compiles, outputs empty, execution
counts null. Thirteen older notebooks changed payload/source/ref only;
instruction text matches after substituting the source/ref. Three new notebooks
are explicitly FULLTRAIN_PREPARATION_ONLY/BLOCKED and cannot activate inference.
Rebuilding old notebooks does not transfer old authority or GPU qualification.

`git diff --check ff64958c22684e8713b428b439521f8f3cb1222a HEAD` passes for the
implementation. BASE-to-HEAD retains one pre-existing blank-line-at-EOF warning
in DECISIONS from the document-first commit; append-only decision bytes are
preserved. Protocol/config Seminar, C1, model/checkpoint/source locks, generation,
HNLO and MiniCPM numerical adapter are unchanged. No data/archive/weights are
tracked; existing unrelated local files are untouched.

Synthetic CLI preparation:3763 planned statuses per candidate, zero model calls,
no predictions; output `data/processed/issue167/preparation-01.zip`, SHA256
`f283d71f23ce4f5820933cbab4e4267e8a133c6dc39116118bc074679b91fd9e`.
Caps160 calls/600s in this example are software-test parameters, not O5/O6.

Real Input/checkpoint/Python/packages/disk/GPU/CUDA, native fulltrain mappings,
legacy history import/selection, G0–G6 final release, O2–O6, independent audit,
merge and postmerge remain **BLOCKED / NOT VERIFIED** as applicable. MiniCPM
remains label-only. No claim of3763 SUCCESS, full roster, scientific baseline,
Accuracy/Macro-F1 or independent audit PASS.
