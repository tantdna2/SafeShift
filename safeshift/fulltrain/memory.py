"""Full-TRAIN RAM custody, based on Issue173 and InternVL's proven primitives.

Advice touches only the new job's copied venv. It is never headroom evidence.
No cache deletion, Input advice, allocation adjustment or threshold fallback.
"""
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
    except (OSError, ValueError, KeyError) as error:
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


def advise_owned_runtime(request, owned, installed, *, deadline, max_entries=100000):
    """Two bounded passes using directory FDs; validate whole lib before advice.

    Initial empty-scratch ownership and successful reaped setup are established
    by the parent. Reject every alias/special file, not just large candidates.
    No Input/checkpoint/output is visited. All descriptors are read-only.
    """
    require(request['model_key'] == 'minicpm4' and ownership(request) == owned,
            'ADVICE_UNOBSERVED_SCRATCH_OWNERSHIP')
    require(installed['request_sha256'] == digest(request), 'ADVICE_RUNTIME_SOURCE_BINDING')
    scratch = Path(request['scratch'])
    prefix = scratch / 'venv3119'
    require(installed['env']['SAFESHIFT_RUNTIME_ROOT'] == str(prefix)
            and installed['python'] == str(prefix / 'bin/python'), 'ADVICE_OWNED_VENV_ONLY')
    require(hasattr(os, 'posix_fadvise') and hasattr(os, 'O_NOFOLLOW'), 'ADVICE_REQUIRES_POSIX')
    require(type(max_entries) is int and 0 < max_entries <= 100000, 'ADVICE_SCAN_BOUND')
    for parent in (prefix, prefix / 'lib'):
        snapshot_stat(parent, directory=True)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    directory_flags = flags | os.O_DIRECTORY
    inventory = {}
    def walk(fd, relative):
        require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
        with os.scandir(fd) as entries:
            names = []
            for entry in entries:
                require(len(inventory) + len(names) < max_entries, 'ADVICE_SCAN_LIMIT')
                names.append(entry.name)
        require(len(inventory) + len(names) <= max_entries, 'ADVICE_SCAN_LIMIT')
        for name in names:
            require(time.monotonic() < deadline and len(inventory) < max_entries, 'ADVICE_DEADLINE_OR_SCAN_LIMIT')
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            require(info.st_dev == owned['device'] and (stat.S_ISDIR(info.st_mode)
                    or stat.S_ISREG(info.st_mode) and info.st_nlink == 1), 'ADVICE_ALIAS_OR_SPECIAL_FILE')
            path = relative + (name,)
            inventory[path] = identity(info)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, directory_flags, dir_fd=fd)
                try:
                    require(identity(os.fstat(child)) == identity(info), 'ADVICE_DIRECTORY_CHANGED')
                    walk(child, path)
                finally:
                    os.close(child)
    root = os.open(prefix / 'lib', directory_flags)
    try:
        root_identity = identity(os.fstat(root))
        walk(root, ())
        # Resolve every ancestor through retained no-follow directory handles.
        count = total = 0
        for path, expected in inventory.items():
            require(time.monotonic() < deadline, 'ADVICE_DEADLINE')
            parent = os.dup(root)
            try:
                for i, name in enumerate(path[:-1]):
                    child = os.open(name, directory_flags, dir_fd=parent)
                    os.close(parent); parent = child
                    require(identity(os.fstat(parent)) == inventory[path[:i+1]], 'ADVICE_DIRECTORY_CHANGED')
                info = os.stat(path[-1], dir_fd=parent, follow_symlinks=False)
                require(identity(info) == expected, 'ADVICE_FILE_CHANGED')
                if stat.S_ISREG(info.st_mode) and info.st_size >= 8 * 2**20:
                    fd = os.open(path[-1], flags, dir_fd=parent)
                    try:
                        require(identity(os.fstat(fd)) == expected, 'ADVICE_OPEN_CHANGED')
                        os.fsync(fd)
                        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
                        require(identity(os.fstat(fd)) == expected, 'ADVICE_CHANGED_DURING_SYSCALL')
                        count += 1; total += info.st_size
                    finally:
                        os.close(fd)
            finally:
                os.close(parent)
        require(identity(os.fstat(root)) == root_identity
                and identity((prefix / 'lib').lstat()) == root_identity, 'ADVICE_ROOT_CHANGED')
        return {'method': 'FSYNC_POSIX_FADV_DONTNEED_OWNED_VENV_LIB_ONLY', 'scan_complete': True,
                'entries': len(inventory), 'advised_files': count, 'advised_bytes': total,
                'deleted_files': 0, 'effect': 'ADVISORY_NOT_RAM_PROOF'}
    finally:
        os.close(root)


def reclaim(request, output, deadline):
    output = Path(output)
    before = observe(output, 'owned-advice-before')
    try:
        complete(before)
        installed = read(output.parent / 'setup/runtime.json')
        result = advise_owned_runtime(request, read(output.parent / 'owned-scratch.json'),
                                      installed, deadline=deadline)
        write(output / 'owned-advice.json', result)
        # Advice may recover nothing. The same signed RAM/disk floor decides.
        resource_check(request, output, 'post-advice')
    finally:
        observe(output, 'owned-advice-after')


@contextmanager
def load_guard(request, output):
    """Scoped checks around the unchanged native processor and weight loader.

    Reuse the loader's existing weight_verifier seam (as InternVL does). All
    original source/weight SHA checks still read every actual byte. No Input
    cache advice, model class/args/dtype substitution or shared-source edit.
    """
    from unittest.mock import patch
    from safeshift.candidates import backend, loading
    processor, loader = backend.native_setup, backend.load_weight_model
    def checked_processor(*args, **kwargs):
        resource_check(request, output, 'before-processor')
        try:
            result = processor(*args, **kwargs)
            resource_check(request, output, 'after-processor')
            return result
        finally:
            observe(output, 'processor-exit')
    def checked_loader(*args, **kwargs):
        require('weight_verifier' not in kwargs, 'MINICPM_NO_REPLACED_WEIGHT_VERIFIER')
        def verifier(path, key):
            result = loading.verify_weights(path, key)
            resource_check(request, output, 'before-weight-deserialization')
            return result
        try:
            result = loader(*args, **kwargs, weight_verifier=verifier)
            resource_check(request, output, 'after-weight-load')
            return result
        finally:
            observe(output, 'weight-loader-exit')
    with patch.object(backend, 'native_setup', checked_processor), patch.object(backend, 'load_weight_model', checked_loader):
        yield
