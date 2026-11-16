# Deferred TRAIN3763 — CPU acceptance, 12/11/2026

Historical initial-HEAD acceptance below is preserved. The PR196 review fix and
new official reader are qualified separately in
[R1 acceptance](TRAIN3763_DEFERRED_REVIEW_R1_20261112.md); use its current tool hashes.

Author-run CPU evidence, **not independent Antigravity audit or live service
qualification**. BASE `341ab626ff2af7ef79ced0d9c3119794eea4a820`; branch
`feat/train3763-offline-continuation`. Stop at one Draft PR. Review, audit,
separately authorized merge, postmerge verification and route release remain
pending. **NOT READY / NOT ACTIVATED.**

[Machine-readable results, final file hashes and log checksums](evidence/train3763_deferred_20261112/cpu-acceptance.json)
and [baseline inspection](evidence/train3763_deferred_20261112/baseline-inspection.json)
cover this implementation scope. Logs remain ignored under
`data/processed/continuation-validation/` in the implementation worktree.

| Check | Actual result |
| --- | --- |
| New route full suite | 40/40 PASS, zero errors/failures/skips,344.140s |
| Inherited manual collector/campaign/notebook suites | 158 run:156 PASS,2 explicit SDK opt-in skips;848.110s |
| The two skipped SDK fixtures with opt-in enabled | 2/2 PASS, zero skips,8.203s; sockets prohibited |
| Source authority / Owner exporter / disconnect hardening | 10/10 PASS,38.532s |
| Final quarantine / missing output / disk / restart / mirror guards | 6/6 PASS,32.438s |
| Updated provider disconnect and positive exporter orchestration | Targeted1/1 PASS |
| Independent directory guard targeted rerun | 1/1 PASS |
| Python AST and whitespace | PASS; no notebook cells executed |

Coverage includes full synthetic ordinal0..3762 completion through17 remaining
shards and ordered aggregate admission; exact INTENT35 migration; no forged
COLLECTED/SUBMITTED/MEASURED; preserved original bytes; new capsule/job identities;
source/checkpoint/authority drift; finite budget/deadline gates; active-job fence;
missing/corrupt ZIP/sidecar, missing/duplicate ordinals and raw vectors; INVALID
retention without parser rescue; running/failed/partial jobs; restart after
reservation/export/copy; interrupted mirror writes; local disk exhaustion;
GitHub/provider disconnect; final duplicate admission; signed URL redaction.

This is **combined evidence**, not a claim that every full suite was rerun after
the last hardening edit. The clean40-case run was followed by targeted source-
authority, export error redaction, directory guard and failed-artifact quarantine
reruns. Earlier development failures were fixture binding errors; corrected
fixtures passed their reruns. No unresolved failure remains. The inherited
collector uses real pinned SDK serialization with mocked transports; no real
Kaggle request is evidence from those tests.

Windows CPython3.11.9. Existing Operator venv: kaggle2.2.5, kagglesdk0.1.38,
requests2.34.2, urllib3 2.8.0. No dependency installation. New route fixtures
prohibit `socket.socket`; the explicitly online Owner tool is exercised only
with mocked transport/authority/native boundaries. Synthetic receipts never
constitute a genuine provider or native-model PASS.

Reproduce from the implementation checkout:

```powershell
python -B -m unittest discover -s tests -p test_train3763_continuation.py -v
$operatorPython = '../../data/processed/operator-venv/Scripts/python.exe'
& $operatorPython -B -m unittest discover -s tests -p test_train3763_manual.py -v
$env:SAFESHIFT3763_SDK_CPU = '1'
& $operatorPython -B -m unittest discover -s tests -p test_internvl3763_campaign.py -v
& $operatorPython -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
git diff --check
```

The unchanged whole-repository suite was not run; validation was routed to the
affected companion and its inherited dependencies. Linux and actual service/GPU
execution are NOT_RUN. No source/runtime/notebook change requiring new native
inference is introduced by this external-companion PR.

Actual Attempt11 ZIP was read only: full frozen runtime verification, native
claims and sealed history PASS;200 calls/SUCCESS ordinal323..522,8264 members.
Quick verification also checked sealed Input/image/checkpoint/Python receipts,
manifest/CRC/raw custody and original handoff. No provider query, production
collection, measurement, admission or reservation was performed. Journal35 stays
open; journals36/37 do not exist in production. Original grant and O5 extension
remain unchanged.

All92 runtime manifest entries retain source digest
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`;
science digest remains
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
No images/weights/TEST/model execution, upload, external API call by Codex, real
result selection, scientific qualification or production mutation occurred.
