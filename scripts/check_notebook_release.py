"""Offline CPU acceptance of a reviewed Git snapshot; never authorizes a run.

Reuse the snapshot's notebook builder, source contract and stdlib test suite.
Candidate no-grant cells execute only through synthetic CPU tests; legacy cells
are inspected without execution. Never enable native opt-ins, network probes,
real grants, weights or GPU execution.
The runtime ref is trusted reviewed repository code, not an arbitrary upload.
"""
import argparse
import ast
import base64
import hashlib
import io
import json
import os
import platform
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import zlib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))


def safe_name(name):
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or ".." in path.parts or "\\" in name
            or ":" in name or path.as_posix() != name):
        raise ValueError("UNSAFE_PATH")
    return name


def inspect_notebook(data, expected, sources, digest):
    """Inspect data/AST only. A matching notebook is not GPU/behavior proof."""
    nb = strict_json(data)
    if nb.get("nbformat") != 4 or not isinstance(nb.get("cells"), list):
        raise ValueError("NOTEBOOK_SCHEMA")
    ids = set()
    code = []
    for cell in nb["cells"]:
        cid = cell.get("id")
        if not isinstance(cid, str) or not cid or cid in ids:
            raise ValueError("CELL_ID")
        ids.add(cid)
        source = cell.get("source")
        if not isinstance(source, list) or not all(isinstance(s, str) for s in source):
            raise ValueError("CELL_SOURCE")
        if cell.get("cell_type") == "code":
            if cell.get("outputs") != [] or cell.get("execution_count") is not None:
                raise ValueError("EXECUTED_NOTEBOOK")
            text = "".join(source)
            compile(text, "<notebook>", "exec")  # Never exec/eval a cell.
            code.append(text)
        elif cell.get("cell_type") != "markdown":
            raise ValueError("CELL_TYPE")
    if len(code) != 1:
        raise ValueError("EXPECTED_SINGLE_CODE_CELL")
    # Literal embedded payload is decoded, never evaluated as Python.
    tree = ast.parse(code[0])
    payloads = []
    hashes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "expected_source_sha256" in names and isinstance(node.value, ast.Constant):
                hashes.append(node.value.value)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "base64"
                and node.func.attr == "b64decode"):
            if len(node.args) != 1 or not isinstance(node.args[0], ast.Constant):
                raise ValueError("NONLITERAL_PAYLOAD")
            packed = base64.b64decode(node.args[0].value, validate=True)
            decoder = zlib.decompressobj()
            raw = decoder.decompress(packed, 8 * 1024 * 1024 + 1)
            if (len(raw) > 8 * 1024 * 1024 or not decoder.eof
                    or decoder.unused_data or decoder.unconsumed_tail):
                raise ValueError("PAYLOAD_LIMIT_OR_TRAILING_BYTES")
            payloads.append(strict_json(raw))
    if len(payloads) != 1 or hashes != [digest]:
        raise ValueError("PAYLOAD_OR_DIGEST_BINDING")
    payload = payloads[0]
    if not isinstance(payload, dict):
        raise ValueError("PAYLOAD_SCHEMA")
    for name, value in payload.items():
        safe_name(name)
        if not isinstance(value, str):
            raise ValueError("PAYLOAD_VALUE")
        if name.endswith(".py"):
            compile(value, name, "exec")
    if payload != sources:
        raise ValueError("EMBEDDED_SOURCE_DIFFERS_FROM_REPOSITORY")
    inventory = {p: sha(t.encode()) for p, t in payload.items()}
    if sha(canonical(inventory)) != digest:
        raise ValueError("SOURCE_DIGEST_MISMATCH")
    if nb.get("metadata", {}).get("safeshift", {}).get("source_sha256") != digest:
        raise ValueError("METADATA_DIGEST_MISMATCH")
    if data != expected:
        raise ValueError("BUILDER_BYTES_DIFFER")
    # This is a bounded secret-pattern check, not a general privacy certificate.
    secret_pattern = rb"hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|PRIVATE KEY-----"
    if any(re.search(secret_pattern, content)
           for content in (data, *(value.encode() for value in payload.values()))):
        raise ValueError("POSSIBLE_CREDENTIAL")
    return {"sha256": sha(data), "embedded_source_sha256": digest, "status": "PASS"}


def unpack_snapshot(archive, destination):
    """Only regular tracked code/config/test/doc files; no aliases or traversal."""
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        seen = set()
        for entry in tar:
            name = safe_name(entry.name.rstrip("/"))
            if name in seen:
                raise ValueError("DUPLICATE_ARCHIVE_MEMBER")
            seen.add(name)
            if entry.isdir():
                continue
            if not entry.isfile() or entry.size > 16 * 1024 * 1024:
                raise ValueError("NONREGULAR_OR_OVERSIZED_SOURCE")
            if name.startswith("data/") or name.endswith((".safetensors", ".bin", ".pt")):
                raise ValueError("DATA_OR_WEIGHTS_NOT_SOURCE")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as out:
                out.write(tar.extractfile(entry).read())


