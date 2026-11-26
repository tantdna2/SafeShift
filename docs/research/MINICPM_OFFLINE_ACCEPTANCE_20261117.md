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

[Original Codex per-test OS/log matrix](MINICPM_OFFLINE_TEST_MATRIX_20261117.csv)
contains exactly91 IDs, generated from the six historical logs and SHA256 listed
below. `NOT_RUN` is not PASS; platform overlap and unittest subTests are never
counted as additional test IDs. This supports the author's historical count
only. The independently submitted audit used different suite groupings and
must be reconciled by its author with its own signed evidence, including the
five ad-hoc cases identified in the review.

Matrix reproduction from the original local logs (after checking their SHA256):

```python
import csv, re
from pathlib import Path
root = Path('data/processed/issue202-cpu')
logs = {
    'windows_regression': 'windows-6d8ea36-pinned-regression.log',
    'windows_adaptive': 'windows-6d8ea36-adaptive.log',
    'linux_offline': 'linux-6d8ea36-offline.log',
    'linux_memory': 'linux-6d8ea36-memory.log',
    'linux_collection': 'linux-6d8ea36-collection.log',
    'linux_forwarding': 'linux-6d8ea36-forwarding.log',
}
rows = {}
for column, name in logs.items():
    for line in (root / name).read_text(encoding='utf-8').splitlines():
        match = re.match(r'test_\w+ \(([^)]+)\) \.\.\. (ok|skipped.*)$', line)
        if match:
            rows.setdefault(match[1], {})[column] = 'PASS' if match[2] == 'ok' else 'SKIP'
assert len(rows) == 91 and all('PASS' in row.values() for row in rows.values())
with (root / 'reproduced-original-matrix.csv').open('x', newline='', encoding='utf-8') as out:
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['test_id', *logs, 'any_platform_pass'])
    for test_id, statuses in sorted(rows.items()):
        writer.writerow([test_id, *[statuses.get(key, 'NOT_RUN') for key in logs], 'PASS'])
```

Corrected tested code/tools commit:
`babbac8e8b7858337417a74b9f25539a4e7f03a6`. Subsequent changes are documentation
and per-test matrices only. Runtime85-file SHA256:
`32aabc133f7ebb9638863207398ab8c905f00bf75ca99d67aa19becc0ba0fd85`;
11-tool manifest SHA256:
`6accf28ddef2635c71eb0c5538ec04fe88ccb6e1a3fb16c29fd3e8e1dde47924`.

**Corrected source:97 distinct test IDs PASS**, no unresolved failures/errors
and no unexercised skips. Windows92-case suite:87 PASS/5 Linux-only SKIP;
separate Windows adaptive5 PASS. Linux21 offline +13 memory +4 collection
+1 forwarding PASS. Platform overlap and subTests are not summed.
[Corrected per-ID OS/log matrix](MINICPM_OFFLINE_REVIEWFIX_TEST_MATRIX_20261117.csv)
includes the six new identity/admission tests. Full3763 is a single test ID;
it rejects same-Owner admission with different comment IDs and leaves official
reading BLOCKED, then admits the separately authorized mock reviewer and
verifies official3763 rows. All source allowlist/record/hash/native/ZIP/mirror
regressions complete on the fixed code above.

Environments and module commands are the same as the historical commands below:
Windows CPython3.11.9, pinned kaggle2.2.5/kagglesdk0.1.38 with socket connections
forbidden; Linux WSL2/x86_64/CPython3.14.4 from an exact Git source archive.
The corrected Windows module loader discovers six additional methods in
`FinalAdmissionIdentityTests`; no new production tool is needed for accounting.
To reproduce the corrected matrix, use the matrix snippet above with these six
log names and require97 distinct IDs instead of91.

| Corrected log in `data/processed/issue202-cpu/` | SHA256 |
| --- | --- |
| `reviewer-fix-windows-regression.log` | `5c69d223d0b1d9680f068dc55fb4a9dd41bab1d3a571b046c7b1cd6f83d80f5b` |
| `reviewer-fix-windows-adaptive.log` | `45a8030da027bbab412604b8743232a87ce8f1e88370127259b7ce3a1d14b046` |
| `reviewer-fix-linux-offline.log` | `28a9d4b2a0a14b3ab2fc0979b3abbd529ec5da2277c5268d171f8d546ca0e779` |
| `reviewer-fix-linux-memory.log` | `7bf9e525eec3791ef08868cce3dda095e7294c26ee29b5c28189cf939d5186b4` |
| `reviewer-fix-linux-collection.log` | `a65ec7ba98fa6f6628acb8b8b02a2a8f9508477cf90a23081866d620c3c80e77` |
| `reviewer-fix-linux-forwarding.log` | `219609f9c96445044fd38795de98ac44ee44f84bb977f29cc08fc24902d12dc6` |

This is Codex author evidence, not independent CI/audit or an authentic execution
grant. The same Antigravity auditor must still recheck the corrected exact HEAD
and own its signed accounting addendum; its five ad-hoc cases remain outside
these97 IDs until the auditor supplies their own reproducible evidence.

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
