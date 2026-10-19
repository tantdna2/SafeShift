"""CPU-only raw replay, exact shard pooling and same-ID model comparisons."""
import argparse
from itertools import combinations
import json
import importlib.metadata
import platform
from pathlib import Path

from safeshift.ls1.artifacts import digest, seal, verify_run, write_json
from safeshift.pa3.native.journal import Journal, no_alias
from safeshift.pa3.native.native_score import pending
from safeshift.pa3.native.train_report import metrics, export
from . import cohort
from .capture import replay
from .contract import AUTHORITY, EVIDENCE, authorize, unit


def cpu_context(repo):
    from .bootstrap import git
    packages = {}
    for name in ("transformers", "tokenizers"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "platform": platform.platform(), "packages": packages,
            "source_commit": git(repo, "rev-parse", "HEAD"), "gpu_used": False,
            "command_module": "safeshift.diagnostics.hnlo_train.audit_or_evaluate"}


def seal_raw(root):
    """Custody includes torn bytes without repairing them or declaring capture PASS."""
    root = Path(root)
    files = {}
    for path in sorted(root.rglob("*")):
        no_alias(path)
        if path.is_file():
            files[path.relative_to(root).as_posix()] = {"size_bytes": path.stat().st_size, "sha256": digest(path)}
    journal = Journal(root / "custody", create=True)
    journal.write("files", files)
    journal.seal()


def verify_custody(root):
    root = Path(root)
    journal = Journal(root / "custody")
    if not journal.verify():
        raise ValueError("RAW_CUSTODY_SEAL_REQUIRED_BEFORE_GT")
    expected = journal.read("files")
    actual = {}
    for path in sorted(root.rglob("*")):
        no_alias(path)
        name = path.relative_to(root).as_posix()
        if path.is_file() and not name.startswith(("custody/", "report/")) and name not in ("result.json", "cpu-audit.log"):
            actual[name] = {"size_bytes": path.stat().st_size, "sha256": digest(path)}
    if actual != expected:
        raise ValueError("RAW_CUSTODY_CHANGED_OR_EXTRA_FILES")
    return expected


def raw_rows(root, planned, tokenizer):
    """No GT read here. Preserve pre-load failures, torn captures and missing tail."""
    root, results, terminal = Path(root), [], False
    index = Journal(root / "raw/index")
    if not index.root.exists():
        results = [pending(r["sample_id"]) for r in planned]
        staging = Journal(root / "input-staging")
        if staging.root.exists() and staging.verify() and staging.exists("failure"):
            failure = staging.read("failure")
            i = failure["ordinal"]
            if type(i) is int and 0 <= i < len(planned):
                results[i].update(status="TECHNICAL_ERROR", errors=["INPUT_STAGING:" + failure["type"]])
        return results, False, "NO_WORKER_JOURNAL"
    try:
        sealed = index.verify()
    except (OSError, ValueError):
        sealed = False
    header = index.read("manifest")
    if header != {"samples": cohort.opaque_rows(planned), "expected_count": len(planned)}:
        raise ValueError("RAW_UNIT_SAMPLE_UNIVERSE_CHANGED")
    intact = sealed
    for i, sample in enumerate(planned):
        name = f"sample-{i:06d}"
        cap = Journal(root / "raw" / name)
        try:
            attempted = index.exists(name + ".attempt")
        except ValueError:
            attempted, intact = True, False
        if terminal and attempted:
            raise ValueError("ATTEMPT_AFTER_STOP_OR_MISSING_ORDINAL")
        row = pending(sample["sample_id"], attempted=attempted)
        if attempted:
            try:
                if index.read(name + ".attempt") != {"ordinal": i, "image_sha256": sample["image_sha256"]}:
                    raise ValueError("ATTEMPT_IDENTITY_CHANGED")
                if cap.read("identity") != {"ordinal": i, "image_sha256": sample["image_sha256"],
                                            "evidence_contract": EVIDENCE}:
                    raise ValueError("CAPTURE_IDENTITY_CHANGED")
                if not cap.verify():
                    raise ValueError("UNSEALED_SAMPLE")
                if cap.exists("trace"):
                    row = replay(cap, tokenizer)
                    row["sample_id"] = sample["sample_id"]
                    if index.exists(name + ".result"):
                        saved = index.read(name + ".result")
                        if {**row, "sample_id": str(i)} != saved:
                            raise ValueError("CPU_RESULT_RECOMPUTATION_MISMATCH")
                elif cap.exists("error"):
                    error = cap.read("error")
                    row.update(status=error["status"], errors=[error["type"]])
                else:
                    raise ValueError("RAW_CAPTURE_INCOMPLETE")
            except (FileNotFoundError, OSError) as error:
                intact = False
                row.update(status="INTERRUPTED", score=None, details=None, errors=[type(error).__name__])
            except ValueError as error:
                # Integrity errors are not silently converted into valid results.
                if str(error).startswith(("TORN_WRITE", "UNSEALED_SAMPLE", "RAW_CAPTURE_INCOMPLETE")):
                    intact = False
                    row.update(status="INTERRUPTED", score=None, details=None, errors=[str(error)])
                else:
                    raise
        elif cap.root.exists():
            raise ValueError("ORPHAN_CAPTURE_WITHOUT_ATTEMPT")
        if row["status"] not in ("SUCCESS", "INVALID"):
            terminal = True
        results.append(row)
    completed = intact and index.exists("finish") and not index.exists("failure") and not index.exists("finalization-error")
    if completed and any(r["status"] not in ("SUCCESS", "INVALID") for r in results):
        raise ValueError("FALSE_UNIT_COMPLETION")
    return results, completed, "PASS" if intact else "PARTIAL_TORN_OR_INTERRUPTED"


