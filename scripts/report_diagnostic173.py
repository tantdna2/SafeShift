"""Sanitize sealed diagnostic evidence. No response text, labels or token IDs."""
import argparse
import json
from pathlib import Path
import zipfile
from safeshift.pilot.artifacts import sha,verify_archive,write
from safeshift.candidates.source import require
from scripts.diagnostic173 import evaluate


def report(archive,expected):
    require(sha(archive)==expected,'DIAGNOSTIC_ARCHIVE_SHA')
    members=verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        get=lambda name:json.loads(bundle.read(name))
        result=get('result.json'); budget=get('budget.json'); history=get('history.json')
        require(history['consumed']=={'qwen3':1,'internvl35':1,'minicpm4':0},'ORIGINAL_CALL_LEDGER')
        require(result['original_smoke_calls_added']==budget['original_train_calls']==0,'NO_ORIGINAL_SMOKE_CALL')
        markers=[n for n in members if n.endswith('/native_call.json')]
        reservations=[n for n in members if n.endswith('/reservation.json')]
        require(len(markers)==result['native_call_markers']<=len(reservations)==result['call_reservations']<=budget['max_calls'],'DIAGNOSTIC_CALL_ACCOUNTING')
        require(result['load_reservations']==int('load-reservation.json' in members)<=budget['max_loads']==1,'LOAD_ACCOUNTING')
        calls=[]
        for name in markers:
            prefix=name.rsplit('/',1)[0]; raw_name=prefix+'/raw.json'; saved_name=prefix+'/result.json'
            row={'variant':prefix.split('/')[-1],'native_marker_sha256':members[name],
                'completion':'UNKNOWN' if saved_name not in members else 'DURABLE_RESULT'}
            if raw_name in members:
                raw=get(raw_name)
                row.update(raw_sha256=members[raw_name],tokens=len(raw['generated_ids']),
                    raw_nonfinite=raw['raw_nonfinite'],tokenizer_replay=raw['cpu_tokenizer_replay']['status'],
                    actual_logits_processors=raw['actual_logits_processors'],capture_error_present=raw['capture_error'] is not None,
                    code_fence_generated=raw['response'].startswith('```'),seconds=raw['seconds'])
                if saved_name in members:
                    saved=get(saved_name); calculated=evaluate(raw,row['variant'])
                    require(saved=={**calculated,'variant':row['variant'],'raw_sha256':members[raw_name]},'STRICT_RESULT_REPLAY')
                    row.update(calculated)
            num=prefix+'/effective_numerics.json'
            if num in members: row['effective_numerics']=get(num)
            calls.append(row)
        stages={}
        for name in members:
            if name.endswith('-memory.json') or name.endswith('-exit-memory.json'):
                value=get(name)
                stages[name]={'available_bytes':value['available_bytes'],
                    'cgroup_current':value['memory.current'],'cgroup_max':value['memory.max'],
                    'cgroup_events':value['memory.events'],'cgroup_anon':value['memory.stat'].get('anon'),
                    'cgroup_file':value['memory.stat'].get('file'),'direct_children':len(value['direct_children'])}
        public={
            'schema':'issue173-synthetic-diagnostic-evidence-v1','archive_sha256':expected,'members':len(members)+1,
            'result':result,'budget':budget,'history':history,'calls':calls,'memory':stages,
            'timeline_samples':len(get('memory-timeline.json')),
            'supervisors':{n:get(n) for n in members if n.endswith('-supervisor.json')},
            'vram':{n:get(n) for n in members if n.endswith('-vram.json')},
            'configuration':get('loaded.json') if 'loaded.json' in members else None,
            'processor':get('processor-source.json') if 'processor-source.json' in members else None,
            'original_train_smoke':'BLOCKED_PENDING_CHATGPT_REVIEW',
            'scientific_results_excluded':True,'no_raw_response_or_token_ids_exported':True}
        # Summary results contain only hashes/status/prefix, never native text.
        if 'failure.json' in members:
            value=get('failure.json'); public['failure']={'type':value['type'],'detail':'SEE_PRIVATE_LOG','evidence_sha256':members['failure.json']}
        return public


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--archive',required=True); p.add_argument('--sha256',required=True)
    p.add_argument('--output',required=True); a=p.parse_args(); write(Path(a.output),report(a.archive,a.sha256))
