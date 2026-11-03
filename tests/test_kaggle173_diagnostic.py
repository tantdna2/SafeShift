"""Synthetic control/format tests; never model weights or real predictions."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
from scripts import diagnostic173 as d
from safeshift.smoke173_history import launch,worker


class DiagnosticTests(unittest.TestCase):
    def test_original_id_and_qwen_cannot_dispatch(self):
        for value in ('issue173-smoke-20261102-v5','qwen3','fresh171','minicpm4',''):
            with self.assertRaises(ValueError): d.admit(value)

    def test_declared_budgets(self):
        self.assertEqual(sum(len(p['variants']) for p in d.PLANS.values()),6)
        self.assertEqual(d.admit('issue173-diag-mini-synthetic-v1')['variants'],['frozen-c1'])

    def test_fences_not_rescued(self):
        raw={'response':'```json\n{"safety_level":"Level04"}\n```'}
        for variant in ('frozen-c1','reminder-v1','prefill-v1'):
            result=d.evaluate(raw,variant)
            self.assertEqual(result['native_status'],'INVALID')
            self.assertFalse(result['posthoc_cleanup'])

    def test_prefill_never_claims_suffix_is_native_json(self):
        result=d.evaluate({'response':'Level04"}'},'prefill-v1')
        self.assertEqual(result['native_status'],'INVALID')
        self.assertEqual(result['assistant_message_status'],'SUCCESS')
        self.assertEqual(result['scientific_status'],'PROPOSED_NON_EQUIVALENT')

    def test_exact_native_json_and_extra_keys(self):
        self.assertEqual(d.evaluate({'response':'{"safety_level":"Level04"}'},'reminder-v1')['native_status'],'SUCCESS')
        for response in ('{"safety_level":"Level04","x":1}','{"safety_level":"Level04","safety_level":"Level04"}','Level04'):
            self.assertEqual(d.evaluate({'response':response},'frozen-c1')['native_status'],'INVALID')

    def test_remaining_train_fenced_even_with_diagnostic_pass(self):
        for fn in (launch,worker):
            with self.assertRaisesRegex(PermissionError,'REVIEW'):
                fn({'status':'NATIVE_FORMAT_PASS','weights_loaded':True,'approved':True})

    def test_prepared_train_dispatch_all_entries_hold_before_io(self):
        from scripts import minicpm173_train_review as train
        with tempfile.TemporaryDirectory() as temp,patch.object(train,'bind_original') as inputs:
            for fn,args in ((train.once,(temp,Path(temp))),
                (train.worker,('native',temp,Path(temp),Path(temp))),
                (train.launch,(temp,temp,temp,'1'*40,{}))):
                with self.assertRaisesRegex(PermissionError,'REVIEW'): fn(*args)
            inputs.assert_not_called()
            self.assertEqual(list(Path(temp).iterdir()),[])

    def test_manifest_required_and_bad_path(self):
        for manifest in ({},{'../outside':'0'*64},{'C:/outside':'0'*64}):
            with self.assertRaises(ValueError): d.source_check(manifest)

    def test_worker_rejects_undeclared_before_input_reads(self):
        with patch.object(d,'read',return_value={'identity':'original-train'}),patch.object(d,'inspect_history') as history:
            with self.assertRaises(ValueError): d.worker('native','unused',Path('unused'),Path('unused'))
            history.assert_not_called()

    def test_empty_vm_terminal_routes_still_block(self):
        from scripts.smoke_kaggle173 import launch as original
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(PermissionError): original(root,root,root,'0'*40)
            self.assertEqual(list(Path(root).iterdir()),[])

    def test_reminder_changes_only_declared_suffix_and_pixels(self):
        prompt=(d.ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
        proc=Mock(); proc.apply_chat_template.return_value='HEAD'+prompt+d.REMINDER+'TAIL'
        pixels=object(); proc.return_value={'pixel_values':pixels}
        original=Mock(return_value=('HEAD'+prompt+'TAIL',{'pixel_values':pixels}))
        fake_torch=Mock(); fake_torch.equal.return_value=True
        with patch.dict('sys.modules',{'torch':fake_torch}):
            rendered,values=d.variant_inputs(original,'reminder-v1')(proc,'internvl35',prompt,object())
        self.assertEqual(rendered.replace(d.REMINDER,''),'HEAD'+prompt+'TAIL')
        fake_torch.equal.assert_called_once_with(pixels,pixels)
        self.assertEqual(proc.apply_chat_template.call_args.kwargs,{'tokenize':False,'add_generation_prompt':True})

    def test_uncertain_native_completion_is_sealed_and_never_retried(self):
        from safeshift.pilot.artifacts import write,verify_archive
        identity='issue173-diag-mini-synthetic-v1'
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'output'; output.mkdir()
            scratch=Path(temp)/'scratch'; scratch.mkdir()
            out=output/identity
            calls=[]
            def run(command,**kwargs):
                stage=command[command.index('--worker')+1]; calls.append(stage)
                if stage=='setup':
                    write(out/'runtime.json',{'python':'NOT_EXECUTED','env':{}})
                else:
                    write(out/'load-reservation.json',{'loads':1})
                    sample=out/'calls/frozen-c1'; sample.mkdir(parents=True)
                    write(sample/'reservation.json',{'max_calls':1})
                    write(sample/'native_call.json',{'invocation':1})
                    raise TimeoutError('SYNTHETIC_UNKNOWN_AFTER_CALL')
            history={'consumed':{'qwen3':1,'internvl35':1,'minicpm4':0}}
            with patch.object(d,'source_check'),patch.object(d,'paths_from_mounts',return_value=[]),\
                 patch.object(d,'inspect_history',return_value=history),patch.object(d,'memory',return_value={}),\
                 patch.object(d.environment,'resources',return_value={}),patch.object(d.provision,'clean_env',return_value={}),\
                 patch.object(d,'advise_owned_runtime',return_value={}),patch.object(d.supervision,'run',side_effect=run):
                result=d.launch(identity,'unused',output,scratch,'1'*40,{'synthetic':'2'*64})
                self.assertEqual(result['status'],'BLOCKED')
                self.assertEqual(result['native_call_markers'],1)
                self.assertEqual(result['call_reservations'],1)
                self.assertEqual(calls,['setup','native'])
                with self.assertRaises(FileExistsError):
                    d.launch(identity,'unused',output,scratch,'1'*40,{'synthetic':'2'*64})
            self.assertIn('calls/frozen-c1/native_call.json',verify_archive(Path(str(out)+'.zip')))
            self.assertFalse((out/'native-result.json').exists())


if __name__=='__main__': unittest.main()
