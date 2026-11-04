"""V2 bounded preflight/controller CLI. Native execution is release-fenced."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

from safeshift import internvl_v2_runtime as runtime
from safeshift.candidates.source import ROOT, require, verify_snapshot
from safeshift.candidates.train_inputs import checkpoint
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.fulltrain import environment, provision, supervision


def policy():
    value = read(ROOT / "configs/grammar/internvl35_v2_runtime.json")
    require(value["identity"] == runtime.IDENTITY and value["limits"] == runtime.LIMITS
            and value["production_activation"] is False and value["execution_authority"] is None,
            "V2_RUNTIME_DESCRIPTOR")
    return environment.policy("internvl35", value["resource_policy"])


def check_checkpoint(inputs, out):
    from safeshift.candidates.loading import verify_weights
    marker, source, weights = checkpoint(inputs, "internvl35")
    spec = verify_snapshot(source, "internvl35")
    locked = verify_weights(weights, "internvl35")
    write(out / "checkpoint.json", {"marker_sha256": sha(marker),
        "model": spec["id"], "revision": spec["revision"],
        "source_hashes": spec["files"], "checkpoint_lock": locked,
        "weights_loaded": False, "status": "ACTUAL_BYTES_VERIFIED"})
    return source, weights


def processor_check(source, out):
    from PIL import Image
    from safeshift.candidates.loading import native_setup
    from safeshift.candidates.inputs import prepare_inputs, validate_inputs
    from tokenizers import Tokenizer
    from safeshift.internvl_grammar import mask_logits
    from transformers.generation.logits_process import PrefixConstrainedLogitsProcessor
    import torch
    evidence = {}
    processor, tokenizer, config, _ = native_setup(source, "internvl35", evidence)
    prompt = (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf8")
    with Image.new("RGB", (448, 448), (128, 128, 128)) as image:
        rendered, inputs = prepare_inputs(processor, "internvl35", prompt, image)
        detail = validate_inputs(processor, "internvl35", config, rendered, inputs, prompt)
    grammar = runtime.native_grammar(tokenizer, read(source / "generation_config.json")["eos_token_id"],
                                     inputs["input_ids"][0].tolist(), config.text_config.vocab_size)
    independent = Tokenizer.from_file(str(source / "tokenizer.json"))
    native = PrefixConstrainedLogitsProcessor(grammar.callback(), num_beams=1)
    steps = 0
    for text, path in zip(grammar.texts, grammar.paths):
        require(independent.decode(list(path), skip_special_tokens=False) == text, "V2_INDEPENDENT_PATH")
        prefix = list(grammar.input_ids)
        for token in path + (grammar.eos[0],):
            scores = torch.zeros((1, grammar.vocab), dtype=torch.float32)
            scores[0, token] = 1
            actual = native(torch.tensor([prefix]), scores)[0].tolist()
            require([None if v == -float("inf") else v for v in actual] ==
                    mask_logits(grammar, prefix[len(grammar.input_ids):], scores[0].tolist()),
                    "V2_NATIVE_MASK_ORACLE")
            prefix.append(token)
            steps += 1
    result = {"status": "CPU_SOFTWARE_PASS", "scope": "SYNTHETIC_PROCESSOR_NO_MODEL_FORWARD",
        "native": evidence, "input_detail": detail, "grammar": grammar.receipt(),
        "logit_width": grammar.vocab, "tokenizer_size": len(tokenizer),
        "mask_steps": steps, "loads": 0, "calls": 0}
    write(out / "processor.json", result)
    return result


def worker(stage, spec, out, scratch, inputs, request=None, deadline=None):
    require(stage in ("setup", "preflight", "native"), "V2_WORKER_STAGE")
    if stage == "native":
        runtime.authorize()  # Before source, private request or Input access.
    runtime.check_source(spec)
    out, scratch, inputs = Path(out), Path(scratch), Path(inputs)
    budgets = policy()
    if stage == "setup":
        from safeshift.candidates.train_runtime import prepare_runtime
        env = provision.clean_env(ROOT, scratch)
        python, env = prepare_runtime(ROOT, "internvl35", scratch, out, env,
                                       time.monotonic() + budgets["setup_seconds"])
        # env is constructed from an allowlist; no credential export.
        write(out / "runtime.json", {"python": str(python), "env": env})
        return
    from scripts.smoke_kaggle173 import bind_cuda_driver, driver_check
    from safeshift.fulltrain.preflight import storage_probe
    write(out / "resources.json", environment.resources("internvl35", budgets, scratch, out))
    write(out / "allocation.json", storage_probe(scratch, out,
        scratch_bytes=budgets["scratch_probe_bytes"], output_bytes=budgets["output_probe_bytes"]))
    bind_cuda_driver(out)
    write(out / "software.json", environment.software("internvl35"))
    write(out / "hardware.json", driver_check("internvl35", budgets, out, "worker"))
    write(out / "cuda.json", environment.cuda("internvl35", budgets))
    source, weights = check_checkpoint(inputs, out)
    processor_check(source, out)
    write(out / "preload-resources.json", environment.resources("internvl35", budgets, scratch, out))
    if stage == "native":
        require(request is not None and deadline is not None, "V2_EXACT_REQUEST_DEADLINE")
        runtime.execute_attempt(spec, read(request), inputs, out, source, weights, deadline)
    else:
        write(out / "preflight.json", {"status": "LIVE_GPU_PREFLIGHT_PASS", "weights_loaded": False,
            "inference_verified": False, "scientific_qualified": False, "loads": 0,
            "calls": 0, "owner_slots_consumed": 0, "native_execution": "BLOCKED"})


def worker_command(python, stage, spec_path, out, scratch, inputs, request, deadline):
    command = [str(python), "-B", "-m", "scripts.internvl_v2", "--worker", stage,
        "--spec", str(spec_path), "--output", str(out), "--scratch", str(scratch), "--inputs", str(inputs)]
    if stage == "native":
        command += ["--request", str(request), "--deadline", str(deadline)]
    return command


def launch(spec, *, mode="preflight", inputs=Path("/kaggle/input"), output=Path("/kaggle/working"),
           scratch_parent=Path("/kaggle/temp"), request=None):
    require(mode in ("preflight", "execute"), "V2_MODE")
    if mode == "execute":
        runtime.authorize()
    runtime.check_source(spec)
    budgets = policy()
    identity = runtime.IDENTITY if mode == "execute" else runtime.IDENTITY + "-preflight-" + uuid.uuid4().hex
    out = Path(output) / identity
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(scratch_parent) / identity
    error = None
    deadline = time.monotonic() + runtime.LIMITS["seconds"]
    try:
        scratch.mkdir(parents=True, exist_ok=False)
        write(out / "source.json", spec)
        if mode == "execute":
            require(request is not None, "V2_REQUEST_REQUIRED")
            runtime.request_binding(spec, read(request))
            # Snapshot exact bytes before child dispatch; outside caller mutation
            # cannot change this attempt's data/source/call identity.
            write(out / "execution-request.json", read(request))
            request = out / "execution-request.json"
        env = provision.clean_env(ROOT, scratch)
        write(out / "initial-resources.json", environment.resources("internvl35", budgets, scratch, out))
        for stage in ("setup", "native" if mode == "execute" else "preflight"):
            python = sys.executable
            if stage != "setup":
                prepared = read(out / "runtime.json")
                python, env = prepared["python"], prepared["env"]
                env["CUDA_VISIBLE_DEVICES"] = "0"
            supervision.run(worker_command(python, stage, out / "source.json", out, scratch,
                                            inputs, request, deadline), cwd=ROOT, env=env,
                deadline=min(deadline, time.monotonic() + budgets[
                    "setup_seconds" if stage == "setup" else "diagnostic_seconds"]),
                log=out / (stage + "-supervisor.log"), receipt=out / (stage + "-supervisor.json"),
                max_log_bytes=budgets["max_log_bytes"], watch_log_root=out)
        require((out / ("sample/result.json" if mode == "execute" else "preflight.json")).is_file(),
                "V2_MISSING_TERMINAL_CHILD_RECEIPT")
    except BaseException as failure:
        # Do not echo arbitrary exception text (paths/raw/credentials). Child
        # streams stay in the private archive; class/stage receipts locate errors.
        error = {"type": type(failure).__name__, "reason": "STAGE_FAILED_NO_AUTOMATIC_RETRY"}
    try:
        if mode == "execute":
            result = runtime.summary(out, error)
        else:
            result = {"status": "BLOCKED" if error else "LIVE_GPU_PREFLIGHT_PASS",
                "error": error, "weights_loaded": False, "inference_verified": False,
                "scientific_qualified": False, "loads": 0, "calls": 0, "owner_slots_consumed": 0,
                "gates": {"G0": "BLOCKED_EXECUTION_AUTHORITY", "G1": "NOT_RUN", "G2": "NOT_RUN",
                          "G3": "NOT_RUN", "G4": "NOT_RUN", "G5": "NOT_RUN_WEIGHTS_INFERENCE", "G6": "PENDING_EXPORT"}}
            for gate, files in {"G1": ("checkpoint.json",), "G2": ("software.json",),
                                "G3": ("processor.json",), "G4": ("cuda.json", "preload-resources.json")}.items():
                if all((out / name).is_file() for name in files):
                    result["gates"][gate] = "PASS"
        write(out / "summary.json", result)
    except BaseException as failure:
        result = {"status": "TECHNICAL_ERROR", "error": {"type": type(failure).__name__},
                  "consumption": "UNKNOWN_NO_RETRY", "hnlo": None, "hnlo_status": runtime.HNLO_STATUS}
        write(out / "summary-error.json", result)
    checksum = export(out, Path(str(out) + ".zip"))
    # Successful return proves sealing; an export exception never reports PASS.
    return {**result, "archive_sha256": checksum, "G6": "SEALED_ARCHIVE_PASS", "execution_authority": None}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--mode", choices=("preflight", "execute"), default="preflight")
    modes.add_argument("--worker", choices=("setup", "preflight", "native"))
    parser.add_argument("--inputs", type=Path, default=Path("/kaggle/input"))
    parser.add_argument("--output", type=Path, default=Path("/kaggle/working"))
    parser.add_argument("--scratch", type=Path, default=Path("/kaggle/temp"))
    parser.add_argument("--request", type=Path)
    parser.add_argument("--deadline", type=float)
    args = parser.parse_args(argv)
    if args.mode == "execute" or args.worker == "native":
        runtime.authorize()
    spec = read(args.spec)
    if args.worker:
        worker(args.worker, spec, args.output, args.scratch, args.inputs, args.request, args.deadline)
        return 0
    result = launch(spec, mode=args.mode, inputs=args.inputs, output=args.output,
                    scratch_parent=args.scratch, request=args.request)
    print(json.dumps(result), flush=True)
    return 0 if result["status"] in ("SUCCESS", "INVALID", "LIVE_GPU_PREFLIGHT_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
