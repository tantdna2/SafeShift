"""Bounded production engineering scopes, recovery and scientific gate regressions."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from safeshift.candidates import train_contract as c, train_history as h, train_owner as owner
from safeshift.candidates import train_run as run, train_route as route, train_runtime as rt
from safeshift.candidates.minicpm_resampler_fp32 import ID, descriptor
from safeshift.pilot.artifacts import read, write, export, sha
from safeshift.pilot.contract import parse_label
from safeshift.pilot.hnlo import replay
from test_candidate160 import fixture, Scripted, raw
from test_candidate160_recovery import StopAfter


class EffectiveScripted(Scripted):
    def generate(self, image, sample):
        result = super().generate(image, sample)
        names = ("scores_fp32_finite_or_negative_mask", "softmax_fp32_finite", "value_product_fp32_finite_and_return_cast")
        write(sample / "effective_numerics.json", {"implementation": descriptor(),
              "before": dict.fromkeys(names, 0),
              "after": {**dict.fromkeys(names, 1), "returned_dtype": "torch.float16"}})
        return result


def start(work, inputs, *, implementation=None, qualification=True, action="resume"):
    output = work / ("minicpm4-" + __import__("uuid").uuid4().hex)
    output.mkdir()
    index = h.collect(work, inputs, output, "minicpm4", implementation=implementation, qualification=qualification)
    g = h.execution("minicpm4", "c"*64, "a"*40, index, owner_start=True, action=action,
                    implementation=implementation, qualification=qualification)
    write(output / "owner_execution.json", g)
    return output, g


def calls(out, g, plan, rows, native):
    write(out / "recovery_plan.json", h.recovery_plan(out, rows, g))
    return run.run_calls(out, plan, rows, lambda: native, g, resources=lambda: {})


class RouteTests(unittest.TestCase):
    def test_delivered_production_notebooks_are_exact_reproducible_bounded_routes(self):
        from scripts.build_candidate160_notebooks import production_notebook
        for key in c.KEYS:
            suffix = "_FP32" if key == "minicpm4" else ""
            path = c.ROOT/f"notebooks/SafeShift_CANDIDATE160_PRODUCTION_{key}{suffix}.ipynb"
            if not path.exists():
                self.skipTest("build exact-commit production notebooks first")
            nb = read(path)
            self.assertEqual(nb, production_notebook(key, nb["metadata"]["safeshift"]["runtime_ref"]))
            code = "".join(nb["cells"][1]["source"])
            compile(code, path.name, "exec")
            self.assertIn('candidate160_action = "qualify"', code)
            self.assertIn("verify_portable_recovery(evidence", code)
            self.assertEqual(nb["metadata"]["safeshift"]["technical_ordinals"], route.ORDINALS)

    def test_three_fixed_cases_not_outcome_selected_and_caps_cannot_be_relaxed(self):
        rows = [{"width": 100, "height": 100, "sample_id": str(i), "image_sha256": "c"*64} for i in range(160)]
        rows[15].update(width=10, height=10)
        rows[111].update(width=100, height=200)
        self.assertEqual(route.selection(rows)["ordinals"], [0, 15, 111])
        g = h.execution("minicpm4", "c"*64, "a"*40,
                        {"runs": {}, **route.fields(ID, True)}, owner_start=True,
                        implementation=ID, qualification=True)
        c.authorize(g, "minicpm4", "c"*64, "a"*40, None)
        for field, value in (("max_native_calls", 160), ("technical_qualification", "other"),
                             ("effective_implementation", "other"), ("max_seconds", 43200)):
            bad = {**g, field: value}
            with self.assertRaises(ValueError):
                c.authorize(bad, "minicpm4", "c"*64, "a"*40, None)

    def test_official_fp32_gate_before_inputs_workers_and_owner_record_cannot_approve_it(self):
        wrong = owner.execution("minicpm4", "c"*64, "a"*40, owner_start=True,
                                implementation=ID, qualification=True)
        with self.assertRaisesRegex(ValueError, "QUALIFICATION_REQUIRES_RECOVERY_SCHEMA"):
            c.authorize(wrong, "minicpm4", "c"*64, "a"*40, None)
        g = owner.execution("minicpm4", "c"*64, "a"*40, owner_start=True, implementation=ID)
        with self.assertRaisesRegex(ValueError, "BLOCKED_PENDING_SCIENTIFIC_DECISION"):
            c.authorize(g, "minicpm4", "c"*64, "a"*40, None)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "BLOCKED_PENDING_SCIENTIFIC_DECISION"):
                rt.launch_owner("minicpm4", "c"*64, Path(d), "a"*40, owner_start=True,
                                implementation=ID, action="resume", work=Path(d)/"out")
            self.assertFalse(list(Path(d).rglob("*.json")))

    def test_real_controller_three_calls_resume_noop_rerun_new_series_and_arithmetic_isolation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            work, inputs = root/"out", root/"input"
            work.mkdir(); inputs.mkdir()
            first, g1 = start(work, inputs, implementation=ID)
            native = EffectiveScripted(key="minicpm4")
            results, reason = calls(first, g1, plan, rows, native)
            self.assertIsNone(reason)
            self.assertEqual(native.calls, 3)
            self.assertEqual([i for i,r in enumerate(rows) if results[r["sample_id"]]["native_calls"]], route.ORDINALS)
            self.assertIsNone(read(first/"summary.json")["metrics"])
            self.assertEqual(read(first/"summary.json")["scientific_selection"], "EXCLUDED")
            before = h.members(first)
            second, g2 = start(work, inputs, implementation=ID)
            self.assertEqual(h.recovery_plan(second, rows, g2)["pending_ordinals"], [])
            self.assertEqual(g1["series_id"], g2["series_id"])
            self.assertEqual(h.members(first), before)
            third, g3 = start(work, inputs, implementation=ID, action="rerun")
            self.assertNotEqual(g3["series_id"], g1["series_id"])
            self.assertEqual(h.recovery_plan(third, rows, g3)["pending_ordinals"], route.ORDINALS)
            baseline, gb = start(work, inputs, qualification=False)
            self.assertFalse(read(baseline/"history_index.json")["runs"])
            self.assertEqual(len(h.recovery_plan(baseline, rows, gb)["pending_ordinals"]), 160)
            self.assertNotEqual(gb["slot_sha256"], g1["slot_sha256"])

    def test_scoped_load_failure_oom_and_nonfinite_keep_pending_and_stop(self):
        for fault in (RuntimeError("SYNTHETIC load failure"), RuntimeError("SYNTHETIC CUDA out of memory"), "nonfinite"):
            with self.subTest(fault=str(fault)), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                plan, rows = fixture(root)
                work, inputs = root/"out", root/"input"
                work.mkdir(); inputs.mkdir()
                out, g = start(work, inputs)
                if fault == "nonfinite":
                    value = raw("Level02")
                    value["steps"][0]["all_finite"] = False
                    native = Scripted(key="minicpm4", value=value)
                else:
                    native = Scripted(key="minicpm4", fault=fault)
                _, reason = calls(out, g, plan, rows, native)
                self.assertIsNotNone(reason)
                self.assertEqual(native.calls, 1)
                again, next_g = start(work, inputs)
                self.assertEqual(h.recovery_plan(again, rows, next_g)["pending_ordinals"], route.ORDINALS)

    def test_raw_without_result_replay_and_zip_only_cross_vm_resume(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            work, inputs = root/"out", root/"input"
            work.mkdir(); inputs.mkdir()
            out, g = start(work, inputs, implementation=ID)
            calls(out, g, plan, rows, EffectiveScripted(key="minicpm4"))
            # Simulate interruption between durable raw and result write.
            (out/"calls/000015/run/samples/000000/result.json").unlink()
            attached = inputs/"attached-output"
            attached.mkdir()
            archive = attached/(out.name+".zip")
            export(out, archive)
            before = sha(archive)
            fresh = root/"fresh"; fresh.mkdir()
            resumed, g2 = start(fresh, inputs, implementation=ID)
            self.assertEqual(h.recovery_plan(resumed, rows, g2)["pending_ordinals"], [])
            self.assertEqual(sha(archive), before)
            # Changed raw after sealing must fail before any model load.
            (out/"calls/000000/run/samples/000000/raw.json").write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "HISTORY_SEAL_MISMATCH"):
                start(work, inputs, implementation=ID)

    def test_invalid_fence_and_alternative_token_segmentation_stay_truthful(self):
        value = raw("Level02")
        value["response"] = '```json\n{"safety_level":"Level02"}\n```'
        self.assertIsNone(parse_label(value["response"]))
        self.assertNotEqual(replay(value, None)["status"], "HNLO_VALIDATED")
        value = raw("Level02")
        # Same text from another native first token is not the proven sequence.
        value["generated_ids"][0] += 100000
        value["steps"][0]["argmax"] = value["generated_ids"][0]
        outcome = replay(value, "Level02")
        self.assertEqual(outcome["reason"], "ACTUAL_OUTPUT_NOT_ONE_OF_PROVEN_NATIVE_CONTINUATIONS")
        self.assertIsNone(outcome["hnlo"])

    def test_portable_probe_real_supervisor_noop_never_provisions_or_loads(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan, rows = fixture(root)
            for r in rows:
                r.update(width=100, height=100)
            rows[15].update(width=10, height=10)
            rows[111].update(width=100, height=200)
            plan["main"] = rows
            work, inputs = root/"out", root/"input"
            work.mkdir()
            inputs.mkdir()
            out, g = start(work, inputs, implementation=ID)
            calls(out, g, plan, rows, EffectiveScripted(key="minicpm4"))
            write(out/"pilot_manifest.json", plan)
            export(out, Path(str(out)+".zip"))
            write(Path(str(out)+".qualification-result.json"), {"status": "TECHNICAL_QUALIFICATION_PASS"})
            with patch.object(rt, "source_hash", return_value="c"*64), \
                 patch.object(rt, "manifest", return_value=(plan, rows)), \
                 patch.object(rt, "prepare_runtime", side_effect=AssertionError("NOOP_MUST_NOT_SETUP")), \
                 patch.object(rt, "hardware", side_effect=AssertionError("NOOP_MUST_NOT_PROBE_GPU")):
                resumed = route.verify_portable_recovery(out, "minicpm4", "c"*64, c.ROOT, "a"*40, ID)
            value = read(Path(str(resumed)+".qualification-result.json"))
            self.assertEqual(value["native_calls"], 0)
            self.assertEqual(value["previously_durable"], route.ORDINALS)
            self.assertFalse((resumed/"model_load_attempt.json").exists())
