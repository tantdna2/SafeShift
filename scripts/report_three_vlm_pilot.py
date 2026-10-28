"""Verify private archives, CPU-replay HNLO, join exact shared manifest, report."""
import argparse
from pathlib import Path
import tempfile

from safeshift.pilot.artifacts import import_archive, read, sha, write
from safeshift.pilot.contract import MODELS, PROMPT_SHA, digest, parse_label, settings
from safeshift.pilot.hnlo import replay, tokenizer_replay
from safeshift.pilot.report import save_reports
from safeshift.pilot.bootstrap import recover_accounting
from scripts.prepare_three_vlm_pilot import processed


def combine_archives(archives, output):
    by_model, plan, expected, failures, unbound, runtime = {}, None, None, {}, {}, {}
    with tempfile.TemporaryDirectory() as scratch:
        for key, archive in archives.items():
            root = import_archive(archive, Path(scratch) / key)
            if not (root / "pilot_manifest.json").exists():
                unbound[key] = {"status": "INCONCLUSIVE/BLOCKED", "reason": "NO_BOUND_MANIFEST_IN_BLOCKED_ARCHIVE"}
                continue
            candidate = read(root / "pilot_manifest.json")
            if expected is not None and digest(candidate) != expected:
                raise ValueError("ALL_THREE_EXACT_SAME_MANIFEST_REQUIRED")
            expected, plan = digest(candidate), candidate
            runtime[key] = {name: read(root / path) if (root / path).exists() else None for name, path in
                            (("session", "session.json"), ("runtime", "run/runtime.json"), ("checkpoint", "model_snapshot.json"))}
            if not (root / "run/identity.json").exists():
                by_model[key] = recover_accounting(root, plan)
                failures[key] = read(root / "supervisor_failure.json") if (root / "supervisor_failure.json").exists() else None
                continue
            identity = read(root / "run/identity.json")
            config = digest(settings(key))
            grant = read(root / "grant.json")
            if (identity["model_key"] != key or identity["model"] != MODELS[key] or identity["manifest_sha256"] != expected
                    or identity["config_sha256"] != config or grant["source_sha256"] != identity["source_sha256"]
                    or grant["config_sha256"] != config or grant["manifest_sha256"] != expected):
                raise ValueError("ARCHIVE_MODEL_OR_INPUT_MISMATCH")
            results = recover_accounting(root, plan)
            decoder = None
            for i, row in enumerate(plan["main"] + plan["supplement"]):
                result = results[row["sample_id"]]
                if result["status"] in ("SUCCESS", "INVALID"):
                    p = root / f"run/samples/{i:06d}/raw.json"
                    if sha(p) != result["raw_sha256"]:
                        raise ValueError("RAW_BINDING_CHECKSUM")
                    raw = read(p)
                    prefix = p.parent
                    native, request = read(prefix / "native.json"), read(prefix / "request.json")
                    import hashlib
                    if (native["input_ids"] != request["input_ids"] or raw["input_ids"] != native["input_ids"]
                            or native["generated_ids"] != raw["generated_ids"]
                            or raw["token_probe"] != request["token_probe"]
                            or hashlib.sha256(request["prompt"].encode()).hexdigest() != PROMPT_SHA
                            or read(prefix / "processors.json")["actual"] != raw["actual_logits_processors"]):
                        raise ValueError("NATIVE_REQUEST_TRACE_BINDING")
                    for j, step in enumerate(raw["steps"]):
                        if read(prefix / f"steps/{j:03d}.json") != step:
                            raise ValueError("RAW_STEP_FILE_BINDING")
                    if result.get("hnlo", {}).get("status") == "HNLO_VALIDATED":
                        from tokenizers import Tokenizer
                        tp = root / "tokenizer/runtime_tokenizer.json"
                        if sha(tp) != raw["tokenizer_serialization_sha256"]:
                            raise ValueError("RUNTIME_TOKENIZER_CHECKSUM")
                        decoder = decoder or Tokenizer.from_file(str(tp))
                        if tokenizer_replay(raw, decoder) != raw["cpu_tokenizer_replay"]:
                            raise ValueError("CPU_TOKENIZER_REPLAY_CHANGED")
                    if (raw["identity"]["sample_id"] != row["sample_id"] or raw["identity"]["input_sha256"] != row["image_sha256"]
                            or raw["identity"]["config_sha256"] != config or raw["identity"]["manifest_sha256"] != expected
                            or raw["identity"]["model"] != MODELS[key] or raw["identity"]["run_id"] != identity["run_id"]):
                        raise ValueError("RAW_SAMPLE_ID_INPUT_BINDING")
                    label = parse_label(raw["response"])
                    if result["label"] != label or result["hnlo"] != replay(raw, label):
                        raise ValueError("INDEPENDENT_CPU_REPLAY_MISMATCH")
            by_model[key] = results
            if (root / "run/failure.json").exists():
                failures[key] = read(root / "run/failure.json")
        if plan is None:
            if not unbound:
                raise ValueError("AT_LEAST_ONE_ACTUAL_ARCHIVE_REQUIRED")
            blocked = {"status": "INCONCLUSIVE/BLOCKED", "reason": "NO_APPROVED_BOUND_ID_TABLE_AVAILABLE",
                       "models": unbound, "metrics": None}
            write(processed(output) / "blocked.json", blocked)
            return blocked
        reports = save_reports(processed(output), plan, by_model, failures=failures, runtime=runtime)
        write(processed(output) / "unbound_archives.json", unbound)
        return reports


def main():
    p = argparse.ArgumentParser()
    for key in MODELS:
        p.add_argument("--" + key)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    combine_archives({k: getattr(a, k) for k in MODELS if getattr(a, k)}, a.output)


if __name__ == "__main__":
    main()
