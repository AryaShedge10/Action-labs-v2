"""Pydantic schema for LLM extraction output; its JSON schema is passed to Ollama's `format` parameter.

Decoding is constrained to this shape, so the model cannot emit an unknown type/status or drop a required
field. Evidence checks (segment id, verbatim quote, ...) still happen in `LLMExtractor`, never here.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EntityTypeName = Literal["SYMPTOM", "FINDING", "ALLERGY", "MEDICATION", "VITAL", "DIAGNOSIS", "PROCEDURE", "DEMOGRAPHIC"]
StatusName = Literal["PRESENT", "ABSENT", "POSSIBLE", "HISTORICAL", "CURRENT", "STOPPED", "RECOMMENDED",
                     "PRESCRIBED", "FAMILY_MEMBER", "UNKNOWN"]


class LLMEntity(BaseModel):
    type: EntityTypeName
    surface_text: str = Field(description="The words as spoken / transcribed, misspellings included")
    normalized: str = Field(description="Canonical clinical term or generic drug name")
    status: StatusName
    segment_id: str
    quote: str = Field(description="Verbatim words copied from the cited segment")
    value: str | None = None
    unit: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)


class LLMExtraction(BaseModel):
    entities: list[LLMEntity]


def extraction_json_schema() -> dict:
    return LLMExtraction.model_json_schema()
