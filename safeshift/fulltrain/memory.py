"""Full-TRAIN file cache advice and fresh host/cgroup resource admission."""
import hashlib
import os
from pathlib import Path
import stat
import time
from contextlib import contextmanager

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest
from safeshift import internvl_v2_memory as precedent
from . import environment


def snapshot(proc=Path('/proc'), cgroup=Path('/sys/fs/cgroup')):
    value = precedent.snapshot(proc, cgroup)
    value['time_unix'] = time.time()
    try:
        with (proc / 'meminfo').open() as stream:
            raw = stream.read(65537)
        require(len(raw) <= 65536, 'MEMINFO_BOUND')
        rows = dict(line.split(':', 1) for line in raw.splitlines())
        value['host_mem_available_bytes'] = int(rows['MemAvailable'].split()[0]) * 1024
        require(value['host_mem_available_bytes'] >= 0, 'NEGATIVE_HOST_MEMORY')
        value['host_memory_bytes'] = {
            name: int(rows[name].split()[0]) * 1024
            for name in ('MemTotal', 'MemFree', 'Buffers', 'Cached', 'SReclaimable', 'Shmem', 'Dirty', 'Writeback')
            if name in rows
        }
    except (OSError, ValueError, KeyError, IndexError) as error:
        value['errors'].append({'file': 'meminfo', 'type': type(error).__name__})
    cg = value['cgroup']
    numbers = [cg.get('memory.current'), *cg.get('memory.stat', {}).values(),
               *cg.get('memory.events', {}).values()]
    maximum = cg.get('memory.max')
    events = cg.get('memory.events', {})
    if (not all(type(n) is int and n >= 0 for n in numbers)
            or not (maximum == 'max' or type(maximum) is int and maximum > 0)
            or not {'oom', 'oom_kill'} <= events.keys()
            or not {'anon', 'file', 'inactive_file'} <= cg.get('memory.stat', {}).keys()
            or not value.get('gate_memory')
            or type(value['gate_memory'].get('available_bytes')) is not int
            or value['gate_memory']['available_bytes'] < 0):
        value['errors'].append({'file': 'required_fields', 'type': 'INVALID_MEMORY_COUNTERS'})
    value['status'] = 'INCOMPLETE' if value['errors'] else 'OBSERVED'
    return value


def observe(out, name):
    value = snapshot()
    write(Path(out) / (name + '-memory.json'), value)
    return value


def ct1_ram_gate(out, name, floor):
    """Record the exact operands and keep the conservative host/cgroup minimum."""
    observe(out, name + '-before')
    try:
        return environment.check_ram(floor, receipt=Path(out) / (name + '.json'), include_ancestors=True)
    except (OSError, ValueError, KeyError):
        observe(out, name + '-failure')
        raise


def complete(value):
    require(value['status'] == 'OBSERVED', 'MEMORY_DIAGNOSTICS_INCOMPLETE')
    events = value['cgroup']['memory.events']
    require(events['oom'] == events['oom_kill'] == 0, 'CGROUP_OOM_OBSERVED_STOP')


def resource_check(request, out, name):
    """Retain near-sampled diagnostics and the separate, fresh unchanged gate."""
    before = observe(out, name + '-before')
    try:
        complete(before)
        result = environment.resources(request['model_key'], request['resource_policy'],
                                       request['scratch'], request['work'])
        write(Path(out) / (name + '-resources.json'), result)
        return result
    except BaseException as error:
        write(Path(out) / (name + '-failure.json'), {'type': type(error).__name__, 'message': str(error)})
        raise
    finally:
        complete(observe(out, name + '-after'))


def ownership(request):
    scratch = Path(request['scratch'])
    for parent in (scratch, *scratch.parents):
        snapshot_stat(parent, directory=True)
    info = scratch.stat()
    return {'schema': 'minicpm-owned-empty-scratch-v1', 'request_sha256': digest(request),
            'device': info.st_dev, 'inode': info.st_ino}


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def check_deadline(deadline):
    require(deadline is None or time.monotonic() < deadline, 'READONLY_ADVICE_DEADLINE')


