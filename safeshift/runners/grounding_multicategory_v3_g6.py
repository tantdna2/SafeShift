"""G6 PaliGemma-only identity wrapper for the frozen synthetic v3 runtime.

The G5 runner remains available as historical code.  G6 changes execution
identity and authority scope only: it binds a new BASE/lock/plan and exposes
PaliGemma's predeclared run ID.  Scientific parser, geometry, prompt and
raw-before-parse behavior are delegated unchanged to the historical runtime.
"""

from contextlib import contextmanager
from pathlib import Path

from safeshift.runners import grounding_multicategory_v3 as _runtime


BASE = "069d780b6590a32a19cbe6e341ffa19cedbcd712"
ROOT = Path(__file__).resolve().parents[2]
PLAN = "configs/pre_freeze/grounding_interface_qualification_plan.v3.json"
MANIFEST = "configs/pre_freeze/external_grounding_interface_cases.v3.json"
LOCK = "configs/pre_freeze/grounding_interface_lock.v3.json"
RUNTIME_LOCK = "configs/pre_freeze/grounding_multicategory_runtime_lock.v3.json"
EXECUTION_PLAN = "configs/pre_freeze/grounding_multicategory_execution_plan.v2.json"
ENV_TEMPLATE = "configs/pre_freeze/grounding_multicategory_environment.v1.json"
RUNNER = "safeshift/runners/grounding_multicategory_v3_g6.py"
PARSER = "safeshift/protocol/grounding_multicategory_candidate.py"
RUN_ROOT = "data/processed/external_grounding_multicategory_v3/runs"
MODELS = {
    "paligemma": ("google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1"),
}
DECODING = dict(do_sample=False, num_beams=1, num_return_sequences=1, max_new_tokens=512)
PARSERS = {"paligemma": _runtime.parse_paligemma_multicategory}
RUN_IDS = {"paligemma": "g6-paligemma-v3-001"}


require = _runtime.require
encode = _runtime.encode
sha = _runtime.sha
text_hash = _runtime.text_hash
read_json = _runtime.read_json
git = _runtime.git
run_path = _runtime.run_path
write_bytes = _runtime.write_bytes
verified_read = _runtime.verified_read
validate_continuation = _runtime.validate_continuation
review_template = _runtime.review_template
verdict = _runtime.verdict
validate_result = _runtime.validate_result


@contextmanager
def _g6_profile():
    """Temporarily bind the historical implementation to the G6 contract."""
    names = ("BASE", "PLAN", "MANIFEST", "LOCK", "RUNTIME_LOCK", "EXECUTION_PLAN",
             "ENV_TEMPLATE", "RUNNER", "PARSER", "RUN_ROOT", "MODELS", "DECODING",
             "PARSERS", "RUN_IDS", "git")
    previous = {name: getattr(_runtime, name) for name in names}
    try:
        for name in names:
            setattr(_runtime, name, globals()[name])
        yield
    finally:
        for name, value in previous.items():
            setattr(_runtime, name, value)


def _model_only(model_key):
    require(model_key in MODELS, "G6_PALIGEMMA_ONLY")


def frozen(repo=ROOT):
    with _g6_profile():
        return _runtime.frozen(repo)


def inventory_snapshot(repo, model_key, snapshot_name):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.inventory_snapshot(repo, model_key, snapshot_name)


def execution_identity(repo):
    with _g6_profile():
        return _runtime.execution_identity(repo)


def inspect_environment(repo, model_key, snapshot_name):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.inspect_environment(repo, model_key, snapshot_name)


def preflight(repo, model_key, run_id, environment=None, authority=None, *, images=True):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.preflight(repo, model_key, run_id, environment, authority, images=images)


def validate_environment(environment, model_key):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.validate_environment(environment, model_key)


class NativeRuntime:
    """Proxy that keeps G6 identity active for direct runtime unit tests."""

    def __init__(self, repo, model_key, environment):
        _model_only(model_key)
        with _g6_profile():
            self._inner = _runtime.NativeRuntime(repo, model_key, environment)

    def load(self):
        with _g6_profile():
            return self._inner.load()

    def generate(self, image_bytes, text):
        with _g6_profile():
            return self._inner.generate(image_bytes, text)

    def __getattr__(self, name):
        return getattr(self._inner, name)


def persist_then_parse(directory, raw_bytes, metadata, model_key, labels):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.persist_then_parse(directory, raw_bytes, metadata, model_key, labels)


def run_calls(repo, model_key, run_id, environment, runtime, command, authority=None):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.run_calls(repo, model_key, run_id, environment, runtime, command, authority)


def execute(repo, model_key, run_id, environment, authority, command):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.execute(repo, model_key, run_id, environment, authority, command)


def finalize(repo, model_key, run_id, reviews):
    _model_only(model_key)
    with _g6_profile():
        return _runtime.finalize(repo, model_key, run_id, reviews)
