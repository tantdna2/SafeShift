"""Synthetic orchestration only: no dataset, credentials, model, GPU or network."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import json
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from safeshift import minicpm173_once as c
from safeshift.pilot.artifacts import read, write, sha, verify_archive
from safeshift.pilot.contract import digest, parse_label
from scripts import minicpm173_train_once as run
from scripts import submit_minicpm173_once as submitter


def grant():
    return {'identity': c.IDENTITY, 'reviewed_head': '1' * 40, 'runtime_commit': '2' * 40,
        'manifest_sha256': '3' * 64, 'notebook_sha256': '4' * 64,
        'notebook_code_sha256': '5' * 64, 'job': c.JOB, 'version': 1,
        'expires_unix': int(time.time()) + 3600, 'limits': dict(c.LIMITS)}


class MiniOnceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ledger = {}
        self.grant = grant()
        self.ctx = {'grant': self.grant, 'approval_comment': 7000000000, 'binding': digest(self.grant)}
        self.coordinator = c.Coordinator(self.grant)

    def create(self, name, value):
        if name in self.ledger:
            raise ValueError('REMOTE_CREATE_CONFLICT')
        self.ledger[name] = deepcopy(value)
        return '6' * 40

    def emit(self, text, **unused):
        if text.startswith(c.PREFIX):
            self.coordinator.accept(json.loads(text[len(c.PREFIX):]))

    def test_cross_vm_duplicate_and_direct_call_cannot_reuse_remote_permit(self):
        with patch.object(c, 'remote_record', side_effect=self.ledger.get), patch.object(c, 'create_record', side_effect=self.create):
            value = c.permit(self.ctx, 'launch', '', emit=self.emit)
            self.assertEqual(value, self.ledger['launch'])
            # Entire local directory is new; remote custody is still authoritative.
            with tempfile.TemporaryDirectory(), self.assertRaisesRegex(ValueError, 'NO_REPLAY'):
                c.permit(self.ctx, 'launch', '', emit=self.emit)
            load = c.permit(self.ctx, 'load', value['nonce'], emit=self.emit)
            call = c.permit(self.ctx, 'call', load['nonce'], emit=self.emit)
            self.coordinator.accept(call)  # Repeated log line is a no-op.
            with self.assertRaisesRegex(ValueError, 'NO_REPLAY'):
                c.permit(self.ctx, 'call', load['nonce'], emit=self.emit)
            self.assertEqual(list(self.ledger), ['launch', 'load', 'call'])

    def test_wrong_process_out_of_order_or_conflicting_log_cannot_get_permit(self):
        challenge = {'identity': c.IDENTITY, 'binding': self.ctx['binding'], 'phase': 'call',
                     'nonce': 'a' * 64, 'parent_nonce': ''}
        with patch.object(c, 'create_record', side_effect=self.create):
            with self.assertRaisesRegex(ValueError, 'PHASE_ORDER'):
                self.coordinator.accept(challenge)
            challenge['phase'] = 'launch'
            self.coordinator.accept(challenge)
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_PROCESS'):
                self.coordinator.accept({**challenge, 'nonce': 'b' * 64})
            with self.assertRaisesRegex(ValueError, 'PARENT_NONCE'):
                self.coordinator.accept({**challenge, 'phase': 'load', 'nonce': 'b' * 64})

    def test_unknown_remote_create_is_never_retried_or_adopted(self):
        def uncertain(name, value):
            self.create(name, value)
            raise TimeoutError('SYNTHETIC_RESPONSE_LOST')
        with patch.object(c, 'remote_record', side_effect=self.ledger.get), patch.object(c, 'create_record', side_effect=uncertain) as creates:
            with self.assertRaises(TimeoutError):
                c.permit(self.ctx, 'launch', '', emit=self.emit)
            with self.assertRaisesRegex(ValueError, 'NO_REPLAY'):
                c.permit(self.ctx, 'launch', '', emit=self.emit)
            self.assertEqual(creates.call_count, 1)

    def test_remote_write_is_create_only_and_failure_not_retried(self):
        response = Mock(returncode=0, stdout=json.dumps({'content': {'path': c.LEDGER + '/launch.json'},
                                                       'commit': {'sha': '1' * 40}}))
        with patch.object(c.subprocess, 'run', return_value=response) as invoke:
            c.create_record('launch', {'synthetic': True})
            payload = json.loads(invoke.call_args.kwargs['input'])
            self.assertNotIn('sha', payload)
            self.assertEqual(payload['branch'], c.BRANCH)
            self.assertEqual(invoke.call_count, 1)
        with patch.object(c.subprocess, 'run', side_effect=subprocess.TimeoutExpired('gh', 30)) as invoke:
            with self.assertRaises(subprocess.TimeoutExpired):
                c.create_record('launch', {})
            self.assertEqual(invoke.call_count, 1)

    def test_review_hold_and_exact_owner_grant(self):
        comment = {'user': {'login': 'tantdna2'}, 'issue_url': c.API + '/issues/175',
                   'body': 'MINICPM173_RELEASE_V1\n```json\n' + json.dumps(self.grant) + '\n```'}
        with patch.object(c, 'public_get', return_value=comment):
            self.assertEqual(c.read_grant(7000000000), self.grant)
            with self.assertRaises(ValueError):
                c.read_grant(6598989252)
        for changed in ({**comment, 'user': {'login': 'not-owner'}},
                        {**comment, 'body': 'approved=True'},
                        {**comment, 'issue_url': c.API + '/issues/173'}):
            with patch.object(c, 'public_get', return_value=changed), self.assertRaises(ValueError):
                c.read_grant(7000000000)
        for key, value in (('job', 'other'), ('version', 2), ('expires_unix', 0),
                           ('limits', {**c.LIMITS, 'model_key': 'internvl35'})):
            bad = {**comment, 'body': 'MINICPM173_RELEASE_V1\n```json\n' + json.dumps({**self.grant, key: value}) + '\n```'}
            with patch.object(c, 'public_get', return_value=bad), self.assertRaises(ValueError):
                c.read_grant(7000000000)
        with patch.object(run, 'check_source'), patch.object(c, 'source_check'), patch.object(c, 'remote_record', return_value=None):
            with self.assertRaisesRegex(ValueError, 'REVIEW_HOLD'):
                run.launch({}, self.root, self.root)
        self.assertEqual(list(self.root.iterdir()), [])

    def exercise(self, *, response='{"safety_level":"Level03"}', failure=None):
        output, scratch = self.root / 'output', self.root / 'scratch'
        output.mkdir(); scratch.mkdir()
        image = self.root / 'synthetic-image.bin'
        image.write_bytes(b'SYNTHETIC_NOT_AN_ACTUAL_IMAGE')
        spec = {'runtime_commit': '2' * 40, 'manifest': {'synthetic': '3' * 64}}
        self.grant['manifest_sha256'] = digest(spec['manifest'])
        self.ctx['binding'] = digest(self.grant)
        spec_file = self.root / 'spec.json'; write(spec_file, spec)
        row = {'ordinal': 0, 'sample_id': 'SYNTHETIC', 'image_sha256': sha(image), 'image': str(image)}
        counts = {'loads': 0, 'calls': 0, 'stages': []}
        class SyntheticBackend:
            environment = {'synthetic': True}
            def generate(self, image_path, sample):
                counts['calls'] += 1
                write(sample / 'native_call.json', {'invocation': 1})
                write(sample / 'native.json', {'scope': 'SYNTHETIC_ONLY'})
                if failure == 'call':
                    raise RuntimeError('SYNTHETIC_GENERATION_ERROR')
                return {'response': response, 'raw_nonfinite': failure == 'nonfinite',
                        'cpu_tokenizer_replay': {'status': 'FAIL' if failure == 'decode' else 'PASS'}}
        def backend(*args, **kwargs):
            counts['loads'] += 1
            self.assertEqual(args[0], 'minicpm4')
            if failure == 'checkpoint':
                raise ValueError('WEIGHT_CHECKSUM:SYNTHETIC')
            if failure == 'oom':
                raise RuntimeError('SYNTHETIC_CUDA_OOM')
            return SyntheticBackend()
        def parsed(text):
            raw_path = output / c.IDENTITY / 'sample/raw.json'
            self.assertTrue(raw_path.exists())
            self.assertEqual(read(raw_path)['response'], text)
            return parse_label(text)
        def supervise(command, **kwargs):
            stage = command[command.index('--worker') + 1]
            counts['stages'].append(stage)
            self.assertGreater(kwargs['deadline'], time.monotonic())
            if stage == 'native' and failure == 'timeout':
                write(output / c.IDENTITY / 'load-reservation.json', {'synthetic': 'uncertain'})
                raise RuntimeError('SUPERVISED_HARD_DEADLINE')
            # Exercise exact CLI -> worker -> loader/call/raw/parser, mock only hardware/model/process.
            run.main(command[4:])
        def prepare(repo, key, scratch, out, env, deadline):
            return Path(sys.executable), env
        def binding(inputs):
            if failure == 'history':
                raise ValueError('ALL_FIVE_ATTEMPTS_REQUIRED_INCLUDING_V5')
            if failure == 'image':
                raise ValueError('ORIGINAL_FIRST_IMAGE_BYTES')
            return {'consumed': {'qwen3': 1, 'internvl35': 1, 'minicpm4': 0}}, row
        def resource(kind):
            def check(*args):
                if failure == kind:
                    raise ValueError('SYNTHETIC_RESOURCE_' + kind.upper())
                return {}
            return check
        with ExitStack() as stack:
            for target, name, value in ((run, 'check_source', lambda s: None), (c, 'context', lambda s: self.ctx),
                (c, 'remote_record', self.ledger.get), (c, 'create_record', self.create),
                (run, 'bind_original', binding), (run, 'diagnostic_history', lambda i: [{'calls': 5}]),
                (run, 'checkpoint', lambda *a: (Path('marker'), Path('source'), Path('weights'))),
                (run, 'verify_snapshot', lambda *a: None), (run, 'memory', lambda: {'available_bytes': 1 if failure == 'ram' else 24 * 2**30}),
                (run, 'bind_cuda_driver', lambda o: None), (run, 'driver_check', resource('driver')),
                (run.environment, 'software', lambda *a: {}), (run.environment, 'cuda', resource('vram')),
                (run.environment, 'resources', resource('disk')), (run.provision, 'clean_env', lambda *a: {}),
                (run, 'advise_owned_runtime', lambda *a: {}), (run.supervision, 'run', supervise),
                (run, 'parse_label', parsed)):
                stack.enter_context(patch.object(target, name, side_effect=value))
            from safeshift.candidates import minicpm_resampler_fp32 as numerical, train_runtime
            stack.enter_context(patch.object(numerical, 'backend', side_effect=backend))
            stack.enter_context(patch.object(train_runtime, 'prepare_runtime', side_effect=prepare))
            stack.enter_context(patch.object(train_runtime, 'memory', return_value={'gpu0_free': 16 * 2**30, 'synthetic': True}))
            # Permit algorithm remains real; its emitter delivers synthetic log events synchronously.
            real_permit = c.permit
            stack.enter_context(patch.object(c, 'permit', side_effect=lambda *a: real_permit(*a, emit=self.emit)))
            with redirect_stdout(io.StringIO()):
                code = run.main(['--spec', str(spec_file), '--output', str(output), '--scratch', str(scratch)])
            out = output / c.IDENTITY
            summary = read(out / 'summary.json')
            members = verify_archive(Path(str(out) + '.zip'))
            verified, _ = submitter.verify_result(Path(str(out) + '.zip'), self.grant)
            self.assertEqual(verified, summary)
            self.assertEqual(sha(Path(str(out) + '.zip')), read(Path(str(out) + '.zip.sha256.json'))['sha256'])
            # New output/scratch roots still cannot run again, even after SUCCESS/INVALID/error.
            fresh = self.root / 'fresh'; fresh.mkdir()
            second = run.launch(spec, fresh, fresh)
            self.assertEqual(second['status'], 'TECHNICAL_ERROR')
            self.assertEqual(second['native_call_markers'], 0)
        return code, summary, members, counts

    def test_full_positive_cli_setup_load_raw_parse_zip_once(self):
        code, result, members, counts = self.exercise()
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['original_smoke_counts'], {'qwen3': 1, 'internvl35': 1, 'minicpm4': 1})
        self.assertEqual(counts, {'loads': 1, 'calls': 1, 'stages': ['setup', 'native']})
        self.assertTrue({'sample/raw.json', 'sample/result.json', 'load-reservation.json'} <= set(members))

    def test_self_consistent_zip_cannot_hide_consumption_or_forge_status(self):
        from safeshift.pilot.artifacts import import_archive, export
        self.exercise()
        original = self.root / 'output' / (c.IDENTITY + '.zip')
        altered = import_archive(original, self.root / 'synthetic-altered')
        summary = read(altered / 'summary.json')
        summary['native_call_markers'] = 0
        # Synthetic re-seal deliberately has valid ZIP hashes but contradictory accounting.
        (altered / 'summary.json').write_text(json.dumps(summary))
        archive = self.root / 'synthetic-altered.zip'
        export(altered, archive)
        with self.assertRaisesRegex(ValueError, 'FINAL_CALL_BUDGET'):
            submitter.verify_result(archive, self.grant)

    def test_invalid_is_terminal_and_raw_is_not_cleaned(self):
        code, result, members, counts = self.exercise(response='```json\n{"safety_level":"Level03"}\n```')
        self.assertEqual((code, result['status'], result['consumption']), (0, 'INVALID', 'COMPLETED'))
        self.assertEqual(counts['calls'], 1)
        self.assertIn('sample/raw.json', members)

    def test_partial_call_error_is_exported_unknown_no_retry(self):
        code, result, members, counts = self.exercise(failure='call')
        self.assertEqual((code, result['consumption']), (1, 'UNKNOWN_NO_RETRY'))
        self.assertIn('sample/native.json', members)
        self.assertNotIn('sample/result.json', members)
        self.assertEqual(counts['calls'], 1)

    def test_ram_blocks_before_load_or_call(self):
        _, result, _, counts = self.exercise(failure='ram')
        self.assertEqual(counts['loads'], 0)
        self.assertEqual(counts['calls'], 0)
        self.assertIn('16GIB', result['error']['message'])

    def test_bad_image_blocks_before_setup(self):
        _, result, _, counts = self.exercise(failure='image')
        self.assertEqual(counts['stages'], [])
        self.assertEqual(counts['calls'], 0)

    def test_disk_gate_blocks_before_setup(self):
        _, result, _, counts = self.exercise(failure='disk')
        self.assertEqual(counts['stages'], [])
        self.assertIn('RESOURCE_DISK', result['error']['message'])

    def test_vram_gate_blocks_before_load(self):
        _, result, _, counts = self.exercise(failure='vram')
        self.assertEqual(counts['loads'], 0)
        self.assertIn('RESOURCE_VRAM', result['error']['message'])

    def test_driver_gate_blocks_before_load(self):
        _, result, _, counts = self.exercise(failure='driver')
        self.assertEqual(counts['loads'], 0)
        self.assertIn('RESOURCE_DRIVER', result['error']['message'])

    def test_nonfinite_raw_is_saved_before_rejection(self):
        _, result, members, counts = self.exercise(failure='nonfinite')
        self.assertEqual(counts['calls'], 1)
        self.assertIn('sample/raw.json', members)
        self.assertNotIn('sample/result.json', members)
        self.assertIn('FINITE_PROOF', result['error']['message'])

    def test_decode_failure_raw_is_saved_before_rejection(self):
        _, result, members, counts = self.exercise(failure='decode')
        self.assertEqual(counts['calls'], 1)
        self.assertIn('sample/raw.json', members)
        self.assertNotIn('sample/result.json', members)

    def test_builder_embeds_exact_source_and_review_gate_without_credentials(self):
        from scripts import build_minicpm173_once as builder
        with patch.object(builder.subprocess, 'check_output', side_effect=lambda args, **kw:
                (run.ROOT / args[2].split(':', 1)[1]).read_bytes()):
            notebook = builder.build('a' * 40)
        code = ''.join(notebook['cells'][1]['source'])
        compile(code, '<synthetic-builder>', 'exec')
        self.assertIn('scripts.minicpm173_train_once import main', code)
        self.assertEqual(notebook['metadata']['safeshift']['limits'], c.LIMITS)
        self.assertEqual(notebook['metadata']['safeshift']['release'], 'OWNER_BOUNDED_DELEGATION_EXTERNAL_SEALED_SOURCE')
        self.assertNotIn('approval_comment', code)
        self.assertNotIn('kaggle.json', code)

    def test_missing_history_blocks_before_setup(self):
        _, result, _, counts = self.exercise(failure='history')
        self.assertEqual(counts['stages'], [])
        self.assertIn('ALL_FIVE', result['error']['message'])

    def test_bad_checkpoint_never_calls_model(self):
        _, result, _, counts = self.exercise(failure='checkpoint')
        self.assertEqual(counts['calls'], 0)
        self.assertIn('WEIGHT_CHECKSUM', result['error']['message'])

    def test_load_oom_preserves_reservation(self):
        _, result, members, counts = self.exercise(failure='oom')
        self.assertEqual(counts['calls'], 0)
        self.assertIn('load-reservation.json', members)
        self.assertFalse(result['weights_loaded'])

    def test_child_timeout_preserves_partial_evidence(self):
        _, result, members, counts = self.exercise(failure='timeout')
        self.assertEqual(counts['calls'], 0)
        self.assertIn('load-reservation.json', members)
        self.assertIn('HARD_DEADLINE', result['error']['message'])

    def test_permit_mismatch_and_expiry_fail_closed(self):
        with patch.object(c, 'remote_record', side_effect=[None, {'nonce': 'foreign'}]):
            with self.assertRaisesRegex(ValueError, 'NONCE_MISMATCH'):
                c.permit(self.ctx, 'launch', '', emit=Mock())
        expired = {**self.ctx, 'grant': {**self.grant, 'expires_unix': 0}}
        with patch.object(c, 'remote_record', return_value=None), self.assertRaises(TimeoutError):
            c.permit(expired, 'launch', '', emit=Mock())

    def test_source_drift_and_missing_source_inventory(self):
        with self.assertRaisesRegex(ValueError, 'COMPLETE_MINI_SOURCE_MANIFEST'):
            run.check_source({'runtime_commit': '1' * 40, 'manifest': {'synthetic': '0' * 64}})
        with patch.object(c, 'ROOT', self.root):
            (self.root / 'fixture.py').write_text('SYNTHETIC')
            with self.assertRaisesRegex(ValueError, 'SOURCE_DRIFT'):
                c.source_check({'runtime_commit': '1' * 40, 'manifest': {'fixture.py': '0' * 64}})

    def test_torn_result_does_not_prevent_partial_archive(self):
        from safeshift.pilot.artifacts import export
        out = self.root / 'partial'
        write(out / 'sample/reservation.json', {'synthetic': True})
        write(out / 'sample/native_call.json', {'synthetic': True})
        (out / 'sample/result.json').write_bytes(b'{"status":')
        summary = run.summarize(out)
        self.assertEqual(summary['status'], 'TECHNICAL_ERROR')
        self.assertEqual(summary['consumption'], 'UNKNOWN_NO_RETRY')
        write(out / 'summary.json', summary)
        export(out, self.root / 'partial.zip')
        self.assertIn('sample/result.json', verify_archive(self.root / 'partial.zip'))

    def test_remote_job_already_exists_or_status_unknown_blocks_submission(self):
        api = Mock()
        api.kernels_list_with_response.return_value = Mock(
            kernels=[Mock(ref=ref) for ref in submitter.kernel_sources()], next_page_token=None)
        with patch.object(submitter, 'get_kernel', return_value=Mock()):
            with self.assertRaisesRegex(ValueError, 'TARGET_ALREADY_EXISTS'):
                submitter.inventory(api)
        with patch.object(submitter, 'get_kernel', side_effect=TimeoutError('SYNTHETIC')):
            with self.assertRaisesRegex(ValueError, 'EXISTENCE_UNKNOWN'):
                submitter.inventory(api)
        api.kernels_push.assert_not_called()

    def test_403_alone_or_incomplete_owner_inventory_does_not_prove_absence(self):
        api = Mock()
        api.kernels_list_with_response.return_value = Mock(kernels=[], next_page_token=None)
        with patch.object(submitter, 'get_kernel') as get, self.assertRaisesRegex(ValueError, 'MISSING_KNOWN_PRIVATE'):
            submitter.inventory(api)
        get.assert_not_called()
        api.kernels_push.assert_not_called()

    def test_full_page_without_cursor_is_not_mistaken_for_complete_inventory(self):
        api = Mock()
        refs = submitter.kernel_sources()
        refs += ['nguynanhtn/synthetic-' + str(i) for i in range(100 - len(refs))]
        api.kernels_list_with_response.side_effect = [
            Mock(kernels=[Mock(ref=r) for r in refs], next_page_token=None),
            Mock(kernels=[Mock(ref=c.JOB)], next_page_token=None)]
        with self.assertRaisesRegex(ValueError, 'TARGET_ALREADY_EXISTS'):
            submitter.inventory(api)
        self.assertEqual(api.kernels_list_with_response.call_args.kwargs['page'], 2)
        api.kernels_push.assert_not_called()

    def test_live_log_split_chunks_duplicate_lines_and_wrong_version(self):
        challenges = []
        parent = ''
        for i, phase in enumerate(c.PHASES):
            challenges.append({'identity': c.IDENTITY, 'binding': digest(self.grant), 'phase': phase,
                               'nonce': str(i + 1) * 64, 'parent_nonce': parent})
            parent = challenges[-1]['nonce']
        text = ''.join('timestamp ' + c.PREFIX + json.dumps(v) + '\n' for v in challenges + challenges[-1:])
        api = Mock()
        api.kernels_logs_stream.return_value = iter([{'data': text[:53]}, {'data': text[53:]}])
        api.kernels_status.return_value.status = 'COMPLETE'
        with patch.object(submitter, 'live_identity', return_value=123), patch.object(c, 'create_record', side_effect=self.create):
            result = submitter.coordinate(api, self.grant, 5)
        self.assertEqual(result['permits'], ['launch', 'load', 'call'])
        self.assertEqual(list(self.ledger), ['launch', 'load', 'call'])
        api.kernels_logs_stream.assert_called_once_with(c.JOB + '/1')
        wrong = Mock()
        wrong.metadata.ref = c.JOB
        wrong.metadata.current_version_number = 2
        with patch.object(submitter, 'get_kernel', return_value=wrong), self.assertRaisesRegex(ValueError, 'VERSION_PRIVACY'):
            submitter.live_identity(api, self.grant)

    def test_broken_live_log_has_no_retry(self):
        api = Mock()
        api.kernels_logs_stream.side_effect = OSError('SYNTHETIC_LOG_DISCONNECT')
        with patch.object(c, 'create_record') as create, self.assertRaisesRegex(ValueError, 'TRANSPORT_ERROR'):
            submitter.coordinate(api, self.grant, 2)
        create.assert_not_called()
        api.kernels_logs_stream.assert_called_once()

    def test_complete_log_event_without_newline_is_acknowledged(self):
        challenge = {'identity': c.IDENTITY, 'binding': digest(self.grant), 'phase': 'launch',
                     'nonce': 'c' * 64, 'parent_nonce': ''}
        api = Mock()
        api.kernels_logs_stream.return_value = iter([{'data': c.PREFIX + json.dumps(challenge)}])
        api.kernels_status.return_value.status = 'COMPLETE'
        with patch.object(submitter, 'live_identity', return_value=123), patch.object(c, 'create_record', side_effect=self.create):
            result = submitter.coordinate(api, self.grant, 5)
        self.assertEqual(result['permits'], ['launch'])

    def test_only_live_log_transport_allows_silent_setup_without_retry(self):
        import types
        calls = []
        class Session:
            adapters = {'https': Mock(max_retries=Mock(total=0))}
            def send(self, request, **kwargs):
                calls.append(kwargs)
                return Mock()
        fake = types.SimpleNamespace(Session=Session)
        with patch.dict('sys.modules', {'requests': fake}), submitter.bounded_http():
            Session().send(Mock(url='https://api.kaggle.com/api/v1/kernels/logs/stream/owner/slug'))
            Session().send(Mock(url='https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel'))
        self.assertEqual([v['timeout'] for v in calls], [(10, 90), (10, 30)])
        self.assertTrue(all(v['allow_redirects'] is False for v in calls))

    def test_submission_timeout_burns_remote_slot_before_push(self):
        nb = {'metadata': {'safeshift': {'identity': c.IDENTITY, 'runtime_commit': self.grant['runtime_commit'],
              'manifest_sha256': self.grant['manifest_sha256'], 'limits': c.LIMITS}},
              'cells': [{'cell_type': 'code', 'source': ['# SYNTHETIC NEVER EXECUTED\n']}]}
        notebook = self.root / 'synthetic.ipynb'; write(notebook, nb)
        self.grant.update(notebook_sha256=sha(notebook), notebook_code_sha256=c.code_hash(nb))
        api = Mock()
        def push(*a, **kw):
            self.assertIn('submission', self.ledger)
            self.assertEqual((kw['timeout'], kw['acc']), ('1800', 'NvidiaTeslaT4'))
            raise TimeoutError('SYNTHETIC_PUSH_RESPONSE_UNKNOWN')
        api.kernels_push.side_effect = push
        with ExitStack() as stack:
            stack.enter_context(patch.object(submitter, 'make_grant', return_value=self.grant))
            stack.enter_context(patch.object(submitter, 'ROOT', self.root))
            stack.enter_context(patch.object(submitter, 'kernel_sources', return_value=['synthetic/history']))
            from scripts import build_minicpm173_once as builder
            stack.enter_context(patch.object(builder, 'build', return_value=nb))
            stack.enter_context(patch.object(submitter, 'predecessor_history', return_value=[]))
            stack.enter_context(patch.object(submitter.subprocess, 'check_output', side_effect=lambda args, **kw:
                self.grant['reviewed_head'] if 'rev-parse' in args else notebook.read_bytes() if 'show' in args else b''))
            stack.enter_context(patch.object(c, 'public_get', return_value={'head': {'sha': self.grant['reviewed_head'],
                'ref': c.BRANCH}, 'draft': True, 'merged': False}))
            stack.enter_context(patch.object(c, 'remote_record', side_effect=self.ledger.get))
            stack.enter_context(patch.object(c, 'create_record', side_effect=self.create))
            stack.enter_context(patch.object(submitter, 'paths_from_mounts', return_value=[]))
            stack.enter_context(patch.object(submitter, 'inspect_history', return_value={'consumed': {'qwen3': 1, 'internvl35': 1, 'minicpm4': 0}}))
            stack.enter_context(patch.object(submitter, 'diagnostic_history', return_value=[{'calls': 5}]))
            stack.enter_context(patch.object(submitter, 'inventory', return_value={'synthetic': True}))
            first_stage = self.root / 'absent-parent' / 'first'
            self.assertFalse(first_stage.parent.exists())
            with self.assertRaises(TimeoutError):
                submitter.submit(api, 7000000000, notebook, self.root, first_stage)
            self.assertTrue((first_stage / 'kernel-metadata.json').is_file())
            with self.assertRaisesRegex(ValueError, 'REMOTE_HISTORY_NONEMPTY'):
                submitter.submit(api, 7000000000, notebook, self.root, self.root / 'new-machine')
        api.kernels_push.assert_called_once()

    @unittest.skipUnless(sys.platform == 'linux', 'real supervised stdout relay')
    def test_child_challenge_is_relayed_without_private_lines(self):
        import threading
        log = self.root / 'native.log'
        stop = threading.Event()
        text = c.PREFIX + json.dumps({'synthetic': True})
        captured = io.StringIO()
        with redirect_stdout(captured):
            thread = threading.Thread(target=run.relay, args=(log, stop))
            thread.start()
            try:
                run.supervision.run([sys.executable, '-B', '-c',
                    'import time; print("PRIVATE_SYNTHETIC_LINE",flush=True); print(' + repr(text) + ',flush=True); time.sleep(.4)'],
                    cwd=self.root, env=os.environ.copy(), deadline=time.monotonic() + 5,
                    log=log, receipt=self.root / 'relay-child.json', max_log_bytes=2**20)
            finally:
                stop.set(); thread.join(timeout=2)
        self.assertIn(text, captured.getvalue())
        self.assertNotIn('PRIVATE_SYNTHETIC_LINE', captured.getvalue())

    @unittest.skipUnless(sys.platform == 'linux', 'real Linux process supervision')
    def test_actual_child_timeout_kills_group_and_keeps_log(self):
        with self.assertRaisesRegex(RuntimeError, 'HARD_DEADLINE'):
            run.supervision.run([sys.executable, '-B', '-c', 'import time; print("SYNTHETIC",flush=True); time.sleep(10)'],
                cwd=self.root, env=os.environ.copy(), deadline=time.monotonic() + .5,
                log=self.root / 'child.log', receipt=self.root / 'child.json', max_log_bytes=2**20)
        self.assertTrue(read(self.root / 'child.json')['group_kill_sent'])
        self.assertIn('SYNTHETIC', (self.root / 'child.log').read_text())


if __name__ == '__main__':
    unittest.main()
