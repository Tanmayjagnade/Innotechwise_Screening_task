import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import DeclarationRequest, DeclarationResponse

DB_PATH = "greenpack.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS declarations (
                record_id   TEXT PRIMARY KEY,
                producer_id TEXT NOT NULL,
                month       TEXT NOT NULL,
                quantities  TEXT NOT NULL,
                timestamp   TEXT NOT NULL,
                UNIQUE(producer_id, month)
            )
        """)
        conn.commit()


def store_declaration(payload: DeclarationRequest) -> DeclarationResponse:
    record_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO declarations VALUES (?, ?, ?, ?, ?)",
            (
                record_id,
                payload.producer_id,
                payload.month,
                json.dumps(payload.declared_quantities_kg),
                timestamp,
            ),
        )
        conn.commit()

    return DeclarationResponse(
        record_id=record_id,
        producer_id=payload.producer_id,
        month=payload.month,
        declared_quantities_kg=payload.declared_quantities_kg,
        timestamp=timestamp,
    )


def get_declaration(producer_id: str, month: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT record_id, producer_id, month, quantities, timestamp "
            "FROM declarations WHERE producer_id = ? AND month = ?",
            (producer_id, month),
        ).fetchone()

    if not row:
        return None

    return {
        "record_id": row[0],
        "producer_id": row[1],
        "month": row[2],
        "declared_quantities_kg": json.loads(row[3]),
        "timestamp": row[4],
    }
