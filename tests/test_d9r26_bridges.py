"""No models: capture native lifecycle and exercise durable synthetic artifacts."""

from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import dataclass, replace
from importlib import import_module
import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.runners import p2_bridge as b, p2_harness as h, p2_preflight as pre
from safeshift.runners.contracts import GenerationFailure, Task, Participation
from safeshift.data import p2_execution as d
from safeshift.protocol import p2_evaluation as ev
from safeshift.protocol.classification_policy import ROOT, load_policy, render_prompt
from safeshift.protocol.reporting import build_report, render_json
from safeshift.protocol.schema import HAZARDS
from tests.test_d9r23_classification_contract import native
from tests.test_d9r24_metrics import cls


class FakeNative:
    def __init__(self, model, outputs):
        actual = b._runner_class(model)
        self.identity, self.version = actual.identity, actual.version
        self.outputs, self.events, self.requests = iter(outputs), [], []

    def initialize(self, context):
        self.events.append(("initialize", context))

    def load(self, context):
        self.events.append(("load", context))

    def prepare_input(self, request, context):
        self.events.append(("prepare", context))
        self.requests.append(request)
        return request

    def generate_raw(self, prepared, context):
        self.events.append(("generate", context))
        value = next(self.outputs)
        if isinstance(value, GenerationFailure):
            raise value
        return value

    def close(self):
        self.events.append(("close", None))


@contextmanager
def fake_lifecycle(model, outputs):
    fake = FakeNative(model, outputs)
    entry = load_policy(qwen3_runtime=model == "qwen3")["classification"][model]
    observation = {"software_versions": entry["software_versions"], "hardware": entry["hardware_contract"]}
    with ExitStack() as stack:
        stack.enter_context(patch.object(b, "require_production_context"))
        stack.enter_context(patch.object(b, "_construct", return_value=fake))
        stack.enter_context(patch.object(b, "_verify_qwen_snapshot"))
        stack.enter_context(patch.object(b, "_loaded_state"))
        stack.enter_context(patch.object(pre, "runtime_observation", return_value=deepcopy(observation)))
        stack.enter_context(patch.object(socket.socket, "connect", side_effect=AssertionError("NO_NETWORK")))
        yield fake, h.resolve_production_backend(model)


