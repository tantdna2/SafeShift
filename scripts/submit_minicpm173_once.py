"""Local official Kaggle submitter + create-only remote coordinator. Never retry."""
import argparse
import hashlib
from contextlib import contextmanager
import json
from pathlib import Path
import queue
import subprocess
import threading
import time
import traceback
from unittest.mock import patch

from safeshift import minicpm173_once as control
from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, verify_archive, safe
from safeshift.pilot.contract import digest
from safeshift.smoke173_history import inspect_history
from scripts.minicpm173_preflight import paths_from_mounts
from scripts.minicpm173_train_review import diagnostic_history


def kernel_sources():
    lock = read(ROOT / 'configs/issue173/diagnostic_custody.json')
    return ['nguynanhtn/safeshift-prepare-minicpm4', 'nguynanhtn/safeshift-issue173-existing-bytes'] + [
        'nguynanhtn/safeshift-issue173-native-smoke' + (f'-v{i}' if i > 1 else '') for i in range(1, 6)
    ] + ['nguynanhtn/' + row['kernel_slug'] for row in lock['attempts']]


def authenticated_github_get(path, *, missing=False):
    """Local gh session only. No token retrieval, notebook secret or read retry."""
    require(path.startswith('/') and not path.startswith('//'), 'GITHUB_RELATIVE_API_PATH')
    result = subprocess.run(['gh', 'api', '--include', 'repos/' + control.REPO + path],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    header, separator, body = result.stdout.replace('\r\n', '\n').partition('\n\n')
    require(separator and header.startswith('HTTP/'), 'AUTHENTICATED_GITHUB_RESPONSE_UNKNOWN')
    status = int(header.splitlines()[0].split()[1])
    if status == 404 and missing:
        return None
    require(status == 200 and result.returncode == 0, 'AUTHENTICATED_GITHUB_READ_HTTP_' + str(status))
    require(len(body.encode()) <= 2**20, 'REMOTE_RESPONSE_BOUND')
    return json.loads(body)


def get_kernel(api, ref):
    from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest
    request = ApiGetKernelRequest()
    request.user_name, request.kernel_slug = ref.split('/')
    with api.build_kaggle_client() as client:
        return client.kernels.kernels_api_client.get_kernel(request)


def inventory(api):
    """Read-only exact job/version inventory; no new experiment/preflight."""
    # Kaggle GetKernel deliberately returns 403 for an absent private slug.
    # Prove absence using the authenticated owner's fully paginated inventory;
    # a 403 by itself is never evidence of absence.
    owned, tokens, token = set(), set(), None
    for number in range(1, 17):
        page = api.kernels_list_with_response(mine=True, page_size=100,
                                             page_token=token, page=None if token else number)
        refs = [row.ref for row in page.kernels]
        require(len(refs) == len(set(refs)) and not owned.intersection(refs)
                and all(ref.startswith('nguynanhtn/') for ref in refs), 'OWNED_INVENTORY_DUPLICATE_OR_ACCOUNT')
        owned.update(refs)
        token = page.next_page_token
        if not token and len(refs) < 100:
            break
        if token:
            require(token not in tokens, 'INVENTORY_REPEATED_PAGE')
            tokens.add(token)
    else:
        raise ValueError('OWNED_INVENTORY_BOUND_INCOMPLETE')
    require(set(kernel_sources()) <= owned, 'OWNED_INVENTORY_MISSING_KNOWN_PRIVATE_JOBS')
    require(control.JOB not in owned, 'TARGET_ALREADY_EXISTS_NO_RESUBMISSION')
    require(not any('nguynanhtn/safeshift-issue173-minicpm-original-train-once-v' + str(n) in owned
                    for n in range(control.JOB_NUMBER, 6)), 'CAMPAIGN_LATER_JOB_EXISTS')
    try:
        get_kernel(api, control.JOB)
    except Exception as failure:
        require(getattr(getattr(failure, 'response', None), 'status_code', None) in (403, 404),
                'TARGET_EXISTENCE_UNKNOWN_NO_SUBMISSION')
    else:
        raise ValueError('TARGET_ALREADY_EXISTS_NO_RESUBMISSION')
    rows = []
    for ref in kernel_sources():
        value = get_kernel(api, ref)
        require(value.metadata.current_version_number == 1
                and str(api.kernels_status(ref).status).endswith('COMPLETE'), 'PINNED_INPUT_VERSION_NOT_COMPLETE')
        rows.append({'ref': ref, 'kernel_id': value.metadata.id, 'version': 1, 'status': 'COMPLETE'})
    quota = api.quota_view().gpu_quota
    q = {name: int(getattr(quota, field).total_seconds()) for name, field in (
        ('used_seconds', 'time_used'), ('reserved_seconds', 'time_reserved'), ('total_seconds', 'total_time_allowed'))}
    require(q['reserved_seconds'] == 0 and q['total_seconds'] - q['used_seconds'] >= 3600,
            'QUOTA_OR_CONCURRENT_GPU_JOB')
    return {'target': control.JOB, 'target_exists': False, 'inputs': rows, 'quota': q,
            'owned_inventory_count': len(owned), 'owned_inventory_sha256': digest(sorted(owned)),
            'owned_inventory_complete': True,
            'observed_unix': int(time.time())}


@contextmanager
def bounded_http():
    """Official SDK transport, zero automatic retry, finite network waits."""
    import requests
    original = requests.Session.send
    def send(session, request, **kwargs):
        require(all(a.max_retries.total == 0 for a in session.adapters.values()), 'SDK_RETRIES_FORBIDDEN')
        # Setup can be silent for minutes. Only the background SSE reader gets
        # a finite idle read timeout; coordinator wall deadline still caps work.
        kwargs['timeout'] = (10, 90 if '/kernels/logs/stream/' in request.url else 30)
        kwargs['allow_redirects'] = False
        response = original(session, request, **kwargs)
        if '/kernels/logs/stream/' in request.url:
            response.encoding = 'utf-8'
            # requests defaults to 512B buffering. A short challenge must reach
            # the coordinator without waiting for the next permitted phase.
            lines = response.iter_lines
            def immediate_lines(*args, **options):
                options['chunk_size'] = 1
                return lines(*args, **options)
            response.iter_lines = immediate_lines
        return response
    with patch.object(requests.Session, 'send', send):
        yield


def live_identity(api, grant):
    value = get_kernel(api, control.JOB)
    require(value.metadata.ref == control.JOB and value.metadata.current_version_number == grant['version']
            and value.metadata.is_private is True, 'LIVE_JOB_VERSION_PRIVACY')
    require(control.code_hash(json.loads(value.blob.source)) == grant['notebook_code_sha256'], 'LIVE_JOB_CODE_DRIFT')
    return value.metadata.id


def sanitized_failure(failure):
    """No URL, response body, credentials or raw stdout in public error records."""
    chain, seen = [], set()
    while failure is not None and id(failure) not in seen and len(chain) < 5:
        seen.add(id(failure))
        response = getattr(failure, 'response', None)
        chain.append({'type': type(failure).__name__, 'module': type(failure).__module__,
            'message_sha256': hashlib.sha256(str(failure).encode()).hexdigest(),
            'http_status': getattr(response, 'status_code', None),
            'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                       for f in traceback.extract_tb(failure.__traceback__)[-8:]]})
        failure = failure.__cause__ or failure.__context__
    return {'exception_chain': chain, 'message_policy': 'HASH_ONLY_NO_PRIVATE_TEXT'}


def coordinate(api, grant, seconds, evidence=None):
    coordinator = control.Coordinator(grant)
    events = queue.Queue(maxsize=128)
    stop = threading.Event()
    def put(kind, value):
        while not stop.is_set():
            try:
                events.put((kind, value), timeout=.2)
                return
            except queue.Full:
                continue
    def stream():
        # Only re-open the read-only stream. Never restart the coordinator,
        # re-submit a notebook, repeat a permit write or repeat a model call.
        for connection in range(4):
            if stop.is_set():
                return
            put('connection', connection)
            try:
                for item in api.kernels_logs_stream(control.JOB + '/1'):
                    if stop.is_set():
                        return
                    require(isinstance(item, dict), 'LIVE_EVENT_SHAPE')
                    data = item.get('data')
                    if data is None:  # SDK heartbeat/control event, no stdout.
                        continue
                    require(isinstance(data, str), 'LIVE_LOG_TYPE')
                    put('data', data)
                state = str(api.kernels_status(control.JOB + '/1').status).split('.')[-1]
                if state in ('COMPLETE', 'ERROR', 'CANCELLED'):
                    put('end', state)
                    return
                require(state in ('RUNNING', 'QUEUED'), 'LIVE_STATUS_UNKNOWN')
                put('disconnect', {'reason': 'EOF_BEFORE_TERMINAL', 'connection': connection})
            except Exception as failure:
                detail = sanitized_failure(failure)
                detail['connection'] = connection
                put('disconnect', detail)
                # Schema/auth failures are not transient connection failures.
                from requests.exceptions import ConnectionError, Timeout, ChunkedEncodingError
                if not isinstance(failure, (ConnectionError, Timeout, ChunkedEncodingError)):
                    put('error', detail)
                    return
            if stop.wait(1):
                return
        put('error', {'reason': 'READ_ONLY_RECONNECT_BUDGET_EXHAUSTED'})
    thread = threading.Thread(target=stream, daemon=True)
    thread.start()
    deadline, pending, total = time.monotonic() + seconds, '', 0
    observations = []
    def observe(value):
        observations.append(value)
        if evidence is not None:
            write(Path(evidence) / ('transport-%03d.json' % len(observations)), value)
    try:
        while time.monotonic() < deadline:
            try:
                kind, value = events.get(timeout=min(5, max(.01, deadline - time.monotonic())))
            except queue.Empty:
                continue
            if kind in ('connection', 'disconnect', 'error'):
                observe({'kind': kind, 'detail': value, 'permits': list(coordinator.accepted)})
            require(kind != 'error', 'LIVE_LOG_TRANSPORT_ERROR_NO_RETRY')
            if kind == 'connection':
                pending = ''  # Reopened SDK stream replays from beginning.
                continue
            if kind == 'disconnect':
                continue
            if kind == 'end':
                return {'permits': list(coordinator.accepted), 'log_stream': 'ENDED',
                        'terminal': value, 'transport': observations}
            require(isinstance(value, str), 'LIVE_LOG_TYPE')
            total += len(value.encode())
            require(total <= 16 * 2**20, 'LIVE_LOG_LIMIT')
            pending += value
            lines = pending.split('\n')
            pending = lines.pop()
            require(len(pending) <= 2**20, 'LIVE_LOG_LINE_LIMIT')
            # Official SDK events may be complete stdout lines without a newline;
            # do not wait until the next process phase to acknowledge this one.
            if control.PREFIX in pending:
                try:
                    json.loads(pending.split(control.PREFIX, 1)[1])
                except json.JSONDecodeError:
                    pass  # Bounded partial chunk; never guess or repair JSON.
                else:
                    lines.append(pending)
                    pending = ''
            for line in lines:
                if control.PREFIX not in line:
                    continue
                # Kaggle may prefix stdout with a timestamp; the payload has no raw.
                challenge = json.loads(line.split(control.PREFIX, 1)[1])
                live_identity(api, grant)
                coordinator.accept(challenge)
        raise TimeoutError('COORDINATOR_DEADLINE_NO_RETRY')
    except BaseException as failure:
        observe({'kind': 'coordinator-failure', **sanitized_failure(failure),
                 'permits': list(coordinator.accepted)})
        raise
    finally:
        stop.set()


def verify_result(archive, grant):
    """Bind local summary to actual archive members, source and strict raw parse."""
    import zipfile
    from safeshift.pilot.contract import parse_label
    require(sha(archive) == read(Path(str(archive) + '.sha256.json'))['sha256'], 'FINAL_EXPORT_SEAL')
    members = verify_archive(archive)
    with zipfile.ZipFile(archive) as bundle:
        summary = json.loads(bundle.read('summary.json'))
        source = json.loads(bundle.read('source.json'))
        release = json.loads(bundle.read('release.json'))
        require(source['runtime_commit'] == grant['runtime_commit']
                and digest(source['manifest']) == grant['manifest_sha256']
                and release['grant'] == grant and release['binding'] == digest(grant), 'FINAL_RELEASE_CUSTODY')
        counts = {'load_reservations': int('load-reservation.json' in members),
            'call_reservations': int('sample/reservation.json' in members),
            'native_call_markers': int('sample/native_call.json' in members)}
        require(summary['identity'] == grant['identity'] and summary['limits'] == control.LIMITS
                and all(summary[k] == v for k, v in counts.items())
                and summary['weights_loaded'] == ('loaded.json' in members)
                and summary['original_smoke_counts'] == {'qwen3': 1, 'internvl35': 1,
                    'minicpm4': counts['native_call_markers']}, 'FINAL_CALL_BUDGET')
        require(summary['status'] in ('SUCCESS', 'INVALID', 'TECHNICAL_ERROR')
                and summary['scientific_results_excluded'] is True and summary['automatic_retry'] is False,
                'FINAL_STATUS_POLICY')
        if summary['status'] in ('SUCCESS', 'INVALID'):
            result = json.loads(bundle.read('sample/result.json'))
            raw = json.loads(bundle.read('sample/raw.json'))
            require(all(v == 1 for v in counts.values()) and summary['weights_loaded']
                    and summary['consumption'] == 'COMPLETED'
                    and result['raw_sha256'] == members['sample/raw.json'], 'FINAL_RAW_CUSTODY')
            label = parse_label(raw['response'])
            require(result['label'] == label and result['status'] == summary['status'] ==
                    ('SUCCESS' if label else 'INVALID') and result['hnlo'] is None
                    and result['hnlo_status'] == 'LABEL_ONLY_OWNER_DECISION'
                    and raw['cpu_tokenizer_replay']['status'] == 'PASS' and not raw['raw_nonfinite'],
                    'FINAL_STRICT_LABEL_ONLY_REPLAY')
    return summary, members


def predecessor_history(api, root):
    """Cross-job budget: require sealed, terminal, affirmative zero-call proof."""
    import zipfile
    require(control.remote_record('campaign-call') is None, 'CAMPAIGN_CALL_ALREADY_RESERVED')
    receipts = []
    require(3 <= control.JOB_NUMBER <= 5, 'NEW_JOB_BUDGET')
    for n in range(2, 6):
        identity = 'issue173-minicpm-original-train-once-v' + str(n)
        records = {name: control.remote_record(name, identity) for name in
                   ('submission', 'submitted', *control.PHASES, 'finished')}
        if n >= control.JOB_NUMBER:
            require(not any(records.values()), 'NEW_OR_LATER_JOB_ALREADY_RESERVED')
            continue
        require(all(records[k] is not None for k in ('submission', 'submitted', 'launch')),
                'PREDECESSOR_CUSTODY_INCOMPLETE')
        grant = records['submission']['grant']
        require(grant['identity'] == identity and grant['job'] == 'nguynanhtn/safeshift-' + identity
                and grant['version'] == 1, 'PREDECESSOR_GRANT_IDENTITY')
        value = get_kernel(api, grant['job'])
        state = str(api.kernels_status(grant['job'] + '/1').status).split('.')[-1]
        require(state in ('COMPLETE', 'ERROR', 'CANCELLED') and value.metadata.is_private is True
                and value.metadata.id == records['submitted']['kernel_id']
                and value.metadata.current_version_number == 1
                and control.code_hash(json.loads(value.blob.source)) == grant['notebook_code_sha256'],
                'PREDECESSOR_NOT_TERMINAL_OR_IDENTITY')
        archive = Path(root) / (identity + '.zip')
        summary, members = verify_result(archive, grant)
        if n == 2:
            require(sha(archive) == '06ed278b2e9973c6186695c6a8327d4522fa9e02b010baac2cd90484b100e03e',
                    'IMMUTABLE_V2_SEAL')
        require(records['call'] is None and summary['native_call_markers'] == 0
                and summary['call_reservations'] == 0 and summary['consumption'] == 'NO_CALL_OBSERVED_NO_AUTO_RETRY',
                'PREDECESSOR_CALL_OR_UNCERTAIN')
        # Absence of a marker alone is insufficient: require normal child exit
        # with a retained pre-call error, followed by supervisor export.
        with zipfile.ZipFile(archive) as bundle:
            supervisor = json.loads(bundle.read('native-supervisor.json'))
            require(supervisor['status'] == 'CHILD_FAILURE' and supervisor['returncode'] == 1,
                    'PREDECESSOR_NATIVE_TERMINATION_UNPROVEN')
            logs = [name for name in members if name.endswith('.log') and 'native' in name]
            require(len(logs) == 1 and b'REMOTE_PERMIT_TIMEOUT_NO_RETRY' in bundle.read(logs[0]),
                    'PREDECESSOR_PRECALL_FAILURE_UNPROVEN')
        receipts.append({'identity': identity, 'state': state, 'archive_sha256': sha(archive),
            'native_calls': 0, 'load_reservations': summary['load_reservations'],
            'records_sha256': digest(records)})
    return receipts


def make_grant(comment_id, notebook, head):
    require(comment_id == 6602848993, 'DELEGATED_AUTHORITY_REQUIRED')
    nb = read(notebook)
    spec = nb['metadata']['safeshift']
    now = int(time.time())
    return control.delegated_grant({'identity': control.IDENTITY, 'source_head': head,
        'runtime_commit': spec['runtime_commit'], 'manifest_sha256': spec['manifest_sha256'],
        'notebook_sha256': sha(notebook), 'notebook_code_sha256': control.code_hash(nb),
        'job': control.JOB, 'version': 1, 'limits': control.LIMITS,
        'issued_unix': now, 'expires_unix': now + 1800, 'authority': control.authority(),
        'authorization_kind': 'OWNER_BOUNDED_DELEGATION_NOT_HEAD_REVIEW'})


def submit(api, comment_id, notebook, history_inputs, stage, predecessor_outputs=None):
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT), 'CLEAN_REVIEWED_TREE_REQUIRED')
    grant = make_grant(comment_id, notebook, head)
    pr = control.public_get('/pulls/175')
    require(pr['head']['sha'] == head and pr['head']['ref'] == control.BRANCH
            and pr['draft'] and not pr['merged'], 'REMOTE_REVIEWED_DRAFT_HEAD')
    require(sha(notebook) == grant['notebook_sha256'], 'REVIEWED_NOTEBOOK_HASH')
    nb = read(notebook)
    spec = nb['metadata']['safeshift']
    require(spec['identity'] == control.IDENTITY and spec['runtime_commit'] == grant['runtime_commit']
            and spec['manifest_sha256'] == grant['manifest_sha256'] and spec['limits'] == control.LIMITS
            and control.code_hash(nb) == grant['notebook_code_sha256'], 'NOTEBOOK_RELEASE_BINDING')
    # The notebook must be tracked in the clean source HEAD, not an arbitrary
    # ignored file supplied with self-consistent hashes.
    relative = Path(notebook).resolve().relative_to(ROOT.resolve()).as_posix()
    require(subprocess.check_output(['git', 'show', head + ':' + relative], cwd=ROOT) == Path(notebook).read_bytes(),
            'NOTEBOOK_NOT_COMMITTED')
    from scripts.build_minicpm173_once import build
    require(build(grant['runtime_commit']) == nb, 'COMMITTED_NOTEBOOK_REPRODUCTION')
    require(all(control.remote_record(n) is None for n in ('submission', 'submitted', *control.PHASES, 'finished')),
            'REMOTE_HISTORY_NONEMPTY_NO_RESUBMISSION')
    history = inspect_history(paths_from_mounts(history_inputs))
    diagnostics = diagnostic_history(history_inputs)
    predecessors = predecessor_history(api, predecessor_outputs)
    observed = inventory(api)
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=False)
    write(stage / 'inventory.json', observed)
    write(stage / 'predecessors.json', predecessors)
    write(stage / 'grant.json', grant)
    metadata = {'id': control.JOB, 'title': 'SafeShift issue173 minicpm original train once v' + str(control.JOB_NUMBER),
        'code_file': 'mini.ipynb', 'language': 'python', 'kernel_type': 'notebook', 'is_private': True,
        'enable_gpu': True, 'enable_tpu': False, 'enable_internet': True,
        'dataset_sources': ['nguynanhtn/inspecsafe-v1-kaggle', 'nguynanhtn/safeshift-pilot-input'],
        'kernel_sources': kernel_sources(), 'competition_sources': [], 'model_sources': []}
    write(stage / 'kernel-metadata.json', metadata)
    with (stage / 'mini.ipynb').open('xb') as stream:
        stream.write(Path(notebook).read_bytes())
    # Before first POST to Kaggle: durable across machines, no TTL/reclaim/reset.
    control.create_record('submission', {'grant': grant, 'approval_comment': comment_id,
        'original_counts': history['consumed'], 'diagnostic_calls': sum(d['calls'] for d in diagnostics),
        'inventory_sha256': digest(observed), 'predecessors': predecessors})
    start = time.monotonic()
    result = api.kernels_push(str(stage), timeout='1800', acc='NvidiaTeslaT4')
    write(stage / 'submit-return.json', result.to_dict())
    kernel_id = live_identity(api, grant)
    control.create_record('submitted', {'job': control.JOB, 'kernel_id': kernel_id, 'version': 1,
        'binding': digest(grant)})
    try:
        report = coordinate(api, grant, max(1, grant['expires_unix'] - time.time()), stage)
        write(stage / 'coordinator.json', report)
    except Exception as failure:
        write(stage / 'coordinator-error.json', sanitized_failure(failure))
        # Never restart dispatch. Continue read-only terminal reconciliation so
        # a failed transport still yields the actual sealed failure evidence.
    while True:
        state = str(api.kernels_status(control.JOB + '/1').status).split('.')[-1]
        if state in ('COMPLETE', 'ERROR', 'CANCELLED'):
            break
        require(state in ('RUNNING', 'QUEUED') and time.monotonic() - start < 1800,
                'TERMINAL_JOB_STATUS_UNKNOWN_NO_RETRY')
        time.sleep(min(15, max(0, 1800 - (time.monotonic() - start))))
    # No re-submit on missing output. Download only this exact version's small evidence.
    output = stage / 'output'
    output.mkdir(exist_ok=False)
    api.kernels_output(control.JOB + '/1', str(output), file_pattern=r'\.zip(?:\.sha256\.json)?$', quiet=True)
    archive = safe(output, control.IDENTITY + '.zip')
    summary, members = verify_result(archive, grant)
    control.create_record('finished', {'binding': digest(grant), 'archive_sha256': sha(archive),
        'status': summary['status'], 'original_smoke_counts': summary['original_smoke_counts'],
        'consumption': summary['consumption'], 'members': len(members) + 1})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--approval-comment', type=int, required=True)
    parser.add_argument('--notebook', type=Path, required=True)
    parser.add_argument('--history-inputs', type=Path, required=True)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--predecessor-outputs', type=Path, required=True)
    args = parser.parse_args()
    from kaggle import api
    with bounded_http(), patch.object(control, 'public_get', authenticated_github_get):
        print(json.dumps(submit(api, args.approval_comment, args.notebook, args.history_inputs, args.stage,
                                args.predecessor_outputs)))
