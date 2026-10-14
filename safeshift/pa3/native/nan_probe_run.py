"""DEC-PA3-009 NaN-localization execution: authority, durable journal, recovery.

Authority reuses the audited PA3 rule BASE -> F1 -> authority-only F2 -> standard
merge M, with its own file and scope. DECISIONS.md text grants nothing. A null
grant (this Draft) denies before Git, runtime, model or image access. Scope is
pinned here: two TRAIN images, baseline then candidate clamp, four prefills, one
run, no retry. Every prefill is journaled as started before it runs, and its
result (raw step-0 logits included) is durably written right after. The journal
is append-only; SHA-256 is integrity, not authenticity.
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from safeshift.protocol.schema import strict_json
from ..artifacts import json_bytes, receipt
from . import preflight
from .journal import Journal, no_alias, run_path

NAN_BASE = "486b4af7ad1f402395b60b0c36ebfd80a74cf4de"
AUTHORITY = "configs/pa3/nan_probe_authority.v1.json"
PRIOR_AUTHORITIES = ("configs/pa3/feasibility_authority.v1.json", "configs/pa3/full_train_authority.v1.json",
                     "configs/pa3/seminar_direction_authority.v1.json")
RUN_ID = "pa3-qwen-nan-probe-dec009"
RUNTIME_PLAN = "configs/pre_freeze/qwen2_5_t4_runtime.v1.json"
SAMPLES = (
    {"sample_id": "power-Level04-Wheeled-001764-002",
     "image_locator": "DATA_PATH/train/Annotations/Normal_data/power-Level04-Wheeled-001764/"
                      "power-Level04-Wheeled-001764-002.jpg",
     "image_sha256": "c11429a2c00fde564fe7e909c3f8d24f1a6cec6775087d52c0cc4c476bd4cb65"},
    {"sample_id": "metallurgy-Level04-Wheeled-001232-001",
     "image_locator": "DATA_PATH/train/Annotations/Normal_data/metallurgy-Level04-Wheeled-001232/"
                      "metallurgy-Level04-Wheeled-001232-001.jpg",
     "image_sha256": "a142dc0d75c9d57466b8295400501f4865dc1c6a4598e98463593684bf04a726"},
)
PASSES = ("baseline", "candidate_merger_clamp")
PLAN = tuple((s["sample_id"], p) for s in SAMPLES for p in PASSES)
SCOPE = {"decision": "DEC-PA3-009", "mode": "nan-localization", "run_id": RUN_ID,
         "purpose": "FP16_NONFINITE_LOCALIZATION_DIAGNOSTIC_NO_PA3_SCORE", "split": "TRAIN",
         "model": "Qwen/Qwen2.5-VL-3B-Instruct", "revision": "66285546d2b821cf421d4f5eb2576359d3770cd3",
         "precision": "FP16", "attention": "sdpa", "gpu": "T4", "prompt": "C1", "batch_size": 1,
         "samples": [dict(s) for s in SAMPLES], "passes": list(PASSES), "max_prefills": 4,
         "max_new_tokens": 1, "max_runs": 1, "retry": False, "test_access": False,
         "not_attempted_access": False, "pa3_scores": False, "production_clamp": False}
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")


def require_authority(repo, source_commit, runtime_inventory_sha256):
    """Deny unless HEAD is a verified standard merge of an authority-only release."""
    repo = Path(repo)
    path = repo / AUTHORITY
    if not path.is_file():
        raise PermissionError("NAN_PROBE_AUTHORITY_NOT_RELEASED")
    value = strict_json(path.read_bytes())
    if set(value) != {"base", "implementation", "scope", "grant"}:
        raise PermissionError("NAN_PROBE_AUTHORITY_SCHEMA")
    if value["scope"] != SCOPE:
        raise PermissionError("NAN_PROBE_SCOPE_CHANGED")
    grant = value["grant"]
    if grant is None:
        raise PermissionError("NAN_PROBE_GRANT_PENDING_RESEARCH_LEAD")
    if (not isinstance(grant, dict) or set(grant) != {"approval", "decision", "runtime_inventory_sha256"}
            or not isinstance(grant["approval"], str) or not grant["approval"].strip()
            or grant["decision"] != SCOPE["decision"]
            or type(grant["runtime_inventory_sha256"]) is not str
            or not HEX64.fullmatch(grant["runtime_inventory_sha256"])
            or not all(type(value[k]) is str and HEX40.fullmatch(value[k]) for k in ("base", "implementation"))):
        raise PermissionError("NAN_PROBE_GRANT_SCHEMA")
    if runtime_inventory_sha256 != grant["runtime_inventory_sha256"]:
        raise PermissionError("NAN_PROBE_APPROVAL_BINDING:runtime_inventory_sha256")
    try:
        head = preflight.git(repo, "rev-parse", "HEAD").decode()
        parents = preflight.git(repo, "rev-list", "--parents", "-n", "1", head).decode().split()
        if head != source_commit or len(parents) != 3 or parents[1] != value["base"]:
            raise PermissionError("NAN_PROBE_STANDARD_MERGE_REQUIRED_DRAFT_LOCKED")
        preflight.git(repo, "merge-base", "--is-ancestor", NAN_BASE, value["base"])
        f2, f1 = parents[2], value["implementation"]
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f2).decode().split() != [f2, f1]:
            raise PermissionError("NAN_PROBE_AUTHORITY_PARENT")
        if preflight.git(repo, "rev-list", "--parents", "-n", "1", f1).decode().split() != [f1, value["base"]]:
            raise PermissionError("NAN_PROBE_IMPLEMENTATION_PARENT")
        if preflight.git(repo, "diff", "--name-only", f1, f2).decode() != AUTHORITY:
            raise PermissionError("NAN_PROBE_AUTHORITY_ONLY_COMMIT_REQUIRED")
        if preflight.git(repo, "rev-parse", head + "^{tree}") != preflight.git(repo, "rev-parse", f2 + "^{tree}"):
            raise PermissionError("NAN_PROBE_MERGE_TREE_CHANGED")
        if path.read_bytes() != preflight.git_blob(repo, f2, AUTHORITY):
            raise PermissionError("NAN_PROBE_AUTHORITY_BYTES_CHANGED")
        for prior in PRIOR_AUTHORITIES:
            if preflight.git_blob(repo, head, prior) != preflight.git_blob(repo, NAN_BASE, prior):
                raise PermissionError("NAN_PROBE_CHANGED_PRIOR_AUTHORITY")
        if preflight.git(repo, "status", "--porcelain", "--untracked-files=no"):
            raise PermissionError("NAN_PROBE_DIRTY_SOURCE")
        # Committed bytes of every execution input; rejects untracked import shadows.
        proof = preflight.source(repo, source_commit)
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError("NAN_PROBE_SOURCE_PROOF_MISSING") from exc
    return {"authority": value, "source": proof}


def open_authorized(sample, dataset_root):
    """Only the two pinned triplets; bytes are hashed before any decode."""
    if sample not in SAMPLES:
        raise PermissionError("NAN_PROBE_IMAGE_OUTSIDE_SCOPE")
    from safeshift.ls1.experiment import open_sample
    return open_sample(dict(sample), dataset_root)


def _fsync_directory(path):
    if os.name != "nt":  # Windows cannot open a directory for fsync
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


class DurableJournal(Journal):
    """Staged temp file, fsync, then an atomic no-overwrite hard link into place."""

    def staging(self):
        return no_alias(self.root.parent / (self.root.name + "-staging"))

    def write(self, name, value):
        if self.path("seal").exists():
            raise ValueError("SEALED_JOURNAL_IMMUTABLE")
        path = self.path(name)
        side = no_alias(path.with_suffix(".sha256.json"))
        if path.exists() or side.exists():
            raise FileExistsError("NO_OVERWRITE_OR_RETRY:" + name)
        staging = self.staging()
        staging.mkdir(exist_ok=True)
        data = json_bytes(value)
        # Payload first, receipt last: a payload without receipt is a detectable torn write.
        for target, payload in ((path, data), (side, json_bytes(receipt(data)))):
            temp = staging / (target.name + ".tmp")
            with temp.open("xb") as stream:  # a stale temp from a crash is never reused
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temp, target)  # atomic; fails if target exists
            os.unlink(temp)
            _fsync_directory(self.root)
        return self.read(name)

    def names(self):
        return sorted(p.name[:-5] for p in self.root.iterdir()
                      if p.name.endswith(".json") and not p.name.endswith(".sha256.json"))


def begin_prefill(journal, index, sample, mode):
    """Durably record a start before the prefill; the four-call budget is on disk."""
    started = [n for n in journal.names() if re.fullmatch(r"prefill-\d+\.attempt", n)]
    if len(started) >= SCOPE["max_prefills"]:
        raise PermissionError("NAN_PROBE_PREFILL_BUDGET_EXHAUSTED")
    if index != len(started) or index >= len(PLAN) or PLAN[index] != (sample["sample_id"], mode):
        raise PermissionError("NAN_PROBE_PREFILL_OUTSIDE_AUTHORIZED_PLAN")
    return journal.write(f"prefill-{index}.attempt", {
        "index": index, "sample": sample, "pass": mode, "retry_permitted": False,
        "timestamp_utc": datetime.now(timezone.utc).isoformat()})


def execute(journal, make_scorer, open_image, probe):
    """Core loop; tests inject CPU doubles. Never retries or skips ahead."""
    journal.write("model-load.attempt", {"timestamp_utc": datetime.now(timezone.utc).isoformat()})
    scorer = make_scorer()
    journal.write("model", {"hardware": scorer.hardware, "software": scorer.software,
                            "snapshot": scorer.snapshot_receipt})
    samples = {s["sample_id"]: s for s in SAMPLES}
    raw = {}
    for index, (sample_id, mode) in enumerate(PLAN):
        sample = samples[sample_id]
        begin_prefill(journal, index, sample, mode)
        with open_image(sample) as image:
            report, logits = probe(scorer, image, clamp=mode != "baseline")
        journal.write(f"prefill-{index}.result", {"index": index, "sample": sample, "pass": mode,
                                                  "pa3_score": None, "raw_step0_logits": logits, **report})
        raw[index] = logits
    journal.write("comparison", compare(raw))
    journal.write("finish", {"status": "COMPLETED", "prefills": len(PLAN)})


def compare(raw):
    """Bitwise identity of baseline vs candidate step-0 raw logits per sample."""
    result = {}
    for k, sample in enumerate(SAMPLES):
        a, b = raw.get(2 * k), raw.get(2 * k + 1)
        result[sample["sample_id"]] = None if a is None or b is None else (
            {key: a[key] for key in ("dtype", "shape")} == {key: b[key] for key in ("dtype", "shape")}
            and a["sha256"] == b["sha256"] and a["base64"] == b["base64"])
    return result


def recover(repo):
    """CPU-only, no authority needed: classify, never repair/retry, then package."""
    root = run_path(repo, RUN_ID)
    if not root.is_dir():
        raise FileNotFoundError("NAN_PROBE_JOURNAL_MISSING")
    journal = DurableJournal(root)
    files = {p.name for p in root.iterdir()}
    names = sorted({n.split(".sha256.json")[0].removesuffix(".json") for n in files})
    states, raw = {}, {}
    for name in names:
        try:
            value = journal.read(name) if journal.exists(name) else None
            states[name] = "VALID" if value is not None else "MISSING"
            if value is not None and re.fullmatch(r"prefill-\d+\.result", name):
                raw[value["index"]] = value["raw_step0_logits"]
        except Exception as exc:  # torn or corrupt: keep bytes, report, never rewrite
            states[name] = "INVALID:" + type(exc).__name__ + ":" + str(exc)[:120]
    prefills = []
    for index, (sample_id, mode) in enumerate(PLAN):
        attempt, result = states.get(f"prefill-{index}.attempt"), states.get(f"prefill-{index}.result")
        status = ("NOT_STARTED" if attempt is None and result is None else
                  "CORRUPT_ATTEMPT_RECORD" if attempt != "VALID" else
                  "COMPLETE" if result == "VALID" else
                  "INCOMPLETE_STARTED_NO_RESULT" if result is None else "INCOMPLETE_STARTED_INVALID_RESULT")
        prefills.append({"index": index, "sample_id": sample_id, "pass": mode, "status": status})
    staging = journal.staging()
    report = {"run_id": RUN_ID, "files": states, "prefills": prefills, "comparison": compare(raw),
              "completed": states.get("finish") == "VALID", "sealed": states.get("seal") == "VALID",
              "staging_leftovers": sorted(p.name for p in staging.iterdir()) if staging.is_dir() else [],
              "retry_permitted": False}
    archive = no_alias(root.with_suffix(".tar.gz"))
    if not archive.exists():
        journal.package()  # exclusive create; packages torn journals as-is
    target = no_alias(root.parent / (root.name + "-recovery.json"))
    if not target.exists():
        with target.open("xb") as stream:
            stream.write(json_bytes(report))
            stream.flush()
            os.fsync(stream.fileno())
    return report


def run(args):
    """Child: authority already rechecked in main(); journal precedes model/data."""
    from safeshift.ls1.runtime import NativeScorer
    from .nan_probe import probe_sample
    journal = DurableJournal(run_path(args.repo, RUN_ID), create=True)  # exists -> no retry
    stage = "AUTHORITY_RECORD"
    try:
        journal.write("authority", args.proof)
        stage = "T1"
        t1, tokenizer = preflight.tokenizer_check(args.repo, args.snapshot)
        journal.write("t1", t1)
        if t1["status"] != "PASS":
            raise ValueError("T1_" + t1["status"])
        stage = "PREFILLS"
        execute(journal, lambda: NativeScorer("qwen2_5", args.snapshot, tokenizer, t1["candidate_token_ids"],
                                              repo=args.repo),
                lambda sample: open_authorized(sample, args.dataset_root), probe_sample)
    except BaseException as exc:
        journal.write("failure", {"stage": stage, "exception_type": type(exc).__name__,
                                  "message": str(exc)[:500], "retry_permitted": False})
        raise
    finally:
        try:
            journal.seal()
        finally:
            journal.package()


def launch(args):
    """Kaggle parent: audited runtime/model restore, one offline child, then recovery."""
    from safeshift.ls1.kaggle import attached_path, verify_runtime_input, runtime_interpreter, restore_model
    from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
    runtime_input = attached_path(args.inputs, args.runtime_input)
    verify_runtime_input(runtime_input, attached_path(args.inputs, args.runtime_inventory_input),
                         args.runtime_inventory_sha256)
    restore_repo = Path(tempfile.mkdtemp(prefix="pa3-nan-probe-runtime-"))
    (restore_repo / RUNTIME_PLAN).parent.mkdir(parents=True)
    shutil.copyfile(args.repo / RUNTIME_PLAN, restore_repo / RUNTIME_PLAN)
    snapshot = restore_model(restore_repo, attached_path(args.inputs, args.model_input), "qwen2_5")
    site = attached_path(args.inputs, args.runtime_site_packages) if args.runtime_site_packages else None
    if site and not site.resolve().is_relative_to(runtime_input.resolve()):
        raise ValueError("SITE_OUTSIDE_HASH_VERIFIED_RUNTIME")
    runtime = runtime_interpreter(restore_repo, runtime_input, "qwen2_5", site)
    env = {**os.environ, **OFFLINE_ENV, "CUDA_VISIBLE_DEVICES": "0", "PYTHONPATH": str(args.repo),
           "PYTHONNOUSERSITE": "1"}
    if runtime["site_packages"]:
        env["PYTHONPATH"] += os.pathsep + runtime["site_packages"]
    env.pop("PYTHONHOME", None)
    command = [runtime["python"], "-s", "-m", "safeshift.pa3.native.nan_probe_run", "--repo", str(args.repo),
               "--source-commit", args.source_commit, "--runtime-inventory-sha256", args.runtime_inventory_sha256,
               "--snapshot", str(snapshot), "--dataset-root", str(attached_path(args.inputs, args.dataset_input))]
    try:
        child = subprocess.run(command, cwd=args.repo, env=env, check=False)  # one attempt, no retry
    finally:
        if run_path(args.repo, RUN_ID).is_dir():
            recover(args.repo)  # also after a child crash, CUDA abort or interrupt
    if child.returncode:
        raise RuntimeError("NAN_PROBE_CHILD_FAILED_NO_RETRY")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--recover", action="store_true", help="CPU-only: classify and package an existing journal")
    parser.add_argument("--launch", action="store_true", help="Kaggle parent mode")
    parser.add_argument("--source-commit")
    parser.add_argument("--runtime-inventory-sha256")
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--dataset-root", type=Path, help="TRAIN root containing DATA_PATH/")
    for name in ("inputs", "runtime-input", "runtime-inventory-input", "runtime-site-packages",
                 "model-input", "dataset-input"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if args.recover:
        return recover(args.repo)
    # Parent and child both check, before any runtime, model, journal or image access.
    args.proof = require_authority(args.repo, args.source_commit, args.runtime_inventory_sha256)
    if run_path(args.repo, RUN_ID).exists():
        raise FileExistsError("NAN_PROBE_RUN_EXISTS_NO_RETRY")
    if args.launch:
        return launch(args)
    if not (args.snapshot and args.dataset_root):
        parser.error("--snapshot and --dataset-root are required in child mode")
    return run(args)


if __name__ == "__main__":
    main()
