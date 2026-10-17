"""Offline CPU T1 for pinned Qwen3 and native Starmie tokenizers.

InternVL3 intentionally continues to use ``safeshift.ls1.tokenizer`` unchanged.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform

from safeshift.runners.internvl3_snapshot import OFFLINE_ENV, network_denied
from .artifacts import write_json
from .core import LEVELS
from .tokenizer import probe

MODELS = {
    "qwen3": {
        "repo_id": "Qwen/Qwen3-VL-8B-Instruct",
        "revision": "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b",
        "software": {"transformers": "4.57.1", "huggingface-hub": "0.36.0"},
        "observed_software": ("transformers", "tokenizers", "huggingface-hub"),
        "files": (
            "chat_template.json", "config.json", "merges.txt", "tokenizer.json",
            "tokenizer_config.json", "vocab.json",
        ),
        "interface": "transformers.AutoTokenizer.from_pretrained",
    },
    "moondream2": {
        "repo_id": "moondream/starmie-v1",
        "revision": "35192e10a54e36eabe0a7cc57a2c1aab371cafc5",
        "software": {"tokenizers": "0.21.2"},
        "observed_software": ("tokenizers", "huggingface-hub"),
        "files": ("README.md", "special_tokens_map.json", "tokenizer.json", "tokenizer_config.json"),
        "interface": "tokenizers.Tokenizer.from_file",
    },
}
VARIANT_NAMES = (
    "compact_json",
    "leading_space_trailing_lf",
    "colon_space",
    "multiline_indented",
    "json_fence_lf",
    "plain_fence_crlf",
    "tab_json_fence_spaced_colon_trailing_lf",
)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_resources(model_key, snapshot, manifest_path):
    expected = MODELS[model_key]
    snapshot = Path(snapshot)
    if not snapshot.is_dir() or snapshot.name != expected["revision"]:
        raise FileNotFoundError("PINNED_REVISION_SNAPSHOT_MISSING")
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "safeshift-hnlo-t1-tokenizer-resources-v1":
        raise ValueError("UNKNOWN_RESOURCE_MANIFEST")
    rows = [row for row in manifest["models"] if row["model_key"] == model_key]
    if len(rows) != 1:
        raise ValueError("EXACTLY_ONE_MODEL_RESOURCE_ENTRY_REQUIRED")
    model = rows[0]
    if (model["repo_id"], model["revision"]) != (expected["repo_id"], expected["revision"]):
        raise ValueError("RESOURCE_IDENTITY_MISMATCH")
    manifest_names = [row["path"] for row in model["files"]]
    if len(manifest_names) != len(set(manifest_names)) or set(manifest_names) != set(expected["files"]):
        raise ValueError("PINNED_RESOURCE_MANIFEST_INVENTORY_MISMATCH")
    names = {item.relative_to(snapshot).as_posix() for item in snapshot.rglob("*") if item.is_file()}
    if names != set(expected["files"]):
        raise ValueError("RESOURCE_INVENTORY_MISMATCH")
    files = []
    for row in model["files"]:
        target = snapshot / row["path"]
        size = target.stat().st_size
        digest = sha256_file(target)
        if size != row["size_bytes"] or digest != row["sha256"]:
            raise ValueError("RESOURCE_SHA256_MISMATCH:" + row["path"])
        files.append({"path": row["path"], "size_bytes": size, "sha256": digest})
    return {"repo_id": model["repo_id"], "revision": model["revision"], "files": files}


def installed_versions(requirements):
    return {name: importlib.metadata.version(name) for name in requirements}


class StarmieAdapter:
    """Expose the existing T1's HF-like encode/decode surface without altering bytes."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def encode(self, text, add_special_tokens=False):
        if type(add_special_tokens) is not bool:
            raise TypeError("BOOLEAN_ADD_SPECIAL_TOKENS_REQUIRED")
        return list(self.tokenizer.encode(text, add_special_tokens=add_special_tokens).ids)

    def decode(self, ids, *, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        if clean_up_tokenization_spaces is not False:
            raise ValueError("CLEANUP_TOKENIZATION_SPACES_FORBIDDEN")
        return self.tokenizer.decode(list(ids), skip_special_tokens=skip_special_tokens)

    def __len__(self):
        return self.tokenizer.get_vocab_size(with_added_tokens=True)


def variant_results(evidence):
    checks = evidence["checks"]
    if len(checks) != len(VARIANT_NAMES) * len(LEVELS):
        raise ValueError("EXACTLY_28_T1_CHECKS_REQUIRED")
    results = []
    for index, name in enumerate(VARIANT_NAMES):
        group = checks[index * 4:(index + 1) * 4]
        mappings = {tuple(row["token_ids"]) for row in group}
        steps = {row["step"] for row in group}
        generated = {row["generated_label"] for row in group}
        if len(mappings) != 1 or len(steps) != 1 or generated != set(LEVELS):
            raise ValueError("VARIANT_MAPPING_INCONSISTENT:" + name)
        ids = next(iter(mappings))
        results.append({
            "variant": name,
            "status": "PASS",
            "decision_step": next(iter(steps)),
            "token_ids": dict(zip(LEVELS, ids)),
            "responses": [row["text"] for row in group],
        })
    return results


def load_tokenizer(model_key, snapshot):
    if model_key == "qwen3":
        from transformers import AutoTokenizer
        return AutoTokenizer.from_pretrained(
            str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True,
        )
    from tokenizers import Tokenizer
    return StarmieAdapter(Tokenizer.from_file(str(Path(snapshot) / "tokenizer.json")))


def t1(model_key, snapshot, manifest):
    expected = MODELS[model_key]
    result = {
        "test": "T1",
        "model_key": model_key,
        "repo_id": expected["repo_id"],
        "revision": expected["revision"],
        "interface": expected["interface"],
        "weights_loaded": False,
        "model_inference_used": False,
        "gpu_used": False,
        "network_used_during_t1": False,
    }
    try:
        resources = verify_resources(model_key, snapshot, manifest)
        actual = installed_versions(expected["observed_software"])
        required_actual = {name: actual[name] for name in expected["software"]}
        result.update(
            resources=resources,
            python_version=platform.python_version(),
            expected_versions=expected["software"],
            actual_versions=actual,
        )
        if required_actual != expected["software"]:
            raise RuntimeError("TOKENIZER_LIBRARY_VERSION_MISMATCH")
        os.environ.update(OFFLINE_ENV)
        with network_denied():
            tokenizer = load_tokenizer(model_key, snapshot)
            evidence = probe(tokenizer)
        result.update(
            status="PASS",
            tokenizer_class=type(tokenizer).__name__,
            vocab_size=len(tokenizer),
            variants=variant_results(evidence),
            **evidence,
        )
    except (FileNotFoundError, importlib.metadata.PackageNotFoundError, ImportError, RuntimeError) as exc:
        result.update(status="BLOCKED", reason=str(exc))
    except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        result.update(status="FAIL", reason=str(exc))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = t1(args.model, args.snapshot, args.manifest)
    write_json(args.output, result)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
