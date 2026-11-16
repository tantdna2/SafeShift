"""Released Owner UI and isolated child entrypoints, using PR195's pipeline."""
import argparse
import os
from pathlib import Path

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, write, safe, sha
from safeshift.pilot.contract import digest
from . import minicpm_release as authority, minicpm_ui as ui

MARKER = "safeshift_minicpm_release_ticket.json"


def metadata(path, limit=64 * 2**20):
    require(snapshot_stat(path).st_size <= limit, "MINICPM_CONTEXT_METADATA_BOUND")
    return read(path)


def run_capsule(inputs, capsule_sha256, locator, *, repo=ROOT):
    # Genuine authority before any Input path, request, credentials or model IO.
    grant = authority.load(locator, repo=repo)
    marker = discover(inputs, MARKER, limit=128)
    require(hasattr(os, "statvfs") and os.statvfs(marker.parent).f_flag & os.ST_RDONLY,
        "MINICPM_CAPSULE_READ_ONLY")
    envelope = metadata(marker, 128 * 2**20)
    value_marker = safe(marker.parent, ui.MARKER)
    require(sha(value_marker) == capsule_sha256, "MINICPM_RELEASE_CAPSULE_PIN")
    authority.verify_ticket(grant, envelope, metadata(value_marker))
    value = ui.verify_capsule(marker.parent, capsule_sha256, repo, release_ticket=True)
    owner, slug, _ = value["capsule_ref"].split("/")
    require(marker.parent.relative_to(Path(inputs)).as_posix() in (slug, "datasets/" + owner + "/" + slug),
        "MINICPM_V2_CAPSULE_MOUNT")
    with authority._activated(grant, locator, envelope, value, "launch", repo=repo) as context:
        request = value["request"]
        work, scratch = Path(request["work"]), Path(request["scratch"])
        require(not work.exists() and not scratch.exists(), "MINICPM_V2_FRESH_VM_WORKSPACE")
        ui.restore_history(marker.parent, value, work)
        work.mkdir(parents=True, exist_ok=True)
        scratch.mkdir(parents=True, exist_ok=False)
        context_file = work.parent / (request["plan"]["run_id"] + "-release-context.json")
        write(context_file, {"locator": locator, "ticket": envelope, "value": value})
        context["context_file"] = str(context_file)
        from .runtime import launch
        return launch(request, repo=repo)


def child_command(python, mode, request_file, repo, output, deadline):
    c = authority.current()
    require(c is not None and "context_file" in c, "MINICPM_SUPERVISED_CAPABILITY_CONTEXT")
    return [str(python), "-B", "-m", "safeshift.fulltrain.minicpm_execution", "--stage", mode,
        "--request", str(request_file), "--repo", str(repo), "--output", str(output), "--deadline", str(deadline),
        "--capability", c["context_file"], "--release-comment-id", str(c["locator"]["comment_id"]),
        "--release-body-sha256", c["locator"]["body_sha256"]]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stage", choices=authority.STAGES[1:], required=True)
    for name in ("request", "repo", "output", "capability"):
        p.add_argument("--" + name, required=True, type=Path)
    p.add_argument("--deadline", type=float, required=True)
    p.add_argument("--release-comment-id", type=int, required=True)
    p.add_argument("--release-body-sha256", required=True)
    args = p.parse_args()
    locator = {"comment_id": args.release_comment_id, "body_sha256": args.release_body_sha256}
    # The signed operator ticket delegates the already independently validated
    # decisions; a child still revalidates current Owner record and merged PR.
    grant = authority.load(locator, repo=args.repo, approvals=False)
    context = metadata(args.capability)
    require(set(context) == {"locator", "ticket", "value"} and context["locator"] == locator, "MINICPM_CHILD_CONTEXT")
    with authority._activated(grant, locator, context["ticket"], context["value"], args.stage, repo=args.repo, child=True):
        request = metadata(args.request, 4 * 2**20)
        authority.authorize(request=request)
        require(digest(request) == digest(context["value"]["request"]), "MINICPM_CHILD_REQUEST_PIN")
        from .admission import stage
        return stage(args.stage, request, args.repo, args.output, args.deadline)


if __name__ == "__main__":
    main()
