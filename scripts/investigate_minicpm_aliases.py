"""Issue165 continuation: falsify native exclusion / additional saved-logit hypotheses.

Read-only CPU diagnostics; never qualifies HNLO or runs a model. The prior exhaustive
receipt is pinned and its packets are rebuilt from the original archive before use.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

from safeshift.evaluation import minicpm_saved_hnlo as b
from safeshift.pilot.contract import LEVELS, digest
from scripts.verify_minicpm_saved_hnlo import write_new

RECORDS_SHA = "fa544e077faf8048029060946636f8d028977eea69ac79e913f23bb14e15684c"
INVENTORY_SHA = "1d2b7e166c45ca9a71b6e57881f4c943b592c5a917b2ea5daa8b16670246aa41"
ALIASES = ((1138, 59345), (1139, 59349), (1140, 59362), (1141, 59370))
SAVED = {str(pair[1]) for pair in ALIASES}
SOURCE_HASHES = {
    "modeling_minicpmv.py": "c59f539caf3bab55b4d491cb56449d6267ae07fe1ff25f63a859ea4a3e7f69e2",
    "tokenization_minicpmv_fast.py": "4512e985d4af814747a5c9d81d5f911fcb95c1d714b547282b01dd06639c08d0",
    "generation_utils.py": "dc9044d10c00abe7d341f2e777fb623925ff59dda2c1d814ecc7d6a685ad2ee1",
    "modeling_llama.py": "9f7e93602e876a8f3f171e4911df5a5898ac407b8eb8982099e52b53daf0469e",
}


def classify_inventory(names, members, source_paths, stem):
    """Exact output membership, not a suffix search that could miss a JSON vector."""
    b.require(len(names) == len(set(names)), "DUPLICATE_OUTPUT_NAME")
    root = "data/processed/candidate160/"
    prefix = root + stem + "/"
    source = "data/processed/candidate160_code/" + b.SOURCE_SHA + "/"
    archive_names = {n[len(prefix):] for n in names if n.startswith(prefix)}
    b.require(archive_names == set(members), "OUTPUT_ARCHIVE_MEMBERSHIP")
    counts = Counter(archive_member=len(archive_names))
    seen_source = set()
    marker_names = {
        "active_72440ef37c0b5d1f7e474e731f836537b918c49ddae7b6d1b8ef63e890f1afd7.lock",
        *["owner_slot_2084720f9c92ada8a31d33e7c967a4cba78cbcd1cb5f2b92ea6b706479d5bea7."
          + b.RUN + suffix for suffix in (".consumed.json", ".json", ".json.terminal.json")],
    }
    for name in names:
        if name.startswith(prefix):
            continue
        if name.startswith(source):
            relative = name[len(source):]
            if relative in source_paths:
                seen_source.add(relative)
                counts["source_file"] += 1
            else:
                match = re.fullmatch(r"(.+)/__pycache__/([^/]+)\.cpython-313\.pyc", relative)
                b.require(match and match[1] + "/" + match[2] + ".py" in source_paths,
                          "UNCLASSIFIED_SOURCE_OUTPUT")
                counts["source_bytecode"] += 1
        elif name in {root + "attempts/" + n for n in marker_names}:
            counts["attempt_marker"] += 1
        elif name in {root + stem + ".zip", root + stem + ".zip.sha256.json"}:
            counts["archive_or_sidecar"] += 1
        else:
            raise ValueError("UNCLASSIFIED_OUTPUT")
    b.require(seen_source == set(source_paths), "OUTPUT_SOURCE_MEMBERSHIP")
    return dict(counts)


def alias_witness(packet, decoders):
    """A stronger full-input/incremental witness; not another token-family selector."""
    raw = packet["raw"]
    ids, inputs = tuple(raw["generated_ids"]), tuple(raw["input_ids"])
    b.require(len(ids) == 11 and ids[-1] in raw["eos_token_ids"], "WITNESS_NATIVE_LENGTH")
    body, position = ids[:-1], 8
    b.require(ids[position] in {p[1] for p in ALIASES}, "WITNESS_ACTUAL_TOKEN")
    b.require(raw["actual_logits_processors"] == [], "WITNESS_PROCESSORS")
    b.require(all(s["all_finite"] is True and s["vocab_size"] == 73448
                  and s["argmax"] == token for s, token in zip(raw["steps"], ids))
              and len(raw["steps"]) == len(ids), "WITNESS_STEPS")
    b.require(all(set(s["raw_candidate_logits"]) == SAVED for s in raw["steps"]),
              "UNEXPECTED_SAVED_COORDINATES")
    response, label = raw["response"], packet["label"]
    b.require(response.count(label) == 1, "WITNESS_LABEL")
    before, after = response.split(label)
    for decoder in decoders:
        full = decoder.decode(inputs + body, False)
        b.require(full.endswith(response), "WITNESS_FULL_INPUT")
        context = full[:-len(response)]
        full_skipped = decoder.decode(inputs + body + ids[-1:], True)
        b.require(full_skipped.endswith(response), "WITNESS_FULL_INPUT_EOS")
        skipped_context = full_skipped[:-len(response)]
        for level, pair in zip(LEVELS, ALIASES):
            b.require(all(t in decoder.vocabulary and t not in decoder.special_ids
                          and t not in raw["eos_token_ids"] for t in pair), "WITNESS_TOKEN_DOMAIN")
            incremental = []
            for token in pair:
                sequence = body[:position] + (token,) + body[position + 1:]
                surface = before + level + after
                b.require(decoder.decode(sequence, False) == surface
                          and decoder.decode(inputs + sequence, False) == context + surface
                          and decoder.decode(inputs + sequence + ids[-1:], True)
                          == skipped_context + surface,
                          "WITNESS_CONTEXT_OR_EOS")
                incremental.append(decoder.decode(inputs + body[:position] + (token,), False))
            b.require(incremental[0] == incremental[1] == context + before + level,
                      "WITNESS_INCREMENTAL_PREFIX")
    return {"decision_step": position, "full_input_context_and_eos": True,
            "incremental_prefix": True, "two_non_special_ids_per_label": True,
            "saved_coordinates_per_step": 4, "absent_alias_coordinates_per_step": 4}


def investigate(archive_path, records_path, inventory_path, source_dir, extracted):
    b.require(b.file_sha(records_path) == RECORDS_SHA, "PRIOR_PROOF_PIN")
    b.require(b.file_sha(inventory_path) == INVENTORY_SHA, "OUTPUT_INVENTORY_PIN")
    for name, expected in SOURCE_HASHES.items():
        b.require(b.file_sha(Path(source_dir) / name) == expected, "NATIVE_SOURCE_PIN")
    records = b.strict_json(Path(records_path).read_bytes())
    inventory = b.strict_json(Path(inventory_path).read_bytes())
    b.require(inventory["kernel"] == "nguynanhtn/safeshift-minicpm4-official160-20261031"
              and inventory["version"] == 2 and inventory["status"] == "COMPLETE", "OUTPUT_IDENTITY")
    archive = b.SealedArchive(archive_path)
    try:
        execution, context, rows, serialized = b.bind_archive(archive)
        tokenizer, first, second = b.decoders(serialized)
        sources = archive.json("source_inventory.json")
        checked_source = {}
        for path in ("safeshift/candidates/backend.py", "safeshift/candidates/loading.py",
                     "safeshift/pilot/hnlo.py", "safeshift/pilot/contract.py",
                     "configs/cpu_g2_g3/public_source_lock.json"):
            original = subprocess.check_output(["git", "show", b.RUNTIME + ":" + path])
            b.require(b.sha(original) == sources[path], "CAPTURE_SOURCE_PIN")
            checked_source[path] = b.sha(original)
            if path.endswith("public_source_lock.json"):
                locked = b.strict_json(original)["minicpm4"]["files"]
                b.require(all(locked[name] == SOURCE_HASHES[name] for name in
                              ("modeling_minicpmv.py", "tokenization_minicpmv_fast.py")),
                          "MODEL_PUBLIC_SOURCE_PIN")
        counts = classify_inventory([r["name"] for r in inventory["remote_inventory"]],
                                    archive.z.namelist(), sources, Path(archive_path).stem)
        # Known official extraction only; bounded metadata walk, bytes hashed only
        # after exact archive membership. No additional data file is interpreted.
        extracted_root = Path(extracted)
        extracted_names = set()
        for index, path in enumerate(extracted_root.rglob("*")):
            b.require(index < 6000 and not path.is_symlink(), "EXTRACTION_WALK_BOUND")
            if path.is_file():
                extracted_names.add(path.relative_to(extracted_root).as_posix())
        b.require(extracted_names == set(archive.z.namelist()), "EXTRACTION_EXTRA_OR_MISSING_FILE")
        for name in sorted(extracted_names):
            expected = archive.checksums.get(name) if name != "checksums.json" else b.sha(archive.z.read(name))
            b.require(b.file_sha(extracted_root / name) == expected, "EXTRACTION_HASH_MISMATCH")
        details, schema_counts = [], Counter()
        for row, previous in zip(rows, records):
            packet, _ = b.packet_for(archive, row, execution, context, tokenizer)
            b.require(packet == previous["packet"] and row["ordinal"] == previous["ordinal"]
                      and row["status"] == previous["original_status"], "PRIOR_PACKET_MISMATCH")
            sample = f"calls/{row['ordinal']:06d}/run/samples/000000/"
            generation = archive.json(sample + "request.json")["generation"]
            b.require(all(generation[k] is None for k in ("bad_words_ids", "begin_suppress_tokens",
                      "suppress_tokens", "constraints", "force_words_ids", "forced_bos_token_id",
                      "forced_decoder_ids", "forced_eos_token_id", "sequence_bias", "watermarking_config"))
                      and generation["generation_kwargs"] == {}
                      and generation["output_scores"] is generation["output_logits"] is False,
                      "WITNESS_GENERATION")
            for step in packet["raw"]["steps"]:
                schema_counts[tuple(sorted(step))] += 1
                b.require(set(step) == {"step", "all_finite", "argmax", "dtype", "origin",
                                       "raw_candidate_logits", "vocab_size"}, "UNEXPECTED_STEP_SCHEMA")
                b.require(set(step["raw_candidate_logits"]) == SAVED, "UNEXPECTED_SAVED_COORDINATES")
            if row["status"] == "SUCCESS":
                negative = previous["derived"]["independent_negative_proof"]
                b.require(negative["complete_families"] == [[8, [list(p) for p in ALIASES]]]
                          and negative["reason"] == "AMBIGUOUS_TOKEN_BRANCH", "PRIOR_FAMILY_MISMATCH")
                details.append({"ordinal": row["ordinal"], "packet_sha256": digest(packet),
                                **alias_witness(packet, (first, second))})
        b.require(len(records) == len(rows) == 160 and len(details) == 155, "WITNESS_COUNTS")
        b.require(b.file_sha(archive_path) == b.ARCHIVE_SHA, "ORIGINAL_ARCHIVE_CHANGED")
        return {"schema": "safeshift-issue165-native-investigation-v1",
            "status": "HARD_BLOCKED_EXISTING_ARCHIVE", "audit_hold": True, "merge_authorized": False,
            "numeric_goal_complete": False, "hnlo_valid": 0, "success_without_hnlo": 155,
            "original_invalid_preserved": 5, "archive_sha256": b.ARCHIVE_SHA,
            "prior_private_records_sha256": RECORDS_SHA, "download_inventory_sha256": INVENTORY_SHA,
            "inventory_custody": "HISTORICAL_LOCAL_RECEIPT_NOT_A_FRESH_REMOTE_LISTING",
            "output_inventory_counts": counts, "full_input_dual_decoder_witnesses": len(details),
            "extracted_copy_members_matched": len(extracted_names),
            "native_steps_checked": sum(schema_counts.values()), "step_schema_variants": len(schema_counts),
            "native_source_sha256": SOURCE_HASHES, "original_archive_unchanged": True,
            "runtime_source_sha256": checked_source,
            "inference_calls": 0, "scientific_definition_changed": False}, details
    finally:
        archive.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("archive", "records", "inventory", "source-dir", "extracted", "output"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    output = Path(args.output)
    b.require(output.resolve().is_relative_to(Path("data/processed").resolve()), "PRIVATE_OUTPUT_REQUIRED")
    output.mkdir(parents=True, exist_ok=False)
    environment = {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "python": sys.version, "platform": platform.platform(), "seed": None,
        "command": ["python", "-B", "-m", "scripts.investigate_minicpm_aliases", *sys.argv[1:]],
        "source_files": {p: b.file_sha(p) for p in ("scripts/investigate_minicpm_aliases.py",
            "safeshift/evaluation/minicpm_saved_hnlo.py", "safeshift/evaluation/hnlo_method_a.py")}}
    write_new(output / "environment.json", environment)
    try:
        summary, details = investigate(args.archive, args.records, args.inventory, args.source_dir, args.extracted)
        write_new(output / "witnesses.private.json", details)
        summary.update(private_witnesses_sha256=b.file_sha(output / "witnesses.private.json"),
                       environment_sha256=b.file_sha(output / "environment.json"),
                       source_files=environment["source_files"])
        write_new(output / "public_receipt.json", summary)
        print(json.dumps(summary, sort_keys=True))
        return 0  # investigation completed; numeric objective remains blocked
    except Exception as error:
        write_new(output / "blocked.json", {"status": "INVESTIGATION_NOT_VERIFIED",
                                           "reason": str(error), "type": type(error).__name__})
        raise


if __name__ == "__main__":
    raise SystemExit(main())
