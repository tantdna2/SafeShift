# Issue202 MiniCPM offline continuation — CPU acceptance

## PR203 post-audit correction — review6943496144

[ChatGPT changes-required](https://github.com/tantdna2/SafeShift/pull/203#issuecomment-6943496144)
identified a real defect in the original final-positive fixture and predicate:
two distinct comment IDs were accepted from the same Owner account. The
historical execution counts below remain execution evidence, **not evidence of
independent account separation**. The corrected code rejects Owner allowlists
(including case variants), missing/invalid/reused stable user IDs, Owner login
aliases and unauthorized reviewers; both reconcile and official-report use
the same identity check. The positive fixture uses only a synthetic distinct
reviewer, and full3763 verifies self-admission rejection before independent
admission succeeds.

Focused regressions exercise missing/changed user/id/login/body hash, wrong
comment/issue/locator, rehashed wrong manifest/report/Owner bindings, consistent
but self-approved final documents, changed grant reviewer lists without new
subject approvals, and the unchanged provider gate. Owner-authenticated GitHub
export custody remains a trust boundary: unsigned local JSON cannot prove its
own origin. No real GitHub reviewer identity or authority is fabricated.

The corrected independent Antigravity audit receipt belongs to auditor session
`e5a463b2-f0ca-4bd8-9d46-19a1d4875c63`, via Owner after exact-HEAD review. Codex
does not certify that audit or its five ad-hoc adversarial cases. The per-ID
OS matrix supplied here is for Codex's own hash-bound logs; the auditor must
provide its own identifiers/logs/hashes or correct unsupported numeric claims.
No audit-only case is invented or added to Codex PASS counts.

Corrected source and test log hashes are recorded below after test completion.

## Historical initial delivery at acae1fa

**SOURCE CANDIDATE ONLY.** This is software evidence using synthetic IDs/raw,
temporary signing keys and mock provider transports. No authentic release,
production journal write, notebook publication, Kaggle/GPU/inference/TEST,
independent audit or merge was performed.

Base: `e713d56d62a5a649a2078f2c2376fde6d025b978` (PR201 merged), re-fetched
before delivery and still main. Branch: `codex/issue202-minicpm-offline-chain`.
Tested code/tools commit: `6d8ea362b93fca415480870cbde515a17d401b5e`.
Subsequent delivery-only documentation does not change these runtime/tool bytes.

| Identity | SHA256 |
| --- | --- |
| Runtime manifest, 85 files | `e3620934ef1662886bb723ac47d13accdfda4bc5362d6e5359112b79390e41ee` |
| Canonical manifest of 11 Operator tools | `88c6939d03add8456e352ac676b3193eb418d33ccc661a46c587d5ad381ecbac` |

`tools_manifest()` and `tool_blobs()` recompute every individual tool SHA256 and
Git blob ID. The delegation locks both; GitHub runtime/reviewed/merged trees must
match. Tools remain outside the Kaggle payload, whose release verifier uses the
authenticated blob IDs. A regression loads the complete authority graph from a
runtime-only checkout with no scripts directory.

## Commands and environments

Windows: CPython3.11.9, Windows10 build26200 (OS version string), existing
`data/processed/operator-venv/Scripts/python.exe`, kaggle2.2.5/kagglesdk0.1.38.
Nothing was installed or updated. Socket connect/create_connection were replaced
with a failure guard before loading any suite. The actual pinned SDK's serializer
and HTTP-adapter fixtures run with synthetic transport; no account authentication
or provider call was performed.

Windows command was a `python -B -` unittest loader with `sys.path.insert(0,
"tests")`, `unittest.defaultTestLoader.loadTestsFromName()` for these modules,
and `TextTestRunner(verbosity=2)`:

```text
test_minicpm_offline_continuation
test_minicpm_offline_notebook
test_minicpm_v5_incident
test_minicpm_v44_incident
test_minicpm_v6_collection
test_minicpm_fulltrain_memory
test_minicpm_fulltrain_ui
test_minicpm_run1_recovery
test_minicpm_execution_boundaries
test_minicpm_execution_transport
test_minicpm_ui_transport
```

Linux: WSL2 kernel6.18.33.2/x86_64, CPython3.14.4, OpenSSL3.5.5. The exact Git
archive of the tested commit was extracted into a fresh owned temporary folder;
setup used `sh -ec` to stop on any extraction/cwd failure. This stdlib CPU test
environment is not a verification of Kaggle's pinned worker ABI/model fit.

```console
python3 -B -m unittest discover -s tests -p test_minicpm_offline_continuation.py -v
python3 -B -m unittest discover -s tests -p test_minicpm_fulltrain_memory.py -v
python3 -B -m unittest discover -s tests -p test_minicpm_v6_collection.py -v
PYTHONPATH=tests python3 -B -m unittest test_minicpm_run1_recovery.LiveSupervisionTests -v
```

Five additional Windows `ExecutionTests` cases were loaded by exact name from
`test_minicpm_fulltrain_execution`: load-overhead before first sample,
adaptive storage, adaptive export/time, MiniCPM-only sizing, and signed
caps/quota/deadline/source drift. They are separate from the 86-case suite.

Synthetic bytes and statuses are deterministic; RSA fixture keys use OpenSSL
entropy in temporary directories and are never production keys or committed.
The large3763 fixture runs the real controller/export/import/C1/claims/mirrors
across an initial1000 and tail2763. Those are fixture caps, not product defaults.
Every distinct ZIP pair is fully replayed once. Repeated state inspections in
that one large fixture reuse its exact replay result only after hashing both
archives/sidecars, request/ticket, proof and package; **production has no cache**.
Small/adversarial cases execute the full verifier on every call.

## Results

**91 distinct test IDs PASS on at least one platform; no unresolved failures or
errors, and no unexercised skip.** Windows86-case suite:81 PASS/5 Linux-only SKIP;
Windows adaptive subset:5 PASS. Linux:15 offline +13 memory +4 collection +1
forwarding PASS. These runs overlap; do not sum them into a distinct PASS count.
The full3763 case also passes official admission, duplicate rejection and a
tampered final mirror rejection. Test execution did not call any real provider.

| Acceptance log in `data/processed/issue202-cpu/` | SHA256 |
| --- | --- |
| `windows-6d8ea36-pinned-regression.log` | `0ba7ba2334bb40e58f6d4c45ad21cc847b7f1fbda7e400e8341ef207a69f14e0` |
| `windows-6d8ea36-adaptive.log` | `d473755302dc036d277be36b9fc9fe6744fb3373f24909d3a16575dbe557136a` |
| `linux-6d8ea36-offline.log` | `0f78bd560c06055ea6a7ec610b23133d0a27c95a3052a1c9fc4ff49c088113f0` |
| `linux-6d8ea36-memory.log` | `56ce64c56c16ed13ee7f6b817cbceb5ff601cf4a936909b412bd01d8dc9932eb` |
| `linux-6d8ea36-collection.log` | `1241c94a79074898a947aea9ae483c15231d2dc50c2af51cf128317dd5473d65` |
| `linux-6d8ea36-forwarding.log` | `7531a0a632f31f14d42e1601863e824ab1aee15632accf5f6c0ed220884b91d0` |

Git source archive `committed-6d8ea36.tar`: SHA256
`0aa1396e85306f04ad8b5f9e10bf1621caf97381a9ff72eeef8d3013c057085a`.
The focused suites above were used; full repository discovery was not run.

Local originals are under `data/processed/issue202-cpu/`, outside Git. Early
development failures (fixture model seam/record ordinal/checksum assumptions),
source-drift detection while edits were still underway, setup failures and
interrupted snapshot runs are not counted as PASS. They remain separate from
the fixed-source acceptance logs. No repeated test is added to a combined PASS
total; cross-platform overlap must not be summed.

## What is covered

- A new explicit release marker/delegation, inherited V4 rights/V5 closures,
  exact source/tool trees, real RSA3072 signatures, forged/expired/replayed
  tickets, signed first-job cap and unchanged held reservations.
- One active job, single-owner OS lock, mirrored create-only events/proofs,
  torn mirror/original append detection, crash after reservation and exact
  export recovery without another reservation or partial-file overwrite.
- Actual scripted controller/C1/native call/generate claims, CRC/SHA/manifest,
  sealed ancestors/source, SUCCESS/INVALID/pending, raw mutation, missing or
  malformed Output/capsule/sidecar/proof and STOP with no official result.
- All3763 ordinals across jobs and tail; no duplicate/missing/skipped ID;
  MiniCPM-only timing/finite quota/expiry/caps, adaptive time/storage guards.
- Every final job/source/version/notebook/five-Input identity is visited by
  mock provider orchestration; all capsule bytes (including ZIP ancestors),
  both Output pairs and sidecars are compared. Foreign/version2/duplicate or
  missing job proof fails. Pinned SDK primitives have independent transport
  fixtures. Real provider verification remains Owner-only and NOT_RUN here.
- A single final admission, compact hash certificate with complete mirrored
  documents, strict Owner/reviewer records, duplicate admission and final
  document tamper rejection, official rows/history/lineage/budget only after
  admission; no metric/GT join or scientific qualification.
- PR201 memory/supervision/native/config/parser and historical notebook bytes
  compared to main exactly. RAM floor16384MiB, scoped owned-runtime advice,
  cgroup/OOM diagnostics, POSIX process groups and V6 collection receipts stay.

## Changed files

| File | Purpose |
| --- | --- |
| `safeshift/fulltrain/minicpm_offline.py` | Delegation, Owner observation schema, signed bounded tickets and sizing |
| `safeshift/fulltrain/minicpm_release.py` | Explicit new marker/authority/tree/ticket dispatch |
| `safeshift/fulltrain/minicpm_ui.py` | Full finite serial ancestry capacity |
| `scripts/minicpm_offline_continuation.py` | Offline journal, staging/custody/recovery, final admission and reader |
| `scripts/owner_verify_minicpm_offline.py` | Owner-only genuine authority export/final provider verifier |
| `scripts/minicpm_fulltrain_operator.py` | Fence legacy writers after offline admission |
| `scripts/generate_minicpm_fulltrain_notebook.py` | Deterministic V7 builder over unchanged native/RAM entrypoint |
| `tests/test_minicpm_offline_continuation.py` | Synthetic signed/offline/final/adversarial regression |
| `tests/test_minicpm_offline_notebook.py` | Exact builder and protected PR201 bytes |
| `docs/MINICPM_OFFLINE_CONTINUATION.md` | Vietnamese Owner/Antigravity runbook and release schema |
| `docs/ARCHITECTURE.md` | Narrow context routing |
| `docs/PROJECT_STATE.md` | Current delivery and honest activation blockers |
| `docs/research/MINICPM_OFFLINE_ACCEPTANCE_20261117.md` | This source/test evidence |

## Remaining gates

Actual MiniCPM Operator UUID/acknowledgment and existing private-key/host custody
remain unconfirmed. The excluded InternVL Attempt4 session is never substituted.
Direct ChatGPT HEAD review, a new independent Antigravity audit, separately
authorized merge/postmerge and an authentic exact-source offline release with
initial cap/expiry precede activation. Owner checks fresh real quota/Inputs
before every Run and personally executes the final provider verifier/admission
exports. No self-issued authority, budget change, refund or V5 ticket reuse.

`KAGGLE_VENV_LAYOUT_UNVERIFIED`; `FAIL_CLOSED_BUT_OWNER_RUN_CAN_STILL_ABORT`.
Fail-closed can still spend provider quota. Increasing ancestry/document custody
needs adequate Owner RAM/disk and existing runtime/archive limits; insufficient
resources STOP instead of pruning history. Final-source Kaggle load/inference/
long-run completion and independent scientific qualification are NOT_RUN.
