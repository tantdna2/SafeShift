"""Reviewed Owner adoption of one numerical configuration for original TRAIN160.

This policy is source-bound, not a notebook permission or a Lead signature.
Review/audit/merge and final-source GPU verification remain release requirements.
"""
from safeshift.pilot.contract import digest
from .source import require

DECISION = "https://github.com/tantdna2/SafeShift/pull/156#issuecomment-6544285481"
IMPLEMENTATION = "minicpm4-resampler-attention-fp32-v1"
CONFIG_SHA256 = "5b85504ff24ff42d4d629dbf00feb0c484022cfef3a7d57b571eaae99d1c8b00"
DESCRIPTOR_SHA256 = "2fe992725df4340f910934b5846278e34968196a9dff3fc4171fb4279bfaf5da"
MANIFEST_SHA256 = "f1ec6a202c3bba05d91cb3c507d5aa16d9aa3ded2418fa84bd62e77c05522995"


def binding(key, implementation):
    from . import train_contract as c
    from .minicpm_resampler_fp32 import descriptor
    require(key == "minicpm4" and implementation == IMPLEMENTATION, "OFFICIAL_FP32_MODEL_IMPLEMENTATION")
    require(descriptor()["implementation_sha256"] == DESCRIPTOR_SHA256, "OFFICIAL_FP32_DESCRIPTOR_DRIFT")
    require(digest(c.config(key, implementation=implementation)) == CONFIG_SHA256,
            "OFFICIAL_FP32_CONFIGURATION_DRIFT")
    require(c.MANIFEST == MANIFEST_SHA256, "OFFICIAL_FP32_MANIFEST_DRIFT")
    return {"schema": "safeshift-owner-minicpm-fp32-train160-adoption-v1",
            "decision_ref": DECISION, "authority": "OWNER_PROJECT_EXPERIMENT_ONLY",
            "scope": "ORIGINAL_TRAIN160_ONLY", "model_key": key,
            "effective_implementation": IMPLEMENTATION,
            "descriptor_sha256": DESCRIPTOR_SHA256, "configuration_sha256": CONFIG_SHA256,
            "manifest_sha256": MANIFEST_SHA256,
            "scientific_selection": "PENDING", "pooling_allowed": False,
            "independent_research_lead_signature": None}


def authorize(value):
    from . import train_contract as c, train_history as history
    expected = binding(value.get("model_key"), value.get("effective_implementation"))
    require(value.get("schema") == history.SCHEMA, "OFFICIAL_FP32_REQUIRES_RECOVERY_SCHEMA")
    require(value.get("official_numerical_approval") == expected, "OFFICIAL_FP32_OWNER_DECISION_BINDING")
    require(value.get("model") == c.model("minicpm4")
            and value.get("candidate_execution_config_sha256") == CONFIG_SHA256
            and value.get("manifest_sha256") == MANIFEST_SHA256
            and value.get("split") == "TRAIN" and value.get("max_initial_ids") == 160
            and value.get("max_native_calls") == 160 and value.get("max_seconds") == 43200
            and not value.get("technical_qualification"), "OFFICIAL_FP32_EXECUTION_SCOPE")
