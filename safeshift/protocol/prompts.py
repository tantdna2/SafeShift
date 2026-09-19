"""Independent request builders; prompt drafts are versioned, not frozen."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .firewall import external_path
from .schema import HAZARDS, SAFETY_LEVELS, Task

PROMPT_VERSIONS = {"classification": "p2-call1-draft-v1", "grounding": "p2-call2-draft-v1",
                   "external_probe": "external-target-draft-v1"}
COORDINATE_INSTRUCTION = "Use [xmin, ymin, xmax, ymax] coordinates in [0,1], origin at the top left."


@dataclass(frozen=True)
class Request:
    task: Task
    image_path: str
    prompt: str
    prompt_version: str

    @property
    def prompt_sha256(self):
        return hashlib.sha256(self.prompt.encode("utf-8")).hexdigest()


def _request(repo: Path, image_path: str, task: Task, prompt: str) -> Request:
    external_path(repo, image_path)
    return Request(task, image_path, prompt, PROMPT_VERSIONS[task])


def classification_request(repo: Path, image_path: str, industry_safety_policy: str) -> Request:
    if not isinstance(industry_safety_policy, str) or not industry_safety_policy.strip():
        raise ValueError("industry safety policy is required; no implicit policy")
    return _request(repo, image_path, "classification",
                    "Classify the image using the supplied industry safety policy. "
                    'Return only a JSON object with the single field "safety_level", one of '
                    + json.dumps(SAFETY_LEVELS) + ".\nIndustry safety policy:\n" + industry_safety_policy)


def grounding_request(repo: Path, image_path: str, vocabulary=HAZARDS) -> Request:
    if tuple(vocabulary) != HAZARDS:
        raise ValueError("Call 2 requires the approved D6 twelve-hazard vocabulary")
    return _request(repo, image_path, "grounding",
                    "Independently inspect the image for observed hazards from this closed vocabulary: "
                    + json.dumps(HAZARDS) + '. Return only {"hazards": [{"hazard_type": "<vocabulary ID>", '
                    '"evidence": [{"bbox": [xmin, ymin, xmax, ymax]}]}]}. '
                    "Use an empty hazards array when no listed hazard is observed. "
                    "Boxes localize visible evidence. " + COORDINATE_INSTRUCTION + " Do not output safety_level.")


def probe_request(repo: Path, image_path: str, target_query: str) -> Request:
    if not isinstance(target_query, str) or not target_query.strip():
        raise ValueError("target query is required")
    return _request(repo, image_path, "external_probe", target_query +
                    '\nReturn only {"bbox": [xmin, ymin, xmax, ymax]} for the target. '
                    + COORDINATE_INSTRUCTION)
