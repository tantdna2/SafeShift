"""Unprivileged CPU metadata/relay fixtures; no external Internet, CUDA or weights."""
from contextlib import redirect_stdout
import errno
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from safeshift.diagnostics.internvl3_recovery import monitor as audit, network, worker, bootstrap, contract, orchestrate
from safeshift.diagnostics.one_click.artifacts import write, sha256, package
from safeshift.runners.internvl3_snapshot import OFFLINE_ENV
from tests.test_internvl3_recovery import approved
from tests.test_hnlo_one_click import FakeOperations, source

ROOT = Path(__file__).resolve().parents[1]


def events(root):
    return [json.loads(p.read_bytes()) for p in sorted((Path(root) / "network-monitor").glob("event-*.json"))]


class MetadataTests(unittest.TestCase):
    def test_permission_failure_is_unobservable_and_does_not_record_error_text(self):
        with patch.object(audit, "start_ticks", side_effect=PermissionError(errno.EACCES, "secret/path")):
            result = audit.peer_channels({"status": "OBSERVED", "pid": 123})
        self.assertEqual(result["status"], "UNOBSERVABLE")
        self.assertEqual(result["channels"], [])
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["errors"][0]["errno"], errno.EACCES)

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Python build has no AF_UNIX")
    def test_peer_credentials_scope_and_unsupported_type(self):
        sock = SimpleNamespace(family=socket.AF_UNIX, type=socket.SOCK_DGRAM)
        self.assertEqual(audit.credentials(sock)["status"], "UNOBSERVABLE")
        sock.type = socket.SOCK_STREAM
        sock.getsockopt = lambda *a: (_ for _ in ()).throw(PermissionError(errno.EACCES, "secret"))
        self.assertEqual(audit.credentials(sock)["status"], "UNOBSERVABLE")

    def test_no_proc_visibility_produces_partial_summary_not_security_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = audit.Monitor(tmp)
            with patch.object(Path, "iterdir", side_effect=PermissionError(errno.EACCES, "secret")):
                monitor.checkpoint("fixture")
            summary = monitor.finish()
            self.assertEqual(events(tmp)[-1]["status"], "UNOBSERVABLE")
            self.assertEqual(summary["security_assessment"], "PARTIAL")
            self.assertEqual(summary["indirect_internet_relay"], "UNOBSERVABLE")
            self.assertFalse(summary["no_leak_claim"])
            self.assertNotIn("secret", json.dumps(events(tmp)))

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Python build has no AF_UNIX")
    def test_metadata_journal_order_destination_hash_and_failed_connect_sanitization(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = audit.Monitor(tmp)
            sock = SimpleNamespace(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
            def bad(*args, **kwargs):
                raise FileNotFoundError(errno.ENOENT, "secret", "private-destination")
            with self.assertRaisesRegex(OSError, "NETWORK_CONNECT_FAILED") as caught:
                monitor.connect(bad, sock, ("private-destination",), {})
            self.assertNotIn("private-destination", str(caught.exception))
            rows = events(tmp)
            self.assertEqual([r["sequence"] for r in rows], [1, 2, 3])
            self.assertTrue(all(r["utc"] and r["pid"] and r["native_thread_id"] for r in rows))
            self.assertLessEqual(rows[1]["monotonic_ns"], rows[2]["monotonic_ns"])
            self.assertEqual(rows[1]["destination"], audit.destination("private-destination"))
            self.assertEqual(rows[2]["outcome"], "OS_ERROR")
            self.assertNotIn("private-destination", json.dumps(rows))
            self.assertNotIn("secret", json.dumps(rows))

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Python build has no AF_UNIX")
    def test_connect_ex_pending_does_not_claim_connected_or_observe_peer(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor = audit.Monitor(tmp)
            sock = SimpleNamespace(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
            with patch.object(monitor, "inspect_peer") as peer:
                result = monitor.connect(lambda *a: errno.EINPROGRESS, sock, ("fixture",), {}, connect_ex=True)
            self.assertEqual(result, errno.EINPROGRESS)
            peer.assert_not_called()
            self.assertEqual(events(tmp)[-1]["outcome"], "PENDING_OR_OS_ERROR")

    @unittest.skipUnless(hasattr(socket, "AF_UNIX"), "Python build has no AF_UNIX")
    def test_forbidden_python_calls_stop_before_dispatch_without_payload_or_dns_logging(self):
        cases = ("connect", "connect_ex", "sendto", "getaddrinfo", "create_connection")
        for name in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp, socket.socket() as sock:
                monitor = audit.Monitor(tmp)
                with network.network_denied(monitor), self.assertRaises(audit.SecurityStop):
                    if name in ("connect", "connect_ex"):
                        getattr(sock, name)(("127.0.0.1", 9))
                    elif name == "sendto":
                        sock.sendto(b"SECRET-PAYLOAD", ("127.0.0.1", 9))
                    elif name == "getaddrinfo":
                        socket.getaddrinfo("SECRET-HOST", 80)
                    else:
                        socket.create_connection(("SECRET-HOST", 80))
                self.assertEqual(events(tmp)[1]["outcome"], "NOT_DISPATCHED")
                self.assertEqual(events(tmp)[1]["policy"], "DENY")
                self.assertNotIn("SECRET", json.dumps(events(tmp)))
                with self.assertRaises(audit.SecurityStop):
                    monitor.checkpoint("after-caller-swallowed-error")
                self.assertEqual(monitor.finish()["stop_reason"], "FORBIDDEN_PYTHON_NETWORK_OPERATION")

    def test_journal_write_failure_and_limit_stop_and_keep_prior_evidence(self):
        for mode in ("write", "limit"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                monitor = audit.Monitor(tmp)
                setting = patch.object(audit, "write", side_effect=OSError("secret")) if mode == "write" else patch.object(audit, "MAX_EVENTS", 1)
                with setting, self.assertRaises(audit.SecurityStop):
                    monitor.event("fixture")
                self.assertEqual(len(events(tmp)), 1)
                self.assertIsNotNone(monitor.finish()["stop_reason"])


class CheckpointRaceTests(unittest.TestCase):
    def checkpoint(self, first_error=None, duplicate_error=None):
        temporary = self.enterContext(tempfile.TemporaryDirectory())
        monitor = audit.Monitor(temporary)
        with patch.object(Path, "iterdir", return_value=iter([Path("/proc/self/fd/99")])), patch.object(
            audit.os, "fstat", side_effect=first_error or [SimpleNamespace(st_mode=0o140000)]), patch.object(
            audit.os, "dup", side_effect=duplicate_error):
            monitor.checkpoint("synthetic_cpu_race")
        return events(temporary)[-1], monitor.finish()

    def test_descriptor_closed_before_first_stat_is_recorded_as_race(self):
        row, summary = self.checkpoint(first_error=OSError(errno.EBADF, "synthetic closed enumeration fd"))
        self.assertEqual(row["closed_before_inspection"], 1)
        self.assertEqual(row["errors"], [])
        self.assertEqual(row["status"], "PARTIAL")
        self.assertFalse(summary["no_leak_claim"])

    def test_permission_failure_remains_unobservable(self):
        row, _ = self.checkpoint(first_error=PermissionError(errno.EACCES, "secret"))
        self.assertEqual(row["status"], "UNOBSERVABLE")
        self.assertEqual(row["errors"], [{"error_type": "PermissionError", "errno": errno.EACCES}])
        self.assertNotIn("secret", json.dumps(row))

    def test_bad_descriptor_after_first_stat_is_not_suppressed(self):
        row, _ = self.checkpoint(duplicate_error=OSError(errno.EBADF, "secret"))
        self.assertEqual(row["status"], "UNOBSERVABLE")
        self.assertEqual(row["errors"][0]["errno"], errno.EBADF)


class WorkerExportTests(unittest.TestCase):
    def test_security_stop_is_fatal_retained_exported_and_never_retried(self):
        # Real recovery worker/monitor + parent exporter; only source/authority,
        # seccomp installation and CUDA admission are synthetic CPU boundaries.
        class StopOperations(FakeOperations):
            failure = None
            events = []
            def worker(self, mode, model):
                self.events.append((mode, model))
                args = ["worker", "--mode", mode, "--model", model, "--cache", "unused",
                        "--source", str(self.source_path), "--evidence", str(self.evidence / model / mode),
                        "--capture-root", str(self.work)]
                def denied(*args, **kwargs):
                    socket.getaddrinfo("SECRET-HOST", 80)
                with patch.object(Path, "cwd", return_value=self.repo), patch.object(sys, "argv", args), patch.object(
                    bootstrap, "verify_topology"), patch.object(network, "deny_inet", return_value={"kind": "FAKE_CPU"}), patch.object(
                    worker, "environment", side_effect=denied), patch.dict(os.environ, OFFLINE_ENV):
                    assert worker.main() == 2
                return json.loads((self.evidence / model / mode / "result.json").read_bytes())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, output = root / "repo", root / "output"
            repo.mkdir(); output.mkdir()
            write(repo / contract.AUTHORITY, approved())
            for session in ("first", "second"):
                work = output / session
                work.mkdir()
                with redirect_stdout(io.StringIO()):
                    result = orchestrate.run(repo, work, output, source(), operations_factory=StopOperations)
                self.assertEqual(result["gpu_probe_status"], "NOT_RUN")
            self.assertEqual(StopOperations.events, [("preflight",), ("prepare", "internvl3"), ("inspect", "internvl3")])
            saved = json.loads((output / "first/evidence/internvl3/inspect/result.json").read_bytes())
            self.assertTrue(saved["common_fatal"])
            self.assertFalse(saved["TECHNICAL_HNLO_VALID"])
            self.assertEqual(saved["network_observation"]["stop_reason"], "FORBIDDEN_PYTHON_NETWORK_OPERATION")
            with tarfile.open(output / "first.tar.gz") as archive:
                names = archive.getnames()
                self.assertTrue(any("network-monitor/summary.json" in n for n in names))
                self.assertTrue(any("network-monitor/event-" in n for n in names))
                self.assertTrue(any(n.endswith("error.log") for n in names))
                self.assertFalse(any("qwen3" in n for n in names))
                journal = [n for n in names if "network-monitor/" in n]
                self.assertTrue(all(b"SECRET" not in archive.extractfile(n).read() for n in journal))
                self.assertTrue(all(b"SECRET" not in archive.extractfile(n).read() for n in names if n.endswith(".log")))
            proof = json.loads((output / "first_sha256.json").read_bytes())
            self.assertEqual(sha256(output / "first.tar.gz"), proof["sha256"])


@unittest.skipUnless(sys.platform == "linux", "Linux CPU procfs/seccomp fixture; not Kaggle evidence")
class LinuxMonitoringTests(unittest.TestCase):
    def child(self, code, *args):
        result = subprocess.run([sys.executable, "-c", code, *map(str, args)], cwd=ROOT,
                                env={**os.environ, "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"},
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_violation_in_library_thread_terminates_whole_child_preserving_journal(self):
        code = '''
import socket, threading, sys
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
m = Monitor(sys.argv[1]); deny_inet()
with network_denied(m):
    thread = threading.Thread(target=lambda: socket.getaddrinfo('SECRET-HOST', 80))
    thread.start(); thread.join()
raise AssertionError('only the library thread stopped')
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); evidence = root / "evidence"; evidence.mkdir()
            result = subprocess.run([sys.executable, "-c", code, str(evidence)], cwd=ROOT,
                                    env={**os.environ, "CUDA_VISIBLE_DEVICES": ""},
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertNotIn("SECRET", result.stderr)
            self.assertEqual(events(evidence)[-1]["reason"], "FORBIDDEN_PYTHON_NETWORK_OPERATION")
            self.assertFalse((evidence / "network-monitor/summary.json").exists())
            archive = package(evidence, root, "terminated")
            self.assertEqual(sha256(archive), json.loads((root / "terminated_sha256.json").read_bytes())["sha256"])
            self.assertTrue(any("network-monitor/event-" in r["path"] for r in json.loads((root / "terminated_manifest.json").read_bytes())["files"]))

    def test_local_forbidden_operations_are_logged_and_native_denials_remain_unobservable(self):
        self.child('''
import socket, tempfile, json, ctypes, errno
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor, SecurityStop
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
deny_inet()
for name in ('sendto', 'sendmsg', 'recvmsg', 'recvmsg_into'):
    with tempfile.TemporaryDirectory() as tmp, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        m = Monitor(tmp)
        with network_denied(m):
            try:
                if name == 'sendto': sock.sendto(b'SECRET', '/tmp/fixture')
                elif name == 'sendmsg': sock.sendmsg([b'SECRET'])
                elif name == 'recvmsg': sock.recvmsg(1)
                else: sock.recvmsg_into([bytearray(1)])
            except SecurityStop: pass
            else: raise AssertionError(name)
        assert m.finish()['stop_reason'] == 'FORBIDDEN_PYTHON_NETWORK_OPERATION'
        rows = [json.loads(p.read_bytes()) for p in m.root.glob('event-*.json')]
        assert any(r.get('operation') == name and r['policy'] == 'DENY' for r in rows)
        assert 'SECRET' not in json.dumps(rows)
with tempfile.TemporaryDirectory() as tmp:
    m = Monitor(tmp); libc = ctypes.CDLL(None, use_errno=True)
    for family in (2, 10):
        assert libc.socket(family, 1, 0) == -1 and ctypes.get_errno() == errno.EPERM
    assert len(list(m.root.glob('event-*.json'))) == 1
    assert 'CREATION_DENIAL_EVENTS' in m.finish()['coverage']['excluded']
''')

    def test_both_guards_unix_connect_and_connect_ex_metadata_and_peer_credentials(self):
        self.child('''
import socket, tempfile, os, json
from pathlib import Path
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
with tempfile.TemporaryDirectory() as tmp:
    m = Monitor(tmp)
    deny_inet()
    with network_denied(m), socket.socket(socket.AF_UNIX) as server:
        server.bind(tmp + '/fixture'); server.listen(2)
        for name in ('connect', 'connect_ex'):
            with socket.socket(socket.AF_UNIX) as client:
                assert getattr(client, name)(server.getsockname()) in (None, 0)
                accepted, _ = server.accept()
                with accepted:
                    os.write(client.fileno(), b'SYNTHETIC-BYTES')
                    assert os.read(accepted.fileno(), 15) == b'SYNTHETIC-BYTES'
                m.checkpoint(name)
    summary = m.finish()
    rows = [json.loads(p.read_bytes()) for p in sorted(m.root.glob('event-*.json'))]
    assert len([r for r in rows if r['kind'] == 'connect_result' and r['outcome'] == 'CONNECTED']) == 2
    assert any(r['kind'] == 'peer_snapshot' and r['peer']['pid'] == os.getpid() for r in rows)
    assert 'SYNTHETIC-BYTES' not in json.dumps(rows)
    assert summary['security_assessment'] == 'PARTIAL' and not summary['no_leak_claim']
''')

    def test_native_connect_unattributed_live_snapshot_and_short_lived_blind_spot(self):
        self.child('''
import ctypes, socket, tempfile, json
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
class Address(ctypes.Structure):
    _fields_ = [('family', ctypes.c_ushort), ('path', ctypes.c_char * 108)]
libc = ctypes.CDLL(None, use_errno=True)
with tempfile.TemporaryDirectory() as tmp:
    m = Monitor(tmp); deny_inet()
    with network_denied(m), socket.socket(socket.AF_UNIX) as server:
        path = (tmp + '/fixture').encode(); server.bind(path); server.listen(2)
        for phase in ('transient', 'persistent'):
            with socket.socket(socket.AF_UNIX) as client:
                address = Address(socket.AF_UNIX, path)
                assert libc.connect(client.fileno(), ctypes.byref(address), len(path) + 3) == 0
                accepted, _ = server.accept()
                with accepted:
                    if phase == 'persistent': m.checkpoint(phase)
        m.checkpoint('closed')
    rows = [json.loads(p.read_bytes()) for p in m.root.glob('event-*.json')]
    assert not any(r['kind'] in ('connect_attempt', 'connect_result') for r in rows)
    live = [r for r in rows if r['kind'] == 'live_socket' and r['socket_state'] == 'CONNECTED_AT_SNAPSHOT']
    assert live and all(r['source'] == 'FD_SNAPSHOT_ORIGIN_UNATTRIBUTED' and r['phase'] == 'persistent' for r in live)
    summary = m.finish()
    assert summary['coverage']['native_connect_events'] == 'UNOBSERVABLE'
    assert summary['indirect_internet_relay'] == 'UNOBSERVABLE' and not summary['no_leak_claim']
''')

    def test_proc_inode_join_ignores_other_owners_and_rejects_pid_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); peer = root / "123"
            (peer / "fd").mkdir(parents=True); (peer / "net").mkdir()
            (peer / "fd/4").symlink_to("socket:[456]")
            row = "0: 0100007F:1234 0100007F:4567 01 0 0 0 0 0 {}\n"
            for protocol in ("tcp", "tcp6", "udp", "udp6"):
                (peer / "net" / protocol).write_text("header\n" + (row.format(999) + row.format(456) if protocol == "tcp" else ""))
            with patch.object(audit, "start_ticks", return_value=10):
                observed = audit.peer_channels({"status": "OBSERVED", "pid": 123}, root)
            self.assertEqual([r["inode"] for r in observed["channels"]], [456])
            self.assertEqual(observed["status"], "PARTIAL")
            self.assertNotIn("0100007F", json.dumps(observed))
            with patch.object(audit, "start_ticks", side_effect=[10, 11]):
                changed = audit.peer_channels({"status": "OBSERVED", "pid": 123}, root)
            self.assertEqual(changed["status"], "UNOBSERVABLE")
            self.assertEqual(changed["channels"], [])

    def test_simulated_relay_forwarding_is_baselined_then_guard_stops_observed_ip_channel(self):
        # External peer is intentionally outside the worker filter. Only loopback
        # TCP is used; its fixture forwarding does NOT prove Internet observation.
        relay_code = '''
import socket, sys
with socket.create_connection(('127.0.0.1', int(sys.argv[2]))) as upstream, socket.socket(socket.AF_UNIX) as server:
    server.bind(sys.argv[1]); server.listen(2); print('ready', flush=True)
    for _ in range(2):
        client, _ = server.accept()
        with client:
            data = client.recv(1024)
            if data: upstream.sendall(data)
'''
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as collector:
            collector.bind(("127.0.0.1", 0)); collector.listen(1); collector.settimeout(10)
            path = Path(tmp) / "relay.sock"
            relay = subprocess.Popen([sys.executable, "-c", relay_code, str(path), str(collector.getsockname()[1])],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, close_fds=True)
            try:
                upstream, _ = collector.accept()
                with upstream:
                    upstream.settimeout(10)
                    self.assertEqual(relay.stdout.readline().strip(), "ready")
                    with socket.socket(socket.AF_UNIX) as baseline:
                        baseline.connect(str(path)); baseline.sendall(b"SYNTHETIC-RELAY")
                    self.assertEqual(upstream.recv(1024), b"SYNTHETIC-RELAY")
                    self.child('''
import socket, sys, json
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor, SecurityStop
from safeshift.diagnostics.internvl3_recovery.network import deny_inet, network_denied
m = Monitor(sys.argv[2]); deny_inet()
with network_denied(m), socket.socket(socket.AF_UNIX) as client:
    try: client.connect(sys.argv[1])
    except SecurityStop: pass
    else: raise AssertionError('relay risk was not stopped')
summary = m.finish()
assert summary['stop_reason'] == 'PEER_CONNECTED_INET_CHANNEL_OBSERVED'
assert summary['indirect_internet_relay'] == 'UNOBSERVABLE'
rows = [json.loads(p.read_bytes()) for p in m.root.glob('event-*.json')]
assert any(r['kind'] == 'peer_snapshot' and r['peer']['pid'] == int(sys.argv[3]) and r['observation']['channels'] for r in rows)
assert not summary['no_leak_claim']
''', path, tmp, relay.pid)
                    self.assertEqual(upstream.recv(1024), b"")  # monitored child never sends a payload
                self.assertEqual(relay.wait(timeout=10), 0)
            finally:
                if relay.poll() is None:
                    relay.terminate(); relay.wait(timeout=10)
                relay.stdout.close(); relay.stderr.close()

    def test_observed_worker_ip_socket_is_direct_fatal_violation(self):
        self.child('''
import socket, tempfile
from safeshift.diagnostics.internvl3_recovery.monitor import Monitor, SecurityStop
# Deliberately violates clean-start/filter invariant in this negative fixture.
with tempfile.TemporaryDirectory() as tmp, socket.socket() as forbidden:
    m = Monitor(tmp)
    try: m.checkpoint('negative-fixture')
    except SecurityStop: pass
    else: raise AssertionError('worker IP fd accepted')
    assert m.finish()['stop_reason'] == 'WORKER_NON_UNIX_SOCKET_OBSERVED'
''')


if __name__ == "__main__":
    unittest.main()
