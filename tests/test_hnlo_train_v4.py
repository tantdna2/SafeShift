"""CPU-only synthetic admission and export faults; no real TRAIN image/weights."""
from copy import deepcopy
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
from unittest.mock import patch

from PIL import Image
from safeshift.diagnostics.hnlo_train import bootstrap as boot, budget, cohort, contract, inputs, orchestrate as flow
from safeshift.diagnostics.one_click.artifacts import sha256, write
from safeshift.pa3.native.journal import Journal
from tests.test_hnlo_train import CPUCase, ROOT, approved, source


class InputTests(CPUCase):
    def setUp(self):
        super().setUp()
        self.mounts = self.root / 'kaggle/input'
        self.dataset = self.mounts / 'datasets/nguynanhtn/inspecsafe-v1-kaggle/InspecSafe-V1-Kaggle/train'
        raw = io.BytesIO()
        Image.new('RGB', (8, 8), (1, 2, 3)).save(raw, format='JPEG')
        self.raw = raw.getvalue()
        self.rows = [{'sample_id': f'synthetic-{i}', 'image_sha256': hashlib.sha256(self.raw).hexdigest(),
            'image_locator': f'DATA_PATH/train/Annotations/synthetic/image-{i:06d}.jpg'} for i in range(941)]
        for row in self.rows:
            path = self.dataset / row['image_locator']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.raw)

    def run_flow(self, model='qwen3', shard=0, notebook=False, tag='unit', fault=None, budget_fault=None):
        out = self.root / ('out-' + tag)
        out.mkdir()
        write(self.root / contract.AUTHORITY, approved(model, shard))
        events, owner = [], self
        class Ops(flow.Operations):
            kaggle_inputs = owner.mounts
            def preflight(self):
                events.append('budget')
                if budget_fault: raise budget_fault
                return {'synthetic_cpu_only': True}
            def software(self): events.append('software')
            def worker(self, mode):
                events.append(mode)
                return {'status': 'RETURNED'}
            def provision(self): events.append('checkpoint')
            def stage(self, rows):
                events.append('stage')
                if fault:
                    with patch.object(inputs.shutil, 'copyfileobj', side_effect=fault):
                        return super().stage(rows)
                return super().stage(rows)
            def evaluate(self):
                raise RuntimeError('SYNTHETIC_NO_RAW_NO_LABEL_JOIN')
        selected = self.rows[:contract.unit(model, shard)['count']]
        original = flow.run
        def invoke(repo, work, output, proof, m, s):
            return original(repo, work, output, proof, m, s, operations_factory=Ops)
        with patch.object(cohort, 'inference', return_value=[selected] * 4):
            if notebook:
                code = ''.join(json.loads((ROOT / f'notebooks/SafeShift_HNLO_TRAIN_{model}_SHARD{shard}_V4.ipynb').read_bytes())['cells'][1]['source'])
                namespace = {'__name__': 'synthetic_notebook'}
                exec(compile(code.rsplit('\nresult = bootstrap(', 1)[0], '<notebook>', 'exec'), namespace)
                namespace['fetch_source'] = lambda scratch: (self.root, source())
                with patch.object(flow, 'run', side_effect=invoke), patch('tempfile.gettempdir', return_value=str(self.root)):
                    result = namespace['bootstrap'](model, shard, output=out)
            else:
                result = invoke(self.root, out / 'work', out, source(), model, shard)
        return result, out, events

    def test_all_eight_actual_notebook_cells_stage_complete_shards_before_setup(self):
        # Same ordinals/count as production; only generated JPEGs and synthetic identity/hash.
        for model in ('qwen3', 'internvl3'):
            for shard in range(4):
                with self.subTest(model=model, shard=shard):
                    authority = self.root / contract.AUTHORITY
                    if authority.exists(): authority.unlink()
                    result, out, events = self.run_flow(model, shard, notebook=True, tag=f'{model}-{shard}')
                    self.assertEqual(events, ['budget', 'stage', 'software', 'inspect', 'checkpoint', 'inference'])
                    preflight = next(out.glob('data/processed/hnlo_train/*/evidence/train-preflight.json'))
                    receipt = json.loads(preflight.read_bytes())
                    count = (941, 941, 941, 940)[shard]
                    self.assertEqual(receipt['count'], count)
                    self.assertEqual([r['ordinal'] for r in receipt['images']], list(range(count)))
                    self.assertEqual(receipt['dataset_root_relative_to_input'], self.dataset.relative_to(self.mounts).as_posix())
                    stage = Journal(preflight.parent / 'input-staging')
                    self.assertTrue(stage.verify())
                    for i in range(count):
                        for kind in ('hash', 'copy'):
                            row = stage.read(f'image-{i:06d}.{kind}')
                            self.assertEqual(row, {'ordinal': i, 'size_bytes': len(self.raw),
                                'expected_sha256': self.rows[i]['image_sha256'], 'actual_sha256': self.rows[i]['image_sha256']})
                    self.assertEqual(result['status'], 'PARTIAL')
                    self.assertEqual(result['export']['status'], 'EXPORTED')
                    self.assertEqual(len(result['sample_journal']), count)

    def assert_failure(self, expected, **kwargs):
        result, out, events = self.run_flow(**kwargs)
        self.assertEqual(result['error']['reason'], expected)
        for event in ('software', 'inspect', 'checkpoint', 'inference'):
            self.assertNotIn(event, events)
        self.assertFalse(result['provisioning_started'])
        self.assertFalse(result['gpu_worker_started'])
        self.assertEqual(result['export']['status'], 'EXPORTED')
        manifest = json.loads(next(out.glob('*_manifest.json')).read_bytes())
        self.assertIn('result.json', [r['path'] for r in manifest['files']])
        receipt = json.loads(next(out.glob('*_export.json')).read_bytes())
        self.assertEqual(receipt['result_sha256'], sha256(next(out.glob('*_result.json'))))
        return result

    def test_zero_root_export_and_no_setup(self):
        self.dataset.rename(self.dataset.with_name('not-an-allowed-root'))
        self.assert_failure('TRAIN_ROOT_NOT_FOUND')

    def test_multiple_roots_export_and_no_setup(self):
        (self.mounts / 'second/DATA_PATH/train/Annotations').mkdir(parents=True)
        self.assert_failure('MULTIPLE_TRAIN_ROOTS')

    def test_missing_last_image_proves_entire_shard_metadata_precedes_bytes(self):
        (self.dataset / self.rows[-1]['image_locator']).unlink()
        with patch.object(inputs, 'sha256', side_effect=AssertionError('EARLY_IMAGE_BYTES')):
            result = self.assert_failure('TRAIN_IMAGE_MISSING')
        self.assertEqual(result['error']['ordinal'], 940)
        self.assertFalse(any(r['staging_read_started'] for r in result['sample_journal']))

    def test_wrong_hash_at_last_ordinal_stops_before_setup(self):
        (self.dataset / self.rows[-1]['image_locator']).write_bytes(b'wrong')
        result = self.assert_failure('TRAIN_IMAGE_HASH_MISMATCH_NO_SKIP')
        self.assertEqual(result['error']['ordinal'], 940)
        self.assertEqual(result['sample_journal'][-1]['status'], 'TECHNICAL_ERROR')

    def test_copy_io_error_export_and_no_setup(self):
        self.assert_failure('TRAIN_STAGING_COPY_OR_READ_FAILED', fault=OSError(errno.EIO, 'synthetic'))

    def test_disk_full_export_and_no_setup(self):
        self.assert_failure('TRAIN_STAGING_NO_SPACE', fault=OSError(errno.ENOSPC, 'synthetic'))

    def test_scratch_budget_failure_blocks_all_setup_and_image_reads(self):
        result = self.assert_failure('SCRATCH_FREE_INSUFFICIENT',
            budget_fault=inputs.TrainInputError('SCRATCH_FREE_INSUFFICIENT', free_bytes=0))
        self.assertFalse(result['dataset_read'])

    def test_staged_copy_corruption_records_size_and_hash(self):
        def corrupt(reader, writer):
            writer.write(b'corrupt')
        with patch.object(inputs.shutil, 'copyfileobj', side_effect=corrupt):
            # Packaging uses tarfile rather than this staging copy function.
            self.assert_failure('STAGED_COPY_HASH_OR_SIZE_MISMATCH')

    def test_hardlink_rejected_before_setup(self):
        os.link(self.dataset / self.rows[-1]['image_locator'], self.root / 'alias.jpg')
        self.assert_failure('TRAIN_IMAGE_HARDLINK_ALIAS_FORBIDDEN')

    def test_nonregular_rejected_before_setup(self):
        path = self.dataset / self.rows[-1]['image_locator']
        path.unlink(); path.mkdir()
        self.assert_failure('TRAIN_IMAGE_NOT_REGULAR_FILE')

    def test_unreadable_metadata_rejected_before_setup(self):
        original = Path.stat
        target = self.dataset / self.rows[-1]['image_locator']
        def broken(path, *args, **kwargs):
            if path == target: raise PermissionError(errno.EACCES, 'synthetic')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'stat', broken):
            self.assert_failure('TRAIN_IMAGE_METADATA_UNREADABLE')

    def test_symlink_image_parent_and_mount_rejected(self):
        if os.name == 'nt': self.skipTest('Real symlinks covered on Linux')
        path = self.dataset / self.rows[-1]['image_locator']
        path.unlink(); path.symlink_to(self.dataset / self.rows[0]['image_locator'])
        self.assert_failure('UNSAFE_TRAIN_IMAGE_PATH')

    def test_torn_timing_does_not_block_failure_export(self):
        real_stage = flow.Operations.stage
        def torn(ops, rows):
            path = ops.evidence / 'raw/model-load-timing.json'
            path.parent.mkdir()
            path.write_bytes(b'{"seconds":')
            return real_stage(ops, rows)
        with patch.object(flow.Operations, 'stage', torn):
            result, out, events = self.run_flow(fault=OSError(errno.EIO, 'synthetic'))
        self.assertEqual(result['export']['status'], 'EXPORTED')
        self.assertEqual(result['timing_errors'][0]['artifact'], 'model-load-timing.json')
        self.assertIsNone(result['model_load_seconds'])

    def test_packaging_failure_retains_result_receipt_and_raw(self):
        # Fail archive creation after the manifest has been written; keep torn archive.
        original = tarfile.open
        def fail_archive(name, mode, *args, **kwargs):
            if mode == 'x:gz':
                Path(name).write_bytes(b'SYNTHETIC_TORN_ARCHIVE')
                raise OSError(errno.ENOSPC, 'synthetic')
            return original(name, mode, *args, **kwargs)
        with patch('safeshift.diagnostics.one_click.artifacts.tarfile.open', side_effect=fail_archive):
            result, out, _ = self.run_flow(fault=OSError(errno.EIO, 'synthetic'))
        self.assertEqual(result['export']['status'], 'FAILED')
        self.assertEqual(result['status'], 'FAILED')
        self.assertTrue(next(out.glob('*_export.json')).exists())
        self.assertTrue(next(out.glob('*_manifest.json')).exists())
        self.assertEqual(next(out.glob('*.tar.gz')).read_bytes(), b'SYNTHETIC_TORN_ARCHIVE')
        checksum = json.loads((out / (contract.unit('qwen3', 0)['run_id'] + '_sha256.json')).read_bytes())
        self.assertEqual(checksum['status'], 'EXPORT_FAILED_NOT_VALIDATED')
        self.assertEqual(checksum['archive_sha256'], sha256(next(out.glob('*.tar.gz'))))


