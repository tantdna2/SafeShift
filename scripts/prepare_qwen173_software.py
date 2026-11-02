"""Acquire exact public Qwen build sources and attempt Linux cp312 closure.

No model weights or data. A source mismatch is retained, never substituted.
Resolver output is a candidate lock, not approval or offline-install proof.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import urllib.request

from scripts.observe_kaggle173 import write, sha

ROOT = Path(__file__).resolve().parents[1]


def download(url, destination, expected, *, max_bytes=64*2**20, seconds=120):
    if not url.startswith('https://') or len(expected) != 64:
        raise ValueError('HTTPS_AND_SHA256_REQUIRED')
    started, count = time.monotonic(), 0
    with urllib.request.urlopen(url, timeout=20) as response, Path(destination).open('xb') as out:
        while True:
            if time.monotonic() - started > seconds:
                raise TimeoutError('PUBLIC_DOWNLOAD_DEADLINE')
            block = response.read(2**20)
            if not block:
                break
            count += len(block)
            if count > max_bytes:
                raise ValueError('PUBLIC_DOWNLOAD_SIZE_BOUND')
            out.write(block)
        out.flush()
        os.fsync(out.fileno())
    actual = sha(destination)
    if actual != expected:
        raise ValueError('PUBLIC_SOURCE_HASH_MISMATCH:' + actual)
    return {'url': url, 'file': Path(destination).name, 'size': count, 'sha256': actual}


def prepare(output, *, repo=ROOT, resolve=True):
    output, repo = Path(output), Path(repo)
    output.mkdir(parents=True, exist_ok=False)
    lock = json.loads((repo / 'configs/fulltrain/qwen3.json').read_text())
    report = {'schema': 'issue173-qwen-public-software-v1', 'source_config_sha256': sha(repo / 'configs/fulltrain/qwen3.json'),
        'host_python': platform.python_version(), 'host_platform': platform.platform(),
        'target': 'CPython3.12.13_linux_x86_64_zlib1.2.11', 'model_calls': 0, 'weight_bytes_downloaded': 0,
        'sources': {}, 'closure': 'NOT_RUN', 'processor': 'NOT_RUN', 'offline_install': 'NOT_RUN'}
    for name in ('python_source', 'zlib_source'):
        row = lock[name]
        try:
            report['sources'][name] = {'status': 'PASS', **download(row['url'], output / row['url'].rsplit('/',1)[1], row['sha256'])}
        except Exception as exc:
            report['sources'][name] = {'status': 'BLOCKED', 'url': row['url'], 'expected_sha256': row['sha256'],
                                      'error_type': type(exc).__name__, 'error': str(exc)}
    # Even on source failure, retain an independent bounded resolver attempt.
    # pip only acquires public package metadata here; it does not install anything.
    if resolve:
        requirements = [n.replace('_','-') + '==' + v for n,v in lock['software'].items() if n not in ('python','zlib')]
        requirements.append('pip==25.0.1')
        argv = [sys.executable, '-I', '-B', '-m', 'pip', '--isolated', '--disable-pip-version-check',
                'install', '--dry-run', '--ignore-installed', '--only-binary=:all:', '--python-version', '3.12',
                '--implementation', 'cp', '--abi', 'cp312',
                '--platform', 'manylinux_2_28_x86_64', '--platform', 'manylinux2014_x86_64',
                '--platform', 'linux_x86_64', '--index-url', 'https://pypi.org/simple',
                '--extra-index-url', 'https://download.pytorch.org/whl/cu128',
                '--retries', '0', '--timeout', '20', '--report', str(output/'resolver.json'), *requirements]
        write(output / 'resolver-command.json', {'argv': ['<python>', *argv[1:]], 'timeout_seconds': 300})
        try:
            with (output/'resolver.log').open('xb') as log:
                result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=300)
            report['closure'] = ('CROSS_HOST_CANDIDATE_NOT_LINUX_CLOSURE' if platform.system() != 'Linux'
                                 else 'RESOLVED_NOT_DOWNLOADED') if result.returncode == 0 else 'WHEELHOUSE_ABI_BLOCKED'
            report['resolver_returncode'] = result.returncode
        except Exception as exc:
            report['closure'] = 'WHEELHOUSE_ABI_BLOCKED'
            report['resolver_error'] = type(exc).__name__ + ':' + str(exc)
    report['status'] = 'SOURCES_VERIFIED_CLOSURE_PENDING' if all(r['status']=='PASS' for r in report['sources'].values()) else 'WHEELHOUSE_ABI_BLOCKED'
    write(output/'receipt.json', report)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.output), indent=2))
