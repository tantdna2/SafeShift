"""Fetch only official model text/code for review. Never fetch weights or dataset.

Run from root. Output is ignored; reviewed hashes belong in the source lock.
"""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

MODELS = {
    "gemma": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
    "phi": ("microsoft/Phi-3.5-vision-instruct", "12b77fb40b63a2c73c68243d3f767aab688a1b2a"),
    "smolvlm2": ("HuggingFaceTB/SmolVLM2-2.2B-Instruct", "482adb537c021c86670beed01cd58990d01e72e4"),
}


def main():
    root = Path("data/processed/three_vlm_source_audit")
    root.mkdir(parents=True, exist_ok=True)
    results = {}
    for key, (model_id, revision) in MODELS.items():
        target = root / key
        target.mkdir(exist_ok=True)
        api = f"https://huggingface.co/api/models/{model_id}/revision/{revision}"
        with urlopen(api, timeout=60) as response:
            metadata = json.load(response)
        if metadata["sha"] != revision:
            raise ValueError("REVISION_MISMATCH")
        files = [r["rfilename"] for r in metadata["siblings"]
                 if "/" not in r["rfilename"] and r["rfilename"].endswith((".py", ".json", ".md", ".txt", ".model"))
                 and not r["rfilename"].endswith(".safetensors.index.json")]
        result = {"id": model_id, "revision": revision, "files": {}, "unavailable": {}}
        for name in files:
            url = f"https://huggingface.co/{model_id}/resolve/{revision}/{name}"
            try:
                with urlopen(url, timeout=60) as response:
                    payload = response.read(32 * 2**20 + 1)
                if len(payload) > 32 * 2**20:
                    raise ValueError("TEXT_SOURCE_TOO_LARGE")
                (target / name).write_bytes(payload)
                result["files"][name] = hashlib.sha256(payload).hexdigest()
            except Exception as error:
                result["unavailable"][name] = type(error).__name__ + ": " + str(error)
        results[key] = result
        print(key, "review files", len(result["files"]), "unavailable", list(result["unavailable"]))
    (root / "inventory.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
