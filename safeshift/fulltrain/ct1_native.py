"""Native CT1 adapter. Reuse the pinned Qwen setup, with bounded text-only capture."""

from copy import deepcopy
from io import BytesIO
import os
from pathlib import Path
import time

from safeshift.candidates.source import require
from safeshift.evaluation.ct1_contract import ARMS, prompt
from safeshift.pilot.artifacts import safe, write
from . import environment, gpu_driver, memory, qwen

MAX_NEW = 768
MAX_INPUT = 4800
MAX_PIXELS = 2560 * 1440
GIB = 2**30
MIB = 2**20


def release_budgets(drivers):
    return environment.policy("qwen3", {
        "review_mode": "EXTERNAL", "driver_versions": drivers, "free_mib_per_gpu": [13000, 13000],
        "free_gpu0_runtime_mib": 13000, "free_ram_mib": 16384,
        "free_scratch_mib": 14 * 1024, "free_output_mib": 256,
        "scratch_probe_bytes": 16 * MIB, "output_probe_bytes": 8 * MIB,
        "max_log_bytes": 16 * MIB, "setup_seconds": 2400, "diagnostic_seconds": 1200,
    })


def memory_headroom(torch, *, before_call):
    host = environment.host_memory()
    if before_call:
        require(host["available_bytes"] >= 2 * GIB, "CT1_AVAILABLE_HOST_RAM")
    devices = []
    for device in range(2):
        free, total = torch.cuda.mem_get_info(device)
        # Reserved, non-live Torch blocks may be reused by this process.
        active, reserved = torch.cuda.memory_allocated(device), torch.cuda.memory_reserved(device)
        if before_call:
            require(free >= 512 * MIB and free + reserved - active >= 1536 * MIB,
                    f"CT1_GPU_{device}_INSUFFICIENT_HEADROOM")
        devices.append({"free_bytes": free, "total_bytes": total, "allocated_bytes": active,
                        "reserved_bytes": reserved, "peak_bytes": torch.cuda.max_memory_allocated(device)})
    return {"host": host, "devices": devices}


def image_size_allowed(size):
    width, height = size
    return 0 < width <= 2560 and 0 < height <= 2560 and width * height <= MAX_PIXELS


def image_from_bytes(payload):
    from PIL import Image
    with Image.open(BytesIO(payload), formats=("PNG",)) as image:
        require(getattr(image, "n_frames", 1) == 1 and image.mode == "RGB"
                and image_size_allowed(image.size),
                "CT1_BOUNDED_STILL_RGB_PNG_REQUIRED")
        require(not image.info and not image.getexif(), "CT1_IMAGE_METADATA_NOT_ALLOWED")
        image.load()
        return image.copy()


def prepare(processor, image, text):
    messages = [{"role": "user", "content": [{"type": "image", "image": image},
                                             {"type": "text", "text": text}]}]
    inputs = processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                           return_dict=True, return_tensors="pt", truncation=False)
    require(len(inputs["input_ids"]) == 1 and "past_key_values" not in inputs, "CT1_BATCH1")
    count = inputs["input_ids"].shape[1]
    require(0 < count <= MAX_INPUT, "CT1_INPUT_TOKEN_BUDGET")
    require(all(v.device.type == "cpu" for v in inputs.values()), "CT1_CPU_PREPROCESS")
    return inputs


class Backend:
    def __init__(self, checkpoint, repo, *, before_load):
        import torch
        import transformers
        self.torch = torch
        self.processor, self.tokenizer, _ = qwen.native_setup(checkpoint, repo)
        self.prompts = {arm: prompt(arm, repo).decode("utf-8") for arm in ARMS}
        before_load()
        self.model = transformers.Qwen3VLForConditionalGeneration.from_pretrained(
            str(checkpoint), local_files_only=True, trust_remote_code=False, dtype=torch.float16,
            device_map=deepcopy(qwen.DEVICE_MAP), attn_implementation="sdpa")
        self.model.eval()
        qwen.loaded_state(self.model)
        require(hasattr(self.model.model, "rope_deltas"), "CT1_QWEN_ROPE_LAYOUT")
        self.config = qwen.generation(self.model.generation_config)
        require(MAX_INPUT + MAX_NEW <= self.model.config.text_config.max_position_embeddings,
                "CT1_CONTEXT_LIMIT")
        self.eos = self.config.eos_token_id
        self.eos = self.eos if isinstance(self.eos, list) else [self.eos]
        require(self.eos and all(type(i) is int and i >= 0 for i in self.eos), "CT1_EOS_REQUIRED")

    def reset(self):
        self.model.model.rope_deltas = None
        if hasattr(self.model, "_cache"):
            self.model._cache = None

    def generate(self, payload, arm, begin, record_tokens):
        torch = self.torch
        qwen.loaded_state(self.model)
        self.reset()
        for i in range(2):
            torch.cuda.reset_peak_memory_stats(i)
        with image_from_bytes(payload) as image:
            inputs = prepare(self.processor, image, self.prompts[arm])
        before = memory_headroom(torch, before_call=True)
        prefix = inputs["input_ids"][0].tolist()
        request = {"prompt_tokens": len(prefix), "image_grid_thw": inputs["image_grid_thw"].tolist(),
                   "memory_before": before, "max_new_tokens": MAX_NEW}
        inputs = inputs.to(self.model.device)
        try:
            began = time.monotonic()
            with torch.inference_mode():
                begin(request)
                output = self.model.generate(
                    **inputs, generation_config=qwen.generation(self.config), do_sample=False,
                    max_new_tokens=MAX_NEW, return_dict_in_generate=False,
                    output_attentions=False, output_hidden_states=False,
                    output_logits=False, output_scores=False)
            returned = output.detach().cpu().tolist()
            record_tokens({"input_ids": prefix, "returned_ids": returned, "seconds": time.monotonic() - began})
            return self.decode({"input_ids": prefix, "returned_ids": returned})
        finally:
            self.reset()

    def decode(self, tokens):
        prefix, sequences = tokens["input_ids"], tokens["returned_ids"]
        require(len(sequences) == 1 and sequences[0][:len(prefix)] == prefix, "CT1_RETURN_PREFIX")
        generated = sequences[0][len(prefix):]
        require(0 < len(generated) <= MAX_NEW, "CT1_CONTINUATION_BOUND")
        return {
            "raw_text": self.tokenizer.decode(generated, skip_special_tokens=True,
                                               clean_up_tokenization_spaces=False),
            "new_tokens": len(generated), "eos": generated[-1] in self.eos,
            "at_cap": len(generated) == MAX_NEW and generated[-1] not in self.eos,
        }

    def failure_memory(self):
        return memory_headroom(self.torch, before_call=False)

    def record_memory(self):
        """An unavailable telemetry probe must not discard completed model output."""
        try:
            return self.failure_memory()
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            return {"status": "UNAVAILABLE", "error_type": type(error).__name__}


