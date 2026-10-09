"""Owner-only P2.1 source preparation, input restore and one-shot packaging.

Importing this module does not inspect a runtime, model, dataset or network.
The functions below execute only when the owner selects the corresponding stage.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile

from safeshift.protocol.schema import strict_json

BASE = "f0b5ea775b3c5bbe5e8618ba1372e59b8b8e150f"
RUN_ID = "internvl3-p21-shard0-rerun1"
OLD_ID = "internvl3-p2-shard0-first"
OLD_MANIFEST = "1c245cacc4bca2230dabc7469824426deb0d5e1345ce9de9618778b6a4221d1c"
OLD_STATUS = "1a5a5c88af34341672b5db1c01f99bd782fb0a588a99a19acb4e7a0fe6237a1b"
RECEIPT = "data/processed/p21_kaggle/source_confirmation.json"
CONFIRMATION_KEYS = {"final_merge_sha", "independent_audit", "chatgpt_code_audit",
                     "research_lead_confirmed", "chatgpt_merge_main_verification",
                     "audit_evidence_reference", "merge_evidence_reference"}
STATUSES = ("SUCCESS", "INVALID", "FAILED", "NOT_ATTEMPTED")


def digest_file(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_new_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args]).decode().strip()


def validate_confirmation(value):
    # These are explicit owner attestations of external review, not Git's proof
    # that a human review took place. Both are required; neither replaces the other.
    if type(value) is not dict or set(value) != CONFIRMATION_KEYS:
        raise ValueError("EXACT_RELEASE_CONFIRMATION_FIELDS_REQUIRED")
    commit = value["final_merge_sha"]
    if (type(commit) is not str or len(commit) != 40
            or any(c not in "0123456789abcdef" for c in commit)):
        raise ValueError("EXACT_FINAL_MERGE_SHA_REQUIRED")
    for field in ("independent_audit", "chatgpt_code_audit", "chatgpt_merge_main_verification"):
        if value[field] != "PASS":
            raise PermissionError("EXTERNAL_REVIEW_PASS_REQUIRED:" + field)
    if value["research_lead_confirmed"] is not True:
        raise PermissionError("RESEARCH_LEAD_RELEASE_CONFIRMATION_REQUIRED")
    for field in ("audit_evidence_reference", "merge_evidence_reference"):
        if type(value[field]) is not str or not value[field].strip():
            raise ValueError("EXTERNAL_REVIEW_EVIDENCE_REFERENCE_REQUIRED:" + field)
    return value


def verify_source(repo, confirmation, *, online_main=False):
    confirmation = validate_confirmation(confirmation)
    from .p2_harness import authorize_production
    from .p21_authority import SCHEMA
    head, authority = authorize_production(repo)
    if (head != confirmation["final_merge_sha"] or authority["schema_version"] != SCHEMA
            or authority["model_key"] != "internvl3"):
        raise PermissionError("CONFIRMED_P21_FINAL_RELEASE_REQUIRED")
    if online_main and git(repo, "rev-parse", "refs/remotes/origin/main") != head:
        raise PermissionError("CONFIRMED_RELEASE_MUST_EQUAL_FETCHED_MAIN")
    return head


def prepare_source(repo, confirmation, output):
    """Package a full-history confirmed main checkout; never prepare Draft F2."""
    repo, output = Path(repo).resolve(), Path(output).resolve()
    if output.is_relative_to(repo):
        raise ValueError("SOURCE_PACKAGE_OUTPUT_MUST_BE_OUTSIDE_CHECKOUT")
    head = verify_source(repo, confirmation, online_main=True)
    if git(repo, "rev-parse", "--is-shallow-repository") != "false":
        raise ValueError("FULL_GIT_HISTORY_REQUIRED")
    if not (repo / ".git").is_dir() or (repo / ".git").is_symlink():
        raise ValueError("SELF_CONTAINED_GIT_CHECKOUT_REQUIRED")
    if ((repo / ".git/objects/info/alternates").exists()
            or any((repo / ".git/objects/pack").glob("*.promisor"))):
        raise ValueError("EXTERNAL_OR_PROMISOR_GIT_OBJECTS_FORBIDDEN")
    output.mkdir(parents=True, exist_ok=True)
    receipt = {"schema_version": "p21-kaggle-source-confirmation-v1",
               "confirmation": confirmation, "verified_head": head,
               "verified_tree": git(repo, "rev-parse", "HEAD^{tree}"),
               "verified_parents": git(repo, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:],
               "full_git_history": True, "external_reviews_are_owner_attestations": True}
    write_new_json(repo / RECEIPT, receipt)
    archive = output / "internvl3_p21_source.tar.gz"
    if archive.exists():
        raise FileExistsError("SOURCE_PACKAGE_ALREADY_EXISTS")
    names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().split("\0")
    files = [repo / name for name in names if name]
    files.extend(p for p in (repo / ".git").rglob("*") if p.is_file())
    files.append(repo / RECEIPT)
    with tarfile.open(archive, "x:gz", dereference=True) as stream:
        for path in sorted(set(files)):
            stream.add(path, arcname="SafeShift/" + path.relative_to(repo).as_posix(), recursive=False)
    manifest = {"schema_version": "p21-kaggle-source-package-v1", "archive": archive.name,
                "archive_sha256": digest_file(archive), "final_merge_sha": head,
                "base_sha": BASE, "receipt": "SafeShift/" + RECEIPT}
    write_new_json(output / "p21_source_release.json", manifest)
    return manifest


def safe_extract(archive, destination, *, skip_external_runtime_links=False):
    """Reject path traversal, devices and escaping links before any extraction."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    try:
        with tarfile.open(archive, "r:*") as stream:
            members = stream.getmembers()
            names = set()
            safe_members = []
            for item in members:
                path = PurePosixPath(item.name)
                if (path.is_absolute() or ".." in path.parts or "\\" in item.name
                        or ":" in item.name or item.name in names):
                    raise ValueError("UNSAFE_OR_DUPLICATE_ARCHIVE_PATH")
                names.add(item.name)
                if not (item.isfile() or item.isdir() or item.issym() or item.islnk()):
                    raise ValueError("ARCHIVE_SPECIAL_FILE_FORBIDDEN")
                if item.issym() or item.islnk():
                    link = PurePosixPath(item.linkname)
                    target = ((destination / path.parent / link) if item.issym()
                              else destination / link).resolve()
                    if link.is_absolute() or not target.is_relative_to(destination):
                        if skip_external_runtime_links and item.issym():
                            # An archived venv may contain a venue-specific Python
                            # symlink. Do not rewrite it or dereference external
                            # files. Use regular bundled managed-Python bytes and
                            # that venv's unchanged site-packages instead.
                            continue
                        raise ValueError("ARCHIVE_LINK_ESCAPES_DESTINATION")
                safe_members.append(item)
            # data filter independently validates link chains and mode bits.
            stream.extractall(destination, members=safe_members, filter="data")
    except BaseException:
        # Keep failed restore evidence; never silently repair or retry it.
        raise
    return destination


