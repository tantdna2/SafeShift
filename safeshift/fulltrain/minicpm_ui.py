"""Owner UI capsule over the shared fresh171 controller; no new model loop.

Capsules bind metadata and custody, never authenticate an execution release.
These V1 public entries stay closed without a capability. The V2 signed release
entrypoint reuses the capsule/history/verifier functions, not a second model loop.
"""
from pathlib import Path
from copy import deepcopy
import os
import shutil
import tempfile
import time

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, write, write_bytes, sha, safe, export, verify_archive
from safeshift.pilot.contract import digest, json_bytes, require_hash
from safeshift import internvl3763_python as py
from . import contract, admission, runtime

MARKER = "safeshift_minicpm_fulltrain_execution.json"
SCHEMA = "safeshift-minicpm-owner-ui-v1"
CHECKPOINT = "nguynanhtn/safeshift-prepare-minicpm4/1"
TRAIN = "nguynanhtn/inspecsafe-v1-kaggle/1"
MASTER = "nguynanhtn/safeshift-pilot-input/1"


def initial(cohort, projection_sha256, resource_policy, *, checkpoint_marker_sha256,
            run_id, attempt_id, job, capsule_ref, max_calls, max_seconds, nested_mounts, repo=ROOT, series=None):
    """Plan metadata only from a separately sealed original-master projection.

    The worker re-derives it from the frozen master; caller metadata confers no
    custody, scientific authority or permission to read images.
    """
    contract.planning.validate_cohort(cohort, projection_sha256)
    from .original_inputs import SCHEMA as ORIGINAL_SCHEMA
    from safeshift.pilot.contract import MASTER_SHA
    binding = {"schema": ORIGINAL_SCHEMA, "master_sha256": MASTER_SHA, "projection_sha256": projection_sha256}
    for name, ref in (("master_dataset", MASTER), ("train_dataset", TRAIN)):
        owner, slug, version = ref.split("/")
        binding[name] = {"ref": owner + "/" + slug, "version": int(version),
            "mount": "datasets/" + owner + "/" + slug if nested_mounts else slug}
    campaign = contract.campaign({k: cohort for k in contract.planning.MODELS}, projection_sha256, series=series)
    plan = contract.plan(campaign, cohort, contract.native_identity("minicpm4", repo), [], action="initial",
        run_id=run_id, attempt_id=attempt_id, max_calls=max_calls, max_seconds=max_seconds)
    request = {"model_key": "minicpm4", "source_sha256": digest(contract.source_manifest(repo)),
        "inputs": "/kaggle/input", "work": "/kaggle/working/minicpm-fulltrain", "scratch": "/kaggle/temp/minicpm-fulltrain",
        "original_inputs": binding, "marker_sha256": digest(binding), "projection_sha256": projection_sha256,
        "campaign": campaign, "plan": plan, "history": [], "resource_policy": resource_policy, "repair_case": None,
        "checkpoint_marker_sha256": checkpoint_marker_sha256, "runtime_lock": None, "runtime_lock_sha256": None,
        "software_input": None, "software_marker_sha256": None, "python_input": py.binding()}
    value = {"schema": SCHEMA, "request": request, "cohort": cohort, "ancestors": [], "job": job,
        "capsule_ref": capsule_ref, "input_sources": {"dataset_sources": [TRAIN, MASTER, py.REF, capsule_ref],
        "kernel_sources": [CHECKPOINT]}, "evidence_refs": {k: None for k in ("input_versions", "rights",
            "execution_release", "source_review", "independent_audit", "live_verification")}}
    return validate(value, repo)


