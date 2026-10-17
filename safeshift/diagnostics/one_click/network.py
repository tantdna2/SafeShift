"""Irreversible Linux x86_64 seccomp filter; inherited by native child threads."""

import ctypes
import errno
import platform
import socket


def deny_inet():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("LINUX_X86_64_SECCOMP_REQUIRED")
    # Deny socket(AF_INET/AF_INET6/AF_PACKET), connect/sendto/sendmsg/sendmmsg,
    # io_uring and namespace changes. AF_UNIX socket creation remains for CUDA.
    # Child starts without inherited network descriptors (subprocess close_fds).
    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]

    instructions = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
                    (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000),
                    (0x06, 0, 0, 0x00050000 | errno.EPERM)]
    for syscall in (42, 44, 46, 307, 425, 426, 427, 272, 308):
        instructions += [(0x15, 0, 1, syscall), (0x06, 0, 0, 0x00050000 | errno.EPERM)]
    # Only socket(AF_UNIX) is permitted; the sole socket branch reads args[0].
    instructions += [(0x15, 0, 4, 41), (0x20, 0, 0, 16), (0x15, 1, 0, socket.AF_UNIX),
                     (0x06, 0, 0, 0x00050000 | errno.EPERM), (0x06, 0, 0, 0x7fff0000),
                     (0x06, 0, 0, 0x7fff0000)]
    array = (Filter * len(instructions))(*(Filter(*row) for row in instructions))
    program = Program(len(array), array)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(22, 2, ctypes.byref(program), 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "SECCOMP_INSTALL_FAILED")
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            probe = socket.socket(family, socket.SOCK_STREAM)
        except OSError as error:
            if error.errno == errno.EPERM:
                continue
            raise
        probe.close()
        raise RuntimeError("SECCOMP_NETWORK_SELF_TEST_FAILED")
    return {"boundary": "SECCOMP", "inet_and_inet6_socket_denied": True,
            "native_descendants_inherit": True, "venue_internet_toggle": "UNCHANGED"}
