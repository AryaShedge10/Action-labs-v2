"""Typed, validated view of rules/hypertension_stg_2016.yaml.

Loading fails loudly (pydantic ValidationError) if any fact has no `source.page`, if an unknown key
appears, or if a value has the wrong type - so a malformed knowledge file can never silently produce a
dose suggestion. The file is parsed once per process (`load_knowledge`).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

RULES_PATH = Path(__file__).resolve().parent / "rules" / "hypertension_stg_2016.yaml"
DOCUMENT_PAGES = 54


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(_Strict):
    page: int = Field(ge=1, le=DOCUMENT_PAGES)
    table_or_section: str = Field(min_length=1)
    quote: str | None = None


class Sourced(_Strict):
    source: Source
    corroborating_sources: list[Source] = Field(default_factory=list)


# --------------------------------------------------------------------------- document / header

class SourceDocument(_Strict):
    title: str
    issuer: str
    date: str
    file: str
    pages: int
    page_numbering: str
    population: str
    population_source: Source


class Discrepancy(_Strict):
    id: str
    description: str
    used: str
    sources: list[Source] = Field(min_length=1)


# --------------------------------------------------------------------------- blood pressure

class BPCategory(Sourced):
    label: str
    sbp_min: int
    dbp_min: int
    rank: int


class IsolatedSystolic(Sourced):
    sbp_min: int
    dbp_below: int
    label: str


class BPClassificationTable(_Strict):
    source: Source
    categories: list[BPCategory] = Field(min_length=1)
    isolated_systolic: IsolatedSystolic


class WarningSymptom(Sourced):
    letter: str
    label: str
    terms: list[str] = Field(min_length=1)


class HypertensiveCrisis(_Strict):
    sbp_greater_than: int
    dbp_greater_than: int
    threshold_source: Source
    emergency_rule_source: Source
    urgency_rule_source: Source
    pathway_source: Source
    warning_symptoms: list[WarningSymptom] = Field(min_length=1)


# --------------------------------------------------------------------------- Table 10, combinations

class ContraindicationItem(Sourced):
    id: str
    label: str
    conditions: list[str] = Field(default_factory=list)
    egfr_below: float | None = None
    handled_by_existing_rule: str | None = None


class ContraindicationGroup(_Strict):
    id: str
    group: str
    classes: list[str] = Field(min_length=1)
    compelling: list[ContraindicationItem] = Field(default_factory=list)
    possible: list[ContraindicationItem] = Field(default_factory=list)


class CombinationRule(Sourced):
    id: str
    kind: Literal["class_pair", "dose_cap"]
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    message: str
    classes_a: list[str] = Field(default_factory=list)
    classes_b: list[str] = Field(default_factory=list)
    label: str | None = None
    drug_a: str | None = None
    drug_b: str | None = None
    capped_drug: str | None = None
    max_daily_dose: float | None = None
    unit: str | None = None

    @model_validator(mode="after")
    def _check_kind(self) -> "CombinationRule":
        if self.kind == "class_pair" and not (self.classes_a and self.classes_b):
            raise ValueError(f"{self.id}: class_pair needs classes_a and classes_b")
        if self.kind == "dose_cap" and not (self.drug_a and self.drug_b and self.capped_drug
                                            and self.max_daily_dose and self.unit):
            raise ValueError(f"{self.id}: dose_cap needs drug_a, drug_b, capped_drug, max_daily_dose, unit")
        return self


class UnsupportedDrug(Sourced):
    name: str
    reason: str


# --------------------------------------------------------------------------- drugs

class ValueText(Sourced):
    value: str


class Dose(Sourced):
    value: float = Field(gt=0)
    unit: str
    note: str | None = None


class Frequency(Sourced):
    value: str
    doses_per_day_min: int = Field(ge=1)
    doses_per_day_max: int = Field(ge=1)


class Titration(Sourced):
    value: str
    min_days: int = Field(ge=1)
    max_days: int = Field(ge=1)


class DoseValue(_Strict):
    value: float = Field(gt=0)
    unit: str


class ConditionTest(_Strict):
    op: Literal["gt", "lt", "is_true", "other_drug_in_classes", "judgment", "none"]
    fact: str | None = None
    threshold: float | None = None
    classes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "ConditionTest":
        if self.op in ("gt", "lt") and (self.fact is None or self.threshold is None):
            raise ValueError("gt/lt tests need fact and threshold")
        if self.op == "is_true" and self.fact is None:
            raise ValueError("is_true tests need fact")
        if self.op == "other_drug_in_classes" and not (self.fact and self.classes):
            raise ValueError("other_drug_in_classes needs fact and classes")
        return self


class LowerStartCondition(Sourced):
    id: str
    description: str
    test: ConditionTest
    start_dose: DoseValue
    age_definition_source: Source | None = None


class RenalAdjustment(Sourced):
    id: str
    description: str
    test: ConditionTest
    effect: Literal["set_dose", "avoid"] | None = None
    start_dose: DoseValue | None = None
    frequency: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def _check(self) -> "RenalAdjustment":
        if self.test.op != "none" and self.effect is None:
            raise ValueError(f"{self.id}: active renal test needs an effect")
        if self.effect == "set_dose" and self.start_dose is None:
            raise ValueError(f"{self.id}: set_dose needs start_dose")
        return self


class HepaticRule(Sourced):
    effect: Literal["lower_start", "warning"]
    text: str


class DrugContraindication(Sourced):
    id: str
    text: str
    conditions: list[str] = Field(min_length=1)


class Caution(Sourced):
    text: str


class PregnancyRule(Sourced):
    effect: Literal["warning", "contraindicated", "not_recommended"]
    text: str


class DrugEntry(_Strict):
    generic_name: str
    names: list[str] = Field(min_length=1)
    drug_class: str
    evidence_tier: Literal["formulary", "dose_table_only"]
    class_label: ValueText | None = None
    indication: ValueText | None = None
    start_dose: Dose
    frequency: Frequency
    max_daily_dose: Dose
    usual_ceiling_dose: Dose | None = None
    titration_interval: Titration | None = None
    lower_start_conditions: list[LowerStartCondition] = Field(default_factory=list)
    renal_adjustments: list[RenalAdjustment] = Field(default_factory=list)
    hepatic: HepaticRule | None = None
    contraindications: list[DrugContraindication] = Field(default_factory=list)
    cautions: list[Caution] = Field(default_factory=list)
    pregnancy: PregnancyRule | None = None

    @model_validator(mode="after")
    def _check_doses(self) -> "DrugEntry":
        if self.start_dose.unit != self.max_daily_dose.unit:
            raise ValueError(f"{self.generic_name}: start and max dose units differ")
        if self.start_dose.value > self.max_daily_dose.value:
            raise ValueError(f"{self.generic_name}: start dose exceeds max daily dose")
        for cond in self.lower_start_conditions:
            if cond.start_dose.unit != self.start_dose.unit or cond.start_dose.value >= self.start_dose.value:
                raise ValueError(f"{self.generic_name}/{cond.id}: lower start dose must be lower, same unit")
        return self


class DoseKnowledge(_Strict):
    schema_version: int
    reviewed_by_clinician: bool
    source_document: SourceDocument
    document_discrepancies: list[Discrepancy] = Field(default_factory=list)
    bp_classification: BPClassificationTable
    hypertensive_crisis: HypertensiveCrisis
    table_10_contraindications: list[ContraindicationGroup]
    combination_rules: list[CombinationRule]
    unsupported_drugs: list[UnsupportedDrug] = Field(default_factory=list)
    drugs: dict[str, DrugEntry]

    @model_validator(mode="after")
    def _unique_names(self) -> "DoseKnowledge":
        seen: dict[str, str] = {}
        for key, drug in self.drugs.items():
            for name in drug.names:
                lowered = name.lower()
                if lowered in seen and seen[lowered] != key:
                    raise ValueError(f"name {name!r} maps to both {seen[lowered]} and {key}")
                seen[lowered] = key
        return self

    def drug_for_name(self, name: str) -> DrugEntry | None:
        wanted = name.strip().lower()
        for drug in self.drugs.values():
            if wanted in (n.lower() for n in drug.names) or wanted == drug.generic_name.lower():
                return drug
        return None

    def unsupported_note(self, name: str) -> UnsupportedDrug | None:
        wanted = name.strip().lower()
        return next((u for u in self.unsupported_drugs if u.name.lower() == wanted), None)


@lru_cache(maxsize=4)
def load_knowledge(path: str | Path = RULES_PATH) -> DoseKnowledge:
    """Parse and validate the knowledge file once; the result is immutable for the process lifetime."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return DoseKnowledge.model_validate(raw)
