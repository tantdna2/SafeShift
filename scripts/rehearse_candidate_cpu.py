"""Public-source G2/G3 CPU checks; no model construction, weights or inference.

Source download reuses pilot_source_audit. Parsing, persistence and failure tests
reuse the pilot suite. This command is a qualification probe, not a backend.
"""
import argparse
import copy
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import inspect
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.pilot.artifacts import Store, read, sha, write
from safeshift.pilot.contract import GENERATION, LEVELS, PROMPT_SHA, parse_label, source_digest
from safeshift.pilot.diagnostics import failure_detail
from safeshift.pilot.runner import error_record

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "configs/cpu_g2_g3/public_source_lock.json"
CASES = ((1, 1), (448, 448), (640, 480), (200, 1200), (1200, 200), (2048, 1536))


def require(value, message):
    if not value:
        raise ValueError(message)


def verify_snapshot(snapshot, key):
    """Never execute local Python until every public source byte is locked."""
    spec = read(LOCK)[key]
    require(snapshot.is_dir() and not snapshot.is_symlink(), "SNAPSHOT_DIRECTORY_REQUIRED")
    actual = {p.name for p in snapshot.iterdir() if p.is_file()}
    require(actual == set(spec["files"]), "SNAPSHOT_EXACT_ALLOWLIST_REQUIRED")
    for name, checksum in spec["files"].items():
        p = snapshot / name
        require(not p.is_symlink() and p.stat().st_nlink == 1, "SOURCE_ALIAS_FORBIDDEN")
        require(sha(p) == checksum, "SOURCE_CHECKSUM:" + name)
    return spec


def environment(key):
    require(sys.prefix != sys.base_prefix, "ISOLATED_VENV_REQUIRED")
    import site
    require(not site.ENABLE_USER_SITE, "USER_SITE_FORBIDDEN")
    expected = {}
    for line in (ROOT / f"configs/cpu_g2_g3/{key}.requirements.txt").read_text().splitlines():
        if line and not line.startswith("--") and "==" in line:
            requirement, _, marker = line.partition(";")
            if marker and sys.platform != "win32":
                continue
            name, version = requirement.strip().split("==")
            expected[name] = version
    for name, version in expected.items():
        require(metadata.version(name) == version, "DEPENDENCY_VERSION:" + name)
    check = subprocess.run([sys.executable, "-m", "pip", "check"], text=True, capture_output=True)
    require(check.returncode == 0, "PIP_CHECK:" + check.stdout + check.stderr)
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze", "--all"],
                            text=True, capture_output=True, check=True).stdout.splitlines()
    import torch, torchvision, transformers, tokenizers, accelerate
    for module in (torch, torchvision, transformers, tokenizers, accelerate):
        require(Path(module.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), "LIBRARY_OUTSIDE_VENV")
    from torchvision.ops import nms
    require(torch.version.cuda is None, "CPU_ONLY_TORCH_REQUIRED")
    # An actual compiled torchvision operator catches ABI/import-only gaps.
    require(nms(torch.tensor([[0., 0., 1., 1.]]), torch.tensor([1.]), 0.5).tolist() == [0], "NMS_ABI")
    torch.set_num_threads(2)
    return {"python": platform.python_version(), "platform": platform.platform(),
            "isolated_venv": True, "user_site": False, "pip_check": check.stdout.strip(),
            "freeze_all": sorted(freeze), "compiled_torchvision_nms": "PASS"}


def guard(stack):
    """Fail closed on network, weights and CUDA even inside public remote code."""
    import torch, transformers, safetensors.torch
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="",
                      HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")
    for target in ("connect", "connect_ex"):
        stack.enter_context(patch.object(socket.socket, target, side_effect=AssertionError("NETWORK_FORBIDDEN")))
    for target in ("init", "_lazy_init", "is_available", "device_count", "get_device_capability",
                   "synchronize", "mem_get_info"):
        stack.enter_context(patch.object(torch.cuda, target, side_effect=AssertionError("CUDA_FORBIDDEN")))
    for owner, name in ((torch, "load"), (safetensors.torch, "load_file"),
                        (transformers.PreTrainedModel, "from_pretrained")):
        stack.enter_context(patch.object(owner, name, side_effect=AssertionError("WEIGHTS_FORBIDDEN")))


