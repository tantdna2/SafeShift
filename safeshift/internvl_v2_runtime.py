"""V2 native capture; exact external campaign permits guard real load/generate."""
import hashlib
import math
from pathlib import Path
import time
from unittest.mock import patch

from safeshift.candidates.source import ROOT, require
from safeshift.internvl_grammar import (
    InternVLGrammarV2, VERSION, POLICY, PROCESSOR, HNLO_STATUS, validate_trace,
)
from safeshift.pilot.artifacts import read, write, write_bytes, sha, safe
from safeshift.pilot.contract import digest, parse_label, require_hash, PROMPT_SHA

IDENTITY = "internvl35-grammar-v2-native-qualification-v1"
SERIES = IDENTITY + "-technical-only"
LIMITS = {"loads": 1, "calls": 1, "seconds": 1800, "max_new_tokens": 64}
FROZEN = {
    "safeshift/internvl_grammar.py": "a3cde12d4dbe463acc9d87bcc36c440492636d7479024876c04ef1c1645c69ca",
    "configs/grammar/internvl35_v2.json": "f6e66ee753bc9c3447aa5b33d52838c226f428b87bafbd8a070bf95edce7e99e",
    "configs/pilot/classification_c1.txt": PROMPT_SHA,
}


def authorize(*args, **kwargs):
    from safeshift.internvl_v2_campaign import authorize as gate
    return gate(*args, **kwargs)


def runtime_sources(repo=ROOT):
    # Reuse the existing dependency inventory, without inheriting any authority.
    from safeshift.fulltrain.contract import sources
    return sorted(set(sources(repo) + list(FROZEN) + [
        "safeshift/diagnostic173_grammar.py", "safeshift/internvl_v2_runtime.py",
        "scripts/internvl_v2.py", "scripts/smoke_kaggle173.py",
        "safeshift/verification173.py", "scripts/verify_kaggle173_inputs.py",
        "configs/grammar/internvl35_v2_runtime.json",
        "safeshift/internvl_v2_campaign.py", "scripts/internvl_v2_campaign.py",
        "safeshift/internvl_v2_memory.py",
    ]))


def source_spec(repo=ROOT):
    return {"identity": IDENTITY, "manifest": {p: sha(Path(repo) / p) for p in runtime_sources(repo)}}


def check_source(spec, repo=ROOT):
    require(type(spec) is dict and set(spec) == {"identity", "manifest"}
            and spec["identity"] == IDENTITY, "V2_SOURCE_IDENTITY")
    require(set(spec["manifest"]) == set(runtime_sources(repo)), "V2_EXACT_SOURCE_INVENTORY")
    for name, expected in spec["manifest"].items():
        require_hash(expected)
        require(sha(safe(repo, name)) == expected, "V2_SOURCE_HASH:" + name)
    for name, expected in FROZEN.items():
        require(spec["manifest"][name] == expected, "V2_APPROVED_METHOD_CHANGED")
    return digest(spec)


def request_binding(spec, request):
    """Immutable single-image technical manifest, never a scientific cohort.

    This checks structure/identity only, not custody or authority. A future
    exact-run release must pin its digest externally before enabling execution.
    """
    require(type(request) is dict and set(request) == {
        "schema", "identity", "series_id", "attempt_id", "split", "ordinal",
        "sample_id", "image", "image_sha256", "source_sha256", "limits",
    }, "V2_EXACT_REQUEST_FIELDS")
    require(request["schema"] == IDENTITY + "-request" and request["identity"] == IDENTITY
            and request["series_id"] == SERIES and request["attempt_id"] == "attempt-0001",
            "V2_SEPARATE_SERIES_ATTEMPT")
    require(request["split"] == "TRAIN" and type(request["ordinal"]) is int
            and request["ordinal"] == 0, "V2_TECHNICAL_ORIGINAL_ORDINAL0_ONLY")
    require(type(request["sample_id"]) is str and 1 <= len(request["sample_id"]) <= 128
            and all(c.isascii() and (c.isalnum() or c in "-_") for c in request["sample_id"]),
            "V2_OPAQUE_SAMPLE_ID")
    from safeshift.pilot.artifacts import relative
    relative(request["image"])
    require_hash(request["image_sha256"])
    require(request["source_sha256"] == digest(spec), "V2_REQUEST_SOURCE_BINDING")
    require(request["limits"] == LIMITS and all(type(request["limits"][k]) is int for k in LIMITS),
            "V2_EXACT_ENGINEERING_LIMITS")
    return digest(request)


