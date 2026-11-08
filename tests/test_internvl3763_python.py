"""Synthetic offline Python Input security and actual inherited setup composition."""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import json
import zipfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from safeshift import internvl3763_python as py
from safeshift import internvl3763_operator as op
from safeshift import internvl3763_campaign as campaign
from safeshift.pilot.artifacts import write, read, sha
from safeshift.pilot.contract import digest


def synthetic_archive(path, members=None):
    with tarfile.open(path, "w:gz") as tar:
        for name, kind, payload in members or [("python/bin/python3.11", "file", b"SYNTHETIC_EXECUTABLE")]:
            member = tarfile.TarInfo(name)
            if kind == "file":
                member.size, member.mode = len(payload), 0o755
                tar.addfile(member, io.BytesIO(payload))
            else:
                member.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE,
                    "fifo": tarfile.FIFOTYPE}[kind]
                member.linkname = payload
                tar.addfile(member)


@contextmanager
def synthetic_mount(inputs, members=None):
    """Replace only archive identity and OS mount observation; real bytes/extractor."""
    expected = deepcopy(py.manifest())
    original_binding = py.binding()
    folder = Path(inputs) / py.REF.split("/")[1]
    folder.mkdir(parents=True, exist_ok=False)
    archive = folder / expected["filename"]
    synthetic_archive(archive, members)
    expected["lock"].update(size_bytes=archive.stat().st_size, sha256=sha(archive))
    write(folder / py.MARKER, expected)
    with patch.object(py, "manifest", return_value=expected), \
            patch.object(py, "binding", return_value=original_binding), \
            patch.object(os, "statvfs", return_value=NS(f_flag=1), create=True), \
            patch.object(os, "ST_RDONLY", 1, create=True):
        yield folder, expected


class PythonInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs, self.scratch, self.out = (self.root / x for x in ("input", "scratch", "out"))
        for path in (self.inputs, self.scratch, self.out):
            path.mkdir()
        self.request = {"bindings": {"runtime": {"python_input": py.binding()},
            "dataset": {"dataset_sources": [py.REF]}}}
        self.download = patch.object(py.train_python, "urlopen", side_effect=AssertionError("NO_PYTHON_NETWORK"))
        self.spy = self.download.start(); self.addCleanup(self.download.stop)
        self.addCleanup(self.spy.assert_not_called)

    def stage(self):
        return py.stage(self.inputs, self.request, self.scratch, self.out, {}, time.monotonic()+60)

    def test_lock_science_and_inherited_source_are_unchanged(self):
        self.assertEqual(digest(campaign.science()), "ea03e1b716d46399032283137da073df899df427eef7dddf3d2d090b1a748f50")
        self.assertEqual(py.manifest()["lock"]["size_bytes"], 29713170)
        self.assertEqual(py.manifest()["lock"]["sha256"], "f6e955dc9ddfcad74e77abe6f439dac48ebca14b101ed7c85a5bf3206ed2c53d")
        for name in ("safeshift/candidates/train_python.py", "safeshift/candidates/train_runtime.py",
                "safeshift/pilot/bootstrap.py", "configs/candidate160/python3119.json"):
            self.assertEqual((py.ROOT/name).read_bytes(), subprocess.check_output(
                ["git", "show", "f88a152f481691bf678ad721ec6d2f25f95084bf:"+name], cwd=py.ROOT))

    def test_missing_input_emits_blocked_receipt_without_probe_download_or_load(self):
        with patch.object(py.boot, "probe_interpreter") as probe, self.assertRaisesRegex(ValueError, "MOUNT"):
            self.stage()
        probe.assert_not_called()
        self.assertEqual(read(self.out / "python-input.json")["status"], "BLOCKED")

    def test_bytes_size_manifest_private_version_and_extra_files_fail_before_extraction(self):
        for fault in ("bytes", "size", "manifest", "private", "version", "extra", "duplicate", "writable", "slug"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                inputs = Path(temp)/"input"
                with synthetic_mount(inputs) as (folder, expected):
                    archive = folder / expected["filename"]
                    if fault == "bytes":
                        archive.write_bytes(b"x"*archive.stat().st_size)
                    elif fault == "size":
                        archive.write_bytes(b"x")
                    elif fault in ("manifest", "private", "version"):
                        bad = deepcopy(expected)
                        if fault == "manifest": bad["lock"]["sha256"] = "0"*64
                        if fault == "private": bad["private"] = False
                        if fault == "version": bad["ref"] = py.REF[:-1]+"2"
                        (folder/py.MARKER).write_text(__import__("json").dumps(bad))
                    elif fault == "extra": (folder/"poison.py").write_bytes(b"x")
                    elif fault == "duplicate":
                        other = inputs/"other"; other.mkdir(); write(other/py.MARKER, expected)
                    elif fault == "slug": folder.rename(inputs/"wrong-slug")
                    with patch.object(py.train_python, "extract") as extract, \
                            patch.object(os, "statvfs", return_value=NS(f_flag=0 if fault == "writable" else 1), create=True), \
                            self.assertRaises(ValueError):
                        py.mounted(inputs, self.request)
                    extract.assert_not_called()

    def test_safe_extract_probe_selection_and_restart_preserves_first_tree(self):
        with synthetic_mount(self.inputs), patch.object(py.boot, "probe_interpreter", side_effect=lambda p, env:
                {"eligible": True, "version": [3,11,9], "executable": str(p)}) as probe:
            selected = self.stage()
            self.assertEqual(selected.read_bytes(), b"SYNTHETIC_EXECUTABLE")
            self.assertEqual(read(self.out/"python-input.json")["selected_python"], str(selected))
            probe.assert_called_once()
            fresh_output = self.root/"out2"; fresh_output.mkdir()
            with self.assertRaises(FileExistsError):
                py.stage(self.inputs, self.request, self.scratch, fresh_output, {}, time.monotonic()+60)
            self.assertEqual(selected.read_bytes(), b"SYNTHETIC_EXECUTABLE")
            self.assertEqual(read(fresh_output/"python-input.json")["status"], "BLOCKED")

    def test_corrupt_archive_and_malicious_tar_never_probe(self):
        cases = [
            [("../escape", "file", b"x")], [("/absolute", "file", b"x")],
            [("python/bin/python3.11", "hardlink", "outside")],
            [("python/bin/python3.11", "symlink", "../../../escape")],
            [("python/bin/fifo", "fifo", "")],
            [("python/bin/python3.11", "file", b"x"), ("python/bin/python3.11", "file", b"y")],
            [("python/link", "symlink", "target"), ("python/target", "file", b"x"),
                ("python/link/child", "file", b"y")],
        ]
        for members in cases:
            with self.subTest(members=members), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); out=root/"out"; out.mkdir(); scratch=root/"scratch"; scratch.mkdir()
                with synthetic_mount(root/"input", members), patch.object(py.boot, "probe_interpreter") as probe:
                    with self.assertRaises(ValueError):
                        py.stage(root/"input", self.request, scratch, out, {}, time.monotonic()+60)
                    probe.assert_not_called()
                    self.assertEqual(read(out/"python-input.json")["status"], "BLOCKED")
        with synthetic_mount(self.inputs) as (folder, expected):
            archive = folder/expected["filename"]; archive.write_bytes(b"not a gzip tar")
            expected["lock"].update(size_bytes=archive.stat().st_size, sha256=sha(archive))
            (folder/py.MARKER).write_text(__import__("json").dumps(expected))
            with self.assertRaises(tarfile.ReadError): self.stage()

    def test_bombs_disk_deadline_and_wrong_interpreter_stop(self):
        for fault in ("members", "expanded", "disk", "deadline", "probe", "version", "executable"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temp:
                root=Path(temp); out=root/"out"; out.mkdir(); scratch=root/"scratch"; scratch.mkdir()
                with synthetic_mount(root/"input") as (folder, expected), ExitStack() as stack:
                    if fault in ("members", "expanded"):
                        expected["lock"]["max_members" if fault == "members" else "max_uncompressed_bytes"] = 0
                        (folder/py.MARKER).write_text(__import__("json").dumps(expected))
                    if fault == "disk": stack.enter_context(patch.object(shutil, "disk_usage", return_value=NS(free=0)))
                    stack.enter_context(patch.object(py.boot, "probe_interpreter", side_effect=lambda p, env: {
                        "eligible": fault != "probe", "version": [3,12,0] if fault == "version" else [3,11,9],
                        "executable": "wrong" if fault == "executable" else str(p)}))
                    with self.assertRaises(ValueError):
                        py.stage(root/"input", self.request, scratch, out, {}, time.monotonic()+(-1 if fault=="deadline" else 60))

    def test_inherited_setup_cannot_fall_back_to_system_or_network(self):
        from safeshift.candidates.train_runtime import prepare_runtime
        verified = self.scratch/"input-cpython3119/python/bin/python3.11"
        original = py.train_python.provision
        with patch.object(py.boot, "probe_interpreter", return_value={"eligible": False}):
            with py.selected_interpreter(verified, self.scratch):
                self.assertFalse(py.boot.probe_interpreter(Path(sys.executable))["eligible"])
                with self.assertRaisesRegex(ValueError, "DOWNLOAD_FORBIDDEN"):
                    prepare_runtime(py.ROOT, "internvl35", self.scratch, self.out, {}, time.monotonic()+60)
        self.assertIs(py.train_python.provision, original)

    def test_current_mount_layout_wrong_owner_and_symlink_alias(self):
        with synthetic_mount(self.inputs) as (folder, expected):
            nested = self.inputs/"datasets/nguynanhtn"; nested.mkdir(parents=True)
            moved = nested/folder.name; folder.rename(moved)
            self.assertEqual(py.mounted(self.inputs, self.request)[0], moved/expected["filename"])
            wrong = self.inputs/"datasets/attacker"; nested.rename(wrong)
            with self.assertRaisesRegex(ValueError, "IDENTITY"):
                py.mounted(self.inputs, self.request)
            wrong.rename(nested)
            archive = moved/expected["filename"]
            saved = self.root/"archive"; archive.rename(saved)
            try:
                archive.symlink_to(saved)
            except OSError:
                self.skipTest("host does not allow symlink creation; covered on Linux")
            with self.assertRaises(ValueError): py.mounted(self.inputs, self.request)

    def test_campaign_wrong_binding_extra_input_or_metadata_rejected_and_ledger_unchanged(self):
        from test_internvl3763_campaign import fixture
        request, grant, comments = fixture(self.root/"ledger")
        ledger = campaign.Ledger.create(self.root/"ledger", self.root/"mirror", grant, "synthetic-machine")
        before = {str(p.relative_to(self.root)): p.read_bytes() for r in (ledger.root, ledger.mirror)
            for p in r.rglob("*") if p.is_file()}
        for fault in ("missing", "version", "private", "owner", "slug", "extra", "duplicate", "capsule"):
            bad = deepcopy(request)
            data = bad["bindings"]["dataset"]["dataset_sources"]
            value = bad["bindings"]["runtime"]["python_input"]
            if fault == "missing": data.remove(py.REF)
            elif fault == "version": value["ref"] = py.REF[:-1]+"2"
            elif fault == "private": value["private"] = False
            elif fault == "owner": value["ref"] = "attacker/python/1"
            elif fault == "slug": value["ref"] = "nguynanhtn/other/1"
            elif fault == "extra": data.append("nguynanhtn/extra/1")
            elif fault == "duplicate": data.append(py.REF)
            else: bad["bindings"]["runtime"]["execution_input"]["ref"] = py.REF
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                campaign.bind(grant, bad, reader=lambda key: comments[key])
        after = {str(p.relative_to(self.root)): p.read_bytes() for r in (ledger.root, ledger.mirror)
            for p in r.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        sources = op.input_sources(request)
        meta = NS(machine_shape="NvidiaTeslaT4", dataset_data_sources=[x.rsplit("/",1)[0] for x in sources["dataset_sources"]],
            kernel_data_sources=[])
        op.verify_kernel_metadata_inputs(meta, sources)
        meta.dataset_data_sources.remove(py.REF.rsplit("/",1)[0])
        with self.assertRaises(ValueError): op.verify_kernel_metadata_inputs(meta, sources)


try:
    import requests
    from kagglesdk import KaggleClient
except ImportError:
    KaggleClient = None


@unittest.skipUnless(KaggleClient, "requires existing pinned operator SDK")
class PythonProviderTests(unittest.TestCase):
    def setUp(self):
        op.check_sdk()
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.folder, self.expected = self.stack.enter_context(synthetic_mount(self.root/"input"))
        self.request = {"bindings": {"runtime": {"python_input": py.binding()},
            "dataset": {"dataset_sources": [py.REF]}}}
        self.calls, self.fault = [], None
        self.active_name = None
        self.stack.enter_context(patch("socket.socket", side_effect=AssertionError("NO_NETWORK")))
        self.stack.enter_context(patch.object(requests.adapters.HTTPAdapter, "send", self.adapter))
        self.client = NS(build_kaggle_client=lambda: KaggleClient(api_token="SYNTHETIC_SECRET"),
            dataset_list_files=self.list_files, kernels_push=Mock())

    def list_files(self, ref, **kwargs):
        self.assertEqual(ref, py.REF)
        files = [NS(name=p.name, total_bytes=p.stat().st_size) for p in self.folder.iterdir()]
        if self.fault == "listing": files.pop()
        return NS(files=files, error_message="", next_page_token="next" if self.fault=="pagination" else "")

    def adapter(self, request, **kwargs):
        self.assertEqual(kwargs["timeout"], (10,30))
        self.calls.append(request)
        response = requests.Response(); response.request = request; response.url = request.url
        response.status_code = 200
        response.headers["Content-Type"] = "application/json"
        body = b""
        if request.url.endswith("/GetDatasetMetadata"):
            body = json.dumps({"info": {"isPrivate": self.fault != "public",
                "ownerUser": "attacker" if self.fault=="owner" else "nguynanhtn",
                "datasetSlug": "wrong" if self.fault=="slug" else py.REF.split("/")[1]}}).encode()
        elif request.url.endswith("/DownloadDataset"):
            value = json.loads(request.body)
            self.assertEqual(value["datasetVersionNumber"], 1)
            self.assertEqual(value["ownerSlug"]+"/"+value["datasetSlug"]+"/1", py.REF)
            self.active_name = value["fileName"]
            response.status_code = 302
            response.headers["Location"] = "https://storage.googleapis.com/synthetic?sig=OPAQUE"
        elif request.url.startswith("https://storage.googleapis.com/"):
            self.assertNotIn("Authorization", request.headers)
            self.assertEqual(kwargs["proxies"], {})
            if self.fault == "transport": raise requests.ConnectionError("SIGNED_SECRET")
            if self.fault == "http": response.status_code = 503
            body = (self.folder/self.active_name).read_bytes()
            if self.fault == "bytes" and self.active_name != py.MARKER: body = b"x"*len(body)
            if self.fault == "size": body += b"x"
            if self.fault in ("zip", "zip-path", "zip-duplicate", "zip-link"):
                stream = io.BytesIO()
                with zipfile.ZipFile(stream, "w") as bundle:
                    entry = zipfile.ZipInfo("../escape" if self.fault=="zip-path" else self.active_name)
                    if self.fault == "zip-link": entry.external_attr = 0o120777 << 16
                    bundle.writestr(entry, body)
                    if self.fault == "zip-duplicate": bundle.writestr("extra", b"x")
                body = stream.getvalue()
            response.headers["Content-Type"] = "application/octet-stream"
        else:
            self.fail("Unexpected request: "+request.url)
        response.raw = io.BytesIO(body)
        response.headers["Content-Length"] = str(len(body))
        return response

    def test_real_sdk_private_v1_metadata_and_downloaded_bytes_before_submit(self):
        for mode in (None, "zip"):
            self.fault = mode
            proof = op.verify_python_input(self.client, self.request, self.root/str(mode))
            self.assertEqual(proof["status"], "PASS")
            self.assertEqual(proof["sha256"], self.expected["lock"]["sha256"])
            self.client.kernels_push.assert_not_called()
        self.assertEqual(len(self.calls), 10)  # metadata + two (RPC + signed GET), twice

    def test_provider_metadata_transport_wrong_bytes_and_poisoned_zip_stop(self):
        for fault in ("public", "owner", "slug", "listing", "pagination", "transport", "http",
                "bytes", "size", "zip-path", "zip-duplicate", "zip-link"):
            self.fault = fault
            with self.subTest(fault=fault), self.assertRaisesRegex(ValueError, "PYTHON_PROVIDER_FAILED_NO_RETRY"):
                op.verify_python_input(self.client, self.request, self.root/fault)
            receipt = read(self.root/fault/"receipt.json")
            self.assertEqual(receipt["status"], "BLOCKED")
            self.assertNotIn("SECRET", json.dumps(receipt))
            self.client.kernels_push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