def validate(value, repo=ROOT):
    require(type(value) is dict and set(value) == {"schema", "request", "cohort", "ancestors",
        "job", "capsule_ref", "input_sources", "evidence_refs"}, "MINICPM_CAPSULE_FIELDS")
    require(value["schema"] == SCHEMA, "MINICPM_CAPSULE_SCHEMA")
    request = value["request"]
    require(set(request) == admission.UI_REQUEST_FIELDS and request["model_key"] == "minicpm4",
            "MINICPM_UI_REQUEST")
    admission.validate_request(request, repo)
    require(request["inputs"] == "/kaggle/input" and request["work"] == "/kaggle/working/minicpm-fulltrain"
        and request["scratch"] == "/kaggle/temp/minicpm-fulltrain", "MINICPM_KAGGLE_ROOTS")
    # This route pins the retained observed versions; a change needs review.
    for name in ("master_dataset", "train_dataset"):
        require(request["original_inputs"][name]["version"] == 1, "MINICPM_RETAINED_INPUT_VERSION")
    cohort, p = value["cohort"], request["plan"]
    contract.planning.validate_cohort(cohort, request["projection_sha256"])
    require(p["action"] in ("initial", "resume") and request["repair_case"] is None, "UI_NO_IMPLICIT_REPAIR")
    require(p == contract.plan(request["campaign"], cohort, contract.native_identity("minicpm4", repo),
        request["history"], action=p["action"], run_id=p["run_id"], attempt_id=p["attempt_id"],
        max_calls=p["max_calls"], max_seconds=p["max_seconds"]), "MINICPM_UI_PLAN")
    require(len(json_bytes(request)) <= 4 * 2**20, "BOUNDED_EXECUTION_REQUEST")
    import re
    require(type(value["job"]) is str and re.fullmatch(r"nguynanhtn/[A-Za-z0-9_-]+", value["job"]), "OWNER_UI_JOB")
    require(type(value["capsule_ref"]) is str and re.fullmatch(
        r"nguynanhtn/safeshift-minicpm-capsule-[A-Za-z0-9_-]+/1", value["capsule_ref"]), "OWNER_UI_CAPSULE_REF")
    require(value["input_sources"] == {"dataset_sources": [TRAIN, MASTER, py.REF, value["capsule_ref"]],
        "kernel_sources": [CHECKPOINT]}, "MINICPM_EXACT_FIVE_INPUTS")
    require(type(value["evidence_refs"]) is dict and set(value["evidence_refs"]) == {
        "input_versions", "rights", "execution_release", "source_review", "independent_audit", "live_verification"},
        "MINICPM_EVIDENCE_REFERENCES")
    # Missing references stay explicit. Neither nonempty strings nor hashes are approvals.
    require(all(v is None or type(v) is str and 0 < len(v) <= 2048 for v in value["evidence_refs"].values()),
            "BOUNDED_EVIDENCE_REFERENCES")
    ancestors = value["ancestors"]
    require(type(ancestors) is list and len(ancestors) == len(request["history"]) <= 512, "ALL_UI_ANCESTORS_REQUIRED")
    for i, item in enumerate(ancestors):
        require(type(item) is dict and set(item) == {"file", "sha256", "plan_sha256"}
            and item["file"] == f"ancestor-{i:04d}.bin", "EXPLICIT_ANCESTOR_FILE")
        require_hash(item["sha256"])
        require_hash(item["plan_sha256"])
    return value


def pair(path, expected=None):
    path = Path(path)
    snapshot_stat(path)
    require(expected is None or sha(path) == expected, "UI_ARCHIVE_OUTER_SHA")
    side = Path(str(path) + ".sha256.json")
    require(snapshot_stat(side).st_size <= 4096, "UI_SIDECAR_BOUND")
    value = read(side)
    entries = verify_archive(path)
    require(value == {"sha256": sha(path), "members": len(entries) + 1}, "UI_ARCHIVE_SIDECAR")
    return entries


def restore_history(directory, value, work):
    """Explicit complete chain only; unchanged native/raw/archive verifier."""
    history = []
    for item, expected in zip(value["ancestors"], value["request"]["history"]):
        path = safe(directory, item["file"])
        pair(path, item["sha256"])
        from safeshift.pilot.artifacts import import_archive
        with tempfile.TemporaryDirectory() as tmp:
            stage = import_archive(path, Path(tmp) / "attempt")
            require(read(stage / "history.json") == history, "UI_MISSING_OR_REORDERED_ANCESTOR")
        got = runtime.import_history(work, path, item["sha256"], value["cohort"],
            value["request"]["campaign"], item["plan_sha256"])
        require(got == expected, "UI_ANCESTOR_CUSTODY")
        history.append(got)
    return history


def verify_capsule(directory, expected_sha256, repo=ROOT, *, release_ticket=False):
    require_hash(expected_sha256)
    marker = safe(directory, MARKER)
    require(snapshot_stat(marker).st_size <= 64 * 2**20 and sha(marker) == expected_sha256, "UI_CAPSULE_PIN")
    value = validate(read(marker), repo)
    names = {MARKER, *[v["file"] for v in value["ancestors"]],
        *[v["file"] + ".sha256.json" for v in value["ancestors"]]}
    if release_ticket:
        from .minicpm_execution import MARKER as TICKET_MARKER
        names.add(TICKET_MARKER)
    found = set()
    for entry in Path(directory).iterdir():
        require(len(found) < len(names) and entry.name in names, "UI_CAPSULE_EXACT_FILES")
        snapshot_stat(safe(directory, entry.name))
        found.add(entry.name)
    require(found == names, "UI_CAPSULE_EXACT_FILES")
    with tempfile.TemporaryDirectory() as tmp:
        restore_history(directory, value, Path(tmp) / "work")
    return value


