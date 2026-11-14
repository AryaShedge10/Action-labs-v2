"""Evidence alignment scoring. This is not clinical correctness."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ..schemas.team_b import Claim, Transcript, TranscriptSegment
from ..validators.conflicts import Conflict, run_conflict_engine
from ..schemas.team_b import Patient


@dataclass
class ClaimValidation:
    claim_id: str
    text: str
    section: str
    citations: list[str]
    evidence_ids: list[str]
    status: str
    origin: str
    deleted: bool

    def to_dict(self) -> dict:
        return asdict(self)


def resolve_segment(transcript: Transcript, segment_id: str) -> TranscriptSegment | None:
    for segment in transcript.segments:
        if segment.id == segment_id:
            return segment
    return None


def claim_is_grounded(claim: Claim, transcript: Transcript) -> bool:
    if not claim.citations:
        return False
    return all(resolve_segment(transcript, citation) is not None for citation in claim.citations)


def evaluate_claims(
    claims: list[Claim],
    transcript: Transcript,
    conflicts: list[Conflict],
) -> list[ClaimValidation]:
    conflict_by_claim: dict[str, list[Conflict]] = {}
    for conflict in conflicts:
        if conflict.claim_id:
            conflict_by_claim.setdefault(conflict.claim_id, []).append(conflict)

    results: list[ClaimValidation] = []
    for claim in claims:
        if claim.deleted:
            status = "deleted"
        elif any(item.severity in {"CRITICAL", "HIGH"} for item in conflict_by_claim.get(claim.id, [])):
            status = "conflict"
        elif claim_is_grounded(claim, transcript):
            status = "supported"
        else:
            status = "unsupported"
        if claim.origin == "physician" and status == "supported":
            status = "supported"
        results.append(
            ClaimValidation(
                claim_id=claim.id,
                text=claim.text,
                section=claim.section,
                citations=claim.citations,
                evidence_ids=claim.citations,
                status=status,
                origin=claim.origin,
                deleted=claim.deleted,
            )
        )
    return results


def grounding_summary(claim_results: list[ClaimValidation]) -> dict:
    active = [item for item in claim_results if not item.deleted]
    total = len(active)
    supported = sum(1 for item in active if item.status == "supported")
    unsupported = sum(1 for item in active if not item.citations)
    contradictory = sum(1 for item in active if item.status == "conflict")
    uncertain = sum(1 for item in active if item.status not in {"supported", "unsupported", "conflict"})
    cited = sum(1 for item in active if item.citations)
    grounding = round((supported / total) * 100) if total else 0
    coverage = round((cited / total) * 100) if total else 0
    return {
        "grounding_score": grounding,
        "citation_coverage": coverage,
        "supported_claims": supported,
        "unsupported_claims": unsupported,
        "contradictory_claims": contradictory,
        "uncertain_claims": uncertain,
        "total_claims": total,
        "disclaimer": (
            "Grounding score measures evidence alignment with the supplied transcript. "
            "It is not proof of clinical correctness."
        ),
    }


def validate_encounter(patient: Patient, transcript: Transcript, claims: list[Claim]) -> dict:
    conflicts = run_conflict_engine(patient, transcript, claims)
    claim_results = evaluate_claims(claims, transcript, conflicts)
    summary = grounding_summary(claim_results)
    critical = sum(1 for item in conflicts if item.severity == "CRITICAL" and not item.resolved)
    high = sum(1 for item in conflicts if item.severity == "HIGH" and not item.resolved)
    if critical:
        review_status = "physician_review_required"
        banner = "Physician Review Required"
    elif high or summary["unsupported_claims"]:
        review_status = "physician_review_required"
        banner = "Physician Review Required"
    else:
        review_status = "ready_for_physician_confirmation"
        banner = "Ready for physician confirmation"
    return {
        "summary": summary,
        "conflicts": [item.to_dict() for item in conflicts],
        "claims": [item.to_dict() for item in claim_results],
        "critical_conflicts": critical,
        "high_conflicts": high,
        "review_status": review_status,
        "banner": banner,
    }
