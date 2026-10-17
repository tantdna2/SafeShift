"""Pending-approval read-only lm_head probe. No HNLO equivalence claim."""

from contextlib import contextmanager
import sys

from safeshift.ls1.runtime import summarize_vector
from safeshift.ls1.t1_cpu import StarmieAdapter
from safeshift.runners.moondream_binding import verified_source, verify_function
from safeshift.runners.moondream_snapshot import MODEL_ID, REVISION, TOKENIZER_REVISION
from .hnlo_capture import tensor_evidence, vector


class HeadObserver:
    """Clone inside the forward hook, before upstream can mask its return in-place.

    The live reference is read at the next head call (or finally on return/error).
    It is never used as raw evidence, changed, returned, or used to select tokens.
    The observed argmax remains an inference until native-answer reconciliation.
    """

    def __init__(self, head, capture, identify_step):
        self.head, self.capture, self.identify_step = head, capture, identify_step
        self.pending = None
        self.calls = 0
        self.events = []

    def flush(self):
        if self.pending is not None:
            index, tensor = self.pending
            self.capture.write(f"processed-{index:03d}", tensor_evidence(tensor))
            self.pending = None

    def hook(self, module, args, output):
        # First operation on this output: detach/clone while still inside forward.
        clone = output.detach().clone()
        index = self.calls
        self.calls += 1
        self.capture.write(f"raw-{index:03d}", tensor_evidence(clone))
        self.pending, previous = (index, output), self.pending
        if previous is not None:
            self.capture.write(f"processed-{previous[0]:03d}", tensor_evidence(previous[1]))
        event = self.identify_step()
        self.events.append(event)
        self.capture.write(f"hook-{index:03d}", {"step": index, **event})
        return None

    @contextmanager
    def installed(self):
        if self.head._forward_hooks:
            raise ValueError("PREEXISTING_HEAD_HOOKS_FORBIDDEN")
        handle = self.head.register_forward_hook(self.hook)
        try:
            yield self
        finally:
            # Detach even if persistence, phase detection or native query raises.
            handle.remove()
            self.flush()
            self.capture.write("hook-summary", {"calls": self.calls,
                "removed": not bool(self.head._forward_hooks), "events": self.events,
                "token_id_status": "INFERRED_UNTIL_NATIVE_ANSWER_CHECK"})


def verified_binding(runner):
    """Verify exact file bytes AND bound upstream code before attaching any hook."""
    binding, inner = runner.binding, runner.model.model
    modules, snapshot = binding.modules, binding.snapshot
    binding.check()
    moon, text = modules["moondream"], modules["text"]
    if type(inner) is not moon.MoondreamModel or inner.text is not runner.model.model.text:
        raise ValueError("PINNED_MOONDREAM_INSTANCE_REQUIRED")
    functions = {}
    for name in ("query", "_prefill_prompt", "_decode_one_tok", "_generate_answer"):
        function = getattr(inner, name)
        if getattr(function, "__self__", None) is not inner:
            raise ValueError("PINNED_BOUND_METHOD_REQUIRED")
        functions[name] = verify_function(function.__func__, moon, snapshot,
                                          "moondream.py", "MoondreamModel." + name)
    head_function = verify_function(text.lm_head, text, snapshot, "text.py", "lm_head")
    if moon.lm_head is not head_function:
        raise ValueError("LM_HEAD_GLOBAL_BINDING_CHANGED")
    hf = modules["hf_moondream"]
    if type(runner.model) is not hf.HfMoondream:
        raise ValueError("PINNED_HF_MOONDREAM_REQUIRED")
    verify_function(type(runner.model).query.fget, hf, snapshot,
                    "hf_moondream.py", "HfMoondream.query")
    if runner.model.query != inner.query:
        raise ValueError("NATIVE_QUERY_BINDING_CHANGED")
    # Hash-check files as well as function identities; never execute source here.
    for filename in ("moondream.py", "text.py", "hf_moondream.py", "config.py"):
        verified_source(snapshot, filename)
    if (inner.config.tokenizer.eos_id != 0 or inner.config.tokenizer.answer_id != 3
            or inner.config.text.group_size is not None):
        raise ValueError("PINNED_TOKENIZER_IDS_OR_PRECISION_CHANGED")
    head = inner.text.lm_head
    linear = runner.backend.torch.nn.Linear
    if type(head) is not linear or head.forward.__func__ is not linear.forward:
        raise ValueError("NATIVE_LINEAR_HEAD_REQUIRED")

    def identify():
        frame = sys._getframe(1)
        try:
            while frame is not None:
                if frame.f_code is functions["_prefill_prompt"].__code__:
                    return {"phase": "prefill", "position": frame.f_locals["pos"]
                            + int(frame.f_locals["prompt_tokens"].shape[1]),
                            "input_ids": frame.f_locals["prompt_tokens"][0].tolist()}
                if frame.f_code is functions["_decode_one_tok"].__code__:
                    # pos_ids is the consumed token position; its head predicts
                    # the following slot, whereas prefill predicts prompt end.
                    return {"phase": "decode", "position": int(frame.f_locals["pos_ids"][0].item()) + 1}
                frame = frame.f_back
        finally:
            del frame
        raise ValueError("HEAD_CALL_OUTSIDE_VERIFIED_GENERATION")

    return head, identify


