"""Linux process-group supervision shared by setup, diagnostics and native work.

This primitive grants no data/model authority. Public fulltrain routes remain
fenced. Every launched command has an absolute deadline and a bounded log.
"""
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from safeshift.candidates.source import require
from safeshift.pilot.artifacts import export, write


@contextmanager
def parent_deadline(deadline, stage):
    """Bound main-thread notebook I/O that starts no process group."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("SUPERVISED_PARENT_DEADLINE_" + stage.upper())
    require(sys.platform == "linux" and signal.getitimer(signal.ITIMER_REAL) == (0, 0),
            "SUPERVISOR_PARENT_TIMER_REQUIRED")

    def expired(*_):
        raise TimeoutError("SUPERVISED_PARENT_DEADLINE_" + stage.upper())

    old = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, remaining)
        yield
        if time.monotonic() >= deadline:
            expired()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def seal_supervisor(output, deadline):
    """Publish the ZIP only after export has produced its verified sidecar."""
    from safeshift.pilot.runner import error_record

    archive = output.with_suffix(".zip")
    partial = archive.with_suffix(".zip.partial")
    sidecar = Path(str(archive) + ".sha256.json")
    verified = False
    try:
        with parent_deadline(deadline - 5, "export"):
            require(not archive.exists() and not sidecar.exists(), "SUPERVISOR_EXPORT_ALREADY_PRESENT")
            export(output, partial)
            verified = True
            Path(str(partial) + ".sha256.json").rename(sidecar)
            partial.rename(archive)
    except Exception as error:
        if verified and archive.is_file() and sidecar.is_file() and not partial.exists():
            return  # The alarm arrived after both verified files were published.
        # The loose control tree and any partial archive are evidence. Leave
        # them and any separately sealed native attempt exactly where they are.
        print("MINICPM_BLOCKED_SUPERVISOR_EXPORT_KEEP_RESERVATION", flush=True)
        try:
            with parent_deadline(deadline, "export_failure_receipt"):
                write(output.with_name(output.name + "-export-failure.json"),
                    {"status": "BLOCKED", "failure": error_record(error, "export"),
                     "automatic_retry": False, "reservation": "KEEP", "partial_evidence": "PRESERVED"})
        except Exception:
            print("MINICPM_BLOCKED_SUPERVISOR_EXPORT_RECEIPT_UNAVAILABLE", flush=True)
        raise

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


def group_members(pgid, proc=Path('/proc')):
    """Bounded Linux observation after SIGKILL. Zombies cannot execute work."""
    found = []
    for i, path in enumerate(proc.iterdir()):
        require(i < 16384, 'PROCESS_GROUP_SCAN_BOUND')
        if not path.name.isdecimal():
            continue
        try:
            value = (path / 'stat').read_text()
            fields = value[value.rfind(')') + 2:].split()
            if int(fields[2]) == pgid:
                found.append({'pid': int(path.name), 'state': fields[0]})
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def process_group_closed(receipt):
    """Only affirmative, persisted reaping evidence can seal a worker ledger."""
    if not isinstance(receipt, dict) or receipt.get("schema") != "fresh-process-supervision-v1":
        return False
    observation = receipt.get("group_exit")
    status = receipt.get("status")
    if (status not in ("EXITED", "CHILD_FAILURE", "HARD_DEADLINE", "LOG_BUDGET_EXCEEDED",
                       "SUPERVISOR_EXCEPTION")
            or receipt.get("group_kill_sent") is not True or type(receipt.get("returncode")) is not int
            or (status == "EXITED" and receipt["returncode"] != 0)
            or not isinstance(observation, dict) or observation.get("status") != "NO_LIVE_MEMBERS"):
        return False
    members = observation.get("members")
    return isinstance(members, list) and all(isinstance(row, dict) and row.get("state") == "Z"
                                              for row in members)


def wait_group_exit(pgid, *, seconds=2):
    deadline = time.monotonic() + seconds
    while True:
        rows = group_members(pgid)
        live = [row for row in rows if row['state'] != 'Z']
        if not live or time.monotonic() >= deadline:
            return {'status': 'NO_LIVE_MEMBERS' if not live else 'LIVE_SURVIVORS', 'members': rows}
        time.sleep(.02)


def run(command, *, cwd, env, deadline, log, receipt, max_log_bytes, watch_log_root=None, pass_fds=(),
        live_prefix=None, readiness=None):
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
    require(live_prefix is None or live_prefix == "SAFESHIFT_MINICPM_LIVE_V3 ", "SUPERVISOR_LIVE_PREFIX")
    begun, child, reason, code = time.monotonic(), None, None, None
    ready = False
    readiness_expired = False
    if readiness is not None:
        ready_fd, ready_by = readiness
        require(type(ready_fd) is int and math.isfinite(ready_by)
                and begun < ready_by <= deadline and not os.get_blocking(ready_fd),
                "SUPERVISOR_NONBLOCKING_READINESS_REQUIRED")
    position, pending = 0, b""
    try:
        with log.open("xb") as stream:
            child = subprocess.Popen([sys.executable, "-I", "-B", "-c", GUARD, str(os.getpid()),
                ','.join(map(str, pass_fds)), *command],
                cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                close_fds=True, start_new_session=True, pass_fds=pass_fds)
            while True:
                code = child.poll()
                if code is not None and code != 0 and live_prefix is None:
                    reason = "CHILD_FAILURE"
                    break
                if time.monotonic() >= deadline:
                    reason = "HARD_DEADLINE"
                    break
                if readiness is not None and not ready:
                    if time.monotonic() >= ready_by:
                        readiness_expired = True
                        reason = "HARD_DEADLINE"
                        break
                    try:
                        ready = os.read(ready_fd, 1) == b"1"
                    except BlockingIOError:
                        pass
                log_bytes = os.fstat(stream.fileno()).st_size
                if live_prefix is not None:
                    # Only small structured public receipts reach provider logs.
                    # The complete child log stays untouched on disk.
                    with log.open("rb") as live:
                        live.seek(position)
                        chunk = live.read(min(65536, max_log_bytes + 1))
                        position += len(chunk)
                    for line in (pending + chunk).splitlines(keepends=True):
                        if line.endswith(b"\n"):
                            if line.startswith(live_prefix.encode()):
                                require(len(line) <= 65536, "SUPERVISOR_LIVE_EVENT_BOUND")
                                print(line.decode("utf-8").rstrip("\r\n"), flush=True)
                            pending = b""
                        else:
                            # Ignore long unstructured lines without buffering
                            # unbounded private model/package diagnostics.
                            pending = line if len(line) <= 65536 else b""
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
                if code is not None and (live_prefix is None or position >= os.fstat(stream.fileno()).st_size):
                    reason = "EXITED" if code == 0 and (readiness is None or ready) else "CHILD_FAILURE"
                    break
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
    except BaseException:
        reason = "SUPERVISOR_EXCEPTION"
        raise
    finally:
        group_exit = {'status': 'NOT_LAUNCHED', 'members': []}
        try:
            if child is not None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                # Kill even on success; observe surviving descendants too.
                code = child.wait(timeout=5)
                group_exit = wait_group_exit(child.pid)
                if group_exit['status'] != 'NO_LIVE_MEMBERS':
                    reason = 'PROCESS_GROUP_SURVIVORS'
        except BaseException as cleanup_error:
            reason = 'PROCESS_GROUP_CLEANUP_UNVERIFIED'
            group_exit = {'status': 'UNVERIFIED', 'error': type(cleanup_error).__name__}
        write(receipt, {"schema": "fresh-process-supervision-v1", "status": reason,
            "returncode": code, "seconds": time.monotonic() - begun,
            "log_bytes": log.stat().st_size if log.exists() else 0,
            "group_kill_sent": child is not None, "group_exit": group_exit, "automatic_retry": False,
            "retention": "ALL_PARTIAL_FILES_RETAINED", "model_fit": "NOT_ESTABLISHED",
            **({"readiness_received": ready, "readiness_deadline_expired": readiness_expired}
               if readiness is not None else {})})
    if reason != "EXITED":
        raise RuntimeError("SUPERVISED_" + str(reason))
    return {"status": reason, "returncode": code}
