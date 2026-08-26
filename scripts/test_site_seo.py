import re
import unittest
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"


def text_content(fragment: str) -> str:
    return re.sub(r"<[^>]+>", "", fragment).strip()


class GeneratedSiteSeoTests(unittest.TestCase):
    def test_every_sitemap_url_maps_to_self_canonical_indexable_html(self):
        sitemap = ET.parse(DOCS_DIR / "sitemap.xml")
        namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locations = [node.text for node in sitemap.findall("sm:url/sm:loc", namespace)]
        self.assertEqual(len(locations), len(set(locations)), "sitemap URLs must be unique")

        failures = []
        prefix = "https://atlas.quizforge.ai/"
        for location in locations:
            relative = location.removeprefix(prefix)
            page = DOCS_DIR / (relative + "index.html" if not relative or relative.endswith("/") else relative + ".html")
            if not page.exists():
                failures.append(f"{location}: no generated file")
                continue

            html = page.read_text(encoding="utf-8")
            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html, re.I)
            if not canonical or canonical.group(1) != location:
                failures.append(f"{location}: canonical is {canonical.group(1) if canonical else 'missing'}")
            if re.search(r'<meta[^>]+name="robots"[^>]+noindex', html, re.I):
                failures.append(f"{location}: noindex")

        self.assertFalse(failures, "\n".join(failures[:50]))

    def test_every_page_has_one_page_specific_h1(self):
        failures = []
        for path in DOCS_DIR.rglob("*.html"):
            html = path.read_text(encoding="utf-8")
            headings = re.findall(r"<h1\b[^>]*>(.*?)</h1>", html, re.I | re.S)
            if len(headings) != 1:
                failures.append(f"{path.relative_to(DOCS_DIR)}: {len(headings)} h1 elements")
                continue

            canonical = re.search(r'<link rel="canonical" href="([^"]+)"', html, re.I)
            heading = text_content(headings[0])
            if canonical and canonical.group(1) != "https://atlas.quizforge.ai/" and heading == "Cert Atlas":
                failures.append(f"{path.relative_to(DOCS_DIR)}: generic site-name h1")

        self.assertFalse(failures, "\n".join(failures[:50]))

    def test_indexable_pages_have_unique_titles(self):
        by_title = defaultdict(list)
        for path in DOCS_DIR.rglob("*.html"):
            html = path.read_text(encoding="utf-8")
            title = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
            if title:
                by_title[text_content(title.group(1))].append(path.relative_to(DOCS_DIR))

        duplicates = {
            title: paths for title, paths in by_title.items() if len(paths) > 1
        }
        self.assertFalse(
            duplicates,
            "\n".join(f"{title}: {', '.join(map(str, paths))}" for title, paths in duplicates.items()),
        )


if __name__ == "__main__":
    unittest.main()
