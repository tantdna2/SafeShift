# Issue #165 — native token / retained logits investigation in PR #166

**HARD_BLOCKED_EXISTING_ARCHIVE. VALID_HNLO: 0/155.** Numeric HNLO acquisition
is not complete. This supersedes the previous completion/audit handoff, pursuant
to [Owner comment6561913353](https://github.com/tantdna2/SafeShift/pull/166#issuecomment-6561913353).
**AUDIT_HOLD=YES; MERGE_AUTHORIZED=NO.** Same session, branch and Draft PR #166.
ChatGPT must inspect GitHub before deciding whether to commission any audit.

The original [archive report](MINICPM_SAVED_HNLO_165.md) and its receipt remain
evidence of the first investigation. This continuation tests additional hypotheses;
it does not reinterpret a zero count as achievement of the numeric objective.

## New observations on all155 SUCCESS

[Diagnostic source](../scripts/investigate_minicpm_aliases.py) rebuilds each packet
from the SHA-pinned original ZIP and requires equality with the prior exhaustive
proof's packet. Both Rust0.21.1 and the independent Python decoder check the
**entire actual input-ID sequence**, continuation prefix at position8, substituted
body, original suffix and terminal EOS. This extends the original32-token boundary
check. All155 pass these additional checks with both alternatives for each label:

| Label | Byte-fallback ID / piece | Ordinary ID / piece | Saved at step8 |
| --- | --- | --- | --- |
| Level01 | 1138 / `<0x31>` | 59345 / `1` | 59345 only |
| Level02 | 1139 / `<0x32>` | 59349 / `2` | 59349 only |
| Level03 | 1140 / `<0x33>` | 59362 / `3` | 59362 only |
| Level04 | 1141 / `<0x34>` | 59370 / `4` | 59370 only |

These are tokenizer metadata, not a published per-sample raw trace. None is
special, EOS, out of vocabulary, or an incomplete UTF-8 byte sequence. At the
actual prefix, each ASCII fallback byte already completes the same label digit;
it does not require a subsequent token to repair decoding. Input text containing
canonical label names is preserved, not globally replaced during the check.

All160 original records are freshly joined to archive custody; all1,760 steps
have the same seven-field capture schema and exactly the four ordinary sparse
coordinates. All155 SUCCESS retain their independent exhaustive ambiguity proof.
Five INVALID remain unchanged. There is no new qualified numeric score.

## Native generation does not exclude the fallback IDs

The exact public MiniCPM source is verified against the original runtime's
source inventory and public-source lock, not the latest model revision:

- [MiniCPM modeling source](https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/modeling_minicpmv.py),
  lines26 and227–238: instantiates `LlamaForCausalLM`, calls its `generate` with
  native embeddings, and returns IDs directly when `decode_text=False`.
- [MiniCPM tokenizer subclass](https://huggingface.co/openbmb/MiniCPM-V-4/blob/6f69a8235885be89608f3a71ffd40695b379e1e7/tokenization_minicpmv_fast.py)
  adds token properties; it does not implement a generation-time BPE admissibility mask.
- [Transformers4.51.3 Llama](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/models/llama/modeling_llama.py#L742)
  projects hidden states to `config.vocab_size` logits; line837 retains that vocabulary axis.
- [Transformers4.51.3 generation](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/utils.py#L3447)
  takes the last-position vector, applies processors, then greedy argmax at3478.
  Appending the selected ID at3485 does not call the tokenizer encoder.

The model's two downloaded files match the original public-source SHA pins.
The two Transformers files are tagged upstream4.51.3 source, downloaded and hashed
for inspection; freeze.txt attests that version. They are **not** a byte-for-byte
capture of the original installed Transformers files. The original runtime source,
recorded processors/config, raw vocab size and finite flag are complementary
evidence; no new model execution was used to strengthen that attestation.

Every original call records an empty actual processor list and no suppression,
forced tokens, constraints, sequence bias or watermarking. All-finite is captured
on the entire74k vector (exact size73,448) before processors. The source and these
receipts support inclusion of both coordinates in the score domain. Greedy
selection makes only one token the realized next output; that does not eliminate
the other labels' counterfactual coordinates from HNLO. Using argmax as the
admissibility test would eliminate the non-selected labels too.

The full-context witnesses prove admissible alternative IDs and decoding with a
fixed observed suffix. They **do not** claim the model would autoregressively
produce that same suffix after a counterfactual ID. No such replay was run.
Canonical BPE encoding chooses one representation of a string; native generation
does not enforce that representation. Decoding equivalence cannot justify
discarding an alternative, equating its logit, or modifying the unique-ID rule.

## What was actually retained

The archived runtime [capture source](https://github.com/tantdna2/SafeShift/blob/c3c223bc69edd253d57bbba9344e0633b65b3de4/safeshift/candidates/backend.py#L116)
indexes the forward vector with the probe's candidate IDs and writes those sparse
values, argmax, all-finite, dtype, step, origin and vocabulary size. The hook
examined a full vector in RAM; **examined is not retained**. Raw.json duplicates
those step dictionaries. `output_logits=False` and `output_scores=False` prevent
the native generate return object from retaining a second full-vector stream.
The four absent alias values cannot be inferred from argmax or the all-finite bit.

Known same-run storage was checked without reading image/GT/TEST contents:

| Location / provenance | Observation |
| --- | --- |
| `m160/final/` official ZIP + sidecar | Original pinned SHA,4,210 payload hashes plus checksum manifest |
| `m160/verified/` known extraction | Exact4,211-file membership and hashes match ZIP; no extra file |
| `m160/download-final.json` version2 output inventory |4,297 unique names:4,211 ZIP members,55 source files,25 corresponding bytecode,4 attempt markers,ZIP+sidecar |
| Output source tree | All55 paths match locked source inventory; all25 bytecode names map to those source files |
| Earlier `m160/hf/` archive filenames | Different archive identities; not used as logits for this INITIAL attempt |

The inventory digest is
`1d2b7e166c45ca9a71b6e57881f4c943b592c5a917b2ea5daa8b16670246aa41`.
It is an existing local receipt of a paginated output listing, also referenced by
the historical evidence index; **not** a fresh remote listing or independently
signed remote attestation. Exact membership, rather than tensor filename suffixes,
is checked, so an extra JSON vector would also fail classification. Source and
artifact schema explain the persisted capture; logs are not treated as logits.
This does not prove that no unknown external backup ever existed. A claimed
additional vector must supply its original custody, run/attempt/sample, prefix,
step, tokenizer/config/source hashes and capture boundary before it can be used.
Missing full vectors in other runs cannot fill these155 records.

## Why additional logits alone cannot unblock the current method

Two separate obstacles apply to all155 records:

1. The unchanged Method A requires exactly one ID per label in the whole
   non-special vocabulary. Both native-admissible alternatives survive. This
   obstruction remains even with every vocabulary logit supplied.
2. The archive lacks1138–1141 at the actual decision prefix. Four finite values,
   argmax and the finite flag leave these coordinates undetermined. A synthetic
   counterexample in the tests holds all observed coordinates and argmax fixed
   while changing missing alias mass. It is an identifiability demonstration,
   not fabricated real logits or an alternative metric implementation.

The scalar `logsumexp(z01,z02,z03)-z04` on the four saved coordinates is computable
and already passes three arithmetic oracles on155/155. It is **not qualified HNLO
under the current unique-token contract**. The blockade is not floating-point
arithmetic. A complete logit dump cannot turn a two-ID label into a one-ID label.

## Exact decision / acquisition needed; none executed or authorized here

There is no data-only acquisition that makes these same155 observed token paths
satisfy the unchanged uniqueness condition. A scientific decision about the
token-event definition is necessary before promising any valid score:

| Separately reviewable option | Required evidence / authorization |
| --- | --- |
| Keep current Method A unchanged | These155 stay unavailable. Only new, source-bound evidence that invalidates an alias in the **original** native domain could overturn this conclusion; current source/config contradict that exclusion. No proposed rerun automatically solves it. |
| Explicitly define one canonical token event per label | Approve a revised mapping policy and its interpretation, fixed independently of favorable logits/GT. Existing four same-step values may then be usable, subject to fresh method review; no new inference is intrinsically required. This is a contract change even if the scalar formula stays identical, and is **not implemented** here. |
| Explicitly define probability mass across aliases | Approve a different label-event/score definition first. At least the missing four coordinates at step8 of each155 prefixes (**620 values**) are needed in addition to the saved four; a full73,448-coordinate capture at those prefixes is preferable for completeness. The mapping, normalization and equivalence to any intended HNLO must be reviewed, not assumed. |

For the last option, an existing original same-step/full-vector capture with
verifiable custody is preferable. None was found in the retained locations above.
If it was never retained, producing it requires a **new authorized model forward**:
exact checkpoint/revision/FP32-resampler identity, original image/visual embedding
input, native prefix IDs through step7, generation/capture settings and a separate
run/attempt/evidence chain. Token IDs alone cannot reconstruct image-conditioned
logits. No such input/weights/model execution was accessed in this task.

A prospective teacher-forced replay would be new numerical evidence, not a
recovered original vector, and cannot be silently attached to the original raw
results. Authorization must specify data access, resources, bounded technical
verification first, replay purpose, custody and whether/how scientific use is
allowed. It would still require the prior definition decision. No GPU, Kaggle,
teacher forcing, rerun155/160, new selection rule or revised score is authorized
or performed by this report.

## Reproduce and inspect

Run the original [CPU verification](MINICPM_SAVED_HNLO_165.md#tái-lập-và-evidence)
to produce `records.private.json`; expected SHA is
`fa544e077faf8048029060946636f8d028977eea69ac79e913f23bb14e15684c`.
Keep the known extraction and historical download inventory. Fetch only these
four public source files into a fresh ignored source directory; the diagnostic
rejects any SHA mismatch (all SHA values are in the continuation receipt):

```powershell
$source = 'data/processed/issue165/native-source-reproduce'
New-Item -ItemType Directory -Path $source
$model = 'https://huggingface.co/openbmb/MiniCPM-V-4/resolve/6f69a8235885be89608f3a71ffd40695b379e1e7'
Invoke-WebRequest "$model/modeling_minicpmv.py" -OutFile "$source/modeling_minicpmv.py"
Invoke-WebRequest "$model/tokenization_minicpmv_fast.py" -OutFile "$source/tokenization_minicpmv_fast.py"
$transformers = 'https://raw.githubusercontent.com/huggingface/transformers/v4.51.3/src/transformers'
Invoke-WebRequest "$transformers/generation/utils.py" -OutFile "$source/generation_utils.py"
Invoke-WebRequest "$transformers/models/llama/modeling_llama.py" -OutFile "$source/modeling_llama.py"
$env:PYTHONPATH='data/processed/issue165-deps;tests'
python -B -m scripts.investigate_minicpm_aliases --archive data/processed/m160/final/minicpm4-0074f8bb22c4466ea33e0c5619ffc576.zip --records data/processed/issue165/final-head/records.private.json --inventory data/processed/m160/download-final.json --source-dir $source --extracted data/processed/m160/verified --output data/processed/issue165/continuation-reproduce
python -B -m unittest test_minicpm_alias_investigation test_hnlo_method_a test_minicpm_saved_hnlo test_pilot.HNLOTests test_triage test_triage_adapter -v
```

Use a new output directory per run. Exit0 means the diagnostic completed, **not**
that HNLO was obtained; read `status`, `numeric_goal_complete` and `hnlo_valid`.
Failures leave `INVESTIGATION_NOT_VERIFIED`, never a fabricated hard-block proof.
Environment receipts include command, Git HEAD, source hashes, versions and seed=null.
Third-party source is read as text only, never imported. No dependency change.

[Continuation receipt](research/evidence/issue165_hnlo/continuation_receipt.json)
comes from `data/processed/issue165/continuation02/`, with fresh per-record
witnesses SHA `d2e9469a6fb93ba6e35134c9579251e8110bc3edd18afed26eced59008ba255e`.
The original proof module, bridge, parser and formula are unchanged in this
continuation. Seven new handwritten synthetic adversarial tests cover native
context/special/missing-step rejection, extra-output detection, non-identifiability
and full-logit ambiguity. The focused suite passes140/140 on Windows CPython3.11.9
with tokenizers0.21.1. Final-HEAD rerun/log hashes are handed off in PR #166.
This is Codex technical evidence, not independent Antigravity audit or scientific
acceptance. Original160 results and original archive remain immutable.
