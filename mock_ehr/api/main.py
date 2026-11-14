"""Mock OpenEMR-style EHR adapter. Stores physician-finalized FHIR bundles only."""

import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import JSON, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv(
    "EHR_DATABASE_URL",
    "postgresql+psycopg://clinical:clinical@localhost:5432/mock_ehr",
)


class Base(DeclarativeBase):
    pass


class StoredBundle(Base):
    __tablename__ = "ehr_bundles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(64), index=True)
    patient_id: Mapped[str] = mapped_column(String(64), index=True)
    physician_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    bundle: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


try:
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
except Exception:
    DATABASE_URL = "sqlite:///mock_ehr.db"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
app = FastAPI(title="Mock EHR Adapter", docs_url="/docs")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


class HandoffIn(BaseModel):
    encounter_id: str
    physician_id: str
    bundle: dict
    patient: dict


@app.get("/health")
def health():
    return {"status": "ok", "system": "mock_ehr"}


@app.post("/api/handoff")
def receive_handoff(body: HandoffIn):
    if body.bundle.get("resourceType") != "Bundle":
        raise HTTPException(status_code=400, detail="FHIR validation failed.")
    patient_id = body.patient.get("id")
    if not patient_id:
        raise HTTPException(status_code=400, detail="Missing patient identifier.")
    resources = [
        entry.get("resource", {}).get("resourceType")
        for entry in body.bundle.get("entry", [])
    ]
    with SessionLocal() as db:
        row = StoredBundle(
            encounter_id=body.encounter_id,
            patient_id=patient_id,
            physician_id=body.physician_id,
            status="SUCCESS",
            bundle={"resourceTypes": resources, "entryCount": len(resources)},
        )
        db.add(row)
        db.commit()
    return {
        "status": "SUCCESS",
        "patient": "matched",
        "encounter": "matched",
        "fhir_bundle": "valid",
        "clinical_note": "submitted",
        "medications": "submitted"
        if "MedicationRequest" in resources or "MedicationStatement" in resources
        else "none",
        "allergies": "submitted" if "AllergyIntolerance" in resources else "none",
        "message": "Mock EHR accepted physician-finalized bundle.",
    }


@app.get("/api/encounters/{encounter_id}")
def lookup(encounter_id: str):
    with SessionLocal() as db:
        row = (
            db.query(StoredBundle)
            .filter_by(encounter_id=encounter_id)
            .order_by(StoredBundle.id.desc())
            .first()
        )
    if not row:
        raise HTTPException(status_code=404, detail="Encounter lookup failed.")
    return {
        "encounter_id": row.encounter_id,
        "patient_id": row.patient_id,
        "status": row.status,
        "stored": row.bundle,
    }
