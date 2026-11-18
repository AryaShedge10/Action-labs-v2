"""Table 4 (page 8) blood-pressure grading, driven by the knowledge file."""

from __future__ import annotations

from dataclasses import dataclass

from .knowledge import load_knowledge


@dataclass(frozen=True)
class BPGrade:
    label: str
    isolated_systolic: bool
    source_page: int = 8
    source: str = "Table 4: Classification of hypertension"


def parse_bp(value: str) -> tuple[int, int] | None:
    try:
        sbp, dbp = (int(x) for x in value.replace(" ", "").split("/"))
    except (ValueError, AttributeError):
        return None
    return sbp, dbp


def classify_bp(sbp: int, dbp: int) -> BPGrade:
    """Category = the higher of the SBP and DBP categories (Table 4 uses 'and/or')."""
    table = load_knowledge().bp_classification
    best_rank, label = 0, table.categories[0].label
    for cat in table.categories:
        if sbp >= cat.sbp_min and cat.rank > 0 or dbp >= cat.dbp_min and cat.rank > 0:
            if cat.rank >= best_rank:
                best_rank, label = cat.rank, cat.label
    iso = table.isolated_systolic
    return BPGrade(label, isolated_systolic=sbp >= iso.sbp_min and dbp < iso.dbp_below)
