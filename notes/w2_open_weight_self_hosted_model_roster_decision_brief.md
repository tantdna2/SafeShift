# W2.5 D9 Decision Brief — Open-Weight Self-Hosted Model Roster Revision

**Decision ID:** `DEC-W2-D9-009`
**Date:** 2026-09-20
**Status:** APPROVED FOR IMPLEMENTATION, PRE-FREEZE
**Protocol freeze:** `PENDING`
**InspecSafe inference under this revision:** `NOT RUN`

## 1. Decision scope

D9 revises only the **P2 model roster and execution backend** selected in D8. It does not alter the scientific framing, dataset, split, labels, hazard taxonomy, metrics, bootstrap procedure, or the benchmark firewall.

The Seminar remains a **frozen zero-shot cross-domain robustness evaluation**. No SafeShift training or fine-tuning on InspecSafe-V1 is introduced by D9. Source-domain training / fine-tuning remains P4 (Thesis / later Domain Generalization work) unless a future approved decision explicitly changes that scope.

D9 supersedes **ONLY the P2 commercial-hosted-provider roster/backend assumptions from D8**. The former Qwen Singapore workspace endpoint, provider billing, GPT/Claude external-provider gates, and live hosted-route verification are `SUPERSEDED_FOR_P2_BY_D9` and no longer P2 protocol-freeze blockers. Their existing files and history remain preserved as historical D8 implementation evidence; they are not deleted or rewritten. Hosted decoding settings are also historical: D9 must pin supported self-hosted settings before freeze, without automatically inheriting the hosted Qwen temperature-zero policy.

D9 does **not** supersede D8's P1 upstream reproduction policy. P1 continues to use the upstream prompt/task policy and `temperature = 0.1`, with the existing `REPRODUCIBLE`, `COMPATIBILITY_REPRODUCTION`, and `NOT_EXACTLY_REPRODUCIBLE` reporting policy when exact upstream model access differs.

## 2. Preserved D8 contracts

The following D8 contracts remain binding:

- Benchmark Firewall and blind-development rules: no InspecSafe capability probing, prompt tuning, parser tuning, threshold tuning, or model selection before protocol freeze.
- Protocol Freeze before the first InspecSafe inference.
- C1 policy-aware safety classification.
- A2 two independent calls: Call 1 classification and Call 2 grounding do not receive each other's outputs.
- B2 closed 12-hazard grounding vocabulary from D6.
- D4 canonical spatial representation, deterministic adapters/parsers, and raw-response preservation before parsing.
- Capability-aware grounding: classification applies to the full selected roster; grounding applies only to models with verified spatial output capability.
- D5 metrics and statistical protocol without modification.
- Post-freeze change control; no performance-driven model or prompt rescue after benchmark results are visible.

D1–D7 remain unchanged, including original split provenance, domain/mismatch policy,
D6 support census, D7 annotation limits and the approved RQ2 hierarchy erratum:
12 atomic hazards are primary strata; seven grouped A–G categories are secondary
exploratory summaries. Post-freeze technical fixes still require an issue, protocol
version bump, invalidation of affected runs and rerunning the relevant evaluation pools.

## 3. Model-selection principle

The P2 roster is chosen **before any InspecSafe inference** and based on research value first. Compute venue is operational infrastructure, not a scientific selection criterion.

Allowed execution venues include a local workstation, Google Colab, Kaggle, or a rented GPU host. A change of venue does not create a new model condition if the exact frozen model revision, preprocessing, decoding, precision/quantization policy, software environment, prompts, and adapters remain equivalent and are recorded.

No model may be promoted, removed, or replaced because of its InspecSafe score.
Full-model backup substitution is allowed only before protocol freeze and before
any InspecSafe inference, when an objective, pre-specified blocker prevents the model
from participating in classification. Allowed reasons are unavailable exact model/weights,
incompatible license/access, inability to load or run the classification runner stably,
failure to produce valid parseable classification output, repeated model/runtime crashes
under the validation procedure, or confirmed compute/runtime incompatibility preventing
classification. Record the reason and validation evidence before substitution. The
validation procedure must be specified before validation; its execution remains pending.

If the classification runner/interface is valid and its output parses, the model
**must remain in the classification track**, even if it fails the spatial grounding
gate or has only a native-point interface incompatible with D5 bounding-box grounding.
Set its grounding role to `NOT_PARTICIPATING`; **do not activate a backup** and do not
assign artificial `IoU = 0`. Grounding-only failure is never a reason to remove a model
from the classification roster.

## 4. Primary P2 roster

### M1 — Qwen3-VL-8B-Instruct

