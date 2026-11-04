# InternVL3.5 grammar V2 native integration

Scope: implementation and CPU synthetic verification only, based on merged
PR #176 (`4578c175e0011783c3573d0003fc5341eaf3ef72`) and its
[post-merge handoff](https://github.com/tantdna2/SafeShift/pull/176#issuecomment-6621575815).
The Owner-approved method, immutable grammar/descriptor, checkpoint, C1,
official parser and HNLO N/A policy remain fixed. This document is the design
record before implementation; verification results will be added in this PR.

The new runtime will use a separate technical qualification identity, with no
historical prediction import and no enrollment in a scientific full-TRAIN series.
Its conservative engineering ceiling is one load, one call and 1800 seconds;
these limits do not grant a call. All public native entrypoints must reject
execution before Input/model access. No editable notebook flag or JSON approval
field may open the fence. A later reviewed exact-run release must establish
authority, remote anti-replay custody, Input/sample hashes and resource bounds.

Native generation uses the existing offline InternVL loader and preprocessing,
then the approved V2 callback. Each full vocabulary forward vector must be saved
and fsynced before the native prefix processor runs. The actual processor list,
prefixes and masked vectors are recorded; native returned IDs precede decode,
and exact response bytes precede official parsing. Independent tokenizer/trace
verification is required. Every result, including failures, has numeric HNLO
null and `HNLO_NA_GRAMMAR_POLICY_V2`.

The notebook will package hash-bound sources and run isolated setup/preflight
children with bounded logs and process-group deadlines. Preflight checks unique
Input/checkpoint markers, source/weight hashes, pinned Python/packages/ABI,
physical GPU/driver and child CUDA, RAM/cgroup, filesystem reserves and actual
scratch allocation, plus synthetic native tokenizer/image-processor/grammar
composition. No model weights are loaded by preflight. Repeated preflight uses
new diagnostic output directories and consumes no execution attempt.

CPU tests must exercise the shared controller/native capture path with scripted
synthetic logits, plus malformed JSON, EOS/prefix/processor drift, hash mutation,
write/log failures, timeout and load failure. Outputs are private by default;
only sanitized synthetic receipts belong in Git. CPU evidence never establishes
Kaggle readiness, real model fit, inference quality or scientific qualification.

Stop at one Draft PR for ChatGPT review. No Kaggle submission, GPU/model load,
TRAIN/TEST image access, full3763 inference or merge in this task.
