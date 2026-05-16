from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo


APP_TZ = ZoneInfo("Asia/Calcutta")


def current_timestamp() -> str:
    return datetime.now(APP_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def generate_record_uid(prefix: str = "INV") -> str:
    stamp = datetime.now(APP_TZ).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{prefix}-{stamp}-{suffix}"
