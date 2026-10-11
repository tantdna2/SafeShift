"""Prepare source once; restore existing trusted prep and run one offline child."""

import argparse
import os
import subprocess
from pathlib import Path

from safeshift.ls1.artifacts import digest, write_json
from safeshift.ls1.kaggle import (attached_path, verify_runtime_input, runtime_interpreter, restore_model)
from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
from . import access, preflight
from .journal import Journal, run_path


def bundle_source(repo, output):
    """Git bundle contains only committed history; no working data/credentials."""
    repo, output = Path(repo).absolute(), Path(output).absolute()
    sha = preflight.git(repo, "rev-parse", "HEAD").decode()
    proof = preflight.source(repo, sha)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "pa3_source.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(archive), "HEAD"], check=True)
    release = {"schema": "pa3-source-release-v1", "source_commit": sha,
               "bundle": archive.name, "bundle_sha256": digest(archive),
               "repository": "tantdna2/SafeShift", "files": proof["files"],
               "execution_authority": False}
    write_json(output / "pa3_source_release.json", release)
    return release


def launch(repo, inputs, settings):
    # Failure evidence is the only permitted write before authorization.
    root = run_path(repo, settings["run_id"])
    journal = Journal(root.parent / (root.name + "-launch"), create=True)
    stage = "AUTHORITY"
    try:
        access.require(settings["mode"], settings)
        access.require("technical", settings)
        stage = "A_SOURCE"
        journal.write("source", preflight.source(repo, settings["source_commit"]))
        stage = "B_PREP_INTEGRITY"
        runtime_input = attached_path(inputs, settings["runtime_input"])
        inventory = attached_path(inputs, settings["runtime_inventory_input"])
        proof = verify_runtime_input(runtime_input, inventory, settings["runtime_inventory_sha256"])
        journal.write("runtime_input", proof)
        model_input = attached_path(inputs, settings["model_input"])
        snapshot = restore_model(repo, model_input, "qwen2_5")
        site = attached_path(inputs, settings["runtime_site_packages"]) if settings.get("runtime_site_packages") else None
        if site and not site.resolve().is_relative_to(runtime_input.resolve()):
            raise ValueError("SITE_OUTSIDE_HASH_VERIFIED_RUNTIME")
        runtime = runtime_interpreter(repo, runtime_input, "qwen2_5", site)
        journal.write("runtime", {"software_versions": runtime["software_versions"],
                                  "inventory_sha256": settings["runtime_inventory_sha256"]})
        journal.write("settings", settings)  # all paths relative to the documented attachment/root
        env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0", "PYTHONPATH": str(repo),
               "PYTHONNOUSERSITE": "1"}
        if runtime["site_packages"]:
            env["PYTHONPATH"] += os.pathsep + runtime["site_packages"]
        env.pop("PYTHONHOME", None)
        stage = "C_TO_G_ONE_CHILD"
        child = subprocess.run([runtime["python"], "-s", "-m", "safeshift.pa3.native.workflow",
                                "--settings", str(journal.path("settings")), "--snapshot", str(snapshot),
                                "--inputs", str(inputs)],
                               cwd=repo, env=env, check=False)
        journal.write("child", {"returncode": child.returncode, "attempts": 1})
        if child.returncode:
            raise RuntimeError("PA3_CHILD_FAILED_NO_RETRY")
        journal.write("finish", {"status": "CHILD_COMPLETED", "execution_authority_from_checksums": False})
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__, "retry_permitted": False})
        raise
    finally:
        try:
            journal.seal()
        finally:
            journal.package()
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-source", action="store_true", required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    bundle_source(args.repo, args.output)


if __name__ == "__main__":
    main()
