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


def build(ref, *, smoke=False):
    if len(ref)!=40 or any(c not in '0123456789abcdef' for c in ref):
        raise ValueError('EXACT_COMMITTED_SOURCE_REQUIRED')
    if smoke:
        return archived_smoke(ref)
    payload={}
    names=sources(ROOT)+['scripts/verify_kaggle173_inputs.py','safeshift/verification173.py']
    if smoke:
        names+=['scripts/smoke_kaggle173.py','configs/issue173/real_smoke.json']
    for name in names:
        data=subprocess.check_output(['git','show',ref+':'+name],cwd=ROOT)
        if data!=(ROOT/name).read_bytes(): raise ValueError('SOURCE_BYTES_CHANGED:'+name)
        payload[name]=data.decode('utf8')
    raw=json.dumps(payload,sort_keys=True).encode()
    action=("from scripts.smoke_kaggle173 import launch\n"
            f"print(launch('/kaggle/input','/kaggle/working','/kaggle/temp',{ref!r}))") if smoke else (
            "from scripts.verify_kaggle173_inputs import run\n"
            f"print(run('/kaggle/input','/kaggle/working',{ref!r}))")
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
{action}
'''
    compile(code,'<verification-notebook>','exec')
    scope=[
        '# Issue173: bounded native smoke\n',
        'Continuation: Qwen already consumed one verified call in v2; execute InternVL3.5 and MiniCPM only (two remaining calls).\n',
        'Private; T4x2; Internet ON for pinned peer software only. Reuse existing checkpoints, original TRAIN and Qwen offline software Input.\n',
        'Hard ceiling 1 original image/model (ordinal0), 3 calls total, 3300s internal/3600s job. One load/model; no retries or production history.\n',
        'All calls have independent smoke identities. Raw/errors/INVALID and ZIP seals stay private; no scientific results or fresh171 import.\n',
        'Do not rerun this notebook/version in another VM: no global shared lock. Codex must check prior Output/history and submit exactly once.\n',
        'Side effects: pinned interpreter/venvs in scratch, existing software archive extraction, 1MiB scratch/output probes, GPU model loads and native inference, private evidence ZIP/SHA256.\n'
    ] if smoke else [
        '# Issue173: verify existing TRAIN/checkpoint bytes\n',
        'Private; CPU; Internet OFF; deadline 3000s/job 3600s. No packages, downloads, weight copies, model loading or inference.\n',
        'Attach existing original dataset + pilot master + three pinned checkpoint Notebook Outputs. Read only locked TRAIN JPGs; never TEST/annotation sidecars.\n',
        'Reuses PR174 software evidence. Outputs include a PRIVATE TRAIN seal (do not publish) and a separate sanitized evidence ZIP.\n',
        'No production reservation/history, smoke grant or scientific qualification. A byte PASS does not prove GPU fit.\n']
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'issue':173,'source_commit':ref,'payload_sha256':hashlib.sha256(raw).hexdigest(),
            'max_model_calls':3 if smoke else 0,'remaining_model_calls':2 if smoke else 0}},
        'cells':[{'cell_type':'markdown','id':'scope','metadata':{},'source':scope},
            {'cell_type':'code','id':'verify','metadata':{},'execution_count':None,'outputs':[],'source':code.splitlines(True)}]}


def archived_smoke(ref):
    """No historical runnable payload is embedded in the post-v5 notebook."""
    return {'nbformat':4,'nbformat_minor':5,'metadata':{
        'kernelspec':{'name':'python3','display_name':'Python 3','language':'python'},
        'safeshift':{'issue':173,'source_commit':ref,'state':'TERMINAL_ARCHIVE',
            'historical_executed_source':'1e744d991613f48d81ccf0046bc35c5fdab9d1e2',
            'historical_submitted_notebook_sha256':'e6a7cf19d57198fe91432d1bec4c0e24aa8075b8ded52dcaf3149c3b27731222',
            'max_model_calls':0,'remaining_model_calls':0}},'cells':[
        {'cell_type':'markdown','id':'terminal','metadata':{},'source':[
            '# Issue173 v5 — terminal historical record\n',
            'Qwen and InternVL calls consumed. This published notebook cannot load or call any model.\n',
            'Original v5 bytes remain immutable at source1e744d9 and in the private staged submission/Output archives.\n',
            'MiniCPM has one unused call; a separate mini-only path remains blocked pending direct ChatGPT review.\n']},
        {'cell_type':'code','id':'refuse','metadata':{},'execution_count':None,'outputs':[],
            'source':["raise PermissionError('ISSUE173_V5_TERMINAL_NO_REPLAY')\n"]}]}


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--source-commit',required=True); p.add_argument('--output',required=True)
    p.add_argument('--smoke',action='store_true')
    args=p.parse_args()
    Path(args.output).write_bytes((json.dumps(build(args.source_commit,smoke=args.smoke),indent=1)+'\n').encode())
