"""Closed five-attempt history, and a distinct MiniCPM-only REVIEW HOLD.

Exact published archive SHA pins are custody seals, not invented signatures.
No model loader exists here; a receipt or caller flag cannot activate a call.
"""
import json
from pathlib import Path
import zipfile
from safeshift.pilot.artifacts import read, sha, verify_archive
from safeshift.candidates.source import require

ARCHIVES=(
    'a296d13984e179a2087acc25a6f45c58f4e15eeb4e32a4efdc46ce8b2a8fac17',
    'f1f4fefabff4a6fc80f8863bcc314a13949c53815f9b535170cceda1ccd7117d',
    '4b74106fe476858bceffa0ce3ec50d940af0e707ecf05456370a56c6101f35c5',
    '2ae1b33411e93c3b9c9a43f9e1d05d9368704d43795a1e7052bf8c12dcf4aaee',
    '035c4d9b0216378e23ecc812e1221d68fe451ec25a9cbc3fd8977b5794690619')
KEYS=('qwen3','internvl35','minicpm4')
CONTINUATION='issue173-minicpm-only-review-hold-20261103-v1'
HOLD='MINICPM173_NATIVE_CALL_BLOCKED_PENDING_CHATGPT_DIRECT_REVIEW'


def inspect_history(paths):
    require(len(paths)==5,'ALL_FIVE_ATTEMPTS_REQUIRED_INCLUDING_V5')
    counts={k:0 for k in KEYS}; seals=[]; images=set()
    for i,(path,expected) in enumerate(zip(paths,ARCHIVES),1):
        path=Path(path)
        require(sha(path)==expected==read(Path(str(path)+'.sha256.json'))['sha256'],f'ATTEMPT_{i}_EXACT_SEAL')
        members=verify_archive(path)
        with zipfile.ZipFile(path) as bundle:
            summary=json.loads(bundle.read('summary.json'))
            require(summary['run_id']==f'issue173-smoke-20261102-v{i}','ATTEMPT_IDENTITY')
            markers={n for n in members if n.endswith('/native_call.json')}
            require(len(markers)==summary['model_calls'],'HISTORY_CALL_MARKERS')
            for key in KEYS:
                called=int(f'{key}/sample/native_call.json' in markers)
                require(summary['models'][key]['native_calls']==called,'MODEL_CALL_ACCOUNTING')
                counts[key]+=called
                if called:
                    raw=json.loads(bundle.read(f'{key}/sample/raw.json'))
                    result=json.loads(bundle.read(f'{key}/sample/result.json'))
                    require(result['raw_sha256']==members[f'{key}/sample/raw.json'],'HISTORY_RAW_CUSTODY')
                    images.add((raw['smoke_identity']['sample_id'],raw['smoke_identity']['image_sha256']))
            require(not any(n.startswith('minicpm4/') and n.endswith(('model-load-reservation.json',
                'loaded-environment.json','native_call.json')) for n in members),'MINICPM_RESERVATION_OR_CONSUMPTION')
        seals.append({'attempt':i,'archive_sha256':expected,'members':len(members)+1})
    require(counts=={'qwen3':1,'internvl35':1,'minicpm4':0} and len(images)==1,'CLOSED_HISTORY_EXACT_COUNTS_IMAGE')
    return {'schema':'issue173-five-attempt-terminal-history-v1','attempts':seals,'consumed':counts,
        'consumed_total':2,'remaining':{'qwen3':0,'internvl35':0,'minicpm4':1},
        'max_one_call_per_model':True,'continuation':CONTINUATION,'native_dispatch':'BLOCKED_PENDING_REVIEW',
        'evidence_type':'EXACT_SHA256_CUSTODY_NOT_A_SIGNATURE_OR_AUTHORIZATION'}


def mini_only_request(history,model_key='minicpm4'):
    require(model_key=='minicpm4','ONLY_UNUSED_MINICPM_MODEL')
    require(history['consumed']=={'qwen3':1,'internvl35':1,'minicpm4':0}
        and len(history['attempts'])==5,'COMPLETE_TERMINAL_HISTORY_REQUIRED')
    return {'schema':'issue173-minicpm-only-review-request-v1','identity':CONTINUATION,
        'model_key':'minicpm4','max_native_calls':1,'max_loads':1,'ordinal':0,
        'remaining_global_calls':1,'scientific_results_excluded':True,
        'dispatch':'BLOCKED_PENDING_CHATGPT_DIRECT_REVIEW'}


def launch(*args,**kwargs):
    raise PermissionError(HOLD)


def worker(*args,**kwargs):
    raise PermissionError(HOLD)
