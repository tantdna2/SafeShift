"""Embed an exact committed, synthetic-only diagnostic; no TRAIN path."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib
from safeshift.candidates.source import ROOT
from safeshift.fulltrain.contract import sources
from scripts.diagnostic173 import admit


def build(ref,identity):
    plan=admit(identity)
    if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref): raise ValueError('EXACT_COMMIT')
    names=sorted(set(sources()+['safeshift/verification173.py','safeshift/smoke173_history.py',
        'scripts/verify_kaggle173_inputs.py','scripts/smoke_kaggle173.py','scripts/minicpm173_preflight.py',
        'scripts/diagnostic173.py','configs/issue173/real_smoke.json']))
    payload={}
    for name in names:
        value=subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
        if value!=(ROOT/name).read_bytes(): raise ValueError('SOURCE_BYTES_CHANGED:'+name)
        payload[name]=value.decode('utf8')
    manifest={n:hashlib.sha256(v.encode()).hexdigest() for n,v in payload.items()}
    raw=json.dumps(payload,sort_keys=True).encode()
    code=f'''import base64,hashlib,json,sys,zlib
from pathlib import Path
raw=zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(raw,9)).decode()!r}))
assert hashlib.sha256(raw).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
root=Path('/kaggle/temp')/{(identity+'-source')!r}
root.mkdir(parents=True,exist_ok=False)
for name,text in json.loads(raw).items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name
    target=root/name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream: stream.write(text.encode('utf8'))
sys.path.insert(0,str(root))
from scripts.diagnostic173 import launch
print(launch({identity!r},'/kaggle/input','/kaggle/working','/kaggle/temp',{ref!r},{manifest!r}))
'''
    compile(code,'<synthetic-diagnostic>','exec')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'source_commit':ref,'identity':identity,'payload_sha256':hashlib.sha256(raw).hexdigest(),
            'model_key':plan['key'],'max_model_calls':len(plan['variants']),'max_loads':1,
            'scope':'SYNTHETIC_ONLY','original_train_calls':0,'max_job_seconds':1800}},
        'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':[
            '# Issue173 bounded synthetic-only diagnostic\n',
            'One pinned checkpoint; five original histories. NO real images or labels. No TEST/fresh171/original smoke.\n',
            'Private T4x2 (one visible); Internet ON only for unchanged pinned software. 1800s job, one load; calls bounded in metadata.\n',
            'Raw/token IDs saved before strict parsing. No retries. InternVL changes PROPOSED only. Mini original TRAIN dispatch stays REVIEW HOLD.\n']},
            {'cell_type':'code','id':'diagnostic','metadata':{},'source':code.splitlines(True),'outputs':[],'execution_count':None}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--identity',required=True)
    p.add_argument('--output',required=True); a=p.parse_args()
    with Path(a.output).open('xb') as stream: stream.write((json.dumps(build(a.source_commit,a.identity),indent=1)+'\n').encode())