def child_env():
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("SAFESHIFT_", "PYTHON", "HF_"))
           and k not in ("HUGGING_FACE_HUB_TOKEN", "TRANSFORMERS_CACHE")}
    env.update(PYTHONIOENCODING="utf-8", PYTHONNOUSERSITE="1", HF_HUB_OFFLINE="1",
               TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="")
    return env


BUILD = '''import json,sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from scripts.build_three_vlm_notebooks import notebook
from safeshift.pilot.contract import MODELS,source_files,source_digest
root=Path.cwd()
items={f"SafeShift_TRAIN_PILOT_{k}.ipynb":notebook(k) for k in MODELS}
items["SafeShift_STORAGE_PREFLIGHT.ipynb"]=notebook("phi",preflight=True)
for k in ("phi","smolvlm2"):
 items[f"SafeShift_ENVIRONMENT_PREFLIGHT_{k}.ipynb"]=notebook(k,environment=True)
result={"expected":{k:json.dumps(v,indent=1,ensure_ascii=False)+"\\n" for k,v in items.items()},
 "sources":{p:(root/p).read_text(encoding="utf-8") for p in source_files(root)},
 "digest":source_digest(root)}
if (root/"scripts/build_candidate160_notebooks.py").is_file():
 from scripts.build_candidate160_notebooks import notebook as candidate_notebook
 from safeshift.candidates.train_contract import KEYS,sources,source_hash
 candidates={}
 for key in KEYS:
  name=f"SafeShift_CANDIDATE160_{key}.ipynb"
  saved=json.loads((root/"notebooks"/name).read_bytes())
  candidates[name]=candidate_notebook(key,saved["metadata"]["safeshift"]["runtime_ref"])
 result["candidate_expected"]={k:json.dumps(v,indent=1,ensure_ascii=False)+"\\n" for k,v in candidates.items()}
 result["candidate_sources"]={p:(root/p).read_text(encoding="utf-8") for p in sources(root)}
 result["candidate_digest"]=source_hash(root)
print(json.dumps(result))
'''

TEST = '''import json,sys,unittest
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
suite=unittest.defaultTestLoader.discover("tests")
result=unittest.TextTestRunner(verbosity=1).run(suite)
print("RELEASE_TEST_RESULT="+json.dumps({"run":result.testsRun,"failures":len(result.failures),
 "errors":len(result.errors),"skipped":len(result.skipped),
 "skip_details":[[str(t),why] for t,why in result.skipped]}))
sys.exit(0 if result.wasSuccessful() and result.testsRun else 1)
'''


def command(args, cwd, timeout=180, git_context=None):
    env = child_env()
    if git_context:
        # Read-only Git object access for exact-ref builders inside an export.
        # Do not inject Python/module/native opt-in variables into the snapshot.
        if set(git_context) != {"GIT_DIR", "GIT_WORK_TREE"}:
            raise ValueError("READ_ONLY_GIT_CONTEXT_REQUIRED")
        env.update(git_context)
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=timeout)


