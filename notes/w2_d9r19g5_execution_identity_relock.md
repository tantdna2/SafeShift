# G5 execution identity relock PREP

Date: 2026-10-04. Task:
`W2.6-D9R19G5-MULTICATEGORY-EXECUTION-IDENTITY-RELOCK`.
Branch: `w2.6-d9r19g5-execution-identity-relock`.
Fetched origin/main / EXECUTION_BASE:
`b3bf4dc770c1b87a9e353a75aab759f67641c2c2`.
[G4 PR #71](https://github.com/tantdna2/SafeShift/pull/71) is MERGED at that commit,
verified read-only through GitHub. DECISIONS/TASKS append closure; original G4
MERGE=NO, old BASE, NOT_RUN, unauthorized/unverified records remain historical.

## Identity and preservation

The G4 guard requires main `685021ef974cc3feef968d7e920e7720ce6349f2`;
it is BLOCKED after merge. Any authority bound to that main is invalid now.
The new [runtime lock v2](../configs/pre_freeze/grounding_multicategory_runtime_lock.v2.json)
binds the current G5 runner/CLI, unchanged G3 plan/manifest/sources/parser/geometry,
G4 result schema and environment contract, historical runtime lock v1, and
the [execution plan](../configs/pre_freeze/grounding_multicategory_execution_plan.v1.json).
It also records hashes of the G4 runner/CLI/schema Git blobs at EXECUTION_BASE.
Text hashes use Git-normalized LF; snapshot/raw hashes use exact bytes.

Only live runner governance changes: BASE/lock selection, plan/run identity,
strict descendant (HEAD cannot equal BASE), observation Git checks before torch,
observation provenance, and distinct normalized reviewer identities. CLI adds
the predeclared observation run-ID check; G4 tests use the G5 run ID in their
fake authorization fixture. Historical G3/G4 evidence/config/note files remain
byte-unchanged, including environment.v1 and runtime_lock.v1. The old executable
versions remain accessible as Git blobs; live runner/CLI changes are explicitly
allowed governance edits, not a rewrite of their historical verification status.

No scientific change: same 12 positive synthetic cases, four-label query,
parser, geometry, greedy max_new_tokens=512, no retry/repair, raw-before-parse,
and human NO_GIANT review of every detection. NativeRuntime, persistence, call
lifecycle, result writer and finalization code are unchanged. Runtime cannot
auto-award PASS. Neither role nor absence semantics is promoted.

HEAD is read from Git, never hard-coded before commit. After push, the final
report and Draft PR identify the exact SHA for independent audit. The future
authority must bind that SHA, fixed main, model, predeclared run ID, environment
hash and runtime lock v2 hash. Any subsequent commit requires a new exact-HEAD
audit/observation/authorization; do not reuse a previous approval.

## Keep the Draft PR OPEN

G5 must remain OPEN/DRAFT throughout environment observation, independent
environment audit, Research Lead authorization, qualification execution and
human review. Merging advances main and invalidates authority. Do not merge.
Before observation and before the future offline execution barrier, fetch and
verify origin/main. The runner checks that local fetched ref; it cannot observe
remote changes after Internet is disabled. Research Lead must keep main at
EXECUTION_BASE for the entire approved workflow. If main moves, STOP and report
Research Lead; no rebase/BASE repair or automatic authorization refresh.

## Future Kaggle observation commands — NOT RUN in G5

Use a separate fresh checkout in each venue: Qwen3 Kaggle T4 x2 and PaliGemma
Kaggle T4 x1. An operator must supply `G5_AUDITED_HEAD_SHA` from the exact pushed
PR HEAD in the final handoff, after independent audit; the branch name is only
a fetch locator. No HEAD value is guessed or embedded in the tracked plan.
These bash commands run from the parent of a new `SafeShift-g5` checkout:

```bash
set -euo pipefail
: "${G5_AUDITED_HEAD_SHA:?Set the exact audited 40-character G5 PR HEAD from the handoff}"
[[ "$G5_AUDITED_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]
git clone --no-checkout https://github.com/tantdna2/SafeShift.git SafeShift-g5
cd SafeShift-g5
git fetch origin main w2.6-d9r19g5-execution-identity-relock
test "$(git rev-parse origin/main)" = b3bf4dc770c1b87a9e353a75aab759f67641c2c2
test "$(git rev-parse origin/w2.6-d9r19g5-execution-identity-relock)" = "$G5_AUDITED_HEAD_SHA"
git checkout --detach "$G5_AUDITED_HEAD_SHA"
test "$(git rev-parse HEAD)" = "$G5_AUDITED_HEAD_SHA"
test "$(git rev-parse HEAD)" != b3bf4dc770c1b87a9e353a75aab759f67641c2c2
git merge-base --is-ancestor b3bf4dc770c1b87a9e353a75aab759f67641c2c2 HEAD
test -z "$(git status --porcelain --untracked-files=all)"
git check-ignore data/processed/grounding_v3_g5_review/qwen3.environment.json
git check-ignore data/processed/grounding_v3_g5_review/paligemma.environment.json
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
```

Provision/mount the exact already approved local snapshots separately using the
existing procedures. G5 does not provision, install or download weights. Snapshot
paths below are repository-relative; retain files under ignored data/processed.
Inventory will stop if dependencies, GPU count, transformers 4.57.1, revision,
weight hashes or required metadata are missing/mismatched. Do not repair a failed
inventory in place without review. Record actual package versions, not historic
smoke versions. No claim that a future venue is currently verified.

Qwen3 session, T4 x2 (run from the checked-out repository root):

```bash
export CUDA_VISIBLE_DEVICES=0,1
python scripts/run_grounding_multicategory_v3.py --model qwen3 --run-id g5-qwen3-v3-001 --inspect-environment --snapshot data/processed/qwen3_hf_cache/models--Qwen--Qwen3-VL-8B-Instruct/snapshots/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b --output data/processed/grounding_v3_g5_review/qwen3.environment.json
```

PaliGemma session, T4 x1:

```bash
export CUDA_VISIBLE_DEVICES=0
python scripts/run_grounding_multicategory_v3.py --model paligemma --run-id g5-paligemma-v3-001 --inspect-environment --snapshot data/processed/paligemma_hf_cache/models--google--paligemma-3b-mix-448/snapshots/ead2d9a35598cb89119af004f5d023b311d1c4a1 --output data/processed/grounding_v3_g5_review/paligemma.environment.json
```

Observation inventories Python/packages/CUDA, actual visible GPUs, all snapshot
files with hashes/sizes, model/processor/tokenizer revisions, code/contracts,
decoding, exact HEAD/main/run ID and v2 lock hash. It never instantiates a
processor/model, calls model.load(), or calls generate(). Output is exclusive,
hash-verified JSON outside Git with execution_authorized=false and
QUALIFICATION_EXECUTION=NOT_RUN. Qwen metadata/tokenizer/template bytes still
need independent exact-revision audit; observation alone is not approval.
Future execution re-observes and requires equality before loading.

## Future authorization — no signed authority supplied

The [template](../configs/pre_freeze/grounding_multicategory_authorization.template.v1.json)
is deliberately false, with null reviewers/hashes/HEAD/model/run and a false
Internet-OFF attestation. Copy it to ignored data/processed only after review;
never commit a true authorization. No fake signature, reviewer or observation.
Research Lead and independent auditor must be different people; a nonempty
review_reference identifies the actual external review. JSON is an operator
attestation, not cryptographic identity verification.

Required future fields: execution_authorized=true, model_key, run_id, head_sha,
main_sha, environment_sha256, runtime_lock_sha256, internet_off_attested=true,
research_lead, independent_auditor, review_reference. Main must equal
EXECUTION_BASE and head_sha must equal the exact audited pushed G5 PR HEAD.
Run IDs remain `g5-qwen3-v3-001` and `g5-paligemma-v3-001`; never select IDs
based on outputs. Environment approval hash is SHA256 of runner encode(JSON),
not arbitrary pretty-print bytes; runtime lock hash uses normalized LF.
Future hash calculation (no GPU/model import), from the checkout root:

```bash
python -c 'from safeshift.runners import grounding_multicategory_v3 as r; print("runtime_lock_sha256=" + r.text_hash(r.ROOT / r.RUNTIME_LOCK))'
python -c 'from safeshift.runners import grounding_multicategory_v3 as r; print("environment_sha256=" + r.sha(r.encode(r.read_json(r.ROOT / "data/processed/grounding_v3_g5_review/qwen3.environment.json"))))'
python -c 'from safeshift.runners import grounding_multicategory_v3 as r; print("environment_sha256=" + r.sha(r.encode(r.read_json(r.ROOT / "data/processed/grounding_v3_g5_review/paligemma.environment.json"))))'
```

Run only the environment hash command corresponding to that venue. Future
qualification needs separately approved exact synthetic image bytes, external
authority and independently attested Internet OFF; this PREP grants none of
those permissions. No execution commands were run here.

## Validation and remaining work

Offline checks cover old guard rejection at G4 merge, new BASE identity,
missing/mismatched authority/environment/main/HEAD/hashes, false authorization,
fixed run IDs, no import/load before preflight, historical byte preservation,
unchanged scientific/runtime functions and append-only logs. Existing G3/G4
tests cover the firewall, 512 budget, 12 cases/query/parser, raw-before-parse,
failure stops and human NO_GIANT / no automatic PASS. Fake authority objects
exist only inside tests and are not real authorization artifacts.

Local environment: Python 3.11.9, Pillow 11.3.0. Validation commands:

```text
python -m unittest tests.test_grounding_execution_relock_g5 tests.test_grounding_multicategory_runtime_v3 tests.test_grounding_multicategory_v3 tests.test_grounding_interface_v2 tests.test_grounding_absence_semantics_audit -q
python -m unittest tests.test_qwen3_external_gate tests.test_qwen3_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result tests.test_paligemma_interface_candidate tests.test_external_gate_cases tests.test_d9r7_paligemma_source_api_audit tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_qwen_runner tests.test_paligemma_prep -q
git diff b3bf4dc770c1b87a9e353a75aab759f67641c2c2 --check
```

113 focused tests (10 new G5 tests) and 267 relevant regression tests PASS:
380 total. Historical byte/AST comparisons, G3 transitive locks, append-only
logs and diff check PASS. On the actual G5 descendant checkout, both models'
static preflight with images=False accepted Git identity and returned BLOCKED
for missing environment/authority; neither torch nor transformers was imported.
This diagnostic omits image-file checks; existing synthetic tests validate the
frozen manifest/bytes. It is not a full execution preflight PASS or qualification.

Full suite was not run: scoped governance changes were checked with the focused
and relevant regression suites above. No full-suite PASS claim. No actual
environment observation, qualification, model/GPU/InspecSafe execution occurred.
Future steps remain unapproved; no promotion or merge.

PR #67 read-only baseline: OPEN/DRAFT,
`e85300ab3ec122f819a2685613332578f7e203d8`.
ENVIRONMENT_STATUS=UNVERIFIED_EXTERNAL_VENUE_LOCK_PENDING;
QUALIFICATION_EXECUTION=NOT_RUN; EXECUTION_AUTHORIZED=NO; MODEL_GPU_EXECUTION=NO;
INSPECSAFE=NOT_RUN; QWEN3_RUNTIME_EXECUTION=BLOCKED;
PALIGEMMA_RUNTIME_EXECUTION=BLOCKED;
QWEN3_PRIMARY_GROUNDING_ROLE=NOT_PARTICIPATING;
PALIGEMMA_PRIMARY_GROUNDING_ROLE=NOT_PARTICIPATING;
QWEN3_ABSENCE_SEMANTICS_BLOCKER=UNRESOLVED;
PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER=UNRESOLVED; PROMOTION=NO; MERGE=NO.

## Qwen3 G5 result/closure overlay (2026-10-04)

Task: `W2.6-D9R19G5R-QWEN3-QUALIFICATION-RESULT-RECORD`.
Append-only record subsequent to the PREP above. [PR #72](https://github.com/tantdna2/SafeShift/pull/72)
is MERGED at `465ec738b6a395801df06e2ef179e2bf51f8b509`, verified through
GitHub and fetched origin/main. This is the documentary task BASE; it does not
replace the historical execution BASE, HEAD or authorization identity.
All PREP statements and future commands above remain historical and unchanged.

Source: Research Lead's supplied audited execution facts in the G5R task request.
The execution/audit results and hashes below are recorded from that source;
this task did not rerun qualification or independently inspect/hash the ZIP.

| Execution identity | Recorded value |
| --- | --- |
| model | `Qwen/Qwen3-VL-8B-Instruct` |
| revision | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` |
| run_id | `g5-qwen3-v3-001` |
| environment_sha256 | `31b2f9461924e8ed469c2cc93ab5e1070168512519ac39c7773e01ba9beebc11` |
| runtime_lock_sha256 | `4ed0bbe80b492eae0c402fd94cb5b050b163bc5cb464813366eeba6cc6342d0b` |
| artifact ZIP SHA256 | `00e9ae05d7fb3d9e369a1127a309b9aec8cb4723ab2239fd2b76683ba79761b5` |

| Audited execution fact | Recorded result |
| --- | --- |
| QUALIFICATION_EXECUTION | EXECUTED |
| model_loads | 1 |
| native_calls | 12 |
| failure | `null` |
| termination_reason | 12/12 EOS |
| raw-before-parse | verified |
| artifact integrity | PASS |
| parse_status under frozen v3 parser | 12/12 INVALID |
| tracking_result | `false` |
| final_verdict | FAIL |
| independent audit | PASS |
| QWEN3_G5_QUALIFICATION | FAIL |
| RERUN | NO |
| INSPECSAFE | NOT_RUN |
| QWEN3_PRIMARY_GROUNDING_ROLE | NOT_PARTICIPATING |
| PROMOTION | NO |

All 12 native outputs were Markdown-fenced JSON, which the frozen v3
strict_json parser rejects. E_red_green also emitted the out-of-query label
"blue square". These observations do not authorize output repair or historical
result reinterpretation. Independent audit PASS does not change qualification
FAIL; Qwen3 primary grounding remains NOT_PARTICIPATING, with no promotion.

This task records the completed run and PR #72 closure only. No new execution,
InspecSafe run, parser/prompt/runner/scientific contract test/model code change,
G6 or merge. No PaliGemma result is inferred.

Documentary validation: `git diff --check` PASS; exact BASE and three-file
change scope PASS; Git-normalized pre-existing content preserved as an unchanged
prefix in all three files; appended local links/anchor and every supplied
identity/result value checked PASS. No historical lines removed or replaced.
Model/scientific tests and full suite were not run: only Markdown was appended,
with no code or scientific contract changes. No model or InspecSafe execution.
