"""D5 consumer contracts and deterministic engine entry point (not frozen).

RQ2 uses image-level Call 1 predictions and authoritative atom membership, never
Call 2 claims. RQ3-A/B remain separate; unsupported atoms are explicit exclusions.
The D9R19 engine preserves D5 Mode A / Mode B, original-polygon pointing/PLC,
E2E failure denominators, and NOT PARTICIPATING semantics.
"""

from dataclasses import dataclass
from typing import Mapping, Protocol

from .schema import BBox, Classification, Grounding, Hazard, HAZARDS, ParseResult, SAFETY_LEVELS

METRIC_ENGINE_VERSION = "d5-engine-d9r19-v1"


class AtomMembershipLookup(Protocol):
    def atoms_for_sample(self, sample_id: str) -> frozenset[str]: ...


class InMemoryAtomMembership:
    """Input is an explicit GT lookup, including empty sets for normal samples."""

    def __init__(self, memberships: Mapping[str, frozenset[str]]):
        self._memberships = {sample: frozenset(atoms) for sample, atoms in memberships.items()}
        if any(not atoms <= set(HAZARDS) for atoms in self._memberships.values()):
            raise ValueError("unknown GT hazard atom")

    def atoms_for_sample(self, sample_id: str) -> frozenset[str]:
        # Missing membership is an error, never silently interpreted as normal.
        return self._memberships[sample_id]


@dataclass(frozen=True)
class OriginalRegion:
    region_id: str
    label: str
    original_polygon: tuple[tuple[float, float], ...]
    derived_bbox: BBox
    coordinate_frame: str  # Explicit original pixels or normalized, with image size.
    image_width: int
    image_height: int


@dataclass(frozen=True)
class GroundTruthAtom:
    atom_id: str
    hazard_type: str
    support: str
    candidate_regions: tuple[OriginalRegion, ...]
    exclusion_reason: str | None = None

    def __post_init__(self):
        if self.hazard_type not in HAZARDS:
            raise ValueError("unknown GT atom")
        if self.support not in ("DIRECT", "WEAK_PROXY", "NO_CURRENT_SPATIAL_GT"):
            raise ValueError("unknown support status")
        if self.support == "NO_CURRENT_SPATIAL_GT":
            if self.candidate_regions or not self.exclusion_reason:
                raise ValueError("unsupported atoms require explicit reason and no spatial GT")
        elif not self.candidate_regions:
            raise ValueError("supported atoms require candidate original regions")
        if self.support == "WEAK_PROXY" and any(r.label != "Person" for r in self.candidate_regions):
            raise ValueError("weak proxy regions must be Person polygons")


@dataclass(frozen=True)
class ClassificationInput:
    sample_id: str
    true_safety_level: str
    domain: str
    point_id: str
    prediction: ParseResult
    rq2_atom_memberships: frozenset[str]

    def __post_init__(self):
        if self.true_safety_level not in SAFETY_LEVELS:
            raise ValueError("unknown GT safety level")
        if not self.rq2_atom_memberships <= set(HAZARDS):
            raise ValueError("unknown RQ2 atom membership")
        if self.prediction.success and not isinstance(self.prediction.value, Classification):
            raise ValueError("classification metrics require Call 1 predictions")


@dataclass(frozen=True)
class SpatialInput:
    sample_id: str
    participation: str
    prediction: ParseResult | None
    direct_atoms: tuple[GroundTruthAtom, ...]
    weak_proxy_atoms: tuple[GroundTruthAtom, ...]
    unsupported_atoms: tuple[GroundTruthAtom, ...]
    classification_correct: bool | None = None
    diagnostic_hazards: tuple[Hazard, ...] = ()

    def __post_init__(self):
        if self.classification_correct is not None and type(self.classification_correct) is not bool:
            raise ValueError("explicit classification correctness required for CGI")
        if self.participation not in ("PARTICIPATING", "NOT PARTICIPATING", "NOT_PARTICIPATING"):
            raise ValueError("unknown grounding participation")
        if self.participation != "PARTICIPATING" and self.prediction is not None:
            raise ValueError("nonparticipants must not receive fabricated grounding results")
        if self.participation == "PARTICIPATING" and self.prediction is None:
            raise ValueError("participants require an explicit parse/missing-response status")
        if self.prediction and self.prediction.success and not isinstance(self.prediction.value, Grounding):
            raise ValueError("spatial prediction must be a grounding result")
        if self.diagnostic_hazards:
            if self.prediction is None or self.prediction.success:
                raise ValueError("diagnostic hazards only supplement a failed response")
            if any(h.hazard_type not in HAZARDS for h in self.diagnostic_hazards):
                raise ValueError("explicit canonical hazard identity required for diagnostics")
            if sum(len(h.evidence) for h in self.diagnostic_hazards) != self.prediction.boxes_valid:
                raise ValueError("diagnostic box count must match parser evidence")
        atom_ids = [atom.atom_id for atom in self.direct_atoms + self.weak_proxy_atoms + self.unsupported_atoms]
        if len(atom_ids) != len(set(atom_ids)):
            raise ValueError("GT atom IDs must be unique across support tracks")
        for atoms, expected in ((self.direct_atoms, "DIRECT"), (self.weak_proxy_atoms, "WEAK_PROXY"),
                                (self.unsupported_atoms, "NO_CURRENT_SPATIAL_GT")):
            if any(atom.support != expected for atom in atoms):
                raise ValueError("do not mix spatial support tracks")


class MetricEngine(Protocol):
    """Consumer interface, implemented by D5MetricEngine; not frozen.

    Consume the complete prediction list including unmatched claims. Never filter
    by GT membership before calculating predicted-box denominators. Preserve
    response-level and box-level parse counts and diagnostic-only valid boxes.
    """

    version: str

    def classification(self, samples: tuple[ClassificationInput, ...]) -> Mapping: ...

    def rq2(self, samples: tuple[ClassificationInput, ...]) -> Mapping: ...

    def direct_grounding(self, samples: tuple[SpatialInput, ...]) -> Mapping: ...

    def weak_proxy(self, samples: tuple[SpatialInput, ...]) -> Mapping: ...


def production_engine():
    from .d5_engine import D5MetricEngine
    return D5MetricEngine()
