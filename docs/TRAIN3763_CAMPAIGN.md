# TRAIN3763 campaign contract — Issue180, 05/11/2026

## Current safe shard resource optimization and full-cohort O5 budget projection — 08/11/2026

[Official task, 07/11/2026](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6705546490)
and [direct ChatGPT PR186 review](https://github.com/tantdna2/SafeShift/pull/186#issuecomment-6708149603),
verified BASE `109be1ab33ef2c86a2604e1c1bc1a894464e17a2` (PR185 merged), use the
published Attempt4 `PASS` / `MEASURED` telemetry
([#6703549766](https://github.com/tantdna2/SafeShift/pull/185#issuecomment-6703549766))
and blocker audit ([#6703678087](https://github.com/tantdna2/SafeShift/pull/185#issuecomment-6703678087))
to harden fail-closed shard resource accounting, enforce pre-call and archive-export
time reserves, audit Grammar V2 capture geometry, and evaluate whether all `3,763`
planned `TRAIN` images can be completed under the approved O5 campaign cap
([#6657871236](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6657871236),
grant [#6658142293](https://github.com/tantdna2/SafeShift/pull/181#issuecomment-6658142293)).
Zero live Kaggle API calls, uploads or submissions, zero GPU/weights/real-image
inference, zero `TEST` reads, zero Attempt5 creation, zero self-modification of O5
or grant caps (`total_gpu_seconds = 80,000` remains active), and zero mutation of
`data/processed/train3763*` occur in this task.

### Baseline custody after Attempt4 PASS/MEASURED (`14,400` physical GPU-s reserved, `3,762` images remaining)

| Metric | Verified Attempt 1–4 Campaign State |
| --- | --- |
| Attempts 1–2 | `ABORTED_PRE_SUBMIT` (`2` calls / `2` jobs / `7,200` physical GPU-s retained, no refund) |
| Attempt 3 | `COLLECTED` terminal `FAIL` (`0` model calls, `3,763` `NOT_ATTEMPTED`; cumulative `3` calls / `3` jobs / `10,800` physical GPU-s) |
| Attempt 4 | `COLLECTED` `PASS` + `MEASURED` on `deef3c26eb55e5fb7196cba96220a79a92a058f028cf957a390fad9e010d14ad` (`nguynanhtn/safeshift-train3763-ivl35-train3763-4/1`, kernel `143188917`); ordinal `0` `SUCCESS` (`Level02`); cumulative `4` calls / `4` jobs / `14,400` physical GPU-s |
| Remaining cohort | **`3,762` `NOT_ATTEMPTED` `TRAIN` images** (ordinals `1..3762`); ordinal `0` is durably complete and never re-executed under `resume` |
| Approved O5 remaining | `4,496 / 4,500` calls, `96 / 100` jobs, **`65,600 / 80,000` physical GPU-seconds** (`32,800` wall-clock seconds on `NvidiaTeslaT4` `physical_gpus = 2`) |
| Observed Attempt4 telemetry | `setup_seconds = 267.21s` (`setup-supervisor.json`), `worker_supervisor_seconds = 605.567s` (`worker-supervisor.json`: `592.147s` preflight + `admit_inputs` + `load_seconds = 73.41s`, plus `sample_seconds = 13.42s`), total `non_sample = 859.357s`, total `wall_clock = 872.777s`, `gpu_peak_allocated = 14,134,920,704` B (`13.16 GiB`), `gpu_peak_reserved = 14,558,429,184` B (`13.56 GiB`), `output_free_bytes = 20,937,965,568` B (`19.50 GiB`), `raw_float32_bytes = 6,077,440` B, `observed_sample_bytes = 14,055,278` B, compressed ZIP `5,617,751` B (`29` members), Kaggle weekly GPU quota remaining `20,727s / 108,000s` |

### Safe technical optimizations and pre-Kaggle hardening (`science_sha256` unchanged)

All 84 inherited files in `safeshift/internvl_v2_runtime.py::source_spec()["manifest"]`,
model/weights/precision (`OpenGVLab/InternVL3_5-4B-HF`, revision
`6bd4487402110ef9889ba50eb7aefeb302526fed`, FP16 on GPU0), `TRAIN` 3,763 master
manifest, canonical labels, Grammar V2 (`configs/grammar/internvl35_v2.json`), strict
C1 parser, full uncompressed `.f32` step logit capture (`raw-before-parse`) and replay
verification remain byte-for-byte identical (`science_sha256` =
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`). Only
`safeshift/internvl3763.py` and `safeshift/internvl3763_campaign.py` change in the
90-file runtime manifest (`runtime_commit` = `855473d61c72e97d2837f34c201e47ba89408a5e`,
`source_sha256` = `a4b21fd409b418d314a59ff881f5bf33cab1ab18a44782faaceecb4e59ee89cb`):

1. **Enforced `180s` pre-call reserve and dynamic `5 MiB/s` ZIP export reserve (`DEADLINE_BEFORE_NEXT_CALL`):**
   `scripts/internvl3763.py::launch()` sets `worker_deadline = container_deadline - 75`
   (`STAGE_EXPORT_RESERVE_SECONDS = 60` + `WORKER_EXIT_RESERVE_SECONDS = 15`). Inside
   `safeshift/internvl3763.py::_execute()`, before **every** sample (including sample `0`
   with zero prior calls, fast samples `< 90s`, slow samples, exact `180.0s` boundary,
   mid-shard stop, and already-expired deadlines), the worker now requires:
   `worker_deadline - monotonic() > max(PRE_CALL_RESERVE_SECONDS, 2 * max_observed_sample_seconds) + extra_export_reserve`,
   where `PRE_CALL_RESERVE_SECONDS = 180` and
   `extra_export_reserve = max(0.0, projected_archive_bytes / EXPORT_RESERVE_BYTES_PER_SECOND - 60)`
   at a conservative `EXPORT_RESERVE_BYTES_PER_SECOND = 5 * 2^20` (`5 MiB/s`). On multi-call
   shards (`~2.45 GiB` observed uncompressed payload across `174` samples), this dynamically
   reserves hundreds of seconds for `artifacts.export()` (ZIP deflate + `SHA256` verification)
   to leave a modeled window for the worker to write `summary.json`, `checksums.json`, and `terminal.json` and
   exit. This is a scheduling assumption, not proof of Kaggle compression/CRC throughput or immunity to container termination; preserve partial evidence on failure.
2. **Audited Grammar V2 10-step & `151,936`-logit invariant with fail-closed `INVALID` fallback:**
   Direct audit against `configs/grammar/internvl35_v2.json`, real `Qwen2TokenizerFast`
   (`tokenizer_size = 151,679`, `eos_token_id = 151645` `<|im_end|>`, padded `lm_head`
   `logit_width = 151,936`), `GenerationConfig(max_new_tokens=64, eos_token_id=151645, do_sample=False)`,
   and `InternVLGrammarV2` proves that all four canonical completions
   (`{"safety_level":"Level01"}<|im_end|>` .. `{"safety_level":"Level04"}<|im_end|>`) tokenize to **exact
   length `10`** (`9` content tokens differing only at index `7` + `1` EOS `151645` at step
   `9`). At step `9`, Grammar V2 masks every token except `151645`, halting `GenerationMixin`
   immediately at `10` steps (`<= max_new_tokens = 64`), and any 11th call into the trie
   raises `GRAMMAR_PREFIX_OUTSIDE_LANGUAGE`. Thus every grammar-constrained `SUCCESS` call
   writes `10 * 151,936 * 4 = 6,077,440` B of `.f32` raw vectors and is strictly bounded by
   `capture_budget(151_936, 10) = 15,378,176` B uncompressed (vs legacy `120,442,880` B).
   `safeshift/internvl3763.py::_backend_capture_budget()` queries `capture.native_grammar()`
   on native runs, `verify_bundle()` calls `verify_retained_raw_vectors()` on **both**
   `SUCCESS` and `INVALID` records (no `.f32` vector is ever discarded), and
   `Ledger.measure()` verifies `LOCKED_INTERNVL35_GRAMMAR_GEOMETRY` + exact `607,744`-byte
   step files while automatically falling back to `capture_budget(200_000, 64) = 120,442,880` B
   if any `INVALID` sample occurs. Using `max(15,378,176, 2 * 14,055,278) = 28,110,556` B/sample
   and `64 MiB` (`67,108,864` B) base non-sample archive reserve under `7 GiB`
   (`7,516,192,768` B) yields **`archive_cap = 264` calls/job**; accounting for simultaneous
   uncompressed `work/samples` + compressed `out.zip` (`2 * 28,110,556 = 56,221,112` B/sample)
   on `19.50 GiB` free disk after `1 GiB` disk reserve plus the `64 MiB` base allowance yields **`disk_cap = 352` calls/job**.
3. **Unified timing constants and budget formulas across runtime, ledger, and `forecast`:**

   | Constant / Parameter | Value | Exact Role Across Code & Runbook |
   | --- | --- | --- |
   | `MINIMUM_EXECUTION_SECONDS` | `120s` | Hard contract floor enforced identically in `validate_execution_request()`, `Ledger.reserve()`, and `required_job_seconds()` |
   | `STAGE_EXPORT_RESERVE_SECONDS` + `WORKER_EXIT_RESERVE_SECONDS` | `60s + 15s = 75s` | `LAUNCH_WORKER_HEADROOM_SECONDS`: container-to-worker deadline gap in `scripts/internvl3763.py::launch()` |
   | `PRE_CALL_RESERVE_SECONDS` | `180s` | Mandatory inner worker time reserve checked before every sample in `_execute()` |
   | `MEASURED_TIME_MARGIN_SECONDS` | `255s` (`75 + 180`) | Added to `ceil(2 * (setup + worker_non_sample))` in both `Ledger.measure()` and `project_campaign_budget()` (`overhead_seconds = ceil(2 * 859.357) + 255 = 1,974s`) |
   | `EXPORT_RESERVE_BYTES_PER_SECOND` | `5,242,880` B/s (`5 MiB/s`) | Added to per-call runtime in `_execute()`, `Ledger.measure()`, and `project_campaign_budget()` (`per_call_seconds = ceil(2 * 13.42 + 14,055,278 / 5,242,880) = 30s`) |
   | `--seconds 1800` | `1,800s` | Operational CLI request parameter for **1-call unmeasured / new-source measurement runs** (`~873s` cold run * `~2.06x`), **not** a hidden floor overriding `120s` in `required_job_seconds()` |

   Under `job_seconds = 7,200`, `time_cap = floor((7,200 - 1,974) / 30) = 174` (`safe_calls = 174`,
   `full_shard_seconds = 7,194s`, `2.81x` higher than `62` while enforcing complete preflight,
   `180s` pre-call, and `5 MiB/s` ZIP export margins). Under an Owner-authorized
   `job_seconds = 10,800`, `time_cap = 294` so `safe_calls` reaches **`264` calls/job**
   (`full_shard_seconds = 9,894s`). `required_job_seconds(measured, calls)` reserves
   `max(120, overhead_seconds + per_call_seconds * calls)` proportionally
   for tail shards and targeted `repair` jobs (with legacy `minimum_seconds` fallback).
4. **Additional storage, supervisor log, and Linux cgroup memory safeguards:**
   `_execute()` checks free space on both `export_root` and `Path(archive).parent`, keeps a
   `16 MiB` summary/export allowance under `min(archive_limit_bytes, 8 GiB)`
   (`ARCHIVE_VERIFIER_8GIB_BOUND_EXPORT_MARGIN`), caps archive members `< 1,000,000`
   using the same stop reason, stops cleanly at `12 MiB` supervisor stdout/stderr
   before the `16 MiB` hard cap (`WORKER_LOG_BUDGET_MARGIN`), and enforces Linux cgroup
   v2 snapshots using top-level `status == OBSERVED`, empty top-level `errors`, numeric nested fields and events. Both pre-call and `Ledger.measure()` require at least `512 MiB` host/cgroup headroom and zero OOM events. `INCOMPLETE`, absent/malformed observations and cgroup-v1-only layouts stop with `CGROUP_MEMORY_UNOBSERVED`; cgroup v1 is not supported by this snapshot contract. `memory.max = max` is admitted only with observed host MemAvailable, current/stat/events and process fields. Missing optional `memory.peak` alone is allowed. Only explicit synthetic rehearsal bypasses the native gate.

### Three distinct GPU-time quantities & non-overclaiming boundary

1. **Ledger reserved physical GPU-seconds (`reserved_gpu_seconds`):**
   `physical_gpus * requested_job_seconds` (`2 * seconds` on `NvidiaTeslaT4`), charged upfront
   against `caps.total_gpu_seconds` (`80,000`) at `INTENT` creation with zero refund on early
   completion, pre-submit abort, or worker failure.
2. **Actual physical dual-T4 GPU-seconds:**
   `2 * actual_session_wall_seconds` while the 2-GPU `NvidiaTeslaT4` VM is allocated (even
   though `InternVL3_5-4B-HF` executes on `GPU0` and `GPU1` remains idle).
3. **Kaggle weekly GPU quota seconds:**
   Kaggle deducts **session wall-clock seconds** (`1x` runtime, not `2x`) from the account's
   `108,000s` (`30h`) rolling weekly GPU quota (`20,727s` remaining after Attempt4).

**Evidentiary boundary (no overclaiming):** Attempt4's `13.42s` sample latency is a
**single-image observation** on `ordinal 0`, **not** a proven upper or lower bound across the
`3,762` remaining `TRAIN` images (`population_latency_distribution_verified = false`). Higher-resolution
images (`dynamic_patch` tiles), container I/O variance, or `repair` reruns can increase actual
per-sample runtime. Similarly, the 2-week Kaggle quota schedules below are **conditional
estimates** assuming Attempt4-like throughput, **not** a calendar completion guarantee.

### Quantitative O5 budget evaluation for all `3,762` remaining `TRAIN` images

**Direct engineering finding:** **NO** — completing all `3,763` `TRAIN` images is
**infeasible** under the current `total_gpu_seconds = 80,000` O5 cap (`65,600` physical
GPU-seconds = `32,800` wall-seconds remaining on `2xT4`) under the modeled safe reservation scenarios below
(`TOTAL_GPU_SECONDS_CAP_INSUFFICIENT_UNDER_MODELED_SAFE_ENVELOPE`), and even an illustrative
extrapolation of Attempt4's `13.42s` rate with zero setup/preflight/load overhead
(`3,762 * 13.42s * 2 GPUs = 100,973` physical GPU-s) would exceed the remaining `65,600`
physical GPU-s by **`+35,373` physical GPU-seconds**. Full reproducible numbers from
`python -B -m scripts.train3763_campaign forecast` are published in
[`budget_projection.json`](research/evidence/train3763_gpu_budget_20261107/budget_projection.json):

| Scenario (`14,400` GPU-s already reserved across Attempts 1–4) | `safe_calls` / job | Future jobs (Total jobs / `100`) | Future reserved GPU-s (Campaign total) | Shortfall vs `80,000` O5 cap | Max remaining images under `80,000` (Left `NOT_ATTEMPTED`) | Conditional Kaggle quota estimate at Attempt4 rate (`Week 1` / `Week 2`) |
| --- | --- | --- | --- | --- | --- | --- |
| **1. Legacy `main`** (`job_seconds=7200`, `64`-step bound, incomplete `802s` overhead, no source change) | `62` | `61` (`65`) | `302,072` (`316,472`) | **`-236,472` GPU-s** | `806` + ord0 = `807` (`2,956` left) | `113,869s` (31.63h), incl. modeled export `10,926s`: W1 11 jobs / 682 imgs (20,592s); W2 50 jobs / 3,080 imgs (93,277s) |
| **2A. Optimized safe (`job_seconds=7200` unchanged)** — incl. mandatory 1-call Attempt5 measurement on ordinal `1` (`3,600` GPU-s) + `22` shards (`21x174 + 1x107` proportional tail `5,184s`) | `174` | **`23` (`27`, `-62.3%` future jobs)** | `316,116` (**`330,516`**) | **`-250,516` GPU-s** | `705` + ord0 = `706` (`3,057` left) | `80,660s` (22.41h), incl. modeled export `10,396s`: W1 6 jobs / 871 imgs (19,264s); W2 17 jobs / 2,891 imgs (61,396s) |
| **2B. Optimized safe + Owner `job_seconds=10800`** — incl. 1-call Attempt5 (`3,600` GPU-s) + `15` shards (`14x264 + 1x65` proportional tail `3,924s`) | `264` | **`16` (`20`, `-73.8%` future jobs)** | `288,480` (**`302,880`**) | **`-222,880` GPU-s** | `793` + ord0 = `794` (`2,969` left) | `74,545s` (20.71h), incl. modeled export `10,298s`: W1 4 jobs / 793 imgs (16,261s); W2 12 jobs / 2,969 imgs (58,284s) |
| **3. Illustrative Attempt4 rate extrapolation** (*NOT a population lower bound or safety gate*) | `174` (illustrative) | `23` (`27`) | `100,973` inference-only; `140,503` w/ 1x overhead (`154,903` total) | **`-74,903` GPU-s** (`-35,373` inference-only) | Not admissible as safety gate | `70,252s` wall-clock (`140,503` physical GPU-s equivalent on `2xT4`) |

*(Note: Scenario 2A's reserved GPU-s ceiling `330,516` is slightly higher than Scenario 1's `316,472` solely because Scenario 1 omitted `~592s` of preflight/input-verification overhead and ZIP export time, whereas Scenario 2A enforces the full `1,974s` 2x non-sample + `255s` margin and `30s/call` including `5 MiB/s` ZIP export while cutting future Kaggle jobs from `61` to `23` and saving a modeled `~9.22h` of session wall-time including export; Scenario 2B at `job_seconds = 10,800` reduces **both** reserved GPU-s to `302,880` and future jobs to `16`.)*

**Latency sensitivity under `job_seconds = 7,200` (with contingency = `4` extra continuation jobs + `100` `repair` calls):**
- `1.00x` Attempt4 sample latency (`per_call = 30s`, `safe_calls = 174`): `330,516` GPU-s zero-error / **`352,308` GPU-s** with contingency.
- `1.25x` Attempt4 sample latency (`per_call = 37s`, `safe_calls = 141`): `402,910` GPU-s zero-error / **`426,102` GPU-s** with contingency.
- `1.50x` Attempt4 sample latency (`per_call = 45s`, `safe_calls = 116`): `486,774` GPU-s zero-error / **`511,566` GPU-s** with contingency.

### Required Owner O5 decision (`PROPOSED_PENDING_OWNER_DECISION_NOT_ACTIVE`)

- Existing `total_calls = 4,500`, `total_jobs = 100`, `archive_bytes = 7,516,192,768`,
  `max_repairs_per_image = 10`, `machine_shape = "NvidiaTeslaT4"` and `physical_gpus = 2`
  already suffice (`27` or `20` total jobs `<< 100`; `3,766` zero-error calls `<< 4,500`).
- **Owner decision requested before full-cohort sharding:** authorize raising
  `caps.total_gpu_seconds` from `80,000` to **`430,000` physical GPU-seconds** (`215,000`
  wall-seconds = `59.72` wall-hours reserved ceiling on `2xT4`, covering `1.25x` mean sample
  latency plus `4` continuation jobs and `100` `repair` calls = `426,102` GPU-s; mathematical
  zero-margin `1.00x` floor is `330,516` at `job_seconds = 7,200` or `302,880` at
  `job_seconds = 10,800`), and optionally raise `caps.job_seconds` from `7,200` to **`10,800`**
  to unlock `264`-call shards (`20` total jobs instead of `27`).
- **Note on Attempt5 1-call re-measurement:** Attempt5 (`--mode resume --calls 1 --seconds 1800`
  on `ordinal 1`) reserves only `3,600` physical GPU-s (cumulative `18,000 / 80,000` GPU-s,
  `5 / 100` jobs, `5 / 4,500` calls), so once this PR is reviewed, audited, merged and
  attested, the 1-call ordinal-1 measurement itself fits inside the existing `80,000` O5 grant,
  whereas full-cohort multi-call completion requires the Owner O5 amendment above.

### Kaggle Operator GO / NO-GO runbook for Attempt5 (`ordinal 1` re-measurement) and subsequent shards

Because `source_sha256` changed (`deef3c26...` -> `a4b21fd4...`), Attempt4's `MEASURED`
record does **not** certify the new runtime (`FINAL_SOURCE_MEASUREMENTS_REQUIRED_BEFORE_SHARDS`).
Execute the following sequence **only AFTER** direct ChatGPT GitHub review, independent
Antigravity audit, separately authorized merge to `main`, and publication of authentic
`SAFESHIFT_TRAIN3763_AUDIT_V1` + `SAFESHIFT_TRAIN3763_TECHNICAL_V1` comments binding
`runtime_commit` `855473d61c72e97d2837f34c201e47ba89408a5e`, `source_sha256`
`a4b21fd409b418d314a59ff881f5bf33cab1ab18a44782faaceecb4e59ee89cb`, execution notebook
SHA256 `310d023c944eca426673bcbe2493f9b25e3c2f961e8fa3edb98635352d93bd33` (`code_sha256`
`bd337944b433edf12a74c94568ebff407992264ce3d02d5192e1032628bab7a2`), and `PREP` notebook
SHA256 `026d48ad8d6fd4c49def698b0e88bf6f8aadfb23d59d083ee3ec4deb8aa58dc9` (`code_sha256`
`9b8c556ecf51130543fdf7e226a5467f9439a689ad34b84edd89fb8e1bdc0b41`).

**Pre-staging GO / NO-GO gate (`STOP` immediately if any check fails):**
- **GO** only if: `git status --porcelain --untracked-files=no` is empty on exact merged `main`;
  `ledger` and `mirror` match with `0` open intents (`4` calls / `4` jobs / `14,400` GPU-s,
  ordinal `0` `SUCCESS`); no prior campaign job (`1..4`) is `RUNNING` or unknown on Kaggle;
  weekly GPU quota remaining `> 1,920s` (`1800 + 120`); and fresh `context-attempt5.json`
  points to a **brand-new** private capsule slug `nguynanhtn/<unique-attempt5-capsule>/1`.
- **NO-GO (`STOP` read-only):** any dirty tracked file, unmerged branch, stale attestation,
  reused capsule slug/directory, open `INTENT` / `PUSH_INTENT`, or provider/journal mismatch.

```powershell
# Step 1 — Read-only status & deterministic forecast check (no network, no mutation)
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Ledger = 'data/processed/train3763-campaign/ledger'
$Attempt5 = 'data/processed/train3763-campaign/attempt-5'
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action status -Directory $Ledger
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action forecast -Directory $Ledger

# Step 2 — Stage Attempt 5 on ordinal 1 (preserves ordinal 0 Level02 SUCCESS; reserves 3,600 GPU-s)
# Requires clean merged main + fresh context-attempt5.json with new technical_revision & unique capsule slug
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action plan `
  -Context data/processed/train3763-campaign/context-attempt5.json `
  -Handoff $Attempt5 -Mode resume -Calls 1 -Seconds 1800

# Step 3 — Upload ONLY the new small private capsule dataset version 1, then run read-only GCS 443 byte proof
$ProofCode = @'
import json, sys, tempfile
from pathlib import Path
from safeshift import internvl3763_operator as op
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write
request = read(Path(sys.argv[1]) / 'request.json')
ledger = op.campaign_ledger(request)
with lock(ledger.root):
    before = ledger.events()
    grant, execution = op.admit_campaign(request)
    client = op.api()
    inventory = op.campaign_inventory(client, request, grant, ledger)
    intent = ledger.open_intent()
    proof_root = Path(tempfile.mkdtemp(prefix='capsule-readonly-', dir=Path(sys.argv[1]).parent))
    proof = op.verify_execution_input(client, request, intent, proof_root / 'download')
    assert ledger.events() == before
    write(proof_root / 'inventory.json', inventory)
    print(json.dumps({'status': 'READ_ONLY_CAPSULE_BYTE_PASS', 'proof': proof}, sort_keys=True))
'@
& $OperatorPython -B -c $ProofCode $Attempt5
if ($LASTEXITCODE -ne 0) { throw 'NO-GO: retain proof/partials; do NOT push or delete intent' }

# Step 4 — Single delegated submit & <=15 min monitor (pause cleanly on RUNNING_UNVERIFIED; NEVER resubmit)
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action start -Directory $Attempt5
# When Kaggle reaches terminal state, resume the saved conversation to collect ZIP/SHA256/logs & verify custody:
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action resume -Directory $Attempt5
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action report -Directory $Attempt5

# Step 5 — Record live MEASURED envelope for the new source_sha256 before planning multi-call shards
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action measure -Directory $Ledger `
  -Job nguynanhtn/safeshift-train3763-ivl35-train3763-5/1
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action forecast -Directory $Ledger
# Next shards (--Mode resume -Calls <measured_safe_calls> -Seconds <required_seconds>) require active Owner O5 cap sufficiency.
```

### Offline acceptance and immutable rebuild

Runtime `855473d61c72e97d2837f34c201e47ba89408a5e` is embedded identically in both rebuilt notebooks. The final
acceptance receipt and sanitized logs in [summary.json](research/evidence/train3763_gpu_budget_20261107/summary.json)
bind the tested commit, exact source/science/manifests, notebooks, test files and logs.
The inherited unpushed commits `7d8d4ec` and `893f5b6` were preserved and reviewed;
the original GitHub head was `f87b2cc`. No tracked uncommitted work was present at takeover;
unrelated untracked files were preserved. Final-source live verification is NOT_RUN.

The default sensitivity values above are calculated with **4 extra job overheads + 100 repair calls**,
not the previously advertised 5/200. At 5/200, totals are **362,256 / 437,450 / 524,514 GPU-s**
for 1.00x / 1.25x / 1.50x. Thus the unapproved 430,000 proposal covers the modeled default
1.25x case (426,102), but not the expanded case (437,450). These contingencies count
extra startup overhead and repair-call time; they do not cover arbitrary full-timeout failed
jobs. Owner must choose the contingency and cap before any corresponding execution.

Quota tables now add `ceil((64 MiB + sample_bytes * calls) / 5 MiB/s)` per job for export;
the old 70,264s / 64,247s figures excluded it. The observed-only extrapolation row explicitly
retains its pre-export basis. All quota estimates use a historical quota snapshot, not live
availability; 5 MiB/s includes an assumed compression/hash/CRC allowance and is **unmeasured**.
Reservations remain 330,516 / 302,880 GPU-s under the modeled schedules. No minimum across
all possible implementations or population latency distribution has been proved.

After review, independent audit, separately authorized merge and authentic source-bound
attestations, the next separately permitted live measurement must resume **ordinal 1**, one
call / 1,800s. Preserve Attempt4 ordinal0 and every Attempt1–4 record; never reuse its MEASURED
entry for this source. No staging, submission, Kaggle API call, GPU or TEST access occurs here.

Final offline acceptance: **241 focused tests (240 PASS, one Windows SKIP), 3 notebook
tests PASS, 100 PR177 tests (88 PASS, 12 Windows SKIPs), 2 foundation smoke tests PASS,
27 Linux tests PASS with zero skips**. Linux covers all platform skips. All ten PR177
native CPU tests were enabled and passed, rather than being counted as Linux coverage.
Exact tested commits are `ac8793d8fea5110728315b5af29f6a1f4d86e989` and
`bb9505de8421482f0bf4ef173fe694ddc7e03c9f`; the latter changes only the affected E2E
timestamp oracle, whose full suite was rerun. No final failure/error remains. See the
[sanitized transcript](research/evidence/train3763_gpu_budget_20261107/validation.txt)
and per-group source/test/log hashes in the receipt. The inherited test compared two
fresh `monotonic` values for equality; the correction compares stable memory fields and
separately asserts freshness, retaining the worker/ZIP/collect/MEASURED rejection checks.

For offline reproduction, use the existing local CPU packages listed in the receipt,
`SAFESHIFT3763_SDK_CPU=1`, and `scripts.qualify_internvl3763 --native` with a new ignored
output directory. PR177 additionally needs `SAFESHIFT_V2_NATIVE_CPU=1` and both
`SAFESHIFT_V2_SOURCE` / `SAFESHIFT_V2_TOKENIZER` pointing to the verified existing
`data/processed/internvl_v2_native/public-source` metadata. Keep CUDA visibility empty,
HF/transformers offline, and `tests` plus those CPU packages on PYTHONPATH. The 1.25x/1.50x
sensitivity multiplies the full per-call allowance (latency plus modeled export).

## Historical PR177-vs-TRAIN3763 end-to-end repair and Attempt3 FAIL collection — 07/11/2026

[Official task, 07/11/2026](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6686823873)
(consolidating diagnosed root cause [#6686513890](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6686513890)),
verified BASE `9f86424d14507fcc2fa08c2bf4a2f9a56e7dd481` (PR184 merged), authorizes
one cohesive Draft PR containing all offline-detectable integration fixes,
end-to-end synthetic tests, rebuilt TRAIN3763 notebooks, runbook updates and
sanitized test receipts. Zero live Kaggle API calls, probes, downloads, uploads
or submissions, zero GPU/weights/real-image inference, zero TEST access, zero
Attempt4 creation and zero mutation of `data/processed/train3763*` occur in this
implementation task. PR177's 04/11/2026 ordinal0 `Level02` `SUCCESS`
(`nguynanhtn/safeshift-internvl-v2-6626498951-j1/1`, kernel `142669354`, dispatch
HEAD `c67d41ab424fa6a4eb3baf61056a8e4e5b77ac66`, runtime
`0553fe56c884eac9b0031e4a96e7a14568606f4f`) is used strictly as an engineering
reference benchmark and is **never** imported or backfilled into TRAIN3763.

### Stage-by-stage differential audit: PR177 (`j1/1`) vs TRAIN3763 (`ivl35-train3763`)

All 84 inherited files in `safeshift/internvl_v2_runtime.py::source_spec()["manifest"]`
and `science_sha256` (`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`)
remain byte-for-byte identical to BASE and PR177. Every divergence on the
6-file TRAIN3763 wrapper layer was audited end-to-end:

| Stage | PR177 (`04/11/2026` `j1/1` PASS) | TRAIN3763 at BASE `9f86424` | Status / Repair in this PR |
| --- | --- | --- | --- |
| 1. Notebook & source admission | Embedded 84-file payload + per-job GitHub tag/release | Embedded 90-file payload (`build_internvl3763 --execute --campaign`) + Owner grant + `TECHNICAL_V1` + `AUDIT_V1` + `campaign-intent.json` | Verified intact; rebuilt deterministically from runtime commit `f2346fae68022d0e032868b73e923458d8e55b2e` |
| 2. Operator SDK & capsule proof | Local `submit_internvl_v2.py` (`bounded_http`) | `internvl3763_operator.py` (`check_sdk`, `v1` `GetKernel`, `capsule_http` `302` to `storage.googleapis.com[:443]` anonymous GET, SHA256/CRC proof before `PUSH_INTENT`) | Verified intact; `input_sources()` additionally rejects duplicate `owner/slug` across different `/N` versions |
| 3. `kernel-metadata.json` & push | Single `kernels_push`, private T4, `/N` pinned Input refs | Same single `kernels_push` after mirrored `PUSH_INTENT`, private T4, `/N` pinned Input refs | Verified intact |
| 4. Launcher & stage supervisor | `scripts/internvl_v2.py::launch()` passed `log=setup / "setup-supervisor.log"` to `supervision.run` | **DEFECT A:** `scripts/internvl3763.py::launch()` passed `log=setup / "setup.log"` (`"xb"`), colliding with child `prepare_runtime()`; setup lacked 60s export margin | **FIXED:** `scripts/internvl3763.py::run_stage()` writes `setup / "setup-supervisor.log"` (`"xb"`), watches stage `.log` files via `os.path.samestat` without double-counting, keeps `PDEATHSIG`/`SIGKILL` group kill, and enforces `stage_deadline = deadline - 60` |
| 5. Python 3.11/3.12 & offline wheel setup | `train_runtime.py::prepare_runtime()` writes `setup / "setup.log"` (`"xb"`) + `setup / "runtime.json"` | Identical frozen `train_runtime.py::prepare_runtime()` | Verified; `LauncherSupervisorSetupCompositionTests` exercises real `launch()` + `prepare_runtime()` on Windows & Linux process groups |
| 6. Preflight, streamed checkpoint, 16 GiB RAM, CUDA & CPU processor child | `internvl_v2_memory.py` streamed 2-shard SHA256 (`9.465 GiB`), owned-venv page-cache advice, `>=16 GiB` floor (`22.24 GiB` observed), GPU0 FP16 probe, 40-step synthetic grammar check | Calls exact same frozen functions in `safeshift/internvl3763.py::preflight()` | Verified byte-identical to PR177 |
| 7. Master & 3,763 TRAIN image admission | Ordinal 0 verified against `MASTER_SHA` | `admit_inputs()` reuses frozen `verification173.verify_train` over all 3,763 `train/Annotations/*.jpg` locators; zero TEST/annotation enumeration | Verified intact |
| 8. Worker deadline & native FP16 load | Single-image 1800s budget | Multi-call shard loop in `_execute()` previously computed `begun + p["max_seconds"]`, ignoring elapsed setup/preflight time | **FIXED:** `launch()` passes `worker_deadline = deadline - 75` into `worker(..., deadline=...)` -> `_execute(..., hard_deadline=deadline)` so multi-call shards stop cleanly before supervisor `SIGKILL` |
| 9. Grammar V2 capture, raw-before-parse & strict C1 parser | `Capture` forward hook `.f32` full-vocab vectors + `GrammarProcessor` + fsync `raw.json` before `parse_label` + `replay_saved` | Same frozen `Capture`/`GrammarProcessor`/`replay_saved` in `safeshift/internvl3763.py::generate_prepared()` | Verified via real `GenerationMixin` + `.f32` binary capture in `EndToEndOfflineCampaignPipelineTests` |
| 10. Archive export & terminal receipts | `terminal.json` + `checksums.json` + `.zip` + `.zip.sha256.json` | `launch()` always exports `.zip` + `.sha256.json`, even when setup or worker fails | **HARDENED:** `verify_bundle()` now checks `terminal.json["status"] == result["status"]`, `fresh-process-supervision-v1` (`automatic_retry is False`) on present supervisor receipts, and explicit failure records on `FAIL` |
| 11. Post-submit / collect `GetKernel` metadata check | Checked ref & privacy | **DEFECT B:** `Train3763Operator.identity()` compared `GetKernel`'s unversioned `owner/slug` lists against `owner/slug/N` strings, raising `REMOTE_ACCELERATOR_OR_INPUT_DRIFT` after Attempt3 `SUBMITTED` | **FIXED:** `verify_kernel_metadata_inputs()` checks `machine_shape == "NvidiaTeslaT4"`, empty `competition_data_sources`/`model_data_sources`, exact duplicate-free `owner/slug` bijection, `is_private is True`, `type(current_version_number) is int and current_version_number == 1`, and exact committed-notebook `code_hash` without treating unversioned `GetKernel` metadata as proof of `/1` |
| 12. Handoff recovery & report acceptance | N/A | **DEFECT C:** `_invoke_agy(resume=True, recover=True)` reused stale `conversation_id` if one existed; `accept_report()` only validated `PASS` fields | **FIXED:** `recover=True` forces `conversation = None` (read-only `collect` only); `accept_report()` validates terminal `FAIL` (`terminal in TERMINAL`, `collection == "FINISHED"`, non-empty `evidence`, and `verification["status"] == "FAIL"` when `terminal == "COMPLETE"`) |
| 13. Mirrored ledger `COLLECTED` reconciliation | GitHub tag `finished` | `verify_remote_custody()` validates ZIP/sidecar/CRC/claims/lineage and appends mirrored `COLLECTED` (idempotent on recollection; zero budget refund) | Verified on read-only Attempt3 bundle structure and full E2E suite |
| 14. Telemetry measurement & next-attempt planning | Single-image campaign stopped after `j1` | `Ledger.measure()` requires `COLLECTED` `PASS` with `NATIVE` telemetry before `calls > 1`; 0-call collected `initial` `FAIL` leaves 1 history entry (`records=[]`) | Verified & documented below: Attempt4 after collecting Attempt3 MUST use `--mode resume --calls 1 --seconds 1800` |

### Read-only operational state and post-merge Attempt3 -> Attempt4 runbook

Read-only local inspection (zero files modified under `data/processed/train3763*`,
76 files aggregate SHA256 `23d65d299fb373c8d510c282ab3001093fe8b9b5d6e01aa5448f2c54126b4f5a`
unchanged before and after this task) confirms:

| Attempt | Current ledger / custody state | Cumulative reservation (no refund) |
| --- | --- | --- |
| 1 | `ABORTED_PRE_SUBMIT` (never submitted) | 1 call / 1 job / 3,600 physical GPU-s |
| 2 | `ABORTED_PRE_SUBMIT` (never submitted) | 2 calls / 2 jobs / 7,200 physical GPU-s |
| 3 | `PUSH_INTENT` + `SUBMITTED` (`nguynanhtn/safeshift-train3763-ivl35-train3763-3/1`, kernel `142976950`); handoff `BLOCKED` post-submit on `REMOTE_ACCELERATOR_OR_INPUT_DRIFT`; Kaggle `COMPLETE` + worker `FAIL` at `setup.log` (`FileExistsError`), 0 model calls, 3,763 `NOT_ATTEMPTED`; preserved ZIP `ivl35-train3763-3-e93478acca244e71a5194ddf1084d0f0.zip` (`2,070,012` bytes, SHA256 `38bb2698d11e23de93c71405ecbf6283437b573c53a6b624f0d26220d66fc60b`, 17 members) | 3 calls / 3 jobs / 10,800 physical GPU-s |

**Mandatory post-merge sequence (operator-only AFTER ChatGPT GitHub review, independent Antigravity audit, and separately authorized merge):**

1. **Reconcile and collect Attempt3 as terminal `FAIL` (never `abort-pre-submit`, never `PASS`):**
   Because `PUSH_INTENT` and `SUBMITTED` exist for Attempt3, `abort-pre-submit` is
   strictly forbidden (`POSSIBLE_SUBMIT_READ_ONLY_RECONCILIATION_ONLY`). From the
   clean merged `main` checkout, collect Attempt3 using its pinned historical
   `commit_sha` (`9f86424d14507fcc2fa08c2bf4a2f9a56e7dd481` via `git show`):
   ```powershell
   $OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
   $Ledger = 'data/processed/train3763-campaign/ledger'
   $Attempt3 = 'data/processed/train3763-campaign/attempt-3'
   # Resume saved conversation cb8d4344-29c4-47d1-a255-01573fe975a8; add -Recover ONLY if that conversation is unavailable.
   ./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action resume -Directory $Attempt3
   ./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action report -Directory $Attempt3
   ./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action status -Directory $Ledger
   ```
   Expected result: handoff report `status = "FAIL"`, `terminal = "COMPLETE"`,
   `collection = "FINISHED"`, `verification.status = "FAIL"`, `model_calls = 0`,
   `counts = {"NOT_ATTEMPTED": 3763}`; mirrored ledger appends `COLLECTED` closing
   Attempt3's open intent while keeping all 3 reserved calls, 3 jobs and 10,800
   physical GPU-seconds without refund. Any corrupt ZIP, wrong sidecar, missing
   provider log or identity mismatch stays `BLOCKED` with unchanged journals.
2. **Record new technical & audit attestations for the merged PR:**
   Obtain authentic `SAFESHIFT_TRAIN3763_AUDIT_V1` and `SAFESHIFT_TRAIN3763_TECHNICAL_V1`
   comments on this merged repair PR binding `runtime_commit`
   `f2346fae68022d0e032868b73e923458d8e55b2e`, `source_sha256`
   `deef3c26eb55e5fb7196cba96220a79a92a058f028cf957a390fad9e010d14ad`, execution
   notebook SHA256 `12fe3ca94e1e07b346d60a4581028a4cefa8ac9aa3b62d2ab00016cf18deb6e9`,
   and execution code SHA256 `f6a9c6dcaef2d99d6f25944c465a316592c0c36421cf5a2a0a46a244511adc66`
   under the unchanged PR181 campaign grant.
3. **Stage Attempt4 with `--mode resume --calls 1 --seconds 1800` (NOT `initial` or `repair`):**
   Once Attempt3 is `COLLECTED`, `ledger.histories()` has 1 sealed ancestor with
   `records = []` (0 consumed/failed samples, 3,763 `NOT_ATTEMPTED`). Therefore
   `--mode initial` is rejected (`NEW_SERIES_REQUIRED`), `--mode repair` is rejected
   (no failed sample targets), and `--calls > 1` is rejected
   (`FINAL_SOURCE_MEASUREMENTS_REQUIRED_BEFORE_SHARDS`). Prepare a fresh
   `context-attempt4.json` pointing to the new `technical_revision` and a new unique
   private capsule `nguynanhtn/<unique-attempt4-capsule>/1`, stage into a new
   `attempt-4` directory (`plan --mode resume --calls 1 --seconds 1800`, scheduling
   ordinal 0 and job `nguynanhtn/safeshift-train3763-ivl35-train3763-4`), upload the
   private capsule, run the read-only signed-download byte preflight below, and hand
   off only after `READ_ONLY_CAPSULE_BYTE_PASS`. Measure Attempt4's `PASS` archive
   before planning multi-call shards.

### Remaining live-only Kaggle risks and gates

Offline unit, installed-SDK, native-CPU `GenerationMixin` and Linux process-group
tests verify contract wiring, serialization and failure custody, but **cannot**
substitute for live Kaggle execution on:

- Live Kaggle container image/kernel updates, `/usr` or `/opt` Python binary paths,
  NVIDIA driver ABI (`libcuda.so.1`) and physical dual-T4 GPU0 placement at job start.
- Live Kaggle API / GCS signed-URL availability, network jitter, and server-side
  timeout/quota enforcement.
- Live T4x2 GPU FP16 weights load (`9.465 GiB`), cgroup page-cache reclaim above the
  `16 GiB` pre-load RAM floor, real image preprocessing and per-sample runtime/archive
  growth on the new `source_sha256` (`deef3c26eb55e5fb7196cba96220a79a92a058f028cf957a390fad9e010d14ad`),
  which remains `NOT_RUN` until 1-call Attempt4 completes and is `MEASURED`
  (even though all 84 inherited runtime/memory/grammar files match PR177 `04/11/2026`).

### Offline acceptance and immutable rebuild

Runtime changes were committed first at `f2346fae68022d0e032868b73e923458d8e55b2e`,
and both `PREP` and execution notebooks were rebuilt deterministically via the
unchanged committed-source builder (`build_internvl3763 --execute --campaign`),
preserving empty cell outputs, exact 90-file manifest embedding and unchanged
`science_sha256` (`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`).
Exact tested identities, commands, sanitized logs and remaining gates are bound in
the [PR177-parity E2E acceptance receipt](research/evidence/train3763_e2e_repair_20261107/summary.json).

Final offline acceptance on clean tested commit
`f98cb79a15197bd5bbf9be3f9882791457c7a7e8` (`tracked_dirty = false`):
**224 focused CPU/SDK/native-CPU tests (`223` PASS, `0` failures, `0` errors, `1`
Linux-only skip covered `5/5 PASS` with `0` skips by real WSL2 Linux process-group
`LauncherSupervisorSetupCompositionTests`), `3/3` notebook tests PASS, and `100`
distinct PR177 regression tests PASS (`88` Windows native-CPU + `22/22` WSL2 Linux
process/memory/streaming tests covering all `12` Windows POSIX skips).** Runtime
commit `f2346fae68022d0e032868b73e923458d8e55b2e`, `source_sha256`
`deef3c26eb55e5fb7196cba96220a79a92a058f028cf957a390fad9e010d14ad`; all 84
inherited PR177 files and 86 unchanged manifest files match BASE. All 3 PowerShell
wrapper scripts and all 9 PowerShell fenced blocks in this runbook parse cleanly.
Subsequent documentation/receipt publication changes only `docs/`, leaving tested
runtime source and notebooks byte-identical.

## Historical signed HTTPS443 capsule repair and Attempt2 recovery

[Official task, 06/11/2026](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6666341490),
BASE `46f0a318a2b822745e3e561869fa69570ac0c220` (PR183 merged), permits one
Draft PR for source, offline installed-SDK tests, rebuilt notebooks and this
handoff. No real Kaggle probe/upload/abort/stage/submit, GPU/inference or TEST
in this Codex task. Earlier repair sections are historical snapshots; their
Attempt1/Attempt2 instructions do not authorize replay of either attempt.

The pinned SDK's observed signed Location uses `https://storage.googleapis.com:443/...`.
`capsule_http()` now admits exactly `storage.googleapis.com` or
`storage.googleapis.com:443`, HTTPS only. The nonroot path/nonempty opaque query,
no userinfo/fragment/control/backslash, one exact DownloadDataset POST followed
by one isolated anonymous GET remain mandatory. All other ports/authorities,
redirect chains and retries are blocked. `bounded_http()` is unchanged; TLS,
`trust_env=False`, credentials isolation, finite time/byte bounds, create-only
partials, ZIP/CRC/exact bytes/SHA256 and Input/private-version checks still
precede any PUSH_INTENT or kernels_push. The synthetic signed URLs in tests
exercise installed SDK serialization/requests streaming, not a live provider.

### Reported operations state and mandatory transition

The official task relays Antigravity's operational report, not a fresh Codex
provider observation:

| Attempt | Reported state | Reservation retained |
| --- | --- | --- |
| 1 | ABORTED_PRE_SUBMIT; never submitted | 1 call / 1 job / 3600 physical GPU-s |
| 2 | INTENT; private capsule `nguynanhtn/safeshift-capsule-ivl35-attempt2/1`; no PUSH_INTENT or kernel submit reported | cumulative 2 calls / 2 jobs / 7200 physical GPU-s |
| 3 | NOT_CREATED; conditional after the gates below | cumulative 3 calls / 3 jobs / 10800 physical GPU-s |

Reported actual GPU consumption is 0; reservations are not measured billing.
Preserve the original PR181 grant/O2-O6, initialization guard, both journals,
all old capsules/versions, request/context/stage, errors, partials and reports.
No refund, ledger reset or source/capsule reuse. A merged fix does not make
Attempt2 runnable with new source. Science SHA256 remains
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.

After direct ChatGPT GitHub review, independent Antigravity audit, separately
authorized merge and verified postmerge, obtain genuine new AUDIT_V1 and
TECHNICAL_V1 attestations for this PR/exact merged source/runtime/notebooks.
Return operations to the same dedicated Antigravity Kaggle session and existing
canonical ledger/mirror; no new Owner grant is required inside unchanged caps.

1. Reconcile fresh authenticated read-only provider inventory, full pagination,
   exact version/checkpoint/Input identity and quota. Confirm Attempt2 still has
   no PUSH_INTENT, `nguynanhtn/safeshift-train3763-ivl35-train3763-2` is truly
   absent, no unexpected/active campaign job or reserved GPU quota, and complete
   matching journals/history. Any unknown submit/provider/history means STOP.
2. Only with that proof, use the existing `abort-pre-submit` command under its
   lock to close Attempt2 without refund. It repeats provider proof itself.
   Preserve Attempt2's INTENT, capsule, old source/context and all failed stages.
3. Prepare a separate `context-attempt3.json` using the authentic new technical
   revision and a different unique private capsule dataset slug/version1. Use a
   new `attempt-3` handoff. Never edit or reuse Attempt2's capsule or directory.
   `plan --mode initial --calls 1 --seconds 1800` must produce original TRAIN
   ordinal0 and job `nguynanhtn/safeshift-train3763-ivl35-train3763-3`. Confirm
   cumulative reservation3 calls/3 jobs/10800 physical GPU-s remains within the
   original grant/deadline. Upload only this new small private capsule through
   the existing authorized operator procedure; do not reupload data/checkpoints.
4. Perform the real signed-download preflight below before handoff. Submission
   then repeats all gates and byte proof before its only PUSH_INTENT/push. An
   unknown return stops for read-only reconciliation, never automatic retry.

### Real-provider read-only preflight before any job POST

Quota, SDK version and Input existence alone are insufficient. Check the exact
clean reviewed merged HEAD, authentic technical revision/grant/rights/caps/time,
complete mirrored intent/history/raw custody, provider absence/private pinned
versions/checkpoint identity, serial jobs and quota. Also exercise the real
DownloadDataset RPC -> signed HTTPS GCS Location (including explicit443) ->
anonymous GET and full byte/SHA256 proof against the exact request AND intent.
Retain only sanitized receipt/host/port/HTTP outcomes and proof hashes privately;
never print/log a signed URL, token or cookie. No fake adapter PASS is real-provider
evidence. This preflight makes metadata/download RPCs only, never SaveKernel or
kernel submission, model load or inference.

Boundary: a final Attempt3 request/intent and its capsule do not exist before
staging, and Attempt2's request has old source. Therefore all read-only gates
possible before staging must pass first; the exact new-capsule download proof
must be repeated immediately after Attempt3 staging/private upload, before any
PUSH_INTENT. The following block is **operator-only AFTER the preceding merge,
attestation and recovery gates**, never part of this Codex task. It uses existing
functions and a new temporary proof directory outside the preserved submission
stage; it neither appends to nor resets the ledger. SDK auth remains local.

```powershell
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Handoff = 'data/processed/train3763-campaign/attempt-3'
$ProofCode = @'
import json, sys, tempfile
from pathlib import Path
from safeshift import internvl3763_operator as op
from safeshift.kaggle_handoff import lock
from safeshift.pilot.artifacts import read, write
request = read(Path(sys.argv[1]) / 'request.json')
ledger = op.campaign_ledger(request)
with lock(ledger.root):
    before = ledger.events()
    grant, execution = op.admit_campaign(request)
    client = op.api()
    inventory = op.campaign_inventory(client, request, grant, ledger)
    intent = ledger.open_intent()
    proof_root = Path(tempfile.mkdtemp(prefix='capsule-readonly-', dir=Path(sys.argv[1]).parent))
    proof = op.verify_execution_input(client, request, intent, proof_root / 'download')
    assert ledger.events() == before
    write(proof_root / 'inventory.json', inventory)
    print(json.dumps({'status': 'READ_ONLY_CAPSULE_BYTE_PASS', 'proof': proof}, sort_keys=True))
'@
& $OperatorPython -B -c $ProofCode $Handoff
if ($LASTEXITCODE -ne 0) { throw 'STOP: retain proof/partials; no PUSH_INTENT or retry' }
```

Retain each proof directory, including failures/partials, in ignored custody.
The read-only preflight does not create submission/ or append PUSH_INTENT.
Do not remove an existing submission/ to retry; diagnose and reconcile under
the contract. Immediately before actual submission, the normal handoff still
rechecks inventory and exact capsule bytes under the campaign lock. No larger
shards before final-source ordinal0 terminal/raw/ZIP/time/VRAM/RAM evidence.
Monitoring stays <=15 minutes, then RUNNING_UNVERIFIED and resume the same session.

### Offline acceptance and immutable rebuild

Commit the runtime change first, rebuild PREP and execution with the unchanged
committed-source builder (`--execute --campaign`), then check empty outputs,
embedded manifest and deterministic bytes. Do not relax exact clean merged-HEAD
admission or edit inherited source/science/data locks. Acceptance identities,
commands, test counts and limitations are recorded in the
[HTTPS443 receipt](research/evidence/train3763_capsule443_20261106/summary.json).
Final-source live-provider/GPU verification, direct review, independent audit,
merge and actual Attempt2/Attempt3 operations remain NOT_RUN/PENDING here.

Final offline acceptance on clean tested commit
`8803a5583d62d06760fb9bc5e9fb19e453d8ab4f`: **213/213 CPU/SDK PASS, notebooks3/3
PASS**, no skips/failures/errors, including20 capsule tests. Runtime commit
`e51211cbeda58a2ed4bea65c700adf36b743b973`, source SHA256
`95857891faf5e8da623ea408f580c899430e4bc464665d128f086575cea76f37`.
All84 inherited files and all89 other manifest files match BASE; each rebuilt
notebook changes only the operator inside its payload. The new PowerShell block
parses, and its embedded Python passes synthetic installed-SDK/adapter rehearsal
with sockets forbidden, no journal mutation and no push. Published sanitized
logs/receipt bind the commands, dependencies and identities. Full-repository
smoke/CI and real-provider PASS are not claimed. Later publication changes only
documentation/evidence; source/notebooks remain those tested.

## Historical pinned GetKernel HTTP404 repair

[06/11/2026 task](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6664802285),
BASE `bce8725047753415aa65ed28fc79ef04131fe366` (PR182 merged), fixes only a
diagnosed SDK version-label blocker. The capsule302 section below records the
previous repair. No live Kaggle action is permitted in this PR, including
read-only probes, uploads, aborting actual Attempt1 or staging Attempt2.

`kernel_version_label()` accepts only canonical positive decimal integers or
strings and produces `vN`. Both pinned `GetKernel` callsites use it: versioned
`kernel_sources` (the existing `nguynanhtn/safeshift-prepare-internvl35/1`) and
legacy witness predecessors. The SDK RPC receives `versionLabel: "v1"`, while
Input locators and `kernels_status` keep `/1`. Missing, zero, boolean, fractional,
negative, noncanonical or pre-prefixed versions are rejected. Never omit the
field, catch404 as absence, substitute latest, or add an API retry.

Returned metadata must match the exact ref, numeric version and private flag;
the Input must be COMPLETE, and a predecessor must be terminal with exact code.
Unknown/missing metadata/state remains blocking. Other related GetKernel calls
in `campaign_inventory` and handoff collection deliberately observe latest to
detect unexpected new job versions, then require the recorded version/identity.
They contain no numeric `version_label` assignment and are not a fallback for
pinned calls. Those legacy/shared implementations and the no-redirect/zero-retry
transport are unchanged. The new next-job regression retains the version2 drift
guard and rejects missing provider history before scheduling.
Installed Kaggle2.2.5 `kernels_status` and `kernels_output` both call their own
`_kernel_version_label` helper; source inspection and actual helper outputs1->v1,
12->v12 are recorded in the receipt. Those SDK routes need no source change.

`test_internvl3763_versions` uses installed Kaggle2.2.5/kagglesdk0.1.38/
requests2.34.2, real request serialization and an offline HTTP adapter with
sockets forbidden. Its synthetic endpoint returns404 for raw `"1"` or a missing
label and200 for `"v1"`; success still requires version1 metadata. It covers the
full `campaign_inventory`/`pre_submit_inventory` paths after provider absence,
both original assignments, malformed versions, ref/private/code/version drift,
nonterminal/unknown state, full pagination, unexpected/missing campaign jobs,
quota, grant drift, timeout/no retry and PUSH_INTENT exclusion. Synthetic aborts
append only after complete valid proof and never refund reservations. The
actual campaign is not used as a test fixture. A skipped SDK suite is not proof.

```powershell
# Offline only; reuse the installed isolated operator SDK. No credentials needed.
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
& $OperatorPython -B -m unittest discover -s tests -p test_internvl3763_versions.py -v
& $OperatorPython -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
```

The focused qualification runner now includes the version transport suite and
its test hash. [Acceptance receipt and test logs](research/evidence/train3763_versionlabel404_20261106/summary.json)
bind exact tested commit, SDK/environment, commands, notebook/code/source hashes,
unchanged science and local custody. Full-repository smoke is not repeated:
PR182 already documents unrelated historical baseline failures/incomplete smoke;
this PR makes no whole-repository or CI PASS claim.

Final acceptance on clean tested commit `39c5d231bc5a8f72879229e4a3cc2c401e1ba244`:
206/206 CPU/SDK tests PASS (17 new version tests, including15 installed-SDK
transport tests), notebook3/3 PASS, no skips/failures/errors. Runtime commit is
`734be541899e1ac59738efef196e5e858ec5b1ea`; source SHA256 is
`ed3b696b8fd76c542df4424e382fc35ac43c5f7b5581c10394a3ea4c584d4667`.
Only the operator file changes in the runtime manifest; all84 inherited files
match BASE. The17 actual campaign metadata files retain identical before/after
aggregate SHA256, including grant, mirror/guard, Attempt1 and capsule. The
preliminary206-test run had one exact-source error while source was being
finalized; its log is preserved, excluded from acceptance and superseded by the
clean final run. Subsequent changes publish only these documents/test receipts.

The committed-source builder is unchanged: commit runtime source first, build
both notebooks from that exact40-character commit with `build_internvl3763`
(`--execute --campaign` for execution), then compare embedded manifest, empty
outputs, notebook/code hashes and reproducibility. Never modify frozen inherited
runtime/config/science locks. Exact clean merged-HEAD admission still rejects an
unreviewed HEAD, changed notebook/source or stale technical revision. Science SHA
remains `ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.

Keep the authentic PR181 campaign grant and O2–O6 unchanged; keep Attempt1,
capsule, ledger/mirror/guard, errors and all charged calls/jobs/GPU-seconds.
This PR stops at one Draft for direct ChatGPT review, independent Antigravity
audit and separate merge authorization. After verified merge, authentic new
technical/audit records must identify this repair PR and exact merged code.
Only the existing Antigravity operations session may then perform fresh live
provider-absence, quota, pinned-version and checkpoint-byte reconciliation under
the same grant before the separately gated no-refund abort/new unique capsule/
Attempt2 workflow below. Any provider/version/history ambiguity means STOP.
No final-source Kaggle, GPU/model, scientific qualification or TEST PASS is
inferred from the offline tests.

## Historical capsule HTTP302 repair and Attempt1 recovery

[Owner task / ChatGPT diagnosis](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6662845867)
starts at BASE `2484095e7b29c3c1d5ad79f18523cfa8dd6a0cac` (PR181 merged).
The original [Owner O2–O6 scoped decision](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6657871236)
and authentic PR181 campaign grant remain the execution authority inside their
unchanged science/rights/caps/deadline. This repair issues no authority and runs
no Kaggle operation, including read-only provider probes, uploads or smoke.
The earlier no-grant/CPU acceptance paragraphs below are historical PR181 snapshots.

### Transport contract

`bounded_http()` is unchanged: metadata, auth, logs, POST/kernel submission and
legacy traffic never gain automatic redirects. Only `verify_execution_input`
wraps the pinned SDK `DownloadDataset` RPC for the exact owner/slug/version/file.
Its POST body is checked against the SDK serialization; an HTTP302 may produce
exactly one **new GET** to `https://storage.googleapis.com` with a nonempty query.
No POST body, Kaggle Authorization/cookies/headers, netrc, proxy credentials or
client certificates reach storage. Other schemes/hosts/ports/userinfo/fragments,
relative URLs, control characters, further redirects and non200 storage responses
fail closed. A new storage host requires a reviewed explicit allowlist change.
TLS verification stays enabled. The signed URL is used opaquely and is never
recorded; download exceptions are replaced without a chained sensitive traceback.

Both requests retain zero adapter retries and10s connect/30s read timeouts.
The writer has no retry/resume loop, caps streamed bytes at64MiB and checks a90s
monotonic budget before every64KiB write and after completion. A blocked read is
additionally bounded by its30s timeout; the90s check is not a hard subprocess kill.
It fsyncs the create-only `download.part` and preserves it on failure. File type
is detected from bytes, never an untrusted URL/filename. Plain JSON must match
the exact size/bytes; a ZIP must have exactly the named capsule, exact uncompressed
size and valid CRC. SHA256 and exact request/intent proof precede PUSH_INTENT and
the only `kernels_push`. The SDK's separate default five-retry file writer is
not called. SDK verbose logging is forbidden during this download.

### Preserve, reconcile, then stage separately

Read-only local inspection in this task found matching root/mirror/guard and one
INTENT, no PUSH_INTENT: job `safeshift-train3763-ivl35-train3763-1`, source
`b571c356361f428eb69278c569bf52a90f362f562b7a3837937dad76f77c1e9c`,
intent `15528ad3f88997fa19416a8dfc8e214eb04a887ff93aaa5c536de287aae8f8f6`.
Attempt1 reserves1 call,1 job and3600 physical GPU-seconds. Its local capsule is
5,630,833 bytes. These are local custody observations, **not provider job absence**.
Nothing in the actual campaign ledger, guard, grant, context or capsule was changed.

Keep the same Antigravity operations session and canonical ledger/mirror paths
from its existing registration. Preserve every existing `submission/`, download
partial, handoff event, report, original private capsule/version and all journals.
An existing submission directory now stops with an explicit preservation error;
never delete/rename it to make an old attempt runnable. `plan` also rejects an
existing handoff before reserving budget. Every attempt requires a new capsule
dataset slug; neither an old capsule nor its newer version can replace Attempt1.

This patch changes operator/campaign source SHA and therefore requires a new
committed runtime, rebuilt PREP/execution notebooks, notebook/code hashes and
technical revision on **this repair PR**. The exact merged HEAD check and source
checks remain enforced. After real ChatGPT review, independent Antigravity audit,
separately authorized merge and verification, retain the PR181 grant locator and
obtain authentic `SAFESHIFT_TRAIN3763_AUDIT_V1` / `TECHNICAL_V1` records for this
new source/regression/runtime/notebook identity. Synthetic test attestations are
not operational evidence. Old Attempt1/context/technical attestations stay frozen.
Science SHA must still equal
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`.

Only after those technical gates may Antigravity run the existing CLI below.
`abort-pre-submit` now authenticates the original grant and checks complete owned
provider inventory, exact absence of the old job, all prior campaign jobs and
zero GPU reservation **under the ledger lock**, before appending mirrored
ABORTED_PRE_SUBMIT with the hash-bound inventory proof. Timeout, existing/unknown
job, pagination/history drift, nonterminal prior job, unknown consumption or any
PUSH_INTENT stops read-only; no abort/refund/new intent follows. It checks the old
request for custody without pretending its source is valid at the new HEAD.

```powershell
# AFTER review/audit/authorized merge only; uses existing operator/session/paths.
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Ledger = 'data/processed/train3763-campaign/ledger'
& $OperatorPython -B -m scripts.train3763_campaign abort-pre-submit --directory $Ledger
# Success is a new ABORTED_PRE_SUBMIT; original INTENT and all charges remain.
# Prepare context-attempt2.json separately with authentic new technical_revision
# and a unique private capsule slug/version. Keep the original context untouched.
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant data/processed/train3763-campaign/grant-locator.json --template data/processed/train3763-campaign/context-attempt2.json --cohort data/processed/train3763-campaign/cohort.json --handoff data/processed/train3763-campaign/attempt-2 --mode initial --calls 1 --seconds 1800
```

With no native job/history, Attempt2 is initial qualification on ordinal0, not
repair of a consumed image. Both attempts retain3763 IDs/order and immutable
lineage; combined reservation is2 calls,2 jobs,7200 GPU-s, with no refund for
Attempt1. Full shards remain blocked until new-source native measurements.
No renewed Owner grant is needed for this technical fix inside existing caps.
This task does not execute either command or close the real Attempt1: provider
absence, final-source live verification and real technical attestations remain
BLOCKED / NOT_RUN pending the permitted operations workflow.

### Checkpoint discrepancy

Attempt1's stored request, the frozen runtime descriptor and #173's saved marker
all identify `OpenGVLab/InternVL3_5-4B-HF`, revision
`6bd4487402110ef9889ba50eb7aefeb302526fed`, mounted from
`nguynanhtn/safeshift-prepare-internvl35/1`. The approved lock and
[actual historical byte receipt](research/evidence/issue173/checkpoint-bytes-v1.json)
agree on both shards: `337d6d5bea97956480a1560c3a88e4e6c4455c3954b94ed468c367cf4b500f20`
(4,954,007,064 bytes) and `343234927f41c7d3a4aa8a2280864f477b1f77795463feb6b26910fa2e4921d3`
(4,511,078,400 bytes); index `4f5f24a16dc7fcba6edeb8df8482f633b369c284685f92c6e3d6069ee3b323e1`.
There is no `InternVL-Chat-V1-5` configuration in this campaign. The reported old
name conflicts with the stored request and verified historical bytes. A current
exact private provider source snapshot is not available in this task, so calling
it a proven report typo would overstate the evidence. Antigravity must reconcile
that label against retained exact source/version/marker/shards before submit;
unresolved identity or different bytes means STOP, never silently change model.

### Repair validation

The regression suite uses installed official SDK0.1.38/requests2.34.2 with a
requests HTTP adapter stub and actual file/ZIP streaming. Sockets are prohibited.
Run it in the existing operator environment, then the campaign/controller/
execution/handoff suites and deterministic notebook rebuild tests. The updated
`scripts.qualify_internvl3763` includes `test_internvl3763_capsule`; a skipped SDK
suite is not HTTP302 proof. [New repair receipt and logs](research/evidence/train3763_capsule302_20261105/summary.json)
record189/189 CPU tests PASS, zero skips/failures/errors, including13 transport
tests; notebook3/3 PASS. Clean tested HEAD is
`d961d3c04f0b36f110ff5954f23e60e9ee021829`, runtime
`216e94bc1a57d7a6715183300ed8088496868417`, source
`649102f0a4c2a13d87044f3a4c9a7316d9b6d9dee71ebc3ddbacfd196c816934`.
All84 inherited runtime files and shared transport match BASE. Repo-wide smoke
is incomplete (600s stop requested, sandbox denial delayed verified process stop
to about703s); official-FP329 tests with1 failure/9 errors and Candidate160-
notebook4 tests with1 failure/1 error reproduce identically on pristine BASE and
this branch. No whole-repo or CI PASS: GitHub Actions has0 configured workflows.
PR181's historical receipt remains unchanged. Live recovery/source qualification,
independent audit and authorized merge remain separate pending gates.

## Historical PR181 implementation contract and acceptance

Design recorded before implementation. BASE: `300fc4e305ffa6f1fed9b86ebfedbc996bc9dde2`.
This PR authorizes code and synthetic CPU checks only. No live Kaggle, GPU,
private raw, TEST, campaign grant or numerical execution budget is issued here.

One authentic Owner campaign record will bind the original3763 projection,
master/Input/checkpoint/method/rights, one operator machine, finite calls/jobs/
physical-GPU seconds/deadline, per-job ceilings, stop rules and technical-fix
policy. Attempts are derived locally inside those caps; no per-job Owner
comment is required. Scientific and third-party decisions remain separate.
The old per-attempt/HTTPS route remains a historical compatibility route;
its grants and consumed claims cannot migrate into a new campaign.

The new route has one serial operator and two create-only journal copies on
separate local custody directories. Every intent is fsynced to both before
the single provider push. Partial writes, divergent copies, unknown submission,
missing ledger/history, provider identity drift, active jobs, corrupt export or
unreconciled calls stop scheduling. Locks cover all mutations. No automatic
POST retry, reclaim, refund or takeover. A full coordinated rollback of both
copies cannot be detected offline; retain independent provider/ZIP/checkpoint
custody. This design does not claim global exactly-once against another machine,
manual notebook replay, administrator tampering or lost custody. Cross-machine
takeover is blocked until the previous operator is fenced and its complete
hash-checked journals and provider history are reconciled read-only.

Resume schedules only NOT_ATTEMPTED from complete sealed lineage. Repair is a
separate action with exact error record hashes, diagnosis, fix and regression
hashes; SUCCESS is never repaired. Technical source versions require reviewed,
merged source and independent audit evidence under campaign-selected reviewer
identities, not renewed Owner execution approval. Frozen scientific bytes and
method identity must match. Every attempt retains its own3763 records; operational
coverage is not scientific output selection, pooling or a claim of100% SUCCESS.

First authorized final-source qualification is ordinal0/one call. Later shard
caps require measured final-source duration, GPU/RAM and archive/raw sizes from
that sealed job. Conservative local storage gates remain in force. Historical
941/941/941/940 is precedent, never a hardcoded shard size or new result input.

Antigravity uses the existing official SDK and foreground conversation handoff.
Monitor at most15 minutes, save RUNNING_UNVERIFIED and exit; Kaggle continues.
On the next user message resume the saved conversation, inspect exact terminal
version, collect ZIP/sidecar/log and validate custody. Preserve FAIL/BLOCKED and
give Codex a bounded diagnostic handoff. No background AI or automatic submit
from a collection operation. The runbook and acceptance receipt are completed
in this same PR after tests.

## Authority records and migration

`internvl3763_campaign.load` authenticates one UTF-8/SHA-pinned Owner GitHub
comment on this merged implementation PR, marker
`SAFESHIFT_TRAIN3763_CAMPAIGN_V1`, followed by one fenced JSON object. The strict
schema is `safeshift-train3763-campaign-v1`:

| Fields | Required meaning |
| --- | --- |
| campaign_id, operator_id, operator_root_sha256 | Safe IDs and hash of canonical ledger location plus machine identity. `identity` prints the hash without publishing personal paths. Another directory/host cannot initialize the same grant. |
| authorization | `GRANTED_FOR_BOUNDED_CAMPAIGN`, issued by the Owner after real decisions. |
| implementation_pr, reviewed_head, merged_sha | This merged PR, exact reviewed HEAD and actual merge SHA on main. No PR177–179 grant reuse. |
| science_sha256, cohort_sha256, input_marker_sha256 | Frozen science fingerprint, original3763 projection and exact original `master_manifest.json` bytes SHA (the locked MASTER_SHA, not a newly invented fulltrain marker). No labels/GT are embedded in plans. |
| inputs | Exact immutable `dataset_sources` and `kernel_sources`, including existing original data/master/checkpoint mounts. New small execution capsules may be added only under the existing Owner account. |
| rights | O2–O6, each with actual `status`, HTTPS `ref`, content `sha256`. Accepted statuses are APPROVED or NOT_REQUIRED_WITH_BASIS. No automatic waiver or PENDING-to-approved conversion. A reference is an attestation, not a forged third-party signature. |
| review_logins, audit_logins | Principals allowed to attest technical review and independent audit. These roles cannot issue more campaign budget. |
| issued_unix, expires_unix | Finite campaign window, maximum366 days. Collection remains possible after expiry. |
| caps | Positive integers: total_calls, total_jobs, total_gpu_seconds, job_calls, job_seconds, archive_bytes, physical_gpus=2, max_repairs_per_image; machine_shape=NvidiaTeslaT4. Job <=43200s, archive <=7GiB. The Owner supplies actual values; this PR supplies no executable budget default. |
| policy | Exactly serial=true; resume=NOT_ATTEMPTED_ONLY; repair=DIAGNOSED_TECHNICAL_ONLY; technical_fixes=REVIEWED_MERGED_SCIENCE_UNCHANGED; ambiguous=STOP_READ_ONLY; refund=false; test=false; scientific_selection=PENDING; pooling=false. |

Technical source qualification is separate from execution permission. A comment
by a campaign-authorized reviewer on the merged source PR uses marker
`SAFESHIFT_TRAIN3763_TECHNICAL_V1`, with campaign_sha256, science_sha256,
implementation_pr, reviewed_head, merged_sha, runtime_commit, source_sha256,
notebook_sha256, notebook_code_sha256, regression_sha256 and an `audit` locator
(`comment_id`, `body_sha256`). The independent audit comment on that same PR uses
`SAFESHIFT_TRAIN3763_AUDIT_V1` with campaign_sha256, reviewed_head, source_sha256,
regression_sha256, status=PASS and independent=true. Both comments are authenticated
by author/ID/body hash and exact merged PR. These are recorded attestations of
actual reviews, not proof generated by the runner that an audit happened. Initial
and subsequent technical versions use this same route; no new Owner campaign
comment is needed. Semantic source changes fail the frozen science fingerprint.

Old release V1 and SQLite/HTTPS witness code remain unchanged in purpose and
retain compatibility tests. The published execution notebook now uses campaign
admission; the builder's legacy `--execute` without `--campaign` only reproduces
the former route. A legacy grant cannot activate campaign mode. Old source locks,
consumed markers and historical result series are never rewritten or imported.

## PowerShell runbook (after review/audit/authorized merge only)

Run from the exact reviewed merged source checkout. Reuse the existing isolated
operator environment and Antigravity account connection. Do not create a new
environment or reauthenticate merely because a new shard is starting. If the
environment is absent, the existing `prepare_train3763_operator.ps1` provisions
the approved pins in a new ignored directory; it does not authenticate or submit.
No command below is executed against Kaggle by this implementation PR.

```powershell
$OperatorPython = './data/processed/operator-venv/Scripts/python.exe'
$Ledger = 'data/processed/train3763-campaign/ledger'
$Mirror = 'data/processed/train3763-campaign-custody/mirror'
$GrantLocator = 'data/processed/train3763-campaign/grant-locator.json'
$Cohort = 'data/processed/train3763-campaign/original-projection.json'
$Context = 'data/processed/train3763-campaign/context.json'
& $OperatorPython -B -c 'from safeshift.internvl3763_operator import check_sdk; print(check_sdk())'
& $OperatorPython -B -m scripts.train3763_campaign identity --directory $Ledger
```

Antigravity first checks existing versioned `inspecsafe-v1-kaggle`,
`safeshift-pilot-input` and the checkpoint Input from #173 read-only, account job
state/quota and local output custody. Reuse exact existing bytes/mounts; never
reupload images/checkpoints merely to match a new slug. #173 and PR177 identify
both checkpoint shard hashes and the successful runtime, not authority for this
new source. Reuse #173's private `ordered-projection.json` as `$Cohort` after
checking its recorded SHA, rather than regenerate metadata from annotations.
The campaign worker discovers the existing `master_manifest.json`, checks its
locked original MASTER_SHA, then calls the unchanged #173 `verify_train` against
`inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train/DATA_PATH`. Only original
master-listed `train/Annotations/*.jpg` locators are hashed/opened; TEST and
annotation sidecars are never enumerated. This route needs no
fresh_fulltrain_input.json, opaque images/ copy or new3763-image upload. The
legacy candidate route retains its packed-Input contract. Only already permitted
original TRAIN metadata may supply `$Cohort`.
The one campaign grant is issued after the remaining real rights/budget/stop-rule
questions are settled. Missing rights outside Owner authority require that actual
authority; the runner cannot infer them. Save its authentic locator privately.

`context.json` has exactly `technical_revision` (comment_id/body_sha256 of the
technical qualification above) and `execution_input` with `kind` equal to
dataset_sources and `ref` equal to the planned immutable
Owner-private capsule Input version, e.g. `nguynanhtn/<capsule-slug>/1`. It contains
no grant override or budget. Commit/runtime/notebook/source/plan/job IDs are derived
by the staging command. Use a unique small capsule slug/version per attempt;
it is separate from all existing data and checkpoint Inputs.

```powershell
# Once per campaign. Use the exact operator_id chosen in the authentic grant.
$ApprovedCampaign = & $OperatorPython -B -c 'import json,sys; from safeshift.internvl3763_campaign import load; from safeshift.pilot.artifacts import read; print(json.dumps(load(read(sys.argv[1]))))' $GrantLocator | ConvertFrom-Json
& $OperatorPython -B -m scripts.train3763_campaign init --directory $Ledger --mirror $Mirror --grant $GrantLocator --operator-id $ApprovedCampaign.operator_id
$JobSeconds = $ApprovedCampaign.caps.job_seconds
$Handoff = 'data/processed/train3763-campaign/attempt-1'
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $Handoff --mode initial --calls 1 --seconds $JobSeconds
```

Staging writes a durable mirrored intent and `$Handoff/package/` containing only
`safeshift_train3763_execution.json`. It does **not** upload or submit. The capsule
binds exact grant/request/source/history/limits and intent. Keep the whole handoff,
mirror and initialization guard; do not upload the handoff directory, CLI logs,
raw ZIPs, credentials or ledger. Prior archives remain in checked local custody
and their original Kaggle Outputs; every local archive/sidecar is revalidated
before admission. The worker trusts this sole operator's hash-bound scheduling
lineage rather than reuploading every historical raw ZIP. Each new ZIP still
contains all3763 status rows. History projection omits only NOT_ATTEMPTED rows to
bound capsule size; those remain pending in the full cohort.

Antigravity uses the existing official private Input upload procedure with the
exact version in context. For a **new** small capsule dataset, put matching
dataset-metadata.json (`id`, `title`, one actual license descriptor for this
Owner-controlled capsule) in package/ and use the pinned official CLI:

```powershell
# Default is private. Never add --public; never change existing dataset privacy.
& $OperatorPython -m kaggle datasets create -p "$Handoff/package" --keep-tabular
# Inspect the actual version/files read-only; mismatch or ambiguous upload is NO-GO.
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action handoff -Directory $Handoff
```

The operator checks pinned SDK, clean merged source/notebook, original Input refs,
complete ledger/raw custody, all known campaign jobs terminal and exact private
versions/code, absence of unexpected campaign jobs, and zero reserved quota plus
enough available quota before its only push site. It also checks capsule privacy,
owner, exact version/file/size and downloads only that small metadata capsule to
compare every byte against the current request/intent before PUSH_INTENT. This
prevents a stale otherwise-valid capsule replaying prior images on a fresh VM;
no image, raw or checkpoint download is needed for this check. Server timeout reserves both
physical T4s without refund; native worker remains GPU0. Do not issue another
submit after timeout. Inspect the exact target job/version read-only instead.

RUNNING_UNVERIFIED is the expected handoff checkpoint. End the AI turn; the
Kaggle job continues independently. When Owner reports completion or asks for
status, resume the same conversation:

```powershell
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action resume -Directory $Handoff
./scripts/kaggle_handoff.ps1 -Python $OperatorPython -Action report -Directory $Handoff
./scripts/train3763_campaign.ps1 -Python $OperatorPython -Action status -Directory $Ledger
```

Use `-Recover` only when the conversation is unavailable; it permits read-only
collection, never submission. Terminal collection requires the exact provider
version/private notebook/Inputs/GPU identity, provider log, ZIP+sidecar, SHA/CRC/
members, raw vectors/masks/trace/counts, source/plan and local native claims.
Successful collection closes the intent even when an intact archive reports
technical FAIL; evidence corruption/missing raw/unknown calls stays BLOCKED.
Recollection is idempotent. It does not refund budget or schedule another job.
Collection checks the job's notebook from its pinned Git commit, so a later
reviewed operator update cannot silently substitute its own notebook. Keep the
original Git objects and all local artifact paths available.

Before shards, use the exact collected final-source archive:

```powershell
& $OperatorPython -B -m scripts.train3763_campaign measure --directory $Ledger --archive $CollectedArchive --seconds $JobSeconds
# safe_calls/minimum_seconds come from this sealed native telemetry, within grant caps.
# Update context to the next private capsule Input; preserve its earlier versions.
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $NextHandoff --mode resume --calls $MeasuredSafeCalls --seconds $JobSeconds
```

Measure records setup/load/sample latency, GPU peaks, process/cgroup/RAM, float32
raw bytes and ZIP/sample sizes. The bound uses twice observed latency, conservative
uncompressed capture sizes and export margin. This is engineering planning;
one image cannot prove worst-case fit. The existing per-call time/storage gates
still stop before the next call. A source revision must be qualified/measured
again before a larger shard. There is no hardcoded941 or throughput claim here.

After an intact technical failure, Antigravity gives Codex the exact request/
intent/source/archive hashes, terminal provider identity, log paths, error stage,
all status counts and remaining caps. Codex diagnoses and tests the fix, keeps
the same science and obtains technical review/independent audit/merge. Refresh
context's technical_revision and notebook/source identity. A `repair.json` has
exactly targets (sample ID -> failed record SHA256), fix_sha256 (reviewed source
spec digest), regression_sha256 (reviewed regression receipt) and diagnosis.
Only errors are eligible; stale targets or SUCCESS are rejected. Then:

```powershell
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $GrantLocator --template $Context --cohort $Cohort --handoff $RepairHandoff --mode repair --repair $RepairRecord --calls $RepairCalls --seconds $JobSeconds
```

The same campaign grant remains valid inside its caps. No Owner reapproval for
this technical repair, next shard or continuation. Never expand science, TEST,
budget or rights to get PASS. Archive every new attempt separately; repair does
not decide scientific output selection. Report actual coverage/INVALID/errors
and all lineage, not a fabricated3763/3763 SUCCESS total.

## GO/NO-GO and recovery

| Condition | Required action |
| --- | --- |
| No campaign grant, unknown real rights, budget absent/exhausted, expired execution window | STOP; settle only the actual missing campaign/authority decision. Read-only collection is still allowed after expiry. |
| Known current job RUNNING/QUEUED | Save RUNNING_UNVERIFIED, exit AI; resume the same conversation later. No next job. |
| Push timed out/crashed or provider state/version unknown | Keep intent/PUSH_INTENT/reservations; read-only exact-job reconciliation. Never retry, switch slug or create version2. |
| ZIP download partial/corrupt/missing sidecar/raw/log | Keep all partials; later collection uses a fresh directory. No next attempt until custody verifies. Hard-kill without recoverable evidence stays BLOCKED. |
| Source/runtime/Input/package mismatch | Fix/qualify the technical cause; do not change scientific pins. If PUSH_INTENT exists, reconcile before another attempt. |
| Staging/provision preparation failed before any PUSH_INTENT | `abort-pre-submit` can close only a proved never-pushed local intent; it does not refund calls/GPU/job budget. Stage a new attempt under the same campaign. |
| One journal rolled back, diverged, missing guard or lost ZIP custody | STOP. Restore exact original files from independent retained custody and reconcile provider history. Never init an empty replacement ledger. |
| Both journals/guard lost, unknown older jobs, or cross-machine takeover | STOP/read-only recovery. Fence the old machine/worker, obtain all original custody and review the concrete migration; this version supplies no automatic takeover command. No claim of global exactly-once. |

The canonical machine/path binding prevents a second local authority. An
initialization guard outside both journal directories prevents empty reinit when
both directories disappear. Live provider inventory detects orphaned campaign
jobs after local rollback. These checks cannot prove integrity after deliberate
coordinated destruction/rollback of every local and provider evidence source.
Do not represent a local hash chain as an external immutable witness.

## Reused evidence and validation

- [#173 checkpoint custody](KAGGLE_CHECKPOINTS_173.md) and [PR177 ordinal0 report](INTERNVL_V2_VERIFIED_ORDINAL0_20261104.md): reuse checkpoint/runtime/Input and RAM-repair experience; no new-source GPU PASS claim.
- Qwen2.5 four shards941/941/941/940: [historical Linux audit at exact31a04e6](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/pa3_r2_cpu_completion_20261015.md).
- [Seminar protocol](research/SEMINAR_PROTOCOL.md) and [results/limitations](RESULTS_AND_LIMITATIONS.md): Qwen3 original3539 SUCCESS/1 error/223 pending, separate Recovery224; InternVL3 saved-score3763 rows. Only operational shard/custody precedents, no new predictions or scientific pooling.
- Inherited84 runtime files, prompt/parser/grammar/model/config/checkpoint locks are compared with exact BASE. Current notebook and PREP rebuild deterministically from committed source with empty outputs.
- CPU reproduction: `python -B -m scripts.qualify_internvl3763 --output data/processed/campaign-cpu-new`; notebook tests separately: `python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v`. Optional native/SDK CPU checks use the already installed pinned environments, no network/weights/GPU.
- Final sanitized receipt records exact tested source, environment, commands, counts, source/notebook/test/log hashes and baseline limitations. Live final-source Kaggle/Inputs/quota/weights/inference/export, independent audit and scientific qualification remain NOT_RUN/PENDING in this PR.

## Final acceptance — 05/11/2026

[Sanitized receipt](research/evidence/internvl3763_campaign_20261105/summary.json):
**172/172 CPU tests PASS, zero skips/failures/errors**, including actual installed
CPU GenerationMixin capture/replay and pinned official SDK serialization, private
capsule version/bytes, ambiguous submit, duplicate/process exclusion, rollback/
loss, quota, crash, ZIP/raw custody, original mounts, repair and source revision.
Notebook3/3 deterministic rebuild/empty-output checks PASS. PowerShell5.1 parses
all3 scripts and6 runbook blocks; actual identity and synthetic report wrappers
PASS. No new actual Antigravity AI turn was run; subprocess/conversation behavior
is covered by contract tests and prior actual CLI evidence remains historical.

Runtime commit `8a0a26e103230946f24bc3b01e69c7d244f20bb5`; source-spec SHA256
`b571c356361f428eb69278c569bf52a90f362f562b7a3837937dad76f77c1e9c`.
All84 inherited runtime files match BASE; approved generation, native backend/
image preparation, trace binding and configuration AST match BASE exactly.
The full repository smoke was bounded to600s and remains incomplete, not PASS.
Official-FP32's9-test suite independently reproduces identical1 failure/9 errors
on pristine BASE and this branch. Historical locks/configuration remain unchanged.

Only current implementation/code review is ready. No live Kaggle submit/upload,
GPU, real model/image/private raw or TEST access occurred. Campaign grant/caps/
genuinely missing rights, direct ChatGPT review, independent Antigravity audit,
authorized merge and subsequent bounded final-source qualification remain open.
