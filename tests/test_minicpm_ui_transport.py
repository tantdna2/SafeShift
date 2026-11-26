"""Real pinned SDK serialization/HTTP adapter fixtures; zero network."""
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace as NS
import unittest
from unittest.mock import MagicMock, patch

import test_train3763_manual as manual
from test_train3763_manual import KaggleClient, output_fixture, DOWNLOAD_OUTPUTS
from safeshift.pilot.artifacts import sha


@unittest.skipUnless(KaggleClient is not None, "requires existing pinned operator venv")
class MiniCPMPairTransportTests(unittest.TestCase):
    setUp = manual.ManualDownloadTests.setUp

    def test_ancestor_download_is_versioned_size_bounded_and_create_only(self):
        from scripts.minicpm_fulltrain_transport import download_ancestor
        client = MagicMock()
        remote = client.build_kaggle_client.return_value.__enter__.return_value
        remote.http_client.return_value._verbose = False
        rpc = remote.datasets.dataset_api_client.download_dataset
        response = rpc.return_value.__enter__.return_value
        response.status_code = 200
        source = self.root / "ancestor-0000.bin"
        source.write_bytes(b"synthetic-ancestor")
        with patch("safeshift.internvl3763_operator.capsule_http", return_value=nullcontext()):
            for index, chunks in enumerate(([source.read_bytes()], [b"first", bytes(66000)])):
                destination = self.root / ("ancestor-download-" + str(index))
                destination.mkdir()
                response.iter_content.return_value = chunks
                args = (client, "nguynanhtn", "example", "1", source, destination)
                if index == 0:
                    self.assertEqual(sha(download_ancestor(*args)), sha(source))
                    with self.assertRaisesRegex(ValueError, "FAILED_NO_RETRY"):
                        download_ancestor(*args)
                else:
                    with self.assertRaisesRegex(ValueError, "FAILED_NO_RETRY"):
                        download_ancestor(*args)
                    self.assertEqual((destination / "download.part").read_bytes(), b"first")
                query = rpc.call_args.args[0]
                self.assertEqual((query.file_name, query.dataset_version_number), (source.name, 1))

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
