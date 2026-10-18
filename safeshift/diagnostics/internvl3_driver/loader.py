"""Load only the two evidenced driver objects, after the caller installs guards.

No search path, environment input, host CUDA Runtime, or fallback is accepted.
Trust is in the root-managed Kaggle image, not an NVIDIA signature attestation.
"""
from contextlib import ExitStack
import ctypes
import hashlib
import os
from pathlib import Path
import stat
import struct

DIRECTORY = Path("/usr/local/nvidia/lib64")  # Evidenced platform ABI location.
OBJECTS = {
    "libcuda.so.1": ("libcuda.so.580.178.04", 96284520),
    "libnvidia-ml.so.1": ("libnvidia-ml.so.580.178.04", 2291896),
}
SYMBOLS = {"libcuda.so.1": ("cuInit", "cuDeviceGetCount"),
           "libnvidia-ml.so.1": ("nvmlInit", "nvmlDeviceGetCount_v2")}
DEPENDENCIES = {"libm.so.6", "libc.so.6", "libdl.so.2", "libpthread.so.0", "librt.so.1"}


def trusted(info, *, directory=False):
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o6022:
        raise PermissionError("DRIVER_OWNER_MODE_OR_TYPE_UNTRUSTED")


def trusted_directory(path):
    # Reject aliases on every ancestor, including the root. No /tmp exception.
    for parent in (*reversed(path.parents), path):
        trusted(parent.lstat(), directory=True)
    if path.resolve(strict=True) != path:
        raise PermissionError("DRIVER_DIRECTORY_ALIAS_FORBIDDEN")


