# Cert Atlas

**The open index of certification exam blueprints.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Exams](https://img.shields.io/badge/exams-1%2C673-2563eb.svg)
![Certifying bodies](https://img.shields.io/badge/certifying%20bodies-223-3b82f6.svg)
![Format](https://img.shields.io/badge/format-JSON-success.svg)
[![Browse online](https://img.shields.io/badge/browse-atlas.quizforge.ai-1d4ed8.svg)](https://atlas.quizforge.ai)

1,673 exams. 223 certifying bodies. Structured, machine-readable JSON sourced from official exam guides and certification pages.

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
- Reviewed, source-linked editorial guidance where the enrichment quality gate has passed

No proprietary questions or answers. Aggregate topic, difficulty, and item-format metadata may inform reviewed preparation guidance, but question text and explanations never enter this repository.

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
# 1673

# All AWS exams
cat data/index.json | jq '[.exams[] | select(.certifying_body == "AWS")]'

# Exams with 4+ domains
cat data/index.json | jq '[.exams[] | select(.domains >= 4)]'
```

## Coverage

| Certifying Body | Exams |
|-----------------|-------|
| ServiceNow | 94 |
| DMV / State Driver Licensing | 51 |
| Microsoft | 45 |
| College Board | 44 |
| DSST | 38 |
| CLEP | 34 |
| Salesforce | 32 |
| NCEES | 29 |
| FINRA | 26 |
| IICRC | 25 |
| SAP | 20 |
| AAPC | 20 |
| Oracle | 19 |
| HVAC Licensing | 17 |
| State Teacher Certification | 17 |
| CompTIA | 16 |
| Google Cloud | 16 |
| ACCA | 15 |
| AWS | 15 |
| *...and 204 more* | |

Full vendor directory: [`data/vendors.json`](data/vendors.json)

**Data completeness across all 1,673 exams:**

| Field | Coverage |
|-------|----------|
| Domain breakdowns | 97% (1,629) |
| Passing score | 69% (1,150) |
| Duration | 80% (1,342) |
| Pricing | 84% (1,399) |
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
| `search_exams` | Keyword search across all 1,673 blueprints, optional body/vendor filter |
| `get_exam_blueprint` | Full blueprint for one exam: domains, weights, scoring, prerequisites, reviewed guidance, and sources |
| `compare_exams` | Compare 2–8 exams side by side (questions, duration, passing score, price, validity) |
| `list_certifying_bodies` | All 223 certifying bodies with exam counts |

```bash
cd mcp && npm install && npm run build
```

It reads the local `data/` JSON when run from this repo, or fetches the published dataset from GitHub when installed standalone — so it's always in sync. See [`mcp/README.md`](mcp/README.md) for setup.

## How this data was collected

Each blueprint was sourced from the certifying body's official exam guide, certification page, or published PDF. The `source_url` field in every exam file links to the original source. Reviewed enrichment can use aggregate topic, difficulty, and format metadata from QuizForge practice records, but the pipeline never reads those records' stems, choices, answers, or explanations into public output.

Data was collected and structured by [QuizForge](https://quizforge.ai), a certification exam prep platform.

## Contributing

Found an outdated exam or missing certification? Contributions welcome.

- **Update an exam:** Edit the JSON file and submit a PR with a link to the updated official source.
- **Add a new exam:** Create a JSON file following the schema above. Include the `source_url`.
- **Report an issue:** Open an issue with the exam name and what needs correcting.

Please include the official source URL for any additions or changes.

## QuizForge automation credentials

`scripts/create_missing_exams.py` requires a dedicated QuizForge automation account. Never place its email, password, or bearer token in source files, command-line arguments, logs, fixtures, or generated output.

Set `QUIZFORGE_LOGIN_EMAIL` and `QUIZFORGE_LOGIN_PASSWORD` in the runtime environment. Production is the default API target. Set `QUIZFORGE_BASE_URL=https://qftest.sntrace.dev` for the gated Test replica or `QUIZFORGE_BASE_URL=http://localhost:5003` for the private Test tunnel. The script rejects other credential destinations.

The GitHub repository stores distinct production and Test values as encrypted Actions secrets: `QUIZFORGE_LOGIN_EMAIL`, `QUIZFORGE_LOGIN_PASSWORD`, `QUIZFORGE_TEST_LOGIN_EMAIL`, and `QUIZFORGE_TEST_LOGIN_PASSWORD`.

## License

This dataset is released under the [MIT License](LICENSE). The exam blueprints themselves are factual information published by their respective certifying bodies. This project consolidates and structures that information for programmatic use.

## Browse online

[atlas.quizforge.ai](https://atlas.quizforge.ai) -- searchable, rendered exam blueprints with domain breakdowns and study resources.

## Acknowledgments

Maintained by [QuizForge](https://quizforge.ai) -- free certification practice exams.
