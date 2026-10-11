"""Read-only source and offline runtime verification; never installs anything."""

import hashlib
import platform
import re
import subprocess
from pathlib import Path

from safeshift.ls1.tokenizer import plan, versions, verify_snapshot, t1
from safeshift.protocol.classification_policy import render_prompt, load_policy
from ..artifacts import receipt

BASE_SHA = "540078902370c88aede1d6c30be73f29fce6722e"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).strip()


def source(repo, expected):
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("REVIEWED_SOURCE_SHA_REQUIRED")
    if git(repo, "rev-parse", "HEAD").decode() != expected:
        raise ValueError("SOURCE_COMMIT_MISMATCH")
    git(repo, "merge-base", "--is-ancestor", BASE_SHA, expected)
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("DIRTY_TRACKED_SOURCE")
    # Check committed bytes, not just the index/mtime, and reject import shadows.
    paths = git(repo, "ls-tree", "-r", "--name-only", expected).decode().splitlines()
    paths = [p for p in paths if p.startswith(("safeshift/", "configs/", "prompts/"))
             or p == "notebooks/pa3_qwen2_5_kaggle.ipynb"]
    observed = {}
    for name in paths:
        path = Path(repo) / name
        if path.is_symlink() or path.resolve() != path.absolute():
            raise ValueError("SOURCE_ALIAS")
        data = path.read_bytes()
        if data != git_blob(repo, expected, name):
            raise ValueError("SOURCE_BYTE_MISMATCH:" + name)
        observed[name] = receipt(data)
    tracked = set(paths)
    for top in ("safeshift", "configs", "prompts"):
        for p in (Path(repo) / top).rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts and p.relative_to(repo).as_posix() not in tracked:
                raise ValueError("UNTRACKED_EXECUTION_INPUT")
    render_prompt("qwen2_5", repo=repo)
    plan("qwen2_5", repo)
    return {"source_commit": expected, "base_sha": BASE_SHA, "files": observed}


def git_blob(repo, commit, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", commit + ":" + path])


def runtime(repo, snapshot):
    expected = plan("qwen2_5", repo)["software"]
    actual = versions(expected)
    if actual != expected or (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise ValueError("EXACT_RUNTIME_REQUIRED_NO_FALLBACK")
    snapshot_proof = verify_snapshot("qwen2_5", snapshot, repo=repo)
    # Extra loader-visible files can change HF behavior despite matching pins.
    allowed = {r["path"] for r in plan("qwen2_5", repo)["snapshot_files"]}
    if {p.name for p in Path(snapshot).iterdir()} != allowed:
        raise ValueError("SNAPSHOT_EXTRA_FILES")
    return {"software": actual, "platform": "Linux_x86_64", "snapshot": snapshot_proof,
            "condition": load_policy(repo)["classification"]["qwen2_5"]}


def tokenizer_check(repo, snapshot):
    evidence, tokenizer = t1("qwen2_5", snapshot, repo=repo)
    if evidence["status"] == "PASS" and len(evidence.get("checks", [])) != 28:
        raise ValueError("EXACT_28_T1_VARIANTS_REQUIRED")
    return evidence, tokenizer
