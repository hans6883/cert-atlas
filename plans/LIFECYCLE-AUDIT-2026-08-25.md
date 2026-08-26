# Certification lifecycle audit - 2026-08-25

## Outcome

Cert Atlas now has a reproducible, candidate-only lifecycle audit across the complete local blueprint registry and the available live provider catalogs. The first reviewed publication batch updates eight retired Microsoft exam pages with dated official evidence, historical blueprint preservation, and precise successor guidance. No question stems, choices, answers, or explanations were used.

The audit deliberately does not turn a text match or a newly discovered link into public content. A retirement is published only after official verification. A catalog link is promoted only after confirming that it is a distinct, current exam with enough official blueprint evidence to produce a useful page.

## Inventory and source coverage

The source audit is recorded in [LIFECYCLE-SOURCE-SCAN-2026-08-25.json](LIFECYCLE-SOURCE-SCAN-2026-08-25.json). The provider comparison is recorded in [PROVIDER-CATALOG-SCAN-2026-08-25.json](PROVIDER-CATALOG-SCAN-2026-08-25.json).

| Surface | Accounted for | Result |
| --- | ---: | --- |
| Registry exam records | 2,582 | 2,582 scanned |
| Certifying bodies | 260 | 260 included in provider accounting |
| Registry source-material records | 12,361 | 10,452 local files scanned; unavailable records remain visible in registry status |
| HTML or text sources | 7,557 | Text inspected for lifecycle evidence |
| PDF records | 2,895 | Accounted for through their normalized blueprint records; not treated as raw-text evidence |
| Exams with local source material | 2,574 | Scanned |
| Exams without a local source | 8 | Explicitly reported, not silently skipped |
| Source parse errors | 1 | Explicitly reported |
| Providers with a catalog URL | 234 of 260 | Compared where fetchable |
| Live catalogs fetched | 134 | Link inventory compared with same-provider registry entries |
| Blocked or failed live catalogs | 100 | Require browser/manual follow-up; no negative conclusion drawn |

The public Cert Atlas dataset contains 1,673 exams from 223 vendors. QuizForge production contains 2,889 exam rows, including 2,502 public rows, and 3,021 exam-type catalog records. The lifecycle reconciliation therefore uses the private registry as the discovery superset and cross-checks affected codes against both public surfaces.

## Published reviewed transitions

These pages now behave as retirement and migration guides, not current-exam sales pages. They retain the final historical blueprint, name the evidence-backed relationship, suppress stale registration and practice calls to action, and compare legacy skills with the current path.

| Retired exam | Retirement date | Current path | Relationship | Official basis |
| --- | --- | --- | --- | --- |
| AI-900 | 2026-06-30 | AI-901 | Direct replacement | Microsoft retirement list, AI-901 page and dated study guides |
| AI-102 | 2026-06-30 | AI-103 | Direct replacement | Microsoft retirement list and June transition announcement |
| DP-100 | 2026-06-01 | AI-300 | Direct replacement | Microsoft retirement list and June transition announcement |
| AZ-204 | 2026-07-31 | AI-200 | Direct replacement | Microsoft retirement list and July transition announcement |
| MB-240 | 2026-06-30 | AB-250 | Related current path, explicitly not direct | Microsoft retirement list and July clarification |
| MB-700 | 2026-06-30 | AB-100 | Collective replacement path | Microsoft retirement list and June transition announcement |
| PL-500 | 2026-06-30 | AB-100 | Collective replacement path | Microsoft retirement list and June transition announcement |
| PL-600 | 2026-06-30 | AB-100 | Collective replacement path | Microsoft retirement list and June transition announcement |

Official sources:

