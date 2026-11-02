"""Synthetic no-dataset checks for the Issue173 observation/export boundary."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts import observe_kaggle173 as o


class ObservationTests(unittest.TestCase):
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
