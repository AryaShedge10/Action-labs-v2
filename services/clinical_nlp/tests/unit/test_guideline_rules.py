"""Phase 4 rules from the MoHFW STG Hypertension 2016 (Table 10, combinations, BP crisis)."""

import pytest

from app.dosing.bp import classify_bp
from app.dosing.engine import DoseEngine
from app.dosing.models import DoseStatus, PatientContext
from app.models.schemas import ConflictStatus, ConflictType, Severity
from tests.conftest import make_payload


def run(pipeline, *turns):
    return pipeline.analyze(make_payload(*turns), "rule", "template")


def by_rule(analysis, rule_id):
    return [c for c in analysis.conflicts if c.rule_id == rule_id]


def first(analysis, rule_id):
    found = by_rule(analysis, rule_id)
    assert found, [c.message for c in analysis.conflicts]
    return found[0]


# ---------------------------------------------------------------- Table 10 contraindications

@pytest.mark.parametrize("history,drug", [
    ("I have asthma.", "atenolol"),
    ("I have second degree AV block.", "metoprolol"),
    ("I have gout.", "hydrochlorothiazide"),
    ("I have gout.", "furosemide"),
    ("I have hyperkalemia.", "enalapril"),
    ("I have hyperkalemia.", "losartan"),
    ("I have bilateral renal artery stenosis.", "lisinopril"),
    ("I have bilateral renal artery stenosis.", "losartan"),
])
def test_table_10_compelling_contraindication_blocks_new_drug(pipeline, history, drug):
    a = run(pipeline, ("PATIENT", history), ("DOCTOR", f"I will prescribe {drug} for your blood pressure."))
    c = first(a, "GUIDELINE_CONTRAINDICATION")
    assert c.type == ConflictType.GUIDELINE_CONTRAINDICATION
    assert c.status == ConflictStatus.BLOCKED and c.severity == Severity.HIGH
    assert c.citations and c.citations[0].page == 16 and "Table 10" in c.citations[0].table_or_section


def test_historical_condition_is_review_not_block(pipeline):
    a = run(pipeline, ("PATIENT", "I had gout in the past."), ("DOCTOR", "I will prescribe hydrochlorothiazide."))
    c = first(a, "GUIDELINE_CONTRAINDICATION")
    assert c.status == ConflictStatus.REVIEW_REQUIRED


def test_spironolactone_with_egfr_below_30(pipeline):
    a = run(pipeline, ("DOCTOR", "Her eGFR is 25."), ("DOCTOR", "I will prescribe spironolactone."))
    c = first(a, "GUIDELINE_CONTRAINDICATION")
    assert c.status == ConflictStatus.BLOCKED and "eGFR" in c.message


def test_spironolactone_with_egfr_30_not_flagged(pipeline):
    a = run(pipeline, ("DOCTOR", "Her eGFR is 30."), ("DOCTOR", "I will prescribe spironolactone."))
    assert not by_rule(a, "GUIDELINE_CONTRAINDICATION")


def test_no_contraindication_without_the_condition(pipeline):
    a = run(pipeline, ("PATIENT", "I have gout."), ("DOCTOR", "I will prescribe amlodipine."))
    assert not by_rule(a, "GUIDELINE_CONTRAINDICATION")


def test_negated_condition_is_not_a_contraindication(pipeline):
    a = run(pipeline, ("DOCTOR", "Do you have asthma?"), ("PATIENT", "No, I do not have asthma."),
            ("DOCTOR", "I will prescribe atenolol."))
    assert not by_rule(a, "GUIDELINE_CONTRAINDICATION")


def test_ace_inhibitor_pregnancy_still_handled_by_existing_rule_without_duplicate(pipeline):
    a = run(pipeline, ("PATIENT", "I am pregnant."), ("DOCTOR", "I will prescribe enalapril."))
    assert by_rule(a, "PREGNANCY_CONTRAINDICATION")
    assert not by_rule(a, "GUIDELINE_CONTRAINDICATION")


# ---------------------------------------------------------------- combinations

