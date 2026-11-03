# Issue173 bounded model diagnostics — 2026-11-03

Authority: [Owner/ChatGPT directive6592812806](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6592812806).
Same session, branch and Draft PR175. Original smoke stays Qwen1/InternVL1/Mini0.
Five archives and all terminal fences remain unchanged. No TEST, GT, TRAIN image,
fresh171 campaign or scientific score is used by these diagnostics.

## Mini final TRAIN implementation — review pending, 03/11/2026

[Directive6598989252](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6598989252)
authorizes completing a new versioned Mini-only route, then stopping for exact
HEAD/job review before the remaining original TRAIN load/call. No live job is
authorized in this implementation pass. The earlier terminal routes stay closed.

Implementation contract: reuse the five original seals and four diagnostic seals,
the exact master/ordinal0 image, Mini checkpoint and frozen numerical adapter.
Routine admission checks on the actual mounted files and current VM remain;
there is no new RAM/software/checkpoint survey or redundant model download.
One private job, one load/one call, 1800 seconds maximum, T4x2 allocation with
only GPU0 used, unchanged RAM/VRAM/disk floors. Raw precedes strict parsing;
INVALID and partial/error evidence are sealed and retained without retry.

Remote exclusion will use one create-only public custody record per submission,
launch, load and call, on this same PR branch. Records contain only public job/
source identities and random execution nonces, never data, raw or credentials.
The authenticated local coordinator reads the exact Kaggle version's live log
and acknowledges each new process nonce once through GitHub's Contents API.
VMs only read these records; no credential is uploaded to Kaggle. Replayed logs
cannot issue another permit, and a new VM/process generates a different nonce.
Unknown write/submission status stops; no lock expiry, takeover, overwrite or
automatic resubmission. This is exclusion for the reviewed execution path,
not protection against a repository administrator deliberately rewriting code
or custody. Live transport remains unverified until the separately approved job.

The coordinator requires an explicit future Owner/ChatGPT approval comment bound
to the reviewed HEAD, runtime source, notebook, fixed job/version and finite
budget. This task does not manufacture that approval. The one review handoff
will include executable notebook/builder, parent/setup/native CLI, synthetic
positive/failure tests, receipt and exact invocation. Future InternVL grammar
work is deferred until PR175 completion, authorized merge and verification.

### Mini-only operator contract for the exact review

Executable: `notebooks/SafeShift_ISSUE173_MINI_TRAIN_ONCE.ipynb`, built by
`scripts/build_minicpm173_once.py` from an immutable runtime commit. Parent and
setup/native CLI: `scripts/minicpm173_train_once.py`. Coordinator:
`scripts/submit_minicpm173_once.py`; remote admission:
`safeshift/minicpm173_once.py`. Existing review/v5/diagnostic notebook bytes and
their terminal entrypoints are retained, not reopened. The notebook embeds all
runtime files and their hashes; the reviewed HEAD also binds the local submitter,
builder and notebook. Runtime commit and containing review HEAD are distinct
because a notebook cannot embed its own containing Git commit without a cycle.

The coordinator accepts only a **new** Owner-transmitted approval comment on
PR175 with one `MINICPM173_RELEASE_V1` marker followed by a fenced JSON object.
The object must contain exactly: `identity`, `reviewed_head`, `runtime_commit`,
`manifest_sha256`, `notebook_sha256`, `notebook_code_sha256`, `job`, `version`,
`expires_unix`, `limits`. The first six identities/hashes come from the exact
reviewed tree and published notebook; `version=1`, `job=nguynanhtn/safeshift-issue173-minicpm-original-train-once-v2`.
Limits are exactly `model_key=minicpm4`, `ordinal=0`, `max_loads=1`, `max_calls=1`,
`max_seconds=1800`, `max_physical_gpu_seconds=3600`. Owner/ChatGPT supplies the
expiry and approval; a template, this directive or local `approved=True` is not
accepted. HTTPS verifies the comment's repository/issue/Owner account. This is
an authenticated review record, not a fabricated digital signature.

