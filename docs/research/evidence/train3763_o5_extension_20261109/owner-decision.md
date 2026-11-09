# DEC-20261109-OWNER-O5-EXTENSION — APPROVED RESOURCE CEILING (TRAIN3763)

**OWNER_DECISION: APPROVED FOR A BOUNDED RESOURCE LIMIT EXTENSION.**
**IMPLEMENTATION: PENDING — CODE / INDEPENDENT AUDIT / MERGE / POSTMERGE VERIFICATION REQUIRED.**
**LIVE KAGGLE ATTEMPT8 / MULTI-IMAGE EXECUTION: NOT AUTHORIZED BY THIS COMMENT ALONE.**

Owner explicitly approved in the SafeShift project conversation (09/11/2026) increasing the original O5 total physical GPU-seconds ceiling from **80,000 to 430,000**, keeping **7,200 seconds maximum per job**, and asked to proceed with obtaining the remaining original TRAIN results **once the amendment is implemented and safely verified**. This is a new Owner resource decision, not a rewrite or re-signing of the 05/11/2026 original approval [#6658142293](https://github.com/tantdna2/SafeShift/pull/181#issuecomment-6658142293). Technical/budget review supporting the request: [#6732868491](https://github.com/tantdna2/SafeShift/issues/180#issuecomment-6732868491).

### Structured resource authority for new implementation

SAFESHIFT_TRAIN3763_O5_AMENDMENT_V1
```json
{
  "schema": "safeshift-train3763-o5-amendment-v1",
  "decision_id": "DEC-20261109-OWNER-O5-EXTENSION",
  "status": "OWNER_APPROVED_RESOURCE_CEILING_PENDING_SAFE_IMPLEMENTATION",
  "campaign_id": "ivl35-train3763",
  "original_grant_comment_id": 6658142293,
  "original_campaign_sha256": "1f672fb601006c7898be271e59f74fb341d7311fc60794a9ed6a332f430395c6",
  "science_sha256": "ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50",
  "limits_before": {
    "total_gpu_seconds": 80000,
    "job_seconds": 7200,
    "physical_gpus": 2,
    "total_calls": 4500,
    "total_jobs": 100
  },
  "limits_after": {
    "total_gpu_seconds": 430000,
    "job_seconds": 7200,
    "physical_gpus": 2,
    "total_calls": 4500,
    "total_jobs": 100
  },
  "historical_reserved_gpu_seconds_at_decision": 25200,
  "historical_jobs_at_decision": 7,
  "historical_calls_at_decision": 7,
  "train_completed_at_decision": 2,
  "train_pending_at_decision": 3761,
  "execution_scope": "ORIGINAL_TRAIN3763_ONLY_RESUME_NOT_ATTEMPTED",
  "historical_ledger": "IMMUTABLE_CREATE_ONLY_ORIGINAL_GRANT_HASH_PRESERVED",
  "test_split": "FORBIDDEN",
  "scientific_changes": "FORBIDDEN",
  "auto_retry_or_refund": false,
  "separate_reviewed_implementation_and_execution_gate": true
}
```

### Exact Owner constraints and implementation requirements

1. Only `caps.total_gpu_seconds` changes **80,000 → 430,000** as **aggregate reservation ceiling** for the same original 3,763 TRAIN IDs, not a bill, not a guarantee and not a new scientific selection/metric/algorithm/label/HNLO rule. Preserve `job_seconds=7200`, `machine_shape=NvidiaTeslaT4`, `physical_gpus=2`, `total_calls=4500`, `total_jobs=100`, per-job calls/archive/repair caps, all original O2/O3/O4/O6 and other O5 conditions.
2. Previous Attempts1–7, historical ordinal0/1 `SUCCESS`, exact source/science hashes, `COLLECTED`/reported `MEASURED` archive custody, immutable original grant, original 24 create-only journals, ledger/mirror and registration/host guard **MUST NEVER be modified, reset, re-keyed or re-created**. Original campaign SHA256 for historical records remains unchanged. One separately authenticated, append-only **extension authority** and/or independently bound extension chain must enforce the new effective ceiling only for *future* reservations; strict anti-replay, single-writer, fail-closed validation, cumulative old+new accounting and artifact lineage are mandatory. Do not attempt to rewrite `registration.grant` or prior event `campaign_sha256` in place.
3. Codex task: **new Codex session / one branch / one Draft PR** from current reviewed `main=ff8963aa1c4a2cfea2a813ff3d02e2aa4f583c2f`. Read `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/TRAIN3763_CAMPAIGN.md`, the `Ledger`/campaign admission and `scripts.train3763_campaign` only as needed. Implement all required verified Owner authority parsing (GitHub comment exact id/body hash/authentic owner + matching original grant), append-only safe extension, non-destructive compatibility, cumulative limits, forecast/status/CLI/operator gates, notebook/source identity updates if code changes, regression tests and docs/PROJECT_STATE **in the same PR**. Test OS portability and failure injection/restore/reconciliation on synthetic copies, not the private production ledger. Do not include real private ledger/ZIP/output in Git. Do not create a separate planning-only or documentation-only PR.
4. **Mandatory independent Antigravity security + provenance audit**, ChatGPT direct source/diff/CI review, separate exact-HEAD merge authorization and postmerge independent verification. Updating protected execution code will require a *fresh* source-bound `SAFESHIFT_TRAIN3763_AUDIT_V1` and `TECHNICAL_V1` technical qualification for the merge. Audit/merge-only sessions follow repo workflow.
5. After all above and **separate ChatGPT execution release** with verified clean source, original history/ledger extension, genuine 24+ local immutable events, provider state and current weekly Kaggle GPU quota, the **same** `operator-asus-win` Kaggle session (Gemini 3.8 Flash High) may begin serial safe TRAIN continuation from **ordinal2**; never rerun ordinal0/1. Job sizes/timing must be bounded by current `MEASURED` source-bound `safe_calls=205` and `required_job_seconds` and *actual* remaining O5/Kaggle quota. Authenticate and check full provider/ledger gates before *every* job; no parallel jobs, double submit, hidden quota escalation or TEST. Collect/verify archive/native logits/trace and record outcomes before next job; stop on unknown/FAIL, exhausted quota/resources or newly unapproved source change.
6. Report each successful collection and the progress of original TRAIN. Kaggle weekly quota and actual image latency are independent restrictions; user approval of O5 does not buy or create more Kaggle quota. This grant does not authorize a background assistant to continue without a running authorized operator workflow.

**APPROVAL BOUNDARY:** Owner **resource ceiling is approved now**; its technical implementation and live GPU execution are **not yet complete or authorized**, and no operator should start Attempt8 from this comment alone.