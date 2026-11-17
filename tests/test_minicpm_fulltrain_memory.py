"""CPU-only RAM replay, owned-file advice and real Linux process supervision."""
from contextlib import ExitStack
from copy import deepcopy
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from safeshift.candidates.source import ROOT
from safeshift.fulltrain import memory as m, admission, supervision
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest
import test_fresh_fulltrain_revision as revisions
from test_fresh_fulltrain_revision import budgets


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.request = {'model_key': 'minicpm4', 'scratch': str(self.root / 'scratch'),
            'work': str(self.root / 'work'), 'resource_policy': {**budgets(), 'free_ram_mib': 16384}}
        for name in ('scratch', 'work'):
            (self.root / name).mkdir()

    def recorded(self, name='setup-after-child-exit-memory.json'):
        return read(ROOT / 'docs/research/evidence/issue173/review/minicpm-only-ram-preflight.json')['memory_stages'][name]

    def proc_fixture(self, row):
        proc, cg = self.root / 'proc', self.root / 'cg'
        (proc / 'self').mkdir(parents=True, exist_ok=True); cg.mkdir(exist_ok=True)
        (proc / 'meminfo').write_text(f"MemAvailable: {row['available_bytes'] // 1024} kB\n")
        rss = row['self_memory_kib']['Rss']
        (proc / 'self/status').write_text(f'VmRSS: {rss} kB\n')
        (proc / 'self/smaps_rollup').write_text(f'Rss: {rss} kB\n')
        for name, value in {'memory.current': row['cgroup_current_bytes'], 'memory.max': row['cgroup_max_bytes'],
                            'memory.stat': row['cgroup_stat'], 'memory.events': row['cgroup_events']}.items():
            (cg / name).write_text(''.join(f'{k} {v}\n' for k, v in value.items()) if isinstance(value, dict) else str(value))
        return proc, cg

    def observed(self):
        return m.snapshot(*self.proc_fixture(self.recorded()))

    def test_real_issue173_file_cache_decline_and_unchanged_floor(self):
        before = self.recorded(); after = self.recorded('after-cache-advice-memory.json')
        self.assertEqual(before['available_bytes'], 17761562624)
        self.assertEqual(after['available_bytes'], 25173176320)
        self.assertGreater(before['cgroup_stat']['file'] - after['cgroup_stat']['file'], 7 * 10**9)
        self.assertLess(abs(before['cgroup_stat']['anon'] - after['cgroup_stat']['anon']), 2 * 2**20)
        for row in (before, after, self.recorded('before-weight-load-memory.json')):
            snap = m.snapshot(*self.proc_fixture(row))
            m.complete(snap)
            self.assertEqual(snap['gate_memory']['available_bytes'], row['available_bytes'])
            self.assertGreaterEqual(snap['gate_memory']['available_bytes'], 16 * 2**30)

    def test_missing_malformed_negative_cgroup_or_oom_blocks(self):
        for field, value in [('memory.stat', ''), ('memory.stat', 'anon -1\nfile 1\ninactive_file 1\n'),
                             ('memory.max', '-1'), ('memory.events', 'oom 1\noom_kill 0\n'),
                             ('memory.current', 'invalid')]:
            with self.subTest(field=field, value=value):
                proc, cg = self.proc_fixture(self.recorded())
                (cg / field).write_text(value)
                observed = m.snapshot(proc, cg)
                with self.assertRaises(ValueError): m.complete(observed)

    def test_exact_boundary_and_failure_receipts_no_model(self):
        observed = self.observed()
        for free in (16 * 2**30 - 1, 16 * 2**30):
            out = self.root / str(free); out.mkdir()
            with patch.object(m, 'snapshot', return_value=observed), \
                    patch.object(m.environment, 'host_memory', return_value={'available_bytes': free}), \
                    patch.object(m.environment.shutil, 'disk_usage', return_value=type('Disk', (), {'free': 2**40})()):
                if free < 16 * 2**30:
                    with self.assertRaisesRegex(ValueError, 'HOST_OR_CGROUP_RAM'): m.resource_check(self.request, out, 'load')
                    self.assertTrue((out / 'load-failure.json').is_file())
                else:
                    self.assertEqual(m.resource_check(self.request, out, 'load')['memory']['available_bytes'], free)
                self.assertTrue((out / 'load-after-memory.json').is_file())

    def test_reclaim_success_is_fresh_gate_and_no_effect_stays_blocked(self):
        out = self.root / 'control/reclaim'; out.mkdir(parents=True)
        write(out.parent / 'owned-scratch.json', m.ownership(self.request))
        write(out.parent / 'setup-process.json', {'status': 'EXITED', 'returncode': 0, 'group_exit': {'status': 'NO_LIVE_MEMBERS'}})
        write(out.parent / 'setup/runtime.json', {'request_sha256': digest(self.request)})
        for n, effect in enumerate((None, ValueError('HOST_OR_CGROUP_RAM'), KeyboardInterrupt())):
            with self.subTest(effect=type(effect).__name__), patch.object(m, 'snapshot', return_value=self.observed()), \
                    patch.object(m, 'advise_owned_runtime', return_value={'scan_complete': True}), \
                    patch.object(m, 'resource_check', side_effect=effect) as gate:
                target = out if n == 0 else out.parent / f'case{n}'; target.mkdir(exist_ok=True)
                if effect:
                    with self.assertRaises(type(effect)): m.reclaim(self.request, target, time.monotonic()+10)
                else:
                    m.reclaim(self.request, target, time.monotonic()+10)
                gate.assert_called_once()
                self.assertTrue((target / 'owned-advice-after-memory.json').exists())

    def test_missing_ownership_or_scan_error_never_runs_gate(self):
        out = self.root / 'control/reclaim'; out.mkdir(parents=True)
        write(out.parent / 'setup-process.json', {'status': 'EXITED', 'returncode': 0, 'group_exit': {'status': 'NO_LIVE_MEMBERS'}})
        write(out.parent / 'setup/runtime.json', {})
        with patch.object(m, 'snapshot', return_value=self.observed()), patch.object(m, 'resource_check') as gate:
            with self.assertRaises(FileNotFoundError): m.reclaim(self.request, out, time.monotonic()+5)
            gate.assert_not_called()
        self.assertTrue((out / 'owned-advice-after-memory.json').exists())

    def test_live_setup_child_prevents_any_advice(self):
        out = self.root / 'control/reclaim'; out.mkdir(parents=True)
        write(out.parent / 'setup-process.json', {'status': 'EXITED', 'returncode': 0,
            'group_exit': {'status': 'LIVE_SURVIVORS'}})
        with patch.object(m, 'snapshot', return_value=self.observed()), patch.object(m, 'advise_owned_runtime') as advice:
            with self.assertRaisesRegex(ValueError, 'SETUP_GROUP_EXIT'): m.reclaim(self.request, out, time.monotonic()+5)
            advice.assert_not_called()

    def test_loader_guard_ram_drop_after_processor_or_rehash_prevents_weight_load(self):
        from safeshift.candidates import backend, loading
        original_processor, original_loader = backend.native_setup, backend.load_weight_model
        for fail_at in ('before-processor', 'after-processor', 'before-weight-deserialization'):
            calls = []
            def check(request, output, name):
                calls.append(name)
                if name == fail_at: raise ValueError('HOST_OR_CGROUP_RAM')
            loaded = Mock()
            def loader(*args, weight_verifier=None, **kwargs):
                weight_verifier('synthetic-weights', 'minicpm4'); loaded()
            with patch.object(backend, 'native_setup', return_value=('synthetic',)*4), \
                    patch.object(backend, 'load_weight_model', side_effect=loader), \
                    patch.object(loading, 'verify_weights', return_value={'all_actual_bytes_checked': True}), \
                    patch.object(m, 'resource_check', side_effect=check), patch.object(m, 'observe'):
                with m.load_guard(self.request, self.root):
                    with self.assertRaisesRegex(ValueError, 'HOST_OR_CGROUP_RAM'):
                        backend.native_setup('snapshot', 'minicpm4', {})
                        backend.load_weight_model('snapshot', 'minicpm4', None, None, 'weights', 'cuda:0')
                loaded.assert_not_called()
            self.assertIs(backend.native_setup, original_processor)
            self.assertIs(backend.load_weight_model, original_loader)

    @unittest.skipUnless(sys.platform == 'linux', 'POSIX directory-FD advice')
    def test_owned_advice_complete_bounded_preserves_bytes_and_rejects_aliases(self):
        scratch = Path(self.request['scratch']); prefix = scratch / 'venv3119'
        lib = prefix / 'lib'; lib.mkdir(parents=True)
        file = lib / 'owned.so'; file.write_bytes(b's' * 8 * 2**20)
        owned = m.ownership(self.request)
        installed = {'request_sha256': digest(self.request), 'python': str(prefix / 'bin/python'),
                     'env': {'SAFESHIFT_RUNTIME_ROOT': str(prefix)}}
        before = sha(file)
        result = m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5)
        self.assertTrue(result['scan_complete']); self.assertEqual(result['advised_files'], 1)
        self.assertEqual(sha(file), before); self.assertEqual(result['deleted_files'], 0)
        for alias in ('symlink', 'hardlink', 'fifo', 'dirlink'):
            path = lib / 'alias'
            if alias == 'symlink': path.symlink_to(file)
            elif alias == 'hardlink': os.link(file, path)
            elif alias == 'fifo': os.mkfifo(path)
            else: path.symlink_to(lib, target_is_directory=True)
            with patch.object(m.os, 'posix_fadvise') as advice:
                with self.assertRaises(ValueError): m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5)
                advice.assert_not_called()
            path.unlink()
        (lib / 'small').write_text('synthetic')
        with patch.object(m.os, 'posix_fadvise') as advice:
            with self.assertRaisesRegex(ValueError, 'SCAN_LIMIT'):
                m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5, max_entries=1)
            advice.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'DEADLINE'):
            m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()-1)
        with self.assertRaisesRegex(ValueError, 'OWNERSHIP'):
            m.advise_owned_runtime(self.request, {**owned, 'inode': -1}, installed, deadline=time.monotonic()+5)
        with patch.object(m.os, 'posix_fadvise', side_effect=OSError('SYNTHETIC')):
            with self.assertRaises(OSError): m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5)
        self.assertEqual(sha(file), before)


