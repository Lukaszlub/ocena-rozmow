from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from src.core.config import AppConfig, is_valid_filename, parse_name_from_filename
from src.core.models import EvaluationResult
from src.core.utils import file_sha256, safe_move
from src.services.db import has_file_hash, insert_evaluation
from src.services.evaluation_engine import evaluate_transcript
from src.services.export_excel import default_report_path, export_to_excel
from src.services.profanity import detect_profanity
from src.services.scoring import compute_score, score_to_stars
from src.services.stt_whisper import transcribe
from src.services.knowledge import ensure_knowledge_index, retrieve_knowledge


def process_file(path: Path, cfg: AppConfig, db_conn) -> EvaluationResult | None:
    if not is_valid_filename(path.name):
        safe_move(path, cfg.invalid_dir / path.name)
        return None

    file_hash = file_sha256(path)
    if has_file_hash(db_conn, file_hash):
        safe_move(path, cfg.processed_dir / path.name)
        return None

    first_name, last_name = parse_name_from_filename(path.name)
    transcription = transcribe(str(path), cfg.transcription)

    ensure_knowledge_index(db_conn, cfg.knowledge)
    knowledge_ctx = retrieve_knowledge(db_conn, cfg.knowledge, transcription.transcript)

    scores, evidence = evaluate_transcript(
        transcription.transcript, cfg.scoring, cfg.criteria, knowledge_ctx
    )
    total = compute_score(cfg.weights, scores)
    stars = score_to_stars(total, cfg.score_thresholds)

    profanity_flag, phrases, excerpt = detect_profanity(transcription.transcript, cfg.profanity_list)
    evidence_summary = ""
    for k in scores.keys():
        if evidence.get(k):
            evidence_summary = evidence.get(k, "")
            break
    if not evidence_summary:
        evidence_summary = transcription.transcript[:200].strip()

    result = EvaluationResult(
        first_name=first_name,
        last_name=last_name,
        file_name=path.name,
        evaluation_timestamp=datetime.now(),
        transcript=transcription.transcript,
        score_total=total,
        stars=stars,
        profanity_flag=profanity_flag,
        profanity_phrases=phrases,
        profanity_excerpt=excerpt,
        score_breakdown=scores,
        evidence_breakdown=evidence,
        evidence_summary=evidence_summary,
        knowledge_snippets=knowledge_ctx,
        transcription_confidence=transcription.confidence,
        call_duration_sec=transcription.duration_sec,
        file_hash=file_hash,
    )

    insert_evaluation(db_conn, result)
    safe_move(path, cfg.processed_dir / path.name)
    return result


def run_batch(cfg: AppConfig, db_conn) -> Path | None:
    rows: List[EvaluationResult] = []

    for path in cfg.input_dir.glob("*.mp3"):
        res = process_file(path, cfg, db_conn)
        if res:
            rows.append(res)

    if cfg.use_excel_export:
        report_path = default_report_path(cfg.reports_dir)
        export_to_excel(rows, report_path)
        return report_path

    return None
