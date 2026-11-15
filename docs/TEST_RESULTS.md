# Comprehensive Test Suite Results

**Project**: Unified AI-Powered Clinical Scribe Platform  
**Target Repository**: `https://github.com/raibhan19/Accion-Labs`  
**Test Date**: 2026-11-15  
**Execution Environment**: Python 3.10.11 on Windows 11 Build 26300  

---

## 1. Monorepo Test Summary

| Test Suite | Location | Tests Run | Passed | Failed | Duration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Root Integration & E2E** | `tests/` | 18 | 18 | 0 | 14.10s |
| **Dashboard Backend Local** | `backend/dashboard/tests/` | 15 | 15 | 0 | 0.90s |
| **Clinical NLP & Safety** | `services/clinical_nlp/tests/` | 110 | 110 | 0 | 0.74s |
| **Transcription & Audio** | `services/transcription/tests/` | 26 | 26 | 0 | 0.16s |
| **Frontend TypeScript Typecheck** | `frontend/` (`npx tsc --noEmit`) | N/A | Pass (0 errors) | 0 | 3.20s |
| **Frontend Production Build** | `frontend/` (`npm run build`) | N/A | Pass (dist/ built) | 0 | 11.45s |
| **TOTALS** | **Monorepo-wide** | **169** | **169** | **0** | **~30s** |

---

## 2. Detailed Test Breakdown

### 2.1 Root Integration & End-to-End Suite (`tests/`)
```
tests/contract/test_contract_compatibility.py::test_2a_transcript_accepted_by_contract PASSED
tests/contract/test_contract_compatibility.py::test_nullable_patient_age_contract PASSED
tests/contract/test_contract_compatibility.py::test_2b_export_accepted_by_2c_dashboard PASSED
tests/contract/test_contract_compatibility.py::test_timestamp_field_equivalence PASSED
tests/end_to_end/test_three_synthetic_consultations.py::test_scenario_1_normal_consultation PASSED
tests/end_to_end/test_three_synthetic_consultations.py::test_scenario_2_allergy_conflict_blocks_finalization PASSED
tests/end_to_end/test_three_synthetic_consultations.py::test_scenario_3_complex_negation_and_historical_context PASSED
tests/unit/test_clinical_safety_and_rules.py::test_penicillin_amoxicillin_allergy_conflict PASSED
tests/unit/test_clinical_safety_and_rules.py::test_negation_detection_prevents_false_symptom PASSED
tests/unit/test_clinical_safety_and_rules.py::test_historical_context_classification PASSED
tests/unit/test_clinical_safety_and_rules.py::test_unknown_patient_age_does_not_trigger_spurious_conflict PASSED
tests/unit/test_failure_modes.py::test_transcript_end_time_before_start_time_raises PASSED
tests/unit/test_failure_modes.py::test_empty_segments_transcript_fails PASSED
tests/unit/test_failure_modes.py::test_invalid_jwt_signature_raises_http_401 PASSED
tests/unit/test_failure_modes.py::test_expired_jwt_raises_http_401 PASSED
tests/unit/test_transcription_and_audio.py::test_audio_preprocessing_resampling_and_channels PASSED
tests/unit/test_transcription_and_audio.py::test_speaker_role_heuristic_classification PASSED
tests/unit/test_transcription_and_audio.py::test_transcript_formatter_dual_timestamp_support PASSED
```

### 2.2 Dashboard Backend Suite (`backend/dashboard/tests/`)
```
tests/test_api_contract.py::test_health_disclaimer_in_payload_contract PASSED
tests/test_api_contract.py::test_rejects_malformed_payload PASSED
tests/test_api_contract.py::test_missing_patient_identifier_invalid PASSED
tests/test_pipeline.py::test_team_b_to_validation_pipeline PASSED
tests/test_safety.py::test_team_b_json_valid PASSED
tests/test_safety.py::test_citation_grounding_supported PASSED
tests/test_safety.py::test_citation_missing_is_ungrounded PASSED
tests/test_safety.py::test_penicillin_amoxicillin_critical PASSED
tests/test_safety.py::test_male_pregnancy_demographic PASSED
tests/test_safety.py::test_incorrect_age PASSED
tests/test_safety.py::test_denies_chest_pain_contradiction PASSED
tests/test_safety.py::test_unsupported_diagnosis_asthma PASSED
tests/test_safety.py::test_unsupported_medication_amoxicillin PASSED
tests/test_safety.py::test_grounding_score_not_perfect_on_demo PASSED
tests/test_safety.py::test_fhir_bundle_structure PASSED
```

### 2.3 Clinical NLP & Safety Suite (`services/clinical_nlp/tests/`)
- Unit tests: 102/102 PASSED
- Evaluation regressions: 6/6 PASSED
- Team C export integration: 2/2 PASSED

### 2.4 Transcription & Audio Suite (`services/transcription/tests/`)
- Alignment rules 1-4: 5/5 PASSED
- Overlap & turn merging: 8/8 PASSED
- Speaker roles heuristics: 6/6 PASSED
- Utterance manager streaming: 4/4 PASSED
- Window refinement & anti-hallucination: 3/3 PASSED

### 2.5 Frontend Build & TypeScript
- TypeScript Compiler (`npx tsc --noEmit`): 0 errors.
- Production bundle: `dist/index.html` (0.51 kB), `dist/assets/index-Bgsokfe9.css` (28.24 kB), `dist/assets/index-JzWNE6oO.js` (776.25 kB).
