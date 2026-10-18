"""Unprivileged metadata observations, never a proof of absence of relay traffic.

No tracing, packet capture, payload reads, monitor threads or CUDA hooks. /proc
snapshots miss transient sockets; a namespace network table alone cannot identify
an owner. Only table rows joined to the observed peer's socket fd inodes count.
"""

from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import socket
import stat
import struct
import threading
import time

from ..one_click.artifacts import write

MAX_FDS = 4096
MAX_ROWS = 8192
MAX_EVENTS = 4096


class SecurityStop(BaseException):
    """Fatal guard decision, not swallowed by an ordinary library except Exception."""


class ConnectionFailure(OSError):
    """Sanitized connect failure; keep OSError semantics for callers."""


class ConnectionCallFailure(RuntimeError):
    """Sanitized non-OS connect failure."""


def failure(error):
    # Exception messages/filenames can contain destinations or secrets.
    return {"error_type": type(error).__name__, "errno": getattr(error, "errno", None)}


def destination(address):
    """Comparable SHA-256 of a destination, never a message/credential argument."""
    if isinstance(address, (str, bytes)):
        raw = os.fsencode(address)
        kind = "UNIX_ABSTRACT" if raw.startswith(b"\0") else "UNIX_PATH" if raw else "UNNAMED"
    elif isinstance(address, tuple) and all(isinstance(v, (str, int)) for v in address):
        raw = json.dumps(address, separators=(",", ":")).encode()
        kind = "INET_ADDRESS_TUPLE"
    else:
        return {"kind": "UNKNOWN", "status": "NOT_COLLECTED"}
    return {"kind": kind, "sha256": hashlib.sha256(kind.encode() + b"\0" + raw).hexdigest()}


