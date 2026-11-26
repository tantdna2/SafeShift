# InternVL grammar V2 — verified original ordinal0 technical result

Private [Kaggle job](https://www.kaggle.com/code/nguynanhtn/safeshift-internvl-v2-6626498951-j1),
version1, kernel142669354: **COMPLETE / SUCCESS**, strict parser **Level02**.
Exactly one model load and one native generation; original TRAIN ordinal0 identity
matches the master and original sealed smoke archive. No GT lookup or correctness
claim. HNLO remains `HNLO_NA_GRAMMAR_POLICY_V2`.

[Owner directive](https://github.com/tantdna2/SafeShift/pull/177#issuecomment-6626498951)
authorized this new namespace; [release6626992475](https://github.com/tantdna2/SafeShift/pull/177#issuecomment-6626992475)
binds the exact source, notebook and request. Runtime commit
`0553fe56c884eac9b0031e4a96e7a14568606f4f`; dispatched clean branch HEAD
`c67d41ab424fa6a4eb3baf61056a8e4e5b77ac66`. Handoff changes after that HEAD are
documentation/evidence only. Same branch `feat/internvl-grammar-v2-native`,
same Draft PR177. No merge; no further Kaggle job after this success.

## Identity and custody

| Item | SHA256 |
| --- | --- |
| Original TRAIN ordinal0 image | `a13ac091662772ec644b5382904dcdcd1606c296d145f41b7de4d513b8261d86` |
| Checkpoint shard1,4,954,007,064 bytes | `337d6d5bea97956480a1560c3a88e4e6c4455c3954b94ed468c367cf4b500f20` |
| Checkpoint shard2,4,511,078,400 bytes | `343234927f41c7d3a4aa8a2280864f477b1f77795463feb6b26910fa2e4921d3` |
| Checkpoint index | `4f5f24a16dc7fcba6edeb8df8482f633b369c284685f92c6e3d6069ee3b323e1` |
| Notebook bytes | `31c74d3250f0fd50680cb58c66ff801d89f72f976d33069a7f62e2de58a51e81` |
| Source spec | `80f1fbd39179b3d58c5bc26d42a6e3b0206c3fcd6c83ce8dfc335ca62be903ef` |
| Source manifest | `24d0f71cccbd3adb71ebc8cf8c8b443d6e2fc211032bb9ab3f101461cf47de21` |
| Request | `c6f34e7abb22cbb76425f7b48cba25188229e20372d98478b7b95bde91187ac5` |
| Private raw record | `0346b6434e3b5478cbc65716cf0f7bf951870dddd4895849602807360f9da677` |
| Private ZIP | `79c7901108b92a17cf458fb6085565ca6befce1ce38ba75b84803f0cd06509e9` |

Model `OpenGVLab/InternVL3_5-4B-HF`, revision
`6bd4487402110ef9889ba50eb7aefeb302526fed`, FP16 weights/eager attention, C1,
grammarV2 and strict parser unchanged. Series `internvl-v2-6626498951-technical-only`,
attempt `attempt-1`. The checkpoint has two shards; there is no invented single
checkpoint-file hash. Individual code/config hashes and all107 archive member
hashes are in [custody.json](research/evidence/internvl_v2_continuous_6626498951/custody.json).

ZIP3,566,373 bytes; SHA256 sidecar, CRC and exact member checksums PASS. Private
Kaggle Outputs retain the original ZIP and logs. Local ignored custody:

```text
data/processed/internvl_v2_native/continuous-6626498951/revision2/job1/output/
  safeshift-internvl-v2-6626498951-j1.zip
  safeshift-internvl-v2-6626498951-j1.zip.sha256.json
```

Raw is `sample/raw.json`; native IDs, processors, grammar and request accompany
`sample/steps/000..009.f32`, `.forward.json` and `.masked.json`. Raw/tokens/logits
are not committed. The exact short raw response is supplied in the Owner handoff;
this report records its checksum and parsed outcome.

## Memory repair and actual resources

Read-only8MiB streaming hashes all9,465,085,464 checkpoint bytes on each of two
passes. Descriptor identity/size/timestamps and locked hashes are checked. Advice
is restricted to already-consumed clean file ranges, with no Input writes,
global cache drop, weakened checksum or changed available-memory formula.
The original16GiB admission floor remains unchanged.

| Observation | Actual bytes / time |
| --- | --- |
| Job2 historical checkpoint file-accounting growth | 9,552,867,328 bytes |
| New preflight checkpoint file-accounting growth | 523,272,192 bytes |
| New loader checkpoint file-accounting growth | 16,384 bytes |
| Preload available RAM | 24,088,915,968 bytes /22.4346GiB |
| Loader available RAM after repeated SHA256 | 23,875,584,000 bytes /22.2359GiB |
| GPU0 peak allocated | 14,134,920,704 bytes /13.1642GiB |
| GPU0 peak reserved | 14,558,429,184 bytes /13.5586GiB |
| GPU0 total | 15,636,037,632 bytes |
| Setup / worker / isolated CPU processor | 268.407s /370.185s /14.345s, all EXITED0 |
| First / loader hashing | 112.665s /72.237s |

Two physical Tesla T4 GPUs, driver580.178.04; onlyGPU0 visible to native worker.
Worker CPython3.11.9 on Linux x86_64, torch2.6.0+cu124, transformers4.55.4,
tokenizers0.21.4; all pins and compiled CPU ABI PASS. Full actual version map,
cgroup/RSS snapshots and GPU memory receipts are in
[resources.json](research/evidence/internvl_v2_continuous_6626498951/resources.json).
Internal preflight was saved at monotonic862.534 before original image access;
loaded GPU receipt1049.118 and post-generation1074.794. Source-bound gates and
nonce permits enforce ordering, not merely these sampled timestamps.

Available RAM after model load was13.329GiB and after generation12.684GiB: the
16GiB requirement is a pre-load reserve, not a promise of16GiB unused throughout
inference. Recorded cgroup OOM counters remain zero. No whole-cohort or
worst-case-image memory guarantee follows from this single-image success.

Per job1800 server seconds; setup900s and parent1750s bounds. Conservative
reservation3600 physical-GPU seconds is retained without refund. Actual account
usage rose12945.311→13622.454 seconds, delta677.143s, reserved0 at terminal;
the quota API does not establish physical GPU allocation-time or a dollar cost.
Historical2400 reserved seconds remain charged; total recorded reservations6000.
Provider `metadata.last_run_time` disagrees with observation time, so it is retained
as reported and not used to infer run date or duration. See
[quota.json](research/evidence/internvl_v2_continuous_6626498951/quota.json).

## Logits, parser and verification

Ten native steps including EOS. Each PRE-grammar vector has151,936 float32
little-endian entries captured from forward output before processors; each
masked vector covers the same vocabulary. Tokenizer size151,679 is separately
recorded. Capture includes the actual native processor list and token history.
All raw vectors are finite; complete vector hashes, greedy/mask/token path and
independent decoder replay agree. Forced grammar step0 is recorded; it is not
evidence of scientific equivalence to unconstrained generation or valid HNLO.

Local saved-trace replay used the hash-locked public tokenizer plus independent
`tokenizers` decoder and the released source/request binding. It exactly matched
the Kaggle `TRACE_CONSISTENT` receipt,10 steps, strict parser SUCCESS/Level02.
No weights, image access or new model call was used. This is a local verification
of actual evidence, not independent Antigravity audit. See
[replay.json](research/evidence/internvl_v2_continuous_6626498951/replay.json).

The authenticated create-only [ledger](research/evidence/internvl_v2_continuous_6626498951/ledger.json)
contains exactly one submission, one load and one call plus terminal finished
record. No active submission remains. The generic historical proof string
`CONSUMED_OR_UNKNOWN` is retained in the verifier record; actual counts and
`consumption_reconciled=true`, private `consumption=COMPLETED`, raw/trace receipts
and COMPLETE establish this attempt's completed consumption. No zero-call refund
or second call is inferred from that string.

## Tests, resolved failures and limits

160 focused tests selected per platform: Windows native148 PASS/12 Linux-only
SKIP; Linux150 PASS/10 native-only SKIP. All160 executed PASS in at least one
environment, plus4 notebook tests. Tests include streamed hash equivalence,
short reads, advice failure, aliases/hardlinks, truncation, SHA mismatch, bounds,
unchanged RAM floor, preflight ordering, owner authentication, immutable history,
per-attempt nonce exclusivity and quota. Existing grammar/strict parser/capture
and historical campaign tests remain covered. Full repository suite was not run.

The first local test invocation used the wrong import path; the repository
qualifier supplies the tests directory and passed. The first native-CPU attempt
used a Python without torch; the existing isolated environment and pinned packages
then passed. Neither invoked Kaggle. A local inspection helper was renamed to
avoid shadowing stdlib `inspect`; this did not alter the running source.

Unused release6626931045 was rejected by exact Owner authentication because a
PowerShell text pipe substituted non-ASCII characters. The error was reproduced;
exact UTF-8 body hash60090d… was pinned and documented append-only. Followup50/55
campaign/continuous tests PASS (5 Linux-only skips) plus4 notebook tests PASS.
No further runtime change after the successful exact release; this byte-level
pin change is the only difference from the full160-test runtime. See
[CPU receipt](research/evidence/internvl_v2_continuous_6626498951/cpu-validation.json).

Execution commands (from repository root; existing authenticated local SDK):

```console
python -B -m scripts.qualify_internvl_v2_runtime --output <new-cpu-output>
python -B -m scripts.qualify_internvl_v2_runtime --output <new-native-cpu-output> --native-source data/processed/internvl_v2_native/public-source --packages data/processed/internvl_grammar_v2/packages --packages data/processed/internvl_v2_native/deps
python -B -m unittest discover -s tests -p test_internvl_v2_notebook.py -v
```

The executed submit command, recorded for provenance only (do not replay):

```console
python -B -m scripts.submit_internvl_v2 --continuous --approval-comment 6626992475 --notebook notebooks/SafeShift_INTERNVL35_GRAMMAR_V2.ipynb --stage data/processed/internvl_v2_native/continuous-6626498951/revision2/job1 --predecessor-directory data/processed/internvl_v2_native/continuous-6626498951/revision2/predecessors
```

All raw/error/history from old Job1/2 remains unchanged. No historical science,
GT, labels, prompt, revision, precision, grammar or parser was changed. No TEST,
full TRAIN, pooling or model selection. The technical objective is complete and
submissions stopped. **INDEPENDENT_AUDIT=PENDING_POST_RESULT;
SCIENTIFIC_QUALIFICATION=NOT_ESTABLISHED.** ChatGPT reviews the final GitHub HEAD
and Antigravity independently audits before any separately authorized merge/use.
