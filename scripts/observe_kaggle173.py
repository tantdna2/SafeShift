"""Issue173 no-Input observation. No weights, dataset reader or inference entry.

Explicit invocation only. Repeat runs get unique output; failed checks survive.
The kernel tensor probe does not qualify any pinned production worker.
"""
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid
import zipfile
from datetime import datetime, timezone


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            h.update(block)
    return h.hexdigest()


def allocation(scratch, output, size=2**20):
    if type(size) is not int or not 0 < size <= 16 * 2**20:
        raise ValueError('OBSERVATION_ALLOCATION_BOUND')
    created, rows = [], []
    try:
        for root in (Path(scratch), Path(output)):
            path = root / ('probe-' + uuid.uuid4().hex)
            with path.open('xb') as stream:
                created.append(path)
                stream.write(b'\xa5' * size)
                stream.flush()
                os.fsync(stream.fileno())
            st = path.stat()
            allocated = st.st_blocks * 512 if hasattr(st, 'st_blocks') else None
            if st.st_size != size or (allocated is not None and allocated < size):
                raise ValueError('PHYSICAL_ALLOCATION_NOT_PROVEN')
            rows.append({'written_bytes': st.st_size, 'allocated_bytes': allocated,
                         'device': st.st_dev, 'free_bytes': shutil.disk_usage(root).free})
    finally:
        for path in created:
            path.unlink()
    return {'allocations': rows, 'cleanup_verified': all(not p.exists() for p in created),
            'same_device': rows[0]['device'] == rows[1]['device'],
            'quota_scope': 'SMALL_PROBE_ONLY_NOT_FULL_MODEL_CAPACITY'}


def command(argv, timeout=45):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    if len(result.stdout) + len(result.stderr) > 65536:
        raise ValueError('OBSERVATION_OUTPUT_BOUND')
    return {'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}


def memory():
    fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    result = {'host_available_bytes': int(fields['MemAvailable'].split()[0]) * 1024,
              'cgroup': {}}
    for rel in ('memory.max', 'memory.current', 'memory/memory.limit_in_bytes',
                'memory/memory.usage_in_bytes'):
        p = Path('/sys/fs/cgroup') / rel
        if p.is_file():
            result['cgroup'][rel] = p.read_text().strip()
    return result


CUDA_PROBE = '''
import json, torch
result = {'torch': torch.__version__, 'cuda_build': torch.version.cuda,
          'available': torch.cuda.is_available(), 'devices': []}
for i in range(torch.cuda.device_count()):
    x = torch.ones((2, 2), device=f'cuda:{i}', dtype=torch.float16)
    y = x @ x
    torch.cuda.synchronize(i)
    result['devices'].append({'index': i, 'name': torch.cuda.get_device_name(i),
        'capability': list(torch.cuda.get_device_capability(i)),
        'memory_bytes': list(torch.cuda.mem_get_info(i)), 'fp16_matmul': y.tolist()})
print(json.dumps(result))
'''


def observe(parent, scratch, *, source_commit, gpu=True):
    if len(source_commit) != 40 or any(c not in '0123456789abcdef' for c in source_commit):
        raise ValueError('EXACT_SOURCE_COMMIT_REQUIRED')
    parent, scratch = Path(parent), Path(scratch)
    if any(p.is_symlink() for root in (parent, scratch) for p in (root, *root.parents)):
        raise ValueError('OUTPUT_ALIAS')
    parent.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)
    run_id = 'issue173-env-' + uuid.uuid4().hex
    root = parent / run_id
    root.mkdir()
    start = time.monotonic()
    report = {'schema': 'safeshift-issue173-observation-v1', 'run_id': run_id,
        'source_commit': source_commit, 'script_sha256': sha(__file__),
        'utc': datetime.now(timezone.utc).isoformat(), 'model_calls': 0,
        'weights_loaded': False, 'dataset_accessed': False, 'owner_slot_consumed': False,
        'scientific_qualified': False, 'production_authorized': False,
        'data_gate': 'DATA_RIGHTS_AND_FRESH_CUSTODY_NOT_VERIFIED',
        'checkpoint_gate': 'NOT_ATTACHED_NOT_VERIFIED',
        'worker_gate': 'PINNED_WORKERS_NOT_VERIFIED', 'checks': {}}
    def check(name, fn):
        try:
            value = fn()
            if isinstance(value, dict) and value.get('returncode', 0) != 0:
                report['checks'][name] = {'status': 'FAIL', 'value': value}
            else:
                report['checks'][name] = {'status': 'OBSERVED', 'value': value}
        except Exception as exc:
            report['checks'][name] = {'status': 'FAIL', 'error_type': type(exc).__name__,
                                     'error': str(exc)[:2000]}
    check('kernel', lambda: {'python': platform.python_version(), 'implementation': platform.python_implementation(),
        'platform': platform.platform(), 'architecture': platform.machine(),
        'abi': sys.implementation.cache_tag})
    check('packages', lambda: {n: metadata.version(n) for n in
        ('pip', 'torch', 'torchvision', 'transformers', 'numpy', 'pillow')})
    check('memory', memory)
    check('storage', lambda: allocation(scratch, root))
    if gpu:
        check('driver', lambda: command(['nvidia-smi', '--query-gpu=index,name,driver_version,memory.total,memory.free',
                                         '--format=csv,noheader,nounits'], 10))
        check('kernel_cuda_tensor_only', lambda: command([sys.executable, '-I', '-B', '-c', CUDA_PROBE]))
    else:
        report['checks']['kernel_cuda_tensor_only'] = {'status': 'NOT_RUN'}
    report['seconds'] = time.monotonic() - start
    report['status'] = 'ENVIRONMENT_OBSERVED' if all(v['status'] != 'FAIL' for v in report['checks'].values()) else 'OBSERVED_WITH_FAILURES'
    report['inference_status'] = 'NOT_ATTEMPTED'
    write(root / 'observation.json', report)
    write(root / 'checksums.json', {'observation.json': sha(root / 'observation.json')})
    archive = parent / (run_id + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(root.iterdir()):
            bundle.write(path, path.name)
    write(Path(str(archive) + '.sha256.json'), {'sha256': sha(archive), 'size': archive.stat().st_size,
        'model_calls': 0, 'source_commit': source_commit})
    return root


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    p.add_argument('--scratch', required=True)
    p.add_argument('--source-commit', required=True)
    a = p.parse_args()
    print(observe(a.output, a.scratch, source_commit=a.source_commit))