class PipelineTests(unittest.TestCase):
    def test_post_image_ram_failure_stops_actual_generate_and_native_receipt(self):
        from safeshift.fulltrain import minicpm_release as a, minicpm_recovery
        from types import SimpleNamespace as NS
        model = NS(generate=Mock())
        backend = NS(model=model, generate=lambda *_: model.generate())
        context = {'grant': {'schema': a.RECOVERY_SCHEMA}, 'value': {'request': {},
            'cohort': {'samples': [{'sample_id': 'SYNTHETIC', 'image_sha256': 'a'*64}]}}}
        with patch.object(a, 'current', return_value=context), patch.object(a, 'authorize'), \
                patch.object(m, 'resource_check', side_effect=ValueError('HOST_OR_CGROUP_RAM')), \
                patch.object(minicpm_recovery, 'native_started') as native:
            with self.assertRaisesRegex(ValueError, 'HOST_OR_CGROUP_RAM'):
                a.GuardedBackend(backend, 0).generate('synthetic', 'synthetic')
            model.generate.assert_not_called(); native.assert_not_called()

    def test_setup_then_reclaim_failure_stops_before_cpu_gpu_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = revisions.RevisionTests(); fixture.root = Path(tmp)
            request = fixture.request('minicpm4')
            request['resource_policy']['free_ram_mib'] = 16384
            stages = []
            def run(command, **kwargs):
                mode = command[command.index('--stage') + 1]; stages.append(mode)
                output = Path(command[command.index('--output') + 1]); output.mkdir()
                if mode == 'reclaim': raise RuntimeError('SUPERVISED_CHILD_FAILURE')
                write(output / 'stage.json', {'status': 'RETURNED', 'stage': mode,
                    'request_sha256': digest(request), 'source_sha256': request['source_sha256'], 'native_attempt_permitted': False})
                if mode == 'setup':
                    write(output / 'runtime.json', {'request_sha256': digest(request),
                        'python': str(Path(request['scratch']) / 'venv3119/bin/python'), 'env': {'CUDA_VISIBLE_DEVICES': ''}})
            with patch.object(admission.supervision, 'run', side_effect=run), patch.object(m, 'observe'), \
                    patch.object(admission.runtime, '_native_factory') as load:
                out = admission.launch_prepared(request)
            self.assertEqual(stages, ['admit', 'setup', 'reclaim']); load.assert_not_called()
            self.assertEqual(read(out / 'release.json')['status'], 'BLOCKED')
            self.assertTrue(Path(str(out) + '.zip').exists())

    def test_child_interruption_keeps_memory_and_failure_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            fixture = revisions.RevisionTests(); fixture.root = Path(tmp)
            request = fixture.request('minicpm4'); output = Path(tmp) / 'stage'
            with patch.object(admission, 'admit', side_effect=KeyboardInterrupt()), patch.object(m, 'snapshot', return_value={'status': 'INCOMPLETE'}):
                with self.assertRaises(KeyboardInterrupt): admission.stage('setup', request, ROOT, output, time.monotonic()+10)
            self.assertEqual(read(output / 'failure.json')['type'], 'KeyboardInterrupt')
            self.assertTrue((output / 'stage-entry-memory.json').exists()); self.assertTrue((output / 'stage-exit-memory.json').exists())


