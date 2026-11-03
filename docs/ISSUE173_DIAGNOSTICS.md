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
If it is INVALID, test a versioned formatting reminder in the user message,
without changing original C1 bytes. If still INVALID, test assistant JSON
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
