# InternVL3 P2.1 authority v4 and Kaggle owner runbook

This Draft PR has no effective production authority. Codex creates source,
synthetic tests and notebooks only: no model, GPU, InspecSafe, network
provisioning or production run. The historical v3 runbook remains unchanged.
See `notes/w2_p21_protocol_amendment.md` for the mandatory benchmark adaptation
disclosure. The old strict P2 parser correctly rejected the observed fences;
P2.1 changes the shared format contract after benchmark observation.

## Release gates and source preparation

BASE is `f0b5ea775b3c5bbe5e8618ba1372e59b8b8e150f`. F1 must be its direct child.
F2 must have only F1 as parent and add only
`configs/frozen/p2_execution_authority.v4.json`. Exact SHAs are in the Draft PR
handoff. Authority v4 pins F1/tree, the plan, protocol amendment, exact parser
and preserved scientific/runtime files. The canonical F2 commit encoding pins
the exact F2 without a self-reference. v4 supersedes v3 by exact SHA-256;
historical v1/v2/v3 bytes remain unchanged. Missing or altered v4 fails closed.

Require all external gates in order:

1. Independent audit PASS; ChatGPT compares that audit with the real GitHub code.
2. Research Lead approves a Standard Merge Commit. No squash/rebase/intermediate
   commit: parent1=exact BASE, parent2=exact F2, final tree=exact F2 tree.
3. ChatGPT verifies final merge SHA, parents, tree and main on GitHub. Research
   Lead confirms that exact release SHA. Local Git proof does not prove these
   reviews happened; the source notebook records explicit owner attestations and
   their audit/merge evidence references as separate mandatory gates.
4. Owner prepares the new confirmed-source output online, then production
   preflight passes in the separate Internet-OFF venue.

Open `notebooks/w2_internvl3_p21_source_prep_kaggle.ipynb` on Kaggle with
Internet ON and accelerator NONE. Fill its `CONFIRMATION` release metadata
after the above checks, then Run All. It full-clones the public credential-free
repository, requires fetched main to equal the supplied merge SHA, checks out
that exact SHA and verifies effective v4. It refuses Draft F2, shallow/shared
object stores, dirty source, wrong parents/tree and other authorities. It
packages tracked source, complete `.git` history and a confirmation receipt as
`p21_source_output/internvl3_p21_source.tar.gz` plus
`p21_source_output/p21_source_release.json` with archive SHA-256. Save that
notebook output. This step downloads repository source only; it does not read
dataset/model/GPU or download weights/runtime.

The production source cannot be selected before merge, because the final merge
SHA is not known then. Never substitute Draft F2 or copy the old source checkout
from model prep into production. The new source archive is intentionally
separate from the existing model and runtime outputs.

## Attached inputs and runtime reuse

Open `notebooks/w2_internvl3_p21_shard0_kaggle.ipynb`, set Internet OFF in Kaggle
Settings and select Tesla T4. Attach:

- The new confirmed-source notebook output described above.
- **InternVL3 Source + Model Prep FIX v2**, reusing its existing exact model
  snapshot. The old source in that output is not used as production source.
- **InternVL3 Runtime Prep FIX v2**, reusing its exact Python/runtime bytes.
- Original owner InspecSafe data plus the exact W1 CSV and provenance JSON.
- Old `internvl3-p2-shard0-first` output, or its owner result tar archive, with
  the actual `run_manifest.json` **and** `run_status.json` bytes.

Fill `SETTINGS.final_merge_sha` with the confirmed final merge SHA and set
`kaggle_internet_off_confirmed=True` only after disabling Internet in Kaggle.
Empty path controls request exact-content discovery. To resolve ambiguous
attachments, fill path controls relative to the attached input root, e.g.
`owner-output-slug/subdirectory/runtime.tar.gz`. The fields are notebook input
settings, not changes to frozen source:

| setting | input to select if discovery is ambiguous |
| --- | --- |
| source_release_manifest | new `p21_source_release.json` |
| source_model_input | exact old model output directory or its tar archive |
| runtime_input | exact runtime output directory, tar archive or executable |
| runtime_site_packages | optional exact `lib/python3.11/site-packages` directory for standalone managed Python |
| historical_results_input | old result directory or result tar archive |
| dataset_root | original dataset root containing `train/DATA_PATH` and `test/DATA_PATH` |
| manifest_path | exact source manifest CSV |
| provenance_path | matching original provenance JSON |

Directory attachments and `.tar`, `.tar.gz`, `.tgz`, `.tar.xz` archives are
supported. Archives reject traversal, devices and escaping links. Runtime prep
can contain managed Python and venv in separate tar archives. A venue-specific
absolute venv interpreter symlink is skipped during restore; its regular
managed Python executable and unchanged original site-packages are reused via
the child process environment. No package source, package version, precision,
model or runtime policy is patched. If the output has neither a runnable exact
interpreter nor archived managed Python and site-packages, preflight stops;
there is no automatic installation, runtime rebuild or download fallback.
Attach the already-prepared managed interpreter alongside its venv in that
case. Never download the 4.18 GB model again to repair a verification failure.

