"""Offline Add Input restoration and one-shot LS1 child; no pip or downloads."""

import argparse
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

from safeshift.protocol.schema import strict_json
from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
from safeshift.runners.p21_kaggle import safe_extract
from .artifacts import digest, write_json
from .experiment import authorize
from .tokenizer import MODELS, plan, verify_snapshot


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def bundle_source(repo, output):
    """Export committed tracked code only. Owner builds after reviewing Draft HEAD."""
    repo, output = Path(repo), Path(output)
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("COMMIT_SOURCE_FIRST")
    sha = git(repo, "rev-parse", "HEAD")
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "ls1_source.tar"
    subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", "--output=" + str(archive.absolute()), sha], check=True)
    write_json(output / "ls1_source_release.json", {"schema": "ls1-source-release-v1", "source_commit": sha,
        "archive": archive.name, "archive_sha256": digest(archive), "repository": "tantdna2/SafeShift"})


def attached_path(inputs, value):
    rel = PurePosixPath(value)
    if not value or rel.is_absolute() or ".." in rel.parts or "\\" in value or ":" in value:
        raise ValueError("INPUT_RELATIVE_PATH_REQUIRED")
    root = Path(inputs).resolve()
    path = root / rel
    if not path.resolve().is_relative_to(root) or not path.exists():
        raise ValueError("ATTACHMENT_MISSING_OR_OUTSIDE_INPUTS")
    return path


def select_input(inputs, explicit, words):
    if explicit:
        return attached_path(inputs, explicit)
    candidates = [p for p in Path(inputs).iterdir() if p.is_dir() and all(w in p.name.lower() for w in words)]
    if len(candidates) != 1:
        raise ValueError("ATTACHMENT_AMBIGUOUS_SET_ONE_INPUT_PATH:" + "-".join(words))
    return candidates[0]


def restore_model(repo, source, model_key):
    revision = MODELS[model_key][1]
    candidates = [source] if source.name == revision else list(source.rglob(revision)) if source.is_dir() else []
    candidates = [p for p in candidates if p.is_dir() and (p / "tokenizer.json").is_file()]
    if len(candidates) > 1:
        raise ValueError("AMBIGUOUS_MODEL_SNAPSHOT")
    if candidates:
        verify_snapshot(model_key, candidates[0], repo=repo)
        return candidates[0]
    archives = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.name.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz")))
    expected = {f["path"] for f in plan(model_key, repo)["snapshot_files"]}
    found = []
    for archive in archives:
        with tarfile.open(archive, "r:*") as stream:
            entries = {}
            for item in stream:
                parts = PurePosixPath(item.name).parts
                if revision in parts:
                    index = parts.index(revision)
                    suffix = "/".join(parts[index + 1:])
                    if suffix in expected:
                        if not item.isfile() or item.name in entries or ".." in parts or item.name.startswith("/") or "\\" in item.name:
                            raise ValueError("UNSAFE_MODEL_ARCHIVE_MEMBER")
                        if suffix in entries:
                            raise ValueError("DUPLICATE_MODEL_FILE")
                        entries[suffix] = item
            if set(entries) == expected:
                found.append((archive, entries))
    if len(found) != 1:
        raise ValueError("EXACT_REUSABLE_MODEL_PREP_REQUIRED_NO_DOWNLOAD")
    archive, entries = found[0]
    target = Path(repo) / "data/processed/ls1/model" / revision
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(archive, "r:*") as stream:
        for name, item in entries.items():
            reader = stream.extractfile(item)
            if reader is None:
                raise ValueError("MODEL_ARCHIVE_UNREADABLE")
            with reader, (target / name).open("xb") as out:
                while block := reader.read(8 * 1024 * 1024):
                    out.write(block)
    verify_snapshot(model_key, target, repo=repo)
    return target


