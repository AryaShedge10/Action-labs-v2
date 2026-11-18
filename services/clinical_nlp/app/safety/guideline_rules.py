"""Safety rules driven by the MoHFW STG Hypertension 2016 knowledge file (Table 10, combinations, BP crisis).

All thresholds, class lists and citations are read from rules/hypertension_stg_2016.yaml - nothing is hard-coded here,
so every alert can be traced to a PDF page. Only rules that appear in that PDF are implemented.
"""

from __future__ import annotations

from itertools import combinations

from ..dosing.bp import classify_bp, parse_bp
from ..dosing.knowledge import DoseKnowledge, Source, load_knowledge
from ..knowledge.drugs import classes_of
from ..models.schemas import (
    ClinicalEntity,
    Conflict,
    ConflictStatus,
    ConflictType,
    EntityStatus,
    EntityType,
    GuidelineCitation,
    Severity,
)
from ..safety.rules import SafetyContext, SafetyRule, evidence_of, min_confidence, status_for

DOCUMENT = "MoHFW India, Standard Treatment Guidelines: Hypertension (May 2016)"
_CONFIRMED = {EntityStatus.PRESENT, EntityStatus.CURRENT}
_UNCERTAIN = {EntityStatus.POSSIBLE, EntityStatus.HISTORICAL}


def cite(source: Source) -> GuidelineCitation:
    return GuidelineCitation(document=DOCUMENT, page=source.page, table_or_section=source.table_or_section)


def _kb(rule: SafetyRule) -> DoseKnowledge:
    return getattr(rule, "knowledge", None) or load_knowledge()


class GuidelineContraindicationRule(SafetyRule):
    rule_id = "GUIDELINE_CONTRAINDICATION"
    description = "Compelling contraindication to an antihypertensive class (STG Hypertension 2016, Table 10, p16)."

    def __init__(self, knowledge: DoseKnowledge | None = None):
        self.knowledge = knowledge

    def evaluate(self, ctx: SafetyContext) -> list[Conflict]:
        kb = _kb(self)
        conflicts: list[Conflict] = []
        diagnoses = ctx.entities.of_type(EntityType.DIAGNOSIS)
        egfr = [e for e in ctx.entities.of_type(EntityType.VITAL) if e.normalized == "egfr"]
        for group in kb.table_10_contraindications:
            meds = [m for m in ctx.candidate_medications() if classes_of(m.normalized) & set(group.classes)]
            if not meds:
                continue
            for item in group.compelling:
                if item.handled_by_existing_rule:
                    continue  # e.g. pregnancy is covered by PREGNANCY_CONTRAINDICATION
                triggers: list[tuple[ClinicalEntity, bool]] = []   # (entity, confirmed)
                for dx in diagnoses:
                    if dx.normalized in item.conditions and dx.status in _CONFIRMED | _UNCERTAIN:
                        triggers.append((dx, dx.status in _CONFIRMED))
                if item.egfr_below is not None:
                    for lab in egfr:
                        try:
                            if float(lab.value) < item.egfr_below:
                                triggers.append((lab, True))
                        except (TypeError, ValueError):
                            continue
                for trigger, confirmed in triggers:
                    for med in meds:
                        status = status_for(med, block=confirmed)
                        qualifier = "" if confirmed else f" (condition {trigger.status.value.lower()}; confirm)"
                        conflicts.append(Conflict(
                            rule_id=self.rule_id,
                            type=ConflictType.GUIDELINE_CONTRAINDICATION,
                            severity=Severity.HIGH,
                            status=status,
                            message=f"{med.display_name} ({group.group}) with {item.label}{qualifier}: "
                                    f"compelling contraindication per STG Hypertension 2016, Table 10 (p{item.source.page}).",
                            medication=med.display_name,
                            involved_terms=[trigger.normalized, med.normalized],
                            entity_ids=[trigger.entity_id, med.entity_id],
                            blocked_entity_ids=[med.entity_id] if status == ConflictStatus.BLOCKED else [],
                            evidence=evidence_of(trigger, med),
                            recommendation="Choose an agent without this contraindication, or document the clinical "
                                           "justification.",
                            confidence=min_confidence(trigger, med),
                            citations=[cite(item.source)],
                        ))
        return conflicts


