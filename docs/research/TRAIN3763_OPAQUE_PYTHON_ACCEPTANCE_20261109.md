# TRAIN3763 opaque CPython transport acceptance — 09/11/2026

Scope: [Owner instruction6731108968](https://github.com/tantdna2/SafeShift/pull/187#issuecomment-6731108968).
BASE `a89c8f7313328460368145cec96f26873fb29640`; branch
`fix/train3763-opaque-python-transport`. This report describes Codex implementation
verification. Independent security/provenance audit has **not** been performed.

Runtime commit: `fd67e7fc392991fba47055556d412f5e5cfad573`.
Source SHA256: `7af690119660920f29465a45dbe20d40ac67ab5ceae90abdc7c420dc26ea2bf5`.
Manifest SHA256: `c6a508803f4e435261da40e3d1c6a08d855ba3fc05af84bf8ecb6edc29ba6e77`.
Science SHA256: `ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
All 84 inherited runtime files match BASE; the embedded manifest has 91 files.

| Notebook | SHA256 |
| --- | --- |
| `SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763.ipynb` | `0ac49ecd4329762b201e3bab0bf470971f771e505d6c22d7c7cbd0739d456d5f` |
| `SafeShift_INTERNVL35_GRAMMAR_V2_TRAIN3763_PREP.ipynb` | `f9da431381281c8240a2709a8d04d5711a9f8ae2a90561d656e699eac32ebd74` |

Both rebuild exactly from the committed runtime and contain empty outputs with
no execution authority. Full code hashes are in the acceptance JSON.

## Actual local original archive

Read-only inspection used the already present, locked CPython archive, with no
download, extraction, interpreter execution or real-image/model access. It has
5,192 members and directly contains both `python/share/terminfo/2/2621A` / `2621a`
and `python/share/terminfo/h/hp2621A` / `hp2621a`. The unchanged original archive
retains complete bundled notices. No repacking or terminfo deletion/renaming.

The real packaging helper restored all 29,713,170 bytes, with original SHA256
`f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d`.
The payload has 39,617,560 bytes and SHA256
`871cccab019cb6ef7417af6f3287233f3ba25e904fc007c429fdcb5e3a67b9f5`.
The original archive and local restoration/proof stay outside the upload folder,
under ignored `data/processed/python-opaque-validation-20261109/`. Only opaque
payload and strict manifest are proposed published members; CLI metadata has a
root description, private intent and `other`, with existing reviewed rights
evidence referenced rather than new legal approval.

## Offline tests

| Final source-stable group | Tests | PASS | SKIP |
| --- | ---: | ---: | ---: |
| Windows broad native CPU + pinned SDK qualification | 263 | 261 | 2 |
| Linux Input security/round-trip | 22 | 19 | 3 SDK cases covered on Windows |
| Linux setup/supervisor composition | 5 | 5 | 0 |
| Exact notebook rebuild | 3 | 3 | 0 |
| Foundation smoke | 2 | 2 | 0 |

No failures/errors remain. Both Windows OS skips pass in the Linux groups.
Groups overlap and are not added into a unique-test count. Broad qualification
ran on clean tracked commit `30cfcafa51e41d44a31e1eb5527a94c34108afcc` in 930.268s; subsequent
changes only finalize documentation/evidence. Its receipt/log are retained under
`data/processed/python-opaque-validation-20261109/final-cpu/`.
Log SHA256: `4f4a04befcd9a2b4308e8956b0a8e88d05ca1d278ce8a34082591beff1db1df9`.
Linux setup log SHA256: `df763102a8dde7e61f8f9e85c43377d63ba6535220b91a16c7d0de2db0da5a5c`.
The final Linux Input evidence is the terminal transcript: 22 tests in 184.059s,
19 PASS/3 SDK skips.

Fixtures replace archive locks and OS mount/probe/dependency observations only
where required, and are explicitly synthetic. They exercise real hash/streaming
decode/frozen safe extraction and actual inherited isolated setup composition.
Native CPU tests use scripted logits and synthetic images, no real model weights.
The official pinned SDK serializes real requests into offline HTTP adapters with
sockets forbidden, including anonymous GCS redirects and raw/ZIP responses.

Coverage includes case-fold collision retention on Linux and refusal without
overwrite/probe on Windows; exact and multi-chunk/padding round-trip; malformed,
truncated, noncanonical, extra/short/oversized and wrong original/transport bytes;
duplicate manifest keys, aliases, private/owner/version/layout drift; tar bombs,
unsafe links/entries; disk, fsync and deadline errors; measured streaming Python
allocation below 1MiB; bounded ZIP central-directory allocation; no Python network;
pre-INTENT/pre-PUSH_INTENT failure with ledger/mirror byte preservation; duplicate
submission/history protections and notebook/source rebuild.

An exploratory Linux run during edits lacked the expected child setup receipt;
the final source-stable complete Input rerun passed that test and the full group.
The exploratory failure is excluded from final PASS counts; no unverified cause
is asserted. Historical scientific/runtime acceptance reports are unchanged.

## Reproduction and limits

```powershell
$env:SAFESHIFT3763_SDK_CPU='1'
data/processed/operator-venv/Scripts/python.exe -B -m scripts.qualify_internvl3763 --output data/processed/python-opaque-new-check --native --packages .venv/Lib/site-packages --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
python -B -m unittest discover -s tests -p test_smoke.py -v
```

Linux: `python3 -B -m unittest discover -s tests -p test_internvl3763_python.py -v`
from the source root on WSL, with scratch temp directories on Linux. The Linux
orchestrator is CPython3.14; exact 3.11.9 worker selection is tested with explicit
synthetic probe doubles and inherited composition, not a real Kaggle interpreter.
Only the existing local software/dependency environments are used.

**DATASET_BYTE_PASS / Kaggle preservation are NOT_VERIFIED.** No live Kaggle API,
upload/create/version, Attempt7, GPU, real-model/image inference or TEST occurred.
Python3.11.9, original data/IDs, ordinal0 success, Attempts1–6, O5 and scientific
decisions remain unchanged. The consumed one-time publication exception cannot
be reused. Stop at the single Draft PR for ChatGPT direct review and decision on
independent audit, separately authorized merge and postmerge verification. Fresh
publication reconciliation/authorization and new technical qualification remain
required before any future operation.
