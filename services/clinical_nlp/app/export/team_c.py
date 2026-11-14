"""Map Team 2B's `ConsultationAnalysis` onto the payload Team 2C's dashboard ingests (`TeamBPayload`).

Team A supplies no patient registry data, so id/name/age come from optional overrides (e.g. the EHR),
falling back to the consultation id and "Unknown patient". Age is left unset rather than guessed.
"""

from __future__ import annotations

from typing import Any

from ..models.schemas import ConsultationAnalysis

_SPEAKER = {"DOCTOR": "physician", "PATIENT": "patient", "NURSE": "nurse", "UNKNOWN": "unknown"}
_SECTIONS = ("subjective", "objective", "assessment", "plan")


def to_team_c_payload(analysis: ConsultationAnalysis, patient: dict[str, Any] | None = None,
                      physician_id: str | None = None, physician_name: str | None = None) -> dict[str, Any]:
    override = {k: v for k, v in (patient or {}).items() if v not in (None, "")}
    info = analysis.patient_info
    sex = info.demographics.sex or "unknown"
    sex = getattr(sex, "value", sex)

    segments = [{
        "id": s.segment_id,
        "speaker": _SPEAKER.get(getattr(s.speaker, "value", str(s.speaker)).upper(), "unknown"),
        "start": s.start_time,
        "end": s.end_time,
        "text": s.text,
        "confidence": s.confidence if s.confidence is not None else 0.0,
        "source_type": "transcript",
    } for s in analysis.transcript]

    note: dict[str, list[dict[str, Any]]] = {sec: [] for sec in _SECTIONS}
    claims: list[dict[str, Any]] = []
    for sec in _SECTIONS:
        for c in getattr(analysis.soap_claims, sec, []):
            note[sec].append({"id": c.claim_id, "text": c.text, "citations": list(c.segment_ids),
                              "origin": "ai", "deleted": False})
            claims.append({"id": c.claim_id, "text": c.text, "section": sec, "citations": list(c.segment_ids),
                           "confidence": min(max(c.confidence or 0.0, 0.0), 1.0), "origin": "ai", "deleted": False})

    return {
        "encounter_id": analysis.consultation_id,
        "physician_id": physician_id,
        "physician_name": physician_name,
        "patient": {
            "id": override.get("id", analysis.consultation_id),
            "name": override.get("name", "Unknown patient"),
            "age": override.get("age", info.demographics.age),
            "sex": override.get("sex", str(sex)),
            "allergies": list(override.get("allergies") if override.get("allergies") is not None else info.allergies),
            "medications": list(override.get("medications") if override.get("medications") is not None else info.medications),
        },
        "transcript": {"segments": segments},
        "clinical_note": note,
        "claims": claims,
        # Extra context from Team 2B (ignored by Team 2C's schema, useful for audit/debug).
        "team_b": {
            "safety_status": getattr(analysis.safety_status, "value", analysis.safety_status),
            "conflicts": [c.model_dump(mode="json") for c in analysis.conflicts],
            "grounding": analysis.grounding.model_dump(mode="json"),
            "pipeline_version": analysis.metadata.pipeline_version,
        },
    }
