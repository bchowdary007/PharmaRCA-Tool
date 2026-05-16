from __future__ import annotations

import json
from typing import Any

from google import genai

from .reporting import safe_json_loads


CATEGORY_EVALUATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "possible_causes": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "reasoning": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "status": {"type": "string"}
    },
    "required": ["possible_causes", "reasoning", "status"]
}


FISHBONE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "machine": CATEGORY_EVALUATION_SCHEMA,
        "method": CATEGORY_EVALUATION_SCHEMA,
        "material": CATEGORY_EVALUATION_SCHEMA,
        "measurement": CATEGORY_EVALUATION_SCHEMA,
        "mother_nature": CATEGORY_EVALUATION_SCHEMA,
        "man": CATEGORY_EVALUATION_SCHEMA
    },
    "required": ["machine", "method", "material", "measurement", "mother_nature", "man"]
}


REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "record_metadata": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "record_id": {"type": "string"},
                "timestamp": {"type": "string"},
                "version": {"type": "string"},
                "investigation_status": {"type": "string"},
                "record_type": {"type": "string"}
            },
            "required": ["record_id", "timestamp", "version", "investigation_status", "record_type"]
        },
        "electronic_signature": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "prepared_by": {"type": "string"},
                "reviewed_by": {"type": "string"},
                "approved_by": {"type": "string"},
                "signature_status": {"type": "string"}
            },
            "required": ["prepared_by", "reviewed_by", "approved_by", "signature_status"]
        },
        "audit_trail": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "creation_event": {"type": "string"},
                "input_traceability": {"type": "string"},
                "modification_status": {"type": "string"}
            },
            "required": ["creation_event", "input_traceability", "modification_status"]
        },
        "deviation_description": {"type": "array", "items": {"type": "string"}, "minItems": 2},
        "initial_assessment": {"type": "array", "items": {"type": "string"}, "minItems": 3},
        "investigation_plan": {"type": "array", "items": {"type": "string"}, "minItems": 5},
        "fishbone_analysis": FISHBONE_SCHEMA,
        "investigation_reasoning": {"type": "array", "items": {"type": "string"}, "minItems": 5},
        "possible_root_causes": {"type": "array", "items": {"type": "string"}, "minItems": 5},
        "root_cause_analysis": {"type": "array", "items": {"type": "string"}, "minItems": 3},
        "most_probable_root_cause": {"type": "string"},
        "confidence_level": {"type": "string"},
        "root_cause_classification": {"type": "string"},
        "impact_assessment": {"type": "array", "items": {"type": "string"}, "minItems": 2},
        "capa": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "immediate_correction": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "corrective_action": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "preventive_action": {"type": "array", "items": {"type": "string"}, "minItems": 2}
            },
            "required": ["immediate_correction", "corrective_action", "preventive_action"]
        },
        "data_gaps": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "conclusion": {"type": "string"}
    },
    "required": [
        "record_metadata",
        "electronic_signature",
        "audit_trail",
        "deviation_description",
        "initial_assessment",
        "investigation_plan",
        "fishbone_analysis",
        "investigation_reasoning",
        "possible_root_causes",
        "root_cause_analysis",
        "most_probable_root_cause",
        "confidence_level",
        "root_cause_classification",
        "impact_assessment",
        "capa",
        "data_gaps",
        "conclusion"
    ]
}


SYSTEM_PROMPT = """
You are PharmaRCA AI, an audit-ready pharmaceutical deviation investigation assistant for regulated environments.

Mandatory compliance:
- 21 CFR Part 11: electronic records, timestamps, traceability, non-overwrite, reviewability
- 21 CFR Part 211: deviation handling, impact assessment, scientifically justified root cause, CAPA
- 21 CFR Part 58: scientific integrity, hypothesis-driven reasoning, no unsupported assumptions
- ALCOA+: attributable, legible, contemporaneous, original, accurate, complete, consistent, enduring, available

Critical investigation rule:
- Human error must NOT be concluded unless Machine, Method, Material, Measurement, and Mother Nature are systematically evaluated first and not confirmed as more likely causes.
- Human error must be treated as the final category and only retained when evidence supports it or when a documented evidence gap prevents confirmation of a system cause.
- Avoid generic statements such as analyst error, operator mistake, or procedural lapse without mechanism-level explanation.

Investigation method requirements:
- Perform Fishbone (Ishikawa) analysis in this order: Machine, Method, Material, Measurement, Mother Nature, Man
- For each category, provide possible causes, scientific reasoning, and a status stating whether the category is ruled out, not ruled out, or requires further evidence
- Provide a separate investigation_reasoning section explaining how each category was evaluated and why it was ruled out or retained
- Provide at least 5 possible root causes
- Prefer system, process, material, method, or instrument causes before human error
- Root cause classification must align with the identified dominant cause category

Output rules:
- Return only JSON matching the provided schema
- Do not include markdown
- Do not invent evidence not present in the input
- Use the RCA candidates provided as weighted hypotheses, not as guaranteed facts
- Root cause must remain provisional if data gaps prevent confirmation
- Risk levels must be one of Critical, Major, Minor
- Confidence level must be one of High, Medium, Low
- Signature status must reflect draft state if reviewers/approvers are pending
""".strip()


def generate_investigation_report(
    *,
    api_key: str,
    model: str,
    case_input: dict[str, Any],
    rca_candidates: list[dict[str, Any]],
    record_metadata: dict[str, Any],
    signature_block: dict[str, Any],
    audit_trail: dict[str, Any],
) -> dict[str, Any]:
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=api_key)
    input_payload = {
        "case_input": case_input,
        "weighted_rca_candidates": rca_candidates,
        "record_metadata": record_metadata,
        "electronic_signature": signature_block,
        "audit_trail": audit_trail
    }
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        "Generate a complete pharmaceutical investigation record using this input. "
        "Include Fishbone 6M analysis in the required priority order and do not conclude human error unless prior categories have been systematically evaluated and justified. "
        "Use only evidence-based reasoning and keep conclusions provisional where data gaps remain.\n\n"
        f"{json.dumps(input_payload, indent=2)}"
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": REPORT_SCHEMA,
            "temperature": 0.2,
        },
    )

    return safe_json_loads(response.text)
