"""Proposed Qwen2.5-equivalent reductions. NOT equivalent to full-vector retention."""
from copy import deepcopy
from datetime import datetime, timezone

from safeshift.ls1.runtime import summarize_tensor
from safeshift.pa3.artifacts import json_bytes
from safeshift.pa3.native.journal import Journal
from safeshift.pa3.native.native_score import score
from .contract import EVIDENCE


class SampleCapture:
    def __init__(self, root, identity, max_bytes=2 * 2**20):
        self.journal = Journal(root, create=True)
        self.max_bytes, self.written = max_bytes, 0
        self.write("identity", {**identity, "evidence_contract": EVIDENCE})
        self.write("started", {"utc": datetime.now(timezone.utc).isoformat()})

    def write(self, name, value):
        size = len(json_bytes(value))
        # Reserve space for one terminal failure; never truncate a vector/step.
        if self.written + size > self.max_bytes - 16384:
            raise OSError("SAMPLE_EVIDENCE_BUDGET_EXCEEDED_NO_TRUNCATION")
        result = self.journal.write(name, value)
        self.written += size
        return result

    def failure(self, error):
        self.journal.write("error", {"type": type(error).__name__,
            "status": "INTERRUPTED" if isinstance(error, (KeyboardInterrupt, SystemExit)) else "TECHNICAL_ERROR"})


def persist(output, input_ids, candidates, tokenizer, cap, config, kwargs, summarize):
    """All native IDs and raw/processed step summaries fsynced BEFORE first decode."""
    native = cap.write("native", {"sequences": output.sequences.tolist(), "input_ids": list(input_ids),
        "raw_steps": len(output.logits or ()), "processed_steps": len(output.scores or ()),
        "tensor_layouts": {kind: [{"dtype": str(t.dtype), "shape": list(t.shape), "device": str(t.device)}
                                  for t in tensors] for kind, tensors in
                           (("raw", output.logits or ()), ("processed", output.scores or ()))},
        "generation_config": deepcopy(config), "generation_kwargs": deepcopy(kwargs),
        "candidate_token_ids": list(candidates)})
    sequences = native["sequences"]
    if len(sequences) != 1 or sequences[0][:len(input_ids)] != list(input_ids):
        raise ValueError("NATIVE_PREFIX_MISMATCH")
    ids = sequences[0][len(input_ids):]
    # Preserve every available native tensor summary, even on a length mismatch.
    for kind, tensors in (("raw", output.logits or ()), ("processed", output.scores or ())):
        for i, tensor in enumerate(tensors):
            # Missing token is a structural error, never an invented generated ID.
            if i >= len(ids):
                raise ValueError("ORPHAN_NATIVE_TENSOR")
            cap.write(f"{kind}-{i:03d}", summarize(tensor, candidates, ids[i]))
    if not 1 <= len(ids) <= 32 or native["raw_steps"] != len(ids) or native["processed_steps"] != len(ids):
        raise ValueError("ALL_MAX32_RAW_PROCESSED_STEPS_REQUIRED")
    trace = {"version": "hnlo-train-raw-v1", "input_ids": list(input_ids), "continuation_ids": ids,
        "candidate_token_ids": list(candidates), "generation_config": config, "generation_kwargs": kwargs,
        "forced_assistant_prefix_ids": [], "decoded_text": tokenizer.decode(ids, skip_special_tokens=True,
            clean_up_tokenization_spaces=False),
        "steps": [{"step": i, "generated_token": token,
                   **{k: cap.journal.read(f"{k}-{i:03d}") for k in ("raw", "processed")}}
                  for i, token in enumerate(ids)]}
    cap.write("trace", trace)


def persist_torch(output, input_ids, candidates, tokenizer, cap, config, kwargs, torch):
    return persist(output, input_ids, candidates, tokenizer, cap, config, kwargs,
                   lambda t, ids, token: summarize_tensor(t, ids, token, torch))


def replay(journal, tokenizer):
    """Recompute HNLO with the unchanged baseline scorer from sealed raw summaries."""
    if not journal.verify():
        raise ValueError("RAW_SAMPLE_SEAL_REQUIRED_BEFORE_PARSE")
    identity = journal.read("identity")
    native, trace = journal.read("native"), journal.read("trace")
    from ..hnlo_capture import ordered_t1_ids
    from safeshift.ls1.tokenizer import probe
    if (journal.read("runtime-t1") != probe(tokenizer)
            or trace["candidate_token_ids"] != ordered_t1_ids(journal.read("runtime-t1"))
            or trace["candidate_token_ids"] != native["candidate_token_ids"]
            or trace["generation_config"] != native["generation_config"]
            or trace["generation_kwargs"] != native["generation_kwargs"]
            or native["input_ids"] != trace["input_ids"]
            or native["sequences"] != [trace["input_ids"] + trace["continuation_ids"]]
            or native["raw_steps"] != len(trace["steps"]) or native["processed_steps"] != len(trace["steps"])
            or not 1 <= len(trace["steps"]) <= 32):
        raise ValueError("NATIVE_TRACE_BINDING_MISMATCH")
    call = journal.read("call")
    if call["configuration"] != native["generation_config"] or call["kwargs"] != native["generation_kwargs"]:
        raise ValueError("CALL_CONFIGURATION_CHANGED")
    if journal.read("raw-provenance") != {"processors": []}:
        raise ValueError("EMPTY_ACTUAL_PROCESSORS_REQUIRED")
    stop = journal.read("stopping")
    eos = trace["generation_config"]["eos_token_id"]
    eos = eos if type(eos) is list else [eos]
    if stop != {"max_length": len(trace["input_ids"]) + 32, "eos_token_ids": eos}:
        raise ValueError("ACTUAL_STOPPING_SETTINGS_MISMATCH")
    effective = {**trace["generation_config"], **trace["generation_kwargs"]}
    if (effective.get("do_sample") is not False or effective.get("num_beams", 1) != 1
            or effective.get("num_return_sequences", 1) != 1 or effective.get("max_new_tokens") != 32
            or any(effective.get(k) is not True for k in ("return_dict_in_generate", "output_logits", "output_scores"))
            or trace["forced_assistant_prefix_ids"]):
        raise ValueError("EXACT_NATIVE_GREEDY_CAPTURE_REQUIRED")
    from ..one_click.worker import no_forcing
    from types import SimpleNamespace
    no_forcing(SimpleNamespace(to_dict=lambda: effective))
    expected = {"identity", "started", "call", "runtime-t1", "raw-provenance", "stopping", "native", "trace", "seal", "complexity"}
    for i, step in enumerate(trace["steps"]):
        for kind in ("raw", "processed"):
            name = f"{kind}-{i:03d}"
            expected.add(name)
            if (journal.read(name) != step[kind]
                    or native["tensor_layouts"][kind][i]["shape"] != [1, step[kind]["vocab_size"]]):
                raise ValueError("RAW_SUMMARY_TRACE_MISMATCH")
    # errors forbid scientific eligibility but retain every persisted observation.
    allowed = expected | {"error"}
    if set(journal.inventory()) - allowed:
        raise ValueError("UNKNOWN_SAMPLE_EVIDENCE")
    result = score(str(identity["ordinal"]), trace, tokenizer)
    if journal.exists("error"):
        result.update(status=journal.read("error")["status"], score=None, details=None,
                      errors=[journal.read("error")["type"]])
    return result
