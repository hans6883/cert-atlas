/**
 * Cert Atlas MCP server definition — tools, resources, and prompts, shared by
 * every transport (stdio in index.ts, Streamable HTTP in http.ts). Call
 * createServer() to get a fresh, fully-wired McpServer instance.
 *
 * Active exams may carry a QuizForge practice link with UTM attribution
 * (utm_source=mcp, utm_campaign=<tool>). Retired exams suppress stale practice
 * and registration actions and point to the current replacement instead.
 * Scheduled retirements retain current actions while clearly naming the cutoff.
 */
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import {
  getIndex,
  getBlueprint,
  resolveExam,
  scoreMatch,
  toText,
  withUtm,
  practiceCta,
  type Blueprint,
  type IndexEntry,
} from "./catalog.js";

export const ATLAS = "https://atlas.quizforge.ai";
export const VERSION = "1.3.0";

const INSTRUCTIONS =
  "Cert Atlas is a source-linked open index of thousands of certification and professional exam " +
  "blueprints. Call search_exams whenever a user mentions a certification or exam " +
  "(e.g. AWS Solutions Architect, CISSP, CompTIA Security+, PMP, CCNA, NCLEX, CFA, Azure AZ-104, CKA). " +
  "Use get_exam_blueprint for what's on an exam / domain weights / prerequisites / passing score / " +
  "duration; compare_exams for 'X vs Y / which is harder or cheaper'; list_certifying_bodies for " +
  "which providers are covered. Active results may include a free QuizForge practice-exam link. " +
  "Scheduled retirements name the cutoff and verified transition while the exam remains available. " +
  "Retired results identify the verified current path, if any, and must not promote stale exam actions.";

// --- practice-link helper ----------------------------------------------------
function practiceLink(e: IndexEntry, bp: Blueprint | null, tool: string): string | null {
  return withUtm(bp?.practice_url ?? e.practice_url, tool);
}

// --- formatting helpers ------------------------------------------------------
export function indexLine(e: IndexEntry, tool: string): string {
  const code = e.exam_code ? `[${e.exam_code}] ` : "";
  const retired = e.lifecycle_status === "retired";
  const scheduled = e.lifecycle_status === "scheduled_retirement";
  const retiredRelationshipLabel = {
    related_successor: "related current path",
    collective_replacement: "broader replacement path",
    direct_replacement: "replaced by",
  }[e.replacement_relationship ?? "direct_replacement"];
  const scheduledRelationshipLabel = {
    related_successor: "related future path",
    collective_replacement: "broader future path",
    direct_replacement: "will be replaced by",
  }[e.replacement_relationship ?? "direct_replacement"];
  const parts = retired
    ? [
        `retired${e.retired_on ? ` ${e.retired_on}` : ""}`,
        e.replacement_exam_code
          ? `${retiredRelationshipLabel} ${e.replacement_exam_code}`
          : "no verified replacement",
      ]
    : scheduled
      ? [
          `retires${e.retires_on ? ` ${e.retires_on}` : ""}`,
          e.replacement_exam_code
            ? `${scheduledRelationshipLabel} ${e.replacement_exam_code}`
            : "no verified replacement named",
          `${e.domains} domains`,
        ]
      : [`${e.domains} domains`];
  if (!retired && e.total_questions != null) parts.push(`${e.total_questions} Q`);
  if (!retired && e.duration_minutes != null) parts.push(`${e.duration_minutes} min`);
  const practice = retired ? null : practiceLink(e, null, tool);
  const practiceStr = practice ? `  ·  practice: ${practice}` : "";
  return `- ${code}${e.exam_name} — ${e.certifying_body}  (${e.exam_id})\n    ${parts.join(" · ")}${practiceStr}`;
}

function dash(v: unknown, suffix = ""): string {
  return v == null || v === "" ? "—" : `${v}${suffix}`;
}

export function datasetSummary(meta: { total_exams: number; total_vendors: number }): string {
  return `${meta.total_exams.toLocaleString("en-US")} exams across ${meta.total_vendors.toLocaleString("en-US")} certifying bodies`;
}

