"""MiniCPM-only resource sizing: estimates are never measurements or grants."""
import math
import time

from safeshift.candidates.source import require


def validate_policy(policy, job_seconds):
    require(type(policy) is dict and set(policy) == {"export_seconds", "first_call_seconds", "safety_milli"}
        and all(type(n) is int and n > 0 for n in policy.values())
        and policy["safety_milli"] >= 1000 and policy["export_seconds"] + policy["first_call_seconds"] < job_seconds,
        "MINICPM_EXPLICIT_SIZING_RESERVES")
    return policy


def propose(grant, pending, reserved, provider, telemetry=None):
    """Use only same-source verified MiniCPM telemetry, otherwise an adaptive cap.

    No live latency/model-fit claim comes from the initial upper call ceiling.
    Native preflight/load/call/end-to-end timings refine the *next* proposal;
    the current job stops before the next call when its guarded time is low.
    """
    caps, policy = grant["caps"], grant["sizing"]
    validate_policy(policy, caps["job_seconds"])
    require(type(pending) is int and pending > 0, "MINICPM_PENDING_COUNT")
    require(reserved["jobs"] < caps["total_jobs"], "MINICPM_JOB_BUDGET_EXHAUSTED")
    quota = provider["quota"]
    seconds = min(caps["job_seconds"], (caps["total_gpu_seconds"] - reserved["gpu_seconds"]) // 2,
        (quota["total"] - quota["used"] - quota["reserved"]) // 2,
        int(grant["expires_unix"] - provider["observed_unix"] - grant["provider_max_age_seconds"]))
    calls = min(pending, caps["job_calls"], caps["total_calls"] - reserved["calls"])
    require(seconds > policy["export_seconds"] + policy["first_call_seconds"] and calls > 0,
        "MINICPM_TIME_QUOTA_OR_CALL_BUDGET_EXHAUSTED")
    status, overhead, per_call = "UNKNOWN_ADAPTIVE_WITHIN_APPROVED_CAPS", None, None
    if telemetry is not None:
        require(type(telemetry) is dict and set(telemetry) == {"source_sha256", "model_key", "overhead_seconds",
            "call_seconds", "provenance_sha256"} and telemetry["model_key"] == "minicpm4"
            and telemetry["source_sha256"] == grant["scope"]["source_sha256"], "MINICPM_NO_PEER_THROUGHPUT_TRANSFER")
        numbers = [telemetry["overhead_seconds"], *telemetry["call_seconds"]]
        require(type(telemetry["call_seconds"]) is list and all(type(n) in (int, float) and math.isfinite(n) and n > 0 for n in numbers),
            "MINICPM_MEASURED_TIMING_REQUIRED")
        from safeshift.pilot.contract import require_hash
        require_hash(telemetry["provenance_sha256"])
        overhead = math.ceil(telemetry["overhead_seconds"] * policy["safety_milli"] / 1000)
        per_call = max(policy["first_call_seconds"], math.ceil(max(telemetry["call_seconds"], default=0) * policy["safety_milli"] / 1000))
        calls = min(calls, max(0, (seconds - overhead - policy["export_seconds"]) // per_call))
        require(calls > 0, "MINICPM_MEASURED_ENVELOPE_CANNOT_FIT")
        status = "MEASURED_SAME_SOURCE_ESTIMATE_NOT_POPULATION_GUARANTEE" if telemetry["call_seconds"] else "MEASURED_OVERHEAD_ONLY_THROUGHPUT_UNKNOWN"
    return {"calls": calls, "seconds": seconds, "status": status, "overhead_bound_seconds": overhead,
        "per_call_estimate_seconds": per_call, "physical_gpus": 2, "worker_gpu": 0,
        "model_fit": "INTEGRATED_PREFLIGHT_REQUIRED", "throughput_source": "MINICPM_ONLY_OR_UNKNOWN"}


class CallBudget:
    def __init__(self, deadline, policy, *, clock=time.monotonic):
        self.deadline, self.policy, self.clock = deadline, policy, clock
        self.timings = []

    def can_start(self):
        reserve = self.policy["first_call_seconds"]
        if self.timings:
            reserve = max(reserve, math.ceil(max(self.timings) * self.policy["safety_milli"] / 1000))
        return self.clock() + reserve < self.deadline - self.policy["export_seconds"]

    def observed(self, seconds):
        require(type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0, "MINICPM_CALL_TIME_FINITE")
        self.timings.append(seconds)
