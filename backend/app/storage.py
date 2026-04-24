import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "meeting_history.db"

REQUIRED_COLUMNS = {
    "speaker_segments": "TEXT NOT NULL DEFAULT '[]'",
    "speaker_aware_transcript": "TEXT NOT NULL DEFAULT ''",
    "diarization_segments": "TEXT NOT NULL DEFAULT '[]'",
    "diarization_status": "TEXT NOT NULL DEFAULT 'not_available'",
    "diarization_backend": "TEXT NOT NULL DEFAULT 'none'",
    "diarization_error": "TEXT NOT NULL DEFAULT ''",
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                template TEXT NOT NULL,
                transcript TEXT NOT NULL,
                cleaned_transcript TEXT NOT NULL,
                summary TEXT NOT NULL,
                action_items TEXT NOT NULL,
                insights TEXT NOT NULL,
                follow_up TEXT NOT NULL,
                speaker_segments TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(meetings)").fetchall()
        }

        for column_name, column_definition in REQUIRED_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE meetings ADD COLUMN {column_name} {column_definition}"
                )

        connection.commit()


def serialize_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def deserialize_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def normalize_row(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "template": row["template"],
        "transcript": row["transcript"],
        "cleaned_transcript": row["cleaned_transcript"],
        "speaker_aware_transcript": row["speaker_aware_transcript"],
        "summary": row["summary"],
        "action_items": deserialize_json(row["action_items"], []),
        "insights": deserialize_json(row["insights"], {}),
        "follow_up": row["follow_up"],
        "speaker_segments": deserialize_json(row["speaker_segments"], []),
        "diarization_segments": deserialize_json(row["diarization_segments"], []),
        "diarization_status": row["diarization_status"],
        "diarization_backend": row["diarization_backend"],
        "diarization_error": row["diarization_error"],
        "created_at": row["created_at"],
    }


def save_meeting(payload: Dict[str, Any]) -> Dict[str, Any]:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO meetings (
                filename,
                template,
                transcript,
                cleaned_transcript,
                speaker_aware_transcript,
                summary,
                action_items,
                insights,
                follow_up,
                speaker_segments,
                diarization_segments,
                diarization_status,
                diarization_backend,
                diarization_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["filename"],
                payload["template"],
                payload["transcript"],
                payload["cleaned_transcript"],
                payload.get("speaker_aware_transcript", ""),
                payload["summary"],
                serialize_json(payload.get("action_items", [])),
                serialize_json(payload.get("insights", {})),
                payload["follow_up"],
                serialize_json(payload.get("speaker_segments", [])),
                serialize_json(payload.get("diarization_segments", [])),
                payload.get("diarization_status", "not_available"),
                payload.get("diarization_backend", "none"),
                payload.get("diarization_error", ""),
            ),
        )
        meeting_id = cursor.lastrowid
        connection.commit()
    return get_meeting(meeting_id)


def list_meetings(limit: int = 10) -> List[Dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM meetings
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [normalize_row(row) for row in rows]


def get_meeting(meeting_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM meetings WHERE id = ?",
            (meeting_id,),
        ).fetchone()
    if row is None:
        return None
    return normalize_row(row)
