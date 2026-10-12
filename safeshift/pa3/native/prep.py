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
from safeshift.ls1.kaggle import inventory_runtime, runtime_interpreter
from safeshift.ls1.tokenizer import plan, verify_snapshot
from .journal import safe_relative

UV_VERSION = "0.6.14"


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
    output.mkdir(parents=True, exist_ok=False)
    root = output / "build"
    root.mkdir()
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONNOUSERSITE": "1",
           "UV_NO_CACHE": "1", "UV_PYTHON_BIN_DIR": str(root / "bin")}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    log = []

    def run(command):
        log.append([str(x) for x in command])
        subprocess.run(command, check=True, env=env)

    try:
        for command in commands(repo, root):
            run(command)
        interpreters = list((root / "managed").glob("*/bin/python3.11"))
        if len(interpreters) != 1:
            raise ValueError("EXACT_MANAGED_PYTHON_REQUIRED")
        python = interpreters[0]
        run([str(python), "-m", "ensurepip"])
        pins = plan("qwen2_5", repo)["software"]
        constraints = output / "constraints.txt"
        constraints.write_text("\n".join(k + "==" + v for k, v in pins.items() if k != "python") + "\n")
        run([str(python), "-m", "pip", "install", "--no-cache-dir", "-c", str(constraints),
             "torch==" + pins["torch"], "torchvision==" + pins["torchvision"],
             "--index-url", "https://download.pytorch.org/whl/cu124"])
        run([str(python), "-m", "pip", "install", "--no-cache-dir", "-c", str(constraints)] +
            [k + "==" + v for k, v in pins.items() if k not in {"python", "torch", "torchvision"}])
        run([str(python), "-m", "pip", "check"])
        # Move the actual Python installation before testing, then archive it.
        # A system-Python venv alone is insufficient for portable Kaggle input.
        relocated = output / "relocated"
        shutil.move(str(python.parent.parent), relocated)
        selected = runtime_interpreter(repo, relocated, "qwen2_5")
        run([selected["python"], "-s", "-c",
             "import torch,torchvision,transformers,qwen_vl_utils; "
             "assert torch.__version__=='2.6.0+cu124'; "
             "assert torch.version.cuda=='12.4'; "
             "from transformers import Qwen2_5_VLForConditionalGeneration"])
        freeze = subprocess.check_output([selected["python"], "-m", "pip", "freeze", "--all"], env=env)
        (output / "resolved-requirements.txt").write_bytes(freeze)
        archive = output / "pa3_runtime.tar.gz"
        pack_tree(relocated, archive)
        from safeshift.runners.p21_kaggle import safe_extract
        restored = safe_extract(archive, output / "archive-roundtrip")
        checked = runtime_interpreter(repo, restored, "qwen2_5")
        run([checked["python"], "-s", "-c",
             "import torch,torchvision,qwen_vl_utils; "
             "from transformers import Qwen2_5_VLForConditionalGeneration; "
             "assert torch.__version__=='2.6.0+cu124'"])
        inventory_sha = inventory_runtime(archive, output / "pa3_runtime_inventory.json")
        write_json(output / "runtime_prep.json", {"status": "CPU_RELOCATION_ARCHIVE_ROUNDTRIP_IMPORT_PASS_GPU_NOT_RUN",
            "software": selected["software_versions"], "uv": UV_VERSION,
            "archive_sha256": digest(archive), "inventory_sha256": inventory_sha,
            "resolved_requirements_sha256": digest(output / "resolved-requirements.txt"),
            "transitive_versions": "CAPTURED_IN_RESOLVED_REQUIREMENTS_NOT_PROSPECTIVELY_LOCKED"})
    finally:
        # Relative commands in exported provenance (no personal absolute paths).
        write_json(output / "commands.json", [[s.replace(str(output), "<prep>") for s in c] for c in log])


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
    parser.add_argument("kind", choices=("runtime", "model"))
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
    {"runtime": runtime, "model": model}[args.kind](repo, output)


if __name__ == "__main__":
    main()