def test_ace_inhibitor_plus_arb(pipeline):
    a = run(pipeline, ("PATIENT", "I take lisinopril."), ("DOCTOR", "I will prescribe losartan."))
    c = first(a, "GUIDELINE_COMBINATION")
    assert c.severity == Severity.HIGH and "should not be combined" in c.message
    assert c.citations[0].page == 49
    assert not [x for x in a.conflicts if x.rule_id == "DRUG_INTERACTION" and "dual" in x.message.lower()]


def test_thiazide_plus_beta_blocker_is_low_not_preferred(pipeline):
    a = run(pipeline, ("PATIENT", "I take atenolol."), ("DOCTOR", "I will prescribe hydrochlorothiazide."))
    c = first(a, "GUIDELINE_COMBINATION")
    assert c.severity == Severity.LOW and "not preferred" in c.message and c.status == ConflictStatus.REVIEW_REQUIRED
    assert c.citations[0].page == 51


def test_ace_plus_thiazide_is_fine(pipeline):
    a = run(pipeline, ("PATIENT", "I take lisinopril."), ("DOCTOR", "I will prescribe hydrochlorothiazide."))
    assert not by_rule(a, "GUIDELINE_COMBINATION")


def test_amlodipine_simvastatin_dose_over_cap(pipeline):
    a = run(pipeline, ("PATIENT", "I take simvastatin 40 mg once daily."), ("DOCTOR", "I will prescribe amlodipine."))
    c = first(a, "GUIDELINE_COMBINATION")
    assert c.type == ConflictType.DOSE_RANGE and c.severity == Severity.HIGH
    assert "40" in c.message and c.citations[0].page == 48


def test_amlodipine_simvastatin_dose_within_cap_not_flagged(pipeline):
    a = run(pipeline, ("PATIENT", "I take simvastatin 20 mg once daily."), ("DOCTOR", "I will prescribe amlodipine."))
    assert not by_rule(a, "GUIDELINE_COMBINATION")


def test_amlodipine_simvastatin_unknown_dose_is_review_medium(pipeline):
    a = run(pipeline, ("PATIENT", "I take simvastatin."), ("DOCTOR", "I will prescribe amlodipine."))
    c = first(a, "GUIDELINE_COMBINATION")
    assert c.severity == Severity.MEDIUM and "not documented" in c.message


# ---------------------------------------------------------------- BP crisis (Table 4, Table 3 p7, Pathway 7)

def test_bp_above_180_110_with_symptom_is_critical(pipeline):
    a = run(pipeline, ("DOCTOR", "Your blood pressure is 190/115."), ("PATIENT", "I have chest pain."))
    c = first(a, "BP_CRISIS")
    assert c.severity == Severity.CRITICAL and "hypertensive emergency" in c.message
    assert "Grade 3 Hypertension" in c.message
    assert {g.page for g in c.citations} >= {7, 8, 37}
    assert a.conflicts[0].rule_id == "BP_CRISIS"           # CRITICAL sorts first


@pytest.mark.parametrize("sentence", [
    "I feel confused.", "I have shortness of breath.", "I had a seizure.", "I have chest pain.",
    "I have weakness in my arm.", "I am passing less urine.", "I have pedal edema.",
])
def test_each_abcdefg_symptom_triggers_critical(pipeline, sentence):
    a = run(pipeline, ("DOCTOR", "Blood pressure is 200/120."), ("PATIENT", sentence))
    assert first(a, "BP_CRISIS").severity == Severity.CRITICAL


def test_papilledema_finding_triggers_critical(pipeline):
    a = run(pipeline, ("DOCTOR", "Blood pressure is 200/120. Fundus shows papilledema."))
    assert first(a, "BP_CRISIS").severity == Severity.CRITICAL


def test_bp_above_180_110_without_symptoms_is_review(pipeline):
    a = run(pipeline, ("DOCTOR", "Your blood pressure is 190/100."), ("PATIENT", "I feel fine, just a mild headache."))
    c = first(a, "BP_CRISIS")
    assert c.severity == Severity.HIGH and c.status == ConflictStatus.REVIEW_REQUIRED
    assert "urgency" in c.message and c.severity != Severity.CRITICAL


