"""Only generated temporary data and scripted native envelopes; no real inference."""

from copy import deepcopy
import ast
import csv
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from safeshift.data import p2_execution as data
from safeshift.data.manifest import FIELDS
from safeshift.protocol import p2_evaluation as evaluation
from safeshift.protocol.d9r24_metrics import rq3_metrics
from safeshift.protocol.classification_policy import QWEN3_AMENDMENT_PATH
from safeshift.runners import p2_harness as h
from safeshift.runners.contracts import GenerationFailure
from tests.test_d9r23_classification_contract import native

BASE = "ac8825e7d0e21e437fda044cadc3aa8b4fc8f508"
ROOT = Path(__file__).resolve().parents[1]


class HarnessTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        self.socket = patch.object(socket.socket, "connect", side_effect=AssertionError("NO_NETWORK"))
        self.socket.start()
        self.addCleanup(self.socket.stop)
        for name in (h.CONTRACT_PATH, *h.contract()["identity_sha256"], QWEN3_AMENDMENT_PATH):
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.counter = 0

    def run_fake(self, outputs=None, *, model="moondream", ids=("b", "a"), run_id=None, **kwargs):
        self.counter += 1
        run_id = run_id or f"run-{self.counter}"
        if outputs is None:
            outputs = [native(model, '{"safety_level":"Level01"}') for _ in ids]
            if model == "internvl3":
                outputs = [data.json_bytes({**json.loads(x), "run_id": run_id, "call_id": h.call_identity(sid)})
                           for sid, x in zip(sorted(ids), outputs)]
        backend = h.ScriptedBackend(outputs)
        path = h.rehearse(model=model, run_id=run_id, sample_ids=ids, backend=backend,
                          repo=ROOT, artifact_repo=self.repo, **kwargs)
        return path, backend

    def read(self, path):
        return json.loads(path.read_bytes())

    def test_current_production_guard_precedes_all_reads_and_load(self):
        with patch.object(h, "resolve_production_backend") as resolver, \
                patch.object(h, "verify_dataset", side_effect=AssertionError("NO_DATASET_READ")) as verify:
            with self.assertRaisesRegex(PermissionError, h.BLOCK):
                h.production_run(model="moondream", run_id="denied", dataset_root="InspecSafe-V1",
                                 manifest_path="missing", provenance_path="missing", repo=self.repo)
            verify.assert_not_called()
        resolver.assert_not_called()

    def test_no_force_environment_or_caller_authority_bypass(self):
        with patch.dict("os.environ", {"SAFESHIFT_FORCE": "1", "INSPECSAFE_AUTHORIZED": "true"}):
            with self.assertRaisesRegex(PermissionError, h.BLOCK):
                h.authorize_production(self.repo)
        params = inspect.signature(h.production_run).parameters
        self.assertFalse({"force", "unsafe", "ignore_freeze", "skip_authorization", "authority"} & set(params))
        with self.assertRaises(TypeError):
            h.authorize_production(self.repo, force=True)

    def test_public_production_has_no_backend_injection(self):
        params = inspect.signature(h.production_run).parameters
        self.assertEqual(set(params), {"model", "run_id", "dataset_root", "manifest_path",
                         "provenance_path", "shard_count", "shard_index", "repo", "rerun_of"})
        for name in ("backend_factory", "backend", "factory", "runner_factory", "model_factory", "generate_callback"):
            with self.subTest(name=name), self.assertRaises(TypeError):
                h.production_run(model="moondream", run_id="denied", dataset_root="missing",
                                 manifest_path="missing", provenance_path="missing", **{name: Mock()})

    def test_exact_internal_registry_and_source_bound_resolver(self):
        c = h.contract()
        self.assertEqual(tuple(h._PRODUCTION_BACKENDS), h.MODELS)
        self.assertEqual({k: list(v) for k, v in h._PRODUCTION_BACKENDS.items()}, c["production_backend_registry"])
        self.assertEqual(h.PRODUCTION_BACKEND_REGISTRY_VERSION, c["production_backend_registry_version"])
        self.assertEqual(c["caller_backend_injection"], "FORBIDDEN")
        self.assertEqual(c["production_backend_binding"], "IMPLEMENTED_SOURCE_BACKED_FREEZE_CANDIDATE")
        for model in h.MODELS:
            with self.subTest(model=model):
                self.assertEqual(h.resolve_production_backend(model).model, model)
        for model in ("paligemma", "ovis", "kosmos", "plamo", "smolvlm2"):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "CLASSIFICATION_NOT_PARTICIPATING"):
                h.resolve_production_backend(model)
        with self.assertRaises(TypeError):
            h._PRODUCTION_BACKENDS["moondream"] = Mock()

    def test_production_auth_dataset_shard_attempt_before_internal_resolution(self):
        rows = [{"sample_id": "a", "image_locator": "generated.png", "image_sha256": data.sha(h.synthetic_image())}]
        calls = []
        def resolve(model, *, repo):
            calls.append("resolve")
            raise PermissionError("TEST_RESOLUTION_BOUNDARY")
        with patch.object(h, "authorize_production", side_effect=lambda repo: (calls.append("auth") or (BASE, {}))), \
                patch.object(h, "verify_dataset", side_effect=lambda *args: (calls.append("dataset") or (rows, "hash"))), \
                patch.object(h, "resolve_production_backend", side_effect=resolve) as resolver:
            args = dict(model="moondream", run_id="pending", repo=self.repo, dataset_root="unused",
                        manifest_path="unused", provenance_path="unused")
            with self.assertRaisesRegex(ValueError, "INVALID_SHARD"):
                h.production_run(**args, shard_count=0)
            resolver.assert_not_called()
            calls.clear()
            with self.assertRaisesRegex(PermissionError, "TEST_RESOLUTION_BOUNDARY"):
                h.production_run(**args)
            self.assertEqual(calls, ["auth", "dataset", "resolve"])
            self.assertFalse(h._run_path(self.repo, "moondream", "pending").exists())
            h._run_path(self.repo, "moondream", "existing").mkdir(parents=True)
            resolver.reset_mock()
            with self.assertRaisesRegex(FileExistsError, "EXISTING_RUN"):
                h.production_run(**{**args, "run_id": "existing"})
            resolver.assert_not_called()

    def test_rehearsal_source_commit_independent_of_artifact_root_and_cwd(self):
        # Real temporary Git source A, separate from this checkout and outputs.
        # It holds the declared code/config source, not merely an output folder.
        source_file = self.repo / "safeshift/runners/p2_harness.py"
        source_file.parent.mkdir(parents=True)
        shutil.copyfile(ROOT / "safeshift/runners/p2_harness.py", source_file)
        def git(*args):
            return subprocess.check_output(["git", *args], cwd=self.repo, stderr=subprocess.DEVNULL)
        git("init")
        git("add", ".")
        git("-c", "user.name=Synthetic Test", "-c", "user.email=synthetic@example.invalid",
            "-c", "commit.gpgsign=false", "commit", "-m", "synthetic source A")
        commit_a = git("rev-parse", "HEAD").decode().strip()
        self.assertNotEqual(commit_a, h._git(ROOT, "rev-parse", "HEAD").decode().strip())
        with TemporaryDirectory() as out_a, TemporaryDirectory() as out_b:
            old_cwd = Path.cwd()
            try:
                os.chdir(out_b)
                for directory in (out_a, out_b):
                    root = h.rehearse(model="moondream", run_id="same", sample_ids=("s",),
                                      backend=h.ScriptedBackend([native("moondream", '{"safety_level":"Level01"}')]),
                                      repo=self.repo, artifact_repo=Path(directory))
                    self.assertEqual(self.read(root / "run_manifest.json")["git_commit"], commit_a)
                    meta = self.read(next((root / "calls").glob("*/metadata.json")))
                    self.assertEqual(meta["git_commit"], commit_a)
                    self.assertEqual(meta["source_kind"], "SYNTHETIC")
            finally:
                os.chdir(old_cwd)

    def test_rehearsal_default_source_and_non_git_source_rejection(self):
        root = h.rehearse(model="moondream", run_id="default-source", sample_ids=("s",),
                          backend=h.ScriptedBackend([b"invalid"]), artifact_repo=self.repo)
        self.assertEqual(self.read(root / "run_manifest.json")["git_commit"],
                         h._git(ROOT, "rev-parse", "HEAD").decode().strip())
        with self.assertRaises(subprocess.CalledProcessError):
            h.rehearse(model="moondream", run_id="not-source", sample_ids=("s",),
                       backend=h.ScriptedBackend([]), repo=self.repo)

    def test_forged_uncommitted_freeze_cannot_authorize(self):
        c = h.contract(self.repo)
        c.update(protocol_freeze="FROZEN", inspecsafe_inference_authorized=True)
        (self.repo / h.CONTRACT_PATH).write_bytes(data.json_bytes(c))
        path = self.repo / c["freeze_manifest_path"]
        path.parent.mkdir(parents=True)
        path.write_text('{"status":"FROZEN","inspecsafe_inference_authorized":true}')
        with self.assertRaisesRegex(PermissionError, h.BLOCK):
            h.authorize_production(self.repo)

    def test_pinned_contract_hash_mismatch(self):
        (self.repo / h.POLICY_PATH).write_bytes((self.repo / h.POLICY_PATH).read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            h.registry(self.repo)

    def test_future_authority_requires_committed_ancestor_and_exact_hashes(self):
        c = h.contract(self.repo)
        c.update(protocol_freeze="FROZEN", inspecsafe_inference_authorized=True)
        freeze = {"protocol_freeze_commit_sha": "a" * 40, "status": "FROZEN",
                  "schema_version": "p2-execution-authority-v1",
                  "implementation_base_sha": h.IMPLEMENTATION_BASE_SHA,
                  "expected_pre_merge_main_sha": h.IMPLEMENTATION_BASE_SHA,
                  "freeze_candidate_path": c["freeze_candidate_path"],
                  "freeze_candidate_sha256": c["freeze_candidate_sha256"], "reruns": [],
                  "inspecsafe_inference_authorized": True, "authority": "RESEARCH_LEAD",
                  "identity_sha256": c["identity_sha256"], "dataset_fingerprint": data.FINGERPRINT,
                  "sample_count": 5013, "protocol_id": "P2"}
        calls = []
        def git(repo, *args):
            calls.append(args)
            if args == ("ls-tree", "--name-only", "HEAD", "--", "configs/frozen/p2_execution_authority.v3.json"):
                return b""  # This fixture models the historical v1 release.
            if args == ("rev-parse", "HEAD"):
                return b"b" * 40
            if args == ("rev-list", "--parents", "-n", "1", "b" * 40):
                return ("b" * 40 + " " + h.IMPLEMENTATION_BASE_SHA + " " + "d" * 40).encode()
            if args == ("rev-list", "--parents", "-n", "1", "d" * 40):
                return ("d" * 40 + " " + "a" * 40).encode()
            if args == ("rev-parse", "a" * 40 + "^"):
                return h.IMPLEMENTATION_BASE_SHA.encode()
            if args[0] == "rev-parse" and args[1].endswith("^{tree}"):
                return b"e" * 40
            if args[0] == "diff":
                return (c["freeze_manifest_path"] + "\n").encode()
            if args[0] in ("status", "merge-base"):
                return b""
            if args in (("show", "b" * 40 + ":" + c["freeze_manifest_path"]),
                        ("show", "d" * 40 + ":" + c["freeze_manifest_path"])):
                return data.json_bytes(freeze)
            if args == ("show", "a" * 40 + ":" + c["freeze_candidate_path"]):
                return (ROOT / c["freeze_candidate_path"]).read_bytes().replace(b"\r\n", b"\n")
            if args[0] == "show" and args[1].startswith("a" * 40 + ":"):
                return (self.repo / args[1][41:]).read_bytes().replace(b"\r\n", b"\n")
            raise AssertionError(args)
        with patch.object(h, "contract", return_value=c), patch.object(h, "_git", side_effect=git):
            self.assertEqual(h.authorize_production(self.repo)[0], "b" * 40)
            self.assertIn(("merge-base", "--is-ancestor", "a" * 40, "b" * 40), calls)
            self.assertIn(("diff", "--name-only", "a" * 40, "b" * 40), calls)
            for key, invalid in (("status", "PENDING"), ("protocol_freeze_commit_sha", "PENDING"),
                                 ("inspecsafe_inference_authorized", False), ("sample_count", 1),
                                 ("identity_sha256", {}), ("dataset_fingerprint", "wrong")):
                old = freeze[key]
                freeze[key] = invalid
                with self.subTest(key=key), self.assertRaisesRegex(PermissionError, h.BLOCK):
                    h.authorize_production(self.repo)
                freeze[key] = old
        def changed_code(repo, *args):
            return b"safeshift/runners/p2_harness.py\n" if args[0] == "diff" else git(repo, *args)
        with patch.object(h, "contract", return_value=c), patch.object(h, "_git", side_effect=changed_code):
            with self.assertRaisesRegex(PermissionError, h.BLOCK):
                h.authorize_production(self.repo)
        with patch.object(h, "contract", return_value=c), patch.object(h, "_git", side_effect=subprocess.CalledProcessError(1, "git")):
            with self.assertRaisesRegex(PermissionError, h.BLOCK):
                h.authorize_production(self.repo)

    def test_registry_exact_and_nonparticipants_rejected(self):
        self.assertEqual(tuple(h.registry(self.repo)), ("qwen3", "qwen2_5", "internvl3", "moondream"))
        for model in ("paligemma", "ovis", "kosmos", "plamo", "smolvlm2"):
            with self.subTest(model=model), self.assertRaisesRegex(ValueError, "CLASSIFICATION_NOT_PARTICIPATING"):
                self.run_fake(model=model, outputs=[])

    def test_all_four_native_adapters_match_d9r23(self):
        for model in h.MODELS:
            with self.subTest(model=model):
                path, backend = self.run_fake(model=model)
                table = evaluation.export_predictions(path, repo=self.repo)
                self.assertEqual([r["safety_level"] for r in table["rows"]], ["Level01", "Level01"])
                self.assertEqual(backend.calls, 2)

    def test_payload_only_image_bytes_and_exact_prompt(self):
        seen = []
        original = h.ScriptedBackend.generate
        def capture(backend, **kwargs):
            seen.append(kwargs)
            return original(backend, **kwargs)
        with patch.object(h.ScriptedBackend, "generate", capture):
            path, _ = self.run_fake()
        for payload in seen:
            self.assertEqual(set(payload), {"image_bytes", "prompt"})
            self.assertEqual(payload["image_bytes"], h.synthetic_image())
            self.assertEqual(data.sha(payload["prompt"].encode()), h.PROMPT_SHA256)
        for row in self.read(path / "execution_manifest.json"):
            self.assertEqual(set(row), data.EXECUTION_FIELDS)

    def test_execution_gt_hazard_and_metadata_injection_rejected(self):
        row = {"sample_id": "s", "image_locator": "generated.png", "image_sha256": "0" * 64}
        for name in ("true_safety_level", "safety_level", "hazard_atoms", "hazard_group", "folder_domain",
                     "annotation_polygon", "d6_census", "other_prediction", "correctness"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "LABEL_FREE"):
                data.execution_records([{**row, name: "injection"}])
        with self.assertRaises(TypeError):
            h.ScriptedBackend([]).generate(image_bytes=b"", prompt="", true_safety_level="Level01")

    def test_synthetic_entry_has_no_image_path_or_arbitrary_backend(self):
        with self.assertRaisesRegex(TypeError, "BUILTIN_SCRIPTED"):
            h.rehearse(model="qwen3", run_id="r", sample_ids=["s"], backend=Mock(), repo=self.repo)
        self.assertNotIn("dataset_root", inspect.signature(h.rehearse).parameters)
        with self.assertRaises(TypeError):
            h.ScriptedBackend([lambda: None])

    def test_raw_durable_before_parser_and_exact_bytes(self):
        raw = native("moondream", '{"safety_level":"Level02"}')
        seen = []
        original = h.parse_stored
        def parser(directory, receipt, *args):
            self.assertEqual((directory / "response.raw").read_bytes(), raw)
            self.assertEqual(h.verified_raw(directory, receipt), raw)
            seen.append(receipt)
            return original(directory, receipt, *args)
        with patch.object(h, "parse_stored", parser):
            path, _ = self.run_fake([raw.decode()], ids=("s",))
        self.assertEqual(len(seen), 1)
        table = evaluation.export_predictions(path, repo=self.repo)
        self.assertEqual(table["rows"][0]["raw_sha256"], data.sha(raw))

    def test_raw_write_failure_blocks_parser(self):
        with patch.object(h, "persist_native", side_effect=OSError("secret not recorded")), patch.object(h, "parse_stored") as parser:
            path, backend = self.run_fake()
        parser.assert_not_called()
        self.assertEqual(backend.calls, 1)
        status = self.read(path / "run_status.json")
        self.assertEqual(status["status"], "FAILED")
        self.assertEqual(status["samples"], {"a": "FAILED", "b": "NOT_ATTEMPTED"})
        self.assertNotIn("secret", (path / "run_status.json").read_text())

    def test_raw_tamper_blocks_parse(self):
        original = h.verified_raw
        def tamper(directory, receipt):
            (directory / "response.raw").write_bytes(b"tampered")
            return original(directory, receipt)
        with patch.object(h, "verified_raw", tamper), patch.object(h, "parse_stored") as parser:
            path, _ = self.run_fake()
        parser.assert_not_called()
        self.assertEqual(self.read(path / "run_status.json")["status"], "FAILED")

    def test_export_detects_raw_and_parsed_tampering(self):
        for name in ("response.raw", "parsed.json"):
            path, _ = self.run_fake(ids=(name,))
            target = next((path / "calls").glob("*/" + name))
            target.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "INTEGRITY"):
                evaluation.export_predictions(path, repo=self.repo)

    def test_atomic_publication_no_overwrite_or_partial_destination(self):
        path = self.repo / "exclusive"
        h.atomic_new(path, b"first")
        with self.assertRaises(FileExistsError):
            h.atomic_new(path, b"second")
        self.assertEqual(path.read_bytes(), b"first")
        with patch.object(h.os, "link", side_effect=OSError("unsupported filesystem")):
            with self.assertRaises(OSError):
                h.atomic_new(self.repo / "unpublished", b"content")
        self.assertFalse((self.repo / "unpublished").exists())
        self.assertFalse(list(self.repo.glob(".pending-*")))

    def test_same_run_resume_rejected_without_backend_load(self):
        self.run_fake(run_id="immutable")
        with patch.object(h.ScriptedBackend, "load") as load:
            with self.assertRaises(FileExistsError):
                self.run_fake(run_id="immutable")
        load.assert_not_called()

    def test_rerun_new_identity_and_authority_required(self):
        path, _ = self.run_fake(run_id="previous")
        reference = {"run_id": "previous", "run_manifest_sha256": data.sha((path / "run_manifest.json").read_bytes())}
        with self.assertRaisesRegex(ValueError, "NEW_ID"):
            self.run_fake(run_id="previous", rerun_of=reference)
        with self.assertRaisesRegex(PermissionError, "RESEARCH_LEAD"):
            self.run_fake(run_id="rerun", rerun_of=reference)
        with self.assertRaisesRegex(ValueError, "REFERENCE_MISMATCH"):
            self.run_fake(run_id="rerun", rerun_of={**reference, "run_manifest_sha256": "0" * 64})
        with self.assertRaisesRegex(PermissionError, "PREVIOUS_ATTEMPT"):
            self.run_fake(run_id="concealed-repeat")

    def test_new_shard_can_only_attempt_previously_unattempted_samples(self):
        self.run_fake([GenerationFailure()], run_id="first", ids=("a", "b"))
        path, backend = self.run_fake(run_id="remaining", ids=("b",))
        self.assertEqual(backend.calls, 1)
        self.assertEqual(self.read(path / "run_status.json")["samples"], {"b": "SUCCESS"})
        with self.assertRaisesRegex(PermissionError, "PREVIOUS_ATTEMPT"):
            self.run_fake(run_id="failed-again", ids=("a",))

    def test_generation_failure_no_retry_no_fabricated_raw(self):
        path, backend = self.run_fake([GenerationFailure(), b"unused"])
        self.assertEqual(backend.calls, 1)
        self.assertFalse(list((path / "calls").glob("*/response.raw")))
        parsed = self.read(next((path / "calls").glob("*/parsed.json")))
        self.assertEqual((parsed["parse_status"], parsed["safety_level"]), ("FAILED", None))
        with self.assertRaisesRegex(ValueError, "COMPLETED"):
            evaluation.export_predictions(path, repo=self.repo)

    def test_generation_partial_raw_preserved_without_parse(self):
        with patch.object(h, "parse_stored") as parse:
            path, backend = self.run_fake([GenerationFailure(b"partial native output")])
        parse.assert_not_called()
        self.assertEqual(backend.calls, 1)
        self.assertEqual(next((path / "calls").glob("*/response.raw")).read_bytes(), b"partial native output")

    def test_interrupted_shard_preserves_completed_and_not_attempted(self):
        original = h.ScriptedBackend.generate
        def interrupt(backend, **kwargs):
            if backend.calls == 1:
                raise KeyboardInterrupt()
            return original(backend, **kwargs)
        with patch.object(h.ScriptedBackend, "generate", interrupt):
            path, _ = self.run_fake(ids=("a", "b", "c"))
        status = self.read(path / "run_status.json")
        self.assertEqual(status["status"], "INTERRUPTED")
        self.assertEqual(status["samples"], {"a": "SUCCESS", "b": "FAILED", "c": "NOT_ATTEMPTED"})
        self.assertEqual(len(list((path / "calls").glob("*/response.raw"))), 1)

    def test_wrong_runtime_observation_stops_before_generation(self):
        with patch.object(h.ScriptedBackend, "observe", return_value={"token": "secret"}):
            path, backend = self.run_fake()
        self.assertEqual(backend.calls, 0)
        self.assertEqual(self.read(path / "run_status.json")["samples"], {"a": "NOT_ATTEMPTED", "b": "NOT_ATTEMPTED"})
        self.assertFalse((path / "environment.json").exists())

    def test_invalid_never_becomes_level04_and_no_semantic_retry(self):
        path, backend = self.run_fake([b"bad JSON", native("moondream", '{"safety_level":"level04"}')])
        table = evaluation.export_predictions(path, repo=self.repo)
        self.assertEqual(backend.calls, 2)
        self.assertEqual([(r["parse_status"], r["safety_level"]) for r in table["rows"]], [("INVALID", None)] * 2)

    def test_call_metadata_complete_secret_free(self):
        path, _ = self.run_fake()
        meta = self.read(next((path / "calls").glob("*/metadata.json")))
        self.assertTrue({"run_id", "sample_id", "call_id", "protocol_id", "model_key", "model_id",
                         "immutable_revision", "prompt_version", "prompt_sha256", "production_policy_identity",
                         "image_sha256", "git_commit", "adapter_version", "parser_version", "decoding",
                         "preprocessing_id", "preprocessing", "precision", "quantization", "software_versions",
                         "hardware_observation", "shard_identity", "started_at", "ended_at", "termination_stage",
                         "failure_cause", "raw_response", "parse_status"} <= set(meta))
        self.assertEqual(set(meta["raw_response"]), {"sha256", "size_bytes", "encoding"})
        self.assertEqual(self.read(path / "environment.json")["observation_kind"], "SIMULATED")

    def test_deterministic_sharding_union_no_gaps_duplicates(self):
        rows = [{"sample_id": str(i), "image_locator": "generated.png", "image_sha256": "0" * 64} for i in range(11)]
        combined = []
        for i in range(4):
            subset, manifest = data.shard(rows, 4, i, "source")
            self.assertEqual((subset, manifest), data.shard(reversed(rows), 4, i, "source"))
            combined.extend(r["sample_id"] for r in subset)
        self.assertEqual(sorted(combined), sorted(r["sample_id"] for r in rows))
        self.assertEqual(len(combined), len(set(combined)))

    def test_sharding_cannot_use_label_or_prediction(self):
        rows = [{"sample_id": "a", "image_locator": "generated.png", "image_sha256": "0" * 64}]
        first = data.shard(rows, 1, 0, "same")
        evaluation_only = {"true_safety_level": "Level01", "prediction": "Level04"}
        evaluation_only.update(true_safety_level="Level04", prediction="Level01")
        self.assertEqual(first, data.shard(rows, 1, 0, "same"))
        with self.assertRaisesRegex(ValueError, "LABEL_FREE"):
            data.shard([{**rows[0], **evaluation_only}], 1, 0, "same")
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            data.shard(rows * 2, 1, 0, "same")

    def tables(self, invalid_moondream=False):
        return [evaluation.export_predictions(self.run_fake(model=m, run_id="fake-" + m,
                    outputs=[b"invalid"] * 2 if m == "moondream" and invalid_moondream else None)[0], repo=self.repo)
                for m in h.MODELS]

    def test_export_deterministic_and_no_gt(self):
        path, _ = self.run_fake()
        table = evaluation.export_predictions(path, repo=self.repo)
        self.assertEqual(data.json_bytes(table), data.json_bytes(evaluation.export_predictions(path, repo=self.repo)))
        self.assertEqual([r["sample_id"] for r in table["rows"]], ["a", "b"])
        for row in table["rows"]:
            self.assertEqual(set(row), evaluation.PREDICTION_FIELDS)
        for key in ("true_safety_level", "folder_domain", "hazard_memberships", "ground_truth"):
            self.assertNotIn(key, data.json_bytes(table).decode())

    def test_four_model_alignment_and_explicit_gt_join_d9r24(self):
        tables = self.tables()
        rows = [{"sample_id": sid, "true_safety_level": "Level01", "folder_domain": "power",
                 "split": "test", "point_id": None, "hazard_memberships": ["SMOKE"]} for sid in ("b", "a")]
        result = evaluation.join_evaluation(tables, rows)
        self.assertEqual([r.sample_id for r in result.samples], ["a", "b"])
        self.assertEqual(result.metadata[0]["split"], "test")
        self.assertEqual(rq3_metrics(result.samples)["pooled"]["joint_valid_4_n"], 2)
        self.assertEqual(evaluation.align_four_models(tables), evaluation.align_four_models(reversed(tables)))

    def test_four_model_invalid_remains_null(self):
        tables = self.tables(invalid_moondream=True)
        aligned = evaluation.align_four_models(tables)
        self.assertIsNone(aligned[0]["predictions"]["moondream"])

    def test_multishard_join_requires_complete_union(self):
        tables = []
        for model in h.MODELS:
            for index in range(3):
                path, _ = self.run_fake(model=model, run_id=f"shard-{model}-{index}",
                                        ids=("a", "b", "c", "d"), shard_count=3, shard_index=index)
                tables.append(evaluation.export_predictions(path, repo=self.repo))
        self.assertEqual([r["sample_id"] for r in evaluation.align_four_models(tables)], ["a", "b", "c", "d"])
        with self.assertRaisesRegex(ValueError, "INCOMPLETE"):
            evaluation.align_four_models(tables[:-1])

    def test_four_model_missing_duplicate_protocol_or_cohort_rejected(self):
        tables = self.tables()
        with self.assertRaises(ValueError):
            evaluation.align_four_models(tables[:3])
        with self.assertRaises(ValueError):
            evaluation.align_four_models(tables + tables[:1])
        for mutate in (lambda t: t[0]["rows"].pop(),
                       lambda t: t[0]["protocol_identity"].update(source_manifest_sha256="different"),
                       lambda t: t[0]["shard"]["cohort_sample_ids"].append("unknown"),
                       lambda t: t[0]["rows"][0].update(true_safety_level="Level01")):
            modified = deepcopy(tables)
            mutate(modified)
            with self.assertRaises(ValueError):
                evaluation.align_four_models(modified)

    def test_gt_join_rejects_missing_duplicate_or_injected_metadata(self):
        tables = self.tables()
        with self.assertRaisesRegex(ValueError, "GT_COHORT"):
            evaluation.join_evaluation(tables, [])

    def test_no_heavy_import_or_model_load(self):
        code = '''import builtins, socket
old = builtins.__import__
def guard(name, *args, **kwargs):
    if name.split('.')[0] in {'torch','transformers','huggingface_hub','requests'}:
        raise AssertionError(name)
    return old(name, *args, **kwargs)
builtins.__import__ = guard
socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError('network'))
from safeshift.runners.p2_harness import registry, synthetic_image
from safeshift.protocol.p2_evaluation import align_four_models
assert len(registry()) == 4
assert synthetic_image().startswith(b'\\x89PNG')
'''
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)

    def test_contract_and_historical_active_artifacts_unchanged(self):
        c = h.contract()
        self.assertEqual(c["sample_count"], 5013)
        self.assertEqual(c["dataset_fingerprint"], data.FINGERPRINT)
        historical = json.loads(subprocess.check_output(
            ["git", "show", "e7628d68f87cf53b5343ea912b7e332064c285af:" + h.CONTRACT_PATH], cwd=ROOT))
        self.assertEqual(historical["protocol_freeze"], "PENDING")
        self.assertFalse(historical["inspecsafe_inference_authorized"])
        self.assertEqual(c["protocol_freeze"], "FROZEN")
        self.assertEqual(c["implementation_freeze"], "FROZEN")
        self.assertTrue(c["inspecsafe_inference_authorized"])
        self.assertEqual(c["authorization_activation"], "FINAL_REVIEWED_MAIN_MERGE_COMMIT_ONLY")
        self.assertEqual(c["primary_grounding"], "DEFERRED_OUT_OF_PRIMARY_SEMINAR_SCOPE")
        protected = [*c["identity_sha256"], "safeshift/runners/production_classification.py",
                     "safeshift/protocol/classification_failure_policy.py",
                     "safeshift/protocol/d9r24_metrics.py", "safeshift/protocol/reporting.py"]
        for name in protected:
            before = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
            self.assertEqual((ROOT / name).read_bytes().replace(b"\r\n", b"\n"), before)
        # The prospective runtime loader is extended; semantic policy functions
        # and the default historical policy view remain exactly preserved.
        path = "safeshift/protocol/classification_policy.py"
        before = subprocess.check_output(["git", "show", f"{BASE}:{path}"], cwd=ROOT)
        def functions(raw):
            return {node.name: ast.dump(node) for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}
        old, current = functions(before), functions((ROOT / path).read_bytes())
        for name in ("same_json", "render_prompt", "validate_context"):
            self.assertEqual(old[name], current[name], name)
        self.assertEqual(h.load_policy(), json.loads((ROOT / h.POLICY_PATH).read_bytes()))
        for name in ("DECISIONS.md", "TASKS.md"):
            before = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
            self.assertTrue((ROOT / name).read_bytes().replace(b"\r\n", b"\n").startswith(before))


class DatasetTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.manifest = self.root / "manifest.csv"
        self.provenance = self.root / "provenance.json"

    def write(self, rows, fingerprint=data.FINGERPRINT):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        raw = stream.getvalue().encode()
        self.manifest.write_bytes(raw)
        self.provenance.write_bytes(data.json_bytes({"dataset": "InspecSafe-V1", "input_sha256": fingerprint,
                                                      "output_sha256": data.sha(raw)}))
        return data.sha(raw)

    def test_wrong_fingerprint_before_backend_factory(self):
        self.write([], fingerprint="wrong")
        with patch.object(h, "resolve_production_backend") as resolver, \
                patch.object(h, "authorize_production", return_value=(BASE, {})):
            with self.assertRaisesRegex(ValueError, "FINGERPRINT"):
                h.production_run(model="moondream", run_id="r", dataset_root=self.root,
                                 manifest_path=self.manifest, provenance_path=self.provenance)
        resolver.assert_not_called()

    def test_wrong_count_before_backend_factory(self):
        self.write([])
        with patch.object(h, "resolve_production_backend") as resolver, \
                patch.object(h, "authorize_production", return_value=(BASE, {})):
            with self.assertRaisesRegex(ValueError, "COUNT"):
                h.production_run(model="moondream", run_id="r", dataset_root=self.root,
                                 manifest_path=self.manifest, provenance_path=self.provenance)
        resolver.assert_not_called()

    def test_duplicate_and_schema_rejected(self):
        self.write([dict.fromkeys(FIELDS, "same")] * 5013)
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            data.verify_dataset(self.root, self.manifest, self.provenance)
        self.manifest.write_text("wrong,schema\n")
        with self.assertRaisesRegex(ValueError, "SCHEMA"):
            data.verify_dataset(self.root, self.manifest, self.provenance)

    def test_paths_traversal_absolute_and_alias_rejected(self):
        for locator in ("../x", "/x", "C:/x", "a/../x", "a\\x", "a//x", "./x", "a:b"):
            with self.subTest(locator=locator), self.assertRaises(ValueError):
                data.safe_path(self.root, locator)
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(ValueError, "ALIAS"):
                data.safe_path(self.root, "image.png")

    def synthetic_triplet(self):
        row = dict.fromkeys(FIELDS, "unused")
        point = "power-Level01-robot-000001"
        sid = point + "-001"
        relative = f"train/DATA_PATH/train/Annotations/Anomaly_data/{point}/{sid}"
        row.update(sample_id=sid, split="train", data_type="Anomaly_data", folder_domain="power",
                   safety_level="Level01", point_id="000001", has_other_modalities="false")
        fingerprint = hashlib.sha256()
        for key, suffix in (("image_relpath", ".jpg"), ("json_relpath", ".json"), ("txt_relpath", ".txt")):
            locator = relative + suffix
            path = self.root / locator
            path.parent.mkdir(parents=True, exist_ok=True)
            content = h.synthetic_image() if suffix == ".jpg" else b"synthetic metadata"
            path.write_bytes(content)
            row[key] = data.NAMESPACE + "/" + locator
            fingerprint.update(json.dumps([row[key], data.sha(content)], ensure_ascii=True).encode("ascii") + b"\n")
        fingerprint.update(json.dumps([sid, False]).encode("ascii") + b"\n")
        digest = fingerprint.hexdigest()
        manifest_sha = self.write([row], fingerprint=digest)
        return row, digest, manifest_sha

    def test_triplet_fingerprint_portable_root_and_image_hash(self):
        row, digest, manifest_sha = self.synthetic_triplet()
        with patch.multiple(data, COUNT=1, FINGERPRINT=digest, MANIFEST_SHA=manifest_sha):
            records, _ = data.verify_dataset(self.root, self.manifest, self.provenance)
            self.assertEqual(records[0]["image_sha256"], data.sha(h.synthetic_image()))
            self.assertEqual(set(records[0]), data.EXECUTION_FIELDS)
            self.assertNotIn(str(self.root), data.json_bytes(records).decode())
            (self.root / row["txt_relpath"][len(data.NAMESPACE)+1:]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "FINGERPRINT"):
                data.verify_dataset(self.root, self.manifest, self.provenance)

    def test_missing_image_fails_and_manifest_tamper_fails(self):
        row, digest, manifest_sha = self.synthetic_triplet()
        with patch.multiple(data, COUNT=1, FINGERPRINT=digest, MANIFEST_SHA=manifest_sha):
            image = self.root / row["image_relpath"][len(data.NAMESPACE)+1:]
            image.unlink()
            with self.assertRaises(FileNotFoundError):
                data.verify_dataset(self.root, self.manifest, self.provenance)
            self.manifest.write_bytes(self.manifest.read_bytes().replace(b"Level01", b"Level04"))
            with self.assertRaisesRegex(ValueError, "MANIFEST_HASH"):
                data.verify_dataset(self.root, self.manifest, self.provenance)


if __name__ == "__main__":
    unittest.main()
