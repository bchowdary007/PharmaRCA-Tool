from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .utils import current_timestamp


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_uid TEXT NOT NULL,
                problem TEXT NOT NULL,
                instrument TEXT NOT NULL,
                test TEXT NOT NULL,
                observation TEXT NOT NULL,
                analyst_name TEXT NOT NULL,
                prepared_by TEXT NOT NULL,
                reviewed_by TEXT,
                approved_by TEXT,
                signature_status TEXT NOT NULL,
                investigation_status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confidence_level TEXT NOT NULL,
                report_json TEXT NOT NULL,
                report_text TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER,
                record_uid TEXT,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(record_id) REFERENCES records(id)
            );

            CREATE INDEX IF NOT EXISTS idx_records_uid_version
            ON records(record_uid, version);

            CREATE INDEX IF NOT EXISTS idx_audit_record_uid
            ON audit_trail(record_uid, timestamp);

            CREATE TRIGGER IF NOT EXISTS prevent_audit_trail_update
            BEFORE UPDATE ON audit_trail
            BEGIN
                SELECT RAISE(ABORT, 'audit_trail rows are append-only');
            END;

            CREATE TRIGGER IF NOT EXISTS prevent_audit_trail_delete
            BEFORE DELETE ON audit_trail
            BEGIN
                SELECT RAISE(ABORT, 'audit_trail rows are append-only');
            END;
            """
        )


def log_audit_event(
    db_path: Path,
    *,
    user: str,
    action: str,
    details: str,
    record_id: int | None = None,
    record_uid: str | None = None,
) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO audit_trail (record_id, record_uid, user, action, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (record_id, record_uid, user, action, details, current_timestamp()),
        )


def get_next_version(db_path: Path, record_uid: str) -> int:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS max_version FROM records WHERE record_uid = ?",
            (record_uid,),
        ).fetchone()
    return int(row["max_version"]) + 1


def save_record(db_path: Path, payload: dict[str, Any]) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO records (
                record_uid, problem, instrument, test, observation, analyst_name,
                prepared_by, reviewed_by, approved_by, signature_status,
                investigation_status, risk_level, confidence_level, report_json,
                report_text, timestamp, version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["record_uid"],
                payload["problem"],
                payload["instrument"],
                payload["test"],
                payload["observation"],
                payload["analyst_name"],
                payload["prepared_by"],
                payload.get("reviewed_by"),
                payload.get("approved_by"),
                payload["signature_status"],
                payload["investigation_status"],
                payload["risk_level"],
                payload["confidence_level"],
                json.dumps(payload["report_json"], indent=2),
                payload["report_text"],
                payload["timestamp"],
                payload["version"],
            ),
        )
        return int(cursor.lastrowid)


def list_records(db_path: Path) -> list[sqlite3.Row]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM records
            ORDER BY timestamp DESC, version DESC
            """
        ).fetchall()
    return list(rows)


def get_record_by_id(db_path: Path, record_id: int) -> sqlite3.Row | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    return row


def get_audit_trail(db_path: Path, record_uid: str) -> list[sqlite3.Row]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM audit_trail
            WHERE record_uid = ?
            ORDER BY timestamp DESC, id DESC
            """,
            (record_uid,),
        ).fetchall()
    return list(rows)
