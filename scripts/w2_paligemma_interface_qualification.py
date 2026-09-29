"""D9R10 PREP: future offline observation, never qualification or scoring."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
from io import BytesIO
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

BASE_SHA = "93a8f32ad8c7d10a28cb3e4b62232cd3697bd0e1"
PLAN = "configs/pre_freeze/paligemma_interface_qualification.v1.json"
PLAN_SHA256 = "05e1f8f8f56af2abfd8f6fe8fb66a5f820faa3508506072adf5b850fdcdcc2fd"
ARTIFACTS = "data/processed/runtime_validation/w2_paligemma_interface_qualification"
RUN_ID = "paligemma-d9r11-01"
COMPLETE = "EVIDENCE_COLLECTION_COMPLETE"
STOP = "STOP_AND_RESEARCH_LEAD_REVIEW_REQUIRED"


def qualification_plan(repo=ROOT):
    path = Path(repo) / PLAN
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PLAN_SHA256:
        raise ValueError("PREDECLARED_PLAN_BYTES_CHANGED")
    plan = json.loads(raw)
    if (plan["base_sha"], plan["model_id"], plan["revision"]) != (BASE_SHA, MODEL_ID, REVISION):
        raise ValueError("EXACT_BASE_MODEL_REVISION_REQUIRED")
    return plan


def fixtures(plan):
    """No dataset, randomness, model answer, or external file inputs."""
    from PIL import Image, ImageDraw
    spec = plan["fixtures"]
    for item in spec["items"]:
        with Image.new(spec["mode"], tuple(spec["size"]), tuple(spec["background"])) as image:
            x0, y0, x1, y1 = item["bbox_xyxy"]
            draw = ImageDraw.Draw(image)
            if item["shape"] == "rectangle":
                draw.rectangle((x0, y0, x1 - 1, y1 - 1), fill=tuple(item["fill"]))
            elif item["shape"] == "ellipse":
                draw.ellipse((x0, y0, x1 - 1, y1 - 1), fill=tuple(item["fill"]))
            else:
                raise ValueError("UNDECLARED_SHAPE")
            pixel_sha = hashlib.sha256(image.tobytes()).hexdigest()
            stream = BytesIO()
            image.save(stream, format="PNG", optimize=False, compress_level=9)
        raw = stream.getvalue()
        yield item["fixture_id"], raw, {
            **item, "size": spec["size"], "mode": spec["mode"],
            "background": spec["background"], "generator": spec["generator"],
            "geometry_convention": spec["geometry_convention"],
            "geometry_use": spec["geometry_use"], "pixel_sha256": pixel_sha,
            "png_sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw),
        }


def persist_verified(store, raw, provenance):
    """The observer only receives bytes re-read AFTER exclusive fsync storage."""
    ref = store.preserve(raw, provenance)
    persisted = (store.repo / ref.path).read_bytes()
    if len(persisted) != ref.size_bytes or hashlib.sha256(persisted).hexdigest() != ref.sha256:
        raise ValueError("REREAD_RAW_HASH_OR_SIZE_MISMATCH")
    return ref, persisted


def observe(persisted):
    """Envelope deserialization/token inventory only; no label or box parser."""
    import re
    envelope = json.loads(persisted)
    ids = envelope["continuation_ids"]
    text = envelope["decoded_with_special_tokens"]
    return {
        "status": "OBSERVED_ONLY", "native_output": envelope,
        "loc_tokens_in_continuation_order": [
            {"continuation_index": i, "token_id": token, "token": f"<loc{token - 256000:04d}>"}
            for i, token in enumerate(ids) if 256000 <= token <= 257023],
        # Include out-of-range/malformed loc-looking strings verbatim as well.
        "loc_text_in_decode_order": [
            {"character_offset": m.start(), "text": m.group(0)}
            for m in re.finditer(r"<loc[^>]*>", text)],
        "continuation_length": len(ids), "eos_token_id_1_observed": 1 in ids,
        "at_generation_cap": len(ids) == DECODING["max_new_tokens"],
        "parser_candidate": {"status": "NOT_YET_QUALIFIED", "executed": False,
                             "canonical_output": None},
        "no_detection_policy": "OBSERVE_VERBATIM_NO_CANONICAL_GRAMMAR_NO_EMPTY_LIST_COERCION",
    }


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
        # Persist before observation, JSON deserialization or timing postprocessing.
        stage = "RAW_PERSISTENCE"
        ref, persisted = persist_verified(store, raw, provenance)
        result["raw"] = asdict(ref)
        torch.cuda.synchronize(0)
        result["timing"]["generate_audit_persist_sync_seconds"] = time.perf_counter() - generation_started
        stage = "OBSERVATION_ONLY"
        result["observation"] = observe(persisted)
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
    report = {"schema_version": "paligemma-interface-evidence-v1", "run_id": RUN_ID,
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
        runtime = load_plan(repo)
        report["preserved_status"] = plan["preserved_status"]
        report["interpretation"] = plan["interpretation"]
        write_json(store.root / "qualification_plan.json", plan)
        report["source_hashes"] = {p: sha256_file(repo / p) for p in (
            PLAN, plan["runtime_plan"], "requirements-paligemma-t4.txt",
            "safeshift/runners/paligemma.py", "safeshift/runners/paligemma_snapshot.py",
            "safeshift/runners/storage.py", "scripts/w2_paligemma_interface_qualification.py")}
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
            inputs = {}
            manifest = []
            for fixture_id, raw, metadata in fixtures(plan):
                inputs[fixture_id] = (raw, metadata)
                manifest.append(metadata)
                with (store.root / (fixture_id + ".png")).open("xb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            write_json(store.root / "fixture_manifest.json", manifest)
            command = ("python scripts/w2_paligemma_interface_qualification.py --expected-commit "
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
            for case in plan["cases"]:
                stage = case["case_id"]
                raw, metadata = inputs[case["fixture_id"]]
                ctx = replace(context, call_id=case["case_id"], input_provenance=metadata)
                request = Request(Task(case["task_type"]), case["case_id"], case["fixture_id"],
                                  raw, case["prompt_id"], plan["prompts"][case["prompt_id"]]["text"])
                result = collect_case(runner, store, request, ctx, metadata, torch_module)
                report["calls"].append({"case_id": case["case_id"], "raw": result["raw"],
                                        "result_path": case["case_id"] + ".json"})
            stage = "FINAL_AUDIT"
            runner._stable("qualification_final")
            if runner.model_load_count != 1 or runner.native_generate_calls != len(plan["cases"]):
                raise ValueError("ONE_LOAD_EIGHT_CALLS_REQUIRED")
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
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--cache-dir", default=CACHE)
    parser.add_argument("--venue-internet-off", required=True, action="store_true")
    args = parser.parse_args()
    report = run_qualification(expected_commit=args.expected_commit,
                               venue_internet_off=args.venue_internet_off, cache_dir=args.cache_dir)
    print(report["status"])
    return 0 if report["status"] == COMPLETE else 1


if __name__ == "__main__":
    raise SystemExit(main())
