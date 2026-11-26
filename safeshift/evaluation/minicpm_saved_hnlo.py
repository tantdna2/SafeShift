"""Issue165: read-only CPU derivation from one externally pinned official ZIP.

No image/GT reader, model import, network, inference, report backfill or T2/T3
activation. Original checksums are checked before constructing derived seals.
"""
from collections import Counter
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

from safeshift.evaluation import hnlo_method_a as a
from safeshift.pilot.contract import GENERATION, LEVELS, PROMPT_SHA, digest, parse_label

ARCHIVE_SHA = "46a41359c3ab2978b9ee4ac010518e49a74141641d9334c29035bdc0c8eac877"
RUN = "owner_minicpm4_f52026d3c3bf49dbab2e3a8e33402f36"
ATTEMPT = RUN + "_a1"
RUNTIME = "c3c223bc69edd253d57bbba9344e0633b65b3de4"
SOURCE_SHA = "b1d6d8210b9b5b03c52b59cd339c75a4ec60f0dafb1fc0106623a9e25a2ec2a3"
CONFIG_SHA = "5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00"
DESCRIPTOR_SHA = "2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da"
MANIFEST_SHA = "f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995"
REVISION = "6f69a8235885be89608f3a71ffd40695b379e1e7"
IMPLEMENTATION = "minicpm4-resampler-attention-fp32-v1"
TOKENIZER_SHA = "8f7ccf860a471f0cf4bd0b75cba2b08ea1035013cadc825000befa6a0f95da56"
DECODER_SPEC = {"type": "Sequence", "decoders": [
    {"type": "Replace", "pattern": {"String": "\u2581"}, "content": " "},
    {"type": "ByteFallback"}, {"type": "Fuse"},
    {"type": "Strip", "content": " ", "start": 1, "stop": 0}]}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def reject(value):
        raise ValueError("NONFINITE_JSON")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=reject)


class SealedArchive:
    """Hash every payload without interpreting images, manifest labels or logs.

    Production callers always use ARCHIVE_SHA. Tests use a handwritten seal.
    Semantic reads are restricted to the explicit metadata/raw allowlist.
    """
    ROOTS = frozenset({"owner_execution.json", "release_config.json",
        "configuration_binding.json", "source_inventory.json", "worker_source.json",
        "accounting.json", "supervisor_accounting.json", "lineage_accounting.json",
        "history_index.json", "recovery_plan.json", "authorization_binding.json",
        "consumption.json", "tokenizer/runtime_tokenizer.json", "freeze.txt"})
    CALL = re.compile(r"calls/[0-9]{6}/run/(?:identity|runtime|results)\.json\Z|"
        r"calls/[0-9]{6}/run/samples/000000/(?:request|native|raw|result|processors|"
        r"effective_numerics|native_call|started)\.json\Z|"
        r"calls/[0-9]{6}/run/samples/000000/steps/[0-9]{3}\.json\Z")

    def __init__(self, path, expected_sha=ARCHIVE_SHA):
        self.path = Path(path)
        require(file_sha(path) == expected_sha, "ARCHIVE_SHA256_MISMATCH")
        self.archive_sha = expected_sha
        sidecar = strict_json(Path(str(path) + ".sha256.json").read_bytes())
        require(sidecar["sha256"] == expected_sha, "SIDECAR_SHA256_MISMATCH")
        self.z = zipfile.ZipFile(path, "r")
        try:
            entries = self.z.infolist()
            names = [e.filename for e in entries]
            require(len(names) == len(set(names)) <= 5000, "ARCHIVE_MEMBERSHIP")
            require(sidecar["members"] == len(names), "SIDECAR_MEMBERSHIP")
            require(all(not e.is_dir() and not e.flag_bits & 1 and e.file_size <= 32_000_000
                        and not e.filename.startswith(("/", "\\"))
                        and ".." not in e.filename.split("/") for e in entries), "ARCHIVE_ENTRY")
            require(sum(e.file_size for e in entries) <= 256_000_000, "ARCHIVE_SIZE_BOUND")
            self.checksums = strict_json(self.z.read("checksums.json"))
            require(set(names) == set(self.checksums) | {"checksums.json"}, "CHECKSUM_MEMBERSHIP")
            for name, checksum in self.checksums.items():
                require(sha(self.z.read(name)) == checksum, "MEMBER_SHA256_MISMATCH")
            self.reads = set()
        except Exception:
            self.z.close()
            raise

    def read(self, name):
        require(name in self.ROOTS or self.CALL.fullmatch(name), "SEMANTIC_READ_OUT_OF_SCOPE")
        self.reads.add(name)
        data = self.z.read(name)
        require(sha(data) == self.checksums[name], "MEMBER_CHANGED")
        return data

    def json(self, name):
        return strict_json(self.read(name))

    def close(self):
        self.z.close()


