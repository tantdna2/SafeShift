# HNLO T1 CPU verification for three tokenizers (2026-10-17)

## Scope and conclusion

T1 passed with the real, immutable-revision tokenizer snapshots for all three
models. Each tokenizer passed all 28 checks (four canonical labels times seven
currently permitted response variants). For every four-response group, the
complete encodings had equal length and differed at exactly one token position,
the four IDs at that position were distinct, and decoding recovered each exact
response string.

This is a tokenizer precondition only. It is **not** evidence that HNLO ran, that
raw model logits can be captured, or that any GPU experiment is authorized.
DEC-PA3-011 remains PROPOSED and D9R22 remains in force.

Base commit: `fe6d3a21f45a6a3d1048d9b6bee457467fdeae99` (PR #109 merge)

| Model/tokenizer | Immutable revision | Interface | Checks | T1 |
|---|---|---|---:|---|
| `Qwen/Qwen3-VL-8B-Instruct` | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | `AutoTokenizer.from_pretrained(..., local_files_only=True, trust_remote_code=False, use_fast=True)` | 28/28 | PASS |
| `OpenGVLab/InternVL3-2B-hf` | `cb57a075cb75a2e6d1b668b128d48bb00ae321d2` | existing `safeshift.ls1.tokenizer` checker | 28/28 | PASS |
| `moondream/starmie-v1` | `35192e10a54e36eabe0a7cc57a2c1aab371cafc5` | native `tokenizers.Tokenizer.from_file(tokenizer.json)` through a surface-only adapter | 28/28 | PASS |

## Token mappings and variant evidence

The IDs below were measured independently from each named snapshot. The equal
Qwen3 and InternVL3 values were not copied from Qwen2.5 or from each other.

| Tokenizer | Level01 | Level02 | Level03 | Level04 | Vocabulary |
|---|---:|---:|---:|---:|---:|
| Qwen3-VL-8B-Instruct | 16 | 17 | 18 | 19 | 151669 |
| InternVL3-2B-hf | 16 | 17 | 18 | 19 | 151675 |
| Starmie v1 (Moondream2) | 3639 | 5476 | 5772 | 5509 | 51200 |

Every cell below is PASS. `step` is the zero-based position of the only token
that changes among Level01-Level04. The mapping in the preceding table held for
every row.

| Permitted response variant | Qwen3 step | InternVL3 step | Moondream2 step |
|---|---:|---:|---:|
| compact JSON | 7 | 7 | 7 |
| leading space and trailing LF | 7 | 7 | 6 |
| space after colon | 8 | 8 | 8 |
| indented multiline JSON | 9 | 9 | 9 |
| `json` fence with LF | 10 | 10 | 10 |
| plain fence with CRLF | 9 | 9 | 10 |
| leading tab, `json` fence, spaced colon, trailing LF | 13 | 13 | 13 |

The checks use the existing `p21-strict-classification-v1` parser before token
alignment. No prompt, response variant, parser, label, or T1 condition was
relaxed to obtain PASS.

## Tokenizer resources

The complete per-file inventory, immutable source URLs, sizes, SHA-256 values,
and upstream hash type/value are recorded in
`notes/hnlo_t1_tokenizer_manifest_20261017.json`.

- Qwen metadata was inspected first at the exact revision. Its saved response
  is 17,745 bytes with SHA-256
  `ded8d2dc94a34b0acf2a07f70f529afae1df75fd445a3e37e6e52f29c08b44f3`.
  Only the six allowlisted tokenizer/config files were then requested.
- InternVL3 reused three locally present files only after validating their
  pinned size and Git blob SHA-1. The other five files were downloaded at the
  exact revision. The checker preserves the pinned distinction between Git
  blob SHA-1 and SHA-256; it does not compare one as the other.
- All four Starmie files were reused after size and SHA-256 validation; none was
  downloaded again.
- The online preparation helper rejects common weight/checkpoint suffixes,
  enforces a flat allowlist and size ceiling, and fetches exact-revision URLs.
  T1 itself sets the existing offline environment controls and denies socket
  access.

The tokenizer bytes, virtual environments, revision metadata response, and full
JSON run results are intentionally outside Git tracking under:

`data/processed/hnlo_t1_cpu_20261017/`

Final result receipts in that ignored directory:

| Result | Bytes | SHA-256 |
|---|---:|---|
| `results/qwen3_t1_final.json` | 13354 | `4e95baea5347a245d9e067bb2893d1610876dbc8164066f15c00e9df342e20e3` |
| `results/internvl3_t1_final.json` | 12166 | `a043b95692b4e67f39f7b9240cc76fdebebd5d584aa11b7d8b0a158775758731` |
| `results/moondream2_t1_final.json` | 13795 | `7a2be89e88aadadbd26ec1bb25d228f3d98d3cea710cf403db272d92067e325e` |

## CPU environments

All three isolated environments used CPython 3.11.9. No environment contained
PyTorch, TensorFlow, a CUDA package, or model weights.

| Environment | Actual relevant versions |
|---|---|
| Qwen3 | `transformers==4.57.1`, `tokenizers==0.22.2`, `huggingface-hub==0.36.0` |
| InternVL3 | `transformers==4.52.4`, `tokenizers==0.21.2`, `huggingface-hub==0.30.2` |
| Moondream2 | `tokenizers==0.21.2`, `huggingface-hub==0.36.2` |

Minimal setup shape (paths are repository-relative and ignored):

```powershell
py -3.11 -m venv data/processed/hnlo_t1_cpu_20261017/envs/qwen3
data/processed/hnlo_t1_cpu_20261017/envs/qwen3/Scripts/python.exe -m pip install transformers==4.57.1 huggingface-hub==0.36.0

py -3.11 -m venv data/processed/hnlo_t1_cpu_20261017/envs/internvl3
data/processed/hnlo_t1_cpu_20261017/envs/internvl3/Scripts/python.exe -m pip install transformers==4.52.4 tokenizers==0.21.2 huggingface-hub==0.30.2

py -3.11 -m venv data/processed/hnlo_t1_cpu_20261017/envs/moondream2
data/processed/hnlo_t1_cpu_20261017/envs/moondream2/Scripts/python.exe -m pip install tokenizers==0.21.2 huggingface-hub==0.36.2
```

The only online resource-preparation command was:

```powershell
python scripts/prepare_hnlo_t1_tokenizers.py --output-root data/processed/hnlo_t1_cpu_20261017
```

After preparation and checksum validation, the three T1 commands were run with
network access denied by the checker:

```powershell
data/processed/hnlo_t1_cpu_20261017/envs/qwen3/Scripts/python.exe -m safeshift.ls1.t1_cpu --model qwen3 --snapshot data/processed/hnlo_t1_cpu_20261017/snapshots/qwen3/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b --manifest data/processed/hnlo_t1_cpu_20261017/resource_manifest.json --output data/processed/hnlo_t1_cpu_20261017/results/qwen3_t1_final.json

data/processed/hnlo_t1_cpu_20261017/envs/internvl3/Scripts/python.exe -m safeshift.ls1.tokenizer --model internvl3 --snapshot data/processed/hnlo_t1_cpu_20261017/snapshots/internvl3/cb57a075cb75a2e6d1b668b128d48bb00ae321d2 --output data/processed/hnlo_t1_cpu_20261017/results/internvl3_t1_final.json

data/processed/hnlo_t1_cpu_20261017/envs/moondream2/Scripts/python.exe -m safeshift.ls1.t1_cpu --model moondream2 --snapshot data/processed/hnlo_t1_cpu_20261017/snapshots/moondream2/35192e10a54e36eabe0a7cc57a2c1aab371cafc5 --manifest data/processed/hnlo_t1_cpu_20261017/resource_manifest.json --output data/processed/hnlo_t1_cpu_20261017/results/moondream2_t1_final.json
```

## Boundary confirmation and remaining gate

- GPU used: NO.
- Model weights/checkpoints downloaded or loaded: NO.
- Model inference used: NO.
- InspecSafe, TEST, annotation, or ground truth accessed: NO.
- Production runners, prompts, production configuration, datasets, labels,
  HNLO formulas, `DECISIONS.md`, and `ROADMAP.md` changed: NO.

There is no remaining T1 blocker for these three tokenizer revisions. Before a
GPU test can be authorized, the research decision/authority gate must still be
resolved and each production model interface must separately demonstrate
durable capture of raw, pre-processor logits. This CPU result neither verifies
that capability nor grants permission to proceed.
