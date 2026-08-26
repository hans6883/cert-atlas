#!/usr/bin/env python3
"""Export aggregate study signals without exporting private exam-bank content."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def _clean(value: Any, fallback: str) -> str:
    text = " ".join(str(value or "").split())
    return text if text else fallback


def _emphasis_level(ratio: float) -> str:
    if ratio >= 0.25:
        return "high"
    if ratio >= 0.1:
        return "medium"
    return "low"


def _topic_key(value: str) -> str:
    return " ".join(value.casefold().split())


def _difficulty_label(value: Any) -> str:
    normalized = _clean(value, "unspecified").casefold()
    return {
        "1": "easy",
        "2": "easy",
        "3": "medium",
        "4": "hard",
        "5": "hard",
    }.get(normalized, normalized)


def _question_type_label(value: Any) -> str:
    normalized = _clean(value, "unspecified").casefold().replace("-", "_").replace(" ", "_")
    return {
        "mcq": "Multiple-choice",
        "multiple_choice": "Multiple-choice",
        "sata": "Multiple-response",
        "multiple_response": "Multiple-response",
        "truefalse": "True/false",
        "true_false": "True/false",
        "scenario": "Scenario",
    }.get(normalized, normalized.replace("_", " ").capitalize())


def aggregate_bank_signals(bank_db: Path | str, exam_type_id: int) -> dict[str, Any]:
    """Aggregate only non-content metadata columns for one canonical exam type."""
    path = Path(bank_db).resolve()
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT topic_name, exam_category, question_type, difficulty
              FROM staged_questions
             WHERE exam_type_id = ?
             ORDER BY topic_name, exam_category, question_type, difficulty
            """,
            (exam_type_id,),
        ).fetchall()
    finally:
        connection.close()

    topic_counts: Counter[str] = Counter()
    topic_display: dict[str, str] = {}
    type_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    hard_by_topic: defaultdict[str, int] = defaultdict(int)
    digest = hashlib.sha256()

    for topic, category, question_type, difficulty in rows:
        safe_topic = _clean(topic, _clean(category, "Uncategorized"))
        topic_key = _topic_key(safe_topic)
        topic_display.setdefault(topic_key, safe_topic)
        safe_type = _question_type_label(question_type)
        safe_difficulty = _difficulty_label(difficulty)
        topic_counts[topic_key] += 1
        type_counts[safe_type] += 1
        difficulty_counts[safe_difficulty] += 1
        if safe_difficulty in {"hard", "advanced", "expert"}:
            hard_by_topic[topic_key] += 1
        digest.update(
            json.dumps(
                [topic_key, _clean(category, "").casefold(), safe_type, safe_difficulty],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )

    total = len(rows)
    topic_emphasis = [
        {
            "topic": topic_display[topic],
            "level": _emphasis_level(count / total) if total else "low",
            "share_percent": round(100 * count / total, 1) if total else 0,
        }
        for topic, count in topic_counts.most_common(12)
    ]

    style_observations = []
    for question_type, count in type_counts.most_common(4):
        share = round(100 * count / total) if total else 0
        style_observations.append(
            f"{question_type} items represent approximately {share}% of the available practice metadata."
        )

    challenge_areas = [
        f"Higher-difficulty practice coverage includes {topic_display[topic]}."
        for topic, _ in sorted(hard_by_topic.items(), key=lambda item: (-item[1], item[0]))[:8]
    ]

    return {
        "topic_emphasis": topic_emphasis,
        "challenge_areas": challenge_areas,
        "question_style_observations": style_observations,
        "difficulty_distribution": dict(sorted(difficulty_counts.items())),
        "input_record_count": total,
        "input_dataset_hash": f"sha256:{digest.hexdigest()}",
        "derivation": "aggregate_metadata_only",
        "official_weighting": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bank-db", required=True, type=Path)
    parser.add_argument("--exam-type-id", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    signals = aggregate_bank_signals(args.bank_db, args.exam_type_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(signals, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Wrote {signals['input_record_count']} aggregate bank records for "
        f"exam_type_id={args.exam_type_id}: {args.output}"
    )


if __name__ == "__main__":
    main()