def runtime_interpreter(repo, source, model_key, site_packages=None):
    expected = plan(model_key, repo)["software"]
    probe = ("import importlib.metadata as m,json,platform; expected=" + repr(expected) +
        "; actual={k:platform.python_version() if k=='python' else m.version(k) for k in expected};" +
        "print(json.dumps(actual)); raise SystemExit(0 if actual==expected else 2)")
    env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0"}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    def select(root):
        paths = [root] if root.is_file() else sorted(p for p in root.rglob("python*")
            if p.name in ("python", "python3", "python3.11") and p.parent.name == "bin" and p.is_file())
        sites = [site_packages] if site_packages else [None] + (sorted(root.rglob("site-packages")) if root.is_dir() else [])
        matched = {}
        for python in paths:
            for site in sites:
                child_env = dict(env)
                if site:
                    child_env["PYTHONPATH"] = str(site)
                try:
                    result = subprocess.run([str(python), "-c", probe], env=child_env,
                                            capture_output=True, text=True, timeout=60)
                except (OSError, subprocess.TimeoutExpired):
                    continue
                if result.returncode == 0:
                    key = (python.resolve(), Path(site).resolve() if site else None)
                    matched.setdefault(key, {"python": str(python), "site_packages": str(site) if site else None,
                                             "software_versions": strict_json(result.stdout)})
        direct = [v for v in matched.values() if v["site_packages"] is None]
        if len(direct) == 1:
            return direct[0]
        if len(matched) > 1:
            raise ValueError("AMBIGUOUS_EXACT_RUNTIME_SET_INTERPRETER_OR_SITE_PATH")
        return next(iter(matched.values()), None)

    selected = select(source) if source.is_dir() or source.name in ("python", "python3", "python3.11") else None
    if selected:
        return selected
    archives = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.name.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz")))
    roots = []
    for archive in archives:
        with tarfile.open(archive, "r:*") as stream:
            is_runtime = any(PurePosixPath(m.name).name == "pyvenv.cfg" or
                PurePosixPath(m.name).parts[-2:] == ("bin", "python3.11") for m in stream)
        if is_runtime:
            root = Path(repo) / "data/processed/ls1/runtime" / ("part-" + str(len(roots)))
            safe_extract(archive, root, skip_external_runtime_links=True)
            roots.append(root)
    if roots:
        selected = select(roots[0].parent)
    if not selected:
        raise ValueError("PINNED_RUNTIME_PREP_MISSING_OR_NOT_RELOCATABLE_NO_REBUILD")
    return selected


def inventory_runtime(source, output):
    """Owner preparation: hash existing Runtime Prep bytes, never rebuild them."""
    source = Path(source).absolute()
    files = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
    root = source.parent if source.is_file() else source
    if Path(output).resolve().is_relative_to(root.resolve()):
        raise ValueError("WRITE_RUNTIME_INVENTORY_OUTSIDE_PREP_INPUT")
    if not files:
        raise ValueError("RUNTIME_PREP_BYTES_MISSING")
    entries = {}
    for path in files:
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("RUNTIME_PREP_LINK_ESCAPES_INPUT")
        name = path.relative_to(root).as_posix()
        entries[name] = {"sha256": digest(path), "size_bytes": path.stat().st_size}
    receipt = {"schema": "ls1-runtime-inventory-v1", "files": entries}
    write_json(output, receipt)
    return digest(output)


def verify_runtime_input(source, inventory_path, trusted_sha256):
    """Require a separately trusted inventory hash BEFORE executing Python."""
    if not trusted_sha256 or digest(inventory_path) != trusted_sha256:
        raise ValueError("TRUSTED_RUNTIME_INVENTORY_CHECKSUM_REQUIRED")
    inventory = strict_json(Path(inventory_path).read_bytes())
    if set(inventory) != {"schema", "files"} or inventory["schema"] != "ls1-runtime-inventory-v1":
        raise ValueError("RUNTIME_INVENTORY_SCHEMA_MISMATCH")
    source = Path(source).absolute()
    root = source.parent if source.is_file() else source
    files = [source] if source.is_file() else [p for p in root.rglob("*") if p.is_file()]
    observed = {p.relative_to(root).as_posix() for p in files}
    if observed != set(inventory["files"]):
        raise ValueError("RUNTIME_INPUT_INVENTORY_MISMATCH")
    for name, receipt in inventory["files"].items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name:
            raise ValueError("UNSAFE_RUNTIME_INVENTORY_PATH")
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("RUNTIME_INPUT_LINK_ESCAPES_INPUT")
        if digest(path) != receipt["sha256"] or path.stat().st_size != receipt["size_bytes"]:
            raise ValueError("RUNTIME_INPUT_CHECKSUM_MISMATCH")
    return inventory