After that one exact review, the local invocation is:

```console
python -B -m scripts.submit_minicpm173_once --approval-comment <new-owner-comment-id> --notebook notebooks/SafeShift_ISSUE173_MINI_TRAIN_ONCE.ipynb --history-inputs data/processed/issue173-minicpm-once-history --stage data/processed/issue173-verification/mini-once-approved-submit
```

Use the existing authenticated official Kaggle Python environment and `gh` on
the local coordinator. `history-inputs` contains the existing five ZIPs and
sidecars plus four diagnostic ZIPs under their Kaggle mount basenames. It is
custody metadata only; no image/weight copy. The job attaches existing Inputs:
Mini checkpoint, original master/data, existing-byte proof and all nine Outputs.
No checkpoint download or copy; new VM installation of the pinned worker is
the necessary runtime setup, not another standalone qualification experiment.

Before any Kaggle submission the coordinator checks clean approved local/remote
HEAD, exact notebook, complete local custody, all owned Kaggle pages, exact old
job versions/status, target absence and unreserved quota. Kaggle returns403 for
an absent private slug: **403 alone is not absence proof**. The authenticated
owner inventory must be exhausted, including numbered pages when a full100-row
page has no cursor; timeout, duplicate pages or missing known jobs block.

It then creates `submission.json` in the fixed public ledger directory on the
same branch, using GitHub Contents API **without an update SHA**. A conflict or
lost response stops. After one `kernels_push`, it confirms exact private job ID,
version and executable cell hash, then streams that version's official logs.
Only matching, sequential random launch/load/call challenges can create the
corresponding fixed permit file. The native child's public challenge lines are
relayed by the supervised parent; other native logs/raw stay private. Repeated
identical log events are no-ops; a second process nonce conflicts. New VM/worker
invocations cannot choose/reuse a nonce. No VM holds GitHub or Kaggle credentials.
The local coordinator must remain connected for the bounded job. Missing permit,
HTTP error/rate limit, log loss or deadline means fail closed, not resubmission.

