"""Proposed, GT-blind CPU triage of already classified synthetic records.

No inference, raw-output reads, calibration, label changes or efficacy claims.
T0 sections 5-6 supply the proposed operational M/E/C/K policy. Callers own
opaque-ID assignment and upstream HNLO validation; this API verifies neither
scientific qualification nor real-data authority. See docs/ARCHITECTURE.md.
"""

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import asdict, dataclass
import hmac
import math
import re

from safeshift.data.schema import PredictionRecord
from safeshift.data.validation import validate_identifier, validate_safety_level

MODES = ("hnlo_only", "peer_only", "combined")
STATUSES = ("SUCCESS", "INVALID", "TECHNICAL_ERROR", "NOT_ATTEMPTED", "MISSING")
HNLO_STATES = ("VALID", "MISSING", "INELIGIBLE", "MALFORMED")


def _tie(sid: str, key: bytes) -> tuple[bytes, bytes]:
    return (hmac.digest(key, b"safeshift-t2-v1\0" + sid.encode("ascii"), "sha256"),
            hmac.digest(key, b"safeshift-t2-v1-secondary\0" + sid.encode("ascii"), "sha512"))


def _opaque_id(value: str) -> None:
    # Deliberately narrower than historical dataset/file-stem identifiers.
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{32}", value) is None:
        raise ValueError("sample_id must be a preassigned opaque 32-lowercase-hex token")


@dataclass(frozen=True)
class HNLOSignal:
    """Focal score plus caller's upstream eligibility assertion, not calibration.

    None is MISSING; wrong numeric types/nonfinite values are MALFORMED. A
    finite number without eligible=True is INELIGIBLE, never silently used.
    Unusable values remain accounted for but are not exported as JSON numbers.
    """

    value: float | None = None
    eligible: bool = False

    def __post_init__(self):
        if type(self.eligible) is not bool:
            raise ValueError("HNLO eligible must be a bool")

    def snapshot(self) -> dict:
        value = self.value
        if value is None:
            state = "MISSING"
        elif type(value) not in (int, float):
            state = "MALFORMED"
        else:
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            state = "MALFORMED" if not finite else (
                "VALID" if self.eligible else "INELIGIBLE")
        return {"state": state, "value": float(value) if state == "VALID" else None}


@dataclass(frozen=True)
class ClassifiedResult:
    """A minimal parsed result. Missing records are synthesized as MISSING.

    HNLO is accepted on focal results only. No raw payload, GT, filename,
    domain, arbitrary metadata or free-text error message is part of this API.
    """

    sample_id: str
    status: str
    predicted_safety_level: str | None = None
    hnlo: HNLOSignal | None = None

    def __post_init__(self):
        _opaque_id(self.sample_id)
        if self.status not in STATUSES[:-1]:
            raise ValueError("expected SUCCESS, INVALID, TECHNICAL_ERROR or NOT_ATTEMPTED")
        if self.status == "SUCCESS":
            validate_safety_level(self.predicted_safety_level)
        elif self.predicted_safety_level is not None:
            raise ValueError("non-SUCCESS result cannot carry a canonical prediction")
        if self.hnlo is not None and type(self.hnlo) is not HNLOSignal:
            raise ValueError("hnlo must be HNLOSignal or None")

    @classmethod
    def from_prediction(cls, prediction: PredictionRecord,
                        *, hnlo: HNLOSignal | None = None) -> "ClassifiedResult":
        """Project the unchanged Foundation record (None means INVALID)."""
        if type(prediction) is not PredictionRecord:
            raise ValueError("expected PredictionRecord")
        return cls(prediction.sample_id,
                   "INVALID" if prediction.predicted_safety_level is None else "SUCCESS",
                   prediction.predicted_safety_level, hnlo)


@dataclass(frozen=True)
class SourceIdentity:
    """Caller-supplied public identifiers; one selected source/attempt per stream.

    Preserve effective implementation/configuration and series/attempt lineage.
    These strings are references, not verified artifacts or selection authority.
    Never supply credentials/private paths. No field participates in ranking.
    """

    model_id: str
    model_revision: str
    implementation_id: str
    configuration_id: str
    run_id: str
    series_id: str
    attempt_id: str

    def __post_init__(self):
        for field, value in asdict(self).items():
            validate_identifier(value, field)


@dataclass(frozen=True)
class ModelResults:
    identity: SourceIdentity
    records: tuple[ClassifiedResult, ...]

    def __post_init__(self):
        if type(self.identity) is not SourceIdentity:
            raise ValueError("expected SourceIdentity")
        object.__setattr__(self, "records", tuple(self.records))
        if any(type(row) is not ClassifiedResult for row in self.records):
            raise ValueError("expected ClassifiedResult records")


