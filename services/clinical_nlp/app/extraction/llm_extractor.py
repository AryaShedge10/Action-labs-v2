"""LLM-based extraction whose every output is verified against the transcript.

The model cites a segment id and a verbatim quote. We keep an entity only if the quote is
really in that segment, it is not taken from a question, and (for diagnoses) the term itself
was actually said. Timestamps and hashes are attached by our code, never by the model.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from ..knowledge.drugs import ALLERGEN_CLASS_TERMS, BRAND_TO_GENERIC, is_known_drug, resolve_brand
from ..knowledge.terms import LAY_TERMS, SYMPTOMS
from ..models.schemas import ClinicalEntity, EntityStatus, EntityType, Evidence, Transcript
from ..nlp.matcher import LexiconMatcher, clinical_matcher
from ..nlp.text import split_sentences, tokens
from ..privacy.phi import PHIRedactor
from ..utils.llm import LLMError, LLMUnavailableError, OllamaClient
from .llm_schema import extraction_json_schema

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a clinical information extraction engine. Extract clinical facts from the doctor-patient transcript below.
The transcript is automatic speech recognition (ASR) output: words may be misspelled or garbled, and speakers may use
lay terms, Indian brand names, or a few Hindi words.

Rules:
1. Extract ONLY facts explicitly stated. Never infer a diagnosis the clinician did not say.
2. Every entity cites exactly ONE segment_id and a "quote" (3-15 words) copied VERBATIM, character for character, from
   that segment. Never paraphrase, correct, translate or invent a quote; if you cannot quote it, omit the entity.
3. Questions asked by the doctor are not facts; use the patient's answer instead.
4. Negated or denied items have status ABSENT. Items about family members have status FAMILY_MEMBER.
   Double negatives cancel out: "I can't deny the cough" / "can't say I don't have a cough" means the cough is PRESENT.
5. "surface_text" is the words exactly as transcribed (misspellings kept). "normalized" is the clean clinical term.
6. Drugs: correct misspelled or ASR-garbled drug names to the proper generic name in "normalized"
   (e.g. "penicilin" -> penicillin, "amoxicilin" -> amoxicillin). Map brand names to generics using this table
   (use the generic name; for a combination product output one MEDICATION entity per generic):
{brand_map}
   If you do not recognise a drug name, keep it as spoken in "normalized"; do not guess a generic.
7. Symptoms: map lay or Hindi phrases to the clinical term. Use these canonical symptom names where one fits:
{symptom_vocab}
   Lay phrase examples:
{lay_terms}
8. An allergy is type ALLERGY with the allergen as "normalized". Never list an allergen as a MEDICATION.
   A described adverse reaction to a NAMED drug (hives, rash, swelling of face/lips, breathing trouble after taking it)
   is an ALLERGY entity for that drug with status PRESENT; put the reaction in attributes {{"reaction": "..."}}.
   Do NOT also list the reaction as a current SYMPTOM. Quote the words that describe the reaction.
9. Medication status: CURRENT (patient already takes it), PRESCRIBED (clinician prescribes it now),
   RECOMMENDED (advised, e.g. over the counter), STOPPED, HISTORICAL, ABSENT (explicitly avoided or not taken).
10. For VITAL put the number in "value" and the unit in "unit". For MEDICATION put dose, frequency, duration,
   route in "attributes". For DEMOGRAPHIC use normalized "sex" or "age" with the value in "value".
11. Bracketed tokens such as [NAME_1] are redacted personal data; never output them.
12. One entity per fact: never join two items ("fever and headache"). "normalized" is ONE clean term with no dose,
   frequency, quantity or filler words ("allergic to", "syrup"); put those details in "attributes".

Output must match the provided JSON schema. Example entity:
{{"type": "SYMPTOM", "surface_text": "sore throat", "normalized": "sore throat", "status": "PRESENT", "segment_id": "S002",
  "quote": "I've had a severe sore throat", "value": null, "unit": null, "attributes": {{}}}}

Transcript:
{transcript}
"""


def build_prompt(transcript_text: str) -> str:
    """Fill the prompt; vocabulary comes from the knowledge base so it is never hard-coded here."""
    brand_map = "\n".join(f"   {brand} -> {' + '.join(generics)}" for brand, generics in sorted(BRAND_TO_GENERIC.items()))
    lay_terms = "\n".join(f'   "{lay}" -> {clinical}' for lay, clinical in LAY_TERMS.items())
    return EXTRACTION_PROMPT.format(brand_map=brand_map, symptom_vocab="   " + ", ".join(sorted(SYMPTOMS)),
                                    lay_terms=lay_terms, transcript=transcript_text)


