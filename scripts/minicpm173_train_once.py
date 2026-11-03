"""Executable Mini-only ordinal0 route. External exact review/remote permits required."""
import argparse
import json
from pathlib import Path
import sys
import threading
import time

from safeshift import minicpm173_once as control
from safeshift.candidates.source import ROOT, require, verify_snapshot
from safeshift.candidates.train_inputs import checkpoint
from safeshift.pilot.artifacts import read, write, sha, export
from safeshift.pilot.contract import parse_label, digest
from safeshift.fulltrain import provision, supervision, environment
from scripts.minicpm173_train_review import bind_original, diagnostic_history
from scripts.minicpm173_preflight import memory, ram_gate, advise_owned_runtime, POLICY
from scripts.smoke_kaggle173 import driver_check, bind_cuda_driver, supervisor_log


def runtime_sources():
    from safeshift.fulltrain.contract import sources
    return sorted(set(sources() + ['safeshift/verification173.py', 'safeshift/smoke173_history.py',
        'safeshift/minicpm173_once.py', 'scripts/minicpm173_train_review.py',
        'scripts/minicpm173_train_once.py', 'scripts/minicpm173_preflight.py',
        'scripts/smoke_kaggle173.py', 'scripts/verify_kaggle173_inputs.py',
        'configs/issue173/real_smoke.json', 'configs/issue173/diagnostic_custody.json']))


def check_source(spec):
    require(set(spec['manifest']) == set(runtime_sources()), 'COMPLETE_MINI_SOURCE_MANIFEST')
    control.source_check(spec)


def execute_native(inputs, out, ctx, parent_nonce):
    """Also fenced when called directly; no persisted permit is reusable."""
    history, row = bind_original(inputs)
    diagnostic_history(inputs)
    marker, source, weights = checkpoint(inputs, 'minicpm4')
    verify_snapshot(source, 'minicpm4')
    permission = control.permit(ctx, 'load', parent_nonce)
    write(out / 'load-reservation.json', permission)
    before = memory()
    write(out / 'admitted-load-memory.json', before)
    ram_gate(before)
    from safeshift.candidates.train_runtime import memory as gpu_memory
    gpu = gpu_memory(True)
    write(out / 'admitted-load-vram.json', gpu)
    require(gpu['gpu0_free'] >= POLICY['free_gpu0_runtime_mib'] * 2**20, 'PRELOAD_VRAM_CHANGED')
    from safeshift.candidates import minicpm_resampler_fp32 as numerical
    # Unchanged loader verifies every actual weight/index SHA before tensors load.
    prompt = (ROOT / 'configs/pilot/classification_c1.txt').read_text(encoding='utf8')
    model = numerical.backend('minicpm4', source, weights, prompt, device='cuda:0')
    write(out / 'loaded.json', model.environment)
    write(out / 'after-load-memory.json', memory())
    require(sha(row['image']) == row['image_sha256'], 'ORIGINAL_IMAGE_PRECALL_HASH')
    sample = out / 'sample'
    sample.mkdir(exist_ok=False)
    call = control.permit(ctx, 'call', permission['nonce'])
    write(sample / 'reservation.json', call)
    # Exact image bound again after waiting; no fallback/alternate image.
    require(sha(row['image']) == row['image_sha256'], 'ORIGINAL_IMAGE_PRECALL_HASH')
    raw = model.generate(row['image'], sample)
    raw['smoke_identity'] = {k: row[k] for k in ('ordinal', 'sample_id', 'image_sha256')}
    raw['smoke_identity'].update(run_id=control.IDENTITY, model_key='minicpm4', series_id=control.IDENTITY)
    checksum = write(sample / 'raw.json', raw)
    require((sample / 'native_call.json').is_file(), 'NATIVE_CALL_MARKER_REQUIRED')
    require(sha(sample / 'raw.json') == checksum, 'RAW_REREAD_HASH')
    saved = read(sample / 'raw.json')
    require(saved['cpu_tokenizer_replay']['status'] == 'PASS' and not saved['raw_nonfinite'],
            'NATIVE_DECODE_FINITE_PROOF')
    label = parse_label(saved['response'])
    write(sample / 'result.json', {'raw_sha256': checksum, 'status': 'SUCCESS' if label else 'INVALID',
        'label': label, 'hnlo': None, 'hnlo_status': 'LABEL_ONLY_OWNER_DECISION',
        'scientific_results_excluded': True})


def worker(stage, request_path, out, scratch):
    require(stage in ('setup', 'native'), 'MINI_STAGE_ONLY')
    request = read(request_path)
    check_source(request['spec'])
    ctx = control.context(request['spec'])
    require(request['binding'] == ctx['binding'], 'WORKER_RELEASE_BINDING')
    launch_permit = control.remote_record('launch')
    require(launch_permit == request['launch_permit'], 'WORKER_LAUNCH_PERMIT')
    inputs = Path('/kaggle/input')  # Not a caller-selectable dataset/model.
    if stage == 'setup':
        from safeshift.candidates.train_runtime import prepare_runtime
        env = provision.clean_env(ROOT, scratch)
        python, env = prepare_runtime(ROOT, 'minicpm4', scratch, out, env, time.monotonic() + 600)
        write(out / 'runtime.json', {'python': str(python), 'env': env})
        return
    bind_cuda_driver(out)
    write(out / 'software.json', environment.software('minicpm4'))
    write(out / 'hardware.json', driver_check('minicpm4', POLICY, out, 'worker'))
    write(out / 'cuda.json', environment.cuda('minicpm4', POLICY))
    write(out / 'resources.json', environment.resources('minicpm4', POLICY, scratch, out))
    before = memory()
    write(out / 'before-load-memory.json', before)
    ram_gate(before)
    try:
        execute_native(inputs, out, ctx, launch_permit['nonce'])
    finally:
        from safeshift.candidates.train_runtime import memory as gpu_memory
        try:
            write(out / 'final-gpu-memory.json', gpu_memory(False))
        except Exception as failure:
            write(out / 'final-gpu-memory-error.json', {'type': type(failure).__name__})


