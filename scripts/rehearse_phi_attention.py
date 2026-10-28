"""CPU evidence using reviewed local Phi text/code. No weights, CUDA or forward.

Run with the unchanged Phi dependency pins. Fetch only the three named text/code
files at MODELS['phi']['revision'] beforehand; --snapshot points to that directory.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import shutil
import re
import sys
import tempfile
from unittest.mock import patch

from safeshift.pilot.artifacts import sha, write
from safeshift.pilot.contract import MODELS, source_digest
from safeshift.pilot.phi_attention import (PHI_ATTENTION_FILES, cpu_attention_probe, eager_phi,
                                         verify_phi_attention, verified_sources)


def rehearse(repo, snapshot, base_commit):
    if not re.fullmatch("[0-9a-f]{40}", base_commit):
        raise ValueError("EXACT_BASE_COMMIT_REQUIRED")
    import torch
    import transformers
    from transformers.models.clip.modeling_clip import CLIPVisionModel, CLIPSdpaAttention, CLIPFlashAttention2
    hashes, payload = verified_sources(repo, snapshot)
    before = dict(hashes)
    forbidden = AssertionError("NO_CUDA_WEIGHTS_FLASH_SDPA_OR_FORWARD_ALLOWED")
    with ExitStack() as guards:
        for name in ("init", "_lazy_init", "is_available", "device_count", "get_device_capability"):
            guards.enter_context(patch.object(torch.cuda, name, side_effect=forbidden))
        guards.enter_context(patch.object(torch.nn.functional, "scaled_dot_product_attention", side_effect=forbidden))
        guards.enter_context(patch.object(torch, "load", side_effect=forbidden))
        guards.enter_context(patch.object(transformers.PreTrainedModel, "from_pretrained", side_effect=forbidden))
        with eager_phi(repo, snapshot) as (config, cls, module, receipt):
            for bad in (module.Phi3FlashAttention2, module.Phi3SdpaAttention,
                        module.CLIPAttentionFA2, CLIPSdpaAttention, CLIPFlashAttention2):
                guards.enter_context(patch.object(bad, "__init__", side_effect=forbidden))
            guards.enter_context(patch.object(cls, "forward", side_effect=forbidden))
            # Use the actual remote config class and Transformers deserializer.
            cases = {}
            for declared in ("eager", "flash_attention_2"):
                synthetic = deepcopy(payload)
                synthetic["_attn_implementation"] = declared
                observed, unused = type(config).from_dict(synthetic, attn_implementation="eager",
                                                          return_unused_kwargs=True)
                cases[declared] = {"effective_after_deserialization": observed._attn_implementation,
                                   "eager_kwarg_still_available": "attn_implementation" in unused}
                if observed._attn_implementation != declared or "attn_implementation" in unused:
                    raise AssertionError("DESERIALIZATION_REPRODUCTION_CHANGED")
                if declared == "flash_attention_2":
                    # Reproduce original hard blocker before model construction.
                    with patch("transformers.modeling_utils.is_flash_attn_2_available", return_value=False):
                        try:
                            cls._autoset_attn_implementation(observed, torch_dtype=torch.float16)
                        except ImportError as error:
                            cases[declared]["original_failure"] = type(error).__name__
                            cases[declared]["requires_flash_attn"] = "flash_attn" in str(error)
                        else:
                            raise AssertionError("EXPECTED_ORIGINAL_FLASH_IMPORT_ERROR")
                observed._attn_implementation = "eager"
                with torch.device("meta"):
                    model = cls._from_config(observed, torch_dtype=torch.float16,
                                             attn_implementation="eager")
                cases[declared]["fixed_modules"] = verify_phi_attention(model, module)
                if any(t.device.type != "meta" or (t.is_floating_point() and t.dtype != torch.float16)
                       for t in (*model.parameters(), *model.buffers())):
                    raise AssertionError("META_FP16_ONLY_REQUIRED")
                del model
            # Separately prove why fixing Phi's outer config alone is insufficient.
            unbound_clip = deepcopy(module.CLIP_VIT_LARGE_PATCH14_336_CONFIG)
            unbound_clip._attn_implementation = None
            auto_clip = CLIPVisionModel._autoset_attn_implementation(unbound_clip, check_device_map=False)
            if auto_clip._attn_implementation != "sdpa":
                raise AssertionError("EXPECTED_CLIP_AUTO_SDPA")
            receipt.update(cases=cases, clip_without_explicit_override="sdpa")
        # Exercise the production pre-consumption probe with a local source-only
        # download double. It must request exactly the reviewed three-file closure.
        with tempfile.TemporaryDirectory(dir=Path(repo) / "data/processed") as temporary:
            local = Path(temporary) / MODELS["phi"]["revision"]
            local.mkdir()
            for name in PHI_ATTENTION_FILES:
                shutil.copyfile(Path(snapshot) / name, local / name)
            with patch("huggingface_hub.snapshot_download", return_value=str(local)) as download:
                receipt["production_cpu_probe"] = cpu_attention_probe(repo)
            if download.call_args.kwargs != {"revision": MODELS["phi"]["revision"],
                                             "allow_patterns": list(PHI_ATTENTION_FILES)}:
                raise AssertionError("SOURCE_ONLY_DOWNLOAD_CONTRACT_CHANGED")
    after, _ = verified_sources(repo, snapshot)
    if before != after:
        raise AssertionError("SOURCE_BYTES_CHANGED")
    return {**receipt, "status": "CPU_REHEARSAL_PASS_NOT_KAGGLE",
            "source_sha256": source_digest(repo), "torch": torch.__version__,
            "weights": "NOT_DOWNLOADED_OR_LOADED", "cuda": "GUARDED_NOT_CALLED",
            "inference": "GUARDED_NOT_RUN", "verified_text_hashes_unchanged": before == after,
            "python": sys.version.split()[0], "platform": sys.platform,
            "base_commit": base_commit,
            "rehearsal_script_sha256": sha(Path(__file__)),
            "model_revision": MODELS["phi"]["revision"]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--base-commit", required=True,
                   help="Exact base SHA verified by the caller; runtime digest binds working source bytes")
    args = p.parse_args()
    repo = Path(__file__).resolve().parents[1]
    result = rehearse(repo, Path(args.snapshot), args.base_commit)
    target = Path(args.output)
    write(target, result)
    write(target.with_suffix(".sha256.json"), {"sha256": sha(target)})
    print(result["status"], result["cases"])


if __name__ == "__main__":
    main()