@contextmanager
def readonly_fd(path, expected_size, deadline, *, expected_identity=None, advise_file=None,
                advise_whole_file=True):
    path = Path(path)
    advise_file = os.posix_fadvise if advise_file is None and hasattr(os, 'posix_fadvise') else advise_file
    check_deadline(deadline)
    for parent in path.parents:
        snapshot_stat(parent, directory=True)
    before = snapshot_stat(path)
    require(expected_size is None or before.st_size == expected_size, 'READONLY_EXPECTED_SIZE')
    require(expected_identity is None or identity(before) == expected_identity, 'READONLY_FILE_CHANGED')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                 | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    try:
        require(identity(os.fstat(fd)) == identity(before), 'READONLY_OPEN_CHANGED')
        advice = hasattr(os, 'posix_fadvise') and hasattr(os, 'POSIX_FADV_DONTNEED')
        try:
            yield fd, before.st_size, advice
        finally:
            if advice and advise_whole_file:
                advise_file(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        require(identity(os.fstat(fd)) == identity(before)
                and identity(snapshot_stat(path)) == identity(before), 'READONLY_FILE_CHANGED')
        check_deadline(deadline)
    finally:
        os.close(fd)


def stream_readonly_sha256(path, *, expected_size=None, deadline=None, copy_to=None,
                           expected_identity=None, advice_errors=None, advise_whole_file=True):
    hashed = hashlib.sha256()
    failed_hints = set()

    def advise_file(fd, offset, length, hint):
        if hint in failed_hints:
            return
        try:
            os.posix_fadvise(fd, offset, length, hint)
        except OSError as error:
            if advice_errors is None:
                raise
            failed_hints.add(hint)
            advice_errors.append({"file": Path(path).name, "hint": hint, "errno": error.errno})

    with readonly_fd(path, expected_size, deadline, expected_identity=expected_identity,
                     advise_file=advise_file, advise_whole_file=advise_whole_file) as (fd, size, advice):
        if advice and hasattr(os, 'POSIX_FADV_RANDOM'):
            advise_file(fd, 0, 0, os.POSIX_FADV_RANDOM)
        page = os.sysconf('SC_PAGE_SIZE') if advice else None
        consumed = advised = 0
        while consumed < size:
            check_deadline(deadline)
            block = os.read(fd, min(8 * 2**20, size - consumed))
            require(block, 'READONLY_SHORT_READ')
            hashed.update(block)
            if copy_to is not None:
                copy_to.write(block)
            consumed += len(block)
            if advice:
                aligned = consumed - consumed % page
                if aligned > advised:
                    advise_file(fd, advised, aligned - advised, os.POSIX_FADV_DONTNEED)
                    advised = aligned
        require(not os.read(fd, 1), 'READONLY_FILE_GREW')
    return hashed.hexdigest()


def evict_readonly_file(path, *, expected_size=None, deadline=None):
    with readonly_fd(path, expected_size, deadline) as (_, size, advice):
        return {'size_bytes': size, 'advised': advice}


def advise_readonly_weights(weights: Path, key: str = 'minicpm4', *, deadline=None):
    from safeshift.candidates.source import LOCK
    locked = read(LOCK.with_name('checkpoint_metadata_lock.json'))[key]['weights']
    files = {name: evict_readonly_file(Path(weights) / name, expected_size=entry['size'],
                                       deadline=deadline) for name, entry in locked.items()}
    return {'files': files, 'effect': 'ADVISORY_NOT_RAM_PROOF'}


def advise_owned_runtime(request, owned, installed, *, deadline, max_entries=100000,
                         min_bytes=1, label='owned-advice'):
    """Validate the complete job-owned inventory before advising any descriptor."""
    from safeshift import internvl3763_python as py
    require(request['model_key'] == 'minicpm4' and ownership(request) == owned,
            'ADVICE_UNOBSERVED_SCRATCH_OWNERSHIP')
    require(installed['request_sha256'] == digest(request), 'ADVICE_RUNTIME_SOURCE_BINDING')
    scratch = Path(request['scratch'])
    prefix = scratch / 'venv3119'
    require(installed['env']['SAFESHIFT_RUNTIME_ROOT'] == str(prefix)
            and installed['python'] == str(prefix / 'bin/python'), 'ADVICE_OWNED_VENV_ONLY')
    archive = py.manifest()['filename']
    targets = (('venv3119', False, True), (archive, True, False),
               ('pip-bootstrap', True, True), ('input-cpython3119', True, True))
    return _advise_owned_files(scratch, owned, targets, deadline=deadline,
                               max_entries=max_entries, min_bytes=min_bytes, label=label)


def advise_ct1_setup(scratch, owned, *, deadline):
    """Advise only the job's copied install, build trees and restored archives."""
    targets = (('qwen-software', False, True), ('ct1-build-archives', False, True))
    return _advise_owned_files(Path(scratch), owned, targets, deadline=deadline,
                               max_entries=100000, min_bytes=2**20, label='ct1-post-setup')


def _advise_owned_files(scratch, owned, targets, *, deadline, max_entries, min_bytes, label):
    require(hasattr(os, 'posix_fadvise') and hasattr(os, 'O_NOFOLLOW'), 'ADVICE_REQUIRES_POSIX')
    for parent in (scratch, *scratch.parents):
        snapshot_stat(parent, directory=True)
    require(type(max_entries) is int and 0 < max_entries <= 100000
            and type(min_bytes) is int and min_bytes >= 1, 'ADVICE_SCAN_BOUND')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_flags = flags | os.O_DIRECTORY
    entries = skipped = 0

    def inspect(parent, name, path, tree, *, optional=False, directory=None, skip_links=False):
        nonlocal entries, skipped
        require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
        require(len(path) <= 64, 'ADVICE_SCAN_LIMIT')
        try:
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            if optional:
                return
            raise
        require(entries < max_entries, 'ADVICE_SCAN_LIMIT')
        entries += 1
        children = {} if stat.S_ISDIR(info.st_mode) else None
        tree[name] = (identity(info), children)
        if (skip_links and stat.S_ISLNK(info.st_mode)
                or (path[0] == 'qwen-software' and stat.S_ISREG(info.st_mode) and info.st_nlink != 1)):
            skipped += 1
            return
        is_dir = stat.S_ISDIR(info.st_mode)
        require(info.st_dev == owned['device'] and (directory is None or directory == is_dir)
                and (is_dir or stat.S_ISREG(info.st_mode) and info.st_nlink == 1),
                'ADVICE_ALIAS_OR_SPECIAL_FILE')
        if is_dir:
            child = os.open(name, directory_flags, dir_fd=parent)
            try:
                require(identity(os.fstat(child)) == identity(info), 'ADVICE_DIRECTORY_CHANGED')
                if path == ('venv3119',):
                    inspect(child, 'lib', path + ('lib',), children, directory=True)
                    inspect(child, 'bin', path + ('bin',), children, optional=True, directory=True)
                else:
                    allow_links = path[:2] == ('venv3119', 'bin') or path[0] in (
                        'input-cpython3119', 'qwen-software')
                    with os.scandir(child) as scanned:
                        for entry in scanned:
                            inspect(child, entry.name, path + (entry.name,), children, skip_links=allow_links)
            finally:
                os.close(child)

    root = os.open(scratch, directory_flags)
    try:
        root_info = os.fstat(root)
        require((root_info.st_dev, root_info.st_ino) == (owned['device'], owned['inode']),
                'ADVICE_ROOT_CHANGED')
        inventory = {}
        for name, optional, directory in targets:
            inspect(root, name, (name,), inventory, optional=optional, directory=directory)

        count = total = 0

        def advise(parent, tree):
            nonlocal count, total
            for name, (expected, children) in tree.items():
                require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                require(identity(info) == expected, 'ADVICE_FILE_CHANGED')
                if children is not None:
                    child = os.open(name, directory_flags, dir_fd=parent)
                    try:
                        require(identity(os.fstat(child)) == expected, 'ADVICE_DIRECTORY_CHANGED')
                        advise(child, children)
                        require(identity(os.fstat(child)) == expected
                                and identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) == expected,
                                'ADVICE_DIRECTORY_CHANGED')
                    finally:
                        os.close(child)
                elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size >= min_bytes:
                    fd = os.open(name, flags, dir_fd=parent)
                    try:
                        require(identity(os.fstat(fd)) == expected, 'ADVICE_OPEN_CHANGED')
                        os.fsync(fd)
                        require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                        require(identity(os.fstat(fd)) == expected, 'ADVICE_CHANGED_DURING_SYSCALL')
                        count += 1
                        total += info.st_size
                    finally:
                        os.close(fd)

        require(identity(os.fstat(root)) == identity(root_info) == identity(scratch.lstat()),
                'ADVICE_ROOT_CHANGED')
        advise(root, inventory)
        require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
        require(identity(os.fstat(root)) == identity(root_info) == identity(scratch.lstat()),
                'ADVICE_ROOT_CHANGED')
        return {'method': 'FSYNC_POSIX_FADV_DONTNEED_OWNED_RUNTIME', 'label': label,
                'scan_complete': True, 'entries': entries,
                'advised_files': count, 'advised_bytes': total,
                'deleted_files': 0, 'effect': 'ADVISORY_NOT_RAM_PROOF',
                ('skipped_aliases' if label == 'ct1-post-setup' else 'skipped_symlinks'): skipped}
    finally:
        os.close(root)


