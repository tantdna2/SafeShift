"""Task 5 authority. Drafts/settings/checksums cannot grant execution rights."""
import hashlib
from pathlib import Path
from safeshift.protocol.schema import strict_json
from . import preflight
from .journal import run_path, no_alias

BASE = "747171e011e35bc8995338402a80ba7ea70d8ff7"
AUTHORITY = "configs/pa3/feasibility_authority.v1.json"
ROOT = Path(__file__).resolve().parents[3]
TECHNICAL = {"run_id": "pa3-qwen-technical-first", "mode": "technical",
    "model": "Qwen/Qwen2.5-VL-3B-Instruct",
    "revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
    "precision": "FP16", "attention": "sdpa", "gpu": "T4",
    "prompt": "C1", "method": "PA3", "max_runs": 1, "max_images": 4}

# Seminar-direction decision diagnostic: separate file, scope and grant. It never
# reads or edits AUTHORITY; the technical scope and `pilot: null` stay byte-identical.
DIAGNOSTIC_AUTHORITY = "configs/pa3/seminar_direction_authority.v1.json"
DIAGNOSTIC_BASE = "28ab17b094da91006a785d0b694c4d035db96902"
DIAGNOSTIC = {"run_id": "pa3-qwen-seminar-direction-90", "mode": "seminar-diagnostic",
    "purpose": "EXPLORATORY_SEMINAR_DIRECTION_DECISION_DIAGNOSTIC", "split": "TRAIN",
    "model": TECHNICAL["model"], "revision": TECHNICAL["revision"], "precision": "FP16",
    "attention": "sdpa", "gpu": "T4", "prompt": "C1", "method": "PA3", "batch_size": 1,
    "max_runs": 1, "max_images": 90, "test_access": False, "retry": False,
    "technical_source_commit": "13ea2fba67f36883518db8a2add1b249c951e48e"}
DIAGNOSTIC_GRANT = ("cohort_manifest_sha256", "inference_manifest_sha256", "technical_seal_sha256",
                    "technical_source_bundle_sha256")


def authority(repo, source_commit):
    """Require BASE -> F1 -> authority-only F2 -> standard merge M.

    Owner separately verifies M on audited main; Git topology is not a signature
    attesting human review. No synthetic merge constructed by an owner is valid.
    """
    repo = Path(repo)
    path = repo / AUTHORITY
    if not path.is_file():
        raise PermissionError("PA3_AUTHORITY_NOT_RELEASED")
    value = strict_json(path.read_bytes())
    if set(value) != {"base", "implementation", "technical", "pilot"}:
        raise PermissionError("PA3_AUTHORITY_SCHEMA")
    if value["technical"] != TECHNICAL:
        raise PermissionError("PA3_TECHNICAL_SCOPE_CHANGED")

    try:
        head = preflight.git(repo, "rev-parse", "HEAD").decode()
        parents = preflight.git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if head != source_commit or len(parents) != 3 or parents[1] != value["base"]:
            raise PermissionError("PA3_STANDARD_MERGE_REQUIRED_DRAFT_LOCKED")
        preflight.git(repo, "merge-base", "--is-ancestor", BASE, value["base"])
        f2, f1 = parents[2], value["implementation"]
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f2).decode().split() != [f2, f1]:
            raise PermissionError("PA3_AUTHORITY_PARENT")
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f1).decode().split() != [f1, value["base"]]:
            raise PermissionError("PA3_IMPLEMENTATION_PARENT")
        if preflight.git(repo, "diff", "--name-only", f1, f2).decode() != AUTHORITY:
            raise PermissionError("PA3_AUTHORITY_ONLY_COMMIT_REQUIRED")
        if preflight.git(repo, "rev-parse", head + "^{tree}") != preflight.git(repo, "rev-parse", f2 + "^{tree}"):
            raise PermissionError("PA3_MERGE_TREE_CHANGED")
        if path.read_bytes() != preflight.git_blob(repo, f2, AUTHORITY):
            raise PermissionError("PA3_AUTHORITY_BYTES_CHANGED")
        if preflight.git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise PermissionError("PA3_DIRTY_SOURCE")
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("PA3_SOURCE_PROOF_MISSING") from exc
    return value


