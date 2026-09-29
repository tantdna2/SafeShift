"""D9R13 canonical SafeShift compatibility PREP; no automatic model PASS."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.runners.contracts import GenerationFailure, Request, RunContext, Task
from safeshift.runners.paligemma import (
    DECODING, PREPROCESSING, PaliGemmaRunner, VerifiedRawStore,
    probe_hardware, software_versions,
)
from safeshift.runners.paligemma_snapshot import (
    CACHE, MODEL_ID, REVISION, OFFLINE_ENV, load_plan, network_denied,
    require_offline_env, sha256_file, write_json,
)
from scripts.w2_paligemma_t4_smoke import checkout_gate, memory_observation
from safeshift.protocol.firewall import external_path
from safeshift.protocol.prompts import classification_request, grounding_request
from safeshift.protocol.schema import strict_json
from safeshift.runners.paligemma_compatibility import observation
from scripts.w2_paligemma_interface_qualification import persist_verified

BASE_SHA = "a3192ddefbc28fe2997190819744e8f4796a6d85"
PLAN = "configs/pre_freeze/paligemma_production_interface_candidate.v1.json"
PLAN_SHA256 = "af1d739169eb264b38c60982d4e0b4896cce1060e84e76afba42d5f661d8edd0"
ARTIFACTS = "data/processed/runtime_validation/w2_paligemma_canonical_compatibility"
RUN_ID = "paligemma-d9r13-01"
COMPLETE = "EVIDENCE_COLLECTION_COMPLETE"
STOP = "STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED"


def qualification_plan(repo=ROOT):
    path = Path(repo) / PLAN
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("PREDECLARED_PLAN_BYTES_CHANGED")
    plan = strict_json(raw)
    if (plan["base_sha"], plan["model_id"], plan["revision"]) != (BASE_SHA, MODEL_ID, REVISION):
        raise ValueError("EXACT_BASE_MODEL_REVISION_REQUIRED")
    return plan


def verified_input(repo, path, expected_sha):
    if type(path) is not str or type(expected_sha) is not str or len(expected_sha) != 64:
        raise ValueError("APPROVED_INPUT_PATH_AND_SHA256_REQUIRED")
    resolved = external_path(Path(repo), path)
    raw = resolved.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("APPROVED_INPUT_HASH_MISMATCH")
    return raw


def prepared_cases(plan, repo=ROOT):
    """Validate ALL approved inputs before any provisioning/model/backend access.

    Annotation fields document coverage only; neither builders nor adapters get GT.
    No fallback policy, synthetic answer card or geometric fixture is manufactured.
    """
    policy = plan["industry_safety_policy"]
    if not isinstance(policy, dict) or not policy.get("source"):
        raise ValueError("APPROVED_PRODUCTION_POLICY_ARTIFACT_REQUIRED")
    policy_text = verified_input(repo, policy["path"], policy["sha256"]).decode("utf-8")
    if not policy_text.strip():
        raise ValueError("EMPTY_POLICY")
    expected = [("C_LEVEL01", "classification"), ("C_LEVEL02", "classification"),
                ("C_LEVEL03", "classification"), ("C_LEVEL04", "classification"),
                ("G_SMOKE", "grounding"), ("G_OPEN_FLAME", "grounding"), ("G_NONE", "grounding")]
    if [(c["case_id"], c["task_type"]) for c in plan["cases"]] != expected:
        raise ValueError("FIXED_FOUR_PLUS_THREE_CASES_REQUIRED")
    if (plan["classification_calls"], plan["grounding_calls"], plan["total_calls"],
            plan["model_loads"]) != (4, 3, 7, 1):
        raise ValueError("EXACT_BUDGET_REQUIRED")
    result = []
    for index, case in enumerate(plan["cases"]):
        if not case["source"] or not case["approval_reference"]:
            raise ValueError("APPROVED_FIXTURE_PROVENANCE_REQUIRED")
        if index < 4:
            if case["expected_safety_level"] != f"Level{index + 1:02d}":
                raise ValueError("FOUR_LEVEL_COVERAGE_REQUIRED")
        elif case["expected_hazards"] != (["SMOKE"], ["OPEN_FLAME"], [])[index - 4]:
            raise ValueError("TWO_DISTINCT_HAZARDS_AND_NEGATIVE_REQUIRED")
        raw = verified_input(repo, case["image_path"], case["image_sha256"])
        canonical = (classification_request(Path(repo), case["image_path"], policy_text)
                     if case["task_type"] == "classification"
                     else grounding_request(Path(repo), case["image_path"]))
        request = Request(Task(case["task_type"]), case["case_id"], case["image_path"],
                          raw, canonical.prompt_version, canonical.prompt)
        metadata = {**case, "policy": policy if index < 4 else None,
                    "prompt": canonical.prompt, "prompt_version": canonical.prompt_version,
                    "prompt_sha256": canonical.prompt_sha256}
        result.append((request, metadata))
    for group in (result[:4], result[4:]):
        if len({hashlib.sha256(r.input_bytes).hexdigest() for r, _ in group}) != len(group):
            raise ValueError("DISTINCT_COVERAGE_IMAGES_REQUIRED")
    return result


def collect_case(runner, store, request, context, fixture, torch):
    provenance = {
        **asdict(context), "sample_id": request.sample_id, "task_type": request.task.value,
        "model_id": MODEL_ID, "revision": REVISION, "runner_version": runner.version,
        "prompt_id": request.prompt_id, "prompt": request.prompt,
        "prompt_sha256": hashlib.sha256(request.prompt.encode("utf-8")).hexdigest(),
        "input_sha256": hashlib.sha256(request.input_bytes).hexdigest(),
        "fixture": fixture, "plan_sha256": PLAN_SHA256, "parse_status": "NOT_ATTEMPTED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
    result = {"case_id": context.call_id, "task_type": request.task.value,
              "prompt": request.prompt, "fixture": fixture, "raw": None,
              "status": STOP, "timing": {}, "observation": None}
    started = time.perf_counter()
    stage = "PREPARE_INPUT"
    try:
        prepared = runner.prepare_input(request, context)
        torch.cuda.synchronize(0)
        generation_started = time.perf_counter()
        stage = "NATIVE_GENERATE"
        try:
            raw = runner.generate_raw(prepared, context)
        except GenerationFailure as exc:
            if exc.partial_raw is not None:
                ref, _ = persist_verified(store, exc.partial_raw, provenance)
                result["raw"] = asdict(ref)
            raise
        # Persist before adapter, JSON deserialization or timing postprocessing.
        stage = "RAW_PERSISTENCE"
        ref, persisted = persist_verified(store, raw, provenance)
        result["raw"] = asdict(ref)
        torch.cuda.synchronize(0)
        result["timing"]["generate_audit_persist_sync_seconds"] = time.perf_counter() - generation_started
        stage = "CANONICAL_ADAPTER"
        result["observation"] = observation(persisted, request.task)
        result["status"] = COMPLETE
    except Exception as exc:
        # Do not serialize arbitrary exception messages/environments into evidence.
        result["failure"] = {"stage": stage, "type": type(exc).__name__}
        raise
    finally:
        result["timing"]["case_wall_seconds"] = time.perf_counter() - started
        write_json(store.root / (context.call_id + ".json"), result)
    return result


def run_qualification(*, expected_commit, venue_internet_off, repo=ROOT,
                      cache_dir=CACHE, runner_factory=PaliGemmaRunner, torch_module=None):
    """One fixed attempt; injection exists for fake tests, not as a CLI option."""
    repo = Path(repo)
    store = VerifiedRawStore(repo, ARTIFACTS + "/" + RUN_ID)
    store.root.mkdir(parents=True, exist_ok=False)
    report = {"schema_version": "paligemma-canonical-compatibility-evidence-v1", "run_id": RUN_ID,
              "status": STOP, "plan_path": PLAN, "plan_sha256": PLAN_SHA256,
              "base_sha": BASE_SHA, "execution_commit": expected_commit,
              "model_id": MODEL_ID, "revision": REVISION,
              "calls": [], "model_load_count": 0, "native_generate_calls": 0,
              "started_at_utc": datetime.now(timezone.utc).isoformat()}
    runner = None
    stage = "CHECKOUT"
    try:
        checkout_gate(repo, expected_commit)
        subprocess.run(["git", "merge-base", "--is-ancestor", BASE_SHA, expected_commit],
                       cwd=repo, check=True, capture_output=True)
        stage = "PLAN"
        plan = qualification_plan(repo)
        stage = "APPROVED_CANONICAL_INPUTS"
        cases = prepared_cases(plan, repo)
        runtime = load_plan(repo)
        report["preserved_status"] = plan["preserved_status"]
        report["interpretation"] = plan["interpretation"]
        write_json(store.root / "qualification_plan.json", plan)
        report["source_hashes"] = {p: sha256_file(repo / p) for p in (
            PLAN, plan["runtime_plan"], "requirements-paligemma-t4.txt",
            "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
            "safeshift/runners/storage.py", "scripts/w2_paligemma_canonical_compatibility.py",
            "scripts/w2_paligemma_interface_qualification.py",
            "safeshift/protocol/prompts.py", "safeshift/protocol/schema.py",
            "safeshift/runners/paligemma_compatibility.py")}
        stage = "OFFLINE_PREFLIGHT"
        if venue_internet_off is not True:
            raise ValueError("OWNER_INTERNET_OFF_REQUIRED")
        require_offline_env()
        if (os.environ.get("CUDA_VISIBLE_DEVICES") != "0"
                or os.environ.get("CUDA_DEVICE_ORDER") != "PCI_BUS_ID"):
            raise ValueError("SINGLE_VISIBLE_T4_MASK_REQUIRED_BEFORE_IMPORT")
        if any(os.environ.get(k) for k in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN")):
            raise ValueError("CREDENTIAL_FREE_RUNTIME_REQUIRED")
        report["offline"] = {"owner_attested_internet_off": True, "variables": dict(OFFLINE_ENV),
                             "socket_denial": True, "cuda_visible_devices": "0",
                             "cuda_device_order": "PCI_BUS_ID"}
        with network_denied():
            stage = "SOFTWARE_HARDWARE"
            report["software"] = software_versions()
            if report["software"] != runtime["software"]:
                raise ValueError("EXACT_SOFTWARE_REQUIRED")
            if platform.system() != "Linux" or platform.machine() != "x86_64":
                raise ValueError("LINUX_X86_64_REQUIRED")
            if torch_module is None:
                import torch as torch_module
            report["hardware"] = probe_hardware(torch_module)
            torch_module.cuda.reset_peak_memory_stats(0)
            stage = "FIXTURES"
            manifest = []
            for request, metadata in cases:
                manifest.append(metadata)
                with (store.root / (request.sample_id + ".input")).open("xb") as stream:
                    stream.write(request.input_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
            write_json(store.root / "fixture_manifest.json", manifest)
            write_json(store.root / "policy.json", {
                **plan["industry_safety_policy"],
                "text": verified_input(repo, plan["industry_safety_policy"]["path"],
                                       plan["industry_safety_policy"]["sha256"]).decode("utf-8")})
            command = ("python scripts/w2_paligemma_canonical_compatibility.py --expected-commit "
                       + expected_commit + " --cache-dir " + cache_dir + " --venue-internet-off")
            context = RunContext(RUN_ID, plan["cases"][0]["case_id"], dict(DECODING),
                                 dict(PREPROCESSING), "FP16", "NONE", {"placement": "cuda:0"},
                                 report["software"], expected_commit, command,
                                 "HANDCRAFTED_RUNTIME_SMOKE")
            # Retain the audited runner's narrow source-kind allowlist. Actual
            # qualification scope/fixture provenance is explicit in every record.
            report["command"] = command
            report["seed"] = None
            runner = runner_factory(repo=repo, cache_dir=cache_dir)
            stage = "INITIALIZE_LOAD"
            started = time.perf_counter()
            runner.initialize(context)
            runner.load(context)
            torch_module.cuda.synchronize(0)
            report["initialize_load_seconds"] = time.perf_counter() - started
            for request, metadata in cases:
                stage = request.sample_id
                ctx = replace(context, call_id=request.sample_id, input_provenance=metadata)
                result = collect_case(runner, store, request, ctx, metadata, torch_module)
                report["calls"].append({"case_id": request.sample_id, "raw": result["raw"],
                                       "result_path": request.sample_id + ".json",
                                       "parse_status": result["observation"]["parse_status"],
                                       "canonical_output": result["observation"]["canonical_output"]})
            report["compatibility_review"] = {
                task: {"all_cases_map_fail_closed": all(c["parse_status"] == "SUCCESS"
                        for c in report["calls"][start:end]),
                       "case_ids": [c["case_id"] for c in report["calls"][start:end]],
                       "research_lead_decision": "PENDING_YES_OR_NO"}
                for task, start, end in (("CLASSIFICATION_COMPATIBLE", 0, 4),
                                         ("GROUNDING_COMPATIBLE", 4, 7))}
            # Invalid model outputs remain recorded with value=null. Continue the
            # fixed independent matrix, without retrying/tuning failed cases.
            stage = "FINAL_AUDIT"
            runner._stable("qualification_final")
            if runner.model_load_count != 1 or runner.native_generate_calls != len(plan["cases"]):
                raise ValueError("ONE_LOAD_SEVEN_CALLS_REQUIRED")
            report["memory"] = memory_observation(torch_module)
            report["status"] = COMPLETE
    except Exception as exc:
        report["failure"] = {"stage": stage, "type": type(exc).__name__}
    finally:
        if runner is not None:
            report.update(model_load_count=runner.model_load_count,
                          native_generate_calls=runner.native_generate_calls,
                          state_audits=runner.audits, runner_state=runner.state,
                          snapshot=runner.snapshot)
            runner.close()
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["artifacts"] = {p.relative_to(store.root).as_posix(): {
            "sha256": sha256_file(p), "size_bytes": p.stat().st_size}
            for p in sorted(store.root.rglob("*")) if p.is_file()}
        write_json(store.root / "summary.json", report)
        write_json(store.root / "summary.sha256.json", {"sha256": sha256_file(store.root / "summary.json")})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-commit")
    parser.add_argument("--validate-inputs", action="store_true")
    parser.add_argument("--cache-dir", default=CACHE)
    parser.add_argument("--venue-internet-off", action="store_true")
    args = parser.parse_args()
    if args.validate_inputs:
        try:
            prepared_cases(qualification_plan())
        except (ValueError, KeyError, OSError) as exc:
            print(STOP + ": " + str(exc))
            return 1
        print("APPROVED_CANONICAL_INPUTS_VERIFIED")
        return 0
    if not args.expected_commit or not args.venue_internet_off:
        parser.error("--expected-commit and --venue-internet-off are required for runtime")
    report = run_qualification(expected_commit=args.expected_commit,
                               venue_internet_off=args.venue_internet_off, cache_dir=args.cache_dir)
    print(report["status"])
    return 0 if report["status"] == COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
