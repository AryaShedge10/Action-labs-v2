"""Deterministic dose engine: every rule path of every supported drug. Expected numbers are the values printed in
the PDF (see rules/hypertension_stg_2016.yaml for page references)."""

import pytest

from app.dosing.engine import DoseEngine
from app.dosing.models import DISCLAIMER, DoseStatus, PatientContext

engine = DoseEngine()

BASE = dict(age_years=40, sex="male", weight_kg=70, pregnant=None, creatinine_clearance_ml_min=90,
            hepatic_impairment=False, conditions=[], current_medications=[], allergies=[])


def ctx(**over) -> PatientContext:
    return PatientContext(**{**BASE, **over})


def suggest(drug, **over):
    return engine.suggest(drug, ctx(**over))


def female(**over):
    return {"sex": "female", "pregnant": False, **over}


# ---------------------------------------------------------------- common contract

def test_every_result_carries_disclaimer_and_provenance():
    for drug in ("amlodipine", "ibuprofen"):
        r = suggest(drug)
        assert "not for clinical use" in r.disclaimer.lower() and r.disclaimer == DISCLAIMER
        assert r.reviewed_by_clinician is False
        assert "Ministry of Health" in r.knowledge_source


def test_suggested_result_has_citations_with_pages():
    r = suggest("amlodipine")
    assert r.status == DoseStatus.SUGGESTED
    supports = {c.supports for c in r.citations}
    assert {"start dose", "maximum daily dose", "frequency"} <= supports
    assert all(c.page >= 1 for c in r.citations)
    assert any(c.page == 47 for c in r.citations)


# ---------------------------------------------------------------- amlodipine (p47-48)

def test_amlodipine_default():
    r = suggest("amlodipine")
    assert (r.status, r.start_dose, r.unit, r.frequency, r.max_daily_dose) == (
        DoseStatus.SUGGESTED, 5, "mg", "once daily", 10)
    assert r.titration_interval == "7-14 days" and r.adjustments_applied == []


@pytest.mark.parametrize("age,expected", [(60, 5), (61, 2.5), (80, 2.5)])
def test_amlodipine_elderly_threshold(age, expected):
    assert suggest("amlodipine", age_years=age).start_dose == expected


def test_amlodipine_hepatic_impairment_lowers_start():
    r = suggest("amlodipine", hepatic_impairment=True)
    assert r.start_dose == 2.5 and any("Hepatic" in a for a in r.adjustments_applied)


def test_amlodipine_added_to_other_antihypertensive():
    r = suggest("amlodipine", current_medications=["enalapril"])
    assert r.start_dose == 2.5 and any("added to another" in a for a in r.adjustments_applied)


def test_amlodipine_other_class_medication_does_not_lower_dose():
    assert suggest("amlodipine", current_medications=["metformin"]).start_dose == 5


def test_amlodipine_no_renal_adjustment():
    assert suggest("amlodipine", creatinine_clearance_ml_min=10).start_dose == 5


def test_amlodipine_small_patient_is_a_warning_not_an_automatic_change():
    r = suggest("amlodipine", weight_kg=40)
    assert r.start_dose == 5 and any("small" in w.lower() for w in r.warnings)


def test_amlodipine_multiple_reasons_take_lowest():
    r = suggest("amlodipine", age_years=75, hepatic_impairment=True)
    assert r.start_dose == 2.5 and len(r.adjustments_applied) == 2


def test_amlodipine_pregnancy_is_a_warning_class_c():
    r = suggest("amlodipine", **female(pregnant=True))
    assert r.status == DoseStatus.SUGGESTED and any("Class C" in w for w in r.warnings)


def test_amlodipine_contraindicated_condition():
    r = suggest("amlodipine", conditions=["cardiogenic shock"])
    assert r.status == DoseStatus.NOT_RECOMMENDED and r.start_dose is None


def test_amlodipine_possible_contraindication_is_warning():
    r = suggest("amlodipine", conditions=["heart failure"])
    assert r.status == DoseStatus.SUGGESTED and any("Possible contraindication" in w for w in r.warnings)


def test_amlodipine_already_on_drug_warns():
    r = suggest("amlodipine", current_medications=["amlodipine"])
    assert any("already recorded" in w for w in r.warnings)


# ---------------------------------------------------------------- enalapril (p49-50, Table 12 p20)

def test_enalapril_default():
    r = suggest("enalapril")
    assert (r.start_dose, r.unit, r.max_daily_dose) == (5, "mg", 20)
    assert "one or two" in r.frequency


@pytest.mark.parametrize("age,expected", [(65, 5), (66, 2.5)])
def test_enalapril_elderly_threshold_is_over_65(age, expected):
    assert suggest("enalapril", age_years=age).start_dose == expected


