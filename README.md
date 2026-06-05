# Cert Atlas

**The open index of certification exam blueprints.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Exams](https://img.shields.io/badge/exams-1%2C562-2563eb.svg)
![Certifying bodies](https://img.shields.io/badge/certifying%20bodies-217-3b82f6.svg)
![Format](https://img.shields.io/badge/format-JSON-success.svg)
[![Browse online](https://img.shields.io/badge/browse-atlas.quizforge.ai-1d4ed8.svg)](https://atlas.quizforge.ai)

1,562 exams. 217 certifying bodies. Structured, machine-readable JSON sourced from official exam guides and certification pages.

🔎 **Browse:** [atlas.quizforge.ai](https://atlas.quizforge.ai) &nbsp;·&nbsp; 📦 **Use:** [`data/index.json`](data/index.json) &nbsp;·&nbsp; 📋 **Data Package:** [`datapackage.json`](datapackage.json) &nbsp;·&nbsp; 🤖 **For LLMs:** [`llms.txt`](https://atlas.quizforge.ai/llms.txt)

Whether you're building a study app, planning your next certification, or researching exam requirements -- this is the most complete open dataset of exam blueprints available.

## What's inside

Every exam file includes the structural blueprint published by the certifying body:

- Exam domains, objectives, and topic weights
- Passing scores, question counts, and time limits
- Pricing, registration links, and testing center info
- Prerequisites, retake policies, and renewal requirements
- Available languages and proctoring options
- Official study resources and objective URLs

No proprietary questions. No scraped content. Just the publicly available exam structure, consolidated and normalized.

## Quick start

Browse by vendor:

```
data/
  aws/
    aws-cloud-practitioner-clf-c02.json
    aws-solutions-architect-associate-saa-c03.json
    ...
  microsoft/
    microsoft-az-104.json
    microsoft-az-900.json
    ...
  comptia/
    comptia-security-plus-sy0-701.json
    comptia-a-plus-core1-220-1101.json
    ...
```

Or use the master index:

```bash
# All exams
cat data/index.json | jq '.exams | length'
# 1562

# All AWS exams
cat data/index.json | jq '[.exams[] | select(.certifying_body == "AWS")]'

# Exams with 4+ domains
cat data/index.json | jq '[.exams[] | select(.domains >= 4)]'
```

## Coverage

| Certifying Body | Exams |
|-----------------|-------|
| DMV / State Driver Licensing | 51 |
| Microsoft | 45 |
| College Board | 44 |
| DSST | 38 |
| CLEP | 34 |
| Salesforce | 32 |
| NCEES | 29 |
| ServiceNow | 27 |
| FINRA | 26 |
| SAP | 20 |
| AAPC | 20 |
| Oracle | 19 |
| CompTIA | 16 |
| Google Cloud | 16 |
| AWS | 15 |
| PeopleCert (AXELOS) | 15 |
| *...and 201 more* | |

Full vendor directory: [`data/vendors.json`](data/vendors.json)

**Data completeness across all 1,562 exams:**

| Field | Coverage |
|-------|----------|
| Domain breakdowns | 95% (1,477) |
| Passing score | 73% (1,132) |
| Duration | 82% (1,279) |
| Pricing | 87% (1,357) |
| Sample questions | not included (see below) |

## Schema

Each exam file follows this structure:

```jsonc
{
  "exam_id": "comptia-security-plus-sy0-701",
  "exam_name": "CompTIA Security+",
  "exam_code": "SY0-701",
  "certifying_body": "CompTIA",
  "source_url": "https://www.comptia.org/certifications/security",

  // Exam logistics
  "passing_score": 750,
  "passing_score_scale": "100-900",
  "total_questions": 90,
  "duration_minutes": 90,
  "exam_price_usd": 404.00,
  "question_types": ["Multiple Choice", "Performance-Based"],

  // The blueprint
  "domains": [
    {
      "id": "1.0",
      "name": "General security concepts",
      "weight_percent": 12.0,
      "objectives": [
        {
          "id": "1.1",
          "title": "Security controls",
          "sub_objectives": ["comparing technical, preventive, ..."]
        }
      ]
    }
  ],

  // Registration and policies
  "prerequisites": [...],
  "retake_policy": { "waiting_period_days": 14, ... },
  "testing_centers": [...],
  "online_proctoring_available": true,
  "certification_validity_years": 3,
  "renewal_required": true,
  "available_languages": ["English", "Japanese", ...],

  // Resources
  "official_objectives_url": "https://...",
  "official_study_resources": [...],

  // Aliases for lookup
  "aliases": ["security+", "sy0-701", "sec+", ...],

  // Practice
  "practice_url": "https://quizforge.ai/tests/comptia-security-plus-sy0-701"
}
```

## Use cases

**Building a study app?** Use `data/index.json` to list exams and `domains` to build topic-based study plans.

**Comparing certifications?** Pull `duration_minutes`, `exam_price_usd`, `total_questions`, and `passing_score` across vendors.

**Tracking your certification path?** Use `prerequisites` to map out dependencies between exams.

**Researching exam difficulty?** Cross-reference `passing_score`, `total_questions`, and `duration_minutes`.

**Grounding an AI assistant or agent?** Cert Atlas is clean, factual, source-linked structured data — ideal for RAG / grounding so an LLM can accurately answer "what does the AWS Solutions Architect exam cover?", "what are the CISSP prerequisites?", or "how is CompTIA Security+ weighted by domain?" The site ships an [`llms.txt`](https://atlas.quizforge.ai/llms.txt) manifest, and each index entry carries a `practice_url` to a matching practice exam.

## MCP server

Want agents to query Cert Atlas **directly**, in context? The [`mcp/`](mcp/) directory ships a [Model Context Protocol](https://modelcontextprotocol.io) server — `cert-atlas-mcp` — that exposes the dataset to Claude, Cursor, and any MCP client. Read-only, no API key.

| Tool | What it does |
|------|--------------|
| `search_exams` | Keyword search across all 1,562 blueprints, optional body/vendor filter |
| `get_exam_blueprint` | Full blueprint for one exam: domains + weights, scoring, prerequisites, renewal |
| `compare_exams` | Compare 2–8 exams side by side (questions, duration, passing score, price, validity) |
| `list_certifying_bodies` | All 217 certifying bodies with exam counts |

```bash
cd mcp && npm install && npm run build
```

It reads the local `data/` JSON when run from this repo, or fetches the published dataset from GitHub when installed standalone — so it's always in sync. See [`mcp/README.md`](mcp/README.md) for setup.

## How this data was collected

Each blueprint was sourced from the certifying body's official exam guide, certification page, or published PDF. The `source_url` field in every exam file links to the original source. No third-party question banks or proprietary content were used.

Data was collected and structured by [QuizForge](https://quizforge.ai), a certification exam prep platform.

## Contributing

Found an outdated exam or missing certification? Contributions welcome.

- **Update an exam:** Edit the JSON file and submit a PR with a link to the updated official source.
- **Add a new exam:** Create a JSON file following the schema above. Include the `source_url`.
- **Report an issue:** Open an issue with the exam name and what needs correcting.

Please include the official source URL for any additions or changes.

## License

This dataset is released under the [MIT License](LICENSE). The exam blueprints themselves are factual information published by their respective certifying bodies. This project consolidates and structures that information for programmatic use.

## Browse online

[atlas.quizforge.ai](https://atlas.quizforge.ai) -- searchable, rendered exam blueprints with domain breakdowns and study resources.

## Acknowledgments

Maintained by [QuizForge](https://quizforge.ai) -- free certification practice exams for 1,500+ exams.
