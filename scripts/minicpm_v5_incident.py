"""Read-only V5 custody. Never signs, publishes, submits or appends a journal."""
import argparse
from copy import deepcopy
from pathlib import Path
import tempfile

from safeshift.candidates.source import ROOT, require
from safeshift.pilot.artifacts import read, write, sha, safe, write_bytes
from safeshift.pilot.contract import digest
from safeshift.fulltrain import minicpm_v5_incident as incident, minicpm_release as a
from scripts import minicpm_v44_incident as v44, minicpm_fulltrain_transport as transport


def prefix(events):
    v44.prefix(events[:6])  # preserves the exact V4-4 prefix/hold
    require(len(events) == 10 and [e['kind'] for e in events[6:]] ==
            ['REPAIR_BOUND', 'PENDING_RESERVED', 'PENDING_PUBLISH_INTENT', 'PENDING_PUBLISHED'],
            'MINICPM_V5_EXACT_JOURNAL_PREFIX')
    binding, active = events[6]['payload'], deepcopy(events[7]['payload'])
    require(binding['grant_sha256'] == incident.PREVIOUS_GRANT
            and digest(active['ticket']) == incident.PREVIOUS_TICKET and digest(active['value']) == incident.PREVIOUS_VALUE
            and active['ticket']['payload']['previous_event_sha256'] == events[7]['previous']
            and active['ticket']['payload']['reserved_after'] == incident.RESERVED
            and all(e['payload']['ticket_sha256'] == incident.PREVIOUS_TICKET for e in events[8:]),
            'MINICPM_V5_JOURNAL_BINDING')
    active.update(locator=binding['locator'], journal_head_sha256=digest(events[-1]))
    return active


def validate_inventory(names, value, archive):
    import re
    require(type(names) is list and 1 <= len(names) <= 16384 and len(names) == len(set(names)),
            'MINICPM_V5_EXHAUSTIVE_INVENTORY')
    control = archive.removesuffix('.zip') + '/'
    exact = {archive, archive + '.sha256.json', value['request']['plan']['run_id'] + '-release-context.json',
        *(control + n for n in incident.MEMBERS | {'checksums.json'}),
        *('minicpm-fulltrain-claims/mcpm4-restart-v1/5/' + n + '.json' for n in ('launch', 'admit', 'setup', 'cpu'))}
    source = 'data/processed/fresh_fulltrain_code/' + incident.PREVIOUS_SOURCE + '/'
    for name in names:
        from safeshift.pilot.artifacts import relative
        relative(name)
        require(name in exact or name.startswith(source) and (name.endswith(('.py', '.json', '.txt'))
            or re.fullmatch(r'(?:[A-Za-z0-9_]+/)+__pycache__/[A-Za-z0-9_]+\.cpython-313\.pyc', name[len(source):]))
            or re.fullmatch(r'minicpm-fulltrain(?:/supervisor_control|\-claims/mcpm4-restart-v1/5)/attempts/active_[0-9a-f]{64}\.lock', name),
            'MINICPM_V5_UNEXPECTED_OUTPUT_NATIVE_AMBIGUITY:' + name)
    require({archive, archive + '.sha256.json'} <= set(names), 'MINICPM_V5_REMOTE_PAIR_REQUIRED')


def inventory(client, value, *, evidence=None):
    # The existing paginator records every provider entry before ZIP selection.
    from contextlib import contextmanager
    from types import SimpleNamespace
    from scripts.reconcile_train3763_manual import output_inventory
    names = []
    class RecordingClient:
        @contextmanager
        def build_kaggle_client(self):
            with client.build_kaggle_client() as remote:
                def listing(query):
                    result = remote.kernels.kernels_api_client.list_kernel_session_output(query)
                    names.extend(f.file_name for f in result.files)
                    return result
                yield SimpleNamespace(_http_client=remote._http_client, kernels=SimpleNamespace(
                    kernels_api_client=SimpleNamespace(list_kernel_session_output=listing)))
    selected, log = output_inventory(RecordingClient(), value['job'], 1)
    if evidence is not None:
        write(Path(evidence) / 'raw-inventory.json', sorted(names))
        write_bytes(Path(evidence) / 'provider.log', log.encode())
    validate_inventory(names, value, v44.output_names(selected))
    return selected, log, sorted(names)


