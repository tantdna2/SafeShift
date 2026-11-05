"""Pinned GetKernel serialization through the real SDK, with no sockets/auth."""
from contextlib import ExitStack
from copy import deepcopy
from datetime import timedelta
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift import internvl3763_operator as op
from safeshift import internvl3763_campaign as campaign
from safeshift import internvl3763_release as authority
from safeshift.pilot.contract import digest
from test_internvl3763_campaign import fixture
from test_internvl3763_execution import fixture as legacy_fixture

try:
    import requests
    from kagglesdk import KaggleClient
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
except ImportError:
    KaggleClient = None


class VersionLabelTests(unittest.TestCase):
    def test_positive_integer_versions_are_canonical_labels(self):
        for version in (1, "1", 12, "12"):
            with self.subTest(version=version):
                self.assertEqual(op.kernel_version_label(version), "v" + str(version))

    def test_missing_malformed_and_lossy_versions_are_rejected(self):
        for version in (None, True, False, 0, -1, 1.0, "", "0", "-1", "01", "1.0",
                "v1", "latest", " 1", "1\n", "\u0661", [], {}):
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, "PINNED_KERNEL_VERSION"):
                op.kernel_version_label(version)


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv (no install/network)")
class InstalledSdkVersionTests(unittest.TestCase):
    def setUp(self):
        op.check_sdk()
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Only this public locator is reused; every response/body is synthetic.
        self.input_job = "nguynanhtn/safeshift-prepare-internvl35"
        self.request, self.grant, self.comments = fixture(self.root/"ledger", kernel_sources=[self.input_job+"/1"])
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(authority, "get", side_effect=lambda path: deepcopy(self.comments[path])))
        stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_KAGGLE_NETWORK")))
        stack.enter_context(patch.object(requests.adapters.HTTPAdapter, "send", self.adapter))
        self.ledger = campaign.Ledger.create(self.root/"ledger", self.root/"mirror", self.grant, "synthetic-machine")
        self.intent = self.ledger.reserve(self.request)
        self.notebook = {"cells": [{"cell_type": "code", "source": ["print('SYNTHETIC_ONLY')"]}]}
        self.metadata = {"ref": self.input_job, "currentVersionNumber": 1, "isPrivate": True}
        self.pages = [NS(kernels=[], next_page_token=None)]
        self.page_calls, self.calls, self.status_calls = [], [], []
        self.statuses = {}
        self.quota = NS(time_used=timedelta(0), time_reserved=timedelta(0),
            total_time_allowed=timedelta(seconds=10000))
        self.provider_failure = None
        self.latest_job, self.latest_metadata = None, None
        self.client = NS(build_kaggle_client=lambda: KaggleClient(api_token="SYNTHETIC_ONLY"),
            kernels_list_with_response=self.list_owned, kernels_status=self.status,
            dataset_list_files=Mock(return_value=NS(files=[NS(name="SYNTHETIC_ONLY")])),
            quota_view=Mock(side_effect=lambda: NS(gpu_quota=self.quota)), kernels_push=Mock())
        stack.enter_context(patch.object(op, "api", return_value=self.client))

    def tearDown(self):
        self.client.kernels_push.assert_not_called()

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def list_owned(self, **kwargs):
        self.page_calls.append(kwargs)
        page = int(kwargs["page_token"]) if kwargs["page_token"] else kwargs["page"]
        return self.pages[min(page-1, len(self.pages)-1)]

    def status(self, ref):
        self.status_calls.append(ref)
        return NS(status=self.statuses.get(ref, "COMPLETE"))

    def adapter(self, request, **kwargs):
        self.assertEqual(request.url, "https://api.kaggle.com/v1/kernels.KernelsApiService/GetKernel")
        self.assertEqual(request.method, "POST")
        self.assertEqual(kwargs["timeout"], (10, 30))
        fields = json.loads(request.body)
        self.calls.append(fields)
        if self.provider_failure:
            raise self.provider_failure("SYNTHETIC_PROVIDER_UNKNOWN")
        response = requests.Response()
        response.request, response.url = request, request.url
        # Reproduce the reported bug instead of making every SDK request pass.
        latest_guard = self.latest_job == fields["userName"]+"/"+fields["kernelSlug"] and "versionLabel" not in fields
        response.status_code = 200 if fields.get("versionLabel") in ("v1", "v12") or latest_guard else 404
        body = {"metadata": self.latest_metadata if latest_guard else self.metadata,
            "blob": {"source": json.dumps(self.notebook)}}
        if response.status_code == 404:
            body = {"error": "SYNTHETIC_HTTP_404_VERSION_LABEL"}
        response.headers["Content-Type"] = "application/json"
        response._content = json.dumps(body).encode()
        response.raw = io.BytesIO(response._content)
        return response

    def proof(self):
        return op.pre_submit_inventory(self.ledger, self.intent)

    def assert_blocked_without_mutation(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, requests.RequestException)):
            self.ledger.abort_pre_submit()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.ledger.open_intent(), self.intent)
        self.assertEqual(self.ledger.summary()["reserved_gpu_seconds"], 3600)

    def test_actual_sdk_serializes_raw_1_as_404_and_v1_as_200_without_fallback(self):
        from scripts.submit_internvl_v2 import bounded_http
        query = ApiGetKernelRequest()
        query.user_name, query.kernel_slug = self.input_job.split("/")
        for label in ("1", "", None, "v1"):
            query.version_label = label
            with bounded_http(), self.client.build_kaggle_client() as remote:
                if label == "v1":
                    value = remote.kernels.kernels_api_client.get_kernel(query)
                    self.assertEqual(value.metadata.current_version_number, 1)
                else:
                    with self.assertRaisesRegex(Exception, "404"):
                        remote.kernels.kernels_api_client.get_kernel(query)
        self.assertEqual([c.get("versionLabel") for c in self.calls], ["1", "", None, "v1"])

    def test_full_campaign_and_pre_submit_inventory_pin_v1_after_provider_absence(self):
        before = self.snapshot()
        observed = op.campaign_inventory(self.client, self.request, self.grant, self.ledger)
        proof = self.proof()
        self.assertTrue(proof["job_absent"])
        self.assertEqual(proof["job"], self.request["job"])
        self.assertEqual(proof["intent_sha256"], digest(self.intent))
        self.assertEqual(observed["inputs"]["kernel_sources"], [self.input_job+"/1"])
        self.assertEqual(self.calls, [{"userName": "nguynanhtn", "kernelSlug": "safeshift-prepare-internvl35",
            "versionLabel": "v1"}]*2)
        self.assertEqual(self.status_calls, [self.input_job+"/1"]*2)
        self.assertEqual(self.snapshot(), before)

    def test_wrong_missing_public_and_mismatched_input_metadata_block_abort(self):
        original = deepcopy(self.metadata)
        for metadata in (None, {}, {**original, "ref": "other/wrong"},
                {**original, "currentVersionNumber": 2}, {**original, "currentVersionNumber": None},
                {**original, "currentVersionNumber": True},
                {**original, "isPrivate": False}, {**original, "isPrivate": None}):
            with self.subTest(metadata=metadata):
                self.metadata = metadata
                self.assert_blocked_without_mutation()
                self.assertEqual(self.calls[-1]["versionLabel"], "v1")

    def test_noncomplete_or_unknown_input_status_blocks_abort(self):
        for state in ("RUNNING", "QUEUED", "ERROR", "CANCELLED", "UNKNOWN", None):
            with self.subTest(state=state):
                self.statuses[self.input_job+"/1"] = state
                self.assert_blocked_without_mutation()

    def test_malformed_or_unversioned_input_never_reaches_get_kernel(self):
        for suffix in ("", "/", "/0", "/01", "/v1", "/latest", "/-1", "/1/2"):
            with self.subTest(suffix=suffix):
                self.request["bindings"]["dataset"]["kernel_sources"] = [self.input_job+suffix]
                with self.assertRaisesRegex(ValueError, "VERSIONED_INPUT"):
                    self.proof()
        self.assertEqual(self.calls, [])

    def test_get_kernel_timeout_and_404_stop_once_and_never_abort_or_retry(self):
        for failure in (requests.ReadTimeout, requests.ConnectionError):
            self.provider_failure = failure; self.calls.clear()
            self.assert_blocked_without_mutation()
            self.assertEqual(len(self.calls), 1)
        self.provider_failure = None; self.calls.clear()
        # A regression to the old serializer must fail, not recover via latest.
        with patch.object(op, "kernel_version_label", return_value="1"):
            self.assert_blocked_without_mutation()
        self.assertEqual([c["versionLabel"] for c in self.calls], ["1"])

    def test_paginated_inventory_detects_existing_job_and_unknown_campaign_history(self):
        for ref in (self.request["job"], self.request["job"]+"-orphan"):
            with self.subTest(ref=ref):
                self.pages = [NS(kernels=[NS(ref="nguynanhtn/unrelated")], next_page_token="2"),
                    NS(kernels=[NS(ref=ref)], next_page_token=None)]
                self.page_calls.clear()
                self.assert_blocked_without_mutation()
                self.assertEqual([c["page_token"] for c in self.page_calls], [None, "2"])
        self.assertEqual(self.calls, [])

    def test_unknown_incomplete_or_repeated_provider_inventory_blocks_abort(self):
        with patch.object(self.client, "kernels_list_with_response", side_effect=requests.ReadTimeout):
            self.assert_blocked_without_mutation()
        self.pages = [NS(kernels=[], next_page_token="2")]
        self.assert_blocked_without_mutation()
        self.pages = [NS(kernels=[], next_page_token=str(i+1)) for i in range(1, 17)]
        self.assert_blocked_without_mutation()
        self.assertEqual(self.calls, [])

    def test_reserved_insufficient_and_invalid_quota_block_after_valid_v1(self):
        for used, reserved, total in ((0, 1, 10000), (0, 0, 3599), (10001, 0, 10000), (-1, 0, 10000)):
            with self.subTest(used=used, reserved=reserved, total=total):
                self.quota.time_used = timedelta(seconds=used)
                self.quota.time_reserved = timedelta(seconds=reserved)
                self.quota.total_time_allowed = timedelta(seconds=total)
                self.assert_blocked_without_mutation()
                self.assertEqual(self.calls[-1]["versionLabel"], "v1")

    def test_synthetic_abort_requires_complete_proof_preserves_intent_and_all_reservations(self):
        result = self.ledger.abort_pre_submit()
        self.assertEqual(result["kind"], "ABORTED_PRE_SUBMIT")
        self.assertFalse(result["refund"])
        self.assertEqual(self.ledger.intents(), [self.intent])
        self.assertEqual([x["kind"] for x in self.ledger.events()], ["INTENT", "ABORTED_PRE_SUBMIT"])
        self.assertEqual(self.ledger.summary()["reserved_calls"], 1)
        self.assertEqual(self.ledger.summary()["reserved_gpu_seconds"], 3600)
        self.assertEqual(self.ledger.summary()["jobs"], 1)
        self.assertIsNone(self.ledger.open_intent())

    def test_push_intent_prevents_abort_before_any_provider_query(self):
        self.ledger.append("PUSH_INTENT", intent_sha256=digest(self.intent), inventory_sha256="e"*64)
        self.assert_blocked_without_mutation()
        self.assertEqual(self.page_calls, [])
        self.assertEqual(self.calls, [])

    def test_grant_drift_blocks_reconciliation_before_any_provider_query(self):
        with patch.object(campaign, "load", return_value={"notice": "WRONG_SYNTHETIC_GRANT"}):
            self.assert_blocked_without_mutation()
        self.assertEqual(self.page_calls, [])
        self.assertEqual(self.calls, [])

    def test_next_job_retains_latest_version_drift_guard_for_prior_campaign_job(self):
        # This existing latest-only observation is a drift guard, not a fallback
        # for the explicitly pinned source/predecessor GetKernel requests.
        previous = deepcopy(self.intent)
        previous["request"]["job"] = self.request["job"]+"-previous"
        self.latest_job = previous["request"]["job"]
        self.latest_metadata = {"ref": self.latest_job, "currentVersionNumber": 1, "isPrivate": True}
        self.pages = [NS(kernels=[NS(ref=self.latest_job)], next_page_token=None)]
        ledger = NS(grant=self.grant, intents=lambda: [previous, self.intent],
            events=lambda: [{"kind": "PUSH_INTENT", "intent_sha256": digest(previous)}])
        with patch.object(op, "campaign_revision_code", return_value=op.code_hash(self.notebook)):
            op.campaign_inventory(self.client, self.request, self.grant, ledger)
            self.assertEqual(self.calls[-2]["versionLabel"], "v1")
            self.assertNotIn("versionLabel", self.calls[-1])
            for change in ({"currentVersionNumber": 2}, {"currentVersionNumber": None},
                    {"ref": "nguynanhtn/wrong"}, {"isPrivate": False}):
                original = deepcopy(self.latest_metadata)
                self.latest_metadata.update(change)
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_RUNNING_UNKNOWN_OR_CHANGED"):
                    op.campaign_inventory(self.client, self.request, self.grant, ledger)
                self.latest_metadata = original
            self.statuses[self.latest_job+"/1"] = "UNKNOWN"
            with self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_RUNNING_UNKNOWN_OR_CHANGED"):
                op.campaign_inventory(self.client, self.request, self.grant, ledger)
            self.statuses.clear()
            self.pages = [NS(kernels=[], next_page_token=None)]
            with self.assertRaisesRegex(ValueError, "PROVIDER_CAMPAIGN_HISTORY"):
                op.campaign_inventory(self.client, self.request, self.grant, ledger)

    def predecessor(self, version=1):
        _, grant, _ = legacy_fixture()
        previous = {"source_sha256": grant["source_sha256"], "job": "nguynanhtn/synthetic-previous",
            "version": version, "notebook_code_sha256": op.code_hash(self.notebook)}
        grant["predecessors"] = [digest(previous)]
        self.metadata = {"ref": previous["job"], "currentVersionNumber": version, "isPrivate": True}
        return grant, previous

    def test_legacy_predecessor_serializes_pinned_v1_and_v12_and_checks_exact_code(self):
        for version in (1, 12):
            with self.subTest(version=version):
                grant, previous = self.predecessor(version)
                request = deepcopy(self.request)
                request["bindings"]["dataset"]["kernel_sources"] = []
                with patch.object(authority, "http", return_value={"witness_id": grant["witness_id"], "claims": {"submit": previous}}):
                    op.inventory(self.client, request, grant)
                self.assertEqual(self.calls[-1], {"userName": "nguynanhtn", "kernelSlug": "synthetic-previous",
                    "versionLabel": "v"+str(version)})
                self.assertIn(previous["job"]+"/"+str(version), self.status_calls)

    def test_legacy_predecessor_rejects_version_privacy_ref_code_and_nonterminal_drift(self):
        grant, previous = self.predecessor()
        original = deepcopy(self.metadata)
        with patch.object(authority, "http", return_value={"witness_id": grant["witness_id"], "claims": {"submit": previous}}):
            for change in ({"currentVersionNumber": 2}, {"currentVersionNumber": None}, {"currentVersionNumber": True},
                    {"ref": "nguynanhtn/wrong"}, {"isPrivate": False}):
                self.metadata = {**original, **change}
                with self.subTest(change=change), self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_IDENTITY"):
                    op.inventory(self.client, self.request, grant)
            self.metadata = None
            with self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_IDENTITY"):
                op.inventory(self.client, self.request, grant)
            self.metadata = original
            self.notebook["cells"][0]["source"] = ["print('WRONG_CODE')"]
            with self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_IDENTITY"):
                op.inventory(self.client, self.request, grant)
            for state in ("RUNNING", "QUEUED", "UNKNOWN", None):
                self.statuses[previous["job"]+"/1"] = state
                self.calls.clear()
                with self.subTest(state=state), self.assertRaisesRegex(ValueError, "PREVIOUS_JOB_RUNNING"):
                    op.inventory(self.client, self.request, grant)
                self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
