"""Verify published CPU receipts against current code; does not execute ML."""
import argparse
from pathlib import Path
from safeshift.pilot.artifacts import read, sha, safe
from safeshift.pilot.contract import source_digest
from safeshift.candidates.source import ROOT, LOCK, require


def verify(index, root=ROOT):
    index = Path(index)
    manifest = read(index)
    models = set()
    for filename, checksum in manifest["receipts"].items():
        path = safe(index.parent, filename)
        require(sha(path) == checksum, "RECEIPT_HASH:" + filename)
        receipt = read(path)
        if receipt.get("schema") != "safeshift-candidate-integration-cpu-v1":
            raise ValueError("RECEIPT_SCHEMA")
        key = receipt["model_key"]
        require(receipt["model"] == {k: read(root/"configs/cpu_g2_g3/public_source_lock.json")[key][k]
                                    for k in ("id", "revision")}, "RECEIPT_MODEL_IDENTITY")
        for name, expected in receipt["source_sha256"].items():
            require(sha(safe(root, name)) == expected, "EXECUTED_SOURCE_HASH:" + name)
        # Reject receipts with missing dependency/script/test coverage as well.
        from scripts.rehearse_candidate_integration import evidence_sources
        require(set(receipt["source_sha256"]) == set(evidence_sources()), "INCOMPLETE_EVIDENCE_SOURCE_SET")
        require(receipt["pilot_source_sha256"] == source_digest(root), "PILOT_SOURCE_CHANGED")
        require(receipt["sources_unchanged_during_run"] is True, "SOURCE_CHANGED_DURING_RUN")
        require(receipt["status"] == "CPU_CHECKS_PASS" and receipt["failures"] == receipt["errors"] == 0,
                "CPU_CHECKS_NOT_PASS")
        events = receipt["test_events"]
        require(len(events) == receipt["tests_run"] and sum(e["status"] == "SKIP" for e in events) == receipt["skips"],
                "TEST_ACCOUNTING")
        require(all(e["status"] in ("PASS", "SKIP") for e in events), "FAILED_TEST_EVENT")
        native = [e for e in events if e["test"].startswith("test_candidate_native.")]
        require(bool(native) and all(e["status"] == "PASS" for e in native), "NATIVE_TESTS_MUST_PASS")
        require(receipt["weights"] == "NOT_DOWNLOADED_OR_DESERIALIZED" and receipt["inference"] == "NOT_RUN"
                and receipt["gpu"] == "NOT_CALLED", "EVIDENCE_SCOPE")
        models.add(key)
    require(models == {"internvl35", "minicpm4"}, "BOTH_CANDIDATES_REQUIRED")
    return {"status": "PASS", "receipts": len(manifest["receipts"]), "models": sorted(models)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index")
    print(verify(parser.parse_args().index))


if __name__ == "__main__":
    main()
