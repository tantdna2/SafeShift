"""Offline transcription checks for supplied audit findings; no model or gate rerun."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from safeshift.protocol.schema import parse_text

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/pre_freeze'
BASE = '23556cf3f0adc93b76075a3247a18dd4686ff87a'
RAW = [
    ('A_1', 'COORDINATE_ERROR', '5bd761d444af8b1be06b30d5e8f0578f6cbaf4f4c81a0e47857a91f936b3d4c0'),
    ('A_2', 'SUCCESS', '7c75ffc2c84b0136c8188e960f723d37a5fcec1dc4678c75080b05c01f61a17f'),
    ('B_1', 'SUCCESS', 'a32f6b9eec054024c39b98d5fa4275da353c62ed0009f7d68c441f59d9da20ba'),
    ('B_2', 'SUCCESS', 'e26ac220c671515c34e515efed62b97ba24afa5c01a2efc4b37ac0e89e33d3d3'),
    ('C_1', 'SUCCESS', 'b8d3ac63efed597d1def415062516acfb0b322b0aaecb1ad2234785915c0fab2'),
    ('C_2', 'SCHEMA_ERROR', '36ffccbbe2d3ab8569bf3457468608bcab4823a8d9a06224fa0ef8f56e524f05'),
    ('D_1', 'SUCCESS', '89a398d88ebb5029be9a3e55a4d4d8b20e0290cc421522992d9045130e4c7816'),
    ('D_2', 'COORDINATE_ERROR', '07454ca2908026a232b5ddb76e2dbbc2b5f8447d45a0cf032c57aa784c5536e0'),
]
BOXES = {
    'A_2': ([0.5, 0.25, 0.75, 0.75], 0.2),
    'B_1': ([0.37, 0.12, 0.63, 0.38], 0.9245562130177516),
    'B_2': ([0.35, 0.62, 0.65, 0.92], 0.6944444444444443),
    'C_1': ([0.0, 0.0, 0.33, 0.33], 0.3248309178743962),
    'D_1': ([0.44, 0.07, 0.81, 0.25], 0.22750252780586458),
}
TEXT = {
    'A_1': '{"bbox": [36, 125, 168, 468]}',
    'C_2': '{"bbox": [0.5, 0.6, 1.0, 0.9], "label": "yellow triangle"}',
    'D_2': '{"bbox": [36, 537, 260, 771]}',
}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path, lf=False):
    raw = path.read_bytes()
    return hashlib.sha256(raw.replace(b'\r\n', b'\n') if lf else raw).hexdigest()


class Qwen3ExternalGateResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = load(CONFIG / 'qwen3_external_gate_result.v1.json')
        cls.roster = load(CONFIG / 'local_models.d9.json')
        cls.model = next(m for m in cls.roster['primary_models'] if m['key'] == 'qwen3_vl_8b_instruct')

    def test_exact_audit_identity_and_evidence_hashes(self):
        r = self.result
        self.assertEqual(r['record_kind'], 'RESEARCH_LEAD_AUDITED_REAL_GATE_RESULT')
        self.assertEqual(r['source']['bundle_inspected_and_rehashed_by'], 'RESEARCH_LEAD')
        self.assertIn('did not independently inspect or rehash', r['source']['recording_basis'])
        self.assertIs(r['source']['bundle_and_raw_bytes_committed'], False)
        self.assertEqual(r['run_id'], 'kaggle-t4x2-qwen3-external-gate-20260925T175057Z-08fe69')
        self.assertEqual(r['execution_commit'], BASE)
        self.assertEqual(r['bundle_sha256'], '4d7429ef729c22889af7763e6d9b5c3fd753169c51b9d8c0999d81da9a23a97c')
        self.assertEqual(r['summary_sha256'], 'e2f77bebbd5b79674b608f748e5987feec3f0f0381f8aea9be38630db4814f24')
        self.assertEqual(r['model_id'], 'Qwen/Qwen3-VL-8B-Instruct')
        self.assertEqual(r['model_revision'], '0c351dd01ed87e9c1b53cbc748cba10e6187ff3b')

    def test_completed_gate_failure_and_exact_lifecycle(self):
        r = self.result
        for key, expected in {'status': 'GATE_FAIL', 'automatic_gate_status': 'FAIL',
                              'execution_status': 'COMPLETED', 'initialize_calls': 1,
                              'load_calls': 1, 'native_generate_calls': 8, 'native_errors': [],
                              'not_attempted_case_ids': [], 'execution_failure': 'NONE',
                              'runtime_failure': 'NONE', 'resource_failure': 'NONE',
                              'oom_status': 'NOT_OBSERVED'}.items():
            self.assertEqual(r[key], expected)
        self.assertIs(r['systematic_tracking'], False)
        self.assertEqual(r['gate_errors'], ['predictions do not track systematic target positions'])

    def test_exact_eight_statuses_raw_hashes_and_counts(self):
        r = self.result
        self.assertEqual([(c['case_id'], c['parse_status'], c['raw_sha256']) for c in r['cases']], RAW)
        counts = Counter(c['parse_status'] for c in r['cases'])
        self.assertEqual(counts, {'SUCCESS': 5, 'COORDINATE_ERROR': 2, 'SCHEMA_ERROR': 1})
        for key, status in [('strict_success_count', 'SUCCESS'), ('coordinate_error_count', 'COORDINATE_ERROR'),
                            ('schema_error_count', 'SCHEMA_ERROR'), ('json_error_count', 'JSON_ERROR')]:
            self.assertEqual(r[key], counts[status])
        self.assertEqual(r['canonical_parsed_bbox_count'], 5)
        self.assertEqual(sum('parsed_bbox' in c for c in r['cases']), 5)

    def test_exact_valid_boxes_and_diagnostic_geometry(self):
        for case in self.result['cases']:
            if case['case_id'] in BOXES:
                box, iou = BOXES[case['case_id']]
                self.assertEqual(case['parsed_bbox'], box)
                self.assertEqual(case['target_iou_diagnostic'], iou)
                self.assertIs(case['center_in_target'], True)
                self.assertIs(case['excludes_distractor_center'], True)
                # The audit supplied parsed boxes, not decoded strings for successes.
                self.assertNotIn('decoded_for_parser', case)
            else:
                self.assertNotIn('parsed_bbox', case)
                self.assertNotIn('target_iou_diagnostic', case)
        for key in ('iou_usage', 'area_usage'):
            self.assertEqual(self.result[key], 'DIAGNOSTIC_ONLY')
        for key in ('iou_threshold', 'area_threshold'):
            self.assertIsNone(self.result[key])

    def test_exact_failure_text_uses_existing_parser_without_conversion(self):
        self.assertEqual(self.result['parser_boundary'], {
            'convention': 'xyxy_1', 'pre_existing_behavior': 'CLAMP_TO_0_1_THEN_GEOMETRY_VALIDATION',
            'post_hoc_coordinate_conversion': False, 'native_convention_inferred': False,
            'parser_repair': False})
        for case in self.result['cases']:
            if case['case_id'] in TEXT:
                text = TEXT[case['case_id']]
                self.assertEqual(case['decoded_for_parser'], text)
                # Offline parser consistency only; no model, gate replay or alternative convention.
                parsed = parse_text(text, 'external_probe')
                self.assertEqual(parsed.status, case['parse_status'])
                self.assertIsNone(parsed.value)

    def test_grounding_only_role_policy_and_resource_anchor(self):
        r, m = self.result, self.model
        self.assertEqual(r['grounding_role_before'], 'DOC_SUPPORTED_PENDING_SYNTHETIC_GATE')
        self.assertEqual(m['grounding'], r['grounding_role'])
        self.assertEqual(r['grounding_role'], 'NOT_PARTICIPATING')
        self.assertEqual(m['grounding_failure_reason'], 'SPATIAL_GATE_FAILURE')
        self.assertEqual(r['grounding_failure_reason'], m['grounding_failure_reason'])
        self.assertEqual(m['external_gate_status'], 'GATE_FAIL')
        self.assertEqual(m['external_gate_evidence'], 'configs/pre_freeze/qwen3_external_gate_result.v1.json')
        self.assertEqual(load(ROOT / m['external_gate_evidence']), r)
        for record in (r, m):
            self.assertIs(record['backup_substitution'], False)
            self.assertIs(record['artificial_zero_iou'], False)
            self.assertEqual(record['resource_role'], 'KAGGLE_T4X2_VALIDATED_ANCHOR')
        self.assertEqual(m['classification'], 'CANDIDATE')
        self.assertEqual(r['classification_status'], 'CANDIDATE')
        self.assertEqual(m['offline_runner_status'], 'COMPLETE')
        self.assertEqual(m['runtime_smoke_status'], 'PASS_VALIDATED')
        self.assertEqual(m['role'], 'ANCHOR_REPRODUCTION_BRIDGE')
        policy = self.roster['replacement_policy']['on_grounding_only_failure_with_valid_parseable_classification']
        self.assertIn(r['grounding_failure_reason'], policy['includes'])
        self.assertEqual(policy['grounding_role'], r['grounding_role'])
        self.assertEqual(policy['classification_participation'], 'MUST_CONTINUE')
        self.assertIs(policy['activate_backup_substitution'], False)
        self.assertIs(policy['assign_artificial_zero_iou'], False)

    def test_no_review_rerun_or_posthoc_changes_and_bounded_interpretation(self):
        r = self.result
        self.assertEqual(r['giant_box_review_status'], 'NOT_REQUIRED_AFTER_AUTOMATIC_GATE_FAILURE')
        self.assertEqual(r['giant_box_reviews'], [])
        self.assertIs(r['post_hoc_changes'], False)
        self.assertIs(r['rerun_performed_by_recording_task'], False)
        self.assertEqual(r['approved_interpretation'],
            'Qwen3-VL-8B failed the frozen SafeShift qualifying box-interface external gate under the pre-specified prompt, decoding and existing parser.')

    def test_gate_runtime_plans_resource_prompt_decoding_unchanged(self):
        r = self.result
        for path_key, hash_key, expected, lf in (
            ('gate_plan_path', 'gate_plan_sha256', 'c7510570f553f3267e65f751b56193a337d3c370dd5c4db45da4d746711888c4', False),
            ('runtime_plan_path', 'runtime_plan_sha256_lf', 'ecd34ba5a8880458734e26f2bf0932f5f820607c2b9f3233b4e092980bf79ef9', True)):
            self.assertEqual(r[hash_key], expected)
            self.assertEqual(sha(ROOT / r[path_key], lf), expected)
        plan = load(ROOT / r['gate_plan_path'])
        runtime = load(ROOT / r['runtime_plan_path'])
        self.assertEqual(r['decoding'], {'do_sample': False, 'max_new_tokens': 32})
        self.assertEqual(r['decoding'], plan['decoding'])
        self.assertEqual(r['decoding'], runtime['decoding'])
        self.assertEqual(r['prompt_version'], 'external-target-draft-v1')
        self.assertEqual(r['prompt_version'], plan['prompt_version'])
        self.assertEqual(r['resource_condition'], plan['resource_condition'])
        self.assertEqual(r['resource_condition'], {k: runtime[k] for k in r['resource_condition']})

    def test_production_runner_adapter_parser_gate_prompt_and_harness_unchanged(self):
        plan = load(ROOT / self.result['gate_plan_path'])
        for path, expected in plan['protected_source_sha256_lf'].items():
            with self.subTest(path=path):
                if path == 'configs/pre_freeze/local_model_provenance.d9.json':
                    # Historical plan hash remains exact; live membership and
                    # unchanged model/source evidence are checked by D9R15.
                    raw = subprocess.check_output(['git', 'show', BASE + ':' + path], cwd=ROOT)
                    self.assertEqual(hashlib.sha256(raw.replace(b'\r\n', b'\n')).hexdigest(), expected)
                else:
                    self.assertEqual(sha(ROOT / path, lf=True), expected)
        self.assertEqual(sha(ROOT / 'scripts/w2_qwen3_external_gate.py', lf=True),
                         'e3bf1df1418ce37a6bd602cb4d6daad4c40eb8f6e5e787776ff05882fb0d807c')

    def test_frozen_manifest_provenance_and_eight_images_unchanged(self):
        r = self.result
        for path_key, hash_key, expected in (
            ('manifest_path', 'manifest_sha256', 'fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379'),
            ('provenance_path', 'provenance_sha256', '0b16be7408784c35bc3dc1a541f008b8086c4fa250957082a236d71ed3fe2e96')):
            self.assertEqual(r[hash_key], expected)
            self.assertEqual(sha(ROOT / r[path_key]), expected)
        images = load(ROOT / r['provenance_path'])['images']
        self.assertEqual([i['case_id'] for i in images], [c[0] for c in RAW])
        for image in images:
            self.assertEqual(sha(ROOT / image['image_path']), image['sha256'])

    def test_qwen3_grounding_result_preserved_after_later_reconciliation(self):
        before = json.loads(subprocess.check_output(
            ['git', 'show', BASE + ':configs/pre_freeze/local_models.d9.json'], cwd=ROOT))
        model = next(m for m in before['primary_models'] if m['key'] == 'qwen3_vl_8b_instruct')
        model.update(grounding='NOT_PARTICIPATING', grounding_failure_reason='SPATIAL_GATE_FAILURE',
                     external_gate_status='GATE_FAIL',
                     external_gate_evidence='configs/pre_freeze/qwen3_external_gate_result.v1.json',
                     backup_substitution=False, artificial_zero_iou=False)
        # D9R15 adds independent reporting participation without changing results.
        model.update(primary_grounding_participation='NOT_PARTICIPATING',
                     exploratory_grounding_participation='INCLUDED')
        self.assertEqual(self.model, model)

    def test_global_d9_pending_inspecsafe_unauthorized_and_freeze_pending(self):
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

    def test_census_untracked_and_if_present_exact_hash(self):
        path = 'data/manifests/w2_grounding_census.json'
        self.assertEqual(subprocess.check_output(['git', 'ls-files', '--', path], cwd=ROOT), b'')
        if (ROOT / path).exists():
            self.assertEqual(sha(ROOT / path), 'cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb')


if __name__ == '__main__':
    unittest.main()