class GuidelineCombinationRule(SafetyRule):
    rule_id = "GUIDELINE_COMBINATION"
    description = "Drug combinations the guideline advises against, and the simvastatin dose cap with amlodipine."

    def __init__(self, knowledge: DoseKnowledge | None = None):
        self.knowledge = knowledge

    def evaluate(self, ctx: SafetyContext) -> list[Conflict]:
        kb = _kb(self)
        meds = ctx.active_medications()
        conflicts: list[Conflict] = []
        for rule in kb.combination_rules:
            if rule.kind == "class_pair":
                conflicts.extend(self._class_pair(rule, meds))
            else:
                conflicts.extend(self._dose_cap(rule, meds))
        return conflicts

    def _class_pair(self, rule, meds) -> list[Conflict]:
        out = []
        for m1, m2 in combinations(meds, 2):
            c1, c2 = classes_of(m1.normalized), classes_of(m2.normalized)
            forward = c1 & set(rule.classes_a) and c2 & set(rule.classes_b)
            backward = c2 & set(rule.classes_a) and c1 & set(rule.classes_b)
            if m1.normalized == m2.normalized or not (forward or backward):
                continue
            out.append(Conflict(
                rule_id=self.rule_id,
                type=ConflictType.DRUG_INTERACTION,
                severity=Severity(rule.severity),
                status=ConflictStatus.REVIEW_REQUIRED,
                message=f"{m1.display_name} + {m2.display_name}: {rule.message} ({rule.label}).",
                medication=(m1 if m1.status in {EntityStatus.PRESCRIBED, EntityStatus.RECOMMENDED} else m2).display_name,
                involved_terms=[m1.normalized, m2.normalized],
                entity_ids=[m1.entity_id, m2.entity_id],
                evidence=evidence_of(m1, m2),
                recommendation="Review the combination against the guideline; document the reason if continued.",
                confidence=min_confidence(m1, m2),
                citations=[cite(rule.source)],
            ))
        return out

    def _dose_cap(self, rule, meds) -> list[Conflict]:
        drug_a = [m for m in meds if m.normalized == rule.drug_a]
        capped = [m for m in meds if m.normalized == rule.capped_drug]
        out = []
        for a in drug_a[:1]:
            for c in capped[:1]:
                daily = self._daily_dose_mg(c)
                if daily is not None and daily <= rule.max_daily_dose:
                    continue
                exceeded = daily is not None
                detail = (f"stated {c.display_name.lower()} dose is {daily:g} {rule.unit}/day, above the cap"
                          if exceeded else f"{c.display_name.lower()} daily dose is not documented")
                out.append(Conflict(
                    rule_id=self.rule_id,
                    type=ConflictType.DOSE_RANGE,
                    severity=Severity.HIGH if exceeded else Severity.MEDIUM,
                    status=ConflictStatus.REVIEW_REQUIRED,
                    message=f"{a.display_name} + {c.display_name}: {rule.message}; {detail}.",
                    medication=c.display_name,
                    involved_terms=[a.normalized, c.normalized],
                    entity_ids=[a.entity_id, c.entity_id],
                    evidence=evidence_of(a, c),
                    recommendation=f"Keep {c.display_name.lower()} at or below {rule.max_daily_dose:g} {rule.unit} per day.",
                    confidence=min_confidence(a, c),
                    citations=[cite(rule.source)],
                ))
        return out

    @staticmethod
    def _daily_dose_mg(med: ClinicalEntity) -> float | None:
        if "dose_mg" not in med.attributes:
            return None
        try:
            dose = float(med.attributes["dose_mg"])
            per_day = int(med.attributes.get("doses_per_day", 0) or 0)
        except ValueError:
            return None
        if per_day:
            return dose * per_day
        return dose if dose > 20 else None   # a single dose already over the cap is over; otherwise frequency unknown