GitHub create-only semantics: [official Contents API](https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents).
Kaggle versioned log interface: [official CLI reference](https://github.com/Kaggle/kaggle-cli/blob/main/skills/references/kernels.md).
The installed official SDK's `kernels_logs_stream` implementation was inspected;
its live transport on this new job is **NOT_RUN**, not claimed PASS from mocks.
Any manual mutation/deletion of remote custody or executable code is outside
the reviewed route's exclusion guarantee; there is no global exactly-once claim
against a hostile administrator. No new branch/PR, service or credential is needed.

Parent/setup/native deadlines are bounded; native guards retain the existing
Linux process-group kill/reap behavior. RAM/VRAM/disk/driver gates still run on
the actual VM, including RAM/VRAM immediately after the load permit. The unchanged
loader checks source/index/weight SHA, FP16/eager and FP32 resampler before use.
Every load/call reservation, native marker, raw/token/step file and error is kept.
Strict parsing reads the durable raw after its checksum verifies. SUCCESS and
INVALID both terminate the slot; partial calls remain UNKNOWN_NO_RETRY.

The parent exports per-file checksums and ZIP/SHA256 even after handled errors;
whole-VM termination or export failure can leave incomplete output, which is
UNKNOWN and never permission to retry. Download the exact version's archive and
verify every member before recording final counts. Public ledger files contain
only nonprivate source/job/nonce/count/hash information. After live execution,
fast-forward this branch to its own ledger commits before adding sanitized result
evidence; never overwrite those commits. All raw/real IDs/images/weights stay private.

### Final Mini implementation evidence — no live execution

[Review evidence directory](research/evidence/issue173/mini-once/) contains six
sanitized receipts. Code snapshot **40a7b400825cb28e01fbce601373cada32078770**:
Linux **90/90 Issue173 PASS**, including34 Mini-only regressions, no skips/errors.
Linux fulltrain **55/55 PASS** at `40fcf820052b042e637bac2287b8889c874df937`;
its complete shared source manifest still matches the final tree byte-for-byte.
CPU Python3.14 is a control-flow test environment, not the pinned native worker
qualification. No additional native inference or software qualification was run.

Embedded runtime: **bf6fbe210a9b92348cec9bef1850aaa7a798f690**;82 source files,
all compiled and matched against the deterministic builder and current files.
Notebook SHA256:
`232ba33cfc1e289eb472bd871b988043753e44a4164e5509eaba6e6b5abc783f`.
Executable-cell SHA256:
`ac6efc40baebbb6ec5c6cac7567b369094b29908e0481e86a244d9df0ebc52a9`.
Manifest SHA256:
`5ff163b22d5a79872e0b23b97066862caa08acf925a0c69c4bffca638fd561c2`.
An isolated CPU process imports the exact embedded files and stops at missing
remote review/submission before data/model I/O; only scratch location and the
offline absent-record reader are substituted in that check. The positive
CLI→parent→setup/native→load→call→raw→parser→ZIP path uses explicitly synthetic
model/hardware/process mocks; real Linux timeout/group kill and log relay also pass.

Remote inventory exhausted **157 owned jobs**, confirms all11 required Inputs/
Outputs at version1 COMPLETE and the proposed job absent. At observation
1793696301 Unix seconds, GPU quota used11,339/reserved0/total108,000 seconds.
This is an observation, not a quota reservation or future environment guarantee.
The initial100-row no-cursor response was superseded after checking numbered
pages; its incomplete intermediate receipt is retained privately and not used.
An initial WSL receipt invocation stopped before tests due to Windows `.git`
paths; only Linux `GIT_DIR`/`GIT_WORK_TREE` were corrected before passing suites.

All five original archives/sidecars and four diagnostic archives revalidated
with exact seals. Smoke counts remain Qwen1/InternVL1/Mini0; diagnostics remain
4loads/5calls. The ignored local custody directory in the command above is now
prepared and validated:18 ZIP/sidecar files,820,969 copied bytes, no images or
weights. No remote dispatch record has been created and no job submitted.

**Handoff is for exact source review, not READY FOR OWNER/full TRAIN.** The only
next release step is ChatGPT's explicit approval for the containing reviewed HEAD,
the runtime/notebook identities above and fixed job/version1/one Mini ordinal0
load/call. Live challenge/permit transport and TRAIN outcome remain **NOT_RUN**;
failure there must retain custody and stop. Whole-PR audit and merge are separate.

## Final format recommendation — 03/11/2026

[Final directive6598354864](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6598354864)
supersedes further diagnostic investigation. This decision pass reads only
relevant public evidence/source and runs one CPU synthetic suite. No Kaggle,
private raw, model/image access or inference. Earlier sections remain historical.

**KHUYẾN NGHỊ: KHÔNG NÊN ÁP DỤNG thay đổi sang P2.1 hoặc grammar lúc này.**
**PHƯƠNG ÁN ĐƯỢC CHỌN: A — giữ C1 và parser JSON thuần đã khóa cho InternVL3.5.**
This is a recommendation to preserve the existing method, not a claim that C1
prevents format failures or that a full TRAIN campaign is released. Existing
evidence does not establish a scientifically comparable replacement with valid
InternVL HNLO. No further generic investigation is requested.

| Exactly three alternatives | Benefit and cost | Decision |
| --- | --- | --- |
| A: current C1, bare JSON | Preserves prompt, generation, acceptance and existing token/logit contract. Native synthetic baseline already demonstrated valid JSON. Fenced responses still remain INVALID and can reduce support; no reliability rate for 3,763 images is established. | **Selected: keep frozen InternVL configuration.** |
| B: historical P2.1, bare JSON or one valid whole-response fence, common to all models | Does not alter native generation/logits and is less invasive than grammar. Strict schema still rejects malformed JSON, duplicate/extra keys, noncanonical labels and extra prose. However, changing acceptance changes INVALID/support and may change downstream results; current InternVL HNLO does not support fenced continuations. Historical authority and validation do not transfer to this checkpoint/campaign. | Do not adopt now; a changed scientific version would require approval. |
| C: four-label constrained grammar | Produces complete canonical JSON through native constrained decoding; one actual diagnostic succeeded. It changes generation, including possible prefixes and label probabilities, suppresses off-language behavior and violates current HNLO's no-processor condition. That one input also matched unconstrained raw argmax, so no causal improvement or classification benefit was demonstrated. | Do not adopt; remains PROPOSED, scientifically non-equivalent. |

### What historical P2.1 actually established

At immutable ref `31a04e6f7175cca818c63b4de0153246b3f3ecdb`, the
[amendment](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/notes/w2_p21_protocol_amendment.md)
records an Owner/Research Lead supplied observation: historical InternVL shard0
had 1,254 INVALID / zero SUCCESS due to fenced JSON. This is reported historical
evidence, not an independent raw audit performed in this task. P2.1 was an
explicit protocol amendment after observing outputs, not a decoder bug fix.
It preserved old P2 results, required new run/protocol identities, unchanged raw
bytes, a common acceptance policy and complete relevant cohort comparisons.
Selective repair of favorable INVALID cases was not the lesson.

The [frozen amendment](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/configs/frozen/p21_protocol_amendment.v1.json)
is marked draft implementation pending audit/standard merge, with exact historical
run authority. Its model is **OpenGVLab/InternVL3-2B-hf**, revision
`cb57a075cb75a2e6d1b668b128d48bb00ae321d2`, not current
**OpenGVLab/InternVL3_5-4B-HF**, revision
`6bd4487402110ef9889ba50eb7aefeb302526fed`.
The relevant records do not substantiate a separate InternVL2.5 run:
`internvl2_5` is a custom conversation-template name in
[candidate screening](research/THESIS_VLM_CANDIDATE_SCREENING_20261029.md).
Neither historical authorization nor historical cohort size authorizes fresh171.

The archived [parser](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/protocol/p21_schema.py),
[shared adapter](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/safeshift/runners/p21_classification.py)
and [tests](https://github.com/tantdna2/SafeShift/blob/31a04e6f7175cca818c63b4de0153246b3f3ecdb/tests/test_p21_classification.py)
accept exactly bare JSON or one complete fence (unlabelled or lowercase `json`,
separate fence lines, LF/CRLF), retaining strict fields/values and original raw.
This is a defined alternative contract, not arbitrary Markdown stripping.

### HNLO and fairness: acceptance alone is insufficient

Current [peer HNLO replay](../safeshift/pilot/hnlo.py) requires proven input
boundary, independent decode replay, raw greedy alignment, no logits processors,
four complete candidate continuations with one differing token and a common
prefix/suffix. It then checks C1 validity and exact whole generated IDs/text
against three **bare JSON** surfaces. The score is
`logsumexp(z01,z02,z03) - z04` at the proven decision position.

Thus a P2.1 label for a fenced response still fails `NO_VALID_GENERATED_LABEL`;
even a synthetic substitution of that acceptance check fails
`ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS`. Removing fences from a
text view cannot remove generated tokens or realign recorded logits. Grammar
fails `NONEMPTY_OR_UNKNOWN_PROCESSORS`, even when raw argmax happens to agree.
Capturing raw logits before constraints does not by itself restore comparability:
forced earlier tokens can change later contexts and logits. The present evidence
does not qualify a wrapper-aware or constrained InternVL HNLO method.

**HNLO verdict: preserve the existing qualification contract, not universal score
availability or three-model comparability.** InternVL v5 remains INVALID with
HNLO unavailable; its saved diagnosis reports native fence generation and exact
decode/token capture, not an implementation fault to fix. Validity of future
scores still requires per-record replay. MiniCPM remains label-only, HNLO N/A.

There is an existing asymmetry: [Qwen semantics](../safeshift/fulltrain/qwen_semantics.py)
retain historical P2.1 parsing and validate decision candidates against the full
original response, including any wrapper. [Fresh171](FRESH_FULLTRAIN_171.md)
explicitly limits that exception to Qwen; the peers retain C1. Keeping C1 does
**not** make acceptance identical across all three models. Common P2.1 would
improve symmetry of syntax acceptance, but Qwen's model-specific token proof
does not qualify InternVL, and identical parsing alone is not scientific
comparability. Grammar would require a common, versioned generation policy as
well. Current evidence supports no accuracy or HNLO-quality superiority claim
for any alternative; valid JSON is not evidence of a correct classification.

For the same 3,763 TRAIN IDs/order/images/labels, a future approved method change
must define a separate complete comparative series and treatment of every
affected model, including full-series rerun where required. Do not selectively
rerun fenced failures, relabel historical INVALID as SUCCESS or pool versions.
Adaptation after observed failures must be disclosed. Retaining frozen C1 now
avoids silently altering this scientific contract; it does not release full TRAIN.

### One bounded CPU check and the next decision

[Five CPU tests](../tests/test_issue173_format_decision.py), **5/5 PASS**, one
Windows/Python3.11.9 invocation, zero model calls:
[receipt](research/evidence/issue173/diagnostics/format-decision-cpu.json).
They compare the archived parser function AST to the already-preserved Qwen
implementation, exercise canonical/fenced/malformed cases, keep strict INVALID
and synthetic raw unchanged, and distinguish acceptance from HNLO alignment and
grammar qualification. Character-token fixtures prove contract mechanics only;
they do not validate native checkpoint HNLO or scientific improvement. Reproducing
the archive comparison requires the exact historical Git object. Earlier Linux
results below apply to their recorded snapshots; they were not rerun in this pass.

**QUYỀN KHOA HỌC:** retaining the frozen method does not require approval of a new
method; adopting P2.1 or grammar would require explicit versioned scientific
approval covering comparability and HNLO. **One next action:** ChatGPT reviews
this recommendation in PR175 and decides whether to retain the locked method.
No additional diagnostic round is proposed. All old results/attempts, smoke2/3,
MiniCPM final TRAIN review hold and merge/audit gates remain unchanged.

## Declared initial budget and hypotheses (before submission)

At most two initial jobs, one model per fresh VM, one weight load per job;
MiniCPM one synthetic call, InternVL at most three synthetic calls. Each job
has 1800 seconds total, 600 setup/900 native child seconds, one visible T4
(Kaggle allocates two; second unused), 16 GiB pre-load available RAM,
13000 MiB pre-load free VRAM, 24 GiB scratch + 1 GiB output reserve.
Cumulative initial ceiling: two loads, four native calls, 3600 seconds wall
and 7200 physical T4-seconds. Submission checks quota and no reserved GPU job.
No internal retries. Unknown consumption stops continuation; failed calls and
loads count. Any further attempt requires a new predeclared ID, ledger update,
reconciled sealed predecessor and finite budget, within this Owner directive.

Input is a deterministic 448x448 RGB constant-gray synthetic image, created
inside the worker. It has no annotation or semantic accuracy target. No dataset
is attached. Hash/dimensions/recipe and actual input tensors are evidenced.

MiniCPM reuses the proven clean-VM preparation and own-cache advice, with the
same pinned software. A new VM must install its local runtime once because the
previous VM scratch is ephemeral; no repeat standalone preflight and no model
download/copy. Test actual pinned load and unchanged FP32 resampler followed by
one C1/greedy native call. Strict parsing and label-only reporting remain exact.

InternVL baseline uses unchanged C1/template/generation on the synthetic input.
The bounded executed plan compares a versioned formatting reminder in the user
message even if baseline passes, without changing original C1 bytes. If the
reminder is still INVALID, test assistant JSON
prefill. The reminder and prefill are **PROPOSED, scientifically non-equivalent**;
they condition next-token probabilities and could affect labels, INVALID rates,
HNLO alignment/distribution and all downstream metrics. No scores or official
selection are computed. A supplied prefix is recorded separately from native
generated text: assembled-message validity must never be described as validity
of the generated suffix alone. No stripping, truncation or label rescue.

The template API's documented continuation mechanism is a basis for the prefill
hypothesis, not proof that this checkpoint complies. See
[Transformers chat templates](https://huggingface.co/docs/transformers/chat_templating).
Pinned runtime and checkpoint template are tested directly; no library update.

## Release boundary

Original smoke notebook/CLI/worker remain terminal. The separate Mini TRAIN
request/launch/worker remain REVIEW HOLD regardless of diagnostic success.
No final original-TRAIN call before direct ChatGPT review of exact dispatch and
cumulative ledger. Scientific adoption of InternVL variants requires a separate
comparability decision. Results and receipts will be appended after execution.

## Additional MiniCPM hypothesis/budget declared after v1 evidence

v1 sealed ZIP `5819e9347f9a376b65c32591b384bd3b1f4b4f9a3b1a8498d3b0edb54413d512`
proves one successful real weight load and one finite native call, exact decoder
replay and active FP32 resampler. On uniform gray, the model generated a JSON
value using the descriptive normal-category phrase rather than the canonical
vocabulary. Strict INVALID is correct; no technical corruption or RAM failure.

Predeclare `issue173-diag-mini-scene-v2`: one new fresh-VM load, at most two
native calls, 1800s wall (3600 allocated T4-seconds), same RAM/VRAM/storage and
all original MiniCPM science/model/runtime settings. Two fixed, procedural,
unannotated 448x448 factory schematics (fire/smoke shapes, then machinery/boxes)
contain no text/class code/GT. Hypothesis: the blank image is outside the visual
task and this descriptive response does not establish a universal canonical
format failure. Test relevant visual structure without changing C1, generation,
preprocessing, parser or resampler. Stop after the first strict native SUCCESS;
retain every INVALID. This is an engineering existence test, not a rate/accuracy
estimate or dataset/cohort selection. No additional attempt is automatically
scheduled. Cumulative ceiling across the three declared jobs: three loads,
six calls, 5400s wall /10800 allocated T4-seconds. v1 remains consumed and sealed.

Existing official160 evidence also reports155 strict valid outputs under the
same FP32 descriptor, but is historical, separately scoped and not substituted
for this new diagnostic result or permission for another TRAIN call.

## InternVL deterministic format candidate, predeclared after v1

InternVL v1 archive `05ed72478ba15585ad3cc13df4479f8ee15bcec98651b7fab093b222c19a82e3`
records two direct native strict SUCCESS outputs, both baseline and reminder.
Therefore it proves capability, **not** a causal improvement from the reminder.
The prefill rendered correctly in native CPU validation but was not inferred.

Predeclare `issue173-diag-intern-grammar-v2`, one fresh-VM load/one synthetic
fire-schematic call, 1800s wall/3600 allocated T4-seconds with unchanged resource
floors. A tokenizer-verified prefix trie allows exactly four complete canonical
C1 JSON strings, then EOS. Model logits choose the label; no GT, forced label,
response rewriting or parser relaxation. `PrefixConstrainedLogitsProcessor`
changes generation semantics and conditional probabilities, so this is strictly
**PROPOSED_NON_EQUIVALENT / BLOCKED_REQUIRES_SCIENTIFIC_DECISION** for research use.
The entire valid JSON must be generated by the model, not assembled from a
prefill. HNLO and all scientific metrics are excluded. CPU tests enumerate all
four accepted paths and reject off-language prefixes before live validation.

Cumulative absolute ceiling for these four jobs: four loads/seven calls,
7200s wall/14400 allocated T4-seconds. No automatic retry or fifth job. Each
submission requires reconciled predecessor ZIPs, no running reservation and
sufficient quota. Original TRAIN smoke remains2/3 with its last call held.

The pinned implementation uses the documented
[Transformers4.55.4 PrefixConstrainedLogitsProcessor](https://huggingface.co/docs/transformers/v4.55.4/en/internal/generation_utils#transformers.PrefixConstrainedLogitsProcessor).
The actual runtime processor list and token steps must verify its application.
The initial prose said reminder only after INVALID; the committed executable
plan actually compared baseline and reminder unconditionally (two calls within
the declared three-call ceiling). This discrepancy is retained explicitly;
the results cannot establish a reminder improvement over an already valid baseline.

## Observed results and exact limits

| Diagnostic | Actual loads/calls | Result | Scientific equivalence |
| --- | --- | --- | --- |
| Mini synthetic v1, uniform gray | 1/1 | Weights loaded; finite inference; strict INVALID because the JSON value uses the descriptive normal phrase | Original C1/greedy/FP16/eager/FP32 resampler, synthetic only |
| Intern format v1, uniform gray | 1/2 | Baseline and reminder both generate complete strict canonical JSON natively | Baseline unchanged; reminder PROPOSED, no causal improvement established |
| Mini scene v2, procedural factory/fire | 1/1 | Weights loaded and strict native SUCCESS; second planned image NOT_RUN | Original C1/generation/processor/numerical implementation unchanged |
| Intern grammar v2, procedural factory/fire | 1/1 | Complete native canonical JSON, strict SUCCESS; actual PrefixConstrainedLogitsProcessor recorded | PROPOSED generation change; no scientific activation |

All four Kaggle jobs are COMPLETE, each version1. Exact jobs:
[Mini v1](https://www.kaggle.com/code/nguynanhtn/safeshift-issue173-diag-mini-synthetic-v1),
[Intern v1](https://www.kaggle.com/code/nguynanhtn/safeshift-issue173-diag-intern-format-v1),
[Mini v2](https://www.kaggle.com/code/nguynanhtn/safeshift-issue173-diag-mini-scene-v2),
[Intern grammar v2](https://www.kaggle.com/code/nguynanhtn/safeshift-issue173-diag-intern-grammar-v2).
Actual total **4 loads /5 calls**, below4/7 ceilings. Original smoke remains2/3.
No unknown consumption or retry. Intern prefill and Mini workshop fallback had
zero native calls. Kaggle reported GPU quota rose9952.784→11339.350 seconds
(delta1386.566); final reserved0. This is the platform quota unit, not an
inferred physical-device billing formula. Total supervised child time1286.55s.

Before-load available RAM: Mini v1 **24,281,993,216B**, Intern v1
**24,190,021,632B**, Mini v2 **24,335,233,024B**, Intern grammar
**24,192,712,704B**; all exceed unchanged17,179,869,184B. Mini peak allocated
VRAM **8,391,736,320B**; Intern peaks9,860,110,848/9,841,352,192B. No OOM events,
no child survivors after exits; all setup/native children exit0. Software
provision occurs once per fresh ephemeral VM, not a repeated preflight in the
same VM. No checkpoint download/copy; native offline loader rehashes weights.

Intern grammar uses no assistant prefix; all10 generated tokens, including EOS,
are finite and independently decoded. The recorded processor is exactly the
declared prefix constraint. On this particular synthetic input, the constrained
sequence also matches every unprocessed argmax, so this call does **not** prove a
changed label or a measured improvement. The closed-language CPU enumeration
proves off-language next tokens (including a leading fence) cannot be admitted;
the real pinned-tokenizer/native-generation run proves integration. Together
they establish a deterministic format mechanism, not universal accuracy or
scientific equivalence. No claim that it fixes v5's image is made; v5 was not rerun.

The four archive SHA256s and exact source commits/calls are pinned in
[`diagnostic_custody.json`](../configs/issue173/diagnostic_custody.json). Kernel IDs
142399731/142401971/142402865/142404153 and full source/payload/notebook hashes are
in each sanitized report. Runtime refs: f2dd41c (first two),767cf45 (Mini v2),
25f760b (Intern grammar); executed notebooks preserved at767cf45/25f760b/4e6b7a9
respectively. Current terminal wrappers are post-run safety changes, never
misattributed as native-executed code.

The Mini v1 INVALID is not corrected, aliased or relabeled. All recorded logits
are finite, independent decoder replay matches and FP32 score/softmax/value
counters execute with FP16 return. Thus this was a model vocabulary-following
failure on blank synthetic input, not a demonstrated loader/image/decode bug.
v2 proves that the same pinned model and adapter can emit a valid canonical
label. It does not promise validity for every real TRAIN image.

Original InternVL v5 still has its generated fences, INVALID and unavailable
HNLO. No old TRAIN image was called. Current baseline synthetic validity does
not invalidate v5's failure or establish that the original format is robust.

Reports under [diagnostic evidence](research/evidence/issue173/diagnostics/)
contain full per-file checkpoint identity through the original byte receipts,
model source/revision, effective implementation, generation, software and
resource observations, ZIP SHA/member verification, remote/submitted notebook
cell equality, strict-parser replay and exact call/load counters. Raw outputs,
token IDs and images stay in private Kaggle Outputs/local ignored storage.

## Review-held original TRAIN continuation

`scripts/minicpm173_train_review.py` makes the one-image path reviewable:
recheck all five exact original archives; verify all sealed new diagnostic
archives and no uncertain calls; rederive the hash-locked3763 master and exact
ordinal0 image; bind it to the original v5 image; load only MiniCPM with the
unchanged numerical adapter; reserve1load/1call; persist raw before strict
parse; label-only; export error/partial custody. Fresh runtime repeats resource
admission, never assumes earlier VM RAM transfers.

**launch, worker, once, CLI and the published TRAIN notebook are REVIEW HOLD
before I/O.** No flag, valid diagnostic receipt or empty VM bypasses the hold.
This prepared downstream path has CPU fence tests and shares the model adapter
verified on synthetic inputs; it has NOT run on TRAIN and is not advertised as
end-to-end TRAIN verified. ChatGPT must review the exact dispatch and cumulative
ledger before a separately committed activation. No new approval is fabricated.

Historical diagnostic source/notebooks remain in immutable refs and private
staging. Current diagnostic launch/worker/CLI and all four current notebooks
are terminal; the builder emits only archival notebooks. This prevents replay
through the current release, not remote revocation of old code copies.

## Reproduce evidence checks without GPU

```console
python -B -m scripts.report_diagnostic173 --archive <private-diagnostic.zip> --sha256 <sealed-SHA256> --output data/processed/issue173-verification/new-report.json
python -B -m unittest discover -s tests -p "test_kaggle173*.py" -v
python -B -m unittest discover -s tests -p "test_fresh_fulltrain*.py" -v
```

Native live sources are recorded separately from post-run terminal wrappers.
The frozen model adapters, parser, C1, checkpoint locks, fresh171 and six PREP
notebooks have no changes in this continuation. No merge or audit PASS claimed.

## Final CPU validation and remaining gates

Final terminal/dispatch/reporting runtime snapshot
`cc1d60e5a3cd090711c032efa17d0b9225012906`: Linux **56/56 Issue173 +55/55 fulltrain
PASS**, no skips/failures/errors. Receipts include source inventory, commands,
platform, log hashes and timing. Earlier live runtime snapshots also passed
51/55 (f2dd41c),53/55 (767cf45),54/55 (25f760b). Later changes are documentation,
sealed evidence and the diagnostic custody config; no live model source change.
This is not full-repository final-HEAD CI or independent audit.

Read-only final check of the four real diagnostic archives through the prepared
TRAIN custody reader passed, without an image/model read or call. All five
original smoke archives rehash unchanged. Structured privacy scan excludes
response text, raw/generated/returned token IDs, private sample IDs and secrets.

Remaining gates: scientific approval/comparability for the proposed InternVL
format variants; direct ChatGPT review and exact activation for MiniCPM's final
original TRAIN call; independent Antigravity audit and separately authorized
merge. No more diagnostic job is running or scheduled. The API approval service
briefly failed due to usage limits before a Linux command; that command did not
execute until the user requested continuation and approval service recovered.
No safety-review bypass, duplicated job or native call resulted.
