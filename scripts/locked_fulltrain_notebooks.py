"""Reproduce a historical Full-TRAIN notebook from its exact Git runtime.

This is read-only compatibility tooling, never an execution/source activation.
The current-worktree builders retain their strict dirty-source checks. Historical
builders run in a disposable, bounded Git snapshot with no site packages/network.
"""
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

from safeshift.candidates.source import ROOT, require

PREFIXES = ("safeshift/__init__.py", "safeshift/candidates", "safeshift/pilot", "safeshift/fulltrain",
    "safeshift/internvl3763_python.py", "safeshift/internvl3763_release.py", "configs/candidate160", "configs/cpu_g2_g3", "configs/pilot",
    "configs/fulltrain", "scripts/__init__.py", "scripts/build_three_vlm_notebooks.py",
    "scripts/build_candidate160_notebooks.py", "scripts/build_fresh_fulltrain_notebooks.py", "scripts/generate_minicpm_fulltrain_notebook.py")

CHILD = r'''
import hashlib, importlib.abc, json, pathlib, socket, sys
sys.stdout.reconfigure(encoding='utf-8')
root, kind, key, ref, diagnostic = sys.argv[1:]
sys.path.insert(0, root)
def forbidden(*args, **kwargs): raise AssertionError("LOCKED_BUILDER_NETWORK_FORBIDDEN")
socket.socket.connect = forbidden
socket.create_connection = forbidden
class NoModel(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('torch', 'transformers', 'PIL', 'kaggle', 'kagglesdk', 'kagglehub'):
            raise AssertionError('LOCKED_BUILDER_MODEL_OR_PROVIDER_IMPORT')
sys.meta_path.insert(0, NoModel())
if kind == 'minicpm':
    from scripts.generate_minicpm_fulltrain_notebook import notebook
    from safeshift.fulltrain.contract import sources
    value = notebook(ref, pathlib.Path(root))
elif kind == 'fresh':
    from scripts.build_fresh_fulltrain_notebooks import notebook
    from safeshift.fulltrain.contract import sources
    value = notebook(key, ref, pathlib.Path(root), diagnostic=diagnostic == '1')
else:
    from scripts.build_candidate160_notebooks import fulltrain_notebook
    from safeshift.candidates.train_contract import sources
    value = fulltrain_notebook(key, ref, pathlib.Path(root))
manifest = {p:hashlib.sha256((pathlib.Path(root)/p).read_bytes()).hexdigest() for p in sources(pathlib.Path(root))}
print(json.dumps({'notebook':value, 'manifest':manifest}, ensure_ascii=False))
'''


def strict_json(raw):
    def pairs(items):
        value = {}
        for name, item in items:
            require(name not in value, "LOCKED_DUPLICATE_JSON_KEY")
            value[name] = item
        return value
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("LOCKED_NONFINITE_JSON")))


@lru_cache(maxsize=32)
def _reproduce(key, ref, repo, kind, diagnostic):
    require(subprocess.check_output(["git", "cat-file", "-t", ref], cwd=repo, stderr=subprocess.PIPE).strip() == b"commit",
        "LOCKED_RUNTIME_COMMIT_REQUIRED")
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", ref, "--", *PREFIXES],
        cwd=repo, stderr=subprocess.PIPE).decode().splitlines()
    require(0 < len(names) <= 512 and len(names) == len(set(names)) and all(
        re.fullmatch(r"[A-Za-z0-9_./-]+", n) and all(p not in ("", ".", "..") for p in n.split("/"))
        for n in names), "BOUNDED_LOCKED_RUNTIME_TREE")
    raw = subprocess.check_output(["git", "archive", "--format=tar", ref, "--", *names], cwd=repo)
    require(len(raw) <= 16 * 2**20, "LOCKED_RUNTIME_ARCHIVE_BOUND")
    git_dir = subprocess.check_output(["git", "rev-parse", "--absolute-git-dir"], cwd=repo, text=True).strip()
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(raw)) as bundle:
            files = [m for m in bundle.getmembers() if not m.isdir()]
            require(len(files) == len(names) and {m.name for m in files} == set(names)
                and all(m.isfile() and not m.sparse and m.size <= 2 * 2**20 for m in files), "EXACT_LOCKED_RUNTIME_TREE")
            for member in files:
                path = target / member.name
                path.parent.mkdir(parents=True, exist_ok=True)
                with bundle.extractfile(member) as source, path.open("xb") as out:
                    out.write(source.read())
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "", "CUDA_VISIBLE_DEVICES": "",
            "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "GIT_DIR": git_dir, "GIT_WORK_TREE": str(target)}
        result = subprocess.run([sys.executable, "-I", "-B", "-S", "-c", CHILD, str(target), kind, key, ref,
            "1" if diagnostic else "0"], cwd=target, env=env, capture_output=True, timeout=90)
        require(result.returncode == 0, "LOCKED_BUILDER_FAILED:" + result.stderr.decode("utf8", errors="replace"))
        require(len(result.stdout) <= 8 * 2**20, "LOCKED_BUILDER_OUTPUT_BOUND")
        value = strict_json(result.stdout)
        require(set(value) == {"notebook", "manifest"} and set(value["manifest"]) <= set(names), "LOCKED_RUNTIME_MANIFEST")
        for name, expected in value["manifest"].items():
            require(hashlib.sha256((target / name).read_bytes()).hexdigest() == expected, "LOCKED_RUNTIME_BYTES")
        return result.stdout


def reproduce(key, ref, repo=ROOT, *, kind="fresh", diagnostic=False):
    require(type(ref) is str and re.fullmatch(r"[0-9a-f]{40}", ref), "EXACT_RUNTIME_COMMIT")
    require(key in ("minicpm4", "internvl35", "qwen3") and kind in ("fresh", "fulltrain", "minicpm")
        and (kind != "minicpm" or key == "minicpm4")
        and type(diagnostic) is bool and (kind == "fresh" or not diagnostic), "LOCKED_NOTEBOOK_KIND")
    # Cache immutable Git-derived bytes, never mutable caller objects or HEAD files.
    return strict_json(_reproduce(key, ref, str(Path(repo).resolve()), kind, diagnostic))


def verify_payload(nb, expected):
    """Exact membership/bytes/digest/ref, with no current-source substitution."""
    import base64
    import zlib
    from safeshift.pilot.contract import digest
    locked, manifest = expected["notebook"], expected["manifest"]
    require(nb["metadata"]["safeshift"] == locked["metadata"]["safeshift"], "LOCKED_NOTEBOOK_METADATA")
    code = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    encoded = re.findall(r"base64\.b64decode\('([^']+)'\)", code)
    require(len(encoded) == 1, "ONE_LOCKED_PAYLOAD")
    payload = strict_json(zlib.decompress(base64.b64decode(encoded[0], validate=True)))
    require(type(payload) is dict and set(payload) == set(manifest), "LOCKED_PAYLOAD_MEMBERSHIP")
    for name, text in payload.items():
        require(type(text) is str and hashlib.sha256(text.encode()).hexdigest() == manifest[name], "LOCKED_PAYLOAD_BYTES:" + name)
    require(digest(manifest) == nb["metadata"]["safeshift"]["source_sha256"], "LOCKED_PAYLOAD_DIGEST")
    return payload
