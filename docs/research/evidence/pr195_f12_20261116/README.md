# PR195 F1/F2 CPU evidence —16/11/2026

[Review response and reproduction](../../PR195_F12_REVIEW_20261116.md).
Tests ran on code HEAD `1e24192eff5f8ba96f36ab33f733e2d47729a80f`, after normal
merge of requested main `89088dbc57d629933ab1462171019cd0125c2869`.
The delivery commit adds documentation/evidence only. All tested code/file hashes
are retained in the individual receipts and checked unchanged at delivery.

Each row is one fresh complete module invocation, not accumulated PASS coverage
from the earlier269-case record. Windows stdlib/operator runs use CPython3.11.9;
the two Linux rows use the existing WSL interpreter. No dependency installation.

| Suite | PASS | FAIL | ERROR | SKIP |
| --- | ---: | ---: | ---: | ---: |
| test_fresh_fulltrain_notebooks | 5 | 0 | 0 | 0 |
| test_fulltrain_notebooks | 3 | 0 | 0 | 0 |
| test_fulltrain_minicpm4_notebook | 9 | 0 | 0 | 0 |
| test_fulltrain | 24 | 0 | 0 | 0 |
| test_fresh_fulltrain | 23 | 0 | 0 | 0 |
| test_fresh_fulltrain_revision | 23 | 0 | 0 | 5 |
| test_fulltrain_original_inputs | 8 | 0 | 0 | 0 |
| test_minicpm_fulltrain_ui | 11 | 0 | 0 | 0 |
| test_minicpm_ui_transport | 3 | 0 | 0 | 0 |
| test_train3763_manual | 107 | 0 | 0 | 0 |
| test_internvl3763_python | 21 | 0 | 0 | 1 |
| test_qwen_composite | 23 | 0 | 0 | 0 |
| test_train3763_continuation | 40 | 0 | 0 | 0 |
| test_train3763_results | 11 | 0 | 0 | 0 |
| Linux: SupervisionTests | 5 | 0 | 0 | 0 |
| Linux: Python Input symlink case | 1 | 0 | 0 | 0 |

The five Windows process/deadline skips and one symlink skip are covered by the
matching Linux rows. Final suites have no unresolved FAIL/ERROR. The original
15/11 operator-initial FAIL and subsequent PASS records remain unchanged at
`../minicpm_owner_ui_20261115/`; they are historical and not relabeled.

The pre-fix integrated notebook module reproduced six runtime source mismatch
subtest errors plus two old-backend/loading comparison failures. Final tests
reconstruct the original builder/source set from each notebook's committed Git
runtime, verify complete notebook equality and every embedded byte, and retain
the current strict builder gate. No expected notebook hash, runtime source lock,
protocol decision or notebook was rewritten to pass. Negative tests reject
added/missing/modified/duplicate source keys and wrong runtime references.

[suites.json](suites.json) records each independent run, elapsed time and original/
exported log SHA. Logs normalize Windows CRLF to LF and replace an absolute
repository prefix if present; original logs are retained under ignored
`data/processed/pr195-f12/`. Receipts retain original log hashes, interpreter,
dependencies, tested commit, source/test hashes, no network attempts, no private
image reads and no production writes. No result data, real raw outputs, weights
or credentials are included.

[notebooks.json](notebooks.json) lists every notebook SHA and runtime/source
binding unchanged from the reviewed HEAD8b9570f. [preservation.json](preservation.json)
contains the two merge parents and byte proofs for old evidence/runtime/locks,
capsule/collector code and PR196/197 main files. [scope.json](scope.json) lists
every changed file relative to the review HEAD and requested main, including
the five F2 code/test files. No claim of a GitHub Actions or full-discovery PASS.

Runtime SHA256: `1ae53f138508c35e2863367f052d3268c862b944294be810e23600d675948335`.
MiniCPM notebook SHA256: `de604979761211127728229240af7c91fe104f263c71e9f6dc66f8911ba96922`.
All capsule/Input/rights/source-release/caps gates remain closed; live GPU/model
verification NOT_RUN. CPU author validation is not independent Antigravity audit,
scientific qualification, merge authorization or source activation.
