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
header h1 { font-size: 20px; font-weight: 700; }
header h1 a { color: var(--text); }
header nav a { margin-left: 24px; font-size: 14px; color: var(--text-muted); }
header nav a:hover { color: var(--accent); text-decoration: none; }

.hero { padding: 48px 0 32px; }
.hero h2 { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
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
.exam-header h2 { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
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
  .hero h2 { font-size: 24px; }
  .stats-bar { gap: 16px; flex-wrap: wrap; }
  .quick-facts { grid-template-columns: repeat(2, 1fr); }
  .info-row { flex-direction: column; gap: 2px; }
  .info-label { min-width: auto; }
}
"""


def page_shell(title, description, canonical, body, schema_json=None, breadcrumb_schema=None):
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
{schemas}<style>{CSS}</style>
</head>
<body>
<header>
<div class="container">
<h1><a href="{SITE_URL}/">Cert Atlas</a></h1>
<nav>
<a href="{SITE_URL}/">Browse</a>
<a href="https://github.com/quizforge/cert-atlas">GitHub</a>
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
<h2>Cert Atlas</h2>
<p>The open index of certification exam blueprints. Browse domains, objectives, and requirements for {index["total_exams"]:,} exams across {index["total_vendors"]} certifying bodies.</p>
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
<h2>{h(name)}</h2>
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
        f"{name} Certification Exams -- Cert Atlas",
        f"Browse exam blueprints for {len(exams)} {name} certification exams. Domains, objectives, passing scores, and study resources.",
        f"{SITE_URL}/{vendor_slug}/",
        body,
        breadcrumb_schema=breadcrumb_schema,
    )


def build_exam_page(vendor_slug, vendor_info, exam):
    name = exam.get("exam_name", "")
    code = exam.get("exam_code", "")
    body_name = exam.get("certifying_body", vendor_info.get("display_name", ""))
    exam_id = exam.get("exam_id", "")

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
            objectives_html = ""
            if dom.get("objectives"):
                obj_items = []
                for obj in dom["objectives"]:
                    sub = ""
                    if obj.get("sub_objectives"):
                        sub = f'<div class="sub-objectives">{h("; ".join(obj["sub_objectives"]))}</div>'
                    obj_items.append(
                        f'<li><span class="obj-id">{h(obj.get("id", ""))}</span>{h(obj.get("title", ""))}{sub}</li>'
                    )
                objectives_html = f'<ul class="objectives">{"".join(obj_items)}</ul>'

            domain_blocks.append(f"""
<div class="domain">
<div class="domain-header">
<span class="domain-name">{h(dom.get("id", ""))} {h(dom.get("name", ""))}</span>
<span class="domain-weight">{weight:.0f}%</span>
</div>
<div class="domain-bar"><div class="domain-bar-fill" style="width:{weight}%"></div></div>
{objectives_html}
</div>""")

        domains_html = f'<section class="domains"><h3>Exam Domains</h3>{"".join(domain_blocks)}</section>'

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
    if info_rows:
        rows = "".join(
            f'<div class="info-row"><span class="info-label">{h(l)}</span><span class="info-value">{h(v)}</span></div>'
            for l, v in info_rows
        )
        info_html = f'<section class="info"><h3>Exam Details</h3><div class="info-grid">{rows}</div></section>'

    # Resources
    resources_html = ""
    resources = exam.get("official_study_resources", [])
    if resources:
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
    if exam.get("exam_registration_url"):
        reg_parts.append(f'<a href="{h(exam["exam_registration_url"])}" rel="nofollow">Register for this exam</a>')
    if exam.get("official_objectives_url"):
        reg_parts.append(f'<a href="{h(exam["official_objectives_url"])}" rel="nofollow">Official exam guide</a>')
    if exam.get("source_url") and exam["source_url"] != exam.get("official_objectives_url"):
        reg_parts.append(f'<a href="{h(exam["source_url"])}" rel="nofollow">Source</a>')
    if reg_parts:
        reg_html = f'<div class="source-link">{" | ".join(reg_parts)}</div>'

    # Practice CTA
    practice_url = exam.get("practice_url", f"{QUIZFORGE_URL}/tests/{exam_id}")
    practice_html = f'<a class="practice-cta" href="{h(practice_url)}">Practice {h(name)} on QuizForge</a>'

    breadcrumb = (
        f'<div class="breadcrumb"><div class="container">'
        f'<a href="{SITE_URL}/">Home</a><span>/</span>'
        f'<a href="{SITE_URL}/{h(vendor_slug)}/">{h(body_name)}</a><span>/</span>'
        f'{h(name)}'
        f'</div></div>'
    )

    body = f"""
{breadcrumb}
<div class="container">
<div class="exam-header">
<h2>{h(name)}</h2>
{f'<p class="exam-code">{h(code)}</p>' if code else ""}
<p class="vendor-link"><a href="{SITE_URL}/{h(vendor_slug)}/">{h(body_name)}</a></p>
</div>
<div class="quick-facts">{facts_html}</div>
{practice_html}
{domains_html}
{info_html}
{resources_html}
{reg_html}
</div>"""

    # Course schema
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

    return page_shell(
        f"{name}{f' ({code})' if code else ''} Exam Blueprint -- Cert Atlas",
        desc[:160],
        f"{SITE_URL}/{vendor_slug}/{exam_id}",
        body,
        schema_json=course_schema,
        breadcrumb_schema=breadcrumb_schema,
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
        f.write("certatlas.org\n")

    print(f"Built {page_count:,} pages in {DOCS_DIR}")
    print(f"  {len(exams_by_vendor)} vendor pages")
    print(f"  {sum(len(v) for v in exams_by_vendor.values()):,} exam pages")


if __name__ == "__main__":
    build()
