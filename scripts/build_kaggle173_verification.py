"""Build an exact-commit CPU-only existing-Input verifier. Never an inference route."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import zlib
from safeshift.fulltrain.contract import sources

ROOT=Path(__file__).resolve().parents[1]


def build(ref):
    if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('EXACT_COMMITTED_SOURCE_REQUIRED')
    payload={}
    for name in sources(ROOT)+['scripts/verify_kaggle173_inputs.py']:
        data=subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
        if data!=(ROOT/name).read_bytes(): raise ValueError('SOURCE_BYTES_CHANGED:'+name)
        payload[name]=data.decode('utf8')
    raw=json.dumps(payload,sort_keys=True).encode()
    code=f'''import base64, hashlib, json, sys, uuid, zlib
from pathlib import Path
data=zlib.decompress(base64.b64decode({base64.b64encode(zlib.compress(raw,9)).decode()!r}))
assert hashlib.sha256(data).hexdigest()=={hashlib.sha256(raw).hexdigest()!r}
root=Path('/kaggle/temp')/('issue173-verifier-source-'+uuid.uuid4().hex)
root.mkdir(parents=True,exist_ok=False)
for name,text in json.loads(data).items():
    assert not name.startswith('/') and '..' not in Path(name).parts and ':' not in name
    path=root/name
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream: stream.write(text.encode('utf8'))
sys.path.insert(0,str(root))
from scripts.verify_kaggle173_inputs import run
print(run('/kaggle/input','/kaggle/working',{ref!r}))
'''
    compile(code,'<verification-notebook>','exec')
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'issue':173,'source_commit':ref,'payload_sha256':hashlib.sha256(raw).hexdigest(),'model_calls':0}},
        'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':[
            '# Issue173: verify existing TRAIN/checkpoint bytes\n',
            'Private; CPU; Internet OFF; deadline 3000s/job 3600s. No packages, downloads, weight copies, model loading or inference.\n',
            'Attach existing original dataset + pilot master + three pinned checkpoint Notebook Outputs. Read only locked TRAIN JPGs; never TEST/annotation sidecars.\n',
            'Reuses PR174 software evidence. Outputs include a PRIVATE TRAIN seal (do not publish) and a separate sanitized evidence ZIP.\n',
            'No production reservation/history, smoke grant or scientific qualification. A byte PASS does not prove GPU fit.\n']},
            {'cell_type':'code','id':'verify','metadata':{},'execution_count':None,'outputs':[],'source':code.splitlines(True)}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--output',required=True)
    args=p.parse_args()
    Path(args.output).write_bytes((json.dumps(build(args.source_commit),indent=1)+'\n').encode())
