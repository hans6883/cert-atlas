#!/usr/bin/env python3
"""
Generate a static GitHub Pages site from cert-atlas JSON data.

Produces:
  docs/index.html                         -- Main browse page
  docs/{vendor-slug}/index.html           -- Per-vendor index
  docs/{vendor-slug}/{exam-id}.html       -- Per-exam detail page
  docs/sitemap.xml                        -- For Google
  docs/robots.txt
  docs/CNAME                              -- Custom domain (optional)
"""

import json
import os
import html as html_mod
from pathlib import Path
from datetime import datetime, timezone

try:
    from scripts.enrichment import has_public_enrichment
except ImportError:
    from enrichment import has_public_enrichment

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = REPO_ROOT / "docs"
SITE_URL = "https://atlas.quizforge.ai"
QUIZFORGE_URL = "https://quizforge.ai"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def h(text):
    """HTML-escape."""
    if text is None:
        return ""
    return html_mod.escape(str(text))


def format_iso_date(value):
    text = str(value or "")
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%B %d, %Y").replace(
            " 0", " "
        )
    except ValueError:
        return text


def load_data():
    with open(DATA_DIR / "index.json", encoding="utf-8") as f:
        index = json.load(f)
    with open(DATA_DIR / "vendors.json", encoding="utf-8") as f:
        vendors = json.load(f)

    exams_by_vendor = {}
    for entry in index["exams"]:
        slug = entry["vendor_slug"]
        exams_by_vendor.setdefault(slug, []).append(entry)

    vendor_map = {v["slug"]: v for v in vendors["vendors"]}
    return index, vendors, exams_by_vendor, vendor_map


def load_exam(vendor_slug, exam_id):
    path = DATA_DIR / vendor_slug / f"{exam_id}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CSS = """
