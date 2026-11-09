# TRAIN3763 O5 extension — 09/11/2026

Owner [decision6733033003](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6733033003)
approves **only** the aggregate reservation ceiling `80000 → 430000` physical
GPU-seconds. The original grant SHA256 remains
`1f672fb601006c7898be271e59f74fb341d7311fc60794a9ed6a332f430395c6`.
`job_seconds=7200`, two physical T4 GPUs, 4500 calls, 100 jobs, deadline, all
per-job/archive/repair limits, original rights and stop policy remain unchanged.
This is neither measured billing nor additional Kaggle weekly quota.

## Implementation and authority

`internvl3763_o5.py` pins the exact GitHub comment ID, UTF-8 body SHA256
`e6953ebda47d83b86db0f5035244947c3a1786baa714ad615c399f3181704b9c`,
structured-decision digest, Owner login/numeric identity, OWNER association,
Issue180, original grant and science SHA256. The original grant is authenticated
at its original comment6658142293 and original merged implementation PR.
Duplicate keys/markers, nonfinite JSON, edits, wrong principals/issue/grant or
missing GitHub evidence fail closed. The public body is preserved verbatim in
[owner-decision.md](research/evidence/train3763_o5_extension_20261109/owner-decision.md).

`extend-o5` holds the existing OS campaign lock and authenticates GitHub. It
requires the exact existing 24-event prefix, seven reservations totaling seven
calls / seven jobs / 25200 GPU-seconds, no open intent, verified ZIP/history
custody and exactly ordinal0/1 SUCCESS. It appends **journal000025** with kind
`O5_EXTENSION` to the existing ledger and mirror, using exclusive create, fsync
and directory sync on supported OSes. No new grant, registration, guard, mirror
or replacement ledger is created. The event retains the original campaign hash,
chains to journal24, binds the registration file SHA256 and stores only public
authority evidence and the original locator. Reapplication is rejected.

All old bytes remain in place. Historical requests, receipts, attempts, archive
hashes and MEASURED entries are read with their original identities. Reservations
before journal25 retain the 80000 ceiling; future reservations bind journal25's
digest in both request and intent. Every read validates cumulative old+new
reservations, integer call/time accounting and per-job caps. Abort/FAIL/early stop
never reduces reservations. The expected effective remainder immediately after
extension is **404800**, with **4493 calls / 93 jobs** remaining.

`status` and ledger-backed `forecast` are offline inspection: they verify the
pinned authority snapshot, chain/mirror/registration and report original versus
effective caps and extension digest. They do not assert a live authority or
execution PASS. `forecast` without `--directory` remains the explicitly historical
Attempt4 public projection. `plan`, `measure` and submit reauthenticate GitHub
when an extension exists. Provider inventory checks the effective budget and
the unchanged physical-GPU multiplier; weekly quota and all previous remote job
identities/terminal states are still independent gates before each submit.

## Separate execution release and source qualification

Resource approval cannot authorize Attempt8. New protected source requires fresh
independent Antigravity security/provenance audit, direct ChatGPT source/diff/CI
review, exact-HEAD merge authorization, independent postmerge verification and
fresh `SAFESHIFT_TRAIN3763_AUDIT_V1` + `SAFESHIFT_TRAIN3763_TECHNICAL_V1`.
Those records continue to bind the **original** campaign SHA256.

The reviewer then separately publishes `SAFESHIFT_TRAIN3763_O5_EXECUTION_V1`
on the merged implementation PR. Its exact JSON fields are:

```text
campaign_sha256: original grant digest
extension_sha256: digest of the new O5_EXTENSION event
science_sha256: unchanged original science digest
implementation_pr, reviewed_head, merged_sha: exact TECHNICAL_V1 identity
source_sha256, notebook_sha256: exact TECHNICAL_V1 identity
status: RELEASED_FOR_SERIAL_RESUME
start_ordinal: 2
test: false
```

No executable release is supplied by this programming task. It must be an
authentic comment by a `review_logins` principal; mismatched source, merge,
extension, status or scope blocks planning/activation/submit. This is one release
for serial continuation under that reviewed source and campaign, not renewed
Owner permission per shard. Any later source change needs new technical
qualification and a matching release. The worker/notebook authenticates the
amendment and release before claims, provision, Input access or GPU/model load.

## Postmerge operator procedure — not authorized in this task

Use only the original `operator-asus-win` machine/session and canonical paths.
Do not copy the active ledger, reinitialize it or reset reservations. Verify clean
reviewed merged source, independent audit/postmerge evidence and exact provider
state. Read-only collection remains possible under historical authority.

