"""PR #115's loader unchanged; retain handles and audit PyTorch's later mappings."""
import ctypes
import os
from pathlib import Path
import sys

from ..internvl3_driver.loader import preload
from ..internvl3_cuda.probes import cudart_path, path_metadata
from ..one_click.artifacts import write

# Do not let execute() returning release strong references before process exit.
_SESSIONS = []


class DriverSession:
    def __init__(self, evidence):
        self.evidence = Path(evidence)
        self.handles, self.records = preload(
            on_verified=lambda rows: write(self.evidence / "driver-verified.json", rows))
        _SESSIONS.append(self)
        write(self.evidence / "driver-loaded.json", self.records)

    def observe(self, stage):
        """No dlclose or driver reloading; RTLD_NOLOAD proves SONAME reuse."""
        try:
            mappings = {}
            for line in Path("/proc/self/maps").read_text().splitlines():
                parts = line.split(maxsplit=5)
                if len(parts) == 6 and parts[5].startswith("/"):
                    mappings[parts[5]] = parts
            for index, row in enumerate(self.records):
                parts = mappings.get(row["target"])
                if parts is None:
                    raise PermissionError("PRELOADED_DRIVER_MAPPING_LOST")
                major, minor = (int(v, 16) for v in parts[3].split(":"))
                if os.makedev(major, minor) != row["device"] or int(parts[4]) != row["inode"]:
                    raise PermissionError("PRELOADED_DRIVER_MAPPING_CHANGED")
                reused = ctypes.CDLL(row["soname"], mode=os.RTLD_NOLOAD | os.RTLD_NOW | os.RTLD_LOCAL)
                if reused._handle != self.handles[2 * index]._handle:
                    raise PermissionError("PYTORCH_DRIVER_SONAME_REUSE_FAILED")
                self.handles.append(reused)
            runtime = cudart_path().resolve(strict=True)
            relevant = sorted(p for p in mappings if any(s in Path(p).name for s in
                ("libcuda", "libnvidia", "libcublas", "libcufft", "libcurand", "libcusolver",
                 "libcusparse", "libcudnn", "libnvrtc", "libnvJitLink", "libtorch", "libc10", "libnccl")))
            expected_drivers = {r["target"] for r in self.records}
            for path in relevant:
                name = Path(path).name
                if name.startswith(("libcuda.so", "libnvidia-ml.so")) and path not in expected_drivers:
                    raise PermissionError("UNEXPECTED_ADDITIONAL_DRIVER_MAPPING")
                if name.startswith("libcudart.so") and Path(path).resolve(strict=True) != runtime:
                    raise PermissionError("UNPINNED_CUDA_RUNTIME_MAPPING")
            write(self.evidence / ("libraries-" + stage + ".json"), {
                "status": "OBSERVED", "driver_soname_reuse": True,
                "libraries": [path_metadata(p, Path(sys.executable).resolve().parents[2]) for p in relevant],
                "scope": "PROC_MAPS_SNAPSHOTS_NOT_TRANSIENT_DLOPEN_TRACE",
                "additional_libraries": "WHEEL_DEPENDENCIES_OBSERVED_UNDER_UNCHANGED_GUARDS"})
        except BaseException as error:
            write(self.evidence / ("libraries-" + stage + "-failure.json"), {"type": type(error).__name__})
            raise
