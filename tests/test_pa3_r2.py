"""Synthetic CPU tests only: no dataset/model downloads, GPU or grant."""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pa3.native import access, r2, r2_prepare, r2_inputs, preflight, train_report, qwen
from safeshift.pa3.native.durable import DurableJournal, recover
from safeshift.pa3.native.merger_clamp import MergerClamp, POLICY
from safeshift.pa3.artifacts import json_bytes

ROOT = Path(__file__).resolve().parents[1]


class R2PreparationTests(unittest.TestCase):
    def test_manifest_exact_original_3763_and_distinct_runs(self):
        value = r2_prepare.build_manifest(ROOT)
        self.assertEqual((ROOT / r2.FULL).read_bytes(), json_bytes(value))
        sha = hashlib.sha256(json_bytes(value)).hexdigest()
        self.assertEqual(len(r2.load_full(ROOT, sha)), 3763)
        ids = []
        for i in range(4):
            rows = r2.inference_payload(ROOT, value, i)["samples"]
            self.assertEqual(len(rows), r2.SIZES[i])
            ids += [r["sample_id"] for r in rows]
            self.assertNotEqual(r2.run_id(i), r2.train.run_id(i))
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 3763)
        value["shards"][0]["run_id"] = r2.train.run_id(0)
        with self.assertRaises(ValueError): r2.inference_payload(ROOT, value, 0)

    def test_null_authority_denies_parent_child_and_direct_data_before_git(self):
        settings = dict(mode=r2.MODE, run_id=r2.run_id(0), shard_id=0, source_commit=r2.BASE)
        with patch.object(preflight, "git", side_effect=AssertionError("GIT_READ")):
            for call in (lambda: access.require(r2.MODE, settings, ROOT),
                         lambda: r2.inference_samples(ROOT, settings),
                         lambda: r2.open_image(ROOT, settings, {}, "NEVER_READ"),
                         lambda: qwen.QwenRawScorer("NEVER_LOAD", None, [], repo=ROOT, settings=settings),
                         lambda: r2_inputs.resolve(ROOT, "NEVER_SCAN", 0, r2.BASE, "unused", "unused")):
                with self.assertRaises(PermissionError):
                    call()
        with patch.object(preflight, 'git', return_value=r2.BASE.encode()):
            with self.assertRaises(PermissionError): r2_prepare.release(ROOT, 'NEVER_WRITE')

    def test_scope_and_original_grant_cannot_authorize_r2(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            p = repo / r2.AUTHORITY
            p.parent.mkdir(parents=True)
            original = json.loads((ROOT / r2.train.AUTHORITY).read_bytes())
            for change in ({}, {"scope": r2.SCOPE}):
                p.write_bytes(json_bytes({**original, **change}))
                with self.assertRaises(PermissionError): r2.authority(repo, r2.BASE)
        settings = dict(mode=r2.MODE, run_id=r2.train.run_id(0), shard_id=0)
        with self.assertRaises(PermissionError): r2.require(settings, ROOT)

    def test_real_git_r2_release_topology_source_and_prior_authority_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                return subprocess.check_output(['git','-C',str(repo),*args], text=True,
                                               stderr=subprocess.DEVNULL).strip()
            git('init','-b','main')
            git('config','core.autocrlf','false')
            git('config','user.name','CPU fixture')
            git('config','user.email','cpu@example.invalid')
            for prior in (access.AUTHORITY, access.DIAGNOSTIC_AUTHORITY, r2.train.AUTHORITY):
                p = repo/prior
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'{}\n')
            git('add','.')
            git('commit','-m','B')
            base = git('rev-parse','HEAD')
            git('checkout','-b','prep')
            p = repo/r2.AUTHORITY
            value = dict(base=base, implementation=None, scope=deepcopy(r2.SCOPE), grant=None)
            p.write_bytes(json_bytes(value))
            git('add','.')
            git('commit','-m','F1')
            f1 = git('rev-parse','HEAD')
            value.update(implementation=f1, grant={**{k:'a'*64 for k in r2.HASHES},
                'approval':'SYNTHETIC ONLY', 'decision':r2.DECISION,
                'shards':[dict(shard_id=i,run_id=r2.run_id(i),max_images=r2.SIZES[i],
                               inference_manifest_sha256='b'*64) for i in range(4)]})
            p.write_bytes(json_bytes(value))
            git('add','.')
            git('commit','-m','F2')
            with patch.object(r2, 'BASE', base):
                with self.assertRaisesRegex(PermissionError,'STANDARD_MERGE'):
                    r2.authority(repo, git('rev-parse','HEAD'))
                git('checkout','main')
                git('merge','--no-ff','prep','-m','M')
                sha = git('rev-parse','HEAD')
                self.assertEqual(r2.authority(repo, sha)['grant'], value['grant'])
                with self.assertRaises(PermissionError): r2.authority(repo, '0'*40)
                (repo/r2.train.AUTHORITY).write_bytes(b'{"edited":true}\n')
                with self.assertRaises(PermissionError): r2.authority(repo, sha)
                # A dirty self-grant cannot borrow the valid topology either.
                value['grant']['approval'] = 'SELF EDIT'
                p.write_bytes(json_bytes(value))
                with self.assertRaises(PermissionError): r2.authority(repo, sha)

    def test_merge_refuses_old_shard_before_auditing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            roots = [Path(tmp) / str(i) for i in range(4)]
            for i, root in enumerate(roots):
                j = DurableJournal(root, create=True)
                j.write("manifest", {"mode": r2.MODE if i == 0 else r2.train.MODE})
            with patch.object(train_report, "checked_run", return_value=(
                    {"shard_id": 0, "full_manifest_sha256": "x", "run_id": r2.run_id(0)},
                    {"results": [], "completed": False}, {})), \
                 patch.object(train_report, "metrics", return_value={}), \
                 patch.object(train_report.Journal, "read", autospec=True) as read:
                def get(j, key):
                    if key == "manifest": return {"mode": r2.MODE if j.root.name == "0" else r2.train.MODE}
                    return {}
                read.side_effect = get
                with self.assertRaisesRegex(ValueError, "MIXED_PA3"):
                    train_report.merge(ROOT, roots, None, Path(tmp) / "report")

    def test_discovery_prunes_test_and_raw_data_and_rejects_ambiguity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested/train/DATA_PATH/train/Annotations").mkdir(parents=True)
            (root / "nested/train/DATA_PATH/test").mkdir()
            (root / "nested/train/DATA_PATH/test/forbidden.bundle").write_bytes(b"NEVER")
            (root / "source").mkdir()
            (root / "source/ok.bundle").write_bytes(b"fixture")
            files, datasets = r2_inputs.inventory(root)
            self.assertEqual([p.name for p in files], ["ok.bundle"])
            self.assertEqual(datasets, [root / "nested/train"])
            with self.assertRaises(ValueError): r2_inputs.unique([], "missing")
            with self.assertRaises(ValueError): r2_inputs.unique([1, 2], "ambiguous")

    def test_resolver_finds_hash_bound_inputs_and_fails_on_duplicate_or_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def put(name, data):
                p=root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
                return p
            source=put('source/new.bundle', b'new')
            technical=put('technical/old.bundle', b'old')
            seal=put('qualification/seal.json', b'{}')
            runtime=put('runtime/runtime.tar.gz', b'runtime')
            model=put('model/model.tar.gz', b'model')
            inv=put('runtime/pa3_runtime_inventory.json', json_bytes({'schema':'ls1-runtime-inventory-v1',
                'files':{runtime.name:{'sha256':r2_inputs.digest(runtime),'size_bytes':runtime.stat().st_size}}}))
            (root/'dataset/DATA_PATH/train/Annotations').mkdir(parents=True)
            grant={**{k:'a'*64 for k in r2.HASHES},
                'technical_source_bundle_sha256':r2_inputs.digest(technical),
                'technical_seal_sha256':r2_inputs.digest(seal),
                'runtime_inventory_sha256':r2_inputs.digest(inv),
                'shards':[{'inference_manifest_sha256':'b'*64}]*4}
            with patch.object(r2,'authority',return_value={'grant':grant}):
                settings=r2_inputs.resolve(ROOT,root,2,r2.BASE,source,r2_inputs.digest(source))
                self.assertEqual(settings['run_id'],r2.run_id(2))
                self.assertEqual(settings['dataset_input'],'dataset')
                duplicate=put('duplicate/model.tar.gz',b'model')
                with self.assertRaisesRegex(ValueError,'MODEL_ARCHIVE'):
                    r2_inputs.resolve(ROOT,root,2,r2.BASE,source,r2_inputs.digest(source))
                duplicate.unlink()
                runtime.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'RUNTIME_ARCHIVE'):
                    r2_inputs.resolve(ROOT,root,2,r2.BASE,source,r2_inputs.digest(source))

    def test_notebook_draft_no_outputs_compiles_and_packages_denial(self):
        nb = json.loads((ROOT / "notebooks/pa3_r2_full_train_kaggle.ipynb").read_bytes())
        self.assertFalse(nb["metadata"]["kaggle"]["isInternetEnabled"])
        with tempfile.TemporaryDirectory() as tmp:
            old = Path.cwd()
            try:
                os.chdir(tmp)
                scope = {}
                for i, cell in enumerate(nb["cells"]):
                    if cell["cell_type"] == "code":
                        self.assertEqual(cell["outputs"], [])
                        exec(compile("".join(cell["source"]), f"cell-{i}", "exec"), scope)
                self.assertTrue((Path(tmp) / "PA3_R2_TRAIN_SHARD_0_OUTPUT.tar.gz").is_file())
            finally:
                os.chdir(old)

    def test_release_fills_four_notebooks_without_mutating_authority(self):
        from safeshift.pa3.native import kaggle
        manifest = r2_prepare.build_manifest(ROOT)
        grant = {'full_manifest_sha256':hashlib.sha256(json_bytes(manifest)).hexdigest(),
                 'shards':manifest['shards']}
        authority_before = (ROOT/r2.AUTHORITY).read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'release'
            def bundle(repo, output):
                output.mkdir()
                return {'source_commit':'a'*40, 'bundle_sha256':'b'*64}
            with patch.object(r2,'authority',return_value={'grant':grant}), \
                 patch.object(preflight,'git',return_value=b'a'*40), \
                 patch.object(kaggle,'bundle_source',side_effect=bundle):
                r2_prepare.release(ROOT,out)
            for i in range(4):
                nb=json.loads((out/f'PA3_R2_SHARD_{i}.ipynb').read_bytes())
                scope={}
                exec(''.join(nb['cells'][1]['source']),scope)
                self.assertEqual(scope['SHARD_ID'],i)
                self.assertEqual(scope['LOCKED'],{'source_commit':'a'*40,'source_bundle_sha256':'b'*64})
            self.assertEqual((ROOT/r2.AUTHORITY).read_bytes(),authority_before)


