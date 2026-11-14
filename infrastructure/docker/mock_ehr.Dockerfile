# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app
COPY mock_ehr/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 20 --timeout 600 -r /app/requirements.txt
COPY mock_ehr /app
ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