_VITAL_NAMES = {
    "temp": "temperature", "temperature": "temperature", "body temperature": "temperature",
    "bp": "blood pressure", "blood pressure": "blood pressure", "hr": "heart rate", "pulse": "heart rate",
    "heart rate": "heart rate", "rr": "respiratory rate", "respiratory rate": "respiratory rate",
    "spo2": "oxygen saturation", "oxygen saturation": "oxygen saturation", "o2 saturation": "oxygen saturation",
    "weight": "weight",
}


@dataclass
class LLMExtractionResult:
    entities: list[ClinicalEntity] = field(default_factory=list)
    proposed: int = 0
    rejected: list[str] = field(default_factory=list)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("’", "'")).strip()


class LLMExtractor:
    def __init__(self, client: OllamaClient, matcher: LexiconMatcher | None = None, redact_phi: bool = True):
        self.client = client
        self.matcher = matcher or clinical_matcher()
        self.redact_phi = redact_phi

    def render_transcript(self, transcript: Transcript) -> str:
        redactor = PHIRedactor()
        lines = []
        for s in transcript.segments:
            text = redactor.redact(s.text) if self.redact_phi else s.text
            lines.append(f"[{s.segment_id}] {s.speaker.value} ({s.start_time:.1f}s): {text}")
        return "\n".join(lines)

    def _request(self, prompt: str) -> dict:
        """Ask for schema-constrained JSON; retry once on a malformed / non-conforming response."""
        schema = extraction_json_schema()
        last: LLMError | None = None
        for attempt in (1, 2):
            try:
                data = self.client.generate_json(prompt, schema=schema)
            except LLMUnavailableError:
                raise
            except LLMError as exc:
                last = exc
            else:
                if isinstance(data, dict) and isinstance(data.get("entities"), list):
                    return data
                last = LLMError("LLM response did not match the extraction schema")
            logger.warning("LLM extraction attempt %d failed schema validation", attempt)
        raise last or LLMError("LLM extraction failed")

    def extract(self, transcript: Transcript) -> LLMExtractionResult:
        data = self._request(build_prompt(self.render_transcript(transcript)))
        items = data["entities"]
        result = LLMExtractionResult(proposed=len(items))
        for item in items:
            entities, reason = self._verify(item, transcript)
            if entities:
                result.entities.extend(entities)
            else:
                result.rejected.append(reason)
                logger.info("LLM entity rejected: %s", reason)
        return result

    # ------------------------------------------------------------------ verification

    def _verify(self, item: object, transcript: Transcript) -> tuple[list[ClinicalEntity], str]:
        """Returns the verified entities (several for a combination brand such as Combiflam) or a rejection reason."""
        if not isinstance(item, dict):
            return [], "non-object entity"
        try:
            etype = EntityType(str(item.get("type", "")).upper())
        except ValueError:
            return [], f"unknown type {item.get('type')!r}"
        surface = str(item.get("surface_text") or item.get("name") or "").strip()   # "name" = legacy field
        proposed = str(item.get("normalized") or item.get("name") or surface).strip()
        if not surface or "[" in surface or "[" in proposed:
            return [], "missing or redacted name"
        segment = transcript.segment(str(item.get("segment_id", "")).strip())
        if segment is None:
            return [], f"invalid segment_id {item.get('segment_id')!r} for {surface!r}"

        quote = self._locate_quote(str(item.get("quote") or ""), segment.text)
        if quote is None:
            return [], f"quote for {surface!r} not found in {segment.segment_id}"
        sentence = next((s for s in split_sentences(segment.text) if quote in s.text or s.text in quote), None)
        if sentence is not None and sentence.is_question:
            return [], f"{surface!r} cited from a question"

        extra: dict[str, str] = {}
        value: str | None
        if etype in (EntityType.MEDICATION, EntityType.ALLERGY):
            names, extra = self._resolve_drug(etype, surface, proposed)
            value = str(item.get("value")).strip() if item.get("value") not in (None, "") else None
        else:
            normalized, value = self._normalize(etype, proposed, item.get("value"))
            if normalized is None:
                return [], f"could not normalise {surface!r}"
            names = [normalized]
        mentioned = self._term_in_text(etype, names[0], surface, segment.text)
        if etype == EntityType.DIAGNOSIS and not mentioned:
            return [], f"diagnosis {surface!r} was not stated in {segment.segment_id}"

        try:
            status = EntityStatus(str(item.get("status", "UNKNOWN")).upper())
        except ValueError:
            status = EntityStatus.UNKNOWN
        attrs = item.get("attributes") if isinstance(item.get("attributes"), dict) else {}
        attrs = {str(k): str(v) for k, v in attrs.items() if v not in (None, "", [], {})}
        attrs.update(extra)
        asr = segment.confidence if segment.confidence is not None else 1.0
        conf = (0.75 if mentioned else 0.55) * asr
        if extra.get("unknown_drug"):
            conf = min(conf, 0.5)
        unit = item.get("unit")
        entities = [
            ClinicalEntity(
                type=etype,
                text=surface,
                normalized=name,
                status=status,
                value=value,
                unit=str(unit) if unit else None,
                attributes=dict(attrs),
                evidence=[Evidence.from_segment(segment, quote)],
                confidence=round(conf, 3),
                source="llm",
                status_history=[status],
            )
            for name in names
        ]
        return entities, ""

    def _resolve_drug(self, etype: EntityType, surface: str, proposed: str) -> tuple[list[str], dict[str, str]]:
        """Canonical generic name(s) for a drug / allergen, plus attributes.

        Known generic or alias -> that generic. Known brand -> its generic(s) (+ `brand` attribute).
        Allergen class term / non-drug allergen -> kept. Anything else -> kept as spoken and flagged
        `unknown_drug`, which the pipeline turns into REVIEW_REQUIRED.
        """
        for candidate in (proposed, surface):
            low = _norm(candidate)
            if etype == EntityType.ALLERGY and low in ALLERGEN_CLASS_TERMS:
                return [low], {}
            canonical = self.matcher.canonical(EntityType.MEDICATION, low)
            if canonical:
                return [canonical], {}
            generics = resolve_brand(low)
            if generics:
                return list(generics), {"brand": candidate}
        # The model sometimes pads the name ("codeine syrup", "ibuprofen 600 mg twice daily", "allergic to sulfa
        # drugs"): accept it only if exactly one known drug / allergen class term is inside the phrase.
        for candidate in (proposed, surface):
            low = _norm(candidate)
            if etype == EntityType.ALLERGY:
                terms = {t for t in ALLERGEN_CLASS_TERMS if re.search(rf"\b{re.escape(t)}\b", low)}
                if terms and len({ALLERGEN_CLASS_TERMS[t] for t in terms}) == 1:    # "sulfa" + "sulfa drugs" = one class
                    return [max(terms, key=len)], {}
            found = {m.canonical for m in self.matcher.find(low, {EntityType.MEDICATION})}
            if len(found) == 1:
                return [found.pop()], {}
        low = _norm(proposed)
        if is_known_drug(low):
            return [low], {}
        return [low], {"unknown_drug": "True"}

    @staticmethod
    def _locate_quote(quote: str, segment_text: str) -> str | None:
        q, t = _norm(quote), _norm(segment_text)
        if not q:
            return None
        idx = t.find(q)
        if idx != -1:
            return segment_text[idx:idx + len(q)] if _norm(segment_text[idx:idx + len(q)]) == q else segment_text
        q_tokens = tokens(q)
        if q_tokens and sum(tok in set(tokens(t)) for tok in q_tokens) / len(q_tokens) >= 0.8:
            return segment_text
        return None

    def _normalize(self, etype: EntityType, name: str, value: object) -> tuple[str | None, str | None]:
        lowered = _norm(name)
        value_str = str(value).strip() if value not in (None, "") else None
        if etype == EntityType.DEMOGRAPHIC:
            if lowered in ("male", "female", "man", "woman"):
                return "sex", "male" if lowered in ("male", "man") else "female"
            if lowered == "sex" and value_str:
                v = value_str.lower()
                return "sex", "male" if v in ("male", "m", "man") else "female" if v in ("female", "f", "woman") else v
            if "age" in lowered and value_str and re.match(r"^\d{1,3}", value_str):
                return "age", re.match(r"^\d{1,3}", value_str).group()
            return None, None
        if etype == EntityType.VITAL:
            return _VITAL_NAMES.get(lowered, lowered), value_str
        if etype == EntityType.ALLERGY:
            if lowered in ALLERGEN_CLASS_TERMS:
                return lowered, value_str
            canonical = self.matcher.canonical(EntityType.MEDICATION, lowered)
            return canonical or lowered, value_str
        canonical = self.matcher.canonical(etype, lowered)
        if canonical:
            return canonical, value_str
        found = [m for m in self.matcher.find(name) if m.type == etype]
        return (found[0].canonical if len(found) == 1 else lowered), value_str

    def _term_in_text(self, etype: EntityType, normalized: str, name: str, text: str) -> bool:
        if _norm(name) in _norm(text) or normalized in _norm(text):
            return True
        if etype in (EntityType.VITAL, EntityType.DEMOGRAPHIC):
            return True
        lookup_type = EntityType.MEDICATION if etype == EntityType.ALLERGY else etype
        return any(m.canonical == normalized for m in self.matcher.find(text, {lookup_type}))
