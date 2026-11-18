"""Deterministic dose-suggestion engine.

No LLM and no remembered values: every number comes from the validated knowledge file
(rules/hypertension_stg_2016.yaml). Fail closed: a missing patient fact yields NEEDS_INFO, an unknown drug yields
NOT_SUPPORTED, and conflicts found by the existing safety engine yield NOT_RECOMMENDED.
"""

from __future__ import annotations

from ..knowledge.drugs import DRUGS, _DOSE_SUFFIX, classes_of, drug_aliases, resolve_brand
from ..models.schemas import (
    ClinicalEntity,
    Conflict,
    ConflictStatus,
    EntitySet,
    EntityStatus,
    EntityType,
    Severity,
    Transcript,
)
from ..safety.engine import SafetyEngine
from .knowledge import DoseKnowledge, DrugEntry, Source, load_knowledge
from .models import DoseCitation, DoseStatus, DoseSuggestion, PatientContext

_CONTEXT_CONDITIONS_NOTE = ("Conditions are checked only against the documented list; absence from the list is not "
                            "confirmation - confirm history (e.g. gout, asthma, AV block) with the patient.")
_BLOCKING_SEVERITIES = {Severity.HIGH, Severity.CRITICAL}


def canonical_name(name: str) -> list[str]:
    """Resolve a typed drug name / brand to canonical generic name(s) using the existing knowledge base."""
    key = _DOSE_SUFFIX.sub("", name.strip().lower())
    if not key:
        return []
    brands = resolve_brand(key)
    if brands:
        return list(brands)
    return [drug_aliases().get(key, key)]


def _entity_name(generic: str) -> str:
    if generic in DRUGS:
        return generic
    first = generic.split()[0]
    return first if first in DRUGS else generic


