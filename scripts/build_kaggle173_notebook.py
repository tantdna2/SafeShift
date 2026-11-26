"""Build a committed, hash-bound, no-Input environment notebook for Issue173."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib

ROOT = Path(__file__).resolve().parents[1]


def build(ref):
    if len(ref) != 40 or any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('EXACT_SOURCE_COMMIT_REQUIRED')
    name = 'scripts/observe_kaggle173.py'
    data = subprocess.check_output(['git', 'show', ref + ':' + name], cwd=ROOT)
    if data != (ROOT / name).read_bytes():
        raise ValueError('COMMITTED_OBSERVER_BYTES_REQUIRED')
    code = f'''import base64, hashlib, uuid
from pathlib import Path
payload = base64.b64decode({base64.b64encode(data).decode()!r})
assert hashlib.sha256(payload).hexdigest() == {hashlib.sha256(data).hexdigest()!r}
root = Path('/kaggle/working') / ('issue173-source-' + uuid.uuid4().hex)
root.mkdir(exist_ok=False)
script = root / 'observe_kaggle173.py'
with script.open('xb') as stream:
    stream.write(payload)
namespace = {{'__file__': str(script), '__name__': 'issue173_observation'}}
exec(compile(payload, str(script), 'exec'), namespace)
receipt = namespace['observe']('/kaggle/working', '/kaggle/temp/issue173', source_commit={ref!r})
print(receipt)
'''
    compile(code, '<notebook>', 'exec')
    return {'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                     'safeshift': {'issue': 173, 'source_commit': ref, 'model_calls': 0, 'inputs': []}},
        'cells': [{'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
            '# Issue173: live environment observation only\n',
            'Private notebook; attach no Inputs. No dataset/checkpoint reads, weight load or inference.\n',
            'Side effects: source/receipt/ZIP files, two simultaneous 1 MiB scratch/output files (removed), ',
            'a tiny FP16 tensor probe on each visible GPU. Repeat creates a new observation.\n',
            'GPU quota/time is used; no production attempt or model call is consumed. ',
            'Kernel CUDA is not pinned-worker or model-fit verification. Export all ZIPs and sidecars.\n']},
            {'cell_type': 'code', 'id': 'observe', 'metadata': {}, 'execution_count': None,
             'outputs': [], 'source': code.splitlines(True)}]}


def build_software(ref):
    from safeshift.fulltrain.contract import sources
    if len(ref) != 40 or any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('EXACT_SOURCE_COMMIT_REQUIRED')
    names = sources(ROOT) + ['scripts/observe_kaggle173.py',
        'scripts/prepare_qwen173_software.py', 'scripts/qualify_kaggle173_software.py',
        'configs/issue173/qwen_linux_cp312_wheels.json']
    payload = {}
    for name in names:
        data = subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
        if data != (ROOT/name).read_bytes():
            raise ValueError('COMMITTED_SOURCE_BYTES_REQUIRED:'+name)
        payload[name] = data.decode('utf-8')
    encoded = json.dumps(payload,sort_keys=True).encode()
    code = f'''import base64, hashlib, json, sys, uuid, zlib
from pathlib import Path
data = zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(encoded,9)).decode()!r}))
assert hashlib.sha256(data).hexdigest() == {hashlib.sha256(encoded).hexdigest()!r}
root = Path('/kaggle/temp') / ('issue173-public-code-' + uuid.uuid4().hex)
root.mkdir(parents=True, exist_ok=False)
for name, text in json.loads(data).items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(text.encode('utf-8'))
sys.path.insert(0, str(root))
from scripts.qualify_kaggle173_software import launch
print(launch('/kaggle/working', '/kaggle/temp', {ref!r}))
'''
    compile(code,'<software-notebook>','exec')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'safeshift':{'issue':173,'source_commit':ref,'payload_sha256':hashlib.sha256(encoded).hexdigest(),
                    'model_calls':0,'inputs':[]}},'cells':[
        {'cell_type':'markdown','id':'scope','metadata':{},'source':[
            '# Issue173 public software preflight\n',
            'Private; Internet ON; T4x2; attach NO Inputs. No dataset, weights or model inference.\n',
            'Build exact CPython/zlib, acquire the sealed Linux cp312 Qwen wheel candidate, ',
            'install offline, then run pinned public processors with synthetic images and tiny CUDA tensors.\n',
            'Peers retain their existing pinned software, strict C1, MiniCPM FP32 resampler and label-only policy.\n',
            'Side effects: public downloads/builds/venvs in scratch, bounded logs/receipts/ZIP in Output. ',
            'Up to 16 GiB Qwen wheels; GPU/job time ceiling 3600 seconds, child deadline 3300 seconds. ',
            'Zero production slots/calls. No checkpoint/model-fit/scientific PASS.\n',
            'The Qwen offline software Input is exported as a separate public-software ZIP/SHA256. ',
            'Every rerun has a unique directory and never resumes a model call.\n']},
        {'cell_type':'code','id':'qualify','metadata':{},'execution_count':None,'outputs':[],
         'source':code.splitlines(True)}]}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source-commit', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--software', action='store_true')
    a = p.parse_args()
    value = build_software(a.source_commit) if a.software else build(a.source_commit)
    Path(a.output).write_bytes((json.dumps(value, indent=1) + '\n').encode('utf-8'))
