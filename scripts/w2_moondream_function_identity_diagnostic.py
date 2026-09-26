"""Identity-only observation; future execution requires a fresh offline process."""

import argparse
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
import inspect
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.moondream_binding import (
    code_signature, load_verified_modules, verified_source,
)
from safeshift.runners.moondream_snapshot import (
    AUDIT_SHA256, MODEL_ID, REVISION, deny_network_permanently, verify_snapshot,
)
from safeshift.runners.storage import FileRawStore
from scripts.w2_moondream_load_diagnostic import sanitized

ARTIFACT_ROOT = "data/processed/moondream_function_identity_diagnostic"
EXPECTED_QUALNAME = "MoondreamModel.__init__"
PREVIOUS_RUN = "moondream-load-diagnostic-20260926T124352Z-d0f85ea7"
MISSING = object()


def _attribute(function, name):
    # Read native function descriptors; never invoke arbitrary callable properties.
    if type(function) is types.FunctionType:
        return getattr(function, name, MISSING)
    return inspect.getattr_static(function, name, MISSING)


def _text(value):
    return value if type(value) is str else None


def _filename(value, repo):
    if type(value) is not str:
        return None
    path = Path(value)
    if path.is_absolute():
        try:
            return path.relative_to(repo.resolve()).as_posix()
        except ValueError:
            return "<external>/" + path.name
    if PureWindowsPath(value).is_absolute():
        return "<external>/" + PureWindowsPath(value).name
    return value.replace("\\", "/")


def identity_metadata(function, module, *, repo):
    """Allowlisted scalar metadata only: no repr, globals dump or cell contents."""
    qualname = _attribute(function, "__qualname__")
    globals_ = _attribute(function, "__globals__")
    closure = _attribute(function, "__closure__")
    code = _attribute(function, "__code__")
    has_code = type(code) is types.CodeType
    namespace = vars(module.MoondreamModel)
    return {
        "function_type_name": type(function).__name__,
        "function_type_module": _text(type(function).__module__),
        "is_exact_types_FunctionType": type(function) is types.FunctionType,
        "actual_qualname": _text(qualname),
        "expected_qualname": EXPECTED_QUALNAME,
        "qualname_matches": qualname == EXPECTED_QUALNAME if type(qualname) is str else None,
        "globals_is_module_vars": globals_ is vars(module) if type(globals_) is dict else None,
        "closure_is_none": closure is None if closure is None or type(closure) is tuple else None,
        "closure_length": 0 if closure is None else len(closure) if type(closure) is tuple else None,
        "co_freevars": list(code.co_freevars) if has_code else None,
        "function_module_name": _text(_attribute(function, "__module__")),
        "function_code_name": code.co_name if has_code else None,
        "function_code_qualname": code.co_qualname if has_code else None,
        "function_code_filename": _filename(code.co_filename, repo) if has_code else None,
        "function_code_filename_policy": "REPO_RELATIVE_OR_EXTERNAL_BASENAME",
        "class_dict_has_own_init": "__init__" in namespace,
        "class_dict_init_is_function": namespace.get("__init__", MISSING) is function,
    }


def expected_code_metadata(function, snapshot):
    # Match verify_function's compile options and depth-first code-object lookup.
    compiled = compile(verified_source(snapshot, "moondream.py"), "moondream.py",
                       "exec", dont_inherit=True)

    def find(code):
        if code.co_qualname == EXPECTED_QUALNAME:
            return code
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                found = find(constant)
                if found is not None:
                    return found
        return None

    expected = find(compiled)
    actual = _attribute(function, "__code__")
    comparable = expected is not None and type(actual) is types.CodeType
    return {"expected_code_exists": expected is not None,
            "code_signature_matches": code_signature(expected) == code_signature(actual)
            if comparable else None}


def run_diagnostic(*, repo, cache_dir, run_id, expected_commit):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", run_id):
        raise ValueError("DIAGNOSTIC_RUN_ID_MUST_BE_A_SINGLE_SAFE_COMPONENT")
    directory = FileRawStore(repo, ARTIFACT_ROOT + "/" + run_id).root
    directory.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": "moondream-function-identity-diagnostic-v1", "run_id": run_id,
        "scope": "FUNCTION_IDENTITY_ONLY_NOT_RUNTIME_QUALIFICATION",
        "previous_load_diagnostic_run_id": PREVIOUS_RUN,
        "status": "FAIL", "stage": "provenance", "exception": None,
        "execution_commit": None, "expected_commit": expected_commit,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID, "model_revision": REVISION, "source_audit_sha256": AUDIT_SHA256,
        "model_manifest": None, "identity": None,
        "expected_code_exists": None, "code_signature_matches": None,
        "software_versions": {"python": platform.python_version()},
        "system": {"system": platform.system(), "machine": platform.machine()},
        "seed": None, "network_policy": "EXISTING_PERMANENT_OFFLINE_NETWORK_DENIAL",
        "artifact_path": directory.relative_to(repo.resolve()).as_posix() + "/report.json",
        "command": ["scripts/w2_moondream_function_identity_diagnostic.py",
                    "--execute-identity-diagnostic", "--expected-commit", expected_commit,
                    "--cache-dir", cache_dir, "--run-id", run_id],
    }
    with (directory / "report.json").open("x", encoding="utf-8") as stream:
        try:
            # All Git calls precede the irreversible subprocess/network denial.
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            report["execution_commit"] = commit
            if (not re.fullmatch(r"[0-9a-f]{40}", expected_commit) or commit != expected_commit
                    or subprocess.check_output(
                        ["git", "status", "--porcelain", "--untracked-files=all"],
                        cwd=repo, text=True).strip()):
                raise ValueError("EXACT_EXECUTION_COMMIT_AND_CLEAN_CHECKOUT_REQUIRED")
            report["stage"] = "local_snapshot"
            cache = FileRawStore(repo, cache_dir).root
            snapshot = cache / "models--vikhyatk--moondream2" / "snapshots" / REVISION
            report["model_manifest"] = verify_snapshot(snapshot, MODEL_ID, REVISION)
            for name in ("torch", "transformers", "tokenizers", "numpy", "pillow",
                         "huggingface-hub", "safetensors"):
                try:
                    report["software_versions"][name] = version(name)
                except PackageNotFoundError:
                    report["software_versions"][name] = None
            report["stage"] = "offline_boundary"
            deny_network_permanently()
            report["stage"] = "verified_module_import"
            _, modules = load_verified_modules(snapshot)
            report["stage"] = "identity_observation"
            module = modules["moondream"]
            function = module.MoondreamModel.__init__
            report["identity"] = identity_metadata(function, module, repo=repo)
            report["stage"] = "expected_code_comparison"
            report.update(expected_code_metadata(function, snapshot))
            report["stage"] = "complete"
            # Completion means observation succeeded, regardless of predicate values.
            report["status"] = "IDENTITY_OBSERVED"
        except BaseException as error:
            # No exception text/traceback/locals: imported source can carry arbitrary values.
            report["exception"] = {"stage": report["stage"], "type": type(error).__name__}
        finally:
            report["finished_utc"] = datetime.now(timezone.utc).isoformat()
            report = sanitized(report)
            json.dump(report, stream, indent=2, ensure_ascii=True, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-identity-diagnostic", action="store_true", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    report = run_diagnostic(repo=ROOT, cache_dir=args.cache_dir, run_id=args.run_id,
                            expected_commit=args.expected_commit)
    print(json.dumps({k: report[k] for k in ("status", "stage", "artifact_path")}))
    return 0 if report["status"] == "IDENTITY_OBSERVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
