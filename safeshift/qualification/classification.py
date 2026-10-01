"""D9R16 prospective classification contract, independent of the grounding gate."""

from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path

from safeshift.protocol.schema import Classification, SAFETY_LEVELS, fields, parse_text, strict_json
from safeshift.runners.contracts import (
    AdaptedOutput, ErrorCode, ParseStatus, Request, Roles, Task, execute_call,
)
from safeshift.runners.paligemma import VerifiedRawStore
from safeshift.runners.storage import _write_new

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "configs/pre_freeze/classification_qualification_cases.v1.json"
PLAN = "configs/pre_freeze/classification_qualification_plan.v1.json"
SUITE = "external-classification-qualification-v1"
SOURCE_KIND = "EXTERNAL_CLASSIFICATION_QUALIFICATION"
FIXTURES = "tests/fixtures/pre_freeze/classification_qualification_v1"
MARKERS = dict(zip(("RED TRIANGLE", "BLUE DIAMOND", "YELLOW CIRCLE", "GREEN SQUARE"), SAFETY_LEVELS))
POLICY = ("Artificial C1 safety policy: RED TRIANGLE -> Level01; BLUE DIAMOND -> Level02; "
          "YELLOW CIRCLE -> Level03; GREEN SQUARE -> Level04. "
          "There is exactly one policy marker in the image. Ignore gray shapes.")
JSON_PROMPT = (POLICY + '\nReturn only {"safety_level":"Level01"}, with the value replaced by '
               'the applicable one of Level01, Level02, Level03, Level04. '
               'No markdown, explanation or extra fields.')
PALI_PROMPT = ("answer en " + POLICY + " Which safety level applies to the image? "
               "Return exactly one of Level01, Level02, Level03, Level04. No other text.")
