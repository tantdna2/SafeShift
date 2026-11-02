"""Public-source-only model software qualification under Linux supervision.

No Input reader, weight loader, production authorization or native model call.
CPU uses the actual pinned processor/meta-loader on synthetic images. GPU stage
is a tensor probe in that same isolated worker; it cannot establish model fit.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback
import uuid
from urllib.parse import unquote, urlparse

from scripts.prepare_qwen173_software import download
from safeshift.candidates.source import ROOT, require, verify_snapshot
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import digest
from safeshift.fulltrain import contract, provision, supervision


def invoke(argv, cwd, env, output, name, deadline):
    with (output / (name + '.log')).open('xb') as stream:
        subprocess.run(list(map(str, argv)), cwd=cwd, env=env, stdout=stream,
                       stderr=subprocess.STDOUT, check=True, timeout=max(.1, deadline-time.monotonic()))


def qwen_runtime(scratch, output, env, deadline):
    """Same build flags/bootstrap/offline install as fulltrain.provision.prepare.

    First acquisition resolves on the actual Linux cp312 interpreter, seals
    every wheel, then installs exclusively from that closure without resolution.
    Subsequent production provisioning accepts this sealed software Input only.
    """
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'LINUX_X86_64_REQUIRED')
    ref = read(ROOT/'configs/fulltrain/qwen3.json')
    software = scratch/'software'
    software.mkdir()
    (software/'wheels').mkdir()
    sources = {}
    for component in ('python', 'zlib'):
        row = ref[component+'_source']
        name = row['url'].rsplit('/',1)[1]
        value = download(row['url'], software/name, row['sha256'])
        sources[component+'_source'] = {k:value[k] for k in ('file','size','sha256')}
        provision.extract_source(software/name, scratch/(component+'-source'))
    write(output/'build-sources.json', sources)
    zsource, zprefix = scratch/'zlib-source/zlib-1.2.11', scratch/'zlib'
    for argv, name in ((['./configure','--prefix='+str(zprefix)],'zlib-configure'),
                       (['make','-j2'],'zlib-make'), (['make','install'],'zlib-install')):
        invoke(argv, zsource, env, output, name, deadline)
    build_env = dict(env, CPPFLAGS='-I'+str(zprefix/'include'),
        LDFLAGS='-L'+str(zprefix/'lib')+' -Wl,-rpath,'+str(zprefix/'lib'),
        ZLIB_CFLAGS='-I'+str(zprefix/'include'), ZLIB_LIBS='-L'+str(zprefix/'lib')+' -lz')
    psource, prefix = scratch/'python-source/Python-3.12.13', scratch/'cpython'
    for argv, name in ((['./configure','--prefix='+str(prefix),'--with-ensurepip=no'],'python-configure'),
                       (['make','-j2'],'python-make'), (['make','install'],'python-install')):
        invoke(argv, psource, build_env, output, name, deadline)
    venv = scratch/'venv'
    invoke([prefix/'bin/python3.12','-I','-B','-m','venv','--without-pip','--copies',venv], ROOT, env, output, 'venv', deadline)
    python = venv/'bin/python'
    pip_ref = read(ROOT/'configs/pilot/pip_bootstrap.json')['pip']
    pip_wheel = software/'wheels'/pip_ref['filename']
    download(pip_ref['url'], pip_wheel, pip_ref['sha256'])
    code = "import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module('pip',run_name='__main__')"
    invoke([python,'-I','-B','-c',code,pip_wheel,'install','--no-index','--no-deps',pip_wheel], ROOT, env, output, 'pip-bootstrap', deadline)
    pip = [python,'-I','-B','-m','pip','--isolated','--disable-pip-version-check']
    req = [n+'=='+v for n,v in ref['software'].items() if n not in ('python','zlib')] + ['pip==25.0.1']
    invoke(pip+['install','--dry-run','--ignore-installed','--only-binary=:all:',
        '--index-url','https://pypi.org/simple','--extra-index-url','https://download.pytorch.org/whl/cu128',
        '--timeout','20','--retries','0','--report',output/'resolver.json',*req], ROOT, env, output, 'resolver', deadline)
    resolved = read(output/'resolver.json')['install']
    require(1 <= len(resolved) <= 256, 'WHEEL_COUNT_BOUND')
    lock = {'versions':{}, 'wheels':[]}
    provenance, total = [], 0
    for item in resolved:
        url = item['download_info']['url']
        require(urlparse(url).scheme == 'https' and urlparse(url).hostname in
                ('files.pythonhosted.org','download.pytorch.org'), 'PUBLIC_WHEEL_HOST')
        name = unquote(urlparse(url).path.rsplit('/',1)[1])
        require('/' not in name and '\\' not in name and name.endswith('.whl'), 'WHEEL_BASENAME')
        checksum = item['download_info']['archive_info']['hashes']['sha256']
        target = software/'wheels'/name
        if target == pip_wheel:
            require(sha(target) == checksum, 'PIP_RESOLVER_HASH')
        else:
            download(url, target, checksum, max_bytes=min(4*2**30,16*2**30-total), seconds=240)
        total += target.stat().st_size
        require(total <= 16*2**30, 'TOTAL_WHEEL_BYTES')
        package = item['metadata']['name'].lower().replace('_','-').replace('.','-')
        require(package not in lock['versions'], 'DUPLICATE_DISTRIBUTION')
        version = item['metadata']['version']
        lock['versions'][package] = version
        lock['wheels'].append({'file':name,'name':package,'version':version,'size':target.stat().st_size,'sha256':checksum})
        provenance.append({'file':name,'url':url,'sha256':checksum})
    marker = software/'fresh_qwen_software.json'
    write(marker, {'schema':'fresh-qwen-software-v1','runtime_lock':lock,**sources})
    provision.software_input(software,sha(marker),lock,ROOT)
    write(output/'runtime-lock.json',lock)
    write(output/'wheel-provenance.json',provenance)
    write(output/'software-marker.json',read(marker))
    write(output/'software-seal.json',{'marker_sha256':sha(marker),'runtime_lock_sha256':digest(lock),
        'wheel_bytes':total,'target':'cp312_linux_x86_64','software_input_scope':'PUBLIC_SOFTWARE_ONLY'})
    invoke(pip+['install','--no-index','--no-deps',*[software/'wheels'/r['file'] for r in lock['wheels']]],
           ROOT,env,output,'offline-install',deadline)
    invoke(pip+['check'],ROOT,env,output,'pip-check',deadline)
    env.update(SAFESHIFT_WORKER_PYTHON=str(python),SAFESHIFT_RUNTIME_ROOT=str(venv),PYTORCH_ALLOC_CONF='expandable_segments:True')
    return python, env


def public_snapshot(key, scratch, output):
    if key == 'qwen3':
        from safeshift.fulltrain.qwen import reference
        spec = reference()
        model = spec['model']
        files = {r['path']:r['sha256'] for r in spec['snapshot_files'] if not r['path'].endswith('.safetensors')}
    else:
        spec = read(ROOT/'configs/cpu_g2_g3/public_source_lock.json')[key]
        model, files = spec, spec['files']
    snapshot = scratch/model['revision']
    snapshot.mkdir()
    receipts = []
    for name, checksum in files.items():
        url = 'https://huggingface.co/'+model['id']+'/resolve/'+model['revision']+'/'+name
        receipts.append(download(url,snapshot/name,checksum))
    if key == 'qwen3':
        from safeshift.fulltrain.qwen import verify_snapshot as verify
        verify(snapshot, weights=False)
    else:
        verify_snapshot(snapshot,key)
    write(output/'public-source.json',{'model':{'id':model['id'],'revision':model['revision']},'files':receipts,'weights':False})
    return snapshot


def worker(key, stage, output, scratch):
    if stage == 'setup':
        env = provision.clean_env(ROOT,scratch)
        deadline = float(os.environ['ISSUE173_DEADLINE'])
        if key == 'qwen3':
            python, env = qwen_runtime(scratch,output,env,deadline)
        else:
            from safeshift.candidates.train_runtime import prepare_runtime
            python, env = prepare_runtime(ROOT,key,scratch,output,env,deadline)
        snapshot = public_snapshot(key,scratch,output)
        write(output/'worker.json',{'python':str(python),'env':env,'snapshot':str(snapshot)})
    elif stage == 'cpu':
        from safeshift.fulltrain.preflight import cpu_native_checks
        spec = read(output/'worker.json')
        lock = read(output/'runtime-lock.json') if key == 'qwen3' else None
        write(output/'cpu.json',cpu_native_checks(key,Path(spec['snapshot']),ROOT,wheel_lock=lock))
    elif stage == 'gpu':
        # Recheck pins in the actual CUDA-visible worker before tensor operations.
        from safeshift.fulltrain.environment import software
        software(key,ROOT,read(output/'runtime-lock.json') if key == 'qwen3' else None)
        import torch
        expected = 2 if key == 'qwen3' else 1
        require(torch.cuda.is_available() and torch.cuda.device_count()==expected,'VISIBLE_GPU_COUNT')
        rows = []
        for i in range(expected):
            require(torch.cuda.get_device_capability(i)==(7,5),'T4_CAPABILITY')
            x = torch.ones((2,2),device=f'cuda:{i}',dtype=torch.float16)
            require((x@x).tolist()==[[2.,2.],[2.,2.]],'FP16_MATMUL')
            torch.cuda.synchronize(i)
            rows.append({'index':i,'name':torch.cuda.get_device_name(i),'memory_bytes':list(torch.cuda.mem_get_info(i))})
        write(output/'gpu.json',{'status':'PINNED_WORKER_TENSOR_PASS','cuda':torch.version.cuda,'gpus':rows,
            'weights_loaded':False,'model_calls':0,'model_fit':'NOT_VERIFIED'})
    else:
        raise ValueError('UNKNOWN_STAGE')


def launch(parent, scratch_parent, ref):
    require(len(ref)==40 and all(c in '0123456789abcdef' for c in ref),'EXACT_SOURCE_COMMIT')
    run_id = 'issue173-software-'+uuid.uuid4().hex
    output, scratch = Path(parent)/run_id, Path(scratch_parent)/run_id
    output.mkdir(parents=True)
    scratch.mkdir(parents=True)
    report = {'run_id':run_id,'source_commit':ref,'source_sha256':digest(contract.source_manifest()),
        'model_calls':0,'weights_loaded':False,'inputs_attached':False,'production_authorized':False,'models':{}}
    write(output/'source-manifest.json',contract.source_manifest())
    deadline = time.monotonic()+3300
    for key in ('qwen3','internvl35','minicpm4'):
        out, temp = output/key,scratch/key
        out.mkdir(); temp.mkdir()
        model = {'status':'BLOCKED','stage':'setup','weights_loaded':False,'model_calls':0}
        report['models'][key] = model
        try:
            env = provision.clean_env(ROOT,temp)
            env['ISSUE173_DEADLINE'] = str(min(deadline,time.monotonic()+(1800 if key=='qwen3' else 600)))
            python = sys.executable
            for stage in ('setup','cpu','gpu'):
                model['stage'] = stage
                if stage != 'setup':
                    spec = read(out/'worker.json')
                    python,env = spec['python'],spec['env']
                    env['CUDA_VISIBLE_DEVICES'] = ('0,1' if key=='qwen3' else '0') if stage=='gpu' else ''
                cap = min(deadline, float(env['ISSUE173_DEADLINE'])) if stage=='setup' else min(deadline,time.monotonic()+180)
                supervision.run([str(python),'-B','-m','scripts.qualify_kaggle173_software','--worker',stage,
                    '--key',key,'--output',str(out),'--scratch',str(temp)],cwd=ROOT,env=env,deadline=cap,
                    log=out/(stage+'-supervisor.log'),receipt=out/(stage+'-supervisor.json'),
                    max_log_bytes=16*2**20,watch_log_root=out)
            model.update(status='CPU_SOFTWARE_AND_PINNED_GPU_TENSOR_PASS',stage='complete')
        except Exception as exc:
            model['error'] = type(exc).__name__+':'+str(exc)
            write(out/'failure.json',{'error':model['error'],'traceback':traceback.format_exc()})
        finally:
            write(out/'result.json',model)
    write(output/'result.json',report)
    export(output,Path(str(output)+'.zip'))
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--worker', choices=('setup','cpu','gpu'))
    p.add_argument('--key',choices=('qwen3','internvl35','minicpm4'))
    p.add_argument('--output',required=True)
    p.add_argument('--scratch',required=True)
    p.add_argument('--source-commit')
    a=p.parse_args()
    if a.worker:
        worker(a.key,a.worker,Path(a.output),Path(a.scratch))
    else:
        print(launch(a.output,a.scratch,a.source_commit))