class DurabilityTests(unittest.TestCase):
    def test_hard_stop_preserves_completed_images_and_never_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            program = '''
import os, sys
from safeshift.pa3.native.durable import DurableJournal
j = DurableJournal(sys.argv[1], create=True)
j.write('manifest', {'mode':'full-train-r2','run_id':'pa3-qwen-r2-train-shard-0','samples':[{'sample_id':str(i)} for i in range(4)]})
for i in range(int(sys.argv[2])):
    p = f'sample-{i:06d}'
    j.write(p+'.attempt', {'sample_id':str(i)})
    j.write(p+'.raw', {'synthetic_raw':'retained'})
    j.write(p+'.result', {'status':'SUCCESS'})
j.write(f'sample-{int(sys.argv[2]):06d}.attempt', {'sample_id':'interrupted'})
os._exit(9)
'''
            for n in (1, 2, 3):
                run = root.with_name('run' + str(n))
                child = subprocess.run([sys.executable, "-c", program, str(run), str(n)], cwd=ROOT)
                self.assertEqual(child.returncode, 9)
                before = {p.name: p.read_bytes() for p in run.iterdir()}
                result = recover(run, Path(tmp) / ('recovery' + str(n)))
                self.assertEqual([r['recovery_status'] for r in result['samples']],
                                 ['COMPLETE'] * n + ['INCOMPLETE'] + ['NOT_ATTEMPTED'] * (3-n))
                self.assertEqual(before, {p.name: p.read_bytes() for p in run.iterdir()})
                with self.assertRaises(FileExistsError): DurableJournal(run).write('manifest', {})

    def test_torn_receipt_and_staging_are_reported_without_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'run'
            j = DurableJournal(root, create=True)
            j.write('manifest', {'mode':r2.MODE,'run_id':r2.run_id(0),'samples':[{'sample_id':'s'}]})
            j.path('sample-000000.attempt').write_bytes(b'{}')
            result = recover(root, Path(tmp) / 'recovered')
            self.assertEqual(result['samples'][0]['recovery_status'], 'CORRUPT_OR_TORN')


