# MiniCPM Run1 recovery V3 — CPU acceptance, 16/11/2026

Owner source: [directive6914854993](https://github.com/tantdna2/SafeShift/pull/198#issuecomment-6914854993).
BASE merged PR198: `507e9817b91054fa7af324c6a915c35d56b5acf1`.
Code/test commit: `b788f3f09d55d59facabbbabd477bd5bc7b1e9b6`.
Runtime80-file SHA256:
`dfc3a043e7b65f68726b9dfc7e0368c9a4f38f2ef4d5667f92bbd62ffd23df0d`.
Subsequent delivery changes are documents/evidence only.

Machine receipts and complete accepted CPU logs are in
[the evidence directory](evidence/minicpm_run1_recovery_20261116/index.json).
No real data/raw, model weights, credentials or private signing keys are included.

| Accepted check | Result | Boundary |
| --- | --- | --- |
| Recovery V3, existing pinned Windows operator venv | 16 run,15 PASS,1 Linux-only SKIP | All genuine RSA3072 signatures/journal/claim/history/C1/ZIP code; provider/model/Owner IO are synthetic doubles |
| Recovery V3, Linux exact Git archive on native temporary filesystem | 16 run,15 PASS,1 pinned-SDK SKIP | Includes real process guardian/streaming; SDK-only positive handoff is covered in Windows |
| Existing focused regression, pinned Windows venv | 67/67 PASS | V2 execution (excluding the full3763 stress case), child CLI, real SDK transport doubles, original Inputs, UI, release dossier and historical notebook reproduction |
| V3 exact-ref notebook reproduction | PASS | All80 runtime bytes Git-pinned, both code cells compile, explicit V3 mode; synthetic locator/capsule, not a releasable production notebook |
| Preservation | PASS | All three original journal heads/mirrors unchanged; no tracked historical notebook/config/CandidateBackend/pilot changes; zero production events/uploads/submissions |

The recovery tests exercise aggregate86400 versus72000, no refund/reset/fourth
campaign, authentic new-source approval graph and original grants, tampered
signatures, expiry, ordered child claims, five nested mount bindings, native/
partial/unknown failures, source/ticket/TRAIN ID/SHA mismatch, ambiguous POST and
duplicate submit. The actual V3 model.generate observation is checked after image
preparation; stage/load-only and stderr logs cannot establish native start.
The live-process test proves a receipt is forwarded before the child exits while
the complete original log remains. The synthetic end-to-end path stages/publishes,
submits once, observes a positive still-RUNNING handoff and never cancels; another
test collects real synthetic ZIP pairs in the same journal, retains INVALID and
stages only remaining ordinals with cumulative budgets and serial5.

Reproduce recovery tests:

```powershell
data/processed/operator-venv/Scripts/python.exe -B -m unittest discover -s tests -p test_minicpm_run1_recovery.py -v
```

Linux acceptance uses a `git archive` of exact b788f3f, extracted into a new
Linux temporary directory, and the same unittest discovery. No source overlay
or network is used; mock socket guards reject network access in recovery tests.
The notebook builder verifies every embedded source against `git show` at b788f3f.
The broad regression loads the eight named suites in its receipt and excludes
only `test_all3763_once_through_controller_export_and_complete_resume_no_calls`.

Development failures are preserved locally and **not acceptance**: two initial
temporary-root fixture errors; a Linux run while source was changing; missing
Linux kagglesdk for its SDK-only case (now explicitly skipped and covered by the
pinned Windows suite); and an early broad run imported before the code commit,
whose dossier exact-HEAD check correctly rejected dirty source. An extra old
Windows full3763 stress invocation was stopped after3000 progress calls because
of filesystem cost; it has no final result. No fresh full3763 stress, full-discovery,
GitHub Actions, live GPU/model-fit/inference or full-TRAIN success is claimed.
Earlier PR198 full3763 synthetic evidence remains its historical source receipt.

The actual current campaign is **BLOCKED**: missing/denied historical provider
jobs conflict with retained local logs; all86400 GPU-s reservations remain held
against the old72000 cap. Genuine terminal custody, any explicit numerical
amendment, direct ChatGPT review, independent Antigravity audit, authorized merge,
postmerge verification and final-source release are outstanding. No approval,
audit, merge, authority, refund or live PASS was self-issued. The authorized
single Kaggle launch and handoff remain later gates in this same Codex task.
