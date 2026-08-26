#!/usr/bin/env python3
"""Tests for the all-record certification lifecycle audit."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.lifecycle_audit import (
    analyze_lifecycle_text,
    discover_missing_catalog_links,
    scan_provider_catalogs,
    scan_registry_snapshot,
)


class LifecycleTextTests(unittest.TestCase):
    def test_detects_retired_exam_and_replacement_code(self):
        result = analyze_lifecycle_text(
            "AI-102 retired on June 30, 2026 and was replaced by Exam AI-103."
        )

        self.assertEqual(result["status"], "retired")
        self.assertEqual(result["replacement_exam_code"], "AI-103")
        self.assertGreaterEqual(result["confidence"], 0.9)

    def test_detects_announced_future_retirement(self):
        result = analyze_lifecycle_text(
            "The AZ-204 exam will retire on July 31, 2026. Its replacement exam is AZ-200."
        )

        self.assertEqual(result["status"], "scheduled_retirement")
        self.assertEqual(result["replacement_exam_code"], "AZ-200")

    def test_rejects_retirement_as_an_exam_topic(self):
        result = analyze_lifecycle_text(
            "Candidates calculate retirement income, pension distributions, and tax liability."
        )

        self.assertIsNone(result)

    def test_does_not_invent_a_replacement(self):
        result = analyze_lifecycle_text("The legacy examination was retired on May 1, 2026.")

        self.assertEqual(result["status"], "retired")
        self.assertIsNone(result["replacement_exam_code"])


class CatalogDiscoveryTests(unittest.TestCase):
    def test_discovers_only_plausible_unregistered_exam_links(self):
        html = """
        <html><body>
          <a href="/credentials/certifications/exams/ai-103">Exam AI-103: Azure AI App Developer</a>
          <a href="/credentials/certifications/exams/ai-102">Exam AI-102</a>
          <a href="/support">Support</a>
          <a href="https://unrelated.example/exam-xy-1">Exam XY-1</a>
        </body></html>
        """

        candidates = discover_missing_catalog_links(
            html,
            catalog_url="https://learn.microsoft.com/en-us/credentials/certifications/",
            known_urls={
                "https://learn.microsoft.com/en-us/credentials/certifications/exams/ai-102"
            },
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["exam_code"], "AI-103")
        self.assertTrue(candidates[0]["url"].endswith("/exams/ai-103"))

    def test_discards_embedded_style_text_from_link_titles(self):
        html = """
        <a href="/certifications/cof-c03">
          Certification COF-C03 SnowPro Core
          <style>.button { display: inline-flex; color: blue; }</style>
          Learn More
        </a>
        """

        candidates = discover_missing_catalog_links(
            html,
            catalog_url="https://learn.snowflake.com/en/certifications/",
            known_urls=set(),
        )

        self.assertEqual(candidates[0]["exam_code"], "COF-C03")
        self.assertEqual(
            candidates[0]["title"],
            "Certification COF-C03 SnowPro Core Learn More",
        )


class RegistrySnapshotTests(unittest.TestCase):
    def test_scans_every_exam_and_records_source_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_dir = root / "data" / "source_material" / "vendor"
            data_dir.mkdir(parents=True)
            (data_dir / "old.html").write_text(
                "<p>EX-100 retired on June 1, 2026 and was replaced by EX-200.</p>",
                encoding="utf-8",
            )
            (data_dir / "active.html").write_text(
                "<p>EX-300 tests current platform administration skills.</p>",
                encoding="utf-8",
            )

            db_path = root / "registry.db"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE certifying_bodies (
                    body_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    exam_list_url TEXT NOT NULL,
                    notes TEXT
                );
                CREATE TABLE exams (
                    exam_id TEXT PRIMARY KEY,
                    certifying_body_id TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_fetched TEXT NOT NULL,
                    content_hash TEXT
                );
                CREATE TABLE source_materials (
                    id INTEGER PRIMARY KEY,
                    exam_id TEXT NOT NULL,
                    body_id TEXT,
                    role TEXT,
                    doc_url TEXT NOT NULL,
                    final_url TEXT,
                    doc_type TEXT,
                    local_path TEXT,
                    content_hash TEXT,
                    byte_size INTEGER,
                    http_status INTEGER,
                    discovery_method TEXT,
                    is_primary INTEGER DEFAULT 0,
                    status TEXT,
                    error TEXT,
                    fetched_at TEXT
                );
                """
            )
            blueprints = [
                {
                    "exam_id": "vendor-ex-100",
                    "exam_name": "Legacy Exam",
                    "exam_code": "EX-100",
                    "certifying_body": "Vendor",
                },
                {
                    "exam_id": "vendor-ex-300",
                    "exam_name": "Current Exam",
                    "exam_code": "EX-300",
                    "certifying_body": "Vendor",
                },
                {
                    "exam_id": "vendor-ex-400",
                    "exam_name": "No Local Source",
                    "exam_code": "EX-400",
                    "certifying_body": "Vendor",
                },
            ]
            connection.execute(
                "INSERT INTO certifying_bodies VALUES (?, ?, ?, ?, ?)",
                ("vendor", "Vendor", "https://vendor.example", "https://vendor.example/exams", ""),
            )
            for blueprint in blueprints:
                connection.execute(
                    "INSERT INTO exams VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        blueprint["exam_id"],
                        "vendor",
                        json.dumps(blueprint),
                        f"https://vendor.example/{blueprint['exam_id']}",
                        "2026-08-01T00:00:00+00:00",
                        "hash",
                    ),
                )
            connection.executemany(
                "INSERT INTO source_materials (exam_id, body_id, role, doc_url, local_path, status, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        "vendor-ex-100",
                        "vendor",
                        "landing",
                        "https://vendor.example/old",
                        "data/source_material/vendor/old.html",
                        "downloaded",
                        "2026-08-01T00:00:00+00:00",
                    ),
                    (
                        "vendor-ex-300",
                        "vendor",
                        "landing",
                        "https://vendor.example/active",
                        "data/source_material/vendor/active.html",
                        "downloaded",
                        "2026-08-01T00:00:00+00:00",
                    ),
                ],
            )
            connection.commit()
            connection.close()

            report = scan_registry_snapshot(db_path, source_root=root)

            self.assertEqual(report["coverage"]["registry_exams"], 3)
            self.assertEqual(report["coverage"]["exams_with_local_sources"], 2)
            self.assertEqual(report["coverage"]["exams_without_local_sources"], 1)
            self.assertEqual(report["coverage"]["exam_records_scanned"], 3)
            self.assertEqual(report["candidates"][0]["exam_id"], "vendor-ex-100")
            self.assertEqual(report["candidates"][0]["replacement_exam_code"], "EX-200")

    def test_live_catalog_scan_accounts_for_every_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            db_path = Path(temp) / "registry.db"
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE certifying_bodies (
                    body_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    exam_list_url TEXT NOT NULL,
                    notes TEXT
                );
                CREATE TABLE exams (
                    exam_id TEXT PRIMARY KEY,
                    certifying_body_id TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    last_fetched TEXT NOT NULL,
                    content_hash TEXT
                );
                """
            )
            connection.executemany(
                "INSERT INTO certifying_bodies VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        "vendor",
                        "Vendor",
                        "https://vendor.example",
                        "https://vendor.example/exams",
                        "",
                    ),
                    ("import", "Imported", "", "", "qf_import"),
                ],
            )
            connection.execute(
                "INSERT INTO exams VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "vendor-ex-100",
                    "vendor",
                    json.dumps({"exam_code": "EX-100", "exam_name": "Existing"}),
                    "https://vendor.example/exams/ex-100",
                    "2026-08-01T00:00:00+00:00",
                    "hash",
                ),
            )
            connection.commit()
            connection.close()

            def fake_fetch(url):
                self.assertEqual(url, "https://vendor.example/exams")
                return {
                    "status": 200,
                    "final_url": url,
                    "content_type": "text/html",
                    "body": (
                        b'<a href="/exams/ex-100">Exam EX-100</a>'
                        b'<a href="/exams/ex-200">Exam EX-200</a>'
                    ),
                    "error": None,
                }

            report = scan_provider_catalogs(db_path, fetcher=fake_fetch, max_workers=1)

            self.assertEqual(report["coverage"]["providers_total"], 2)
            self.assertEqual(report["coverage"]["catalogs_fetched"], 1)
            self.assertEqual(report["coverage"]["providers_without_catalog_url"], 1)
            self.assertEqual(report["new_exam_candidates"][0]["exam_code"], "EX-200")


if __name__ == "__main__":
    unittest.main()
