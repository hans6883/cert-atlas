#!/usr/bin/env python3
"""Apply reviewed Git enrichment overlays to the existing public dataset only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.enrichment import merge_overlay, validate_overlay
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from enrichment import merge_overlay, validate_overlay


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _reviewed_at(overlay: dict[str, Any]) -> str | None:
    reviewed_at = str(overlay.get("quality", {}).get("reviewed_at") or "")
    return reviewed_at or None


def apply_enrichments(
    data_root: Path | str,
    enrichment_root: Path | str,
    *,
    write: bool = False,
) -> dict[str, Any]:
    """Validate overlays and optionally merge them into already-published exam files.

    This intentionally cannot add new exam URLs. Registry expansion stays behind the
    separate export gate, where new exams require a reviewed enrichment first.
    """
    data_root = Path(data_root)
    enrichment_root = Path(enrichment_root)
    index_path = data_root / "index.json"
    index = _read_json(index_path)
    index_entries = {
        str(item.get("exam_id") or ""): item
        for item in index.get("exams", [])
        if isinstance(item, dict)
    }
    report: dict[str, Any] = {
        "checked": 0,
        "eligible": 0,
        "applied": 0,
        "rejected": 0,
        "missing_public_exam": 0,
        "errors": [],
    }
    index_changed = False

    for overlay_path in sorted(enrichment_root.glob("*/*.json")):
        report["checked"] += 1
        vendor_slug = overlay_path.parent.name
        try:
            overlay = _read_json(overlay_path)
        except (OSError, json.JSONDecodeError) as error:
            report["rejected"] += 1
            report["errors"].append(f"{overlay_path}: {error}")
            continue

        exam_id = str(overlay.get("exam_id") or overlay_path.stem)
        exam_path = data_root / vendor_slug / f"{exam_id}.json"
        if not exam_path.exists() or exam_id not in index_entries:
            report["missing_public_exam"] += 1
            report["errors"].append(
                f"{overlay_path}: no existing public exam; use the gated registry export"
            )
            continue

        try:
            exam = _read_json(exam_path)
        except (OSError, json.JSONDecodeError) as error:
            report["rejected"] += 1
            report["errors"].append(f"{exam_path}: {error}")
            continue

        validation = validate_overlay(exam, overlay)
        if not validation.publishable:
            report["rejected"] += 1
            report["errors"].append(
                f"{overlay_path}: " + "; ".join(validation.errors)
            )
            continue

        report["eligible"] += 1
        if not write:
            continue

        _write_json(exam_path, merge_overlay(exam, overlay))
        entry = index_entries[exam_id]
        entry.pop("content_status", None)
        entry["enriched"] = True
        entry["verified_at"] = _reviewed_at(overlay)
        lifecycle = overlay.get("lifecycle")
        if isinstance(lifecycle, dict) and lifecycle.get("status") == "retired":
            replacement = lifecycle.get("replacement") or {}
            entry["lifecycle_status"] = "retired"
            entry["retired_on"] = lifecycle.get("retired_on")
            entry["replacement_exam_code"] = replacement.get("exam_code")
            entry["replacement_relationship"] = replacement.get(
                "relationship", "direct_replacement"
            )
            entry["replacement_url"] = replacement.get("url")
            entry["practice_url"] = None
        report["applied"] += 1
        index_changed = True

    if write and index_changed:
        _write_json(index_path, index)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--enrichment-root", type=Path, default=Path("enrichment"))
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write valid reviewed overlays. Without this flag, only validate.",
    )
    args = parser.parse_args()
    report = apply_enrichments(
        args.data_root,
        args.enrichment_root,
        write=args.write,
    )
    print(json.dumps(report, indent=2))
    return 1 if report["rejected"] or report["missing_public_exam"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