:root {
  --bg: #ffffff;
  --bg-alt: #f8f9fa;
  --text: #1a1a2e;
  --text-muted: #6c757d;
  --accent: #2563eb;
  --accent-hover: #1d4ed8;
  --border: #e2e8f0;
  --bar: #3b82f6;
  --bar-bg: #e2e8f0;
  --card-shadow: 0 1px 3px rgba(0,0,0,0.08);
  --radius: 8px;
  --green: #059669;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--accent); text-decoration: none; }
a:hover { color: var(--accent-hover); text-decoration: underline; }

.container { max-width: 960px; margin: 0 auto; padding: 0 24px; }

header {
  border-bottom: 1px solid var(--border);
  padding: 16px 0;
  background: var(--bg);
  position: sticky;
  top: 0;
  z-index: 10;
}
header .container { display: flex; align-items: center; justify-content: space-between; }
header .site-name { font-size: 20px; font-weight: 700; }
header .site-name a { color: var(--text); }
header nav a { margin-left: 24px; font-size: 14px; color: var(--text-muted); }
header nav a:hover { color: var(--accent); text-decoration: none; }

.hero { padding: 48px 0 32px; }
.hero h1 { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.hero p { font-size: 18px; color: var(--text-muted); max-width: 600px; }

.stats-bar {
  display: flex; gap: 32px; padding: 16px 0 32px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.stat { text-align: center; }
.stat-num { font-size: 28px; font-weight: 700; color: var(--accent); display: block; }
.stat-label { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

.search-box {
  width: 100%; padding: 12px 16px;
  border: 1px solid var(--border); border-radius: var(--radius);
  font-size: 16px; outline: none;
  margin-bottom: 24px;
}
.search-box:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }

.vendor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 48px;
}
.vendor-card {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 20px;
  transition: box-shadow 0.15s;
}
.vendor-card:hover { box-shadow: var(--card-shadow); text-decoration: none; }
.vendor-card h3 { font-size: 16px; margin-bottom: 4px; }
.vendor-card .count { color: var(--text-muted); font-size: 14px; }

.breadcrumb {
  padding: 12px 0;
  font-size: 14px;
  color: var(--text-muted);
}
.breadcrumb a { color: var(--text-muted); }
.breadcrumb span { margin: 0 6px; }

.exam-header { padding: 24px 0 16px; }
.exam-header h1 { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.exam-header .exam-code { color: var(--text-muted); font-size: 16px; }
.exam-header .vendor-link { font-size: 14px; margin-top: 8px; }

.quick-facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin: 20px 0 32px;
}
.fact {
  background: var(--bg-alt);
  padding: 16px;
  border-radius: var(--radius);
  text-align: center;
}
.fact-value { font-size: 20px; font-weight: 700; display: block; }
.fact-label { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }

section.domains { margin: 32px 0; }
section.domains h3 { font-size: 20px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }

.domain {
  margin-bottom: 24px;
  padding: 16px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.domain-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.domain-name { font-weight: 600; font-size: 16px; }
.domain-weight { font-weight: 700; color: var(--accent); font-size: 15px; white-space: nowrap; }
.domain-weight.weight-na { font-weight: 400; color: var(--text-muted); font-size: 13px; font-style: italic; }
.domain-bar { height: 6px; background: var(--bar-bg); border-radius: 3px; margin-bottom: 12px; }
.domain-bar-fill { height: 100%; background: var(--bar); border-radius: 3px; }

.objectives { list-style: none; padding-left: 0; }
.objectives li { padding: 4px 0 4px 16px; font-size: 14px; border-left: 2px solid var(--border); margin-bottom: 4px; }
.obj-id { color: var(--text-muted); font-weight: 600; margin-right: 6px; font-size: 13px; }
.sub-objectives { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

section.info { margin: 32px 0; }
section.info h3 { font-size: 20px; margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
.info-grid { display: grid; gap: 12px; }
.info-row { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--bg-alt); font-size: 14px; }
.info-label { font-weight: 600; min-width: 180px; color: var(--text-muted); }
.info-value { flex: 1; }

.practice-cta {
  display: inline-block;
  background: var(--accent);
  color: #fff;
  padding: 12px 28px;
  border-radius: var(--radius);
  font-size: 16px;
  font-weight: 600;
  margin: 24px 0;
  transition: background 0.15s;
}
.practice-cta:hover { background: var(--accent-hover); color: #fff; text-decoration: none; }

.resources { margin: 24px 0; }
.resource-item { padding: 8px 0; border-bottom: 1px solid var(--bg-alt); font-size: 14px; }
.resource-type { display: inline-block; background: var(--bg-alt); padding: 2px 8px; border-radius: 4px; font-size: 12px; color: var(--text-muted); margin-right: 8px; }

.exam-list { list-style: none; }
.exam-list li { padding: 12px 0; border-bottom: 1px solid var(--border); }
.exam-list li:last-child { border-bottom: none; }
.exam-list a { font-weight: 500; }
.exam-list .meta { font-size: 13px; color: var(--text-muted); margin-top: 2px; }

footer {
  border-top: 1px solid var(--border);
  padding: 24px 0;
  margin-top: 48px;
  font-size: 13px;
  color: var(--text-muted);
  text-align: center;
}
footer a { color: var(--text-muted); }

.source-link { font-size: 13px; color: var(--text-muted); margin-top: 8px; }
.source-link a { color: var(--text-muted); }

@media (max-width: 640px) {
  .hero h1 { font-size: 24px; }
  .stats-bar { gap: 16px; flex-wrap: wrap; }
  .quick-facts { grid-template-columns: repeat(2, 1fr); }
  .info-row { flex-direction: column; gap: 2px; }
  .info-label { min-width: auto; }
}
"""

ENRICHMENT_CSS = """
.editorial { margin: 32px 0; }
.editorial h2 { margin: 28px 0 10px; font-size: 23px; }
.editorial h3 { margin: 22px 0 8px; font-size: 18px; }
.editorial p { margin: 0 0 14px; }
.editorial ul { margin: 8px 0 18px 22px; }
.editorial li { margin: 5px 0; }
.study-signals { background: var(--bg-alt); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
.signal-note { color: var(--text-muted); font-size: 13px; }
.verification { border-top: 1px solid var(--border); padding-top: 20px; }
.verification-date { color: var(--text-muted); font-size: 13px; margin-bottom: 10px; }
.source-list { list-style: none; margin-left: 0; }
.source-list li { margin: 8px 0; }
.source-publisher { color: var(--text-muted); font-size: 13px; }
.retirement-alert { background: #fff7ed; border: 1px solid #fdba74; border-left: 5px solid #ea580c; border-radius: var(--radius); margin: 20px 0 28px; padding: 20px; }
.retirement-alert h2 { margin: 0 0 8px; font-size: 22px; }
.retirement-label { color: #9a3412; font-size: 12px; font-weight: 700; letter-spacing: .06em; margin-bottom: 6px; text-transform: uppercase; }
.replacement-link { display: inline-block; font-weight: 700; margin-top: 6px; }
.migration-map { margin: 30px 0; }
.comparison-wrap { overflow-x: auto; }
.comparison-table { border-collapse: collapse; font-size: 14px; margin: 12px 0 20px; min-width: 720px; width: 100%; }
.comparison-table th, .comparison-table td { border: 1px solid var(--border); padding: 10px; text-align: left; vertical-align: top; }
.comparison-table th { background: var(--bg-alt); }
.methodology { background: var(--bg-alt); border-radius: var(--radius); padding: 18px; }
.source-accessed { color: var(--text-muted); font-size: 12px; }
"""


def page_shell(
    title,
    description,
    canonical,
    body,
    schema_json=None,
    breadcrumb_schema=None,
    extra_css="",
):
    schemas = ""
    if schema_json:
        schemas += f'<script type="application/ld+json">{json.dumps(schema_json, ensure_ascii=False)}</script>\n'
    if breadcrumb_schema:
        schemas += f'<script type="application/ld+json">{json.dumps(breadcrumb_schema, ensure_ascii=False)}</script>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<link rel="icon" type="image/svg+xml" href="{SITE_URL}/favicon.svg">
<link rel="icon" type="image/x-icon" href="{SITE_URL}/favicon.ico">
<meta name="description" content="{h(description)}">
<link rel="canonical" href="{h(canonical)}">
<meta property="og:title" content="{h(title)}">
<meta property="og:description" content="{h(description)}">
<meta property="og:url" content="{h(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Cert Atlas">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{h(title)}">
<meta name="twitter:description" content="{h(description)}">
{schemas}<style>{CSS}{extra_css}</style>
</head>
<body>
<header>
<div class="container">
<div class="site-name"><a href="{SITE_URL}/">Cert Atlas</a></div>
<nav>
<a href="{SITE_URL}/">Browse</a>
<a href="https://raw.githubusercontent.com/hans6883/cert-atlas/master/data/index.json">Download</a>
<a href="https://github.com/hans6883/cert-atlas">GitHub</a>
<a href="{QUIZFORGE_URL}">QuizForge</a>
</nav>
</div>
</header>
{body}
<footer>
<div class="container">
Data sourced from official certifying body publications.
Maintained by <a href="{QUIZFORGE_URL}">QuizForge</a> &mdash; free certification practice exams.
</div>
</footer>
</body>
</html>"""


def build_home(index, vendors, vendor_map):
    vendor_cards = []
    for v in vendors["vendors"]:
        vendor_cards.append(
            f'<a class="vendor-card" href="{SITE_URL}/{h(v["slug"])}/">'
            f'<h3>{h(v["display_name"])}</h3>'
            f'<span class="count">{v["exam_count"]} exam{"s" if v["exam_count"] != 1 else ""}</span>'
            f'</a>'
        )

    body = f"""
<div class="container">
<div class="hero">
<h1>Cert Atlas: Open Certification Exam Blueprint Index</h1>
<p>The open index of certification exam blueprints. Browse domains, objectives, and requirements for {index["total_exams"]:,} exams across {index["total_vendors"]} certifying bodies.</p>
<p style="margin-top:1rem"><strong>Download the dataset (free, MIT):</strong> <a href="https://raw.githubusercontent.com/hans6883/cert-atlas/master/data/index.json">master index (JSON)</a> &middot; <a href="https://github.com/hans6883/cert-atlas/archive/refs/heads/master.zip">full dataset (.zip)</a> &middot; <a href="https://github.com/hans6883/cert-atlas">browse on GitHub</a></p>
</div>
<div class="stats-bar">
<div class="stat"><span class="stat-num">{index["total_exams"]:,}</span><span class="stat-label">Exams</span></div>
<div class="stat"><span class="stat-num">{index["total_vendors"]}</span><span class="stat-label">Certifying Bodies</span></div>
<div class="stat"><span class="stat-num">{index["exams_with_domain_breakdowns"]:,}</span><span class="stat-label">With Blueprints</span></div>
</div>
<input type="text" class="search-box" id="vendorSearch" placeholder="Search certifying bodies..." oninput="filterVendors(this.value)">
<div class="vendor-grid" id="vendorGrid">
{"".join(vendor_cards)}
</div>
</div>
<script>
function filterVendors(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.vendor-card').forEach(c => {{
    c.style.display = c.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>"""

    return page_shell(
        "Cert Atlas -- Open Index of Certification Exam Blueprints",
        f"Browse exam blueprints for {index['total_exams']:,} certification exams across {index['total_vendors']} certifying bodies. Domains, objectives, requirements, and study resources.",
        f"{SITE_URL}/",
        body,
    )


def build_vendor_page(vendor_slug, vendor_info, exams):
    name = vendor_info["display_name"]
    exam_items = []
    for ex in sorted(exams, key=lambda e: e["exam_name"]):
        meta_parts = []
        lifecycle_status = ex.get("lifecycle_status")
        if lifecycle_status == "retired":
            retired_label = format_iso_date(ex.get("retired_on"))
            meta_parts.append(f"Retired {retired_label}".strip())
            replacement_code = str(ex.get("replacement_exam_code") or "").strip()
            if replacement_code:
                relationship = ex.get(
                    "replacement_relationship", "direct_replacement"
                )
                relationship_label = {
                    "related_successor": "related current path",
                    "collective_replacement": "broader replacement path",
                    "direct_replacement": "replaced by",
                }.get(relationship, "current path")
                meta_parts.append(f"{relationship_label} {replacement_code}")
        elif lifecycle_status == "scheduled_retirement":
            retirement_label = format_iso_date(ex.get("retires_on"))
            meta_parts.append(f"Retires {retirement_label}".strip())
            replacement_code = str(ex.get("replacement_exam_code") or "").strip()
            if replacement_code:
                relationship = ex.get(
                    "replacement_relationship", "direct_replacement"
                )
                relationship_label = {
                    "related_successor": "related future path",
                    "collective_replacement": "broader future path",
                    "direct_replacement": "will be replaced by",
                }.get(relationship, "future path")
                meta_parts.append(f"{relationship_label} {replacement_code}")
            if ex.get("total_questions"):
                meta_parts.append(f'{ex["total_questions"]} questions')
            if ex.get("duration_minutes"):
                meta_parts.append(f'{ex["duration_minutes"]} min')
            if ex.get("domains"):
                meta_parts.append(f'{ex["domains"]} domains')
        else:
            if ex.get("total_questions"):
                meta_parts.append(f'{ex["total_questions"]} questions')
            if ex.get("duration_minutes"):
                meta_parts.append(f'{ex["duration_minutes"]} min')
            if ex.get("domains"):
                meta_parts.append(f'{ex["domains"]} domains')
        meta = " | ".join(meta_parts)

        exam_items.append(
            f'<li>'
            f'<a href="{SITE_URL}/{h(vendor_slug)}/{h(ex["exam_id"])}">{h(ex["exam_name"])}</a>'
            f'{" (" + h(ex.get("exam_code", "")) + ")" if ex.get("exam_code") else ""}'
            f'<div class="meta">{h(meta)}</div>'
            f'</li>'
        )

    breadcrumb = (
        f'<div class="breadcrumb"><div class="container">'
        f'<a href="{SITE_URL}/">Home</a><span>/</span>{h(name)}'
        f'</div></div>'
    )

    body = f"""
{breadcrumb}
<div class="container">
<div class="exam-header">
<h1>{h(name)} Certification Exams</h1>
<p class="exam-code">{len(exams)} certification exam{"s" if len(exams) != 1 else ""}</p>
{f'<p class="vendor-link"><a href="{h(vendor_info.get("certification_page", vendor_info.get("website", "")))}" rel="nofollow">Official certification page</a></p>' if vendor_info.get("certification_page") else ""}
</div>
<ul class="exam-list">
{"".join(exam_items)}
</ul>
</div>"""

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": f"{SITE_URL}/{vendor_slug}/"},
        ],
    }

    return page_shell(
        (f"{name} Certification Exams -- Cert Atlas"
         if len(f"{name} Certification Exams -- Cert Atlas") <= 70
         else f"{name} Exams | Cert Atlas"),
        f"Browse exam blueprints for {len(exams)} {name} certification exams. Domains, objectives, passing scores, and study resources.",
        f"{SITE_URL}/{vendor_slug}/",
        body,
        breadcrumb_schema=breadcrumb_schema,
    )


def build_enrichment_html(exam):
    if not has_public_enrichment(exam):
        return ""

    editorial = exam.get("editorial", {})
    lifecycle = exam.get("lifecycle", {})
    lifecycle_status = lifecycle.get("status")
    retired = lifecycle_status == "retired"
    scheduled_retirement = lifecycle_status == "scheduled_retirement"
    lifecycle_notice = retired or scheduled_retirement
    sections = ['<section class="editorial" aria-label="Exam guide">']

    if lifecycle_notice:
        replacement = lifecycle.get("replacement")
        replacement = replacement if isinstance(replacement, dict) else {}
        exam_code = str(exam.get("exam_code") or exam.get("exam_name") or "This exam")
        replacement_code = str(replacement.get("exam_code") or "")
        relationship = str(replacement.get("relationship") or "direct_replacement")
        replacement_cta = {
            "related_successor": "Explore related current path",
            "collective_replacement": "Explore the broader replacement path",
        }.get(relationship, "Prepare for")
        lifecycle_date = format_iso_date(
            lifecycle.get("retired_on" if retired else "retires_on")
        )
        sections.extend(
            [
                '<div class="retirement-alert" role="note">',
                f'<p class="retirement-label">{"Retired exam" if retired else "Scheduled retirement"}</p>',
                (
                    f'<h2>{h(exam_code)} was retired on {h(lifecycle_date)}</h2>'
                    if retired
                    else f'<h2>{h(exam_code)} retires on {h(lifecycle_date)}</h2>'
                ),
                f'<p>{h(lifecycle.get("summary") or "")}</p>',
            ]
        )
        if replacement:
            sections.append(
                f'<a class="replacement-link" href="{h(replacement.get("url") or "")}" rel="nofollow">'
                f'{h(replacement_cta)} {h(replacement_code)}: '
                f'{h(replacement.get("name") or "current path")}</a>'
            )
        else:
            sections.append(
                '<p class="lifecycle-no-replacement">'
                'No direct replacement is named in the reviewed official sources.</p>'
            )
        sections.append("</div>")

        if retired:
            sections.extend(
                [
                    f'<h2>Historical {h(exam_code)} Scope</h2><p>{h(editorial.get("overview", ""))}</p>',
                    f'<h2>Who {h(exam_code)} Was For</h2><p>{h(editorial.get("who_should_take", ""))}</p>',
                ]
            )
        else:
            sections.extend(
                [
                    f'<h2>What This Exam Validates</h2><p>{h(editorial.get("overview", ""))}</p>',
                    f'<h2>Who Should Take This Exam</h2><p>{h(editorial.get("who_should_take", ""))}</p>',
                ]
            )
    else:
        sections.extend(
            [
                f'<h2>What This Exam Validates</h2><p>{h(editorial.get("overview", ""))}</p>',
                f'<h2>Who Should Take This Exam</h2><p>{h(editorial.get("who_should_take", ""))}</p>',
            ]
        )

    skills = [
        str(item).strip()
        for item in editorial.get("skills_summary", [])
        if str(item).strip()
    ]
    if skills:
        sections.append(
            '<h2>Skills You Should Be Ready to Demonstrate</h2><ul>'
            + "".join(f"<li>{h(item)}</li>" for item in skills)
            + "</ul>"
        )

    preparation_heading = (
        "How to Reuse Your Preparation"
        if retired
        else "How to Prepare Before Retirement"
        if scheduled_retirement
        else "How to Prepare"
    )
    sections.append(
        f'<h2>{preparation_heading}</h2><p>{h(editorial.get("preparation_strategy", ""))}</p>'
    )

    if lifecycle_notice:
        replacement = lifecycle.get("replacement")
        replacement = replacement if isinstance(replacement, dict) else {}
        exam_code = str(exam.get("exam_code") or "the retiring exam")
        replacement_code = str(replacement.get("exam_code") or "")
        relationship = str(replacement.get("relationship") or "direct_replacement")
        comparisons = [
            item
            for item in lifecycle.get("skill_comparison", [])
            if isinstance(item, dict)
        ]
        if comparisons and replacement_code:
            comparison_heading = (
                f"How {exam_code} skills compare with {replacement_code}"
                if relationship == "related_successor"
                else f"What changed from {exam_code} to {replacement_code}"
            )
            sections.append(
                f'<div class="migration-map"><h2>{h(comparison_heading)}</h2>'
            )
            rows = "".join(
                "<tr>"
                f'<td>{h(item.get("legacy_skill"))}<br><strong>{h(item.get("legacy_weight"))}</strong></td>'
                f'<td>{h(item.get("replacement_skill"))}<br><strong>{h(item.get("replacement_weight"))}</strong></td>'
                f'<td>{h(item.get("change"))}</td>'
                "</tr>"
                for item in comparisons
            )
            sections.append(
                '<div class="comparison-wrap"><table class="comparison-table">'
                f'<thead><tr><th>{"Historical" if retired else "Current"} {h(exam_code)}</th>'
                f'<th>Current {h(replacement_code)}</th><th>Practical impact</th></tr></thead>'
                f'<tbody>{rows}</tbody></table></div></div>'
            )

        actions = [
            str(item).strip()
            for item in lifecycle.get("migration_actions", [])
            if str(item).strip()
        ]
        if actions:
            sections.append(
                '<div class="migration-map">'
                f'<h3>{"Migration" if retired else "Transition"} checklist</h3><ol>'
                + "".join(f"<li>{h(item)}</li>" for item in actions)
                + "</ol></div>"
            )

        study_guide_url = h(replacement.get("study_guide_url") or "")
        if study_guide_url:
            sections.append(
                f'<p><a href="{study_guide_url}" rel="nofollow">'
                f'Open the official {h(replacement_code)} study guide</a></p>'
            )

    domain_names = {
        str(domain.get("id")): str(domain.get("name") or "")
        for domain in exam.get("domains", [])
        if isinstance(domain, dict)
    }
    guidance = editorial.get("domain_guidance", [])
    if guidance:
        sections.append(
            "<h2>Historical Domain Guide</h2>"
            if retired
            else "<h2>Domain Study Guidance</h2>"
        )
        for item in guidance:
            if not isinstance(item, dict):
                continue
            domain_id = str(item.get("domain_id") or "")
            label = domain_names.get(domain_id) or f"Domain {domain_id}"
            suffix = "Historical Scope" if retired else "Study Guidance"
            sections.append(f"<h3>{h(label)}: {suffix}</h3>")
            sections.append(f'<p>{h(item.get("summary", ""))}</p>')
            focus = [
                str(value).strip()
                for value in item.get("study_focus", [])
                if str(value).strip()
            ]
            if focus:
                sections.append(
                    "<ul>"
                    + "".join(f"<li>{h(value)}</li>" for value in focus)
                    + "</ul>"
                )

    exam_day = str(editorial.get("exam_day_guidance") or "").strip()
    if exam_day and not retired:
        sections.append(f"<h2>Exam-Day Guidance</h2><p>{h(exam_day)}</p>")

    signals = exam.get("study_signals")
    if isinstance(signals, dict) and not retired:
        signal_items = []
        for item in signals.get("topic_emphasis", []):
            if isinstance(item, dict) and item.get("topic"):
                details = []
                if item.get("level"):
                    details.append(str(item["level"]))
                if item.get("share_percent") is not None:
                    details.append(f'{item["share_percent"]}% of practice metadata')
                suffix = f' ({", ".join(details)})' if details else ""
                signal_items.append(f'{item.get("topic")}{suffix}')
        signal_items.extend(
            str(item)
            for item in signals.get("challenge_areas", [])
            if str(item).strip()
        )
        signal_items.extend(
            str(item)
            for item in signals.get("question_style_observations", [])
            if str(item).strip()
        )
        if signal_items:
            sections.append(
                '<div class="study-signals"><h2>Preparation Signals</h2>'
            )
            sections.append(
                '<p class="signal-note">Derived from aggregate practice patterns. '
                'These are study aids, not official exam weights or predictions.</p>'
            )
            sections.append(
                "<ul>"
                + "".join(f"<li>{h(item)}</li>" for item in signal_items)
                + "</ul></div>"
            )

    sources = exam.get("sources", [])
    quality = exam.get("content_quality", {})
    if sources:
        reviewed_at = str(quality.get("reviewed_at") or "")[:10]
        sections.append('<div class="verification"><h2>Sources and Verification</h2>')
        if reviewed_at:
            sections.append(
                f'<p class="verification-date">Verified {h(reviewed_at)}</p>'
            )
        source_items = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            title = h(source.get("title") or "Official source")
            url = h(source.get("url") or "")
            publisher = h(source.get("publisher") or "")
            link = f'<a href="{url}" rel="nofollow">{title}</a>' if url else title
            accessed = h(source.get("accessed") or "")
            suffix = (
                f' <span class="source-publisher">{publisher}</span>'
                if publisher
                else ""
            )
            if accessed:
                suffix += (
                    f' <span class="source-accessed">accessed {accessed}</span>'
                )
            source_items.append(f"<li>{link}{suffix}</li>")
        sections.append(
            '<ul class="source-list">' + "".join(source_items) + "</ul></div>"
        )

    methodology = editorial.get("methodology")
    if isinstance(methodology, dict) and methodology.get("summary"):
        sections.append(
            '<div class="methodology"><h2>How this page was made</h2>'
            f'<p>{h(methodology.get("summary"))}</p></div>'
        )

    sections.append("</section>")
    return "".join(sections)

def build_exam_page(vendor_slug, vendor_info, exam):
    name = exam.get("exam_name", "")
    code = exam.get("exam_code", "")
    body_name = exam.get("certifying_body", vendor_info.get("display_name", ""))
    exam_id = exam.get("exam_id", "")
    lifecycle = exam.get("lifecycle", {})
    retired = lifecycle.get("status") == "retired"
    scheduled_retirement = lifecycle.get("status") == "scheduled_retirement"

    # Quick facts
    facts = []
    if exam.get("total_questions"):
        facts.append(("Questions", str(exam["total_questions"])))
    if exam.get("duration_minutes"):
        facts.append(("Duration", f'{exam["duration_minutes"]} min'))
    if exam.get("passing_score"):
        scale = f'/{exam["passing_score_scale"]}' if exam.get("passing_score_scale") else ""
        facts.append(("Passing Score", f'{exam["passing_score"]}{scale}'))
    if exam.get("exam_price_usd"):
        facts.append(("Price", f'${exam["exam_price_usd"]:.0f}'))
    if exam.get("certification_validity_years"):
        facts.append(("Valid For", f'{exam["certification_validity_years"]} years'))
    if exam.get("available_languages"):
        facts.append(("Languages", str(len(exam["available_languages"]))))
    if retired:
        facts = []

    facts_html = "".join(
        f'<div class="fact"><span class="fact-value">{h(v)}</span><span class="fact-label">{h(l)}</span></div>'
        for l, v in facts
    )

    # Domains
    domains_html = ""
    domains = exam.get("domains", [])
    if domains:
        domain_blocks = []
        for dom in domains:
            weight = dom.get("weight_percent") or 0
            weight_min = dom.get("weight_min_percent")
            weight_max = dom.get("weight_max_percent")
            objectives_html = ""
            if dom.get("objectives"):
                obj_items = []
                for obj in dom["objectives"]:
                    if isinstance(obj, str):
                        obj_id = ""
                        obj_title = obj
                        sub_objectives = []
                    elif isinstance(obj, dict):
                        obj_id = obj.get("id", "")
                        obj_title = obj.get("title", "")
                        sub_objectives = obj.get("sub_objectives") or []
                    else:
                        continue
                    sub = ""
                    if sub_objectives:
                        normalized_sub_objectives = [
                            item.get("title", "") if isinstance(item, dict) else str(item)
                            for item in sub_objectives
                        ]
                        sub = f'<div class="sub-objectives">{h("; ".join(normalized_sub_objectives))}</div>'
                    obj_items.append(
                        f'<li><span class="obj-id">{h(obj_id)}</span>{h(obj_title)}{sub}</li>'
                    )
                objectives_html = f'<ul class="objectives">{"".join(obj_items)}</ul>'

            if weight_min is not None and weight_max is not None:
                if float(weight_min) == float(weight_max):
                    weight_label = f"{float(weight_min):.0f}%"
                else:
                    weight_label = f"{float(weight_min):.0f}-{float(weight_max):.0f}%"
                weight_html = f'<span class="domain-weight">{weight_label}</span>'
                bar_width = (float(weight_min) + float(weight_max)) / 2
                bar_html = f'<div class="domain-bar"><div class="domain-bar-fill" style="width:{bar_width}%"></div></div>'
            elif weight > 0:
                weight_html = f'<span class="domain-weight">{weight:.0f}%</span>'
                bar_html = f'<div class="domain-bar"><div class="domain-bar-fill" style="width:{weight}%"></div></div>'
            else:
                weight_html = '<span class="domain-weight weight-na">Weight not published</span>'
                bar_html = ''

            domain_blocks.append(f"""
<div class="domain">
<div class="domain-header">
<span class="domain-name">{h(dom.get("id", ""))} {h(dom.get("name", ""))}</span>
{weight_html}
</div>
{bar_html}
{objectives_html}
</div>""")

        domains_heading = f'Historical {h(code)} Domains' if retired and code else "Exam Domains"
        domains_html = f'<section class="domains"><h3>{domains_heading}</h3>{"".join(domain_blocks)}</section>'

    # Info section
    info_rows = []
    if exam.get("question_types"):
        info_rows.append(("Question Types", ", ".join(exam["question_types"])))
    if exam.get("exam_format"):
        info_rows.append(("Format", exam["exam_format"]))
    if exam.get("online_proctoring_available") is not None:
        info_rows.append(("Online Proctoring", "Available" if exam["online_proctoring_available"] else "Not available"))
    if exam.get("id_requirements"):
        info_rows.append(("ID Requirements", exam["id_requirements"]))
    if exam.get("renewal_required") is not None:
        renewal = "Required" if exam["renewal_required"] else "Not required"
        if exam.get("renewal_options"):
            renewal += f' -- {exam["renewal_options"]}'
        info_rows.append(("Renewal", renewal))
    if exam.get("prerequisites"):
        prereqs = []
        for p in exam["prerequisites"]:
            desc = p.get("description", "")
            req = " (recommended)" if not p.get("is_required", True) else ""
            prereqs.append(f"{desc}{req}")
        if prereqs:
            info_rows.append(("Prerequisites", "; ".join(prereqs)))
    if exam.get("retake_policy") and exam["retake_policy"].get("notes"):
        info_rows.append(("Retake Policy", exam["retake_policy"]["notes"]))
    if exam.get("available_languages"):
        info_rows.append(("Languages", ", ".join(exam["available_languages"])))

    info_html = ""
    if info_rows and not retired:
        rows = "".join(
            f'<div class="info-row"><span class="info-label">{h(l)}</span><span class="info-value">{h(v)}</span></div>'
            for l, v in info_rows
        )
        info_heading = "Historical Exam Details" if retired else "Exam Details"
        info_html = f'<section class="info"><h3>{info_heading}</h3><div class="info-grid">{rows}</div></section>'

    # Resources
    resources_html = ""
    resources = exam.get("official_study_resources", [])
    if resources and not retired:
        items = []
        for r in resources:
            rtype = r.get("resource_type", "").replace("_", " ")
            title = r.get("title", "")
            url = r.get("url", "")
            price = f' (${r["price_usd"]:.0f})' if r.get("price_usd") else " (free)" if r.get("price_usd") == 0 else ""
            link = f'<a href="{h(url)}" rel="nofollow">{h(title)}</a>' if url else h(title)
            items.append(f'<div class="resource-item"><span class="resource-type">{h(rtype)}</span>{link}{h(price)}</div>')
        resources_html = f'<section class="info"><h3>Official Study Resources</h3><div class="resources">{"".join(items)}</div></section>'

    # Registration links
    reg_html = ""
    reg_parts = []
    if exam.get("exam_registration_url") and not retired:
        reg_parts.append(f'<a href="{h(exam["exam_registration_url"])}" rel="nofollow">Register for this exam</a>')
    if exam.get("official_objectives_url"):
        reg_parts.append(f'<a href="{h(exam["official_objectives_url"])}" rel="nofollow">Official exam guide</a>')
    if exam.get("source_url") and exam["source_url"] != exam.get("official_objectives_url"):
        reg_parts.append(f'<a href="{h(exam["source_url"])}" rel="nofollow">Source</a>')
    if reg_parts:
        reg_html = f'<div class="source-link">{" | ".join(reg_parts)}</div>'

    # Practice CTA
    practice_url = exam.get("practice_url", f"{QUIZFORGE_URL}/tests/{exam_id}")
    practice_html = "" if retired else f'<a class="practice-cta" href="{h(practice_url)}">Practice {h(name)} on QuizForge</a>'
    enrichment_html = build_enrichment_html(exam)
    enrichment_line = f"\n{enrichment_html}" if enrichment_html else ""
    pre_facts_content = enrichment_line if retired else ""
    post_facts_content = "" if retired else f"{practice_html}{enrichment_line}"
    facts_heading = f'<h2>Historical {h(code)} Exam Facts</h2>' if retired and facts_html else ""
    if facts_heading:
        pre_facts_content += f"\n{facts_heading}"

    breadcrumb = (
        f'<div class="breadcrumb"><div class="container">'
        f'<a href="{SITE_URL}/">Home</a><span>/</span>'
        f'<a href="{SITE_URL}/{h(vendor_slug)}/">{h(body_name)}</a><span>/</span>'
        f'{h(name)}'
        f'</div></div>'
    )

    if retired and code:
        replacement = lifecycle.get("replacement")
        page_heading = (
            f"{h(code)} Retired: What Replaced It and What Carries Over"
            if isinstance(replacement, dict) and replacement.get("exam_code")
            else f"{h(code)} Retired: Historical Blueprint and Next Steps"
        )
    elif scheduled_retirement and code:
        retirement_date = format_iso_date(lifecycle.get("retires_on"))
        page_heading = f"{h(code)} Retires {h(retirement_date)}: Transition Guide"
    else:
        page_heading = h(name) + (f' ({h(code)})' if code else '') + " Exam Blueprint"

    body = f"""
{breadcrumb}
<div class="container">
<div class="exam-header">
<h1>{page_heading}</h1>
{f'<p class="exam-code">{h(code)}</p>' if code else ""}
<p class="vendor-link"><a href="{SITE_URL}/{h(vendor_slug)}/">{h(body_name)}</a></p>
</div>{pre_facts_content}
<div class="quick-facts">{facts_html}</div>
{post_facts_content}
{domains_html}
{info_html}
{resources_html}
{reg_html}
</div>"""

    # Structured data
    course_schema = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": name,
        "description": f"Exam blueprint for {name}{f' ({code})' if code else ''} by {body_name}. {len(domains)} domains, {exam.get('total_questions', 'N/A')} questions, {exam.get('duration_minutes', 'N/A')} minutes.",
        "provider": {
            "@type": "Organization",
            "name": body_name,
        },
        "hasCourseInstance": {
            "@type": "CourseInstance",
            "courseMode": "Online" if exam.get("online_proctoring_available") else "InPerson",
        },
    }
    if exam.get("available_languages"):
        course_schema["inLanguage"] = exam["available_languages"][0] if len(exam["available_languages"]) == 1 else exam["available_languages"]
    if has_public_enrichment(exam):
        overview = str(exam.get("editorial", {}).get("overview") or "").strip()
        if overview:
            course_schema["description"] = overview
        reviewed_at = str(exam.get("content_quality", {}).get("reviewed_at") or "")[:10]
        if reviewed_at:
            course_schema["dateModified"] = reviewed_at
    if retired:
        replacement = lifecycle.get("replacement", {})
        course_schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": f"{code} retired exam migration guide",
            "description": str(lifecycle.get("summary") or ""),
            "dateModified": str(exam.get("content_quality", {}).get("reviewed_at") or "")[:10],
            "about": {
                "@type": "EducationalOccupationalCredential",
                "name": name,
                "credentialCategory": "Retired certification exam",
                "recognizedBy": {"@type": "Organization", "name": body_name},
            },
        }
        if isinstance(replacement, dict) and replacement.get("url"):
            course_schema["significantLink"] = replacement["url"]

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{SITE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": body_name, "item": f"{SITE_URL}/{vendor_slug}/"},
            {"@type": "ListItem", "position": 3, "name": name, "item": f"{SITE_URL}/{vendor_slug}/{exam_id}"},
        ],
    }

    desc = f"{name}"
    if code:
        desc += f" ({code})"
    desc += f" exam blueprint. "
    desc_parts = []
    if exam.get("total_questions"):
        desc_parts.append(f'{exam["total_questions"]} questions')
    if exam.get("duration_minutes"):
        desc_parts.append(f'{exam["duration_minutes"]} minutes')
    if exam.get("passing_score"):
        desc_parts.append(f'passing score {exam["passing_score"]}')
    if desc_parts:
        desc += ", ".join(desc_parts) + ". "
    if domains:
        desc += f'{len(domains)} domains with objectives and topic weights.'
    if has_public_enrichment(exam):
        editorial = exam.get("editorial", {})
        meta_description = str(editorial.get("meta_description") or "").strip()
        overview = str(editorial.get("overview") or "").strip()
        if meta_description or overview:
            desc = meta_description or overview

    # Bing "Title too long" (>70 chars): never repeat a code the name already carries,
    # and drop the body / brand segments before the exam name would be cut.
    exam_label = name if (not code or f"({code})" in name) else f"{name} ({code})"
    page_title = next(
        (t for t in (
            f"{exam_label} Exam Blueprint - {body_name} | Cert Atlas",
            f"{exam_label} Exam Blueprint | Cert Atlas",
            f"{name} Exam Blueprint | Cert Atlas",
            f"{name} Exam Blueprint",
        ) if len(t) <= 70),
        None,
    )
    if page_title is None:
        # Long name: cut it at a word boundary; the full name still lives in the h1.
        cut = name[:55]
        if " " in cut[20:]:
            cut = cut[:cut.rfind(" ")]
        page_title = f"{cut.rstrip(' -:,(–')} Exam Blueprint"
    if retired:
        replacement = lifecycle.get("replacement", {})
        if isinstance(replacement, dict) and replacement.get("exam_code"):
            replacement_code = replacement["exam_code"]
            relationship = replacement.get("relationship") or "direct_replacement"
            relation_label = "Related Path" if relationship == "related_successor" else "Replacement"
            page_title = f"{code or name} Retired: {replacement_code} {relation_label} & Skill Map | Cert Atlas"
        else:
            page_title = f"{code or name} Retired: Blueprint & Next Steps | Cert Atlas"
    elif scheduled_retirement:
        retirement_value = str(lifecycle.get("retires_on") or "")
        try:
            retirement_short = datetime.strptime(
                retirement_value, "%Y-%m-%d"
            ).strftime("%b %d").replace(" 0", " ")
        except ValueError:
            retirement_short = retirement_value
        replacement = lifecycle.get("replacement", {})
        replacement_code = (
            replacement.get("exam_code")
            if isinstance(replacement, dict)
            else None
        )
        transition_label = (
            f"{replacement_code} Replacement"
            if replacement_code
            else "Transition Guide"
        )
        page_title = (
            f"{code or name} Retires {retirement_short}: "
            f"{transition_label} | Cert Atlas"
        )
    elif has_public_enrichment(exam):
        page_title = f"{code or name} Exam Guide, Domains & Skills | Cert Atlas"

    return page_shell(
        page_title,
        desc[:160],
        f"{SITE_URL}/{vendor_slug}/{exam_id}",
        body,
        schema_json=course_schema,
        breadcrumb_schema=breadcrumb_schema,
        extra_css=ENRICHMENT_CSS if has_public_enrichment(exam) else "",
    )


def build_sitemap(index, exams_by_vendor):
    urls = [f'<url><loc>{SITE_URL}/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>']

    for vendor_slug in sorted(exams_by_vendor.keys()):
        urls.append(f'<url><loc>{SITE_URL}/{vendor_slug}/</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>')
        for ex in exams_by_vendor[vendor_slug]:
            urls.append(f'<url><loc>{SITE_URL}/{vendor_slug}/{ex["exam_id"]}</loc><changefreq>monthly</changefreq><priority>0.9</priority></url>')

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{"".join(urls)}
</urlset>"""


def build():
    index, vendors, exams_by_vendor, vendor_map = load_data()

    # Clean docs dir
    if DOCS_DIR.exists():
        import shutil
        shutil.rmtree(DOCS_DIR)
    DOCS_DIR.mkdir(parents=True)

    # Copy static assets (favicons)
    import shutil as _shutil
    for asset in ["favicon.ico", "favicon.svg"]:
        src = REPO_ROOT / asset
        if not src.exists():
            src = REPO_ROOT / "docs" / asset  # might survive rmtree if pre-copied
        # Copy from repo root if available
        asset_src = REPO_ROOT / asset
        if asset_src.exists():
            _shutil.copy2(asset_src, DOCS_DIR / asset)

    # Home page
    with open(DOCS_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(build_home(index, vendors, vendor_map))

    # Vendor pages + exam pages
    page_count = 1
    for vendor_slug, exams in exams_by_vendor.items():
        vendor_info = vendor_map.get(vendor_slug, {"display_name": vendor_slug, "website": "", "certification_page": ""})
        vendor_dir = DOCS_DIR / vendor_slug
        vendor_dir.mkdir(parents=True, exist_ok=True)

        with open(vendor_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(build_vendor_page(vendor_slug, vendor_info, exams))
        page_count += 1

        for ex_entry in exams:
            exam_data = load_exam(vendor_slug, ex_entry["exam_id"])
            with open(vendor_dir / f'{ex_entry["exam_id"]}.html', "w", encoding="utf-8") as f:
                f.write(build_exam_page(vendor_slug, vendor_info, exam_data))
            page_count += 1

    # Sitemap
    with open(DOCS_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(build_sitemap(index, exams_by_vendor))

    # Robots
    with open(DOCS_DIR / "robots.txt", "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    # CNAME placeholder
    with open(DOCS_DIR / "CNAME", "w", encoding="utf-8") as f:
        f.write("atlas.quizforge.ai\n")

    print(f"Built {page_count:,} pages in {DOCS_DIR}")
    print(f"  {len(exams_by_vendor)} vendor pages")
    print(f"  {sum(len(v) for v in exams_by_vendor.values()):,} exam pages")


if __name__ == "__main__":
    build()
