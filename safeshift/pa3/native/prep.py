"""Explicit ONLINE owner preparation, separate from the OFFLINE inference notebook.

No action on import. CPU only: build/test a relocatable runtime OR download the
exact model snapshot without loading it. Never invokes inference or reads data.
"""
import argparse
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile

from safeshift.ls1.artifacts import digest, write_json
from safeshift.ls1.kaggle import inventory_runtime, runtime_interpreter, verify_runtime_input
from safeshift.ls1.tokenizer import plan, verify_snapshot
from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
from .journal import safe_relative

UV_VERSION = "0.6.14"
OFFLINE_SOURCE_COMMIT = "13ea2fba67f36883518db8a2add1b249c951e48e"
# preflight.source() byte-checks these paths. ONLINE prep may change only itself.
PREP_ONLY_EXECUTION_PATHS = frozenset({"safeshift/pa3/native/prep.py"})
RUNTIME_MODULES = ("torch", "torchvision", "transformers", "qwen_vl_utils", "accelerate",
                   "PIL", "huggingface_hub", "tokenizers", "safetensors")
# The OFFLINE inventory must live outside the archive's directory (ls1 rule).
ARCHIVE = "runtime-archive/pa3_runtime.tar.gz"
# Fixed restore location of the unchanged ls1.kaggle.runtime_interpreter; it
# extracts the archive's top-level "runtime/" under part-0.
CONSUMER_ROOT = "data/processed/ls1/runtime"
CONSUMER_RUNTIME = CONSUMER_ROOT + "/part-0/runtime"


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def prep_source_scope(repo, sha):
    """ONLINE prep source descends from OFFLINE source without altering its execution inputs."""
    if subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", OFFLINE_SOURCE_COMMIT, sha],
                      capture_output=True).returncode:
        raise ValueError("PREP_SOURCE_NOT_DESCENDANT_OF_OFFLINE_SOURCE")
    changed = git(repo, "diff", "--name-only", OFFLINE_SOURCE_COMMIT, sha).splitlines()
    protected = [p for p in changed if p not in PREP_ONLY_EXECUTION_PATHS and (
        p.startswith(("safeshift/", "configs/", "prompts/")) or p == "notebooks/pa3_qwen2_5_kaggle.ipynb")]
    if protected:
        raise ValueError("PREP_SOURCE_CHANGES_OFFLINE_EXECUTION_INPUTS:" + ",".join(protected))
    return changed


def bundle_prep_source(repo, output):
    """A separately audited ONLINE tool release; grants no execution rights."""
    repo, output = Path(repo).resolve(), Path(output).absolute()
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("COMMIT_PREP_SOURCE_FIRST")
    sha = git(repo, "rev-parse", "HEAD")
    changed = prep_source_scope(repo, sha)
    output.mkdir(parents=True, exist_ok=False)
    bundle = output / "pa3_prep_source.bundle"
    subprocess.run(["git", "-C", str(repo), "bundle", "create", str(bundle), "HEAD"], check=True)
    release = {"schema": "pa3-online-prep-source-v1", "prep_source_commit": sha,
               "offline_source_commit": OFFLINE_SOURCE_COMMIT,
               "changed_paths_since_offline_source": changed,
               "bundle": bundle.name, "bundle_sha256": digest(bundle),
               "repository": "tantdna2/SafeShift", "execution_authority": False}
    write_json(output / "pa3_prep_source_release.json", release)
    return release


def package_command(python, site, constraints, pins):
    """Install outside the managed interpreter's scheme (PEP 668 --target).

    Explicit official CUDA wheels keep other dependencies on PyPI; constraints
    still enforce every existing pin, including the CUDA local versions.
    """
    wheels = [name + " @ https://download.pytorch.org/whl/cu124/" + name + "-" +
              pins[name].replace("+", "%2B") + "-cp311-cp311-linux_x86_64.whl"
              for name in ("torch", "torchvision")]
    return [sys.executable, "-m", "uv", "pip", "install", "--python", str(python),
            "--target", str(site), "--no-config", "--no-cache", "--link-mode", "copy",
            "--only-binary", ":all:", "--index-url", "https://pypi.org/simple",
            "-c", str(constraints), *wheels,
            *(k + "==" + v for k, v in pins.items()
              if k not in {"python", "torch", "torchvision"})]


