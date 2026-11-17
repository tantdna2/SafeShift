"""Exact V5 CPU RAM failure: technical custody, no predictions or refund.

Historical V4-4 closure remains separate and immutable. This contract cannot
close a later/native failure or reuse V5's ticket on repaired source.
"""
from copy import deepcopy
import math
from pathlib import Path
import tempfile

from safeshift.candidates.source import require, snapshot_stat
from safeshift.pilot.artifacts import read, sha, import_archive
from safeshift.pilot.contract import digest, require_hash
from . import minicpm_release as a, minicpm_ui as ui, minicpm_incident as v44

SCHEMA = 'safeshift-minicpm-v5-ram-repair-v1'
DIRECTIVE = 6937169950
PREVIOUS_GRANT = '9bef24e5908eff58798c04042e90db468675014028ceaa0cdf55a4ece7feddca'
PREVIOUS_TICKET = '631540ae8c5013b114e0c9be2f9c85ba6685677670cf8ce840ce7ab9df815b41'
PREVIOUS_VALUE = '25cc8068bf170110ef8896a2fc92c95f31acb5fed0d161dc69e0d3f3b886bd60'
PREVIOUS_SOURCE = '3054352804cebd536b048389e01849344aacc6f5a6f2a76eb830500df9da185c'
PREVIOUS_MERGE = '006105080fc9b240e6ffff31618d325adac41522'
RESERVED = {'calls': 10526, 'jobs': 5, 'gpu_seconds': 144000}
JOB = 'nguynanhtn/safeshift-minicpm-mcpm4-restart-v1-5'
MEMBERS = {'admit-process.json', 'admit.log', 'admit/checkpoint.json', 'admit/resources.json',
    'admit/stage.json', 'capability.json', 'claims.json', 'cpu-process.json', 'cpu.log',
    'cpu/checkpoint.json', 'cpu/failure.json', 'cpu/software.json', 'failure.json', 'final_timing.json',
    'release.json', 'request.json', 'retention.json', 'setup-process.json', 'setup.log',
    'setup/allocation.json', 'setup/freeze.txt', 'setup/interpreters.json', 'setup/pip_bootstrap.json',
    'setup/pip_controller.json', 'setup/python-input.json', 'setup/python_venv_library.json',
    'setup/runtime.json', 'setup/setup.log', 'setup/stage.json', 'setup/venv_interpreter.json', 'setup/worker_pip.json'}


def previous_release(reader, locator):
    old = a.record(v44.owner_record(reader, locator, 200)['body'], a.RECOVERY_MARKER)
    require(digest(old) == PREVIOUS_GRANT and old['implementation_pr'] == 200
            and old['merged_sha'] == PREVIOUS_MERGE and old['scope']['source_sha256'] == PREVIOUS_SOURCE,
            'MINICPM_EXACT_V5_RELEASE_HISTORY')
    return old


def validate_repair(grant):
    r = grant['repair']
    require(type(r) is dict and set(r) == {'schema', 'directive', 'previous_release', 'previous_ticket',
        'journal_head_sha256', 'closure_sha256', 'reserved_after'} and r['schema'] == SCHEMA,
        'MINICPM_V5_REPAIR_FIELDS')
    from .minicpm_recovery import locator
    locator(r['directive']); locator(r['previous_release'])
    require(grant['implementation_pr'] > 200 and r['directive']['comment_id'] == DIRECTIVE
            and r['reserved_after'] == RESERVED, 'MINICPM_V5_NO_REFUND_OR_REPLAY')
    for name in ('journal_head_sha256', 'closure_sha256'):
        require_hash(r[name])
    ticket = r['previous_ticket']
    require(digest(ticket) == PREVIOUS_TICKET and ticket['payload']['grant_sha256'] == PREVIOUS_GRANT
            and ticket['payload']['value_sha256'] == PREVIOUS_VALUE
            and ticket['payload']['reserved_after'] == RESERVED, 'MINICPM_EXACT_V5_SIGNED_HOLD')
    a.verify_signature(grant['public_key'], ticket['payload'], ticket['signature'])


def authenticate_repair(grant, reader):
    validate_repair(grant)
    v44.owner_record(reader, grant['repair']['directive'], 200)
    old = previous_release(reader, grant['repair']['previous_release'])
    v44.authenticate_repair(old, reader)
    require(old['public_key'] == grant['public_key'] and old['caps'] == grant['caps']
            and old['recovery'] == grant['recovery'], 'MINICPM_V5_BUDGET_OR_AUTHORITY_DRIFT')
    before, after = deepcopy(old['scope']), deepcopy(grant['scope'])
    for scope in (before, after):
        scope.pop('source_sha256'); scope['identity'].pop('implementation_sha256')
    require(before == after, 'MINICPM_V5_SCIENCE_OR_INPUT_DRIFT')


