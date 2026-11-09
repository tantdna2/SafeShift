# TRAIN3763 opaque CPython Input — 09/11/2026

## Current route: Base64 transport, publication STOP

Authority: [Owner task6731108968](https://github.com/tantdna2/SafeShift/pull/187#issuecomment-6731108968).
BASE is merged PR187/main `a89c8f7313328460368145cec96f26873fb29640`.
One new branch/Draft PR prepares code and offline evidence only. **No Kaggle
API operation/upload/create/version/delete, Attempt7, GPU, inference or TEST.**
The one-time publication exception is consumed. A new create requires fresh
reconciliation and separate authorization after review/audit/merge/postmerge
verification. Historical publication commands below are **superseded and must
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
Reproduction commands in the historical acceptance section below still apply
with fresh output paths and the current source. **DATASET_BYTE_PASS remains
NOT_VERIFIED.** Science SHA, Python3.11.9, original TRAIN data/IDs/config/grammar/
prompt, ordinal0 success, Attempts1–6, O5 and all scientific decisions remain
unchanged. New source/notebook/manifest hashes need review/audit/technical
requalification. Stop at one Draft PR for ChatGPT review and audit decision.

## Historical PR187 raw-tar route (superseded; do not execute)

Authority: [Owner choice, PR186 comment6720571990](https://github.com/tantdna2/SafeShift/pull/186#issuecomment-6720571990),
BASE `f88a152f481691bf678ad721ec6d2f25f95084bf`. This supersedes HTTP retry work
only for TRAIN3763 campaign setup. This change is code/CPU preparation; it does
not upload a dataset, submit Kaggle, run GPU/inference/TEST, create Attempt7,
amend O5, or attest independent audit. Historical Attempts1–6 stay immutable.

## Fixed artifact and Input contract

| Field | Required value |
| --- | --- |
| Python | CPython **3.11.9**, release **20240726**, Linux `x86_64-unknown-linux-gnu` |
| Filename | `cpython-3.11.9+20240726-x86_64-unknown-linux-gnu-install_only.tar.gz` |
| Bytes | **29,713,170**, original archive bytes |
| SHA256 | `f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d` |
| Limits | **6,000** members; **104,857,600** expanded bytes |
| Proposed required Input | `nguynanhtn/safeshift-cpython3119-20240726/1`, **private** |
| Second file | `safeshift_train3763_python.json`, generated from the unchanged lock |
| Source lock | `configs/candidate160/python3119.json`, including original upstream URL |

**Dataset existence, publication, license review and real provider byte verification
are NOT_VERIFIED.** The slug is a fixed target for the Operator to create after
review, not evidence of an existing dataset. No alternate owner/slug/version,
nearby release, changed lock or system Python substitution is allowed. If v1
cannot be created at this identity, stop for a reviewed technical change.

Request/submit metadata requires all original grant-pinned dataset/kernel sources
plus exactly this one Python Dataset and one distinct private per-attempt capsule.
No third extra Input is accepted. The original campaign grant is not rewritten.
The runtime binding is generated by `scripts.train3763_python_input describe`;
it includes `kind`, `ref`, strict `private=true`, and canonical manifest SHA256.
Copy its `binding` object into the existing campaign template as `python_input`,
alongside `technical_revision` and `execution_input`.

`scripts.train3763_campaign.stage` verifies actual private owner/slug metadata,
the exact versioned file listing, and independently downloaded bytes **before
binding/reservation**. It preserves proof in `<handoff>-python-proof`. Submit
repeats that verification in `submission/python-proof` before `PUSH_INTENT` and
the single provider POST. GetKernel reports unversioned owner/slug attachments;
these must match the request exactly. Version is enforced by versioned listing,
explicit SDK `datasetVersionNumber=1` downloads, submitted `/1` metadata and the
worker's exact manifest/byte lock; unversioned metadata alone is not proof.

## Operator publication procedure (after review, not executed in this PR)

Use the separately authorized **Gemini 3.8 Flash Kaggle Operator session** and
the existing pinned official SDK environment (`kaggle==2.2.5`,
`kagglesdk==0.1.38`, `requests==2.34.2`). Authenticate through its existing official
credential mechanism. Never paste credentials into chat or include them in logs,
Git, dataset metadata or receipts. Preserve all local evidence under ignored
`data/processed/`; use a fresh directory for every failed packaging/verification.

1. Confirm redistribution rights before upload: inspect the upstream release's
   license information and retained third-party notices for this exact archive.
   Record the reviewed license identifier accepted by Kaggle and an evidence
   reference. Python-build-standalone bundles components with their own notices;
   do not infer that one generic license covers them all. Keep the archive
   unchanged, including bundled notices. The packaging arguments record the
   Operator's review; they do not automatically establish legal rights. If rights
   or access are unresolved, stop publication.
2. On the trusted Operator machine, download **once** from `lock.url`. The notebook
   never performs this download. Example PowerShell (fresh paths, no retry loop):

   ```powershell
   $pythonLock = Get-Content configs/candidate160/python3119.json -Raw | ConvertFrom-Json
   $pythonWork = 'data/processed/python-input-publication-20261109'
   New-Item -ItemType Directory -Path $pythonWork -ErrorAction Stop
   $pythonName = 'cpython-3.11.9+20240726-x86_64-unknown-linux-gnu-install_only.tar.gz'
   $pythonArchive = Join-Path $pythonWork $pythonName
   Invoke-WebRequest -Uri $pythonLock.url -OutFile $pythonArchive -TimeoutSec 180
   if ((Get-Item -LiteralPath $pythonArchive).Length -ne $pythonLock.size_bytes) { throw 'Wrong length' }
   if ((Get-FileHash -LiteralPath $pythonArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pythonLock.sha256) { throw 'Wrong SHA256' }
   ```

3. Create a separate upload folder with the helper (replace the two review
   placeholders with actual evidence; do not execute with placeholder values):

   ```powershell
   data/processed/operator-venv/Scripts/python.exe -B -m scripts.train3763_python_input prepare --archive $pythonArchive --output "$pythonWork/package" --license-name '<reviewed Kaggle license identifier>' --redistribution-ref '<license/access review evidence reference>'
   ```

   The helper rechecks length/SHA before creating anything, copies original bytes,
   checks them again, and writes the manifest and `local-proof.json`. Kaggle's
   `dataset-metadata.json` is upload metadata; the published v1 must contain only
   the tarball and the manifest. Do not upload ZIP/capsule/other files. Keep the
   compressed tarball as an ordinary file: use `--keep-tabular` and `--dir-mode skip`
   (these control table conversion and local folders, not a guarantee of server
   archive handling). Verify listing/bytes afterward; never replace it with
   extracted members. If Kaggle transforms it, STOP: do not rename/repack the
   locked artifact or proceed with a different layout without technical review.

4. Create private v1 using the reviewed official CLI:

   ```powershell
   data/processed/operator-venv/Scripts/kaggle.exe datasets create -p "$pythonWork/package/dataset" --keep-tabular --dir-mode skip
   ```

   Do **not** pass `--public`; do not update an existing Dataset to v2 to work
   around a failed v1. Confirm the command's supported flags with the installed
   pinned CLI help before operating. Preserve returned dataset identity/version
   and local proof. Upload failure/ambiguity means STOP and read-only reconciliation,
   not another create or version call. Do not create an Attempt or kernel.
5. Independently download v1 through the pinned official API into a **new** proof
   directory and verify the bytes, not uploader metadata:

   ```powershell
   data/processed/operator-venv/Scripts/python.exe -B -m scripts.train3763_python_input verify-provider --output "$pythonWork/provider-proof"
   ```

   PASS requires real metadata `is_private=True`, exact owner/slug, versioned
   listing with exactly two expected files/sizes, explicit v1 download of each,
   manifest identity and archive SHA256/length. The bounded transport allows only
   the audited anonymous GCS download redirect, omits credentials from storage
   requests, preserves partial files, rejects poisoned ZIP wrappers and does not
   retry. File hashes provided by an uploader are not trusted. Report the actual
   `receipt.json` and hashes separately; do not label local fixtures Kaggle PASS.

After publication PASS, provide only the verified binding and provider proof to
the Operator's reviewed campaign context. Planning/submission repeats the proof;
it is not sufficient to manufacture a local `status=PASS` JSON. The original
Input/checkpoint/SDK assets are reused without reupload or new live probing here.

## Notebook setup and failure handling

The campaign launcher invokes a dedicated supervised `--mode setup` child. It
accepts the current `/kaggle/input/datasets/nguynanhtn/<slug>` or legacy
`/kaggle/input/<slug>` layout, with bounded mount discovery and exactly one marker.
Read-only filesystem, parent aliases, exact path/manifest/file inventory, byte
length and SHA are checked before extraction. The inherited safe tar validator
checks all entries before writing files: traversal, duplicate paths, hardlinks,
devices, sparse files, privilege bits, link ancestors and escaping symlinks fail.
Only safe internal symlinks are allowed. The destination is a fresh private
`input-cpython3119` tree inside the unique attempt scratch directory. No Input is
modified; a restart never reuses or overwrites a partial extraction.

The extracted interpreter is actually probed for CPython/Linux/x86_64/required
stdlib/exact 3.11.9 and executable identity. A process-local adapter restricts
inherited interpreter discovery/probes to this binary and its derived venv,
and replaces the legacy Python provider with an unconditional refusal for the
duration of setup. Frozen `train_python.py`, `train_runtime.py`, `bootstrap.py`
and their source locks are unchanged. The inherited setup creates its venv from
that verified binary, copies and rechecks the PBS library, and probes the venv.
**Pinned pip/wheel/package installation remains unchanged and can use network;
only CPython provisioning is fully offline.**

`setup/python-input.json` records PASS/BLOCKED, bytes/hash, extraction/probe and
selected interpreter or structured error. The outer supervisor enforces the
hard setup deadline/log bound, including hash/extraction/probe; disk space is
checked before extraction. Setup failures stop before GPU/weights/model calls
and export the usual FAIL terminal/ZIP/receipts. Preserve partial scratch, logs,
archives and all journal/mirror entries; never turn absence/error into fallback.

## Acceptance and next operational gate

Run `python -B -m unittest discover -s tests -p 'test_internvl3763_python.py' -v`
in the pinned operator environment for real SDK serialization with an offline HTTP
adapter. Run `scripts.qualify_internvl3763` for campaign/launcher/setup/lifecycle
regressions, and `test_internvl3763_notebook.py` for exact committed-source rebuild.
Tests use synthetic archives/mounts/probe/dependency doubles, no model or real image.
Linux covers real process groups and symlink paths; Windows skips those OS cases.

Science SHA256 must remain
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
New runtime/notebook hashes require direct ChatGPT review, independent audit,
separately authorized merge, and **new `AUDIT_V1` + `TECHNICAL_V1`** evidence.
No prior technical attestation or MEASURED result validates this source.

The Owner task reports Attempts1–6 and **21,600/80,000 reserved physical GPU-s**;
the stated future Attempt7 would add **3,600**, reaching **25,200**, leaving
**54,800**. These are supplied planning facts, not a fresh local ledger/provider
audit. Only after review/audit/merge/attestation, actual Input PASS and all original
grant/deadline/resource/history gates may a separately operated Attempt7 be
considered: **one image ordinal1, 1,800s**, never rerun completed ordinal0.
This PR stops at Draft; no Attempt7 is staged and no scientific qualification is claimed.
