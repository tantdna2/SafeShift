"""Opt-in CPU storage profile: 32 full synthetic raw AND processed vectors.

No torch, tokenizer download, checkpoint, CUDA API or model is used. The planning
ceiling (200,000) is deliberately not represented as the model's vocabulary.
"""
import argparse
from array import array
import json
from pathlib import Path
import resource
import shutil
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.diagnostics.hnlo_capture import Capture, persist_hf
from safeshift.diagnostics.one_click.artifacts import package, write
from safeshift.diagnostics.internvl3_hnlo.resources import VOCAB_CEILING, budget


class Tensor:
    dtype, device = "torch.float32", "cpu-synthetic-array-not-torch"

    def __init__(self, values):
        self.values, self.shape = array("f", values), (1, len(values))

    def tolist(self):
        return [self.values.tolist()]


class Sequence:
    def tolist(self):
        return [[123] + [0] * 32]


class Tokenizer:
    def __init__(self, cap):
        self.cap = cap

    def decode(self, *args, **kwargs):
        for kind in ("raw", "processed"):
            for i in range(32):
                self.cap.journal.read(f"{kind}-{i:03d}")
        return "SYNTHETIC INVALID CPU RESOURCE PROFILE"


def profile(root):
    started = time.monotonic()
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    cap = Capture(root, {"run_id": "hnlo-cpu-full-vector-profile", "sample_id": "SYNTHETIC_ONLY",
        "model_id": "NO_MODEL", "revision": "a" * 40, "tokenizer_revision": "a" * 40,
        "tokenizer_files": [{"path": "synthetic", "sha256": "a" * 64}], "software": {"python": sys.version},
        "source_commit": "a" * 40, "sources": [{"path": "synthetic", "sha256": "a" * 64}],
        "command": "python scripts/profile_internvl3_hnlo_vectors.py", "prompt": "SYNTHETIC",
        "input_sha256": "b" * 64, "configuration": budget(), "seed": None})
    values = array("f", (-(i % 8191) / 997.0 for i in range(VOCAB_CEILING)))
    values[0] = 10.0
    raw = [Tensor(values) for _ in range(32)]
    processed = [Tensor(values) for _ in range(32)]
    output = SimpleNamespace(sequences=Sequence(), logits=raw, scores=processed)
    persist_hf(output, [123], [1, 2, 3, 4], Tokenizer(cap), cap, {"eos_token_id": 999}, {"do_sample": False})
    cap.journal.seal()
    if not cap.journal.verify():
        raise ValueError("PROFILE_CAPTURE_NOT_SEALED")
    evidence = root / "evidence"
    shutil.copytree(cap.journal.root, evidence / "capture")
    archive = package(evidence, root, "cpu-vector-profile")
    vector_bytes = sum(cap.journal.path(f"{kind}-{i:03d}").stat().st_size
                       for kind in ("raw", "processed") for i in range(32))
    result = {"kind": "CPU_SYNTHETIC_STORAGE_PROFILE_NOT_GPU", "budget": budget(),
              "raw_vectors": 32, "processed_vectors": 32, "all_vectors_verified_before_decode": True,
              "vector_json_bytes": vector_bytes, "archive_bytes": archive.stat().st_size,
              "elapsed_seconds": time.monotonic() - started,
              "peak_host_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
              "total_retained_bytes": sum(p.stat().st_size for p in root.rglob("*") if p.is_file()),
              "HNLO_RESEARCH_VERIFIED": False, "TECHNICAL_HNLO_VALID": False}
    write(root / "profile.json", result)
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=Path("data/processed/internvl3_hnlo_vector_profile"))
    args = parser.parse_args()
    target = args.output_root.resolve()
    if not target.is_relative_to((ROOT / "data/processed").resolve()):
        raise ValueError("PROFILE_OUTPUT_MUST_BE_UNDER_DATA_PROCESSED")
    profile(target)
