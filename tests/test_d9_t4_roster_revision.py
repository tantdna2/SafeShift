"""Offline D9R1 decision/provenance regressions; no model or network calls."""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/pre_freeze'
REASON = 'PRE_FREEZE_RESOURCE_CONSTRAINT'
PRIMARY = [
    ('qwen3_vl_8b_instruct', 'Qwen/Qwen3-VL-8B-Instruct', '0c351dd01ed87e9c1b53cbc748cba10e6187ff3b'),
    ('qwen2_5_vl_3b_instruct', 'Qwen/Qwen2.5-VL-3B-Instruct', '66285546d2b821cf421d4f5eb2576359d3770cd3'),
    ('internvl3_2b_hf', 'OpenGVLab/InternVL3-2B-hf', 'cb57a075cb75a2e6d1b668b128d48bb00ae321d2'),
    ('moondream2_2025_06_21', 'vikhyatk/moondream2', '9a7d4024050840e001defacec2b00727e89149e6'),
]
BACKUPS = [
    ('paligemma_3b_mix_448', 'google/paligemma-3b-mix-448', 'ead2d9a35598cb89119af004f5d023b311d1c4a1'),
    ('smolvlm2_2_2b_instruct', 'HuggingFaceTB/SmolVLM2-2.2B-Instruct', '482adb537c021c86670beed01cd58990d01e72e4'),
]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def walk(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key, item
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


class D9T4RosterRevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load(CONFIG / 'local_models.d9.json')
        cls.provenance = load(CONFIG / 'local_model_provenance.d9.json')
        cls.freeze = load(CONFIG / 'freeze_manifest.d9.template.json')
        cls.fixture = load(ROOT / 'tests/fixtures/d9r1_protected_files.json')
        cls.primary = cls.roster['primary_models']
        cls.backups = cls.roster['backups_in_order']
        cls.active = cls.primary + cls.backups
        cls.by_key = {m['key']: m for m in cls.provenance['models']}
        cls.retired = cls.roster['retired_primary_models']

    def test_01_primary_exactly_four(self):
        self.assertEqual(len(self.primary), 4)

    def test_02_anchor_identity_revision_role_unchanged(self):
        m = self.primary[0]
        self.assertEqual((m['key'], m['model_id'], m['immutable_revision']), PRIMARY[0])
        self.assertEqual(m['role'], 'ANCHOR_REPRODUCTION_BRIDGE')
        self.assertEqual(m['resource_role'], 'KAGGLE_T4X2_VALIDATED_ANCHOR')

    def test_03_new_primary_identities_and_pins_exact(self):
        self.assertEqual([(m['key'], m['model_id'], m['immutable_revision']) for m in self.primary], PRIMARY)

    def test_04_all_active_revisions_full_hex(self):
        for m in self.active:
            self.assertRegex(m['immutable_revision'], r'\A[0-9a-f]{40}\Z')

    def test_05_all_active_provenance_matches(self):
        for m in self.active:
            p = self.by_key[m['provenance_key']]
            self.assertEqual(p['model_id'], m['model_id'])
            self.assertEqual(p['immutable_revision'], m['immutable_revision'])
        revision = self.provenance['roster_revision']
        self.assertEqual(revision['active_primary_keys'], [m['key'] for m in self.primary])
        self.assertEqual(revision['active_backup_keys'], [m['key'] for m in self.backups])

    def test_06_no_duplicate_ids_or_keys(self):
        for records in (self.active, self.provenance['models']):
            for field in ('key', 'model_id'):
                self.assertEqual(len(records), len({m[field] for m in records}))

    def test_07_resource_status_tracks_recorded_runtime_evidence(self):
        for m in self.primary[1:]:
            self.assertEqual(m['classification'], 'CANDIDATE')
            expected = 'PASS_VALIDATED' if m['key'] == PRIMARY[1][0] else 'T4_FEASIBILITY_CANDIDATE'
            self.assertEqual(m['resource_status'], expected)
            self.assertEqual(m['target_validation'], ['COLAB_T4_1X16GB_PRIMARY', 'KAGGLE_T4_FALLBACK_ALLOWED'])

    def test_08_documentary_history_and_unqualified_models_not_promoted(self):
        for m in self.active[1:]:
            p = self.by_key[m['key']]
            # Documentary snapshot remains historical; current runtime evidence
            # is separately linked by the roster, as for the Qwen3 anchor.
            self.assertFalse(p['runtime_validated'])
            self.assertEqual(p['t4_status'], 'FEASIBILITY_CANDIDATE')
            qualified = m['key'] == PRIMARY[1][0]
            self.assertEqual(m['runtime_smoke_status'], 'PASS_VALIDATED' if qualified else 'PENDING')
            for _, value in walk([p] if qualified else [m, p]):
                if isinstance(value, str):
                    self.assertNotIn(value, {'T4_VALIDATED', 'COLAB_VALIDATED', 'KAGGLE_VALIDATED', 'PASS_VALIDATED'})

    def test_09_retired_ovis_preserves_runtime_and_identity(self):
        m = self.retired[0]
        self.assertEqual(m['model_id'], 'AIDC-AI/Ovis2.5-9B')
        self.assertEqual(m['immutable_revision'], 'd73b2283ae2a930b7762f8d7b8b8a3f0f3b5c3bd')
        self.assertEqual(m['historical_offline_runner_status'], 'COMPLETE')
        self.assertEqual(m['historical_runtime_smoke_status'], 'PASS_VALIDATED')

    def test_10_retired_molmo_preserves_runner_and_not_run(self):
        m = self.retired[1]
        self.assertEqual(m['model_id'], 'allenai/Molmo2-O-7B')
        self.assertEqual(m['immutable_revision'], '784410650d12be9bc086118fdefa32d2c3bced86')
        self.assertEqual(m['historical_offline_runner_status'], 'COMPLETE')
        self.assertEqual(m['historical_runtime_smoke_status'], 'NOT_RUN')
        self.assertEqual(m['historical_b3b_prep']['status'], 'OPEN_DRAFT_UNMERGED_UNTOUCHED')

    def test_11_retired_gemma_before_implementation(self):
        m = self.retired[2]
        self.assertEqual(m['model_id'], 'google/gemma-4-12B-it')
        self.assertEqual(m['immutable_revision'], '707f0a3b8a3c7ad586ed01e27eafbad8a27dd0f7')
        self.assertEqual(m['historical_offline_runner_status'], 'NOT_COMPLETED')
        self.assertEqual(m['historical_runtime_smoke_status'], 'NOT_RUN')

    def test_12_retirement_reason_and_history_explicit(self):
        for m in self.retired + self.roster['retired_backups']:
            self.assertEqual(m['status'], 'RETIRED_PRE_FREEZE')
            self.assertEqual(m['reason'], REASON)
            self.assertIs(m['replacement_selection_used_inspecsafe_results'], False)
            self.assertIs(m['current_primary'], False)
            self.assertTrue(m['code_and_evidence_preserved'])
            self.assertTrue(m['historical_grounding_documentary_status'])
            self.assertNotIn(m['model_id'], [a['model_id'] for a in self.active])

    def test_13_old_backups_preserved(self):
        self.assertEqual([(m['model_id'], m['immutable_revision']) for m in self.roster['retired_backups']], [
            ('google/paligemma2-10b-mix-448', 'b26d16fb4251090ba4a4aa5af9fca1f8248ed5b6'),
            ('openbmb/MiniCPM-V-4.6', '36f34a661a4bd35d0dc2294cb044d2584646c7d3')])

    def test_14_new_backups_exact_order(self):
        self.assertEqual([(m['key'], m['model_id'], m['immutable_revision']) for m in self.backups], BACKUPS)
        self.assertEqual([m['replacement_status'] for m in self.backups], ['BACKUP_1_ONLY', 'BACKUP_2_ONLY'])

    def test_15_backup_pins_and_candidate_status(self):
        for m in self.backups:
            self.assertRegex(m['immutable_revision'], r'\A[0-9a-f]{40}\Z')
            self.assertEqual(m['status'], 'T4_FEASIBILITY_CANDIDATE')
            self.assertEqual(m['classification'], 'CANDIDATE')

    def test_16_no_inspecsafe_selection_or_performance(self):
        for c in (self.roster, self.freeze, self.provenance['roster_revision']):
            self.assertIs(c['inspecsafe_performance_used'], False)
            self.assertTrue(c['roster_revision_before_protocol_freeze'])
            self.assertTrue(c['roster_revision_before_inspecsafe'])
            self.assertEqual(c['roster_revision_reason'], REASON)
        for key, value in walk([self.roster, self.provenance, self.freeze]):
            if key in {'inspecsafe_performance_used', 'inspecsafe_used', 'replacement_selection_used_inspecsafe_results'}:
                self.assertIs(value, False)

    def test_17_protocol_and_component_freeze_pending(self):
        for c in (self.roster, self.provenance, self.freeze):
            self.assertEqual(c['protocol_freeze_commit_sha'], 'PENDING')
        self.assertTrue(all(v == 'PENDING' for v in self.freeze['frozen_components'].values()))
        for m in self.freeze['primary_models']:
            for field in ('decoding_policy_id', 'precision_or_quantization', 'preprocessing_id'):
                self.assertEqual(m[field], 'PENDING')

    def test_18_inspecsafe_inference_unauthorized(self):
        for c in (self.roster, self.provenance, self.freeze):
            self.assertIs(c['inspecsafe_inference_authorized'], False)

    def test_19_d5_and_p1_protocol_unchanged(self):
        self.assertEqual(digest(self.roster['preserved_protocol']), self.fixture['preserved_protocol_sha256'])
        self.assertEqual(digest(self.freeze['p1_policy']), self.fixture['p1_policy_sha256'])
        for path in ('notes/w2_metrics_statistics_decision_brief.md', 'notes/w2_protocol_decision_brief.md'):
            self.assertProtected(path)

    def assertProtected(self, path):
        content = (ROOT / path).read_bytes()
        # Compare Git blob content across Windows autocrlf and LF checkouts.
        # Binary images are never normalized; census has its own raw-byte check.
        if Path(path).suffix in {'.py', '.json', '.md', '.txt'} or Path(path).name == '.gitkeep':
            content = content.replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(content).hexdigest(),
                         self.fixture['protected_file_sha256'][path], path)

    def test_20_synthetic_manifest_and_assets_unchanged(self):
        for c, key in ((self.roster, 'synthetic_gate'), (self.freeze, 'synthetic_external_gate')):
            gate = c[key]
            self.assertEqual(gate['manifest_sha256'], 'fcd6ca6205e769626fb7db702474a485796e57415601b39025bcc112b0e8a379')
            self.assertProtected(gate['manifest'])
        for path in self.fixture['protected_file_sha256']:
            if path.startswith('tests/fixtures/pre_freeze/'):
                self.assertProtected(path)

    def test_21_historical_runtime_code_config_and_evidence_unchanged(self):
        for path in self.fixture['protected_file_sha256']:
            with self.subTest(path=path):
                self.assertProtected(path)
        self.assertEqual(digest(self.provenance['models'][:6]), self.fixture['historical_provenance_sha256'])

    def test_22_pr28_prep_files_not_imported(self):
        # Live PR state is documentary evidence, not queried by offline tests.
        for path in ('configs/pre_freeze/molmo_gpu_smoke.v1.json',
                     'notes/w2_molmo_gpu_smoke_runbook.md',
                     'scripts/provision_molmo2_o_snapshot.py', 'scripts/w2_molmo_gpu_smoke.py',
                     'tests/test_molmo_gpu_smoke_harness.py'):
            self.assertFalse((ROOT / path).exists(), path)

    def test_23_only_explicitly_authorized_post_d9r1_runner_source(self):
        # D9R1's no-runner boundary applied to that decision PR. D9R2A/B-PREP/INIT-DIAG
        # authorize these sources; all historical protected blob hashes stay fixed.
        authorized = {'safeshift/runners/qwen2_5_vl.py',
                      'scripts/provision_qwen2_5_snapshot.py',
                      'scripts/w2_qwen2_5_t4_smoke.py',
                      'scripts/w2_qwen2_5_t4_init_probe.py'}
        authorized.add('scripts/w2_qwen2_5_external_gate.py')
        # D9R2D authorizes only the separate Qwen3 external gate PREP harness.
        authorized.add('scripts/w2_qwen3_external_gate.py')
        for directory in self.fixture['source_roots']:
            expected = {p for p in self.fixture['protected_file_sha256'] if p.startswith(directory + '/') and p.endswith('.py')}
            expected |= {p for p in authorized if p.startswith(directory + '/')}
            observed = {p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*.py')}
            self.assertEqual(observed, expected)

    def test_24_resource_policy_forbids_silent_fallbacks(self):
        p = self.roster['resource_qualification_policy']
        self.assertEqual(p, self.freeze['resource_qualification_policy'])
        for k, v in {'gpu_target': 'SINGLE_NVIDIA_T4_16GB', 'precision_candidate': 'FP16',
                     'quantization': 'NONE', 'batch_size': 1,
                     'cpu_offload': 'FORBIDDEN_FOR_PRIMARY_T4_QUALIFICATION',
                     'disk_offload': 'FORBIDDEN_FOR_PRIMARY_T4_QUALIFICATION',
                     'automatic_precision_fallback': 'FORBIDDEN',
                     'automatic_quantization_fallback': 'FORBIDDEN',
                     'model_substitution_after_inspecsafe': 'FORBIDDEN', 'failure_reason': REASON}.items():
            self.assertEqual(p[k], v)
        self.assertIs(self.roster['paid_gpu_required_by_policy'], False)
        self.assertNotIn('rented_gpu_host', self.roster['execution_policy']['allowed_venues'])
        self.assertEqual(p['anchor_exception']['key'], PRIMARY[0][0])
        self.assertTrue(p['failure_requires_prespecified_smoke_evidence'])

    def test_25_qwen_license_and_grounding_not_upgraded(self):
        p = self.by_key[PRIMARY[1][0]]
        self.assertEqual(p['license_access']['repository_license'], 'Qwen Research License')
        self.assertIn('DOCUMENTED_BOX_AND_POINT', p['spatial']['status'])
        self.assertEqual(p['spatial']['d5_box_qualification'], 'NOT_YET_QUALIFIED')
        resolution = p['required_files_resolution']['results']
        self.assertEqual(len(resolution), 13)
        self.assertTrue(all(r['http_status'] == 200 and r['method'] == 'HEAD' and not r['body_downloaded'] for r in resolution))

    def test_26_internvl_license_complexity_and_no_grounding_promotion(self):
        p = self.by_key[PRIMARY[2][0]]
        self.assertIn('MIT project + Qwen component', p['license_access']['repository_license'])
        self.assertEqual(p['spatial']['status'], 'NOT_YET_DOCUMENTARILY_QUALIFIED')

    def test_27_moondream_release_api_and_grounding_not_gate_pass(self):
        p = self.by_key[PRIMARY[3][0]]
        self.assertEqual(p['release_tag_resolution']['tag'], '2025-06-21')
        self.assertEqual(p['release_tag_resolution']['immutable_revision'], PRIMARY[3][2])
        self.assertEqual(p['license_access']['repository_license'], 'apache-2.0')
        for api in ('model.detect', 'model.point'):
            self.assertIn(api, p['runtime']['documented_loader_api'])
        self.assertEqual(p['spatial']['d5_box_qualification'], 'NOT_YET_QUALIFIED')

    def test_28_backup_license_access_and_metadata(self):
        pali, smol = [self.by_key[m['key']] for m in self.backups]
        self.assertEqual(pali['license_access']['repository_license'], 'gemma')
        self.assertEqual(pali['license_access']['access_status'], 'GATED_USAGE_TERMS_ACCEPTANCE_REQUIRED')
        self.assertEqual(pali['license_access']['owner_acceptance_status'], 'NOT_VERIFIED')
        self.assertEqual(smol['license_access']['repository_license'], 'apache-2.0')
        self.assertEqual(smol['weight_provenance']['published_parameter_count'], 2246784880)
        self.assertEqual(smol['spatial']['status'], 'NOT_YET_DOCUMENTARILY_QUALIFIED')

    def test_29_provenance_required_fields_and_documentary_sources(self):
        sources = self.provenance['sources']
        for m in self.active[1:]:
            p = self.by_key[m['key']]
            for field in ('model_id', 'resolved_repository_id', 'immutable_revision', 'revision_resolution_source',
                          'revision_resolution_timestamp_utc', 'model_card_url', 'files_tree_url'):
                self.assertTrue(p[field])
            when = datetime.fromisoformat(p['revision_resolution_timestamp_utc'])
            self.assertEqual(when.utcoffset().total_seconds(), 0)
            for field in ('model_card_url', 'files_tree_url'):
                self.assertIn(p['immutable_revision'], p[field])
            for field in ('local_weight_bytes_verified', 'downloaded', 'runtime_validated', 'inspecsafe_used'):
                self.assertIs(p[field], False)
            for section in ('license_access', 'runtime', 'precision_quantization', 'spatial', 'weight_provenance'):
                self.assertTrue(p[section]['evidence'])
                for ref in p[section]['evidence']:
                    self.assertIn(ref, sources)
                    self.assertRegex(sources[ref]['response_sha256'], r'\A[0-9a-f]{64}\Z')
            weights = p['weight_provenance']
            self.assertEqual(weights['published_safetensors_size_bytes'], sum(w['size_bytes'] for w in weights['files']))
            for w in weights['files']:
                self.assertGreater(w['size_bytes'], 0)
                self.assertRegex(w['lfs_sha256'], r'\A[0-9a-f]{64}\Z')

    def test_30_freeze_roster_and_checklist_match(self):
        self.assertEqual([(m['provenance_key'], m['model_id'], m['immutable_revision']) for m in self.freeze['primary_models']], PRIMARY)
        self.assertEqual([(m['provenance_key'], m['model_id'], m['immutable_revision']) for m in self.freeze['backups_in_order']], BACKUPS)
        for key, status in self.roster['d9_checklist'].items():
            self.assertEqual(status, 'COMPLETE' if key.startswith('1_') else 'PENDING')
        self.assertEqual(self.roster['decision_id'], 'DEC-W2-D9-009')

    def test_31_grounding_only_failure_cannot_substitute(self):
        p = self.roster['replacement_policy']['on_grounding_only_failure_with_valid_parseable_classification']
        self.assertEqual(p['classification_participation'], 'MUST_CONTINUE')
        self.assertIs(p['activate_backup_substitution'], False)
        self.assertIs(p['assign_artificial_zero_iou'], False)

    def test_qwen25_recorded_single_t4_pass_has_bounded_evidence(self):
        m = self.primary[1]
        evidence = load(ROOT / m['runtime_evidence'])
        self.assertEqual(m['offline_runner_status'], 'COMPLETE')
        self.assertEqual(evidence['model_id'], m['model_id'])
        self.assertEqual(evidence['immutable_revision'], m['immutable_revision'])
        self.assertEqual(evidence['run_id'], 'kaggle-t4-qwen25-smoke-after-initfix-20260925T073925Z-bb567e')
        self.assertEqual(evidence['execution_commit'], '3124b1f7c2bd8d2311d1a1db6474950e200a689f')
        self.assertEqual(evidence['source']['evidence_bundle_sha256'],
                         '0b04a616a71aa0b063711f2b403c536b7d096f9c758c31c9ac21709e9583c105')
        self.assertEqual(evidence['plan_sha256'], digest(load(CONFIG / 'qwen2_5_t4_runtime.v1.json')))
        self.assertEqual(evidence['resource_status'], m['resource_status'])
        self.assertEqual(evidence['status'], 'RUNTIME_INTERFACE_PASS')
        self.assertEqual(evidence['validation_scope'], 'RUNTIME_INTERFACE_ONLY')
        self.assertEqual(evidence['validated_for'], 'SINGLE_T4_LOAD_AND_GENERATION_FEASIBILITY')
        self.assertEqual(evidence['not_validated_for'], ['CLASSIFICATION_CAPABILITY', 'GROUNDING_CAPABILITY',
                                                       'SYNTHETIC_CAPABILITY_GATE', 'INSPECSAFE_BENCHMARK_PERFORMANCE'])
        self.assertEqual(evidence['hardware']['visible_gpu_count'], 1)
        self.assertEqual(evidence['hardware']['gpu_name'], 'Tesla T4')
        self.assertEqual(evidence['native_generate_calls'], 2)
        self.assertEqual(evidence['native_errors'], [])
        self.assertIs(evidence['oom_observed'], False)
        self.assertEqual([c['case_id'] for c in evidence['calls']], ['case_01', 'case_02'])
        for c in evidence['calls']:
            self.assertEqual(c['parse_status'], 'INVALID')
            self.assertEqual(c['error'], 'INVALID_CLASSIFICATION_OUTPUT')
            self.assertEqual(c['observed_image_grid_thw'], [[1, 32, 32]])
            self.assertEqual(c['observed_spatial_merge_size'], 2)
            self.assertEqual(c['observed_visual_token_count'], 256)
            self.assertEqual(c['observed_image_token_placeholder_count'], 256)
        shards = self.by_key[m['key']]['weight_provenance']['files']
        self.assertEqual(evidence['snapshot_verification']['files'],
                         [{'path': s['path'], 'sha256': s['lfs_sha256']} for s in shards])
        self.assertEqual(evidence['synthetic_capability_gate_status'], 'PENDING')
        self.assertEqual(evidence['protocol_freeze_commit_sha'], 'PENDING')
        for key in ('inspecsafe_used', 'inspecsafe_inference_authorized', 'synthetic_gate_used'):
            self.assertIs(evidence[key], False)

    def test_32_local_census_hash_when_present(self):
        # Optional local artifact; never required or distributed as a test fixture.
        path = ROOT / 'data/manifests/w2_grounding_census.json'
        if path.exists():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),
                             'cd17c210878bf8b6dc10fcbb036fd1f61ad850bc1f2264cd10deab0aa0f9cdbb')


if __name__ == '__main__':
    unittest.main()
