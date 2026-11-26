"""Explicit SYNTHETIC operations rehearsal; no images, predictions or Kaggle API."""
import argparse
import json
from pathlib import Path
import subprocess
import zipfile

from safeshift.kaggle_handoff import SCHEMA, Session, prepare, operate
from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, export, verify_archive
from safeshift.pilot.contract import digest


class SyntheticOperator:
    def __init__(self, root):
        self.root = Path(root)

    def preflight(self, request):
        require(request["scope"] == "SYNTHETIC_ONLY", "SYNTHETIC_ONLY")

    def submit(self, request):
        # Exclusive local marker makes the simulation reject duplicate submission.
        write(self.root / "synthetic-submitted.json", {"binding": digest(request)})
        return {"job_id": request["job"], "version": request["version"]}

    def identity(self, request):
        return {"job_id": request["job"], "version": request["version"],
            "notebook_sha256": request["notebook_sha256"]}

    def status(self, request):
        return read(sorted(self.root.glob("synthetic-provider-*.json"))[-1])["state"]

    def download(self, request, destination):
        evidence = destination / "evidence"
        evidence.mkdir()
        write(evidence / "operation.json", {"notice": "SYNTHETIC OPERATIONS ONLY - NOT A RESEARCH RESULT",
            "binding": digest(request), "model_calls": 0, "dataset_accessed": False,
            "commit_sha": request["commit_sha"], "runtime_commit": request["runtime_commit"],
            "notebook_sha256": request["notebook_sha256"], "state": self.status(request)})
        (evidence / "worker.log").write_text("SYNTHETIC no worker/model executed\n", encoding="utf8")
        export(evidence, destination / "synthetic.zip")

    def verify(self, request, destination, state):
        archive = destination / "synthetic.zip"
        require(sha(archive) == read(str(archive) + ".sha256.json")["sha256"], "SIDECAR_SHA256")
        members = verify_archive(archive)
        with zipfile.ZipFile(archive) as z:
            require(z.testzip() is None, "CRC")
            row = json.loads(z.read("operation.json"))
        require(row["binding"] == digest(request) and row["model_calls"] == 0
            and row["dataset_accessed"] is False and row["state"] == state
            and all(row[k] == request[k] for k in ("commit_sha", "runtime_commit", "notebook_sha256")),
            "SYNTHETIC_RECEIPT_BINDINGS")
        return {"status": "PASS" if state == "COMPLETE" else "FAIL", "scope": "SYNTHETIC_ONLY",
            "archive_sha256": sha(archive), "members": len(members) + 1, "model_calls": 0,
            "sha256": "PASS", "crc": "PASS", "bindings": "PASS", "scientific_qualified": False}


def request(handoff_id):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"schema": SCHEMA, "handoff_id": handoff_id, "scope": "SYNTHETIC_ONLY",
        "job": "synthetic/never-submitted-to-kaggle", "version": 1,
        "commit_sha": head, "runtime_commit": head, "notebook": "scripts/rehearse_kaggle_handoff.py",
        "notebook_sha256": sha(ROOT / "scripts/rehearse_kaggle_handoff.py"),
        "bindings": {key: {"scope": "SYNTHETIC_ONLY"} for key in
            ("dataset", "checkpoint", "source", "runtime", "rights", "scientific_method")},
        "limits": {"monitor_seconds": 1, "max_calls": 0, "job_seconds": 1},
        "coordinator_required": False, "execution_release": None,
        "plan": {"scope": "SYNTHETIC_ONLY", "model_calls": 0},
        "plan_sha256": digest({"scope": "SYNTHETIC_ONLY", "model_calls": 0})}


def advance(root, state):
    require(state in ("RUNNING", "COMPLETE", "ERROR", "UNKNOWN"), "SYNTHETIC_PROVIDER_STATE")
    root = Session(root).root
    entries = list(root.glob("synthetic-provider-*.json"))
    write(root / f"synthetic-provider-{len(entries)+1:05d}.json", {"state": state})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("prepare", "advance", "step"))
    p.add_argument("--directory", required=True, type=Path)
    p.add_argument("--state", choices=("RUNNING", "COMPLETE", "ERROR", "UNKNOWN"))
    p.add_argument("--action", choices=("start", "collect"))
    a = p.parse_args(argv)
    if a.command == "prepare":
        prepare(a.directory, request(a.directory.name))
        advance(a.directory, "RUNNING")
        result = {"status": "PREPARED", "scope": "SYNTHETIC_ONLY"}
    elif a.command == "advance":
        advance(a.directory, a.state)
        result = {"status": a.state, "scope": "SYNTHETIC_ONLY"}
    else:
        result = operate(Session(a.directory), SyntheticOperator(a.directory), a.action)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