def package(value, ancestor_paths, destination, notebook, repo=ROOT):
    """Offline candidate only, never upload, reserve, approve or run a job.

    The notebook callback must build from an exact committed runtime. Private
    dataset contains only marker/history bytes; no TRAIN/checkpoint duplication.
    """
    validate(value, repo)
    require(len(ancestor_paths) == len(value["ancestors"]), "ALL_UI_ANCESTORS_REQUIRED")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    dataset = destination / "dataset"
    dataset.mkdir()
    for src, item in zip(ancestor_paths, value["ancestors"]):
        pair(src, item["sha256"])
        target = safe(dataset, item["file"])
        with Path(src).open("rb") as stream, target.open("xb") as out:
            shutil.copyfileobj(stream, out, 2**20)
            out.flush(); os.fsync(out.fileno())
        write_bytes(Path(str(target) + ".sha256.json"), Path(str(src) + ".sha256.json").read_bytes())
    capsule_sha = write(dataset / MARKER, value)
    verify_capsule(dataset, capsule_sha, repo)
    nb = notebook(capsule_sha)
    write_bytes(destination / "notebook.ipynb", (__import__('json').dumps(nb, indent=1, ensure_ascii=False) + "\n").encode())
    write(destination / "kernel-metadata.json", {"id": value["job"], "title": value["job"].split("/")[1],
        "code_file": "notebook.ipynb", "language": "python", "kernel_type": "notebook", "is_private": True,
        "enable_gpu": True, "enable_tpu": False, "enable_internet": True,
        "competition_sources": [], "model_sources": [], **value["input_sources"]})
    write(destination / "dataset-metadata.json", {"id": value["capsule_ref"].rsplit("/", 1)[0],
        "title": value["capsule_ref"].split("/")[1], "isPrivate": True,
        "description": "Private MiniCPM execution metadata and immutable same-series history; no images or weights.",
        "licenses": [{"name": "other"}]})
    write(destination / "handoff.json", {"status": "CANDIDATE_RELEASE_BLOCKED", "capsule_sha256": capsule_sha,
        "request_sha256": digest(value["request"]), "notebook_sha256": sha(destination / "notebook.ipynb"),
        "input_sources": value["input_sources"], "job": value["job"], "provider_version": 1,
        "native_calls": 0, "scientific_qualified": False, "evidence_refs": value["evidence_refs"]})
    return destination


def run_capsule(inputs, expected_sha256, *, repo=ROOT):
    contract.authorize()  # BEFORE even path conversion/discovery; no grant-file bypass.
    marker = discover(inputs, MARKER)
    value = verify_capsule(marker.parent, expected_sha256, repo)
    owner, slug, _ = value["capsule_ref"].split("/")
    require(marker.parent.relative_to(Path(inputs)).as_posix() in (slug, "datasets/" + owner + "/" + slug),
            "UI_CAPSULE_MOUNT_IDENTITY")
    request = value["request"]
    work, scratch = Path(request["work"]), Path(request["scratch"])
    require(not work.exists() and not scratch.exists(), "UI_FRESH_WORKSPACE_REQUIRED_NO_REPLAY")
    restore_history(marker.parent, value, work)
    work.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=False)
    # request.json outside work avoids UNKNOWN_OUTPUT_BEFORE_SETUP.
    request_file = work.parent / (request["plan"]["run_id"] + "-request.json")
    request_sha = write(request_file, request)
    from .minicpm_notebook import run_request
    return run_request(request_file, request_sha, repo=repo)


