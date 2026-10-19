"""Synthetic CPU storage arithmetic. No model, dataset, GPU or throughput claim."""
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from tests.test_hnlo_train import fill
    from safeshift.diagnostics.hnlo_train.capture import SampleCapture
    with tempfile.TemporaryDirectory(dir=ROOT / "data/processed") as temp:
        cap = SampleCapture(Path(temp) / "synthetic", {"ordinal": 0, "image_sha256": "1" * 64})
        fill(cap)
        cap.journal.seal()
        total = sum(p.stat().st_size for p in cap.journal.root.iterdir())
        steps = cap.journal.read("native")["raw_steps"]
    rows = []
    for model, vocab in (("qwen3", 151936), ("internvl3", 151674)):
        rows.append({"model": model, "vocab": vocab, "steps_cap": 32,
            "full_raw_processed_float32_bytes_per_image": vocab * 32 * 2 * 4,
            "full_raw_processed_float32_bytes_941_images": vocab * 32 * 2 * 4 * 941,
            "full_raw_processed_float32_bytes_3763_images": vocab * 32 * 2 * 4 * 3763,
            "synthetic_summary_bytes_per_image": total, "synthetic_steps": steps,
            "synthetic_projection_941_bytes": total * 941,
            "summary_primary_json_cap_per_image": 2 * 2**20,
            "summary_primary_json_cap_941_bytes": 2 * 2**20 * 941})
    print(json.dumps({"kind": "SYNTHETIC_CPU_STORAGE_ONLY", "models": rows,
        "real_image_throughput": None, "actual_train_ram_vram": None,
        "caveat": "Full-vector numbers exclude metadata/archive; synthetic summary projections do not predict real-image input lengths or runtime."}, indent=2))


if __name__ == "__main__":
    (ROOT / "data/processed").mkdir(parents=True, exist_ok=True)
    main()
