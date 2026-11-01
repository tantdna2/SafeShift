"""CPU-only CLI for the single archive authorized by Issue165."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys

from safeshift.evaluation.minicpm_saved_hnlo import (verify, sha,
    RUNTIME, SOURCE_SHA, require, SealedArchive)


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        stream.write("\n")


def public_projection(summary):
    # Explicit fields, so future private fields cannot silently leak to GitHub.
    fields = ("schema result qualification archive_sha256 source_sha256 runtime_commit "
        "configuration_sha256 descriptor_sha256 run_id series_id attempt_id run_kind planned "
        "original_success original_invalid hnlo_valid success_without_hnlo unresolved reasons "
        "payload_checksums_verified original_archive_unchanged native_steps_checked tokenizer_sha256 "
        "vocabulary_sha256 vocabulary_size tokenizers exhaustive_searches structural_cache_hits "
        "independent_negative_proofs missing_sparse_alias_records available_four_coordinate_oracle_checks "
        "inference_calls scientific_selection original_numeric_hnlo private_records_sha256").split()
    return {k: summary[k] for k in fields}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    require(output.resolve().is_relative_to(Path("data/processed").resolve()), "PRIVATE_OUTPUT_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    environment = {"python": sys.version, "platform": platform.platform(), "seed": None,
        "command": ["python", "-B", "-m", "scripts.verify_minicpm_saved_hnlo", *sys.argv[1:]],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_files": {p: sha(Path(p).read_bytes()) for p in (
            "safeshift/evaluation/hnlo_method_a.py", "safeshift/evaluation/minicpm_saved_hnlo.py",
            "scripts/verify_minicpm_saved_hnlo.py", "safeshift/pilot/hnlo.py")}}
    write_new(output / "environment.json", environment)
    try:
        archive = SealedArchive(args.archive)
        try:
            inventory = archive.json("source_inventory.json")
            require(sha(archive.read("source_inventory.json")) == SOURCE_SHA, "SOURCE_PIN")
            checked = {}
            for path in ("safeshift/candidates/backend.py", "safeshift/candidates/train_run.py",
                         "safeshift/pilot/hnlo.py", "safeshift/pilot/contract.py",
                         "safeshift/candidates/minicpm_resampler_fp32.py"):
                original = subprocess.check_output(["git", "show", RUNTIME + ":" + path])
                require(sha(original) == inventory[path], "RUNTIME_SOURCE_MISMATCH")
                if path in ("safeshift/pilot/hnlo.py", "safeshift/pilot/contract.py"):
                    # Parser and arithmetic called here must remain the released bytes.
                    current = Path(path).read_bytes().replace(b"\r\n", b"\n")
                    require(sha(current) == inventory[path], "PARSER_OR_HNLO_SOURCE_CHANGED")
                checked[path] = sha(original)
            write_new(output / "runtime_source.json", checked)
        finally:
            archive.close()
        def progress(n, status):
            if n == 1 or n % 20 == 0:
                print(json.dumps({"completed": n, "last_status": status}), flush=True)
        summary, rows = verify(args.archive, progress)
        write_new(output / "records.private.json", rows)
        summary["private_records_sha256"] = sha((output / "records.private.json").read_bytes())
        write_new(output / "verification.json", summary)
        public = public_projection(summary)
        public["environment_sha256"] = sha((output / "environment.json").read_bytes())
        public["verification_sha256"] = sha((output / "verification.json").read_bytes())
        public["source_files"] = environment["source_files"]
        write_new(output / "public_receipt.json", public)
        print(json.dumps({k: public[k] for k in ("result", "hnlo_valid", "success_without_hnlo", "reasons")}))
        return 0 if summary["result"] != "BLOCKED" else 2
    except Exception as error:
        # Keep failure evidence; never turn missing custody/decoder into NO.
        write_new(output / "blocked.json", {"result": "BLOCKED", "type": type(error).__name__,
            "reason": str(error), "qualification": "NOT_VERIFIED"})
        print(json.dumps({"result": "BLOCKED", "type": type(error).__name__, "reason": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