def stage_python(request, scratch, output, env, deadline):
    """Reuse exact InternVL transport/extractor/selection, no Python download."""
    require(request["python_input"] == py.binding(), "MINICPM_EXACT_OFFLINE_PYTHON")
    marker = discover(request["inputs"], py.MARKER, limit=128)
    owner, slug, _ = py.REF.split("/")
    require(marker.parent.relative_to(Path(request["inputs"])).as_posix() in
        (slug, "datasets/" + owner + "/" + slug), "PYTHON_INPUT_MOUNT_IDENTITY")
    require(hasattr(os, "statvfs") and os.statvfs(marker.parent).f_flag & os.ST_RDONLY,
            "PYTHON_INPUT_READ_ONLY_REQUIRED")
    require(snapshot_stat(marker).st_size <= 16384 and read(marker) == py.manifest(), "PYTHON_INPUT_MANIFEST")
    require({p.name for p in marker.parent.iterdir()} == {py.MARKER, py.PAYLOAD}, "PYTHON_INPUT_EXACT_FILES")
    lock = py.manifest()["lock"]
    require(shutil.disk_usage(scratch).free >= lock["max_uncompressed_bytes"] + lock["size_bytes"], "PYTHON_INPUT_SCRATCH_SPACE")
    archive = Path(scratch) / py.manifest()["filename"]
    proof = py.decode(marker.parent / py.PAYLOAD, archive, deadline)
    python, extraction = py.train_python.extract(archive, Path(scratch) / "input-cpython3119", lock)
    probe = py.boot.probe_interpreter(python, env)
    require(time.monotonic() < deadline and probe.get("eligible") and probe.get("version") == [3, 11, 9]
        and Path(probe["executable"]).resolve() == python.resolve(), "PYTHON_INPUT_INTERPRETER")
    write(Path(output) / "python-input.json", {"status": "PASS", "ref": py.REF, "python_downloads": 0,
        "proof": proof, "extraction": extraction, "probe": probe})
    return python


def verify_results(value, directory, attempt, supervisor, destination, *, repo=ROOT, memory_required=False):
    """Internal offline verifier, used by collection and synthetic regression.

    A local verification receipt is never COLLECTED, MEASURED or permission.
    """
    validate(value, repo)
    pair(attempt)
    pair(supervisor)
    request, cohort = value["request"], value["cohort"]
    with tempfile.TemporaryDirectory() as tmp:
        from safeshift.pilot.artifacts import import_archive
        work = Path(tmp) / "work"
        restore_history(directory, value, work)
        control = import_archive(supervisor, Path(tmp) / "supervisor")
        require(read(control / "request.json") == request, "UI_SUPERVISOR_REQUEST")
        release = read(control / "release.json")
        require(release["source_sha256"] == request["source_sha256"] and release["diagnostic"] is False
            and release["attempt_observed"] is True and release["scientific_qualified"] is False,
            "UI_SUPERVISOR_BINDING")
        if release["failure"] is None:
            modes = ('admit', 'setup', 'reclaim', 'cpu', 'gpu', 'native') if memory_required else ('admit', 'setup', 'cpu', 'gpu', 'native')
            for mode in modes:
                process = read(control / (mode + "-process.json"))
                require(process["status"] == "EXITED" and process["returncode"] == 0, "UI_STAGE_PROCESS")
                require(read(control / mode / "stage.json") == {"status": "RETURNED", "stage": mode,
                    "request_sha256": digest(request), "source_sha256": request["source_sha256"],
                    "native_attempt_permitted": mode == "native"}, "UI_STAGE_REQUEST")
                if memory_required:
                    require(process.get('group_exit', {}).get('status') == 'NO_LIVE_MEMBERS', 'UI_PROCESS_GROUP_UNVERIFIED')
            if memory_required:
                advice = read(control / 'reclaim/owned-advice.json')
                require(advice['scan_complete'] is True and advice['deleted_files'] == 0
                        and advice['effect'] == 'ADVISORY_NOT_RAM_PROOF', 'UI_OWNED_ADVICE_UNVERIFIED')
                from .memory import complete
                for mode in modes:
                    complete(read(control / mode / 'stage-entry-memory.json'))
                    complete(read(control / mode / 'stage-exit-memory.json'))
                post = read(control / 'reclaim/post-advice-resources.json')
                require(post['memory']['available_bytes'] >= request['resource_policy']['free_ram_mib'] * 2**20,
                        'UI_UNCHANGED_RAM_FLOOR')
        old = import_archive(attempt, Path(tmp) / "result")
        require(read(old / "plan.json") == request["plan"] and read(old / "history.json") == request["history"],
                "UI_ATTEMPT_REQUEST")
        history = runtime.import_history(work, attempt, sha(attempt), cohort, request["campaign"], digest(request["plan"]))
        receipt = read(old / "receipt.json")
        require(receipt["native_calls"] == receipt["observed_native_markers"] <= request["plan"]["max_calls"]
            and receipt["load_attempts"] <= 1 and receipt["loads"] <= 1, "UI_NATIVE_ACCOUNTING")
        require(not (old / "accounting_failure.json").exists(), "UI_ACCOUNTING_UNVERIFIED")
    successful = (release["status"] == "TECHNICAL_STAGES_RETURNED_NOT_RELEASE_AUTHORITY"
        and release["failure"] is None and release["last_stage"] == "native"
        and receipt["stop"] in (None, "ADAPTIVE_TIME_STOP", "ADAPTIVE_STORAGE_STOP"))
    next_history = [*request["history"], history]
    preview = contract.plan(request["campaign"], cohort, request["plan"]["identity"], next_history,
        action="resume", run_id="preview-next", attempt_id="preview-next-attempt",
        max_calls=1, max_seconds=1)
    report = {"status": "LOCAL_VERIFIED_NOT_PROVIDER_AUTHORITY", "continuation": "REVIEW_CAPS_AND_RELEASE" if successful else "STOP_RECONCILE_FAILURE",
        "request_sha256": digest(request), "attempt_sha256": sha(attempt), "supervisor_sha256": sha(supervisor),
        "history": next_history, "counts": preview["counts"], "native_calls": receipt["native_calls"],
        "source_sha256": request["source_sha256"], "scientific_selection": "PENDING", "pooling_allowed": False}
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    write(destination / "verification.json", report)
    return report


