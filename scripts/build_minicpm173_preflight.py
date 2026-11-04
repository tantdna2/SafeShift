"""Exact-source MiniCPM-only fresh-VM RAM preflight; zero calls by construction."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib
from safeshift.candidates.source import ROOT
from safeshift.fulltrain.contract import sources


def build(ref):
    if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref): raise ValueError('EXACT_COMMIT')
    names=sources()+['safeshift/verification173.py','safeshift/smoke173_history.py',
        'scripts/verify_kaggle173_inputs.py','scripts/smoke_kaggle173.py','scripts/minicpm173_preflight.py',
        'configs/issue173/real_smoke.json']
    payload={}
    for name in names:
        value=subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
        if value!=(ROOT/name).read_bytes(): raise ValueError('SOURCE_BYTES_CHANGED:'+name)
        payload[name]=value.decode('utf8')
    raw=json.dumps(payload,sort_keys=True).encode()
    code=f'''import base64,hashlib,json,sys,uuid,zlib
from pathlib import Path
raw=zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(raw,9)).decode()!r}))
assert hashlib.sha256(raw).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
root=Path('/kaggle/temp')/('issue173-mini-preflight-source-'+uuid.uuid4().hex)
root.mkdir(parents=True,exist_ok=False)
for name,text in json.loads(raw).items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name
    target=root/name
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream: stream.write(text.encode('utf8'))
sys.path.insert(0,str(root))
from scripts.minicpm173_preflight import launch
print(launch('/kaggle/input','/kaggle/working','/kaggle/temp',{ref!r}))
'''
    compile(code,'<mini-no-inference>','exec')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'source_commit':ref,'payload_sha256':hashlib.sha256(raw).hexdigest(),
            'model_key':'minicpm4','max_model_calls':0,'weights_loaded':False,'native_dispatch':'BLOCKED_PENDING_CHATGPT_REVIEW'}},
        'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':[
            '# MiniCPM-only fresh-VM RAM preflight — NO INFERENCE\n',
            'Private T4x2; Internet ON for pinned software. Attach only existing MiniCPM checkpoint and five sealed historical smoke Outputs.\n',
            'No real images, weights loads, generation, production attempts or consumption. Native continuation remains a code-level review hold.\n',
            'Measure startup/setup/cache/processor/CUDA/before-load RAM and cgroup file/anonymous memory, owned process lifetime.\n',
            'Side effects: exact pinned venv/software in unique owned scratch; advisory eviction of owned regular scratch file pages only; no global cache or Input changes.\n',
            'Deadline1500s/job1800s; zero model calls. Export receipt ZIP/SHA256; a RAM PASS does not prove model fit or approve the unused call.\n']},
            {'cell_type':'code','id':'preflight','metadata':{},'source':code.splitlines(True),'outputs':[],'execution_count':None}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    Path(a.output).write_bytes((json.dumps(build(a.source_commit),indent=1)+'\n').encode())
