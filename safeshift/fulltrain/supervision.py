"""Linux process-group supervision shared by setup, diagnostics and native work.

This primitive grants no data/model authority. Public fulltrain routes remain
fenced. Every launched command has an absolute deadline and a bounded log.
"""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import write

# Keep a stdlib guardian alive above the target process. Linux parent-death
# signal kills the whole process group if the notebook/supervisor disappears.
# SIGKILL to the guardian itself remains an OS/container-level limitation.
GUARD = r'''
import ctypes, os, signal, subprocess, sys
def stop(*unused):
    os.killpg(os.getpgrp(), signal.SIGKILL)
signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
parent = int(sys.argv[1])
libc = ctypes.CDLL(None, use_errno=True)
if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
    raise OSError(ctypes.get_errno(), 'PDEATHSIG_REQUIRED')
if os.getppid() != parent:
    stop()
fds = tuple(int(v) for v in sys.argv[2].split(',') if v)
child = subprocess.Popen(sys.argv[3:], close_fds=True, pass_fds=fds)
raise SystemExit(child.wait())
'''


def run(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_root=None, pass_fds=()):
    """Reap one tree, never retry; timeout includes hanging load/native calls.

    Descendants must not deliberately escape their process group. The reviewed
    workers do not daemonize. This is resource control, not a hostile-code jail.
    Logs may exceed the cap by at most one polling interval's writes; use an
    external filesystem quota as well. No truncation or old output deletion.
    """
    require(sys.platform == "linux", "SUPERVISOR_REQUIRES_LINUX_PROCESS_GROUPS")
    require(type(command) is list and command and all(isinstance(x, str) and x for x in command),
            "ARGV_LIST_REQUIRED")
    require(type(deadline) in (float, int) and math.isfinite(deadline) and deadline > time.monotonic(),
            "ABSOLUTE_DEADLINE_EXPIRED")
    require(type(max_log_bytes) is int and max_log_bytes > 0, "EXPLICIT_LOG_BUDGET")
    log, receipt = Path(log), Path(receipt)
    require(not receipt.exists(), "SUPERVISOR_RECEIPT_EXISTS")
    begun, child, reason, code = time.monotonic(), None, None, None
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-c", GUARD, str(os.getpid()),
                ','.join(map(str, pass_fds)), *command],
                cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True, pass_fds=pass_fds)
            while True:
                code = child.poll()
                if time.monotonic() >= deadline:
                    reason = "HARD_DEADLINE"
                    break
                log_bytes = os.fstat(stream.fileno()).st_size
                if watch_log_root is not None and Path(watch_log_root).is_dir():
                    # Known direct stage logs only; never an unbounded recursive scan.
                    for i, entry in enumerate(Path(watch_log_root).iterdir()):
                        require(i < 128, "STAGE_DIRECT_ENTRY_BOUND")
                        if entry.suffix == ".log":
                            require(not entry.is_symlink() and entry.is_file(), "STAGE_LOG_ALIAS")
                            log_bytes += entry.stat().st_size
                if log_bytes > max_log_bytes:
                    reason = "LOG_BUDGET_EXCEEDED"
                    break
                if code is not None:
                    reason = "EXITED" if code == 0 else "CHILD_FAILURE"
                    break
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
    except BaseException:
        reason = "SUPERVISOR_EXCEPTION"
        raise
    finally:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Kill even on success: no orphan descendant may outlive a stage.
            code = child.wait(timeout=5)
        write(receipt, {"schema": "fresh-process-supervision-v1", "status": reason,
            "returncode": code, "seconds": time.monotonic() - begun,
            "log_bytes": log.stat().st_size if log.exists() else 0,
            "group_kill_sent": child is not None, "automatic_retry": False,
            "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED"})
    if reason != "EXITED":
        raise RuntimeError("SUPERVISED_" + str(reason))
    return {"status": reason, "returncode": code}