class BudgetTests(CPUCase):
    def test_gpu_headroom_matches_model_pilot_observations_before_cuda(self):
        def observation(free0, free1):
            return f'Tesla T4, 15360, {free0}, synthetic-driver\nTesla T4, 15360, {free1}, synthetic-driver'
        budget.admit_gpu('qwen3', observation(14336, 14336))
        for free in ((14335, 14336), (14336, 14335)):
            with self.assertRaisesRegex(inputs.TrainInputError, 'GPU_FREE_BUDGET'):
                budget.admit_gpu('qwen3', observation(*free))
        self.assertEqual(budget.admit_gpu('internvl3', observation(6144, 0))['selected_devices'], [0])
        with self.assertRaisesRegex(inputs.TrainInputError, 'GPU_FREE_BUDGET'):
            budget.admit_gpu('internvl3', observation(6143, 15000))
        with self.assertRaisesRegex(inputs.TrainInputError, 'OBSERVATION_UNREADABLE'):
            budget.admit_gpu('qwen3', 'synthetic-malformed-observation')

    def test_output_scratch_archive_sidecar_and_shared_device_boundaries(self):
        plan = budget.estimate(941, 5 * budget.GIB)
        self.assertGreater(plan['output_required_bytes'], 2 * 941 * budget.PRIMARY_PER_SAMPLE)
        self.assertLess(plan['output_required_bytes'], budget.OUTPUT_CAP)
        output, scratch = plan['output_required_bytes'], plan['scratch_required_bytes']
        budget.admit(plan, output_free=output, scratch_free=scratch)
        for args, reason in (({'output_free': output-1, 'scratch_free': scratch}, 'OUTPUT_FREE'),
            ({'output_free': output, 'scratch_free': scratch-1}, 'SCRATCH_FREE'),
            ({'output_free': output, 'scratch_free': scratch, 'same_device': True}, 'SCRATCH_FREE'),
            ({'output_free': output, 'scratch_free': scratch, 'existing_output': budget.OUTPUT_CAP}, 'OUTPUT_CAP')):
            with self.assertRaisesRegex(inputs.TrainInputError, reason): budget.admit(plan, **args)

    def test_fresh_unit_attempts_and_pilot_overlap_preserved(self):
        units = contract.scope()['units']
        self.assertEqual(len({u['run_id'] for u in units}), 8)
        self.assertEqual(len({u['attempt_id'] for u in units}), 8)
        self.assertEqual(contract.scope()['pilot_exposure']['ordinals'], list(range(8)))
        from safeshift.diagnostics.resource_pilot.cohort import IMAGE_SHA256
        self.assertEqual([r['image_sha256'] for r in cohort.inference(ROOT)[0][:8]], list(IMAGE_SHA256))
        for version in (1, 2, 3):
            old = json.loads((ROOT / f'configs/diagnostics/resource_pilot_authority.v{version}.json').read_bytes())
            with self.assertRaises(PermissionError): contract.authorize(old, source(), 'qwen3', 0)
        value = approved()
        value['grant']['units'][0]['unit']['attempt_id'] = 'resource-pilot8-v3-qwen3-20261019-a1'
        with self.assertRaises(PermissionError): contract.authorize(value, source(), 'qwen3', 0)
        value = approved(); value['grant']['decision_url'] = 'https://github.com/tantdna2/SafeShift/pull/121#wrong'
        with self.assertRaises(PermissionError): contract.authorize(value, source(), 'qwen3', 0)


