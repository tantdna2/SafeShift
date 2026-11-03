"""Mini original TRAIN one-shot admission and public, credential-free VM permits.

Only the local authenticated coordinator writes create-only GitHub records.
Every executing process generates its own nonce; saved permits cannot resume it.
"""
import base64
import hashlib
import json
import re
import secrets
import subprocess
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import sha
from safeshift.pilot.contract import digest

JOB_NUMBER = 3
IDENTITY = 'issue173-minicpm-original-train-once-v' + str(JOB_NUMBER)
JOB = 'nguynanhtn/safeshift-' + IDENTITY
BRANCH = 'verify/issue173-real-checkpoints'
REPO = 'tantdna2/SafeShift'
API = 'https://api.github.com/repos/' + REPO
LEDGER = 'docs/research/evidence/issue173/dispatch/' + IDENTITY
CAMPAIGN = 'docs/research/evidence/issue173/dispatch/mini-delegation-6602848993'
AUTHORITY = {6602848993: '136e1b35928e9bfb36a3b9ae1241d72971a9416be570dfe8de066c64ae893734',
             6603028889: 'f9aea8ece42fa08c5f10fee92b5a2b3c1b97c77362a2061a22da4b582f93abb5'}
PREFIX = 'SAFESHIFT_MINI173_CHALLENGE '
PHASES = ('launch', 'load', 'call')
LIMITS = {'model_key': 'minicpm4', 'ordinal': 0, 'max_loads': 1,
          'max_calls': 1, 'max_seconds': 1800, 'max_physical_gpu_seconds': 3600}


def public_get(path, *, missing=False):
    """One bounded HTTPS read. Only an absent permit is pollable; errors stop."""
    request = Request(API + path, headers={'Accept': 'application/vnd.github+json',
        'User-Agent': 'SafeShift-Mini173', 'Cache-Control': 'no-cache'})
    try:
        with urlopen(request, timeout=15) as response:
            require(response.geturl().startswith(API + '/'), 'REMOTE_REDIRECT')
            payload = response.read(2**20 + 1)
            require(len(payload) <= 2**20, 'REMOTE_RESPONSE_BOUND')
            return json.loads(payload)
    except HTTPError as error:
        if error.code == 404 and missing:
            return None
        raise RuntimeError('REMOTE_READ_HTTP_' + str(error.code)) from None


def record_path(name, identity=None):
    require(name in ('submission', 'submitted', *PHASES, 'finished', 'campaign-call'), 'LEDGER_RECORD_NAME')
    if name == 'campaign-call':
        return CAMPAIGN + '/call.json'
    if identity is not None:
        require(identity in ['issue173-minicpm-original-train-once-v' + str(n) for n in range(2, 6)], 'LEDGER_IDENTITY')
    return ('docs/research/evidence/issue173/dispatch/' + identity if identity else LEDGER) + '/' + name + '.json'


def remote_record(name, identity=None):
    value = public_get('/contents/' + record_path(name, identity) + '?ref=' + BRANCH
                       + '&cache=' + str(time.time_ns()), missing=True)
    if value is None:
        return None
    require(value['type'] == 'file' and value['encoding'] == 'base64', 'LEDGER_CONTENT_TYPE')
    return json.loads(base64.b64decode(value['content'], validate=False))


def create_record(name, value):
    """No SHA/update/delete/retry. A lost response is UNKNOWN, never success."""
    path = record_path(name)
    payload = {'branch': BRANCH, 'message': 'evidence(issue173): reserve ' + name,
        'content': base64.b64encode((json.dumps(value, sort_keys=True) + '\n').encode()).decode()}
    result = subprocess.run(['gh', 'api', '--method', 'PUT', 'repos/' + REPO + '/contents/'
        + path, '--input', '-'], input=json.dumps(payload),
        text=True, capture_output=True, timeout=30)
    require(result.returncode == 0, 'REMOTE_CREATE_FAILED_OR_UNKNOWN_NO_RETRY')
    receipt = json.loads(result.stdout)
    require(receipt.get('content', {}).get('path') == path
            and receipt.get('commit', {}).get('sha'), 'REMOTE_CREATE_UNCONFIRMED_NO_RETRY')
    return receipt['commit']['sha']


