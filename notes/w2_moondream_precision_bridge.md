# W2.6-D9R2F — post-normalization CPU precision bridge

**PREPARED_NOT_RUNTIME_VALIDATED.** Research Lead explicitly authorized this
pre-freeze runtime condition before model inference, synthetic gate and InspecSafe:
upstream crop/resize/conversion/BF16 allocation/BF16 normalization run unchanged on
CPU; after `prepare_crops` returns, SafeShift adds intentional BF16-to-FP16
conversion on CPU. Only the resulting FP16 tensor may later move to CUDA.
This is not the original upstream runtime and does not establish numerical
equivalence across precisions or environments.

Base main: `08a501b6f7d1086c5a74c8352c96d05172c6c1e6`.
Branch: `implementation/d9-moondream2-precision-bridge`.
[Decision](../DECISIONS.md#d9r2f-moondream-post-normalization-precision-bridge-2026-09-26),
[machine-readable plan](../configs/pre_freeze/moondream_precision_bridge.v1.json),
[helper](../safeshift/runners/moondream_precision.py),
[tests](../tests/test_moondream_precision.py).

## Exact source and placement

Model `vikhyatk/moondream2` is pinned to
`9a7d4024050840e001defacec2b00727e89149e6`. Existing local source captures were read
as text and rehashed against the unchanged
[D9R2E audit](../configs/pre_freeze/moondream_prep_audit.v1.json). Five checked files:
`vision.py`, `moondream.py`, `hf_moondream.py`, `image_crops.py`, `config.py`.
Their exact SHA-256/size/source URLs are also in the bridge plan. No upstream
source bytes were edited or executed; no source is vendored by this change.

The pinned [Moondream source](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/moondream.py#L202)
imports `prepare_crops` into **moondream.py's global namespace** from `.vision`.
`MoondreamModel._run_vision_encoder` calls it using `device=self.device`, unpacks
`all_crops, tiling`, calls `torch._dynamo.mark_dynamic(all_crops, 0)`, then consumes
the tensor via `self._vis_enc(all_crops)`. `_vis_enc` calls `vision_encoder`; its
first parameterized operation is `patch_emb`. HF properties forward query/detect/
point to the inner model, whose `encode_image` reaches `_run_vision_encoder`.

```text
HF query/detect/point -> inner encode_image -> _run_vision_encoder
  prepare_crops(image, vision_config, device=CPU) [future integration routes CPU]
    original crop/resize/RGB conversion
    original BF16 allocation + all BF16 normalization, on CPU
    return (all_crops, tiling)
  SafeShift post_normalization_fp16_bridge(return_value)
    validate -> CPU BF16-to-FP16 copy -> validate -> (FP16 CPU crops, tiling)
  [future runner only: validated FP16 CPU -> CUDA]
  original mark_dynamic -> _vis_enc -> vision_encoder -> patch_emb
```

The [pinned return value](https://huggingface.co/vikhyatk/moondream2/blob/9a7d4024050840e001defacec2b00727e89149e6/vision.py#L25)
is a two-tuple, not just a tensor. `image_crops.py` allocates one global crop plus
`rows * cols` local crops; `vision.py` transposes NHWC to NCHW, returning
`(Tensor[1+rows*cols, 3, 378, 378], (rows, cols))`. Non-contiguous strided tensors
are legitimate. Tiling consists of positive Python integers. No arbitrary crop
count cap is added by the bridge. No crop or tiling is reordered.

A hook on patch_emb or `_vis_enc` alone is **too late**: unchanged
`prepare_crops(..., device=self.device)` would already allocate BF16 on CUDA.
The future call-site wrapper must explicitly request CPU from the original
function, wait for its complete return, and then invoke the bridge. A return-only
hook that leaves the original CUDA device argument is forbidden.

## Implemented helper contract

`post_normalization_fp16_bridge(upstream_result)` only validates, converts and
returns. It lazily imports PyTorch and knows no model loader, image path, remote
module, network client, prompt, native spatial API or model output parser.

- Accept only an exact built-in two-tuple with one plain `torch.Tensor` and an
  exact two-tuple of positive built-in integers. Reject lists, dictionaries,
  Tensor subclasses, extra/nested tensors, tensor-valued tiling and bools.
- Require CPU before arithmetic; require exact BF16. Already-FP16, FP32,
  non-floating and any non-CPU device are errors, not accepted alternatives.
- Require dense strided, non-nested crops with no gradients and the exact derived
  shape. Require finite input. Never attempt a device transfer to recover input.
- Execute `crops.to(dtype=torch.float16, copy=True)` without a device argument.
  Check returned device/dtype/shape and finiteness, including FP16 overflow.
  Return a fresh tensor and the original immutable tiling tuple. Do not mutate
  input storage. A conversion failure propagates; no retry/fallback/autocast.

No value-based research threshold is introduced. Finite input/output and geometry
are technical contract checks. Underflow/rounding that remains finite is not
repaired. The helper cannot prove preprocessing history from a tensor, nor prevent
an unrelated caller from bypassing it; enforcement belongs to future integration.
The strict closed return structure prevents an extra floating tensor travelling
through this boundary unconverted.

## Future integration design — not installed or runtime-tested

Prefer a **per-instance binding of the original function bytecode with a private
globals overlay**, avoiding mutation of a shared module-global function reference.
This plan requires review/tests during the future runner task; this PR installs
no hook, binding, monkeypatch or remote function.

1. Dedicated single-owner process, one audited model instance. Verify exact model,
   config and remote-file hashes before loading (tokenizer enforcement is separate
   and still unimplemented). Reject compiled/replaced call paths. Confirm
   `type(inner)._run_vision_encoder` is the exact audited function,
   `inner._run_vision_encoder.__func__ is expected_function`, and
   `expected_function.__globals__["prepare_crops"] is verified_vision.prepare_crops`.
   Validate unchanged config and the selected resize backend. No guessing by name
   or signature alone; bytes and actual function identities must match.
2. Copy that function's globals dictionary privately and replace **only** its
   `prepare_crops` entry with a process-local wrapper. Construct a function with
   `types.FunctionType` using the unchanged `__code__`, defaults and closure;
   preserve keyword defaults. Bind to this one inner instance using
   `types.MethodType`. Do not assign `vision.prepare_crops`,
   `moondream.prepare_crops`, any class attribute or a torch global. The copied
   dictionary is private integration state and must not be exposed or mutated
   during calls. Original bytecode, crop logic and downstream reconstruction stay
   intact; no modified upstream source is written/imported.
3. Wrapper accepts only the audited arguments/vision-config identity and expected
   requested target device. Invoke the saved **original** prepare function with
   `device="cpu"`. It completes original BF16 normalization. Pass its entire return
   value through the helper. Only then may the future runner transfer this exact
   FP16 CPU tensor to its separately validated target. Reject non-FP16 output at
   the transfer boundary and again at vision consumption. No other tensor can use
   this transfer path. Never move the original BF16 crop tensor.
4. Hold a non-reentrant exclusive ownership guard across binding, preprocessing,
   transfer, consumption and restoration; reject concurrent/reentrant load/call,
   do not queue an unsafe second call. No other thread may use the instance.
   In `finally`, restore the exact prior instance attribute, or delete the shadow
   attribute if originally absent. Verify restoration after success and exception;
   unexpected intervening changes invalidate the process. Do not leave a partially
   bound instance reusable after failure. No worker may bypass the guard.
5. Forbid user-supplied `EncodedImage` (it short-circuits image encoding), stale
   encoded caches, custom preprocessors and alternative vision entry points.
   Audit all floating image tensors before any future CUDA transfer. Separate
   model parameters, buffers, caches and non-image tensors need their own audit.

Thus no **module-global monkeypatch** is needed in this proposed design. A scoped
instance-method substitution is still a deliberate runtime intervention requiring
identity checks, exclusive ownership and `finally` restoration. It is not asserted
compatible with compilation, arbitrary Transformers revisions or concurrent calls.
The helper itself is stateless; callers must not mutate its input concurrently.

The helper neither changes nor selects a resize backend. Pinned upstream chooses
pyvips when import succeeds and Pillow otherwise; a future runner must pin/verify
the branch and software before calls, with no automatic switch. None was executed
in this task. The bridge does not normalize in FP16 or cast between upstream
normalization steps.

## CPU evidence and reproduction

Tests use real CPU tensors and local fakes, never imported remote Moondream code.
CUDA-like rejection tests temporarily mock device metadata on real CPU tensors;
they reject before arithmetic or transfers. Test guards reject `.cuda()`, CUDA
initialization, autocast, socket access, file reads during conversion and imports
of model/Hub/tokenizer libraries. No GPU device probe is needed.

Dependencies: Python 3.11.9 and `torch==2.6.0+cpu`; PyTorch reports no CUDA build.
The CPU wheel source follows [official versioned installation guidance](https://pytorch.org/get-started/previous-versions/#v260).
This is only a bridge test environment, not a frozen model environment. Install
the dedicated requirements plus existing validation requirements for the full suite:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-moondream-bridge.txt
.venv/Scripts/python.exe -m pip install -r requirements-validation.txt
.venv/Scripts/python.exe -m unittest tests.test_moondream_precision -v
.venv/Scripts/python.exe -c "import json; from tests.test_moondream_precision import numerical_diagnostic; print(json.dumps(numerical_diagnostic(), indent=2))"
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -m py_compile safeshift/runners/moondream_precision.py tests/test_moondream_precision.py
.venv/Scripts/python.exe -m json.tool configs/pre_freeze/moondream_precision_bridge.v1.json > $null
git diff --check
```

Deterministic fixture: 256 float32 values from linspace(-1,1), converted to BF16
and repeated to `(2,3,378,378)`. Seed not applicable; no randomness. These are
handcrafted normalized-like values, not an upstream image preprocessing execution.
Observed diagnostic: BF16 CPU -> FP16 CPU, shape unchanged, input/output finite,
`max(abs(float32(input_BF16) - float32(output_FP16))) = 0.0`.
These normal-range BF16 fixture values are representable in FP16; that result
does not compare bit encodings or establish a general equivalence. A separate
tiny-value test (`2**-30`) demonstrates a nonzero difference on conversion;
finite large BF16 inputs overflowing FP16 are rejected. No research metric,
empirical prompt/dtype selection or accuracy threshold is involved.

The tested dependency versions are recorded in the validation section below.
NumPy is not needed by this independent tensor helper; PyTorch's import warning
about absent NumPy is expected in this minimal environment. It does not mean that
the future upstream preprocessing environment is ready (upstream requires NumPy).

Environment observed with `pip freeze`: torch 2.6.0+cpu, filelock 3.32.3,
fsspec 2026.7.0, Jinja2 3.1.6, MarkupSafe 3.0.3, mpmath 1.3.0, networkx 3.6.1,
sympy 1.13.1, typing_extensions 4.16.0; existing Pillow 12.3.0. Tests ran on
Windows with Python 3.11.9. Only PyTorch CPU software dependencies were downloaded.
The Git commit containing these files identifies the tested helper; no model run
or model-output artifact exists. To reproduce the CPU diagnostic as a local
artifact, serialize `numerical_diagnostic()` under `data/processed/`; do not call
an upstream method to produce it.

## Remaining qualification boundary

Validation completed: **24/24 bridge tests PASS**, **893/893 full-suite tests
PASS**, new Python files compile, bridge JSON validates and `git diff --check`
passes. Eighteen protected repository files (including eight PNGs) match exact
base hashes; text checks normalize checkout CRLF to Git LF, PNGs remain byte-exact.
Five upstream captures were separately rehashed against the audit, all matching.
No tests rely on importing those captures. The initial full-suite run rejected
the new helper in the historical source allowlist; only this explicitly authorized
helper path was added to that list. No protected hash or runtime requirement was
relaxed. No real runtime validation was performed.

FULL_FP16_RUNTIME remains NOT_VALIDATED. This helper addresses only image
preprocessing output. It proves nothing about model parameters, buffers, KV cache,
vision encoder, text model or region model precision/device/feasibility. Real T4
smoke remains required in a later task. Runner PENDING; T4 smoke NOT_RUN; resource
T4_FEASIBILITY_CANDIDATE; classification CANDIDATE; grounding
DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE.

Starmie remains `moondream/starmie-v1` at
`35192e10a54e36eabe0a7cc57a2c1aab371cafc5`; runtime enforcement NOT_IMPLEMENTED.
No weights, model inference, external synthetic gate or InspecSafe were used.
No full runner, loader, adapters or smoke harness were created. Protocol freeze
SHA remains PENDING. Historical D9R2E audit and all protected files remain intact.
Census remains UNTRACKED/UNTOUCHED, SHA-256
`cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb`.
