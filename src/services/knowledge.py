from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List, Dict


def _chunk_text(text: str, chunk_chars: int, overlap_chars: int) -> List[str]:
    chunks = []
    i = 0
    while i < len(text):
        end = min(len(text), i + chunk_chars)
        chunks.append(text[i:end].strip())
        i = max(end - overlap_chars, end)
    return [c for c in chunks if c]


def _extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages = []
    for p in reader.pages:
        pages.append(p.extract_text() or "")
    return "\n".join(pages)


def ensure_knowledge_index(conn: sqlite3.Connection, cfg_knowledge: Dict[str, str]) -> None:
    if not cfg_knowledge or not cfg_knowledge.get("enabled", True):
        return
    folder = Path(cfg_knowledge.get("folder", "data/knowledge"))
    folder.mkdir(parents=True, exist_ok=True)

    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
        USING fts5(source, chunk, content);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_meta (
            source TEXT PRIMARY KEY,
            mtime REAL
        );
        """
    )
    conn.commit()

    for pdf in folder.glob("*.pdf"):
        mtime = pdf.stat().st_mtime
        row = conn.execute(
            "SELECT mtime FROM knowledge_meta WHERE source = ?", (pdf.name,)
        ).fetchone()
        if row and float(row[0]) == mtime:
            continue

        text = _extract_pdf_text(pdf)
        chunks = _chunk_text(
            text,
            int(cfg_knowledge.get("chunk_chars", 1000)),
            int(cfg_knowledge.get("overlap_chars", 150)),
        )
        conn.execute("DELETE FROM knowledge_fts WHERE source = ?", (pdf.name,))
        for ch in chunks:
            conn.execute(
                "INSERT INTO knowledge_fts (source, chunk, content) VALUES (?, ?, ?)",
                (pdf.name, ch, ch),
            )
        conn.execute(
            "INSERT OR REPLACE INTO knowledge_meta (source, mtime) VALUES (?, ?)",
            (pdf.name, mtime),
        )
        conn.commit()


def _build_query(text: str) -> str:
    tokens = re.findall(r"[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{3,}", text.lower())
    stop = {
        "oraz", "jest", "oraz", "sie", "się", "nie", "tak", "ale", "czy",
        "dla", "ten", "taka", "taki", "jak", "jako", "na", "do", "od",
        "o", "w", "z", "że", "to", "co", "po", "za", "pod", "nad",
    }
    uniq = []
    for t in tokens:
        if t in stop:
            continue
        if t not in uniq:
            uniq.append(t)
        if len(uniq) >= 20:
            break
    return " OR ".join(uniq)


def retrieve_knowledge(
    conn: sqlite3.Connection, cfg_knowledge: Dict[str, str], transcript: str
) -> List[str]:
    if not cfg_knowledge or not cfg_knowledge.get("enabled", True):
        return []
    query = _build_query(transcript)
    if not query:
        return []
    top_k = int(cfg_knowledge.get("top_k", 3))
    cur = conn.execute(
        """
        SELECT source, chunk
        FROM knowledge_fts
        WHERE knowledge_fts MATCH ?
        LIMIT ?
        """,
        (query, top_k),
    )
    return [f"[{r[0]}] {r[1]}" for r in cur.fetchall()]
