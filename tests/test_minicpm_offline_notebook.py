"""Exact-source V7 builder and PR201 byte preservation; no notebook execution."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unittest
import zlib

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import contract
from safeshift.pilot.contract import digest
from scripts.generate_minicpm_fulltrain_notebook import notebook


class OfflineNotebookTests(unittest.TestCase):
    def test_v7_reproducible_payload_and_same_native_entrypoint(self):
        ref=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
        args={"capsule_sha256":"a"*64,"release_locator":{"comment_id":1,"body_sha256":"b"*64},"release_version":7}
        first=notebook(ref,**args)
        self.assertEqual(first,notebook(ref,**args))
        meta=first["metadata"]["safeshift"]
        self.assertEqual(meta["source_sha256"],digest(contract.source_manifest()))
        self.assertEqual(meta["resource_stages"],["admit","setup","reclaim","cpu","gpu","native"])
        self.assertEqual(meta["continuation_route"],"safeshift-minicpm-offline-continuation-v2")
        code="\n".join("".join(cell["source"]) for cell in first["cells"] if cell["cell_type"]=="code")
        self.assertIn("safeshift.fulltrain.minicpm_execution",code)
        payload=json.loads(zlib.decompress(base64.b64decode(re.search(r"base64\.b64decode\('([^']+)'\)",code).group(1))))
        self.assertIn("safeshift/fulltrain/minicpm_offline.py",payload)
        self.assertFalse(any(name.startswith("scripts/") for name in payload))
        for name,text in payload.items():
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),contract.source_manifest()[name])
            if name.endswith(".py"):compile(text,name,"exec")
        for cell in first["cells"]:
            if cell["cell_type"]=="code":
                compile("".join(cell["source"]),cell.get("id","cell"),"exec")
                self.assertEqual(cell["outputs"],[])

    def test_pr201_ram_supervisor_native_and_historical_notebooks_unchanged(self):
        base="e713d56d62a5a649a2078f2c2376fde6d025b978"
        protected=("safeshift/fulltrain/memory.py","safeshift/fulltrain/supervision.py",
            "safeshift/fulltrain/environment.py","safeshift/fulltrain/runtime.py","safeshift/fulltrain/admission.py",
            "safeshift/candidates/backend.py","safeshift/candidates/minicpm_resampler_fp32.py",
            "safeshift/pilot/contract.py","notebooks/SafeShift_FULLTRAIN_MINICPM4_RAM_V6_CANDIDATE.ipynb",
            "notebooks/SafeShift_FULLTRAIN_MINICPM4_FP32.ipynb")
        for name in protected:
            with self.subTest(name=name):
                expected=subprocess.check_output(["git","show",base+":"+name],cwd=ROOT)
                self.assertEqual((ROOT/name).read_bytes(),expected)


if __name__=="__main__":unittest.main()
