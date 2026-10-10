"""LS1 orchestration with persisted raw-before-parse and explicit split gates."""

import argparse
from datetime import datetime, timezone
import hashlib
import re
from pathlib import Path

from safeshift.protocol.classification_policy import PROMPT_SHA256, PROMPT_PATH
from safeshift.protocol.p21_schema import parse_classification
from safeshift.protocol.schema import strict_json
from safeshift.data.p2_execution import MANIFEST_SHA, FINGERPRINT, safe_path
from .artifacts import digest, json_bytes, write_json, read_verified, seal
from .core import REFERENCE_SPEC, reference_images, locate_decision, score_decision, calibrate, validate_trace
from .tokenizer import MODELS, t1

METHOD_PATH = "configs/experiments/ls1.v1.json"
SPLIT_EXECUTION_LOCK = "LS1_SPLIT_EXECUTION_LOCKED_PENDING_DEC_LS1_001"


def method_hash(repo):
    return digest(Path(repo) / METHOD_PATH)


def authorize(settings, repo):
    """Must run before tokenizer/runtime imports, dataset reads or artifacts.

    Train/test have no receipt-based authorization while DEC-LS1-001 is pending.
    """
    if settings["model_key"] not in MODELS or settings["mode"] not in ("technical", "train", "test"):
        raise ValueError("SUPPORTED_LS1_MODE_REQUIRED")
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}", settings["run_id"]):
        raise ValueError("SAFE_UNIQUE_RUN_ID_REQUIRED")
    if not re.fullmatch(r"[0-9a-f]{40}", settings["source_commit"]):
        raise ValueError("EXACT_SOURCE_COMMIT_REQUIRED")
    if type(settings.get("protect_level01", False)) is not bool:
        raise ValueError("BOOLEAN_GUARD_REQUIRED")
    if settings["mode"] == "technical":
        if settings.get("protect_level01", False):
            raise ValueError("TECHNICAL_MODE_USES_DEFAULT_NO_GUARD")
        return None
    raise PermissionError(SPLIT_EXECUTION_LOCK)


