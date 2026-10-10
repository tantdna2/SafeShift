"""T1: hash-pinned real tokenizers only, never model weights or downloads."""

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from safeshift.protocol.schema import strict_json
from safeshift.runners.internvl3_snapshot import network_denied, OFFLINE_ENV
from .artifacts import digest, write_json
from .core import LEVELS, candidates

ROOT = Path(__file__).resolve().parents[2]
MODELS = {
    "qwen2_5": ("Qwen/Qwen2.5-VL-3B-Instruct", "66285546d2b821cf421d4f5eb2576359d3770cd3"),
    "internvl3": ("OpenGVLab/InternVL3-2B-hf", "cb57a075cb75a2e6d1b668b128d48bb00ae321d2"),
}
PLANS = {"qwen2_5": "configs/pre_freeze/qwen2_5_t4_runtime.v1.json",
         "internvl3": "configs/pre_freeze/internvl3_t4_runtime.v1.json"}
PLAN_HASHES = {"qwen2_5": "aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb",
               "internvl3": "c2ad3137fbdba8809f2d86b75c6869955d51d462431905a7796cf109d1bf65b6"}
TOKENIZER_FILES = {"tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                   "added_tokens.json", "vocab.json", "merges.txt", "chat_template.json", "chat_template.jinja",
                   "config.json"}


def plan(model, repo=ROOT):
    value = strict_json((Path(repo) / PLANS[model]).read_bytes())
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    if hashlib.sha256(canonical).hexdigest() != PLAN_HASHES[model]:
        raise ValueError("PINNED_RUNTIME_PLAN_CHANGED")
    if (value["model_id"], value["model_revision"]) != MODELS[model]:
        raise ValueError("MODEL_IDENTITY_MISMATCH")
    return value


def verify_snapshot(model, snapshot, *, tokenizer_only=False, repo=ROOT):
    snapshot = Path(snapshot)
    if not snapshot.is_dir():
        raise FileNotFoundError("PINNED_SNAPSHOT_MISSING")
    if snapshot.name != MODELS[model][1]:
        raise ValueError("PINNED_REVISION_DIRECTORY_REQUIRED")
    files = []
    for item in plan(model, repo)["snapshot_files"]:
        if tokenizer_only and item["path"] not in TOKENIZER_FILES:
            continue
        path = snapshot / item["path"]
        if not path.is_file():
            raise FileNotFoundError("SNAPSHOT_FILE_MISSING:" + item["path"])
        # HF cache blobs may be symlinks, confined to their own cache repository.
        if not (path.resolve().is_relative_to(snapshot.resolve()) or
                (snapshot.parent.name == "snapshots" and
                 path.resolve().is_relative_to((snapshot.parent.parent / "blobs").resolve()))):
            raise ValueError("SNAPSHOT_FILE_ESCAPES_INPUT")
        size = path.stat().st_size
        h = hashlib.sha256() if item["hash_algorithm"] == "sha256" else hashlib.sha1()
        if item["hash_algorithm"] == "git_blob_sha1":
            h.update(("blob " + str(size) + "\0").encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                h.update(block)
        if size != item["size_bytes"] or h.hexdigest() != item["expected_hash"]:
            raise ValueError("PINNED_SNAPSHOT_CHECKSUM_MISMATCH:" + item["path"])
        files.append({**item, "sha256": digest(path)})
    return {"model_id": MODELS[model][0], "revision": MODELS[model][1],
            "plan_sha256": PLAN_HASHES[model], "tokenizer_only": tokenizer_only, "files": files}


def versions(names):
    return {name: platform.python_version() if name == "python" else importlib.metadata.version(name)
            for name in names}


def probe(tokenizer):
    texts = [f'{{"safety_level":"{label}"}}' for label in LEVELS]
    templates = [lambda s: s, lambda s: " " + s + "\n", lambda s: s.replace(":", ": "),
                 lambda s: s.replace("{", "{\n  ").replace("}", "\n}"),
                 lambda s: "```json\n" + s + "\n```", lambda s: "```\r\n" + s + "\r\n```",
                 lambda s: "\t```json\n" + s.replace(":", " : ") + "\n```\n"]
    checks = []
    for transform in templates:
        for text in texts:
            variant = transform(text)
            checks.append({"text": variant, **candidates(tokenizer, variant)})
    return {"bare_label_ids": {label: tokenizer.encode(label, add_special_tokens=False) for label in LEVELS},
            "checks": checks, "candidate_token_ids": sorted({i for c in checks for i in c["token_ids"]})}


def t1(model, snapshot=None, *, repo=ROOT):
    result = {"test": "T1", "model_key": model, "model_id": MODELS[model][0],
              "revision": MODELS[model][1], "weights_loaded": False, "network_used": False}
    try:
        if snapshot is None:
            raise FileNotFoundError("PINNED_SNAPSHOT_NOT_SUPPLIED")
        receipt = verify_snapshot(model, snapshot, tokenizer_only=True, repo=repo)
        expected = {k: plan(model, repo)["software"][k] for k in ("transformers", "tokenizers", "huggingface-hub")}
        actual = versions(expected)
        result.update(snapshot=receipt, expected_versions=expected, actual_versions=actual,
                      python_version=platform.python_version())
        if actual != expected:
            raise RuntimeError("TOKENIZER_LIBRARY_VERSION_MISMATCH")
        import os
        os.environ.update(OFFLINE_ENV)
        with network_denied():
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True,
                                                       trust_remote_code=False, use_fast=True)
            evidence = probe(tokenizer)
        result.update(status="PASS", tokenizer_class=type(tokenizer).__name__, vocab_size=len(tokenizer), **evidence)
        return result, tokenizer
    except (FileNotFoundError, importlib.metadata.PackageNotFoundError, ImportError, RuntimeError) as exc:
        result.update(status="BLOCKED", reason=str(exc))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        result.update(status="FAIL", reason=str(exc))
    return result, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result, _ = t1(args.model, args.snapshot)
    write_json(args.output, result)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
