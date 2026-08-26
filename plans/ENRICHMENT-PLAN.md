# Cert Atlas source-bound enrichment plan

## Outcome

Turn Cert Atlas from a thin blueprint directory into a rich, source-linked certification reference repository while preserving the public URL inventory and preventing private exam-bank material from entering Git, HTML, or MCP responses.

The first implementation baseline contains 1,673 public exams across 223 certifying bodies. The current registry contains 2,582 exams, but 909 registry records are withheld from publication until each has sufficient official evidence and a reviewed enrichment overlay. Existing URLs remain stable even when an older record is temporarily absent from the current registry.

## Source precedence

Factual claims use this order:

1. Current official exam guide or objectives.
2. Current official certification, registration, candidate-handbook, renewal, or documentation page.
3. Existing normalized Cert Atlas record, when it does not conflict with a current official source.
4. Aggregate private-bank metadata, for preparation emphasis only.

Private-bank content is never a factual authority. Search snippets, competitor pages, model memory, and inferred values cannot establish exam mechanics or policy.

## Exam-bank synthesis boundary

Allowed aggregate inputs are topic labels, exam category, difficulty labels, question-format labels, record counts, and a deterministic dataset hash. They may support statements such as which published topics deserve extra practice or which broad scenario styles appear useful for preparation.

The pipeline must never select, copy, reconstruct, summarize closely, or publish question stems, answer choices, correct answers, explanations, screenshots, diagrams, raw database rows, or recognizable bank phrasing. Public output must carry a disclaimer that aggregate preparation signals are not official weights or predictions.

## Git data model

Each candidate enrichment is stored at `enrichment/<vendor-slug>/<exam-id>.json`. It contains:

- concise SEO metadata;
- exam overview, intended audience, skills, preparation strategy, and exam-day guidance;
- per-domain study guidance tied to existing domain IDs;
- optional aggregate study signals;
- source-backed factual corrections;
- official source URLs, access dates, and content hashes;
- generation and independent review metadata.

Evidence packs, source text, generation requests, responses, and private paths stay under ignored `.tmp/` storage. They are reproducible working artifacts, not public dataset content.

## Pipeline

1. Read the canonical registry and locate only approved primary official sources.
2. Resolve each source path beneath the approved source-material root and verify its hash.
3. Extract bounded text while recursively removing question-shaped fields.
4. Optionally compute safe bank aggregates using a fixed-column SQL query that never reads private text columns.
5. Create a provider-neutral model request containing the evidence, safe signals, prompt, and JSON schema.
6. Require the model to return a draft that cannot approve itself.
7. Validate identifiers, word counts, sources, confidence, hashes, prohibited fields, and correction targets.
8. Review the draft against official evidence and promote it to `reviewed` only after corrections.
9. Apply reviewed overlays to existing public records through the narrow apply command.
10. Add a new registry exam only through the gated exporter and only when its reviewed enrichment passes.
11. Rebuild the static site and MCP snapshot, then run all SEO, content, MCP, and security checks.

## Publication gates

An overlay is publishable only when all of these conditions hold:

- status is `reviewed` and `publishable` is true;
- evidence coverage and factual confidence are each at least 0.80;
- at least one current official source is present with HTTPS URL, access date, and SHA-256 hash;
- all editorial and domain source IDs resolve;
- every domain or objective correction targets an existing normalized item;
- editorial content meets minimum substance thresholds and the meta description is complete;
- no prohibited bank-shaped field appears anywhere in the overlay;
- all aggregate signals include a record count and deterministic hash.

Failure at any gate leaves the current public record unchanged. New records remain unpublished.

## SEO and page requirements

Every enriched page must retain one indexable canonical URL, one page-specific H1, a unique title, a complete 70-160 character meta description, useful visible prose, correct domain ranges, visible source provenance, and a review date. Structured data uses the reviewed overview and `dateModified`. Enrichment CSS is emitted only on enriched pages so pilot releases do not rewrite the full generated site.

The content should answer, without a practice-test click: what the credential validates, who it is for, what skills matter, how the domains relate, how to prepare, and where the facts came from. It must avoid keyword stuffing, generic filler, difficulty claims, pass-rate claims, salary claims, and predictions about unpublished questions.

## Defensible first-party value

The durable differentiator is structured analysis that combines current official sources with safe QuizForge metadata, not additional generic prose. Each enriched page should add the most useful applicable artifacts from this list:

- a lifecycle banner that distinguishes active, retiring, and retired exams and suppresses stale registration or practice calls to action;
- a source-backed predecessor-to-replacement skill map, including changed weights and a migration checklist;
- a blueprint-change ledger generated from dated source hashes, with changed records queued for review before publication;
- normalized practice-corpus coverage by official domain, question format, and difficulty, clearly labeled as QuizForge coverage rather than official weighting;
- an objective-to-official-learning-resource map using current vendor documentation, modules, labs, and practice assessments;
- deterministic two-, four-, and six-week study plans built from official objectives and user-selected study time;
- privacy-thresholded learner performance signals only after a page has enough completed attempts and distinct learners to prevent disclosure or misleading small-sample claims;
- visible source access dates and a plain-language Who/How/Why disclosure describing AI assistance, factual review, and excluded inputs.

Exam-dump text, answers, explanations, and recognizable derivatives remain excluded even when locally available. A feature is not valuable enough to publish merely because it can be computed; it must also be lawful, current, explainable, and useful without requiring a QuizForge conversion.

## MCP parity

The MCP is a second rendering of the same canonical public JSON, not a separate content store. It must:

- derive dataset counts from the bundled current index;
- return rich sections only for approved reviewed content;
- display official weight ranges and source verification;
- remain compatible with local and remote blueprint loading;
- use the latest compatible Model Context Protocol SDK only after build, contract tests, and dependency audit pass.

## Rollout

Phase 1 is one representative, evidence-rich pilot: Microsoft AI-102. Live source re-verification found that Microsoft retired AI-102 on June 30, 2026 and replaced it with AI-103. The pilot therefore proves lifecycle correction, stale-action suppression, source-backed replacement mapping, exact historical range correction, corrupted-objective correction, transparent AI methodology, HTML rendering, MCP rendering, and fail-closed model handling. It also demonstrates why source drift must be checked before prose generation.

Phase 2 enriches a deliberately varied batch across technology, healthcare, finance, trades, and academic testing. Batch results must be reviewed for source coverage, repetition, content usefulness, factual correction rate, and generation abstentions.

Phase 3 works through the 909 withheld registry exams, prioritizing records with primary downloaded official sources and meaningful blueprints. Thin or ambiguous records stay withheld.

Phase 4 continuously re-verifies sources by access date and content hash, queues changed exams for review, and publishes only reviewed deltas.

The 2026-08-25 lifecycle expansion is documented in [LIFECYCLE-AUDIT-2026-08-25.md](LIFECYCLE-AUDIT-2026-08-25.md). It adds a full-registry candidate scan, an available-provider catalog comparison, and 15 reviewed Microsoft lifecycle overlays. The second batch adds scheduled-retirement support for AZ-500, AZ-800, AZ-801, and MS-102, plus no-invented-successor historical pages for MB-910, MB-920, and MS-900. Lifecycle relationships are explicitly typed as direct, collective, related, or absent so neither the static site nor the MCP overstates equivalence. The accompanying live-catalog findings remain a review queue; discovery alone never passes the publication gate. QuizForge follow-up is separately scoped in [QUIZFORGE-LIFECYCLE-ACTION-2026-08-26.md](QUIZFORGE-LIFECYCLE-ACTION-2026-08-26.md) so it can be executed in an isolated worktree after concurrent application work is merged.

## Current registry quality decision

The 2026-08-25 gated dry run compared all 1,673 existing public records with the 2,582-record local registry after rebasing the ServiceNow expansion. The newer registry would add domain data to 34 previously domainless records, increase domain counts for 69 records, and increase objective counts for one record. It is not yet safe as a wholesale replacement because 14 records would lose objectives and malformed legacy practice URLs still require an explicit repair or redirect decision. No passing-score or whole-domain breakdown losses remain in this comparison. Therefore the current implementation updates the MCP snapshot to the latest reviewed public dataset and promotes only the AI-102 pilot; it does not overwrite all existing exam JSON with the raw latest registry export.

Before a bulk registry refresh, the exporter needs a monotonic merge policy for independently verified facts, explicit review of every domain/objective regression, and a URL repair or redirect policy for malformed legacy practice slugs. Coverage gain alone is not a sufficient quality signal.

## Acceptance criteria

- No raw or recognizable private question content exists in tracked changes or rendered output.
- The full 1,897-page static build passes canonical, indexability, H1, sitemap, and unique-title tests.
- The pilot has source-linked substantive content, corrected official ranges, and no known parser corruption.
- Draft, invalid, unsupported, and low-confidence overlays cannot change public files.
- Registry expansion does not expose any of the 909 thin records without approved content.
- MCP build and tests pass on the selected SDK and `npm audit` reports zero vulnerabilities.
- Git diff contains only intentional source, dataset, MCP, plan, schema, prompt, and pilot artifacts.