def checked(root, repo, tokenizer, *, source=None):
    root, repo = Path(root), Path(repo)
    verify_custody(root)  # before metadata/GT or scores
    binding = json.loads((root / "binding.json").read_bytes())
    u = unit(binding["unit"]["model"], binding["unit"]["shard"])
    if binding["unit"] != u:
        raise ValueError("UNIT_IDENTITY_CHANGED")
    from .bootstrap import verify_topology
    proof = verify_topology(repo, binding["source"]["github_pr"], binding["source"]["payload_sha256"])
    if proof != binding["source"] or source is not None and proof != source:
        raise ValueError("RAW_SOURCE_PROOF_MISMATCH")
    if binding["authority"] != json.loads((repo / AUTHORITY).read_bytes()):
        raise PermissionError("RAW_GRANT_MUST_MATCH_RELEASED_AUTHORITY")
    authorize(binding["authority"], proof, u["model"], u["shard"])
    planned = cohort.inference(repo)[u["shard"]]
    if binding["samples"] != planned:
        raise ValueError("ORIGINAL_ID_ORDER_OR_IMAGE_HASH_CHANGED")
    rows, completed, integrity = raw_rows(root, planned, tokenizer)
    index = Journal(root / "raw/index")
    if index.root.exists():
        allowed = {"manifest", "model", "load-start", "load-return", "native-counts", "finish", "failure", "finalization-error"}
        allowed |= {f"sample-{i:06d}.{kind}" for i in range(u["count"]) for kind in ("attempt", "result")}
        try:
            unknown = set(index.inventory()) - allowed
        except (OSError, ValueError):
            unknown = set()  # raw_rows already marks torn integrity PARTIAL
        if unknown:
            raise ValueError("UNKNOWN_OR_EXTRA_UNIT_SAMPLE_RECORD")
    if any(r["attempted"] for r in rows):
        from safeshift.protocol.classification_policy import load_policy, render_prompt
        model = index.read("model")
        policy = load_policy(repo, qwen3_runtime=True)["classification"][u["model"]]
        runtime = model["runtime"]
        from safeshift.ls1.tokenizer import probe
        if model["tokenizer_t1"] != probe(tokenizer):
            raise ValueError("MODEL_TOKENIZER_T1_MISMATCH")
        expected = policy["software_versions"]
        if u["model"] == "qwen3":
            build = json.loads((repo / "configs/diagnostics/hnlo_one_click_build.v1.json").read_bytes())
            expected = {**expected, **build["qwen3_additional_pins"]}
        if (model["model"] != u["model"] or model["policy"] != policy or model["clamp"] is not None
                or model["snapshot"]["model_id"] != u["id"] or model["snapshot"]["revision"] != u["revision"]
                or model["prompt"] != render_prompt(u["model"], repo=repo)
                or runtime["actual"] != expected or runtime["expected"] != expected
                or runtime["cuda"] != u["cuda"] or runtime["visible_devices"] != u["cuda_visible_devices"]):
            raise ValueError("EXACT_MODEL_RUNTIME_PROMPT_REQUIRED")
        from ..hnlo_hf import CAPTURE_FLAGS, QWEN_SOURCES
        source_rows = json.loads((root / "inference/generation-sources.json").read_bytes())
        source_hashes = {r["path"]: r["sha256"] for r in source_rows}
        if u["model"] == "qwen3":
            expected_sources = {"transformers/" + k: v for k, v in QWEN_SOURCES.items()}
        else:
            extra = json.loads((repo / "configs/diagnostics/internvl3_hnlo_generation_sources.v1.json").read_bytes())
            expected_sources = {"transformers/" + r["path"]: r["sha256"] for r in extra["files"]}
        if any(source_hashes.get(k) != v for k, v in expected_sources.items()):
            raise ValueError("PINNED_GENERATION_SOURCE_RECEIPTS_REQUIRED")
        for i, row in enumerate(rows):
            cap = Journal(root / "raw" / f"sample-{i:06d}")
            if row["persisted"]:
                raw = cap.read("trace")
                if (raw["generation_config"] != model["generation_config"] or
                        raw["generation_kwargs"] != {**policy["decoding"], **CAPTURE_FLAGS}):
                    raise ValueError("NATIVE_MODEL_CONFIG_OR_POLICY_CHANGED")
        counts = index.read("native-counts") if index.exists("native-counts") else None
        if counts is not None and (counts["load_calls"] != 1 or
                counts["generate_ordinals"] != list(range(len(counts["generate_ordinals"]))) or
                any(type(i) is not int or not 0 <= i < u["count"] for i in counts["generate_ordinals"])):
            raise ValueError("NATIVE_CALL_BUDGET_OR_DUPLICATE")
        if completed and (counts is None or counts["generate_ordinals"] != list(range(u["count"]))):
            raise ValueError("COMPLETE_NATIVE_COUNTS_REQUIRED")
        worker_path = root / "inference/result.json"
        worker_result = json.loads(worker_path.read_bytes()) if worker_path.exists() else {"status": "KILLED"}
        if worker_result["status"] != "RETURNED":
            completed = False
            for row in rows:
                if row["status"] == "SUCCESS":
                    row.update(status="TECHNICAL_ERROR", score=None, details=None,
                               errors=["GLOBAL_WORKER_ADMISSION_OR_FINALIZATION_FAILED"])
        if u["model"] == "internvl3" and worker_result["status"] == "RETURNED":
            observation = worker_result["network_observation"]
            if (not worker_result["driver_handles_retained_through_finalization"] or
                    observation.get("stop_reason") is not None or observation.get("security_assessment") != "PARTIAL"):
                raise ValueError("DRIVER_OR_NETWORK_PREREQUISITES_FAILED")
    return u, rows, completed, integrity


