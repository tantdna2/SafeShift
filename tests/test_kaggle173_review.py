"""Post-v5 terminal safety, synthetic INVALID diagnosis and RAM boundaries."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from safeshift.pilot.artifacts import write,sha,export
from safeshift.pilot.contract import parse_label,GENERATION
from safeshift import smoke173_history as history
from scripts import smoke_kaggle173 as smoke
from scripts import minicpm173_preflight as mini
from scripts.diagnose_internvl173 import diagnose
from scripts.build_kaggle173_verification import build


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def synthetic_history(self):
        paths=[]; pins=[]
        for i in range(1,6):
            out=self.root/f'synthetic{i}'; out.mkdir()
            counts={'qwen3':int(i==2),'internvl35':int(i==5),'minicpm4':0}
            summary={'run_id':f'issue173-smoke-20261102-v{i}','model_calls':sum(counts.values()),
                'models':{k:{'native_calls':n} for k,n in counts.items()}}
            for key,n in counts.items():
                if n:
                    sample=out/key/'sample'
                    raw_hash=write(sample/'raw.json',{'smoke_identity':{'sample_id':'SYNTHETIC','image_sha256':'a'*64}})
                    write(sample/'result.json',{'raw_sha256':raw_hash})
                    write(sample/'native_call.json',{'invocation':1})
            write(out/'summary.json',summary)
            archive=out.with_suffix('.zip'); export(out,archive)
            paths.append(archive); pins.append(sha(archive))
        return paths,tuple(pins)

    def test_five_sealed_attempts_reconcile_consumed_models_not_an_authority(self):
        paths,pins=self.synthetic_history()
        with patch.object(history,'ARCHIVES',pins):
            receipt=history.inspect_history(paths)
        self.assertEqual(receipt['consumed'],{'qwen3':1,'internvl35':1,'minicpm4':0})
        self.assertEqual(history.mini_only_request(receipt)['max_native_calls'],1)
        with self.assertRaisesRegex(ValueError,'ONLY_UNUSED'): history.mini_only_request(receipt,'internvl35')
        for fn in (history.launch,history.worker):
            with self.assertRaisesRegex(PermissionError,'PENDING_CHATGPT'): fn(receipt,approved=True)

    def test_missing_forged_or_reordered_v5_cannot_admit_history(self):
        paths,pins=self.synthetic_history()
        with patch.object(history,'ARCHIVES',pins):
            with self.assertRaisesRegex(ValueError,'ALL_FIVE'): history.inspect_history(paths[:4])
            with self.assertRaisesRegex(ValueError,'EXACT_SEAL'): history.inspect_history(paths[:4]+[paths[3]])
            paths[4].write_bytes(b'SYNTHETIC_TAMPERED_V5')
            with self.assertRaisesRegex(ValueError,'EXACT_SEAL'): history.inspect_history(paths)

    def test_empty_new_vm_old_history_or_forged_approval_never_loads(self):
        paths,pins=self.synthetic_history()
        for witness in ({'attempts':paths[:4]},{'attempts':paths,'signed_v5':True},{'approved':True},{}):
            for key in history.KEYS:
                with self.subTest(witness=len(witness),key=key),patch.object(smoke,'read',return_value=witness),\
                        patch.object(smoke,'qwen_flat_backend',side_effect=AssertionError('NO_LOAD')):
                    with self.assertRaisesRegex(PermissionError,'V5_TERMINAL'):
                        smoke.launch(str(self.root/'empty-input'),str(self.root/'empty-output'),str(self.root/'empty-scratch'),'a'*40)
                    with self.assertRaisesRegex(PermissionError,'V5_TERMINAL'):
                        smoke.worker(key,'native',self.root/'missing-request',self.root,self.root)
                    factory=Mock(side_effect=AssertionError('NO_FACTORY'))
                    with self.assertRaisesRegex(PermissionError,'V5_TERMINAL'): smoke.once(self.root,{},factory,key)
                    factory.assert_not_called()
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
            sorted([f'synthetic{i}'+suffix for i in range(1,6) for suffix in ('','.zip','.zip.sha256.json')]))

    def test_archival_notebook_refuses_before_any_import_or_filesystem_use(self):
        notebook=build('a'*40,smoke=True)
        cell=next(c for c in notebook['cells'] if c['cell_type']=='code')
        code=''.join(cell['source'])
        self.assertNotIn('base64',code); self.assertNotIn('launch',code)
        with self.assertRaisesRegex(PermissionError,'V5_TERMINAL'): exec(compile(code,'<new-vm>','exec'),{})
        self.assertEqual(notebook['metadata']['safeshift']['max_model_calls'],0)

    def test_direct_cli_refuses_on_empty_cwd_without_native_imports(self):
        env=os.environ.copy(); env['PYTHONPATH']=str(smoke.ROOT)
        command=[sys.executable,'-B','-m','scripts.smoke_kaggle173','--worker','native','--key','internvl35',
            '--request',str(self.root/'missing'),'--output',str(self.root/'new-out'),'--scratch',str(self.root/'new-scratch')]
        r=subprocess.run(command,cwd=self.root,env=env,text=True,capture_output=True,timeout=20)
        self.assertNotEqual(r.returncode,0); self.assertIn('V5_TERMINAL',r.stderr)
        self.assertFalse((self.root/'new-out').exists())
        from safeshift.fulltrain.contract import authorize
        with self.assertRaises(PermissionError): authorize(approved=True)

    def fixture(self):
        prompt=(smoke.ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
        ids=[7,8,99]; inputs=[2,2,2]
        # Deliberately synthetic label differs from the private actual prediction.
        text='```json\n{"safety_level":"Level03"}\n```'
        raw={'response':text,'generated_ids':ids,'input_ids':inputs,'steps':[{'all_finite':True,'argmax':n} for n in ids],
            'raw_nonfinite':False,'cpu_tokenizer_replay':{'status':'PASS'},'actual_logits_processors':[],'capture_error':None}
        request={'prompt':prompt,'rendered_prompt':'user\n'+prompt+'\n<|im_start|>assistant\n',
            'generation':{**GENERATION,'eos_token_id':99},'input_ids':inputs,
            'input_detail':{'pixel_shapes':[[1,3,448,448]],'tiles_including_thumbnail':1,'image_tokens':256,'input_length':3}}
        native={'input_ids':inputs,'generated_ids':ids,'returned_ids':[inputs+ids],'input_prefix_match':True}
        result={'status':'INVALID','label':None,'hnlo':{'status':'RAW_LOGITS_AVAILABLE_BUT_UNALIGNED'}}
        return raw,request,native,result,text,prompt

    def test_fence_is_generated_not_decode_or_capture_fault_and_never_rescued(self):
        args=self.fixture(); evidence=diagnose(*args)
        self.assertEqual(evidence['cause'],'MODEL_GENERATED_MARKDOWN_CODE_FENCE_CONTRARY_TO_C1')
        self.assertFalse(evidence['prediction_rescue_applied']); self.assertIsNone(parse_label(args[4]))
        self.assertNotIn('response',evidence)
        for field in ('argmax','all_finite'):
            bad=deepcopy(args); bad[0]['steps'][0][field]=0
            with self.assertRaises(ValueError): diagnose(*bad)
        bad=deepcopy(args); bad[2]['returned_ids'][0][-1]=42
        with self.assertRaisesRegex(ValueError,'CONTINUATION'): diagnose(*bad)
        bad=list(args); bad[4]='different decode'
        with self.assertRaisesRegex(ValueError,'DECODE_MISMATCH'): diagnose(*bad)

    def test_unchanged_ram_floor_boundary_and_minicpm_native_hold(self):
        self.assertEqual(mini.ram_gate({'available_bytes':16384*2**20})['required_bytes'],17179869184)
        for n in (0,13950664704,17179869183):
            with self.assertRaisesRegex(ValueError,'UNCHANGED_16GIB'): mini.ram_gate({'available_bytes':n})
        with self.assertRaisesRegex(ValueError,'PREFLIGHT_STAGES_ONLY'):
            mini.worker('native','missing',self.root,self.root)
        with self.assertRaisesRegex(PermissionError,'PENDING_CHATGPT'): history.worker(approved=True,max_calls=1)

    def test_owned_ram_advice_never_touches_checkpoint_or_raw(self):
        scratch=self.root/'issue173-minicpm-ram-synthetic'; scratch.mkdir()
        runtime=scratch/'owned-runtime.so'
        with runtime.open('wb') as stream: stream.truncate(8*2**20)
        outside=self.root/'checkpoint.safetensors'; outside.write_bytes(b'SYNTHETIC_CHECKPOINT_UNCHANGED')
        raw=self.root/'old-raw.json'; raw.write_bytes(b'SYNTHETIC_RAW_UNCHANGED')
        original=sha(runtime)
        with patch.object(mini.os,'fsync'),patch.object(mini.os,'posix_fadvise',create=True) as advise,patch.object(mini.os,'POSIX_FADV_DONTNEED',4,create=True):
            result=mini.advise_owned_runtime(scratch)
        advise.assert_called_once(); self.assertTrue(result['scan_complete'])
        self.assertEqual(result['deleted_files'],0); self.assertEqual(sha(runtime),original)
        self.assertEqual(outside.read_bytes(),b'SYNTHETIC_CHECKPOINT_UNCHANGED')
        self.assertEqual(raw.read_bytes(),b'SYNTHETIC_RAW_UNCHANGED')
        with self.assertRaisesRegex(ValueError,'OWNED_PREFLIGHT_ROOT'): mini.advise_owned_runtime(self.root)


if __name__=='__main__': unittest.main()
