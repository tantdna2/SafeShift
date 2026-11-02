"""Synthetic no-dataset checks for the Issue173 observation/export boundary."""
import json
import io
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import subprocess

from scripts import observe_kaggle173 as o


class ObservationTests(unittest.TestCase):
    def test_software_setup_failure_seals_evidence_and_never_reaches_cpu_gpu(self):
        from scripts import qualify_kaggle173_software as q
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch.object(q.supervision,'run',side_effect=RuntimeError('synthetic setup failure')) as run:
                out=q.launch(root/'out',root/'scratch','a'*40)
            self.assertEqual(run.call_count,3)
            for call in run.call_args_list:
                argv=call.args[0]
                self.assertEqual(argv[argv.index('--worker')+1],'setup')
                self.assertEqual(call.kwargs['env']['CUDA_VISIBLE_DEVICES'],'')
            result=json.loads((out/'result.json').read_text())
            self.assertEqual(result['model_calls'],0)
            self.assertFalse(result['inputs_attached'])
            self.assertTrue(all(v['stage']=='setup' and v['status']=='BLOCKED' for v in result['models'].values()))
            from safeshift.pilot.artifacts import verify_archive
            names=verify_archive(Path(str(out)+'.zip'))
            self.assertIn('qwen3/failure.json',names)
            self.assertNotIn('qwen3/cpu.json',names)
            self.assertFalse(any('attempt' in n or 'consumption' in n for n in names))

    def test_official_wheel_cdn_and_nvidia_reject_spoofed_hosts(self):
        from scripts.qualify_kaggle173_software import wheel_location
        rows=[('torch','https://download-r2.pytorch.org/whl/cu128/torch-2.whl'),
              ('jinja2','https://download.pytorch.org/whl/jinja2-3.1.6-py3-none-any.whl'),
              ('nvidia-cublas-cu12','https://pypi.nvidia.com/nvidia-cublas-cu12/nvidia.whl')]
        for name,url in rows:
            self.assertEqual(wheel_location({'name':name,'url':url,'sha256':'a'*64})[0],name)
        for url in ('http://download.pytorch.org/whl/torch.whl',
                    'https://download-r2.pytorch.org.evil.invalid/whl/torch.whl',
                    'https://user:password@download.pytorch.org/whl/torch.whl',
                    'https://download.pytorch.org/whl/%2Ftorch.whl',
                    'https://pypi.nvidia.com/torch/torch.whl'):
            with self.assertRaises(ValueError):
                wheel_location({'name':'torch','url':url,'sha256':'a'*64})

    def test_software_bundle_all_paths_committed_and_cells_compile(self):
        from scripts.build_kaggle173_notebook import build_software, ROOT
        ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        nb=build_software(ref)
        self.assertEqual(nb['metadata']['safeshift']['source_commit'],ref)
        self.assertEqual(nb['metadata']['safeshift']['inputs'],[])
        for cell in nb['cells']:
            if cell['cell_type']=='code':
                compile(''.join(cell['source']),'<notebook>','exec')
                self.assertEqual(cell['outputs'],[])

    def test_mutable_notebook_ref_rejected(self):
        from scripts.build_kaggle173_notebook import build, build_software
        for builder in (build, build_software):
            with self.assertRaises(ValueError):
                builder('HEAD')

    def test_public_download_rejects_hash_and_size_preserves_bytes(self):
        from scripts.prepare_qwen173_software import download
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'synthetic')):
                with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
                    download('https://example.invalid/source',root/'bad', 'a'*64)
            self.assertEqual((root/'bad').read_bytes(),b'synthetic')
            with patch('urllib.request.urlopen',return_value=io.BytesIO(b'12345')):
                with self.assertRaisesRegex(ValueError,'SIZE_BOUND'):
                    download('https://example.invalid/source',root/'large', 'a'*64,max_bytes=4)
            self.assertTrue((root/'large').exists())
            payload=b'synthetic'
            with patch('urllib.request.urlopen',return_value=io.BytesIO(payload)):
                row=download('https://example.invalid/source',root/'ok',hashlib.sha256(payload).hexdigest())
            self.assertEqual(row['size'],len(payload))

    def test_repeat_and_failure_retained_without_gpu_or_model(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(o, 'memory', side_effect=OSError('synthetic memory failure')), \
                 patch.object(o, 'command', side_effect=AssertionError('must not call GPU')), \
                 patch.object(o.metadata, 'version', return_value='synthetic'):
                first = o.observe(root / 'out', root / 'scratch', source_commit='a'*40, gpu=False)
                before = (first / 'observation.json').read_bytes()
                second = o.observe(root / 'out', root / 'scratch', source_commit='a'*40, gpu=False)
            self.assertNotEqual(first, second)
            self.assertEqual(before, (first / 'observation.json').read_bytes())
            report = json.loads(before)
            self.assertEqual(report['status'], 'OBSERVED_WITH_FAILURES')
            self.assertEqual(report['model_calls'], 0)
            self.assertFalse(report['weights_loaded'])
            self.assertFalse(report['dataset_accessed'])
            self.assertFalse(report['owner_slot_consumed'])
            self.assertEqual(report['checks']['kernel_cuda_tensor_only']['status'], 'NOT_RUN')
            archive = Path(str(first) + '.zip')
            seal = json.loads(Path(str(archive)+'.sha256.json').read_text())
            self.assertEqual(seal['sha256'], o.sha(archive))
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                hashes = json.loads(z.read('checksums.json'))
                self.assertEqual(hashes['observation.json'], o.sha(first / 'observation.json'))
            self.assertEqual(list((root / 'scratch').iterdir()), [])

    def test_partial_allocation_cleanup_and_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FileNotFoundError):
                o.allocation(root, root / 'absent', 4096)
            self.assertEqual(list(root.iterdir()), [])
            for bad in (0, -1, True, 17*2**20):
                with self.assertRaises(ValueError):
                    o.allocation(root, root, bad)

    def test_invalid_commit_before_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                o.observe(Path(temp)/'out', Path(temp)/'scratch', source_commit='main', gpu=False)
            self.assertEqual(list(Path(temp).iterdir()), [])