@contextmanager
def r2_running(tmp, failure_at=None):
    from tests.test_pa3_full_train import running_fixture
    from safeshift.pa3.native import merger_clamp
    class MockClamp:
        def __init__(self, model, torch, record):
            self.record, self.calls = record, 0
        def __enter__(self):
            self.record(0, {'policy':POLICY, 'triggered':False, 'overflow_count':0,
                           'input_nonfinite':{'nan':0,'positive_inf':0,'negative_inf':0}})
            self.calls = 1
            return self
        def __exit__(self, *exc): pass
    with running_fixture(tmp, failure_at) as (repo, old, inputs, model, _, _), \
         patch.object(r2, 'COUNT', 8), patch.object(r2, 'SIZES', (2,2,2,2)), \
         patch.object(merger_clamp, 'MergerClamp', MockClamp):
        value = r2_prepare.build_manifest(repo)
        payload = json_bytes(value)
        (repo/r2.FULL).write_bytes(payload)
        settings = {**old, 'mode':r2.MODE, 'run_id':r2.run_id(0),
                    'full_manifest_sha256':hashlib.sha256(payload).hexdigest(),
                    'inference_manifest_sha256':value['shards'][0]['inference_manifest_sha256']}
        with patch.object(r2, 'require', return_value={'grant':{}}):
            yield repo, settings, inputs, model, value


