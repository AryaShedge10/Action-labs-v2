# Known Technical Issues, Discrepancies, and Resolutions

| Issue ID | Severity | Component | Description | Resolution / Status |
|----------|----------|-----------|-------------|---------------------|
| ISS-001 | High | Transcription (2A) | `live_routes.py` bound to server hardware microphone via `sounddevice`. In cloud/Docker environments, remote clients cannot record audio. | Introduced browser-based audio capture via HTML5 `MediaRecorder` and HTTP multipart upload route to Transcription service. |
| ISS-002 | Critical | Transcription (2A) | `app/services/llm_correction.py` transmitted transcript text to external Groq API without explicit HIPAA disclosure. | Made external LLM processing explicit and disabled by default (`ENABLE_EXTERNAL_LLM=false`). Implemented offline heuristic content-based role detection. |
| ISS-003 | Medium | Transcription (2A) | UTF-8 BOM (`\ufeff`) in `app/api/routes.py` caused AST parsing and linting failures. | Stripped BOM character and saved with standard UTF-8 encoding. |
| ISS-004 | Critical | Schema Incompatibility | Field name divergence: 2A outputs `start_time`/`end_time`; 2C expects `start`/`end`. | Standardized shared contract with Pydantic field aliases and bidirectional converters. |
| ISS-005 | High | Schema Incompatibility | 2C schema required integer `age`, failing on real transcripts with unstated patient age. | Merged 2B's fix into authoritative 2C schema: `age: int | None = None` across backend and frontend TypeScript types. |
| ISS-006 | Medium | Clinical NLP (2B) | Repository B duplicated Repository C's `backend/`, `frontend/`, and `mock_ehr/`, creating divergent codebases. | Excluded duplicate directories from 2B, merged the nullable age improvement into 2C, and unified repository. |
| ISS-007 | Medium | Dashboard Auth (2C) | Demo authentication in `auth.py` accepted any non-empty string as a Bearer token without verification. | Clearly isolated `AUTH_DISABLED=true` demo mode from production token validation hook; added role-based check enforcing physician privileges. |
| ISS-008 | Low | Environment / Hardware | Faster-Whisper and Pyannote may fail without GPU/CUDA. | Added CPU fallback mode (`WHISPER_DEVICE=cpu`, `compute_type=float32`) and heuristic diarization fallback when HuggingFace tokens are not provided. |