def check_links(root):
    root = Path(root).resolve()
    links = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            target = path.resolve(strict=True)
            if not target.is_relative_to(root):
                raise ValueError("PREP_LINK_ESCAPES_ROOT")
            links[path.relative_to(root).as_posix()] = target.relative_to(root).as_posix()
    return links


def probe_script(expected, modules=RUNTIME_MODULES):
    """Child-side checks; argv[1] is the runtime root. Each failure names its cause."""
    lines = [
        "import importlib, importlib.metadata as m, json, pathlib, platform, sys",
        "root = pathlib.Path(sys.argv[1]).resolve()",
        "inside = lambda p: pathlib.Path(p).resolve().is_relative_to(root)",
        "expected = " + repr(expected),
        "for name in " + repr(tuple(modules)) + ":",
        "    if not inside(importlib.import_module(name).__file__):",
        "        raise SystemExit('MODULE_OUTSIDE_RUNTIME:' + name)",
        "for name in expected:",
        "    if name != 'python' and not inside(m.distribution(name).locate_file('')):",
        "        raise SystemExit('METADATA_OUTSIDE_RUNTIME:' + name)",
        "actual = {k: platform.python_version() if k == 'python' else m.version(k) for k in expected}",
        "if actual != expected:",
        "    raise SystemExit('RUNTIME_VERSION_MISMATCH:' + json.dumps(actual, sort_keys=True))",
        "if not all(inside(p) for p in (sys.executable, sys.prefix, sys.base_prefix)):",
        "    raise SystemExit('INTERPRETER_OUTSIDE_RUNTIME')",
    ]
    if "torch" in modules:
        lines += ["import torch",
                  "from transformers import Qwen2_5_VLForConditionalGeneration",
                  "if torch.version.cuda != '12.4' or torch.cuda.is_initialized():",
                  "    raise SystemExit('TORCH_CUDA_BUILD_MISMATCH')"]
    lines.append("print(json.dumps(actual, sort_keys=True))")
    return "\n".join(lines)


def probe_runtime(repo, source, root, env, run):
    """Select with the unchanged OFFLINE selector, then prove every origin is inside root.

    source is a runtime directory or, for the OFFLINE consumer path, the archive
    that runtime_interpreter itself restores to CONSUMER_RUNTIME (= root).
    """
    selected = runtime_interpreter(repo, source, "qwen2_5")
    root = Path(root).resolve()
    if not (selected["site_packages"] and Path(selected["python"]).resolve().is_relative_to(root)
            and Path(selected["site_packages"]).resolve().is_relative_to(root)):
        raise ValueError("RUNTIME_NOT_SELECTED_INSIDE_ROOT")
    links = check_links(root)
    child_env = {k: v for k, v in env.items() if k not in ("PYTHONPATH", "PYTHONHOME")}
    child_env["PYTHONPATH"] = selected["site_packages"]
    run([selected["python"], "-B", "-s", "-c", probe_script(plan("qwen2_5", repo)["software"]),
         str(root)], child_env)
    # Host pip's documented --python runner also works when target has no pip.
    run([sys.executable, "-m", "pip", "--python", selected["python"], "check"], child_env)
    return selected, child_env, links


def probe_offline_child(repo, selected, env, run):
    """Import the OFFLINE child module with the launcher's PYTHONPATH and flags (CPU only)."""
    child_env = {k: v for k, v in env.items() if k != "PYTHONHOME"}
    child_env.update(OFFLINE_ENV, PYTHONNOUSERSITE="1",
                     PYTHONPATH=str(repo) + os.pathsep + selected["site_packages"])
    run([selected["python"], "-B", "-s", "-c", "import safeshift.pa3.native.workflow"], child_env)


def require_same(reference, links, observed, observed_links):
    if links != observed_links or reference["software_versions"] != observed["software_versions"]:
        raise ValueError("RUNTIME_ROUNDTRIP_CHANGED")


def commands(repo, root):
    pins = plan("qwen2_5", repo)["software"]
    uv = [sys.executable, "-m", "uv"]
    return [
        [sys.executable, "-m", "pip", "install", "uv==" + UV_VERSION],
        uv + ["python", "install", pins["python"], "--install-dir", str(root / "managed")],
    ]