@pytest.mark.parametrize("diuretic", ["hydrochlorothiazide", "furosemide", "spironolactone", "hctz"])
def test_enalapril_on_diuretic_lowers_start(diuretic):
    assert suggest("enalapril", current_medications=[diuretic]).start_dose == 2.5


def test_enalapril_renal_adjustment_below_30():
    r = suggest("enalapril", creatinine_clearance_ml_min=29)
    assert r.start_dose == 2.5 and r.frequency == "once a day"
    assert any(c.page == 50 for c in r.citations)


def test_enalapril_renal_boundary_30_is_not_reduced():
    assert suggest("enalapril", creatinine_clearance_ml_min=30).start_dose == 5


def test_enalapril_pregnancy_not_recommended():
    r = suggest("enalapril", **female(pregnant=True))
    assert r.status == DoseStatus.NOT_RECOMMENDED and any("PREGNANCY" in x.upper() for x in r.reasons)


def test_enalapril_male_needs_no_pregnancy_status():
    assert suggest("enalapril", pregnant=None).status == DoseStatus.SUGGESTED


def test_enalapril_female_unknown_pregnancy_needs_info():
    r = suggest("enalapril", sex="female", pregnant=None)
    assert r.status == DoseStatus.NEEDS_INFO and r.needs_info == ["pregnant (or sex = male)"]


def test_enalapril_unknown_sex_and_pregnancy_needs_info():
    r = suggest("enalapril", sex=None, pregnant=None)
    assert r.status == DoseStatus.NEEDS_INFO and "pregnant (or sex = male)" in r.needs_info


def test_enalapril_hepatic_impairment_warns():
    r = suggest("enalapril", hepatic_impairment=True)
    assert r.start_dose == 5 and any("Hepatic" in w for w in r.warnings)


def test_enalapril_contraindicated_bilateral_renal_artery_stenosis():
    r = suggest("enalapril", conditions=["bilateral renal artery stenosis"])
    assert r.status == DoseStatus.NOT_RECOMMENDED


def test_enalapril_with_lithium_high_severity_interaction_not_recommended():
    r = suggest("enalapril", current_medications=["lithium"])
    assert r.status == DoseStatus.NOT_RECOMMENDED and any("lithium" in x.lower() for x in r.reasons)


def test_enalapril_with_potassium_sparing_diuretic_is_a_warning():
    r = suggest("enalapril", current_medications=["spironolactone"])
    assert r.status == DoseStatus.SUGGESTED and any("hyperkal" in w.lower() for w in r.warnings)


# ---------------------------------------------------------------- hydrochlorothiazide (p51-52)

def test_hctz_default_and_max():
    r = suggest("hydrochlorothiazide")
    assert (r.start_dose, r.unit, r.max_daily_dose, r.frequency) == (12.5, "mg", 25, "once daily")


def test_hctz_no_lower_start_conditions():
    assert suggest("hctz", age_years=85, hepatic_impairment=True).start_dose == 12.5


def test_hctz_renal_avoid_below_30():
    r = suggest("hydrochlorothiazide", creatinine_clearance_ml_min=25)
    assert r.status == DoseStatus.NOT_RECOMMENDED and any("Avoid" in x for x in r.reasons)


def test_hctz_pregnancy_not_recommended():
    r = suggest("hydrochlorothiazide", **female(pregnant=True))
    assert r.status == DoseStatus.NOT_RECOMMENDED


def test_hctz_listed_contraindications():
    r = suggest("hydrochlorothiazide", conditions=["hypokalemia"])
    assert r.status == DoseStatus.NOT_RECOMMENDED or any("hypokalemia" in w.lower() for w in r.warnings)


def test_hctz_hepatic_warning():
    assert any("liver" in w.lower() for w in suggest("hctz", hepatic_impairment=True).warnings)


# ---------------------------------------------------------------- Table 12 only drugs (p20)

@pytest.mark.parametrize("drug,start,maxd,freq", [
    ("lisinopril", 5, 10, "once daily"), ("telmisartan", 40, 80, "once daily"),
    ("chlorthalidone", 12.5, 25, "once daily"), ("atenolol", 50, 100, "once daily"),
    ("losartan", 50, 100, "once or twice daily"), ("metoprolol succinate", 50, 100, None),
])
def test_table_12_drugs(drug, start, maxd, freq):
    r = suggest(drug)
    assert r.status == DoseStatus.SUGGESTED, r
    assert (r.start_dose, r.max_daily_dose) == (start, maxd)
    if freq:
        assert r.frequency == freq


def test_losartan_under_50kg_starts_at_25():
    r = suggest("losartan", weight_kg=49.9)
    assert r.start_dose == 25 and any(c.page == 20 for c in r.citations)
    assert suggest("losartan", weight_kg=50).start_dose == 50


