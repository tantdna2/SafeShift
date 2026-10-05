"""Future owner CLI. Observation does not load a model; run requires separate authority."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from safeshift.qualification.d9r20 import runtime as r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("observe", "run", "bundle"))
    parser.add_argument("--model", required=True, choices=("ovis", "plamo", "kosmos"))
    parser.add_argument("--observation")
    parser.add_argument("--authorization")
    args = parser.parse_args()
    config = r.read(ROOT, r.CONFIG)
    candidate = config["models"][args.model]
    snapshot = f".cache/d9r20_snapshots/{args.model}/{candidate['revision']}"
    if args.action == "bundle":
        if args.observation:
            path = r.relative(ROOT, args.observation, r.OUTPUT)
            value = r.strict_json(path.read_bytes())
            if value.get("model") != args.model or path.stat().st_size > 32 * 1024 * 1024:
                raise ValueError("OBSERVATION_BUNDLE_IDENTITY_OR_SIZE")
            with zipfile.ZipFile(path.with_suffix(".zip"), "x", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.write(path, "observation.json")
            print("OBSERVATION_BUNDLE=" + path.with_suffix(".zip").relative_to(ROOT).as_posix())
            return
        folder = r.relative(ROOT, f"{r.OUTPUT}/{candidate['run_id']}", r.OUTPUT)
        report = r.read(ROOT, f"{r.OUTPUT}/{candidate['run_id']}/result.json")
        paths = sorted(folder.rglob("*.json"))
        if not paths or sum(p.stat().st_size for p in paths) > 32 * 1024 * 1024:
            raise ValueError("BUNDLE_EXCEEDS_32_MIB_BOUND")
        for call in report["calls"]:
            for field in ("preparse", "raw", "decoded"):
                if call.get(field):
                    record = call[field]
                    data = (folder / call["call_id"] / record["file"]).read_bytes()
                    if len(data) != record["size_bytes"] or r.digest(data) != record["sha256"]:
                        raise ValueError("BUNDLE_ARTIFACT_INTEGRITY")
        with zipfile.ZipFile(folder.with_suffix(".zip"), "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in paths:
                archive.write(path, path.relative_to(folder).as_posix())
        print("Bounded bundle:", folder.with_suffix(".zip").relative_to(ROOT).as_posix())
        return
    # Required before imports/custom-code execution, including nested asset loads.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_MODULES_CACHE"] = str(ROOT / ".cache/d9r20_modules" / args.model)
    observed = r.observe(ROOT, args.model, snapshot)
    if args.action == "observe":
        if not args.observation:
            parser.error("--observation is required")
        output = r.relative(ROOT, args.observation, r.OUTPUT)
        output.parent.mkdir(parents=True, exist_ok=True)
        r.persisted(output, r.encode(observed))
        print("OBSERVATION_ONLY; MODEL_LOADS=0; failed=" + str(bool(observed["observation_failure"]))
              + "; sha256=" + r.digest(output.read_bytes()))
        return
    if not args.observation or not args.authorization:
        parser.error("run requires --observation and --authorization")
    observation_path = r.relative(ROOT, args.observation, r.OUTPUT)
    authority_path = r.relative(ROOT, args.authorization, r.OUTPUT)
    saved = r.strict_json(observation_path.read_bytes())
    authority = r.strict_json(authority_path.read_bytes())
    if r.encode(saved) != r.encode(observed):
        raise ValueError("LIVE_ENVIRONMENT_SNAPSHOT_OR_IDENTITY_CHANGED")
    r.check_authority(args.model, candidate, saved, authority, r.identity(ROOT), r.digest(observation_path.read_bytes()))
    subprocess.run(["git", "merge-base", "--is-ancestor", r.BASE, "HEAD"], cwd=ROOT, check=True)
    cases = r.prepared_cases(ROOT, args.model)
    from safeshift.qualification.d9r20.backends import NativeBackend
    backend = NativeBackend(args.model, candidate, r.relative(ROOT, snapshot, ".cache"), config["generation"], config["seed"])
    with r.offline():
        report = r.run_kernel(ROOT, args.model, saved, backend, cases, authority=authority)
    print("OWNER_RESULT=" + report["final_verdict"] + "; PARTICIPATION_NOT_AWARDED")


if __name__ == "__main__":
    main()
