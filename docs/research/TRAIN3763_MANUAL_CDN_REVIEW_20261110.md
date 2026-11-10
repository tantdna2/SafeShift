# PR191 real CDN token and security self-review — 10/11/2026

Continuation on the same branch `fix/manual-kaggle-cdn` and [Draft PR191](https://github.com/tantdna2/SafeShift/pull/191),
BASE `519cb16a8f0e66ab03d5a1b0f1ed3981261ca6f6`, initial PR head
`fad414c01dc18e63b7848a121678e9734213a834`. The Owner's direct continuation permits
read-only inspection/download of the existing Attempt8 output and CPU tests;
GPU, inference, Kaggle submit, production COLLECTED/MEASURED and self-merge remain
forbidden. This is the author's self-review and technical evidence, not the
required independent security/provenance audit. The [09/11 evidence](TRAIN3763_MANUAL_CDN_ACCEPTANCE_20261109.md)
is retained as a historical snapshot; its simple token fixture was insufficient.

## Observed defect and fix

A direct official SDK `ListKernelSessionOutput` request pinned to the existing
Owner job/version1 observed the exact HTTPS origin `www.kaggleusercontent.com`,
`/kf/<positive-decimal-run>/<token>/<exact-original-filename>`, no query/fragment.
Both ZIP and sidecar tokens had **five dot-separated fields**, with field lengths
**47, 0, 22, 640, 22** (735 characters total). No real token, decoded payload or
signed URL is published. Raw listing stays in the ignored private proof directory.

The old PR191 validator rejects that actual shape. The final validator admits the
observed `<header>..<iv>.<ciphertext>.<tag>` shape, each nonempty field containing
only ASCII letters/digits/`_`/`-`, and retains simple opaque tokens. Dots remain
inside one path segment. It does not decode or validate token claims; original
authority, exact provider origin/path/name and archive SHA verification remain the
trust gates. Unobserved dotted forms, nonempty second field, malformed/empty
fields, escapes, slashes, `=`/`;`, traversal, queries, fragments, userinfo, ports
and lookalike hosts stay blocked. GCS retains its exact origin, signed query and
filename checks. Synthetic fixtures now reproduce the observed dotted structure.

## Additional security/completeness findings

- Idle read timeouts plus checks between 64KiB chunks can stall on a peer that
  continuously trickles bytes. A shared 240-second deadline watchdog now shuts
  down registered TLS sockets during response headers/body. Normal certificate
  verification and bounded connect/read waits remain. Expired connection
  completion is rejected. The per-session pool registry is private; timer work
  is cancelled/joined on every exit. The OS resolver is not force-terminated by
  this watchdog; late results never pass admission.
- SDK verbose output can print response JSON with bearer URLs; urllib3 debug/
  warning output can also print paths. The companion disables pinned SDK verbose
  output, transport logging and HTTP debug printing during network access, then
  restores logging state, including exceptions and timer-start failure.
- Declared Content-Length must equal received bytes when present, in addition
  to stream caps and archive/sidecar SHA checks. Missing/oversized provider logs,
  inadequate disk, malformed listings and unsafe sidecar URLs stop before GET.
- Requests redirect preparation remains disabled, preventing unbounded redirect
  body reads even with allow_redirects=False. Every retained partial uses exclusive
  creation/fsync. Failure cannot reach ledger append; no automatic retry occurs.
- Runbook examples now use distinct PR191 tool, release-locator and evidence
  paths. The earlier evidence path already contains BLOCKED and must not be reused
  or cleared. Old tools/locators/partials and historical acceptance stay intact.

## Direct read-only proof with the real saved Attempt8 result

Final companion transport downloaded into a new private directory, with no calls
to `reconcile`, `Ledger.append` or `measure`:

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Original Attempt8 ZIP | 5646071 | `3b30e0bcff7f5aa986b411c5a5d85798c7f63b7aa3e5302cc3a6d3c4867c7493` |
| ZIP sidecar | 92 | `020215601722fef2ac6a92721bc8a79a92de08f4544c0566022cd127462b2486` |
| Provider log from pinned SDK listing | 2315 | `70c555ef63aa8313172790bcf4bd103a68dbc6019681f7da7e7970e9aacf27ed` |

Download plus bundle replay took 6.032 seconds on the final companion bytes.
The original unchanged `verify_bundle`, native-custody and Input-receipt checks
PASS: saved raw/trace/claims, 3763 TRAIN receipt, original checkpoint source/weights
stream receipts and original Python transport. One native call exists **inside
the historical bundle**; new model/image calls, GPU jobs and submits are **zero**.
This does not claim fresh remote hardware attestation, a new dataset/weights
byte scan, production collection/measurement or new science qualification.

Loading the new companion with imports from the original approved Operator
checkout also passes `approved_source`, authenticated existing grant/execution/
O5 bindings, Owner factual attestation and immutable BLOCKED handoff checks.
The original source HEAD remains `4407dc939e045d115f4147e2d1d49605ec8b2f7a`;
there are **26 journals and 26 mirrored copies** with unchanged open Attempt8
INTENT. Original grant SHA256:
`1f672fb601006c7898be271e59f74fb341d7311fc60794a9ed6a332f430395c6`.
Original notebook SHA256:
`c2e574c132c1305efccde569bac63c027eeafe8814285ebaf092701cb3f033e7`.
The new collection-tool release remains pending; no approval is fabricated.

## Preserved source and custody

All **92 runtime manifest files** and **37 tracked notebooks** remain identical
to BASE. Runtime source SHA256:
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`.
Science SHA256:
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
No TRAIN ID/data/split/label, checkpoint, science, rights/cap or runtime changes.
The private inventory covers **519 original production/evidence files**, including
all journals/mirrors, old BLOCKED/partial files, locators and old deployed tool.
Its original aggregate SHA256 is
`2888a99d2d6aa0f1ed972f35287415bef01996c5005b95954b94a80addf09715`.
Final before/after comparison confirms every one of the 519 hashes and the
aggregate unchanged. The final public diff also contains zero real URLs/tokens
from the private provider listing. New probes/downloads/tests are isolated under ignored
`data/processed/manual-cdn-review-20261110/` and existing proof storage; no old
artifact is overwritten or deleted. Raw URLs/logs/archives remain private.

## Final focused CPU evidence

Environment retained from the Operator venv: CPython3.11.9 / Windows AMD64
build26200, kaggle2.2.5, kagglesdk0.1.38, requests2.34.2 and installed urllib3
2.8.0. No dependency installation/change or model/weights load. Transport behavior
is verified on those installed versions; later dependency changes require new
verification. Reproduce the committed focused tests from the tools checkout:

```console
python -B -m unittest discover -s tests -p test_train3763_manual.py -v
```

The final complete suite under an additional process-wide socket-construction
guard passes **44/44, zero failures/errors/skips**, 116.202 seconds. No socket is
created; zero construction attempts occur during the tests. One urllib3 import
IPv6 capability probe is separately blocked before test execution. Real-network
proof above is distinct from these synthetic CPU tests. The private launcher
verifies companion/test hashes before and after the suite. Earlier harness/test
placement errors and every earlier probe/download remain retained separately;
no old evidence is cleared to obtain PASS.

Coverage includes observed-length dotted tokens, malformed/unsafe URLs, GCS
regression, real SDK/requests serialization over HTTP doubles, anonymous TLS
verification, ZIP/sidecar/log completion, listing/log/disk/byte bounds, redirect
body rejection, connect/read timeouts, deadline/late connection interruption,
watchdog cleanup/global pool isolation, verbose/debug token suppression and
logging restoration. Original collection integration continues to verify raw/
trace/authority/lineage, no duplicate append, partial preservation and both
synthetic journal/mirror copies unchanged on failures.

| Final artifact | SHA256 |
| --- | --- |
| Companion | `5df9d3ffae01a007e94521d322622473868b3b951189c0f1b7d96bbe40e787be` |
| Focused test source | `744e3831065c3abb9e18c3791b5b698418d6311b630a340ee41cb278fa19b445` |
| Private focused socket-guard log | `38e49759007b5349df8bf31ca1233b57e4642acc17158f62def0ecc0f11f070e` |
| Private real download/bundle receipt | `c716e6c059d0c3069e2237944793ff11cc6144d2d43c79481c5805894fda125b` |
| Private original-source/authority compatibility receipt | `e3b4857302cde4860351378499be5af3fc3500320e423839963420db39e98e10` |

## Final broad CPU regression

```powershell
$env:SAFESHIFT3763_SDK_CPU = '1'
python -B -m scripts.qualify_internvl3763 --output data/processed/manual-cdn-review-20261110/qualification-final
```

Use a fresh output directory from the tools checkout; the actual run kept its
private output alongside the worktree. **324 tests: 313 PASS, 11 skips, zero
failures/errors**, 912.585 seconds. All final 44 companion cases and the opt-in
SDK serialization/inventory cases execute without skips. Source/test SHA checks
at run start/end match the table and the real downloaded-result proof.
Qualifier `tests.log` SHA256:
`744de49f0ded88cbbbc7aea64ef41e7131699ae2b6824a3a0a94f8a9e332e935`.

The 11 skips are six native CPU torch/transformers opt-in cases, three native
grammar E2E dependency cases, Linux process supervision and host symlink support.
The unchanged runtime's native/cross-OS qualification is not repeated, nor is the
entire repository's default discovery. No failure/error or unresolved observed
collector defect remains in this scope. `git diff --check` passes. Technical
PASS does not waive authentic source/provider/history/release gates or replace
independent review/audit.

## Remaining rollout gates

Direct ChatGPT review of final GitHub HEAD, a short independent security/provenance
audit (dotted-token allowlist, TLS watchdog, diagnostics, custody), separate merge
permission and postmerge identity verification must precede a **new authentic
MANUAL_ADAPTER_V1 release**. Old PR190 release bytes/locator cannot authorize this
tool. No source lock/runtime migration, ordinal2 rerun, official 213-call envelope,
200-image shard release or scientific upgrade follows from this technical PASS.
Provider availability, URL expiry and actual release/identity/history checks can
still stop later collection safely; retain evidence and reconcile read-only.
