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
import stat
import subprocess
import ctypes.util
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
ACTIVE_KEYS=('internvl35','minicpm4')
SOFTWARE_SHA='b068aeb381cb3cff2b0978e7b5a398e009cb44dc4a43e6410083a766a252308f'
SOFTWARE_MARKER='f5af28b0d7b77b30a88732d2416b9216435bd1328e7d1aa336b753d3817820cc'
SLUGS=dict(zip(KEYS,('safeshift-qwen3-m1-model-provision-kaggle','safeshift-prepare-internvl35','safeshift-prepare-minicpm4')))
RUN_ID='issue173-smoke-20261102-v5'
NVIDIA_DRIVER_DIR=Path('/usr/local/nvidia/lib64')
_DRIVER_HANDLE=None


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


def previous_preload_failure(archive,pin):
    require(sha(archive)==pin['prior_preload_failure_sha256'],'PRIOR_FAILURE_PIN')
    members=verify_archive(archive)
    require(not any(n.endswith(('native_call.json','model-load-reservation.json','loaded-environment.json')) for n in members),
        'PRIOR_LOAD_OR_CALL_RESERVATION_NO_RETRY')
    with zipfile.ZipFile(archive) as bundle:
        old=json.loads(bundle.read('summary.json'))
    require(old['run_id']=='issue173-smoke-20261102-v1' and old['source_commit']==pin['prior_source_commit']
        and set(old['models'])==set(KEYS) and old['model_calls']==0
        and all(r['native_calls']==0 and r['weights_loaded'] is False for r in old['models'].values()),
        'PRIOR_CONSUMPTION_UNKNOWN_NO_RETRY')
    return old


def previous_completed_qwen(archive,pin):
    require(sha(archive)==pin['prior_qwen_archive_sha256'],'PRIOR_QWEN_ARCHIVE_PIN')
    members=verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        old=json.loads(bundle.read('summary.json'))
        raw=json.loads(bundle.read('qwen3/sample/raw.json'))
        result=json.loads(bundle.read('qwen3/sample/result.json'))
    require(old['source_commit']==pin['prior_qwen_source_commit'] and old['model_calls']==1
        and old['models']['qwen3']['native_calls']==1 and old['models']['qwen3']['weights_loaded'] is True
        and all(old['models'][k]['native_calls']==0 for k in ACTIVE_KEYS),'PRIOR_MODEL_CALL_ACCOUNTING')
    require({n for n in members if n.endswith('/native_call.json')}=={'qwen3/sample/native_call.json'}
        and {n for n in members if n.endswith('/model-load-reservation.json')}=={'qwen3/model-load-reservation.json'}
        and {n for n in members if n.endswith('/loaded-environment.json')}=={'qwen3/loaded-environment.json'},
        'PRIOR_UNKNOWN_OR_PEER_LOAD_NO_RETRY')
    require(raw['raw_nonfinite'] is False and result['raw_sha256']==members['qwen3/sample/raw.json']
        and raw['smoke_identity']['model_key']=='qwen3','PRIOR_QWEN_RAW_CUSTODY')
    return raw['smoke_identity']


def supervisor_log(out,stage):
    return Path(out)/(stage+'-supervisor.log')  # runtime exclusively owns setup.log


