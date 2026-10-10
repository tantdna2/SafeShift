# LS1 independent experimental scorer — Draft handoff

Prepared against verified main `1722f82d5ced5624e5182a3311c7e0e24fca9458` on
2026-10-10. This is implementation for review, not a completed experiment or
execution authorization. No InspecSafe pixels/annotations, model weights or GPU
were used by Codex. Stop at Draft PR for ChatGPT review and Antigravity audit.

The Research Lead reports Qwen2.5 Accuracy 2.72% on 1,250 test images and
near-absence of Level04, with similar behavior in InternVL3. Those historical
artifacts were not supplied or independently audited here. The hypothesis is
that image discrimination may survive an output bias toward Level03. LS1 can
test that hypothesis; neither discrimination nor improvement is established.
Its design follows observation of benchmark behavior: do not claim the whole
study was designed independently of InspecSafe observations. Calibration itself
consumes no InspecSafe labels and fits no parameters.

## Method and limits

Both models retain official C1 bytes, revision, FP16/NONE, SDPA, native image
processing and single-T4 placement. The standalone LS1 scorer requests native
generation logits and scores; it never invokes the production generation
lifecycle. Existing runtime validation helpers are reused read-only. Generation
is greedy, batch one, with the existing 32-token cap and fresh cache/rope state.
The original checkpoint generation configuration and explicit overrides are
saved, including otherwise inactive sampling defaults.

T1 loads only `AutoTokenizer` from an existing revision-named snapshot with
`local_files_only=True`, `trust_remote_code=False`, networking denied. It hashes
tokenizer/config/template bytes against the existing immutable Hub inventory,
checks transformers/tokenizers/huggingface-hub versions, and records bare labels
and 28 JSON/whitespace/fence cases. Token IDs are derived separately for each
model. Missing bytes/libraries or wrong library versions are BLOCKED; wrong
hashes or unsupported tokenization are FAIL. The hash receipt identifies the
verified tokenizer subset, never claims weights were verified by T1.

For every schema-valid actual response, replace its label with each canonical
label and re-tokenize the entire response. Require identical prefix and suffix,
one varying position and four distinct token IDs. Require exact alignment with
the actual generated IDs after removal of at most one terminal EOS. Escaped
spellings, ambiguous positions, internal special tokens or multi-token branches
are unsupported and stop the run. There is no fallback to an approximate
sequence probability. P2.1 parsing is reused solely as LS1's acceptance rule;
this does not turn LS1 into a P2.1 result or modify any historical record.

At the proven decision step, let `z[i]` be the **raw model logits** for four
candidate tokens. LS1 reports `log_softmax(z)` and its probabilities conditional
on those four tokens. These are not guaranteed calibrated posterior class
probabilities. It separately records raw full-vocabulary log probabilities and
the total probability mass assigned to the four tokens. Low mass limits
interpretation. The subset softmax does not include the shared JSON prefix or
suffix probability. Generated labels come from **processed scores**, whose
global argmax must equal the generated token at every step; raw argmax may
differ. Raw values, processed values and argmax identities remain distinct.

Calibration uses fixed RGB 448×448 images: gray=(128,128,128), black=(0,0,0),
white=(255,255,255). The actual generated assistant prefix before the decision
token is teacher-forced after the same C1/native prompt for each reference.
Each reference call generates one token and saves its native raw trace. Its
fragment is a technical scoring call, not a canonical image classification.
Cache the three calls per exact prefix; never substitute sample logits. This
controls formatting context but makes the measured bias conditional on the
sample's generated prefix. It is not a universal image-independent prior.

Define `b[i] = mean_reference(log_softmax(reference_z)[i])` and
`calibrated_p = softmax(z - b)`, with fixed coefficient **1**. No temperature,
threshold, label-dependent parameter or train/test fitting exists. Uncalibrated
and calibrated modes share the identical sample `z`. References are uniform
images, not representative normal industrial scenes; their bias correction can
increase misses. No improvement, causal diagnosis or safety guarantee follows
from the formula. Argmax ties use the first class in canonical order.

The optional Level01 guard is **disabled in technical mode**. The pure CPU
calibration helper tests its proposed behavior: it retains only an
**uncalibrated LS1** Level01 decision when calibration
would change it. It does not protect an actual Level01 hazard originally scored
Level02/03/04, and does not refer to GT or the free-generated label. It can retain
false alarms. Its prediction can differ from calibrated argmax; both are saved.
Probabilities/AUROC stay unchanged. Tests exercise both preservation and the
missed-hazard limitation. Train/test execution remains locked with either guard
value; this PR grants no permission to run that ablation.

