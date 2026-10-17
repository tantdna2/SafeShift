"""Online preparation only; no torch import, model construction or generation."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from urllib.request import urlopen

from .artifacts import sha256, write
from .contract import MODELS


def fetch(url, path, expected):
    path = Path(path)
    with urlopen(url, timeout=120) as response, path.open("xb") as stream:
        while block := response.read(8 * 1024 * 1024):
            stream.write(block)
        stream.flush()
        os.fsync(stream.fileno())
    if sha256(path) != expected:
        raise ValueError("DOWNLOAD_CHECKSUM_MISMATCH:" + path.name)


def extract(archive, dest):
    with tarfile.open(archive) as stream:
        members = stream.getmembers()
        for member in members:
            target = dest / member.name
            if (member.name.startswith("/") or ".." in member.name.split("/")
                    or not target.absolute().is_relative_to(dest.absolute())
                    or not (member.isfile() or member.isdir())):
                raise ValueError("UNSAFE_SOURCE_ARCHIVE_MEMBER")
        stream.extractall(dest, members=members)


def invoke(command, cwd, log, *, env=None):
    with Path(log).open("xb") as stream:
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, close_fds=True)
    if result.returncode:
        raise RuntimeError("PROVISION_COMMAND_FAILED:" + Path(log).name)


def build_environment(model, repo, runtime, evidence):
    """Compile exact official CPython; Qwen links the audited old zlib explicitly."""
    repo, runtime, evidence = Path(repo), Path(runtime), Path(evidence)
    runtime.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    pin = json.loads((repo / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
    version = MODELS[model]["python"]
    sources = runtime / "sources"
    sources.mkdir()
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SSL_CERT_FILE", "SSL_CERT_DIR")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    env.update(PIP_CONFIG_FILE=os.devnull, PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1")
    if model == "qwen3":
        zpin = pin["zlib"]
        archive = sources / "zlib.tar.gz"
        fetch(zpin["url"], archive, zpin["sha256"])
        extract(archive, sources)
        zroot = sources / "zlib-1.2.11"
        zprefix = runtime / "zlib"
        invoke(["./configure", "--prefix=" + str(zprefix)], zroot, evidence / "zlib-configure.log", env=env)
        invoke(["make", "-j2"], zroot, evidence / "zlib-make.log", env=env)
        invoke(["make", "install"], zroot, evidence / "zlib-install.log", env=env)
        env.update(CPPFLAGS="-I" + str(zprefix / "include"),
                   LDFLAGS="-L" + str(zprefix / "lib") + " -Wl,-rpath," + str(zprefix / "lib"),
                   ZLIB_CFLAGS="-I" + str(zprefix / "include"), ZLIB_LIBS="-L" + str(zprefix / "lib") + " -lz")
    pp = pin["python"][version]
    archive = sources / "python.tar.xz"
    fetch(pp["url"], archive, pp["sha256"])
    extract(archive, sources)
    src = sources / ("Python-" + version)
    prefix = runtime / "python"
    invoke(["./configure", "--prefix=" + str(prefix), "--with-ensurepip=install"], src,
           evidence / "python-configure.log", env=env)
    invoke(["make", "-j2"], src, evidence / "python-make.log", env=env)
    invoke(["make", "install"], src, evidence / "python-install.log", env=env)
    python = prefix / "bin" / ("python" + ".".join(version.split(".")[:2]))
    # Fresh prefix, own site-packages, no host or competing torch installation.
    from safeshift.protocol.classification_policy import load_policy
    wanted = load_policy(repo, qwen3_runtime=True)["classification"][model]["software_versions"]
    if model == "qwen3":
        wanted = {**wanted, **pin["qwen3_additional_pins"]}
    requirements = [k.replace("huggingface_hub", "huggingface-hub") + "==" + v
                    for k, v in wanted.items() if k not in ("python", "zlib")]
    index = "https://download.pytorch.org/whl/cu" + MODELS[model]["cuda"].replace(".", "")
    invoke([python, "-m", "pip", "install", "--only-binary=:all:", "--index-url", "https://pypi.org/simple",
            "--extra-index-url", index, "--report", evidence / "pip-install.json", *requirements],
           repo, evidence / "pip-install.log", env=env)
    invoke([python, "-m", "pip", "check"], repo, evidence / "pip-check.log", env=env)
    write(evidence / "build-pins.json", {"model": model, "sources": {"python": pp, "zlib": pin["zlib"] if model == "qwen3" else None},
                                       "requirements": requirements, "pytorch_index": index})
    return python


def qwen_files(repo):
    from scripts.provision_qwen3vl_snapshot import weight_files
    value = json.loads((Path(repo) / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
    rows = value["qwen3_snapshot_files"]
    weights = {r["path"]: r for r in weight_files(repo)}
    for row in rows:
        if row["path"] in weights:
            expected = weights[row["path"]]
            if (row["expected_hash"], row["size_bytes"], row["hash_algorithm"]) != (expected["lfs_sha256"], expected["size_bytes"], "sha256"):
                raise ValueError("QWEN_WEIGHT_INVENTORY_DRIFT")
    if not set(weights) <= {r["path"] for r in rows}:
        raise ValueError("QWEN_WEIGHT_INVENTORY_MISSING")
    return rows


def verify_qwen(snapshot, repo):
    from scripts.provision_qwen3vl_snapshot import verify_weights, weight_files
    snapshot = Path(snapshot)
    if snapshot.name != MODELS["qwen3"]["revision"]:
        raise ValueError("QWEN_REVISION_DIRECTORY_REQUIRED")
    rows = qwen_files(repo)
    if {p.name for p in snapshot.iterdir()} != {r["path"] for r in rows}:
        raise ValueError("QWEN_SNAPSHOT_INVENTORY_MISMATCH")
    files = []
    for row in rows:
        path = snapshot / row["path"]
        if not path.resolve().is_relative_to(snapshot.parent.parent.resolve()):
            raise ValueError("QWEN_CACHE_FILE_ESCAPE")
        size = path.stat().st_size
        actual = sha256(path)
        if row["hash_algorithm"] == "git_blob_sha1":
            h = hashlib.sha1(("blob " + str(size) + "\0").encode())
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    h.update(block)
            official = h.hexdigest()
        else:
            official = actual
        if size != row["size_bytes"] or official != row["expected_hash"]:
            raise ValueError("QWEN_SNAPSHOT_CHECKSUM_MISMATCH:" + row["path"])
        files.append({**row, "sha256": actual})
    weight_receipt = verify_weights(snapshot, weight_files(repo))
    if not weight_receipt["LOCAL_WEIGHT_BYTES_VERIFIED"]:
        raise ValueError("QWEN_WEIGHTS_NOT_VERIFIED")
    return {"model_id": MODELS["qwen3"]["id"], "revision": MODELS["qwen3"]["revision"],
            "files": files, "local_bytes_verified": True, "weight_receipt": weight_receipt}


def provision_model(model, repo, cache, evidence):
    if model == "internvl3":
        from safeshift.runners.internvl3_snapshot import provision_or_verify
        receipt = provision_or_verify(provision=True, repo=repo, cache_dir=cache)
    else:
        from huggingface_hub import snapshot_download
        from scripts.provision_qwen3vl_snapshot import cached_snapshot
        root = Path(repo) / cache
        if root.exists() and any(root.iterdir()):
            raise ValueError("CACHE_NOT_EMPTY_NO_REPAIR_OR_OVERWRITE")
        rows = qwen_files(repo)
        downloaded = Path(snapshot_download(repo_id=MODELS[model]["id"], revision=MODELS[model]["revision"],
            cache_dir=str(root), allow_patterns=[r["path"] for r in rows], local_files_only=False))
        # Existing pinned cache resolver + weight verifier; extended full inventory.
        if cached_snapshot(str(root), offline=True).absolute() != downloaded.absolute():
            raise ValueError("QWEN_DOWNLOADED_SNAPSHOT_MISMATCH")
        receipt = verify_qwen(downloaded, repo)
    write(Path(evidence) / "model-provision.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    provision_model(args.model, Path.cwd(), args.cache, args.evidence)


if __name__ == "__main__":
    main()
