"""Deterministic clinical conflict detection. Not an LLM."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from ..schemas.team_b import Claim, Patient, Transcript


PENICILLIN_CLASS = {
    "penicillin",
    "penicillins",
    "amoxicillin",
    "amoxil",
    "ampicillin",
    "augmentin",
    "amoxicillin-clavulanate",
    "amoxicillin clavulanate",
    "piperacillin",
    "zosyn",
    "oxacillin",
    "nafcillin",
    "dicloxacillin",
    "ticarcillin",
    "benzylpenicillin",
    "penicillin vk",
    "penicillin g",
}

SULFA_CLASS = {
    "sulfa",
    "sulfonamide",
    "sulfamethoxazole",
    "trimethoprim-sulfamethoxazole",
    "bactrim",
    "septra",
}

NSAID_CLASS = {
    "nsaid",
    "ibuprofen",
    "naproxen",
    "aspirin",
    "diclofenac",
    "ketorolac",
    "celecoxib",
}

ALLERGY_CLASSES = {
    "penicillin": PENICILLIN_CLASS,
    "penicillins": PENICILLIN_CLASS,
    "pcn": PENICILLIN_CLASS,
    "sulfa": SULFA_CLASS,
    "sulfonamide": SULFA_CLASS,
    "nsaid": NSAID_CLASS,
    "nsaids": NSAID_CLASS,
    "aspirin": NSAID_CLASS,
    "ibuprofen": NSAID_CLASS,
}

PREGNANCY_TERMS = (
    "pregnant",
    "pregnancy",
    "gravid",
    "gestation",
    "prenatal",
    "fetus",
    "fetal",
    "obstetric",
)

SYMPTOMS = (
    "chest pain",
    "shortness of breath",
    "dyspnea",
    "headache",
    "fever",
    "cough",
    "nausea",
    "vomiting",
    "dizziness",
    "asthma",
    "wheezing",
    "rash",
    "abdominal pain",
    "syncope",
)

AGE_PATTERN = re.compile(r"(\d{1,3})\s*[- ]?\s*year[s]?[ -]?old", re.I)
MED_TOKEN = re.compile(r"[a-z][a-z0-9\-]{2,}")


@dataclass
class Conflict:
    id: str
    severity: str
    category: str
    title: str
    message: str
    claim_id: str | None = None
    resolved: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _active_claims(claims: list[Claim]) -> list[Claim]:
    return [claim for claim in claims if not claim.deleted]


def _allergy_matches(allergy: str, medication: str) -> bool:
    allergy_n = _norm(allergy)
    med_n = _norm(medication)
    if allergy_n and allergy_n in med_n:
        return True
    drug_class = ALLERGY_CLASSES.get(allergy_n)
    if drug_class and med_n in drug_class:
        return True
    if allergy_n in PENICILLIN_CLASS and med_n in PENICILLIN_CLASS:
        return True
    return False


def detect_allergy_conflicts(patient: Patient, claims: list[Claim]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    allergies = [_norm(item) for item in patient.allergies]
    for claim in _active_claims(claims):
        text = _norm(claim.text)
        for allergy in allergies:
            for token in {allergy, *ALLERGY_CLASSES.get(allergy, set())}:
                if token and token in text and (
                    "prescrib" in text
                    or "start" in text
                    or "given" in text
                    or "plan" in claim.section
                    or "medication" in text
                ):
                    if _allergy_matches(allergy, token) or token in text:
                        conflicts.append(
                            Conflict(
                                id=f"allergy-{claim.id}-{allergy}",
                                severity="CRITICAL",
                                category="allergy",
                                title="CRITICAL SAFETY CONFLICT",
                                message=(
                                    f"Patient allergy ({allergy}) conflicts with generated "
                                    f"medication language in claim {claim.id}."
                                ),
                                claim_id=claim.id,
                            )
                        )
                        break
    # also scan plan statements for medication names even without "prescribed"
    for claim in _active_claims(claims):
        if claim.section != "plan":
            continue
        words = set(MED_TOKEN.findall(_norm(claim.text)))
        for allergy in allergies:
            related = {allergy, *ALLERGY_CLASSES.get(allergy, set())}
            overlap = words & related
            if overlap:
                cid = f"allergy-plan-{claim.id}-{allergy}"
                if any(item.id == cid for item in conflicts):
                    continue
                conflicts.append(
                    Conflict(
                        id=cid,
                        severity="CRITICAL",
                        category="allergy",
                        title="CRITICAL SAFETY CONFLICT",
                        message=(
                            f"Allergy '{allergy}' vs generated medication "
                            f"{', '.join(sorted(overlap))}."
                        ),
                        claim_id=claim.id,
                    )
                )
    return _dedupe(conflicts)


def detect_demographic_conflicts(patient: Patient, claims: list[Claim]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    sex = _norm(patient.sex)
    male_like = sex in {"male", "m", "man"}
    for claim in _active_claims(claims):
        text = _norm(claim.text)
        if male_like and any(term in text for term in PREGNANCY_TERMS):
            conflicts.append(
                Conflict(
                    id=f"demo-preg-{claim.id}",
                    severity="CRITICAL",
                    category="demographic",
                    title="DEMOGRAPHIC CONFLICT",
                    message="Generated statement implies pregnancy for a patient recorded as male.",
                    claim_id=claim.id,
                )
            )
        match = AGE_PATTERN.search(claim.text)
        if match and patient.age is not None:
            stated_age = int(match.group(1))
            if abs(stated_age - patient.age) >= 5:
                conflicts.append(
                    Conflict(
                        id=f"demo-age-{claim.id}",
                        severity="HIGH",
                        category="age",
                        title="DEMOGRAPHIC CONFLICT",
                        message=(
                            f"Generated age ({stated_age}) differs from recorded age ({patient.age})."
                        ),
                        claim_id=claim.id,
                    )
                )
    return _dedupe(conflicts)


def detect_medication_conflicts(patient: Patient, claims: list[Claim]) -> list[Conflict]:
    conflicts: list[Conflict] = []
    current = [_norm(item) for item in patient.medications]
    plan_meds: list[tuple[str, str]] = []
    for claim in _active_claims(claims):
        if claim.section != "plan":
            continue
        text = _norm(claim.text)
        tokens = MED_TOKEN.findall(text)
        for token in tokens:
            if token in current:
                plan_meds.append((token, claim.id))
                if "discontinu" in text or "stop" in text:
                    continue
                # duplicate continuation is medium, duplicate new start is high
                if "start" in text or "prescrib" in text or "add" in text:
                    conflicts.append(
                        Conflict(
                            id=f"med-dup-{claim.id}-{token}",
                            severity="MEDIUM",
                            category="medication",
                            title="Duplicate medication",
                            message=f"Plan appears to re-prescribe existing medication '{token}'.",
                            claim_id=claim.id,
                        )
                    )
        if "discontinu" in text and "continue" in text:
            conflicts.append(
                Conflict(
                    id=f"med-contradict-{claim.id}",
                    severity="HIGH",
                    category="medication",
                    title="Contradictory medication instructions",
                    message="Plan both continues and discontinues therapy in the same statement.",
                    claim_id=claim.id,
                )
            )
    return _dedupe(conflicts)


def detect_transcript_contradictions(
    transcript: Transcript, claims: list[Claim]
) -> list[Conflict]:
    conflicts: list[Conflict] = []
    joined = " ".join(_norm(seg.text) for seg in transcript.segments)
    for symptom in SYMPTOMS:
        denied = bool(
            re.search(
                rf"(denies|denied|deny|no known|no history of|does not have|negative for|without)\s+[^.]*{re.escape(symptom)}",
                joined,
            )
        ) or bool(
            re.search(
                rf"(no known history of|denies)\s+{re.escape(symptom)}",
                joined,
            )
        )
        if not denied:
            # also "Patient has no known history of asthma"
            denied = bool(
                re.search(
                    rf"(no known history of|denies|denied)\s+{re.escape(symptom)}",
                    joined,
                )
            )
        if not denied:
            continue
        for claim in _active_claims(claims):
            text = _norm(claim.text)
            if symptom not in text:
                continue
            if re.search(rf"(denies|no known|does not|negative for|without)\s+[^.]*{re.escape(symptom)}", text):
                continue
            if re.search(rf"(reports|has|presents with|complains of|positive for|history of)\s+[^.]*{re.escape(symptom)}", text) or (
                f"has {symptom}" in text or f"have {symptom}" in text or f"with {symptom}" in text
            ):
                conflicts.append(
                    Conflict(
                        id=f"tx-{claim.id}-{symptom.replace(' ', '-')}",
                        severity="HIGH",
                        category="transcript",
                        title="TRANSCRIPT CONTRADICTION",
                        message=(
                            f"Transcript denies or lacks '{symptom}', but generated note affirms it."
                        ),
                        claim_id=claim.id,
                    )
                )
    return _dedupe(conflicts)


def detect_patient_source_conflicts(patient: Patient, claims: list[Claim]) -> list[Conflict]:
    """Generated content vs source-of-truth patient record."""
    return detect_demographic_conflicts(patient, claims) + detect_allergy_conflicts(
        patient, claims
    )


def run_conflict_engine(
    patient: Patient, transcript: Transcript, claims: list[Claim]
) -> list[Conflict]:
    results = (
        detect_allergy_conflicts(patient, claims)
        + detect_demographic_conflicts(patient, claims)
        + detect_medication_conflicts(patient, claims)
        + detect_transcript_contradictions(transcript, claims)
    )
    return _dedupe(results)


def _dedupe(conflicts: list[Conflict]) -> list[Conflict]:
    seen: set[str] = set()
    unique: list[Conflict] = []
    for item in conflicts:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return unique
