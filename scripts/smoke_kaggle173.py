"""TERMINAL post-v5 Issue173 smoke route. Historical execution is immutable.

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
from safeshift.verification173 import verify_qwen, storage_budget
from scripts.verify_kaggle173_inputs import unique_mount

DIRECTIVE='https://github.com/tantdna2/SafeShift/issues/173#issuecomment-6580770922'
KEYS=('qwen3','internvl35','minicpm4')
ACTIVE_KEYS=()
TERMINAL_REASON='ISSUE173_V5_TERMINAL_QWEN_AND_INTERNVL_CONSUMED_MINICPM_REVIEW_REQUIRED'
SOFTWARE_SHA='b068aeb381cb3cff2b0978e7b5a398e009cb44dc4a43e6410083a766a252308f'
SOFTWARE_MARKER='f5af28b0d7b77b30a88732d2416b9216435bd1328e7d1aa336b753d3817820cc'
SLUGS=dict(zip(KEYS,('safeshift-qwen3-m1-model-provision-kaggle','safeshift-prepare-internvl35','safeshift-prepare-minicpm4')))
RUN_ID='issue173-smoke-20261102-v5'
NVIDIA_DRIVER_DIR=Path('/usr/local/nvidia/lib64')
_DRIVER_HANDLE=None


def terminal():
    """Permanent code fence, independent of local files or caller approval flags."""
    raise PermissionError(TERMINAL_REASON)


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


def utility_hardware(key,budgets,utility_env):
    """Smoke-local NVML check, same original driver/count/memory validation."""
    environment.policy(key,budgets)
    result=subprocess.run(['nvidia-smi','--query-gpu=index,name,memory.free,driver_version',
        '--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=5,env=utility_env)
    rows=[line.split(',') for line in result.stdout.strip().splitlines()]
    require(len(rows)==2 and all(len(r)==4 for r in rows),'EXACT_TWO_PHYSICAL_T4')
    observed=[]
    for i,row in enumerate(rows):
        index,name,free,driver=[s.strip() for s in row]
        require(index==str(i) and name in ('Tesla T4','NVIDIA T4'),'ORDERED_T4_IDENTITIES')
        require(driver in budgets['driver_versions'],'UNAPPROVED_DRIVER')
        require(tuple(map(int,driver.split('.')))>=(525,60,13),'CUDA12_DRIVER_FLOOR')
        require(int(free)>=budgets['free_mib_per_gpu'][i],'INDIVIDUAL_GPU_HEADROOM')
        observed.append({'index':i,'name':name,'free_mib':int(free),'driver':driver})
    return {'physical_gpus':observed,'cuda_initialized':False,'model_fit':'NOT_ESTABLISHED'}


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
        result=utility_hardware(key,policy,utility_env) if phase=='worker' else environment.hardware(key,policy)
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
    terminal()


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
    terminal()


def qwen_flat_backend(root):
    terminal()


def once(output,row,factory,key):
    terminal()


def worker(key,stage,request,out,scratch):
    terminal()


def launch(inputs,output,scratch,ref):
    terminal()


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(); p.add_argument('--worker',choices=('setup','reclaim','native','release')); p.add_argument('--key',choices=KEYS)
    p.add_argument('--request'); p.add_argument('--output',required=True); p.add_argument('--scratch',required=True)
    p.add_argument('--source-commit'); p.add_argument('--inputs',default='/kaggle/input'); a=p.parse_args()
    if a.worker: worker(a.key,a.worker,a.request,Path(a.output),Path(a.scratch))
    else: print(launch(a.inputs,a.output,a.scratch,a.source_commit))
