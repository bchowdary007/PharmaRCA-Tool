from __future__ import annotations

import json
from typing import Any

import streamlit as st

from pharmarca_ai.config import get_config
from pharmarca_ai.services.ai_service import generate_investigation_report
from pharmarca_ai.services.database import (
    get_audit_trail,
    get_record_by_id,
    initialize_database,
    list_records,
    log_audit_event,
    save_record,
)
from pharmarca_ai.services.pdf_service import build_pdf
from pharmarca_ai.services.rca_engine import score_root_causes
from pharmarca_ai.services.reporting import render_report_text
from pharmarca_ai.services.utils import current_timestamp, generate_record_uid


INSTRUMENT_OPTIONS = ["HPLC", "GC", "Dissolution", "UV", "FTIR", "Other"]
CREDITS_TEXT = "Designed & Developed by Bhaskar Chowdary"


def initialize_state() -> None:
    st.session_state.setdefault("generated_report", None)
    st.session_state.setdefault("generated_payload", None)
    st.session_state.setdefault("generated_pdf", None)
    st.session_state.setdefault("saved_record_id", None)
    st.session_state.setdefault("gemini_api_key", "")


def build_case_input(
    problem: str,
    instrument: str,
    test: str,
    observation: str,
    analyst_name: str,
) -> dict[str, Any]:
    return {
        "problem": problem.strip(),
        "instrument": instrument.strip(),
        "test": test.strip(),
        "observation": observation.strip(),
        "analyst_name": analyst_name.strip(),
    }


def _derive_risk_level(assessment_items: list[str]) -> str:
    for level in ("Critical", "Major", "Minor"):
        if any(level.lower() in item.lower() for item in assessment_items):
            return level
    return "Major"


def resolve_api_key(config) -> str:
    manual_key = st.session_state.get("gemini_api_key", "").strip()
    return manual_key or config.gemini_api_key