def evaluate(root, repo, tokenizer, *, source=None):
    u, rows, completed, integrity = checked(root, repo, tokenizer, source=source)
    all_metadata = cohort.metadata(repo)  # raw custody + explicit per-unit label approval checked
    metadata = {r["sample_id"]: all_metadata[r["sample_id"]] for r in rows}
    evaluation = metrics(rows, metadata, completed)
    export(Path(root) / "report", rows, metadata, evaluation,
           {"schema": "hnlo-train-cpu-audit-v1", "unit": u, "integrity": integrity, "results": rows,
            "cpu_environment": cpu_context(repo),
            "evidence_contract": EVIDENCE, "full_vocab_replay": False,
            "claim": "RAW_SUMMARY_REPLAY_ONLY_NOT_FULL_VECTOR_RECONSTRUCTION"})
    return evaluation


def pool(shards, expected_ids):
    """Pure validation, never shard-AUROC averaging; useful for synthetic tests."""
    if len(shards) != 4 or {s[0]["shard"] for s in shards} != set(range(4)):
        raise ValueError("EXACT_FOUR_DISTINCT_SHARDS_REQUIRED")
    models = {s[0]["model"] for s in shards}
    if len(models) != 1:
        raise ValueError("MIXED_MODEL_POOL_FORBIDDEN")
    rows = [r for _, part, _, _ in shards for r in part]
    if len(rows) != len(expected_ids) or {r["sample_id"] for r in rows} != set(expected_ids):
        raise ValueError("EXACT_DISJOINT_COMPLETE_RESULT_UNIVERSE_REQUIRED")
    return sorted(rows, key=lambda r: r["sample_id"])