def native_setup(snapshot, key, evidence):
    import transformers
    opts = dict(local_files_only=True, trust_remote_code=key == "minicpm4")
    spec = read(LOCK)[key]
    opts.update(revision=spec["revision"], code_revision=spec["revision"])
    processor = transformers.AutoProcessor.from_pretrained(str(snapshot), **opts)
    tokenizer = transformers.AutoTokenizer.from_pretrained(str(snapshot), **opts)
    config = transformers.AutoConfig.from_pretrained(str(snapshot), **opts)
    require(processor.tokenizer.get_vocab() == tokenizer.get_vocab(), "TOKENIZER_PROCESSOR_VOCAB_MISMATCH")
    if key == "internvl35":
        from transformers.models.auto.modeling_auto import MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING
        model_class = MODEL_FOR_IMAGE_TEXT_TO_TEXT_MAPPING[type(config)]
    else:
        from transformers.dynamic_module_utils import get_class_from_dynamic_module
        model_class = get_class_from_dynamic_module(config.auto_map["AutoModel"], str(snapshot),
                                                    local_files_only=True, revision=spec["revision"],
                                                    code_revision=spec["revision"])
    # Import and map the real class. Do not instantiate it or claim weight loading.
    evidence["native_classes"] = {name: type(obj).__name__ for name, obj in
                                  (("processor", processor), ("tokenizer", tokenizer), ("config", config))}
    evidence["native_classes"]["model_import_only"] = model_class.__name__
    evidence["trust_remote_code"] = opts["trust_remote_code"]
    evidence["native_image_config"] = processor.image_processor.to_dict()
    evidence["implementation_sha256"] = {}
    for obj in (type(processor), type(processor.image_processor), type(tokenizer), model_class):
        evidence["implementation_sha256"][obj.__name__] = sha(inspect.getfile(obj))
    return processor, tokenizer, config, model_class


def prepare(processor, key, prompt, image):
    """Exercise the checkpoint's native wrapper text and actual processor."""
    require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA, "FROZEN_C1_SHA")
    if key == "internvl35":
        messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
        rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor(text=rendered, images=image, return_tensors="pt")
    else:
        messages = [{"role": "user", "content": "(<image>./</image>)\n" + prompt}]
        rendered = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = processor([rendered], [[image]], return_tensors="pt", max_length=None)
    require(rendered.count(prompt) == 1, "C1_NOT_PRESERVED_ONCE")
    require("system" not in rendered and "<think>" not in rendered, "HIDDEN_SYSTEM_OR_THINKING")
    return rendered, inputs