MODELS = {
    "qwen3": ("Qwen/Qwen3-VL-8B-Instruct", "0c351dd01ed87e9c1b53cbc748cba10e6187ff3b"),
    "qwen2_5": ("Qwen/Qwen2.5-VL-3B-Instruct", "66285546d2b821cf421d4f5eb2576359d3770cd3"),
    "internvl3": ("OpenGVLab/InternVL3-2B-hf", "cb57a075cb75a2e6d1b668b128d48bb00ae321d2"),
    "moondream": ("vikhyatk/moondream2", "9a7d4024050840e001defacec2b00727e89149e6"),
    "paligemma": ("google/paligemma-3b-mix-448", "ead2d9a35598cb89119af004f5d023b311d1c4a1"),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def same_json(left, right):
    """Compare exact JSON types as well as values (False is not integer zero)."""
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def prompt_for(model):
    if model not in MODELS:
        raise ValueError("UNKNOWN_MODEL")
    return PALI_PROMPT if model == "paligemma" else JSON_PROMPT


def load_suite(repo=ROOT):
    """No free-form paths, labels, policy, or external media accepted."""
    from PIL import Image
    repo = Path(repo).resolve()
    manifest = strict_json((repo / MANIFEST).read_bytes())
    if (manifest["suite"] != SUITE or manifest["version"] != 1
            or manifest["source_kind"] != SOURCE_KIND
            or manifest["NOT_INSPECSAFE"] is not True
            or manifest["NOT_ACCURACY_BENCHMARK"] is not True
            or manifest["policy_text"] != POLICY
            or manifest["policy_sha256"] != digest(POLICY.encode())):
        raise ValueError("SUITE_POLICY_MISMATCH")
    cases = manifest["cases"]
    if [c["case_id"] for c in cases] != [f"cq_{i:02d}" for i in range(1, 9)]:
        raise ValueError("EXACT_EIGHT_ORDERED_CASES_REQUIRED")
    if Counter(c["expected_safety_level"] for c in cases) != Counter(dict.fromkeys(SAFETY_LEVELS, 2)):
        raise ValueError("TWO_CASES_PER_LEVEL_REQUIRED")
    prepared = []
    for case in cases:
        path = f"{FIXTURES}/{case['case_id']}.png"
        if (case["image_path"] != path or (repo / path).resolve() != repo / path
                or MARKERS.get(case["marker"]) != case["expected_safety_level"]):
            raise ValueError("FIXTURE_PATH_OR_MARKER_MISMATCH")
        raw = (repo / path).read_bytes()
        if digest(raw) != case["image_sha256"]:
            raise ValueError("FIXTURE_HASH_MISMATCH")
        with Image.open(BytesIO(raw)) as image:
            image.load()
            if image.format != "PNG" or image.mode != "RGB" or image.size != (256, 256) or image.info:
                raise ValueError("RGB_256_PNG_WITHOUT_METADATA_REQUIRED")
        prepared.append((case, raw))
    return prepared


def _tokens(value):
    if type(value) is not list or not value or any(type(v) is not int or v < 0 for v in value):
        raise ValueError("INVALID_TOKEN_IDS")
    return value


def _hf_text(obj, model):
    from safeshift.runners import internvl3, paligemma
    module = paligemma if model == "paligemma" else internvl3
    required = {"model_id", "revision", "schema_version", "input_token_ids", "input_boundary",
                "decoding", "run_id", "call_id", "generated_ids_full", "continuation_ids",
                "decoded_with_special_tokens", "decoded_text"}
    if model == "paligemma":
        required |= {"hardware", "dtype", "device", "quantization", "generation_kwargs"}
    fields(obj, required)
    if ((obj["model_id"], obj["revision"]) != MODELS[model]
            or obj["schema_version"] != f"{model}-native-output-v1"
            or not same_json(obj["decoding"], module.DECODING)):
        raise ValueError("NATIVE_ENVELOPE_IDENTITY_OR_DECODING")
    prefix, ids = _tokens(obj["input_token_ids"]), _tokens(obj["continuation_ids"])
    if obj["generated_ids_full"] != [prefix + ids] or len(ids) > module.DECODING["max_new_tokens"]:
        raise ValueError("NATIVE_TOKEN_BOUNDARY")
    # Validate the full native row separately: bool must not compare equal to int.
    full = obj["generated_ids_full"]
    if type(full) is not list or len(full) != 1:
        raise ValueError("NATIVE_SINGLE_ROW_REQUIRED")
    _tokens(full[0])
    if any(type(obj[k]) is not str or not obj[k] for k in ("run_id", "call_id")):
        raise ValueError("CALL_IDENTITY_REQUIRED")
    if any(type(obj[k]) is not str for k in ("decoded_text", "decoded_with_special_tokens")):
        raise ValueError("NATIVE_TEXT_REQUIRED")
    boundary = obj["input_boundary"]
    fields(boundary, {"pixel_values_shape", "pixel_values_dtype", "input_ids_dtype", "device",
                      "image_token_count", "input_tokens"})
    token = 257152 if model == "paligemma" else 151667
    shape = boundary["pixel_values_shape"]
    if (boundary["pixel_values_dtype"] != "FP16" or boundary["input_ids_dtype"] != "int64"
            or type(boundary["input_tokens"]) is not int or type(boundary["image_token_count"]) is not int
            or boundary["device"] != "cuda:0" or boundary["input_tokens"] != len(prefix)
            or boundary["image_token_count"] != prefix.count(token)
            or type(shape) is not list or len(shape) != 4 or any(type(v) is not int for v in shape)
            or shape[1:] != [3, 448, 448]
            or type(shape[0]) is not int or not 1 <= shape[0] <= 13
            or prefix.count(token) != (1024 if model == "paligemma" else 256 * shape[0])):
        raise ValueError("NATIVE_IMAGE_BOUNDARY")
    if model == "paligemma":
        hw = obj["hardware"]
        fields(hw, {"gpu_name", "visible_gpu_count", "compute_capability", "total_vram_bytes",
                    "device", "cuda_runtime"})
        if (shape[0] != 1 or obj["dtype"] != "FP16" or obj["device"] != "cuda:0"
                or obj["quantization"] != "NONE" or not same_json(obj["generation_kwargs"], {"logits_to_keep": 1})
                or hw["gpu_name"] not in ("T4", "Tesla T4", "NVIDIA T4")
                or type(hw["visible_gpu_count"]) is not int or hw["visible_gpu_count"] != 1
                or hw["compute_capability"] != [7, 5] or hw["device"] != "cuda:0"
                or hw["cuda_runtime"] != "12.4" or type(hw["total_vram_bytes"]) is not int
                or not 14 * 2**30 <= hw["total_vram_bytes"] <= 16 * 2**30):
            raise ValueError("NATIVE_RUNTIME_CONTRACT")
        if ids[-1] != 1 or 1 in ids[:-1] or obj["decoded_with_special_tokens"] != obj["decoded_text"] + "<eos>":
            raise ValueError("NATIVE_EOS_TEXT_BOUNDARY")
    return obj["decoded_text"]


class CandidateAdapter:
    """Qualification only. No expected level supplied and no repair of any kind."""
    version = "d9r16-classification-candidate-v1"
    parser_version = "d9r16-strict-classification-v1"

    def __init__(self, model, *, run_id=None, call_id=None):
        if model not in MODELS:
            raise ValueError("UNKNOWN_MODEL")
        self.model = model
        self.run_id, self.call_id = run_id, call_id

    def adapt(self, raw, task):
        if task != Task.CLASSIFICATION:
            raise ValueError("ZERO_GROUNDING_CALLS")
        try:
            if type(raw) is not bytes:
                raise ValueError("RAW_BYTES_REQUIRED")
            if self.model in ("qwen3", "qwen2_5"):
                from safeshift.runners.qwen3_vl import Qwen3VLAdapter
                from safeshift.runners.qwen2_5_vl import Qwen2_5VLAdapter
                adapter = Qwen3VLAdapter() if self.model == "qwen3" else Qwen2_5VLAdapter()
                return adapter.adapt(raw, task)
            obj = strict_json(raw)
            if self.model in ("internvl3", "paligemma"):
                for name, expected in (("run_id", self.run_id), ("call_id", self.call_id)):
                    if expected is not None and obj.get(name) != expected:
                        raise ValueError("NATIVE_CALL_IDENTITY_MISMATCH")
            if self.model == "moondream":
                # Exact lossless query envelope; do not deserialize permissive tags/duplicate keys.
                fields(obj, {"schema_version", "native"})
                if obj["schema_version"] != "moondream-native-lossless-v1":
                    raise ValueError("NATIVE_ENVELOPE_VERSION")
                node = obj["native"]
                if (type(node) is not list or len(node) != 2 or node[0] != "dict"
                        or type(node[1]) is not list or len(node[1]) != 1):
                    raise ValueError("EXACT_QUERY_ANSWER_REQUIRED")
                pair = node[1][0]
                if (type(pair) is not list or len(pair) != 2 or pair[0] != ["str", "answer"]
                        or type(pair[1]) is not list or len(pair[1]) != 2
                        or pair[1][0] != "str" or type(pair[1][1]) is not str):
                    raise ValueError("EXACT_QUERY_ANSWER_STRING_REQUIRED")
                text = pair[1][1]
            else:
                text = _hf_text(obj, self.model)
            if self.model == "paligemma":
                if text not in SAFETY_LEVELS:
                    raise ValueError("EXACT_LEVEL_STRING_REQUIRED")
                return AdaptedOutput(ParseStatus.SUCCESS, Classification(text))
            parsed = parse_text(text, "classification")
            return AdaptedOutput(ParseStatus.SUCCESS if parsed.success else ParseStatus.INVALID, parsed.value)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, UnicodeError, RecursionError):
            return AdaptedOutput(ParseStatus.INVALID)