def synthetic_samples():
    """Four generated technical images, no semantic ground truth or benchmark."""
    from PIL import Image, ImageDraw
    images = []
    for name, color in (("red_square", "red"), ("blue_circle", "blue"),
                        ("green_triangle", "green"), ("yellow_lines", "yellow")):
        image = Image.new("RGB", (448, 448), (220, 220, 220))
        draw = ImageDraw.Draw(image)
        if name == "red_square":
            draw.rectangle((120, 120, 328, 328), fill=color)
        elif name == "blue_circle":
            draw.ellipse((120, 120, 328, 328), fill=color)
        elif name == "green_triangle":
            draw.polygon([(224, 100), (100, 348), (348, 348)], fill=color)
        else:
            for y in range(80, 400, 60):
                draw.line((40, y, 408, y), fill=color, width=10)
        images.append({"sample_id": "ls1-synthetic-" + name, "image": image,
                       "image_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                       "hash_scope": "RGB_PIXEL_BYTES_448x448"})
    return images


def dataset_samples(settings):
    """Direct calls cannot bypass the pending-study split execution lock."""
    raise PermissionError(SPLIT_EXECUTION_LOCK)


def open_sample(row, dataset_root=None):
    if "image" in row:
        return row["image"].copy()
    from PIL import Image
    import warnings
    path = safe_path(dataset_root, row["image_locator"])
    if digest(path) != row["image_sha256"]:
        raise ValueError("IMAGE_CHANGED_AFTER_PREFLIGHT")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise ValueError("ONE_STILL_IMAGE_REQUIRED")
            image.load()
            return image.convert("RGB")


def reference_scores(scorer, prefix, token_ids, root, context):
    key = hashlib.sha256(json_bytes(prefix)).hexdigest()
    directory = root / "references" / key
    directory.mkdir(parents=True, exist_ok=False)
    scores = {}
    images = reference_images()
    try:
        for name, pixel in REFERENCE_SPEC:
            image = images[name]
            raw = {**scorer.generate(image, prefix), "context": context,
                   "call_kind": "REFERENCE_FORCED_PREFIX_ONE_TOKEN", "sample_id": "reference-" + name,
                   "prefix_ids": list(prefix), "pixel_value": pixel, "image_mode": "RGB", "image_size": [448, 448],
                   "image_pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest()}
            path = directory / (name + ".raw.json")
            receipt = write_json(path, raw)
            saved = read_verified(path, receipt)
            if saved["forced_assistant_prefix_ids"] != list(prefix) or len(saved["steps"]) != 1:
                raise ValueError("REFERENCE_PREFIX_OR_STEP_MISMATCH")
            row = saved["steps"][0]
            if (any(row["raw"]["nonfinite"].values()) or row["processed"]["nonfinite"]["nan"]
                    or row["processed"]["nonfinite"]["positive_inf"]
                    or row["generated_token"] != row["processed"]["argmax_id"]):
                raise ValueError("INVALID_REFERENCE_LOGITS_OR_SELECTION")
            scores[name] = [row["raw"]["candidate_values"][str(i)] for i in token_ids]
        return scores, key
    finally:
        for image in images.values():
            image.close()


def run(repo, settings, *, scorer_factory=None, tokenizer_check=t1):
    repo = Path(repo).absolute()
    authorize(settings, repo)
    root = safe_path(repo, "data/processed/ls1/runs/" + settings["run_id"])
    root.mkdir(parents=True, exist_ok=False)  # refusal persists even for failed attempts
    results, images, scorer = [], [], None
    try:
        context = {"protocol": "LS1", "version": "ls1-v1", "run_id": settings["run_id"],
                   "mode": settings["mode"], "source_commit": settings["source_commit"],
                   "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                   "model_key": settings["model_key"], "model_id": MODELS[settings["model_key"]][0],
                   "model_revision": MODELS[settings["model_key"]][1], "prompt_sha256": PROMPT_SHA256,
                   "method_sha256": method_hash(repo), "seed": None,
                   "command": "python -m safeshift.ls1.experiment --settings <input-relative-settings>",
                   "artifact_root": root.relative_to(repo).as_posix()}
        prompt = (repo / PROMPT_PATH).read_bytes()
        if hashlib.sha256(prompt).hexdigest() != PROMPT_SHA256:
            raise ValueError("OFFICIAL_C1_CHANGED")
        write_json(root / "run_manifest.json", {**context, "method": strict_json((repo / METHOD_PATH).read_bytes()),
                   "prompt": prompt.decode(),
                   "protect_level01": settings.get("protect_level01", False)})
        evidence, tokenizer = tokenizer_check(settings["model_key"], settings.get("snapshot"), repo=repo)
        write_json(root / "t1.json", evidence)
        if evidence["status"] != "PASS":
            raise RuntimeError("T1_" + evidence["status"])
        if settings["mode"] == "technical":
            images, gt = synthetic_samples(), None
        else:
            images, gt = dataset_samples(settings)
        write_json(root / "cohort.json", {"source_kind": "SYNTHETIC" if gt is None else "INSPECSAFE",
            "mode": settings["mode"], "source_manifest_sha256": MANIFEST_SHA if gt else None,
            "dataset_fingerprint": FINGERPRINT if gt else None,
            "rows": [{k: v for k, v in row.items() if k != "image"} for row in images]})
        if scorer_factory is None:
            from .runtime import NativeScorer
            scorer_factory = NativeScorer
        scorer = scorer_factory(settings["model_key"], settings["snapshot"], tokenizer,
                                evidence["candidate_token_ids"], repo=repo)
        write_json(root / "runtime.json", {"hardware": scorer.hardware, "software": scorer.software,
                   "snapshot": scorer.snapshot_receipt, "source_receipt": settings.get("source_receipt"),
                   "runtime_input_receipt": settings.get("runtime_input_receipt")})
        reference_cache = {}
        eos_ids = scorer.config.eos_token_id
        eos_ids = [eos_ids] if isinstance(eos_ids, int) else (eos_ids or [])
        for row in images:
            sid = row["sample_id"]
            call = hashlib.sha256(sid.encode()).hexdigest()
            directory = root / "calls" / call
            image = open_sample(row, settings.get("dataset_root"))
            try:
                raw = {**scorer.generate(image), "context": context, "sample_id": sid,
                       "image_sha256": row["image_sha256"], "call_id": call, "call_kind": "SAMPLE_GREEDY"}
            finally:
                image.close()
            raw_path = directory / "response.raw.json"
            receipt = write_json(raw_path, raw)
            saved = read_verified(raw_path, receipt)  # only this object enters parsing/scoring
            result = {"sample_id": sid, "status": "INVALID", "modes": None, "errors": [],
                      "raw_path": raw_path.relative_to(root).as_posix(), "raw_receipt": receipt}
            parsed = parse_classification(saved["decoded_text"])
            result.update(parser_version="p21-strict-classification-v1", generated_parse_status=parsed.status,
                          format_wrapper_detected=parsed.format_wrapper_detected)
            try:
                validate_trace(saved)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                result["errors"] = [str(exc)]
                write_json(directory / "result.json", result)
                results.append(result)
                raise RuntimeError("LS1_GENERATION_CONDITION_FAILURE_STOP_NO_RETRY") from exc
            if not parsed.success:
                result["errors"] = list(parsed.errors)
                write_json(directory / "result.json", result)
                results.append(result)
                continue
            try:
                mapping = locate_decision(tokenizer, saved["decoded_text"], saved["continuation_ids"], eos_ids)
                score = score_decision(saved, mapping)
                key = hashlib.sha256(json_bytes(mapping["prefix_ids"])).hexdigest()
                if key not in reference_cache:
                    ref_scores, ref_key = reference_scores(scorer, mapping["prefix_ids"], mapping["token_ids"], root, context)
                    reference_cache[key] = (ref_scores, ref_key, mapping["token_ids"])
                refs, ref_key, ref_ids = reference_cache[key]
                if ref_ids != mapping["token_ids"]:
                    raise ValueError("REFERENCE_CANDIDATE_IDS_CHANGED")
                modes = calibrate(score["raw_label_logits"], refs, protect_level01=settings.get("protect_level01", False))
                result.update(status="SUCCESS", score=score, modes=modes, reference_key=ref_key)
            except (ValueError, KeyError, TypeError, IndexError) as exc:
                result["errors"] = [str(exc)]
                write_json(directory / "result.json", result)
                results.append(result)
                raise RuntimeError("LS1_TECHNICAL_CONDITION_FAILURE_STOP_NO_RETRY") from exc
            write_json(directory / "result.json", result)
            results.append(result)
        write_json(root / "results.json", results)
        if gt is not None:
            from .evaluate import report
            write_json(root / "evaluation.json", report(results, gt))
        write_json(root / "run_status.json", {"status": "FINISHED", "protocol": "LS1", "total_n": len(images),
                   "scored_n": sum(r["status"] == "SUCCESS" for r in results),
                   "invalid_n": sum(r["status"] == "INVALID" for r in results),
                   "performance_claim": "NOT_EVALUATED_TECHNICAL_MODE" if gt is None else "EXPLORATORY_ONLY"})
    except BaseException as exc:
        write_json(root / "run_failure.json", {"status": "STOPPED", "exception_type": type(exc).__name__,
                   "scored_or_invalid_n": len(results), "results": results, "retry_permitted": False})
        raise
    finally:
        for row in images:
            if "image" in row:
                row["image"].close()
        seal(root)
    return root


def main():
    import os
    from safeshift.runners.internvl3_snapshot import OFFLINE_ENV, network_denied
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    os.environ.update(OFFLINE_ENV)
    settings = strict_json(args.settings.read_bytes())
    with network_denied():
        print(run(args.repo, settings))


if __name__ == "__main__":
    main()
