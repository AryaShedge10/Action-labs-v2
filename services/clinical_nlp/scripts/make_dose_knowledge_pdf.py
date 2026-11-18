"""Generate a reviewer-friendly PDF of everything the dose feature uses from the MoHFW STG Hypertension 2016 PDF.

Built from the same validated knowledge file the engine loads, so the document cannot drift from the software.
    python scripts/make_dose_knowledge_pdf.py [output.pdf]
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.dosing.knowledge import load_knowledge  # noqa: E402

kb = load_knowledge()
ss = getSampleStyleSheet()
BODY = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
SMALL = ParagraphStyle("s", parent=BODY, fontSize=8, leading=10)
CELL = ParagraphStyle("c", parent=BODY, fontSize=8, leading=10, alignment=TA_LEFT)
CELLB = ParagraphStyle("cb", parent=CELL, fontName="Helvetica-Bold")
H1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#14405a"))
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5, spaceBefore=8, spaceAfter=3, textColor=colors.HexColor("#14405a"))
NAVY = colors.HexColor("#14405a")


def p(text, style=CELL):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)


def src(s):
    return f"p{s.page} · {s.table_or_section}"


def table(rows, widths, header=True):
    data = [[c if not isinstance(c, str) else p(c, CELLB if (header and i == 0) else CELL) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#b8c4cc")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e3edf3"))]
    t.setStyle(TableStyle(style))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#555"))
    canvas.drawString(15 * mm, 9 * mm, "Decision support prototype, not for clinical use. Values NOT yet reviewed by a doctor or pharmacist.")
    canvas.drawRightString(195 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def cond_text(t):
    return {"gt": f"{t.fact} > {t.threshold:g}" if t.threshold is not None else "", "lt": f"{t.fact} < {t.threshold:g}" if t.threshold is not None else "",
            "is_true": f"{t.fact} is true", "other_drug_in_classes": "patient already takes another drug from: " + ", ".join(t.classes),
            "judgment": "clinician judgment only - the PDF gives no measurable criterion (never applied automatically)"}.get(t.op, t.op)


def build(out: Path):
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title="Information used from MoHFW STG Hypertension 2016", author="Clinical Scribe dose-suggestion prototype")
    sd = kb.source_document
    s = []
    s.append(Paragraph("Information used from the Government Hypertension Guideline", ParagraphStyle("t", parent=H1, fontSize=19, spaceAfter=2)))
    s.append(Paragraph("Dose-suggestion feature - what we take from the PDF, and from which page", BODY))
    s.append(Spacer(1, 4))
    s.append(table([
        ["Source document", sd.title],
        ["Issuer / date", f"{sd.issuer} - {sd.date}"],
        ["File", f"{sd.file}  ({sd.pages} pages; printed page number = PDF page number)"],
        ["Population", sd.population + " - the tool refuses patients under 18"],
        ["Clinician review", "NOT reviewed (reviewed_by_clinician = false). Every value must be confirmed by a doctor or pharmacist before any real use."],
    ], [38, 142], header=False))
    s.append(Spacer(1, 6))
    s.append(Paragraph("<b>Ground rules.</b> Doses come only from this PDF. The software never uses remembered values and the language model never computes or suggests doses. "
                       "If a drug or value is not in the PDF the answer is NOT SUPPORTED; if a patient fact is missing the answer is NEEDS INFO. The output is a suggestion for the doctor, never an order.", BODY))
    s.append(Paragraph("What we use, at a glance", H2))
    s.append(table([
        ["Section", "Source in PDF", "Used for"],
        ["1. bp_classification", "Table 4, p8", "Grading blood pressure: Optimal, Normal, High Normal, Grade 1-3, isolated systolic"],
        ["2. hypertensive_crisis", "Tables 3 and 4 (p7-8), 4.9.1 (p25), 4.10.1 (p26), Pathway 7 (p37)", "BP above 180/110, and the ABCDEFG warning symptoms (altered consciousness, breathlessness, chest pain, ...)"],
        ["3. table_10_contraindications", "Table 10, p16", "Drug class vs condition, e.g. beta-blockers with asthma or AV block, diuretics with gout"],
        ["4. combination_rules", "Annexure 3 formulary: p48 (amlodipine), p49 (enalapril), p51 (thiazides)", "Class pairs to avoid, and the simvastatin dose cap with amlodipine"],
        ["5. unsupported_drugs", "Table 12 (p20), Table 10 (p16)", "Drugs the guideline gives no usable dose for (metoprolol without 'succinate', spironolactone)"],
        ["6. drugs", "Annexure 3 formulary (p47-52) and Table 12 (p20)", "Per drug: start dose, frequency, maximum, titration, lower-start conditions, renal and hepatic rules, contraindications, cautions, pregnancy"],
    ], [38, 62, 80]))
    s.append(Spacer(1, 3))
    s.append(Paragraph("Note: the combination rules come from the Annexure 3 formulary text, not the management pathway.", SMALL))

    # 1
    s.append(PageBreak())
    s.append(Paragraph("1. Blood-pressure classification - Table 4, page 8", H1))
    rows = [["Category", "Systolic (mmHg)", "Diastolic (mmHg)", "Source"]]
    ranges = {"Optimal": ("< 120", "and < 80"), "Normal": ("120-129", "and/or 80-84"), "High Normal": ("130-139", "and/or 85-89"),
              "Grade 1 Hypertension": ("140-159", "and/or 90-99"), "Grade 2 Hypertension": ("160-179", "and/or 100-109"),
              "Grade 3 Hypertension": (">= 180", "and/or >= 110")}
    for c in kb.bp_classification.categories:
        a, b = ranges[c.label]
        rows.append([c.label, a, b, src(c.source)])
    i = kb.bp_classification.isolated_systolic
    rows.append([i.label, f">= {i.sbp_min}", f"and < {i.dbp_below}", src(i.source)])
    s.append(table(rows, [48, 32, 34, 66]))
    s.append(Paragraph("How we apply it: the category is the higher of the systolic and diastolic categories (Table 4 uses 'and/or'). Used for the grade label shown in blood-pressure alerts.", SMALL))

    # 2
    c = kb.hypertensive_crisis
    s.append(Paragraph("2. Hypertensive crisis - Tables 3 and 4, pages 7-8 (and p25, p26, p37)", H1))
    s.append(table([
        ["Rule", "How the software applies it", "Source"],
        ["Trigger", f"Systolic > {c.sbp_greater_than} and/or diastolic > {c.dbp_greater_than} mmHg (strictly greater; exactly 180/110 does not trigger; 175/105 never triggers)", src(c.threshold_source)],
        ["With any ABCDEFG symptom", "CRITICAL alert: 'treat as hypertensive emergency'", src(c.emergency_rule_source) + "; " + src(c.pathway_source)],
        ["Without ABCDEFG symptoms", "REVIEW (high severity): possible hypertensive urgency - doctor to check A-G", src(c.urgency_rule_source)],
    ], [34, 100, 46]))
    s.append(Spacer(1, 4))
    rows = [["Letter", "Warning symptom / sign (verbatim meaning)", "Words the extractor recognises", "Source"]]
    for w in c.warning_symptoms:
        rows.append([w.letter, w.label, ", ".join(w.terms), src(w.source)])
    s.append(table(rows, [12, 62, 56, 50]))
    s.append(Paragraph("A symptom counts only if affirmed (present or possible) - negated symptoms ('no chest pain') do not. Headache alone is not an ABCDEFG symptom (p26: 'relatively asymptomatic except for a mild headache').", SMALL))

    # 3
    s.append(Paragraph("3. Contraindications by drug class - Table 10, page 16", H1))
    rows = [["Drug group (Table 10)", "Compelling contraindication (alert / NOT RECOMMENDED)", "Possible contraindication (warning only)", "Our drug classes"]]
    for g in kb.table_10_contraindications:
        comp = "\n".join(("- " + x.label + ("  [pregnancy handled by existing pregnancy rule]" if x.handled_by_existing_rule else "")) for x in g.compelling) or "-"
        poss = "\n".join("- " + x.label for x in g.possible) or "-"
        rows.append([g.group, comp, poss, ", ".join(g.classes)])
    s.append(table(rows, [38, 56, 50, 36]))
    s.append(Paragraph("Table 10 lists 'Diuretics' generally; we apply it to thiazide and loop diuretics. Table 10 also lists non-dihydropyridine calcium channel blockers; these are not in our drug list so no rule is built for them. Spironolactone uses eGFR < 30 ml/min.", SMALL))

    # 4
    s.append(Paragraph("4. Combination and dose-cap rules - Annexure 3 formulary", H1))
    rows = [["Rule", "Severity", "Source"]]
    for r in kb.combination_rules:
        rows.append([r.message + (f" ({r.label})" if r.label else ""), r.severity, src(r.source)])
    s.append(table(rows, [98, 18, 64]))
    s.append(Paragraph("Quotes: " + " | ".join(f'"{r.source.quote}"' for r in kb.combination_rules), SMALL))

    # 5
    s.append(Paragraph("5. Drugs the guideline gives no usable dose for", H1))
    rows = [["Drug entered", "Result", "Why", "Source"]]
    for u in kb.unsupported_drugs:
        rows.append([u.name, "NOT SUPPORTED", u.reason, src(u.source)])
    rows.append(["any other drug (e.g. ibuprofen, ramipril, nifedipine)", "NOT SUPPORTED", "Not in the PDF's dose tables - nothing is guessed.", "-"])
    rows.append(["combination brands (e.g. Combiflam)", "NOT SUPPORTED", "The guideline gives single-drug doses only.", "-"])
    s.append(table(rows, [44, 26, 66, 44]))

    # 6
    s.append(PageBreak())
    s.append(Paragraph("6. Drugs - Annexure 3 formulary (p47-52) and Table 12 (p20)", H1))
    s.append(Paragraph("Tier 'formulary' = full Annexure 3 entry (amlodipine, enalapril, hydrochlorothiazide). Tier 'dose table only' = only start dose, maximum and doses per day from Table 12 (page 20).", SMALL))
    summary = [["Drug", "Class", "Start dose", "Max / day", "Doses / day", "Tier", "Source"]]
    for k, d in kb.drugs.items():
        summary.append([d.generic_name, d.drug_class.replace("_", " "), f"{d.start_dose.value:g} {d.start_dose.unit}", f"{d.max_daily_dose.value:g} {d.max_daily_dose.unit}",
                        d.frequency.value, "formulary" if d.evidence_tier == "formulary" else "dose table only", src(d.start_dose.source)])
    s.append(table(summary, [30, 28, 17, 17, 34, 20, 34]))

    for k, d in kb.drugs.items():
        blk = [Paragraph(d.generic_name.title(), H2)]
        rows = [["Item", "Value used", "Source"]]
        if d.class_label:
            rows.append(["Class", d.class_label.value, src(d.class_label.source)])
        if d.indication:
            rows.append(["Indication", d.indication.value, src(d.indication.source)])
        rows.append(["Start dose", f"{d.start_dose.value:g} {d.start_dose.unit}", src(d.start_dose.source)])
        rows.append(["Frequency", d.frequency.value, src(d.frequency.source)])
        rows.append(["Maximum per day", f"{d.max_daily_dose.value:g} {d.max_daily_dose.unit}" + (f"\n{d.max_daily_dose.note}" if d.max_daily_dose.note else ""), src(d.max_daily_dose.source)])
        if d.usual_ceiling_dose:
            rows.append(["Usual ceiling", f"{d.usual_ceiling_dose.value:g} {d.usual_ceiling_dose.unit} (benefit above this may be minimal)", src(d.usual_ceiling_dose.source)])
        if d.titration_interval:
            rows.append(["Titration interval", d.titration_interval.value, src(d.titration_interval.source)])
        for lc in d.lower_start_conditions:
            rows.append([f"Lower start dose: {lc.id.replace('_', ' ')}", f"{lc.start_dose.value:g} {lc.start_dose.unit} when {cond_text(lc.test)}\n({lc.description})", src(lc.source)])
        for r in d.renal_adjustments:
            if r.test.op == "none":
                rows.append(["Renal", r.description, src(r.source)])
            else:
                eff = f"set {r.start_dose.value:g} {r.start_dose.unit} {r.frequency or ''}".strip() if r.effect == "set_dose" else "AVOID (NOT RECOMMENDED)"
                rows.append(["Renal adjustment", f"Creatinine clearance < {r.test.threshold:g} ml/min -> {eff}", src(r.source)])
        if d.hepatic:
            rows.append(["Hepatic", ("Lower start dose (see above). " if d.hepatic.effect == "lower_start" else "Warning: ") + d.hepatic.text, src(d.hepatic.source)])
        for ci in d.contraindications:
            rows.append(["Contraindication", ci.text, src(ci.source)])
        for ca in d.cautions:
            rows.append(["Caution", ca.text, src(ca.source)])
        if d.pregnancy:
            rows.append(["Pregnancy", f"[{d.pregnancy.effect.replace('_', ' ')}] {d.pregnancy.text}", src(d.pregnancy.source)])
        else:
            rows.append(["Pregnancy", "No statement for this drug in the PDF (class rule from Table 10 may still apply)", "-"])
        blk.append(table(rows, [34, 96, 50]))
        s.append(KeepTogether(blk) if len(rows) < 9 else blk[0]); 
        if len(rows) >= 9:
            s.append(blk[1])

    # appendix
    s.append(PageBreak())
    s.append(Paragraph("Inconsistencies inside the PDF and judgement calls", H1))
    rows = [["Issue", "What the PDF says", "What the software uses"]]
    for d in kb.document_discrepancies:
        rows.append([d.id.replace("_", " "), d.description + "\n" + "\n".join(f"{src(x)}: \"{x.quote}\"" for x in d.sources), d.used])
    s.append(table(rows, [32, 100, 48]))
    s.append(Spacer(1, 6))
    s.append(Paragraph("Other calls to confirm", H2))
    for line in [
        "Metoprolol succinate: Table 12 prints '2 doses per day' - kept as printed; unusual for succinate, please check.",
        "Amlodipine 'small patients' and atenolol 25 mg 'in certain situations' have no measurable criterion in the PDF, so they appear as warnings and are never applied automatically.",
        "Hepatic impairment is recorded as yes/no, so 'avoid in severe liver disease' (thiazides) is shown as a warning, not an automatic refusal.",
        "Table 10 'Diuretics' is applied to loop diuretics as well as thiazides.",
        "Conditions are checked only against the documented list; a condition not mentioned is not proof it is absent.",
        "Eclampsia can occur below 180/110 (p25); not implemented.",
    ]:
        s.append(Paragraph("&bull; " + escape(line), BODY))
    s.append(Spacer(1, 10))
    s.append(Paragraph("Reviewer sign-off", H2))
    s.append(table([["Reviewer name / role", "Date", "Values confirmed (Y/N)", "Comments"], ["", "", "", ""], ["", "", "", ""]], [50, 25, 35, 70]))
    doc.build(s, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "docs" / "dose_knowledge_summary.pdf"
    build(target)
    print(target)
