# Comprehensive File Mapping and Reconciliation Matrix

**Project:** Unified AI-Powered Clinical Scribe Platform  
**Classification Codes:**
- **KEEP:** Preserved as-is with original functionality.
- **MERGE:** Merged with complementary implementations to resolve discrepancies.
- **REFACTOR:** Modified to satisfy shared contracts, fix security/privacy issues, or support browser capture.
- **EXCLUDE:** Excluded duplicate code, local test artifacts, or superseded implementations.
- **EXPERIMENTAL:** Preserved in dedicated data/evaluation/experimental folders.

---

## 1. Repository A Mapping (Audio & Transcription)

| Source Path | Classification | Target Path | Reason / Action |
|-------------|----------------|-------------|-----------------|
| repo_a/.env.example | REFACTOR | services/transcription/.env.example | Pin dependencies, document environment variables |
| repo_a/.gitignore | KEEP | services/transcription/.gitignore | Documentation and project specifications |
| repo_a/BUG_FIXES_SUMMARY.md | KEEP | services/transcription/BUG_FIXES_SUMMARY.md | Documentation and project specifications |
| repo_a/create_sample_audio.py | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/CURRENT_STATUS.txt | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/INSTALLATION_GUIDE.md | KEEP | services/transcription/INSTALLATION_GUIDE.md | Documentation and project specifications |
| repo_a/install_fix.bat | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/NEXT_STEPS.md | KEEP | services/transcription/NEXT_STEPS.md | Documentation and project specifications |
| repo_a/Port | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/PROJECT_DOCUMENTATION.md | KEEP | services/transcription/PROJECT_DOCUMENTATION.md | Documentation and project specifications |
| repo_a/quick_test.py | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/README.md | REFACTOR | services/transcription/README.md | Pin dependencies, document environment variables |
| repo_a/README_WINDOWS_SETUP.md | KEEP | services/transcription/README_WINDOWS_SETUP.md | Documentation and project specifications |
| repo_a/record_live_audio.py | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/requirements-simple.txt | KEEP | services/transcription/requirements-simple.txt | Documentation and project specifications |
| repo_a/requirements.txt | REFACTOR | services/transcription/requirements.txt | Pin dependencies, document environment variables |
| repo_a/SETUP_GUIDE.md | KEEP | services/transcription/SETUP_GUIDE.md | Documentation and project specifications |
| repo_a/START_HERE.md | KEEP | services/transcription/START_HERE.md | Documentation and project specifications |
| repo_a/TEAM_B_COMPATIBILITY_SUMMARY.md | KEEP | services/transcription/TEAM_B_COMPATIBILITY_SUMMARY.md | Documentation and project specifications |
| repo_a/TEAM_B_INTEGRATION.md | KEEP | services/transcription/TEAM_B_INTEGRATION.md | Documentation and project specifications |
| repo_a/TESTING_GUIDE.md | KEEP | services/transcription/TESTING_GUIDE.md | Documentation and project specifications |
| repo_a/test_transcription.py | EXCLUDE | None | Local developer scratch scripts superseded by unified test suite and web UI |
| repo_a/WHATS_NEW.md | KEEP | services/transcription/WHATS_NEW.md | Documentation and project specifications |
| repo_a/app\main.py | KEEP | services/transcription/app\main.py | Documentation and project specifications |
| repo_a/app\__init__.py | KEEP | services/transcription/app\__init__.py | Documentation and project specifications |
| repo_a/app\api\live_routes.py | KEEP | services/transcription/app\api\live_routes.py | Documentation and project specifications |
| repo_a/app\api\routes.py | KEEP | services/transcription/app\api\routes.py | Documentation and project specifications |
| repo_a/app\api\__init__.py | KEEP | services/transcription/app\api\__init__.py | Documentation and project specifications |
| repo_a/app\audio\audio_loader.py | KEEP | services/transcription/app\audio\audio_loader.py | Documentation and project specifications |
| repo_a/app\audio\preprocessing.py | KEEP | services/transcription/app\audio\preprocessing.py | Documentation and project specifications |
| repo_a/app\audio\__init__.py | KEEP | services/transcription/app\audio\__init__.py | Documentation and project specifications |
| repo_a/app\services\alignment.py | KEEP | services/transcription/app\services\alignment.py | Documentation and project specifications |
| repo_a/app\services\diarization.py | KEEP | services/transcription/app\services\diarization.py | Documentation and project specifications |
| repo_a/app\services\llm_correction.py | KEEP | services/transcription/app\services\llm_correction.py | Documentation and project specifications |
| repo_a/app\services\merge.py | KEEP | services/transcription/app\services\merge.py | Documentation and project specifications |
| repo_a/app\services\pipeline.py | KEEP | services/transcription/app\services\pipeline.py | Documentation and project specifications |
| repo_a/app\services\roles.py | KEEP | services/transcription/app\services\roles.py | Documentation and project specifications |
| repo_a/app\services\text_cleanup.py | KEEP | services/transcription/app\services\text_cleanup.py | Documentation and project specifications |
| repo_a/app\services\utterance_manager.py | KEEP | services/transcription/app\services\utterance_manager.py | Documentation and project specifications |
| repo_a/app\services\__init__.py | KEEP | services/transcription/app\services\__init__.py | Documentation and project specifications |
| repo_a/app\speaker\diarization_interface.py | KEEP | services/transcription/app\speaker\diarization_interface.py | Documentation and project specifications |
| repo_a/app\speaker\__init__.py | KEEP | services/transcription/app\speaker\__init__.py | Documentation and project specifications |
| repo_a/app\transcription\transcript_formatter.py | KEEP | services/transcription/app\transcription\transcript_formatter.py | Documentation and project specifications |
| repo_a/app\transcription\whisper_service.py | KEEP | services/transcription/app\transcription\whisper_service.py | Documentation and project specifications |
| repo_a/app\transcription\__init__.py | KEEP | services/transcription/app\transcription\__init__.py | Documentation and project specifications |
| repo_a/output\.gitkeep | KEEP | services/transcription/output\.gitkeep | Documentation and project specifications |
| repo_a/output\temp_processed.wav | KEEP | services/transcription/output\temp_processed.wav | Documentation and project specifications |
| repo_a/sample_audio\.gitkeep | KEEP | services/transcription/sample_audio\.gitkeep | Documentation and project specifications |
| repo_a/sample_audio\test.m4a | KEEP | services/transcription/sample_audio\test.m4a | Documentation and project specifications |
| repo_a/static\index.html | KEEP | services/transcription/static\index.html | Documentation and project specifications |
| repo_a/static\transcript.html | KEEP | services/transcription/static\transcript.html | Documentation and project specifications |
| repo_a/tests\test_alignment.py | KEEP | services/transcription/tests\test_alignment.py | Documentation and project specifications |
| repo_a/tests\test_merge.py | KEEP | services/transcription/tests\test_merge.py | Documentation and project specifications |
| repo_a/tests\test_roles.py | KEEP | services/transcription/tests\test_roles.py | Documentation and project specifications |
| repo_a/tests\test_swap_endpoint.py | KEEP | services/transcription/tests\test_swap_endpoint.py | Documentation and project specifications |
| repo_a/tests\test_utterance_manager.py | KEEP | services/transcription/tests\test_utterance_manager.py | Documentation and project specifications |
| repo_a/tests\test_window_refiner.py | KEEP | services/transcription/tests\test_window_refiner.py | Documentation and project specifications |
| repo_a/tests\__init__.py | KEEP | services/transcription/tests\__init__.py | Documentation and project specifications |
| repo_a/tests\logs\all_completed_events.jsonl | KEEP | services/transcription/tests\logs\all_completed_events.jsonl | Documentation and project specifications |
| repo_a/tests\logs\completed_1791201724294.json | KEEP | services/transcription/tests\logs\completed_1791201724294.json | Documentation and project specifications |
| repo_a/tests\logs\completed_1791201724307.json | KEEP | services/transcription/tests\logs\completed_1791201724307.json | Documentation and project specifications |
| repo_a/tests\logs\completed_1791202083338.json | KEEP | services/transcription/tests\logs\completed_1791202083338.json | Documentation and project specifications |
| repo_a/tests\logs\completed_1791202083374.json | KEEP | services/transcription/tests\logs\completed_1791202083374.json | Documentation and project specifications |
| repo_a/tests\logs\completed_1791832894444.json | KEEP | services/transcription/tests\logs\completed_1791832894444.json | Documentation and project specifications |
| repo_a/tests\logs\completed_1791832894550.json | KEEP | services/transcription/tests\logs\completed_1791832894550.json | Documentation and project specifications |
| repo_a/tests\logs\nvidia_events.jsonl | KEEP | services/transcription/tests\logs\nvidia_events.jsonl | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\.env.example | KEEP | services/transcription/tests\realtime_nvidia\.env.example | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\ASSEMBLYAI_CLEANUP_REPORT.md | KEEP | services/transcription/tests\realtime_nvidia\ASSEMBLYAI_CLEANUP_REPORT.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\DISK_USAGE_REPORT.md | KEEP | services/transcription/tests\realtime_nvidia\DISK_USAGE_REPORT.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\INSTALLATION_GUIDE.md | KEEP | services/transcription/tests\realtime_nvidia\INSTALLATION_GUIDE.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\ISOLATION_REPORT.md | KEEP | services/transcription/tests\realtime_nvidia\ISOLATION_REPORT.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\MIGRATION_FROM_ASSEMBLYAI.md | KEEP | services/transcription/tests\realtime_nvidia\MIGRATION_FROM_ASSEMBLYAI.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\MOSS_REMAINING_ARTIFACTS.md | KEEP | services/transcription/tests\realtime_nvidia\MOSS_REMAINING_ARTIFACTS.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\README.md | KEEP | services/transcription/tests\realtime_nvidia\README.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\run_nemo_server.bat | KEEP | services/transcription/tests\realtime_nvidia\run_nemo_server.bat | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\run_test_backend.bat | KEEP | services/transcription/tests\realtime_nvidia\run_test_backend.bat | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\run_test_backend.ps1 | KEEP | services/transcription/tests\realtime_nvidia\run_test_backend.ps1 | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\verify_isolation.py | KEEP | services/transcription/tests\realtime_nvidia\verify_isolation.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\requirements.txt | KEEP | services/transcription/tests\realtime_nvidia\backend\requirements.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\__init__.py | KEEP | services/transcription/tests\realtime_nvidia\backend\__init__.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\config.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\config.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\main.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\main.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\models.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\models.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\provider.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\provider.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\session_manager.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\session_manager.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\backend\app\__init__.py | KEEP | services/transcription/tests\realtime_nvidia\backend\app\__init__.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\frontend\index.html | KEEP | services/transcription/tests\realtime_nvidia\frontend\index.html | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\.gitkeep | KEEP | services/transcription/tests\realtime_nvidia\logs\.gitkeep | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\example_event_flow.json | KEEP | services/transcription/tests\realtime_nvidia\logs\example_event_flow.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\nvidia_events.jsonl | KEEP | services/transcription/tests\realtime_nvidia\logs\nvidia_events.jsonl | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_152910.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_152910.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_152910.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_152910.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_153748.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_153748.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_153748.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_153748.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_154356.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_154356.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_154356.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_154356.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_162733.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_162733.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_162733.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_162733.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_173143.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_173143.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_173143.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_173143.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_173419.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_173419.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261005_173419.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261005_173419.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261013_004745.json | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261013_004745.json | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\logs\session_nv_20261013_004745.txt | KEEP | services/transcription/tests\realtime_nvidia\logs\session_nv_20261013_004745.txt | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\model_cache\.gitkeep | KEEP | services/transcription/tests\realtime_nvidia\model_cache\.gitkeep | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\.gitkeep | KEEP | services/transcription/tests\realtime_nvidia\recordings\.gitkeep | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\clinical_test_dialogue.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\clinical_test_dialogue.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_filler_pause.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_filler_pause.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_interruption.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_interruption.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_long_silence.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_long_silence.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_medical_terms.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_medical_terms.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_quiet_patient.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_quiet_patient.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\recordings\test_rapid_switching.wav | KEEP | services/transcription/tests\realtime_nvidia\recordings\test_rapid_switching.wav | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\reports\NVIDIA_REALTIME_REPORT.md | KEEP | services/transcription/tests\realtime_nvidia\reports\NVIDIA_REALTIME_REPORT.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\reports\NVIDIA_RUNTIME_VERSION.md | KEEP | services/transcription/tests\realtime_nvidia\reports\NVIDIA_RUNTIME_VERSION.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\reports\REALTIME_EVENT_DEBUG.md | KEEP | services/transcription/tests\realtime_nvidia\reports\REALTIME_EVENT_DEBUG.md | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\runtime\.gitkeep | KEEP | services/transcription/tests\realtime_nvidia\runtime\.gitkeep | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\scripts\benchmark_latency.py | KEEP | services/transcription/tests\realtime_nvidia\scripts\benchmark_latency.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\scripts\create_test_audio.py | KEEP | services/transcription/tests\realtime_nvidia\scripts\create_test_audio.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\scripts\debug_nemo_events.py | KEEP | services/transcription/tests\realtime_nvidia\scripts\debug_nemo_events.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\scripts\test_3min_session.py | KEEP | services/transcription/tests\realtime_nvidia\scripts\test_3min_session.py | Documentation and project specifications |
| repo_a/tests\realtime_nvidia\scripts\test_realtime_events.py | KEEP | services/transcription/tests\realtime_nvidia\scripts\test_realtime_events.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\.env.example | KEEP | services/transcription/tests\realtime_stt_eval\.env.example | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\CLEANUP_AFTER.md | KEEP | services/transcription/tests\realtime_stt_eval\CLEANUP_AFTER.md | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\CLEANUP_BEFORE.md | KEEP | services/transcription/tests\realtime_stt_eval\CLEANUP_BEFORE.md | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\inventory_after.json | KEEP | services/transcription/tests\realtime_stt_eval\inventory_after.json | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\inventory_before.json | KEEP | services/transcription/tests\realtime_stt_eval\inventory_before.json | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\measure_inventory.py | KEEP | services/transcription/tests\realtime_stt_eval\measure_inventory.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\perform_cleanup.py | KEEP | services/transcription/tests\realtime_stt_eval\perform_cleanup.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\README.md | KEEP | services/transcription/tests\realtime_stt_eval\README.md | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\run_test_server.bat | KEEP | services/transcription/tests\realtime_stt_eval\run_test_server.bat | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\run_test_server.ps1 | KEEP | services/transcription/tests\realtime_stt_eval\run_test_server.ps1 | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\verify_isolation.py | KEEP | services/transcription/tests\realtime_stt_eval\verify_isolation.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\requirements.txt | KEEP | services/transcription/tests\realtime_stt_eval\backend\requirements.txt | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\__init__.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\__init__.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\config.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\config.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\main.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\main.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\models.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\models.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\provider.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\provider.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\session_manager.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\session_manager.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\backend\app\__init__.py | KEEP | services/transcription/tests\realtime_stt_eval\backend\app\__init__.py | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\frontend\index.html | KEEP | services/transcription/tests\realtime_stt_eval\frontend\index.html | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\recordings\clinical_test_dialogue.wav | KEEP | services/transcription/tests\realtime_stt_eval\recordings\clinical_test_dialogue.wav | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\reports\ASSEMBLYAI_REALTIME_REPORT.md | KEEP | services/transcription/tests\realtime_stt_eval\reports\ASSEMBLYAI_REALTIME_REPORT.md | Documentation and project specifications |
| repo_a/tests\realtime_stt_eval\tests\create_test_audio.py | KEEP | services/transcription/tests\realtime_stt_eval\tests\create_test_audio.py | Documentation and project specifications |

