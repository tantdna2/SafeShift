"""Documentary boundary checks only: no runtime imports, network or model calls."""

import json
from pathlib import Path, PurePosixPath
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = 'configs/pre_freeze/moondream_prep_audit.v1.json'


class MoondreamPrepAuditTests(unittest.TestCase):
    def setUp(self):
        self.audit = json.loads((ROOT / AUDIT).read_text(encoding='utf-8'))

    def test_pins_agree_with_roster_and_provenance(self):
        for name, collection in [('local_models.d9.json', 'primary_models'),
                                 ('local_model_provenance.d9.json', 'models')]:
            document = json.loads((ROOT / 'configs/pre_freeze' / name).read_text(encoding='utf-8'))
            model = next(m for m in document[collection] if m['key'] == 'moondream2_2025_06_21')
            self.assertEqual(model['immutable_revision'], self.audit['model_revision'])
            self.assertEqual(model['model_id'], self.audit['model_id'])
        self.assertEqual(self.audit['model_revision'], '9a7d4024050840e001defacec2b00727e89149e6')
        self.assertEqual(self.audit['tokenizer_revision'], '35192e10a54e36eabe0a7cc57a2c1aab371cafc5')

    def test_artifact_identity_and_evidence_are_unambiguous(self):
        identities = set()
        for row in self.audit['artifacts']:
            identity = row['repo_id'], row['revision'], row['path']
            self.assertNotIn(identity, identities)
            identities.add(identity)
            self.assertRegex(row['revision'], r'\A[0-9a-f]{40}\Z')
            self.assertRegex(row['sha256'], r'\A[0-9a-f]{64}\Z')
            self.assertGreater(row['size_bytes'], 0)
            path = PurePosixPath(row['path'])
            self.assertFalse(path.is_absolute())
            self.assertNotIn('..', path.parts)
            if row['verification'] == 'LOCAL_BYTES_AND_PINNED_API_GIT_BLOB':
                self.assertIn('/' + row['revision'] + '/', row['source_url'])
                self.assertRegex(row['git_blob_sha1'], r'\A[0-9a-f]{40}\Z')
            else:
                self.assertEqual(row['path'], 'model.safetensors')
                self.assertEqual(row['verification'], 'PINNED_API_LFS_METADATA_ONLY_NOT_DOWNLOADED')
        source_names = {r['path'] for r in self.audit['artifacts']
                        if r['repo_id'] == self.audit['model_id'] and r['path'].endswith('.py')}
        self.assertEqual(source_names, set(self.audit['remote_code_files_audited']))

    def test_required_tokenizer_bytes_are_pinned_separately(self):
        rows = {r['path']: r for r in self.audit['artifacts']
                if r['repo_id'] == 'moondream/starmie-v1'}
        tokenizer = rows['tokenizer.json']
        self.assertEqual(tokenizer['sha256'], '0512fdcac4a5f9e7746cbefce4a468dc93bf0f93f11e701b84f8b31bff199e9c')
        self.assertEqual(tokenizer['size_bytes'], 3694206)
        self.assertEqual({r['revision'] for r in rows.values()}, {self.audit['tokenizer_revision']})
        self.assertTrue({'tokenizer_config.json', 'special_tokens_map.json'} <= rows.keys())

    def test_stop_cannot_be_reported_as_runtime_or_grounding_pass(self):
        self.assertTrue(self.audit['status'].startswith('STOP_'))
        self.assertEqual(self.audit['runner_status'], 'PENDING')
        self.assertEqual(self.audit['tokenizer_runtime_enforcement'], 'NOT_IMPLEMENTED')
        self.assertEqual(self.audit['fp16_plan_status'], 'NOT_FROZEN_STOP_REQUIRED')
        self.assertEqual(self.audit['resource_status'], 'T4_FEASIBILITY_CANDIDATE')
        self.assertEqual(self.audit['grounding'], 'DOCUMENTED_NATIVE_DETECT_AND_POINT_PENDING_SYNTHETIC_GATE')
        self.assertEqual(self.audit['protocol_freeze_commit_sha'], 'PENDING')
        for key in ('runner_path', 'provisioner_path', 'smoke_harness_path'):
            self.assertIsNone(self.audit[key])
        for key in ('gpu_used', 'model_inference_used', 'weights_downloaded',
                    'remote_code_executed', 'remote_code_changed', 'synthetic_gate_run', 'inspecsafe_used'):
            self.assertIs(self.audit[key], False)

    def test_spatial_contract_keeps_unclamped_boxes_and_separate_points(self):
        detect = self.audit['detect_contract']
        self.assertLess(detect['corner_range'][0], 0)
        self.assertGreater(detect['corner_range'][1], 1)
        self.assertEqual(detect['origin'], 'NOT_EXPLICITLY_DECLARED_IN_PINNED_SOURCE')
        self.assertEqual(detect['runtime_determinism'], 'NOT_VERIFIED')
        self.assertEqual(self.audit['point_contract']['point_to_box'], 'FORBIDDEN')

    def test_evidence_does_not_embed_credentials_or_personal_paths(self):
        text = json.dumps(self.audit)
        self.assertIsNone(re.search(r'(?<![A-Za-z])[A-Za-z]:[\\/]|Bearer |hf_[A-Za-z0-9]{20,}', text))
        for row in self.audit['metadata_responses']:
            self.assertTrue(row['url'].startswith('https://'))
            self.assertNotIn('token=', row['url'])
        condition = self.audit['required_resource_condition']
        self.assertEqual((condition['precision'], condition['quantization'], condition['batch_size']),
                         ('FP16', 'NONE', 1))
        for name in ('cpu_offload', 'disk_offload', 'automatic_precision_fallback',
                     'automatic_quantization_fallback'):
            self.assertEqual(condition[name], 'FORBIDDEN')


if __name__ == '__main__':
    unittest.main()
