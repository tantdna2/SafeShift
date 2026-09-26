"""Synthetic bytecode/closures only; no upstream source or model execution."""

import hashlib
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

from safeshift.runners import moondream_binding as binding


SOURCE = b'''class MoondreamModel:
    def __init__(self):
        super().__init__()
        self.owner = __class__
    def _run_vision_encoder(self, image):
        return image
    def _vis_enc(self, crops):
        return crops
def prepare_crops(image):
    return image
def vision_encoder(crops):
    return crops
def ordinary(value):
    return value + 1
'''


class FunctionClosureTests(unittest.TestCase):
    def setUp(self):
        self.module = types.ModuleType("synthetic_audited_module")
        exec(compile(SOURCE, "synthetic.py", "exec", dont_inherit=True), vars(self.module))
        self.function = self.module.MoondreamModel.__init__

    def verify(self, function, source=SOURCE):
        with patch.object(binding, "verified_source", return_value=source):
            return binding.verify_function(function, self.module, "unused",
                                           "synthetic.py", function.__qualname__)

    def clone(self, closure):
        return types.FunctionType(self.function.__code__, vars(self.module), closure=closure)

    def test_audited_class_cell_accepted_without_constructing_class(self):
        self.assertEqual(self.function.__code__.co_freevars, ("__class__",))
        self.assertIs(self.function.__closure__[0].cell_contents, self.module.MoondreamModel)
        self.assertIs(self.verify(self.function), self.function)

    def test_same_bytecode_wrong_class_or_nonclass_cell_rejected(self):
        # Same name and a subclass must still fail exact identity.
        for wrong in (type("MoondreamModel", (), {}),
                      type("Child", (self.module.MoondreamModel,), {}), None, object()):
            with self.subTest(wrong=wrong):
                function = self.clone((types.CellType(wrong),))
                self.assertIs(function.__code__, self.function.__code__)
                with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                    self.verify(function)

    def test_empty_and_deleted_cell_rejected(self):
        dead = types.CellType(self.module.MoondreamModel)
        del dead.cell_contents
        for cell in (types.CellType(), dead):
            with self.subTest(cell=cell), self.assertRaisesRegex(
                    ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                self.verify(self.clone((cell,)))

    def test_missing_or_nonclass_module_owner_rejected_even_if_cell_matches(self):
        del self.module.MoondreamModel
        with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
            self.verify(self.function)
        for owner in (None, object()):
            self.module.MoondreamModel = owner
            with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                self.verify(self.clone((types.CellType(owner),)))

    def test_unexpected_audited_freevars_rejected_despite_matching_bytecode(self):
        for expression in ("secret", "(__class__, secret)"):
            source = ("def factory():\n"
                      " secret = 1\n"
                      " class Other:\n"
                      "  def __init__(self):\n"
                      f"   return {expression}\n"
                      " return Other\n").encode()
            exec(compile(source, "synthetic.py", "exec", dont_inherit=True), vars(self.module))
            function = self.module.factory().__init__
            with self.subTest(expression=expression), self.assertRaisesRegex(
                    ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                self.verify(function, source)

    def test_ordinary_and_vision_functions_require_none_not_empty_tuple(self):
        for function in (self.module.ordinary, self.module.MoondreamModel._run_vision_encoder,
                         self.module.MoondreamModel._vis_enc, self.module.prepare_crops,
                         self.module.vision_encoder):
            with self.subTest(qualname=function.__qualname__):
                self.assertEqual(function.__code__.co_freevars, ())
                self.assertIsNone(function.__closure__)
                self.assertIs(self.verify(function), function)
                empty = types.FunctionType(function.__code__, vars(self.module), closure=())
                self.assertEqual(empty.__closure__, ())
                with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                    self.verify(empty)

    def test_bytecode_and_freevar_mismatch_still_rejected(self):
        for code in (self.function.__code__.replace(co_names=("changed",)),
                     self.function.__code__.replace(co_freevars=("other",))):
            function = types.FunctionType(code, vars(self.module), closure=self.function.__closure__)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, "AUDITED_BYTECODE_REQUIRED"):
                self.verify(function)

    def test_missing_expected_code_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "AUDITED_BYTECODE_REQUIRED"):
            self.verify(self.function, b"unrelated = 1\n")

    def test_globals_qualname_and_type_mismatch_still_rejected(self):
        globals_mismatch = types.FunctionType(self.function.__code__, dict(vars(self.module)),
                                             closure=self.function.__closure__)
        qualname_mismatch = self.clone(self.function.__closure__)
        qualname_mismatch.__qualname__ = "wrong"
        impersonator = types.SimpleNamespace(__globals__=vars(self.module),
                                            __qualname__=self.function.__qualname__,
                                            __closure__=self.function.__closure__,
                                            __code__=self.function.__code__)
        for function in (globals_mismatch, qualname_mismatch, impersonator,
                         types.MethodType(self.function, object())):
            with self.subTest(function=function), patch.object(binding, "verified_source") as source:
                with self.assertRaisesRegex(ValueError, "AUDITED_FUNCTION_IDENTITY_REQUIRED"):
                    binding.verify_function(function, self.module, "unused", "synthetic.py",
                                            "MoondreamModel.__init__")
                source.assert_not_called()

    def test_source_hash_and_size_still_verified_before_closure_acceptance(self):
        row = {"path": "synthetic.py", "size_bytes": len(SOURCE),
               "sha256": hashlib.sha256(SOURCE).hexdigest()}
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(binding, "artifact_rows", return_value=[row]):
            path = Path(folder) / "synthetic.py"
            path.write_bytes(SOURCE)
            self.assertIs(binding.verify_function(self.function, self.module, folder,
                          "synthetic.py", "MoondreamModel.__init__"), self.function)
            for content in (SOURCE.replace(b"super", b"sUper"), SOURCE + b"\n"):
                path.write_bytes(content)
                with self.assertRaisesRegex(ValueError, "REMOTE_SOURCE_HASH_MISMATCH"):
                    binding.verify_function(self.function, self.module, folder,
                                            "synthetic.py", "MoondreamModel.__init__")


if __name__ == "__main__":
    unittest.main()
