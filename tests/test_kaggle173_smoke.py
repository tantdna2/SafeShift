"""Synthetic single-call journal tests, no model imports or live execution."""
from pathlib import Path
import subprocess
import sys
import os
import time
import tempfile
import unittest
from unittest.mock import Mock, patch

from safeshift.pilot.artifacts import write,read,sha,export
from scripts import smoke_kaggle173 as smoke


class SmokeJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.out=Path(self.temp.name)/'model'; self.out.mkdir()
        self.row={'sample_id':'synthetic','image_sha256':'a'*64,'image':'SYNTHETIC_NOT_OPENED'}

    def backend(self,response='{"safety_level":"Level04"}'):
        backend=Mock(); backend.environment={'scope':'SYNTHETIC_ONLY'}
        def generate(image,sample):
            write(sample/'native_call.json',{'invocation':1,'max_new_tokens':64})
            return {'response':response,'raw_nonfinite':False,'generated_ids':[1,2],
                'cpu_tokenizer_replay':{'status':'PASS'}}
        backend.generate.side_effect=generate
        return backend

    def test_raw_durable_before_parser_and_hnlo_single_call(self):
        backend=self.backend(); factory=Mock(return_value=backend)
        def parse(text):
            self.assertEqual(read(self.out/'sample/raw.json')['response'],text)
            return 'Level04'
        with patch.object(smoke,'parse_label',side_effect=parse),patch('safeshift.pilot.hnlo.replay',return_value={'hnlo':None}):
            result=smoke.once(self.out,self.row,factory,'internvl35')
        self.assertEqual(result['native_calls'],1); backend.generate.assert_called_once(); factory.assert_called_once()
        self.assertEqual(read(self.out/'sample/raw.json')['smoke_identity']['ordinal'],0)
        with self.assertRaises(FileExistsError): smoke.once(self.out,self.row,factory,'internvl35')
        factory.assert_called_once()

    def test_load_failure_reservation_survives_and_no_retry(self):
        factory=Mock(side_effect=RuntimeError('SYNTHETIC_LOAD_FAILURE'))
        with self.assertRaisesRegex(RuntimeError,'SYNTHETIC_LOAD'): smoke.once(self.out,self.row,factory,'internvl35')
        self.assertTrue((self.out/'model-load-reservation.json').is_file())
        with self.assertRaises(FileExistsError): smoke.once(self.out,self.row,factory,'internvl35')
        factory.assert_called_once()

    def test_hnlo_failure_preserves_classification_and_stops(self):
        backend=self.backend()
        with patch('safeshift.pilot.hnlo.replay',side_effect=ValueError('SYNTHETIC_ALIGNMENT_FAILURE')):
            with self.assertRaisesRegex(ValueError,'CLASSIFICATION_PRESERVED'):
                smoke.once(self.out,self.row,lambda:backend,'internvl35')
        self.assertEqual(read(self.out/'sample/result.json')['status'],'SUCCESS')
        self.assertEqual(read(self.out/'sample/result.json')['hnlo']['replay_status'],'FAIL')

    def test_invalid_is_durable_and_minicpm_does_not_seek_hnlo(self):
        backend=self.backend('```json\n{"safety_level":"Level04"}\n```')
        with patch('safeshift.pilot.hnlo.replay',side_effect=AssertionError('NO_HNLO_SEARCH')):
            result=smoke.once(self.out,self.row,lambda:backend,'minicpm4')
        self.assertEqual(result['status'],'INVALID'); self.assertIsNone(result['label'])
        self.assertEqual(result['hnlo'],{'status':'LABEL_ONLY_OWNER_DECISION','hnlo':None})
        self.assertEqual(read(self.out/'sample/result.json')['status'],'INVALID')

    def test_missing_pin_blocks_before_private_inputs(self):
        with (patch.object(smoke,'read',side_effect=FileNotFoundError('NO_COMMITTED_PROOF_PIN')),
                patch.object(smoke,'unique_mount',side_effect=AssertionError('NO_PRIVATE_READ'))):
            with self.assertRaises(FileNotFoundError): smoke.launch('/kaggle/input','/kaggle/working','/kaggle/temp','a'*40)

    def test_direct_worker_rejects_arbitrary_call_scope_before_model_import(self):
        for calls,ordinal in ((2,0),(1,1),(160,0)):
            with self.subTest(calls=calls,ordinal=ordinal):
                with patch.object(smoke,'read',return_value={'directive':smoke.DIRECTIVE,'max_native_calls':calls,'ordinal':ordinal}),\
                        patch.object(smoke,'scope',side_effect=AssertionError('NO_INPUTS_OR_MODEL')):
                    with self.assertRaisesRegex(ValueError,'SMOKE_ONLY_SCOPE'):
                        smoke.worker('internvl35','native','unused',self.out,self.out)

    def test_forged_first_image_rejected_by_direct_worker(self):
        pin={'resource_policy':{}}
        request={'directive':smoke.DIRECTIVE,'max_native_calls':1,'ordinal':0,'model_key':'internvl35',
            'row':{'sample_id':'forged'}}
        with patch.object(smoke,'read',return_value=request),patch.object(smoke,'scope',return_value=(pin,self.row)):
            with self.assertRaisesRegex(ValueError,'WORKER_EXACT_ORIGINAL_SCOPE'):
                smoke.worker('internvl35','native','unused',self.out,self.out)

    def test_consumed_qwen_direct_cli_cannot_load_or_read_private_inputs(self):
        with patch.object(smoke,'read',side_effect=AssertionError('NO_PRIVATE_READ')):
            with self.assertRaisesRegex(ValueError,'ALREADY_CONSUMED'):
                smoke.worker('qwen3','native','unused',self.out,self.out)

    def test_driver_exit12_is_preserved_and_remains_blocked(self):
        error=subprocess.CalledProcessError(12,['nvidia-smi'],output='SYNTHETIC_STDOUT',stderr='SYNTHETIC_NVML_FAILURE')
        with patch.object(smoke.environment,'hardware',side_effect=error),patch.object(smoke.ctypes.util,'find_library',return_value=None):
            with self.assertRaises(subprocess.CalledProcessError): smoke.driver_check('internvl35',{},self.out,'worker')
        receipt=read(self.out/'worker-driver-diagnostic.json')
        self.assertEqual(receipt['status'],'BLOCKED'); self.assertEqual(receipt['returncode'],12)
        self.assertEqual(receipt['stderr'],'SYNTHETIC_NVML_FAILURE')

    @unittest.skipUnless(sys.platform=='linux','real Linux process supervisor')
    def test_supervised_setup_does_not_collide_with_runtime_exclusive_log(self):
        code="from pathlib import Path; import sys; p=Path(sys.argv[1])/'setup.log'; p.open('x').write('SYNTHETIC_SETUP')"
        smoke.supervision.run([sys.executable,'-B','-c',code,str(self.out)],cwd=self.out,env=os.environ.copy(),
            deadline=time.monotonic()+20,log=smoke.supervisor_log(self.out,'setup'),
            receipt=self.out/'synthetic-supervisor.json',max_log_bytes=2**20)
        self.assertEqual((self.out/'setup.log').read_text(),'SYNTHETIC_SETUP')
        self.assertTrue(smoke.supervisor_log(self.out,'setup').is_file())

    def test_previous_zero_summary_cannot_hide_call_or_load_reservation(self):
        for marker in (None,'qwen3/sample/native_call.json','qwen3/model-load-reservation.json'):
            with self.subTest(marker=marker):
                root=self.out/str(len(list(self.out.iterdir()))); root.mkdir()
                value={'run_id':'issue173-smoke-20261102-v1','source_commit':'a'*40,'model_calls':0,
                    'models':{k:{'native_calls':0,'weights_loaded':False} for k in smoke.KEYS}}
                write(root/'summary.json',value)
                if marker: write(root/marker,{'SYNTHETIC':True})
                archive=root.with_suffix('.zip'); export(root,archive)
                pin={'prior_preload_failure_sha256':sha(archive),'prior_source_commit':'a'*40}
                if marker:
                    with self.assertRaisesRegex(ValueError,'PRIOR_LOAD_OR_CALL'): smoke.previous_preload_failure(archive,pin)
                else: self.assertEqual(smoke.previous_preload_failure(archive,pin),value)

    def test_reclamation_is_owned_only_retains_runtime_and_ram_floor(self):
        root=self.out/smoke.RUN_ID; root.mkdir()
        for name in ('existing-qwen-software','qwen3/qwen-software/python-source','qwen3/qwen-software/zlib-source'):
            p=root/name; p.mkdir(parents=True); (p/'SYNTHETIC_CACHE').write_bytes(b'cache')
        retained=root/'qwen3/qwen-software/venv/lib'; retained.mkdir(parents=True)
        binary=retained/'synthetic.so'; binary.write_bytes(b'synthetic retained runtime')
        witness=self.out/'historical-raw'; witness.write_bytes(b'KEEP_HISTORY')
        with patch.object(smoke.environment,'host_memory',side_effect=[{'available_bytes':100},{'available_bytes':200}]),\
                patch.object(smoke.os,'fsync'),patch.object(smoke.os,'posix_fadvise',create=True) as advice,\
                patch.object(smoke.os,'POSIX_FADV_DONTNEED',4,create=True):
            result=smoke.reclaim_setup_cache(root,self.out,minimum_bytes=1)
        self.assertEqual(len(result['removed_owned_cache_directories']),3)
        self.assertEqual(binary.read_bytes(),b'synthetic retained runtime'); advice.assert_called_once()
        self.assertEqual(witness.read_bytes(),b'KEEP_HISTORY')
        self.assertEqual(result['ram_floor_mib_unchanged'],16384)
        self.assertEqual(result['after']['available_bytes'],200)
        with self.assertRaisesRegex(ValueError,'OWNED_SCRATCH_ROOT'): smoke.reclaim_setup_cache(self.out,self.out)

    def test_notebook_committed_payload_compiles_without_outputs(self):
        from scripts.build_kaggle173_verification import build,ROOT
        with self.assertRaisesRegex(ValueError,'EXACT_COMMITTED_SOURCE'): build('main',smoke=True)
        ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        notebook=build(ref,smoke=True)
        for cell in notebook['cells']:
            if cell['cell_type']=='code':
                compile(''.join(cell['source']),'<smoke-notebook>','exec')
                self.assertEqual(cell['outputs'],[])
        self.assertEqual(notebook['metadata']['safeshift']['max_model_calls'],3)

    def test_new_release_pin_matches_source_and_keeps_prior_ram_budget(self):
        from safeshift.fulltrain.contract import source_manifest
        from safeshift.pilot.contract import digest
        pin=read(smoke.ROOT/'configs/issue173/real_smoke.json')
        self.assertEqual(pin['smoke_script_sha256'],sha(Path(smoke.__file__)))
        self.assertEqual(pin['source_inventory_sha256'],digest(source_manifest()))
        self.assertEqual(pin['resource_policy']['free_ram_mib'],16384)


if __name__=='__main__': unittest.main()
