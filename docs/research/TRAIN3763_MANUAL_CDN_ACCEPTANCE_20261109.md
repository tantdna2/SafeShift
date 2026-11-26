# Attempt8 CDN companion fix CPU acceptance — 09/11/2026

Scope: [task6739558259](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6739558259),
BASE `519cb16a8f0e66ab03d5a1b0f1ed3981261ca6f6` (PR190 MERGED), branch
`fix/manual-kaggle-cdn`. One external companion fix, CPU synthetic verification
and documentation; no GPU, real inference, live Kaggle operation, production
ledger append or new scientific qualification. See [rollout gates](../TRAIN3763_MANUAL_RECONCILIATION.md).

## Security and compatibility

The SDK-listed ZIP and sidecar must both have the exact expected filename.
The new allowlist accepts only canonical HTTPS
`www.kaggleusercontent.com/kf/<positive-decimal-run>/<URL-safe-token>/<filename>`
without query, plus the existing exact `storage.googleapis.com` origin with a
nonempty signed query and exact filename. Fixtures use a synthetic token in the
Operator-reported path shape; no actual provider token or signed URL is published.
All filenames, bytes and model-independent ZIP payloads in tests are synthetic.

Tests exercise real SDK request serialization and real requests session behavior,
replacing only HTTPAdapter.send. They cover both byte-for-byte ZIP/sidecar
downloads, checksums, exact v1 listing, unsafe hosts/userinfo/ports/fragments,
CDN queries, noncanonical paths/escapes/traversal/run/token/filename, duplicate/
missing/extra outputs, pagination, redirect statuses, connect/read timeouts,
deadline checks, oversized/malformed content lengths, streamed byte limits,
content encoding, changed/truncated bytes and mismatched sidecar SHA256.

Anonymous GET ignores ambient proxies/netrc and sends no Authorization or Cookie.
Its explicit finite timeouts shrink with the shared 240-second budget. The SDK
timeout wrapper is scoped to listing so it cannot overwrite that shrinking GET
timeout. Redirect preparation is disabled as well as redirect following: requests
otherwise reads a redirect body even with allow_redirects=False. Tests make any
read of a non-200 body fail and verify no additional GET/retry occurs.

The integration case feeds the downloaded synthetic ZIP through the existing
collector. Injected download failures retain partials/BLOCKED evidence and leave
both synthetic journals, handoff and original open intent unchanged. Reusing an
evidence directory fails create-only admission. The original raw/trace verifier,
source/commit/authority/native-custody/Input checks remain exercised and unchanged.

## Runtime and custody

The companion remains outside the runtime manifest. All **92 manifest files** and
all **37 tracked notebooks** match BASE byte-for-byte; original Operator HEAD stays
`4407dc939e045d115f4147e2d1d49605ec8b2f7a`. Runtime source SHA256:
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`.
Science SHA256:
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
No runtime, notebook, science/data/split/label/TEST, O5 cap or historical release
changes. The earlier PR190 acceptance remains immutable historical evidence.

The private inventory includes the original campaign, supplied Attempt8 output,
existing blocked collection directory, Owner/tool locators and deployed standalone
tool where present. It contains **519 existing files**, aggregate SHA256
`2888a99d2d6aa0f1ed972f35287415bef01996c5005b95954b94a80addf09715`.
Paths/payloads are private under ignored `data/processed/manual-cdn-fix-proof/`.
Only hashes/counts are published. The final after-inventory exactly equals the
before-inventory: all 519 hashes and the aggregate are unchanged. No old BLOCKED
receipt, partial, journal or tool is overwritten. The Operator checkout and
registered ledger remain in place.

## Final focused CPU validation

CPython **3.11.9**, Windows AMD64 build26200; existing isolated Operator software
only: requests **2.34.2**, urllib3 **2.8.0**, kaggle **2.2.5**, kagglesdk **0.1.38**.
No new dependency install, live connectivity probe, dataset/model read or SDK
credential authentication is needed. No randomness/seed is used.

Final focused command, from the separate tools worktree with the existing pinned
Operator Python executable:

```console
python -B -m unittest discover -s tests -p test_train3763_manual.py -v
```

**36/36 PASS, zero failures/errors/skips**, 124.033 seconds. The private launcher
checks companion/test SHA256 before and after the child process to ensure the
tests ran against the final bytes. An earlier test-fixture failure is retained
privately in `focused-first.log`; the final result supersedes it. Tests do not
qualify a real provider result or constitute independent security audit.

| Final focused artifact | SHA256 |
| --- | --- |
| Companion script | `18a1a250ffeaf22d07065014da934e53e764c54431789b79c0291485e286f526` |
| Focused tests | `6915f2902d31508fe5ee5762d67b371723d69aca12bc928d54b9c37f503a5f70` |
| Private `focused-final.log` | `1d70131a3517e8c6b1d0cf4c2792692f3946060b9247a979971edbe630d85db3` |

Additional process-wide socket guard: **36/36 PASS**, zero failures/errors/skips,
131.014 seconds. Socket construction is forbidden during module loading and the
entire suite. One urllib3 import-time IPv6 capability probe was blocked; after
module loading there were **zero socket construction attempts**, and no socket
was created in either phase. Individual HTTP/collection tests also keep their
own socket guards. Private `focused-no-sockets-final.log` SHA256:
`3358eb0c4915e904af16e45b10efe7d85f17edf57b38e2a1ed58872f63c00bb7`.
The private guard/launcher and JSON receipts remain in the ignored proof directory;
they do not change the tested companion or test bytes.

## Broad unchanged-runtime regression

```console
python -B -m scripts.qualify_internvl3763 --output data/processed/manual-cdn-fix-proof/qualification-final
```

Run from the tools worktree with an independent fresh output directory (the actual
private run used the ignored proof directory alongside that worktree).
**316 tests: 301 PASS, 15 skips, zero failures/errors**, 1025.923 seconds. This
single run includes all 36 final companion tests and the unchanged controller,
execution/campaign/O5, capsule/version, E2E, Python Input, handoff, fulltrain,
grammar and saved-verification regression suites. The launcher confirms final
companion/test hashes at both run start and end. Qualifier `tests.log` SHA256:
`5111408678995cf0900c023b6ad86472362dc9686dad5ee13865bc7536691ee1`.

The 15 skips are nine native CPU torch/transformers/tokenizer dependency/opt-in
cases, four opt-in SDK serialization/inventory cases, one Linux process-group
case and one host symlink case. No companion test is skipped. This task does not
repeat native/cross-OS qualification of unchanged runtime or run the entire
repository's default discovery suite. No live provider or inference PASS is
claimed. `git diff --check` passes; the diff contains only the companion, its
synthetic tests, project state, manual runbook and this acceptance record.

## Activation remains pending

CPU PASS cannot activate this tool. The PR190 release pins old SHA256
`9fa7259b51e7e4caabfd1dfbfdbadd51f3cd569c0fd9f58a70b334150fcc602b`.
New bytes require ChatGPT's direct GitHub review, focused independent Antigravity
security/provenance audit, separately authorized merge, postmerge SHA/parents/tree
verification and one new authentic MANUAL_ADAPTER_V1 release. No self-issued
approval/audit/merge is supplied. After those gates, Operator may collect the same
saved job/ZIP into a fresh directory while retaining every prior failure. The
existing factual Owner attestation remains valid unless facts change. Ordinal2
must not be rerun. Production collection/measurement, official 213-call envelope,
200-image shard release and scientific statuses remain separate and pending.