def trace_binding(spec, request, tokenizer_sha):
    request_binding(spec, request)
    descriptor = read(ROOT / "configs/grammar/internvl35_v2.json")
    return {"source_sha256": digest(spec), "tokenizer_sha256": tokenizer_sha,
        "model_revision_sha256": digest(descriptor["model_revision"]),
        "input_sha256": request["image_sha256"], "prompt_sha256": PROMPT_SHA,
        "generation_sha256": digest(POLICY),
        "series_sha256": digest({"series": SERIES, "request": request})}


def native_grammar(tokenizer, eos, input_ids, logit_width):
    """Expose padded head columns to the unchanged full-vocabulary verifier.

    No tokens are added/resized/re-encoded. The trie only admits original native
    paths/EOS; extra head columns remain disallowed, but their raw scores are
    retained and included in the mask/argmax audit.
    """
    tokenizer_size = len(tokenizer)
    require(type(logit_width) is int and tokenizer_size <= logit_width <= 200000,
            "V2_NATIVE_LOGIT_WIDTH")
    require(all(type(i) is int and 0 <= i < tokenizer_size for i in input_ids),
            "V2_INPUT_TOKENIZER_RANGE")
    class VocabularyView:
        def __len__(self):
            return logit_width
        def __getattr__(self, name):
            return getattr(tokenizer, name)
    native = InternVLGrammarV2(tokenizer, eos, input_ids)
    full = InternVLGrammarV2(VocabularyView(), eos, input_ids)
    require(full.receipt() == native.receipt(), "V2_PADDED_HEAD_MUST_NOT_CHANGE_GRAMMAR")
    return full


