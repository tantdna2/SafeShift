"""Fresh pinned interpreter per stage. No inference outside the gated probe mode."""

import argparse
from contextlib import contextmanager
import importlib.metadata
from io import BytesIO
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import traceback

from .artifacts import sha256, write
from .contract import AUTHORITY, MODELS, authorize, scope, synthetic_png


def empty(model):
    return {"model": model, "environment": "NOT_RUN", "t1": "NOT_RUN", "capture": "NOT_RUN",
            "alignment": "N/A", "technical_hnlo": "N/A", "result": "NOT_ATTEMPTED", "hnlo": None,
            "CAPTURE_VALID": False, "ALIGNMENT_VALID": False, "TECHNICAL_HNLO_VALID": False,
            "HNLO_RESEARCH_VERIFIED": False, "load_calls": 0, "generate_calls": 0, "common_fatal": False}


def environment(model, repo, torch=None):
    from safeshift.protocol.classification_policy import load_policy
    import zlib
    expected = load_policy(repo, qwen3_runtime=True)["classification"][model]["software_versions"]
    if model == "qwen3":
        build = json.loads((repo / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
        expected = {**expected, **build["qwen3_additional_pins"]}
    actual = {k: platform.python_version() if k == "python" else zlib.ZLIB_RUNTIME_VERSION if k == "zlib"
              else importlib.metadata.version(k) for k in expected}
    if actual != expected or platform.system() != "Linux" or platform.machine() != "x86_64":
        raise ValueError("EXACT_PINNED_LINUX_ENVIRONMENT_REQUIRED:" + json.dumps(actual, sort_keys=True))
    if model == "qwen3" and zlib.ZLIB_VERSION != "1.2.11":
        raise ValueError("QWEN_ZLIB_COMPILE_VERSION_MISMATCH")
    if os.environ.get("CUDA_VISIBLE_DEVICES") != MODELS[model]["cuda_visible_devices"]:
        raise ValueError("GPU_VISIBILITY_MUST_BE_SET_BEFORE_PYTHON_START")
    if torch is None:
        import torch
    count = len(MODELS[model]["cuda_visible_devices"].split(","))
    if (not torch.cuda.is_available() or torch.cuda.device_count() != count
            or torch.version.cuda != MODELS[model]["cuda"]):
        raise ValueError("EXACT_CUDA_BUILD_AND_VISIBLE_GPU_COUNT_REQUIRED")
    devices = []
    for i in range(count):
        prop = torch.cuda.get_device_properties(i)
        if prop.name not in ("Tesla T4", "NVIDIA T4", "T4") or (prop.major, prop.minor) != (7, 5):
            raise ValueError("T4_CC75_REQUIRED_NO_HARDWARE_SUBSTITUTION")
        if not 14 * 2**30 <= prop.total_memory <= 16 * 2**30:
            raise ValueError("T4_VRAM_CAPACITY_MISMATCH")
        free, total = torch.cuda.mem_get_info(i)
        if free < 13 * 2**30:
            raise ValueError("INSUFFICIENT_FREE_VRAM")
        devices.append({"index": i, "name": prop.name, "compute_capability": [prop.major, prop.minor],
                        "total_bytes": total, "free_bytes": free})
    return {"expected": expected, "actual": actual, "visible_devices": os.environ["CUDA_VISIBLE_DEVICES"],
            "cuda": torch.version.cuda, "devices": devices, "executable_name": Path(sys.executable).name,
            "python_compiler": platform.python_compiler(), "zlib_compile_version": zlib.ZLIB_VERSION,
            "zlib_runtime_version": zlib.ZLIB_RUNTIME_VERSION,
            "all_distributions": sorted(({"name": d.metadata["Name"], "version": d.version}
                                        for d in importlib.metadata.distributions()), key=lambda d: d["name"].lower())}


def memory(torch=None):
    import resource
    result = {"peak_host_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    if torch is not None:
        result["vram"] = [{"device": i, "allocated_bytes": torch.cuda.memory_allocated(i),
                            "reserved_bytes": torch.cuda.memory_reserved(i),
                            "peak_allocated_bytes": torch.cuda.max_memory_allocated(i),
                            "peak_reserved_bytes": torch.cuda.max_memory_reserved(i)} for i in range(torch.cuda.device_count())]
    return result


@contextmanager
def count_native(model_key, evidence, state, capture=None):
    """Instrument the exact model class entry points; never alter returned values."""
    from unittest.mock import patch
    import transformers
    cls = getattr(transformers, "Qwen3VLForConditionalGeneration" if model_key == "qwen3" else "InternVLForConditionalGeneration")
    original_load, original_generate = cls.from_pretrained, cls.generate

    def observe_processors(native, *args, **kwargs):
        processors = original_processors(native, *args, **kwargs)
        record = {"processors": [type(item).__module__ + "." + type(item).__name__ for item in processors],
                  "criterion": "EMPTY_ACTUAL_PROCESSOR_LIST_WITH_PINNED_GREEDY_GENERATION_SOURCE"}
        capture.write("raw-provenance", record)
        # Both audited generation versions append raw_logits after calling the
        # processor list. Empty actual lists prove absence of in-place mutation;
        # equality of raw/processed numbers alone does not prove provenance.
        if processors:
            raise ValueError("UNVERIFIED_RAW_LOGIT_PROCESSOR_PIPELINE")
        return processors

    def observe_stopping(native, *args, **kwargs):
        criteria = original_stopping(native, *args, **kwargs)
        names = [type(item).__name__ for item in criteria]
        capture.write("stopping-criteria", {"classes": names, "criteria": [
            {"class": type(item).__name__, "max_length": getattr(item, "max_length", None)} for item in criteria]})
        if "MaxLengthCriteria" not in names or set(names) - {"MaxLengthCriteria", "EosTokenCriteria"}:
            raise ValueError("UNREVIEWED_STOPPING_CRITERION")
        return criteria

    def load(*args, **kwargs):
        if state["load_calls"]:
            raise RuntimeError("SECOND_MODEL_LOAD_FORBIDDEN")
        write(evidence / "native-load-start.json", {"ordinal": 1, "model": model_key})
        state["load_calls"] += 1
        result = original_load(*args, **kwargs)
        write(evidence / "native-load-return.json", {"ordinal": 1})
        return result

    def generate(native, *args, **kwargs):
        if state["generate_calls"]:
            raise RuntimeError("SECOND_GENERATE_FORBIDDEN")
        write(evidence / "native-generate-start.json", {"ordinal": 1, "model": model_key})
        state["generate_calls"] += 1
        result = original_generate(native, *args, **kwargs)
        write(evidence / "native-generate-return.json", {"ordinal": 1})
        return result

    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(cls, "from_pretrained", side_effect=load))
        stack.enter_context(patch.object(cls, "generate", generate))
        if capture is not None:
            original_processors, original_stopping = cls._get_logits_processor, cls._get_stopping_criteria
            stack.enter_context(patch.object(cls, "_get_logits_processor", observe_processors))
            stack.enter_context(patch.object(cls, "_get_stopping_criteria", observe_stopping))
        yield


def verify_snapshot(model, repo, cache):
    from safeshift.runners.internvl3_snapshot import snapshot_path, verify_snapshot as verify_intern
    if model == "internvl3":
        snapshot = snapshot_path(repo, cache)
        return snapshot, verify_intern(snapshot, repo=repo)
    from scripts.provision_qwen3vl_snapshot import cached_snapshot
    from .provision import verify_qwen
    snapshot = cached_snapshot(str(repo / cache), offline=True)
    return snapshot, verify_qwen(snapshot, repo)


def no_forcing(config):
    """Reject checkpoint defaults that would add prefixes/force semantic output."""
    values = config.to_dict()
    for key in ("forced_bos_token_id", "forced_eos_token_id", "forced_decoder_ids", "force_words_ids", "constraints"):
        if values.get(key) is not None:
            raise ValueError("FORCING_CHECKPOINT_DEFAULT_FORBIDDEN:" + key)


def replay(repo, run_id, tokenizer):
    """CPU-only reconstruction from sealed persisted full vectors and native IDs."""
    from safeshift.diagnostics.hnlo_capture import Capture, ordered_t1_ids, review_trace, vector
    from safeshift.ls1.core import log_softmax
    from safeshift.ls1.evaluate import anomaly_log_odds
    cap = Capture.open(repo, run_id)
    if not cap.journal.verify():
        raise ValueError("SEALED_CAPTURE_REQUIRED")
    native, trace = cap.journal.read("native"), cap.journal.read("trace")
    provenance = cap.journal.read("raw-provenance")
    stopping = cap.journal.read("stopping-criteria")
    if (provenance["processors"] or provenance["criterion"] != "EMPTY_ACTUAL_PROCESSOR_LIST_WITH_PINNED_GREEDY_GENERATION_SOURCE"
            or "MaxLengthCriteria" not in stopping["classes"]
            or set(stopping["classes"]) - {"MaxLengthCriteria", "EosTokenCriteria"}):
        raise ValueError("RAW_PROVENANCE_OR_STOPPING_NOT_VERIFIED")
    if (native["input_ids"] != trace["input_ids"] or native["sequences"] != [trace["input_ids"] + trace["continuation_ids"]]
            or native["candidate_token_ids"] != trace["candidate_token_ids"]
            or native["raw_steps"] != len(trace["steps"]) or native["processed_steps"] != len(trace["steps"])
            or ordered_t1_ids(cap.journal.read("runtime-t1")) != trace["candidate_token_ids"]):
        raise ValueError("NATIVE_TRACE_ALIGNMENT_MISMATCH")
    review = review_trace(cap, tokenizer)
    result = {"CAPTURE_VALID": True, "ALIGNMENT_VALID": review["alignment"] == "PASS",
              "TECHNICAL_HNLO_VALID": False, "HNLO_RESEARCH_VERIFIED": False,
              "capture": "CAPTURE_VALID", "alignment": "ALIGNMENT_VALID" if review["alignment"] == "PASS" else "N/A",
              "technical_hnlo": "N/A", "hnlo": None, "review": review,
              "stop_observation": trace["eos_observation"], "raw_provenance": provenance,
              "stopping_criteria": stopping}
    count = len(trace["continuation_ids"])
    eos = trace["eos_observation"]
    if count > 32 or (eos["positions"] and eos["positions"] != [count - 1]):
        raise ValueError("STOPPING_OR_EOS_CONTRACT_MISMATCH")
    result["stop_reason"] = "EOS" if eos["terminal_eos"] else "MAX_NEW_TOKENS" if count == 32 else "UNEXPLAINED_EARLY_STOP"
    if result["stop_reason"] == "UNEXPLAINED_EARLY_STOP":
        result.update(ALIGNMENT_VALID=False, alignment="N/A")
        return result
    if review["alignment"] == "PASS":
        decision = review["decision"]
        saved = vector(cap.journal.read(f"raw-{decision['step']:03d}"))
        four = [saved[i] for i in decision["token_ids"]]
        if four != review["raw_label_logits"] or not all(math.isfinite(v) for v in four):
            raise ValueError("FOUR_SAVED_RAW_LOGITS_MISMATCH")
        value = anomaly_log_odds(log_softmax(four))
        if not math.isfinite(value):
            raise ValueError("NONFINITE_TECHNICAL_HNLO")
        result.update(TECHNICAL_HNLO_VALID=True, technical_hnlo="TECHNICAL_HNLO_VALID", hnlo=value,
                      ordered_token_ids=decision["token_ids"], raw_label_logits=four,
                      processed_label_scores=review["processed_label_scores"], decision_step=decision["step"],
                      numerical_tolerance=scope()["numerical_tolerance"])
    return result


def probe(model, repo, evidence, source, grant, cache, state, *, capture_root):
    from safeshift.diagnostics.hnlo_capture import Capture, ordered_t1_ids
    from safeshift.diagnostics.hnlo_hf import InternVL3Diagnostic, Qwen3Diagnostic, installed_qwen_sources
    from safeshift.ls1.tokenizer import TOKENIZER_FILES, probe as t1_probe
    from safeshift.protocol.classification_policy import load_policy, render_prompt
    from transformers import AutoTokenizer
    import torch
    from PIL import Image
    snapshot, receipt = verify_snapshot(model, repo, cache)
    write(evidence / "offline-snapshot.json", receipt)
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
    t1 = t1_probe(tokenizer)
    candidate_ids = ordered_t1_ids(t1)
    write(evidence / "preload-t1.json", t1)
    state["reference_t1"] = "PASS_28_OF_28"
    state["t1"] = "REFERENCE_PASS_RUNTIME_NOT_RUN"
    run_id = "hnlo-" + grant["attempt_id"] + "-" + model
    state["run_id"] = run_id
    policy = load_policy(repo, qwen3_runtime=True)["classification"][model]
    sources = [{"path": r["path"], "sha256": r["sha256"]} for r in json.loads((repo / "configs/diagnostics/hnlo_one_click_source.v1.json").read_bytes())["files"]]
    if model == "qwen3":
        sources.extend(installed_qwen_sources())
    else:
        import transformers
        audit = json.loads((repo / "configs/pre_freeze/internvl3_source_audit.v1.json").read_bytes())
        for row in audit["sources"].values():
            if "/src/transformers/" in row["url"]:
                relative = row["url"].split("/src/transformers/", 1)[1]
                local = Path(transformers.__file__).parent / relative
                if sha256(local) != row["response_sha256"]:
                    raise ValueError("AUDITED_TRANSFORMERS_SOURCE_MISMATCH:" + relative)
                sources.append({"path": "transformers/" + relative, "sha256": sha256(local), "size_bytes": local.stat().st_size})
    prompt = render_prompt(model, repo=repo)
    cap = Capture(capture_root, {"run_id": run_id, "sample_id": scope()["sample_id"], "model_id": MODELS[model]["id"],
        "revision": MODELS[model]["revision"], "tokenizer_revision": MODELS[model]["revision"],
        "tokenizer_files": [r for r in receipt["files"] if r["path"] in TOKENIZER_FILES],
        "software": state["runtime"], "source_commit": source["merge_commit"], "sources": sources,
        "command": "python -m safeshift.diagnostics.one_click.worker --mode probe --model " + model,
        "prompt": prompt, "input_sha256": scope()["input_sha256"], "configuration": policy,
        "seed": None, "authority": grant, "source_release": source})
    cap.write("synthetic-input", {"kind": "RGB", "size": [448, 448], "color": [128, 128, 128],
                                   "png_sha256": scope()["input_sha256"]})
    failure = None
    try:
        with count_native(model, evidence, state, cap):
            if model == "internvl3":
                from safeshift.ls1.runtime import NativeScorer
                scorer = NativeScorer(model, snapshot, tokenizer, candidate_ids, repo=repo)
                no_forcing(scorer.config)
                with Image.open(BytesIO(synthetic_png())) as image:
                    InternVL3Diagnostic(scorer).generate(image, cap)
            else:
                from safeshift.runners.qwen3_vl import Qwen3VLRunner
                from safeshift.runners.contracts import Request, RunContext, Task
                context = RunContext(run_id=run_id, call_id="synthetic-once", git_commit_sha=source["merge_commit"],
                    command="hnlo-one-click", source_kind="SYNTHETIC", **{k: policy[k] for k in
                    ("decoding", "preprocessing", "precision", "quantization", "device", "software_versions", "seed")})
                runner = Qwen3VLRunner()
                runner.initialize(context)
                runner.load(context)
                no_forcing(runner._resources[1].generation_config)
                request = Request(Task.CLASSIFICATION, scope()["sample_id"], "synthetic-rgb", synthetic_png(), "p2-classification-c1-v1", prompt)
                prepared = runner.prepare_input(request, context)
                Qwen3Diagnostic(runner, tokenizer).generate(prepared, context, cap)
        for required in ("raw-provenance", "stopping-criteria"):
            if not cap.journal.exists(required):
                raise ValueError("NATIVE_GENERATION_PIPELINE_OBSERVATION_MISSING")
        cap.journal.seal()
    except BaseException as error:
        failure = error
        if not cap.journal.exists("failure"):
            cap.failure(error)
        if not cap.journal.exists("seal"):
            cap.journal.seal()
        raise
    finally:
        if cap.journal.exists("runtime-t1"):
            actual = cap.journal.read("runtime-t1")
            ordered_t1_ids(actual)
            state["t1"] = "PASS_28_OF_28" if actual == t1 and "RUNTIME_TOKENIZER_T1_MISMATCH" not in str(failure) else "FAIL"
    state.update(capture="PERSISTED_AWAITING_CPU_REPLAY", result="AWAITING_CPU_REPLAY")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inspect", "probe", "replay"), required=True)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--capture-root", type=Path, required=True)
    args = parser.parse_args()
    repo, state, started, torch = Path.cwd(), empty(args.model), time.monotonic(), None
    args.evidence.mkdir(parents=True, exist_ok=False)
    try:
        from .bootstrap import verify_topology
        source = json.loads(args.source.read_bytes())
        verify_topology(repo, source["github_pr"], source["payload_sha256"])
        grant = authorize(json.loads((repo / AUTHORITY).read_bytes()), source)
        from safeshift.runners.internvl3_snapshot import require_offline_env, network_denied
        require_offline_env()
        if "torch" in sys.modules:
            raise RuntimeError("TORCH_IMPORTED_BEFORE_NETWORK_AND_VISIBILITY_GUARDS")
        from .network import deny_inet
        boundary = deny_inet()
        write(args.evidence / "network.json", boundary)
        with network_denied():
            if args.mode == "replay":
                if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
                    raise RuntimeError("CPU_REPLAY_MUST_HIDE_ALL_GPUS")
                from transformers import AutoTokenizer
                # Replay only opens known local tokenizer files; never imports torch directly.
                snapshot, receipt = verify_snapshot(args.model, repo, args.cache)
                tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
                state.update(replay(args.capture_root, "hnlo-" + grant["attempt_id"] + "-" + args.model, tokenizer))
                state["result"] = "TECHNICAL_VALID" if state["TECHNICAL_HNLO_VALID"] else "N/A"
            else:
                state["runtime"] = environment(args.model, repo)
                state["environment"] = "EXACT_MATCH"
                import torch
                for i in range(torch.cuda.device_count()):
                    torch.cuda.reset_peak_memory_stats(i)
                state["memory_before"] = memory(torch)
                if args.mode == "probe":
                    probe(args.model, repo, args.evidence, source, grant, args.cache, state, capture_root=args.capture_root)
                else:
                    state["result"] = "ENVIRONMENT_VALID"
    except BaseException as error:
        state.update(result="FAILED", error_type=type(error).__name__, reason=str(error),
                     failure_traceback=traceback.format_exc())
        with (args.evidence / "error.log").open("x", encoding="utf-8") as stream:
            stream.write(state["failure_traceback"])
            stream.flush()
            os.fsync(stream.fileno())
        # Unrecognized process failure is handled as shared/fatal by the parent.
        state["common_fatal"] = isinstance(error, (PermissionError, OSError)) or any(
            marker in str(error) for marker in ("SOURCE", "AUTHORITY", "CHECKSUM", "INVENTORY", "SECCOMP", "NETWORK", "AUDITED", "TORN", "SEALED"))
    finally:
        try:
            state["memory_after"] = memory(torch)
        except BaseException as error:
            state["memory_collection_error"] = type(error).__name__
        state["elapsed_seconds"] = time.monotonic() - started
        write(args.evidence / "result.json", state)
    return 0 if state["result"] not in ("FAILED", "BLOCKED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