def diagnostic_authority(repo, source_commit):
    """Same BASE -> F1 -> authority-only F2 -> standard merge M rule, own file.

    A null grant (this Draft) denies before any Git, data or model access.
    """
    import re
    repo = Path(repo)
    path = repo / DIAGNOSTIC_AUTHORITY
    if not path.is_file():
        raise PermissionError("PA3_DIAGNOSTIC_AUTHORITY_NOT_RELEASED")
    value = strict_json(path.read_bytes())
    if set(value) != {"base", "implementation", "scope", "grant"}:
        raise PermissionError("PA3_DIAGNOSTIC_AUTHORITY_SCHEMA")
    if value["scope"] != DIAGNOSTIC:
        raise PermissionError("PA3_DIAGNOSTIC_SCOPE_CHANGED")
    grant = value["grant"]
    if grant is None:
        raise PermissionError("PA3_DIAGNOSTIC_GRANT_PENDING_RESEARCH_LEAD")
    if (not isinstance(grant, dict) or set(grant) != {*DIAGNOSTIC_GRANT, "approval"}
            or not isinstance(grant["approval"], str) or not grant["approval"].strip()
            or any(type(grant[k]) is not str or not re.fullmatch(r"[0-9a-f]{64}", grant[k]) for k in DIAGNOSTIC_GRANT)):
        raise PermissionError("PA3_DIAGNOSTIC_GRANT_SCHEMA")
    try:
        head = preflight.git(repo, "rev-parse", "HEAD").decode()
        parents = preflight.git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if head != source_commit or len(parents) != 3 or parents[1] != value["base"]:
            raise PermissionError("PA3_DIAGNOSTIC_STANDARD_MERGE_REQUIRED_DRAFT_LOCKED")
        preflight.git(repo, "merge-base", "--is-ancestor", DIAGNOSTIC_BASE, value["base"])
        f2, f1 = parents[2], value["implementation"]
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f2).decode().split() != [f2, f1]:
            raise PermissionError("PA3_DIAGNOSTIC_AUTHORITY_PARENT")
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f1).decode().split() != [f1, value["base"]]:
            raise PermissionError("PA3_DIAGNOSTIC_IMPLEMENTATION_PARENT")
        if preflight.git(repo, "diff", "--name-only", f1, f2).decode() != DIAGNOSTIC_AUTHORITY:
            raise PermissionError("PA3_DIAGNOSTIC_AUTHORITY_ONLY_COMMIT_REQUIRED")
        if preflight.git(repo, "rev-parse", head + "^{tree}") != preflight.git(repo, "rev-parse", f2 + "^{tree}"):
            raise PermissionError("PA3_DIAGNOSTIC_MERGE_TREE_CHANGED")
        if path.read_bytes() != preflight.git_blob(repo, f2, DIAGNOSTIC_AUTHORITY):
            raise PermissionError("PA3_DIAGNOSTIC_AUTHORITY_BYTES_CHANGED")
        # The old technical grant and `pilot: null` must be untouched by this release.
        if preflight.git_blob(repo, head, AUTHORITY) != preflight.git_blob(repo, DIAGNOSTIC_BASE, AUTHORITY):
            raise PermissionError("PA3_DIAGNOSTIC_CHANGED_PRIOR_AUTHORITY")
        if preflight.git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise PermissionError("PA3_DIAGNOSTIC_DIRTY_SOURCE")
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("PA3_DIAGNOSTIC_SOURCE_PROOF_MISSING") from exc
    return value


