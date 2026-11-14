# API Contracts & Inter-Service Specifications

## 1. Canonical Identifier Specification

Across all services, consultations and encounters use a shared canonical identifier:
- **Format:** Regular expression `^[A-Za-z0-9_.:\-]{1,128}$`
- **Example:** `ENC-20261114-001` or `20261114_143022`

---

## 2. Transcript Contract (Service A -> Service B)

### Contract Schema: `TeamATranscriptIn`
```json
{
  "consultation_id": "ENC-20261114-001",
  "language": "en-US",
  "segments": [
    {
      "speaker": "DOCTOR",
      "start_time": 0.0,
      "end_time": 3.45,
      "text": "Good morning. What brings you into the clinic today?",
      "confidence": 0.98
    },
    {
      "speaker": "PATIENT",
      "start_time": 3.82,
      "end_time": 8.15,
      "text": "I have had a severe sore throat and fever for the past three days.",
      "confidence": 0.96
    }
  ]
}
```

### Normalization of Timestamp Field Discrepancies
- **Service A Emission:** `start_time` / `end_time` (floats in seconds).
- **Service C Expectation:** `start` / `end` (floats in seconds).
- **Resolution:** Shared adapter and Pydantic validators accept both `start`/`end` and `start_time`/`end_time`, normalizing into canonical attributes without data loss.

---

## 3. Clinical Analysis Contract (Service B -> Service C)

### Contract Schema: `TeamBPayload`
```json
{
  "encounter_id": "ENC-20261114-001",
  "encounter_at": "2026-11-14T14:30:22Z",
  "physician_id": "phys-001",
  "physician_name": "Dr. Sarah Smith, MD",
  "patient": {
    "id": "PT-98214",
    "name": "Jane Doe",
    "age": null,
    "date_of_birth": "1982-05-12",
    "sex": "female",
    "gender": "female",
    "allergies": ["penicillin"],
    "medications": ["lisinopril 10mg"],
    "medical_history": ["hypertension"],
    "family_history": ["type 2 diabetes"],
    "known_conditions": []
  },
  "transcript": {
    "segments": [
      {
        "id": "seg_001",
        "speaker": "physician",
        "start": 0.0,
        "end": 3.45,
        "text": "Good morning. What brings you into the clinic today?",
        "confidence": 0.98,
        "source_type": "transcript"
      }
    ]
  },
  "clinical_note": {
    "subjective": [
      {
        "id": "claim_001",
        "text": "Patient presents with sore throat and fever for three days.",
        "citations": ["seg_002"],
        "origin": "ai",
        "deleted": false
      }
    ],
    "objective": [],
    "assessment": [],
    "plan": []
  },
  "claims": [
    {
      "id": "claim_001",
      "text": "Patient presents with sore throat and fever for three days.",
      "section": "subjective",
      "citations": ["seg_002"],
      "confidence": 0.95,
      "origin": "ai",
      "deleted": false
    }
  ]
}
```

### Critical Schema Harmonization: Nullable Age
- **Previous Repository C:** `age: int = Field(ge=0, le=130)` -> failed validation when patient age was unstated.
- **Unified Standard:** `age: int | None = Field(default=None, ge=0, le=130)`. In both backend schemas and frontend TypeScript types (`age?: number | null`), unknown age is explicitly represented as `null` without fabricating dummy numbers.

---

## 4. Encounter Finalization & Mock EHR Handoff Contract

### Mock EHR Ingestion Payload:
```json
{
  "encounter_id": "ENC-20261114-001",
  "physician_id": "phys-001",
  "patient": {
    "id": "PT-98214"
  },
  "bundle": {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
      { "resource": { "resourceType": "Composition", "status": "final" } },
      { "resource": { "resourceType": "Patient", "id": "PT-98214" } },
      { "resource": { "resourceType": "Encounter", "status": "finished" } }
    ]
  }
}
```

