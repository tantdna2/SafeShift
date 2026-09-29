# D9R8 — PaliGemma offline runner and single-T4 smoke PREP

Task: `W2.6-D9R8-PALIGEMMA-RUNNER-SMOKE-PREP`, 2026-09-28.
Base: `97682b682f85ee0d9cfe646e5a69367c4d46afa6` (merge of PR #55).
Authority: the owner's explicit D9R8 PREP instruction. No new research policy.

**NO REAL MODEL OR GPU EXECUTION. NO WEIGHTS DOWNLOADED.** No provision, external
gate, InspecSafe, promotion, protocol freeze or merge is performed in this task.
Historical D9R6/D9R7 evidence, DECISIONS, roster and provenance stay unchanged.
The owner's untracked census manifest is excluded and untouched.

## Status boundary

| Field | PREP status |
| --- | --- |
| Runner | `PREPARED_NOT_RUNTIME_VALIDATED` |
| Real runtime | `PENDING_QUALIFICATION` / `NOT_RUN` |
| Exact runtime verified | `false` |
| Grounding / classification interface / external gate | `PENDING_QUALIFICATION` |
| Production adapters | classification `INVALID`, grounding `UNSUPPORTED`; no canonical value |
| Role / primary count | `BACKUP_1` / `4` |
| Protocol freeze / InspecSafe authorized | `PENDING` / `BLOCKED`; `false` |

## Immutable identity and snapshot

Model: `google/paligemma-3b-mix-448`.
Revision: `ead2d9a35598cb89119af004f5d023b311d1c4a1`.
[Runtime plan](../configs/pre_freeze/paligemma_t4_runtime.v1.json) SHA256:
`4138071ff3fcbcf2cb16d456c01a2b3dbc42a628b0faa0d04dd6a635803b0ab7`.
Hash definition: UTF-8 JSON with recursively sorted keys, compact separators,
`ensure_ascii=True`, `allow_nan=False`, no trailing newline. The snapshot module
embeds this digest and refuses any changed plan. It is not the pretty-file hash.

All 14 files in the exact revision are allowlisted with published sizes and Git
blob SHA1 or LFS SHA256. Three safetensor shards total 11,697,486,320 bytes; their
hashes/sizes agree with the existing PaliGemma provenance. The five previously
verified metadata entries agree with the D9R7 audit. Remaining inventory is from
the [exact public Hub metadata](https://huggingface.co/api/models/google/paligemma-3b-mix-448/revision/ead2d9a35598cb89119af004f5d023b311d1c4a1?blobs=true),
read on 2026-09-28 without authentication. No checkpoint/tokenizer bodies were
downloaded for this task. Local weight bytes remain unverified.

Provisioning is a separate explicit `--provision` process, never a runtime
fallback. It requests only the exact ID, revision and inventory in a fresh,
dedicated repository-relative cache. Nonempty/interrupted caches are refused;
there is no overwrite or repair. Select a fresh path after review on failure.
Runtime and `--verify-only` rehash every file, reject missing/extra files,
size/hash mismatch and incorrect revision directories before either loader.
Hub blob symlinks must remain inside the dedicated model cache; escaping aliases
are rejected. Verification assumes a trusted filesystem without concurrent edits.

## Native model semantics and software

The [D9R7 audit](../configs/pre_freeze/paligemma_source_api_audit.v1.json) supplies
the exact config/interface and v4.57.1 source evidence. InternVL3 is used only as
a lifecycle/storage/harness structural reference. Its chat template, dynamic
tiling, image-token IDs, Qwen RoPE/cache rules and output semantics are not used.

The loader is `PaliGemmaForConditionalGeneration`; `AutoProcessor` maps natively
to `PaliGemmaProcessor`. Both use `trust_remote_code=False`,
`local_files_only=True` and the verified local exact-revision directory. The
native v4.57.1 default loads slow `SiglipImageProcessor` and `GemmaTokenizerFast`;
both concrete classes are checked. `use_fast` is deliberately omitted: in this
audited native loader, explicitly setting it false also switches the tokenizer
to SentencePiece. This default selection is bound by software/source hashes and
checked after load; any different classes fail rather than trigger fallback.

Input is local image bytes via SafeShift `Request`, decoded to a fresh RGB PIL
image, plus caller-supplied explicit text. No URL image loader or chat history.
The native processor owns resize to 448x448, rescale/normalization, 1,024 image
tokens (ID 257152), BOS and newline. Runner checks one image/batch, token count,
tensor dimensions and FP16 pixels/int64 tokens on cuda:0. No bespoke resize/crop.

Smoke uses `answer en What color is the shape?` on two locally drawn shapes.
`answer en {question}` and `detect {object}` are documentary prompt families;
there is no final SafeShift classification prompt. Qualification decoding is
greedy, at most 32 new tokens, one beam/return sequence, `use_cache=False`, no
scores/logits/attention/hidden-state returns. Native `logits_to_keep=1` limits
logit materialization to the last position. Each call gets fresh inputs and a
deep copy of checkpoint generation configuration. Research prompt/decoding
freeze remains PENDING. No output or KV cache is carried between calls.

[Isolated requirements](../requirements-paligemma-t4.txt) pin CPython 3.11.11 /
Linux x86_64 candidate dependencies. Reuse the established torch 2.6.0+cu124,
CUDA 12.4, torchvision 0.21.0+cu124, Pillow 11.2.1, numpy 1.26.4 and safetensors
0.5.3 pins; select audited Transformers 4.57.1, tokenizers 0.22.1,
huggingface-hub 0.35.3 and its hf-xet 1.1.10 dependency. Xet remains disabled at
runtime. No global environment update or dependency installation here.

The [versioned dependency table](https://raw.githubusercontent.com/huggingface/transformers/v4.57.1/src/transformers/dependency_versions_table.py)
and package metadata URLs recorded in the plan establish the required hub
>=0.34,<1 and tokenizers >=0.22,<=0.23 bounds; the older InternVL pins cannot be
reused unchanged. This is a candidate, not an installed-environment claim.
Actual future wheel installation and `pip check` must pass without changing pins;
an unresolvable conflict requires `STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED`.

Metadata-only closure check: 40/40 pinned distributions, zero unresolved active
requirements for Linux x86_64 / CPython 3.11.11 with no extras. Read each
`https://pypi.org/pypi/{name}/{version_without_local_suffix}/json`, evaluate
`requires_dist` markers for that environment, and compare each requirement with
the candidate pins. For torch/torchvision, this checks the base release metadata,
not the cu124 wheel bytes or an actual resolver/install. Local diagnostic report:
`data/processed/paligemma_dependency_metadata_report.json` (ignored, not committed).

Exactly one process-visible NVIDIA/Tesla T4, CC 7.5, 14–16 GiB, cuda:0, FP16
parameters, NONE quantization, batch 1. All parameters/buffers must reside on
cuda:0; CPU checkpoint deserialization is not CPU inference offload. Missing,
unexpected or mismatched checkpoint keys fail. No device_map=auto, CPU/disk
offload, alternative model/revision, BF16/quantization or attention fallback.

## Offline boundary and persistence

Required HF offline variables and Python socket denial precede backend imports
and remain active through the runner lifecycle. Source hashes from D9R7 and all
software versions are checked. Python network denial is not a host firewall;
venue Internet OFF is separately required and recorded as owner attestation.

Use `paligemma.execute_call` with `VerifiedRawStore`: native generate/decode →
exclusive raw/provenance write → flush/fsync → re-read → size/SHA256/metadata
verification → adapter. Corruption or failed fsync blocks adaptation. Successful
decoding preserves full native generated IDs, continuation IDs, text both with
and without special tokens (including loc tokens). Records bind model/revision,
execution commit, run/call/sample IDs, input hash, explicit prompt/text/hash,
dtype/device, software, hardware, decoding, command, timestamp and raw checksum.
Decode/post-generation audit failures preserve captured IDs before reporting
failure. A blocking generate failure cannot promise tokens it never returned.

Failures terminate the lifecycle; no retry with another precision/device/model.
The PaliGemma executor also terminates on storage or parser exceptions. Expected
pending-adapter INVALID/UNSUPPORTED results are not runtime failures. A fresh
call ID cannot recover a failed runner. `close()` releases the network guard.

`loc_values_to_d4` is a pure helper, not a detection grammar parser. D9R7 maps
integer `[y_min,x_min,y_max,x_max]` in 0..1023 to
`[x_min/1024.0,y_min/1024.0,x_max/1024.0,y_max/1024.0]`.
Maximum is 1023/1024, never rescaled to 1.0. Invalid types/ranges, reversed or
degenerate boxes fail `PARSER_FAIL_NO_REPAIR` under existing D4 validity rules.
NO_CLAMP, no point-to-box, fabricated boxes or artificial zero IoU. Native output
grammar conformance remains PENDING_QUALIFICATION. Pending adapters never call
this helper to infer a canonical model result.

## Future owner runbook — NOT EXECUTED IN PREP

After review and separate authorization, use a clean checkout at the reviewed
40-hex execution commit, a fresh isolated CPython 3.11.11 Linux environment, and
owner-configured HF access covered by Gemma terms. Never paste credentials into
chat or record them in artifacts. Install and provision in separate processes:

```sh
python -m pip install -r requirements-paligemma-t4.txt
python -m pip check
python scripts/provision_paligemma_snapshot.py --provision --cache-dir data/processed/paligemma_hf_cache --manifest data/processed/paligemma_provision_01.json
```

Then disable venue Internet. On Kaggle T4x2, mask to one T4 before Python starts;
restart any existing notebook kernel. The runtime checks process-visible count:

```sh
export CUDA_VISIBLE_DEVICES=0
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1
export HF_HUB_ENABLE_HF_TRANSFER=0 HF_HUB_DISABLE_XET=1
python scripts/provision_paligemma_snapshot.py --verify-only --cache-dir data/processed/paligemma_hf_cache --manifest data/processed/paligemma_verify_01.json
python scripts/w2_paligemma_t4_smoke.py --run-id paligemma-t4-smoke-UNIQUE --expected-commit REVIEWED_40_HEX_EXECUTION_SHA --cache-dir data/processed/paligemma_hf_cache --venue-internet-off
```

Replace placeholders explicitly; do not infer the reviewed SHA from arbitrary
HEAD. The harness accepts no dataset/input image path and loads once for two
independent calls. A pre-existing run directory cannot be overwritten. Artifacts
stay under `data/processed/runtime_validation/w2_paligemma_t4_smoke/<run_id>/`:
run metadata, full software/hardware environment, snapshot manifest, local input
drawings, raw/provenance/results, memory/state audits and checksummed summary.
Stop on any failure; do not repair the run by changing model/resource settings.

A future `RUNTIME_INTERFACE_PASS` only reports the native interface and resource
smoke returning under these conditions. It does not qualify grounding,
classification, external gate, promotion, exact research protocol or InspecSafe.

## Validation

44/44 focused PaliGemma fake/static tests and 162 related regression tests PASS
(206 total), on Windows / Python 3.11.9. All 28 pre-freeze JSON files parse; both
new CLI `--help` paths work without importing a backend; `git diff --check` PASS.
The D9 source allowlist test adds only the four newly authorized PREP source files.

```powershell
.venv/Scripts/python.exe -m unittest tests.test_paligemma_prep tests.test_local_runners tests.test_internvl3_prep tests.test_internvl3_runtime_result tests.test_d9r6_paligemma_primary_expansion_precommit tests.test_d9r7_paligemma_source_api_audit tests.test_d9_t4_roster_revision tests.test_model_provenance -q
.venv/Scripts/python.exe -c "import json,pathlib; paths=list(pathlib.Path('configs/pre_freeze').glob('*.json')); [json.loads(p.read_text(encoding='utf-8')) for p in paths]; print(len(paths))"
.venv/Scripts/python.exe scripts/w2_paligemma_t4_smoke.py --help
.venv/Scripts/python.exe scripts/provision_paligemma_snapshot.py --help
git diff --check
```

Coverage includes exact identity/plan/software pins, hardware restrictions,
snapshot inventory/hash/size/revision, explicit fake provisioning/no fallback,
native processor/input checks, independent calls/no cache, pending adapters,
fsync/re-read/checksum-before-adapter, corrupt/failed persistence, terminal failure,
partial token evidence, /1024 endpoint and malformed/no-repair boundaries. Fake
smoke PASS values are test assertions, never real qualification results.

No real backend import, GPU stack install, snapshot provision or real smoke was
performed. Full repository suite was not run because the change is confined to
PaliGemma PREP; related contracts, roster, history and runners were checked above.
Future environment install and runtime remain unrun by the explicit task scope.