Physical FIX v2 output layouts/contents were not supplied to Codex and have not
been venue-validated here. Content discovery and optional input controls avoid
assuming a particular Kaggle slug or archive filename. All restore and launch
logic is in this PR; owner changes only release/attachment settings. No further
code PR or authority session is needed. Synthetic tests cover failure and
one-shot packaging; actual offline owner preflight remains mandatory.

The exact environment is Linux x86_64, one process-visible NVIDIA/Tesla T4
CC7.5, CUDA 12.4, Python **3.11.11**, torch **2.6.0+cu124**, transformers 4.52.4
and every software pin in
`configs/pre_freeze/internvl3_t4_runtime.v1.json`. Interpreter discovery probes
distribution metadata only, never torch/model/GPU. The production child gets
`CUDA_VISIBLE_DEVICES=0` and offline flags before interpreter startup. The
existing native preflight then measures every software/hardware pin before
loading. FP16, quantization NONE, SDPA, `cuda:0`, no CPU/disk offload, the exact
official dynamic tiles and deterministic decoding remain unchanged.

## Exact history, data and shard0 Run All

Historical bytes are copied exclusively into
`data/processed/benchmark/p2/internvl3/internvl3-p2-shard0-first/`. Before any
dataset/model/runtime access, verify:

| historical file | exact SHA-256 |
| --- | --- |
| run_manifest.json | `1c245cacc4bca2230dabc7469824426deb0d5e1345ce9de9618778b6a4221d1c` |
| run_status.json | `1a5a5c88af34341672b5db1c01f99bd782fb0a588a99a19acb4e7a0fe6237a1b` |

Never create a manifest from the supplied count summary. Missing, wrong or
reused lineage fails. P2.1 shard0 is a full new attempt, not reparsing old raw
responses. Dataset fingerprint stays
`7966858d4903f0f7e53e4dda66ef22427cdb400fb33c8ae23b45231b5f03f9f5`,
source manifest SHA-256 stays
`3025edb985d947cbcfe3e397b37aed505e2305b32ece46663d46115c28568577`,
sample count=5013. The production harness rehashes original dataset bytes and
validates all paths/images before backend load; source-authority verification
and historical lineage happen first. The dataset is read from its original
read-only attachment; local metadata copies are ignored derivative artifacts.

Run All **once**. The notebook restores the new source with full Git history,
verifies archive SHA, effective authority and exact old lineage, copies the
existing snapshot to the fixed relative cache, selects the exact runtime and
launches one production child for `internvl3-p21-shard0-rerun1`, shard0/4,
1254 samples. There is no model warm-up, trial generation, automatic retry,
partial resume or same-ID repeat. Re-running in the same working directory
refuses overwrite. Raw output is saved, hash-verified, reread and only then
parsed under `p21-strict-classification-v1`.

An outer `finally` always packages ordinary runtime/preflight/generation
failures and completed 100%-INVALID runs. Notebook bootstrap failures also get
a wrapper report when source code cannot be imported. Save
`internvl3_p21_shard0_output/internvl3-p21-shard0-rerun1_results.tar.gz`,
`owner_result_summary.json`, archive checksum and child log. The archive includes
all available run artifacts, raw responses, receipts and summary; it excludes
dataset/model/runtime bytes. SUCCESS, INVALID, FAILED, NOT_ATTEMPTED,
`zero_canonical_yield` and `stop_before_shards_1_3` are printed. A missing final
status after a process interruption is reported with unknown sample accounting;
partial output never becomes a fabricated COMPLETED run. Host/VM loss or
uncatchable kernel termination cannot execute Python cleanup; preserve whatever
bytes remain and do not resume/retry.

## Remaining three authorized IDs and stop condition

| run_id | shard | samples | lineage |
| --- | --- | --- | --- |
| internvl3-p21-shard0-rerun1 | 0/4 | 1254 | cross-protocol rerun of exact P2 shard0 manifest/status |
| internvl3-p21-shard1-first | 1/4 | 1253 | P2.1 FIRST_ATTEMPT |
| internvl3-p21-shard2-first | 2/4 | 1253 | P2.1 FIRST_ATTEMPT |
| internvl3-p21-shard3-first | 3/4 | 1253 | P2.1 FIRST_ATTEMPT |

If shard0 has zero canonical yield or generation/runtime failure, preserve
artifacts and stop before shards1–3. Authority guards their progression. The
notebook intentionally runs only shard0. After successful owner-reviewed shard0,
the exact remaining run IDs are available through the unchanged thin CLI,
using the selected pinned interpreter and original inputs, with shard-count4
and the corresponding shard-index. There is no permission for a fifth run,
Qwen3, Qwen2.5 or Moondream. Formal model comparisons require matched P2.1
cohorts; historical Qwen2.5 P2 cannot be imported as P2.1 automatically.

Stop after this Draft PR for ChatGPT GitHub verification and Antigravity audit.
Do not merge or execute production in Codex.
