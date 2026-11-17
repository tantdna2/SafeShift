"""V6 collection requires RAM/reclaim/group receipts; CPU synthetic only."""
from copy import deepcopy
from pathlib import Path
import unittest

import test_minicpm_fulltrain_ui as fixtures
from safeshift.fulltrain import minicpm_ui as ui
from safeshift.pilot.artifacts import read, write, export
from safeshift.pilot.contract import digest


class V6CollectionTests(unittest.TestCase):
    setUp = fixtures.OwnerUITests.setUp
    results = fixtures.OwnerUITests.results

    def control(self):
        attempt, supervisor, _ = self.results()
        root = supervisor.with_suffix('')
        (root/'checksums.json').unlink()
        snapshot = {'status': 'OBSERVED', 'cgroup': {'memory.events': {'oom': 0, 'oom_kill': 0}},
                    'scope': 'SYNTHETIC_RECEIPT_ONLY'}
        for mode in ('admit', 'setup', 'reclaim', 'cpu', 'gpu', 'native'):
            process = root/(mode+'-process.json')
            if process.exists():
                value = read(process); process.unlink()
            else:
                value = {'status': 'EXITED', 'returncode': 0}
            value['group_exit'] = {'status': 'NO_LIVE_MEMBERS'}
            write(process, value)
            stage = root/mode/'stage.json'
            if not stage.exists():
                write(stage, {'status': 'RETURNED', 'stage': mode,
                    'request_sha256': digest(self.value['request']), 'source_sha256': self.value['request']['source_sha256'],
                    'native_attempt_permitted': False})
            write(root/mode/'stage-entry-memory.json', snapshot)
            write(root/mode/'stage-exit-memory.json', snapshot)
        write(root/'reclaim/owned-advice.json', {'scan_complete': True, 'deleted_files': 0, 'effect': 'ADVISORY_NOT_RAM_PROOF'})
        floor = self.value['request']['resource_policy']['free_ram_mib']*2**20
        write(root/'reclaim/post-advice-resources.json', {'memory': {'available_bytes': floor}})
        return attempt, root

    def verify(self, attempt, control):
        archive = control.parent/'v6-supervisor.zip'
        export(control, archive)
        return ui.verify_results(self.value, self.dataset, attempt, archive, self.root/'verified', memory_required=True)

    def test_complete_v6_receipts_preserve_pending_only_results(self):
        report = self.verify(*self.control())
        self.assertEqual(report['counts'], {'SUCCESS': 1, 'INVALID': 1, 'NOT_ATTEMPTED': 3761})
        self.assertEqual(report['status'], 'LOCAL_VERIFIED_NOT_PROVIDER_AUTHORITY')

    def test_missing_ram_or_unobserved_group_blocks_collection(self):
        attempt, control = self.control()
        (control/'reclaim/post-advice-resources.json').unlink()
        with self.assertRaises(FileNotFoundError): self.verify(attempt, control)

    def test_ineffective_reclaim_never_promoted_to_verified_continuation(self):
        attempt, control = self.control()
        path = control/'reclaim/post-advice-resources.json'; path.unlink()
        write(path, {'memory': {'available_bytes': 0}})
        with self.assertRaisesRegex(ValueError, 'UNCHANGED_RAM_FLOOR'): self.verify(attempt, control)

    def test_live_group_never_promoted_to_verified_continuation(self):
        attempt, control = self.control()
        path = control/'setup-process.json'; path.unlink()
        write(path, {'status': 'EXITED', 'returncode': 0, 'group_exit': {'status': 'LIVE_SURVIVORS'}})
        with self.assertRaisesRegex(ValueError, 'PROCESS_GROUP_UNVERIFIED'): self.verify(attempt, control)
