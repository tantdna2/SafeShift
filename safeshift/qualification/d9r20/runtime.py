"""Shared offline-only lifecycle for separately authorized future owner runs."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
from unittest.mock import patch

from safeshift.protocol.gate import area, center, contains, iou
from safeshift.protocol.schema import strict_json
from safeshift.qualification.classification import JSON_PROMPT, load_suite
from safeshift.runners.storage import _write_new
from .parsers import PARSERS, classification

ROOT = Path(__file__).resolve().parents[3]
CONFIG = "configs/pre_freeze/d9r20_candidates.v1.json"
SOURCES = "configs/pre_freeze/d9r20_sources.v1.json"
OUTPUT = "data/processed/d9r20"
BASE = "668aae839bbde91b67686d143259e07c8a89608c"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def failure_reason(exc):
    # Retain our fixed diagnostic codes, never arbitrary native exception text
    # (which may include credentials, input text or personal absolute paths).
    message = str(exc)
    if type(exc) is ValueError and re.fullmatch(r"[A-Z][A-Z_0-9]+(?::[A-Za-z0-9_.-]+)?", message):
        return message
    return type(exc).__name__


def encode(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def read(repo, path):
    return strict_json((repo / path).read_bytes())


def relative(repo, path, prefix=None):
    path = Path(path)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("REPOSITORY_RELATIVE_PATH_REQUIRED")
    full = repo / path
    if full.resolve() != full or (prefix and not full.is_relative_to(repo / prefix)):
        raise ValueError("PATH_ESCAPE_OR_ALIAS")
    return full


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True, encoding="utf-8").strip()


def identity(repo):
    if git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("DIRTY_TRACKED_CHECKOUT")
    return {"head": git(repo, "rev-parse", "HEAD"), "main": git(repo, "rev-parse", "origin/main"),
            "base": BASE}


def check_authority(key, candidate, observed, authority, live_identity, environment_hash):
    if observed.get("observation_failure"):
        raise ValueError("FAILED_OBSERVATION_CANNOT_AUTHORIZE_LOAD")
    expected = {"model": key, "model_id": candidate["model_id"], "revision": candidate["revision"],
                "run_id": candidate["run_id"], "base": BASE}
    for name, value in expected.items():
        if authority.get(name) != value or observed.get(name) != value:
            raise ValueError("AUTHORITY_IDENTITY_MISMATCH:" + name)
    if authority.get("execution_authorized") is not True or authority.get("prep_merged") is not True:
        raise ValueError("SEPARATE_POST_MERGE_AUTHORIZATION_REQUIRED")
    if (live_identity["base"] != BASE or live_identity["head"] == BASE
            or live_identity["head"] != live_identity["main"]
            or any(authority.get(n) != live_identity[n] or observed.get(n) != live_identity[n]
                   for n in ("head", "main"))):
        raise ValueError("WRONG_HEAD_OR_MAIN")
    if authority.get("observation_sha256") != environment_hash:
        raise ValueError("OBSERVATION_NOT_APPROVED")
    if not authority.get("research_lead") or not authority.get("review_reference"):
        raise ValueError("RESEARCH_LEAD_REVIEW_REQUIRED")
    if candidate["owner_acceptance_required"] and authority.get("owner_license_accepted") is not True:
        raise ValueError("ACCESS_REQUIRES_OWNER_ACCEPTANCE")
    if authority.get("scope") != "RESOURCE_SMOKE_AND_SINGLE_TARGET_SYNTHETIC_ONLY":
        raise ValueError("NO_PRODUCTION_CALL2_AUTHORITY")


def hash_file(path, algorithm="sha256", git_blob=False):
    h = hashlib.new(algorithm)
    if git_blob:
        h.update(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def snapshot_inventory(repo, key, snapshot):
    config, sources = read(repo, CONFIG), read(repo, SOURCES)
    candidate, source = config["models"][key], sources["models"][key]
    # A local directory identity alone is insufficient: verify every required byte.
    folder = relative(repo, snapshot, ".cache")
    if folder.name != candidate["revision"] or folder.parent.name != key:
        raise ValueError("EXACT_SNAPSHOT_DIRECTORY_REQUIRED")
    if (source["model_id"], source["revision"]) != (candidate["model_id"], candidate["revision"]):
        raise ValueError("SOURCE_REVISION_MISMATCH")
    records = []
    for item in source["files"]:
        name = item["rfilename"]
        if not name.endswith((".py", ".json", ".jsonl", ".txt", ".model", ".tiktoken", ".safetensors")):
            continue
        path = relative(repo, f"{snapshot}/{name}", ".cache")
        if not path.is_file() or path.stat().st_size != item["size"]:
            raise ValueError("SNAPSHOT_MISSING_OR_SIZE:" + name)
        sha = hash_file(path)
        if "lfs" in item:
            good = sha == item["lfs"]["sha256"]
        else:
            good = hash_file(path, "sha1", git_blob=True) == item["blobId"]
        if not good:
            raise ValueError("SNAPSHOT_HASH:" + name)
        records.append({"file": name, "sha256": sha, "size_bytes": item["size"]})
    if not any(r["file"].endswith(".safetensors") for r in records):
        raise ValueError("NO_WEIGHTS_IN_VERIFIED_INVENTORY")
    return {"path": snapshot, "files": records, "size_bytes": sum(r["size_bytes"] for r in records)}


def environment(key, candidate):
    import torch  # invoked only by explicit future observe/run CLI, never by tests
    versions = {name: metadata.version(name) for name in candidate["environment"] if name not in ("python", "cuda")}
    expected = candidate["environment"]
    if platform.python_version_tuple()[:2] != tuple(expected["python"].split(".")):
        raise ValueError("PYTHON_VERSION")
    for name, version in versions.items():
        if version.split("+")[0] != expected[name]:
            raise ValueError("DEPENDENCY_VERSION:" + name)
    if torch.version.cuda != expected["cuda"]:
        raise ValueError("CUDA_RUNTIME_VERSION")
    count = torch.cuda.device_count()
    if count != 1:
        raise ValueError("EXACT_SINGLE_T4_REQUIRED")
    props = torch.cuda.get_device_properties(0)
    gpu = {"name": props.name, "count": count, "compute_capability": list(torch.cuda.get_device_capability(0)),
           "total_memory": props.total_memory, "cuda": torch.version.cuda, "device": "cuda:0"}
    if (gpu["name"] not in ("T4", "Tesla T4", "NVIDIA T4") or gpu["compute_capability"] != [7, 5]
            or not 14 * 2**30 <= props.total_memory <= 16 * 2**30):
        raise ValueError("EXACT_SINGLE_T4_16GB_REQUIRED")
    if key == "ovis":
        try:
            metadata.version("flash-attn")
        except metadata.PackageNotFoundError:
            pass
        else:
            raise ValueError("OVIS_PREDECLARED_SDPA_REQUIRES_FLASH_ATTN_ABSENT")
    driver = subprocess.check_output(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True).strip()
    return {"python": platform.python_version(), "platform": platform.platform(), "dependencies": versions,
            "all_distributions": sorted((d.metadata["Name"], d.version) for d in metadata.distributions()),
            "gpu": gpu, "driver": driver, "torch": torch.__version__}


def observe(repo, key, snapshot):
    config = read(repo, CONFIG)
    candidate = config["models"][key]
    record = {"schema": "d9r20-observation-v1", "model": key, "model_id": candidate["model_id"],
              "revision": candidate["revision"], "run_id": candidate["run_id"], "base": BASE,
              "model_load_attempts": 0, "INSPECSAFE": "NOT_RUN", "observation_failure": None}
    phase = "IDENTITY"
    try:
        record.update(identity(repo))
        phase = "ENVIRONMENT"
        record["environment"] = environment(key, candidate)
        phase = "SNAPSHOT"
        record["snapshot"] = snapshot_inventory(repo, key, snapshot)
    except Exception as exc:
        record["observation_failure"] = {"phase": phase, "reason": failure_reason(exc),
                                          "resource_result": "NOT_QUALIFIED_NO_LOAD"}
    record["config_sha256"] = digest((repo / CONFIG).read_bytes())
    record["sources_sha256"] = digest((repo / SOURCES).read_bytes())
    return record


def prepared_cases(repo, key):
    """No supplied image paths or GT-conditioned query; source only fixed manifests."""
    config = read(repo, CONFIG)
    candidate = config["models"][key]
    cases = []
    for case, raw in load_suite(repo):
        prompt = JSON_PROMPT if key != "kosmos" else "Question: " + JSON_PROMPT + " Answer:"
        cases.append({**case, "call_id": case["case_id"], "task": "classification", "prompt": prompt, "raw_image": raw})
    manifest = read(repo, config["grounding"]["manifest"])
    if manifest["source_kind"] != "synthetic" or manifest["statement"] != "NO_INSPECSAFE_CONTENT_USED":
        raise ValueError("SYNTHETIC_ONLY")
    # Always the same target, even on target-absent cases. Added queries are fixed
    # in the PREP contract and confined to a single synthetic image.
    specs = [(c, "red square", "g_" + c["case_id"]) for c in manifest["cases"]]
    last = next(c for c in manifest["cases"] if c["case_id"] == "H_all_four")
    specs += [(last, "green circle", "g_H_green"), (last, "cyan rectangle", "g_H_cyan")]
    for case, target, call_id in specs:
        path = relative(repo, case["image_path"], "data/processed/external_grounding_multicategory_v3/images")
        raw = path.read_bytes()
        if digest(raw) != case["image_sha256"]:
            raise ValueError("SYNTHETIC_IMAGE_HASH")
        cases.append({**case, "target": target, "call_id": call_id, "task": "grounding",
                      "prompt": candidate["grounding_prompt"].format(target=target), "raw_image": raw})
    return cases


def diagnostics(case, detections):
    """Retain all boxes and all pairwise evidence; never select-first or drop extras."""
    targets = [t["bbox"] for t in case["targets"] if t["label"] == case["target"]]
    others = case["distractor_boxes"] + [t["bbox"] for t in case["targets"] if t["label"] != case["target"]]
    edges, boxes = [], []
    for index, detection in enumerate(detections):
        b = detection["bbox"]
        row = {"prediction_index": index, "area": area(b), "full_image": b == [0., 0., 1., 1.],
               "center": center(b), "target_ious": [iou(b, t) for t in targets],
               "target_centers_inside": [contains(t, center(b)) for t in targets],
               "excludes_distractor_centers": all(not contains(b, center(d)) for d in others),
               "giant_box_review": "PENDING_HUMAN_REVIEW"}
        boxes.append(row)
        edges.append([j for j, inside in enumerate(row["target_centers_inside"]) if inside])
    # Deterministic maximum-cardinality center matching for diagnostics only.
    matched = {}
    def augment(i, seen):
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in matched or augment(matched[j], seen):
                matched[j] = i
                return True
        return False
    for index in range(len(detections)):
        augment(index, set())
    witnesses = [b["prediction_index"] for b in boxes if any(b["target_centers_inside"])
                 and b["excludes_distractor_centers"] and not b["full_image"]]
    return {"boxes": boxes, "expected_count": len(targets), "predicted_count": len(detections),
            "center_matching": sorted((j, i) for j, i in matched.items()),
            "unmatched_predictions": [i for i in range(len(detections)) if i not in matched.values()],
            "missed_instances": [j for j in range(len(targets)) if j not in matched],
            "false_positive_count_if_target_absent": len(detections) if not targets else None,
            "capability_witness_indices": witnesses, "semantic_errors_do_not_auto_disqualify": True}


def capability_observations(rows):
    by_id = {r["call_id"]: r for r in rows}
    required = ("g_A_1", "g_A_2", "g_H_all_four", "g_H_green", "g_H_cyan")
    evidence = all(by_id.get(i, {}).get("diagnostics", {}).get("capability_witness_indices") for i in required)
    pairs = []
    for left, right, axes in (("g_A_1", "g_A_2", (0,)), ("g_H_all_four", "g_H_green", (0,)),
                              ("g_H_all_four", "g_H_cyan", (0, 1))):
        a, b = by_id.get(left, {}).get("diagnostics", {}), by_id.get(right, {}).get("diagnostics", {})
        tracking = any(all(b["boxes"][j]["center"][axis] > a["boxes"][i]["center"][axis] for axis in axes)
                       for i in a.get("capability_witness_indices", []) for j in b.get("capability_witness_indices", []))
        pairs.append({"calls": [left, right], "tracking_observed": tracking})
    return {"mandatory_sanity_witnesses_observed": bool(evidence), "tracking_pairs": pairs,
            "human_matched_box_no_giant_review": "REQUIRED", "call2": "CALL2_ORCHESTRATION_BLOCKER",
            "eligibility": "PENDING_REVIEW", "automatic_pass": False}


@contextmanager
def offline():
    def reject(*args, **kwargs):
        raise RuntimeError("NETWORK_FORBIDDEN_DURING_OWNER_RUN")
    with patch.object(socket.socket, "connect", reject), patch.object(socket.socket, "connect_ex", reject), \
            patch("socket.create_connection", reject):
        yield


def persisted(path, raw):
    _write_new(path, raw)  # exclusive, flush, fsync; never overwrite
    observed = path.read_bytes()
    if observed != raw:
        raise ValueError("RAW_STORAGE_VERIFICATION_FAILURE")
    return {"file": path.name, "sha256": digest(observed), "size_bytes": len(observed)}


def run_kernel(repo, key, observation, backend, cases, authority=None):
    """Caller must preflight. Backend receives no expected label, GT or past output."""
    config = read(repo, CONFIG)
    candidate = config["models"][key]
    root = relative(repo, f"{OUTPUT}/{candidate['run_id']}", OUTPUT)
    root.mkdir(parents=True, exist_ok=False)  # consumes attempt even on load failure
    report = {"schema": "d9r20-result-v1", "model": key, "model_id": candidate["model_id"],
              "revision": candidate["revision"], "run_id": candidate["run_id"], "observation": observation,
              "authorization": authority,
              "resource": config["resource"], "generation": config["generation"], "seed": config["seed"],
              "load_result": "NOT_ATTEMPTED", "resource_smoke": "NOT_COMPLETED", "calls": [], "failure": None, "model_load_attempts": 0,
              "INSPECSAFE": "NOT_RUN", "PROTOCOL_FREEZE": "PENDING", "participation": "PENDING_RESEARCH_LEAD_DECISION",
              "final_verdict": "PENDING_REVIEW", "automatic_pass": False, "command": " ".join(sys.argv),
              "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    phase = "LOAD"
    try:
        report["model_load_attempts"] = 1
        backend.load()
        report["load_result"] = "LOADED_PLACEMENT_VERIFIED"
        report["memory_after_load"] = backend.memory()
        for case in cases:
            phase = "GENERATE"
            call = {"call_id": case["call_id"], "sample_id": case["case_id"], "task": case["task"],
                    "prompt": case["prompt"], "prompt_sha256": digest(case["prompt"].encode()),
                    "image_sha256": digest(case["raw_image"]), "parse_status": "NOT_ATTEMPTED", "canonical": None,
                    "raw": None, "preparse": None, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
            report["calls"].append(call)
            folder = root / case["call_id"]
            folder.mkdir()
            call["preparse"] = persisted(folder / "preparse.json", encode({**call, "run_id": candidate["run_id"],
                      "model_id": candidate["model_id"], "revision": candidate["revision"],
                      "generation": config["generation"], "seed": config["seed"]}))
            native = backend.generate(case["raw_image"], case["prompt"])
            phase = "RAW_PERSIST"
            call["raw"] = persisted(folder / "native.raw.json", encode(native))
            # Raw IDs, input IDs and generation defaults exist durably BEFORE
            # decode, boundary validation, official postprocessing, or parsing.
            phase = "DECODE"
            decoded = backend.decode(strict_json((folder / "native.raw.json").read_bytes()))
            call["decoded"] = persisted(folder / "decoded.json", encode(decoded))
            report["resource_smoke"] = "LOAD_AND_GENERATION_OBSERVED_NOT_SEMANTIC_PASS"
            call["termination"] = decoded["termination"]
            phase = "PARSE"
            try:
                if decoded["termination"] != "EOS":
                    raise ValueError("TRUNCATED_OR_BAD_TERMINATION")
                text = strict_json((folder / "decoded.json").read_bytes())["text"]
                if case["task"] == "classification":
                    canonical = classification(text)
                    call["semantic_correct"] = canonical["safety_level"] == case["expected_safety_level"]
                else:
                    canonical = PARSERS[key](text, case["target"])
                    call["diagnostics"] = diagnostics(case, canonical)
                call.update(parse_status="SUCCESS", canonical=canonical)
            except (ValueError, TypeError, KeyError) as exc:
                call.update(parse_status="INVALID", parse_reason=str(exc))
            call["memory"] = backend.memory()
            persisted(folder / "result.json", encode(call))
    except Exception as exc:
        # No exception text or credentials/absolute paths in bounded bundle.
        report["failure"] = {"phase": phase, "reason": failure_reason(exc),
                             "resource_result": "RESOURCE_FAIL_NO_GO" if phase in ("LOAD", "GENERATE") else "PIPELINE_FAILURE"}
        if phase == "LOAD":
            report["load_result"] = "FAILED"
    finally:
        try:
            report["peak_memory"] = backend.memory()
        except Exception as exc:
            report["peak_memory"] = {"available": False, "reason": type(exc).__name__}
    report["capability_observations"] = capability_observations(report["calls"])
    report["classification_interface"] = ("OBSERVED_VALID_PENDING_REVIEW" if
        len([r for r in report["calls"] if r["task"] == "classification" and r["parse_status"] == "SUCCESS"]) == 8
        else "NOT_ESTABLISHED")
    report["completed_calls"] = len([r for r in report["calls"] if r["parse_status"] != "NOT_ATTEMPTED"])
    persisted(root / "result.json", encode(report))
    return report
