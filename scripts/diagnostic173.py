"""Bounded synthetic-only diagnostics; never an original TRAIN smoke dispatcher."""
import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

from safeshift.candidates.source import ROOT, require, verify_snapshot
from safeshift.candidates.train_inputs import checkpoint
from safeshift.candidates.train_runtime import prepare_runtime
from safeshift.fulltrain import provision, supervision, environment
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import parse_label, PROMPT_SHA
from safeshift.smoke173_history import inspect_history
from scripts.minicpm173_preflight import memory, ram_gate, advise_owned_runtime, paths_from_mounts, POLICY
from scripts.smoke_kaggle173 import driver_check, bind_cuda_driver, supervisor_log

DIRECTIVE='https://github.com/tantdna2/SafeShift/pull/175#issuecomment-6592812806'
PLANS={
    'issue173-diag-mini-synthetic-v1': {'key':'minicpm4','variants':['frozen-c1']},
    'issue173-diag-intern-format-v1': {'key':'internvl35','variants':['frozen-c1','reminder-v1','prefill-v1']},
}
REMINDER='\nFormatting requirement: Begin your reply immediately with the character { and end with }. Write the JSON object directly, without Markdown or backticks.'
PREFIX='{"safety_level":"'


def admit(identity):
    require(identity in PLANS,'DECLARED_SYNTHETIC_DIAGNOSTIC_ONLY')
    return PLANS[identity]


def source_check(manifest):
    require(bool(manifest),'SOURCE_MANIFEST_REQUIRED')
    for name,digest in manifest.items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts and ':' not in name,'SOURCE_PATH')
        require(sha(ROOT/name)==digest,'DIAGNOSTIC_SOURCE_DRIFT:'+name)


def variant_inputs(original,variant):
    """Scoped diagnostic adapter only. Official adapter and template bytes unchanged."""
    require(variant in ('reminder-v1','prefill-v1'),'PROPOSED_VARIANT')
    def prepare(processor,key,prompt,image):
        require(key=='internvl35' and hashlib.sha256(prompt.encode()).hexdigest()==PROMPT_SHA,'INTERNVL_FROZEN_C1_BASE')
        baseline,base_inputs=original(processor,key,prompt,image)
        if variant=='reminder-v1':
            messages=[{'role':'user','content':[{'type':'image'},{'type':'text','text':prompt+REMINDER}]}]
            rendered=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
            require(rendered.replace(REMINDER,'')==baseline,'ONLY_DECLARED_REMINDER_CHANGED')
        else:
            messages=[{'role':'user','content':[{'type':'image'},{'type':'text','text':prompt}]},
                      {'role':'assistant','content':[{'type':'text','text':PREFIX}]}]
            rendered=processor.apply_chat_template(messages,tokenize=False,add_generation_prompt=False,continue_final_message=True)
            require(rendered==baseline+PREFIX,'EXACT_ASSISTANT_PREFILL_RENDERING')
        values=processor(text=rendered,images=image,return_tensors='pt')
        # Identical image preprocessing, not a resize/normalization workaround.
        import torch
        require(torch.equal(base_inputs['pixel_values'],values['pixel_values']),'DIAGNOSTIC_PIXEL_DRIFT')
        return rendered,values
    return prepare


def evaluate(raw,variant):
    """Parse exact native bytes first; never turn a fenced answer into SUCCESS."""
    native=parse_label(raw['response'])
    assembled=PREFIX+raw['response'] if variant=='prefill-v1' else raw['response']
    return {'native_status':'SUCCESS' if native else 'INVALID',
        'assistant_message_status':'SUCCESS' if parse_label(assembled) else 'INVALID',
        'native_response_sha256':hashlib.sha256(raw['response'].encode()).hexdigest(),
        'assistant_prefix':PREFIX if variant=='prefill-v1' else '',
        'scientific_status':'FROZEN_CONFIGURATION_SYNTHETIC_ONLY' if variant=='frozen-c1' else 'PROPOSED_NON_EQUIVALENT',
        'hnlo':'NOT_COMPUTED_DIAGNOSTIC_LABEL_ONLY','posthoc_cleanup':False}


