# Issue171 CPU validation and remaining release work

Date: 02/11/2026. [Draft PR #172](https://github.com/tantdna2/SafeShift/pull/172).
BASE: `1acb3ef7c0deadbbde7da0b1c63b71296e3950e5`.
Document-first commit: `8fdfc8dd95f3f25229f40605c14275840709330e`.
Runtime payload: `d12dc2d0796c22e077dfad7e6cd009710d422151`.
Notebook/test snapshot: `be2e2207a3bac1dafc59e3cb7de0a63cc514c06c`.
Regression correction: `585779791b38495cfbe10a53e0154b7bc30ea4b8`.

This is evidence for CPU preparation and review, not a native release PASS.
No private TRAIN master/projection/images/GT/raw, weights, Kaggle/GPU, real
inference or TEST were accessed. Synthetic fixtures and scripted native-boundary
objects are not model predictions or scientific results.

## Checks actually run

| Check | Exact snapshot / Python | Outcome |
| --- | --- | --- |
| Windows new tests and all six notebooks | `be2e220`, Python3.11.9 | 27 PASS, no failures/errors/skips; 105.031 seconds |
| Linux full suite | `be2e220`, Python3.14.4 | 569 run: 527 PASS, 41 SKIP, 1 FAIL, no errors; 567.709 seconds |
| Linux corrected integration module | `5857797`, Python3.14.4 | 7 PASS, no failures/errors/skips; 1.195 seconds |
| Synthetic preparation CLI | `be2e220` | 3 distinct new series, identical synthetic cohort, 3,763 pending/model, 11,289 planned initial calls, zero model calls; ZIP verified |
| Historical preservation | BASE versus new commits | Four required documents in first commit; original text retained. Existing notebooks/configs/candidate/pilot/parser/science bytes retained |

Machine-readable receipts: [Windows](windows-final-01.json),
[Linux full invocation](linux-final-01.json), [Linux regression rerun](linux-regression-02.json).
[Index](index.json) binds their hashes, immutable snapshot archive hashes, source
manifest, all six notebook hashes, development failures and synthetic ZIP hash.
The full invocation remains **FAIL** in its original receipt. It was not rerun
in full after the targeted correction. All seven tests in the affected module
passed on the subsequent snapshot; runtime, source locks and notebook bytes
did not change. Later evidence/document commits do not alter tested code.

The Linux failure was
`CandidateIntegrationTests.test_protected_pilot_c1_generation_and_source_bytes`:
the old test required the entire thesis plan to equal Issue167's document-first
commit. Issue171 explicitly requires a new Owner directive in that document.
The correction pins the new file to Issue171's document-first commit and checks
the exact old title and entire old body remain unchanged. Historical protected
Git-object hashes and source locks remain unchanged; the guard was not removed.

The 41 skips include optional pinned-native/public-source, tokenizers and network
bootstrap checks, plus a Windows-only junction test; names/reasons are in the
Linux receipt. Python3.14 here
is a stdlib test host, **not** the approved native worker version. Native ML
dependencies, processor/compiled ABI and real model behavior were not validated
by these invocations. The test runner disables native opt-ins, hides CUDA and
sets Hugging Face/Transformers offline mode.

Earlier development evidence is retained locally and summarized in the index:
these were working-tree runs, so their `source_commit` identifies the then-HEAD,
not an immutable snapshot of the uncommitted development code.
23 controller tests passed; a first notebook check failed six byte-comparison
subtests because Windows wrote CRLF. The builder now explicitly writes UTF-8/LF
bytes. The original receipt's `passed=-2` was also a subtest-counting defect;
subsequent receipts count failed parent tests correctly. Neither the failed log
nor its original receipt was overwritten. Final Windows notebook checks passed.

## Scope covered

- All three synthetic initial plans contain exactly3,763 IDs with no inheritance;
  four synthetic shards complete each plan and resume becomes a no-op.
- Resume/repair separation; identity, series, cohort/order/hash rejection;
  explicit failed-outcome/cause/fix/regression binding; unknown reservation block.
- Raw persisted before parser; load/parser/storage/torn-raw failure retention;
  durable INVALID; native-custody binding; changed image blocked before a call.
- ZIP checksum/member validation and import into a new workspace; no overwrite;
  foreign history rejection; source/checkpoint/configuration identity preserved.
- Scripted CPU peer composition through existing adapters and native evidence
  validators. Hardware/admission/loading boundaries are mocked; no real native
  load or model-fit claim follows.
- Bounded Input discovery/hash/mapping cases; storage/fsync/quota cleanup;
  false receipts cannot unlock execution; public entries stop before private I/O.
- Six deterministic notebooks compile with empty outputs, execute twice in clean
  CPU children, export BLOCKED with no attempts/calls, and reject corrupt payloads.

## Reproduction

Use a separate checkout of the stated snapshot with the repository's historical
Git objects available. Do not run from an untracked legacy working tree. Create
an empty ignored `data/processed/` directory first; an existing Phi test requires
that parent. From that checkout, use a new output path for each command:

```console
python -B -m scripts.check_fresh_fulltrain_cpu --pattern "test_fresh_fulltrain*.py" --output data/processed/review171/windows-new
python -B -m scripts.check_fresh_fulltrain_cpu --pattern "test*.py" --output data/processed/review171/linux-new
python -B -m scripts.check_fresh_fulltrain_cpu --pattern test_candidate_integration.py --output data/processed/review171/regression-new
python -B -m scripts.prepare_fresh_fulltrain --output data/processed/review171/prep-new --max-calls 3763 --max-seconds 60
```

The recorded runs exported `git archive` snapshots into temporary directories,
created that empty parent, and supplied read-only Git context for historical
object assertions. No untracked local files were copied. Snapshot/harness and
log hashes are in the index; original stdout/test logs and receipts remain under
ignored `data/processed/issue171/`. Public receipts contain source hashes and
test metadata only. The synthetic CLI limits above are test parameters, not O5
caps or permission to execute TRAIN.

## Release remains incomplete

See the [runbook and O2-O6/B1-B6/G0-G6 matrix](../../../FRESH_FULLTRAIN_171.md).
Qwen has no qualified fresh native source/checkpoint/runtime/HNLO contract.
Peers reuse existing native adapters, but fresh provisioning/supervision and
hard deadlines still need integration, pinned-native CPU evidence and authorized
live validation. The six notebooks are preparation/diagnostic artifacts; they
do not inspect real Inputs, provision workers or execute production.

Real master/projection custody, exact checkpoint allowlists, final worker Python/
dependencies/ABI, driver/GPU/CUDA, RAM/disk/quota/model-fit/time budgets and actual
load/inference/export remain NOT_VERIFIED or NOT_RUN. No approval, O5 value,
scientific selection, new HNLO method or all-SUCCESS claim is supplied. MiniCPM
remains label-only. ChatGPT review of final GitHub HEAD, independent Antigravity
audit and separately authorized merge/release are still required. Stop at Draft.