class Capture:
    """Synchronous durable full-vocabulary evidence at the outer forward boundary."""
    def __init__(self, grammar, folder, deadline):
        self.grammar, self.folder, self.deadline = grammar, Path(folder), deadline
        self.raw_hashes, self.step_hashes = [], []
        self.actual = None
        require(0 < grammar.vocab <= 200000, "V2_VOCAB_MEMORY_BOUND")

    def check_time(self):
        require(time.monotonic() < self.deadline, "V2_CALL_DEADLINE")

    def forward(self, module, args, kwargs, output):
        import torch
        self.check_time()
        index = len(self.raw_hashes)
        require(index == len(self.step_hashes) and index < self.grammar.required_tokens,
                "V2_FORWARD_PROCESSOR_ORDER_OR_BUDGET")
        require(output.logits.ndim == 3 and output.logits.shape[0] == 1
                and output.logits.shape[-1] == self.grammar.vocab, "V2_FORWARD_LOGIT_SHAPE")
        last = output.logits[0, -1, :].detach().float().cpu()
        # Binary bytes preserve NaN/Inf/error evidence too. JSON never invents a
        # replacement finite score. This write completes before processor dispatch.
        binary = last.contiguous().numpy().astype("<f4", copy=False).tobytes()
        raw_hash = write_bytes(self.folder / f"steps/{index:03d}.f32", binary)
        write(self.folder / f"steps/{index:03d}.forward.json", {
            "step": index, "raw_sha256": raw_hash, "vocab": self.grammar.vocab,
            "encoding": "float32-little-endian", "origin": "forward_before_processors",
            "original_dtype": str(output.logits.dtype), "all_finite": bool(torch.isfinite(last).all()),
        })
        self.raw_hashes.append(raw_hash)
        require(bool(torch.isfinite(last).all()), "V2_NONFINITE_RAW_PRESERVED")

    def processors(self, original, *args, **kwargs):
        from transformers.generation.logits_process import LogitsProcessorList
        require(self.actual is None, "V2_PROCESSOR_LIST_REBUILT")
        actual = original(*args, **kwargs)
        self.actual = [type(p).__module__ + "." + type(p).__name__ for p in actual]
        write(self.folder / "processors.json", {"actual": self.actual})
        require(self.actual == [PROCESSOR], "V2_EXACT_NATIVE_PROCESSOR_REQUIRED")
        capture = self

        class ObservedList(LogitsProcessorList):
            def __call__(self, input_ids, scores, **unused):
                capture.check_time()
                index = len(capture.step_hashes)
                require(len(capture.raw_hashes) == index + 1, "V2_RAW_MUST_PRECEDE_PROCESSOR")
                require(list(scores.shape) == [1, capture.grammar.vocab]
                        and input_ids.ndim == 2 and input_ids.shape[0] == 1, "V2_PROCESSOR_SHAPE")
                import torch
                raw = capture.raw(index)
                require(scores[0].detach().float().cpu().tolist() == raw, "V2_SCORES_CHANGED_BEFORE_MASK")
                prefix = input_ids[0].tolist()
                require(prefix[:len(capture.grammar.input_ids)] == list(capture.grammar.input_ids),
                        "V2_PROCESSOR_INPUT_PREFIX")
                require(len(prefix) == len(capture.grammar.input_ids) + index, "V2_PROCESSOR_STEP_PREFIX")
                # Only the actual admitted native processor applies the mask.
                masked = actual(input_ids, scores)
                vector = masked[0].detach().float().cpu()
                require(not bool(torch.isnan(vector).any()) and not bool(torch.isposinf(vector).any()),
                        "V2_INVALID_MASKED_SCORE")
                values = [None if x == -math.inf else x for x in vector.tolist()]
                record = {"step": index, "prefix_ids": prefix, "masked_logits": values,
                          "raw_sha256": capture.raw_hashes[index]}
                checksum = write(capture.folder / f"steps/{index:03d}.masked.json", record)
                capture.step_hashes.append(checksum)
                return masked

        return ObservedList(actual)

    def raw(self, index):
        import struct
        path = self.folder / f"steps/{index:03d}.f32"
        require(path.stat().st_size == 4 * self.grammar.vocab
                and sha(path) == self.raw_hashes[index], "V2_RAW_VECTOR_HASH_SIZE")
        return list(struct.unpack("<" + "f" * self.grammar.vocab, path.read_bytes()))

    def steps(self):
        require(len(self.raw_hashes) == len(self.step_hashes), "V2_INCOMPLETE_CAPTURE")
        rows = []
        for i, checksum in enumerate(self.step_hashes):
            path = self.folder / f"steps/{i:03d}.masked.json"
            require(sha(path) == checksum, "V2_MASKED_VECTOR_HASH")
            row = read(path)
            require(row.pop("raw_sha256") == self.raw_hashes[i], "V2_STEP_RAW_BINDING")
            row["raw_logits"] = self.raw(i)
            rows.append(row)
        return rows


def replay_saved(sample, tokenizer, independent_decoder, binding, raw_sha256):
    """Offline readback after caller verifies archive/source/request custody.

    Hashes supplied from raw.json only bind that record's members; the caller
    must pin raw_sha256 externally (the controller uses its durable write hash).
    """
    sample = Path(sample)
    require(sha(sample / "raw.json") == raw_sha256, "V2_RAW_BEFORE_PARSE_HASH")
    raw = read(sample / "raw.json")
    grammar = native_grammar(tokenizer, raw["grammar"]["eos"], raw["input_ids"], raw["logit_width"])
    require(raw["tokenizer_size"] == len(tokenizer), "V2_TOKENIZER_SIZE")
    capture = Capture(grammar, sample, time.monotonic())
    capture.raw_hashes = raw["raw_vector_hashes"]
    capture.step_hashes = raw["masked_vector_hashes"]
    require(len(capture.raw_hashes) <= 64 and len(capture.step_hashes) <= 64, "V2_REPLAY_STEP_BOUND")
    return validate_trace(grammar, independent_decoder, {**raw, "steps": capture.steps()}, binding)