def collect(package_dir, attempt, supervisor, destination, *, repo=ROOT, client=None):
    contract.authorize()  # No provider/authentication/raw I/O in this unreleased source.
    package_dir = Path(package_dir)
    handoff = read(package_dir / "handoff.json")
    value = verify_capsule(package_dir / "dataset", handoff["capsule_sha256"], repo)
    require(sha(package_dir / "notebook.ipynb") == handoff["notebook_sha256"], "UI_NOTEBOOK_PIN")
    from scripts.reconcile_train3763_manual import observe_kernel, download_outputs
    from safeshift import internvl3763_operator as operator
    # The same official SDK/Private/latest-version/code/Input check as InternVL.
    # Output pairs are downloaded explicitly by the operator, never globbed.
    client = client if client is not None else operator.api()
    observed = observe_kernel(client, value["job"], 1,
        read(package_dir / "notebook.ipynb"), value["input_sources"])
    # Compare explicit local Output pairs with independently downloaded provider
    # bytes. The shared collector exhausts all pages before any GET and rejects
    # extra/conflicting ZIPs. Local files alone never establish provider custody.
    attempt, supervisor = Path(attempt), Path(supervisor)
    require(attempt.name == value["request"]["plan"]["run_id"] + ".zip", "UI_ATTEMPT_ARCHIVE_NAME")
    require(len(supervisor.stem) == 32 and all(c in "0123456789abcdef" for c in supervisor.stem), "UI_SUPERVISOR_ARCHIVE_NAME")
    download_dir = Path(str(destination) + "-provider")
    download_dir.mkdir(parents=True, exist_ok=False)
    names = {"minicpm-fulltrain/" + attempt.name: attempt,
        "minicpm-fulltrain/supervision/" + supervisor.name: supervisor}
    proof = download_outputs(client, value["job"], 1, attempt, sha(attempt), download_dir, output_pairs=names)
    report = verify_results(value, package_dir / "dataset",
        download_dir / ("minicpm-fulltrain/" + attempt.name),
        download_dir / ("minicpm-fulltrain/supervision/" + supervisor.name), destination, repo=repo)
    write(Path(destination) / "provider.json", observed)
    write(Path(destination) / "provider-output.json", proof)
    return report


def next_capsule(value, report, *, run_id, attempt_id, job, capsule_ref, max_calls, max_seconds):
    """No automatic repair, cap inheritance or job submission."""
    require(report["status"] == "LOCAL_VERIFIED_NOT_PROVIDER_AUTHORITY"
        and report["continuation"] == "REVIEW_CAPS_AND_RELEASE"
        and report["request_sha256"] == digest(value["request"]), "UI_NEXT_REQUIRES_VERIFIED_RESULT")
    result = deepcopy(value)
    request = result["request"]
    request["history"] = report["history"]
    request["plan"] = contract.plan(request["campaign"], result["cohort"], request["plan"]["identity"],
        request["history"], action="resume", run_id=run_id, attempt_id=attempt_id,
        max_calls=max_calls, max_seconds=max_seconds)
    require(request["plan"]["scheduled_ordinals"], "UI_NO_PENDING_SAMPLES")
    result["ancestors"].append({"file": f"ancestor-{len(result['ancestors']):04d}.bin",
        "sha256": report["attempt_sha256"], "plan_sha256": digest(value["request"]["plan"])})
    result.update(job=job, capsule_ref=capsule_ref)
    result["input_sources"]["dataset_sources"][-1] = capsule_ref
    return result