```powershell
$Ledger = 'data/processed/train3763-campaign/ledger'
$Grant = 'data/processed/train3763-campaign/grant-locator.json'
# Use the existing isolated SDK Python; never expose credentials.
$OperatorPython = 'data/processed/operator-venv/Scripts/python.exe'
& $OperatorPython -B -m scripts.train3763_campaign status --directory $Ledger
# Append only after review/audit/authorized merge/postmerge verification.
& $OperatorPython -B -m scripts.train3763_campaign extend-o5 --directory $Ledger --grant $Grant
& $OperatorPython -B -m scripts.train3763_campaign status --directory $Ledger
& $OperatorPython -B -m scripts.train3763_campaign forecast --directory $Ledger --weekly-remaining <observed-physical-gpu-seconds>
```

After extension the reviewer can bind its exact digest in the execution release.
Create a **new** context file, retaining the original `technical_revision`, private
new-capsule `execution_input` and pinned `python_input` fields, and adding
`o5_execution_release: {comment_id, body_sha256}` for that authentic release.
Do not edit prior context/handoff/capsule files. `plan` obtains `o5_extension`
directly from the verified ledger; no cap override or caller-supplied amendment
is accepted. Planning remains blocked until the separate release exists.

```powershell
# Only after the separate ChatGPT execution release and current provider/quota GO.
& $OperatorPython -B -m scripts.train3763_campaign plan --directory $Ledger --grant $Grant --template data/processed/train3763-campaign/context-attempt8.json --cohort data/processed/train3763-campaign/cohort.json --handoff data/processed/train3763-campaign/attempt-8 --mode resume --calls 1 --seconds 1800
```

New source SHA means existing Attempt7 `safe_calls=205` is **historical evidence**,
not certification of the changed source. The first newly authorized job must
resume ordinal2 with one call and preserve ordinal0/1 SUCCESS. Collect terminal
ZIP/SHA/raw/logits/trace under the existing handoff protocol before another job;
run `measure --archive <verified-new-source-zip> --seconds 7200` and then ledger
`forecast`. Larger jobs use at most the new source's measured safe_calls,
`required_job_seconds(measured,calls)`, 7200 wall seconds/job, remaining campaign
reservations and actual weekly quota. A measured ceiling is not a requirement
to fill a job; smaller tail shards use their proportional required seconds.

No automatic next job, refund, retry or parallel session. Unknown submit/history/
provider/ZIP, FAIL, exhausted resources or unapproved source stops scheduling.
Monitor at most15 minutes, checkpoint and exit; resume the same conversation for
terminal collection on the next user message. Source fixes do not replace the
independent audit or authorize science/TEST changes.

## Failure handling and portability

A partial primary/mirror append, fsync failure or process death is STOP, not
permission to retry or delete the stranded event. Reopen performs full equality/
gap/chain/authority checks. Offline synthetic tests demonstrate recovery only by
explicitly restoring the exact already-written missing mirror bytes from verified
custody, under stopped single-writer operation. There is no automatic restore,
replay, takeover, TTL or budget refund command. Production discrepancies require
read-only reconciliation and independently reviewed recovery evidence.

Windows uses the existing kernel file lock and file fsync; directory fsync is
performed only where the OS supports it. Linux follows the same create-only chain
and lock contract. One local operator and mirrored custody cannot detect a
coordinated rollback of every copy/guard before later evidence exists, nor prove
global exactly-once across independent VMs. Existing provider/history checks and
STOP rules remain necessary. No new cross-machine or durability guarantee is made.

Science SHA256 stays
`ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50`;
original 3763 TRAIN IDs, model checkpoint, FP16, prompt/parser/grammar/HNLO and
TEST closure are unchanged. CPU synthetic acceptance is separate from final-source
Kaggle verification, scientific qualification and O2–O6 evidence.

## Reproduce CPU acceptance

See [completed acceptance and source/custody evidence](research/TRAIN3763_O5_ACCEPTANCE_20261109.md).

`scripts.qualify_internvl3763` includes `test_internvl3763_o5` and records its
checksum with the existing controller/ledger/operator suites. Use a new ignored
output path; the qualifier disables CUDA and Hub access. Native CPU checks use
scripted logits/synthetic bytes and existing pinned public software, no weights.

```powershell
$env:SAFESHIFT3763_SDK_CPU = '1'
& data/processed/operator-venv/Scripts/python.exe -B -m scripts.qualify_internvl3763 --output data/processed/<new-cpu-evidence> --native --packages .venv/Lib/site-packages --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
python -B -m unittest discover -s tests -p test_internvl3763_o5.py -v
python -B -m unittest discover -s tests -p test_internvl3763_notebook.py -v
python -B -m unittest discover -s tests -p test_smoke.py -v
```

Linux O5 tests use `python3 -B -m unittest discover -s tests -p
test_internvl3763_o5.py -v`; no SDK/native dependencies are required for that
suite. The temporary ledger/archives are explicitly synthetic and separate from
`data/processed/train3763-campaign`. Production amendment/Attempt8 remains NOT_RUN.
