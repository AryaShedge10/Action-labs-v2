"""
LLM-based role refinement using Groq.

Key fixes vs previous version:
- Primary model changed to llama3-70b-8192 (fast, handles large context, no JSON issues)
- Large transcripts (>30 segments) are sampled: send representative 30 segments,
  infer the rest from alternating pattern — avoids token limit failures
- Fallback chain updated to reliable models only
"""
import os
import json
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# Fast, reliable models on Groq — ordered by preference
# NOTE: model IDs must NOT have the "groq/" prefix when calling Groq SDK directly
_PRIMARY_MODEL   = "openai/gpt-oss-120b"
_FALLBACK_MODELS = ["openai/gpt-oss-20b", "qwen/qwen3.8-27b"]

# Max segments to send in one LLM call — beyond this we sample
_MAX_SEGMENTS_PER_CALL = 20


def refine_roles_with_llm(segments: List[Dict]) -> List[Dict]:
    """
    Refine Doctor/Patient role assignments using Groq LLM.
    For large transcripts, samples key segments and infers the rest.
    Strict privacy mode: disabled by default unless ENABLE_EXTERNAL_LLM=true.
    """
    if not segments:
        return segments

    enable_external = os.getenv("ENABLE_EXTERNAL_LLM", "false").strip().lower() in ("true", "1", "yes")
    if not enable_external:
        print("  [PRIVACY] ENABLE_EXTERNAL_LLM is disabled; skipping external Groq LLM refinement to protect PHI.")
        for seg in segments:
            if "role_source" not in seg:
                seg["role_source"] = "local_heuristic"
        return segments

    print(f"  Sending {len(segments)} segments to Groq LLM for role refinement...")

    try:
        if len(segments) <= _MAX_SEGMENTS_PER_CALL:
            # Small transcript — send everything
            refined_roles = _call_groq(segments)
        else:
            # Large transcript — sample intelligently
            refined_roles = _call_groq_sampled(segments)

        if not refined_roles or len(refined_roles) != len(segments):
            print("  [WARN]  LLM refinement failed, keeping diarization roles")
            for seg in segments:
                seg["role_source"] = "diarization_only"
            return segments

        changes = 0
        for i, seg in enumerate(segments):
            if seg["role"] != refined_roles[i]:
                seg["role"] = refined_roles[i]
                seg["role_source"] = "llm_corrected"
                changes += 1
            else:
                seg["role_source"] = "llm_confirmed"

        print(f"  [OK] LLM refined: {changes} change(s), {len(segments)-changes} confirmed")
        return segments

    except Exception as e:
        print(f"  [WARN]  LLM refinement error: {e}")
        for seg in segments:
            seg["role_source"] = "diarization_only"
        return segments


def _call_groq_sampled(segments: List[Dict]) -> List[str]:
    """
    For large transcripts: send first 15 + last 15 segments to establish
    the role pattern, then apply that pattern to all segments.
    """
    n = len(segments)
    half = _MAX_SEGMENTS_PER_CALL // 2

    # Take first half + last half as representative sample
    sample_indices = list(range(half)) + list(range(n - half, n))
    sample_segs = [segments[i] for i in sample_indices]

    print(f"  [LLM] Large transcript ({n} segs) — sampling {len(sample_segs)} representative segments")

    sample_roles = _call_groq(sample_segs)
    if not sample_roles or len(sample_roles) != len(sample_segs):
        return []

    # Map sample indices back to their roles
    sample_role_map = {sample_indices[i]: sample_roles[i] for i in range(len(sample_indices))}

    # Build a speaker-to-role mapping from the sampled results
    # This is more reliable than alternating heuristic — uses actual diarization speaker IDs
    speaker_role_map: dict = {}
    for i, role in zip(sample_indices, sample_roles):
        spk = segments[i].get("speaker", "UNKNOWN")
        if spk != "UNKNOWN":
            # If we see conflicting assignments for same speaker, majority wins
            if spk not in speaker_role_map:
                speaker_role_map[spk] = {}
            speaker_role_map[spk][role] = speaker_role_map[spk].get(role, 0) + 1

    # Resolve to single role per speaker
    resolved_speaker_role: dict = {}
    for spk, votes in speaker_role_map.items():
        resolved_speaker_role[spk] = max(votes, key=votes.get)

    print(f"  [LLM] Speaker→Role map from sample: {resolved_speaker_role}")

    # Build full roles list — use speaker map for all segments
    full_roles = []
    for i, seg in enumerate(segments):
        if i in sample_role_map:
            full_roles.append(sample_role_map[i])
        else:
            spk = seg.get("speaker", "UNKNOWN")
            if spk in resolved_speaker_role:
                full_roles.append(resolved_speaker_role[spk])
            else:
                # Fallback: use the role of the previous segment
                full_roles.append(full_roles[-1] if full_roles else "Doctor")

    return full_roles


