# W2.6-D9R2J-MOONDREAM-FUNCTION-IDENTITY-DIAGNOSTIC-PREP

Status: **PREPARED_NOT_RUN**. New branch/task based on
`b8a53ca25dad354c378591bf124e73d557a38caf`; independent Draft PR, no merge.
This preparation does not relax a guard or change the runner, source loader,
snapshot policy, precision bridge, software pins or runtime conditions.

## Evidence and unresolved question

Research Lead supplied the following evidence in this task; the original bundle
was not independently opened or rehashed here:

- Run `moondream-load-diagnostic-20260926T124352Z-d0f85ea7`, executed exactly once
  at `b8a53ca25dad354c378591bf124e73d557a38caf`.
- FAIL / load / ValueError / `AUDITED_FUNCTION_IDENTITY_REQUIRED`.
- Trace: `Moondream2Runner.load` -> `NativeBackend.load` -> `starmie_redirect`
  -> `verify_function(module.MoondreamModel.__init__, ...)`.
- Python 3.11.11 and exact software pins correct; exactly one process-visible
  Tesla T4, CC 7.5. Model/tokenizer snapshot verification PASS;
  provision manifest equals verify manifest.
- Query = 0, detect = 0, `state_audits = []`, `image_boundaries = []`.
  Precision bridge not reached; model inference did not occur.

The failing guard is localized, but its failing subcondition is **UNKNOWN**.
No decorator, wrapper, closure or globals explanation is asserted as fact.
No old diagnostic rerun, runtime repair or qualification follows from this PREP.

Sources: supplied run evidence above and the existing local
[`verify_function`](../safeshift/runners/moondream_binding.py),
[`NativeBackend.load`](../safeshift/runners/moondream2.py),
[`snapshot verifier`](../safeshift/runners/moondream_snapshot.py), and
[`pinned source audit`](../configs/pre_freeze/moondream_prep_audit.v1.json).

## Diagnostic contract

Separate entrypoint:
[`scripts/w2_moondream_function_identity_diagnostic.py`](../scripts/w2_moondream_function_identity_diagnostic.py).
Use a fresh dedicated process with venue networking disabled. Its only model-side
operation is the existing `load_verified_modules(model_snapshot)` import.

1. Reserve an exclusive report in
   `data/processed/moondream_function_identity_diagnostic/<run_id>/report.json`.
   Reject unsafe IDs, path escapes/aliases and reused output directories.
2. Require a full expected Git SHA equal to HEAD and a clean checkout, including
   nonignored untracked files. All Git subprocesses finish before network denial.
   Existing ignored caches/reports are allowed; unrelated untracked files are not.
3. Verify the complete local pinned model snapshot with the unchanged audit/hash
   verifier. Weights are read only for existing byte verification, never loaded
   as tensors. No cache search, download or reprovision fallback exists.
4. Record Python, primary dependency versions and platform as metadata only.
   Use the unchanged `requirements-moondream-t4.txt` environment for future
   execution; this script does not initialize the runner to check software/GPU.
5. Install existing `deny_network_permanently()`. Import through
   `load_verified_modules(snapshot)`, which also verifies the snapshot and source
   bytes and rejects reuse of its module namespace in a nonfresh process.
6. Take `module = modules["moondream"]` and
   `function = module.MoondreamModel.__init__`; record allowlisted metadata.
7. Independently compile `verified_source(snapshot, "moondream.py")` with filename
   `moondream.py`, mode `exec`, `dont_inherit=True`, exactly as `verify_function`.
   Find the first depth-first code object with `co_qualname ==
   "MoondreamModel.__init__"`; compare using the existing `code_signature` helper.
   Compilation does not execute the resulting code. No guard is invoked or altered.

`IDENTITY_OBSERVED` / exit 0 means observation completed, even if predicates or
the signature comparison are false. It is not a runtime PASS. Failures produce
`FAIL` / exit 1 with stage and exception type only. If compilation fails after
identity observation, the identity metadata remains in the report.

The report records commit, timestamp, command, artifact path, model revision,
source-audit digest, verified manifest and software metadata. Seed is null because
no sampling occurs. It reports no GPU measurements, model output or metrics.