---

## 2. Repository B Mapping (Clinical NLP & Safety)

| Source Path | Classification | Target Path | Reason / Action |
|-------------|----------------|-------------|-----------------|
| repo_b/.dockerignore | KEEP | services/clinical_nlp/.dockerignore | Documentation and configuration files |
| repo_b/.env.example | REFACTOR | services/clinical_nlp/.env.example | Service containerization and test configuration |
| repo_b/.gitignore | KEEP | services/clinical_nlp/.gitignore | Documentation and configuration files |
| repo_b/docker-compose.yml | KEEP | services/clinical_nlp/docker-compose.yml | Documentation and configuration files |
| repo_b/Dockerfile | REFACTOR | services/clinical_nlp/Dockerfile | Service containerization and test configuration |
| repo_b/pytest.ini | REFACTOR | services/clinical_nlp/pytest.ini | Service containerization and test configuration |
| repo_b/README.md | KEEP | services/clinical_nlp/README.md | Documentation and configuration files |
| repo_b/requirements-dev.txt | KEEP | services/clinical_nlp/requirements-dev.txt | Documentation and configuration files |
| repo_b/requirements.txt | REFACTOR | services/clinical_nlp/requirements.txt | Service containerization and test configuration |
| repo_b/streamlit_app.py | KEEP | services/clinical_nlp/streamlit_app.py | Documentation and configuration files |
| repo_b/app\config.py | KEEP | services/clinical_nlp/app\config.py | Documentation and configuration files |
| repo_b/app\main.py | KEEP | services/clinical_nlp/app\main.py | Documentation and configuration files |
| repo_b/app\pipeline.py | KEEP | services/clinical_nlp/app\pipeline.py | Documentation and configuration files |
| repo_b/app\__init__.py | KEEP | services/clinical_nlp/app\__init__.py | Documentation and configuration files |
| repo_b/app\evaluation\harness.py | KEEP | services/clinical_nlp/app\evaluation\harness.py | Documentation and configuration files |
| repo_b/app\evaluation\__init__.py | KEEP | services/clinical_nlp/app\evaluation\__init__.py | Documentation and configuration files |
| repo_b/app\export\team_c.py | KEEP | services/clinical_nlp/app\export\team_c.py | Documentation and configuration files |
| repo_b/app\export\__init__.py | KEEP | services/clinical_nlp/app\export\__init__.py | Documentation and configuration files |
| repo_b/app\extraction\extractor.py | KEEP | services/clinical_nlp/app\extraction\extractor.py | Documentation and configuration files |
| repo_b/app\extraction\llm_extractor.py | KEEP | services/clinical_nlp/app\extraction\llm_extractor.py | Documentation and configuration files |
| repo_b/app\extraction\rule_based.py | KEEP | services/clinical_nlp/app\extraction\rule_based.py | Documentation and configuration files |
| repo_b/app\extraction\__init__.py | KEEP | services/clinical_nlp/app\extraction\__init__.py | Documentation and configuration files |
| repo_b/app\generation\llm_soap.py | KEEP | services/clinical_nlp/app\generation\llm_soap.py | Documentation and configuration files |
| repo_b/app\generation\prescriptions.py | KEEP | services/clinical_nlp/app\generation\prescriptions.py | Documentation and configuration files |
| repo_b/app\generation\soap_generator.py | KEEP | services/clinical_nlp/app\generation\soap_generator.py | Documentation and configuration files |
| repo_b/app\generation\template.py | KEEP | services/clinical_nlp/app\generation\template.py | Documentation and configuration files |
| repo_b/app\generation\__init__.py | KEEP | services/clinical_nlp/app\generation\__init__.py | Documentation and configuration files |
| repo_b/app\grounding\verifier.py | KEEP | services/clinical_nlp/app\grounding\verifier.py | Documentation and configuration files |
| repo_b/app\grounding\__init__.py | KEEP | services/clinical_nlp/app\grounding\__init__.py | Documentation and configuration files |
| repo_b/app\ingestion\adapter.py | KEEP | services/clinical_nlp/app\ingestion\adapter.py | Documentation and configuration files |
| repo_b/app\ingestion\team_a_client.py | KEEP | services/clinical_nlp/app\ingestion\team_a_client.py | Documentation and configuration files |
| repo_b/app\ingestion\__init__.py | KEEP | services/clinical_nlp/app\ingestion\__init__.py | Documentation and configuration files |
| repo_b/app\knowledge\drugs.py | KEEP | services/clinical_nlp/app\knowledge\drugs.py | Documentation and configuration files |
| repo_b/app\knowledge\terms.py | KEEP | services/clinical_nlp/app\knowledge\terms.py | Documentation and configuration files |
| repo_b/app\knowledge\__init__.py | KEEP | services/clinical_nlp/app\knowledge\__init__.py | Documentation and configuration files |
| repo_b/app\models\contracts.py | KEEP | services/clinical_nlp/app\models\contracts.py | Documentation and configuration files |
| repo_b/app\models\schemas.py | KEEP | services/clinical_nlp/app\models\schemas.py | Documentation and configuration files |
| repo_b/app\models\__init__.py | KEEP | services/clinical_nlp/app\models\__init__.py | Documentation and configuration files |
| repo_b/app\nlp\context.py | KEEP | services/clinical_nlp/app\nlp\context.py | Documentation and configuration files |
| repo_b/app\nlp\matcher.py | KEEP | services/clinical_nlp/app\nlp\matcher.py | Documentation and configuration files |
| repo_b/app\nlp\text.py | KEEP | services/clinical_nlp/app\nlp\text.py | Documentation and configuration files |
| repo_b/app\nlp\__init__.py | KEEP | services/clinical_nlp/app\nlp\__init__.py | Documentation and configuration files |
| repo_b/app\privacy\phi.py | KEEP | services/clinical_nlp/app\privacy\phi.py | Documentation and configuration files |
| repo_b/app\privacy\__init__.py | KEEP | services/clinical_nlp/app\privacy\__init__.py | Documentation and configuration files |
| repo_b/app\safety\allergy_rules.py | KEEP | services/clinical_nlp/app\safety\allergy_rules.py | Documentation and configuration files |
| repo_b/app\safety\clinical_rules.py | KEEP | services/clinical_nlp/app\safety\clinical_rules.py | Documentation and configuration files |
| repo_b/app\safety\demographic_rules.py | KEEP | services/clinical_nlp/app\safety\demographic_rules.py | Documentation and configuration files |
| repo_b/app\safety\engine.py | KEEP | services/clinical_nlp/app\safety\engine.py | Documentation and configuration files |
| repo_b/app\safety\medication_rules.py | KEEP | services/clinical_nlp/app\safety\medication_rules.py | Documentation and configuration files |
| repo_b/app\safety\rules.py | KEEP | services/clinical_nlp/app\safety\rules.py | Documentation and configuration files |
| repo_b/app\safety\__init__.py | KEEP | services/clinical_nlp/app\safety\__init__.py | Documentation and configuration files |
| repo_b/app\storage\repository.py | KEEP | services/clinical_nlp/app\storage\repository.py | Documentation and configuration files |
| repo_b/app\storage\__init__.py | KEEP | services/clinical_nlp/app\storage\__init__.py | Documentation and configuration files |
| repo_b/app\utils\llm.py | KEEP | services/clinical_nlp/app\utils\llm.py | Documentation and configuration files |
| repo_b/app\utils\__init__.py | KEEP | services/clinical_nlp/app\utils\__init__.py | Documentation and configuration files |
| repo_b/backend\pytest.ini | KEEP | services/clinical_nlp/backend\pytest.ini | Documentation and configuration files |
| repo_b/backend\requirements.txt | KEEP | services/clinical_nlp/backend\requirements.txt | Documentation and configuration files |
| repo_b/backend\app\auth.py | KEEP | services/clinical_nlp/backend\app\auth.py | Documentation and configuration files |
| repo_b/backend\app\config.py | KEEP | services/clinical_nlp/backend\app\config.py | Documentation and configuration files |
| repo_b/backend\app\database.py | KEEP | services/clinical_nlp/backend\app\database.py | Documentation and configuration files |
| repo_b/backend\app\logging_config.py | KEEP | services/clinical_nlp/backend\app\logging_config.py | Documentation and configuration files |
| repo_b/backend\app\main.py | KEEP | services/clinical_nlp/backend\app\main.py | Documentation and configuration files |
| repo_b/backend\app\__init__.py | KEEP | services/clinical_nlp/backend\app\__init__.py | Documentation and configuration files |
| repo_b/backend\app\api\ehr.py | KEEP | services/clinical_nlp/backend\app\api\ehr.py | Documentation and configuration files |
| repo_b/backend\app\api\encounters.py | KEEP | services/clinical_nlp/backend\app\api\encounters.py | Documentation and configuration files |
| repo_b/backend\app\api\__init__.py | KEEP | services/clinical_nlp/backend\app\api\__init__.py | Documentation and configuration files |
| repo_b/backend\app\integrations\ehr.py | KEEP | services/clinical_nlp/backend\app\integrations\ehr.py | Documentation and configuration files |
| repo_b/backend\app\integrations\__init__.py | KEEP | services/clinical_nlp/backend\app\integrations\__init__.py | Documentation and configuration files |
| repo_b/backend\app\models\orm.py | KEEP | services/clinical_nlp/backend\app\models\orm.py | Documentation and configuration files |
| repo_b/backend\app\models\__init__.py | KEEP | services/clinical_nlp/backend\app\models\__init__.py | Documentation and configuration files |
| repo_b/backend\app\schemas\team_b.py | KEEP | services/clinical_nlp/backend\app\schemas\team_b.py | Documentation and configuration files |
| repo_b/backend\app\schemas\__init__.py | KEEP | services/clinical_nlp/backend\app\schemas\__init__.py | Documentation and configuration files |
| repo_b/backend\app\services\demo.py | KEEP | services/clinical_nlp/backend\app\services\demo.py | Documentation and configuration files |
| repo_b/backend\app\services\encounter.py | KEEP | services/clinical_nlp/backend\app\services\encounter.py | Documentation and configuration files |
| repo_b/backend\app\services\fhir.py | KEEP | services/clinical_nlp/backend\app\services\fhir.py | Documentation and configuration files |
| repo_b/backend\app\services\pdf.py | KEEP | services/clinical_nlp/backend\app\services\pdf.py | Documentation and configuration files |
| repo_b/backend\app\services\__init__.py | KEEP | services/clinical_nlp/backend\app\services\__init__.py | Documentation and configuration files |
| repo_b/backend\app\validators\conflicts.py | KEEP | services/clinical_nlp/backend\app\validators\conflicts.py | Documentation and configuration files |
| repo_b/backend\app\validators\grounding.py | KEEP | services/clinical_nlp/backend\app\validators\grounding.py | Documentation and configuration files |
| repo_b/backend\app\validators\__init__.py | KEEP | services/clinical_nlp/backend\app\validators\__init__.py | Documentation and configuration files |
| repo_b/backend\tests\test_api_contract.py | KEEP | services/clinical_nlp/backend\tests\test_api_contract.py | Documentation and configuration files |
| repo_b/backend\tests\test_pipeline.py | KEEP | services/clinical_nlp/backend\tests\test_pipeline.py | Documentation and configuration files |
| repo_b/backend\tests\test_safety.py | KEEP | services/clinical_nlp/backend\tests\test_safety.py | Documentation and configuration files |
| repo_b/data\evaluation\cases.jsonl | KEEP | services/clinical_nlp/data\evaluation\cases.jsonl | Documentation and configuration files |
| repo_b/data\samples\demo_conflict_001.json | KEEP | services/clinical_nlp/data\samples\demo_conflict_001.json | Documentation and configuration files |
| repo_b/data\samples\team_a_20261031_143022.json | KEEP | services/clinical_nlp/data\samples\team_a_20261031_143022.json | Documentation and configuration files |
| repo_b/docker\backend.Dockerfile | KEEP | services/clinical_nlp/docker\backend.Dockerfile | Documentation and configuration files |
| repo_b/docker\frontend.Dockerfile | KEEP | services/clinical_nlp/docker\frontend.Dockerfile | Documentation and configuration files |
| repo_b/docker\init-db.sql | KEEP | services/clinical_nlp/docker\init-db.sql | Documentation and configuration files |
| repo_b/docker\mock_ehr.Dockerfile | KEEP | services/clinical_nlp/docker\mock_ehr.Dockerfile | Documentation and configuration files |
| repo_b/docker\nginx.conf | KEEP | services/clinical_nlp/docker\nginx.conf | Documentation and configuration files |
| repo_b/docker\README.md | KEEP | services/clinical_nlp/docker\README.md | Documentation and configuration files |
| repo_b/docs\api.md | KEEP | services/clinical_nlp/docs\api.md | Documentation and configuration files |
| repo_b/docs\architecture.md | KEEP | services/clinical_nlp/docs\architecture.md | Documentation and configuration files |
| repo_b/docs\CURRENT_STATE.md | KEEP | services/clinical_nlp/docs\CURRENT_STATE.md | Documentation and configuration files |
| repo_b/docs\DATASETS.md | KEEP | services/clinical_nlp/docs\DATASETS.md | Documentation and configuration files |
| repo_b/docs\PROJECT_DOCUMENTATION.md | KEEP | services/clinical_nlp/docs\PROJECT_DOCUMENTATION.md | Documentation and configuration files |
| repo_b/docs\team-b.example.json | KEEP | services/clinical_nlp/docs\team-b.example.json | Documentation and configuration files |
| repo_b/docs\samples\team_c_response_20261031_143022.json | KEEP | services/clinical_nlp/docs\samples\team_c_response_20261031_143022.json | Documentation and configuration files |
| repo_b/docs\samples\team_c_response_conflict.json | KEEP | services/clinical_nlp/docs\samples\team_c_response_conflict.json | Documentation and configuration files |
| repo_b/frontend\index.html | KEEP | services/clinical_nlp/frontend\index.html | Documentation and configuration files |
| repo_b/frontend\package-lock.json | KEEP | services/clinical_nlp/frontend\package-lock.json | Documentation and configuration files |
| repo_b/frontend\package.json | KEEP | services/clinical_nlp/frontend\package.json | Documentation and configuration files |
| repo_b/frontend\postcss.config.js | KEEP | services/clinical_nlp/frontend\postcss.config.js | Documentation and configuration files |
| repo_b/frontend\tailwind.config.js | KEEP | services/clinical_nlp/frontend\tailwind.config.js | Documentation and configuration files |
| repo_b/frontend\tsconfig.json | KEEP | services/clinical_nlp/frontend\tsconfig.json | Documentation and configuration files |
| repo_b/frontend\vite.config.ts | KEEP | services/clinical_nlp/frontend\vite.config.ts | Documentation and configuration files |
| repo_b/frontend\src\App.tsx | KEEP | services/clinical_nlp/frontend\src\App.tsx | Documentation and configuration files |
| repo_b/frontend\src\index.css | KEEP | services/clinical_nlp/frontend\src\index.css | Documentation and configuration files |
| repo_b/frontend\src\main.tsx | KEEP | services/clinical_nlp/frontend\src\main.tsx | Documentation and configuration files |
| repo_b/frontend\src\vite-env.d.ts | KEEP | services/clinical_nlp/frontend\src\vite-env.d.ts | Documentation and configuration files |
| repo_b/frontend\src\components\audit\AuditDrawer.tsx | KEEP | services/clinical_nlp/frontend\src\components\audit\AuditDrawer.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\finalize\FinalizeDialog.tsx | KEEP | services/clinical_nlp/frontend\src\components\finalize\FinalizeDialog.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\layout\ActionBar.tsx | KEEP | services/clinical_nlp/frontend\src\components\layout\ActionBar.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\layout\HeaderBar.tsx | KEEP | services/clinical_nlp/frontend\src\components\layout\HeaderBar.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\note\SoapEditor.tsx | KEEP | services/clinical_nlp/frontend\src\components\note\SoapEditor.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\patient\PatientPanel.tsx | KEEP | services/clinical_nlp/frontend\src\components\patient\PatientPanel.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\transcript\TranscriptViewer.tsx | KEEP | services/clinical_nlp/frontend\src\components\transcript\TranscriptViewer.tsx | Documentation and configuration files |
| repo_b/frontend\src\components\validation\ValidationPanel.tsx | KEEP | services/clinical_nlp/frontend\src\components\validation\ValidationPanel.tsx | Documentation and configuration files |
| repo_b/frontend\src\hooks\useEncounter.ts | KEEP | services/clinical_nlp/frontend\src\hooks\useEncounter.ts | Documentation and configuration files |
| repo_b/frontend\src\pages\EncounterPage.tsx | KEEP | services/clinical_nlp/frontend\src\pages\EncounterPage.tsx | Documentation and configuration files |
| repo_b/frontend\src\pages\HomePage.tsx | KEEP | services/clinical_nlp/frontend\src\pages\HomePage.tsx | Documentation and configuration files |
| repo_b/frontend\src\services\api.ts | KEEP | services/clinical_nlp/frontend\src\services\api.ts | Documentation and configuration files |
| repo_b/frontend\src\types\clinical.ts | KEEP | services/clinical_nlp/frontend\src\types\clinical.ts | Documentation and configuration files |
| repo_b/frontend\src\utils\format.ts | KEEP | services/clinical_nlp/frontend\src\utils\format.ts | Documentation and configuration files |
| repo_b/legacy\pipeline_demo.py | KEEP | services/clinical_nlp/legacy\pipeline_demo.py | Documentation and configuration files |
| repo_b/mock_ehr\requirements.txt | KEEP | services/clinical_nlp/mock_ehr\requirements.txt | Documentation and configuration files |
| repo_b/mock_ehr\api\main.py | KEEP | services/clinical_nlp/mock_ehr\api\main.py | Documentation and configuration files |
| repo_b/mock_ehr\api\__init__.py | KEEP | services/clinical_nlp/mock_ehr\api\__init__.py | Documentation and configuration files |
| repo_b/reports\evaluation_report.md | KEEP | services/clinical_nlp/reports\evaluation_report.md | Documentation and configuration files |
| repo_b/reports\metrics.json | KEEP | services/clinical_nlp/reports\metrics.json | Documentation and configuration files |
| repo_b/scripts\build_eval_cases.py | KEEP | services/clinical_nlp/scripts\build_eval_cases.py | Documentation and configuration files |
| repo_b/scripts\convert_mts_dialog.py | KEEP | services/clinical_nlp/scripts\convert_mts_dialog.py | Documentation and configuration files |
| repo_b/scripts\evaluate.py | KEEP | services/clinical_nlp/scripts\evaluate.py | Documentation and configuration files |
| repo_b/tests\conftest.py | KEEP | services/clinical_nlp/tests\conftest.py | Documentation and configuration files |
| repo_b/tests\__init__.py | KEEP | services/clinical_nlp/tests\__init__.py | Documentation and configuration files |
| repo_b/tests\evaluation\test_regression.py | KEEP | services/clinical_nlp/tests\evaluation\test_regression.py | Documentation and configuration files |
| repo_b/tests\evaluation\__init__.py | KEEP | services/clinical_nlp/tests\evaluation\__init__.py | Documentation and configuration files |
| repo_b/tests\integration\test_api.py | KEEP | services/clinical_nlp/tests\integration\test_api.py | Documentation and configuration files |
| repo_b/tests\integration\test_team_c_export.py | KEEP | services/clinical_nlp/tests\integration\test_team_c_export.py | Documentation and configuration files |
| repo_b/tests\integration\__init__.py | KEEP | services/clinical_nlp/tests\integration\__init__.py | Documentation and configuration files |
| repo_b/tests\unit\test_adapter.py | KEEP | services/clinical_nlp/tests\unit\test_adapter.py | Documentation and configuration files |
| repo_b/tests\unit\test_extraction.py | KEEP | services/clinical_nlp/tests\unit\test_extraction.py | Documentation and configuration files |
| repo_b/tests\unit\test_grounding.py | KEEP | services/clinical_nlp/tests\unit\test_grounding.py | Documentation and configuration files |
| repo_b/tests\unit\test_llm_layer.py | KEEP | services/clinical_nlp/tests\unit\test_llm_layer.py | Documentation and configuration files |
| repo_b/tests\unit\test_safety.py | KEEP | services/clinical_nlp/tests\unit\test_safety.py | Documentation and configuration files |
| repo_b/tests\unit\__init__.py | KEEP | services/clinical_nlp/tests\unit\__init__.py | Documentation and configuration files |