def elf_identity(data, soname):
    """Bounded ELF64 LE x86-64 ET_DYN check; parse, never execute readelf/ldd."""
    def span(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise PermissionError("DRIVER_ELF_BOUNDS_INVALID")
        return data[offset:offset + size]

    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        raise PermissionError("DRIVER_ELF64_REQUIRED")
    if struct.unpack_from("<HHI", data, 16) != (3, 62, 1):
        raise PermissionError("DRIVER_ELF_ARCH_OR_TYPE_INVALID")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    ehsize, phsize, count = struct.unpack_from("<HHH", data, 52)
    if ehsize != 64 or phsize != 56 or not 1 <= count <= 128:
        raise PermissionError("DRIVER_ELF_HEADER_INVALID")
    headers = [struct.unpack("<IIQQQQQQ", span(phoff + i * 56, 56)) for i in range(count)]
    dynamic = [h for h in headers if h[0] == 2]
    if len(dynamic) != 1 or dynamic[0][5] % 16 or dynamic[0][5] > 65536:
        raise PermissionError("DRIVER_ELF_DYNAMIC_INVALID")
    raw = span(dynamic[0][2], dynamic[0][5])
    tags = []
    for offset in range(0, len(raw), 16):
        tag, value = struct.unpack_from("<qQ", raw, offset)
        if tag == 0:
            break
        tags.append((tag, value))
    else:
        raise PermissionError("DRIVER_ELF_DYNAMIC_UNTERMINATED")
    # No embedded search paths, audit modules, or alternate/filter objects.
    if any(t in {15, 29, 0x6ffffefb, 0x6ffffefc, 0x7ffffffd, 0x7fffffff} for t, _ in tags):
        raise PermissionError("DRIVER_ELF_SEARCH_OR_INJECTION_TAG_FORBIDDEN")

    def singleton(tag):
        values = [v for t, v in tags if t == tag]
        if len(values) != 1:
            raise PermissionError("DRIVER_ELF_REQUIRED_TAG_INVALID")
        return values[0]

    address, size = singleton(5), singleton(10)
    if not 1 <= size <= 16 * 2**20:
        raise PermissionError("DRIVER_ELF_STRING_TABLE_INVALID")
    loads = [h for h in headers if h[0] == 1 and h[3] <= address and address + size <= h[3] + h[5]]
    if len(loads) != 1:
        raise PermissionError("DRIVER_ELF_STRING_MAPPING_INVALID")
    strings = span(loads[0][2] + address - loads[0][3], size)

    def string(offset):
        end = strings.find(b"\0", offset) if offset < len(strings) else -1
        if end < 0:
            raise PermissionError("DRIVER_ELF_STRING_INVALID")
        return strings[offset:end]

    if string(singleton(14)) != soname.encode():
        raise PermissionError("DRIVER_ELF_SONAME_MISMATCH")
    needed = [string(v) for t, v in tags if t == 1]
    if not needed or any(n not in {s.encode() for s in DEPENDENCIES} for n in needed):
        raise PermissionError("DRIVER_ELF_DEPENDENCY_NOT_ALLOWED")
    return [n.decode("ascii") for n in needed]


def verify_object(directory, soname):
    if directory != DIRECTORY or soname not in OBJECTS:
        raise PermissionError("DRIVER_LOCATION_NOT_ALLOWED")
    trusted_directory(directory)
    filename, size = OBJECTS[soname]
    alias, target = directory / soname, directory / filename
    link = alias.lstat()
    if not stat.S_ISLNK(link.st_mode) or link.st_uid != 0:
        raise PermissionError("DRIVER_SONAME_SYMLINK_UNTRUSTED")
    if os.readlink(alias) not in (filename, str(target)) or alias.resolve(strict=True) != target:
        raise PermissionError("DRIVER_SYMLINK_TARGET_NOT_ALLOWED")
    trusted(target.lstat())  # Reject target symlinks, devices and writable objects.
    descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    stream = os.fdopen(descriptor, "rb")
    try:
        info = os.fstat(stream.fileno())
        trusted(info)
        if info.st_size != size:
            raise PermissionError("DRIVER_EVIDENCED_SIZE_MISMATCH")
        data = stream.read(size + 1)
        if len(data) != size:
            raise PermissionError("DRIVER_FILE_CHANGED")
        needed = elf_identity(data, soname)
        after = os.fstat(stream.fileno())
        if (info.st_ino, info.st_dev, info.st_mtime_ns, info.st_ctime_ns, info.st_size) != (
                after.st_ino, after.st_dev, after.st_mtime_ns, after.st_ctime_ns, after.st_size):
            raise PermissionError("DRIVER_FILE_CHANGED")
        return stream, {"soname": soname, "target": str(target), "size_bytes": size,
                        "sha256": hashlib.sha256(data).hexdigest(), "needed": needed,
                        "device": info.st_dev, "inode": info.st_ino,
                        "trust": "ROOT_MANAGED_KAGGLE_IMAGE_NOT_VENDOR_SIGNATURE"}
    except BaseException:
        stream.close()
        raise


def preload(on_verified=None):
    """Caller must already hold seccomp + Python guard; keep handles for process life."""
    if "LD_LIBRARY_PATH" in os.environ or "LD_PRELOAD" in os.environ or "LD_AUDIT" in os.environ:
        raise PermissionError("DRIVER_SANITIZED_LOADER_ENVIRONMENT_REQUIRED")
    # Fail before native constructors if a driver/Runtime was already imported.
    maps = Path("/proc/self/maps").read_text()
    if any(name in maps for name in ("libcuda.so", "libnvidia-ml.so", "libcudart.so")):
        raise PermissionError("DRIVER_OR_RUNTIME_ALREADY_LOADED")
    handles, records = [], []
    with ExitStack() as stack:
        verified = []
        for soname in OBJECTS:
            stream, row = verify_object(DIRECTORY, soname)
            stack.enter_context(stream)
            verified.append((stream, row))
        if on_verified is not None:
            on_verified([row for _, row in verified])
        # Pin the verified inode through dlopen, avoiding a second pathname lookup.
        # DT_SONAME lets subsequent SONAME loads reuse this object, tested on CPU.
        for stream, row in verified:
            handle = ctypes.CDLL("/proc/self/fd/" + str(stream.fileno()), mode=os.RTLD_NOW | os.RTLD_LOCAL)
            if not all(hasattr(handle, symbol) for symbol in SYMBOLS[row["soname"]]):
                raise PermissionError("DRIVER_REQUIRED_SYMBOL_MISSING")
            # Confirm a later dlopen(SONAME) returns the very same object.
            reused = ctypes.CDLL(row["soname"], mode=os.RTLD_NOW | os.RTLD_LOCAL)
            if reused._handle != handle._handle:
                raise PermissionError("DRIVER_SONAME_RESOLVED_DIFFERENT_OBJECT")
            handles.extend((handle, reused))
            records.append({**row, "soname_reuse": True})
    return handles, records