def build_review_queue(
    planned_ids: Iterable[str], focal: ModelResults, peers: Iterable[ModelResults],
    *, mode: str, budget: int, tie_key: bytes,
) -> dict:
    """Return a detached JSON-compatible operational queue for synthetic inputs.

    All arguments governing policy are explicit. HNLO-only needs valid focal
    HNLO; peer-only needs all configured peers; combined needs both. Zero peers
    is supported for HNLO-only, rejected for the two peer-based modes. Focal
    failure is always mandatory. Missing arm-required features are mandatory
    only for valid focal Normal. Focal hazards never enter false-safe ranking.

    Mandatory cases precede ranked cases and share budget K, one slot per ID.
    HNLO descends; peer hazard fraction descends; combined sorts fraction then
    HNLO. HMAC-SHA256 over opaque IDs breaks ties and orders mandatory cases.
    A second domain-separated SHA512 HMAC handles primary digest collisions;
    an unresolved double collision raises instead of depending on input order.
    The caller retains the key externally; neither it nor digests are exported.
    """
    if mode not in MODES:
        raise ValueError("unknown triage mode")
    if type(budget) is not int or budget < 0:
        raise ValueError("budget must be a nonnegative integer")
    if type(tie_key) is not bytes or not tie_key:
        raise ValueError("tie_key must be nonempty caller-supplied bytes")
    if isinstance(planned_ids, (str, bytes)):
        raise ValueError("planned_ids must be an iterable of opaque IDs")
    planned = tuple(planned_ids)
    for sid in planned:
        _opaque_id(sid)
    if len(set(planned)) != len(planned):
        raise ValueError("duplicate planned ID")
    peers = tuple(peers)
    if len(peers) > 2 or any(type(s) is not ModelResults for s in (focal, *peers)):
        raise ValueError("expected focal and at most two peer ModelResults")
    if mode != "hnlo_only" and not peers:
        raise ValueError("peer-based modes require at least one configured peer")
    sources = (focal, *sorted(peers, key=lambda s: s.identity.model_id))
    if len({s.identity.model_id for s in sources}) != len(sources):
        raise ValueError("focal and peers must have distinct model IDs")
    expected = set(planned)
    indices = []
    for position, source in enumerate(sources):
        index = {}
        for row in source.records:
            if row.sample_id not in expected:
                raise ValueError("result ID outside planned cohort")
            if row.sample_id in index:
                raise ValueError("duplicate result ID within model")
            if position and row.hnlo is not None:
                raise ValueError("peer HNLO is not an input signal")
            index[row.sample_id] = row
        indices.append(index)

    ties = {sid: _tie(sid, tie_key) for sid in planned}
    if len(set(ties.values())) != len(planned):
        raise ValueError("tie digest collision; provide another external key")
    ordered_ids = sorted(planned, key=ties.__getitem__)
    counts = [{status: 0 for status in STATUSES} for _ in sources]
    hnlo_counts = {state: 0 for state in HNLO_STATES}
    normal_hnlo_counts = dict(hnlo_counts)
    cases = []
    normal_n = peer_complete_n = 0
    for sid in ordered_ids:
        outputs = []
        for source, index, counter in zip(sources, indices, counts):
            row = index.get(sid)
            status = row.status if row else "MISSING"
            counter[status] += 1
            outputs.append({"model_id": source.identity.model_id, "status": status,
                            "predicted_safety_level": row.predicted_safety_level if row else None})
        row = indices[0].get(sid)
        score = (row.hnlo if row and row.hnlo else HNLOSignal()).snapshot()
        hnlo_counts[score["state"]] += 1
        normal = outputs[0]["predicted_safety_level"] == "Level04"
        peers_complete = bool(peers) and all(o["status"] == "SUCCESS" for o in outputs[1:])
        hazard_votes = sum(o["status"] == "SUCCESS" and
                           o["predicted_safety_level"] != "Level04" for o in outputs[1:])
        disagreement = hazard_votes / len(peers) if peers_complete else None
        reasons = []
        if outputs[0]["status"] != "SUCCESS":
            reasons.append("FOCAL_" + outputs[0]["status"])
        if normal:
            normal_n += 1
            normal_hnlo_counts[score["state"]] += 1
            peer_complete_n += int(peers_complete)
            if mode in ("hnlo_only", "combined") and score["state"] != "VALID":
                reasons.append("FOCAL_HNLO_" + score["state"])
            if mode in ("peer_only", "combined"):
                reasons.extend("PEER_" + o["status"] + ":" + o["model_id"]
                               for o in outputs[1:] if o["status"] != "SUCCESS")
        category = "MANDATORY" if reasons else ("RANKED" if normal else "OUTSIDE_FOCAL_NORMAL")
        if category == "RANKED":
            reasons.append({"hnlo_only": "FOCAL_HNLO_DESCENDING",
                            "peer_only": "PEER_HAZARD_FRACTION_DESCENDING",
                            "combined": "PEER_HAZARD_FRACTION_THEN_FOCAL_HNLO"}[mode])
        elif category == "OUTSIDE_FOCAL_NORMAL":
            reasons.append("FOCAL_HAZARD_NOT_FALSE_SAFE_CANDIDATE")
        case = {"sample_id": sid, "category": category, "outputs": outputs,
                "focal_hnlo": score, "peer_hazard_votes": hazard_votes,
                "peer_count": len(peers), "peer_hazard_fraction": disagreement,
                "reasons": reasons, "selected": False, "review_order": None}
        cases.append(case)
    return {
        "schema_version": "safeshift-triage-v1",
        "data_status": "SYNTHETIC_ONLY", "policy_status": "PROPOSED_NOT_FROZEN",
        "qualification": "NOT_SCIENTIFICALLY_QUALIFIED", "mode": mode,
        "comparison_scope": "OPERATIONAL_ARM_SPECIFIC_ELIGIBILITY",
        "planned_count": len(planned), "focal_normal_count": normal_n,
        "coverage": {
            "models": [{"identity": asdict(s.identity), "denominator": len(planned),
                        "statuses": counter,
                        "valid_fraction": counter["SUCCESS"] / len(planned) if planned else None}
                       for s, counter in zip(sources, counts)],
            "focal_hnlo": {"denominator": len(planned), "states": hnlo_counts},
            "focal_normal_hnlo": {"denominator": normal_n, "states": normal_hnlo_counts},
            "complete_peers_on_focal_normal": {"denominator": normal_n,
                                                "count": peer_complete_n if peers else None}},
        **_allocate(cases, mode, budget, ties),
    }


