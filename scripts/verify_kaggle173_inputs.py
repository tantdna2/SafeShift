"""CPU-only, no-network verification of already attached private Inputs/Outputs."""
import os
from pathlib import Path
import platform
import shutil
import signal
import sys
import time
import traceback
import uuid

from safeshift.candidates.source import ROOT, require
from safeshift.candidates.train_inputs import mounts, discover
from safeshift.fulltrain.verification173 import verify_peer, verify_qwen, verify_train, storage_budget
from safeshift.pilot.artifacts import read, safe, sha, write, write_bytes, export
from safeshift.pilot.contract import digest


def unique_mount(inputs, slug):
    found = [p for p in mounts(inputs) if p.name == slug]
    require(len(found) == 1, "UNIQUE_MOUNT_REQUIRED:" + slug)
    return found[0]


def timeout(signum, frame):
    raise TimeoutError("VERIFICATION_DEADLINE")


def run(inputs, output, source_commit):
    require(platform.system() == 'Linux', 'LINUX_BOUND_REQUIRED')
    require(len(source_commit) == 40 and all(c in '0123456789abcdef' for c in source_commit), 'SOURCE_COMMIT')
    start = time.monotonic()
    signal.signal(signal.SIGALRM, timeout)
    signal.alarm(3000)
    root = Path(output)/('issue173-bytes-'+uuid.uuid4().hex)
    public, private = root/'public', root/'private'
    public.mkdir(parents=True, exist_ok=False)
    private.mkdir()
    source_files = ['scripts/verify_kaggle173_inputs.py', 'safeshift/fulltrain/verification173.py',
                    'configs/fulltrain/qwen3.json', 'configs/cpu_g2_g3/checkpoint_metadata_lock.json',
                    'configs/cpu_g2_g3/public_source_lock.json']
    result = {'schema':'issue173-existing-input-byte-verification-v1', 'source_commit':source_commit,
              'source_files':{n:sha(ROOT/n) for n in source_files}, 'model_calls':0, 'weights_loaded':False,
              'production_authorized':False, 'software_preflight':'REUSED_PR174_V2_NOT_RERUN',
              'input_copy_bytes':0, 'download_bytes':0, 'models':{}, 'train':{'status':'NOT_RUN'},
              'runtime':{'python':sys.version, 'platform':platform.platform(), 'gpu_requested':False,
                         'deadline_seconds':3000}}
    for name in ('/kaggle/working','/kaggle/temp'):
        usage=shutil.disk_usage(name)
        result['runtime'][name]={'device':os.stat(name).st_dev,'free_bytes':usage.free,'total_bytes':usage.total}
    for name in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.peak','/proc/meminfo'):
        p=Path(name)
        if p.is_file(): result['runtime'][name]=p.read_text()[:4096]
    try:
        storage_budget(shutil.disk_usage(output).free, 0, reserve_bytes=32*2**20)
        for key,slug,fn in (
            ('qwen3','safeshift-qwen3-m1-model-provision-kaggle',verify_qwen),
            ('internvl35','safeshift-prepare-internvl35',lambda p:verify_peer(p,'internvl35')),
            ('minicpm4','safeshift-prepare-minicpm4',lambda p:verify_peer(p,'minicpm4'))):
            try:
                result['models'][key] = fn(unique_mount(inputs,slug))
            except TimeoutError:
                raise
            except Exception as error:
                write_bytes(private/(key+'-failure.txt'),traceback.format_exc().encode())
                result['models'][key]={'status':'BLOCKED','error_type':type(error).__name__,
                    'reason':str(error) if isinstance(error,ValueError) else 'SEE_PRIVATE_FAILURE',
                    'weights_loaded':False,'model_calls':0}
            write(public/(key+'.json'),result['models'][key])
            print(key,result['models'][key]['status'],flush=True)
        try:
            master=discover(inputs,'master_manifest.json')
            original=unique_mount(inputs,'inspecsafe-v1-kaggle')
            # Only locked TRAIN JPG locators are opened; no TEST walk or sidecars.
            train_root=safe(original,'InspecSafe-V1-Kaggle/train/DATA_PATH')
            checked,projection,mapping=verify_train(master,train_root)
            write(private/'ordered-projection.json',projection)
            write(private/'original-image-mapping.json',mapping)
            write(private/'seal.json',{'schema':'issue173-original-train-seal-v1',**checked,
                'three_model_projection_sha256':{k:digest(projection) for k in ('qwen3','internvl35','minicpm4')}})
            # Per-image identities and derived private hashes stay outside public receipts.
            result['train']={k:v for k,v in checked.items() if k not in ('projection_sha256','mapping_sha256')}
            result['train']['identical_ordered_projection_for_three_models']=True
        except TimeoutError:
            raise
        except Exception as error:
            write_bytes(private/'train-failure.txt',traceback.format_exc().encode())
            result['train']={'status':'BLOCKED','error_type':type(error).__name__,
                'reason':str(error) if isinstance(error,ValueError) else 'SEE_PRIVATE_FAILURE'}
    except Exception:
        write_bytes(private/'job-failure.txt',traceback.format_exc().encode())
        result['job_failure']='SEE_PRIVATE_FAILURE'
    finally:
        signal.alarm(0)
        result['seconds']=time.monotonic()-start
        result['smoke']='NOT_RUN_CHECKPOINT_VERIFICATION_ONLY'
        write(public/'result.json',result)
        export(private,root/'PRIVATE-TRAIN-SEAL.zip')
        public_sha=export(public,root/'public-evidence.zip')
    print('VERIFY_EXPORTED',root.name,public_sha,flush=True)
    return {'run_id':root.name,'public_evidence_sha256':public_sha,'model_calls':0}