def reconcile(observer, native, tokenizer, candidate_ids, *, answer_id=3, eos_id=0, max_tokens=32):
    """Read only persisted tensors; fail closed for extra/missing/out-of-order calls."""
    capture = observer.capture
    if not 1 <= observer.calls <= max_tokens + 1 or len(observer.events) != observer.calls:
        raise ValueError("MISSING_OR_EXTRA_HEAD_CALL")
    steps, inferred = [], []
    for i, event in enumerate(observer.events):
        if (event["phase"] != ("prefill" if i == 0 else "decode")
                or event["position"] != observer.events[0]["position"] + i):
            raise ValueError("HEAD_STEP_ORDER_OR_POSITION_MISMATCH")
        raw = vector(capture.journal.read(f"raw-{i:03d}"))
        post = vector(capture.journal.read(f"processed-{i:03d}"))
        if len(raw) != len(post) or answer_id not in range(len(raw)):
            raise ValueError("POST_MASK_SHAPE_MISMATCH")
        if any(a != b for j, (a, b) in enumerate(zip(raw, post)) if i == 0 or j != answer_id):
            raise ValueError("UNEXPECTED_POST_MASK_CHANGE")
        if i and post[answer_id] != float("-inf"):
            raise ValueError("ANSWER_ID_MASK_NOT_OBSERVED")
        # This is explicitly inferred, not an observed native token ID.
        token = max(range(len(post)), key=post.__getitem__)
        inferred.append(token)
        steps.append({"step": i, "generated_token": token,
                      "raw": summarize_vector(raw, candidate_ids, token),
                      "processed": summarize_vector(post, candidate_ids, token)})
    capture.write("inferred-ids", {"ids": inferred, "status": "NOT_YET_RECONCILED"})
    if inferred[-1] != eos_id or eos_id in inferred[:-1]:
        raise ValueError("NO_TERMINAL_EOS_OR_UNCONSUMED_LOOKAHEAD")
    if type(native) is not dict or set(native) != {"answer"} or type(native["answer"]) is not str:
        raise ValueError("EXACT_NATIVE_ANSWER_REQUIRED")
    text = tokenizer.decode(inferred, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    if text != native["answer"] or tokenizer.encode(text, add_special_tokens=False) != inferred[:-1]:
        raise ValueError("INFERRED_IDS_NATIVE_ANSWER_MISMATCH")
    return capture.write("trace", {"version": "hnlo-moondream-hook-pending-v1",
        "input_ids": observer.events[0]["input_ids"],
        "input_id_scope": "NATIVE_QUERY_PROMPT_EXCLUDES_IMAGE_EMBEDDINGS",
        "continuation_ids": inferred, "decoded_text": text,
        "candidate_token_ids": list(candidate_ids), "steps": steps,
        "generation_config": {"eos_token_id": eos_id}, "forced_assistant_prefix_ids": [],
        "token_id_status": "INFERRED_MATCHES_NATIVE_ANSWER_AND_ENCODING",
        "equivalence": "PENDING_RESEARCH_LEAD_APPROVAL"})


class MoondreamDiagnostic:
    """Reuse an already loaded runner, pinned bridge, caches and native query.

    No second generation is performed. State audit covers stable layout/device/
    dtype invariants; KV contents naturally change during the single query.
    """

    def __init__(self, runner):
        self.runner, self.used = runner, False

    def generate(self, prepared, context, capture):
        from safeshift.runners.contracts import Task
        from safeshift.runners.moondream2 import DECODING, audit_model_state, serialize_native
        from safeshift.runners.moondream_snapshot import exclusive_owner, require_offline
        if self.used:
            raise RuntimeError("DIAGNOSTIC_NO_RETRY")
        self.used = True
        r = self.runner
        observer = None
        try:
            with exclusive_owner():
                r._condition(context)
                require_offline()
                if ((capture.metadata["model_id"], capture.metadata["revision"]) != (MODEL_ID, REVISION)
                        or capture.metadata["tokenizer_revision"] != TOKENIZER_REVISION
                        or context.source_kind != "SYNTHETIC" or prepared[0] != Task.CLASSIFICATION):
                    raise ValueError("SYNTHETIC_NATIVE_CLASSIFICATION_ONLY")
                head, identify = verified_binding(r)
                tokenizer = StarmieAdapter(r.model.model.tokenizer)
                candidate_ids = capture.runtime_t1(tokenizer)
                before = audit_model_state(r.model, r.backend.torch)
                capture.write("state-before", before)
                for block in r.model.model.text.blocks:
                    block.kv_cache.k_cache.zero_()
                    block.kv_cache.v_cache.zero_()
                observer = HeadObserver(head, capture, identify)
                capture.write("call", {"query": DECODING["query"], "reasoning": False,
                    "stream": False, "model_revision": REVISION, "input_prompt": prepared[2],
                    "software": r.backend.software, "snapshot": r.evidence})
                try:
                    with observer.installed(), r.backend.torch.inference_mode(), r.binding.installed():
                        native = r.model.query(prepared[1], prepared[2], reasoning=False, stream=False,
                                               settings=dict(DECODING["query"]))
                        capture.write("native-answer", {"lossless_native_utf8": serialize_native(native).decode("utf-8")})
                finally:
                    after = audit_model_state(r.model, r.backend.torch)
                    capture.write("state-after", after)
                    verified_binding(r)
                    if before != after:
                        raise ValueError("STABLE_MODEL_STATE_DRIFT")
                return reconcile(observer, native, tokenizer, candidate_ids)
        except BaseException as error:
            r.valid = False
            capture.failure(error)
            raise
