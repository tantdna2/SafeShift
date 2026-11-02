"""Synthetic no-dataset checks for the Issue173 observation/export boundary."""
import json
import io
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import observe_kaggle173 as o


class ObservationTests(unittest.TestCase):
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