def credentials(sock):
    if sock.family != socket.AF_UNIX or sock.type != socket.SOCK_STREAM:
        return {"status": "UNOBSERVABLE", "reason": "PEERCRED_SCOPE_NOT_SUPPORTED"}
    try:
        pid, uid, gid = struct.unpack("3i", sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
        if pid <= 0:
            return {"status": "UNOBSERVABLE", "reason": "PEER_PID_UNAVAILABLE"}
        return {"status": "OBSERVED", "source": "SO_PEERCRED", "pid": pid, "uid": uid, "gid": gid,
                "identity_scope": "CREDENTIALS_AT_CONNECT_LISTEN_OR_SOCKETPAIR_NOT_CURRENT_EXECUTABLE"}
    except (OSError, AttributeError) as error:
        return {"status": "UNOBSERVABLE", **failure(error)}


def start_ticks(directory):
    # comm is parenthesized and may contain spaces or ')'; never export comm.
    text = (directory / "stat").read_text()
    return int(text[text.rfind(")") + 2:].split()[19])


def peer_channels(peer, proc=Path("/proc")):
    result = {"status": "UNOBSERVABLE", "forwarded_payload": "UNOBSERVABLE", "channels": [],
              "limitations": ["SNAPSHOT_NOT_TRAFFIC", "TRANSIENT_OR_LATER_CONNECTIONS_MISSED",
                              "CREDENTIAL_PID_MAY_HAVE_EXITED_OR_BEEN_REUSED", "OTHER_PROCESS_HOPS_UNOBSERVABLE"],
              "errors": []}
    if peer.get("status") != "OBSERVED":
        return result
    directory = Path(proc) / str(peer["pid"])
    try:
        before = start_ticks(directory)
        fds = {}
        for index, fd in enumerate((directory / "fd").iterdir()):
            if index >= MAX_FDS:
                result["errors"].append({"reason": "FD_SCAN_TRUNCATED"})
                break
            try:
                link = os.readlink(fd)
                if link.startswith("socket:[") and link.endswith("]"):
                    fds.setdefault(link[8:-1], []).append(fd)
            except OSError as error:
                result["errors"].append(failure(error))
        readable = 0
        channels = []
        for protocol in ("tcp", "tcp6", "udp", "udp6"):
            try:
                with (directory / "net" / protocol).open() as stream:
                    next(stream, None)
                    for index, line in enumerate(stream):
                        if index >= MAX_ROWS:
                            result["errors"].append({"reason": "NET_TABLE_TRUNCATED", "table": protocol})
                            break
                        fields = line.split()
                        if len(fields) < 10:
                            continue
                        inode, remote, state = fields[9], fields[2], fields[3]
                        # TCP ESTABLISHED or UDP with a connected remote endpoint.
                        if inode not in fds or state != "01" or not int(remote.replace(":", ""), 16):
                            continue
                        # Recheck the peer fd association, not namespace-wide activity.
                        if not any(os.readlink(fd) == "socket:[" + inode + "]" for fd in fds[inode]):
                            continue
                        channels.append({"protocol": protocol, "inode": int(inode), "state": state,
                                         "destination_sha256": hashlib.sha256((protocol + ":" + remote).encode()).hexdigest(),
                                         "evidence": "PEER_FD_INODE_JOIN_NET_TABLE_RECHECKED"})
                readable += 1
            except (OSError, ValueError) as error:
                result["errors"].append({"table": protocol, **failure(error)})
        after = start_ticks(directory)
        if before != after:
            result["errors"].append({"reason": "PEER_IDENTITY_CHANGED_DURING_SCAN"})
            return result
        result.update(status="PARTIAL" if readable and (fds or not result["errors"]) else "UNOBSERVABLE", channels=channels,
                      process_start_ticks=before, readable_tables=readable)
    except (OSError, ValueError, IndexError) as error:
        result["errors"].append(failure(error))
    return result


class Monitor:
    def __init__(self, evidence):
        self.root = Path(evidence) / "network-monitor"
        self.root.mkdir(exist_ok=False)
        self.lock = threading.RLock()  # creates no thread before seccomp admission
        self.sequence = 0
        self.stopped = None
        self.observations = {"peer_snapshots": 0, "peer_metadata_partial": 0, "peer_metadata_unobservable": 0}
        self.coverage = {
            "python_connections": "PARTIAL",
            "wrapped_calls": "ATTEMPT_AND_RESULT_METADATA_WHEN_WRAPPER_IS_REACHED",
            "native_connect_events": "UNOBSERVABLE",
            "native_live_sockets": "PARTIAL_AT_EXPLICIT_CHECKPOINTS_OR_UNOBSERVABLE",
            "peer_egress": "UNOBSERVABLE_TRAFFIC_PARTIAL_SOCKET_METADATA_WHEN_PERMITTED",
            "excluded": ["CACHED_PYTHON_METHODS", "DIRECT_NATIVE_SYSCALL_EVENTS", "CREATION_DENIAL_EVENTS",
                         "SHORT_LIVED_SOCKETS", "DESCENDANT_PROCESS_EVENTS", "PEER_PAYLOAD_OR_NETWORK_BYTES",
                         "REMOTE_OR_LATER_HOPS", "PROVISIONING_BEFORE_WORKER", "GUARD_INSTALLATION_SELF_TEST"],
            "privileged_observers": "NOT_USED", "background_sampling": False,
            "absence_of_events_means_no_leak": False,
        }
        self.event("coverage", source="MONITOR", coverage=self.coverage)

    def event(self, kind, **metadata):
        with self.lock:
            if self.sequence >= MAX_EVENTS:
                self.stopped = "NETWORK_MONITOR_EVENT_LIMIT"
                self.abort(self.stopped)
            self.sequence += 1
            row = {"sequence": self.sequence, "kind": kind,
                   "utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.monotonic_ns(),
                   "pid": os.getpid(), "native_thread_id": threading.get_native_id(), **metadata}
            try:
                write(self.root / (f"event-{self.sequence:06d}.json"), row)
            except Exception:
                self.stopped = "NETWORK_MONITOR_EVIDENCE_WRITE_FAILED"
                self.abort(self.stopped)
            return self.sequence

    def abort(self, reason):
        # Raising in a library thread would only kill that thread and can print
        # caller source lines through threading.excepthook. Terminate the worker
        # after durable stop metadata instead; the parent exports partial logs.
        if threading.current_thread() is not threading.main_thread():
            os._exit(2)
        raise SecurityStop("NETWORK_SECURITY_STOP:" + reason) from None

    def stop(self, reason, **evidence):
        self.stopped = reason
        self.event("stop", source="MONITOR_POLICY", reason=reason, **evidence)
        self.abort(reason)

    def require_running(self):
        if self.stopped:
            self.abort(self.stopped)

    def deny(self, operation, sock=None, address=None):
        self.require_running()
        record = self.event("operation", source="PYTHON_GUARD", operation=operation,
                            family=int(sock.family) if sock is not None else None,
                            destination=destination(address), policy="DENY", outcome="NOT_DISPATCHED")
        self.stop("FORBIDDEN_PYTHON_NETWORK_OPERATION", event=record)

    def connect(self, original, sock, args, kwargs, *, connect_ex=False):
        self.require_running()
        address = args[0] if args else kwargs.get("address")
        operation = "connect_ex" if connect_ex else "connect"
        if sock.family != socket.AF_UNIX:
            self.deny(operation, sock, address)
        attempt = self.event("connect_attempt", source="PYTHON_SOCKET_WRAPPER", operation=operation,
                             family=int(sock.family), socket_type=int(sock.type), destination=destination(address), policy="ALLOW_AF_UNIX")
        try:
            value = original(sock, *args, **kwargs)
        except OSError as error:
            self.event("connect_result", source="PYTHON_SOCKET_WRAPPER", attempt=attempt,
                       outcome="OS_ERROR", **failure(error))
            raise ConnectionFailure(error.errno or errno.EIO, "NETWORK_CONNECT_FAILED") from None
        except Exception as error:
            self.event("connect_result", source="PYTHON_SOCKET_WRAPPER", attempt=attempt,
                       outcome="CALL_ERROR", **failure(error))
            raise ConnectionCallFailure("NETWORK_CONNECT_CALL_FAILED") from None
        code = int(value) if connect_ex else 0
        self.event("connect_result", source="PYTHON_SOCKET_WRAPPER", attempt=attempt,
                   outcome="CONNECTED" if code == 0 else "PENDING_OR_OS_ERROR", errno=code)
        if code == 0:
            self.inspect_peer(sock, "PYTHON_SOCKET_WRAPPER", attempt=attempt)
        return value

    def inspect_peer(self, sock, source, **context):
        peer = credentials(sock)
        observation = peer_channels(peer)
        with self.lock:
            self.observations["peer_snapshots"] += 1
            self.observations["peer_metadata_" + observation["status"].lower()] += 1
        event = self.event("peer_snapshot", source=source, peer=peer, observation=observation, **context)
        if observation["channels"]:
            # A proven IP channel is a conservative stop trigger, NOT proof that
            # this process forwarded worker data or reached the public Internet.
            self.stop("PEER_CONNECTED_INET_CHANNEL_OBSERVED", event=event,
                      forwarded_worker_data="UNOBSERVABLE")

    def checkpoint(self, phase):
        self.require_running()
        examined = 0
        errors = []
        try:
            for index, entry in enumerate(Path("/proc/self/fd").iterdir()):
                if index >= MAX_FDS:
                    errors.append({"reason": "FD_SCAN_TRUNCATED"})
                    break
                duplicate = None
                try:
                    fd = int(entry.name)
                    if not stat.S_ISSOCK(os.fstat(fd).st_mode):
                        continue
                    duplicate = os.dup(fd)
                    sock = socket.socket(fileno=duplicate)
                    duplicate = None  # ownership moved to sock
                    with sock:
                        examined += 1
                        inode = os.fstat(sock.fileno()).st_ino
                        try:
                            address = sock.getpeername()
                        except OSError:
                            address = None
                        event = self.event("live_socket", source="FD_SNAPSHOT_ORIGIN_UNATTRIBUTED", phase=phase,
                                           inode=inode, family=int(sock.family), socket_type=int(sock.type),
                                           destination=destination(address), connect_result="UNOBSERVABLE_HISTORY",
                                           timestamp_scope="OBSERVATION_NOT_CONNECT_TIME",
                                           socket_state="CONNECTED_AT_SNAPSHOT" if address is not None else "UNCONNECTED_OR_UNOBSERVABLE")
                        if sock.family != socket.AF_UNIX:
                            self.stop("WORKER_NON_UNIX_SOCKET_OBSERVED", event=event)
                        if address is not None:
                            self.inspect_peer(sock, "FD_SNAPSHOT_ORIGIN_UNATTRIBUTED", socket_event=event)
                except OSError as error:
                    errors.append(failure(error))
                finally:
                    if duplicate is not None:
                        os.close(duplicate)
        except OSError as error:
            errors.append(failure(error))
        self.event("checkpoint", source="PROC_SELF_FD", phase=phase, examined_sockets=examined,
                   status="UNOBSERVABLE" if errors and not examined else "PARTIAL", errors=errors)
        self.require_running()

    def finish(self):
        summary = {"schema": "internvl3-network-observation-v1", "coverage": self.coverage,
                   "observations": self.observations,
                   "security_assessment": "VIOLATION_OR_RISK_SIGNAL" if self.stopped else "PARTIAL",
                   "stop_reason": self.stopped, "events_attempted": self.sequence,
                   "indirect_internet_relay": "UNOBSERVABLE", "no_leak_claim": False,
                   "residual_risk": "LOCAL_PEER_RELAY_NOT_EXCLUDED_REQUIRES_LEAD_DECISION"}
        write(self.root / "summary.json", summary)
        return summary
