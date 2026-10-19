"""Profile a full synthetic 941-sample shard, with no model, GPU or real data."""
import json
import hashlib
import subprocess
from pathlib import Path
import resource
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from safeshift.diagnostics.hnlo_train import audit, cohort, engine
    from safeshift.diagnostics.one_click.artifacts import package
    from tests.test_hnlo_train import FakeBackend, TOK
    count = 941
    fingerprint_paths = sorted((ROOT / "safeshift/diagnostics/hnlo_train").glob("*.py"))
    fingerprint_paths += [Path(__file__), ROOT / "tests/test_hnlo_train.py", ROOT / "tests/test_hnlo_capture.py"]
    fingerprint = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in fingerprint_paths}
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    rows = [{"sample_id": f"synthetic-{i}", "image_sha256": f"{i+1:064x}"} for i in range(count)]
    with tempfile.TemporaryDirectory(prefix="safeshift-synthetic-profile-") as temp:
        root = Path(temp) / "data/processed/synthetic-shard"
        root.mkdir(parents=True)
        output = root.parent / "export"
        output.mkdir()
        start = time.monotonic()
        index = engine.execute(root / "raw", cohort.opaque_rows(rows), count, lambda j: FakeBackend(j))
        creation = time.monotonic() - start
        print("SYNTHETIC_941_CREATED", flush=True)
        assert index.verify() and index.read("finish") == {"count": count}
        start = time.monotonic()
        audited, completed, integrity = audit.raw_rows(root, rows, TOK)
        assert completed and integrity == "PASS"
        assert len(audited) == count and all(r["status"] == "SUCCESS" for r in audited)
        replay = time.monotonic() - start
        print("SYNTHETIC_941_CPU_REPLAY_PASS", flush=True)
        start = time.monotonic()
        audit.seal_raw(root)
        audit.verify_custody(root)
        custody = time.monotonic() - start
        files = [p for p in root.rglob("*") if p.is_file()]
        file_count, byte_count = len(files), sum(p.stat().st_size for p in files)
        start = time.monotonic()
        archive = package(root, output, "synthetic-941")
        packaging = time.monotonic() - start
        stats = {"kind": "SYNTHETIC_CPU_FULL_SHARD_NOT_TRAIN", "samples": count,
            "successful_raw_replays": len(audited), "steps_per_sample": 27, "synthetic_vocab": 1000,
            "file_count": file_count, "evidence_bytes": byte_count,
            "creation_and_online_replay_seconds": creation, "creation_files_per_second": file_count / creation,
            "independent_cpu_replay_seconds": replay, "custody_seal_and_verify_seconds": custody,
            "archive_and_member_verification_seconds": packaging, "archive_bytes": archive.stat().st_size,
            "process_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            "python": sys.version, "git_commit": commit, "working_source_sha256": fingerprint, "cuda_or_model_used": False, "real_train_images_read": False,
            "limits": "Small synthetic input/token IDs, 27 steps/1000 vocab and Linux temporary filesystem; no GPU, TRAIN complexity, Kaggle FUSE or worst-case 2 MiB/sample throughput prediction."}
        print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
