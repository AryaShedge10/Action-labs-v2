"""The dose knowledge file must be traceable to the PDF: every value carries a source page, every quote is
verbatim from that page, and the file parses strictly. These tests are the guard against hand-edited / invented values."""

import copy
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from app.dosing.knowledge import DOCUMENT_PAGES, RULES_PATH, DoseKnowledge, load_knowledge
from app.knowledge.drugs import DRUGS

REPO_ROOT = Path(__file__).resolve().parents[4]
PDF = REPO_ROOT / "docs" / "references" / "stg_hypertension_2016.pdf"

# A dict holding any of these keys is a "value" and must be covered by a `source` on itself or an ancestor.
VALUE_KEYS = {"value", "threshold", "sbp_min", "dbp_min", "sbp_greater_than", "dbp_greater_than", "egfr_below",
              "terms", "conditions", "doses_per_day_min", "min_days"}


def unsourced_values(node, covered=False, path="$") -> list[str]:
    """Paths of value-bearing mappings that have no `source.page` on themselves or any ancestor."""
    problems: list[str] = []
    if isinstance(node, dict):
        src = node.get("source")
        has_source = isinstance(src, dict) and isinstance(src.get("page"), int)
        # named sibling sources (e.g. threshold_source) also cover the thresholds next to them
        has_source = has_source or any(k.endswith("_source") and isinstance(v, dict) and isinstance(v.get("page"), int)
                                       for k, v in node.items())
        if "source" in node and not has_source:
            problems.append(f"{path}: source without integer page")
        covered_here = covered or has_source
        if not covered_here and VALUE_KEYS & node.keys():
            problems.append(f"{path}: value without source page")
        for key, child in node.items():
            if key in ("source", "corroborating_sources", "age_definition_source", "population_source"):
                continue
            problems.extend(unsourced_values(child, covered_here, f"{path}.{key}"))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            problems.extend(unsourced_values(child, covered, f"{path}[{i}]"))
    return problems


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load(Path(RULES_PATH).read_text(encoding="utf-8"))


def test_file_validates_and_is_unreviewed_by_default():
    kb = load_knowledge()
    assert isinstance(kb, DoseKnowledge)
    assert kb.reviewed_by_clinician is False
    assert kb.source_document.issuer.startswith("Ministry of Health")
    assert kb.source_document.date == "May 2016"
    assert {"amlodipine", "enalapril", "hydrochlorothiazide"} <= set(kb.drugs)


def test_every_value_has_a_source_page(raw):
    assert unsourced_values(raw) == []


def test_checker_detects_a_value_without_source(raw):
    broken = copy.deepcopy(raw)
    del broken["drugs"]["amlodipine"]["start_dose"]["source"]
    assert any("amlodipine.start_dose" in p for p in unsourced_values(broken))
    broken2 = copy.deepcopy(raw)
    del broken2["drugs"]["enalapril"]["renal_adjustments"][0]["source"]
    assert any("enalapril.renal_adjustments" in p for p in unsourced_values(broken2))


def test_model_rejects_missing_or_out_of_range_page(raw):
    broken = copy.deepcopy(raw)
    del broken["drugs"]["amlodipine"]["max_daily_dose"]["source"]["page"]
    with pytest.raises(Exception):
        DoseKnowledge.model_validate(broken)
    broken = copy.deepcopy(raw)
    broken["drugs"]["amlodipine"]["start_dose"]["source"]["page"] = DOCUMENT_PAGES + 1
    with pytest.raises(Exception):
        DoseKnowledge.model_validate(broken)


def test_model_rejects_unknown_keys(raw):
    broken = copy.deepcopy(raw)
    broken["drugs"]["amlodipine"]["usual_dose_from_memory"] = 7
    with pytest.raises(Exception):
        DoseKnowledge.model_validate(broken)


def test_classes_referenced_exist_in_drug_knowledge_base():
    kb = load_knowledge()
    known = set().union(*(d.classes for d in DRUGS.values()))
    referenced: set[str] = set()
    for drug in kb.drugs.values():
        referenced.add(drug.drug_class)
        for cond in drug.lower_start_conditions:
            referenced.update(cond.test.classes)
    for group in kb.table_10_contraindications:
        referenced.update(group.classes)
    for rule in kb.combination_rules:
        referenced.update(rule.classes_a + rule.classes_b)
    assert referenced <= known, referenced - known


def test_drug_names_agree_with_class_in_drugs_py():
    kb = load_knowledge()
    for drug in kb.drugs.values():
        known = DRUGS.get(drug.generic_name)
        if known is not None:
            assert drug.drug_class in known.classes, drug.generic_name


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _collect_sources(node, out):
    if isinstance(node, dict):
        if "page" in node and "quote" in node:
            out.append(node)
        for child in node.values():
            _collect_sources(child, out)
    elif isinstance(node, list):
        for child in node:
            _collect_sources(child, out)


@pytest.mark.skipif(not PDF.exists() or shutil.which("pdftotext") is None,
                    reason="source PDF or pdftotext not available")
def test_every_quote_appears_on_its_cited_pdf_page(raw):
    sources: list[dict] = []
    _collect_sources(raw, sources)
    assert len(sources) > 80  # sanity: the walk really found the quotes
    page_text: dict[int, str] = {}
    missing = []
    for src in sources:
        page = src["page"]
        if page not in page_text:
            out = subprocess.run(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(PDF), "-"],
                                 capture_output=True, text=True, check=True).stdout
            page_text[page] = _norm(out)
        if _norm(src["quote"]) not in page_text[page]:
            missing.append((page, src["quote"]))
    assert not missing, missing
