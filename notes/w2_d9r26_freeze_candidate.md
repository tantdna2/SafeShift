# D9R26 implementation freeze candidate

Stacked on PR #82, exact D HEAD `a3a5fdcc0a17b920f2c15942247b6fd61d25aa2d`.
This is implementation for independent review, not runtime qualification or
execution authority. A-E remain unmerged. No model, GPU, snapshot download or
InspecSafe execution occurs here; historical runtime observations were not rerun.

The four internal bindings in `safeshift/runners/p2_bridge.py` are Qwen3VLRunner,
Qwen2_5VLRunner, InternVL3Runner and Moondream2Runner in their existing modules.
The bridge reuses initialize -> load -> prepare_input -> generate_raw, without
model inference duplication, parsing or raw writes. D9R25 owns persistence and
strict adaptation only after atomic publication, hash/size reread verification.
Public production_run still has no implementation/factory injection. Native
module/class/version/model/revision are checked before loading. Qwen native
envelopes carry measured complete software versions; native observations must
match policy, including loaded placement/precision checks. No GPU status is
claimed from static preflight.

Two narrow native guard extensions are necessary: InternVL3 may accept an
authorized INSPECSAFE classification context (its historical source allowlist
otherwise remains intact); Moondream's authorized classification context uses
query-only decoding. Neither relabels production as synthetic. Both reject
grounding in production. Historical generation/query logic is unchanged.

Model payload is exactly image bytes + fixed C1 prompt. RunContext carries
run/call/sample/image identity, authorized Git SHA, model/source and exact policy
condition separately. Roles are classification PARTICIPATING and grounding
NOT_PARTICIPATING; seed remains null. Each call gets `call1-<SHA256(sample_id)>`
under `call1-sample-sha256-v1`, needed for InternVL3 envelope identity and unique
attempts. Version d9r26-run-v1 records this; export still reads historical
d9r25-run-v1 call1 artifacts. Ranking, metrics, taxonomy and retry policy do not change.

The four `w2_d9r26_*_p2_runbook.md` files and thin `p2_owner` CLI replace duplicate
notebooks. They pin policy conditions and reuse provisioning scripts/native
loaders; no notebook copies inference code. Managed Python is explicit; venv pip
is not assumed. Qwen3 retains two visible T4s/Python 3.12.13/CUDA12.8; the other
three use Python3.11.11/CUDA12.4 with one visible T4 before the child starts.
Provisioning recipes are prospective owner instructions, not rerun evidence.

Offline validation commands (synthetic temporary files only):

```text
python -m unittest tests.test_d9r26_bridges tests.test_d9r26_candidate -v
python -m safeshift.runners.p2_owner preflight
```

Preflight verifies candidate/policy bytes without dataset or GPU access and
returns PROTOCOL_FREEZE_REQUIRED (exit 2). Production authorization remains the
first execution gate, before dataset reads. Dataset mismatch precedes bridge
construction/load. Fake-native integration tests patch private construction and
observation only; no such selector exists at the production boundary. Rehearsal
uses both ScriptedBackend and fake native lifecycle, then durable raw -> parser
-> export -> four-model alignment -> explicit GT join -> RQ1/RQ2/RQ3 -> stable
JSON. Cases include unanimity correct/wrong, 3-1, 2-2, all different, invalid,
Level01 downgrade, anomaly-to-normal, overlapping hazards and multiple domains.
No performance or accuracy claim about actual models follows from these tests.

Historical source-byte regression tests read the exact pre-D9R26 Git source for
the historical gate identity. Disposable fake gate fixtures retain the original
Moondream source hash; no historical plan/result/authority hash is repinned.
Current production guard tests run against the new source, and AST comparisons
protect the unchanged native initialize/load/generate methods. The historical
gate intentionally rejects the new live source; this does not authorize running
that old gate on the D9R26 implementation.

`configs/pre_freeze/protocol_freeze_candidate.d9r26.v1.json` pins UTF-8 Git
repository bytes with SHA256. Working-checkout CRLF is normalized to LF only;
no JSON reserialization, whitespace stripping or content canonicalization.
Tests verify current bytes and historical Git blobs. The candidate never hashes
itself (no circular digest); its reviewed Git commit binds it. Regeneration is
explicit via `python -m safeshift.protocol.freeze_candidate` to stdout followed
by a reviewed file update. Changes to pinned sources invalidate the candidate.
No local dataset, snapshot weight, secret or raw output is hashed by this list.
Snapshot identity is the D9R23 immutable revision; existing native verifiers
still enforce their historical local snapshot contracts when later authorized.
PaliGemma's shared receipt/types dependency is hash-pinned but it remains
CLASSIFICATION_NOT_PARTICIPATING. No grounding execution dependency is added.

READY_FOR_INDEPENDENT_AUDIT_BEFORE_FREEZE=true is conditional on recorded tests.
READY_TO_RUN_INSPECSAFE=false. Still pending: ChatGPT GitHub verification,
independent audit, merge A->E, a final post-merge freeze/authorization PR,
final protocol SHA, Research Lead authorization and actual execution.
The final SHA cannot be known until audit and merge. Candidate status is
FREEZE_CANDIDATE_NOT_FROZEN; protocol_freeze_commit_sha=PENDING,
protocol_freeze=PENDING, implementation_freeze=PENDING,
inspecsafe_inference_authorized=false. P1 remains separate; grounding remains
DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE. This task performs no audit or merge.
