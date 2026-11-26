# MiniCPM V7 Owner final approval — CPU acceptance

[Owner decision6954626555](https://github.com/tantdna2/SafeShift/issues/202#issuecomment-6954626555)
supersedes PR203's second GitHub reviewer account requirement. Base main:
`0f598f1f4f67619edbf8948492ac9b12af119edd`. Tested code/tests/tools commit:
`826b3f83ed358ee7ca59cdd594fce737124d199a`. Subsequent delivery changes are docs only.

The version2 delegation/release/ticket/final markers remove `review_logins` and
the second comment/CLI locator. ONE authentic Owner Issue202 final comment binds
the complete ordered 3763 manifest and full per-job provider report. Existing
`owner_record`, body/locator SHA, source-stage approval graph, signatures,
historical rights/closures/reservations, mirrors, strict raw/native/parser/RAM
verification and official-report revalidation remain required. Offline JSON
origin still relies on Owner-acquired authentic exports and checking originals;
synthetic fixtures do not authenticate a real GitHub or Kaggle result.

Initial ceiling is 100, with lower signed limits from time/quota/caps. Release
window is exactly 30 days from genuine issuance, with cleared unsigned-template
timestamps and a 4h job cap. No measured speed or completion guarantee is claimed.
Original Operator session/key/host remain mandatory. Source subject hashes cover
the changed schema, limits and timestamps; no old source grant can activate it.

Runtime manifest SHA256:
`cc0141cb3800898398d32d8114c275e0c89773a41affcd3dcd2ca2a8b86b2f95`.
11-tool manifest SHA256:
`13c00f692d30a94b17010bed8e822ebee3f946092d202608958a9d6330230033`.

## Validation

Execution spans 17–18/11/2026 (Asia/Bangkok); the filename follows the Owner
decision date 17/11/2026.

**100 distinct test IDs PASS**, zero unresolved failures/errors, no unexercised
platform skips. Counts are the union of passed test IDs, not the sum of runs or
subTests. All tests use synthetic records/scripted model outputs, fresh ephemeral
test-only RSA keys and mocked provider boundaries. No dataset, model weights, GPU, Kaggle, real
source release/ticket signing or production journal is used. `scientific_qualified`
remains false and scientific selection remains PENDING.

| Accepted run | Run | PASS | SKIP | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Windows regression | 95 | 90 | 5 | 659.770 |
| Linux offline/full3763 | 24 | 24 | 0 | 801.391 |
| Linux RAM/collection/supervision/adaptive | 23 | 23 | 0 | 22.981 |

All five Windows skips passed on Linux. Logs and per-ID union are Git-ignored
under `data/processed/v7-owner-cpu/`; their SHA256:

```text
windows-regression.log 1fb88634a1ee96d649527ffbd8184bea605180a0c7cd1e79f95a52a7ada730da
linux-offline.log      44c9066a09bb5ea4f1effa0541d98561bf377d1a41553982b46e3d1f1adfcd71
linux-regression.log   7d90f53023f7039d6bac3b9701363b3dfb78f50249695142699750ebcce39274
```

The summary verifies all changed runtime/tool/test bytes still equal the tested
commit. `git diff --check` PASS. No model fit, throughput or scientific PASS is
inferred from these CPU tests.

Windows uses CPython 3.11.9, kaggle 2.2.5/kagglesdk 0.1.38 in the existing local venv;
socket connections are forbidden. The unittest loader adds repository root and
`tests` to `sys.path`, then loads these modules with verbosity2:

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

Linux uses WSL Ubuntu/CPython 3.14.4 and an exact `git archive` of the tested
commit, extracted into a fresh temporary directory. Commands:

```sh
python3 -B -m unittest discover -s tests -p test_minicpm_offline_continuation.py -v
PYTHONPATH=tests python3 -B -m unittest test_minicpm_fulltrain_memory test_minicpm_v6_collection test_minicpm_run1_recovery.LiveSupervisionTests test_minicpm_fulltrain_execution.ExecutionTests.test_actual_load_overhead_stops_before_first_sample_start_and_exports_pending test_minicpm_fulltrain_execution.ExecutionTests.test_adaptive_storage_boundary_has_no_sample_start_or_native_call test_minicpm_fulltrain_execution.ExecutionTests.test_retention_refuses_unsealed_or_changed_tree_without_moving_it test_minicpm_fulltrain_execution.ExecutionTests.test_duplicate_upload_intent_and_torn_mirror_never_release_budget test_minicpm_fulltrain_execution.ExecutionTests.test_claimed_native_controller_raw_invalid_and_adaptive_resume -v
```

Coverage includes full 3763 synthetic ordered completion over two jobs (first 100,
then 3663), actual archive/raw/native-claim/mirror replay, single Owner final
admission and official reading. It also checks missing/malformed/foreign Owner
records, bad issue/locator/body hash, rehashed wrong manifest/report/status,
provider job omissions/duplicates/order/version/source/output/capsule drift,
historical drift, duplicate final append, tampered mirrored journal, old grants,
30-day expiry, initial100/time-lowered cap and unsigned-template timestamps.

PR201 RAM/supervisor/native/science and historical notebook byte checks compare
against exact PR201 main `e713d56d62a5a649a2078f2c2376fde6d025b978`. The diff from
PR203 main also leaves those files, model/precision/parser, configs, prompts and
TRAIN/TEST unchanged. Untracked pre-existing local files remain outside the PR.

Two development launcher errors (WSL shell quoting and a local test-runner import
path) were corrected before accepted runs; neither represents an accepted test
PASS. The initial Windows 22-case exploratory run passed 21 with one Linux-only
skip before two further tests were added; it is excluded from final counts.
Full-repository test discovery was not run; these are focused route/regression
checks. Independent review/audit/merge/postmerge and real release remain pending.