def pack_tree(root, archive):
    """Preserve contained relative aliases so Python is unambiguous after restore."""
    root = Path(root).resolve()
    check_links(root)
    with tarfile.open(archive, "x:gz", dereference=False) as stream:
        for p in sorted(root.rglob("*")):
            if not p.resolve().is_relative_to(root):
                raise ValueError("PREP_LINK_ESCAPES_ROOT")
            name = "runtime/" + p.relative_to(root).as_posix()
            if p.is_symlink():
                member = stream.gettarinfo(str(p), arcname=name)
                member.linkname = os.path.relpath(p.resolve(), p.parent).replace(os.sep, "/")
                stream.addfile(member)
            elif p.is_file():
                stream.add(p, arcname=name, recursive=False)


def runtime(repo, output):
    if (platform.system(), platform.machine()) != ("Linux", "x86_64"):
        raise ValueError("PREP_REQUIRES_LINUX_X86_64")
    repo, output = Path(repo).absolute(), Path(output).absolute()
    consumer = repo / CONSUMER_ROOT
    if consumer.exists():
        raise FileExistsError("OFFLINE_CONSUMER_RESTORE_PATH_EXISTS")
    output.mkdir(parents=True, exist_ok=False)
    root = output / "build"
    root.mkdir()
    temporary = output / "install-temp"
    temporary.mkdir()
    free_at_start = shutil.disk_usage(output).free
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONNOUSERSITE": "1",
           "PYTHONDONTWRITEBYTECODE": "1",
           "UV_NO_CACHE": "1", "UV_PYTHON_BIN_DIR": str(root / "bin"),
           "TMPDIR": str(temporary)}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    log = []
    checks = {}

    def run(command, child_env=None):
        log.append([str(x) for x in command])
        subprocess.run(command, check=True, env=child_env or env)

    try:
        for command in commands(repo, root):
            run(command)
        interpreters = list((root / "managed").glob("*/bin/python3.11"))
        if len(interpreters) != 1:
            raise ValueError("EXACT_MANAGED_PYTHON_REQUIRED")
        # No ensurepip, marker deletion, system install or bare venv archive.
        payload = root / "payload"
        payload.mkdir()
        shutil.move(str(interpreters[0].parent.parent), payload / "python")
        python = payload / "python/bin/python3.11"
        site = payload / "packages/site-packages"
        pins = plan("qwen2_5", repo)["software"]
        constraints = output / "constraints.txt"
        constraints.write_text("\n".join(k + "==" + v for k, v in pins.items() if k != "python") + "\n")
        run(package_command(python, site, constraints, pins))
        # Console scripts embed install-time shebangs. They are not part of the
        # library-only OFFLINE contract; retain separately, never ship them.
        scripts = site / "bin"
        if scripts.exists():
            shutil.move(str(scripts), output / "excluded-console-scripts")
        relocated = output / "relocated"
        shutil.move(str(payload), relocated)
        selected, selected_env, links = probe_runtime(repo, relocated, relocated, env, run)
        checks["1_relocated_tree_before_archive"] = "PASS"
        # Not processed from PYTHONPATH; the imports above prove none is needed.
        pth = sorted(p.name for p in Path(selected["site_packages"]).glob("*.pth"))
        freeze_command = [sys.executable, "-m", "pip", "--python", selected["python"],
                          "freeze", "--all", "--path", selected["site_packages"]]
        log.append(freeze_command)
        freeze = subprocess.check_output(freeze_command, env=selected_env)
        (output / "resolved-requirements.txt").write_bytes(freeze)
        archive = output / ARCHIVE
        archive.parent.mkdir()
        pack_tree(relocated, archive)
        checks["2_archive_created"] = "PASS"
        # Delete every built tree: no earlier path or file can mask a broken archive.
        shutil.rmtree(relocated)
        shutil.rmtree(root)
        from safeshift.runners.p21_kaggle import safe_extract
        restored = safe_extract(archive, output / "archive-roundtrip") / "runtime"
        checked, _, restored_links = probe_runtime(repo, restored, restored, env, run)
        require_same(selected, links, checked, restored_links)
        checks["3_strict_extract_new_path"] = "PASS"
        shutil.rmtree(restored.parent)
        # The OFFLINE launcher's own path: trusted inventory, then archive selection.
        inventory = output / "pa3_runtime_inventory.json"
        inventory_sha = inventory_runtime(archive, inventory)
        verify_runtime_input(archive, inventory, inventory_sha)
        consumed, _, consumed_links = probe_runtime(repo, archive, repo / CONSUMER_RUNTIME, env, run)
        require_same(selected, links, consumed, consumed_links)
        probe_offline_child(repo, consumed, env, run)
        checks["4_offline_runtime_interpreter_from_archive"] = "PASS"
        shutil.rmtree(consumer)
        write_json(output / "runtime_prep.json", {"status": "CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN",
            "checks": checks, "software": selected["software_versions"], "uv": UV_VERSION,
            "layout": "standalone-python-plus-explicit-target-site-packages-v1",
            "symlinks": links, "console_scripts": "EXCLUDED_LIBRARY_ONLY_RUNTIME",
            "pth_files_not_processed_on_pythonpath": pth,
            "prep_source_commit": git(repo, "rev-parse", "HEAD"),
            "prep_module_sha256": digest(Path(__file__)),
            "prep_tracked_dirty": bool(git(repo, "status", "--porcelain", "--untracked-files=no")),
            "offline_source_commit": OFFLINE_SOURCE_COMMIT,
            "archive": ARCHIVE, "archive_sha256": digest(archive),
            "inventory": inventory.name, "inventory_sha256": inventory_sha,
            "free_bytes_at_start": free_at_start,
            "resolved_requirements_sha256": digest(output / "resolved-requirements.txt"),
            "transitive_versions": "CAPTURED_IN_RESOLVED_REQUIREMENTS_NOT_PROSPECTIVELY_LOCKED"})
    finally:
        # Relative commands in exported provenance (no personal absolute paths).
        write_json(output / "commands.json", [[s.replace(sys.executable, "<prep-host-python>")
            .replace(str(output), "<prep>").replace(str(repo), "<repo>") for s in c] for c in log])


