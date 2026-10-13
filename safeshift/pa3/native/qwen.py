"""Real Qwen raw-only backend. Native loading/preprocessing reuse audited LS1.

No LS1 experiment orchestration or reference/calibration calls. Output summaries
and native IDs are durably saved before decode, validation or semantic parsing.
"""

from copy import deepcopy
from datetime import datetime, timezone

from safeshift.ls1.runtime import NativeScorer, summarize_tensor
from . import access, preflight


class QwenRawScorer(NativeScorer):
    def __init__(self, snapshot, tokenizer, candidate_ids, *, repo, settings):
        access.require(settings["mode"], settings, repo)
        preflight.source(repo, settings["source_commit"])
        if settings["mode"] == "full-train":
            from . import train
            train.verify_prior(repo, settings, settings["train_inputs_root"], tokenizer)
        elif settings["mode"] == "pilot-train":
            from . import pilot
            pilot.verify_prior(repo, settings, settings["pilot_inputs_root"], tokenizer)
        elif settings["mode"] == access.DIAGNOSTIC["mode"]:
            from . import seminar
            seminar.verify_prior(repo, settings, settings["diagnostic_inputs_root"], tokenizer)
        access.model_ticket(repo, settings)
        super().__init__("qwen2_5", snapshot, tokenizer, candidate_ids, repo=repo)
        self.settings = deepcopy(settings)
        self.authority_repo = repo
        # The processor must use exactly the T1 tokenizer behavior as well.
        from safeshift.ls1.tokenizer import probe
        if probe(self.processor.tokenizer) != probe(tokenizer):
            raise ValueError("PROCESSOR_TOKENIZER_T1_MISMATCH")

    def evidence(self):
        return {"hardware": self.hardware, "software": self.software, "snapshot": self.snapshot_receipt,
                "generation_config": self.config.to_dict(), "processor_class": type(self.processor).__name__,
                "model_class": type(self.model).__name__, "precision": "FP16", "attention": "sdpa",
                "quantization": "NONE", "prompt": self.prompt}

    def generate(self, image, journal, prefix):
        access.image_ticket(self.authority_repo, self.settings, image, journal, prefix)
        if self.failed:
            raise RuntimeError("FAILED_SCORER_NO_RETRY")
        try:
            self.validator()
            if hasattr(self.model, "rope_deltas"):
                self.model.rope_deltas = None
            if hasattr(self.model, "_cache"):
                self.model._cache = None
            inputs = self.prepare(image, ())  # freely generated C1; no forced prefix
            config = deepcopy(self.config)
            kwargs = {**self.condition["decoding"], "max_new_tokens": 32,
                      "do_sample": False, "num_beams": 1, "num_return_sequences": 1,
                      "return_dict_in_generate": True, "output_logits": True, "output_scores": True}
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, generation_config=config, **kwargs)
            native = journal.write(prefix + ".native", {
                "sequences": output.sequences.tolist(), "input_ids": inputs["input_ids"][0].tolist(),
                "generation_config": config.to_dict(), "generation_kwargs": kwargs,
                "input_shapes": {k: list(v.shape) for k, v in inputs.items()},
                "image_grid_thw": inputs["image_grid_thw"].tolist(),
                "raw_steps": len(output.logits), "processed_steps": len(output.scores),
                "timestamp_utc": datetime.now(timezone.utc).isoformat()})
            sequences, input_ids = native["sequences"], native["input_ids"]
            if len(sequences) != 1 or sequences[0][:len(input_ids)] != input_ids:
                raise ValueError("NATIVE_GENERATION_PREFIX_MISMATCH")
            ids = sequences[0][len(input_ids):]
            if not ids or len(ids) != len(output.logits) or len(ids) != len(output.scores):
                raise ValueError("RAW_AND_PROCESSED_REQUIRED_EVERY_STEP")
            steps = []
            for i, token in enumerate(ids):
                steps.append(journal.write(prefix + f".step-{i:02d}", {
                    "step": i, "generated_token": token,
                    "raw": summarize_tensor(output.logits[i], self.candidate_ids, token, self.torch),
                    "processed": summarize_tensor(output.scores[i], self.candidate_ids, token, self.torch)}))
            text = self.tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            raw = journal.write(prefix + ".raw", {
                "version": "pa3-qwen-raw-v1", "input_ids": input_ids, "continuation_ids": ids,
                "decoded_text": text, "candidate_token_ids": list(self.candidate_ids), "steps": steps,
                "generation_config": native["generation_config"], "generation_kwargs": kwargs,
                "forced_assistant_prefix_ids": [], "timestamp_utc": native["timestamp_utc"]})
            self.validator()  # failures still retain the complete raw evidence
            return raw
        except BaseException:
            self.failed = True
            raise