- [Microsoft retired certification exams](https://learn.microsoft.com/en-us/credentials/support/retired-certification-exams)
- [Microsoft June 2026 partner announcements](https://learn.microsoft.com/en-us/partner-center/announcements/2026-june)
- [Microsoft July 2026 partner announcements](https://learn.microsoft.com/en-us/partner-center/announcements/2026-july)
- [AI-901 exam page](https://learn.microsoft.com/en-us/credentials/certifications/exams/ai-901/)

The lifecycle schema now distinguishes `direct_replacement`, `collective_replacement`, and `related_successor`. Rendering and MCP responses use different labels for each, preventing a related option such as AB-250 from being misrepresented as a one-for-one replacement for MB-240.

## Confirmed transitions still requiring publication work

The second reviewed publication batch completed seven of the original follow-up records. The lifecycle schema now supports `scheduled_retirement`, plus retired records with no replacement object. Scheduled pages retain valid current registration and practice actions until the cutoff; retired pages suppress them. An absent official replacement is stated directly and never filled with a model inference.

| Exam | Published state | Public behavior |
| --- | --- | --- |
| AZ-500 | Retires 2026-08-31; SC-500 direct replacement | Shows cutoff and a source-backed SC-500 skill map while AZ-500 remains available |
| AZ-800 and AZ-801 | Retire 2026-09-30; no verified replacement named | Shows cutoff, preserves current mechanics, and does not infer an exam from the AZ-802 course name |
| MS-102 | Retires 2026-11-30; no verified replacement named | Shows cutoff and role-specific preparation without inventing a successor |
| MB-910 and MB-920 | Retired 2025-12-31; no verified replacement named | Historical process maps with no registration, price, or practice action |
| MS-900 | Retired 2026-03-31; no verified replacement named | Historical Microsoft 365 scope with current-path selection guidance |

The following confirmed transitions still require publication work. PL-200 and MB-335 are not in the current public Cert Atlas inventory, so they require the new-record publication gate rather than a simple overlay.

| Exam | Verified state | Required action |
| --- | --- | --- |
| PL-200 | Retires 2026-08-31; AB-410 is the announced successor | Add a scheduled-retirement overlay now, then switch to retired after the date |
| DP-203, MB-210, MB-220, SC-400 | Retired legacy pages | Verify the current path from a first-party announcement before publishing a relationship |
| MB-335 | Retired 2026-06-30; part of the AB-100 consolidation | Add the collective-replacement overlay |

The next lifecycle run should automatically reclassify scheduled pages after their cutoff, but only after re-fetching Microsoft sources in case a date or transition changes.

## Other-provider retirement findings

The local scan produced 67 candidates. Manual review confirmed high-value cases including:

- Alibaba Cloud ACE-Cloud retired on 2025-05-13 and points to Solutions Architect (Expert).
- Alibaba Cloud ACP-Cloud retired on 2025-05-13 and points to Cloud Architect (Professional).
- Alibaba Cloud ACA-Cloud retired on 2025-03-31 and points to Cloud Engineer (Associate).
- AWS American Welding Society retired the standalone SCWI examination and now uses eligible endorsement paths.
- HashiCorp retired Consul Associate 003 on 2026-07-15; Consul is absent from the current certification catalog.
- ISACA retired CSX-P; no direct replacement was established.

These need provider-specific overlays after the same official-source review used for Microsoft. Shared catalog pages caused false positives for several Alibaba, HashiCorp, Okta, PTCB and welding records. Wording such as “retired questions,” a retired delivery mode, or another exam on the same page is not sufficient evidence about the candidate exam.

Relevant first-party catalogs include [HashiCorp certifications](https://developer.hashicorp.com/certifications), [the retired Consul 003 review page](https://developer.hashicorp.com/consul/tutorials/certification-003/associate-review-003), and [Cisco's retired exam list](https://www.cisco.com/site/us/en/learn/training-certifications/exams/retired.html).

## New-exam and missing-catalog discovery

The refreshed live provider comparison found 310 links that do not map to a same-provider registry URL. This is a deliberately broad triage queue containing exams, certification landing pages, handbooks, bundles, localized duplicates, and navigation links. It must not be counted as 310 new exams. Fetch availability can change between runs; the artifact records its exact coverage and failures.

Confirmed official Microsoft launches or successor exam codes missing from QuizForge's exam-type catalog are:

- AI-901, AI-103, AI-300 and AI-200
- AB-250, AB-100, AB-210 and AB-410
- SC-500
- GH-600 and DP-800
- AB-620, which requires blueprint readiness review before publication

High-value current-provider catalog gaps found for further verification include:

- Snowflake: COF-C03, ADA-C02, DAA-C01, DEA-C02, DSA-C03, GES-C02, MLA-B01, NAS-C02, SEA-C01 and SPS-C01.
- Nutanix: NCP-AI, NCP-BC, NCP-CI-AWS, NCP-CI-Azure, NCP-CN, NCP-EUC, NCP-MCA, NCP-NS, NCP-US and NPX.
- Smaller candidate sets from IABAC, PTCB and Meta Blueprint.

These are confirmed current catalog entries or strong catalog gaps, not all confirmed recent launches. Each must be classified as new launch, renamed version, localized duplicate, track/bundle page, or genuinely missing exam before ingestion. Official catalog references include [Snowflake certifications](https://learn.snowflake.com/en/certifications/) and [Nutanix certifications](https://www.nutanix.com/support-services/training-certification/certifications).

## Publication policy and next run

1. Refresh both candidate artifacts with `python scripts/lifecycle_audit.py --registry C:\Users\stephen\source\repos\web-scraper-mcp\data\blueprint_registry.db --source-root C:\Users\stephen\source\repos\web-scraper-mcp --public-index data\index.json --output plans\LIFECYCLE-SOURCE-SCAN-2026-08-25.json --provider-output plans\PROVIDER-CATALOG-SCAN-2026-08-25.json`. Registry `local_path` values are relative to the web-scraper repository root. The provider phase uses live network requests, so review its fetch-failure count each run.
2. Review candidates against an official retirement list, dated announcement, exam page, or study guide.
3. Record relationship semantics; never infer direct replacement from similar titles.
4. Require current official objectives and sufficient source depth before adding a new exam.
5. Generate an enrichment overlay, validate it, review rendered copy, and only then mark it `reviewed`.
6. Keep retired URLs live as historical migration resources, but remove price, scheduling, registration, practice and current-exam structured data.
7. Re-run the audit monthly and immediately after a provider announcement cycle.

The machine artifacts are candidate evidence and inventory, while reviewed enrichment JSON remains the publication gate.