def require(operation, settings=None, repo=None):
    settings = settings or {}
    if operation == DIAGNOSTIC["mode"]:
        if settings.get("mode") != DIAGNOSTIC["mode"] or settings.get("run_id") != DIAGNOSTIC["run_id"]:
            raise PermissionError("PA3_DIAGNOSTIC_EXACT_MODE_RUN_REQUIRED")
        if any(settings.get(k) for k in ("dataset_root", "cohort_plan_input", "cohort_plan", "cohort_plan_sha256",
                                         "pilot_manifest_input", "pilot_manifest_sha256")):
            raise PermissionError("PA3_DIAGNOSTIC_HAS_NO_PILOT_OR_COHORT_PLAN_RIGHTS")
        for key in ("model", "revision", "precision", "attention", "gpu", "prompt", "method", "technical_source_commit"):
            if key in settings and settings[key] != DIAGNOSTIC[key]:
                raise PermissionError("PA3_DIAGNOSTIC_SCOPE_MISMATCH:" + key)
        value = diagnostic_authority(repo or ROOT, settings.get("source_commit"))
        for key in DIAGNOSTIC_GRANT:
            if settings.get(key) != value["grant"][key]:
                raise PermissionError("PA3_DIAGNOSTIC_APPROVAL_BINDING:" + key)
        return value
    if operation == "pilot-train":
        if settings.get("mode") != "pilot-train":
            raise PermissionError("PA3_PILOT_MODE_REQUIRED")
        value = authority(repo or ROOT, settings.get("source_commit"))
        grant = value["pilot"]
        fields = {"run_id", "pilot_manifest_sha256", "technical_seal_sha256",
                  "technical_source_commit", "technical_source_bundle_sha256",
                  "model", "revision", "precision", "attention", "gpu", "prompt", "method"}
        if (not isinstance(grant, dict) or set(grant) != fields | {"approval", "max_runs", "max_images"}
                or type(grant["max_runs"]) is not int or grant["max_runs"] != 1
                or type(grant["max_images"]) is not int or grant["max_images"] != 40
                or not isinstance(grant["approval"], str) or not grant["approval"].strip()):
            raise PermissionError("PA3_PILOT_MANIFEST_AND_TECHNICAL_APPROVAL_PENDING")
        if grant["run_id"] != "pa3-qwen-pilot-train-first":
            raise PermissionError("PA3_PILOT_RUN_ID")
        import re
        for key in fields:
            if key in TECHNICAL and key != "run_id" and grant[key] != TECHNICAL[key]:
                raise PermissionError("PA3_PILOT_MODEL_METHOD_CHANGED")
            if key.endswith("sha256") and (type(grant[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", grant[key])):
                raise PermissionError("PA3_PILOT_HASH_REQUIRED")
            if settings.get(key, TECHNICAL.get(key)) != grant[key]:
                raise PermissionError("PA3_PILOT_APPROVAL_BINDING:" + key)
        return value
    if operation != "technical":
        raise PermissionError("PA3_" + operation.upper().replace("-", "_") + "_LOCKED")
    if settings.get("mode") != "technical" or settings.get("run_id") != TECHNICAL["run_id"]:
        raise PermissionError("PA3_EXACT_MODE_RUN_REQUIRED")
    if any(settings.get(k) for k in ("dataset_input", "dataset_root", "cohort_plan_input",
                                    "cohort_plan", "cohort_plan_sha256", "pilot_manifest_input")):
        raise PermissionError("PA3_TECHNICAL_HAS_NO_DATA_RIGHTS")
    for key in ("model", "revision", "precision", "attention", "gpu", "prompt", "method"):
        if key in settings and settings[key] != TECHNICAL[key]:
            raise PermissionError("PA3_SCOPE_MISMATCH:" + key)
    return authority(repo or ROOT, settings.get("source_commit"))


def model_ticket(repo, settings):
    """Consume the single model-load attempt before calling the native loader."""
    require(settings["mode"], settings, repo)
    root = run_path(repo, settings["run_id"])
    if not root.is_dir():
        raise PermissionError("PA3_WORKFLOW_JOURNAL_REQUIRED_BEFORE_MODEL_LOAD")
    tickets = no_alias(root.parent / (root.name + "-tickets"))
    tickets.mkdir(exist_ok=True)
    with (tickets / "model-load.ticket").open("xb") as stream:
        stream.write(settings["source_commit"].encode())


def image_ticket(repo, settings, image, journal, prefix):
    """Exclusive persisted generation tickets; fresh-session replay needs owner ledger."""
    require(settings["mode"], settings, repo)
    if settings["mode"] == DIAGNOSTIC["mode"]:
        from . import seminar
        # Same exact-membership, pixel and one-use ticket rule as the pilot path.
        inputs = Path(settings["diagnostic_inputs_root"])
        samples = seminar.inference_samples(repo, settings)
        if journal.root != run_path(repo, settings["run_id"]):
            raise PermissionError("PA3_EXACT_DIAGNOSTIC_JOURNAL_REQUIRED")
        index = next((i for i in range(len(samples)) if prefix == f"sample-{i:06d}"), None)
        if index is None or journal.read(prefix + ".attempt") != samples[index]:
            raise PermissionError("PA3_DIAGNOSTIC_SAMPLE_IDENTITY")
        with seminar.open_image(repo, settings, samples[index], inputs) as expected:
            if (image.mode, image.size, image.tobytes()) != (expected.mode, expected.size, expected.tobytes()):
                raise PermissionError("PA3_DIAGNOSTIC_IMAGE_PIXELS")
        tickets = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-tickets")
        no_alias(tickets).mkdir(exist_ok=True)
        with (tickets / (prefix + ".ticket")).open("xb") as stream:
            stream.write(samples[index]["image_sha256"].encode())
        return
    if settings["mode"] == "pilot-train":
        from . import pilot
        # The path is supplied by the workflow, but every byte read is gated by
        # the committed manifest hash and exact selected sample membership.
        inputs = Path(settings["pilot_inputs_root"])
        samples = pilot.samples(repo, settings, inputs)
        if journal.root != run_path(repo, settings["run_id"]):
            raise PermissionError("PA3_EXACT_PILOT_JOURNAL_REQUIRED")
        index = next((i for i in range(len(samples)) if prefix == f"sample-{i:06d}"), None)
        if index is None or journal.read(prefix + ".attempt") != samples[index]:
            raise PermissionError("PA3_PILOT_SAMPLE_IDENTITY")
        with pilot.open_image(repo, settings, samples[index], inputs) as expected:
            if (image.mode, image.size, image.tobytes()) != (expected.mode, expected.size, expected.tobytes()):
                raise PermissionError("PA3_PILOT_IMAGE_PIXELS")
        tickets = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-tickets")
        no_alias(tickets).mkdir(exist_ok=True)
        with (tickets / (prefix + ".ticket")).open("xb") as stream:
            stream.write(samples[index]["image_sha256"].encode())
        return
    from safeshift.ls1.experiment import synthetic_samples
    rows = synthetic_samples()
    try:
        if journal.root != run_path(repo, settings["run_id"] + "-qualification"):
            raise PermissionError("PA3_EXACT_JOURNAL_REQUIRED")
        candidates = [i for i, r in enumerate(rows) if image.mode == "RGB" and image.size == (448, 448)
                      and hashlib.sha256(image.tobytes()).hexdigest() == r["image_sha256"]]
        if len(candidates) != 1 or prefix != f"sample-{candidates[0]:06d}":
            raise PermissionError("PA3_EXACT_SYNTHETIC_PIXELS_REQUIRED")
        row = rows[candidates[0]]
        if journal.read(prefix + ".attempt") != {k: v for k, v in row.items() if k != "image"}:
            raise PermissionError("PA3_SYNTHETIC_IDENTITY_MISMATCH")
        tickets = run_path(repo, settings["run_id"]).parent / (settings["run_id"] + "-tickets")
        no_alias(tickets).mkdir(exist_ok=True)
        with (tickets / (prefix + ".ticket")).open("xb") as stream:
            stream.write(row["image_sha256"].encode())
    finally:
        for row in rows:
            row["image"].close()
