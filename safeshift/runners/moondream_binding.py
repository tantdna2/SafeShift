"""Audited per-instance vision binding and narrowly scoped Starmie redirect."""

from contextlib import contextmanager
import hashlib
import importlib
import importlib.abc
import importlib.util
from pathlib import Path
import sys
import types

from . import moondream_precision as precision
from .moondream_snapshot import (
    MODEL_ID, REVISION, TOKENIZER_REPO, TOKENIZER_REVISION, artifact_rows,
    require_offline, verify_snapshot,
)


def code_signature(code):
    """Compare compiled code without executing it, independent of checkout path."""
    return (code.co_code, code.co_names, code.co_varnames, code.co_freevars,
            code.co_cellvars, code.co_argcount, code.co_kwonlyargcount,
            code.co_posonlyargcount, code.co_flags, code.co_exceptiontable,
            tuple(code_signature(c) if isinstance(c, types.CodeType) else c
                  for c in code.co_consts))


def verified_source(snapshot, filename):
    expected = next(r for r in artifact_rows(MODEL_ID, REVISION) if r["path"] == filename)
    content = (Path(snapshot) / filename).read_bytes()
    if (len(content) != expected["size_bytes"]
            or hashlib.sha256(content).hexdigest() != expected["sha256"]):
        raise ValueError("REMOTE_SOURCE_HASH_MISMATCH")
    return content


def verify_function(function, module, snapshot, filename, qualname):
    if (type(function) is not types.FunctionType or function.__globals__ is not vars(module)
            or function.__qualname__ != qualname):
        raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED")
    compiled = compile(verified_source(snapshot, filename), filename, "exec", dont_inherit=True)
    def find(code):
        if code.co_qualname == qualname:
            return code
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                found = find(constant)
                if found is not None:
                    return found
        return None
    expected = find(compiled)
    if expected is None or code_signature(expected) != code_signature(function.__code__):
        raise ValueError("AUDITED_BYTECODE_REQUIRED")
    # Only the audited class cell is allowed; never accept arbitrary closures.
    closure = function.__closure__
    if expected.co_freevars == ():
        if closure is not None:
            raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED")
    elif expected.co_freevars == ("__class__",):
        owner = vars(module).get(qualname.rpartition(".")[0])
        if (function.__code__.co_freevars != ("__class__",)
                or type(closure) is not tuple or len(closure) != 1
                or not isinstance(owner, type)):
            raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED")
        try:
            cell_class = closure[0].cell_contents
        except ValueError:
            raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED") from None
        if cell_class is not owner:
            raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED")
    else:
        raise ValueError("AUDITED_FUNCTION_IDENTITY_REQUIRED")
    return function


