"""
Role mapping for clinical conversations (Doctor/Patient).

The core problem with the previous implementation: it always assumed the FIRST speaker
is the Doctor. This is wrong — diarization does NOT guarantee speaker order.

This version uses content-based heuristics to reliably detect Doctor vs Patient,
then falls back to the first_speaker_is hint only if no strong evidence is found.
"""
from typing import List, Dict
import re


# Strong lexical signals for Doctor
_DOCTOR_PATTERNS = [
    r"\bhow are you\b",
    r"\bfeeling today\b",
    r"\bwhat brings you\b",
    r"\bany symptoms\b",
    r"\bprescri",              # prescribe, prescription
    r"\bdiagnos",             # diagnose, diagnosis
    r"\bi'll refer\b",
    r"\btake this medication\b",
    r"\bdosage\b",
    r"\bmg\b",                # medication dose
    r"\bblood pressure\b",
    r"\bexamination\b",
    r"\btest results\b",
    r"\bfollow.?up\b",
    r"\bmedical history\b",
    r"\bany allergies\b",
    r"\blet me check\b",
    r"\bgood morning.*can i help\b",
    r"\bopen your mouth\b",
    r"\bdeep breath\b",
    r"\bhow long have you\b",
]

# Strong lexical signals for Patient
_PATIENT_PATTERNS = [
    r"\bdoctor\b",            # addressing the doctor
    r"\bthank you doctor\b",
    r"\bi have been\b",
    r"\bi've been\b",
    r"\bmy chest\b",
    r"\bmy stomach\b",
    r"\bmy back\b",
    r"\bmy head\b",
    r"\bpain\b",
    r"\bfever\b",
    r"\bsick\b",
    r"\bnausea\b",
    r"\bvomiting\b",
    r"\bsore throat\b",
    r"\bcan't sleep\b",
    r"\blosing weight\b",
    r"\bshortness of breath\b",
    r"\byes doctor\b",
    r"\bno doctor\b",
]


def _score_text_for_role(text: str) -> Dict[str, float]:
    """Return {'Doctor': score, 'Patient': score} based on lexical heuristics."""
    text_lower = text.lower()
    doc_score = sum(1 for pat in _DOCTOR_PATTERNS if re.search(pat, text_lower))
    pat_score = sum(1 for pat in _PATIENT_PATTERNS if re.search(pat, text_lower))
    return {"Doctor": float(doc_score), "Patient": float(pat_score)}


