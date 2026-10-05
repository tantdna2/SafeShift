"""Offline PREP verification: handcrafted strings, fake backends, no model imports."""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.qualification.d9r20 import parsers as p, runtime as r
from safeshift.qualification.d9r20.backends import NativeBackend
from safeshift.qualification.classification import JSON_PROMPT, load_suite

ROOT = Path(__file__).resolve().parents[1]
CONFIG = r.read(ROOT, r.CONFIG)
PINS = {
    "ovis": ("ATH-MaaS/Ovis2.5-2B", "393c932b2a03e28eb9aaa503e3c4ab3ad384d958"),
    "plamo": ("pfnet/plamo-2.1-2b-vl", "3d32366444f1ab36e5df4bf7a4c0c0bbe2a56027"),
    "kosmos": ("microsoft/kosmos-2-patch14-224", "1f66d913fde5307936383dc9460b12ccb82f2133"),
}
OVIS = "<box>(0.125,0.375),(0.375,0.625)</box>"
KOSMOS = "<object><patch_index_0044><patch_index_0863></object>"


class Contracts(unittest.TestCase):
    def test_exact_identities(self):
        source = r.read(ROOT, r.SOURCES)
        for key, pair in PINS.items():
            c = CONFIG["models"][key]
            self.assertEqual((c["model_id"], c["revision"]), pair)
            self.assertEqual((source["models"][key]["model_id"], source["models"][key]["revision"]), pair)
        self.assertEqual(CONFIG["base_sha"], r.BASE)

    def test_source_manifest(self):
        source = r.read(ROOT, r.SOURCES)
        self.assertFalse(source["weights_downloaded"])
        records = source["official_implementations"] + source["official_author_comments"]
        for key, model in source["models"].items():
            records += model["sources"] + [model["api"]]
            for item in model["sources"]:
                self.assertIn(PINS[key][1], item["url"])
                self.assertLess(item["size_bytes"], 500000)
        for record in records:
            self.assertRegex(record["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(record["access_date"], "2026-10-05")
            self.assertTrue(record["url"].startswith(("https://huggingface.co/", "https://raw.githubusercontent.com/", "https://api.github.com/")))
        self.assertEqual(len(source["official_author_comments"]), 2)

    def test_weight_metadata_only(self):
        source = r.read(ROOT, r.SOURCES)
        expected = {"ovis": 5140960552, "plamo": 11518321192, "kosmos": 6658052808}
        for key, total in expected.items():
            weights = [f for f in source["models"][key]["files"] if f["rfilename"].endswith(".safetensors")]
            self.assertEqual(sum(f["size"] for f in weights), total)
            for item in weights:
                self.assertRegex(item["lfs"]["sha256"], r"^[0-9a-f]{64}$")

    def test_license_access(self):
        self.assertEqual(CONFIG["models"]["ovis"]["license"], "Apache-2.0")
        self.assertEqual(CONFIG["models"]["kosmos"]["license"], "MIT")
        self.assertEqual(CONFIG["models"]["plamo"]["access"], "ACCESS_REQUIRES_OWNER_ACCEPTANCE")
        self.assertTrue(CONFIG["models"]["plamo"]["owner_acceptance_required"])
        self.assertIs(r.read(ROOT, r.SOURCES)["models"]["plamo"]["gated"], False)

    def test_isolation_resource_and_no_promotion(self):
        self.assertEqual(len({c["run_id"] for c in CONFIG["models"].values()}), 3)
        self.assertEqual({c["environment"]["transformers"] for c in CONFIG["models"].values()}, {"4.51.3", "4.57.1"})
        self.assertEqual(CONFIG["resource"], {"gpu": "Tesla T4", "count": 1, "compute_capability": [7, 5],
            "precision": "FP16", "quantization": "NONE", "batch_size": 1,
            "cpu_offload": False, "disk_offload": False, "automatic_fallback": False})
        for c in CONFIG["models"].values():
            self.assertEqual(c["call2"], "CALL2_ORCHESTRATION_BLOCKER")
            self.assertNotIn("PARTICIPATING", c.values())
        self.assertFalse(CONFIG["execution_authorized"])
        self.assertFalse(CONFIG["grounding"]["fan_out_authorized"])
        from safeshift.protocol.schema import HAZARDS
        plan = r.read(ROOT, 'configs/pre_freeze/grounding_interface_qualification_plan.v3.json')
        self.assertEqual([x['hazard_id'] for x in plan['fixed_hazard_query_map']], list(HAZARDS))

    def test_classification_policy_unchanged(self):
        cases = load_suite(ROOT)
        self.assertEqual(len(cases), 8)
        self.assertIn('Return only {"safety_level":"Level01"}', JSON_PROMPT)
        self.assertEqual(CONFIG["classification"]["policy"], "D9R16_UNCHANGED")

    def test_historical_files_and_append_only_logs(self):
        paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", r.BASE], cwd=ROOT, text=True).splitlines()
        changed = set(subprocess.check_output(["git", "diff", "--name-only", r.BASE], cwd=ROOT, text=True).splitlines())
        self.assertFalse((changed & set(paths)) - {"DECISIONS.md", "TASKS.md"})
        for path in ("DECISIONS.md", "TASKS.md"):
            base = subprocess.check_output(["git", "show", f"{r.BASE}:{path}"], cwd=ROOT)
            current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
            self.assertTrue(current.startswith(base.replace(b"\r\n", b"\n")))

    def test_lazy_model_imports(self):
        code = """import builtins
old = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.split('.')[0] in {'torch','transformers','huggingface_hub','mamba_ssm'}:
        raise AssertionError('real model import')
    return old(name, *args, **kwargs)
builtins.__import__ = guarded
import safeshift.qualification.d9r20.runtime
import safeshift.qualification.d9r20.backends
import safeshift.qualification.d9r20.parsers
"""
        subprocess.run([__import__("sys").executable, "-c", code], cwd=ROOT, check=True)


class Parsers(unittest.TestCase):
    def test_classification_strict(self):
        for level in ("Level01", "Level02", "Level03", "Level04"):
            self.assertEqual(p.classification(json.dumps({"safety_level": level})), {"safety_level": level})
        for text in ('```json\n{"safety_level":"Level01"}\n```', 'Level01',
                     '{"safety_level":"level01"}', '{"safety_level":"Level01","x":0}',
                     '{"safety_level":"Level01","safety_level":"Level02"}', 'Answer: {"safety_level":"Level01"}'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.classification(text)

    def test_ovis_bare_ref_multiple(self):
        for text, count in ((OVIS, 1), ('<ref>red square</ref>' + OVIS, 1),
                            ('[' + OVIS + ',\n' + OVIS + ' ]', 2)):
            self.assertEqual(len(p.ovis(text, 'red square')), count)
        self.assertEqual(p.ovis(OVIS, 'red square')[0]['bbox'], [.125, .375, .375, .625])

    def test_ovis_malformed_no_search_or_repair(self):
        for text in ('Text ' + OVIS, OVIS + ' more', OVIS + OVIS, '[' + OVIS + ',]',
                     '[]', '<ref>Red square</ref>' + OVIS, '(0,0),(0.2,0.2)',
                     '<point>(0.1,0.2)</point>', '<box>(0,0),(1,1)</box>', '<box>(0.8,0),(0.2,0.5)</box>'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.ovis(text, 'red square')

    def test_plamo_grammars_and_multiple(self):
        self.assertEqual(p.plamo('[0,0,1,1]', 'crane')[0]['bbox'], [0., 0., 1., 1.])
        self.assertEqual(len(p.plamo('helmet[0,0,0.2,0.3]\nhelmet[0.5,0.6,0.7,0.8]', 'helmet')), 2)

    def test_plamo_no_salvage(self):
        for text in ('Helmet[0,0,1,1]', 'helmet [0,0,1,1]', 'unknown[0,0,1,1]',
                     'helmet[0,0,1,1]\nunknown[0,0,1,1]', '[]', '[[0,0,1,1]]',
                     'Output: [0,0,1,1]', '[0,0,1,1]\nprose', '[false,0,1,1]',
                     '[0,0,NaN,1]', '[-0.1,0,1,1]', '[0,0,1.01,1]', '[0.7,0,0.1,1]'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.plamo(text, 'helmet')

    def test_kosmos_official_example(self):
        self.assertEqual(p.kosmos(KOSMOS, 'snowman')[0]['bbox'], [.390625, .046875, .984375, .828125])

    def test_kosmos_multiple_and_boundaries(self):
        text = '<phrase>snowman</phrase><object><patch_index_0044><patch_index_0863>' + p.MULTI + '<patch_index_0000><patch_index_0000></object>'
        self.assertEqual(len(p.kosmos(text, 'snowman')), 2)
        self.assertEqual(p.patch_box(0, 0), [0, 0, 1/32, 1/32])
        self.assertEqual(p.patch_box(1023, 1023), [31/32, 31/32, 1, 1])
        self.assertEqual(p.patch_box(0, 31), [0, 0, 1, 1/32])
        self.assertEqual(p.patch_box(0, 992), [0, 0, 1/32, 1])

    def test_kosmos_malformed_and_unknown_labels(self):
        for text in (KOSMOS + ' prose', '<phrase>Snowman</phrase>' + KOSMOS, KOSMOS.replace('0044', '1024'),
                     KOSMOS.replace('0044', '0864'), '<object></object>', '<object><patch_index_0044></object>',
                     KOSMOS.replace('0044', '44'), ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                p.kosmos(text, 'snowman')

    def test_coordinate_order_range_no_clamp(self):
        for value in ([1,0,0,1], [0,.8,1,.2], [0,0,0,1], [0,0,1,0], [0,0,float('inf'),1], [False,0,1,1]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.coordinates(value)
        self.assertEqual(p.coordinates([.1,.2,.8,.9]), [.1,.2,.8,.9])

    def test_kosmos_equivalence_to_audited_official_function(self):
        # Extract ONLY the pure official arithmetic function; no Transformers import.
        source = r.read(ROOT, r.SOURCES)
        record = next(x for x in source['official_implementations'] if x['locator'].endswith('processing_kosmos2.py'))
        path = ROOT / record['local_audit_cache']
        if not path.exists():
            self.skipTest('optional downloaded source cache absent; official example/boundaries still tested')
        raw = path.read_bytes()
        self.assertEqual(r.digest(raw), record['sha256'])
        fn = next(x for x in ast.parse(raw).body if isinstance(x, ast.FunctionDef) and x.name == 'patch_index_to_coordinate')
        scope = {}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), '<audited-pure-coordinate-function>', 'exec'), scope)
        for ul in range(1024):
            for lr in (ul, 1023):
                self.assertEqual(p.patch_box(ul, lr), list(scope['patch_index_to_coordinate'](ul, lr, 32)))


class Authority(unittest.TestCase):
    def setUp(self):
        self.c = CONFIG['models']['ovis']
        self.live = {'head': 'a'*40, 'main': 'a'*40, 'base': r.BASE}
        self.obs = {**self.live, 'model': 'ovis', 'model_id': self.c['model_id'], 'revision': self.c['revision'], 'run_id': self.c['run_id']}
        self.auth = {**self.obs, 'execution_authorized': True, 'prep_merged': True, 'observation_sha256': 'b'*64,
                     'research_lead': 'reviewer', 'review_reference': 'external-audit',
                     'scope': 'RESOURCE_SMOKE_AND_SINGLE_TARGET_SYNTHETIC_ONLY'}

    def check(self):
        r.check_authority('ovis', self.c, self.obs, self.auth, self.live, 'b'*64)

    def test_explicit_future_authority(self):
        self.check()

    def test_wrong_revision_head_main_run_id(self):
        for field in ('revision','model_id','model','run_id','head','main','base','observation_sha256'):
            original = self.auth[field]
            self.auth[field] = 'wrong'
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check()
            self.auth[field] = original

    def test_observed_identity_cannot_be_swapped(self):
        self.obs['run_id'] = CONFIG['models']['kosmos']['run_id']
        with self.assertRaises(ValueError):
            self.check()

    def test_unmerged_and_preparation_authority_refused(self):
        for field in ('execution_authorized', 'prep_merged'):
            self.auth[field] = False
            with self.assertRaises(ValueError):
                self.check()
            self.auth[field] = True
        self.auth['scope'] = 'INSPECSAFE'
        with self.assertRaises(ValueError):
            self.check()

    def test_plamo_requires_owner_acceptance_even_public_api(self):
        c = CONFIG['models']['plamo']
        obs = {**self.live, 'model': 'plamo', 'model_id': c['model_id'], 'revision': c['revision'], 'run_id': c['run_id']}
        auth = {**self.auth, **obs}
        with self.assertRaisesRegex(ValueError, 'ACCESS_REQUIRES_OWNER_ACCEPTANCE'):
            r.check_authority('plamo', c, obs, auth, self.live, 'b'*64)
        auth['owner_license_accepted'] = True
        r.check_authority('plamo', c, obs, auth, self.live, 'b'*64)

    def test_network_firewall(self):
        import socket
        with r.offline(), self.assertRaisesRegex(RuntimeError, 'NETWORK_FORBIDDEN'):
            socket.create_connection(('example.invalid', 443))

    def test_path_escape_rejected(self):
        for path in ('../elsewhere', '/absolute', 'data/raw/InspecSafe-V1/foo'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                r.relative(ROOT, path, r.OUTPUT)


class FakeBackend:
    def __init__(self, folder, text='{"safety_level":"Level04"}', fail=None):
        self.folder, self.text, self.fail = folder, text, fail
        self.loads = self.calls = self.decodes = 0

    def load(self):
        self.loads += 1
        if self.fail == 'LOAD':
            raise RuntimeError('private failure text')

    def generate(self, image, prompt):
        self.calls += 1
        if self.fail == 'GENERATE':
            raise RuntimeError('private failure text')
        return {'generated_ids': [[11, 22]], 'input_ids': [[33]], 'unprocessed': True}

    def decode(self, native):
        assert list(self.folder.rglob('native.raw.json')), 'decode before raw'
        self.decodes += 1
        if self.fail == 'DECODE':
            raise ValueError('private failure text')
        return {'text': self.text, 'with_special_tokens': self.text + '</s>', 'termination': 'EOS'}

    def memory(self):
        return {'peak_allocated': 10, 'peak_reserved': 20}


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name).resolve()
        (self.repo / 'configs/pre_freeze').mkdir(parents=True)
        shutil.copyfile(ROOT / r.CONFIG, self.repo / r.CONFIG)
        self.cases = [{'call_id': f'cq_{i:02d}', 'case_id': f'cq_{i:02d}', 'task': 'classification',
                       'prompt': JSON_PROMPT, 'raw_image': b'fake-synthetic-only', 'expected_safety_level': 'Level01'}
                      for i in range(1, 9)]
        self.backend = FakeBackend(self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def run_fake(self):
        return r.run_kernel(self.repo, 'ovis', {'base': r.BASE}, self.backend, self.cases)

    def test_raw_before_decode_parse_and_wrong_semantics_kept(self):
        result = self.run_fake()
        self.assertEqual(self.backend.loads, 1)
        self.assertEqual(self.backend.calls, 8)
        self.assertEqual(result['classification_interface'], 'OBSERVED_VALID_PENDING_REVIEW')
        self.assertTrue(all(not row['semantic_correct'] for row in result['calls']))
        self.assertEqual(result['final_verdict'], 'PENDING_REVIEW')
        self.assertFalse(result['automatic_pass'])
        schema = r.read(ROOT, 'schemas/d9r20_result.v1.schema.json')
        self.assertTrue(set(schema['required']).issubset(result))
        for key in ('schema','final_verdict','automatic_pass','INSPECSAFE','PROTOCOL_FREEZE','participation','model_load_attempts'):
            self.assertEqual(result[key], schema['properties'][key]['const'])
        for row in result['calls']:
            path = self.repo / r.OUTPUT / CONFIG['models']['ovis']['run_id'] / row['call_id'] / row['raw']['file']
            self.assertEqual(r.digest(path.read_bytes()), row['raw']['sha256'])

    def test_refuses_repeated_attempt(self):
        self.run_fake()
        with self.assertRaises(FileExistsError):
            self.run_fake()
        self.assertEqual(self.backend.loads, 1)

    def test_load_failure_resource_not_semantic(self):
        self.backend.fail = 'LOAD'
        result = self.run_fake()
        self.assertEqual(result['failure']['resource_result'], 'RESOURCE_FAIL_NO_GO')
        self.assertEqual(result['calls'], [])
        self.assertEqual(self.backend.loads, 1)
        self.assertNotIn('private', json.dumps(result))

    def test_generation_failure_records_attempt(self):
        self.backend.fail = 'GENERATE'
        result = self.run_fake()
        self.assertEqual(len(result['calls']), 1)
        self.assertEqual(result['calls'][0]['parse_status'], 'NOT_ATTEMPTED')
        self.assertEqual(self.backend.decodes, 0)

    def test_decode_failure_preserves_native(self):
        self.backend.fail = 'DECODE'
        result = self.run_fake()
        self.assertEqual(result['failure']['phase'], 'DECODE')
        self.assertIsNotNone(result['calls'][0]['raw'])
        self.assertIsNone(result['calls'][0]['canonical'])

    def test_storage_failure_never_decodes(self):
        original = r.persisted
        def fail(path, raw):
            if path.name == 'native.raw.json':
                raise OSError('disk')
            return original(path, raw)
        with patch.object(r, 'persisted', fail):
            result = self.run_fake()
        self.assertEqual(result['failure']['phase'], 'RAW_PERSIST')
        self.assertEqual(self.backend.decodes, 0)

    def test_format_failure_is_not_repaired(self):
        self.backend.text = '```json\n{"safety_level":"Level01"}\n```'
        result = self.run_fake()
        self.assertTrue(all(c['parse_status'] == 'INVALID' and c['canonical'] is None for c in result['calls']))
        self.assertEqual(self.backend.calls, 8)

    def test_model_run_directories_independent(self):
        self.run_fake()
        other = FakeBackend(self.repo)
        result = r.run_kernel(self.repo, 'kosmos', {}, other, self.cases)
        self.assertEqual(result['run_id'], CONFIG['models']['kosmos']['run_id'])
        self.assertEqual(other.loads, 1)

    def test_bounded_bundle_contains_provenance_and_no_images(self):
        import zipfile
        from scripts import run_d9r20_candidate as cli
        result = self.run_fake()
        with patch.object(cli, 'ROOT', self.repo), patch.object(sys, 'argv', ['run_d9r20_candidate.py','bundle','--model','ovis']):
            cli.main()
        bundle = self.repo / r.OUTPUT / (result['run_id'] + '.zip')
        with zipfile.ZipFile(bundle) as archive:
            self.assertIn('result.json', archive.namelist())
            self.assertIn('cq_01/native.raw.json', archive.namelist())
            self.assertTrue(all(name.endswith('.json') for name in archive.namelist()))
            self.assertLess(sum(i.file_size for i in archive.infolist()), 32*1024*1024)

    def test_bundle_rejects_corrupt_metadata_or_raw(self):
        from scripts import run_d9r20_candidate as cli
        result = self.run_fake()
        folder = self.repo / r.OUTPUT / result['run_id'] / 'cq_01'
        for name in ('native.raw.json', 'preparse.json'):
            raw = (folder / name).read_bytes()
            (folder / name).write_bytes(b'CORRUPT')
            with patch.object(cli, 'ROOT', self.repo), patch.object(sys, 'argv', ['run_d9r20_candidate.py','bundle','--model','ovis']), self.assertRaisesRegex(ValueError, 'BUNDLE_ARTIFACT_INTEGRITY'):
                cli.main()
            (folder / name).write_bytes(raw)

    def test_reread_corruption_stops_before_decode(self):
        original = r._write_new
        def corrupt(path, raw):
            original(path, b'corrupt' if path.name == 'native.raw.json' else raw)
        with patch.object(r, '_write_new', corrupt):
            result = self.run_fake()
        self.assertEqual(self.backend.decodes, 0)
        self.assertEqual(result['failure']['reason'], 'RAW_STORAGE_VERIFICATION_FAILURE')


class Geometry(unittest.TestCase):
    def test_extra_predictions_preserved_without_capability_auto_fail(self):
        case = {'target': 'red square', 'targets': [{'label': 'red square', 'bbox': [.1,.1,.3,.3]}],
                'distractor_boxes': [[.6,.6,.9,.9]]}
        detections = [{'label': 'red square', 'bbox': [.1,.1,.3,.3]}, {'label':'red square','bbox':[.6,.6,.9,.9]}]
        obs = r.diagnostics(case, detections)
        self.assertEqual(obs['predicted_count'], 2)
        self.assertEqual(obs['capability_witness_indices'], [0])
        self.assertEqual(obs['unmatched_predictions'], [1])
        self.assertEqual(len(detections), 2)

    def test_missed_instances_and_full_image(self):
        case = {'target': 'red', 'targets': [{'label':'red','bbox':[.1,.1,.3,.3]}], 'distractor_boxes': []}
        obs = r.diagnostics(case, [{'label':'red','bbox':[0,0,1,1]}])
        self.assertTrue(obs['boxes'][0]['full_image'])
        self.assertFalse(obs['capability_witness_indices'])
        self.assertEqual(obs['missed_instances'], [0])

    def test_absent_false_positives_recorded(self):
        obs = r.diagnostics({'target':'red','targets':[],'distractor_boxes':[]}, [{'label':'red','bbox':[0,0,1,1]}])
        self.assertEqual(obs['false_positive_count_if_target_absent'], 1)
        self.assertEqual(obs['expected_count'], 0)

    def test_tracking_requires_target_change_and_never_awards_pass(self):
        rows = []
        for call_id in CONFIG['grounding']['mandatory_sanity']:
            rows.append({'call_id':call_id, 'diagnostics': {'capability_witness_indices':[0], 'boxes':[{'center':[.2,.2]}]}})
        result = r.capability_observations(rows)
        self.assertFalse(any(p['tracking_observed'] for p in result['tracking_pairs']))
        self.assertFalse(result['automatic_pass'])
        self.assertEqual(result['eligibility'], 'PENDING_REVIEW')


class NativeBoundaries(unittest.TestCase):
    def backend(self, key):
        backend = NativeBackend(key, CONFIG['models'][key], Path('fake'), CONFIG['generation'], 0)
        tokenizer = SimpleNamespace(decode=lambda ids, **kw: repr(ids))
        backend.processor = tokenizer if key == 'ovis' else SimpleNamespace(tokenizer=tokenizer)
        return backend

    def native(self, key, prefix, ids):
        return {'model_id': PINS[key][0], 'revision': PINS[key][1], 'input_ids':[prefix], 'generated_ids':[ids],
                'effective_generation_defaults': {'eos_token_id':2}}

    def test_ovis_completion_not_prefix_and_sentinels(self):
        b = self.backend('ovis')
        result = b.decode(self.native('ovis', [12,-301,-300,-302], [20,2]))
        self.assertEqual(result['continuation_ids'], [20,2])
        with self.assertRaises(ValueError):
            b.decode(self.native('ovis', [12,-200], [20,2]))

    def test_hf_exact_prefix_no_text_strip(self):
        for key in ('plamo','kosmos'):
            b = self.backend(key)
            self.assertEqual(b.decode(self.native(key, [0,11], [0,11,20,2]))['continuation_ids'], [20,2])
            with self.assertRaises(ValueError):
                b.decode(self.native(key, [0,11], [12,11,20,2]))

    def test_eos_and_truncation(self):
        b = self.backend('ovis')
        for ids in ([11,12], [11,2,12,2], [11]*512+[2]):
            self.assertEqual(b.decode(self.native('ovis',[1],ids))['termination'], 'INVALID_OR_TRUNCATED')

    def test_cannot_load_twice_even_after_failure(self):
        b = self.backend('ovis')
        b.load_attempted = True
        with self.assertRaisesRegex(ValueError, 'ONE_LOAD_ATTEMPT_ONLY'):
            b.load()

    def test_model_specific_loaders_never_offload_quantize_or_fallback(self):
        for key in PINS:
            with self.subTest(key=key):
                calls = []
                tensor = SimpleNamespace(device='cuda:0', dtype='fake-fp16', is_floating_point=lambda: True)
                class Model:
                    config = SimpleNamespace(name_or_path='fake')
                    text_tokenizer = object()
                    def to(self, device):
                        calls.append(('placement', device))
                        return self
                    def eval(self):
                        return self
                    def named_parameters(self):
                        return [('parameter', tensor)]
                    def named_buffers(self):
                        return []
                def factory(path, **kwargs):
                    calls.append(('load', path, kwargs))
                    return Model()
                def processor(path, **kwargs):
                    calls.append(('processor', path, kwargs))
                    return object()
                fake_torch = SimpleNamespace(float16='fake-fp16', manual_seed=lambda seed: None,
                    cuda=SimpleNamespace(manual_seed_all=lambda seed: None, reset_peak_memory_stats=lambda index: None))
                fake_transformers = SimpleNamespace(AutoModelForCausalLM=SimpleNamespace(from_pretrained=factory),
                    Kosmos2ForConditionalGeneration=SimpleNamespace(from_pretrained=factory),
                    AutoProcessor=SimpleNamespace(from_pretrained=processor))
                b = self.backend(key)
                with patch.dict(sys.modules, torch=fake_torch, transformers=fake_transformers):
                    b.load()
                load = next(c for c in calls if c[0] == 'load')
                self.assertEqual(load[2], {'revision':PINS[key][1], 'local_files_only':True,
                    'trust_remote_code':key != 'kosmos', 'torch_dtype':'fake-fp16', 'use_safetensors':True})
                self.assertIn(('placement','cuda:0'), calls)
                tensor.device = 'cpu'
                with self.assertRaises(ValueError):
                    b.check_placement()
                tensor.device, tensor.dtype = 'cuda:0', 'BF16'
                with self.assertRaises(ValueError):
                    b.check_placement()


class Provisioning(unittest.TestCase):
    def test_snapshot_hash_size_identity_and_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp).resolve()
            (repo / 'configs/pre_freeze').mkdir(parents=True)
            shutil.copyfile(ROOT / r.CONFIG, repo / r.CONFIG)
            revision = PINS['plamo'][1]
            relative = f'.cache/d9r20_snapshots/plamo/{revision}'
            folder = repo / relative
            folder.mkdir(parents=True)
            weights, tokenizer = b'FAKE_WEIGHTS_NOT_A_MODEL', b'{"fake":"tokenizer"}\n'
            (folder / 'model.safetensors').write_bytes(weights)
            (folder / 'tokenizer.jsonl').write_bytes(tokenizer)
            model = {'model_id':PINS['plamo'][0], 'revision':revision, 'files':[
                {'rfilename':'model.safetensors','size':len(weights),'lfs':{'sha256':r.digest(weights)}},
                {'rfilename':'tokenizer.jsonl','size':len(tokenizer),
                 'blobId': hashlib.sha1(f'blob {len(tokenizer)}\0'.encode()+tokenizer).hexdigest()}]}
            (repo / r.SOURCES).write_bytes(r.encode({'models':{'plamo':model}}))
            inventory = r.snapshot_inventory(repo, 'plamo', relative)
            self.assertEqual(len(inventory['files']), 2)
            with self.assertRaises(ValueError):
                r.snapshot_inventory(repo, 'plamo', relative.replace(revision, 'main'))
            (folder / 'tokenizer.jsonl').write_bytes(b'X' * len(tokenizer))
            with self.assertRaisesRegex(ValueError, 'SNAPSHOT_HASH'):
                r.snapshot_inventory(repo, 'plamo', relative)
            (folder / 'model.safetensors').write_bytes(b'X')
            with self.assertRaisesRegex(ValueError, 'SNAPSHOT_MISSING_OR_SIZE'):
                r.snapshot_inventory(repo, 'plamo', relative)

    def test_environment_resource_dependency_and_flash_preflight(self):
        candidate = CONFIG['models']['ovis']
        gpu = SimpleNamespace(name='Tesla T4', total_memory=15*2**30)
        fake = SimpleNamespace(__version__='2.4.0+cu121', version=SimpleNamespace(cuda='12.1'),
            cuda=SimpleNamespace(device_count=lambda: 1, get_device_properties=lambda _: gpu,
                                 get_device_capability=lambda _: (7,5)))
        def version(name):
            if name == 'flash-attn':
                raise r.metadata.PackageNotFoundError(name)
            return candidate['environment'][name]
        with patch.dict(sys.modules, torch=fake), patch.object(r.metadata, 'version', side_effect=version), \
             patch.object(r.metadata, 'distributions', return_value=[]), \
             patch.object(r.platform, 'python_version_tuple', return_value=('3','11','9')), \
             patch.object(r.subprocess, 'check_output', return_value='fake-driver'):
            self.assertEqual(r.environment('ovis', candidate)['gpu']['count'], 1)
            gpu.name = 'A100'
            with self.assertRaises(ValueError):
                r.environment('ovis', candidate)
            gpu.name = 'Tesla T4'
            fake.version.cuda = '12.4'
            with self.assertRaisesRegex(ValueError, 'CUDA_RUNTIME_VERSION'):
                r.environment('ovis', candidate)
            fake.version.cuda = '12.1'
            with patch.object(r.metadata, 'version', side_effect=lambda n: '2.7.0.post2' if n == 'flash-attn' else version(n)), self.assertRaisesRegex(ValueError, 'SDPA_REQUIRES_FLASH_ATTN_ABSENT'):
                r.environment('ovis', candidate)

    def test_failed_observation_never_authorizes_model(self):
        with patch.object(r, 'identity', return_value={'head':'a'*40,'main':'a'*40,'base':r.BASE}), \
             patch.object(r, 'environment', side_effect=ValueError('EXACT_SINGLE_T4_REQUIRED')):
            observed = r.observe(ROOT, 'ovis', '.cache/fake')
        self.assertEqual(observed['observation_failure']['phase'], 'ENVIRONMENT')
        self.assertEqual(observed['observation_failure']['reason'], 'EXACT_SINGLE_T4_REQUIRED')
        self.assertEqual(observed['model_load_attempts'], 0)
        with self.assertRaisesRegex(ValueError, 'FAILED_OBSERVATION'):
            r.check_authority('ovis', CONFIG['models']['ovis'], observed, {}, {}, '')

    def test_fixed_synthetic_inputs_and_classification_independence(self):
        real_read = Path.read_bytes
        opened = []
        def synthetic_read(path):
            relative = path.relative_to(ROOT).as_posix()
            opened.append(relative)
            return real_read(path)
        for key in PINS:
            with patch.object(Path, 'read_bytes', synthetic_read):
                cases = r.prepared_cases(ROOT, key)
            self.assertEqual(len(cases), 22)
            self.assertEqual([c['target'] for c in cases[8:20]], ['red square'] * 12)
            self.assertEqual([c['target'] for c in cases[20:]], ['green circle','cyan rectangle'])
            for c in cases[:8]:
                self.assertIn(JSON_PROMPT, c['prompt'])
        self.assertFalse(any('/raw/' in path or 'InspecSafe' in path for path in opened))

    def test_downloaded_source_text_checksums(self):
        source = r.read(ROOT, r.SOURCES)
        records = source['official_implementations'] + source['official_author_comments']
        for model in source['models'].values():
            records += model['sources'] + [model['api']]
        if not all((ROOT / x['local_audit_cache']).exists() for x in records):
            self.skipTest('downloaded audit cache not shipped; manifest structural tests remain mandatory')
        for record in records:
            raw = (ROOT / record['local_audit_cache']).read_bytes()
            self.assertEqual((r.digest(raw),len(raw)), (record['sha256'],record['size_bytes']))


if __name__ == '__main__':
    unittest.main()
