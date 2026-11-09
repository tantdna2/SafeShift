# TRAIN3763 opaque CPython Input — 09/11/2026

## Current route: Base64 transport, publication STOP

Authority: [Owner task6731108968](https://github.com/tantdna2/SafeShift/pull/187#issuecomment-6731108968).
BASE is merged PR187/main `a89c8f7313328460368145cec96f26873fb29640`.
One new branch/Draft PR prepares code and offline evidence only. **No Kaggle
API operation/upload/create/version/delete, Attempt7, GPU, inference or TEST.**
The one-time publication exception is consumed. A new create requires fresh
reconciliation and separate authorization after review/audit/merge/postmerge
verification. The historical raw-tar publication procedure is **superseded and must
not be executed**. The operator remains STOP except separately allowed read-only
reconciliation. The fixed v1 target is usable only if reconciliation proves safe;
ambiguity or occupancy means STOP, never v2/alternate slug/overwrite/retry.

Owner reported `Creation failed — File already exists: 2621a`. Read-only listing
of the existing locally SHA-verified tar directly confirms both
`python/share/terminfo/2/2621A` and `2621a`, and both
`python/share/terminfo/h/hp2621A` and `hp2621a`. Owner's linked Kaggle staff
explanation supports automatic expansion with case-insensitive collisions; no
new backend probe was performed. Metadata/license selection is not the supported
cause of this specific failure. Do not delete/rename members or repack Python.

The new representation is **uncompressed canonical RFC4648 Base64**, standard
alphabet and padding, with no whitespace/newline/header. Only the encoded `.bin`
and strict manifest become published members. This changes content recognition,
not just the filename. Base64 is **not encryption**, with no password/key/secret.
**Kaggle preservation remains NOT_VERIFIED** until newly authorized publication
and independent remote byte proof. Local round-trip is not provider evidence.

| Identity | Length / SHA256 |
| --- | --- |
| Original CPython3.11.9 tar, unchanged | 29,713,170 / `f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d` |
| `safeshift-cpython3119-base64.bin` | 39,617,560 / `871cccab019cb6ef7417af6f3287233f3ba25e904fc007c429fdcb5e3a67b9f5` |
| `safeshift_train3763_python.json` | Canonical source-pinned manifest, schema `train3763-python-input-v2` |
| Dataset target | `nguynanhtn/safeshift-cpython3119-20240726/1`, private |

Both hashes are source-pinned, never accepted from uploader claims. Manifest
includes the complete unchanged original lock and transport descriptor. Schema
**v2** is distinct from Dataset **v1**. Exact binding changes; regenerate the
technical context using `describe`, never amend the original science grant.

### Local preparation, no publication

Reuse the existing verified archive and retained redistribution evidence; do not
download/reupload original Inputs/checkpoints/SDK. Use a fresh ignored path:

```powershell
$OperatorPython = 'data/processed/operator-venv/Scripts/python.exe'
$Original = 'data/processed/python-input-publication-20261109/cpython-3.11.9+20240726-x86_64-unknown-linux-gnu-install_only.tar.gz'
& $OperatorPython -B -m scripts.train3763_python_input prepare --archive $Original --output data/processed/python-opaque-new-package --license-name other --redistribution-ref '<existing reviewed rights evidence reference>'
& $OperatorPython -B -m scripts.train3763_python_input describe
```

The helper verifies original bytes before creating the package, encodes/verifies
the `.bin`, writes the strict manifest, then restores and rechecks the original
**outside** `dataset/`. It never extracts or executes Python. The original and
all notices remain intact. `dataset/` contains only `.bin`, manifest and CLI
`dataset-metadata.json`; metadata is not a published Dataset member. Proof and
restored `.tar.gz` stay in the parent. Never upload the parent directory.

Metadata has a root `description`, private intent and truthful `other` category.
This does not relicense bundled components or establish redistribution rights;
retain the existing reviewed notices/access evidence. Arguments record an
evidence reference, not legal approval. The pinned CLI actually uses its default
`public=False` to create privately; its metadata privacy field alone is not
enforcement. Never pass `--public`. Provider verification independently requires
actual privacy. No publication command is authorized by this runbook.

### Provider, reservation, submit and worker verification

Under a future separate authorization, `verify-provider --output <fresh-path>`
checks actual private owner/slug metadata, explicit `/1` listing of exactly two
members/sizes and independent downloads via `datasetVersionNumber=1`. Existing
pinned official SDK and authentication remain unchanged. Approved anonymous GCS
redirects carry no credentials. Raw bytes or one-member server ZIP wrappers are
accepted. Before ZIP parsing, bounded EOCD validation limits entry count to one
and central-directory metadata to 4KiB; ZIP64/multi-disk/extra entries/trailing
data fail. Exact name/type/encryption/expanded-length, manifest and transport
SHA are checked, followed by streaming restore and original length/SHA. No
extractor/interpreter runs during provider proof. Unknown response/history,
pagination, changed privacy/owner/version/bytes or poisoned wrapper means STOP.

This full proof runs before campaign ledger **INTENT** and repeats before
**PUSH_INTENT** and the single POST. Failed proof leaves ledger/history unchanged.
Existing one-operator locks, anti-replay and caps remain. GetKernel's unversioned
attachments or a locally manufactured PASS receipt cannot prove v1 bytes.

Worker checks exact binding, one read-only mount/layout/owner, exactly two files,
strict manifest and transport size/SHA. It streams restored original into fresh
scratch, checks canonical Base64/padding, original length/SHA, fsyncs and re-reads
durable original bytes. **Only then** does unchanged `train_python.extract`
validate/extract, probe exact 3.11.9 and feed inherited isolated venv setup.
No Python network or system fallback; pip/wheel/package installation is unchanged.
Legacy/Candidate160 source and frozen locks remain byte-identical.

Distinct case-sensitive tar members remain intact on Linux. Exclusive-create
collision on a case-insensitive filesystem fails without overwriting the first
file or probing Python. Partial restores/extractions remain for diagnosis and
cannot be reused/overwritten. Duplicate exact names and malicious tar entries
continue to fail through the inherited hardened extractor.

### Resource limits and evidence

Encoder reads 49,152 bytes per block; decode/hash reads at most 65,536, never a
whole archive. Only final-block canonical padding is admitted. Helper deadline
is 180s; provider total deadline 240s with inherited 90s/64MiB per-download bounds.
Worker hash/decode uses the supplied deadline; the inherited supervisor enforces
hard setup/extraction/probe wall time and log limits. ZIP loops are also bounded.
Disk admission reserves original+expanded limits in worker scratch
(134,570,770 bytes), 1MiB stage output reserve, and two download/copy inventories
plus 2MiB wrapper overhead and original length for provider scratch. Writes are
bounded by pinned lengths. Space/quota/I/O/fsync/deadline errors produce
BLOCKED/FAIL before model calls; partials remain and no retry occurs.

Synthetic tests measure streaming peak Python allocation below 1MiB across
multi-chunk fixtures. They cover corrupted/truncated/noncanonical/oversized bytes,
wrong original hash, disk/time limits, tar bombs, aliases/extra files/duplicate
keys, private/versioned Inputs, real SDK serialization through offline HTTP,
poisoned ZIPs, staging/submit ordering and immutable custody. Windows exercises
collision refusal; Linux exercises retaining both spellings. Actual Kaggle
RAM/quota/GPU/model fit are not established by these tests.

See [opaque acceptance](research/TRAIN3763_OPAQUE_PYTHON_ACCEPTANCE_20261109.md)
for final counts/source/notebook identities and local original-archive proof.
Reproduce using the existing pinned environments and fresh output paths:

```powershell
$env:SAFESHIFT3763_SDK_CPU='1'
& $OperatorPython -B -m scripts.qualify_internvl3763 --output data/processed/python-opaque-new-check --native --packages .venv/Lib/site-packages --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
python -B -m unittest discover -s tests -p test_smoke.py -v
```

Linux: `python3 -B -m unittest discover -s tests -p test_internvl3763_python.py -v`.

**DATASET_BYTE_PASS remains
NOT_VERIFIED.** Science SHA, Python3.11.9, original TRAIN data/IDs/config/grammar/
prompt, ordinal0 success, Attempts1–6, O5 and all scientific decisions remain
unchanged. New source/notebook/manifest hashes need review/audit/technical
requalification. Stop at one Draft PR for ChatGPT review and audit decision.
## Historical source

The [PR187 raw-tar runbook at its exact merged commit](https://github.com/tantdna2/SafeShift/blob/a89c8f7313328460368145cec96f26873fb29640/docs/TRAIN3763_PYTHON_INPUT.md)
retains the previous implementation and historical planning/accounting. Its
raw-tar publication procedure is superseded; its one-time publication exception
cannot be reused. Historical grants, acceptance reports and Attempts1–6 are
unchanged.