def validate_inputs(processor, key, config, rendered, inputs, prompt):
    import torch
    ids, mask = inputs["input_ids"], inputs["attention_mask"]
    require(ids.ndim == 2 and ids.shape[0] == 1 and ids.dtype in (torch.int32, torch.int64), "INPUT_IDS_DTYPE_SHAPE")
    require(mask.shape == ids.shape and bool((mask == 1).all()), "ATTENTION_MASK")
    require(bool((ids >= 0).all()) and bool((ids < len(processor.tokenizer)).all()), "VOCAB_RANGE")
    decoded = processor.tokenizer.decode(ids[0].tolist(), skip_special_tokens=False,
                                        clean_up_tokenization_spaces=False)
    require(decoded.count(prompt) == 1, "EXPANDED_INPUT_C1_TRUNCATED_OR_CHANGED")
    require(ids.shape[1] + GENERATION["max_new_tokens"] <=
            (config.text_config.max_position_embeddings if key == "internvl35" else config.max_position_embeddings),
            "CONTEXT_OVERFLOW")
    pixels = inputs["pixel_values"]
    if key == "internvl35":
        require(config.image_token_id == 151671, "EXACT_4B_HF_IMAGE_TOKEN")
        require(processor.image_seq_length == 256, "NATIVE_256_TOKENS_PER_TILE")
        count = int((ids == config.image_token_id).sum())
        require(pixels.ndim == 4 and list(pixels.shape[1:]) == [3, 448, 448], "INTERNVL_TILES")
        require(1 <= pixels.shape[0] <= 13 and count == pixels.shape[0] * 256, "IMAGE_TOKEN_TILE_COUNT")
        tensors = [pixels]
        detail = {"tiles_including_thumbnail": pixels.shape[0], "image_tokens": count,
                  "pixel_shapes": [list(pixels.shape)]}
    else:
        ip = processor.image_processor
        require((ip.image_feature_size, ip.patch_size, ip.max_slice_nums, ip.scale_resolution, ip.use_image_id) ==
                (config.query_num, config.patch_size, config.slice_config.max_slice_nums,
                 config.slice_config.scale_resolution, config.use_image_id), "MINICPM_CONFIG_PROCESSOR_DRIFT")
        tensors = pixels[0]
        bounds = inputs["image_bound"][0]
        require(len(tensors) == len(bounds) and 1 <= len(tensors) <= 10, "SLICE_BOUND_COUNT")
        require(all(int(end - start) == 64 for start, end in bounds), "SLICE_64_QUERY_TOKENS")
        require(all(int((ids[0, start:end] == processor.tokenizer.unk_id).sum()) == 64
                    for start, end in bounds), "SLICE_PLACEHOLDER_IDS")
        require(len(inputs["tgt_sizes"][0]) == len(tensors), "PATCH_GRID_COUNT")
        for tensor, grid in zip(tensors, inputs["tgt_sizes"][0]):
            require(tensor.shape[0] == 3 and tensor.numel() == 3 * int(grid.prod()) * 14**2,
                    "PIXEL_PATCH_GRID")
        detail = {"slices_including_global": len(tensors), "image_tokens": len(tensors) * 64,
                  "pixel_shapes": [list(t.shape) for t in tensors],
                  "patch_grids": inputs["tgt_sizes"][0].tolist()}
    require(all(t.device.type == "cpu" and t.dtype == torch.float32 and bool(torch.isfinite(t).all())
                for t in tensors), "PIXELS_CPU_FLOAT32_FINITE")
    return {**detail, "input_length": ids.shape[1], "ids_dtype": str(ids.dtype),
            "mask_dtype": str(mask.dtype), "rendered_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "input_ids_sha256": hashlib.sha256(ids.cpu().numpy().tobytes()).hexdigest()}


def processor_probe(processor, key, config, output):
    from PIL import Image
    import torch
    prompt = (ROOT / "configs/pilot/classification_c1.txt").read_bytes().decode()
    require(hashlib.sha256(prompt.encode()).hexdigest() == PROMPT_SHA, "FROZEN_C1_SHA")
    cases = []
    for size in CASES:
        try:
            with Image.new("RGB", size, color=(40, 80, 120)) as image:
                rendered, inputs = prepare(processor, key, prompt, image)
                detail = validate_inputs(processor, key, config, rendered, inputs, prompt)
                # A constant RGB input independently verifies normalization/channel order.
                pixels = inputs["pixel_values"] if key == "internvl35" else inputs["pixel_values"][0]
                mean, std = (([.485, .456, .406], [.229, .224, .225]) if key == "internvl35" else ([.5]*3, [.5]*3))
                expected = (torch.tensor([40, 80, 120]) / 255 - torch.tensor(mean)) / torch.tensor(std)
                for tensor in pixels:
                    require(torch.allclose(tensor.flatten(1).mean(1), expected, atol=1e-5), "RGB_NORMALIZATION")
                cases.append({"status": "PASS", "rgb_size": list(size), **detail})
        except Exception as error:
            cases.append({"status": "FAIL", "rgb_size": list(size),
                          **failure_detail(error, "native_image_processor", "synthetic_rgb")})
    # Actual image decode: content, not a filename extension, determines format.
    with Image.new("RGBA", (64, 80), color=(40, 80, 120, 255)) as rgba:
        path = output / "synthetic_png_under_jpg.jpg"
        rgba.save(path, format="PNG")
        with Image.open(path) as decoded:
            require(decoded.format == "PNG", "SYNTHETIC_PNG_DECODE")
            rgb = decoded.convert("RGB")
            rendered, inputs = prepare(processor, key, prompt, rgb)
            detail = validate_inputs(processor, key, config, rendered, inputs, prompt)
    return {"status": "FAIL" if any(c["status"] == "FAIL" for c in cases) else "PASS",
            "c1_sha256": PROMPT_SHA, "cases": cases,
            "rgba_png_explicit_rgb": detail, "generation": GENERATION,
            "synthetic_png_sha256": sha(path),
            "limits": "Constant-color synthetic images; no industrial quality or weight parity claim"}


def wrapper_probe(model_class, processor, config, key):
    if key == "internvl35":
        from safeshift.pilot.backend import native_generation_config
        from transformers import GenerationConfig
        generation = GenerationConfig.from_pretrained(str(processor._qualification_snapshot), local_files_only=True)
        resolved = native_generation_config(SimpleNamespace(generation_config=generation)).to_dict()
        require(all(resolved[k] == v for k, v in GENERATION.items()), "NATIVE_GENERATION_CONFIG")
        return {"status": "PASS", "scope": "GenerationConfig construction only; generate BLOCKED without weights",
                "frozen_values": {k: resolved[k] for k in GENERATION}, "repetition_penalty": resolved["repetition_penalty"]}
    from PIL import Image
    import torch
    calls = []
    def intercepted(**kwargs):
        calls.append(kwargs)
        return ["SYNTHETIC_WRAPPER_INTERCEPTION_NO_MODEL_CALL"]
    standin = SimpleNamespace(config=config, device=torch.device("cpu"), generate=intercepted)
    prompt = (ROOT / "configs/pilot/classification_c1.txt").read_bytes().decode()
    with Image.new("RGB", (64, 80)) as image:
        model_class.chat(standin, image=image, msgs=[{"role": "user", "content": prompt}],
                         tokenizer=processor.tokenizer, processor=processor, sampling=False)
        model_class.chat(standin, image=image, msgs=[{"role": "user", "content": prompt}],
                         tokenizer=processor.tokenizer, processor=processor, sampling=False,
                         **{k: v for k, v in GENERATION.items() if k != "do_sample"}, do_sample=False)
    observed = calls[1]
    received = {k: observed.get(k, "DROPPED") for k in GENERATION}
    same_contract = (received == GENERATION and not observed.get("decode_text")
                     and observed.get("repetition_penalty", 1.0) == 1.0)
    return {"status": "PASS" if same_contract else "FAIL",
            "scope": "Real unbound chat wrapper, generate intercepted; no inference",
            "received_generation": received, "repetition_penalty": observed.get("repetition_penalty"),
            "sampling_false_defaults": {k: calls[0].get(k, "DROPPED") for k in
                                        ("num_beams", "repetition_penalty", "do_sample", "max_new_tokens")},
            "decode_text": observed.get("decode_text"),
            "reason": "chat filters frozen kwargs, defaults repetition_penalty=1.2 and forces decode_text=True; adapter review required"}


def scripted_outputs(tokenizer, output):
    """Exercise native tokenization/decoding and existing custody with mock IDs.

    No GenerationMixin or model forward is called. Missing EOS alone does not
    change the frozen parser; diagnostic flags and classification stay separate.
    """
    from safeshift.pilot.output_diagnostics import summarize
    store = Store(output / "scripted", {"synthetic": True, "prompt_sha256": PROMPT_SHA})
    cases = [(level, '{"safety_level":"' + level + '"}', level) for level in LEVELS]
    cases += [("whitespace", ' \n{"safety_level":"Level04"}\n', "Level04"),
              ("invalid_json", "not JSON", None),
              ("duplicate_key", '{"safety_level":"Level01","safety_level":"Level04"}', None),
              ("repeated_label", '{"safety_level":"Level01Level01"}', None),
              ("repeated_objects", '{"safety_level":"Level04"}'*2, None),
              ("extra_key", '{"safety_level":"Level04","reason":"x"}', None),
              ("empty_tokens", "", None),
              ("same_output_again", '{"safety_level":"Level04"}', "Level04"),
              ("missing_token", '{"safety_level":"Level04"}', None),
              ("no_eos_valid_json", '{"safety_level":"Level04"}', "Level04"),
              ("truncated_max64", '{"safety_level":"Level04"}'*20, None)]
    records = []
    for i, (name, text, expected) in enumerate(cases):
        ids = tokenizer.encode(text, add_special_tokens=False)
        if name == "missing_token":
            ids = ids[:-1]
        elif name == "truncated_max64":
            ids = ids[:64]
        elif name not in ("empty_tokens", "no_eos_valid_json"):
            ids += [tokenizer.eos_token_id]
        raw = tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        record = {"response": raw, "generated_ids": ids, "eos_token_ids": [tokenizer.eos_token_id],
                  "evidence_kind": "SYNTHETIC_SCRIPTED_LOGITS_NOT_MODEL_PREDICTIONS",
                  "simulation": "TOKEN_IDS_ONLY_NO_LOGITS_NO_MODEL", "sample_id": name,
                  "prompt_sha256": PROMPT_SHA, "generation": GENERATION}
        checksum = store.raw(i, record)
        require(read(store.root / f"samples/{i:06d}/raw.json") == record, "RAW_BEFORE_PARSE")
        label = parse_label(raw)
        require(label == expected, "SCRIPTED_PARSER:" + name)
        records.append({"case": name, "label": label, "tokens": len(ids),
                        "ends_with_eos": bool(ids and ids[-1] == tokenizer.eos_token_id), "raw_sha256": checksum})
    summary = summarize(store.root)
    require(summary["raw_records"] == len(cases) and summary["at_max64_n"] == 1
            and summary["largest_identical_token_sequence_n"] == 2, "SCRIPTED_ACCOUNTING")
    return {"status": "PASS", "scope": "Mock IDs, real tokenizer, existing Store/parser/diagnostics; no generated predictions",
            "cases": records, "summary": summary}


def input_faults(processor, key, config):
    from PIL import Image
    prompt = (ROOT / "configs/pilot/classification_c1.txt").read_bytes().decode()
    with Image.new("RGB", (64, 80)) as image:
        rendered, original = prepare(processor, key, prompt, image)
        faults = {}
        for name in ("ids_float", "mask_zero", "image_token_missing", "pixels_half"):
            inputs = copy.deepcopy(original)
            if name == "ids_float":
                inputs["input_ids"] = inputs["input_ids"].float()
            elif name == "mask_zero":
                inputs["attention_mask"][0, 0] = 0
            elif name == "image_token_missing":
                if key == "internvl35":
                    inputs["input_ids"][inputs["input_ids"] == config.image_token_id] = 0
                else:
                    inputs["input_ids"][0, inputs["image_bound"][0][0][0]] = processor.tokenizer.bos_id
            elif key == "internvl35":
                inputs["pixel_values"] = inputs["pixel_values"].half()
            else:
                inputs["pixel_values"][0] = [t.half() for t in inputs["pixel_values"][0]]
            try:
                validate_inputs(processor, key, config, rendered, inputs, prompt)
            except ValueError as error:
                faults[name] = str(error)
            else:
                raise ValueError("INPUT_CORRUPTION_NOT_REJECTED:" + name)
        try:
            prepare(processor, key, prompt + " changed", image)
        except ValueError as error:
            faults["c1_changed"] = str(error)
        else:
            raise ValueError("CHANGED_C1_ACCEPTED")
    return {"status": "PASS", "rejected": faults}


def run_tests(output):
    sys.path.insert(0, str(ROOT / "tests"))
    suite = unittest.TestSuite()
    # Existing raw-before-parse, duplicate JSON, partial-write/archive and diagnostic
    # tests; never enroll candidates into the production roster or mint a grant.
    loader = unittest.defaultTestLoader
    for name in ("test_pilot.ParserTests", "test_pilot.ArtifactAndEngineTests",
                 "test_phi_evidence", "test_smol_evidence", "test_candidate_cpu"):
        suite.addTests(loader.loadTestsFromName(name))
    with (output / "tests.log").open("x", encoding="utf-8") as stream:
        from contextlib import redirect_stdout, redirect_stderr
        with redirect_stdout(stream), redirect_stderr(stream):
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {"status": "PASS" if result.wasSuccessful() else "FAIL", "run": result.testsRun,
            "failures": len(result.failures), "errors": len(result.errors),
            "skips": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
            "log_sha256": sha(output / "tests.log")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True, choices=("internvl35", "minicpm4"))
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    output = Path(a.output).resolve()
    require(output.is_relative_to((ROOT / "data/processed").resolve()), "OUTPUT_UNDER_DATA_PROCESSED_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    os.environ.update(HF_MODULES_CACHE=str(output / "modules"), HF_HUB_OFFLINE="1",
                      TRANSFORMERS_OFFLINE="1", CUDA_VISIBLE_DEVICES="", HF_HUB_DISABLE_TELEMETRY="1")
    before = source_digest(ROOT)
    inputs = [Path(__file__), ROOT / "scripts/pilot_source_audit.py", ROOT / "tests/test_candidate_cpu.py",
              *sorted((ROOT / "configs/cpu_g2_g3").glob("*"))]
    receipt = {"schema": "safeshift-candidate-cpu-g2-g3-v1", "model_key": a.model,
               "executed_utc": datetime.now(timezone.utc).isoformat(),
               "evidence_kind": "PUBLIC_SOURCE_SYNTHETIC_CPU_NOT_MODEL_PREDICTIONS",
               "synthetic_recipe": {"rgb_color": [40, 80, 120], "sizes": CASES, "randomness": None},
               "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
               "script_sha256": sha(Path(__file__)), "source_lock_sha256": sha(LOCK),
               "rehearsal_sources_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs if p.is_file()},
               "production_source_sha256": before, "checks": {},
               "weights": "NOT_DOWNLOADED_OR_LOADED", "inference": "NOT_RUN", "gpu": "NOT_CALLED"}
    try:
        receipt["checks"]["environment"] = {"status": "PASS", **environment(a.model)}
        snapshot = Path(a.snapshot).resolve()
        spec = verify_snapshot(snapshot, a.model)
        receipt["model"] = {k: spec[k] for k in ("id", "revision")}
        receipt["checks"]["source"] = {"status": "PASS", "files": spec["files"]}
        # Work from a short, revision-named path to keep dynamic imports on Windows
        # reproducible and separate from a user's global HF module cache.
        local = output / spec["revision"]
        shutil.copytree(snapshot, local)
        os.environ["HF_MODULES_CACHE"] = str(output / "modules")
        with ExitStack() as stack:
            guard(stack)
            setup = {}
            processor, tokenizer, config, model_class = native_setup(local, a.model, setup)
            processor._qualification_snapshot = local
            receipt["checks"]["native_load"] = {"status": "PASS", "scope": "processor/tokenizer/config/class import only", **setup}
            receipt["checks"]["processor"] = processor_probe(processor, a.model, config, output)
            receipt["checks"]["generation_wrapper"] = wrapper_probe(model_class, processor, config, a.model)
            receipt["checks"]["scripted_native_tokens_custody"] = scripted_outputs(tokenizer, output)
            receipt["checks"]["native_input_faults"] = input_faults(processor, a.model, config)
    except Exception as error:
        receipt["checks"]["exception"] = {"status": "FAIL", **failure_detail(error, "cpu_qualification", "native_probe")}
    receipt["checks"]["g3_existing_and_candidate_tests"] = run_tests(output)
    for name in ("native_load", "processor", "generation_wrapper", "scripted_native_tokens_custody"):
        receipt["checks"].setdefault(name, {"status": "BLOCKED", "reason": "Earlier CPU check failed; not executed"})
    receipt["checks"]["production_unchanged"] = {"status": "PASS" if before == source_digest(ROOT) else "FAIL"}
    for name, reason in {
        "real_weight_loader_attention": "No weights: real from_pretrained/deserialization and effective layer dispatch untested",
        "real_generation_raw_continuation": "No weights/inference: actual IDs, slicing, EOS, logits/HNLO and raw custody untested",
        "gpu_fp16_memory_driver_behavior": "No authorized GPU: finite activations, per-GPU peak, child driver and industrial C1 quality untested",
        "production_candidate_adapter": "Candidates are not registered pilot backends; adapter/release and independent review pending",
    }.items():
        receipt["checks"][name] = {"status": "BLOCKED", "reason": reason}
    receipt["overall"] = "FAIL" if any(v["status"] == "FAIL" for v in receipt["checks"].values()) else "BLOCKED"
    write(output / "receipt.json", receipt)
    write(output / "receipt.sha256.json", {"sha256": sha(output / "receipt.json")})
    print(a.model, receipt["overall"], {k: v["status"] for k, v in receipt["checks"].items()})
    return 1 if receipt["overall"] == "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
