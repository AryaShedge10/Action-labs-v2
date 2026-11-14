from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..models.orm import Encounter
from ..schemas.team_b import ClinicalNote, Patient
from ..validators.grounding import validate_encounter
from ..schemas.team_b import Claim, Transcript


NAVY = colors.HexColor("#0f3d4c")
RULE = colors.HexColor("#c5d0d3")


def _section_text(note: ClinicalNote, name: str) -> str:
    items = getattr(note, name)
    lines = [item.text for item in items if not item.deleted]
    if not lines:
        return "None recorded."
    return "<br/>".join(f"• {line}" for line in lines)


def build_pdf(encounter: Encounter) -> bytes:
    patient = Patient.model_validate(encounter.patient)
    note = ClinicalNote.model_validate(encounter.clinical_note)
    claims = [Claim.model_validate(item) for item in encounter.claims]
    transcript = Transcript.model_validate(encounter.transcript)
    validation = validate_encounter(patient, transcript, claims)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.7 * inch,
        title=f"Clinical Encounter Note {encounter.encounter_id}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleClinical",
        parent=styles["Title"],
        fontName="Times-Bold",
        fontSize=16,
        textColor=NAVY,
        spaceAfter=8,
        alignment=0,
    )
    heading = ParagraphStyle(
        "HeadingClinical",
        parent=styles["Heading2"],
        fontName="Times-Bold",
        fontSize=11,
        textColor=NAVY,
        spaceBefore=12,
        spaceAfter=4,
        borderPadding=2,
    )
    body = ParagraphStyle(
        "BodyClinical",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=10,
        leading=14,
    )
    small = ParagraphStyle(
        "SmallClinical",
        parent=styles["BodyText"],
        fontName="Times-Italic",
        fontSize=8,
        textColor=colors.HexColor("#4b5c61"),
    )

    story = [
        Paragraph("CLINICAL ENCOUNTER NOTE", title),
        Paragraph(
            "AI-generated draft reviewed by a physician. Not an independent diagnosis.",
            small,
        ),
        Spacer(1, 8),
        Paragraph("Patient Information", heading),
        Paragraph(
            f"Name: {patient.name}<br/>"
            f"Patient ID: {patient.id}<br/>"
            f"Age: {patient.age}<br/>"
            f"Date of birth: {patient.date_of_birth or '—'}<br/>"
            f"Sex: {patient.sex}<br/>"
            f"Allergies: {', '.join(patient.allergies) or 'None recorded'}<br/>"
            f"Current medications: {', '.join(patient.medications) or 'None recorded'}",
            body,
        ),
        Paragraph("Encounter Information", heading),
        Paragraph(
            f"Encounter ID: {encounter.encounter_id}<br/>"
            f"Date: {encounter.encounter_at.strftime('%d %B %Y %H:%M UTC')}<br/>"
            f"Physician: {encounter.physician_name}<br/>"
            f"Status: {encounter.workflow_status}",
            body,
        ),
    ]
    for name, label in (
        ("subjective", "Subjective"),
        ("objective", "Objective"),
        ("assessment", "Assessment"),
        ("plan", "Plan"),
    ):
        story.append(Paragraph(label, heading))
        story.append(Paragraph(_section_text(note, name), body))

    summary = validation["summary"]
    story.append(Paragraph("Validation Summary", heading))
    table = Table(
        [
            ["Grounding score (evidence alignment)", f"{summary['grounding_score']}%"],
            ["Citation coverage", f"{summary['citation_coverage']}%"],
            ["Unsupported claims", str(summary["unsupported_claims"])],
            ["Critical conflicts", str(validation["critical_conflicts"])],
            [
                "Physician review",
                "Finalized" if encounter.workflow_status == "finalized" else "Not finalized",
            ],
            ["Physician", encounter.physician_name],
        ],
        colWidths=[3.6 * inch, 3.2 * inch],
    )
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "Generated using privacy-preserving clinical documentation software. "
            "Physician review and approval required. Grounding score is not a measure of clinical accuracy.",
            small,
        )
    )

    def footer(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(0.7 * inch, 0.5 * inch, letter[0] - 0.7 * inch, 0.5 * inch)
        canvas.setFont("Times-Italic", 8)
        canvas.setFillColor(colors.HexColor("#4b5c61"))
        canvas.drawString(
            0.7 * inch,
            0.32 * inch,
            "Generated using privacy-preserving clinical documentation software. Physician review and approval required.",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