class ReferenceDecoder:
    """Independent Python implementation of the exact serialized decoder chain.

    BPE merges/encoder/normalizer do not participate in decoding. ByteFallback
    emits one U+FFFD per buffered byte if the complete run is invalid UTF-8,
    matching Rust; it does not use Python's partial replacement semantics.
    """
    def __init__(self, serialized):
        t = strict_json(serialized)
        require(t["decoder"] == DECODER_SPEC and t["model"]["type"] == "BPE",
                "UNSUPPORTED_RUNTIME_DECODER")
        vocab = t["model"]["vocab"]
        require(len(set(vocab.values())) == len(vocab), "VOCABULARY_ID_ALIAS")
        self.pieces = {v: k for k, v in vocab.items()}
        self.special = set()
        for token in t["added_tokens"]:
            i, value = token["id"], token["content"]
            require(i not in self.pieces or self.pieces[i] == value, "ADDED_TOKEN_CONFLICT")
            self.pieces[i] = value
            if token["special"]:
                self.special.add(i)
        require(all(type(i) is int and i >= 0 for i in self.pieces), "VOCABULARY_ID_TYPE")
        require(len(self.pieces) <= 131_072, "VOCABULARY_BOUND")
        self.units = {}
        for i, value in self.pieces.items():
            value = value.replace("\u2581", " ")
            self.units[i] = int(value[3:5], 16) if re.fullmatch(r"<0x[0-9A-Fa-f]{2}>", value) else value

    def decode(self, ids, skip):
        parts, buffered = [], bytearray()
        def flush():
            if buffered:
                try:
                    parts.append(buffered.decode("utf-8", errors="strict"))
                except UnicodeDecodeError:
                    parts.append("\ufffd" * len(buffered))
                buffered.clear()
        for i in ids:
            if skip and i in self.special:
                continue
            unit = self.units[i]
            if type(unit) is int:
                buffered.append(unit)
            else:
                flush()
                parts.append(unit)
        flush()
        text = ''.join(parts)
        return text[1:] if text.startswith(' ') else text


def decoders(serialized):
    # Only Rust tokenizer runtime is required, never Transformers or torch.
    import tokenizers
    require(tokenizers.__version__ == "0.21.1", "TOKENIZERS_VERSION_MISMATCH")
    native = tokenizers.Tokenizer.from_str(serialized.decode("utf-8"))
    reference = ReferenceDecoder(serialized)
    require(native.get_vocab(with_added_tokens=True) == {v: k for k, v in reference.pieces.items()},
            "INDEPENDENT_VOCABULARY_MISMATCH")
    ids, special = tuple(sorted(reference.pieces)), tuple(sorted(reference.special))
    # Includes all added IDs and special-token skipping, not just sparse keys.
    for i in ids:
        for skip in (False, True):
            require(native.decode([i], skip_special_tokens=skip) == reference.decode((i,), skip),
                    "INDEPENDENT_VOCABULARY_DECODE_MISMATCH")
    first = a.Decoder(serialized, ids, special,
                      lambda seq, skip: native.decode(list(seq), skip_special_tokens=skip))
    second = a.Decoder(serialized, ids, special, reference.decode)
    return native, first, second


