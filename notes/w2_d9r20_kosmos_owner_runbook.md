# Owner run 3 — Kosmos-2 (NOT RUN)

Read [shared workflow](w2_d9r20_owner_workflow.md) first. Exact checkpoint
`microsoft/kosmos-2-patch14-224@1f66d913fde5307936383dc9460b12ccb82f2133`.
MIT; no HF gate observed. Safetensors metadata is 6,658,052,808 bytes. Download
only safetensors, not the duplicate pytorch_model.bin. FP16 single-T4 feasibility
is unverified; the official Fairseq FP16 path is not a tested HF/T4 result.

After separate authorization, create its own Linux single-T4 environment:

```sh
python3.11 -m venv .cache/d9r20_envs/kosmos
.cache/d9r20_envs/kosmos/bin/python -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu126
.cache/d9r20_envs/kosmos/bin/python -m pip install -r requirements-d9r20-kosmos.txt
.cache/d9r20_envs/kosmos/bin/hf download microsoft/kosmos-2-patch14-224 --revision 1f66d913fde5307936383dc9460b12ccb82f2133 --include '*.safetensors' '*.json' '*.txt' '*.model' --local-dir .cache/d9r20_snapshots/kosmos/1f66d913fde5307936383dc9460b12ccb82f2133
```

Use `Kosmos2ForConditionalGeneration` and native `AutoProcessor`, no remote code,
torch FP16, explicit cuda:0. These HF dependency versions are SafeShift prospective
pins, not a claim that Microsoft published this full environment. Do not alter
native image processing or save/reload JPEG as the illustrative README does;
qualification uses fixed hashed RGB PNG bytes and square images only.

Turn venue Internet off, prepare synthetic inputs, then observe:

```sh
.cache/d9r20_envs/kosmos/bin/python scripts/run_d9r20_candidate.py observe --model kosmos --observation data/processed/d9r20/kosmos-observation.json
```

After separate approval of exact environment and post-merge identity:

```sh
.cache/d9r20_envs/kosmos/bin/python scripts/run_d9r20_candidate.py run --model kosmos --observation data/processed/d9r20/kosmos-observation.json --authorization data/processed/d9r20/kosmos-authorization.json
.cache/d9r20_envs/kosmos/bin/python scripts/run_d9r20_candidate.py bundle --model kosmos
```

Run ID `d9r20-kosmos-fp16-001`. Raw generated IDs are persisted before any decode
or official-equivalent coordinate extraction. The strict REC grammar preserves
all location-token pairs; no select-first, discarded caption entities or repaired
labels. Absent-target false positives/giant boxes and multi-instance misses are
recorded separately from interface observations; no output correction.
`CALL2_ORCHESTRATION_BLOCKER` and non-square production preprocessing audit remain.