---

## 3. Repository C Mapping (Authoritative Dashboard & EHR)

| Source Path | Classification | Target Path | Reason / Action |
|-------------|----------------|-------------|-----------------|
| repo_c/.env.example | REFACTOR | .env.example | Root monorepo configuration |
| repo_c/.gitignore | REFACTOR | .gitignore | Root monorepo configuration |
| repo_c/docker-compose.yml | REFACTOR | docker-compose.yml | Root monorepo configuration |
| repo_c/README.md | REFACTOR | README.md | Root monorepo configuration |
| repo_c/backend\pytest.ini | REFACTOR | backend\pytest.ini | Root monorepo configuration |
| repo_c/backend\requirements.txt | REFACTOR | backend\requirements.txt | Root monorepo configuration |
| repo_c/backend\app\auth.py | REFACTOR | backend\app\auth.py | Root monorepo configuration |
| repo_c/backend\app\config.py | REFACTOR | backend\app\config.py | Root monorepo configuration |
| repo_c/backend\app\database.py | REFACTOR | backend\app\database.py | Root monorepo configuration |
| repo_c/backend\app\logging_config.py | REFACTOR | backend\app\logging_config.py | Root monorepo configuration |
| repo_c/backend\app\main.py | REFACTOR | backend\app\main.py | Root monorepo configuration |
| repo_c/backend\app\__init__.py | REFACTOR | backend\app\__init__.py | Root monorepo configuration |
| repo_c/backend\app\api\ehr.py | REFACTOR | backend\app\api\ehr.py | Root monorepo configuration |
| repo_c/backend\app\api\encounters.py | REFACTOR | backend\app\api\encounters.py | Root monorepo configuration |
| repo_c/backend\app\api\__init__.py | REFACTOR | backend\app\api\__init__.py | Root monorepo configuration |
| repo_c/backend\app\integrations\ehr.py | REFACTOR | backend\app\integrations\ehr.py | Root monorepo configuration |
| repo_c/backend\app\integrations\__init__.py | REFACTOR | backend\app\integrations\__init__.py | Root monorepo configuration |
| repo_c/backend\app\models\orm.py | REFACTOR | backend\app\models\orm.py | Root monorepo configuration |
| repo_c/backend\app\models\__init__.py | REFACTOR | backend\app\models\__init__.py | Root monorepo configuration |
| repo_c/backend\app\schemas\team_b.py | REFACTOR | backend\app\schemas\team_b.py | Root monorepo configuration |
| repo_c/backend\app\schemas\__init__.py | REFACTOR | backend\app\schemas\__init__.py | Root monorepo configuration |
| repo_c/backend\app\services\demo.py | REFACTOR | backend\app\services\demo.py | Root monorepo configuration |
| repo_c/backend\app\services\encounter.py | REFACTOR | backend\app\services\encounter.py | Root monorepo configuration |
| repo_c/backend\app\services\fhir.py | REFACTOR | backend\app\services\fhir.py | Root monorepo configuration |
| repo_c/backend\app\services\pdf.py | REFACTOR | backend\app\services\pdf.py | Root monorepo configuration |
| repo_c/backend\app\services\__init__.py | REFACTOR | backend\app\services\__init__.py | Root monorepo configuration |
| repo_c/backend\app\validators\conflicts.py | REFACTOR | backend\app\validators\conflicts.py | Root monorepo configuration |
| repo_c/backend\app\validators\grounding.py | REFACTOR | backend\app\validators\grounding.py | Root monorepo configuration |
| repo_c/backend\app\validators\__init__.py | REFACTOR | backend\app\validators\__init__.py | Root monorepo configuration |
| repo_c/backend\tests\test_api_contract.py | REFACTOR | backend\tests\test_api_contract.py | Root monorepo configuration |
| repo_c/backend\tests\test_pipeline.py | REFACTOR | backend\tests\test_pipeline.py | Root monorepo configuration |
| repo_c/backend\tests\test_safety.py | REFACTOR | backend\tests\test_safety.py | Root monorepo configuration |
| repo_c/docker\backend.Dockerfile | REFACTOR | docker\backend.Dockerfile | Root monorepo configuration |
| repo_c/docker\frontend.Dockerfile | REFACTOR | docker\frontend.Dockerfile | Root monorepo configuration |
| repo_c/docker\init-db.sql | REFACTOR | docker\init-db.sql | Root monorepo configuration |
| repo_c/docker\mock_ehr.Dockerfile | REFACTOR | docker\mock_ehr.Dockerfile | Root monorepo configuration |
| repo_c/docker\nginx.conf | REFACTOR | docker\nginx.conf | Root monorepo configuration |
| repo_c/docker\README.md | REFACTOR | docker\README.md | Root monorepo configuration |
| repo_c/docs\api.md | REFACTOR | docs\api.md | Root monorepo configuration |
| repo_c/docs\architecture.md | REFACTOR | docs\architecture.md | Root monorepo configuration |
| repo_c/docs\team-b.example.json | REFACTOR | docs\team-b.example.json | Root monorepo configuration |
| repo_c/docs\report\build_report.py | REFACTOR | docs\report\build_report.py | Root monorepo configuration |
| repo_c/docs\report\content_ch1_3.py | REFACTOR | docs\report\content_ch1_3.py | Root monorepo configuration |
| repo_c/docs\report\content_ch4_6.py | REFACTOR | docs\report\content_ch4_6.py | Root monorepo configuration |
| repo_c/docs\report\content_ch7_9.py | REFACTOR | docs\report\content_ch7_9.py | Root monorepo configuration |
| repo_c/docs\report\diagrams.py | REFACTOR | docs\report\diagrams.py | Root monorepo configuration |
| repo_c/docs\report\postprocess_report.ps1 | REFACTOR | docs\report\postprocess_report.ps1 | Root monorepo configuration |
| repo_c/docs\report\figures\fig1_1_context.png | REFACTOR | docs\report\figures\fig1_1_context.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_1_architecture.png | REFACTOR | docs\report\figures\fig4_1_architecture.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_2_dfd0.png | REFACTOR | docs\report\figures\fig4_2_dfd0.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_3_dfd1.png | REFACTOR | docs\report\figures\fig4_3_dfd1.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_4_er.png | REFACTOR | docs\report\figures\fig4_4_er.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_5_usecase.png | REFACTOR | docs\report\figures\fig4_5_usecase.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_6_class.png | REFACTOR | docs\report\figures\fig4_6_class.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_7_sequence.png | REFACTOR | docs\report\figures\fig4_7_sequence.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig4_8_state.png | REFACTOR | docs\report\figures\fig4_8_state.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig5_1_gantt.png | REFACTOR | docs\report\figures\fig5_1_gantt.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig8_1_home.png | REFACTOR | docs\report\figures\fig8_1_home.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig8_2_encounter.png | REFACTOR | docs\report\figures\fig8_2_encounter.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig8_3_finalize.png | REFACTOR | docs\report\figures\fig8_3_finalize.png | Root monorepo configuration |
| repo_c/docs\report\figures\fig8_4_audit.png | REFACTOR | docs\report\figures\fig8_4_audit.png | Root monorepo configuration |
| repo_c/frontend\index.html | REFACTOR | frontend\index.html | Root monorepo configuration |
| repo_c/frontend\package-lock.json | REFACTOR | frontend\package-lock.json | Root monorepo configuration |
| repo_c/frontend\package.json | REFACTOR | frontend\package.json | Root monorepo configuration |
| repo_c/frontend\postcss.config.js | REFACTOR | frontend\postcss.config.js | Root monorepo configuration |
| repo_c/frontend\tailwind.config.js | REFACTOR | frontend\tailwind.config.js | Root monorepo configuration |
| repo_c/frontend\tsconfig.json | REFACTOR | frontend\tsconfig.json | Root monorepo configuration |
| repo_c/frontend\vite.config.ts | REFACTOR | frontend\vite.config.ts | Root monorepo configuration |
| repo_c/frontend\src\App.tsx | REFACTOR | frontend\src\App.tsx | Root monorepo configuration |
| repo_c/frontend\src\index.css | REFACTOR | frontend\src\index.css | Root monorepo configuration |
| repo_c/frontend\src\main.tsx | REFACTOR | frontend\src\main.tsx | Root monorepo configuration |
| repo_c/frontend\src\vite-env.d.ts | REFACTOR | frontend\src\vite-env.d.ts | Root monorepo configuration |
| repo_c/frontend\src\components\audit\AuditDrawer.tsx | REFACTOR | frontend\src\components\audit\AuditDrawer.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\finalize\FinalizeDialog.tsx | REFACTOR | frontend\src\components\finalize\FinalizeDialog.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\layout\ActionBar.tsx | REFACTOR | frontend\src\components\layout\ActionBar.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\layout\HeaderBar.tsx | REFACTOR | frontend\src\components\layout\HeaderBar.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\note\SoapEditor.tsx | REFACTOR | frontend\src\components\note\SoapEditor.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\patient\PatientPanel.tsx | REFACTOR | frontend\src\components\patient\PatientPanel.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\transcript\TranscriptViewer.tsx | REFACTOR | frontend\src\components\transcript\TranscriptViewer.tsx | Root monorepo configuration |
| repo_c/frontend\src\components\validation\ValidationPanel.tsx | REFACTOR | frontend\src\components\validation\ValidationPanel.tsx | Root monorepo configuration |
| repo_c/frontend\src\hooks\useEncounter.ts | REFACTOR | frontend\src\hooks\useEncounter.ts | Root monorepo configuration |
| repo_c/frontend\src\pages\EncounterPage.tsx | REFACTOR | frontend\src\pages\EncounterPage.tsx | Root monorepo configuration |
| repo_c/frontend\src\pages\HomePage.tsx | REFACTOR | frontend\src\pages\HomePage.tsx | Root monorepo configuration |
| repo_c/frontend\src\services\api.ts | REFACTOR | frontend\src\services\api.ts | Root monorepo configuration |
| repo_c/frontend\src\types\clinical.ts | REFACTOR | frontend\src\types\clinical.ts | Root monorepo configuration |
| repo_c/frontend\src\utils\format.ts | REFACTOR | frontend\src\utils\format.ts | Root monorepo configuration |
| repo_c/mock_ehr\requirements.txt | REFACTOR | mock_ehr\requirements.txt | Root monorepo configuration |
| repo_c/mock_ehr\api\main.py | REFACTOR | mock_ehr\api\main.py | Root monorepo configuration |
| repo_c/mock_ehr\api\__init__.py | REFACTOR | mock_ehr\api\__init__.py | Root monorepo configuration |