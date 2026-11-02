# Issue173 — reuse original TRAIN and real checkpoint verification

Date: 02/11/2026 (Asia/Bangkok). BASE/main:
`33e9f3cc4daf00c37a31b2347c143444d6add0bb` (PR174 merged).
Authority: [Owner's continuation](https://github.com/tantdna2/SafeShift/issues/173#issuecomment-6580770922)
and the direct task in this session. One branch `verify/issue173-real-checkpoints`,
one Draft PR, no merge. Historical fresh171 production fences remain intact.

## Rights and reused evidence

**RIGHTS_VERIFIED_FOR_THIS_SCOPE**: private, noncommercial SafeShift TRAIN
integrity checks and bounded technical smoke on Owner-controlled Kaggle resources;
no public raw redistribution, TEST reads, new labeling, or scientific release.
This combines the Owner's explicit confirmation of control/data rights with the
historical source/rights record in [THESIS_DATA_PROTOCOL](research/THESIS_DATA_PROTOCOL.md#2-registry-mức-hồ-sơ-nguồn-số-lượng-quyền-và-hdvt),
the original private Input and prior authorized execution receipts, and a fresh
read of the official dataset card at the **exact pinned revision**:
[Tetrabot2026/InspecSafe-V1](https://huggingface.co/datasets/Tetrabot2026/InspecSafe-V1/raw/f3cb7d3e7827c1afc1c5bfd0524257984bba46ab/README.md).
Its bytes SHA256 is `3b667d549cb8612b044a2642da06e66fbcb6d86c321cca4ad9c65bc40f0be203`.
Both YAML and License section declare CC BY 4.0; the card reports 3,763 TRAIN.
No cloud-specific prohibition was found in that card or the inherited project
record. The private Kaggle copies report license `unknown` in upload metadata;
this is not a replacement license or proof of a contrary restriction. Their
bytes must independently match the source locks before use.

Attribution: **Tetrabot2026 / TetraBOT, InspecSafe-V1**, revision
`f3cb7d3e7827c1afc1c5bfd0524257984bba46ab`,
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Images and existing labels remain unchanged; only a derived integrity projection
is generated privately if no suitable seal exists. This scope finding is not
a new certificate about industrial sites, people or other third-party rights.
No specific conflicting restriction has been identified requiring a new Owner
confirmation. New data, redistribution and scientific release remain separate.

Reused rather than rerun: [PR174 software v2](KAGGLE_PREFLIGHT_173.md#version-2-all-pinned-softwareprocessor-checks-passed),
all three exact processor/ABI/CUDA tensor results and the 4.21 GB Qwen software
archive. Historical MiniCPM official160 and InternVL official recovery admission
receipts match the tracked checkpoint identities; these are inherited evidence,
not a fresh byte check. No historical predictions are imported.

## Read-only verification design

Existing private Inputs: original `inspecsafe-v1-kaggle` plus
`safeshift-pilot-input` (which already contains the original 2,488,945-byte master).
The local original master's SHA matches
`a35e91fb431752dbf3b6c161f227d953d5748d69ef9f39aef613019faca33008`.
TRAIN160 alone is not evidence for the complete original TRAIN image bytes.

Existing checkpoint Outputs: `safeshift-prepare-internvl35/1`,
`safeshift-prepare-minicpm4/1`, and
`safeshift-qwen3-m1-model-provision-kaggle` (exact version resolved at submission).
All three are COMPLETE. Downloaded real JSON indices match their expected sizes;
the Qwen historical manifest identifies the four expected shards. The Kaggle
SDK `kernels_list_files` size field returned values around 900 for these objects,
including multi-GB shards. Those listing sizes are **not** accepted as physical
file sizes or integrity evidence; mounted `stat` and streamed SHA256 are required.

`verification173.py` checks the exact flat inventories, source/marker identity,
index bytes, every shard's size and streamed SHA256, bounded safetensors headers,
unique JSON keys, shapes/dtypes, contiguous byte spans, complete tensor-to-shard
membership and total tensor bytes. It imports no tensor/model libraries. The
historical layouts are verified in place; no source lock or revision directory is
renamed to make an old release executable.

`verify_kaggle173_inputs.py` reads only JPG paths from the SHA-verified original
master under the original TRAIN subtree. It does not open annotation sidecars or
TEST files, copy images, change ordering or decode images. Original master label
fields are validated by the existing integrity contract, never exported or used
to repair predictions. A private ordered projection/mapping seal records the
common three-model cohort. It does not activate a fresh171 Input or campaign.

CPU notebook: private, Internet OFF, no GPU, 3,000-second internal alarm and
3,600-second job ceiling. Read-only mounts avoid duplicating 17.53 GB Qwen weights,
9.47 GB InternVL or 8.12 GB MiniCPM and avoid reinstalling software. A small
Output reserve is required. No downloader exists in this verification route.
The storage helper rejects a Qwen download plus software archive and reserve on
the previously observed 19.5 GiB Output filesystem.

Two separate exports: sanitized checkpoint/environment/count receipts; and
**PRIVATE-TRAIN-SEAL.zip**, containing private per-image metadata/failure traces.
Keep the latter outside Git/GitHub. Every invocation creates a new evidence
directory, never an inference attempt or production reservation. Byte PASS does
not imply weights loaded, GPU fit, smoke PASS or scientific qualification.

Build from committed bytes:

```console
python -B -m unittest discover -s tests -p test_kaggle173_verification.py -v
python -B -m scripts.build_kaggle173_verification --source-commit <exact40hex> --output notebooks/SafeShift_ISSUE173_CHECKPOINTS.ipynb
```

Live results, final-source receipts and exact blockers will be appended in this
same branch/PR. Smoke remains subject to the real input/checkpoint/resource gates
and the total ceiling of one image/model and three calls; no bypass of public
production authorization is permitted.
