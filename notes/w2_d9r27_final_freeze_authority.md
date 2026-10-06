# D9R27 final protocol freeze and merge-gated authority

This task freezes the reviewed P2 execution contract in F1 and records the
execution authority in F2. The implementation base is the exact audited
`e7628d68f87cf53b5343ea912b7e332064c285af`. The reviewed D9R26 candidate is
preserved byte-for-byte and pinned by SHA-256
`0901bab9b0dbd648b263071d5fdbd677120880eb91a2a5d4724c064905ab2ec2`.

F1 is the immutable final freeze commit. F2 is its direct child and contains
only `configs/frozen/p2_execution_authority.v1.json`. The authority file is a
declaration on a Draft PR branch; it is effective only after Research Lead /
ChatGPT GitHub review, independent audit, a Standard Merge Commit whose first
parent is the exact implementation base and whose second parent is F2, and
final Research Lead / ChatGPT verification of that merge commit.

`authorize_production()` proves this Git structure and a clean tracked
checkout. A one-parent F2 Draft PR therefore fails closed with
`FINAL_MERGE_REQUIRED`. Static preflight never reads the dataset or imports a
model/GPU library. P1 remains separate and unimplemented; primary grounding
remains `DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE`; PaliGemma remains
`NOT_PARTICIPATING`.

No model, GPU, network, dataset, InspecSafe run, Antigravity call, or merge is
performed by D9R27. After the eventual reviewed merge, the owner must run the
static preflight again and obtain the Research Lead / ChatGPT verification
before execution.

## D9R27 authority-gate correction

The final gate also requires the exact authority schema version and proves that
parent two is F2, the direct child of F1: `git rev-list --parents -n 1 parent2`
must be exactly `[parent2, protocol_freeze_commit_sha]`. Intermediate commits
and merge commits used as parent two fail closed. The committed D9R27 tests
construct and verify real temporary Git merge histories for valid and mutated
cases.

The focused suite exercises the real authorizer against temporary local Git
repositories, including separate semantic failures for parent-one drift,
non-direct/intermediate/multi-parent F2, parent-two authority mismatch, tree
mismatch, executable edits after F1 and dirty tracked files. Authority fields
are mutated individually, including absent/wrong schema, all identity pins,
dataset count/fingerprint, reruns and activation declarations. Missing and
untracked authority are tested on two-parent histories, so an earlier
one-parent rejection cannot mask those boundaries.

Fresh Python subprocesses block model/GPU imports and network connections,
dataset verification, backend resolution/load and runtime observation during
both blocked Draft preflight and authorized synthetic-merge preflight. Owner
CLI exit codes are 2 and 0 respectively; neither path creates P2 artifacts.
Preservation assertions cover Git blobs, the exact four-model registry and
ASTs of raw storage/parse, no-GT execution, retry and sharding consumers.

Historical D9R26 builder tests now read the reviewed source at the exact
implementation base. They still reject source drift and verify every candidate
hash; the candidate and builder themselves are unchanged. D9R25 tests exercise
the final merge contract, and D9R22/23 allowlists add only the three D9R27
artifacts. D9R22-D9R27 regression: 128 tests passed before the final rebuild.
Full-suite BASE/HEAD comparison uses the same Python environment and LF Git
checkouts. Final commit identities and full-suite results belong in PR #84's
handoff, since adding them to F1 after hashing it would invalidate F2.

Git structure verification is offline. Research Lead review, independent audit
and post-merge GitHub verification remain external governance requirements;
synthetic commits in tests do not attest that those reviews occurred. Network
use for this task is limited to the requested Git/GitHub PR maintenance, with
no inference, dataset download or network access from preflight tests.
