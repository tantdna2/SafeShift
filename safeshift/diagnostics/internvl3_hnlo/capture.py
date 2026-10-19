"""Compose existing InternVL capture/scorer/replay; no alternative HNLO formula."""
from io import BytesIO
from contextlib import contextmanager
import json
from pathlib import Path
import re

from ..hnlo_capture import Capture, ordered_t1_ids
from ..hnlo_hf import InternVL3Diagnostic
from ..one_click.artifacts import sha256, write
from ..one_click import worker as original
from ..one_click.contract import MODELS, synthetic_png
from .contract import LOCK, scope
from .resources import require_resources


@contextmanager
def count_native(evidence, state, cap):
    """Keep existing counters/provenance, add complete effective stop settings."""
    from transformers import InternVLForConditionalGeneration as cls
    from unittest.mock import patch
    with original.count_native("internvl3", evidence, state, cap):
        observed_stopping = cls._get_stopping_criteria

        def stopping(native, *args, **kwargs):
            criteria = observed_stopping(native, *args, **kwargs)
            details = []
            for item in criteria:
                eos = getattr(item, "eos_token_id", None)
                details.append({"class": type(item).__module__ + "." + type(item).__name__,
                                "max_length": getattr(item, "max_length", None),
                                "eos_token_id": None if eos is None else eos.tolist()})
            cap.write("actual-stopping-details", details)
            return criteria

        with patch.object(cls, "_get_stopping_criteria", stopping):
            yield


def verify_sources(repo):
    import transformers
    if transformers.__version__ != "4.52.4":
        raise ValueError("TRANSFORMERS_4_52_4_REQUIRED")
    audit = json.loads((repo / "configs/pre_freeze/internvl3_source_audit.v1.json").read_bytes())
    rows = []
    for row in audit["sources"].values():
        if "/src/transformers/" in row["url"]:
            relative = row["url"].split("/src/transformers/", 1)[1]
            local = Path(transformers.__file__).parent / relative
            if sha256(local) != row["response_sha256"]:
                raise ValueError("AUDITED_TRANSFORMERS_SOURCE_MISMATCH:" + relative)
            rows.append({"path": "transformers/" + relative, "sha256": row["response_sha256"]})
    extra = json.loads((repo / "configs/diagnostics/internvl3_hnlo_generation_sources.v1.json").read_bytes())
    if extra["transformers_version"] != transformers.__version__:
        raise ValueError("GENERATION_SOURCE_VERSION_MISMATCH")
    for row in extra["files"]:
        local = Path(transformers.__file__).parent / row["path"]
        if local.stat().st_size != row["size_bytes"] or sha256(local) != row["sha256"]:
            raise ValueError("GENERATION_SOURCE_CHECKSUM_MISMATCH")
        rows.append({"path": "transformers/" + row["path"], "sha256": row["sha256"]})
    required = {"transformers/generation/utils.py", "transformers/generation/logits_process.py",
                "transformers/generation/stopping_criteria.py"}
    if not required <= {row["path"] for row in rows}:
        raise ValueError("AUDITED_GENERATION_SOURCES_REQUIRED")
    return rows


