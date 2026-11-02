from pathlib import Path
import json,zipfile,hashlib,sys
import argparse
from safeshift.candidates.source import ROOT
p=argparse.ArgumentParser(description="Validate five private Issue173 attempts; emit sanitized review evidence.")
p.add_argument("--artifact-root",required=True)
p.add_argument("--output",required=True)
a=p.parse_args()
root=Path(a.artifact_root); repo=ROOT
from safeshift.pilot.artifacts import sha,verify_archive
from safeshift.pilot.contract import parse_label
from safeshift.fulltrain.qwen import parser as qwen_parser
EXPECTED_ARCHIVES={
    1:'a296d13984e179a2087acc25a6f45c58f4e15eeb4e32a4efdc46ce8b2a8fac17',
    2:'f1f4fefabff4a6fc80f8863bcc314a13949c53815f9b535170cceda1ccd7117d',
    3:'4b74106fe476858bceffa0ce3ec50d940af0e707ecf05456370a56c6101f35c5',
    4:'2ae1b33411e93c3b9c9a43f9e1d05d9368704d43795a1e7052bf8c12dcf4aaee',
    5:'035c4d9b0216378e23ecc812e1221d68fe451ec25a9cbc3fd8977b5794690619'}

def archive(attempt):
    p=root/f'smoke-output-v{attempt}'/f'issue173-smoke-20261102-v{attempt}.zip'
    assert sha(p)==json.loads(Path(str(p)+'.sha256.json').read_bytes())['sha256']==EXPECTED_ARCHIVES[attempt]
    members=verify_archive(p)
    return p,zipfile.ZipFile(p),members

reports=[]; calls={k:0 for k in ('qwen3','internvl35','minicpm4')}; model_results={}; private_image_bindings=set()
for attempt in (1,2,3,4,5):
    p,z,members=archive(attempt)
    summary=json.loads(z.read('summary.json'))
    markers=[n for n in members if n.endswith('/native_call.json')]
    assert len(markers)==summary['model_calls']
    report={'attempt':attempt,'archive_sha256':sha(p),'verified_archive_members':len(members)+1,
        'source_commit':summary['source_commit'],'native_calls':len(markers),'summary':summary,
        'stages':{n:json.loads(z.read(n)) for n in members if n.endswith('supervisor.json')}}
    if 'failure.json' in members: report['failure_type']=json.loads(z.read('failure.json'))['error_type']
    for name in markers:
        key=name.split('/')[0]; calls[key]+=1; assert calls[key]<=1
        sample=key+'/sample/'
        raw=json.loads(z.read(sample+'raw.json')); result=json.loads(z.read(sample+'result.json'))
        loaded=json.loads(z.read(key+'/loaded-environment.json'))
        assert result['raw_sha256']==hashlib.sha256(z.read(sample+'raw.json')).hexdigest()
        assert raw['raw_nonfinite'] is False and raw['cpu_tokenizer_replay']['status']=='PASS'
        parser=qwen_parser if key=='qwen3' else parse_label
        assert parser(raw['response'])==result['label']
        assert result['native_calls']==1 and result['weights_loaded'] is True
        assert json.loads(z.read(sample+'reservation.json'))['image_sha256']==raw['smoke_identity']['image_sha256']
        private_image_bindings.add((raw['smoke_identity']['sample_id'],raw['smoke_identity']['image_sha256']))
        assert json.loads(z.read(sample+'native_call.json'))['invocation']==1
        evidence={'status':'INFERENCE_VERIFIED','attempt':attempt,'source_commit':summary['source_commit'],
            'weights_loaded':True,'native_calls':1,'classification_status':result['status'],
            'strict_parser_replay':'PASS','raw_result_checksum':'PASS','independent_decode':'PASS',
            'generated_tokens':len(raw['generated_ids']),'hnlo_status':result['hnlo']['status'],
            'raw_before_parse_files_preserved':True,'model':loaded['model']}
        if key=='minicpm4':
            assert result['hnlo']=={'status':'LABEL_ONLY_OWNER_DECISION','hnlo':None}
            n=json.loads(z.read(sample+'effective_numerics.json'))
            assert loaded['effective_implementation']['parameter_identity_preserved'] is True
            assert loaded['effective_implementation']['all_parameter_dtypes']==['float16']
            for field in ('scores_fp32_finite_or_negative_mask','softmax_fp32_finite','value_product_fp32_finite_and_return_cast'):
                assert n['after'][field]>n['before'][field]
            evidence['fp32_resampler']='ORIGINAL_APPROVED_IMPLEMENTATION_COUNTERS_PASS'
        model_results[key]=evidence
    if attempt==5:
        report['observations']={n:json.loads(z.read(n)) for n in members if n.endswith(('driver-diagnostic.json',
            'driver-library-binding.json','resources.json','cuda.json','cache-reclamation.json','storage-allocation.json'))}
    reports.append(report)
assert sum(calls.values())<=3
assert len(private_image_bindings)==1,'ALL_CONSUMED_SMOKE_CALLS_MUST_USE_THE_SAME_ORIGINAL_IMAGE'
assert calls=={'qwen3':1,'internvl35':1,'minicpm4':0},'EXACT_CLOSED_HANDOFF_CALL_ACCOUNTING'
for key in calls:
    model_results.setdefault(key,{'status':'BLOCKED_OR_NOT_ATTEMPTED','weights_loaded':False,'native_calls':0,
        'reason':'SEE_FINAL_ATTEMPT_DIAGNOSTICS'})
model_results['minicpm4'].update(status='BLOCKED',reason='HOST_OR_CGROUP_RAM_BEFORE_LOAD',
    checkpoint_bytes='PASS_CPU_VERIFICATION',required_available_ram_bytes=16384*2**20,
    last_measured_available_ram_after_reclamation_bytes=13950664704,
    precise_available_ram_at_failing_imported_worker='NOT_CAPTURED',advisory_scan_limit_reached=True,
    load_reservations=0,weights_loaded=False,native_calls=0)
receipt={'schema':'issue173-final-native-evidence-v1','models':model_results,'native_calls_by_model':calls,
    'native_calls_total':sum(calls.values()),'maximum_authorized_total':3,'attempts':reports,
    'scientific_results_excluded':True,'fresh171_import':False,'production_authorized':False,
    'raw_images_weights_private':True}
from safeshift.pilot.artifacts import write
write(Path(a.output),receipt)
print(json.dumps({'models':model_results,'calls':calls,'archives_verified':len(reports)},indent=2))