def detect_speaker_roles(
    merged_segments: List[Dict],
    first_speaker_is: str = "Doctor"
) -> Dict[str, str]:
    """
    Analyse all segments and return a mapping of speaker -> role.
    Uses lexical scoring across all segments to identify who sounds like Doctor/Patient.
    Returns e.g. {"SPEAKER_00": "Doctor", "SPEAKER_01": "Patient"}
    """
    # Aggregate lexical scores per speaker
    speaker_scores: Dict[str, Dict[str, float]] = {}
    for seg in merged_segments:
        spk = seg.get("speaker", "UNKNOWN")
        if spk == "UNKNOWN":
            continue
        text = seg.get("text", "")
        scores = _score_text_for_role(text)
        if spk not in speaker_scores:
            speaker_scores[spk] = {"Doctor": 0.0, "Patient": 0.0}
        speaker_scores[spk]["Doctor"] += scores["Doctor"]
        speaker_scores[spk]["Patient"] += scores["Patient"]

    # Determine speaker order (for tie-breaking)
    seen_speakers = []
    for seg in merged_segments:
        spk = seg.get("speaker", "UNKNOWN")
        if spk != "UNKNOWN" and spk not in seen_speakers:
            seen_speakers.append(spk)
            if len(seen_speakers) >= 2:
                break

    speakers = list(speaker_scores.keys())
    if not speakers:
        return {}

    print(f"\n  [Roles] Lexical score analysis:")
    for spk in speakers:
        sc = speaker_scores[spk]
        print(f"    {spk}: Doctor={sc['Doctor']:.0f}  Patient={sc['Patient']:.0f}")

    # Only one speaker
    if len(seen_speakers) == 1:
        spk = seen_speakers[0]
        sc = speaker_scores.get(spk, {"Doctor": 0.0, "Patient": 0.0})
        if sc["Patient"] > sc["Doctor"]:
            return {spk: "Patient"}
        return {spk: "Doctor"}

    # Two-speaker case: assign roles based on net scores
    spk0, spk1 = seen_speakers[0], seen_speakers[1]
    sc0 = speaker_scores.get(spk0, {"Doctor": 0.0, "Patient": 0.0})
    sc1 = speaker_scores.get(spk1, {"Doctor": 0.0, "Patient": 0.0})

    doc_diff_0 = sc0["Doctor"] - sc0["Patient"]  # positive => spk0 leans Doctor
    doc_diff_1 = sc1["Doctor"] - sc1["Patient"]  # positive => spk1 leans Doctor

    total_evidence = abs(doc_diff_0) + abs(doc_diff_1)

    if total_evidence >= 1.0:  # enough lexical evidence
        if doc_diff_0 >= doc_diff_1:
            mapping = {spk0: "Doctor", spk1: "Patient"}
        else:
            mapping = {spk0: "Patient", spk1: "Doctor"}
        print(f"  [Roles] Lexical evidence ({total_evidence:.0f} pts) => {mapping}")
    else:
        # No strong lexical signal => fall back to first_speaker_is hint
        first_role = "Doctor" if str(first_speaker_is).strip().lower() == "doctor" else "Patient"
        second_role = "Patient" if first_role == "Doctor" else "Doctor"
        mapping = {spk0: first_role, spk1: second_role}
        print(f"  [Roles] Weak evidence ({total_evidence:.0f} pts) => fallback first-speaker={first_role}: {mapping}")

    # Pass through any extra speakers unchanged
    for spk in speakers:
        if spk not in mapping:
            mapping[spk] = spk

    return mapping


def label_roles(
    merged_segments: List[Dict],
    first_speaker_is: str = "Doctor"
) -> List[Dict]:
    """
    Map raw speaker labels to clinical roles.

    First tries content-based detection (lexical heuristics).
    Falls back to first_speaker_is hint if evidence is insufficient.

    Args:
        merged_segments: List of segments with "speaker" field
        first_speaker_is: Fallback role for first speaker ("Doctor" or "Patient")

    Returns:
        List of segments with added "role" and "role_source" fields
    """
    if not merged_segments:
        return merged_segments

    # Try content-based detection
    role_map = detect_speaker_roles(merged_segments, first_speaker_is=first_speaker_is)

    # If content detection gave no result, use first_speaker_is
    if not role_map:
        seen_speakers = []
        for seg in merged_segments:
            speaker = seg["speaker"]
            if speaker not in seen_speakers and speaker != "UNKNOWN":
                seen_speakers.append(speaker)
                if len(seen_speakers) >= 2:
                    break

        role_map = {}
        if len(seen_speakers) >= 1:
            if first_speaker_is == "Doctor":
                role_map[seen_speakers[0]] = "Doctor"
                if len(seen_speakers) >= 2:
                    role_map[seen_speakers[1]] = "Patient"
            else:
                role_map[seen_speakers[0]] = "Patient"
                if len(seen_speakers) >= 2:
                    role_map[seen_speakers[1]] = "Doctor"
        print(f"  [Roles] Empty detect_speaker_roles => fallback: {role_map}")

    # Apply role mapping
    result = []
    for seg in merged_segments:
        speaker = seg.get("speaker", "UNKNOWN")
        role = role_map.get(speaker, speaker)
        result.append({
            **seg,
            "role": role,
            "role_source": seg.get("role_source", "lexical_heuristic"),
        })

    return result