def reclaim(request, output, deadline, *, label='owned-advice', gate='post-advice'):
    output = Path(output)
    before = observe(output, label + '-before')
    try:
        complete(before)
        process = read(output.parent / 'setup-process.json')
        require(process['status'] == 'EXITED' and process['returncode'] == 0
                and process.get('group_exit', {}).get('status') == 'NO_LIVE_MEMBERS',
                'ADVICE_SETUP_GROUP_EXIT_UNVERIFIED')
        installed = read(output.parent / 'setup/runtime.json')
        result = advise_owned_runtime(request, read(output.parent / 'owned-scratch.json'),
                                      installed, deadline=deadline, label=label)
        write(output / (label + '.json'), result)
        # Advice may recover nothing. The same signed RAM/disk floor decides.
        resource_check(request, output, gate)
    finally:
        observe(output, label + '-after')


@contextmanager
def load_guard(request, output, *, deadline=None):
    """Bracket processor setup, verified weight deserialization and cache advice."""
    from unittest.mock import patch
    from safeshift.candidates import backend, loading
    diagnostics = Path(output) / "memory"
    processor, loader = backend.native_setup, backend.load_weight_model
    def checked_processor(*args, **kwargs):
        resource_check(request, diagnostics, 'before-processor')
        try:
            result = processor(*args, **kwargs)
            resource_check(request, diagnostics, 'after-processor')
            return result
        finally:
            observe(diagnostics, 'processor-exit')
    def checked_loader(snapshot, key, config, model_class, weights, device, **kwargs):
        require('weight_verifier' not in kwargs, 'MINICPM_NO_REPLACED_WEIGHT_VERIFIER')
        def verifier(path, key):
            result = loading.verify_weights(path, key, hash_reader=lambda item:
                                            stream_readonly_sha256(item, deadline=deadline))
            resource_check(request, diagnostics, 'before-weight-deserialization')
            return result
        try:
            result = loader(snapshot, key, config, model_class, weights, device,
                            **kwargs, weight_verifier=verifier)
            advice = advise_readonly_weights(weights, key, deadline=deadline)
            write(Path(output) / 'post-weight-load-advice.json', advice)
            resource_check(request, diagnostics, 'after-weight-load')
            return result
        finally:
            observe(diagnostics, 'weight-loader-exit')
    with patch.object(backend, 'native_setup', checked_processor), patch.object(backend, 'load_weight_model', checked_loader):
        yield
