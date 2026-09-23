# W2.6B1B-PREP — Kaggle T4 x2 Qwen runtime smoke

**Historical execution procedure.** The [2026-09-23 audited result](w2_qwen_kaggle_smoke_result.md)
records PASS at `784c465cae5188ed6ede5673140a4a281f2ffb52`. The pending statements
below describe PREP, before that run. `B1B_PREP_HEAD` now retains that execution
commit while PR HEAD includes result-recording changes. Cell 2's original equality
guard will therefore stop on the current PR; keep it intact. This recording task
does not authorize a rerun or updating the execution pin to the recording commit.

**PREPARED; REAL KAGGLE EXECUTION PENDING.** Base main:
`bd18a64bc76653893abaf5d36a3d9d6dd2665073` (PR #23).
Branch: `validation/d9-qwen-kaggle-smoke`. This is an Owner-run technical smoke,
not SYNTHETIC V1, a hazard accuracy evaluation, or an authorization for dataset
inference. Grounding remains `UNCERTAIN_REQUIRES_EXTERNAL_GATE` / `NOT_YET_QUALIFIED`.
Checklist #1 COMPLETE documentary; #2–#8 PENDING;
`protocol_freeze_commit_sha=PENDING`. No role assignment or backup activation.

The [plan](../configs/pre_freeze/qwen_kaggle_smoke.v1.json) locks the literal prompt,
its SHA-256, two handcrafted geometric images, FP16 / NONE / auto / official processor,
native default attention and greedy `do_sample=false, max_new_tokens=32` **before
seeing any model output**. FP16 is the requested runtime candidate for T4's memory
budget; it is not `selected_precision`, an established working configuration, or
a research decoding/environment freeze. No BF16 attempt, FP32, quantized fallback,
flash-attn installation, placement rescue, or tuning is allowed in this procedure.
Image generation uses fixed Pillow primitives, 224x192 RGB PNG with fixed compression,
no random seed needed. Both hashes are checked against all eight SYNTHETIC V1 hashes;
only its provenance JSON is read, never its images as inputs. Generator source hash,
Pillow and zlib versions make the byte-generation environment auditable; cross-version
PNG-byte equality is not assumed.

Use a **fresh Kaggle Notebook**, accelerator **GPU T4 x2**, Internet ON for Cells 2–6.
The SafeShift repository is private. In Kaggle **Add-ons → Secrets**, add and enable
`SAFESHIFT_GITHUB_TOKEN`: a GitHub fine-grained token restricted to `tantdna2/SafeShift`
with **Contents: read** and **Pull requests: read**. Do not paste its value into cells.
Execute these Python cells in order. Stop on any cell exception; do not continue past
a failed provisioning/verification/preflight. Following a smoke failure, Cells 9–10
remain available to collect evidence. Cells are for the Project Owner; none were
executed against real hardware during PREP.

## Cell 1 — inspect Kaggle environment

```python
import os, sys, subprocess, json, platform
import torch
from pathlib import Path
subprocess.run(["nvidia-smi"], check=True)
torch_before = {"python": platform.python_version(), "torch": str(torch.__version__),
                "cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available(),
                "gpu_count": torch.cuda.device_count(),
                "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}
print(json.dumps(torch_before, indent=2))
assert torch_before["cuda_available"] and torch_before["gpu_count"] == 2
assert all("T4" in name.split() for name in torch_before["gpu_names"])
```

## Cell 2 — clone the exact validation branch and read its published PREP pin

The final draft PR body contains `B1B_PREP_HEAD: <40-character SHA>` published after
commit. This external pin avoids a self-referential commit hash in its own runbook.
The cell reads that literal immutable SHA, rejects a moved PR head, and does not use
`main` or a moving branch as execution provenance. If the PR has changed, stop for
Research Lead review and an updated PREP pin; do not remove this assertion.

```python
import urllib.request, re, base64
from kaggle_secrets import UserSecretsClient
github_token = UserSecretsClient().get_secret("SAFESHIFT_GITHUB_TOKEN")
branch = "validation/d9-qwen-kaggle-smoke"
api = "https://api.github.com/repos/tantdna2/SafeShift/pulls?state=open&head=tantdna2:" + branch
github_request = urllib.request.Request(api, headers={"Authorization": "Bearer " + github_token,
                                                     "Accept": "application/vnd.github+json"})
with urllib.request.urlopen(github_request) as response:
    prs = json.load(response)
assert len(prs) == 1 and prs[0]["draft"], "Expected one draft PREP PR"
match = re.search(r"B1B_PREP_HEAD: ([0-9a-f]{40})", prs[0]["body"] or "")
assert match, "Published immutable PREP pin missing"
PREP_HEAD = match.group(1)
assert prs[0]["head"]["sha"] == PREP_HEAD, "PR moved since PREP publication"
# Temporary subprocess-only header; no token in URL, command arguments or disk config.
git_env = {**os.environ, "GIT_CONFIG_COUNT": "1", "GIT_TERMINAL_PROMPT": "0",
           "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
           "GIT_CONFIG_VALUE_0": "Authorization: Basic " + base64.b64encode(
               ("x-access-token:" + github_token).encode()).decode()}
try:
    subprocess.run(["git", "-c", "credential.helper=", "clone", "--branch", branch, "--single-branch",
                    "https://github.com/tantdna2/SafeShift.git", "SafeShift"], check=True, env=git_env)
finally:
    del github_token, github_request, git_env
os.chdir("SafeShift")
```

## Cell 3 — checkout exact B1B-PREP HEAD

```python
subprocess.run(["git", "checkout", "--detach", PREP_HEAD], check=True)
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == PREP_HEAD
assert not subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], text=True).strip()
subprocess.run(["git", "merge-base", "--is-ancestor",
                "bd18a64bc76653893abaf5d36a3d9d6dd2665073", PREP_HEAD], check=True)
print("B1B_PREP_HEAD:", PREP_HEAD)
```

## Cell 4 — install only smoke dependencies; preserve Kaggle torch/CUDA

Qwen3-VL requires Transformers >=4.57.0; this procedure targets **4.57.1** only.
The [versioned native Qwen3-VL documentation](https://huggingface.co/docs/transformers/v4.57.1/model_doc/qwen3_vl)
describes the runner's native processor/model route. The supporting versions below
are a compatible dependency candidate, not a frozen or GPU-validated environment.
Torch's installed distribution version is constrained so pip must fail rather than
replace it. No torch/torchvision/CUDA reinstall or flash-attn is requested. An existing
Kaggle torch/torchvision import mismatch is a runtime blocker to record, not permission
to repair the stack opportunistically. Subsequent commands use fresh child processes,
so notebook imports do not reuse a stale Transformers module after installation.

```python
import importlib.metadata
setup = Path("data/processed/runtime_validation/w2_qwen_kaggle_smoke_setup")
setup.mkdir(parents=True, exist_ok=False)
(setup / "torch_constraint.txt").write_text("torch==" + importlib.metadata.version("torch") + "\n")
(setup / "kaggle_before_install.json").write_text(json.dumps(torch_before, indent=2))
subprocess.run([sys.executable, "-m", "pip", "install", "--constraint", str(setup / "torch_constraint.txt"),
                "transformers==4.57.1", "accelerate==1.11.0", "huggingface_hub==0.36.0",
                "safetensors==0.6.2", "pillow==11.3.0"], check=True)
installed = json.loads(subprocess.check_output([sys.executable, "-c",
    "import torch,json,importlib.metadata as m; print(json.dumps({'torch':str(torch.__version__),"
    "'cuda':torch.version.cuda,'packages':{n:m.version(n) for n in "
    "['transformers','accelerate','huggingface_hub','safetensors','pillow']}}))"], text=True))
assert installed["torch"] == torch_before["torch"] and installed["cuda"] == torch_before["cuda"]
(setup / "installed_versions.json").write_text(json.dumps(installed, indent=2))
print(json.dumps(installed, indent=2))
```

## Cell 5 — provision exact snapshot (online, before runner execution)

[snapshot_download](https://huggingface.co/docs/huggingface_hub/package_reference/file_download)
uses the normal HF cache layout with exact repo/revision. The optional `--cache-dir`
must be under repository-relative `data/processed/`; set `HF_HUB_CACHE` to that same
directory in every later child process. These cells already do so. No `local_dir`
layout is used, and neither model factory runs during provisioning.

```python
os.environ["HF_HUB_CACHE"] = str(Path("data/processed/hf-cache").resolve())
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)
subprocess.run([sys.executable, "scripts/provision_qwen3vl_snapshot.py",
                "--cache-dir", "data/processed/hf-cache",
                "--report", str(setup / "provision_verification.json")], check=True)
```

The provisioner streams SHA-256 for all four shards and compares both hash and size
against `local_model_provenance.d9.json`. `LOCAL_WEIGHT_BYTES_VERIFIED=true` describes
only these local bytes. It does not rewrite documentary provenance or establish a
global freeze. Missing/mismatched files produce false, exit 1, and no model execution.

## Cell 6 — independent local-only hash verification

```python
subprocess.run([sys.executable, "scripts/provision_qwen3vl_snapshot.py", "--verify-only",
                "--cache-dir", "data/processed/hf-cache",
                "--report", str(setup / "local_weight_verification.json")], check=True)
verification = json.loads((setup / "local_weight_verification.json").read_text())
assert verification["LOCAL_WEIGHT_BYTES_VERIFIED"] is True
print("LOCAL_WEIGHT_BYTES_VERIFIED:", verification["LOCAL_WEIGHT_BYTES_VERIFIED"])
```

## Cell 7 — set offline mode before the smoke Python process starts

```python
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
print({k: os.environ[k] for k in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")})
```

Smoke additionally denies Python socket connections, resolves only the cached exact
snapshot, and hashes it again before runner initialization. The runner already passes
`local_files_only=True` to both factories. This checks ordinary Python/HF network
independence; it is not an OS-level sandbox for arbitrary native libraries. No download
occurs inside `execute_call()`.

## Cell 8 — run exactly two sequential calls

```python
from datetime import datetime, timezone
RUN_ID = "kaggle-t4x2-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
run_root = Path("data/processed/runtime_validation/w2_qwen_kaggle_smoke") / RUN_ID
completed = subprocess.run([sys.executable, "scripts/w2_qwen_kaggle_smoke.py", "--run-id", RUN_ID])
print("Smoke exit code:", completed.returncode, "Evidence:", run_root)
```

Do not rerun automatically. Every rerun needs a new ID, `--rerun-of PREVIOUS_ID` and
`--rerun-reason REASON`, retaining all previous evidence, including failed attempts.
The script refuses existing run directories and refuses an unlinked new attempt when
previous reports exist locally. Across fresh notebooks, the Owner must still supply
the previous ID/reason. Research Lead review is required before any changed plan;
do not tune prompt, decoding, precision or placement after seeing outputs.

## Cell 9 — concise report summary

```python
report = json.loads((run_root / "runtime_report.json").read_text())
print(json.dumps({k: report[k] for k in
    ("run_id", "git_commit", "status", "blocker", "native_errors", "notes", "device_map")}, indent=2))
print(json.dumps(report["calls"], indent=2))
```

`RUNTIME_SMOKE_PASS` requires verified weight bytes, two T4s, exact model/revision,
one load lifecycle, two observable native generations with raw+metadata preserved,
cache/RoPE cleared after each independent request, no native exception/OOM and no disk
offload. `CLASSIFICATION_PARSE_INVALID` does **not** fail runtime or measure accuracy.
Only `INVALID_CLASSIFICATION_OUTPUT` is a nonblocking runtime note.
`PARSER_FAILURE`, including adapter exceptions or structural failures, is a smoke
runtime/integration blocker in the runner → raw envelope → adapter path, even when
native generation worked. It is not a model capability failure. PASS requires both
classification parse statuses to be `SUCCESS` or `INVALID`; `FAILED`, `UNSUPPORTED`
and `NOT_ATTEMPTED` cannot pass.
Load/generation/storage failures stop further calls. CPU offload is
`RUNTIME_NOTE_CPU_OFFLOAD` for Research Lead review. Both `cuda:0` and `cuda:1` are
the expected map; absence of either produces a separate review note rather than
claiming dual-GPU placement. No placement changes are made.

The harness instruments the existing runner's load method to inspect its actual model
and intercept native `generate` only to record the underlying exception type (including
OOM) before B1A converts it to `GenerationFailure`. The real runner alone invokes
generation; no parallel loader or direct inference path exists. Arbitrary exception
messages are excluded to avoid leaking paths/tokens. Error type, stage and original
runner code are retained; opaque native crashes cannot yield an invented exception.
Fatal process termination may prevent a final report: preserve the existing partial
raw files and Kaggle failure evidence, never infer PASS or rerun to hide that attempt.

The report includes config/prompt/image/source hashes, exact software and driver/GPU
identity, device map, pre/post-load and post-call free/total memory plus allocator
peaks, per-call IDs/statuses and SHA-256 of `response.raw` and pre-parse `metadata.json`.
Memory is diagnostic only; no throughput ranking. FileRawStore persists raw before
Qwen3VLAdapter. `result.json` is also retained locally after adaptation.

## Cell 10 — bundle only small evidence and download

```python
import zipfile
from IPython.display import FileLink, display
bundle = Path("data/processed/w2_qwen_kaggle_smoke_evidence.zip")
allowed = [run_root / "runtime_report.json", run_root / "environment_summary.json",
           run_root / "weight_verification.json", setup / "local_weight_verification.json",
           setup / "provision_verification.json", setup / "kaggle_before_install.json",
           setup / "installed_versions.json"]
for call in report["calls"]:
    for key in ("metadata", "raw_output"):
        if call[key]:
            path = Path(call[key]["path"])
            assert path.resolve().is_relative_to(run_root.resolve())
            assert path.name in {"metadata.json", "response.raw"}
            if path.stat().st_size <= 2 * 1024 * 1024:
                allowed.append(path)
            else:
                print("Oversized raw/metadata omitted; exact hash retained in report:", call[key])
with zipfile.ZipFile(bundle, "x", zipfile.ZIP_DEFLATED) as archive:
    for path in allowed:
        if path.exists():
            archive.write(path, path.relative_to("data/processed").as_posix())
display(FileLink(str(bundle)))
```

Download the displayed zip and send it to Research Lead. The explicit allowlist excludes
weights, cache, dataset, generated input images, secrets and arbitrary logs. Small raw
envelopes and metadata for both calls are preferred; omitted oversized artifacts retain
their exact hashes in the report. Nothing from the runtime is committed in PREP.
