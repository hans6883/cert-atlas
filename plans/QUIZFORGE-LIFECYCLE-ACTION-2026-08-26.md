# QuizForge lifecycle reconciliation task

## Outcome

Bring QuizForge's exam catalog, public exam list, practice availability, search behavior, and redirects into agreement with the reviewed Cert Atlas lifecycle evidence. Execute this in a fresh QuizForge worktree after the concurrent Claude work is merged. Deploy and validate on the private Test replica before production.

## Source of truth

Use the reviewed Cert Atlas lifecycle records and their linked Microsoft sources. Do not derive QuizForge state from page prose, a model response, similarly named exams, or course codes.

## Required reconciliation

1. Inventory both `ExamType` catalog entries and exam rows for AI-900, AI-102, DP-100, AZ-204, MB-240, MB-700, PL-500, PL-600, AZ-500, AZ-800, AZ-801, MS-102, MB-910, MB-920, MS-900, PL-200, and MB-335.
2. Inventory current successor entries AI-901, AI-103, AI-300, AI-200, AB-250, AB-100, SC-500, and AB-410. Classify each as present, missing, duplicate, incomplete, or not public.
3. Mark fully retired exams unavailable for new practice starts and remove them from current-exam promotion, while preserving historical analytics and existing user attempt data.
4. Keep AZ-500, AZ-800, AZ-801, and MS-102 active only through their verified retirement dates. Store the cutoff as data and queue a post-cutoff state transition; do not hardcode the date only in UI copy.
5. Represent replacement semantics explicitly: direct replacement, collective replacement, related current path, or no verified replacement. MB-240 to AB-250 is related, not direct.
6. Add missing successor or new exam types only through `ExamTypeCatalogService.GetOrCreateCatalogEntryAsync()`. Never create `ExamType` records directly.
7. For each new exam with sufficient official blueprint evidence, create or update the blueprint through `BlueprintParser.ParseJsonData()`. Queue any AI question generation, call `ExtractJsonFromAiResponse()` before parsing, and run `_deduplicationService.RemoveDuplicatesAsync(..., 0.85f)` before saving.
8. Redirect retired-exam discovery to a lifecycle explanation or the correctly typed current path. Never redirect a no-replacement exam to a merely similar credential.
9. Update search labels, admin views, sitemap/indexability decisions, and API responses so retired exams cannot appear current through a secondary surface.

## Test acceptance

- Test replica deployment succeeds and no production write occurs first.
- Retired exams cannot start a new practice session through direct URL, search, API, or cached UI state.
- Scheduled exams remain usable before the cutoff and are clearly labeled with the retirement date.
- Direct, collective, related, and no-replacement relationships render distinctly.
- Historical attempts, scores, subscriptions, and reporting remain intact.
- Successor creation is idempotent and creates no duplicate exam types or exams.
- Public search, canonical URLs, sitemap behavior, and redirects agree with the resulting lifecycle state.
- Unit and Playwright coverage exercise the state matrix and cutoff boundary in Test.

## Initial verified queue

| State | Exams |
| --- | --- |
| Retired with direct replacement | AI-900 to AI-901; AI-102 to AI-103; DP-100 to AI-300; AZ-204 to AI-200 |
| Retired with collective replacement | MB-700, PL-500, PL-600, and MB-335 to AB-100 |
| Retired with related path | MB-240 to AB-250 |
| Retired without verified direct replacement | MB-910, MB-920, MS-900 |
| Scheduled with direct replacement | AZ-500 to SC-500; PL-200 to AB-410 |
| Scheduled without verified replacement | AZ-800, AZ-801, MS-102 |

Do not start this task in the current QuizForge checkout while another agent has overlapping work. Begin by recording the clean base commit and reviewing `git status`, then use the standard Test-first deployment workflow in `docs/TEST-ENV.md`.
