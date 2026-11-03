# Issue173 bounded model diagnostics — 2026-11-03

Authority: [Owner/ChatGPT directive6592812806](https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6592812806).
Same session, branch and Draft PR175. Original smoke stays Qwen1/InternVL1/Mini0.
Five archives and all terminal fences remain unchanged. No TEST, GT, TRAIN image,
fresh171 campaign or scientific score is used by these diagnostics.

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
