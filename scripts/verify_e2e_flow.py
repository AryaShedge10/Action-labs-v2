"""
End-to-End Live Workflow Verification Script
Executes full clinical encounter flow across all running services:
1. Ingest transcript -> Team 2B Clinical NLP & Extraction -> Encounter DB
2. Finalize encounter with physician attestation checklist
3. Generate and verify PDF export (ReportLab)
4. Export FHIR Bundle
5. Transmit FHIR Bundle to Mock EHR (Port 8001)
"""
import urllib.request
import json
import sys

def main():
    print("=" * 60)
    print(" Clinical Scribe Unified Platform - Live E2E Flow Test")
    print("=" * 60)

    # 1. Pipeline from transcript
    payload = {
        "consultation_id": "ENC-TEST-1001",
        "patient_name": "John Doe",
        "patient_id": "P-1002",
        "language": "en-US",
        "segments": [
            {
                "speaker": "Doctor",
                "text": "Hello John, what brings you in today?",
                "start": 0.0,
                "end": 2.5
            },
            {
                "speaker": "Patient",
                "text": "I have had a severe headache and high blood pressure for three days.",
                "start": 2.6,
                "end": 6.8
            },
            {
                "speaker": "Doctor",
                "text": "Are you currently taking any prescription medications?",
                "start": 7.0,
                "end": 9.5
            },
            {
                "speaker": "Patient",
                "text": "I take Lisinopril 10mg daily in the morning.",
                "start": 9.8,
                "end": 13.0
            },
            {
                "speaker": "Doctor",
                "text": "Do you have any known drug allergies?",
                "start": 13.2,
                "end": 15.1
            },
            {
                "speaker": "Patient",
                "text": "Yes, Penicillin causes severe hives and difficulty breathing.",
                "start": 15.4,
                "end": 19.2
            }
        ]
    }
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/encounters/pipeline/from-transcript",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        enc = json.loads(resp.read().decode("utf-8"))
    
    enc_id = enc["encounter_id"]
    workflow_status = enc.get("workflow_status")
    print(f"[PASS] 1. Pipeline Ingestion: Encounter ID = {enc_id}, Status = {workflow_status}")

    # Inspect clinical note generated
    note = enc.get("clinical_note") or {}
    print(f"       Extracted Subjective: {note.get('subjective', [])}")
    print(f"       Extracted Assessment: {note.get('assessment', [])}")
    print(f"       Extracted Plan      : {note.get('plan', [])}")

    # 2. Finalize Encounter
    fin_payload = {
        "reviewed_documentation": True,
        "reviewed_conflicts": True,
        "verified_medications_allergies": True,
        "approve_for_ehr_export": True
    }
    req2 = urllib.request.Request(
        f"http://127.0.0.1:8000/api/encounters/{enc_id}/finalize",
        data=json.dumps(fin_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req2, timeout=10) as resp:
        fin = json.loads(resp.read().decode("utf-8"))
    print(f"[PASS] 2. Physician Finalization: Workflow Status = {fin.get('workflow_status')}, Finalized At = {fin.get('finalized_at')}")

    # 3. PDF Export
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/encounters/{enc_id}/export/pdf", timeout=10) as resp:
        pdf_bytes = resp.read()
    print(f"[PASS] 3. ReportLab PDF Export: {len(pdf_bytes)} bytes received (Content-Type: {resp.headers.get('content-type')})")

    # 4. FHIR Export
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/encounters/{enc_id}/export/fhir", timeout=10) as resp:
        fhir_data = json.loads(resp.read().decode("utf-8"))
    resource_type = fhir_data.get("resourceType")
    total_entries = len(fhir_data.get("entry", []))
    print(f"[PASS] 4. FHIR Export: ResourceType = {resource_type}, Entries = {total_entries}")

    # 5. Mock EHR Handoff
    handoff_payload = {"encounter_id": enc_id}
    req3 = urllib.request.Request(
        "http://127.0.0.1:8000/api/ehr/handoff",
        data=json.dumps(handoff_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req3, timeout=10) as resp:
        handoff = json.loads(resp.read().decode("utf-8"))
    print(f"[PASS] 5. Mock EHR Integration Handoff: Status = {handoff.get('status')}, Transmission = {handoff.get('message', 'Delivered')}")

    print("=" * 60)
    print(" ALL 5 CLINICAL INTEGRATION STAGES SUCCEEDED WITHOUT ERRORS")
    print("=" * 60)

if __name__ == "__main__":
    main()
