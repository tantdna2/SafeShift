"""CPU simulations for the supervised driver and the renamed Serial 8 export."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from safeshift.fulltrain import gpu_driver as driver, minicpm_serial8 as serial8
from safeshift.pilot.artifacts import read, write
from safeshift.pilot.contract import digest
from scripts import minicpm_fulltrain_recovery as recovery, owner_verify_minicpm_offline as owner
from scripts import reconcile_train3763_manual as manual
from test_fresh_fulltrain_revision import budgets


class DriverTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        for name in driver.LIBRARIES:
            (self.root / name).write_bytes(b"\x7fELFfixture")

    def test_missing_driver_blocks_and_retains_probe(self):
        (self.root / "libcuda.so.1").unlink()
        with self.assertRaisesRegex(ValueError, "DRIVER_MOUNT"):
            driver.bind(self.root, directories=(str(self.root),))
        self.assertEqual(read(self.root / "driver-library-binding.json")["status"], "BLOCKED")

    def test_isolated_binding_and_exit_12_evidence(self):
        loader = Mock()
        with patch.dict(driver._HANDLE, clear=True), patch.dict(os.environ, {"LD_LIBRARY_PATH": "unchanged"}):
            bound = driver.bind(self.root, directories=(str(self.root),), loader=loader)
            loader.assert_called_once()
            run = Mock(side_effect=subprocess.CalledProcessError(12, driver.QUERY, stderr="NVML unavailable"))
            with self.assertRaises(subprocess.CalledProcessError):
                driver.hardware("minicpm4", budgets(), bound, self.root, run=run)
            self.assertEqual(run.call_args.kwargs["env"]["LD_LIBRARY_PATH"], str(bound))
            self.assertEqual(os.environ["LD_LIBRARY_PATH"], "unchanged")
            receipt = read(self.root / "gpu-nvidia-smi.json")
            self.assertEqual((receipt["returncode"], receipt["stderr"]), (12, "NVML unavailable"))

    def test_loaded_floor_and_preload_floor_are_independently_enforced(self):
        run = Mock(return_value=SimpleNamespace(returncode=0,
            stdout="0,NVIDIA T4,5,570.0.0\n1,NVIDIA T4,20,570.0.0\n"))
        policy = budgets()
        with self.assertRaisesRegex(ValueError, "INDIVIDUAL_GPU_HEADROOM"):
            driver.hardware("minicpm4", policy, self.root, self.root, run=run)
        torch = Mock()
        torch.version.cuda = "12.4"
        torch.cuda.device_count.return_value = 1
        torch.cuda.get_device_capability.return_value = (7, 5)
        torch.cuda.mem_get_info.return_value = (5 * 2**20, 32 * 2**20)
        torch.ones.return_value.sum.return_value.item.return_value = 1
        with patch.dict(os.environ, {"CUDA_VISIBLE_DEVICES": "0"}):
            got = driver.loaded("minicpm4", policy, self.root, self.root, "admitted", 5, run=run, torch_module=torch)
            self.assertEqual(got["resident_gpu0_min_free_mib"], 5)
            with self.assertRaisesRegex(ValueError, "RESIDENT_GPU0_HEADROOM"):
                driver.loaded("minicpm4", policy, self.root, self.root, "blocked", 6, run=run, torch_module=torch)


class OwnerClosureTests(unittest.TestCase):
    def test_renamed_serial8_owner_transport_repeat_checks_and_ambiguous_inventory(self):
        job = serial8.TICKET_JOB
        client = Mock()
        client.kernels_status.return_value.status = "COMPLETE"
        provider = {"job_id": job, "version": 1, "state": "COMPLETE", "kernel_id": serial8.KERNEL_ID,
            "enable_gpu": True, "machine_shape": "NvidiaTeslaT4", "notebook_code_sha256": "a" * 64,
            "remote_notebook_sha256": "b" * 64, "safeshift_metadata": "MATCHED"}
        ticket = {"payload": {"start_before_unix": 1, "notebook_code_sha256": "a" * 64}}
        value = {"job": job, "input_sources": {"dataset_sources": ["one/1", "two/1", "three/1", "four/1"],
            "kernel_sources": ["five/1"]}, "ancestors": []}
        item = {"notebook": {"cells": []}, "ticket": ticket, "value": value}
        from safeshift.fulltrain.minicpm_execution import MARKER
        cap = {"metadata": {"observed_unix": 1}, "private": True, "version": 1,
            "files": {owner.c.ui.MARKER: digest(value), MARKER: digest(ticket)}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = sorted([serial8.ARCHIVE, serial8.ARCHIVE + ".sha256.json"])
            side = write(root / names[1], {"synthetic": True})
            local = {"supervisor": serial8.ARCHIVE, "supervisor_sha256": serial8.ZIP_SHA,
                "sidecar_sha256": side, "provider_files_sha256": digest(names)}
            output = {"pairs": {serial8.ARCHIVE: serial8.ZIP_SHA}, "log_sha256": "e" * 64, "inventory": names}
            with patch.object(recovery, "account_jobs", return_value={job}) as inventory, \
                    patch.object(manual, "observe_kernel", side_effect=lambda *args, **kw: deepcopy(provider)) as observe, \
                    patch.object(manual, "download_outputs", return_value=output), patch.object(owner, "capsule", return_value=cap):
                closure = owner.provider_closure(client, item, local, root, root, root, serial8.PROVIDER_JOBS,
                    kernel_id=serial8.KERNEL_ID)
                serial8.verify_closure(closure, local, item)
                self.assertEqual(observe.call_count, 2)
                self.assertEqual(inventory.call_count, 2)
                self.assertTrue(all(call.kwargs["kernel_id"] == serial8.KERNEL_ID for call in observe.call_args_list))
                inventory.return_value = set(serial8.PROVIDER_JOBS)
                with self.assertRaisesRegex(ValueError, "ABSENT_OR_AMBIGUOUS"):
                    owner.provider_closure(client, item, local, root, root, root, serial8.PROVIDER_JOBS,
                        kernel_id=serial8.KERNEL_ID)
