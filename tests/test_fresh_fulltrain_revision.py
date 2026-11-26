"""Issue171 re-review: public-source parity and adversarial CPU process tests.

No weights, private dataset, GPU or real model invocation. Fake tokenizers and
scripted process workers are technical fixtures, never scientific evidence.
"""
import ast
from contextlib import ExitStack, nullcontext
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.fulltrain import admission as a, contract as c, environment as e, provision as p
from safeshift.fulltrain import qwen as q, qwen_semantics as s, runtime as rt, supervision as sup
from safeshift.candidates import fulltrain_run as journal
from safeshift.candidates.source import ROOT
from safeshift.pilot.artifacts import read, write, sha
from safeshift.pilot.contract import digest, parse_label


def budgets():
    return {"review_mode": "EXTERNAL", "driver_versions": ["570.0.0"], "free_mib_per_gpu": [10, 20],
        **{n: 1 for n in ("free_gpu0_runtime_mib", "free_ram_mib", "free_scratch_mib", "free_output_mib")},
        "scratch_probe_bytes": 4096, "output_probe_bytes": 4096, "max_log_bytes": 2**20,
        "setup_seconds": 30, "diagnostic_seconds": 20}


class Tokenizer:
    """Synthetic one-character vocabulary, four single-token label alternatives."""
    def encode(self, text, **kwargs): return [ord(ch) for ch in text]
    def decode(self, ids, **kwargs): return ''.join(chr(i) for i in ids if i != 0)


