import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from safeshift.ls1 import tokenizer
from safeshift.ls1.t1_cpu import StarmieAdapter, VARIANT_NAMES, variant_results, verify_resources
from scripts import prepare_hnlo_t1_tokenizers as prep


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=False):
        return "".join(chr(value) for value in ids)


class NativeEncoding:
    def __init__(self, ids):
        self.ids = ids


class NativeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return NativeEncoding([ord(char) for char in text])

    def decode(self, ids, skip_special_tokens=False):
        return "".join(chr(value) for value in ids)

    def get_vocab_size(self, with_added_tokens=True):
        return 256


class HnloT1CpuTests(unittest.TestCase):
    def test_preparation_output_is_confined_to_data_processed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "data" / "processed"
            processed.mkdir(parents=True)
            expected = processed / "t1-run"
            self.assertEqual(
                prep.resolve_output_root("data/processed/t1-run", root=root),
                expected.resolve(),
            )
            self.assertFalse(expected.exists())
            with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_INSIDE_DATA_PROCESSED"):
                prep.resolve_output_root("data/processed/../../escape", root=root)
            with self.assertRaisesRegex(ValueError, "OUTPUT_MUST_BE_INSIDE_DATA_PROCESSED"):
                prep.resolve_output_root(root.parent / "absolute-escape", root=root)

    def test_starmie_adapter_preserves_exact_text(self):
        adapter = StarmieAdapter(NativeTokenizer())
        text = '\t```json\n{"safety_level" : "Level04"}\n```\n'
        ids = adapter.encode(text, add_special_tokens=False)
        self.assertEqual(adapter.decode(ids, clean_up_tokenization_spaces=False), text)
        self.assertEqual(len(adapter), 256)

    def test_variant_report_covers_exact_28_existing_checks(self):
        evidence = tokenizer.probe(CharacterTokenizer())
        rows = variant_results(evidence)
        self.assertEqual([row["variant"] for row in rows], list(VARIANT_NAMES))
        self.assertEqual(sum(len(row["responses"]) for row in rows), 28)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_resource_manifest_checks_sha256_and_inventory(self):
        revision = "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / revision
            snapshot.mkdir()
            files = []
            for index, name in enumerate(prep.QWEN_FILES):
                payload = (name + ":" + str(index)).encode("ascii")
                (snapshot / name).write_bytes(payload)
                files.append({
                    "path": name,
                    "size_bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                })
            manifest = {
                "schema_version": "safeshift-hnlo-t1-tokenizer-resources-v1",
                "models": [{
                    "model_key": "qwen3",
                    "repo_id": "Qwen/Qwen3-VL-8B-Instruct",
                    "revision": revision,
                    "files": files,
                }],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(
                len(verify_resources("qwen3", snapshot, manifest_path)["files"]),
                len(prep.QWEN_FILES),
            )
            (snapshot / "tokenizer.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "RESOURCE_SHA256_MISMATCH"):
                verify_resources("qwen3", snapshot, manifest_path)

            manifest["models"][0]["files"].pop()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PINNED_RESOURCE_MANIFEST_INVENTORY_MISMATCH"):
                verify_resources("qwen3", snapshot, manifest_path)

    def test_preparation_allowlist_excludes_weights(self):
        self.assertEqual(set(prep.QWEN_FILES), {
            "chat_template.json", "config.json", "merges.txt", "tokenizer.json",
            "tokenizer_config.json", "vocab.json",
        })
        for name in prep.QWEN_FILES:
            self.assertFalse(name.endswith(prep.FORBIDDEN_SUFFIXES))
        with self.assertRaisesRegex(ValueError, "MODEL_WEIGHT_DOWNLOAD_FORBIDDEN"):
            prep.safe_relative_file("model.safetensors")


if __name__ == "__main__":
    unittest.main()
