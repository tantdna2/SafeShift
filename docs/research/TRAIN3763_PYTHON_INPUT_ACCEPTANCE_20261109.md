# TRAIN3763 offline CPython Input acceptance — 09/11/2026

Scope: [Owner task6720571990](https://github.com/tantdna2/SafeShift/pull/186#issuecomment-6720571990).
BASE `f88a152f481691bf678ad721ec6d2f25f95084bf`; branch
`feat/train3763-offline-python-input`. This is implementation verification by
Codex, **not independent audit**, publication proof or scientific qualification.

## Source identity

Runtime commit: `cc1edb8dadf07a74ac6138f097f6a53f92b0585c`.
Runtime SHA256: `3c488254f751de216c0e1d23fd576c70b773a40e6e399d20039dc6ddd69f1e8e`.
Science SHA256: `ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
All **84 inherited manifest files** match BASE bytes. The runtime manifest now
has 91 files, including the campaign-only Python Input helper.

| Notebook | SHA256 |
| --- | --- |
| `SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb` | `3f845a32c120adb0d51a726ede6ed9eec4a90527ae133a29cd3ab99f8fcd3765` |
| `SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763_PREP.ipynb` | `1386a5400998313afe433aa198dad1e19c0b7b0130781a9b224bbec5a7fd16b2` |

Both rebuild exactly from the committed runtime, contain no cell outputs and
embed no grant. Subsequent changes only concern tests, Operator staging error
ordering and documentation; they do not change embedded runtime bytes.

## Evidence and limits

The new security tests use bounded synthetic tarballs and actual extraction/hash
code. The dedicated setup child invokes inherited `prepare_runtime`; fixture
doubles replace interpreter identity and dependency installation, and assert
that venv creation selects the verified Input path. `train_python.urlopen` is
spied and must receive zero calls. A separate real OS subprocess probe rejects a
corrupt executable, and a real setup CLI child exports failure when Input is
absent. No real CPython archive was downloaded/executed in this task.

The pinned official SDK tests exercise actual request serialization through an
offline HTTP adapter with sockets forbidden. They verify private owner/slug,
explicit version1, exact file listing, independent downloaded bytes and poisoned
wrapper rejection. The broader capsule/lifecycle fixtures isolate Python provider
proof with an explicit test double; the Python SDK suite tests that proof itself.

Covered failures: missing/duplicate/wrong-layout/writable/aliased mount;
manifest/private/version/owner/slug mismatch; changed bytes/size; corruption;
traversal, hardlink, escaping symlink, FIFO, duplicate/link-ancestor entries;
member/expanded-size bounds; disk/deadline; wrong interpreter/version/path;
restart preserving extraction; provider transport/HTTP/pagination/listing errors;
poisoned ZIP path/duplicates/symlink; request/remote attachment drift; no push
intent on failed Python proof; ledger/mirror and scientific source invariance.

Detailed local logs and receipts are retained under ignored
`data/processed/cpython-input-validation-20261109/`. Final counts, commands and
hashes are recorded in the adjacent acceptance JSON.

The broad qualification ran **252 tests**: 247 PASS, two OS skips and three
initial regressions. Those three were fixed and rerun **3/3 PASS**: preserve the
existing-handoff rejection before validating a new private path, and give the
two capsule-submit transport fixtures their explicit Python-proof test double.
The final affected E2E/Input run is **28 tests: 26 PASS, two OS skips**. Linux
adds **13 Input PASS** (two SDK skips covered on Windows) and **5 setup PASS**,
including both Windows OS skips. Notebook rebuild and foundation smoke: **5/5
PASS**. Across these groups there are **261 unique tests with final PASS** and
no unresolved failure. This is combined evidence, not one clean full-suite rerun.

The broad run imported tests at `0d8e29a` before test fixes; its generated receipt
records HEAD/file hashes at completion. Preserve that initial FAIL receipt and
use the final affected/rerun logs for changed tests. Runtime source was unchanged
throughout. Final implementation/test commit is `b908938f143d0c55e1d64f0954930e560b6d97fe`.

Reproduce the broad CPU qualification with existing pinned software only:

```powershell
$env:SAFESHIFT3763_SDK_CPU='1'
data/processed/operator-venv/Scripts/python.exe -B -m scripts.qualify_internvl3763 --output data/processed/python-input-new-check --native --packages .venv/Lib/site-packages --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
python -B -m unittest discover -s tests -p test_smoke.py -v
```

On Linux, use a clean local checkout and run `test_internvl3763_python.py` plus
`test_internvl3763_e2e.LauncherSupervisorSetupCompositionTests` with `PYTHONPATH=tests`.
The Linux host has CPython3.14.4 for orchestration; synthetic probe results are
explicit test doubles, not proof of the real CPython3.11.9 Kaggle environment.

No live Kaggle API, upload, submit, GPU, model weights, real image inference,
TEST, Attempt7 or historical ledger/mirror mutation was performed. Private
Dataset publication and real worker execution remain NOT_VERIFIED. Direct
ChatGPT review, independent audit, separately authorized merge and new
AUDIT_V1/TECHNICAL_V1 remain required before separately operated live work.
