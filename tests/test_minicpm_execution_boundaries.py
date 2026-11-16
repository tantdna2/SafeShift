"""Actual child CLI/capability wiring with synthetic authority/stage boundaries."""
import sys
import time
import unittest
from unittest.mock import patch

import test_minicpm_fulltrain_execution as fixtures
from safeshift.fulltrain import minicpm_execution as entry, minicpm_release as a, contract
from safeshift.pilot.artifacts import write


class ChildBoundaryTests(unittest.TestCase):
    setUpClass=classmethod(fixtures.ExecutionTests.setUpClass.__func__)
    tearDownClass=classmethod(fixtures.ExecutionTests.tearDownClass.__func__)
    setUp=fixtures.ExecutionTests.setUp
    make_ticket=fixtures.ExecutionTests.make_ticket

    def argv(self,context,request):
        return ["minicpm_execution","--stage","native","--request",str(request),"--repo",str(entry.ROOT),
            "--output",str(self.root/"native-output"),"--deadline",str(time.monotonic()+60),
            "--capability",str(context),"--release-comment-id","1","--release-body-sha256","f"*64]

    def context(self):
        context,request=self.root/"context.json",self.root/"request.json"
        write(context,{"locator":self.locator,"ticket":self.ticket,"value":self.value})
        write(request,self.value["request"])
        return context,request

    def test_actual_child_cli_installs_capability_and_rejects_replay(self):
        context,request=self.context()
        seen=[]
        def stage(mode,value,repo,output,deadline):
            seen.append((mode,a.current()["phase"]))
            contract.authorize(request=value)
            return "SYNTHETIC_STAGE_BOUNDARY"
        with patch.object(a,"CLAIMS",self.root/"claims"),patch.object(a,"load",return_value=self.grant), \
                patch("safeshift.fulltrain.admission.stage",side_effect=stage) as target,patch.object(sys,"argv",self.argv(context,request)):
            with a._activated(self.grant,self.locator,self.ticket,self.value,"launch"):pass
            for phase in a.STAGES[1:-1]:
                with a._activated(self.grant,self.locator,self.ticket,self.value,phase,child=True):pass
            self.assertEqual(entry.main(),"SYNTHETIC_STAGE_BOUNDARY")
            self.assertEqual(seen,[("native","native")])
            target.reset_mock()
            with self.assertRaises(FileExistsError):entry.main()
            target.assert_not_called()
        with self.assertRaises(PermissionError):contract.authorize()

    def test_signed_local_context_without_authenticated_launch_cannot_start_child(self):
        context,request=self.context()
        with patch.object(a,"CLAIMS",self.root/"absent-claims"),patch.object(a,"load",return_value=self.grant), \
                patch("safeshift.fulltrain.admission.stage") as stage,patch.object(sys,"argv",self.argv(context,request)):
            with self.assertRaises(FileNotFoundError):entry.main()
            stage.assert_not_called()


if __name__=="__main__":unittest.main()