def test_diastolic_alone_above_110_triggers(pipeline):
    a = run(pipeline, ("DOCTOR", "Blood pressure is 170/115."))
    assert by_rule(a, "BP_CRISIS")


def test_near_miss_175_105_does_not_trigger_even_with_symptom(pipeline):
    a = run(pipeline, ("DOCTOR", "Your blood pressure is 175/105."), ("PATIENT", "I have chest pain."))
    assert not by_rule(a, "BP_CRISIS")


@pytest.mark.parametrize("bp", ["180/110", "180/100", "170/110"])
def test_exactly_at_threshold_does_not_trigger_strict_greater_than(pipeline, bp):
    a = run(pipeline, ("DOCTOR", f"Your blood pressure is {bp}."), ("PATIENT", "I have chest pain."))
    assert not by_rule(a, "BP_CRISIS")


def test_symptom_without_high_bp_does_not_trigger(pipeline):
    a = run(pipeline, ("DOCTOR", "Your blood pressure is 130/85."), ("PATIENT", "I have chest pain."))
    assert not by_rule(a, "BP_CRISIS")


def test_negated_symptom_does_not_make_it_critical(pipeline):
    a = run(pipeline, ("DOCTOR", "Blood pressure is 190/115. Any chest pain?"), ("PATIENT", "No, I do not have chest pain."))
    assert first(a, "BP_CRISIS").severity == Severity.HIGH


# ---------------------------------------------------------------- Table 4 grade labels

@pytest.mark.parametrize("sbp,dbp,label", [
    (110, 70, "Optimal"), (125, 78, "Normal"), (135, 82, "High Normal"), (145, 85, "Grade 1 Hypertension"),
    (150, 105, "Grade 2 Hypertension"), (165, 80, "Grade 2 Hypertension"), (185, 90, "Grade 3 Hypertension"),
    (175, 112, "Grade 3 Hypertension"), (119, 79, "Optimal"), (120, 79, "Normal"),
])
def test_table_4_grades(sbp, dbp, label):
    assert classify_bp(sbp, dbp).label == label


def test_isolated_systolic_flag():
    assert classify_bp(150, 85).isolated_systolic and not classify_bp(150, 95).isolated_systolic


# ---------------------------------------------------------------- the dose engine inherits the new rules

def test_dose_engine_not_recommended_for_beta_blocker_with_asthma():
    ctx = PatientContext(age_years=40, sex="male", weight_kg=70, creatinine_clearance_ml_min=90,
                         hepatic_impairment=False, conditions=["asthma"], current_medications=[], allergies=[])
    r = DoseEngine().suggest("atenolol", ctx)
    assert r.status == DoseStatus.NOT_RECOMMENDED and any("GUIDELINE_CONTRAINDICATION" in x for x in r.reasons)
    assert any(c.page == 16 for c in r.citations)


def test_dose_engine_ace_plus_arb_not_recommended():
    ctx = PatientContext(age_years=40, sex="male", weight_kg=70, creatinine_clearance_ml_min=90,
                         hepatic_impairment=False, conditions=[], current_medications=["losartan"], allergies=[])
    assert DoseEngine().suggest("enalapril", ctx).status == DoseStatus.NOT_RECOMMENDED


def test_dose_engine_thiazide_with_beta_blocker_is_only_a_warning():
    ctx = PatientContext(age_years=40, sex="male", weight_kg=70, creatinine_clearance_ml_min=90,
                         hepatic_impairment=False, conditions=[], current_medications=["atenolol"], allergies=[])
    r = DoseEngine().suggest("hydrochlorothiazide", ctx)
    assert r.status == DoseStatus.SUGGESTED and any("not preferred" in w for w in r.warnings)


def test_dose_engine_simvastatin_cap_warning_with_amlodipine():
    ctx = PatientContext(age_years=40, sex="male", weight_kg=70, creatinine_clearance_ml_min=90,
                         hepatic_impairment=False, conditions=[], current_medications=["simvastatin"], allergies=[])
    r = DoseEngine().suggest("amlodipine", ctx)
    assert any("simvastatin" in w.lower() and "20" in w for w in r.warnings)