Native generation semantics were checked against the primary HF sources:
[4.51.3 generation](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/utils.py),
[4.52.4 generation](https://github.com/huggingface/transformers/blob/v4.52.4/src/transformers/generation/utils.py)
and [4.51.3 logit processors](https://github.com/huggingface/transformers/blob/v4.51.3/src/transformers/generation/logits_process.py).
Greedy `_sample` stores `next_token_logits` in `logits`, processed
`next_token_scores` in `scores`, then selects the latter's argmax. No beam or
sampling score semantics are assumed. Real GPU behavior remains unverified.

## CPU validation and T1

```powershell
python -m unittest tests.test_ls1 -v
python -m unittest discover -s tests
```

Pure probability, calibration, evaluation, checksum and fake native integration
tests require no torch/transformers/GPU. Synthetic Pillow drawing tests use the
already available Pillow, with no additional dependency installation.
Real tokenizer tests are opt-in through `LS1_QWEN_SNAPSHOT` and
`LS1_INTERNVL_SNAPSHOT`. SKIP is reported separately; never count it as T1 PASS.
Use each model's matching runtime environment for its tokenizer version:

```powershell
python -m safeshift.ls1.tokenizer --model qwen2_5 --snapshot data/processed/model-prep/66285546d2b821cf421d4f5eb2576359d3770cd3 --output data/processed/ls1/t1-qwen-first.json
python -m safeshift.ls1.tokenizer --model internvl3 --snapshot data/processed/model-prep/cb57a075cb75a2e6d1b668b128d48bb00ae321d2 --output data/processed/ls1/t1-internvl-first.json
```

The paths above are examples, not a new dataset/model layout requirement.
Local T1 Qwen2.5=BLOCKED and InternVL3=BLOCKED: neither complete snapshot nor
matching transformers/tokenizers installation is present. No tokenizer or model
was downloaded. See [validation record](ls1_validation.md) for actual checks.

## Source and existing Runtime Prep preparation

After reviewing the exact branch HEAD, export only committed source. Use a new
output directory under `data/processed`; untracked data/weights are excluded by
`git archive`. This owner CPU preparation does not require GPU or a new model.

```powershell
python -m safeshift.ls1.kaggle --bundle-source --repo . --output data/processed/ls1/source-first
```

Save `ls1_source.tar`, `ls1_source_release.json`, its `source_commit` and trusted
`archive_sha256`. Upload/attach that small source output to Kaggle. The notebook
checks the externally entered SHA, receipt checksum and embedded Git archive
commit before importing its code. These checks establish consistency with the
owner-reviewed artifact; they do not replace GitHub review or authenticate an
arbitrary attachment based only on its self-declared receipt.

Reuse the original Model Prep and Runtime Prep outputs. InternVL3 uses its
matching FIX v2 outputs. Model files are independently checked against the
existing per-file pinned hashes, including weights, before use. Runtime
executable bytes are checked **before any metadata probe executes them**:
create one small inventory from the exact saved Runtime Prep directory, then
attach it as a separate supplementary receipt (outside the Runtime Prep tree).

```powershell
python -m safeshift.ls1.kaggle --repo . --inventory-runtime data/processed/existing-runtime-prep --output data/processed/ls1/ls1_runtime_inventory.json
```

Record the printed SHA-256 independently and enter it in SETTINGS. This hashes
the existing files/archives without installing, rebuilding or modifying them.
The inventory uses input-relative paths. External symlinks in a live runtime
tree are refused; use the original portable prep archives instead. `.tar`,
`.tar.gz`, `.tgz`, `.tar.xz`, managed Python plus separate venv archives and
internal links are supported. Old venue-specific external venv symlinks are
skipped during restore; exact managed Python/site-packages must still work.
Several distinct matching runtimes are an ambiguity, never an automatic choice.

## Kaggle technical run

Open the appropriate notebook:

- [Qwen2.5](../notebooks/ls1_qwen2_5_kaggle.ipynb).
- [InternVL3](../notebooks/ls1_internvl3_kaggle.ipynb).

Add Input: reviewed LS1 source prep, existing model prep, matching runtime prep,
and the supplementary runtime inventory. Set Internet OFF and T4. Edit **one
SETTINGS cell**: exact source SHA, trusted source archive SHA, trusted runtime
inventory SHA, and Internet confirmation. Model/runtime/source paths can remain
empty if discovery is unambiguous. If attachment names differ or several match,
use paths relative to the attached input root; executable and site-packages
paths are explicit overrides under the verified runtime input.

Run All **once**. The child exposes GPU 0 only, requires exact Linux x86_64,
Python 3.11.11 and all existing runtime pins, T4 CC7.5/CUDA12.4, FP16/NONE,
no offload/fallback, model checksums and T1 PASS before generation. Offline
environment is set before torch import and Python networking is denied. There
is no pip, HF download, retry, resume or environment fallback.

Default `mode="technical"` uses four deterministic colored drawings outside
InspecSafe and the three reference images. It supplies no semantic GT and emits
no accuracy report. Runtime/snapshot/T1/storage/token alignment/nonfinite errors
stop safely and leave failure artifacts. Invalid semantic responses stay
INVALID and are never forced to a label. A run directory and notebook launch
directory are exclusive; rerunning an existing attempt refuses overwrite.
Preserve failed evidence and obtain any new attempt rights externally.

## Train/test rights — both locked

This task authorizes implementation and synthetic/CPU validation only. The new
LS1 execution decision is **PENDING** in DECISIONS.md. P2/P2.1 authority grants no
LS1 permission. **Train and test are unconditionally LOCKED in this revision.**
After the unchanged model/mode/run-ID/source-SHA/guard type checks, both modes
raise exactly:

```text
PermissionError("LS1_SPLIT_EXECUTION_LOCKED_PENDING_DEC_LS1_001")
```

The rejection occurs before reading approval JSON, dataset, tokenizer, model or
runtime, and before reserving an attempt or creating outputs. A self-created
receipt with all former fields and a matching SHA-256 is still rejected without
being read. The receipt parser and launcher receipt path resolution were removed;
the dataset helper also rejects direct calls. Notebook execution cells reject
train/test before even reading the source package. No environment variable,
receipt, configuration option or alternative launch path opens the lock.

Technical mode requires no approval, uses only the four generated drawings and
three fixed references, and rejects an enabled Level01 guard. A future Research
Lead decision must be addressed in a separately reviewed change; this PR creates
no new approval mechanism and does not change DEC-LS1-001's PENDING status.

## Artifacts, recomputation and metrics

All run artifacts live in `data/processed/ls1/runs/<run_id>/`. They include
run/method/source/prompt identity, complete prompt/hash, software/hardware,
snapshot hashes, trusted runtime input inventory, cohort IDs/image checksums,
T1 evidence, native raw response text/IDs and per-step scores, reference call
records, results, status/failure and an exact checksum inventory. Artifacts are
new files with fsync and verified reread. No historical P2/P2.1 files are opened
for rewriting or replaced. The Kaggle output includes a checksummed result tar
archive, receipts and failure evidence. Temporary launch settings may contain
venue-resolved paths and are excluded from the research archive.

Raw traces retain every generated step's candidate logits/scores, generated
token value, full-vocab argmax/value, float64 logsumexp and NaN/+Inf/-Inf counts.
They avoid storing full 150k-token vocabularies for every sample. They suffice
to recompute the LS1 probabilities/calibration and inspect recorded selection
evidence, **not** to reconstruct arbitrary token distributions or independently
prove a summary's authenticity. Nonfinite values are explicit strings and counts,
never non-standard JSON NaN. Full model outputs were never discarded in favor
of just predicted labels. Exact checksum inventory cannot detect coordinated
forgery of all files; retain the independently recorded package checksum.

```powershell
python -m safeshift.ls1.audit --run data/processed/ls1/runs/EXACT_RUN_ID
```

The CPU-tested evaluator supports uncalibrated and calibrated Balanced Accuracy,
Macro-F1, descriptive Accuracy, full-cohort Level01 and Level04 Recall,
parse-conditional FPR/FNR, failure-aware anomaly non-detection, Level01 protection
failure, four-class-plus-INVALID confusion matrices, binary anomaly AUROC and
four-class one-vs-rest/macro AUROC.
AUROC ranks log class probabilities and anomaly log odds (monotone in
`1-p(Level04)`) to avoid probability underflow and subtraction saturation.
No decision threshold is chosen. Every denominator is explicit. Undefined
supports/rates are null, never zero; fixed four-class macro scores require all
four GT classes. INVALID adds FN to its true class, never an invented FP.
AUROC excludes missing scores explicitly and is score-conditional; no AUROC is
claimed for the full cohort when INVALID exists. Optional guarding affects
predicted labels, not calibrated AUROC scores. These are prepared reporting
semantics; current locked train/test paths produce no dataset metrics.

Reports separately enumerate Level01/02/03→Level04 changes, sample IDs, actual
anomaly misses and true Level01 misses, and generated-label→Level04 changes.
Inspect these alongside normal recall/FPR: an apparent gain on the majority
class can conceal loss of hazard recall. P2, P2.1 and LS1 are distinct; old P2
results do not become P2.1 and none become LS1. LS1 is excluded from current RQ3.
No retrospective threshold choice or label-conditioned calibration is allowed.

Before GPU work: ChatGPT review, independent Antigravity audit, real snapshot
and runtime input checksums, model-specific T1 PASS, correct Kaggle offline/T4
preflight and a fresh approved technical attempt. InspecSafe execution remains
unavailable in this revision even if a receipt is supplied. A separate Research
Lead decision and reviewed implementation change are required before any future
split execution. These are missing external conditions, not completed milestones.
This Draft PR is not merged.