def generate_prepared(backend, inputs, sample, binding, deadline):
    """Shared actual generate/capture path; only tests inject scripted forward."""
    authorize()
    import torch
    from safeshift.candidates.backend import persist_ids
    sample = Path(sample)
    grammar = native_grammar(backend.tokenizer, backend.generation.eos_token_id,
                             inputs["input_ids"][0].tolist(), backend.logit_width)
    require(backend.key == "internvl35", "V2_INTERNVL_ONLY")
    require(all(getattr(backend.generation, k) == v for k, v in POLICY.items() if k != "batch_size"),
            "V2_FROZEN_GREEDY_POLICY")
    write(sample / "grammar.json", grammar.receipt())
    capture = Capture(grammar, sample, deadline)
    original = backend.model._get_logits_processor
    handle = backend.model.register_forward_hook(capture.forward, with_kwargs=True)
    try:
        with patch.object(backend.model, "_get_logits_processor",
                          lambda *a, **k: capture.processors(original, *a, **k)), torch.inference_mode():
            capture.check_time()
            authorize("call")  # Durable cross-VM campaign permit immediately before generate.
            capture.check_time()
            write(sample / "native_call.json", {"identity": IDENTITY, "invocation": 1,
                                                "binding": binding, "limits": LIMITS})
            result = backend.model.generate(**inputs, generation_config=backend.generation,
                                             prefix_allowed_tokens_fn=grammar.callback())
    finally:
        handle.remove()
    # Store IDs even if prefix/shape is wrong; then decode, store exact response,
    # and only then parse/replay. No posthoc cleanup or fence stripping.
    input_ids, generated = persist_ids(result, inputs, "internvl35", sample / "native.json")
    response = backend.tokenizer.decode(generated, skip_special_tokens=True,
                                        clean_up_tokenization_spaces=False)
    raw = {"schema": VERSION + "-trace", "binding": binding, "grammar": grammar.receipt(),
        "policy": dict(POLICY), "actual_logits_processors": capture.actual,
        "capture_origin": "scripted_before_processors" if backend.evidence_kind == "SYNTHETIC" else "forward_before_processors",
        "evidence_kind": backend.evidence_kind,
        "capture_error": None, "input_ids": input_ids, "generated_ids": generated,
        "response": response, "raw_vector_hashes": capture.raw_hashes,
        "masked_vector_hashes": capture.step_hashes, "logit_width": grammar.vocab,
        "tokenizer_size": len(backend.tokenizer), "hnlo": None, "hnlo_status": HNLO_STATUS}
    checksum = write(sample / "raw.json", raw)
    require(sha(sample / "raw.json") == checksum, "V2_RAW_BEFORE_PARSE_HASH")
    saved = read(sample / "raw.json")
    label = parse_label(saved["response"])
    # Hash failures are technical custody errors, never a rescued INVALID.
    capture.steps()
    verification_error = None
    try:
        verified = replay_saved(sample, backend.tokenizer, backend.cpu_tokenizer, binding, checksum)
        write(sample / "trace-verification.json", verified)
    except ValueError as error:
        verification_error = type(error).__name__
        write(sample / "trace-failure.json", {"type": verification_error, "status": "FAIL"})
    status = "INVALID" if label is None else "TECHNICAL_ERROR" if verification_error else "SUCCESS"
    result = {"status": status, "label": label if status == "SUCCESS" else None,
              "raw_sha256": checksum, "trace_verified": verification_error is None,
              "hnlo": None, "hnlo_status": HNLO_STATUS, "scientific_results_excluded": True}
    write(sample / "result.json", result)
    return result