def _allocate(cases, mode, budget, ties):
    """Allocate detached cases already ordered by keyed ID; no GT access."""
    mandatory = [c for c in cases if c["category"] == "MANDATORY"]
    eligible = [c for c in cases if c["category"] == "RANKED"]

    def priority(case):
        h = case["focal_hnlo"]["value"]
        d = case["peer_hazard_fraction"]
        signal = (-h,) if mode == "hnlo_only" else (
            (-d,) if mode == "peer_only" else (-d, -h))
        return (*signal, ties[case["sample_id"]])

    eligible.sort(key=priority)
    candidates = mandatory + eligible
    selected = candidates[:budget]
    for case in cases:
        case["selected"], case["review_order"] = False, None
    for order, case in enumerate(selected, 1):
        case["selected"], case["review_order"] = True, order
    mandatory_used = min(budget, len(mandatory))
    ranked_used = len(selected) - mandatory_used
    return {
        "eligible_count": len(eligible), "mandatory_count": len(mandatory),
        "budget": budget, "slots_used": len(selected), "slots_unused": budget - len(selected),
        "mandatory_selected_count": mandatory_used, "ranked_selected_count": ranked_used,
        "status": "OVERLOAD" if len(mandatory) > budget else "WITHIN_CAPACITY",
        "backlog": {"mandatory": len(mandatory) - mandatory_used,
                    "ranked": len(eligible) - ranked_used,
                    "total": len(candidates) - len(selected),
                    "sample_ids": [c["sample_id"] for c in candidates[budget:]]},
        "review": [{"sample_id": c["sample_id"], "order": c["review_order"],
                    "category": c["category"], "reasons": list(c["reasons"])} for c in selected],
        "cases": cases,
    }


def compare_review_queues(
    planned_ids: Iterable[str], focal: ModelResults, peers: Iterable[ModelResults],
    *, budget: int, tie_key: bytes,
) -> dict:
    """Compare all three proposed rules without GT, on one planned batch.

    Operational queues retain arm-specific M/E. Signal-control queues use the
    union of mandatory cases and intersection of eligible cases across arms,
    as proposed in T0 section 6. Their artificial common workload is explicitly
    marked, never presented as the operational cost of HNLO-only. Requires
    1-2 peers because all three arms are compared. Does not select a best arm.
    """
    if isinstance(planned_ids, (str, bytes)):
        raise ValueError("planned_ids must be an iterable of opaque IDs")
    planned, peers = tuple(planned_ids), tuple(peers)
    operational = {mode: build_review_queue(planned, focal, peers, mode=mode,
                                            budget=budget, tie_key=tie_key) for mode in MODES}
    mandatory_reasons = {}
    for queue in operational.values():
        for case in queue["cases"]:
            if case["category"] == "MANDATORY":
                mandatory_reasons.setdefault(case["sample_id"], set()).update(case["reasons"])
    common = deepcopy(operational)
    ties = {sid: _tie(sid, tie_key) for sid in planned}
    for mode, queue in common.items():
        queue["comparison_scope"] = "SIGNAL_CONTROL_COMMON_ELIGIBILITY_ARTIFICIAL_WORKLOAD"
        for case in queue["cases"]:
            if case["sample_id"] in mandatory_reasons:
                case["category"] = "MANDATORY"
                case["reasons"] = ["COMMON_MANDATORY:" + reason
                                   for reason in sorted(mandatory_reasons[case["sample_id"]])]
        queue.update(_allocate(queue["cases"], mode, budget, ties))
    return {"operational": operational, "signal_control": common}
