"""Build the exact committed Mini-only executable; no release is embedded."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

from safeshift.candidates.source import ROOT, require
from safeshift.minicpm173_once import IDENTITY, JOB, LIMITS
from safeshift.pilot.artifacts import write_bytes
from safeshift.pilot.contract import digest
from scripts.minicpm173_train_once import runtime_sources


def build(ref):
    require(len(ref) == 40 and all(c in '0123456789abcdef' for c in ref), 'COMMITTED_RUNTIME_REQUIRED')
    payload = {}
    for name in runtime_sources():
        value = subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
        require(value == (ROOT / name).read_bytes(), 'RUNTIME_BYTES_UNCOMMITTED:' + name)
        payload[name] = value.decode('utf8')
    packed = json.dumps(payload, sort_keys=True).encode()
    manifest = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in payload.items()}
    spec = {'runtime_commit': ref, 'manifest': manifest}
    code = f'''import base64,hashlib,json,sys,uuid,zlib
from pathlib import Path
packed=zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(packed,9)).decode()!r}))
assert hashlib.sha256(packed).hexdigest()=={hashlib.sha256(packed).hexdigest()!r}
root=Path('/kaggle/temp')/('mini173-source-'+uuid.uuid4().hex)
root.mkdir(parents=True,exist_ok=False)
for name,text in json.loads(packed).items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name
    target=root/name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream: stream.write(text.encode())
sys.path.insert(0,str(root))
from safeshift.pilot.artifacts import write
from scripts.minicpm173_train_once import main
write(root/'mini-spec.json',{spec!r})
result=main(['--spec',str(root/'mini-spec.json')])
if result: raise RuntimeError('MINICPM173_TERMINAL_ERROR_SEE_SEALED_OUTPUT')
'''
    compile(code, '<mini173-once>', 'exec')
    return {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'name': 'python3', 'display_name': 'Python 3', 'language': 'python'},
            'safeshift': {'identity': IDENTITY, 'job': JOB, 'version': 1, 'runtime_commit': ref,
                'manifest_sha256': digest(manifest), 'limits': LIMITS,
                'release': 'EXTERNAL_EXACT_REVIEW_REQUIRED_NO_APPROVAL_EMBEDDED'}},
        'cells': [{'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
            '# MiniCPM original TRAIN ordinal0 — one-shot executable, review required\n',
            'Use only the reviewed local submission coordinator. Missing remote grant stops before data access.\n',
            'Five original smoke Outputs, four diagnostic Outputs, original data/master/byte proof and Mini weights are required.\n',
            'One load/one call, private T4x2 (GPU0 only), 1800 seconds; unchanged C1/FP16/eager/FP32 resampler/label-only.\n',
            'No retry, Qwen/InternVL call, TEST, scientific metric or fresh171 enrollment.\n',
            'Remote process permits are read-only here; no credentials in notebook. Preserve ZIP/SHA256 including INVALID/errors.\n']},
            {'cell_type': 'code', 'id': 'mini-once', 'metadata': {}, 'outputs': [],
             'execution_count': None, 'source': code.splitlines(True)}]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    write_bytes(args.output, (json.dumps(build(args.source_commit), indent=1) + '\n').encode())