class BridgeTests(unittest.TestCase):
    def test_real_lightweight_construction_uses_exact_native_classes_without_load(self):
        for model, entry in load_policy(qwen3_runtime=True)["classification"].items():
            with self.subTest(model=model):
                observation = {"software_versions": deepcopy(entry["software_versions"])}
                runner = b._construct(model, ROOT, entry, observation)
                self.assertIs(type(runner), b._runner_class(model))
                b._check_identity(runner, model, entry)
                if model == "moondream":
                    self.assertEqual(runner.model_snapshot.name, entry["immutable_revision"])
                    self.assertEqual(runner.tokenizer_snapshot.name, entry["tokenizer_revision"])
                if model in ("qwen3", "qwen2_5"):
                    @dataclass
                    class MetadataOnly:
                        software_versions: dict
                    module = import_module(b.REGISTRY[model][0])
                    with patch.object(module, "_native_backend", return_value=MetadataOnly({"torch": entry["software_versions"]["torch"]})):
                        measured = runner._backend_factory()
                        self.assertEqual(measured.software_versions, observation["software_versions"])
                    with patch.object(module, "_native_backend", return_value=MetadataOnly({"torch": "wrong"})):
                        with self.assertRaisesRegex(ValueError, "NATIVE_SOFTWARE_MISMATCH"):
                            runner._backend_factory()

    def test_runtime_observation_reuses_native_probes_with_fake_torch(self):
        from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
        for model, entry in load_policy(qwen3_runtime=True)["classification"].items():
            torch = SimpleNamespace(version=SimpleNamespace(cuda=entry["hardware_contract"]["cuda_runtime"]))
            with ExitStack() as stack:
                stack.enter_context(patch.dict("os.environ", OFFLINE_ENV))
                if model == "qwen3":
                    from safeshift.runners.qwen3_placement import ALLOCATOR_NAME, ALLOCATOR_VALUE
                    stack.enter_context(patch.dict("os.environ", {ALLOCATOR_NAME: ALLOCATOR_VALUE}))
                stack.enter_context(patch.dict(sys.modules, {"torch": torch}))
                stack.enter_context(patch.object(pre, "software_observation", return_value=entry["software_versions"]))
                stack.enter_context(patch.object(pre.platform, "system", return_value="Linux"))
                stack.enter_context(patch.object(pre.platform, "machine", return_value="x86_64"))
                if model == "qwen3":
                    mod = import_module("scripts.w2_qwen_kaggle_smoke")
                    observed = {"cuda_available": True, "gpu_count": 2,
                                "nvidia_smi": [{"name": "Tesla T4"}] * 2,
                                "gpus": [{"name": "Tesla T4", "compute_capability": [7, 5]}] * 2}
                    probe = stack.enter_context(patch.object(mod, "probe_hardware", return_value=observed))
                elif model in ("qwen2_5", "internvl3"):
                    mod = import_module("scripts.w2_qwen2_5_t4_smoke" if model == "qwen2_5" else "safeshift.runners.internvl3")
                    probe = stack.enter_context(patch.object(mod, "probe_hardware", return_value={"visible_gpu_count": 1, "compute_capability": [7, 5]}))
                else:
                    torch.cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 1,
                        get_device_properties=lambda _: SimpleNamespace(name="Tesla T4", major=7, minor=5, total_memory=16 * 1024**3))
                    mod = import_module("safeshift.runners.moondream2")
                    probe = stack.enter_context(patch.object(mod, "validate_device", wraps=mod.validate_device))
                self.assertEqual(pre.runtime_observation(model)["hardware"], entry["hardware_contract"])
                probe.assert_called_once()
                torch.version.cuda = "wrong"
                with self.assertRaisesRegex(ValueError, "HARDWARE_CONTRACT"):
                    pre.runtime_observation(model)

    def test_exact_modules_and_wrong_runner_substitution_rejected(self):
        expected = {"qwen3": "Qwen3VLRunner", "qwen2_5": "Qwen2_5VLRunner",
                    "internvl3": "InternVL3Runner", "moondream": "Moondream2Runner"}
        self.assertEqual(set(b.REGISTRY), set(expected))
        models = list(expected)
        for i, model in enumerate(models):
            module, name, version = b.REGISTRY[model]
            self.assertEqual(name, expected[model])
            self.assertEqual(b._runner_class(model), getattr(import_module(module), name))
            wrong = b._runner_class(models[(i + 1) % 4])
            with patch.object(import_module(module), name, wrong):
                with self.assertRaisesRegex(ValueError, "BINDING_MISMATCH"):
                    h.resolve_production_backend(model)
        with self.assertRaisesRegex(ValueError, "NOT_PARTICIPATING"):
            h.resolve_production_backend("paligemma")

    def test_exact_context_request_lifecycle_and_opaque_bytes_all_models(self):
        image, raw = h.synthetic_image(), b"opaque native bytes\x00\xff"
        for model in b.REGISTRY:
            with self.subTest(model=model), fake_lifecycle(model, [raw, raw]) as (fake, bridge):
                run = b.RunIdentity("run", "a" * 40, "INSPECSAFE")
                bridge.load(bridge.entry, operational=run)
                for sid in ("sample-A", "sample-B"):
                    call = b.CallIdentity(sid, b.call_identity(sid), d.sha(image))
                    self.assertIs(bridge.generate(image_bytes=image, prompt=render_prompt(model), operational=call), raw)
                    ctx = fake.events[-1][1]
                    self.assertEqual((ctx.run_id, ctx.call_id, ctx.git_commit_sha, ctx.source_kind),
                                     (run.run_id, call.call_id, run.git_commit, "INSPECSAFE"))
                    for name in ("decoding", "preprocessing", "precision", "quantization", "device", "software_versions", "seed"):
                        self.assertEqual(getattr(ctx, name), bridge.entry[name], name)
                    self.assertEqual(ctx.roles.classification, Participation.PARTICIPATING)
                    self.assertEqual(ctx.roles.grounding, Participation.NOT_PARTICIPATING)
                    request = fake.requests[-1]
                    self.assertEqual((request.task, request.sample_id, request.input_id, request.input_bytes,
                                      request.prompt_id, request.prompt),
                                     (Task.CLASSIFICATION, sid, "sha256:" + d.sha(image), image,
                                      bridge.entry["prompt_version"], render_prompt(model)))
                    self.assertNotIn(sid, request.prompt)
                    self.assertNotIn(call.call_id, request.prompt)
                    self.assertEqual(set(ctx.input_provenance), {"sample_id", "input_id", "image_sha256", "model_key"})
                with self.assertRaisesRegex(ValueError, "EXACT_IMAGE_PROMPT_CALL"):
                    bridge.generate(image_bytes=image, prompt=render_prompt(model), operational=call)
                with self.assertRaisesRegex(ValueError, "ONE_EXACT_BRIDGE"):
                    bridge.load(bridge.entry, operational=run)
                self.assertEqual([x[0] for x in fake.events], ["initialize", "load", "prepare", "generate", "prepare", "generate"])
                self.assertEqual(bridge.observe()["hardware"], bridge.entry["hardware_contract"])
                bridge.close()

    def test_failure_is_same_exception_partial_raw_and_no_retry(self):
        failure = GenerationFailure(partial_raw=b"partial\x00")
        for model in b.REGISTRY:
            with self.subTest(model=model), fake_lifecycle(model, [failure]) as (fake, bridge):
                bridge.load(bridge.entry, operational=b.RunIdentity("r", "a" * 40, "INSPECSAFE"))
                kwargs = dict(image_bytes=h.synthetic_image(), prompt=render_prompt(model),
                              operational=b.CallIdentity("s", b.call_identity("s"), d.sha(h.synthetic_image())))
                with self.assertRaises(GenerationFailure) as caught:
                    bridge.generate(**kwargs)
                self.assertIs(caught.exception, failure)
                self.assertEqual(caught.exception.partial_raw, b"partial\x00")
                with self.assertRaisesRegex(RuntimeError, "NO_RETRY"):
                    bridge.generate(**kwargs)
                self.assertEqual(sum(x[0] == "generate" for x in fake.events), 1)
                bridge.close()

    def test_identity_revision_and_execution_condition_rejected(self):
        with fake_lifecycle("qwen3", []) as (fake, bridge):
            fake.identity = replace(fake.identity, immutable_revision="b" * 40)
            with self.assertRaisesRegex(ValueError, "MODEL_IDENTITY"):
                bridge.load(bridge.entry, operational=b.RunIdentity("r", "a" * 40, "INSPECSAFE"))
            self.assertEqual(fake.events, [("close", None)])
        bridge = h.resolve_production_backend("qwen3")
        with self.assertRaisesRegex(ValueError, "ONE_EXACT_BRIDGE"):
            bridge.load({**bridge.entry, "seed": 42}, operational=b.RunIdentity("r", "a" * 40, "INSPECSAFE"))

    def test_direct_bridge_current_guard_before_any_runtime_observation_or_load(self):
        for model in b.REGISTRY:
            with self.subTest(model=model), patch.object(pre, "runtime_observation") as observation, patch.object(b, "_construct") as construct:
                bridge = h.resolve_production_backend(model)
                with self.assertRaisesRegex(PermissionError, h.BLOCK):
                    bridge.load(bridge.entry, operational=b.RunIdentity("r", "a" * 40, "INSPECSAFE"))
                observation.assert_not_called()
                construct.assert_not_called()

    def test_no_semantic_parse_persistence_or_execute_call_in_bridge(self):
        source = inspect.getsource(b)
        for token in ("execute_call(", "parse_stored(", "persist_native(", ".adapt(", "write_bytes(", ".generate(", ".query("):
            self.assertNotIn(token, source)

    def test_native_guard_extensions_accept_only_authorized_classification(self):
        from safeshift.runners.internvl3 import InternVL3Runner
        from safeshift.runners.moondream2 import Moondream2Runner
        from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
        for model, runner in (("internvl3", InternVL3Runner()), ("moondream", Moondream2Runner("unused", "unused"))):
            ctx = b.context_for(model, load_policy()["classification"][model], b.RunIdentity("r", "a" * 40, "INSPECSAFE"))
            with patch.dict("os.environ", OFFLINE_ENV), patch.object(h, "authorize_production", return_value=("a" * 40, {})):
                runner._condition(ctx)  # no backend initialization
                request = b.Request(Task.GROUNDING, "s", "id", b"bytes", "p", "prompt")
                with self.assertRaisesRegex(ValueError, "CLASSIFICATION_ONLY"):
                    runner.prepare_input(request, ctx)

    def test_import_resolve_without_heavy_packages(self):
        code = '''import builtins
old = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub'}:
        raise AssertionError('NO_MODEL_IMPORT')
    return old(name, *args, **kwargs)
builtins.__import__ = guard
from safeshift.runners.p2_harness import resolve_production_backend, MODELS
for model in MODELS:
    resolve_production_backend(model)
'''
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)


