"""CPU-only grammar qualification with receipts; no model/data/GPU entrypoint.

Default: stdlib synthetic tests. Optional native tokenizer/processor check uses
pinned local public tokenizer files and handwritten full-vocabulary logits.
--fetch-public-tokenizer downloads only seven named hash-locked text files.
"""
import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
FILES = ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
         "added_tokens.json", "vocab.json", "merges.txt", "generation_config.json")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf8', newline='\n') as out:
        json.dump(value, out, indent=2, sort_keys=True, allow_nan=False)
        out.write('\n'); out.flush(); os.fsync(out.fileno())


def native_check(source, output, fetch=False):
    from safeshift.internvl_grammar import (InternVLGrammarV2, validate_trace, mask_logits,
                                          BINDING_KEYS, POLICY, PROCESSOR, VERSION)
    from safeshift.pilot.contract import digest
    lock = json.loads((ROOT / 'configs/cpu_g2_g3/public_source_lock.json').read_text())['internvl35']
    if fetch:
        source.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = source / name
        if fetch and not target.exists():
            url = lock['source_url_pattern'].format(id=lock['id'], revision=lock['revision'], filename=name)
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read(16 * 1024 * 1024 + 1)
            if len(content) > 16 * 1024 * 1024 or hashlib.sha256(content).hexdigest() != lock['files'][name]:
                raise ValueError('PUBLIC_TOKENIZER_SIZE_OR_HASH')
            with target.open('xb') as stream: stream.write(content)
        if sha(target) != lock['files'][name]:
            raise ValueError('PUBLIC_TOKENIZER_HASH_MISMATCH:' + name)

    import torch
    import transformers
    import tokenizers
    from transformers import Qwen2TokenizerFast
    from transformers.generation.logits_process import PrefixConstrainedLogitsProcessor
    if transformers.__version__ != '4.55.4' or tokenizers.__version__ != '0.21.4':
        raise ValueError('PINNED_TOKENIZER_PROCESSOR_VERSIONS_REQUIRED')
    torch.set_num_threads(1)
    tokenizer = Qwen2TokenizerFast.from_pretrained(str(source), local_files_only=True)
    independent = tokenizers.Tokenizer.from_file(str(source / 'tokenizer.json'))
    prompt = '<|im_start|>user\nSYNTHETIC CPU TOKEN BOUNDARY ONLY<|im_end|>\n<|im_start|>assistant\n'
    inputs = tokenizer.encode(prompt, add_special_tokens=False)
    eos = json.loads((source / 'generation_config.json').read_text())['eos_token_id']
    grammar = InternVLGrammarV2(tokenizer, eos, inputs)
    old = json.loads((ROOT / 'docs/research/evidence/issue173/diagnostics/issue173-diag-intern-grammar-v2.json').read_text())
    if grammar.receipt()['paths_sha256'] != old['calls'][0]['grammar']['paths_sha256']:
        raise ValueError('PR175_NATIVE_PATH_DIGEST_CHANGED')
    processor = PrefixConstrainedLogitsProcessor(grammar.callback(), num_beams=1)
    cases = []
    for label_index in range(4):
        for forced in (False, True):
            ids = grammar.paths[label_index] + (grammar.eos[0],)
            steps = []
            for index, chosen in enumerate(ids):
                # Scripted scores, no neural forward or weights. Run the actual HF
                # processor and torch argmax, compare with the stdlib mask oracle.
                scores = torch.full((1, len(tokenizer)), -7.0, dtype=torch.float32, device='cpu')
                scores[0, chosen] = 2.0
                if forced and index == 0:
                    scores[0, tokenizer.encode('`', add_special_tokens=False)[0]] = 9.0
                prefix = list(grammar.input_ids + ids[:index])
                masked = processor(torch.tensor([prefix], device='cpu'), scores)
                actual = [None if z == -float('inf') else z for z in masked[0].tolist()]
                raw = scores[0].tolist()
                if actual != mask_logits(grammar, ids[:index], raw) or int(masked.argmax()) != chosen:
                    raise ValueError('NATIVE_CPU_MASK_OR_ARGMAX_MISMATCH')
                steps.append({'step': index, 'prefix_ids': prefix, 'raw_logits': raw, 'masked_logits': actual})
            binding = {key: digest('SYNTHETIC_' + key) for key in BINDING_KEYS}
            binding.update(source_sha256=sha(ROOT / 'safeshift/internvl_grammar.py'),
                           tokenizer_sha256=sha(source / 'tokenizer.json'),
                           model_revision_sha256=digest(lock['revision']), prompt_sha256=digest(prompt),
                           generation_sha256=digest(POLICY))
            trace = {'schema': VERSION + '-trace', 'binding': binding, 'grammar': grammar.receipt(),
                     'policy': dict(POLICY), 'actual_logits_processors': [PROCESSOR],
                     'capture_origin': 'scripted_before_processors', 'evidence_kind': 'SYNTHETIC', 'capture_error': None,
                     'input_ids': inputs, 'generated_ids': list(ids), 'steps': steps,
                     'response': tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)}
            # This is synthetic evidence; preserve it before verification and do
            # not mistake its declared capture boundary for a real forward hook.
            path = output / f'synthetic-{label_index}-{int(forced)}.json'
            save(path, trace)
            sealed = sha(path)
            verified = validate_trace(grammar, independent, json.loads(path.read_text()), binding)
            if sha(path) != sealed:
                raise ValueError('SYNTHETIC_TRACE_MUTATED')
            cases.append({'label_index': label_index, 'forced': forced,
                          'raw_fixture_sha256': sealed, 'verification': verified})
    # Actual native tie rule, at the proven common decision boundary.
    prefix = list(grammar.input_ids + grammar.paths[0][:grammar.decision_step])
    tied = processor(torch.tensor([prefix]), torch.zeros((1, len(tokenizer))))
    if int(tied.argmax()) != min(grammar.decision_tokens):
        raise ValueError('NATIVE_TIE_RULE')
    return {'status': 'CPU_TOKENIZER_AND_PROCESSOR_PASS', 'model': lock['id'], 'revision': lock['revision'],
            'public_files': {n: sha(source / n) for n in FILES}, 'grammar': grammar.receipt(),
            'native_processor_source_sha256': hashlib.sha256(inspect.getsource(PrefixConstrainedLogitsProcessor).encode()).hexdigest(),
            'dependencies': {n: importlib.metadata.version(n) for n in
                             ('torch', 'transformers', 'tokenizers', 'numpy', 'huggingface-hub',
                              'regex', 'safetensors', 'packaging', 'filelock', 'typing-extensions',
                              'tqdm', 'pyyaml', 'requests', 'fsspec', 'certifi', 'charset-normalizer',
                              'idna', 'urllib3', 'colorama')},
            'cases': cases, 'native_tie_rule': 'PASS', 'weights_loaded': False,
            'model_calls': 0, 'input_kind': 'SYNTHETIC_TEXT_ONLY_NO_IMAGE_PROCESSOR',
            'live_kaggle_v2': 'NOT_RUN', 'native_forward_capture': 'NOT_VERIFIED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-source', type=Path)
    parser.add_argument('--fetch-public-tokenizer', action='store_true')
    parser.add_argument('--packages', type=Path, help='Optional isolated dependency target')
    args = parser.parse_args()
    if args.fetch_public_tokenizer and not args.native_source:
        parser.error('--fetch-public-tokenizer requires --native-source')
    os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    for name in tuple(os.environ):
        if name.startswith('SAFESHIFT_'): del os.environ[name]
    if args.packages: sys.path.insert(0, str(args.packages.resolve()))
    sys.path.insert(0, str(ROOT / 'tests'))
    args.output.mkdir(parents=True, exist_ok=False)
    names = ['test_internvl_grammar', 'test_issue173_format_decision', 'test_pilot.HNLOTests',
             'test_kaggle173_diagnostic']
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    with (args.output / 'unittest.log').open('x', encoding='utf8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    paths = ['safeshift/internvl_grammar.py', 'tests/test_internvl_grammar.py',
             'configs/grammar/internvl35_v2.json', 'tests/test_issue173_format_decision.py',
             'tests/test_pilot.py', 'tests/test_kaggle173_diagnostic.py',
             'scripts/qualify_internvl_grammar.py', 'safeshift/diagnostic173_grammar.py',
             'safeshift/pilot/hnlo.py', 'safeshift/pilot/contract.py',
             'configs/pilot/classification_c1.txt', 'configs/cpu_g2_g3/public_source_lock.json',
             'configs/issue173/diagnostic_custody.json',
             'docs/research/evidence/issue173/diagnostics/issue173-diag-intern-grammar-v2.json']
    receipt = {'schema': 'internvl35-grammar-v2-cpu-qualification',
               'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'source_manifest': {p: sha(ROOT / p) for p in paths},
               'python': sys.version, 'platform': platform.platform(), 'randomness': 'NONE',
               'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
               'skipped': len(result.skipped), 'log_sha256': sha(args.output / 'unittest.log'),
               'test_suites': names, 'native_cpu': 'NOT_REQUESTED', 'gpu_calls': 0,
               'status': 'PASS' if result.wasSuccessful() else 'FAIL', 'science': 'PROPOSED_LABEL_ONLY_HNLO_NA'}
    receipt['command'] = ['python', '-B', '-m', 'scripts.qualify_internvl_grammar', '--output', '<new-output>']
    if args.packages: receipt['command'] += ['--packages', '<isolated-dependencies>']
    if args.native_source: receipt['command'] += ['--native-source', '<hash-locked-public-tokenizer>']
    if args.fetch_public_tokenizer: receipt['command'].append('--fetch-public-tokenizer')
    try:
        if result.wasSuccessful() and args.native_source:
            receipt['native_cpu'] = native_check(args.native_source, args.output, args.fetch_public_tokenizer)
    except Exception as error:
        receipt.update(status='FAIL', native_cpu={'status': 'FAIL', 'error_type': type(error).__name__,
                                                'reason': str(error)[:300]})
        raise
    finally:
        save(args.output / 'receipt.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('status', 'tests_run', 'failures', 'errors', 'skipped')}))
    return 0 if receipt['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
