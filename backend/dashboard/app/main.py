from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.dose import router as dose_router
from .api.ehr import router as ehr_router
from .api.encounters import router as encounter_router
from .config import get_settings
from .database import Base, engine
from .logging_config import configure_logging
from .models import orm  # noqa: F401

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="Clinical Scribe EHR Interface",
    description=(
        "Physician-facing validation dashboard APIs. "
        "AI drafts require explicit physician approval. "
        "This system does not independently diagnose or prescribe."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.exception_handler(HTTPException)
def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
def unhandled(_: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. No stack trace is returned."},
    )


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "privacy": "local_private",
        "role": "clinical_documentation_validation",
        "disclaimer": "AI generates drafts; physicians validate and finalize clinical information.",
    }


app.include_router(encounter_router)
app.include_router(dose_router)
app.include_router(ehr_router)
