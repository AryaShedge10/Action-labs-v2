from datetime import datetime, timezone

from ..schemas.team_b import Claim, ClinicalNote, Patient, TeamBPayload, Transcript, TranscriptSegment, SoapStatement


def demo_payload() -> TeamBPayload:
    """Synthetic encounter with intentional safety errors for demonstration."""
    patient = Patient(
        id="P001",
        name="John Doe",
        age=42,
        date_of_birth="1984-03-12",
        sex="male",
        gender="man",
        allergies=["penicillin"],
        medications=["metformin"],
        medical_history=["type 2 diabetes mellitus"],
        family_history=["father with type 2 diabetes"],
        known_conditions=["type 2 diabetes mellitus"],
    )
    transcript = Transcript(
        segments=[
            TranscriptSegment(
                id="SEG001",
                speaker="patient",
                start=12.5,
                end=18.2,
                text="I have had a really bad headache for about three days.",
                confidence=0.97,
            ),
            TranscriptSegment(
                id="SEG002",
                speaker="physician",
                start=19.0,
                end=22.4,
                text="Any chest pain?",
                confidence=0.99,
            ),
            TranscriptSegment(
                id="SEG003",
                speaker="patient",
                start=22.8,
                end=26.1,
                text="No, I deny chest pain.",
                confidence=0.96,
            ),
            TranscriptSegment(
                id="SEG004",
                speaker="physician",
                start=27.0,
                end=31.0,
                text="Any history of asthma or breathing problems?",
                confidence=0.98,
            ),
            TranscriptSegment(
                id="SEG005",
                speaker="patient",
                start=31.4,
                end=36.0,
                text="I have no known history of asthma.",
                confidence=0.98,
            ),
            TranscriptSegment(
                id="SEG006",
                speaker="physician",
                start=40.0,
                end=44.0,
                text="Any medication allergies?",
                confidence=0.99,
            ),
            TranscriptSegment(
                id="SEG007",
                speaker="patient",
                start=44.5,
                end=49.2,
                text="Yes, I have a penicillin allergy.",
                confidence=0.99,
            ),
            TranscriptSegment(
                id="SEG008",
                speaker="physician",
                start=80.0,
                end=92.0,
                text="Blood pressure 128 over 82, heart rate 76, temperature 37.0.",
                confidence=0.95,
            ),
            TranscriptSegment(
                id="SEG009",
                speaker="physician",
                start=120.0,
                end=128.0,
                text="This is likely a tension-type headache. Continue metformin. Follow up in one week if symptoms persist.",
                confidence=0.93,
            ),
        ]
    )
    claims = [
        Claim(
            id="CLM001",
            text="Patient reports severe headache for three days.",
            section="subjective",
            citations=["SEG001"],
            confidence=0.94,
        ),
        Claim(
            id="CLM002",
            text="Patient denies chest pain.",
            section="subjective",
            citations=["SEG003"],
            confidence=0.96,
        ),
        Claim(
            id="CLM003",
            text="Patient has no known history of asthma.",
            section="subjective",
            citations=["SEG005"],
            confidence=0.95,
        ),
        Claim(
            id="CLM004",
            text="Patient reports penicillin allergy.",
            section="subjective",
            citations=["SEG007"],
            confidence=0.99,
        ),
        Claim(
            id="CLM005",
            text="Vital signs: BP 128/82, HR 76, temperature 37.0 C.",
            section="objective",
            citations=["SEG008"],
            confidence=0.92,
        ),
        Claim(
            id="CLM006",
            text="Patient has asthma.",
            section="assessment",
            citations=[],
            confidence=0.41,
        ),
        Claim(
            id="CLM007",
            text="Likely tension-type headache.",
            section="assessment",
            citations=["SEG009"],
            confidence=0.88,
        ),
        Claim(
            id="CLM008",
            text="Amoxicillin prescribed.",
            section="plan",
            citations=[],
            confidence=0.33,
        ),
        Claim(
            id="CLM009",
            text="Continue metformin.",
            section="plan",
            citations=["SEG009"],
            confidence=0.90,
        ),
        Claim(
            id="CLM010",
            text="Follow up in one week if symptoms persist.",
            section="plan",
            citations=["SEG009"],
            confidence=0.91,
        ),
        Claim(
            id="CLM011",
            text="Patient is a 65-year-old male.",
            section="subjective",
            citations=[],
            confidence=0.20,
        ),
        Claim(
            id="CLM012",
            text="Patient reports chest pain.",
            section="subjective",
            citations=[],
            confidence=0.22,
        ),
    ]

    def stmts(section: str) -> list[SoapStatement]:
        return [
            SoapStatement(
                id=claim.id,
                text=claim.text,
                citations=claim.citations,
                origin=claim.origin,
            )
            for claim in claims
            if claim.section == section
        ]

    note = ClinicalNote(
        subjective=stmts("subjective"),
        objective=stmts("objective"),
        assessment=stmts("assessment"),
        plan=stmts("plan"),
    )
    return TeamBPayload(
        encounter_id="ENC-2026-00124",
        encounter_at=datetime(2026, 8, 15, 14, 5, tzinfo=timezone.utc),
        physician_id="phys-001",
        physician_name="Dr. Smith",
        patient=patient,
        transcript=transcript,
        clinical_note=note,
        claims=claims,
    )