@unittest.skipUnless(sys.platform == 'linux', 'Linux process groups')
class ProcessTests(unittest.TestCase):
    def test_real_success_and_timeout_kill_descendants_before_next_stage(self):
        for timeout in (False, True):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                code = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); " + ('time.sleep(30)' if timeout else 'time.sleep(.05)')
                args = dict(cwd=root, env=dict(os.environ), deadline=time.monotonic() + (1 if timeout else 10),
                    log=root/'stage.log', receipt=root/'process.json', max_log_bytes=100000)
                if timeout:
                    with self.assertRaisesRegex(RuntimeError, 'HARD_DEADLINE'): supervision.run([sys.executable, '-c', code], **args)
                else:
                    supervision.run([sys.executable, '-c', code], **args)
                self.assertEqual(read(root/'process.json')['group_exit']['status'], 'NO_LIVE_MEMBERS')

    def test_unverified_cleanup_or_live_child_blocks_even_exit_zero(self):
        for result in ({'status': 'LIVE_SURVIVORS', 'members': [{'pid': 123, 'state': 'S'}]}, OSError('SYNTHETIC')):
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                options = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                with patch.object(supervision, 'wait_group_exit', **options):
                    with self.assertRaisesRegex(RuntimeError, 'PROCESS_GROUP'):
                        supervision.run([sys.executable, '-c', 'pass'], cwd=root, env=dict(os.environ),
                            deadline=time.monotonic()+5, log=root/'s.log', receipt=root/'s.json', max_log_bytes=10000)
                self.assertTrue((root/'s.json').is_file())
