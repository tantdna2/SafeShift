"""CPU text-only mapping using downloaded official tokenizer JSON, no torch.

Uses an explicitly supplied local dependency directory (no install/network here).
Actual image-expanded boundary and generated alignment remain runtime checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from safeshift.pilot.artifacts import write
from safeshift.pilot.hnlo import probe
from safeshift.pilot.contract import LEVELS, MODELS


def audit(source, dependencies, output):
    sys.path.insert(0, str(dependencies))
    import tokenizers
    import jinja2
    from jinja2.sandbox import ImmutableSandboxedEnvironment
    env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)
    prompt = Path("configs/pilot/classification_c1.txt").read_text(encoding="utf-8")
    result = {"status": "TEXT_ONLY_NOT_GPU_HNLO_VALIDATION", "tokenizers": tokenizers.__version__,
              "jinja2": jinja2.__version__, "models": {}}
    for key in ("phi", "smolvlm2"):
        root = Path(source) / key
        tokenizer = tokenizers.Tokenizer.from_file(str(root / "tokenizer.json"))
        config = json.loads((root / "tokenizer_config.json").read_bytes())
        template = config.get("chat_template")
        if not template:
            template = json.loads((root / "chat_template.json").read_bytes())["chat_template"]
        content = "<|image_1|>\n" + prompt if key == "phi" else [{"type": "image"}, {"type": "text", "text": prompt}]
        rendered = env.from_string(template).render(messages=[{"role": "user", "content": content}],
                 add_generation_prompt=True, bos_token=config.get("bos_token", ""), eos_token=config.get("eos_token", ""),
                 raise_exception=lambda m: (_ for _ in ()).throw(ValueError(m)))
        base = tokenizer.encode(rendered, add_special_tokens=False).ids
        class Adapter:
            def encode(self, text, add_special_tokens=False):
                return tokenizer.encode(text, add_special_tokens=add_special_tokens).ids
            def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
                return tokenizer.decode(ids, skip_special_tokens=skip_special_tokens)
        evidence = probe(Adapter(), rendered, base)
        result["models"][key] = {"model": MODELS[key], "text_only_probe": evidence,
            "tokenizer_sha256": hashlib.sha256((root / "tokenizer.json").read_bytes()).hexdigest(),
            "standalone_labels": {l: tokenizer.encode(l, add_special_tokens=False).ids for l in LEVELS},
            "actual_image_boundary": "NOT_RUN", "generated_alignment": "NOT_RUN"}
    result["models"]["gemma"] = {"model": MODELS["gemma"], "status": "BLOCKED_GATED_401_NO_TOKENIZER",
                                    "mapping": None, "generated_alignment": "NOT_RUN"}
    write(output, result)


def main():
    p = argparse.ArgumentParser()
    for name in ("source", "dependencies", "output"):
        p.add_argument("--" + name, required=True)
    a = p.parse_args()
    audit(a.source, a.dependencies, a.output)


if __name__ == "__main__":
    main()