def verify_evidence(directory, previous, *, online=False, client=None):
    from scripts.reconcile_train3763_manual import observe_kernel
    from safeshift.internvl3763_operator import api, code_hash
    directory = Path(directory)
    value, ticket = previous['value'], previous['ticket']
    require(read(directory / 'value.json') == value and read(directory / 'ticket.json') == ticket, 'MINICPM_V5_EVIDENCE_PACKAGE')
    notebook = read(directory / 'notebook.ipynb')
    require(code_hash(notebook) == ticket['payload']['notebook_code_sha256'], 'MINICPM_V5_NOTEBOOK_PIN')
    zip_inventory = read(directory / 'inventory.json')
    name = v44.output_names(zip_inventory)
    names = read(directory / 'full-inventory.json')
    validate_inventory(names, value, name)
    provider = read(directory / 'provider.json')
    result = incident.verify_supervisor(value, ticket, safe(directory / 'provider', name), provider)
    result.update(provider_log_sha256=sha(directory / 'provider.log'), output_names=sorted(zip_inventory),
        journal_head_sha256=previous['journal_head_sha256'], full_inventory_sha256=digest(names))
    if online:
        client = api() if client is None else client
        observed = observe_kernel(client, value['job'], 1, notebook, value['input_sources'],
            expected_state=provider['state'], kernel_id=provider['kernel_id'])
        require(observed == provider, 'MINICPM_V5_PROVIDER_CHANGED')
        selected, log, remote_names = inventory(client, value)
        require(v44.output_names(selected) == name and log.encode() == (directory / 'provider.log').read_bytes()
                and remote_names == names, 'MINICPM_V5_REMOTE_INVENTORY_OR_LOG_CHANGED')
        with tempfile.TemporaryDirectory() as tmp:
            transport.download_selected(selected, {name: 64 * 2**20, name + '.sha256.json': 4096}, tmp)
            require(sha(Path(tmp) / name) == result['supervisor_sha256'], 'MINICPM_V5_REMOTE_ARCHIVE_CHANGED')
            incident.verify_supervisor(value, ticket, Path(tmp) / name, observed)
    return result


def prepare(directory, *, operator=None, client=None, reader=None):
    from scripts.minicpm_fulltrain_recovery import RecoveredSerialJournal
    from scripts.reconcile_train3763_manual import observe_kernel
    from safeshift.internvl3763_operator import api
    from scripts.submit_internvl_v2 import bounded_http
    operator = RecoveredSerialJournal() if operator is None else operator
    previous = prefix(operator.events())
    old = incident.previous_release(a.github_get if reader is None else reader, previous['locator'])
    a.verify_signature(old['public_key'], previous['ticket']['payload'], previous['ticket']['signature'])
    package = safe(ROOT, previous['package'])
    client = api() if client is None else client
    with bounded_http():
        state = str(client.kernels_status(incident.JOB + '/1').status).split('.')[-1]
    require(state in ('COMPLETE', 'ERROR'), 'MINICPM_V5_TERMINAL_REQUIRED')
    notebook = read(package / 'notebook.ipynb')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    provider = observe_kernel(client, incident.JOB, 1, notebook, previous['value']['input_sources'], expected_state=state)
    write(directory / 'provider.json', provider)
    selected, log, names = inventory(client, previous['value'], evidence=directory)
    name = v44.output_names(selected)
    for filename, value in {'inventory.json': sorted(selected), 'full-inventory.json': names,
        'value.json': previous['value'], 'ticket.json': previous['ticket'], 'notebook.ipynb': notebook}.items():
        write(directory / filename, value)
    transport.download_selected(selected, {name: 64 * 2**20, name + '.sha256.json': 4096}, directory / 'provider')
    report = verify_evidence(directory, previous)
    write(directory / 'verification.json', report)
    require(prefix(operator.events()) == previous, 'MINICPM_V5_JOURNAL_CHANGED_DURING_READ')
    return report


def repair_template(grant, previous, closure, directive):
    from safeshift.fulltrain.minicpm_recovery import locator
    locator(directive)
    require(directive['comment_id'] == incident.DIRECTIVE, 'MINICPM_EXACT_V5_DIRECTIVE')
    grant = deepcopy(grant)
    grant['implementation_pr'] = None
    grant['repair'] = {'schema': incident.SCHEMA, 'directive': directive, 'previous_release': previous['locator'],
        'previous_ticket': previous['ticket'], 'journal_head_sha256': previous['journal_head_sha256'],
        'closure_sha256': digest(closure), 'reserved_after': deepcopy(incident.RESERVED)}
    return grant


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = prepare(args.output)
    print(result['disposition'], 'reservation retained; no journal append')


if __name__ == '__main__':
    main()
