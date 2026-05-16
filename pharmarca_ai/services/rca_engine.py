from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_rca_library(library_path: Path) -> dict[str, list[dict[str, Any]]]:
    with library_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def build_case_keys(problem: str, instrument: str, observation: str) -> list[str]:
    normalized_problem = problem.lower()
    normalized_observation = observation.lower()
    normalized_instrument = instrument.strip().upper()

    keys: list[str] = []
    if normalized_instrument == "HPLC" and ("air bubble" in normalized_problem or "baseline" in normalized_observation):
        keys.append("HPLC_AIR_BUBBLE")
    if normalized_instrument == "HPLC" and "baseline" in normalized_observation:
        keys.append("HPLC_BASELINE_FLUCTUATION")
    if normalized_instrument == "GC":
        keys.append("GC_GENERAL")
    if normalized_instrument == "DISSOLUTION":
        keys.append("DISSOLUTION_GENERAL")
    keys.append(f"{normalized_instrument}_GENERAL")
    keys.append("DEFAULT_GENERAL")
    return keys


def score_root_causes(
    *,
    problem: str,
    instrument: str,
    observation: str,
    library_path: Path,
) -> list[dict[str, Any]]:
    library = load_rca_library(library_path)
    keys = build_case_keys(problem, instrument, observation)

    merged: dict[str, dict[str, Any]] = {}
    for key in keys:
        for item in library.get(key, []):
            cause = item["cause"]
            existing = merged.get(cause)
            if existing:
                existing["weight"] = max(existing["weight"], item["weight"])
                continue
            merged[cause] = {
                "cause": cause,
                "category": item["category"],
                "weight": float(item["weight"]),
                "source_key": key,
            }

    ranked = sorted(merged.values(), key=lambda item: item["weight"], reverse=True)
    return ranked[:5]
