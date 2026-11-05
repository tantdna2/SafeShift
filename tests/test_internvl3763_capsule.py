"""Offline HTTP adapter + real pinned SDK/requests streaming; never Kaggle."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import traceback
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch
import zipfile

from safeshift import internvl3763_operator as op
from safeshift import internvl3763_campaign as c
from safeshift.pilot.contract import digest, json_bytes
from safeshift.pilot.artifacts import write
from test_internvl3763_campaign import fixture

try:
    import requests
    from kagglesdk import KaggleClient
except ImportError:
    KaggleClient = None


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv (no install/network)")
class CapsuleTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request, self.grant, self.comments = fixture(self.root/"ledger")
        self.intent = {"notice": "SYNTHETIC_ONLY", "request": self.request}
        self.payload = json_bytes({"request": self.request, "campaign_intent": self.intent})
        self.name = "safeshift_train3763_execution.json"
        self.download = "https://api.kaggle.com/v1/datasets.DatasetApiService/DownloadDataset"
        self.storage = "https://storage.googleapis.com/kaggle-data-sets/synthetic/capsule?X-Goog-Signature=SIGNED_SECRET"
        self.calls = []
        self.download_status = 302
        self.storage_status = 200
        self.failure = None
        self.body = self.payload
        self.wrong_version = False
        self.private = True
        self.client = NS(build_kaggle_client=lambda: KaggleClient(api_token="KAGGLE_SECRET"),
            dataset_list_files=self.list_files, kernels_push=Mock(return_value=NS(to_dict=lambda: {"notice": "SYNTHETIC"})))
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")))
        stack.enter_context(patch.object(requests.adapters.HTTPAdapter, "send", self.adapter))

    def list_files(self, ref, **kwargs):
        self.assertEqual(ref, self.request["bindings"]["runtime"]["execution_input"]["ref"])
        return NS(error_message="", next_page_token="", files=[NS(name=self.name, total_bytes=len(self.payload))])

    def adapter(self, request, **kwargs):
        self.assertEqual(kwargs["timeout"], (10, 30))
        self.calls.append((request, kwargs))
        response = requests.Response()
        response.request, response.url = request, request.url
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        if request.url.endswith("/GetDatasetMetadata"):
            body = json.dumps({"info": {"isPrivate": self.private, "ownerUser": "nguynanhtn", "datasetSlug": "synthetic-capsule"}}).encode()
        elif request.url == self.download:
            fields = json.loads(request.body)
            self.assertEqual(fields, {"ownerSlug": "nguynanhtn", "datasetSlug": "synthetic-capsule",
                "datasetVersionNumber": 1, "fileName": self.name})
            response.status_code = self.download_status
            response.headers["Location"] = self.storage
            body = b"" if response.status_code == 302 else self.body
        elif request.url.startswith("https://storage.googleapis.com/"):
            self.assertEqual(request.method, "GET")
            self.assertIsNone(request.body)
            self.assertEqual(dict(request.headers), {"Accept-Encoding": "identity"})
            self.assertTrue(kwargs["verify"])
            self.assertEqual(kwargs["proxies"], {})
            self.assertIsNone(kwargs["cert"])
            if self.failure:
                raise self.failure("SIGNED_SECRET KAGGLE_SECRET " + request.url)
            response.status_code = self.storage_status
            response.headers["Location"] = self.storage
            body = self.body if not self.wrong_version else b"x"*len(self.payload)
        else:
            body = b""
            response.status_code = 302
            response.headers["Location"] = self.storage
        response.raw = io.BytesIO(body)
        response.headers["Content-Length"] = str(len(body))
        return response

    def verify(self, path="proof"):
        return op.verify_execution_input(self.client, self.request, self.intent, self.root/path)

    def test_real_sdk_302_anonymous_get_streams_exact_file_without_secrets(self):
        # Poison ambient auth and the session defaults; storage must not inherit them.
        with patch.dict("os.environ", {"HTTP_PROXY": "http://proxy.invalid", "HTTPS_PROXY": "http://proxy.invalid",
                "NETRC": "nonexistent-synthetic-netrc"}), patch("sys.stdout", new_callable=io.StringIO) as out:
            proof = self.verify()
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(proof["sha256"], hashlib.sha256(self.payload).hexdigest())
        self.assertEqual((self.root/"proof/download.part").read_bytes(), self.payload)
        self.assertEqual([r.method for r, _ in self.calls], ["POST", "POST", "GET"])
        self.assertEqual(self.calls[1][0].headers["Authorization"], "Bearer KAGGLE_SECRET")
        self.assertNotIn("SECRET", json.dumps(proof))
        self.client.kernels_push.assert_not_called()

    def test_unsafe_host_scheme_userinfo_port_fragment_and_empty_signature_block(self):
        for location in ("http://storage.googleapis.com/a?sig=x", "https://evil.invalid/a?sig=x",
                "https://storage.googleapis.com.evil.invalid/a?sig=x", "https://storage.googleapis.com@evil.invalid/a?sig=x",
                "https://user:pass@storage.googleapis.com/a?sig=x", "https://storage.googleapis.com:443/a?sig=x",
                "https://storage.googleapis.com/a?sig=x#secret", "https://storage.googleapis.com/a",
                "/relative?sig=x", "https://storage.googleapis.com/a?sig=\nsecret"):
            with self.subTest(location=location):
                self.storage = location; self.calls.clear()
                with self.assertRaisesRegex(ValueError, "NO_RETRY"):
                    self.verify("bad-"+str(len(list(self.root.iterdir()))))
                self.assertEqual(len(self.calls), 2)

    def test_storage_chain_and_initial_other_redirect_codes_are_never_followed(self):
        for status in (301, 302, 303, 307, 308, 403):
            self.storage_status = status; self.calls.clear()
            with self.assertRaises(ValueError):
                self.verify("storage-"+str(status))
            self.assertEqual(len(self.calls), 3)
        self.storage_status = 200
        for status in (301, 303, 307, 308):
            self.download_status = status; self.calls.clear()
            with self.assertRaises(ValueError):
                self.verify("initial-"+str(status))
            self.assertEqual(len(self.calls), 2)

    def test_timeout_connect_failure_zero_retry_and_sanitized_traceback(self):
        for failure in (requests.ReadTimeout, requests.ConnectTimeout, requests.ConnectionError):
            self.failure = failure; self.calls.clear()
            try:
                self.verify(failure.__name__)
                self.fail("must fail closed")
            except ValueError:
                rendered = traceback.format_exc()
                self.assertNotIn("SIGNED_SECRET", rendered)
                self.assertNotIn("KAGGLE_SECRET", rendered)
                self.assertNotIn("storage.googleapis.com", rendered)
            self.assertEqual(len(self.calls), 3)
            self.assertFalse((self.root/"input-proof.json").exists())

    def test_direct_200_wrong_bytes_truncation_wrong_version_and_private_metadata(self):
        self.download_status = 200
        self.assertEqual(self.verify("direct")["bytes"], len(self.payload))
        self.download_status = 302
        for index, body in enumerate((b"x"*len(self.payload), self.payload[:-1])):
            self.body = body
            with self.assertRaisesRegex(ValueError, "STALE_OR_WRONG|DOWNLOAD_BOUND"):
                self.verify("wrong-"+str(index))
            self.assertEqual((self.root/("wrong-"+str(index))/"download.part").read_bytes(), body)
        self.body = self.payload; self.wrong_version = True
        with self.assertRaisesRegex(ValueError, "STALE_OR_WRONG"):
            self.verify("wrong-version")
        self.wrong_version = False; self.private = False; self.calls.clear()
        with self.assertRaisesRegex(ValueError, "PRIVATE_OWNER"):
            self.verify("public")
        self.assertEqual(len(self.calls), 1)

    def test_zip_wrapper_exact_member_size_crc_and_wrong_member(self):
        for index, name in enumerate((self.name, "wrong.json")):
            packed = io.BytesIO()
            with zipfile.ZipFile(packed, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(name, self.payload)
            self.body = packed.getvalue()
            if index == 0:
                self.assertEqual(self.verify("zip")["bytes"], len(self.payload))
            else:
                with self.assertRaisesRegex(ValueError, "WRAPPER_INTEGRITY"):
                    self.verify("zip-wrong")

    def test_download_rpc_scoped_by_method_and_exact_version_body(self):
        from scripts.submit_internvl_v2 import bounded_http
        from kagglesdk.datasets.types.dataset_api_service import ApiDownloadDatasetRequest
        query = ApiDownloadDatasetRequest()
        query.owner_slug, query.dataset_slug, query.file_name, query.dataset_version_number = "nguynanhtn", "synthetic-capsule", self.name, 1
        for method, fields in (("GET", query.to_dict()), ("POST", {**query.to_dict(), "datasetVersionNumber": 2})):
            with self.assertRaises(ValueError), bounded_http(), op.capsule_http(query), requests.Session() as session:
                session.send(requests.Request(method, self.download, json=fields).prepare())
        self.assertEqual(self.calls, [])

    def test_metadata_push_and_legacy_post_redirect_defaults_unchanged(self):
        from scripts.submit_internvl_v2 import bounded_http
        from kagglesdk.datasets.types.dataset_api_service import ApiDownloadDatasetRequest
        query = ApiDownloadDatasetRequest()
        query.owner_slug, query.dataset_slug, query.file_name, query.dataset_version_number = "nguynanhtn", "synthetic-capsule", self.name, 1
        with bounded_http(), op.capsule_http(query), requests.Session() as session:
            for endpoint in ("https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel",
                    "https://api.kaggle.com/v1/datasets.DatasetApiService/GetDatasetMetadata",
                    "https://www.kaggle.com/api/v1/kernels/push"):
                response = session.send(requests.Request("POST", endpoint, json={}).prepare())
                response.close()
            with self.client.build_kaggle_client() as remote:
                response = remote.datasets.dataset_api_client.download_dataset(query)
                response.close()
        self.assertEqual(len(self.calls), 5)
        self.calls.clear()
        for endpoint in ("https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel",
                "https://api.kaggle.com/v1/datasets.DatasetApiService/GetDatasetMetadata",
                "https://www.kaggle.com/api/v1/kernels/push"):
            with bounded_http(), requests.Session() as session:
                response = session.send(requests.Request("POST", endpoint, json={}).prepare())
                response.close()
        self.assertEqual(len(self.calls), 3)

    def test_actual_submit_pushes_once_only_after_download_and_exact_byte_proof(self):
        from safeshift import internvl3763_release as old
        with patch.object(old, "get", side_effect=lambda path: deepcopy(self.comments[path])):
            ledger = c.Ledger.create(self.root/"ledger", self.root/"mirror", self.grant, "synthetic-machine")
            self.intent = ledger.reserve(self.request)
        self.payload = json_bytes({"request": self.request, "campaign_intent": self.intent})
        self.body = self.payload
        execution = self.request["bindings"]["runtime"]["execution_request"]
        handoff = self.root/"handoff"; handoff.mkdir()
        notebook = self.root/"synthetic.ipynb"; write(notebook, {"cells": []})
        def push(*args, **kwargs):
            self.assertEqual((handoff/"submission/input-proof/download.part").read_bytes(), self.payload)
            self.assertTrue((handoff/"submission/input-proof.json").is_file())
            self.assertEqual([x["kind"] for x in ledger.events()], ["INTENT", "PUSH_INTENT"])
            return NS(to_dict=lambda: {"notice": "SYNTHETIC_ONLY"})
        self.client.kernels_push.side_effect = push
        with patch.object(op, "campaign_ledger", return_value=ledger), \
                patch.object(op, "admit_campaign", return_value=(self.grant, execution)), patch.object(op, "safe", return_value=notebook), \
                patch.object(op, "api", return_value=self.client), patch.object(op, "campaign_inventory", return_value={}):
            result = op.submit_campaign(self.request, self.grant, execution, handoff)
        self.assertEqual(result, {"job_id": self.request["job"], "version": 1})
        self.client.kernels_push.assert_called_once()
        self.assertEqual([x["kind"] for x in ledger.events()], ["INTENT", "PUSH_INTENT", "SUBMITTED"])

    def test_retry_adapter_and_download_deadline_rejected(self):
        from scripts.submit_internvl_v2 import bounded_http
        with bounded_http(), requests.Session() as session, self.assertRaisesRegex(ValueError, "RETRIES_FORBIDDEN"):
            session.mount("https://", requests.adapters.HTTPAdapter(max_retries=1))
            session.get(self.download)
        self.assertEqual(self.calls, [])
        # A trickling stream cannot reset the absolute 90-second budget.
        with patch.object(op.time, "monotonic", side_effect=[0, 91]), self.assertRaisesRegex(ValueError, "NO_RETRY"):
            self.verify("deadline")
        self.assertEqual(len(self.calls), 3)
        self.assertEqual((self.root/"deadline/download.part").read_bytes(), b"")

    def test_read_failure_preserves_partial_and_never_retries_or_leaks_signed_url(self):
        real_iter = requests.Response.iter_content
        def interrupted(response, *args, **kwargs):
            if response.url.startswith("https://storage.googleapis.com/"):
                yield b"partial"
                raise requests.ConnectionError("SIGNED_SECRET " + response.url)
            else:
                yield from real_iter(response, *args, **kwargs)
        with patch.object(requests.Response, "iter_content", interrupted):
            try:
                self.verify("partial")
                self.fail("interrupted transfer must fail")
            except ValueError:
                self.assertNotIn("SIGNED_SECRET", traceback.format_exc())
        self.assertEqual((self.root/"partial/download.part").read_bytes(), b"partial")
        self.assertEqual(len(self.calls), 3)

    def test_read_only_recovery_requires_complete_provider_absence_and_no_active_job(self):
        from datetime import timedelta
        from safeshift import internvl3763_release as old
        quota = NS(time_used=timedelta(0), time_reserved=timedelta(0), total_time_allowed=timedelta(seconds=10000))
        owned = []
        client = NS(kernels_list_with_response=lambda **_: NS(kernels=[NS(ref=x) for x in owned], next_page_token=None),
            dataset_list_files=lambda *a, **k: NS(files=[NS(name="SYNTHETIC")]), quota_view=lambda: NS(gpu_quota=quota))
        with patch.object(old, "get", side_effect=lambda path: deepcopy(self.comments[path])), patch.object(op, "api", return_value=client):
            ledger = c.Ledger.create(self.root/"ledger", self.root/"mirror", self.grant, "synthetic-machine")
            ledger.reserve(self.request)
            for state in ("exists", "active", "unknown"):
                if state == "exists":
                    owned.append(self.request["job"])
                elif state == "active":
                    owned.clear(); quota.time_reserved = timedelta(seconds=1)
                else:
                    client.kernels_list_with_response = Mock(side_effect=TimeoutError("SYNTHETIC_UNKNOWN"))
                with self.assertRaises((ValueError, TimeoutError)):
                    ledger.abort_pre_submit()
                self.assertEqual([x["kind"] for x in ledger.events()], ["INTENT"])
            quota.time_reserved = timedelta(0)
            client.kernels_list_with_response = lambda **_: NS(kernels=[], next_page_token=None)
            result = ledger.abort_pre_submit()
            self.assertTrue(result["provider"]["job_absent"])
            self.assertEqual(result["provider"]["job"], self.request["job"])
            self.assertIsNone(ledger.open_intent())

    def test_actual_submit_waits_for_verified_bytes_failure_preserves_intent_and_stage(self):
        from safeshift import internvl3763_release as old
        with patch.object(old, "get", side_effect=lambda path: deepcopy(self.comments[path])):
            ledger = c.Ledger.create(self.root/"ledger", self.root/"mirror", self.grant, "synthetic-machine")
            intent = ledger.reserve(self.request)
        self.intent = intent; self.payload = json_bytes({"request": self.request, "campaign_intent": intent})
        self.body = b"x"*len(self.payload)
        execution = self.request["bindings"]["runtime"]["execution_request"]
        handoff = self.root/"handoff"; handoff.mkdir()
        with patch.object(op, "campaign_ledger", return_value=ledger), \
                patch.object(op, "admit_campaign", return_value=(self.grant, execution)), \
                patch.object(op, "api", return_value=self.client), patch.object(op, "campaign_inventory", return_value={}):
            with self.assertRaisesRegex(ValueError, "STALE_OR_WRONG"):
                op.submit_campaign(self.request, self.grant, execution, handoff)
            self.assertEqual([x["kind"] for x in ledger.events()], ["INTENT"])
            self.client.kernels_push.assert_not_called()
            retained = {p.relative_to(handoff).as_posix(): p.read_bytes() for p in handoff.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "STALE_SUBMISSION_PRESERVED"):
                op.submit_campaign(self.request, self.grant, execution, handoff)
            self.assertEqual(retained, {p.relative_to(handoff).as_posix(): p.read_bytes() for p in handoff.rglob("*") if p.is_file()})
            self.assertEqual(ledger.open_intent(), intent)


if __name__ == "__main__":
    unittest.main()