def authority():
    for number, expected in AUTHORITY.items():
        value = public_get('/issues/comments/' + str(number))
        require(value['user']['login'] == 'tantdna2' and value['issue_url'] == API + '/issues/175'
                and hashlib.sha256(value['body'].encode()).hexdigest() == expected,
                'DELEGATED_AUTHORITY_CHANGED_OR_WRONG_OWNER')
    return {str(k): v for k, v in AUTHORITY.items()}


def delegated_grant(grant):
    require(set(grant) == {'identity', 'source_head', 'runtime_commit', 'manifest_sha256',
        'notebook_sha256', 'notebook_code_sha256', 'job', 'version', 'issued_unix',
        'expires_unix', 'limits', 'authority', 'authorization_kind'}, 'DELEGATED_GRANT_FIELDS')
    require(3 <= JOB_NUMBER <= 5 and grant['identity'] == IDENTITY and grant['job'] == JOB
        and type(grant['version']) is int and grant['version'] == 1 and grant['limits'] == LIMITS
        and grant['authorization_kind'] == 'OWNER_BOUNDED_DELEGATION_NOT_HEAD_REVIEW'
        and grant['authority'] == authority(), 'DELEGATED_SCOPE')
    for key in ('source_head', 'runtime_commit', 'manifest_sha256', 'notebook_sha256', 'notebook_code_sha256'):
        size = 40 if key.endswith(('head', 'commit')) else 64
        require(isinstance(grant[key], str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', grant[key]), 'RELEASE_HASH')
    require(type(grant['issued_unix']) is int and type(grant['expires_unix']) is int
        and grant['expires_unix'] - grant['issued_unix'] == LIMITS['max_seconds']
        and grant['issued_unix'] <= time.time() < grant['expires_unix'], 'DELEGATED_DEADLINE')
    return grant


def read_grant(comment_id):
    require(type(comment_id) is int and comment_id > 6598989252, 'EXPLICIT_NEW_REVIEW_COMMENT_REQUIRED')
    comment = public_get('/issues/comments/' + str(comment_id))
    require(comment['user']['login'] == 'tantdna2'
            and comment['issue_url'] == API + '/issues/175', 'OWNER_PR175_APPROVAL_REQUIRED')
    matches = re.findall(r'MINICPM173_RELEASE_V1\s*```json\s*(\{.*?\})\s*```', comment['body'], re.S)
    require(len(matches) == 1, 'EXACT_MACHINE_READABLE_RELEASE_REQUIRED')
    grant = json.loads(matches[0])
    fields = {'identity', 'reviewed_head', 'runtime_commit', 'manifest_sha256', 'notebook_sha256',
              'notebook_code_sha256', 'job', 'version', 'expires_unix', 'limits'}
    require(set(grant) == fields and grant['identity'] == IDENTITY
            and grant['job'] == JOB and type(grant['version']) is int and grant['version'] == 1
            and grant['limits'] == LIMITS, 'EXACT_MINI_ONLY_RELEASE')
    for key in ('reviewed_head', 'runtime_commit', 'manifest_sha256', 'notebook_sha256', 'notebook_code_sha256'):
        size = 40 if key.endswith(('head', 'commit')) else 64
        require(isinstance(grant[key], str) and re.fullmatch('[0-9a-f]{' + str(size) + '}', grant[key]), 'RELEASE_HASH')
    require(type(grant['expires_unix']) is int and time.time() < grant['expires_unix'], 'RELEASE_EXPIRED')
    return grant


def source_check(spec):
    require(set(spec) == {'runtime_commit', 'manifest'}, 'SOURCE_SPEC_FIELDS')
    require(re.fullmatch('[0-9a-f]{40}', spec['runtime_commit']) and spec['manifest'], 'EXACT_RUNTIME_SOURCE')
    for name, expected in spec['manifest'].items():
        from safeshift.pilot.artifacts import safe
        require(sha(safe(ROOT, name)) == expected, 'MINI_SOURCE_DRIFT:' + name)


def context(spec):
    source_check(spec)
    submitted = remote_record('submission')
    require(submitted is not None, 'REVIEW_HOLD_NO_REMOTE_SUBMISSION')
    require(submitted['approval_comment'] == 6602848993, 'DELEGATED_AUTHORITY_REQUIRED')
    grant = delegated_grant(submitted['grant'])
    require(submitted['grant'] == grant and grant['runtime_commit'] == spec['runtime_commit']
            and grant['manifest_sha256'] == digest(spec['manifest']), 'SOURCE_RELEASE_BINDING')
    return {'grant': grant, 'approval_comment': submitted['approval_comment'], 'binding': digest(grant)}


def permit(ctx, phase, parent_nonce, *, emit=print):
    """Every invocation creates a new challenge, including direct worker calls."""
    require(phase in PHASES, 'MINI_PHASE_ONLY')
    nonce = secrets.token_hex(32)
    challenge = {'identity': IDENTITY, 'binding': ctx['binding'], 'phase': phase,
                 'nonce': nonce, 'parent_nonce': parent_nonce}
    # A saved grant cannot authorize a new process, even on an empty fresh VM.
    require(remote_record(phase) is None, 'REMOTE_PHASE_ALREADY_RESERVED_NO_REPLAY')
    emit(PREFIX + json.dumps(challenge, sort_keys=True), flush=True)
    deadline = min(time.monotonic() + 240, time.monotonic() + ctx['grant']['expires_unix'] - time.time())
    while time.monotonic() < deadline:
        value = remote_record(phase)
        if value is not None:
            require(value == challenge, 'REMOTE_PERMIT_NONCE_MISMATCH_NO_REPLAY')
            if phase == 'call' and 'authorization_kind' in ctx['grant']:
                require(remote_record('campaign-call') == challenge, 'CAMPAIGN_CALL_BINDING')
            require(time.time() < ctx['grant']['expires_unix'], 'RELEASE_EXPIRED')
            return value
        time.sleep(min(15, max(0, deadline - time.monotonic())))
    raise TimeoutError('REMOTE_PERMIT_TIMEOUT_NO_RETRY')


def code_hash(notebook):
    return digest([{'cell_type': c['cell_type'], 'source': ''.join(c['source'])}
                   for c in notebook['cells'] if c['cell_type'] == 'code'])


class Coordinator:
    """Single local observer; no restart/adoption after an uncertain submission."""
    def __init__(self, grant):
        self.grant, self.accepted = grant, {}

    def accept(self, challenge):
        require(set(challenge) == {'identity', 'binding', 'phase', 'nonce', 'parent_nonce'}, 'CHALLENGE_FIELDS')
        phase = challenge['phase']
        require(phase in PHASES and challenge['identity'] == IDENTITY
                and challenge['binding'] == digest(self.grant), 'CHALLENGE_IDENTITY')
        require(re.fullmatch('[0-9a-f]{64}', challenge['nonce']), 'CHALLENGE_NONCE')
        if phase in self.accepted:
            require(self.accepted[phase] == challenge, 'DUPLICATE_PROCESS_NO_PERMIT')
            return  # Repeated log chunk, never another write.
        require(phase == PHASES[len(self.accepted)], 'PHASE_ORDER')
        parent = '' if phase == 'launch' else self.accepted[PHASES[PHASES.index(phase)-1]]['nonce']
        require(challenge['parent_nonce'] == parent, 'PHASE_PARENT_NONCE')
        require(time.time() < self.grant['expires_unix'], 'RELEASE_EXPIRED')
        if phase == 'call' and 'authorization_kind' in self.grant:
            create_record('campaign-call', challenge)
        create_record(phase, challenge)  # Atomic create; a conflict or timeout aborts.
        self.accepted[phase] = challenge