- Exact repository/model ID candidate: `Qwen/Qwen3-VL-8B-Instruct`.
- Research role: **anchor and reproduction bridge** to the upstream InspecSafe study, which already evaluated Qwen3-VL variants.
- P2 classification: candidate.
- Grounding evidence: official Qwen3-VL material documents spatial understanding and grounding capabilities; SafeShift still requires the frozen synthetic gate for its own wrapper/parser contract before final grounding eligibility is assigned.
- License observed at review: Apache-2.0.

### M2 — Ovis2.5-9B

- Exact repository/model ID candidate: `AIDC-AI/Ovis2.5-9B`.
- Research role: open-weight comparison with a different visual stack while retaining a Qwen3-8B language backbone; this is a descriptive architectural contrast, not a causal experiment.
- P2 classification: candidate.
- Grounding evidence: official model material documents both point and bounding-box outputs; coordinates are documented as normalized to `[0,1)` with top-left origin.
- License observed at review: Apache-2.0.
- Important constraint: do not infer or repair a coordinate scale from benchmark outputs. The exact frozen model revision and documented native format must be validated on synthetic cases before the adapter is frozen.

### M3 — Molmo2-O-7B

- Exact repository/model ID candidate: `allenai/Molmo2-O-7B`.
- Research role: independent OLMo-family model to reduce over-concentration on Qwen-derived language backbones.
- P2 classification: candidate.
- Grounding evidence: official Ai2 material documents image/multi-image/video grounding and point-driven localization. Molmo's native pointing representation must remain point-native unless a documented model interface emits a box; SafeShift must not fabricate bounding boxes from a point.
- License observed at review: Apache-2.0 for the model repository. Dataset/source-use conditions must be reviewed separately before final freeze where required by the model card.

### M4 — Gemma 4 12B IT

- Exact repository/model ID candidate: `google/gemma-4-12B-it`.
- Research role: independent current Google open-weight multimodal family, increasing model-family diversity.
- P2 classification: candidate.
- Grounding: `PENDING_EXTERNAL_GATE`; no generic bounding-box capability is assumed by D9. If the model does not satisfy the external spatial gate, it remains classification-only and receives no synthetic zero grounding score.
- License observed at review: Apache-2.0.

## 5. Backup order

Backups are frozen by order before benchmark results are visible:

1. `google/paligemma2-10b-mix-448` — explicit object-detection/segmentation task support; Hugging Face access requires accepting Google's Gemma usage terms. It is not treated as an Apache-2.0 model.
2. `openbmb/MiniCPM-V-4.6` — compact open-weight multimodal model; useful if a primary model is operationally infeasible. License observed at review: Apache-2.0.

Backups are not extra benchmark entrants by default. A backup enters the primary roster only through the classification-blocking replacement policy above, with the reason recorded before protocol freeze and before any InspecSafe inference. An activated backup must meet the same revision/provenance, runner, decoding, interface and applicable synthetic-gate prerequisites before final role assignment. Passing the spatial gate is required only for grounding participation; a classification-valid backup with grounding-only failure also remains in classification with grounding role `NOT_PARTICIPATING`, without further substitution or an artificial zero grounding score.

## 6. Capability policy under D9

All four primary models are intended to enter the classification track after local/self-hosted runner validation.

Grounding eligibility is assigned only after documentation review plus the frozen external `SYNTHETIC V1` Target+Distractor gate:

- Qwen3-VL-8B-Instruct: documented spatial capability; synthetic gate still required for SafeShift integration.
- Ovis2.5-9B: documented point/box capability; synthetic gate still required for SafeShift integration.
- Molmo2-O-7B: documented point-driven grounding; compatibility with the approved box interface is unresolved. Point documentation alone does not qualify the model for the existing grounding track. Preserve native points in raw output; do not convert a native point into a fabricated box.
- Gemma 4 12B IT: classification-only unless the pre-specified external gate provides qualifying spatial evidence.

Failure to participate in grounding is `NOT PARTICIPATING`, not `IoU = 0`.

The D8 evidence hierarchy remains binding: Level 1 or Level 2A is required for
grounding; Level 2B format operability and Level 3 unverified spatial output are
insufficient. D9 additionally requires wrapper validation on the frozen synthetic
suite for its selected self-hosted interfaces; this does not transfer D8 hosted
eligibility automatically to a new runtime.

**Box/point boundary:** The unchanged [canonical schema](../schemas/canonical.schema.json)
and D8 gate require boxes. [D5](w2_metrics_statistics_decision_brief.md) defines Pointing Hit
using a predicted box's center inside original GT polygons, not a native-point-only
track. Retaining native points as raw evidence does not extend the canonical schema
or authorize point-to-box conversion. Until a qualifying box interface is verified,
a point-only model remains a classification candidate and `NOT PARTICIPATING` in
current grounding. Any point-only schema, gate or metric extension requires a separate
approved decision; D9 does not introduce one. No D5 definition changes here.

