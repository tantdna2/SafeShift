"""Read-only saved InternVL diagnosis; export only sanitized structural evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from safeshift.candidates.source import require, ROOT
from safeshift.pilot.contract import parse_label, PROMPT_SHA, GENERATION
from safeshift.pilot.artifacts import sha,read,verify_archive,write
from safeshift.smoke173_history import ARCHIVES


def diagnose(raw,request,native,result,decoded,prompt):
    require(raw['response']==decoded,'INDEPENDENT_TOKENIZER_DECODE_MISMATCH')
    require(raw['generated_ids']==native['generated_ids'] and raw['input_ids']==native['input_ids']==request['input_ids'],
        'CAPTURED_SEQUENCE_IDENTITY')
    require(native['input_prefix_match'] is True and native['returned_ids']==[native['input_ids']+native['generated_ids']],
        'ACTUAL_PREFIX_CONTINUATION')
    require(len(raw['steps'])==len(raw['generated_ids']) and all(s['all_finite'] and
        s['argmax']==token for s,token in zip(raw['steps'],raw['generated_ids'])),'NATIVE_GREEDY_ARGMAX')
    require(request['prompt']==prompt and hashlib.sha256(prompt.encode()).hexdigest()==PROMPT_SHA,'FROZEN_C1')
    require(request['rendered_prompt'].count(prompt)==1 and request['rendered_prompt'].endswith('<|im_start|>assistant\n')
        and not request['rendered_prompt'].endswith('```json\n'),'NO_INJECTED_OUTPUT_FENCE')
    require(all(request['generation'][k]==v for k,v in GENERATION.items()),'FROZEN_GENERATION')
    require(raw['generated_ids'][-1]==request['generation']['eos_token_id'] and len(raw['generated_ids'])<64,'EOS_NOT_TRUNCATION')
    require(parse_label(decoded) is None and result['status']=='INVALID' and result['label'] is None,'STRICT_INVALID_PRESERVED')
    require(decoded.startswith('```json\n') and decoded.endswith('\n```'),'EXPECTED_FENCE_DIAGNOSIS')
    # Inspect the object for diagnosis only, never return a rescued prediction.
    require(type(json.loads(decoded[len('```json\n'):-len('\n```')])) is dict,'INNER_JSON_OBJECT')
    detail=request['input_detail']
    require(detail['pixel_shapes']==[[detail['tiles_including_thumbnail'],3,448,448]]
        and detail['image_tokens']==256*detail['tiles_including_thumbnail']
        and detail['input_length']==len(raw['input_ids']),'SAVED_PROCESSOR_INVARIANTS')
    require(raw['raw_nonfinite'] is False and raw['cpu_tokenizer_replay']['status']=='PASS','SAVED_NUMERIC_DECODE')
    require(raw['actual_logits_processors']==[] and raw['capture_error'] is None,'NO_HIDDEN_PROCESSOR_OR_CAPTURE_ERROR')
    return {'schema':'issue173-internvl-invalid-diagnosis-v1','classification':'INVALID',
        'cause':'MODEL_GENERATED_MARKDOWN_CODE_FENCE_CONTRARY_TO_C1',
        'technical_capture_fault_found':False,'independent_decode':'MATCH','greedy_argmax_every_token':'MATCH',
        'input_prefix_continuation':'MATCH','original_C1_once':'PASS','output_fence_in_template':False,
        'generation':'EXACT_LOCKED_GREEDY_MAX64','eos_present':True,'truncated':False,
        'processor_recorded_invariants':'PASS','generated_tokens':len(raw['generated_ids']),
        'hnlo_status':result['hnlo']['status'],'prediction_rescue_applied':False,'inference_calls':0,
        'limits':'Saved evidence proves generated fence and capture integrity; no new model forward or semantic image-quality claim.'}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--archive',required=True); p.add_argument('--tokenizer',required=True); p.add_argument('--output',required=True)
    a=p.parse_args(); archive=Path(a.archive)
    require(sha(archive)==ARCHIVES[4]==read(Path(str(archive)+'.sha256.json'))['sha256'],'EXACT_V5_ARCHIVE')
    members=verify_archive(archive)
    tokenizer_pin=read(ROOT/'configs/cpu_g2_g3/public_source_lock.json')['internvl35']['files']['tokenizer.json']
    require(sha(a.tokenizer)==tokenizer_pin,'EXACT_PUBLIC_TOKENIZER')
    import tokenizers
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_file(a.tokenizer)
    with zipfile.ZipFile(archive) as bundle:
        r={n:json.loads(bundle.read('internvl35/sample/'+n+'.json')) for n in ('raw','request','native','result')}
        require(r['result']['raw_sha256']==members['internvl35/sample/raw.json'],'RAW_RESULT_CUSTODY')
        decoded=tokenizer.decode(r['raw']['generated_ids'],skip_special_tokens=True)
        value=diagnose(r['raw'],r['request'],r['native'],r['result'],decoded,(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf8'))
        runtime=json.loads(bundle.read('internvl35/loaded-environment.json'))
        require(runtime['native']['implementation_sha256']==read(ROOT/'configs/cpu_g2_g3/implementation_lock.json')['internvl35'],
            'PINNED_NATIVE_IMPLEMENTATIONS')
    value.update(archive_sha256=ARCHIVES[4],executed_source='1e744d991613f48d81ccf0046bc35c5fdab9d1e2',
        tokenizer_sha256=tokenizer_pin,independent_decoder_version=tokenizers.__version__,
        native_implementation_hashes='MATCH_LOCK',raw_exported=False)
    write(Path(a.output),value)
    print(json.dumps(value,indent=2))


if __name__=='__main__': main()
