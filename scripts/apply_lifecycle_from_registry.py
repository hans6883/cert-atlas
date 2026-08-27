#!/usr/bin/env python3
"""Mirror reviewed lifecycle facts from the registry into the published Cert Atlas dataset.

Source of truth: web-scraper-mcp/data/blueprint_registry.db table `exam_lifecycle`
(status, effective_date, replacement code/relationship/url, summary, evidence_url).
Enrichment overlays may carry richer lifecycle prose; the registry decides the FACTS
(status, date, replacement, relationship). This step runs after export.py and
apply_enrichments.py and before build_site.py / the MCP build, and is idempotent.

Usage:
    python scripts/apply_lifecycle_from_registry.py            # validate + report drift
    python scripts/apply_lifecycle_from_registry.py --write    # stamp index.json + exam files
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = os.environ.get(
    "BLUEPRINT_DB_PATH",
    str(Path.home() / "source" / "repos" / "web-scraper-mcp" / "data" / "blueprint_registry.db"),
)
FACT_KEYS = ("status", "retired_on", "retires_on", "replacement")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def registry_rows(db_path: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM exam_lifecycle ORDER BY exam_id")]
    finally:
        conn.close()


def lifecycle_block(row: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    """Registry facts win; overlay prose (summary, migration_actions, source_ids) is kept when present."""
    block: dict[str, Any] = dict(existing or {})
    for key in FACT_KEYS:
        block.pop(key, None)
    block["status"] = row["status"]
    if row["status"] == "retired":
        block["retired_on"] = row.get("effective_date")
    elif row["status"] == "scheduled_retirement":
        block["retires_on"] = row.get("effective_date")
    if row.get("replacement_exam_code"):
        block["replacement"] = {
            "exam_code": row["replacement_exam_code"],
            "relationship": row.get("replacement_relationship") or "direct_replacement",
            "url": row.get("replacement_url"),
        }
    if not block.get("summary") and row.get("summary"):
        block["summary"] = row["summary"]
    block["evidence_url"] = row.get("evidence_url")
    block["verified_at"] = row.get("verified_at")
    return block


def index_fields(row: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {"lifecycle_status": row["status"]}
    if row["status"] == "retired":
        fields["retired_on"] = row.get("effective_date")
    elif row["status"] == "scheduled_retirement":
        fields["retires_on"] = row.get("effective_date")
    if row.get("replacement_exam_code"):
        fields["replacement_exam_code"] = row["replacement_exam_code"]
        fields["replacement_relationship"] = row.get("replacement_relationship") or "direct_replacement"
        fields["replacement_url"] = row.get("replacement_url")
    return fields


def apply(data_root: Path, db_path: str, write: bool) -> dict[str, Any]:
    index_path = data_root / "index.json"
    index = _read_json(index_path)
    entries = {str(e.get("exam_id")): e for e in index.get("exams", []) if isinstance(e, dict)}
    rows = registry_rows(db_path)
    report: dict[str, Any] = {"registry_rows": len(rows), "stamped": 0, "unchanged": 0,
                              "missing_from_atlas": [], "drift": [], "atlas_only": []}
    index_changed = False

    for row in rows:
        entry = entries.get(row["exam_id"])
        if entry is None:
            report["missing_from_atlas"].append(row["exam_id"])
            continue
        vendor_slug = entry.get("vendor_slug") or row["exam_id"].split("-")[0]
        exam_path = data_root / vendor_slug / f"{row['exam_id']}.json"
        if not exam_path.exists():
            report["missing_from_atlas"].append(row["exam_id"])
            continue

        exam = _read_json(exam_path)
        wanted_entry = index_fields(row)
        current_entry = {k: entry.get(k) for k in wanted_entry}
        wanted_block = lifecycle_block(row, exam.get("lifecycle"))
        changed = current_entry != wanted_entry or exam.get("lifecycle") != wanted_block
        if current_entry.get("lifecycle_status") != wanted_entry["lifecycle_status"] and current_entry.get("lifecycle_status"):
            report["drift"].append(f"{row['exam_id']}: atlas={current_entry.get('lifecycle_status')} registry={row['status']}")
        if not changed:
            report["unchanged"] += 1
            continue
        report["stamped"] += 1
        if not write:
            continue
        for key in ("lifecycle_status", "retired_on", "retires_on", "replacement_exam_code",
                    "replacement_relationship", "replacement_url"):
            entry.pop(key, None)
        entry.update(wanted_entry)
        if row["status"] == "retired":
            entry["practice_url"] = None
        exam["lifecycle"] = wanted_block
        _write_json(exam_path, exam)
        index_changed = True

    registry_ids = {r["exam_id"] for r in rows}
    report["atlas_only"] = sorted(k for k, e in entries.items() if e.get("lifecycle_status") and k not in registry_ids)
    if write and index_changed:
        _write_json(index_path, index)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-root", type=Path, default=ROOT / "data")
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    report = apply(args.data_root, args.db, args.write)
    print(json.dumps(report, indent=2))
    # atlas_only means a lifecycle claim with no registry backing: fail so it gets reviewed.
    return 1 if report["atlas_only"] else 0


if __name__ == "__main__":
    sys.exit(main())
