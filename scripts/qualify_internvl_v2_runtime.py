"""CPU-only tests/receipt. Optional public source fetch excludes all weights."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import urllib.request

from safeshift.internvl_v2_runtime import ROOT, source_spec
from safeshift.pilot.artifacts import read, write, sha


def public_source(path):
    lock = read(ROOT / "configs/cpu_g2_g3/public_source_lock.json")["internvl35"]
    path.mkdir(parents=True, exist_ok=True)
    for name, checksum in lock["files"].items():
        if not name.endswith((".json", ".txt", ".py", ".jinja", ".md")):
            raise ValueError("PUBLIC_TEXT_SOURCE_ONLY")
        target = path / name
        if not target.exists():
            url = lock["source_url_pattern"].format(id=lock["id"], revision=lock["revision"], filename=name)
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = response.read(16 * 2**20 + 1)
            if len(payload) > 16 * 2**20 or hashlib.sha256(payload).hexdigest() != checksum:
                raise ValueError("PUBLIC_SOURCE_HASH_SIZE")
            from safeshift.pilot.artifacts import write_bytes
            write_bytes(target, payload)
        if sha(target) != checksum:
            raise ValueError("PUBLIC_SOURCE_CHECKSUM")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--packages", type=Path, action="append", default=[])
    p.add_argument("--native-source", type=Path)
    p.add_argument("--fetch-public-source", action="store_true")
    args = p.parse_args()
    if args.fetch_public_source and args.native_source is None:
        p.error("--fetch-public-source requires --native-source")
    args.output.mkdir(parents=True, exist_ok=False)
    for key in list(os.environ):
        if key.startswith("SAFESHIFT_"):
            del os.environ[key]
    os.environ.update(CUDA_VISIBLE_DEVICES="", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      TOKENIZERS_PARALLELISM="false")
    for directory in args.packages:
        sys.path.insert(0, str(directory.resolve()))
    sys.path.insert(0, str(ROOT / "tests"))
    if args.fetch_public_source:
        public_source(args.native_source)
    dependencies = {}
    if args.native_source:
        os.environ.update(SAFESHIFT_V2_NATIVE_CPU="1", SAFESHIFT_V2_SOURCE=str(args.native_source.resolve()),
                          SAFESHIFT_V2_TOKENIZER=str(args.native_source.resolve()))
        dependencies = {name: importlib.metadata.version(name) for name in
                        ("torch", "torchvision", "transformers", "tokenizers", "numpy", "Pillow")}
    names = ["test_internvl_v2_runtime", "test_internvl_v2_campaign", "test_internvl_v2_memory", "test_internvl_v2_continuous", "test_internvl_grammar", "test_issue173_format_decision",
             "test_pilot.HNLOTests", "test_kaggle173_diagnostic",
             "test_fresh_fulltrain.FreshTests.test_storage_simultaneous_cleanup_repeat_and_quota_failure",
             "test_fresh_fulltrain_revision.RevisionTests.test_cgroup_ram_and_shared_distinct_disk_reserves",
             "test_fresh_fulltrain_revision.RevisionTests.test_hardware_missing_driver_memory_count_and_cuda_probe_each_gpu",
             "test_kaggle173_smoke.SmokeJournalTests.test_driver_exit12_is_preserved_and_remains_blocked",
             "test_kaggle173_smoke.SmokeJournalTests.test_scoped_utility_keeps_driver_count_and_memory_gates"]
    names.append("test_candidate160_preflight.PreflightAdmissionTests.test_real_checkpoint_admission_missing_duplicate_wrong_mount_source_or_weights_blocks")
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with (args.output / "tests.log").open("x", encoding="utf8") as log:
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    receipt = {"schema": "internvl-v2-native-integration-cpu-v1",
        "status": "PASS" if result.wasSuccessful() else "FAIL", "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors), "skips": len(result.skipped),
        "skip_reasons": [reason for _, reason in result.skipped], "test_suites": names,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source": source_spec(), "test_sha256": sha(ROOT / "tests/test_internvl_v2_runtime.py"),
        "qualifier_sha256": sha(Path(__file__)), "log_sha256": sha(args.output / "tests.log"),
        "python": sys.version, "platform": platform.platform(), "dependencies": dependencies,
        "command": ["python", "-B", "-m", "scripts.qualify_internvl_v2_runtime", "--output", "<new-output>"]
            + (["--native-source", "<public-source>", "--packages", "<isolated-packages>"] if args.native_source else []),
        "evidence_kind": "CPU_SYNTHETIC_SCRIPTED_NOT_MODEL_INFERENCE", "randomness": "NONE",
        "weights_loaded": False, "real_image_reads": 0, "model_inference_calls": 0,
        "kaggle_submissions": 0, "live_gpu_preflight": "NOT_RUN", "scientific_qualified": False,
        "execution_authority": None}
    write(args.output / "receipt.json", receipt)
    print(json.dumps({k: receipt[k] for k in ("status", "tests_run", "failures", "errors", "skips")}))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