class RehearsalTests(unittest.TestCase):
    def test_scripted_and_fake_native_full_pipeline_same_deterministic_report(self):
        # Predictions defined without consulting evaluation labels.
        votes = [(1, 1, 1, 1), (4, 4, 4, 4), (2, 2, 2, 3), (1, 1, 4, 4),
                 (1, 2, 3, 4), (None, 1, 1, 1), (3, 3, 3, 3), (2, 2, 1, 3)]
        ids = [f"synthetic-{i}" for i in range(len(votes))]
        reports = []
        for mode in ("scripted", "native"):
            with TemporaryDirectory() as out:
                tables = []
                for mi, model in enumerate(h.MODELS):
                    run_id = "fake-" + model
                    raws = [native(model, "invalid" if v[mi] is None else json.dumps({"safety_level": f"Level0{v[mi]}"})) for v in votes]
                    if model == "internvl3":
                        raws = [d.json_bytes({**json.loads(raw), "run_id": run_id, "call_id": b.call_identity(sid)}) for sid, raw in zip(ids, raws)]
                    if mode == "scripted":
                        root = h.rehearse(model=model, run_id=run_id, sample_ids=ids,
                                          backend=h.ScriptedBackend(raws), artifact_repo=Path(out))
                    else:
                        image = h.synthetic_image()
                        rows = d.execution_records({"sample_id": sid, "image_locator": "generated.png", "image_sha256": d.sha(image)} for sid in ids)
                        with fake_lifecycle(model, raws) as (fake, bridge):
                            root = h._execute(repo=ROOT, artifact_repo=Path(out), model=model, entry=bridge.entry,
                                run_id=run_id, rows=rows, source_hash=d.sha(d.json_bytes(rows)),
                                dataset_fingerprint="SYNTHETIC_NOT_INSPECSAFE", source="SYNTHETIC",
                                image_reader=lambda row: image, shard_count=1, shard_index=0,
                                commit=h._git(ROOT, "rev-parse", "HEAD").decode().strip(), backend_factory=lambda: bridge)
                        self.assertEqual(len(fake.requests), len(ids))
                    table = ev.export_predictions(root)
                    self.assertEqual([r["raw_sha256"] for r in table["rows"]], [d.sha(x) for x in raws])
                    self.assertFalse({"true_safety_level", "hazard_memberships", "folder_domain"} & set(table["rows"][0]))
                    tables.append(table)
                aligned = ev.align_four_models(tables)
                self.assertIsNone(aligned[5]["predictions"]["qwen3"])
                # The first GT-bearing object is created only after inference/export/alignment.
                gt = [{"sample_id": sid, "true_safety_level": f"Level0{[1, 2, 2, 1, 4, 1, 1, 3][i]}",
                       "folder_domain": ("power", "metallurgy")[i % 2], "split": "test", "point_id": f"point-{i}",
                       "hazard_memberships": list(HAZARDS[:2]) if i != 4 else []} for i, sid in enumerate(ids)]
                joined = ev.join_evaluation(tables, gt)
                classification = [cls(s.sample_id, s.true_safety_level, s.predictions["qwen3"], s.folder_domain,
                                      s.hazard_memberships, s.point_id) for s in joined.samples]
                report = build_report(classification_samples=classification, disagreement_samples=joined.samples)
                self.assertEqual(report["cohort_parse_availability"]["joint_valid_4_n"], 7)
                self.assertNotEqual(report["RQ1"].get("status"), "NO_INPUT")
                self.assertEqual(render_json(report), render_json(build_report(
                    classification_samples=reversed(classification), disagreement_samples=reversed(joined.samples))))
                reports.append(render_json(report))
        self.assertEqual(*reports)


if __name__ == "__main__":
    unittest.main()