class DoseEngine:
    def __init__(self, knowledge: DoseKnowledge | None = None, safety: SafetyEngine | None = None):
        self.kb = knowledge or load_knowledge()
        self.safety = safety or SafetyEngine()

    # ------------------------------------------------------------------ public

    def suggest(self, drug: str, patient: PatientContext) -> DoseSuggestion:
        base = dict(drug=drug, knowledge_source=f"{self.kb.source_document.issuer}, {self.kb.source_document.title} "
                    f"({self.kb.source_document.date})", reviewed_by_clinician=self.kb.reviewed_by_clinician,
                    patient_context=patient)
        resolved = self._resolve(drug)
        if isinstance(resolved, DoseSuggestion):
            return resolved.model_copy(update=base)
        entry = resolved
        if patient.age_years is not None and patient.age_years < 18:
            return DoseSuggestion(status=DoseStatus.NOT_SUPPORTED, resolved_drug=entry.generic_name,
                                  reasons=["The source guideline covers adults only (age < 18 years)."],
                                  citations=[self._cite(self.kb.source_document.population_source, "adult population")],
                                  **base)

        citations: dict[tuple, DoseCitation] = {}
        warnings: list[str] = []
        reasons: list[str] = []

        # 1. existing safety engine: allergies, interactions, pregnancy, Table 10, combination rules
        conflicts = self._safety_conflicts(entry, patient)
        engine_pregnancy_block = False
        for c in conflicts:
            text = f"{c.message}" + (f" {c.recommendation}" if c.recommendation else "")
            for g in c.citations:
                self._add(citations, DoseCitation(page=g.page, table_or_section=g.table_or_section,
                                                  supports=f"safety rule {c.rule_id}"))
            if c.status == ConflictStatus.BLOCKED or c.severity in _BLOCKING_SEVERITIES:
                reasons.append(f"[{c.rule_id}] {text}")
                engine_pregnancy_block |= c.rule_id == "PREGNANCY_CONTRAINDICATION"
            else:
                warnings.append(f"[{c.rule_id}] {text}")

        # 2. drug-specific rules from the knowledge file
        self._pregnancy(entry, patient, reasons, warnings, citations, engine_pregnancy_block)
        self._hepatic_warning(entry, patient, warnings, citations)
        self._renal_avoid(entry, patient, reasons, citations)
        self._drug_contraindications(entry, patient, reasons, citations)
        self._possible_contraindications(entry, patient, warnings, citations)
        for caution in entry.cautions:
            warnings.append(f"Caution: {caution.text}")
            self._add(citations, self._cite(caution.source, "caution"))
        if self._already_on(entry, patient):
            warnings.append(f"Patient is already recorded as taking {entry.generic_name}; a starting dose may not apply.")
        if patient.conditions is not None:
            warnings.append(_CONTEXT_CONDITIONS_NOTE)

        missing = self._missing(entry, patient)
        common = dict(resolved_drug=entry.generic_name, needs_info=missing, **base)

        if reasons:
            return DoseSuggestion(status=DoseStatus.NOT_RECOMMENDED, reasons=_dedupe(reasons),
                                  warnings=_dedupe(warnings), citations=list(citations.values()), **common)
        if missing:
            return DoseSuggestion(status=DoseStatus.NEEDS_INFO, warnings=_dedupe(warnings),
                                  citations=list(citations.values()), **common)

        start, unit, frequency, applied = self._dose(entry, patient, warnings, citations)
        self._add(citations, self._cite(entry.start_dose.source, "start dose"))
        self._add(citations, self._cite(entry.frequency.source, "frequency"))
        self._add(citations, self._cite(entry.max_daily_dose.source, "maximum daily dose"))
        titration = None
        if entry.titration_interval:
            titration = entry.titration_interval.value
            self._add(citations, self._cite(entry.titration_interval.source, "titration interval"))
        if entry.pregnancy is None and patient.pregnant:
            warnings.append("The source guideline has no pregnancy statement for this drug.")
        return DoseSuggestion(
            status=DoseStatus.SUGGESTED, start_dose=start, unit=unit, frequency=frequency,
            max_daily_dose=entry.max_daily_dose.value, titration_interval=titration, adjustments_applied=applied,
            warnings=_dedupe(warnings), citations=list(citations.values()), **common)

    # ------------------------------------------------------------------ resolution

    def _resolve(self, drug: str) -> DrugEntry | DoseSuggestion:
        def unsupported(reason: str, source: Source | None = None) -> DoseSuggestion:
            cites = [self._cite(source, "why unsupported")] if source else []
            return DoseSuggestion(status=DoseStatus.NOT_SUPPORTED, drug=drug, reasons=[reason], citations=cites)

        if not drug or not drug.strip():
            return unsupported("No drug name supplied.")
        names = canonical_name(drug)
        if len(names) > 1:
            return unsupported(f"'{drug}' is a combination product ({' + '.join(names)}); the guideline gives "
                               "single-drug doses only.")
        for candidate in (drug.strip().lower(), names[0]):
            note = self.kb.unsupported_note(candidate)
            if note:
                return unsupported(note.reason, note.source)
            entry = self.kb.drug_for_name(candidate)
            if entry:
                return entry
        return unsupported(f"'{drug}' has no dosing entry in the source guideline (Standard Treatment Guidelines: "
                           "Hypertension, 2016).")

    # ------------------------------------------------------------------ safety engine reuse

    def _safety_conflicts(self, entry: DrugEntry, p: PatientContext) -> list[Conflict]:
        items: list[ClinicalEntity] = []

        def add(type_, normalized, status=EntityStatus.PRESENT, **kw):
            items.append(ClinicalEntity(entity_id=f"D{len(items) + 1:03d}", type=type_, text=normalized,
                                        normalized=normalized, status=status, confidence=1.0, **kw))
            return items[-1]

        if p.age_years is not None:
            add(EntityType.DEMOGRAPHIC, "age", value=str(int(p.age_years)), attributes={"basis": "stated"})
        if p.sex:
            add(EntityType.DEMOGRAPHIC, "sex", value=p.sex.lower(), attributes={"basis": "stated"})
        if p.pregnant:
            add(EntityType.DIAGNOSIS, "pregnancy")
        for cond in p.conditions or []:
            if cond.strip().lower() != "pregnancy":
                add(EntityType.DIAGNOSIS, cond.strip().lower())
        for allergy in p.allergies or []:
            for name in canonical_name(allergy.lower().replace(" allergy", "")):
                add(EntityType.ALLERGY, name)
        for med in p.current_medications or []:
            for name in canonical_name(med):
                add(EntityType.MEDICATION, name, EntityStatus.CURRENT)
        candidate = add(EntityType.MEDICATION, _entity_name(entry.generic_name), EntityStatus.PRESCRIBED)
        transcript = Transcript(consultation_id="dose-check", source_format="dose-check", segments=[], sha256="")
        result = self.safety.run(EntitySet(items=items), transcript)
        return [c for c in result.conflicts if candidate.entity_id in c.entity_ids]

    # ------------------------------------------------------------------ knowledge-file rules

    def _pregnancy(self, entry, p, reasons, warnings, citations, engine_blocked):
        rule = entry.pregnancy
        if rule is None or not p.pregnant:
            return
        self._add(citations, self._cite(rule.source, "pregnancy"))
        if rule.effect == "warning":
            warnings.append(f"Pregnancy: {rule.text}")
        elif rule.effect == "not_recommended" or (rule.effect == "contraindicated" and not engine_blocked):
            reasons.append(f"Pregnancy: {rule.text}")

    def _hepatic_warning(self, entry, p, warnings, citations):
        if entry.hepatic and entry.hepatic.effect == "warning" and p.hepatic_impairment:
            warnings.append(f"Hepatic impairment: {entry.hepatic.text}")
            self._add(citations, self._cite(entry.hepatic.source, "hepatic impairment"))

    def _renal_avoid(self, entry, p, reasons, citations):
        for r in entry.renal_adjustments:
            if r.effect == "avoid" and self._test(r.test, entry, p) is True:
                reasons.append(f"Renal: {r.text}")
                self._add(citations, self._cite(r.source, "renal impairment"))

    def _drug_contraindications(self, entry, p, reasons, citations):
        for c in entry.contraindications:
            hits = _matching(p.conditions, c.conditions)
            if hits:
                reasons.append(f"Contraindication ({', '.join(hits)}): {c.text}")
                self._add(citations, self._cite(c.source, "contraindication"))

    def _possible_contraindications(self, entry, p, warnings, citations):
        for group in self.kb.table_10_contraindications:
            if entry.drug_class not in group.classes:
                continue
            for item in group.possible:
                hits = _matching(p.conditions, item.conditions)
                if hits:
                    warnings.append(f"Possible contraindication ({', '.join(hits)}): {group.group} - {item.label}")
                    self._add(citations, self._cite(item.source, "possible contraindication"))

    # ------------------------------------------------------------------ facts and dose

    def _missing(self, entry: DrugEntry, p: PatientContext) -> list[str]:
        needed: list[str] = ["age_years", "allergies", "current_medications", "conditions"]
        for c in entry.lower_start_conditions:
            if c.test.fact:
                needed.append(c.test.fact)
        for r in entry.renal_adjustments:
            if r.test.op != "none" and r.test.fact:
                needed.append(r.test.fact)
        if entry.hepatic:
            needed.append("hepatic_impairment")
        pregnancy_relevant = entry.pregnancy is not None or any(
            entry.drug_class in g.classes and any(i.id == "pregnancy" for i in g.compelling)
            for g in self.kb.table_10_contraindications)
        missing = []
        for fact in dict.fromkeys(needed):
            if getattr(p, fact, None) is None:
                missing.append(fact)
        if pregnancy_relevant and p.pregnant is None and (p.sex or "").lower() != "male":
            missing.append("pregnant (or sex = male)")
        return missing

    def _dose(self, entry: DrugEntry, p: PatientContext, warnings, citations):
        start, frequency, applied = entry.start_dose.value, entry.frequency.value, []
        for cond in entry.lower_start_conditions:
            if cond.test.op == "judgment":
                warnings.append(f"Guideline permits a lower start dose of {cond.start_dose.value:g} {cond.start_dose.unit}: "
                                f"{cond.description}. Not applied automatically - clinician judgment.")
                self._add(citations, self._cite(cond.source, f"lower start dose ({cond.id}), judgment only"))
            elif self._test(cond.test, entry, p) is True:
                if cond.start_dose.value < start:
                    start = cond.start_dose.value
                applied.append(f"{cond.description}: start {cond.start_dose.value:g} {cond.start_dose.unit} "
                               f"(p{cond.source.page})")
                self._add(citations, self._cite(cond.source, f"lower start dose ({cond.id})"))
                if cond.age_definition_source:
                    self._add(citations, self._cite(cond.age_definition_source, "definition of elderly"))
        for r in entry.renal_adjustments:
            if r.effect == "set_dose" and self._test(r.test, entry, p) is True:
                start = min(start, r.start_dose.value)
                frequency = r.frequency or frequency
                applied.append(f"{r.description}: {r.start_dose.value:g} {r.start_dose.unit} {r.frequency or ''}".strip()
                               + f" (p{r.source.page})")
                self._add(citations, self._cite(r.source, "renal adjustment"))
        return start, entry.start_dose.unit, frequency, applied

    def _test(self, test, entry: DrugEntry, p: PatientContext) -> bool | None:
        """True/False, or None when the needed fact is unknown or the test is not machine-evaluable."""
        if test.op in ("judgment", "none"):
            return None
        value = getattr(p, test.fact, None)
        if value is None:
            return None
        if test.op == "gt":
            return float(value) > test.threshold
        if test.op == "lt":
            return float(value) < test.threshold
        if test.op == "is_true":
            return bool(value)
        if test.op == "other_drug_in_classes":
            own = {entry.generic_name, _entity_name(entry.generic_name)}
            for med in value:
                for name in canonical_name(med):
                    if name not in own and classes_of(name) & set(test.classes):
                        return True
            return False
        return None

    def _already_on(self, entry: DrugEntry, p: PatientContext) -> bool:
        own = {entry.generic_name, _entity_name(entry.generic_name)}
        return any(n in own for m in p.current_medications or [] for n in canonical_name(m))

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _cite(source: Source, supports: str) -> DoseCitation:
        return DoseCitation(page=source.page, table_or_section=source.table_or_section, quote=source.quote,
                            supports=supports)

    @staticmethod
    def _add(store: dict, citation: DoseCitation) -> None:
        store.setdefault((citation.page, citation.table_or_section, citation.supports), citation)


def _matching(conditions: list[str] | None, wanted: list[str]) -> list[str]:
    found = []
    for cond in conditions or []:
        low = cond.strip().lower()
        if low and any(w == low or w in low for w in wanted if w):
            found.append(cond)
    return found


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