class R2WorkflowTests(unittest.TestCase):
    def test_four_shards_reaudit_export_clamp_and_pool_only_r2(self):
        from safeshift.pa3.native import workflow
        from tests.test_pa3_native import TOK
        import csv
        with tempfile.TemporaryDirectory() as tmp, r2_running(tmp) as (repo, settings, inputs, model, value):
            roots = []
            for i in range(4):
                s = {**settings, 'shard_id':i, 'run_id':r2.run_id(i),
                     'inference_manifest_sha256':value['shards'][i]['inference_manifest_sha256']}
                roots.append(workflow.execute(repo, s, 'fixture', inputs))
            out = Path(tmp)/'merged'
            result = train_report.merge(repo, roots, TOK, out)
            self.assertTrue(result['completed'])
            self.assertEqual(len(model.calls), 8)
            with (out/'samples.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(r['clamp_triggered']=='False' and r['overflow_count']=='0' for r in rows))

    def test_generation_error_preserves_prior_result_and_clamp_tail(self):
        from safeshift.pa3.native import workflow
        from safeshift.pa3.native.journal import run_path, Journal
        with tempfile.TemporaryDirectory() as tmp, r2_running(tmp, 2) as (repo, settings, inputs, model, _):
            with self.assertRaises(RuntimeError): workflow.execute(repo, settings, 'fixture', inputs)
            root = run_path(repo, settings['run_id'])
            rows = Journal(root.parent/(root.name+'-report')).read('audit')['results']
            self.assertEqual([r['status'] for r in rows], ['SUCCESS','TECHNICAL_ERROR'])
            self.assertTrue(all(r['merger_clamp'] is not None for r in rows))
            self.assertEqual(len(model.calls), 2)
            with self.assertRaises(FileExistsError): workflow.execute(repo, settings, 'fixture', inputs)


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('transformers'), 'pinned CPU environment required')
class PinnedQwen32Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch, transformers
        if transformers.__version__ != '4.51.3':
            raise unittest.SkipTest('transformers 4.51.3 required')
        cls.torch = torch
        torch.set_num_threads(2)

    def scorer(self, kind=None):
        from transformers import Qwen2_5_VLConfig, Qwen2_5_VLForConditionalGeneration, GenerationConfig
        torch = self.torch
        torch.manual_seed(0)
        config = Qwen2_5_VLConfig(vision_config=dict(depth=2, hidden_size=32, intermediate_size=64,
            num_heads=2, out_hidden_size=64, patch_size=14, spatial_merge_size=2, temporal_patch_size=2,
            window_size=56, fullatt_block_indexes=[1], in_chans=3), hidden_size=64, num_hidden_layers=2,
            num_attention_heads=4, num_key_value_heads=2, intermediate_size=128, vocab_size=128,
            max_position_embeddings=512, rope_scaling={'type':'mrope','mrope_section':[2,3,3]},
            attn_implementation='sdpa', image_token_id=124, video_token_id=125,
            vision_start_token_id=126, vision_end_token_id=127)
        model = Qwen2_5_VLForConditionalGeneration(config).half().eval()
        if kind:
            with torch.no_grad():
                block = model.visual.blocks[0 if kind == 'early' else -1]
                block.attn.proj.bias[0] = -40000.
                block.mlp.down_proj.bias[0] = -40000.
        ids = torch.tensor([[1, 126] + [124]*8 + [127, 2]])
        inputs = dict(input_ids=ids, attention_mask=torch.ones_like(ids),
                      pixel_values=torch.randn(32, 3*2*14*14).half(), image_grid_thw=torch.tensor([[1,4,8]]))
        scorer = qwen.QwenRawScorer.__new__(qwen.QwenRawScorer)
        scorer.model, scorer.torch = model, torch
        scorer.settings = {'mode':r2.MODE}
        scorer.authority_repo, scorer.failed = ROOT, False
        scorer.validator = lambda: None
        scorer.prepare = lambda *_: inputs
        scorer.config = GenerationConfig(eos_token_id=None, pad_token_id=0, bos_token_id=1)
        scorer.condition, scorer.candidate_ids = {'decoding':{}}, [10,11,12,13]
        scorer.tokenizer = type('Tokenizer', (), {'decode':lambda *a, **k:'synthetic'})()
        return scorer

    def test_official_runner_32_fp16_sdpa_steps_after_overflow_and_hook_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, 'image_ticket'):
            j = DurableJournal(Path(tmp)/'run', create=True)
            scorer = self.scorer('last')
            raw = scorer.generate(None, j, 'sample-000000')
            self.assertEqual(len(raw['steps']), 32)
            self.assertTrue(j.read('sample-000000.clamp-00')['triggered'])
            self.assertGreater(j.read('sample-000000.clamp-00')['overflow_count'], 0)
            self.assertTrue(all(not any(s['raw']['nonfinite'].values()) for s in raw['steps']))
            self.assertFalse(scorer.model.visual.merger._forward_pre_hooks)
            self.assertEqual(raw['generation_kwargs']['max_new_tokens'], 32)

    def test_finite_32_steps_bitwise_identical_and_no_leaked_counts_next_image(self):
        torch = self.torch
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, 'image_ticket'):
            j = DurableJournal(Path(tmp)/'run', create=True)
            scorer = self.scorer()
            inputs = scorer.prepare(None, ())
            with torch.inference_mode():
                baseline = scorer.model.generate(**inputs, generation_config=deepcopy(scorer.config),
                    max_new_tokens=32, do_sample=False, num_beams=1, num_return_sequences=1,
                    return_dict_in_generate=True, output_logits=True, output_scores=True)
                scorer.model.rope_deltas = None
                with MergerClamp(scorer.model, torch, lambda *_: None):
                    clamped = scorer.model.generate(**inputs, generation_config=deepcopy(scorer.config),
                        max_new_tokens=32, do_sample=False, num_beams=1, num_return_sequences=1,
                        return_dict_in_generate=True, output_logits=True, output_scores=True)
                self.assertTrue(all(torch.equal(a.view(torch.int32), b.view(torch.int32))
                                    for a,b in zip(baseline.logits, clamped.logits)))
            raw = scorer.generate(None, j, 'sample-000000')
            self.assertEqual(raw['continuation_ids'], baseline.sequences[0, inputs['input_ids'].shape[1]:].tolist())
            from safeshift.ls1.runtime import summarize_tensor
            for i, step in enumerate(raw['steps']):
                self.assertEqual(step['raw'], summarize_tensor(baseline.logits[i], scorer.candidate_ids,
                    raw['continuation_ids'][i], torch))
            self.assertFalse(j.read('sample-000000.clamp-00')['triggered'])
            scorer.generate(None, j, 'sample-000001')
            self.assertEqual(j.read('sample-000001.clamp-00')['overflow_count'], 0)

    def test_earlier_nan_preserved_raw_saved_error_and_no_retry(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(access, 'image_ticket'):
            j = DurableJournal(Path(tmp)/'run', create=True)
            scorer = self.scorer('early')
            with self.assertRaisesRegex(ValueError, 'R2_NONFINITE_RAW_LOGITS'):
                scorer.generate(None, j, 'sample-000000')
            self.assertTrue(j.exists('sample-000000.raw'))
            self.assertGreater(j.read('sample-000000.clamp-00')['input_nonfinite']['nan'], 0)
            self.assertFalse(scorer.model.visual.merger._forward_pre_hooks)
            with self.assertRaisesRegex(RuntimeError, 'NO_RETRY'):
                scorer.generate(None, j, 'sample-000001')

    def test_exact_candidate_semantics_finite_extremes_and_nan(self):
        torch = self.torch
        from types import SimpleNamespace
        merger = torch.nn.Identity()
        events = []
        clamp = MergerClamp(SimpleNamespace(visual=SimpleNamespace(merger=merger)), torch,
                            lambda i, e: events.append(e))
        x = torch.tensor([65504., -65504., 0., -0.], dtype=torch.float16)
        with clamp:
            self.assertIs(merger(x), x)
            y = merger(torch.tensor([float('-inf'), float('nan'), 65504.], dtype=torch.float16))
        self.assertEqual(y[0].item(), -64512.)
        self.assertTrue(y[1].isnan())
        self.assertEqual(y[2].item(), 64512.)
        self.assertEqual(events[1]['finite_values_clipped'], 1)


if __name__ == '__main__':
    unittest.main()