def probe(repo, evidence, source, grant, cache, state, capture_root, drivers):
    from safeshift.ls1.tokenizer import TOKENIZER_FILES, probe as t1_probe
    from safeshift.ls1.runtime import NativeScorer
    from safeshift.protocol.classification_policy import load_policy, render_prompt
    from transformers import AutoTokenizer
    from PIL import Image
    verified_sources = verify_sources(repo)
    write(evidence / "generation-source.json", verified_sources)
    snapshot, receipt = original.verify_snapshot("internvl3", repo, cache)
    write(evidence / "offline-snapshot.json", receipt)
    write(evidence / "full-vector-budget.json", require_resources(capture_root, snapshot=snapshot))
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot), local_files_only=True, trust_remote_code=False, use_fast=True)
    t1 = t1_probe(tokenizer)
    candidate_ids = ordered_t1_ids(t1)
    write(evidence / "preload-t1.json", t1)
    state.update(t1="REFERENCE_PASS_RUNTIME_NOT_RUN", reference_t1="PASS_28_OF_28")
    run_id = "hnlo-" + grant["attempt_id"] + "-internvl3"
    state["run_id"] = run_id
    policy = load_policy(repo)["classification"]["internvl3"]
    sources = json.loads((repo / LOCK).read_bytes())["files"] + verified_sources
    png = synthetic_png()
    import hashlib
    if hashlib.sha256(png).hexdigest() != scope()["input_sha256"]:
        raise ValueError("SYNTHETIC_INPUT_CHECKSUM_MISMATCH")
    cap = Capture(capture_root, {"run_id": run_id, "sample_id": scope()["sample_id"],
        "model_id": MODELS["internvl3"]["id"], "revision": MODELS["internvl3"]["revision"],
        "tokenizer_revision": MODELS["internvl3"]["revision"],
        "tokenizer_files": [r for r in receipt["files"] if r["path"] in TOKENIZER_FILES],
        "software": state["runtime"], "source_commit": source["merge_commit"], "sources": sources,
        "command": "python -m safeshift.diagnostics.internvl3_hnlo.worker --mode probe --model internvl3",
        "prompt": render_prompt("internvl3", repo=repo), "input_sha256": scope()["input_sha256"],
        "configuration": policy, "seed": None, "authority": grant, "source_release": source})
    cap.write("synthetic-input", {"kind": "RGB", "size": [448, 448], "color": [128, 128, 128],
                                  "png_sha256": scope()["input_sha256"]})
    try:
        with count_native(evidence, state, cap):
            scorer = NativeScorer("internvl3", snapshot, tokenizer, candidate_ids, repo=repo)
            drivers.observe("after_model_load")
            original.no_forcing(scorer.config)
            with Image.open(BytesIO(png)) as image:
                # Existing persist_hf writes every raw/processed vector BEFORE
                # tokenizer.decode / parser. Never call scorer.generate here.
                InternVL3Diagnostic(scorer).generate(image, cap)
            drivers.observe("after_generate")
        for name in ("raw-provenance", "stopping-criteria", "runtime-t1", "trace"):
            if not cap.journal.exists(name):
                raise ValueError("NATIVE_GENERATION_EVIDENCE_MISSING")
        if cap.journal.read("runtime-t1") != t1:
            raise ValueError("RUNTIME_TOKENIZER_T1_MISMATCH")
        state["t1"] = "PASS_28_OF_28"
        cap.journal.seal()
    except BaseException as error:
        cap.failure(error)
        if not cap.journal.exists("seal"):
            cap.journal.seal()
        raise
    state.update(capture="PERSISTED_AWAITING_CPU_REPLAY", result="AWAITING_CPU_REPLAY")


def replay(root, run_id, tokenizer, probe_state):
    """All actual worker prerequisites AND persisted-vector CPU replay must pass."""
    from safeshift.ls1.tokenizer import probe as t1_probe
    if (probe_state.get("result") != "AWAITING_CPU_REPLAY" or
            probe_state.get("environment") != "EXACT_MATCH" or
            probe_state.get("t1") != "PASS_28_OF_28" or
            probe_state.get("load_calls") != 1 or probe_state.get("generate_calls") != 1 or
            probe_state.get("common_fatal") or
            probe_state.get("network_observation", {}).get("security_assessment") != "PARTIAL" or
            probe_state.get("network_observation", {}).get("stop_reason") is not None):
        raise ValueError("ALL_ACTUAL_PROBE_PREREQUISITES_REQUIRED")
    cap = Capture.open(root, run_id)
    if not cap.journal.verify():
        raise ValueError("SEALED_CAPTURE_REQUIRED")
    if cap.journal.read("runtime-t1") != t1_probe(tokenizer):
        raise ValueError("CPU_RUNTIME_TOKENIZER_T1_MISMATCH")
    native = cap.journal.read("native")
    details = cap.journal.read("actual-stopping-details")
    maxima = [r["max_length"] for r in details if r["class"].endswith(".MaxLengthCriteria")]
    eos_rows = [r["eos_token_id"] for r in details if r["class"].endswith(".EosTokenCriteria")]
    eos = native["generation_config"]["eos_token_id"]
    eos = eos if isinstance(eos, list) else [eos]
    if len(details) != 2 or maxima != [len(native["input_ids"]) + 32] or eos_rows != [eos]:
        raise ValueError("ACTUAL_STOPPING_SETTINGS_MISMATCH")
    raw_steps, processed_steps = native["raw_steps"], native["processed_steps"]
    if (type(raw_steps) is not int or type(processed_steps) is not int or
            not 1 <= raw_steps <= 32 or raw_steps != processed_steps):
        raise ValueError("ALL_MAX32_RAW_AND_PROCESSED_STEPS_REQUIRED")
    expected = {f"{kind}-{i:03d}" for kind in ("raw", "processed") for i in range(raw_steps)}
    if {n for n in cap.journal.inventory() if re.fullmatch(r"(?:raw|processed)-\d+", n)} != expected:
        raise ValueError("FULL_VECTOR_INVENTORY_MISMATCH")
    # Existing replay re-reads every vector, checks canonical Level01..04 order,
    # decision token, argmax, EOS, score provenance, and the existing formula.
    return original.replay(root, run_id, tokenizer)