def merge(roots, repo, tokenizer, output):
    shards = [checked(root, repo, tokenizer) for root in roots]
    # Every raw package is checked before any GT metadata is opened.
    all_metadata = cohort.metadata(repo)
    rows = pool(shards, all_metadata)
    evaluation = metrics(rows, all_metadata, all(s[2] for s in shards))
    export(output, rows, all_metadata, evaluation,
           {"schema": "hnlo-train-pooled-audit-v1", "results": rows,
            "cpu_environment": cpu_context(repo),
            "shards": [{"unit": s[0], "integrity": s[3]} for s in shards],
            "method": "RAW_REPLAY_THEN_POOLED_NOT_SHARD_AUC_AVERAGE"})
    return rows, evaluation


def comparisons(models, metadata):
    """Each model's full coverage plus paired/triple intersections, by domain too."""
    if set(models) != {"qwen2_5", "qwen3", "internvl3"}:
        raise ValueError("EXACT_THREE_MODELS_REQUIRED_MOONDREAM_DEFERRED")
    own = {m: metrics(rows, metadata, False) for m, rows in models.items()}
    indices = {m: {r["sample_id"]: r for r in rows} for m, rows in models.items()}
    intersections = {}
    for n in (2, 3):
        for names in combinations(sorted(models), n):
            ids = sorted(set.intersection(*[{sid for sid, r in indices[m].items() if r["status"] == "SUCCESS"} for m in names]))
            common_meta = {sid: metadata[sid] for sid in ids}
            intersections["|".join(names)] = {"n": len(ids), "planned": len(metadata),
                "coverage_of_planned": len(ids) / len(metadata) if metadata else None,
                "eligible_ids": ids, "models": {m: metrics([indices[m][sid] for sid in ids], common_meta, False) for m in names}}
    return {"scope": "DESCRIPTIVE_FULL_TRAIN", "full_cohort": own, "same_ids": intersections,
            "technical_difference": "Qwen2.5 PA3-R2 pre-merger clamp; Qwen3/InternVL3 no clamp.",
            "hnlo_accuracy": None, "threshold": None, "moondream2": "DEFERRED_STILL_REQUIRED_FOR_SEMINAR"}


def baseline_rows(root):
    """Consume the exact previously audited Qwen2.5 report; never touch raw dataset."""
    root = Path(root)
    verify_run(root)
    expected = {"metrics.json": "21cbb7fded176c657298ab0e3dc5f2098801211082a453952de6e9feecf4daf4",
                "audit.json": "87b005541c7342c42967e7a4e48723401d12e33699103875917b583a25db894e"}
    if any(digest(root / name) != h for name, h in expected.items()):
        raise ValueError("EXACT_OFFICIAL_QWEN25_CPU_REPORT_REQUIRED")
    evidence = json.loads((root / "audit.json").read_bytes())
    return [r for shard in evidence["shards"] for r in shard["audit"]["results"]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--runs", type=Path, nargs=4, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True, help="Already available pinned tokenizer files; never downloads")
    parser.add_argument("--model", choices=("qwen3", "internvl3"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    a = parser.parse_args()
    import os
    os.environ.update(CUDA_VISIBLE_DEVICES="", USE_TORCH="0", USE_TF="0", USE_FLAX="0",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from transformers import AutoTokenizer
    from .tokenizer import verify
    verify(a.model, a.tokenizer, a.repo)
    from ..hnlo_capture import ordered_t1_ids
    from safeshift.ls1.tokenizer import probe
    tokenizer = AutoTokenizer.from_pretrained(str(a.tokenizer), local_files_only=True, trust_remote_code=False, use_fast=True)
    ordered_t1_ids(probe(tokenizer))
    checked_units = [json.loads((p / "binding.json").read_bytes())["unit"] for p in a.runs]
    if any(u["model"] != a.model for u in checked_units):
        raise ValueError("CLI_MODEL_AND_PACKAGES_MISMATCH")
    merge(a.runs, a.repo, tokenizer, a.output)


if __name__ == "__main__":
    main()