def input_path(inputs, relative):
    root = Path(inputs).resolve()
    relative = PurePosixPath(relative)
    path = root / relative
    if relative.is_absolute() or ".." in relative.parts or not path.resolve().is_relative_to(root):
        raise ValueError("INPUT_PATH_MUST_BE_RELATIVE_TO_ATTACHED_INPUTS")
    if not path.exists():
        raise FileNotFoundError("ATTACHED_INPUT_NOT_FOUND:" + str(relative))
    return path


def attachment(inputs, explicit, words):
    if explicit:
        return input_path(inputs, explicit)
    candidates = [p for p in Path(inputs).iterdir()
                  if p.is_dir() and all(word in p.name.lower() for word in words)]
    if len(candidates) != 1:
        raise ValueError("SELECT_EXACT_ATTACHED_OUTPUT:" + ",".join(words))
    return candidates[0]


def archives(root):
    return sorted(p for p in Path(root).rglob("*")
                  if p.is_file() and (p.name.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz"))))


def restore_history(repo, inputs, explicit=""):
    """Copy only actual hash-pinned historical bytes, never fabricate a manifest."""
    root = input_path(inputs, explicit) if explicit else Path(inputs)
    wanted = {"run_manifest.json": OLD_MANIFEST, "run_status.json": OLD_STATUS}
    found = {}
    search_root = root.parent if root.is_file() else root
    for name, digest in wanted.items():
        matches = [p for p in search_root.rglob(name) if digest_file(p) == digest]
        if matches:
            found[name] = matches[0].read_bytes()
    if len(found) != 2:
        packs = [root] if root.is_file() else archives(root)
        for pack in packs:
            with tarfile.open(pack, "r:*") as stream:
                for item in stream:
                    name = PurePosixPath(item.name).name
                    if item.isfile() and name in wanted and item.size < 16 * 1024 * 1024:
                        raw = stream.extractfile(item).read()
                        if hashlib.sha256(raw).hexdigest() == wanted[name]:
                            found[name] = raw
            if len(found) == 2:
                break
    if set(found) != set(wanted):
        raise ValueError("EXACT_HISTORICAL_MANIFEST_AND_STATUS_REQUIRED_NO_RECONSTRUCTION")
    target = Path(repo) / "data/processed/benchmark/p2/internvl3" / OLD_ID
    target.mkdir(parents=True, exist_ok=False)
    for name, raw in found.items():
        with (target / name).open("xb") as stream:
            stream.write(raw)
        if digest_file(target / name) != wanted[name]:
            raise ValueError("HISTORICAL_COPY_SHA_MISMATCH")
    return target


def restore_model(repo, source):
    from .internvl3_snapshot import CACHE, REPOSITORY, REVISION, load_plan, verify_snapshot
    source = Path(source)
    candidates = list(source.rglob(REVISION)) if source.is_dir() else []
    snapshots = [p for p in candidates if p.is_dir() and (p / "model.safetensors").is_file()]
    if not snapshots:
        packs = [source] if source.is_file() else archives(source)
        matches = []
        for pack in packs:
            with tarfile.open(pack, "r:*") as stream:
                if any(PurePosixPath(i.name).parts[-2:] == (REVISION, "model.safetensors")
                       for i in stream):
                    matches.append(pack)
        if len(matches) != 1:
            raise ValueError("EXACT_EXISTING_MODEL_PREP_OUTPUT_REQUIRED_NO_DOWNLOAD")
        extracted = safe_extract(matches[0], Path(repo) / "data/processed/p21_restore/model")
        snapshots = [p for p in extracted.rglob(REVISION)
                     if p.is_dir() and (p / "model.safetensors").is_file()]
    if len(snapshots) != 1:
        raise ValueError("AMBIGUOUS_EXISTING_SNAPSHOT_SELECT_EXACT_INPUT")
    target = Path(repo) / CACHE / REPOSITORY / "snapshots" / REVISION
    target.mkdir(parents=True, exist_ok=False)
    # Materialize each exact allowed snapshot file; historical source is untouched.
    for item in load_plan(repo)["snapshot_files"]:
        old = snapshots[0] / item["path"]
        new = target / item["path"]
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, new)
    return verify_snapshot(target, repo=repo)


def runtime_interpreter(repo, source, *, site_packages=None):
    """Reuse existing exact runtime; no pip, uv, downloads or fallback install."""
    from .internvl3_snapshot import load_plan, OFFLINE_ENV
    software = load_plan(repo)["software"]
    source = Path(source)
    env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0"}
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    probe = ("import importlib.metadata as m,json,platform; expected=" + repr(software)
             + "; actual={k:platform.python_version() if k=='python' else m.version(k) for k in expected};"
             + "print(json.dumps(actual,sort_keys=True)); raise SystemExit(0 if actual==expected else 2)")

    def select(root):
        paths = [root] if root.is_file() and root.name in {"python", "python3", "python3.11"} else [
            p for p in root.rglob("python*")
            if p.name in {"python", "python3", "python3.11"} and p.parent.name == "bin" and p.is_file()]
        # Multiple executable aliases in one venv are equivalent. Prefer bin/python.
        if site_packages is not None:
            sites = [Path(site_packages)]
        elif root.is_dir():
            sites = [None] + sorted(p for p in root.rglob("site-packages")
                                    if p.is_dir() and p.parent.name == "python3.11")
        else:
            sites = [None]
        observed = {}
        for path in sorted(paths, key=lambda p: (p.name != "python", str(p))):
            for site in sites:
                child_env = dict(env)
                if site is not None:
                    child_env["PYTHONPATH"] = str(site)
                try:
                    result = subprocess.run([str(path), "-c", probe], env=child_env, capture_output=True,
                                            text=True, timeout=60, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    continue
                if result.returncode == 0:
                    # Alias paths in a venv and its underlying managed Python
                    # may resolve to the same executable. One exact site tree
                    # is still required; multiple different matches fail closed.
                    key = (path.resolve(), site.resolve() if site else None)
                    observed.setdefault(key, {"python": str(path),
                                              "site_packages": str(site) if site else None,
                                              "software_versions": json.loads(result.stdout)})
        # Prefer a fully working venv without PYTHONPATH over its standalone
        # equivalent. Different package trees remain an explicit ambiguity.
        direct = [v for v in observed.values() if v["site_packages"] is None]
        if len(direct) == 1:
            return direct[0]
        if len(observed) > 1:
            raise ValueError("AMBIGUOUS_EXACT_RUNTIME_SELECT_INTERPRETER_INPUT")
        return next(iter(observed.values()), None)

    interpreter = select(source) if source.is_dir() or source.name.startswith("python") else None
    if interpreter:
        return interpreter
    packs = [source] if source.is_file() else archives(source)
    candidates = []
    for pack in packs:
        with tarfile.open(pack, "r:*") as stream:
            if any(PurePosixPath(i.name).name == "pyvenv.cfg"
                   or PurePosixPath(i.name).parts[-2:] == ("bin", "python3.11") for i in stream):
                candidates.append(pack)
    if not candidates:
        raise ValueError("EXACT_REUSABLE_RUNTIME_ARCHIVE_REQUIRED_NO_REBUILD")
    # A Prep output may store managed Python and venv in separate archives.
    # Preserve both layouts and use exact metadata probing to select one runtime.
    restored = Path(repo) / "data/processed/p21_restore/runtime"
    for index, pack in enumerate(candidates):
        safe_extract(pack, restored / ("part-" + str(index)), skip_external_runtime_links=True)
    interpreter = select(restored)
    if interpreter is None:
        raise ValueError("EXISTING_RUNTIME_NOT_RELOCATABLE_OR_PIN_MISMATCH_NO_REBUILD")
    return interpreter


def run_offline(repo, inputs, settings, output):
    """Restore existing outputs, launch one child, package in an outer finally."""
    repo, inputs, output = Path(repo), Path(inputs), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    failure = None
    try:
        if settings.get("kaggle_internet_off_confirmed") is not True:
            raise PermissionError("KAGGLE_SETTINGS_INTERNET_OFF_CONFIRMATION_REQUIRED")
        # Venue Internet OFF is an external setting. Offline environment + Python
        # network denial are additional boundaries, not an OS firewall claim.
        from .internvl3_snapshot import OFFLINE_ENV, network_denied
        receipt = strict_json((repo / RECEIPT).read_bytes())
        if receipt["confirmation"]["final_merge_sha"] != settings["final_merge_sha"]:
            raise PermissionError("OFFLINE_SOURCE_MUST_EQUAL_CONFIRMED_FINAL_MERGE")
        with network_denied():
            verify_source(repo, receipt["confirmation"])
            from .p2_preflight import static_preflight
            preflight = static_preflight(repo)
            if preflight.get("effective_authorization") is not True or preflight.get("models") != ["internvl3"]:
                raise PermissionError("EFFECTIVE_V4_PREFLIGHT_REQUIRED")
            old_root = restore_history(repo, inputs, settings.get("historical_results_input", ""))
            from .p21_authority import verify_lineage
            from .p2_harness import authorize_production
            _, authority = authorize_production(repo)
            # The harness repeats this before actual dataset/runtime access.
            reference = {"run_id": OLD_ID, "run_manifest_sha256": OLD_MANIFEST}
            verify_lineage(repo, authority, "internvl3", RUN_ID, reference)
            model_input = attachment(inputs, settings.get("source_model_input", ""),
                                     ("internvl3", "source", "model", "fix", "v2"))
            model_receipt = restore_model(repo, model_input)
            runtime_input = attachment(inputs, settings.get("runtime_input", ""),
                                       ("internvl3", "runtime", "fix", "v2"))
            site_packages = (input_path(inputs, settings["runtime_site_packages"])
                             if settings.get("runtime_site_packages") else None)
            runtime = runtime_interpreter(repo, runtime_input, site_packages=site_packages)
            dataset_root, manifest, provenance = locate_dataset(
                repo, inputs, settings.get("dataset_root", ""), settings.get("manifest_path", ""),
                settings.get("provenance_path", ""))
            runtime_receipt = {**runtime, "path_base": "REPOSITORY_ROOT"}
            for name in ("python", "site_packages"):
                runtime_receipt[name] = (os.path.relpath(runtime[name], repo).replace("\\", "/")
                                         if runtime[name] is not None else None)
            launch = {"schema_version": "p21-kaggle-launch-v1", "run_id": RUN_ID,
                      "final_merge_sha": settings["final_merge_sha"], "preflight": preflight,
                      "model_snapshot": model_receipt, "runtime": runtime_receipt,
                      "previous_manifest_sha256": digest_file(old_root / "run_manifest.json"),
                      "previous_status_sha256": digest_file(old_root / "run_status.json"),
                      "cuda_visible_devices_before_child_start": "0", "production_attempts": 1,
                      "internet_off_owner_attestation": True}
            write_new_json(repo / "data/processed/p21_kaggle/launch_receipt.json", launch)
        env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0"}
        env.pop("PYTHONHOME", None)
        env["PYTHONPATH"] = str(repo) + (os.pathsep + runtime["site_packages"] if runtime["site_packages"] else "")
        command = [runtime["python"], "-m", "safeshift.runners.p21_kaggle", "--repo", str(repo),
                   "--dataset-root", str(dataset_root), "--manifest-path", manifest, "--provenance-path", provenance]
        # This is the sole model-production subprocess. Discovery probes above
        # inspect distribution metadata only; they never import torch or infer.
        with (output / "production_child.log").open("x", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=repo, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, bufsize=1)
            try:
                for line in process.stdout:
                    print(line, end="", flush=True)
                    log.write(line)
                    log.flush()
                code = process.wait()
            except BaseException:
                process.terminate()
                process.wait()
                raise
        if code:
            failure = {"stage": "PRODUCTION_CHILD", "returncode": code}
    except BaseException as exc:
        failure = {"stage": "OWNER_PREFLIGHT_OR_LAUNCH", "type": type(exc).__name__, "message": str(exc)}
    finally:
        summary = package_result(repo, output, failure)
    return summary


def locate_dataset(repo, inputs, dataset="", manifest="", provenance=""):
    """Select original owner attachments; validate all bytes in production_run."""
    from safeshift.data.p2_execution import FINGERPRINT, MANIFEST_SHA
    inputs = Path(inputs)
    if dataset:
        dataset_root = input_path(inputs, dataset)
    else:
        candidates = [p for p in inputs.rglob("DATA_PATH") if p.parent.name == "train"
                      and (p.parent.parent / "test/DATA_PATH").is_dir()]
        if len(candidates) != 1:
            raise ValueError("SELECT_EXACT_INSPECSAFE_DATASET_ROOT")
        dataset_root = candidates[0].parent.parent
    if manifest:
        source_manifest = input_path(inputs, manifest)
    else:
        candidates = [p for p in inputs.rglob("*.csv") if digest_file(p) == MANIFEST_SHA]
        if len(candidates) != 1:
            raise ValueError("SELECT_EXACT_HASH_PINNED_MANIFEST")
        source_manifest = candidates[0]
    if provenance:
        source_provenance = input_path(inputs, provenance)
    else:
        candidates = []
        for path in inputs.rglob("*.json"):
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            try:
                item = strict_json(path.read_bytes())
            except (ValueError, UnicodeError):
                continue
            if (isinstance(item, dict) and item.get("dataset") == "InspecSafe-V1"
                    and item.get("input_sha256") == FINGERPRINT
                    and item.get("output_sha256") == MANIFEST_SHA):
                candidates.append(path)
        if len(candidates) != 1:
            raise ValueError("SELECT_EXACT_DATASET_PROVENANCE")
        source_provenance = candidates[0]
    if (digest_file(source_manifest) != MANIFEST_SHA
            or strict_json(source_provenance.read_bytes()).get("input_sha256") != FINGERPRINT):
        raise ValueError("EXACT_DATASET_MANIFEST_AND_FINGERPRINT_REQUIRED")
    # These are owner input locators, not committed machine paths or model payload.
    # Keep repository metadata paths relative; original dataset remains read-only.
    target = Path(repo) / "data/processed/p21_kaggle/inputs"
    target.mkdir(parents=True, exist_ok=False)
    for name, source in (("dataset_manifest.csv", source_manifest), ("dataset_provenance.json", source_provenance)):
        shutil.copyfile(source, target / name)
    return dataset_root, "data/processed/p21_kaggle/inputs/dataset_manifest.csv", "data/processed/p21_kaggle/inputs/dataset_provenance.json"


def result_summary(run_root, failure=None):
    path = Path(run_root) / "run_status.json"
    counts = {name: 0 for name in STATUSES}
    if path.is_file():
        status = strict_json(path.read_bytes())
        samples = status["samples"]
        if (type(samples) is not dict or len(samples) != 1254
                or any(value not in STATUSES for value in samples.values())):
            raise ValueError("CANONICAL_RUN_STATUS_ACCOUNTING_INVALID")
        counts.update(Counter(samples.values()))
        state = status["status"]
        failure = failure or status.get("failure")
    else:
        counts["NOT_ATTEMPTED"] = 1254
        state = "PREFLIGHT_OR_PROCESS_FAILED_NO_FINAL_RUN_STATUS"
        # If a process died before durable final status, do not invent sample
        # statuses from partial artifacts. Explicitly mark accounting unknown.
        if Path(run_root).exists():
            counts = {name: None for name in STATUSES}
    zero = counts["SUCCESS"] == 0 if counts["SUCCESS"] is not None else None
    return {"run_id": RUN_ID, "protocol_version": "P2.1", "execution_status": state,
            **counts, "zero_canonical_yield": zero, "failure": failure,
            "sample_accounting_known": counts["SUCCESS"] is not None,
            "stop_before_shards_1_3": state != "COMPLETED" or zero is not False}


def package_result(repo, output, failure=None):
    """Always publish a wrapper report and available bytes, including FAILED."""
    repo, output = Path(repo), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    run_root = repo / "data/processed/benchmark/p2/internvl3" / RUN_ID
    try:
        summary = result_summary(run_root, failure)
    except (ValueError, KeyError, OSError) as exc:
        summary = {"run_id": RUN_ID, "protocol_version": "P2.1", "execution_status": "STATUS_INTEGRITY_FAILURE",
                   **{k: None for k in STATUSES}, "zero_canonical_yield": None,
                   "sample_accounting_known": False, "stop_before_shards_1_3": True,
                   "failure": {"type": type(exc).__name__, "message": str(exc)}}
    write_new_json(output / "owner_result_summary.json", summary)
    archive = output / (RUN_ID + "_results.tar.gz")
    with tarfile.open(archive, "x:gz") as stream:
        stream.add(output / "owner_result_summary.json", arcname="owner_result_summary.json")
        if run_root.exists():
            stream.add(run_root, arcname="run/" + RUN_ID)
        for relative in (RECEIPT, "data/processed/p21_kaggle/launch_receipt.json"):
            path = repo / relative
            if path.is_file():
                stream.add(path, arcname=PurePosixPath(relative).name)
        log = output / "production_child.log"
        if log.is_file():
            stream.add(log, arcname=log.name)
    write_new_json(output / "result_package_sha256.json", {"archive": archive.name, "sha256": digest_file(archive)})
    print(json.dumps(summary, sort_keys=True, indent=2))
    print("RESULT_PACKAGE=" + str(archive))
    return summary


def production_child(repo, dataset_root, manifest_path, provenance_path):
    """Exactly one harness call; no loop/retry, no new model/runtime behavior."""
    repo = Path(repo)
    receipt = strict_json((repo / RECEIPT).read_bytes())
    verify_source(repo, receipt["confirmation"])
    from .p2_harness import production_run
    return production_run(repo=repo, model="internvl3", run_id=RUN_ID, shard_count=4, shard_index=0,
                          dataset_root=dataset_root, manifest_path=repo / manifest_path,
                          provenance_path=repo / provenance_path)


def child_main(argv=None):
    parser = argparse.ArgumentParser(description="Owner-only single P2.1 shard0 call")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--dataset-root", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--provenance-path", required=True)
    args = vars(parser.parse_args(argv))
    try:
        production_child(**args)
    except BaseException as exc:
        print(json.dumps({"owner_child_failure": type(exc).__name__, "message": str(exc)}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(child_main())
