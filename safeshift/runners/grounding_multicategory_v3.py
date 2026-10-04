"""Isolated synthetic v3 runtime. Import/dry-run never imports torch or loads models.

Execution requires a separately reviewed, exact-HEAD authorization and environment
inventory. G3's historical PREP plan is immutable, not an execution authorization.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import re
import subprocess

from safeshift.protocol.firewall import external_path
from safeshift.protocol.grounding_multicategory_candidate import (
    VERSION, prompt, parse_qwen3_multicategory, parse_paligemma_multicategory,
)
from safeshift.protocol.grounding_multicategory_geometry import observe, systematic_tracking

BASE = "b3bf4dc770c1b87a9e353a75aab759f67641c2c2"
ROOT = Path(__file__).resolve().parents[2]
PLAN = "configs/pre_freeze/grounding_interface_qualification_plan.v3.json"
MANIFEST = "configs/pre_freeze/external_grounding_interface_cases.v3.json"
LOCK = "configs/pre_freeze/grounding_interface_lock.v3.json"
RUNTIME_LOCK = "configs/pre_freeze/grounding_multicategory_runtime_lock.v2.json"
EXECUTION_PLAN = "configs/pre_freeze/grounding_multicategory_execution_plan.v1.json"
ENV_TEMPLATE = "configs/pre_freeze/grounding_multicategory_environment.v1.json"
RUNNER = "safeshift/runners/grounding_multicategory_v3.py"
PARSER = "safeshift/protocol/grounding_multicategory_candidate.py"
RUN_ROOT = "data/processed/external_grounding_multicategory_v3/runs"
MODELS = {
    "qwen3": ("Qwen/Qwen3-VL-8B-Instruct", "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"),
    "paligemma": ("google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1"),
}
DECODING = dict(do_sample=False, num_beams=1, num_return_sequences=1, max_new_tokens=512)
PARSERS = {"qwen3": parse_qwen3_multicategory, "paligemma": parse_paligemma_multicategory}
RUN_IDS = {"qwen3": "g5-qwen3-v3-001", "paligemma": "g5-paligemma-v3-001"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encode(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False).encode("utf-8")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def text_hash(path):
    # Same Git-normalized representation as G3; raw artifacts NEVER normalize.
    return sha(Path(path).read_bytes().replace(b"\r\n", b"\n"))


def read_json(path):
    return json.loads(Path(path).read_bytes())


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def frozen(repo=ROOT):
    lock = read_json(repo / RUNTIME_LOCK)
    for name, expected in lock["sha256"].items():
        require(text_hash(external_path(repo, name)) == expected, "FROZEN_HASH: " + name)
    execution = read_json(repo / EXECUTION_PLAN)
    require(lock["base_sha"] == execution["execution_base"] == BASE
            and execution["run_ids"] == RUN_IDS, "EXECUTION_PLAN_IDENTITY")
    old = read_json(repo / LOCK)
    for name, expected in old["sha256"].items():
        require(text_hash(external_path(repo, name)) == expected, "G3_HASH: " + name)
    # Working-tree bytes, not just HEAD, must preserve the historical contracts.
    for name, expected in old["historical_git_blobs"].items():
        raw = external_path(repo, name).read_bytes()
        if not name.endswith(".png"):
            raw = raw.replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        require(blob == expected, "HISTORICAL_BLOB: " + name)
    plan, manifest = read_json(repo / PLAN), read_json(repo / MANIFEST)
    require(plan["execution_authorized"] is False and plan["QUALIFICATION_EXECUTION"] == "NOT_RUN",
            "G3_PREP_AUTHORITY_CHANGED")
    require(len(manifest["cases"]) == plan["required_calls_per_model"] == 12, "TWELVE_CASES")
    require([c["case_id"] for c in manifest["cases"]] == plan["case_ids"], "CASE_IDENTITIES")
    require(manifest["source_kind"] == "synthetic", "SYNTHETIC_ONLY")
    for case in manifest["cases"]:
        require(case["query_labels"] == plan["query_labels"] == manifest["query_labels"], "SAME_QUERY")
        require(bool(case["targets"]), "POSITIVE_ONLY")
        require(case["expected_counts"] == {label: sum(t["label"] == label for t in case["targets"])
                                           for label in plan["query_labels"]}, "EXACT_COUNTS")
        path = external_path(repo, case["image_path"])
        require(path == external_path(repo, f"data/processed/external_grounding_multicategory_v3/images/{case['case_id']}.png"),
                "FROZEN_SYNTHETIC_PATH")
    for key, identity in MODELS.items():
        spec = plan["models"][key]
        require((spec["model_id"], spec["immutable_revision"]) == identity, "MODEL_IDENTITY")
        require(spec["decoding"] == DECODING, "FIXED_512_GREEDY")
    return plan, manifest, lock


def run_path(repo, run_id):
    require(type(run_id) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id), "RUN_ID")
    path = external_path(repo, f"{RUN_ROOT}/{run_id}")
    require(not path.exists(), "NEW_EXECUTION_DIRECTORY_REQUIRED")
    return path


def write_bytes(path, raw):
    """Exclusive durable write; caller must reread before interpretation."""
    with path.open("xb") as stream:
        require(stream.write(raw) == len(raw), "SHORT_WRITE")
        stream.flush()
        os.fsync(stream.fileno())
    return {"sha256": sha(raw), "size_bytes": len(raw)}


def verified_read(path, receipt):
    raw = path.read_bytes()
    require(len(raw) == receipt["size_bytes"] and sha(raw) == receipt["sha256"], "STORAGE_HASH_OR_SIZE")
    return raw


def inventory_snapshot(repo, model_key, snapshot_name):
    """No download. Record all processor/tokenizer/model bytes for external review."""
    snapshot = external_path(repo, snapshot_name)
    model_id, revision = MODELS[model_key]
    require(snapshot.name == revision and snapshot.parent.name == "snapshots"
            and snapshot.parent.parent.name == "models--" + model_id.replace("/", "--"), "PINNED_SNAPSHOT_PATH")
    if model_key == "paligemma":
        from .paligemma_snapshot import verify_snapshot
        verify_snapshot(snapshot, repo=repo)
    else:
        from scripts.provision_qwen3vl_snapshot import verify_weights, weight_files
        require(verify_weights(snapshot, weight_files(repo))["LOCAL_WEIGHT_BYTES_VERIFIED"], "QWEN_WEIGHT_HASH")
    files = {}
    for path in sorted(snapshot.rglob("*")):
        if path.is_dir():
            continue
        resolved = path.resolve()
        require(resolved.is_relative_to(snapshot.parent.parent.resolve()), "SNAPSHOT_ESCAPE")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        files[path.relative_to(snapshot).as_posix()] = {"sha256": digest.hexdigest(), "size_bytes": path.stat().st_size}
    needed = {"config.json", "generation_config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json"}
    if model_key == "qwen3":
        needed.add("chat_template.json")
    require(needed <= files.keys(), "PROCESSOR_TOKENIZER_INVENTORY")
    return files


def execution_identity(repo):
    """G5 must remain an unmerged, clean descendant of the fixed execution BASE."""
    head = git(repo, "rev-parse", "HEAD")
    require(git(repo, "rev-parse", "origin/main") == BASE, "MAIN_IDENTITY_CHANGED_RESEARCH_LEAD_REQUIRED")
    require(head != BASE and git(repo, "merge-base", BASE, head) == BASE, "HEAD_NOT_DESCENDED_FROM_BASE")
    return head


def inspect_environment(repo, model_key, snapshot_name):
    """Future operator inventory only. Never called by --dry-run or G4 tests."""
    plan, _, lock = frozen(repo)
    head = execution_identity(repo)
    require(not git(repo, "status", "--porcelain", "--untracked-files=all"), "CLEAN_EXECUTION_CHECKOUT_REQUIRED")
    import torch
    versions = {name: importlib.metadata.version(name) for name in
                ("torch", "transformers", "tokenizers", "Pillow", "accelerate", "huggingface-hub", "safetensors")}
    versions["python"] = platform.python_version()
    hardware = [{"name": torch.cuda.get_device_name(i),
                 "compute_capability": list(torch.cuda.get_device_capability(i))}
                for i in range(torch.cuda.device_count())]
    require(len(hardware) == (2 if model_key == "qwen3" else 1)
            and all("T4" in g["name"] and g["compute_capability"] == [7, 5] for g in hardware), "T4_HARDWARE")
    require(versions["transformers"] == "4.57.1", "AUDITED_TRANSFORMERS_REQUIRED")
    return {"schema_version": "grounding-v3-environment-observation-v1", "model_key": model_key,
            "model_id": MODELS[model_key][0], "revision": MODELS[model_key][1],
            "processor_revision": MODELS[model_key][1], "tokenizer_revision": MODELS[model_key][1],
            "software_versions": versions, "cuda": torch.version.cuda, "hardware": hardware,
            "snapshot": snapshot_name, "snapshot_files": inventory_snapshot(repo, model_key, snapshot_name),
            "code_and_contract_hashes": lock["sha256"], "generation_config": plan["models"][model_key]["decoding"],
            "git_commit": head, "main_sha": BASE, "run_id": RUN_IDS[model_key], "observed": True,
            "runtime_lock_sha256": text_hash(repo / RUNTIME_LOCK),
            "execution_authorized": False, "QUALIFICATION_EXECUTION": "NOT_RUN"}


def preflight(repo, model_key, run_id, environment=None, authority=None, *, images=True):
    """Static preflight checks authority without touching torch/GPU/model/cache."""
    plan, manifest, lock = frozen(repo)
    output = run_path(repo, run_id)
    head = execution_identity(repo)
    if images:
        for case in manifest["cases"]:
            raw = external_path(repo, case["image_path"]).read_bytes()
            require(sha(raw) == case["image_sha256"] and len(raw) == case["image_size_bytes"], "IMAGE_HASH")
    blockers = []
    if environment is None or authority is None:
        blockers.append("EXTERNAL_ENVIRONMENT_AND_EXECUTION_APPROVAL_REQUIRED")
    else:
        require(run_id == RUN_IDS[model_key], "PREDECLARED_RUN_ID_REQUIRED")
        validate_environment(environment, model_key)
        require(authority.get("execution_authorized") is True, "EXECUTION_NOT_AUTHORIZED")
        require(authority.get("model_key") == model_key and authority.get("run_id") == run_id, "AUTHORITY_SCOPE")
        require(authority.get("head_sha") == head and authority.get("main_sha") == BASE, "AUTHORITY_GIT_IDENTITY")
        require(authority.get("environment_sha256") == sha(encode(environment)), "APPROVED_ENVIRONMENT_HASH")
        require(authority.get("runtime_lock_sha256") == text_hash(repo / RUNTIME_LOCK), "APPROVED_RUNTIME_LOCK")
        require(authority.get("internet_off_attested") is True, "VENUE_OFFLINE_ATTESTATION")
        for field in ("research_lead", "independent_auditor", "review_reference"):
            require(type(authority.get(field)) is str and bool(authority[field].strip()), "EXTERNAL_REVIEW_REQUIRED")
        require(authority["research_lead"].strip().casefold() != authority["independent_auditor"].strip().casefold(),
                "INDEPENDENT_REVIEW_REQUIRED")
        require(environment.get("observed") is True and environment.get("git_commit") == head, "ENVIRONMENT_UNVERIFIED")
        require(environment.get("model_key") == model_key and environment.get("model_id") == MODELS[model_key][0]
                and environment.get("revision") == MODELS[model_key][1], "ENVIRONMENT_MODEL")
        require(environment.get("code_and_contract_hashes") == lock["sha256"]
                and environment.get("generation_config") == DECODING, "ENVIRONMENT_CONTRACT")
        require(not git(repo, "status", "--porcelain", "--untracked-files=all"), "CLEAN_EXECUTION_CHECKOUT_REQUIRED")
    return {"status": "BLOCKED" if blockers else "PREFLIGHT_PASS", "blockers": blockers,
            "QUALIFICATION_EXECUTION": "NOT_RUN", "execution_authorized": not blockers,
            "head_sha": head, "main_sha": BASE, "output": output.relative_to(repo.resolve()).as_posix(),
            "required_calls": 12, "prompt": prompt(model_key, plan["query_labels"]), "decoding": DECODING}


def validate_environment(environment, model_key):
    require(environment.get("schema_version") == "grounding-v3-environment-observation-v1", "ENVIRONMENT_SCHEMA")
    for field in ("processor_revision", "tokenizer_revision", "revision"):
        require(environment.get(field) == MODELS[model_key][1], "ENVIRONMENT_REVISION")
    versions = environment.get("software_versions", {})
    for name in ("python", "torch", "transformers", "tokenizers", "Pillow", "accelerate", "huggingface-hub", "safetensors"):
        require(type(versions.get(name)) is str and bool(versions[name]), "ENVIRONMENT_VERSION: " + name)
    require(versions["transformers"] == "4.57.1" and type(environment.get("cuda")) is str
            and bool(environment["cuda"]), "AUDITED_CUDA_TRANSFORMERS")
    hardware = environment.get("hardware", [])
    require(len(hardware) == (2 if model_key == "qwen3" else 1)
            and all("T4" in g.get("name", "") and g.get("compute_capability") == [7, 5] for g in hardware), "ENVIRONMENT_HARDWARE")
    files = environment.get("snapshot_files", {})
    require({"config.json", "generation_config.json", "preprocessor_config.json", "tokenizer.json", "tokenizer_config.json"} <= files.keys(), "ENVIRONMENT_SNAPSHOT_HASHES")
    for name, entry in files.items():
        require(type(entry.get("sha256")) is str and re.fullmatch("[0-9a-f]{64}", entry["sha256"])
                and type(entry.get("size_bytes")) is int and entry["size_bytes"] > 0, "ENVIRONMENT_SNAPSHOT_HASH")


class NativeRuntime:
    """One load, one native generate per case, no retries or adaptive prompts."""

    def __init__(self, repo, model_key, environment):
        self.repo, self.key, self.environment = repo, model_key, environment
        self.count = 0

    def load(self):
        import torch
        from transformers import AutoProcessor, PaliGemmaForConditionalGeneration, Qwen3VLForConditionalGeneration
        self.torch = torch
        path = external_path(self.repo, self.environment["snapshot"])
        kwargs = dict(revision=MODELS[self.key][1], local_files_only=True, trust_remote_code=False)
        self.processor = AutoProcessor.from_pretrained(str(path), **kwargs)
        factory = Qwen3VLForConditionalGeneration if self.key == "qwen3" else PaliGemmaForConditionalGeneration
        extra = {"device_map": "auto"} if self.key == "qwen3" else {}
        self.model, info = factory.from_pretrained(str(path), **kwargs, **extra, dtype=torch.float16,
                                                  attn_implementation="sdpa", use_safetensors=True,
                                                  output_loading_info=True)
        require(not any(info.get(k) for k in ("missing_keys", "unexpected_keys", "mismatched_keys", "error_msgs")), "WEIGHT_KEYS")
        if self.key == "paligemma":
            self.model.to("cuda:0")
            ip = self.processor.image_processor
            require(type(self.processor).__name__ == "PaliGemmaProcessor"
                    and type(self.processor.tokenizer).__name__ == "GemmaTokenizerFast"
                    and type(ip).__name__ == "SiglipImageProcessor"
                    and ip.size == {"height": 448, "width": 448}, "PINNED_PALI_PROCESSOR")
        else:
            require(type(self.processor).__name__ == "Qwen3VLProcessor" and hasattr(self.model.model, "rope_deltas"), "QWEN_PROCESSOR_STATE")
        require(all(p.device.type == "cuda" and p.dtype == torch.float16 for p in self.model.parameters()), "NO_OFFLOAD_FP16_ONLY")
        self.model.eval()
        self.config = deepcopy(self.model.generation_config)
        # Operational output/cache controls do not change G3's greedy token budget.
        self.config.update(**DECODING, use_cache=False, return_dict_in_generate=False,
                           output_scores=False, output_logits=False, output_attentions=False, output_hidden_states=False)
        self.effective = self.config.to_dict()
        eos = self.config.eos_token_id
        self.eos_ids = [eos] if type(eos) is int else eos
        require(bool(self.eos_ids) and all(type(x) is int for x in self.eos_ids), "PINNED_EOS_REQUIRED")

    def generate(self, image_bytes, text):
        from PIL import Image
        evidence = {}
        try:
            with Image.open(BytesIO(image_bytes)) as image:
                require(image.mode == "RGB" and image.size == (256, 256), "FROZEN_RGB_IMAGE")
                if self.key == "qwen3":
                    self.model.model.rope_deltas = None
                    if hasattr(self.model, "_cache"):
                        self.model._cache = None
                    messages = [{"role": "user", "content": [{"type": "image", "image": image}, {"type": "text", "text": text}]}]
                    inputs = self.processor.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                                                return_dict=True, return_tensors="pt").to(self.model.device)
                else:
                    require("\n" not in text, "PROCESSOR_OWNS_NEWLINE")
                    inputs = self.processor(text=text, images=image, return_tensors="pt").to("cuda:0", dtype=self.torch.float16)
            rows = inputs["input_ids"].tolist()
            require(len(rows) == 1 and bool(rows[0]) and "past_key_values" not in inputs, "BATCH_ONE_INDEPENDENT_INPUT")
            prefix = rows[0]
            if self.key == "paligemma":
                decoded_prefix = self.processor.decode(prefix, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                require(decoded_prefix == text + "\n", "EXACT_PROCESSOR_NEWLINE")
                processed_size = [448, 448]
                require(list(inputs["pixel_values"].shape) == [1, 3, 448, 448], "PALI_IMAGE_SHAPE")
                grid = None
            else:
                grid = inputs["image_grid_thw"].tolist()
                require(len(grid) == 1 and len(grid[0]) == 3
                        and self.processor.image_processor.patch_size == 16, "QWEN_IMAGE_GRID")
                processed_size = [grid[0][1] * 16, grid[0][2] * 16]
            evidence.update(input_token_ids=prefix, effective_generation_config=self.effective,
                            eos_token_ids=self.eos_ids, processed_image_size=processed_size,
                            pixel_values_shape=list(inputs["pixel_values"].shape), image_grid_thw=grid)
            self.count += 1
            extra = {"logits_to_keep": 1} if self.key == "paligemma" else {}
            with self.torch.inference_mode():
                generated = self.model.generate(**inputs, generation_config=deepcopy(self.config), **extra)
            evidence["generated_rows"] = generated.tolist()
            require(len(evidence["generated_rows"]) == 1, "ONE_GENERATED_ROW")
            full = evidence["generated_rows"][0]
            evidence["generated_ids_full"] = full
            require(full[:len(prefix)] == prefix, "TOKEN_BOUNDARY")
            continuation = full[len(prefix):]
            evidence["continuation_ids"] = continuation
            evidence["decoded_with_special_tokens"] = self.processor.decode(continuation, skip_special_tokens=False, clean_up_tokenization_spaces=False)
            evidence["parser_decode"] = self.processor.decode(continuation, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            evidence["termination_reason"] = "EOS" if continuation and continuation[-1] in self.eos_ids else "NO_EOS_OR_TRUNCATION"
            evidence["native_ok"] = True
        except Exception as exc:
            evidence.update(native_ok=False, failure_type=type(exc).__name__)
        finally:
            if self.key == "qwen3":
                self.model.model.rope_deltas = None
                if hasattr(self.model, "_cache"):
                    self.model._cache = None
        return encode(evidence)


def validate_continuation(raw):
    require(raw.get("native_ok") is True, "NATIVE_GENERATION_FAILURE")
    prefix, full, tail = (raw[k] for k in ("input_token_ids", "generated_ids_full", "continuation_ids"))
    require(all(type(ids) is list and all(type(v) is int and v >= 0 for v in ids) for ids in (prefix, full, tail)), "TOKEN_IDS")
    require(prefix and full == prefix + tail and 1 <= len(tail) <= 512, "TOKEN_BOUNDARY")
    require(type(raw["parser_decode"]) is str and type(raw["decoded_with_special_tokens"]) is str, "DECODE_TEXT")
    require(all(raw["effective_generation_config"].get(k) == v for k, v in DECODING.items()), "GENERATION_CONFIG_CHANGED")
    require(raw["termination_reason"] == "EOS" and tail[-1] in raw["eos_token_ids"]
            and not any(v in raw["eos_token_ids"] for v in tail[:-1]), "EOS_REQUIRED_NO_TRUNCATION")


def persist_then_parse(directory, raw_bytes, metadata, model_key, labels):
    """The only route into a candidate parser: verified reread raw + metadata."""
    directory.mkdir()
    raw_receipt = write_bytes(directory / "raw.json", raw_bytes)
    meta = {**metadata, "raw_sha256": raw_receipt["sha256"], "raw_size_bytes": raw_receipt["size_bytes"],
            "parse_status": "NOT_ATTEMPTED", "canonical_detections": None}
    meta_receipt = write_bytes(directory / "preparse.json", encode(meta))
    persisted = verified_read(directory / "raw.json", raw_receipt)
    reread_meta = json.loads(verified_read(directory / "preparse.json", meta_receipt))
    require(reread_meta == meta, "PREPARSE_METADATA_CHANGED")
    envelope = json.loads(persisted)
    validate_continuation(envelope)
    parsed = PARSERS[model_key](envelope["parser_decode"], labels)
    return parsed, envelope, {"raw.json": raw_receipt, "preparse.json": meta_receipt}


def review_template(calls):
    return [{"case_id": call["case_id"], "detection_index": i, "detection": detection,
             "raw_sha256": call["raw_hashes"]["raw.json"]["sha256"],
             "image_path": f"data/processed/external_grounding_multicategory_v3/images/{call['case_id']}.png",
             "reviewer": None, "rationale": None, "decision": None}
            for call in calls for i, detection in enumerate(call["canonical_detections"] or [])]


def verdict(result, cases, reviews):
    """No partial PASS and no automatic NO_GIANT; review identity includes raw hash."""
    if result["QUALIFICATION_EXECUTION"] == "NOT_RUN":
        return "BLOCKED"
    calls = result["calls"]
    if (result.get("failure") or not result.get("artifact_audit_complete")
            or result.get("native_calls") != 12 or result.get("model_loads") != 1
            or [c["case_id"] for c in calls] != [c["case_id"] for c in cases]
            or any(c["parse_status"] != "SUCCESS" or not c["geometry_observations"]["geometry_ok"] for c in calls)
            or not result["tracking_result"]):
        return "FAIL"
    expected = review_template(calls)
    identities = [(r["case_id"], r["detection_index"]) for r in reviews]
    if len(identities) != len(set(identities)):
        return "FAIL"
    by_id = dict(zip(identities, reviews))
    if set(by_id) - {(r["case_id"], r["detection_index"]) for r in expected}:
        return "FAIL"
    pending = False
    for row in expected:
        review = by_id.get((row["case_id"], row["detection_index"]))
        if review is None:
            pending = True
            continue
        if any(review.get(k) != row[k] for k in ("detection", "raw_sha256")):
            return "FAIL"
        if review.get("decision") == "GIANT":
            return "FAIL"
        if review.get("decision") not in (None, "NO_GIANT"):
            return "FAIL"
        if (review.get("decision") is None or not all(type(review.get(k)) is str and review[k].strip()
                                                      for k in ("reviewer", "rationale"))):
            pending = True
    return "PENDING_REVIEW" if pending else "PASS"


def run_calls(repo, model_key, run_id, environment, runtime, command, authority=None):
    """Internal lifecycle, injectable for offline tests; public execution uses execute()."""
    plan, manifest, _ = frozen(repo)
    cases = manifest["cases"]
    output = run_path(repo, run_id)
    output.mkdir(parents=True, exist_ok=False)
    hashes = {}
    result = {"schema_version": "grounding-v3-result-v1", "RUN_ID": run_id,
              "MODEL_ID": MODELS[model_key][0], "REVISION": MODELS[model_key][1],
              "ENVIRONMENT": environment, "QUALIFICATION_EXECUTION": "NOT_RUN",
              "calls": [], "model_loads": 0, "native_calls": 0, "failure": None,
              "tracking_result": None, "NO_GIANT_review_status": "NOT_RUN",
              "artifact_audit_complete": False, "final_verdict": "BLOCKED"}
    try:
        hashes["environment.json"] = write_bytes(output / "environment.json", encode(environment))
        if authority is not None:
            hashes["authorization.json"] = write_bytes(output / "authorization.json", encode(authority))
        runtime.load()
        result["model_loads"] = 1
        fixed_prompt = prompt(model_key, plan["query_labels"])
        for case in cases:
            # No GT/expected counts/case identity passed into the native runtime.
            image_bytes = external_path(repo, case["image_path"]).read_bytes()
            require(sha(image_bytes) == case["image_sha256"], "INPUT_CHANGED")
            result["QUALIFICATION_EXECUTION"] = "EXECUTED"
            raw = runtime.generate(image_bytes, fixed_prompt)
            result["native_calls"] = runtime.count
            spec = plan["models"][model_key]
            meta = {"run_id": run_id, "case_id": case["case_id"], "sample_id": case["case_id"],
                    "call_id": case["case_id"], "logical_call_id": case["case_id"],
                    "model_id": spec["model_id"], "immutable_revision": spec["immutable_revision"],
                    "prompt_id": spec["prompt_id"], "prompt_version": spec["prompt_id"], "prompt_text": fixed_prompt,
                    "prompt_sha256": sha(fixed_prompt.encode()), "query_labels": plan["query_labels"],
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(), "input_image_sha256": case["image_sha256"],
                    "input_image_path": case["image_path"], "original_image_size": [256, 256],
                    "preprocessing": spec["preprocessing"], "precision": "FP16", "quantization": "NONE",
                    "decoding": DECODING, "seed": None, "parser_version": VERSION,
                    "parser_input_field": "parser_decode", "parser_sha256": text_hash(repo / PARSER),
                    "plan_sha256": text_hash(repo / PLAN), "manifest_sha256": text_hash(repo / MANIFEST),
                    "source_audit_sha256": text_hash(repo / plan["sources"]), "lock_sha256": text_hash(repo / LOCK),
                    "git_commit": environment["git_commit"], "command": command,
                    "software_versions": environment["software_versions"], "hardware": environment["hardware"],
                    "raw_path": f"{RUN_ROOT}/{run_id}/{case['case_id']}/raw.json"}
            parsed, envelope, receipts = persist_then_parse(output / case["case_id"], raw, meta, model_key, plan["query_labels"])
            row = {"case_id": case["case_id"], "raw_hashes": receipts, "parse_status": parsed.status,
                   "canonical_detections": None if parsed.detections is None else
                   [{"bbox": list(d.bbox), "label": d.label} for d in parsed.detections],
                   "geometry_observations": observe(case, parsed), "termination_reason": envelope["termination_reason"],
                   "raw_token_count": len(envelope["continuation_ids"])}
            for name, receipt in receipts.items():
                hashes[f"{case['case_id']}/{name}"] = receipt
            hashes[f"{case['case_id']}/parsed.json"] = write_bytes(output / case["case_id"] / "parsed.json", encode(row))
            result["calls"].append(row)
        result["tracking_result"] = systematic_tracking(cases, {c["case_id"]: c["geometry_observations"] for c in result["calls"]})
        hashes["human_review.template.json"] = write_bytes(output / "human_review.template.json", encode(review_template(result["calls"])))
        for name, receipt in hashes.items():
            verified_read(output / name, receipt)
        result["artifact_audit_complete"] = True
        result["NO_GIANT_review_status"] = "PENDING_HUMAN_REVIEW"
    except Exception as exc:
        result["failure"] = {"type": type(exc).__name__,
                             "reason": str(exc) if isinstance(exc, ValueError) else type(exc).__name__}
    result["final_verdict"] = verdict(result, cases, [])
    validate_result(result)
    hashes["result.json"] = write_bytes(output / "result.json", encode(result))
    verified_read(output / "result.json", hashes["result.json"])
    receipt = write_bytes(output / "artifact_index.json", encode(hashes))
    verified_read(output / "artifact_index.json", receipt)
    return result


def execute(repo, model_key, run_id, environment, authority, command):
    check = preflight(repo, model_key, run_id, environment, authority)
    require(check["status"] == "PREFLIGHT_PASS", "EXECUTION_BLOCKED")
    from .paligemma_snapshot import require_offline_env, network_denied
    require_offline_env()
    with network_denied():
        # Re-observe exact versions, GPU and every snapshot byte BEFORE model load.
        actual = inspect_environment(repo, model_key, environment["snapshot"])
        require(actual == environment, "LIVE_ENVIRONMENT_DIFFERS_FROM_REVIEWED_LOCK")
        return run_calls(repo, model_key, run_id, environment,
                         NativeRuntime(repo, model_key, environment), command, authority)


def validate_result(result):
    required = {"schema_version", "RUN_ID", "MODEL_ID", "REVISION", "ENVIRONMENT", "QUALIFICATION_EXECUTION",
                "calls", "model_loads", "native_calls", "failure", "tracking_result", "NO_GIANT_review_status",
                "artifact_audit_complete", "final_verdict"}
    require(set(result) == required and result["schema_version"] == "grounding-v3-result-v1", "RESULT_SCHEMA")
    require(result["final_verdict"] in {"BLOCKED", "FAIL", "PENDING_REVIEW", "PASS"}, "FINAL_VERDICT_ENUM")
    require(result["QUALIFICATION_EXECUTION"] in {"NOT_RUN", "EXECUTED"}, "RESULT_EXECUTION_STATUS")
    require(0 <= len(result["calls"]) <= result["native_calls"] <= 12, "RESULT_CALL_COUNTS")
    # Runtime writer has no human reviews. PASS is exclusively an offline reviewed decision.
    require(result["final_verdict"] != "PASS", "RUNTIME_CANNOT_AUTO_AWARD_PASS")
    for call in result["calls"]:
        require(set(call) == {"case_id", "raw_hashes", "parse_status", "canonical_detections",
                             "geometry_observations", "termination_reason", "raw_token_count"}, "CALL_SCHEMA")
        require(call["parse_status"] in {"SUCCESS", "INVALID", "POSITIVE_GUARANTEE_MISS"}, "PARSE_STATUS")
        require((call["canonical_detections"] is None) == (call["parse_status"] != "SUCCESS"), "CANONICAL_NULL_ON_FAILURE")


def finalize(repo, model_key, run_id, reviews):
    """Offline, append-only finalization; original runtime result is never overwritten."""
    output = external_path(repo, f"{RUN_ROOT}/{run_id}")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run_id), "RUN_ID")
    _, manifest, _ = frozen(repo)
    index = read_json(output / "artifact_index.json")
    for name, receipt in index.items():
        path = external_path(repo, f"{RUN_ROOT}/{run_id}/{name}")
        require(path.is_relative_to(output), "ARTIFACT_ESCAPE")
        verified_read(path, receipt)
    result = json.loads(verified_read(output / "result.json", index["result.json"]))
    validate_result(result)
    require((result["MODEL_ID"], result["REVISION"]) == MODELS[model_key]
            and result["RUN_ID"] == run_id, "REVIEW_RUN_MODEL_IDENTITY")
    decision = {"RUN_ID": run_id, "runtime_result_sha256": index["result.json"]["sha256"],
                "reviews": reviews, "final_verdict": verdict(result, manifest["cases"], reviews),
                "promotion": False}
    receipt = write_bytes(output / "human_review.final.json", encode(decision))
    verified_read(output / "human_review.final.json", receipt)
    return decision
