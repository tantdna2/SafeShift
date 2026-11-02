"""Synthetic single-call journal tests, no model imports or live execution."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from safeshift.pilot.artifacts import write,read
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


if __name__=='__main__': unittest.main()
