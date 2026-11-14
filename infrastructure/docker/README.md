# Docker

Services: `postgres`, `backend`, `frontend`, `mock_ehr`.

- Frontend: port 8080 (nginx proxies `/api` to the backend)
- Backend: port 8000
- Mock EHR: port 8001
- Postgres: port 5432

Secrets belong in `.env`, never in images. Rotate `SECRET_KEY` and database passwords before any non-demo deployment.

To keep PHI on a private network, do not publish ports beyond the host you control, and do not attach public telemetry sidecars.
