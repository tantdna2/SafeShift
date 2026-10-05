"""Offline canonical bytes, pixel semantics and D9R20 portability regressions."""

from copy import deepcopy
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from safeshift.qualification.d9r20 import runtime as r
from scripts import verify_grounding_multicategory_v4 as v4
from scripts.prepare_grounding_multicategory_v3 import MANIFEST as V3_MANIFEST, build

ROOT = Path(__file__).resolve().parents[1]
BASE = "4520597a654d25f73ff1b425aa94ad27326c026f"


class Equivalence(unittest.TestCase):
    def test_manifest_semantics_and_order(self):
        old = r.read(ROOT, V3_MANIFEST)
        new = r.read(ROOT, r.GROUNDING_MANIFEST)
        self.assertEqual([c['case_id'] for c in new['cases']], list(v4.CASE_IDS))
        normalized = deepcopy(new)
        normalized['schema_version'] = old['schema_version']
        for before, after in zip(old['cases'], normalized['cases']):
            for field in ('image_path', 'image_sha256', 'image_size_bytes'):
                after[field] = before[field]
        self.assertEqual(normalized, old)

    def test_a_to_d_exact_historical_bytes(self):
        manifest = r.read(ROOT, r.GROUNDING_MANIFEST)
        old = r.read(ROOT, V3_MANIFEST)
        for case, historical in zip(manifest['cases'][:8], old['cases'][:8]):
            with self.subTest(case=case['case_id']):
                raw = (ROOT / case['image_path']).read_bytes()
                self.assertEqual(raw, (ROOT / 'tests/fixtures/pre_freeze/frozen_external_gate'
                                       / (case['case_id'] + '.png')).read_bytes())
                self.assertEqual(r.digest(raw), historical['image_sha256'])

    def test_all_decoded_pixels_match_unchanged_v3_build(self):
        generated, images = build()
        committed = r.read(ROOT, r.GROUNDING_MANIFEST)
        for before, after in zip(generated['cases'], committed['cases']):
            with self.subTest(case=after['case_id']), \
                    Image.open(BytesIO(images[before['image_path']])) as expected, \
                    Image.open(ROOT / after['image_path']) as actual:
                self.assertEqual((actual.size, actual.mode), ((256, 256), 'RGB'))
                self.assertEqual((actual.size, actual.mode), (expected.size, expected.mode))
                self.assertEqual(actual.tobytes(), expected.tobytes())
                # Deliberately no assertion about regenerated encoded PNG bytes.

    def test_candidate_config_only_manifest_changes(self):
        old = json.loads(subprocess.check_output(
            ['git', 'show', f'{BASE}:{r.CONFIG}'], cwd=ROOT))
        new = r.read(ROOT, r.CONFIG)
        old['grounding']['manifest'] = r.GROUNDING_MANIFEST
        self.assertEqual(new, old)
        self.assertIs(new['execution_authorized'], False)
        self.assertEqual(new['protocol_freeze'], 'PENDING')
        self.assertEqual(new['participation'], 'PENDING_RESEARCH_LEAD_DECISION')

    def test_read_only_cli_no_model_or_renderer_import(self):
        code = '''import builtins, runpy, socket
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch', 'transformers', 'huggingface_hub', 'mamba_ssm'} or 'prepare_grounding' in name or 'generate_external' in name:
        raise AssertionError('model/network/renderer dependency')
    return original(name, *args, **kwargs)
def denied(*args, **kwargs):
    raise AssertionError('network forbidden')
builtins.__import__ = guarded
socket.socket.connect = denied
socket.create_connection = denied
runpy.run_path('scripts/verify_grounding_multicategory_v4.py', run_name='__main__')
'''
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('V4_FIXTURE_VERIFICATION=PASS', result.stdout)