def driver_check(key,policy,out,phase):
    """Preserve the actual failing subprocess streams; never bypass its gate."""
    probe={'phase':phase,'binary':shutil.which('nvidia-smi'),'nvml_find_library':ctypes.util.find_library('nvidia-ml'),
        'loader_environment':{n:os.environ.get(n) for n in ('LD_LIBRARY_PATH','LD_PRELOAD','NVIDIA_VISIBLE_DEVICES','NVIDIA_DRIVER_CAPABILITIES')},
        'nvml_paths':{p:Path(p).exists() for p in ('/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1',
            '/usr/local/nvidia/lib64/libnvidia-ml.so.1','/usr/lib64/libnvidia-ml.so.1')}}
    utility_env=None
    if phase=='worker':
        require((NVIDIA_DRIVER_DIR/'libnvidia-ml.so.1').is_file(),'SYSTEM_NVML_DRIVER_MOUNT_REQUIRED')
        utility_env={**os.environ,'LD_LIBRARY_PATH':str(NVIDIA_DRIVER_DIR)}
        probe['utility_only_loader_override']={'LD_LIBRARY_PATH':str(NVIDIA_DRIVER_DIR)}
    try:
        result=environment.hardware(key,policy,utility_env=utility_env)
        probe.update(status='PASS',hardware=result)
        return result
    except subprocess.CalledProcessError as error:
        probe.update(status='BLOCKED',returncode=error.returncode,command=error.cmd,
            stdout=str(error.stdout or '')[:4096],stderr=str(error.stderr or '')[:4096])
        raise
    finally:
        write(Path(out)/(phase+'-driver-diagnostic.json'),probe)


def bind_cuda_driver(out):
    """Load only the mounted host CUDA driver, without changing Python LD paths."""
    global _DRIVER_HANDLE
    library=NVIDIA_DRIVER_DIR/'libcuda.so.1'
    require(library.is_file(),'SYSTEM_CUDA_DRIVER_MOUNT_REQUIRED')
    with library.open('rb') as stream: require(stream.read(4)==b'\x7fELF','SYSTEM_CUDA_DRIVER_ELF')
    _DRIVER_HANDLE=ctypes.CDLL(str(library),mode=ctypes.RTLD_GLOBAL)
    write(Path(out)/'driver-library-binding.json',{'implementation':'issue173-explicit-host-cuda-driver-v1',
        'library':str(library),'library_sha256':sha(library),'library_bytes':library.stat().st_size,
        'python_ld_library_path_changed':False,'nvml_utility_loader_scoped_to_subprocess':True,
        'cuda_initialized':False,'model_calls':0})


def scope(inputs='/kaggle/input'):
    """Re-derive the sole allowed row; direct child CLI cannot inject an image."""
    from safeshift.candidates.fulltrain import cohort
    from safeshift.fulltrain.contract import source_manifest
    pin=read(ROOT/'configs/issue173/real_smoke.json')
    require(pin['schema']=='issue173-single-smoke-release-v5' and pin['directive']==DIRECTIVE,'SMOKE_RELEASE_IDENTITY')
    require(sha(Path(__file__))==pin['smoke_script_sha256'] and
        digest(source_manifest())==pin['source_inventory_sha256'],'EXACT_SMOKE_SOURCE_PIN')
    proof_root=safe(unique_mount(inputs,'safeshift-issue173-existing-bytes'),pin['byte_run_id'])
    proof=admit_proof(proof_root,pin['byte_evidence_sha256'])
    require(proof['source_commit']==pin['byte_source_commit'],'BYTE_SOURCE_PIN')
    prior=safe(unique_mount(inputs,'safeshift-issue173-native-smoke'),'issue173-smoke-20261102-v1.zip')
    previous_preload_failure(prior,pin)
    completed=safe(unique_mount(inputs,'safeshift-issue173-native-smoke-v2'),'issue173-smoke-20261102-v2.zip')
    previous=previous_completed_qwen(completed,pin)
    zero=safe(unique_mount(inputs,'safeshift-issue173-native-smoke-v3'),'issue173-smoke-20261102-v3.zip')
    require(sha(zero)==pin['prior_zero_peer_archive_sha256'],'PRIOR_ZERO_PEER_PIN')
    members=verify_archive(zero)
    require(not any(n.endswith(('native_call.json','model-load-reservation.json','loaded-environment.json')) for n in members),
        'PRIOR_PEER_RESERVATION_OR_CALL_NO_RETRY')
    with zipfile.ZipFile(zero) as bundle: old=json.loads(bundle.read('summary.json'))
    require(old['source_commit']==pin['prior_zero_peer_source_commit'] and old['model_calls']==0
        and old['prior_native_calls']==1,'PRIOR_ZERO_PEER_ACCOUNTING')
    zero=safe(unique_mount(inputs,'safeshift-issue173-native-smoke-v4'),'issue173-smoke-20261102-v4.zip')
    require(sha(zero)==pin['prior_driver_diagnostic_sha256'],'PRIOR_DRIVER_DIAGNOSTIC_PIN')
    members=verify_archive(zero)
    require(not any(n.endswith(('native_call.json','model-load-reservation.json','loaded-environment.json')) for n in members),
        'PRIOR_DIAGNOSTIC_CONSUMPTION_NO_RETRY')
    with zipfile.ZipFile(zero) as bundle: old=json.loads(bundle.read('summary.json'))
    require(old['model_calls']==0 and old['prior_native_calls']==1 and old['source_commit']==pin['prior_driver_source_commit'],
        'PRIOR_DRIVER_DIAGNOSTIC_ACCOUNTING')
    master=discover(inputs,'master_manifest.json')
    raw=master.read_bytes(); projection=cohort(raw)
    first=projection['samples'][0]
    original=json.loads(raw)['samples'][0]
    image=safe(unique_mount(inputs,'inspecsafe-v1-kaggle'),
        'InspecSafe-V1-Kaggle/train/'+original['image_locator'])
    row={**first,'image':str(image)}
    require(sha(image)==row['image_sha256'],'FIRST_ORIGINAL_IMAGE_HASH')
    require(previous['sample_id']==row['sample_id'] and previous['image_sha256']==row['image_sha256']
        and previous['ordinal']==0,'EXACT_SAME_ORIGINAL_SMOKE_IMAGE')
    return pin,row


