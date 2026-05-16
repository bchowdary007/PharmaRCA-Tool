from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppConfig:
    app_name: str = "PharmaRCA AI"
    database_path: Path = Path("data/pharmarca_ai.db")
    rca_library_path: Path = Path("data/rca_library.json")
    ai_model: str = "gemini-2.5-flash"
    timezone: str = "Asia/Calcutta"

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "").strip()


def get_config() -> AppConfig:
    base_dir = Path(__file__).resolve().parents[1]
    load_dotenv(base_dir / ".env", override=False)
    return AppConfig(
        database_path=base_dir / "data" / "pharmarca_ai.db",
        rca_library_path=base_dir / "data" / "rca_library.json",
        ai_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )
