"""Offline admission of measured receipts; never provision, load or probe GPU.

The fulltrain notebook is intentionally preparation-only under Issue167. These
checks describe/validate evidence a later authorized Kaggle preflight must emit.
PASS here establishes structural consistency only, never measured provenance.
"""
from safeshift.pilot.contract import digest, require_hash
from .source import require
from .fulltrain import release_report
from .train_preflight import evidence_levels

CHECKS = ("source_binding", "environment", "host_abi", "manifest", "checkpoint", "scratch", "storage",
          "runtime_setup", "software_cpu", "cpu_native", "images_cpu", "live_resources", "gpu_driver", "cuda_child")


def prepare_notebook(key, source_hash, repo, runtime_ref, *, work=None):
    """Export preparation requirements only; no Input/environment/GPU discovery."""
    from pathlib import Path
    import uuid
    from safeshift.pilot.artifacts import write, export
    from .train_contract import source_hash as actual_source_hash
    require(actual_source_hash(repo) == source_hash, "FINAL_PREPARATION_SOURCE_MISMATCH")
    output = Path(work or Path.cwd() / "data/processed/fulltrain_prep") / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    report = release_report(key)
    report.update(source_sha256=source_hash, runtime_ref=runtime_ref,
                  scope="PREPARATION_ONLY_NO_INPUT_OR_MODEL_ACCESS", attempt_consumed=False)
    write(output / "release.json", report)
    export(output, Path(str(output) + ".zip"))
    return output


def inspect_receipts(model_key, binding, receipts, expected_hashes):
    """All checks are bound to the same cohort/source/runtime/checkpoint identity.

    Expected hashes must come from a separately reviewed custody manifest.
    Supplying a self-authored PASS or recalculating hashes cannot enable launch.
    """
    require(set(binding) == {"cohort_sha256", "source_sha256", "runtime_sha256", "checkpoint_sha256"}, "PREFLIGHT_BINDING")
    for value in binding.values():
        require_hash(value)
    require(set(receipts) <= set(CHECKS) and set(expected_hashes) == set(receipts), "PREFLIGHT_RECEIPT_MEMBERSHIP")
    checks = {}
    for name in CHECKS:
        status, reason = "NOT_RUN", "MISSING_RECEIPT"
        if name in receipts:
            r = receipts[name]
            require_hash(expected_hashes[name])
            require(digest(r) == expected_hashes[name] and r.get("binding") == binding, "PREFLIGHT_CUSTODY_OR_BINDING")
            require(set(r) == {"binding", "evidence"}, "PREFLIGHT_RECEIPT_FIELDS")
            e = r["evidence"]
            require(type(e) is dict, "PREFLIGHT_EVIDENCE")
            ok = False
            if name == "source_binding":
                ok = e.get("actual_source_sha256") == binding["source_sha256"] and e.get("allowlist_exact") is True
            elif name == "environment":
                ok = all(type(e.get(k)) is str and e[k] for k in ("kernel_python", "worker_python", "os", "architecture"))
            elif name == "host_abi":
                ok = e.get("system") == "Linux" and e.get("machine") == "x86_64" and e.get("pointer_bits") == 64
            elif name == "manifest":
                ok = (e.get("unique_markers") == 1 and e.get("marker_sha256") == e.get("expected_marker_sha256")
                      and type(e.get("marker_sha256")) is str and len(e["marker_sha256"]) == 64
                      and e.get("cohort_sha256") == binding["cohort_sha256"] and e.get("planned_ids") == 3763
                      and e.get("split") == "TRAIN" and e.get("order_and_ids_verified") is True)
            elif name == "checkpoint":
                ok = e.get("actual_sha256") == binding["checkpoint_sha256"] and e.get("allowlist_exact") is True
            elif name == "scratch":
                ok = all(e.get(k) is True for k in ("mount_verified", "write_fsync_verified", "cleanup_verified"))
                ok = ok and all(type(e.get(k)) is int and e[k] > 0 for k in ("scratch_device", "output_device", "allocated_bytes"))
                ok = ok and e.get("allocated_bytes") == e.get("requested_bytes")
            elif name in ("storage", "live_resources"):
                fields = ("scratch_free", "output_free") if name == "storage" else ("ram_free", "quota_remaining", "time_remaining")
                ok = all(type(e.get(k)) is int and type(e.get(k + "_required")) is int
                         and e[k] >= e[k + "_required"] > 0 for k in fields)
            elif name == "runtime_setup":
                ok = e.get("actual_runtime_sha256") == binding["runtime_sha256"] and all(e.get(k) is True for k in ("worker_isolated", "python_pin_matches"))
            elif name == "software_cpu":
                ok = all(e.get(k) is True for k in ("pins_match", "pip_check", "compiled_abi", "native_imports"))
            elif name == "cpu_native":
                ok = e.get("shared_production_path") is True and e.get("processor_cases_pass") is True
            elif name == "images_cpu":
                ok = e.get("verified_images") == 3763 and e.get("checksum_and_decode") is True
            elif name == "gpu_driver":
                ok = all(e.get(k) is True for k in ("count_matches", "model_matches", "driver_matches", "visibility_matches"))
            elif name == "cuda_child":
                ok = e.get("worker_cuda") == "MEASURED_FP16_FUNCTIONAL" and e.get("same_worker_runtime_sha256") == binding["runtime_sha256"]
            status, reason = ("PASS", "STRUCTURAL_RECEIPT_CHECK_ONLY") if ok else ("BLOCKED", "INCOMPLETE_OR_FAILED_EVIDENCE")
        checks[name] = {"status": status, "reason": reason}
    result = release_report(model_key)
    result.update(checks=checks, receipt_reported_levels=evidence_levels(checks),
                  receipt_admission="PASS" if all(v["status"] == "PASS" for v in checks.values()) else "BLOCKED",
                  evidence_trust="CALLER_SUPPLIED_HASHES_REQUIRE_INDEPENDENT_CUSTODY_REVIEW")
    return result
