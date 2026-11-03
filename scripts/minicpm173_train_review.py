"""Exact one-image MiniCPM dispatch PREPARED FOR REVIEW, never activated here.

Every executable entry is held before I/O or model imports. The downstream code
is reviewable and CPU-testable; it is not a claim of real TRAIN path verification.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import zipfile

from safeshift.candidates.source import ROOT,require
from safeshift.candidates.train_inputs import checkpoint,discover
from safeshift.candidates.fulltrain import cohort
from safeshift.pilot.artifacts import read,write,sha,safe,export,verify_archive
from safeshift.pilot.contract import parse_label
from safeshift.smoke173_history import inspect_history,HOLD
from scripts.minicpm173_preflight import paths_from_mounts,memory,ram_gate,advise_owned_runtime,POLICY
from scripts.smoke_kaggle173 import admit_proof,driver_check,bind_cuda_driver,supervisor_log
from scripts.verify_kaggle173_inputs import unique_mount
from safeshift.fulltrain import provision,supervision,environment

IDENTITY='issue173-minicpm-original-train-last-review-v1'


def review_boundary():
    raise PermissionError(HOLD)


def bind_original(inputs):
    """Read-only exact source/ordinal binding, behind the public review fence."""
    history=inspect_history(paths_from_mounts(inputs))
    pin=read(ROOT/'configs/issue173/real_smoke.json')
    proof=safe(unique_mount(inputs,'safeshift-issue173-existing-bytes'),pin['byte_run_id'])
    checked=admit_proof(proof,pin['byte_evidence_sha256'])
    require(checked['source_commit']==pin['byte_source_commit'],'ORIGINAL_BYTE_PROOF_SOURCE')
    master=discover(inputs,'master_manifest.json').read_bytes()
    projection=cohort(master)  # Hash before JSON; original order, all 3763 IDs.
    first=projection['samples'][0]; original=json.loads(master)['samples'][0]
    image=safe(unique_mount(inputs,'inspecsafe-v1-kaggle'),'InspecSafe-V1-Kaggle/train/'+original['image_locator'])
    require(sha(image)==first['image_sha256'],'ORIGINAL_FIRST_IMAGE_BYTES')
    with zipfile.ZipFile(paths_from_mounts(inputs)[4]) as bundle:
        prior=json.loads(bundle.read('internvl35/sample/raw.json'))['smoke_identity']
    require(prior['ordinal']==first['ordinal']==0 and prior['sample_id']==first['sample_id']
        and prior['image_sha256']==first['image_sha256'],'SAME_ORIGINAL_ORDINAL_ZERO')
    return history,{**first,'image':str(image)}


def diagnostic_history(inputs):
    """Exact completed diagnostic seals must be supplied at future activation."""
    lock=read(ROOT/'configs/issue173/diagnostic_custody.json')
    receipts=[]
    for item in lock['attempts']:
        archive=safe(unique_mount(inputs,item['kernel_slug']),item['identity']+'.zip')
        require(sha(archive)==item['archive_sha256'],'DIAGNOSTIC_CUMULATIVE_CUSTODY')
        members=verify_archive(archive)
        with zipfile.ZipFile(archive) as bundle:
            result=json.loads(bundle.read('result.json'))
        require(result['identity']==item['identity'] and result['source_commit']==item['source_commit'],
            'DIAGNOSTIC_IDENTITY')
        require(result['call_reservations']==result['native_call_markers']==item['native_calls']
            and sum(n.endswith('/raw.json') for n in members)==item['native_calls'],
            'NO_UNCERTAIN_DIAGNOSTIC_CONSUMPTION')
        if item['model_key']=='minicpm4':
            require(result['weights_loaded'] and result['status']=='NATIVE_FORMAT_PASS','MINICPM_ACTUAL_DIAGNOSTIC_REQUIRED')
        receipts.append({'identity':item['identity'],'sha256':item['archive_sha256'],'calls':item['native_calls']})
    require(bool(receipts) and sum(r['calls'] for r in receipts)==lock['total_native_calls'],'COMPLETE_DIAGNOSTIC_LEDGER')
    return receipts


def once(inputs,out):
    review_boundary()
    history,row=bind_original(inputs); diagnostic_history(inputs)
    marker,source,weights=checkpoint(inputs,'minicpm4')
    from safeshift.candidates import minicpm_resampler_fp32 as numerical
    prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
    write(out/'load-reservation.json',{'identity':IDENTITY,'max_loads':1,'max_calls':1})
    model=numerical.backend('minicpm4',source,weights,prompt,device='cuda:0')
    write(out/'loaded.json',model.environment)
    sample=out/'sample'; sample.mkdir(exist_ok=False)
    write(sample/'reservation.json',{'identity':IDENTITY,'model_key':'minicpm4','ordinal':0,
        'sample_id':row['sample_id'],'image_sha256':row['image_sha256']})
    require(sha(row['image'])==row['image_sha256'],'ORIGINAL_IMAGE_PRECALL_HASH')
    raw=model.generate(row['image'],sample)
    raw['smoke_identity']={k:row[k] for k in ('ordinal','sample_id','image_sha256')}
    raw['smoke_identity'].update(run_id=IDENTITY,model_key='minicpm4',series_id=IDENTITY)
    checksum=write(sample/'raw.json',raw)
    require(raw['cpu_tokenizer_replay']['status']=='PASS' and not raw['raw_nonfinite'],'NATIVE_DECODE_FINITE_PROOF')
    label=parse_label(raw['response'])
    write(sample/'result.json',{'raw_sha256':checksum,'status':'SUCCESS' if label else 'INVALID',
        'label':label,'hnlo':None,'hnlo_status':'LABEL_ONLY_OWNER_DECISION','scientific_results_excluded':True})


def worker(stage,request_path,out,scratch):
    review_boundary()
    from scripts.diagnostic173 import source_check
    request=read(request_path)
    require(request['identity']==IDENTITY and stage in ('setup','native'),'EXACT_REVIEWED_MINI_STAGE')
    source_check(request['source_manifest']); bind_original('/kaggle/input'); diagnostic_history('/kaggle/input')
    if stage=='setup':
        from safeshift.candidates.train_runtime import prepare_runtime
        env=provision.clean_env(ROOT,scratch)
        python,env=prepare_runtime(ROOT,'minicpm4',scratch,out,env,time.monotonic()+600)
        write(out/'runtime.json',{'python':str(python),'env':env}); return
    bind_cuda_driver(out)
    write(out/'software.json',environment.software('minicpm4'))
    write(out/'hardware.json',driver_check('minicpm4',POLICY,out,'worker'))
    write(out/'cuda.json',environment.cuda('minicpm4',POLICY))
    write(out/'resources.json',environment.resources('minicpm4',POLICY,scratch,out))
    before=memory(); write(out/'before-load-memory.json',before); ram_gate(before)
    once('/kaggle/input',out)


def launch(inputs,output,scratch_parent,ref,manifest):
    review_boundary()
    from scripts.diagnostic173 import source_check
    source_check(manifest); history,row=bind_original(inputs); diagnostics=diagnostic_history(inputs)
    out=Path(output)/IDENTITY; out.mkdir(exist_ok=False)
    scratch=Path(scratch_parent)/('issue173-minicpm-ram-'+IDENTITY); scratch.mkdir(exist_ok=False)
    write(out/'request.json',{'identity':IDENTITY,'source_commit':ref,'source_manifest':manifest})
    write(out/'history.json',history); write(out/'diagnostic-history.json',diagnostics)
    write(out/'budget.json',{'max_loads':1,'max_calls':1,'max_seconds':1800,'model_key':'minicpm4',
        'ordinal':0,'original_global_calls_before':2,'original_global_calls_after_at_most':3,'policy':POLICY})
    deadline=time.monotonic()+1650; env=provision.clean_env(ROOT,scratch)
    try:
        for stage in ('setup','native'):
            python=sys.executable
            if stage=='native':
                write(out/'cache-advice.json',advise_owned_runtime(scratch))
                runtime=read(out/'runtime.json'); python,env=runtime['python'],runtime['env']; env['CUDA_VISIBLE_DEVICES']='0'
            supervision.run([str(python),'-B','-m','scripts.minicpm173_train_review','--worker',stage,
                '--request',str(out/'request.json'),'--output',str(out),'--scratch',str(scratch)],
                cwd=ROOT,env=env,deadline=min(deadline,time.monotonic()+(600 if stage=='setup' else 900)),
                log=supervisor_log(out,stage),receipt=out/(stage+'-supervisor.json'),max_log_bytes=16*2**20,watch_log_root=out)
    finally:
        write(out/'final-memory.json',memory()); export(out,Path(str(out)+'.zip'))


if __name__=='__main__':
    review_boundary()  # Also fail CLI before accepting a caller's flags or paths.
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('setup','native'),required=True)
    for name in ('request','output','scratch'): p.add_argument('--'+name,required=True)
    a=p.parse_args(); worker(a.worker,a.request,Path(a.output),Path(a.scratch))