def model(repo, output):
    """Download only pinned filenames; hash every file; never load model/tokenizer."""
    from huggingface_hub import snapshot_download
    output.mkdir(parents=True, exist_ok=False)
    config = plan("qwen2_5", repo)
    required = 2 * sum(f["size_bytes"] for f in config["snapshot_files"]) + 2**30
    if shutil.disk_usage(output).free < required:
        raise OSError("MODEL_PREP_DISK_NEEDS_CACHE_PLUS_ARCHIVE_PLUS_1_GIB:" + str(required))
    downloaded = Path(snapshot_download(repo_id=config["model_id"], revision=config["model_revision"],
        cache_dir=str(output / "cache"), allow_patterns=[f["path"] for f in config["snapshot_files"]]))
    proof = verify_snapshot("qwen2_5", downloaded, repo=repo)
    archive = output / "pa3_model.tar.gz"
    with tarfile.open(archive, "x:gz", dereference=True) as stream:
        for row in config["snapshot_files"]:
            stream.add(downloaded / row["path"], arcname=config["model_revision"] + "/" + row["path"], recursive=False)
    write_json(output / "model_prep.json", {"snapshot": proof, "archive_sha256": digest(archive),
        "snapshot_bytes": sum(f["size_bytes"] for f in config["snapshot_files"]),
        "model_load": "NOT_RUN"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("runtime", "model", "bundle-source"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--execute-online-owner-prep", action="store_true", required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    relative = safe_relative(args.output)
    if not relative.startswith("data/processed/"):
        raise ValueError("PREP_OUTPUT_MUST_BE_UNDER_DATA_PROCESSED")
    output = repo / relative
    if output.resolve() != output.absolute():
        raise ValueError("PREP_OUTPUT_ALIAS")
    if args.kind != "bundle-source":
        # Never build inputs from a source that alters OFFLINE execution inputs.
        prep_source_scope(repo, git(repo, "rev-parse", "HEAD"))
    {"runtime": runtime, "model": model, "bundle-source": bundle_prep_source}[args.kind](repo, output)


if __name__ == "__main__":
    main()
