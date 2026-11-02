"""Isolated software setup, always executed under the fresh hard supervisor.

Peers reuse reviewed CPython3119/venv/pip provisioning unchanged. Qwen builds
the exact historical CPython/zlib sources from sealed offline software Inputs,
then installs an explicitly sealed, closed cp312 wheelhouse without resolution.
No checkpoint downloader, kernel fallback, unpinned pip install or ensurepip.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import time

from safeshift.candidates.source import require, ROOT, snapshot_stat
from safeshift.pilot.artifacts import read, safe, sha, write, relative
from safeshift.pilot.contract import digest, require_hash
from .qwen import reference


def clean_env(repo, scratch):
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR") if k in os.environ}
    env.update(HOME=str(scratch), TMPDIR=str(scratch), PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(repo), CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
        HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false", PIP_CONFIG_FILE=os.devnull,
        PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1")
    env.update(HF_HOME=str(Path(scratch)/"hf"), HF_HUB_CACHE=str(Path(scratch)/"hf/hub"),
        HF_MODULES_CACHE=str(Path(scratch)/"hf/modules"), XDG_CACHE_HOME=str(Path(scratch)/"cache"),
        TORCH_HOME=str(Path(scratch)/"torch"))
    return env


def software_input(root, expected_sha, runtime_lock, repo=ROOT):
    root = Path(root)
    marker = safe(root, "fresh_qwen_software.json")
    require_hash(expected_sha)
    require(marker.stat().st_size <= 2**20 and sha(marker) == expected_sha, "QWEN_SOFTWARE_MARKER_PIN")
    value = read(marker)
    require(set(value) == {"schema", "runtime_lock", "python_source", "zlib_source"}
            and value["schema"] == "fresh-qwen-software-v1" and value["runtime_lock"] == runtime_lock,
            "QWEN_SOFTWARE_MANIFEST")
    require(set(runtime_lock) == {"versions", "wheels"} and type(runtime_lock["versions"]) is dict
            and type(runtime_lock["wheels"]) is list and 1 <= len(runtime_lock["wheels"]) <= 256,
            "QWEN_CLOSED_WHEEL_LOCK_REQUIRED")
    normalize = lambda n: n.lower().replace("_", "-").replace(".", "-")
    require(all(normalize(n) == n and isinstance(v, str) and v for n, v in runtime_lock["versions"].items()),
            "QWEN_NORMALIZED_EXACT_VERSIONS")
    ref = reference(repo)
    for name, version in ref["software"].items():
        if name not in ("python", "zlib"):
            require(runtime_lock["versions"].get(normalize(name)) == version, "QWEN_REQUIRED_PACKAGE_PIN:" + name)
    # Reuse the checked pip-wheel bootstrap version, not host/kernel pip.
    require(runtime_lock["versions"].get("pip") == "25.0.1", "QWEN_PINNED_PIP_BOOTSTRAP")
    names, paths, total = set(), set(), 0
    for row in runtime_lock["wheels"]:
        require(type(row) is dict and set(row) == {"file", "name", "version", "size", "sha256"}, "QWEN_WHEEL_FIELDS")
        relative(row["file"])
        require("/" not in row["file"] and row["file"].endswith(".whl") and row["file"] not in paths,
                "QWEN_WHEEL_BASENAME")
        require(row["name"] not in names and runtime_lock["versions"].get(row["name"]) == row["version"], "QWEN_WHEEL_VERSION")
        require(type(row["size"]) is int and row["size"] > 0, "QWEN_WHEEL_SIZE")
        require_hash(row["sha256"])
        p = safe(root, "wheels/" + row["file"])
        snapshot_stat(p)
        require(p.stat().st_size == row["size"] and sha(p) == row["sha256"], "QWEN_WHEEL_HASH")
        names.add(row["name"]); paths.add(row["file"]); total += row["size"]
    require(names == set(runtime_lock["versions"]) and total <= 16 * 2**30, "QWEN_CLOSED_WHEEL_INVENTORY")
    require({p.name for p in (root / "wheels").iterdir()} == paths, "QWEN_NO_EXTRA_WHEELS")
    for name in ("python_source", "zlib_source"):
        row = value[name]
        require(set(row) == {"file", "size", "sha256"} and row["sha256"] == ref[name]["sha256"], "QWEN_BUILD_SOURCE_PIN")
        relative(row["file"])
        require("/" not in row["file"] and type(row["size"]) is int and 0 < row["size"] <= 64 * 2**20, "QWEN_SOURCE_BOUND")
        p = safe(root, row["file"])
        snapshot_stat(p)
        require(p.stat().st_size == row["size"] and sha(p) == row["sha256"], "QWEN_BUILD_ARCHIVE_HASH")
    return value


def extract_source(archive, target):
    """Bounded regular-file-only source extraction; no extractall or alias paths."""
    target = Path(target)
    target.mkdir(exist_ok=False)
    with tarfile.open(archive) as bundle:
        rows, total = {}, 0
        for member in bundle:
            name = member.name.rstrip("/")
            relative(name)
            require(name not in rows and len(rows) < 30000, "BUILD_ARCHIVE_INVENTORY")
            require((member.isdir() or member.isreg()) and not member.sparse and not member.mode & 0o7000,
                    "BUILD_ARCHIVE_TYPE")
            total += member.size
            require(0 <= member.size and total <= 512 * 2**20, "BUILD_ARCHIVE_SIZE")
            rows[name] = member
        for name, member in rows.items():
            p = safe(target, name)
            if member.isdir():
                p.mkdir(parents=True, exist_ok=True)
            else:
                p.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as stream, p.open("xb") as out:
                    shutil.copyfileobj(stream, out, 2**20)
                p.chmod(0o755 if member.mode & 0o111 else 0o644)


def prepare(request, repo, output, deadline):
    """Called in the supervised setup child; all its descendants share one group."""
    key, scratch = request["model_key"], Path(request["scratch"])
    env = clean_env(repo, scratch)
    if key != "qwen3":
        from safeshift.candidates.train_runtime import prepare_runtime
        python, env = prepare_runtime(Path(repo), key, scratch, Path(output), env, deadline)
    else:
        from safeshift.pilot import bootstrap
        root = Path(request["software_input"])
        seal = software_input(root, request["software_marker_sha256"], request["runtime_lock"], repo)
        runtime = scratch / "qwen-software"
        runtime.mkdir(exist_ok=False)
        def invoke(argv, name, cwd):
            require(time.monotonic() < deadline, "SETUP_DEADLINE")
            with (Path(output) / (name + ".log")).open("xb") as log:
                subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                               check=True, timeout=max(.001, deadline - time.monotonic()))
        for component in ("zlib", "python"):
            extract_source(root / seal[component + "_source"]["file"], runtime / (component + "-source"))
        zsource = runtime / "zlib-source/zlib-1.2.11"
        zprefix = runtime / "zlib"
        invoke(["./configure", "--prefix=" + str(zprefix)], "zlib-configure", zsource)
        invoke(["make", "-j2"], "zlib-make", zsource)
        invoke(["make", "install"], "zlib-install", zsource)
        env.update(CPPFLAGS="-I" + str(zprefix / "include"),
            LDFLAGS="-L" + str(zprefix / "lib") + " -Wl,-rpath," + str(zprefix / "lib"),
            ZLIB_CFLAGS="-I" + str(zprefix / "include"), ZLIB_LIBS="-L" + str(zprefix / "lib") + " -lz")
        psource, prefix = runtime / "python-source/Python-3.12.13", runtime / "cpython"
        invoke(["./configure", "--prefix=" + str(prefix), "--with-ensurepip=no"], "python-configure", psource)
        invoke(["make", "-j2"], "python-make", psource)
        invoke(["make", "install"], "python-install", psource)
        venv = runtime / "venv"
        invoke([prefix / "bin/python3.12", "-I", "-B", "-m", "venv", "--without-pip", "--copies", venv], "venv", repo)
        python = venv / "bin/python"
        # Invoke pip directly from its sealed wheel to bootstrap itself. This
        # avoids ensurepip and importing the notebook's pip controller.
        pip_row = next(r for r in request["runtime_lock"]["wheels"] if r["name"] == "pip")
        require(pip_row["sha256"] == read(Path(repo) / "configs/pilot/pip_bootstrap.json")["pip"]["sha256"], "QWEN_PIP_WHEEL_PIN")
        wheel = root / "wheels" / pip_row["file"]
        code = "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')"
        invoke([python, "-I", "-B", "-c", code, wheel, "install", "--no-index", "--no-deps", wheel], "pip-bootstrap", repo)
        pip = [python, "-I", "-B", "-m", "pip", "--isolated", "--disable-pip-version-check"]
        wheels = [root / "wheels" / r["file"] for r in request["runtime_lock"]["wheels"]]
        invoke(pip + ["install", "--no-index", "--no-deps", *wheels], "offline-install", repo)
        invoke(pip + ["check"], "pip-check", repo)
        env = clean_env(repo, scratch)
        env.update(SAFESHIFT_WORKER_PYTHON=str(python), SAFESHIFT_RUNTIME_ROOT=str(venv),
                   PYTORCH_ALLOC_CONF="expandable_segments:True")
    write(Path(output) / "runtime.json", {"python": str(python), "env": env,
        "request_sha256": digest(request), "weights_loaded": False, "model_calls": 0})
    return python, env
