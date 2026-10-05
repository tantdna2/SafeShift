"""Bounded official source-text audit; never request model weights or accept licenses."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "ovis": ("ATH-MaaS/Ovis2.5-2B", "393c932b2a03e28eb9aaa503e3c4ab3ad384d958"),
    "plamo": ("pfnet/plamo-2.1-2b-vl", "3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027"),
    "kosmos": ("microsoft/kosmos-2-patch14-224", "1f66d913fde5307936383dc9460b12ccb82f2133"),
}


def fetch(url, target):
    with urlopen(Request(url, headers={"User-Agent": "SafeShift-source-audit"}), timeout=60) as response:
        raw = response.read(500001)
    if len(raw) > 500000:
        raise ValueError("source exceeds text-only size bound")
    raw.decode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return {"url": url, "access_date": "2026-10-05", "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "local_audit_cache": target.relative_to(ROOT).as_posix()}


def main():
    manifest = {"schema": "d9r20-official-source-audit-v1", "weights_downloaded": False, "models": {}}
    for key, (model, revision) in PINS.items():
        folder = ROOT / ".cache/d9r20_sources" / key
        api = fetch(f"https://huggingface.co/api/models/{model}/revision/{revision}?blobs=true", folder / "api.json")
        metadata = json.loads((folder / "api.json").read_bytes())
        if metadata["sha"] != revision or metadata["id"] != model:
            raise ValueError("official API model/revision identity mismatch")
        row = {"model_id": model, "revision": revision, "gated": metadata["gated"],
               "license": metadata.get("cardData", {}).get("license"), "api": api,
               "files": metadata["siblings"], "sources": []}
        for item in row["files"]:
            name = item["rfilename"]
            if (name.endswith(".py") or name in ("README.md", "LICENSE", "LICENSE.txt", "NOTICE", "config.json",
                    "preprocessor_config.json", "processor_config.json", "generation_config.json",
                    "requirements.txt", "special_tokens_map.json", "tokenizer_config.json")):
                source = fetch(f"https://huggingface.co/{model}/resolve/{revision}/{name}", folder / name)
                source["locator"] = name
                row["sources"].append(source)
        manifest["models"][key] = row
        print(key, revision, "gated=", row["gated"], "source_count=", len(row["sources"]))
    manifest["official_implementations"] = []
    for repo, ref, files in (
        ("huggingface/transformers", "8cb5963cc22174954e7dca2c0a3320b7dc2f4edc", ["src/transformers/models/kosmos2/processing_kosmos2.py", "src/transformers/models/kosmos2/modeling_kosmos2.py", "docs/source/en/model_doc/kosmos-2.md"]),
        ("microsoft/unilm", "31c5b904ca1bf2afb4c234a6675c683a4e5fc7cd", ["kosmos-2/README.md", "kosmos-2/demo/gradio_app.py", "LICENSE"]),
        ("state-spaces/mamba", "f1493ff6e9335160eb134eb67e59f8e4d9adefd6", ["README.md", "setup.py"]),
        ("Dao-AILab/causal-conv1d", "da6dbaa9fd5a919967f14d3fd031da1288ad5025", ["README.md", "setup.py"]),
    ):
        folder = ROOT / ".cache/d9r20_sources" / repo.split("/")[1]
        identity = fetch(f"https://api.github.com/repos/{repo}/commits/{ref}", folder / "commit.json")
        commit = json.loads((folder / "commit.json").read_bytes())["sha"]
        for name in files:
            source = fetch(f"https://raw.githubusercontent.com/{repo}/{commit}/{name}", folder / name)
            source.update(repository=repo, revision=commit, locator=name, ref_at_access=ref)
            manifest["official_implementations"].append(source)
        print(repo, commit)
    manifest["official_author_comments"] = []
    for comment in (1628617454, 1632078662):
        source = fetch(f"https://api.github.com/repos/microsoft/unilm/issues/comments/{comment}",
                       ROOT / f".cache/d9r20_sources/unilm/comment-{comment}.json")
        source["locator"] = f"https://github.com/microsoft/unilm/issues/1186#issuecomment-{comment}"
        source["limitation"] = "Author statement; mutable comment pinned by access date and downloaded JSON SHA256"
        manifest["official_author_comments"].append(source)
    target = ROOT / "configs/pre_freeze/d9r20_sources.v1.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