def _call_groq(segments: List[Dict]) -> List[str]:
    """
    Call Groq API with a list of segments (max _MAX_SEGMENTS_PER_CALL).
    Returns list of role strings or empty list on failure.
    """
    try:
        from groq import Groq
    except ImportError:
        print("  [WARN]  groq package not installed")
        return []

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("  [WARN]  GROQ_API_KEY not configured")
        return []

    # Build compact context — just index, role, and text (no speaker labels)
    lines = []
    for i, seg in enumerate(segments):
        lines.append(f'{i}|{seg["role"]}|{seg["text"][:120]}')
    context = "\n".join(lines)

    prompt = f"""You are a clinical conversation analyst. Fix Doctor/Patient role assignments.

Format: index|CurrentRole|text
Return JSON: {{"roles": ["Doctor","Patient",...]}} with exactly {len(segments)} labels.

Rules:
- Doctor greets first ("Good morning", "How can I help")
- Doctor asks diagnostic questions, gives instructions, prescribes
- Patient describes symptoms, answers questions, says "thank you doctor"
- Roles should alternate naturally

Transcript ({len(segments)} lines):
{context}

Return ONLY the JSON object, no explanation."""

    models_to_try = [_PRIMARY_MODEL] + _FALLBACK_MODELS

    client = Groq(api_key=api_key)

    for model in models_to_try:
        try:
            print(f"  Trying model: {model}")

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system",
                     "content": "Return only valid JSON with a 'roles' array."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=max(512, len(segments) * 12),
            )

            content = response.choices[0].message.content
            if not content or not content.strip():
                print(f"  [FAIL] {model}: empty response")
                continue

            content = content.strip()

            # Strip markdown fences if present
            if "```" in content:
                for part in content.split("```"):
                    part = part.strip().lstrip("json").strip()
                    if part.startswith("{"):
                        content = part
                        break

            parsed = json.loads(content)

            # Find roles array — try multiple key names
            roles = None
            for key in ["roles", "labels", "result", "data", "output"]:
                if key in parsed and isinstance(parsed[key], list):
                    roles = parsed[key]
                    break

            if roles is None or len(roles) != len(segments):
                print(f"  [FAIL] {model}: expected {len(segments)} roles, got "
                      f"{len(roles) if roles else 'None'}")
                continue

            # Normalise role strings (handle "doctor", "DOCTOR", "Doctor")
            normalised = []
            for r in roles:
                r_str = str(r).strip().lower()
                if r_str in ("doctor", "dr", "physician"):
                    normalised.append("Doctor")
                elif r_str in ("patient", "pt"):
                    normalised.append("Patient")
                else:
                    normalised.append(r)  # will fail validation below

            invalid = [r for r in normalised if r not in ("Doctor", "Patient")]
            if invalid:
                print(f"  [FAIL] {model}: invalid roles {invalid[:3]}")
                continue

            print(f"  [OK] LLM success with {model}")
            return normalised

        except Exception as e:
            print(f"  [FAIL] {model}: {type(e).__name__}: {str(e)[:120]}")
            if hasattr(e, "response"):
                print(f"    HTTP {getattr(e.response, 'status_code', '?')}: "
                      f"{getattr(e.response, 'text', '')[:150]}")
            continue

    print("  [FAIL] All models failed")
    return []