## Observed fields and interpretation

| Guard subcondition | Independent report field |
| --- | --- |
| `type(function) is types.FunctionType` | `is_exact_types_FunctionType` |
| `function.__globals__ is vars(module)` | `globals_is_module_vars` |
| `function.__qualname__ == "MoondreamModel.__init__"` | `qualname_matches` |
| `function.__closure__ is None` | `closure_is_none` |

Additional fields: `function_type_name`, `function_type_module`,
`actual_qualname`, `expected_qualname`, `closure_length`, `co_freevars`,
`function_module_name`, `function_code_name`, `function_code_qualname`,
`function_code_filename`, `class_dict_has_own_init`,
`class_dict_init_is_function`, `expected_code_exists`, `code_signature_matches`.

`class_dict_init_is_function` means the class's own dictionary entry **is the
same object** as the retrieved function; it is not another function-type test.
Closure length is zero for None, otherwise tuple length. Free-variable names
are reported without reading cell contents. For a nonfunction, unsupported or
missing metadata is null, never silently false; arbitrary properties are not
invoked. Expected-code existence and signature match are null if their stage was
not completed. Signature match is also null when either code object is unavailable.

Code filenames are repository-relative where possible; external absolute paths
are reduced to `<external>/<basename>` and marked by the filename policy field.
The existing sanitizer is reused unchanged for strings. No globals contents,
closure values, repr of callable objects, exception text/locals/tracebacks,
weights or credentials are serialized. Redacted metadata must be read as such;
predicate booleans are computed before redaction.

## Future execution, after PREP audit and merge only

Use the existing provisioned cache if it remains. If absent, stop: PREP does not
download. Later execution follows PR #45's authorized exact reprovision and
verify-only policy, including its manifest comparison, before running this new
identity-only command. That policy does not authorize rerunning the old diagnostic.

From repository root in the pinned environment, with venue networking disabled,
substitute the reviewed merged execution SHA and a fresh run ID:

```bash
python scripts/w2_moondream_function_identity_diagnostic.py \
  --execute-identity-diagnostic \
  --expected-commit <REVIEWED_MERGED_EXECUTION_SHA> \
  --cache-dir data/processed/moondream_cache \
  --run-id <NEW_IDENTITY_ONLY_RUN_ID>
```

This command has **not** been run. No GPU inventory or CUDA API call is required.
No MoondreamModel construction, Tokenizer.from_pretrained,
HfMoondream.from_pretrained, model.to(), runner initialize/load, query/detect,
precision bridge, official smoke, synthetic gate or InspecSafe is permitted.

## Redaction finding (characterization only)

The old load diagnostic regex contains `\bhf_[A-Za-z0-9]+\b`. It matches
`hf_moondream` before the dot in `hf_moondream.py`, yielding `[REDACTED].py`.
The same false positive occurs in a path such as `cache/hf_moondream.py` and for
`hf_utils.py`. It does not match every `hf_` filename: the additional underscore
in `hf_model_utils.py` prevents the trailing word boundary.

Fake tests reproduce these results and retain token redaction coverage. The old
redactor and artifacts remain unchanged. Propose a **separate follow-up** to
design filename-aware observability while retaining credential suppression;
this PREP neither restores old reports nor weakens credential matching.

## Validation

Windows, Python 3.11.9, fake/static fixtures only:

```text
python -m unittest tests.test_moondream_function_identity_diagnostic tests.test_moondream_load_diagnostic tests.test_moondream_runner_smoke
Ran 72 tests; OK
```

Coverage includes each identity predicate independently, original guard rejection,
closure/freevar names without values, missing attributes, descriptors, inherited
constructors, expected-code absence/mismatch, compile without execution,
provenance/dirty checkout, missing or invalid snapshots, import/compile failure,
path safety, redaction, no construction/runtime entry and no reads/writes of old
smoke/diagnostic artifact namespaces. Synthetic constructors raise if called.

Real diagnostic, snapshot import/verification against real cache, GPU/model
execution and all qualification checks are intentionally NOT_RUN. The fake test
environment is not claimed to reproduce the pinned runtime identity failure.
