"""Fetch only official model text/code for review. Never fetch weights or dataset.

Run from root. Output is ignored; reviewed hashes belong in the source lock.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, HTTPRedirectHandler, build_opener

from safeshift.pilot.artifacts import write, write_bytes
from safeshift.pilot.runner import error_record

MODELS = {
    "gemma": ("google/gemma-3-4b-it", "093f9f388b31de276ce2de164bdc2081324b9767"),
    "phi": ("microsoft/Phi-3.5-vision-instruct", "12b77fb40b63a2c73c68243d3f767aab688a1b2a"),
    "smolvlm2": ("HuggingFaceTB/SmolVLM2-2.2B-Instruct", "482adb537c021c86670beed01cd58990d01e72e4"),
    # Public CPU qualification only; these entries do not enroll pilot backends.
    "internvl35": ("OpenGVLab/InternVL3_5-4B-HF", "6bd4487402110ef9889ba50eb7aefeb302526fed"),
    "minicpm4": ("openbmb/MiniCPM-V-4", "6f69a8235885be89608f3a71ffd40695b379e1e7"),
}


class NoCredentialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            redirected.remove_header("Authorization")
        return redirected


def audit(root, keys, authenticated=False):
    root = Path(root).resolve()
    if not root.is_relative_to((Path.cwd() / "data/processed").resolve()):
        raise ValueError("AUDIT_OUTPUT_MUST_BE_UNDER_DATA_PROCESSED")
    token = os.environ.get("HF_TOKEN") if authenticated else None
    if authenticated and not token:
        raise PermissionError("HF_TOKEN_ENV_REQUIRED_NEVER_PASTE_IN_CODE_OR_ARGUMENTS")
    root.mkdir(parents=True, exist_ok=False)
    opener = build_opener(NoCredentialRedirect())
    def fetch(url):
        headers = {"Authorization": "Bearer " + token} if token else {}
        with opener.open(Request(url, headers=headers), timeout=60) as response:
            payload = response.read(32 * 2**20 + 1)
        if len(payload) > 32 * 2**20:
            raise ValueError("TEXT_SOURCE_TOO_LARGE")
        return payload
    results = {}
    for key in keys:
        model_id, revision = MODELS[key]
        target = root / key
        target.mkdir()
        api = f"https://huggingface.co/api/models/{model_id}/revision/{revision}"
        metadata = json.loads(fetch(api))
        if metadata["sha"] != revision:
            raise ValueError("REVISION_MISMATCH")
        files = [r["rfilename"] for r in metadata["siblings"]
                 if "/" not in r["rfilename"] and r["rfilename"].endswith((".py", ".json", ".md", ".txt", ".model", ".jinja"))
                 and not r["rfilename"].endswith(".safetensors.index.json")]
        result = {"id": model_id, "revision": revision, "authenticated": authenticated, "files": {}, "unavailable": {}}
        for name in files:
            url = f"https://huggingface.co/{model_id}/resolve/{revision}/{name}"
            try:
                payload = fetch(url)
                write_bytes(target / name, payload)
                result["files"][name] = hashlib.sha256(payload).hexdigest()
            except Exception as error:
                result["unavailable"][name] = {**error_record(error, "source_audit"),
                                                "http_status": getattr(error, "code", None)}
        results[key] = result
        print(key, "review files", len(result["files"]), "unavailable", list(result["unavailable"]))
    write(root / "inventory.json", results)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", choices=tuple(MODELS), default=["gemma", "phi", "smolvlm2"])
    p.add_argument("--output", default="data/processed/three_vlm_source_audit")
    p.add_argument("--authenticated", action="store_true",
                   help="Owner-authorized text/source access only; reads HF_TOKEN from environment")
    a = p.parse_args()
    audit(a.output, a.models, a.authenticated)


if __name__ == "__main__":
    main()