def validate_groq_config() -> str:
    """Validate Groq config at startup. Returns warning string or empty string."""
    enable_external = os.getenv("ENABLE_EXTERNAL_LLM", "false").strip().lower() in ("true", "1", "yes")
    if not enable_external:
        return ""

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return ""

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        models_response = client.models.list()
        available = [m.id for m in models_response.data]

        if _PRIMARY_MODEL in available:
            print(f"[OK] Groq configured — primary model: {_PRIMARY_MODEL}")
            return ""
        else:
            return (f"[WARN]  Primary model '{_PRIMARY_MODEL}' not found. "
                    f"Available: {', '.join(available[:5])}")
    except Exception as e:
        return f"[WARN]  Groq validation error: {e}"


# ---------------------------------------------------------------------------
# Master Prompt 3-Chunk Window Contextual Refiner (Sections 8, 9, 10, 11, 25, 26)
# ---------------------------------------------------------------------------

def _extract_words_set(text: str) -> set:
    import re
    return set(re.findall(r"\b[a-zA-Z0-9']+\b", text.lower()))


_COMMON_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just",
    "don", "should", "now", "i", "me", "my", "myself", "we", "our", "ours",
    "you", "your", "yours", "yourself", "yourselves", "he", "him", "his",
    "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they",
    "them", "their", "theirs", "themselves", "am", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "having", "do", "does", "did"
}


def _validate_anti_hallucination(input_utterances: List[Dict], output_turns: List[Dict]) -> bool:
    """
    Section 25: Ensure the LLM never invented clinical facts or hallucinated words.
    Output words must be substantially covered by the input words.
    """
    if not output_turns:
        return False

    input_text = " ".join(u.get("text", "") for u in input_utterances)
    output_text = " ".join(t.get("text", "") for t in output_turns)

    in_words = _extract_words_set(input_text)
    out_words = _extract_words_set(output_text)

    if not out_words:
        return False

    # Out-of-vocabulary words created by LLM (excluding common grammatical stopwords)
    new_substantive_words = (out_words - in_words) - _COMMON_STOPWORDS
    if len(new_substantive_words) > 2:
        print(f"  [WARN] LLM hallucination detected! New substantive words: {list(new_substantive_words)[:5]}")
        return False

    return True


def local_rule_refine_window(window_payload: Dict) -> Dict:
    """
    Deterministic rule-based window refiner used as primary logic or fallback.
    - Merges consecutive same-speaker segments (Section 12)
    - Keeps different speakers split (Section 13)
    - Preserves overlaps (Section 14)
    - Applies lexical role mapping from roles.py (Section 15)
    - Preserves exact Whisper words verbatim (Section 25)
    """
    from app.services.roles import detect_speaker_roles

    utterances = window_payload.get("utterances", [])
    if not utterances:
        return {"turns": []}

    # Lexical role detection
    role_map = detect_speaker_roles(utterances)

    turns = []
    for u in utterances:
        raw_spk = u.get("speaker", "UNKNOWN")
        role = role_map.get(raw_spk, raw_spk).upper()
        if role not in ("DOCTOR", "PATIENT"):
            role = "DOCTOR" if "00" in raw_spk else "PATIENT"

        turns.append({
            "speaker": role,
            "speaker_raw": raw_spk,
            "start": round(float(u.get("start", 0.0)), 2),
            "end": round(float(u.get("end", 0.0)), 2),
            "text": str(u.get("text", "")).strip(),
            "overlap": bool(u.get("overlap", False))
        })

    # Merge consecutive same-speaker turns
    if len(turns) <= 1:
        return {"turns": turns}

    merged_turns = []
    curr = dict(turns[0])

    for nxt in turns[1:]:
        same_spk = curr["speaker"] == nxt["speaker"]
        gap = nxt["start"] - curr["end"]
        # Merge if same speaker and small gap and neither is overlapping
        if same_spk and gap <= 4.0 and not curr["overlap"] and not nxt["overlap"]:
            c_txt = curr["text"].rstrip()
            n_txt = nxt["text"].lstrip()
            if c_txt and not c_txt.endswith((".", "?", "!", ",", ";")):
                curr["text"] = f"{c_txt}. {n_txt}"
            else:
                curr["text"] = f"{c_txt} {n_txt}"
            curr["end"] = max(curr["end"], nxt["end"])
        else:
            merged_turns.append(curr)
            curr = dict(nxt)

    merged_turns.append(curr)
    return {"turns": merged_turns}


