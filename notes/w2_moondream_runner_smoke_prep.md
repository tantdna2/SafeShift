# W2.6-D9R2G — pinned Moondream2 runner and smoke PREP

Status: **PREPARED_NOT_RUNTIME_VALIDATED**. Smoke harness:
**PREPARED_NOT_RUN**. This change implements offline enforcement and prepares a
future feasibility attempt; no GPU, model weights download, remote model code
execution, inference, real smoke, eight-case gate or InspecSafe use occurred.
Protocol freeze remains **PENDING**. Nothing promotes the roster or grounding.

Base main: `cf16e056d7e5a1580f78a9431ed86bad60771c6a`.
Branch: `implementation/d9-moondream2-runner-smoke-prep` (new, not PR #42's branch).
The commit containing this note identifies the implementation and test version.

## Immutable identities and verification

- Model: `vikhyatk/moondream2` at
  `9a7d4024050840e001defacec2b00727e89149e6`.
- Nested tokenizer: `moondream/starmie-v1` at
  `35192e10a54e36eabe0a7cc57a2c1aab371cafc5`.
- [Unchanged source audit](../configs/pre_freeze/moondream_prep_audit.v1.json).
  All 18 local source/config/card/tokenizer captures were rehashed against it,
  without importing or executing them. All matched. Local captures remain ignored.
- [Runtime plan](../configs/pre_freeze/moondream_t4_runtime.v1.json), canonical JSON
  SHA-256 `387fcf1bd9abb7cb0d265ebbebabfb25f24e2518eece825b67e425e6f6d2c1a8`.
  Code checks this digest, plus canonical digests of the historical audit and
  bridge plan. No protected file is edited.

[Snapshot verification](../safeshift/runners/moondream_snapshot.py) accepts only
`models--<owner>--<repo>/snapshots/<exact revision>`, with no directory aliases.
HF file links within that repository's cache are allowed; external links fail.
Every audited file is required, including all four Starmie artifacts. Additional
files are rejected. Use a fresh dedicated cache rather than a legacy full snapshot
containing unaudited sources. Size and SHA-256 are checked for every file.

The model weight hash is **not invented**: the unchanged audit records the pinned
API LFS metadata SHA-256
`70a7d94c0c8349eb58ed2d9e636ef2d0916960f321ecabeac6354b8ba3d7403f`,
size 3,854,538,968 bytes. Those bytes were NOT downloaded/verified in PREP.
Future provisioning must hash the actual weights and produce a manifest;
runtime repeats verification. The source/config hashes were verified against
captured bytes and pinned Git blob identities in the earlier audit. Each future
manifest records both original evidence category and `local_bytes_verified`,
per-file hashes, immutable identity, relative snapshot suffix and its own digest.
No personal absolute path is written to a manifest.

## Runner and dedicated process

[Moondream2Runner](../safeshift/runners/moondream2.py) implements the unchanged
`LocalRunner` methods. Native dependencies are lazy; test backends are injected.
One process-wide, nonblocking ownership lock covers initialization, load and each
call. Only the main thread in a dedicated single-owner process may enter. Reentrant
or concurrent requests fail, as does a forked/reused runner. A process can claim
only one model-load attempt; a failed attempt invalidates the runner.
Repeated successful `initialize/load` through the contract are idempotent, without
a second native model load. There is no replacement model or retry route.

The future loader verifies the complete snapshot before importing model code.
A package-scoped source loader accepts only the audited Python closure, reads and
rehashes source immediately before execution, and never consumes `.pyc` files.
It imports the pinned `HfMoondream` class directly; no mutable AutoModel lookup or
alternate architecture is selected. Modules must not already exist in the process.
No modified or vendored upstream source is produced. PREP never calls this loader.

The runtime permanently sets HF offline/telemetry flags and installs a Python audit
hook before native imports/load. Socket network operations and child-process launch
are denied. This is not an OS firewall: the future venue **must also disable
networking**, including native-library egress. The harness requires an explicit
venue-network-disabled attestation. Provision in a separate process before this
boundary. There is no mechanism to reenable network from the runner.

## Exact Starmie redirect

Pinned `moondream.py::MoondreamModel.__init__` invokes
`Tokenizer.from_pretrained("moondream/starmie-v1")`, with no revision parameter.
The [binding implementation](../safeshift/runners/moondream_binding.py) verifies
the constructor's function identity, module globals and compiled bytecode against
the hash-verified source before intercepting this call.

Only that remote module's `Tokenizer` reference is temporarily replaced during
construction. The factory accepts exactly one call, the exact positional repo ID,
no kwargs, the exact constructor code object and its exact globals. All unexpected
requests fail. It rechecks the pinned Starmie snapshot and calls the genuine
`tokenizers.Tokenizer.from_file` on the verified `tokenizer.json`. The actual
constructed model must hold that exact returned tokenizer object. The original
reference is restored in `finally` and restoration is checked; a load failure is
terminal. Neither the tokenizers class nor any shared tokenizer library is patched.

The source evidence for `tokenizers==0.21.2` is already in the audit: both APIs
ultimately use the native file deserializer. Other Starmie artifacts are also
verified, although this native API reads only `tokenizer.json`. This enforcement is
**PREPARED_NOT_RUNTIME_VALIDATED**, not a successful model construction claim.

## Precision bridge and Pillow-only condition

Research Lead decision: **PRE_FREEZE_RUNTIME_CONDITION**, made before inference,
gate or InspecSafe. Qualification requires **PILLOW_ONLY**. Upstream's actual
`image_crops.HAS_VIPS` must be exactly false; its `Image` must be the imported PIL
module, with no pyvips binding. The `overlap_crop_image` reference must also match.
These checks occur at load and before each crop operation. Selecting pyvips or any
other backend fails; the runner never changes the upstream backend flag. There is
no claim that Pillow and pyvips are numerically equivalent.

Bridge: unchanged `moondream-post-normalization-fp16-v1`,
[helper](../safeshift/runners/moondream_precision.py),
[approved plan](../configs/pre_freeze/moondream_precision_bridge.v1.json).
Integration follows **INSTANCE_BOUND_ORIGINAL_BYTECODE_WITH_PRIVATE_GLOBALS_OVERLAY**:

1. Check exact instance class, original `_run_vision_encoder`, `prepare_crops`,
   `_vis_enc`, `vision_encoder`, globals references and unchanged code identities.
   Source verification compiles bytes for comparison without executing them.
2. `types.FunctionType` retains the original `_run_vision_encoder.__code__`, defaults
   and closure. Its private globals copy changes **only `prepare_crops`**.
   `types.MethodType` binds this function to the single audited instance.
3. The wrapper accepts only the audited vision-config identity and cuda:0 target.
   It calls the original `prepare_crops(..., device="cpu")`. Original crop,
   resize, RGB conversion, BF16 allocation and full BF16 normalization finish first.
4. Pass the **entire return tuple** to the merged bridge. Validate CPU/FP16, then
   transfer only its returned tensor to cuda:0 and validate again. The original
   BF16 crop is never transferred.
5. Original bytecode continues through `mark_dynamic` to `_vis_enc`. A temporary
   instance consumer guard verifies the exact transferred tensor and FP16/cuda:0
   immediately before calling the unchanged original `_vis_enc`. Nothing patches
   module/class/torch globals for the precision integration.
6. `finally` restores both prior instance attributes, including absence of a prior
   shadow; restoration and identities are rechecked. Invariant/restoration failures
   invalidate the binding. The runner also becomes unusable on generation failure.

Effective graph: `query/detect -> encode_image -> _run_vision_encoder -> original
prepare_crops(CPU BF16) -> bridge(CPU FP16) -> CUDA FP16 -> mark_dynamic -> guarded
_vis_enc -> original vision_encoder -> patch_emb`. External EncodedImage inputs,
history, variants, compilation and alternate preprocessing are not exposed.

## Device, model state and dependencies

Require exactly one NVIDIA/Tesla T4, compute capability 7.5, reported physical VRAM
between 14 and 16 GiB inclusive (covers driver-reported usable memory for the nominal
16 GB T4). CPU-only, zero/multiple GPUs, other names/capabilities/memory fail.
FP16/NONE/batch 1/cuda:0 only; device_map auto, quantization, CPU/disk offload,
autocast and automatic precision/quantization fallback have no accepted path.

The HF load is staged on CPU, converted explicitly to FP16 **before** CUDA transfer,
then placed entirely on cuda:0. CPU staging is not inference offload. Caches are
created after placement from the model's FP16 vision dtype. Audits inspect all
named parameters and buffers, including nonpersistent RoPE/mask, known registered
k/v caches, and tensor-valued extra attributes. Unexpected FP32/BF16 floating
state or any model state on CPU fails; no floating exceptions are invented.
Integer/bool state stays integer/bool and on the target. Audits run after load and
before/after each native call. Independent calls zero k/v caches and encode their
own fresh image; no earlier EncodedImage is accepted. This is not a claim that
every temporary arithmetic intermediate in upstream spatial decoding is FP16.

[Requirements](../requirements-moondream-t4.txt) pin the full 38-package dependency
closure for Linux x86_64 / Python 3.11.11. No package was installed to test a model.
[Versioned metadata evidence](../configs/pre_freeze/moondream_software_evidence.v1.json)
records exact PyPI URLs, response digests, Python requirements and active dependency
constraints; all 38 selected versions satisfy the static dependency constraints.
The future runtime checks every installed version. Use an isolated environment;
do not add pyvips, torchvision, quantization or acceleration alternatives.

- Transformers 4.52.4 comes directly from the pinned model `config.json`.
  Its [versioned setup source](https://raw.githubusercontent.com/huggingface/transformers/v4.52.4/setup.py)
  supports the selected torch, tokenizers, Hub, safetensors and Pillow versions.
- Torch 2.6.0+cu124 / Python 3.11.11 and Pillow 11.2.1 / Hub 0.30.2 /
  safetensors 0.5.3 reuse existing Qwen runtime-plan software evidence. The earlier
  bridge was tested on torch 2.6.0+cpu. GPU equivalence is not asserted.
- Tokenizers 0.21.2 matches the already audited native-deserializer source and
  Transformers' declared compatibility. NumPy 1.26.4 supports Python 3.11 and the
  ordinary array/transpose/asarray operations used by pinned image preprocessing.
  Remaining exact pins were selected from package metadata constraints, without
  model output, performance or trial-and-error inference.

Static source/package compatibility is documented; the full FP16 T4 execution is
**NOT_VALIDATED**. This distinction is precisely what the future smoke tests.

## Native output and adapter boundary

Native query returns its whole dictionary; native detect returns its whole objects
dictionary. The runner does not extract, clamp, rescale or repair coordinates.
Point remains the documented upstream `{"points": [{"x": ..., "y": ...}]}` API;
no SafeShift point-to-box execution path is introduced. Grounding uses detect.
Coordinates remain **NORMALIZED_XYXY_NOT_CLAMPED**, origin
**NOT_EXPLICITLY_DECLARED_IN_PINNED_SOURCE**.

Native structure -> deterministic tagged JSON bytes -> FileRawStore/checksum ->
adapter or smoke interface check. The serialization format
`moondream-native-lossless-v1` preserves dictionary entries/order, lists, scalar
types and every IEEE float64 bit (including negative zero and nonfinite values),
without semantic parsing or dropping native fields. Its decoder is used only after
raw persistence. Unexpected non-native types fail rather than stringify silently.
If a complete native return exists before a later invariant fails, its raw bytes
travel in `GenerationFailure.partial_raw`. An upstream blocking call that raises
before returning exposes no partial native structure; none is fabricated.

The placeholder adapter keeps grounding UNSUPPORTED/PENDING with raw native evidence;
classification mapping is also not qualified here. It never declares participation.
The smoke checks native interface structure only after persistence, accepts an empty
objects list and out-of-range coordinates, and never measures accuracy.

## Frozen future smoke procedure — DO NOT RUN DURING PREP

First obtain separate Research Lead authorization for the exact reviewed execution
commit; the Draft PR is not that authorization. No protocol freeze is implied.

1. Create a clean Linux x86_64 / Python 3.11.11 environment and install the exact
   requirements. Provision a dedicated cache in a separate network-enabled process:

   ```sh
   python scripts/provision_moondream_snapshot.py --provision --cache-dir data/processed/moondream_hf --manifest data/processed/moondream_provision.json
   ```

2. Disable network at the venue. In a fresh process, verify without downloading:

   ```sh
   python scripts/provision_moondream_snapshot.py --verify-only --cache-dir data/processed/moondream_hf --manifest data/processed/moondream_verify.json
   ```

3. On exactly one T4, using the approved clean tracked checkout, execute ONCE:

   ```sh
   python scripts/w2_moondream_t4_smoke.py --execute-frozen-smoke --venue-network-disabled --expected-commit APPROVED_EXECUTION_SHA --cache-dir data/processed/moondream_hf --run-id UNIQUE_RUN_ID
   ```

The harness records the actual Git HEAD before permanently denying subprocesses.
A fixed exclusive-create `data/processed/moondream_t4_smoke/ATTEMPT.json` prevents
another attempt even with a different RUN_ID. Do not delete it or move to a fresh
directory to retry. Interrupted attempts are failed attempts, never permission to
rerun. A call failure stops the smoke. No retry, tuning or alternate condition.

Fixture: [red_rectangle.v1.png](../tests/fixtures/moondream_smoke/red_rectangle.v1.png),
1,050 bytes, 384x256 RGB, SHA-256
`aa44c8cbb27ddcdf294a32904cdf7dbbc4bebe027245ed93bd6a6dbce1d3e9cd`.
Handcrafted with stdlib PNG encoding: background (245,245,245), rectangle
(210,40,35) at x in [112,272), y in [64,192), filter 0, zlib level 9, IHDR/IDAT/IEND.
The committed PNG bytes are authoritative. It is separate from all frozen gate
images; no dataset image or generation model was used.

Exactly **one load, one query, one detect**, both on the same fixed bytes:

- Query ID `moondream-runtime-smoke-query-v1`: “Describe the shapes and colors in
  this image in one short sentence.” Settings: temperature 0, top_p 1.0,
  max_tokens 32, variant null, stream false.
- Detect object: `red rectangle`. Settings: max_objects 50, variant null.
  Greedy native spatial decoding; no invented sampling arguments.

Smoke outputs may never be used to tune prompt, dtype, bridge, parser, backend,
dependencies or gate. An unexpected failure must be reported, with no automatic
repair/rerun. Any new condition requires a separate pre-freeze Research Lead decision.

## Future artifacts and remaining boundary

`result.json` schema `moondream-smoke-result-v1` includes run ID, execution commit,
plan/fixture hashes, immutable model/tokenizer IDs, verified snapshot manifests and
their hashes, exact software versions, GPU name/count/VRAM/capability, FP16/NONE,
offload/Pillow/bridge policies, model-load/query/detect counts, raw references and
SHA-256, errors (safe stage/type/cause-type), CUDA allocated/reserved peaks, all
parameter/buffer/cache audit observations and image boundary dtype/device/shape.
`raw/` uses existing FileRawStore with input/prompt/run/call/config provenance.
Pre-parse records remain immutable. All artifacts stay under `data/processed/`.

Process exit zero alone is insufficient. `RUNTIME_INTERFACE_PASS` requires both
raw native outputs, exact counts, five successful state audits, all six expected
image boundaries, valid/restored bindings, native interface checks and memory
observations without errors. This future result means runtime feasibility only.
PREP contains no such result and no full FP16 validation claim.

Current statuses: runner, Starmie enforcement and bridge integration
**PREPARED_NOT_RUNTIME_VALIDATED**; harness **PREPARED_NOT_RUN**;
FULL_FP16_RUNTIME **NOT_VALIDATED**; resource **T4_FEASIBILITY_CANDIDATE**;
classification **CANDIDATE**; grounding
**DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE**.
Protocol freeze SHA remains **PENDING**.

## Validation

Dedicated tests use local synthetic programs, bytes and fake device metadata;
they never import downloaded model code or probe a GPU. The existing bridge tests
exercise real CPU tensors only. Protected-file checks remain in the full suite.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_moondream_runner_smoke tests.test_moondream_precision -v
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m py_compile safeshift/runners/moondream2.py safeshift/runners/moondream_binding.py safeshift/runners/moondream_snapshot.py scripts/provision_moondream_snapshot.py scripts/w2_moondream_t4_smoke.py tests/test_moondream_runner_smoke.py
.venv/Scripts/python.exe -m json.tool configs/pre_freeze/moondream_t4_runtime.v1.json
git diff --check
```

Validation completed: **63/63 dedicated tests PASS** (39 new runner/snapshot/
binding/harness tests plus 24 existing CPU bridge tests), **932/932 full-suite tests
PASS**. All six new Python files compile, both new JSON documents validate, and
`git diff --check` passes. Twenty-one protected files match exact base bytes
(checkout CRLF normalized for text; all eight gate PNGs byte-exact). Test environment:
Windows, Python 3.11.9, torch 2.6.0+cpu; no CUDA build used by bridge tests.
Logs remain ignored under `data/processed/moondream_runner_smoke_prep/`.
Real Linux/T4/model execution checks were intentionally not run under the PREP
firewall. No GitHub Actions workflow exists in this checkout; remote PR check state
will be reported separately, never inferred from local test success. The historical
source allowlist adds only the explicitly authorized D9R2G source paths; its
protected hashes and runtime policies remain unchanged. Census remains untracked
and untouched, SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
