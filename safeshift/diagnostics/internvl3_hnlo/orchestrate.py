"""Reuse durable one-click state machine with software -> CUDA -> weights order."""
from ..one_click.orchestrate import Operations as OriginalOperations, run as original_run, child_environment
from ..one_click.provision import build_environment, invoke
from ..one_click.artifacts import write
from .contract import AUTHORITY, ORDER, authorize
from .resources import require_resources


class Operations(OriginalOperations):
    worker_module = "safeshift.diagnostics.internvl3_hnlo.worker"

    def preflight(self):
        row = super().preflight()
        return {**row, "full_vector_budget": require_resources(self.work)}

    def cache(self, model):
        if model != "internvl3":
            raise PermissionError("HNLO_PROBE_INTERNVL3_ONLY")
        return "data/processed/internvl3-hnlo/" + self.grant["attempt_id"] + "/cache/internvl3"

    def prepare(self, model):
        self.cache(model)
        evidence = self.evidence / model
        evidence.mkdir()
        self.pythons[model] = build_environment(model, self.repo, self.repo.parent / "runtime" / model, evidence / "build")
        return {"status": "SOFTWARE_ONLY_CHECKPOINT_NOT_DOWNLOADED"}

    def worker(self, mode, model):
        result = super().worker(mode, model)
        if mode == "inspect" and result["result"] == "ENVIRONMENT_VALID" and not result["common_fatal"]:
            evidence = self.evidence / model
            # This CUDA-inspection child has exited. Checkpoint bytes are prepared
            # online by a CPU-only child, before the single offline model probe.
            env = child_environment(model, self.repo, self.cache(model), offline=False, cpu=True)
            invoke([self.pythons[model], "-m", "safeshift.diagnostics.one_click.provision",
                    "--model", model, "--cache", self.cache(model), "--evidence", evidence],
                   self.repo, evidence / "model-provision.log", env=env)
            write(evidence / "checkpoint-after-cuda.json", {"cuda_inspect": "ENVIRONMENT_VALID", "loads_so_far": 0})
        return result


def run(repo, work, output, source, *, operations_factory=Operations):
    return original_run(repo, work, output, source, operations_factory=operations_factory,
                        order=ORDER, authority_path=AUTHORITY, authorizer=authorize,
                        result_schema="internvl3-hnlo-gpu-probe-v1")
