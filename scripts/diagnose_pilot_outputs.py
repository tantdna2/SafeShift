"""Verify an evidence ZIP and summarize raw output repetition/format, CPU only."""
import argparse
from pathlib import Path
import tempfile

from safeshift.pilot.artifacts import import_archive, read, sha, write
from safeshift.pilot.output_diagnostics import summarize
from scripts.prepare_three_vlm_pilot import processed


def diagnose(archive, output):
    archive_hash = sha(archive)
    if read(Path(str(archive) + ".sha256.json"))["sha256"] != archive_hash:
        raise ValueError("ARCHIVE_EXTERNAL_SIDECAR_CHECKSUM")
    with tempfile.TemporaryDirectory() as temporary:
        root = import_archive(archive, Path(temporary) / "verified")
        result = {"archive_sha256": archive_hash, "external_sidecar": "PASS", **summarize(root / "run")}
    target = processed(output)
    write(target, result)
    write(Path(str(target) + ".sha256.json"), {"sha256": sha(target)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(diagnose(args.archive, args.output))


if __name__ == "__main__":
    main()
