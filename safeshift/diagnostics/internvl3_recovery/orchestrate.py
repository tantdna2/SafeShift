"""Compose the existing durable pipeline with a single-model recovery contract."""

from ..one_click.orchestrate import Operations as OriginalOperations, run as original_run
from .contract import AUTHORITY, ORDER, authorize


class Operations(OriginalOperations):
    worker_module = "safeshift.diagnostics.internvl3_recovery.worker"

    def cache(self, model):
        if model != "internvl3":
            raise PermissionError("RECOVERY_INTERNVL3_ONLY")
        return "data/processed/internvl3-recovery/" + self.grant["attempt_id"] + "/cache/internvl3"


def run(repo, work, output, source, *, operations_factory=Operations):
    return original_run(repo, work, output, source, operations_factory=operations_factory,
                        order=ORDER, authority_path=AUTHORITY, authorizer=authorize,
                        result_schema="internvl3-recovery-probe-v1")
