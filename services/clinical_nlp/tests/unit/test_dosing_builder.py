"""PatientContext builder: fills only what the pipeline extracted; everything else stays None."""

from app.dosing.builder import patient_context_from_analysis
from app.dosing.engine import DoseEngine
from app.dosing.models import DoseStatus
from tests.conftest import make_payload


def analyze(pipeline, *turns):
    return pipeline.analyze(make_payload(*turns), "rule", "template")


def test_unmentioned_facts_stay_none(pipeline):
    ctx = patient_context_from_analysis(analyze(pipeline, ("DOCTOR", "How are you today?"), ("PATIENT", "I have a cough.")))
    assert ctx.model_dump() == {k: None for k in ctx.model_dump()}


def test_extracts_age_sex_weight_and_renal(pipeline):
    a = analyze(pipeline, ("DOCTOR", "This is a 72-year-old woman. Her weight is 48 kg and creatinine clearance is 25."),
                ("PATIENT", "I am not pregnant."))
    ctx = patient_context_from_analysis(a)
    assert ctx.age_years == 72 and ctx.sex == "female"
    assert ctx.weight_kg == 48 and ctx.creatinine_clearance_ml_min == 25


def test_pounds_converted_exactly(pipeline):
    ctx = patient_context_from_analysis(analyze(pipeline, ("DOCTOR", "Her weight is 110 lbs.")))
    assert ctx.weight_kg == 49.9


def test_nkda_means_allergies_known_empty(pipeline):
    ctx = patient_context_from_analysis(analyze(pipeline, ("DOCTOR", "Any allergies?"),
                                                ("PATIENT", "No known drug allergies.")))
    assert ctx.allergies == []


def test_documented_allergy_and_current_medicine(pipeline):
    ctx = patient_context_from_analysis(analyze(
        pipeline, ("DOCTOR", "Any allergies?"), ("PATIENT", "I am allergic to penicillin. I take lisinopril daily.")))
    assert ctx.allergies == ["penicillin"] and ctx.current_medications == ["lisinopril"]


def test_conditions_from_diagnoses(pipeline):
    ctx = patient_context_from_analysis(analyze(pipeline, ("PATIENT", "I have gout and asthma.")))
    assert ctx.conditions is not None and {"gout", "asthma"} <= set(ctx.conditions)


def test_end_to_end_missing_facts_give_needs_info(pipeline):
    ctx = patient_context_from_analysis(analyze(pipeline, ("DOCTOR", "This is a 50-year-old man with hypertension.")))
    r = DoseEngine().suggest("amlodipine", ctx)
    assert r.status == DoseStatus.NEEDS_INFO
    assert "age_years" not in r.needs_info and "hepatic_impairment" in r.needs_info
