"""New campaign identity, isolated from historical prediction inheritance.

Hashes bind bytes, not signatures. No caller-controlled field enables execution.
The historical candidate sources/configuration/notebooks are not modified.
"""
from copy import deepcopy
from pathlib import Path

from safeshift.candidates import fulltrain as planning
from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_contract import sources as candidate_sources, config
from safeshift.candidates import minicpm_resampler_fp32 as numerical
from safeshift.pilot.artifacts import sha
from safeshift.pilot.contract import digest, require_hash

BASE = "1acb3ef7c0deadbbde7da0b1c63b71296e3950e5"
DIRECTION = "OWNER_FRESH_FULLTRAIN_ONLY"
SERIES = {key: "fresh171-" + key + "-v1" for key in planning.MODELS}
QWEN = {"id": "Qwen/Qwen3-VL-8B-Instruct",
        "revision": "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"}


def sources(repo=ROOT):
    repo = Path(repo)
    return sorted(set(candidate_sources(repo) + [
        p.relative_to(repo).as_posix() for p in (repo / "safeshift/fulltrain").glob("*.py")]))


def source_manifest(repo=ROOT):
    return {name: sha(Path(repo) / name) for name in sources(repo)}


def descriptor(key):
    require(key in planning.MODELS, "FULLTRAIN_MODEL_KEY")
    if key == "qwen3":
        # A model ID/revision in tracked metadata is not a native release lock.
        return {"model": dict(QWEN), "status": "BLOCKED_NATIVE_CONTRACT",
                "historical_reference_only": {
                    "commit": "31a04e6f7175cca818c63b4de0153246b3f3ecdb",
                    "path": "notes/hnlo_train_v4_20261019.md",
                    "python": "3.12.13", "torch": "2.10.0+cu128", "transformers": "4.57.1",
                    "dtype": "float16", "attention": "sdpa", "max_new_tokens": 32,
                    "placement": "CPU embedding; visual GPU1; layers0-20 GPU0,21-35 GPU1; norm/head GPU1",
                    "transfer_authority": False},
                "missing": ["reviewed_fresh_source_and_checkpoint_allowlist",
                            "effective_generation_preprocessing_precision_and_placement",
                            "pinned_worker_dependencies", "native_raw_and_HNLO_alignment"],
                "historical_predictions_required": False}
    old = config(key, implementation=numerical.ID if key == "minicpm4" else None)
    effective = deepcopy(old["effective_candidate"])
    historical_selection = effective.pop("selection")
    return {"schema": "safeshift-fresh-native-config-v1", "model": effective["model"],
            "status": "PREPARED_NOT_NATIVE_VERIFIED", "effective_candidate": effective,
            "selection": {"split": "TRAIN", "count": planning.COUNT,
                          "direction": DIRECTION, "prediction_inheritance": False},
            "hnlo_policy": "LABEL_ONLY" if key == "minicpm4" else "LOCKED_EXISTING_METHOD",
            "historical_config_sha256": digest(old),
            "historical_selection_reference_only": historical_selection}


def native_identity(key, repo=ROOT):
    """Derive a fresh identity; never substitute a V4 transport hash for config."""
    d = descriptor(key)
    require(d["status"] != "BLOCKED_NATIVE_CONTRACT", "QWEN_FRESH_NATIVE_CONTRACT_REQUIRED")
    e = d["effective_candidate"]
    return planning.identity({"model_key": key, "model_id": d["model"]["id"],
        "model_revision": d["model"]["revision"], "hnlo_policy": d["hnlo_policy"],
        "implementation_sha256": digest(source_manifest(repo)), "configuration_sha256": digest(d),
        "prompt_sha256": e["generation"]["prompt_sha256"],
        "parser_sha256": sha(Path(repo) / "safeshift/pilot/contract.py"),
        "generation_sha256": digest(e["generation"]), "preprocessing_sha256": digest(e["preprocessing"]),
        "checkpoint_sha256": e["checkpoint_lock_sha256"],
        "runtime_sha256": digest({n: e[n] for n in ("python", "cuda_build", "requirements_sha256")})})


def campaign(cohorts, expected_projection_sha256, *, series=None):
    """No data access: the real projection must come from checked master bytes.

    A caller-authored projection/hash alone does not prove master derivation.
    Admission of real bytes additionally uses inputs.project_master below.
    """
    require_hash(expected_projection_sha256)
    require(planning.same_cohort(cohorts) == expected_projection_sha256, "PAIRED_PROJECTION_PIN")
    series = dict(SERIES if series is None else series)
    require(set(series) == set(planning.MODELS) and len(set(series.values())) == 3, "THREE_NEW_SERIES")
    for key, sid in series.items():
        planning.token(sid)
        require(sid.startswith("fresh171-" + key + "-"), "FRESH_SERIES_NAMESPACE")
    return {"schema": "safeshift-fresh-campaign-v1", "direction": DIRECTION,
            "cohort_sha256": expected_projection_sha256, "series": series,
            "planned_per_model": planning.COUNT, "planned_initial_calls": 3 * planning.COUNT,
            "prediction_inheritance": False, "scientific_selection": "PENDING"}


def plan(c, cohort, spec, history, *, action, run_id, attempt_id, max_calls, max_seconds, repair=None):
    require(c == campaign({k: cohort for k in planning.MODELS}, c["cohort_sha256"], series=c["series"]),
            "CAMPAIGN_CHANGED")
    key = spec["model_key"]
    sid = c["series"][key]
    require(action in ("initial", "resume", "repair"), "RERUN_REQUIRES_NEW_CAMPAIGN_AND_SERIES")
    require(all(h["series_id"] == sid and h["identity"] == spec for h in history), "FOREIGN_HISTORY_FORBIDDEN")
    # No inherited ancestors from any other series, even if they have the same IDs.
    return planning.plan(cohort, c["cohort_sha256"], spec, history, digest(history), action=action,
        series_id=sid, run_id=run_id, attempt_id=attempt_id,
        max_calls=max_calls, max_seconds=max_seconds, repair=repair)


def release_report(key):
    result = planning.release_report(key)
    result.update(schema="safeshift-fresh-release-v1", direction=DIRECTION, series_id=SERIES[key],
                  native=descriptor(key), runtime_binding="NEW_FRESH_RELEASE_REQUIRED",
                  historical_predictions_required=False, inherited_predictions=0,
                  original_projection="NOT_VERIFIED_CUSTODIAN_SEAL_REQUIRED",
                  execution_caps=None, live_constraints="NOT_MEASURED")
    return result


def authorize(*args, **kwargs):
    """Immutable task fence. A reviewed release change is required to activate."""
    raise PermissionError("ISSUE171_NO_GPU_INFERENCE_PRIVATE_INPUT: RELEASE_O2_O6_G0_G6_BLOCKED")