def probe_runtime(snapshot, repo, lock, drivers, scratch, output, data, plan):
    """Run the pinned ABI, CUDA and token envelope checks in a disposable process."""
    from . import preflight as common_preflight
    limits = release_budgets(drivers)
    require(Path(os.environ["SAFESHIFT_RUNTIME_ROOT"]).is_relative_to(scratch), "CT1_RUNTIME_OUTSIDE_SCRATCH")
    evidence = output / "evidence" / "runtime-probe"
    memory.observe(evidence, "before-gate")
    try:
        resources = environment.resources("qwen3", limits, scratch, output,
                                          memory_receipt=evidence / "ram-gate.json")
    except (OSError, ValueError, KeyError):
        memory.observe(evidence, "gate-failure")
        raise
    storage = common_preflight.storage_probe(scratch, output, scratch_bytes=limits["scratch_probe_bytes"],
                                             output_bytes=limits["output_probe_bytes"])
    driver = gpu_driver.bind(evidence)
    physical = gpu_driver.hardware("qwen3", limits, driver, evidence, "probe")
    software = environment.software("qwen3", repo, lock)
    write(evidence / "software.json", software)
    cuda = environment.cuda("qwen3", limits)
    write(evidence / "cuda.json", cuda)
    metadata = qwen.verify_snapshot(snapshot, repo=repo, weights=False, permit_unread_weights=True)
    write(evidence / "checkpoint-metadata.json", metadata)
    processor, tokenizer, _ = qwen.native_setup(snapshot, repo)
    from PIL import Image
    with Image.new("RGB", (448, 448)) as image:
        sample_tokens = {arm: prepare(processor, image, prompt(arm, repo).decode())["input_ids"].shape[1]
                         for arm in ARMS}
    text_tokens = {arm: len(tokenizer.encode(prompt(arm, repo).decode(), add_special_tokens=False))
                   for arm in ARMS}
    from .ct1_run import IMAGE_BYTES, read_sealed
    texts = {arm: prompt(arm, repo).decode() for arm in ARMS}
    counts = {}
    for item in plan["cases"]:
        case, digest = item["case_id"], item["image_sha256"]
        payload = read_sealed(safe(data, "images/" + case + ".png"), digest, IMAGE_BYTES)
        with image_from_bytes(payload) as image:
            counts[case] = {arm: prepare(processor, image, text)["input_ids"].shape[1]
                            for arm, text in texts.items()}
    return {"resources": resources, "storage": storage, "software": software, "physical": physical,
            "cuda": cuda, "checkpoint_metadata": metadata, "fixture_prompt_tokens": sample_tokens,
            "text_tokens": text_tokens, "planned_input_tokens": counts,
            "model_calls": 0, "weights_loaded": False}


def advise_locked_files(root, files, receipt, deadline):
    """Release cache held by already verified input files without writing the mount."""
    results = {}
    for name, size in sorted(files.items()):
        memory.check_deadline(deadline)
        try:
            results[name] = memory.evict_readonly_file(safe(root, name), expected_size=size, deadline=deadline)
        except (OSError, ValueError) as error:
            results[name] = {"advised": False, "error_type": type(error).__name__}
    memory.check_deadline(deadline)
    write(receipt, {"files": results, "effect": "ADVISORY_NOT_RAM_PROOF"})


def verify_checkpoint(snapshot, repo, drivers, evidence, deadline):
    """Hash the locked weights before this process imports Torch or enters CUDA."""
    floor = release_budgets(drivers)["free_ram_mib"] * MIB
    memory.ct1_ram_gate(evidence, "before-checkpoint-ram-gate", floor)
    advice_errors = []
    try:
        checkpoint = qwen.verify_snapshot(snapshot, repo=repo, hash_reader=lambda path, size:
            memory.stream_readonly_sha256(path, expected_size=size, deadline=deadline,
                                          advice_errors=advice_errors, advise_whole_file=False))
    finally:
        write(evidence / "checkpoint-cache-advice.json", {
            "method": "READONLY_SHA256_ADVISE_CONSUMED_PAGES", "errors": advice_errors,
            "available": hasattr(os, "posix_fadvise"), "effect": "ADVISORY_NOT_RAM_PROOF"})
        memory.observe(evidence, "checkpoint-hash-exit")
    return checkpoint
