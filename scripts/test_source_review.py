import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_site


def test_review_is_visible_without_claiming_full_quality_approval():
    exam = {"exam_id": "test", "exam_name": "Test", "domains": [], "source_review": {
        "checked_at": "2026-09-05", "effective_at": "2026-04-17", "source_url": "https://example.org/guide",
        "policy_url": "https://example.org/policy", "method": "Official-source reconciliation",
        "changes": ["Corrected an objective"], "study_actions": []}}
    page = build_site.build_exam_page("microsoft", {"display_name": "Microsoft"}, exam)
    assert "Source review and study planning" in page
    assert "Objectives effective 2026-04-17" in page
    assert "Corrected an objective" in page


def test_sitemap_only_uses_explicit_content_modification_dates():
    xml = build_site.build_sitemap({}, {"microsoft": [{"exam_id": "reviewed", "content_modified_at": "2026-09-05"}, {"exam_id": "unreviewed"}]})
    assert xml.count("<lastmod>") == 1
    assert "<lastmod>2026-09-05</lastmod>" in xml


def test_official_resource_with_unknown_price_has_no_free_claim():
    exam = {"exam_id": "test", "exam_name": "Test", "domains": [],
            "official_study_resources": [{"title": "Learning paths or instructor-led course",
            "url": "https://learn.microsoft.com/training/", "price_usd": None}]}
    page = build_site.build_exam_page("microsoft", {"display_name": "Microsoft"}, exam)
    assert "Learning paths or instructor-led course" in page
    assert "(free)" not in page
