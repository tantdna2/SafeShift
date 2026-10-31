"""Isolated effective-config/history contracts and real native CPU numerics."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

from safeshift.candidates import train_contract as c, train_smoke as smoke, train_run as run
from safeshift.candidates import minicpm_resampler_fp32 as numerical
from safeshift.pilot.artifacts import read, write, export, verify_archive, sha
from safeshift.pilot.contract import digest


class EffectiveContractTests(unittest.TestCase):
    def test_new_identity_config_and_no_scientific_or_production_permission(self):
        original = smoke.execution("minicpm4", "c"*64, "a"*40)
        altered = smoke.execution("minicpm4", "c"*64, "a"*40, implementation=numerical.ID)
        self.assertNotEqual(altered["campaign"], original["campaign"])
        self.assertEqual(altered["series_id"], altered["run_id"])
        self.assertNotEqual(altered["candidate_execution_config_sha256"], original["candidate_execution_config_sha256"])
        self.assertEqual(altered["legacy_transport_config_sha256"], original["legacy_transport_config_sha256"])
        self.assertEqual(altered["model"], original["model"])
        self.assertEqual(altered["max_native_calls"], 1)
        self.assertFalse(altered["resume"])
        c.authorize(altered, "minicpm4", "c"*64, "a"*40, None)
        self.assertIn("effective_implementation", c.execution_binding(altered))
        value = c.config("minicpm4", implementation=numerical.ID)
        before = c.config("minicpm4")
        self.assertEqual(value["effective_candidate"]["dtype"], "float16")
        for field in ("model", "preprocessing", "logits", "generation", "selection", "attention", "checkpoint_lock_sha256", "public_source_lock_sha256"):
            self.assertEqual(value["effective_candidate"][field], before["effective_candidate"][field])
        for field, replacement in (("max_native_calls",160),("resume",True),("effective_implementation","unknown"),("series_id", original["run_id"])):
            invalid = copy.deepcopy(altered)
            invalid[field] = replacement
            with self.assertRaises(ValueError):
                c.authorize(invalid, "minicpm4", "c"*64, "a"*40, None)
        with self.assertRaises(ValueError):
            smoke.execution("internvl35", "c"*64, "a"*40, implementation=numerical.ID)

    def test_different_implementation_raw_cannot_be_recovered_or_imported_as_production(self):
        from test_candidate160 import fixture, Scripted
        from safeshift.candidates import train_history as history
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            out = root / "effective"
            out.mkdir()
            g = smoke.execution("minicpm4", "c"*64, "a"*40, implementation=numerical.ID)
            class SyntheticEffective(Scripted):
                def generate(self, image, sample):
                    result = super().generate(image, sample)
                    names = ("scores_fp32_finite_or_negative_mask", "softmax_fp32_finite", "value_product_fp32_finite_and_return_cast")
                    write(sample / "effective_numerics.json", {"implementation": numerical.descriptor(),
                        "before": {**dict.fromkeys(names,0),"returned_dtype":None},
                        "after": {**dict.fromkeys(names,1),"returned_dtype":"torch.float16"}})
                    return result
            native = SyntheticEffective(key="minicpm4")
            results, reason = run.run_calls(out, plan, rows, lambda:native, g, resources=lambda:{})
            self.assertIsNone(reason)
            self.assertEqual(native.calls,1)
            self.assertEqual(results[rows[0]["sample_id"]]["status"], "SUCCESS")
            self.assertIsNone(read(out/"summary.json")["metrics"])
            wrong = copy.deepcopy(g)
            wrong.pop("effective_implementation")
            wrong.update(c.configuration_hashes("minicpm4"))
            self.assertEqual(run.recover(out, rows, wrong)[rows[0]["sample_id"]]["status"],"TECHNICAL_ERROR")
            archive = root/"effective.zip"
            export(out,archive)
            verify_archive(archive)
            before=sha(archive)
            work=root/"prod"
            work.mkdir()
            inputs=root/"input"
            inputs.mkdir()
            new=work/"new"
            new.mkdir()
            # A fake owner_execution wrapping the technical record is rejected;
            # the new schema/config cannot become production completion.
            write(out/"owner_execution.json",g)
            with self.assertRaises(ValueError):
                history._scope(out,"minicpm4")
            self.assertEqual(sha(archive),before)

    def test_effective_launcher_rejects_unknown_implementation_and_isolates_smoke(self):
        from safeshift.candidates import train_runtime as rt
        from safeshift.candidates.source import ROOT
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            inputs=root/"input"
            inputs.mkdir()
            with self.assertRaisesRegex(ValueError,"UNKNOWN_EFFECTIVE_IMPLEMENTATION"):
                rt.launch("minicpm4",c.source_hash(),ROOT,"a"*40,owner_start=True,
                    recovery_action="rerun",implementation="unknown",work=root/"out",inputs=inputs)
            out=rt.launch_owner("minicpm4",c.source_hash(),ROOT,"a"*40,owner_start=True,
                action="technical_smoke_resampler_fp32_v1",work=root/"out",inputs=inputs)
            self.assertEqual(out.parent.name,"out_smoke_resampler_fp32_v1")
            self.assertFalse((out/"owner_execution.json").exists())
            self.assertEqual(read(out/"technical_execution.json")["effective_implementation"],numerical.ID)
            self.assertFalse(list((root/"out").rglob("*.json")))
            self.assertEqual(read(Path(str(out)+".smoke-result.json"))["status"],"BLOCKED_NOT_VERIFIED")

    def test_effective_notebook_is_reproducible_and_only_has_one_image_route(self):
        from safeshift.candidates.source import ROOT
        from scripts.build_candidate160_notebooks import effective_notebook
        path=ROOT/"notebooks/SafeShift_CANDIDATE160_MINICPM4_FP32_ATTENTION_SMOKE.ipynb"
        if not path.exists(): self.skipTest("generate exact-commit notebook before notebook check")
        nb=read(path)
        self.assertEqual(nb,effective_notebook(nb["metadata"]["safeshift"]["runtime_ref"]))
        self.assertEqual(nb["metadata"]["safeshift"]["max_images"],1)
        code="\n".join("".join(cell["source"]) for cell in nb["cells"] if cell["cell_type"]=="code")
        compile(code,"effective-notebook","exec")
        self.assertIn('action="technical_smoke_resampler_fp32_v1")',code)
        self.assertNotIn('action=candidate160_action)',code)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            script=root/"notebook.py"
            script.write_text(code,encoding="utf-8")
            process=subprocess.run([sys.executable,"-I","-B",str(script)],cwd=root,
                capture_output=True,text=True,timeout=60)
            self.assertEqual(process.returncode,0,process.stderr)
            archive,=(root/"data/processed/candidate160_smoke_resampler_fp32_v1").glob("*.zip")
            verify_archive(archive)
            self.assertFalse(list((root/"data/processed/candidate160").glob("*.json")))


@unittest.skipUnless(os.environ.get("SAFESHIFT_NUMERICS_SNAPSHOT"), "locked public MiniCPM source and isolated torch stack required")
class NativeResamplerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        cls.torch=torch
        snapshot=Path(os.environ["SAFESHIFT_NUMERICS_SNAPSHOT"])
        cls.path=snapshot/"resampler.py"
        cls.source_before=sha(cls.path)
        spec=importlib.util.spec_from_file_location("locked_fp32_resampler_tests",cls.path)
        cls.module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=cls.module
        spec.loader.exec_module(cls.module)
        cls.addClassCleanup(lambda:sys.modules.pop(spec.name,None))

    def attention(self):
        torch=self.torch
        attention=self.module.MultiheadAttention(4,1).half().eval()
        with torch.no_grad():
            attention.in_proj_weight.zero_()
            attention.in_proj_bias.zero_()
            for i in range(3):
                attention.in_proj_weight[i*4:(i+1)*4].copy_(torch.eye(4,dtype=torch.float16))
            attention.out_proj.weight.copy_(torch.eye(4,dtype=torch.float16))
            attention.out_proj.bias.zero_()
        return attention

    def test_original_overflows_and_effective_finite_matches_fp32_reference(self):
        torch=self.torch
        with torch.no_grad():
            attention=self.attention()
            q=torch.full((2,1,4),1024.,dtype=torch.float16)
            k=q.clone()
            v=torch.tensor([[[1.,2.,3.,4.]], [[3.,4.,5.,6.]]],dtype=torch.float16)
            native,_=attention(q,k,v)
            self.assertFalse(bool(torch.isfinite(native).all()))
            original={n:p.clone() for n,p in attention.named_parameters()}
            cls_method=type(attention).multi_head_attention_forward
            evidence=numerical.install_attention(attention)
            actual,probabilities=attention(q,k,v)
            reference=torch.full((2,1,4),0.,dtype=torch.float32)
            reference[:]=v.float().mean(dim=0)
            self.assertTrue(bool(torch.isfinite(actual).all()))
            self.assertTrue(torch.equal(actual,reference.half()))
            self.assertEqual(actual.dtype,torch.float16)
            self.assertEqual(probabilities.dtype,torch.float32)
            self.assertIs(type(attention).multi_head_attention_forward,cls_method)
            self.assertTrue(all(torch.equal(p,original[n]) and p.dtype==torch.float16 for n,p in attention.named_parameters()))
            self.assertEqual(sha(self.path),self.source_before)
            self.assertNotEqual(evidence["native_method_sha256"],evidence["derived_method_sha256"])
            self.assertEqual(attention._safeshift_numerics["softmax_fp32_finite"],1)
            with self.assertRaises(ValueError): numerical.install_attention(attention)

    def test_zero_mask_partial_mask_all_mask_and_unsupported_modes(self):
        torch=self.torch
        with torch.no_grad():
            a=self.attention()
            numerical.install_attention(a)
            q=torch.ones((2,1,4),dtype=torch.float16)
            v=torch.arange(8,dtype=torch.float16).view(2,1,4)
            result,_=a(q,q,v,key_padding_mask=torch.tensor([[False,True]]))
            self.assertTrue(torch.equal(result,v[0:1].expand_as(result)))
            with self.assertRaisesRegex(ValueError,"NONFINITE_SOFTMAX"):
                a(q,q,v,key_padding_mask=torch.tensor([[True,True]]))
            with self.assertRaisesRegex(ValueError,"EAGER_EVAL_ZERO_DROPOUT"):
                a(q,q,v,need_weights=False)
            a.train()
            with self.assertRaisesRegex(ValueError,"EAGER_EVAL_ZERO_DROPOUT"):
                a(q,q,v)

    def test_nonuniform_native_attention_matches_independent_scalar_oracle(self):
        import math
        torch=self.torch
        with torch.no_grad():
            a=self.attention()
            numerical.install_attention(a)
            q=torch.tensor([[[2.,-1.,.5,3.]],[[.25,1.,-2.,.5]]],dtype=torch.float16)
            k=torch.tensor([[[1.,2.,3.,4.]], [[-1.,.5,2.,0.]], [[2.,-1.,0.,1.]]],dtype=torch.float16)
            v=torch.tensor([[[1.,3.,5.,7.]], [[2.,4.,6.,8.]], [[-1.,-3.,-5.,-7.]]],dtype=torch.float16)
            actual,probabilities=a(q,k,v,key_padding_mask=torch.tensor([[False,True,False]]))
            expected=[]
            for query in q[:,0].tolist():
                scores=[sum((query[t]/2)*key[t] for t in range(4)) for key in k[:,0].tolist()]
                scores[1]=-math.inf
                weights=[math.exp(s-max(scores)) for s in scores]
                weights=[w/sum(weights) for w in weights]
                expected.append([sum(weights[i]*float(v[i,0,j]) for i in range(3)) for j in range(4)])
            target=torch.tensor(expected,dtype=torch.float16).view(2,1,4)
            self.assertTrue(torch.allclose(actual,target,atol=.004,rtol=.002))
            self.assertTrue(bool(torch.isfinite(probabilities).all()))

    def test_changed_native_source_rejected_before_binding(self):
        def unrelated(): pass
        with self.assertRaises(ValueError): numerical.rewritten_method(unrelated)


if __name__=="__main__": unittest.main()
