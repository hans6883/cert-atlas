#!/usr/bin/env python3
"""Audit every registry record for exam lifecycle evidence and catalog drift.

This tool is deliberately evidence-first. It produces candidates for editorial
review; it never changes blueprints or publishes pages automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sqlite3
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen


RETIREMENT_PATTERNS = (
    re.compile(r"\b[A-Z0-9]{1,10}(?:-[A-Z0-9]{2,10})+\b.{0,60}\b(?:was|is|has been)?\s*retired\b", re.I | re.S),
    re.compile(r"\b(?:exam(?:ination)?|credential|certification)\b.{0,90}\b(?:was|is|has been) retired\b", re.I | re.S),
    re.compile(r"\b(?:exam(?:ination)?|credential|certification)\b.{0,90}\bretired (?:on|as of|effective)\b", re.I | re.S),
    re.compile(r"\bretired (?:exam|examination|credential|certification)\b", re.I),
)
SCHEDULED_PATTERNS = (
    re.compile(r"\b(?:exam(?:ination)?|credential|certification)\b.{0,90}\bwill (?:be )?retire(?:d)?\b", re.I | re.S),
    re.compile(r"\bretirement date\b.{0,80}\b(?:exam|examination|credential|certification)\b", re.I | re.S),
)
REPLACEMENT_PATTERNS = (
    re.compile(
        r"\b(?:replaced by|replacement exam(?:ination)? is|successor exam(?:ination)? is)\s+(?:the\s+)?(?:exam(?:ination)?\s+)?([A-Z0-9]{1,10}(?:-[A-Z0-9]{2,10})+)\b",
        re.I,
    ),
    re.compile(
        r"\b([A-Z0-9]{1,10}(?:-[A-Z0-9]{2,10})+)\b\s+(?:replaces|is the replacement for|succeeds)\b",
        re.I,
    ),
)
EXAM_CODE_PATTERN = re.compile(r"\b[A-Z0-9]{1,10}(?:-[A-Z0-9]{2,10})+\b", re.I)
SPACE_PATTERN = re.compile(r"\s+")
TAG_PATTERN = re.compile(r"<[^>]+>")


def _clean_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", value)
    value = TAG_PATTERN.sub(" ", value)
    return SPACE_PATTERN.sub(" ", html.unescape(value)).strip()


def _evidence_snippet(text: str, match: re.Match[str], radius: int = 180) -> str:
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    return SPACE_PATTERN.sub(" ", text[start:end]).strip()


def analyze_lifecycle_text(raw_text: str) -> dict[str, Any] | None:
    """Return strong exam-specific lifecycle evidence or ``None``.

    Generic curricular references such as retirement income are intentionally
    excluded by requiring an exam, credential, or certification term near the
    lifecycle verb.
    """
    text = _clean_text(raw_text)
    status = None
    match = None
    for pattern in RETIREMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            status = "retired"
            break
    if not match:
        for pattern in SCHEDULED_PATTERNS:
            match = pattern.search(text)
            if match:
                status = "scheduled_retirement"
                break
    if not match or not status:
        return None

    replacement_code = None
    replacement_match = None
    for pattern in REPLACEMENT_PATTERNS:
        replacement_match = pattern.search(text)
        if replacement_match:
            replacement_code = replacement_match.group(1).upper()
            break

    return {
        "status": status,
        "replacement_exam_code": replacement_code,
        "confidence": 0.98 if replacement_code else 0.9,
        "evidence": _evidence_snippet(text, replacement_match or match),
    }


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._parts: list[str] = []
        self._ignored_text_depth = 0
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_text_depth += 1
            return
        if tag.lower() != "a":
            return
        self._href = next((value for key, value in attrs if key.lower() == "href"), None)
        self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None and self._ignored_text_depth == 0:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style"}:
            self._ignored_text_depth = max(0, self._ignored_text_depth - 1)
            return
        if tag.lower() == "a" and self._href is not None:
            self.links.append((self._href, SPACE_PATTERN.sub(" ", " ".join(self._parts)).strip()))
            self._href = None
            self._parts = []


def _normalized_url(value: str) -> str:
    parsed = urlsplit(value)
    path = parsed.path.rstrip("/") or "/"
    # Locale prefixes are routing variants, not distinct exam catalog entries.
    path = re.sub(r"^/[a-z]{2}(?:-[a-z]{2})?(?=/)", "", path, flags=re.I) or "/"
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, "", ""))


def discover_missing_catalog_links(
    raw_html: str,
    *,
    catalog_url: str,
    known_urls: Iterable[str],
) -> list[dict[str, str | None]]:
    """Find plausible same-provider exam links absent from the registry."""
    parser = _LinkParser()
    parser.feed(raw_html)
    catalog_host = urlsplit(catalog_url).netloc.lower()
    known = {_normalized_url(value) for value in known_urls if value}
    ignored_terms = ("support", "sign in", "login", "privacy", "terms", "contact")
    discovered: dict[str, dict[str, str | None]] = {}

    for href, title in parser.links:
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        absolute = _normalized_url(urljoin(catalog_url, href))
        parsed = urlsplit(absolute)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != catalog_host:
            continue
        if absolute in known or any(term in title.lower() for term in ignored_terms):
            continue

        path = parsed.path.lower()
        code_match = EXAM_CODE_PATTERN.search(title)
        exam_like_path = any(term in path for term in ("/exam", "/certif", "/credential"))
        exam_like_title = bool(
            re.search(r"\b(?:exam|examination|certification|credential)\b", title, re.I)
        )
        if not title or not (exam_like_path and (exam_like_title or code_match)):
            continue

        discovered[absolute] = {
            "url": absolute,
            "title": title,
            "exam_code": code_match.group(0).upper() if code_match else None,
        }

    return sorted(discovered.values(), key=lambda item: (item["exam_code"] or "", item["url"] or ""))


def _fetch_catalog(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": "CertAtlasLifecycleAudit/1.0 (+https://atlas.quizforge.ai/)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.5",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read(5 * 1024 * 1024 + 1)
            if len(body) > 5 * 1024 * 1024:
                body = body[: 5 * 1024 * 1024]
            return {
                "status": getattr(response, "status", 200),
                "final_url": response.geturl(),
                "content_type": response.headers.get("Content-Type", ""),
                "body": body,
                "error": None,
            }
    except Exception as error:
        return {
            "status": getattr(error, "code", None),
            "final_url": getattr(error, "url", url),
            "content_type": "",
            "body": b"",
            "error": f"{type(error).__name__}: {error}",
        }


def scan_provider_catalogs(
    registry_path: Path | str,
    *,
    fetcher: Any = _fetch_catalog,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Fetch every configured provider catalog and flag unregistered exam links."""
    connection = sqlite3.connect(Path(registry_path))
    connection.row_factory = sqlite3.Row
    bodies = connection.execute(
        "SELECT body_id, display_name, base_url, exam_list_url, notes "
        "FROM certifying_bodies ORDER BY body_id"
    ).fetchall()
    exams = connection.execute(
        "SELECT exam_id, certifying_body_id, blueprint_json, source_url FROM exams ORDER BY exam_id"
    ).fetchall()
    connection.close()

    known_urls: dict[str, set[str]] = defaultdict(set)
    known_codes: dict[str, set[str]] = defaultdict(set)
    for row in exams:
        body_id = str(row["certifying_body_id"])
        if row["source_url"]:
            known_urls[body_id].add(str(row["source_url"]))
        try:
            blueprint = json.loads(row["blueprint_json"])
        except (TypeError, json.JSONDecodeError):
            blueprint = {}
        code = str(blueprint.get("exam_code") or "").strip().upper()
        if code:
            known_codes[body_id].add(code)

    provider_results: list[dict[str, Any]] = []
    missing_url_results: list[dict[str, Any]] = []
    fetchable: list[sqlite3.Row] = []
    for body in bodies:
        catalog_url = str(body["exam_list_url"] or "").strip()
        if not catalog_url.startswith(("http://", "https://")):
            missing_url_results.append(
                {
                    "body_id": body["body_id"],
                    "display_name": body["display_name"],
                    "status": "missing_catalog_url",
                    "notes": body["notes"],
                }
            )
        else:
            fetchable.append(body)

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
        futures = {
            executor.submit(fetcher, str(body["exam_list_url"])): body for body in fetchable
        }
        for future in as_completed(futures):
            body = futures[future]
            body_id = str(body["body_id"])
            try:
                fetched = future.result()
            except Exception as error:
                fetched = {
                    "status": None,
                    "final_url": body["exam_list_url"],
                    "content_type": "",
                    "body": b"",
                    "error": f"{type(error).__name__}: {error}",
                }
            raw_body = fetched.get("body") or b""
            if isinstance(raw_body, str):
                body_bytes = raw_body.encode("utf-8", errors="ignore")
                raw_html = raw_body
            else:
                body_bytes = bytes(raw_body)
                raw_html = body_bytes.decode("utf-8", errors="ignore")
            links = []
            if fetched.get("status") == 200 and "pdf" not in str(fetched.get("content_type") or "").lower():
                links = discover_missing_catalog_links(
                    raw_html,
                    catalog_url=str(fetched.get("final_url") or body["exam_list_url"]),
                    known_urls=known_urls.get(body_id, set()),
                )
                links = [
                    link
                    for link in links
                    if not link.get("exam_code")
                    or str(link["exam_code"]).upper() not in known_codes.get(body_id, set())
                ]
            provider_results.append(
                {
                    "body_id": body_id,
                    "display_name": body["display_name"],
                    "catalog_url": body["exam_list_url"],
                    "final_url": fetched.get("final_url"),
                    "http_status": fetched.get("status"),
                    "content_type": fetched.get("content_type"),
                    "content_hash": "sha256:" + hashlib.sha256(body_bytes).hexdigest() if body_bytes else None,
                    "error": fetched.get("error"),
                    "new_exam_candidates": links,
                }
            )

    provider_results.extend(missing_url_results)
    provider_results.sort(key=lambda item: str(item["body_id"]))
    candidates = []
    for provider in provider_results:
        for candidate in provider.get("new_exam_candidates", []):
            candidates.append(
                {
                    "body_id": provider["body_id"],
                    "certifying_body": provider["display_name"],
                    **candidate,
                }
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": "same-provider catalog link comparison; candidates require official manual verification",
        "coverage": {
            "providers_total": len(bodies),
            "providers_with_catalog_url": len(fetchable),
            "providers_without_catalog_url": len(missing_url_results),
            "catalogs_fetched": sum(1 for item in provider_results if item.get("http_status") == 200),
            "catalog_fetch_failures": sum(
                1
                for item in provider_results
                if item.get("status") != "missing_catalog_url" and item.get("http_status") != 200
            ),
            "new_exam_candidates": len(candidates),
        },
        "new_exam_candidates": sorted(
            candidates,
            key=lambda item: (str(item["body_id"]), str(item.get("exam_code") or ""), str(item["url"])),
        ),
        "providers": provider_results,
    }


