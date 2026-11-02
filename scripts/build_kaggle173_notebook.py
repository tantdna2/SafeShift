"""Build a committed, hash-bound, no-Input environment notebook for Issue173."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(ref):
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


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source-commit', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    Path(a.output).write_text(json.dumps(build(a.source_commit), indent=1) + '\n', encoding='utf-8')
