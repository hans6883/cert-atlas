# Cert Atlas

**The open index of certification exam blueprints.**

1,562 exams. 217 certifying bodies. Structured, machine-readable JSON sourced from official exam guides and certification pages.

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
