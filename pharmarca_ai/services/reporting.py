from __future__ import annotations

import json
from typing import Any


FISHBONE_ORDER = [
    ("machine", "Machine (Instrument)"),
    ("method", "Method"),
    ("material", "Material"),
    ("measurement", "Measurement"),
    ("mother_nature", "Mother Nature (Environment)"),
    ("man", "Man (Human)"),
]


def render_report_text(report: dict[str, Any]) -> str:
    lines: list[str] = []

    def add_section(title: str, values: list[str]) -> None:
        lines.append(title)
        for value in values:
            lines.append(f"- {value}")
        lines.append("")

    metadata = report["record_metadata"]
    add_section(
        "Record Metadata",
        [
            f"Record ID: {metadata['record_id']}",
            f"Timestamp: {metadata['timestamp']}",
            f"Version: {metadata['version']}",
            f"Investigation Status: {metadata['investigation_status']}",
            f"Record Type: {metadata['record_type']}",
        ],
    )

    signature = report["electronic_signature"]
    add_section(
        "Electronic Signature",
        [
            f"Prepared By: {signature['prepared_by']}",
            f"Reviewed By: {signature['reviewed_by']}",
            f"Approved By: {signature['approved_by']}",
            f"Signature Status: {signature['signature_status']}",
        ],
    )

    audit = report["audit_trail"]
    add_section(
        "Audit Trail",
        [
            f"Creation Event: {audit['creation_event']}",
            f"Input Traceability: {audit['input_traceability']}",
            f"Modification Status: {audit['modification_status']}",
        ],
    )

    add_section("Deviation Description", report["deviation_description"])
    add_section("Initial Assessment", report["initial_assessment"])
    add_section("Investigation Plan", report["investigation_plan"])

    lines.append("Fishbone Analysis (6M)")
    fishbone = report["fishbone_analysis"]
    for key, label in FISHBONE_ORDER:
        category = fishbone[key]
        lines.append(f"- {label}:")
        lines.append(f"  - Status: {category['status']}")
        lines.append("  - Possible Causes:")
        for item in category["possible_causes"]:
            lines.append(f"    - {item}")
        lines.append("  - Reasoning:")
        for item in category["reasoning"]:
            lines.append(f"    - {item}")
    lines.append("")

    add_section("Investigation Reasoning", report["investigation_reasoning"])
    add_section("Possible Root Causes", report["possible_root_causes"])
    add_section("Root Cause Analysis", report["root_cause_analysis"])
    add_section("Most Probable Root Cause", [report["most_probable_root_cause"]])
    add_section("Confidence Level", [report["confidence_level"]])
    add_section("Root Cause Classification", [report["root_cause_classification"]])
    add_section("Impact Assessment", report["impact_assessment"])
    add_section("CAPA - Immediate Correction", report["capa"]["immediate_correction"])
    add_section("CAPA - Corrective Action", report["capa"]["corrective_action"])
    add_section("CAPA - Preventive Action", report["capa"]["preventive_action"])
    add_section("Data Gaps", report["data_gaps"])
    add_section("Conclusion", [report["conclusion"]])

    return "\n".join(lines).strip()


def safe_json_loads(raw_response: str) -> dict[str, Any]:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"AI response was not valid JSON: {exc}") from exc
