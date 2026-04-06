#!/usr/bin/env python3
"""
Export blueprint_registry.db into cert-atlas JSON files.

Produces:
  data/{vendor-slug}/{exam-id}.json   -- one file per exam (no sample questions)
  data/index.json                     -- master index for programmatic consumers
  data/vendors.json                   -- vendor directory with exam counts

Sample questions are stripped so the dataset stays purely structural.
"""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DB_PATH = os.environ.get(
    "BLUEPRINT_DB",
    str(Path.home() / "source" / "repos" / "web-scraper-mcp" / "data" / "blueprint_registry.db"),
)

QUIZFORGE_BASE = "https://quizforge.ai/tests"

# Fields to keep in per-exam JSON (order matters for readability)
KEEP_FIELDS = [
    "exam_id",
    "exam_name",
    "exam_code",
    "certifying_body",
    "certification_name",
    "version",
    "source_url",
    "passing_score",
    "passing_score_scale",
    "total_questions",
    "question_types",
    "exam_format",
    "duration_minutes",
    "exam_price_usd",
    "exam_price_notes",
    "voucher_url",
    "exam_registration_url",
    "testing_centers",
    "online_proctoring_available",
    "id_requirements",
    "exam_rules",
    "certification_validity_years",
    "renewal_required",
    "renewal_options",
    "continuing_education_units",
    "available_languages",
    "target_audience",
    "recommended_experience",
    "prerequisites",
    "retake_policy",
    "domains",
    "official_objectives_url",
    "official_study_resources",
]

# Fields intentionally excluded:
#   sample_questions  -- drives traffic to QuizForge instead
#   last_fetched      -- internal metadata
#   content_hash      -- internal metadata


def slugify(text: str) -> str:
    """Convert display name to filesystem-safe slug."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def make_practice_url(exam_id: str) -> str:
    """Generate a QuizForge practice URL from the exam ID."""
    return f"{QUIZFORGE_BASE}/{exam_id}"


def export():
    if not os.path.exists(DB_PATH):
        print(f"Database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Load vendors
    vendors_raw = conn.execute(
        "SELECT body_id, display_name, base_url, exam_list_url, notes FROM certifying_bodies"
    ).fetchall()
    vendor_map = {v["body_id"]: dict(v) for v in vendors_raw}

    # Load all exams
    exams_raw = conn.execute(
        "SELECT exam_id, certifying_body_id, blueprint_json, source_url FROM exams"
    ).fetchall()

    # Load aliases for lookup enrichment
    aliases_raw = conn.execute("SELECT alias, exam_id FROM aliases").fetchall()
    aliases_by_exam = {}
    for a in aliases_raw:
        aliases_by_exam.setdefault(a["exam_id"], []).append(a["alias"])

    conn.close()

    # Clear and recreate data dir
    if DATA_DIR.exists():
        import shutil
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(parents=True)

    index_entries = []
    vendor_exam_counts = {}
    total_with_domains = 0
    total_exams = 0

    for row in exams_raw:
        exam_id = row["exam_id"]
        body_id = row["certifying_body_id"]
        blueprint = json.loads(row["blueprint_json"])

        # Filter to kept fields
        exam_data = {}
        for field in KEEP_FIELDS:
            if field in blueprint:
                exam_data[field] = blueprint[field]

        # Add aliases
        if exam_id in aliases_by_exam:
            exam_data["aliases"] = sorted(aliases_by_exam[exam_id])

        # Add practice link
        exam_data["practice_url"] = make_practice_url(exam_id)

        # Determine vendor slug for directory
        vendor_info = vendor_map.get(body_id, {})
        vendor_slug = slugify(vendor_info.get("display_name", body_id))

        # Write per-exam file
        vendor_dir = DATA_DIR / vendor_slug
        vendor_dir.mkdir(parents=True, exist_ok=True)
        exam_path = vendor_dir / f"{exam_id}.json"
        with open(exam_path, "w", encoding="utf-8") as f:
            json.dump(exam_data, f, indent=2, ensure_ascii=False)

        # Track stats
        has_domains = bool(exam_data.get("domains"))
        domain_count = len(exam_data.get("domains", []))
        if has_domains:
            total_with_domains += 1
        total_exams += 1
        vendor_exam_counts[body_id] = vendor_exam_counts.get(body_id, 0) + 1

        # Index entry (lightweight)
        index_entries.append({
            "exam_id": exam_id,
            "exam_name": exam_data.get("exam_name", ""),
            "exam_code": exam_data.get("exam_code"),
            "certifying_body": exam_data.get("certifying_body", ""),
            "vendor_slug": vendor_slug,
            "domains": domain_count,
            "total_questions": exam_data.get("total_questions"),
            "duration_minutes": exam_data.get("duration_minutes"),
            "source_url": exam_data.get("source_url", ""),
            "practice_url": exam_data["practice_url"],
        })

    # Sort index by vendor then exam name
    index_entries.sort(key=lambda e: (e["certifying_body"], e["exam_name"]))

    # Write master index
    with open(DATA_DIR / "index.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated": "2026-04-05",
            "total_exams": total_exams,
            "total_vendors": len(vendor_exam_counts),
            "exams_with_domain_breakdowns": total_with_domains,
            "exams": index_entries,
        }, f, indent=2, ensure_ascii=False)

    # Write vendors file
    vendors_out = []
    for body_id, info in sorted(vendor_map.items(), key=lambda x: x[1]["display_name"]):
        count = vendor_exam_counts.get(body_id, 0)
        if count == 0:
            continue
        vendors_out.append({
            "vendor_id": body_id,
            "display_name": info["display_name"],
            "website": info["base_url"],
            "certification_page": info["exam_list_url"],
            "exam_count": count,
            "slug": slugify(info["display_name"]),
        })
    vendors_out.sort(key=lambda v: -v["exam_count"])

    with open(DATA_DIR / "vendors.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated": "2026-04-05",
            "total_vendors": len(vendors_out),
            "vendors": vendors_out,
        }, f, indent=2, ensure_ascii=False)

    print(f"Exported {total_exams} exams across {len(vendor_exam_counts)} vendors")
    print(f"  {total_with_domains} exams have domain breakdowns")
    print(f"  Output: {DATA_DIR}")


if __name__ == "__main__":
    export()
