"""Synthetic configuration checks only; no model requests, images or outputs."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.protocol.adapters import ADAPTERS
from safeshift.protocol.qwen_config import (
    ENDPOINT_ENV, ENDPOINT_TEMPLATE, PENDING, WORKSPACE_ID_ENV, QwenConfiguration,
    resolve_qwen_configuration, validate_qwen_policy, validate_workspace_endpoint,
)
from scripts.validate_qwen_config import main

REPO = Path(__file__).resolve().parents[1]
# An invented test DNS label, never a real configured workspace or access claim.
SYNTHETIC_ENDPOINT = ENDPOINT_TEMPLATE.format(WorkspaceId="synthetic-test")


class QwenConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((REPO / "configs/pre_freeze/providers.json").read_bytes())["providers"]["qwen_dashscope"]

    def resolve(self, env):
        with patch.dict(os.environ, env, clear=True):
            return resolve_qwen_configuration(self.config)

    def test_valid_singapore_workspace_endpoint(self):
        self.assertEqual(validate_workspace_endpoint(SYNTHETIC_ENDPOINT), SYNTHETIC_ENDPOINT)
        result = self.resolve({ENDPOINT_ENV: SYNTHETIC_ENDPOINT})
        self.assertEqual(result.workspace_endpoint, SYNTHETIC_ENDPOINT)
        self.assertEqual(result.workspace_endpoint_status, "RESOLVED")
        self.assertEqual(result.report()["checklist_1"], "DONE")
        self.assertFalse(result.report()["live_route_verified"])

    def test_wrong_region_legacy_trial_and_lookalike_hosts_rejected(self):
        for endpoint in (
            SYNTHETIC_ENDPOINT.replace("ap-southeast-1", "cn-beijing"),
            SYNTHETIC_ENDPOINT.replace("ap-southeast-1", "ap-southeast-2"),
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ENDPOINT_TEMPLATE.format(WorkspaceId="trial"),
            SYNTHETIC_ENDPOINT.replace(".com/", ".com.evil.example/"),
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                self.resolve({ENDPOINT_ENV: endpoint})

    def test_malformed_workspace_ids_rejected_for_both_inputs(self):
        for value in ("", "-test", "test-", "bad_id", "a.b", "a/b", "a@b", "a b",
                      "a\nb", "a%2eb", "{WorkspaceId}", "a" * 64, "tést", "trial"):
            for name, supplied in ((WORKSPACE_ID_ENV, value),
                                   (ENDPOINT_ENV, ENDPOINT_TEMPLATE.format(WorkspaceId=value))):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.resolve({name: supplied})

    def test_noncanonical_urls_and_credentials_rejected_without_echo(self):
        for endpoint in (
            SYNTHETIC_ENDPOINT.replace("https://", "http://"),
            SYNTHETIC_ENDPOINT.replace("https://", "https://SECRET:SECRET@"),
            SYNTHETIC_ENDPOINT.replace(".com/", ".com:443/"),
            SYNTHETIC_ENDPOINT + "?api_key=SECRET",
            SYNTHETIC_ENDPOINT + "#SECRET",
            SYNTHETIC_ENDPOINT + "/", SYNTHETIC_ENDPOINT + "/chat/completions",
            " " + SYNTHETIC_ENDPOINT, SYNTHETIC_ENDPOINT + "\n",
            SYNTHETIC_ENDPOINT.replace("https://", "https://\t"),
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError) as ctx:
                self.resolve({ENDPOINT_ENV: endpoint})
            self.assertNotIn("SECRET", str(ctx.exception))
            self.assertNotIn(endpoint, str(ctx.exception))

    def test_id_derivation_and_endpoint_precedence(self):
        self.assertEqual(self.resolve({WORKSPACE_ID_ENV: "synthetic-test"}).workspace_endpoint,
                         SYNTHETIC_ENDPOINT)
        result = self.resolve({ENDPOINT_ENV: SYNTHETIC_ENDPOINT, WORKSPACE_ID_ENV: "invalid/id"})
        self.assertEqual(result.workspace_endpoint, SYNTHETIC_ENDPOINT)
        for endpoint in ("", "bad"):
            with self.assertRaises(ValueError):
                self.resolve({ENDPOINT_ENV: endpoint, WORKSPACE_ID_ENV: "synthetic-test"})

    def test_absent_environment_is_pending_even_with_generic_route_vars(self):
        result = self.resolve({"OPENAI_BASE_URL": SYNTHETIC_ENDPOINT,
                               "DASHSCOPE_BASE_URL": SYNTHETIC_ENDPOINT})
        self.assertIsNone(result.workspace_endpoint)
        self.assertEqual(result.report()["checklist_1"], PENDING)
        self.assertEqual(result.report()["checklist_2"], "DONE")

    def test_only_route_environment_variables_are_read(self):
        with patch("safeshift.protocol.qwen_config.os.environ") as env:
            env.get.return_value = None
            resolve_qwen_configuration(self.config)
            self.assertEqual([call.args for call in env.get.call_args_list],
                             [(ENDPOINT_ENV,), (WORKSPACE_ID_ENV,)])

    def test_inline_endpoint_credentials_and_extra_controls_rejected(self):
        for key, value in (("workspace_endpoint", SYNTHETIC_ENDPOINT),
                           ("api_key", "SECRET"), ("WorkspaceId", "synthetic-test"),
                           ("endpoint", SYNTHETIC_ENDPOINT), ("temperature", 0),
                           ("extra_body", {"enable_thinking": True}),
                           ("endpoint_env", "OPENAI_BASE_URL")):
            config = deepcopy(self.config)
            config[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError) as ctx:
                validate_qwen_policy(config)
            self.assertNotIn("SECRET", str(ctx.exception))

    def test_model_region_thinking_and_evidence_are_fixed(self):
        for key, value in (("model_id", "qwen3-vl-8b-thinking"), ("region", "cn-beijing"),
                           ("thinking_enabled", True), ("thinking_enabled", 0),
                           ("thinking_policy", "PROVIDER_DEFAULT"),
                           ("live_route_verified", True), ("legacy_endpoint_fallback", True)):
            config = deepcopy(self.config)
            config[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_qwen_policy(config)

    def test_exact_decoding_policy_disallows_second_knob_and_thinking(self):
        validate_qwen_policy(self.config)
        for decoding in ({}, "PROVIDER_DEFAULT", {"temperature": False},
                         {"temperature": "0"}, {"temperature": 0.1},
                         {"temperature": float("nan")},
                         *({"temperature": 0, key: value} for key, value in (
                             ("top_p", 1), ("top_k", 1), ("seed", 42), ("do_sample", False),
                             ("enable_thinking", True), ("thinking", "low"),
                             ("extra_body", {"enable_thinking": False})))):
            config = deepcopy(self.config)
            config["decoding"] = decoding
            with self.subTest(decoding=decoding), self.assertRaises(ValueError):
                validate_qwen_policy(config)

    def test_cli_reports_status_only_on_success_and_error(self):
        for endpoint, expected in ((SYNTHETIC_ENDPOINT, 0),
                                   (SYNTHETIC_ENDPOINT + "?key=SECRET", 2)):
            out, err = io.StringIO(), io.StringIO()
            with patch.dict(os.environ, {ENDPOINT_ENV: endpoint, "DASHSCOPE_API_KEY": "SECRET"}, clear=True), redirect_stdout(out), redirect_stderr(err):
                self.assertEqual(main([]), expected)
            self.assertNotIn("SECRET", out.getvalue() + err.getvalue())
            self.assertNotIn("synthetic-test", out.getvalue() + err.getvalue())
            if expected == 0:
                self.assertFalse(json.loads(out.getvalue())["live_route_verified"])
        self.assertNotIn("synthetic-test", repr(self.resolve({ENDPOINT_ENV: SYNTHETIC_ENDPOINT})))

    def test_cli_does_not_load_dotenv_or_echo_malformed_config(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            config_path = repo / "configs/pre_freeze/providers.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(json.dumps({"providers": {"qwen_dashscope": self.config}}))
            (repo / ".env").write_text(ENDPOINT_ENV + "=" + SYNTHETIC_ENDPOINT)
            out = io.StringIO()
            with patch.dict(os.environ, {}, clear=True), redirect_stdout(out):
                self.assertEqual(main([], repo=repo), 0)
            self.assertEqual(json.loads(out.getvalue())["checklist_1"], PENDING)
            config_path.write_text('{"SECRET": invalid json}')
            err = io.StringIO()
            with redirect_stderr(err):
                self.assertEqual(main([], repo=repo), 2)
            self.assertNotIn("SECRET", err.getvalue())

    def test_cli_rejects_inline_arguments_without_echo(self):
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            main(["--endpoint", "https://SECRET:SECRET@example.com"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertNotIn("SECRET", err.getvalue())

    def test_configuration_object_cannot_report_invalid_url_as_resolved(self):
        with self.assertRaises(ValueError):
            QwenConfiguration("https://invalid.example")

    def test_manifest_matches_provider_policy_and_preserves_pending_freeze(self):
        manifest = json.loads((REPO / "configs/pre_freeze/freeze_manifest.template.json").read_bytes())
        for key, value in manifest["provider_routes"]["qwen_dashscope"].items():
            self.assertEqual(value, self.config[key])
        self.assertEqual(manifest["decoding_parameters"]["qwen_dashscope"], self.config["decoding"])
        for key, value in manifest["qwen_decoding_policy"].items():
            self.assertEqual(value, self.config[key])
        self.assertEqual(manifest["final_model_roles"], "PENDING")
        self.assertEqual(manifest["protocol_freeze_commit_sha"], "PENDING")
        self.assertFalse(manifest["model_ids_live_verified"])
        self.assertEqual(manifest["external_case_manifest_sha256"],
                         "fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379")

    def test_transport_stays_disabled_after_route_resolution(self):
        self.resolve({ENDPOINT_ENV: SYNTHETIC_ENDPOINT})
        with self.assertRaisesRegex(RuntimeError, "OFFLINE_ONLY"):
            ADAPTERS["qwen_dashscope"].send(None)


if __name__ == "__main__":
    unittest.main()