def worker(stage,request_path,out,scratch):
    request=read(request_path); plan=admit(request['identity']); key=plan['key']
    require(stage in ('setup','native'),'DECLARED_STAGE')
    source_check(request['source_manifest'])
    history=inspect_history(paths_from_mounts('/kaggle/input'))
    require(history['consumed']=={'qwen3':1,'internvl35':1,'minicpm4':0},'ORIGINAL_HISTORY')
    # Re-discover, never accept a caller-supplied model, image or dataset path.
    marker,source,weights=checkpoint('/kaggle/input',key)
    verify_snapshot(source,key)
    if stage=='setup':
        env=provision.clean_env(ROOT,scratch)
        python,env=prepare_runtime(ROOT,key,scratch,out,env,time.monotonic()+600)
        write(out/'runtime.json',{'python':str(python),'env':env})
        return
    write(out/'native-before-import-memory.json',memory()); bind_cuda_driver(out)
    write(out/'software.json',environment.software(key))
    write(out/'hardware.json',driver_check(key,POLICY,out,'worker'))
    write(out/'cuda.json',environment.cuda(key,POLICY))
    write(out/'storage-and-ram.json',environment.resources(key,POLICY,scratch,out))
    from safeshift.candidates import backend as adapter
    from safeshift.candidates.train_runtime import memory as gpu_memory
    from safeshift.candidates import minicpm_resampler_fp32 as numerical
    from PIL import Image
    before=memory(); write(out/'before-load-memory.json',before); ram_gate(before)
    write(out/'before-load-vram.json',gpu_memory(True))
    prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
    write(out/'load-reservation.json',{'loads':1,'identity':request['identity'],'key':key})
    backend=(numerical.backend(key,source,weights,prompt,device='cuda:0') if key=='minicpm4'
             else adapter.CandidateBackend(key,source,weights,prompt,device='cuda:0'))
    write(out/'loaded.json',backend.environment)
    write(out/'after-load-memory.json',memory()); write(out/'after-load-vram.json',gpu_memory(False))
    image_path=out/'synthetic-gray.png'
    with Image.new('RGB',(448,448),(128,128,128)) as image: image.save(image_path)
    image_hash=sha(image_path)
    write(out/'input.json',{'scope':'SYNTHETIC_ONLY_NO_GROUND_TRUTH','recipe':'PIL RGB 448x448 constant (128,128,128)',
        'sha256':image_hash,'model_revision':backend.environment['model'],'source_commit':request['source_commit']})
    results=[]
    for variant in plan['variants']:
        require(sha(image_path)==image_hash,'SYNTHETIC_INPUT_CHANGED')
        sample=out/'calls'/variant; sample.mkdir(parents=True,exist_ok=False)
        write(sample/'reservation.json',{'identity':request['identity'],'variant':variant,'max_calls':1,
            'input_sha256':image_hash,'source_commit':request['source_commit'],'directive':DIRECTIVE})
        context=(nullcontext() if variant=='frozen-c1' else
            patch.object(adapter,'prepare_inputs',variant_inputs(adapter.prepare_inputs,variant)))
        with context: raw=backend.generate(image_path,sample)
        # The raw response and tokens are durable before parsing/format evaluation.
        write(sample/'raw.json',raw)
        result=evaluate(raw,variant); result.update(variant=variant,raw_sha256=sha(sample/'raw.json'))
        write(sample/'result.json',result); results.append(result)
        write(sample/'memory.json',memory()); write(sample/'vram.json',gpu_memory(False))
        require(not raw['raw_nonfinite'],'NONFINITE_DIAGNOSTIC_STOP')
        if result['native_status']=='SUCCESS' and (key=='minicpm4' or variant!='frozen-c1'): break
    write(out/'native-result.json',{'weights_loaded':True,'calls':len(results),'results':results,
        'status':'NATIVE_FORMAT_PASS' if any(r['native_status']=='SUCCESS' for r in results) else 'NATIVE_FORMAT_INVALID',
        'original_smoke_calls_added':0,'scientific_adoption':False})


