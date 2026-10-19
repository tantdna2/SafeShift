"""Notebook trust root. Stdlib only; copied verbatim into its single code cell."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import traceback
from urllib.request import Request as URLRequest, urlopen

PAYLOAD_SHA256 = "0000000000000000000000000000000000000000000000000000000000000000"
BASE_SHA = "7dd96e083a8d409355062e6087624e306e4a5b2c"
REPO = "tantdna2/SafeShift"
HEAD_BRANCH = "prep/hnlo-train-v4-gpu-monitor-20261020"
AUTHORITY_PATH = "configs/diagnostics/hnlo_train_authority.v4.json"
LOCK_PATH = "configs/diagnostics/hnlo_train_source.v4.json"
NOTEBOOK_PATHS = tuple(f"notebooks/SafeShift_HNLO_TRAIN_{m}_SHARD{s}_V4.ipynb" for m in ("qwen3", "internvl3") for s in range(4))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def notebook_bytes(data):
    notebook = json.loads(data)
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            code = "".join(cell["source"])
            code = re.sub(r'PAYLOAD_SHA256 = "[0-9a-f]{64}"', 'PAYLOAD_SHA256 = "' + "0" * 64 + '"', code)
            cell["source"] = code.splitlines(keepends=True)
    return canonical(notebook)


def api(path):
    request = URLRequest("https://api.github.com/repos/" + REPO + "/" + path,
                         headers={"Accept": "application/vnd.github+json", "User-Agent": "SafeShift-HNLO-TRAIN-PREP"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT).strip()


def verify_payload(repo, expected, *, worker=False):
    lock_bytes = (repo / LOCK_PATH).read_bytes()
    lock = json.loads(lock_bytes)
    if hashlib.sha256(canonical(lock)).hexdigest() != expected:
        raise ValueError("AUDITED_SOURCE_PAYLOAD_MISMATCH")
    if lock["schema"] != "hnlo-source-lock-v1" or lock["base_sha"] != BASE_SHA:
        raise ValueError("AUDITED_SOURCE_SCHEMA_MISMATCH")
    names = git(repo, "ls-files", "-z").rstrip("\0").split("\0")
    if set(names) != {r["path"] for r in lock["files"]} | {AUTHORITY_PATH, LOCK_PATH}:
        raise ValueError("SOURCE_INVENTORY_MISMATCH")
    for row in lock["files"]:
        path = row["path"]
        if path.startswith("/") or ".." in path.split("/") or "\\" in path or ":" in path:
            raise ValueError("UNSAFE_SOURCE_PATH")
        # Parent verifies the complete tree. Inference must not even hash-read
        # label-bearing full/cohort manifests or historical result documents.
        # Recheck all executable Python and configuration/prompt dependencies;
        # immutable Git topology + prior parent proof bind the other tracked bytes.
        if worker and not (path.endswith(".py") or path.startswith(("configs/", "prompts/"))):
            continue
        target = repo / path
        if target.is_symlink() or not target.is_file():
            raise ValueError("SOURCE_ALIAS_OR_MISSING_FILE")
        data = target.read_bytes()
        if path in NOTEBOOK_PATHS:
            data = notebook_bytes(data)
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("AUDITED_FILE_MISMATCH:" + path)
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("TRACKED_SOURCE_DRIFT")
    return lock


def verify_topology(repo, pr, expected, *, worker=False):
    if not pr.get("merged_at") or pr.get("draft") or pr["base"]["ref"] != "main":
        raise PermissionError("MERGED_REVIEWED_RELEASE_REQUIRED")
    if pr["head"]["ref"] != HEAD_BRANCH or pr["head"]["repo"]["full_name"] != REPO:
        raise PermissionError("WRONG_RELEASE_PR")
    merge = pr["merge_commit_sha"]
    if not re.fullmatch("[0-9a-f]{40}", merge):
        raise ValueError("IMMUTABLE_MERGE_REQUIRED")
    parents = git(repo, "show", "-s", "--format=%P", merge).split()
    if len(parents) != 2 or parents[0] != BASE_SHA or parents[1] != pr["head"]["sha"]:
        raise PermissionError("STANDARD_MERGE_EXACT_BASE_AND_HEAD_REQUIRED")
    final = parents[1]
    implementation_parents = git(repo, "show", "-s", "--format=%P", final).split()
    if len(implementation_parents) != 1:
        raise PermissionError("AUTHORITY_ONLY_CHILD_REQUIRED")
    implementation = implementation_parents[0]
    if git(repo, "show", "-s", "--format=%P", implementation) != BASE_SHA:
        raise PermissionError("SINGLE_REVIEWED_IMPLEMENTATION_COMMIT_REQUIRED")
    if git(repo, "diff", "--name-only", implementation, final) != AUTHORITY_PATH:
        raise PermissionError("AUTHORITY_ONLY_CHILD_REQUIRED")
    if git(repo, "rev-parse", merge + "^{tree}") != git(repo, "rev-parse", final + "^{tree}"):
        raise PermissionError("MERGE_TREE_CHANGED")
    # Discovery through main never selects executable bytes from its current HEAD.
    git(repo, "merge-base", "--is-ancestor", merge, "origin/main")
    if git(repo, "rev-parse", "HEAD") != merge:
        raise PermissionError("EXACT_RELEASE_CHECKOUT_REQUIRED")
    prior = json.loads(git(repo, "show", implementation + ":" + AUTHORITY_PATH))
    now = json.loads((repo / AUTHORITY_PATH).read_bytes())
    if prior.get("grant") is not None or {**now, "grant": None} != prior:
        raise PermissionError("IMMUTABLE_AUTHORITY_CONTRACT_REQUIRED")
    verify_payload(repo, expected, worker=worker)
    return {"merge_commit": merge, "authority_commit": final, "implementation_commit": implementation,
            "payload_sha256": expected, "pr_url": pr["html_url"], "pr_number": pr["number"], "github_pr": pr}


def fetch_source(work):
    # A fixed PR branch is discovery only. Every executed tracked byte is locked.
    matches = api("pulls?state=all&base=main&head=tantdna2:" + HEAD_BRANCH + "&per_page=100")
    if len(matches) != 1:
        raise PermissionError("EXACTLY_ONE_REVIEWED_RELEASE_PR_REQUIRED")
    pr = api("pulls/" + str(matches[0]["number"]))
    if not pr.get("merged_at"):
        raise PermissionError("DRAFT_OR_UNMERGED_SOURCE_NO_EXECUTION")
    repo = work / "source"
    subprocess.run(["git", "clone", "--no-checkout", "https://github.com/" + REPO + ".git", str(repo)],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    git(repo, "checkout", "--detach", pr["merge_commit_sha"])
    return repo, verify_topology(repo, pr, PAYLOAD_SHA256)


def bootstrap(model, shard, output=Path("/kaggle/working")):
    """Discover the reviewed release without Owner code, SHA or path edits."""
    from datetime import datetime, timezone
    import tempfile
    import uuid
    output = Path(output)
    stem = f"hnlo-train-{model}-s{shard}-session-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    work = output / "data/processed/hnlo_train" / stem
    work.mkdir(parents=True, exist_ok=False)
    try:
        scratch = Path(tempfile.gettempdir()) / ("safeshift-" + stem)
        if scratch.resolve().is_relative_to(output.resolve()):
            raise RuntimeError("SCRATCH_MUST_BE_OUTSIDE_OUTPUT")
        scratch.mkdir(exist_ok=False)
        repo, source = fetch_source(scratch)
        sys.path.insert(0, str(repo))
        from safeshift.diagnostics.hnlo_train.orchestrate import run
    except BaseException as error:
        result = {"result": "BLOCKED", "stage": "BOOTSTRAP", "full_vocab_replay": False,
                  "planned": (941, 941, 941, 940)[shard],
                  "sample_journal": [{"ordinal": i, "status": "NOT_ATTEMPTED"} for i in range((941, 941, 941, 940)[shard])], "HNLO_RESEARCH_VERIFIED": False, "TECHNICAL_HNLO_VALID": False,
                  "gpu_initialization_attempted": False, "load_calls": 0, "generate_calls": 0,
                  "error": {"type": type(error).__name__, "reason": str(error)[:512], "errno": getattr(error, "errno", None)}}
        data = (json.dumps(result, indent=2) + "\n").encode()
        (output / (stem + "_result.json")).write_bytes(data)
        path = work / "result.json"
        path.write_bytes(data)
        manifest = canonical({"files": [{"path": "result.json", "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)}]})
        manifest_path = work / "manifest.json"
        manifest_path.write_bytes(manifest)
        (output / (stem + "_manifest.json")).write_bytes(manifest)
        archive = output / (stem + ".tar.gz")
        with tarfile.open(archive, "x:gz") as stream:
            stream.add(path, arcname="result.json", recursive=False)
            stream.add(manifest_path, arcname="manifest.json", recursive=False)
        (output / (stem + "_sha256.json")).write_text(json.dumps({"archive": archive.name,
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(), "status": "BOOTSTRAP_BLOCKED"}), encoding="utf-8")
        receipt = output / (stem + "_export.json")
        receipt.write_text(json.dumps({"status": "EXPORTED_BOOTSTRAP_BLOCKED", "archive": archive.name,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
            "result_sha256": hashlib.sha256(data).hexdigest()}), encoding="utf-8")
        (output / (stem + "_export_sha256.json")).write_text(json.dumps({
            "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}), encoding="utf-8")
        print("BLOCKED before trusted diagnostics:", type(error).__name__)
        return result
    return run(repo, work, output, source, model, shard)