def check_accounting(rows):
    require(type(rows) is list and len(rows) == 160
            and [r["ordinal"] for r in rows] == list(range(160))
            and len({r["sample_id"] for r in rows}) == 160, "PLANNED_ACCOUNTING")
    require(Counter(r["status"] for r in rows) == {"SUCCESS": 155, "INVALID": 5}, "ORIGINAL_COUNTS")
    require(all(r["hnlo"]["hnlo"] is None and r["attempts"] == r["native_calls"] == 1 for r in rows),
            "ORIGINAL_RESULTS_CHANGED")


def bind_archive(archive):
    execution = archive.json("owner_execution.json")
    expected = {"run_id": RUN, "attempt_id": ATTEMPT, "series_id": RUN, "run_kind": "INITIAL",
        "runtime_ref": RUNTIME, "source_sha256": SOURCE_SHA,
        "candidate_execution_config_sha256": CONFIG_SHA, "manifest_sha256": MANIFEST_SHA,
        "effective_implementation": IMPLEMENTATION, "model_key": "minicpm4", "split": "TRAIN"}
    require(all(execution[k] == v for k, v in expected.items()), "OFFICIAL_EXECUTION_IDENTITY")
    require(execution["model"]["id"] == "openbmb/MiniCPM-V-4"
            and execution["model"]["revision"] == REVISION, "MODEL_REVISION")
    require(archive.checksums["source_inventory.json"] == SOURCE_SHA
            and archive.checksums["pilot_manifest.json"] == MANIFEST_SHA, "SOURCE_MANIFEST_PIN")
    require(archive.json("worker_source.json") == {"model": execution["model"],
            "runtime_ref": RUNTIME, "source_sha256": SOURCE_SHA}, "WORKER_SOURCE")
    config = archive.json("release_config.json")
    require(digest(config) == CONFIG_SHA, "OFFICIAL_CONFIG_PIN")
    policy = config["effective_candidate"]["numerical_policy"]
    require(policy["id"] == IMPLEMENTATION and policy["implementation_sha256"] == DESCRIPTOR_SHA
            and execution["official_numerical_approval"]["descriptor_sha256"] == DESCRIPTOR_SHA,
            "DESCRIPTOR_PIN")
    context = archive.json("configuration_binding.json")
    require(context["configuration_contract"] == config, "CONFIGURATION_BINDING")
    binding = context["execution_release"]
    require(all(execution[k] == v for k, v in binding.items()), "EXECUTION_BINDING")
    authorization = archive.json("authorization_binding.json")
    require(authorization["execution_sha256"] == digest(execution), "AUTHORIZATION_BINDING")
    require(archive.json("consumption.json") == {"attempt_consumed": True, "attempt_id": ATTEMPT},
            "ATTEMPT_CONSUMPTION")
    history = archive.json("history_index.json")
    require(not history["runs"] and digest(history) == execution["history_sha256"], "INITIAL_HISTORY")
    lineage = archive.json("lineage_accounting.json")
    require(lineage["run_id"] == lineage["series_id"] == RUN and lineage["pooling_allowed"] is False,
            "LINEAGE_SERIES")
    require(len(lineage["samples"]) == 160 and all(not r["previous_results"] for r in lineage["samples"]),
            "INITIAL_LINEAGE")
    rows = archive.json("accounting.json")
    require(rows == archive.json("supervisor_accounting.json"), "ACCOUNTING_CUSTODY")
    check_accounting(rows)
    serialized = archive.read("tokenizer/runtime_tokenizer.json")
    require(sha(serialized) == TOKENIZER_SHA, "RUNTIME_TOKENIZER_PIN")
    freeze = archive.read("freeze.txt").decode().splitlines()
    require("tokenizers==0.21.1" in freeze and "transformers==4.51.3" in freeze, "RUNTIME_VERSIONS")
    return execution, context, rows, serialized


