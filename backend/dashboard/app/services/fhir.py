from datetime import datetime, timezone

from ..models.orm import Encounter
from ..schemas.team_b import Claim, ClinicalNote, Patient


def build_fhir_bundle(encounter: Encounter, physician_name: str) -> dict:
    patient = Patient.model_validate(encounter.patient)
    note = ClinicalNote.model_validate(encounter.clinical_note)
    claims = [Claim.model_validate(item) for item in encounter.claims]
    finalized = encounter.workflow_status == "finalized"
    now = datetime.now(timezone.utc).isoformat()
    patient_ref = f"Patient/{patient.id}"
    encounter_ref = f"Encounter/{encounter.encounter_id}"

    def statements(section: str) -> str:
        items = getattr(note, section)
        lines = [item.text for item in items if not item.deleted]
        return "\n".join(f"- {line}" for line in lines) or "None recorded."

    narrative = (
        f"Subjective\n{statements('subjective')}\n\n"
        f"Objective\n{statements('objective')}\n\n"
        f"Assessment\n{statements('assessment')}\n\n"
        f"Plan\n{statements('plan')}"
    )

    entries: list[dict] = [
        {
            "fullUrl": f"urn:uuid:{patient.id}",
            "resource": {
                "resourceType": "Patient",
                "id": patient.id,
                "identifier": [{"system": "urn:clinical-scribe:patient", "value": patient.id}],
                "name": [{"text": patient.name}],
                "gender": patient.sex if patient.sex in {"male", "female", "other"} else "unknown",
                "birthDate": patient.date_of_birth,
            },
        },
        {
            "fullUrl": f"urn:uuid:{encounter.encounter_id}",
            "resource": {
                "resourceType": "Encounter",
                "id": encounter.encounter_id,
                "status": "finished" if finalized else "in-progress",
                "class": {"code": "AMB", "display": "ambulatory"},
                "subject": {"reference": patient_ref},
                "period": {"start": encounter.encounter_at.isoformat()},
                "participant": [
                    {
                        "individual": {
                            "display": physician_name,
                        }
                    }
                ],
            },
        },
    ]

    for index, allergy in enumerate(patient.allergies):
        entries.append(
            {
                "fullUrl": f"urn:uuid:allergy-{index}",
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": f"allergy-{index}",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "patient": {"reference": patient_ref},
                    "code": {"text": allergy},
                },
            }
        )

    for index, med in enumerate(patient.medications):
        entries.append(
            {
                "fullUrl": f"urn:uuid:med-current-{index}",
                "resource": {
                    "resourceType": "MedicationStatement",
                    "id": f"med-current-{index}",
                    "status": "active",
                    "medicationCodeableConcept": {"text": med},
                    "subject": {"reference": patient_ref},
                },
            }
        )

    plan_meds = [
        claim
        for claim in claims
        if claim.section == "plan" and not claim.deleted and "prescrib" in claim.text.lower()
    ]
    for index, claim in enumerate(plan_meds):
        entries.append(
            {
                "fullUrl": f"urn:uuid:medreq-{index}",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": f"medreq-{index}",
                    "status": "completed" if finalized else "draft",
                    "intent": "order",
                    "medicationCodeableConcept": {"text": claim.text},
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": encounter_ref},
                    "note": [{"text": "Physician-reviewed draft mapped from clinical note."}],
                },
            }
        )

    assessment_claims = [
        claim for claim in claims if claim.section == "assessment" and not claim.deleted
    ]
    for index, claim in enumerate(assessment_claims):
        entries.append(
            {
                "fullUrl": f"urn:uuid:condition-{index}",
                "resource": {
                    "resourceType": "Condition",
                    "id": f"condition-{index}",
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "verificationStatus": {
                        "coding": [{"code": "confirmed" if finalized else "provisional"}]
                    },
                    "code": {"text": claim.text},
                    "subject": {"reference": patient_ref},
                    "encounter": {"reference": encounter_ref},
                },
            }
        )

    entries.append(
        {
            "fullUrl": "urn:uuid:impression-1",
            "resource": {
                "resourceType": "ClinicalImpression",
                "id": "impression-1",
                "status": "completed" if finalized else "in-progress",
                "subject": {"reference": patient_ref},
                "encounter": {"reference": encounter_ref},
                "summary": statements("assessment"),
                "note": [
                    {
                        "text": (
                            "Draft/export generated from physician-finalized documentation. "
                            "Not an independent diagnostic system."
                            if finalized
                            else "Draft export. Physician finalization required before EHR use."
                        )
                    }
                ],
            },
        }
    )
    entries.append(
        {
            "fullUrl": "urn:uuid:document-1",
            "resource": {
                "resourceType": "DocumentReference",
                "id": "document-1",
                "status": "current",
                "docStatus": "final" if finalized else "preliminary",
                "type": {"text": "Clinical encounter note"},
                "subject": {"reference": patient_ref},
                "date": now,
                "author": [{"display": physician_name}],
                "description": "Physician-reviewed clinical documentation export",
                "content": [
                    {
                        "attachment": {
                            "contentType": "text/plain",
                            "title": "SOAP note",
                            "language": "en",
                        }
                    }
                ],
                "text": {"status": "generated", "div": f"<div>{narrative}</div>"},
            },
        }
    )
    entries.append(
        {
            "fullUrl": "urn:uuid:report-1",
            "resource": {
                "resourceType": "DiagnosticReport",
                "id": "report-1",
                "status": "final" if finalized else "partial",
                "code": {"text": "Clinical encounter documentation"},
                "subject": {"reference": patient_ref},
                "encounter": {"reference": encounter_ref},
                "conclusion": statements("assessment"),
            },
        }
    )

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "timestamp": now,
        "meta": {
            "tag": [
                {
                    "system": "urn:clinical-scribe:export",
                    "code": "physician-reviewed" if finalized else "draft",
                    "display": (
                        "FHIR export generated from physician-finalized documentation"
                        if finalized
                        else "Draft FHIR export — not for EHR filing"
                    ),
                }
            ]
        },
        "entry": entries,
    }
