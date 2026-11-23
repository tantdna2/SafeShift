"""CPU-only RAM replay, owned-file advice and real Linux process supervision."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
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

    def test_released_cpu_budget_and_other_stage_limits(self):
        request = self.request | {"original_inputs": {}, "plan": {"max_seconds": 14400}}
        request["resource_policy"].update(setup_seconds=1800, diagnostic_seconds=600)
        active = {"grant": {"continuation": {}, "sizing": {"export_seconds": 600}}}
        until = admission.stage_deadline("cpu", request, 14400, active, now=100)
        self.assertLess(100 + 601, until)
        self.assertEqual(until, 100 + 1200)
        self.assertEqual(admission.stage_deadline("cpu", request, 14400, None, now=100), 700)
        for mode in ("gpu", "reclaim"):
            self.assertEqual(admission.stage_deadline(mode, request, 14400, active, now=100), 700)
        self.assertEqual(admission.stage_deadline("setup", request, 14400, active, now=100), 1900)
        for mode in ("admit", "setup", "reclaim", "cpu", "gpu", "native"):
            self.assertEqual(admission.stage_deadline(mode, request, 14400, active, now=13799), 13800)

    def test_export_reserve_exhaustion_never_starts_a_child(self):
        from safeshift.fulltrain import minicpm_execution, minicpm_release
        request = self.request | {"inputs": str(self.root / "inputs"), "software_input": None,
            "original_inputs": {}, "source_sha256": "a" * 64, "campaign": {},
            "plan": {"run_id": "synthetic", "max_seconds": 600, "scheduled_ordinals": [0]}}
        claims = self.root / "claims"
        write(claims / "launch.json", {"time_unix": 100})
        active = {"grant": {"continuation": {}, "sizing": {"export_seconds": 600}},
            "locator": {}, "ticket": {}, "claims": claims, "capsule_directory": self.root}
        with ExitStack() as stack:
            for obj, name, value in (
                (admission, "validate_request", None), (m, "observe", None),
                (minicpm_release, "current", active), (minicpm_release, "authorize", None),
                (minicpm_release, "claims_snapshot", {}), (minicpm_execution, "retain_sealed_trees", {}),
                (time, "time", 100), (time, "monotonic", 200),
            ):
                stack.enter_context(patch.object(obj, name, return_value=value))
            supervise = stack.enter_context(patch.object(supervision, "run"))
            output = admission.launch_prepared(request)
        supervise.assert_not_called()
        self.assertEqual(read(output / "admit-budget.json"), {"seconds": 0, "export_seconds": 600})
        self.assertEqual(read(output / "release.json")["status"], "BLOCKED")
        self.assertIn("STAGE_NO_TIME_BEFORE_EXPORT_RESERVE", read(output / "failure.json")["message"])
        self.assertTrue(output.with_suffix(".zip").is_file())

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

    def test_readonly_hash_ranges_final_advice_and_no_fsync(self):
        path = self.root / 'input'
        data = b'X' * (8 * 2**20 + 4099)
        path.write_bytes(data)
        with patch.object(os, 'posix_fadvise', create=True) as advice, \
                patch.object(os, 'POSIX_FADV_DONTNEED', 4, create=True), \
                patch.object(os, 'POSIX_FADV_RANDOM', 1, create=True), \
                patch.object(os, 'sysconf', return_value=4096, create=True), patch.object(os, 'fsync') as sync:
            self.assertEqual(m.stream_readonly_sha256(path, expected_size=len(data)), hashlib.sha256(data).hexdigest())
            self.assertEqual([c.args[1:] for c in advice.call_args_list],
                             [(0, 0, 1), (0, 8*2**20, 4), (8*2**20, 4096, 4), (0, 0, 4)])
            advice.reset_mock()
            with patch.object(os, 'read', side_effect=AssertionError('eviction must not read')):
                self.assertEqual(m.evict_readonly_file(path)['advised'], True)
            self.assertEqual([c.args[1:] for c in advice.call_args_list], [(0, 0, 4)])
            sync.assert_not_called()

    def test_readonly_changed_fd_size_or_deadline_stop(self):
        path = self.root / 'input'
        path.write_bytes(b'synthetic')
        for func in (m.stream_readonly_sha256, m.evict_readonly_file):
            with self.assertRaisesRegex(ValueError, 'EXPECTED_SIZE'):
                func(path, expected_size=12)
            with self.assertRaisesRegex(ValueError, 'DEADLINE'):
                func(path, deadline=time.monotonic()-1)
            other = self.root.stat()
            with patch.object(os, 'fstat', side_effect=[path.stat(), other]):
                with self.assertRaisesRegex(ValueError, 'FILE_CHANGED'):
                    func(path)
        with patch.object(m.time, 'monotonic', side_effect=[1, 2, 4]):
            with self.assertRaisesRegex(ValueError, 'DEADLINE'):
                m.stream_readonly_sha256(path, deadline=3)

    @unittest.skipUnless(sys.platform == 'linux', 'POSIX aliases and special files')
    def test_readonly_rejects_fifo_links_and_symlink_parent(self):
        file = self.root / 'ordinary'
        file.touch()
        link = self.root / 'alias'
        link.symlink_to(file)
        parent = self.root / 'parent-link'
        parent.symlink_to(self.root, target_is_directory=True)
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        for item in (link, parent / file.name, fifo):
            for func in (m.stream_readonly_sha256, m.evict_readonly_file):
                with self.assertRaises(ValueError):
                    func(item)

    def test_postload_advises_every_locked_shard_with_exact_sizes(self):
        from safeshift.candidates.source import LOCK
        locked = read(LOCK.with_name('checkpoint_metadata_lock.json'))['minicpm4']['weights']
        with patch.object(m, 'evict_readonly_file', return_value={'advised': True}) as evict:
            receipt = m.advise_readonly_weights(self.root, deadline=99)
        self.assertEqual(set(receipt['files']), set(locked))
        self.assertEqual([(c.args[0], c.kwargs) for c in evict.call_args_list],
                         [(self.root / name, {'expected_size': row['size'], 'deadline': 99})
                          for name, row in locked.items()])

    def test_loader_hashes_then_advises_before_after_load_gate(self):
        from safeshift.candidates import backend, loading
        shard = self.root / 'synthetic-shard'
        shard.write_bytes(b'shard')
        calls = []
        def verify(path, key, *, hash_reader):
            self.assertEqual(hash_reader(shard), hashlib.sha256(b'shard').hexdigest())
            calls.append('hash')
        def load(snapshot, key, config, cls, weights, device, *, weight_verifier):
            weight_verifier(weights, key)
            calls.append('load')
            return 'model'
        def advise(weights, key, *, deadline):
            calls.append('advice')
            return {'files': 1}
        with patch.object(backend, 'load_weight_model', side_effect=load), \
             patch.object(loading, 'verify_weights', side_effect=verify), \
             patch.object(m, 'observe'), patch.object(m, 'advise_readonly_weights', side_effect=advise), \
             patch.object(m, 'resource_check', side_effect=lambda r, o, n: calls.append(n)):
            with m.load_guard(self.request, self.root):
                self.assertEqual(backend.load_weight_model(None, 'minicpm4', None, None, self.root, 'cuda:0'), 'model')
        self.assertEqual(calls, ['hash', 'before-weight-deserialization', 'load', 'advice', 'after-weight-load'])
        self.assertEqual(read(self.root / 'post-weight-load-advice.json'), {'files': 1})

    @unittest.skipUnless(sys.platform == 'linux', 'POSIX directory-FD advice')
    def test_owned_advice_complete_bounded_preserves_bytes_and_rejects_aliases(self):
        scratch = Path(self.request['scratch']); prefix = scratch / 'venv3119'
        lib = prefix / 'lib'; lib.mkdir(parents=True)
        file = lib / 'owned.so'; file.write_bytes(b's' * 8 * 2**20)
        owned = m.ownership(self.request)
        installed = {'request_sha256': digest(self.request), 'python': str(prefix / 'bin/python'),
                     'env': {'SAFESHIFT_RUNTIME_ROOT': str(prefix)}}
        from safeshift import internvl3763_python as py
        for directory in (lib, prefix / 'bin', scratch / 'input-cpython3119/lib', scratch / 'pip-bootstrap'):
            directory.mkdir(exist_ok=True, parents=True)
            (directory / 'tiny').write_bytes(b'x')
        (scratch / py.manifest()['filename']).write_bytes(b'archive')
        (prefix / 'bin/python').symlink_to('../lib/tiny')
        (scratch / 'input-cpython3119/lib/libpython.so').symlink_to('tiny')
        (scratch / 'outside-allowlist').write_bytes(b'untouched')
        before = sha(file)
        result = m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5)
        self.assertTrue(result['scan_complete']); self.assertEqual(result['advised_files'], 6)
        self.assertEqual(result['skipped_symlinks'], 2)
        self.assertEqual(result['advised_bytes'], file.stat().st_size + 11)
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


    @unittest.skipUnless(sys.platform == 'linux', 'POSIX directory-FD advice')
    def test_owned_pass_two_reuses_directories_for_a_wide_deep_tree(self):
        scratch = Path(self.request['scratch'])
        prefix = scratch / 'venv3119'
        leaf = prefix / 'lib' / Path(*(['nested'] * 20))
        leaf.mkdir(parents=True)
        for i in range(300):
            (leaf / f'{i:04}.so').write_bytes(b'x')
        owned = m.ownership(self.request)
        installed = {'request_sha256': digest(self.request), 'python': str(prefix / 'bin/python'),
                     'env': {'SAFESHIFT_RUNTIME_ROOT': str(prefix)}}
        original_open = os.open
        directory_opens = []
        def counted_open(name, flags, *args, **kwargs):
            if flags & os.O_DIRECTORY:
                directory_opens.append(name)
            return original_open(name, flags, *args, **kwargs)
        open_fds = len(list(Path('/proc/self/fd').iterdir()))
        with patch.object(m.os, 'open', side_effect=counted_open), patch.object(m.os, 'fsync'), \
                patch.object(m.os, 'posix_fadvise') as advice:
            result = m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+10)
        self.assertEqual(result['advised_files'], 300)
        self.assertEqual(advice.call_count, 300)
        self.assertEqual(len(directory_opens), 1 + 2 * 22)
        self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), open_fds)

        (leaf / Path(*(['deeper'] * 43))).mkdir(parents=True)
        with patch.object(m.os, 'posix_fadvise') as advice:
            with self.assertRaisesRegex(ValueError, 'ADVICE_SCAN_LIMIT'):
                m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+10)
            advice.assert_not_called()
        self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), open_fds)

    @unittest.skipUnless(sys.platform == 'linux', 'POSIX directory-FD advice')
    def test_owned_pass_two_rejects_changed_inode_and_metadata(self):
        scratch = Path(self.request['scratch'])
        prefix = scratch / 'venv3119'
        path = prefix / 'lib' / 'owned.so'
        path.parent.mkdir(parents=True)
        owned = m.ownership(self.request)
        installed = {'request_sha256': digest(self.request), 'python': str(prefix / 'bin/python'),
                     'env': {'SAFESHIFT_RUNTIME_ROOT': str(prefix)}}
        real_stat = os.stat
        for mutation in ('inode', 'size', 'mode'):
            with self.subTest(mutation=mutation):
                path.write_bytes(b'x')
                path.chmod(0o600)
                seen = 0
                def stat_after_inventory(name, *args, **kwargs):
                    nonlocal seen
                    if name == path.name and kwargs.get('dir_fd') is not None:
                        seen += 1
                        if seen == 2:
                            if mutation == 'inode':
                                replacement = path.with_suffix('.new')
                                replacement.write_bytes(b'x')
                                replacement.replace(path)
                            elif mutation == 'size':
                                path.write_bytes(b'xx')
                            else:
                                path.chmod(0o640)
                    return real_stat(name, *args, **kwargs)
                open_fds = len(list(Path('/proc/self/fd').iterdir()))
                with patch.object(os, 'stat', side_effect=stat_after_inventory), patch.object(os, 'posix_fadvise') as advice:
                    with self.assertRaisesRegex(ValueError, 'ADVICE_FILE_CHANGED'):
                        m.advise_owned_runtime(self.request, owned, installed, deadline=time.monotonic()+5)
                    advice.assert_not_called()
                self.assertEqual(seen, 2)
                self.assertEqual(len(list(Path('/proc/self/fd').iterdir())), open_fds)


class PipelineTests(unittest.TestCase):
    def test_controller_preserves_calls_raw_and_primary_error_before_image_advice(self):
        from test_fresh_fulltrain import FreshTests, Scripted
        from safeshift.candidates.fulltrain_run import BoundStore
        from safeshift.fulltrain import runtime, minicpm_release
        fixture = FreshTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        for case, model_error, advice_error, expired, stop, calls in (
            ('ok', False, False, False, None, 2),
            ('advice', False, True, False, 'IMAGE_CACHE_ADVICE_FAILURE', 1),
            ('model', True, False, False, 'TECHNICAL_STOP', 1),
            ('both', True, True, False, 'TECHNICAL_STOP', 1),
            ('expiry', False, False, True, 'ADAPTIVE_TIME_STOP', 1),
        ):
            with self.subTest(case=case):
                p = fixture.plan(name=case, cap=2)
                work = fixture.root / ('work-' + case)
                claims = fixture.root / ('claims-' + case)
                write(claims / 'launch.json', {'time_unix': time.time()})
                active = {'value': {'request': {'plan': p}}, 'locator': {}, 'ticket': {}, 'claims': claims,
                          'grant': {'sizing': {'export_seconds': 5, 'first_call_seconds': 1, 'safety_milli': 1000}}}
                result_text = '{"safety_level":"Level04"}'
                native = Scripted([ValueError('SYNTHETIC_MODEL_FAILURE') if model_error else result_text, result_text])
                now = Mock(return_value=0.0)
                generate = native.generate

                def timed_generate(*args):
                    try:
                        return generate(*args)
                    finally:
                        now.return_value += 56.0 if expired else 2.0

                native.generate = timed_generate

                def advice(path, *, deadline):
                    ordinal = int(Path(path).stem)
                    call = work / case / f'calls/{ordinal:06d}/run'
                    sample = call / 'samples/000000'
                    self.assertTrue((sample / 'result.json').is_file())
                    self.assertEqual((sample / 'raw.json').is_file(), not model_error)
                    self.assertTrue((work / case / f'checkpoints/{ordinal:06d}.json').is_file())
                    self.assertGreater(deadline, time.monotonic())
                    if advice_error:
                        raise OSError('SYNTHETIC_ADVICE_FAILURE')
                    return {'advised': True}

                with patch.object(minicpm_release, 'current', return_value=active), \
                     patch.object(minicpm_release, 'GuardedBackend', side_effect=lambda backend, _: backend), \
                     patch.object(minicpm_release, 'claims_snapshot', return_value={}), \
                     patch.object(m, 'evict_readonly_file', side_effect=advice) as evict:
                    root = runtime._execute(work, fixture.bundle, fixture.cohort, fixture.campaign, p, [],
                        lambda: native, image_path=lambda i: f'{i:06d}.bin', store_class=BoundStore, clock=now)
                receipt = read(root / 'receipt.json')
                self.assertEqual((receipt['native_calls'], receipt['observed_native_markers'], native.calls), (calls,) * 3)
                self.assertEqual(receipt['stop'], stop)
                self.assertEqual(read(root / 'timing.json')['call_seconds'], [56.0 if expired else 2.0] * calls)
                self.assertEqual(evict.call_count, 0 if expired else calls)
                self.assertFalse((root / 'accounting_failure.json').exists())
                self.assertTrue(root.with_suffix('.zip').is_file())
                for ordinal in range(calls):
                    call = root / f'calls/{ordinal:06d}/run'
                    sample = call / 'samples/000000'
                    status = 'TECHNICAL_ERROR' if model_error else 'SUCCESS'
                    self.assertEqual(read(sample / 'result.json')['status'], status)
                    self.assertEqual(read(root / 'accounting.json')['samples'][ordinal]['status'], status)
                    if model_error:
                        self.assertIn('SYNTHETIC_MODEL_FAILURE', read(call / 'failure.json')['message'])
                    else:
                        self.assertEqual(read(sample / 'result.json')['raw_sha256'], sha(sample / 'raw.json'))
                    self.assertEqual(read(root / f'checkpoints/{ordinal:06d}.json')['native_calls'], ordinal + 1)
                    self.assertEqual(read(call / 'image-cache-advice.json')['status'],
                                     'DEADLINE' if expired else 'FAILED' if advice_error else 'RETURNED')
                if calls == 1:
                    self.assertEqual(read(root / 'accounting.json')['samples'][1]['status'], 'NOT_ATTEMPTED')

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
