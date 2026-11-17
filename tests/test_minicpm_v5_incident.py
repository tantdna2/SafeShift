"""Synthetic exact V5 closure/source transition; no real authority/provider IO."""
from copy import deepcopy
from pathlib import Path
import shutil
import unittest
from unittest.mock import Mock, patch

import test_minicpm_v44_incident as fixtures
from safeshift.fulltrain import minicpm_v5_incident as incident, minicpm_incident as v44, minicpm_release as a
from safeshift.pilot.artifacts import read, write, write_bytes, export
from safeshift.pilot.contract import digest
from scripts import minicpm_v5_incident as op, minicpm_v44_incident as oldop, minicpm_fulltrain_recovery as journal, minicpm_fulltrain_operator as old


class V5Tests(unittest.TestCase):
    setUpClass = classmethod(fixtures.IncidentTests.setUpClass.__func__)
    tearDownClass = classmethod(fixtures.IncidentTests.tearDownClass.__func__)
    make_ticket = fixtures.IncidentTests.make_ticket
    build = fixtures.IncidentTests.build
    staged_operator = fixtures.IncidentTests.staged_operator
    verify_receipt = fixtures.IncidentTests.verify_receipt

    def setUp(self):
        fixtures.IncidentTests.setUp(self)
        api_patch = patch('safeshift.internvl3763_operator.api', return_value=Mock())
        api_patch.start(); self.addCleanup(api_patch.stop)
        first_report = self.verify_receipt()
        first_directory = self.directory
        self.grant5 = oldop.repair_template(self.grant, self.previous, first_report,
            {'comment_id': v44.DIRECTIVE, 'body_sha256': 'd' * 64})
        self.grant5['implementation_pr'] = 200
        self.value5 = journal.restart_spec(self.value, source_repair=True)
        with patch.object(a, 'load', return_value=self.grant5), patch.object(old, 'clean_source'), \
                patch.object(oldop, 'verify_evidence', return_value=first_report):
            self.operator.rebind_release(self.locator, self.value5, self.directory)
            provider = deepcopy(self.provider)
            provider['technical_predecessor'] = {'job': v44.JOB, 'version': 1, 'state': 'COMPLETE', 'kernel_id': 10}
            with patch.object(self.operator, 'observe_provider', return_value=provider), \
                    patch.object(old, 'notebook', side_effect=self.build), \
                    patch.object(old.sizing, 'propose', return_value={'calls': 3, 'seconds': 600}):
                self.operator.stage(self.key, self.root / 'data/processed/serial5')
            self.active = self.operator.state()[3]
        self.operator.append('PUBLISH_INTENT', {'ticket_sha256': digest(self.active['ticket'])})
        self.operator.append('PUBLISHED', {'ticket_sha256': digest(self.active['ticket']), 'proof': {'synthetic': True}})
        self.value, self.ticket = self.active['value'], self.active['ticket']
        for name, value in {'PREVIOUS_GRANT': digest(self.grant5), 'PREVIOUS_TICKET': digest(self.ticket),
            'PREVIOUS_VALUE': digest(self.value), 'PREVIOUS_SOURCE': self.value['request']['source_sha256'],
            'PREVIOUS_MERGE': self.grant5['merged_sha'], 'RESERVED': self.ticket['payload']['reserved_after']}.items():
            p = patch.object(incident, name, value); p.start(); self.addCleanup(p.stop)
        p = patch.object(op, 'ROOT', self.root); p.start(); self.addCleanup(p.stop)
        self.previous = op.prefix(self.operator.events())
        self.directory = self.root / 'data/processed/v5-incident'; self.directory.mkdir()
        self.control = self.root / 'synthetic-v5-supervisor'; self.control.mkdir()
        failure = {'stage': 'cpu', 'category': 'TECHNICAL', 'message': 'SUPERVISED_CHILD_FAILURE'}
        write(self.control / 'failure.json', failure)
        write(self.control / 'release.json', {'status': 'BLOCKED', 'last_stage': 'cpu', 'attempt_observed': False,
            'diagnostic': False, 'recovery': 'NO_ATTEMPT', 'scientific_qualified': False,
            'source_sha256': incident.PREVIOUS_SOURCE, 'failure': failure})
        write(self.control / 'request.json', self.value['request'])
        write(self.control / 'capability.json', {'ticket': self.ticket})
        for mode in ('admit', 'setup', 'cpu'):
            write(self.control / (mode + '-process.json'), {'schema': 'fresh-process-supervision-v1',
                'status': 'CHILD_FAILURE' if mode == 'cpu' else 'EXITED', 'returncode': int(mode == 'cpu'),
                'group_kill_sent': True, 'automatic_retry': False})
            if mode != 'cpu':
                write(self.control / mode / 'stage.json', {'status': 'RETURNED', 'stage': mode,
                    'request_sha256': digest(self.value['request']), 'source_sha256': incident.PREVIOUS_SOURCE,
                    'native_attempt_permitted': False})
        write(self.control / 'cpu/failure.json', {'stage': 'cpu', 'category': 'TECHNICAL', 'message': 'HOST_OR_CGROUP_RAM'})
        write(self.control / 'setup/runtime.json', {'request_sha256': digest(self.value['request'])})
        write(self.control / 'retention.json', {'retained': []})
        write(self.control / 'admit/resources.json', {'memory': {'available_bytes': 21102653440, 'cgroup_remaining_bytes': [21102653440]}})
        claims = {kind + '.json': {'kind': kind, 'number': 5, 'request_sha256': digest(self.value['request']),
            'ticket_sha256': digest(self.ticket), 'time_unix': self.ticket['payload']['issued_unix'] + i}
            for i, kind in enumerate(('launch', 'admit', 'setup', 'cpu'))}
        write(self.control / 'claims.json', claims)
        for name in incident.MEMBERS:
            if not (self.control / name).exists(): write(self.control / name, {'synthetic': True})
        self.archive = self.directory / 'provider' / self.name
        self.archive.parent.mkdir(parents=True); export(self.control, self.archive)
        self.provider_receipt.update(job_id=incident.JOB, notebook_code_sha256=self.ticket['payload']['notebook_code_sha256'])
        for filename, value in {'provider.json': self.provider_receipt, 'inventory.json': [self.name, self.name+'.sha256.json'],
            'full-inventory.json': [self.name, self.name+'.sha256.json'], 'value.json': self.value,
            'ticket.json': self.ticket, 'notebook.ipynb': read(self.root / self.active['package'] / 'notebook.ipynb')}.items():
            write(self.directory / filename, value)
        write_bytes(self.directory / 'provider.log', b'synthetic v5 provider log\n')

    def verify5(self):
        return op.verify_evidence(self.directory, self.previous)

    def replace(self, name, mutate):
        value = read(self.control/name); mutate(value)
        (self.control/name).write_text(__import__('json').dumps(value))
        (self.control/'checksums.json').unlink()
        self.archive.unlink(); Path(str(self.archive)+'.sha256.json').unlink()
        export(self.control, self.archive)

    def test_cpu_failure_closes_without_collected_refund_or_fabricated_cause(self):
        before = self.operator.events()
        report = self.verify5()
        self.assertEqual(report['native_calls'], 0)
        self.assertEqual(report['reserved_after'], incident.RESERVED)
        self.assertFalse(report['refund']); self.assertFalse(report['history_import'])
        self.assertEqual(report['memory_evidence']['cause'], 'CACHE_VS_ANON_UNRESOLVED')
        self.assertEqual(before, self.operator.events())

    def test_native_claim_partial_inventory_or_running_provider_cannot_close(self):
        for path in ('minicpm-fulltrain/run6/calls/000000/native_call.json', 'raw.json', 'other.zip'):
            with self.assertRaises(ValueError): op.validate_inventory([self.name, self.name+'.sha256.json', path], self.value, self.name)
        with self.assertRaisesRegex(ValueError, 'TERMINAL_PROVIDER'):
            incident.verify_supervisor(self.value, self.ticket, self.archive, {**self.provider_receipt, 'state': 'RUNNING'})
        self.replace('claims.json', lambda c: c.update({'load.json': c['cpu.json']}))
        with self.assertRaisesRegex(ValueError, 'NO_NATIVE'): self.verify5()

    def test_oom_or_wrong_failure_and_unreaped_child_rejected(self):
        self.replace('cpu/failure.json', lambda c: c.update(message='OOM'))
        with self.assertRaisesRegex(ValueError, 'RAM_FAILURE'): self.verify5()

    def test_unreaped_cpu_cannot_be_closed(self):
        self.replace('cpu-process.json', lambda c: c.update(group_kill_sent=False))
        with self.assertRaisesRegex(ValueError, 'REAPED_STAGE'): self.verify5()

    def test_new_source_authenticates_v5_and_v44_chain_without_science_or_cap_drift(self):
        report = self.verify5()
        grant = op.repair_template(self.grant5, self.previous, report,
            {'comment_id': incident.DIRECTIVE, 'body_sha256': 'd'*64})
        grant['implementation_pr'] = 201
        with patch.object(v44, 'owner_record'), patch.object(incident, 'previous_release', return_value=self.grant5), \
                patch.object(v44, 'authenticate_repair') as earlier:
            incident.authenticate_repair(grant, Mock())
            earlier.assert_called_once()
            bad = deepcopy(grant); bad['caps']['total_calls'] += 1
            with self.assertRaisesRegex(ValueError, 'BUDGET_OR_AUTHORITY'): incident.authenticate_repair(bad, Mock())
            bad = deepcopy(grant); bad['scope']['identity']['model_revision'] = '0'*40
            with self.assertRaisesRegex(ValueError, 'SCIENCE_OR_INPUT'): incident.authenticate_repair(bad, Mock())

    def test_fresh_serial6_rebind_retains_both_failures_and_all_reservations(self):
        report = self.verify5()
        grant6 = op.repair_template(self.grant5, self.previous, report,
            {'comment_id': incident.DIRECTIVE, 'body_sha256': 'd'*64})
        grant6['implementation_pr'] = 201
        a.validate(grant6)
        value6 = journal.restart_spec(self.value, ram_repair=True)
        old_events = self.operator.events()
        with patch.object(a, 'load', return_value=grant6), patch.object(old, 'clean_source'), \
                patch.object(op, 'verify_evidence', return_value=report), patch.object(journal, 'verify_v44_prefix'):
            result = self.operator.rebind_release(self.locator, value6, self.directory)
            self.assertEqual(result['next_serial'], 6)
            self.assertEqual(self.operator.state()[2], incident.RESERVED)
            self.assertEqual(self.operator.state()[4], [])
            with self.assertRaises(ValueError): self.operator.rebind_release(self.locator, value6, self.directory)
            provider = deepcopy(self.provider)
            provider['technical_predecessor'] = {'job': incident.JOB, 'version': 1, 'state': 'COMPLETE', 'kernel_id': 11}
            provider['technical_history'] = [{'job': v44.JOB, 'version': 1, 'state': 'COMPLETE', 'kernel_id': 10}]
            with patch.object(self.operator, 'observe_provider', return_value=provider), \
                    patch.object(old, 'notebook', side_effect=self.build), \
                    patch.object(old.sizing, 'propose', return_value={'calls': 3, 'seconds': 600}):
                self.operator.stage(self.key, self.root/'data/processed/serial6')
            _, events, reserved, active, completed = self.operator.state()
            self.assertEqual(active['ticket']['payload']['number'], 6)
            self.assertEqual(active['ticket']['payload']['reserved_before'], incident.RESERVED)
            self.assertEqual(reserved['calls'], incident.RESERVED['calls']+3)
            self.assertEqual(active['value']['request']['history'], [])
            self.assertEqual(active['value']['request']['plan']['scheduled_ordinals'][0], 0)
            self.assertEqual(events[:len(old_events)], old_events)
            self.assertNotIn('RESTART_COLLECTED', [e['kind'] for e in events])
            bad = deepcopy(active['ticket']); bad['payload']['provider'].pop('technical_history')
            with self.assertRaises(ValueError): a.verify_ticket(grant6, bad, active['value'])
        bad = deepcopy(grant6); bad['repair']['reserved_after']['calls'] = 0
        with self.assertRaisesRegex(ValueError, 'NO_REFUND'): a.validate(bad)
        with self.assertRaises(ValueError): a.verify_ticket(grant6, self.ticket, value6, collection=True)