class _VerifiedLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Read verified source directly: never accept a cached .pyc or moving alias."""

    package = "_safeshift_moondream_" + REVISION

    def __init__(self, snapshot):
        self.snapshot = Path(snapshot)
        self.names = {r["path"][:-3] for r in artifact_rows(MODEL_ID, REVISION)
                      if r["path"].endswith(".py")}

    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(self.package + "."):
            name = fullname[len(self.package) + 1:]
            if name not in self.names:
                raise ImportError("UNREVIEWED_REMOTE_MODULE")
            return importlib.util.spec_from_loader(fullname, self)
        return None

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        require_offline()
        filename = module.__name__.rsplit(".", 1)[1] + ".py"
        source = verified_source(self.snapshot, filename)
        module.__file__ = str(self.snapshot / filename)
        exec(compile(source, module.__file__, "exec", dont_inherit=True), vars(module))


def load_verified_modules(snapshot):
    """Future real execution only, after full snapshot verification/offline boundary."""
    require_offline()
    verify_snapshot(snapshot, MODEL_ID, REVISION)
    loader = _VerifiedLoader(snapshot)
    if any(k == loader.package or k.startswith(loader.package + ".") for k in sys.modules):
        raise RuntimeError("DEDICATED_FRESH_PROCESS_REQUIRED")
    package = types.ModuleType(loader.package)
    package.__path__ = []
    sys.modules[loader.package] = package
    sys.meta_path.insert(0, loader)
    try:
        hf = importlib.import_module(loader.package + ".hf_moondream")
        modules = {n: sys.modules[loader.package + "." + n] for n in loader.names}
        return hf, modules
    finally:
        sys.meta_path.remove(loader)


@contextmanager
def starmie_redirect(module, snapshot, tokenizer_snapshot, native_tokenizer):
    """Caller owns the process lock. Change only this remote module's binding."""
    require_offline()
    manifest = verify_snapshot(tokenizer_snapshot, TOKENIZER_REPO, TOKENIZER_REVISION)
    constructor = verify_function(module.MoondreamModel.__init__, module, snapshot,
                                  "moondream.py", "MoondreamModel.__init__")
    original = module.Tokenizer
    if original is not native_tokenizer:
        raise ValueError("ORIGINAL_TOKENIZER_IDENTITY_REQUIRED")
    evidence = {"manifest": manifest, "calls": 0, "tokenizer": None}

    class PinnedStarmie:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            caller = sys._getframe(1)
            if (args != (TOKENIZER_REPO,) or kwargs or evidence["calls"] != 0
                    or caller.f_code is not constructor.__code__
                    or caller.f_globals is not vars(module)):
                raise ValueError("UNEXPECTED_TOKENIZER_REQUEST")
            require_offline()
            verify_snapshot(tokenizer_snapshot, TOKENIZER_REPO, TOKENIZER_REVISION)
            evidence["calls"] += 1
            tokenizer = native_tokenizer.from_file(str(Path(tokenizer_snapshot) / "tokenizer.json"))
            evidence["tokenizer"] = tokenizer
            return tokenizer

    module.Tokenizer = PinnedStarmie
    try:
        yield evidence
        if evidence["calls"] != 1 or evidence["tokenizer"] is None:
            raise ValueError("STARMIE_LOAD_NOT_OBSERVED")
    finally:
        intact = module.Tokenizer is PinnedStarmie
        module.Tokenizer = original
        if not intact or module.Tokenizer is not original:
            raise RuntimeError("TOKENIZER_RESTORATION_INVARIANT_FAILED")


def require_pillow(modules, pillow_image):
    crops = modules["image_crops"]
    if (crops.HAS_VIPS is not False or vars(crops).get("Image") is not pillow_image
            or "pyvips" in vars(crops)):
        raise ValueError("PILLOW_ONLY_REQUIRED")
    if modules["vision"].prepare_crops.__globals__.get("overlap_crop_image") is not crops.overlap_crop_image:
        raise ValueError("CROP_BACKEND_IDENTITY_MISMATCH")


def tensor_boundary(tensor, torch, device):
    if (type(tensor) is not torch.Tensor or tensor.dtype != torch.float16
            or str(tensor.device) != device):
        raise ValueError("FP16_IMAGE_BOUNDARY_REQUIRED")
    return {"dtype": str(tensor.dtype), "device": str(tensor.device), "shape": list(tensor.shape)}


