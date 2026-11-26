# Manual Kaggle collection CPU acceptance — 09/11/2026

Scope: [directive6736965547](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6736965547),
BASE `4407dc939e045d115f4147e2d1d49605ec8b2f7a`, branch
`feat/train3763-owner-manual-reconciliation`. This is software verification,
not independent Antigravity audit, live provider observation or execution release.
The [runbook](../TRAIN3763_MANUAL_RECONCILIATION.md) defines exact activation gates.

The separately reviewed companion writes a truthful `COLLECTED` through the
existing mirrored Ledger and preserves `manual.provenance=OWNER_UI_MANUAL`, actual
kernel slug/version/ID, original scheduled slug and all evidence bindings. It
does not patch runtime modules or synthesize API submission events. Original
histories/measure are exercised directly by synthetic integration tests.

## Source and production custody

All **92 runtime manifest files** match BASE byte-for-byte; neither production nor
PREP notebook changed. Runtime source SHA256:
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`.
Science SHA256:
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
The companion/qualifier/tests/docs are outside that manifest. A positive original
notebook admission test and a negative changed-HEAD test establish that equal
source hashes do not waive the original exact merged-commit gate.

The private before/after inventory covers 512 original campaign and supplied-output
files, including both copies of the 26 journals, initialization/registration guards,
BLOCKED handoff and supplied ZIP/extracted evidence. Aggregate SHA256:
`660dbc59f897534d7edfe8d7f73bf47c1d2d76c2f79f92cb200f8d03eba36118`.
No production journal, mirror, handoff, native raw or supplied evidence is changed.
The inventory itself stays ignored under
`data/processed/manual-reconcile-code-20261109/`.

Read-only verification of the saved ZIP with the unchanged runtime verifier and
native-custody verifier PASS: archive SHA256
`3b30e0bcff7f5aa986b411c5a5d85798c7f63b7aa3e5302cc3a6d3c4867c7493`,
105 members, one SUCCESS/native call on ordinal2, 3762 NOT_ATTEMPTED in that job.
Saved TRAIN/checkpoint/Python Input receipts also satisfy the new CPU checker.
This proves saved artifact integrity; provider status/identity/absence/downloads
were not re-observed. No COLLECTED or MEASURED is appended to production.

## CPU validation

Final focused suite: **26/26 PASS**, zero failures/errors/skips, 112.603 seconds
on CPython 3.11.9 / Windows AMD64 build 26200. This run uses final companion and
test bytes; private log `manual-final-v5.log` is retained in the ignored acceptance
directory. Broad unchanged-runtime regression is recorded separately below.
No private logs, raw, archives or credentials are published.

Broad CPU qualifier: **298 cases, 283 PASS, 15 skips, zero failures/errors**,
974.348 seconds. It loaded 18 earlier companion cases before final guard/diagnostic
additions; those are superseded by the final 26-case run above. Its **280 unchanged
runtime cases (265 PASS, 15 skips)** remain regression evidence on the same 92-file
runtime. This is combined evidence, not a claim of one final 306-case run. The
broad receipt's end-of-run companion file hashes are not used as proof of its
run-start companion identity; final focused source/log hashes below are authoritative.
Skips concern native CPU dependencies/opt-in and Linux process supervision or
symlink behavior on Windows; no new companion test was skipped. This task does
not repeat cross-OS/native qualification of unchanged runtime code.

| Final focused evidence | SHA256 |
| --- | --- |
| Companion script | `9fa7259b51e7e4caabfd1dfbfdbadd51f3cd569c0fd9f58a70b334150fcc602b` |
| Focused test source | `ce25bfcc28e5d054a22a17b897fb15968e58e1c7a77d7edcb5d548b3d9f78239` |
| Private final focused log | `bbd0f252d478db4d2dae8a0c1f151c299aa9d34dbf5e9daf71c5659beff439b8` |

Reproduce focused validation from repository root:

```powershell
& data/processed/operator-venv/Scripts/python.exe -B -m unittest discover -s tests -p test_train3763_manual.py -v
& data/processed/operator-venv/Scripts/python.exe -B -m scripts.qualify_internvl3763 --output data/processed/manual-cpu-new-directory
```

The existing isolated environment supplies official Kaggle 2.2.5,
kagglesdk 0.1.38 and requests 2.34.2; no package installation/network probing occurs.
SDK tests use real serialization/transport adapters with synthetic HTTP and a
socket trap. All image/controller fixtures are synthetic CPU records. The
coordinator integration explicitly mocks the native authenticity boundary;
separate tests invoke real archive/raw verification and sealed native claims.
Neither scripted telemetry nor CPU vectors establish GPU/native qualification.

Coverage includes authenticated Owner/tool/audit/merged-source binding, wrong
kernel/version/private/source/metadata/accelerator/Input, absent scheduled slug,
unknown/replayed provider job, changed inventory/status during collection,
archive SHA/sidecar/CRC/member/raw and native intent claims, source-bound unchanged
measure and resume, immutable BLOCKED handoff, prior ordinal0/1 plus manual2 →
ordinal3 planning, no refunds, reservation drift, double collection, process lock,
ledger divergence/loss/torn mirror, wrong evidence directory and provider-copy
tampering after download. The final source/science digests are regression sentinels.

## Still blocked for operations

ChatGPT direct GitHub review, independent Antigravity audit, separately authorized
merge and verified collection-tool attestation remain pending. The Operator must
retain the original clean approved checkout/canonical ledger and obtain authentic
Owner factual attestation plus actual pinned provider proof. Only then may the
existing ZIP become COLLECTED and feed the unchanged Ledger.measure. The task
does not create those authentic records or treat the reported213 estimate as an
official measurement. A new specific 200-image preparation release remains separate.

No Kaggle submit/upload, GPU/model weights, real-image inference, TRAIN/TEST data
modification, label/parser/HNLO/metric/science change, refund, scientific selection
or qualification occurs. The task ends at one Draft PR; it does not run the
independent audit or merge itself.
