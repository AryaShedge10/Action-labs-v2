from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    physician_id: Mapped[str] = mapped_column(String(64))
    physician_name: Mapped[str] = mapped_column(String(128))
    encounter_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ai_status: Mapped[str] = mapped_column(String(32), default="draft_ready")
    validation_status: Mapped[str] = mapped_column(String(32), default="required")
    workflow_status: Mapped[str] = mapped_column(String(32), default="draft")
    patient: Mapped[dict] = mapped_column(JSON)
    transcript: Mapped[dict] = mapped_column(JSON)
    clinical_note: Mapped[dict] = mapped_column(JSON)
    claims: Mapped[list] = mapped_column(JSON)
    original_note: Mapped[dict] = mapped_column(JSON)
    original_claims: Mapped[list] = mapped_column(JSON)
    acknowledgements: Mapped[dict] = mapped_column(JSON, default=lambda: {})
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    audits: Mapped[list["AuditEvent"]] = relationship(back_populates="encounter")
    handoffs: Mapped[list["EhrHandoff"]] = relationship(back_populates="encounter")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_pk: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    encounter_id: Mapped[str] = mapped_column(String(64), index=True)
    physician_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounter: Mapped[Encounter] = relationship(back_populates="audits")


class EhrHandoff(Base):
    __tablename__ = "ehr_handoffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    encounter_pk: Mapped[int] = mapped_column(ForeignKey("encounters.id"))
    encounter_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(32))
    summary: Mapped[dict] = mapped_column(JSON, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounter: Mapped[Encounter] = relationship(back_populates="handoffs")
