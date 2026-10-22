"""Same V4 native inference, with separate passive observation journals."""
from copy import deepcopy
from dataclasses import replace
import hashlib

from ..hnlo_train.backend import Backend as BaselineBackend
from ..hnlo_train.capture import persist_torch


class Backend(BaselineBackend):
    def __init__(self, repo, cache, inputs, index, source, runtime, checkpoint, observer):
        self.observer, self.handles = observer, []
        try:
            observer.event("before_model_load")
            super().__init__(repo, "qwen3", cache, inputs, index, source, runtime, checkpoint)
            from .cohort import NEW_RUN
            self.context = replace(self.context, run_id=NEW_RUN, command="qwen3-s2-recovery224-worker")
            observer.event("after_model_load")
            self.handles = observer.hooks(self.model)
        except BaseException as error:
            observer.failure(error)
            if hasattr(self, "stack"):
                self.stack.close()
            raise

    def generate(self, row, cap):
        from safeshift.runners.contracts import Request, Task
        from safeshift.runners.qwen3_placement import require_loaded_state
        from ..hnlo_hf import greedy
        observe = self.observer
        self.cap = cap
        try:
            data = (self.inputs / f"{row['ordinal']:06d}.image").read_bytes()
            if hashlib.sha256(data).hexdigest() != row["image_sha256"]:
                raise ValueError("STAGED_IMAGE_CHECKSUM_MISMATCH")
            cap.write("runtime-t1", self.t1)
            self.runner._clear_call_state(self.model)
            observe.event("before_prepare")
            prepared = self.runner.prepare_input(Request(Task.CLASSIFICATION, str(row["ordinal"]),
                "opaque-image", data, "p2-classification-c1-v1", self.prompt), self.context)
            inputs = prepared.inputs
            observe.event("after_prepare", tensors={k: {"shape": list(v.shape),
                "dtype": str(v.dtype), "device": str(v.device)} for k, v in inputs.items()},
                image_grid_thw=inputs["image_grid_thw"].tolist())
            config = deepcopy(self.model.generation_config)
            kwargs = greedy(config, deepcopy(self.policy["decoding"]))
            require_loaded_state(self.model)
            cap.write("call", {"configuration": config.to_dict(), "kwargs": kwargs,
                               "input_shapes": {k: list(v.shape) for k, v in inputs.items()}})
            observe.event("before_native_generate")
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, generation_config=config, **kwargs)
            observe.event("after_native_generate")
            observe.event("before_raw_persistence")
            persist_torch(output, inputs["input_ids"][0].tolist(), self.candidates, self.tokenizer,
                          cap, config.to_dict(), kwargs, self.torch)
            observe.event("after_raw_persistence")
            require_loaded_state(self.model)
            self.runner._clear_call_state(self.model)
            self.cap = None
            observe.event("after_clear_before_frame_return")
            # Locals leave scope on return, exactly as in the V4 adapter.
        except BaseException as error:
            observe.failure(error)
            raise

    def close(self):
        try:
            super().close()
        finally:
            for handle in self.handles:
                handle.remove()
