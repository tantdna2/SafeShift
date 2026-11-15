"""Real pinned SDK serialization/HTTP adapter fixtures; zero network."""
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

import test_train3763_manual as manual
from test_train3763_manual import KaggleClient, output_fixture, DOWNLOAD_OUTPUTS
from safeshift.pilot.artifacts import sha


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
class MiniCPMPairTransportTests(unittest.TestCase):
    setUp = manual.ManualDownloadTests.setUp

    def pairs(self):
        supervisor = self.root / ("a" * 32 + ".zip")
        supervisor.write_bytes(self.archive.read_bytes())
        self.transport.payloads[supervisor.name] = supervisor.read_bytes()
        self.transport.payloads[supervisor.name + ".sha256.json"] = ('{"sha256":"' + sha(supervisor) + '"}').encode()
        pairs = {"minicpm-fulltrain/" + self.archive.name: self.archive,
            "minicpm-fulltrain/supervision/" + supervisor.name: supervisor}
        files = []
        for name, local in pairs.items():
            fixture = output_fixture(local)
            for item in fixture["files"]:
                item["fileName"] = name + (".sha256.json" if item["fileName"].endswith(".json") else "")
                item["url"] = item["url"].rsplit('/',1)[0] + '/' + item["fileName"]
                files.append(item)
        self.transport.output["files"] = files
        return pairs

    def test_two_nested_pairs_real_sdk_exact_four_anonymous_gets(self):
        pairs = self.pairs()
        destination = self.root / "downloads"; destination.mkdir()
        proof = DOWNLOAD_OUTPUTS(self.client, "nguynanhtn/synthetic-mini", 1,
            self.archive, sha(self.archive), destination, output_pairs=pairs)
        self.assertEqual(proof["pairs"], {name: sha(local) for name, local in pairs.items()})
        self.assertEqual(len(self.transport.gets), 4)
        self.assertEqual(len(self.transport.listings), 1)
        for name, local in pairs.items(): self.assertEqual((destination / name).read_bytes(), local.read_bytes())

    def test_two_pairs_missing_extra_or_conflicting_path_before_get(self):
        from copy import deepcopy
        pairs = self.pairs(); original = deepcopy(self.transport.output)
        for i, change in enumerate((lambda f:f.pop(), lambda f:f.append({"fileName": "other.zip", "url":"invalid"}),
            lambda f:f[0].update(fileName="../synthetic.zip"), lambda f:f[0].update(url="https://evil.invalid/archive.zip"))):
            self.transport.output = deepcopy(original); change(self.transport.output["files"])
            destination = self.root / f"blocked-{i}"; destination.mkdir()
            with self.assertRaises(ValueError):
                DOWNLOAD_OUTPUTS(self.client, "nguynanhtn/synthetic-mini", 1,
                    self.archive, sha(self.archive), destination, output_pairs=pairs)
            self.assertEqual(self.transport.gets, [])
            self.assertEqual(list(destination.iterdir()), [])

    def test_two_pairs_sha_disagreement_preserves_download_without_acceptance(self):
        pairs = self.pairs()
        self.transport.payloads[self.archive.name + ".sha256.json"] = b'{"sha256":"wrong"}'
        destination = self.root / "partial"; destination.mkdir()
        with self.assertRaisesRegex(ValueError, "MANUAL_PROVIDER_ARCHIVE_MISMATCH"):
            DOWNLOAD_OUTPUTS(self.client, "nguynanhtn/synthetic-mini", 1,
                self.archive, sha(self.archive), destination, output_pairs=pairs)
        self.assertTrue((destination / "minicpm-fulltrain" / self.archive.name).exists())


if __name__ == "__main__":
    unittest.main()
