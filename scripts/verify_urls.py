#!/usr/bin/env python3
"""
Verify practice_url links in cert-atlas data point to real QuizForge pages.

Checks a sample of direct slug URLs (rate-limited to avoid 429s).
Reports broken links and stats.
"""

import json
import os
import sys
import time
import random
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    os.system("pip install requests -q")
    import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
QUIZFORGE_HOST = "quizforge.ai"
TIMEOUT = 10
DELAY = 0.5  # seconds between requests


def check_url(practice_url):
    """Check if a practice URL resolves on QuizForge. Returns (status, http_code)."""
    parsed = urlparse(practice_url)
    if parsed.path == "/" and "q=" in (parsed.query or ""):
        return "search_fallback", None

    try:
        resp = requests.get(
            practice_url,
            headers={"Host": QUIZFORGE_HOST},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        return ("ok" if resp.status_code == 200 else "broken"), resp.status_code
    except requests.RequestException as e:
        return "error", str(e)


def main():
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50

    # Collect all practice URLs
    all_urls = []
    for vendor_dir in sorted(DATA_DIR.iterdir()):
        if not vendor_dir.is_dir():
            continue
        for exam_file in sorted(vendor_dir.glob("*.json")):
            with open(exam_file, encoding="utf-8") as f:
                exam = json.load(f)
            exam_id = exam.get("exam_id", exam_file.stem)
            practice_url = exam.get("practice_url", "")
            if practice_url:
                all_urls.append((exam_id, practice_url))

    # Categorize
    direct = [(eid, url) for eid, url in all_urls if "/?q=" not in url]
    search = [(eid, url) for eid, url in all_urls if "/?q=" in url]

    print(f"Total exams: {len(all_urls)}")
    print(f"  Direct slug links: {len(direct)}")
    print(f"  Search fallback links: {len(search)}")
    print()

    # Sample direct URLs for verification
    sample = random.sample(direct, min(sample_size, len(direct)))
    print(f"Verifying {len(sample)} random direct links (with {DELAY}s delay)...")
    print()

    ok = 0
    broken = []
    errors = []

    for i, (eid, url) in enumerate(sample):
        status, detail = check_url(url)
        if status == "ok":
            ok += 1
            print(f"  OK  {eid}")
        elif status == "broken":
            broken.append((eid, url, detail))
            print(f"  BROKEN [{detail}] {eid} -> {url}")
        else:
            errors.append((eid, url, detail))
            print(f"  ERROR {eid} -> {detail}")

        if i < len(sample) - 1:
            time.sleep(DELAY)

    # Report
    print()
    print("=" * 60)
    print(f"Sample: {len(sample)} direct links checked")
    print(f"  OK:     {ok}")
    print(f"  Broken: {len(broken)}")
    print(f"  Errors: {len(errors)}")
    print()
    print(f"Overall breakdown:")
    print(f"  Direct (verified by slug): {len(direct)}")
    print(f"  Search fallback:           {len(search)}")

    if broken:
        print()
        print("BROKEN LINKS:")
        for eid, url, code in broken:
            print(f"  [{code}] {eid} -> {url}")

    if broken or errors:
        sys.exit(1)
    else:
        print()
        print(f"All {len(sample)} sampled links verified OK.")


if __name__ == "__main__":
    main()
