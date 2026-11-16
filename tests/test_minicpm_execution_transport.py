"""Actual pinned SDK serialization/HTTP-adapter doubles, no real network."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

import test_train3763_manual as manual
import test_minicpm_ui_transport as pair_tests
from scripts.minicpm_fulltrain_transport import fetch_outputs
from safeshift.pilot.artifacts import read, sha


@unittest.skipUnless(manual.KaggleClient is not None,"requires existing pinned SDK environment")
class FirstCollectionTests(unittest.TestCase):
    setUp = manual.ManualDownloadTests.setUp
    pairs = pair_tests.MiniCPMPairTransportTests.pairs

    def value(self):
        return {"job":"nguynanhtn/synthetic-mini","request":{"plan":{"run_id":self.archive.stem}}}

    def test_first_download_reuses_sdk_inventory_and_exact_four_gets(self):
        pairs=self.pairs()
        attempt,supervisor=fetch_outputs(self.client,self.value(),self.root/"first",16*2**20)
        self.assertEqual(attempt.read_bytes(),self.archive.read_bytes())
        self.assertEqual(len(self.transport.gets),4)
        self.assertEqual(read(str(supervisor)+".sha256.json")["sha256"],sha(supervisor))

    def test_extra_late_pair_or_bad_url_blocks_before_download(self):
        pairs=self.pairs();saved=deepcopy(self.transport.output)
        for i,mutate in enumerate((lambda v:v["files"].append({"fileName":"extra.zip","url":"invalid"}),
                                   lambda v:v["files"][0].update(url="https://evil.invalid/extra.zip"))):
            self.transport.output=deepcopy(saved);mutate(self.transport.output)
            with self.subTest(i=i),self.assertRaises(ValueError):
                fetch_outputs(self.client,self.value(),self.root/f"blocked-{i}",16*2**20)
            self.assertEqual(self.transport.gets,[])

    def test_sidecar_mismatch_retains_download_and_blocks_acceptance(self):
        self.pairs()
        self.transport.payloads[self.archive.name+".sha256.json"]=b'{"sha256":"wrong"}'
        output=self.root/"bad"
        with self.assertRaisesRegex(ValueError,"PROVIDER_ZIP_SHA"):fetch_outputs(self.client,self.value(),output,16*2**20)
        self.assertTrue((output/"minicpm-fulltrain"/self.archive.name).exists())

    def test_pinned_sdk_create_response_uses_status_and_error_fields(self):
        from kagglesdk.datasets.types.dataset_api_service import ApiCreateDatasetResponse
        from scripts.minicpm_fulltrain_operator import check_create_response
        response=ApiCreateDatasetResponse()
        response.status="ok";response.error=""
        check_create_response(response)
        response.status="error";response.error="already exists"
        with self.assertRaisesRegex(ValueError,"CREATE_FAILED_NO_RETRY"):check_create_response(response)


if __name__=="__main__":unittest.main()