class PreservationTests(CPUCase):
    def test_all_existing_files_preserved_except_append_only_task_and_decision_logs(self):
        import subprocess
        tracked = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', contract.BASE_SHA], text=True).splitlines()
        for name in tracked:
            before = subprocess.check_output(['git', '-C', str(ROOT), 'show', contract.BASE_SHA + ':' + name])
            after = (ROOT / name).read_bytes()
            if name in ('DECISIONS.md', 'TASKS.md'):
                self.assertTrue(after.startswith(before), name)
            else:
                self.assertEqual(before, after, name)


class ExposureTests(CPUCase):
    def test_native_call_marker_durable_before_callback_and_duplicate_rejected(self):
        from safeshift.diagnostics.hnlo_train.backend import record_native_call
        from safeshift.diagnostics.hnlo_train.capture import SampleCapture
        cap = SampleCapture(self.root / "sample", {"ordinal": 0, "image_sha256": "a" * 64})
        index = Journal(self.root / "index", create=True)
        calls = set()
        record_native_call(index, cap, calls)
        self.assertEqual(index.read("sample-000000.native-call"), {"ordinal": 0,
            "exposure": "NATIVE_CALL_START_RECORDED_BEFORE_INVOCATION"})
        self.assertEqual(calls, {0})
        with self.assertRaisesRegex(RuntimeError, "SECOND_CALL"):
            record_native_call(index, cap, calls)