def refine_window_with_llm(window_payload: Dict) -> Dict:
    """
    Master Prompt Section 8-11:
    Sends a rolling 3-chunk window to Groq for contextual refinement:
    - Conversational grouping and sentence merging across chunks
    - Doctor / Patient role confirmation
    - Preserves exact transcript wording (anti-hallucination check)
    Falls back gracefully to local_rule_refine_window on any failure.
    """
    utterances = window_payload.get("utterances", [])
    if not utterances:
        return {"turns": []}

    enable_external = os.getenv("ENABLE_EXTERNAL_LLM", "false").strip().lower() in ("true", "1", "yes")
    if not enable_external:
        return local_rule_refine_window(window_payload)

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        return local_rule_refine_window(window_payload)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
    except Exception:
        return local_rule_refine_window(window_payload)

    # Prepare structured JSON prompt
    system_prompt = (
        "You are a clinical conversation segmentation engine. "
        "You receive structured transcription segments with timestamps and acoustic speaker labels.\n"
        "Your task:\n"
        "1. Map speakers to 'DOCTOR' and 'PATIENT' based on provided evidence and dialogue context.\n"
        "2. Merge consecutive speech from the same speaker into one conversational turn.\n"
        "3. Keep turns split when the other speaker speaks. Support interruptions.\n"
        "4. CRITICAL: NEVER invent, rewrite, summarize, or alter spoken words. Keep the exact transcript wording from the input.\n"
        "5. Return ONLY a valid JSON object: {\"turns\": [{\"speaker\": \"DOCTOR\"|\"PATIENT\", \"start\": float, \"end\": float, \"text\": string, \"overlap\": boolean}]}"
    )

    user_payload_str = json.dumps(window_payload, indent=2)
    models_to_try = [_PRIMARY_MODEL] + _FALLBACK_MODELS

    for model in models_to_try:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_payload_str}
                ],
                temperature=0.0,
                max_tokens=1024,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            if not raw_content or not raw_content.strip():
                continue

            parsed = json.loads(raw_content.strip())
            turns = parsed.get("turns") or parsed.get("utterances")
            if not turns or not isinstance(turns, list):
                continue

            # Validate anti-hallucination
            if not _validate_anti_hallucination(utterances, turns):
                print("  [WARN] LLM failed anti-hallucination check, falling back to local refiner")
                return local_rule_refine_window(window_payload)

            # Normalise speaker names
            clean_turns = []
            for t in turns:
                spk_str = str(t.get("speaker", "UNKNOWN")).strip().upper()
                if "DOC" in spk_str:
                    spk = "DOCTOR"
                elif "PAT" in spk_str:
                    spk = "PATIENT"
                else:
                    spk = "DOCTOR"

                clean_turns.append({
                    "speaker": spk,
                    "start": round(float(t.get("start", 0.0)), 2),
                    "end": round(float(t.get("end", 0.0)), 2),
                    "text": str(t.get("text", "")).strip(),
                    "overlap": bool(t.get("overlap", False))
                })

            print(f"  [OK] Groq 3-chunk window refined ({model}): {len(clean_turns)} turns")
            return {"turns": clean_turns}

        except Exception as e:
            print(f"  [WARN] Groq model {model} error: {e}")
            continue

    # Graceful local fallback
    print("  [INFO] Using local rule refiner for 3-chunk window")
    return local_rule_refine_window(window_payload)

