# D9R9 Kaggle orchestration notebook — pre-runtime tooling

Task: `W2.6-D9R9-PALIGEMMA-SINGLE-T4-RUNTIME-QUALIFICATION`.
Execution base: `180c0623149bbc7d64f5b659f6c044c39b1e1cd0`.
Owner's revised instruction: deliver a self-contained notebook for Research Lead
review and subsequent owner execution, without per-cell feedback to Codex.

[Notebook](../notebooks/w2_paligemma_d9r9_kaggle.ipynb) orchestrates the exact D9R8
checkout, plan, provisioning CLI and smoke harness. The notebook delivery commit
is separate from the pinned runtime execution commit. No runtime result JSON is
created in the repository. Real runtime remains `NOT_RUN` / `PENDING_QUALIFICATION`;
exact runtime verified remains false. No weights, GPU or model were used in this
authoring task. The owner's historical untracked manifest remains untouched in
the main checkout; work uses a separate clone under ignored `data/processed/`.

The online cell checks Kaggle Linux x86_64 and physical T4 hardware, masks all
children to GPU 0, clones a fresh dedicated checkout, installs `uv==0.8.22` in a
bootstrap venv, obtains managed CPython 3.11.11, and creates an isolated runtime
venv. It installs the unchanged `requirements-paligemma-t4.txt`, records installed
distributions and pip freeze, requires pip check and exact plan versions, and
probes one process-visible T4 using the isolated Python. The kernel environment
is not upgraded. Repository/software setup precedes the separate provision phase.

HF_TOKEN is required from Kaggle Secrets. Private-repository authentication uses
optional SAFESHIFT_GITHUB_TOKEN in a subprocess-only Git header; clone failure
stops with the secret setup instruction and no authentication retry. Neither
credential is placed in command arguments, URLs, Git config files or artifacts.
Logs are sanitized before writing. Runtime environment uses an allowlist without
inherited credentials or Python configuration. Bootstrap and runtime directories
are fresh and never repaired or overwritten.

Provision and independent verification use D9R8's complete 14-file byte verifier.
Only after these pass does the notebook reach its single manual barrier: the
owner disables venue Internet and sets OWNER_ATTEST_INTERNET_OFF=True. It cannot
disable venue Internet itself. No session restart or provisioning rerun is needed.
Offline variables and socket denial precede backend imports. Runtime re-verifies
the snapshot and requires the unchanged checkout to remain clean, including
untracked files. An exclusive attempt marker prevents runtime retries.

D9R8 does not expose load/generation durations. The notebook's external stdlib
profile observer runs the unchanged smoke CLI with runpy, without replacing
model or runner functions. Timing scopes are explicit: the complete runner load
includes snapshot hashing/device transfer, while native GenerationMixin.generate
is synchronized at entry/exit. These instrumented wall times are not benchmarks.
Missing spans or observer errors stop completion; they cannot fabricate a timing.
Observer source and timing records are bundled for review. Native inference,
raw persistence, fsync/re-read/checksum and adapters remain entirely in D9R8.

The exporter checks summary/artifact checksums before reading raw envelopes. It
copies allowlisted evidence without rewriting raw bytes; logs were already
sanitized at capture. Files are capped at 4 MiB and selected evidence at 32 MiB.
No snapshot blobs, checkpoints, environment directories or arbitrary checkout
files enter the bundle. Failure bundles contain available evidence and a STOP
record; no success marker is printed on failure. Kernel termination may prevent
export and must be reviewed before any rerun. The success marker means evidence
export completed, not qualification or promotion.

Native IDs and both decoded texts are OBSERVED_ONLY. Loc-token text presence is
only a textual observation. The color question does not test detection separators
or no-detection behavior. No production classification grammar is frozen by this
notebook; the Research Lead reviews any documentary discrepancy. Classification
adapter remains INVALID, grounding adapter expected UNSUPPORTED and unexecuted,
external gate pending, synthetic gate and InspecSafe NOT_RUN, BACKUP_1, four
primaries, promotion NO and protocol freeze BLOCKED.

Validation (static/fake only): 94 tests PASS across notebook orchestration (15),
D9R8 PaliGemma preparation (44), and D9 roster/governance regression (35).
Notebook JSON and every code cell/embedded child script compile. Fake checks
cover the online sequence, installation failure stopping before provision,
attestation barrier, retry prohibition, credential redaction/environment filtering,
untracked checkout rejection, bounded allowlisted export, byte preservation,
checksum/native failures, and timing observation. No protected source allowlist
change is needed. No Kaggle package installation, real GPU probe, snapshot download
or real model execution was performed during validation.

```text
python -m unittest tests.test_paligemma_d9r9_notebook tests.test_paligemma_prep tests.test_d9_t4_roster_revision -q
git diff --check
```

Actual Kaggle wheel availability, HF access and runtime behavior await owner
execution after Research Lead review; a successful fake test is not their evidence.