def packet_for(archive, row, execution, context, tokenizer):
    ordinal = row["ordinal"]
    root = f"calls/{ordinal:06d}/run/"
    sample = root + "samples/000000/"
    before = set(archive.reads)
    identity, runtime = archive.json(root + "identity.json"), archive.json(root + "runtime.json")
    request, native, raw, result = (archive.json(sample + n + ".json")
                                  for n in ("request", "native", "raw", "result"))
    binding = context["execution_release"]
    require(all(identity.get(k) == v for k, v in binding.items()), "CALL_EXECUTION_BINDING")
    require(identity["sample_id"] == row["sample_id"] and identity["ordinal"] == ordinal,
            "CALL_PLANNED_ID")
    require(raw["configuration_provenance"] == context and raw["execution_release"] == binding,
            "RAW_CONFIGURATION_BINDING")
    legacy = context["configuration_contract"]["legacy_transport_compatibility"]
    require(digest(legacy["settings_snapshot"]) == binding["legacy_transport_config_sha256"],
            "LEGACY_CONFIG_BINDING")
    expected_transport = {"config_sha256": binding["legacy_transport_config_sha256"],
        "input_sha256": identity["input_sha256"], "sample_id": row["sample_id"],
        "run_id": RUN, "model": execution["model"], "manifest_sha256": identity["runner_manifest_sha256"]}
    require(raw["identity"] == expected_transport, "RAW_TRANSPORT_BINDING")
    require(result == {k: v for k, v in row.items() if k not in ("ordinal", "sample_id")},
            "RESULT_ACCOUNTING_BINDING")
    require(result["raw_sha256"] == archive.checksums[sample + "raw.json"], "RAW_RESULT_CUSTODY")
    require(request["model"] == {k: execution["model"][k] for k in ("id", "revision")}
            and runtime["model"] == request["model"], "NATIVE_MODEL_BINDING")
    require(sha(request["prompt"].encode()) == PROMPT_SHA == runtime["prompt_sha256"], "PROMPT_PIN")
    require(request["input_ids"] == native["input_ids"] == raw["input_ids"]
            and native["generated_ids"] == raw["generated_ids"]
            and native["returned_ids"] == [raw["generated_ids"]]
            and native["input_prefix_match"] is None, "NATIVE_TOKEN_CUSTODY")
    require(native["sequence_semantics"] == "continuation_only_inputs_embeds", "NATIVE_SEMANTICS")
    require(archive.json(sample + "processors.json")["actual"] == raw["actual_logits_processors"] == [],
            "PROCESSOR_CUSTODY")
    require(archive.json(sample + "native_call.json") == {"invocation": 1, "max_new_tokens": 64},
            "NATIVE_CALL_COUNT")
    for i, step in enumerate(raw["steps"]):
        require(step == archive.json(sample + f"steps/{i:03d}.json") and step["vocab_size"] == 73448,
                "RAW_STEP_CUSTODY")
    generation = request["generation"]
    require(generation == runtime["generation"], "GENERATION_CUSTODY")
    require(all(generation[k] == v for k, v in GENERATION.items())
            and generation["bos_token_id"] == raw["input_ids"][0] == 1
            and generation["eos_token_id"] == raw["eos_token_ids"] == [73440, 2]
            and generation["num_return_sequences"] == 1
            and generation["stop_strings"] is None and generation["max_time"] is None
            and generation["token_healing"] is False, "GENERATION_SETTINGS")
    projection = {k: generation[k] for k in GENERATION}
    projection.update({k: generation[k] for k in ("pad_token_id", "repetition_penalty", "min_new_tokens")})
    projection["eos_token_ids"] = generation["eos_token_id"]
    rendered = tokenizer.encode(request["rendered_prompt"], add_special_tokens=False).ids
    probe = raw["token_probe"]
    tail = min(32, len(rendered), len(raw["input_ids"]))
    require(probe == request["token_probe"] and probe["boundary_ok"] is True
            and probe["boundary_tokens"] == probe["actual_boundary_tokens"] == rendered[-tail:]
            == raw["input_ids"][-tail:], "INDEPENDENT_RENDERED_BOUNDARY")
    require(parse_label(raw["response"]) == result["label"], "STRICT_PARSER_REPLAY")
    provenance = {"model_id": "openbmb/MiniCPM-V-4", "model_revision": REVISION,
        "runtime_commit": RUNTIME, "implementation_id": IMPLEMENTATION, "sample_id": row["sample_id"],
        "run_id": RUN, "series_id": RUN, "attempt_id": ATTEMPT, "source_sha256": SOURCE_SHA,
        "descriptor_sha256": DESCRIPTOR_SHA, "input_sha256": identity["input_sha256"],
        "prompt_sha256": PROMPT_SHA, "tokenizer_sha256": TOKENIZER_SHA,
        "configuration_sha256": digest(projection)}
    packet = {"schema": a.SCHEMA, "scope": a.SAVED_SCOPE, "label": result["label"],
        "provenance": provenance, "config": projection, "rendered_prompt_ids": rendered,
        "native": native, "raw": {k: raw[k] for k in ("generated_ids", "input_ids", "response",
        "eos_token_ids", "logit_capture_boundary", "tokenizer_serialization_sha256", "capture_error",
        "raw_nonfinite", "actual_logits_processors", "steps")}}
    links = {name: archive.checksums[name] for name in sorted(archive.reads - before)}
    return packet, links


