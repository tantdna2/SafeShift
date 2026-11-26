# Issue171 revised engineering evidence

Response to [ChatGPT review6572757952](https://github.com/tantdna2/SafeShift/pull/172#issuecomment-6572757952)
of `542e4dd620a1fb40874b7707dbcd8ef16893d180`. Same branch
`feat/issue171-fresh-fulltrain`, same [Draft PR172](https://github.com/tantdna2/SafeShift/pull/172).
The prior FAIL verdict is not replaced by a self-review or by CPU tests.

Runtime commit: `70825d24ad4e18877321f7134f773e592e051ff8`.
Immutable final code/notebook/test snapshot:
`a3264770138525d2d3e4acd760bd516df9f21d6c`.
Embedded source digest:
`7282c5c6e0f8b771b71ea3d0d4d5bd6f88815bdf6155b17c18767ddeea8079c6`.
Subsequent commit changes documentation/evidence only; compare against this
snapshot to verify that no tested code/config/notebook bytes changed.

## Actual final results

Final results and snapshot/log hashes are recorded in [index.json](index.json),
with full receipts for [Linux](linux-review-final-01.json) and
[Windows](windows-review-final-01.json). Both invocations export the exact same
tracked commit with `git archive`; no local legacy files or private inputs are
included. The harness supplies read-only Git context for historical-object tests
and creates only the empty ignored `data/processed/` parent needed by an older
Phi test. The runner hides CUDA, disables native opt-ins and sets HF offline.

| Invocation | Host Python | Result | Elapsed receipt seconds |
| --- | --- | --- | --- |
| Linux full `test*.py` | 3.14.4 | 597 run: **556 PASS / 41 SKIP / 0 FAIL / 0 ERROR** | 543.134 |
| Windows focused `test_fresh_fulltrain*.py` | 3.11.9 | 55 run: **50 PASS / 5 SKIP / 0 FAIL / 0 ERROR** | 107.766 |

The Linux full-suite run includes all new Linux process supervision tests.
Optional-native/public-source/network skips remain explicit in the receipts;
stdlib host Python is not the approved native worker environment. Windows skips
five Linux-only process-group/parent-death tests, which are exercised on Linux.
No skipped test is counted as PASS.

The [old evidence](../README.md) and every old receipt/index remain intact.
In particular, `linux-final-01.json` still reports 527 PASS / 41 SKIP / 1 FAIL
at `be2e220`; the old 7-test correction receipt also remains. The new full run
is a separate invocation after the correction and the native preparation work.
Development working-tree results are identified separately in the new index.
One Windows development console invocation had a test-fixture serialization
error (`MagicMock` returned as software evidence); the fixture was corrected,
then the affected checks and final snapshot checks were rerun. It has no saved
receipt and is not represented as a successful invocation.

## Review findings addressed in code

| Review requirement | Implementation and CPU evidence | Limit |
| --- | --- | --- |
| Qwen fresh native contract | Exact revision inventory; offline processor/tokenizer/model setup; original two-device placement, SDPA/FP16/max32; raw/processed reductions persisted before decode; alignment and original HNLO replay | Real processor/weights/native fit NOT_RUN |
| Isolated worker and hard deadline | Peer provisioner reused; Qwen sealed offline CPython/zlib/wheel build; staged child processes, absolute deadline, process-group kill/reap, parent-death guardian and log budgets | Full native software builds/ABI unverified; kernel uninterruptible I/O requires VM stop |
| Prepared admission/preflight | Source/request/history/Input/checkpoint binding, bounded inventory, image hashes/decoding, RAM/cgroup, shared/separate disk and fsync allocation, exact physical/visible GPU and CUDA/driver checks | Hardware checks use synthetic boundaries here; no Kaggle measurements |
| Failure controls | Unknown output blocks before setup; no foreign-series import; missing lock, corrupt source/checkpoint/image, package/CUDA/driver/resource failure, timeout/orphan/parent death, preserved partial bytes | No global lock across independent Kaggle VMs; all prior Outputs still required |
| Full validation after fix | Same immutable code/notebook/test snapshot on Linux and Windows, separate receipts/hashes | CPU evidence only; public authorization fences remain closed |

`tests/test_fresh_fulltrain_revision.py` adds 28 regression tests. It checks
exact AST parity of imported Qwen semantic functions against their recorded
historical Git objects, and controller/recovery parity except for explicit
parser injection. Scripted tensors/processor/model objects execute the new
Qwen capture and custody code; they are synthetic test doubles, not predictions.
The preexisting fresh-suite tests retain 3 x 3,763 initial IDs, same order/hash,
new-series isolation, resume/repair separation and immutable raw/archive checks.
All six regenerated notebooks are byte-reproducible, compile with empty outputs,
run twice as preparation-only CPU notebooks and reject changed payloads.

Original peer code, source/checkpoint locks, prior notebooks, parser and HNLO
remain unchanged. Qwen imports its original P2.1 parsing functions: historical
whole-response JSON fence handling is preserved only for Qwen; the peers retain
strict C1. No metric, label, scientific selection, calibration or GT correction
was added. Qwen HNLO uses the original raw log-odds functions and alignment;
MiniCPM remains label-only.

## Public Qwen evidence and exact missing prerequisites

[Public source check](qwen-public-source-check.json) records an independent
comparison of the exact HF revision metadata to the historical inventory:
16 entries, including metadata-only size/SHA for four weight shards. Twelve
non-weight snapshot files were fetched and checked by SHA256 and Git-blob SHA1;
nine official Transformers4.57.1 source files have exact hashes/URLs.
No weight shard was downloaded or deserialized. Historical provenance is in
`configs/fulltrain/qwen3.json` and `qwen_semantics_provenance.json`.

[Tokenizer CPU receipt](qwen-tokenizer-cpu-01.json) records 28/28 synthetic
T1 cases with the exact public tokenizer and `tokenizers==0.22.2`, ordered
candidate IDs 16/17/18/19. This used host Windows Python3.11.9 and a local
isolated package directory; it does not establish target Python3.12.13/zlib,
Transformers processor parity or GPU validity. Reproduce with the public
tokenizer SHA in the receipt, a `tokenizers.Tokenizer` encode/decode adapter
(always `add_special_tokens=False`) and `qwen_semantics.probe(adapter)`.

Release remains **BLOCKED / NOT VERIFIED**, for these concrete reasons:

- Qwen historical records provide top-level versions, not a complete sealed
  cp312 Linux wheel closure. No such reviewed software Input is supplied here.
  The implemented setup refuses missing/changed closure, sources, wheel hashes
  or installed distribution sets; it has no alternate Python/resolver fallback.
  Actual CPython3.12.13/zlib1.2.11 build and compiled ABI checks remain unrun.
- All three pinned native stacks, processors and actual checkpoint bytes require
  target validation. Metadata SHA alone does not prove mounted weights are right.
- Original 3,763-image projection, master/image mapping and custody/rights seals
  were not accessed. Public routes reject before private I/O; synthetic 3,763
  plans do not establish real Input correctness.
- Kaggle RAM/cgroup/quota/filesystems, exact driver/CUDA/two-T4 headroom and
  model fit have not been measured. No real load/inference/raw/HNLO/export smoke
  occurred because this task explicitly prohibits it.
- O2-O6, G0-G6 and the rights/scientific conditions in the
  [runbook](../../../../FRESH_FULLTRAIN_171.md) remain separate gates. Requests,
  hashes, tests and review mode values do not authenticate authority. Public
  entrypoints still reject all real execution. Activation needs a separate
  reviewed exact-source grant binding, not deleting the fence or setting a flag.

No READY FOR OWNER/KAGGLE claim follows. ChatGPT must review the new GitHub
HEAD, then decide independent Antigravity audit; merge is separately authorized.

## Reproduce

Use a clean checkout of `a3264770138525d2d3e4acd760bd516df9f21d6c` with the
historical Git objects available and an empty `data/processed/` directory.
Use a new output path for each invocation:

```console
python -B -m scripts.check_fresh_fulltrain_cpu --pattern "test*.py" --output data/processed/review171/linux-new
python -B -m scripts.check_fresh_fulltrain_cpu --pattern "test_fresh_fulltrain*.py" --output data/processed/review171/windows-new
```

The recorded harness uses `git archive`, a temporary extracted tree and
`GIT_DIR`/`GIT_WORK_TREE` for read-only historical assertions. Its SHA, the
archive SHA, exact command, interpreter, platform, source inventory and log SHA
are bound in the receipts/index. Raw test stdout stays under ignored
`data/processed/issue171/`; public receipts contain no private data or model raw.
