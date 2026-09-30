"""Offline audit-record consistency checks; never loads model or runtime evidence."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/pre_freeze'
RAW = [
    ('A_1', 'SCHEMA_ERROR', 'c77df4ad026fd07af11638c3d8617906b37e17c19628007ac2ec9ba6dae75851'),
    ('A_2', 'JSON_ERROR', '6ab96fea8e6abbb060872b3de5aa71567411cda556b687ad0f4f2b3fafb18888'),
    ('B_1', 'SCHEMA_ERROR', '08a441cd5a173da47c00beeac6c32cb1f1ce3927467153303c5b0697f35d5fa1'),
    ('B_2', 'JSON_ERROR', '9e38dbc9ad8d06b80475943a329f35142201e46bc420cb5c22ae076d62a56080'),
    ('C_1', 'JSON_ERROR', '41b1b6fbb03ebe910aef8ef552a011da74b6658cf85d416485d1bc37c43c0471'),
    ('C_2', 'JSON_ERROR', '1feeceda5ba1f871151088af199ae74e9325ffe02b2fa0f4c8274af858b65789'),
    ('D_1', 'JSON_ERROR', 'bbc6d467073508af50582fc418fc9a606794eab15bf71c4d38141e11118fb4a4'),
    ('D_2', 'JSON_ERROR', '202c6273e260755862501c2e06f464a211b461ec6fe99e371a09a873f19e1203'),
]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class ExternalGateResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(CONFIG / 'qwen2_5_external_gate_result.v1.json')
        cls.roster = load(CONFIG / 'local_models.d9.json')
        cls.model = next(m for m in cls.roster['primary_models'] if m['key'] == 'qwen2_5_vl_3b_instruct')

    def test_audited_identity_and_hashes(self):
        r = self.result
        self.assertEqual(r['record_kind'], 'RESEARCH_LEAD_AUDITED_REAL_GATE_RESULT')
        self.assertEqual(r['source']['bundle_inspected_and_rehashed_by'], 'RESEARCH_LEAD')
        self.assertIs(r['source']['bundle_and_raw_bytes_committed'], False)
        self.assertEqual(r['run_id'], 'kaggle-t4-qwen25-external-gate-20260925T092550Z-c1c1d8')
        self.assertEqual(r['execution_commit'], 'c08fe8420fe0189b8776741eaa5cc2fb945a77fa')
        self.assertEqual(r['bundle_sha256'], '1cea70eaa173efeb594a5c5159b7661362d45fe1f87007b51a9957d16643e6e8')
        self.assertEqual(r['summary_sha256'], 'bf2b4a96d9cfb1fb4a89972c155cf0f026f0d213d61c9e4ee9be1144e6ed7155')
        self.assertEqual(r['model_id'], self.model['model_id'])
        self.assertEqual(r['model_revision'], self.model['immutable_revision'])

    def test_completed_gate_failure_is_not_execution_or_resource_failure(self):
        r = self.result
        self.assertEqual(r['status'], 'GATE_FAIL')
        self.assertEqual(r['automatic_gate_status'], 'FAIL')
        self.assertEqual(r['execution_status'], 'COMPLETED')
        self.assertEqual(r['native_generate_calls'], 8)
        self.assertEqual(r['native_errors'], [])
        self.assertEqual(r['not_attempted_case_ids'], [])
        self.assertEqual(r['execution_failure'], 'NONE')
        self.assertEqual(r['oom_status'], 'NOT_OBSERVED')
        self.assertIs(r['systematic_tracking'], False)
        self.assertEqual(r['gate_errors'], ['predictions do not track systematic target positions'])

    def test_exact_case_results_and_raw_hashes(self):
        cases = self.result['cases']
        self.assertEqual([(c['case_id'], c['parse_status'], c['raw_sha256']) for c in cases], RAW)
        counts = Counter(c['parse_status'] for c in cases)
        self.assertEqual(counts, {'SCHEMA_ERROR': 2, 'JSON_ERROR': 6})
        for field, status in [('strict_success_count', 'SUCCESS'), ('schema_error_count', 'SCHEMA_ERROR'),
                              ('json_error_count', 'JSON_ERROR')]:
            self.assertEqual(self.result[field], counts[status])
        self.assertEqual(self.result['canonical_parsed_bbox_count'], 0)
        for c in cases:
            self.assertRegex(c['raw_sha256'], r'\A[0-9a-f]{64}\Z')
            self.assertNotIn('bbox', c)

    def test_roster_policy_grounding_only_nonparticipation(self):
        r, m = self.result, self.model
        self.assertEqual(m['grounding'], r['grounding_role'])
        self.assertEqual(r['grounding_role'], 'NOT_PARTICIPATING')
        self.assertEqual(m['grounding_failure_reason'], 'SPATIAL_GATE_FAILURE')
        self.assertEqual(r['grounding_failure_reason'], m['grounding_failure_reason'])
        self.assertEqual(m['external_gate_status'], 'GATE_FAIL')
        self.assertEqual(load(ROOT / m['external_gate_evidence']), r)
        for record in (r, m):
            self.assertIs(record['backup_substitution'], False)
            self.assertIs(record['artificial_zero_iou'], False)
            self.assertEqual(record['resource_status'], 'PASS_VALIDATED')
        self.assertEqual(m['classification'], 'CANDIDATE')
        self.assertEqual(r['classification_status'], 'CANDIDATE')
        policy = self.roster['replacement_policy']['on_grounding_only_failure_with_valid_parseable_classification']
        self.assertIn(r['grounding_failure_reason'], policy['includes'])
        self.assertEqual(r['grounding_role'], policy['grounding_role'])
        self.assertIs(policy['activate_backup_substitution'], False)
        self.assertIs(policy['assign_artificial_zero_iou'], False)

    def test_no_giant_review_fabricated_and_no_posthoc_changes(self):
        self.assertEqual(self.result['giant_box_review_status'], 'NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE')
        self.assertEqual(self.result['giant_box_reviews'], [])
        self.assertIs(self.result['post_hoc_changes'], False)
        self.assertIs(self.result['rerun_performed_by_recording_task'], False)
        self.assertEqual(self.result['approved_interpretation'],
            'Qwen2.5 failed the frozen SafeShift qualifying box-interface external gate under the pre-specified prompt, decoding and strict parser.')

    def test_gate_runtime_plan_prompt_decoding_unchanged(self):
        r = self.result
        for path_key, hash_key, expected in (
            ('gate_plan_path', 'gate_plan_sha256', 'd7e09c1400e23a534b97e91aa432d87108ece137ff60f8a918e3c0f977f2bb4b'),
            ('runtime_plan_path', 'runtime_plan_sha256', 'aa4fcff85d670d844025a540d85f10514919c60f6709de8be8f6be0922fd63fb')):
            self.assertEqual(r[hash_key], expected)
            self.assertEqual(canonical_sha(load(ROOT / r[path_key])), expected)
        plan = load(ROOT / r['gate_plan_path'])
        runtime = load(ROOT / r['runtime_plan_path'])
        self.assertEqual(r['decoding'], {'do_sample': False, 'max_new_tokens': 32})
        self.assertEqual(r['decoding'], plan['decoding'])
        self.assertEqual(r['decoding'], runtime['smoke']['decoding'])
        self.assertEqual(r['prompt_version'], plan['prompt_version'])
        for path, expected in plan['protected_source_sha256_lf'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest(), expected)

    def test_frozen_suite_preserved(self):
        r = self.result
        for path_key, hash_key, expected in (
            ('manifest_path', 'manifest_sha256', 'fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379'),
            ('provenance_path', 'provenance_sha256', '0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96')):
            self.assertEqual(r[hash_key], expected)
            self.assertEqual(hashlib.sha256((ROOT / r[path_key]).read_bytes()).hexdigest(), expected)
        for image in load(ROOT / r['provenance_path'])['images']:
            self.assertEqual(hashlib.sha256((ROOT / image['image_path']).read_bytes()).hexdigest(), image['sha256'])

    def test_global_checklist_and_inspecsafe_still_pending_unauthorized(self):
        self.assertEqual(self.roster['synthetic_gate']['status'], 'RESOLVED_CAPABILITY_AWARE')
        self.assertEqual(self.result['global_d9_synthetic_gate_status'], 'PENDING')
        completed = {'1_model_revisions_and_license_provenance',
                     '2_local_self_hosted_runners',
                     '5_synthetic_gate_primary_models'}
        for key, value in self.roster['d9_checklist'].items():
            self.assertEqual(value, 'COMPLETE' if key in completed else 'PENDING')
        for record in (self.result, self.roster):
            self.assertEqual(record['protocol_freeze_commit_sha'], 'PENDING')
            self.assertIs(record['inspecsafe_inference_authorized'], False)
        self.assertIs(self.result['inspecsafe_used'], False)
        self.assertEqual(self.result['inspecsafe_status'], 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