def reclaim_setup_cache(root,out,*,minimum_bytes=8*2**20,phase='setup'):
    """Delete only this attempt's redundant public install/build cache.

    Advise eviction of large regular files in the retained OWN runtime only;
    never change bytes, a RAM threshold, global caches, Inputs, weights or history.
    The subsequent measured RAM gate decides, not success of this advice.
    """
    root=Path(root)
    require(root.name==RUN_ID and root.is_dir() and not root.is_symlink(),'OWNED_SCRATCH_ROOT')
    resolved=root.resolve()
    before=environment.host_memory()
    removed=[]
    targets=('existing-qwen-software','qwen3/qwen-software/python-source','qwen3/qwen-software/zlib-source')
    for name in targets:
        path=safe(root,name)
        require(path.resolve().is_relative_to(resolved) and path.resolve()!=resolved,'CLEANUP_OUTSIDE_ATTEMPT')
        if path.exists():
            require(path.is_dir() and not path.is_symlink(),'CACHE_DIRECTORY_REQUIRED')
            shutil.rmtree(path)
            removed.append(name)
    advised=advised_bytes=visited=0
    bounded=False
    errors=[]
    for directory,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[n for n in dirs if not (Path(directory)/n).is_symlink()]
        for name in files:
            visited+=1
            if visited>50000:
                bounded=True
                break
            path=Path(directory)/name
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size<minimum_bytes: continue
            require(path.resolve().is_relative_to(resolved),'ADVICE_OUTSIDE_ATTEMPT')
            try:
                with path.open('rb') as stream:
                    os.fsync(stream.fileno())
                    os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
                advised+=1; advised_bytes+=info.st_size
            except (OSError,AttributeError) as error:
                errors.append(type(error).__name__)
        if bounded: break
    value={'schema':'issue173-owned-cache-reclamation-v1','before':before,'after':environment.host_memory(),
        'removed_owned_cache_directories':removed,'advised_regular_files':advised,'advised_file_bytes':advised_bytes,
        'advice_errors':errors,'scan_limit_reached':bounded,'weights_or_inputs_modified':False,'runtime_files_retained':True,
        'ram_floor_mib_unchanged':16384,'proof':'ADVISORY_ONLY_SUBSEQUENT_RAM_GATE_REQUIRED'}
    write(Path(out)/(phase+'-cache-reclamation.json'),value)
    return value


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
        'run_id':output.parent.name,'series_id':RUN_ID+'-'+key,'ordinal':0}
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
    require(key in ACTIVE_KEYS,'MODEL_ALREADY_CONSUMED_NO_LOAD_OR_CALL')
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
    if stage=='reclaim':
        require((out/'runtime.json').is_file()
            and not (out/'model-load-reservation.json').exists(),'RECLAIM_ONLY_AFTER_SETUP_BEFORE_LOAD')
        reclaim_setup_cache(scratch.parent,out)
        return
    if stage=='release':
        require((out/'sample/result.json').is_file() and (out/'sample/native_call.json').is_file(),
            'POST_CALL_RECLAMATION_REQUIRES_DURABLE_RESULT')
        reclaim_setup_cache(scratch.parent,out,phase='post-call')
        return
    require(stage=='native','ONE_NATIVE_STAGE')
    bind_cuda_driver(out)
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
    write(out/'hardware.json',driver_check(key,p,out,'worker'))
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
        'series':RUN_ID,'fresh171_import':False,'metrics_excluded':True,
        'global_exactly_once':'NOT_CLAIMED_EXTERNAL_SINGLE_SUBMISSION_CHECK_REQUIRED'})
    summary={'source_commit':ref,'run_id':run_id,'models':{'qwen3':{
        'status':'PRIOR_SMOKE_CONSUMED_NOT_REPLAYED','native_calls':0,'prior_native_calls':1,'weights_loaded':False}},
        'model_calls':0,'prior_native_calls':1,'production_authorized':False}
    deadline=time.monotonic()+3300
    try:
        driver_check('internvl35',pin['resource_policy'],root,'kernel')
        for key in ACTIVE_KEYS:
            slug=SLUGS[key]
            out,temp=root/key,scratch/key; out.mkdir(); temp.mkdir()
            request={'model_key':key,'scratch':str(temp),'directive':DIRECTIVE,'max_native_calls':1,'ordinal':0,
                'row':row,'checkpoint_root':str(unique_mount(inputs,slug)),
                'model_revision':checkpoint_spec(key)['model']['revision'],'resource_policy':pin['resource_policy']}
            write(out/'request.json',request)
            env=provision.clean_env(ROOT,temp)
            for stage in ('setup','reclaim','native','release'):
                python=sys.executable
                if stage=='native':
                    runtime=read(out/'runtime.json'); python,env=runtime['python'],runtime['env']
                    env['CUDA_VISIBLE_DEVICES']='0,1' if key=='qwen3' else '0'
                else:
                    env=provision.clean_env(ROOT,temp)
                command=[str(python),'-B','-m','scripts.smoke_kaggle173','--worker',stage,'--key',key,
                    '--request',str(out/'request.json'),'--output',str(out),'--scratch',str(temp)]
                cap=300 if stage in ('reclaim','release') else 600
                supervision.run(command,cwd=ROOT,env=env,deadline=min(deadline,time.monotonic()+cap),
                    log=supervisor_log(out,stage),receipt=out/(stage+'-supervisor.json'),max_log_bytes=16*2**20,watch_log_root=out)
                if stage=='native':
                    summary['models'][key]={'status':'INFERENCE_VERIFIED','native_calls':1,'weights_loaded':True,
                        'classification':read(out/'sample/result.json')['status']}
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
        require(summary['model_calls']<=2 and summary['prior_native_calls']+summary['model_calls']<=3,'GLOBAL_THREE_CALL_CAP')
        write(root/'summary.json',summary)
        export(root,Path(str(root)+'.zip'))
    return summary


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('setup','reclaim','native','release')); p.add_argument('--key',choices=KEYS)
    p.add_argument('--request'); p.add_argument('--output',required=True); p.add_argument('--scratch',required=True)
    p.add_argument('--source-commit'); p.add_argument('--inputs',default='/kaggle/input'); a=p.parse_args()
    if a.worker: worker(a.key,a.worker,a.request,Path(a.output),Path(a.scratch))
    else: print(launch(a.inputs,a.output,a.scratch,a.source_commit))