def verify_supervisor(value, ticket, archive, provider):
    require(digest(value) == PREVIOUS_VALUE and digest(ticket) == PREVIOUS_TICKET
            and value['job'] == JOB and value['request']['source_sha256'] == PREVIOUS_SOURCE,
            'MINICPM_EXACT_V5_INCIDENT')
    require(provider['state'] in ('COMPLETE', 'ERROR') and provider['job_id'] == JOB
            and provider['version'] == 1 and type(provider['kernel_id']) is int
            and provider['notebook_code_sha256'] == ticket['payload']['notebook_code_sha256']
            and provider['safeshift_metadata'] == 'MATCHED', 'MINICPM_V5_TERMINAL_PROVIDER')
    require(snapshot_stat(archive).st_size <= 64 * 2**20, 'MINICPM_V5_ARCHIVE_BOUND')
    require(set(ui.pair(archive)) == MEMBERS, 'MINICPM_V5_EXACT_PRE_NATIVE_MEMBERS')
    with tempfile.TemporaryDirectory() as tmp:
        out = import_archive(archive, Path(tmp) / 'supervisor')
        require(read(out / 'request.json') == value['request']
                and read(out / 'capability.json')['ticket'] == ticket, 'MINICPM_V5_REQUEST_TICKET')
        release, failure = read(out / 'release.json'), read(out / 'failure.json')
        require(release['status'] == 'BLOCKED' and release['last_stage'] == 'cpu'
                and release['attempt_observed'] is False and release['diagnostic'] is False
                and release['recovery'] == 'NO_ATTEMPT' and release['scientific_qualified'] is False
                and release['source_sha256'] == PREVIOUS_SOURCE and release['failure'] == failure
                and failure['stage'] == 'cpu' and failure['category'] == 'TECHNICAL'
                and failure['message'] == 'SUPERVISED_CHILD_FAILURE', 'MINICPM_V5_CPU_FAILURE_REQUIRED')
        cpu_failure = read(out / 'cpu/failure.json')
        require(cpu_failure['stage'] == 'cpu' and cpu_failure['category'] == 'TECHNICAL'
                and cpu_failure['message'] == 'HOST_OR_CGROUP_RAM', 'MINICPM_V5_RAM_FAILURE_REQUIRED')
        for mode in ('admit', 'setup', 'cpu'):
            process = read(out / (mode + '-process.json'))
            require(process['schema'] == 'fresh-process-supervision-v1' and process['group_kill_sent'] is True
                    and process['automatic_retry'] is False and type(process['returncode']) is int
                    and (process['status'] == 'CHILD_FAILURE' and process['returncode'] != 0 if mode == 'cpu'
                         else process['status'] == 'EXITED' and process['returncode'] == 0),
                    'MINICPM_V5_REAPED_STAGE_REQUIRED')
            if mode != 'cpu':
                require(read(out / mode / 'stage.json') == {'status': 'RETURNED', 'stage': mode,
                    'request_sha256': digest(value['request']), 'source_sha256': PREVIOUS_SOURCE,
                    'native_attempt_permitted': False}, 'MINICPM_V5_STAGE_BINDING')
        require(read(out / 'setup/runtime.json')['request_sha256'] == digest(value['request'])
                and read(out / 'retention.json')['retained'] == [], 'MINICPM_V5_NO_RETAINED_NATIVE')
        claims = read(out / 'claims.json')
        require(set(claims) == {'launch.json', 'admit.json', 'setup.json', 'cpu.json'}, 'MINICPM_V5_NO_NATIVE_OR_UNKNOWN_CLAIM')
        times = []
        for kind in ('launch', 'admit', 'setup', 'cpu'):
            claim = claims[kind + '.json']
            require(set(claim) == {'kind', 'number', 'request_sha256', 'ticket_sha256', 'time_unix'}
                    and claim['kind'] == kind and claim['number'] == 5
                    and claim['request_sha256'] == digest(value['request']) and claim['ticket_sha256'] == digest(ticket)
                    and type(claim['time_unix']) in (int, float) and math.isfinite(claim['time_unix']), 'MINICPM_V5_CLAIM_BINDING')
            times.append(claim['time_unix'])
        require(times == sorted(times) and ticket['payload']['issued_unix'] <= times[0] < ticket['payload']['start_before_unix']
                and times[-1] < times[0] + value['request']['plan']['max_seconds'], 'MINICPM_V5_CLAIM_WINDOW')
        admitted = read(out / 'admit/resources.json')
    return {'schema': SCHEMA, 'disposition': 'FAILED_PRE_NATIVE_NO_USABLE_RESULTS', 'job': JOB, 'version': 1,
        'provider': provider, 'ticket_sha256': digest(ticket), 'value_sha256': digest(value),
        'supervisor_sha256': sha(archive), 'failure_sha256': digest(cpu_failure), 'claims_sha256': digest(claims),
        'native_calls': 0, 'native_evidence': 'AUTHENTICATED_CPU_FAILURE_AND_EXHAUSTIVE_PROVIDER_INVENTORY',
        'reserved_after': deepcopy(RESERVED), 'refund': False, 'history_import': False, 'scientific_qualified': False,
        'memory_evidence': {'admit': admitted['memory'], 'cpu_failure': 'HOST_OR_CGROUP_RAM',
            'cgroup_breakdown': 'NOT_RECORDED', 'failure_available_bytes': 'NOT_RECORDED',
            'cause': 'CACHE_VS_ANON_UNRESOLVED', 'group_exit': 'LEADER_REAPED_KILL_SENT_NO_SURVIVOR_SNAPSHOT'}}