def launch(identity,inputs,output,scratch_parent,ref,manifest):
    plan=admit(identity); source_check(manifest)
    require(len(ref)==40 and all(c in '0123456789abcdef' for c in ref),'EXACT_SOURCE_COMMIT')
    history=inspect_history(paths_from_mounts(inputs))
    out=Path(output)/identity; out.mkdir(exist_ok=False)
    # The existing advice implementation can only touch this newly owned tree.
    scratch=Path(scratch_parent)/('issue173-minicpm-ram-'+identity); scratch.mkdir(exist_ok=False)
    request={'identity':identity,'source_commit':ref,'source_manifest':manifest,'scope':'SYNTHETIC_ONLY'}
    write(out/'request.json',request); write(out/'history.json',history)
    write(out/'budget.json',{'max_loads':1,'max_calls':len(plan['variants']),'job_seconds':1800,
        'visible_t4':1,'allocated_t4':2,'ram_floor_bytes':16384*2**20,'policy':POLICY,
        'original_train_calls':0,'directive':DIRECTIVE})
    samples=[]; stop=threading.Event()
    def monitor():
        while not stop.wait(.5):
            if len(samples)<3600: samples.append(memory())
    thread=threading.Thread(target=monitor,daemon=True); thread.start()
    result={'identity':identity,'status':'BLOCKED','source_commit':ref,'original_smoke_calls_added':0}
    deadline=time.monotonic()+1650
    try:
        write(out/'startup-memory.json',memory())
        write(out/'startup-resources.json',environment.resources(plan['key'],POLICY,scratch,out))
        env=provision.clean_env(ROOT,scratch)
        for stage in ('setup','native'):
            python=sys.executable
            if stage=='native':
                write(out/'before-advice-memory.json',memory())
                write(out/'cache-advice.json',advise_owned_runtime(scratch))
                write(out/'after-advice-memory.json',memory())
                runtime=read(out/'runtime.json'); python,env=runtime['python'],runtime['env']; env['CUDA_VISIBLE_DEVICES']='0'
            command=[str(python),'-B','-m','scripts.diagnostic173','--worker',stage,'--request',str(out/'request.json'),
                '--output',str(out),'--scratch',str(scratch)]
            supervision.run(command,cwd=ROOT,env=env,deadline=min(deadline,time.monotonic()+(600 if stage=='setup' else 900)),
                log=supervisor_log(out,stage),receipt=out/(stage+'-supervisor.json'),max_log_bytes=16*2**20,watch_log_root=out)
            write(out/(stage+'-after-exit-memory.json'),memory())
        result.update(read(out/'native-result.json'))
    except Exception as error:
        import traceback
        write(out/'failure.json',{'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()})
    finally:
        stop.set(); thread.join(timeout=2)
        result.update(load_reservations=int((out/'load-reservation.json').exists()),weights_loaded=(out/'loaded.json').exists(),
            call_reservations=len(list((out/'calls').glob('*/reservation.json'))),native_call_markers=len(list((out/'calls').glob('*/native_call.json'))))
        write(out/'memory-timeline.json',samples); write(out/'final-memory.json',memory())
        write(out/'result.json',result); export(out,Path(str(out)+'.zip'))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--worker',required=True,choices=('setup','native'))
    p.add_argument('--request',required=True); p.add_argument('--output',required=True); p.add_argument('--scratch',required=True)
    a=p.parse_args(); worker(a.worker,a.request,Path(a.output),Path(a.scratch))