def relay(path, stop):
    """Forward only public handshake lines from supervised child to Kaggle log."""
    position, pending = 0, ''
    while not stop.wait(.1):
        if not path.is_file():
            continue
        with path.open('r', encoding='utf8', errors='replace') as stream:
            stream.seek(position)
            pending += stream.read(2**20)
            position = stream.tell()
        lines = pending.split('\n')
        pending = lines.pop()
        for line in lines:
            if line.startswith(control.PREFIX) and len(line) < 2048:
                print(line, flush=True)
        if len(pending) > 2**20:
            pending = ''  # Logs remain intact; an overlong line cannot be a challenge.


def summarize(out, error=None):
    result_path = out / 'sample/result.json'
    calls = int((out / 'sample/native_call.json').exists())
    reservations = int((out / 'sample/reservation.json').exists())
    status = read(result_path)['status'] if result_path.exists() and error is None else 'TECHNICAL_ERROR'
    return {'identity': control.IDENTITY, 'status': status, 'error': error,
        'load_reservations': int((out / 'load-reservation.json').exists()),
        'weights_loaded': (out / 'loaded.json').exists(), 'call_reservations': reservations,
        'native_call_markers': calls,
        'original_smoke_counts': {'qwen3': 1, 'internvl35': 1, 'minicpm4': calls},
        'consumption': 'COMPLETED' if status in ('SUCCESS', 'INVALID') else
            'UNKNOWN_NO_RETRY' if reservations or calls else 'NO_CALL_OBSERVED_NO_AUTO_RETRY',
        'diagnostic_calls_separate': 5, 'scientific_results_excluded': True,
        'automatic_retry': False, 'limits': control.LIMITS}


def launch(spec, output=Path('/kaggle/working'), scratch_parent=Path('/kaggle/temp')):
    check_source(spec)
    ctx = control.context(spec)  # Missing approval/submission stops before I/O.
    out = Path(output) / control.IDENTITY
    out.mkdir(exist_ok=False)
    scratch = Path(scratch_parent) / ('issue173-minicpm-ram-' + control.IDENTITY)
    error = None
    deadline = time.monotonic() + 1750
    write(out / 'source.json', spec)
    write(out / 'release.json', ctx)
    try:
        permission = control.permit(ctx, 'launch', '')
        scratch.mkdir(exist_ok=False)
        history, row = bind_original('/kaggle/input')
        diagnostics = diagnostic_history('/kaggle/input')
        write(out / 'history.json', history)
        write(out / 'diagnostic-history.json', diagnostics)
        write(out / 'original-image.json', row)
        write(out / 'initial-memory.json', memory())
        write(out / 'initial-resources.json', environment.resources('minicpm4', POLICY, scratch, out))
        write(out / 'budget.json', {'limits': control.LIMITS, 'policy': POLICY})
        write(out / 'request.json', {'spec': spec, 'binding': ctx['binding'], 'launch_permit': permission})
        env = provision.clean_env(ROOT, scratch)
        for stage in ('setup', 'native'):
            python = sys.executable
            if stage == 'native':
                write(out / 'cache-advice.json', advise_owned_runtime(scratch))
                runtime = read(out / 'runtime.json')
                python, env = runtime['python'], runtime['env']
                env['CUDA_VISIBLE_DEVICES'] = '0'
            log = supervisor_log(out, stage)
            stop = threading.Event()
            thread = threading.Thread(target=relay, args=(log, stop), daemon=True)
            thread.start()
            try:
                supervision.run([str(python), '-B', '-m', 'scripts.minicpm173_train_once',
                    '--worker', stage, '--request', str(out / 'request.json'), '--output', str(out),
                    '--scratch', str(scratch)], cwd=ROOT, env=env,
                    deadline=min(deadline, time.monotonic() + (600 if stage == 'setup' else 900)),
                    log=log, receipt=out / (stage + '-supervisor.json'),
                    max_log_bytes=16 * 2**20, watch_log_root=out)
            finally:
                stop.set()
                thread.join(timeout=2)
        require((out / 'sample/result.json').is_file(), 'MISSING_NATIVE_RESULT_NO_RETRY')
    except BaseException as failure:
        error = {'type': type(failure).__name__, 'message': str(failure)[:2048]}
    finally:
        # Any missing/partial marker is uncertainty, never permission to repeat.
        result = summarize(out, error)
        write(out / 'summary.json', result)
        try:
            write(out / 'final-memory.json', memory())
        except Exception as failure:
            write(out / 'final-memory-error.json', {'type': type(failure).__name__})
        checksum = export(out, Path(str(out) + '.zip'))
    return {**result, 'archive_sha256': checksum}


def main(argv=None):
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--spec')
    modes.add_argument('--worker', choices=('setup', 'native'))
    parser.add_argument('--request')
    parser.add_argument('--output', default='/kaggle/working')
    parser.add_argument('--scratch', default='/kaggle/temp')
    args = parser.parse_args(argv)
    if args.worker:
        require(args.request is not None, 'WORKER_REQUEST_REQUIRED')
        worker(args.worker, args.request, Path(args.output), Path(args.scratch))
        return 0
    result = launch(read(args.spec), Path(args.output), Path(args.scratch))
    print(json.dumps(result), flush=True)
    return 0 if result['status'] in ('SUCCESS', 'INVALID') else 1


if __name__ == '__main__':
    raise SystemExit(main())
