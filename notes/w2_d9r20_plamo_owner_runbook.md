# Owner run 2 — PLaMo 2.1-2B-VL (NOT RUN)

Read [shared workflow](w2_d9r20_owner_workflow.md) first. Exact checkpoint
`pfnet/plamo-2.1-2b-vl@3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027`.
`ACCESS_REQUIRES_OWNER_ACCEPTANCE`: review the official model-card community
license and accept it yourself before downloading. API `gated=false` is not
license consent. This task has not accepted terms or supplied a use clearance.

After owner acceptance and separate authorization, use a new Linux single-T4
environment, never the Ovis environment. A CUDA toolkit/build setup compatible
with torch 2.8.0/cu126 and the pinned extensions may be required by the venue.
Build/toolkit failures must be recorded; do not replace kernels with CPU paths.

```sh
python3.11 -m venv .cache/d9r20_envs/plamo
.cache/d9r20_envs/plamo/bin/python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu126
.cache/d9r20_envs/plamo/bin/python -m pip install packaging ninja wheel setuptools
.cache/d9r20_envs/plamo/bin/python -m pip install --no-build-isolation -r requirements-d9r20-plamo.txt
.cache/d9r20_envs/plamo/bin/hf download pfnet/plamo-2.1-2b-vl --revision 3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027 --include '*.safetensors' '*.json' '*.jsonl' '*.txt' '*.py' --local-dir .cache/d9r20_snapshots/plamo/3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027
```

Build-tool and transitive versions are not a fully resolved installation lock;
observation records all exact installed versions for independent authorization.
Official BF16 usage does not prove FP16. Extension sm_75 targets and FP16 support
do not prove complete Mamba2/Triton compatibility on T4. About 11.5 GB of repository
weights does not prove loaded VRAM fits 16 GB. No quantization/offload rescue.
Keep native ja01 template/dynamic tiling, batch one; include tokenizer.jsonl.

Turn venue Internet off, prepare verified synthetic inputs, then observe:

```sh
.cache/d9r20_envs/plamo/bin/python scripts/run_d9r20_candidate.py observe --model plamo --observation data/processed/d9r20/plamo-observation.json
```

After exact observation review and owner-confirmed license flag in separate
Research Lead authorization:

```sh
.cache/d9r20_envs/plamo/bin/python scripts/run_d9r20_candidate.py run --model plamo --observation data/processed/d9r20/plamo-observation.json --authorization data/processed/d9r20/plamo-authorization.json
.cache/d9r20_envs/plamo/bin/python scripts/run_d9r20_candidate.py bundle --model plamo
```

Run ID `d9r20-plamo-fp16-001`. Record build/kernel/load/memory failure as a
resource blocker, not evidence about grounding semantics. Bare xyxy and exact
target detection lines are predeclared; unknown labels/text invalidate the whole
response. All instances remain in raw and canonical output when parse succeeds.
`CALL2_ORCHESTRATION_BLOCKER` remains after any successful single-target smoke.