def generate_report_workflow(config, case_input: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    record_uid = generate_record_uid()
    version = 1
    timestamp = current_timestamp()

    metadata = {
        "record_id": record_uid,
        "timestamp": timestamp,
        "version": str(version),
        "investigation_status": "Under Investigation",
        "record_type": "Electronic Record",
    }
    signature = {
        "prepared_by": case_input["analyst_name"],
        "reviewed_by": "Pending QA Review",
        "approved_by": "Pending QA Approval",
        "signature_status": "Draft - Not Electronically Signed",
    }
    audit = {
        "creation_event": f"Record generated in PharmaRCA AI on {timestamp}",
        "input_traceability": (
            f"Problem={case_input['problem']}; Instrument={case_input['instrument']}; "
            f"Test={case_input['test']}; Observation={case_input['observation']}; "
            f"Analyst Name={case_input['analyst_name']}"
        ),
        "modification_status": "Initial version created; no modifications recorded",
    }
    rca_candidates = score_root_causes(
        problem=case_input["problem"],
        instrument=case_input["instrument"],
        observation=case_input["observation"],
        library_path=config.rca_library_path,
    )

    report_json = generate_investigation_report(
        api_key=resolve_api_key(config),
        model=config.ai_model,
        case_input=case_input,
        rca_candidates=rca_candidates,
        record_metadata=metadata,
        signature_block=signature,
        audit_trail=audit,
    )
    report_text = render_report_text(report_json)
    pdf_bytes = build_pdf(report_json)

    payload = {
        "record_uid": record_uid,
        "problem": case_input["problem"],
        "instrument": case_input["instrument"],
        "test": case_input["test"],
        "observation": case_input["observation"],
        "analyst_name": case_input["analyst_name"],
        "prepared_by": report_json["electronic_signature"]["prepared_by"],
        "reviewed_by": report_json["electronic_signature"]["reviewed_by"],
        "approved_by": report_json["electronic_signature"]["approved_by"],
        "signature_status": report_json["electronic_signature"]["signature_status"],
        "investigation_status": report_json["record_metadata"]["investigation_status"],
        "risk_level": _derive_risk_level(report_json["initial_assessment"]),
        "confidence_level": report_json["confidence_level"],
        "report_json": report_json,
        "report_text": report_text,
        "timestamp": report_json["record_metadata"]["timestamp"],
        "version": version,
    }
    return report_json, payload, pdf_bytes


def render_generated_report(report: dict[str, Any]) -> None:
    st.subheader("Generated Investigation Report")
    st.json(report, expanded=True)


def render_record_table(config) -> None:
    records = list_records(config.database_path)
    if not records:
        st.info("No saved records are available yet.")
        return

    st.subheader("Saved Records")
    for row in records:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(
                f"**{row['record_uid']}** | Version {row['version']} | "
                f"{row['instrument']} | {row['timestamp']} | Status: {row['investigation_status']}"
            )
            st.caption(f"Problem: {row['problem']}")
        with col2:
            if st.button("Open", key=f"open_{row['id']}"):
                log_audit_event(
                    config.database_path,
                    user=row["analyst_name"],
                    action="VIEW",
                    details="Record viewed from Streamlit record browser",
                    record_id=row["id"],
                    record_uid=row["record_uid"],
                )
                record = get_record_by_id(config.database_path, row["id"])
                if record:
                    st.session_state["view_record"] = record["id"]

    selected_record_id = st.session_state.get("view_record")
    if selected_record_id:
        record = get_record_by_id(config.database_path, selected_record_id)
        if record:
            st.markdown("---")
            st.markdown(f"### Record Detail: {record['record_uid']} / v{record['version']}")
            st.text_area(
                "Report Text",
                value=record["report_text"],
                height=360,
                disabled=True,
                key=f"report_text_{record['id']}",
            )
            audit_rows = get_audit_trail(config.database_path, record["record_uid"])
            st.markdown("#### Audit Trail")
            st.dataframe(
                [
                    {
                        "Timestamp": item["timestamp"],
                        "User": item["user"],
                        "Action": item["action"],
                        "Details": item["details"],
                    }
                    for item in audit_rows
                ],
                use_container_width=True,
            )


def main() -> None:
    config = get_config()
    initialize_database(config.database_path)
    initialize_state()

    st.set_page_config(page_title="PharmaRCA AI", page_icon=":microscope:", layout="wide")
    st.title("PharmaRCA AI")
    st.caption(
        "AI-powered deviation investigation software with Part 11-style auditability, "
        "RCA scoring, CAPA generation, and PDF export."
    )

    with st.sidebar:
        st.markdown("### System Status")
        st.write(f"Database: `{config.database_path.name}`")
        st.write(f"Gemini Model: `{config.ai_model}`")
        st.write("Audit Trail: Enabled")
        st.write("Version Control: Insert-only record versions")
        st.markdown("### Gemini Access")
        st.text_input(
            "Gemini API Key",
            key="gemini_api_key",
            type="password",
            help="Used only for the current Streamlit session if GEMINI_API_KEY is not set in the environment.",
        )
        if resolve_api_key(config):
            st.success("Gemini API key available")
        else:
            st.warning("Add a Gemini API key here or set GEMINI_API_KEY before generating a report.")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("Deviation Input")
        with st.form("investigation_form"):
            analyst_name = st.text_input("Analyst Name")
            problem = st.text_area("Problem")
            instrument = st.selectbox("Instrument", INSTRUMENT_OPTIONS)
            test = st.text_input("Test")
            observation = st.text_area("Observation")
            generate_clicked = st.form_submit_button("Generate Investigation", use_container_width=True)

        if generate_clicked:
            if not resolve_api_key(config):
                st.error("Gemini API key is missing. Enter it in the sidebar or set GEMINI_API_KEY before generating an investigation.")
            elif not all([analyst_name.strip(), problem.strip(), instrument.strip(), test.strip(), observation.strip()]):
                st.error("All input fields are required before generating an investigation.")
            else:
                case_input = build_case_input(problem, instrument, test, observation, analyst_name)
                try:
                    report, payload, pdf_bytes = generate_report_workflow(config, case_input)
                except Exception as exc:
                    st.error(f"Unable to generate investigation: {exc}")
                else:
                    st.session_state["generated_report"] = report
                    st.session_state["generated_payload"] = payload
                    st.session_state["generated_pdf"] = pdf_bytes
                    st.session_state["saved_record_id"] = None
                    st.success("Investigation report generated successfully.")

        if st.session_state["generated_report"]:
            render_generated_report(st.session_state["generated_report"])

    with col2:
        st.subheader("Record Actions")
        payload = st.session_state.get("generated_payload")
        generated_pdf = st.session_state.get("generated_pdf")

        save_disabled = payload is None
        if st.button("Save Record", use_container_width=True, disabled=save_disabled):
            record_id = save_record(config.database_path, payload)
            log_audit_event(
                config.database_path,
                user=payload["analyst_name"],
                action="CREATE",
                details="Initial record version saved from Streamlit UI",
                record_id=record_id,
                record_uid=payload["record_uid"],
            )
            st.session_state["saved_record_id"] = record_id
            st.success(f"Record saved successfully with database ID {record_id}.")

        st.download_button(
            "Download PDF",
            data=generated_pdf or b"",
            file_name=f"{payload['record_uid'] if payload else 'pharmarca_ai_report'}.pdf",
            mime="application/pdf",
            use_container_width=True,
            disabled=generated_pdf is None,
        )

        if payload and st.session_state.get("saved_record_id"):
            st.code(json.dumps(payload["report_json"], indent=2), language="json")

        st.markdown("---")
        render_record_table(config)

    st.markdown("---")
    st.caption(CREDITS_TEXT)