class BPCrisisRule(SafetyRule):
    rule_id = "BP_CRISIS"
    description = "BP above 180/110 (Table 4): CRITICAL with an ABCDEFG warning symptom, otherwise review (urgency)."

    def __init__(self, knowledge: DoseKnowledge | None = None):
        self.knowledge = knowledge

    def evaluate(self, ctx: SafetyContext) -> list[Conflict]:
        kb = _kb(self)
        crisis = kb.hypertensive_crisis
        symptoms = self._warning_symptoms(ctx, crisis)
        conflicts: list[Conflict] = []
        seen: set[str] = set()
        for vital in ctx.entities.of_type(EntityType.VITAL):
            if vital.normalized != "blood pressure" or vital.value in seen:
                continue
            parsed = parse_bp(vital.value)
            if parsed is None:
                continue
            sbp, dbp = parsed
            if not (sbp > crisis.sbp_greater_than or dbp > crisis.dbp_greater_than):
                continue
            seen.add(vital.value)
            grade = classify_bp(sbp, dbp)
            reading = f"{sbp}/{dbp} mmHg ({grade.label}, Table 4)"
            if symptoms:
                names = ", ".join(sorted({f"{label} [{s.normalized}]" for s, label in symptoms}))
                conflicts.append(Conflict(
                    rule_id=self.rule_id,
                    type=ConflictType.HYPERTENSIVE_CRISIS,
                    severity=Severity.CRITICAL,
                    status=ConflictStatus.REVIEW_REQUIRED,
                    message=f"BP {reading} with ABCDEFG warning symptom(s): {names}. Treat as hypertensive emergency.",
                    involved_terms=["blood pressure", *sorted({s.normalized for s, _ in symptoms})],
                    entity_ids=[vital.entity_id, *[s.entity_id for s, _ in symptoms]],
                    evidence=evidence_of(vital, *[s for s, _ in symptoms]),
                    recommendation="Assess for acute target-organ damage and manage as a hypertensive emergency "
                                   "(parenteral therapy, not sublingual nifedipine).",
                    confidence=min_confidence(vital, *[s for s, _ in symptoms]),
                    citations=[cite(crisis.threshold_source), cite(crisis.emergency_rule_source),
                               cite(crisis.pathway_source)],
                ))
            else:
                conflicts.append(Conflict(
                    rule_id=self.rule_id,
                    type=ConflictType.HYPERTENSIVE_CRISIS,
                    severity=Severity.HIGH,
                    status=ConflictStatus.REVIEW_REQUIRED,
                    message=f"BP {reading} is above 180/110 with no ABCDEFG warning symptom documented in the "
                            f"transcript: possible hypertensive urgency - review.",
                    involved_terms=["blood pressure"],
                    entity_ids=[vital.entity_id],
                    evidence=evidence_of(vital),
                    recommendation="Actively check A-G (consciousness, breathlessness, chest pain, limb deficit/urine "
                                   "output, edema, fundus, seizures); absence in the transcript is not proof of absence.",
                    confidence=min_confidence(vital),
                    citations=[cite(crisis.threshold_source), cite(crisis.urgency_rule_source)],
                ))
        return conflicts

    @staticmethod
    def _warning_symptoms(ctx: SafetyContext, crisis) -> list[tuple[ClinicalEntity, str]]:
        wanted = {term: s.label for s in crisis.warning_symptoms for term in s.terms}
        found = []
        for e in ctx.entities.of_type(EntityType.SYMPTOM, EntityType.FINDING):
            if e.normalized in wanted and e.status in {EntityStatus.PRESENT, EntityStatus.POSSIBLE}:
                found.append((e, wanted[e.normalized]))
        return found
