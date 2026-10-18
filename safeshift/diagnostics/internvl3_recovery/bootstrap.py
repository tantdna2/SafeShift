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
BASE_SHA = "cb6ae2041e71c74fa1b4943e5986158f5e1b6d83"
REPO = "tantdna2/SafeShift"
HEAD_BRANCH = "fix/internvl3-cuda-recovery-20261017"
AUTHORITY_PATH = "configs/diagnostics/internvl3_recovery_authority.v1.json"
LOCK_PATH = "configs/diagnostics/internvl3_recovery_source.v1.json"
NOTEBOOK_PATH = "notebooks/SafeShift_InternVL3_RECOVERY_ONE_CLICK.ipynb"


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
                         headers={"Accept": "application/vnd.github+json", "User-Agent": "SafeShift-HNLO-probe"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.STDOUT).strip()


def verify_payload(repo, expected):
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
        target = repo / path
        if target.is_symlink() or not target.is_file():
            raise ValueError("SOURCE_ALIAS_OR_MISSING_FILE")
        data = target.read_bytes()
        if path == NOTEBOOK_PATH:
            data = notebook_bytes(data)
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("AUDITED_FILE_MISMATCH:" + path)
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("TRACKED_SOURCE_DRIFT")
    return lock


def verify_topology(repo, pr, expected):
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
    verify_payload(repo, expected)
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


def bootstrap(output=Path("/kaggle/working")):
    """One invocation; export an honest BLOCKED package even before trusted import."""
    from datetime import datetime, timezone
    import uuid
    output = Path(output)
    work = output / ("internvl3-recovery-session-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    work.mkdir(parents=True, exist_ok=False)
    try:
        import tempfile
        scratch = Path(tempfile.gettempdir()) / ("safeshift-" + work.name)
        if scratch.resolve().is_relative_to(output.resolve()):
            raise RuntimeError("SCRATCH_MUST_BE_OUTSIDE_KAGGLE_OUTPUT")
        scratch.mkdir(exist_ok=False)
        repo, source = fetch_source(scratch)
        sys.path.insert(0, str(repo))
        from safeshift.diagnostics.internvl3_recovery.orchestrate import run
        loaded_run = run
    except BaseException as error:
        # No downloaded module is needed to explain a failure of the trust root.
        result = {"result": "BLOCKED", "stage": "BOOTSTRAP", "error_type": type(error).__name__,
                  "reason": str(error), "gpu_executed": False, "HNLO_RESEARCH_VERIFIED": False,
                  "models": [{"model": name, "result": "BLOCKED", "environment": "NOT_RUN", "t1": "NOT_RUN",
                              "capture": "NOT_RUN", "alignment": "N/A", "technical_hnlo": "N/A",
                              "load_calls": 0, "generate_calls": 0} for name in ("internvl3",)]}
        stem = work.name
        data = (json.dumps(result, indent=2) + "\n").encode()
        (output / (stem + "_result.json")).write_bytes(data)
        failure = traceback.format_exc().encode()
        (work / "bootstrap-error.log").write_bytes(failure)
        report = "# SafeShift HNLO: BLOCKED\n\n" + type(error).__name__ + ": " + str(error) + "\n\n"
        report += "| Model | Environment | T1 | Capture | Alignment | Technical HNLO | Result |\n|---|---|---|---|---|---|---|\n"
        for row in result["models"]:
            report += "| " + row["model"] + " | NOT_RUN | NOT_RUN | NOT_RUN | N/A | N/A | BLOCKED |\n"
        report_data = report.encode("utf-8")
        (output / (stem + "_report.md")).write_bytes(report_data)
        inventory = {"files": [{"path": "bootstrap-error.log", "sha256": hashlib.sha256(failure).hexdigest(), "size_bytes": len(failure)},
                               {"path": "result.json", "sha256": hashlib.sha256(data).hexdigest(), "size_bytes": len(data)},
                               {"path": "report.md", "sha256": hashlib.sha256(report_data).hexdigest(), "size_bytes": len(report_data)}]}
        manifest = canonical(inventory)
        (output / (stem + "_manifest.json")).write_bytes(manifest)
        archive = output / (stem + ".tar.gz")
        with tarfile.open(archive, "x:gz") as stream:
            stream.add(work / "bootstrap-error.log", arcname="bootstrap-error.log")
            stream.add(output / (stem + "_result.json"), arcname="result.json")
            stream.add(output / (stem + "_report.md"), arcname="report.md")
            stream.add(output / (stem + "_manifest.json"), arcname="manifest.json")
        h = hashlib.sha256()
        with archive.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                h.update(block)
        (output / (stem + "_sha256.json")).write_text(json.dumps({"archive": archive.name, "sha256": h.hexdigest()}), encoding="utf-8")
        print(report)
        print("Evidence:", archive.name)
        return result
    # Runtime/export exceptions must never be relabeled "GPU not executed" by
    # the source-only bootstrap failure envelope.
    return loaded_run(repo, work, output, source)
