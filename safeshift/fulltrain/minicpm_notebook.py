"""MiniCPM full-TRAIN notebook boundary; no caller flag can open the release.

Preparation is stdlib-only. Execution delegates to the existing supervised native
pipeline, whose public release fence is deliberately unchanged in this task.
"""
from pathlib import Path

from safeshift.candidates.source import ROOT, require, snapshot_stat
from safeshift.pilot.artifacts import read, sha, write, export, verify_archive
from safeshift.pilot.contract import digest, require_hash
from . import contract, preflight

KEY = "minicpm4"


def prepare(expected_source_sha256, repo, runtime_ref, *, work=None):
    """Observe kernel/source only, then seal honest readiness and Input contracts."""
    repo = Path(repo)
    require(digest(contract.source_manifest(repo)) == expected_source_sha256, "FINAL_SOURCE_MISMATCH")
    # Reuse its unique-directory/environment contract, but enrich the export
    # before sealing. Never modify an already sealed preparation directory.
    import uuid
    output = Path(work or Path.cwd() / "data/processed/minicpm_fulltrain") / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    report = contract.release_report(KEY)
    report.update(runtime_ref=runtime_ref, source_sha256=expected_source_sha256,
                  notebook_mode="EXECUTION_CANDIDATE_RELEASE_BLOCKED",
                  native_calls=0, weights_loaded=False, attempt_consumed=False,
                  owner_slot_created=False, production_ledger_written=False,
                  scientific_qualified=False, execution_caps=None,
                  final_source_live_verification="NOT_RUN")
    try:
        observed = preflight.environment_observation()
        report["levels"]["ENVIRONMENT_OBSERVED"] = "PASS"
        write(output / "environment.json", observed)
        write(output / "source_manifest.json", contract.source_manifest(repo))
        write(output / "native_contract.json", contract.descriptor(KEY))
        lock = read(repo / "configs/cpu_g2_g3/checkpoint_metadata_lock.json")[KEY]
        write(output / "checkpoint_contract.json", lock)
        write(output / "pipeline.json", {
            "entrypoint": "safeshift.fulltrain.minicpm_notebook.run_request",
            "release": "contract.authorize BEFORE request read; runtime.launch repeats gate",
            "stages": ["admit", "setup", "cpu", "gpu", "native"],
            "native": "runtime._worker -> runtime._native_factory -> minicpm_resampler_fp32.backend",
            "controller": "runtime._execute / NativeStore / pilot.runner.execute",
            "parser": "safeshift.pilot.contract.parse_label (strict C1, unchanged)",
            "hnlo": "LABEL_ONLY; evaluator=None; numeric HNLO forbidden",
            "history": "runtime.import_history (explicit ZIP SHA and all ancestors); runtime.recover",
            "resume": "only NOT_ATTEMPTED in fresh171-minicpm4-v1 with identical identity",
            "repair": "exact failed outcomes, diagnosis/cause/fix/regression and separate authority",
            "export": "immutable per-attempt raw/native/errors/checkpoints/accounting + ZIP/sidecar",
            "cross_vm_lock": "NONE; one operator, previous VM terminal, complete history required",
            "batch": "NO DEFAULT; explicit approved calls/time/resources required",
            "test_split": "CLOSED", "status": "BLOCKED"})
    finally:
        write(output / "release.json", report)
        archive = Path(str(output) + ".zip")
        export(output, archive)
        verify_archive(archive)
        require(read(Path(str(archive) + ".sha256.json"))["sha256"] == sha(archive), "EXPORT_SIDECAR")
    return output


def run_request(request_file, expected_request_sha256, *, repo=ROOT):
    """Future source-reviewed activation boundary, not a grant-file bypass.

    All model loading, image preprocessing, native generation/raw custody, C1,
    recovery and export bodies reside in the reviewed shared runtime. No second
    adapter/parser/loop is maintained in notebook cells. This version ALWAYS
    raises PermissionError before touching the request or any Input.
    """
    contract.authorize()
    require_hash(expected_request_sha256)
    path = Path(request_file)
    require(snapshot_stat(path).st_size <= 4 * 2**20, "BOUNDED_EXECUTION_REQUEST")
    require(sha(path) == expected_request_sha256, "EXECUTION_REQUEST_PIN")
    request = read(path)
    require(request["model_key"] == KEY, "MINICPM_ONLY_NOTEBOOK")
    from .admission import validate_request
    from .runtime import launch
    validate_request(request, repo)
    return launch(request, repo=repo)
