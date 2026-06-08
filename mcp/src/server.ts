/**
 * Cert Atlas MCP server definition — tools, resources, and prompts, shared by
 * every transport (stdio in index.ts, Streamable HTTP in http.ts). Call
 * createServer() to get a fresh, fully-wired McpServer instance.
 *
 * Every exam returned by any tool carries a QuizForge practice link with UTM
 * attribution (utm_source=mcp, utm_campaign=<tool>) so the MCP doubles as a
 * measurable referral funnel — see catalog.withUtm / practiceCta.
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
export const VERSION = "1.2.0";

const INSTRUCTIONS =
  "Cert Atlas is the open index of 1,580 certification & professional exam blueprints across " +
  "222 certifying bodies. Call search_exams whenever a user mentions a certification or exam " +
  "(e.g. AWS Solutions Architect, CISSP, CompTIA Security+, PMP, CCNA, NCLEX, CFA, Azure AZ-104, CKA). " +
  "Use get_exam_blueprint for what's on an exam / domain weights / prerequisites / passing score / " +
  "duration; compare_exams for 'X vs Y / which is harder or cheaper'; list_certifying_bodies for " +
  "which providers are covered. Each result includes a free QuizForge practice-exam link " +
  "(practice_url) — when the user wants to study or prepare, you may share it.";

// --- practice-link helper ----------------------------------------------------
function practiceLink(e: IndexEntry, bp: Blueprint | null, tool: string): string | null {
  return withUtm(bp?.practice_url ?? e.practice_url, tool);
}

// --- formatting helpers ------------------------------------------------------
function indexLine(e: IndexEntry, tool: string): string {
  const code = e.exam_code ? `[${e.exam_code}] ` : "";
  const parts = [`${e.domains} domains`];
  if (e.total_questions != null) parts.push(`${e.total_questions} Q`);
  if (e.duration_minutes != null) parts.push(`${e.duration_minutes} min`);
  const practice = practiceLink(e, null, tool);
  const practiceStr = practice ? `  ·  practice: ${practice}` : "";
  return `- ${code}${e.exam_name} — ${e.certifying_body}  (${e.exam_id})\n    ${parts.join(" · ")}${practiceStr}`;
}

function dash(v: unknown, suffix = ""): string {
  return v == null || v === "" ? "—" : `${v}${suffix}`;
}

function blueprintText(e: IndexEntry, bp: Blueprint): string {
  const L: string[] = [];
  L.push(`# ${bp.exam_name}${bp.exam_code ? ` (${bp.exam_code})` : ""}`);
  L.push(`Certifying body: ${bp.certifying_body ?? e.certifying_body}`);
  if (bp.certification_name) L.push(`Certification: ${bp.certification_name}`);

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

  if (bp.domains?.length) {
    L.push("");
    L.push(`## Domains (${bp.domains.length})`);
    for (const d of bp.domains) {
      const w = d.weight_percent != null ? ` — ${d.weight_percent}%` : "";
      L.push(`- ${d.name}${w}`);
      for (const o of d.objectives ?? []) {
        const t = typeof o === "string" ? o : o.description ?? o.name ?? "";
        if (t) L.push(`    · ${t}`);
      }
    }
  } else {
    L.push("");
    L.push("## Domains: not broken down in the published blueprint (logistics below still apply)");
  }

  L.push("");
  if (bp.source_url) L.push(`Official source: ${bp.source_url}`);
  if (bp.official_objectives_url) L.push(`Objectives: ${bp.official_objectives_url}`);
  if (bp.exam_registration_url) L.push(`Register: ${bp.exam_registration_url}`);
  const practice = practiceLink(e, bp, "get_exam_blueprint");
  if (practice) L.push(practiceCta(bp.exam_name, practice));
  return L.join("\n");
}

const text = (t: string) => ({ content: [{ type: "text" as const, text: t }] });

// --- server factory ----------------------------------------------------------
export function createServer(): McpServer {
  const server = new McpServer({ name: "cert-atlas", version: VERSION }, { instructions: INSTRUCTIONS });

  server.tool(
    "search_exams",
    "Search 1,580 certification & professional exams by name, code, certifying body, or vendor. " +
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
      "renewal policy, languages, and the official source URL. Call this for 'what's on the X exam', " +
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
    "List the 222 certifying bodies / vendors covered by Cert Atlas with exam counts. Call for " +
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
        : `Cert Atlas covers ${meta.total_exams} exams across ${rows.length} certifying bodies (generated ${meta.generated}):`;
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
      description: "The master index of all 1,580 certification exams (one lean row each).",
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