def evaluate(cases, rows, runtime_failure=None):
    """Run verdict cannot write a roster or decide a research role."""
    expected = {case["case_id"]: case["expected_safety_level"] for case, _ in cases}
    reasons = []
    for row in rows:
        if row.get("parse_status") in ("INVALID", "FAILED"):
            reasons.append("INTERFACE_OR_FORMAT_FAILURE")
        elif row.get("parse_status") == "SUCCESS" and row.get("safety_level") != expected.get(row["case_id"]):
            reasons.append("SEMANTIC_CLASSIFICATION_FAILURE")
    complete = (len(rows) == 8 and [r["case_id"] for r in rows] == list(expected)
                and Counter(expected.values()) == Counter(dict.fromkeys(SAFETY_LEVELS, 2))
                and all(r.get("raw_output") and r.get("parse_status") == "SUCCESS" for r in rows))
    status = "FAIL" if reasons else "INCONCLUSIVE" if runtime_failure else "PASS" if complete else "FAIL"
    if runtime_failure:
        reasons.append("INFRASTRUCTURE_OR_RUNTIME_FAILURE")
    if not complete and not reasons:
        reasons.append("INCOMPLETE_EIGHT_CASE_RUN")
    return {"run_status": status, "causes": sorted(set(reasons)),
            "model_role_after_run": "PENDING_RESEARCH_LEAD_REVIEW",
            "review_status": "PENDING_REVIEW", "roster_membership_changed": False,
            "production_adapter_promoted": False, "automatic_rerun": False,
            "runtime_failure": runtime_failure}


def run_suite(runner, context, *, model, repo=ROOT, artifact_root=None):
    """Shared offline execution kernel. CLI owns preflight; fakes exercise this kernel.

    Exclusive per-model directory consumes the attempt even on failure. No rerun
    switch: a separate reviewed task must prepare any subsequent attempt.
    """
    cases = load_suite(repo)
    from .runtime import condition
    decoding, preprocessing, device, versions = condition(model, ROOT)
    if (not same_json(context.decoding, decoding) or not same_json(context.preprocessing, preprocessing)
            or context.device != device or context.software_versions != versions
            or context.precision != "FP16" or context.quantization != "NONE" or context.seed is not None):
        raise ValueError("UNCHANGED_RUNTIME_CONDITION_REQUIRED")
    if ((runner.identity.model_id, runner.identity.immutable_revision) != MODELS[model]
            or context.source_kind != SOURCE_KIND or context.roles != Roles()):
        raise ValueError("QUALIFICATION_IDENTITY_SOURCE_AND_PENDING_ROLES_REQUIRED")
    store = VerifiedRawStore(Path(repo), artifact_root or f"data/processed/classification_qualification_v1/{model}")
    store.root.mkdir(parents=True, exist_ok=False)
    rows, failure = [], None
    try:
        for case, raw in cases:
            current = replace(context, call_id=case["case_id"], input_provenance={
                "suite": SUITE, "image_path": case["image_path"], "image_sha256": case["image_sha256"],
                "policy_sha256": digest(POLICY.encode()), "NOT_INSPECSAFE": True,
                "plan_sha256": digest((ROOT / PLAN).read_bytes()),
                "manifest_sha256": digest((Path(repo) / MANIFEST).read_bytes()),
                "NOT_ACCURACY_BENCHMARK": True})
            request = Request(Task.CLASSIFICATION, case["case_id"], case["case_id"], raw,
                              SUITE + ("/native-answer" if model == "paligemma" else "/strict-json"),
                              prompt_for(model))
            adapter = CandidateAdapter(model, run_id=context.run_id, call_id=case["case_id"])
            result = execute_call(runner, adapter, store, request, current)
            rows.append({"case_id": case["case_id"], "parse_status": result.parse_status.value,
                         "safety_level": result.canonical.safety_level if result.canonical else None,
                         "raw_output": asdict(result.raw_output) if result.raw_output else None,
                         "error": asdict(result.error) if result.error else None})
            store.save_result(result)
            if result.error and result.error.code not in {ErrorCode.INVALID_CLASSIFICATION, ErrorCode.PARSER_FAILURE}:
                failure = asdict(result.error)
                break
    except Exception as exc:
        failure = {"exception_type": type(exc).__name__, "stage": "HARNESS_OR_STORAGE"}
    finally:
        if hasattr(runner, "close"):
            try:
                runner.close()
            except Exception as exc:
                failure = failure or {"exception_type": type(exc).__name__, "stage": "CLOSE"}
    report = {"suite": SUITE, "model": model, "model_id": MODELS[model][0],
              "revision": MODELS[model][1], "run_id": context.run_id,
              "git_commit": context.git_commit_sha, "calls": rows,
              "grounding_calls": 0, "retry_count": 0, "repair_count": 0,
              "protocol_freeze": "PENDING", "inspecsafe_authorized": False,
              "completed_at": datetime.now(timezone.utc).isoformat(), **evaluate(cases, rows, failure)}
    _write_new(store.root / "qualification_result.json", json_bytes(report))
    return report
