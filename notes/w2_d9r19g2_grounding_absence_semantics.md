# D9R19G2 — absence semantics source audit

Date: 2026-10-04. Task:
`W2.6-D9R19G2-QWEN3-PALIGEMMA-ABSENCE-SEMANTICS-RESOLUTION`.
Fetched `origin/main` equals required BASE
`dd83c6231e5758cdb85ba84e293d4b462e38a696`.
Branch: `w2.6-d9r19g2-grounding-absence-semantics`.

**Both blockers remain BLOCKED.** No exact valid native zero-detection output
was established by the inspected authoritative sources. This is a bounded
negative finding, not a claim that no such source exists anywhere.

The [audit manifest](../configs/pre_freeze/grounding_absence_semantics_audit.v1.json)
records URLs, revisions (or explicitly mutable snapshots), SHA256, byte sizes,
locators, findings and limits for 29 inspected source/documentary files. Its
version is an audit-record version, **not a new parser/qualification contract**.
No v3 contract is created without a resolution. Candidate v2.0 and its v2
source/plan/lock remain in effect and byte-unchanged.

## Qwen3: evidence and missing link

Official repository revision: `96588727e44c78b25ba03ea03b8e12f7e64fd0da`.
The recursive tree was complete (`truncated=false`). Scope includes the 2D
cookbook, ODinW-13 input/parser/evaluator and fine-tuning preprocessing.

