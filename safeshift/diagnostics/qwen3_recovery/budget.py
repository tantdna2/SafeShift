"""V4 admission plus explicit observation storage/file reserves."""
from ..hnlo_train.budget import admit, admit_gpu, RUN_RESERVE, GIB
from ..hnlo_train.budget import estimate as baseline_estimate


def estimate(count, staging_bytes):
    if count != 224:
        raise ValueError("RECOVERY224_ONLY")
    plan = baseline_estimate(count, staging_bytes)
    # 1 MiB primary diagnostic JSON + sidecars/seals; <=128 events/sample.
    extra_live = count * 2 * 2**20 + RUN_RESERVE
    extra_archive = extra_live + count * 300 * 2048
    return {**plan, "live_evidence_bytes": plan["live_evidence_bytes"] + extra_live,
        "archive_and_tar_headers_bytes": plan["archive_and_tar_headers_bytes"] + extra_archive,
        "output_required_bytes": plan["output_required_bytes"] + extra_live + extra_archive,
        "observation_primary_bytes_per_sample": 2**20,
        "observation_events_per_sample": 128,
        "files_per_sample_bound": plan["files_per_sample_bound"] + 300}