def trace(text='{"safety_level":"Level03"}'):
    tokenizer = Tokenizer()
    ids = tokenizer.encode(text) + [0]
    mapping = s.locate_decision(tokenizer, text, ids, [0])
    rows = []
    for i, token in enumerate(ids):
        values = {str(t): float(j) for j, t in enumerate(mapping["token_ids"])}
        values[str(token)] = 10.
        summary = {"vocab_size": 256, "candidate_values": values, "generated_value": 10.,
            "argmax_id": token, "argmax_value": 10., "logsumexp": 11.,
            "nonfinite": {"nan": 0, "positive_inf": 0, "negative_inf": 0}}
        rows.append({"step": i, "generated_token": token, "raw": summary, "processed": copy.deepcopy(summary)})
    return {"response": text, "generated_ids": ids, "trace": {"decoded_text": text, "continuation_ids": ids, "steps": rows},
        "mapping": mapping, "eos_token_ids": [0], "cpu_tokenizer_replay": {"status": "PASS", "mapping": True}}


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def request(self, key="internvl35"):
        cohort = journal.synthetic_cohort()
        campaign = c.campaign({k: cohort for k in c.planning.MODELS}, digest(cohort))
        plan = c.plan(campaign, cohort, c.native_identity(key), [], action="initial", run_id="fresh-run",
                      attempt_id="fresh-attempt", max_calls=1, max_seconds=120)
        for name in ("inputs", "work", "scratch"):
            (self.root / name).mkdir(exist_ok=True)
        return {"model_key": key, "source_sha256": digest(c.source_manifest()), "inputs": str(self.root / "inputs"),
            "work": str(self.root / "work"), "scratch": str(self.root / "scratch"), "marker_sha256": "a"*64,
            "projection_sha256": digest(cohort), "campaign": campaign, "plan": plan, "history": [],
            "resource_policy": budgets(), "repair_case": None, "checkpoint_marker_sha256": "b"*64,
            "runtime_lock": None, "runtime_lock_sha256": None, "software_input": None, "software_marker_sha256": None}

    def test_qwen_exact_semantic_function_bodies_from_pinned_git_objects(self):
        proof = read(ROOT / "configs/fulltrain/qwen_semantics_provenance.json")
        current = {n.name: n for n in ast.parse((ROOT / "safeshift/fulltrain/qwen_semantics.py").read_bytes()).body
                   if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        for path, info in proof["sources"].items():
            original = subprocess.check_output(["git", "show", proof["commit"]+":"+path], cwd=ROOT)
            self.assertEqual(hashlib.sha256(original).hexdigest(), info["sha256"])
            nodes = {n.name: n for n in ast.parse(original).body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
            for name in info["functions"]:
                self.assertEqual(ast.dump(current[name]), ast.dump(nodes[name]), name)

    def test_shared_engine_copy_changes_only_explicit_parser_injection(self):
        from safeshift.fulltrain import engine
        import inspect
        original=inspect.getsource(__import__('safeshift.pilot.runner',fromlist=['execute']).execute)
        adapted=original.replace('hnlo_replay=replay):','hnlo_replay=replay, label_parser=parse_label):')
        adapted=adapted.replace('parse_label(', 'label_parser(').replace('from .diagnostics import failure_detail',
            'from safeshift.pilot.diagnostics import failure_detail')
        self.assertEqual(ast.dump(ast.parse(inspect.getsource(engine.execute))),ast.dump(ast.parse(adapted)))
        for name in ('_record','recover'):
            source=inspect.getsource(getattr(journal,name))
            source=source.replace('def _record(root, row, p):','def _record(root, row, p, label_parser):')
            source=source.replace('def recover(root, cohort_value, expected_plan_hash):',
                'def recover(root, cohort_value, expected_plan_hash, *, label_parser=parse_label):')
            source=source.replace('parse_label(', 'label_parser(').replace('_record(root, rows[i], p)',
                '_record(root, rows[i], p, label_parser)')
            self.assertEqual(ast.dump(ast.parse(inspect.getsource(getattr(engine,name)))),ast.dump(ast.parse(source)))

    def test_qwen_parser_is_historical_only_peer_parser_unchanged(self):
        for label in s.LEVELS:
            plain = '{"safety_level":"'+label+'"}'
            fenced = '```json\n'+plain+'\n```'
            self.assertEqual(q.parser(plain), label)
            self.assertEqual(q.parser(fenced), label)
            self.assertIsNone(parse_label(fenced))
        for invalid in ('before {"safety_level":"Level01"}', '{"safety_level":"Level01","x":0}',
                        '{"safety_level":"Level01","safety_level":"Level04"}',
                        '```json\n{"safety_level":"Level01"}\n```\nextra'):
            self.assertIsNone(q.parser(invalid))
        self.assertEqual(len(s.probe(Tokenizer())["checks"]), 28)

    def test_qwen_hnlo_native_alignment_reductions_and_corruption(self):
        raw = trace()
        h = q.replay(raw, "Level03")
        z = h["details"]["raw_label_logits"]
        self.assertAlmostEqual(h["hnlo"], math.log(sum(math.exp(v) for v in z[:3])) - z[3])
        for mutate in (lambda r: r["generated_ids"].pop(),
                       lambda r: r["trace"]["steps"][0]["processed"].update(argmax_id=999),
                       lambda r: r["trace"]["steps"][0]["raw"]["nonfinite"].update(nan=1),
                       lambda r: r.update(mapping=None),
                       lambda r: r["cpu_tokenizer_replay"].update(status="FAIL")):
            bad = copy.deepcopy(raw); mutate(bad)
            with self.assertRaises((ValueError, KeyError)):
                q.replay(bad, "Level03")
        ids = raw["generated_ids"] + [0]
        with self.assertRaises(ValueError):
            s.locate_decision(Tokenizer(), raw["response"], ids, [0])

    def test_qwen_native_factory_binds_snapshot_and_not_peer_adapter(self):
        with patch.object(q, "QwenBackend", return_value="bound") as model:
            self.assertEqual(rt._native_factory("qwen3", self.root, self.root), "bound")
            model.assert_called_once_with(self.root, repo=ROOT)
            with self.assertRaisesRegex(ValueError, "ONE_SEALED"):
                rt._native_factory("qwen3", self.root, self.root / "other")

    def test_qwen_loader_exact_dtype_device_map_offline_processor_and_no_fallback(self):
        native = SimpleNamespace(model=SimpleNamespace(rope_deltas=None), eval=Mock(), generation_config=SimpleNamespace(to_dict=lambda: {}))
        factory = Mock(return_value=native)
        fake_transformers = SimpleNamespace(Qwen3VLForConditionalGeneration=SimpleNamespace(from_pretrained=factory))
        with patch.dict(sys.modules, {"torch": SimpleNamespace(float16="FP16"), "transformers": fake_transformers}), \
             patch.object(q, "verify_snapshot", return_value={}), patch.object(q, "native_setup", return_value=(None,None,{})), \
             patch.object(q, "verify_transformers", return_value={}), patch.object(q, "loaded_state"):
            q.QwenBackend(self.root)
        self.assertEqual(factory.call_args.kwargs, {"local_files_only": True, "trust_remote_code": False,
                         "dtype": "FP16", "device_map": q.DEVICE_MAP})
        self.assertEqual(q.DEVICE_MAP["model.language_model.layers.20"], 0)
        self.assertEqual(q.DEVICE_MAP["model.language_model.layers.21"], 1)
        self.assertEqual(q.DEVICE_MAP["model.language_model.embed_tokens"], "cpu")

    def test_qwen_generate_real_orchestration_scripted_towers_raw_before_decode_and_native_custody(self):
        sample=self.root/'sample'
        raw=trace(); ids=raw['generated_ids']; input_ids=[99,98]
        backend=q.QwenBackend.__new__(q.QwenBackend)
        backend.repo=ROOT; backend.snapshot=self.root
        backend.prompt=(ROOT/'configs/pilot/classification_c1.txt').read_text(encoding='utf-8')
        backend.t1=s.probe(Tokenizer())
        def decode(seq, **kw):
            # Native IDs plus every returned raw/processed summary precede the first decode.
            self.assertTrue((sample/'native.json').exists())
            self.assertEqual(len(list((sample/'raw').glob('*.json'))),len(ids))
            self.assertEqual(len(list((sample/'processed').glob('*.json'))),len(ids))
            return Tokenizer().decode(seq,**kw)
        backend.tokenizer=SimpleNamespace(encode=Tokenizer().encode,decode=decode)
        class Input:
            shape=(1,2)
            def __len__(self): return 1
            def __getitem__(self,i): return SimpleNamespace(tolist=lambda:input_ids)
        class Inputs(dict):
            def to(self,device): return self
        backend.processor=SimpleNamespace(apply_chat_template=Mock(return_value=Inputs(input_ids=Input())))
        config=SimpleNamespace(eos_token_id=[0],to_dict=lambda:{'eos_token_id':[0],'num_beams':1,'num_return_sequences':1})
        backend.config=config
        stop_eos=type('EosTokenCriteria',(),{'eos_token_id':SimpleNamespace(tolist=lambda:[0])})()
        stop_length=type('MaxLengthCriteria',(),{'max_length':len(input_ids)+32})()
        model=SimpleNamespace(device='cpu',model=SimpleNamespace(rope_deltas='stale'),_cache='stale',
            _get_logits_processor=lambda:[],_get_stopping_criteria=lambda:[stop_eos,stop_length])
        def generate(**kwargs):
            self.assertEqual(kwargs['max_new_tokens'],32)
            self.assertIsNone(model.model.rope_deltas)
            self.assertTrue((sample/'native_call.json').exists())
            model._get_logits_processor(); model._get_stopping_criteria()
            return SimpleNamespace(sequences=SimpleNamespace(detach=lambda:SimpleNamespace(cpu=lambda:SimpleNamespace(tolist=lambda:[input_ids+ids]))),
                logits=[row['raw'] for row in raw['trace']['steps']],scores=[row['processed'] for row in raw['trace']['steps']])
        model.generate=generate; backend.model=model
        class Image:
            n_frames=1
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def load(self): pass
            def convert(self,*args): return self
        cpu=SimpleNamespace(encode=lambda text,**kw:SimpleNamespace(ids=Tokenizer().encode(text)),decode=Tokenizer().decode)
        official_sha=next(r['sha256'] for r in q.reference()['snapshot_files'] if r['path']=='tokenizer.json')
        with patch.dict(sys.modules,{'torch':SimpleNamespace(inference_mode=nullcontext),
            'PIL':SimpleNamespace(Image=SimpleNamespace(open=lambda _:Image())),
            'tokenizers':SimpleNamespace(Tokenizer=SimpleNamespace(from_file=lambda _:cpu))}), \
             patch.object(q,'loaded_state'), patch.object(q.semantic,'summarize_tensor',side_effect=lambda tensor,*args:tensor), \
             patch.object(q,'sha',return_value=official_sha):
            result=backend.generate('synthetic-only',sample)
        q.validate_raw(sample,result,c.native_identity('qwen3'))
        self.assertEqual(q.replay(result,'Level03')['status'],'HNLO_VALIDATED')
        self.assertIsNone(model._cache)
        self.assertIsNone(model.model.rope_deltas)
        changed=copy.deepcopy(result); changed['input_ids']=[0]
        with self.assertRaises(ValueError): q.validate_raw(sample,changed,c.native_identity('qwen3'))

    def test_qwen_controller_parser_and_recovery_keep_original_fenced_raw(self):
        from safeshift.fulltrain import engine
        cohort=journal.synthetic_cohort(); campaign=c.campaign({k:cohort for k in c.planning.MODELS},digest(cohort))
        spec=c.native_identity('qwen3')
        plan=c.plan(campaign,cohort,spec,[],action='initial',run_id='qrun',attempt_id='qattempt',max_calls=1,max_seconds=30)
        bundle=self.root/'bundle'; bundle.mkdir(); (bundle/'000000.bin').write_bytes(journal.synthetic_bytes(0))
        response='```json\n{"safety_level":"Level02"}\n```'
        class Scripted:
            environment={'scope':'CPU_SCRIPTED_ONLY'}
            def generate(self,image,sample):
                write(sample/'native_call.json',{'invocation':1})
                return {'response':response}
        with patch.object(rt,'validate_native_raw'):
            root=rt._execute(self.root/'work',bundle,cohort,campaign,plan,[],Scripted,
                image_path=lambda i:'000000.bin',evaluator=lambda raw,label:{'status':'SCRIPTED_ONLY','hnlo':None})
        h=rt.recover(root,cohort,digest(plan))
        self.assertEqual(h['records'][0]['label'],'Level02')
        self.assertEqual(read(root/'calls/000000/run/samples/000000/raw.json')['response'],response)
        resume=c.plan(campaign,cohort,spec,[h],action='resume',run_id='qnext',attempt_id='qnext-a',max_calls=1,max_seconds=30)
        self.assertEqual(resume['scheduled_ordinals'],[1])

    def test_qwen_synthetic_snapshot_missing_extra_wrong_hash_revision_and_no_weights_read(self):
        snapshot = self.root / ("a"*40)
        snapshot.mkdir()
        content = b'{"synthetic":true}\n'
        (snapshot / "config.json").write_bytes(content)
        reference = {"model": {"revision": snapshot.name}, "snapshot_files": [
            {"path": "config.json", "size_bytes": len(content), "hash_algorithm": "git_blob_sha1",
             "sha256": hashlib.sha256(content).hexdigest()},
            {"path": "model-00001.safetensors", "size_bytes": 999, "hash_algorithm": "sha256", "expected_hash": "f"*64}]}
        with patch.object(q, "reference", return_value=reference):
            self.assertFalse(q.verify_snapshot(snapshot, weights=False)["weight_bytes_verified"])
            with self.assertRaisesRegex(ValueError, "INVENTORY"): q.verify_snapshot(snapshot)
            (snapshot / "config.json").write_bytes(b'x'*len(content))
            with self.assertRaisesRegex(ValueError, "SHA256"): q.verify_snapshot(snapshot, weights=False)
            (snapshot / "extra.py").write_text('raise AssertionError()')
            with self.assertRaisesRegex(ValueError, "INVENTORY"): q.verify_snapshot(snapshot, weights=False)

    def test_explicit_budget_policy_no_default_or_pooled_gpu(self):
        for key in c.planning.MODELS:
            self.assertEqual(e.policy(key, budgets()), budgets())
        for change in ({"free_mib_per_gpu": [40]}, {"free_ram_mib": True}, {"review_mode": "OWNER"}, {"driver_versions": []}):
            with self.assertRaises(ValueError): e.policy("qwen3", {**budgets(), **change})

    def test_cgroup_ram_and_shared_distinct_disk_reserves(self):
        proc, group = self.root / "meminfo", self.root / "cg"
        proc.write_text('MemAvailable: 20000 kB\n'); group.mkdir()
        (group / "memory.max").write_text('10000'); (group / "memory.current").write_text('9999')
        self.assertEqual(e.host_memory(proc, group)["available_bytes"], 1)
        with patch.object(e, "host_memory", return_value={"available_bytes": 1}):
            with self.assertRaisesRegex(ValueError, "RAM"): e.resources("qwen3", budgets(), self.root, self.root)
        with patch.object(e, "host_memory", return_value={"available_bytes": 10*2**20}), \
             patch.object(e.shutil, "disk_usage", return_value=SimpleNamespace(free=int(1.5*2**20))):
            with self.assertRaisesRegex(ValueError, "SHARED"): e.resources("qwen3", budgets(), self.root, self.root)
        (group / "memory.current").unlink()
        with self.assertRaises(FileNotFoundError): e.host_memory(proc, group)

    def test_hardware_missing_driver_memory_count_and_cuda_probe_each_gpu(self):
        good = "0, Tesla T4, 100, 570.0.0\n1, Tesla T4, 200, 570.0.0\n"
        for text in (good.splitlines()[0], good.replace('200', '1'), good.replace('570.0.0', '525.0.0'), good.replace('T4','P100')):
            with patch.object(e.subprocess, "run", return_value=SimpleNamespace(stdout=text)):
                with self.assertRaises(ValueError): e.hardware("qwen3", budgets())
        with patch.object(e.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError): e.hardware("qwen3", budgets())
        cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 2, get_device_capability=lambda i:(7,5),
            mem_get_info=lambda i:(100*2**20, 1000*2**20), synchronize=Mock())
        torch = SimpleNamespace(version=SimpleNamespace(cuda="12.8"), cuda=cuda, float16="fp16",
            ones=Mock(return_value=SimpleNamespace(sum=lambda:SimpleNamespace(item=lambda:1.))))
        with patch.dict(sys.modules, {"torch":torch}), patch.dict(os.environ,{"CUDA_VISIBLE_DEVICES":"0,1"}):
            self.assertEqual(len(e.cuda("qwen3",budgets())["gpus"]),2)
            self.assertEqual([call.kwargs['device'] for call in torch.ones.call_args_list], ['cuda:0','cuda:1'])
            torch.version.cuda="12.4"
            with self.assertRaises(ValueError): e.cuda("qwen3",budgets())

    def test_qwen_missing_closed_software_lock_fails_before_input_or_gpu(self):
        request=self.request("qwen3")
        with patch.object(a.inputs,"admit") as private:
            with self.assertRaisesRegex(ValueError,"SOFTWARE_LOCK"): a.admit(request)
            private.assert_not_called()

    def test_request_source_plan_marker_and_roots_fail_before_setup(self):
        for mutate in (lambda r:r.update(source_sha256='f'*64), lambda r:r.update(checkpoint_marker_sha256='bad'),
                       lambda r:r.update(scratch=r['work']), lambda r:r['plan'].update(identity={}),
                       lambda r:r.update(history=[{}])):
            req=self.request(); mutate(req)
            with self.assertRaises((ValueError,KeyError)): a.validate_request(req)

    def test_unknown_outputs_and_reservations_block_before_inputs_or_setup(self):
        request=self.request()
        for name in ('unknown-run', 'attempts/unknown.json'):
            path=Path(request['work'])/name
            path.parent.mkdir(parents=True,exist_ok=True); path.write_text('partial')
            with patch.object(a.inputs,'admit') as private:
                with self.assertRaisesRegex(ValueError,'UNKNOWN'): a.admit(request)
                private.assert_not_called()
            path.unlink()

    def test_software_hash_pin_and_missing_python_archive_fail_closed(self):
        root=self.root/'software'; root.mkdir(); (root/'wheels').mkdir()
        marker=root/'fresh_qwen_software.json'
        write(marker,{'schema':'wrong'})
        with self.assertRaisesRegex(ValueError,'MARKER_PIN'): p.software_input(root,'f'*64,{},ROOT)
        with self.assertRaisesRegex(ValueError,'SOFTWARE_MANIFEST'): p.software_input(root,sha(marker),{},ROOT)

    def test_qwen_offline_provision_commands_no_kernel_fallback_or_ensurepip(self):
        request=self.request('qwen3')
        wheel={'file':'pip-25.0.1-py3-none-any.whl','name':'pip','version':'25.0.1',
               'sha256':read(ROOT/'configs/pilot/pip_bootstrap.json')['pip']['sha256']}
        request.update(software_input=str(self.root/'offline-software'),software_marker_sha256='a'*64,
                       runtime_lock={'versions':{'pip':'25.0.1'},'wheels':[wheel]})
        seal={'python_source':{'file':'python.tar.xz'},'zlib_source':{'file':'zlib.tar.gz'}}
        output=self.root/'build-output'; output.mkdir()
        with patch.object(p,'software_input',return_value=seal), patch.object(p,'extract_source'), \
             patch.object(p.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            python,env=p.prepare(request,ROOT,output,time.monotonic()+60)
        commands=[call.args[0] for call in run.call_args_list]
        self.assertTrue(any('--with-ensurepip=no' in cmd for cmd in commands))
        self.assertTrue(any('--without-pip' in cmd for cmd in commands))
        installs=[cmd for cmd in commands if 'install' in cmd and 'make' not in cmd]
        self.assertTrue(all('--no-index' in cmd and '--no-deps' in cmd for cmd in installs))
        self.assertFalse(any('--extra-index-url' in cmd for cmd in commands))
        self.assertTrue(Path(python).is_relative_to(Path(request['scratch'])))
        self.assertEqual(env['CUDA_VISIBLE_DEVICES'],'')
        self.assertEqual(env['PYTORCH_ALLOC_CONF'],'expandable_segments:True')

    def test_cpu_stage_missing_package_or_corrupt_image_never_reaches_gpu_or_native(self):
        request=self.request()
        for kind in ('software','image'):
            out=self.root/kind
            with patch.object(a,'admit',return_value=(self.root,{},[],self.root,self.root,{})), \
                 patch.object(e,'resources',return_value={}), patch.object(e,'hardware') as gpu, \
                 patch.object(e,'software',return_value={},side_effect=ImportError('PIN_MISMATCH') if kind=='software' else None), \
                 patch.object(a,'verify_images',side_effect=ValueError('IMAGE_CORRUPT')), \
                 patch.object(rt,'_worker') as native, patch.dict(os.environ,{'CUDA_VISIBLE_DEVICES':''}):
                with self.assertRaises((ImportError,ValueError)): a.stage('cpu',request,ROOT,out,time.monotonic()+30)
                gpu.assert_not_called(); native.assert_not_called()
            self.assertTrue((out/'failure.json').exists())

    def test_stage_sequence_diagnostic_never_native_and_failure_blocks_following_stages(self):
        for failure in (None,'cpu','gpu'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                req=self.request(); req['work']=str(Path(folder)/'work'); req['scratch']=str(Path(folder)/'scratch')
                Path(req['scratch']).mkdir()
                visited=[]
                def run(command, **kw):
                    mode=command[command.index('--stage')+1]; visited.append(mode)
                    output=Path(command[command.index('--output')+1]); output.mkdir()
                    recorded=read(command[command.index('--request')+1])
                    if mode==failure: raise RuntimeError('SYNTHETIC_STAGE_FAILURE')
                    write(output/'stage.json', {'status':'RETURNED','stage':mode,'request_sha256':digest(recorded),
                        'source_sha256':recorded['source_sha256'],'native_attempt_permitted':mode=='native'})
                    if mode=='setup':
                        write(output/'runtime.json',{'python':str(Path(req['scratch'])/'venv/bin/python'),
                            'env':{'CUDA_VISIBLE_DEVICES':''},'request_sha256':digest(recorded)})
                with patch.object(a.supervision,'run',side_effect=run):
                    output=a.launch_prepared(req, diagnostic=True)
                self.assertNotIn('native',visited)
                if failure=='cpu': self.assertNotIn('gpu',visited)
                self.assertFalse(read(output/'release.json')['attempt_observed'])
                self.assertFalse((Path(req['work'])/'attempts').exists())
                self.assertTrue(Path(str(output)+'.zip').exists())

    def test_closed_stage_cli_fails_before_private_request_and_any_setup(self):
        result=subprocess.run([sys.executable,'-B','-m','safeshift.fulltrain.admission','--request',str(self.root/'PRIVATE')],
            cwd=ROOT,capture_output=True,text=True,timeout=15)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('ISSUE171_NO_GPU',result.stderr)
        self.assertNotIn('FileNotFoundError',result.stderr)

    def test_build_archive_rejects_traversal_links_duplicates_and_retains_sources(self):
        for kind in ('traversal','symlink','duplicate'):
            archive=self.root/(kind+'.tar')
            with tarfile.open(archive,'w') as bundle:
                row=tarfile.TarInfo('../escape' if kind=='traversal' else 'root/file')
                if kind=='symlink': row.type=tarfile.SYMTYPE; row.linkname='/etc/passwd'
                else: row.size=1
                bundle.addfile(row,io.BytesIO(b'x') if kind!='symlink' else None)
                if kind=='duplicate': bundle.addfile(row,io.BytesIO(b'x'))
            with self.assertRaises(ValueError): p.extract_source(archive,self.root/kind)
            self.assertTrue(archive.exists())

    def test_setup_stage_uses_existing_peer_provisioner_after_admission_and_allocation(self):
        request=self.request()
        with patch.object(a,'admit'), patch.object(e,'resources',return_value={'scope':'SYNTHETIC'}), \
             patch('safeshift.candidates.train_runtime.prepare_runtime',return_value=(self.root/'scratch/venv/bin/python',{'CUDA_VISIBLE_DEVICES':''})) as setup:
            a.stage('setup',request,ROOT,self.root/'setup-output',time.monotonic()+30)
        setup.assert_called_once()
        self.assertTrue(read(self.root/'setup-output/allocation.json')['cleanup_verified'])
        self.assertFalse(read(self.root/'setup-output/runtime.json')['weights_loaded'])

    def test_complete_resume_no_setup_gpu_or_attempt(self):
        request=self.request(); request['plan']['scheduled_ordinals']=[]
        visited=[]
        def run(command,**kw):
            mode=command[command.index('--stage')+1]; visited.append(mode)
            output=Path(command[command.index('--output')+1]); output.mkdir()
            recorded=read(command[command.index('--request')+1])
            write(output/'stage.json',{'status':'RETURNED','stage':mode,'request_sha256':digest(recorded),
                'source_sha256':recorded['source_sha256'],'native_attempt_permitted':False})
        with patch.object(a.supervision,'run',side_effect=run): a.launch_prepared(request)
        self.assertEqual(visited,['admit'])


@unittest.skipUnless(sys.platform=='linux','Linux process-group and parent-death control; Kaggle target')
class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root=Path(self.tmp.name)

    def run_child(self, code, seconds=2, cap=100000):
        return sup.run([sys.executable,'-I','-B','-c',code],cwd=self.root,env={**os.environ,'CUDA_VISIBLE_DEVICES':''},
            deadline=time.monotonic()+seconds,log=self.root/'child.log',receipt=self.root/'receipt.json',max_log_bytes=cap,
            watch_log_root=self.root/'stage')

    def test_success_nonzero_and_no_output_overwrite(self):
        self.assertEqual(self.run_child('print("synthetic")')['status'],'EXITED')
        with self.assertRaises(ValueError): self.run_child('raise AssertionError()')
        self.assertEqual(read(self.root/'receipt.json')['status'],'EXITED')

    def test_hung_native_tree_is_killed_and_partial_raw_retained(self):
        code="""import subprocess,sys,time,signal,pathlib,os
signal.signal(signal.SIGTERM,signal.SIG_IGN)
p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'])
pathlib.Path('child.pid').write_text(str(p.pid))
pathlib.Path('raw.partial').write_bytes(b'SYNTHETIC RAW BEFORE HANG')
time.sleep(90)
"""
        began=time.monotonic()
        with self.assertRaisesRegex(RuntimeError,'HARD_DEADLINE'): self.run_child(code)
        self.assertLess(time.monotonic()-began,8)
        self.assertEqual((self.root/'raw.partial').read_bytes(),b'SYNTHETIC RAW BEFORE HANG')
        pid=int((self.root/'child.pid').read_text())
        for _ in range(20):
            stat=Path(f'/proc/{pid}/stat')
            if not stat.exists() or stat.read_text().split()[2]=='Z': break
            time.sleep(.05)
        else: self.fail('grandchild survived deadline')
        self.assertFalse(read(self.root/'receipt.json')['automatic_retry'])

    def test_large_internal_setup_log_stops_without_truncating(self):
        code="import pathlib,time; p=pathlib.Path('stage'); p.mkdir(); (p/'setup.log').write_bytes(b'x'*10000); time.sleep(90)"
        with self.assertRaisesRegex(RuntimeError,'LOG_BUDGET'): self.run_child(code,cap=100)
        self.assertEqual((self.root/'stage/setup.log').stat().st_size,10000)

    def test_deadline_expired_before_launch(self):
        with patch.object(sup.subprocess,'Popen') as spawn:
            with self.assertRaises(ValueError):
                sup.run(['anything'],cwd=self.root,env={},deadline=time.monotonic()-1,log=self.root/'log',
                    receipt=self.root/'receipt',max_log_bytes=1)
            spawn.assert_not_called()

    def test_parent_death_terminates_guard_and_native_descendants(self):
        code="""import os,pathlib,time
pathlib.Path('native.pid').write_text(str(os.getpid()))
time.sleep(90)
"""
        supervisor_code="import sys,time,os; from pathlib import Path; from safeshift.fulltrain.supervision import run; run([sys.executable,'-c',"+repr(code)+"],cwd=Path.cwd(),env=os.environ.copy(),deadline=time.monotonic()+60,log=Path('log'),receipt=Path('receipt'),max_log_bytes=100000)"
        parent=subprocess.Popen([sys.executable,'-B','-c',supervisor_code],cwd=self.root,
            env={**os.environ,'PYTHONPATH':str(ROOT)},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: parent.kill() if parent.poll() is None else None)
        until=time.monotonic()+8
        while not (self.root/'native.pid').exists() and time.monotonic()<until: time.sleep(.05)
        self.assertTrue((self.root/'native.pid').exists())
        pid=int((self.root/'native.pid').read_text())
        parent.kill(); parent.wait(timeout=5)
        for _ in range(50):
            path=Path(f'/proc/{pid}/stat')
            if not path.exists() or path.read_text().split()[2]=='Z': break
            time.sleep(.05)
        else: self.fail('native child survived supervisor death')


if __name__=='__main__': unittest.main()