- [ODinW input construction](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/dataset_utils.py#L149)
  constructs a prompt from category names, but constructs no absent answer.
- [Official evaluation parser](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/run_odinw.py#L215)
  removes fences, uses `ast.literal_eval`, iterates predictions and skips invalid
  bbox lengths. An empty iterable produces empty boxes; the exception branch
  also produces empty boxes and labels. Thus evaluator acceptance alone cannot
  distinguish valid absence from parsing failure. None of these permissive
  operations is adopted by SafeShift.
- [COCO serialization](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/evaluation/ODinW-13/eval_utils.py#L32)
  initializes an aggregate list and JSON-dumps it after appending evaluated
  boxes. This is **evaluation artifact serialization**, downstream of the
  permissive parser, not construction of a native assistant answer when every
  requested category is absent. Its empty array is not the missing proof.
- [Training preprocessing](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/qwenvl/data/data_processor.py#L140)
  passes supplied assistant conversation text into the processor/template.
  It does not construct grounding target text from a zero-object annotation.
  The companion `tools/process_bbox.ipynb` illustrates positive coordinate
  conversion for Qwen2/Qwen2.5; it cannot establish Qwen3 absence semantics.
- [2D cookbook](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/cookbooks/2d_grounding.ipynb),
  cells 8–10, describes omission of negative categories. It does not demonstrate
  all-requested-categories-absent serialization. Positive arrays and omission
  are insufficient to select `[]`.
- [Technical report v1](https://arxiv.org/html/2511.21631v1#S3.SS2.SSS4)
  describes box annotation construction and the 0–1000 coordinate system;
  sections 3.2.4/5.5 do not specify the all-absent answer string.

Decision: `QWEN3_ABSENCE_SEMANTICS_BLOCKER` retained. Native zero output remains
unknown. `[]` (including legal JSON whitespace) continues to return `BLOCKED`
with canonical detections `None`; blank/null/prose/malformed forms remain
`INVALID`, never a successful empty detection tuple.

## PaliGemma: target construction, tokenization and decoding

Official `google-research/big_vision` revision:
`0127fb6b337ee2a27bf4e54dea79cff176527356`. Recursive tree complete
(`truncated=false`). Inspected PaliGemma preprocessing, transfer config,
segmentation target/evaluator, tokenizer interface and decoding source.

- [Training/evaluation suffix plumbing](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/configs/proj/paligemma/transfers/common.py#L29):
  training tokenizes a supplied suffix with EOS. Evaluation defaults a missing
  *input* suffix to an empty string without EOS so generation can start. This
  default is not a zero-detection answer and must not be mistaken for one.
- [Tokenization and string join](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/pp/proj/paligemma/ops.py#L89)
  provide generic EOS and string-reduction operations. No inspected detection
  target builder connects an empty set of matching objects to these operations.
  Hypothesis: an empty suffix could be represented with EOS; missing premise:
  the `detect {label}` training contract actually chooses that suffix for an
  absent label. The hypothesis is not adopted.
- [Actual RefCOCO target construction](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/pp/proj/paligemma/segmentation.py#L37)
  requires one bbox with shape `[4]`, one reference and a mask. It constructs
  location plus segmentation tokens. The transfer config chooses an annotated
  object first. This proves a segmentation target path, not zero-detection
  serialization for PaliGemma 1 mix. Its quantization is not substituted for
  the existing detection coordinate contract.
- [Tokenizer interface](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/pp/tokenizer.py#L29)
  documents EOS handling, while [decode stopping](https://github.com/google-research/big_vision/blob/0127fb6b337ee2a27bf4e54dea79cff176527356/big_vision/trainers/proj/paligemma/predict_fns.py#L215)
  recognizes EOS independently of object presence. Neither maps absence to EOS.
- [Official PaliGemma 1 demo](https://huggingface.co/spaces/big-vision/paligemma-hf/blob/d914d4446a6ff8c5b3110411abca69887f035c41/app.py#L280)
  and [companion parser](https://huggingface.co/spaces/big-vision/paligemma/blob/b19d492be08ec5e8aad190a522db919d4444f529/paligemma_parse.py)
  have permissive empty/no-match extraction. That behavior is not an
  authoritative training target. Download hashes match the G1 source pins.
- [Google task syntax](https://ai.google.dev/gemma/docs/paligemma/prompt-system-instructions#prompt-task-syntax)
  documents `detect` prompts, without the zero-object target. The
  [PaliGemma report v2](https://arxiv.org/html/2407.07726v2#S3.SS2.SSS5)
  describes detection pretraining and general suffix/EOS layout without that
  missing rule. The model card similarly gives output types, not zero syntax.

Other leads were checked and rejected: the current fine-tuning notebook is
a PaliGemma 2 caption tutorial; `reward_tune/detection_reward.py` uses a different
2023 detector token representation. Official-repository issue search for
`detection` returned #106/#113: a contributor points to the generic colab, and
a community comment points to third-party fine-tuning. Neither supplies the
required original-checkpoint training contract. No issue/comment was posted.

Decision: `PALIGEMMA_ABSENCE_SEMANTICS_BLOCKER` retained. Exact empty decoded
text remains `BLOCKED` with detections `None`. Literal EOS text, whitespace,
`[]`, prose and malformed loc strings remain `INVALID`. No source proves that
empty decoded text/EOS-only is valid zero detection for the pinned mix model.

## Reproduction, scope and validation

Source-only downloads were stored under ignored
`data/processed/d9r19g2_source_audit/`. No downloaded module/notebook was imported
or executed, and no weights or dataset were downloaded. Notebook cells were
read as JSON/text. The source notebooks can contain embedded upstream example
assets; those files stay ignored and are not qualification inputs.

To repeat source verification: fetch each manifest `url` as bytes; compare
`bytes` and SHA256; read the indicated locator. Git sources are commit-pinned;
arXiv reports are versioned; Google pages and issue comments have no immutable
revision and their hashes identify only this accessed snapshot. Search result
lists are mutable and are not proof of exhaustive absence. Official issue
queries used `gh search issues QUERY --repo REPO --limit 30 --json number,title,url`
(limit 50 for `detection`). Unrelated results were not used as evidence.

Offline checks use handcrafted strings only; no historical SafeShift model
output was read to infer a rule. No dataset/split/label/metric changed. No
historical gate result, adapter, model role, fixture, parser or prompt changed.
Nine G1 files have Git-normalized SHA256 protection in the new audit; the existing v2 lock
also protects historical Git blobs. DECISIONS/TASKS must retain their BASE bytes
as a prefix (Git-normalized LF) and receive only new append records.

Environment: Python 3.11.9, Pillow 11.3.0, zlib 1.3.1; stdlib unittest/hashlib;
no randomness or seed. Focused commands, from repository root:

```text
python -m unittest tests.test_grounding_absence_semantics_audit tests.test_grounding_interface_v2 -q
python -m unittest tests.test_qwen3_external_gate tests.test_qwen3_external_gate_result tests.test_paligemma_external_gate tests.test_paligemma_external_gate_result tests.test_paligemma_interface_candidate tests.test_external_gate_cases tests.test_d9r7_paligemma_source_api_audit tests.test_d9r15_five_model_roster_exploratory_grounding tests.test_qwen_runner tests.test_paligemma_prep -q
git diff --check
```

Validation: **43/43 focused tests PASS; 267/267 relevant regression tests PASS**
(310 combined). The regression selection covers native runners, historical
gate/parser/result paths, source audit, fixtures and roster/exploratory policy.
Strict JSON parse and local rehash of all 29 downloaded sources PASS.
`git diff --check` PASS. Nine G1 file hashes and the v2 lock's 61 historical
Git blobs are unchanged; logs retain their BASE prefix. The first focused run
also verified same-checkout raw byte hashes for all nine G1 files; the final
portable regression uses Git-normalized hashes for notes/tests while the
retained v2 lock enforces exact contract bytes.

Full repository suite was not run: validation is scoped to this documentary
addition and its affected interfaces; no full-suite PASS is claimed. The
unrelated D9R18 task-diff allowlist module is outside this regression selection
(G1 already documents its incompatibility with later task scopes). No old tests
were edited or disabled. Source implementation was inspected, never executed;
offline parser tests do not establish model conformance or qualification.

```text
NEW_CONTRACT_VERSION=NONE (both blockers retained; v2 unchanged)
QUALIFICATION_EXECUTION=NOT_RUN
QUALIFICATION=NOT_RUN
execution_authorized=false
MODEL_GPU_EXECUTION=NO
INSPECSAFE=NOT_RUN
PROMOTION=NO
MERGE=NO
```

G1 closure: PR #68 merged at `dd83c6231e5758cdb85ba84e293d4b462e38a696`.
Historical G1 `MERGE=NO` statements remain preserved. PR #67 is separately
OPEN/DRAFT at `e85300ab3ec122f819a2685613332578f7e203d8`; no mutation requested.
