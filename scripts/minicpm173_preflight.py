"""MiniCPM-only RAM/processor preflight. No model loader or inference dispatcher.

Native continuation remains in permanent REVIEW HOLD in smoke173_history.
This diagnostic has zero calls, no attempt consumption and no production grant.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid

from safeshift.candidates.source import ROOT,require,verify_snapshot
from safeshift.candidates.train_inputs import checkpoint
from safeshift.candidates.train_runtime import prepare_runtime
from safeshift.fulltrain import provision,supervision,environment
from safeshift.pilot.artifacts import read,write,sha,export,safe
from safeshift.smoke173_history import inspect_history,mini_only_request,CONTINUATION
from scripts.verify_kaggle173_inputs import unique_mount
from scripts.smoke_kaggle173 import driver_check,bind_cuda_driver,supervisor_log

RAM_FLOOR=16384*2**20
POLICY=read(ROOT/'configs/issue173/real_smoke.json')['resource_policy']
MODEL='minicpm4'


def memory():
    root=Path('/sys/fs/cgroup')
    result={'monotonic':time.monotonic(),'pid':os.getpid(),'ppid':os.getppid(),**environment.host_memory()}
    for name in ('memory.current','memory.max','memory.peak','memory.events','memory.stat'):
        p=root/name
        if p.is_file():
            text=p.read_text()
            result[name]=({k:int(v) for k,v in (line.split() for line in text.splitlines())}
                if name in ('memory.events','memory.stat') else text.strip())
    p=Path('/proc/self/smaps_rollup')
    if p.is_file():
        result['self_smaps_rollup_kib']={r.split(':')[0]:int(r.split(':')[1].split()[0])
            for r in p.read_text().splitlines() if ':' in r and r.split(':')[1].split()[0].isdigit()}
    p=Path(f'/proc/self/task/{os.getpid()}/children')
    result['direct_children']=p.read_text().split() if p.is_file() else []
    pending=[os.getpid()]; tree=[]; seen=set()
    while pending and len(seen)<128:
        pid=pending.pop()
        if pid in seen: continue
        seen.add(pid)
        base=Path('/proc')/str(pid)
        try:
            fields={r.split(':',1)[0]:r.split(':',1)[1].strip() for r in (base/'status').read_text().splitlines() if ':' in r}
            tree.append({'pid':pid,'ppid':int(fields['PPid']),'rss_kib':int(fields.get('VmRSS','0 kB').split()[0]),
                'state':fields.get('State','UNKNOWN').split()[0]})
            pending.extend(map(int,(base/f'task/{pid}/children').read_text().split()))
        except (FileNotFoundError,ProcessLookupError): pass
    result['owned_process_tree']=tree
    result['process_tree_bound_reached']=bool(pending)
    return result


def ram_gate(observed):
    require(type(observed['available_bytes']) is int and observed['available_bytes']>=RAM_FLOOR,
        'MINICPM_RAM_BELOW_UNCHANGED_16GIB')
    return {'available_bytes':observed['available_bytes'],'required_bytes':RAM_FLOOR,'status':'PASS'}


def advise_owned_runtime(scratch):
    """Only this diagnostic's regular scratch files; never Input or history.

    No deletion. Bounded advice of installed large files releases file cache
    when possible. Measuring the next worker decides whether the floor passes.
    """
    scratch=Path(scratch)
    require(scratch.name.startswith('issue173-minicpm-ram-') and not scratch.is_symlink(),'OWNED_PREFLIGHT_ROOT')
    resolved=scratch.resolve(); count=visited=total=0; errors=[]; complete=True
    for directory,dirs,files in os.walk(scratch,followlinks=False):
        dirs[:]=[n for n in dirs if not (Path(directory)/n).is_symlink()]
        for name in files:
            visited+=1
            if visited>100000: complete=False; break
            path=Path(directory)/name
            require(path.resolve().is_relative_to(resolved),'ADVICE_OUTSIDE_OWNED_ROOT')
            info=path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size<8*2**20: continue
            try:
                with path.open('rb') as stream:
                    os.fsync(stream.fileno()); os.posix_fadvise(stream.fileno(),0,0,os.POSIX_FADV_DONTNEED)
                count+=1; total+=info.st_size
            except (OSError,AttributeError) as error: errors.append(type(error).__name__)
        if not complete: break
    return {'files_visited':visited,'scan_complete':complete,'advised_files':count,'advised_bytes':total,
        'errors':errors,'deleted_files':0,'input_or_checkpoint_bytes_changed':False,'effect':'ADVISORY_NOT_RAM_PROOF'}


def paths_from_mounts(inputs):
    result=[]
    for i in range(1,6):
        slug='safeshift-issue173-native-smoke'+(f'-v{i}' if i>1 else '')
        result.append(safe(unique_mount(inputs,slug),f'issue173-smoke-20261102-v{i}.zip'))
    return result


def worker(stage,request_path,out,scratch):
    require(stage in ('setup','processor'),'PREFLIGHT_STAGES_ONLY_NO_NATIVE_STAGE')
    request=read(request_path)
    require(request['model_key']=='minicpm4' and request['max_native_calls']==0
        and request['identity']==CONTINUATION,'MINICPM_ONLY_NO_CALL_REQUEST')
    history=inspect_history(paths_from_mounts('/kaggle/input'))
    require(history['consumed']['minicpm4']==0,'MINICPM_UNUSED_HISTORY')
    if stage=='setup':
        write(out/'setup-start-memory.json',memory())
        env=provision.clean_env(ROOT,scratch)
        python,env=prepare_runtime(ROOT,MODEL,scratch,out,env,time.monotonic()+600)
        write(out/'runtime.json',{'python':str(python),'env':env})
        write(out/'setup-finished-memory.json',memory())
        return
    write(out/'processor-before-import-memory.json',memory())
    bind_cuda_driver(out)
    write(out/'software.json',environment.software(MODEL))
    write(out/'software-after-import-memory.json',memory())
    from safeshift.candidates.loading import native_setup
    source=Path(request['source'])
    evidence={}
    processor,tokenizer,config,model_class=native_setup(source,MODEL,evidence)
    write(out/'processor-memory.json',memory())
    write(out/'processor-source.json',evidence)
    # Exercise image packing only, on a clearly synthetic image. Never forward.
    from PIL import Image
    from safeshift.candidates.inputs import prepare_inputs,validate_inputs
    prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
    with Image.new('RGB',(448,448),(128,128,128)) as image:
        rendered,values=prepare_inputs(processor,MODEL,prompt,image)
        detail=validate_inputs(processor,MODEL,config,rendered,values,prompt)
    write(out/'synthetic-processor.json',{'scope':'SYNTHETIC_IMAGE_NO_MODEL','detail':detail,'model_calls':0})
    write(out/'synthetic-processor-memory.json',memory())
    write(out/'hardware.json',driver_check(MODEL,POLICY,out,'worker'))
    write(out/'cuda.json',environment.cuda(MODEL,POLICY))
    before=memory(); write(out/'before-weight-load-memory.json',before)
    passed=ram_gate(before)
    write(out/'preload-ram-gate.json',passed)
    write(out/'processor-result.json',{'status':'MINICPM_SOFTWARE_PROCESSOR_CUDA_AND_PRELOAD_RAM_PASS',
        'weights_loaded':False,'model_calls':0,'model_fit':'NOT_VERIFIED','native_dispatch':'BLOCKED_PENDING_CHATGPT_REVIEW'})


def launch(inputs,output,scratch_parent,ref):
    require(len(ref)==40 and all(c in '0123456789abcdef' for c in ref),'EXACT_COMMITTED_SOURCE')
    history=inspect_history(paths_from_mounts(inputs))
    # No original dataset, Qwen weights or InternVL weights are attached/read.
    marker,source,weights=checkpoint(inputs,MODEL)
    verify_snapshot(source,MODEL)
    from safeshift.verification173 import checkpoint_spec
    spec=checkpoint_spec(MODEL)
    require(sha(weights/spec['index'])==spec['files'][spec['index']]['sha256'],'MINICPM_INDEX_PIN')
    require(all((weights/n).stat().st_size==p['size'] for n,p in spec['files'].items()),'EXISTING_CHECKPOINT_FILE_SIZES')
    run_id='issue173-minicpm-ram-'+uuid.uuid4().hex
    out=Path(output)/run_id; out.mkdir(exist_ok=False)
    scratch=Path(scratch_parent)/run_id; scratch.mkdir(exist_ok=False)
    request={'identity':CONTINUATION,'model_key':MODEL,'max_native_calls':0,'source':str(source)}
    write(out/'request.json',request); write(out/'history.json',history)
    write(out/'prepared-mini-only-request.json',mini_only_request(history))
    initial=memory(); write(out/'startup-memory.json',initial)
    result={'schema':'issue173-minicpm-fresh-ram-preflight-v1','run_id':run_id,'source_commit':ref,
        'model_calls':0,'weights_loaded':False,'consumption_created':False,'status':'BLOCKED',
        'history_native_calls':history['consumed'],'ram_floor_bytes':RAM_FLOOR,
        'native_dispatch':'BLOCKED_PENDING_CHATGPT_DIRECT_REVIEW','input_copy_bytes':0,'weight_download_bytes':0}
    samples=[]; stop=threading.Event()
    def monitor():
        while not stop.wait(.5):
            if len(samples)<3000: samples.append(memory())
    thread=threading.Thread(target=monitor,daemon=True); thread.start()
    deadline=time.monotonic()+1500
    try:
        env=provision.clean_env(ROOT,scratch)
        for stage in ('setup','processor'):
            python=sys.executable
            if stage=='processor':
                write(out/'before-cache-advice-memory.json',memory())
                write(out/'owned-cache-advice.json',advise_owned_runtime(scratch))
                write(out/'after-cache-advice-memory.json',memory())
                runtime=read(out/'runtime.json'); python,env=runtime['python'],runtime['env']
                env['CUDA_VISIBLE_DEVICES']='0'
            command=[str(python),'-B','-m','scripts.minicpm173_preflight','--worker',stage,
                '--request',str(out/'request.json'),'--output',str(out),'--scratch',str(scratch)]
            supervision.run(command,cwd=ROOT,env=env,deadline=min(deadline,time.monotonic()+600),
                log=supervisor_log(out,stage),receipt=out/(stage+'-supervisor.json'),max_log_bytes=16*2**20,watch_log_root=out)
            write(out/(stage+'-after-child-exit-memory.json'),memory())
        result['status']='PREFLIGHT_PASS_NATIVE_REVIEW_HOLD'
    except Exception as error:
        # Failure log/trace remains private in this diagnostic export; no raw/model call.
        import traceback
        write(out/'failure.json',{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()})
        result['failure']='SEE_FAILURE_AND_PRELOAD_MEMORY_NO_INFERENCE'
    finally:
        stop.set(); thread.join(timeout=2)
        write(out/'memory-timeline.json',samples)
        write(out/'final-memory.json',memory()); write(out/'result.json',result)
        export(out,Path(str(out)+'.zip'))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('setup','processor'))
    p.add_argument('--request'); p.add_argument('--output',required=True); p.add_argument('--scratch',required=True)
    p.add_argument('--inputs',default='/kaggle/input'); p.add_argument('--source-commit'); a=p.parse_args()
    if a.worker: worker(a.worker,a.request,Path(a.output),Path(a.scratch))
    else: print(launch(a.inputs,a.output,a.scratch,a.source_commit))
