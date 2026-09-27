# W2.6-D9R2L-MOONDREAM-POSTFIX-SMOKE-PREP

Status: **PREPARED_NOT_RUN**. Authority: Research Lead task, 2026-09-27.
Base main: `a6f5c012437bf8f404924e8dfb19a11536a92d77` (PR #47 closure fix).
This PR prepares a separate post-fix smoke; it does not authorize execution or merge.

## Evidence supplied by the Research Lead

Load diagnostic `moondream-load-diagnostic-20260927T014821Z-b3c87faa`:
**LOAD_ONLY_PASS**, stage complete, diagnostic exit 0, exception null;
model_load_count 1, state audit VALID, query_call_count 0, detect_call_count 0.
Exactly one process-visible Tesla T4, CC 7.5; Python 3.11.11 and exact pinned
dependencies; provision manifest equals verify manifest; execution commit equals
the base SHA above. The bundle was not independently opened/rehashed in this PREP.
This updates the prior load-only status; query/detect feasibility is still untested.

Historical official smoke
`kaggle-t4-moondream-smoke-20260926T070217Z-4c2d43` remains **FAIL**, with its
attempt **consumed**, failing before successful model load. The post-fix smoke is
a separate experiment, not a retry, replacement or superseding official result.
Never delete, reset, fabricate or reuse the historical ledger, even if its old
ephemeral session no longer exists. See the [historical contract](w2_moondream_runner_smoke_prep.md)
and [load diagnostic evidence history](w2_moondream_load_diagnostic.md).

## Minimal implementation and attempt boundary

[Wrapper](../scripts/w2_moondream_postfix_smoke.py) calls the existing `run_smoke()`.
The shared helper gains only an optional `command` keyword to record the actual
post-fix launch in raw provenance; its old default and all runtime logic stay intact.
No runner, model/upstream, bridge, redactor, frozen plan, prompt or dependency edits.

| Artifact | Historical official smoke | Separate post-fix smoke |
| --- | --- | --- |
| Namespace | `data/processed/moondream_t4_smoke/` | `data/processed/moondream_postfix_smoke/` |
| Fixed ledger | `ATTEMPT.json` (consumed) | `ATTEMPT.json` (exclusive create) |
| Result / raw | Original FAIL, untouched | `result.json`, `raw/` |
| Result schema | `moondream-smoke-result-v1` | `moondream-postfix-smoke-result-v1` |

The wrapper never accesses the historical artifact namespace. Its result/ledger
explicitly retain the historical run ID, FAIL, consumed=true and superseded=false.
Run IDs must start `moondream-postfix-smoke-`; changing the ID does not bypass the
single fixed ledger. No output-root override, retry, reset or force flag exists.
The ledger is exclusively created and flushed/fsynced before runner construction;
result output is also exclusively reserved before runtime entry. PASS, FAIL,
interrupt or incomplete result all consume the attempt. If an ephemeral session
is lost, restore/preserve the evidence and STOP; absence of a local ledger is not
permission for another attempt. Preflight rejection before reservation makes no
runtime call. Storage/process termination may leave a partial or empty report.

## Future execution contract — NOT executed in this PR

Use a separately authorized exact 40-character execution SHA **containing this
wrapper**, not the base SHA which lacks it. The wrapper checks HEAD and a clean
checkout including nonignored untracked files before runtime. Ignored cache and
artifacts are allowed. Use the unchanged Linux x86_64 / Python 3.11.11 pinned
environment from `requirements-moondream-t4.txt`.

Reuse only existing `data/processed/moondream_hf`. Missing or invalid cache is STOP;
no download, reprovision, alternate cache or fallback is provided. Before the
single future launch, verify-only in a separate process and compare the complete
manifest against the retained PASS diagnostic provision/verify pair. Disable venue
networking; the wrapper retains the official smoke's explicit network attestation.
The unchanged runner also permanently denies Python network/subprocess operations
and rehashes both pinned snapshots before loading their source/weights.

Illustrative commands for later authorization, from repository root (placeholders
must be replaced; do not execute during PREP):

```bash
python scripts/provision_moondream_snapshot.py --verify-only --cache-dir data/processed/moondream_hf --manifest data/processed/moondream_postfix_smoke/verify.json
cmp RETAINED_VERIFIED_MANIFEST data/processed/moondream_postfix_smoke/verify.json
CUDA_VISIBLE_DEVICES=0 python scripts/w2_moondream_postfix_smoke.py --execute-postfix-smoke --venue-network-disabled --expected-commit APPROVED_EXECUTION_SHA --run-id moondream-postfix-smoke-UNIQUE_ID
```

Stop on any failure. Launch a fresh OS process with the mask set by the shell
before Python starts, never `%run` or a reused notebook kernel. Runner metadata
must show exactly one T4 at cuda:0, CC 7.5, 14–16 GiB; a host with T4x2 is acceptable
only with this process isolation. No GPU switch or second worker on failure.

Reuse means exactly initialize, load, one classification query, one native detect
on the existing handcrafted red-rectangle fixture; failures stop immediately.
FP16, quantization NONE, batch 1, PILLOW_ONLY, unchanged precision bridge, no
CPU/disk inference offload or fallback. No InspecSafe or external gate access.
Lossless raw output is preserved before native parsing/checking, including returned
partial raw on failure. PASS still requires counts 1/1/1, five VALID state audits,
six ordered image boundaries, valid/restored bindings and memory observations.

Preserve ledger, result, raw bytes/metadata, verification manifests, launch command,
mask, exit code, UTC times and file checksums before ending the session. Compare
the result's model/tokenizer manifests with verify.json. A post-fix interface PASS
would establish only this smoke's feasibility, never historical PASS, grounding
qualification, accuracy, roster promotion or protocol freeze (still PENDING).

## PREP validation

**131/131 fake/static tests PASS**, including 10 new wrapper tests, on Windows /
Python 3.11.9. Raw-before-check, command provenance, untouched historical sentinels,
same/different-ID refusal after success/failure/interrupt, state/image/count failure,
exact SHA/clean checkout, launch mask and required flags are covered. Existing
runner/load/closure/source-audit regressions pass. The historical source allowlist
adds this wrapper plus D9R2J's already-present identity diagnostic (missing at base);
protected hashes and assertions remain unchanged.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_moondream_postfix_smoke tests.test_moondream_runner_smoke tests.test_moondream_load_diagnostic tests.test_moondream_binding tests.test_moondream_function_identity_diagnostic tests.test_moondream_prep_audit tests.test_d9_t4_roster_revision
.venv/Scripts/python.exe -m py_compile scripts/w2_moondream_postfix_smoke.py scripts/w2_moondream_t4_smoke.py tests/test_moondream_postfix_smoke.py
git diff --check
```

Compile and diff checks **PASS**. Full suite and CPU tensor bridge tests were not
rerun: scope is the wrapper/provenance seam; runner and precision bridge are unchanged.
No real GPU/model load, download, smoke, query/detect, external gate or InspecSafe
execution. Test artifacts use disposable temporary directories. The pre-existing
untracked census manifest is untouched and excluded from the PR. No redaction fix
or merge; future Linux/T4/model execution remains **NOT_RUN**.