function hasApprovedEnrichment(bp: Blueprint): boolean {
  return Boolean(
    bp.editorial &&
      bp.content_quality?.status === "reviewed" &&
      bp.content_quality?.publishable === true,
  );
}

// editorial.faq is newer than the EditorialContent type in catalog.ts; declared
// locally so this file alone surfaces it without touching the shared catalog types.
type EditorialFaqItem = { question_title?: string | null; answer_text?: string | null };

export function blueprintText(e: IndexEntry, bp: Blueprint): string {
  const L: string[] = [];
  const retired = bp.lifecycle?.status === "retired" || e.lifecycle_status === "retired";
  const scheduled =
    bp.lifecycle?.status === "scheduled_retirement" ||
    e.lifecycle_status === "scheduled_retirement";
  const lifecycleNotice = retired || scheduled;
  const lifecycleDate = scheduled
    ? bp.lifecycle?.retires_on ?? e.retires_on
    : bp.lifecycle?.retired_on ?? e.retired_on;
  const headingSuffix = retired
    ? " - Retired"
    : scheduled && lifecycleDate
      ? ` - Retires ${lifecycleDate}`
      : scheduled
        ? " - Scheduled retirement"
        : "";
  L.push(
    `# ${bp.exam_name}${bp.exam_code ? ` (${bp.exam_code})` : ""}${headingSuffix}`,
  );
  L.push(`Certifying body: ${bp.certifying_body ?? e.certifying_body}`);
  if (bp.certification_name) L.push(`Certification: ${bp.certification_name}`);

  if (lifecycleNotice) {
    const lifecycle = bp.lifecycle;
    const replacement = lifecycle?.replacement;
    L.push("");
    L.push(retired ? "## Retirement and replacement" : "## Scheduled retirement and transition");
    if (lifecycle?.summary) L.push(lifecycle.summary);
    if (lifecycleDate) L.push(`${retired ? "Retired" : "Retires"}: ${lifecycleDate}`);
    const replacementCode = replacement?.exam_code ?? e.replacement_exam_code;
    const replacementUrl = replacement?.url ?? e.replacement_url;
    const replacementLabel = [replacementCode, replacement?.name].filter(Boolean).join(": ");
    const relationshipLabel = {
      related_successor: "Related current path",
      collective_replacement: "Broader replacement path",
      direct_replacement: "Replacement",
    }[replacement?.relationship ?? "direct_replacement"];
    if (replacementLabel || replacementUrl) {
      L.push(
        `${relationshipLabel}: ${replacementLabel || "current exam"}${replacementUrl ? ` - ${replacementUrl}` : ""}`,
      );
    } else {
      L.push("No verified replacement named in the reviewed official sources.");
    }
    if (replacement?.study_guide_url) {
      L.push(`Replacement study guide: ${replacement.study_guide_url}`);
    }
  }

  if (!retired) {
    const mech: string[] = [];
    if (bp.total_questions != null) mech.push(`${bp.total_questions} questions`);
    if (bp.duration_minutes != null) mech.push(`${bp.duration_minutes} min`);
    if (bp.passing_score != null)
      mech.push(`pass ${bp.passing_score}${bp.passing_score_scale ? ` (${bp.passing_score_scale})` : ""}`);
    if (bp.exam_format) mech.push(String(bp.exam_format));
    if (mech.length) L.push(`Format: ${mech.join(" · ")}`);
    if (bp.question_types?.length) L.push(`Question types: ${bp.question_types.join(", ")}`);
    if (bp.exam_price_usd != null)
      L.push(`Price: $${bp.exam_price_usd}${bp.exam_price_notes ? ` (${bp.exam_price_notes})` : ""}`);
    if (bp.available_languages?.length) L.push(`Languages: ${bp.available_languages.join(", ")}`);

    const prereq = toText(bp.prerequisites);
    L.push(`Prerequisites: ${prereq ? prereq : "None stated"}`);
    const recExp = toText(bp.recommended_experience);
    if (recExp) L.push(`Recommended experience: ${recExp}`);

    const ren: string[] = [];
    if (bp.certification_validity_years != null) ren.push(`valid ${bp.certification_validity_years} yr`);
    if (bp.renewal_required != null) ren.push(bp.renewal_required ? "renewal required" : "no renewal");
    if (ren.length) L.push(`Validity: ${ren.join(" · ")}${bp.renewal_options ? ` — ${toText(bp.renewal_options)}` : ""}`);
    const retake = toText(bp.retake_policy);
    if (retake) L.push(`Retake policy: ${retake}`);
  }

  if (hasApprovedEnrichment(bp) && bp.editorial) {
    const editorial = bp.editorial;
    L.push("");
    L.push(retired ? "## Historical scope" : "## What this exam validates");
    L.push(editorial.overview);
    L.push("");
    L.push(retired ? "## Who this was for" : "## Who should take it");
    L.push(editorial.who_should_take);
    if (editorial.skills_summary?.length) {
      L.push("");
      L.push("## Skills to demonstrate");
      for (const skill of editorial.skills_summary) L.push(`- ${skill}`);
    }
    L.push("");
    L.push(retired ? "## How to reuse prior preparation" : "## How to prepare");
    L.push(editorial.preparation_strategy);
    if (lifecycleNotice && bp.lifecycle) {
      const replacementCode = bp.lifecycle.replacement?.exam_code ?? "the current credential catalog";
      const relationship = bp.lifecycle.replacement?.relationship ?? "direct_replacement";
      if (bp.lifecycle.skill_comparison?.length) {
        L.push("");
        L.push(
          relationship === "related_successor"
            ? `## How ${bp.exam_code ?? "the retired exam"} skills compare with ${replacementCode}`
            : `## What changed from ${bp.exam_code ?? "the retired exam"} to ${replacementCode}`,
        );
        for (const item of bp.lifecycle.skill_comparison) {
          const legacy = `${item.legacy_skill ?? "Legacy skill"}${item.legacy_weight ? ` (${item.legacy_weight})` : ""}`;
          const current = `${item.replacement_skill ?? "Replacement skill"}${item.replacement_weight ? ` (${item.replacement_weight})` : ""}`;
          L.push(`- ${legacy} -> ${current}${item.change ? `: ${item.change}` : ""}`);
        }
      }
      if (bp.lifecycle.migration_actions?.length) {
        L.push("");
        L.push(retired ? "## Migration checklist" : "## Transition checklist");
        for (const action of bp.lifecycle.migration_actions) L.push(`- ${action}`);
      }
    }
    if (editorial.domain_guidance?.length) {
      L.push("");
      L.push(retired ? "## Historical domain guide" : "## Domain study guidance");
      for (const guidance of editorial.domain_guidance) {
        const domain = bp.domains?.find((item) => String(item.id ?? "") === guidance.domain_id);
        L.push(`### ${domain?.name ?? `Domain ${guidance.domain_id}`}`);
        L.push(guidance.summary);
        for (const focus of guidance.study_focus ?? []) L.push(`- ${focus}`);
      }
    }
    if (editorial.exam_day_guidance && !retired) {
      L.push("");
      L.push("## Exam-day guidance");
      L.push(editorial.exam_day_guidance);
    }
    const faq = (editorial as { faq?: EditorialFaqItem[] | null }).faq;
    if (faq?.length) {
      L.push("");
      L.push("## Frequently asked questions");
      for (const item of faq) {
        if (!item.question_title?.trim() || !item.answer_text?.trim()) continue;
        L.push(`Q: ${item.question_title}`);
        L.push(`A: ${item.answer_text}`);
      }
    }
    if (bp.study_signals) {
      const signals = bp.study_signals;
      const topics = signals.topic_emphasis ?? [];
      const challenges = signals.challenge_areas ?? [];
      const styles = signals.question_style_observations ?? [];
      if (topics.length || challenges.length || styles.length) {
        L.push("");
        L.push("## Preparation signals");
        L.push(
          "Derived only from aggregate practice metadata; these are study aids, not official exam weights or predictions.",
        );
        for (const topic of topics) {
          const details = [topic.level, topic.share_percent != null ? `${topic.share_percent}%` : null]
            .filter(Boolean)
            .join(", ");
          L.push(`- ${topic.topic}${details ? ` (${details})` : ""}`);
        }
        for (const challenge of challenges) L.push(`- ${challenge}`);
        for (const style of styles) L.push(`- ${style}`);
      }
    }
  }

  if (bp.domains?.length) {
    L.push("");
    L.push(retired ? "## Historical domains" : `## Domains (${bp.domains.length})`);
    for (const d of bp.domains) {
      let w = "";
      if (d.weight_min_percent != null && d.weight_max_percent != null) {
        w = d.weight_min_percent === d.weight_max_percent
          ? ` — ${d.weight_min_percent}%`
          : ` — ${d.weight_min_percent}-${d.weight_max_percent}%`;
      } else if (d.weight_percent != null) {
        w = ` — ${d.weight_percent}%`;
      }
      L.push(`- ${d.name}${w}`);
      for (const o of d.objectives ?? []) {
        if (typeof o === "string") {
          if (o) L.push(`    · ${o}`);
          continue;
        }
        const t = o.description ?? o.title ?? o.name ?? "";
        const label = [o.id, t].filter(Boolean).join(" ");
        if (label) L.push(`    · ${label}`);
        for (const subObjective of o.sub_objectives ?? []) {
          if (subObjective) L.push(`        - ${subObjective}`);
        }
      }
    }
  } else {
    L.push("");
    L.push("## Domains: not broken down in the published blueprint (logistics below still apply)");
  }

  L.push("");
  if (bp.source_url) L.push(`Official source: ${bp.source_url}`);
  if (bp.official_objectives_url) L.push(`Objectives: ${bp.official_objectives_url}`);
  if (bp.exam_registration_url && !retired) L.push(`Register: ${bp.exam_registration_url}`);
  if (hasApprovedEnrichment(bp) && bp.sources?.length) {
    L.push("");
    L.push("## Sources and verification");
    const reviewed = bp.content_quality?.reviewed_at?.slice(0, 10);
    if (reviewed) L.push(`Verified: ${reviewed}`);
    for (const source of bp.sources) {
      L.push(`- ${source.title} (${source.publisher}): ${source.url}`);
    }
  }
  if (hasApprovedEnrichment(bp) && bp.editorial?.methodology?.summary) {
    L.push("");
    L.push("## How this record was made");
    L.push(bp.editorial.methodology.summary);
  }
  const practice = practiceLink(e, bp, "get_exam_blueprint");
  if (practice && !retired) L.push(practiceCta(bp.exam_name, practice));
  return L.join("\n");
}

