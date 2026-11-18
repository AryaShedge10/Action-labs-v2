"""Print every value in the dose knowledge file with its PDF page, for line-by-line verification.

    python scripts/print_dose_knowledge.py            # markdown table
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dosing.knowledge import DrugEntry, load_knowledge  # noqa: E402


def src(s) -> str:
    return f"p{s.page} {s.table_or_section}"


def rows(key: str, d: DrugEntry):
    yield key, "class", f"{d.drug_class} ({d.class_label.value if d.class_label else 'no label in PDF table'})", (
        src(d.class_label.source) if d.class_label else "Table 12 (p20)")
    if d.indication:
        yield key, "indication", d.indication.value, src(d.indication.source)
    yield key, "start dose", f"{d.start_dose.value:g} {d.start_dose.unit}", src(d.start_dose.source)
    yield key, "frequency", d.frequency.value, src(d.frequency.source)
    yield key, "max daily dose", f"{d.max_daily_dose.value:g} {d.max_daily_dose.unit}", src(d.max_daily_dose.source)
    if d.usual_ceiling_dose:
        yield key, "usual ceiling", f"{d.usual_ceiling_dose.value:g} {d.usual_ceiling_dose.unit}", src(d.usual_ceiling_dose.source)
    if d.titration_interval:
        yield key, "titration interval", d.titration_interval.value, src(d.titration_interval.source)
    for c in d.lower_start_conditions:
        t = c.test
        crit = {"gt": f"{t.fact} > {t.threshold:g}" if t.threshold is not None else "", "lt": f"{t.fact} < {t.threshold:g}" if t.threshold is not None else "",
                "is_true": t.fact, "other_drug_in_classes": "on other drug in " + "/".join(t.classes),
                "judgment": "clinician judgment (no criterion in PDF)"}.get(t.op, t.op)
        yield key, f"lower start: {c.id}", f"{c.start_dose.value:g} {c.start_dose.unit} when {crit}", src(c.source)
    for r in d.renal_adjustments:
        if r.test.op == "none":
            yield key, "renal", r.description, src(r.source)
        else:
            what = (f"set {r.start_dose.value:g} {r.start_dose.unit} {r.frequency or ''}".strip()
                    if r.effect == "set_dose" else "avoid")
            yield key, "renal", f"CrCl < {r.test.threshold:g} ml/min -> {what}", src(r.source)
    if d.hepatic:
        yield key, "hepatic", f"[{d.hepatic.effect}] {d.hepatic.text}", src(d.hepatic.source)
    for c in d.contraindications:
        yield key, "contraindication", c.text, src(c.source)
    for c in d.cautions:
        yield key, "caution", c.text, src(c.source)
    if d.pregnancy:
        yield key, "pregnancy", f"[{d.pregnancy.effect}] {d.pregnancy.text}", src(d.pregnancy.source)


def main() -> None:
    k = load_knowledge()
    print(f"reviewed_by_clinician: {k.reviewed_by_clinician}")
    print(f"source: {k.source_document.title} | {k.source_document.issuer} | {k.source_document.date}\n")
    print("| Drug | Field | Value | PDF source |\n|---|---|---|---|")
    for key, d in k.drugs.items():
        for r in rows(key, d):
            print("| " + " | ".join(str(x).replace("|", "/") for x in r) + " |")
    print("\n| Table 4 category | SBP >= | DBP >= | PDF source |\n|---|---|---|---|")
    for c in k.bp_classification.categories:
        print(f"| {c.label} | {c.sbp_min} | {c.dbp_min} | {src(c.source)} |")
    i = k.bp_classification.isolated_systolic
    print(f"| {i.label} | {i.sbp_min} | DBP < {i.dbp_below} | {src(i.source)} |")
    print("\n| Table 10 group | Compelling | Possible | PDF source |\n|---|---|---|---|")
    for g in k.table_10_contraindications:
        print(f"| {g.group} | {', '.join(x.label for x in g.compelling) or '-'} | "
              f"{', '.join(x.label for x in g.possible) or '-'} | p16 Table 10 |")
    print("\n| Combination / cap rule | Severity | PDF source |\n|---|---|---|")
    for r in k.combination_rules:
        print(f"| {r.message} | {r.severity} | {src(r.source)} |")
    print("\nDocument discrepancies:")
    for d in k.document_discrepancies:
        print(f"- {d.id}: {d.description} (used: {d.used})")


if __name__ == "__main__":
    main()