class NativeBackend:
    def __init__(self, source, weights):
        authorize("load")
        from safeshift.candidates.backend import CandidateBackend
        prompt = (ROOT / "configs/pilot/classification_c1.txt").read_text(encoding="utf8")
        self.backend = CandidateBackend("internvl35", source, weights, prompt, device="cuda:0")
        self.backend.logit_width = self.backend.config.text_config.vocab_size
        self.backend.evidence_kind = "NATIVE"
        self.environment = self.backend.environment

    def generate(self, image_path, sample, binding, deadline):
        authorize()
        from PIL import Image
        from safeshift.candidates.inputs import prepare_inputs, validate_inputs
        from safeshift.candidates.backend import transfer_inputs
        b = self.backend
        with Image.open(image_path) as original:
            require(getattr(original, "n_frames", 1) == 1, "STILL_IMAGE_REQUIRED")
            original.load()
            with original.convert("RGB") as image:
                rendered, inputs = prepare_inputs(b.processor, "internvl35", b.prompt, image)
                detail = validate_inputs(b.processor, "internvl35", b.config, rendered, inputs, b.prompt)
        write(Path(sample) / "request.json", {"prompt": b.prompt, "rendered_prompt": rendered,
            "input_ids": inputs["input_ids"][0].tolist(), "input_detail": detail,
            "generation": b.generation.to_dict(), "binding": binding})
        inputs = transfer_inputs(inputs, b.device, b.dtype)
        return generate_prepared(b, inputs, sample, binding, deadline)


def execute_attempt(spec, request, inputs_root, out, source, weights, deadline, *, factory=NativeBackend):
    """One exclusive load/call. Failures remain consumed/unknown; never resume."""
    authorize()
    check_source(spec)
    request_binding(spec, request)
    require(time.monotonic() < deadline <= time.monotonic() + LIMITS["seconds"], "V2_ATTEMPT_DEADLINE")
    out = Path(out)
    # Parent creates the run directory exclusively. This reservation also fences
    # repeated direct worker dispatch into that directory, including load failure.
    write(out / "attempt.json", {"request": request, "source": spec, "binding": digest(request)})
    image = safe(inputs_root, request["image"])
    require(sha(image) == request["image_sha256"], "V2_IMAGE_HASH")
    binding = trace_binding(spec, request, sha(Path(source) / "tokenizer.json"))
    write(out / "load-reservation.json", {"loads": 1, "identity": IDENTITY})
    backend = factory(source, weights)
    write(out / "loaded.json", backend.environment)
    require(time.monotonic() < deadline, "V2_PRECALL_DEADLINE")
    check_source(spec)
    require(sha(image) == request["image_sha256"], "V2_PRECALL_IMAGE_HASH")
    sample = out / "sample"
    sample.mkdir(exist_ok=False)
    write(sample / "reservation.json", {"calls": 1, "binding": binding})
    return backend.generate(image, sample, binding, deadline)


def summary(out, error=None):
    out = Path(out)
    status, result = "TECHNICAL_ERROR", None
    p = out / "sample/result.json"
    if p.is_file() and error is None:
        result = read(p)
        require(sha(out / "sample/raw.json") == result["raw_sha256"], "V2_RESULT_RAW_HASH")
        require(result["status"] in ("SUCCESS", "INVALID", "TECHNICAL_ERROR")
                and result["hnlo"] is None and result["hnlo_status"] == HNLO_STATUS
                and all((out / p).is_file() for p in ("attempt.json", "load-reservation.json",
                    "loaded.json", "sample/reservation.json", "sample/native_call.json")), "V2_RESULT_CUSTODY")
        status = result["status"]
    return {"identity": IDENTITY, "series_id": SERIES, "status": status,
        "result": result, "error": error,
        "load_reservations": int((out / "load-reservation.json").exists()),
        "weights_loaded": (out / "loaded.json").exists(),
        "call_reservations": int((out / "sample/reservation.json").exists()),
        "native_call_markers": int((out / "sample/native_call.json").exists()),
        "consumption": "COMPLETED" if status in ("SUCCESS", "INVALID") else "UNKNOWN_NO_RETRY",
        "hnlo": None, "hnlo_status": HNLO_STATUS, "automatic_retry": False,
        "scientific_results_excluded": True, "scientific_qualified": False,
        "historical_predictions_imported": 0}