def test_losartan_needs_weight():
    r = suggest("losartan", weight_kg=None)
    assert r.status == DoseStatus.NEEDS_INFO and r.needs_info == ["weight_kg"]


def test_atenolol_low_dose_is_judgment_warning():
    r = suggest("atenolol")
    assert r.start_dose == 50 and any("25" in w and "judgment" in w for w in r.warnings)


def test_class_pregnancy_for_arbs_and_ace():
    for drug in ("losartan", "lisinopril", "telmisartan"):
        assert suggest(drug, **female(pregnant=True)).status == DoseStatus.NOT_RECOMMENDED


# ---------------------------------------------------------------- NEEDS_INFO (fail closed)

@pytest.mark.parametrize("field,drug", [
    ("age_years", "amlodipine"), ("allergies", "amlodipine"), ("current_medications", "enalapril"),
    ("conditions", "hydrochlorothiazide"), ("hepatic_impairment", "amlodipine"),
    ("creatinine_clearance_ml_min", "enalapril"), ("weight_kg", "losartan"),
])
def test_missing_fact_gives_needs_info_naming_exactly_that_fact(field, drug):
    r = suggest(drug, **{field: None})
    assert r.status == DoseStatus.NEEDS_INFO
    assert r.needs_info == [field]
    assert r.start_dose is None and r.max_daily_dose is None


def test_all_unknown_lists_every_missing_fact():
    r = engine.suggest("enalapril", PatientContext())
    assert r.status == DoseStatus.NEEDS_INFO
    assert set(r.needs_info) == {"age_years", "allergies", "current_medications", "conditions",
                                 "creatinine_clearance_ml_min", "hepatic_impairment", "pregnant (or sex = male)"}


def test_irrelevant_missing_fact_is_not_requested():
    # amlodipine has no renal rule and no weight rule
    assert suggest("amlodipine", creatinine_clearance_ml_min=None, weight_kg=None).status == DoseStatus.SUGGESTED


# ---------------------------------------------------------------- NOT_SUPPORTED

@pytest.mark.parametrize("drug", ["ibuprofen", "ramipril", "nifedipine", "zzz", "  "])
def test_unknown_drug_not_supported(drug):
    r = suggest(drug)
    assert r.status == DoseStatus.NOT_SUPPORTED and r.start_dose is None and r.reasons


def test_metoprolol_without_formulation_not_supported():
    r = suggest("metoprolol")
    assert r.status == DoseStatus.NOT_SUPPORTED and "succinate" in r.reasons[0].lower()


def test_spironolactone_not_supported_with_citation():
    r = suggest("spironolactone")
    assert r.status == DoseStatus.NOT_SUPPORTED and r.citations[0].page == 16


def test_combination_brand_not_supported():
    assert suggest("Combiflam").status == DoseStatus.NOT_SUPPORTED


def test_child_not_supported():
    r = suggest("amlodipine", age_years=12)
    assert r.status == DoseStatus.NOT_SUPPORTED and "adults" in r.reasons[0]


# ---------------------------------------------------------------- name resolution

@pytest.mark.parametrize("name", ["Amlodipine", "NORVASC", "amlong", "Amlong 5", "amlodipine besilate"])
def test_amlodipine_names_resolve(name):
    r = suggest(name)
    assert r.status == DoseStatus.SUGGESTED and r.resolved_drug == "amlodipine"


def test_hctz_alias_resolves():
    assert suggest("HCTZ").resolved_drug == "hydrochlorothiazide"


# ---------------------------------------------------------------- allergies

def test_direct_allergy_not_recommended():
    r = suggest("amlodipine", allergies=["amlodipine"])
    assert r.status == DoseStatus.NOT_RECOMMENDED and any("ALLERGY" in x for x in r.reasons)


def test_brand_name_allergy_matches_generic():
    assert suggest("amlodipine", allergies=["Norvasc"]).status == DoseStatus.NOT_RECOMMENDED


def test_unrelated_allergy_does_not_block():
    assert suggest("amlodipine", allergies=["penicillin"]).status == DoseStatus.SUGGESTED


def test_allergy_beats_missing_info():
    r = engine.suggest("amlodipine", PatientContext(allergies=["amlodipine"]))
    assert r.status == DoseStatus.NOT_RECOMMENDED and r.needs_info  # still reports what is missing


# ---------------------------------------------------------------- no hidden defaults

def test_result_is_deterministic():
    a, b = suggest("enalapril", age_years=70), suggest("enalapril", age_years=70)
    assert a.model_dump() == b.model_dump()


def test_patient_context_echoed_for_audit():
    assert suggest("amlodipine", age_years=33).patient_context.age_years == 33
