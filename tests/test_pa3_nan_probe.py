"""PA3 Qwen FP16 non-finite probe; synthetic CPU weights, never real model/data.

Model tests run the pinned upstream Transformers 4.51.3 Qwen2.5-VL code on a tiny
random configuration. They reproduce the archived symptom shape (all step-0 raw
logits NaN, argmax token 0) from one injected FP16 overflow. They do not show
that the archived Shard 0 failure had this cause; that needs the approved GPU probe.
"""

import importlib.metadata
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.pa3.native import nan_probe

SAMPLE = "s|DATA_PATH/train/Annotations/Normal_data/x/x-001.jpg|" + "a" * 64


def pinned_upstream():
    if not (importlib.util.find_spec("torch") and importlib.util.find_spec("transformers")):
        return False
    return importlib.metadata.version("transformers") == "4.51.3"


class GateTests(unittest.TestCase):
    def repo(self, text):
        root = Path(tempfile.mkdtemp())
        (root / "DECISIONS.md").write_text(text, encoding="utf-8")
        return root

    def test_proposed_or_missing_decision_blocks_before_any_access(self):
        for text in ("", "DEC-PA3-009 status: PROPOSED_NOT_APPROVED\n",
                     "x DEC-PA3-009 status: APPROVED_FOR_NAN_LOCALIZATION\n"):
            repo = self.repo(text)
            with patch.object(nan_probe, "launch") as launch, patch.object(nan_probe, "run") as run, \
                    self.assertRaises(PermissionError):
                nan_probe.main(["--repo", str(repo), "--decision", "DEC-PA3-009", "--sample", SAMPLE,
                                "--output", str(repo / "out.json"), "--launch"])
            launch.assert_not_called()
            run.assert_not_called()

    def test_approved_line_dispatches_once_and_never_overwrites(self):
        repo = self.repo("DEC-PA3-009 status: APPROVED_FOR_NAN_LOCALIZATION\n")
        argv = ["--repo", str(repo), "--decision", "DEC-PA3-009", "--sample", SAMPLE,
                "--output", str(repo / "out.json"), "--launch"]
        with patch.object(nan_probe, "launch", return_value=0) as launch:
            nan_probe.main(argv)
        launch.assert_called_once()
        (repo / "out.json").write_text("{}", encoding="utf-8")
        with patch.object(nan_probe, "launch") as launch, self.assertRaises(FileExistsError):
            nan_probe.main(argv)
        launch.assert_not_called()

    def test_launch_verifies_runtime_before_restore_and_runs_one_offline_child(self):
        repo = self.repo("DEC-PA3-009 status: APPROVED_FOR_NAN_LOCALIZATION\n")
        plan = repo / nan_probe.PLAN
        plan.parent.mkdir(parents=True)
        plan.write_text("{}", encoding="utf-8")
        calls = []
        record = lambda name, value=None: (lambda *a, **k: calls.append(name) or value)
        args = nan_probe.argparse.Namespace(
            repo=repo, inputs="in", runtime_input="rt.tar", runtime_inventory_input="inv.json",
            runtime_inventory_sha256="b" * 64, runtime_site_packages=None, model_input="m.tar",
            dataset_input="train", decision="DEC-PA3-009", sample=[SAMPLE, SAMPLE], candidate_clamp=True,
            output=repo / "out.json")
        with patch("safeshift.ls1.kaggle.attached_path", side_effect=lambda root, rel: Path(root) / rel), \
                patch("safeshift.ls1.kaggle.verify_runtime_input", record("verify")), \
                patch("safeshift.ls1.kaggle.restore_model", record("restore", Path("snap"))), \
                patch("safeshift.ls1.kaggle.runtime_interpreter",
                      record("runtime", {"python": "py", "site_packages": None})), \
                patch.object(nan_probe.subprocess, "run",
                             return_value=nan_probe.subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(nan_probe.launch(args), 0)
        self.assertEqual(calls, ["verify", "restore", "runtime"])
        run.assert_called_once()
        command, env = run.call_args.args[0], run.call_args.kwargs["env"]
        self.assertEqual(command[:4], ["py", "-s", "-m", "safeshift.pa3.native.nan_probe"])
        self.assertEqual(command.count("--sample"), 2)
        self.assertIn("--candidate-clamp", command)
        self.assertNotIn("--launch", command)
        self.assertEqual((env["HF_HUB_OFFLINE"], env["CUDA_VISIBLE_DEVICES"]), ("1", "0"))
        self.assertTrue(run.call_args.kwargs["check"])

    def test_only_explicit_train_triplets(self):
        self.assertEqual(nan_probe.parse_samples([SAMPLE])[0]["sample_id"], "s")
        for bad in ("s|DATA_PATH/test/x.jpg|" + "a" * 64, "s|DATA_PATH/train/x.jpg|abc",
                    "s|/abs/DATA_PATH/train/x.jpg|" + "a" * 64, "s|DATA_PATH/train/x.jpg"):
            with self.assertRaises(ValueError):
                nan_probe.parse_samples([bad])


@unittest.skipUnless(pinned_upstream(), "requires torch and pinned transformers==4.51.3 (CPU)")
class UpstreamQwenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        from transformers import Qwen2_5_VLConfig, Qwen2_5_VLForConditionalGeneration
        cls.torch = torch
        torch.manual_seed(0)
        cls.config = Qwen2_5_VLConfig(
            vision_config=dict(depth=4, hidden_size=32, intermediate_size=64, num_heads=2, out_hidden_size=64,
                               patch_size=14, spatial_merge_size=2, temporal_patch_size=2, window_size=56,
                               fullatt_block_indexes=[3], in_chans=3),
            hidden_size=64, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
            intermediate_size=128, vocab_size=151936, max_position_embeddings=512,
            rope_scaling={"type": "mrope", "mrope_section": [2, 3, 3]}, attn_implementation="sdpa",
            image_token_id=151655, video_token_id=151656, vision_start_token_id=151652,
            vision_end_token_id=151653)
        cls.state = Qwen2_5_VLForConditionalGeneration(cls.config).eval().state_dict()
        cls.factory = Qwen2_5_VLForConditionalGeneration
        cls.ids = torch.tensor([[151644, 872, 198, 151652] + [151655] * 8 +
                                [151653, 13, 151645, 198, 151644, 77091, 198]])
        cls.pixels = torch.randn(32, 3 * 2 * 14 * 14)

    def model(self, dtype=None, edit=None):
        model = self.factory(self.config).eval()
        model.load_state_dict(self.state)
        model = model.to(dtype or self.torch.float16)
        if edit:
            with self.torch.no_grad():
                edit(model.visual.blocks)
        return model

    def generate(self, model, clamp=False):
        torch = self.torch
        handle = nan_probe.install_merger_clamp(model, torch) if clamp else None
        try:
            with nan_probe.NonfiniteProbe(model, torch) as probe, torch.inference_mode():
                model.rope_deltas = None
                output = model.generate(input_ids=self.ids, attention_mask=torch.ones_like(self.ids),
                                        pixel_values=self.pixels.to(model.dtype),
                                        image_grid_thw=torch.tensor([[1, 4, 8]]), max_new_tokens=1,
                                        do_sample=False, return_dict_in_generate=True, output_logits=True)
        finally:
            if handle:
                handle.remove()
        return output.logits[0], probe

    @staticmethod
    def last_mlp_residual(blocks):
        blocks[-1].attn.proj.bias[0] = 40000.0  # each operand finite in FP16; sum 80000
        blocks[-1].mlp.down_proj.bias[0] = 40000.0

    def test_last_vit_residual_overflow_reproduces_all_nan_bang_symptom_then_clamp_restores(self):
        logits, probe = self.generate(self.model(edit=self.last_mlp_residual))
        self.assertEqual(int(logits.isnan().sum()), logits.numel())  # fails before the candidate
        self.assertEqual(int(logits[0].argmax()), 0)  # Qwen token 0 decodes to "!"
        origin = probe.origin
        self.assertEqual((origin["kind"], origin["block"]), ("MLP_RESIDUAL_ADD", "visual.blocks.3"))
        self.assertTrue(origin["recompute"]["exceeds_fp16_max"])
        self.assertEqual(origin["recompute"]["fp32_absmax"], 80000.0)
        first_nan = next(e for e in probe.events if e["output"] and e["output"]["nan"])
        self.assertEqual(first_nan["module"], "visual.merger.ln_q")  # RMSNorm: inf * rsqrt(inf) = NaN
        clamped, _ = self.generate(self.model(edit=self.last_mlp_residual), clamp=True)
        self.assertTrue(bool(self.torch.isfinite(clamped).all()))  # passes after the candidate
        reference, ref_probe = self.generate(self.model(self.torch.float32, self.last_mlp_residual))
        self.assertTrue(bool(self.torch.isfinite(reference).all()))
        self.assertIsNone(ref_probe.origin)

    def test_clamp_is_bitwise_identity_without_overflow_and_probe_is_passive(self):
        baseline, probe = self.generate(self.model())
        self.assertIsNone(probe.origin)
        clamped, _ = self.generate(self.model(), clamp=True)
        self.assertTrue(nan_probe.bitwise_equal(baseline, clamped, self.torch))
        model = self.model()
        with self.torch.inference_mode():
            plain = model.generate(input_ids=self.ids, attention_mask=self.torch.ones_like(self.ids),
                                   pixel_values=self.pixels.half(), image_grid_thw=self.torch.tensor([[1, 4, 8]]),
                                   max_new_tokens=1, do_sample=False, return_dict_in_generate=True,
                                   output_logits=True).logits[0]
        self.assertTrue(nan_probe.bitwise_equal(plain, baseline, self.torch))
        self.assertEqual(len(model.visual.merger._forward_pre_hooks), 0)

    def test_early_overflow_stays_nan_with_clamp_never_masked(self):
        def first_block(blocks):
            blocks[0].attn.proj.bias[0] = 40000.0
            blocks[0].mlp.down_proj.bias[0] = 40000.0
        logits, probe = self.generate(self.model(edit=first_block), clamp=True)
        self.assertEqual(int(logits.isnan().sum()), logits.numel())
        self.assertEqual(probe.origin["block"], "visual.blocks.0")

    def test_attention_residual_and_linear_origins_are_distinguished(self):
        def attention(blocks):
            blocks[2].mlp.down_proj.bias[0] = 30000.0
            blocks[3].attn.proj.bias[0] = 60000.0
        _, probe = self.generate(self.model(edit=attention))
        self.assertEqual((probe.origin["kind"], probe.origin["module"]),
                         ("ATTENTION_RESIDUAL_ADD", "visual.blocks.3.norm2"))
        self.assertTrue(probe.origin["recompute"]["exceeds_fp16_max"])

        def linear(blocks):  # known positive input 10*1 per element; 64 * 10 * 200 = 128000
            mlp = blocks[3].mlp
            for proj, bias in ((mlp.gate_proj, 10.0), (mlp.up_proj, 1.0)):
                proj.weight.zero_()
                proj.bias.fill_(bias)
            mlp.down_proj.weight[0, :] = 200.0
        _, probe = self.generate(self.model(edit=linear))
        self.assertEqual((probe.origin["kind"], probe.origin["module"]),
                         ("LINEAR", "visual.blocks.3.mlp.down_proj"))
        self.assertTrue(probe.origin["recompute"]["exceeds_fp16_max"])

    def test_cast_overflow_semantics(self):
        torch = self.torch
        finite = torch.tensor([1.0, -2.0], dtype=torch.float16)
        self.assertIs(nan_probe.cast_overflow_fp16(finite, torch), finite)
        out = nan_probe.cast_overflow_fp16(torch.tensor([float("inf"), float("-inf"), float("nan"), 3.0],
                                                        dtype=torch.float16), torch)
        self.assertEqual(out[:2].tolist(), [64512.0, -64512.0])  # 65504 - 1000 rounded to FP16
        self.assertTrue(bool(out[2].isnan()))
        self.assertEqual(float(out[3]), 3.0)
        wide = torch.tensor([float("inf")])
        self.assertIs(nan_probe.cast_overflow_fp16(wide, torch), wide)


if __name__ == "__main__":
    unittest.main()