class Verification(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name).resolve()
        self.manifest = r.read(ROOT, r.GROUNDING_MANIFEST)
        config = r.read(ROOT, r.CONFIG)
        paths = [r.CONFIG, r.GROUNDING_MANIFEST, config['classification']['manifest']]
        paths += [c['image_path'] for c in self.manifest['cases']]
        paths += [c['image_path'] for c, _ in r.load_suite(ROOT)]
        for name in paths:
            destination = self.repo / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        self.image = self.repo / self.manifest['cases'][0]['image_path']

    def save_manifest(self):
        (self.repo / r.GROUNDING_MANIFEST).write_bytes(r.encode(self.manifest))

    def test_verifier_pass_is_read_only(self):
        before = {p.relative_to(self.repo): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.repo.rglob('*') if p.is_file()}
        with patch.object(Image.Image, 'save', side_effect=AssertionError('no render')):
            self.assertEqual(v4.verify(self.repo), 12)
        after = {p.relative_to(self.repo): (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(after, before)

    def test_same_size_byte_tamper_fails_verifier_and_runtime(self):
        raw = bytearray(self.image.read_bytes())
        raw[len(raw) // 2] ^= 1
        self.image.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_HASH'):
            v4.verify(self.repo)
        for key in ('ovis', 'plamo', 'kosmos'):
            with self.subTest(model=key), self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_HASH'):
                r.prepared_cases(self.repo, key)

    def test_wrong_size_fails(self):
        self.manifest['cases'][0]['image_size_bytes'] += 1
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_SIZE'):
            v4.verify(self.repo)
        with self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_SIZE'):
            r.prepared_cases(self.repo, 'ovis')

    def test_missing_fixture_fails_without_regeneration(self):
        self.image.unlink()
        with self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_MISSING'):
            v4.verify(self.repo)
        with self.assertRaises(FileNotFoundError):
            r.prepared_cases(self.repo, 'ovis')
        self.assertFalse(self.image.exists())

    def test_wrong_outside_absolute_and_traversal_paths_fail(self):
        for name in ('tests/fixtures/pre_freeze/frozen_external_gate/A_1.png',
                     r.GROUNDING_FIXTURES + '/A_2.png',
                     r.GROUNDING_FIXTURES + '/../frozen_external_gate/A_1.png',
                     r.GROUNDING_FIXTURES + '_alias/A_1.png',
                     str(self.image), '../A_1.png'):
            self.manifest['cases'][0]['image_path'] = name
            self.save_manifest()
            with self.subTest(path=name), self.assertRaises(ValueError):
                v4.verify(self.repo)
            with self.subTest(runtime_path=name), self.assertRaises(ValueError):
                r.prepared_cases(self.repo, 'ovis')

    def test_fixture_directory_alias_rejected(self):
        folder = self.repo / r.GROUNDING_FIXTURES
        target = folder.with_name('alias_target')
        folder.rename(target)
        if os.name == 'nt':
            # Junctions exercise Path.resolve alias rejection without admin rights.
            def literal(path):
                return "'" + str(path).replace("'", "''") + "'"
            subprocess.run(['powershell', '-NoProfile', '-Command',
                            f'New-Item -ItemType Junction -Path {literal(folder)} '
                            f'-Target {literal(target)} | Out-Null'], check=True)
        else:
            folder.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'PATH_ESCAPE_OR_ALIAS'):
            v4.verify(self.repo)
        with self.assertRaisesRegex(ValueError, 'PATH_ESCAPE_OR_ALIAS'):
            r.prepared_cases(self.repo, 'ovis')

    def test_wrong_canvas_or_mode_fails_even_with_matching_hash(self):
        for mode, size in (('RGBA', (256, 256)), ('RGB', (128, 256))):
            with Image.new(mode, size) as image:
                image.save(self.image, format='PNG')
            raw = self.image.read_bytes()
            self.manifest['cases'][0].update(image_sha256=r.digest(raw), image_size_bytes=len(raw))
            self.save_manifest()
            with self.subTest(mode=mode, size=size), self.assertRaisesRegex(ValueError, 'SYNTHETIC_IMAGE_CANVAS'):
                v4.verify(self.repo)

    def test_invalid_png_fails_even_with_matching_hash(self):
        raw = b'not a PNG'
        self.image.write_bytes(raw)
        self.manifest['cases'][0].update(image_sha256=r.digest(raw), image_size_bytes=len(raw))
        self.save_manifest()
        with self.assertRaises(OSError):
            v4.verify(self.repo)

    def test_missing_duplicate_or_reordered_cases_fail(self):
        original = deepcopy(self.manifest['cases'])
        for cases in (original[:-1], original + original[:1], original[::-1]):
            self.manifest['cases'] = cases
            self.save_manifest()
            with self.assertRaisesRegex(ValueError, 'V4_MANIFEST_CONTRACT'):
                v4.verify(self.repo)

    def test_cli_failure_is_nonzero(self):
        self.image.write_bytes(b'tampered')
        with patch.object(v4, 'ROOT', self.repo), patch('sys.stderr', new_callable=StringIO) as err:
            self.assertEqual(v4.main(), 2)
        self.assertIn('V4_FIXTURE_VERIFICATION=FAIL', err.getvalue())

    def test_d9r20_unchanged_22_call_sequence_without_renderer(self):
        # No generated data/processed images exist in this temporary checkout.
        self.assertFalse((self.repo / 'data').exists())
        with r.offline(), patch('scripts.prepare_grounding_multicategory_v3.build',
                                side_effect=AssertionError('no renderer')), \
                patch.object(Image.Image, 'save', side_effect=AssertionError('no PNG encoding')):
            for key in ('ovis', 'plamo', 'kosmos'):
                cases = r.prepared_cases(self.repo, key)
                self.assertEqual([c['call_id'] for c in cases],
                                 [f'cq_{i:02d}' for i in range(1, 9)] +
                                 ['g_' + name for name in v4.CASE_IDS] + ['g_H_green', 'g_H_cyan'])
                self.assertEqual([c['task'] for c in cases], ['classification'] * 8 + ['grounding'] * 14)
                self.assertEqual([c['target'] for c in cases[8:]],
                                 ['red square'] * 12 + ['green circle', 'cyan rectangle'])
                candidate = r.read(self.repo, r.CONFIG)['models'][key]
                for case in cases[8:]:
                    self.assertEqual(case['prompt'], candidate['grounding_prompt'].format(target=case['target']))
                    self.assertEqual(r.digest(case['raw_image']), case['image_sha256'])
                    self.assertTrue(case['image_path'].startswith(r.GROUNDING_FIXTURES + '/'))
        self.assertFalse((self.repo / 'data').exists())

    def test_d9r20_refuses_v3_manifest(self):
        config = r.read(self.repo, r.CONFIG)
        config['grounding']['manifest'] = V3_MANIFEST
        (self.repo / r.CONFIG).write_bytes(r.encode(config))
        with self.assertRaisesRegex(ValueError, 'COMMITTED_V4_MANIFEST_REQUIRED'):
            r.prepared_cases(self.repo, 'ovis')

    def test_d9r20_cannot_accept_caller_image_path(self):
        with self.assertRaises(TypeError):
            r.prepared_cases(self.repo, 'ovis', image_path=str(self.image))


if __name__ == '__main__':
    unittest.main()
