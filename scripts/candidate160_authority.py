"""Emit unsigned worksheets or validate supplied authority; never grant approval.

Only authority JSON is read by --check. No TRAIN, weights, GPU or ledger mutation.
"""
import argparse
from pathlib import Path

from safeshift.candidates import train_contract as c
from safeshift.candidates.source import ROOT
from safeshift.pilot import contract as pilot
from safeshift.pilot.artifacts import read, write


REFERENCES = ("G0", "T0", "O3", "code_review_ref", "manifest_review_ref", "policy_approval_ref",
              "runtime_approval_ref", "external_ledger_ref", "owner_approval_ref", "research_lead_review_ref")
PERMISSIONS = ("allow_train_images", "allow_folder_gt", "allow_checkpoint_read", "allow_gpu",
               "allow_raw_export", "allow_software_install", "private_custody_approved")


def worksheet(key, ref, source):
    """Bindings are facts; null values are decisions still required from humans."""
    p = {n: None for n in ("early_behavior_after", "review_after", "review_wait_seconds", "review_mode",
         "invalid_max_count", "repeat_max_count", "dominance_min_valid", "dominance_max_fraction",
         "normal_min_support", "normal_fpr_max", "anomaly_min_support", "anomaly_fnr_max",
         "driver_versions", "free_mib_per_gpu", "free_ram_mib", "free_scratch_mib", "free_output_mib",
         "free_gpu0_runtime_mib")}
    grant = {"schema": "safeshift-candidate160-grant-v2", "model_key": key, "model": c.model(key),
        "base": c.BASE, "runtime_ref": ref, "source_sha256": source, **c.configuration_hashes(key),
        "manifest_sha256": c.MANIFEST, "inventory_sha256": c.INVENTORY,
        "data_revision": pilot.DATA_REVISION, "master_sha256": pilot.MASTER_SHA, "split": "TRAIN",
        "max_initial_ids": 160, "max_native_calls": 160, "retry_sample_ids": [], "resume": False,
        "run_id": None, "attempt_id": None, "max_seconds": None, "expires_unix": None,
        **{n: None for n in (*REFERENCES, *PERMISSIONS)}, "policy": p, "batch_authorization": None}
    reservation = {"schema": "safeshift-candidate160-reservation-v1", "status": None,
        **{n: grant[n] for n in ("run_id", "attempt_id", "model_key", "source_sha256", "runtime_ref",
                               "manifest_sha256", "expires_unix", "external_ledger_ref")}, "grant_sha256": None}
    batch = {"schema": "safeshift-candidate160-batch-authorization-v1", "allow_automatic_continuation": None,
        "research_lead_approval_ref": None, "policy_sha256": None, "execution_binding_sha256": None,
        "conditions": c.BATCH_CONDITIONS}
    return grant, reservation, batch


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=c.KEYS, required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--templates", help="New directory under data/processed for unsigned worksheets")
    group.add_argument("--check", help="Supplied grant JSON (no private data/checkpoint reads)")
    p.add_argument("--ledger", help="Supplied external reservation JSON, required with --check")
    a = p.parse_args(argv)
    meta = read(ROOT / f"notebooks/SafeShift_CANDIDATE160_{a.model}.ipynb")["metadata"]["safeshift"]
    source, ref = c.source_hash(), meta["runtime_ref"]
    if meta["source_sha256"] != source:
        p.error("NOTEBOOK_SOURCE_STALE")
    if a.templates:
        target = Path(a.templates).absolute()
        if not target.is_relative_to(ROOT / "data/processed"):
            p.error("UNSIGNED_WORKSHEETS_MUST_STAY_LOCAL_DATA_PROCESSED")
        target.mkdir(parents=True, exist_ok=False)
        g, ledger, batch = worksheet(a.model, ref, source)
        write(target / f"grant_candidate160_{a.model}.json", g)
        write(target / f"ledger_candidate160_{a.model}.json", ledger)
        write(target / "batch_authorization.UNAPPROVED.json", batch)
        write(target / f"candidate_checkpoint_{a.model}.json",
              {"schema": "safeshift-candidate160-checkpoint-v1", "model": c.model(a.model)})
        print("BLOCKED: unsigned worksheets; no approval, reservation or execution created")
        return 0
    if not a.ledger:
        p.error("--ledger required with --check")
    try:
        c.authorize(read(a.check), a.model, source, ref, read(a.ledger))
    except (ValueError, KeyError, TypeError, OSError) as error:
        print("BLOCKED:", str(error))
        return 2
    print("AUTHORITY_RECORDS_STRUCTURALLY_VALID; independently verify real approvals/current ledger. GPU UNVERIFIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