def launch(repo, inputs, settings):
    """Authorize before touching data/model/runtime. Launch once, package finally."""
    repo, inputs = Path(repo).absolute(), Path(inputs)
    if settings.get("internet_off_confirmed") is not True:
        raise PermissionError("CONFIRM_KAGGLE_INTERNET_OFF")
    selected = dict(settings)
    if selected.get("approval_input"):
        selected["approval_path"] = str(attached_path(inputs, selected["approval_input"]))
    authorize(selected, repo)
    run_root = repo / "data/processed/ls1/runs" / selected["run_id"]
    if run_root.exists():
        raise FileExistsError("RUN_EXISTS_NO_RETRY_OR_OVERWRITE")
    output = repo.parent / ("ls1-output-" + selected["run_id"])
    output.mkdir(exist_ok=False)
    # Only discover the selected model's prep attachments; no generic dataset scan.
    words = ("internvl3",) if selected["model_key"] == "internvl3" else ("qwen", "2")
    try:
        model_input = select_input(inputs, selected.get("model_input", ""), (*words, "model"))
        runtime_input = select_input(inputs, selected.get("runtime_input", ""), (*words, "runtime"))
        if selected.get("runtime_inventory_input"):
            inventory_path = attached_path(inputs, selected["runtime_inventory_input"])
        else:
            inventories = list(inputs.glob("*/ls1_runtime_inventory.json"))
            if len(inventories) != 1:
                raise ValueError("ATTACH_ONE_TRUSTED_RUNTIME_INVENTORY")
            inventory_path = inventories[0]
        runtime_inventory = verify_runtime_input(runtime_input, inventory_path, selected.get("runtime_inventory_sha256"))
        snapshot = restore_model(repo, model_input, selected["model_key"])
        site = attached_path(inputs, selected["runtime_site_packages"]) if selected.get("runtime_site_packages") else None
        if site is not None and not site.resolve().is_relative_to(runtime_input.resolve()):
            raise ValueError("SITE_PACKAGES_OUTSIDE_VERIFIED_RUNTIME_INPUT")
        runtime = runtime_interpreter(repo, runtime_input, selected["model_key"], site)
        selected["snapshot"] = str(snapshot)
        selected["runtime_input_receipt"] = {"input_inventory": runtime_inventory,
            "inventory_sha256": selected["runtime_inventory_sha256"],
            "runtime_input": os.path.relpath(runtime_input, inputs).replace("\\", "/")}
        if selected["mode"] != "technical":
            for key in ("dataset_root", "manifest_path", "provenance_path"):
                selected[key] = str(attached_path(inputs, selected[key]))
        settings_path = output / "launch_settings.json"
        # Local launch settings may contain temporary absolute paths; never export
        # them as research provenance or include them in the result archive.
        write_json(settings_path, selected)
        env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0", "PYTHONPATH": str(repo)}
        if runtime["site_packages"]:
            env["PYTHONPATH"] += os.pathsep + runtime["site_packages"]
        env.pop("PYTHONHOME", None)
        write_json(output / "runtime_receipt.json", {"software_versions": runtime["software_versions"],
            "input_inventory": runtime_inventory, "inventory_sha256": selected["runtime_inventory_sha256"],
            "runtime_input": os.path.relpath(runtime_input, inputs).replace("\\", "/"),
            "model_input": os.path.relpath(model_input, inputs).replace("\\", "/")})
        subprocess.run([runtime["python"], "-m", "safeshift.ls1.experiment", "--repo", str(repo),
                        "--settings", str(settings_path)], cwd=repo, env=env, check=True)
    except BaseException as exc:
        write_json(output / "launch_failure.json", {"status": "STOPPED", "exception_type": type(exc).__name__,
                                                   "retry_permitted": False})
        raise
    finally:
        if run_root.exists():
            archive = output / "ls1_results.tar.gz"
            with tarfile.open(archive, "x:gz") as stream:
                stream.add(run_root, arcname="ls1/" + selected["run_id"])
            write_json(output / "result_package.json", {"archive": archive.name, "sha256": digest(archive),
                       "source_commit": selected["source_commit"], "protocol": "LS1"})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-source", action="store_true")
    parser.add_argument("--inventory-runtime", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.inventory_runtime is not None and args.output is not None:
        print(inventory_runtime(args.inventory_runtime, args.output))
        return
    if not args.bundle_source or args.output is None:
        parser.error("Use --bundle-source --repo REPO --output NEW_DIR")
    bundle_source(args.repo, args.output)


if __name__ == "__main__":
    main()