class VisionBinding:
    def __init__(self, inner, modules, snapshot, torch, pillow_image):
        self.inner, self.modules, self.snapshot = inner, modules, snapshot
        self.torch, self.pillow_image = torch, pillow_image
        self.valid = True
        self.events = []
        moon, vision = modules["moondream"], modules["vision"]
        self.original = verify_function(type(inner)._run_vision_encoder, moon, snapshot,
                                        "moondream.py", "MoondreamModel._run_vision_encoder")
        self.prepare = verify_function(vision.prepare_crops, vision, snapshot,
                                      "vision.py", "prepare_crops")
        self.consume = verify_function(type(inner)._vis_enc, moon, snapshot,
                                      "moondream.py", "MoondreamModel._vis_enc")
        verify_function(vision.vision_encoder, vision, snapshot, "vision.py", "vision_encoder")
        self.encoder = vision.vision_encoder
        self.codes = tuple(f.__code__ for f in (self.original, self.prepare, self.consume, self.encoder))
        self.check()

    def check(self):
        inner = self.inner
        if (not self.valid or type(inner) is not self.modules["moondream"].MoondreamModel
                or type(inner)._run_vision_encoder is not self.original
                or inner._run_vision_encoder.__func__ is not self.original
                or inner._vis_enc.__func__ is not self.consume
                or self.modules["vision"].prepare_crops is not self.prepare
                or self.modules["vision"].vision_encoder is not self.encoder
                or any(f.__code__ is not code for f, code in zip(
                    (self.original, self.prepare, self.consume, self.encoder), self.codes))
                or self.original.__globals__.get("prepare_crops") is not self.prepare
                or self.consume.__globals__.get("vision_encoder") is not self.modules["vision"].vision_encoder
                or str(inner.device) != "cuda:0"):
            raise ValueError("INSTANCE_BINDING_IDENTITY_MISMATCH")
        require_pillow(self.modules, self.pillow_image)

    @contextmanager
    def installed(self):
        """Under runner's non-reentrant process guard; restore even on exceptions."""
        self.check()
        inner, torch = self.inner, self.torch
        missing = object()
        prior = {name: vars(inner).get(name, missing) for name in ("_run_vision_encoder", "_vis_enc")}
        transferred = None
        prepares = consumes = 0

        def prepare(image, config, *, device):
            nonlocal transferred, prepares
            if config is not inner.config.vision or str(device) != "cuda:0" or prepares:
                raise ValueError("UNEXPECTED_PREPARE_CROPS_CALL")
            require_pillow(self.modules, self.pillow_image)
            prepares += 1
            upstream = self.prepare(image, config, device="cpu")
            # Entire tuple, strictly after the unmodified BF16 normalization.
            bridged = precision.post_normalization_fp16_bridge(upstream)
            self.events.append({"boundary": "bridge_cpu", **tensor_boundary(bridged[0], torch, "cpu")})
            transferred = bridged[0].to(device="cuda:0")
            self.events.append({"boundary": "transfer", **tensor_boundary(transferred, torch, "cuda:0")})
            return transferred, bridged[1]

        def consume(instance, crops):
            nonlocal consumes
            if instance is not inner or crops is not transferred or consumes:
                raise ValueError("UNEXPECTED_VISION_CONSUMPTION")
            self.events.append({"boundary": "vision_consumption", **tensor_boundary(crops, torch, "cuda:0")})
            consumes += 1
            return self.consume(instance, crops)

        overlay = self.original.__globals__.copy()
        overlay["prepare_crops"] = prepare
        function = types.FunctionType(self.original.__code__, overlay, self.original.__name__,
                                      self.original.__defaults__, self.original.__closure__)
        function.__kwdefaults__ = self.original.__kwdefaults__
        binding = types.MethodType(function, inner)
        consumer = types.MethodType(consume, inner)
        failed = False
        try:
            inner._run_vision_encoder, inner._vis_enc = binding, consumer
            yield
            if prepares != 1 or consumes != 1:
                raise ValueError("IMAGE_PATH_NOT_OBSERVED_EXACTLY_ONCE")
        except BaseException:
            failed = True
            raise
        finally:
            intact = inner._run_vision_encoder is binding and inner._vis_enc is consumer
            try:
                for name, value in prior.items():
                    if value is missing:
                        if name in vars(inner):
                            delattr(inner, name)
                    else:
                        setattr(inner, name, value)
                if not intact or any(vars(inner).get(k, missing) is not v for k, v in prior.items()):
                    raise RuntimeError("INSTANCE_RESTORATION_FAILED")
                self.check()
                if failed:
                    self.valid = False
            except BaseException:
                self.valid = False
                raise
