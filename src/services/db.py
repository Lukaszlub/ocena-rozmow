from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from src.core.models import EvaluationResult


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS call_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT,
            last_name TEXT,
            file_name TEXT,
            file_hash TEXT UNIQUE,
            call_duration INTEGER,
            evaluation_timestamp TEXT,
            transcript TEXT,
            score_total REAL,
            stars INTEGER,
            profanity_flag INTEGER,
            profanity_phrases TEXT,
            profanity_excerpt TEXT,
            score_breakdown TEXT,
            evidence_breakdown TEXT,
            evidence_summary TEXT,
            transcription_confidence REAL
        );
        """
    )
    _ensure_column(conn, "call_evaluations", "profanity_excerpt", "TEXT")
    _ensure_column(conn, "call_evaluations", "evidence_breakdown", "TEXT")
    _ensure_column(conn, "call_evaluations", "evidence_summary", "TEXT")
    conn.commit()
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def has_file_hash(conn: sqlite3.Connection, file_hash: str) -> bool:
    cur = conn.execute("SELECT 1 FROM call_evaluations WHERE file_hash = ? LIMIT 1", (file_hash,))
    return cur.fetchone() is not None


def insert_evaluation(conn: sqlite3.Connection, r: EvaluationResult) -> None:
    conn.execute(
        """
        INSERT INTO call_evaluations (
            first_name, last_name, file_name, file_hash, call_duration,
            evaluation_timestamp, transcript, score_total, stars,
            profanity_flag, profanity_phrases, profanity_excerpt, score_breakdown,
            evidence_breakdown, evidence_summary, transcription_confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            r.first_name,
            r.last_name,
            r.file_name,
            r.file_hash,
            r.call_duration_sec,
            r.evaluation_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            r.transcript,
            r.score_total,
            r.stars,
            1 if r.profanity_flag else 0,
            ", ".join(r.profanity_phrases),
            r.profanity_excerpt,
            json.dumps(r.score_breakdown, ensure_ascii=False),
            json.dumps(r.evidence_breakdown, ensure_ascii=False),
            r.evidence_summary,
            r.transcription_confidence,
        ),
    )
    conn.commit()


def list_evaluations(
    conn: sqlite3.Connection, limit: int = 200, offset: int = 0, name_filter: str | None = None
) -> List[EvaluationResult]:
    where = ""
    params = []
    if name_filter:
        where = "WHERE first_name LIKE ? OR last_name LIKE ?"
        nf = f"%{name_filter}%"
        params.extend([nf, nf])
    cur = conn.execute(
        f"""
        SELECT
            first_name, last_name, file_name, file_hash, call_duration,
            evaluation_timestamp, transcript, score_total, stars,
            profanity_flag, profanity_phrases, profanity_excerpt, score_breakdown,
            evidence_breakdown, evidence_summary, transcription_confidence
        FROM call_evaluations
        {where}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    )
    rows = []
    for r in cur.fetchall():
        rows.append(
            EvaluationResult(
                first_name=r[0],
                last_name=r[1],
                file_name=r[2],
                file_hash=r[3],
                call_duration_sec=int(r[4] or 0),
                evaluation_timestamp=datetime.strptime(r[5], "%Y-%m-%d %H:%M:%S"),
                transcript=r[6] or "",
                score_total=float(r[7] or 0.0),
                stars=int(r[8] or 0),
                profanity_flag=bool(r[9]),
                profanity_phrases=(r[10].split(", ") if r[10] else []),
                profanity_excerpt=r[11] or "",
                score_breakdown=json.loads(r[12] or "{}"),
                evidence_breakdown=json.loads(r[13] or "{}"),
                evidence_summary=r[14] or "",
                transcription_confidence=float(r[15] or 0.0),
            )
        )
    return rows


def count_evaluations(conn: sqlite3.Connection, name_filter: str | None = None) -> int:
    where = ""
    params = []
    if name_filter:
        where = "WHERE first_name LIKE ? OR last_name LIKE ?"
        nf = f"%{name_filter}%"
        params.extend([nf, nf])
    cur = conn.execute(f"SELECT COUNT(1) FROM call_evaluations {where}", params)
    return int(cur.fetchone()[0])
