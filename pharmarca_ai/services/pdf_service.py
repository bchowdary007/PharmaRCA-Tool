from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FOOTER_TEXT = "Designed & Developed by Bhaskar Chowdary"
FISHBONE_ORDER = [
    ("machine", "Machine (Instrument)"),
    ("method", "Method"),
    ("material", "Material"),
    ("measurement", "Measurement"),
    ("mother_nature", "Mother Nature (Environment)"),
    ("man", "Man (Human)"),
]


def _draw_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 0.35 * inch, FOOTER_TEXT)
    canvas.restoreState()


def build_pdf(report: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.55 * inch,
        bottomMargin=0.7 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title="PharmaRCA AI Investigation Report",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], leading=14, spaceAfter=4))

    story: list[Any] = []
    story.append(Paragraph("PharmaRCA AI", styles["Title"]))
    story.append(Paragraph("Deviation Investigation Report", styles["Heading2"]))
    story.append(Spacer(1, 8))

    metadata = report["record_metadata"]
    signature = report["electronic_signature"]
    meta_table = Table(
        [
            ["Record ID", metadata["record_id"], "Timestamp", metadata["timestamp"]],
            ["Version", metadata["version"], "Status", metadata["investigation_status"]],
            ["Prepared By", signature["prepared_by"], "Signature Status", signature["signature_status"]],
            ["Reviewed By", signature["reviewed_by"], "Approved By", signature["approved_by"]]
        ],
        colWidths=[1.1 * inch, 2.1 * inch, 1.2 * inch, 2.3 * inch],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7F0EA")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11)
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 10))

    first_sections = [
        ("Audit Trail", report["audit_trail"].values()),
        ("Deviation Description", report["deviation_description"]),
        ("Initial Assessment", report["initial_assessment"]),
        ("Investigation Plan", report["investigation_plan"]),
    ]

    for title, items in first_sections:
        story.append(Paragraph(title, styles["SectionHeading"]))
        for item in items:
            story.append(Paragraph(f"&bull; {item}", styles["BodySmall"]))

    story.append(Paragraph("Fishbone Analysis (6M)", styles["SectionHeading"]))
    fishbone = report["fishbone_analysis"]
    for key, label in FISHBONE_ORDER:
        category = fishbone[key]
        story.append(Paragraph(label, styles["BodySmall"]))
        story.append(Paragraph(f"&bull; Status: {category['status']}", styles["BodySmall"]))
        story.append(Paragraph("&bull; Possible Causes:", styles["BodySmall"]))
        for item in category["possible_causes"]:
            story.append(Paragraph(f"&bull; {item}", styles["BodySmall"]))
        story.append(Paragraph("&bull; Reasoning:", styles["BodySmall"]))
        for item in category["reasoning"]:
            story.append(Paragraph(f"&bull; {item}", styles["BodySmall"]))

    remaining_sections = [
        ("Investigation Reasoning", report["investigation_reasoning"]),
        ("Possible Root Causes", report["possible_root_causes"]),
        ("Root Cause Analysis", report["root_cause_analysis"]),
        ("Most Probable Root Cause", [report["most_probable_root_cause"]]),
        ("Confidence Level", [report["confidence_level"]]),
        ("Root Cause Classification", [report["root_cause_classification"]]),
        ("Impact Assessment", report["impact_assessment"]),
        ("CAPA - Immediate Correction", report["capa"]["immediate_correction"]),
        ("CAPA - Corrective Action", report["capa"]["corrective_action"]),
        ("CAPA - Preventive Action", report["capa"]["preventive_action"]),
        ("Data Gaps", report["data_gaps"]),
        ("Conclusion", [report["conclusion"]])
    ]

    for title, items in remaining_sections:
        story.append(Paragraph(title, styles["SectionHeading"]))
        for item in items:
            story.append(Paragraph(f"&bull; {item}", styles["BodySmall"]))

    doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
