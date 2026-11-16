# PR196 R1 — official reader acceptance, 12/11/2026

Addresses [ChatGPT review6817877168](https://github.com/tantdna2/SafeShift/pull/196#issuecomment-6817877168)
against HEAD `12475113e3c0b65269ec2c6f6257da3fe62f32eb`, in the same branch/session
and Draft PR196. [Review snapshot](evidence/train3763_deferred_review_r1_20261112/review.md)
and [CPU/hash receipt](evidence/train3763_deferred_review_r1_20261112/cpu-acceptance.json)
record the exact scope. This is Codex-authored CPU evidence, not independent
Antigravity audit or new GitHub approval. **NOT READY FOR MERGE OR EXECUTION.**

The blocker was a missing authoritative downstream path: legacy COLLECTED/INTENT
readers ignore deferred records even after a final certificate. The fix adds
`official-report`, a read-only bridge over the sealed new-route event and custody.
It shares admission's exact Owner/reviewer/native proof validator, independently
recomputes reservations from original and deferred intents, and emits a versioned
3763-row observation/lineage/attempt/resource handoff. A final event's presence
alone can no longer make operational status claim official results. No historical
rewrite, fake COLLECTED/MEASURED, native runtime/notebook change, GT join, new
metric or scientific permission.

| Run | Result |
| --- | --- |
| New official reader/provider suite | 11/11 PASS, zero skips/errors/failures;216.204s elapsed |
| Existing continuation suite after the fix | 40/40 PASS, zero skips/errors/failures;380.610s elapsed |
| Inherited manual/campaign/notebook, including SDK opt-in fixtures | 158/158 PASS, zero skips/errors/failures;868.109s elapsed |
| Final reservation-tamper and full official handoff rerun | 2/2 PASS;111.485s elapsed |

209 distinct tests covered. Elapsed values include runner/import overhead; the
raw unittest logs can differ slightly. Earlier new-fixture failures (identical
empty ZIPs colliding in the SHA map, and mutating an admission-bound registration
while arranging a mock) were corrected in fixture construction. Subsequent clean
runs above leave no unresolved failure. The final two tests followed the additive
original-cap/O5-reference output fields and independent budget-tamper assertion;
this is combined evidence rather than a claim of rerunning every suite after
that last small edit. Logs and initial failures are preserved in ignored
`data/processed/continuation-review-r1/` under the implementation worktree.

The full synthetic campaign has11 original reservations and17 deferred jobs:
28 jobs,3768 calls and316800 physical GPU-seconds reserved. It produces3763
observations including one INVALID, retains the3 pre-submit aborts and2 historical
FAIL jobs, and returns25 executed histories. The bridge reports3763 actual native
calls from the synthetic ZIP telemetry while legacy APIs remain at323 results,
528 calls/11 jobs/72000 GPU-seconds. These are **fixture assertions**, not new real
campaign results or measurements. GPU billing remains NOT_OBSERVED.

Adversarial cases include complete local outputs without final release; wrong
Owner/admission principals and edited/missing exported comments; a mutated final
report even with matching mirrors; lost/changed mirrored ZIP; authenticated
account records with false resource facts; independent budget-total tampering;
nonfinite/missing telemetry; delayed last native/provider failure; and unchanged
legacy status separation. Native authenticity/qualification is an explicit test
boundary, never a claim that synthetic vectors or model outputs are genuine.

The Owner verifier orchestration tests exercise all25 job/version/capsule/output
boundaries (7 historical +18 from Attempt11 onward), including the real-world
distinct-slug shape for Attempt8. They assert50 before/after provider observations,
25 capsule checks and25 ZIP/sidecar downloads, fresh GitHub reads replacing a
cached response, and preservation of early proofs when the last provider fails.
Transport is mocked and every socket construction is prohibited; genuine live
provider verification still belongs to the Owner after review/audit/merge/release.
Account authorship on GitHub is not proof of which human or app clicked `gh`.

Reproduce from this worktree with existing CPython3.11.9/Operator venv:

```powershell
python -B -m unittest discover -s tests -p test_train3763_results.py -v
python -B -m unittest discover -s tests -p test_train3763_continuation.py -v
$operatorPython = '../../data/processed/operator-venv/Scripts/python.exe'
$env:SAFESHIFT3763_SDK_CPU = '1'
& $operatorPython -B -m unittest discover -s tests -p test_train3763_manual.py -v
& $operatorPython -B -m unittest discover -s tests -p test_internvl3763_campaign.py -v
& $operatorPython -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
git diff --check
```

SDK pins: kaggle2.2.5, kagglesdk0.1.38, requests2.34.2, urllib3 2.8.0. No installs.
Linux, whole-repository suite, real Kaggle API/GPU/inference/TEST and production
mutation are NOT_RUN. Native92-file source SHA remains
`f062f170c38f2f70c21c6f7462d9408e5a5ea6862b923a40cf9e58b75489239d`;
science SHA remains
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.
Changed tools, including the reader, need a fresh exact four-file release after
direct ChatGPT re-review, independent Antigravity audit and authorized merge.
