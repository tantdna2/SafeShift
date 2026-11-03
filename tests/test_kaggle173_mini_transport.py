"""Synthetic stream/authority regressions; no credentials, GPU or dataset."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from safeshift import minicpm173_once as c
from safeshift.pilot.contract import digest
from safeshift.pilot.artifacts import read
from scripts import submit_minicpm173_once as s


def delegated():
    now = int(time.time())
    return {'identity': c.IDENTITY, 'job': c.JOB, 'version': 1, 'source_head': 'a' * 40,
        'runtime_commit': 'b' * 40, 'manifest_sha256': 'c' * 64, 'notebook_sha256': 'd' * 64,
        'notebook_code_sha256': 'e' * 64, 'issued_unix': now, 'expires_unix': now + 1800,
        'limits': c.LIMITS.copy(), 'authority': {str(k): v for k, v in c.AUTHORITY.items()},
        'authorization_kind': 'OWNER_BOUNDED_DELEGATION_NOT_HEAD_REVIEW'}


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.grant = delegated()
        self.rows = []
        parent = ''
        for n, phase in enumerate(c.PHASES):
            row = {'identity': c.IDENTITY, 'binding': digest(self.grant), 'phase': phase,
                   'nonce': str(n + 1) * 64, 'parent_nonce': parent}
            self.rows.append(row)
            parent = row['nonce']
        self.records = {}
        self.api = Mock()
        self.api.kernels_status.return_value.status = 'COMPLETE'

    def create(self, name, value):
        if name in self.records:
            raise ValueError('CONFLICT')
        self.records[name] = deepcopy(value)

    def event(self, row):
        return {'stream_name': 'stdout', 'time': 1.0, 'data': c.PREFIX + json.dumps(row) + '\n'}

    def coordinate(self, seconds=5, evidence=None):
        with patch.object(s, 'live_identity', return_value=123), patch.object(c, 'create_record', side_effect=self.create):
            return s.coordinate(self.api, self.grant, seconds, evidence)

    def test_post_launch_disconnect_replay_delayed_split_events_complete_once(self):
        from requests.exceptions import ChunkedEncodingError
        def first():
            yield self.event(self.rows[0])
            raise ChunkedEncodingError('SYNTHETIC_PRIVATE_SECRET_URL')
        def second():
            yield {'stream_name': 'heartbeat', 'time': 1}
            yield self.event(self.rows[0])
            time.sleep(.04)
            payload = self.event(self.rows[1])['data']
            yield {'data': payload[:31]}
            yield {'data': payload[31:]}
            yield self.event(self.rows[2])
            yield self.event(self.rows[2])
        self.api.kernels_logs_stream.side_effect = [first(), second()]
        with tempfile.TemporaryDirectory() as directory:
            result = self.coordinate(evidence=directory)
            content = ''.join(p.read_text() for p in Path(directory).glob('*.json'))
            self.assertNotIn('SYNTHETIC_PRIVATE_SECRET_URL', content)
            self.assertIn('ChunkedEncodingError', content)
        self.assertEqual(result['permits'], list(c.PHASES))
        self.assertEqual(list(self.records), ['launch', 'load', 'campaign-call', 'call'])
        self.assertEqual(self.api.kernels_logs_stream.call_count, 2)
        self.api.kernels_push.assert_not_called()

    def test_read_timeout_reconnect_has_finite_budget_and_no_permit(self):
        from requests.exceptions import ReadTimeout
        self.api.kernels_logs_stream.side_effect = ReadTimeout('SYNTHETIC')
        with self.assertRaisesRegex(ValueError, 'TRANSPORT_ERROR'):
            self.coordinate(seconds=8)
        self.assertEqual(self.api.kernels_logs_stream.call_count, 4)
        self.assertEqual(self.records, {})

    def test_early_eof_does_not_mean_success(self):
        self.api.kernels_status.return_value.status = 'RUNNING'
        self.api.kernels_logs_stream.side_effect = lambda *a: iter([])
        with self.assertRaisesRegex(ValueError, 'TRANSPORT_ERROR'):
            self.coordinate(seconds=8)
        self.assertEqual(self.api.kernels_logs_stream.call_count, 4)

    def test_deadline_cannot_issue_late_permit(self):
        def delayed():
            time.sleep(.15)
            yield self.event(self.rows[0])
        self.api.kernels_logs_stream.return_value = delayed()
        with self.assertRaisesRegex(TimeoutError, 'DEADLINE'):
            self.coordinate(seconds=.02)
        time.sleep(.2)
        self.assertEqual(self.records, {})

    def test_wrong_nonce_order_binding_and_schema_cannot_issue_call(self):
        for bad in ({**self.rows[0], 'nonce': 'BAD'}, self.rows[1],
                    {**self.rows[0], 'binding': 'f' * 64}, {**self.rows[0], 'extra': 1}):
            self.api.kernels_logs_stream.return_value = iter([self.event(bad)])
            with self.assertRaises(ValueError):
                self.coordinate()
            self.assertEqual(self.records, {})

    def test_cross_job_call_conflict_and_lost_write_stop_before_call_permit(self):
        for failure in (ValueError('CONFLICT'), TimeoutError('UNKNOWN_WRITE')):
            self.records.clear()
            coord = c.Coordinator(self.grant)
            def create(name, value):
                if name == 'campaign-call':
                    raise failure
                self.create(name, value)
            with patch.object(c, 'create_record', side_effect=create):
                coord.accept(self.rows[0]); coord.accept(self.rows[1])
                with self.assertRaises(type(failure)):
                    coord.accept(self.rows[2])
            self.assertNotIn('call', self.records)

    def test_delegated_grant_rejects_changed_science_expiry_identity_and_pseudo_review(self):
        with patch.object(c, 'authority', return_value=self.grant['authority']):
            self.assertEqual(c.delegated_grant(self.grant), self.grant)
            for key, value in [('limits', {**c.LIMITS, 'max_calls': 2}), ('identity', 'v2'),
                ('version', 2), ('expires_unix', self.grant['expires_unix'] + 1),
                ('authorization_kind', 'CHATGPT_HEAD_APPROVED'), ('source_head', 'bad')]:
                with self.assertRaises(ValueError):
                    c.delegated_grant({**self.grant, key: value})

    def test_authority_requires_exact_owner_issue_and_body(self):
        body = 'SYNTHETIC AUTHORITY'
        comment = {'body': body, 'user': {'login': 'tantdna2'}, 'issue_url': c.API + '/issues/175'}
        with patch.object(c, 'AUTHORITY', {1: hashlib.sha256(body.encode()).hexdigest()}):
            with patch.object(c, 'public_get', return_value=comment):
                c.authority()
            for change in ({'body': body + 'edited'}, {'user': {'login': 'other'}}, {'issue_url': 'other'}):
                with patch.object(c, 'public_get', return_value={**comment, **change}), self.assertRaises(ValueError):
                    c.authority()

    def test_campaign_slot_already_present_blocks_predecessor_admission(self):
        with patch.object(c, 'remote_record', return_value=self.rows[2]), self.assertRaisesRegex(ValueError, 'CAMPAIGN_CALL'):
            s.predecessor_history(self.api, Path('unused'))
        self.api.kernels_status.assert_not_called()

    def test_local_authenticated_reads_distinguish_absence_rate_limit_and_unknown(self):
        for status, code in ((200, 0), (404, 1), (403, 1), (429, 1)):
            reply = Mock(returncode=code, stdout='HTTP/2.0 %d status\nContent-Type: application/json\n\n{}' % status)
            with patch.object(s.subprocess, 'run', return_value=reply) as invoke:
                if status == 200:
                    self.assertEqual(s.authenticated_github_get('/synthetic'), {})
                elif status == 404:
                    self.assertIsNone(s.authenticated_github_get('/synthetic', missing=True))
                else:
                    with self.assertRaisesRegex(ValueError, 'READ_HTTP'):
                        s.authenticated_github_get('/synthetic', missing=True)
                self.assertEqual(invoke.call_count, 1)
                self.assertNotIn('token', str(invoke.call_args))
        with patch.object(s.subprocess, 'run', return_value=Mock(stdout='', returncode=1)), self.assertRaisesRegex(ValueError, 'UNKNOWN'):
            s.authenticated_github_get('/synthetic', missing=True)

    def test_actual_installed_sdk_sse_parser_short_event_and_heartbeat(self):
        # Exercise the official parser without authentication/network if installed.
        import importlib.util
        if importlib.util.find_spec('kaggle') is None:
            self.skipTest('official SDK not installed in CPU-only interpreter')
        from kaggle.api.kaggle_api_extended import KaggleApi
        response = Mock()
        response.iter_lines.return_value = iter([': heartbeat', '', 'data: ' + json.dumps(self.event(self.rows[0])),
                                               'data: END_OF_LOG'])
        events = list(KaggleApi._iter_sse_events(KaggleApi(), response))
        self.assertEqual(events, [self.event(self.rows[0])])


if __name__ == '__main__':
    unittest.main()