def _read_source_text(path: Path) -> tuple[str | None, str | None]:
    try:
        if path.suffix.lower() == ".pdf":
            # PDF guides are already normalized into blueprint_json by the registry
            # pipeline. Retirement notices are expected on current landing/catalog
            # HTML; parsing thousands of arbitrary PDFs here is both redundant and
            # vulnerable to malformed or mislabeled files.
            return None, "binary_pdf"
        return path.read_text(encoding="utf-8", errors="ignore"), None
    except Exception as error:  # Corrupt and encrypted evidence must remain visible in coverage.
        return None, f"{type(error).__name__}: {error}"


def scan_registry_snapshot(
    registry_path: Path | str,
    *,
    source_root: Path | str,
    public_exam_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Scan all registry exams and all available local evidence files."""
    registry_path = Path(registry_path)
    source_root = Path(source_root)
    public_exam_ids = public_exam_ids or set()
    connection = sqlite3.connect(registry_path)
    connection.row_factory = sqlite3.Row
    exam_rows = connection.execute(
        "SELECT exam_id, certifying_body_id, blueprint_json, source_url, last_fetched FROM exams ORDER BY exam_id"
    ).fetchall()
    source_rows = connection.execute(
        "SELECT exam_id, role, doc_url, final_url, local_path, status, fetched_at, content_hash "
        "FROM source_materials ORDER BY exam_id, id"
    ).fetchall()
    body_rows = connection.execute(
        "SELECT body_id, display_name, base_url, exam_list_url FROM certifying_bodies ORDER BY body_id"
    ).fetchall()
    connection.close()

    sources_by_exam: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for source in source_rows:
        sources_by_exam[str(source["exam_id"])].append(source)

    candidates: list[dict[str, Any]] = []
    source_files_scanned = 0
    binary_pdf_records = 0
    source_parse_errors: list[dict[str, str]] = []
    exams_with_local_sources = 0

    for row in exam_rows:
        exam_id = str(row["exam_id"])
        try:
            blueprint = json.loads(row["blueprint_json"])
        except (TypeError, json.JSONDecodeError):
            blueprint = {}
        local_sources = [source for source in sources_by_exam.get(exam_id, []) if source["local_path"]]
        if local_sources:
            exams_with_local_sources += 1

        evidence_items: list[dict[str, Any]] = []
        for source in local_sources:
            path = source_root / str(source["local_path"])
            if not path.is_file():
                source_parse_errors.append({"exam_id": exam_id, "path": str(path), "error": "file not found"})
                continue
            source_files_scanned += 1
            raw_text, error = _read_source_text(path)
            if error == "binary_pdf":
                binary_pdf_records += 1
                continue
            if error:
                source_parse_errors.append({"exam_id": exam_id, "path": str(path), "error": error})
                continue
            evidence = analyze_lifecycle_text(raw_text or "")
            if evidence:
                evidence_items.append(
                    {
                        **evidence,
                        "role": source["role"],
                        "url": source["final_url"] or source["doc_url"],
                        "fetched_at": source["fetched_at"],
                        "content_hash": source["content_hash"],
                    }
                )

        if evidence_items:
            best = max(
                evidence_items,
                key=lambda item: (item["confidence"], bool(item["replacement_exam_code"])),
            )
            candidates.append(
                {
                    "exam_id": exam_id,
                    "exam_code": blueprint.get("exam_code"),
                    "exam_name": blueprint.get("exam_name"),
                    "certifying_body_id": row["certifying_body_id"],
                    "certifying_body": blueprint.get("certifying_body"),
                    "public": exam_id in public_exam_ids,
                    "status": best["status"],
                    "replacement_exam_code": best["replacement_exam_code"],
                    "confidence": best["confidence"],
                    "source_url": row["source_url"],
                    "last_fetched": row["last_fetched"],
                    "evidence": evidence_items,
                }
            )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "publication_policy": "candidate_only_manual_official_verification_required",
            "local_material_hash": "sha256:"
            + hashlib.sha256(
                "\n".join(
                    f"{row['exam_id']}|{row['content_hash'] or ''}|{row['fetched_at'] or ''}"
                    for row in source_rows
                ).encode("utf-8")
            ).hexdigest(),
        },
        "coverage": {
            "registry_exams": len(exam_rows),
            "exam_records_scanned": len(exam_rows),
            "certifying_bodies": len(body_rows),
            "source_material_records": len(source_rows),
            "source_files_scanned": source_files_scanned,
            "html_or_text_sources_scanned": source_files_scanned - binary_pdf_records,
            "binary_pdf_records_normalized_via_blueprints": binary_pdf_records,
            "exams_with_local_sources": exams_with_local_sources,
            "exams_without_local_sources": len(exam_rows) - exams_with_local_sources,
            "source_parse_errors": len(source_parse_errors),
        },
        "candidates": sorted(candidates, key=lambda item: item["exam_id"]),
        "source_parse_errors": source_parse_errors,
        "provider_catalogs": [dict(row) for row in body_rows],
    }
    return report


def _load_public_ids(path: Path | None) -> set[str]:
    if path is None:
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(item["exam_id"]) for item in data.get("exams", []) if item.get("exam_id")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--public-index", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--provider-output",
        type=Path,
        help="Also compare fetchable provider catalogs and write the candidate link report.",
    )
    parser.add_argument("--provider-workers", type=int, default=8)
    args = parser.parse_args()

    report = scan_registry_snapshot(
        args.registry,
        source_root=args.source_root,
        public_exam_ids=_load_public_ids(args.public_index),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary: dict[str, Any] = {
        "coverage": report["coverage"],
        "lifecycle_candidates": len(report["candidates"]),
    }
    if args.provider_output:
        provider_report = scan_provider_catalogs(
            args.registry,
            max_workers=args.provider_workers,
        )
        args.provider_output.parent.mkdir(parents=True, exist_ok=True)
        args.provider_output.write_text(
            json.dumps(provider_report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        summary["provider_coverage"] = provider_report["coverage"]
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