## 7. Active D9 pre-freeze checklist

1. Freeze exact model IDs **and immutable revisions**, access/license evidence, and weight provenance for the four primary candidates and two backups.
2. Implement local/self-hosted runners with explicit preprocessing, precision/quantization, device, software-version, and raw-output provenance.
3. Pin one low-variance decoding policy per model before benchmark inference; no empirical selection on InspecSafe.
4. Implement deterministic native-output adapters/parsers compatible with the unchanged canonical box schema. Preserve native points in raw output; no fabricated boxes or implicit point-only track.
5. Review interface eligibility for all four primary candidates and execute the unchanged 8-case `SYNTHETIC V1` Target+Distractor gate on qualifying box interfaces; no InspecSafe images. Fix the qualitative giant-box review procedure before execution, without inventing numeric pass thresholds. Record point-only incompatibility or spatial-gate failure as `NOT_PARTICIPATING` in grounding; retain valid classification participation without substitution or an artificial zero score. The same rule applies to activated backups.
6. Assign final classification/grounding roles and record any backup substitution only for an evidenced, pre-specified classification blocker before protocol freeze and before any InspecSafe inference; never use InspecSafe scores.
7. Complete and freeze exact prompts, schema, adapters/parsers, runner environment, and the full D5 metric engine.
8. Record `protocol_freeze_commit_sha`, then and only then begin W3 InspecSafe inference.

The historical D8 provider-specific checklist remains audit evidence, but its Qwen workspace endpoint, GPT/Claude provider gates, commercial billing, and provider live-route items are `SUPERSEDED_FOR_P2_BY_D9` and are not active blockers for the self-hosted P2 path. All eight D9 prerequisites remain pending. This is the active P2 checklist, mirrored in [TASKS.md](../TASKS.md#w2--active-d9-pre-freeze-checklist-2026-09-20) and the D9 configuration templates. The current PR synchronizes protocol/documentation only: no runner implementation, weight downloads or model calls are authorized by this task. `protocol_freeze_commit_sha: PENDING`.

## 8. Evidence reviewed on 2026-09-20

Official / first-party sources used for roster capability and access review:

- Qwen3-VL official repository: https://github.com/QwenLM/Qwen3-VL
- Qwen exact Hugging Face model: https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct
- Ovis2.5 exact Hugging Face model: https://huggingface.co/AIDC-AI/Ovis2.5-9B
- Ovis grounding instructions: model README for `AIDC-AI/Ovis2.5-9B`
- Molmo2-O-7B exact model: https://huggingface.co/allenai/Molmo2-O-7B
- Molmo2 official repository: https://github.com/allenai/molmo2
- Gemma 4 official model documentation: https://ai.google.dev/gemma/docs/core/model_card_4
- Gemma 4 exact Hugging Face model: https://huggingface.co/google/gemma-4-12B-it
- PaliGemma 2 backup: https://huggingface.co/google/paligemma2-10b-mix-448
- MiniCPM-V backup: https://huggingface.co/openbmb/MiniCPM-V-4.6

Documentation claims are evidence of documented interfaces/capabilities, not evidence of SafeShift task performance. No InspecSafe performance information was used to select this roster.

## 9. Impact and non-impact

- Dataset: unchanged.
- Split/evaluation pools: unchanged.
- Domain policy: unchanged.
- Hazard taxonomy/support census: unchanged.
- D5 metrics/bootstrap/statistics: unchanged.
- P1 reproduction policy: unchanged.
- P2 execution path: revised from mandatory commercial hosted-provider roster to open-weight self-hosted/user-controlled GPU execution.
- Seminar training policy: unchanged; P1/P2 remain frozen zero-shot.
- Protocol freeze: still pending.

## 10. Approval basis

Project Owner / Research Lead approved the research-value-first model-selection direction and instructed continuation of the current repository on 2026-09-20 after reviewing the proposed primary roster (`Qwen3-VL-8B-Instruct`, `Ovis2.5-9B`, `Molmo2-O-7B`, `Gemma 4 12B IT`) and backup strategy.

This brief records the D9 direction for the dedicated branch. The consolidated
[DEC-W2-D9-009 ledger entry](../DECISIONS.md#dec-w2-d9-009--p2-open-weight-self-hosted-model-roster)
records the same limited supersession boundary. PR #20 remains pre-freeze;
documentation approval does not complete the execution prerequisites or authorize
InspecSafe inference. **NO_INSPECSAFE_INFERENCE**.