const text = (t: string) => ({ content: [{ type: "text" as const, text: t }] });

// --- server factory ----------------------------------------------------------
export function createServer(): McpServer {
  const server = new McpServer({ name: "cert-atlas", version: VERSION }, { instructions: INSTRUCTIONS });

  server.tool(
    "search_exams",
    "Search the current Cert Atlas certification and professional exam index by name, code, certifying body, or vendor. " +
      "Call this whenever a user mentions a certification or exam — e.g. AWS Solutions Architect, " +
      "CISSP, CompTIA Security+, PMP, CCNA, NCLEX, CFA, Azure AZ-104, CKA — or asks what certs a " +
      "body offers. Returns matching exams with code, certifying body, question count, domain count, " +
      "and a free practice-exam link.",
    {
      query: z.string().optional().describe("Keywords: certification name, exam code, vendor, or topic"),
      certifying_body: z
        .string()
        .optional()
        .describe("Filter by certifying body, e.g. 'AWS', 'CompTIA', 'ISC2', 'Microsoft'"),
      vendor_slug: z.string().optional().describe("Filter by vendor slug, e.g. 'aws', 'microsoft', 'comptia'"),
      limit: z.number().int().min(1).max(50).optional().describe("Max results (default 20)"),
    },
    async ({ query, certifying_body, vendor_slug, limit }) => {
      const { exams, meta } = await getIndex();
      const max = limit ?? 20;
      let pool = exams;
      if (certifying_body) {
        const b = certifying_body.toLowerCase();
        pool = pool.filter((e) => e.certifying_body.toLowerCase().includes(b));
      }
      if (vendor_slug) {
        const v = vendor_slug.toLowerCase();
        pool = pool.filter((e) => e.vendor_slug.toLowerCase() === v || e.vendor_slug.toLowerCase().includes(v));
      }

      const q = (query ?? "").trim();
      if (!q && !certifying_body && !vendor_slug) {
        return text(
          `Provide a query (e.g. "aws solutions architect", "CISSP") and/or a certifying_body / ` +
            `vendor_slug filter. Cert Atlas indexes ${meta.total_exams} exams across ${meta.total_vendors} ` +
            `bodies — list them with list_certifying_bodies. Browse: ${ATLAS}`,
        );
      }

      let ranked: IndexEntry[];
      if (q) {
        ranked = pool
          .map((e) => ({ e, s: scoreMatch(e, q) }))
          .filter((x) => x.s > 0)
          .sort((a, b2) => b2.s - a.s)
          .slice(0, max)
          .map((x) => x.e);
      } else {
        ranked = pool.slice(0, max);
      }

      if (ranked.length === 0) {
        const filterNote = [certifying_body && `body="${certifying_body}"`, vendor_slug && `vendor="${vendor_slug}"`]
          .filter(Boolean)
          .join(", ");
        return text(
          `No Cert Atlas exam matched "${query ?? ""}"${filterNote ? ` (${filterNote})` : ""}. ` +
            `Try a broader keyword or an exam code. Browse the full index: ${ATLAS}`,
        );
      }
      const totalMatches = q ? pool.filter((e) => scoreMatch(e, q) > 0).length : pool.length;
      const more = totalMatches > ranked.length;
      return text(
        `Found ${ranked.length}${more ? ` of ${totalMatches}` : ""} Cert Atlas exam(s) ` +
          `for "${query ?? "(filtered)"}":\n\n` +
          ranked.map((e) => indexLine(e, "search_exams")).join("\n") +
          (more ? `\n\n…more available — raise \`limit\`.` : "") +
          `\n\nFull blueprint: get_exam_blueprint(<id or code>). Browse: ${ATLAS}`,
      );
    },
  );

  server.tool(
    "get_exam_blueprint",
    "Get the full published blueprint for ONE certification exam: domain/objective breakdown with " +
      "topic weights, passing score, question count & types, duration, price, prerequisites, retake & " +
      "renewal policy, languages, and the official source URL. Reviewed records also include an exam " +
      "overview, audience, preparation guidance, aggregate study signals, and source verification. " +
      "Call this for 'what's on the X exam', " +
      "'how is X weighted by domain', 'prerequisites for X', 'passing score for X', 'how long is X'. " +
      "Accepts an exam_id, exam_code, or certification name. Includes a free practice-exam link.",
    { exam: z.string().describe("Exam id, exam code, or certification name") },
    async ({ exam }) => {
      const entry = await resolveExam(exam);
      if (!entry) {
        return text(
          `"${exam}" didn't resolve to a Cert Atlas exam. Try search_exams("${exam}") to find ` +
            `the right id or code, or browse ${ATLAS}.`,
        );
      }
      try {
        const bp = await getBlueprint(entry);
        return text(blueprintText(entry, bp));
      } catch (err) {
        return text(
          `Resolved "${exam}" to ${entry.exam_name} (${entry.exam_id}) but couldn't load its ` +
            `blueprint file: ${(err as Error).message}`,
        );
      }
    },
  );

  server.tool(
    "compare_exams",
    "Compare 2–8 certification exams side by side — price, duration, passing score, question count, " +
      "and domain count. Call for 'X vs Y', 'which is harder/cheaper', 'easiest cloud cert', " +
      "'CCNA vs Network+'. Accepts exam ids, codes, or names; each row links a free practice exam.",
    { exams: z.array(z.string()).min(2).max(8).describe("2–8 exam ids, codes, or names to compare") },
    async ({ exams }) => {
      const resolved = await Promise.all(exams.map(async (q) => ({ q, entry: await resolveExam(q) })));
      const unresolved = resolved.filter((r) => !r.entry).map((r) => r.q);
      const found = resolved.filter((r) => r.entry) as { q: string; entry: IndexEntry }[];
      if (found.length < 2) {
        return text(
          `Need at least 2 resolvable exams to compare. Unresolved: ${unresolved.join(", ") || "(none)"}. ` +
            `Use search_exams to find ids.`,
        );
      }

      const rows = await Promise.all(
        found.map(async ({ entry }) => {
          let bp: Blueprint | null = null;
          try {
            bp = await getBlueprint(entry);
          } catch {
            /* fall back to index-only fields */
          }
          return {
            label: entry.exam_code || entry.exam_id,
            name: bp?.exam_name ?? entry.exam_name,
            body: entry.certifying_body,
            questions: bp?.total_questions ?? entry.total_questions,
            duration: bp?.duration_minutes ?? entry.duration_minutes,
            pass: bp?.passing_score ?? null,
            scale: bp?.passing_score_scale ?? null,
            price: bp?.exam_price_usd ?? null,
            valid: bp?.certification_validity_years ?? null,
            domains: bp?.domains?.length ?? entry.domains,
            practice: practiceLink(entry, bp, "compare_exams"),
          };
        }),
      );

      const header = `| Exam | Body | Questions | Duration | Passing | Price | Valid | Domains |`;
      const sep = `|------|------|-----------|----------|---------|-------|-------|---------|`;
      const bodyRows = rows
        .map(
          (r) =>
            `| ${r.label} | ${r.body} | ${dash(r.questions)} | ${dash(r.duration, " min")} | ` +
            `${r.pass != null ? `${r.pass}${r.scale ? ` (${r.scale})` : ""}` : "—"} | ` +
            `${dash(r.price != null ? `$${r.price}` : null)} | ${dash(r.valid != null ? `${r.valid} yr` : null)} | ` +
            `${dash(r.domains)} |`,
        )
        .join("\n");
      const links = rows
        .filter((r) => r.practice)
        .map((r) => `- ${practiceCta(r.name, r.practice as string)}`)
        .join("\n");

      return text(
        [
          `Comparing ${rows.length} exams:`,
          "",
          header,
          sep,
          bodyRows,
          unresolved.length ? `\nCouldn't resolve: ${unresolved.join(", ")}` : "",
          links ? `\nPractice free (QuizForge):\n${links}` : "",
        ]
          .filter((s) => s !== "")
          .join("\n"),
      );
    },
  );

  server.tool(
    "list_certifying_bodies",
    "List the certifying bodies / vendors in the current Cert Atlas index with exam counts. Call for " +
      "'what certification providers/vendors are covered', 'how many AWS/Microsoft/Cisco certs'. " +
      "Optionally filter by a substring.",
    { contains: z.string().optional().describe("Optional substring filter on the body name, e.g. 'micro', 'aws'") },
    async ({ contains }) => {
      const { byBody, meta } = await getIndex();
      let rows = [...byBody.entries()].map(([b, list]) => ({
        body: b,
        vendor_slug: list[0]?.vendor_slug ?? "",
        count: list.length,
      }));
      if (contains) {
        const c = contains.toLowerCase();
        rows = rows.filter((r) => r.body.toLowerCase().includes(c) || r.vendor_slug.toLowerCase().includes(c));
      }
      rows.sort((a, b2) => b2.count - a.count || a.body.localeCompare(b2.body));
      if (rows.length === 0) {
        return text(`No certifying body matched "${contains}". ${meta.total_vendors} bodies total. Browse: ${ATLAS}`);
      }
      const head = contains
        ? `${rows.length} certifying bodies matching "${contains}":`
        : `Cert Atlas covers ${datasetSummary(meta)} (generated ${meta.generated}):`;
      return text(
        `${head}\n\n` +
          rows.map((r) => `- ${r.body} (${r.vendor_slug}): ${r.count} exam${r.count === 1 ? "" : "s"}`).join("\n") +
          `\n\nSearch within one via search_exams(query, certifying_body="<name>"). Browse: ${ATLAS}`,
      );
    },
  );

  // --- resources -------------------------------------------------------------
  server.registerResource(
    "cert-atlas-index",
    "cert-atlas://index",
    {
      title: "Cert Atlas index",
      description: "The current master index of Cert Atlas certification exams (one lean row each).",
      mimeType: "application/json",
    },
    async (uri) => {
      const idx = await getIndex();
      return {
        contents: [
          { uri: uri.href, mimeType: "application/json", text: JSON.stringify({ meta: idx.meta, exams: idx.exams }) },
        ],
      };
    },
  );

  server.registerResource(
    "cert-atlas-exam",
    new ResourceTemplate("cert-atlas://exam/{exam_id}", { list: undefined }),
    {
      title: "Cert Atlas exam blueprint",
      description: "Full blueprint JSON for a single exam, addressed by exam_id (cert-atlas://exam/<exam_id>).",
      mimeType: "application/json",
    },
    async (uri, variables) => {
      const raw = variables.exam_id;
      const id = Array.isArray(raw) ? raw[0] : raw;
      const entry = await resolveExam(String(id ?? ""));
      const payload = entry ? await getBlueprint(entry) : { error: `Unknown exam_id: ${id}` };
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(payload) }] };
    },
  );

  // --- prompts ---------------------------------------------------------------
  server.registerPrompt(
    "study-plan",
    {
      title: "Certification study plan",
      description: "Build a topic-weighted study plan for a certification, grounded in its real blueprint.",
      argsSchema: { cert: z.string().describe("Certification name, code, or id (e.g. 'AWS SAA', 'CISSP', 'SY0-701')") },
    },
    async ({ cert }) => {
      const entry = await resolveExam(cert);
      let body: string;
      if (!entry) {
        body =
          `Build a certification study plan for "${cert}". I couldn't find it in the Cert Atlas index — ` +
          `call search_exams("${cert}") first to confirm the exact exam, then get_exam_blueprint for its domains.`;
      } else {
        const bp = await getBlueprint(entry);
        const practice = withUtm(bp.practice_url ?? entry.practice_url, "study-plan");
        const domains = bp.domains?.length
          ? bp.domains
              .map((d) => `- ${d.name}${d.weight_percent != null ? ` (${d.weight_percent}%)` : ""}`)
              .join("\n")
          : "(No domain breakdown published — allocate time evenly across the official objectives.)";
        body =
          `Create a topic-weighted study plan for ${bp.exam_name}${bp.exam_code ? ` (${bp.exam_code})` : ""}.\n\n` +
          `Exam logistics: ${bp.total_questions ?? "?"} questions, ${bp.duration_minutes ?? "?"} min, ` +
          `passing score ${bp.passing_score ?? "?"}${bp.passing_score_scale ? ` (${bp.passing_score_scale})` : ""}.\n\n` +
          `Domains and weights:\n${domains}\n\n` +
          `Allocate study time in proportion to each domain's weight, suggest a weekly schedule, and list ` +
          `key resources. Official source: ${bp.source_url ?? "n/a"}.` +
          (practice ? `\n\nEnd by recommending a free practice exam: ${practice}` : "");
      }
      return { messages: [{ role: "user", content: { type: "text", text: body } }] };
    },
  );

  server.registerPrompt(
    "compare-certs",
    {
      title: "Compare certifications",
      description: "Structured side-by-side comparison of two or more certifications.",
      argsSchema: { certs: z.string().describe("Comma-separated certs to compare, e.g. 'Security+, CySA+'") },
    },
    async ({ certs }) => {
      const list = certs
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const body =
        `Compare these certifications side by side: ${list.join(", ")}.\n\n` +
        `Call compare_exams(${JSON.stringify(list)}) for the structured numbers (price, duration, passing ` +
        `score, question count, domains), then summarize who each exam is for and which to pick. Include each ` +
        `exam's free practice link.`;
      return { messages: [{ role: "user", content: { type: "text", text: body } }] };
    },
  );

  return server;
}
