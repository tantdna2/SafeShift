"""Proposed local IPC boundary. Install only after the recovery grant is checked.

BPF cannot inspect sockaddr pointers or infer an fd's family. The proof instead
starts single-threaded without ANY sockets, permits only AF_UNIX socket/socketpair,
and blocks descriptor import and alternate network syscalls in all descendants.
Local peers can relay traffic: this is explicitly a Lead-approved scope change,
not a claim of venue-wide isolation or a sandbox for malicious native code.
"""

from contextlib import contextmanager, ExitStack
import ctypes
import errno
import os
from pathlib import Path
import platform
import socket
import stat
from unittest.mock import patch

from safeshift.runners.internvl3_snapshot import block_network
from .contract import BOUNDARY


def assert_clean_start():
    if len(list(Path("/proc/self/task").iterdir())) != 1:
        raise RuntimeError("SECCOMP_SINGLE_THREAD_START_REQUIRED")
    for item in Path("/proc/self/fd").iterdir():
        try:
            mode = os.fstat(int(item.name)).st_mode
        except OSError as error:
            if error.errno == errno.EBADF:  # closed directory enumeration fd
                continue
            raise
        if stat.S_ISSOCK(mode):
            raise RuntimeError("SECCOMP_INHERITED_SOCKET_FORBIDDEN")


def deny_inet():
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("LINUX_X86_64_SECCOMP_REQUIRED")
    assert_clean_start()

    class Filter(ctypes.Structure):
        _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte),
                    ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint)]

    class Program(ctypes.Structure):
        _fields_ = [("len", ctypes.c_ushort), ("filter", ctypes.POINTER(Filter))]

    deny = 0x00050000 | errno.EPERM
    rows = [(0x20, 0, 0, 4), (0x15, 1, 0, 0xc000003e), (0x06, 0, 0, 0x80000000),
            (0x20, 0, 0, 0), (0x35, 0, 1, 0x40000000), (0x06, 0, 0, deny)]
    # Keep sendto/sendmsg/sendmmsg, io_uring, unshare/setns denied. Also prevent
    # SCM_RIGHTS receipt, pidfd_getfd and ptrace from importing an INET fd.
    for syscall in (44, 46, 307, 47, 299, 438, 101, 425, 426, 427, 272, 308):
        rows += [(0x15, 0, 1, syscall), (0x06, 0, 0, deny)]
    # Both socket and socketpair accept AF_UNIX only. Reload syscall number
    # after testing args[0], so the second branch cannot mistake it for a syscall.
    for syscall in (41, 53):
        rows += [(0x15, 0, 4, syscall), (0x20, 0, 0, 16),
                 (0x15, 1, 0, socket.AF_UNIX), (0x06, 0, 0, deny),
                 (0x06, 0, 0, 0x7fff0000), (0x20, 0, 0, 0)]
    rows += [(0x06, 0, 0, 0x7fff0000)]
    array = (Filter * len(rows))(*(Filter(*row) for row in rows))
    program = Program(len(array), array)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), "SECCOMP_NO_NEW_PRIVS_FAILED")
    # seccomp(SECCOMP_SET_MODE_FILTER, SECCOMP_FILTER_FLAG_TSYNC, &program).
    # TSYNC covers every thread; no fallback to an unsynchronized filter.
    result = libc.syscall(317, 1, 1, ctypes.byref(program))
    if result != 0:
        raise OSError(ctypes.get_errno(), "SECCOMP_TSYNC_INSTALL_FAILED:" + str(result))
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            probe = socket.socket(family, socket.SOCK_STREAM)
        except OSError as error:
            if error.errno == errno.EPERM:
                continue
            raise
        probe.close()
        raise RuntimeError("SECCOMP_NETWORK_SELF_TEST_FAILED")
    # Actual local connect, not merely creation. No external peer or network.
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind("\0safeshift-recovery-" + str(os.getpid()))
        server.listen(1)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(server.getsockname())
            accepted, _ = server.accept()
            accepted.close()
    return {"boundary": BOUNDARY, "no_inherited_sockets": True, "single_thread_start": True,
            "inet_and_inet6_socket_denied": True, "unix_connect_self_test": "PASS",
            "native_descendants_inherit": True, "tsync": True,
            "fd_receipt_denied": True, "venue_internet_toggle": "UNCHANGED",
            "local_peer_relay_risk": "REQUIRES_SEPARATE_LEAD_APPROVAL"}


@contextmanager
def network_denied():
    """Keep Python denial; the only added operation is AF_UNIX connect[_ex]."""
    connect, connect_ex = socket.socket.connect, socket.socket.connect_ex

    def unix_connect(sock, *args, **kwargs):
        if sock.family != socket.AF_UNIX:
            block_network()
        return connect(sock, *args, **kwargs)

    def unix_connect_ex(sock, *args, **kwargs):
        if sock.family != socket.AF_UNIX:
            block_network()
        return connect_ex(sock, *args, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", unix_connect))
        stack.enter_context(patch.object(socket.socket, "connect_ex", unix_connect_ex))
        for name in ("sendto", "sendmsg", "recvmsg", "recvmsg_into"):
            if hasattr(socket.socket, name):
                stack.enter_context(patch.object(socket.socket, name, block_network))
        for name in ("create_connection", "getaddrinfo"):
            stack.enter_context(patch.object(socket, name, block_network))
        yield
