"""Issue173 ONLY: one original TRAIN image/model, no production dispatcher.

This independent technical route never calls fulltrain.runtime internals or
alters contract.authorize(). Its byte-proof pin must be committed after the
separate CPU verification succeeds. It cannot dispatch arbitrary cohorts.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback
import uuid
import zipfile

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_inputs import discover
from safeshift.pilot.artifacts import read, safe, sha, write, write_bytes, export, verify_archive
from safeshift.pilot.contract import digest, parse_label, PROMPT_SHA
from safeshift.fulltrain import provision, supervision, environment
from safeshift.fulltrain.verification173 import verify_qwen, storage_budget
from scripts.verify_kaggle173_inputs import unique_mount

DIRECTIVE='https://github.com/tantdna2/SafeShift/issues/173#issuecomment-6580770922'
KEYS=('qwen3','internvl35','minicpm4')
SOFTWARE_SHA='b068aeb381cb3cff2b0978e7b5a398e009cb44dc4a43e6410083a766a252308f'
SOFTWARE_MARKER='f5af28b0d7b77b30a88732d2416b9216435bd1328e7d1aa336b753d3817820cc'
SLUGS=dict(zip(KEYS,('safeshift-qwen3-m1-model-provision-kaggle','safeshift-prepare-internvl35','safeshift-prepare-minicpm4')))
RUN_ID='issue173-smoke-20261102-v1'


def admit_proof(root, expected):
    archive=safe(root,'public-evidence.zip')
    require(sha(archive)==expected,'PINNED_BYTE_PROOF_ARCHIVE')
    hashes=verify_archive(archive)
    result=read(safe(root,'public/result.json'))
    require(sha(root/'public/result.json')==hashes['result.json'],'BYTE_PROOF_RESULT_BINDING')
    require(result['model_calls']==0 and result['weights_loaded'] is False
        and set(result['models'])==set(KEYS) and all(result['models'][k]['status']=='CHECKPOINT_BYTES_AND_HEADERS_PASS' for k in KEYS),
        'ALL_THREE_REAL_CHECKPOINT_PROOFS_REQUIRED')
    require(result['train']['status']=='TRAIN_BYTES_PASS' and result['train']['verified_images']==3763
        and all(result['train'][n]==0 for n in ('missing','changed','duplicate_ids')),'COMPLETE_ORIGINAL_TRAIN_PROOF_REQUIRED')
    private=safe(root,'PRIVATE-TRAIN-SEAL.zip')
    require(sha(private)==read(Path(str(private)+'.sha256.json'))['sha256'],'PRIVATE_SEAL_SIDECAR')
    verify_archive(private)
    return result


def scope(inputs='/kaggle/input'):
    """Re-derive the sole allowed row; direct child CLI cannot inject an image."""
    from safeshift.candidates.fulltrain import cohort
    from safeshift.fulltrain.contract import source_manifest
    pin=read(ROOT/'configs/issue173/real_smoke.json')
    require(sha(Path(__file__))==pin['smoke_script_sha256'] and
        digest(source_manifest())==pin['source_inventory_sha256'],'EXACT_SMOKE_SOURCE_PIN')
    proof_root=safe(unique_mount(inputs,'safeshift-issue173-existing-bytes'),pin['byte_run_id'])
    proof=admit_proof(proof_root,pin['byte_evidence_sha256'])
    require(proof['source_commit']==pin['byte_source_commit'],'BYTE_SOURCE_PIN')
    master=discover(inputs,'master_manifest.json')
    raw=master.read_bytes(); projection=cohort(raw)
    first=projection['samples'][0]
    original=json.loads(raw)['samples'][0]
    image=safe(unique_mount(inputs,'inspecsafe-v1-kaggle'),
        'InspecSafe-V1-Kaggle/train/'+original['image_locator'])
    row={**first,'image':str(image)}
    require(sha(image)==row['image_sha256'],'FIRST_ORIGINAL_IMAGE_HASH')
    return pin,row


def software_archive(inputs, scratch):
    # Exactly the already verified PR174 public software archive, no downloads.
    mount=unique_mount(inputs,'safeshift-issue173-public-software')
    found=[p for p in mount.iterdir() if p.name.endswith('-qwen-software.zip')]
    require(len(found)==1,'ONE_EXISTING_QWEN_SOFTWARE_ARCHIVE')
    archive=found[0]
    require(archive.stat().st_size==4209365519 and sha(archive)==SOFTWARE_SHA,'EXISTING_SOFTWARE_SHA')
    storage_budget(shutil.disk_usage(scratch).free,4209365519,temporary_bytes=12*2**30,reserve_bytes=2*2**30)
    target=Path(scratch)/'existing-qwen-software'; target.mkdir(exist_ok=False)
    with zipfile.ZipFile(archive) as bundle:
        rows=bundle.infolist()
        require(len(rows)==51 and sum(i.file_size for i in rows)<4300*2**20,'SOFTWARE_ZIP_BOUND')
        require(len({i.filename for i in rows})==51,'SOFTWARE_ZIP_DUPLICATE')
        for info in rows:
            require(not info.is_dir() and info.file_size<2*2**30,'SOFTWARE_ZIP_MEMBER_BOUND')
            destination=safe(target,info.filename); destination.parent.mkdir(parents=True,exist_ok=True)
            with bundle.open(info) as source,destination.open('xb') as out:
                shutil.copyfileobj(source,out,2**20)
    require(sha(target/'fresh_qwen_software.json')==SOFTWARE_MARKER,'SOFTWARE_MARKER_PIN')
    lock=read(target/'fresh_qwen_software.json')['runtime_lock']
    provision.software_input(target,SOFTWARE_MARKER,lock)
    return target,lock


def qwen_flat_backend(root):
    """Historical verified flat layout; inherit the unchanged V4 generation path.

    This explicitly identified constructor changes only snapshot path admission.
    No symlink, hardlink, renamed lock, weight copy or production fence bypass.
    """
    from safeshift.fulltrain import qwen
    import torch,transformers
    class VerifiedFlatQwen(qwen.QwenBackend):
        def __init__(self):
            self.stage='model_load'
            self.snapshot,self.repo=safe(root,'QWEN3_MODEL_FLAT'),ROOT
            self.receipt=verify_qwen(root)
            self.processor,self.tokenizer,self.t1=qwen.native_setup(self.snapshot,ROOT)
            require(sha(ROOT/'configs/pilot/classification_c1.txt')==PROMPT_SHA,'FROZEN_C1')
            self.prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
            self.model=transformers.Qwen3VLForConditionalGeneration.from_pretrained(str(self.snapshot),
                local_files_only=True,trust_remote_code=False,dtype=torch.float16,device_map=deepcopy(qwen.DEVICE_MAP))
            self.model.eval(); qwen.loaded_state(self.model)
            require(hasattr(self.model.model,'rope_deltas'),'QWEN_NATIVE_ROPE_LAYOUT')
            self.config=qwen.generation(self.model.generation_config)
            self.environment={'model':qwen.reference()['model'],'checkpoint':self.receipt,
                'source':qwen.verify_transformers(transformers),'generation':self.config.to_dict(),
                'device_map':qwen.DEVICE_MAP,'prompt_sha256':PROMPT_SHA,'tokenizer_t1':self.t1,
                'constructor':'issue173-verified-historical-flat-v1','constructor_sha256':sha(Path(__file__))}
    return VerifiedFlatQwen()


def once(output,row,factory,key):
    """Exclusive single-call journal; raw is fsynced before either parser/HNLO."""
    output=Path(output)
    write(output/'model-load-reservation.json',{'maximum_loads':1,'maximum_native_calls':1,'directive':DIRECTIVE})
    backend=factory()
    write(output/'loaded-environment.json',backend.environment)
    sample=output/'sample'; sample.mkdir(exist_ok=False)
    write(sample/'reservation.json',{'sample_id':row['sample_id'],'image_sha256':row['image_sha256'],
        'ordinal':0,'model_key':key,'scientific_results_excluded':True,'directive':DIRECTIVE})
    raw=backend.generate(row['image'],sample)
    raw['smoke_identity']={'model_key':key,'sample_id':row['sample_id'],'image_sha256':row['image_sha256'],
        'run_id':output.parent.name,'series_id':'issue173-smoke-'+key+'-20261102-v1','ordinal':0}
    raw_hash=write(sample/'raw.json',raw)
    require(raw.get('cpu_tokenizer_replay',{}).get('status')=='PASS','SMOKE_INDEPENDENT_DECODE_PROOF')
    from safeshift.fulltrain import qwen
    label=qwen.parser(raw['response']) if key=='qwen3' else parse_label(raw['response'])
    try:
        if key=='minicpm4':
            hnlo={'status':'LABEL_ONLY_OWNER_DECISION','hnlo':None}
        elif key=='qwen3': hnlo=qwen.replay(raw,label)
        else:
            from safeshift.pilot.hnlo import replay
            hnlo=replay(raw,label)
    except Exception as error:
        hnlo={'status':'HNLO_TECHNICAL_FAILURE','hnlo':None,'replay_status':'FAIL','error_type':type(error).__name__}
    require(raw.get('raw_nonfinite') is False,'SMOKE_NONFINITE_RAW')
    require((sample/'native_call.json').is_file(),'SMOKE_NATIVE_CALL_MARKER')
    result={'status':'SUCCESS' if label else 'INVALID','technical_status':'INFERENCE_AND_EXPORT_PENDING',
        'label':label,'raw_sha256':raw_hash,'native_calls':1,'weights_loaded':True,'hnlo':hnlo}
    write(sample/'result.json',result)
    require(hnlo.get('replay_status')!='FAIL' and hnlo.get('status')!='HNLO_TECHNICAL_FAILURE',
        'SMOKE_HNLO_REPLAY_FAILURE_CLASSIFICATION_PRESERVED')
    return result


def worker(key,stage,request,out,scratch):
    request=read(request)
    require(request['directive']==DIRECTIVE and request['max_native_calls']==1 and request['ordinal']==0,'SMOKE_ONLY_SCOPE')
    pin,row=scope()
    from safeshift.fulltrain.verification173 import checkpoint_spec
    require(request['model_key']==key and request['row']==row
        and request['checkpoint_root']==str(unique_mount('/kaggle/input',SLUGS[key]))
        and request['model_revision']==checkpoint_spec(key)['model']['revision']
        and request['resource_policy']==pin['resource_policy'],'WORKER_EXACT_ORIGINAL_SCOPE')
    require(out==Path('/kaggle/working')/RUN_ID/key and scratch==Path('/kaggle/temp')/RUN_ID/key
        and request['scratch']==str(scratch),'WORKER_FIXED_JOURNAL_AND_SCRATCH')
    activation=read(out.parent/'activation.json')
    require(activation['smoke_script_sha256']==sha(Path(__file__)) and activation['max_calls_total']==3
        and activation['max_calls_per_model']==1 and activation['directive']==DIRECTIVE,'PARENT_SMOKE_ACTIVATION')
    if stage=='setup':
        provision.prepare(request,ROOT,out,time.monotonic()+(1800 if key=='qwen3' else 600))
        return
    require(stage=='native','ONE_NATIVE_STAGE')
    write(out/'software.json',environment.software(key,ROOT,request.get('runtime_lock')))
    row=request['row']
    require(sha(row['image'])==row['image_sha256'],'FIRST_ORIGINAL_IMAGE_HASH')
    from PIL import Image
    with Image.open(row['image']) as image:
        require(getattr(image,'n_frames',1)==1,'FIRST_IMAGE_STILL'); image.load()
        write(out/'image-decode.json',{'size':list(image.size),'mode':image.mode,'rewritten':False})
    # Explicit technical budgets for this smoke only, never scientific O5.
    p=request['resource_policy']
    write(out/'resources.json',environment.resources(key,p,scratch,out))
    from safeshift.fulltrain.preflight import storage_probe
    write(out/'storage-allocation.json',storage_probe(scratch,out,
        scratch_bytes=p['scratch_probe_bytes'],output_bytes=p['output_probe_bytes']))
    write(out/'hardware.json',environment.hardware(key,p))
    write(out/'cuda.json',environment.cuda(key,p))
    prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
    require(sha(ROOT/'configs/pilot/classification_c1.txt')==PROMPT_SHA,'C1_PIN')
    if key=='qwen3': factory=lambda:qwen_flat_backend(request['checkpoint_root'])
    else:
        from safeshift.candidates.backend import CandidateBackend
        from safeshift.candidates.minicpm_resampler_fp32 import backend
        source=Path(request['checkpoint_root'])/'source'/request['model_revision']
        weights=Path(request['checkpoint_root'])/'weights'
        factory=(lambda:backend(key,source,weights,prompt,device='cuda:0')) if key=='minicpm4' else (
            lambda:CandidateBackend(key,source,weights,prompt,device='cuda:0'))
    once(out,row,factory,key)


def launch(inputs,output,scratch,ref):
    from safeshift.fulltrain.verification173 import checkpoint_spec
    from safeshift.fulltrain.contract import source_manifest
    require(inputs=='/kaggle/input' and output=='/kaggle/working' and scratch=='/kaggle/temp','FIXED_KAGGLE_ROOTS')
    require(len(ref)==40 and all(c in '0123456789abcdef' for c in ref),'EXACT_SOURCE_COMMIT')
    pin,row=scope(inputs)
    run_id=RUN_ID
    root=Path(output)/run_id; root.mkdir(exist_ok=False)
    scratch=Path(scratch)/run_id; scratch.mkdir(exist_ok=False)
    write(root/'activation.json',{'directive':DIRECTIVE,'source_commit':ref,'source_files':source_manifest(),
        'smoke_script_sha256':sha(Path(__file__)),'max_calls_total':3,'max_calls_per_model':1,
        'series':'issue173-smoke-20261102-v1','fresh171_import':False,'metrics_excluded':True,
        'global_exactly_once':'NOT_CLAIMED_EXTERNAL_SINGLE_SUBMISSION_CHECK_REQUIRED'})
    summary={'source_commit':ref,'run_id':run_id,'models':{},'model_calls':0,'production_authorized':False}
    deadline=time.monotonic()+3300
    try:
        software,lock=software_archive(inputs,scratch)
        for key,slug in SLUGS.items():
            out,temp=root/key,scratch/key; out.mkdir(); temp.mkdir()
            request={'model_key':key,'scratch':str(temp),'directive':DIRECTIVE,'max_native_calls':1,'ordinal':0,
                'row':row,'checkpoint_root':str(unique_mount(inputs,slug)),
                'model_revision':checkpoint_spec(key)['model']['revision'],'resource_policy':pin['resource_policy']}
            if key=='qwen3': request.update(software_input=str(software),software_marker_sha256=SOFTWARE_MARKER,runtime_lock=lock)
            write(out/'request.json',request)
            env=provision.clean_env(ROOT,temp)
            for stage in ('setup','native'):
                python=sys.executable
                if stage=='native':
                    runtime=read(out/'runtime.json'); python,env=runtime['python'],runtime['env']
                    env['CUDA_VISIBLE_DEVICES']='0,1' if key=='qwen3' else '0'
                command=[str(python),'-B','-m','scripts.smoke_kaggle173','--worker',stage,'--key',key,
                    '--request',str(out/'request.json'),'--output',str(out),'--scratch',str(temp)]
                cap=1800 if key=='qwen3' and stage=='setup' else 600
                supervision.run(command,cwd=ROOT,env=env,deadline=min(deadline,time.monotonic()+cap),
                    log=out/(stage+'.log'),receipt=out/(stage+'-supervisor.json'),max_log_bytes=16*2**20,watch_log_root=out)
            summary['models'][key]={'status':'INFERENCE_VERIFIED','native_calls':1,'weights_loaded':True,
                'classification':read(out/'sample/result.json')['status']}
    except Exception as error:
        write(root/'failure.json',{'error_type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()})
        summary['failure']='SEE_PRIVATE_FAILURE_NO_RETRY'
    finally:
        for key in KEYS:
            sample=root/key/'sample'
            calls=int((sample/'native_call.json').is_file())
            summary['model_calls']+=calls
            summary['models'].setdefault(key,{'status':'BLOCKED' if (root/key).exists() else 'NOT_ATTEMPTED','native_calls':calls,
                'weights_loaded':(root/key/'loaded-environment.json').is_file()})
        require(summary['model_calls']<=3,'GLOBAL_THREE_CALL_CAP')
        write(root/'summary.json',summary)
        export(root,Path(str(root)+'.zip'))
    return summary


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('setup','native')); p.add_argument('--key',choices=KEYS)
    p.add_argument('--request'); p.add_argument('--output',required=True); p.add_argument('--scratch',required=True)
    p.add_argument('--source-commit'); p.add_argument('--inputs',default='/kaggle/input'); a=p.parse_args()
    if a.worker: worker(a.key,a.worker,a.request,Path(a.output),Path(a.scratch))
    else: print(launch(a.inputs,a.output,a.scratch,a.source_commit))