def independent_numeric(values):
    # Direct exponent/sum/log, independent of both shifted production routines.
    with localcontext() as ctx:
        ctx.prec = 90
        numbers = [Decimal.from_float(float(v)) for v in values]
        return float(sum(v.exp() for v in numbers[:3]).ln() - numbers[3])


def verify(path, progress=None):
    archive = SealedArchive(path)
    try:
        execution, context, rows, serialized = bind_archive(archive)
        tokenizer, first, second = decoders(serialized)
        vocabulary_sha = digest({"ids": sorted(first.vocabulary), "special_ids": sorted(first.special_ids)})
        cache = a.EnumerationCache()
        derived = []
        for row in rows:
            packet, links = packet_for(archive, row, execution, context, tokenizer)
            for decoder in (first, second):
                require(decoder.decode(tuple(packet["raw"]["generated_ids"]), True)
                        == packet["raw"]["response"], "INDEPENDENT_FULL_OUTPUT_DECODE")
            # The seal binds a deterministic projection AFTER original custody,
            # not a self-issued replacement for the independently pinned ZIP.
            seal = a.Seal(digest(packet), TOKENIZER_SHA, vocabulary_sha)
            if row["status"] == "INVALID":
                require(packet["label"] is None, "INVALID_LABEL_RESCUE")
                result = {"status": "UNAVAILABLE", "reason": "ORIGINAL_INVALID_PRESERVED", "hnlo": None}
                proof = None
            else:
                require(packet["label"] in LEVELS, "SUCCESS_LABEL_MISSING")
                result = a.evaluate(packet, first, second, seal, cache=cache)
                proof = None
                if result["status"] == "PASS":
                    proof = a.build_proof(packet, first, seal, cache=cache)
                    independent = independent_numeric([result["raw_logits"][l] for l in LEVELS])
                    require(math.isclose(independent, result["hnlo"], rel_tol=1e-10, abs_tol=1e-10),
                            "THIRD_NUMERIC_ORACLE_MISMATCH")
                    result["decimal90_hnlo"] = independent
                elif result["reason"] in ("AMBIGUOUS_TOKEN_BRANCH", "AMBIGUOUS_DECISION_STEP",
                                          "NO_SINGLE_TOKEN_FAMILY", "MISSING_DECISION_LOGITS"):
                    negative = a.verify_unavailable(packet, second, seal, cache=cache)
                    require(negative["reason"] == result["reason"], "INDEPENDENT_REFUSAL_DISAGREEMENT")
                    result["independent_negative_proof"] = negative
                    # Check arithmetic for the available four coordinates, if
                    # present, without selecting them as a unique token family.
                    arithmetic = []
                    for step, labels in negative["complete_families"]:
                        sparse = packet["raw"]["steps"][step]["raw_candidate_logits"]
                        available = [[t for t in tokens if str(t) in sparse] for tokens in labels]
                        missing = [[t for t in tokens if str(t) not in sparse] for tokens in labels]
                        check = {"step": step, "available_ids": available, "missing_ids": missing,
                                 "numeric_check": "NOT_RUN", "qualified_hnlo": None}
                        if all(len(tokens) == 1 for tokens in available):
                            values = [sparse[str(tokens[0])] for tokens in available]
                            expected = independent_numeric(values)
                            require(math.isclose(a.hnlo(values), expected, rel_tol=1e-10, abs_tol=1e-10)
                                    and math.isclose(a.oracle(values), expected, rel_tol=1e-10, abs_tol=1e-10),
                                    "AVAILABLE_COORDINATES_ORACLE_MISMATCH")
                            check["numeric_check"] = "THREE_FORMULAS_AGREE_NOT_QUALIFIED"
                        arithmetic.append(check)
                    result["coordinate_diagnostics"] = arithmetic
            derived.append({"ordinal": row["ordinal"], "sample_id": row["sample_id"],
                "original_status": row["status"], "original_member_sha256": links,
                "packet_sha256": seal.evidence_sha256, "packet": packet,
                "proof": None if proof is None else {"decision_step": proof.decision_step,
                    "sequences": proof.sequences, "evidence_sha256": proof.evidence_sha256},
                "derived": result})
            if progress:
                progress(row["ordinal"] + 1, result["status"])
        require(file_sha(path) == ARCHIVE_SHA, "ORIGINAL_ARCHIVE_CHANGED")
        valid = sum(r["derived"]["status"] == "PASS" for r in derived)
        conclusive_missing = {"AMBIGUOUS_TOKEN_BRANCH", "AMBIGUOUS_DECISION_STEP",
            "NO_SINGLE_TOKEN_FAMILY", "MISSING_DECISION_LOGITS", "ORIGINAL_INVALID_PRESERVED"}
        unresolved = sum(r["derived"]["status"] != "PASS" and
            (r["derived"]["status"] != "UNAVAILABLE" or r["derived"]["reason"] not in conclusive_missing)
            for r in derived)
        summary = {"schema": "safeshift-issue165-derivation-v1", "result": "BLOCKED" if unresolved else "YES" if valid else "NO",
            "qualification": "CODEX_TECHNICAL_FINDING_PENDING_REVIEW_AND_INDEPENDENT_AUDIT",
            "archive_sha256": ARCHIVE_SHA, "source_sha256": SOURCE_SHA, "runtime_commit": RUNTIME,
            "configuration_sha256": CONFIG_SHA, "descriptor_sha256": DESCRIPTOR_SHA,
            "run_id": RUN, "series_id": RUN, "attempt_id": ATTEMPT, "run_kind": "INITIAL",
            "planned": 160, "original_success": 155, "original_invalid": 5,
            "hnlo_valid": valid, "success_without_hnlo": 155 - valid, "unresolved": unresolved,
            "reasons": dict(Counter(r["derived"]["reason"] or "VALID" for r in derived)),
            "payload_checksums_verified": len(archive.checksums), "original_archive_unchanged": True,
            "native_steps_checked": sum(len(r["packet"]["raw"]["steps"]) for r in derived),
            "tokenizer_sha256": TOKENIZER_SHA, "vocabulary_sha256": vocabulary_sha,
            "vocabulary_size": len(first.vocabulary), "tokenizers": "0.21.1",
            "exhaustive_searches": cache.searches, "structural_cache_hits": cache.hits,
            "independent_negative_proofs": sum("independent_negative_proof" in r["derived"] for r in derived),
            "missing_sparse_alias_records": sum(any(any(c["missing_ids"])
                for c in r["derived"].get("coordinate_diagnostics", [])) for r in derived),
            "available_four_coordinate_oracle_checks": sum(any(c["numeric_check"] ==
                "THREE_FORMULAS_AGREE_NOT_QUALIFIED" for c in r["derived"].get("coordinate_diagnostics", []))
                for r in derived),
            "semantic_members_read": sorted(archive.reads), "inference_calls": 0,
            "scientific_selection": "PENDING", "original_numeric_hnlo": 0}
        return summary, derived
    finally:
        archive.close()