def evaluate(repo, runtime_ref):
    receipt = {"schema": "safeshift-notebook-cpu-review-v1", "software_status": "BLOCKED",
               "release_status": "BLOCKED", "runtime_commit": runtime_ref,
               "cpu_environment": {"python": sys.version, "platform": platform.platform()},
               "no_grant_created": True, "notebook_cells_executed": False,
               "native_model_forward": "NOT_RUN", "checks": {},
               "gates": {"G0_authority": "BLOCKED_REVIEW_REQUIRED",
                         "G1_notebook": "NOT_RUN", "G2_native_environment": "REQUIRES_PINNED_CPU_ENV",
                         "G3_custody": "NOT_RUN", "G4_kaggle": "REQUIRES_AUTHORIZED_GPU",
                         "G5_behavior": "REQUIRES_AUTHORIZED_GPU",
                         "G6_release": "BLOCKED_REVIEW_REQUIRED"}}
    try:
        if not re.fullmatch("[0-9a-f]{40}", runtime_ref):
            raise ValueError("EXACT_COMMIT_REQUIRED")
        commit = command(["git", "rev-parse", runtime_ref + "^{commit}"], repo)
        if commit.returncode or commit.stdout.decode().strip() != runtime_ref:
            raise ValueError("COMMIT_NOT_AVAILABLE")
        archive = command(["git", "archive", "--format=tar", runtime_ref], repo)
        if archive.returncode:
            raise ValueError("SOURCE_EXPORT_FAILED")
        receipt["snapshot_archive_sha256"] = sha(archive.stdout)
        git_directory = command(["git", "rev-parse", "--absolute-git-dir"], repo)
        if git_directory.returncode:
            raise ValueError("READ_ONLY_SOURCE_GIT_CONTEXT_UNAVAILABLE")
        with tempfile.TemporaryDirectory(prefix="safeshift-release-cpu-") as directory:
            root = Path(directory).resolve()
            unpack_snapshot(archive.stdout, root)
            if not (root / "scripts/build_three_vlm_notebooks.py").is_file():
                receipt["reason"] = "RUNTIME_BUILDER_ABSENT_AT_REF"
                return receipt
            # Existing evidence tests allocate synthetic artifacts here; Git
            # intentionally does not track this empty scratch directory.
            (root / "data/processed").mkdir(parents=True, exist_ok=True)
            tracked = {p.relative_to(root).as_posix(): sha(p.read_bytes())
                       for p in root.rglob("*") if p.is_file()}
            git_context = {"GIT_DIR": git_directory.stdout.decode().strip(), "GIT_WORK_TREE": str(root)}
            build = command([sys.executable, "-B", "-I", "-c", BUILD], root, git_context=git_context)
            if build.returncode:
                raise ValueError("REPOSITORY_BUILDER_FAILED")
            built = strict_json(build.stdout)
            actual = {p.name for p in (root / "notebooks").glob("*.ipynb")}
            expected = {**built["expected"], **built.get("candidate_expected", {})}
            if actual != set(expected):
                raise ValueError("NOTEBOOK_INVENTORY_MISMATCH")
            receipt["checks"]["notebooks"] = {
                name: inspect_notebook((root / "notebooks" / name).read_bytes(), expected.encode(),
                                       built["candidate_sources"] if name in built.get("candidate_expected", {}) else built["sources"],
                                       built["candidate_digest"] if name in built.get("candidate_expected", {}) else built["digest"])
                for name, expected in expected.items()}
            receipt["gates"]["G1_notebook"] = "PASS"
            # Candidate160 adds full batch/recovery/archive rehearsals for both
            # models. Durable fsync on Windows can exceed the old ten-minute
            # checker budget; this is only a CPU test budget, never run authority.
            tests = command([sys.executable, "-B", "-I", "-c", TEST], root, timeout=1800, git_context=git_context)
            lines = [l for l in tests.stdout.decode("utf-8").splitlines()
                     if l.startswith("RELEASE_TEST_RESULT=")]
            receipt["checks"]["stdlib_suite"] = {
                "returncode": tests.returncode, "stdout_sha256": sha(tests.stdout),
                "stderr_sha256": sha(tests.stderr),
                "stdout": tests.stdout.decode("utf-8", errors="replace").replace(str(root), "<snapshot>"),
                "stderr": tests.stderr.decode("utf-8", errors="replace").replace(str(root), "<snapshot>"),
                "counts": strict_json(lines[-1].split("=", 1)[1]) if len(lines) == 1 else None}
            if tests.returncode or len(lines) != 1:
                raise ValueError("RUNTIME_TESTS_FAILED_OR_MISSING_SUMMARY")
            # Tests must not change any exported tracked source/release bytes.
            if any(not (root / p).is_file() or sha((root / p).read_bytes()) != h
                   for p, h in tracked.items()):
                raise ValueError("SNAPSHOT_MUTATED_BY_TESTS")
            receipt["gates"]["G3_custody"] = "PASS_STDLIB_ONLY_NATIVE_SKIPS_SEPARATE"
            receipt["software_status"] = "CODE_PASS"
            receipt["source_sha256"] = built["digest"]
            if built.get("candidate_digest"):
                receipt["candidate_source_sha256"] = built["candidate_digest"]
                receipt["notebook_cells_executed"] = "CPU_NO_GRANT_BLOCKED_ONLY_IN_SYNTHETIC_DIRECTORIES"
            receipt["limits"] = ["No native opt-in or live pip/source audit was run.",
                                 "Scripted tests do not establish real model behavior.",
                                 "No authority, ledger, release or GPU readiness certified.",
                                 "Trusted repository tests are not an OS network sandbox."]
    except (ValueError, KeyError, TypeError, AttributeError, OSError, SyntaxError, subprocess.TimeoutExpired,
            tarfile.TarError, zlib.error) as error:
        receipt["software_status"] = "FAIL"
        receipt["reason"] = type(error).__name__ + ":" + str(error)[:200]
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-ref", required=True, help="Reviewed full 40-character Git SHA")
    parser.add_argument("--output", required=True, help="New ignored local JSON receipt path")
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[1]
    output = Path(args.output)
    # Never overwrite an existing receipt or write through aliases.
    if any(p.is_symlink() for p in (output, *output.parents)):
        parser.error("RECEIPT_PATH_ALIAS")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        receipt = evaluate(repo, args.runtime_ref)
        receipt["checker_sha256"] = sha(Path(__file__).read_bytes())
        stream.write(canonical(receipt))
    print(json.dumps({"software_status": receipt["software_status"],
                      "release_status": receipt["release_status"],
                      "receipt_sha256": sha(output.read_bytes()), "output": str(output)}))
    return 0 if receipt["software_status"] == "CODE_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
