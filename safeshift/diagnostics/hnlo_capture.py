"""Durable CPU-readable evidence, never a new metric or an HNLO verdict.

Only already loaded/injected backends are consumed. There is no CLI, provisioner,
model loader, dataset reader, retry, reference generation or authority release.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
from types import SimpleNamespace

from safeshift.ls1.core import LEVELS, locate_decision, score_decision
from safeshift.ls1.runtime import capture_output, summarize_vector
from safeshift.ls1.tokenizer import probe
from safeshift.pa3.artifacts import json_bytes
from safeshift.pa3.native.journal import Journal, safe_relative


def digest(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def ordered_t1_ids(evidence):
    """Recover canonical label order from all 28 existing T1 branch proofs.

    probe.candidate_token_ids is a sorted inventory, not a label-to-ID mapping.
    Each check.token_ids follows LEVELS; require the same mapping in all cases.
    """
    checks = evidence["checks"]
    if len(checks) != 7 * len(LEVELS):
        raise ValueError("T1_EXACT_28_CASES_REQUIRED")
    ordered, variants = None, {}
    for check in checks:
        ids = check["token_ids"]
        if (len(ids) != len(LEVELS) or len(set(ids)) != len(LEVELS)
                or any(type(token) is not int or token < 0 for token in ids)):
            raise ValueError("T1_FOUR_DISTINCT_MAPPING_IDS_REQUIRED")
        if ordered is None:
            ordered = list(ids)
        if ids != ordered:
            raise ValueError("T1_INCONSISTENT_LABEL_TOKEN_MAPPING")
        label = check["generated_label"]
        if label not in LEVELS:
            raise ValueError("T1_CANONICAL_LABEL_REQUIRED")
        prefix, suffix = check["prefix_ids"], check["suffix_ids"]
        if (check["step"] != len(prefix)
                or check["response_ids"] != prefix + [ids[LEVELS.index(label)]] + suffix):
            raise ValueError("T1_RESPONSE_LABEL_MAPPING_MISMATCH")
        labels = variants.setdefault((tuple(prefix), tuple(suffix)), set())
        if label in labels:
            raise ValueError("T1_DUPLICATE_LABEL_CASE")
        labels.add(label)
    if len(variants) != 7 or any(labels != set(LEVELS) for labels in variants.values()):
        raise ValueError("T1_ALL_FOUR_LABELS_PER_VARIANT_REQUIRED")
    if evidence["candidate_token_ids"] != sorted(ordered):
        raise ValueError("T1_CANDIDATE_INVENTORY_MAPPING_MISMATCH")
    return ordered


class Capture:
    """One new run/call directory; every write fsyncs, hashes and rereads.

    Provenance is supplied by the future authorized caller, not inferred from a
    model name. Hashes establish integrity, not research authorization/authenticity.
    """

    def __init__(self, repo, metadata):
        required = {"run_id", "sample_id", "model_id", "revision", "tokenizer_revision",
                    "tokenizer_files", "software", "source_commit", "sources", "command",
                    "prompt", "input_sha256", "configuration", "seed"}
        if not required <= metadata.keys():
            raise ValueError("CAPTURE_PROVENANCE_REQUIRED")
        run_id = metadata["run_id"]
        if not re.fullmatch(r"hnlo-[a-z0-9][a-z0-9_-]{0,95}", run_id):
            raise ValueError("UNIQUE_DIAGNOSTIC_RUN_ID_REQUIRED")
        for key in ("revision", "tokenizer_revision", "source_commit"):
            if not re.fullmatch(r"[0-9a-f]{40}", metadata[key]):
                raise ValueError("IMMUTABLE_SOURCE_REQUIRED:" + key)
        if not re.fullmatch(r"[0-9a-f]{64}", metadata["input_sha256"]):
            raise ValueError("INPUT_CHECKSUM_REQUIRED")
        for key in ("tokenizer_files", "sources"):
            if not metadata[key]:
                raise ValueError("SOURCE_CHECKSUMS_REQUIRED")
            for row in metadata[key]:
                safe_relative(row["path"])
                if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                    raise ValueError("SOURCE_CHECKSUM_REQUIRED")
        self.journal = Journal(Path(repo) / "data/processed/hnlo_capture" / run_id, create=True)
        self.metadata = self.write("manifest", {
            **deepcopy(metadata), "schema": "hnlo-capture-diagnostic-v1",
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "prompt_sha256": digest(metadata["prompt"]),
            "hnlo": "N/A", "research_status": "PREPARED_NOT_VERIFIED",
        })

    def write(self, name, value):
        return self.journal.write(name, value)

    @classmethod
    def open(cls, repo, run_id):
        """Reopen evidence on CPU; do not create files or replay generation."""
        if not re.fullmatch(r"hnlo-[a-z0-9][a-z0-9_-]{0,95}", run_id):
            raise ValueError("UNIQUE_DIAGNOSTIC_RUN_ID_REQUIRED")
        instance = object.__new__(cls)
        instance.journal = Journal(Path(repo) / "data/processed/hnlo_capture" / run_id)
        instance.metadata = instance.journal.read("manifest")
        if instance.metadata["run_id"] != run_id:
            raise ValueError("MANIFEST_RUN_ID_MISMATCH")
        return instance

    def failure(self, error):
        # If storage itself fails, retain original files/torn writes and exception.
        try:
            self.write("failure", {"error_type": type(error).__name__, "reason": str(error),
                                   "hnlo": "N/A"})
        except (OSError, ValueError):
            pass

    def runtime_t1(self, tokenizer, comparison_tokenizer=None):
        actual = probe(tokenizer)
        self.write("runtime-t1", actual)
        ordered = ordered_t1_ids(actual)
        if comparison_tokenizer is not None and actual != probe(comparison_tokenizer):
            raise ValueError("RUNTIME_TOKENIZER_T1_MISMATCH")
        return ordered


def tensor_evidence(tensor):
    """Native scalar values plus dtype/shape; no lossy reduction before persistence."""
    return {"values": tensor.tolist(), "shape": list(tensor.shape),
            "dtype": str(tensor.dtype), "device": str(tensor.device)}


def vector(record):
    rows = record["values"]
    if (len(record["shape"]) != 2 or record["shape"][0] != 1
            or len(rows) != 1 or len(rows[0]) != record["shape"][1]):
        raise ValueError("BATCH1_VOCAB_LOGITS_REQUIRED")
    return rows[0]


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def tolist(self):
        return deepcopy(self.rows)


def persist_hf(output, input_ids, candidate_ids, tokenizer, capture, config, kwargs):
    """Persist native IDs and EVERY available raw/processed tensor before decode.

    In particular this must run before NativeScorer.capture_output, not after
    NativeScorer.generate. Independent files retain raw even if scores are absent.
    """
    sequences = output.sequences.tolist()
    raw = tuple(output.logits or ())
    scores = tuple(output.scores or ())
    native = capture.write("native", {
        "sequences": sequences, "input_ids": list(input_ids),
        "raw_steps": len(raw), "processed_steps": len(scores),
        "generation_config": config, "generation_kwargs": kwargs,
        "candidate_token_ids": list(candidate_ids),
    })
    for kind, tensors in (("raw", raw), ("processed", scores)):
        for i, tensor in enumerate(tensors):
            capture.write(f"{kind}-{i:03d}", tensor_evidence(tensor))
    saved = SimpleNamespace(sequences=Rows(native["sequences"]),
        logits=[capture.journal.read(f"raw-{i:03d}") for i in range(len(raw))],
        scores=[capture.journal.read(f"processed-{i:03d}") for i in range(len(scores))])
    record = capture_output(saved, input_ids, candidate_ids, tokenizer,
                            lambda row, ids, token: summarize_vector(vector(row), ids, token))
    record.update(generation_config=config, generation_kwargs=kwargs, forced_assistant_prefix_ids=[])
    eos = config.get("eos_token_id")
    eos = eos if type(eos) is list else [eos]
    record["eos_observation"] = {"configured_ids": eos,
        "positions": [i for i, token in enumerate(record["continuation_ids"]) if token in eos],
        "terminal_eos": record["continuation_ids"][-1] in eos}
    return capture.write("trace", record)


def review_trace(capture, tokenizer, *, persist=False):
    """CPU replay using existing alignment/selection rules, without computing HNLO."""
    raw = capture.journal.read("trace")
    try:
        if capture.journal.exists("failure"):
            raise ValueError("FAILED_CAPTURE_NOT_ELIGIBLE")
        if raw["forced_assistant_prefix_ids"]:
            raise ValueError("FORCED_PREFIX_FORBIDDEN")
        # Recompute summaries from the original fsynced vectors on CPU. The
        # compact trace alone must not become a replacement for native evidence.
        for i, step in enumerate(raw["steps"]):
            for kind in ("raw", "processed"):
                values = vector(capture.journal.read(f"{kind}-{i:03d}"))
                summary = summarize_vector(values, raw["candidate_token_ids"], step["generated_token"])
                if summary != step[kind]:
                    raise ValueError("PERSISTED_VECTOR_TRACE_MISMATCH")
        eos = raw["generation_config"]["eos_token_id"]
        eos = eos if type(eos) is list else [eos]
        mapping = locate_decision(tokenizer, raw["decoded_text"], raw["continuation_ids"], eos)
        details = score_decision(raw, mapping)
        if mapping["token_ids"] != raw["candidate_token_ids"]:
            raise ValueError("RUNTIME_CANDIDATE_IDS_CHANGED")
        result = {"alignment": "PASS", "decision": mapping,
                  "raw_label_logits": details["raw_label_logits"],
                  "processed_label_scores": details["processed_label_scores"],
                  "raw_and_processed_label_scores_equal": details["raw_and_processed_label_scores_equal"]}
    except (ValueError, KeyError, TypeError, IndexError, OverflowError) as error:
        result = {"alignment": "FAIL", "reason": str(error)}
    result = {**result, "hnlo": "N/A", "hnlo_verified": False}
    return capture.write("review", result) if persist else result
